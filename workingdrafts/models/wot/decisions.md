# WoT Registry Decision Record

<!-- words: WoT wotid derivedfrom thingdescription thingmodel -->
<!-- words: thingdescriptionid thingmodelid canonicalurl standardsbody -->
<!-- words: openusd href td tm matchversions repointing -->
<!-- words: contentdigest minversion prereleases versionorigin -->

This document records the identity, versioning, lookup and provenance
decisions behind the [WoT Registry specification](spec.md) and its
[model](model.json), together with the reasoning that led to each one. It is a
working document and changes with the draft.

## 1. Identity and version are separate values

**Decision.** A `wotid` is the document's authored `id` and MUST NOT change on
a compatible revision. A Thing Model's stable `wotid` includes its major
version, such as `:v2`; it does not encode each minor or patch revision.

**Why.** An identifier that changes with each compatible revision cannot be
a stable reference. If every revision gets a new identifier, the registry
cannot identify documents that describe the same logical Thing or form their
`ancestor` lineage, and every holder of a reference has to update it. Keeping
minor and patch versions out of the identifier lets a recipient resolve the
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
token. See [Decision 6](#6-a-breaking-change-produces-a-new-logical-thing).

See [Section 1.3](spec.md#13-versioning),
[Section 5.1](spec.md#51-wot-identifiers-and-registry-ids) and
[Section 5.3](spec.md#53-lookup).

## 2. Customer WoT references are preserved, never rewritten

**Decision.** A registry stores a WoT document as supplied and MUST NOT
rewrite its `id`, `links[].href`, `tm:extends` or `tm:ref` values into
registry-specific identifiers.

**Why.** Documents arrive already authored and already referenced from
artifacts the registry never sees. Rewriting breaks those external references,
makes the registry's copy misrepresent a standard document, and gives the same
bytes two identities in two registries.

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

**Decision.** This specification does not define a mapping between a `wotid`
and a `thingdescriptionid`/`thingmodelid`. The client that creates a Resource
supplies both; the registry relates them by storing them together, not by
computing one from the other.

**Why.** A WoT identifier is a URI and an xRegistry id uses a much narrower
grammar, so the two cannot be equated — but mandating a particular
construction buys little and costs portability. The point of a first-party
`wotid` is precisely that a Consumer holding a WoT identifier does not need to
know the Resource id: it queries on `wotid`. Hosting environments also differ
in what they permit in a name, and a deployment whose ids are constrained more
tightly than xRegistry's own rules — an ARM-backed registry, for example —
would otherwise be unable to conform.

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
`thingmodel`, is defined in the extension model rather than left to an
application-managed label, and SHOULD be indexed so that
`?filter=wotid=<id>` is served without scanning.

**Why.** An informal label is not enforced, not validated and not indexed, so
a resolver cannot depend on it. Defining the attribute in the model means the
registry can reject a document that has no identity when it is written,
instead of failing to find it later.

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

## 6. A breaking change produces a new logical Thing

**Decision.** A breaking change creates a new Resource, reached by authoring a
new `wotid`, not by revising the existing one. The predecessor retains its
Versions and MUST set `deprecated.alternative` to the successor Resource URL.
A Thing Model identifier MUST carry a major-version token.

**Why.** [Decision 1](#1-identity-and-version-are-separate-values) holds a
`wotid` constant across revisions, and `wotid` is declared `matchversions`, so
every Version of a Resource carries the same one. A document incompatible with
its predecessor therefore cannot be a Version of it, and the only place a
successor can come from is a newly authored identifier. Stating this
explicitly removes an apparent contradiction between the two rules: without
it, a breaking change has no legal representation, since it can neither become
a Version of the existing Resource nor reuse its `wotid`.

The major-version token is the convention the
[Schema Registry](https://xregistry.io/xreg/xregistryspecs/schema-v1/docs/spec.html)
already recommends for `schemaid`, and `deprecated` is how it already links a
superseded schema to its replacement; reusing both keeps a WoT registry
legible to anyone who knows the approved specifications.

**Consequence.** A consumer holding a stale identifier is not stranded: the
old Resource still resolves, still serves its documents, and points at the
successor.

See [Section 5.1.1](spec.md#511-breaking-changes-and-successor-identifiers).

## 7. Version floors, semantic versions and reproducible resolution

**Decision.** Thing Models use `versionmode: semver` with
`singleversionroot: true`, and `compatibility` defaults to `backward`. The
resolver accepts a minimum-version floor, honours a sticky default, and
returns an exact selection with its origin.

**Why.** The resolver separates a dependency's minimum compatible version
from a caller's request to reproduce a previous selection:

| Choice | Rationale |
|---|---|
| Floor, not range | The major is part of identity, so a lower bound states the dependency without an upper bound or a range language. |
| Major in identity | Incompatible contracts are distinct Resources; a stable reference cannot silently acquire a breaking revision. Core `deprecated.alternative` points to the successor without redirecting old references. |
| `versionid` equals `version.model` | One authored SemVer value identifies the same revision inside and outside a registry. Mismatches are rejected; build metadata cannot fit Core's id grammar. |
| Generated `0.0.0-N`, not `0.0.N` | Generated ids do not collide with authored patch releases. Allocation skips occupied ids, including authored prereleases of the same spelling, and `versionorigin` distinguishes their source. Generated ids are not compatibility promises and cannot be floors. |
| Prereleases excluded by default | A dependency does not silently adopt an unstable or generated revision. A prerelease floor or caller opt-in makes prereleases eligible. There is no fallback for a collection containing only generated Versions. |
| Sticky default honoured, never bypassed | An operator's deliberate selection is authoritative unless the caller supplies an explicit pin. A sticky Version below the floor fails rather than selecting a different Version. |
| Pin in output, not document | The tuple `(wotid, versionid, contentdigest, origin)` supports reproducibility without putting registry-specific choices into portable WoT documents. Caller pins deliberately override normal floor selection. |

**Example.** Publishing `1.0.1` after `1.1.0` does not replace the newer
default. A TD derived from model `1.1.0` has that implicit floor when it has
exactly one type link. Several type links with a document-level model version
require explicit `tm:minVersion` on every link.

**Consequence.** Producers preserve the authored document bytes. Operators
migrate compatible legacy roots to one SemVer lineage and separate
incompatible identities before enabling the model. Consumers retain pins
externally and implement the error outcomes and algorithm in
[Section 5.4](spec.md#54-versioned-reference-resolution).

See the informative [versioning design](versioning-design.md) and the
[canonical test vectors](tests/resolution/README.md).
