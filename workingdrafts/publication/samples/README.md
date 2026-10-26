# Publication Examples

<!-- words: cas jsonld py pytest readme workingdrafts -->

These examples check the domain-independent
[publication contract](../spec.md). The authored
[Registry export](registry.json) and [document](intro.txt) are synthetic
inputs. Generated `manifest.json`, `channel.json` and `open.json` bind their
exact bytes. URLs use reserved example domains; checks perform no network IO.

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

The suite checks raw size/digest, schema shape, context equality, document
associations, case-insensitive Resource collisions, missing defaults,
unsupported mandatory extensions, stale head writes, forks, rollback epochs
and non-reused deleted channel identities. Negative graph cases recompute
digests after altering the graph.
The checks therefore have to detect the invalid graph, not just changed
bytes.

The helper accepts this example's self-contained interpreted model only.
It explicitly rejects aliases and is not a full Core graph or domain-closure
validator. The channel helper serializes in-memory operations. Its results do
not establish atomicity, retention or non-reuse across process restarts. Native
binding mapping, HTTP context links and durable server writes need adapter
integration evidence before conformance is claimed.

`publication-package.json` supplies the portable URL-to-local-file map.
The offline reader checks resolved containment and rejects unsafe paths.
This demonstrates byte-bundle replay, not Git or OCI native projection.
