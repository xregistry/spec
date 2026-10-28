# WoT Registry Service - Version 1.0-rc4

<!-- words: WoT readme -->
<!-- words: py pytest workingdrafts -->
<!-- words: workflows -->

This draft defines the [WoT Registry specification][Spec] and its
[model][Model]. The [decision record][Decisions] captures its design
decisions. The informative [versioning design][Versioning] and
[samples][Samples] provide additional context.

The [publication companion][Publication] defines how to bind dependencies and
publish a set. Those workflows use the
[generic publication contract](../../publication/spec.md). That contract covers:
- [manifest integrity][Manifest]
- [channel operations][Channel]
- [export and federation][Export]
- [domain closure][Closure]

The companion's closure schema and checks validate shape. They do not establish
deployed resolver conformance.

The [27 representative vectors](tests/resolution/README.md) test how the
registry assigns versions and resolves references. Some cases test how the
registry applies floors and matches caller pins. Others test how it honors
sticky defaults and selects prerelease versions. Run
`python workingdrafts/models/wot/tests/resolution/check_vectors.py` from the
repository root. Normal pytest runs the same cases with schema validation.
These examples do not provide exhaustive regression coverage.

[Manifest]: ../../publication/spec.md#manifest-and-integrity
[Channel]: ../../publication/spec.md#publishing-and-opening-a-channel
[Export]: ../../publication/spec.md#export-federation-and-binding-equivalence
[Closure]: ../../publication/spec.md#domain-closure-and-compatibility
[Publication]: publication/design.md#wot-channels-snapshots-and-dependency-bindings
[Spec]: spec.md
[Model]: model.json
[Decisions]: decisions.md
[Versioning]: publication/design.md#wot-versioning-design-overview
[Samples]: samples/README.md
