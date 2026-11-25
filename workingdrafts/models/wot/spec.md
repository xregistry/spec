# WoT Registry Service - Version 1.0-rc4

<!-- words: WoT JSON-LD Servient affordances affordance discoverability tm td -->
<!-- words: thingdescription thingdescriptionid thingdescriptionurl thingdescriptions thingdescriptionsurl thingdescriptionscount thingdescriptionbase -->
<!-- words: thingmodel thingmodels thingmodelid thingmodelurl thingmodelsurl thingmodelscount thingmodelbase -->
<!-- words: thingdescriptiongroup thingdescriptiongroups thingdescriptiongroupid thingdescriptiongroupsurl thingdescriptiongroupscount -->
<!-- words: thingmodelgroup thingmodelgroups thingmodelgroupid thingmodelgroupsurl thingmodelgroupscount -->
<!-- words: invokeaction readproperty writeproperty subscribeevent securitydefinitions versionmode urn href -->
<!-- words: workbench fabrikam lamp lighting jwt tenantid deviceid -->
<!-- words: formatvalidated compatibilityvalidated formatvalidatedreason compatibilityvalidatedreason -->
<!-- words: coap describedby integrators lifecycles modbus opc tds tms ua matchversions -->
<!-- words: wotid wotids derivedfrom canonicalurl standardsbody submodel spdx openusd -->
<!-- words: toolchain byom contoso maturity publisher nosniff validateformat -->
<!-- words: shortself -->
<!-- words: allowprerelease contentdigest minversion prereleases unversioned versionorigin -->
<!-- words: marcschier namespace sourcename uav viewversion iri jsonld -->
<!-- words: percent dereferenceable affordanceselector -->
<!-- words: compatibilityline wotversionprofile wotversion vn -->

## Abstract

This specification extends the xRegistry document format and API
[specification][xRegistry Core] with a WoT (Web of Things) Registry for
storing, managing, and discovering W3C
[WoT Thing Description (WoT-TD)][WoT-TD-1.1] and
[WoT Thing Model (WoT-TM)][WoT-TM-1.1] documents.

## Table of Contents

- [WoT Registry Service - Version 1.0-rc4](#wot-registry-service---version-10-rc4)
  - [Abstract](#abstract)
  - [Table of Contents](#table-of-contents)
  - [1. Overview](#1-overview)
    - [1.1. Thing Descriptions and Thing Models](#11-thing-descriptions-and-thing-models)
    - [1.2. Relationship to Other xRegistry Specs](#12-relationship-to-other-xregistry-specs)
    - [1.3. Versioning](#13-versioning)
    - [1.4. Document Store](#14-document-store)
  - [2. Notations and Terminology](#2-notations-and-terminology)
    - [2.1. Notational Conventions](#21-notational-conventions)
    - [2.2. Terminology](#22-terminology)
      - [2.2.1. Thing Description](#221-thing-description)
      - [2.2.2. Thing Model](#222-thing-model)
      - [2.2.3. WoT Identifier](#223-wot-identifier)
    - [2.3. Thing Description Group](#23-thing-description-group)
    - [2.4. Thing Model Group](#24-thing-model-group)
  - [3. WoT Registry Model](#3-wot-registry-model)
  - [4. WoT Registry](#4-wot-registry)
    - [4.1. Thing Description Groups](#41-thing-description-groups)
    - [4.2. Thing Description Resources](#42-thing-description-resources)
    - [4.3. Thing Model Groups](#43-thing-model-groups)
    - [4.4. Thing Model Resources](#44-thing-model-resources)
    - [4.5. Formats](#45-formats)
      - [4.5.1. WoT Thing Description](#451-wot-thing-description)
      - [4.5.2. WoT Thing Model](#452-wot-thing-model)
    - [4.6. Provenance and Selection Metadata](#46-provenance-and-selection-metadata)
  - [5. Identity and Resolution](#5-identity-and-resolution)
    - [5.1. WoT Identifiers and Registry Ids](#51-wot-identifiers-and-registry-ids)
      - [5.1.1. Breaking Changes and Successor Identifiers](#511-breaking-changes-and-successor-identifiers)
    - [5.2. Preserving Customer Documents](#52-preserving-customer-documents)
    - [5.3. Lookup](#53-lookup)
      - [5.3.1. CloudEvents WoT Source Resolution](#531-cloudevents-wot-source-resolution)
    - [5.4. Versioned Reference Resolution](#54-versioned-reference-resolution)
      - [5.4.1. Floors and Pins](#541-floors-and-pins)
      - [5.4.2. Resolver Algorithm](#542-resolver-algorithm)
      - [5.4.3. Errors and Test Vectors](#543-errors-and-test-vectors)
      - [5.4.4. Publication closure](#544-publication-closure)
    - [5.5. Incremental Profile](#55-incremental-profile)
  - [6. Relationships and Cross-References](#6-relationships-and-cross-references)
    - [6.1. Thing Description to Thing Model](#61-thing-description-to-thing-model)
    - [6.2. Thing Description to Thing Description](#62-thing-description-to-thing-description)
    - [6.3. Thing Description to Endpoint Registry](#63-thing-description-to-endpoint-registry)
    - [6.4. Thing Description to Schema Registry](#64-thing-description-to-schema-registry)
    - [6.5. Affordance Grouping](#65-affordance-grouping)
  - [7. Security](#7-security)

## 1. Overview

A WoT Registry stores and manages two W3C Web of Things document classes.
Thing Descriptions (TDs) describe concrete, network-facing Things. Thing Models
(TMs) define reusable, abstract templates for classes of Things.

Device fleets, gateways, integrators, and consuming applications use the
Registry to share Thing metadata and discover Things and their templates as
described by W3C [WoT Discovery][WoT-Discovery]. TDs and TMs can also be
cross-referenced from xRegistry [Endpoint][xRegistry Endpoint],
[Message][xRegistry Message], and [Schema][xRegistry Schema] entries.

### 1.1. Thing Descriptions and Thing Models

A Thing Description (TD) is a [JSON-LD 1.1][JSON-LD] document conforming to
[WoT-TD 1.1][WoT-TD-1.1]. It identifies a deployed Thing, declares its
properties, actions, and events, and provides `forms` that bind those
interaction affordances to network endpoints over protocols such as HTTP,
MQTT, CoAP, OPC-UA, or Modbus.

A JSON-LD document is JSON whose context defines the meaning of its terms.
WoT document semantics come from the WoT specifications. A resolver uses
the applicable JSON-LD context where this draft calls for expanded terms.

A Thing Model (TM) is a JSON-LD 1.1 document conforming to
[WoT-TM 1.1][WoT-TM-1.1]. It describes an abstract class of Things and
typically omits the network target (`href`) from its forms. A TD MAY be
derived from more than one TM and can identify the models with `type`
links, as described in
[Section 6.1](#61-thing-description-to-thing-model). A concrete TD MAY
extend or compose one or more TMs through WoT mechanisms such as
`tm:extends` for inheritance or `tm:ref` for a definition reference.
JSON-LD `@type` declares a type; it does not instruct a processor to merge
documents and is not the `type` link relation.

Although both document classes use JSON-LD and share part of its vocabulary,
a WoT Registry MUST treat them as distinct Resource types. Their intended use,
validation rules and lifecycles differ.

### 1.2. Relationship to Other xRegistry Specs

A WoT Registry is complementary to the xRegistry [Endpoint][xRegistry Endpoint],
[Message][xRegistry Message], and [Schema][xRegistry Schema] registries:

- A Thing Description's `forms` array describes protocol bindings that MAY
  also be represented as `endpoint` Resources. See
  [Section 6.3](#63-thing-description-to-endpoint-registry).
- A Thing Description's property/action/event data schemas (declared inline
  via WoT data-schema vocabulary) MAY reference external schemas managed by
  the xRegistry Schema Registry. See
  [Section 6.4](#64-thing-description-to-schema-registry).
- A Thing Description MAY reference one or more Thing Models from which it
  is derived. See [Section 6.1](#61-thing-description-to-thing-model).

The [xRegistry Publication working draft](../../publication/spec.md) defines
immutable snapshots and domain-closure requirements. WoT closure records
exact Versions for entry documents and reachable in-scope dependencies.
[Section 5.4.4](#544-publication-closure) defines prerequisites for WoT
publication closure and records the mapping decisions still needed to
reconstruct a pinned WoT view. It does not yet define a complete WoT closure
profile.

For ordinary storage, this specification does not require the Registry to
resolve or validate the cross-references listed above. An implementation
MAY check that a referent exists, but it still stores and serves the document
when a referent is absent. The requirements for a publication claiming
closure are separate. A Consumer composing a TD from Thing Models or
binding an affordance to an endpoint depends on those references independently
of the Registry's checks.

### 1.3. Versioning

A Registry exposes either the [Semantic Versioning][SemVer] (SemVer)
[model](model.json) or the [incremental model](model-incremental.json).
The SemVer profile uses semantic precedence. The incremental profile uses
increasing integer IDs within one Resource sequence. The read-only Registry
attribute `wotversionprofile` identifies the model as `semver` or
`incremental`. If the Consumer already knows that a trusted source uses
the legacy SemVer model, omission denotes `semver`. Omission MUST NOT
identify an arbitrary Core provider as SemVer. An unrecognized profile fails
version-aware selection with `unknown-profile`. Neither a Version ID
nor an authored document field identifies the profile.

The SemVer-specific assignment, compatibility and successor rules below
apply only to the SemVer profile. The incremental profile uses
[Section 5.5](#55-incremental-profile) instead and retains the shared
document, identity and retrieval rules.

Each Version of a `thingdescription` or `thingmodel` Resource holds a complete
WoT document, stored without rewriting its bytes. A Resource's `wotid` and
Registry Resource id are stable across compatible revisions. `wotid` is
declared with [`matchversions`][xRegistry matchversions]. A registry MUST
reject a Version that supplies a different `wotid`. In the SemVer profile,
a Thing Model's major version MUST be part of its `wotid`, and a breaking
Thing Model change MUST use a new `wotid` and a new Resource
([Section 5.1.1](#511-breaking-changes-and-successor-identifiers)).

Thing Model Resources and Thing Description Resources MUST use Core
[`versionmode`][Core versionmode] `semver` and
[`singleversionroot`][Core singleversionroot] `true`. Core orders each
Resource's [`ancestorid`][Core ancestorid] lineage by SemVer precedence and
forbids multiple roots with these aspects. The assignment rules for the
corresponding authored fields are:

| Resource | Authored field | SemVer without build metadata that fits a Core ID | Missing or non-SemVer |
| --- | --- | --- | --- |
| TM | `version.model` | `versionid` MUST equal the authored value verbatim. | The registry MUST assign `0.0.0-N`. |
| TD | `version.instance` | `versionid` MUST equal the authored value verbatim. | The registry MUST assign `0.0.0-N`. |

For either Resource type, the registry MUST inspect the authored field
without modifying the stored document. The original authored field MUST NOT
be rewritten, including when absent or non-SemVer.

SemVer build metadata (`+build`) MUST be rejected as `invalid-version`
because `+` is not allowed by Core's [ID constraints][Core id constraints].
An authored SemVer value that exceeds Core's 128-character limit MUST also
be rejected as `invalid-version`. These values do not take the generated-ID
branch in the table.

`N` is the lowest positive integer whose complete id is not already used
in the Resource. The registry MUST assign an omitted `versionid`. A supplied
`versionid` MUST equal the authored or generated assignment, or the registry
MUST reject it as `version-mismatch`. A supplied id that violates Core's id
grammar MUST be rejected as `invalid-version` before this comparison. Core
requires an immutable, unique [`versionid`][Core versionid]. This extension
defines the assignment in place of its default
[Version ID algorithm][Core Version IDs].

The Registry MUST perform assignment and creation atomically with respect to
concurrent writes, so it cannot assign the same generated id to two writes.

Each Thing Model Version and each Thing Description Version MUST have a
server-set, read-only `versionorigin`. Its value MUST be `authored` when the
Version's id comes from a SemVer authored field, and `generated` otherwise.

Client-supplied `versionorigin` MUST be ignored under Core's
[read-only attribute rules][Core read-only rules]. The model initializes
the attribute to `authored`. When the registry assigns a generated id, it
MUST replace that initial value with `generated`. The model default does
not replace the assignment rules above.

Generated ids are prereleases. They MUST NOT be used as minimum-version floors,
even when the target Version is absent.

A TD's `version.model` describes a model dependency, not the TD's instance
version. [Section 5.4](#54-versioned-reference-resolution) defines when it
sets an implicit floor and how floors apply to TD, TM, and projection
source references.

These pseudo-JSON fragments show the authored version and the Version
attributes the registry assigns. Ellipses mark omitted members. The TM
reference's `tm:minVersion` constrains the dependency, not the TM's own
`versionid`.

```yaml
{
  "id": "urn:example:pump:v1",
  "version": { "model": "1.4.0" },
  "properties": {
    "pressure": {
      "tm:ref": "./base.tm.json#/properties/pressure",
      "tm:minVersion": "1.2.0"
    }
  },
  ...
}
```

```yaml
{
  "versionid": "1.4.0",
  "versionorigin": "authored",
  ...
}
```

A TD's `version.instance` determines its own Version ID independently of
the floor on a TD it extends. In this example the Version gets
`versionid: "2.0.0"` and `versionorigin: "authored"`:

```yaml
{
  "@context": [...],
  "id": "urn:example:pump:42",
  "version": { "instance": "2.0.0" },
  "links": [
    {
      "rel": "td:extends",
      "href": "urn:example:pump:base",
      "td:minVersion": "1.4.0"
    }
  ],
  ...
}
```

For Thing Models, the Resource-level [`compatibility`][Core compatibility]
attribute in `meta` MUST default to `backward`. A backward-compatible TM
revision MUST NOT remove or narrow an affordance, a data schema, or an `@type`,
and MUST NOT introduce a new mandatory member. Narrowing includes reducing
the accepted values or operations of an existing member. These constraints
apply to every earlier Version in the Resource's Core
[`ancestorid`][Core ancestorid] lineage.

A Registry MAY validate this domain-specific compatibility rule through Core's
[`validatecompatibility`][Core validatecompatibility]
capability. Core's [`strictvalidation`][Core strictvalidation] rules still
apply. The requirement to use a successor Resource for a breaking Thing
Model change applies even if the Registry does not check compatibility.

When [`defaultversionsticky`][Core defaultversionsticky] is false, Core's SemVer
[`versionmode`][Core versionmode] orders the default. A late `1.0.1` after
`1.1.0` MUST NOT replace `1.1.0` as the default. A sticky default MUST be
honoured.

Reference resolution additionally applies floors and prerelease eligibility in
[Section 5.4](#54-versioned-reference-resolution). An ordinary unversioned
Resource retrieval still serves Core's default.

For migration, an operator SHOULD inventory every Version and root of a
legacy Resource before enabling this model. Compatible TM roots SHOULD be
imported into one SemVer-ordered lineage with ids assigned by the rules above.
Incompatible roots MUST be placed in distinct Resources with distinct
major-version `wotid`s.

The operator SHOULD inventory legacy TD Resources with manually assigned
`versionid`s and re-import them with ids assigned from `version.instance` or
generated by these rules.

Where changing an old immutable id or authored document would be necessary,
the operator SHOULD preserve the legacy Resource outside the conforming
collection and import a copy under a new registry Resource id.

The operator MUST preserve authored bytes, record old-to-new registry paths
for callers holding pins, and establish a valid default before enabling
`singleversionroot`. The path mapping records the migration; it does not
redirect an exact pin or guarantee that the old path remains available.
An operator MUST NOT claim that an unresolved multiple-root Resource
conforms to this model.

`tm:minVersion` and `td:minVersion` are proposed extensions to the W3C WoT
Thing Description. They are not part of the published WoT 1.1 Recommendation.
Sections 5.4 and 6.2 define their resolver and TD-composition behavior.

### 1.4. Document Store

The WoT Registry is a document store. The `thingdescriptions` and `thingmodels`
Resources use the xRegistry Core default of
[`hasdocument`][xRegistry hasdocument] `true`; [model.json](model.json)
therefore does not declare it.

Such a Resource is exposed through two views. The applicable protocol binding
defines how they are selected. The xRegistry HTTP Binding uses these URL
forms:

| URL form | View | Representation |
| --- | --- | --- |
| [`self`][xRegistry self] with `$details` | Metadata | xRegistry attributes. |
| The same URL without `$details` | Document | Stored document bytes. |
| [`shortself`][xRegistry shortself], when enabled | Document | Alternative document URL. |

The document view serves stored JSON-LD bytes under their media type:
[`application/td+json`][WoT-TD media] for TDs and
[`application/tm+json`][WoT-TM media] for TMs, or an explicitly registered
deployment media type under [Section 4.2](#42-thing-description-resources)
or [Section 4.4](#44-thing-model-resources).

An xRegistry-unaware WoT consumer MAY use a Version's `self` URL with the
`$details` suffix removed, or its `shortself` URL, as a regular WoT TD or TM
URL. The unchanged `self` URL returns xRegistry metadata rather than the
document. The metadata and document URLs are not interchangeable.

Addressing a `thingdescription` or `thingmodel` Resource without naming a
Version serves that Resource's [Core default Version][Core defaults].
[Section 5.3](#53-lookup) describes both forms of retrieval.

## 2. Notations and Terminology

### 2.1. Notational Conventions

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD",
"SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be
interpreted as described in [RFC 2119](https://tools.ietf.org/html/rfc2119).

For clarity, OPTIONAL attributes (specification-defined and extensions) are
OPTIONAL for clients to use, but the servers' responsibility will vary.
In writes, the server MUST silently store server-unknown extension
attributes in the backing datastore. If a client supplies a
specification-defined or server-known extension attribute whose feature
is unsupported or disabled, the server MUST report an error.

However, as with all attributes, if accepting the attribute results in a bad
state (such as exceeding a size limit or resulting in a security issue), then
the server MAY choose to reject the request.

In the pseudo JSON format snippets `?` means the preceding attribute is
OPTIONAL, `*` means the preceding attribute MAY appear zero or more times,
and `+` means the preceding attribute MUST appear at least once. An
unquoted `#` starts a comment in these pseudo-JSON snippets.
Whitespace characters in the JSON snippets are used for readability and are
not normative.

### 2.2. Terminology

This specification defines the following terms:

#### 2.2.1. Thing Description

The Thing Description is the WoT-TD 1.1 JSON-LD document. A
`thingdescription` Resource groups one or more Versions for the same Thing
instance, each holding one such document. Addressing the Resource without
naming a Version serves its [default Version][xRegistry version-ids].

The TD's `version.instance` carries its revision, including breaking major
revisions. A major revision remains under the same `id`, `wotid`, and Resource.
If a Resource declares the [`compatibility`][xRegistry compatibility] attribute,
all its Versions MUST adhere to that policy. A TD that identifies a different
Thing MUST use that Thing's `id` and a corresponding Resource. See
[Section 1.3](#13-versioning).

#### 2.2.2. Thing Model

The Thing Model is the WoT-TM 1.1 JSON-LD document. A `thingmodel`
Resource groups its Versions, each holding one such document. As with
Things, the Resource's `compatibility` attribute governs versioning.

A Thing Model describes a class of Things and typically lacks concrete `href`
values in its forms. A Thing Description instead describes a specific deployed
Thing instance.

#### 2.2.3. WoT Identifier

A WoT identifier is the URI a WoT document carries in its `id` member, as
defined by [WoT-TD 1.1][WoT-TD-1.1], for example `urn:fabrikam:lamp:42`. Other
WoT documents and tools use it to identify what the document describes,
independently of its storage location.

A WoT identifier is held in the `wotid` attribute. It is distinct from the
xRegistry `thingdescriptionid`/`thingmodelid`, which identifies the Resource
within a Registry. The two MAY hold the same string when the authored identifier
satisfies xRegistry's id grammar. Most do not: a URL such as
`https://fabrikam.example/things/lamp-42` is not a legal xRegistry id. The
model therefore keeps them as separate attributes rather than reusing the
Resource id.
[Section 5.1](#51-wot-identifiers-and-registry-ids) defines how the two
relate.

### 2.3. Thing Description Group

A Thing Description Group contains Thing Descriptions related in an
application-defined way, for example all TDs for a tenant, fleet, or physical
site. This specification places no restriction on which Thing Descriptions a
Group contains.

### 2.4. Thing Model Group

A Thing Model Group contains Thing Models related in an application-defined
way, for example all TMs published by one vendor or for one product family.
This specification places no restriction on which Thing Models a Group
contains.

## 3. WoT Registry Model

The authoritative xRegistry extension models for the WoT Registry are
[model.json](model.json) for SemVer and
[model-incremental.json](model-incremental.json) for incremental.
Their `modelversion` is `0.1` while this remains a working draft. It identifies
the WoT model version independently of the xRegistry Core specification
version in a Registry's `specversion`.

This notation shows the SemVer serialization. An incremental Registry
uses the same collections and additionally exposes the OPTIONAL Version
attribute `compatibilityline` (Section 5.5.2).

```yaml
{
  "specversion": "<STRING>",                       # xRegistry core attributes
  "wotversionprofile": "semver",
  "registryid": "<STRING>",
  "self": "<URL>",
  "xid": "<XID>",
  "epoch": <UINTEGER>,
  "name": "<STRING>", ?
  "description": "<STRING>", ?
  "documentation": "<URL>", ?
  "labels": {
    "<STRING>": "<STRING>" *
  }, ?
  "createdat": "<TIMESTAMP>",
  "modifiedat": "<TIMESTAMP>",

  "model": { ... }, ?

  "thingdescriptiongroups": {                      # ThingDescriptionGroups collection
    "KEY": {                                       # thingdescriptiongroupid
      "thingdescriptiongroupid": "<STRING>",                  # xRegistry core attributes
      "self": "<URL>",
      "xid": "<XID>",
      "epoch": <UINTEGER>,
      "name": "<STRING>", ?
      "description": "<STRING>", ?
      "documentation": "<URL>", ?
      "labels": { "<STRING>": "<STRING>" * }, ?
      "createdat": "<TIMESTAMP>",
      "modifiedat": "<TIMESTAMP>",
      "deprecated": { ... }, ?

      "thingdescriptions": {                       # ThingDescriptions collection
        "KEY": {                                   # thingdescriptionid
          "thingdescriptionid": "<STRING>",                   # xRegistry core attributes
          "versionid": "<STRING>",
          "self": "<URL>",
          "xid": "<XID>",

          #  Start of default Version's attributes
          "epoch": <UINTEGER>,
          "name": "<STRING>", ?
          "description": "<STRING>", ?
          "documentation": "<URL>", ?
          "labels": { "<STRING>": "<STRING>" * }, ?
          "createdat": "<TIMESTAMP>",
          "modifiedat": "<TIMESTAMP>",
          "ancestorid": "<STRING>",
          "versionorigin": "<STRING>",              # authored or generated; server-set
          "contenttype": "<STRING>", ?             # application/td+json; see 4.2
          "format": "<STRING>",                    # MUST be "JSON-LD/1.1"
          "wotid": "<STRING>",                     # the document's authored 'id'
          "derivedfrom": [ "<STRING>" * ], ?       # advisory index of referenced TM wotids
          "license": "<STRING>", ?                 # provenance metadata
          "publisher": "<STRING>", ?
          "standardsbody": "<STRING>", ?
          "canonicalurl": "<URL>", ?
          "maturity": "<STRING>", ?
          "formatvalidated": <BOOLEAN>, ?
          "formatvalidatedreason": "<STRING>", ?
          "compatibilityvalidated": <BOOLEAN>, ?
          "compatibilityvalidatedreason": "<STRING>", ?

          "thingdescriptionurl": "<URL>", ?
          "thingdescription": <ANY>, ?                        # the WoT-TD JSON-LD document
          "thingdescriptionbase64": "<STRING>", ?
          #  End of default Version's attributes

          "metaurl": "<URL>",
          "meta": { ... }, ?

          "versions": { ... }, ?
          "versionsurl": "<URL>",
          "versionscount": <UINTEGER>
        } *
      }, ?
      "thingdescriptionsurl": "<URL>",
      "thingdescriptionscount": <UINTEGER>
    } *
  }, ?
  "thingdescriptiongroupsurl": "<URL>",
  "thingdescriptiongroupscount": <UINTEGER>,

  "thingmodelgroups": {                            # ThingModelGroups collection
    "KEY": {                                       # thingmodelgroupid
      "thingmodelgroupid": "<STRING>",                        # xRegistry core attributes
      "self": "<URL>",
      "xid": "<XID>",
      "epoch": <UINTEGER>,
      "name": "<STRING>", ?
      "description": "<STRING>", ?
      "documentation": "<URL>", ?
      "labels": { "<STRING>": "<STRING>" * }, ?
      "createdat": "<TIMESTAMP>",
      "modifiedat": "<TIMESTAMP>",
      "deprecated": { ... }, ?

      "thingmodels": {                             # ThingModels collection
        "KEY": {                                   # thingmodelid
          "thingmodelid": "<STRING>",                         # xRegistry core attributes
          "versionid": "<STRING>",
          "self": "<URL>",
          "xid": "<XID>",

          #  Start of default Version's attributes
          "epoch": <UINTEGER>,
          "name": "<STRING>", ?
          "description": "<STRING>", ?
          "documentation": "<URL>", ?
          "labels": { "<STRING>": "<STRING>" * }, ?
          "createdat": "<TIMESTAMP>",
          "modifiedat": "<TIMESTAMP>",
          "ancestorid": "<STRING>",
          "versionorigin": "<STRING>",              # authored or generated; server-set
          "contenttype": "<STRING>", ?             # application/tm+json; see 4.4
          "format": "<STRING>",                    # MUST be "JSON-LD/1.1"
          "wotid": "<STRING>",                     # the document's authored 'id'
          "derivedfrom": [ "<STRING>" * ], ?       # advisory index of referenced TM wotids
          "license": "<STRING>", ?                 # provenance metadata
          "publisher": "<STRING>", ?
          "standardsbody": "<STRING>", ?
          "canonicalurl": "<URL>", ?
          "maturity": "<STRING>", ?
          "formatvalidated": <BOOLEAN>, ?
          "formatvalidatedreason": "<STRING>", ?
          "compatibilityvalidated": <BOOLEAN>, ?
          "compatibilityvalidatedreason": "<STRING>", ?

          "thingmodelurl": "<URL>", ?
          "thingmodel": <ANY>, ?                              # the WoT-TM JSON-LD document
          "thingmodelbase64": "<STRING>", ?
          #  End of default Version's attributes

          "metaurl": "<URL>",
          "meta": { ... }, ?

          "versions": { ... }, ?
          "versionsurl": "<URL>",
          "versionscount": <UINTEGER>
        } *
      }, ?
      "thingmodelsurl": "<URL>",
      "thingmodelscount": <UINTEGER>
    } *
  }, ?
  "thingmodelgroupsurl": "<URL>",
  "thingmodelgroupscount": <UINTEGER>
}
```

## 4. WoT Registry

The WoT Registry organizes Thing Descriptions, Thing Models, and their Versions.
It stores both their metadata and their documents.

Implementations of this specification MAY include additional extension
attributes, including the `*` attribute of type `any`.

Groups, Resources, and Versions inherit their Core attributes from the
[xRegistry specification][xRegistry Core].

### 4.1. Thing Description Groups

A Thing Description Group collects Thing Descriptions related in an
application-defined way, without restricting the contained Thing Descriptions.
Its Group Type (`<GROUP>`) name is `thingdescriptiongroup` (singular), and
its collection name is `thingdescriptiongroups`. It has no specific extension
attributes.

Every `thingdescription` Resource MUST reside inside a Thing Description
Group.

Example:

```yaml
{
  # xRegistry top-level attributes excluded for brevity

  "thingdescriptiongroups": {
    "fabrikam.factory-floor-01": {
      "thingdescriptiongroupid": "fabrikam.factory-floor-01",
      # other xRegistry Group-level attributes excluded for brevity

      "thingdescriptionsurl": "https://example.com/thingdescriptiongroups/fabrikam.factory-floor-01/thingdescriptions",
      "thingdescriptionscount": 12
    }
  },
  "thingdescriptiongroupsurl": "https://example.com/thingdescriptiongroups",
  "thingdescriptiongroupscount": 1
}
```

### 4.2. Thing Description Resources

A Thing Description Resource contains one or more Versions, each holding a
complete WoT-TD 1.1 JSON-LD document. Inside Thing Description Groups, its
Resource Type (`<RESOURCE>`) name is `thingdescription` and its collection
name is `thingdescriptions`.

In the SemVer profile, Thing Description Resources MUST use Core [`versionmode`][Core versionmode]
value `semver` and [`singleversionroot`][Core singleversionroot]
value `true`, as specified in [Section 1.3](#13-versioning). Core derives
`ancestorid` by SemVer precedence and enforces one root
([`ancestorid`][Core ancestorid]).

The Version-level `versionorigin` attribute is REQUIRED, read-only, and uses
the strict enumeration `authored` or `generated`. In the SemVer profile,
[Section 1.3](#13-versioning) assigns `versionid` from `version.instance`
when valid, distinguishes generated IDs from rejected values, and
preserves the original document bytes. The incremental profile assigns
IDs as described in [Section 5.5](#55-incremental-profile).

The `format` attribute of a `thingdescription` Resource Version MUST be
`"JSON-LD/1.1"`. [model.json](model.json) declares the `format` enumeration
as `strict`, so a registry rejects any other value.

The `contenttype` of a `thingdescription` document MUST be
[`application/td+json`][WoT-TD media] or another media type that the
deployment has explicitly registered for WoT documents.

`contenttype` is client-supplied and determines the media type used to serve
the stored bytes through the document view
([Section 1.4](#14-document-store)). A Registry MUST NOT serve a stored
document under a client-supplied media type that would interpret it as active
content, such as `text/html`, `image/svg+xml`, or `application/xhtml+xml`.
A Registry MUST either reject such a write or serve the document under the
media type this section requires.

WoT tooling dereferences a Version's document-view URL directly. When serving
a document it did not author over HTTP, a Registry SHOULD return
`X-Content-Type-Options: nosniff` or serve that document from an HTTP origin
separate from any Registry user interface. See [Section 7](#7-security).

The `wotid` attribute is REQUIRED and holds the document's authored WoT
identifier, distinct from the `thingdescriptionid`. See
[Section 5.1](#51-wot-identifiers-and-registry-ids). The OPTIONAL
`derivedfrom` attribute lists the `wotid`s of the Thing Models this Thing
Description extends or composes. It is a producer-supplied index rather than
an authority over the document's own references, as
[Section 5.2](#52-preserving-customer-documents) describes.

All Versions of a single Thing Description Resource MUST adhere to the
semantic rules of the Thing Description's [`compatibility`][Core compatibility]
attribute, if specified.

Implementations of this specification SHOULD use the xRegistry default
algorithm for generating new `versionid` values.

The default Version is the one served when no Version is named. It MUST be
determined by the xRegistry Core rules, including the Resource's
[`defaultversionsticky`][Core defaultversionsticky] setting. A deployment MAY
use that setting to pin the default to a Version other than the newest.
This specification does not redefine default-Version selection. See
[Version IDs][xRegistry version-ids] for more information.

### 4.3. Thing Model Groups

A Thing Model Group is a collection of Thing Models related in some
application-defined way, typically by vendor or product family. Its Group Type
name is `thingmodelgroup` (singular), and its collection name is
`thingmodelgroups`. It has no specific extension attributes.

Every `thingmodel` Resource MUST reside inside a Thing Model Group.

### 4.4. Thing Model Resources

A Thing Model Resource groups one or more `versions`, each holding a concrete
WoT-TM 1.1 JSON-LD document. Within Thing Model Groups, its Resource Type
name is `thingmodel` and its collection name is `thingmodels`. Each
`thingmodel` represents the logical grouping.

The `format` attribute of a `thingmodel` Resource Version MUST be
`"JSON-LD/1.1"`, enforced by the same `strict` enumeration used for
`thingdescription`. The `contenttype` MUST be
[`application/tm+json`][WoT-TM media] or another media type that the
deployment has explicitly registered for WoT documents. The constraint on
serving stored bytes as active content in
[Section 4.2](#42-thing-description-resources) also applies.

The `compatibility`, `versionid`, `versionorigin`, and
[`ancestorid`][Core ancestorid] rules for Thing
Models are defined in [Section 1.3](#13-versioning), subject to Core's
[`compatibility`][Core compatibility] and
[`versionid`][Core versionid] semantics. The Version-level `versionorigin` is
a REQUIRED string with the strict enumeration `authored` or `generated`, and is
read-only. The SemVer model declares `compatibility` under `metaattributes`, with
`required: true` and `default: backward`, as Core requires for an attribute
with a default.

The `wotid` attribute is REQUIRED on a `thingmodel` and holds the document's
authored WoT identifier, which is distinct from the `thingmodelid`. Where a
Thing Model extends another through a `tm:extends` link relation, references
one through `tm:ref`, or composes one through `tm:submodel`, the referenced
Thing Models' `wotid`s SHOULD be listed in `derivedfrom`. For the proposed
versioned-reference vocabulary, see the [proposal][WoT reference proposal].

### 4.5. Formats

Both Thing Descriptions and Thing Models are serialized as JSON-LD 1.1
documents, so both use the
[core specification's `format`](../../../core/spec.md#format-attribute) identifier
`JSON-LD/1.1`. The Resource type (`thingdescription` versus `thingmodel`) and
the `contenttype` attribute distinguish the two document classes; `format`
does not.

#### 4.5.1. WoT Thing Description

- Format identifier: `JSON-LD/1.1`
- `contenttype`: [`application/td+json`][WoT-TD media], subject to the
  deployment rules in [Section 4.2](#42-thing-description-resources).
- Document: a JSON-LD 1.1 document conformant with
  [W3C WoT Thing Description 1.1][WoT-TD-1.1].
- The document's `@context` MUST include
  `https://www.w3.org/2022/wot/td/v1.1`.
- A URI-reference pointing to a TD MAY use a JSON-Pointer
  ([RFC 6901](https://www.rfc-editor.org/rfc/rfc6901)) fragment to deep-link
  into a particular property, action, or event affordance, for example,
  `…/thingdescriptions/lamp-42#/properties/status`.

#### 4.5.2. WoT Thing Model

- Format identifier: `JSON-LD/1.1`
- `contenttype`: [`application/tm+json`][WoT-TM media], subject to the
  deployment rules in [Section 4.4](#44-thing-model-resources).
- Document: a JSON-LD 1.1 document conformant with
  [W3C WoT Thing Model 1.1][WoT-TM-1.1].
- The document's `@context` MUST include
  `https://www.w3.org/2022/wot/td/v1.1` and the document's top-level
  `@type` MUST include `tm:ThingModel`.
- Deep-linking through JSON-Pointer fragments is permitted, as for TDs.

### 4.6. Provenance and Selection Metadata

Tools and autonomous agents need explicit metadata to choose among documents
describing similar Things rather than inferring their provenance from titles
or naming conventions. Each Version of a `thingdescription` or `thingmodel`
Resource can carry the following OPTIONAL attributes:

| Attribute | Type | Meaning |
|---|---|---|
| `license` | string | The license the document is offered under, as an [SPDX][SPDX] license expression or a URL |
| `publisher` | string | The organization that published the document |
| `standardsbody` | string | The standards organization that defines or endorses the document, where one does |
| `canonicalurl` | url | The canonical upstream location of the document, where it is also published outside this registry |
| `maturity` | string | One of `Standard`, `Vendor`, `Community`, or `Experimental` |

A Consumer choosing between candidate Thing Models SHOULD prefer, in order:

1. `maturity` of `Standard` accompanied by a `standardsbody`.
2. `maturity` of `Vendor`, or `maturity` of `Standard` with no `standardsbody`.
   The two rank equally: marking a document `Standard` does not make it an
   interoperable standard.
3. `maturity` of `Community`.
4. `maturity` of `Experimental`.
5. No `maturity` at all.

If the choice remains open, the Consumer SHOULD prefer the document whose
`canonicalurl` it already trusts. [model.json](model.json) declares the
`maturity` enumeration as `strict`, so a Registry rejects values outside this
set. A Consumer that nonetheless encounters one, for example from a federated
Registry, MUST NOT rank it above `Experimental`. This specification defines
no precedence for it.

These attributes are advisory and unverified assertions by the Resource's
writer about the document's origin and maturity. This specification defines
no mechanism for a Registry to validate a `publisher` or `standardsbody`
claim. A Registry MUST NOT be assumed to have validated one.

A Consumer MUST NOT treat these attributes as authenticated provenance. The
preference order only breaks ties among documents the Consumer already trusts,
whether by Group, writer identity, or an out-of-band signature. It MUST NOT be
used to establish trust in a document from an untrusted writer.

One `wotid` MAY legitimately match several Resources written by different
parties ([Section 5.3](#53-lookup)), so a Consumer can face this choice.
See also [Section 7](#7-security).

These attributes do not determine WoT identity. A Registry MUST NOT infer
that two documents share a WoT identity because their provenance attributes
agree, or that their WoT identities differ because those attributes differ.
`wotid` identifies the Thing or model, not an exact Version's bytes or
a unique Resource across Groups.

Each Version carries these attributes alongside the document they describe,
just as it carries `format` and `wotid`. The xRegistry Core rules for writing
and updating Version attributes apply.

## 5. Identity and Resolution

### 5.1. WoT Identifiers and Registry Ids

xRegistry gives every entity an id — a `thingdescriptionid` or
`thingmodelid` for a Resource — and an [`xid`][xRegistry Core], the stable
path those ids form within the registry. Each entity id is constrained to
[RFC 3986][RFC3986] `unreserved` characters plus `:` and `@`, starting with a
letter, a digit, or `_`, at most 128 characters long, and unique
case-insensitively within its parent. A WoT identifier is the value of a TD's
or TM's `id` member: a URI, most often a URN such as `urn:fabrikam:lamp:42`,
but equally a URL such as `https://fabrikam.example/things/lamp-42`.

These identifiers serve a similar purpose but follow different grammars.
`https://fabrikam.example/things/lamp-42` is not a valid entity id or `xid`
component. The Thing author supplies the WoT identifier; the Registry assigns
the `xid`. Where an authored identifier satisfies the id grammar, a client MAY
use it as the Resource id. A Registry cannot rely on that choice.

This specification therefore does not equate them, and does not define a
mapping between them:

> A `thingdescription`'s `wotid` is its document's identity in the WoT
> identifier space ([Section 2.2.3](#223-wot-identifier)). Its
> `thingdescriptionid` is the Resource's id *within this registry* and is
> chosen by the client that creates the Resource, subject to the xRegistry
> Core id rules and to whatever further naming constraints the deployment
> imposes. This specification mandates no derivation between them. The same
> applies to a `thingmodel`'s `wotid` and `thingmodelid`.

A client creating a Resource therefore chooses its id the same way it chooses
a Group id:

- It names the id in the request path.
- It supplies the id in the request body.
- It omits the id and lets the registry assign one under the xRegistry
  Core rules.

This specification does not dictate this choice, and later resolution does not
depend on it. A Consumer holding a WoT identifier queries the first-party
`wotid` attribute ([Section 5.3](#53-lookup)) to find the Resource rather than
reconstructing its path.

A deployment MAY derive its Resource ids from `wotid` values by a convention
of its own. The [OpenUSD Artifact Registry][OpenUSD Draft] working draft
defines one such construction. No convention is mandated by this
specification, and a Consumer MUST NOT assume that an id it did not assign
was produced by one.

A `wotid` MUST NOT encode a compatible revision of the document it names. In
the SemVer profile a Thing Model's major version MUST be included in that stable identity, for
example `urn:fabrikam:lamp:v1` or `https://fabrikam.example/tm/lamp/v1`. Minor
and patch revisions are carried by `versionid` and `version.model`, not
appended to the identifier. No particular spelling of the major-version token
is mandated.

When a document is revised compatibly, its `wotid` and Resource id MUST
remain unchanged, and a new Version is created under the same Resource. A
SemVer Thing Model breaking revision uses a distinct major-version `wotid` as
specified in [Section 5.1.1](#511-breaking-changes-and-successor-identifiers).
A Thing Description major revision remains under its existing `id` and
`wotid`. A new TD identifier names a different concrete Thing.

A `wotid` is REQUIRED, and the rule for populating it depends on the document:

- Where the document carries an `id` member, `wotid` MUST equal it verbatim.
  A registry that parses the stored document MUST reject a write whose
  `wotid` differs from that `id`, rather than storing two identities for one
  document. A registry that does not parse the document cannot detect the
  disagreement. Both types of registry MUST NOT rewrite either value to
  resolve the disagreement, because
  [Section 5.2](#52-preserving-customer-documents) forbids editing the
  document.
- Where the document carries no `id` member — which
  [WoT-TD 1.1][WoT-TD-1.1] permits for TDs served from a fixed URL, and which
  is common for TMs — the Producer MUST supply a `wotid` at write time, and
  that supplied value is thereafter the document's identity in this registry.
- A registry MUST reject a write that supplies neither an `id` member nor a
  `wotid`, rather than inventing one, because an invented identifier is not
  stable across registries.

[Decision 4](decisions.md#4-wotid-is-a-required-model-attribute)
records that whether a future revision ought to define a derivation for the
second case is not yet settled.

#### 5.1.1. Breaking Changes and Successor Identifiers

This subsection applies to SemVer. Incremental compatibility boundaries
follow Section 5.5.2.

A breaking Thing Model change MUST use a new major-version `wotid` and a
distinct Resource. The predecessor's `wotid` MUST NOT be modified. A major
Thing Description revision remains a Version of the same concrete Thing under
the same `id`, `wotid`, and Resource. A distinct TD `id` and `wotid` identify
a different concrete Thing, not a breaking revision of the existing one.

The predecessor Resource MUST be marked with Core's
[`deprecated`][xRegistry deprecated] attribute, whose `alternative` MUST be
the successor Resource's URL. Its Versions MUST remain retrievable.
Deprecation alone MUST NOT cause the resolver to redirect a reference to the
successor. A Consumer MAY inspect the successor and explicitly choose to adopt
its different identity.

| | Predecessor | Successor |
|---|---|---|
| `wotid` | `urn:fabrikam:lamp:v1` | `urn:fabrikam:lamp:v2` |
| `thingmodelid` | `urn.fabrikam.lamp.v1` | `urn.fabrikam.lamp.v2` |
| Versions | `1.0.0`, `1.1.0`, `1.1.1` | `2.0.0` |
| `deprecated` | `alternative` names the successor URL | absent |

### 5.2. Preserving Customer Documents

Registries store existing Thing Models and Thing Descriptions as authored.
A vendor, standards body, or toolchain can supply a document, and artifacts
outside the Registry can already reference it.

- A registry MUST store the WoT document byte-for-byte as supplied, apart
  from transformations the client explicitly requested. Those transformations
  do not authorize the identifier rewriting prohibited below.
- A registry MUST NOT rewrite the document's `id` member, its `links[].href`
  values, its `tm:extends` or `tm:ref` targets, or any other identifier
  internal to the document, into registry-specific identifiers.
- A retrieval of a stored Version through the document view MUST return the
  exact bytes supplied. Re-serializing the document on retrieval —
  reordering members, re-indenting, or normalizing its JSON-LD — is not
  permitted.

Rewriting is incompatible with these documents for three reasons:

- A TM published by a standards body is referenced by `id` from artifacts
  outside the registry, and rewriting the `id` would break those references
  even though the registry would still serve its copy as the standard document.
- A TD's `tm:extends` target resolves in the WoT identifier space, so a
  rewritten target no longer matches what any other WoT tool would look for.
- A document copied between two registries would acquire two different
  identities for the same bytes, so neither registry could tell the copies
  apart from distinct documents.

The Registry identifies the Resource through its `thingdescriptionid` or
`thingmodelid` and the resulting `xid`. An exact Version address identifies
a particular document revision. The Version's metadata carries its WoT
identity in `wotid`, which preserves the authored `id` when present, and
can index WoT references in `derivedfrom`. Keeping the identifier spaces
separate lets the document round-trip unchanged.

Where a registry wants the TD-to-TM link to be traversable without parsing the
document, it records the referenced Thing Models' *authored* identifiers in
the `derivedfrom` attribute. `derivedfrom` holds the target TMs' `wotid`
values, not `xid` values or the literal syntax of a relative reference.
Identify the target TM under the applicable reference rules before comparing
its `wotid` to this index.

`derivedfrom` is a producer-supplied *index* of the document's references, not
an authority over them. A registry MAY verify that it matches the
`tm:extends`, `tm:submodel`, `tm:ref`, and `links[].rel="type"` targets in the
stored document, and SHOULD reject a write where the two disagree. Where a
registry does not verify, the document is authoritative.

When making a trust, allow-list, or compliance decision about a document's
lineage, a Consumer MUST derive that lineage from the document itself and
MUST NOT rely on `derivedfrom` alone.

### 5.3. Lookup

A Consumer can resolve a WoT identifier to a stored document in two ways. The
identifier typically comes from a `tm:extends` link, a `tm:ref`, another
`links[].href`, or a message attribute.

**By path.** If the Consumer already has the Resource's Group and id, or
follows a stored `self` URL, it addresses the Resource directly:

```
/thingmodelgroups/<thingmodelgroupid>/thingmodels/<thingmodelid>
```

**By `wotid`.** Otherwise, the Consumer queries the `wotid` attribute. This is
the usual case because WoT documents reference one another by authored
identifier rather than by registry path:

```
GET /thingmodelgroups/Fabrikam.Lighting/thingmodels?filter=wotid=urn:fabrikam:lamp:v1
```

An implementation SHOULD avoid a full scan for each lookup, for example by
indexing `wotid` on `thingdescriptions` and `thingmodels`. Returning the
matching Resources still takes work proportional to the size of the result.

A `wotid` SHOULD be unique within a Group, so that a Group-scoped query for
one identifies a single Resource. Across Groups a `wotid` MAY repeat — the
same vendor TM legitimately appears in two tenants' Groups. A
registry-wide query MAY therefore match more than one Resource. Naming a
Group narrows the query but does not guarantee a unique match.

A Registry-wide query MUST return every matching Resource rather than an
arbitrary one of them. A Consumer can query the relevant Groups using Core
operations; the Group-scoped example does not define a root `thingmodels`
collection. [Section 4.6](#46-provenance-and-selection-metadata) governs
how a Consumer chooses among candidate TMs.

Version selection is separate from the *identifier*. The URL carries the
selection through the `versions` collection:

| Intent | Request |
|---|---|
| Default Version | `<resource-url>`, which serves its default Version |
| A specific Version | `<resource-url>/versions/<versionid>` |
| Enumerate Versions | `<resource-url>/versions` |

`<resource-url>` above is the Resource's [`self`][xRegistry self] URL with
the `$details` suffix removed. For HTTP Resource or Version metadata,
append `$details` at the end of the complete Resource or Version URL.
`<resource-url>/versions/2$details`, for example, requests Version `2`'s
metadata, and `<resource-url>/versions/2` requests its document. See
[Section 1.4](#14-document-store).

A request to the Resource URL without a Version returns the Core default,
even when [`defaultversionsticky`][Core defaultversionsticky]
is true. A registry MUST serve that default
when no Version is named.

For WoT document reference resolution, a resolver MUST use
[Section 5.4](#54-versioned-reference-resolution), not lexical id order,
publication time or an assumption that the default satisfies the reference.

Callers SHOULD NOT fold the identifier and version into one opaque string.
When carrying both through a transport, such as message headers, a caller
SHOULD use separate values, for example a
`wotid` header and a `versionid` header, rather than a single compound token
like `urn:fabrikam:lamp@3` that every recipient has to take apart. The
identifier stays a WoT identifier, and the version stays a `versionid` the
recipient can put straight into a URL.

#### 5.3.1. CloudEvents WoT Source Resolution

CloudEvents for a TD in this Registry MUST follow the proposed
[CloudEvents WoT profile][CE WoT profile]
([CloudEvents PR 1406](https://github.com/cloudevents/spec/pull/1406)). The
profile requires `describedby` and selects the TD through a Descriptor entry
of class `thingdescription`. The publication profile selects that entry by
name or, without a name, by the unique entry of that class. `source` and
`subject` retain their CloudEvents Core meanings; neither a `wotid` nor a
`wotversion` source query selects the TD or provides a fallback.

For a TD in this Registry, the Descriptor Publisher SHOULD use the document
URL of an explicit Thing Description Version as the entry's `url`. A Resource URL
returns the current Core default Version, including a sticky default, and
therefore does not identify a stable view.

The Document bytes of the referenced Version MUST be the resolved TD view.
Producing or publishing the view MUST NOT overwrite or rewrite stored authored
source bytes ([Section 5.2](#52-preserving-customer-documents)). When the
resolved view differs from the authored source, the Producer MUST publish the
resolved bytes as a publication Version with its own exact document address.
It MUST retain the authored source bytes separately. The Descriptor Publisher
MUST NOT reference an authored source Version whose bytes do not represent
the resolved view.

When the resolved view or its source closure changes, the Producer MUST create
a new publication Version according to [Section 1.3](#13-versioning) and MUST
NOT reuse an authored instance version for the changed view. The Descriptor
Publisher MUST NOT change the resolved view at a previously published Version
URL and MUST publish a new Descriptor Version that references the new publication
Version. These rules apply to publication Versions referenced by this profile,
not to all xRegistry Versions.

The entry's OPTIONAL `affordanceselector` is a plain JSON Pointer selecting a
property, action or event in the referenced Version's resolved Document bytes,
not Registry metadata or an unresolved source document. Omission selects the
whole Thing. A Consumer MUST report a missing, invalid, ambiguous or unavailable
Descriptor, TD or selector rather than substitute another description.

A Consumer MAY retrieve the published resolved TD or reconstruct the same
logical view from a complete pinned source closure and the applicable
resolution rules. If the closure cannot establish that result, the Consumer
MUST obtain the published view or report failure. It MUST NOT substitute live
dependencies or a pointer into an unresolved source document.
[Section 5.4.4](#544-publication-closure) records unresolved closure mappings;
the existing closure extension and schema alone do not establish that such
reconstruction is possible.

The [Publication byte checks](../../publication/spec.md#byte-descriptors)
apply to captured document bytes and the closure extension. They do not
replace the authored projection source digest check in
[Section 5.4.4](#544-publication-closure).

The CloudEvents `type` identifies the payload contract, not the Registry
Resource or TD Version; its revision is independent of `version.instance`,
`version.model`, `versionid`, and the Descriptor Version.

The [CloudEvents samples](samples/cloudevents.json) address an affordance and
the whole TD through Descriptors that reference an explicit Version.

### 5.4. Versioned Reference Resolution

The resolver uses the target's trusted profile, not the referring document's
profile or the spelling of a version. [Section 1.3](#13-versioning) defines
SemVer Version assignment; [Section 5.5](#55-incremental-profile) defines
Incremental assignment and compatibility-line claims.

The following four records are informative descriptions of information already
used by the resolver. They do not define new document or Registry fields:

- **Revision:** a TD or TM revision in an authorized Resource sequence, with
  its logical identity, stored `versionid`, authored version, profile,
  `versionorigin`, compatibility line when applicable, and byte digest.
  The authored version and the stored id can differ.
- **Requirement:** what one reference asks for: its operator or source
  media type, target and any fragment, effective minimum version
  (floor), explicit line if applicable, and any declared projection source
  byte digest.
- **Request:** how the caller wants to resolve the target: live selection,
  raw exact replay, or snapshot composition. Source authorization,
  prerelease policy, replay pins, and publication selection are caller inputs,
  not part of the authored requirement.
- **Result:** the exact target and the evidence used to identify it. A
  snapshot binding identifies the captured occurrence; the manifest identifies
  the publication in which the binding was verified.

#### 5.4.1. Floors and Pins

The table gives the permitted requirements for each authored occurrence.
An author MAY supply a floor, but MUST NOT supply a version range. In the
Incremental column, the line selector is `uav:compatibilityLine` and the only
permitted floor term is `uav:minVersion`.

| Authored occurrence | Target kind | SemVer requirement | Incremental requirement for live selection or snapshot composition |
|---|---|---|---|
| `tm:extends` or `tm:submodel` link, or object containing an ordinary `tm:ref` | TM | OPTIONAL `tm:minVersion` or `uav:minVersion`; no major cap. | Explicit line; OPTIONAL numeric floor. |
| TD link with `rel: "type"` | TM | OPTIONAL `tm:minVersion` or `uav:minVersion`, combined with the TD's `version.model` as specified below; no major cap. | Explicit line; OPTIONAL numeric floor. `version.model` supplies no implicit floor. |
| `td:extends` or `td:subthing` link, or object containing an ordinary `td:ref` | TD | OPTIONAL `td:minVersion` or `uav:minVersion`; the TD major cap applies only if there is a floor. | Explicit line; OPTIONAL numeric floor. |
| Experimental projection source-manifest entry (Section 5.4.4) | TD or TM, from the entry's expected media type | OPTIONAL kind-correct `tm:minVersion` or `td:minVersion`, or `uav:minVersion`; the major cap applies only to a TD source with a floor. | Explicit line; OPTIONAL numeric floor. |

Consumers MUST recognize floor and line members by expanded IRI under the
active [JSON-LD context][JSON-LD], including any term-scoped context. The
`uav` terms expand under `http://opcfoundation.org/UA/WoT-Binding/`. For
example, a different prefix mapped to that same namespace does not change
the expanded IRI of `uav:minVersion`. These terms do not add operators or
change the allowed locations of the WoT links and reference members.
An affordance selector is not a projection source entry. The root is not a
reference: a root line describes the containing Incremental revision
(Section 5.5.2) and is never inherited by its dependencies. The root does
not take an explicit floor. Values inside opaque payloads such as `default`
and `examples` are not reference occurrences.

A floor MUST be a string and a line MUST be an absolute URI string.
`null` is not omission. More than one explicit floor term on an occurrence
is `invalid-floor`, even when the values agree. A floor term for the wrong
target kind is also `invalid-floor`.

- A SemVer floor MUST be a SemVer 2.0.0 string without build metadata
  and MUST NOT have the generated `0.0.0-N` form. Core's 128-character
  [id limit][Core id constraints] does not apply to floors. A line is
  not valid on a reference to a SemVer target.
- An Incremental floor MUST be a canonical positive decimal integer string
  (`[1-9][0-9]*`) in the target sequence. A generated integer is a normal
  candidate and MAY be used as a floor. An Incremental target has no
  implicit floor, major cap, or prerelease filter. A portable SemVer floor
  term is not valid for an Incremental target.

For SemVer, a Version MUST be at or above the effective floor if one is
present. A TD floor additionally requires the Version's major to equal the
floor's major, even for major zero. For example, a TD floor of `0.3.0`
admits `0.4.0` but excludes `1.0.0-rc.1` even if prereleases are allowed.
A TD reference with no floor can cross majors. A TM floor has no such cap:
a breaking TM major has a different `wotid`, not another candidate for the
same reference. Neither version field of a referring TD or of a projection
plan supplies a floor for TD-to-TD references or projection sources.

For TD type links, determine the target profiles before interpreting the
TD's `version.model`. It is an implicit floor for the SemVer-target links
only. If the TD has `version.model` and more than one SemVer-target link,
each such link MUST have an explicit floor. If one lacks it, SemVer type-link
resolution MUST report `ambiguous-floor`, even when the selected SemVer
link has its own floor. Report that ambiguity before validating individual
floor values. Otherwise use the greater of the implicit and explicit floors
by SemVer precedence, or the only floor present. Without `version.model`,
each SemVer link uses its own floor if present and omission is not
ambiguous. Incremental links independently require their own line.

A Consumer MAY retain the resolution result outside the document and later
supply a `versionid` or digest as a replay pin. A request MUST NOT supply
both. Authored references MUST NOT carry Registry replay pins. A projection
source's declared byte digest is a separate check on the selected source
(Section 5.4.4), not a request to choose a Version by digest.

When the resolver derives an implicit floor for a SemVer-target link from
`version.model`, a present value MUST satisfy the SemVer floor rules above.
An invalid value MUST produce `invalid-version`. Core's 128-character ID
limit does not apply to this floor.

<a id="553-reference-selection-and-replay"></a>

#### 5.4.2. Resolver Algorithm

For an external live or raw replay request, the caller MUST select an
authorized Registry and Group scope that identifies one Resource by `wotid`
([Section 5.3](#53-lookup)). Even a Group-scoped lookup can require
disambiguation. Find that Resource before processing a pin or deriving
requirements. If it does not exist, return `not-found`. A deprecated
Resource remains eligible; the resolver MUST NOT follow its
`deprecated.alternative` as a substitute. Compare Versions only within the
selected authoritative sequence. Live candidates MUST be Versions of a
conforming Resource of the expected target kind.

| Request | How it selects a Version | What the resolver MUST check |
|---|---|---|
| Live selection | Derive the requirement, then use the Core sticky `defaultversionid` if sticky. Otherwise select the highest eligible Version by SemVer precedence or Incremental numeric order. | Apply the target-kind and profile rules in Section 5.4.1. A sticky choice bypasses SemVer prerelease filtering only; if missing, return `not-found`, or if incompatible, return `unsatisfied`. With no sticky default and no eligible Version, return `unsatisfied`. Do not retry with another Resource or Version. |
| Raw exact replay | Use the caller's `versionid` or digest pin in the authorized Resource. If the digest matches multiple Versions, select the highest matching Version under the known target profile, irrespective of line. | Verify identity, authority and bytes, and any retained expectations used to verify the replayed revision. Do not derive or apply the authored floor or line, TD major cap, prerelease filter, or sticky default. Return `not-found` for a missing named Version or `pin-mismatch` for a digest with no match. Do not retry as live selection. |
| Snapshot composition | Open the supplied channel once, or verify the exact snapshot and its manifest. For an external occurrence, obtain the exact captured binding under Section 5.4.4 before testing acceptance. | Verify the bound revision's identity, authority and bytes. Check that revision against the authored requirement and applicable caller acceptance policy. Return `unsatisfied` if the revision fails the floor, line, major cap, or applicable prerelease policy. Do not retry with a live target, another bound revision or digest match, or another snapshot. Incomplete closure is not a successful composition. |

Ordinary Resource retrieval still serves the [Core default][Core defaults].
The resolver uses [`defaultversionsticky`][Core defaultversionsticky] for
live selection only. In manual mode the Core default need not be the highest
numeric Version. For live selection and snapshot composition, a SemVer
prerelease, including a generated id, is ineligible unless the caller sets
`allowPrerelease` or the effective floor is a prerelease. Only a sticky
default in live selection bypasses this filter. The filter does not weaken
the floor or TD major cap. An Incremental candidate MUST have an accepted claim
for the requested line and meet any numeric floor.

For `tm:ref` and `td:ref`, resolve the URI-reference against the
containing document's base URI and remove the fragment before lookup.
In snapshot composition, use the captured source base
([Section 5.4.4](#544-publication-closure)), not the URI of a local copy.
If the result identifies the containing document, the reference is
document-local. Check the containing revision itself, without a Resource
lookup, pin, or substitution. For SemVer and a local floor, use that
revision's authored `version.model` for `tm:ref` or `version.instance`
for `td:ref`. A missing authored value is `unsatisfied` and an invalid
one is `invalid-version`.
The TD major cap still applies. For Incremental, use the containing
Version's trusted line and Version ID. Apply a valid fragment after selecting
the document.

A successful resolution MUST return `(wotid, versionid, contentdigest, origin)`.
`origin` identifies the Registry that supplied the stored bytes and
`contentdigest` is their digest, not a manifest or closure digest.

Raw replay does not validate the referring document. When validation or
composition uses the retrieved content, it MUST still apply the document and
reference rules for that operation. A pin cannot make invalid authored
syntax valid. Core-only storage does not establish that a document's
references are valid.

For example, a TD with `version.model: "2.3.0"` has a type link to the TM
`urn:example:pump-model:v2`. With revisions `2.2.0`, `2.3.0`, and `2.4.0`
available and no sticky default, live selection chooses `2.4.0`. A raw
pin for `2.2.0` returns that revision. Composition with a snapshot that
binds `2.2.0` rejects it as `unsatisfied`; a snapshot that binds `2.3.0`
can satisfy the requirement without replacing it with `2.4.0`.

#### 5.4.3. Errors and Test Vectors

| Error | Meaning |
|---|---|
| `not-found` | Resource, pinned Version, or sticky default is absent. |
| `pin-mismatch` | No Version matches the caller's replay digest, or selected projection source bytes do not match their declared digest. |
| `unsatisfied` | No live candidate is eligible, or the selected, containing, or bound revision fails an applicable floor, line, major cap, or prerelease check. |
| `ambiguous-floor` | A TD has `version.model` and more than one SemVer-target type link, at least one without its own floor. |
| `invalid-floor` | Competing floor terms appear on one occurrence, or the term is not valid for the target kind or profile. |
| `invalid-line` | A line is not a valid absolute URI string, is not valid at that location, or is supplied for SemVer. |
| `compatibility-required` | An Incremental reference checked by live selection or snapshot composition lacks an explicit line. |
| `unknown-profile` | Trusted metadata does not establish a recognized target profile for live selection, snapshot acceptance, or ranking multiple replay digest matches. |
| `version-mismatch` | A supplied publication `versionid` disagrees with the authored or generated assignment. |
| `invalid-version` | A floor, local authored version, or publication version violates the applicable version rules. |
| `inconsistent-publication` | The root line and authorized Version metadata disagree, or trusted publication data identifies conflicting bytes or fixed metadata for the same source revision. |
| `closure-incomplete` | The manifest digest does not match, or necessary closure data, a binding, or bound content is absent or unsupported. |

These names identify domain outcomes, not replacements for Core's protocol
error envelopes or its [`versionid`][Core versionid]
constraints. The
[canonical resolution vectors](tests/resolution/README.md) define portable
SemVer resolver inputs and expected outcomes, including write-side version
assignment.

#### 5.4.4. Publication closure

The requirements below define WoT closure data and its reference mapping.
The xRegistry Publication working draft defines
[opening a channel](../../publication/spec.md#opening-a-channel),
[manifest and byte integrity](../../publication/spec.md#manifest-and-integrity),
and [domain closure](../../publication/spec.md#domain-closure-and-compatibility).
The [publication design](../../publication/design/design.md#a-complete-wot-publication)
is informative. Passing the closure schema alone does not establish that a
pinned WoT view is reconstructible.

A WoT publication that claims domain-complete closure MUST include the
`http://opcfoundation.org/UA/WoT-Binding/publication-closure/1` extension as
a REQUIRED manifest extension. Its document format is
`wot-publication-closure/1`, as defined by the
[closure schema](schemas/publication-closure.schema.json). The extension does
not change the authored WoT documents or their reference semantics.

The closure's `entries` array identifies the starting Version documents.
The Producer follows the domain closure rules above to check reference
occurrences reachable from those entries. Each `entries` item, binding
`source`, and binding `target` MUST be an exact Version XID in the
captured Registry view. A target MUST identify one associated Version
document, not a Resource XID, default-Version alias, WoT identifier or URL.
The closure document does not add a target-kind field or authorize a
substitute for the bound Version.

A Producer MUST derive the closure from the captured source document bytes,
not from the binding list. Each in-scope external reference occurrence in the
closure MUST have exactly one binding to its exact target Version. The binding's
`source`, `pointer`, `operator`, and `href` MUST identify that occurrence and
preserve its authored reference. A Consumer MUST verify those values against
the captured source bytes and MUST NOT resolve a missing binding against a
live Registry, select a default Version, or replace the target with a newer
Version.

The binding key MUST be `(source, pointer)`. Source identity follows Core's
XID rules; pointer comparison MUST be case-sensitive. `pointer` MUST be an
RFC 6901 JSON Pointer into the original captured JSON document, not a
URI-fragment pointer or a pointer into expanded or resolved JSON-LD.
For a `links` occurrence it MUST identify the link object. For an ordinary
`tm:ref` or `td:ref` it MUST identify the object containing that member.
For a projection source it MUST identify the source-manifest entry.
JSON Pointer escaping applies to the actual authored member names, including
an alternative JSON-LD prefix. Array indexes MUST use their RFC 6901 spelling.

Each reachable in-scope external occurrence MUST have exactly one binding.
A Consumer MUST reject duplicate binding keys, including duplicates with the
same target, and MUST reject bindings to local, unreachable, or nonexistent
occurrences. Two different occurrences referring to the same target remain
distinct bindings. If one pointed-to object contains several in-scope
reference members, including aliases for the same expanded member, a
Consumer MUST reject it as an ambiguous occurrence rather than choosing one.
The binding's `href` MUST equal the source reference's JSON string value,
including its fragment, without URI resolution or percent decoding.

`operator` MUST use the canonical string in the following table. These
strings are closure labels, not terms expanded through a context on the
closure document:

| Source occurrence | Canonical `operator` |
| --- | --- |
| Link with `rel: "tm:extends"` | `tm:extends` |
| Link with `rel: "tm:submodel"` | `tm:submodel` |
| Ordinary member expanding to `https://www.w3.org/2019/wot/tm#ref` | `tm:ref` |
| Link with `rel: "td:extends"` | `td:extends` |
| Link with `rel: "td:subthing"` | `td:subthing` |
| Ordinary member expanding to `https://www.w3.org/2019/wot/td#ref` | `td:ref` |
| TD link with `rel: "type"` | `type` |
| Experimental projection source-manifest entry | `https://raw.githubusercontent.com/marcschier/wot-thing-description/main/proposals/wot-projections/context.experimental-v1.jsonld#projects` |

The projection operator IRI is a label, not a URL a Consumer fetches.
Use the context artifact from the pinned proposal below.

A Consumer MUST compare canonical operators as exact strings and MUST reject
unknown or mismatched operators. Member names MUST be interpreted under
their captured effective JSON-LD contexts; the literal prefix alone does not
establish a member's meaning. Link relations in the table are literal `rel`
values. A prefix declaration MUST NOT turn another relation string into one
of these values. In particular, `type` is a link relation, not `@type` or an
IRI formed by appending `type` to the TD namespace. These representation rules
do not change the composition semantics of the named operators.

For example, `/properties/a~1b~0c` identifies the object under the authored
property name `a/b~c`. If that object contains an ordinary reference spelled
`model:ref`, expanding to `https://www.w3.org/2019/wot/tm#ref`, its binding
records `operator: "tm:ref"` and retains the pointer's authored spelling.
Recording `model:ref` as the binding operator is invalid. Binding `/links/0`
twice is also invalid even if both records name the same Version. Omitting
`/links/1` because it references that same Version leaves closure incomplete.

The experimental projection mapping selects the
[Projection Plans proposal at commit `79ddf72`](https://github.com/marcschier/wot-thing-description/blob/79ddf72d70eff97d9541afc83e20631cc3ba3567/proposals/wot-projections/spec.md)
and its context artifact at that revision. This is a repository-controlled
experiment, not a W3C or OPC Foundation vocabulary assignment. A Consumer
MUST identify its projection marker and `projects` member by the expanded
IRIs defined there. The former placeholder namespace is not an alias.
Consumers MUST use captured contexts or a supported immutable context set;
opening a publication MUST NOT fetch live contexts.

A projection plan describes a view composed from selected source documents.
In a marked projection plan, each external source-manifest entry is a
dependency occurrence, in its authored array order. Its binding MUST record
that entry's `href` and the projection operator above. The entry's expected
media `type` identifies the kind under the pinned proposal, for example
`application/td+json` for a TD or `application/tm+json` for a TM.
The Consumer MUST verify the captured target's actual kind. A `tm:ref`
affordance selector matched to that source under the selected proposal MUST
use the entry's binding and MUST NOT have a second binding of its own.
Ordinary `td:ref` occurrences remain separate dependencies. An otherwise
well-shaped closure binding MUST NOT be used to accept a marker, source
entry, or selector that fails the selected proposal's rules.

In live selection or snapshot composition, the Consumer MUST verify every
declared `wotproj:sourceDigest` against the exact selected source bytes,
including for sources that contribute nothing to the resolved view.
A mismatch fails as `pin-mismatch`; the Consumer MUST NOT look for a
different Version with matching bytes. Verifying an unused source's digest
does not add a provenance link for it. If both the declared digest and an
applicable floor or line check fail, the Consumer MUST reject the result;
this specification does not assign priority between them.

Before validating closure bindings, the Producer and Consumer MUST determine
candidate targets from the captured Registry model, Registry view, and document
associations. Target matching MUST use each candidate's Group and Resource
identity, Resource kind, applicable `wotid`, original document URI base, and
document-view URI from the captured Registry metadata. The Publication
[document association](../../publication/spec.md#registry-json-and-document-associations)
supplies `base` for relative references. Each URI identity MUST
distinguish a Resource from an exact Version. `originRegistry` is provenance,
not a document URI identity, and MUST NOT be used for target matching.
Neither side MAY use closure binding targets, unrecorded retrieval locations,
or requests to a live Registry to establish the candidate identities.

For each external reference occurrence, the Producer and Consumer MUST resolve
the authored `href` against the source document's captured base and remove its
fragment before matching captured URI identities. The operator's rules
determine whether the occurrence identifies a Resource or an exact Version.
For a Resource-level match, the bound Version MUST belong to that Resource.
For an exact-Version match, the binding MUST name that Version. If no
mapping is defined for the reference kind, the Consumer MUST reject the
binding. Having established the exact bound Version, the Consumer MUST
check it under the snapshot composition row of Section 5.4.2. Neither a
Resource-level match nor an exact-Version URI waives this check.

For an ordinary `tm:ref`, one unique identity match to a Thing Model Resource
classifies the occurrence as an in-scope dependency. One unique match to a
Schema Resource classifies it as a Schema reference outside this WoT closure
profile; that occurrence MUST NOT have a closure binding. A match to another
Resource kind is invalid. This classification uses captured model and URI
identities, not a binding target. The Schema document itself is not thereby
included in WoT closure or validated by this profile.

A `links` occurrence with `rel: "describedby"` that identifies a Schema
Resource is also outside this profile and MUST NOT have a closure binding.

For `td:ref`, `type`, and the other operators, the captured Resource kind
MUST agree with the target kind defined for that operator. A `type` link MAY
identify a Thing Model by its `wotid` or by a captured document-view URI,
including an exact-Version URI. A captured document URI is usable only at the
Resource or Version scope recorded for it. If the resolved URI identifies
more than one distinct Resource or Version, the mapping is ambiguous.
Duplicate records for the same identity do not create ambiguity.

If no captured identity matches or the match is ambiguous, the Producer MUST
NOT claim domain-complete closure and the Consumer MUST reject such a claim.
The binding list cannot resolve the ambiguity. This profile does not include
Schema Resource documents or OPC UA `uav:dataTypeDefinitions` materialization
references; another closure profile is needed to cover those dependencies.

The [closure schema](schemas/publication-closure.schema.json) checks the
structure shown in the [closure example](samples/publication-closure.json).
It does not verify that a publication covers every in-scope reference or
binds it to the correct Version.

### 5.5. Incremental Profile

#### 5.5.1. Publication

The incremental model uses Core `versionmode: manual` and
`singleversionroot: false`. Core lineage and default retrieval do not
define compatibility or numeric ordering. An endpoint MUST NOT switch
profiles in place after publishing Versions.

A Version ID is a string matching `[1-9][0-9]*` and fitting Core's
128-character limit. The publishing authority MUST maintain a durable
high-water mark for each authoritative Resource sequence, including
deleted Versions. It MUST assign the ID as follows:

1. If TM `version.model` or TD `version.instance` is a canonical
   positive integer string, use that value and set `versionorigin` to
   `authored`. Reject it if oversized or not greater than the mark.
2. Otherwise preserve the authored field, including absence, assign
   the mark plus one, and set `versionorigin` to `generated`. If no ID
   fits, reject publication.
3. If the caller supplied a Version ID, reject invalid syntax as
   `invalid-version` or a different assignment as `version-mismatch`.
4. Commit the bytes, metadata and new mark atomically. Failed writes
   MUST NOT expose a Version or change the mark.

The mark starts at zero for a fresh sequence. Deleting a Resource or
restoring a backup MUST NOT permit reuse under the same authoritative
sequence identity. Migration uses a separate endpoint, with explicit
old-to-new mappings if numbering changes. A resolver MUST NOT compare
numbers from independent sequences. It MAY compare replica results
only against verified original sequence identity and numbering.

#### 5.5.2. Compatibility Line

A compatibility line is an absolute URI compared exactly. A later
Version in a line claims that it can substitute for every earlier
Version of that Resource in the same line under the publisher's
documented public interface. Neither shared ancestry nor a larger ID
proves compatibility. The SemVer rule requiring a TM major in `wotid`
does not apply. A breaking update to the same logical document can
start a different line without changing `wotid`.

An authorized Producer MAY author `uav:compatibilityLine` in the document
root or supply `compatibilityline` separately as Version metadata.
Supplying metadata does not change the document bytes. If both values are
present they MUST agree exactly, or publication fails as
`inconsistent-publication`. A value, when supplied, MUST be an
absolute URI; null or an empty string is not omission. Creation fixes
the effective value, including absence. Changing it requires a new
Version. Replacing the document bytes also requires a new Version.
A missing line MUST NOT be inferred from `wotid`, a digest or
the Version ID.

The publisher MUST bind a claim to the profile, authoritative Resource
sequence, exact Version and content digest. A Consumer MUST accept it
only from an authorized publisher or configured trusted provider acting
for that sequence. A Version without an accepted claim MAY be fetched
directly but MUST NOT satisfy compatibility-line selection. The
incremental model does not assert Core Resource-wide backward
compatibility across different lines.

## 6. Relationships and Cross-References

Sections [6.1](#61-thing-description-to-thing-model),
[6.3](#63-thing-description-to-endpoint-registry), and
[6.4](#64-thing-description-to-schema-registry) describe relationships
informatively. [Section 6.2](#62-thing-description-to-thing-description)
identifies the proposed TD-to-TD mechanisms covered by the resolution
rules in [Section 5.4](#54-versioned-reference-resolution). Those rules do
not require a Registry to resolve references during ordinary storage.
[Section 6.5](#65-affordance-grouping) is normative.

### 6.1. Thing Description to Thing Model

A WoT-TD 1.1 document can declare that it conforms to one or more Thing
Models using the `links` member ([WoT-TD 1.1 §6.3.8][WoT-TD-1.1]) with
`"rel": "type"`, the convention specified in
[WoT-TD 1.1 §9.4, Derivation of Thing Description Instances][WoT-TD-1.1].

When the referenced Thing Model resides in the same WoT Registry, the `href`
can point at that Thing Model's document-view URL. This is its
[`self`][xRegistry self] URL with the `$details` suffix removed, or
equivalently its [`shortself`][xRegistry shortself] URL. A `link`
carrying `"type": "application/tm+json"` is expected to dereference to the TM
document itself and not to xRegistry metadata
([Section 1.4](#14-document-store)).

Because
[Section 5.2](#52-preserving-customer-documents) forbids rewriting, a document
that already carries an `href` in the WoT identifier space keeps it. The
Producer can record the target's `wotid` in `derivedfrom` without modifying
the link.

The `href` in such a link is an absolute URI. A registry-relative path would
not survive a copy of the document to another registry. See
[Section 5.2](#52-preserving-customer-documents).

For example:

```json
{
  "@context": "https://www.w3.org/2022/wot/td/v1.1",
  "@type": "Thing",
  "title": "Lamp #42",
  "links": [
    {
      "rel": "type",
      "href": "https://example.com/thingmodelgroups/Fabrikam.Lighting/thingmodels/urn.fabrikam.lamp.v1",
      "type": "application/tm+json"
    }
  ]
}
```

A Thing Description and the Thing Model it derives from are two distinct
Resources with independent lifecycles, so this relationship is expressed
through the TD document's `links` member rather than through the xRegistry
[`xref`][xRegistry xref] attribute, which exists to surface the *same*
Resource under more than one Group.

### 6.2. Thing Description to Thing Description

For `td:extends`, `td:subthing`, and `td:ref`,
[Section 5.4](#54-versioned-reference-resolution) defines how a resolver
identifies the TD revision supplied to the composition operator. It does
not change the operator's inheritance, child-relationship, or
definition-reference semantics. Other TD links are outside this rule. The
[WoT versioned-reference proposal][WoT reference proposal] defines the
proposed vocabulary and processing model.

### 6.3. Thing Description to Endpoint Registry

A WoT-TD 1.1 `forms` entry binds an interaction affordance to a network
endpoint.

When a Thing Description shares an endpoint independently managed by an
xRegistry [Endpoint Registry][xRegistry Endpoint], implementations typically
correlate the TD's `forms[].href` with a protocol binding documented by
the corresponding `endpoint` Resource. The `href` addresses the Thing
interface, not the Registry Resource that describes it.

This specification does not require an `endpoint` Resource to exist for every
`forms` entry, nor does it require any specific naming or correlation
mechanism. Implementations are free to define their own conventions to
correlate the two.

### 6.4. Thing Description to Schema Registry

A WoT-TD 1.1 property, action, or event affordance can reference an external
data schema rather than declaring its data schema inline.

When the referenced
schema is managed by an xRegistry [Schema Registry][xRegistry Schema],
implementations typically express the reference using the WoT
[`tm:ref`][WoT-TM-1.1] mechanism (in TMs) or a `links` entry with
`"rel": "describedby"` (in TDs). The `tm:ref` value or the link's `href`,
respectively, refers to the `schema` Resource Version's document-view URL:
the `self` URL with the `$details` suffix removed.

### 6.5. Affordance Grouping

A Thing Description declares its properties, actions, and events in the
`properties`, `actions`, and `events` members of a single document, as defined
by [WoT-TD 1.1][WoT-TD-1.1]. This specification requires nothing more:

- A registry MUST accept and serve a valid TD whose affordances are all
  declared in one document, with no grouping construct of any kind.
- A registry MUST NOT require an affordance to belong to a group before the
  registry stores, retrieves, or references it.
- Nothing in this specification — Resource layout, identity, versioning, or
  cross-referencing — depends on affordances being partitioned.

Proposals to sub-divide a large TD's affordances, such as a `td:submodel`
grouping member, are being discussed in the W3C WoT community. Were such a
mechanism to be standardized, a WoT Registry would store a TD that uses it
exactly as it stores any other TD, since the grouping is a member of the
document rather than the registry model. Interpreting the grouping is
OPTIONAL. A registry that does not understand the mechanism MUST still
store and serve the document unchanged, as specified in
[Section 5.2](#52-preserving-customer-documents).

Documents authored outside the Registry routinely contain no grouping
construct. They MUST remain fully supported.

## 7. Security

Like [xRegistry Core][xRegistry Core], this specification does not specify how
to authenticate users, what access levels to grant them, or how to secure the
APIs.

Implementations are expected to use authentication and authorization
suited to the application domain and deployment environment. These
mechanisms MAY include OAuth 2.0, OpenID Connect, API keys, or other options
suited to the use case.

A deployment can use `thingdescriptiongroup` and `thingmodelgroup` as
authorization boundaries, granting users access to specific Groups and the
Things or Thing Models they contain. It can also restrict access to specific
Versions of `thingdescription` and `thingmodel` Resources.

Operators of a WoT Registry SHOULD be aware that Thing Descriptions can
expose detailed information about deployed devices, including network
locations, operational endpoints, and security schemes. The
[WoT Security and Privacy Considerations][WoT-Security] document gives
additional guidance.

The document-preservation and selection rules introduce the following risks:

- **Composition can retrieve external documents.** A Thing Model composes
  other Thing Models through `tm:extends` and `tm:ref`, and a Thing Description
  names network endpoints through `links[].href` and `forms[].href`. These
  are authored strings taken verbatim from a document the registry did not
  write ([Section 5.2](#52-preserving-customer-documents)). Looking up a
  Registry identity is not the same as fetching an authored URL or invoking
  the Thing operation named by a form. When a resolver fetches a URL, it
  uses its own network position and credentials, not the author's.

  A Consumer or Registry that resolves them SHOULD confine resolution to the
  Registry and its declared federation links. Where a deployment has to
  dereference an authored URL it SHOULD:

  - Restrict the scheme to `https`,
  - Reject targets that resolve to loopback, link-local, or other internal
    address ranges,
  - Decline to follow cross-origin redirects, and
  - Bound both the depth and the total size of the composition closure.

  The same applies to the `thingdescriptionurl` and `thingmodelurl` attributes,
  whose bytes come from a location the registry does not control and for
  which this specification defines no integrity check.

- **Provenance metadata is self-asserted.** `license`, `publisher`,
  `standardsbody`, `canonicalurl`, and `maturity` are supplied by the
  writer of each Version. This specification mandates no verification of
  these claims
  ([Section 4.6](#46-provenance-and-selection-metadata)).

  The same `wotid` MAY appear in more than one Group
  ([Section 5.3](#53-lookup)). A writer with access to any Group within a
  Registry-wide query's scope can therefore publish a document carrying another
  party's `wotid` and use `maturity` or `standardsbody` to raise its rank. A
  Consumer selecting on those attributes alone would compose the attacker's
  Thing Model and bind its affordances to that model's endpoints.

  Selection MUST therefore be scoped to writers the Consumer already trusts.

- **Serving stored documents from the Registry UI's origin adds risk.** A
  document is stored byte-for-byte
  ([Section 5.2](#52-preserving-customer-documents)) and
  served under a client-supplied `contenttype`.
  [Section 4.2](#42-thing-description-resources) constrains which media types
  a registry will serve it under. Format validation does not help here: a
  document can be valid JSON-LD 1.1 and still execute as script if served as
  `text/html`.

---

[Core versionmode]: ../../../core/model.md#groupsstringresourcesstringversionmode
[Core singleversionroot]: ../../../core/model.md#groupsstringresourcesstringsingleversionroot
[Core ancestorid]: ../../../core/spec.md#ancestorid-attribute
[Core id constraints]: ../../../core/spec.md#singularid-id-attribute
[Core versionid]: ../../../core/spec.md#versionid-attribute
[Core Version IDs]: ../../../core/spec.md#version-ids
[Core read-only rules]: ../../../core/spec.md#read-only-changed
[Core compatibility]: ../../../core/spec.md#compatibility-attribute
[Core validatecompatibility]: ../../../core/model.md#groupsstringresourcesstringvalidatecompatibility
[Core strictvalidation]: ../../../core/model.md#groupsstringresourcesstringstrictvalidation
[Core defaultversionsticky]: ../../../core/spec.md#defaultversionsticky-attribute
[Core defaults]: ../../../core/spec.md#default-version-of-a-resource
[WoT-TD-1.1]: https://www.w3.org/TR/wot-thing-description11/
[WoT-TM-1.1]: https://www.w3.org/TR/wot-thing-description11#thing-model
[WoT-TD media]: https://www.w3.org/TR/wot-thing-description11#media-type-section
[WoT-TM media]: https://www.w3.org/TR/wot-thing-description11#media-type-section-tm
[JSON-LD]: https://www.w3.org/TR/json-ld11/
[SemVer]: https://semver.org/spec/v2.0.0.html
[CE WoT profile]: https://github.com/cloudevents/spec/blob/278dcbde5f51b65e62863c5d0d144c7f366fec74/cloudevents/extensions/wot.md
[WoT reference proposal]: https://github.com/marcschier/wot-thing-description/blob/f66f89ab59196be3d19b088692f9ce7c22e7785e/proposals/td-versioned-references/spec.md
[WoT-Discovery]: https://www.w3.org/TR/wot-discovery/
[WoT-Security]: https://www.w3.org/TR/wot-security/
[RFC3986]: https://www.rfc-editor.org/rfc/rfc3986
[SPDX]: https://spdx.org/licenses/
[OpenUSD Draft]: ../openusd/spec.md
[xRegistry Core]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html
[xRegistry Endpoint]: https://xregistry.io/xreg/xregistryspecs/endpoint-v1/docs/spec.html
[xRegistry Message]: https://xregistry.io/xreg/xregistryspecs/message-v1/docs/spec.html
[xRegistry Schema]: https://xregistry.io/xreg/xregistryspecs/schema-v1/docs/spec.html
[xRegistry self]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#self-attribute
[xRegistry shortself]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#shortself-attribute
[xRegistry compatibility]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#compatibility-attribute
[xRegistry ancestorid]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#ancestorid-attribute
[xRegistry deprecated]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#deprecated
[xRegistry matchversions]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/model.html#attributesstringmatchversions
[xRegistry version-ids]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#version-ids
[xRegistry hasdocument]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#hasdocument
[xRegistry xref]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#xref-attribute
