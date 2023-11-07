# Schema Registry Service - Version 0.5-wip

## Abstract

This specification defines a schema registry extension to the xRegistry document
format and API [specification](../core/spec.md).

## Table of Contents

- [Overview](#overview)
- [Notations and Terminology](#notations-and-terminology)
  - [Notational Conventions](#notational-conventions)
  - [Terminology](#terminology)
- [Schema Registry](#schema-registry)
  - [Schema Groups](#group-schemagroups)
  - [Schemas](#resource-schemas)

## Overview

This specification defines a schema registry extension to the xRegistry document
format and API [specification](../core/spec.md).

## Notations and Terminology

### Notational Conventions

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD",
"SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be
interpreted as described in [RFC 2119](https://tools.ietf.org/html/rfc2119).

For clarity, when a feature is marked as "OPTIONAL" this means that it is
OPTIONAL for both the sender and receiver of a message to support that
feature. In other words, a sender can choose to include that feature in a
message if it wants, and a receiver can choose to support that feature if it
wants. A receiver that does not support that feature is free to take any
action it wishes, including no action or generating an error, as long as
doing so does not violate other requirements defined by this specification.
However, the RECOMMENDED action is to ignore it. The sender SHOULD be prepared
for the situation where a receiver ignores that feature. An
Intermediary SHOULD forward OPTIONAL attributes.

In the pseudo JSON format snippets `?` means the preceding attribute is
OPTIONAL, `*` means the preceding attribute MAY appear zero or more times,
and `+` means the preceding attribute MUST appear at least once.

### Terminology

This specification defines the following terms:

#### Schema

A schema in the sense of this specification defines the structure of the
body/payload of a serialized message, but also of a structured data element
stored on disk or elsewhere. In self-describing serialization formats like JSON,
XML, BSON, or MessagePack, schemas primarily help with validating whether a
message body conforms with a set of rules defined in the schema and with
generating code that can produce or consume the defined structure. For
schema-dependent serialization formats like Protobuf or Apache Avro, a schema 
is needed to decode the structured data from its serialized, binary form.

We use the term **schema** in this specification as a logical grouping of
**schema versions**. A **schema version** is a concrete document. The **schema**
is a semantic umbrella formed around one or more concrete schema version
documents. The semantic condition for **schema versions** to coexist in the same 
**schema** is that any new schema version is backwards compatible with all previous
versions of the same **schema**. Any breaking change forms a new **schema**.

In "semantic versioning" terms, you can think of a **schema** as a "major
version" and the **schema versions** as "minor versions". 

#### Schema Group

A schema group is a container for schemas that are related to each other in some
application-defined way. This specification does not impose any restrictions on
what schemas can be contained in a schema group.


## Schema Registry

The schema registry is a metadata store for organizing schemas and schema
versions of any kind; it is a document store.

The Registry API extension model of the Schema Registry, which is defined in
detail below, is as follows:

``` JSON
{
  "schemas": ["json-schema/draft-07"],
  "groups": [
    {
      "singular": "schemaGroup",
      "plural": "schemaGroups",
      "resources": [
        {
          "singular": "schema",
          "plural": "schemas",
          "versions": 0,
          "attributes" : {
            "format": {
              "description": "Schema format identifier for this schema version.",
              "type": "STRING",
              "required": true
            },
            "schemaobject": {
              "description": "Inlined schema document object",
              "type": "OBJECT",
              "required": false
            },
            "schema": {
              "description": "Inlined schema document string",
              "type": "STRING",
              "required": false
            },
            "schemaurl":{
              "description": "Inlined schema document string",
              "type": "URL",
              "required": false
            }
          }
        }
      ]
    }
  ]
}
```

Since the schema registry is an application of the xRegistry specification, all
attributes for groups, resources, and resource version objects are inherited
from there.

### Group: schemaGroups

The group (GROUP) name for the Schema Registry is `schemaGroups`. The group does
not have any specific extension attributes.

A schema group is a collection of schemas that are related to each other in some
application-defined way. A schema group does not impose any restrictions on the
contained schemas, meaning that a schema group can contain schemas of different
formats. Every schema MUST reside inside a schema group.

Example:

``` meta
{
  "schemaGroupsUrl": "http://example.com/schemagroups",
  "schemaGroupsCount": 1,
  "schemaGroups": {
    "com.example.schemas": {
      "id": "com.example.schemas",
      "schemasUrl": "https://example.com/schemagroups/com.example.schemas/schemas",
      "schemasCount": 5,
      "schemas": {
        ...
      }
    }
  }
}
```

### Resource: schemas

The resources (RESOURCE) collection inside of schema groups is named `schemas`.
The type of the resource is `schema`. Any single `schema` is a container for
one or more `versions`, which hold the concrete schema documents or schema
document references.

Any new schema version that is added to a schema definition MUST be backwards
compatible with all previous versions of the schema, meaning that a consumer
using the new schema MUST be able to understand data encoded using a prior
version of the schema. If a new version introduces a breaking change, it MUST be
registered as a new schema with a new name.

When semantic versioning is used in a solution, it is RECOMMENDED to include a
major version identifier in the schema `id`, like `"com.example.event.v1"` or
`"com.example.event.2024-02"`, so that incompatible, but historically related
schemas can be more easily identified by users and developers. The schema
version identifier then functions as the semantic minor version identifier.

When you retrieve a schema without qualifying the version, you will get the
latest version of the schema, see [retrieving a
resource](../core/spec.md#retrieving-a-resource). The latest version is the
lexically greatest version number, whereby all version ids MUST be left-padded
with spaces to the same length before being compared.

The following extension is defined for the `schema` object in addition to the
basic [attributes](../core/spec.md#attributes-and-extensions):

#### `format` (Schema format)

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
    the name of the schema format and `{VERSION}` is the version of the schema
    format in the format defined by the schema format itself.
- Examples:
  - `JsonSchema/draft-07`
  - `Protobuf/3`
  - `XSD/1.1`
  - `Avro/1.9`

### Resource Version: schemaversion

The `VERSION` object of the `schema` resource is of type `schemaversion`. The
[`format`](#format-schema-format) extension attribute of `schema` MAY be
repeated in `schemaversion` for clarity, but MUST be identical.
`schemaversion` has the following extension attributes.

#### `schemaobject`

- Type: Object
- Description: Embedded schema object. The format of the schema is defined by
  the `format` attribute.
- Constraints:
  - Mutually exclusive with `schemaurl` and `schema`. One of the three
    attributes MUST be present.
  - Schemas MAY be embedded as schema objects if and only if the schema
    definition language is a self-describing object graph consisting of arrays
    and key-value maps. Examples for this are JSON Schema and Apache Avro. Not
    conformant is XML Schema that leans on a combination of elements and
    attributes that do not translate well into such object graphs. Also not
    conformant is Protobuf schema, which leans on a custom interface definition
    language.

#### `schema`

- Type: String
- Description: Embedded schema string. The format and encoding of the schema is
  defined by the `format` attribute.
- Constraints:
  - Mutually exclusive with `schemaurl` and `schemaobject`. One of the three
    MUST be present.
  - Schema strings MAY be embedded if and only if the schema is expressible as a
    Unicode string. XML Schema and Protobuf schema MUST be embedded in this way
    if not expressed as schema document reference.

#### `schemaurl`

- Type: URI
- Description: Reference to a schema document external to the registry.
- Constraints:
  - Mutually exclusive with `schema` and `schemaobject`. One of the two MUST be present.
  - Cross-references to a schema document within the same registry MUST NOT be
    used.
- Remarks: 
  - The `schemaurl` MAY be a well-known identifier that is readily understood by
    all registry users and resolves to a common type definition or an item in
    some private store or cache, rather than a networked document location. In
    such cases, it is RECOMMENDED for the identifier to be a uniform resource
    name (URN). With XML, it is common practice to reference schema documents
    abstractly using URIs that use the `http` scheme, but do not actually point
    to a networked resource. This practice is NOT RECOMMENDED here.


The following example shows three embedded `Protobuf/3` schema versions for a
schema named `com.example.telemetrydata`:

``` JSON
{
  "schemaGroupsUrl": "...",
  "schemaGroupsCount": 1,
  "schemaGroups": {
    "com.example.telemetry": {
      "id": "com.example.telemetry",

      "schemasUrl": "...",
      "schemasCount": 1,
      "schemas": {
        "com.example.telemetrydata": {
          "id": "com.example.telemetrydata",
          "description": "device telemetry event data",
          "format": "Protobuf/3",
          "versionsUrl": "...",
          "versionsCount": 3,
          "versions": {
            "1.0": {
              "id": "1.0",
              "schema": "syntax = \"proto3\"; message Metrics { float metric = 1; } }"
            },
            "2.0": {
              "id": "2.0",
              "schema": "syntax = \"proto3\"; message Metrics { float metric = 1; string unit = 2; } }"
            },
            "3.0": {
              "id": "3.0",
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

This section defines a set of common schema formats that MUST be used for the
given formats, but applications MAY define extensions for other formats on their
own.

#### JSON Schema

The [`format`](#format-schema-format) identifier for JSON Schema is
`JsonSchema`.

When the `format` attribute is set to `JsonSchema`, the `schema` attribute of
the `schemaversion` is a JSON object representing a JSON Schema document
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

The [`format`](#format-schema-format) identifier for XML Schema is `XSD`. The
version of the XML Schema format is the version of the W3C XML Schema
specification that is used to define the schema.

When the `format` attribute is set to `XSD`, the `schema` attribute of
`schemaversion` is a string containing an XML Schema document conformant with
the declared version.

A URI-reference, like
[`schemaurl`](../message/spec.md#schemaurl-message-schema-url) that points
to a XSD Schema document MAY use an XPath expression to deep link into the
schema document to reference a particular type definition. Otherwise the root
element definition of the schema is used.

The identifiers for the following XML Schema versions

- 1.0: `https://www.w3.org/TR/xmlschema-1/`
- 1.1: `https://www.w3.org/TR/xmlschema11-1/`

are defined as follows:

- `XSD/1.0`
- `XSD/1.1`

#### Apache Avro Schema

The [`format`](#format-schema-format) identifier for Apache Avro Schema is
`Avro`. The version of the Apache Avro Schema format is the version of the
Apache Avro Schema release that is used to define the schema.

When the `format` attribute is set to `Avro`, the `schema` attribute of the
`schemaversion` is a JSON object representing an Avro schema document conformant
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
- If the Avro schema document is a local schema registry reference like
`#/schemaGroups/com.example.telemetry/schemas/com.example.telemetrydata`, in the
which the reference is already in the form of a URI fragment, the suffix is
appended separated with a colon, for instance
`.../com.example.telemetrydata:TelemetryEvent`.

#### Protobuf Schema

The [`format`](#format-schema-format) identifier for Protobuf Schema is
`Protobuf`. The version of the Protobuf Schema format is the version of the
Protobuf syntax that is used to define the schema.

When the `format` attribute is set to `Protobuf`, the `schema` attribute of the
`schemaversion` is a string containing a Protobuf schema document conformant
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
- If the Protobuf schema document is a local schema registry reference like
  `#/schemaGroups/com.example.telemetry/schemas/com.example.telemetrydata`, in
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
