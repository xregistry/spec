# Descriptor Registry Service - Version 1.0-rc4

<!-- words: descriptorgroup descriptorgroups descriptorgroupid -->
<!-- words: descriptorgroupsurl descriptorgroupscount descriptorid -->
<!-- words: descriptorsurl descriptorscount entityid entitytype -->
<!-- words: bundleurl baseurl describedby matchversions readonly -->
<!-- words: thingdescription thingdescriptiongroups thingdescriptions -->
<!-- words: usdasset usdassetgroups usdassets opcuawriter -->
<!-- words: opcuapublisherid opcuadatasetwriterid opcuadatasetwritername -->
<!-- words: opcuadatasetname UInt16 PumpProcessData affordanceselector processData -->
<!-- words: acme servicekind actorinfo -->
<!-- words: descriptorurl ETags OpenUSD prebuilt reserializing -->

## Abstract

This specification defines a Descriptor Registry extension to the xRegistry
document format and API [specification][Core]. It exposes portable
Descriptor fields as native Resource Version metadata. The
[CloudEvents Descriptor specification][Descriptor format] defines the
portable response and entry profiles. xRegistry adds Registry identity,
writes, publication, bundle negotiation and Version management.

## Table of Contents

- [Abstract](#abstract)
- [Table of Contents](#table-of-contents)
- [1. Overview](#1-overview)
- [2. Notations and Terminology](#2-notations-and-terminology)
- [3. Descriptor Registry Model](#3-descriptor-registry-model)
- [4. Descriptor Registry](#4-descriptor-registry)
  - [4.1. Descriptor Groups](#41-descriptor-groups)
  - [4.2. Descriptor Resources](#42-descriptor-resources)
  - [4.3. `entries` Attribute](#43-entries-attribute)
  - [4.4. `entityid` and `entitytype` Attributes](#44-entityid-and-entitytype-attributes)
  - [4.5. `bundleurl` Attribute](#45-bundleurl-attribute)
  - [4.6. Core Property Semantics](#46-core-property-semantics)
- [5. Retrieval and Publication](#5-retrieval-and-publication)
  - [5.1. Ordinary Retrieval](#51-ordinary-retrieval)
  - [5.2. Writes and Null Values](#52-writes-and-null-values)
  - [5.3. Publication and Identity Stability](#53-publication-and-identity-stability)
  - [5.4. Publication Within and Across Registries](#54-publication-within-and-across-registries)
  - [5.5. Bundled Representations](#55-bundled-representations)
- [6. Examples](#6-examples)
- [7. Validation and Failure Handling](#7-validation-and-failure-handling)
- [8. Security](#8-security)

## 1. Overview

A Descriptor associates named entries with representations or inline
metadata used to describe an entity or interpret messages. Each entry has
a class, an OPTIONAL retrieval URL and colocated profile fields. Repeated
classes are permitted; the applicable profile defines how an operation
selects entries or reports ambiguity.

The portable representation is defined by CloudEvents and can be served
without xRegistry. This domain maps those fields directly to native Version
metadata. An ordinary GET returns them together with Core bookkeeping;
there is no translation adapter or separate portable view.

An Actor description identifies a participant independently of its
conversation roles. Publisher, Producer and Consumer denote responsibilities
that a participant can combine. A Processing Descriptor supplies shared
interpretation inputs. It does not describe an observed execution: a named
entry or endpoint description establishes neither message delivery nor
successful processing.

CloudEvents owns the common `describedby` contract and failure boundary.
Applicable profiles own entry definitions, `source` and `subject`
interpretation, schema selection and native metadata conveyance. This
domain owns their native storage and Core operation semantics.

## 2. Notations and Terminology

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD",
"SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" are interpreted as
described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

| Term | Meaning |
| --- | --- |
| Descriptor | A metadata-only `descriptor` Resource. Its default Version fields appear at the Resource URL. |
| Entry | A named object in the portable `entries` map. Its class and profile determine its meaning and URL requirements. |
| Publisher | A client that stores and publishes Descriptors and makes their REQUIRED representations available. |
| Consumer | A client that retrieves a Descriptor or uses its entries. |
| Processing Descriptor | A Descriptor selected by a message binding to supply processing inputs. |
| Bundled representation | The portable bundle defined by CloudEvents, with documents embedded under linked entries. |

In pseudo-JSON, `?` denotes an OPTIONAL attribute and `*` permits zero or more
map entries. Ellipses denote omissions. Concrete `json` examples are valid
JSON. Core's extension support, omission, validation and resource limits
apply to metadata writes.

## 3. Descriptor Registry Model

The extension model is [model.json](model.json). Its `modelversion` is `0.1`,
independent of the Registry's Core `specversion`.

```text
Registry
  descriptorgroups/{descriptorgroupid}
    descriptors/{descriptorid}
      meta
      versions/{versionid}
```

The following metadata specimen omits other Core attributes for brevity.
The Resource includes its default Version's portable fields.

```yaml
{
  "specversion": "<STRING>",
  "registryid": "<STRING>",
  "descriptorgroups": {
    "KEY": {
      "descriptorgroupid": "<STRING>",
      "descriptors": {
        "KEY": {
          "descriptorid": "<STRING>",
          "versionid": "<STRING>",
          "entityid": "<URI>", ?
          "entitytype": "<URI>", ?
          "entries": {
            "<STRING>": {
              "class": "<STRING>",
              "url": "<URL>", ?
              # Profile fields omitted
            } *
          },
          "bundleurl": "<URL>", ?
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

`hasdocument` is `false`. Ordinary Resource or Version retrieval returns
metadata without `$details`. The Core document attributes `descriptor`,
`descriptorurl` and `descriptorbase64` are not defined for this Resource.

Generated schemas express the native structure. The portable JSON Schema
and applicable entry profiles supply additional constraints, including
HTTP(S) URL syntax, class semantics and linked versus inline admission.
The Core model alone does not prove those conditions.

## 4. Descriptor Registry

Groups, Resources, Versions and operations inherit their behavior from
[Core][Core]. Implementations MAY define Core-compatible metadata extensions.
Core-only properties are Registry-specific overhead, not portable entry
profile definitions. Consumers MUST NOT silently use such properties to
replace REQUIRED profile inputs.

### 4.1. Descriptor Groups

The Group Type is `descriptorgroup`, with collection name `descriptorgroups`.
Every Descriptor Resource MUST reside in a Descriptor Group.

Group organization is application-defined. Names such as `devices`,
`actors` and `streams` do not establish classifications. Consumers MUST NOT
infer entry semantics, participant identity or permissions from Group or
Resource names.

### 4.2. Descriptor Resources

The Resource Type is `descriptor`, with collection name `descriptors`.
It permits unlimited Versions (`maxversions: 0`) and client-specified
Version IDs (`setversionid: true`).

`descriptorid` and `versionid` are Core IDs and simultaneously identify the
portable response. Core validates their supplied values and determines the
addressed Version. A Resource URL selects its default Version. Consumers
requiring a fixed interpretation SHOULD select a specific Version URL.

### 4.3. `entries` Attribute

- Type: Map of objects
- Description: Named portable Descriptor entries.

- Constraints:
  - REQUIRED. An empty map (`{}`) is valid. Profiles can require particular
    entries for an operation.
  - Names MUST follow Core map-key syntax and be unique within the map.
  - Every entry MUST contain a non-null string `class`.
  - Entry classes, allowed names, profile fields and selection rules follow
    the [portable format and its profiles][Descriptor format]. A Consumer
    MUST NOT guess a selection from map order or Registry paths.
  - A present `url` MUST be a non-null absolute, fragment-free HTTP(S) URL.
    Linked entry profiles require it; inline-only entry profiles forbid it.
    An inline entry omits `url` rather than using `null`.
  - Colocated profile fields MUST satisfy the applicable profile and Core
    attribute semantics. Deployment models SHOULD declare their types.
  - Former top-level `references`, `data` and selector layouts MUST NOT be
    used as aliases for the portable representation.

The native model declares `urlabsolute`, whose generated pattern is broader
than HTTP(S). Implementations MUST also apply the portable HTTP(S) URL
constraint. Independently defined entry fields remain subject to Core's
[extension rules][Core extensions]; this domain invents no additional Core
types or nullable REQUIRED attributes.

### 4.4. `entityid` and `entitytype` Attributes

`entityid` is OPTIONAL and identifies the described entity, independently
of Core `descriptorid`. Its value MUST be a nonempty RFC 3986 URI with a
scheme and no fragment. Comparison MUST be exact, without normalization.
URNs are permitted. The model declares scalar `entityid` with
`matchversions: true`; its presence and value MUST agree across retained
Versions.

`entitytype` is OPTIONAL xRegistry metadata describing the entity's type
under an applicable vocabulary. It requires a non-null `entityid` and a
URI with a scheme. A fragment MAY identify an ontology class. Its comparison
MUST be exact. It is not a portable entry-class selector.

Examples of entity identity include `https://assets.example/devices/pump7`
and `urn:example:asset:pump7`. Type examples include
`https://models.example/ontologies/devices.owl#Device` and
`https://models.example/classes/software-actor`.

Changing or adding an entity association requires a new Descriptor Resource.
The Publisher MUST NOT repurpose a published Resource URL for another
entity, including after deletion. Updating the sole Version or every
retained Version together does not bypass this history rule.

### 4.5. `bundleurl` Attribute

- Type: Absolute URL (`urlabsolute`)
- Description: Direct retrieval URL advertised by a server that supports
  the portable bundled representation.

- Constraints:
  - OPTIONAL and read-only for clients.
  - A present value MUST meet the portable absolute HTTP(S) URL rules and
    retrieve the bundle directly.
  - A server MUST omit it when that retrieval option is unsupported.
  - In a bundled response it identifies that bundled view's own retrieval
    URL, following the portable direct-retrieval contract.
  - Consumers MUST use it unchanged. They MUST NOT derive it by appending
    a suffix or rewriting a Core metadata URL.

Client attempts to set or delete this server-managed field follow Core's
read-only rules. Support is not inferred merely from the model declaring
the attribute.

### 4.6. Core Property Semantics

Core `epoch`, `createdat`, `modifiedat`, `ancestorid`, `self`, `xid`,
default-Version selection and other bookkeeping describe the Registry
entity. They follow Core unchanged and MAY accompany the portable fields.
An ordinary Version response needs no conversion to expose those fields.

Core `matchversions` compares retained Versions; it does not preserve deleted
history or implement publication retention. Epochs and ETags have different
roles: a Registry epoch does not validate remotely referenced content.

## 5. Retrieval and Publication

### 5.1. Ordinary Retrieval

A Consumer requests the selected Descriptor URL unchanged:

```http
GET /descriptorgroups/streams/descriptors/pump7-telemetry/versions/1 HTTP/1.1
Host: registry.example
Accept: application/json
```

The response contains portable fields and Core metadata. The Consumer MUST
check status, media type and shape, then apply the entry profiles needed for
its operation. Entry URLs are used as supplied, subject to retrieval policy.
Core-only fields do not supply missing profile inputs.

### 5.2. Writes and Null Values

Publishers use ordinary Core metadata operations to create or update a
Descriptor. For example, this Version input has no entries:

```http
PUT /descriptorgroups/streams/descriptors/pump7-telemetry/versions/1 HTTP/1.1
Host: registry.example
Content-Type: application/json

{
  "descriptorid": "pump7-telemetry",
  "versionid": "1",
  "entries": {}
}
```

Core validates IDs and types and applies
[HTTP metadata write semantics][HTTP processing]. PUT and POST replace
specified entities; PATCH updates explicitly supplied attributes. Complex
attributes such as `entries` are replaced by their supplied values under
Core's rules, not recursively merged as individual profile-field patches.

Core `null` writes express deletion or reset. Null is not a portable
inline-entry URL. Publishers MUST submit inline entries with `url` omitted.
Deleting a linked entry's REQUIRED URL makes that entry invalid under its
profile and MUST NOT silently convert it to inline metadata.

Publishers MUST NOT write bundled `document` members into stored entries.
Those members are part of an OPTIONAL response representation, not a second
stored copy of each linked resource. This domain defines no portable
bundle-write or entry-level PATCH API.

### 5.3. Publication and Identity Stability

Once published for use, the Publisher MUST preserve a Version's
processing-significant entries and entity identity. Semantic changes
require a new Version. Making a description available to catalog readers
counts as publication for use, independently of whether an event has
carried its URL.

Publisher permissions and retained history enforce the no-reassignment
rule in [Section 4.4](#44-entityid-and-entitytype-attributes), including cases
that retained-Version comparison cannot detect. Core bookkeeping retains
its Core behavior.

Publishers MUST keep REQUIRED linked representations stable and available
for the intended processing and replay period. A Version URL does not
independently guarantee retention, byte integrity or authorization.

A Resource URL can select a new default Version. Consumers SHOULD bound
cache freshness when using that alias. If a selected historical Version is
unavailable, Consumers MUST report the missing input and MUST NOT silently
substitute the current Version.

### 5.4. Publication Within and Across Registries

Core root publication can include Descriptors and linked resources in one
request when the Registry supports the relevant Group types and operation.
The [sample](samples/descriptor.json) contains ordinary Core create/update
inputs. Atomic write processing does not prove that external entry URLs
resolve or satisfy their declared profiles.

Across Registries, the Publisher MUST make REQUIRED representations
available and verify them before publishing the Descriptor for use.
A failed prerequisite stops publication for use. This domain adds no
cross-registry transaction or runtime admission service.

### 5.5. Bundled Representations

The [portable contract][Descriptor format] defines the bundle object,
embedded documents, direct `bundleurl` retrieval and associated validation,
authorization and freshness rules. This section adds OPTIONAL single-hop
negotiation at the unchanged selected xRegistry Descriptor URL.

Generic Core metadata serving does not assemble a bundle. A supporting
deployment needs a resolver or correctly configured prebuilt response.
An ordinary Descriptor remains usable without this capability.

A Consumer requests:

```http
GET /descriptorgroups/streams/descriptors/pump7-telemetry/versions/1 HTTP/1.1
Host: registry.example
Accept: application/vnd.xregistry.descriptor-bundle+json, application/json;q=0.5
```

A supporting server MUST choose the preferred acceptable representation.
For a bundle, it MUST return `200 OK` with
`Content-Type: application/vnd.xregistry.descriptor-bundle+json`, or apply
the conditional response rules for that representation.
Absent `Accept` or `*/*` alone retains ordinary JSON at the ordinary
Descriptor URL. A server implementing negotiation MUST return
`406 Not Acceptable` when it cannot provide an acceptable representation. Consumers
MUST distinguish responses by media type and reject an unexpected format.

Once bundling is selected, assembly failure MUST return an error rather
than silently switch to ordinary JSON. A Consumer MAY retry ordinary JSON
at the same Descriptor URL and retrieve only the representations it needs.
This does not change description selection. Consumers MUST follow supplied
URLs unchanged; they MUST NOT add/remove `$details` or derive a bundle path.
A negotiated bundle MUST satisfy the portable bundle contract. If it
includes `bundleurl`, that field follows the portable direct retrieval
self-link rules. Negotiation does not require a separate direct bundle URL.
Presentation of the bundled view MUST NOT change stored
entries or cause a Core metadata update.

Negotiating servers MUST send `Vary: Accept` on ordinary and bundled
responses, preserving other REQUIRED variation fields. Core conditional
retrieval is applied to the entire selected representation. An epoch or
ETag for only the Descriptor metadata MUST NOT be used to assert that
remotely retrieved bundle content is unchanged.

Bundle completeness, content encoding, redirects, inline admission,
authorization and cache freshness follow the portable specification rather
than another xRegistry entry grammar. Errors SHOULD use the
[Core HTTP error format][HTTP errors]. Prebuilt responses and caches follow
the same portable requirements as resolver-produced responses.

Embedded `content: null` is representation content, not a Core attribute
update. A negotiated read MUST NOT interpret document content as metadata
write instructions. This distinction does not relax the prohibition on
null entry URLs in the portable metadata.

## 6. Examples

This native Version input provides TD entries, a schema, an asset and inline
writer metadata. The CloudEvents publication profile names `pump7` as its TD entry.

```json
{
  "descriptorid": "pump7-telemetry",
  "versionid": "1",
  "entries": {
    "pump7": {
      "class": "thingdescription",
      "url": "https://registry.example/thingdescriptiongroups/factory/thingdescriptions/pump7/versions/3.0.0",
      "affordanceselector": "/properties/processData"
    },
    "gateway1": {
      "class": "thingdescription",
      "url": "https://registry.example/thingdescriptiongroups/factory/thingdescriptions/gateway1/versions/1.0.0"
    },
    "payload": {
      "class": "schema",
      "url": "https://schemas.example/pump-process-data/versions/3"
    },
    "geometry": {
      "class": "usdasset",
      "url": "https://assets.example/usdassetgroups/line1/usdassets/pump7/versions/2"
    },
    "writer": {
      "class": "opcuawriter",
      "opcuapublisherid": "UInt16:12",
      "opcuadatasetwriterid": 17,
      "opcuadatasetwritername": "pump7-process",
      "opcuadatasetname": "PumpProcessData"
    }
  }
}
```

The [sample](samples/descriptor.json) also includes entity and actor
descriptions. Inline entries omit URLs. Writer values and TD/schema/asset
Versions are unchanged; no generic selector or inferred merge is introduced.

## 7. Validation and Failure Handling

Publishers MUST validate native metadata, the portable schema, applicable
profiles and REQUIRED dependencies before publication for use. Core model
validation alone does not establish all profile requirements.

Consumers MUST validate the portable fields and profiles before
interpretation. Repeated classes are permitted. Each profile selects a
named entry or reports ambiguity. Invalid or unavailable REQUIRED inputs
MUST be reported and MUST NOT result in successful interpretation.

The generated schemas do not enforce HTTP(S)-only URLs, all class syntax,
profile relationships or historical retention. A portable field that meets
Core type constraints can still be invalid under its profile. Entry
`url: null` is invalid; native omission is the inline representation.

Core HTTP errors, conditional writes and extension handling retain their
Core definitions. The generic model permits profile fields under `*`;
deployment models SHOULD declare known field types. This domain adds no
Core error codes, attribute types or profile-specific selection rules.

## 8. Security

Deployments authenticate and authorize Registry operations under Core.
Access to a Descriptor does not grant access to linked documents or
permission to invoke an operation. Entity identity and entry class values
do not establish authenticated origin or ownership.

All entry URLs and profile fields are untrusted input. Consumers MUST apply
retrieval and content-validation policy. Bundle servers MUST establish
caller-specific authorization and outbound request policy for local,
cached and remote content before including it.

Access controls MUST account for the entire response, including inline
entries and Core properties. Documents and metadata can disclose participant
identities, network locations and operational information. Observations
and provenance retain their own evidence and disclosure rules; publishing
a description does not establish execution evidence.

[Core]: ../../../core/spec.md
[Core extensions]: ../../../core/spec.md#extensions
[HTTP processing]: ../../../core/http.md#creating-or-updating-entities
[HTTP errors]: ../../../core/http.md#error-processing
[Descriptor format]: https://github.com/cloudevents/spec/pull/1406
