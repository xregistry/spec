// verify.go is a Go port of tools/verify.py + tools/test_verify.py.
//
// Usage:
//
//	go run verify.go [root]     # scan ROOT (default ".") for issues in *.md/*.htm* files
//	go run verify.go --test     # run the self-test suite against tools/fake-docs fixtures
//
// It checks markdown/html docs for: dangling local/http(s) links, undefined
// markdown bookmark references, banned phrases ("Cloud Event(s)"), incorrect
// capitalization of RFC-2119 keywords, missing capital letter after a list
// dash, missing translation files, and mismatched titles between spec.md and
// README.md (and their translations).
package main

import (
	"bytes"
	"crypto/tls"
	"flag"
	"fmt"
	"io/fs"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"runtime"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/duglin/goldmark"
	"github.com/duglin/goldmark/extension"
	"github.com/duglin/goldmark/parser"
	ghtml "github.com/duglin/goldmark/renderer/html"
	xhtml "golang.org/x/net/html"
)

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Issue string

type TaggedIssue struct {
	Path  string
	Issue Issue
}

type Settings struct {
	ExcludedPaths      map[string]bool // absolute paths
	HTTPMaxAttempts    int
	HTTPTimeoutSeconds int
}

// ---------------------------------------------------------------------------
// Paths / globals (mirrors _TOOLS_DIR / _REPO_ROOT / _FAKE_DOCS_DIR in verify.py)
// ---------------------------------------------------------------------------

var (
	toolsDir         string
	repoRoot         string
	fakeDocsDir      string
	rootLanguagesDir string
)

func init() {
	_, thisFile, _, _ := runtime.Caller(0)
	toolsDir, _ = filepath.Abs(filepath.Dir(thisFile))
	repoRoot = filepath.Dir(toolsDir)
	fakeDocsDir = filepath.Join(toolsDir, "fake-docs")
	rootLanguagesDir = filepath.Join(repoRoot, "languages")
}

// ---------------------------------------------------------------------------
// Regexes (RE2 has no lookaround, so patterns needing lookaround are matched
// with a permissive base regex and then filtered manually - see the
// filtered*Matches helpers below).
// ---------------------------------------------------------------------------

var (
	reSkipText = regexp.MustCompile(`(?i)<!--\s*no[\s-]+verify[\s-]+(?P<type>\w+)[\s-]*-->`)

	// base pattern for markdown bookmark refs; lookaround is applied manually
	reBookmarkBase = regexp.MustCompile(`(?i)\[[^?=].+?\]\[.+?\]`)

	// base pattern for RFC-2119 keywords; lookaround is applied manually
	reCapWordsBase = regexp.MustCompile(`(?i)(?P<must>MUST(\s+NOT)?)|(?P<required>REQUIRED)|(?P<shall>\bSHALL(\s+NOT)?\b)|(?P<should>SHOULD(\s+NOT)?)|(?P<recommended>RECOMMENDED)|(?P<may>\bMAY\b)|(?P<optional>\bOPTIONAL\b)`)

	reBannedPhrase = regexp.MustCompile(`(?i)Cloud\s+Events?`)

	// no lookaround needed here
	reCapitalDash = regexp.MustCompile(`(?m)(^\s*)(-\s*([a-wyz]|(x([^R]|$))))`)

	reLanguagesDir = regexp.MustCompile(`(^|/)languages(/|$)`)
)

const languagesDirName = "languages"

// ---------------------------------------------------------------------------
// Small python-ish helpers
// ---------------------------------------------------------------------------

// pyRepr approximates Python's repr() for strings: single-quoted, backslash
// and control characters escaped, using double quotes if the string contains
// a single quote but no double quote.
func pyRepr(s string) string {
	quote := byte('\'')
	if strings.Contains(s, "'") && !strings.Contains(s, "\"") {
		quote = '"'
	}
	var b strings.Builder
	b.WriteByte(quote)
	for _, r := range s {
		switch r {
		case '\\':
			b.WriteString(`\\`)
		case rune(quote):
			b.WriteByte('\\')
			b.WriteRune(r)
		case '\n':
			b.WriteString(`\n`)
		case '\r':
			b.WriteString(`\r`)
		case '\t':
			b.WriteString(`\t`)
		default:
			b.WriteRune(r)
		}
	}
	b.WriteByte(quote)
	return b.String()
}

func isTextAllUppercase(text string) bool {
	return text == strings.ToUpper(text)
}

func lineOfMatch(text string, pos int) int {
	if pos > len(text) {
		pos = len(text)
	}
	return strings.Count(text[:pos], "\n") + 1
}

func toPosix(p string) string {
	return filepath.ToSlash(p)
}

func isASCIIText(s string) bool {
	for i := 0; i < len(s); i++ {
		if s[i] > 127 {
			return false
		}
	}
	return true
}

// ---------------------------------------------------------------------------
// skip-comment handling
// ---------------------------------------------------------------------------

func skipType(text string) string {
	m := reSkipText.FindStringSubmatch(text)
	if m == nil {
		return ""
	}
	idx := reSkipText.SubexpIndex("type")
	if idx < 0 || idx >= len(m) {
		return ""
	}
	return m[idx]
}

func shouldSkipPlainTextIssues(text string) bool   { return skipType(text) == "specs" }
func shouldSkipHTMLIssues(html string) bool        { return skipType(html) == "links" }
func shouldSkipTranslationIssues(text string) bool { return skipType(text) == "translation" }

// ---------------------------------------------------------------------------
// Bookmark reference matching (manual lookaround)
// ---------------------------------------------------------------------------

type textMatch struct {
	start, end int
	text       string
}

func filteredBookmarkMatches(text string) []textMatch {
	var out []textMatch
	for _, loc := range reBookmarkBase.FindAllStringIndex(text, -1) {
		start, end := loc[0], loc[1]
		if start > 0 && text[start-1] == '\\' {
			continue
		}
		rest := text[end:]
		lower := strings.ToLower(rest)
		if strings.HasPrefix(lower, "</code") || strings.HasPrefix(lower, "*</code") {
			continue
		}
		out = append(out, textMatch{start, end, text[start:end]})
	}
	return out
}

func firstBookmarkMatch(text string) (string, bool) {
	m := filteredBookmarkMatches(text)
	if len(m) == 0 {
		return "", false
	}
	return m[0].text, true
}

func undefinedBookmarkIssues(html string) []Issue {
	var issues []Issue
	for _, m := range filteredBookmarkMatches(html) {
		issues = append(issues, Issue(fmt.Sprintf(
			"line %d: Undefined markdown bookmark referenced (%s)",
			lineOfMatch(html, m.start), pyRepr(m.text),
		)))
	}
	return issues
}

// ---------------------------------------------------------------------------
// RFC-2119 keyword capitalization matching (manual lookaround)
// ---------------------------------------------------------------------------

func filteredCapMatches(text string) []textMatch {
	names := reCapWordsBase.SubexpNames()
	var out []textMatch
	for _, m := range reCapWordsBase.FindAllStringSubmatchIndex(text, -1) {
		start, end := m[0], m[1]
		kind := ""
		for gi := 1; gi < len(names); gi++ {
			if names[gi] == "" {
				continue
			}
			if 2*gi+1 < len(m) && m[2*gi] != -1 {
				kind = names[gi]
				break
			}
		}
		valid := true
		switch kind {
		case "must", "shall", "should", "recommended", "may", "optional":
			if start > 0 && text[start-1] == '`' {
				valid = false
			}
		case "required":
			if start > 0 && strings.IndexByte("-.`\"_#", text[start-1]) >= 0 {
				valid = false
			}
			if end < len(text) && strings.IndexByte("`\"_", text[end]) >= 0 {
				valid = false
			}
		}
		if !valid {
			continue
		}
		out = append(out, textMatch{start, end, text[start:end]})
	}
	return out
}

func firstCapMatch(text string) (string, bool) {
	m := filteredCapMatches(text)
	if len(m) == 0 {
		return "", false
	}
	return m[0].text, true
}

func miscasedPhraseIssues(text string) []Issue {
	var issues []Issue
	for _, m := range filteredCapMatches(text) {
		if isTextAllUppercase(m.text) {
			continue
		}
		issues = append(issues, Issue(fmt.Sprintf(
			"line %d: %s MUST be capitalized (%s)",
			lineOfMatch(text, m.start), pyRepr(m.text), pyRepr(strings.ToUpper(m.text)),
		)))
	}
	return issues
}

// ---------------------------------------------------------------------------
// Banned phrase + capital-dash issues
// ---------------------------------------------------------------------------

func bannedPhraseIssues(text string) []Issue {
	var issues []Issue
	for _, loc := range reBannedPhrase.FindAllStringIndex(text, -1) {
		matched := text[loc[0]:loc[1]]
		issues = append(issues, Issue(fmt.Sprintf(
			"line %d: %s is banned", lineOfMatch(text, loc[0]), pyRepr(matched),
		)))
	}
	return issues
}

func capitalDashIssues(text string) []Issue {
	var issues []Issue
	for _, m := range reCapitalDash.FindAllStringSubmatchIndex(text, -1) {
		// group 2 is the "-\s*X" portion
		g2start, g2end := m[4], m[5]
		if g2start < 0 {
			continue
		}
		group2 := text[g2start:g2end]
		issues = append(issues, Issue(fmt.Sprintf(
			"line %d: %s should start with a capital letter after the dash",
			lineOfMatch(text, m[0]), pyRepr(group2),
		)))
	}
	return issues
}

func plainTextIssues(text string) []Issue {
	if shouldSkipPlainTextIssues(text) {
		return nil
	}
	var issues []Issue
	issues = append(issues, bannedPhraseIssues(text)...)
	issues = append(issues, capitalDashIssues(text)...)
	issues = append(issues, miscasedPhraseIssues(text)...)
	return issues
}

// ---------------------------------------------------------------------------
// Markdown -> HTML rendering
// ---------------------------------------------------------------------------

var md = goldmark.New(
	goldmark.WithExtensions(extension.GFM),
	goldmark.WithParserOptions(parser.WithAutoHeadingID()),
	goldmark.WithRendererOptions(ghtml.WithUnsafe()),
)

func removeAnglesInHeaders(text string) string {
	lines := strings.Split(text, "\n")
	for i, line := range lines {
		if strings.HasPrefix(strings.TrimSpace(line), "#") {
			lines[i] = strings.NewReplacer("<", "", ">", "").Replace(line)
		}
	}
	return strings.Join(lines, "\n")
}

func renderMarkdownToHTML(markdownText string) string {
	var buf bytes.Buffer
	_ = md.Convert([]byte(markdownText), &buf)
	return buf.String()
}

// ---------------------------------------------------------------------------
// Read/render caches (mirrors @lru_cache on _read_text / read_html_text)
// ---------------------------------------------------------------------------

var (
	textCacheMu sync.Mutex
	textCache   = map[string]string{}
	htmlCacheMu sync.Mutex
	htmlCache   = map[string]string{}
)

func readText(path string) string {
	textCacheMu.Lock()
	if v, ok := textCache[path]; ok {
		textCacheMu.Unlock()
		return v
	}
	textCacheMu.Unlock()

	data, err := os.ReadFile(path)
	if err != nil {
		return ""
	}
	text := string(data)

	textCacheMu.Lock()
	textCache[path] = text
	textCacheMu.Unlock()
	return text
}

func readHTMLText(path string) string {
	htmlCacheMu.Lock()
	if v, ok := htmlCache[path]; ok {
		htmlCacheMu.Unlock()
		return v
	}
	htmlCacheMu.Unlock()

	var result string
	if strings.HasSuffix(path, ".md") {
		result = renderMarkdownToHTML(removeAnglesInHeaders(readText(path)))
	} else {
		result = readText(path) // assume already html
	}

	htmlCacheMu.Lock()
	htmlCache[path] = result
	htmlCacheMu.Unlock()
	return result
}

// ---------------------------------------------------------------------------
// HTML walking helpers (replacement for BeautifulSoup)
// ---------------------------------------------------------------------------

func findAllHrefs(htmlText string) []string {
	doc, err := xhtml.Parse(strings.NewReader(htmlText))
	if err != nil {
		return nil
	}
	var hrefs []string
	var walk func(*xhtml.Node)
	walk = func(n *xhtml.Node) {
		if n.Type == xhtml.ElementNode && n.Data == "a" {
			for _, a := range n.Attr {
				if a.Key == "href" {
					v := strings.TrimSpace(a.Val)
					if v != "" {
						hrefs = append(hrefs, v)
					}
				}
			}
		}
		for c := n.FirstChild; c != nil; c = c.NextSibling {
			walk(c)
		}
	}
	walk(doc)
	return hrefs
}

// htmlContainsID mirrors _does_html_contains_id in verify.py: if the id is
// not found, it also returns every valid id present in the document
// (sorted), so the caller can attach that list directly to the reported
// issue (keeping it next to the relevant error instead of printed
// separately/out-of-order during the scan).
func htmlContainsID(htmlText, id string) (bool, []string) {
	doc, err := xhtml.Parse(strings.NewReader(htmlText))
	if err != nil {
		return false, nil
	}
	found := false
	var allIDs []string
	var walk func(*xhtml.Node)
	walk = func(n *xhtml.Node) {
		if n.Type == xhtml.ElementNode {
			for _, a := range n.Attr {
				if a.Key == "id" {
					allIDs = append(allIDs, a.Val)
					if a.Val == id {
						found = true
					}
				}
			}
		}
		for c := n.FirstChild; c != nil; c = c.NextSibling {
			walk(c)
		}
	}
	walk(doc)

	if found {
		return true, nil
	}
	sort.Strings(allIDs)
	return false, allIDs
}

// ---------------------------------------------------------------------------
// URI issue resolution
// ---------------------------------------------------------------------------

func missingSegmentIssue(path, segment string, validIDs []string) Issue {
	msg := fmt.Sprintf("%s does not contain %s segment", toPosix(path), pyRepr("#"+segment))
	if len(validIDs) > 0 {
		msg += "\nVALID IDs:\n" + strings.Join(validIDs, "\n") + "\n"
	}
	return Issue(msg)
}

func missingFileIssue(path string) Issue {
	return Issue(fmt.Sprintf("%s does not exist", toPosix(path)))
}

func localPathURIIssues(uri, currentPath string) []Issue {
	parts := strings.Split(uri, "#")
	var path, segment string
	switch len(parts) {
	case 1:
		path = filepath.Join(filepath.Dir(currentPath), parts[0])
	case 2:
		if parts[0] == "" {
			path = currentPath
		} else {
			path = filepath.Join(filepath.Dir(currentPath), parts[0])
		}
		segment = parts[1]
	default:
		return []Issue{Issue("Invalid local path uri: " + uri)}
	}

	if _, err := os.Stat(path); err != nil {
		return []Issue{missingFileIssue(path)}
	}
	if segment != "" {
		if found, validIDs := htmlContainsID(readHTMLText(path), segment); !found {
			return []Issue{missingSegmentIssue(path, segment, validIDs)}
		}
	}
	return nil
}

func uriAvailabilityIssues(uri string, settings Settings) []Issue {
	if strings.Contains(uri, "example.com") || strings.Contains(uri, "ietf.org") || strings.Contains(uri, "rfc-edit.org") {
		return nil
	}

	client := &http.Client{
		Timeout: time.Duration(settings.HTTPTimeoutSeconds) * time.Second,
		Transport: &http.Transport{
			TLSClientConfig: &tls.Config{InsecureSkipVerify: true}, // mirrors ssl=False in verify.py
		},
	}

	maxAttempts := settings.HTTPMaxAttempts
	if maxAttempts <= 0 {
		maxAttempts = 1
	}
	for attempt := 0; attempt < maxAttempts; attempt++ {
		resp, err := client.Get(uri)
		if err != nil {
			continue
		}
		status := resp.StatusCode
		resp.Body.Close()
		if status == http.StatusNotFound {
			return []Issue{Issue(fmt.Sprintf("%s was not found", pyRepr(uri)))}
		}
		return nil
	}
	return []Issue{Issue(fmt.Sprintf("Could Not access %s", pyRepr(uri)))}
}

func uriIssues(uri, path string, settings Settings) []Issue {
	scheme := strings.SplitN(uri, ":", 2)[0]
	switch scheme {
	case "http", "https":
		return uriAvailabilityIssues(uri, settings)
	case "mailto":
		return nil
	default:
		return localPathURIIssues(uri, path)
	}
}

// ---------------------------------------------------------------------------
// Per-file HTML issues (links + undefined bookmarks)
// ---------------------------------------------------------------------------

func htmlIssues(path string, settings Settings) []Issue {
	htmlText := readHTMLText(path)
	if shouldSkipHTMLIssues(htmlText) {
		return nil
	}

	hrefs := findAllHrefs(htmlText)
	var issues []Issue
	var mu sync.Mutex
	var wg sync.WaitGroup
	for _, uri := range hrefs {
		wg.Add(1)
		go func(u string) {
			defer wg.Done()
			iss := uriIssues(u, path, settings)
			if len(iss) > 0 {
				mu.Lock()
				issues = append(issues, iss...)
				mu.Unlock()
			}
		}(uri)
	}
	wg.Wait()

	issues = append(issues, undefinedBookmarkIssues(htmlText)...)
	return issues
}

// ---------------------------------------------------------------------------
// Translation-file existence checks
// ---------------------------------------------------------------------------

func isEnglishFile(path string) bool {
	abs, err := filepath.Abs(path)
	if err != nil {
		abs = path
	}
	return !reLanguagesDir.MatchString(filepath.ToSlash(abs))
}

func isDir(path string) bool {
	info, err := os.Stat(path)
	return err == nil && info.IsDir()
}

func isRootLanguagesDir(path string) bool {
	abs, _ := filepath.Abs(path)
	rootAbs, _ := filepath.Abs(rootLanguagesDir)
	return abs == rootAbs
}

// translationsDirectory walks up from path's ancestors looking for a sibling
// "languages" directory, mirroring _translations_directory in verify.py.
func translationsDirectory(path string) (string, bool) {
	if !isEnglishFile(path) {
		return "", false
	}
	cur := path
	for {
		parent := filepath.Dir(cur)
		langDir := filepath.Join(parent, languagesDirName)
		if isDir(langDir) && !isRootLanguagesDir(langDir) {
			return langDir, true
		}
		if parent == cur {
			return "", false
		}
		cur = parent
	}
}

func expectedLanguageCodes(langDir string) []string {
	entries, err := os.ReadDir(langDir)
	if err != nil {
		return nil
	}
	var codes []string
	for _, e := range entries {
		if e.IsDir() {
			codes = append(codes, e.Name())
		}
	}
	return codes
}

func expectedTranslationFiles(path string) []string {
	if !isEnglishFile(path) {
		return nil
	}
	langDir, ok := translationsDirectory(path)
	if !ok {
		return nil
	}
	projectDir := filepath.Dir(langDir)
	relPath, err := filepath.Rel(projectDir, path)
	if err != nil {
		return nil
	}
	var files []string
	for _, code := range expectedLanguageCodes(langDir) {
		files = append(files, filepath.Join(langDir, code, relPath))
	}
	return files
}

func translationIssues(path string) []Issue {
	if shouldSkipTranslationIssues(readText(path)) {
		return nil
	}
	if !isEnglishFile(path) {
		return nil
	}
	var issues []Issue
	for _, tf := range expectedTranslationFiles(path) {
		if _, err := os.Stat(tf); err != nil {
			issues = append(issues, Issue(fmt.Sprintf("Translation file %s does not exist", toPosix(tf))))
		}
	}
	return issues
}

// ---------------------------------------------------------------------------
// Title-matching checks
// ---------------------------------------------------------------------------

func filesThatShouldHaveMatchingTitles(path string) []string {
	files := append([]string{}, expectedTranslationFiles(path)...)
	if filepath.Base(path) == "spec.md" {
		files = append(files, filepath.Join(filepath.Dir(path), "README.md"))
	}
	return files
}

func existingPaths(paths []string) []string {
	var out []string
	for _, p := range paths {
		if _, err := os.Stat(p); err == nil {
			out = append(out, p)
		}
	}
	return out
}

func fileTitle(path string) string {
	text := readText(path)
	lines := strings.SplitN(text, "\n", 2)
	return strings.TrimRight(lines[0], " \t\r")
}

func titlesMatch(a, b string) bool {
	if isASCIIText(a) && isASCIIText(b) {
		return a == b
	}
	return true // translations probably have specific titles
}

func nonMatchingTitlesIssue(pathA, pathB string) Issue {
	return Issue(fmt.Sprintf(
		"title (%s) does not match the title of %s (%s)",
		pyRepr(fileTitle(pathA)), toPosix(pathB), pyRepr(fileTitle(pathB)),
	))
}

func titleIssues(path string) []Issue {
	var issues []Issue
	for _, other := range existingPaths(filesThatShouldHaveMatchingTitles(path)) {
		if !titlesMatch(fileTitle(path), fileTitle(other)) {
			issues = append(issues, nonMatchingTitlesIssue(path, other))
		}
	}
	return issues
}

// ---------------------------------------------------------------------------
// Aggregating per-file / per-directory issues
// ---------------------------------------------------------------------------

func fileIssues(path string, settings Settings) []TaggedIssue {
	var issues []Issue
	issues = append(issues, htmlIssues(path, settings)...)
	issues = append(issues, plainTextIssues(readText(path))...)
	issues = append(issues, translationIssues(path)...)
	issues = append(issues, titleIssues(path)...)

	tagged := make([]TaggedIssue, len(issues))
	for i, is := range issues {
		tagged[i] = TaggedIssue{Path: path, Issue: is}
	}
	return tagged
}

func allDocs(root string, excludedPaths map[string]bool) []string {
	var out []string
	_ = filepath.WalkDir(root, func(p string, d fs.DirEntry, err error) error {
		if err != nil || d.IsDir() {
			return nil
		}
		lower := strings.ToLower(d.Name())
		if !strings.HasSuffix(lower, ".md") && !strings.Contains(lower, ".htm") {
			return nil
		}
		abs, _ := filepath.Abs(p)
		if excludedPaths[abs] {
			return nil
		}
		out = append(out, p)
		return nil
	})
	sort.Strings(out)
	return out
}

func directoryIssues(root string, settings Settings) []TaggedIssue {
	docs := allDocs(root, settings.ExcludedPaths)

	var mu sync.Mutex
	var all []TaggedIssue
	var wg sync.WaitGroup
	sem := make(chan struct{}, 8)

	for _, path := range docs {
		wg.Add(1)
		sem <- struct{}{}
		go func(p string) {
			defer wg.Done()
			defer func() { <-sem }()
			iss := fileIssues(p, settings)
			if len(iss) > 0 {
				mu.Lock()
				all = append(all, iss...)
				mu.Unlock()
			}
		}(path)
	}
	wg.Wait()
	return all
}

func printIssues(issues []TaggedIssue) {
	seen := map[string]bool{}
	for _, ti := range issues {
		fmt.Printf("> %s: %s\n", ti.Path, ti.Issue)
		seen[ti.Path] = true
	}
	fmt.Printf("ERROR: Had %d issues, in %d files\n", len(issues), len(seen))
}

// ---------------------------------------------------------------------------
// main
// ---------------------------------------------------------------------------

func defaultExcludedPaths() map[string]bool {
	excluded := map[string]bool{}
	abs, _ := filepath.Abs(fakeDocsDir)
	_ = filepath.WalkDir(abs, func(p string, d fs.DirEntry, err error) error {
		if err != nil {
			return nil
		}
		a, _ := filepath.Abs(p)
		excluded[a] = true
		return nil
	})
	return excluded
}

func main() {
	testMode := flag.Bool("test", false,
		"run the self-test suite against tools/fake-docs fixtures")
	flag.Parse()

	if *testMode {
		if !runSelfTests() {
			os.Exit(1)
		}
		if flag.NArg() == 0 {
			os.Exit(0)
		}
	}

	root := "."
	if flag.NArg() > 0 {
		root = flag.Arg(0)
	}

	settings := Settings{
		ExcludedPaths:      defaultExcludedPaths(),
		HTTPMaxAttempts:    5,
		HTTPTimeoutSeconds: 10,
	}

	issues := directoryIssues(root, settings)
	if len(issues) > 0 {
		printIssues(issues)
		os.Exit(1)
	}
	fmt.Println("Spec verification succeeded")
}

// ---------------------------------------------------------------------------
// Self-test harness (go run verify.go --test)
//
// This reproduces test_verify.py's unit tests (regex/pattern behavior) plus
// its test_app integration test, run against the same tools/fake-docs
// fixtures. It is a hand-rolled assertion harness (not `go test`) so that
// verify.go can remain a single, dependency-free-of-testing-framework file.
// ---------------------------------------------------------------------------

type testResult struct {
	name string
	pass bool
	msg  string
}

var testResults []testResult

func check(name string, cond bool, msg string) {
	testResults = append(testResults, testResult{name: name, pass: cond, msg: msg})
}

func checkEqual(name string, got, want interface{}) {
	gs := fmt.Sprintf("%v", got)
	ws := fmt.Sprintf("%v", want)
	check(name, gs == ws, fmt.Sprintf("got:  %s\nwant: %s", gs, ws))
}

func runSelfTests() bool {
	testResults = nil

	testSkipTextPattern()
	testBookmarkPatternMatches()
	testBannedPhrasePatternMatches()
	testCapitalizationPhrases()
	testIsTextAllUppercase()
	testPlainTextIssues()
	testHeadersRenderedWithIDs()
	testApp()

	failed := 0
	for _, r := range testResults {
		if !r.pass {
			failed++
			fmt.Printf("[FAIL] %s\n", r.name)
			if r.msg != "" {
				fmt.Println(indent(r.msg, "    "))
			}
		}
	}
	fmt.Printf("Validating the tool: %d/%d tests passed\n",
		len(testResults)-failed, len(testResults))
	return failed == 0
}

func indent(s, prefix string) string {
	lines := strings.Split(s, "\n")
	for i, l := range lines {
		lines[i] = prefix + l
	}
	return strings.Join(lines, "\n")
}

// test_skip_text (parametrized)
func testSkipTextPattern() {
	cases := []struct{ given, expected string }{
		{"sadnakskd bad <!--  no verify specs --> dasdasd", "<!--  no verify specs -->"},
		{"sadnakskd bad <!--\t no-verify-docs --> dasdasd", "<!--\t no-verify-docs -->"},
		{"sadnakskd bad <!--no-verify-specs--> dasdasd", "<!--no-verify-specs-->"},
	}
	for _, c := range cases {
		m := reSkipText.FindString(c.given)
		checkEqual(fmt.Sprintf("test_skip_text(%q)", c.given), m, c.expected)
	}
}

// test_bookmark_pattern_matches_given_patterns
func testBookmarkPatternMatches() {
	cases := []struct {
		given    string
		expected string
		hasMatch bool
	}{
		{"sadnakskd bad [Hello][World] dasdasd", "[Hello][World]", true},
		{"sadnakskd bad [What is going][on]dasdasd", "[What is going][on]", true},
		{"This is [not] [a bookmark]", "", false},
	}
	for _, c := range cases {
		got, ok := firstBookmarkMatch(c.given)
		if c.hasMatch {
			checkEqual(fmt.Sprintf("test_bookmark_pattern(%q)", c.given), got, c.expected)
		} else {
			check(fmt.Sprintf("test_bookmark_pattern(%q)", c.given), !ok, fmt.Sprintf("expected no match, got %q", got))
		}
	}
}

// test_bookmark_pattern_matches_given_patterns (banned phrase variant, same
// name reused in python for the banned-phrase pattern test)
func testBannedPhrasePatternMatches() {
	cases := []struct {
		given    string
		expected string
		hasMatch bool
	}{
		{"sad asd Cloud Events asd asd", "Cloud Events", true},
		{"sad asd Cloud Event asd asd", "Cloud Event", true},
		{"CloudEvent", "", false},
		{"CloudEvents", "", false},
		{"sad asd cloud\t\t\t  events asd asd", "cloud\t\t\t  events", true},
		{"sad asd cloud\nevent asd asd", "cloud\nevent", true},
		{"cloudevent", "", false},
		{"cloudevents", "", false},
	}
	for _, c := range cases {
		loc := reBannedPhrase.FindStringIndex(c.given)
		if c.hasMatch {
			got := ""
			if loc != nil {
				got = c.given[loc[0]:loc[1]]
			}
			checkEqual(fmt.Sprintf("test_banned_phrase(%q)", c.given), got, c.expected)
		} else {
			gotStr := ""
			if loc != nil {
				gotStr = c.given[loc[0]:loc[1]]
			}
			check(fmt.Sprintf("test_banned_phrase(%q)", c.given), loc == nil, fmt.Sprintf("expected no match, got %q", gotStr))
		}
	}
}

// test_capitalization_phrases
func testCapitalizationPhrases() {
	cases := []struct {
		given    string
		expected string
		hasMatch bool
	}{
		{"this sHouLd\n\nnot jsakhndja", "sHouLd\n\nnot", true},
		{"asdjkasbndkj optional asjdkjasjd", "optional", true},
		{"optionally", "", false},
		{" asd asd shall            not asdasdas", "shall            not", true},
		{`asd "required" not asdasdas`, "", false},
		{"this Must, handle commas", "Must", true},
		{"this (must) handle braces", "must", true},
		{"marshall is ok not to be matched", "", false},
		{"may be matched", "may", true},
		{"maybe", "", false},
		{"`required`", "", false},
		{" dasa shall not asjdbajsbd", "shall not", true},
		{"ds as must not asd ", "must not", true},
	}
	for _, c := range cases {
		got, ok := firstCapMatch(c.given)
		if c.hasMatch {
			checkEqual(fmt.Sprintf("test_capitalization(%q)", c.given), got, c.expected)
		} else {
			check(fmt.Sprintf("test_capitalization(%q)", c.given), !ok, fmt.Sprintf("expected no match, got %q", got))
		}
	}
}

// test_upper_text_must_be_detected_as_such / test_non_upper_text_must_be_detected_as_such
func testIsTextAllUppercase() {
	check("test_upper_text_must_be_detected_as_such", isTextAllUppercase("YES"), "")
	check("test_non_upper_text_must_be_detected_as_such", !isTextAllUppercase("tHis Is NoT cOrRect"), "")
}

// test_text_issues
func testPlainTextIssues() {
	text := `
                Hello World this MUST be a test
                SHOULD NOT be something
                should be CloudEvents 
                CloudEvent
                Cloud
                Event
                Cloud Events 
                Cloud
                Events 
                must
                MAY
                MUST
                ShOULD        nOt
                mAy
                Optionally
                - each
                "required"
				marshall
				marshalled
				optionally
				dismay
				maybe
				` + "`required`" + `
				.required
                `

	got := map[string]bool{}
	for _, is := range plainTextIssues(text) {
		got[string(is)] = true
	}

	want := []string{
		"line 6: 'Cloud\\n                Event' is banned",
		"line 8: 'Cloud Events' is banned",
		"line 9: 'Cloud\\n                Events' is banned",
		"line 4: 'should' MUST be capitalized ('SHOULD')",
		"line 11: 'must' MUST be capitalized ('MUST')",
		"line 14: 'ShOULD        nOt' MUST be capitalized ('SHOULD        NOT')",
		"line 15: 'mAy' MUST be capitalized ('MAY')",
		"line 17: '- e' should start with a capital letter after the dash",
	}

	missing := []string{}
	for _, w := range want {
		if !got[w] {
			missing = append(missing, w)
		}
	}
	extra := []string{}
	wantSet := map[string]bool{}
	for _, w := range want {
		wantSet[w] = true
	}
	for g := range got {
		if !wantSet[g] {
			extra = append(extra, g)
		}
	}
	msg := ""
	if len(missing) > 0 {
		msg += fmt.Sprintf("missing: %v\n", missing)
	}
	if len(extra) > 0 {
		msg += fmt.Sprintf("extra: %v\n", extra)
	}
	check("test_text_issues", len(missing) == 0 && len(extra) == 0, msg)
}

// test_headers_must_be_rendered_with_ids / test_rtl_unicode_must_be_rendered_in_the_id
//
// Note: unlike python-markdown, goldmark follows CommonMark strictly and
// requires a space after the leading '#' for a line to be parsed as an ATX
// heading (all real docs in this repo already use "# Title" with a space),
// so this uses "# Hello World" rather than verify.py's lenient "#Hello World".
func testHeadersRenderedWithIDs() {
	got := strings.TrimSpace(renderMarkdownToHTML("# Hello World"))
	checkEqual("test_headers_must_be_rendered_with_ids", got, `<h1 id="hello-world">Hello World</h1>`)
}

// test_app: full directory scan over tools/fake-docs, compared as a set of
// (path, issue) tuples against the expected results. This intentionally
// performs live HTTP requests, matching test_verify.py::test_app's behavior.
func testApp() {
	origWD, _ := os.Getwd()
	if err := os.Chdir(toolsDir); err != nil {
		check("test_app", false, "could not chdir to tools dir: "+err.Error())
		return
	}
	defer os.Chdir(origWD)

	settings := Settings{ExcludedPaths: map[string]bool{}, HTTPMaxAttempts: 2, HTTPTimeoutSeconds: 5}
	got := directoryIssues("fake-docs", settings)

	// The "missing segment" issue message may have a "VALID IDs:" list
	// appended after the first line; compare only the first line so this
	// test doesn't need to track the exact set of ids in the fixtures.
	firstLine := func(s string) string {
		if i := strings.IndexByte(s, '\n'); i >= 0 {
			return s[:i]
		}
		return s
	}

	gotSet := map[string]bool{}
	for _, ti := range got {
		gotSet[fmt.Sprintf("%s\x00%s", toPosix(ti.Path), firstLine(string(ti.Issue)))] = true
	}

	want := []TaggedIssue{
		{"fake-docs/link-verification.md", "Could Not access 'http://non-existing-website.sadkjaskldjalksjd'"},
		{"fake-docs/link-verification.md", "'https://google.com/non-existing-page' was not found"},
		{"fake-docs/link-verification.md", "fake-docs/README.md does not contain '#non-existing' segment"},
		{"fake-docs/link-verification.md", "fake-docs/link-verification.md does not contain '#non-existing' segment"},
		{"fake-docs/link-verification.md", "fake-docs/non-existing.md does not exist"},
		{"fake-docs/text-verification.md", "line 13: 'Cloud\\n\\nEvent' is banned"},
		{"fake-docs/text-verification.md", "line 23: 'must' MUST be capitalized ('MUST')"},
		{"fake-docs/text-verification.md", "line 25: 'must NOT' MUST be capitalized ('MUST NOT')"},
		{"fake-docs/text-verification.md", "line 35: 'must\\n\\nnot' MUST be capitalized ('MUST\\n\\nNOT')"},
		{"fake-docs/text-verification.md", "line 39: 'sHoulD' MUST be capitalized ('SHOULD')"},
		{"fake-docs/text-verification.md", "line 41: 'should not' MUST be capitalized ('SHOULD NOT')"},
		{"fake-docs/text-verification.md", "line 43: 'optionaL' MUST be capitalized ('OPTIONAL')"},
		{"fake-docs/text-verification.md", "line 47: 'shall' MUST be capitalized ('SHALL')"},
		{"fake-docs/text-verification.md", "line 49: 'shall not' MUST be capitalized ('SHALL NOT')"},
		{"fake-docs/text-verification.md", "line 53: 'required' MUST be capitalized ('REQUIRED')"},
		{"fake-docs/text-verification.md", "line 9: 'Cloud Event' is banned"},
		{"fake-docs/text-verification.md", "line 9: 'Cloud Events' is banned"},
		{"fake-docs/README.md", "Translation file fake-docs/languages/your-lang/README.md does not exist"},
		{"fake-docs/README.md", "Translation file fake-docs/languages/my-lang/README.md does not exist"},
		{"fake-docs/link-verification.md", "Translation file fake-docs/languages/your-lang/link-verification.md does not exist"},
		{"fake-docs/text-verification.md", "Translation file fake-docs/languages/my-lang/text-verification.md does not exist"},
		{"fake-docs/yourspec/spec.md", "title ('# Your Spec - Version 1.0.1') does not match the title of fake-docs/yourspec/README.md ('# His Spec - Version 1.0.0')"},
		{"fake-docs/languages/your-lang/myspec/spec.md", "title ('# Your Spec - Version 1.0.0') does not match the title of fake-docs/languages/your-lang/myspec/README.md ('# His Spec - Version 1.0.0')"},
		{"fake-docs/myspec/README.md", "title ('# My Spec - Version 1.0.0') does not match the title of fake-docs/languages/your-lang/myspec/README.md ('# His Spec - Version 1.0.0')"},
		{"fake-docs/myspec/spec.md", "title ('# My Spec - Version 1.0.0') does not match the title of fake-docs/languages/your-lang/myspec/spec.md ('# Your Spec - Version 1.0.0')"},
		// The following issue's exact line number is renderer-dependent (goldmark
		// vs python-markdown produce different HTML for the same source), so we
		// only assert it by path+prefix below rather than hardcoding it in `want`.
	}

	wantSet := map[string]bool{}
	for _, ti := range want {
		wantSet[fmt.Sprintf("%s\x00%s", toPosix(ti.Path), firstLine(string(ti.Issue)))] = true
	}

	// The "undefined markdown bookmark" issue depends on the renderer's exact
	// HTML output layout, so match it by prefix/suffix instead of exact line #.
	bookmarkIssueFound := false
	for _, ti := range got {
		if toPosix(ti.Path) == "fake-docs/link-verification.md" &&
			strings.Contains(string(ti.Issue), "Undefined markdown bookmark referenced ('[link to non existing bookmark][non-existing]')") {
			bookmarkIssueFound = true
			key := fmt.Sprintf("%s\x00%s", toPosix(ti.Path), firstLine(string(ti.Issue)))
			// treat as satisfied/expected so it doesn't show up as "extra" below
			wantSet[key] = true
			want = append(want, ti)
		}
	}

	var missing, extra []string
	for _, w := range want {
		key := fmt.Sprintf("%s\x00%s", toPosix(w.Path), firstLine(string(w.Issue)))
		if !gotSet[key] {
			missing = append(missing, key)
		}
	}
	for k := range gotSet {
		if !wantSet[k] {
			extra = append(extra, k)
		}
	}

	msg := ""
	if !bookmarkIssueFound {
		msg += "missing: undefined markdown bookmark issue for fake-docs/link-verification.md\n"
	}
	if len(missing) > 0 {
		sort.Strings(missing)
		msg += fmt.Sprintf("missing (%d):\n  %s\n", len(missing), strings.Join(missing, "\n  "))
	}
	if len(extra) > 0 {
		sort.Strings(extra)
		msg += fmt.Sprintf("extra (%d):\n  %s\n", len(extra), strings.Join(extra, "\n  "))
	}
	check("test_app (fake-docs integration)", bookmarkIssueFound && len(missing) == 0 && len(extra) == 0, msg)
}
