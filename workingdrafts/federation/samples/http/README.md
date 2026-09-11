# HTTP Federation Offline Examples

<!-- words: federationerror opc opcua py ua validators website weburl -->

These are synthetic, offline inputs for the
[HTTP federation draft](../../../bindings/http-federation.md), not traffic
captured from a public deployment. No server, credentials or network access
is needed.

## Files

`read-mapping.json` defines a compact model source and fifteen concrete
abstract-request to HTTP-URL mappings. All successful mappings use `GET`.
The model source is interpretation input, not a claim that an effective
`/model` response omits Core's expanded fields. The metadata-only catalog
and document-bearing assets share the paths used by the federation examples.

`transcripts.json` contains named synthetic exchanges. Each `request.url`
is absolute. `request.headers` is the complete set relevant to the example.
Each `response.status` is the HTTP status, `headers` retains significant
headers, and exactly one of `json`, `text` or `base64` supplies a body when
there is one. JSON bodies describe metadata values, not a canonical JSON
byte encoding. `text` is UTF-8 without an added newline. `base64` denotes
exact response bytes. A response without a body member has zero body bytes.
`expected` states the resolver outcome. It is not an HTTP response field.

Collection payloads are metadata maps. No transcript puts domain bytes in
a metadata-only catalog entry. Pagination links are opaque inputs, and the
second page can make an initially promising selection ambiguous.

## Concrete Read Sequences

The `no-filter-catalog` transcript reads enabled capabilities containing
`flags: null` and then reads the complete unfiltered collection:

```http
GET /catalog/capabilities HTTP/1.1
Host: catalog.example.com

HTTP/1.1 200 OK
Content-Type: application/json

{"flags":null,"mutable":[],"pagination":false,"specversions":["1.0-rc4"]}
```

```http
GET /catalog/categories/dev/registries HTTP/1.1
Host: catalog.example.com
```

The JSON fixture supplies the complete second response. Applying the
literal selector `stage=PRODUCTION` chooses `bridge`, whose label value is
`production`. `website` has no matching label and only a `weburl`.
There is no `filter` or `inline` request and no domain document read.

The redirect example uses an explicitly synthetic, non-secret Authorization
value to make the credential boundary visible. Neither that header nor the
source's conditional validator appears on the destination request.

The `document-revalidation` transcript preserves the document bytes across
conditional retrieval:

```http
GET /services/xreg/documents/main/assets/item/versions/v1 HTTP/1.1
Host: first.example.com
If-None-Match: "document-v1"

HTTP/1.1 304 Not Modified
ETag: "document-v1"
Cache-Control: private, max-age=0
```

The applicable cached `200` response is in the fixture. The `304` is not
an empty replacement document. By contrast, `zero-byte-document` is an
actual `200` with an empty document and `Content-Length: 0`.

## Validation and Later Test Cases

The fixtures use only JSON and can be loaded with Python's standard
library. `tools\http_examples.py` supplies `request_url`, `literal_filter`
and `interpret_transcript` for offline mapping and exchange execution.
The interpreter ignores `expected`, returns actual values and request
traces, and raises the shared `FederationError` on failures. It supports
contiguous range assembly and same-URL cache revalidation, not a complete
HTTP cache. It performs no network I/O.

Use `tools\federation_examples.py` for profile and literal-label selection.
Its `execute_selected` invokes one supplied read function. It does not catch
a failure and try another advertisement. Tests exercise these helpers
against the transcripts and separately assert their outcomes and traces.

The executable OPC UA examples use the same `item` XID, default `v1`,
non-default `v2`, and zero-byte `v3`. Its
[export](../opcua/registry-export.json) also demonstrates local `xref` and
document-local navigation.

| Area | Cases supplied or directly derivable |
| --- | --- |
| Addressing | Root and non-root bases. All entity and collection kinds. Explicit and default Versions. No `$details` on Meta or collections. |
| Views | Metadata versus JSON domain bytes. Metadata-only catalog. Binary and zero-byte documents. Separate model/model source. |
| Selection | No-filter fallback. Ignored filters. Empty/absent labels. Escaped literal `*`. Bracket-quoted key. Literal `null`. Later-page ambiguity. |
| Pagination | Exact next URL. Relative next URL. Incomplete later page. Changing count. Page budget exhaustion. |
| HTTP | Applicable `304` cache reuse. Strong versus weak validators. Complete `200` replacing partial bytes. Truncated content. Distinct metadata/document validators. |
| Trust | External-document `303`. Independent destination credentials. Denied redirect. No silent fallback after `401`/`403`. Cached temporary redirect still subject to policy. |
| Capture | Incompatible Core release. Changing default Version. Lack of Registry-wide atomicity. Colliding XIDs in independent contexts. |

The matrix is an inventory for the dedicated test phase, not a claim that
every derivable mutation already has an executable test.
