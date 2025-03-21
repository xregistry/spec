# Message Definitions Registry Service - Version 0.5-wip

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
of the catalog is to provide a machine-readable description of message and event
envelopes and logical grouping of related messages and events.

Managing the description of the payloads of those messages and events is not in
scope, but delegated to the [schema registry extension](../schema/spec.md) for
xRegistry.

For easy reference, the JSON serialization of a Message Registry adheres to
this form:

```yaml
{
  "specversion": "STRING",
  "registryid": "STRING",
  "self": "URL",
  "xid": "XID",
  "epoch": UINTEGER,
  "name": "STRING", ?
  "description": "STRING", ?
  "documentation": "URL", ?
  "labels": {
      "STRING": "STRING" *
  }, ?
  "createdat": "TIMESTAMP",
  "modifiedat": "TIMESTAMP",
  "modelversion": "1.0", ?
  "compatiblewith": "https://raw.githubusercontent.com/xregistry/spec/refs/heads/main/message/model.json", ?

  "model": { ... }, ?

  "messagegroupsurl": "URL",
  "messagegroupscount": UINTEGER,
  "messagegroups": {
    "KEY": {                                    # messagegroupid
      "messagegroupid": "STRING",               # xRegistry core attributes
      "self": "URL",
      "xid": "XID",
      # Start of default Version's attributes
      "epoch": UINTEGER,
      "name": "STRING", ?
      "description": "STRING", ?
      "documentation": "URL", ?
      "labels": { "STRING": "STRING" * }, ?
      "createdat": "TIMESTAMP",
      "modifiedat": "TIMESTAMP",

      "envelope": "STRING", ?                  # e.g. CloudEvents/1.0
      "protocol": "STRING", ?                  # e.g. HTTP/1.1

      "messagesurl": "URL",
      "messagescount": UINTEGER,
      "messages" : {
        "KEY": {                               # messageid
          "messageid": "STRING",               # xRegistry core attributes
          "versionid": "STRING",
          "self": "URL",
          "xid": "XID",
          # Start of default Version's attributes
          "epoch": UINTEGER,
          "name": "STRING", ?
          "description": "STRING", ?
          "documentation": "URL", ?
          "labels": { "STRING": "STRING" * }, ?
          "createdat": "TIMESTAMP",
          "modifiedat": "TIMESTAMP",

          "deprecated": {
            "effective": "TIMESTAMP", ?
            "removal": "TIMESTAMP", ?
            "alternative": "URL", ?
            "docs": "URL"?
          }, ?

          "basemessageurl": "URL", ?           # Message being extended

          "envelope": "STRING", ?              # e.g. CloudEvents/1.0
          "envelopemetadata": {
            "STRING": JSON-VALUE *

            # CloudEvents/1.0 "envelope" the "envelopemetadata" is of the form:
            "STRING": {
              "type": "TYPE", ?
              "value": ANY, ?
              "required": BOOLEAN              # Default=false
            } *
          }, ?
          "envelopeoptions": {
            "STRING": JSON-VALUE *
          },

          "protocol": "STRING", ?              # e.g. HTTP/1.1
          "protocoloptions": { ... }, ?

          "dataschemaformat": "STRING", ?
          "dataschema": ANY, ?
          "dataschemauri": "URI", ?
          "datacontenttype": "STRING", ?
          # End of default Version's attributes

          "metaurl": "URL",
          "meta": { ... }, ?
          "versionsurl": "URL",
          "versionscount": UINTEGER,
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

#### Message and Event

A **message** is a transport wrapper around a **message body** (interchangeably
referred to as payload) that is decorated with **metadata**. The metadata
describes the message body without an intermediary having to inspect it and
carries further information useful for identification, routing, and dispatch.

In this specification, **message** is an umbrella term that refers to all kinds
of messages as well as to **events** as a special form of messages.

The definition of [message][message] from the CloudEvents specification applies.

## Message Definitions Registry

The Message Definitions Registry (or "Message Catalog") is a registry of
metadata definitions for messages and events. The entries in the registry
describe constraints for the metadata of messages and events, for instance the
concrete values and patterns for the `type`, `source`, and `subject` attributes
of a CloudEvent.

A message group is a collection of message definitions that are related to
each other in some application-specific way. For instance, a message group
can be used to group all events raised by a particular application module or by
a particular role of an application protocol exchange pattern.

All message definitions MUST defined inside message groups.

## Message Definition Registry Model

The formal xRegistry extension model of the Message Definitions Registry
resides in the [model.json](model.json) file.

By importing and keeping the `compatiblewith` label and its value,
interoperability on the CNCF defined endpoint model is stated.

### Message Definition Groups

The Group (GROUP) name is `messagegroups`. The type of a group is
`messagegroup`.

The following attributes are defined for the `messagegroup` object in
addition to the basic [attributes](../core/spec.md#attributes-and-extensions):

#### `envelope` (Message Group)

- Type: String
- Description: Identifies the common, transport protocol independent message
  metadata format. Message metadata envelopes are referenced by name and version
  as `{NAME}/{VERSION}`. This specification defines a set of common
  [metadata envelope names](#metadata-envelopes) that MUST be used for the given
  envelopes, but applications MAY define extensions for other envelopes on their
  own. All definitions inside a group MUST use this same envelope.
- Constraints:
  - At least one of `envelopemetadata` and `protocol` MUST be specified.
  - If present, MUST be a non-empty string
  - If present, MUST follow the naming convention `{NAME}/{VERSION}`, whereby
    `{NAME}` is the name of the metadata envelope and `{VERSION}` is the
    version of the metadata envelope.
- Examples:
  - `CloudEvents/1.0`

#### `protocol` (Message Group)

- Type: String
- Description: Identifies a transport protocol to be used for this Message.
  Protocols are referenced by name and version as `{NAME}/{VERSION}`. This
  specification defines a set of common [message protocol
  names](#message-protocols) that MUST be used for the given protocols, but
  applications MAY define extensions for other protocols on their own. All
  messages inside a group MUST use this same protocol.
- Constraints:
  - At least one of `envelopemetadata` and `protocol` MUST be specified.
  - If present, MUST be a non-empty string
  - If present, MUST follow the naming convention `{NAME}/{VERSION}`, whereby `{NAME}` is
    the name of the protocol and `{VERSION}` is the version of protocol.
- Examples:
  - `MQTT/3.1.1`
  - `AMQP/1.0`
  - `Kafka/0.11`

### Message Definitions

The resource (RESOURCE) collection name inside `messagegroup` is
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

#### `deprecated`

- Type: Object containing the following properties:
  - `effective`<br>
    An OPTIONAL property indicating the time when the message entered, or will
    enter, a deprecated state. The date MAY be in the past or future. If this
    property is not present the message is already in a deprecated state.
    If present, this MUST be an [RFC3339][rfc3339] timestamp.

  - `removal`<br>
    An OPTIONAL property indicating the time when the message MAY be removed.
    The message MUST NOT be removed before this time. If this property is not
    present then client can not make any assumption as to when the message
    might be removed. Note: as with most properties, this property is mutable.
    If present, this MUST be an [RFC3339][rfc3339] timestamp and MUST NOT be
    sooner than the `effective` time if present.

  - `alternative`<br>
    An OPTIONAL property specifying the URL to an alternative message the
    client can consider as a replacement for this message. There is no
    guarantee that the referenced message is an exact replacement, rather the
    client is expected to investigate the message to determine if it is
    appropriate.

  - `docs`<br>
    An OPTIONAL property specifying the URL to additional information about
    the deprecation of the message. This specification does not mandate any
    particular format or information, however some possibilities include:
    reasons for the deprecation or additional information about likely
    alternative message. The URL MUST support an HTTP GET request.

  Note that an implementation is not mandated to use this attribute in
  advance of removing an message, but is it RECOMMENDED that they do so.
- Constraints:
  - OPTIONAL
- Examples:
  - `"deprecated": {}`
  - ```
    "deprecated": {
      "removal": "2030-12-19T00:00:00-00:00",
      "alternative": "https://example.com/messages/popped"
    }
    ```

#### `basemessageurl`

- Type: URI-reference
- Description: if present, the URL points to a message definition that is the
  base for this message definition. By following the URL, the base message
  can be retrieved and extended with the properties of this message. This is
  useful for defining variants of messages that only differ in minor aspects to
  avoid repetition, or messages that only have a `envelope` with associated
  `envelopemetadata` to be bound to various protocols.
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
- Description: Describes the metadata constraints for messages of this type. The
  content of this property is defined by the message envelope, but all
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
  - REQUIRED
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
  - If present, MUST follow the naming convention `{NAME}/{VERSION}`, whereby
    `{NAME}` is the name of the schema format and `{VERSION}` is the version of
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

#### `datacontenttype`

- Type: Type: `String` per [RFC 2046](https://tools.ietf.org/html/rfc2046)
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
  [IANA Media Types](http://www.iana.org/assignments/media-types/media-types.xhtml)

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

##### `required`

- Type: Boolean
- Description: Indicates whether the property is REQUIRED to be present in a
  message of this type.
- Constraints:
  - OPTIONAL. Defaults MUST be `false`.
  - If present, MUST be a boolean value.

##### `description`

- Type: String
- Description: A human-readable description of the property.
- Constraints:
  - OPTIONAL.
  - If present, MUST be a non-empty string.

##### `value`

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

##### `type`

- Type: String
- Description: The type of the property. This is used to constrain the value of
  the property.
- Constraints:
  - OPTIONAL. Default value MUST be "string".
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

##### `specurl`

- Type: URI-reference
- Description: Contains a relative or absolute URI that points to the
  human-readable specification of the property.
- Constraints:
  - OPTIONAL

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
- The `specversion` attribute is implied by the message envelope and is NOT
  REQUIRED. If present, it MUST be declared with a `string` type and set to the
  value "1.0".
- The `type`, `id`, and `source` attributes implicitly have the `required` flag
  set to `true` and MUST NOT be declared as `required: false`.
- The `id` attribute's `value` SHOULD NOT be defined.
- The `time` attribute's `value` default value MUST be `01-01-0000T00:00:00Z`
  ("current time") and SHOULD NOT be declared with a different value.
- The `datacontenttype` attribute's `value` is inferred from the
  [`dataschemaformat`](#dataschemaformat) attribute of the message definition
  if absent.
- The `dataschema` attribute's `value` is inferred from the
  [`dataschemauri`](#dataschemauri) attribute or
  [`dataschema`](#dataschema) attribute of the message definition if
  absent.
- The `type` of the property definition defaults to the CloudEvents type
  definition for the attribute, if any. The `type` of an attribute MAY be
  modified be to further constrained. For instance, the `source` type
  `urireference` MAY be changed to
  `uritemplate` or the `subject` type `string` MAY be constrained to a
  `urireference` or `stringified integer`. If no CloudEvents type definition
  exists, the default value MUST be `string`.

The values of all `string` and `uritemplate`-typed attributes MAY contain
placeholders using the [RFC6570][RFC6570] Level 1 URI Template syntax. When the
same placeholder is used in multiple properties, the value of the placeholder is
assumed to be identical.

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
    "value": "STRING", ?
    "type": "string", ?
  },
  "type": {
    "value": "STRING", ?
    "type": "string", ?
  },
  "source": {
    "value": "STRING", ?
    "type": "string", ?
  },
  "subject": {
    "value": "STRING", ?
    "type": "string" ?
  },
  "time": {
    "value": "TIME", ?
    "type": "timestamp" ?
  },
  "dataschema": {
    "value": "URITEMPLATE", ?
    "type": "uritemplate" ?
  },
  "*": {
    "value": ANY, ?
    "type": "TYPE", ?
    "required": BOOLEAN ?
  }
}
```

The following example declares a CloudEvent with a JSON payload. The attribute
`id` is REQUIRED in the declared event per the CloudEvents specification in
spite of such a declaration being absent here, the `type` of the `type`
attribute is `string` and the attribute is `required` even though the
declarations are absent. The `time` attribute is made `required` contrary to the
CloudEvents base specification. The implied `datacontenttype` is
`application/json` and the implied `dataschema` is
`https://example.com/schemas/com.example.myevent.json`:

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
| `headers` | Array         | The HTTP headers. See below. |
| `query`   | Map           | The HTTP query parameters.   |
| `path`    | `uritemplate` | The HTTP path.               |
| `method`  | `string`      | The http method              |
| `status`  | `string`      | The http status code         |

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

```yaml
{
  "protocol": "HTTP/1.1",
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

TODO: - vs _ for prop names in the table below

| Property                 | Type | Description                                                                     |
| ------------------------ | ---- | ------------------------------------------------------------------------------- |
| `properties`             | Map  | The AMQP 1.0 [Message Properties][AMQP 1.0 Message Properties] section.         |
| `application-properties` | Map  | The AMQP 1.0 [Application Properties][AMQP 1.0 Application Properties] section. |
| `message-annotations`    | Map  | The AMQP 1.0 [Message Annotations][AMQP 1.0 Message Annotations] section.       |
| `delivery-annotations`   | Map  | The AMQP 1.0 [Delivery Annotations][AMQP 1.0 Delivery Annotations] section.     |
| `header`                 | Map  | The AMQP 1.0 [Message Header][AMQP 1.0 Message Header] section.                 |
| `footer`                 | Map  | The AMQP 1.0 [Message Footer][AMQP 1.0 Message Footer] section.                 |

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

##### `properties` (AMQP 1.0)

The `properties` property is an object that contains the properties of the
AMQP 1.0 [Message Properties][AMQP 1.0 Message Properties] section. The
following properties are defined, with type constraints:

| Property               | Type          | Description                                                                      |
| ---------------------- | ------------- | -------------------------------------------------------------------------------- |
| `message-id`           | `string`      | uniquely identifies a message within the message system                          |
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

##### `application-properties` (AMQP 1.0)

The `application-properties` property is an object that contains the custom
properties of the AMQP 1.0 [Application Properties][AMQP 1.0 Application Properties] section.

The names of the properties MUST be of type `symbol` and MUST be unique.
The values of the properties MAY be of any permitted type.

##### `message-annotations` (AMQP 1.0)

The `message-annotations` property is an object that contains the custom
properties of the AMQP 1.0 [Message Annotations][AMQP 1.0 Message Annotations]
section.

The names of the properties MUST be of type `symbol` and MUST be unique.
The values of the properties MAY be of any permitted type.

##### `delivery-annotations` (AMQP 1.0)

The `delivery-annotations` property is an object that contains the custom
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

The `footer` property is an object that contains the custom properties of the
AMQP 1.0 [Message Footer][AMQP 1.0 Message Footer] section.

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
| `topic-name`              | `string`      | yes        | yes      | Topic name                       |
| `payload-format`          | `integer`     | no         | yes      | Payload format indicator         |
| `message-expiry-interval` | `integer`     | no         | yes      | Message expiry interval          |
| `response-topic`          | `uritemplate` | no         | yes      | Response topic                   |
| `correlation-data`        | `binary`      | no         | yes      | Correlation data                 |
| `content-type`            | `symbol`      | no         | yes      | MIME content type of the payload |
| `user-properties`         | Array         | no         | yes      | User properties                  |

Like HTTP, the MQTT allows for multiple user properties with the same name,
so the `user-properties` property is an array of objects, each of which
contains a single property name and value.

The values of all `string`, `symbol`, and `uritemplate`-typed properties and
user-properties MAY contain placeholders using the [RFC6570][RFC6570] Level 1
URI Template syntax. When the same placeholder is used in multiple properties,
the value of the placeholder is assumed to be identical.

The following example shows a message with the "MQTT/5.0" protocol, asking for
QoS 1 delivery, with a topic name of "mytopic", and a user property of
"my-application-property" with a value of "my-application-property-value":

```yaml
{
  "protocol": "MQTT/5.0",
  "protocoloptions": {
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

### "Kafka" protocol

The "Kafka" protocol is used to define messages that are sent over [Apache
Kafka][Apache Kafka] connections. The version number reflects the last version
in which the record structure was changed in the Apache Kafka project, not the
current version. If the version number is omitted, the latest version is
assumed.

The [`protocoloptions`](#protocoloptions) object contains the common elements
of the Kafka [producer][Apache Kafka producer] and
[consumer][Apache Kafka consumer] records, with the `headers` element
corresponding to the application properties collection of other protocols.

The following properties are defined:

| Property    | Type      | Description                                                                         |
| ----------- | --------- | ----------------------------------------------------------------------------------- |
| `topic`     | `string`  | The topic the record will be appended to                                            |
| `partition` | `integer` | The partition to which the record ought be sent                                     |
| `key`       | `binary`  | The key that will be included in the record                                         |
| `headers`   | Map       | A map of headers to set on the record                                               |
| `timestamp` | `integer` | The timestamp of the record; if 0 (default), the producer will assign the timestamp |

The values of all `string`, `symbol`, `uritemplate`-typed properties
and headers MAY contain placeholders using the [RFC6570][RFC6570] Level 1 URI
Template syntax. When the same placeholder is used in multiple properties, the
value of the placeholder is assumed to be identical.

Example:

```yaml
{
  "protocol": "Kafka",
  "protocoloptions": {
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
[message]: https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md#message
