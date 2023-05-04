# Message Definitions Registry Service - Version 0.5-wip

## Abstract

TODO

## Table of Contents

- [Overview](#overview)
- [Notations and Terminology](#notations-and-terminology)
  - [Notational Conventions](#notational-conventions)
  - [Terminology](#terminology)
- [CloudEvents Registry](#cloudevents-registry)
  - [Message Definitions Registry](#message-definitions-registry)
    - [Message Definition Groups](#message-definition-groups)
    - [Message Definitions](#message-definitions)

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

- The [Schema Registry](../schema/spec.md) specification describes the metadata
  description of payload schemas for events and messages. The schema registry is
  universally applicable to any scenario where collaborating parties share
  structured data that is defined by formal schemas. For instance, when storing
  Protobuf encoded structured data in a cloud file store, you might place a
  schema registry in file form in the parent directory, which formally organizes
  and documents all versions of all Protobuf schemas that are used in the
  directory.
- The [Message Definitions Registry](#message-definitions-registry) section
  describes the metadata description of events and messages. The payload schemas
  for events and messages can be embedded in the definition, reference an
  external schema document, or can be referenced into the schema registry. The
  message definitions registry is universally applicable to any asynchronous
  messaging and eventing scenario. You might define a group of definitions that
  describe precisely which messages, with which metadata, are permitted to flow
  into a channel and can thus be expected by consumers of that channel and then
  associate that definition group with a topic or queue in your eventing or
  messaging infrastructure. That association might be a metadata attribute on
  the topic or queue in the messaging infrastructure that embeds the metadata or
  points to it.
- The [Endpoint Registry](../endpoint/spec.md) section defines the metadata
  description of network endpoints that accept or emit events and messages. The
  endpoint registry is a formal description of associations of message
  definitions and network endpoints, which can be used to discover endpoints
  that consume or emit particular messages or events via a central registry. The
  message definitions can be embedded into the endpoint metadata or as
  a reference into the message definitions registry.

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
Formats](#message-formats) section therefore not only describes the attribute
meta-schema for CloudEvents, but also meta-schemas for the native message
envelopes of MQTT, AMQP, and other messaging protocols.

The registry is designed to be extensible to support any structured data
encoding and related schemas for message or event payloads. The [Schema
Formats](../schema/spec.md#schema-formats) section describes the meta-schema
for JSON Schema, XML Schema, Apache Avro schema, and Protobuf schema.

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

### Message Definitions Registry

The Message Definitions Registry (or "Message Catalog") is a registry of
metadata definitions for messages and events. The entries in the registry
describe constraints for the metadata of messages and events, for instance the
concrete values and patterns for the `type`, `source`, and `subject` attributes
of a CloudEvent.

All message definitions (events are a from of messages and are therefore always
implied to be included from here on forward) are defined inside definition
groups.

A definition group is a collection of message definitions that are related to
each other in some application-specific way. For instance, a definition group
can be used to group all events raised by a particular application module or by
a particular role of an application protocol exchange pattern.

The Registry API extension model of the Message Definitions Registry is

``` JSON
{
  "groups": [
    {
      "singular": "definitionGroup",
      "plural": "definitionGroups",
      "schema": "TBD",
      "resources": [
        {
          "singular": "definition",
          "plural": "definitions",
          "versions": 1,
        }
      ]
    }
  ]
}
```

#### Message Definition Groups

The Group (GROUP) name is `definitionGroups`. The type of a group is
`definitionGroup`.

The following attributes are defined for the `definitionGroup` object in
addition to the basic [attributes](../core/spec.md#attributes-and-extensions):

##### `format` (Message format)

- Type: String
- Description: Identifies the message metadata format. Message metadata formats
  are referenced by name and version as `{NAME}/{VERSION}`. This specification
  defines a set of common [message format names](#message-formats) that MUST be
  used for the given formats, but applications MAY define extensions for other
  formats on their own. All definitions inside a group MUST use this same
  format.
- Constraints:
  - REQUIRED
  - MUST be a non-empty string
  - MUST follow the naming convention `{NAME}/{VERSION}`, whereby `{NAME}` is
    the name of the message format and `{VERSION}` is the version of the schema
    format in the format defined by the schema format itself.
- Examples:
  - `CloudEvents/1.0`
  - `MQTT/3.1.1`
  - `AMQP/1.0`
  - `Kafka/0.11`

#### Message Definitions

The resource (RESOURCE) collection name inside `definitionGroup` is
`definitions`. The resource name is `definition`.

Different from schemas, message definitions do not contain a
version history. If the metadata of two messages differs, they are considered
different definitions.

The following extension is defined for the `definition` object in addition to
the basic [attributes](../core/spec.md#attributes-and-extensions):

##### `format` (Message format, definition)

Same as the [`format`](#format-message-format) attribute of the
`definitionGroup` object.

Since definitions MAY be cross-referenced ("borrowed") across definition group
boundaries, this attribute is also REQUIRED and MUST be the same as the `format`
attribute of the `definitionGroup` object into which the definition is embedded
or referenced.

Illustrating example:

``` JSONC

"definitionGroupsUrl": "...",
"definitionGroupsCount": 2,
"definitionGroups": {
  "com.example.abc": {
    "id": "com.example.abc",
    "format": "CloudEvents/1.0",

    "definitionsUrl": "...",
    "definitionsCount": 2,
    "definitions": {
      "com.example.abc.event1": {
        "id": "com.example.abc.event1",
        "format": "CloudEvents/1.0",
         // ... details ...
        }
      },
      "com.example.abc.event2": {
        "id": "com.example.abc.event1",
        "format": "CloudEvents/1.0",
        // ... details ...
      }
  },
  "com.example.def": {
    "id": "com.example.def",
    "format": "CloudEvents/1.0",

    "definitionsUrl": "...",
    "definitionsCount": 1,
    "definitions": {
      "com.example.abc.event1": {
        "uri": "#/definitionGroups/com.example.abc/definitions/com.example.abc.event1",
        // ... details ...
      }
    }
  }
}
```

##### `metadata` (Message metadata)

- Type: Object
- Description: Describes the metadata constraints for messages of this type. The
  content of the metadata property is defined by the message format, but all
  formats use a common schema for the constraints defined for their metadata
  headers, properties or attributes.
- Constraints:
  - REQUIRED
- Examples:
  - See [Message Formats](#message-formats)

##### `schemaformat`

- Type: String
- Description: Identifies the schema format applicable to the message payload,
  equivalent to the schema ['format'](../schema/spec.md#format-schema-format)
  attribute.
- Constraints:
  - OPTIONAL
  - If present, MUST be a non-empty string
  - If present, MUST follow the naming convention `{NAME}/{VERSION}`, whereby
    `{NAME}` is the name of the schema format and `{VERSION}` is the version of
    the schema format in the format defined by the schema format itself.
- Examples:
  - 'JSONSchema/draft-07'
  - 'Avro/1.9.0'
  - 'Protobuf/3'

##### `schema` (Message schema)

- Type: String | Object as defined by the schema format
- Description: Contains the inline schema for the message payload. The schema
  format is identified by the `schemaformat` attribute. Equivalent to the
  schemaversion
  ['schema'](../schema/spec.md#schema) attribute
- Constraints:
  - OPTIONAL.
  - Mutually exclusive with the `schemaurl` attribute.
  - If present, `schemaformat` MUST be present.
- Examples:
  - See [Schema Formats](../schema/spec.md#schema-formats)

##### `schemaurl` (Message schema URL)

- Type: URI-reference
- Description: Contains a relative or absolute URI that points to the schema
  object to use for the message payload. The schema format is identified by the
  `schemaformat` attribute. See
  [Schema Formats](../schema/spec.md#schema-formats) for details on
  how to reference specific schema objects for the message payload. It is not
  sufficient for the URI-reference to point to a schema document; it MUST
  resolve to a concrete schema object.
- Constraints:
  - OPTIONAL.
  - Mutually exclusive with the `schema` attribute.
  - If present, `schemaformat` MUST be present.

#### Message Formats

This section defines the message formats that are directly supported by this
specification. Message formats lean on a protocol-neutral metadata definition
like CloudEvents or on the message model definition of a specific protocol like
AMQP or MQTT or Kafka. A message format defines constraints for the fixed and
variable headers/properties/attributes of the event format or protocol message
model.

> Message format definitions might be specific to a particular client instance
> and used to configure that client. Therefore, the message format definitions
> allow for specifying very narrow constraints like the exact value of an Apache
> Kafka record `key`.

##### Common properties

The following properties are common to all definitions of message
headers/properties/attributes constraints:

###### `required` (REQUIRED)

- Type: Boolean
- Description: Indicates whether the property is REQUIRED to be present in a
  message of this type.
- Constraints:
  - OPTIONAL. Defaults to `false`.
  - If present, MUST be a boolean value.

###### `description` (Description)

- Type: String
- Description: A human-readable description of the property.
- Constraints:
  - OPTIONAL.
  - If present, MUST be a non-empty string.

###### `value` (Value)

- Type: Any
- Description: The value of the property. With a few exceptions, see below, this
  is the value that MUST be literally present in the message for the message to
  be considered conformant with this metaschema.
- Constraints:
  - OPTIONAL.
  - If present, MUST be a valid value for the property.

If the `type` property has the value `uritemplate`, `value` MAY contain
placeholders. As defined in [RFC6570][RFC6570] (Level 1), the placeholders MUST
be enclosed in curly braces (`{` and `}`) and MUST be a valid `symbol`.
Placeholders that are used multiple times in the same message definition are
assumed to represent identical values.

When validating a message property against this value, the placeholders act as
wildcards. For example, the value `{foo}/bar` would match the value `abc/bar` or
`xyz/bar`.

When creating a message based on a metaschema with such a value, the
placeholders MUST be replaced with valid values. For example, the value
`{foo}/bar` would be replaced with `abc/bar` or `xyz/bar` when creating a
message.

If the `type` property has the value `timestamp` and the `value` property is
set to a value of `01-01-0000T00:00:00Z`, the value MUST be replaced with the
current timestamp when creating a message.

###### `type` (Type)

- Type: String
- Description: The type of the property. This is used to constrain the value of
  the property.
- Constraints:
  - OPTIONAL. Defaults to "string".
  - The valid types are those defined in the [CloudEvents][CloudEvents Types]
    core specification, with some additions:
    - `var`: Any type of value, including `null`.
    - `boolean`: CloudEvents "Boolean" type.
    - `string`: CloudEvents "String" type.
    - `symbol`: A `string` that is restricted to alphanumerical characters and
      underscores.
    - `binary`: CloudEvents "Binary" type.
    - `timestamp`: CloudEvents "Timestamp" type (RFC3339 DateTime)
    - `duration`: RFC3339 Duration
    - `uritemplate`: [RFC6570][RFC6570] Level 1 URI Template
    - `uri`: CloudEvents "URI" type (RFC3986 URI)
    - `urireference`: CloudEvents "URI-reference" type (RFC3986 URI-reference)
    - `number`: IEEE754 Double
    - `integer`: CloudEvents "Integer" type (RFC 7159, Section 6)

###### `specurl` (Specification URL)

- Type: URI-reference
- Description: Contains a relative or absolute URI that points to the
  human-readable specification of the property.
- Constraints:
  - OPTIONAL

###### CloudEvents/1.0

For the "CloudEvents/1.0" format, the [`metadata`](#metadata-message-metadata)
object contains a property `attributes`, which is an object whose properties
correspond to the CloudEvents context attributes.

As with the [CloudEvents specification][CloudEvents], the attributes form a
flat list and extension attributes are allowed. Attribute names are restricted
to lower-case alphanumerical characters without separators.

The base attributes are defined as follows:

| Attribute | Type |
| ---- | ---- |
| `type` | `string` |
| `source` | `uritemplate` |
| `subject` | `string` |
| `id` | `string` |
| `time` | `timestamp` |
| `dataschema` | `uritemplate` |
| `datacontenttype` | `string` |

The following rules apply to the attribute declarations:

- All attribute declarations are OPTIONAL. Requirements for absent
  definitions are implied by the CloudEvents specification.
- The `specversion` attribute is implied by the message format and is NOT
  REQUIRED. If present, it MUST be declared with a `string` type and set to the
  value "1.0".
- The `type`, `id`, and `source` attributes implicitly have the `required` flag
  set to `true` and MUST NOT be declared as `required: false`.
- The `id` attribute's `value` SHOULD NOT be defined.
- The `time` attribute's `value` defaults to `01-01-0000T00:00:00Z` ("current
  time") and SHOULD NOT be declared with a different value.
- The `datacontenttype` attribute's `value` is inferred from the
  [`schemaformat`](#schemaformat) attribute of the message definition if absent.
- The `dataschema` attribute's `value` is inferred from the
  [`schemaurl`](#schemaurl-message-schema-url) attribute or
  [`schema`](#schema-message-schema) attribute of the message definition if
  absent.
- The `type` of the property definition defaults to the CloudEvents type
  definition for the attribute, if any. The `type` of an attribute MAY be
  modified. For instance, the `source` type `urireference` MAY be changed to
  `uritemplate` or the `subject` type `string` MAY be constrained to a
  `urireference` or `integer`. If no CloudEvents type definition exists, the
  type defaults to `string`.

The values of all `string` and `uritemplate`-typed attributes MAY contain
placeholders using the [RFC6570][RFC6570] Level 1 URI Template syntax. When the
same placeholder is used in multiple properties, the value of the placeholder is
assumed to be identical.

The following example declares a CloudEvent with a JSON payload. The attribute
`id` is REQUIRED in the declared event per the CloudEvents specification in
spite of such a declaration being absent here, the `type` of the `type`
attribute is `string` and the attribute is `required` even though the
declarations are absent. The `time` attribute is made `required` contrary to the
CloudEvents base specification. The implied `datacontenttype` is
`application/json` and the implied `dataschema` is
`https://example.com/schemas/com.example.myevent.json`:

``` JSON
{
  "format": "CloudEvents/1.0",
  "metadata": {
    "attributes": {
      "type": {
        "value": "com.example.myevent"
      },
      "source": {
        "value": "https://{tenant}/{module}/myevent",
        "type": "uritemplate"
      },
      "subject": {
        "type": "urireference"
      },
      "time": {
        "required": true
      },
    }
  },
  "schemaformat": "JsonSchema/draft-07",
  "schemaurl": "https://example.com/schemas/com.example.myevent.json",
}
```

For clarity of the definition, you MAY always declare all implied attribute
properties explicitly, but they MUST conform with the rules above.

#### "HTTP/1.1", "HTTP/2", "HTTP/3"

The "HTTP" format is used to define messages that are sent over an HTTP
connection. The format is based on the [HTTP Message Format][HTTP Message
 Format] and is common across all version of HTTP.

The [`metadata`](#metadata-message-metadata) object MAY contain several
properties:

| Property | Type | Description |
| --- | --- | --- |
| `headers` | Array | The HTTP headers. See below. |
| `query` | Map | The HTTP query parameters. |
| `path` | `uritemplate` | The HTTP path. |
| `method` | `string` | The http method |
| `status` | `string` | The http status code |

HTTP allows for multiple headers with the same name. The `headers` property is
therefore an array of objects with `name` and `value` properties. The `name`
property is a string that MUST be a valid HTTP header name.

The `query` property is a map of string keys to string values.

The `path` property is a URI template.

The `method` property is a string that MUST be a valid HTTP method.

The `status` property is a string that MUST be a valid HTTP response
code. The `status` and `method` properties are mutually exclusive and
MUST NOT be present at the same time.

The values of all `string` and `uritemplate`-typed properties and headers and
query elements MAY contain placeholders using the [RFC6570][RFC6570] Level 1 URI
Template syntax. When the same placeholder is used in multiple properties, the
value of the placeholder is assumed to be identical.

The following example defines a message that is sent over HTTP/1.1:

``` JSON
{
  "format": "HTTP/1.1",
  "metadata": {
    "headers": [
      {
        "name": "Content-Type",
        "value": "application/json"
      }
    ],
    "query": {
      "foo": "bar"
    },
    "path": "/foo/{bar}",
    "method": "POST"
  },
  "schemaformat": "JsonSchema/draft-07",
  "schemaurl": "https://example.com/schemas/com.example.myevent.json",
}
```

#### "AMQP/1.0"

The "AMQP/1.0" format is used to define messages that are sent over an
[AMQP][AMQP 1.0] connection. The format is based on the default
[AMQP 1.0 Message Format][AMQP 1.0 Message Format].

The [`metadata`](#metadata-message-metadata) object MAY contain several
properties, each of which corresponds to a section of the AMQP 1.0 Message:

| Property | Type | Description |
| ---- | --- | ---- |
| `properties` | Map | The AMQP 1.0 [Message Properties][AMQP 1.0 Message Properties] section. |
| `application-properties` | Map | The AMQP 1.0 [Application Properties][AMQP 1.0 Application Properties] section. |
| `message-annotations` | Map | The AMQP 1.0 [Message Annotations][AMQP 1.0 Message Annotations] section. |
| `delivery-annotations` | Map | The AMQP 1.0 [Delivery Annotations][AMQP 1.0 Delivery Annotations] section. |
| `header` | Map | The AMQP 1.0 [Message Header][AMQP 1.0 Message Header] section. |
| `footer` | Map | The AMQP 1.0 [Message Footer][AMQP 1.0 Message Footer] section. |

As in AMQP, all sections and properties are OPTIONAL.

The values of all `string`, `symbol`, `uri`, and `uritemplate`-typed properties
MAY contain placeholders using the [RFC6570][RFC6570] Level 1 URI Template
syntax. When the same placeholder is used in multiple properties, the value of
the placeholder is assumed to be identical.

Example for an AMQP 1.0 message type that declares a fixed `subject` (analogous
to CloudEvents' `type`), a custom property, and a `content-type` of
`application/json` without declaring a schema reference in the message
definition:

``` JSON
{
  "format": "AMQP/1.0",
  "metadata": {
    "properties": {
      "message-id": {
        "required": true
      },
      "to": {
        "value": "https://{host}/{queue}"
      },
      "subject": {
        "value": "MyMessageType"
        "required": true
      },
      "content-type": {
        "value": "application/json"
      },
      "content-encoding": {
        "value": "utf-8"
      }
    },
    "application-properties": {
      "my-application-property": {
        "value": "my-application-property-value"
      }
    }
  }
}
```

##### `properties` (AMQP 1.0 Message Properties)

The `properties` property is an object that contains the properties of the
AMQP 1.0 [Message Properties][AMQP 1.0 Message Properties] section. The
following properties are defined, with type constraints:

| Property | Type | Description |
| --- | --- | --- |
| `message-id` | `string` | uniquely identifies a message within the message system |
| `user-id` | `binary` | identity of the user responsible for producing the message |
| `to` | `uritemplate` | address of the node to send the message to |
| `subject` | `string` | message subject |
| `reply-to` | `uritemplate` | address of the node to which the receiver of this message ought to send replies |
| `correlation-id` | `string` | client-specific id that can be used to mark or identify messages between clients |
| `content-type` | `symbol` | MIME content type for the message |
| `content-encoding` | `symbol` | MIME content encoding for the message |
| `absolute-expiry-time` | `timestamp` | time when this message is considered expired |
| `group-id` | `string` | group this message belongs to |
| `group-sequence` | `integer` | position of this message within its group |
| `reply-to-group-id` | `uritemplate` | group-id to which the receiver of this message ought to send replies to |

##### `application-properties` (AMQP 1.0 Application Properties)

The `application-properties` property is an object that contains the custom
properties of the AMQP 1.0 [Application Properties][AMQP 1.0 Application
Properties] section.

The names of the properties MUST be of type `symbol` and MUST be unique.
The values of the properties MAY be of any permitted type.

##### `message-annotations` (AMQP 1.0 Message Annotations)

The `message-annotations` property is an object that contains the custom
properties of the AMQP 1.0 [Message Annotations][AMQP 1.0 Message Annotations]
section.

The names of the properties MUST be of type `symbol` and MUST be unique.
The values of the properties MAY be of any permitted type.

##### `delivery-annotations` (AMQP 1.0 Delivery Annotations)

The `delivery-annotations` property is an object that contains the custom
properties of the AMQP 1.0
[Delivery Annotations][AMQP 1.0 Delivery Annotations] section.

The names of the properties MUST be of type `symbol` and MUST be unique.
The values of the properties MAY be of any permitted type.

###### `header` (AMQP 1.0 Message Header)

The `header` property is an object that contains the properties of the
AMQP 1.0 [Message Header][AMQP 1.0 Message Header] section. The
following properties are defined, with type constraints:

| Property | Type | Description |
| --- | --- | --- |
| `durable` | `boolean` | specify durability requirements |
| `priority` | `integer` | relative message priority |
| `ttl` | `integer` | message time-to-live in milliseconds |
| `first-acquirer` | `boolean` | indicates whether the message has not been acquired previously |
| `delivery-count` | `integer` | number of prior unsuccessful delivery attempts |

##### `footer` (AMQP 1.0 Message Footer)

The `footer` property is an object that contains the custom properties of the
AMQP 1.0 [Message Footer][AMQP 1.0 Message Footer] section.

The names of the properties MUST be of type `symbol` and MUST be unique.
The values of the properties MAY be of any permitted type.

#### "MQTT/3.1.1" and "MQTT/5.0"

The "MQTT/3.1.1" and "MQTT/5.0" formats are used to define messages that are
sent over [MQTT 3.1.1][MQTT 3.1.1] or [MQTT 5.0][MQTT 5.0] connections. The
format describes the [MQTT PUBLISH packet][MQTT 5.0] content.

The [`metadata`](#metadata-message-metadata) object contains the elements of the
MQTT PUBLISH packet directly, with the `user-properties` element corresponding
to the application properties collection of other protocols.

The following properties are defined. The MQTT 3.1.1 and MQTT 5.0 columns
indicate whether the property is supported for the respective MQTT version.

| Property | Type | MQTT 3.1.1 | MQTT 5.0 | Description |
| --- | --- | --- | --- | --- |
| `qos` | `integer` | yes | yes | Quality of Service level |
| `retain` | `boolean` | yes | yes | Retain flag |
| `topic-name` | `string` | yes | yes | Topic name |
| `payload-format` | `integer` | no | yes | Payload format indicator |
| `message-expiry-interval` | `integer` | no | yes | Message expiry interval |
| `response-topic` | `uritemplate` | no | yes | Response topic |
| `correlation-data` | `binary` | no | yes | Correlation data |
| `content-type` | `symbol` | no | yes | MIME content type of the payload |
| `user-properties` | Array | no | yes | User properties |

Like HTTP, the MQTT allows for multiple user properties with the same name,
so the `user-properties` property is an array of objects, each of which
contains a single property name and value.

The values of all `string`, `symbol`, and `uritemplate`-typed properties and
user-properties MAY contain placeholders using the [RFC6570][RFC6570] Level 1
URI Template syntax. When the same placeholder is used in multiple properties,
the value of the placeholder is assumed to be identical.

The following example shows a message with the "MQTT/5.0" format, asking for
QoS 1 delivery, with a topic name of "mytopic", and a user property of
"my-application-property" with a value of "my-application-property-value":

``` JSON
{
  "format": "MQTT/5.0",
  "metadata": {
    "qos": {
      "value": 1
    },
    "retain": {
      "value": false
    },
    "topic-name": {
      "value": "mytopic"
    },
    "user-properties": [
      { "my-application-property": {
            "value": "my-application-property-value"
          }
      }
    ]
  }
}
```

#### "Kafka/0.11" format

The "Kafka" format is used to define messages that are sent over [Apache
Kafka][Apache Kafka] connections. The version number reflects the last version
in which the record structure was changed in the Apache Kafka project, not the
current version. If the version number is omitted, the latest version is
assumed.

The [`metadata`](#metadata-message-metadata) object contains the common elements
of the Kafka [producer][Apache Kafka producer] and [consumer][Apache Kafka
consumer] records, with the `headers` element corresponding to the application
properties collection of other protocols.

The following properties are defined:

| Property | Type | Description |
| --- | --- | --- |
| `topic` | `string` | The topic the record will be appended to |
| `partition` | `integer` | The partition to which the record ought be sent |
| `key` | `binary` | The key that will be included in the record |
| `headers` | Map | A map of headers to set on the record |
| `timestamp` | `integer` | The timestamp of the record; if 0 (default), the producer will assign the timestamp |

The values of all `string`, `symbol`, `uritemplate`-typed properties
and headers MAY contain placeholders using the [RFC6570][RFC6570] Level 1 URI
Template syntax. When the same placeholder is used in multiple properties, the
value of the placeholder is assumed to be identical.

Example:

``` JSON
{
  "format": "Kafka/0.11",
  "metadata": {
    "topic": {
      "value": "mytopic"
    },
    "key": {
      "value": "thisdevice"
    }
  }
}

```

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
