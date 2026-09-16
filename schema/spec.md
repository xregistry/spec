# Schema Registry Service - Version 1.0-rc4

<!-- words: formatvalidated compatibilityvalidated -->
<!-- words: formatvalidatedreason compatibilityvalidatedreason -->
<!-- words: jsonstructure jstruct namespace -->
<!-- words: namespaces targetnamespace xmlns -->

## Abstract

This specification defines a Schema Registry extension to the xRegistry
document format and API [specification][xRegistry Core]. A Schema Registry
allows for the storage, management and discovery of schema documents.

## Table of Contents

- [Abstract](#abstract)
- [Table of Contents](#table-of-contents)
- [1. Overview](#1-overview)
  - [1.1. Schemas](#11-schemas)
  - [1.2. Schema References](#12-schema-references)
  - [1.3. Versioning](#13-versioning)
  - [1.4. Document Store](#14-document-store)
- [2. Notations and Terminology](#2-notations-and-terminology)
  - [2.1. Notational Conventions](#21-notational-conventions)
  - [2.2. Terminology](#22-terminology)
    - [2.2.1. Schema](#221-schema)
  - [2.3. Schema Group](#23-schema-group)
- [3. Schema Registry Model](#3-schema-registry-model)
- [4. Schema Registry](#4-schema-registry)
  - [4.1. Schema Groups](#41-schema-groups)
  - [4.2. Schema Resources](#42-schema-resources)
  - [4.3. Schema Formats](#43-schema-formats)
    - [4.3.1. JSON Schema](#431-json-schema)
    - [4.3.2. XML Schema](#432-xml-schema)
    - [4.3.3. Apache Avro Schema](#433-apache-avro-schema)
    - [4.3.4. Protobuf Schema](#434-protobuf-schema)
    - [4.3.5. JSON Structure Schema](#435-json-structure-schema)
    - [4.3.6. Schema Object Selection](#436-schema-object-selection)

## 1. Overview

A schema registry provides a repository for managing serialization, validation,
and data type definition schemas as they are commonly used in distributed
systems. Common schema formats include JSON Schema, JSON Structure, Apache Avro
Schema, Google Protobuf Schema, and XML Schema. However, this specification does
not mandate, or limit, which schema formats are used.

### 1.1. Schemas

Schema registries are generally used to share such schemas amongst multiple
parties.

When schemas are used to drive the serialization and encoding of data, like in
the cases of Apache Avro or Google Protobuf, the deserialization of structured
data from its encoded form requires the schema to be available to the
deserializer. The compactness of these serialization formats is achieved by
externalizing type information into a schema document. The registry allows for a
publisher of data to publish the schema document and pass a reference to it, and
for a consumer of data to retrieve the schema document and use it to decode the
data.

Formats like XML and JSON do not require a schema to decode the data, but
schemas are still very useful to establish a common understanding of the data
structures that are exchanged, provide a foundation for code generation, allow
for validation of the data, and provide an anchor for documentation and semantic
information, like scientific units for numeric values, that goes beyond simple
labels and data types. Generally, it is a best practice for data structures that
are exchanged in a distributed system to be described by a schema, even if the
data serialization model does not require one.

### 1.2. Schema References

In the [CloudEvents][CloudEvents dataschema] specification, the `dataschema`
attribute holds a URI and is specifically meant to reference a schema document
residing in a registry. For example, a CloudEvent with a `dataschema` attribute
pointing to a schema version in a schema registry might look like this, using
the schema version's [`self`][xRegistry self] URL as the value of the
`dataschema` attribute:

```json
{
    "specversion": "1.0",
    "id": "1234-5678-9012",
    "type": "com.example.event",
    "source": "https://example.com/source",
    "dataschema": "https://example.com/registry/schemagroups/com.example.schemas/schemas/com.example.event/versions/1.0",
    "datacontenttype": "application/vnd.google.protobuf",
    "data_base64": "...base64-encoded-data..."
}
```

Since this URL might be a bit long, the xRegistry core specification allows for
an implementation to provide an alternative, shorter, self-referencing URL that
points to the same schema version, via the [`shortself`][xRegistry shortself]
attribute. The specification is not prescriptive about the format of the shorter
URL, but it might follow common URL-shortening practices. With that, the above
example might look like this:

```json
{
    "specversion": "1.0",
    "id": "1234-5678-9012",
    "type": "com.example.event",
    "source": "https://example.com/source",
    "dataschema": "https://example.com/$267shU79S",
    "datacontenttype": "application/vnd.google.protobuf",
    "data_base64": "...base64-encoded-data..."
}
```

### 1.3. Versioning

When schemas are used in a system, they typically evolve over time. Data
structures are extended or modified, with parts added or deprecated or even
removed. Some of these changes are compatible with existing data, while others
are not.

Serialization generally occurs based on a specific schema version that the data
publisher uses. Multiple versions of publishers might exist in the same system,
using different schema versions, which is a common occurrence in systems that
perform live updates. Once data has been published, data serialized based on
several different versions might exist in a system, in queues, in databases, or
in files.

The schema registry therefore allows managing multiple versions of schemas,
declares their lineage, and states their compatibility policy. The compatibility
policy is used to determine whether a schema change is compatible with prior
versions and whether data that has been serialized based on prior versions can
still be deserialized and/or validated using the new schema. This compatibility
check is important to ensure that changes to schemas do not inadvertently break
the ability to read existing data, and MAY be enforced by implementations of the
schema registry. The [xRegistry Core][xRegistry Core] specification defines the
versioning and compatibility relationship mechanisms.

### 1.4. Document Store

The schema registry is a document store and therefore has the
[`hasdocument`][xRegistry hasdocument] attribute defined in the xRegistry Core
attribute (implicitly) defined as `true` for the `schema` Resource.

This means that the schema registry exposes the schema document through the
Resource's document view, using the stored media type. When no Version is
explicitly selected, the [default version][xRegistry default-version] is
exposed. The applicable protocol binding defines how clients select the
document and metadata views and how those views are retrieved.

This enables the ability to provide external parties with a link that they can
use without needing to know any details about xRegistry.

The applicable protocol binding also defines how clients create or update
schema Versions through the document view.

For example, the xRegistry HTTP Binding uses the `$details` URL suffix to
access the metadata view of the schema Resource or a specific Version.

Beyond this, the [xRegistry Core][xRegistry Core] specification provides rich
filtering and export/import capabilities, which can be used to retrieve schema
documents in bulk, or to export/import schemas and schema Versions in a
structured way. The [xRegistry pagination][xRegistry pagination] mechanism can
be used to retrieve large sets of schemas or schema versions in a paginated
manner.

## 2. Notations and Terminology

### 2.1. Notational Conventions

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD",
"SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be
interpreted as described in [RFC 2119](https://tools.ietf.org/html/rfc2119).

For clarity, OPTIONAL attributes (specification-defined and extensions) are
OPTIONAL for clients to use, but the servers' responsibility will vary.
Server-unknown extension attributes MUST be silently stored in the backing
datastore. Specification-defined and server-known extension attributes MUST
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

### 2.2. Terminology

This specification defines the following terms:

#### 2.2.1. Schema

We use the term **schema** (or schema Resource) in this specification as a
logical grouping of **schema Versions**. A **schema Version** is a concrete
document. The **schema** Resource is a semantic umbrella formed around one or
more concrete schema Version documents that represent iterations of the same
logical schema. Per the definition of the [`compatibility`][xRegistry
compatibility] attribute, all Versions of a single **schema** MUST adhere to the
rules defined by the `compatibility` attribute. Any breaking change MUST result
in a new **schema** Resource being created.

In terms of versioning, you can think of a **schema** as a collection of
versions that are compatible according to the selected `compatibility` mode.
The [`deprecated`][xRegistry deprecated] attribute MAY be used to indicate the
appropriate new schema to use following a breaking change.

### 2.3. Schema Group

A Schema Group is a container for schemas that are related to each other in
some application-defined way. This specification does not impose any
restrictions on what schemas can be contained in a Schema Group.

## 3. Schema Registry Model

The authoritative xRegistry extension model of the Schema Registry resides in
the [model.json](model.json) file.

For easy reference, the JSON serialization of a Schema Registry adheres to
this form:

```yaml
{
  "specversion": "<STRING>",                       # xRegistry core attributes
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

  "schemagroupsurl": "<URL>",                      # SchemaGroups collection
  "schemagroupscount": <UINTEGER>,
  "schemagroups": {
    "KEY": {                                       # schemagroupid
      "schemagroupid": "<STRING>",                 # xRegistry core attributes
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
      "format": "<STRING>", ?

      "schemasurl": "<URL>",                       # Schemas collection
      "schemascount": <UINTEGER>,
      "schemas": {
        "KEY": {                                   # schemaid
          "schemaid": "<STRING>",                  # xRegistry core attributes
          "versionid": "<STRING>",
          "self": "<URL>",
          "xid": "<XID>",

          #  Start of default Version's attributes
          "epoch": <UINTEGER>,
          "name": "<STRING>", ?                    # Version level attrs
          "description": "<STRING>", ?
          "documentation": "<URL>", ?
          "labels": { "<STRING>": "<STRING>" * }, ?
          "createdat": "<TIMESTAMP>",
          "modifiedat": "<TIMESTAMP>",
          "ancestorid": "<STRING>",
          "contenttype": "<STRING>", ?
          "format": "<STRING>", ?
          "formatvalidated": <BOOLEAN>, ?
          "formatvalidatedreason": "<STRING>", ?
          "compatibilityvalidated": <BOOLEAN>, ?
          "compatibilityvalidatedreason": "<STRING>", ?

          "schemaurl": "<URL>", ?
          "schema": <ANY> ?
          "schemabase64": "<STRING>", ?
          #  End of default Version's attributes

          "metaurl": "<URL>",                      # Resource level attrs
          "meta": { ... }, ?

          "versionsurl": "<URL>",
          "versionscount": <UINTEGER>,
          "versions": { ... } ?
        } *
      } ?
    } *
  } ?
}
```

## 4. Schema Registry

The Schema Registry is a metadata store for organizing schemas and schema
Versions of any kind; it is a document store.

Implementations of this specification MAY include additional extension
attributes, including the `*` attribute of type `any`.

Since the Schema Registry is an application of the [xRegistry
specification][xRegistry Core], all attributes for Groups, Resources, and
Resource Version objects are inherited from there.

### 4.1. Schema Groups

The Group (`<GROUP>`) name for the Schema Registry is `schemagroup` (singular).
The plural, used as the collection name, is `schemagroups`. The Schema Group
does not have any specific extension attributes.

A schema group is a collection of schemas that are related to each other in
some application-defined way. A Schema Group does not impose any restrictions
on the contained schemas, meaning that a Schema Group MAY contain schemas of
different formats.

Every schema (i.e. the schema Resource) MUST reside inside a Schema Group.

Example:

The following abbreviated Schema Registry content shows a single Schema Group
containing 5 schemas.

```yaml
{
  "specversion": "1.0-rc4",
  # other xRegistry top-level attributes excluded for brevity

  "schemagroupsurl": "http://example.com/schemagroups",
  "schemagroupscount": 1,
  "schemagroups": {
    "com.example.schemas": {
      "schemagroupid": "com.example.schemas",
      # Other xRegistry Group-level attributes excluded for brevity

      "schemasurl": "https://example.com/schemagroups/com.example.schemas/schemas",
      "schemascount": 5
    }
  }
}
```

There might be cases where all schemas within a schemagroup need to have the
same `format` value. To enable this, set the schemagroup's `format` value to
the string that all schemas/Versions within that schemagroup need to use.

Additionally, if desired, a schemagroup-instance level constraint MAY be added:

```yaml
"constraints": {
  "schemas.format": {
    "default": "JsonSchema/draft-07"
  }
}
```

This will define a schemagroup-specific default value for the schemas' `format`
value so clients would not need to specify it manually for each schema.

### 4.2. Schema Resources

The Resource (`<RESOURCE>`) inside of Schema Groups is named `schema`. The
plural, used as the collection name, is `schemas`. Any single `schema` is a
container for one or more `versions`, which hold the concrete schema documents
or schema document references.

All Versions of a single Schema Resource MUST adhere to the semantic rules of
the schema's [`compatibility`][xRegistry compatibility] attribute, if specified.

Implementations of this specification MAY choose to support any of the
[`compatibility`][xRegistry compatibility] values defined in the core xRegistry
specification.

Implementations of this specification SHOULD use the xRegistry default algorithm
for generating new `versionid` values and for determining which is the latest
Version. See [Version IDs][xRegistry version-ids] for more information, but in
summary it means:

- `versionid`s are unsigned integers starting with `1`
- They monotonically increase by `1` with each new Version
- The latest is the Version with the lexically largest `versionid` value after
  all `versionid`s have been left-padded with spaces to the same length

When semantic versioning is used in a solution, it is RECOMMENDED to include a
major version identifier in the `schemaid`, like `"com.example.event.v1"` or
`"com.example.event.2024-02"`, so that incompatible, but historically related
schemas can be more easily identified by users and developers. The schema
`versionid` then functions as the semantic minor version identifier.

The [`ancestorid`][xRegistry ancestorid] attribute permits multiple version
branches to exist, and allows for implementations to determine the Version
lineage. See the [`ancestorid`][xRegistry ancestorid] attribute in the core
xRegistry specification for more information.

### 4.3. Schema Formats

This specification further refines the
[core specification's `format`](../core/spec.md#format-attribute) for use
in a Schema Registry by defining a set of common schema format names that MUST
be used for the given formats, but applications MAY define extensions for
other formats on their own.

These names do not require a Registry to support every format or version. For
each format and version it supports, a Registry MUST admit the root categories
allowed by that format, rather than imposing an object-only restriction. Other
applicable validation and compatibility requirements still apply. Parsing a
document alone does not establish support for all of its semantics.

The native document representations described below do not override Core's
[`<RESOURCE>`](../core/spec.md#resource-attribute) and
[`<RESOURCE>base64`](../core/spec.md#resourcebase64-attribute) rules. In
particular, JSON schema documents retain their native JSON value kind when
inlined in JSON metadata; they MUST NOT be wrapped in an object or converted
to a string containing JSON text. The document view exposes the document,
not its surrounding xRegistry metadata. A base64 representation encodes the
document's bytes, not a different schema representation.

- Examples:
  - `JsonSchema/draft-07`
  - `Protobuf/3`
  - `XSD/1.1`
  - `Avro/1.9`

The following abbreviated example shows three embedded `Protobuf/3` schema
Versions for a schema named `com.example.telemetrydata`:

```yaml
{
  "specversion": "1.0-rc4",
  # other xRegistry top-level attributes excluded for brevity

  "schemagroupsurl": "http://example.com/schemagroups",
  "schemagroupscount": 1,
  "schemagroups": {
    "com.example.telemetry": {
      "schemagroupid": "com.example.telemetry",
      # other xRegistry group-level attributes excluded for brevity

      "schemasurl": "http://example.com/schemagroups/com.example.telemetry/schemas",
      "schemascount": 1,
      "schemas": {
        "com.example.telemetrydata": {
          "schemaid": "com.example.telemetrydata",
          "versionid": "3",
          "isdefault": true,
          "description": "device telemetry event data",
          "ancestorid": "2",
          "format": "Protobuf/3",
          # other xRegistry default Version attributes excluded for brevity

          "schema": "syntax = \"proto3\"; message Metrics { float metric = 1; string unit = 2; string description = 3; } }",

          "metaurl": "http://example.com/schemagroups/com.example.telemetry/schemas/com.example.telemetrydata/meta",

          "versionsurl": "http://example.com/schemagroups/com.example.telemetry/schemas/com.example.telemetrydata/versions",
          "versionscount": 3,
          "versions": {
            "1": {
              "schemaid": "com.example.telemetrydata",
              "versionid": "1",
              "isdefault": false,
              "description": "device telemetry event data",
              "ancestorid": "1",
              "format": "Protobuf/3",
              # other xRegistry Version-level attributes excluded for brevity

              "schema": "syntax = \"proto3\"; message Metrics { float metric = 1; } }"
            },
            "2": {
              "schemaid": "com.example.telemetrydata",
              "versionid": "2",
              "isdefault": false,
              "description": "device telemetry event data",
              "ancestorid": "1",
              "format": "Protobuf/3",
              # other xRegistry Version-level attributes excluded for brevity

              "schema": "syntax = \"proto3\"; message Metrics { float metric = 1; string unit = 2; } }"
            },
            "3": {
              "schemaid": "com.example.telemetrydata",
              "versionid": "3",
              "isdefault": true,
              "description": "device telemetry event data",
              "ancestorid": "2",
              "format": "Protobuf/3",
              # other xRegistry Version-level attributes excluded for brevity

              "schema": "syntax = \"proto3\"; message Metrics { float metric = 1; string unit = 2; string description = 3; } }"
            }
          }
        }
      }
    }
  }
}
```

#### 4.3.1. JSON Schema

The [`format`](../core/spec.md#format-attribute) identifier for JSON Schema is
`JsonSchema`.

When the `format` attribute is set to `JsonSchema`, the schema Resource's
document is a JSON Schema conformant with the declared version. For the
versions listed below, its root is a JSON object or a JSON boolean, `true` or
`false`, as defined by [JSON Schema][JSON Schema Core]. Both boolean values are
valid schemas: `true` accepts every instance and `false` rejects every instance.
An array, string, number or JSON `null` is not a JSON Schema root.

When a URI, like the Message Registry's
[`dataschemauri`](../message/spec.md#dataschemauri), points to a JSON Schema
document, it MAY use a [JSON pointer][JSON pointer] expression to deep link into
the schema document to reference a particular type definition. Otherwise the
entire root schema is used, including a boolean root. A selected subschema can
also be an object or boolean; selecting a non-schema value or a location that
does not exist is an error.

JSON Pointer selectors are relative to the schema document, not its surrounding
xRegistry metadata. Their encoding and document boundary follow
[Schema Object Selection](#436-schema-object-selection). An empty JSON Pointer
selects the root; a pointer to a value that is not a schema is an error. Other
fragment forms, such as anchors, retain the meaning assigned by the declared
JSON Schema version. They MUST NOT be treated as a JSON Pointer or silently
replaced with root selection. Use a schema document URI with its own fragment
for such forms, rather than appending them to a local entity pointer.

The `format` value identifies the version of the JSON Schema specification
used to define the schema. If a schema object includes `$schema`, the version
it identifies MUST agree with `format`. Boolean roots cannot carry `$schema`;
their version is supplied by `format`.

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

These examples show complete UTF-8 JSON documents and their document media
types. When inlined in JSON metadata, `schema` has the same JSON value shown
in the last column, without an extra layer of JSON quoting.

| Format | Document `contenttype` | Document |
| --- | --- | --- |
| `JsonSchema/draft/2020-12` | `application/schema+json` | `true` |
| `JsonSchema/draft/2020-12` | `application/schema+json` | `false` |
| `JsonSchema/draft/2020-12` | `application/schema+json` | `{"type":"string"}` |

#### 4.3.2. XML Schema

The [`format`](../core/spec.md#format-attribute) identifier for XML Schema is
`XSD`. The version of the XML Schema format is the version of the W3C XML
Schema specification that is used to define the schema.

When the `format` attribute is set to `XSD`, the `schema` attribute of the
schema Resource is a string containing an XML Schema document conformant with
the declared version.

When a URI, like the Message Registry's
[`dataschemauri`](../message/spec.md#dataschemauri), points to an XML Schema
document, it MAY use an XPath expression to select an element declaration or
a simple or complex type definition in the schema document. This profile uses
[XPath 1.0][XPath] for both XSD versions listed below. The context node is the
XML document node, with context position and size both `1`. Only the XPath core
function library is available; no variables or extension functions are bound.

The expression's namespace context contains the non-empty prefix bindings on
the document's `schema` element, with `xs` reserved for
`http://www.w3.org/2001/XMLSchema` and `xml` reserved for the XML namespace.
The document's default namespace does not apply to unprefixed XPath names.
This context is fixed for the expression; it does not depend on the prefixes
chosen by the caller or on namespace declarations below the `schema` element.
The expression is encoded as specified in
[Schema Object Selection](#436-schema-object-selection).

The result MUST contain exactly one node representing an element declaration,
simple type definition or complex type definition. A scalar result, a different
kind of node, or zero or multiple matching declarations is an error. Without
a selector, the document MUST contain exactly one such declaration directly
under its `schema` element; otherwise an explicit selector MUST be supplied. This
does not make a schema with multiple declarations invalid.

For example, this schema requires an explicit selector:

```xml
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           targetNamespace="urn:example:orders">
  <xs:element name="Order" type="xs:string"/>
  <xs:element name="Cancel" type="xs:string"/>
</xs:schema>
```

The XPath `/xs:schema/xs:element[@name='Order']` selects `Order`. A URI carrying
that selector is
`https://example.com/schemas/orders.xsd#%2Fxs%3Aschema%2Fxs%3Aelement%5B%40name%3D%27Order%27%5D`.

The identifiers for the following XML Schema versions:

- 1.0: `https://www.w3.org/TR/xmlschema-1/`
- 1.1: `https://www.w3.org/TR/xmlschema11-1/`

are defined as follows:

- `XSD/1.0`
- `XSD/1.1`

#### 4.3.3. Apache Avro Schema

The [`format`](../core/spec.md#format-attribute) identifier for Apache Avro
Schema is `Avro`. The version of the Apache Avro Schema format is the version
of the Apache Avro Schema release that is used to define the schema.

When the `format` attribute is set to `Avro`, the schema Resource's document
is an Avro schema conformant with the declared version. As defined by
[Apache Avro][Avro Specification], its JSON representation is a string naming
a defined type, an object defining a type, or an array defining a union.
This includes primitive schemas, named record, enum and fixed schemas, and
array, map and union schemas. A named type reference still requires that type
to be defined in the applicable Avro name context; admission of string roots
does not make an undefined name valid. JSON booleans, numbers and `null` are
not Avro schemas. The JSON string `"null"` is the schema for Avro's null type.

Examples:

- `Avro/1.8.2` is the identifier for the Apache Avro release 1.8.2.
- `Avro/1.11.0` is the identifier for the Apache Avro release 1.11.0

When a URI, like the Message Registry's
[`dataschemauri`](../message/spec.md#dataschemauri), points to an Avro Schema
document, it MAY use a URI fragment suffix `[:]{type-name}` to deep link into
the schema document to reference a particular type definition. Otherwise the
entire root schema is used, including primitive, array, map and union schemas.
A union is not an implicit selection of its first branch. The ':' character
is used as a separator when the URI already contains a fragment.

The selected declaration can be a record, enum or fixed type. Its identity is
its case-sensitive [Avro full name][Avro Names], including the namespace
determined by Avro's name rules. A qualified selector MUST match that full name
exactly. An unqualified selector is accepted only when exactly one named
declaration in the document has that simple name. Aliases do not participate
in this lookup. A missing or ambiguous name is an error; no namespace or first
union branch is guessed. This does not change selection of the root when no
name is supplied, or turn an unnamed schema into a named declaration.

These examples show complete UTF-8 JSON documents. Their document media type
is `application/json`; it does not describe the encoding of data governed by
the schema. In particular, the primitive string schema's document bytes include
the JSON quotation marks in `"string"`, unlike a plain text document containing
`string`. In JSON metadata its `schema` value is the JSON string `"string"`.

| Format | Document `contenttype` | Document |
| --- | --- | --- |
| `Avro/1.12.0` | `application/json` | `"string"` |
| `Avro/1.12.0` | `application/json` | `["null","string"]` |
| `Avro/1.12.0` | `application/json` | `{"type":"record","name":"Reading","fields":[{"name":"value","type":"long"}]}` |

Clients that previously assumed every schema was a JSON object need to preserve
these native root kinds. They MUST NOT convert a primitive or union root to
a record merely to fit an object-only representation.

Examples:

- If the Avro schema document is referenced using the URI
`https://example.com/avro/telemetry.avsc#TelemetryEvent`, the URI fragment
`#TelemetryEvent` references the record declaration of the `TelemetryEvent`
record.
- If the Avro schema document is a local Schema Registry reference like
`#/schemagroups/com.example.telemetry/schemas/com.example.telemetrydata`, in
which the reference is already in the form of a URI fragment, the suffix is
appended, separated by a colon, for instance
`.../com.example.telemetrydata:TelemetryEvent`.

#### 4.3.4. Protobuf Schema

The [`format`](../core/spec.md#format-attribute) identifier for Protobuf Schema
is `Protobuf`. The version of the Protobuf Schema format is the version of the
Protobuf syntax that is used to define the schema.

When the `format` attribute is set to `Protobuf`, the `schema` attribute of the
schema Resource is a string containing a Protobuf schema document conformant
with the declared version.

- `Protobuf/3` is the identifier for the Protobuf syntax version 3.
- `Protobuf/2` is the identifier for the Protobuf syntax version 2.

A URI, like the Message Registry's
[`dataschemauri`](../message/spec.md#dataschemauri), that points to a Protobuf
Schema document MUST reference a Protobuf `message` declaration contained in the
schema document. If the URI does not contain a fragment, the message name MUST
be appended as a URI fragment using `#{message-name}`. If the URI already
contains a fragment, the message name MUST be appended to the fragment using
`:{message-name}`.

The selected declaration MUST be a message, not an enum, service or field.
Its full name includes the Protobuf package and enclosing message names. A
qualified selector, with or without Protobuf's leading `.`, MUST match the full
name exactly. An unqualified selector is accepted only when exactly one message
declaration in the document has that simple name. Partial suffix matching,
choosing the first message, and guessing a package are not permitted. Missing
or ambiguous names are errors. These name rules follow the
[Protobuf language's scope rules][Protobuf Names]; the document and selector
encoding rules below apply without changing the `#` and `:` separators.

Examples:

- If the Protobuf schema document is referenced using the URI
  `https://example.com/protobuf/telemetry.proto`, the URI fragment
  `#TelemetryEvent` references the message declaration of the `TelemetryEvent`
  message.
- If the Protobuf schema document is a local Schema Registry reference like
  `#/schemagroups/com.example.telemetry/schemas/com.example.telemetrydata`, in
  which the reference is already in the form of a URI fragment, the suffix
  is appended, separated by a colon, for instance
  `.../com.example.telemetrydata:TelemetryEvent`.

#### 4.3.5. JSON Structure Schema

The [`format`](../core/spec.md#format-attribute) identifier for JSON Structure
Schema is `JsonStructure`. When the `format` attribute is set to `JsonStructure`,
the `schema` attribute of the schema Resource is a JSON object representing a JSON
Structure schema document [JSTRUCT-CORE].

The version identifier follows the pattern `JsonStructure/{version}`, where
`{version}` is the version of the JSON Structure Core specification that is
used to define the schema.

`JsonStructure/draft-04` is the identifier for the Internet-Draft version 04 of
the JSON Structure Core specification. If a future RFC is published, the
version identifier will be updated to reflect the RFC number, for example
`JsonStructure/rfc-0000`.

When a URI, like the Message Registry's
[`dataschemauri`](../message/spec.md#dataschemauri), points to a JSON Structure
schema document, it MAY use a [JSON pointer][JSON pointer] expression to deep
link into the schema document to reference a particular type definition. This is
typically used to reference type definitions within the `definitions` namespace.

For `JsonStructure/draft-04`, an explicit non-empty pointer MUST select a
reusable type declaration within `definitions`, including nested namespaces.
Selecting a namespace object or an inline compound type that the native format
does not permit to be referenced externally is an error. A type declaration
is not limited to the `object` data type.

Without an explicit selection, use the document's inline root type or its
`$root` designation, as defined by [JSON Structure Core draft 04][JSTRUCT-04].
`$root` selects a type within `definitions`, and is mutually exclusive with
an inline root `type`. A document with neither has no selected root, even if
it contains only one reusable declaration. An explicit pointer MUST then be
supplied. This preserves primitive and compound roots, and roots designated
by `$root`, including type unions; it does not infer a root from declaration
order or mistake a namespace for a type.

Examples:

- `https://example.com/schemas/person.json#/definitions/Employee` uses the
  `#/definitions/Employee` fragment to reference the `Employee` type definition.
- For local Schema Registry references like
  `#/schemagroups/com.example.schemas/schemas/com.example.person/versions/1/definitions/Employee`,
  append the JSON Pointer fragment to reference a specific type within that schema.

#### 4.3.6. Schema Object Selection

A schema object reference has two distinct parts: the document locator and
the format-defined selector within that document. The locator can identify a
Schema Resource, selecting its default Version's document, or a particular
Schema Version. Selecting an object does not change that owning entity.
These rules define selection, not which formats a Registry has to support,
and do not override the native format's schema validity rules.

For a schema document URI without a fragment, append the selector after `#`.
For a locator that already uses a fragment to identify a Schema entity in
an xRegistry document, the boundary of that entity MUST be established before
interpreting a selector:

- For JSON Schema and JSON Structure JSON Pointer selectors, append the
  pointer's tokens to the entity pointer. For example, a known Version locator
  `#/schemagroups/g/schemas/s/versions/1` and selector `/definitions/T` give
  `#/schemagroups/g/schemas/s/versions/1/definitions/T`. No extra `schema`
  metadata token is inserted.
- For Avro names, Protobuf names and XPath expressions, append `:` followed
  by the encoded selector. This also applies to an entity pointer in an
  external xRegistry document, such as
  `https://example.com/registry.json#/schemagroups/g/schemas/s:Event`.

The entity boundary comes from the containing xRegistry document's metadata
or an explicitly supplied owning entity, not from stripping a suffix from an
identifier. If more than one owner/selector interpretation is possible, the
reference MUST be rejected as ambiguous. For example,
`#/schemagroups/g/schemas/a:B` can denote the literal Resource `a:B` or select
`B` within Resource `a`. Neither interpretation takes precedence. The same
rule applies if trailing pointer tokens could identify a Version or a member
of a Resource's schema document. An explicit owner can remove the ambiguity;
otherwise use a schema document URI with a separate selector fragment.

When constructing local entity pointers, literal colons in identifiers MUST
be percent-encoded as `%3A`; for example,
`#/schemagroups/g/schemas/a%3AB` denotes the literal Resource `a:B`, not a
selector on `a`. An encoded colon MUST NOT be promoted to a separator.
Existing references containing colons that are not percent-encoded remain
usable when their owner boundary is unambiguous, but MUST NOT be silently
reinterpreted when another matching entity is added.

Encode each selector as UTF-8 followed by URI fragment percent-encoding.
Identify the document boundary and any separating literal `:` before decoding
the selector. Percent-decode the selected component exactly once. For JSON
Pointers, then apply [RFC 6901][JSON Pointer], including its `~1` and `~0`
token escapes; do not apply those token escapes to names or XPath expressions.
Thus a literal `%2F` in a JSON member name is encoded as `%252F`, not decoded
a second time into `/`. Preserve case and Unicode code points. Invalid escapes
or invalid UTF-8 are errors. Decoding a selector MUST NOT normalize or change
the document locator's unrelated URI components.

An inline schema has no inherent document URI. Apply the format's root
selection rule, or an explicitly supplied selector in a context that supports
one, without inventing a locator or publishing the schema. If the document,
owner context, needed schema dependencies, or the selector facility is
unavailable, report selection as unresolved or unsupported rather than claim
that a concrete object has been selected. Selection does not require automatic
network acquisition. When the needed information is available, a missing,
invalid or ambiguous target is an error, not permission to choose another
object or a different Version.

Consumers that used suffix stripping, implicit namespace lookup or first-root
selection need to retain explicit owner and selector information. Producers
can use encoded literal identifiers and fully qualified names to avoid those
heuristics. These rules do not alter unrelated URI equality requirements.

Like the [xRegistry Core][xRegistry Core] specification, this specification does
not explicitly address authentication or authorization levels of users, nor how
to securely protect the APIs.

It is expected that any implementation of this specification will use
authentication and authorization mechanisms that are appropriate for the
application domain and the deployment environment. This MAY include, but is not
limited to, OAuth 2.0, OpenID Connect, API keys, or other mechanisms appropriate
for the use case.

For authorization, the `schemagroup` concept provides a natural authorization
boundary, where users can be granted access to specific schema groups, and
therefore to the schemas contained within those groups. The `schema` Resource
itself can be used to further restrict access to specific schema Versions within
a schema, allowing for fine-grained access control.

---

[JSON Pointer]: https://www.rfc-editor.org/rfc/rfc6901
[JSON Schema Core]: https://json-schema.org/draft/2020-12/json-schema-core#section-4.3
[Avro Specification]: https://avro.apache.org/docs/1.12.0/specification/
[XPath]: https://www.w3.org/TR/1999/REC-xpath-19991116/
[Avro Names]: https://avro.apache.org/docs/1.12.0/specification/
[Protobuf Names]: https://protobuf.dev/programming-guides/proto3/
[JSTRUCT-CORE]: https://json-structure.github.io/core/draft-vasters-json-structure-core.html
[JSTRUCT-04]: https://www.ietf.org/archive/id/draft-vasters-json-structure-core-04.html
[CloudEvents dataschema]: https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md#dataschema
[xRegistry Core]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html
[xRegistry self]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#self-attribute
[xRegistry shortself]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#shortself-attribute
[xRegistry compatibility]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#compatibility-attribute
[xRegistry version-ids]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#version-ids
[xRegistry attributes-and-extensions]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#attributes-and-extensions
[xRegistry ancestorid]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#ancestorid-attribute
[xRegistry pagination]: https://xregistry.io/xreg/xregistryspecs/pagination-v1/docs/spec.html
[xRegistry deprecated]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#deprecated
[xRegistry default-version]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#registry-design
[xRegistry hasdocument]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#hasdocument
