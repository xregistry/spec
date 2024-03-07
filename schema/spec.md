# Schema Registry Service - Version 0.5-wip

## Abstract

This specification defines a Schema Registry extension to the xRegistry document
format and API [specification](../core/spec.md). A Schema Registry allows for
the storage, management and discovery of schema documents.

## Table of Contents

- [Overview](#overview)
- [Notations and Terminology](#notations-and-terminology)
  - [Notational Conventions](#notational-conventions)
  - [Terminology](#terminology)
- [Schema Registry](#schema-registry)
  - [Schema Groups](#group-schemagroups)
  - [Schemas](#resource-schemas)

## Overview

This specification defines a Schema Registry extension to the xRegistry document
format and API [specification](../core/spec.md).

For easy reference, the JSON serialization of a Schema Registry adheres to
this form:

```yaml
{
  "specversion": "STRING",                         # xRegistry core attributes
  "id": "STRING",
  "name": "STRING", ?
  "epoch": UINTEGER,
  "self": "URL",
  "description": "STRING", ?
  "documentation": "URL", ?
  "labels": { "STRING": "STRING" * }, ?

  "model": { ... }, ?

  "schemagroupsurl": "URL",                        # SchemaGroups collection
  "schemagroupscount": UINTEGER,
  "schemagroups": {
    "ID": {
      "id": "STRING",                              # xRegistry core attributes
      "name": "STRING", ?
      "epoch": UINTEGER,
      "self": "URL",
      "description": "STRING", ?
      "documentation": "URL", ?
      "labels": { "STRING": "STRING" * }, ?
      "origin": "STRING", ?
      "createdby": "STRING", ?
      "createdon": "TIME", ?
      "modifiedby": "STRING", ?
      "modifiedon": "TIME", ?

      "schemasurl": "URL",                         # Schemas collection
      "schemascount": UINTEGER,
      "schemas": {
        "ID": {
          "id": "STRING",                          # xRegistry core attributes
          "name": "STRING", ?
          "epoch": UINTEGER,
          "self": "URL",
          "latestversionid": "STRING",
          "latestversionurl": "URL",
          "description": "STRING", ?
          "documentation": "URL", ?
          "labels": { "STRING": "STRING" * }, ?
          "origin": "STRING", ?
          "createdby": "STRING", ?
          "createdon": "TIME", ?
          "modifiedby": "STRING", ?
          "modifiedon": "TIME", ?

          "format": "STRING",                      # Notice it is mandatory

          "schemaobject": { ... }, ?               # TODO - check this
          "schema": "STRING", ?
          "schemaurl": "URL" ?

          "versionsurl": "URL",
          "versionscount": UINTEGER,
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

For clarity, OPTIONAL attributes (specification defined and extensions) are
OPTIONAL for clients to use, but servers MUST be prepared for them to appear
in incoming requests and MUST support them since "support" simply means
persisting them in the backing datastore. However, as with all attributes, if
accepting the attribute would result in a bad state (such as exceeding a size
limit, or results in a security issue), then the server MAY choose to reject
the request.

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
stored on disk or elsewhere. In self-describing serialization formats like JSON,
XML, BSON, or MessagePack, schemas primarily help with validating whether a
message body conforms with a set of rules defined in the schema and with
generating code that can produce or consume the defined structure. For
schema-dependent serialization formats like Protobuf or Apache Avro, a schema
is needed to decode the structured data from its serialized, binary form.

We use the term **schema** (or schema Resource) in this specification as a
logical grouping of **schema Versions**. A **schema Version** is a concrete
document. The **schema** Resoruce is a semantic umbrella formed around one or
more concrete schema Version documents. The semantic condition for **schema
Versions** to coexist in the same **schema** is that any new schema Version
MUST be backwards compatible with all previous versions of the same **schema**.
Any breaking change MUST result in a new **schema** Resource.

In "semantic Versioning" terms, you can think of a **schema** as a "major
version" and the **schema Versions** as "minor versions".

#### Schema Group

A schema group is a container for schemas that are related to each other in some
application-defined way. This specification does not impose any restrictions on
what schemas can be contained in a schema group.


## Schema Registry

The Schema Registry is a metadata store for organizing schemas and schema
Versions of any kind; it is a document store.

The xRegistry API extension model of the Schema Registry, which is defined in
detail below, is as follows:

```yaml
{
  "schemas": [
    "json-schema/draft-07"
  ],
  "groups": [
    {
      "singular": "schemagroup",
      "plural": "schemagroups",

      "resources": [
        {
          "singular": "schema",
          "plural": "schemas",
          "versions": 0,

          "attributes": {
            "format": {
              "name": "format",
              "type": "string",
              "description": "Schema format identifier for this schema version",
              "clientrequired": true,
              "serverrequired": true
            }
          }
        }
      ]
    }
  ]
}
```

Implementations of this specification MAY include additional extension
attributes, including the `*` attribute of type `any`.

Since the Schema Registry is an application of the xRegistry specification, all
attributes for Groups, Resources, and Resource Version objects are inherited
from there.

### Group: schemagroups

The group (GROUP) name for the Schema Registry is `schemagroups`. The group does
not have any specific extension attributes.

A schema group is a collection of schemas that are related to each other in some
application-defined way. A schema group does not impose any restrictions on the
contained schemas, meaning that a schema group MAY contain schemas of different
formats. Every schema MUST reside inside a schema group.

Example:

The follow abbreviated Schema Registry's contents shows a single schema group
containing 5 schemas.

```yaml
{
  "specversion": 0.5,
  # other xRegsitry top-level attributes excluded for brevity

  "schemagroupsurl": "http://example.com/schemagroups",
  "schemagroupscount": 1,
  "schemagroups": {
    "com.example.schemas": {
      "id": "com.example.schemas",
      # Other xRegistry group-level attributes excluded for brevity

      "schemasurl": "https://example.com/schemagroups/com.example.schemas/schemas",
      "schemascount": 5
    }
  }
}
```

### Resource: schemas

The resources (RESOURCE) collection inside of schema groups is named `schemas`.
The type of the resource is `schema`. Any single `schema` is a container for
one or more `Versions`, which hold the concrete schema documents or schema
document references.

Any new schema Version that is added to a schema definition SHOULD be backwards
compatible with all previous Versions of the schema, meaning that a consumer
using the new schema would be able to understand data encoded using a prior
Version of the schema. If a new Version introduces a breaking change, it SHOULD
be registered as a new schema with a new name.

Implementations of this specification SHOULD use the xRegistry default
algorithm for generating new `id` values and for determining which is the
latest Version. See [Version IDs](../core/spec.md#version-ids) for more
information, but in summary it means:
- `id`s are unsigned integers starting with `1`
- They monotomically increase by `1` with each new Version
- The latest is the Version with the lexically largest `id` value after all
  Version's `id`s have been left-padded with spaces to the same length

When semantic versioning is used in a solution, it is RECOMMENDED to include a
major version identifier in the schema `id`, like `"com.example.event.v1"` or
`"com.example.event.2024-02"`, so that incompatible, but historically related
schemas can be more easily identified by users and developers. The schema
Version `id` then functions as the semantic minor version identifier.

The following extensions are defined for the `schema` object in addition to the
core xRegistry Resource
[attributes](../core/spec.md#attributes-and-extensions):

#### `format`

- Type: String
- Description: Identifies the schema format. In absence of formal media-type
  definitions for several important schema formats, we define a convention here
  to reference schema formats by name and version as `{NAME}/{VERSION}`. This
  specification defines a set of common [schema format names](#schema-formats)
  that MUST be used for the given formats, but applications MAY define
  extensions for other formats on their own.
- Constraints:
  - REQUIRED
  - MUST be a non-empty string
  - MUST follow the naming convention `{NAME}/{VERSION}`, whereby `{NAME}` is
    the name of the schema format and `{VERSION}` is the Version of the schema
    format in the format defined by the schema format itself.
- Examples:
  - `JsonSchema/draft-07`
  - `Protobuf/3`
  - `XSD/1.1`
  - `Avro/1.9`

The following abbreviated example shows three embedded `Protobuf/3` schema
Versions for a schema named `com.example.telemetrydata`:

```yaml
{
  "specversion": 0.5,
  # other xRegsitry top-level attributes excluded for brevity

  "schemagroupsurl": "http://example.com/schemagroups",
  "schemagroupscount": 1,
  "schemagroups": {
    "com.example.telemetry": {
      "id": "com.example.telemetry",
      # other xRegistry group-level attributes excluded for brevity

      "schemasurl": "http://example.com/schemagroups/com.example.telemetry/schemas",
      "schemascount": 1,
      "schemas": {
        "com.example.telemetrydata": {
          "id": "com.example.telemetrydata",
          "latesversionurl": "http://example.com/schemagroups/com.example.telemetry/schemas/com.example.telemetrydata/versions/3",
          "latestversionid": "3",
          "description": "device telemetry event data",
          "format": "Protobuf/3",
          # other xRegistry resource-level attributes excluded for brevity

          "schema": "syntax = \"proto3\"; message Metrics { float metric = 1; string unit = 2; string description = 3; } }"

          "versionsurl": "http://example.com/schemagroups/com.example.telemetry/schemas/com.example.telemetrydata/versions",
          "versionscount": 3,
          "versions": {
            "1": {
              "id": "1",
              "description": "device telemetry event data",
              "format": "Protobuf/3",
              # other xRegistry resource-level attributes excluded for brevity

              "schema": "syntax = \"proto3\"; message Metrics { float metric = 1; } }"
            },
            "2": {
              "id": "2",
              "description": "device telemetry event data",
              "format": "Protobuf/3",
              # other xRegistry resource-level attributes excluded for brevity

              "schema": "syntax = \"proto3\"; message Metrics { float metric = 1; string unit = 2; } }"
            },
            "3": {
              "id": "3",
              "description": "device telemetry event data",
              "format": "Protobuf/3",
              # other xRegistry resource-level attributes excluded for brevity

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

A URI-reference, like
[`schemaurl`](../message/spec.md#schemaurl-message-schema-url) that points
to a JSON Schema document MAY use a JSON pointer expression to deep link into
the schema document to reference a particular type definition. Otherwise the
top-level object definition of the schema is used.

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

A URI-reference, like
[`schemaurl`](../message/spec.md#schemaurl-message-schema-url) that points
to a XSD Schema document MAY use an XPath expression to deep link into the
schema document to reference a particular type definition. Otherwise the root
element definition of the schema is used.

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
schema Resource is a JSON object representing an Avro schema document conformant
with the declared version.

Examples:

- `Avro/1.8.2` is the identifier for the Apache Avro release 1.8.2.
- `Avro/1.11.0` is the identifier for the Apache Avro release 1.11.0

A URI-reference, like
[`schemaurl`](../message/spec.md#schemaurl-message-schema-url) that points
to an Avro Schema document MUST reference an Avro record declaration contained
in the schema document using a URI fragment suffix `[:]{record-name}`. The ':'
character is used as a separator when the URI already contains a fragment.

Examples:

- If the Avro schema document is referenced using the URI
`https://example.com/avro/telemetry.avsc`, the URI fragment `#TelemetryEvent`
references the record declaration of the `TelemetryEvent` record.
- If the Avro schema document is a local Schema Registry reference like
`#/schemagroups/com.example.telemetry/schemas/com.example.telemetrydata`, in the
which the reference is already in the form of a URI fragment, the suffix is
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
[`schemaurl`](../message/spec.md#schemaurl-message-schema-url) that points
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
[CloudEvents Types]: https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/spec.md#type-system
[AMQP 1.0]: https://docs.oasis-open.org/amqp/core/v1.0/os/amqp-core-overview-v1.0-os.html
[AMQP 1.0 Message Format]: http://docs.oasis-open.org/amqp/core/v1.0/os/amqp-core-messaging-v1.0-os.html#section-message-format
[AMQP 1.0 Message Properties]: http://docs.oasis-open.org/amqp/core/v1.0/os/amqp-core-messaging-v1.0-os.html#type-properties
[AMQP 1.0 Application Properties]: http://docs.oasis-open.org/amqp/core/v1.0/os/amqp-core-messaging-v1.0-os.html#type-application-properties
[AMQP 1.0 Message Annotations]: http://docs.oasis-open.org/amqp/core/v1.0/os/amqp-core-messaging-v1.0-os.html#type-message-annotations
[AMQP 1.0 Delivery Annotations]: http://docs.oasis-open.org/amqp/core/v1.0/os/amqp-core-messaging-v1.0-os.html#type-delivery-annotations
[AMQP 1.0 Message Header]: http://docs.oasis-open.org/amqp/core/v1.0/os/amqp-core-messaging-v1.0-os.html#type-header
[AMQP 1.0 Message Footer]: http://docs.oasis-open.org/amqp/core/v1.0/os/amqp-core-messaging-v1.0-os.html#type-footer
[MQTT 5.0]: https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html
[MQTT 3.1.1]: https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/mqtt-v3.1.1.html
[CloudEvents]: https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md
[CloudEvents Subscriptions API]: https://github.com/cloudevents/spec/blob/main/subscriptions/spec.md
[NATS]: https://docs.nats.io/reference/reference-protocols/nats-protocol
[Apache Kafka]: https://kafka.apache.org/protocol
[Apache Kafka producer]: https://kafka.apache.org/31/javadoc/org/apache/kafka/clients/producer/ProducerRecord.html
[Apache Kafka consumer]: https://kafka.apache.org/31/javadoc/org/apache/kafka/clients/consumer/ConsumerRecord.html
[HTTP Message Format]: https://www.rfc-editor.org/rfc/rfc9110#section-6
[RFC6570]: https://www.rfc-editor.org/rfc/rfc6570
[rfc3339]: https://tools.ietf.org/html/rfc3339
