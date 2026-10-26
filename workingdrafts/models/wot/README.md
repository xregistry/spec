# WoT Registry Service - Version 1.0-rc4

<!-- words: WoT readme -->
<!-- words: py workingdrafts -->
<!-- words: workflows -->

See the [WoT Registry specification](spec.md), its [model](model.json), its
[decision record](decisions.md), the informative
[versioning design](versioning-design.md), and the
[samples](samples/README.md).

The [publication companion](publication-design.md) describes dependency
bindings and set-publication workflows over the
[generic publication contract](../../publication/spec.md). Its closure
schema and checks establish shape, not deployed resolver conformance.

The [canonical resolution vectors](tests/resolution/README.md) cover version
assignment, floors, caller pins, sticky defaults and prerelease selection. Run
`python workingdrafts/models/wot/tests/resolution/check_vectors.py` from the
repository root.
