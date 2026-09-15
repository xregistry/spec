# JSON-null document round-trip examples

<!-- no verify-specs -->
<!-- words: base64 falsy json nan powershell py pytest typemap -->

[The issue 592 tests](test_json_null_document_592.py) combine the
[document response rules](../core/spec.md#resource-attribute) with the
[document-field request rules](../core/spec.md#resource-attribute-processing).
They also execute the new Core base64 example and check the
[JSON type mapping exception](../core/model.md#groupsstringresourcesstringtypemap)
against the actual source.

The abstract export/import calculation starts with stored document bytes.
For a non-empty JSON-null document, it preserves all bytes, including surrounding
JSON whitespace, using the base64 form without requiring the binary flag.
An empty document remains distinct. The tests distinguish JSON `null` from the
JSON string `"null"`, `false`, zero, empty strings, empty arrays, empty objects,
and nested null values. Explicit request null still resets each of the three
document fields; omitted fields and unrelated metadata null do not reset a
locally stored document.

This is source-contract and abstract round-trip evidence, not a live server
or client conformance test. The helper accepts already resolved JSON or binary
selections and UTF-8 document examples; matching type maps and encoding string
documents belong to a separate issue. It does not implement model admission,
external document retrieval, general metadata updates, or full request
transactions. Exact-byte preservation is asserted for base64 paths. Ordinary
non-null JSON writes can still change insignificant formatting; these examples
do not require byte-for-byte preservation for every inline JSON document.

Run the focused examples from the repository root:

```powershell
python -B -m pytest tools\test_json_null_document_592.py -q
```
