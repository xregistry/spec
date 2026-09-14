# WoT Registry Decision Record

<!-- words: WoT wotid derivedfrom thingdescription thingmodel -->
<!-- words: thingdescriptionid thingmodelid canonicalurl standardsbody -->
<!-- words: openusd href td tm -->

This document records the identity, versioning, lookup and provenance
decisions behind the [WoT Registry specification](spec.md) and its
[model](model.json), together with the reasoning that led to each one. It is a
working document and changes with the draft.

## 1. Identity and version are separate values

**Decision.** A `wotid` is the document's authored `id` and MUST NOT carry a
version suffix such as `:v2`.

**Why.** An identifier that changes when the document changes is not an
identifier. With a version baked in, the registry cannot tell that two
documents describe the same logical Thing, `ancestor` lineage cannot be
formed, and every holder of a reference has to be rewritten on each revision.
Keeping the two apart also lets a recipient resolve a document without taking
a string apart, and reusing the Core rule for "latest" avoids a second,
conflicting notion of it.

**Example.** A typo is fixed in the lamp `urn:fabrikam:lamp:42`. Its `wotid`
and its `thingdescriptionid` do not change, and the correction becomes a new
Version of the same Resource. A Consumer that wants the correction asks for
the Resource `self` URL; one that wants the earlier text asks for that Version
by name.

**Consequence.** Revising a document leaves `wotid`, `thingdescriptionid` and
`thingmodelid` unchanged and adds a Version.

**Scope.** This constrains *mutating* an identifier, not the characters in
one. An author who publishes a second, incompatible Thing is naming a
different Thing, and the identifier they choose for it may legitimately carry
a `v2` token — that token is part of the new Thing's own permanent `wotid`,
not a version appended to an existing one. See
[Decision 10](#10-a-breaking-change-produces-a-new-logical-thing).

See [Section 1.3](spec.md#13-versioning),
[Section 5.1](spec.md#51-wot-identifiers-and-xids) and
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

**Consequence.** All registry-side identity lives outside the document, in
`wotid` and `derivedfrom`.

See [Section 5.2](spec.md#52-preserving-customer-documents).

## 3. A one-way construction maps a WoT identifier to an xRegistry id

**Decision.** `thingdescriptionid` and `thingmodelid` are the symbolic
identifier constructed from `wotid`. The construction is deterministic,
closed-form and lossy; implementations MUST NOT invert it, and recover the
authored identifier by reading `wotid`.

**Why.** A WoT identifier is a URI and an xRegistry id uses a much narrower
grammar, so the two cannot be equated. A deterministic construction lets a
Consumer work out a Resource path on its own, with no lookup table, while the
stored attribute remains the authority. The construction is deliberately the
same one the OpenUSD working draft uses, so an implementation that supports
both needs only one copy of it.

**Example.** `urn:fabrikam:lamp:42` becomes `urn.fabrikam.lamp.42`. The URI
scheme is discarded along the way, so two identifiers that differ only in
their scheme produce the same symbolic identifier. That is what "lossy" means
here, and it is why the construction is only ever run forwards.

See [Section 5.1.1](spec.md#511-the-symbolic-identifier-construction).

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

## 5. Ambiguous lookup is an explicit outcome, never an arbitrary pick

**Decision.** A Group-scoped lookup is unique by construction. A
registry-wide query that matches several Resources returns all of them; a
registry MUST NOT return an arbitrary first result. Unknown identifier and
unknown version are `404`; a malformed version or `wotid` is `400`.

**Why.** Returning whichever match happens to come first makes the answer
depend on storage order — not reproducible, and unusable in production.

**Example.** Two tenants each hold the same vendor Thing Model in their own
Group. A registry-wide query for its `wotid` matches both and returns both. A
caller that needs exactly one narrows the query by naming the Group.

See [Section 5.4](spec.md#54-ambiguity-and-errors).

## 6. Provenance metadata is advisory and does not affect identity

**Decision.** `license`, `publisher`, `standardsbody`, `canonicalurl` and
`maturity` describe where a document came from. They never determine whether
two documents are the same document, and changing one does not by itself
require a new Version. Adoption counts are registry operational data and are
not modeled.

**Why.** Agents need an explicit basis for preferring an official model over
an obscure one, but a popularity count is an observation of one registry's
traffic rather than a property of the document, and does not travel with it.

**Example.** An agent prefers a Thing Model marked `Standard` by a
`standardsbody` over one marked `Community`. Two documents that share a
`publisher` are still two documents, because identity is `wotid` alone, and
correcting a misspelled `publisher` does not create a Version.

See [Section 4.6](spec.md#46-provenance-and-selection-metadata).

## 10. A breaking change produces a new logical Thing

**Decision.** A breaking change creates a new Resource, and that Resource is
reached by authoring a **new `wotid`** — not by revising the existing one. The
superseded Resource retains its Versions and SHOULD set `deprecated` naming
the successor. Where a solution versions Things semantically, the authored
identifier SHOULD carry a major-version token.

**Why.** [Decision 1](#1-a-wot-identifier-never-encodes-a-version) makes a
Resource's id a pure function of its `wotid`, and holds that `wotid` constant
across revisions. Two Resources therefore require two `wotid`s, so the only
place a successor can come from is a newly authored identifier. Stating this
explicitly removes an apparent contradiction between the two rules: without
it, a breaking change has no legal representation, since it may neither become
a Version nor acquire an id.

The major-version token is the convention the
[Schema Registry](https://xregistry.io/xreg/xregistryspecs/schema-v1/docs/spec.html)
already recommends for `schemaid`, and `deprecated` is how it already links a
superseded schema to its replacement; reusing both keeps a WoT registry
legible to anyone who knows the approved specifications.

**Consequence.** A consumer holding a stale identifier is not stranded: the
old Resource still resolves, still serves its documents, and points at the
successor.

See [Section 5.1.2](spec.md#512-breaking-changes-and-successor-identifiers).

