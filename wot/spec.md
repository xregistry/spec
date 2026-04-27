# WoT Registry Service - Version 1.0-rc2

<!-- words: WoT JSON-LD Servient affordances affordance discoverability tm td -->
<!-- words: thing thingid thingurl things thingsurl thingscount thingbase -->
<!-- words: thingmodel thingmodels thingmodelid thingmodelurl thingmodelsurl thingmodelscount thingmodelbase -->
<!-- words: thinggroup thinggroups thinggroupid thinggroupsurl thinggroupscount -->
<!-- words: thingmodelgroup thingmodelgroups thingmodelgroupid thingmodelgroupsurl thingmodelgroupscount -->
<!-- words: invokeaction readproperty writeproperty subscribeevent securitydefinitions versionmode urn href -->
<!-- words: workbench fabrikam lamp lighting jwt tenantid deviceid -->
<!-- words: formatvalidated compatibilityvalidated formatvalidatedreason compatibilityvalidatedreason -->

## Abstract

This specification defines a WoT (Web of Things) Registry extension to the
xRegistry document format and API [specification][xRegistry Core]. A WoT
Registry allows for the storage, management and discovery of W3C
[WoT Thing Description (WoT-TD)][WoT-TD-1.1] and
[WoT Thing Model (WoT-TM)][WoT-TM-1.1] documents.

## Table of Contents

- [WoT Registry Service - Version 1.0-rc2](#wot-registry-service---version-10-rc2)
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
      - [2.2.1. Thing](#221-thing)
      - [2.2.2. Thing Model](#222-thing-model)
    - [2.3. Thing Group](#23-thing-group)
    - [2.4. Thing Model Group](#24-thing-model-group)
  - [3. WoT Registry Model](#3-wot-registry-model)
  - [4. WoT Registry](#4-wot-registry)
    - [4.1. Thing Groups](#41-thing-groups)
    - [4.2. Thing Resources](#42-thing-resources)
    - [4.3. Thing Model Groups](#43-thing-model-groups)
    - [4.4. Thing Model Resources](#44-thing-model-resources)
    - [4.5. Formats](#45-formats)
      - [4.5.1. WoT Thing Description](#451-wot-thing-description)
      - [4.5.2. WoT Thing Model](#452-wot-thing-model)
  - [5. Relationships and Cross-References](#5-relationships-and-cross-references)
    - [5.1. Thing Description to Thing Model](#51-thing-description-to-thing-model)
    - [5.2. Thing Description to Endpoint Registry](#52-thing-description-to-endpoint-registry)
    - [5.3. Thing Description to Schema Registry](#53-thing-description-to-schema-registry)
  - [6. Security](#6-security)

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
intended to be reused: a concrete Thing Description may extend or compose one
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
  [Section 5.2](#52-thing-description-to-endpoint-registry).
- A Thing Description's property/action/event data schemas (declared inline
  via WoT data-schema vocabulary) MAY reference external schemas managed by
  the xRegistry Schema Registry; see
  [Section 5.3](#53-thing-description-to-schema-registry).
- A Thing Description MAY reference one or more Thing Models from which it
  is derived; see [Section 5.1](#51-thing-description-to-thing-model).

These cross-references are informative: a WoT Registry implementation MAY
choose to validate them, but this specification does not mandate that all
referents resolve.

### 1.3. Versioning

WoT-TD 1.1 defines an OPTIONAL `version` member with `instance` and `model`
sub-members. Implementations of this specification SHOULD reflect a TD's or
TM's `version.instance` (or, when absent, an implementation-chosen identifier)
into the xRegistry [`versionid`][xRegistry version-ids] when ingesting the
document.

The xRegistry Core versioning rules (monotonically increasing integer
`versionid`s, `ancestor` lineage, default-Version selection) apply unchanged.
A breaking change to a TD or TM that violates the Resource's
[`compatibility`][xRegistry compatibility] policy MUST result in a new
Resource, not a new Version.

### 1.4. Document Store

The WoT Registry is a document store: the `things` and `thingmodels` Resources
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

#### 2.2.1. Thing

We use the term **Thing** (or `thing` Resource) in this specification as a
logical grouping of **Thing Versions**. A **Thing Version** is a concrete
WoT-TD 1.1 JSON-LD document. The **Thing** Resource is a semantic umbrella
formed around one or more concrete Thing Description documents that represent
iterations of the same logical Thing instance. Per the definition of the
[`compatibility`][xRegistry compatibility] attribute, all Versions of a single
**Thing** MUST adhere to the rules defined by the `compatibility` attribute.
Any breaking change MUST result in a new **Thing** Resource being created.

#### 2.2.2. Thing Model

We use the term **Thing Model** (or `thingmodel` Resource) in this
specification as a logical grouping of **Thing Model Versions**. A **Thing
Model Version** is a concrete WoT-TM 1.1 JSON-LD document. As with Things,
versioning is governed by the Resource's `compatibility` attribute.

A Thing Model is distinguished from a Thing by purpose: a Thing Model
describes a **class** of Things and typically lacks concrete `href` values in
its forms, whereas a Thing Description describes a **specific** deployed Thing
instance.

### 2.3. Thing Group

A Thing Group is a container for Thing Descriptions that are related to each
other in some application-defined way (for example, all TDs for a tenant, a
fleet, or a physical site). This specification does not impose any
restrictions on what Things can be contained in a Thing Group.

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

  "thinggroupsurl": "<URL>",                       # ThingGroups collection
  "thinggroupscount": <UINTEGER>,
  "thinggroups": {
    "KEY": {                                       # thinggroupid
      "thinggroupid": "<STRING>",                  # xRegistry core attributes
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

      "thingsurl": "<URL>",                        # Things collection
      "thingscount": <UINTEGER>,
      "things": {
        "KEY": {                                   # thingid
          "thingid": "<STRING>",                   # xRegistry core attributes
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
          "ancestor": "<STRING>",
          "contenttype": "<STRING>", ?            # SHOULD be application/td+json
          "format": "<STRING>",                    # MUST be "WoT-TD/1.1"
          "formatvalidated": <BOOLEAN>, ?
          "formatvalidatedreason": "<STRING>", ?
          "compatibilityvalidated": <BOOLEAN>, ?
          "compatibilityvalidatedreason": "<STRING>", ?

          "thingurl": "<URL>", ?
          "thing": <ANY> ?                         # the WoT-TD JSON-LD document
          "thingbase64": "<STRING>", ?
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
      "thingmodelgroupid": "<STRING>",
      # ... xRegistry Group-level attributes ...

      "thingmodelsurl": "<URL>",                   # ThingModels collection
      "thingmodelscount": <UINTEGER>,
      "thingmodels": {
        "KEY": {                                   # thingmodelid
          "thingmodelid": "<STRING>",
          "versionid": "<STRING>",
          # ... xRegistry Resource and default-Version attributes ...

          "format": "<STRING>",                    # MUST be "WoT-TM/1.1"
          "contenttype": "<STRING>", ?            # SHOULD be application/tm+json
          "thingmodelurl": "<URL>", ?
          "thingmodel": <ANY> ?                    # the WoT-TM JSON-LD document
          "thingmodelbase64": "<STRING>", ?

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

### 4.1. Thing Groups

The Group (`<GROUP>`) name for Thing Descriptions is `thinggroup` (singular).
The plural, used as the collection name, is `thinggroups`. The Thing Group
does not have any specific extension attributes.

A Thing Group is a collection of Thing Descriptions that are related to each
other in some application-defined way. A Thing Group does not impose any
restrictions on the contained Things.

Every Thing Description (i.e. the `thing` Resource) MUST reside inside a Thing
Group.

Example:

```yaml
{
  "specversion": "1.0-rc2",
  # other xRegistry top-level attributes excluded for brevity

  "thinggroupsurl": "https://example.com/thinggroups",
  "thinggroupscount": 1,
  "thinggroups": {
    "fabrikam.factory-floor-01": {
      "thinggroupid": "fabrikam.factory-floor-01",
      # other xRegistry Group-level attributes excluded for brevity

      "thingsurl": "https://example.com/thinggroups/fabrikam.factory-floor-01/things",
      "thingscount": 12
    }
  }
}
```

### 4.2. Thing Resources

The Resource (`<RESOURCE>`) inside of Thing Groups is named `thing`. The
plural, used as the collection name, is `things`. Any single `thing` is a
container for one or more `versions`, each of which holds the concrete
WoT-TD 1.1 JSON-LD document.

The `format` attribute of a `thing` Resource Version MUST be `"WoT-TD/1.1"`.
The `contenttype` of a `thing` document SHOULD be `application/td+json` per
[WoT-TD 1.1][WoT-TD-1.1].

All Versions of a single Thing Resource MUST adhere to the semantic rules of
the Thing's [`compatibility`][xRegistry compatibility] attribute, if specified.

Implementations of this specification SHOULD use the xRegistry default
algorithm for generating new `versionid` values and for determining which is
the latest Version. See [Version IDs][xRegistry version-ids] for more
information.

When a Thing Description carries a WoT `version.instance` value, that value
SHOULD be used as the xRegistry `versionid`, provided it satisfies the
constraints of the Resource's `versionmode`.

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
`"WoT-TM/1.1"`. The `contenttype` SHOULD be `application/tm+json` per
[WoT-TM 1.1][WoT-TM-1.1].

The same `compatibility`, `versionid`, and `ancestor` rules described for
`thing` Resources apply to `thingmodel` Resources.

### 4.5. Formats

This specification refines the
[core specification's `format`](../core/spec.md#format-attribute) for use in
a WoT Registry by defining the format identifiers a WoT Registry MUST
recognize. Implementations MAY define extension format identifiers for
non-W3C Thing-description dialects, but MUST NOT use the identifiers below
for any document that is not conformant with the corresponding W3C
specification.

#### 4.5.1. WoT Thing Description

- Format identifier: `WoT-TD/1.1`
- Document: a JSON-LD 1.1 document conformant with
  [W3C WoT Thing Description 1.1][WoT-TD-1.1].
- The document's `@context` MUST include
  `https://www.w3.org/2022/wot/td/v1.1`.
- A URI-reference pointing to a TD MAY use a JSON-Pointer
  ([RFC 6901](https://www.rfc-editor.org/rfc/rfc6901)) fragment to deep-link
  into a particular property, action, or event affordance, e.g.
  `…/things/lamp-42#/properties/status`.

#### 4.5.2. WoT Thing Model

- Format identifier: `WoT-TM/1.1`
- Document: a JSON-LD 1.1 document conformant with
  [W3C WoT Thing Model 1.1][WoT-TM-1.1].
- The document's `@context` MUST include
  `https://www.w3.org/2022/wot/td/v1.1` and the document's top-level
  `@type` MUST include `tm:ThingModel`.
- Deep-linking via JSON-Pointer fragments is permitted, as for TDs.

## 5. Relationships and Cross-References

This section is informative.

### 5.1. Thing Description to Thing Model

A WoT-TD 1.1 document MAY declare that it conforms to one or more Thing Models
using the `links` member with `"rel": "type"`, per
[WoT-TD 1.1 §6.3.4][WoT-TD-1.1]. When the referenced Thing Model resides in
the same WoT Registry, the `href` SHOULD point to that Thing Model's
[`self`][xRegistry self] URL (or `shortself` URL).

For example:

```json
{
  "@context": "https://www.w3.org/2022/wot/td/v1.1",
  "@type": "Thing",
  "title": "Lamp #42",
  "links": [
    {
      "rel": "type",
      "href": "https://example.com/thingmodelgroups/fabrikam.lighting/thingmodels/lamp",
      "type": "application/tm+json"
    }
  ]
}
```

A registry MAY also surface this relationship through standard xRegistry
[`xref`][xRegistry xref] mechanisms when the implementation chooses to model
the Thing-to-Thing-Model link as a registry-native cross-reference.

### 5.2. Thing Description to Endpoint Registry

A WoT-TD 1.1 `forms` entry binds an interaction affordance to a network
endpoint. When a Thing Description shares an endpoint that is independently
managed by an xRegistry [Endpoint Registry][xRegistry Endpoint], the
`forms[].href` value SHOULD be a URL that resolves to (or is consistent with)
the corresponding `endpoint` Resource's protocol bindings.

This specification does not require an `endpoint` Resource to exist for every
`forms` entry, nor does it require any specific naming or correlation
mechanism. Implementations MAY use [`endpointuri`][xRegistry endpoint] or
similar conventions to correlate the two.

### 5.3. Thing Description to Schema Registry

A WoT-TD 1.1 property, action, or event affordance MAY reference an external
data schema rather than declaring its data schema inline. When the referenced
schema is managed by an xRegistry [Schema Registry][xRegistry Schema], the
reference SHOULD be expressed using the WoT
[`tm:ref`][WoT-TM-1.1] mechanism (in TMs) or a `links` entry with
`"rel": "describedby"` (in TDs), with the `href` resolving to the
`schema` Resource Version's `self` URL.

## 6. Security

Like the [xRegistry Core][xRegistry Core] specification, this specification
does not explicitly address authentication or authorization levels of users,
nor how to securely protect the APIs.

It is expected that any implementation of this specification will use
authentication and authorization mechanisms that are appropriate for the
application domain and the deployment environment. This MAY include, but is
not limited to, OAuth 2.0, OpenID Connect, API keys, or other mechanisms
appropriate for the use case.

For authorization, the `thinggroup` and `thingmodelgroup` concepts provide a
natural authorization boundary, where users can be granted access to specific
groups, and therefore to the Things or Thing Models contained within those
groups. The `thing` and `thingmodel` Resources themselves can be used to
further restrict access to specific Versions, allowing for fine-grained
access control.

Operators of a WoT Registry SHOULD be aware that Thing Descriptions can
expose detailed information about deployed devices, including network
locations, operational endpoints, and security schemes. The
[WoT Security and Privacy Considerations][WoT-Security] document gives
additional guidance.

---

[WoT-TD-1.1]: https://www.w3.org/TR/wot-thing-description11/
[WoT-TM-1.1]: https://www.w3.org/TR/wot-thing-description11/#thing-model
[WoT-Discovery]: https://www.w3.org/TR/wot-discovery/
[WoT-Security]: https://www.w3.org/TR/wot-security/
[xRegistry Core]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html
[xRegistry Endpoint]: https://xregistry.io/xreg/xregistryspecs/endpoint-v1/docs/spec.html
[xRegistry Message]: https://xregistry.io/xreg/xregistryspecs/message-v1/docs/spec.html
[xRegistry Schema]: https://xregistry.io/xreg/xregistryspecs/schema-v1/docs/spec.html
[xRegistry self]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#self-attribute
[xRegistry compatibility]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#compatibility-attribute
[xRegistry version-ids]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#version-ids
[xRegistry hasdocument]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#hasdocument
[xRegistry endpoint]: https://xregistry.io/xreg/xregistryspecs/endpoint-v1/docs/spec.html
[xRegistry xref]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#xref-attribute
