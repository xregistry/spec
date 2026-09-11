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
<!-- words: disambiguator toolchain userinfo byom contoso maturity publisher -->

## Abstract

This specification defines a WoT (Web of Things) Registry extension to the
xRegistry document format and API [specification][xRegistry Core]. A WoT
Registry allows for the storage, management and discovery of W3C
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
    - [5.1. WoT Identifiers and `xid`s](#51-wot-identifiers-and-xids)
      - [5.1.1. The Symbolic Identifier Construction](#511-the-symbolic-identifier-construction)
      - [5.1.2. Breaking Changes and Successor Identifiers](#512-breaking-changes-and-successor-identifiers)
    - [5.2. Preserving Customer Documents](#52-preserving-customer-documents)
    - [5.3. Lookup](#53-lookup)
    - [5.4. Ambiguity and Errors](#54-ambiguity-and-errors)
  - [6. Relationships and Cross-References](#6-relationships-and-cross-references)
    - [6.1. Thing Description to Thing Model](#61-thing-description-to-thing-model)
    - [6.2. Thing Description to Endpoint Registry](#62-thing-description-to-endpoint-registry)
    - [6.3. Thing Description to Schema Registry](#63-thing-description-to-schema-registry)
    - [6.4. Affordance Grouping](#64-affordance-grouping)
  - [7. Security](#7-security)

## 1. Overview

A WoT Registry provides a repository for managing W3C Web of Things documents:
**Thing Descriptions** (TDs), which describe concrete network-facing instances
of Things, and **Thing Models** (TMs), which describe reusable, abstract
templates for classes of Things.

A WoT Registry is generally used to share Thing metadata amongst multiple
parties: device fleets, gateways, integrators, and consuming applications. The
registry is intended to make Things and their templates **discoverable** in a
manner aligned with the W3C
[WoT Discovery][WoT-Discovery] specification, while also allowing TDs and TMs
to be cross-referenced from xRegistry [Endpoint][xRegistry Endpoint],
[Message][xRegistry Message], and [Schema][xRegistry Schema] entries.

### 1.1. Thing Descriptions and Thing Models

A **Thing Description** (TD) is a JSON-LD 1.1 document conforming to
[WoT-TD 1.1][WoT-TD-1.1]. It identifies a deployed Thing instance, declares its
properties, actions, and events, and provides one or more `forms` that bind
those interaction affordances to network endpoints over specific protocols
(HTTP, MQTT, CoAP, OPC-UA, Modbus, etc.).

A **Thing Model** (TM) is a JSON-LD 1.1 document conforming to
[WoT-TM 1.1][WoT-TM-1.1]. It is an **abstract** description of a class of
Things, typically without `href` values in its forms. Thing Models are
intended to be reused: a concrete Thing Description MAY extend or compose one
or more Thing Models via the WoT `tm:extends` and `tm:ref` mechanisms, or via
JSON-LD `@type` declarations.

Both document classes are JSON-LD; they share a common subset of vocabulary,
but a WoT Registry MUST treat them as distinct Resource types because their
intended use, validation rules, and lifecycle are different.

### 1.2. Relationship to Other xRegistry Specs

A WoT Registry is complementary to the xRegistry [Endpoint][xRegistry Endpoint],
[Message][xRegistry Message], and [Schema][xRegistry Schema] registries:

- A Thing Description's `forms` array describes protocol bindings that MAY
  also be represented as `endpoint` Resources; see
  [Section 6.2](#62-thing-description-to-endpoint-registry).
- A Thing Description's property/action/event data schemas (declared inline
  via WoT data-schema vocabulary) MAY reference external schemas managed by
  the xRegistry Schema Registry; see
  [Section 6.3](#63-thing-description-to-schema-registry).
- A Thing Description MAY reference one or more Thing Models from which it
  is derived; see [Section 6.1](#61-thing-description-to-thing-model).

These cross-references are informative: a WoT Registry implementation MAY
choose to validate them, but this specification does not mandate that all
referents resolve.

### 1.3. Versioning

Each Version of a `thingdescription` or `thingmodel` Resource holds a complete
WoT-TD or WoT-TM document. This specification does not require a registry to
parse the document in order to derive registry metadata; the document is
stored as-is and the xRegistry [`versionid`][xRegistry version-ids] is
assigned by the xRegistry Core rules.

A version is never part of an identifier. A Resource's `wotid`,
`thingdescriptionid` and `thingmodelid` are stable across revisions of the
document they name; `wotid` is declared with
[`matchversions`][xRegistry matchversions], so a registry rejects a Version
that supplies a different one. See
[Section 5.1](#51-wot-identifiers-and-xids).

The xRegistry Core versioning rules (monotonically increasing integer
`versionid`s, [`ancestorid`][xRegistry ancestorid] lineage, default-Version
selection) apply unchanged. A breaking change to a TD or TM that violates the
Resource's [`compatibility`][xRegistry compatibility] policy MUST result in a
new Resource, not a new Version.

Because a Resource's id is a function of its `wotid`, that successor Resource
is reached by authoring a *new* WoT identifier, and the superseded Resource
records where the successor lives; see
[Section 5.1.2](#512-breaking-changes-and-successor-identifiers).

### 1.4. Document Store

The WoT Registry is a document store: the `thingdescriptions` and `thingmodels` Resources
are defined with [`hasdocument`][xRegistry hasdocument] set to `true`. A GET
against a Resource Version's [`self`][xRegistry self] URL returns the JSON-LD
TD or TM document with the appropriate content-type
(`application/td+json` for TDs, `application/tm+json` for TMs, per
[WoT-TD 1.1 §11.1][WoT-TD-1.1]). Resource metadata is returned in HTTP headers
or via the `$details` suffix.

This means an xRegistry-unaware WoT consumer MAY treat a Resource Version's
`self` URL as a regular WoT TD URL.

## 2. Notations and Terminology

### 2.1. Notational Conventions

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD",
"SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be
interpreted as described in [RFC 2119](https://tools.ietf.org/html/rfc2119).

For clarity, OPTIONAL attributes (specification-defined and extensions) are
OPTIONAL for clients to use, but the servers' responsibility will vary.
Server-unknown extension attributes MUST be silently stored in the backing
datastore. Specification-defined, and server-known extension, attributes MUST
generate an error if the corresponding feature is not supported or enabled.

In the pseudo JSON format snippets `?` means the preceding attribute is
OPTIONAL, `*` means the preceding attribute MAY appear zero or more times,
and `+` means the preceding attribute MUST appear at least once. The presence
of the `#` character means the remaining portion of the line is a comment.
Whitespace characters in the JSON snippets are used for readability and are
not normative.

### 2.2. Terminology

This specification defines the following terms:

#### 2.2.1. Thing Description

We use the term **Thing Description** (or `thingdescription` Resource) in this specification as a
logical grouping of **Thing Description Versions**. A **Thing Description Version** is a concrete
WoT-TD 1.1 JSON-LD document. The **Thing Description** Resource is a semantic umbrella
formed around one or more concrete Thing Description documents that represent
iterations of the same logical Thing instance. Per the definition of the
[`compatibility`][xRegistry compatibility] attribute, all Versions of a single
**Thing Description** MUST adhere to the rules defined by the `compatibility` attribute.
Any breaking change MUST result in a new **Thing Description** Resource being created.

#### 2.2.2. Thing Model

We use the term **Thing Model** (or `thingmodel` Resource) in this
specification as a logical grouping of **Thing Model Versions**. A **Thing
Model Version** is a concrete WoT-TM 1.1 JSON-LD document. As with Things,
versioning is governed by the Resource's `compatibility` attribute.

A Thing Model is distinguished from a Thing by purpose: a Thing Model
describes a **class** of Things and typically lacks concrete `href` values in
its forms, whereas a Thing Description describes a **specific** deployed Thing
instance.

#### 2.2.3. WoT Identifier

A **WoT identifier** is the URI a WoT document carries in its `id` member, as
defined by [WoT-TD 1.1][WoT-TD-1.1] — for example `urn:fabrikam:lamp:42`. It
is location-independent: it names *what* the document describes, not where it
is stored, and it is the identifier that other WoT documents and WoT tooling
use to refer to it.

A WoT identifier is held in the `wotid` attribute and is distinct from the
xRegistry `thingdescriptionid`/`thingmodelid`, which is the Resource's id
*within a registry*. [Section 5.1](#51-wot-identifiers-and-xids) defines how
the two relate.

### 2.3. Thing Description Group

A Thing Description Group is a container for Thing Descriptions that are related to each
other in some application-defined way (for example, all TDs for a tenant, a
fleet, or a physical site). This specification does not impose any
restrictions on what Thing Descriptions can be contained in a Thing Description Group.

### 2.4. Thing Model Group

A Thing Model Group is a container for Thing Models that are related to each
other in some application-defined way (for example, all TMs published by a
single vendor, or all TMs for a product family). This specification does not
impose any restrictions on what Thing Models can be contained in a Thing
Model Group.

## 3. WoT Registry Model

The authoritative xRegistry extension model of the WoT Registry resides in
the [model.json](model.json) file.

For easy reference, the JSON serialization of a WoT Registry adheres to this
form:

```yaml
{
  "specversion": "<STRING>",                       # xRegistry core attributes
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

  "thingdescriptiongroupsurl": "<URL>",                       # ThingDescriptionGroups collection
  "thingdescriptiongroupscount": <UINTEGER>,
  "thingdescriptiongroups": {
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

      "thingdescriptionsurl": "<URL>",                        # ThingDescriptions collection
      "thingdescriptionscount": <UINTEGER>,
      "thingdescriptions": {
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
          "contenttype": "<STRING>", ?            # SHOULD be application/td+json
          "format": "<STRING>",                    # MUST be "JSON-LD/1.1"
          "wotid": "<STRING>",                     # the document's authored 'id'
          "derivedfrom": [ "<STRING>" * ], ?       # wotids of the TMs it derives from
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
          "thingdescription": <ANY> ?                         # the WoT-TD JSON-LD document
          "thingdescriptionbase64": "<STRING>", ?
          #  End of default Version's attributes

          "metaurl": "<URL>",
          "meta": { ... }, ?

          "versionsurl": "<URL>",
          "versionscount": <UINTEGER>,
          "versions": { ... } ?
        } *
      } ?
    } *
  }, ?

  "thingmodelgroupsurl": "<URL>",                  # ThingModelGroups collection
  "thingmodelgroupscount": <UINTEGER>,
  "thingmodelgroups": {
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

      "thingmodelsurl": "<URL>",                              # ThingModels collection
      "thingmodelscount": <UINTEGER>,
      "thingmodels": {
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
          "contenttype": "<STRING>", ?            # SHOULD be application/tm+json
          "format": "<STRING>",                    # MUST be "JSON-LD/1.1"
          "wotid": "<STRING>",                     # the document's authored 'id'
          "derivedfrom": [ "<STRING>" * ], ?       # wotids of the TMs it extends
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
          "thingmodel": <ANY> ?                               # the WoT-TM JSON-LD document
          "thingmodelbase64": "<STRING>", ?
          #  End of default Version's attributes

          "metaurl": "<URL>",
          "meta": { ... }, ?

          "versionsurl": "<URL>",
          "versionscount": <UINTEGER>,
          "versions": { ... } ?
        } *
      } ?
    } *
  } ?
}
```

## 4. WoT Registry

The WoT Registry is a metadata store for organizing Thing Descriptions, Thing
Models, and their Versions; it is a document store.

Implementations of this specification MAY include additional extension
attributes, including the `*` attribute of type `any`.

Since the WoT Registry is an application of the
[xRegistry specification][xRegistry Core], all attributes for Groups,
Resources, and Resource Version objects are inherited from there.

### 4.1. Thing Description Groups

The Group (`<GROUP>`) name for Thing Descriptions is `thingdescriptiongroup` (singular).
The plural, used as the collection name, is `thingdescriptiongroups`. The Thing Description Group
does not have any specific extension attributes.

A Thing Description Group is a collection of Thing Descriptions that are related to each
other in some application-defined way. A Thing Description Group does not impose any
restrictions on the contained Thing Descriptions.

Every Thing Description (i.e. the `thingdescription` Resource) MUST reside inside a Thing
Description Group.

Example:

```yaml
{
  "specversion": "1.0-rc4",
  # other xRegistry top-level attributes excluded for brevity

  "thingdescriptiongroupsurl": "https://example.com/thingdescriptiongroups",
  "thingdescriptiongroupscount": 1,
  "thingdescriptiongroups": {
    "fabrikam.factory-floor-01": {
      "thingdescriptiongroupid": "fabrikam.factory-floor-01",
      # other xRegistry Group-level attributes excluded for brevity

      "thingdescriptionsurl": "https://example.com/thingdescriptiongroups/fabrikam.factory-floor-01/thingdescriptions",
      "thingdescriptionscount": 12
    }
  }
}
```

### 4.2. Thing Description Resources

The Resource (`<RESOURCE>`) inside of Thing Description Groups is named `thingdescription`. The
plural, used as the collection name, is `thingdescriptions`. Any single `thingdescription` is a
container for one or more `versions`, each of which holds the concrete
WoT-TD 1.1 JSON-LD document.

The `format` attribute of a `thingdescription` Resource Version MUST be `"JSON-LD/1.1"`.
The `contenttype` of a `thingdescription` document SHOULD be `application/td+json` per
[WoT-TD 1.1][WoT-TD-1.1].

The `wotid` attribute is REQUIRED and holds the document's authored WoT
identifier; the `thingdescriptionid` is constructed from it. See
[Section 5.1](#51-wot-identifiers-and-xids). The OPTIONAL `derivedfrom`
attribute lists the `wotid`s of the Thing Models this Thing Description
extends or composes.

All Versions of a single Thing Description Resource MUST adhere to the semantic rules of
the Thing Description's [`compatibility`][xRegistry compatibility] attribute, if specified.

Implementations of this specification SHOULD use the xRegistry default
algorithm for generating new `versionid` values and for determining which is
the latest Version. See [Version IDs][xRegistry version-ids] for more
information.

### 4.3. Thing Model Groups

The Group name for Thing Models is `thingmodelgroup` (singular), with
collection name `thingmodelgroups`. The Thing Model Group does not have any
specific extension attributes.

A Thing Model Group is a collection of Thing Models related in some
application-defined way (typically by vendor or product family).

Every Thing Model (i.e. the `thingmodel` Resource) MUST reside inside a Thing
Model Group.

### 4.4. Thing Model Resources

The Resource inside of Thing Model Groups is named `thingmodel`, with
collection name `thingmodels`. Any single `thingmodel` is a container for one
or more `versions`, each of which holds the concrete WoT-TM 1.1 JSON-LD
document.

The `format` attribute of a `thingmodel` Resource Version MUST be
`"JSON-LD/1.1"`. The `contenttype` SHOULD be `application/tm+json` per
[WoT-TM 1.1][WoT-TM-1.1].

The same `compatibility`, `versionid`, and
[`ancestorid`][xRegistry ancestorid] rules described for `thingdescription`
Resources apply to `thingmodel` Resources.

The `wotid` attribute is REQUIRED on a `thingmodel` and holds the document's
authored WoT identifier, from which the `thingmodelid` is constructed. Where a
Thing Model extends another via `tm:extends`, or references one via `tm:ref`,
the referenced Thing Models' `wotid`s SHOULD be listed in `derivedfrom`.

### 4.5. Formats

Both Thing Descriptions and Thing Models are serialized as JSON-LD 1.1
documents, so both use the
[core specification's `format`](../../../core/spec.md#format-attribute) identifier
`JSON-LD/1.1`. The distinction between the two document classes is carried by
the Resource type (`thingdescriptions` versus `thingmodels`) and by the
`contenttype` attribute, not by `format`.

#### 4.5.1. WoT Thing Description

- Format identifier: `JSON-LD/1.1`
- `contenttype`: `application/td+json`
- Document: a JSON-LD 1.1 document conformant with
  [W3C WoT Thing Description 1.1][WoT-TD-1.1].
- The document's `@context` MUST include
  `https://www.w3.org/2022/wot/td/v1.1`.
- A URI-reference pointing to a TD MAY use a JSON-Pointer
  ([RFC 6901](https://www.rfc-editor.org/rfc/rfc6901)) fragment to deep-link
  into a particular property, action, or event affordance, e.g.
  `…/thingdescriptions/lamp-42#/properties/status`.

#### 4.5.2. WoT Thing Model

- Format identifier: `JSON-LD/1.1`
- `contenttype`: `application/tm+json`
- Document: a JSON-LD 1.1 document conformant with
  [W3C WoT Thing Model 1.1][WoT-TM-1.1].
- The document's `@context` MUST include
  `https://www.w3.org/2022/wot/td/v1.1` and the document's top-level
  `@type` MUST include `tm:ThingModel`.
- Deep-linking via JSON-Pointer fragments is permitted, as for TDs.

### 4.6. Provenance and Selection Metadata

A registry is consumed by tools and by autonomous agents that have to choose
between several documents describing similar Things. Choosing well needs
metadata that is *explicit*, rather than inferred from a title or a naming
convention. Both `thingdescription` and `thingmodel` Resources therefore carry
the following OPTIONAL attributes:

| Attribute | Type | Meaning |
|---|---|---|
| `license` | string | The license the document is offered under, as an [SPDX][SPDX] license expression or a URL |
| `publisher` | string | The organization that published the document |
| `standardsbody` | string | The standards organization that defines or endorses the document, where one does |
| `canonicalurl` | url | The canonical upstream location of the document, where it is also published outside this registry |
| `maturity` | string | One of `Standard`, `Vendor`, `Community` or `Experimental` |

A Consumer choosing between candidate Thing Models SHOULD prefer, in order, a
`maturity` of `Standard` with a `standardsbody`, then `Vendor`, then
`Community`, then `Experimental`. Where the choice remains open the Consumer
SHOULD prefer the document whose `canonicalurl` it already trusts.

These attributes are **advisory**. They describe where a document came from
and how established it is; they are not part of its semantic identity. In
particular:

- A registry MUST NOT treat two documents as the same document because their
  provenance attributes agree, nor as different documents because they differ.
  Identity is `wotid` alone ([Section 5.1](#51-wot-identifiers-and-xids)).
- Changing a provenance attribute is not a change to the WoT document and
  MUST NOT, by itself, require a new Version.

Adoption signals such as download or reference counts are **registry
operational data**, not document metadata: they describe the registry's
observation of traffic rather than the document, they are not portable between
registries, and a document copied to a second registry would acquire different
values for the same bytes. This specification therefore does not model them.
An implementation that publishes such signals SHOULD do so as extension
attributes, and a Consumer MUST NOT rely on them being present or comparable
across registries.

## 5. Identity and Resolution

### 5.1. WoT Identifiers and `xid`s

xRegistry defines an [`xid`][xRegistry Core] as the stable path of an entity
within its registry, and constrains each entity id to [RFC 3986][RFC3986]
`unreserved` characters plus `:` and `@`, starting with a letter, a digit or
`_`, at most 128 characters long, and unique case-insensitively within its
parent. A WoT identifier is the value of a TD's or TM's `id` member: a URI,
most often a URN such as `urn:fabrikam:lamp:42`, but equally a URL such as
`https://fabrikam.example/things/lamp-42`.

The two express the same idea but are **not the same grammar**:
`https://fabrikam.example/things/lamp-42` is not a valid `xid`, and an `xid`
is not what a Thing author writes.

This specification therefore does not equate them. It derives one from the
other by a **closed-form, one-way construction**, and keeps the authored
identifier as the authority:

> A `thingdescription`'s `wotid` MUST be the `id` member of its WoT document,
> verbatim. Its `thingdescriptionid` MUST be the **symbolic identifier** of
> that `wotid` ([Section 5.1.1](#511-the-symbolic-identifier-construction)).
> The `wotid` attribute is REQUIRED and is the authority: an implementation
> MUST NOT recover a WoT identifier by attempting to invert the construction.
> The same rules apply to a `thingmodel`'s `wotid` and `thingmodelid`.

A `wotid` MUST NOT encode a revision of the document it names. Encoding one —
for example as a `:v2` suffix appended when the document is edited — makes the
identifier change whenever the document changes, so the registry can no longer
tell that two documents describe the same logical Thing,
[`ancestorid`][xRegistry ancestorid] lineage is broken, and every consumer
holding a reference has to be rewritten on each revision. The version of a
document is carried by the xRegistry `versionid` and, where the document
declares one, by its own WoT `version` member; neither is part of the
identifier.

This is a prohibition on *versioning an identifier*, not on the characters
that may appear in one. A vendor who deliberately publishes a second,
incompatible Thing alongside the first is naming a different Thing, and the
identifier they author for it — which may well carry a `v2` token — is that
Thing's own stable `wotid`; see
[Section 5.1.2](#512-breaking-changes-and-successor-identifiers).

Consequently, where a document is revised:

- Its `wotid` is unchanged.
- Its `thingdescriptionid` (or `thingmodelid`) is unchanged, because the
  construction is a function of the `wotid` alone.
- A new Version is created under the same Resource.

#### 5.1.1. The Symbolic Identifier Construction

A symbolic identifier is built from a source string as follows. The result is
a dot-separated token in the alphabet `A-Z a-z 0-9 _ . -`, a strict subset of
what xRegistry permits, so that it is simultaneously safe in a URL, on a
command line and as a file name. The construction is deliberately identical to
the one used by the [OpenUSD Artifact Registry][OpenUSD Draft] working draft,
so that an implementation supporting both needs only one implementation of it.

1. Split the source into an *authority* and a *path*. For an absolute URI with
   an authority component the authority is the host together with its port
   when present, and the path is the URI path; the scheme, userinfo, query and
   fragment are discarded. For a URN the authority is empty and the path is
   the URN split on `:`. Otherwise the authority is empty and the path is the
   source split on `/`.
2. Reverse the authority's `.`-separated labels (`fabrikam.example` becomes
   `example`, `fabrikam`), appending the port, where present, as a further
   label.
3. Percent-decode each path segment and discard the empty ones.
4. Normalize each label: replace every run of characters outside
   `A-Z a-z 0-9 _ . -` with a single `-`; collapse runs of `-` and runs of
   `.`; strip leading and trailing `-` and `.`; discard a label that becomes
   empty. Letter case is preserved.
5. Join the surviving labels with `.`. If no label survives, the identifier is
   `_`.
6. If the result is longer than 128 characters, drop trailing labels — never
   the first — until it is at most 119 characters long; if that first label is
   itself longer than 119 characters, truncate it to 119 and strip any
   trailing `-` or `.`. Then append the disambiguator of step 7.
7. Where step 6 truncated the result, or where the result would collide
   case-insensitively with an existing sibling in the same collection, append
   `.` followed by the first eight lower-case hexadecimal characters of the
   SHA-256 of the UTF-8 encoding of the **exact source string**. The
   disambiguator is a function of the identifier, not of any document, so it
   does not change when a new Version is written.

The construction is deterministic, so a Producer and a Consumer agree without
a lookup table; it is lossy, so only the forward direction is defined:

| Direction | Operation |
|---|---|
| authored `id` → registry location | apply the construction, append to the Group's `thingdescriptions`/`thingmodels` collection |
| `thingdescriptionid` → authored `id` | read the Resource's `wotid` attribute |

For example:

| Authored `id` | `thingdescriptionid` |
|---|---|
| `urn:fabrikam:lamp:42` | `urn.fabrikam.lamp.42` |
| `https://fabrikam.example/things/lamp-42` | `example.fabrikam.things.lamp-42` |
| `urn:uuid:6ba7b810-9dad-11d1-80b4-00c04fd430c8` | `urn.uuid.6ba7b810-9dad-11d1-80b4-00c04fd430c8` |

A `wotid` is REQUIRED. A document whose `id` member is absent — which
[WoT-TD 1.1][WoT-TD-1.1] permits for TDs served from a fixed URL, and which is
common for TMs — MUST be assigned a `wotid` by its Producer at write time, and
that assigned value is thereafter the document's identity in this registry. A
registry MUST reject a write that supplies neither an `id` member nor a
`wotid`, rather than inventing one, because an invented identifier is not
stable across registries.

#### 5.1.2. Breaking Changes and Successor Identifiers

[Section 1.3](#13-versioning) requires a breaking change to result in a new
Resource rather than a new Version. Since a Resource's id is a function of its
`wotid` alone, and a `wotid` does not change when its document is revised, a
successor Resource cannot be produced by editing an existing document: it is
produced by authoring a **new logical Thing** with its own `wotid`.

- The successor's `wotid` is a new authored identifier, distinct from the
  predecessor's. It is that Thing's permanent identity and is itself never
  revised thereafter.
- Its `thingdescriptionid` (or `thingmodelid`) follows from that `wotid` by the
  construction in [Section 5.1.1](#511-the-symbolic-identifier-construction),
  so the two Resources occupy distinct paths in the same Group.
- The predecessor's Versions are retained and remain retrievable. A breaking
  change does not remove history.
- The predecessor SHOULD set [`deprecated`][xRegistry deprecated], naming the
  successor Resource, so a consumer holding the old identifier can find the
  new one without a side channel.

Where a solution versions its Things semantically, it is RECOMMENDED that the
authored identifier carry a major-version token — `urn:fabrikam:lamp:v2`, or
`https://fabrikam.example/tm/lamp/v2` — so that incompatible but historically
related Things are recognizable to users and developers. The `versionid` then
functions as the minor-version identifier within each of them. This mirrors
the convention the [Schema Registry][xRegistry Schema] recommends for
`schemaid`.

This does not contradict [Section 5.1](#51-wot-identifiers-and-xids): the
token is chosen once, by the author, as part of naming a distinct Thing, and
that Thing's `wotid` is thereafter stable across all of its own revisions. What
Section 5.1 forbids is a registry or a Producer *mutating* an identifier — a
`wotid` that becomes `…:v2` because the document it already names was edited.

For example, a lamp whose control interface changes incompatibly:

| | Predecessor | Successor |
|---|---|---|
| `wotid` | `urn:fabrikam:lamp` | `urn:fabrikam:lamp:v2` |
| `thingmodelid` | `urn.fabrikam.lamp` | `urn.fabrikam.lamp.v2` |
| Versions | `1`, `2`, `3` — retained | `1`, growing independently |
| `deprecated` | set, naming the successor | absent |

### 5.2. Preserving Customer Documents

Registries are populated with Thing Models and Thing Descriptions that already
exist: authored by a vendor, published by a standards body, or generated by a
toolchain, and referenced from artifacts the registry never sees. Such a
document is stored as it was authored.

- A registry MUST store the WoT document byte-for-byte as supplied, apart from
  transformations the client explicitly requested.
- A registry MUST NOT rewrite the document's `id` member, its `links[].href`
  values, its `tm:extends` or `tm:ref` targets, or any other identifier
  internal to the document, into registry-specific identifiers.
- A retrieval of a stored Version MUST return a document that is semantically
  identical to the one supplied, with the same identifiers in the same
  identifier space.

Rewriting is incompatible with these documents for three reasons. A TM
published by a standards body is referenced by `id` from artifacts outside the
registry, and rewriting the `id` would break those references while leaving
the registry's own copy claiming to be the standard document. A TD's
`tm:extends` target resolves in the WoT identifier space, so a rewritten
target no longer matches what any other WoT tool would look for. And a
document copied between two registries would acquire two different identities
for the same bytes, so neither registry could tell the copies apart from
genuinely distinct documents.

The registry's own identifiers therefore live *outside* the document, in the
`wotid`, `thingdescriptionid` and `derivedfrom` attributes. This keeps the
authored identifier space and the registry identifier space separate and
allows a document to round-trip unchanged.

Where a registry wants the TD-to-TM link to be traversable without parsing the
document, it records the referenced Thing Models' *authored* identifiers in
the `derivedfrom` attribute. `derivedfrom` holds `wotid` values, not `xid`s,
precisely so that it can be compared directly against what the document
authored.

### 5.3. Lookup

A Consumer holding a WoT identifier — typically taken from a `tm:extends`
target, a `links[].href`, or a message attribute — resolves it to a stored
document in one of two ways.

**By construction.** Where the Consumer also knows the Group, it computes the
Resource path directly, with no lookup:

```
/thingmodelgroups/<thingmodelgroupid>/thingmodels/<symbolic-id-of(wotid)>
```

**By query.** Otherwise it queries on the `wotid` attribute, which is the
defined indexed path for identifier lookup:

```
GET /thingmodels?filter=wotid=urn:fabrikam:lamp
```

An implementation SHOULD index `wotid` on both `thingdescriptions` and
`thingmodels` such that this query is served without scanning the collection.
The two forms are functionally equivalent from the Consumer's point of view
and MUST return the same Resource where both are applicable.

A `wotid` is expected to be unique within a Group; the construction of
[Section 5.1.1](#511-the-symbolic-identifier-construction) guarantees it,
since two Resources in one Group cannot share a `thingdescriptionid`. Across
Groups a `wotid` MAY repeat — the same vendor TM legitimately appears in two
tenants' Groups — so a registry-wide query MAY match more than one Resource.

Version selection is a second, separate step, and is never encoded in the
identifier:

| Intent | Request |
|---|---|
| Latest Version | the Resource's `self` URL, which serves its default Version |
| A specific Version | `<self>/versions/<versionid>` |
| Enumerate Versions | `<self>/versions` |

"Latest" is the Resource's [default Version][xRegistry version-ids], as
determined by the xRegistry Core rules and the Resource's `defaultversionsticky`
setting; this specification does not redefine it. A Consumer that omits a
version MUST be served the default Version, and MUST NOT infer the latest
Version by sorting `versionid`s itself.

A caller that carries an identifier and a version through a transport — for
example in message headers — SHOULD carry them as two separate values, so that
the recipient resolves the document without parsing a compound string.

### 5.4. Ambiguity and Errors

Resolution behavior is deterministic:

| Condition | Behavior |
|---|---|
| Identifier not found | `404 Not Found`. A registry MUST NOT substitute a near match |
| Version not found on an existing Resource | `404 Not Found` |
| Malformed version, or a `versionid` that violates the Resource's `versionmode` | `400 Bad Request` |
| Malformed `wotid` on write — absent, empty, or not a URI where the document declares an `id` | `400 Bad Request` |
| A registry-wide query matching more than one Resource | all matches are returned |

A registry MUST NOT resolve an ambiguous match by returning an arbitrary
first result. Where a caller requires a single document it MUST narrow the
query — most simply by naming the Group — and where the query is
Group-scoped a match is unique by construction. Returning an arbitrary
member of a match set makes the result depend on storage order, which is not
reproducible and cannot be relied on in production.

## 6. Relationships and Cross-References

Sections [6.1](#61-thing-description-to-thing-model) through
[6.3](#63-thing-description-to-schema-registry) are informative;
[Section 6.4](#64-affordance-grouping) is normative.

### 6.1. Thing Description to Thing Model

A WoT-TD 1.1 document MAY declare that it conforms to one or more Thing Models
using the `links` member with `"rel": "type"`, per
[WoT-TD 1.1 §6.3.4][WoT-TD-1.1]. When the referenced Thing Model resides in
the same WoT Registry, the `href` SHOULD point to that Thing Model's
[`self`][xRegistry self] URL (or `shortself` URL). Because the Thing Model's
Resource id is constructed from its `wotid`, a Producer computes that URL
without a lookup; and because [Section 5.2](#52-preserving-customer-documents)
forbids rewriting, a document that already carried an `href` in the WoT
identifier space keeps it, and the link is recorded in `derivedfrom` instead.

For example:

```json
{
  "@context": "https://www.w3.org/2022/wot/td/v1.1",
  "@type": "Thing",
  "title": "Lamp #42",
  "links": [
    {
      "rel": "type",
      "href": "https://example.com/thingmodelgroups/Fabrikam.Lighting/thingmodels/urn.fabrikam.lamp",
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

### 6.2. Thing Description to Endpoint Registry

A WoT-TD 1.1 `forms` entry binds an interaction affordance to a network
endpoint. When a Thing Description shares an endpoint that is independently
managed by an xRegistry [Endpoint Registry][xRegistry Endpoint], the
`forms[].href` value SHOULD be a URL that resolves to (or is consistent with)
the corresponding `endpoint` Resource's protocol bindings.

This specification does not require an `endpoint` Resource to exist for every
`forms` entry, nor does it require any specific naming or correlation
mechanism. Implementations MAY define their own conventions to correlate the
two.

### 6.3. Thing Description to Schema Registry

A WoT-TD 1.1 property, action, or event affordance MAY reference an external
data schema rather than declaring its data schema inline. When the referenced
schema is managed by an xRegistry [Schema Registry][xRegistry Schema], the
reference SHOULD be expressed using the WoT
[`tm:ref`][WoT-TM-1.1] mechanism (in TMs) or a `links` entry with
`"rel": "describedby"` (in TDs), with the `href` resolving to the
`schema` Resource Version's `self` URL.

### 6.4. Affordance Grouping

A Thing Description declares its properties, actions and events in the
`properties`, `actions` and `events` members of a single document, as defined
by [WoT-TD 1.1][WoT-TD-1.1]. This specification requires nothing more:

- A registry MUST accept and serve a valid TD whose affordances are all
  declared in one document, with no grouping construct of any kind.
- A registry MUST NOT require an affordance to belong to a group in order to
  be stored, retrieved, or referenced.
- Nothing in this specification — Resource layout, identity, versioning, or
  cross-referencing — depends on affordances being partitioned.

Proposals to sub-divide a large TD's affordances, such as a `td:submodel`
grouping member, are being discussed in the W3C WoT community. Were such a
mechanism to be standardized, a WoT Registry would store a TD that uses it exactly as
it stores any other TD, since the grouping is a member of the document rather
than of the registry model. Support for it is OPTIONAL, and a registry that
does not understand it MUST still store and serve the document unchanged, per
[Section 5.2](#52-preserving-customer-documents).

This matters for documents the registry did not author: those routinely
contain no grouping construct, and MUST remain fully supported.

## 7. Security

Like the [xRegistry Core][xRegistry Core] specification, this specification
does not explicitly address authentication or authorization levels of users,
nor how to securely protect the APIs.

It is expected that any implementation of this specification will use
authentication and authorization mechanisms that are appropriate for the
application domain and the deployment environment. This MAY include, but is
not limited to, OAuth 2.0, OpenID Connect, API keys, or other mechanisms
appropriate for the use case.

For authorization, the `thingdescriptiongroup` and `thingmodelgroup` concepts provide a
natural authorization boundary, where users can be granted access to specific
groups, and therefore to the Things or Thing Models contained within those
groups. The `thingdescription` and `thingmodel` Resources themselves can be used to
further restrict access to specific Versions, allowing for fine-grained
access control.

Operators of a WoT Registry SHOULD be aware that Thing Descriptions can
expose detailed information about deployed devices, including network
locations, operational endpoints, and security schemes. The
[WoT Security and Privacy Considerations][WoT-Security] document gives
additional guidance.

---

[WoT-TD-1.1]: https://www.w3.org/TR/wot-thing-description11/
[WoT-TM-1.1]: https://www.w3.org/TR/wot-thing-description11/
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
[xRegistry compatibility]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#compatibility-attribute
[xRegistry ancestorid]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#ancestorid-attribute
[xRegistry deprecated]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#deprecated
[xRegistry matchversions]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/model.html#attributesstringmatchversions
[xRegistry version-ids]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#version-ids
[xRegistry hasdocument]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#hasdocument
[xRegistry xref]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#xref-attribute
