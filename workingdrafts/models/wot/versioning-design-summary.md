# WoT Versioning: Design Overview

<!-- words: minversion prereleases subthing ua uav versionorigin -->
<!-- words: compatibilityline lockfile marcschier opcfoundation unversioned -->
<!-- words: workflow workflows -->
<!-- words: href namespace opc workaround -->

This document proposes an incremental profile. No implementation exists yet.
The [full design](versioning-design.md) defines the mechanisms and catalogs
63 workflows. Its [D7 selection flow][D7] describes defaults and exact pins.
The [publication design](publication-design.md) adds 12 workflows. They cover:

- Editing individual documents and publishing sets
- Managing channels and snapshots
- Exporting manifests and federating sources

The existing [specification](spec.md) defines SemVer rules. The
[vectors](tests/resolution/README.md) exercise that baseline.

## Decision and problem

Keep native SemVer behavior and add an incremental profile. During
provisioning, an operator assigns it to each endpoint/model. The registry
does not infer it from an individual document's version string. Both profiles
use the existing TD and TM collection names. To support both, the operator
provisions separate endpoint/model instances. The instances can share a
physical server.

A TM can contain `version.model`; a TD can contain `version.instance`.
Requiring SemVer everywhere makes an ordinary integer or an unchanged
external document difficult to publish and reference. The current generated
`0.0.0-N` fallback is a prerelease label that cannot be a floor. It does not
provide ordinary incremental revision selection.

The registry assigns integer revision IDs. A publisher declares each
Version's compatibility line. A consumer follows a named line and can set a
numeric floor. The resolver returns an exact pin for repeatable use.

Channels name update streams, while immutable snapshots fix complete
publication sets. Neither is a Group, and neither determines compatibility.
A channel can advance across compatibility lines; consumers still reject a
head that violates their requirements.

## Publication and identity

The publisher uploads unchanged bytes and declares a line. An editable
document can carry root `uav:compatibilityLine`; otherwise authorized
metadata supplies `compatibilityline`. Publication rejects conflicting
declarations.
A line is an absolute URI, not another registry Resource.

With watermark 41, an unversioned or free-form document receives registry
revision `"42"` and `versionorigin: generated`. A canonical authored integer
can supply the ID only when it exceeds the allocation watermark. Publication
then sets `versionorigin` to `authored`. Neither path rewrites the document.

The publication owner commits the high-water mark with content, line, and
applicable Core state. Deleting history or restarting does not reset it.
Adapters without durable allocation state reject publication rather than
approximate it.
Counter exhaustion fails; publication never recycles old IDs.

A line-less upload remains available for raw retrieval and exact pins, but
cannot participate in automatic line selection. The publishing diagnostic
reports that limitation. Each revision keeps the line declared at creation,
including no line. To add or change a line later, publish another revision.

Each revision ID belongs to one originating Resource and sequence.
Independent copies with the same authored `id` do not share a numeric floor.
Replicas preserve source identity and numbering or provide explicit mappings.

## Reference vocabulary and selection

The proposal places the extensions in the existing namespace
`http://opcfoundation.org/UA/WoT-Binding/`:

```json
{
  "rel": "td:extends",
  "href": "urn:example:pump:base",
  "uav:compatibilityLine": "urn:example:pump:control-a",
  "uav:minVersion": "42"
}
```

This excerpt assumes the appropriate composition and extension contexts.
The same versioning members work for TM targets. Existing operators identify
the target kind. A line alone is enough; add a floor only for a feature
requirement. When resolving an incremental target, the resolver derives no
floor from the referring document's model/instance version or root line.

For history 42/A, 43/B, 44/A, a line-A reference selects 44. A floor of 45
fails. An unpinned incremental reference without a line fails. A sticky
default of 43/B makes the A reference fail; it does not silently select 44.
Without a sticky default, choose the highest qualifying integer.

For SemVer targets, the resolver keeps the existing rules:

- Native ordering and ancestry
- Target-kind floors, including TD next-major caps
- Implicit floors for type links
- The resolver requires opt-in or an effective floor for prereleases

The resolver applies those rules only to SemVer targets. Generated integer
IDs are ordinary revisions and valid floors. The SemVer profile's generated
`0.0.0-N` IDs remain prereleases and cannot serve as floors.

Ordinary retrieval serves Core's default. In the incremental manual profile
that can differ from numeric compatible selection. Consumer examples use
constrained resolution, not raw retrieval as a substitute.

## Compatibility, pins, and operation

A publisher claims that each later revision is compatible with every earlier
revision in the same line. A breaking incremental change uses another line.
Its target ID can stay the same. Labels and digests do not prove semantic
compatibility or publisher authority.

A consumer keeps these values outside the authored document:

- Target, Version ID, digest, and origin
- Applicable profile and line expectations

During replay, the consumer retrieves the exact revision and bytes before
floor/default selection. A missing pin fails without an upgrade. A bare
digest can identify bytes shared by several revisions and lines, so it alone
does not pin line membership.

The consumer retains records for all transitive dependencies. To refresh, it
resolves new candidates for review or activation through existing deployment
machinery. Offline operation also needs trusted metadata for declarations
absent from the bytes. This design adds no lockfile or signature protocol.

For set publication, a publisher follows the generic xRegistry
manifest/channel contract. It can convert a standard or capture a revision
of a server model. It reuses unchanged document Versions and records the
source release as provenance. It binds each dependency to an exact target.
An individual author follows the same flow with one changed document.

The publisher persists a complete snapshot before conditionally updating one
channel head. A fork, promotion, or rollback uses an existing manifest. A
stale update fails rather than overwriting another publisher's work.

During federation, a consumer opens each moving source once and retains its
pin and context.

The extension maps each reference pointer in a source Version to an exact
target Version. During snapshot-bound composition, the resolver checks the
authored requirement against that target. It never falls back to live
highest-version selection.
Offline replay needs the manifest, trusted metadata, contexts and exact bytes.

After an anonymous upload times out, the publisher checks existing
request-status or explicit-ID read facilities when available. Otherwise, it
inspects Version history for matching bytes and metadata. Looking only at the
highest revision is unsafe under concurrent writers. No match does not prove
failure while a request might still commit. The publisher reconciles or
explicitly accepts possible duplicates on retry. Anonymous publication has
no exactly-once guarantee.

## Core mapping, adoption, and next gate

The SemVer model remains native. The incremental model uses Core `manual`
ordering and permits multiple roots. Ancestor trees define neither
compatibility nor numeric order. Deleting a middle ancestor needs no
single-root repair, but can make exact pins unavailable.

Migration uses a separately validated endpoint and an offline manifest. The
manifest records:

- Bytes and revisions
- Lines and counters
- Defaults and origin mappings

The migration preserves the source so old pins remain usable. Cutover or
rollback changes routing, not history or revision IDs.

The author hosts the [core-vocabulary proposal][WoT proposal] on a fork.
It does not establish W3C adoption. Deployments can use `uav` before
that process finishes. Readers retain floor forms from earlier drafts during
migration. A reader rejects both old and new floors
on one reference. Upgrade readers before removing old forms; do not duplicate
composition links as an alias workaround.

The [evidence index](versioning-design.md#workflow-evidence-index) in the full
design separates current SemVer checks from planned incremental, publication,
and migration checks.

### Implementation proof gates

- The WoT publisher preserves durable allocation.
- The provider supplies trusted candidate metadata.
- The generic publication adapter preserves checked context and binding
  equivalence.
- The OPC UA generator preserves append-only NodeIds.

The generic publication proposal includes schemas and synthetic examples.
The schema validates only the closure descriptor's shape. Neither
the examples nor the schema demonstrate deployed closure enforcement. This
document does not implement incremental-profile enforcement or regenerate
OPC UA outputs. It does not change either .NET runtime.

[WoT proposal]: https://github.com/marcschier/wot-thing-description/pull/1
[D7]: versioning-design.md#d7-selection-defaults-and-exact-pins
