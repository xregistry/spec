# HTTP Federation Offline Examples

<!-- words: federationerror opc opcua py ua validators website weburl -->
<!-- words: pathlib workingdrafts -->

These examples use synthetic exchanges to exercise the request mapping and
response handling in the [HTTP federation draft](../../../bindings/http-federation.md).
They do not represent captured deployment traffic and run without a server,
credentials, or network access.

## Files

`read-mapping.json` defines a compact model source and fifteen concrete
abstract-request to HTTP-URL mappings. All successful mappings use `GET`.
The model source is interpretation input, not a claim that an effective
`/model` response omits Core's expanded fields. The metadata-only catalog and
document-bearing assets use the same paths as the federation examples.

`transcripts.json` contains named synthetic exchanges. Each `request.url` is
absolute, and `request.headers` contains the complete set of headers relevant
to the example. `response.status` gives the HTTP status, and `response.headers`
contains the significant response headers. When a response has a body, exactly
one of `json`, `text`, or `base64` supplies it. `json` describes metadata
values, not a canonical JSON byte encoding. `text` is UTF-8 without an added
newline. `base64` denotes exact response bytes. Without a body member, the
response has zero body bytes. The `expected` member states the resolver
outcome. It is not a field in an HTTP response.

Collection payloads are metadata maps. No transcript places domain bytes in a
metadata-only catalog entry. Pagination links are opaque. A later page can
make an initially promising selection ambiguous.

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

The JSON fixture supplies the complete second response. The literal selector
`stage=PRODUCTION` selects `bridge`, whose label value is `production`.
`website` has no matching label and provides a `weburl`. The example includes
no `filter` or `inline` request and reads no domain document.

To observe the selection independently of the fixture's `expected` field,
run this Python block from the repository root:

```python
import json
from pathlib import Path
from workingdrafts.bindings.tools.http_examples import interpret_transcript

data = json.loads(Path(
    "workingdrafts/federation/samples/http/transcripts.json"
).read_text())
case = next(t for t in data["transcripts"] if t["name"] == "no-filter-catalog")
result = interpret_transcript(case)
value = result["value"]
print(value["registryid"], result["pages"], len(result["trace"]))
```

```text
bridge 1 2
```

The example makes two requests and receives one complete collection page. It
reads no domain document. The [selection rule](../../spec.md#selectors) says
the resolver has to check every necessary page. The `later-page-ambiguity`
fixture shows how a later page can make an earlier match ambiguous.

The redirect example shows the credential boundary with a synthetic,
non-secret Authorization value. The destination request carries neither
that header nor the source's conditional validator.

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

Executing `document-revalidation` through the same helper returns
`cache_reused: true`, two traced requests, and the cached bytes
`b'{"type":"string"}'`. The
[HTTP consistency rules](../../../bindings/http-federation.md#http-validators-and-partial-content)
define validator scope by representation. This result does not establish a
Registry snapshot.

## Validation and Later Test Cases

Python's standard library can load the JSON fixtures.
[`http_examples.py`](../../../bindings/tools/http_examples.py) provides
`request_url`, `literal_filter`, and `interpret_transcript` for offline mapping
and exchange execution. The interpreter ignores `expected` and returns actual
values and request traces. On failures, it raises the shared `FederationError`.
It assembles contiguous ranges and supports revalidating the cache for the same
URL. It is not a complete HTTP cache and performs no network I/O.

Use [`federation_examples.py`](../../tools/federation_examples.py) for profile
and literal-label selection.
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

Use the matrix to identify scenarios and boundary cases for conformance
checks, not as an exhaustive report of implemented test coverage.
