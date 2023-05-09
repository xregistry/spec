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
  "docs": "URL", ?
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
      "name": "STRING",
      "epoch": UINT,
      "self": "URL",
      "description": "STRING", ?
      "docs": "URL", ?
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
          "name": "STRING",
          "epoch": UINT,
          "self": "URL",
          "versionId": "STRING",
          "description": "STRING", ?
          "docs": "URL", ?
          "tags": { "STRING": "STRING" * }, ?
          "format": "STRING", ?
          "createdBy": "STRING", ?
          "createdOn": "TIME", ?
          "modifiedBy": "STRING", ?
          "modifiedOn": "TIME", ?

          "RESOURCEUri": "URI", ?                  # if not local
          "RESOURCE": { Resource contents }, ?     # if inlined & JSON
          "RESOURCEBase64": " STRING", ?           # if inlined & ~JSON

          "versionsUrl": "URL",
          "versionsCount": INT,
          "versions": {                            # only if inlined
            "ID": {                                # the Version id
              "id": "STRING",
              "name": "STRING",
              "epoch": UINT,
              "self": "URL",
              "description": "STRING", ?
              "docs": "URL", ?
              "tags": { "STRING": "STRING" * }, ?
              "format": "STRING", ?
              "createdBy": "STRING", ?
              "createdOn": "TIME", ?
              "modifiedBy": "STRING", ?
              "modifiedOn": "TIME", ?

              "RESOURCEUri": "URI", ?              # if not local
              "RESOURCE": { Resource contens }, ?  # if inlined & JSON
              "RESOURCEBase64": " STRING" ?        # if inlined & ~JSON
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
- `DECIMAL` - Number conforming to regexp: `-?[1-9]*[0-9](\.[0-9]*[1-9])?`
- `INT` - Signed integer conforming to regexp: `-?[1-9]*[0-9]`
- `STRING` - Sequence of Unicode characters
- `TIME` - an [RFC3339](https://tools.ietf.org/html/rfc3339) timestamp
- `UINT` - Unsigned integer conforming to regexp: `[1-9]*[0-9]`
- `URI` - Absolute URI as defined in [RFC 3986 Section 4.3](https://tools.ietf.org/html/rfc3986#section-4.3)
- `URI-Reference` - URI-reference as defined in [RFC 3986 Section 4.1](https://tools.ietf.org/html/rfc3986#section-4.1)
- `URL` - URL as defined in [RFC 1738](https://datatracker.ietf.org/doc/html/rfc1738)

TODO: do we need to size the numbers? e.g. CE has 32-bit ints

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
- `"docs": "URL"`
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
  - MUST be a non-empty string consisting of visible US-ASCII octets (33-126)
  - MUST be case-insensitive unique within the scope of the entity's parent.
    In the case of the `id` for the Registry itself, the uniqueness scope will
    be based on where the Registry is used. For example, a publicly accessible
    Registry might want to consider using a UUID, while a private Registry
    does not need to be so widely unique
  - MUST be immutable
- Examples:
  - `a183e0a9-abf8-4763-99bc-e6b7fcc9544b`
  - `myEntity`

Since `id` is immutable this means that it is not possible to modify an entity
to have a new `id` value if the value needs to change (eg. a typo). Rather,
a new entity with a deep-copy of all attributes and nested entities will need
to be done, and then the old entity can be deleted.

TODO: SHOULD we restrict it to URL chars that do not need to be escaped?
      ALPHA / DIGIT / "-" / "." / "_" / "~"

#### `name`

- Type: String
- Description: A human readable name of the entity.
  Note that implementations MAY choose to enforce constraints on this value.
  For example, they could mandate that `id` and `name` be the same value.
  How any such requirement is shared with all parties is out of scope of this
  specification
- Constraints:
  - MUST be a non-empty string
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

TODO: absolute URL ok?

#### `description`

- Type: String
- Description: A human readable summary of the purpose of the entity
- Constraints:
  - When this attribute has no value, or is an empty string, it MAY be
    excluded from the serialization of the owning entity
- Examples:
  - `A queue of the sensor generated messages`

#### `docs`

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
          "versions": UINT ?           # Num Versions(>=0). Def=1, 0=unlimited
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
    TODO - include model??
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

TODO: if they remove a group/resource SHOULD it delete things from the DB?

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
  "docs": "URL", ?
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
- [`self`](#self) - REQUIRED in responses in API view, otherwise OPTIONAL
- [`description`](#description) - OPTIONAL
- [`docs`](#docs) - OPTIONAL
- [`tags`](#tags) - OPTIONAL

and the following Registry entity specific attributes:

**`specVersion`**
- Type: String
- Description: The version of this specification that the serialization
  adheres to
  TODO: "serialization" or "Registry"? Can a reg support more than one version?
- Constraints:
  - REQUIRED
  - MUST be a non-empty string
  - MUST be a read-only attribute in API view
- Examples:
  - `1.0`

**`model`**
- Type: Registry Model
- Description: A description of the Groups and Resources supported by this
  Registry. See [Registry Model](#registry-model)
- Constraints:
  - OPTIONAL based on the incoming request
  - MUST NOT be included unless requested
  - MUST be included if requested
  - MUST be a read-only attribute in API view, use the `/model` API to update

**`GROUPs` collections**
- Type: Set of [Registry Collections](#registry-collections)
- Description: A list of Registry collections that contain the set of Groups
  supported by the Registry
- Constraints:
  - REQUIRED
  - MUST be a read-only attribute in API view
  - MUST include all nested Group Collections

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
  "docs": "URL", ?
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
  "docs": "URL" ?
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
  "docs": "URL", ?
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
  "name": "STRING",
  "epoch": UINT,
  "self": "URL",
  "description": "STRING", ?
  "docs": "URL", ?
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
- [`id`](#id) - REQUIRED, except on create request in API view
- [`name`](#name) - REQUIRED
- [`epoch`](#epoch) - REQUIRED in responses in API view, otherwise OPTIONAL
- [`self`](#self) - REQUIRED in responses in API view, otherwise OPTIONAL
- [`description`](#description) - OPTIONAL
- [`docs`](#docs) - OPTIONAL
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
  - REQUIRED
  - MUST include all nested Resource Collections of the owning Group

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

TODO: count = total number of items, not just the # in this response

{
  "ID": {                                     # The Group id
    "id": "STRING",                           # A Group
    "name": "STRING",
    "epoch": UINT,
    "self": "URL",
    "description": "STRING", ?
    "docs": "URL", ?
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
- the key (`ID`) of each item in the map is the `id` of the Group

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
  "name": "STRING",
  "epoch": UINT, ?
  "description": "STRING", ?
  "docs": "URL", ?
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
  "name": "STRING",
  "epoch": UINT,
  "self": "URL",
  "description": "STRING", ?
  "docs": "URL", ?
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
  "name": "STRING",
  "epoch": UINT,
  "self": "URL",
  "description": "STRING", ?
  "docs": "URL", ?
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
  "docs": "URL", ?
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
  "name": "STRING",
  "epoch": UINT,
  "self": "URL",
  "description": "STRING", ?
  "docs": "URL", ?
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

TODO: Allow for other 2xx's on all APIs

with an empty HTTP body, or:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: ...

{
  "id": "STRING",
  "name": "STRING",
  "epoch": UINT,
  "self": "URL",
  "description": "STRING", ?
  "docs": "URL", ?
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
  deleted
- the response MAY exclude the nested Resource collections if returning them
  is too challenging

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

{
  "ID": {
    "id": "STRING",
    "name": "STRING",
    "epoch": UINT,
    "self": "URL",
    "description": "STRING", ?
    "docs": "URL", ?
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
- the key (`ID`) of each item in the map is the `id` of the Group
- the HTTP body SHOULD contain the latest representation of the Groups being
  deleted
- the response MAY exclude the nested Resource collections if returning them
  is too challenging

TODO: Do we want to support deleting all groups?

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
"latest" Version of the Resource. Meaning, it "points" to a specific entity
in the Resource's `versions` collection, and as such, many of the attributes
shown when retrieving the Resource will come from that Version. However,
there are a few exceptions:
- `id` MUST be for the Resource itself and not the `id` from the "latest"
  Version. The `id` of each Version MUST be unique within the scope of the
  Resource, but to ensure the Resource itself has a consistent `id` value
  it is distinct from any Version's `id`. There MUST be a `versionId` attribute
  in the serialization of a Resource that can be used to determine which
  Version is the latest Version (meaning, which Version this Resource is an
  alias for)

  Additionally, Resource `id` values are often human readable (eg. `mySchema`),
  while Version `id` values are meant to be versions string values
  (e.g. `1.0`).
- `self` MUST be an absolute URL to the Resource, and not to a specific
  Version in the `versions` collection

Additionally, when serialized in an HTTP response the Resource MUST include a
`Content-Location` HTTP header that MUST contain a URL to the latest Version
in `versions` collection of the Resource.

Unlike Groups, Resources are typically defined by domain-specific data
and as such the Registry defined attributes are not present in the Resources
themselves. This means the Registry metadata needs to be managed separately
from the contents of the Resource.
In the case of creating and updating Resources, the Registry Resource metadata
(including extensions) MUST be exposed as HTTP headers with a `xRegistry-`
prefix - as long as they are not too large to be serialized as HTTP headers.
However, there is another option where the Registry metadata is available as a
JSON object in the HTTP body - see [Retrieving a Resource's
Metadata](#retrieving-a-resources-metadata). This second option is useful when
the values of certain attributes are too large to be sent as HTTP headers.

When serialized as a JSON object, a Resource adheres to this form:

``` text
{
  "id": "STRING",
  "name": "STRING",
  "epoch": UINT,
  "self": "URL",
  "versionId": "STRING",
  "description": "STRING", ?
  "docs": "URL", ?
  "tags": { "STRING": "STRING" * }, ?
  "format": "STRING", ?
  "createdBy": "STRING", ?
  "createdOn": "TIME", ?
  "modifiedBy": "STRING", ?
  "modifiedOn": "TIME", ?

  "RESOURCEUri": "URI", ?                  # if not local
  "RESOURCE": { Resource contents }, ?     # if inlined & JSON
  "RESOURCEBase64": " STRING", ?           # if inlined & ~JSON

  "versionsUrl": "URL",
  "versionsCount": INT,
  "versions": { Versions collection } ?    # if inlined
}
```

Resources include the following common attributes:
- [`id`](#id) - REQUIRED, except on create request in API view
- [`name`](#name) - REQUIRED
- [`epoch`](#epoch) - REQUIRED in responses in API view, otherwise OPTIONAL
- [`self`](#self) - REQUIRED in responses in API view, otherwise OPTIONAL
- [`description`](#description) - OPTIONAL
- [`docs`](#docs) - OPTIONAL
- [`tags`](#tags) - OPTIONAL
- [`format`](#format) - OPTIONAL
- [`createdBy`](#createdby) - OPTIONAL
- [`createdOn`](#createdon) - OPTIONAL
- [`modifiedBy`](#modifiedby) - OPTIONAL
- [`modifiedOn`](#modifiedon) - OPTIONAL

TODO: how is "latest" determined?
TODO: does "self" point to the Resource or to the specific Version? Resource
TODO: SHOULD `versionId` be `latestId` ?
TODO: is it ok that a Resource's ID == a Version ID?

and the following Resource specific attributes:

**`versionId`**
- Type: String
- Description: the `id` of the latest Version of the Resource.
  This specification makes no statement as to the format of this string or
  versioning scheme used by implementations of this specification. However, it
  is assumed that newer Versions of a Resource will have a "higher"
  `id` value than older Versions. Also see [`epoch`](#epoch)
- Constraints:
  - REQUIRED
  - MUST be a non-empty string
  - MUST be unique across all Versions of the Resource
  - MUST be the `id` of the latest Version of the Resource
  - MUST be a read-only attribute in API view except on the creation of a
    Resource API call
- Examples:
  - `1`, `2.0`, `v3-rc1`

**`RESOURCEUri`**
- Type: URI-Reference
- Description: if the content of the Resource are stored outside of the
  current Registry then this attribute MUST contain a URI-Reference to the
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
  - REQUIRED
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
    "name": "STRING",
    "epoch": UINT,
    "self": "URL",
    "versionId": "STRING",
    "description": "STRING", ?
    "docs": "URL", ?
    "tags": { "STRING": "STRING" * }, ?
    "format": "STRING", ?
    "createdBy": "STRING", ?
    "createdOn": "TIME", ?
    "modifiedBy": "STRING", ?
    "modifiedOn": "TIME", ?

    "RESOURCEUri": "URI", ?                  # if not local
    "RESOURCE": { Resource contents }, ?     # if inlined & JSON
    "RESOURCEBase64": " STRING", ?           # if inlined & ~JSON

    "versionsUrl": "URL",
    "versionsCount": INT,
    "versions": { Versions collection } ?    # if inlined
  } *
}
```

Where:
- the key (`ID`) of each item in the map is the `id` of the Resource

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
    "versionId": "1.0",
    "format": "CloudEvents/1.0",

    "versionsUrl": "https://example.com/endpoints/123/definitions/456/versions",
    "versionsCount": 1
  }
}
```

TODO: do we need a URL to the latest to make it easier to retrieve?

##### Creating Resources

To create a new Resource, an HTTP `POST` MAY be used.

TODO: Add POST .../RESOURCEs?meta ??

The request MUST be of the form:

``` text
POST /GROUPs/gID/RESOURCEs
Content-Type: ...
Content-Length: ...
xRegistry-id: STRING ?
xRegistry-name: STRING
xRegistry-epoch: STRING ?
xRegistry-versionId: STRING ?
xRegistry-description: STRING ?
xRegistry-docs: STRING ?
xRegistry-tags: STRING (JSON map) ?
xRegistry-format: STRING ?
xRegistry-RESOURCEUri: URI ?

...Resource contents... ?
```

Where:
- `id` is OPTIONAL and if absent the server MUST assign it a new unique value
- whether `id` is provided or generated by the server, it MUST be unique
  across all Resources of this type for this Group
- `epoch` is OPTIONAL and if present MUST be silently ignored
- `versionId` is OPTIONAL and if present it MUST be used as the resulting
  Version `id` value. If absent the server MUST assign it a new unique value.
  Note, normally `versionId` is read-only, but in this case it is not
- if `RESOURCEUri` is present the HTTP body MUST be empty
- the HTTP body MUST contain the contents of the new Resource if the
  `RESOURCEUri` HTTP header is absent. Note, the body MAY be empty
  even if the HTTP header is not present, indicating that the Resource is
  empty
- a request that is missing a mandatory attribute MUST generate an error.
  If a manadatory attribute is too large for an HTTP header value then
  this operation MUST be done via a POST to the `?meta` API

Notice the Resource attributes (metadata) are passed as HTTP headers, not
in the HTTP body. Also, as a reminder, HTTP headers are case insensitive.

If any of the HTTP header values are too large then a subsequent HTTP `PUT`
to the Resource's `?meta` API SHOULD be used to set those attributes.
See [Retrieving a Resource's Metadata](#retrieving-a-resources-metadata).

This operation MUST result in one Version of the new Resource being created.

A successful response MUST include the same content than an HTTP `GET` on the
Resource would return, and be of the form:

``` text
HTTP/1.1 201 Created
Content-Type: ...
Content-Length: ...
xRegistry-id: STRING
xRegistry-name: STRING
xRegistry-epoch: UINT
xRegistry-self: URL
xRegistry-versionId: STRING
xRegistry-description: STRING ?
xRegistry-docs: STRING ?
xRegistry-tags: STRING (JSON map) ?
xRegistry-format: STRING ?
xRegistry-createdBy: STRING ?
xRegistry-createdOn: TIME ?
xRegistry-modifiedBy: STRING ?
xRegistry-modifiedOn: TIME ?
xRegistry-versionsUrl: URL
xRegistry-versionsCount: INT
xRegistry-RESOURCEUri: URI ?
Location: URL
Content-Location: URL

...Resource contents... ?
```

TODO: Check Content-Location
TODO: Self points to Resource, not version - yes? Check all "Where"s below

Where:
- `Location` MUST be a URL to the Resource - same as `self`
- `Content-Location` MUST be a URL to the Version of the Resource in the
  `versions` collection
- if `RESOURCEUri` is present then the HTTP body MUST be empty
- if the HTTP body is not empty then `RESOURCEUri` MUST NOT be present

Any Resource attribute that is too large for an HTTP header MUST be excluded
and the client MAY use the `?meta` API for the Resource to retrieve the full
set of Resource attributes.
See [Retrieving a Resource's Metadata](#retrieving-a-resources-metadata).

TODO: do we need some kind of indicator for missing headers?

**Examples:**

Request:

``` text
POST /endpoints/123/definitions
Content-Type: application/json; charset=utf-8
Content-Length: ...
xRegistry-name: Blob Created
xRegistry-format: CloudEvents/1.0
xRegistry-versionId: 1.0

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
xRegistry-versionId: 1.0
xRegistry-format: CloudEvents/1.0
xRegistry-versionsUrl: https://example.com/endpoints/123/definitions/456/versions
xRegistry-versionsCount: 1
Location: https://example.com/endpoints/123/definitions/456
Content-Location: https://example.com/endpoints/123/definitions/456/versions/1.0

{
  # definition of a "Blob Created" event excluded for brevity
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
Registry, or an HTTP redirect to the `RESOURCEUri` value stored external
to the Registry, if one is set.

In the case of returning the Resource, the response MUST be of the form:

``` text
HTTP/1.1 200 OK
Content-Type: ...
Content-Length: ...
xRegistry-id: STRING
xRegistry-name: STRING
xRegistry-epoch: UINT
xRegistry-self: URL
xRegistry-versionId: STRING
xRegistry-description: STRING ?
xRegistry-docs: STRING ?
xRegistry-tags: STRING (JSON map) ?
xRegistry-format: STRING ?
xRegistry-createdBy: STRING ?
xRegistry-createdOn: TIME ?
xRegistry-modifiedBy: STRING ?
xRegistry-modifiedOn: TIME ?
xRegistry-versionsUrl: URL
xRegistry-versionsCount: INT
Content-Location: URL

...Resource contents...
```

Where:
- `id` is the ID of the Resource, not of the latest Version of the Resource
- `self` is a URL to the Resource, not to the latest Version of the Resource
- `Content-Location` MUST be a URL to the latest Version of this Resource
  in the `versions` collection

In the case of a redirect, the response MUST be of the form:

``` text
HTTP/1.1 307 Temporary Redirect
xRegistry-id: STRING
xRegistry-name: STRING
xRegistry-epoch: UINT
xRegistry-self: URL
xRegistry-versionId: STRING
xRegistry-description: STRING ?
xRegistry-docs: STRING ?
xRegistry-tags: STRING (JSON map) ?
xRegistry-format: STRING ?
xRegistry-createdBy: STRING ?
xRegistry-createdOn: TIME ?
xRegistry-modifiedBy: STRING ?
xRegistry-modifiedOn: TIME ?
xRegistry-versionsUrl: URL
xRegistry-versionsCount: INT
xRegistry-RESOURCEUri: URI
Content-Location: URL
Location: URL
```

Where:
- `id` is the ID of the Resource, not of the latest Version of the Resource
- `self` is a URL to the Resource, not to the latest Version of the Resource
- `Content-Location` MUST be a URL to the latest Version of this Resource
  in the `versions` collection
- `Location` and `RESOURCEUri` MUST have the same value

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
xRegistry-versionId: 1.0
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
Content-Location: URL

{
  "id": "STRING",
  "name": "STRING",
  "epoch": UINT,
  "self": "URL",
  "versionId": "STRING",
  "description": "STRING", ?
  "docs": "URL", ?
  "tags": { "STRING": "STRING" * }, ?
  "format": "STRING", ?
  "createdBy": "STRING", ?
  "createdOn": "TIME", ?
  "modifiedBy": "STRING", ?
  "modifiedOn": "TIME", ?

  "RESOURCEUri": "URI", ?                  # if not local
  "RESOURCE": { Resource contents }, ?     # if inlined & JSON
  "RESOURCEBase64": " STRING", ?           # if inlined & ~JSON

  "versionsUrl": "URL",
  "versionsCount": INT,
  "versions": { Versions collection } ?    # if inlined
}
```

TODO: do we need a property with the URL to the latest Version?

Where:
- `id` MUST be the Resource's `id` and not the `id` of the latest Version
- `self` is a URL to the Resource, not to the latest Version of the Resource
- `RESOURCE`, or `RESOURCEBase64`, depending on the type of the Resource's
  content, MUST only be included if requested via the `inline` query parameter
  and `RESOURCEUri` is not set
- `Content-Location` MUST be a URL to the latest Version of this Resource
  in the `versions` collection

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
  "self": "https://example.com/endpoints/123/definitions/456",
  "versionId": "1.0",
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
xRegistry-docs: STRING ?
xRegistry-tags: STRING (JSON map) ?
xRegistry-format: STRING ?
xRegistry-RESOURCEUri: URI ?

...Resource contents... ?
```

Where:
- if `id` is present then it MUST match the `rID` in the PATH
- if an `epoch` value is specified then the server MUST check to ensure that
  the value matches the current `epoch` value and if it differs then an error
  MUST be generated
- if `RESOURCEUri` is present then the body MUST be empty and any
  local Resource contents MUST be erased
- if `format` is present and changing it would result in Versions of this
  Resource becoming invalid with respect to their own `format` values, then
  an error MUST be generated
- if the body is empty and `RESOURCEUri` is absent then the Resource's
  contents MUST be erased
- a request to update a read-only attribute MUST be silently ignored
- a request to update a mutable attribute with an invalid value MUST generate
  an error
- complex attributes that have nested values (eg. `tags`) MUST be specified
  in their entirety
- a request that is missing a mandatory attribute MUST generate an error.
  If a manadatory attribute is too large for an HTTP header value then
  this operation MUST be done via a PUT to the `?meta` API

Missing Registry HTTP headers MUST NOT be interpreted as a request to delete
the attribute as it is impossible to know if it is missing due to a desire to
delete it or if the value is too large to be serialized as an HTTP header.
In this respect, processing of the HTTP headers is similar to how an HTTP
`PATCH` behaves - meaning, only the attributes wishing to be updated are
included in the request.

Note: `versionId` is a read-only attribute in this context and therefore
if present MUST be silently ignored.

To delete an attribute a `PUT` to the `?meta` API of the Resource SHOULD
be used.

TODO: SHOULD we support some kind of "null" value to allow delete?

Upon successful processing, the Version's `epoch` value MUST be incremented -
see [epoch](#epoch).

A successful response MUST include the same content than an HTTP `GET` on the
Resource would return, and be of the form:

``` text
HTTP/1.1 200 OK
Content-Type: ...
Content-Length: ...
xRegistry-id: STRING
xRegistry-name: STRING
xRegistry-epoch: UINT
xRegistry-self: URL
xRegistry-versionId: STRING
xRegistry-description: STRING ?
xRegistry-docs: STRING ?
xRegistry-tags: STRING (JSON map) ?
xRegistry-format: STRING ?
xRegistry-createdBy: STRING ?
xRegistry-createdOn: TIME ?
xRegistry-modifiedBy: STRING ?
xRegistry-modifiedOn: TIME ?
xRegistry-versionsUrl: URL
xRegistry-versionsCount: INT
xRegistry-RESOURCEUri: URI ?
Content-Location: URL

...Resource contents... ?
```

Where:
- `id` MUST be the Resource's `id` and not the `id` of the latest Version
- `self` is a URL to the Resource, not to the latest Version of the Resource
- `Content-Location` MUST be a URL to the latest Version of this Resource
  in the `versions` collection

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
xRegistry-versionId: 1.0
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

TODO: Do we want to support ?epoch too?  I'm leaning towards "no"

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
  "docs": "URL", ?
  "tags": { "STRING": "STRING" * }, ?
  "format": "STRING", ?

  "RESOURCEUri": "URI", ?
  "RESOURCE": { Resource contents }, ?
  "RESOURCEBase64": " STRING" ?
}
```

Where:
- if `id` is present then it MUST match the `rID` in the PATH
- if an `epoch` value is specified then the server MUST check to ensure that
  the value matches the current `epoch` value and if it differs then an error
  MUST be generated
- since `RESOURCE` and `RESOURCEBase64` are special attributes that will
  only appear in the Resource's serialization when requested, this update
  operation MUST interpret their absence from the request (when `RESOURCEUri`
  is also not present) as a request to leave the Resource contents unchanged.
  However, if any of those 3 attributes are in the request then it MUST
  be interpreted as a request to update the contents of the Resource
  appropriately. A value of `null` for any of them MUST be interpreted
  as a request to delete the contents. If none of those 3 attributes are in
  the request, but the `RESOURCEUri` attribute is set on the server then it
  MUST be interpreted as a request to delete the attribute
- at most, only one of `RESOURCEUri`, `RESOURCE` or `RESOURCEBase64` MAY
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
- a request that is missing a mandatory attribute MUST generate an error

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
  "name": "STRING",
  "epoch": UINT,
  "self": "URL",
  "versionId": "STRING",
  "description": "STRING", ?
  "docs": "URL", ?
  "tags": { "STRING": "STRING" * }, ?
  "format": "STRING", ?
  "createdBy": "STRING", ?
  "createdOn": "TIME", ?
  "modifiedBy": "STRING", ?
  "modifiedOn": "TIME", ?

  "RESOURCEUri": "URI", ?                  # if not local

  "versionsUrl": "URL",
  "versionsCount": INT,
  "versions": { Versions collection } ?
}
```

TODO: SHOULD PUT support ?inline in the PATH to control whether the
response has inlined stuff or not?

**Examples:**
Request:

``` text
PUT /endpoints/123/definitions/456?meta

{
  "id": "456",
  "name": "Blob Created",
  "epoch": 2,
  "self": "https://example.com/endpoints/123/definitions/456",
  "versionId": "1.0",
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
  "self": "https://example.com/endpoints/123/definitions/456",
  "versionId": "1.0",
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
xRegistry-name: STRING
xRegistry-epoch: UINT
xRegistry-self: URL
xRegistry-versionId: STRING ?
xRegistry-description: STRING ?
xRegistry-docs: STRING ?
xRegistry-tags: STRING (JSON map) ?
xRegistry-format: STRING ?
xRegistry-createdBy: STRING ?
xRegistry-createdOn: TIME ?
xRegistry-modifiedBy: STRING ?
xRegistry-modifiedOn: TIME ?
xRegistry-RESOURCEUri: URI ?

...Resource contents... ?
```

Where:
- the HTTP body SHOULD contain the latest representation of the Resource being
  deleted
- the response MAY exclude the nested Versons collection if returning it
  is too challenging

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
- the request body contains the list of Resource IDs to be deleted
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
    "name": "STRING",
    "epoch": UINT,
    "self": "URL",
    "versionId": "STRING", ?
    "description": "STRING", ?
    "docs": "URL", ?
    "tags": { "STRING": "STRING" * }, ?
    "format": "STRING", ?
    "createdBy": "STRING", ?
    "createdOn": "TIME", ?
    "modifiedBy": "STRING", ?
    "modifiedOn": "TIME", ?

    "RESOURCEUri": "URI", ?
  } *
}
```

Where:
- the HTTP body SHOULD contain the latest representation of the Resources being
  deleted
- the response MAY exclude the nested Versons collection if returning it
  is too challenging

A `DELETE /GROUPs/gID/RESOURCEs` without a body MUST delete all Resources in the
Group.

TODO: yes?? ^

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
  "name": "STRING",
  "epoch": UINT,
  "self": "URL",
  "description": "STRING", ?
  "docs": "URL", ?
  "tags": { "STRING": "STRING" * }, ?
  "format": "STRING", ?
  "createdBy": "STRING", ?
  "createdOn": "TIME", ?
  "modifiedBy": "STRING", ?
  "modifiedOn": "TIME", ?

  "RESOURCEUri": "URI", ?                  # if not local
  "RESOURCE": { Resource contents }, ?     # if inlined & JSON
  "RESOURCEBase64": " STRING" ?            # if inlined & ~JSON
}
```

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
    "name": "STRING",
    "epoch": UINT,
    "self": "URL",
    "description": "STRING", ?
    "docs": "URL", ?
    "tags": { "STRING": "STRING" * }, ?
    "format": "STRING", ?
    "createdBy": "STRING", ?
    "createdOn": "TIME", ?
    "modifiedBy": "STRING", ?
    "modifiedOn": "TIME", ?

    "RESOURCEUri": "URI", ?                  # if not local
    "RESOURCE": { Resource contents }, ?     # if inlined & JSON
    "RESOURCEBase64": " STRING" ?            # if inlined & ~JSON
  } *
}
```

Where:
- the key (`ID`) of each item in the map is the `id` of the Version

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
    "format": "CloudEvents/1.0"
  }
}
```

##### Creating a new Version of a Resource

To create a new Version of a Resource, an HTTP `POST` MAY be used.

Note that the new Version will not inherit any values from any existing
Version, so the new Version will need to be fully specified as part of the
request.

TODO: add POST ?meta

The request MUST be of the form:

``` text
POST /GROUPs/gID/RESOURCEs/rID/versions
Content-Type: ...
Content-Length: ...
xRegistry-id: STRING ?
xRegistry-name: STRING
xRegistry-epoch: STRING ?
xRegistry-description: STRING ?
xRegistry-docs: STRING ?
xRegistry-tags: STRING (JSON map) ?
xRegistry-format: STRING ?
xRegistry-RESOURCEUri: URI ?      # If present body MUST be empty

...Resource contents... ?         # If present RESOURCEUri MUST be absent
```

Where:
- if `id` is present then it MUST be unique across all Versions within this
  Resource. If absent then the server MUST generate a new unique value
- `epoch` is OPTIONAL and if present MUST be silently ignored
- if `RESOURCEUri` is present the HTTP body MUST be empty
- the HTTP body MUST contain the contents of the new Version if the
  `RESOURCEUri` HTTP header is absent. Note, the body MAY be empty even if
  the HTTP header is not present, indicating that the Version is empty
- a request that is missing a mandatory attribute MUST generate an error.
  If a manadatory attribute is too large for an HTTP header value then
  this operation MUST be done via a POST to the `?meta` API

Notice the Version attributes (metadata) are passed as HTTP headers, not
in the HTTP body. Also, as a reminder HTTP headers are case insensitive.

If any of the HTTP header values are too large then a subsequent HTTP `PUT`
to the Version's `?meta` API SHOULD be used to set those attributes.
See [Retrieving a Version's Metadata](#retrieving-a-versions-metadata).

A successful response MUST include the same content than an HTTP `GET` on the
Resource would return, and be of the form:

``` text
HTTP/1.1 201 Created
Content-Type: ...
Content-Length: ...
xRegistry-id: STRING
xRegistry-name: STRING
xRegistry-epoch: UINT
xRegistry-self: STRING
xRegistry-description: STRING ?
xRegistry-docs: STRING ?
xRegistry-tags: STRING ?
xRegistry-format: STRING ?
xRegistry-createdBy: STRING ?
xRegistry-createdOn: TIME ?
xRegistry-modifiedBy: STRING ?
xRegistry-modifiedOn: TIME ?
xRegistry-RESOURCEUri: URI ?
Location: URL

...Resource contents... ?
```

Where:
- `Location` MUST be a URL to the Version - same as `self`
- if `RESOURCEUri` is present then the HTTP body MUST be empty
- if the HTTP body is not empty then `RESOURCEUri` MUST NOT be present

Any Version attribute that is too large for an HTTP header MUST be excluded
and the client MAY use the `?meta` API for the Version to retrieve the full
set of Version attributes.
See [Retrieving a Version's Metadata](#retrieving-a-versions-metadata).

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
xRegistry-format: CloudEvents/1.0
Location: https://example.com/endpoints/123/definitions/456/versions/v2.0

{
  # definition of a "Blob Created" event excluded for brevity
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
the `RESOURCEUri` value when defined.

In the case of returning the Resource, the response MUST be of the form:

``` text
HTTP/1.1 200 OK
Content-Type: ...
Content-Length: ...
xRegistry-id: STRING
xRegistry-name: STRING
xRegistry-epoch: UINT
xRegistry-self: URL
xRegistry-description: STRING ?
xRegistry-docs: STRING ?
xRegistry-tags: STRING (JSON map) ?
xRegistry-format: STRING ?
xRegistry-createdBy: STRING ?
xRegistry-createdOn: TIME ?
xRegistry-modifiedBy: STRING ?
xRegistry-modifiedOn: TIME ?

...Resource contents...
```

Where:
- `id` is the ID of the Version, not of the owning Resource

In the case of a redirect, the response MUST be of the form:

``` text
HTTP/1.1 307 Temporary Redirect
xRegistry-id: STRING
xRegistry-name: STRING
xRegistry-epoch: UINT
xRegistry-self: URL
xRegistry-description: STRING ?
xRegistry-docs: STRING ?
xRegistry-tags: STRING (JSON map) ?
xRegistry-format: STRING ?
xRegistry-createdBy: STRING ?
xRegistry-createdOn: TIME ?
xRegistry-modifiedBy: STRING ?
xRegistry-modifiedOn: TIME ?
xRegistry-RESOURCEUri: URI
Location: URL
```

Where:
- `id` is the ID of the Version, not of the owning Resource
- `Location` and `RESOURCEUri` MUST have the same value

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
  "name": "STRING",
  "epoch": UINT,
  "self": "URL",
  "description": "STRING", ?
  "docs": "URL", ?
  "tags": { "STRING": "STRING" * }, ?
  "format": "STRING", ?
  "createdBy": "STRING", ?
  "createdOn": "TIME", ?
  "modifiedBy": "STRING", ?
  "modifiedOn": "TIME", ?

  "RESOURCEUri": "URI", ?                  # if not local
  "RESOURCE": { Resource contents }, ?     # if inlined & JSON
  "RESOURCEBase64": " STRING" ?            # if inlined & ~JSON
}
```

Where:
- `id` MUST be the Version's `id` and not the `id` of the owning Resource

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
xRegistry-description: STRING ?
xRegistry-docs: STRING ?
xRegistry-tags: STRING (JSON map) ?
xRegistry-format: STRING ?
xRegistry-RESOURCEUri: URI ?

...Resource contents... ?
```

Where:
- if `id` is present then it MUST match the `vID` in the PATH
- if an `epoch` value is specified then the server MUST check to ensure that
  the value matches the current `epoch` value and if it differs then an error
  MUST be generated
- if `RESOURCEUri` is present then the body MUST be empty and any
  local Version contents MUST be erased
- if `format` is present and changing it would result in the Version
  becoming invalid with respect to the `format` of the owning Resource, then
  an error MUST be generated
- if the body is empty and `RESOURCEUri` is absent then the Version's
  contents MUST be erased
- a request to update a read-only attribute MUST be silently ignored
- a request to update a mutable attribute with an invalid value MUST generate
  an error
- complex attributes that have nested values (eg. `tags`) MUST be specified
  in their entirety
- a request that is missing a mandatory attribute MUST generate an error.
  If a manadatory attribute is too large for an HTTP header value then
  this operation MUST be done via a PUT to the `?meta` API

Missing Registry HTTP headers MUST NOT be interpreted as deleting the
attribute as it is impossible to know if it is missing due to a desire to
delete it or if the value is too large to be serialized as an HTTP header.
In this respect, processing of the HTTP headers is similar to how an HTTP
`PATCH` behaves - meaning, only the attributes wishing to be updated are
included in the request.

To delete an attribute a `PUT` to the `?meta` API of the Version SHOULD
be used.

TODO: SHOULD we support some kind of "null" value to allow delete?

A successful response MUST include the same content than an HTTP `GET` on the
Version would return, and be of the form:

``` text
HTTP/1.1 200 OK
Content-Type: ...
Content-Length: ...
xRegistry-id: STRING
xRegistry-name: STRING
xRegistry-epoch: UINT
xRegistry-self: URL
xRegistry-description: STRING ?
xRegistry-docs: STRING ?
xRegistry-tags: STRING (JSON map) ?
xRegistry-format: STRING ?
xRegistry-createdBy: STRING ?
xRegistry-createdOn: TIME ?
xRegistry-modifiedBy: STRING ?
xRegistry-modifiedOn: TIME ?
xRegistry-RESOURCEUri: URI ?

...Resource contents... ?
```

Where:
- `id` MUST be the Version's `id` and not the `id` of the owning Resource
- `self` is a URL to the Version, not to the owning Resource

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
xRegistry-format: CloudEvents/1.0

{
  # updated definition of a "Blob Created" event excluded for brevity
}
```

Notice in this case aside from an updated "Blob Created" event (in the HTTP
body) we've included the `epoch` value in the request. If the current value
does not match `2` then an error would have been generated.

TODO: Do we want to support ?epoch too?  I'm leaning towards "no"


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
  "description": "STRING", ?
  "docs": "URL", ?
  "tags": { "STRING": "STRING" * }, ?
  "format": "STRING", ?

  "RESOURCEUri": "URI", ?
  "RESOURCE": { Resource contents }, ?
  "RESOURCEBase64": " STRING" ?
}
```

Where:
- if `id` is present then it MUST match the `vID` in the PATH
- if an `epoch` value is specified then the server MUST check to ensure that
  the value matches the current `epoch` value and if it differs then an error
  MUST be generated
- since `RESOURCE` and `RESOURCEBase64` are special attributes that will
  only appear in the Resource's serialization when requested, this update
  operation MUST interpret their absence from the request (when `RESOURCEUri`
  is also not present) as a request to leave the Resource contents unchanged.
  However, if any of those 3 attributes are in the request then it MUST
  be interpreted as a request to update the contents of the Resource
  appropriately. A value of `null` for any of them MUST be interpreted
  as a request to delete the contents. If none of those 3 attributes are in
  the request, but the `RESOURCEUri` attribute is set on the server then it
  MUST be interpreted as a request to delete the attribute
- at most, only one of `RESOURCEUri`, `RESOURCE` or `RESOURCEBase64` MAY
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
- a request that is missing a mandatory attribute MUST generate an error

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
  "name": "STRING",
  "epoch": UINT,
  "self": "URL",
  "description": "STRING", ?
  "docs": "URL", ?
  "tags": { "STRING": "STRING" * }, ?
  "format": "STRING", ?
  "createdBy": "STRING", ?
  "createdOn": "TIME", ?
  "modifiedBy": "STRING", ?
  "modifiedOn": "TIME", ?

  "RESOURCEUri": "URI", ?                  # if not local
}
```

TODO: SHOULD PUT support ?inline in the PATH to control whether the
response has inlined stuff or not?

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
  "description": "An updated description",
  "format": "CloudEvents/1.0"
}
```

##### Deleting Versions of a Resource
To delete a single Version of a Resource, an HTTP `DELETE` MAY be used.

The request MUST be of the form:

``` text
DELETE /GROUPs/gID/RESOURCEs/rID/versions/vID[?epoch=EPOCH]
```

Where:
- the request body SHOULD be empty

The following query parameters MUST be supported by servers:
- `epoch`<br>
  The presence of this query parameter indicates that the server MUST check
  to ensure that the `EPOCH` value matches the Resource's current `epoch` value
  and if it differs then an error MUST be generated

If a Resource only has one Version, an attempt to delete it MUST generate an
error.

If the latest Version is deleted then the remaining Version with the largest
`versionId` value MUST become the latest.

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
xRegistry-name: STRING
xRegistry-epoch: UINT
xRegistry-self: URL
xRegistry-description: STRING ?
xRegistry-docs: STRING ?
xRegistry-tags: STRING (JSON map) ?
xRegistry-format: STRING ?
xRegistry-createdBy: STRING ?
xRegistry-createdOn: TIME ?
xRegistry-modifiedBy: STRING ?
xRegistry-modifiedOn: TIME ?
xRegistry-RESOURCEUri: URI ?

...Resource contents... ?
```

Where:
- the HTTP body SHOULD contain the latest representation of the Version being
  deleted

If the latest Version is deleted then the remaining Version with the largest
`versionId` value MUST become the latest.

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
DELETE /GROUPs/gID/RESOURCEs/rID/versions

[
  {
    "id": "STRING",
    "epoch": UINT ?     # If present it MUST match current value
  } +
]
```

Where:
- the request body contains the list of Version IDs to be deleted
- if an `epoch` value is specified for a Version then the server MUST check
  to ensure that the value matches the Version's current `epoch` value and if
  it differs then an error MUST be generated
- the HTTP body MUST contain at least one Version ID

An attempt to delete all Versions MUST generate an error.

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
    "name": "STRING",
    "epoch": UINT,
    "self": "URL",
    "description": "STRING", ?
    "docs": "URL", ?
    "tags": { "STRING": "STRING" * }, ?
    "format": "STRING", ?
    "createdBy": "STRING", ?
    "createdOn": "TIME", ?
    "modifiedBy": "STRING", ?
    "modifiedOn": "TIME", ?

    "RESOURCEUri": "URI", ?
  } +
}
```

Where:
- the HTTP body SHOULD contain the latest representation of the Versions being
  deleted

If the latest Version is deleted then the remaining Version with the largest
`versionId` value MUST become the latest.

TODO: examples

### Inlining

The `inline` query parameter on a request indicates that the response
MUST include the contents of all specified inlinable attributes. Inlinable
attributes include:
- all [Registry Collection](#registry-collections) types - eg. `GROUPs`,
  `RESOURCEs` and `versions`
- the `RESOURCE` attribute in a Resource

While the `RESOURCE` ands `RESOURCEBase64` attributes are two separate
attributes, since the usage of each will be based on the content type of
the Resource, specifying `RESOURCE` in the `inline` query parameter MUST
be interpreted as a request for the appropriate attribute.

TODO: reword? ^^

Some examples:
- `GET /?inline=endpoints`
- `GET /?inline=endpoints.definitions`
- `GET /endpoints/123/?inline=definitions.definition`
- `GET /endpoints/123/definitions/456?inline=definition`

This is useful for cases where the contents of the Registry are to be
represented as a single (self-contained) document.

The format of the `inline` query parameter is:

``` text
inline[=PATH[,...]]
```

Where `PATH` is a string indicating which inlinable attributes to include in
include in the response. References to nested attributes are
represented using a dot(`.`) notation - for example `GROUPs.RESOURCEs`.

There MAY be multiple `PATH`s specified, either as comma separated values on
a single `inline` query parameter or via multiple `inline` query parameters.
 Absence of a value, or a value of an empty string, indicates that all nested
inlinable attributes MUST be inlined.

The specific value of `PATH` will vary based on where the request is directed.
For example, a request to the root of the Registry MUST start with a `GROUPs`
name, while a request directed at a Group would start with a `RESOURCEs` name.

For example:

Given a Registry with a model that has "endpoints" as a Group and "definitions"
as a Resource within "endpoints":

| HTTP `GET` Path | Example ?inline=PATH values |
| --- | --- |
| / | ?inline=endpoints |
| / | ?inline=endpoints.definitions.versions |
| /endpoints | ?inline=definitions |
| /endpoints/123 | ?inline=definitions.versions |
| /endpoints/123 | ?inline=definitions.definition |
| /endpoints/123 | ?inline=endpoints # Invalid, already in 'endpoints' |

Note that asking for an attribute to be inlined will implicitly cause all of
its parents to be inlined as well.

When specifying a collection to be inlined, it MUST be specified using the
plural name for the collection in its defined case.

A request to inline an unknown, or non-inlinable, attribute MUST NOT return
an error and MUST continue as if that inline PATH was not specified.

TODO: yes? ^^

Note: If the Registry can not return all expected data in one response then it
MUST generate an error. In those cases, the client will need to query the
individual inlinable attributes in isolation so the Registry can leverage
pagination of the response.

TODO: define the error
TODO: add pagination

### Filtering

The `filter` query parameter on a request indicates that the response
MUST include only those entities that match the specified filter criteria.
This means that any Registry Collection's attributes MUST be modified
to match the resulting subset. In particular:
- the `Url` attribute MUST include the filter expression(s) in its query
  parameters
- the `Count` attribute MUST only count the entities that match the
  filter expression(s)
- the inlined collection itself MUST only include entities that match the
  filter expression(s)

The format of the `filter` query parameter is:

``` text
filter=EXPRESSION[,EXPRESSION]
```

Where:
- each `EXPRESSION` within the scope of one `filter` query parameter MUST be
  interpreted as an `AND` and any matching entities MUST satisfy all
  of the specified expressions within that `filter` query parameter
- the `filter` query parameter can appear multiple times and is so each MUST
  be interpreted as an `OR` and the response MUST include all entities that
  match any of the specified filter query parameters

The abstract processing logic would be:
- for each `filter` query parameter, find all entities that satisfy all
  expressions for that `filter`
- after processing all `filter` query parameters, combine all entities found
  into one result - removing any duplicates

The format of the `EXPRESSION` is:

``` text
[PATH.]ATTRIBUTE[=VALUE]
```

Where:
- `PATH` is a dot(`.`) notation traversal of the Registry to the entity
  of interest, or absent if at the root of the Registry
- `ATTRIBUTE` is the attribute of the entity to be examined
- `VALUE` is the desired value of the attribute being examined. Only entities
  whose specified `ATTRIBUTE` with this `VALUE` MUST be included in the
  response. See below for more information

When comparing an `ATTRIBUTE` to the specified `VALUE` the following rules
MUST apply for an entity to be considered a match of the filter expression:
- for numeric attributes, it MUST be an exact match (eg. 1 and 1.0 are not
  considered to be a match). When `VALUE` is not present then the attribute
  matches if its value is non-zero
- for string attributes, its value MUST contain the `VALUE` within it but
  does not need to be an exact case match. When `VALUE` is not present then
  the attribute matches if its value is a non-empty string
- for boolean attributes, its value MUST be an exact match (`true` or
  `false`). When `VALUE` is not present then it attribute is matches is its
  value is `true`

**Examples:**


| Filter query | Commentary |
| --- | --- |
| `filter=endpoints.description=cool` | Only endpoints with the word 'cool' in the description |
| `filter=endpoints.definitions.versions.id=1.0` | Only versions (and their owning endpoints/definitions) that have an ID of '1.0' |
| `filter=endpoints.format=CloudEvents/1.0,endpoints.description=cool&filter=schemaGroups.modifiedBy=John` | Only endpoints whose format is 'CloudEvents/1.0' and whose description contains the word 'cool', as well as any schemaGroups that were modified by 'John' |
