# Publication Examples

<!-- words: cas jsonld py pytest readme workingdrafts -->
<!-- words: deepcopy hashlib hexdigest pathlib publicationerror viewversion walkthrough -->

Use these examples to check the domain-independent
[publication contract](../spec.md) without network IO. The authored
[Registry export](registry.json) and [document](intro.txt) are synthetic.
Generated `manifest.json`, `channel.json` and `open.json` bind their exact
bytes. All URLs use reserved example domains.

The compact Registry input uses Core document view with a complete
containment/default graph for this example and no external model includes.
It is not an API response containing all server-generated metadata. The
original document bytes are stored separately from the Registry's external
document locator; the in-memory object map supplies them during offline replay.

After changing an authored input, regenerate its descriptors:

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

Negative graph cases recompute digests after altering the graph. The checks
therefore need to detect invalid graph structure even when byte integrity
checks pass.

The helper accepts only this example's self-contained interpreted model and
explicitly rejects aliases. It is not a full Core graph or domain-closure
validator. The channel helper serializes operations in memory, so its results
do not establish atomicity, retention or non-reuse across process restarts.
Before claiming conformance, obtain adapter integration evidence for native
binding mapping, HTTP context links and durable server writes.

For local replay, `publication-package.json` maps URLs to portable local file
paths. The offline reader checks resolved containment and rejects unsafe
paths. This exercises byte-bundle replay, not Git or OCI native projection.

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

The output shows that the reader still verifies the second manifest after
the channel returns to the first. Neither promotion nor rollback creates a
document revision. Removing a captured object from the supplied byte map
causes an explicit failure; the helper does not contact the original URL to
repair the offline read.

The [bundle map](publication-package.json) maps URLs to local files. Under the
[packaging rules](../spec.md#export-federation-and-binding-equivalence), the
reader applies the same check to bytes stored in those files.
