# WoT Versioning: Design Overview

<!-- words: minversion prereleases subthing ua uav versionorigin -->
<!-- words: compatibilityline lockfile marcschier opcfoundation unversioned -->
<!-- words: workflow workflows -->
<!-- words: href namespace opc workaround -->

This is an informative proposal, not an implemented incremental profile.
The [full design](versioning-design.md) defines the mechanisms and all
63 publisher, consumer, administrator, migration, and standardization
workflows. The [publication design](publication-design.md) adds 12 workflows
for individual/set publication, channels, snapshots, export and federation.
The current [specification](spec.md) and
[vectors](tests/resolution/README.md) remain the SemVer baseline.

## Decision and problem

Keep native SemVer behavior and add a separate incremental model profile.
A deployment chooses its profile per endpoint/model, not by interpreting
each document's version string. Both profiles use existing TD and TM
collection names. Supporting both needs separate endpoint/model instances,
not necessarily separate physical servers.

A TM can contain `version.model`; a TD can contain `version.instance`.
Requiring SemVer everywhere makes an ordinary integer or an unchanged
external document difficult to publish and reference. The current generated
`0.0.0-N` fallback is a prerelease label that cannot be a floor. It does not
provide ordinary incremental revision selection.

Separate revision order from compatibility. An incremental registry assigns
integer IDs; a publisher declares which compatibility line a Version belongs
to. A consumer follows a named line and optionally sets a numeric floor.
Exact pins record what it actually selected.

Channels name update streams; immutable snapshots fix complete publication
sets. Compatibility stays separate, and none of these concepts is a Group.
A channel can advance across compatibility lines, but consumers still reject
a selected head that violates their requirements.

## Publication and identity

The routine publisher uploads unchanged bytes and a line declaration.
An editable document can declare root `uav:compatibilityLine`; otherwise
authorized metadata supplies `compatibilityline`. When both exist they
have to agree. A line is an absolute URI, not another registry Resource.

With watermark 41, an unversioned or free-form document receives registry
revision `"42"` and `versionorigin: generated`. A canonical authored
integer can instead supply the ID with origin `authored`, provided it
exceeds historical allocation state. Neither path rewrites the document.

Persist the high-water mark atomically with content, line, and applicable
Core state. Deleting history or restarting does not reset it. Adapters
without durable allocation reject publication rather than approximate it.
Counter exhaustion fails; it never recycles old IDs.

A line-less upload can succeed for raw retrieval and exact pins, but its
publishing diagnostic states that automatic line selection cannot use it.
Line membership, including absence, is fixed at creation. A correction
requires another revision.

Registry revision IDs are scoped to an originating Resource/sequence.
Independent copies with the same authored `id` do not share a numeric floor.
Replicas preserve source identity/numbering or provide explicit mappings.

## Reference vocabulary and selection

Deploy the extensions in the existing namespace
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
requirement. Incremental references derive no implicit requirement from
the referencing document's model/instance version or root line.

For history 42/A, 43/B, 44/A, a line-A reference selects 44. A floor of 45
fails. An unpinned incremental reference without a line fails. A sticky
default of 43/B makes the A reference fail; it does not silently select 44.
Without a sticky default, choose the highest qualifying integer.

Keep SemVer semantics: native ordering and ancestry, target-kind floors,
TD next-major caps, type-link implicit floors, and prerelease eligibility.
The resolver applies those rules only to SemVer targets. Generated integer
IDs are ordinary revisions and valid floors; generated SemVer bookkeeping
IDs retain their current restrictions.

Ordinary retrieval serves Core's default. In the incremental manual profile
that can differ from numeric compatible selection. Consumer examples use
constrained resolution, not raw retrieval as a substitute.

## Compatibility, pins, and operation

A later revision in one line claims compatibility with every earlier one
in that line. A breaking incremental change uses another line; its target
ID can stay the same. Publishers own the claim. Labels and digests do not
prove semantic compatibility or publisher authority.

A consumer stores target, revision, digest, origin, and applicable profile
and line expectations outside authored documents. Replay retrieves the exact
revision/bytes before floor/default selection; a missing pin fails without
an upgrade. A bare digest can identify bytes shared by several revisions
and lines, so it alone does not pin line membership.

Retain records for all transitive dependencies. Refresh explicitly resolves
new candidates for review/activation through existing deployment machinery.
Offline operation also needs trusted metadata for declarations absent from
the bytes. Do not add a new lockfile or signature protocol.

For set publication, reuse the generic xRegistry manifest/channel contract.
Convert a standard or capture a server model revision, reuse unchanged
document Versions, record source release provenance and bind dependencies
exactly. Individual authors use the same flow with one changed document.
Persist a complete snapshot, then conditionally update one channel head.
Fork/promotion/rollback reuse manifests; stale updates fail rather than
overwrite another publisher. Resolve moving sources once for federation.

A WoT closure extension binds each source Version/reference location to an
exact target. Snapshot-bound consumption checks authored compatibility against
that target; it never falls back to live highest-version selection.
Offline replay needs the manifest, trusted metadata, contexts and exact bytes.

After an anonymous upload timeout, use existing request-status facilities
or inspect history for matching bytes and metadata. Looking only at the
highest revision is unsafe under concurrent writers. No match does not prove
failure while a request might still commit. Reconcile or explicitly accept
possible duplicates on retry; no exactly-once guarantee is added.

## Core mapping, adoption, and next gate

The SemVer model stays native. The incremental model uses Core `manual`
ordering with multiple roots permitted; ancestor trees do not define
compatibility or numeric order. Middle deletion therefore needs no custom
single-root repair, though it can make exact pins unavailable.

Migrate into a separately validated endpoint using an offline manifest of
bytes, revisions, lines, counters, defaults, and origin mappings. Preserve
the source for old pins. Cutover/rollback changes routing, never old IDs.

The [WoT proposal][WoT proposal] pursues core-vocabulary standardization.
It is currently on the author's fork, not evidence of W3C adoption.
`uav` deployment does not wait for that process. Readers retain old draft
floor forms, but duplicate old/new floors on one reference fail. Upgrade
readers first; never duplicate composition links as an alias workaround.

The [full design](versioning-design.md#workflow-evidence-index) distinguishes
current SemVer evidence from planned incremental/publication/migration checks.
Actual counter durability, provider trust/context handling, and OPC generated
model changes remain proof gates. The generic publication proposal includes
schemas and synthetic examples; the WoT closure schema checks shape only.
Neither demonstrates deployed closure enforcement or implements the pending
incremental/OPC/.NET changes.

[WoT proposal]: https://github.com/marcschier/wot-thing-description/pull/1
