# xRegistry Primer

<!-- words: validatecompatibility validateformat -->
<!-- words: strictvalidation matchversions messageurl -->
<!-- words: readme standalone upserts -->

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
    - [3.2.3. Resources: metadata vs. the actual
      document](#323-resources-metadata-vs-the-actual-document)
    - [3.2.4. Versions](#324-versions)
    - [3.2.5. Deleting](#325-deleting)
    - [3.2.6. Errors](#326-errors)
  - [3.3. Defining a Basic Model](#33-defining-a-basic-model)
    - [3.3.1. Adding your own attributes
      (extensions)](#331-adding-your-own-attributes-extensions)
  - [3.4. Where to go next](#34-where-to-go-next)
- [4. History](#4-history)
- [5. Value proposition](#5-value-proposition)
  - [5.1. Why build something new?](#51-why-build-something-new)
  - [5.2. Discovery](#52-discovery)
  - [5.3. Vendor-agnostic](#53-vendor-agnostic)
  - [5.4. Versioning](#54-versioning)
  - [5.5. Validation and compatibility](#55-validation-and-compatibility)
  - [5.6. Metadata sharing](#56-metadata-sharing)
    - [5.6.1. Payload reduction](#561-payload-reduction)
    - [5.6.2. Schema-based contract and client
      generation](#562-schema-based-contract-and-client-generation)
  - [5.7. Messaging models as a basis for further
    development](#57-messaging-models-as-a-basis-for-further-development)
- [6. Non-Goals](#6-non-goals)
- [7. Representations](#7-representations)
  - [7.1. File](#71-file)
  - [7.2. Static File Server](#72-static-file-server)
  - [7.3. API Server](#73-api-server)
- [8. Embeddings, References, and
  Federation](#8-embeddings-references-and-federation)
  - [8.1. Formats and Content/Media-Types](#81-formats-and-contentmedia-types)
  - [8.2. Embeddings and Links](#82-embeddings-and-links)
  - [8.3. Federation](#83-federation)
    - [8.3.1. Storage and data-source choices](#831-storage-and-data-source-choices)
    - [8.3.2. Entity identity across registry
      views](#832-entity-identity-across-registry-views)
- [9. Possible Use Cases](#9-possible-use-cases)
  - [9.1. CloudEvents](#91-cloudevents)
  - [9.2. Business objects](#92-business-objects)
- [10. Design decisions or topics of
  interest](#10-design-decisions-or-topics-of-interest)
  - [10.1. Resource.ID vs Resource.Version.ID](#101-resourceid-vs-resourceversionid)
  - [10.2. Valid Characters](#102-valid-characters)
  - [10.3. Extensions](#103-extensions)
    - [10.3.1. Potential extensions](#1031-potential-extensions)
  - [10.4. Group organization](#104-group-organization)
  - [10.5. Detection of Referenced
    Resources](#105-detection-of-referenced-resources)
  - [10.6. Shared/Referenced Resources](#106-sharedreferenced-resources)
  - [10.7. Why Epoch?](#107-why-epoch)
  - [10.8. Naming and Case Sensitivity](#108-naming-and-case-sensitivity)
  - [10.9. Why are Group and Resource type names more
    restricted?](#109-why-are-group-and-resource-type-names-more-restricted)
  - [10.10. Choosing unique Group and Resource
    names](#1010-choosing-unique-group-and-resource-names)
  - [10.11. Are `self` and `shortself` attributes
    static?](#1011-are-self-and-shortself-attributes-static)
  - [10.12. Why does an unknown query parameter not generate an
    error?](#1012-why-does-an-unknown-query-parameter-not-generate-an-error)
  - [10.13. Updating attributes with
    `ifvalues`](#1013-updating-attributes-with-ifvalues)
  - [10.14. Multi-root ancestor hierarchies](#1014-multi-root-ancestor-hierarchies)
  - [10.15. `singleversionroot` Policy
    Enforcement](#1015-singleversionroot-policy-enforcement)
  - [10.16. Pruning Versions with `singleversionroot`
    enabled](#1016-pruning-versions-with-singleversionroot-enabled)
  - [10.17. What's the oldest/newest Version of a
    Resource?](#1017-whats-the-oldestnewest-version-of-a-resource)
  - [10.18. Can `validatecompatibility` and `validateformat` be `true` for
    file-servers?](#1018-can-validatecompatibility-and-validateformat-be-true-for-file-servers)
  - [10.19. Detecting circular references between
    Versions](#1019-detecting-circular-references-between-versions)
  - [10.20. Optional required fields in
    requests](#1020-optional-required-fields-in-requests)
  - [10.21. Deprecation of entities in an
    xRegistry](#1021-deprecation-of-entities-in-an-xregistry)
  - [10.22. Problematic characters in values](#1022-problematic-characters-in-values)
  - [10.23. Why do Resources have 3 levels of
    data?](#1023-why-do-resources-have-3-levels-of-data)
  - [10.24. Why isn't `PUT` idempotent?](#1024-why-isnt-put-idempotent)
  - [10.25. Validation edge cases](#1025-validation-edge-cases)
    - [10.25.1. Empty format capabilities](#10251-empty-format-capabilities)
    - [10.25.2. Constraints and `matchversions`](#10252-constraints-and-matchversions)
  - [10.26. Relative Resource URLs in the File
    representation](#1026-relative-resource-urls-in-the-file-representation)


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
GET/PUT/PATCH        /                                                 # the Registry itself
GET                  /model                                            # the model definition
GET/PUT              /modelsource                                      # the model, as you defined it

GET/POST/PATCH       /<GROUPS>                                         # e.g. GET /endpoints
GET/PUT/PATCH/DELETE /<GROUPS>/<GID>                                   # e.g. .../endpoints/ep1

GET/POST/PATCH       /<GROUPS>/<GID>/<RESOURCES>                       # e.g. .../endpoints/ep1/messages
GET/PUT/PATCH/DELETE /<GROUPS>/<GID>/<RESOURCES>/<RID>                 # a Resource (its default Version)

GET/PUT/PATCH/DELETE /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>  # a specific Version
```

`<GROUPS>` and `<RESOURCES>` are whatever plural names your Registry's model
defines (e.g. `endpoints`, `messages`) - they're not literal.

#### 3.2.1. Reading things

A plain `GET` on a Registry, Group, or metadata-only Resource returns its
metadata as JSON. The same applies to a Version of a metadata-only Resource.
Retrieving a Document Resource or one of its Versions returns its
domain-specific document by default, as described in section
[3.2.3](#323-resources-metadata-vs-the-actual-document).

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

Creating a nested entity also creates any missing parent entities when their
required attributes can be populated by the server or defaults. If a required
parent value cannot be supplied that way, the parent must be created explicitly
first; otherwise creation of the nested entity fails with
`required_attribute_missing`.

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
`schema` can have domain-specific content in addition to its
xRegistry metadata (`epoch`, `name`, etc.).

- `GET /schemagroups/sg1/schemas/schema1` → returns the Resource's **document**
  (its raw content) directly in the HTTP body.
- `GET /schemagroups/sg1/schemas/schema1$details` → returns the Resource's
  **metadata** as JSON instead (with the document's metadata such as
  `contenttype`, but not the document body itself).

For `PUT`, `PUT .../schema1` with a raw body sets the document content.
`PUT .../schema1$details` accepts a JSON Resource body and can update both metadata
and document content. The document can be supplied through the `schema`,
`schemabase64`, or `schemaurl` attribute.

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

### 3.4. Where to go next

- [`spec.md`](./spec.md) - the full core specification (concepts, entities,
  capabilities).
- [`http.md`](./http.md) - the full HTTP binding (every API, header, and
  query parameter in detail).
- [`model.md`](./model.md) - the full model specification (every model
  attribute and option).

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
later moved into its own project.

## 5. Value proposition

xRegistry provides a specification to define metadata and extensions for
resources in an abstract model that can be used to centralize and standardize
information about resources in a system. The core specification defines the
basic building blocks for managing metadata about resources and provides
multiple formats to [represent](#7-representations) this information.

The design aims to make discovery, validation, and versioning interoperable
through a consistent metadata structure and API, with extension points for
resource metadata and errors.

xRegistry can be used to represent any type of metadata, as long as it adheres
to the basic model in which a registry consists of groups, which in turn
consists of multiple resources which can have multiple versions defined. This
model is useful for any metadata that is crucial to the operation of a system or
helps facilitate the interaction between systems. The use cases for xRegistry
are therefore very broad. See
[possible use cases](#9-possible-use-cases) for more examples.

In addition to the core specification, xRegistry provides secondary
specifications for [endpoints](../endpoint/spec.md),
[schemas](../schema/spec.md), and [messages](../message/spec.md), that further
build upon the core to provide more domain-specific standardization in the
context of event-driven systems. The following subsections describe benefits of
the common model and API, using event-driven systems as examples.

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
[8.3.1](#831-storage-and-data-source-choices) explains how an xRegistry API can project
resources managed by another registry.

### 5.2. Discovery

Teams need to discover the resources available in a system and find the
metadata and documents that describe them. xRegistry provides a common model
and API for publishing and querying that information across teams and
organizations. Model extensions can add domain-specific attributes and declare
which are required. Human-readable descriptions let developers, data analysts,
and business analysts use the same registry. For example, an event-driven
system can publish information about endpoints and the events they produce or
consume.

### 5.3. Vendor-agnostic

xRegistry defines a common model, document format, and API for describing and
managing resources independently of a particular vendor or product. Clients
can discover a registry's model and use the same operations to query metadata,
retrieve documents, and manage Versions across implementations. Domain-specific
models describe the resources without requiring a different core API for each
domain.

Schema registries are one example. Products such as
[Confluent Schema
Registry](https://docs.confluent.io/platform/current/schema-registry/index.html),
[Azure Event Hubs Schema
Registry](https://learn.microsoft.com/en-us/azure/event-hubs/schema-registry-overview),
[Apicurio Registry](https://www.apicur.io/registry/), and
[AWS Glue Schema
Registry](https://docs.aws.amazon.com/glue/latest/dg/schema-registry.html)
expose different interfaces. An xRegistry API can provide a common view of
resources managed by these systems while the source registries remain
authoritative, as described in
[Storage and data-source choices](#831-storage-and-data-source-choices).

### 5.4. Versioning

Resources and their metadata change as systems evolve. xRegistry can retain
multiple Versions of a Resource, identify a default Version, and let clients
retrieve a particular Version explicitly. These mechanisms apply across
resource types, allowing clients to use a known Version while newer Versions
are introduced.

Compatibility rules depend on the kind of resource. For example, a schema
registry can declare a compatibility strategy and check schema changes against
it. The [Endpoint specification](../endpoint/spec.md) also defines deprecation
metadata and can identify an alternative endpoint. These domain-specific
features build on the common Resource and Version model.

### 5.5. Validation and compatibility

xRegistry models define the attributes and constraints used to validate
registry metadata. For Resource Versions, a model can also enable
[format validation](./model.md#groupsstringresourcesstringvalidateformat) and
[compatibility checking](./model.md#groupsstringresourcesstringvalidatecompatibility).
Format validation checks a Version against the rules identified by its `format`
attribute. Those rules can describe a domain-specific document or the Version's
metadata definitions and values, such as a Message definition. Compatibility
checking evaluates Versions against the Resource's declared compatibility
policy. These checks depend on the model settings and the formats and policies
supported by the implementation.

Schema documents are one example: a registry can check that a stored schema is
valid and that changes satisfy the selected compatibility policy, helping
teams evolve schemas without breaking existing consumers. These checks validate
registry metadata and documents; they do not require xRegistry to validate
application traffic.

### 5.6. Metadata sharing

xRegistry provides a central place to publish shared metadata and documents
that applications can discover and retrieve by reference. The same model and
APIs support sharing across domains, rather than requiring a separate discovery
mechanism for each use case. Payload reduction and code generation are two
examples of how applications can use this shared information.

#### 5.6.1. Payload reduction

Applications can reference a shared document instead of embedding a copy in
every use. For example, an event can carry a URL identifying its payload schema
rather than carrying the schema itself. Consumers can retrieve the schema
through the registry when needed. Where the encoding permits it, a shared
schema can also support compact serialization that omits repeated field names
and other structural information.

#### 5.6.2. Schema-based contract and client generation

The [file and API representations](#7-representations) can both supply versioned
metadata and documents to code generators. For example, teams can generate
data contracts from schemas instead of maintaining shared packages for those
contracts by hand. A schema in a
vendor-agnostic, well-defined format can drive tools that generate
broker-specific consumers or event-store inserts. Generated producers and
consumers reduce the amount of contract code that teams must write and test.
Generated contracts can be created on demand or published alongside a model
version as reusable libraries, allowing consumers to use them without
installing the generator tooling.
Clemens Vasters built a proof-of-concept that shows this approach in
the [Avrotize VS Code Extension](https://github.com/clemensv/avrotize).

### 5.7. Messaging models as a basis for further development

The [Endpoint](../endpoint/spec.md) and [Message](../message/spec.md)
specifications build on the protocol-independent core xRegistry model to
describe messaging resources. These domain-specific models provide a basis
for tools and additional models that describe how messages move between
endpoints across protocols such as MQTT, HTTP, Kafka, and AMQP.

For example, the [Endpoint specification](../endpoint/spec.md#overview) can
correlate message definitions with endpoints. Other tools or models can use
that metadata to describe event flows, although defining those flows is
outside the Endpoint specification's scope. Once those flow descriptions
exist, applications can discover them rather than reconstructing them from
manually maintained documentation or observed runtime behavior.

## 6. Non-Goals

- **Authentication and Authorization:** Rely on established security standards
  depending on the registry representation.

## 7. Representations

An xRegistry can be represented as a JSON file, a static file server, or an API
server. Resources
(user-supplied data) will most often be embedded in the registry, but the
resource metadata might also point to an external location where such data
exists; also see the discussion about [embeddings and
references](#8-embeddings-references-and-federation).

The representations are symmetric so that data can move between them. Choose a
representation based on how the registry will be updated and deployed.

### 7.1. File

A registry can be represented as a single JSON file, with mechanisms available
to split the registry across multiple files.

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

### 7.2. Static File Server

The registry is represented by multiple JSON files, where each one represents a
single entity within the registry, served via a static file server (e.g. S3 or
similar) that follows the folder and file structure of the API server.

This representation allows clients to retrieve individual entities instead of
the entire registry as one JSON document. It can also serve data exported from
an API server.

It requires storage but no continuously running compute. For example, the
[xRegistry specification registry](https://xregistry.io/xreg/) is hosted on
GitHub Pages.

Since the static file server is read-only, adding resources to the registry is
only possible by rebuilding the server and file structure, e.g. via pipelines.
If you want to directly write to the server or need sophisticated searching and
filtering, you might consider using the API server instead. Adding server logic
to the static file server to make up for the features of the API server is
considered an anti-pattern.

### 7.3. API Server

An API server suits registries shared by multiple teams, especially when
resources have distributed ownership and require different authorization
policies.

It allows direct writes and can provide server-side searching, filtering, and
export without requiring users to generate a static directory structure.

You can use the [xRegistry reference server](https://github.com/xregistry/server)
rather than implementing an API server from scratch.

Running the API server requires you to set up a host and a persistence
layer and maintain both. Start with this representation when direct writes,
authorization, or server-side queries are already required.

## 8. Embeddings, References, and Federation

The purpose of a registry is to act as a catalog more than as a container.

xRegistry models allow domain-specific catalog entries to describe different
kinds of resources. You could fairly precisely
catalog a fleet of vehicles using xRegistry, but the vehicles themselves would
quite obviously not exist inside of it.

However, when a model declares a resource to be of the
["document"](spec.md#document-resources-vs-metadata-only-resources) type,
xRegistry can embed content such as schema documents. The following sections
separate document format metadata from the choice to embed, encode, or link the
document.

The model declares document metadata but does not define the document's
internal shape. Implementations may use the `format` attribute to interpret and
validate that shape.

### 8.1. Formats and Content/Media-Types

`format` and the supported values are a convention chosen for this
specification because the IANA "media-types" are not consistently available for
many document types that are in focus. There is additionally a
[contenttype](spec.md#contenttype-attribute) attribute that should be set for
each document, that provides the corresponding media-type. An example for this
is that Apache Avro schema has no official media type, so that the content type
might be `application/json`, but the `format` is `Avro/1.12`.

Some xRegistry implementations, including the
[reference server](https://github.com/xregistry/server), validate well-known
formats such as Apache Avro schema and check compatibility between versions.
The specification does not define those validation implementations.
It defines indicators through which a server reports whether validation is
available and has been applied. Model metadata gives the server the information
needed to validate embedded data.

A registry server can only enforce validation constraints on embedded documents
that are under its own control. If a document is external, meaning that the
resource entry does not embed it but links to it, the document might change at
the external location without the registry knowing.

The [Schema specification](../schema/spec.md#43-schema-formats) requires
`format` for schema Versions, even when an implementation supports only one
format. This keeps the format explicit in exports so that another server,
including one that supports several formats, can import them without ambiguity.

### 8.2. Embeddings and Links

In a serialized registry representation, a document Resource can carry its
document as an [embedded JSON value](spec.md#resource-attribute), a
[base64-encoded value](spec.md#resourcebase64-attribute), or an [external URL
reference](spec.md#resourceurl-attribute). These are serialization choices;
they do not prescribe how the server stores the document.

In JSON, documents that are valid JSON can appear directly in `<RESOURCE>`;
other document formats use `<RESOURCE>base64`. For example, an Avro schema
written as JSON can appear in `schema`, while a Protobuf schema written as text
is base64 encoded in `schemabase64`. The `contenttype` attribute identifies the
document's media type.

You can also refer to the target document through a `<RESOURCE>url` attribute.
The URL can identify an HTTP resource or a file-system location, which allows
documents in an existing registry or public repository to remain in place. The
`format` and `contenttype` information still needs to exist in xRegistry so
that clients can interpret the document before resolving it. The registry does
not resolve the URL or load the content; clients do that. API servers can also
use external links when proxying content from non-xRegistry registries; see
[Storage and data-source choices](#831-storage-and-data-source-choices).

### 8.3. Federation

xRegistry does not define a synchronization API. A client can read data from
several registries using the same xRegistry API. A proxy can present data from
several registries through one xRegistry endpoint. The specification does not
define how to merge conflicting sources, assign precedence, or implement
shadowing. Those behaviors are outside the scope of xRegistry 1.0.

#### 8.3.1. Storage and data-source choices

xRegistry defines the model and the behavior of the registry's representations,
not the storage architecture behind them. An implementation can keep data in
memory, use a database, or load registry documents from files.

An API server can also act as a proxy that presents multiple underlying
registries, including non-xRegistry ones, through a single xRegistry interface.
The [xrproxy](https://github.com/xregistry/xrproxy) project provides reference
implementations of such proxies. The source registry can remain authoritative;
the proxy need not copy its documents into xRegistry storage.

Whatever storage or data sources it uses, the representation it exposes must
conform to its xRegistry model and the applicable specification rules. Clients
do not need to know how the data is stored to use that representation.

#### 8.3.2. Entity identity across registry views

When two registry views intentionally represent the same logical entity using
the same model hierarchy and IDs, the entity has the same `xid` in each view.
An application can resolve that relative path against the registry available in
its environment. For example, an application in a private network can use a
local registry while another application uses a public registry.

When correlating entities this way, an application needs to account for the
scope of each identifier. An entity's `<SINGULAR>id` is unique only within its
parent, and its `xid` is unique only within one Registry. Matching `xid` values
can support correlation, but do not by themselves establish that entities in
different Registries represent the same logical entity. Globally unique entity
identity across Registries is intentionally outside the scope of xRegistry 1.0.

The `self` and `shortself` attributes are URLs through which an entity can be
retrieved. They can differ between registry services that expose the same
logical entity and therefore are not portable identifiers across registries.

## 9. Possible Use Cases

### 9.1. CloudEvents

Since xRegistry emerged from the CloudEvents project and initially was called
"CloudEvents Discovery" the obvious use case is to manage all the CloudEvents of
your event-driven architecture inside xRegistry. The specification supports
"CloudEvents" as a format and allows you to define further restrictions on how your
CloudEvents look, what extensions they use or which fields are required for your
specific use-case even though the original specification marks them as optional.
In addition, the `dataschema` attribute of a CloudEvent can then point to a
xRegistry schema document making this two projects that work hand in hand.
The [CloudEvents Registry specification](../cloudevents/spec.md) describes the
combined model for endpoints, messages, and payload schemas.

### 9.2. Business objects

When defining the schemas of business objects in an enterprise, the
[xRegistry Schema Registry](../schema/spec.md) can be the schema store for these
definitions. One can then reference them in a data
catalogue as well as in OpenAPI and AsyncAPI documents without repeating the
schemas for the actual business objects.

## 10. Design decisions or topics of interest

### 10.1. Resource.ID vs Resource.Version.ID

Resources, like all xRegistry entities, have unique `id` values. Resource
`id`s are often user-friendly values that often have an implied semantic
meaning of the purpose of the underlying Resource document. Also, since they
are static values and as the Resource changes over time (meaning, new Versions
are created), it's important for end-users to have a static URL reference to
the default Version of the Resource.

A Resource's `defaultversionid` selects its default Version. Resource-level
attributes are not default values inherited by the Resource's Versions.

Versions of a Resource, on the other hand, might change quite often and the
`id` isn't meant to convey the purpose of the underlying entity, rather it is
meant to uniquely specify its "version number". As such, the semantics
meaning and usage of the two `id` values are quite different. This means that
there might be times when they are the same value. However, while this is
allowable, it has no influence on any specification defined semantics of the
xRegistry model. As a result, implementations might want to avoid using `id`
values that could appear on a Resource and one of its Versions simply to avoid
potential confusion for their end-users.

### 10.2. Valid Characters

Attribute names appear in JSON objects, HTTP headers, URLs, and generated code.
The specification therefore uses a restricted character set that works across
those contexts. Section [10.8](#108-naming-and-case-sensitivity) explains the
casing rules. Section
[10.9](#109-why-are-group-and-resource-type-names-more-restricted) explains the additional
restrictions on Group and Resource type names.

The specification permits underscores in attribute names, but some proxies,
including nginx with its default configuration, drop HTTP headers containing
underscores. Implementations that expose attributes as headers need to account
for that behavior.

Map keys allow more characters than attribute names because they are normally
stored as strings rather than mapped to named fields in code structures.

### 10.3. Extensions

Extensions should be defined in the model. A model can also define a `*`
extension to allow attributes supplied at runtime. Extension names follow the
[valid character](#102-valid-characters) and
[casing](#108-naming-and-case-sensitivity) rules for all attributes.

#### 10.3.1. Potential extensions

Implementations that track the identity responsible for a change might define
`createdby` and `modifiedby` extensions alongside `createdat` and `modifiedat`.
The core specification does not define them because it does not define
authentication or identity tracking.

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

### 10.5. Detection of Referenced Resources

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

### 10.6. Shared/Referenced Resources

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

### 10.7. Why Epoch?

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

### 10.8. Naming and Case Sensitivity

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
  provide a better user experience.

  Additionally, treating them in a case-insensitive way could lead to
  inconsistencies and frustration for users. If a user purposely used a certain
  casing pattern, but then someone else uses a different pattern for the same
  entity, it is possible that one of those users would end up seeing an
  unexpected casing and could be confused or believe there was an error.

  The specification therefore requires case-sensitive lookup while prohibiting
  IDs that differ only by case within the same parent.

### 10.9. Why are Group and Resource type names more restricted?

Attribute names and key names are limited to 63 characters, so why are some
Group and Resource names limited to less? Because when they appear as part of
attribute names and they can be appended with phrases like `url`, `count`
or `base64`, and they still have to fit within the 63-character limit, and so
we need to take into account the length of those phrases. As a result, Group
type singular names are limited to 61 characters.
Group type plural names and Resource type singular and plural names are
limited to 57 characters.

### 10.10. Choosing unique Group and Resource names

Aside from choosing names that give some descriptive meaning to the purpose
of these entities, care should be taken when choosing names for entities that
might be imported into other Registries. For example, Group names are often
suffixed (or prefixed) with domain (or company) specific words to avoid
name collisions with other similarly named entities. This might be useful
for Resource names too (if they might co-exist under shared Groups), but
normally ensuring uniqueness at the Group level is sufficient.

The same collision guidance applies to model extensions and new APIs; their
names should remain clear of future xRegistry additions.

### 10.11. Are `self` and `shortself` attributes static?

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

### 10.12. Why does an unknown query parameter not generate an error?

People have identified cases where query parameters might be added to request
URLs without the client (or developer) having control to prevent it. It might
be client-side tooling or intermediaries (e.g. proxies) that might modify
the URL - for example to add tracking or end-to-end tracing information.

To avoid these clients not being able to interact with an xRegistry deployment,
the authors chose to have the server ignore unknown query parameters. The
specification says they SHOULD be ignored, not that they MUST be ignored. An
implementation can reject them, but doing so risks interoperability problems.

### 10.13. Updating attributes with `ifvalues`

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

### 10.14. Multi-root ancestor hierarchies

The [`ancestorid` attribute](./spec.md#ancestorid-attribute) builds a Version
hierarchy for compatibility checking when the
[`compatibility` attribute](./spec.md#compatibility-attribute) is set. Some
use cases need multiple roots. Pruning can also create additional roots;
section [10.16](#1016-pruning-versions-with-singleversionroot-enabled)
describes the case in which `singleversionroot` prevents that operation.

To signal that a Version represents a root of a hierarchy, the `ancestorid`
attribute has its value set to the Version's `versionid` attribute. This
makes the ancestor explicit, and the possible ambiguity of using another
value such as `null` which, based on the scenario, could mean "no ancestor" or
"default to the newest".

### 10.15. `singleversionroot` Policy Enforcement

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

### 10.16. Pruning Versions with `singleversionroot` enabled

The [normal pruning rules](model.md#groupsstringresourcesstringmaxversions)
apply when creating a Version would exceed `maxversions` or when that limit is
reduced.
However, if pruning would create multiple roots while `singleversionroot`
is `true`, the server must reject the request.

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

### 10.17. What's the oldest/newest Version of a Resource?

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
sorted by their `versionid` values in descending alphabetical order
(case-insensitive), and the first is the newest Version.

### 10.18. Can `validatecompatibility` and `validateformat` be `true` for file-servers?

`validatecompatibility` and `validateformat` report both policy and validation
state. A file server cannot enforce those policies on write, but it can expose
either attribute as `true` when the published data was validated before
deployment.

For example, an API server can validate data before exporting it to a file
server. Clients can then use either representation without needing to account
for that deployment choice.

### 10.19. Detecting circular references between Versions

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

### 10.20. Optional required fields in requests

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

### 10.21. Deprecation of entities in an xRegistry

The core specification defines a `deprecated` attribute for Groups and under a
Resource's `meta` sub-object. Resource deprecation applies to the whole Resource
rather than to individual Versions. Models that need Version-level deprecation
can define an extension on Versions, preferably using the core attribute's
definition for consistency.

### 10.22. Problematic characters in values

Attribute values can be used outside the scope of the xRegistry specification.
For example, a `name` or ID value might become a file name. The character rules
for values cannot account for every constraint imposed by those external
systems, such as the restriction on colons (`:`) in Windows file names.

Tooling must decide how to handle such cases. It can convert or escape the
value, reject it, or require the user to choose a value that is valid in the
target system. The specification does not prescribe that behavior.

### 10.23. Why do Resources have 3 levels of data?

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

### 10.24. Why isn't `PUT` idempotent?

As stated in the [core](./spec.md) specification, the `PUT` operations are
almost idempotent, per the HTTP specification. For the most part, multiple
similar `PUT` requests will have the same effect as a single one, with the
exception that `epoch` and `modifiedat` will be updated each time. This is
due to the desire to avoid having server implementations perform a "diff" type
of check on all attributes to determine if anything changed, and then only
"bumping" those attributes' values if there was a change. This could be an
expensive or ambiguous check to perform, so it was determined it would be best
to avoid it all together.

### 10.25. Validation edge cases

Sections [5.5](#55-validation-and-compatibility) and
[8.1](#81-formats-and-contentmedia-types) explain the purpose and boundaries of
validation. The following cases cover two less obvious interactions between
validation settings.

#### 10.25.1. Empty format capabilities

If a Resource model sets both `validateformat` and `strictvalidation` to `true`,
but the Registry's `capabilities` declares no `format` values, the server will
reject every non-empty `format` value as unknown.

A lightweight server that performs no validation can therefore expose an
unusable Resource type if its model enables those aspects and clients supply
`format`.

#### 10.25.2. Constraints and `matchversions`

`constraints` and `matchversions` validate only scalar attributes in objects.
They do not apply inside maps, arrays, `ifvalues` clauses, or `*` extensions.
Extending validation into those structures would increase implementation
complexity and make consistent support across servers less likely.

### 10.26. Relative Resource URLs in the File representation

The [File representation](#71-file) can use relative URLs for Resource documents.
This allows a repository to move without rewriting the URLs or duplicating
the documents in the registry file.

**Example:**

```
Repository structure:
    /project-root
        ...
        /registry
            xreg.json
        /schemas
            schema1.json
            schema2.json
        ...
```

For a repository structured as shown above, a schema version in xRegistry
could look like:

```yaml
"schemagroups": {
    "MySchemaGroup": {
        "schemas": {
            "MySchema": {
                "versions": {
                    "1": {
                        "format": "JsonStructure/draft-02",
                        "schemaurl": "../schemas/schema1.json"
                    }
                }
            }
        }
    }
}
```

The specification requires resource URLs to be resolvable which, in the context
of the files of the repository, is possible. When uploading registry content to
a server, ensure that all relative URLs are resolved and that the referenced
documents are included in the upload. Client-side tooling may be able to
assist with this process.
