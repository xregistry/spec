# Publication Examples

<!-- words: cas jsonld py pytest readme workingdrafts -->
<!-- words: deepcopy hashlib hexdigest pathlib publicationerror viewversion walkthrough -->

These examples check the domain-independent
[publication contract](../spec.md). The authored
[Registry export](registry.json) is synthetic. The [document](intro.txt) is
synthetic too. Generated `manifest.json`, `channel.json` and `open.json` bind
their exact bytes. URLs use reserved example domains; checks perform no network IO.

The Registry is a compact Core document-view input, not an API response with
all server-generated metadata. It has a complete containment/default graph
for this example and no external model includes. Original document bytes are
separate from the Registry's external document locator. The in-memory object
map supplies those bytes for offline replay.

Regenerate descriptors after changing an authored input:

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
- Stale head writes and forks
- Rollback epochs and non-reused deleted channel identities

Negative graph cases recompute digests after altering the graph.
The checks therefore have to detect the invalid graph, not just changed
bytes.

The helper accepts this example's self-contained interpreted model only.
It explicitly rejects aliases and is not a full Core graph or domain-closure
validator. The channel helper serializes in-memory operations. Its results do
not establish atomicity, retention, or non-reuse across process restarts. A
conformance claim requires evidence from adapter integration. That evidence
must cover native binding mapping, HTTP context links, and durable server writes.

`publication-package.json` supplies the portable map from URLs to local files.
The offline reader checks resolved containment and rejects unsafe paths.
This demonstrates byte-bundle replay, not Git or OCI native projection.

## Promotion, Rollback and an Already-Open Reader

Run this Python walkthrough from the repository root with the same
dependencies as the checks above. The second manifest adds preparation
history but reuses the first manifest's document Version and bytes.
The in-memory helper starts epochs at one and increments by one; the
[publication contract](../spec.md#publishing-and-opening-a-channel)
requires increasing epochs, not that particular increment.

```python
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from workingdrafts.publication.tools.publication_examples import (
    Channels, PublicationError, check_snapshot, open_package,
)

p = Path("workingdrafts/publication/samples")
context = json.loads((p / "open.json").read_text())
objects = {
    "https://content.example.test/" + name: (p / name).read_bytes()
    for name in ("manifest.json", "registry.json", "intro.txt")
}
first = context["snapshot"]
next_manifest = json.loads(objects[first["url"]])
next_manifest["parent"] = first
raw = (json.dumps(next_manifest, indent=2) + "\n").encode()
second = {
    "url": "https://content.example.test/next.json",
    "digest": "sha256:" + hashlib.sha256(raw).hexdigest(),
    "size": len(raw),
}
objects[second["url"]] = raw
channels = Channels()
channels.create("stable", context["scope"], first, objects)
channels.move("stable", 1, second, objects)
record = channels.records["stable"]
reader = deepcopy(record["head"])
try:
    channels.move("stable", 1, first, objects)
except PublicationError as error:
    print("stale update:", error.code)
channels.move("stable", 2, first, objects)
record = channels.records["stable"]
print("rollback epoch:", record["epoch"])
print("reader still on second:", reader == second)
manifest = check_snapshot(reader, objects)
document, = manifest["documents"]
print("selected Version:", document["viewVersion"])
print("offline package:", open_package(p)["completeness"])
missing = dict(objects)
del missing["https://content.example.test/intro.txt"]
try:
    check_snapshot(reader, missing)
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

The reader still verifies the second manifest after the channel returns
to the first. Neither promotion nor rollback creates a document revision.
The helper fails explicitly when a captured object is missing from the
supplied byte map. It never uses the original URL to repair the offline read.
The [bundle map](publication-package.json) maps URLs to local files. The
[packaging rules](../spec.md#export-federation-and-binding-equivalence) apply
the same check when the bytes reside in local files.
