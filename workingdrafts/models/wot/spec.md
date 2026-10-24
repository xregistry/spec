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

This specification does not require a registry to resolve or validate these
cross-references: an implementation MAY check that a referent exists, but a
document whose referents are absent is still stored and served. That is a
statement about what the *registry* enforces, not about whether the
references matter — a Consumer composing a TD from its Thing Models, or
binding an affordance to an endpoint, depends on them.

### 1.3. Versioning

Each Version of a `thingdescription` or `thingmodel` Resource holds a complete
WoT document, stored without rewriting its bytes. A Resource's `wotid` and
registry Resource id are stable across compatible revisions; `wotid` is
declared with [`matchversions`][xRegistry matchversions]. A registry MUST
reject a Version that supplies a different `wotid`. A Thing Model's major
version MUST be part of its `wotid`; a breaking change MUST use a new `wotid`
and a new Resource
([Section 5.1.1](#511-breaking-changes-and-successor-identifiers)).

Thing Models MUST use Core `versionmode: semver` and
`singleversionroot: true`. The registry MUST inspect `version.model` without
modifying the stored document. If it is a SemVer 2.0.0 value without build
metadata, the Version's `versionid` MUST equal it verbatim; the registry MUST
assign it when omitted and MUST reject a supplied mismatch as
`version-mismatch`. SemVer build metadata (`+build`) MUST be rejected as
`invalid-version`, since `+` is not in Core's `versionid` grammar. An authored
SemVer value that exceeds Core's 128-character id limit MUST also be rejected
as `invalid-version`.

If `version.model` is absent or is not SemVer, the registry MUST assign
`0.0.0-N`, where N is the lowest positive integer whose complete id is not
already used in the Resource. A client-supplied `versionid`, if present, MUST
equal that assignment or the registry MUST reject it as `version-mismatch`. A
supplied id that violates Core's id grammar MUST be rejected as
`invalid-version` before this comparison. The original absent or non-SemVer
`version.model` MUST NOT be rewritten. Assignment and creation MUST be atomic
with respect to concurrent writes, so two writes cannot claim the same
generated id.

Each Thing Model Version MUST have the server-set, read-only `versionorigin`
attribute: `authored` when its id comes from a SemVer `version.model`, and
`generated` otherwise. Client-supplied `versionorigin` MUST be ignored, under
Core's rules for read-only attributes. Generated ids are prereleases. They
MUST NOT be used as minimum-version floors; the `0.0.0-N` form is reserved
from use as a floor, even when the target Version is not present in the
registry.

Thing Descriptions MUST use `versionmode: manual`. Their `versionid` MAY be
any value permitted by Core; it need not equal `version.instance` or
`version.model`. A TD's `version.model` describes its model dependency, not
its instance revision.

For Thing Models, the Resource-level `compatibility` attribute in `meta` MUST
default to `backward`. A backward-compatible TM revision MUST NOT remove or
narrow an affordance, a data schema or an `@type`, and MUST NOT introduce a
new mandatory member. Narrowing includes reducing the accepted values or
operations of an existing member. These constraints apply to every earlier
Version of the same Resource. A registry MAY validate this domain-specific
compatibility rule; Core's validation capability and strict-validation rules
still apply. A lack of a domain validator does not permit a Producer to
publish an incompatible revision under the same `wotid`.

Core's SemVer lineage determines the default when `defaultversionsticky` is
false: a late `1.0.1` after `1.1.0` MUST NOT replace `1.1.0` as the default. A
sticky default MUST be honoured. Reference resolution additionally applies
floors and prerelease eligibility as specified in
[Section 5.4](#54-versioned-reference-resolution); an ordinary unversioned
Resource retrieval still serves Core's default.

For migration, an operator SHOULD inventory every Version and root of a legacy
Resource before enabling this model. Compatible roots SHOULD be imported into
one SemVer-ordered lineage with ids assigned by the rules above; incompatible
roots MUST be placed in distinct Resources with distinct major-version
`wotid`s. Where changing an old immutable id or authored document would be
necessary, the operator SHOULD preserve the legacy Resource outside the
conforming collection and import a copy under a new registry Resource id. The
operator MUST preserve authored bytes, record the old-to-new registry paths
for callers holding pins, and establish a valid default before enabling
`singleversionroot`. An operator MUST NOT claim that an unresolved
multiple-root Resource conforms to this model.

The [versioning design note](versioning-design.md) explains the design
informatively. The `tm:minVersion` member is defined by a proposed extension
to the W3C WoT Thing Description; it is informative context, not a claim that
this member is part of the published WoT 1.1 Recommendation.

### 1.4. Document Store

The WoT Registry is a document store: the `thingdescriptions` and
`thingmodels` Resources rely on the xRegistry Core default of
[`hasdocument`][xRegistry hasdocument] `true`, which is why
[model.json](model.json) does not declare it.

Such a Resource is exposed through two views:

- The **document view** serves the stored JSON-LD TD or TM document itself,
  using its stored media type — `application/td+json` for TDs and
  `application/tm+json` for TMs, per
  [WoT-TD 1.1 §12.1 and §12.2][WoT-TD-1.1].
- The **metadata view** serves the entity's xRegistry attributes. The
  applicable protocol binding defines how the two views are selected; the
  xRegistry HTTP Binding uses the `$details` URL suffix to select the
  metadata view.

Because these Resources have a document, an entity's
[`self`][xRegistry self] URL is its **metadata-view** URL — in the HTTP
binding, the `$details`-suffixed one. The URL that serves the document is that
same URL *without* the `$details` suffix, which is also what
[`shortself`][xRegistry shortself] is an alternative for where a deployment
enables that capability.

This means an xRegistry-unaware WoT consumer MAY be handed a Version's `self`
URL with the `$details` suffix removed — or its `shortself` URL — and treat it
as a regular WoT TD or TM URL. Handing that consumer the `self` URL unchanged
would return xRegistry metadata rather than the document, so the two are not
interchangeable.

Addressing a `thingdescription` or `thingmodel` Resource without naming a
Version serves that Resource's [default Version][xRegistry version-ids];
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

We use the term **Thing Description** (or `thingdescription` Resource) in this specification as a
logical grouping of **Thing Description Versions**. A **Thing Description Version** is a concrete
WoT-TD 1.1 JSON-LD document. The **Thing Description** Resource names one or
more concrete Thing Description documents that represent iterations of the
same logical Thing instance. It is more than a container for them: addressing
the Resource without naming a Version addresses its
[default Version][xRegistry version-ids], so the Resource also acts as a
stable alias for whichever Version is current. Per the definition of the
[`compatibility`][xRegistry compatibility] attribute, all Versions of a single
**Thing Description** MUST adhere to the rules defined by the `compatibility` attribute.
A breaking change that violates that policy MUST result in a new **Thing
Description** Resource being created; see [Section 1.3](#13-versioning).

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
*within a registry*. The two MAY hold the same string where the authored
identifier happens to satisfy the xRegistry id grammar, but most do not — a
URL such as `https://fabrikam.example/things/lamp-42` is not a legal
xRegistry id — so this specification keeps them as two attributes rather than
reusing the Resource id for both.
[Section 5.1](#51-wot-identifiers-and-registry-ids) defines how the two
relate.

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
the [model.json](model.json) file. Its `modelversion` — `0.1` while this
remains a working draft — versions *this* model, and moves independently of
the xRegistry Core specification version that appears in a Registry's
`specversion`.

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

The WoT Registry is a metadata store for organizing Thing Descriptions, Thing
Models, and their Versions; it is a document store.

Implementations of this specification MAY include additional extension
attributes, including the `*` attribute of type `any`.

Since the WoT Registry is an application of the
[xRegistry specification][xRegistry Core], all attributes for Groups,
Resources, and Resource Version objects are inherited from there.

### 4.1. Thing Description Groups

The Group Type (`<GROUP>`) name for Thing Descriptions is `thingdescriptiongroup` (singular).
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

The Resource Type (`<RESOURCE>`) inside of Thing Description Groups is named `thingdescription`. The
plural, used as the collection name, is `thingdescriptions`. Any single `thingdescription` is a
container for one or more `versions`, each of which holds the concrete
WoT-TD 1.1 JSON-LD document.

The `format` attribute of a `thingdescription` Resource Version MUST be
`"JSON-LD/1.1"`. [model.json](model.json) declares the `format` enumeration
as `strict`, so a registry rejects any other value rather than merely
discouraging it.

The `contenttype` of a `thingdescription` document MUST be
`application/td+json` per [WoT-TD 1.1 §12.1][WoT-TD-1.1], or another media
type the deployment has explicitly registered for WoT documents. `contenttype`
is client-supplied, and the document view serves the stored bytes under it
([Section 1.4](#14-document-store)), so a registry MUST NOT serve a stored
document under a client-supplied media type that causes it to be interpreted
as active content — for example `text/html`, `image/svg+xml` or
`application/xhtml+xml`. A registry MUST either reject such a write or serve
the document under the media type this section requires. Because a Version's
document-view URL is intended to be dereferenced directly by WoT tooling, a
registry SHOULD additionally return `X-Content-Type-Options: nosniff` for
documents it did not itself author, or serve them from an origin separate
from any registry user interface. See [Section 7](#7-security).

The `wotid` attribute is REQUIRED and holds the document's authored WoT
identifier, which is distinct from the `thingdescriptionid`. See
[Section 5.1](#51-wot-identifiers-and-registry-ids). The OPTIONAL
`derivedfrom` attribute lists the `wotid`s of the Thing Models this Thing
Description extends or composes; it is a producer-supplied index rather than
an authority over the document's own references, as
[Section 5.2](#52-preserving-customer-documents) describes.

All Versions of a single Thing Description Resource MUST adhere to the semantic rules of
the Thing Description's [`compatibility`][xRegistry compatibility] attribute, if specified.

Implementations of this specification SHOULD use the xRegistry default
algorithm for generating new `versionid` values. Which Version is the default
Version — the one served when no Version is named — MUST be determined by the
xRegistry Core rules, including the Resource's `defaultversionsticky`
setting, which a deployment MAY use to pin the default to a Version other
than the newest. This specification does not redefine either. See
[Version IDs][xRegistry version-ids] for more information.

### 4.3. Thing Model Groups

The Group Type name for Thing Models is `thingmodelgroup` (singular), with
collection name `thingmodelgroups`. The Thing Model Group does not have any
specific extension attributes.

A Thing Model Group is a collection of Thing Models related in some
application-defined way (typically by vendor or product family).

Every Thing Model (i.e. the `thingmodel` Resource) MUST reside inside a Thing
Model Group.

### 4.4. Thing Model Resources

The Resource Type inside of Thing Model Groups is named `thingmodel`, with
collection name `thingmodels`. Any single `thingmodel` is a container for one
or more `versions`, each of which holds the concrete WoT-TM 1.1 JSON-LD
document.

The `format` attribute of a `thingmodel` Resource Version MUST be
`"JSON-LD/1.1"`, enforced by the same `strict` enumeration used for
`thingdescription`. The `contenttype` MUST be `application/tm+json` per
[WoT-TM 1.1 §12.2][WoT-TM-1.1], or another media type the deployment has
explicitly registered for WoT documents, and the same constraint on serving
stored bytes as active content applies as in
[Section 4.2](#42-thing-description-resources).

The `compatibility`, `versionid`, `versionorigin` and
[`ancestorid`][xRegistry ancestorid] rules for Thing Models are defined in
[Section 1.3](#13-versioning). The Version-level `versionorigin` is a REQUIRED
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

A Consumer choosing between candidate Thing Models SHOULD prefer, in order:

1. `maturity` of `Standard` accompanied by a `standardsbody`.
2. `maturity` of `Vendor`, **or** `maturity` of `Standard` with no
   `standardsbody` — the two rank equally, because a document is not an
   interoperable standard merely because its writer marked it `Standard`.
3. `maturity` of `Community`.
4. `maturity` of `Experimental`.
5. No `maturity` at all.

Where the choice remains open the Consumer SHOULD prefer the document whose
`canonicalurl` it already trusts. [model.json](model.json) declares the
`maturity` enumeration as `strict`, so a registry rejects a value outside
this set; a Consumer that nonetheless encounters one — from a federated
registry, for example — MUST NOT rank it above `Experimental`, because this
specification defines no precedence for it.

These attributes are **advisory and unverified**. They describe where a
document claims to have come from and how established its writer says it is.
They are asserted by whoever writes the Resource, and this specification
defines no mechanism by which a registry validates that a `publisher` or
`standardsbody` claim is genuine; a registry MUST NOT be assumed to have done
so. A Consumer MUST NOT treat them as authenticated provenance, and the
preference order above is a tie-break among documents the Consumer has
*already* decided to trust — by Group, by writer identity, or by an
out-of-band signature. It MUST NOT be used to establish trust in a document
from an untrusted writer. [Section 5.3](#53-lookup) notes that one `wotid`
MAY legitimately match several Resources, so this is a real choice among
candidates written by different parties; see also
[Section 7](#7-security).

These attributes are also not part of a document's semantic identity. A
registry MUST NOT treat two documents as the same document because their
provenance attributes agree, nor as different documents because they differ:
identity is `wotid` alone
([Section 5.1](#51-wot-identifiers-and-registry-ids)).

They are Version attributes, carried on each Version alongside the document
they describe, as `format` and `wotid` are. This specification defines no
special update semantics for them; they are written and updated exactly as any
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

The two express the same idea but are **not the same grammar**:
`https://fabrikam.example/things/lamp-42` is not a valid entity id, so it is
also not a valid `xid` component, and an `xid` is not what a Thing author
writes. Where an authored identifier does satisfy the id grammar a client MAY
use it as the Resource id, but a registry cannot rely on that.

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
a Group id: it either names the id in the request path, or supplies it in the
request body, or omits it and lets the registry assign one under the xRegistry
Core rules. Nothing in the document dictates the choice, and nothing later
depends on it, because `wotid` is a first-party attribute: a Consumer holding
a WoT identifier finds the Resource by querying on it
([Section 5.3](#53-lookup)) rather than by reconstructing a path. A deployment
MAY derive its Resource ids from `wotid` values by a convention of its own —
the [OpenUSD Artifact Registry][OpenUSD Draft] working draft defines one such
construction — but no convention is mandated by this specification, and a
Consumer MUST NOT assume that an id it did not assign was produced by one.

A `wotid` MUST NOT encode a compatible revision of the document it names. A
Thing Model's major version MUST be included in that stable identity, for
example `urn:fabrikam:lamp:v1` or `https://fabrikam.example/tm/lamp/v1`. Minor
and patch revisions are carried by `versionid` and `version.model`, not
appended to the identifier. No particular spelling of the major-version token
is mandated.

When a document is revised compatibly, its `wotid` and `thingdescriptionid` or
`thingmodelid` MUST remain unchanged, and a new Version is created under the
same Resource. A breaking revision instead names a distinct logical Thing as
specified in [Section 5.1.1](#511-breaking-changes-and-successor-identifiers).

A `wotid` is REQUIRED, and the rule for populating it depends on the document:

- Where the document carries an `id` member, `wotid` MUST equal it verbatim.
  A registry that parses the stored document MUST reject a write whose
  `wotid` differs from that `id`, rather than storing two identities for one
  document. A registry that does not parse the document cannot detect the
  disagreement; neither MUST resolve one by rewriting either value, because
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
distinct Resource. The predecessor's `wotid` MUST NOT be modified. A breaking
TD change that violates its declared compatibility policy MUST likewise use a
distinct `wotid` and Resource.

The predecessor Resource MUST be marked with Core's
[`deprecated`][xRegistry deprecated] attribute, whose `alternative` MUST be
the successor Resource's URL. Its Versions MUST remain retrievable;
deprecation alone MUST NOT cause the resolver to redirect a reference to the
successor. A Consumer MAY inspect the successor and explicitly choose to adopt
its different identity.

| | Predecessor | Successor |
|---|---|---|
| `wotid` | `urn:fabrikam:lamp:v1` | `urn:fabrikam:lamp:v2` |
| `thingmodelid` | `urn.fabrikam.lamp.v1` | `urn.fabrikam.lamp.v2` |
| Versions | `1.0.0`, `1.1.0`, `1.1.1` | `2.0.0` |
| `deprecated` | `alternative` names the successor URL | absent |

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
- A retrieval of a stored Version through the document view MUST return the
  exact bytes supplied, as the xRegistry Core document view already requires.
  Re-serializing the document — reordering members, re-indenting, or
  normalizing its JSON-LD — is not permitted.

Rewriting is incompatible with these documents for three reasons. A TM
published by a standards body is referenced by `id` from artifacts outside the
registry, and rewriting the `id` would break those references while leaving
the registry's own copy claiming to be the standard document. A TD's
`tm:extends` target resolves in the WoT identifier space, so a rewritten
target no longer matches what any other WoT tool would look for. And a
document copied between two registries would acquire two different identities
for the same bytes, so neither registry could tell the copies apart from
genuinely distinct documents.

The registry's own identity for a document — its `thingdescriptionid` or
`thingmodelid`, and the `xid` those form — therefore lives *outside* the
document, and the identifiers the document itself authored are carried
alongside it, unchanged, in the `wotid` and `derivedfrom` attributes. This
keeps the authored identifier space and the registry identifier space
separate and allows a document to round-trip unchanged.

Where a registry wants the TD-to-TM link to be traversable without parsing the
document, it records the referenced Thing Models' *authored* identifiers in
the `derivedfrom` attribute. `derivedfrom` holds `wotid` values, not `xid`s,
precisely so that it can be compared directly against what the document
authored.

`derivedfrom` is a producer-supplied *index* of the document's references, not
an authority over them. A registry MAY verify that it matches the
`tm:extends`, `tm:submodel`, `tm:ref` and `links[].rel="type"` targets in the
stored document, and SHOULD reject a write where the two disagree; where a
registry does not verify, the document is authoritative. A Consumer making a
trust, allow-list or compliance decision about a document's lineage MUST
derive that lineage from the document itself and MUST NOT rely on
`derivedfrom` alone.

### 5.3. Lookup

A Consumer holding a WoT identifier — typically taken from a `tm:extends`
link, a `tm:ref`, another `links[].href`, or a message attribute — resolves it
to a stored document in one of two ways.

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

An implementation SHOULD serve this query in time that does not grow with the
size of the collection — in practice by indexing `wotid` on both
`thingdescriptions` and `thingmodels`. Resolution is on the critical path of
composing a TD from its Thing Models, so a linear scan per reference does not
scale.

A `wotid` SHOULD be unique within a Group, so that a Group-scoped query for
one identifies a single Resource. Across Groups a `wotid` MAY repeat — the
same vendor TM legitimately appears in two tenants' Groups — so a
registry-wide query MAY match more than one Resource, and a caller that needs
exactly one narrows the query by naming the Group. A registry-wide match MUST
return every matching Resource rather than an arbitrary one of them, and
[Section 4.6](#46-provenance-and-selection-metadata) governs how a Consumer
chooses among them.

Version selection is a second, separate step, and is never encoded in the
*identifier*. It is, of course, encoded in the URL — that is what the
`versions` collection is for:

| Intent | Request |
|---|---|
| Latest Version | the Resource's URL, which serves its default Version |
| A specific Version | `<resource-url>/versions/<versionid>` |
| Enumerate Versions | `<resource-url>/versions` |

`<resource-url>` above is the Resource's [`self`][xRegistry self] URL for the
metadata view, or that URL with the `$details` suffix removed for the
document view; see [Section 1.4](#14-document-store).

The Resource URL serves the Core default Version, including when
`defaultversionsticky` is true. A registry MUST serve that default when no
Version is named. This retrieval is distinct from resolving a reference: a
resolver MUST use [Section 5.4](#54-versioned-reference-resolution), not
lexical sorting, publication time or an assumption that the default always
satisfies the reference.

What a caller SHOULD NOT do is fold the two into one opaque string. A caller
that carries an identifier and a version through a transport — for example in
message headers — SHOULD carry them as two separate values, such as a
`wotid` header and a `versionid` header, rather than a single compound token
like `urn:fabrikam:lamp@3` that every recipient has to take apart. The
identifier stays a WoT identifier, and the version stays a `versionid` the
recipient can put straight into a URL.

### 5.4. Versioned Reference Resolution

#### 5.4.1. Floors and Pins

A reference MAY carry a minimum SemVer, called its floor, but MUST NOT carry a
version range. For `tm:extends` and `tm:submodel`, `tm:minVersion` is a member
of the link object. For `tm:ref`, it is a sibling of `tm:ref` in the referring
object. A floor MUST be a SemVer 2.0.0 string without build metadata, within
Core's id length limit, and MUST NOT have the generated `0.0.0-N` form. An
invalid floor MUST produce `invalid-version`.

For a TD with exactly one `rel: "type"` link, its `version.model`, when
present, is the implicit floor of that link. If the link also has an explicit
`tm:minVersion`, the greater value by SemVer precedence is the effective
floor; an explicit lower value MUST NOT weaken the implicit floor. If only one
floor is present, that floor applies. For a TD with several type links and
`version.model`, every type link MUST carry its own `tm:minVersion`; otherwise
resolution MUST fail as `ambiguous-floor`, including when resolving a
different, fully specified link of that TD. When every link has an explicit
floor, each link MUST use the greater of its own `tm:minVersion` and
`version.model` by SemVer precedence. For several type links without
`version.model`, there is no implicit floor: each link uses its own
`tm:minVersion` if present, and otherwise has no floor. An omitted floor in
that case MUST NOT produce `ambiguous-floor`. A non-SemVer implicit floor MUST
produce `invalid-version`, not silently disappear.

A resolver MUST return `(wotid, versionid, contentdigest, origin)`, where
`origin` identifies the registry from which the stored bytes were obtained and
`contentdigest` is the digest of those bytes. A Consumer MAY retain this tuple
outside the document and pass either a digest pin or a `versionid` pin on a
subsequent resolution. A request MUST contain at most one kind of pin.
Documents MUST NOT carry registry version pins or digest pins; a floor is a
compatibility requirement, not a pin. Authored references and document bytes
MUST remain portable between registries.

#### 5.4.2. Resolver Algorithm

The caller first selects a registry and Group scope that identifies one
Resource by `wotid`, following [Section 5.3](#53-lookup). For `tm:ref`, the
lookup target is the document identifier resolved from the reference URI,
excluding any fragment; the fragment is applied to the selected document after
version selection. Resource disambiguation across Groups precedes this
algorithm.

The resolver MUST apply the following steps in order:

1. Find the Resource whose `wotid` equals the reference target. If none
   exists, fail as `not-found`. A deprecated Resource is eligible and MUST NOT
   be replaced automatically by its `deprecated.alternative`.
2. If a digest pin is supplied, return a Version of that Resource whose
   `contentdigest` equals the pin, or fail as `pin-mismatch`. If several
   Versions have identical bytes and the same digest, return the one with
   highest SemVer precedence. If a `versionid` pin is supplied, return that
   exact Version or fail as `not-found`. Pins are caller overrides: they
   bypass floor derivation, prerelease filtering and sticky-default selection.
   They do not authorize substituting bytes or following a successor.
3. Derive and validate the floor as specified in Section 5.4.1. Report
   `ambiguous-floor` before validating individual floors when the
   multiple-type-link rule is violated.
4. If `defaultversionsticky` is true, select the Version named by
   `defaultversionid` as-is. Do not substitute another Version or apply
   prerelease filtering to an operator's sticky choice. If the named Version
   is unavailable, fail as `not-found`.
5. Otherwise, exclude all prereleases, including generated ids, unless the
   floor is a prerelease or the caller explicitly opts in with
   `allowPrerelease`. Select the highest remaining Version by SemVer 2.0.0
   precedence, not lexicographic order. If none is eligible, fail as
   `unsatisfied`. Even a Resource containing only generated Versions requires
   an opt-in or an explicit pin or sticky default.
6. If a floor exists and the selected Version is below it, fail as
   `unsatisfied`. Never downgrade, bypass a sticky default or retry with a
   lower Version. Otherwise return the selected
   `(wotid, versionid, contentdigest, origin)`.

For an unpinned reference, only SemVer Versions from a conforming Thing Model
Resource are inputs to this algorithm. Thing Description instance revisions
are not ordered by this resolver.

#### 5.4.3. Errors and Test Vectors

| Error | Meaning |
|---|---|
| `not-found` | Resource, pinned Version or sticky default is absent. |
| `pin-mismatch` | The target Resource has no Version with the caller's digest. |
| `unsatisfied` | No eligible Version exists, or the selected Version is below the floor. |
| `ambiguous-floor` | A TD has `version.model`, several type links and at least one link without its own floor. |
| `version-mismatch` | A supplied publication `versionid` disagrees with the authored or generated assignment. |
| `invalid-version` | A floor or publication version violates the version syntax or generated-floor restriction. |

These names identify domain outcomes, not replacements for Core's protocol
error envelopes. The
[canonical resolution vectors](tests/resolution/README.md) define portable
resolver inputs and expected outcomes, including write-side version
assignment.

## 6. Relationships and Cross-References

Sections [6.1](#61-thing-description-to-thing-model) through
[6.3](#63-thing-description-to-schema-registry) describe how existing WoT and
xRegistry mechanisms compose. They place no requirements on a conformant
registry and use no RFC 2119 keywords;
[Section 6.4](#64-affordance-grouping) is normative.

### 6.1. Thing Description to Thing Model

A WoT-TD 1.1 document can declare that it conforms to one or more Thing
Models using the `links` member ([WoT-TD 1.1 §6.3.8][WoT-TD-1.1]) with
`"rel": "type"`, the convention specified in
[WoT-TD 1.1 §9.4, Derivation of Thing Description Instances][WoT-TD-1.1].
When the referenced Thing Model resides in the same WoT Registry, the `href`
can point at that Thing Model's document-view URL — its
[`self`][xRegistry self] URL with the `$details` suffix removed, or
equivalently its [`shortself`][xRegistry shortself] URL — since a `link`
carrying `"type": "application/tm+json"` is expected to dereference to the TM
document itself and not to xRegistry metadata
([Section 1.4](#14-document-store)). Because
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

### 6.2. Thing Description to Endpoint Registry

A WoT-TD 1.1 `forms` entry binds an interaction affordance to a network
endpoint. When a Thing Description shares an endpoint that is independently
managed by an xRegistry [Endpoint Registry][xRegistry Endpoint],
implementations typically make the `forms[].href` value a URL that resolves to
one of the protocol bindings declared by the corresponding `endpoint`
Resource, so that the two descriptions of the same endpoint do not drift.

This specification does not require an `endpoint` Resource to exist for every
`forms` entry, nor does it require any specific naming or correlation
mechanism. Implementations are free to define their own conventions to
correlate the two.

### 6.3. Thing Description to Schema Registry

A WoT-TD 1.1 property, action, or event affordance can reference an external
data schema rather than declaring its data schema inline. When the referenced
schema is managed by an xRegistry [Schema Registry][xRegistry Schema],
implementations typically express the reference using the WoT
[`tm:ref`][WoT-TM-1.1] mechanism (in TMs) or a `links` entry with
`"rel": "describedby"` (in TDs), with the `href` resolving to the `schema`
Resource Version's document-view URL — the `self` URL with the `$details`
suffix removed.

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

Three further considerations follow from this specification's own rules.

- **Resolution is composition.** A Thing Model composes other Thing Models
  through `tm:extends` and `tm:ref`, and a Thing Description names network
  endpoints through `links[].href` and `forms[].href`. These are authored
  strings taken verbatim from a document the registry did not write
  ([Section 5.2](#52-preserving-customer-documents)), and resolving one is a
  fetch performed with the resolver's network position and credentials, not
  the author's. A Consumer or registry that resolves them SHOULD confine
  resolution to the registry and its declared federation links. Where a
  deployment has to dereference an authored URL it SHOULD restrict the scheme
  to `https`, reject targets that resolve to loopback, link-local or other
  internal address ranges, decline to follow cross-origin redirects, and
  bound both the depth and the total size of the composition closure. The
  same applies to the `thingdescriptionurl` and `thingmodelurl` attributes,
  whose bytes come from a location the registry does not control and for
  which this specification defines no integrity check.

- **Provenance metadata is self-asserted.** `license`, `publisher`,
  `standardsbody`, `canonicalurl` and `maturity` are written by whoever
  creates the Resource and are verified by nothing in this specification
  ([Section 4.6](#46-provenance-and-selection-metadata)). Because the same
  `wotid` MAY appear in more than one Group
  ([Section 5.3](#53-lookup)), a writer with access to any Group in a
  registry-wide query's scope can publish a document carrying another
  party's `wotid` and a flattering `maturity`/`standardsbody` pair. A
  Consumer that selects on those attributes alone would then compose an
  attacker's Thing Model and bind its affordances to the endpoints that
  model declares. Selection MUST therefore be scoped to writers the Consumer
  already trusts.

- **Stored documents are served from the registry's origin.** A document is
  stored byte-for-byte ([Section 5.2](#52-preserving-customer-documents)) and
  served under a client-supplied `contenttype`, so
  [Section 4.2](#42-thing-description-resources) constrains which media types
  a registry will serve it under. Format validation does not help here: a
  document can be valid JSON-LD 1.1 and still execute as script if served as
  `text/html`.

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
[xRegistry shortself]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#shortself-attribute
[xRegistry compatibility]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#compatibility-attribute
[xRegistry ancestorid]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#ancestorid-attribute
[xRegistry deprecated]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#deprecated
[xRegistry matchversions]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/model.html#attributesstringmatchversions
[xRegistry version-ids]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#version-ids
[xRegistry hasdocument]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#hasdocument
[xRegistry xref]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#xref-attribute
