# OCI Snapshot Fixtures

<!-- words: OCI ORAS DAG sha256 jsonschema configs shards sharding -->
<!-- words: artifactType mediaType formatversion modelresolved hasdocument -->
<!-- words: offline-complete ximportresources xref -->
<!-- words: emptygroups federationerror fixturelayout gitattributes opencontainers powershell py standalone workingdrafts -->

These offline fixtures exercise the unreleased
[OCI binding](../../../bindings/oci.md). They are not container images, a
production resolver, an OCI server, or evidence of universal client support.

`layout` is a standard OCI image layout containing two separately selected
Registry roots. [expected.json](expected.json) records their exact digests
and document bytes. All REQUIRED containment uses OCI index `manifests`
and manifest `config`/`layers` descriptors. `.gitattributes` disables text
conversion for content-addressed blobs, including JSON and empty blobs.

| Reference | Registry ID | Class | Closure |
| --- | --- | --- | --- |
| `offline` | `fixture-offline` | `offline-complete` | 99 objects |
| `linked` | `fixture-linked` | `linked` | 98 objects |

Each root has 44 indexes, 25 manifests and 25 entity configs. The offline
root has four document blobs. The linked root has three and one external
document URL. Both include the OCI two-byte empty-layer placeholder.
The roots share unchanged content but are independent contexts with
colliding XIDs. Neither root depends on the other root.

The generic `dirs` / `files` vocabulary comes from the
[Core example](../../../../core/sample-model.json). JSON Schema documents
are ordinary domain bytes, not a newly invented document format. `notes`
is a metadata-only Resource type. `imports` imports the same `files`
model type using `ximportresources`. `emptygroups` has no instances.
The complete model, original compact model source and include-resolved
compact source are present in the Registry config.

## Fixture Inventory

| XID under the offline Registry | Purpose |
| --- | --- |
| `/dirs/main/files/sample` | Two Versions, explicitly defaulting to older `v1` |
| `/dirs/main/files/sample/versions/v1` | `{"type":"string"}` plus one LF. Labels and nested extension data |
| `/dirs/main/files/sample/versions/v2` | `{"type":"number"}` plus one LF. Independent Version read |
| `/dirs/main/files/binary` | Seven exact bytes: `00 01 7f 80 ff 0d 0a` |
| `/dirs/main/files/empty` | Zero bytes, not the two-byte OCI placeholder |
| `/dirs/main/notes/info` | `hasdocument: false`, with Version metadata |
| `/dirs/main/files/alias` | One-hop local reference to `sample` |
| `/imports/shared/files/alias` | Valid same-type reference across Group model types |
| `/dirs/main/files/dangling` | Target Group instance does not exist |
| `/dirs/main/files/chain` | Target is itself an alias. No transitive expansion |
| `/dirs/empty/files` | Empty Resource collection |
| `/emptygroups` | Empty Group collection |

The linked Registry changes the `v2` document to an uncaptured URL,
`https://documents.example.org/sample-v2.json`. The fixture helper never
fetches it. Default `v1` remains embedded.

Routing pages were deliberately built with `page_size=2`. This creates
multi-level range shards even in a small example. Entity indexes still
have their fixed two or three control descriptors. `page_size` is not a
different normative entity-index limit. Every index remains below both
256 descriptors and 1,048,576 bytes.

## Executable Helper

Run from the repository root with Python and the existing `jsonschema`
dependency in `tools\requirements.txt`:

```powershell
python -B tools\oci_examples.py validate workingdrafts\federation\samples\oci\layout --reference offline
python -B tools\oci_examples.py validate workingdrafts\federation\samples\oci\layout --reference linked
python -B tools\oci_examples.py lookup workingdrafts\federation\samples\oci\layout /dirs/main/files/sample/versions/v2 --reference offline --operation document --trace trace.json
python -B tools\oci_examples.py lookup workingdrafts\federation\samples\oci\layout /dirs/main/files/sample/meta --reference offline
python -B tools\oci_examples.py lookup workingdrafts\federation\samples\oci\layout /dirs --reference offline --operation collection --label empty --value ""
```

Without a reference, this layout produces `ambiguous`. Native
advertisements always supply `parameters.reference`. A helper error is
JSON on standard error with a shared error code and a nonzero exit status.
`--trace` saves observed file reads even on failure. It does not simulate
successful HTTP traffic. `route` distinguishes a Distribution manifest
route from a blob route, although the files all reside in the layout.

`validate` walks the entire closure, including document bytes.
`--inventory <path>` saves the actually verified descriptors. `lookup`
reads only what its operation needs. A Version document request does not
fetch other Version payloads. Collection label selection visits all
necessary pages and detects ambiguity, including on a later page.

Metadata results contain `value`, the standalone Core document-view JSON,
and `pointer`, a JSON Pointer selecting the requested entity within
`value`. Pointers in the Core metadata are relative to `value`, not the
fixture CLI's reporting envelope. A standalone Meta request returns its
owning Resource document with `pointer: "/meta"`, so its default Version
navigation has a real in-document target. No synthetic absolute `self`
URL is invented.

Python document results contain raw `data: bytes`, `mediaType`, the
original `target`, and the actual `resolved` Version XID. The CLI
substitutes `base64` and `size` for `data`. `snapshot` is always the pinned
root digest, not a Resource Version ID. Metadata operations on an alias
do not project target metadata. Domain-document operations follow at
most one same-type local hop.

### Python interfaces

The module is [`tools/oci_examples.py`](../../../../tools/oci_examples.py).
It imports only the frozen shared helpers `FederationError`,
`select_label`, `validate_profile`, and `validate_xid`.

```python
build_layout(
    path, records, documents=None, *,
    reference="snapshot", page_size=256, max_index_bytes=1048576
)  # -> OCI root descriptor

FixtureLayout(
    path, reference=None, *,
    trace=None, max_depth=64, max_objects=100000
)
reader.root_digest            # pinned SHA-256 string
reader.root_descriptor        # selected OCI descriptor
reader.inventory              # list of actually fetched descriptors
reader.fetch(descriptor)      # -> verified bytes
reader.validate()             # -> closure summary
reader.lookup(
    target, *, operation="entity", selector=None
)                            # -> result dictionary

validate_layout(path, reference=None, **limits)  # -> summary
lookup_layout(
    path, target, *, reference=None, operation="entity",
    selector=None, trace=None
)                                             # -> result dictionary
sample_records(*, linked=False)                # -> (records, documents)
check_index(data, *, profile=True)              # -> parsed index
decode_json(data)                              # -> strict JSON value
encode_json(value)                             # -> fixture JSON bytes
sha256_digest(data)                            # -> SHA-256 string
distribution_url(endpoint, reference, *, blob=False)  # no network I/O
```

`records` is a list of objects conforming to
[oci-record.schema.json](../../../bindings/schemas/oci-record.schema.json).
`documents` maps full Version XIDs to raw bytes for precisely the
`embedded` Versions. A missing byte mapping, extra mapping, duplicate
record, dangling default, wrong type-sharing reference or incomplete
parent hierarchy is an explicit error.

The CLI can instead read `--input <path>` with this fixture-only shape:

```json
{
  "records": [],
  "documents": {}
}
```

Here each `documents` value is a base64 string, and `records` needs an
actual Registry plus its entity records for a valid build. This builder
input is not the published OCI format and is never used as hidden
containment. The published graph uses only the binding's descriptors.
The helper validates graph/profile invariants and Core model shapes.
It is not a general domain-document validator or full Core server.

Reproduce the two roots in a scratch directory:

```powershell
python -B tools\oci_examples.py build scratch-layout --sample --reference offline --page-size 2
python -B tools\oci_examples.py build scratch-layout --sample --linked --reference linked --page-size 2
```

The builder writes bottom-up, then atomically replaces the layout entry
point, preserving other tags and blobs. A later build can move a tag, but
an already constructed `FixtureLayout` keeps its original root pin.
The fixture's sorted, indented JSON is a producer choice, not a global
semantic digest definition.

## Standard Artifact Copy

The actual interoperability exercise uses ORAS **1.3.0** and both standard
layout modes, without `--recursive`, a server or any remote publication:

```powershell
oras cp --from-oci-layout --to-oci-layout workingdrafts\federation\samples\oci\layout:offline copied-layout:copied
python -B tools\oci_examples.py validate copied-layout --reference copied --inventory copied-inventory.json
```

This command was executed during implementation. The selected root
digest and all 99 REQUIRED objects were preserved byte-for-byte,
including configs, range shards, empty collections, binary bytes and the
zero-byte document. The linked Registry root was not selected or copied.
Environment-specific command logs, release-checksum verification and
the independently compared closure inventory are retained in the
implementation session, not represented by a fabricated passing test.

ORAS also placed auxiliary descriptors for copied internal indexes and
manifests in the destination layout's `index.json`: 69 entries in this
exercise, of which exactly one is an eligible Registry root. That mutable
entry-point index is not the selected Registry index, which still has
two descriptors and the same digest. Consumers MUST NOT mistake the
auxiliary entries for additional Registry snapshots. Large copy jobs
also need to check the destination entry-point bounds. This small
exercise does not establish every tool's behavior at every scale.

All stored index and manifest objects were additionally validated with
the unmodified, pinned [OCI Image v1.1.1 schemas][oci-schemas], using
their declared Draft 4 validator, alongside the profile schemas and
the Core model schema. JSON Schema validation does not replace
descriptor hashing or the full graph walk.

## Edge Cases for Conformance Checks

Positive and negative probes for later automated suites include:

- Exact 256/257 descriptor and 1,048,576/1,048,577 encoded-byte boundaries,
  with control descriptors included and byte-driven splitting below 256.
- Multiple shard levels, inclusive lower and exclusive upper boundaries,
  strict case-sensitive keys, empty collections, gaps, overlaps,
  duplicates, missing shards, impossible entry budgets and traversal limits.
- Multiple roots, duplicate tags, explicit digest selection, immutable
  pins across moving tags and reuse of unchanged subtrees without replay.
- Standard OCI object shapes, wrong artifact/media types or roles,
  unsupported profile/Core versions, bad UTF-8, duplicate JSON keys,
  non-finite numbers, wrong hashes/sizes and missing descendant blobs.
- Version/default/Meta consistency, model-source preservation, resolved
  includes, imported versus structurally similar Resource types,
  one-hop aliases, dangling targets and alias-of-alias behavior.
- Case-insensitive literal label values, missing and empty labels,
  ambiguity discovered on later shards, and no implicit normalization.
- Core document-view pointers, including escaped `~` in IDs, retained
  nested extensions, no default Version projection, and Meta context.
- Separate metadata-only, zero-byte, binary and external-only document
  states. Rejection of absent document-capable content and false
  offline-complete claims. Selective fetch traces.
- Actual artifact-aware layout copying and byte-level closure comparison,
  without requiring OPTIONAL referrer traversal.

[oci-schemas]: https://github.com/opencontainers/image-spec/tree/v1.1.1/schema
