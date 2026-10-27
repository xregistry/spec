# Federation Conformance Examples

<!-- words: opcua py pytest readme workingdrafts -->
<!-- words: ua walkthrough -->

These examples check the read and selection rules in the unreleased
[federation specification](../spec.md). All inputs are synthetic and run
offline. They contain no credentials or production endpoints.

| Path | Purpose |
| --- | --- |
| [selection.json](selection.json) | Abstract requests, colliding XIDs in independent contexts, labels, explicit defaults and local alias cases. |
| [document-tree](../../bindings/samples/mapping) | Shared portable records and exact content used by Git and File. |
| [oci](oci) | Standard OCI descriptor graph with independently retrievable content. |
| [http](./http/README.md) | HTTP request/response and consistency examples. |
| [opcua](opcua) | Native addressing and transfer examples. |
| [Registry samples](../../models/registry/samples) | Base catalog and richer binding advertisements. |
| [Source selection](../tools/federation_resolution_examples.py) | Local Resource shadows and ordered source misses, using in-memory reads. |

The source-selection helper's `Source` accepts the selected view's enabled
capabilities. With `{"federation":{"resolution":"producer"}}`, the helper
reads the requested operation from that view without consulting the source
list. With no signal or an explicit `consumer`, it checks the local view
before configured sources. A failed read does not change the resolution owner.

The `registry` object in `selection.json` is a reduced logical test vector,
not a complete serialized Core API response. It omits server-generated
metadata. That omission does not authorize an API to omit the same metadata.
The binding formats define their complete record representations separately.

Use these examples to inspect concrete read outcomes:

- [HTTP selection and cache sequence](http/README.md#concrete-read-sequences)
- [OCI selective lookup](oci/README.md#executable-helper)
- [UA reference remapping](opcua/README.md#reference-and-root-mapping)

The helpers produced these results offline. They do not represent deployed
protocol traffic. The
[publication walkthrough](../../publication/samples/README.md#promotion-rollback-and-an-already-open-reader)
shows how a reader can continue using its selected manifest while the channel
moves.

Run the conformance suite from the repository root:

```console
python -B -m pytest workingdrafts -q
```

Each draft bundle keeps its helpers and tests in a sibling `tools` directory.
The [shared helpers](../tools) and [binding helpers](../../bindings/tools)
exercise specified algorithms without implementing a production client or
server. Tests construct negative cases in memory or temporary directories.
Checked-in positive JSON examples have unique keys. Check byte integrity,
selected Version identity, full graph closure and selective fetch traces
independently. A passing assertion for one does not
establish the others.

OCI copying uses artifact-aware tooling and the format's standard containment
edges. A parser accepting JSON does not show that an implementation can copy
the whole graph.
The [OCI binding](../../bindings/oci.md) defines the interoperability boundary
and local copy procedure.
