# Federation Example Source

<!-- words: dockerfile exampleformat jsonschema opc oras powershell py pytest -->
<!-- words: reparse resolvedmodelsource symlink ua walkthrough wot -->

The federation and binding examples share the Registry content in
[`examples.json`](examples.json). The
[generator](../tools/generate_examples.py) produces File, Git and OCI
representations from that source. The
[HTTP](../../bindings/tools/test_http_examples.py) and
[OPC UA](../../bindings/tools/test_opcua_examples.py) binding tests supply
synthetic protocol exchanges and expected outcomes. The generator does not
start servers for those bindings.

The [deployment profile examples](../design/design.md#deployment-operations-by-transport) show one
chunk append over HTTPS, OPC UA, and MQTT. The
[offline deployment cases](../tools/test_deployment_examples.py) also cover
conditional creation and replacement, lost responses, and a pinned
Publication source. They use a reduced in-memory receiver, not a live
deployment service.

See the [Federation specification](../spec.md) for the read contract.

## Generating and Reading Examples

Select a named example to generate a File mapping, a local Git repository,
or a native OCI artifact. Each example supports all three formats. A name
selects example content, not a Registry ID or revision pin.

| Example | Content |
| --- | --- |
| `walkthrough` | One `widget` Resource and its exact 18-byte document, using the project paths in the [mapping walkthrough](../../bindings/mapping.md#worked-example-map-one-existing-file). |
| `portable` | Typed collections, explicit defaults, local aliases, a metadata-only catalog, binary content, and an empty document. |
| `offline` | Complete `dirs` / `files` Registry with imported types, aliases, and locally captured documents. |
| `linked` | A separate Registry context whose non-default `v2` document remains an external URL. |
| `first` | The Registry used in the HTTP and OPC UA examples, with default `v1`, explicit Versions, and metadata-only catalog entries. |
| `second` | An independent Registry with a colliding asset XID and different bytes. |

Run commands from the repository root with Python 3.10 or later and
`jsonschema` from [tools/requirements.txt](../../../tools/requirements.txt).
Git is needed for Git output. ORAS 1.3.0 is needed only for explicit OCI
copying or publication. Validate all named examples without writing output:

```console
python -B -m workingdrafts.federation.tools.generate_examples validate
```

Use a new or empty output directory outside the checkout. The generator
rejects nonempty destinations, filesystem roots, and symlink or reparse
escapes rather than overwriting an existing project.

```powershell
python -B -m workingdrafts.federation.tools.generate_examples file --example walkthrough --output D:\temp\xregistry-file
python -B -m workingdrafts.federation.tools.generate_examples git --example walkthrough --output D:\temp\xregistry-git
python -B -m workingdrafts.federation.tools.generate_examples oci --example offline --output D:\temp\xregistry-oci --reference offline --page-size 2
```

On Linux, substitute absolute output paths outside the checkout, for example
`$HOME/xregistry-examples/file`, `$HOME/xregistry-examples/git`, and
`$HOME/xregistry-examples/oci`.

Each command reports its generated root and a `pin` field as JSON. For File,
the pin is the captured root record's SHA-256, not a guarantee of filesystem
immutability. Git reports a commit ID and OCI reports the root digest. Git
output is a bare repository containing the mapping under `xregistry`, with
a deterministic commit at `refs/heads/main` and an annotated tag at
`refs/tags/snapshot`. It has no remote and is not pushed.
OCI defaults to `--reference snapshot` and `--page-size 256`. The smaller
page size above controls the index layout
of the sharded fixture, not a read limit. Compare the pin with the
[expected OCI digest](../../bindings/oci.md#example-inventory-and-pins).

File and Git store records and indexes separately by default. Use `--inline`
to embed them in `registry.json`. The `walkthrough` example always uses its
inline project layout. OCI does not accept `--inline`.

Read the generated outputs with the binding helpers:

```powershell
python -B -m workingdrafts.bindings.tools.mapping_examples entity D:\temp\xregistry-file /documents/main/assets/widget/versions/v1
python -B -m workingdrafts.bindings.tools.mapping_examples document --git-dir D:\temp\xregistry-git --revision refs/tags/snapshot --path xregistry --target /documents/main/assets/widget/versions/v1
python -B -m workingdrafts.bindings.tools.oci_examples lookup D:\temp\xregistry-oci /dirs/main/files/sample/versions/v2 --reference offline --operation document
```

Use the corresponding output paths on Linux. The readers distinguish
metadata from document operations. A Git commit or OCI digest does not
replace a Core Version ID. See the
[File](../../bindings/file.md#motivation-and-example),
[Git](../../bindings/git.md#conformance), and
[OCI](../../bindings/oci.md#generate-and-read-a-layout) examples for full
validation and selective reads.

OCI publication is opt-in. Add
`--push registry.example.org/team/catalog:example` to copy the generated
descriptor graph to that destination. The
[publication procedure](../../bindings/oci.md#publish-or-retry-an-oci-artifact)
covers login, direct `oras cp`, retries, and digest-pinned retrieval. No
Dockerfile or container-image tar wrapper is involved.

### Example Source Format

The input has `exampleformat: 1` and an `examples` map. Each example contains
neutral `records` with `kind` and `entity`, a `snapshot` class (`linked` or
`offline-complete`), an optional `resolvedmodelsource`, and `documents`
keyed by full Version XID. Each document declares exactly one of `text`,
`base64`, `url`, or `none: true` for a metadata-only Version. Only captured
`text` or `base64` documents can include `origin` or `base`, both absolute
URIs when supplied. The generator writes `text` as UTF-8 without adding a
newline, preserves binary and empty bytes supplied as `base64`, and retains
`url` without retrieving it. Use `--input PATH` to supply another source
document. This is example input, not an interchange format. See the
[input checks](../tools/federation_examples.py).

### Offline Checks

Run the binding, Federation, and WoT example tests from the repository root:

```console
python -B -m pytest workingdrafts/bindings/tools workingdrafts/federation/tools workingdrafts/models/wot/tests -q
```

The [generator tests](../tools/test_generate_examples.py) check representative
outputs, not every example and binding pair. The
[selection tests](../tools/test_spec_examples.py) check local shadows and
ordered source misses. The tests distinguish selected Version identity,
document bytes, graph validation, and selective fetch traces. They do not
exercise deployed services. For an example in which a channel advances
while a reader stays pinned, see the
[Publication walkthrough](../../publication/samples/README.md#promotion-rollback-and-an-already-open-reader).
