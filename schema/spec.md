# Schema Registry Service - Version 1.0-rc2

## Abstract

This specification defines a Schema Registry extension to the xRegistry
document format and API [specification][xRegistry Core]. A Schema Registry
allows for the storage, management and discovery of schema documents.

## Table of Contents

- [Schema Registry Service - Version 1.0-rc2](#schema-registry-service---version-10-rc2)
  - [Abstract](#abstract)
  - [Table of Contents](#table-of-contents)
  - [1. Overview](#1-overview)
    - [1.1. Schemas](#11-schemas)
    - [1.2. Schema References](#12-schema-references)
    - [1.3. Versioning](#13-versioning)
    - [1.4. Document Store](#14-document-store)
  - [2. Notations and Terminology](#2-notations-and-terminology)
    - [2.1. Notational Conventions](#21-notational-conventions)
    - [2.2. Terminology](#22-terminology)
      - [2.2.1. Schema](#221-schema)
    - [2.3. Schema Group](#23-schema-group)
  - [3. Schema Registry Model](#3-schema-registry-model)
  - [4. Schema Registry](#4-schema-registry)
    - [4.1. Schema Groups](#41-schema-groups)
    - [4.2. Schema Resources](#42-schema-resources)
      - [4.2.1. `validation`](#421-validation)
      - [4.2.2. `format`](#422-format)
    - [4.3. Schema Formats](#43-schema-formats)
      - [4.3.1. JSON Schema](#431-json-schema)
      - [4.3.2. XML Schema](#432-xml-schema)
      - [4.3.3. Apache Avro Schema](#433-apache-avro-schema)
      - [4.3.4. Protobuf Schema](#434-protobuf-schema)
    - [5. Security Considerations](#5-security-considerations)

## 1. Overview

A schema registry provides a respository for managing serialization and
validation and data type definitions schemas as they are commonly used in
distributed systems. Common schema formats include JSON Schema, JSON
Structure, Apache Avro Schema, Google Protobuf Schema, and XML Schema.

### 1.1. Schemas

Schema registries are generally used to share such schemas amongst multiple
parties.

When schemas are used to drive the serialization and encoding of data, like in
the cases of Apache Avro or Google Protobuf, the deserialization of structured
data from its encoded form requires the schema to be available to the
deserializer. The compactness of these serialization formats is achieved by
externalizing type information into a schema document. The registry allows for a
publisher of data to publish the schema document and pass a reference to it, and
for a consumer of data to retrieve the schema document and use it to decode the
data.

Formats like XML and JSON do not require a schema to decode the data, but
schemas are still very useful to establish a common understanding of the data
structures that are exchanged, provide a foundation for code generation, allow
for validation of the data, and provide an anchor for documentation and semantic
information, like scientific units for numeric values, that goes beyond simple
labels and data types. Generally, it is a best practice for data structures that
are exchanged in a distributed systems ought to be described by a schema, even
if the data serialization model does not require one.

### 1.2. Schema References

In the [CloudEvents][CloudEvents dataschema] specification, the `dataschema`
attribute holds a URI and is specifically thought to reference a schema document
residing in a registry. For example, a CloudEvent with a `dataschema` attribute
pointing to a schema version in a schema registry might look like this, using
the schema version's [`self`][xRegistry self] URL as the value of the `dataschema` attribute:

```json
{
    "specversion": "1.0",
    "id": "1234-5678-9012",
    "type": "com.example.event",
    "source": "https://example.com/source",
    "dataschema": "https://example.com/registry/schemagroups/com.example.schemas/schemas/com.example.event/versions/1.0",
    "datacontenttype": "application/vnd.google.protobuf",
    "data_base64": "...base64-encoded-data..."
}
```

Since this URL might be a bit long, the xRegistry core specification allows for
an implementation to provide an alternative, shorter, self-referencing URL that
points to the same schema version, via the [`shortself`][xRegistry shortself]
attribute. The specification is not prescriptive about the format of the shorter
URL, but it might follow common URL-shorneter practices. With that, the above
example might look like this:

```json
{
    "specversion": "1.0",
    "id": "1234-5678-9012",
    "type": "com.example.event",
    "source": "https://example.com/source",
    "dataschema": "https://example.com/$267shU79S",
    "datacontenttype": "application/vnd.google.protobuf",
    "data_base64": "...base64-encoded-data..."
}
```

### 1.3. Versioning

When schemas are used in a system, they typically evolve over time. Data
structures are extended or modified, with parts added or deprecated or even
removed. Some of these changes are compatible with existing data, while others
are not.

Serialization generally occurs based on a specific schema version that the data
publisher uses. Multiple versions of publishers may exist in the same system,
using different schema versions, which is a common occurrence in systems that
perform live updates. Once data has been published, data serialized based on
several different versions may exist in a system, in queues, in databases, or in
files.

The schema registry therefore allows managing multiple versions of schemas,
declare their lineage, and state the compatibility policy. The compatibility
policy is used to determine whether a schema change is compatible with existing
data, and MAY be enforced by implementations of the schema registry. For this,
this specification leans on the [xRegistry Core][xRegistry Core] specification
that already defines these versioning mechanisms for any kind of resource.

### 1.4. Document Store

The schema registry is a document store and therefore also has the
[`hasdocument`][xRegistry hasdocument] attribute defined in the xRegistry Core
attribute (implicitly) defined as `true` for the `schema` Resource.

What this means is that the schema registry immediately yields a document with
the stored content-type when the a client issues a GET request to the
[`self`][xRegistry self] URL of a schema Version. The associated metadata is
returned in the HTTP headers. The [default version][xRegistry default-version]
of the schema Version is returned when the client issues a GET request to the
[`self`][xRegistry self] URL of the `schema` Resource.

This allows to provide external parties with a link that they can use without
needing to know any details about xRegistry.

Storing a new schema is similarly straightforward for clients that do not know
xRegistry specifics, by simply using a POST against [`self`][xRegistry self] URL
of the `schema` Resource in the simplest case.

To access the metadata of the `schema` or the schema version as a JSON document,
the client can append a `$details`suffix to the URL, like
`https://example.com/schemagroups/com.example.schemas/schemas/com.example.event/versions/1.0$details`
or
`https://example.com/schemagroups/com.example.schemas/schemas/com.example.event$details`.

Beyopnd this, the [xRegistry Core][xRegistry Core] specification provides rich
filtering and export/import capabilities, which can be used to retrieve schema
documents in bulk, or to export/import schemas and schema versions in a
structured way. The [xRegistry pagination][xRegistry pagination] mechanism can be used to
retrieve large sets of schemas or schema versions in a paginated manner.

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
However, as with all attributes, if accepting the attribute would result in a
bad state (such as exceeding a size limit, or results in a security issue),
then the server MAY choose to reject the request.

In the pseudo JSON format snippets `?` means the preceding attribute is
OPTIONAL, `*` means the preceding attribute MAY appear zero or more times,
and `+` means the preceding attribute MUST appear at least once. The presence
of the `#` character means the remaining portion of the line is a comment.
Whitespace characters in the JSON snippets are used for readability and are
not normative.

### 2.2. Terminology

This specification defines the following terms:

#### 2.2.1. Schema

We use the term **schema** (or schema Resource) in this specification as a
logical grouping of **schema Versions**. A **schema Version** is a concrete
document. The **schema** Resource is a semantic umbrella formed around one or
more concrete schema Version documents. Per the definition of the
[`compatibility`][xRegistry compatibility] attribute, all Versions of a single
**schema** MUST adhere to the rules defined by the `compatibility` attribute.
Any breaking change MUST result in a new **schema** Resource being created.

In terms of versioning, you can think of a **schema** as a collection of
versions that are compatible according to the selected `compatibility` mode.
When that compatibility is broken across versions, a completely new **schema**
MUST be created, to indicate the breaking change.

### 2.3. Schema Group

A Schema Group is a container for schemas that are related to each other in
some application-defined way. This specification does not impose any
restrictions on what schemas can be contained in a Schema Group.

## 3. Schema Registry Model

The authoritative xRegistry extension model of the Schema Registry resides in
the [model.json](model.json) file.

For easy reference, the JSON serialization of a Schema Registry adheres to
this form:

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

  "schemagroupsurl": "<URL>",                      # SchemaGroups collection
  "schemagroupscount": <UINTEGER>,
  "schemagroups": {
    "KEY": {                                       # schemagroupid
      "schemagroupid": "<STRING>",                 # xRegistry core attributes
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

      "schemasurl": "<URL>",                       # Schemas collection
      "schemascount": <UINTEGER>,
      "schemas": {
        "KEY": {                                   # schemaid
          "schemaid": "<STRING>",                  # xRegistry core attributes
          "versionid": "<STRING>",
          "self": "<URL>",
          "xid": "<XID>",

          #  Start of default Version's attributes
          "epoch": <UINTEGER>,
          "name": "<STRING>", ?                    # Version level attrs
          "description": "<STRING>", ?
          "documentation": "<URL>", ?
          "labels": { "<STRING>": "<STRING>" * }, ?
          "createdat": "<TIMESTAMP>",
          "modifiedat": "<TIMESTAMP>",
          "ancestor": "<STRING>",

          "format": "<STRING>", ?                  # schema extension attr

          "schemaurl": "<URL>", ?
          "schema": <ANY> ?
          "schemabase64": "<STRING>", ?
          #  End of default Version's attributes

          "metaurl": "<URL>",                      # Resource level attrs
          "meta": {
            ... core spec metadata attributes ...
            "validation": <BOOLEAN> ?              # schema extension attr
          }, ?

          "versionsurl": "<URL>",
          "versionscount": <UINTEGER>,
          "versions": { ... } ?
        } *
      } ?
    } *
  } ?
}
```

## 4. Schema Registry

The Schema Registry is a metadata store for organizing schemas and schema
Versions of any kind; it is a document store.

Implementations of this specification MAY include additional extension
attributes, including the `*` attribute of type `any`.

Since the Schema Registry is an application of the xRegistry specification, all
attributes for Groups, Resources, and Resource Version objects are inherited
from there.

### 4.1. Schema Groups

The Group (`<GROUP>`) name for the Schema Registry is `schemagroups`. The
Schema Group does not have any specific extension attributes.

A schema group is a collection of schemas that are related to each other in
some application-defined way. A Schema Group does not impose any restrictions
on the contained schemas, meaning that a Schema Group MAY contain schemas of
different formats.

Every schema MUST reside inside a Schema Group.

Example:

The follow abbreviated Schema Registry's contents shows a single Schema Group
containing 5 schemas.

```yaml
{
  "specversion": 1.0-rc2,
  # other xRegistry top-level attributes excluded for brevity

  "schemagroupsurl": "http://example.com/schemagroups",
  "schemagroupscount": 1,
  "schemagroups": {
    "com.example.schemas": {
      "schemagroupid": "com.example.schemas",
      # Other xRegistry Group-level attributes excluded for brevity

      "schemasurl": "https://example.com/schemagroups/com.example.schemas/schemas",
      "schemascount": 5
    }
  }
}
```

### 4.2. Schema Resources

The Resources (`<RESOURCE>`) collection inside of Schema Groups is named
`schemas`. The type of the Resource is `schema`. Any single `schema` is a
container for one or more `versions`, which hold the concrete schema
documents or schema document references.

All Versions of a Schema MUST adhere to the semantic rules of the schema's
[`compatibility`][xRegistry compatibility] attribute.

This specification defines "compatibility" for schemas as follows; version B of
a schema is said to be compatible with version A of a schema if all of the
following are true:

- Any document that adheres to the rules specified by schema A also adheres to
  rules specified by schema B.
- Any processing rules defined for schema A also apply for schema B.
- Any processing rules defined for schema B, that are not defined for schema
  A, do not conflict with the processing rules for schema A.

Implementations of this specification MAY choose to support any of the
[`compatibility`][xRegistry compatibility] values defined in the core xRegistry
specification.

Implementations of this specification SHOULD use the xRegistry default
algorithm for generating new `versionid` values and for determining which is
the latest Version. See [Version IDs][xRegistry version-ids] for more
information, but in summary it means:

- `versionid`s are unsigned integers starting with `1`
- They monotonically increase by `1` with each new Version
- The latest is the Version with the lexically largest `versionid` value after
  all `versionid`s have been left-padded with spaces to the same length

When semantic versioning is used in a solution, it is RECOMMENDED to include a
major version identifier in the `schemaid`, like `"com.example.event.v1"` or
`"com.example.event.2024-02"`, so that incompatible, but historically related
schemas can be more easily identified by users and developers. The schema
`versionid` then functions as the semantic minor version identifier.

Version lineage is defined by the [`ancestor`][xRegistry ancestor] attribute,
which is a `versionid` of the Version that this Version is based on. The `ancestor`
attribute permits multiple version branches to exist, and allows for
implementations to determine the Version lineage. See the
[`ancestor`][xRegistry ancestor] attribute in the core xRegistry specification
for more information.

The following extensions are defined for the `schema` Resource in addition to
the core xRegistry Resource [attributes][xRegistry attributes-and-extensions]:

#### 4.2.1. `validation`

- Type: Boolean
- Description: Indicates whether or not the server will validate the Resource's
  document(s) against the specified `format` attribute. A value of `true`
  indicates that the server MUST reject any request that would cause any
  Version of this Resource to be invalid per the rules as defined by the
  `format` specification. Note, this includes a request to set this attribute
  to `true`. This means that before validation can be enabled, all existing
  Versions of the Resource MUST be compliant.

  A value of `false` indicates that the server MUST NOT do any validation.

  If `format` is not specified, or if the value is not known by the server
  (but is an allowable value), then the server MUST NOT perform any validation.
- Constraints:
  - OPTIONAL.
  - When not specified, the default value MUST be `false`.

#### 4.2.2. `format`

- Type: String
- Description: Identifies the schema format. In absence of formal media-type
  definitions for several important schema formats, we define a convention here
  to reference schema formats by name and version as `<NAME>/<VERSION>`. This
  specification defines a set of common [schema format names](#43-schema-formats)
  that MUST be used for the given formats, but applications MAY define
  extensions for other formats on their own.

  For many schema registry use cases this attribute is important for schema
  validation purposes, and as such implementations can choose to modify the
  model to make this attribute mandatory.

  It is RECOMMENDED that the same schema format `<NAME>` be used for all
  Versions of a schema Resource.

  Managers of the xRegistry instance can set a default value for this
  attribute, making it a REQUIRED attribute.
- Constraints:
  - OPTIONAL.
  - If present, MUST be a non-empty case-insensitive string.
  - MUST follow the naming convention `<NAME>/<VERSION>`, whereby `<NAME>` is
    the name of the schema format and `<VERSION>` is the Version of the schema
    format in the format defined by the schema format itself.
  - MUST be present if the `compatibility` attribute is set to a value other
    than `None` and when the `compatibilityauthority` attribute is set to
    `server`, to enable validation of the schema document.
- Examples:
  - `JsonSchema/draft-07`
  - `Protobuf/3`
  - `XSD/1.1`
  - `Avro/1.9`

The following abbreviated example shows three embedded `Protobuf/3` schema
Versions for a schema named `com.example.telemetrydata`:

```yaml
{
  "specversion": 1.0-rc2,
  # other xRegistry top-level attributes excluded for brevity

  "schemagroupsurl": "http://example.com/schemagroups",
  "schemagroupscount": 1,
  "schemagroups": {
    "com.example.telemetry": {
      "schemagroupid": "com.example.telemetry",
      # other xRegistry group-level attributes excluded for brevity

      "schemasurl": "http://example.com/schemagroups/com.example.telemetry/schemas",
      "schemascount": 1,
      "schemas": {
        "com.example.telemetrydata": {
          "schemaid": "com.example.telemetrydata",
          "versionid": "3",
          "isdefault": true,
          "description": "device telemetry event data",
          "ancestor": "2",
          "format": "Protobuf/3",
          # other xRegistry default Version attributes excluded for brevity

          "schema": "syntax = \"proto3\"; message Metrics { float metric = 1; string unit = 2; string description = 3; } }",

          "metaurl": "http://example.com/schemagroups/com.example.telemetry/schemas/com.example.telemetrydata/meta",
          "versionsurl": "http://example.com/schemagroups/com.example.telemetry/schemas/com.example.telemetrydata/versions",
          "versionscount": 3,
          "versions": {
            "1": {
              "schemaid": "com.example.telemetrydata",
              "versionid": "1",
              "isdefault": false,
              "description": "device telemetry event data",
              "ancestor": "1",
              "format": "Protobuf/3",
              # other xRegistry Version-level attributes excluded for brevity

              "schema": "syntax = \"proto3\"; message Metrics { float metric = 1; } }"
            },
            "2": {
              "schemaid": "com.example.telemetrydata",
              "versionid": "2",
              "isdefault": false,
              "description": "device telemetry event data",
              "ancestor": "1",
              "format": "Protobuf/3",
              # other xRegistry Version-level attributes excluded for brevity

              "schema": "syntax = \"proto3\"; message Metrics { float metric = 1; string unit = 2; } }"
            },
            "3": {
              "schemaid": "com.example.telemetrydata",
              "versionid": "3",
              "isdefault": true,
              "description": "device telemetry event data",
              "ancestor": "2",
              "format": "Protobuf/3",
              # other xRegistry Version-level attributes excluded for brevity

              "schema": "syntax = \"proto3\"; message Metrics { float metric = 1; string unit = 2; string description = 3; } }"
            }
          }
        }
      }
    }
  }
}
```

### 4.3. Schema Formats

This section defines a set of common schema `format` values that MUST be used
for the given formats, but applications MAY define extensions for other
formats on their own.

#### 4.3.1. JSON Schema

The [`format`](#422-format) identifier for JSON Schema is `JsonSchema`.

When the `format` attribute is set to `JsonSchema`, the `schema` attribute of
the schema Resource is a JSON object representing a JSON Schema document
conformant with the declared version.

When a URI-reference, like [`schemauri`](../message/spec.md#dataschemauri),
points to a JSON Schema document it MAY use a [JSON pointer][JSON pointer]
expression to deep link into the schema document to reference a particular
type definition. Otherwise the top-level object definition of the schema is
used.

The version of the JSON Schema format is the version of the JSON
Schema specification that is used to define the schema. The version of the JSON
Schema specification is defined in the `$schema` attribute of the schema
document.

The identifiers for the following JSON Schema versions

- Draft 07: `http://json-schema.org/draft-07/schema`
- Draft 2019-09: `https://json-schema.org/draft/2019-09/schema`
- Draft 2020-12: `https://json-schema.org/draft/2020-12/schema`

are defined as follows:

- `JsonSchema/draft-07`
- `JsonSchema/draft/2019-09`
- `JsonSchema/draft/2020-12`

which follows the exact convention as defined for JSON schema and expecting an
eventually released version 1.0 of the JSON Schema specification using a plain
version number.

#### 4.3.2. XML Schema

The [`format`](#422-format) identifier for XML Schema is `XSD`. The
version of the XML Schema format is the version of the W3C XML Schema
specification that is used to define the schema.

When the `format` attribute is set to `XSD`, the `schema` attribute of
schema Resource is a string containing an XML Schema document conformant with
the declared version.

When a URI-reference, like [`schemauri`](../message/spec.md#dataschemauri),
points to a JSON Schema document it MAY use an XPath
expression to deep link into the schema document to reference a particular
type definition. Otherwise the top-level object definition of the schema is
used.

The identifiers for the following XML Schema versions:

- 1.0: `https://www.w3.org/TR/xmlschema-1/`
- 1.1: `https://www.w3.org/TR/xmlschema11-1/`

are defined as follows:

- `XSD/1.0`
- `XSD/1.1`

#### 4.3.3. Apache Avro Schema

The [`format`](#422-format) identifier for Apache Avro Schema is
`Avro`. The version of the Apache Avro Schema format is the version of the
Apache Avro Schema release that is used to define the schema.

When the `format` attribute is set to `Avro`, the `schema` attribute of the
schema Resource is a JSON object representing an Avro schema document
conformant with the declared version.

Examples:

- `Avro/1.8.2` is the identifier for the Apache Avro release 1.8.2.
- `Avro/1.11.0` is the identifier for the Apache Avro release 1.11.0

When a URI-reference, like [`schemauri`](../message/spec.md#dataschemauri),
points to a JSON Schema document it MAY use a URI fragment suffix
`[:]{record-name}` to deep link into the schema document to reference a
particular type definition. Otherwise the top-level object definition of the
schema is used. The ':' character is used as a separator when the URI already
contains a fragment.

Examples:

- If the Avro schema document is referenced using the URI
`https://example.com/avro/telemetry.avsc#TelemetryEvent`, the URI fragment
`#TelemetryEvent` references the record declaration of the `TelemetryEvent`
record.
- If the Avro schema document is a local Schema Registry reference like
`#/schemagroups/com.example.telemetry/schemas/com.example.telemetrydata`, in
the which the reference is already in the form of a URI fragment, the suffix is
appended separated with a colon, for instance
`.../com.example.telemetrydata:TelemetryEvent`.

#### 4.3.4. Protobuf Schema

The [`format`](#422-format) identifier for Protobuf Schema is
`Protobuf`. The version of the Protobuf Schema format is the version of the
Protobuf syntax that is used to define the schema.

When the `format` attribute is set to `Protobuf`, the `schema` attribute of the
schema Resource is a string containing a Protobuf schema document conformant
with the declared version.

- `Protobuf/3` is the identifier for the Protobuf syntax version 3.
- `Protobuf/2` is the identifier for the Protobuf syntax version 2.

A URI-reference, like
[`schemauri`](../message/spec.md#dataschemauri that points
to an Protobuf Schema document MUST reference an Protobuf `message` declaration
contained in the schema document using a URI fragment suffix
`[:]{message-name}`. The ':' character is used as a separator when the URI
already contains a fragment.

Examples:

- If the Protobuf schema document is referenced using the URI
  `https://example.com/protobuf/telemetry.proto`, the URI fragment
  `#TelemetryEvent` references the message declaration of the `TelemetryEvent`
  message.
- If the Protobuf schema document is a local Schema Registry reference like
  `#/schemagroups/com.example.telemetry/schemas/com.example.telemetrydata`, in
  the which the reference is already in the form of a URI fragment, the suffix
  is appended separated with a colon, for instance
  `.../com.example.telemetrydata:TelemetryEvent`.

### 5. Security Considerations

Like [xRegistry Core][xRegistry Core] specification, this specification does not
explicitly address authentication or authorization levels of users, nor how to
securely protect the APIs.

It is expected that any implementation of this specification will use
authentication and authorization mechanisms that are appropriate for the
application domain and the deployment environment. This may include, but is not
limited to, OAuth 2.0, OpenID Connect, API keys, or other mechanisms
appropriate for the use case.

For authorization, the `schemagroup` concept provides a natural authorization
boundary, where users can be granted access to specific schema groups, and
therefore to the schemas contained within those groups. The `schema` Resource
itself can be used to further restrict access to specific schema Versions
within a schema, allowing for fine-grained access control.

---

[JSON Pointer]: https://www.rfc-editor.org/rfc/rfc6901
[CloudEvents dataschema]: https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md#dataschema
[xRegistry Core]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html
[xRegistry self]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#self-attribute
[xRegistry shortself]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#shortself-attribute
[xRegistry compatibility]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#compatibility-attribute
[xRegistry version-ids]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#version-ids
[xRegistry attributes-and-extensions]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#attributes-and-extensions
[xRegistry ancestor]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#ancestor-attribute
[xRegistry hasdocument]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#--model-groupsstringresourcesstringhasdocument
[xRegistry default-version]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#registry-design
[xRegistry pagination]: https://xregistry.io/xreg/xregistryspecs/pagination-v1/docs/spec.html
