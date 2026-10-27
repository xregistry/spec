# WoT Registry Decision Record

<!-- words: WoT wotid derivedfrom thingdescription thingmodel -->
<!-- words: thingdescriptionid thingmodelid canonicalurl standardsbody -->
<!-- words: openusd href td tm matchversions repointing -->
<!-- words: contentdigest minversion prereleases versionorigin -->

This document records identity, versioning, lookup, and provenance decisions
for the [WoT Registry specification](spec.md) and its [model](model.json). It
explains the reasoning behind those decisions. This working document changes
with the draft.

## 1. Identity and version are separate values

**Decision.** A `wotid` is the document's authored `id`. A registry MUST
reject a Version that supplies a different `wotid`. A Thing Model's stable
`wotid` includes its major version, such as `:v2`; it does not encode minor or
patch revisions.

**Why.** An identifier that changes with each compatible revision cannot
serve as a stable reference. If each revision used a new `wotid`, the registry
could not group documents for the same logical Thing or form their `ancestor`
lineage. Every reference holder would replace its stored `wotid`. The `wotid`
excludes minor and patch versions, so a recipient can resolve the document
without parsing a version suffix.

**Example.** A typo fix in the lamp `urn:fabrikam:lamp:42` leaves its `wotid`
and `thingdescriptionid` unchanged. The correction becomes a new Version of the
same Resource. A Consumer who wants the correction asks for the Resource
`self` URL. A Consumer who wants the earlier text asks for that Version by
name.

**Consequence.** Each revision leaves `wotid`, `thingdescriptionid`, and
`thingmodelid` unchanged. Each revision adds a Version to the same Resource.

**Scope.** This rule constrains revisions of an existing identifier. An
author publishing a second, incompatible Thing assigns it a distinct,
permanent `wotid`. A Thing Model's identifier MUST include a major-version
token. See [Decision 6](#6-a-breaking-thing-model-change-uses-a-successor-identifier).

See [Section 1.3](spec.md#13-versioning),
[Section 5.1](spec.md#51-wot-identifiers-and-registry-ids) and
[Section 5.3](spec.md#53-lookup).

## 2. Customer WoT references are preserved, never rewritten

**Decision.** The registry stores each WoT document as supplied. The registry
MUST NOT rewrite these values into registry-specific identifiers:

- `id`
- `links[].href`
- `tm:extends`
- `tm:ref`

**Why.** WoT documents can refer to artifacts that the registry does not store
or see. Rewriting these references would break them. It would also
misrepresent the standard document and give identical bytes different
identities in separate registries.

**Example.** A Thing Description can extend a Thing Model published elsewhere
by using that model's authored identifier. Repointing the reference to this
registry's own path would make the link easy to follow inside the registry but
useless outside it. Other WoT tools resolve the reference in the WoT identifier
space.

**Consequence.** The Resource `id` identifies a document within the registry,
outside its content. The registry stores the document's authored identifiers
unchanged in `wotid` and `derivedfrom`. Neither attribute holds an `xid`.

See [Section 5.2](spec.md#52-preserving-customer-documents).

## 3. The Resource id is chosen by the client, not derived by the registry

**Decision.** This specification does not map a `wotid` to a
`thingdescriptionid` or `thingmodelid`. The client that creates a Resource
supplies both values. The registry stores them together; it does not derive
one from the other.

**Why.** A WoT identifier is a URI, but xRegistry restricts which IDs are
valid. Requiring one construction would add little and reduce portability. A
first-party `wotid` lets a Consumer find the Resource by querying `wotid`.
Hosting environments differ in the names they permit. An ARM-backed registry
may permit fewer IDs than xRegistry. If the specification required every
registry to derive IDs the same way, an ARM-backed registry with stricter name
limits could not conform.

**Example.** A registry may store `urn:fabrikam:lamp:42` under the Resource id
`lamp-42`. It may instead use `urn.fabrikam.lamp.42`. Both choices conform. A
query for `?filter=wotid=urn:fabrikam:lamp:42` returns the same Resource.

**Consequence.** A deployment MAY use a local rule to derive Resource IDs. The
[OpenUSD Artifact Registry](../openusd/spec.md) working draft defines one. A
Consumer MUST NOT assume that a deployment used that rule to produce an id.

See [Section 5.1](spec.md#51-wot-identifiers-and-registry-ids).

## 4. `wotid` is a REQUIRED, indexed, first-party attribute

**Decision.** The extension model defines `wotid` as REQUIRED on every
`thingdescription` and `thingmodel`. An implementation SHOULD index `wotid` so
it can serve `?filter=wotid=<id>` without scanning the collection.

**Why.** A resolver cannot rely on an informal label. The registry does not
enforce, validate, or index such labels. The model defines `wotid` so the
registry can reject a write with no identity. This avoids a later failure when
a resolver looks for the document.

**Open point.** When a document has no `id` member, the Producer has to supply
a `wotid`. The registry rejects a write that provides neither an `id` nor a
`wotid`; it does not invent a value. This draft has not decided whether a
future revision should derive a `wotid` for that case.

See [Section 5.3](spec.md#53-lookup).

## 5. Provenance metadata is advisory and does not affect identity

**Decision.** Each Version carries these provenance attributes: `license`,
`publisher`, and `standardsbody`. It also carries `canonicalurl` and
`maturity`. They describe where the document came from. They never determine
whether two documents are the same.

**Why.** Agents need an explicit basis to prefer an official model over an
obscure one. A title or naming convention alone is guesswork. Each Version
stores these attributes with the document it describes. The metadata does not
affect identity.

**Example.** An agent can prefer a Thing Model marked `Standard` by its
`standardsbody` over one marked `Community`. Two documents from the same
`publisher` remain distinct because `wotid` alone determines identity.

**Consequence.** Updating one of these attributes is an ordinary update of a
Version attribute, governed by the Core rules for updating a Version. This
specification grants it no exemption from them.

See [Section 4.6](spec.md#46-provenance-and-selection-metadata).

## 6. A breaking Thing Model change uses a successor identifier

**Decision.** A breaking change to a Thing Model creates a new Resource with a
new major-version `wotid`. The predecessor keeps its Versions and MUST set
`deprecated.alternative` to the successor's Resource URL. A Thing Model's
`wotid` MUST include a major-version token. A breaking major revision to a TD
creates a new Version of the same concrete Thing, with its existing `id` and
`wotid`.

**Why.** [Decision 1](#1-identity-and-version-are-separate-values) keeps each
Thing Model's major compatibility line in its `wotid`. A breaking TM contract
therefore needs a new Resource. Thing Descriptions identify concrete Things.
Their `version.instance` marks a breaking major revision without changing the
Thing's `id` or `wotid`.

The [Schema Registry](https://xregistry.io/xreg/xregistryspecs/schema-v1/docs/spec.html)
recommends a major-version token for `schemaid`. It also uses `deprecated` to
link a superseded schema to its replacement. A WoT registry can reuse both
conventions, which makes the model familiar to readers of the approved
specifications.

**Consequence.** A Consumer holding a stale TM identifier can retrieve the
predecessor and inspect its successor. A TD consumer resolves a major instance
revision under the same Thing identifier.

See [Section 5.1.1](spec.md#511-breaking-changes-and-successor-identifiers).

## 7. How resolvers enforce floors and reproduce exact versions

**Decision.** Thing Models and Thing Descriptions use
`versionmode: semver` with `singleversionroot: true`. A TM `versionid` equals
`version.model`; a TD `versionid` equals `version.instance`. Both receive a
server-set `versionorigin`. A reference from one Thing Description to another
can set `td:minVersion` as a floor. The resolver keeps the selected version
below the next major. The resolver honours a sticky default only when it
satisfies the applicable floor and range, and returns an exact selection with
its origin.

**Why.** A dependency can set a minimum compatible version. A caller can ask
the resolver for the exact Version selected earlier:

| Choice | Rationale |
|---|---|
| TM floors are uncapped; TD floors are caret-bounded | A Thing Model's major version is part of its `wotid`. A Thing Description's `id` names a concrete Thing, so its floor stays within that major. Without a floor, a reference between Thing Descriptions can cross majors. |
| Major in TM identity | Thing Models with incompatible contracts use distinct Resources, so a stable reference cannot silently acquire a breaking revision. A TD `id` names one concrete Thing; a breaking major revision stays under that `id`. Core `deprecated.alternative` points to the TM's successor without redirecting old references. |
| `versionid` follows the document revision | For valid SemVer, `versionid` MUST equal `version.model` on a Thing Model and `version.instance` on a Thing Description. The registry rejects a supplied mismatch. Core's `id` rules exclude build metadata. |
| Generated `0.0.0-N`, not `0.0.N` | This format avoids authored patch releases. The registry skips occupied ids, including authored prereleases with the same spelling. When `versionid` comes from an authored SemVer field, the server sets `versionorigin` to `authored`. Otherwise, the server sets it to `generated`. Generated IDs do not promise compatibility and cannot serve as floors. |
| Prereleases excluded by default | A dependency does not silently adopt an unstable or generated revision. A prerelease floor or caller opt-in makes prereleases eligible. The resolver returns no fallback when a collection contains only generated Versions. |
| Sticky default honoured only in range | An operator's deliberate selection is authoritative unless the caller supplies an explicit pin. A sticky Version below the floor or in a higher TD major fails rather than selecting a different Version. |
| Pin in output, not document | The tuple `(wotid, versionid, contentdigest, origin)` supports reproducibility without putting registry-specific choices into portable WoT documents. Caller pins deliberately override normal floor selection. |

**Example: Sticky default.** Publishing `1.0.1` after `1.1.0` does not replace
the newer default.

**Example: Implicit floor.** A Thing Description derived from model version
`1.1.0` has that implicit floor only when it has exactly one type link.

**Example: Major cap.** A `1.2.0` floor on a reference between Thing
Descriptions admits versions below `2.0.0`. Without a floor, the reference can
select a later major.

**Example: Multiple type links.** When a Thing Description has several type
links and carries `version.model` on the document, each link needs its own
`tm:minVersion`.

**Consequence.** Producers preserve the authored document bytes. Operators
migrate compatible legacy roots to one SemVer lineage and separate
incompatible identities before enabling the model. Consumers keep pins
outside the document. They implement the error outcomes and algorithm in
[Section 5.4](spec.md#54-versioned-reference-resolution).

The following design and test resources provide supporting detail:
- [versioning design](versioning-design.md)
- [D7 selection flow](versioning-design.md#d7-selection-defaults-and-exact-pins)
- [snapshot acceptance rules](publication-design.md#selection-and-acceptance)
- [canonical test vectors](tests/resolution/README.md)
