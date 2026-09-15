# Document encoding precedence examples

<!-- no verify-specs -->
<!-- words: base64 json nan powershell py pytest typemap utf -->

[The issue 591 tests](test_document_encoding_591.py) exercise the
[Core document fields](../core/spec.md#resource-attribute) and
[Model type mapping rules](../core/model.md#groupsstringresourcesstringtypemap).
They also read the existing document-store sample and implicit mappings from
the actual source files.

The abstract encoding illustration gives the binary flag priority, resolves
explicit and implicit mappings, escapes strings, embeds valid JSON, and
preserves bytes in the base64 fallback. It covers conflicting and agreeing
wildcard matches, case and media-type parameters, arbitrary non-text bytes,
empty documents, and the limited server preference for base64 when no mapping
applies. JSON number text is retained instead of being rounded to host numeric
types; non-JSON constants such as `NaN` are rejected.

This is a focused source contract and reference calculation, not live server
or client conformance. Models and media types are assumed to have already
passed admission checks. The string examples use UTF-8; the helper does not
define a universal character encoding, infer other character encodings, fetch
documents, or implement write processing. JSON-null round-trip preservation is
a separate issue and is not established by these tests.

Run the focused examples from the repository root:

```powershell
python -B -m pytest tools\test_document_encoding_591.py -q
```
