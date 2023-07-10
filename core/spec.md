# Registry Service - Version 0.5-wip

## Abstract

A Registry Service exposes Resources, and their metadata, for the purposes
of enabling discovery of those Resources for either end-user consumption or
automation and tooling.

## Table of Contents

- [Overview](#overview)
- [Notations and Terminology](#notations-and-terminology)
  - [Notational Conventions](#notational-conventions)
  - [Terminology](#terminology)
- [Registry Formats and APIs](#registry-formats-and-apis)
  - [Attributes and Extensions](#attributes-and-extensions)
  - [Registry APIs](#registry-apis)
    - [Registry Model](#registry-model)
    - [Registry Collections](#registry-collections)
    - [Registry Entity](#registry-entity)
    - [Groups](#groups)
    - [Resources](#resources)
    - [Versions](#versions)
  - [Inlining](#inlining)
  - [Filtering](#filtering)

## Overview

A Registry Service is one that manages metadata about Resources. At its core,
the management of an individual Resource is simply a REST-based interface for
creating, modifying and deleting the Resource. However, many Resource models
share a common pattern of grouping Resources (eg. by their "format") and can
optionally support versioning of the Resources. This specification aims to
provide a common interaction pattern for these types of services with the goal
of providing an interoperable framework that will enable common tooling and
automation to be created.

This document is meant to be a framework from which additional specifications
can be defined that expose model specific Resources and metadata.

For easy reference, the serialization of a Registry adheres to this form:

``` text
{
  "specVersion": "STRING",
  "id": "STRING",
  "name": "STRING", ?
  "self": "URL",
  "description": "STRING", ?
  "documentation": "URL", ?
  "tags": { "STRING": "STRING" * }, ?

  "model": {                            # only if inlined
    "schema": "URI-Reference", ?        # schema doc for the entire Registry
    "groups": [
      { "singular": "STRING",           # eg. "endpoint"
        "plural": "STRING",             # eg. "endpoints"
        "schema": "URI-Reference", ?    # schema doc for the group

        "resources": [
          { "singular": "STRING",       # eg. "definition"
            "plural": "STRING",         # eg. "definitions"
            "versions": UINT ?          # num Versions(>=0). Def=1, 0=unlimited
            "versionId": BOOL, ?         # Supports client specific Version IDs
            "latest": BOOL ?             # Supports client "latest" selection
          } *
        ] ?
      } *
    ] ?
  } ?

  # Repeat for each Group type
  "GROUPsUrl": "URL",                              # eg. "endpointsUrl"
  "GROUPsCount": INT                               # eg. "endpointsCount"
  "GROUPs": {                                      # only if inlined
    "ID": {                                        # the Group id
      "id": "STRING",                              # a Group
      "name": "STRING", ?
      "epoch": UINT,
      "self": "URL",
      "description": "STRING", ?
      "documentation": "URL", ?
      "tags": { "STRING": "STRING" * }, ?
      "format": "STRING", ?
      "createdBy": "STRING", ?
      "createdOn": "TIME", ?
      "modifiedBy": "STRING", ?
      "modifiedOn": "TIME", ?

      # Repeat for each Resource type in the Group
      "RESOURCEsUrl": "URL",                       # eg. "definitionsUrl"
      "RESOURCEsCount": INT,                       # eg. "definitionsCount"
      "RESOURCEs": {                               # only if inlined
        "ID": {                                    # the Resource id
          "id": "STRING",
          "name": "STRING", ?
          "epoch": UINT,
          "self": "URL",
          "latestId": "STRING",
          "latestUrl": "URL",
          "description": "STRING", ?
          "documentation": "URL", ?
          "tags": { "STRING": "STRING" * }, ?
          "format": "STRING", ?
          "createdBy": "STRING", ?
          "createdOn": "TIME", ?
          "modifiedBy": "STRING", ?
          "modifiedOn": "TIME", ?

          "RESOURCEUrl": "URL", ?                  # if not local
          "RESOURCE": { Resource contents }, ?     # if inlined & JSON
          "RESOURCEBase64": "STRING", ?            # if inlined & ~JSON

          "versionsUrl": "URL",
          "versionsCount": INT,
          "versions": {                            # only if inlined
            "ID": {                                # the Version id
              "id": "STRING",
              "name": "STRING", ?
              "epoch": UINT,
              "self": "URL",
              "description": "STRING", ?
              "documentation": "URL", ?
              "tags": { "STRING": "STRING" * }, ?
              "format": "STRING", ?
              "createdBy": "STRING", ?
              "createdOn": "TIME", ?
              "modifiedBy": "STRING", ?
              "modifiedOn": "TIME", ?

              "RESOURCEUrl": "URL", ?              # if not local
              "RESOURCE": { Resource contents }, ? # if inlined & JSON
              "RESOURCEBase64": "STRING" ?         # if inlined & ~JSON
            } *
          } ?
        } *
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

For clarity, when a feature is marked as "OPTIONAL" this means that it is
OPTIONAL for both the sender and receiver of a message to support that
feature. In other words, a sender can choose to include that feature in a
message if it wants, and a receiver can choose to support that feature if it
wants. A receiver that does not support that feature is free to take any
action it wishes, including no action or generating an error, as long as
doing so does not violate other requirements defined by this specification.
However, the RECOMMENDED action is to ignore it. The sender SHOULD be prepared
for the situation where a receiver ignores that feature. An
intermediary SHOULD forward OPTIONAL attributes.

In the pseudo JSON format snippets `?` means the preceding attribute is
OPTIONAL, `*` means the preceding attribute MAY appear zero or more times,
and `+` means the preceding attribute MUST appear at least once.

Use of the words `GROUP` and `RESOURCE` are meant to represent the singular
form of a Group and Resource type being used. While `GROUPs` and `RESOURCEs`
are the plural form of those respective types.

The following are used to denote data types:
- `BOOLEAN` - case sensitive `true` or `false`
- `DECIMAL` - Number (integer or floating point)
- `INT` - Signed integer
- `STRING` - Sequence of Unicode characters
- `TIME` - an [RFC3339](https://tools.ietf.org/html/rfc3339) timestamp
- `UINT` - Unsigned integer
- `URI` - Absolute URI as defined in [RFC 3986 Section 4.3](https://tools.ietf.org/html/rfc3986#section-4.3)
- `URI-Reference` - URI-reference as defined in [RFC 3986 Section 4.1](https://tools.ietf.org/html/rfc3986#section-4.1)
- `URL` - URL as defined in [RFC 1738](https://datatracker.ietf.org/doc/html/rfc1738)

### Terminology

This specification defines the following terms:

#### Group

An entity that acts as a collection of related Resources.

#### Registry

An implementation of this specification. Typically, the implementation would
include model specific Groups, Resources and extension attributes.

#### Resource

A Resource is the main entity that is stored within a Registry Service. It
MAY be versioned and grouped as needed.

## Registry Formats and APIs

This section defines common Registry metadata attributes and APIs. It is an
explicit goal for this specification that metadata can be created and managed in
files in a file system, for instance in a Git repository, and also managed in a
Registry service that implements the API described here.

For instance, during development of a module, the metadata about the events
raised by the modules will best be managed in a file that resides alongside the
module's source code. When the module is ready to be deployed into a concrete
system, the metadata about the events will be registered in a Registry service
along with the endpoint where those events can be subscribed to or consumed
from, and which allows discovery of the endpoint and all related metadata by
other systems at runtime.

Therefore, the hierarchical structure of the Registry model is defined in such
a way that it can be represented in a single file, including but not limited
to JSON, or via the entity graph of a REST API.

In the remainder of this specification, in particular when defining the
attributes of the Registry entities, the terms "document view" or "API view"
will be used to indicate whether the serialization of the entity in question
is meant for use as a stand-alone document or as part of a REST API message
exchange.

### Attributes and Extensions

Unless otherwise noted, all attributes MUST be mutable.

Implementations of this specification MAY define additional (extension)
attributes, and they MAY appear at any level of the model. However they MUST
adhere to the following rules:

- it is STRONGLY RECOMMENDED that they be named in such a way as to avoid
  potential conflicts with future Registry Service attributes. For example,
  use of a model (or domain) specific prefix can help
- they MUST differ from sibling attributes irrespective of case. This avoids
  potential conflicts if the attributes are serialized in a case-insensitive
  situation, such as HTTP headers
- for case sensitive serializations, it is RECOMMENDED that attribute names
  be defined in camelCase and acronyms have only their first letter
  capitalized. For example, `Id` not `ID`
- they MUST only be of type: BOOLEAN (case sensitive `true` or `false`),
  DECIMAL, or STRING. Subtypes of these MAY be used to restrict the
  allowable syntax of their values. For example, using TIME in place of STRING
- the string serialization of the attribute name and its value MUST NOT exceed
  4096 bytes. This is to ensure that it can appear in an HTTP header without
  exceeding implemantion limits (see
  [RFC6265/Limits](https://datatracker.ietf.org/doc/html/rfc6265#section-6.1)).
  In cases where larger amounts of data is needed, it is RECOMMENDED that
  an attribute (defined as a URL) be defined that references a separate
  document. For example, `documentation` can be considered such an attribute
  for `description`

In situations where an attribute is serialized in a case-sensitive situation,
then the case specified by this specification, or the defining extension
specification, MUST be adhere to.

The following attributes are used by one or more entities defined by this
specification. They are defined here once rather than repeating them
throughout the specification.

For easy reference, the serialization these attributes adheres to this form:
- `"id": "STRING"`
- `"name": "STRING"`
- `"epoch": UINT`
- `"self": "URL"`
- `"description": "STRING"`
- `"documentation": "URL"`
- `"tags": { "STRING": "STRING" * }`
- `"format": "STRING"`
- `"createdBy": "STRING"`
- `"createdOn": "TIME"`
- `"modifiedBy": "STRING"`
- `"modifiedOn": "TIME"`

#### `id`

- Type: String
- Description: An immutable unique identifier of the entity
- Constraints:
  - MUST be a non-empty string consisting of [RFC3986 `unreserved`
    characters](https://datatracker.ietf.org/doc/html/rfc3986#section-2.3)
    (ALPHA / DIGIT / "-" / "." / "_" / "~").
  - MUST be case-insensitive unique within the scope of the entity's parent.
    In the case of the `id` for the Registry itself, the uniqueness scope will
    be based on where the Registry is used. For example, a publicly accessible
    Registry might want to consider using a UUID, while a private Registry
    does not need to be so widely unique
  - MUST be immutable
- Examples:
  - `a183e0a9-abf8-4763-99bc-e6b7fcc9544b`
  - `myEntity`
  - `myEntity.example.com`

Note, since `id` is immutable, in order to change its value a new entity would
need to be created that is a deep-copy of the existing entity. Then the
existing entity can be deleted.

#### `name`

- Type: String
- Description: A human readable name of the entity. This is often used
  as the "display name" for an entity rather than the `id` especially when
  the `id` might be something like a UUID. In cases where `name` is OPTIONAL
  and absent, the `id` value SHOULD be displayed in its place.

  Note that implementations MAY choose to enforce constraints on this value.
  For example, they could mandate that `id` and `name` be the same value.
  How any such requirement is shared with all parties is out of scope of this
  specification
- Constraints:
  - MUST be non-empty
- Examples:
  - `My Endpoints`

#### `epoch`

- Type: Unsigned Integer
- Description: A numeric value used to determine whether an entity has been
  modified. Each time the associated entity is updated, this value MUST be
  set to a new value that is greater than the current one.
  Note, this attribute is most often managed by the Registry itself.
  Additionally, if a new Version of a Resource is created that is based on
  existing Version of that Resource, then the new Version's `epoch` value MAY
  be reset (eg. to zero) since the scope of its values is the Version and not
  the entire Resource
- Constraints:
  - MUST be an unsigned integer equal to or greater than zero
  - MUST increase in value each time the entity is updated
- Examples:
  - `1`, `2`, `3`

#### `self`

- Type: URL
- Description: A unique absolute URL for an entity. In the case of pointing
  to an entity in a [Registry Collection](#registry-collections), the URL MUST
  be a combination of the base URL for the collection appended with the `id`
  of the entity
- Constraints:
  - MUST be a non-empty absolute URL
  - MUST be a read-only attribute in API view
- Examples:
  - `https://example.com/registry/endpoints/123`

#### `description`

- Type: String
- Description: A human readable summary of the purpose of the entity
- Constraints:
  - When this attribute has no value, or is an empty string, it MAY be
    excluded from the serialization of the owning entity
- Examples:
  - `A queue of the sensor generated messages`

#### `documentation`

- Type: URL
- Description: A URL to additional documentation about this entity.
  This specification does not place any constraints on the data returned from
  an HTTP `GET` to this value
- Constraints:
  - MUST be a non-empty URL
  - MUST support an HTTP(s) `GET` to this URL
- Examples:
  - `https://example.com/docs/myQueue`

#### `tags`

- Type: Map of name/value string pairs
- Description: A mechanism in which additional metadata about the entity can
  be stored without changing the schema of the entity
- Constraints:
  - MUST be a map of zero or more name/value string pairs
  - each name MUST be a non-empty string consisting of only alphanumeric
    characters, `-`, `_` or a `.`; be no longer than 63 characters;
    start with an alphanumeric character and be unique within the scope of
    this map
  - Values MAY be empty strings
  - When serialized as a string (e.g. in an HTTP header), the serialization
    SHOULD be in JSON without line-breaks
- Examples:
  - `{ "owner": "John", "verified": "" }`

#### `format`

- Type: String
- Description: The name of the specification that defines the Resource
  stored in the registry. Often it is difficult to unambiguously determine
  what a Resource is via simple inspect of its serialization. This attribute
  provides a mechanism by which it can be determined without examination of
  the Resource at all
- Constraints:
  - if present, MUST be a non-empty string of the form `SPEC[/VERSION]`,
    where `SPEC` is the name of the specification that defines the Resource.
    An OPTIONAL `VERSION` value SHOULD be included if there are multiple
    versions of the specification available
  - for comparison purposes, this attribute MUST be considered case sensitive
  - If a `VERSION` is specified at the Group level, all Resources within that
    Group MUST have a `VERSION` value that is at least as precise as its
    Group, and MUST NOT be more open. For example, if a Group had a
    `format` value of `myspec`, then Resources within that Group can have
    `format` values of `myspec` or `myspec/1.0`. However, if a Group has a
    value of `myspec/1.0` it would be invalid for a Resource to have a value of
    `myspec/2.0` or just `myspec`. Additionally, if a Group does not have
    a `format` attribute then there are no constraints on its Resources
    `format` attributes
  - This specification places no restriction on the case of the `SPEC` value
    or on the syntax of the `VERSION` value
- Examples:
  - `CloudEvents/1.0`
  - `MQTT`

#### `createdBy`

- Type: String
- Description: A reference to the user or component that was responsible for
  the creation of this entity. This specification makes no requirement on
  the semantics or syntax of this value
- Constraints:
  - When this attribute has no value, or is an empty string, it MAY be
    excluded from the serialization of the owning entity
  - MUST be a read-only attribute in API view
- Examples:
  - `John Smith`
  - `john.smith@example.com`

#### `createdOn`

- Type: Timestamp
- Description: The date/time of when the entity was created
- Constraints:
  - MUST be a [RFC3339](https://tools.ietf.org/html/rfc3339) timestamp
  - MUST be a read-only attribute in API view
- Examples:
  - `2030-12-19T06:00:00Z`

#### `modifiedBy`

- Type: String
- Description: A reference to the user or component that was responsible for
  the latest update of this entity. This specification makes no requirement
  on the semantics or syntax of this value
- Constraints:
  - When this attribute has no value, or is an empty string, it MAY be
    excluded from the serialization of the owning entity
  - MUST be a read-only attribute in API view
- Examples:
  - `John Smith`
  - `john.smith@example.com`

#### `modifiedOn`

- Type: Timestamp
- Description: The date/time of when the entity was last updated
- Constraints:
  - MUST be a [RFC3339](https://tools.ietf.org/html/rfc3339) timestamp
  - MUST be a read-only attribute in API view
- Examples:
  - `2030-12-19T06:00:00Z`

### Registry APIs

This specification defines the following API patterns:

``` text
/                                              # Access the Registry
/model                                         # Access the Registry model definition
/GROUPs                                        # Access a Group Type
/GROUPs/gID                                    # Access a Group
/GROUPs/gID/RESOURCEs                          # Access a Resource Type
/GROUPs/gID/RESOURCEs/rID                      # Access the latest Resource Version
/GROUPs/gID/RESOURCEs/rID?meta                 # Metadata about the latest Resource Version
/GROUPs/gID/RESOURCEs/rID/versions             # Show versions of a Resource
/GROUPs/gID/RESOURCEs/rID/versions/vID         # Access a Version
/GROUPs/gID/RESOURCEs/rID/versions/vID?meta    # Metadata about a Version
```

Where:
- `GROUPs` is a Group name (plural). eg. `endpoints`
- `gID` is the `id` of a single Group
- `RESOURCEs` is the type of Resource (plural). eg. `definitions`
- `rID` is the `id` of a single Resource
- `vID` is the `id` of a Version of a Resource

These acronyms definitions apply to the remainder of this specification.

While these APIs are shown to be at the root path of a Registry Service,
implementation MAY choose to prefix them as necessary. However, the same
prefix MUST be used consistently for all APIs in the same Registry Service.

Support for any particular API defined by this specification is OPTIONAL,
however it is STRONGLY RECOMMENDED that server-side implementations support at
least the "read" (HTTP `GET`) operations. Implementations MAY choose to
incorporate authentication and/or authorization mechanisms for the APIs.
If an API is not supported by the server then a `405 Method Not Allowed`
HTTP response MUST be generated.

The remainder of this specification focuses on the successful interaction
patterns of the APIs. For example, most examples will show an HTTP "200 OK"
as the response. Each implementation MAY choose to return a more appropriate
response based on the specific situation. For example, in the case of an
authentication error the server could return a `4xx` type of error instead.

The following sections define the APIs in more detail.

#### Registry Model

The Registry model defines the Groups and Resources supported by the Registry
Service. This information will usually be used by tooling that does not have
advance knowledge of the type of data stored within the Registry.

The Registry model can be retrieved two ways:

1. as a stand-alone entity. This is useful when management of the Registry's
   model is needed independent of the entities within the Registry.
   See [Retrieving the Registry Model](#retrieving-the-registry-model) for
   more information
2. as part of the Registry entities. This is useful when it is desirable to
   view the entire Registry as a single document - such as an "export" type
   of scenario. See the [Retrieving the Registry](#retrieving-the-registry)
   section (the `model` query parameter) for more information on this option

Regardless of how the model is retrieved, the overall format is as follows:

``` text
{
  "schema": "URI-Reference", ?         # Schema doc for the entire Registry
  "groups": [
    { "singular": "STRING",            # eg. "endpoint"
      "plural": "STRING",              # eg. "endpoints"
      "schema": "URI-Reference", ?     # Schema doc for the group

      "resources": [
        { "singular": "STRING",        # eg. "definition"
          "plural": "STRING",          # eg. "definitions"
          "versions": UINT, ?          # Num Versions(>=0). Def=1, 0=unlimited
          "versionId": BOOL, ?         # Supports client specific Version IDs
          "latest": BOOL ?             # Supports client "latest" selection
        } *
      ] ?
    } *
  ] ?
}
```

The following describes the attributes of Registry model:

- `schema`
  - A URI-reference to a schema that describes the entire Registry, include
    the model
  - Type: URI-Reference
  - OPTIONAL
- `groups`
  - The set of Groups supported by the Registry
  - Type: Array
  - REQUIRED if there are any Groups defined for the Registry
- `groups.singular`
  - The singular name of a Group. eg. `endpoint`
  - Type: String
  - REQUIRED
  - MUST be unique across all Groups in the Registry
- `groups.plural`
  - The plural name of a Group. eg. `endpoints`
  - Type: String
  - REQUIRED
  - MUST be unique across all Groups in the Registry
- `groups.schema`
  - A URI-Reference to a schema document for the Group
  - Type: URI-Reference
  - OPTIONAL
- `groups.resources`
  - The set of Resource entities defined for the Group
  - Type: Array
  - REQUIRED if there are any Resources defined for the Group
- `groups.resources.singular`
  - The singular name of the Resource. eg. `definition`
  - Type: String
  - REQUIRED
- `groups.resources.plural`
  - The plural name of the Resource. eg. `definitions`
  - Type: String
  - REQUIRED
- `groups.resources.versions`
  - Number of Versions per Resource that will be stored in the Registry
  - Type: Unsigned Integer
  - OPTIONAL
  - The default value is one (`1`), meaning only the latest Version will
    be stored
  - A value of zero (`0`) indicates there is no stated limit, and
    implementations MAY prune non-latest Versions at any time. Implementations
    MUST prune Versions by deleting the oldest Versions first
- `groups.resources.versionId`
  - Indicated whether support for client-side select of a Version's `id` is
    supported
  - Type: Boolean (`true` or `false`, case sensitive)
  - OPTIONAL
  - The default value is `true`
  - A value of `true` indicates the client MAY specify the `id` of a Version
    during its creation process
- `groups.resources.latest`
  - Indicated whether support for client-side selection of the "latest"
    Version of a Resource is supported
  - Type: Boolean (`true` or `false`, case sensitive)
  - OPTIONAL
  - The default value is `true`
  - A value of `true` indicates the client MAY select the latest Version of
    a Resource via one of the methods described in this specification

##### Retrieving the Registry Model

To retrieve the Registry Model as a stand-alone entity, an HTTP `GET` MAY be
used.

The request MUST be of the form:

``` text
GET /model
```

A successful response MUST be of the form:

```  text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...

{
  "schema": "URI-Reference", ?
  "groups": [
    { "singular": "STRING",
      "plural": "STRING",
      "schema": "URI-Reference", ?

      "resources": [
        { "singular": "STRING",
          "plural": "STRING",
          "versions": UINT ?
        } *
      ] ?
    } *
  ] ?
}
```

**Examples:**

Request:

``` text
GET /model
```

Response:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...

{
  "model": {
    "groups": [
      { "singular": "endpoint",
        "plural": "endpoints",

        "resources": [
          { "singular": "definition",
            "plural": "definitions",
            "versions": 1
          }
        ]
      }
    ]
  }
}
```

##### Updating the Registry Model

To update the Registry Model, an HTTP `PUT` MAY be used.

The request MUST be of the form:

``` text
PUT /model
Content-Type: application/json; charset=utf-8
Content-Length: ...

{
  "schema": "URI-Reference", ?
  "groups": [
    { "singular": "STRING",
      "plural": "STRING",
      "schema": "URI-Reference", ?

      "resources": [
        { "singular": "STRING",
          "plural": "STRING",
          "versions": UINT ?
        } *
      ] ?
    } *
  ] ?
}
```

Where:
- the HTTP body MUST contain the full representation of the Registry model
- attributes not present in the request, or present with a value of `null`,
  MUST be interpreted as a request to delete the attribute

The deletion of a Group or Resource from the model SHOULD change the underlying
datastore of the implementation to match.

A successful response MUST include a full representation of the Registry model
and be of the form:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...

{
  "schema": "URI-Reference", ?
  "groups": [
    { "singular": "STRING",
      "plural": "STRING",
      "schema": "URI-Reference", ?

      "resources": [
        { "singular": "STRING",
          "plural": "STRING",
          "versions": UINT ?
        } *
      ] ?
    } *
  ] ?
}
```

**Examples:**

Request:

``` text
PUT /model
Content-Type: application/json; charset=utf-8
Content-Length: ...

{
  "model": {
    "groups": [
      { "singular": "endpoint",
        "plural": "endpoints",

        "resources": [
          { "singular": "definition",
            "plural": "definitions",
            "versions": 1
          }
        ]
      },
      { "singular": "schemaGroup",
        "plural": "schemaGroups",

        "resources": [
          { "singular": "schema",
            "plural": "schemas"
          }
        ]
      }
    ]
  }
}
```

Response:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...

{
  "model": {
    "groups": [
      { "singular": "endpoint",
        "plural": "endpoints",

        "resources": [
          { "singular": "definition",
            "plural": "definitions",
            "versions": 1
          }
        ]
      },
      { "singular": "schemaGroup",
        "plural": "schemaGroups",

        "resources": [
          { "singular": "schema",
            "plural": "schemas"
          }
        ]
      }
    ]
  }
}
```

#### Registry Collections

Registry collections (`GROUPs`, `RESOURCEs` and `versions`) that are defined
by the [Registry Model](#registry-model) MUST be serialized according to the
rules defined below.

The serialization of a collection is done as 3 attributes and adheres to this
form:

``` text
"COLLECTIONsUrl": "URL, ?
"COLLECTIONsCount": UINT, ?
"COLLECTIONs": {
  # map of entities in the collection, key is the "id" of each entity
} ?
```

Where:
- the term `COLLECTIONs` MUST be the plural name of the collection
  (e.g. endpoints, versions)
- the `COLLECTIONsUrl` attribute MUST be an absolute URL that can be used to
  retrieve the `COLLECTIONs` map via an HTTP `GET` (including any necessary
  [filter](#filtering))
- the `COLLECTIONsCount` attribute MUST contain the number of entities in the
  `COLLECTIONs` map (including any necessary [filter](#filtering))
- the `COLLECTIONs` attribute is a map and MUST contain the entities of the
  collection (including any necessary [filter](#filtering)), and MUST use
  each entity's `id` as the key for that map entry
- the specifics of whether each attribute is REQUIRED or OPTIONAL will be
  based whether dcoument or API view is being used - see below

When the `COLLECTIONs` attribute is expected to be present in the
serialization, but the number of entities is zero, it MUST still be included
as an empty map.

The set of entities that are part of the `COLLECTIONs` attribute is a
point-in-time view of the Registry. There is no guarantee that a `GET` to the
`COLLECTIONsUrl` will return the exact same collection since the contents of
the Registry might have changed.

##### Document view

In document view:
- `COLLECTIONsUrl` and `COLLECTIONsCount` are OPTIONAL
- `COLLECTIONs` is REQUIRED

##### API view

In API view:
- `COLLECTIONsUrl` and `COLLECTIONsCount` are REQUIRED
- `COLLECTIONs` is OPTIONAL and MUST only be included if the Registry request
  included the [`inline`](#inlining) flag indicating that this collection's
  values are to be returned as part of the result
- all 3 attributes MUST be read-only and MUST NOT be updated directly via
  an API call. Rather, to modify it the collection specific APIs MUST be used
  (eg. an HTTP `POST` to the collection's URL to add a new entity). The
  presence of the collection attributes in a write operation MUST be silently
  ignored by the server

#### Registry Entity

The Registry entity represents the root of a Registry and is the main
entry-point for traversal.

The serialization of the Registry entity adheres to this form:

``` text
{
  "specVersion": "STRING",
  "id": "STRING",
  "name": "STRING", ?
  "self": "URL",
  "description": "STRING", ?
  "documentation": "URL", ?
  "tags": { "STRING": "STRING" * }, ?

  "model": { Registry model } ?       # only if  "?model" is present

  # Repeat for each Group type
  "GROUPsUrl": "URL",                 # eg. "endpointsUrl"
  "GROUPsCount": INT                  # eg. "endpointsCount"
  "GROUPs": { GROUPs collection } ?   # only if inlined
}
```

The Registry entity includes the following common attributes:
- [`id`](#id) - REQUIRED
- [`name`](#name) - OPTIONAL
- [`self`](#self) - REQUIRED in responses, OPTIONAL in requests and in
  document view
- [`description`](#description) - OPTIONAL
- [`documentation`](#documentation) - OPTIONAL
- [`tags`](#tags) - OPTIONAL

and the following Registry entity specific attributes:

**`specVersion`**
- Type: String
- Description: The version of this specification that the serialization
  adheres to
- Constraints:
  - REQUIRED in responses, OPTIONAL in requests
  - REQUIRED in document view
  - MUST be a read-only attribute in API view
  - MUST be non-empty
  - an implementation of this specification MUST only support one version
    of this specification per server endpoint
- Examples:
  - `1.0`

**`model`**
- Type: Registry Model
- Description: A description of the Groups and Resources supported by this
  Registry. See [Registry Model](#registry-model)
- Constraints:
  - OPTIONAL
  - MUST NOT be included in responses unless requested
  - MUST be included in responses if requested
  - SHOULD be included in document view when the model is not known in advance
  - MUST be a read-only attribute in API view, use the `/model` API to update

**`GROUPs` collections**
- Type: Set of [Registry Collections](#registry-collections)
- Description: A list of Registry collections that contain the set of Groups
  supported by the Registry
- Constraints:
  - REQUIRED in responses, SHOULD NOT be included in requests
  - REQUIRED in document view
  - MUST be a read-only attribute in API view
  - if present, MUST include all nested Group Collection types

##### Retrieving the Registry

To retrieve the Registry, its metadata attributes and Groups, an HTTP `GET`
MAY be used.

The request MUST be of the form:

``` text
GET /[?model&inline=...&filter=...]
```

The following query parameters MUST be supported by servers:
- `model`<br>
  The presence of this query parameter indicates that the request is asking
  for the Registry model to be included in the response. See
  [Registry Model](#registry-model) for more information
- `inline` - See [inlining](#inlining) for more information
- `filter` - See [filtering](#filtering) for more information

A successful response MUST be of the form:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...

{
  "specVersion": "STRING",
  "id": "STRING",
  "name": "STRING", ?
  "self": "URL",
  "description": "STRING", ?
  "documentation": "URL", ?
  "tags": { "STRING": "STRING" * }, ?

  "model": { Registry model } ?       # only if  "?model" is present

  # Repeat for each Group type
  "GROUPsUrl": "URL",                 # eg. "endpointsUrl"
  "GROUPsCount": INT                  # eg. "endpointsCount"
  "GROUPs": { GROUPs collection } ?   # only if inlined
}
```

**Examples:**

Request:

``` text
GET /
```

Response:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...

{
  "specVersion": "0.5",
  "id": "987654321",
  "self": "https://example.com/",

  "endpointsUrl": "https://example.com/endpoints",
  "endpointsCount": 42,

  "schemaGroupsUrl": "https://example.com/schemaGroups",
  "schemaGroupsCount": 1
}
```

Another example asking for the model to be included and for one of the
top-level Group collections to be inlined:

Request:

``` text
GET /?model&inline=schemaGroups
```

Response:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...

{
  "specVersion": "0.5",
  "id": "987654321",
  "self": "https://example.com/",

  "model": {
    "groups": [
      { "singular": "endpoint",
        "plural": "endpoints",

        "resources": [
          { "singular": "definition",
            "plural": "definitions",
            "versions": 1
          }
        ]
      },
      { "singular": "schemaGroup",
        "plural": "schemaGroups",

        "resources": [
          { "singular": "schema",
            "plural": "schemas",
            "versions": 1
          }
        ]
      },
    ]
  },

  "endpointsUrl": "https://example.com/endpoints",
  "endpointsCount": 42,

  "schemaGroupsUrl": "https://example.com/schemaGroups",
  "schemaGroupsCount": 1,
  "schemaGroups": {
    "mySchemas": {
      "id": "mySchemas",
      # remainder of Group is excluded for brevity
    }
  }
}
```

##### Updating the Registry

To update a Registry's metadata attributes, an HTTP `PUT` MAY be used.

The request MUST be of the form:

``` text
PUT /
Content-Type: application/json; charset=utf-8
Content-Length: ...

{
  "id": "STRING", ?
  "name": "STRING", ?
  "description": "STRING", ?
  "documentation": "URL" ?
  "tags": { "STRING": "STRING" * }, ?
}
```

Where:
- the HTTP body MUST contain the full representation of the Registry's
  mutable metadata
- attributes not present in the request, or present with a value of `null`,
  MUST be interpreted as a request to delete the attribute
- a request to update, or delete, a nested Group collection or a read-only
  attribute MUST be silently ignored
- a request to update a mutable attribute with an invalid value MUST
  generate an error (this includes deleting a mandatory mutable attribute)
- complex attributes that have nested values (eg. `tags`) MUST be specified
  in their entirety

A successful response MUST include the same content that an HTTP `GET`
on the Registry would return, and be of the form:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...

{
  "specVersion": "STRING",
  "id": "STRING",
  "name": "STRING", ?
  "self": "URL",
  "description": "STRING", ?
  "documentation": "URL", ?
  "tags": { "STRING": "STRING" * }, ?

  # Repeat for each Group type
  "GROUPsUrl": "URL",
  "GROUPsCount": INT
}
```

**Examples:**

Request:

``` text
PUT /
Content-Type: application/json; charset=utf-8
Content-Length: ...

{
  "id": "987654321",
  "name": "My Registry",
  "description": "An even cooler registry!"
}
```

Response:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...

{
  "specVersion": "0.5",
  "id": "987654321",
  "name": "My Registry",
  "self": "https://example.com/",
  "description": "An even cooler registry!",

  "endpointsUrl": "https://example.com/endpoints",
  "endpointsCount": 42,

  "schemaGroupsUrl": "https://example.com/schemaGroups",
  "schemaGroupsCount": 1
}
```

#### Groups

Groups represent top-level entities in a Registry that act as a collection
mechanism for related Resources. Each Group type MAY have any number of
Resource types within it. This specification does not define how the Resources
within a Group type are related other.

The serialization of a Group entity adheres to this form:

``` text
{
  "id": "STRING",
  "name": "STRING", ?
  "epoch": UINT,
  "self": "URL",
  "description": "STRING", ?
  "documentation": "URL", ?
  "tags": { "STRING": "STRING" * }, ?
  "format": "STRING", ?
  "createdBy": "STRING", ?
  "createdOn": "TIME", ?
  "modifiedBy": "STRING", ?
  "modifiedOn": "TIME", ?

  # Repeat for each Resource type in the Group
  "RESOURCEsUrl": "URL",                    # eg. "definitionsUrl"
  "RESOURCEsCount": INT,                    # eg. "definitionsCount"
  "RESOURCEs": { RESOURCEs collection } ?   # if inlined
}
```

Groups include the following common attributes:
- [`id`](#id) - REQUIRED, except on create request
- [`name`](#name) - OPTIONAL
- [`epoch`](#epoch) - REQUIRED in responses, otherwise OPTIONAL
- [`self`](#self) - REQUIRED in responses, OPTIONAL in requests and in
  document view
- [`description`](#description) - OPTIONAL
- [`documentation`](#documentation) - OPTIONAL
- [`tags`](#tags) - OPTIONAL
- [`format`](#format) - OPTIONAL
- [`createdBy`](#createdby) - OPTIONAL
- [`createdOn`](#createdon) - OPTIONAL
- [`modifiedBy`](#modifiedby) - OPTIONAL
- [`modifiedOn`](#modifiedon) - OPTIONAL

and the following Group specific attributes:

**`RESOURCEs` collections**
- Type: Set of [Registry Collections](#registry-collections)
- Description: A list of Registry collections that contain the set of
  Resources supported by the Group
- Constraints:
  - REQUIRED in responses, SHOULD NOT be present in requests
  - REQUIRED in document view
  - if present, MUST include all nested Resource Collection types of the
    owning Group

##### Retrieving a Group Collection

To retrieve a Group collection, an HTTP `GET` MAY be used.

The request MUST be of the form:

``` text
GET /GROUPs[?inline=...&filter=...]
```

The following query parameters MUST be supported by servers:
- `inline` - See [inlining](#inlining) for more information
- `filter` - See [filtering](#filtering) for more information

A successful response MUST be of the form:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...
Link: <URL>;rel=next;count=INT ?

{
  "ID": {                                     # The Group id
    "id": "STRING",                           # A Group
    "name": "STRING", ?
    "epoch": UINT,
    "self": "URL",
    "description": "STRING", ?
    "documentation": "URL", ?
    "tags": { "STRING": "STRING" * }, ?
    "format": "STRING", ?
    "createdBy": "STRING", ?
    "createdOn": "TIME", ?
    "modifiedBy": "STRING", ?
    "modifiedOn": "TIME", ?

    # Repeat for each Resource type in the Group
    "RESOURCEsUrl": "URL",                    # eg. "definitionsUrl"
    "RESOURCEsCount": INT,                    # eg. "definitionsCount"
    "RESOURCEs": { RESOURCEs collection } ?   # if inlined
  } *
}
```

Where:
- the key (`ID`) of each item in the map MUST be the `id` of the
  respective Group

Also see [Groups](#groups).

**Examples:**

Request:

``` text
GET /endpoints
```

Response:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...
Link: <https://example.com/endpoints&page=2>;rel=next;count=100

{
  "123": {
    "id": "123",
    "name": "A cool endpoint",
    "epoch": 1,
    "self": "https://example.com/endpoints/123",

    "definitionsUrl": "https://example.com/endpoints/123/definitions",
    "definitionsCount": 5
  },
  "124": {
    "id": "124",
    "name": "Redis Queue",
    "epoch": 3,
    "self": "https://example.com/endpoints/124",

    "definitionsUrl": "https://example.com/endpoints/124/definitions",
    "definitionsCount": 1
  }
}
```

##### Creating a Group

To create a new Group, an HTTP `POST` MAY be used.

The request MUST be of the form:

``` text
POST /GROUPs
Content-Type: application/json; charset=utf-8
Content-Length: ...

{
  "id": "STRING", ?
  "name": "STRING", ?
  "epoch": UINT, ?
  "description": "STRING", ?
  "documentation": "URL", ?
  "tags": { "STRING": "STRING" * }, ?
  "format": "STRING" ?
}
```

Where:
- `id` is OPTIONAL and if absent the server MUST assign it a new unique value
- whether `id` is provided or generated by the server, it MUST be unique
  across all Groups of this type
- `epoch` is OPTIONAL and if present MUST be silently ignored

A successful response MUST be of the form:

``` text
HTTP/1.1 201 Created
Content-Type: application/json; charset=utf-8
Content-Length: ...
Location: URL

{
  "id": "STRING",
  "name": "STRING", ?
  "epoch": UINT,
  "self": "URL",
  "description": "STRING", ?
  "documentation": "URL", ?
  "tags": { "STRING": "STRING" * }, ?
  "format": "STRING", ?
  "createdBy": "STRING", ?
  "createdOn": "TIME", ?
  "modifiedBy": "STRING", ?
  "modifiedOn": "TIME", ?

  # Repeat for each Resource type in the Group
  "RESOURCEsUrl": "URL",                    # eg. "definitionsUrl"
  "RESOURCEsCount": INT                     # eg. "definitionsCount"
}
```

Where:
- The `Location` HTTP header MUST be included and be the same value as `self`
- The HTTP body MUST include the full representation of the new Group, the
  same as an HTTP `GET` on the Group w/o any inlining or filtering

**Examples:**

Request:

``` text
POST /endpoints
Content-Type: application/json; charset=utf-8
Content-Length: ...

{
  "name": "myEndpoint"
}
```

Response:

``` text
HTTP/1.1 201 Created
Content-Type: application/json; charset=utf-8
Content-Length: ...
Location: https://example.com/endpoints/123

{
  "id": "123",
  "name": "myEndpoint",
  "epoch": 1,
  "self": "https://example.com/endpoints/123",

  "definitionsUrl": "https://example.com/endpoints/123/definitions",
  "definitionsCount": 0
}
```

##### Retrieving a Group

To retrieve a Group, an HTTP `GET` MAY be used.

The request MUST be of the form:

``` text
GET /GROUPs/gID[?inline=...&filter=...]
```

The following query parameters MUST be supported by servers:
- `inline` - See [inlining](#inlining) for more information
- `filter` - See [filtering](#filtering) for more information

A successful response MUST be of the form:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...

{
  "id": "STRING",
  "name": "STRING", ?
  "epoch": UINT,
  "self": "URL",
  "description": "STRING", ?
  "documentation": "URL", ?
  "tags": { "STRING": "STRING" * }, ?
  "format": "STRING", ?
  "createdBy": "STRING", ?
  "createdOn": "TIME", ?
  "modifiedBy": "STRING", ?
  "modifiedOn": "TIME", ?

  # Repeat for each Resource type in the Group
  "RESOURCEsUrl": "URL",                     # eg. "definitionsUrl"
  "RESOURCEsCount": INT,                     # eg. "definitionsCount"
  "RESOURCEs": { RESOURCEs collection } ?    # if inlined
}
```

**Examples:**

Request:

``` text
GET /endpoints/123
```

Response:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...

{
  "id": "123",
  "name": "myEndpoint",
  "epoch": 1,
  "self": "https://example.com/endpoints/123",

  "definitionsUrl": "https://example.com/endpoints/123/definitions",
  "definitionsCount": 5
}
```

##### Updating a Group

To update a Group an HTTP `PUT` MAY be used.

The request MUST be of the form:

``` text
PUT /GROUPs/gID

{
  "name": "STRING", ?
  "epoch": UINT, ?
  "description": "STRING", ?
  "documentation": "URL", ?
  "tags": { "STRING": "STRING" * }, ?
  "format": "STRING" ?
}
```

Where:
- the HTTP body MUST contain the full representation of the Group's mutable
  attributes
- attributes not present in the request, or present with a value of `null`,
  MUST be interpreted as a request to delete the attribute
- a request to update, or delete, a nested Resource collection or a read-only
  attribute MUST be silently ignored
- a request to update a mutable attribute with an invalid value MUST
  generate an error (this includes deleting a mandatory mutable attribute)
- complex attributes that have nested values (eg. `tags`) MUST be specified
  in their entirety
- if `epoch` is present then the server MUST reject the request if the Group's
  current `epoch` value is different from the one in the request

Upon successful processing, the Group's `epoch` value MUST be incremented - see
[epoch](#epoch).

A successful response MUST include the same content that an HTTP `GET`
on the Group would return, and be of the form:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...

{
  "id": "STRING",
  "name": "STRING", ?
  "epoch": UINT,
  "self": "URL",
  "description": "STRING", ?
  "documentation": "URL", ?
  "tags": { "STRING": "STRING" * }, ?
  "format": "STRING", ?
  "createdBy": "STRING", ?
  "createdOn": "TIME", ?
  "modifiedBy": "STRING", ?
  "modifiedOn": "TIME", ?

  # Repeat for each Resource type in the Group
  "RESOURCEsUrl": "URL",                     # eg. "definitionsUrl"
  "RESOURCEsCount": INT                      # eg. "definitionsCount"
}
```

**Examples:**

Request:

``` text
PUT /endpoints/123

{
  "name": "myOtherEndpoint",
  "epoch": 1
}
```

Response:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...

{
  "id": "123",
  "name": "myOtherEndpoint",
  "epoch": 2,
  "self": "https://example.com/endpoints/123",

  "definitionsUrl": "https://example.com/endpoints/123/definitions",
  "definitionsCount": 5
}
```

##### Deleting Groups

To delete a single Group, an HTTP `DELETE` MAY be used.

The request MUST be of the form:

``` text
DELETE /GROUPs/gID[?epoch=EPOCH]
```

Where:
- the request body SHOULD be empty

The following query parameters MUST be supported by servers:
- `epoch`<br>
  The presence of this query parameter indicates that the server MUST check
  to ensure that the `EPOCH` value matches the Group's current `epoch` value
  and if it differs then an error MUST be generated

A successful response MUST return either:

``` text
HTTP/1.1 204 No Content
```

with an empty HTTP body, or:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...

{
  "id": "STRING",
  "name": "STRING", ?
  "epoch": UINT,
  "self": "URL",
  "description": "STRING", ?
  "documentation": "URL", ?
  "tags": { "STRING": "STRING" * }, ?
  "format": "STRING", ?
  "createdBy": "STRING", ?
  "createdOn": "TIME", ?
  "modifiedBy": "STRING", ?
  "modifiedOn": "TIME" ?
} ?
```

Where:
- the HTTP body SHOULD contain the latest representation of the Group being
  deleted prior to being deleted
- the response MAY exclude the nested Resource collections if returning them
  is challenging

To delete multiple Groups an HTTP `DELETE` MAY be used.

The request MUST be of the form:

``` text
DELETE /GROUPs

[
  {
    "id": "STRING",
    "epoch": UINT ?     # If present it MUST match current value
  } *
]
```

Where:
- the request body MUST contain the list of Group IDs to be deleted, however
  an empty list or an empty body MUST be interpreted as a request to delete
  all Groups of this Group type
- if an `epoch` value is specified for a Group then the server MUST check
  to ensure that the value matches the Group's current `epoch` value and if it
  differs then an error MUST be generated

Any error MUST result in the entire request being rejected.

A successful response MUST return either:

``` text
HTTP/1.1 204 No Content
```

with an empty HTTP body, or:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...
Link: <URL>;rel=next;count=INT ?

{
  "ID": {
    "id": "STRING",
    "name": "STRING", ?
    "epoch": UINT,
    "self": "URL",
    "description": "STRING", ?
    "documentation": "URL", ?
    "tags": { "STRING": "STRING" * }, ?
    "format": "STRING", ?
    "createdBy": "STRING", ?
    "createdOn": "TIME", ?
    "modifiedBy": "STRING", ?
    "modifiedOn": "TIME" ?
  } *
} ?
```

Where:
- the key (`ID`) of each item in the map MUST be the `id` of the
  respective Group
- the HTTP body SHOULD contain the latest representation of the Groups being
  deleted prior to being deleted
- the response MAY exclude the nested Resource collections if returning them
  is challenging

#### Resources

Resources represent the main entity that the Registry is managing. Each
Resource is associated with a Group to aid in their discovery and to show
a relationship with related Resources in that same Group. Those Resources
appear within the Group's `RESOURCEs` collection.

Resources, like all entities in the Registry can be modified, but Resources
can also have a version history associated with them, allowing for users to
retrieve previous Versions of the Resource. In this respect, Resources have
a 2-layered definition. The first layer is the Registry Resource entity itself,
while the second layer is the `versions` collection - the version history of
the Resource. The Resource entity can be thought of as an alias for the
"latest" Version of the Resource, and as such, many of the attributes
shown when retrieving the Resource will come from that Version. However,
there are a few exceptions:
- `id` MUST be for the Resource itself and not the `id` from the "latest"
  Version. The `id` of each Version MUST be unique within the scope of the
  Resource, but to ensure the Resource itself has a consistent `id` value
  it is distinct from any Version's `id`. There MUST be a `latestId` attribute
  in the serialization of a Resource that can be used to determine which
  Version is the latest Version (meaning, which Version this Resource is an
  alias for)

  Additionally, Resource `id` values are often human readable (eg. `mySchema`),
  while Version `id` values are meant to be versions string values
  (e.g. `1.0`).
- `self` MUST be an absolute URL to the Resource, and not to a specific
  Version in the `versions` collection

Additionally, when serialized in an HTTP response the Resource MAY include an
`Content-Location` HTTP header, and if present it MUST contain a URL to the
latest Version in `versions` collection of the Resource.

Unlike Groups, Resources are typically defined by domain-specific data
and as such the Registry defined attributes are not present in the Resources
themselves. This means the Registry metadata needs to be managed separately
from the contents of the Resource, as a result, there are two ways to
serialize the Resource in HTTP:
- the contents of the Resource appears in the HTTP body, and each Registry
  attribute (along with its value) appears as an HTTP header with its name
  prefixed with `xRegistry-`
- the Registry attributes, and the Resource contents, are serialized as a
  single JSON object that appears in the HTTP body

When serialized as a JSON object, a Resource adheres to this form:

``` text
{
  "id": "STRING",
  "name": "STRING", ?
  "epoch": UINT,
  "self": "URL",
  "latestId": "STRING",
  "latestUrl": "URL",
  "description": "STRING", ?
  "documentation": "URL", ?
  "tags": { "STRING": "STRING" * }, ?
  "format": "STRING", ?
  "createdBy": "STRING", ?
  "createdOn": "TIME", ?
  "modifiedBy": "STRING", ?
  "modifiedOn": "TIME", ?

  "RESOURCEUrl": "URL", ?                  # if not local
  "RESOURCE": { Resource contents }, ?     # if inlined & JSON
  "RESOURCEBase64": "STRING", ?            # if inlined & ~JSON

  "versionsUrl": "URL",
  "versionsCount": INT,
  "versions": { Versions collection } ?    # if inlined
}
```

Resources include the following common attributes:
- [`id`](#id) - REQUIRED, except on create request where it is OPTIONAL
- [`name`](#name) - OPTIONAL (inherited from the latest version)
- [`epoch`](#epoch) - REQUIRED in responses, otherwise OPTIONAL (inherited
  from the latest version)
- [`self`](#self) - REQUIRED in responses, OPTIONAL in requests and in
  document view
- [`description`](#description) - OPTIONAL (inherited from the latest version)
- [`documentation`](#documentation) - OPTIONAL (inherited from the latest version)
- [`tags`](#tags) - OPTIONAL (inherited from the latest version)
- [`format`](#format) - OPTIONAL (inherited from the latest version)
- [`createdBy`](#createdby) - OPTIONAL (inherited from the latest version)
- [`createdOn`](#createdon) - OPTIONAL (inherited from the latest version)
- [`modifiedBy`](#modifiedby) - OPTIONAL (inherited from the latest version)
- [`modifiedOn`](#modifiedon) - OPTIONAL (inherited from the latest version)

and the following Resource specific attributes:

**`latestId`**
- Type: String
- Description: the `id` of the latest Version of the Resource.
  This specification makes no statement as to the format of this string or
  versioning scheme used by implementations of this specification. However, it
  is assumed that newer Versions of a Resource will have a "higher"
  `id` value than older Versions. Also see [`epoch`](#epoch)
- Constraints:
  - REQUIRED in responses, OPTIONAL on requests (except 'create' see below)
  - REQUIRED in document view
  - MUST be a read-only attribute in API view except in the API to create a
    Resource, where it is REQUIRED
  - MUST be non-empty
  - MUST be unique across all Versions of the Resource
  - MUST be the `id` of the latest Version of the Resource
- Examples:
  - `1`, `2.0`, `v3-rc1`

**`latestUrl`**
- Type: URL
- Description: an absolute URL to the latest Version of the Resource
- Constraints:
  - REQUIRED in responses, OPTIONAL in requests
  - OPTIONAL in document view
  - MUST be a read-only attribute in API view
  - MUST be an absolute URL to the latest Version of the Resource, and MUST
    be the absolute URL to the Resource's `versions` collection  appended with
    `latestId`
- Examples:
  - `https://example.com/endpoints/123/definitions/456/versions/1.0`

**`RESOURCEUrl`**
- Type: URL
- Description: if the content of the Resource are stored outside of the
  current Registry then this attribute MUST contain a URL to the
  location where it can be retrieved
- Constraints:
  - REQUIRED if the Resource contents are stored outside of the current
    Registry
  - the referenced URI MUST support an HTTP(s) `GET` to retrieve the contents

**`RESOURCE`**
- Type: Resource Contents
- Description: This attribute is a serialization of the corresponding
  Resource entity's contents. If the contents can be serialized in the same
  format being used to serialize the Registry, then this attribute MUST be
  used if the request asked for the contents to be inlined in the response.
- Constraints
  - MUST NOT be present when the Resource's Registry metadata are being
    serialized as HTTP headers
  - if the Resource's contents are not empty, then either `RESOURCE` or
    `RESOURCEBase64` MUST be present
  - MUST only be used if the Resource contents can be serialized in the same
    format as the Registry Resource entity
  - MUST NOT be present if `RESOURCEBase64` is also present

**`RESOURCEBase64`**
- Type: String
- Description: This attribute is a base64 serialization of the corresponding
  Resource entity's contents. If the contents can not be serialized in the same
  format being used to serialize the Registry Resource, then this attribute
  MUST be used if the request asked for the content to be inlined in the
  response.
  While the `RESOURCE` attribute SHOULD be used whenever possible,
  implementations MAY choose to use `RESOURCEBase64` if they wish even if the
  Resource could be serialized in the same format.
  Note, this attribute will only be used when requesting the Resource be
  serialized as a Registry Resource (eg. via `?meta`).
- Constraints:
  - MUST NOT be present when the Resource's Registry metadata are being
    serialized as HTTP headers
  - if the Resource's contents are not empty, then either `RESOURCE` or
    `RESOURCEBase64` MUST be present
  - MUST be a base64 encoded string of the Resource's contents
  - MUST NOT be present if `RESOURCE` is also present

**`versions` collection**
- Type: [Registry Collection](#registry-collections)
- Description: A list of Versions of the Resource
- Constraints:
  - REQUIRED in responses, SHOULD NOT be present in requests
  - REQUIRED in document view
  - MUST always have at least one Version (the "latest" Version)

##### Retrieving a Resource Collection

To retrieve all Resources in a Group, an HTTP `GET` MAY be used.

The request MUST be of the form:

``` text
GET /GROUPs/gID/RESOURCEs[?inline=...&filter=...]
```

The following query parameters MUST be supported by servers:
- `inline` - See [inlining](#inlining) for more information
- `filter` - See [filtering](#filtering) for more information

A successful response MUST be of the form:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...
Link: <URL>;rel=next;count=INT ?

{
  "ID": {                                     # The Resource id
    "id": "STRING",
    "name": "STRING", ?
    "epoch": UINT,
    "self": "URL",
    "latestId": "STRING",
    "latestUrl": "URL",
    "description": "STRING", ?
    "documentation": "URL", ?
    "tags": { "STRING": "STRING" * }, ?
    "format": "STRING", ?
    "createdBy": "STRING", ?
    "createdOn": "TIME", ?
    "modifiedBy": "STRING", ?
    "modifiedOn": "TIME", ?

    "RESOURCEUrl": "URL", ?                  # if not local
    "RESOURCE": { Resource contents }, ?     # if inlined & JSON
    "RESOURCEBase64": "STRING", ?            # if inlined & ~JSON

    "versionsUrl": "URL",
    "versionsCount": INT,
    "versions": { Versions collection } ?    # if inlined
  } *
}
```

Where:
- the key (`ID`) of each item in the map MUST be the `id` of the
  respective Resource

**Examples:**

Request:

``` text
GET /endpoints/123/definitions
```

Response:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...
Link: <https://example.com/endpoints/123/definitions&page=2>;rel=next;count=100

{
  "456": {
    "id": "456",
    "name": "Blob Created",
    "epoch": 1,
    "self": "https://example.com/endpoints/123/definitions/456",
    "latestId": "1.0",
    "latestUrl": "https://example.com/endpoints/123/definitions/456/versions/1.0",
    "format": "CloudEvents/1.0",

    "versionsUrl": "https://example.com/endpoints/123/definitions/456/versions",
    "versionsCount": 1
  }
}
```

##### Creating Resources

To create a new Resource, an HTTP `POST` MAY be used.

The request MUST be of the form:

``` text
POST /GROUPs/gID/RESOURCEs
Content-Type: ...
Content-Length: ...
xRegistry-id: STRING ?
xRegistry-name: STRING ?
xRegistry-epoch: STRING ?
xRegistry-latestId: STRING ?
xRegistry-description: STRING ?
xRegistry-documentation: STRING ?
xRegistry-tags: STRING (JSON map) ?
xRegistry-format: STRING ?
xRegistry-RESOURCEUrl: URL ?

...Resource contents... ?
```

Where:
- `id` is OPTIONAL and if absent the server MUST assign it a new unique value
- whether `id` is provided or generated by the server, it MUST be unique
  across all Resources of this type for this Group
- `epoch` is OPTIONAL and if present MUST be silently ignored
- `latestId` is OPTIONAL and if present it MUST be used as the resulting
  Version `id` value. If absent the server MUST assign it a new unique value.
  Note, normally `latestId` is read-only, but in this case it is not
- if `RESOURCEUrl` is present the HTTP body MUST be empty
- the HTTP body MUST contain the contents of the new Resource if the
  `RESOURCEUrl` HTTP header is absent. Note, the body MAY be empty
  even if the HTTP header is not present, indicating that the Resource is
  empty
- a request that is missing a mandatory attribute MUST generate an error

This operation MUST result in one Version of the new Resource being created.

A successful response MUST include the same content than an HTTP `GET` on the
Resource would return, and be of the form:

``` text
HTTP/1.1 201 Created
Content-Type: ...
Content-Length: ...
xRegistry-id: STRING
xRegistry-name: STRING ?
xRegistry-epoch: UINT
xRegistry-self: URL
xRegistry-latestId: STRING
xRegistry-latestUrl: URL
xRegistry-description: STRING ?
xRegistry-documentation: STRING ?
xRegistry-tags: STRING (JSON map) ?
xRegistry-format: STRING ?
xRegistry-createdBy: STRING ?
xRegistry-createdOn: TIME ?
xRegistry-modifiedBy: STRING ?
xRegistry-modifiedOn: TIME ?
xRegistry-versionsUrl: URL
xRegistry-versionsCount: INT
xRegistry-RESOURCEUrl: URL ?
Location: URL
Content-Location: URL ?

...Resource contents... ?
```

Where:
- `Location` MUST be a URL to the Resource - same as `self`
- if `Content-Location` is present then it MUST be a URL to the Version of the
  Resource in the `versions` collection - same as `latestUrl`
- if `RESOURCEUrl` is present then the HTTP body MUST be empty
- if the HTTP body is not empty then `RESOURCEUrl` MUST NOT be present

**Examples:**

Request:

``` text
POST /endpoints/123/definitions
Content-Type: application/json; charset=utf-8
Content-Length: ...
xRegistry-name: Blob Created
xRegistry-format: CloudEvents/1.0
xRegistry-latestId: 1.0

{
  # definition of a "Blob Created" event excluded for brevity
}
```

Response:

``` text
HTTP/1.1 201 Created
Content-Type: application/json; charset=utf-8
Content-Length: ...
xRegistry-id: 456
xRegistry-name: Blob Created
xRegistry-epoch: 1
xRegistry-self: https://example.com/endpoints/123/definitions/456
xRegistry-latestId: 1.0
xRegistry-latestUrl: https://example.com/endpoints/123/definitions/456/versions/1.0
xRegistry-format: CloudEvents/1.0
xRegistry-versionsUrl: https://example.com/endpoints/123/definitions/456/versions
xRegistry-versionsCount: 1
Location: https://example.com/endpoints/123/definitions/456
Content-Location: https://example.com/endpoints/123/definitions/456/versions/1.0

{
  # definition of a "Blob Created" event excluded for brevity
}
```

##### Creating a Resource as Metadata

To create a new Resource as metadata (Resource attributes), an HTTP `POST` with
the `?meta` query parameter MAY be used.

The request MUST be of the form:

``` text
POST /GROUPs/gID/RESOURCEs?meta
Content-Type: application/json; charset=utf-8
Content-Length: ...

{
  "id": "STRING", ?
  "name": "STRING", ?
  "epoch": UINT, ?
  "latestId": "STRING", ?
  "description": "STRING", ?
  "documentation": "URL", ?
  "tags": { "STRING": "STRING" * }, ?
  "format": "STRING", ?

  "RESOURCEUrl": "URL", ?                  # if not local
  "RESOURCE": { Resource contents }, ?     # if inlined & JSON
  "RESOURCEBase64": "STRING" ?             # if inlined & ~JSON
}
```

Where:
- `id` is OPTIONAL and if absent the server MUST assign it a new unique value
- whether `id` is provided or generated by the server, it MUST be unique
  across all Resources of this type for this Group
- `epoch` is OPTIONAL and if present MUST be silently ignored
- `latestId` is OPTIONAL and if present it MUST be used as the resulting
  Version `id` value. If absent the server MUST assign it a new unique value.
  Note, normally `latestId` is read-only, but in this case it is not
- at most, only one of `RESOURCEUrl`, `RESOURCE` or `RESOURCEBase64` MAY
  be present
- a request that is missing a mandatory attribute MUST generate an error.

This operation MUST result in one Version of the new Resource being created.

A successful response MUST include the same content than an HTTP `GET` on the
Resource would return, and be of the form:

``` text
HTTP/1.1 201 Created
Content-Type: ...
Content-Length: ...
Location: URL
Content-Location: URL ?

{
  "id": "STRING",
  "name": "STRING", ?
  "epoch": UINT,
  "self": "URL",
  "latestId": "STRING",
  "latestUrl": "URL",
  "description": "STRING", ?
  "documentation": "URL", ?
  "tags": { "STRING": "STRING" * }, ?
  "format": "STRING", ?
  "createdBy": "STRING", ?
  "createdOn": "TIME", ?
  "modifiedBy": "STRING", ?
  "modifiedOn": "TIME", ?

  "RESOURCEUrl": "URL", ?                  # if not local

  "versionsUrl": "URL",
  "versionsCount": INT,
}
```

Where:
- `self` is a URL to the Resource (with the `?meta`), not to the latest
  Version of the Resource
- `Location` MUST be a URL to the Resource - same as `self`
- if `Content-Location` is present then it MUST be a URL to the Version of the
  Resource in the `versions` collection - same as `latestUrl`

Note that the response MUST NOT include the `RESOURCE`, `RESOURCEBase64`
or `versions` attributes.

**Examples:**

Request:

``` text
POST /endpoints/123/definitions?meta
Content-Type: application/json; charset=utf-8
Content-Length: ...

{
  "name": "Blob Created",
  "latestId": "1.0",
  "format": "CloudEvents/1.0",
  "definition": {
    # definition of a "Blob Created" event excluded for brevity
  }
}
```

Response:

``` text
HTTP/1.1 201 Created
Content-Type: application/json; charset=utf-8
Content-Length: ...
Location: https://example.com/endpoints/123/definitions/456
Content-Location: https://example.com/endpoints/123/definitions/456/versions/1.0

{
  "id": "456",
  "name": "Blob Created",
  "epoch": 1,
  "self": "https://example.com/endpoints/123/definitions/456"
  "latestId": "1.0",
  "latestUrl": "https://example.com/endpoints/123/definitions/456/versions/1.0",
  "format": "CloudEvents/1.0",

  "versionsUrl": "https://example.com/endpoints/123/definitions/456/versions",
  "versionsCount": 1
}
```

##### Retrieving a Resource

To retrieve a Resource, an HTTP `GET` MAY be used.

The request MUST be of the form:

``` text
GET /GROUPs/gID/RESOURCEs/rID
```

This MUST retrieve the latest Version of a Resource. Note that `rID` will be
for the Resource and not the `id` of the underlying Version (see
[Resources](#resources).

A successful response MUST either return the Resource if stored within the
Registry, or an HTTP redirect to the `RESOURCEUrl` value stored external
to the Registry, if one is set.

In the case of returning the Resource, the response MUST be of the form:

``` text
HTTP/1.1 200 OK
Content-Type: ...
Content-Length: ...
xRegistry-id: STRING
xRegistry-name: STRING ?
xRegistry-epoch: UINT
xRegistry-self: URL
xRegistry-latestId: STRING
xRegistry-latestUrl: URL
xRegistry-description: STRING ?
xRegistry-documentation: STRING ?
xRegistry-tags: STRING (JSON map) ?
xRegistry-format: STRING ?
xRegistry-createdBy: STRING ?
xRegistry-createdOn: TIME ?
xRegistry-modifiedBy: STRING ?
xRegistry-modifiedOn: TIME ?
xRegistry-versionsUrl: URL
xRegistry-versionsCount: INT
Content-Location: URL ?

...Resource contents...
```

Where:
- `id` MUST be the ID of the Resource, not of the latest Version of the
  Resource
- `self` MUST be a URL to the Resource, not to the latest Version of the
  Resource
- if `Content-Location` is present then it MUST be a URL to the Version of the
  Resource in the `versions` collection - same as `latestUrl`

In the case of a redirect, the response MUST be of the form:

``` text
HTTP/1.1 307 Temporary Redirect
xRegistry-id: STRING
xRegistry-name: STRING ?
xRegistry-epoch: UINT
xRegistry-self: URL
xRegistry-latestId: STRING
xRegistry-latestUrl: URL
xRegistry-description: STRING ?
xRegistry-documentation: STRING ?
xRegistry-tags: STRING (JSON map) ?
xRegistry-format: STRING ?
xRegistry-createdBy: STRING ?
xRegistry-createdOn: TIME ?
xRegistry-modifiedBy: STRING ?
xRegistry-modifiedOn: TIME ?
xRegistry-versionsUrl: URL
xRegistry-versionsCount: INT
xRegistry-RESOURCEUrl: URL
Location: URL
Content-Location: URL ?
```

Where:
- `id` MUST be the Resource's `id` and not the `id` of the latest Version
- `self` MUST be a URL to the Resource, not to the latest Version of the
  Resource
- if `Content-Location` is present then it MUST be a URL to the Version of the
  Resource in the `versions` collection - same as `latestUrl`
- `Location` and `RESOURCEUrl` MUST have the same value

**Examples:**

Request:

``` text
GET /endpoints/123/definitions/456
```

Response:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...
xRegistry-id: 456
xRegistry-name: Blob Created
xRegistry-epoch: 1
xRegistry-self: https://example.com/endpoints/123/definitions/456
xRegistry-latestId: 1.0
xRegistry-latestUrl: https://example.com/endpoints/123/definitions/456/versions/1.0
xRegistry-format: CloudEvents/1.0
xRegistry-versionsUrl: https://example.com/endpoints/123/definitions/456/versions
xRegistry-versionsCount: 1
Content-Location: https://example.com/endpoints/123/definitions/456/versions/1.0

{
  # definition of a "Blob Created" event excluded for brevity
}
```

##### Retrieving a Resource's Metadata

To retrieve a Resource's metadata (Resource attributes) as a JSON object, an
HTTP `GET` with the `?meta` query parameter MAY be used.

The request MUST be of the form:

``` text
GET /GROUPs/gID/RESOURCEs/rID?meta[&inline=...&filter=...]
```

A successful response MUST be of the form:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...
Content-Location: URL ?

{
  "id": "STRING",
  "name": "STRING", ?
  "epoch": UINT,
  "self": "URL",
  "latestId": "STRING",
  "latestUrl": "URL",
  "description": "STRING", ?
  "documentation": "URL", ?
  "tags": { "STRING": "STRING" * }, ?
  "format": "STRING", ?
  "createdBy": "STRING", ?
  "createdOn": "TIME", ?
  "modifiedBy": "STRING", ?
  "modifiedOn": "TIME", ?

  "RESOURCEUrl": "URL", ?                  # if not local
  "RESOURCE": { Resource contents }, ?     # if inlined & JSON
  "RESOURCEBase64": "STRING", ?            # if inlined & ~JSON

  "versionsUrl": "URL",
  "versionsCount": INT,
  "versions": { Versions collection } ?    # if inlined
}
```

Where:
- `id` MUST be the Resource's `id` and not the `id` of the latest Version
- `self` is a URL to the Resource (with the `?meta`), not to the latest
  Version of the Resource
- `RESOURCE`, or `RESOURCEBase64`, depending on the type of the Resource's
  content, MUST only be included if requested via the `inline` query parameter
  and `RESOURCEUrl` is not set
- if `Content-Location` is present then it MUST be a URL to the Version of the
  Resource in the `versions` collection - same as `latestUrl`

The following query parameters MUST be supported by servers:
- `inline` - See [inlining](#inlining) for more information
- `filter` - See [filtering](#filtering) for more information

**Examples:**

Request:

``` text
GET /endpoints/123/definitions/456?meta
```

Response:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...
Content-Location: https://example.com/endpoints/123/definitions/456/versions/1.0

{
  "id": "456",
  "name": "Blob Created",
  "epoch": 1,
  "self": "https://example.com/endpoints/123/definitions/456i?meta,
  "latestId": "1.0",
  "latestUrl": "https://example.com/endpoints/123/definitions/456/versions/1.0",
  "format": "CloudEvents/1.0",

  "versionsUrl": "https://example.com/endpoints/123/definitions/456/versions",
  "versionsCount": 1
}
```

##### Updating a Resource

To update the latest Version a Resource, an HTTP `PUT` MAY be used.

The request MUST be of the form:

``` text
PUT /GROUPs/gID/RESOURCEs/rID
xRegistry-id: STRING ?
xRegistry-name: STRING ?
xRegistry-epoch: UINT ?
xRegistry-description: STRING ?
xRegistry-documentation: STRING ?
xRegistry-tags: STRING (JSON map) ?
xRegistry-format: STRING ?
xRegistry-RESOURCEUrl: URL ?

...Resource contents... ?
```

Where:
- if `id` is present then it MUST match the `rID` in the PATH
- if an `epoch` value is specified then the server MUST check to ensure that
  the value matches the current `epoch` value and if it differs then an error
  MUST be generated
- if `RESOURCEUrl` is present then the body MUST be empty and any
  local Resource contents MUST be erased
- if `format` is present and changing it would result in Versions of this
  Resource becoming invalid with respect to their own `format` values, then
  an error MUST be generated
- if the body is empty and `RESOURCEUrl` is absent then the Resource's
  contents MUST be erased
- a request to update a read-only attribute MUST be silently ignored
- a request to update a mutable attribute with an invalid value MUST
  generate an error (this includes deleting a mandatory mutable attribute)
- complex attributes that have nested values (eg. `tags`) MUST be specified
  in their entirety

Missing Registry HTTP headers MUST be interpreted as a request to delete the
attribute.

Note: `latestId` is a read-only attribute in this context and therefore
if present MUST be silently ignored.

Upon successful processing, the Version's `epoch` value MUST be incremented -
see [epoch](#epoch).

A successful response MUST include the same content than an HTTP `GET` on the
Resource would return, and be of the form:

``` text
HTTP/1.1 200 OK
Content-Type: ...
Content-Length: ...
xRegistry-id: STRING
xRegistry-name: STRING ?
xRegistry-epoch: UINT
xRegistry-self: URL
xRegistry-latestId: STRING
xRegistry-latestUrl: URL
xRegistry-description: STRING ?
xRegistry-documentation: STRING ?
xRegistry-tags: STRING (JSON map) ?
xRegistry-format: STRING ?
xRegistry-createdBy: STRING ?
xRegistry-createdOn: TIME ?
xRegistry-modifiedBy: STRING ?
xRegistry-modifiedOn: TIME ?
xRegistry-versionsUrl: URL
xRegistry-versionsCount: INT
xRegistry-RESOURCEUrl: URL ?
Content-Location: URL ?

...Resource contents... ?
```

Where:
- `id` MUST be the Resource's `id` and not the `id` of the latest Version
- `self` MUST be a URL to the Resource, not to the latest Version of the
  Resource
- if `Content-Location` is present then it MUST be a URL to the Version of the
  Resource in the `versions` collection - same as `latestUrl`

**Examples:**

Request:

``` text
PUT /endpoints/123/definitions/456
Content-Type: application/json; charset=utf-8
Content-Length: ...
xRegistry-epoch: 1

{
  # updated definition of a "Blob Created" event excluded for brevity
}
```

Response:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...
xRegistry-id: 456
xRegistry-name: Blob Created
xRegistry-epoch: 2
xRegistry-self: https://example.com/endpoints/123/definitions/456
xRegistry-latestId: 1.0
xRegistry-latestUrl: https://example.com/endpoints/123/definitions/456/versions/1.0
xRegistry-format: CloudEvents/1.0
xRegistry-versionsUrl: https://example.com/endpoints/123/definitions/456/versions
xRegistry-versionsCount: 1
Content-Location: https://example.com/endpoints/123/definitions/456/versions/1.0

{
  # updated definition of a "Blob Created" event excluded for brevity
}
```

Notice in this case aside from an updated "Blob Created" event (in the HTTP
body) we've included the `epoch` value in the request. If the current value
does not match `1` then an error would have been generated.

##### Updating a Resource's metadata

To update a Resource's metadata, an HTTP `PUT` with the `?meta` query parameter
MAY be used. Note, this will update the metadata of the latest Version of a
Resource without creating a new Version.

Note, unlike the other variant of the `PUT`, this operation is a complete
replacement of the latest Version and therefore any missing attributes from
the HTTP body will be removed.

The request MUST be of the form:

``` text
PUT /GROUPs/gID/RESOURCEs/rID?meta

{
  "id": "STRING", ?
  "name": "STRING", ?
  "epoch": UINT, ?
  "description": "STRING", ?
  "documentation": "URL", ?
  "tags": { "STRING": "STRING" * }, ?
  "format": "STRING", ?

  "RESOURCEUrl": "URL", ?
  "RESOURCE": { Resource contents }, ?
  "RESOURCEBase64": "STRING" ?
}
```

Where:
- if `id` is present then it MUST match the `rID` in the PATH
- if an `epoch` value is specified then the server MUST check to ensure that
  the value matches the current `epoch` value and if it differs then an error
  MUST be generated
- since `RESOURCE` and `RESOURCEBase64` are special attributes that will
  only appear in the Resource's serialization when requested, this update
  operation MUST interpret their absence from the request (when `RESOURCEUrl`
  is also not present) as a request to leave the Resource contents unchanged.
  However, if any of those 3 attributes are in the request then it MUST
  be interpreted as a request to update the contents of the Resource
  appropriately. A value of `null` for any of them MUST be interpreted
  as a request to delete the contents. If none of those 3 attributes are in
  the request, but the `RESOURCEUrl` attribute is set on the server then it
  MUST be interpreted as a request to delete the attribute
- at most, only one of `RESOURCEUrl`, `RESOURCE` or `RESOURCEBase64` MAY
  be present
- attributes not present in the request, or present with a value of `null`,
  MUST be interpreted as a request to delete the attribute (excluding the
  `RESOURCE` attributes mentioned above)
- if `format` is present and changing it would result in Versions of this
  Resource becoming invalid with respect to their `format` values, then
  an error MUST be generated
- a request to update, or delete, a nested `versions` collection, or a
  read-only attribute, MUST be silently ignored
- a request to update a mutable attribute with an invalid value MUST
  generate an error (this includes deleting a mandatory mutable attribute)
- complex attributes that have nested values (eg. `tags`) MUST be specified
  in their entirety

Upon successful processing, the Resource's `epoch` value MUST be incremented -
see [epoch](#epoch).

A successful response MUST include the same content that an HTTP `GET`
on the Resource's metadata would return, and be of the form:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...

{
  "id": "STRING",
  "name": "STRING", ?
  "epoch": UINT,
  "self": "URL",
  "latestId": "STRING",
  "latestUrl": "URL",
  "description": "STRING", ?
  "documentation": "URL", ?
  "tags": { "STRING": "STRING" * }, ?
  "format": "STRING", ?
  "createdBy": "STRING", ?
  "createdOn": "TIME", ?
  "modifiedBy": "STRING", ?
  "modifiedOn": "TIME", ?

  "RESOURCEUrl": "URL", ?                  # if not local

  "versionsUrl": "URL",
  "versionsCount": INT,
  "versions": { Versions collection } ?
}
```

**Examples:**
Request:

``` text
PUT /endpoints/123/definitions/456?meta

{
  "id": "456",
  "name": "Blob Created",
  "epoch": 2,
  "self": "https://example.com/endpoints/123/definitions/456",
  "latestId": "1.0",
  "description": "An updated description",
  "format": "CloudEvents/1.0"
}
```

Response:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...
Content-Location: https://example.com/endpoints/123/definitions/456/versions/1.0

{
  "id": "456",
  "name": "Blob Created",
  "epoch": 3,
  "self": "https://example.com/endpoints/123/definitions/456?meta",
  "latestId": "1.0",
  "latestUrl": "https://example.com/endpoints/123/definitions/456/versions/1.0",
  "description": "An updated description",
  "format": "CloudEvents/1.0",

  "versionsUrl": "https://example.com/endpoints/123/definitions/456/versions",
  "versionsCount": 1
}
```

##### Deleting Resources

To delete a single Resource, and all of its Versions, an HTTP `DELETE` MAY be
used.

The request MUST be of the form:

``` text
DELETE /GROUPs/gID/RESOURCEs/rID[?epoch=EPOCH]
```

Where:
- the request body SHOULD be empty

The following query parameters MUST be supported by servers:
- `epoch`<br>
  The presence of this query parameter indicates that the server MUST check
  to ensure that the `EPOCH` value matches the Resource's current `epoch` value
  and if it differs then an error MUST be generated

A successful response MUST return either:

``` text
HTTP/1.1 204 No Content
```

with an empty HTTP body, or:

``` text
HTTP/1.1 200 OK
Content-Type: ...
Content-Length: ...
xRegistry-id: STRING
xRegistry-name: STRING ?
xRegistry-epoch: UINT
xRegistry-self: URL
xRegistry-latestId: STRING ?
xRegistry-description: STRING ?
xRegistry-documentation: STRING ?
xRegistry-tags: STRING (JSON map) ?
xRegistry-format: STRING ?
xRegistry-createdBy: STRING ?
xRegistry-createdOn: TIME ?
xRegistry-modifiedBy: STRING ?
xRegistry-modifiedOn: TIME ?
xRegistry-RESOURCEUrl: URI ?

...Resource contents... ?
```

Where:
- the HTTP body SHOULD contain the latest representation of the Resource being
  deleted prior to being deleted
- the response MAY exclude the nested Versons collection (and `latestUrl`)
  if returning them is challenging

**Examples:**

Request:

``` text
DELETE /endpoints/123/definitions/456
```

Response:

``` text
HTTP/1.1 204 No Content
```

To delete multiple Resources, and all of their Versions,  an HTTP `DELETE` MAY
be used.

The request MUST be of the form:

``` text
DELETE /GROUPs/gID/RESOURCEs

[
  {
    "id": "STRING",
    "epoch": UINT ?     # If present it MUST match current value
  } *
]
```

Where:
- the request body MUST contain the list of Resource IDs to be deleted, however
  an empty list or an empty body MUST be interpreted as a request to delete
  all Resources of the specified Group
- if an `epoch` value is specified for a Resource then the server MUST check
  to ensure that the value matches the Resource's current `epoch` value and if
  it differs then an error MUST be generated

Any error MUST result in the entire request being rejected.

A successful response MUST return either:

``` text
HTTP/1.1 204 No Content
```

with an empty HTTP body, or:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...
Link: <URL>;rel=next;count=INT ?

{
  "ID": {
    "id": "STRING",
    "name": "STRING", ?
    "epoch": UINT,
    "self": "URL",
    "latestId": "STRING", ?
    "description": "STRING", ?
    "documentation"": "URL", ?
    "tags": { "STRING": "STRING" * }, ?
    "format": "STRING", ?
    "createdBy": "STRING", ?
    "createdOn": "TIME", ?
    "modifiedBy": "STRING", ?
    "modifiedOn": "TIME", ?

    "RESOURCEUrl": "URL" ?
  } *
}
```

Where:
- the HTTP body SHOULD contain the latest representation of the Resources being
  deleted prior to being deleted
- the response MAY exclude the nested Versons collection (and `latestUrl`)
  if returning them is challenging

A `DELETE /GROUPs/gID/RESOURCEs` without a body MUST delete all Resources in the
Group.

#### Versions

Versions represent historical instances of a Resource. When a Resource is
updated, there are two ways this might happen. First, the update can completely
replace an existing state of the Resource. This is most typically
done when the previous state of the Resource is no longer valid and there
is no reason to allow people to reference it. The second situation is when
both the old and new Versions of a Resource are meaningful and both might need
to be referenced. In this case the update will cause a new Version of the
Resource to be created and will be have a unique `id` within the scope of
the owning Resource.

For example, updating the state of Resource without creating a new Version
would make sense if there is a typo in the `description` field. But, adding
additional data to the content of a Resource might require a new Version and
a new ID (eg. change from "1.0" to "1.1").

This specification does not mandate a particular versioning scheme.

The serialization of a Version entity adheres to this form:

``` text
{
  "id": "STRING",
  "name": "STRING", ?
  "epoch": UINT,
  "self": "URL",
  "latest": BOOL,
  "description": "STRING", ?
  "documentation"": "URL", ?
  "tags": { "STRING": "STRING" * }, ?
  "format": "STRING", ?
  "createdBy": "STRING", ?
  "createdOn": "TIME", ?
  "modifiedBy": "STRING", ?
  "modifiedOn": "TIME", ?

  "RESOURCEUrl": "URL", ?                  # if not local
  "RESOURCE": { Resource contents }, ?     # if inlined & JSON
  "RESOURCEBase64": "STRING" ?             # if inlined & ~JSON
}
```

Versions include the following attributes as defined by the
[Resource](#resources) entity:
- [`id`](#id)
- [`name`](#name)
- [`epoch`](#epoch)
- [`self`](#self)
- [`description`](#description)
- [`documentation`](#documentation)
- [`tags`](#tags)
- [`format`](#format)
- [`createdBy`](#createdby)
- [`createdOn`](#createdon)
- [`modifiedBy`](#modifiedby)
- [`modifiedOn`](#modifiedon)
- `RESOURCEUrl`
- `RESOURCE`
- `RESOURCEBase64`

and the following Version specific attributes:

**`latest`**
- Type: Boolean
- Description: indicates whether this Version is the "latest" Version of the
  owning Resource. This value is different from other attributes in that it
  might often be a calculated value rather than persisted in a datastore.
  Thus, when its value changes due to the latest Version of a Resource
  changing, the Version itself does not change - meaning the `epoch` value
  remains unchanged.
- Constraints:
  - REQUIRED in responses, OPTIONAL on requests
  - OPTIONAL in document view
  - MUST be a read-only attribute in API view
  - MUST be either `true` or `false`, case sensitive
- Examples:
  - `true`
  - `false`

##### Version IDs

If a server does not support client-side specification of the `id` of a new
Version, or if a client choose to not specify the `id`, then the server MUST
create a new unique `id` itself.

Servers MAY have their own algorithm for creation of new Version `id` values,
but the default algorithm is as follows:
- `id` MUST be a string serialization of a monotonically increasing (by `1`)
  unsigned integer starting with `1` and is scoped to the owning Resource
- each time a new `id` is generated, if an existing Version already has that
  `id` then the server MUST generate the next `id` in the sequence and try
  again
- for clarity, if a Version is deleted its `id` will never be reused because
  the `id` values are always increasing and never reset back to `1`

##### Latest Version of a Resource

As Versions of a Resource are added or removed there needs to be a mechanism
by which the "latest" one is known. This can be determined by the client
explicitly indicating which one is the latest, or it can be determined by the
server.

For a client to indicate which Version is the "latest", certain APIs support
a `latestId` query parameter whose value is the Version `id` that is to
become the latest. This query parameter MAY appear on the creation of a
new Version API and on the deletion of a Verson API. See those respective
APIs for more information.

To change the latest Version of a resource outside of a create or delete
operation, there are two options available.

**Updating the `latestId` on a Resource**

The latest Version MAY be selected via a request to the owning Resource.

The request MUST be of the form:

``` text
PUT /GROUPs/gID/RESOURCEs/rID?latestId=vID
```

Where:
- `vID` MUST be the `id` of the Version that is to become the latest Version
- the request SHOULD NOT include any xRegistry HTTP headers nor any HTTP body
  but if present then they SHOULD be silently ignored

Note that while this API looks very similar to the API to update the content
and metadata about the "latest" Version, this only updates the reference in
the Resource to the latest Version and nothing else. This is why there are
no xRegistry HTTP headers or HTTP body in the request.

If the `vID` value does not reference an existing Version of this Resource
then an HTTP `400 Bad Request` error MUST be generated.

Upon successful completion of the request the `latestId` and `latestUrl`
fields of the Resource MUST be updated appropriately, and the `latest`
attribute on both the previous latest Version and the new latest Version
MUST be updated as well.

A successful response MUST be of the form:

``` text
HTTP/1.1 200 OK
Content-Type: ...
Content-Length: ...
xRegistry-id: STRING
xRegistry-name: STRING ?
xRegistry-epoch: UINT
xRegistry-self: URL
xRegistry-latestId: STRING
xRegistry-latestUrl: URL
xRegistry-description: STRING ?
xRegistry-documentation: STRING ?
xRegistry-tags: STRING (JSON map) ?
xRegistry-format: STRING ?
xRegistry-createdBy: STRING ?
xRegistry-createdOn: TIME ?
xRegistry-modifiedBy: STRING ?
xRegistry-modifiedOn: TIME ?
xRegistry-versionsUrl: URL
xRegistry-versionsCount: INT
xRegistry-RESOURCEUrl: URL ?
Content-Location: URL ?

...Resource contents... ?
```

Where:
- if `Content-Location` is present then it MUST be a URL to the Version of the
  Resource in the `versions` collection - same as `latestUrl`
- if `RESOURCEUrl` is present then the HTTP body MUST be empty
- if the HTTP body is not empty then `RESOURCEUrl` MUST NOT be present

Note the response is the same response as an HTTP `GET` to the Resource.

**Updating the `latest` via a Version**

The latest Version MAY be selected via a request to the new latest Version.

The request MUST be of the form:

``` text
PUT /GROUPs/gID/RESOURCEs/rID/versions/vID?latest=true
```

Where:
- the request SHOULD NOT include any xRegistry HTTP headers nor any HTTP body
  but if present then they SHOULD be silently ignored

Note that while this API looks very similar to the API to update the content
and metadata about a Version, this only updates the reference in
the Resource to the latest Version and nothing else. No changes are made to
the Version entities (new or previous latest Version). This is why there are
no xRegistry HTTP headers or HTTP body in the request.

If the `vID` value does not reference an existing Version of this Resource
then an HTTP `404 Not Found` error MUST be generated.

Upon successful completion of the request the `latestId` and `latestUrl`
fields of the Resource MUST be updated appropriately, and the `latest`
attribute on both the previous latest Version and the new latest Version
MUST be updated as well.

A successful response MUST be of the form:

``` text
HTTP/1.1 200 OK
Content-Type: ...
Content-Length: ...
xRegistry-id: STRING
xRegistry-name: STRING ?
xRegistry-epoch: UINT
xRegistry-self: URL
xRegistry-description: STRING ?
xRegistry-documentation: STRING ?
xRegistry-tags: STRING (JSON map) ?
xRegistry-format: STRING ?
xRegistry-createdBy: STRING ?
xRegistry-createdOn: TIME ?
xRegistry-modifiedBy: STRING ?
xRegistry-modifiedOn: TIME ?
xRegistry-versionsUrl: URL
xRegistry-versionsCount: INT
xRegistry-RESOURCEUrl: URL ?

...Resource contents... ?
```

Where:
- if `RESOURCEUrl` is present then the HTTP body MUST be empty
- if the HTTP body is not empty then `RESOURCEUrl` MUST NOT be present

Note the response is the same response as an HTTP `GET` to the Version.

##### Retrieving all Versions of a Resource

To retrieve all Versions of a Resource, an HTTP `GET` MAY be used.

The request MUST be of the form:

``` text
GET /GROUPs/gID/RESOURCEs/rID/versions[?inline=...&filter=...]
```

The following query parameters MUST be supported by servers:
- `inline` - See [inlining](#inlining) for more information
- `filter` - See [filtering](#filtering) for more information

A successful response MUST be of the form:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...
Link: <URL>;rel=next;count=INT ?

{
  "ID": {                                     # The Version id
    "id": "STRING",
    "name": "STRING", ?
    "epoch": UINT,
    "self": "URL",
    "latest": BOOL,
    "description": "STRING", ?
    "documentation"": "URL", ?
    "tags": { "STRING": "STRING" * }, ?
    "format": "STRING", ?
    "createdBy": "STRING", ?
    "createdOn": "TIME", ?
    "modifiedBy": "STRING", ?
    "modifiedOn": "TIME", ?

    "RESOURCEUrl": "URL", ?                  # if not local
    "RESOURCE": { Resource contents }, ?     # if inlined & JSON
    "RESOURCEBase64": "STRING" ?             # if inlined & ~JSON
  } *
}
```

Where:
- the key (`ID`) of each item in the map MUST be the `id` of the
  respective Version

**Examples:**

Request:

``` text
GET /endpoints/123/definitions/456/versions
```

Response:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...
Link: <https://example.com/endpoints/123/definitions/456/versions&page=2>;rel=next;count=100

{
  "1.0": {
    "id": "1.0",
    "name": "Blob Created",
    "epoch": 1,
    "self": "https://example.com/endpoints/123/definitions/456",
    "latest": true,
    "format": "CloudEvents/1.0"
  }
}
```

##### Creating a new Version of a Resource

To create a new Version of a Resource, an HTTP `POST` MAY be used.

Note that the new Version will not inherit any values from any existing
Version, so the new Version will need to be fully specified as part of the
request.

The request MUST be of the form:

``` text
POST /GROUPs/gID/RESOURCEs/rID/versions[?latest[=true|false]]
Content-Type: ...
Content-Length: ...
xRegistry-id: STRING ?
xRegistry-name: STRING ?
xRegistry-epoch: STRING ?
xRegistry-description: STRING ?
xRegistry-documentation: STRING ?
xRegistry-tags: STRING (JSON map) ?
xRegistry-format: STRING ?
xRegistry-RESOURCEUrl: URL ?      # If present body MUST be empty

...Resource contents... ?         # If present RESOURCEUrl MUST be absent
```

TODO: SHOULD "latest" be an attribute instead?

Where:
- if `id` is present then it MUST be unique across all Versions within this
  Resource. If absent then the server MUST generate a new unique value
- `epoch` is OPTIONAL and if present MUST be silently ignored
- if `RESOURCEUrl` is present the HTTP body MUST be empty
- the HTTP body MUST contain the contents of the new Version if the
  `RESOURCEUrl` HTTP header is absent. Note, the body MAY be empty even if
  the HTTP header is not present, indicating that the Version is empty
- a request that is missing a mandatory attribute MUST generate an error
- `latest` indicates whether the new Version is to become the latest Version
  for the Resource, see below

Notice the Version attributes (metadata) are passed as HTTP headers, not
in the HTTP body. Also, as a reminder HTTP headers are case insensitive.

Processing of `latest` MUST adhere to the following rules:
- if `latest` is not present then the new Version MUST become the latest
  Version
- if `latest` is present with a value of `true` or no value at all, then the
  new Version MUST becomes the latest Version
- if `latest` is present with a value of `false` then the current latest
  Version does not change
- any other value for `latest` MUST generate an error
- if `latest` is present but the server does not support this flag then
  an error MUST be generated - see `latest` in the
  [Registry Model](#registry-model) section

A successful response MUST include the same content than an HTTP `GET` on the
Version would return, and be of the form:

``` text
HTTP/1.1 201 Created
Content-Type: ...
Content-Length: ...
xRegistry-id: STRING
xRegistry-name: STRING ?
xRegistry-epoch: UINT
xRegistry-self: STRING
xRegistry-latest: BOOL
xRegistry-description: STRING ?
xRegistry-documentation: STRING ?
xRegistry-tags: STRING ?
xRegistry-format: STRING ?
xRegistry-createdBy: STRING ?
xRegistry-createdOn: TIME ?
xRegistry-modifiedBy: STRING ?
xRegistry-modifiedOn: TIME ?
xRegistry-RESOURCEUrl: URL ?
Location: URL

...Resource contents... ?
```

Where:
- `id` MUST be the ID of the Version, not of the owning Resource
- `self` MUST be a URL to the Version, not to the owning Resource
- if `RESOURCEUrl` is present then the HTTP body MUST be empty
- if the HTTP body is not empty then `RESOURCEUrl` MUST NOT be present
- `Location` MUST be a URL to the Version - same as `self`

**Examples:**

Request:

``` text
POST /endpoints/123/definitions/456/versions
Content-Type: application/json; charset=utf-8
Content-Length: ...
xRegistry-id: v2.0
xRegistry-name: Blob Created
xRegistry-format: CloudEvents/1.0

{
  # definition of a "Blob Created" event excluded for brevity
}
```

Response:

``` text
HTTP/1.1 201 Created
Content-Type: application/json; charset=utf-8
Content-Length: ...
xRegistry-id: v2.0
xRegistry-name: Blob Created
xRegistry-epoch: 1
xRegistry-self: https://example.com/endpoints/123/definitions/456/versions/v2.0
xRegistry-latest: true
xRegistry-format: CloudEvents/1.0
Location: https://example.com/endpoints/123/definitions/456/versions/v2.0

{
  # definition of a "Blob Created" event excluded for brevity
}
```

##### Creating a New Version of a Resource as Metadata

To create a new Version of a Resource as metadata (Resource attributes), an
HTTP `POST` with the `?meta` query parameter MAY be used.

Note that the new Version will not inherit any values from any existing
Version, so the new Version will need to be fully specified as part of the
request.

The request MUST be of the form:

``` text
POST /GROUPs/gID/RESOURCEs/rID/versions?meta
Content-Type: application/json; charset=utf-8
Content-Length: ...

{
  "id": "STRING", ?
  "name": "STRING", ?
  "epoch": UINT, ?
  "description": "STRING", ?
  "documentation"": "URL", ?
  "tags": { "STRING": "STRING" * }, ?
  "format": "STRING", ?

  "RESOURCEUrl": "URL", ?                  # if not local
  "RESOURCE": { Resource contents }, ?     # if inlined & JSON
  "RESOURCEBase64": "STRING" ?             # if inlined & ~JSON
}
```

Where:
- if `id` is present then it MUST be unique across all Versions within this
  Resource. If absent then the server MUST generate a new unique value
- `epoch` is OPTIONAL and if present MUST be silently ignored
- at most, only one of `RESOURCEUrl`, `RESOURCE` or `RESOURCEBase64` MAY
  be present
- a request that is missing a mandatory attribute MUST generate an error.

Note that the response MUST NOT include the `RESOURCE` or `RESOURCEBase64`
attributes.

A successful response MUST include the same content than an HTTP `GET` on the
Version would return, and be of the form:

``` text
HTTP/1.1 201 Created
Content-Type: ...
Content-Length: ...
Location: URL

{
  "id": "STRING",
  "name": "STRING", ?
  "epoch": UINT,
  "self": "URL",
  "latest": BOOL,
  "description": "STRING", ?
  "documentation"": "URL", ?
  "tags": { "STRING": "STRING" * }, ?
  "format": "STRING", ?
  "createdBy": "STRING", ?
  "createdOn": "TIME", ?
  "modifiedBy": "STRING", ?
  "modifiedOn": "TIME", ?

  "RESOURCEUrl": "URL", ?                  # if not local
  "RESOURCE": { Resource contents }, ?     # if inlined & JSON
  "RESOURCEBase64": "STRING" ?             # if inlined & ~JSON
}
```

Where:
- `Location` MUST be a URL to the Version - same as `self`
- `self` MUST be a URL to the metadata of the Version (i.e. with `?meta`)

**Examples:**

Request:

``` text
POST /endpoints/123/definitions/456/versions?meta
Content-Type: application/json; charset=utf-8
Content-Length: ...

{
  "id": "v2.0",
  "name": "Blob Created",
  "format": "CloudEvents/1.0",
  "definition": {
    # definition of a "Blob Created" event excluded for brevity
  }
}
```

Response:

``` text
HTTP/1.1 201 Created
Content-Type: application/json; charset=utf-8
Content-Length: ...
Location: https://example.com/endpoints/123/definitions/456/versions/v2.0

{
  "id": "v2.0",
  "name": "Blob Created",
  "epoch": 1,
  "self": "https://example.com/endpoints/123/definitions/456/versions/v2.0"
  "latest": true,
  "format": "CloudEvents/1.0",
}
```

##### Retrieving a Version of a Resource

To retrieve a particular Version of a Resource, an HTTP `GET` MAY be used.

The request MUST be of the form:

``` text
GET /GROUPs/gID/RESOURCEs/rID/versions/vID[?inline=...]
```

The following query parameters MUST be supported by servers:
- `inline` - See [inlining](#inlining) for more information

A successful response MUST either return the Version or an HTTP redirect to
the `RESOURCEUrl` value when defined.

In the case of returning the Resource, the response MUST be of the form:

``` text
HTTP/1.1 200 OK
Content-Type: ...
Content-Length: ...
xRegistry-id: STRING
xRegistry-name: STRING ?
xRegistry-epoch: UINT
xRegistry-self: URL
xRegistry-latest: BOOL
xRegistry-description: STRING ?
xRegistry-documentation: STRING ?
xRegistry-tags: STRING (JSON map) ?
xRegistry-format: STRING ?
xRegistry-createdBy: STRING ?
xRegistry-createdOn: TIME ?
xRegistry-modifiedBy: STRING ?
xRegistry-modifiedOn: TIME ?

...Resource contents...
```

Where:
- `id` MUST be the ID of the Version, not of the owning Resource
- `self` MUST be a URL to the Version, not to the owning Resource

In the case of a redirect, the response MUST be of the form:

``` text
HTTP/1.1 307 Temporary Redirect
xRegistry-id: STRING
xRegistry-name: STRING ?
xRegistry-epoch: UINT
xRegistry-self: URL
xRegistry-latest: BOOL
xRegistry-description: STRING ?
xRegistry-documentation: STRING ?
xRegistry-tags: STRING (JSON map) ?
xRegistry-format: STRING ?
xRegistry-createdBy: STRING ?
xRegistry-createdOn: TIME ?
xRegistry-modifiedBy: STRING ?
xRegistry-modifiedOn: TIME ?
xRegistry-RESOURCEUrl: URL
Location: URL
```

Where:
- `id` MUST be the ID of the Version, not of the owning Resource
- `self` MUST be a URL to the Version, not to the owning Resource
- `Location` and `RESOURCEUrl` MUST have the same value

**Examples:**

Request:

``` text
GET /endpoints/123/definitions/456/versions/1.0
```

Response:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...
xRegistry-id: 1.0
xRegistry-name: Blob Created
xRegistry-epoch: 2
xRegistry-self: https://example.com/endpoints/123/definitions/456/versions/1.0
xRegistry-latest: true
xRegistry-format: CloudEvents/1.0

{
  # definition of a "Blob Created" event excluded for brevity
}
```

##### Retrieving a Version's metadata

To retrieve a particular Version's metadata (Version attributes), an HTTP
 `GET` with the `?meta` query parameter MAY be used.

The request MUST be of the form:

``` text
GET /GROUPs/gID/RESOURCEs/rID/versions/vID?meta[&inline=...]
```

A successful response MUST be of the form:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...

{
  "id": "STRING",
  "name": "STRING", ?
  "epoch": UINT,
  "self": "URL",
  "latest": BOOL,
  "description": "STRING", ?
  "documentation"": "URL", ?
  "tags": { "STRING": "STRING" * }, ?
  "format": "STRING", ?
  "createdBy": "STRING", ?
  "createdOn": "TIME", ?
  "modifiedBy": "STRING", ?
  "modifiedOn": "TIME", ?

  "RESOURCEUrl": "URL", ?                  # if not local
  "RESOURCE": { Resource contents }, ?     # if inlined & JSON
  "RESOURCEBase64": "STRING" ?             # if inlined & ~JSON
}
```

Where:
- `id` MUST be the Version's `id` and not the `id` of the owning Resource
- `self` MUST be a URL to the Version, not to the owning Resource

**Examples:**

Request:

``` text
GET /endpoints/123/definitions/456/versions/1.0?meta
```

Response:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...

{
  "id": "1.0",
  "name": "Blob Created",
  "epoch": 2,
  "self": "https://example.com/endpoints/123/definitions/456/versions/1.0",
  "latest": true,
  "format": "CloudEvents/1.0"
}
```

##### Updating a Version of a Resource

To update a Version of a Resource, an HTTP 'PUT' MAY be used.

Note, this will update an existing Version and not create a new one.

The request MUST be of the form:

``` text
PUT /GROUPs/gID/RESOURCEs/rID/versions/vID
xRegistry-id: STRING ?
xRegistry-name: STRING ?
xRegistry-epoch: UINT ?
xRegistry-latest: BOOL ?
xRegistry-description: STRING ?
xRegistry-documentation: STRING ?
xRegistry-tags: STRING (JSON map) ?
xRegistry-format: STRING ?
xRegistry-RESOURCEUrl: URL ?

...Resource contents... ?
```

Where:
- if `id` is present then it MUST match the `vID` in the PATH
- if an `epoch` value is specified then the server MUST check to ensure that
  the value matches the current `epoch` value and if it differs then an error
  MUST be generated
- if `latest` is present with a value of `true` then this Version MUST become
  the latest Version of the owning Resource and all other Versions MUST be
  changed to have a `latest` value of `false`
- if `RESOURCEUrl` is present then the body MUST be empty and any
  local Version contents MUST be erased
- if `format` is present and changing it would result in the Version
  becoming invalid with respect to the `format` of the owning Resource, then
  an error MUST be generated
- if the body is empty and `RESOURCEUrl` is absent then the Version's
  contents MUST be erased
- a request to update a read-only attribute MUST be silently ignored
- a request to update a mutable attribute with an invalid value MUST
  generate an error (this includes deleting a mandatory mutable attribute)
- complex attributes that have nested values (eg. `tags`) MUST be specified
  in their entirety

A successful response MUST include the same content than an HTTP `GET` on the
Version would return, and be of the form:

``` text
HTTP/1.1 200 OK
Content-Type: ...
Content-Length: ...
xRegistry-id: STRING
xRegistry-name: STRING ?
xRegistry-epoch: UINT
xRegistry-self: URL
xRegistry-latest: BOOL
xRegistry-description: STRING ?
xRegistry-documentation: STRING ?
xRegistry-tags: STRING (JSON map) ?
xRegistry-format: STRING ?
xRegistry-createdBy: STRING ?
xRegistry-createdOn: TIME ?
xRegistry-modifiedBy: STRING ?
xRegistry-modifiedOn: TIME ?
xRegistry-RESOURCEUrl: URL ?

...Resource contents... ?
```

Where:
- `id` MUST be the Version's `id` and not the `id` of the owning Resource
- `self` MUST be a URL to the Version, not to the owning Resource

**Examples:**

Request:

``` text
PUT /endpoints/123/definitions/456/versions/1.0
Content-Type: application/json; charset=utf-8
Content-Length: ...
xRegistry-epoch: 2

{
  # updated definition of a "Blob Created" event excluded for brevity
}
```

Response:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...
xRegistry-id: 1.0
xRegistry-name: Blob Created
xRegistry-epoch: 3
xRegistry-self: https://example.com/endpoints/123/definitions/456/versions/1.0
xRegistry-latest: true
xRegistry-format: CloudEvents/1.0

{
  # updated definition of a "Blob Created" event excluded for brevity
}
```

Notice in this case aside from an updated "Blob Created" event (in the HTTP
body) we've included the `epoch` value in the request. If the current value
does not match `2` then an error would have been generated.

##### Updating a Version's metadata

To update a Version's metadata, an HTTP `PUT` with the `?meta` query parameter
MAY be used. Note, this will update the metadata of a particular Version of a
Resource without creating a new one.

Note, unlike the other variant of the `PUT`, this operation is a complete
replacement of the Version and therefore any missing attributes from the HTTP
body will be removed.

The request MUST be of the form:

``` text
PUT /GROUPs/gID/RESOURCEs/rID/versions/vID?meta

{
  "id": "STRING", ?
  "name": "STRING", ?
  "epoch": UINT, ?
  "latest": BOOL, ?
  "description": "STRING", ?
  "documentation"": "URL", ?
  "tags": { "STRING": "STRING" * }, ?
  "format": "STRING", ?

  "RESOURCEUrl": "URL", ?
  "RESOURCE": { Resource contents }, ?
  "RESOURCEBase64": "STRING" ?
}
```

Where:
- if `id` is present then it MUST match the `vID` in the PATH
- if an `epoch` value is specified then the server MUST check to ensure that
  the value matches the current `epoch` value and if it differs then an error
  MUST be generated
- if `latest` is present with a value of `true` then this Version MUST become
  the latest Version of the owning Resource and all other Versions MUST be
  changed to have a `latest` value of `false`
- since `RESOURCE` and `RESOURCEBase64` are special attributes that will
  only appear in the Resource's serialization when requested, this update
  operation MUST interpret their absence from the request (when `RESOURCEUrl`
  is also not present) as a request to leave the Resource contents unchanged.
  However, if any of those 3 attributes are in the request then it MUST
  be interpreted as a request to update the contents of the Resource
  appropriately. A value of `null` for any of them MUST be interpreted
  as a request to delete the contents. If none of those 3 attributes are in
  the request, but the `RESOURCEUrl` attribute is set on the server then it
  MUST be interpreted as a request to delete the attribute
- at most, only one of `RESOURCEUrl`, `RESOURCE` or `RESOURCEBase64` MAY
  be present
- attributes not present in the request, or present with a value of `null`,
  MUST be interpreted as a request to delete the attribute (excluding the
  `RESOURCE` attributes mentioned above)
- if `format` is present and changing it would result in the Version
  becoming invalid with respect to the `format` of the owning Resource, then
  an error MUST be generated
- a request to update a mutable attribute with an invalid value MUST
  generate an error (this includes deleting a mandatory mutable attribute)
- complex attributes that have nested values (eg. `tags`) MUST be specified
  in their entirety

Upon successful processing, the Version's `epoch` value MUST be incremented -
see [epoch](#epoch).

A successful response MUST include the same content that an HTTP `GET`
on the Version's metadata would return, and be of the form:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...

{
  "id": "STRING",
  "name": "STRING", ?
  "epoch": UINT,
  "self": "URL",
  "latest": BOOL,
  "description": "STRING", ?
  "documentation"": "URL", ?
  "tags": { "STRING": "STRING" * }, ?
  "format": "STRING", ?
  "createdBy": "STRING", ?
  "createdOn": "TIME", ?
  "modifiedBy": "STRING", ?
  "modifiedOn": "TIME", ?

  "RESOURCEUrl": "URL", ?                  # if not local
}
```

**Examples:**

Request:

``` text
PUT /endpoints/123/definitions/456/versions/1.0?meta

{
  "id": "1.0",
  "name": "Blob Created",
  "epoch": 2,
  "description": "An updated description"
}
```

Response:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...

{
  "id": "1.06",
  "name": "Blob Created",
  "epoch": 3,
  "self": "https://example.com/endpoints/123/definitions/456/versions/1.0",
  "latest": true,
  "description": "An updated description",
  "format": "CloudEvents/1.0"
}
```

##### Deleting Versions of a Resource
To delete a single Version of a Resource, an HTTP `DELETE` MAY be used.

The request MUST be of the form:

``` text
DELETE /GROUPs/gID/RESOURCEs/rID/versions/vID[?epoch=EPOCH][&latestId=vID]
```

Where:
- the request body SHOULD be empty

The following query parameters MUST be supported by servers:
- `epoch`<br>
  The presence of this query parameter indicates that the server MUST check
  to ensure that the `EPOCH` value matches the Resource's current `epoch` value
  and if it differs then an error MUST be generated

If the server supports client-side selection of the latest Version of a
Resource (see the [Registry Model](#registry-model)), then the following
applies:
- `latestId` query parameter MUST be suported and its value (`vID`) is the
  `id` of Version which is the become the latest Version of the owning Resource
- `latestId` MAY be specified even if the Version being delete is not currently
  the latest Version
- if `latestId` is present but its value does not match any Version (after the
  delete operation is completed) then an error MUST be generated and the
  entire delete MUST be rejected
- if the latest Verison of a Resource is being deleted but `latestId` was
  not specified, then the following rules apply:
  - the server SHOULD choose the most recently create Version as the latest
    Version
  - if the creation times can not be determined, then the server SHOULD choose
    the Version with the lexicographical highest Version `id` value as the
    latest Version
  - implementations MAY choose use their own algorithm for choosing the new
    latest Version
  - implementations MAY choose to generate an error, thus forcing the client
    to always choose the next "latest" Version

If a Resource only has one Version, an attempt to delete it MUST generate an
error.

A successful response MUST return either:

``` text
HTTP/1.1 204 No Content
```

with an empty HTTP body, or:

``` text
HTTP/1.1 200 OK
Content-Type: ...
Content-Length: ...
xRegistry-id: STRING
xRegistry-name: STRING ?
xRegistry-epoch: UINT
xRegistry-self: URL
xRegistry-latest: BOOL
xRegistry-description: STRING ?
xRegistry-documentation: STRING ?
xRegistry-tags: STRING (JSON map) ?
xRegistry-format: STRING ?
xRegistry-createdBy: STRING ?
xRegistry-createdOn: TIME ?
xRegistry-modifiedBy: STRING ?
xRegistry-modifiedOn: TIME ?
xRegistry-RESOURCEUrl: URL ?

...Resource contents... ?
```

Where:
- the HTTP body SHOULD contain the latest representation of the Version being
  deleted prior to being deleted

**Examples:**

Request:

``` text
DELETE /endpoints/123/definitions/456/versions/1.0
```

Response:

``` text
HTTP/1.1 204 No Content
```

To delete multiple Versions, an HTTP `DELETE` MAY be used.

The request MUST be of the form:

``` text
DELETE /GROUPs/gID/RESOURCEs/rID/versions[?latestId=vID]

[
  {
    "id": "STRING",
    "epoch": UINT ?     # If present it MUST match current value
  } +
]
```

Where:
- the request body MUST contain the list of Version IDs to be deleted
- if an `epoch` value is specified for a Version then the server MUST check
  to ensure that the value matches the Version's current `epoch` value and if
  it differs then an error MUST be generated
- the HTTP body MUST contain at least one Version ID. An attempt to delete all
  Versions MUST generate an error.

If the server supports client-side selection of the latest Version of a
Resource (see the [Registry Model](#registry-model)), then the following
applies:
- `latestId` query parameter MUST be suported and its value (`vID`) is the
  `id` of Version which is the become the latest Version of the owning Resource
- `latestId` MAY be specified even if the Version being delete is not currently
  the latest Version
- if `latestId` is present but its value does not match any Version (after the
  delete operation is completed) then an error MUST be generated and the
  entire delete MUST be rejected
- if the latest Verison of a Resource is being deleted but `latestId` was
  not specified, then the following rules apply:
  - the server SHOULD choose the most recently create Version as the latest
    Version
  - if the creation times can not be determined, then the server SHOULD choose
    the Version with the lexicographical highest Version `id` value as the
    latest Version
  - implementations MAY choose use their own algorithm for choosing the new
    latest Version
  - implementations MAY choose to generate an error, thus forcing the client
    to always choose the next "latest" Version

Any error MUST result in the entire request being rejected.

A successful response MUST return either:

``` text
HTTP/1.1 204 No Content
```

with an empty HTTP body, or:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...
Link: <URL>;rel=next;count=INT ?

{
  "ID": {
    "id": "STRING",
    "name": "STRING", ?
    "epoch": UINT,
    "self": "URL",
    "latest": BOOL,
    "description": "STRING", ?
    "documentation"": "URL", ?
    "tags": { "STRING": "STRING" * }, ?
    "format": "STRING", ?
    "createdBy": "STRING", ?
    "createdOn": "TIME", ?
    "modifiedBy": "STRING", ?
    "modifiedOn": "TIME", ?

    "RESOURCEUrl": "URL" ?
  } +
}
```

Where:
- the HTTP body SHOULD contain the latest representation of the Versions being
  deleted prior to being deleted

### Inlining

The `inline` query parameter on a request indicates that the response
MUST include the contents of all specified inlinable attributes. Inlinable
attributes include:
- all [Registry Collection](#registry-collections) types - eg. `GROUPs`,
  `RESOURCEs` and `versions`
- the `RESOURCE` attribute in a Resource

While the `RESOURCE` and `RESOURCEBase64` attributes are defined as two
separate attributes, they are technically two separate "views" of the same
underlying data. As such, the usage of each will be based on the content type
of the Resource, specifying `RESOURCE` in the `inline` query parameter MUST
be interpreted as a request for the appropriate attribute. In other words,
`RESOURCEBase64` is not be a valid inlinable attribute name.

Use of this feature is useful for cases where the contents of the Registry are
to be represented as a single (self-contained) document.

Some examples:
- `GET /?inline=endpoints`
- `GET /?inline=endpoints.definitions`
- `GET /endpoints/123/?inline=definitions.definition`
- `GET /endpoints/123/definitions/456?inline=definition`

The format of the `inline` query parameter is:

``` text
inline[=PATH[,...]]
```

Where `PATH` is a string indicating which inlinable attributes to inline in
in the response. References to nested attributes are
represented using a dot(`.`) notation - for example `GROUPs.RESOURCEs`.

There MAY be multiple `PATH`s specified, either as comma separated values on
a single `inline` query parameter or via multiple `inline` query parameters.
Absence of a value, or a value of an empty string, indicates that all nested
inlinable attributes MUST be inlined.

The specific value of `PATH` will vary based on where the request is directed.
For example, a request to the root of the Registry MUST start with a `GROUPs`
name, while a request directed at a Group would start with a `RESOURCEs` name.

For example, given a Registry with a model that has "endpoints" as a Group and
"definitions" as a Resource within "endpoints", the table below shows some
`PATH` values and a description of the result:

| HTTP `GET` Path | Example ?inline=PATH values | Comment |
| --- | --- | --- |
| / | ?inline=endpoints | Inlines the `endpoints` collection, but just one level of it, not any nested inlinable attributes |
| / | ?inline=endpoints.definitions.versions | Inlines the `version` collection of all definitions. Note that this implicitly means the parent attribtues (`definitions` and `endpoints` would also be inlined - however any other `GROUPs` or `RESOURCE`s types would not be |
| /endpoints | ?inline=definitions | Inlines just `definitions` and not any neseted attributes. Note we don't need to specify the parent `GROUP` since the URL already included it |
| /endpoints/123 | ?inline=definitions.versions | Similar to the previous `endpoints.definitions.version` example |
| /endpoints/123 | ?inline=definitions.definition | Inline the Resource itself |
| /endpoints/123 | ?inline=endpoints | Invalid, already in `endpoints` and there is no `RESOURCE` called `endpoints` |

Note that asking for an attribute to be inlined will implicitly cause all of
its parents to be inlined as well.

When specifying a collection to be inlined, it MUST be specified using the
plural name for the collection in its defined case.

A request to inline an unknown, or non-inlinable, attribute MUST generate an
error.

Note: If the Registry can not return all expected data in one response then it
MUST generate an HTTP `406 Not Acceptable` error and SHOULD include a error
message in the HTTP body indicating that the response is too large to be
sent in one message. In those cases, the client will need to query the
individual inlinable attributes in isolation so the Registry can leverage
[pagination](../pagination/spec.md) of the response.

### Filtering

The `filter` query parameter on a request indicates that the response
MUST include only those entities that match the specified filter criteria.
This means that any Registry Collection's attributes MUST be modified
to match the resulting subset. In particular:
- if the collection is inlined it MUST only include entities that match the
  filter expression(s)
- the collection `Url` attribute MUST include the filter expression(s) in its
  query parameters
- the collection `Count` attribute MUST only count the entities that match the
  filter expression(s)

The format of the `filter` query parameter is:

``` text
filter=EXPRESSION[,EXPRESSION]
```

Where:
- all `EXPRESSION` values within the scope of one `filter` query parameter
  MUST be evaluated as a logical `AND` and any matching entities MUST satisfy
  all of the specified expressions within that `filter` query parameter
- the `filter` query parameter can appear multiple times and if so MUST
  be evaluated as a logical `OR` and the response MUST include all entities
  that match any of the individual filter query parameters

The abstract processing logic would be:
- for each `filter` query parameter, find all entities that satisfy all
  expressions for that `filter`
- after processing all individual `filter` query parameters, combine those
  individual results into one result set and remove any duplicates - adjusting
  any collection `Url` and `Count` values as needed

The format of `EXPRESSION` is:

``` text
[PATH.]ATTRIBUTE[=VALUE]
```

Where:
- `PATH` MUST be a dot(`.`) notation traversal of the Registry to the entity
  of interest, or absent if at the top of the Registry request. Note that
  the `PATH` value is based on the requesting URL and not the root of the
  Registry. See the examples below
- `PATH` MUST only consist of valid `GROUPs`, `RESOURCEs` or `versions`,
  otherwise an error MUST be generated
- `ATTRIBUTE` MUST be the attribute of the entity to be examined
- a reference to a nonexistent attribute SHOULD NOT generate an error and
  SHOULD be treated the same as a non-matching situation
- `VALUE` MUST be the desired value of the attribute being examined. Only
  entities whose specified `ATTRIBUTE` with this `VALUE` MUST be included in
  the response. In general, when `VALUE` is absent, a successful match occurs
  when the `ATTRIBUTE` has a non-empty/zero value. See below for more
  information

When comparing an `ATTRIBUTE` to the specified `VALUE` the following rules
MUST apply for an entity to be considered a match of the filter expression:
- for numeric attributes, it MUST be an exact match. When `VALUE` is not
  present then the attribute matches if its value is non-zero
- for string attributes, its value MUST contain the `VALUE` within it but
  does not need to be an exact case match. When `VALUE` is not present then
  the attribute matches if its value is a non-empty string. Note that a string
  attribute with no value MUST be considered the same one with an empty string
- for boolean attributes, its value MUST be an exact case-sensitive match
  (`true` or `false`). When `VALUE` is not present then the attribute is a
  match is its value is `true`

**Examples:**

| Request PATH | Filter query | Commentary |
| --- | --- | --- |
| / | `filter=endpoints.description=cool` | Only endpoints with the word `cool` in the description |
| /endpoints | `filter=description=CooL` | Same results as previous, with a different request URL |
| / | `filter=endpoints.definitions.versions.id=1.0` | Only versions (and their owning endpoints/definitions) that have an ID of `1.0` |
| / | `filter=endpoints.format=CloudEvents/1.0,endpoints.description=cool&filter=schemaGroups.modifiedBy=John` | Only endpoints whose format is `CloudEvents/1.0` and whose description contains the word `cool`, as well as any schemaGroups that were modified by 'John' |


Specifying a filter does not imply inlining.
