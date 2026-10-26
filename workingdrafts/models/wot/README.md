# WoT Registry Service - Version 1.0-rc4

<!-- words: WoT readme -->
<!-- words: py workingdrafts -->
<!-- words: workflows -->

This draft defines the [WoT Registry specification](spec.md) and its
[model](model.json). The [decision record](decisions.md) captures its design
decisions; the informative [versioning design](versioning-design.md) and
[samples](samples/README.md) provide additional context.

The [publication companion](publication-design.md) defines dependency
bindings and set-publication workflows that use the
[generic publication contract](../../publication/spec.md), including
[manifest integrity][Manifest], [channel operations][Channel],
[export and federation][Export], and [domain closure][Closure].
Its closure schema and checks validate shape; they do not establish deployed
resolver conformance.

The [canonical resolution vectors](tests/resolution/README.md) exercise
version assignment, floors, caller pins, sticky defaults and prerelease
selection. Run
`python workingdrafts/models/wot/tests/resolution/check_vectors.py` from the
repository root.

[Manifest]: ../../publication/spec.md#manifest-and-integrity
[Channel]: ../../publication/spec.md#publishing-and-opening-a-channel
[Export]: ../../publication/spec.md#export-federation-and-binding-equivalence
[Closure]: ../../publication/spec.md#domain-closure-and-compatibility
