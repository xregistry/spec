# WoT Registry Decision Record

<!-- words: WoT wotid derivedfrom byom td tm tds tms -->

This document records the identity, versioning, lookup and grouping decisions
behind the [WoT Registry specification](spec.md) and its [model](model.json),
together with the reasoning that led to each one. It is a working document and
changes with the draft.

## 1. A WoT identifier never encodes a version

**Decision.** A `wotid` is the document's authored `id`, and MUST NOT be
rewritten — for example by appending a `:v2` suffix — because the document it
names was revised. It is enforced with `matchversions`, so all Versions of a
Resource carry one `wotid`.

**Why.** An identifier that changes when the document changes is not an
identifier. With a revision baked in, the registry cannot tell that two
documents describe the same logical Thing, `ancestorid` lineage cannot be
formed, and every holder of a reference has to be rewritten on each revision.

**Consequence.** Revising a document leaves `wotid`, `thingdescriptionid` and
`thingmodelid` unchanged and adds a Version.

**Scope.** This constrains *mutating* an identifier, not the characters in
one. An author who publishes a second, incompatible Thing is naming a
different Thing, and the identifier they choose for it may legitimately carry
a `v2` token — that token is part of the new Thing's own permanent `wotid`,
not a version appended to an existing one. See
[Decision 10](#10-a-breaking-change-produces-a-new-logical-thing).

See [Section 5.1](spec.md#51-wot-identifiers-and-xids).

## 2. Version is carried separately from identity

**Decision.** Version lives in the xRegistry `versionid`, and — where the
document declares one — in the document's own WoT `version` member. It is
never part of an identifier, and a caller passing an identifier and a version
over a transport passes them as two values.

**Why.** Separating them lets a recipient resolve a document without parsing a
compound string, and keeps "which Thing" independent of "which revision".

See [Section 1.3](spec.md#13-versioning) and
[Section 5.3](spec.md#53-lookup).

## 3. Lookup supports exact version and latest version

**Decision.** The Resource `self` URL serves the default Version; a specific
Version is addressed at `<self>/versions/<versionid>`. "Latest" is the
xRegistry Core default Version, which this specification does not redefine.

**Why.** Reusing the Core rule avoids a second, divergent notion of latest,
and both forms fall out of the existing API with no WoT-specific endpoint.

See [Section 5.3](spec.md#53-lookup).

## 4. Customer WoT references are preserved, never rewritten

**Decision.** A registry stores a WoT document as supplied and MUST NOT
rewrite its `id`, `links[].href`, `tm:extends` or `tm:ref` values into
registry-specific identifiers.

**Why.** Documents arrive already authored and already referenced from
artifacts the registry never sees. Rewriting breaks those external references,
makes the registry's copy misrepresent a standard document, and gives the same
bytes two identities in two registries.

**Consequence.** All registry-side identity lives outside the document, in
`wotid` and `derivedfrom`.

See [Section 5.2](spec.md#52-preserving-customer-documents).

## 5. A one-way construction maps a WoT identifier to an xRegistry id

**Decision.** `thingdescriptionid` and `thingmodelid` are the symbolic
identifier constructed from `wotid`. The construction is deterministic,
closed-form and lossy; implementations MUST NOT invert it, and recover the
authored identifier by reading `wotid`.

**Why.** WoT identifiers are URIs and xRegistry ids are a restricted grammar,
so they cannot be equated. A deterministic construction lets a Consumer
compute a Resource path with no lookup table, while the stored attribute
remains the authority. The construction is deliberately the same one the
OpenUSD working draft uses, so an implementation needs only one copy of it.

See [Section 5.1.1](spec.md#511-the-symbolic-identifier-construction).

## 6. `wotid` is a REQUIRED, indexed, first-party attribute

**Decision.** `wotid` is REQUIRED on every `thingdescription` and
`thingmodel`, is defined in the extension model rather than left to an
application-managed label, and SHOULD be indexed so that
`?filter=wotid=<id>` is served without scanning.

**Why.** An informal label is unenforced, unvalidated and un-indexable, so a
resolver cannot depend on it. Making the attribute first-party means the
registry can reject a document that lacks identity at write time rather than
failing to find it later.

**Open point.** Where a document carries no `id` member, the Producer has to
supply a `wotid`; the registry rejects a write that supplies neither rather
than inventing a value. Whether a future revision ought to define a derivation
for that case is not yet settled.

See [Section 5.3](spec.md#53-lookup).

## 7. Ambiguous lookup is an explicit outcome, never an arbitrary pick

**Decision.** A Group-scoped lookup is unique by construction. A
registry-wide query that matches several Resources returns all of them; a
registry MUST NOT return an arbitrary first result. Unknown identifier and
unknown version are `404`; a malformed version or `wotid` is `400`.

**Why.** Returning an arbitrary member of a match set makes the answer depend
on storage order — not reproducible, and unusable in production.

See [Section 5.4](spec.md#54-ambiguity-and-errors).

## 8. Affordance grouping is OPTIONAL, with a single-document fallback

**Decision.** Nothing in this specification depends on a TD's affordances
being partitioned. A proposal such as `td:submodel` is a member of the WoT
document, not of the registry model, so support for it is OPTIONAL and its
rejection does not block WoT registry support.

**Why.** Documents that arrive from outside routinely contain no grouping
construct, and have to remain fully supported.

See [Section 6.4](spec.md#64-affordance-grouping).

## 9. Provenance metadata is advisory and does not affect identity

**Decision.** `license`, `publisher`, `standardsbody`, `canonicalurl` and
`maturity` describe where a document came from. They never determine whether
two documents are the same document, and changing one does not by itself
require a new Version. Adoption counts are registry operational data and are
not modeled.

**Why.** Agents need an explicit basis for preferring an official model over
an obscure one, but a popularity count is an observation of one registry's
traffic rather than a property of the document, and does not travel with it.

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

## Open items

These are not yet decided and are tracked here rather than inferred:

- Whether a `wotid` ought to be unique registry-wide, rather than
  Group-wide, for registries that serve a single tenant.
- Whether `derivedfrom` ought to be REQUIRED where the document declares
  `tm:extends`, which would let a registry validate the closure but would also
  force it to parse the document.
- Whether a future revision defines a derivation of `wotid` for documents that
  carry no `id` member.
