# Message Definitions Registry Service - Version 1.0-rc1

## Abstract

This specification defines a message and event catalog extension to the
xRegistry document format and API [specification](../core/spec.md).

## Table of Contents

- [Overview](#overview)
- [Notations and Terminology](#notations-and-terminology)
  - [Notational Conventions](#notational-conventions)
  - [Terminology](#terminology)
- [Message Definitions Registry](#message-definitions-registry)
  - [Message Definition Groups](#message-definition-groups)
  - [Message Definitions](#message-definitions)

## Overview

This specification defines a message and event catalog extension to the
xRegistry document format and API [specification](../core/spec.md). The purpose
of the catalog is to provide a machine-readable definitions for message and
event envelopes and logical grouping of related messages and events.

Managing the description of the payloads of those messages and events is not in
scope, but delegated to the [schema registry extension](../schema/spec.md) for
xRegistry. Schemas are linked to messages and event declarations by a URI
reference.

For easy reference, the JSON serialization of a Message Registry adheres to
this form:

```yaml
{
  "specversion": "<STRING>",
  "registryid": "<STRING>",
  "self": "<URL>",
  "shortself": "<URL>",
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

  "messagegroupsurl": "<URL>",
  "messagegroupscount": <UINTEGER>,
  "messagegroups": {
    "<KEY>": {                                    # messagegroupid
      "messagegroupid": "<STRING>",             # xRegistry core attributes
      "self": "<URL>",
      "shortself": "<URL>",
      "xid": "<XID>",
      # Start of default Version's attributes
      "epoch": <UINTEGER>,
      "name": "<STRING>", ?
      "description": "<STRING>", ?
      "documentation": "<URL>", ?
      "labels": { "<STRING>": "<STRING>" * }, ?
      "createdat": "<TIMESTAMP>",
      "modifiedat": "<TIMESTAMP>",

      "envelope": "<STRING>", ?                 # e.g. CloudEvents/1.0
      "protocol": "<STRING>", ?                 # e.g. HTTP/1.1

      "messagesurl": "<URL>",
      "messagescount": <UINTEGER>,
      "messages" : {
        "<KEY>": {                              # messageid
          "messageid": "<STRING>",              # xRegistry core attributes
          "versionid": "<STRING>",
          "self": "<URL>",
          "shortself": "<URL>",
          "xid": "<XID>",
          # Start of default Version's attributes
          "epoch": <UINTEGER>,
          "name": "<STRING>", ?
          "description": "<STRING>", ?
          "documentation": "<URL>", ?
          "labels": { "<STRING>": "<STRING>" * }, ?
          "createdat": "<TIMESTAMP>",
          "modifiedat": "<TIMESTAMP>",
          "ancestor": "<STRING>",

          "basemessageurl": "<URL>", ?         # Message being extended

          "envelope": "<STRING>", ?            # e.g. CloudEvents/1.0
          "envelopemetadata": {
            "<STRING>": <JSON-VALUE> *

            # CloudEvents/1.0 "envelope" the "envelopemetadata" is of the form:
            "<STRING>": {
              "type": "<TYPE>", ?
              "value": <ANY>, ?
              "required": <BOOLEAN>            # Default=false
            } *
          }, ?
          "envelopeoptions": {
            "<STRING>": <JSON-VALUE> *
          }, ?

          "protocol": "<STRING>", ?            # e.g. HTTP/1.1
          "protocoloptions": { ... }, ?

          "dataschemaformat": "<STRING>", ?
          "dataschema": <ANY>, ?
          "dataschemauri": "<URI>", ?
          "dataschemaxid": "<XID>", ?
          "datacontenttype": "<STRING>", ?
          # End of default Version's attributes

          "metaurl": "<URL>",
          "meta": { ... }, ?
          "versionsurl": "<URL>",
          "versionscount": <UINTEGER>,
          "versions": { ... } ?
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
generate an error if corresponding feature is not supported or enabled.
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

#### Message and Event

A **message** is a transport wrapper around a **message body** (interchangeably
referred to as payload) that is decorated with **metadata**. The metadata
describes the message body without an intermediary having to inspect it and
carries further information useful for identification, routing, and dispatch.

In this specification, **message** is an umbrella term that refers to all kinds
of messages as well as to **events** as a special form of messages.

The definition of [message][message] from the CloudEvents specification
applies.

#### Envelopes and Protocols

An **envelope** is a transport protocol-independent message metadata
convention. The [CNCF CloudEvents][CloudEvents] specification is an example of
a message envelope and is the only envelope explicitly defined in this
specification.

A similar transport protocol-independent message metadata convention is, for
example, the [W3C SOAP 1.2 envelope][SOAP] for which support could be added by
an extension.

This specification uses **protocol** to refer to a transport protocol-specific
message metadata convention. When a known protocol is explicitly specified for
a message definition, the "protocoloptions" section MAY contain constraints
for the protocol-specific metadata.

## Message Definitions Registry

The Message Definitions Registry (or "Message Catalog") is a registry of
metadata definitions for messages and events. The entries in the registry
describe constraints for the metadata of messages and events, for instance the
concrete values and patterns for the `type`, `source`, and `subject` attributes
of a CloudEvent.

Message definitions can be used in various contexts. A code generator for
message producers can be informed, which properties or headers have to be set,
and which data types, values, or patterns are expected to produce a conformant
message. A message consumer can use the definitions to validate incoming
messages and to extract the metadata for routing or processing.

A message group is a collection of message definitions that are related to
each other in some application-specific way. For instance, a message group
can be used to group all events raised by a particular application module or by
a particular role of an application protocol exchange pattern.

All message definitions MUST be defined inside message groups.

A message processor for a messaging or eventing channel can use a message group
and its contained message definitions to match incoming messages to the
declared message definitions and determine whether an incoming message
conforms to the expected metadata constraints. If a conformant message has
been identified, the processor might then use the linked schema to handle the
message body. This is especially useful in scenarios where the message itself
does not contain a schema hint or even content type information as it is the
case, for instance, in MQTT 3.1.1.

Whether a message is conformant to a message definition is determined by the
message processor and its implementation-specific rules. Conformance rules are
out of the scope of this specification.

The [Endpoint Registry](../endpoint/spec.md) is a related registry that leans
on this concept and allows associating one or more message definition groups
with an endpoint, thus effectively defining a contract for the endpoint. An
"endpoint" as defined in that specification is also a message definition group
in itself, with the message definitions following the rules of this
specification.

## Message Definition Registry Model

The formal xRegistry extension model of the Message Definitions Registry
resides in the [model.json](model.json) file.

### Message Definition Groups

The Group (`<GROUP>`) name is `messagegroups`. The type of a group is
`messagegroup`.

The following attributes are defined for the `messagegroup` object in addition
to the xRegistry-defined core
[attributes](../core/spec.md#attributes-and-extensions):

#### `envelope` (Message Group)

- Type: String
- Description: Identifies the common, transport protocol independent message
  metadata format. Message metadata envelopes are referenced by name and
  version as `<NAME>/<VERSION>`. This specification defines a set of common
  [metadata envelope names](#metadata-envelopes) that MUST be used for the
  given envelopes, but applications MAY define extensions for other envelopes
  on their own. All definitions inside a group MUST use this same envelope.
- Constraints:
  - At least one of `envelopemetadata` and `protocol` MUST be specified.
  - If present, MUST be a non-empty string
  - If present, MUST follow the naming convention `<NAME>/<VERSION>`, whereby
    `<NAME>` is the name of the metadata envelope and `<VERSION>` is the
    version of the metadata envelope.
- Examples:
  - `CloudEvents/1.0`

#### `protocol` (Message Group)

- Type: String
- Description: Identifies a transport protocol to be used for this Message.
  Protocols are referenced by name and version as `<NAME>/<VERSION>`. This
  specification defines a set of common [message protocol
  names](#message-protocols) that MUST be used for the given protocols, but
  applications MAY define extensions for other protocols on their own. All
  messages inside a group MUST use this same protocol.
- Constraints:
  - At least one of `envelopemetadata` and `protocol` MUST be specified.
  - If present, MUST be a non-empty string
  - If present, MUST follow the naming convention `<NAME>` or
    `<NAME>/<VERSION>`, whereby `<NAME>` is the name of the protocol and
    `<VERSION>` is the version of protocol. The version is REQUIRED if
    multiple, mutually incompatible versions of the protocol exist and
    protocol options differ between versions.
- Examples:
  - `MQTT/3.1.1`
  - `AMQP/1.0`
  - `KAFKA`

### Message Definitions

The resource (`<RESOURCE>`) collection name inside `messagegroup` is
`messages`. The resource name is `message`.

Different from schemas, message definitions do not contain a
version history. If the metadata of two messages differs, they are considered
different messages.

When [CloudEvents](https://cloudevents.io) is being used for a particular
message, it is RECOMMENDED that the message's `messageid` attribute be the
same as the [CloudEvents `type`
attribute](https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md#type). Doing so makes for easier management of the meta-model by correlating
the look-up value (id) of messages with their related events.

The following extensions are defined for the `message` Resource in addition to
the core xRegistry Resource
[attributes](../core/spec.md#attributes-and-extensions):

#### `basemessageurl`

- Type: URI-reference
- Description: if present, the URL points to a message definition that is the
  base for this message definition. By following the URL, the base message
  can be retrieved and extended with the properties of this message. This is
  useful for defining variants of messages that only differ in minor aspects to
  avoid repetition, or messages that only have a `envelope` with associated
  `envelopemetadata` to be bound to various protocols.
  Attributes defined in this message fully override the attributes of the base
  message.
- Constraints:
  - OPTIONAL
  - If present, MUST be a valid URI-reference
  - If present, MUST point to a resource of type `message` using JSON Pointer
    [RFC6901][JSON Pointer] notation.

#### `envelope`

Same as the [`envelope`](#envelope-message-group) attribute of the
`messagegroup` object.

Since messages MAY be cross-referenced ("borrowed") across message group
boundaries, this attribute is also REQUIRED and MUST be the same as the
`envelope` attribute of the `messagegroup` object into which the message is
embedded or referenced.

Illustrating example:

```yaml

"messagegroupsurl": "...",
"messagegroupscount": 2,
"messagegroups": {
  "com.example.abc": {
    "messagegroupid": "com.example.abc",
    "envelope": "CloudEvents/1.0",

    "messagesurl": "...",
    "messagescount": 2,
    "messages": {
      "com.example.abc.event1": {
        "messageid": "com.example.abc.event1",
        "envelope": "CloudEvents/1.0",
         # ... details ...
        }
      },
      "com.example.abc.event2": {
        "messageid": "com.example.abc.event1",
        "envelope": "CloudEvents/1.0",
        # ... details ...
      }
  },
  "com.example.def": {
    "messagegroupid": "com.example.def",
    "envelope": "CloudEvents/1.0",

    "messagesurl": "...",
    "messagescount": 1,
    "messages": {
      "com.example.abc.event1": {
        "uri": "#/messagegroups/com.example.abc/messages/com.example.abc.event1",
        # ... details ...
      }
    }
  }
}
```

#### `envelopemetadata`

- Type: Object
- Description: Describes the metadata constraints for messages of this type.
  The content of this property is defined by the message envelope, but all
  envelopes use a common schema for the constraints defined for their
  metadata headers, properties or attributes.
- Constraints:
  - REQUIRED if `envelope` is specified.
- Examples:
  - See [Metadata Envelopes](#metadata-envelopes)

#### `envelopeoptions`

See [`envelopeoptions`](../endpoint/spec.md#envelopeoptions) in the Endpoint
specification.

#### `protocol`

- Same as the [`protocol`](#protocol-message-group) attribute of the
  `messagegroup` object.

#### `protocoloptions`

- Type: Object
- Description: Describes the message constraints for the protocol being used.
  The content of this property is defined by the protocol message binding,
  but all protocols use a common schema model for the
  constraints defined for their metadata headers, properties or attributes.
- Constraints:
  - REQUIRED if `protocol` is specified.
- Examples:
  - See [Message protocols](#message-protocols)

#### `dataschemaformat`

- Type: String
- Description: Identifies the schema format applicable to the message payload,
  equivalent to the schema ['format'](../schema/spec.md#format)
  attribute.
- Constraints:
  - OPTIONAL
  - If present, MUST be a non-empty string
  - If present, MUST follow the naming convention `<NAME>/<VERSION>`, whereby
    `<NAME>` is the name of the schema format and `<VERSION>` is the version of
    the schema format in the format defined by the schema format itself.
- Examples:
  - 'JSONSchema/draft-07'
  - 'Avro/1.9.0'
  - 'Protobuf/3'

#### `dataschema`

- Type: Any
- Description: Contains the inline schema for the message payload. The schema
  format is identified by the `dataschemaformat` attribute. Equivalent to the
  schemaversion
  ['schema'](../schema/spec.md#schema) attribute
- Constraints:
  - OPTIONAL.
  - Mutually exclusive with the `dataschemauri` attribute.
  - If present, `dataschemaformat` MUST be present.
- Examples:
  - See [Schema Formats](../schema/spec.md#schema-formats)

#### `dataschemauri`

- Type: URI-reference
- Description: Contains a relative or absolute URI that points to the schema
  object to use for the message payload. The schema format is identified by the
  `dataschemaformat` attribute. See
  [Schema Formats](../schema/spec.md#schema-formats) for details on
  how to reference specific schema objects for the message payload. It is not
  sufficient for the URI-reference to point to a schema document; it MUST
  resolve to a concrete schema object.
- Constraints:
  - OPTIONAL.
  - Mutually exclusive with the `dataschema` attribute.
  - If present, `dataschemaformat` MUST be present.

#### `dataschemaxid`

- Type: XID
- Description: Contains the `xid` of the xRegistry `schema` Resource entity
  associated with the `dataschemauri` referenced schema document. Note that
  this means the entity MUST be located within the same Registry.
- Constraints:
  - OPTIONAL.
  - If present, `dataschemauri` MUST be present.

#### `datacontenttype`

- Type: `String` per [RFC 2046](https://tools.ietf.org/html/rfc2046)
- Description: Content type of the message payload. This attribute MAY be
  duplicative with some other metadata within the message definition. For
  example, in the case of using CloudEvents, the `envelopemetadata` attribute
  might include the `datacontenttype` attribute. This possible duplication
  of data is expected so as to allow for a more consistent, and easy, discovery
  of the message's format. This means that if this information does appear in
  more than one location within the message metadata they MUST all have the
  same values.

  Note that when an `envelope` is defined for a message and the data of
  interest is serialized as being nested within the envelope (e.g.
  CloudEvents "structured" mode), then this attribute MUST be the content type
  of the message envelope and not of the data nested within the envelope.

  As specified in [RFC 2045](https://tools.ietf.org/html/rfc2045), the media
  type part of the content type MUST be treated in a case-insensitive manner
  by consumers, along with the attribute names in parameters. For example,
  a `datacontenttype` of `text/plain; charset=utf-8` MUST be treated in the
  same way as `TEXT/Plain; CharSet=utf-8`.
- Constraints:
  - OPTIONAL
  - If present, MUST adhere to the format specified in
    [RFC 2046](https://tools.ietf.org/html/rfc2046)
- For Media Type examples see
  [IANA Media
  Types](http://www.iana.org/assignments/media-types/media-types.xhtml)

### Metadata Envelopes and Message Protocols

This section defines the metadata envelopes and message protocols that are
directly supported by this specification.

Metadata envelopes lean on a protocol-neutral metadata definition like
CloudEvents. Message protocols lean on a message model definition of a specific
protocol like AMQP or MQTT or Kafka.

A message can use either a metadata `envelope`, a message `protocol`, or both.

If a message only uses a metadata `envelope`, any implicit protocol bindings
defined by the envelope apply. For instance, a message definition that uses the
"CloudEvents/1.0" envelope but no explicit `protocol` implicitly applies to all
protocols for which CloudEvents bindings exist, and using the respective
protocol binding rules.

If a message uses both a metadata `envelope` and a message `protocol`, the
message binding rules apply over the metadata envelope rules. For instance, if
a message definition uses the "CloudEvents/1.0" envelope and an "AMQP/1.0"
protocol, then the implicit protocol bindings of the "CloudEvents/1.0" envelope
are overridden by the "AMQP/1.0" protocol rules.

If a message uses only a message `protocol`, only the metadata constraints
defined by the message `protocol` rules apply.

#### Common properties

The following properties are common to all messages with
headers/properties/attributes constraints:

##### `description`

- Type: String
- Description: A human-readable description of the property.
- Constraints:
  - OPTIONAL.
  - If present, MUST be a non-empty string.

##### `required`

- Type: Boolean
- Description: Indicates whether the property is REQUIRED to be present in a
  message of this type.
- Constraints:
  - OPTIONAL. Defaults MUST be `false`.
  - If present, MUST be a boolean value.

##### `specurl`

- Type: URI-reference
- Description: Contains a relative or absolute URI that points to the
  human-readable specification of the property.
- Constraints:
  - OPTIONAL

##### `type`

- Type: String
- Description: The type of the property. This is used to constrain the value of
  the property.
- Constraints:
  - OPTIONAL.
  - Default value MUST be "string".
  - The valid types are those defined in the [CloudEvents][CloudEvents Types]
    core specification, with some additions:
    - `any`: Any type of value, including `null`.
    - `boolean`: CloudEvents "Boolean" type.
    - `string`: CloudEvents "String" type.
    - `symbol`: A `string` that is restricted to alphanumerical characters and
      underscores.
    - `binary`: CloudEvents "Binary" type.
    - `timestamp`: CloudEvents "Timestamp" type (RFC3339 DateTime)
    - `duration`: RFC3339 Duration
    - `uritemplate`: [RFC6570][RFC6570] Level 1 URI Template
    - `uri`: CloudEvents URI type (RFC3986 URI)
    - `urireference`: CloudEvents "URI-reference" type (RFC3986 URI-reference)
    - `number`: IEEE754 Double
    - `integer`: CloudEvents "Integer" type (RFC 7159, Section 6)

##### `value`

- Type: Any
- Description: The value of the property. With a few exceptions, see below,
  this is the value that MUST be literally present in the message for the
  message to be considered conformant with this metaschema.
- Constraints:
  - OPTIONAL.
  - If present, MUST be a valid value for the property.

If the `type` property has the value `uritemplate`, `value` MAY contain
placeholders. As defined in [RFC6570][RFC6570] (Level 1), the placeholders MUST
be enclosed in curly braces (`{` and `}`) and MUST be a valid `symbol`.
Placeholders that are used multiple times in the same message definition MUST
to represent identical values.

When validating a message property against this value, the placeholders act as
wildcards. For example, the value `{foo}/bar` would match the value `abc/bar`
or `xyz/bar`.

When creating a message based on a metaschema with such a value, the
placeholders MUST be replaced with valid values. For example, the value
`{foo}/bar` would be replaced with `abc/bar` or `xyz/bar` when creating a
message.

If the `type` property has the value `timestamp` and the `value` property is
set to a value of `0000-01-01T00:00:00Z`, the value MUST be replaced with the
current timestamp when creating a message.

#### Metadata Envelopes

This specification only defines one metadata envelope: "CloudEvents/1.0".

##### CloudEvents/1.0

For the "CloudEvents/1.0" envelope, the
[`envelopemetadata`](#envelopemetadata) object contains a property
`attributes`, which is an object whose properties correspond to the
CloudEvents context attributes.

As with the [CloudEvents specification][CloudEvents], the attributes form a
flat list and extension attributes are allowed. Attribute names are restricted
to lower-case alphanumerical characters without separators.

The base attributes are defined as follows:

| Attribute         | Type          |
| ----------------- | ------------- |
| `specversion`     | `string`      |
| `id`              | `string`      |
| `type`            | `string`      |
| `source`          | `uritemplate` |
| `subject`         | `string`      |
| `time`            | `timestamp`   |
| `dataschema`      | `uritemplate` |
| `datacontenttype` | `string`      |

The following rules apply to the attribute declarations:

- All attribute declarations are OPTIONAL. Requirements for absent
  definitions are implied by the CloudEvents specification.
- The `specversion` attribute is implied by the message envelope and is
  OPTIONAL. If present, it MUST be declared with a `string` type and set to the
  value "1.0".
- The `type`, `id`, and `source` attributes implicitly have the `required` flag
  set to `true` and MUST NOT be declared as `required: false`.
- The `id` attribute's `value` SHOULD NOT be defined.
- The `time` attribute's `value` default value MUST be `0000-01-01T00:00:00Z`
  ("current time") and SHOULD NOT be declared with a different value.
- The `datacontenttype` attribute's `value` is inferred from the
  [`dataschemaformat`](#dataschemaformat) attribute of the message definition
  if absent.
- The `dataschema` attribute's `value` is inferred from the
  [`dataschemauri`](#dataschemauri) attribute or
  [`dataschema`](#dataschema) attribute of the message definition if
  absent. If present, the value MUST match the `dataschemauri` attribute of the
  message definition.
- The `type` of the property definition defaults to the CloudEvents type
  definition for the attribute, if any. The `type` of an attribute MAY be
  modified be to further constrained. For instance, the `source` type
  `urireference` MAY be changed to
  `uritemplate` or the `subject` type `string` MAY be constrained to a
  `urireference` or `stringified integer`. If no CloudEvents type definition
  exists, the default value MUST be `string`.

The values of all `string` and `uritemplate`-typed attributes MAY contain
placeholders using the [RFC6570][RFC6570] Level 1 URI Template syntax. When the
same placeholder is used in multiple properties, the value of the placeholder
is assumed to be identical.

The following shows the format of a CloudEvents "envelopemetadata" section for
a message (see the [model file](model.json) for the complete definition):

```yaml
"envelope": "CloudEvents/1.0",
"envelopemetadata" {
  # "CloudEvents/1.0" envelope metadata
  "specversion": {
    "value": "1.0",
    "type": "string"
  },
  "id": {
    "value": "<STRING>", ?
    "type": "string", ?
  },
  "type": {
    "value": "<STRING>", ?
    "type": "string", ?
  },
  "source": {
    "value": "<STRING>", ?
    "type": "string", ?
  },
  "subject": {
    "value": "<STRING>", ?
    "type": "string" ?
  },
  "time": {
    "value": "<TIMESTAMP>", ?
    "type": "timestamp" ?
  },
  "dataschema": {
    "value": "<URITEMPLATE>", ?
    "type": "uritemplate" ?
  },
  "*": {
    "value": <ANY>, ?
    "type": "<TYPE>"
  }
}
```

The following example declares a CloudEvent with a JSON payload. The attribute
`id` is REQUIRED in the declared event per the CloudEvents specification in
spite of such a declaration being absent here, the `type` of the `type`
attribute is `string` and the attribute is `required` even though the
declarations are absent. The `time` attribute is made `required` contrary to
the CloudEvents base specification. The implied CloudEvents `datacontenttype`
attribute value is `application/json` and the implied CloudEvents `dataschema`
attribute value is `https://example.com/schemas/com.example.myevent.json`:

```yaml
{
  "envelope": "CloudEvents/1.0",
  "envelopemetadata": {
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
  },
  "dataschemaformat": "JsonSchema/draft-07",
  "dataschemauri": "https://example.com/schemas/com.example.myevent.json",
}
```

For clarity of the definition, you MAY always declare all implied attribute
properties explicitly, but they MUST conform with the rules above.

#### Message Protocols

##### "HTTP/1.1", "HTTP/2", "HTTP/3" protocols

The "HTTP" protocol is used to define messages that are sent over an HTTP
connection. The protocol is based on the
[HTTP Message Format][HTTP Message Format] and is common across all versions of
HTTP.

The [`protocoloptions`](#protocoloptions) object MAY contain several
properties:

| Property  | Type          | Description                  |
| --------- | ------------- | ---------------------------- |
| `headers` | Array         | The HTTP headers. See below  |
| `query`   | Map           | The HTTP query parameters    |
| `path`    | `uritemplate` | The HTTP path                |
| `method`  | `string`      | The HTTP method              |
| `status`  | `string`      | The HTTP status code         |

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
query elements MAY contain placeholders using the [RFC6570][RFC6570] Level 1
URI Template syntax. When the same placeholder is used in multiple properties,
the value of the placeholder is assumed to be identical.

The following example defines a message that is sent over HTTP/1.1:

```yaml
{
  "protocol": "HTTP",
  "protocoloptions": {
    "headers": [
      {
        "name": "Content-Type",
        "value": "application/json"
      }
    ],
    "query": [
      {
        "name": "foo",
        "value": "bar"
      }
    ],
    "path": "/foo/{bar}",
    "method": "POST"
  },
  "dataschemaformat": "JsonSchema/draft-07",
  "dataschemauri": "https://example.com/schemas/com.example.myevent.json",
}
```

##### "AMQP/1.0" protocol

The "AMQP/1.0" protocol is used to define messages that are sent over an
[AMQP][AMQP 1.0] connection. It is based on the default
[AMQP 1.0 Message Format][AMQP 1.0 Message Format].

The [`protocoloptions`](#protocoloptions) object MAY contain several
properties, each of which corresponds to a section of the AMQP 1.0 Message:

| Property                 | Type | Description                                                                     |
| ------------------------ | ---- | ------------------------------------------------------------------------------- |
| `properties`             | Map  | The AMQP 1.0 [Message Properties][AMQP 1.0 Message Properties] section          |
| `application-properties` | Map  | The AMQP 1.0 [Application Properties][AMQP 1.0 Application Properties] section. |
| `message-annotations`    | Map  | The AMQP 1.0 [Message Annotations][AMQP 1.0 Message Annotations] section        |
| `delivery-annotations`   | Map  | The AMQP 1.0 [Delivery Annotations][AMQP 1.0 Delivery Annotations] section      |
| `header`                 | Map  | The AMQP 1.0 [Message Header][AMQP 1.0 Message Header] section                  |
| `footer`                 | Map  | The AMQP 1.0 [Message Footer][AMQP 1.0 Message Footer] section                  |

As in AMQP, all sections and properties are OPTIONAL.

The values of all `string`, `symbol`, `uri`, and `uritemplate`-typed properties
MAY contain placeholders using the [RFC6570][RFC6570] Level 1 URI Template
syntax. When the same placeholder is used in multiple properties, the value of
the placeholder is assumed to be identical.

Example for an AMQP 1.0 message type that declares a fixed `subject` (analogous
to CloudEvents' `type`), a custom property, and a `content-type` of
`application/json` without declaring a schema reference in the message
definition:

```yaml
{
  "protocol": "AMQP/1.0",
  "protocoloptions": {
    "properties": {
      "message-id": {
        "required": true
      },
      "to": {
        "value": "https://{host}/{queue}"
      },
      "subject": {
        "value": "MyMessageType",
        "required": true
      },
      "content-type": {
        "value": "application/json"
      },
      "content-encoding": {
        "value": "gzip"
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

##### `properties` (AMQP 1.0)

The `properties` property is an object that contains the fixed properties of
the AMQP 1.0 [Message Properties][AMQP 1.0 Message Properties] section. The
following properties are defined, with type constraints:

| Property               | Type          | Description                                                                      |
| ---------------------- | ------------- | -------------------------------------------------------------------------------- |
| `message-id`           | (see note below) | uniquely identifies a message within the message system                          |
| `user-id`              | `binary`      | identity of the user responsible for producing the message                       |
| `to`                   | `uritemplate` | address of the node to send the message to                                       |
| `subject`              | `string`      | message subject                                                                  |
| `reply-to`             | `uritemplate` | address of the node to which the receiver of this message ought to send replies  |
| `correlation-id`       | `string`      | client-specific id that can be used to mark or identify messages between clients |
| `content-type`         | `symbol`      | MIME content type for the message                                                |
| `content-encoding`     | `symbol`      | MIME content encoding for the message                                            |
| `absolute-expiry-time` | `timestamp`   | time when this message is considered expired                                     |
| `group-id`             | `string`      | group this message belongs to                                                    |
| `group-sequence`       | `integer`     | position of this message within its group                                        |
| `reply-to-group-id`    | `uritemplate` | group-id to which the receiver of this message ought to send replies to          |

The `message-id` permits the types `ulong`, `uuid`, `binary`, `string`, and
`uritemplate`. A `value` constraint for `message-id` property SHOULD NOT be
defined in the message definition except for the case where the `message-id`
is a `uritemplate`.

##### `application-properties` (AMQP 1.0)

The `application-properties` property is a map that contains the custom
properties of the AMQP 1.0 [Application Properties][AMQP 1.0 Application
Properties] section.

The names of the properties MUST be of type `symbol` and MUST be unique.
The values of the properties MAY be of any permitted type.

##### `message-annotations` (AMQP 1.0)

The `message-annotations` property is a map that contains the custom
properties of the AMQP 1.0 [Message Annotations][AMQP 1.0 Message Annotations]
section.

The names of the properties MUST be of type `symbol` and MUST be unique.
The values of the properties MAY be of any permitted type.

##### `delivery-annotations` (AMQP 1.0)

The `delivery-annotations` property is a map that contains the custom
properties of the AMQP 1.0
[Delivery Annotations][AMQP 1.0 Delivery Annotations] section.

The names of the properties MUST be of type `symbol` and MUST be unique.
The values of the properties MAY be of any permitted type.

###### `header` (AMQP 1.0)

The `header` property is an object that contains the properties of the
AMQP 1.0 [Message Header][AMQP 1.0 Message Header] section. The
following properties are defined, with type constraints:

| Property         | Type      | Description                                                    |
| ---------------- | --------- | -------------------------------------------------------------- |
| `durable`        | `boolean` | specify durability requirements                                |
| `priority`       | `integer` | relative message priority                                      |
| `ttl`            | `integer` | message time-to-live in milliseconds                           |
| `first-acquirer` | `boolean` | indicates whether the message has not been acquired previously |
| `delivery-count` | `integer` | number of prior unsuccessful delivery attempts                 |

###### `footer` (AMQP 1.0)

The `footer` property is a map that contains the custom properties of the AMQP
1.0 [Message Footer][AMQP 1.0 Message Footer] section.

The names of the properties MUST be of type `symbol` and MUST be unique.
The values of the properties MAY be of any permitted type.

##### "MQTT/3.1.1" and "MQTT/5.0" protocols

The "MQTT/3.1.1" and "MQTT/5.0" protocols are used to define messages that are
sent over [MQTT 3.1.1][MQTT 3.1.1] or [MQTT 5.0][MQTT 5.0] connections. The
format describes the [MQTT PUBLISH packet][MQTT 5.0] content.

The [`protocoloptions`](#protocoloptions) object contains the elements of the
MQTT PUBLISH packet directly, with the `user-properties` element corresponding
to the application properties collection of other protocols.

The following properties are defined. The MQTT 3.1.1 and MQTT 5.0 columns
indicate whether the property is supported for the respective MQTT version.

| Property                  | Type          | MQTT 3.1.1 | MQTT 5.0 | Description                      |
| ------------------------- | ------------- | ---------- | -------- | -------------------------------- |
| `qos`                     | `integer`     | yes        | yes      | Quality of Service level         |
| `retain`                  | `boolean`     | yes        | yes      | Retain flag                      |
| `topic_name`              | `string`      | yes        | yes      | Topic name                       |
| `payload_format`          | `integer`     | no         | yes      | Payload format indicator         |
| `message_expiry_interval` | `integer`     | no         | yes      | Message expiry interval          |
| `response_topic`          | `uritemplate` | no         | yes      | Response topic                   |
| `correlation_data`        | `binary`      | no         | yes      | Correlation data                 |
| `content_type`            | `symbol`      | no         | yes      | MIME content type of the payload |
| `user_properties`         | Array         | no         | yes      | User properties                  |

Like HTTP, the MQTT allows for multiple user properties with the same name,
so the `user_properties` property is an array of objects, each of which
contains a single property name and value.

The values of all `string`, `symbol`, and `uritemplate`-typed properties and
user properties MAY contain placeholders using the [RFC6570][RFC6570] Level 1
URI Template syntax. When the same placeholder is used in multiple properties,
the value of the placeholder is assumed to be identical.

The following example shows a message with the "MQTT/5.0" protocol, asking for
QoS 1 delivery, with a topic name of "mytopic", and a user property of
"my-application-property" with a value of "my-application-property-value":

```yaml
{
  "protocol": "MQTT/5.0",
  "protocoloptions": {
    "qos": 1,
    "retain":  false,
    "topic_name": "mytopic",
    "user_properties": [
      {
        "name": "My Application Property",
        "value": "Value 1"
      }
    ]
  }
}
```

### "KAFKA" protocol

The "KAFKA" protocol is used to define messages that are sent using the [Apache
Kafka][Apache Kafka] RPC protocol.

The [`protocoloptions`](#protocoloptions) object contains the common elements
of the Kafka [producer][Apache Kafka producer] and
[consumer][Apache Kafka consumer] records, with the `headers` element
corresponding to the application properties collection of other protocols.

The following properties are defined:

| Property    | Type      | Description                                                                         |
| ----------- | --------- | ----------------------------------------------------------------------------------- |
| `topic`     | `string`  | The topic the record will be appended to                                            |
| `partition` | `integer` | The partition to which the record is to be sent or has been received from           |
| `key`       | `string`  | The key that is associated with the record, UTF-8 encoded                           |
| `key_base64`| `binary`  | The key that is associated with the record as a base64 encoded string               |
| `headers`   | Map       | A map of headers to set on the record                                               |

The `key` and `key_base64` properties are mutually exclusive and MUST NOT be
present at the same time.

The `partition` property is included because there are cases where applications
use partitions explicitly for addressing and routing messages within the scope
of a topic.

The values of all `string`, `symbol`, `uritemplate`-typed properties
and headers MAY contain placeholders using the [RFC6570][RFC6570] Level 1 URI
Template syntax. When the same placeholder is used in multiple properties, the
value of the placeholder is assumed to be identical.

Example:

```yaml
{
  "protocol": "Kafka",
  "protocoloptions": {
    "topic": "mytopic",
    "key": "thisdevice"
  }
}
```

### "NATS" protocol

The "NATS" protocol is used to define messages that are sent using the
[NATS][NATS] protocol.

The [`protocoloptions`](#protocoloptions) object contains the available
elements of the NATS message for the `HPUB` operation.

The following properties are defined:

| Property    | Type      | Description                                                                         |
| ----------- | --------- | ----------------------------------------------------------------------------------- |
| `subject`   | `uritemplate`  | The subject the message will be published to                                   |
| `reply-to`  | `uritemplate`  | The subject the receiver ought to reply to                                        |
| `headers`   | Array     | A list of headers to set on the message                                             |

The values of all `string`, `symbol`, `uritemplate`-typed properties
and headers MAY contain placeholders using the [RFC6570][RFC6570] Level 1 URI
Template syntax. When the same placeholder is used in multiple properties, the
value of the placeholder is assumed to be identical.

Example:

```yaml
{
  "protocol": "NATS",
  "protocoloptions": {
    "subject": "mytopic",
    "reply-to": "replytopic"
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
[message]: https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md#message
[SOAP]: https://www.w3.org/TR/soap12-part1/
