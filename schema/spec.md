# Schema Registry Service - Version 1.0-rc2

## Abstract

This specification defines a Schema Registry extension to the xRegistry
document format and API [specification](../core/spec.md). A Schema Registry
allows for the storage, management and discovery of schema documents.

## Table of Contents

- [Overview](#overview)
- [Notations and Terminology](#notations-and-terminology)
  - [Notational Conventions](#notational-conventions)
  - [Terminology](#terminology)
- [Schema Registry](#schema-registry-model)
  - [Schema Groups](#schema-groups)
  - [Schema Resources](#schema-resources)

## Overview

This specification defines a Schema Registry extension to the xRegistry
document format and API [specification](../core/spec.md).

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

## Notations and Terminology

### Notational Conventions

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

### Terminology

This specification defines the following terms:

#### Schema

A schema, in the sense of this specification, defines the structure of the
body/payload of a serialized message, but also of a structured data element
stored on disk or elsewhere. In self-describing serialization formats like
JSON, XML, BSON, or MessagePack, schemas primarily help with validating
whether a message body conforms with a set of rules defined in the schema and
with generating code that can produce or consume the defined structure. For
schema-dependent serialization formats like Protobuf or Apache Avro, a schema
is needed to decode the structured data from its serialized, binary form.

We use the term **schema** (or schema Resource) in this specification as a
logical grouping of **schema Versions**. A **schema Version** is a concrete
document. The **schema** Resource is a semantic umbrella formed around one or
more concrete schema Version documents. Per the definition of the
[`compatibility`](../core/spec.md#compatibility-attribute) attribute, all
Versions of a single **schema** MUST adhere to the rules defined by the
`compatibility` attribute. Any breaking change MUST result in a new **schema**
Resource being created.

In terms of versioning, you can think of a **schema** as a collection of
versions that are compatible according to the selected `compatibility` mode.
When that compatibility is broken across versions, a completely new **schema**
MUST be created, to indicate the breaking change.

## Schema Registry Model

The formal xRegistry extension model of the Schema Registry
resides in the [model.json](model.json) file.

#### Schema Groups

A schema Group is a container for schemas that are related to each other in
some application-defined way. This specification does not impose any
restrictions on what schemas can be contained in a schema Group.

The Group plural name (`<GROUPS.`) is `schemagroups`, and the Group singular
name (`<GROUP>`) is `schemagroup`.

The Group does not have any specific extension attributes.

A schema Group is a collection of schemas that are related to each other in
some application-defined way. A schema Group does not impose any restrictions
on the contained schemas, meaning that a schema Group MAY contain schemas of
different formats. Every schema Resource MUST reside inside a schema Group.

Example:

The follow abbreviated Schema Registry's contents shows a single schema Group
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

### Schema Resources

The Resource plural name (`<RESOURCES>`) is `schemas`, and the Resource
singular name (`<RESOURCE>`) is `schema`.

Any single `schema` is a container for one or more `Versions`, which hold the
concrete schema documents or schema document references.

All Versions of a schema MUST adhere to the semantic rules of the schema's
`compatibility` attribute. This specification defines "compatibility" for
schemas as follows; version B of a schema is said to be compatible with
version A of a schema if all of the following are true:
- Any document that adheres to the rules specified by schema A also adheres to
  rules specified by schema B.
- Any processing rules defined for schema A also apply for schema B.
- Any processing rules defined for schema B, that are not defined for schema
  A, do not conflict with the processing rules for schema A.

Implementations of this specification MAY choose to support any of the
[`compatibility`](../core/spec.md#compatibility-attribute) values defined in
the core xRegistry specification.

Implementations of this specification SHOULD use the xRegistry default
algorithm for generating new `versionid` values and for determining which is
the latest Version. See [Version IDs](../core/spec.md#version-ids) for more
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

The following extensions are defined for the `schema` Resource in addition to
the core xRegistry Resource
[attributes](../core/spec.md#attributes-and-extensions):

#### `validation`

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

#### `format`

- Type: String
- Description: Identifies the schema format. In absence of formal media-type
  definitions for several important schema formats, we define a convention here
  to reference schema formats by name and version as `<NAME>/<VERSION>`. This
  specification defines a set of common [schema format names](#schema-formats)
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

### Schema Formats

This section defines a set of common schema `format` values that MUST be used
for the given formats, but applications MAY define extensions for other
formats on their own.

#### JSON Schema

The [`format`](#format) identifier for JSON Schema is `JsonSchema`.

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

#### XML Schema

The [`format`](#format) identifier for XML Schema is `XSD`. The
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

#### Apache Avro Schema

The [`format`](#format) identifier for Apache Avro Schema is
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

#### Protobuf Schema

The [`format`](#format) identifier for Protobuf Schema is
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

[JSON Pointer]: https://www.rfc-editor.org/rfc/rfc6901
