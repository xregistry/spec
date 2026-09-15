# Document pointer regression examples

<!-- no verify-specs -->
<!-- words: jsonpointer powershell py pytest sdk serializer -->

[The issue 580 tests](test_document_pointers_580.py) resolve the actual
[Core Doc Flag examples](../core/spec.md#doc-flag) using the independent
`jsonpointer` library, after decoding the URI fragment. In particular, `#`
selects the response root, while `#/` selects an empty-name member.

An abstract link projection also exercises Registry, Group, Resource, Meta,
Version, and collection response roots. It takes an already selected response
and explicit target locations, escapes pointer tokens, and converts only links
to included targets. Assertions cover collection, Meta, default-Version and
`self` links, escaped tilde tokens, fragment percent-encoding, removal of the
HTTP metadata suffix from local links, preservation of external links, and
unchanged API input. Generic JSON keys in the encoding example test RFC6901;
they do not extend the permitted xRegistry identifier characters.

Source-contract assertions separately guard the distinction between immutable
API identity and response-local `self` values. These tests are not a server,
an SDK conformance test, or a complete document-view serializer: they do not
perform filtering, inlining, document retrieval, or the other Doc Flag
transformations.

Run the focused examples from the repository root:

```powershell
python -B -m pytest tools\test_document_pointers_580.py -q
```
