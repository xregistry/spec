# Endpoint Registry Service - Version 1.0-rc3
<!-- words: apikeyname apikeyin plainscheme plainusernamefield plainpasswordfield sasl oauthbearer -->

## Abstract

This specification defines an endpoint registry extension to the xRegistry
document format and API [specification](../core/spec.md). An endpoint registry
allows for publishing and discovery of asynchronous event sources, sinks, and
subscription points in the scope of a system, along with important
configuration parameters.

## Table of Contents

- [Overview](#overview)
- [Notations and Terminology](#notations-and-terminology)
  - [Notational Conventions](#notational-conventions)
  - [Terminology](#terminology)
- [Endpoint Registry](#endpoint-registry-model)
  - [Endpoints](#endpoints-groups)

## Overview

This specification defines a registry of metadata definitions for abstract and
concrete network endpoints to which messages can be produced, from which
messages can be consumed, or which make messages available for subscriptions.

The metadata model defined in this specification is specifically focused on
describing unidirectional endpoints for asynchronous information flows like
discrete events, event streams, queueing, and publish/subscribe patterns.

Endpoint information is provided through the registry for discovery of
endpoints, dynamic configuration of clients, and code generation.

The model allows for a loose correlation of endpoints through a `channel`
concept, to designate, for instance, the input and output ends of a queue, but
it intentionally avoids being specific about the shape of messaging and
eventing entities. The correlation of endpoints for the purposes of realizing
specific message exchange patterns like request/response or scatter/gather is
also intentionally out of scope for this metadata model, because modeling such
correlation contracts with sufficient depth is a whole additional definition
layer above what this model aims to achieve.

The goal of this endpoint metadata model is to provide metadata structure to
asynchronous topics and streams and queues in a way that is similar to how
table and column definitions provide structure to databases. Database schemas
structure data that you have. Endpoint definitions with their referenced or
embedded message definitions with referenced or embedded schema definitions
structure data that you will yet receive.

Continuing that analogy, the endpoint scope corresponds to the database, the
message groups are schema scopes, and the message definitions correspond to
tables. The schema associated with a message definition determines the column
layout of the table. As event streams often end up landing in databases for
long-term archival and analysis, this structural alignment is very helpful.

### Endpoints

In a distributed system, the networked input sinks and output sources of an
application, or an application infrastructure component like an event broker,
are commonly called “endpoints”. Those endpoints serve as communication
conduits to make information available to the application, or for the
application to make information available to others.

In this specification we distinguish three distinct `usage` roles for
endpoints:

- `producer`: A producer endpoint is made available by a consumer or
  intermediary (like an application or a queue) to a producer, so that the
  producer can send events/messages to the endpoint. Those events/messages
  MUST conform to the declared constraints. If the endpoint is associated with
  at least one message group, only messages/events that match one of the
  declared message definitions can be sent. If the message definition
  references a data schema, the message payload MUST match that schema.

- `consumer`: A consumer endpoint is made available by a producer or
  intermediary for a consumer to retrieve messages/events from. Examples for
  these are queues or consumer groups on streams, but also peer-to-peer
  endpoints exposed by applications.

- `subscriber`: A subscriber endpoint is made available to consumers for the
  purpose of setting up their own consumer endpoint. The
  [CloudEvents Subscriptions API](https://github.com/cloudevents/spec/blob/main/subscriptions/spec.md)
  specification enumerates the subscription mechanisms intended for these
  endpoints. As subscription mechanisms can vary substantially across products
  that implement the same protocol, it is RECOMMENDED to use the `label`
  mechanism to identify the specific product that provides the endpoint.

Each endpoint definition defines a `protocol` selector by which the specific
network application protocol is chosen to communicate with the endpoint. If a
networked entity supports multiple protocols, each protocol endpoint MUST be
declared separately, even if those are multiplexed over the same port. For
instance, if you have an MQTT broker that can dynamically select between
MQTT 3.1.1 and MQTT 5.0, those endpoints are to be declared separately as
the capabilities differ substantially.

The `protocol` selector value determines which `protocoloptions` become
available to define for the endpoint. The protocol-specific options are
enumerated and explained in [protocol options](#protocol-options).

Each endpoint MAY also define an `envelope` selector which allows for defining
particular `envelopeoptions` at the endpoint level. For CloudEvents, this
permits the definition of the serialization mode (binary or structured) and the
event format for structured mode.

### Message Groups

The Endpoint is an xRegistry group-level construct that is conceptually an
extension of the [message definition group](../message/spec.md), meaning there
are no “groups of endpoints”. An endpoint MAY contain directly embedded
message definitions. In the simplest case, an endpoint MAY embed its message
definitions locally which in turn MAY embed their data schema definitions
locally, all in one compact construct.

More commonly, Endpoints will reference one or more
[message definition groups](../message/spec.md) that are defined externally in
a message registry, and which have the advantage of being shareable across
multiple Endpoints.

For describing a message broker queue, the best approach is to define a
message group that defines the messages that are be allowed to flow on the
queue and for that message group to then be referenced from the `producer` and
the `consumer` endpoints of the queue, whereby both of those endpoints share
the same `channel` identifier.

In the endpoint context, message groups have a function similar to interfaces
in programming languages. They define related sets of messages that can be
associated with an endpoint all at once.

### Scenarios

Endpoint definitions can be abstract or concrete, distinguished by the
`deployed` flag. If the `deployed` flag is set to `true`, one can expect the
endpoint to be reachable on the network with the given parameters, assuming
the client is within the same network scope. If the flag is set to `false`,
the endpoint definition is to be treated like a template where configuration
elements like the endpoint URI will have to be supplied by external
configuration for the client to become functional.

A possible application of the latter are Endpoint definitions that define
endpoint patterns as they are common for applications of the MQTT protocol.
For instance, the [Eclipse Sparkplug](https://sparkplug.eclipse.org/) protocol
is a convention that defines endpoint roles and messages and schemas for MQTT,
and the
[SparkPlugB](../cloudevents/samples/scenarios/mqtt-sparkplugB.xreg.json)
example that illustrates how Registry Endpoints can model the convention in
formal terms.

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

### Endpoint

An "endpoint" is a logical or physical network location to which messages can
be produced, from which messages can be consumed, or which makes messages
available via subscription for delivery to a consumer-designated endpoint.

## Endpoint Registry Model

The Endpoint Registry is a registry of metadata definitions for abstract and
concrete network endpoints to which messages can be produced, from which
messages can be consumed, or which makes messages available via subscription
and delivery to a consumer-designated endpoint.

As discussed in the [CloudEvents Registry overview](../cloudevents/spec.md),
endpoints are supersets of
[message definition groups](../message/spec.md#message-definition-groups) and
MAY contain inlined messages. Therefore, the Resources in the meta-model for
the Endpoint Registry are likewise `messages` as defined in the
[message catalog specification](../message/spec.md).

The formal xRegistry extension model of the Endpoints Registry
resides in the [model.json](model.json) file.

For easy reference, the JSON serialization of an Endpoint Registry adheres to
this form:

```yaml
{
  "specversion": "<STRING>",
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

  "endpointsurl": "<URL>",
  "endpointscount": <UINTEGER>,
  "endpoints": {
    "<KEY>": {
      "endpointid": "<STRING>",                   # xRegistry core attributes
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

      "usage": [ "<STRING>" + ] ,                 # subscriber, consumer, producer
      "channel": "<STRING>", ?

      # Start of Endpoint extension attributes
      "envelope": "<STRING>", ?                   # e.g. CloudEvents/1.0
      "envelopeoptions": {
        "<STRING>": <JSON-VALUE> *

        # CloudEvents/1.0 options
        "mode": "<STRING>", ?                     # binary, structured
        "format": "<STRING>" ?                    # e.g. application/json
      },

      "protocol": "<STRING>", ?                   # e.g. HTTP/1.1
      "protocoloptions": {
        "<STRING>": <JSON-VALUE> *

        # Common protocol options
        "endpoints": [
          {
            "uri": "<URI>"                        # plus endpoint extensions
          } *
        ], ?
        "authorization": [
          {
            "type": "<STRING>", ?
            "mechanism": "<STRING>", ?
            "resourceuri": "<URI>", ?
            "authorityuri": "<URI>" ?
          } *
        ], ?
        "deployed": <BOOLEAN>, ?

        # "HTTP" protocol options
        "method": "<STRING>", ?                          # Default: POST
        "headers": [ { "name": "<STRING>", "value": "<STRING>" } * ], ?
        "query": { "<STRING>": "<STRING>" * }, ?
        "apikeyname": "<STRING>", ?
        "apikeyin": "header" | "query" ?,              # Default: header
        "plainscheme": "basic" | "form" | "query" ?, # Default: basic
        "plainusernamefield": "<STRING>", ?
        "plainpasswordfield": "<STRING>" ?

        # "AMQP/1.0" protocol options
        "node": "<STRING>", ?
        "durable": <BOOLEAN>, ?                          # Default: false
        "link-properties": { "<STRING>": "<STRING>" * }, ?
        "connection-properties": { "<STRING>": "<STRING>" * }, ?
        "distribution-mode": "move" | "copy" ?,         # Default: move
        "connection-capabilities": [ "<STRING>" * ], ?
        "node-capabilities": [ "<STRING>" * ], ?
        "source-filters": { "<STRING>": <JSON-VALUE> * }, ?
        "dynamic": <BOOLEAN>, ?
        "terminus-durability": "none" | "configuration" | "unsettled-state" ?,
        "expiry-policy": "link-detach" | "session-end" | "connection-close" | "never" ?,
        "timeout": <UINTEGER>, ?
        "sender-settle-mode": "unsettled" | "settled" | "mixed" ?,
        "receiver-settle-mode": "first" | "second" ?

        # "MQTT/3.1.1" protocol options
        "topic": "<STRING>", ?
        "qos": <UINTEGER>, ?                             # Default: 0
        "retain": <BOOLEAN>, ?                           # Default: false
        "cleansession": <BOOLEAN>, ?                     # Default: true
        "topicfilter": "<STRING>", ?
        "willtopic": "<STRING>", ?
        "willmessage": "<XID>" ?

        # "MQTT/5.0" protocol options
        "topic": "<STRING>", ?
        "qos": <UINTEGER>, ?                             # Default: 0
        "retain": <BOOLEAN>, ?                           # Default: false
        "topicfilter": "<STRING>", ?
        "cleanstart": <BOOLEAN>, ?
        "sessionexpiryinterval": <UINTEGER>, ?
        "sharedsubscriptiongroup": "<STRING>", ?
        "nolocal": <BOOLEAN>, ?
        "retainaspublished": <BOOLEAN>, ?
        "retainhandling": 0 | 1 | 2 ?,
        "willtopic": "<STRING>", ?
        "willmessage": "<XID>" ?

        # "KAFKA" protocol options
        "topic": "<STRING>", ?
        "acks": <INTEGER>, ?                             # Default: 1
        "key": "<STRING>", ?
        "partition": <INTEGER>, ?
        "consumergroup": "<STRING>", ?
        "headers": { "<STRING>": "<STRING>" * }, ?
        "keyserializer": "<STRING>", ?
        "valueserializer": "<STRING>", ?
        "autooffsetreset": "earliest" | "latest" | "none" ?,
        "enableautocommit": <BOOLEAN> ?

        # "NATS" protocol options
        "subject": "<STRING>", ?
        "subjectfilter": "<STRING>", ?
        "queuegroup": "<STRING>" ?
      }, ?

      "messagegroups": [ XID * ], ?
      # End of Endpoint extensions

      "messagesurl": "<URL>", ?
      "messagescount": <UINTEGER>, ?
      "messages": {
        "<KEY>": {                                # messageid
          # See Message Definition spec for details
        } *
      } ?
    } *
  } ?
}
```

### Endpoints Groups

The Group plural name (`<GROUPS>`) is `endpoints`, and the Group singular
name (`<GROUP>`) is `endpoint`.

The following attributes are defined for the `endpoint` object in addition
to the xRegistry-defined core
[attributes](../core/spec.md#attributes-and-extensions):

#### `usage`

- Type: Array of String (Enum: `subscriber`, `consumer`, `producer`)
- Description: The `usage` attribute is a set of strings that indicates the
  intended usage of the endpoint by communicating parties. In other words, the
  roles a client can act in when talking with the endpoint.

  Each of these parties will have a different perspective on an endpoint. For
  instance, a `producer` endpoint is seen as a "target" by the originator of
  messages, and as a "source" by the party that accepts the messages. The
  nomenclature used for the `usage` field is primarily oriented around the
  common scenario of network endpoints being provided by some sort of
  intermediary like a message broker. The term `producer` primarily describes
  the relationship of a client with that intermediary.

  In a direct-delivery scenario where the originator of messages connects
  directly to the target (e.g. a "WebHook" call), the target endpoint
  implements the accepting end of the `producer` relationship.

  Some of these perspectives are mentioned below for illustration, but not
  formally defined or reflected in the metadata model. Perspectives depend on
  the context in which the endpoint metadata is used and this metadata model is
  intentionally leaving perspectives open to users.

  The following values are defined for `usage`

  - `subscriber`: The endpoint offers managing subscriptions for delivery of
    messages to another endpoint, using the [CloudEvents Subscriptions
    API][CloudEvents Subscriptions API].

    Some perspectives that might exist on a subscriber endpoint:
    - Application from which messages originate.
    - Application which accepts messages from the delivery agent.
    - Application which manages subscriptions for delivery of messages to the
      target application. This might be a message broker subscription manager.

  - `consumer`: The endpoint offers messages being consumed (pulled) from it.

    Some perspectives that might exist on a consumer endpoint:
    - Message store or source which makes messages available for consumption;
      this might be a message broker topic or a queue.
    - Proxy or other intermediary which solicits messages from the source and
      forwards them to the target endpoint.
    - Application which consumes messages.

  - `producer`: The endpoint offers messages being produced (pushed) to it.

    Some perspectives might exist on a producer endpoint:
    - Application from which messages originate.
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
  - MUST contain only the following possible values:
    - "subscriber"
    - "consumer"
    - "producer"
  - MUST be an array of at least one.
  - SHOULD declare exactly one usage value per endpoint.
  - Mixed usage declarations SHOULD be used only when the same protocol
    interface and the same endpoint contract unambiguously serve each declared
    role.
  - Declarations that mix `producer` with any other role are strongly
    discouraged. Prefer separate endpoint declarations, connected with a shared
    `channel` when correlation is useful.

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

  This specification does not make any statement about whether two endpoints
  that do not share the same non-empty value have any relationship or not.
  They might, but how this is determined is out of scope of this specification.
  Additionally, while it is expected that this attribute's value will be a
  single value, given this specification does not place any constraints on
  its syntax or semantic meaning, implementations might choose to "encode"
  multiple values within this single string. That would then imply that the
  comparison algorithm of two `channel` values might need to be more
  complicated than a "string compare" in those cases.

- Constraints:
  - OPTIONAL.
  - When specified, the value MUST be a non-empty string.
- Examples:
  - `queue1`

#### `envelope`

- Type: String
- Description: The name of the specification that defines the Resource
  stored in the registry. Often it is difficult to unambiguously determine
  what a Resource is by simply inspecting its serialized form. This attribute
  provides a mechanism by which it can be determined without examination of
  the Resource at all.
- Constraints:
  - MUST be a non-empty case-insensitive string of the form
    `<SPEC>[/<VERSION>]`,
    where `<SPEC>` is the non-empty string name of the specification that
    defines the Resource. An OPTIONAL `<VERSION>` value SHOULD be included if
    there are multiple versions of the specification available.
  - If a `<VERSION>` is specified at the Group level, all Resources within that
    Group MUST have a `<VERSION>` value that is at least as precise as its
    Group, and MUST NOT expand it. For example, if a Group had a
    `envelope` value of `myspec`, then Resources within that Group can have
    `envelope` values of `myspec` or `myspec/1.0`. However, if a Group has a
    value of `myspec/1.0`, it would be invalid for a Resource to have a value
    of `myspec/2.0` or just `myspec`. Additionally, if a Group does not have
    a `envelope` attribute then there are no constraints on its Resources
    `envelope` attributes.
  - This specification places no restriction on the syntax of the
    `<VERSION>` value.
- Examples:
  - `CloudEvents/1.0`

#### `envelopeoptions`

- Type: Map
- Description: Configuration details of the endpoint with respect to the
  envelope format used to transmit the messages.

- Constraints:
  - OPTIONAL.
- Examples:
  - For an endpoint using an `envelope` value of `CloudEvents/1.0`:
    `{ "mode": "binary", "format": "application/json" }`

This specification defines the following envelope options for the indicated
`envelope` values:

##### `CloudEvents/1.0`

- `mode` : indicates whether the CloudEvent will use `binary` or `structured`
  (mode)[https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md#message].
  When specified, its value MUST be one of: `binary` or `structured`, case
  sensitive. When not specified, the endpoint is indicating that either mode
  is acceptable.
- `format` : indicates the format of the CloudEvent when sent in `structured`
  mode. This attribute MUST NOT be specified when `mode` is `binary`. The value
  used MUST match the expected content type of the message (e.g. for HTTP the
  `Content-Type` header value).

#### `protocol`

- Type: String
- Description: The transport or application protocol used by the endpoint. This
  specification defines a set of common protocol names that MUST be used for
  respective protocol endpoints, but implementations MAY define and use
  additional protocol names.

  An example for an extension protocol identifier might be "BunnyMQ/0.9.1".

  Predefined protocols SHOULD be referred to by name and version as
  `<NAME>/<VERSION>`. The version number format is determined by the protocol
  specification's usage of versions. If the version is not specified, the
  default version of the protocol is assumed. For AMQP and MQTT, see the list
  below. For others, refer to the protocol specifications.

  The predefined protocol names are:
  - "HTTP" - Used for HTTP/1.1, HTTP/2, HTTP/3.
  - "AMQP/1.0" - Use the [AMQP 1.0][AMQP 1.0] protocol. MAY be shortened to
    "AMQP". AMQP draft versions before 1.0 (e.g. 0.9) are *not* AMQP.
  - "MQTT/3.1.1", "MQTT/5.0" - Use the MQTT [3.1.1][MQTT 3.1.1] or [5.0][MQTT
    5.0] protocol. The shorthand "MQTT" maps to "MQTT/5.0".
  - "NATS" - Use the [NATS][NATS] protocol.
  - "KAFKA" - Use the [Apache Kafka][Apache Kafka] protocol.

  All messages inside an Endpoint MUST use this same protocol.
- Constraints:
  - MUST be a non-empty case-insensitive string.
  - SHOULD follow the naming convention `<NAME>/<VERSION>`,
    whereby `<NAME>` is the name of the protocol and `<VERSION>` is the
    version of protocol.
- Examples:
  - `MQTT/3.1.1`
  - `AMQP/1.0`
  - `KAFKA`

#### `protocoloptions`

- Type: Map
- Description: Configuration details of the endpoint related to the protocol
  used to transmit the messages. An endpoint MAY be defined without detail
  configuration. In this case, the endpoint is considered to be "abstract".
  For per-protocol option definitions, see [Protocol Options](#protocol-options).

- Constraints:
  - OPTIONAL.

##### `protocoloptions.endpoints`

- Type: Array of Objects
- Description: An array of objects map where each object contains a `uri`
  attribute with the network address to which clients can communicate with
  the endpoint. The object MAY contain extension attributes that can be used
  by clients to determine which URI to use, or to configure access to the
  specific URI. Whether the URI identifies a network host or links directly to
  a resource managed by the network host is protocol specific.
- Constraints:
  - OPTIONAL.
  - Each object MUST contain a `uri` attribute with a valid, absolute URI (URL).
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

##### `protocoloptions.authorization`

- Type: Map
- Description: OPTIONAL authorization configuration details of the endpoint.
  When specified, the authorization configuration MUST provide sufficient
  metadata for clients to select the authorization mechanism
  and discover where authorization is obtained. Runtime credentials and
  deployment-specific values are expected to be supplied separately through
  external configuration. The configuration keys below MUST be used as
  defined. Additional endpoint-specific configuration keys MAY be added.

- Constraints:
  - OPTIONAL.
  - MUST only be used for authorization configuration.
  - MUST NOT be used for credential configuration.

###### `protocoloptions.authorization.type`

- Type: String
- Description: The type of the authorization configuration. The value SHOULD be
  one of the following:
  - `OAuth2`: OAuth 2.0 authorization is used. The `authorityuri` SHOULD
    reference authorization server metadata as defined by RFC 8414.
  - `Plain`: The client uses username with a plaintext password for
    authentication and authorization. For HTTP, see protocol options
    `plainscheme`, `plainusernamefield`, and `plainpasswordfield`; for other
    protocols, equivalent transport-specific options MAY be defined as
    protocol extensions.
  - `SASL`: The client uses a SASL authentication mechanism. The
    `mechanism` attribute SHOULD be provided when this type is selected.
  - `X509Cert`: The client uses client certificate authentication and
    authorization.
  - `APIKey`: The client uses an API key for authentication and
    authorization. For HTTP, see protocol options `apikeyname` and
    `apikeyin`; for other protocols, equivalent carrier-specific options MAY
    be defined as protocol extensions.

- Constraints:
  - OPTIONAL.
  - MUST be a non-empty string if used.

- Examples:
  - `OAuth2`: `{ "type": "OAuth2", "authorityuri": "https://login.example.com/tenant/v2.0" }`.
    This points clients to the OAuth 2.0 authorization server/issuer metadata.
  - `Plain`: `{ "type": "Plain", "authorityuri": "https://docs.example.com/auth/plain" }`.
    This points clients to product documentation for username/password-based authorization setup.
  - `SASL`: `{ "type": "SASL", "mechanism": "SCRAM-SHA-256", "authorityuri": "https://docs.example.com/auth/sasl" }`.
    This points clients to mechanism-specific setup guidance (for example SASL profile and parameter requirements).
  - `X509Cert`: `{ "type": "X509Cert", "authorityuri": "https://docs.example.com/auth/x509" }`.
    This points clients to certificate enrollment and trust-chain requirements.
  - `APIKey`: `{ "type": "APIKey", "authorityuri": "https://docs.example.com/auth/apikey" }`.
    This points clients to key provisioning and placement guidance (for example header/query usage).

###### `protocoloptions.authorization.mechanism`

- Type: String
- Description: The SASL mechanism name for `authorization.type = "SASL"`
  (for example `PLAIN`, `SCRAM-SHA-256`, `SCRAM-SHA-512`, `OAUTHBEARER`,
  or `EXTERNAL`).

- Constraints:
  - OPTIONAL.
  - MUST be a non-empty string if used.
  - MUST only be used when `protocoloptions.authorization.type` is `SASL`.

###### `protocoloptions.authorization.resourceuri`

- Type: URI
- Description: The URI of the resource for which the authorization is
  requested. The format of the URI depends on the authorization type.

- Constraints:
  - OPTIONAL.
  - MUST be a non-empty URI if used.

###### `protocoloptions.authorization.authorityuri`

- Type: URI
- Description: The URI of the authorization authority from which the
  authorization is requested. The format of the URI depends on the
  authorization type.

- Constraints:
  - OPTIONAL.
  - MUST be a non-empty URI if used.

##### `protocoloptions.deployed`

- Type: Boolean
- Description: If `true`, the endpoint metadata represents a public, live
  endpoint that is expected to be available for communication.
- Constraints:
  - OPTIONAL.
  - If present, MUST be either `true` or `false`, case-sensitive.
  - When not specified, the default value is MUST be `true`.

Protocol-specific options are direct children of `protocoloptions`.
There is no nested `protocoloptions.options` object.

#### `messagegroups`

The `messagegroups` attribute is an array of XID-references to message
definition groups. The `messagegroups` attribute is used to reference
message definition groups that are not inlined in the endpoint definition.

Example:

```yaml
{
  "protocol": "HTTP/1.1",
  "protocoloptions": {
    "method": "POST"
  },
  "messagegroups": [
    "/messagegroups/mygroup"
  ]
}
```

#### `messages`

Endpoints are supersets of
[message definition groups](../message/spec.md#message-definition-groups) and
MAY contain inlined messages. See
[Message Definitions](../message/spec.md#message-definitions).

Example:

```yaml
{
  "protocol": "HTTP/1.1",
  "protocoloptions": {
    "method": "POST"
  },

  "messagesurl": "...",
  "messagescount": 1,
  "messages": {
    "myevent": {
      "envelope": "CloudEvents/1.0",
      "envelopemetadata": {
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

When this specification, and the [message specification](../message/spec.md),
are used with specifications such as [CloudEvents](https://cloudevents.io),
where a semantically unique identifier is used in a runtime message (e.g.
CloudEvent's `type` attribute), it is STRONGLY RECOMMENDED that the
`messageid` values of the message definitions for an Endpoint match that
unique identifier and therefore be unique across all messages within the
`messages` collection and the messages referenced by the `messagegroups`
attribute. This will allow for an easy "lookup" from an incoming runtime
message to its related message definition.

However, there are times when this is not possible. For example, take the case
where an Endpoint might have the same semantic message defined twice, once for
a JSON serialization and once for an XML serialization. Using the same
`messageid` value is not possible (even though the CloudEvent `type` attribute
would be the same for both runtime messages), so one (or both) message
definition's `messageid` values might not match the runtime message's `type`
value. In those cases, finding the appropriate message definition will need to
be done via examination of some other metadata - such as the message's
`envelopemetadata.type` value along with its `envelopeoptions.format` value.
These details are out of scope for this specification to define and are left as
an implementation detail.

Implementations MAY choose to generate an error if it detects duplicate
`messageid` values across the `messages` collection message definitions and
the `messagegroups` referenced message definitions, if that is the desired
constraint for their users.

#### Protocol Options

The following protocol options are direct children of `protocoloptions` for
the respective protocols. All of these are OPTIONAL.

This specification is primarily descriptive for protocol options: it guides
clients on how to interpret metadata. It does not require a validator to reject
every role-inapplicable option.

In each table below, role applicability is shown as:
- `✓`: The option applies to that role. Clients acting in that role SHOULD
  apply the option semantics.
- `-`: The option does not apply to that role.

##### HTTP options

The [endpoint URIs](#protocoloptionsendpoints) for "HTTP" endpoints MUST be
valid HTTP URIs using the "http" or "https" scheme as defined in
[HTTP Message Format].

HTTP commonly uses separate endpoint declarations for subscriber, consumer,
and producer interactions.

| Name | Type | P | C | S | Description |
|---|---|---|---|---|---|
| `method` | string (HTTP method), default `POST` | ✓ | ✓ | ✓ | HTTP method for the concrete operation represented by the endpoint. |
| `headers` | array of `{name: string, value: string}` | ✓ | ✓ | ✓ | HTTP request headers. Duplicate names are allowed. |
| `query` | map of string to string | ✓ | ✓ | ✓ | HTTP query parameters for the operation. |
| `apikeyname` | string | ✓ | ✓ | ✓ | Name of the API key carrier when `authorization.type` is `APIKey` (for example `x-api-key`). |
| `apikeyin` | enum: `header`, `query`, default `header` | ✓ | ✓ | ✓ | Placement of API key metadata when `authorization.type` is `APIKey`. `header` SHOULD be used; `query` SHOULD only be used when header placement is not possible. |
| `plainscheme` | enum: `basic`, `form`, `query`, default `basic` | ✓ | ✓ | ✓ | Transport pattern for `authorization.type` = `Plain`. `basic` refers to HTTP Basic authentication ([RFC7617][RFC7617]). |
| `plainusernamefield` | string | ✓ | ✓ | ✓ | Parameter or header field name carrying the username when `plainscheme` is `form` or `query`. |
| `plainpasswordfield` | string | ✓ | ✓ | ✓ | Parameter or header field name carrying the password when `plainscheme` is `form` or `query`. |

The values of all `query` and `headers` MAY contain placeholders using the
[RFC6570][RFC6570] Level 1 URI Template syntax. When the same placeholder is
used in multiple properties, the value of the placeholder is assumed to be
identical.

These options only define protocol-level placement and naming metadata.
Credential values (API keys, usernames, passwords) MUST NOT be stored in
endpoint metadata and MUST be supplied out-of-band.

##### AMQP options

The [endpoint URIs](#protocoloptionsendpoints) for "AMQP" endpoints MUST be
valid AMQP URIs using the "amqp" or "amqps" scheme. If the path portion of the
URI is present, it MUST be a valid AMQP node name according to
[AMQP Addressing Version 1.0].

The following options are defined for AMQP endpoints.

| Name | Type | P | C | S | Description |
|---|---|---|---|---|---|
| `node` | string | ✓ | ✓ | ✓ | AMQP node (address). When set, it overrides the URI path. |
| `durable` | boolean, default `false` | ✓ | - | - | AMQP durable flag. This does not imply a delivery guarantee and is distinct from terminus durability. |
| `link-properties` | map of string to string | ✓ | ✓ | ✓ | AMQP link properties. |
| `connection-properties` | map of string to string | ✓ | ✓ | ✓ | AMQP connection properties. |
| `distribution-mode` | enum: `move`, `copy`, default `move` | - | ✓ | - | AMQP receive distribution mode. |
| `connection-capabilities` | array of string | ✓ | ✓ | ✓ | AMQP connection capabilities. |
| `node-capabilities` | array of string | ✓ | ✓ | ✓ | AMQP node capabilities. |
| `source-filters` | map of string to any | - | ✓ | ✓ | AMQP source filter expressions/descriptor keys for receive setup. |
| `dynamic` | boolean | ✓ | ✓ | ✓ | Dynamic node creation for source/target setup, depending on role. |
| `terminus-durability` | enum: `none`, `configuration`, `unsettled-state` | ✓ | ✓ | ✓ | Durability mode for the applicable source or target terminus. |
| `expiry-policy` | enum: `link-detach`, `session-end`, `connection-close`, `never` | ✓ | ✓ | ✓ | Expiry policy for the applicable terminus. |
| `timeout` | uinteger | ✓ | ✓ | ✓ | Timeout value used with terminus expiry policy. |
| `sender-settle-mode` | enum: `unsettled`, `settled`, `mixed` | ✓ | ✓ | ✓ | AMQP sender settlement mode for the active sending side of the link. |
| `receiver-settle-mode` | enum: `first`, `second` | ✓ | ✓ | ✓ | AMQP receiver settlement mode for the active receiving side of the link. |

The values of all `link-properties` and `connection-properties` MAY contain
placeholders using the [RFC6570][RFC6570] Level 1 URI Template syntax. When the
same placeholder is used in multiple properties, the value of the placeholder
is assumed to be identical.

##### MQTT options

The [endpoint URIs](#protocoloptionsendpoints) for "MQTT" endpoints MUST be
valid MQTT URIs using the (informal) "mqtt" or "mqtts" scheme. If the path
portion of the URI is present, it MUST be a valid MQTT topic name as described
by [MQTT 3.1.1] and [MQTT 5.0]. The informal
schemes "tcp" (plain TCP/1883), "ssl" (TLS TCP/8883), and "wss"
(Websockets/443) MAY also be used, but MUST NOT have a path.

The following options are defined for MQTT 3.1.1 and MQTT 5.0 endpoints.

| Name | Type | P | C | S | Description |
|---|---|---|---|---|---|
| `topic` | string | ✓ | - | - | Concrete publish topic name. Prefer concrete destinations over filter syntax. |
| `topicfilter` | string | - | - | ✓ | Subscribe topic filter. |
| `qos` | enum: `0`, `1`, `2`, default `0` | ✓ | ✓ | ✓ | Role-relative QoS intent: publish QoS for producer, requested max QoS for subscriber, effective delivery QoS for consumer context. |
| `retain` | boolean, default `false` | ✓ | - | - | MQTT retain flag for publish behavior. |
| `willtopic` | string | ✓ | ✓ | ✓ | CONNECT Will topic configuration. |
| `willmessage` | xid (message reference) | ✓ | ✓ | ✓ | CONNECT Will message definition reference. |

MQTT 3.1.1 specific options:

| Name | Type | P | C | S | Description |
|---|---|---|---|---|---|
| `cleansession` | boolean, default `true` | ✓ | ✓ | ✓ | MQTT 3.1.1 clean-session behavior for the connection. |

MQTT 5.0 specific options:

| Name | Type | P | C | S | Description |
|---|---|---|---|---|---|
| `cleanstart` | boolean | ✓ | ✓ | ✓ | MQTT 5 clean-start behavior for the connection. |
| `sessionexpiryinterval` | uinteger (`0..4294967295`) | ✓ | ✓ | ✓ | MQTT 5 session expiry interval in seconds. |
| `sharedsubscriptiongroup` | string | - | - | ✓ | Shared subscription group. Use with `topicfilter`. |
| `nolocal` | boolean | - | - | ✓ | MQTT 5 subscribe no-local flag. |
| `retainaspublished` | boolean | - | - | ✓ | MQTT 5 subscribe retain-as-published flag. |
| `retainhandling` | enum: `0`, `1`, `2` | - | - | ✓ | MQTT 5 retain-handling mode. |

For MQTT 5.0, prefer `cleanstart` and `sessionexpiryinterval`; `cleansession`
SHOULD NOT be used.

##### KAFKA options

The [endpoint URIs](#protocoloptionsendpoints) for "Kafka" endpoints MUST be
valid Kafka bootstrap server addresses. The scheme follows Kafka configuration
usage as described in [Apache Kafka], e.g. `SSL://<HOST>:<PORT>` or
`PLAINTEXT://<HOST>:<PORT>`.

The following options are defined for Kafka endpoints.

| Name | Type | P | C | S | Description |
|---|---|---|---|---|---|
| `topic` | string | ✓ | ✓ | ✓ | Kafka topic name. |
| `acks` | integer (`-1..1`), default `1` | ✓ | - | - | Producer acknowledgement setting. |
| `key` | string | ✓ | - | - | Producer record key. |
| `partition` | integer | ✓ | ✓ | - | Fixed producer partition target or explicit consumer partition selection. |
| `consumergroup` | string | - | ✓ | - | Consumer group identifier for group-based consumption. |
| `headers` | map of string to string | ✓ | - | - | Producer record headers. |
| `keyserializer` | string | ✓ | - | - | Producer key serializer class/name. |
| `valueserializer` | string | ✓ | - | - | Producer value serializer class/name. |
| `autooffsetreset` | enum: `earliest`, `latest`, `none` | - | ✓ | - | Consumer offset reset behavior when no valid committed offset exists. |
| `enableautocommit` | boolean | - | ✓ | - | Consumer automatic commit behavior. |

##### NATS options

The [endpoint URIs](#protocoloptionsendpoints) for "NATS" endpoints MUST be
valid NATS URIs as described by [NATS]. The scheme MUST be "nats" or "tls" or
"ws" and the URI MUST include a port number, e.g. `nats://<HOST>:<PORT>` or
`tls://<HOST>:<PORT>`.

The following options are defined for NATS endpoints.

| Name | Type | P | C | S | Description |
|---|---|---|---|---|---|
| `subject` | string | ✓ | - | - | Concrete publish subject. |
| `subjectfilter` | string | - | - | ✓ | Subscription subject filter. |
| `queuegroup` | string | - | - | ✓ | Queue subscription group associated with a subject filter. |

[JSON Pointer]: https://www.rfc-editor.org/rfc/rfc6901
[CloudEvents Types]: https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/spec.md#type-system
[AMQP 1.0]: https://docs.oasis-open.org/amqp/core/v1.0/os/amqp-core-overview-v1.0-os.html
[AMQP Addressing Version 1.0]: https://docs.oasis-open.org/amqp/addressing/v1.0/csd01/addressing-v1.0-csd01.html
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
[RFC7617]: https://www.rfc-editor.org/rfc/rfc7617
[RFC6570]: https://www.rfc-editor.org/rfc/rfc6570
[rfc3339]: https://tools.ietf.org/html/rfc3339
