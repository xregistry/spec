# HTTP metadata and document example checks

<!-- no spellcheck -->
<!-- no verify specs -->

`test_http_metadata_views_596.py` checks actual Resource, Version and Meta
exchanges in `core/http.md`. The examples state local `hasdocument` assumptions:
metadata-only collection URLs stay bare, document-bearing metadata URLs use
`$details`, and raw-document response headers still use document URLs.

The checks compare metadata `self`, applicable `Content-Location`, Meta
`defaultversionurl`, suffix-free XIDs and explicit false-valued `readonly`.
The PUT example proves that sending a document does not implicitly inline it
in a response; the POST and single-Version PUT examples explicitly request it.

Complete bodies used here are parsed as JSON. In other exchanges with
independently tracked literal-syntax defects, only the relevant actual JSON
scalar fields are projected and decoded, and explicit document-member
declarations are inspected. This does not accept malformed JSON as wire input.
Entity-ID copy errors and literal punctuation are separate repairs; the tests
do not silently fix them or claim those exchanges are fully serializable.

These are source-example representation checks, not a server, serializer,
generated-client or interoperability qualification.

Run from the repository root:

```console
python -B -m pytest tools/test_http_metadata_views_596.py -q -p no:cacheprovider
```
