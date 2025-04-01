# CloudEvents Registry Service - Version 1.0-rc1

## Abstract

The CloudEvents Registry is a universal catalog and discovery metadata format
as well as a metadata service API for messaging and eventing schemas,
metaschemas, and messaging and eventing endpoints.

## Table of Contents

- [Notations and Terminology](#notations-and-terminology)
  - [Notational Conventions](#notational-conventions)
- [CloudEvents Registry](#cloudevents-registry)

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

```yaml
{
  "$schema": "https://cloudevents.io/schemas/registry",
  "specversion": "1.0-rc1",
  "registryid": "Example Registry",
  "self": "http://example.com",
  "xid": "/",
  "epoch": 4,
  "createdat": "2024-04-30T12:00:00Z",
  "modifiedat": "2024-04-31T12:00:00Z",

  "endpointsurl": "https://example.com/endpoints",
  "endpointscount": 1,
  "endpoints": {
    "com.example.telemetry": {
      "endpointid": "com.example.telemetry",
      "self": "https://example.com/endpoints/com.example.telemetry",
      "xid": "/endpoints/com.example.telemetry",
      "epoch": 5,
      "createdat": "2024-04-30T12:00:00Z",
      "modifiedat": "2024-04-31T12:00:00Z",

      "usage": "consumer",
      "format": "CloudEvents/1.0",

      "config": {
        "protocol": "MQTT/5.0",
        "endpoints": [
            { "uri": "mqtt://mqtt.example.com:1883" }
        ],
        "options": {
            "topic": "{deviceid}/telemetry"
        }
      },

      "messagesurl": "https://example.com/endpoints/com.example.telemetry/messages",
      "messagescount": 1,
      "messages": {
        "com.example.telemetry": {
          "messageid": "com.example.telemetry",
          "versionid": "1.0",
          "self": "https://example.com/endpoints/com.example.telemetry/messages/com.example.telemetry",
          "xid": "/endpoints/com.example.telemetry/messages/com.example.telemetry",
          "epoch": 5,
          "isdefault": true,
          "description": "device telemetry event",
          "createdat": "2024-04-30T12:00:00Z",
          "modifiedat": "2024-04-31T12:00:00Z",
          "ancestor": "1.0",

          "format": "CloudEvents/1.0",
          "metadata": {
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
              "type": "timestamp",
              "required": true
            },
            "source": {
              "type": "uritemplate",
              "value": "{deploymentid}/{deviceid}",
              "required": true
            }
          },

          "dataschemaformat": "Protobuf/3.0",
          "dataschema": "syntax = \"proto3\"; message Metrics { float metric = 1; } }",
          "datacontenttype": "Protobuf/3.0",

          "metaurl": "https://example.com/endpoints/com.example.telemetry/messages/com.example.telemetry/meta",
          "versionsurl": "https://example.com/endpoints/com.example.telemetry/messages/com.example.telemetry/versions",
          "versionscount": 1
        }
      }
    }
  }
}
```

The same metadata can be expressed by spreading the metadata across the message
definition and schema registries, which makes the definitions reusable for other
scenarios:

```yaml
{
  "$schema": "https://cloudevents.io/schemas/registry",
  "specversion": "1.0-rc1",
  "registryid": "Example Registry",
  "self": "http://example.com",
  "xid": "/",
  "epoch": 4,
  "createdat": "2024-04-30T12:00:00Z",
  "modifiedat": "2024-04-31T12:00:00Z",

  "endpointsurl": "https://example.com/endpoints",
  "endpointscount": 1,
  "endpoints": {
    "com.example.telemetry": {
      "endpointid": "com.example.telemetry",
      "self": "https://example.com/endpoints/com.example.telemetry",
      "xid": "/endpoints/com.example.telemetry",
      "epoch": 5,
      "createdat": "2024-04-30T12:00:00Z",
      "modifiedat": "2024-04-31T12:00:00Z",

      "usage": "consumer",
      "format": "CloudEvents/1.0",

      "config": {
        "protocol": "MQTT/5.0",
        "endpoints": [
            { "uri": "mqtt://mqtt.example.com:1883" }
        ],
        "options": {
            "topic": "{deviceid}/telemetry"
        }
      },

      "messagegroups": [ "#/messagegroups/com.example.telemetryEvents" ],

      "messagesurl": "https://example.com/endpoints/com.example.telemetry/messages",
      "messagescount": 0
    }
  },

  "messagegroupsurl": "https://example.com/messagegroups",
  "messagegroupscount": 1,
  "messagegroups": {
    "com.example.telemetryEvents": {
      "messageid": "com.example.telemetryEvents",
      "self": "https://example.com/messagegroups/com.example.telemetryEvents",
      "xid": "/messagegroups/com.example.telemetryEvents",
      "epoch": 3,
      "createdat": "2024-04-30T12:00:00Z",
      "modifiedat": "2024-04-31T12:00:00Z",

      "messagesurl": "https://example.com/messagegroups/com.example.telemetryEvents/messages",
      "messagescount": 1,
      "messages": {
        "com.example.telemetry": {
          "messageid": "com.example.telemetry",
          "versionid": "1.0",
          "self": "https://example.com/endpoints/com.example.telemetry/messages/com.example.telemetry",
          "xid": "/endpoints/com.example.telemetry/messages/com.example.telemetry",
          "epoch": 5,
          "isdefault": true,
          "description": "device telemetry event",
          "createdat": "2024-04-30T12:00:00Z",
          "modifiedat": "2024-04-31T12:00:00Z",
          "ancestor": "1.0",

          "format": "CloudEvents/1.0",
          "metadata": {
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
              "type": "timestamp",
              "required": true
            },
            "source": {
              "type": "uritemplate",
              "value": "{deploymentid}/{deviceid}",
              "required": true
            }
          },

          "dataschemaformat": "Protobuf/3.0",
          "dataschemauri": "#/schemagroups/com.example.telemetry/schema/com.example.telemetrydata/versions/1.0",
          "datacontenttype": "Protobuf/3.0",

          "metaurl": "https://example.com/endpoints/com.example.telemetry/messages/com.example.telemetry/meta",
          "versionsurl": "https://example.com/endpoints/com.example.telemetry/messages/com.example.telemetry/versions",
          "versionscount": 1
        }
      }
    }
  },

  "schemagroupscount": 1,
  "schemagroups": {
    "com.example.telemetry": {
      "schemagroupid": "com.example.telemetry",
      "self": "https://example.com/schemagroups/com.example.telemetry",
      "xid": "/schemagroups/com.example.telemetry",
      "epoch": 5,
      "createdat": "2024-04-30T12:00:00Z",
      "modifiedat": "2024-04-31T12:00:00Z",

      "schemascount": 1,
      "schemas": {
        "com.example.telemetrydata": {
          "schemaid": "com.example.telemetrydata",
          "versionid": "1.0",
          "self": "https://example.com/schemagroups/com.example.telemetry/schemas",
          "xid": "/schemagroups/com.example.telemetry/schemas",
          "epoch": 5,
          "isdefault": true,
          "description": "device telemetry event data",
          "createdat": "2024-04-30T12:00:00Z",
          "modifiedat": "2024-04-31T12:00:00Z",
          "ancestor": "1.0",

          "format": "Protobuf/3.0",
          "schema": "syntax = \"proto3\"; message Metrics { float metric = 1;}",

          "metaurl": "https://example.com/schemagroups/com.example.telemetry/schemas/meta",
          "versionscount": 1,
          "versionsurl": "https://example.com/schemagroups/com.example.telemetry/schemas/versions"
        }
      }
    }
  }
}
```

If we assume the message definitions and schemas to reside at an API endpoint,
an endpoint definition might just reference the associated message definition
group with a deep link to the respective object in the service:

```yaml
{
  "$schema": "https://cloudevents.io/schemas/registry",
  "specversion": "1.0-rc1",
  "registryid": "Example Registry",

  "endpointsurl": "https://example.com/endpoints",
  "endpointscount": 1,
  "endpoints": {
    "com.example.telemetry": {
      "endpointid": "com.example.telemetry",
      "self": "https://example.com/endpoints/com.example.telemetry",
      "xid": "/endpoints/com.example.telemetry",
      "epoch": 5,
      "createdat": "2024-04-30T12:00:00Z",
      "modifiedat": "2024-04-31T12:00:00Z",

      "usage": "consumer",
      "format": "CloudEvents/1.0",

      "config": {
        # ... details ...
      },

      "messagegroups": [ "https://example.com/messagegroups/com.example.telemetryEvents" ]
    }
  }
}
```

If the message definitions and schemas are stored in a file-based registry,
including files shared via public version control repositories, the reference
link will first reference the file and then the object within the file, using
[JSON Pointer][JSON Pointer] syntax:

```yaml
{
  "$schema": "https://cloudevents.io/schemas/registry",
  "specversion": "1.0-rc1",
  "registryid": "Example Registry",

  "endpointsurl": "https://example.com/endpoints",
  "endpointscount": 1,
  "endpoints": {
    "com.example.telemetry": {
      "endpointid": "com.example.telemetry",
      "self": "https://example.com/endpoints/com.example.telemetry",
      "xid": "/endpoints/com.example.telemetry",
      "epoch": 5,
      "createdat": "2024-04-30T12:00:00Z",
      "modifiedat": "2024-04-31T12:00:00Z",

      "usage": "consumer",
      "format": "CloudEvents/1.0",

      "config": {
        # ... details ...
      },

      "messagegroups": [ "https://rawdata.repos.example.com/myorg/myproject/main/example.telemetryEvents.cereg#/definitiongroups/com.example.telemetryEvents" ]
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
Formats](../message/spec.md#metadata-envelopes-and-message-protocols) section
therefore not only describes the attribute meta-schema for CloudEvents, but also
meta-schemas for the native message envelopes of MQTT, AMQP, and other messaging
protocols.

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
[CloudEvents Registry Document Schema](../cloudevents/schemas/document-schema.json),
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

```yaml
{
  "$schema": "https://cloudevents.io/schemas/registry",
  "specversion": "1.0-rc1",
  "registryid": "STRING",

  "endpointsurl": "URL",
  "endpointscount": INT,
  "endpoints": { ... },

  "definitiongroupsurl": "URL",
  "definitiongroupscount": INT,
  "definitiongroups": { ... },

  "schemagroupsurl": "URL",
  "schemagroupscount": INT,
  "schemagroups": { ... }
}
```

While the file structure leads with endpoints followed by definition groups and
then schema groups by convention, the order of the sub-registries is not
significant.

## References


[JSON Pointer]: https://www.rfc-editor.org/rfc/rfc6901
[CloudEvents]: https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md
