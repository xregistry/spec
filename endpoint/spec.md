# Endpoint Registry Service - Version 0.5-wip

## Abstract

TODO

## Table of Contents

- [Overview](#overview)
- [Notations and Terminology](#notations-and-terminology)
  - [Notational Conventions](#notational-conventions)
  - [Terminology](#terminology)
- [CloudEvents Registry](#cloudevents-registry)
  - [Endpoint Registry](#endpoint-registry)
    - [Endpoints](#endpoints-endpoints)

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
- The [Message Definitions Registry](../message/spec.md) specification
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
- The [Endpoint Registry](#endpoint-registry) specification defines the metadata
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
Formats](../message/spec.md#message-formats) section therefore not only
describes the attribute meta-schema for CloudEvents, but also meta-schemas for
the native message envelopes of MQTT, AMQP, and other messaging protocols.

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
[CloudEvents Registry Document Schema](#cloudevents-registry-document-schema),
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

### Endpoint Registry

The Endpoint Registry is a registry of metadata definitions for abstract and
concrete network endpoint to which messages can be produced, from which messages
can be consumed, or which makes messages available for subscription and
delivery to a consumer-designated endpoint.

As discussed in [CloudEvents Registry overview](#cloudevents-registry),
endpoints are supersets of
[message definition groups](../message/spec.md#message-definition-groups) and
MAY contain inlined definitions. Therefore, the RESORCE level in the meta-model
for the Endpoint Registry are likewise `definitions`:

``` JSON
{
  "groups": [
    {
      "singular": "endpoint",
      "plural": "endpoints",
      "schema": "TBD",
      "resources": [
        {
          "singular": "definition",
          "plural": "definitions",
          "versions": 1,
          "mutable": true
        }
      ]
    }
  ]
}
```

#### Endpoints: endpoints

A Group (GROUP) name is `endpoints`. The type of a group is `endpoint`.

The following attributes are defined for the `endpoint` type:

##### `usage`

- Type: String (Enum: `subscriber`, `consumer`, `producer`)
- Description: The `usage` attribute is a string that indicates the intended
  usage of the endpoint by communicating parties.

  Each of these parties will have a different perspective on an endpoint. For
  instance, a `producer` endpoint is seen as a "target" by the originator of
  messages, and as a "source" by the party that accepts the messages. The
  nomenclature used for the `usage` field is primarily oriented around the
  common scenario of network endpoints being provided by some sort of
  intermediary like a message broker. The term `producer` primarily describes
  the relationship of a client with that intermediary.

  In a direct-delivery scenario where the originator of messages connects
  directly to the target (e.g. a "WebHook" call), the target endpoint implements
  the accepting end of the `producer` relationship.

  Some of these perspectives are mentioned below for illustration, but not
  formally defined or reflected in the metadata model. Perspectives depend on
  the context in which the endpoint metadata is used and this metadata model is
  intentionally leaving perspectives open to users.

  The following values are defined for `usage`

  - `subscriber`: The endpoint offers managing subscriptions for delivery of
    messages to another endpoint, using the [CloudEvents Subscriptions
    API][CloudEvents Subscriptions API].

    Some perspectives that might exist on a subscriber endpoint:
    - Application from which messages originate
    - Application which accepts messages from the delivery agent
    - Application which manages subscriptions for delivery of messages to the
      target application. This might be a message broker subscription manager.

  - `consumer`:  The endpoint offers messages being consumed from it.

    Some perspectives that might exist on a consumer endpoint:
    - Message store or source which makes messages available for consumption;
      this might be a message broker topic or a queue.
    - Proxy or other intermediary which solicits messages from the source and
      forwards them to the target endpoint.
    - Application which consumes messages

  - `producer`: The endpoint offers messages being produces (sent) to it.

    Some perspectives might exist on a producer endpoint:
    - Application from which messages originate
    - Reverse proxy or other intermediary which accepts messages from the
      originator and forwards them to the target endpoint.
    - Application which accepts messages. This might be a message broker topic
      or a queue. This might be an HTTP endpoint that directly accepts and
      handles messages.

  Any endpoint can be seen from different role perspectives:

  There might also be further perspectives such as pipeline stages for
  pre-/post-processing, etc.

- Constraints:
  - REQUIRED.
  - MUST be one of "subscriber", "consumer", or "producer".

#### `origin`

- Type: URI
- Description: A URI reference to the original source of this Endpoint. This
  can be used to locate the true authority owner of the Endpoint in cases of
  distributed Endpoint Registries. If this property is absent its default value
  is the value of the `self` property and in those cases its presence in the
  serialization of the Endpoint is OPTIONAL.
- Constraints:
  - OPTIONAL if this Endpoint Registry is the authority owner
  - REQUIRED if this Endpoint Registry is not the authority owner
  - if present, MUST be a non-empty URI
- Examples:
  - `https://example2.com/myregistry/endpoints/9876`

#### `deprecated`

- Type: Object containing the following properties:
  - effective<br>
    An OPTIONAL property indicating the time when the Endpoint entered, or will
    enter, a deprecated state. The date MAY be in the past or future. If this
    property is not present the Endpoint is already in a deprecated state.
    If present, this MUST be an [RFC3339][rfc3339] timestamp.

  - removal<br>
    An OPTIONAL property indicating the time when the Endpoint MAY be removed.
    The Endpoint MUST NOT be removed before this time. If this property is not
    present then client can not make any assumption as to when the Endpoint
    might be removed. Note: as with most properties, this property is mutable.
    If present, this MUST be an [RFC3339][rfc3339] timestamp and MUST NOT be
    sooner than the `effective` time if present.

  - alternative<br>
    An OPTIONAL property specifying the URL to an alternative Endpoint the
    client can consider as a replacement for this Endpoint. There is no
    guarantee that the referenced Endpoint is an exact replacement, rather the
    client is expected to investigate the Endpoint to determine if it is
    appropriate.

  - docs<br>
    An OPTIONAL property specifying the URL to additional information about
    the deprecation of the Endpoint. This specification does not mandate any
    particular format or information, however some possibilities include:
    reasons for the deprecation or additional information about likely
    alternative Endpoints. The URL MUST support an HTTP GET request.

- Description: This specification makes no statement as to whether any
  existing secondary resources (such as subscriptions) will still be valid and
  usable after the Endpoint is removed. However, it is expected that new
  requests to create a secondary resource will likely be rejected.

  Note that an implementation is not mandated to use this attribute in
  advance of removing an Endpoint, but is it RECOMMENDED that they do so.
- Constraints:
  - OPTIONAL
- Examples:
  - `"deprecated": {}`
  - ```
    "deprecated": {
      "removal": "2030-12-19T00:00:00-00:00",
      "alternative": "https://example.com/endpoints/123"
    }
    ```

#### `channel`

- Type: String
- Description: A string that can be used to correlate Endpoints. Any Endpoints
  within an instance of an Endpoint Registry that share the same non-empty
  `channel` value MUST have some relationship. This specification does not
  define that relationship or the specific values used in this property.
  However, it is expected that the `usage` value in combination with this
  `channel` property will provide some information to help determine the
  relationship.

  For instance, a message broker queue "queue1" might be represented with a
  `producer` endpoint and a `consumer` endpoint, both with the same `channel`
  attribute value of "queue1".

  An event processing pipeline might have a sequence of stages, each with a
  `producer` endpoint and a `consumer` endpoint, all with the same `channel`
  attribute value of "pipeline1", or some further qualification like
  "pipeline1-stage1", etc.

  When this property has no value it MUST either be serialized as an empty
  string or excluded from the serialization entirely.
- Constraints:
  - OPTIONAL
  - if present, MUST be a string
- Examples:
  - `queue1`

##### `definitions` (Endpoint)

Endpoints are supersets of
[message definition groups](../message/spec.md#message-definition-groups) and
MAY contain inlined definitions. See
[Message Definitions](../message/spec.md#message-definitions).

Example:

``` JSON
{
  "protocol": "HTTP/1.1",
  "options": {
    "method": "POST"
    },
  "definitionsUrl": "..."
  "definitionsCount": 1,
  "definitions": {
    "myevent": {
      "format": "CloudEvents/1.0",
      "metadata": {
        "attributes": {
          "type": {
            "value": "myevent"
          }
}}}}}
```

##### `definitionGroups` (Endpoint)

The `definitionGroups` attribute is an array of URI-references to message
definition groups. The `definitionGroups` attribute is used to reference
message definition groups that are not inlined in the endpoint definition.

Example:

``` JSON
{
  "protocol": "HTTP/1.1",
  "options": {
    "method": "POST"
    },
  "definitionGroups": [
    "https://example.com/registry/definitiongroups/mygroup"
  ]
}
```

##### `config`

- Type: Map
- Description: Configuration details of the endpoint. An endpoint
  MAY be defined without detail configuration. In this case, the endpoint is
  considered to be "abstract".
  > Note: Authentication and authorization details are intentionally **not**
  > included in the endpoint metadata. The supported authentication and
  > authorization mechanisms are either part of the protocol, negotiated at
  > runtime (e.g. SASL), made available through the specific endpoint's
  > documentation, or separate metadata specific to security policies.
- Constraints:
  - OPTIONAL

##### `config.protocol`

- Type: String
- Description: The transport or application protocol used by the endpoint. This
  specification defines a set of common protocol names that MUST be used for
  respective protocol endpoints, but implementations MAY define and use
  additional protocol names.

  Predefined protocols are referred to by name and version as
  `{NAME}/{VERSION}`. If the version is not specified, the default version of
  the protocol is assumed. The version number format is determined by the
  protocol specification's usage of versions.

  The predefined protocol names are:
  - "HTTP/1.1", "HTTP/2", "HTTP/3" - Use the *lowest* HTTP version
    that the endpoints supports; that is commonly "HTTP/1.1". The default
    version is "HTTP/1.1" and MAY be shortened to "HTTP".
  - "AMQP/1.0" - Use the [AMQP 1.0][AMQP 1.0] protocol. MAY be shortened to
    "AMQP". AMQP draft versions before 1.0 (e.g. 0.9) are *not* AMQP.
  - "MQTT/3.1.1", "MQTT/5.0" - Use the MQTT [3.1.1][MQTT 3.1.1] or [5.0][MQTT
    5.0] protocol. The shorthand "MQTT" maps to "MQTT/5.0".
  - "NATS/1.0.0" - Use the [NATS][NATS] protocol. MAY be shortened to "NATS",
  - which assumes usage of the latest NATS clients.
  - "KAFKA/3.5" - Use the [Apache Kafka][Apache Kafka] protocol. MAY be
    shortened to "KAFKA", which assumes usage of the latest Apache Kafka
    clients.

  An example for an extension protocol identifier might be "BunnyMQ/0.9.1".

- Constraints:
  - REQUIRED
  - MUST be a non-empty string.

##### `config.endpoints`

- Type: Array of URI
- Description: The network addresses that are for communication with the
  endpoint. The endpoints are ordered by preference, with the first endpoint
  being the preferred endpoint. Some protocol implementations might not support
  multiple endpoints, in which case all but the first endpoint might be ignored.
  Whether the URI just identifies a network host or links directly to a resource
  managed by the network host is protocol specific.
- Constraints:
  - OPTIONAL
  - Each entry MUST be a valid, absolute URI (URL)
- Examples:
  - `["tcp://example.com", "wss://example.com"]`
  - `["https://example.com"]`

##### `config.options`

- Type: Map
- Description: Additional configuration options for the endpoint. The
  configuration options are protocol specific and described in the
  [protocol options](#protocol-options) section below.
- Constraints:
  - OPTIONAL
  - When present, MUST be a map of non-empty strings to non-empty strings.
  - If `config.protocol` is a well-known protocol, the options MUST be
    compliant with the [protocol's options](#protocol-options).

##### `config.strict`

- Type: Boolean
- Description: If `true`, the endpoint metadata represents a public, live
  endpoint that is available for communication and a strict validator MAY test
  the liveness of the endpoint.
- Constraints:
  - OPTIONAL.
  - Default value is `false`.

##### Protocol Options

The following protocol options (`config.options`) are defined for the respective
protocols. All of these are OPTIONAL.

###### HTTP options

The [endpoint URIs](#configendpoints) for "HTTP" endpoints MUST be valid HTTP
URIs using the "http" or "https" scheme.

The following options are defined for HTTP:

- `method`: The HTTP method to use for the endpoint. The default value is
  `POST`. The value MUST be a valid HTTP method name.
- `headers`: An array of HTTP headers to use for the endpoint. HTTP allows for
  duplicate headers. The objects in the array have the following attributes:
  - `name`: The name of the HTTP header. The value MUST be a non-empty string.
  - `value`: The value of the HTTP header. The value MUST be a non-empty string.
- `query`: A map of HTTP query parameters to use for the endpoint. The value
  MUST be a map of non-empty strings to non-empty strings.

The values of all `query` and `headers` MAY contain placeholders using the
[RFC6570][RFC6570] Level 1 URI Template syntax. When the same placeholder is
used in multiple properties, the value of the placeholder is assumed to be
identical.

Example:

```JSON
{
  "protocol": "HTTP/1.1",
  "options": {
    "method": "POST",
    "headers": [
      {
        "name": "Content-Type",
        "value": "application/json"
      }
    ],
    "query": {
      "operation": "send"
    }
  }
}
```

##### AMQP options

The [endpoint URIs](#configendpoints) for "AMQP" endpoints MUST be valid AMQP
URIs using the "amqp" or "amqps" scheme. If the path portion of the URI is
present, it MUST be a valid AMQP node name.

The following options are defined for AMQP endpoints.

- `node`: The name of the AMQP node (a queue or topic or some addressable
  entity) to use for the endpoint. If present, the value overrides the path
  portion of the Endpoint URI.
- `durable`: If `true`, the AMQP `durable` flag is set on transfers. The default
  value is `false`. This option only applies to `usage:producer` endpoints.
- `link-properties`: A map of AMQP link properties to use for the endpoint. The
  value MUST be a map of non-empty strings to non-empty strings.
- `connection-properties`: A map of AMQP connection properties to use for the
  endpoint. The value MUST be a map of non-empty strings to non-empty strings.
- `distribution-mode`: Either `move` or `copy`. The default value is `move`. The
  distribution mode is AMQP's way of expressing whether a receiver operates on
  copies of messages (it's a topic subscriber) or whether it moves messages from
  the queue (it's a queue consumer). This option only applies to
  `usage:consumer` endpoints.

The values of all `link-properties` and `connection-properties` MAY contain
placeholders using the [RFC6570][RFC6570] Level 1 URI Template syntax. When the
same placeholder is used in multiple properties, the value of the placeholder is
assumed to be identical.

Example:

```JSON
{
  "usage": "producer",
  "protocol": "AMQP/1.0",
  "options": {
    "node": "myqueue",
    "durable": true,
    "link-properties": {
      "my-link-property": "my-link-property-value"
    },
    "connection-properties": {
      "my-connection-property": "my-connection-property-value"
    },
    "distribution-mode": "move"
  }
}
```

##### MQTT options

The [endpoint URIs](#configendpoints) for "MQTT" endpoints MUST be valid MQTT
URIs using the (informal) "mqtt" or "mqtts" scheme. If the path portion of the
URI is present, it MUST be a valid MQTT topic name. The informal schemes "tcp"
(plain TCP/1883), "ssl" (TLS TCP/8883), and "wss" (Websockets/443) MAY also be
used, but MUST NOT have a path.

The following options are defined for MQTT endpoints.

- `topic`: The MQTT topic to use for the endpoint. If present, the value
  overrides the path portion of the Endpoint URI. The value MAY contain
  placeholders using the [RFC6570][RFC6570] Level 1 URI Template syntax
- `qos`: The MQTT Quality of Service (QoS) level to use for the endpoint. The
  value MUST be an integer between 0 and 2. The default value is 0. The value is
  overidden by the `qos` property of the
  [MQTT message format](../message/spec.md#mqtt311-and-mqtt50).
- `retain`: If `true`, the MQTT `retain` flag is set on transfers. The default
  value is `false`. The value is overidden by the `retain` property of the [MQTT
  message format](../message/spec.md#mqtt311-and-mqtt50). This option only
  applies to `usage:producer` endpoints.
- `clean-session`: If `true`, the MQTT `clean-session` flag is set on
  connections. The default value is `true`.
- `will-topic`: The MQTT `will-topic` to use for the endpoint. The value MUST be
  a non-empty string. The value MAY contain placeholders using the
  [RFC6570][RFC6570] Level 1 URI Template syntax
- `will-message`: This is URI and/or JSON Pointer that refers to the MQTT
  `will-message` to use for the endpoint. The value MUST be a non-empty string.
  It MUST point to a valid
  [´definition´](../message/spec.md#message-definitions) that MUST either
  use the ["CloudEvents/1.0"](../message/spec.md#cloudevents10) or
  ["MQTT/3.1.1." or "MQTT/5.0"](../message/spec.md#mqtt311-and-mqtt50)
  [`format`](../message/spec.md#format-message-format).

Example:

```JSON
{
  "usage": "producer",
  "protocol": "MQTT/5.0",
  "options": {
    "topic": "mytopic",
    "qos": 1,
    "retain": false,
    "clean-session": false,
    "will-topic": "mytopic",
    "will-message": "#/definitionGroup/mygroup/definitions/my-will-message"
  }
}
```

##### KAFKA options

The [endpoint URIs](#configendpoints) for "Kafka" endpoints MUST be valid Kafka
bootstrap server addresses. The scheme follows Kafka configuration usage, e.g.
`SSL://{host}:{port}` or `PLAINTEXT://{host}:{port}`.

The following options are defined for Kafka endpoints.

- `topic`: The Kafka topic to use for the endpoint. The value MUST be a
  non-empty string if present. The value MAY contain placeholders using the
  [RFC6570][RFC6570] Level 1 URI Template syntax
- `acks`: The Kafka `acks` setting to use for the endpoint. The value MUST be an
  integer between -1 and 1. The default value is 1. This option only applies to
  `usage:producer` endpoints.
- `key`: The fixed Kafka key to use for this endpoint. The value MUST be a
  non-empty string if present. This option only applies to `usage:producer`
  endpoints. The value MAY contain placeholders using the
  [RFC6570][RFC6570] Level 1 URI Template syntax
- `partition`: The fixed Kafka partition to use for this endpoint. The value
  MUST be an integer if present. This option only applies to `usage:producer`
  endpoints.
- `consumer-group`: The Kafka consumer group to use for this endpoint. The value
  MUST be a non-empty string if present. This option only applies to
  `usage:consumer` endpoints. The value MAY contain placeholders using the
  [RFC6570][RFC6570] Level 1 URI Template syntax

Example:

```JSON
{
  "usage": "producer",
  "protocol": "Kafka/2.0",
  "options": {
    "topic": "mytopic",
    "acks": 1,
    "key": "mykey",
  }
}
```

##### NATS options

The [endpoint URIs](#configendpoints) for "NATS" endpoints MUST be valid NATS
URIs. The scheme MUST be "nats" or "tls" or "ws" and the URI MUST include a port
number, e.g. `nats://{host}:{port}` or `tls://{host}:{port}`.

The following options are defined for NATS endpoints.

- `subject`: The NATS subject to use. The value MAY contain placeholders using
  the [RFC6570][RFC6570] Level 1 URI Template syntax

Example:

```JSON
{
  "usage": "producer",
  "protocol": "NATS/1.0.0",
  "options": {
    "subject": "mysubject"
  }
}
```

## References

### CloudEvents Registry Document Schema

See [CloudEvents Registry Document Schema](../message/schemas/xregistry_messaging_catalog.json).

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
