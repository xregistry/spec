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

## Abstract

This specification extends the xRegistry document format and API
[specification][xRegistry Core] with a WoT (Web of Things) Registry for
storing, managing and discovering W3C
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
    - [5.4. Versioned Reference Resolution](#54-versioned-reference-resolution)
      - [5.4.1. Floors and Pins](#541-floors-and-pins)
      - [5.4.2. Resolver Algorithm](#542-resolver-algorithm)
      - [5.4.3. Errors and Test Vectors](#543-errors-and-test-vectors)
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

Device fleets, gateways, integrators and consuming applications use the
Registry to share Thing metadata and discover Things and their templates as
described by W3C [WoT Discovery][WoT-Discovery]. TDs and TMs can also be
cross-referenced from xRegistry [Endpoint][xRegistry Endpoint],
[Message][xRegistry Message], and [Schema][xRegistry Schema] entries.

### 1.1. Thing Descriptions and Thing Models

A Thing Description (TD) is a JSON-LD 1.1 document conforming to
[WoT-TD 1.1][WoT-TD-1.1]. It identifies a deployed Thing, declares its
properties, actions and events, and provides `forms` that bind those
interaction affordances to network endpoints over protocols such as HTTP,
MQTT, CoAP, OPC-UA or Modbus.

A Thing Model (TM) is a JSON-LD 1.1 document conforming to
[WoT-TM 1.1][WoT-TM-1.1]. It describes an abstract class of Things and
typically omits `href` values from its forms. Thing Models are reusable: a
concrete Thing Description MAY extend or compose one or more Thing Models
through WoT `tm:extends` and `tm:ref` mechanisms or JSON-LD `@type`
declarations.

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

This specification does not require the Registry to resolve or validate these
cross-references. An implementation MAY check that a referent exists, but it
still stores and serves the document when a referent is absent. A Consumer
composing a TD from Thing Models or binding an affordance to an endpoint
depends on those references independently of the Registry's checks.

### 1.3. Versioning

Each Version of a `thingdescription` or `thingmodel` Resource holds a complete
WoT document, stored without rewriting its bytes. A Resource's `wotid` and
registry Resource id are stable across compatible revisions. `wotid` is
declared with [`matchversions`][xRegistry matchversions]. A registry MUST
reject a Version that supplies a different `wotid`. A Thing Model's major
version MUST be part of its `wotid`. A breaking change MUST use a new `wotid`
and a new Resource
([Section 5.1.1](#511-breaking-changes-and-successor-identifiers)).

Thing Model Resources and Thing Description Resources MUST use Core
[`versionmode`][Core versionmode] `semver` and
[`singleversionroot`][Core singleversionroot] `true`. Core orders each
Resource's [`ancestorid`][Core ancestorid] lineage by SemVer precedence and
forbids multiple roots with these aspects. The assignment rules for the
corresponding authored fields are:

| Resource | Authored field | Valid SemVer | Missing or non-SemVer |
| --- | --- | --- | --- |
| TM | `version.model` | `versionid` MUST equal the authored value verbatim. | The registry MUST assign `0.0.0-N`. |
| TD | `version.instance` | `versionid` MUST equal the authored value verbatim. | The registry MUST assign `0.0.0-N`. |

For either Resource type, the registry MUST inspect the authored field
without modifying the stored document. The original authored field MUST NOT
be rewritten, including when absent or non-SemVer.

A valid authored value is SemVer 2.0.0 without build metadata and fits Core's
128-character [id constraint][Core id constraints]. SemVer build metadata
(`+build`) MUST be rejected as `invalid-version`, since `+` is not allowed by
Core's id constraints. An authored SemVer value that exceeds Core's
128-character id limit MUST also be rejected under those constraints.

`N` is the lowest positive integer whose complete id is not already used
in the Resource. The registry MUST assign an omitted `versionid`. A supplied
`versionid` MUST equal the authored or generated assignment, or the registry
MUST reject it as `version-mismatch`. A supplied id that violates Core's id
grammar MUST be rejected as `invalid-version` before this comparison. Core
requires an immutable, unique [`versionid`][Core versionid]. This extension
defines the assignment in place of its default
[Version ID algorithm][Core Version IDs].

The Registry MUST perform assignment and creation atomically with respect to
concurrent writes, so two writes cannot claim the same generated id.

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

A TD's `version.model` describes a model dependency. Only a TD's
`rel: "type"` link uses it as an implicit floor. It does not determine the
TD's instance version or supply a floor for a TD-to-TD reference. The
proposed TD composition operators `td:extends`, `td:subthing`, and `td:ref`
resolve under Sections 5.4 and 6.2. A projection plan selects sources by
target kind: `tm:minVersion` is uncapped for TMs, while `td:minVersion`
uses a TD caret range. An unfloored TD source can cross major versions.
The projection envelope's own `version.model` and `version.instance` do
not set a source floor.

The following illustrative JSON fragments show the authored version and the
Version attributes assigned by the registry. Ellipses mark omitted members.
They are not JSON tokens.

```json
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

```json
{
  "versionid": "1.4.0",
  "versionorigin": "authored",
  ...
}
```

A TD can identify its instance revision independently of its model dependency:

```json
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
revision MUST NOT remove or narrow an affordance, a data schema or an `@type`,
and MUST NOT introduce a new mandatory member. Narrowing includes reducing
the accepted values or operations of an existing member. These constraints
apply to every earlier Version in the Resource's Core
[`ancestorid`][Core ancestorid] lineage.

A Registry MAY validate this domain-specific compatibility rule through Core's
[`validatecompatibility`][Core validatecompatibility]
capability. Core's [`strictvalidation`][Core strictvalidation] rules still
apply. Absence of a domain validator does not permit a Producer to publish an
incompatible revision under the same `wotid`.

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
`singleversionroot`. An operator MUST NOT claim that an unresolved multiple-root
Resource conforms to this model.

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
`application/td+json` for TDs and `application/tm+json` for TMs, per
[WoT-TD 1.1 §12.1 and §12.2][WoT-TD-1.1].

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
Server-unknown extension attributes MUST be silently stored in the backing
datastore. Specification-defined, and server-known extension, attributes MUST
generate an error if the corresponding feature is not supported or enabled.

However, as with all attributes, if accepting the attribute results in a bad
state (such as exceeding a size limit or resulting in a security issue), then
the server MAY choose to reject the request.

In the pseudo JSON format snippets `?` means the preceding attribute is
OPTIONAL, `*` means the preceding attribute MAY appear zero or more times,
and `+` means the preceding attribute MUST appear at least once. The presence
of the `#` character means the remaining portion of the line is a comment.
Whitespace characters in the JSON snippets are used for readability and are
not normative.

### 2.2. Terminology

This specification defines the following terms:

#### 2.2.1. Thing Description

This specification uses Thing Description (or `thingdescription` Resource) for
a logical grouping of Thing Description Versions. Each Version holds a concrete
WoT-TD 1.1 JSON-LD document for the same Thing instance. The Resource groups
one or more such documents and provides a stable alias for its
[default Version][xRegistry version-ids], which is addressed when no Version
is named.

The TD's `version.instance` carries its revision, including breaking major
revisions. A major revision remains under the same `id`, `wotid`, and Resource.
If a Resource declares the [`compatibility`][xRegistry compatibility] attribute,
all its Versions MUST adhere to that policy. A TD that identifies a different
Thing MUST use that Thing's `id` and a corresponding Resource. See
[Section 1.3](#13-versioning).

#### 2.2.2. Thing Model

This specification uses Thing Model (or `thingmodel` Resource) for a logical
grouping of Thing Model Versions. Each Version holds a concrete WoT-TM 1.1
JSON-LD document. As with Things, the Resource's `compatibility` attribute
governs versioning.

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
application-defined way, for example all TDs for a tenant, fleet or physical
site. This specification does not restrict which Thing Descriptions a Group
can contain.

### 2.4. Thing Model Group

A Thing Model Group contains Thing Models related in an application-defined
way, for example all TMs published by one vendor or for one product family.
This specification does not restrict which Thing Models a Group can contain.

## 3. WoT Registry Model

The authoritative xRegistry extension model of the WoT Registry resides in
[model.json](model.json). Its `modelversion` is `0.1` while this remains a
working draft. It versions the WoT model independently of the xRegistry Core
specification version in a Registry's `specversion`.

The JSON serialization of a WoT Registry adheres to this form:

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

The WoT Registry organizes Thing Descriptions, Thing Models and their Versions.
It stores both their metadata and their documents.

Implementations of this specification MAY include additional extension
attributes, including the `*` attribute of type `any`.

Groups, Resources and Versions inherit their Core attributes from the
[xRegistry specification][xRegistry Core].

### 4.1. Thing Description Groups

A Thing Description Group collects Thing Descriptions related in an
application-defined way, without restricting the contained Thing Descriptions.
Its Group Type (`<GROUP>`) name is `thingdescriptiongroup` (singular), and
its collection name is `thingdescriptiongroups`. It has no specific extension
attributes.

Every Thing Description (the `thingdescription` Resource) MUST reside inside
a Thing Description Group.

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

Thing Description Resources MUST use Core [`versionmode`][Core versionmode]
value `semver` and [`singleversionroot`][Core singleversionroot]
value `true`, as specified in [Section 1.3](#13-versioning). Core derives
`ancestorid` by SemVer precedence and enforces one root
([`ancestorid`][Core ancestorid]).

The Version-level `versionorigin` attribute is REQUIRED, read-only, and uses
the strict enumeration `authored` or `generated`. The `versionid` is assigned
from `version.instance` when that member is SemVer without build metadata.
Otherwise it is the lowest free `0.0.0-N` id. The original document bytes,
including `version.instance`, are not rewritten.

The `format` attribute of a `thingdescription` Resource Version MUST be
`"JSON-LD/1.1"`. [model.json](model.json) declares the `format` enumeration
as `strict`, so a registry rejects any other value rather than merely
discouraging it.

The `contenttype` of a `thingdescription` document MUST be
`application/td+json` per [WoT-TD 1.1 §12.1][WoT-TD-1.1], or another media
type the deployment has explicitly registered for WoT documents.

`contenttype` is client-supplied and determines the media type used to serve
the stored bytes through the document view
([Section 1.4](#14-document-store)). A Registry MUST NOT serve a stored
document under a client-supplied media type that would interpret it as active
content, such as `text/html`, `image/svg+xml` or `application/xhtml+xml`.
A Registry MUST either reject such a write or serve the document under the
media type this section requires.

WoT tooling dereferences a Version's document-view URL directly. For documents
it did not author, a Registry SHOULD additionally return
`X-Content-Type-Options: nosniff` or serve them from an origin separate from
any Registry user interface. See [Section 7](#7-security).

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

Every Thing Model (i.e. the `thingmodel` Resource) MUST reside inside a Thing
Model Group.

### 4.4. Thing Model Resources

A Thing Model Resource groups one or more `versions`, each holding a concrete
WoT-TM 1.1 JSON-LD document. Within Thing Model Groups, its Resource Type
name is `thingmodel` and its collection name is `thingmodels`. Each
`thingmodel` represents the logical grouping.

The `format` attribute of a `thingmodel` Resource Version MUST be
`"JSON-LD/1.1"`, enforced by the same `strict` enumeration used for
`thingdescription`. The `contenttype` MUST be `application/tm+json` per
[WoT-TM 1.1 §12.2][WoT-TM-1.1], or another media type the deployment has
explicitly registered for WoT documents, and the same constraint on serving
stored bytes as active content applies as in
[Section 4.2](#42-thing-description-resources).

The `compatibility`, `versionid`, `versionorigin` and
[`ancestorid`][Core ancestorid] rules for Thing
Models are defined in [Section 1.3](#13-versioning), subject to Core's
[`compatibility`][Core compatibility] and
[`versionid`][Core versionid] semantics. The Version-level `versionorigin` is a REQUIRED
string with the strict enumeration `authored` or `generated`, and is
read-only. The model declares `compatibility` under `metaattributes`, with
`required: true` and `default: backward`, as Core requires for an attribute
with a default.

The `wotid` attribute is REQUIRED on a `thingmodel` and holds the document's
authored WoT identifier, which is distinct from the `thingmodelid`. Where a
Thing Model extends another via a `tm:extends` link relation, or references
one via `tm:ref`, or composes one via `tm:submodel`, the referenced Thing
Models' `wotid`s SHOULD be listed in `derivedfrom`.

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

Tools and autonomous agents need explicit metadata to choose among documents
describing similar Things rather than inferring their provenance from titles
or naming conventions. Both `thingdescription` and `thingmodel` Resources
carry the following OPTIONAL attributes:

| Attribute | Type | Meaning |
|---|---|---|
| `license` | string | The license the document is offered under, as an [SPDX][SPDX] license expression or a URL |
| `publisher` | string | The organization that published the document |
| `standardsbody` | string | The standards organization that defines or endorses the document, where one does |
| `canonicalurl` | url | The canonical upstream location of the document, where it is also published outside this registry |
| `maturity` | string | One of `Standard`, `Vendor`, `Community` or `Experimental` |

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
whether by Group, writer identity or an out-of-band signature. It MUST NOT be
used to establish trust in a document from an untrusted writer.

One `wotid` MAY legitimately match several Resources written by different
parties ([Section 5.3](#53-lookup)), so a Consumer can face this choice.
See also [Section 7](#7-security).

These attributes are also not part of a document's semantic identity. A
registry MUST NOT treat two documents as the same document because their
provenance attributes agree, nor as different documents because they differ:
identity is `wotid` alone
([Section 5.1](#51-wot-identifiers-and-registry-ids)).

They are Version attributes, carried on each Version alongside the document
they describe, as `format` and `wotid` are. This specification defines no
special update semantics for them. They are written and updated exactly as any
other Version attribute is, under the xRegistry Core rules.

## 5. Identity and Resolution

### 5.1. WoT Identifiers and Registry Ids

xRegistry gives every entity an id — a `thingdescriptionid` or
`thingmodelid` for a Resource — and an [`xid`][xRegistry Core], the stable
path those ids form within the registry. Each entity id is constrained to
[RFC 3986][RFC3986] `unreserved` characters plus `:` and `@`, starting with a
letter, a digit or `_`, at most 128 characters long, and unique
case-insensitively within its parent. A WoT identifier is the value of a TD's
or TM's `id` member: a URI, most often a URN such as `urn:fabrikam:lamp:42`,
but equally a URL such as `https://fabrikam.example/things/lamp-42`.

These identifiers serve a similar purpose but follow different grammars.
`https://fabrikam.example/things/lamp-42` is not a valid entity id or `xid`
component. An `xid` is not what a Thing author writes. Where an authored
identifier satisfies the id grammar, a client MAY use it as the Resource id.
A Registry cannot rely on that choice.

This specification therefore does not equate them, and does not define a
mapping between them:

> A `thingdescription`'s `wotid` is its document's identity in the WoT
> identifier space ([Section 2.2.3](#223-wot-identifier)). Its
> `thingdescriptionid` is the Resource's id *within this registry* and is
> chosen by the client that creates the Resource, subject to the xRegistry
> Core id rules and to whatever further naming constraints the deployment
> imposes. Neither is derived from the other. The same applies to a
> `thingmodel`'s `wotid` and `thingmodelid`.

A client creating a Resource therefore chooses its id the same way it chooses
a Group id:

- It names the id in the request path.
- It supplies the id in the request body.
- It omits the id and lets the registry assign one under the xRegistry
  Core rules.

The document does not dictate this choice, and later resolution does not
depend on it. A Consumer holding a WoT identifier queries the first-party
`wotid` attribute ([Section 5.3](#53-lookup)) to find the Resource rather than
reconstructing its path.

A deployment MAY derive its Resource ids from `wotid` values by a convention
of its own. The [OpenUSD Artifact Registry][OpenUSD Draft] working draft
defines one such construction. No convention is mandated by this
specification, and a Consumer MUST NOT assume that an id it did not assign
was produced by one.

A `wotid` MUST NOT encode a compatible revision of the document it names. A
Thing Model's major version MUST be included in that stable identity, for
example `urn:fabrikam:lamp:v1` or `https://fabrikam.example/tm/lamp/v1`. Minor
and patch revisions are carried by `versionid` and `version.model`, not
appended to the identifier. No particular spelling of the major-version token
is mandated.

When a document is revised compatibly, its `wotid` and Resource id MUST
remain unchanged, and a new Version is created under the same Resource. A
Thing Model breaking revision uses a distinct major-version `wotid` as
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

[Decision 4](decisions.md#4-wotid-is-a-required-indexed-first-party-attribute)
records that whether a future revision ought to define a derivation for the
second case is not yet settled.

#### 5.1.1. Breaking Changes and Successor Identifiers

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
A vendor, standards body or toolchain can supply a document, and artifacts
outside the Registry can already reference it.

- A registry MUST store the WoT document byte-for-byte as supplied, apart from
  transformations the client explicitly requested.
- A registry MUST NOT rewrite the document's `id` member, its `links[].href`
  values, its `tm:extends` or `tm:ref` targets, or any other identifier
  internal to the document, into registry-specific identifiers.
- A retrieval of a stored Version through the document view MUST return the
  exact bytes supplied, as the xRegistry Core document view already requires.
  Re-serializing the document — reordering members, re-indenting, or
  normalizing its JSON-LD — is not permitted.

Rewriting is incompatible with these documents for three reasons:

- A TM published by a standards body is referenced by `id` from artifacts
  outside the registry, and rewriting the `id` would break those references
  while leaving the registry's own copy claiming to be the standard document.
- A TD's `tm:extends` target resolves in the WoT identifier space, so a
  rewritten target no longer matches what any other WoT tool would look for.
- A document copied between two registries would acquire two different
  identities for the same bytes, so neither registry could tell the copies
  apart from distinct documents.

The Registry identifies a document externally through its `thingdescriptionid`
or `thingmodelid` and the resulting `xid`. The document's authored identifiers
are carried alongside it, unchanged, in `wotid` and `derivedfrom`. Keeping
these identifier spaces separate allows the document to round-trip unchanged.

Where a registry wants the TD-to-TM link to be traversable without parsing the
document, it records the referenced Thing Models' *authored* identifiers in
the `derivedfrom` attribute. `derivedfrom` holds `wotid` values, not `xid`s,
so they can be compared directly with the document's authored references.

`derivedfrom` is a producer-supplied *index* of the document's references, not
an authority over them. A registry MAY verify that it matches the
`tm:extends`, `tm:submodel`, `tm:ref` and `links[].rel="type"` targets in the
stored document, and SHOULD reject a write where the two disagree. Where a
registry does not verify, the document is authoritative.

When making a trust, allow-list or compliance decision about a document's
lineage, a Consumer MUST derive that lineage from the document itself and
MUST NOT rely on `derivedfrom` alone.

### 5.3. Lookup

A Consumer holding a WoT identifier — typically from a `tm:extends` link, a
`tm:ref`, another `links[].href` or a message attribute — can resolve it to a
stored document in either of two ways.

**By path.** Where the Consumer already knows the Resource's Group and id —
because it was given them, or because it follows a stored `self` URL — it
addresses the Resource directly:

```
/thingmodelgroups/<thingmodelgroupid>/thingmodels/<thingmodelid>
```

**By `wotid`.** Otherwise — the usual case, since WoT documents reference one
another by authored identifier rather than by registry path — it queries on
the `wotid` attribute:

```
GET /thingmodels?filter=wotid=urn:fabrikam:lamp:v1
```

An implementation SHOULD serve this query in time that does not grow with
collection size, in practice by indexing `wotid` on both `thingdescriptions`
and `thingmodels`. A linear scan for each reference would make TD composition
slower as the collection grows.

A `wotid` SHOULD be unique within a Group, so that a Group-scoped query for
one identifies a single Resource. Across Groups a `wotid` MAY repeat — the
same vendor TM legitimately appears in two tenants' Groups. A
registry-wide query MAY therefore match more than one Resource. A caller
that needs exactly one narrows the query by naming the Group.

A Registry-wide query MUST return every matching Resource rather than an
arbitrary one of them. [Section 4.6](#46-provenance-and-selection-metadata)
governs how a Consumer chooses among them.

Version selection is separate from the *identifier*. The URL carries the
selection through the `versions` collection:

| Intent | Request |
|---|---|
| Latest Version | the Resource's URL, which serves its default Version |
| A specific Version | `<resource-url>/versions/<versionid>` |
| Enumerate Versions | `<resource-url>/versions` |

`<resource-url>` above is the Resource's [`self`][xRegistry self] URL for the
metadata view, or that URL with the `$details` suffix removed for the
document view. See [Section 1.4](#14-document-store).

A request to the Resource URL without a Version returns the Core default,
even when [`defaultversionsticky`][Core defaultversionsticky]
is true. A registry MUST serve that default
when no Version is named.

For reference resolution, a resolver MUST use
[Section 5.4](#54-versioned-reference-resolution), not lexical id order,
publication time or an assumption that the default satisfies the reference.

Callers SHOULD NOT fold the identifier and version into one opaque string.
When carrying both through a transport, such as message headers, a caller
SHOULD use separate values, for example a
`wotid` header and a `versionid` header, rather than a single compound token
like `urn:fabrikam:lamp@3` that every recipient has to take apart. The
identifier stays a WoT identifier, and the version stays a `versionid` the
recipient can put straight into a URL.

### 5.4. Versioned Reference Resolution

#### 5.4.1. Floors and Pins

A reference MAY carry a minimum SemVer, called its floor, but MUST NOT carry
a version range. `tm:minVersion` is a member of `tm:extends` or
`tm:submodel` links and a sibling of `tm:ref`. `td:minVersion` is a member
of `td:extends` or `td:subthing` links and a sibling of `td:ref`.

A floor MUST be a SemVer 2.0.0 string without build metadata and within Core's
128-character [id limit][Core id constraints]. It MUST NOT have the generated
`0.0.0-N` form.
Invalid syntax or a generated floor MUST produce `invalid-version`.
`td:minVersion` on a TM reference and `tm:minVersion` on a TD-to-TD
reference MUST produce `invalid-floor`.

A TM floor has no upper bound. The TM major is part of its `wotid`. A TD
floor `X.Y.Z` admits target versions greater than or equal to `X.Y.Z` and
below `(X+1).0.0`, including when X is zero. It also excludes prereleases
whose major is `X+1`.

A TD reference without a floor has no lower or upper bound and can select a
version in any major. Neither the referencing TD's `version.instance` nor its
`version.model` supplies an implicit floor for a TD-to-TD reference. The
`version.model` implicit floor applies only to a TD's `rel: "type"` link to
a TM.

For a TD with exactly one `rel: "type"` link, its `version.model`, when
present, is the implicit floor of that link. If the link also has an explicit
`tm:minVersion`, the greater value by SemVer precedence is the effective
floor. An explicit lower value MUST NOT weaken the implicit floor. If only one
floor is present, that floor applies.

For a TD with several type links and `version.model`, every type link MUST
carry its own `tm:minVersion`. Otherwise, resolution MUST fail as
`ambiguous-floor`, including when resolving a different, fully specified link.
When every link has a floor, each link MUST use the greater of its own floor
and `version.model`.

For several type links without `version.model`, each link uses its own floor
if present. An omitted floor MUST NOT produce `ambiguous-floor`.

A non-SemVer implicit floor MUST produce `invalid-version`.

A resolver MUST return `(wotid, versionid, contentdigest, origin)`, where
`origin` identifies the registry from which the stored bytes were obtained
and `contentdigest` is the digest of those bytes. A Consumer MAY retain this
tuple outside the document and pass either a digest pin or a `versionid` pin
on a subsequent resolution. A request MUST contain at most one kind of pin.
Documents MUST NOT carry registry version pins or digest pins. A floor is a
compatibility requirement, not a pin. Authored references and document bytes
MUST remain portable between registries.

#### 5.4.2. Resolver Algorithm

The caller selects a registry and Group scope identifying one Resource by
`wotid`, following [Section 5.3](#53-lookup). For `tm:ref` or `td:ref`, the
lookup target is the document identifier resolved from the reference URI,
excluding any fragment. The fragment is applied after version selection.
Resource disambiguation across Groups precedes this algorithm.

Core defines Resource defaults and Version lineage through
[`defaultversionsticky`][Core defaultversionsticky],
[`versionmode`][Core versionmode],
and [`ancestorid`][Core ancestorid]. This resolver
uses those Core values but applies target-kind floors before returning an
unpinned candidate.

The resolver MUST apply these steps in order:

1. Find the Resource whose `wotid` equals the reference target. If none
   exists, fail as `not-found`. A deprecated Resource is eligible and MUST
   NOT be replaced automatically by its `deprecated.alternative`.
2. If a digest pin is supplied, return a Version with that `contentdigest`,
   or fail as `pin-mismatch`. For duplicate bytes, return the Version with
   highest SemVer precedence. If a `versionid` pin is supplied, return that
   exact Version or fail as `not-found`. Pins bypass floor derivation, the TD
   major cap, prerelease filtering and sticky-default selection. They do not
   authorize substituting bytes or following a successor.
3. Derive the target kind and floor as specified in Section 5.4.1. Report
   `ambiguous-floor` before validating individual floors when the
   multiple-type-link rule is violated.
4. If [`defaultversionsticky`][Core defaultversionsticky] is true, select
   `defaultversionid` as-is. Do not substitute another Version or apply
   prerelease filtering to a sticky choice. If it is unavailable, fail as
   `not-found`. If a floor exists and the selected Version is below it, or a
   TD target's major is at least `floor.major + 1`, fail as `unsatisfied`.
5. Otherwise, exclude prereleases, including generated ids, unless the floor
   is a prerelease or the caller opts in with `allowPrerelease`. For TD targets
   with a floor, also exclude Versions below the floor and those with
   major at least `floor.major + 1`, including prereleases of the next major.
   Select the highest remaining Version by SemVer precedence. If none is
   eligible, fail as `unsatisfied`. A generated-only Resource requires an
   opt-in, pin or sticky default.
6. If a floor exists and the selected Version is below it, or a TD target's
   major is at least `floor.major + 1`, fail as `unsatisfied`. Never downgrade,
   bypass a sticky default or retry with a lower Version.
   Otherwise return `(wotid, versionid, contentdigest, origin)`.

For an unpinned reference, only SemVer Versions from a conforming Resource of
the indicated target kind are inputs. A TD Resource's `versionid` is derived
from `version.instance`. A TM Resource's is derived from `version.model`.

#### 5.4.3. Errors and Test Vectors

| Error | Meaning |
|---|---|
| `not-found` | Resource, pinned Version or sticky default is absent. |
| `pin-mismatch` | The target Resource has no Version with the caller's digest. |
| `unsatisfied` | No eligible Version exists, or the selected Version is below the floor or outside the TD major cap. |
| `ambiguous-floor` | A TD has `version.model`, several type links and at least one link without its own floor. |
| `invalid-floor` | A floor term is used with a reference to the other document kind. |
| `version-mismatch` | A supplied publication `versionid` disagrees with the authored or generated assignment. |
| `invalid-version` | A floor or publication version violates the version syntax or generated-floor restriction. |

These names identify domain outcomes, not replacements for Core's protocol
error envelopes or its [`versionid`][Core versionid]
constraints. The
[canonical resolution vectors](tests/resolution/README.md) define portable
resolver inputs and expected outcomes, including write-side version
assignment.

## 6. Relationships and Cross-References

Sections [6.1](#61-thing-description-to-thing-model) through
[6.4](#64-thing-description-to-schema-registry) describe how existing WoT and
xRegistry mechanisms compose. They place no requirements on a conformant
registry.
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
that already carried an `href` in the WoT identifier space keeps it, and the
link is recorded in `derivedfrom` instead.

The `href` in such a link is an absolute URI. A registry-relative path would
not survive a copy of the document to another registry, which is the outcome
[Section 5.2](#52-preserving-customer-documents) exists to prevent.

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

A TD-to-TD reference selects a Version of the target `thingdescription`
Resource using its `wotid` and SemVer `versionid`, derived from the target
`version.instance` as specified in [Section 1.3](#13-versioning). For
`td:extends`, `td:subthing` and `td:ref`, `td:minVersion` is an OPTIONAL
floor. A floor limits the target Version to `[floor, (major + 1).0.0)`.
Without a floor, resolution selects the highest eligible Version overall and
can cross major versions. The referencing TD's `version.instance` and
`version.model` do not supply an implicit floor.

This selection rule identifies the TD supplied to the composition operator.
It does not change the operator's inheritance, child-relationship, or
definition-reference semantics. A `td:minVersion` on a TM reference or a
`tm:minVersion` on a TD-to-TD reference is `invalid-floor`. Other TD links are
outside this rule. The W3C versioned-reference proposal defines the proposed
vocabulary and processing model.

### 6.3. Thing Description to Endpoint Registry

A WoT-TD 1.1 `forms` entry binds an interaction affordance to a network
endpoint.

When a Thing Description shares an endpoint independently managed by an
xRegistry [Endpoint Registry][xRegistry Endpoint], implementations typically
link the two descriptions through `forms[].href`. Its value is a URL that
resolves to one of the protocol bindings declared by the corresponding
`endpoint` Resource, so that the two descriptions of the same endpoint do
not drift.

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
`"rel": "describedby"` (in TDs). The `href` resolves to the `schema`
Resource Version's document-view URL: the `self` URL with the `$details`
suffix removed.

### 6.5. Affordance Grouping

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
mechanism to be standardized, a WoT Registry would store a TD that uses it
exactly as it stores any other TD, since the grouping is a member of the
document rather than of the registry model. Support is OPTIONAL. A registry
that does not understand the mechanism MUST still store and serve the document
unchanged, per
[Section 5.2](#52-preserving-customer-documents).

Documents authored outside the Registry routinely contain no grouping
construct. They MUST remain fully supported.

## 7. Security

Like the [xRegistry Core][xRegistry Core] specification, this specification
does not explicitly address authentication or authorization levels of users,
nor how to securely protect the APIs.

Implementations are expected to use authentication and authorization
appropriate to the application domain and deployment environment. Those
mechanisms MAY include OAuth 2.0, OpenID Connect, API keys or other options
appropriate to the use case.

For authorization, `thingdescriptiongroup` and `thingmodelgroup` provide
natural boundaries. Users can receive access to specific Groups and the
Things or Thing Models they contain. Access can also be restricted to
specific Versions of `thingdescription` and `thingmodel` Resources. This
supports fine-grained access control.

Operators of a WoT Registry SHOULD be aware that Thing Descriptions can
expose detailed information about deployed devices, including network
locations, operational endpoints, and security schemes. The
[WoT Security and Privacy Considerations][WoT-Security] document gives
additional guidance.

The document-preservation and selection rules introduce the following risks:

- **Resolution is composition.** A Thing Model composes other Thing Models
  through `tm:extends` and `tm:ref`, and a Thing Description names network
  endpoints through `links[].href` and `forms[].href`. These are authored
  strings taken verbatim from a document the registry did not write
  ([Section 5.2](#52-preserving-customer-documents)), and resolving one is a
  fetch performed with the resolver's network position and credentials, not
  the author's.

  A Consumer or Registry that resolves them SHOULD confine resolution to the
  Registry and its declared federation links. Where a deployment has to
  dereference an authored URL it SHOULD:

  - Restrict the scheme to `https`,
  - Reject targets that resolve to loopback, link-local or other internal
    address ranges,
  - Decline to follow cross-origin redirects, and
  - Bound both the depth and the total size of the composition closure.

  The same applies to the `thingdescriptionurl` and `thingmodelurl` attributes,
  whose bytes come from a location the registry does not control and for
  which this specification defines no integrity check.

- **Provenance metadata is self-asserted.** `license`, `publisher`,
  `standardsbody`, `canonicalurl` and `maturity` are written by whoever
  creates the Resource and are verified by nothing in this specification
  ([Section 4.6](#46-provenance-and-selection-metadata)).

  The same `wotid` MAY appear in more than one Group
  ([Section 5.3](#53-lookup)). A writer with access to any Group within a
  Registry-wide query's scope can therefore publish a document carrying another
  party's `wotid` and claims of high `maturity`/`standardsbody` status. A
  Consumer selecting on those attributes alone would compose the attacker's
  Thing Model and bind its affordances to that model's endpoints.

  Selection MUST therefore be scoped to writers the Consumer already trusts.

- **Stored documents are served from the registry's origin.** A document is
  stored byte-for-byte ([Section 5.2](#52-preserving-customer-documents)) and
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
[xRegistry shortself]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#shortself-attribute
[xRegistry compatibility]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#compatibility-attribute
[xRegistry ancestorid]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#ancestorid-attribute
[xRegistry deprecated]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#deprecated
[xRegistry matchversions]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/model.html#attributesstringmatchversions
[xRegistry version-ids]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#version-ids
[xRegistry hasdocument]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#hasdocument
[xRegistry xref]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#xref-attribute
