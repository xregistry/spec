# WoT Registry Decision Record

<!-- words: WoT wotid derivedfrom thingdescription thingmodel -->
<!-- words: thingdescriptionid thingmodelid canonicalurl standardsbody -->
<!-- words: openusd href td tm matchversions repointing -->
<!-- words: contentdigest minversion prereleases versionorigin -->

This working document explains the identity, versioning, lookup and provenance
decisions behind the [WoT Registry specification](spec.md) and its
[model](model.json). It changes with the draft.

## 1. Identity and version are separate values

**Decision.** A `wotid` is the document's authored `id` and MUST NOT change on
a compatible revision. A Thing Model's stable `wotid` includes its major
version, such as `:v2`. It does not encode minor or patch revisions.

**Why.** Changing the identifier on each compatible revision would force every
reference holder to replace its stored `wotid`. The Registry could no longer
group documents for the same logical Thing or form their `ancestor` lineage.
The stable `wotid` excludes minor and patch versions, so a recipient resolves
the document without parsing a version suffix from its `wotid`.

**Example.** Correcting a typo in the lamp `urn:fabrikam:lamp:42` creates a new
Version of the same Resource without changing its `wotid` or
`thingdescriptionid`. A Consumer retrieves the correction through the
Resource's `self` URL or names the earlier Version to retrieve the old text.

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

**Why.** A WoT document can refer to artifacts outside the Registry. Rewriting
those references would break them and misrepresent the standard document.
It would also give identical bytes different identities in separate Registries.

**Example.** A Thing Description can extend an externally published Thing Model
using that model's authored identifier. Repointing the reference to a local
Registry path would make it easy to follow there but useless outside that
Registry. Other WoT tools resolve the authored reference in the WoT identifier
space.

**Consequence.** The Resource `id` identifies a document within the registry,
outside its content. The registry stores the document's authored identifiers
unchanged in `wotid` and `derivedfrom`. Neither attribute holds an `xid`.

See [Section 5.2](spec.md#52-preserving-customer-documents).

## 3. The Resource id is chosen by the client, not derived by the registry

**Decision.** This specification does not map a `wotid` to a
`thingdescriptionid` or `thingmodelid`. The client that creates a Resource
supplies both values. The registry stores them together. It does not derive
one from the other.

**Why.** A WoT identifier is a URI, while xRegistry restricts entity IDs.
Hosting environments can restrict them further: an ARM-backed Registry can
permit fewer IDs than Core. A mandatory construction would prevent such a
Registry from conforming. It would add little and reduce portability because
the first-party `wotid` already lets a Consumer find the Resource by querying
`wotid`.

**Example.** A registry can store `urn:fabrikam:lamp:42` under the Resource id
`lamp-42`. It can instead use `urn.fabrikam.lamp.42`. Both choices conform. A
query for `?filter=wotid=urn:fabrikam:lamp:42` returns the same Resource.

**Consequence.** A deployment MAY use a local rule to derive Resource IDs. The
[OpenUSD Artifact Registry](../openusd/spec.md) working draft defines one. A
Consumer MUST NOT assume that a deployment used that rule to produce an id.

See [Section 5.1](spec.md#51-wot-identifiers-and-registry-ids).

## 4. `wotid` is a REQUIRED, indexed, first-party attribute

**Decision.** The extension model defines `wotid` as REQUIRED on every
`thingdescription` and `thingmodel`. An implementation SHOULD index `wotid` so
it can serve `?filter=wotid=<id>` without scanning the collection.

**Why.** A resolver cannot rely on an informal label that the Registry does
not enforce, validate or index. Defining `wotid` in the model lets the Registry
reject a write with no identity rather than leave the resolver to fail when it
later looks for the document.

**Open point.** When a document has no `id` member, the Producer has to supply
a `wotid`. The registry rejects a write that provides neither an `id` nor a
`wotid`. It does not invent a value. This draft has not decided whether a
future revision ought to define a derivation for that case.

See [Section 5.3](spec.md#53-lookup).

## 5. Provenance metadata is advisory and does not affect identity

**Decision.** Each Version carries provenance metadata in `license`,
`publisher`, `standardsbody`, `canonicalurl` and `maturity`. These attributes
describe where the document came from; they do not determine whether two
documents are the same.

**Why.** An agent needs explicit metadata to prefer an official model over an
obscure one rather than guess from a title or naming convention. Keeping the
attributes on each Version associates them with the document they describe
without changing its identity.

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
`version.model`. A TD `versionid` equals `version.instance`. Both receive a
server-set `versionorigin`. A reference from one Thing Description to another
can set `td:minVersion` as a floor. The resolver keeps the selected version
below the next major. The resolver honours a sticky default only when it
satisfies the applicable floor and range, and returns an exact selection with
its origin.

**Why.** Floors let a dependency require a minimum compatible version. Pins
let a caller reproduce the exact Version selected earlier. The choices below
define how the resolver handles both:

| Choice | Rationale |
|---|---|
| TM floors are uncapped, TD floors are caret-bounded | A Thing Model's major version is part of its `wotid`. A Thing Description's `id` names a concrete Thing, so its floor stays within that major. Without a floor, a reference between Thing Descriptions can cross majors. |
| Major in TM identity | Thing Models with incompatible contracts use distinct Resources, so a stable reference cannot silently acquire a breaking revision. A TD `id` names one concrete Thing. A breaking major revision stays under that `id`. Core `deprecated.alternative` points to the TM's successor without redirecting old references. |
| `versionid` follows the document revision | For valid SemVer, `versionid` equals `version.model` on a Thing Model and `version.instance` on a Thing Description. The registry rejects a supplied mismatch. Core's `id` rules exclude build metadata. |
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
- [versioning design](../../publication/design/design.md)
- [D7 selection flow](../../publication/design/design.md#d7-selection-defaults-and-exact-pins)
- [snapshot acceptance rules](../../publication/design/design.md#selection-and-acceptance)
- [canonical test vectors](tests/resolution/README.md)
