# Endpoint Registry Service - Version 0.5-wip

## Abstract

This specification defines an endpoint registry existension to the xRegistry
document format and API [specification](../core/spec.md).


## Table of Contents

- [Overview](#overview)
- [Notations and Terminology](#notations-and-terminology)
  - [Notational Conventions](#notational-conventions)
  - [Terminology](#terminology)
- [Endpoint Registry](#endpoint-registry)
  - [Endpoints](#endpoints-endpoints)

## Overview

This specification defines a registry of metadata definitions for abstract and
concrete network endpoints to which messages can be produced, from which
messages can be consumed, or which make messages available for subscription.

For easy reference, the JSON serialization of an Endpoint Registry adheres to
this form:

```yaml
{
  "specversion": "STRING",
  "id": "STRING",
  "name": "STRING", ?
  "epoch": UINTEGER,
  "self": "URL",
  "description": "STRING", ?
  "documentation": "URL", ?
  "labels": { "STRING": "STRING" * }, ?

  "model": { ... }, ?

  "endpointsurl": "URL",
  "endpointscount": UINTEGER,
  "endpoints": {
    "ID": {
      "id": "STRING",                           # xRegistry core attributes
      "name": "STRING", ?
      "epoch": UINTEGER,
      "self": "URL",
      "description": "STRING", ?
      "documentation": "URL", ?
      "labels": { "STRING": "STRING" * }, ?
      "format": "STRING", ?
      "createdby": "STRING", ?
      "createdon": "TIME", ?
      "modifiedby": "STRING", ?
      "modifiedon": "TIME", ?

      "usage": "STRING",                        # subscriber, consumer, producer
      "origin": "URI", ?                        # default: 'self' URL
      "channel": "STRING", ?
      "deprecated": {
        "effective": "TIMESTAMP", ?
        "removal": "TIMESTAMP", ?
        "alternative": "URL", ?
        "docs": "URL"?
      }, ?

      "config": {
        "protocol": "STRING",
        "endpoints": [
          {
            "uri": "URI"                        # plus endpoint extensions
          } *
        ], ?
        "authorization": {
          "type": "STRING", ?
          "resourceurl": "URL", ?
          "authorityuri": "URI", ?
          "grant_types": [ "STRING" * ] ?
        }, ?
        "strict": BOOLEAN, ?

        "options": {
          "STRING": JSON-VALUE *

          # "http" protocol options
          "method": "STRING", ?                          # default: POST
          "headers": { { "name": "STRING", "value": "STRING" } * }, ?
          "query": { "STRING": "STRING" * } ?

          # "amqp" protocol options
          "node": "STRING", ?
          "durable": BOOLEAN, ?                          # default: false
          "link-properties": { "STRING": "STRING" * }, ?
          "connection-properties": { "STRING": "STRING" * }, ?
          "distribution-mode": "move" | "copy" ?         # default: "move"

          # "mqtt" protocol options
          "topic": "STRING", ?
          "qos": UINTEGER, ?                             # default: 0
          "retrain": BOOLEAN, ?                          # default: false
          "clean-session": BOOLEAN, ?                    # default: true
          "will-topic": "STRING", ?
          "will-message": "STRING" ?

          # "kafka" protocol options
          "topic": "STRING", ?
          "acks": INTEGER,                               # default: 1
          "key": "STRING", ?
          "partition": INTEGER, ?
          "consumer-group": "STRING" ?

          # "nats" protocol options
          "subject": "STRING" ?
        } ?
      }, ?

      "messagegroups": [ URI * ], ?

      "messagesurl": "URL", ?
      "messagescount": UINTEGER, ?
      "messages": {
        "ID": {
          # See Message Definition spec for details
        }, *
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

### Endpoint

An "endpoint" is a logical or physical network location to which messages can
be produced, from which messages can be consumed, or which makes messages
available for subscription for delivery to a consumer-designated endpoint.

## Endpoint Registry

The Endpoint Registry is a registry of metadata definitions for abstract and
concrete network endpoint to which messages can be produced, from which messages
can be consumed, or which makes messages available for subscription and
delivery to a consumer-designated endpoint.

As discussed in [CloudEvents Registry overview](../cloudevents/spec.md),
endpoints are supersets of
[message definition groups](../message/spec.md#message-definition-groups) and
MAY contain inlined messages. Therefore, the RESOURCE level in the meta-model
for the Endpoint Registry are likewise `messages` as defined in the
[message catalog specification](../message/spec.md).

The resource model for endpoints can be found in [model.json](model.json).

### Endpoints: endpoints

A Group (GROUP) name is `endpoints`. The type of a group is `endpoint`.

The following attributes are defined for the `endpoint` type:

#### `usage`

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

  - `consumer`: The endpoint offers messages being consumed from it.

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

### `origin`

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

### `channel`

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

### `deprecated`

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

#### `config`

- Type: Map
- Description: Configuration details of the endpoint. An endpoint
  MAY be defined without detail configuration. In this case, the endpoint is
  considered to be "abstract".

- Constraints:
  - OPTIONAL

#### `config.protocol`

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

#### `config.endpoints`

- Type: Array of Objects
- Description: An array of objects map where each object contains a `uri`
  attribute with the the network address to which clients can communicate with
  the endpoint. The object MAY contain extension attributes that can be used
  by clients to determine which URI to use, or to configure access to the
  specific URI. Whether the URI identifies a network host or links directly to
  a resource managed by the network host is protocol specific.
- Constraints:
  - OPTIONAL
  - Each object key MUST contain a `uri` attirbute with a valid, absolute
    URI (URL)
- Examples:
  - `[ {"uri": "https://example.com" } ]`
  - ```
    [
      { "uri": "tcp://example.com" },
      { "uri": "wss://example.com" }
    ]
    ```
  - ```
    [
      {
        "uri": "tcp://example.com",
        "priority": 1,
        "status": "down"
      },
      {
        "uri": "wss://example.com",
        "priority": 2,
        "status": "up"
      }
    ]
    ```

#### `config.authorization`

- Type: Map
- Description: OPTIONAL authorization configuration details of the endpoint.
  When present, the authorization configuration MUST be a map of non-empty
  strings to non-empty strings. The configuration keys below MUST be used as
  defined. Additional, endpoint-specific configuration keys MAY be added.

- Constraints:
  - OPTIONAL
  - MUST only be used for authorization configuration
  - MUST NOT be used for credential configuration

#### `config.authorization.type`

- Type: String
- Description: The type of the authorization configuration. The value SHOULD be
  one of the following:
  - OAuth2: OAuth 2.0 authorization is used.
  - Plain: The client uses username with a plaintext password for authentication
    and authorization.
  - X509Cert: The client uses client certificate authentication and authorization.
  - APIKey: The client uses an API key for authentication and authorization.

- Constraints:
  - OPTIONAL
  - MUST be a non-empty string if used

#### `config.authorization.resourceuri`

- Type: URI
- Description: The URI of the resource for which the authorization is
  requested. The format of the URI depends on the authorization type.

- Constraints:
  - OPTIONAL
  - MUST be a non-empty URI if used

#### `config.authorization.authorityuri`

- Type: URI
- Description: The URI of the authorization authority from which the
  authorization is requested. The format of the URI depends on the authorization
  type.

- Constraints:
  - OPTIONAL
  - MUST be a non-empty URI if used

#### `config.authorization.grant_types`

- Type: Array of Strings
- Description: The supported authorization grant types. The value SHOULD be a
  list of strings.

- Constraints:
  - OPTIONAL
  - MUST be a non-empty array if used

#### `config.strict`

- Type: Boolean
- Description: If `true`, the endpoint metadata represents a public, live
  endpoint that is available for communication and a strict validator MAY test
  the liveness of the endpoint.
- Constraints:
  - OPTIONAL.
  - Default value is `false`.

#### `config.options`

- Type: Map
- Description: Additional configuration options for the endpoint. The
  configuration options are protocol specific and described in the
  [protocol options](#protocol-options) section below.
- Constraints:
  - OPTIONAL
  - When present, MUST be a map of non-empty strings to `ANY` type values.
  - If `config.protocol` is a well-known protocol, the options MUST be
    compliant with the [protocol's options](#protocol-options).

#### `messages` (Endpoint)

Endpoints are supersets of
[message definition groups](../message/spec.md#message-definition-groups) and
MAY contain inlined messages. See
[Message Definitions](../message/spec.md#message-definitions).

Example:

```yaml
{
  "protocol": "HTTP/1.1",
  "options": {
    "method": "POST"
  },

  "messagesurl": "...",
  "messagescount": 1,
  "messages": {
    "myevent": {
      "format": "CloudEvents/1.0",
      "metadata": {
        "attributes": {
          "type": {
            "value": "myevent"
          }
        }
      }
    }
  }
}
```

#### `messagegroups` (Endpoint)

The `messagegroups` attribute is an array of URI-references to message
definition groups. The `messagegroups` attribute is used to reference
message definition groups that are not inlined in the endpoint definition.

Example:

```yaml
{
  "protocol": "HTTP/1.1",
  "options": {
    "method": "POST"
  },
  "messagegroups": [
    "https://example.com/registry/messagegroups/mygroup"
  ]
}
```

#### Protocol Options

The following protocol options (`config.options`) are defined for the respective
protocols. All of these are OPTIONAL.

##### HTTP options

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

```yaml
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

#### AMQP options

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

```yaml
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

#### MQTT options

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
  [MQTT message format](../message/spec.md#mqtt311-and-mqtt50-bindings).
- `retain`: If `true`, the MQTT `retain` flag is set on transfers. The default
  value is `false`. The value is overidden by the `retain` property of the [MQTT
  message format](../message/spec.md#mqtt311-and-mqtt50-bindings). This option only
  applies to `usage:producer` endpoints.
- `clean-session`: If `true`, the MQTT `clean-session` flag is set on
  connections. The default value is `true`.
- `will-topic`: The MQTT `will-topic` to use for the endpoint. The value MUST be
  a non-empty string. The value MAY contain placeholders using the
  [RFC6570][RFC6570] Level 1 URI Template syntax
- `will-message`: This is URI and/or JSON Pointer that refers to the MQTT
  `will-message` to use for the endpoint. The value MUST be a non-empty string.
  It MUST point to a valid
  [´message´](../message/spec.md#message-definitions) that MUST either
  use the ["CloudEvents/1.0"](../message/spec.md#cloudevents10) or
  ["MQTT/3.1.1." or "MQTT/5.0"](../message/spec.md#mqtt311-and-mqtt50-bindings)
  [`format`](../message/spec.md#format-metadata-format).

Example:

```yaml
{
  "usage": "producer",
  "protocol": "MQTT/5.0",
  "options": {
    "topic": "mytopic",
    "qos": 1,
    "retain": false,
    "clean-session": false,
    "will-topic": "mytopic",
    "will-message": "#/messagegroups/mygroup/messages/my-will-message"
  }
}
```

#### KAFKA options

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

```yaml
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

#### NATS options

The [endpoint URIs](#configendpoints) for "NATS" endpoints MUST be valid NATS
URIs. The scheme MUST be "nats" or "tls" or "ws" and the URI MUST include a port
number, e.g. `nats://{host}:{port}` or `tls://{host}:{port}`.

The following options are defined for NATS endpoints.

- `subject`: The NATS subject to use. The value MAY contain placeholders using
  the [RFC6570][RFC6570] Level 1 URI Template syntax

Example:

```yaml
{
  "usage": "producer",
  "protocol": "NATS/1.0.0",
  "options": {
    "subject": "mysubject"
  }
}
```

## References


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
