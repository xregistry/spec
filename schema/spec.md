# Schema Registry Service - Version 0.5-wip

## Abstract

TODO

## Table of Contents

- [Overview](#overview)
- [Notations and Terminology](#notations-and-terminology)
  - [Notational Conventions](#notational-conventions)
  - [Terminology](#terminology)
- [CloudEvents Registry](#cloudevents-registry)
  - [Schema Registry](#schema-registry)
    - [Schema Groups](#group-schemagroups)
    - [Schemas](#resource-schemas)

## Overview

TODO

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

#### ???

TODO

## CloudEvents Registry

The CloudEvents Registry is a universal catalog and discovery metadata format
as well as a metadata service API for messaging and eventing schemas,
metaschemas, and messaging and eventing endpoints.

The CloudEvents registry model contains three separate registries that can be
implemented separately or in combination.

- The [Schema Registry](#schema-registry) specification describes the metadata
  description of payload schemas for events and messages. The schema registry is
  universally applicable to any scenario where collaborating parties share
  structured data that is defined by formal schemas. For instance, when storing
  Protobuf encoded structured data in a cloud file store, you might place a
  schema registry in file form in the parent directory, which formally organizes
  and documents all versions of all Protobuf schemas that are used in the
  directory.
- The [Message Definitions Registry](../message/spec.md)
  specification describes the metadata description of events and messages. The
  payload schemas for events and messages can be embedded in the definition,
  reference an external schema document, or can be referenced into the schema
  registry. The message definitions registry is universally applicable to any
  asynchronous messaging and eventing scenario. You might define a group of
  definitions that describe precisely which messages, with which metadata, are
  permitted to flow into a channel and can thus be expected by consumers of
  that channel and then associate that definition group with a topic or queue
  in your eventing or messaging infrastructure. That association might be a
  metadata attribute on the topic or queue in the messaging infrastructure
  that embeds the metadata or points to it.
- The [Endpoint Registry](../endpoint/spec.md) specification defines the
  metadata description of network endpoints that accept or emit events and
  messages. The endpoint registry is a formal description of associations of
  message definitions and network endpoints, which can be used to discover
  endpoints that consume or emit particular messages or events via a central
  registry. The message definitions can be embedded into the endpoint metadata
  or as a reference into the message definitions registry.

The metadata model is structured such that network endpoint information and
message metadata and payload schemas can be described compactly in a single
metadata object (and therefore as a single document) in the simplest case or can
be spread out and managed across separate registry products in a sophisticated
large-enterprise scenario.

The following is an exemplary, compact definition of an MQTT 5.0 consumer
endpoint with a single, embedded message definition using an embedded Protobuf 3
schema for its payload.

``` JSON
{
  "$schema": "https://cloudevents.io/schemas/registry",
  "specversion": "0.5-wip",
  "id": "urn:uuid:3978344f-8596-4c3a-a978-8fc9a6a469f7",
  "endpoints":
  {
    "com.example.telemetry": {
      "id": "com.example.telemetry",
      "usage": "consumer",
      "config": {
        "protocol": "MQTT/5.0",
        "strict": false,
        "endpoints": [
            "mqtt://mqtt.example.com:1883"
        ],
        "options": {
            "topic": "{deviceid}/telemetry"
        }
      },
      "format": "CloudEvents/1.0",
      "definitions": {
        "com.example.telemetry": {
          "id": "com.example.telemetry",
          "description": "device telemetry event",
          "format": "CloudEvents/1.0",
          "metadata": {
            "attributes": {
              "id": {
                "type": "string",
                "required": true
              },
              "type": {
                "type": "string",
                "value": "com.example.telemetry",
                "required": true
              },
              "time": {
                "type": "datetime",
                "required": true
              },
              "source": {
                "type": "uritemplate",
                "value": "{deploymentid}/{deviceid}",
                "required": true
              }
            }
          },
          "schemaformat": "Protobuf/3.0",
          "schema": "syntax = \"proto3\"; message Metrics { float metric = 1; } }"
        }
      }
    }
  }
}
```

The same metadata can be expressed by spreading the metadata across the message
definition and schema registries, which makes the definitions reusable for other
scenarios:

``` JSON
{
  "$schema": "https://cloudevents.io/schemas/registry",
  "specversion": "0.4-wip",
  "id": "urn:uuid:3978344f-8596-4c3a-a978-8fc9a6a469f7",

  "endpointsCount": 1,
  "endpoints":
  {
    "com.example.telemetry": {
      "id": "com.example.telemetry",
      "usage": "consumer",
      "config": {
        "protocol": "MQTT/5.0",
        "strict": false,
        "endpoints": [
          "mqtt://mqtt.example.com:1883"
        ],
        "options": {
          "topic": "{deviceid}/telemetry"
        }
      },
      "format": "CloudEvents/1.0",
      "definitionGroups": [
        "#/definitionGroups/com.example.telemetryEvents"
      ]
    }
  },

  "definitionGroupsCount": 1,
  "definitionGroups": {
    "com.example.telemetryEvents": {
      "id": "com.example.telemetryEvents",

      "definitionsCount": 1,
      "definitions": {
        "com.example.telemetry": {
          "id": "com.example.telemetry",
          "description": "device telemetry event",
          "format": "CloudEvents/1.0",
          "metadata": {
            "attributes": {
              "id": {
                "type": "string",
                "required": true
              },
              "type": {
                "type": "string",
                "value": "com.example.telemetry",
                "required": true
              },
              "time": {
                "type": "datetime",
                "required": true
              },
              "source": {
                "type": "uritemplate",
                "value": "{deploymentid}/{deviceid}",
                "required": true
              }
            }
          },
          "schemaformat": "Protobuf/3.0",
          "schemaurl": "#/schemaGroups/com.example.telemetry/schema/com.example.telemetrydata/versions/1.0"
        }
      }
    }
  },

  "schemaGroupsCount": 1,
  "schemaGroups": {
    "com.example.telemetry": {
      "id": "com.example.telemetry",

      "schemasCount": 1,
      "schemas": {
        "com.example.telemetrydata": {
          "id": "com.example.telemetrydata",
          "description": "device telemetry event data",
          "format": "Protobuf/3.0",

          "versionsCount": 1,
          "versions": {
            "1.0": {
              "id": "1.0",
              "schema": "syntax = \"proto3\"; message Metrics { float metric = 1; }"
            }
          }
        }
      }
    }
  }
}
```

If we assume the message definitions and schemas to reside at an API endpoint,
an endpoint definition might just reference the associated message definition
group with a deep link to the respective object in the service:

``` JSONC
{
  "$schema": "https://cloudevents.io/schemas/registry",
  "specversion": "0.4-wip",
  "id": "urn:uuid:3978344f-8596-4c3a-a978-8fc9a6a469f7",

  "endpointsCount": 1,
  "endpoints":
  {
    "com.example.telemetry": {
      "id": "com.example.telemetry",
      "usage": "consumer",
      "config": {
        // ... details ...
      },
      "format": "CloudEvents/1.0",
      "definitionGroups": [
          "https://site.example.com/registry/definitiongroups/com.example.telemetryEvents"
      ]
    }
  }
}
```

If the message definitions and schemas are stored in a file-based registry,
including files shared via public version control repositories, the reference
link will first reference the file and then the object within the file, using
[JSON Pointer][JSON Pointer] syntax:

``` JSONC
{
  "$schema": "https://cloudevents.io/schemas/registry",
  "specversion": "0.4-wip",
  "id": "urn:uuid:3978344f-8596-4c3a-a978-8fc9a6a469f7",

  "endpointsCount": 1,
  "endpoints":
  {
    "com.example.telemetry": {
      "id": "com.example.telemetry",
      "usage": "consumer",
      "config": {
        // ... details ......
      },
      "format": "CloudEvents/1.0",
      "definitionGroups": [
        "https://rawdata.repos.example.com/myorg/myproject/main/example.telemetryEvents.cereg#/definitionGroups/com.example.telemetryEvents"
      ]
    }
  }
}
```

All other references to other objects in the registry can be expressed in the
same way.

While the CloudEvents Registry is primarily motivated by enabling development of
CloudEvents-based event flows, the registry is not limited to CloudEvents. It
can be used to describe any asynchronous messaging or eventing endpoint and its
messages, including endpoints that do not use CloudEvents at all. The [Message
Formats](../message/spec.md#message-formats) section therefore not only
describes the attribute
meta-schema for CloudEvents, but also meta-schemas for the native message
envelopes of MQTT, AMQP, and other messaging protocols.

The registry is designed to be extensible to support any structured data
encoding and related schemas for message or event payloads. The [Schema
Formats](#schema-formats) section describes the meta-schema for JSON Schema, XML
Schema, Apache Avro schema, and Protobuf schema.

### File format

A CloudEvents Registry can be implemented using the Registry API or with plain
text files.

When using the file-based model, files with the extension `.cereg` use JSON
encoding. Files with the extension `.cereg.yaml` or `.cereg.yml` use YAML
encoding. The formal JSON schema for the file format is defined in the
[CloudEvents Registry Document
Schema](../endpoint/spec.md#cloudevents-registry-document-schema),
which implements the Registry format and the CloudEvents Registry format.

The media-type for the file format is `application/cloudevents-registry+json`
for the JSON encoding and `application/cloudevents-registry+yaml` for the YAML
encoding.

The JSON schema identifier is `https://cloudevents.io/schemas/registry` and the
`specversion` property indicates the version of this specification that the
elements of the file conform to.

A CloudEvents Registry file MUST contain a single JSON object or YAML document.
The object declares the roots of the three sub-registries, which are either
embedded or referenced. Any of the three sub-registries MAY be omitted.

``` meta
{
   "$schema": "https://cloudevents.io/schemas/registry",
   "specversion": "0.4-wip",

   "endpointsUrl": "URL",
   "endpointsCount": INT,
   "endpoints": { ... },

   "definitionGroupsUrl": "URL",
   "definitionGroupsCount": INT,
   "definitionGroups": { ... },

   "schemaGroupsUrl": "URL",
   "schemaGroupsCount": INT,
   "schemaGroups": { ... }
}
```

While the file structure leads with endpoints followed by definition groups and
then schema groups by convention, the order of the sub-registries is not
significant.

### Schema Registry

The schema registry is a metadata store for organizing data schemas of any kind.

The Registry API extension model of the Schema Registry is:

``` JSON
{
  "groups": [
    {
      "singular": "schemaGroup",
      "plural": "schemaGroups",
      "schema": "TBD",
      "resources": [
        {
          "singular": "schema",
          "plural": "schemas",
          "versions": 0
        }
      ]
    }
  ]
}
```

#### Group: schemaGroups

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

#### Resource: schemas

The resources (RESOURCE) collection inside of schema groups is named `schemas`.
The type of the resource is `schema`. Any single `schema` is a container for
one or more `versions`, which hold the concrete schema documents or schema
document references.

Any new schema version that is added to a schema definition MUST be backwards
compatible with all previous versions of the schema, meaning that a consumer
using the new schema MUST be able to understand data encoded using a prior
version of the schema. If a new version introduces a breaking change, it MUST be
registered as a new schema with a new name.

When you retrieve a schema without qualifying the version, you will get the
latest version of the schema, see [retrieving a
resource](../core/spec.md#retrieving-a-resource). The latest version is the
lexically greatest version number, whereby all version ids MUST be left-padded
with spaces to the same length before being compared.

The following extension is defined for the `schema` object in addition to the
basic [attributes](../core/spec.md#attributes-and-extensions):

##### `format` (Schema format)

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

#### Resource Version: schemaversion

The `VERSION` object of the `schema` resource is of type `schemaversion`. The
[`format`](#format-schema-format) extension attribute of `schema` MAY be
repeated in `schemaversion` for clarity, but MUST be identical.
`schemaversion` has the following extension attributes.

##### `schema`

- Type: String | Object
- Description: Embedded schema string or object. The format and encoding of the
  schema is defined by the `format` attribute.
- Constraints:
  - Mutually exclusive with `schemaurl`. One of the two MUST be present.

##### `schemaurl`

- Type: URI
- Description: Reference to a schema document external to the registry.
- Constraints:
  - Mutually exclusive with `schemaurl`. One of the two MUST be present.
  - Cross-references to a schema document within the same registry MUST NOT be
    used.

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

#### Schema Formats

This section defines a set of common schema formats that MUST be used for the
given formats, but applications MAY define extensions for other formats on their
own.

##### JSON Schema

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

##### XML Schema

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

##### Apache Avro Schema

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

##### Protobuf Schema

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
