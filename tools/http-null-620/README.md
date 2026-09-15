# Header deletion and literal string examples

<!-- no verify-specs -->
<!-- words: py pytest redecoded roundtrip sentinel -->

[Reference helper](header_null_620.py) and
[regressions](test_header_null_620.py) accompany the
[HTTP document metadata rules](../../core/http.md#serializing-resource-domain-specific-documents).

Run from the repository root:

```console
python -B -m pytest tools/http-null-620 -q
```

The tests parse the specification's header table and JSON examples. Exact bytes
distinguish `{"name":"null"}` from `{"name":null}`. Bare, quoted and percent-encoded
header spellings of the four-character string remain deletion requests after
one decoding pass. Copying a read header therefore cannot preserve that literal
string on a write; JSON metadata can. Empty strings, case differences, quoted
data and escaped percent signs are not conflated with deletion.

This helper models updates to one optional string attribute, `name`, with no
default, while preserving unrelated metadata. It is not a server or a complete
model validator. Invalid UTF-8, control bytes, malformed escapes, duplicate JSON
keys and non-string values are errors, not successful deletion fallbacks.
Encoded control characters remain metadata data, not raw HTTP framing.
No Core document-null behavior, native HTTP field grammar or metadata map-key
encoding is changed. These are source and abstract codec regressions, not live
HTTP or peer interoperability evidence.
