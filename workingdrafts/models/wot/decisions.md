# WoT Registry Decision Record

<!-- words: WoT wotid derivedfrom thingdescription thingmodel -->
<!-- words: thingdescriptionid thingmodelid canonicalurl standardsbody -->
<!-- words: openusd href td tm matchversions repointing -->
<!-- words: contentdigest minversion prereleases versionorigin -->

This document records the identity, versioning, lookup and provenance
decisions for the [WoT Registry specification](spec.md) and its
[model](model.json), including the reasoning behind them. This working
document changes with the draft.

## 1. Identity and version are separate values

**Decision.** A `wotid` is the document's authored `id` and MUST NOT change on
a compatible revision. A Thing Model's stable `wotid` includes its major
version, such as `:v2`; it does not encode each minor or patch revision.

**Why.** An identifier that changes with each compatible revision cannot
serve as a stable reference. If every revision gets a new identifier, the
registry cannot group documents that describe the same logical Thing or form
their `ancestor` lineage, and every reference holder has to update its
identifier. Excluding minor and patch versions lets a recipient resolve the
document without parsing a version suffix.

**Example.** A typo is fixed in the lamp `urn:fabrikam:lamp:42`. Its `wotid`
and its `thingdescriptionid` do not change, and the correction becomes a new
Version of the same Resource. A Consumer that wants the correction asks for
the Resource `self` URL; one that wants the earlier text asks for that Version
by name.

**Consequence.** Revising a document leaves `wotid`, `thingdescriptionid` and
`thingmodelid` unchanged and adds a Version.

**Scope.** This rule constrains revisions of an existing identifier. An
author publishing a second, incompatible Thing assigns it a distinct,
permanent `wotid`. A Thing Model's identifier MUST include a major-version
token. See [Decision 6](#6-a-breaking-thing-model-change-uses-a-successor-identifier).

See [Section 1.3](spec.md#13-versioning),
[Section 5.1](spec.md#51-wot-identifiers-and-registry-ids) and
[Section 5.3](spec.md#53-lookup).

## 2. Customer WoT references are preserved, never rewritten

**Decision.** A registry stores a WoT document as supplied and MUST NOT
rewrite its `id`, `links[].href`, `tm:extends` or `tm:ref` values into
registry-specific identifiers.

**Why.** Documents arrive authored and referenced from artifacts the registry
never sees. Rewriting breaks those external references, misrepresents a
standard document in the registry, and assigns different identities to the
same bytes in different registries.

**Example.** A Thing Description extends a Thing Model published elsewhere, by
that model's authored identifier. Repointing the reference at this registry's
own path would make the link easy to follow inside this registry and useless
outside it, because every other WoT tool resolves the reference in the WoT
identifier space.

**Consequence.** The registry's own identity for a document — its Resource id
— lives outside the document, and the identifiers the document itself authored
are carried alongside it, unchanged, in `wotid` and `derivedfrom`. Neither of
those attributes holds an `xid`.

See [Section 5.2](spec.md#52-preserving-customer-documents).

## 3. The Resource id is chosen by the client, not derived by the registry

**Decision.** This specification does not map a `wotid` to a
`thingdescriptionid` or `thingmodelid`. The client creating the Resource
supplies both values. The registry relates them by storing them together,
not by deriving one from the other.

**Why.** A WoT identifier is a URI, while an xRegistry id has a much narrower
grammar. Requiring one construction would add little and reduce portability.
A first-party `wotid` lets a Consumer holding a WoT identifier find the
Resource by querying `wotid`. Hosting environments also differ in the names
they permit; a deployment with tighter id restrictions than xRegistry itself,
such as an ARM-backed registry, would otherwise be unable to conform.

**Example.** A registry that stores `urn:fabrikam:lamp:42` under the Resource
id `lamp-42` is conformant, and so is one that stores it under
`urn.fabrikam.lamp.42`. Both answer `?filter=wotid=urn:fabrikam:lamp:42` with
the same Resource.

**Consequence.** A deployment MAY adopt a derivation convention of its own —
the [OpenUSD Artifact Registry](../openusd/spec.md) working draft defines one
— but it is a local convention, and a Consumer MUST NOT assume an id was
produced by it.

See [Section 5.1](spec.md#51-wot-identifiers-and-registry-ids).

## 4. `wotid` is a REQUIRED, indexed, first-party attribute

**Decision.** `wotid` is REQUIRED on every `thingdescription` and
`thingmodel`, and is defined in the extension model rather than left to an
application-managed label. It SHOULD be indexed so that
`?filter=wotid=<id>` is served without scanning.

**Why.** A resolver cannot depend on an informal label that is not enforced,
validated or indexed. Defining the attribute in the model lets the registry
reject a write with no identity instead of failing to find the document later.

**Open point.** Where a document carries no `id` member, the Producer has to
supply a `wotid`; the registry rejects a write that supplies neither rather
than inventing a value. Whether a future revision ought to define a derivation
for that case is not yet settled.

See [Section 5.3](spec.md#53-lookup).

## 5. Provenance metadata is advisory and does not affect identity

**Decision.** `license`, `publisher`, `standardsbody`, `canonicalurl` and
`maturity` describe where a document came from. They are Version attributes,
carried on each Version alongside the document they describe, and they never
determine whether two documents are the same document.

**Why.** Agents need an explicit basis for preferring an official model over
an obscure one, and inferring it from a title or a naming convention is
guesswork. Keeping the attributes on the Version keeps each stored document
described by the provenance recorded with it; keeping them out of identity
keeps two documents from collapsing into one because they happen to share a
publisher.

**Example.** An agent prefers a Thing Model marked `Standard` by a
`standardsbody` over one marked `Community`. Two documents that share a
`publisher` are still two documents, because identity is `wotid` alone.

**Consequence.** Updating one of these attributes is an ordinary update of a
Version attribute, governed by the Core rules for updating a Version. This
specification grants it no exemption from them.

See [Section 4.6](spec.md#46-provenance-and-selection-metadata).

## 6. A breaking Thing Model change uses a successor identifier

**Decision.** A breaking Thing Model change creates a new Resource under a
new major-version `wotid`. The predecessor retains its Versions and MUST set
`deprecated.alternative` to the successor Resource URL. A Thing Model
identifier MUST carry a major-version token. A breaking TD major revision is a
new Version of the same concrete Thing under its existing `id` and `wotid`.

**Why.** [Decision 1](#1-identity-and-version-are-separate-values) keeps a Thing
Model's major compatibility line in its `wotid`. A breaking TM contract
therefore cannot be published as another Version of that Resource. Thing
Descriptions identify concrete Things instead: a major `version.instance`
marks a breaking revision without changing the Thing's `id` or `wotid`.

The major-version token is the convention the
[Schema Registry](https://xregistry.io/xreg/xregistryspecs/schema-v1/docs/spec.html)
already recommends for `schemaid`, and `deprecated` is how it already links a
superseded schema to its replacement; reusing both keeps a WoT registry
legible to anyone who knows the approved specifications.

**Consequence.** A Consumer holding a stale TM identifier can retrieve the
predecessor and inspect its successor. A TD consumer resolves a major instance
revision under the same Thing identifier.

See [Section 5.1.1](spec.md#511-breaking-changes-and-successor-identifiers).

## 7. Version floors, semantic versions and reproducible resolution

**Decision.** Thing Models and Thing Descriptions use
`versionmode: semver` with `singleversionroot: true`. A TM `versionid` equals
`version.model`; a TD `versionid` equals `version.instance`. Both receive a
server-set `versionorigin`. TD-to-TD floors use `td:minVersion` and cap the
selected version below the next major. The resolver honours a sticky default
only when it satisfies the applicable floor and range, and returns an exact
selection with its origin.

**Why.** The resolver separates a dependency's minimum compatible version
from a caller's request to reproduce a previous selection:

| Choice | Rationale |
|---|---|
| TM floors are uncapped; TD floors are caret-bounded | A TM major is part of its `wotid`; a TD `id` names a concrete Thing, so a TD floor selects within its major. An unfloored TD reference can cross majors. |
| Major in TM identity | Incompatible TM contracts are distinct Resources; a stable reference cannot silently acquire a breaking revision. A TD `id` names one concrete Thing, so its breaking major revision remains under that id. Core `deprecated.alternative` points to a TM successor without redirecting old references. |
| `versionid` follows the document revision | TM identity comes from SemVer `version.model`; TD identity comes from SemVer `version.instance`. Mismatches are rejected; build metadata cannot fit Core's id grammar. |
| Generated `0.0.0-N`, not `0.0.N` | Generated ids do not collide with authored patch releases. Allocation skips occupied ids, including authored prereleases of the same spelling, and `versionorigin` distinguishes their source. Generated ids are not compatibility promises and cannot be floors. |
| Prereleases excluded by default | A dependency does not silently adopt an unstable or generated revision. A prerelease floor or caller opt-in makes prereleases eligible. There is no fallback for a collection containing only generated Versions. |
| Sticky default honoured only in range | An operator's deliberate selection is authoritative unless the caller supplies an explicit pin. A sticky Version below the floor or in a higher TD major fails rather than selecting a different Version. |
| Pin in output, not document | The tuple `(wotid, versionid, contentdigest, origin)` supports reproducibility without putting registry-specific choices into portable WoT documents. Caller pins deliberately override normal floor selection. |

**Example.** Publishing `1.0.1` after `1.1.0` does not replace the newer
default. A TD derived from model `1.1.0` has that implicit floor when it has
exactly one type link. A TD-to-TD floor of `1.2.0` admits versions below
`2.0.0`; an unfloored TD reference can select a later major. Several type
links with a document-level model version require explicit `tm:minVersion`
on every link.

**Consequence.** Producers preserve the authored document bytes. Operators
migrate compatible legacy roots to one SemVer lineage and separate
incompatible identities before enabling the model. Consumers retain pins
externally and implement the error outcomes and algorithm in
[Section 5.4](spec.md#54-versioned-reference-resolution).

See the informative [versioning design](versioning-design.md) and the
[canonical test vectors](tests/resolution/README.md).
