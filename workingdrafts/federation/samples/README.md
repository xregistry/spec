# Federation Conformance Examples

<!-- words: opcua py pytest readme -->

These examples accompany the unreleased
[federation specification](../spec.md). They are synthetic, offline inputs,
not credentials or production endpoints.

| Path | Purpose |
| --- | --- |
| [selection.json](selection.json) | Abstract requests, colliding XIDs in independent contexts, labels, explicit defaults and local alias cases. |
| [document-tree](../../bindings/samples/mapping) | Shared portable records and exact content used by Git and File. |
| [oci](oci) | Standard OCI descriptor graph with independently retrievable content. |
| [http](./http/README.md) | HTTP request/response and consistency examples. |
| [opcua](opcua) | Native addressing and transfer examples. |
| [Registry samples](../../models/registry/samples) | Base catalog and richer binding advertisements. |
| [Source selection](../../../tools/federation_resolution_examples.py) | Local Resource shadows and ordered source misses, using in-memory reads. |

The source-selection helper's `Source` accepts the selected view's enabled
capabilities. With `{"federation":{"resolution":"producer"}}`, it calls the
view's requested read directly and does not consult the source list.
With no signal, or explicit `consumer`, it performs local-first resolution.
Read failures remain failures rather than triggering a different owner mode.

The `registry` object in `selection.json` is a reduced logical test vector,
not a complete serialized Core API response. In particular, omission of
server-generated metadata there is not permission to omit it from an API.
The binding formats define their complete record representations separately.

Run the conformance suite from the repository root:

```console
python -m pytest tools/test_registry_model.py tools/test_federation_examples.py tools/test_federation_resolution_examples.py tools/test_mapping_examples.py tools/test_git_examples.py tools/test_oci_examples.py tools/test_http_examples.py tools/test_opcua_examples.py -q
```

The helper modules under `tools` exercise specified algorithms without
implementing a production client or server. Tests construct negative cases
in memory or temporary directories. Checked-in positive JSON examples have
unique keys. Byte integrity, selected Version identity, full graph closure
and selective fetch traces are different assertions.

OCI copying uses artifact-aware tooling and the format's standard containment
edges. A parser accepting JSON is not evidence of whole-graph copy support.
The [OCI binding](../../bindings/oci.md) defines the interoperability boundary
and local copy procedure.
