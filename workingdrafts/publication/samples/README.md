# Publication Examples

<!-- words: cas jsonld py pytest readme workingdrafts -->
<!-- words: deepcopy hashlib hexdigest pathlib publicationerror viewversion walkthrough -->
<!-- words: opcua versiondocuments -->

Use these examples to check the domain-independent
[publication contract](../spec.md) without network IO. The authored
[Registry export](registry.json) and [document](intro.txt) are synthetic.
Generated `manifest.json`, `channel.json` and `open.json` bind their exact
bytes. The `opcua-` examples select native UA access instead of HTTP. All
endpoints use reserved example domains.

In a deployed publication, the publisher stores captured Registry JSON and
document bytes as xRegistry Version documents, constructs and stores the
manifest as the snapshot's `manifest` Version, then conditionally updates
the channel. Every descriptor selects an exact Version through a Registry
binding. The specification's
[storage boundary](../spec.md#storage-boundary) and
[publishing sequence](../spec.md#publishing-a-snapshot) explain those
responsibilities and the Registry's implementation-specific backing
storage.

Here, the checked-in files supply the captured content, and the sample
builder generates the manifest and selection records locally. It does not
upload them or start a Registry server. `VersionDocuments` associates exact
Version references with local bytes; its `read` method stands in for the
binding's document operation. HTTP and UA references select separate example
access contexts. The same bytes do not establish that real endpoints expose
equivalent Registries.

The compact Registry input uses Core document view with a complete
containment/default graph for this example and no external model includes.
It is not an API response containing all server-generated metadata. The
original document bytes are stored separately from the captured metadata.
The manifest associates them with an exact view Version. A Registry JSON
Version document is not a request to export changing live metadata.

After changing an authored input, regenerate its descriptors and the
corresponding JSON examples in the specification:

```console
python workingdrafts/publication/tools/build_samples.py
```

Run checks from the repository root:

```console
python -B -m pytest workingdrafts/publication/tools -q
```

The suite checks:

- Raw size and digest
- Schema shape and context equality
- Document associations
- Case-insensitive Resource collisions
- Missing defaults and unsupported mandatory extensions
- Exact Version dispatch, selected UA roots and unsupported bindings
- Rejection of URL-only descriptors and mutable Git/OCI selectors
- Stale head writes and forks
- Rollback epochs and non-reused deleted channel identities

Negative graph cases recompute digests after altering the graph. The checks
therefore need to detect invalid graph structure even when byte integrity
checks pass.

The helper accepts only this example's self-contained interpreted model and
explicitly rejects aliases. It is not a full Core graph or domain-closure
validator. The channel helper serializes operations in memory, so its results
do not establish atomicity, retention or non-reuse across process restarts.
The document map permits mutation to exercise integrity failures; it is not
an immutable storage implementation.
Before claiming conformance, obtain adapter integration evidence for native
binding mapping, HTTP context links and durable server writes.

For local replay, `publication-package.json` contains `reference`/`path`
entries for the HTTP and UA examples. The offline reader checks resolved
containment, duplicate equivalent references and byte/object limits. It
rejects unsafe paths and never contacts a network endpoint. This exercises
byte-bundle replay, not a network binding, Git or OCI native projection.

## Promotion, Rollback and an Already-Open Reader

Run the following Python walkthrough from the repository root using the same
dependencies as the checks above. It creates a second manifest with
preparation history while reusing the first manifest's document Version and
bytes. The in-memory helper starts epochs at one and increments by one. The
[publication contract](../spec.md#publishing-and-opening-a-channel)
requires increasing epochs, not that particular increment.

```python
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from workingdrafts.publication.tools.publication_examples import (
    Channels, PublicationError, VersionDocuments, check_snapshot, open_package,
)

p = Path("workingdrafts/publication/samples")
context = json.loads((p / "open.json").read_text())
package = json.loads((p / "publication-package.json").read_text())
objects = VersionDocuments()
for entry in package["objects"]:
    objects.put(entry["reference"], (p / entry["path"]).read_bytes())
first = context["snapshot"]
next_manifest = json.loads(objects.read(first["reference"]))
next_manifest["parent"] = first
raw = (json.dumps(next_manifest, indent=2) + "\n").encode()
digest = hashlib.sha256(raw).hexdigest()
second = deepcopy(first)
second_reference = second["reference"]
second_reference["version"] = (
    f"/publications/team/snapshots/{digest}/versions/manifest"
)
second.update(digest="sha256:" + digest, size=len(raw))
objects.put(second["reference"], raw)
channels = Channels()
channels.create("stable", context["scope"], first, objects.read)
channels.move("stable", 1, second, objects.read)
record = channels.records["stable"]
reader = deepcopy(record["head"])
try:
    channels.move("stable", 1, first, objects.read)
except PublicationError as error:
    print("stale update:", error.code)
channels.move("stable", 2, first, objects.read)
record = channels.records["stable"]
print("rollback epoch:", record["epoch"])
print("reader still on second:", reader == second)
manifest = check_snapshot(reader, objects.read)
document, = manifest["documents"]
print("selected Version:", document["viewVersion"])
print("offline package:", open_package(p)["completeness"])
missing = deepcopy(objects)
content = document["content"]
missing.remove(content["reference"])
try:
    check_snapshot(reader, missing.read)
except PublicationError as error:
    print("missing bytes:", error.code)
```

The output is:

```text
stale update: mismatched_epoch
rollback epoch: 3
reader still on second: True
selected Version: /sets/manual/documents/intro/versions/7
offline package: offline-complete
missing bytes: unavailable
```

The output shows that the reader still verifies the second manifest after
the channel returns to the first. Neither promotion nor rollback creates a
document revision. Removing a captured Version document from the supplied
store causes an explicit failure; the helper does not contact another
Registry to repair the offline read.

The [bundle map](publication-package.json) maps Version references to local
files. Under the
[packaging rules](../spec.md#export-federation-and-binding-equivalence), the
reader applies the same check to bytes stored in those files.
