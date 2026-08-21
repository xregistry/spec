# xRegistry Primer

<!-- words: validatecompatibility validateformat -->
<!-- words: strictvalidation matchversions readme upserts -->

<!-- no verify-specs -->

## 1. Abstract

This non-normative document provides an overview of the [xRegistry
specification](https://github.com/xregistry/spec/blob/main/core/spec.md). It is
meant to complement the xRegistry specification to provide additional background
and insight into the history and design decisions made during the development of
the specification. This allows the specification itself to focus on the
normative technical details.

## 2. Table of Contents

- [1. Abstract](#1-abstract)
- [2. Table of Contents](#2-table-of-contents)
- [3. A Quick Introduction to xRegistry](#3-a-quick-introduction-to-xregistry)
  - [3.1. What is xRegistry?](#31-what-is-xregistry)
  - [3.2. Core HTTP Interactions](#32-core-http-interactions)
    - [3.2.1. Reading things](#321-reading-things)
    - [3.2.2. Creating / updating things](#322-creating--updating-things)
    - [3.2.3. Resources: metadata vs. the actual document](#323-resources-metadata-vs-the-actual-document)
    - [3.2.4. Versions](#324-versions)
    - [3.2.5. Deleting](#325-deleting)
    - [3.2.6. Errors](#326-errors)
  - [3.3. Defining a Basic Model](#33-defining-a-basic-model)
    - [3.3.1. Adding your own attributes (extensions)](#331-adding-your-own-attributes-extensions)
- [4. History](#4-history)
- [5. Value proposition](#5-value-proposition)
  - [5.1. Why build something new?](#51-why-build-something-new)
  - [5.2. Discovery](#52-discovery)
  - [5.3. Vendor-agnostic](#53-vendor-agnostic)
  - [5.4. Versioning](#54-versioning)
  - [5.5. Schema validation](#55-schema-validation)
  - [5.6. Payload reduction](#56-payload-reduction)
  - [5.7. Schema-based contract and client generation](#57-schema-based-contract-and-client-generation)
  - [5.8. Basis for further developments](#59-basis-for-further-developments)
- [6. Non-Goals](#7-design-goals)
- [7. Representations](#8-representations)
  - [7.1. File](#81-file)
  - [7.2. Static File Server](#82-static-file-server)
  - [7.3. API Server](#83-api-server)
- [8. Embeddings, References, and Federation](#9-embeddings-references-and-federation)
  - [8.1. Formats and Content/Media-Types](#91-formats-and-contentmedia-types)
  - [8.2. Embeddings and Links](#92-embeddings-and-links)
  - [8.3. Federation](#93-federation)
    - [8.3.1. Composing registries in memory](#931-composing-registries-in-memory)
    - [8.3.2. Shadowing](#932-shadowing)
    - [8.3.3. Identifiers](#933-identifiers)
    - [8.3.4. API Servers and Proxies](#934-api-servers-and-proxies)
- [9. Possible Use Cases](#10-possible-use-cases)
  - [9.1. CloudEvents](#101-cloudevents)
  - [9.2. Business objects](#102-business-objects)
  - [9.3. Metadata files in repositories](#103-metadata-files-in-repositories)
- [10. Design decisions or topics of interest](#11-design-decisions-or-topics-of-interest)
  - [10.1. Resource.ID vs Resource.Version.ID](#111-resourceid-vs-resourceversionid)
  - [10.2. Valid Characters](#112-valid-characters)
  - [10.3. Extensions](#113-extensions)
  - [10.4. Group organization](#114-group-organization)
  - [10.5. Deleting entities](#115-deleting-entities)
  - [10.6. Detection of Referenced Resources](#116-detection-of-referenced-resources)
  - [10.7. Shared/Referenced Resources](#117-sharedreferenced-resources)
  - [10.8. Default Version and Maximum Versions](#118-default-version-and-maximum-versions)
  - [10.9. Why Epoch?](#1110-why-epoch)
  - [10.10. Naming and Case Sensitivity](#1111-naming-and-case-sensitivity)
  - [10.11. Why are Group and Resource type names more restricted?](#1112-why-the-lower-character-limit-on-some-group-and-resource-type-names)
  - [10.12. Choosing unique Group and Resource names](#1114-choosing-unique-group-and-resource-names)
  - [10.13. Are `self` and `shortself` attributes static?](#1115-are-self-and-shortself-attributes-static)
  - [10.14. Why does an unknown query parameter not generate an error?](#1116-why-does-an-unknown-query-parameter-not-generate-an-error)
  - [10.15. Updating attributes with `ifvalues`](#1117-updating-attributes-with-ifvalues)
  - [10.16. Multi-root ancestor hierarchies](#1118-multi-root-ancestor-hierarchies)
  - [10.17. `singleversionroot` Policy Enforcement](#1119-singleversionroot-policy-enforcement)
  - [10.18. Pruning Versions with `singleversionroot` enabled](#1120-pruning-versions-with-singleversionroot-enabled)
  - [10.19. What's the oldest/newest Version of a Resource?](#1121-whats-the-oldestnewest-version-of-a-resource)
  - [10.20. Can `validatecompatibility` and `validateformat` be `true` for file-servers?](#1122-can-validatecompatibility-and-validateformat-be-true-for-file-servers)
  - [10.21. Detecting circular references between Versions](#1123-detecting-circular-references-between-versions)
  - [10.22. Optional required fields in requests](#1124-optional-required-fields-in-requests)
  - [10.23. Deprecation of entities in an xRegistry](#1125-deprecation-of-entities-in-an-xregistry)
- [11. Problematic characters in values](#13-problematic-characters-in-values)
- [12. Why do Resources have 3 levels of data?](#14-why-do-resources-have-3-levels-of-data)
- [13. Why are some (conditional) read-only attributes not ignored?](#15-why-are-some-conditional-read-only-attributes-not-ignored)
- [14. Why isn't `PUT` idempotent?](#16-why-isnt-put-idempotent)
- [15. Validation edge cases](#18-validation-edge-cases)
  - [15.1. Empty format capabilities](#181-empty-format-capabilities)
  - [15.2. Constraints and `matchversions`](#182-constraints-and-matchversions)


## 3. A Quick Introduction to xRegistry

*A quick-start guide for developers who just want to use xRegistry, not read
the whole spec.*

This section is a short, informal introduction to xRegistry. It intentionally
skips edge cases, admin-level configuration and formal `MUST`/`SHOULD`
language. If you need the full details later, see [`spec.md`](./spec.md),
[`http.md`](./http.md) and [`model.md`](./model.md). This guide assumes you
already know how typical REST APIs work (`GET`/`POST`/`PUT`/`PATCH`/`DELETE`,
JSON bodies, HTTP status codes).

### 3.1. What is xRegistry?

xRegistry is a generic way to expose and manage collections of metadata (and
optionally documents) over HTTP, using a consistent, predictable URL/JSON
shape - so tooling written against one xRegistry-based API mostly works
against any other one.

Think of it like a filesystem exposed over HTTP:

- A **Registry** is the root of the whole thing - like the root of a
  filesystem/drive.
- **Groups** are like folders - they organize related things together.
  Example: `endpoints`.
- **Resources** are like files - the actual "things" you care about.
  Example: `messages` (inside an `endpoint`).
- **Versions** are like a file's revision history - a Resource can have one
  or more Versions over time. If you don't care about versioning, just
  ignore Versions and treat the Resource as if it has one version.

The entity hierarchy is:

```
Registry
 └── <GROUPS>/<GID>                      e.g. endpoints/ep1
      └── <RESOURCES>/<RID>              e.g. messages/msg1
           └── versions/<VID>            e.g. versions/1
```

Every Registry has a **model** that declares what Group and Resource types
it supports (their names, and any extra attributes they carry). Clients can
fetch this model at runtime, so tooling can be written generically without
hard-coding knowledge of a specific Registry's shape.

Everything (Registries, Groups, Resources, Versions) shares a small set of
common metadata attributes, the most important being:

| Attribute    | Meaning                                                 |
|--------------|----------------------------------------------------------|
| `<TYPE>id`   | The unique ID of the entity, e.g. `messageid`             |
| `name`       | A human-friendly display name (optional)                  |
| `epoch`      | A number that increments on every change (for concurrency) |
| `self`       | The absolute URL of this entity                            |
| `createdat` / `modifiedat` | Timestamps                                    |

You don't need to memorize these - they just show up automatically in
responses.

### 3.2. Core HTTP Interactions

xRegistry maps directly onto normal REST/HTTP verbs. The URL patterns are:

```
GET/PUT/PATCH        /                                        # the Registry itself
GET                  /model                                   # the model definition
GET/PUT              /modelsource                              # the model, as you defined it

GET/POST/PATCH       /<GROUPS>                                 # e.g. GET /endpoints
GET/PUT/PATCH/DELETE /<GROUPS>/<GID>                            # e.g. .../endpoints/ep1

GET/POST/PATCH       /<GROUPS>/<GID>/<RESOURCES>                # e.g. .../endpoints/ep1/messages
GET/PUT/PATCH/DELETE /<GROUPS>/<GID>/<RESOURCES>/<RID>           # a Resource (its default Version)

GET/PUT/PATCH/DELETE /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>  # a specific Version
```

`<GROUPS>` and `<RESOURCES>` are whatever plural names your Registry's model
defines (e.g. `endpoints`, `messages`) - they're not literal.

#### 3.2.1. Reading things

A plain `GET` on a Registry, Group, metadata-only Resource, or Version returns
its metadata as JSON. Document Resources are the exception described in
section 3.2.3.

```
GET /endpoints/ep1

{
  "endpointid": "ep1",
  "self": "https://example.com/endpoints/ep1",
  "epoch": 3,
  "name": "My Endpoint",
  "messagesurl": "https://example.com/endpoints/ep1/messages",
  "messagescount": 5
}
```

Notice collections aren't inlined by default - you get a `<COLLECTION>url`
and `<COLLECTION>count` instead, and you `GET` that URL to see the actual
list. (You can ask for things to be inlined with `?inline`, but that's an
advanced topic.)

`GET`-ing a collection (e.g. `GET /endpoints`) returns a map of `id -> entity`
for everything in it.

#### 3.2.2. Creating / updating things

- `POST` on a **collection** creates (or upserts) one or more entities in it.
- `PUT`/`PATCH` on a **specific entity** creates it (if it doesn't exist) or
  updates it.
  - `PUT` = full replacement (anything you omit gets reset/cleared).
  - `PATCH` = partial update (only what you include is changed; `null`
    deletes an attribute).

Example - create a Group:

```
PUT /endpoints/ep1
Content-Type: application/json

{ "name": "My Endpoint" }
```

```
HTTP/1.1 201 Created

{
  "endpointid": "ep1",
  "self": "https://example.com/endpoints/ep1",
  "epoch": 1,
  "name": "My Endpoint",
  "createdat": "...",
  "modifiedat": "..."
}
```

#### 3.2.3. Resources: metadata vs. the actual document

Document Resources differ from metadata-only Resources. A Resource such as a
`message` or `schema` can have domain-specific content in addition to its
xRegistry metadata (`epoch`, `name`, etc.).

- `GET /endpoints/ep1/messages/msg1` → returns the Resource's **document**
  (its raw content) directly in the HTTP body.
- `GET /endpoints/ep1/messages/msg1$details` → returns the Resource's
  **metadata** as JSON instead (with the document's metadata such as
  `contenttype`, but not the document body itself).

For `PUT`, `PUT .../msg1` with a raw body sets the document content, while
`PUT .../msg1$details` with a JSON body updates only the metadata.

If a Resource type doesn't have its own separate document (just metadata),
then `$details` isn't needed - plain requests just return the metadata.

#### 3.2.4. Versions

If you don't care about history, ignore `versions` entirely - just treat
`/<GROUPS>/<GID>/<RESOURCES>/<RID>` as "the Resource", and every update just
changes its one Version in place.

If you do want history, `POST` to the `versions` collection to add a new
Version, and `GET .../versions` to list them all. The most recent (or
explicitly-chosen "default") Version is always what you get back when you
address the Resource directly, without a specific `versionid`.

#### 3.2.5. Deleting

`DELETE` on any entity or collection member removes it, cascading to
everything beneath it (delete a Group, its Resources go too).

#### 3.2.6. Errors

Errors come back as normal HTTP status codes with a JSON body describing
what went wrong, e.g.:

```json
{
  "type": "https://...#not_found",
  "title": "Not found",
  "detail": "..."
}
```

### 3.3. Defining a Basic Model

Before you can create Groups/Resources, the Registry needs a **model**
telling it what types of Groups and Resources are allowed. At its simplest,
this is just names:

```json
{
  "groups": {
    "endpoints": {
      "singular": "endpoint",
      "resources": {
        "messages": {
          "singular": "message"
        }
      }
    }
  }
}
```

This says: "there's a Group type called `endpoints` (singular `endpoint`),
and each `endpoint` can contain `messages` (singular `message`)." That's a
complete, valid model - you can have as many Group types as you like, and
each Group type can have as many Resource types as you like.

You load this via:

```
PUT /modelsource
Content-Type: application/json

{ ... model json above ... }
```

Once loaded, you can immediately do things like:

```
PUT /endpoints/ep1
PUT /endpoints/ep1/messages/msg1
```

#### 3.3.1. Adding your own attributes (extensions)

If you want Resources/Groups to carry extra domain-specific fields, add
them under `attributes`:

```json
{
  "groups": {
    "endpoints": {
      "singular": "endpoint",
      "resources": {
        "messages": {
          "singular": "message",
          "attributes": {
            "format": {
              "type": "string",
              "required": true
            }
          }
        }
      }
    }
  }
}
```

Now every `message` Resource must include a `format` string attribute, e.g.:

```json
{ "messageid": "msg1", "format": "avro" }
```

Common `type` values you'll use most often: `string`, `boolean`, `integer`,
`uinteger`, `decimal`, `timestamp`, `uri`, `array`, `map`, `object`. Useful
attribute flags: `required`, `default`, `readonly`, `enum` (restrict to a
fixed set of values).

This model is sufficient to create Groups and Resources. The full model
specification covers constraints, versioning policies, `xid` targets,
`ifvalues`, and other advanced scenarios; see [`model.md`](./model.md).

## 4. History

The CNCF Serverless Working group was originally created by the CNCF's Technical
Oversight Committee to investigate Serverless Technology and to recommend some
possible next steps for some CNCF related activities in this space. After
creating [CloudEvents](https://github.com/cloudevents) as a foundation for an
interoperable ecosystem for event-driven applications the next step was to
create a metadata model for declaring CloudEvents, their payloads and
associating those declarations with application endpoints. As a result, the
xRegistry (extensible registry) specification was created.

xRegistry was initially part of CloudEvents, called "CloudEvents Discovery" but
later moved into its own repository.

## 5. Value proposition

xRegistry provides a specification to define metadata and extensions for
resources in an abstract model that can be used to centralize and standardize
information about resources in a system. The core specification defines the
basic building blocks for managing metadata about resources and provides
multiple formats to [represent](#8-representations) this information.

xRegistry can be used to represent any type of metadata, as long as it adheres
to the basic model in which a registry consists of groups, which in turn
consists of multiple resources which can have multiple versions defined. This
model is useful for any metadata that is crucial to the operation of a system or
helps facilitate the interaction between systems. The use cases for xRegistry
are therefore very broad. See
[possible use cases](#10-possible-use-cases) for more examples.

In addition to the core specification, xRegistry provides secondary
specifications for [endpoints](../endpoint/spec.md),
[schemas](../schema/spec.md), and [messages](../message/spec.md), that further
build upon the core to provide more domain-specific standardization in the
context of event-driven systems. The following subsections provide a more
specific overview of how xRegistry can be used to address common challenges in
the event-driven space.

### 5.1. Why build something new?

There are numerous metadata registries available today. Several schema
registries exist. There are standards for container image registries, package
registries, and API registries. When this effort was started, there was no
registry for the particular use case of managing metadata about events and their
endpoints. The CloudEvents project had already defined a schema registry API to
complement the `dataschema` attribute of CloudEvents, which the team sought to
extend.

As the project evolved, it became clear that the specification needed to be more
generic to accommodate a wider range of use cases, which is why the xRegistry
specification was created. The result is a symmetric API and document format
that can be used to manage and discover the full metadata graph of a system,
given models that declare the respective resource types.

Existing registry standards like OCI, Maven, or NPM can indeed be projected into
the xRegistry resource model. This provides consistent metadata and
cross-references while the source registries remain authoritative. For example,
a container image can contain an application, published as a package, that
exposes an endpoint for events with particular payload schemas. Section
[8.3.4](#934-api-servers-and-proxies) explains how an xRegistry API can project
resources managed by another registry.

### 5.2. Discovery

One of the pain points of event-driven systems is the need to create and
maintain documentation about endpoints and the events they expose, enabling
consumers from other teams or even other organizations to find the information
they need. A centralized registry gives teams one place to discover and query
endpoints and the events they produce or consume. Extensions can describe these
events in more detail, including which metadata are required. Descriptions can
also be written for people rather than tools, so developers, data analysts, and
business analysts can use the same registry.

### 5.3. Vendor-agnostic

xRegistry provides a specification to define, query, group, version and enforce
schemas for systems. Multiple schema registry solutions exist already, including
[Confluent Schema
Registry](https://docs.confluent.io/platform/current/schema-registry/index.html),
[Azure Event Hubs
Registry](https://learn.microsoft.com/en-us/azure/event-hubs/schema-registry-overview)
or [Apicurio Registry](https://www.apicur.io/registry/), [AWS Glue Schema
Registry](https://docs.aws.amazon.com/glue/latest/dg/schema-registry.html) and
more.

These schema registries are broker- and therefore vendor-specific and even
protocol-specific, which causes friction when an event travels through multiple
brokers. In such cases, clients have to deal with the implementation differences
across registries, for example when validating event structures, hindering
interoperability and, therefore, complicating integration scenarios. xRegistry
aims to address this with an agnostic specification, providing a common base
across these offerings.

### 5.4. Versioning

As systems evolve, the endpoints that emit events may change, as may the events
themselves. These changes can break consumers, so compatibility strategies must
tell consumers how events and endpoints may evolve. xRegistry lets a registry
declare a compatibility strategy and enforces that strategy when the registry
changes. The specifications also allow endpoints to be marked as deprecated and
can identify an alternative endpoint. Event schemas are version-aware and can
retain multiple versions of a data schema.

### 5.5. Schema validation

The registry contains granular event definitions and schemas that serve as a
contract between publishers and consumers. This applies to both the message
payload and its metadata. Implementations can also use these definitions for
enforcement. For example, an event service could validate events when they are
published and reject events that do not conform to the schema for that context.

### 5.6. Payload reduction

Schema information enables real-time analysis of incoming data based on its
context. Applications therefore often use serialization formats such as JSON
that carry structural information in each payload. With that information
available from a centralized registry, applications can use lighter-weight
serialization formats and reduce bandwidth without giving up contextual
analysis.

### 5.7. Schema-based contract and client generation

The [file and API representations](#8-representations) can both supply versioned
model input to code generators. Teams can generate the data contracts needed to
interact with endpoints instead of maintaining shared packages for those
contracts by hand. A schema in a
vendor-agnostic, well-defined format can drive tools that generate
broker-specific consumers or event-store inserts. Generated producers and
consumers reduce the amount of contract code that teams must write and test.
Clemens Vasters built a proof-of-concept that shows this approach in
the [Avrotize VS Code Extension](https://github.com/clemensv/avrotize).

<a id="59-basis-for-further-developments"></a>
### 5.8. Basis for further developments

CloudEvents serve as a mechanism to aid in the delivery of events from a
producer to a consumer, which is applicable independently of the protocol (MQTT,
HTTP, Kafka, and AMQP) or encoding (JSON, XML, SOAP, Avro, etc.). xRegistry
further builds upon this by providing a specification to define resources that
correlate specific events to endpoints, providing versioning information and
more extensive metadata.

Correlating events and endpoints across a system also provides the information
needed to define event flows. Those flows can then be discovered directly
instead of reconstructed from manually maintained documentation or observed
runtime behavior.

<a id="7-design-goals"></a>
<a id="71-non-goals"></a>
## 6. Non-Goals

- **Authentication and Authorization:** Rely on established security standards
  depending on the registry representation.
- **Relationships between event channels:** Focus on precisely describing a
  single event channel before standardizing the relationships between event
  channels.

<a id="8-representations"></a>
## 7. Representations

An xRegistry can be represented as a JSON file, a static file server, or an API
server. Resources
(user-supplied data) will most often be embedded in the registry, but the
resource metadata might also point to an external location where such data
exists; also see the discussion about [embeddings and
references](#9-embeddings-references-and-federation).

The representations are symmetric so that data can move between them. Choose a
representation according to the required write path and deployment model.

<a id="81-file"></a>
### 7.1. File

The registry is represented as a single JSON file.

The primary use case for this representation is a registry whose purpose is to
be used where file-based access is preferred over network-based access.

This could be a project on your local machine or a public Git repository, where
the registry becomes a declaration manifest for the applications. Keeping the
file beside source code also keeps each revision of the registry metadata with
the corresponding code revision.

It is anticipated that application modules that need to share resources with
others, like the shape of raised events and associated schemas, will have one or
multiple associated xRegistry files that describe those resources and that
these files can later be merged into another xRegistry when the module is
deployed, so that other participants in the system can understand the
raised events.

Writing a registry by hand is useful for learning or small projects. Larger or
shared registries will usually need tooling or an API server.

<a id="82-static-file-server"></a>
### 7.2. Static File Server

The registry is represented by multiple JSON files, where each one represents a
single entity within the registry, served via a static file server (e.g. S3 or
similar) that follows the folder and file structure of the API server.

This representation allows clients to retrieve individual entities instead of
the entire registry as one JSON document. It can also serve data exported from
an API server.

It requires storage but no continuously running compute. For example, an
xRegistry can be hosted on GitHub Pages, much like a Helm registry.

Since the static file server is read-only, adding resources to the registry is
only possible by rebuilding the server and file structure, e.g. via pipelines.
If you want to directly write to the server or need sophisticated searching and
filtering, you might consider using the API server instead. Adding server logic
to the static file server to make up for the features of the API server is
considered an anti pattern.

<a id="83-api-server"></a>
### 7.3. API Server

An API server suits registries shared by multiple teams, especially when
resources have distributed ownership and require different authorization
policies.

It allows direct writes and can provide server-side searching, filtering, and
export without requiring users to generate a static directory structure.

Running the API server requires you to set up a host and a persistence
layer and maintain both. Start with this representation when direct writes,
authorization, or server-side queries are already required.

<a id="9-embeddings-references-and-federation"></a>
## 8. Embeddings, References, and Federation

The purpose of a registry is to act as a catalog more than as a container.

xRegistry is extensible with models so that the catalog entries can be
customized for the described kind of resource. You could fairly precisely
catalog a fleet of vehicles using xRegistry, but the vehicles themselves would
quite obviously not exist inside of it.

However, when a model declares a resource to be of the
["document"](spec.md#document-resources-vs-metadata-only-resources) type,
xRegistry can embed content such as schema documents. The following sections
separate document format metadata from the choice to embed, encode, or link the
document.

<a id="91-formats-and-contentmedia-types"></a>
### 8.1. Formats and Content/Media-Types

`format` and the supported values are a convention chosen for this
specification because the IANA "media-types" are not consistently available for
many document types that are in focus. There is additionally a
[contenttype](spec.md#contenttype-attribute) attribute that should be set for
each document, that provides the corresponding media-type. An example for this
is that Apache Avro schema has no official media type, so that the content type
might be "application/json", but the `format` is "Avro/1.12".

Some xRegistry implementations, including the reference server, validate
well-known formats such as Apache Avro schema and check compatibility between
versions. The specification does not define those validation implementations.
It defines indicators through which a server reports whether validation is
available and has been applied. Model metadata gives the server the information
needed to validate embedded data.

A registry server can only enforce validation constraints on embedded documents
that are under its own control. If a document is external, meaning that the
resource entry does not embed it but links to it, the document might change at
the external location without the registry knowing.

<a id="12-the-format-attribute-in-the-schema-spec"></a>
The Schema specification requires `format` when `compatibility` is anything
other than `none`, even when an implementation supports only one format. This
keeps the format explicit in exports so that another server, including one that
supports several formats, can import them without ambiguity.

<a id="92-embeddings-and-links"></a>
### 8.2. Embeddings and Links

When the resource is declared to be a document, it can be stored inside the
registry either as a directly [embedded object](spec.md#resource-attribute), a
[binary blob](spec.md#resourcebase64-attribute), or an [external URL
reference](spec.md#resourceurl-attribute).

Strictly speaking, the choice between whether, say, a schema is represented as
`schema` with an embedded object or `schemabase64` with base64 binary content
depends on the encoding of the registry metadata.

When a document is embedded, the encoding needs to align with the hosting
registry document for the [embedded object](spec.md#resource-attribute) variant.
At present, all examples and implementations use JSON and so it might appear
that this is a JSON-related feature, but it's very feasible to encode the entire
registry in Avro binary and there is a formal schema for Avro.

In JSON, we can embed JSON-data like an Avro Schema into `schema` and we can
also embed a single string for a text file into `schema` as long as we are
applying appropriate escaping rules for JSON strings and we can use the same
character encoding as the hosting JSON document. Any other document will be
base64 encoded and stored in `schemabase64`. The `schemacontenttype` is meant
to hold media-type and encoding of that data.

You can also refer to the target document through a `<RESOURCE>url` attribute.
The URL can identify an HTTP resource or a file-system location, which allows
documents in an existing registry or public repository to remain in place. The
`format` and `contenttype` information still needs to exist in xRegistry so
that clients can interpret the document before resolving it. The registry does
not resolve the URL or load the content; clients do that.

<a id="93-federation"></a>
### 8.3. Federation

xRegistry does not have a synchronization API, by intent. Since xRegistry is
both a document format model and an API, the integration of multiple registries
("federation") does not rely on making copies but is intended to work via
cross-referencing and "shadowing" across the [representations](#8-representations)
described earlier.

<a id="931-composing-registries-in-memory"></a>
#### 8.3.1. Composing registries in memory

A registry document, whether a single [file](#81-file) or the root of a
[static file server](#82-static-file-server) layout, is meant to be loaded into
an application as a local, in-memory registry. A registry document used on its
own must embed a model to be valid. A server may nevertheless accept source
input that contains only resources and metadata, supply a model it already
knows, and construct a valid registry from both. There are several examples of
such source documents in the
[cloudevents/samples](../cloudevents/samples/README.md) folder.

When the registry is split across multiple files in a folder structure, the
application can load the root document and traverse `<RESOURCE>url` links to
individual documents on demand, building an in-memory view that combines the
root document with only those branches that are relevant to the application. The
same applies when the root sits behind an [API server](#83-api-server) or proxy:
the client fetches and caches just the branches it needs.

<a id="932-shadowing"></a>
#### 8.3.2. Shadowing

Federation in xRegistry is intended to be built on *shadowing*: an application's
view is a layered combination of registries, where a local registry can override
or extend entries from an underlying one without modifying it. We say "intended"
because the specification does not define a protocol for this composition.

Layering registries and selective shadowing lets an application keep locally
modified copies of selected resources while continuing to read untouched
resources from the underlying registry. Layer precedence resolves duplicate
entries, but incompatible models or constraints can still make the composed
registry invalid.

When dealing with files, applications load files in order and merge the
content, with later files taking precedence over earlier ones.

The principle applies uniformly across representations. A file can shadow
another file, a folder can shadow an API server, and an API server can shadow
another API server. The application always sees the composed result as a
single registry.

For the xRegistry 1.0 release, composition and shadowing should be considered an
emerging best practice. Mind that there is potential for conflicts when multiple
registries are layered where the models are not identical or when resources and
their versions are merged and constraints are not fully aligned. We believe that
composition and shadowing is the best approach to federation, but the project
will need to gain more experience with it in practice before it can be
formalized.

<a id="933-identifiers"></a>
#### 8.3.3. Identifiers

For shadowing and cross-referencing to work, identifiers need to be stable
across registries. Group identifiers should be treated as globally unique, so
that the same group can be recognized across different registries. Resource
identifiers are only unique within a group, so a cross-registry reference should
always use the combination of group identifier (group name and id) and resource
identifier (resource name and id).

The authority portion of a URL into a registry identifies the hosting endpoint,
not the resource itself. The same resource may be available in multiple
registries, and applications can refer to it using the same *relative URI*
regardless of which registry hosts it. For example, an application in a private
network may resolve the URI against a local registry when it cannot reach the
public registry.

<a id="934-api-servers-and-proxies"></a>
#### 8.3.4. API Servers and Proxies

An API server can also act as a proxy that presents multiple underlying
registries - including non-xRegistry ones - through a single xRegistry
interface. The [xrproxy](https://github.com/xregistry/xrproxy) project provides
reference implementations of such proxies, showing both how to federate
xRegistry APIs and how to project other registry models into the xRegistry
model.

Shadowing applies here too: any API client can shadow the API server with a
local registry to add or modify entries without affecting the underlying
registry, and a proxying API server can do the same on behalf of its clients.

<a id="10-possible-use-cases"></a>
## 9. Possible Use Cases

<a id="101-cloudevents"></a>
### 9.1. CloudEvents

Since xRegistry emerged from the CloudEvents project and initially was called
"CloudEvents Discovery" the obvious use case is to manage all the CloudEvents of
your event-driven architecture inside xRegistry. The spec supports "CloudEvents"
as a format and allows you to define further restrictions on how your
CloudEvents look, what extensions they use or which fields are required for your
specific use-case even though the original spec marks them as optional. In
addition, the `dataschema` attribute of a CloudEvent can then point to a
xRegistry schema document making this two projects that work hand in hand.

<a id="102-business-objects"></a>
### 9.2. Business objects

When defining the schemas of business objects in an enterprise, xRegistry can be
the schema store for these definitions. One can then reference them in a data
catalogue as well as in OpenAPI and AsyncAPI documents without repeating the
schemas for the actual business objects.

<a id="103-metadata-files-in-repositories"></a>
### 9.3. Metadata files in repositories

The [file representation](#81-file) supports a repository-level manifest similar
to `package.json`. Such a manifest can list the repository's metadata files and
provide machine-readable access to project dependencies and configuration.

<a id="11-design-decisions-or-topics-of-interest"></a>
## 10. Design decisions or topics of interest

<a id="111-resourceid-vs-resourceversionid"></a>
### 10.1. Resource.ID vs Resource.Version.ID

Resources, like all xRegistry entities, have unique `id` values. Resource
`id`s are often user-friendly values that often have an implied semantic
meaning of the purpose of the underlying Resource document. Also, since they
are static values and as the Resource changes over time (meaning, new Versions
are created), it's important for end-users to have a static URL reference to
the default Version of the Resource.

Versions of a Resource, on the other hand, might change quite often and the
`id` isn't meant to convey the purpose of the underlying entity, rather it is
meant to uniquely specify its "version number". As such, the semantics
meaning and usage of the two `id` values are quite different. This means that
there might be times when they are the same value. However, while this is
allowable, it has no influence on any specification defined semantics of the
xRegistry model. As a result, implementations might want to avoid using `id`
values that could appear on a Resource and one of its Versions simply to avoid
potential confusion for their end-users.

<a id="112-valid-characters"></a>
### 10.2. Valid Characters

Attribute names appear in JSON objects, HTTP headers, URLs, and generated code.
The specification therefore uses a restricted character set that works across
those contexts. Section [10.10](#1111-naming-and-case-sensitivity) explains the
casing rules. Section 10.11 explains the additional restrictions on Group and
Resource type names.

The specification permits underscores in attribute names, but some proxies,
including nginx with its default configuration, drop HTTP headers containing
underscores. Implementations that expose attributes as headers need to account
for that behavior.

Map keys allow more characters than attribute names because they are normally
stored as strings rather than mapped to named fields in code structures.

<a id="113-extensions"></a>
### 10.3. Extensions

Extensions SHOULD be defined in the model. A model can also define a `*`
extension to allow attributes supplied at runtime. Extension names follow the
[valid character](#112-valid-characters) and
[casing](#1111-naming-and-case-sensitivity) rules for all attributes.

Required aspects apply at each level of a nested extension. In particular,
`clientrequired=true` also requires `serverrequired=true`; otherwise the model
is invalid.

<a id="119-potential-extensions"></a>
Implementations that track the identity responsible for a change might define
`createdby` and `modifiedby` extensions alongside `createdat` and `modifiedat`.
The core specification does not define them because it does not define
authentication or identity tracking.

<a id="114-group-organization"></a>
### 10.4. Group organization

Groups are intentionally a single organizational dimension above Resources:
the model is always Registry → Group → Resource → Version, and Groups
themselves do not contain other Groups. This is a deliberate design choice.
Allowing arbitrary nesting of Groups would significantly complicate the
model, the URL space, traversal and filter semantics, access-control
reasoning, and tooling, without adding expressive power that cannot be
achieved by other means.

Where hierarchical organization is useful, xRegistry instead relies on
dot-notation in Group identifiers. Because Group IDs may contain dots, an
identifier like `Contoso.ERP.Orders` naturally expresses a logical
hierarchy (`Contoso` → `ERP` → `Orders`) while keeping the underlying
collection flat. Prefix filters can select related identifiers without adding
nested containers to the model.

Labels provide independent classification dimensions. They are free-form
name/value pairs attached to Registries, Groups, Resources, Meta entities, and
Versions, for example `stage=dev`, `team=payments`, or `tier=gold`. Server
implementations may support filtering and lookup by labels; see the filter
examples in the core specification.

<a id="115-deleting-entities"></a>
### 10.5. Deleting entities

The "delete" operation typically has two variants:

- `DELETE .../<ID>[?setdefaultversionid=VID]`
- `DELETE .../<COLLECTION>[?setdefaultversionid=VID]`

where the first will delete a single entity, and the second can be used to
delete multiple entities. For collection deletion:

- if the HTTP body is empty, then the entire collection will be deleted.
  If the collection is `versions`, then the owning Resource must also be
  deleted since a Resource must always have at least one Version
- if the HTTP contain an array, then an empty (zero item) array is valid,
  but it will have no change on the server since there are not items listed
  to be deleted
- if the array is not empty and one of the items in there is already deleted,
  or never existed at all, then rather than generating an error (e.g. a `404`),
  the server will ignore this condition and continue processing the list.
  This is because the net result will be what the user is asking for.
  Note, that this is different from `DELETE ../<ID>` case where if the
  referenced entity can not be found then a `404` must be generated.
- when the `?setdefaultversionid` query parameter is specified (when
  deleting Version) then it will be applied after all requested items have
  been deleted successfully. It can be used even if the current "default"
  Version isn't being deleted. Note that a `404` in the `DELETE .../<ID>` case
  is an error and no changes to the "default" Version will occur.

<a id="116-detection-of-referenced-resources"></a>
### 10.6. Detection of Referenced Resources

The xRegistry specification allows for Resources to appear in multiple Groups
via use of the `xref` feature. This could lead to situations where a user
deletes a Resource without knowing that other Resources reference it -
resulting in "dangling pointers". The specification does not define any
mechanism by which a user can determine if a Resource is the target of an
`xref`, or how many other Resources might reference it, in order to avoid
this situation. However, implementations may choose to take some action to
help users if they wish. For example, provide some kind of "warning" of the
impending "dangling pointer" state prior to doing the delete, or providing
some kind of "xref counter" extension on the target Resource. The specification
might consider adding some feature to address this in the future, but as of now
it is left as an implementation choice.

<a id="117-sharedreferenced-resources"></a>
### 10.7. Shared/Referenced Resources

Beyond detecting dangling references, users need to decide how shared Resources
are owned. For example, if a
Resource might be removed from any of the Groups it is a member of, then it
might be best to create a dedicated "shared resources" type of Group so that
it can have a lifecycle that is independent of its association of any other
Group. Similarly, choosing an initial Group for the Resource could be a
critical decision as it can not be changed later on, and that Group ID will
be part of the Resource's unique identifier forever.

Additionally, how the implementation of the xRegistry manages
access-control-rights of Resources (often via Groups) might influence the
initial placement into a Group of a new Resource.

<a id="118-default-version-and-maximum-versions"></a>
### 10.8. Default Version and Maximum Versions

Each Resource type can specify the maximum number of Versions that the
server must save. Once that limit is reached then it must delete Versions
to stay within the limit - by deleting oldest Versions first. However, since
tagging a Version as "default" marks that Version as special, this pruning
logic must skip the "default" Version. There is one exception to this rule.
If the maximum Versions is set to 1 then when a new Version is created, that
Version will become the "default" Version regardless of whether or not the
user asked for it to be.

In general, during an operation that creates, updates or deletes the Versions
of a Resource, the following logic is applied:

- Modify the Versions collection as requested
- Apply the "default" processing logic by setting (or not) which Version is the
  "default"
- If the number of Versions exceeds the maximum allowed Versions then, starting
  with the oldest, keep deleting until the collection is within the limit.
  Except if the limit is 1, in which case if a new Version is created then it
  it tagged as "default"

Let's walk through a complex example:

- Max allowed Versions is 2
- Initially the following Versions exist: v4, v2 (default)
- Max allowed Versions is now set to 0 (meaning unlimited)
- New Versions are created in this order: v5 (default=true), v6, v7
- The resulting Versions are (newest to oldest): v7, v6, v5 (default), v4, v2
- The maximum allowed Version is now set to 1, this will cause pruning
- The result is: v5. Note that it is not v7 because v5 was tagged as "default"
- A new Version (v8) is created
- The result is: v8 regardless of whether v8 was created with isdefault=true or
  not

<a id="1110-why-epoch"></a>
### 10.9. Why Epoch?

Why such an unusual name? As the specification describes, `epoch` is used as a
way to help detect when an entity has been modified. It is very similar to
HTTP's [ETag](https://datatracker.ietf.org/doc/html/rfc9110#name-etag)
header.

When choosing a name for this attribute the most obvious choices revolved
the word `version`. However, the potential overlapping naming and differing
semantics conflicts with the Version entity of the model could lead to
confusion. We decided to use `epoch` because "epoch" is about "time",
which is indirectly related to what this attribute is meant to convey: has
this entity's history changed?

Additionally, the word is unique enough that the chances of people assuming
they know what it means due to some other usage in this technology space
seemed unlikely. In fact, use of this word might pique people's curiosity
and cause them to look it up in the specification to find out more about it.

<a id="1111-naming-and-case-sensitivity"></a>
### 10.10. Naming and Case Sensitivity

The following explains some of the reasoning behind the casing and case
sensitivity rules in the specification.

- Attributes must be lower case.
  Attributes, include extensions attributes, can appear in many different
  locations. When serialized as part of the xRegistry metadata for an entity,
  they would appear in a JSON object as an attribute name and in those cases
  the case of the name matters. However, that same name might also appear in
  an HTTP header name - where its case is not relevant, and can be freely
  changed by middleware.

  Since it is possible for unknown attributes to appear in case insensitive
  locations, it would then be impossible for implementations of the
  specification to know what the true/intended case of the attribute name
  should be. To avoid mismatches, confusion and interoperability issues, the
  specification requires all attribute names to be in lower case. This avoids
  complicated logic to guess as to the proper case of these names.

- Groups and Resources must be lower case.
  The plural version of the Group and Resource type names can appear in URLs
  (which is case-sensitive). Additionally, the plural variant can also appear
  in attribute names (e.g. `<COLLECTION>*` attributes), and as discussed above,
  attributes must be lower case.

  The singular version of the Group and Resource type names, can also appear
  in the `<RESOURCE>*` attributes, which (again) means they must be lower case.

  For these reasons, both the plural and singular names of Group and Resource
  types must be defined as lower case.

- IDs are case-sensitive and case-insensitive.
  Entity identifiers (`id`s), never appear as attribute or HTTP header
  names. Meaning, they never appear in case-insensitive locations, so they
  do not have the same constraints that attributes, Groups or Resources do.
  For this reason, IDs are not restricted to using just lower case letters.
  This then also means that when there is a "look-up" done by an ID, it must
  be done in a case-sensitive way.

  However, there is another aspect of IDs that needs to be taken into account:
  the human factor. Despite them being case-sensitive, if the specification
  allowed for two entities at the same location in the data model to exist
  where they had the same IDs except for their case, it could make things very
  error-prone for users and leave them with a bad user experience.

  For this reason, while the processing of IDs is treated as case-sensitive
  values, the specification requires that IDs must be case-insensitive unique
  within the scope of its parent entity.

  While it may have been more consistent to just require IDs to be lower case
  like many of the other names in the specification, it was deemed unnecessary
  from a technical perspective. Additionally, IDs are often exposed to end
  users as unique identifiers (almost as a "name"), allowing mixed case can
  provider a better user experience.

  Additionally, treating them in a case-insensitive way could lead to
  inconsistencies and frustration for users. If a user purposely used a certain
  casing pattern, but then someone else uses a different pattern for the same
  entity, it is possible that one of those users would end up seeing an
  unexpected casing and could be confused or believe there was an error.

  The specification therefore requires case-sensitive lookup while prohibiting
  IDs that differ only by case within the same parent.

<a id="1112-why-the-lower-character-limit-on-some-group-and-resource-type-names"></a>
### 10.11. Why are Group and Resource type names more restricted?

Attribute names and key names are limited to 63 characters, so why are some
Group and Resource names limited to less? Because when they appear as part of
attribute names and they can be appended with phrases like `url`, `count`
or `base64`, and they still have to fit within the 63-character limit, and so
we need to take into account the length of those phrases. As a result, both
Group and Resource type names (both singular and plural) are limited to
57 characters.

<a id="1113-why-must-group-type-and-resource-type-names-be-valid-attribute-names"></a>
Since Group type and Resource type names will appear as attribute names (e.g.
`<GROUPS>count` and `<RESOURCE>url`), the character set (and length) of their
names need to be restricted in the same way as a attribute names.

<a id="1114-choosing-unique-group-and-resource-names"></a>
### 10.12. Choosing unique Group and Resource names

Aside from choosing names that give some descriptive meaning to the purpose
of these entities, care should be taken when choosing names for entities that
might be imported into other Registries. For example, Group names are often
suffixed (or prefixed) with domain (or company) specific words to avoid
name collisions with other similarly named entities. This might be useful
for Resource names too (if they might co-exist under shared Groups), but
normally ensuring uniqueness at the Group level is sufficient.

<a id="17-defining-extensions"></a>
The same collision guidance applies to model extensions and new APIs; their
names should remain clear of future xRegistry additions.

<a id="1115-are-self-and-shortself-attributes-static"></a>
### 10.13. Are `self` and `shortself` attributes static?

In general any URL reference to an entity in the Registry should remain
static for the lifetime of the entity, otherwise anything persisting that
reference will break when it attempts to use it. So, in this sense, yes
these attributes should be static in general. However, the specification
can not mandate this because there may be times when the risk of breaking
existing references becomes necessary.

For example, perhaps a Registry needs to move to a new host, and the old
one is no longer available, even to offer a redirect. Or, if the server
needs to switch to a new "URL shortener" service and so all of the "shortself"
values need to change.

Obviously, situations like these should be rare but the specification needs
to allow for them.

<a id="1116-why-does-an-unknown-query-parameter-not-generate-an-error"></a>
### 10.14. Why does an unknown query parameter not generate an error?

People have identified cases where query parameters might be added to request
URLs without the client (or developer) having control to prevent it. It might
be client-side tooling or intermediaries (e.g. proxies) that might modify
the URL - for example to add tracking or end-to-end tracing information.

To avoid these clients not being able to interact with an xRegistry deployment,
the authors chose to have the server ignore unknown query parameters. The
specification says they SHOULD be ignored, not that they MUST be ignored. An
implementation can reject them, but doing so risks interoperability problems.

<a id="1117-updating-attributes-with-ifvalues"></a>
### 10.15. Updating attributes with `ifvalues`

The `ifvalues` feature might be a new concept for some readers, so a point
of clarification might be useful. If an attribute is defined with an `ifvalues`
aspect, then if that attribute's value changes it is possible that the
set of sibling attributes that are part of that entity's model could change
due to a new `ifvalues` match (or due to no match at all).

When a client is performing a write operation that changes that attribute's
value, the client must ensure that the net result of the changes are compliant
with the resulting model. Meaning, if that attribute's new value adds or
removes attributes then the client might need to also change other attributes
in the entity in order to be model compliant.

Likewise, implementations of the server must validate the entire entity
against the new model, not just a subset of the entity's attributes.

<a id="1118-multi-root-ancestor-hierarchies"></a>
### 10.16. Multi-root ancestor hierarchies

The [`ancestorid` attribute](./spec.md#ancestorid-attribute) builds a Version
hierarchy for compatibility checking when the
[`compatibility` attribute](./spec.md#compatibility-attribute) is set. Some
use cases need multiple roots. Pruning can also create additional roots;
section [10.18](#1120-pruning-versions-with-singleversionroot-enabled)
describes the case in which `singleversionroot` prevents that operation.

To signal that a Version represents a root of a hierarchy, the `ancestorid`
attribute has its value set to the Version's `versionid` attribute. This
makes the ancestor explicit, and the possible ambiguity of using another
value such as null which, based on the scenario, could mean "no ancestor" or
"default to the newest".

<a id="1119-singleversionroot-policy-enforcement"></a>
### 10.17. `singleversionroot` Policy Enforcement

Related to the previous discussions concerning the `ancestorid` attribute,
the [Resource Model](./model.md#registry-model) `singleversionroot` attribute
controls whether a Resource is allowed to have more than one "root" Version,
or whether all Versions of that Resource must be a descendant of the same
"root" Version.

Whether `singleversionroot` is `true` or `false` will depend on the use case
in which the Registry is being used. Some examples that might help pick the
most appropriate value include:

- If each major version of a Resource is a significant change, such that to
  that domain's users it could be considered an entirely new Resource (e.g.
  a non-backwards compatible change has been made), then setting
  `singleversionroot` to `true` and using a different xRegistry Resource for
  each major version might be appropriate. Note that this then implies that all
  Versions under each Resources will likely be compatible, and some
  environments have such a policy requirement.

- However, if a new Resource for each major version introduces a concern about
  the proliferation of Resources, and a domain's users are comfortable if
  checking the Versions string for each Version of a Resource as a hint to the
  compatibility of the Versions, then setting `singleversionroot` to `false`
  might be appropriate. Additionally, a value of `false` might make sense if
  the version string is "just another attribute" of the Version and the
  Resource is acting more like a "collection" of Versions rather than an
  enforcer of a semantic versioning policy.

These examples are not meant to be complete. The flexibility of the
specification allows for model authors to choose the most appropriate value
for their needs.

<a id="1120-pruning-versions-with-singleversionroot-enabled"></a>
### 10.18. Pruning Versions with `singleversionroot` enabled

There are cases in which the server will need to prune Versions. For
example, this can happen when attempting to create a new Version that would
exceed the value set on the `groups.resources.maxversions` attribute of the
[Resource Model](./model.md#registry-model), or when adjusting this attribute's
value that is smaller than the number of existing Versions. In such
scenarios, the server may be unable to prune Versions, when the
`groups.resources.singleversionroot` attribute of the
[Resource Model](./model.md#registry-model) is set to `true` and the request
must be rejected.

Consider a scenario in which 3 Versions exist: v1 is the root (and therefore
has its `ancestorid` attribute set to v1), and v2 and v3 both have
their `ancestorid` attribute set to v1. In addition, the
`groups.resources.maxversions` is set to 3. When creating a new Version, the
server will find the oldest Version (v1) and attempt to prune it. However,
deleting v1 would mean that v2 and v3 would become roots, as both of them
would need to point to themselves. This is exactly the behavior that the
`groups.resources.singleversionroot` attribute prevents when set to `true`.
Therefore, the server is unable to prune Versions and will block the
creation of a new Version. To resolve this, the user will have to manually
delete v2 or v3 to allow the server to prune the oldest Version (v1) before
creating a new Version.

<a id="1121-whats-the-oldestnewest-version-of-a-resource"></a>
### 10.19. What's the oldest/newest Version of a Resource?

The oldest Version of a Resource isn't necessarily the one with the oldest
`createdat` timestamp, because the `ancestorid` attribute takes precedence
over the `createdat` attribute. This is because the ancestor tree more
accurately describes an ordered lineage of the Versions than timestamps. In
the case multiple Versions exist with the same `createdat` timestamp, those
Versions are sorted in a ascending alphabetical order, and the first is the
oldest Version.

The newest Version of a Resource is selected by searching in the opposite
direction: first identifying all leaves of the hierarchy (i.e. all Versions
that are not used as ancestors for any other Versions), and then finding the
one with the newest `createdat` timestamp. In the case that multiple
Versions exist with the same `createdat` timestamp, those Versions are
sorted in an descending alphabetical order, and the first is the newest
Version.

<a id="1122-can-validatecompatibility-and-validateformat-be-true-for-file-servers"></a>
### 10.20. Can `validatecompatibility` and `validateformat` be `true` for file-servers?

`validatecompatibility` and `validateformat` report both policy and validation
state. A file server cannot enforce those policies on write, but it can expose
either attribute as `true` when the published data was validated before
deployment.

For example, an API server can validate data before exporting it to a file
server. Clients can then use either representation without needing to account
for that deployment choice.

<a id="1123-detecting-circular-references-between-versions"></a>
### 10.21. Detecting circular references between Versions

The specification mentions that the Version's `ancestorid` attribute should not
be set in such a way as to cause a circular dependency list between Versions.
However, when talking about the server generating an error in such conditions
it says it is "STRONGLY RECOMMENDED" that an error is generated, not that it
"MUST" be generated. This is not meant to be used by implementations as a way
to avoid doing the check in general. However, it is recognized that there
might be situations (such as when the number of Versions is very large) that
performing this check upon every change could become a performance concern.

Rather than mandating a potentially burdensome requirement on implementations,
the specification allows for this check to be skipped if there is no
reasonable way to do it. However, if an implementation chooses not to perform
the check then it becomes incumbent upon them to ensure that there are no
negative ramifications. For example, when performing backwards compatibility
checking, they may need to add extra logic to ensure they don't go caught in
an infinite loop. Additionally, implementations should also document that they
do not enforce this check to set the proper expectation levels for their users.

<a id="1124-optional-required-fields-in-requests"></a>
### 10.22. Optional required fields in requests

One of the design principles of the specification was to try to make each
object be fully self-describing, within reason. For example, this is why when
objects appear within maps the map key is often replicated within the object
itself. For example, when looking at a Versions collection it might look like
this:

```yaml
"version": {
  "v1": {
    "versionid": "v1",
    ...
  },
  "v2": {
    "versionid": "v2",
    ...
  }
}
```

Notice that the key is duplicated as the `versionid` in each case.

However, when those attributes are defined as "required", that does not
necessarily mean that they are required to appear on all requests if the
server can determine the proper value via some other means, such as the owning
map key, or if the request URL includes the information.

From specification perspective, all that's required is that after any
operation all required fields have valid values. Whether it is provided by
the client or calculated/inferred by the server is an implementation detail.

This accommodation only applies to incoming messages. All server generated
messages (aside from when special flags, like the `?doc` flag, is enabled)
must include all required attributes, even if they are duplicated elsewhere
in the message.

<a id="1125-deprecation-of-entities-in-an-xregistry"></a>
### 10.23. Deprecation of entities in an xRegistry

The core specification defines a `deprecated` attribute that may appear
under a Resource's `meta` sub-object. This attribute was added to the Resource
itself rather than to the Version because it was determined that the most
likely usage of this feature is to express the intent to deprecate the entire
Resource rather than just one Version (or subset of Versions). This is not say
that the use of this feature might not be useful at the Version-level or even
at the Group-level. However, for those cases, custom models may define
an extension at the appropriate location in the model to meet their needs.
When doing so it is recommended to use the same attribute definition as
defined in the core specification for consistency. The Endpoint
[specification](../endpoint/spec.md) does exactly this to indicate when an
Endpoint (i.e. a Group) is deprecated.

<a id="13-problematic-characters-in-values"></a>
## 11. Problematic characters in values

Attribute values can be used outside the scope of the xRegistry specification.
For example, a `name` or ID value might become a file name. The character rules
for values cannot account for every constraint imposed by those external
systems, such as the restriction on colons (`:`) in Windows file names.

Tooling must decide how to handle such cases. It can convert or escape the
value, reject it, or require the user to choose a value that is valid in the
target system. The specification does not prescribe that behavior.

<a id="14-why-do-resources-have-3-levels-of-data"></a>
## 12. Why do Resources have 3 levels of data?

Resource attributes are split into 3 categories:

- Resource level
- Resource Meta level
- Resource Version level

which corresponds to the structure of the Resource object. In other words the
Resource, serialized in JSON, appears like this:

```yaml
{
  "<RESOURCE>id": ...,
  # Resource level attributes appear here
  # Additionally the "default" Version's attributes would appear here

  "meta": {
    "<RESOURCE>id": ...,
    # Resource meta level attributes appear here
  }

  "versions": {
    "<KEY>": {
      "<RESOURCE>id": ...,
      "versionid": ...
      # Resource Version level attributes appear here
    }
  }
}
```

"Resource level" attributes consist of two types:
1 - Attributes that makes sense when the Resource is viewed as an alias for
    the default Version of that Resource. So this would include all of the
    default Version's attributes with the exception that any URLs referencing
    the Version (e.g. `self`) would point to the Resource instead.
2 - Attributes to help in the navigation of the Resource structure. This
    includes the "meta" sub-object, the "metaurl" and the "versions"
    collection related attributes.

This allows for clients to interact with the Resource and the Resource's
default Version almost interchangeably. Most notable difference are the extra
attributes from group 2 above.

"Resource Meta" level attributes are attributes that are global, and apply
to the Resource itself and potentially to all Versions of the Resource.
Such as the creation date of the Resource, or whether the Resource and its
Versions are read-only. Ideally, these would be present at the Resource level
but to avoid potential collisions with Version attributes, it was moved into
the "meta" sub-object. Additionally, it's expected that the "meta" level
attribute are not normally the most significant data of the Resource - that
would be the Version attributes - and they will probably not be examined or
changed nearly as often as the Version attributes.

"Resource Version" level attributes, as the name implies, are attributes
that can change on a per-Version basis. These are expected to be the main
reason for the Resource to exist.

The choice of when an attribute appears in the "meta" sub-object versus in the
Version should be driven by whether the use cases being supported by the
Resource type definition requires that attribute to be consistent across all
Versions or have a Version-specific value.

<a id="15-why-are-some-conditional-read-only-attributes-not-ignored"></a>
## 13. Why are some (conditional) read-only attributes not ignored?

Attributes that are always defined as "read-only" normally have semantics such
that attempts to update them are silently ignored. This is especially useful
for attributes that might change over time so that clients do not need to
either ensure they have the latest value, or remove them from an update
request.

However, there are times when trying to update a read-only attribute must
generate an error. This will happen when the attribute might be read-only based
on the configuration of the owning entity, in which case it is important for
clients to know that updating this particular instance of this
"sometimes read-only" attribute failed. So, while it may seem inconsistent,
the risk of clients assuming a non-error response meant the request was fully
adhere to was considered more important.

For example, if a Resource is defined with the `setdefaultversionsticky`
aspect set to `false` then the `meta.defaultversionid` attribute of instances
of that Resource becomes "read-only". And any attempt to update it will result
in an error being generated.

<a id="16-why-isnt-put-idempotent"></a>
## 14. Why isn't `PUT` idempotent?

As stated in the [core](./spec.md) specification, the `PUT` operations are
almost idempotent, per the HTTP specification. For the most part, multiple
similar `PUT` requests will have the same effect as a single one, with the
exception that `epoch` and `modifiedat` will be updated each time. This is
due to the desire to avoid having server implementations perform a "diff" type
of check on all attributes to determine if anything changed, and then only
"bumping" those attributes' values if there was a change. This could be an
expensive or ambiguous check to perform, so it was determined it would be best
to avoid it all together.

<a id="18-validation-edge-cases"></a>
## 15. Validation edge cases

Sections [5.5](#55-schema-validation) and
[8.1](#91-formats-and-contentmedia-types) explain the purpose and boundaries of
validation. The following cases cover two less obvious interactions between
validation settings.

<a id="181-empty-format-capabilities"></a>
### 15.1. Empty format capabilities

If a Resource model sets both `validateformat` and `strictvalidation` to `true`,
but the Registry's `capabilities` declares no `format` values, the server will
reject every non-empty `format` value as unknown.

A lightweight server that performs no validation can therefore expose an
unusable Resource type if its model enables those aspects and clients supply
`format`.

<a id="constraints-and-matchversions-features"></a>
<a id="182-constraints-and-matchversions"></a>
### 15.2. Constraints and `matchversions`

`constraints` and `matchversions` validate only scalar attributes in objects.
They do not apply inside maps, arrays, `ifvalues` clauses, or `*` extensions.
Extending validation into those structures would increase implementation
complexity and make consistent support across servers less likely.
