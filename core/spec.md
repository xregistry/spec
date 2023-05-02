# Registry Service - Version 0.5-wip

## Abstract

A Registry Service exposes resources, and their metadata, for the purposes
of enabling discovery of those resources for either end-user consumption or
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
    - [Managing Resources](#managing-resources)
    - [Managing versions of a Resource](#managing-versions-of-a-resource)
  - [Inlining Collections](#inlining-collections)
  - [Filtering](#filtering)

## Overview

A Registry Service is one that manages metadata about resources. At its core,
the management of an individual resource is simply a REST-based interface for
creating, modifying and deleting the resource. However, many resource models
share a common pattern of grouping resources by their "format" and can
optionally support versioning of the resources. This specification aims to
provide a common interaction pattern for these types of services with the goal
of providing an interoperable framework that will enable common tooling and
automation to be created.

This document is meant to be a framework from which additional specifications
can be defined that expose model specific resources and metadata.

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

Use of the words `GROUP` and `RESOURCE` are meant to represent the singular
form of a Group and Resource type being used.  While `GROUPs` and `RESOURCEs`
are the plural form of those respective types.

### Terminology

This specification defines the following terms:

#### Group

An entity that acts as a collection of related Resources.

#### Registry

An implementation of this specification. Typically, the implementation would
include model specific Groups, Resources and extension attributes.

#### Resource

A Resource is the main entity that is stored within a Registry Service. It
MAY be versioned and grouped as needed by the Registry's model.

## Registry Formats and APIs

This section defines common Registry metadata elements and APIs. It is an
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

Therefore, the hierarchical structure of the Registry model is defined in such a
way that it can be represented in a single file, including but not limited to
JSON or YAML, or via the resource graph of a REST API.

### Attributes and Extensions

The following attributes are used by one or more entities defined by this
specification. They are defined here once rather than repeating them
throughout the specification.

Attributes:

- `"id": "STRING"`
- `"name": "STRING"`
- `"description": "STRING"`
- `"tags": { "STRING": "STRING" * }`
- `"versionId": STRING`
- `"epoch": UINT`
- `"self": "URL"`
- `"createdBy": "STRING"`
- `"createdOn": "TIME"`
- `"modifiedBy": "STRING"`
- `"modifiedOn": "TIME"`
- `"docs": "URI"`

Implementations of this specification MAY define additional (extension)
attributes, and they MAY appear at any level of the model. However they MUST
adhere to the following rules:

- it is STRONGLY RECOMMENDED that they be named in such a way as to avoid
  potential conflicts with future Registry Service attributes. For example,
  use of a model (or domain) specific prefix can help.
- they MUST differ from sibling attributes irrespective of case. This avoids
  potential conflicts if the attributes are serialized in a case-insensitive
  situation, such as HTTP headers.
- for case sensitive serializations, it is RECOMMENDED that attribute names
  be defined in camelCase and acronyms have only their first letter
  capitalized. For example, `Id` not `ID`.

In situations where an attribute is serialized in a case-sensitive situation,
then the case specified by this specification, or the defining extension
specification, MUST be adhere to.

#### `id`

- Type: String   # SHOULD this be a URI-Reference?
- Description: An immutable unique identifier of the entity.
- Constraints:
  - MUST be a non-empty string consisting of visible US-ASCII octets (33-126).
  - MUST be immutable
  - MUST be case-insensitive unique within the scope of the entity's parent.
    In the case of the `id` for the Registry itself, the uniqueness scope will
    be based on where the Registry is used. For example, a publicly accessible
    Registry might want to consider using a UUID, while a private Registry
    does not need to be so widely unique.
- Examples:
  - A UUID

#### `name`

- Type: String
- Description: A human readable name of the entity.
  Note that implementations MAY choose to enforce constraints on this value.
  For example, they could mandate that `id` and `name` be the same value.
  How any such requirement is shared with all parties is out of scope of this
  specification.
- Constraints:
  - MUST be a non-empty string
- Examples:
  - `My Endpoints`

#### `description`

- Type: String
- Description: A human readable summary of the purpose of the entity.
- Constraints:
  - When this attribute has no value it MUST be serialized by either an empty
    string or by being excluded from the serialization of the owning entity
- Examples:
  - `A queue of the sensor generated messages`

#### `tags`

- Type: Map of name/value string pairs
- Description: A mechanism in which additional metadata about the entity can
  be stored without changing the schema of the entity.
- Constraints:
  - if present, MUST be a map of zero or more name/value string pairs
  - each name MUST be a non-empty string consisting of only alphanumeric
    characters, `-`, `_` or a `.`; be no longer than 63 characters;
    start with an alphanumeric character and be unique within the scope of
    this map. Values MAY be empty strings
- Examples:
  - `{ "owner": "John", "verified": "" }`

#### `versionId`

- Type: String
- Description: The ID of a specific version of an entity.
  Note that versions of an entity can be modified without changing the
  `versionId` value. Often this value is controlled by a user of the Registry.
  This specification makes no statement as to the format or versioning scheme
  used by implementations of this specification. However, it is assumed that
  newer versions of an entity will have a "higher" versionId value than older
  versions.  Also see `epoch`.
- Constraints:
  - MUST be a non-empty string.
  - MUST be unique across all versions of the entity
- Examples:
  - `1`, `2.0`, `v3-rc1`

#### `epoch`

- Type: Unsigned Integer
- Description: A numeric value used to determine whether an entity has been
  modified. Each time the associated entity is updated, this value MUST be
  set to a new value that is greater than the current one.
  Note that unlike `versionId`, this attribute is most often managed by
  the Registry itself. Additionally, if an entity is created that is based
  on another entity (e.g. a new version of an entity is created), then the
  new entity's `epoch` value can be reset (e.g. to zero) since the scope of
  its values is the entity.
- Constraints:
  - MUST be an unsigned integer equal to or greater than zero
  - MUST be unique within the scope of a version of an entity. If the entity
    is not versioned then the scope is just the entity itself
- Examples:
  - `1`, `2`, `3`

#### `self`

- Type: URL
- Description: A unique URL for the entity. The URL MUST be a combination of
  the base URL for the list of resources of this type of entity appended with
  the `id` of the entity.
- Constraints:
  - MUST be a non-empty URL
- Examples:
  - `https://example.com/registry/endpoints/123`

#### `createdBy`

- Type: String
- Description: A reference to the user or component that was responsible for
  the creation of this entity. This specification makes no requirement on
  the semantics or syntax of this value.
- Constraints:
  - When this attribute has no value it MUST be serialized by either an empty
    string or by being excluded from the serialization of the owning entity
- Examples:
  - `John Smith`
  - `john.smith@example.com`

#### `createdOn`

- Type: Timestamp
- Description: The date/time of when the entity was created.
- Constraints:
  - MUST be a [RFC3339](https://tools.ietf.org/html/rfc3339) timestamp
- Examples:
  - `2030-12-19T06:00:00Z"

#### `modifiedBy`

- Type: String
- Description: A reference to the user or component that was responsible for
  the the latest update of this entity. This specification makes no requirement
  on the semantics or syntax of this value.
- Constraints:
  - When this attribute has no value it MUST be serialized by either an empty
    string or by being excluded from the serialization of the owning entity
- Examples:
  - `John Smith`
  - `john.smith@example.com`

#### `modifiedOn`

- Type: Timestamp
- Description: The date/time of when the entity was last updated.
- Constraints:
  - MUST be a [RFC3339](https://tools.ietf.org/html/rfc3339) timestamp
- Examples:
  - `2030-12-19T06:00:00Z"

#### `docs`

- Type: URI-Reference
- Description: A URI-Reference to additional documentation about this entity.
  This specification does not place any constraints on the data returned from
  an HTTP GET to this value.
- Constraints:
  - if present, MUST be a non-empty URI-Reference
  - if present with a scheme, it MUST use either `http` or `https`
  - MUST support an HTTP GET to this URI-Reference
- Examples:
  - `https://example.com/docs/myQueue`

#### `format`

- Type: String
- Description: The name of the specification that defines the resource
  stored in the registry. Often it is difficult to unambiguously determine
  what a resource is via simple inspect of its serialization. This attribute
  provides a mechanism by which it can be determined without examination of
  the resource at all.
- Constraints:
  - if present, MUST be a non-empty string of the form `SPEC[/VERSION]`,
    where `SPEC` is the name of the specification that defines the resource.
    An OPTIONAL `VERSION` value SHOULD be included if there are multiple
    versions of the specification available.
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

### Registry APIs

This specification defines the following API patterns:

``` meta
/model                              # Manage the registry model
/                                   # Show all Groups
/GROUPs                             # Manage a Group Type
/GROUPs/gID                         # Manage a Group
/GROUPs/gID/RESOURCEs               # Manage a Resource Type
/GROUPs/gID/RESOURCEs/rID           # Manage the latest Resource version
/GROUPs/gID/RESOURCEs/rID?meta      # Metadata about the latest Resource version
/GROUPs/gID/RESOURCEs/rID/versions  # Show version strings for a Resource
/GROUPs/gID/RESOURCEs/rID/versions/vID         # Manage a Resource version
/GROUPs/gID/RESOURCEs/rID/versions/vID?meta    # Metadata about a version
```

Where:
- `GROUPs` is a Group name (plural). E.g. `endpoints`
- `gID` is the unique identifier of a single Group
- `RESOURCEs` is the type of Resource (plural). E.g. `definitions`
- `rID` is the unique identifier of a single Resource
- `vID` is the unique identifier of a version of a Resource

While these APIs are shown to be at the root path of a Registry Service,
implementation MAY choose to prefix them as necessary. However, the same
prefix MUST be used consistently for all APIs in the same Registry Service.

The following sections define the APIs in more detail.

#### Registry Model

The Registry model defines the Groups and Resources supported by the Registry
Service. This information will usually be used by tooling that does not have
advanced knowledge of the data stored within the Registry.

The Registry model can be retrieved two ways:

1. as a stand-alone resource. This is useful when management of the Registry's
   model is needed independently from the resources within the Registry.
2. as part of the Registry resources. This is useful when it is desirable to
   view the entire Registry as a single document - such as an "export" type
   of scenario. See the [Retrieving the Registry](#retrieving-the-registry)
   section (the `?model` flag) for more information on this option.

Regardless of how the model is retrieved, the overall format is as follows:

``` meta
{
  "schema": "URI-Reference", ?         # Schema doc for the entire Registry
  "groups": [
    { "singular": "STRING",            # eg. "endpoint"
      "plural": "STRING",              # eg. "endpoints"
      "schema": "URI-Reference", ?     # Schema doc for the group

      "resources": [
        { "singular": "STRING",        # eg. "definition"
          "plural": "STRING",          # eg. "definitions"
          "versions": UINT ?           # Num versions(>=1). Def=1, 0=unlimited
        } +
      ] ?
    } +
  ] ?
}
```

The following describes the attributes of Registry model:

- `groups`
  - REQUIRED if there are any Groups defined for the Registry
  - The set of Groups supported by the Registry
- `groups.singular`
  - REQUIRED
  - The singular name of a Group. E.g. `endpoint`
  - MUST be unique across all Groups in the Registry
- `groups.plural`
  - REQUIRED
  - The plural name of a Group. E.g. `endpoints`
  - MUST be unique across all Groups in the Registry
- `groups.schema`
  - OPTIONAL
  - A URI-Reference to a schema document for the Group
- `groups.resources`
  - REQUIRED if there are any Resources defined for the Group
  - The set of Resource entities defined for the Group
- `groups.resources.singular`
  - REQUIRED
  - The singular name of the Resource. E.g. `definition`
- `groups.resources.plural`
  - REQUIRED
  - The plural name of the Resource. E.g. `definitions`
- `groups.resources.versions`
  - OPTIONAL
  - Number of versions per Resource that will be stored in the Registry
  - The default value is zero (`1`), meaning only the current version will
    be stored
  - A value of negative one (`0`) indicates there is no stated limit, and
    implementation MAY prune non-latest versions at any time. Implementation
    MUST NOT delete a version without also deleting all older versions.


Below describes how to retrieve the model as an independent resource.

The request MUST be of the form:

``` meta
GET /model
```

A successful response MUST be of the form:

``` meta
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: nnnn

{
  "schema": "URI-Reference", ?         # Schema doc for the entire Registry
  "groups": [
    { "singular": "STRING",            # eg. "endpoint"
      "plural": "STRING",              # eg. "endpoints"
      "schema": "URI-Reference", ?     # Schema doc for the group

      "resources": [
        { "singular": "STRING",        # eg. "definition"
          "plural": "STRING",          # eg. "definitions"
          "versions": UINT ?           # Num versions. Def=1, 0=unlimited
        } +
      ] ?
    } +
  ] ?
}
```

**Examples:**

Request:

``` meta
GET /model
```

Response:

``` meta
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: nnnn

{
  "model": {
    "groups": [
      { "singular": "endpoint",
        "plural": "endpoints",

        "resources": [
          { "singular": "definitionGroup",
            "plural": "definitionGroups",
            "versions": 1
          }
        ]
      }
    ]
  }
}
```

#### Registry Collections

The Registry collections (groupings of same-typed resources) that are defined
by the Registry Model discussed in the previous section follow a consistent
pattern with respect to how they are represented in the serialization of the
Registry.

Each collection MUST be serialized as 2 REQUIRED properties and 1 OPTIONAL
one - as shown in the following example:
```
  "GROUPsUrl": "URL,
  "GROUPsCount": UINT,
  "GROUPs": { ... map of Resources in the Group, key is the "id" of each ... } ?
```

Each property MUST start with the plural name of the entity type. For example,
`endpointsUrl`, not `endpointUrl`. The `xxxsUrl` property MUST always be
present and MUST contain an absolute URL that can be used to retrieve the
latest set of entities in the collection via an HTTP `GET`. The `xxxsCount`
property MUST always be present and MUST contain the number of entities in
the collection after any filtering that might have been applied. The `xxxs`
property is OPTIONAL and MUST only be included if the Registry request included
the [`inline`](#inlining-collections) flag indicating that this collection's
value are to be returned as part of the result. This property MUST be a map
with the key equal to the `id` of each entity in the collection. When filtering
is applied then this property MUST only include entities that satisfy the
filter criteria.

The set of entities returned in the `xxxs` property is a point-in-time view
of the Registry. There is no guarantee that a `GET` to the `xxxsUrl` will
return the exact same collection since the contents of the Registry might
have changed.

When the number of entities in the collection (after filtering) is zero, the
`xxxs` property MAY be excluded from the serialization, even if
[`inline`](#inlining-collections) is specified.

For clarity, these rules MUST apply to the Groups(`GROUPs`),
Resources(`RESOURCEs`) and Versions(`versions`) collections.

#### Registry Entity

The Registry entity represents the root of a Registry and is the main
entry-point for traversal.

The Registry entity includes the following common attributes:
- [`id`](#id) - REQUIRED
- [`name`](#name) - OPTIONAL
- [`description`](#description) - OPTIONAL
- [`tags`](#tags) - OPTIONAL
- [`self`](#self) - REQUIRED
- [`docs`](#docs) - OPTIONAL

and the following Registry specific attributes:

##### `specVersion`
- Type: String
- Description: The version of this specification that the serialization
  adheres to
- Constraints:
  - MUST be included in any serialization that includes the top-level
    Registry resource
- Examples:
  - `1.0`

##### `model`
- Type: Registry Model
- Description: A description of the Groups and Resources supported by this
  Registry.
- Constraints:
  - OPTIONAL based on the incoming request
  - MUST NOT be included unless requested
  - MUST be included if requested

##### `GROUPs` collections
- Type: [Registry Collection](#registry-collections)
- Description: A list of Registry collections that contain the set of
  Groups(`GROUPs) supported by the Registry
- Constraints:
  - MUST include all Group Collections unless one was excluded due to a filter

##### Retrieving the Registry

To retrieve the Registry, its metadata attributes and Groups, an HTTP GET
MAY be used.

The request MUST be of the form:

``` meta
GET /[?model&inline=...&filter=...]
```

The following query parameters MUST be supported:
- `model`<br>
  The presence of this query parameter indicates that the request is asking
  for the Registry model to be included in the response. See
  [`model`](#model) for more information.
- `inline`<br>
  The presence of this query parameter indicates that the response MUST
  include the contents of the specified collections as part of the response.
  See [inlining](#inlining-collections) for more information.
- `filter`<br>
  The presence of this query parameter indicates that response MUST only
  include data matching the specified [filter](#filtering) expression.

A successful response MUST be of the form:

``` meta
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: nnnn

{
  "id": "STRING",
  "name": "STRING", ?
  "description": "STRING", ?
  "specVersion": "STRING",
  "self": "URL",
  "tags": { "STRING": "STRING" * }, ?
  "docs": "URL", ?

  "model": { ... } ?                  # if "model" query parameter is present

  # Repeat for each Group type
  "GROUPsUrl": "URL",                 # eg. "endpointsUrl"
  "GROUPsCount": INT                  # eg. "endpointsCount"
  "GROUPs": { GROUPs collection }, ?  # if inlined
}
```

**Examples:**

Request:

``` meta
GET /
```

Response:

``` meta
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: nnnn

{
  "id": "123",
  "specVersion": "0.1",
  "self": "http://example.com/",

  "endpointsURL": "https://example.com/endpoints",
  "endpointsCount": 42,

  "definitionGroupsURL": "https://example.com/definitionGroups",
  "definitionGroupsCount": 1
}
```

Another example asking for the model to be included and for one of the
collections to be inlined:

Request:

``` meta
GET /?model&inline=definitionGroups
```

Response:

``` meta
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: nnnn

{
  "id": "123",
  "specVersion": "0.1",
  "self": "http://example.com/",

  "model": {
    "groups": [
      { "singular": "endpoint",
        "plural": "endpoints",

        "resources": [
          { "singular": "definitionGroup",
            "plural": "definitionGroups",
            "versions": 1
          }
        ]
      }
    ]
  },

  "endpointsUrl": "https://example.com/endpoints",
  "endpointsCount": 42,

  "definitionGroupsUrl": "https://example.com/definitionGroups",
  "definitionGroupsCount": 1,
  "definitionGroups": {
    "blobStoreEvents": {
      "id": "blobStoreEvents",
      ... excluded for brevity ...
    }
  }
}
```

#### Groups

Groups represent top-level resources in a Registry that act as a collection
mechanism for related Resources. Each Group definition MAY have any number of
Resource types within it. This specification does not define how the Resources
within a Group definition are related.

Groups include the following common attributes:
- [`id`](#id) - REQUIRED
- [`name`](#name) - REQUIRED
- [`epoch`](#epoch) - REQUIRED

and the following Group specific attributes:

##### `RESOURCEs` collections
- Type: [Registry Collection](#registry-collections)
- Description: A list of Registry collections that contain the set of
  Resources supported by the Group
- Constraints:
  - MUST include all nested Resource Collections of the owning Group unless
    one was excluded due to a filter

##### Retrieving A Group Collection

To retrieve all Groups of a certain type, an HTTP GET MAY be used.

The request MUST be of the form:

``` meta
GET /GROUPs[?inline=...&filter=...]
```

Where GROUPs is the plural name of a Group type.

The following query parameters MUST be supported:
- `inline`<br>
  The presence of this query parameter indicates that the response MUST
  include the contents of the specified collections as part of the response.
  See [inlining](#inlining-collections) for more information.
- `filter`<br>
  The presence of this query parameter indicates that the response MUST only
  include data matching the specified [filter](#filtering) expression.

A successful response MUST be of the form:

``` meta
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: nnnn
Link: <URL>;rel=next;count=INT  # If pagination is needed

{
  "ID": {                   # The Group ID
    "id": "STRING",         # Group attributes
    "name": "STRING",
    "epoch": UINT,          # Server controlled

    # Repeat for each Resource type in the Group
    "RESOURCEsUrl": "URL",                    # eg. "schemasUrl"
    "RESOURCEsCount": INT,                    # eg. "schemasCount"
    "RESOURCEs": { RESOURCEs collection } ?   # if inlined
  } *
}
```

Note: If the `inline` query parameter is present and the presence of the
`RESOURCEs` map results in even a single Group being too large to return in
one response then an error MUST be generated. In those cases the client will
need to query the individual Resources via the `RESOURCEsUrl` so the Registry
can leverage pagination of the response data.

TODO: define the error

**Examples:**

Request:

``` meta
GET /endpoints
```

Response:

``` meta
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: nnnn
Link: <http://example.com/endpoints&page=2>;rel=next;count=100

{
  "123": {
    "id": "123",
    "name": "A cool endpoint",
    "epoch": 1,

    "definitionsUrl": "https://example.com/endpoints/123/definitions",
    "definitionsCount": 5
  },
  "124": {
    "id": "124",
    "name": "Redis Queue",
    "epoch": 3,

    "definitionsUrl": "https://example.com/endpoints/124/definitions",
    "definitionsCount": 1
  }
}
```

##### Creating a Group

This will add a new Group to the Registry.

The request MUST be of the form:

``` meta
POST /GROUPs

{
  "id": "STRING", ?       # If absent then it's server defined
  "name": "STRING",
}
```

A successful response MUST be of the form:

``` meta
HTTP/1.1 201 Created
Content-Type: application/json; charset=utf-8
Content-Length: nnnn
Location: URL             # .../GROUPs/ID

{                         # MUST be full representation of new Group
  "id": "STRING",
  "name": "STRING",
  "epoch": UINT,

  # Repeat for each Resource type in the Group
  "RESOURCEsUrl": "URL",  # URL to retrieve all nested Resources
  "RESOURCEsCount": INT   # Total number resources
}
```

**Examples:**

Request:

``` meta
POST /endpoints

{ TODO }
```

Response:

``` meta
HTTP/1.1 201 Created
Content-Type: application/json; charset=utf-8
Content-Length: nnnn
Location: https://example.com/endpoints/ID

{ TODO }
```

##### Retrieving a Group

This will return a single Group.

The request MUST be of the form:

``` meta
GET /GROUPs/ID[?inline[=PATH,...]]
```

Where `PATH` is a string indicating which collections of RESOURCEs and
`versions` to include in the response. The PATH MUST be of the form
`RESOURCEs[.versions]` where `RESOURCEs` is replaced with the plural name of
a Resource. There MAY be mulitple PATHs specified, either as comma separated
values or via mulitple `inline` query parameters. Absence of a value, or a
value of an empty string, indicates that all nested collections MUST be inlined.

A successful response MUST be of the form:

``` meta
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: nnnn

{
  "id": "STRING",         # Group attributes
  "name": "STRING",
  "epoch": UINT,           # Server controlled

  # Repeat for each Resource type in the Group
  "RESOURCEsUrl": "URL",  # URL to retrieve all nested Resources
  "RESOURCEsCount": INT,  # Total number resources
  "RESOURCEs": {          # Only when ?inline is present
    "ID": {
      "id": "STRING",
      ... remaining Resource ?meta and Resource itself ...

      "versionsUrl": "URL",
      "versionsCount": INT,
      "versions": {       # Only when ?inline is present
        "ID": {
          "id": "STRING",
          ... remaining VERSION ?meta and VERSION itself ...
        } ?
      } ?
    } *
  } ?                     # OPTIONAL if RESOURCEsCount is zero
}
```

**Examples:**

Request:

``` meta
GET /endpoints/123
```

Response:

``` meta
HTTP/1.1 ...
Content-Type: application/json; charset=utf-8
Content-Length: nnnn

{
  "id": "123",
  "name": "A cool endpoint",
  "epoch": 1,

  "definitionsUrl": "https://example.com/endpoints/123/definitions",
  "definitionsCount": 5
}
```

##### Updating a Group

This will update the attributes of a Group.

The request MUST be of the form:

``` meta
PUT /GROUPs/ID[?epoch=EPOCH]

{
  # Missing attributes are deleted from Group
  "id": "STRING",            # MUST match URL if present
  "name": "STRING",
  "epoch": UINT ?            # OPTIONAL - MUST be current value if present

  # Presence of the RESOURCEs attributes are OPTIONAL and MUST be ignored
}
```

A successful response MUST be of the form:

``` meta
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: nnnn

{
  "id": "STRING",
  "name": "STRING",
  "epoch": UINT,          # MUST be greater than previous value

  # Repeat for each Resource type in the Group
  "RESOURCEsUrl": "URL",
  "RESOURCEsCount": INT
}
```

**Examples:**

Request:

``` meta
PUT /endpoints/123

{
  "id": "123",
  "name": "A cooler endpoint",
  "epoch": 1
}
```

Response:

``` meta
HTTP/1.1 OK
Content-Type: application/json; charset=utf-8
Content-Length: nnnn

{
  "id": "123",
  "name": "A cooler endpoint",
  "epoch": 2,

  "definitionsUrl": "https://example.com/endpoints/123/definitions",
  "definitionsCount": 5,
}
```

##### Deleting Groups

To delete a single Group the following API can be used.

The request MUST be of the form:

``` meta
DELETE /GROUPs/ID[?epoch=EPOCH]
```

If `epoch` is present then it MUST match the current value.

A successful response MUST be of the form:

``` meta
HTTP/1.1 200 OK                  # 202 or 204 are ok
Content-Type: application/json; charset=utf-8
Content-Length: nnnn

{                       # RECOMMENDED, last known state of entity
  "id": "STRING",
  "name": "STRING",
  "epoch": UINT,
  ...
} ?
```

To delete multiple Groups the following API can be used.

The request MUST be of the form:

``` meta
DELETE /GROUPs

[
  {
    "id": "STRING",
    "epoch": UINT ?     # If present it MUST match current value
  } *
]
```

A successful response MUST be of the form:

``` meta
HTTP/1.1 200 OK                  # 202 or 204 are ok
Content-Type: application/json; charset=utf-8
Content-Length: nnnn

{ "ID": { ... } * } ?   # RECOMMENDED
```

If any of the individual deletes fails then the entire request MUST fail
and none of the Groups are deleted.

A `DELETE /GROUPs` without a body MUST delete all Groups.

#### Managing Resources

##### Retrieving all Resources

This will retrieve the Resources from a Group.

The request MUST be of the form:

``` meta
GET /GROUPs/ID/RESOURCEs[?inline[=versions]]
```

Where `inline` indicates whether to include the `versions` collection
in the response. In this case the "versions" value is OPTIONAL since it is the
only collection within the Resource that might be shown. Absence of a value, or
a value of an empty string, indicates that the `versions` collection MUST
be inlined.

A successful response MUST be of the form:

``` meta
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: nnnn
Link: <URL>;rel=next;count=INT  # If pagination is needed

{
  "ID": {
    "id": "STRING",
    "name": "STRING",
    "versionId": "STRING",
    "epoch": UINT,
    "self": "URL",                   # URL to specific version

    "RESOURCEUri": "URI", ?          # If not locally stored (singular)
    "RESOURCE": {} ?,                # If ?inline present & JSON (singular)
    "RESOURCEBase64": "STRING" ?     # If ?inline present & ~JSON (singular)

    "versionsUrl": "URL",
    "versionsCount": INT,
    "versions": {                    # Only when ?inline is present
      "ID": {
        "id": "STRING",
        ... remaining VERSION ?meta and VERSION itself ...
      } ?
    } ?
  } *
}
```

Note: If the `inline` query parameter is present and the presence of the
`versions` map results in even a single Resource being too large to return in
one response then an error MUST be generated. In those cases the client will
need to query the individual Versions via the `versionUrl` so the Registry
can leverage pagination of the response data.

**Examples:**

Request:

``` meta
GET /endpoints/123/definitions
```

Response:

``` meta
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: nnnn
Link: <http://example.com/endpoints/123/definitions&page=2>;rel=next;count=100

{
  "456": {
    "id": "456",
    "name": "Blob Created",
    "format": "CloudEvents/1.0",
    "versionId": "3.0",
    "epoch": 1,
    "self": "https://example.com/endpoints/123/definitions/456/version/3"
  }
}
```

##### Creating Resources

This will create a new Resources in a particular Group.

The request MUST be of the form:

``` meta
POST /GROUPs/ID/RESOURCEs
Registry-name: STRING ?          # If absent, default to the ID?
Registry-type: STRING ?
Registry-RESOURCEURI: URI ?      # If present body MUST be empty (singular)

{ ...Resource entity... } ?
```

A successful response MUST be of the form:

``` meta
HTTP/1.1 201 Created
Content-Type: application/json; charset=utf-8
Content-Length: nnnn
Registry-id: STRING
Registry-name: STRING
Registry-type: STRING ?
Registry-version: STRING
Registry-epoch: UINT
Registry-self: STRING            # URL to the specific version
Registry-RESOURCEURI: URI ?      # If present body MUST be empty (singular)
Location: URL                    # Points to "latest" URL
Content-Location: URL            # Same as Registry-self value

{ ...Resource entity... } ?
```

**Examples:**

Request:

``` meta
TODO
```

##### Retrieving a Resource

This will retrieve the latest version of a Resource. This can be considered an
alias for `/GROUPs/gID/RESOURCEs/rID/versions/vID` where `vID` is the latest
versionId value.

The request MUST be of the form:

``` meta
GET /GROUPs/ID/RESOURCEs/ID[?inline[=versions]]
```

Where `inline` indicates whether to include the `versions` collection
in the response. In this case the "versions" value is OPTIONAL since it is the
only collection within the Resource that might be shown. Absence of a value, or
a value of an empty string, indicates that the `versions` collection MUST
be inlined.

A successful response MUST be of the form:

``` meta
HTTP/1.1 200 OK  or 307 Temporary Redirect    # 307 if RESOURCEURI is present
Content-Type: application/json; charset=utf-8
Content-Length: nnnn

Registry-id: STRING
Registry-name: STRING
Registry-type: STRING ?
Registry-version: STRING
Registry-epoch: UINT
Registry-self: STRING            # URL to the specific version
Registry-RESOURCEURI: URI ?      # If present body MUST be empty (singular)
Content-Location: URL            # Same as Registry-self value
Location: URL                    # If 307. Same a Registry-RESOURCEURI

{ ...Resource entity... } ?
```

**Examples:**

Request:

``` meta
TODO
```

##### Retrieving a Resource's Metadata

This will retrieve the metadata for the latest version of a Resource. This can
be considered an alias for
`/GROUPs/ID/RESOURCEs/RESOURCEID/versions/VERSIONID?meta` where `VERSIONID` is
the latest versionId value.

The request MUST be of the form:

``` meta
GET /GROUPs/ID/RESOURCEs/ID?meta
```

A successful response MUST be of the form:

``` meta
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: nnnn

{
  "id": "STRING",
  "name": "STRING",
  "versionId": "STRING",
  "epoch": UINT,
  "self": "URL",
  "RESOURCEUri": "URI" ?     # singular
}
```

**Examples:**

Request:

``` meta
TODO
```

##### Updating a Resource

This will update the latest version of a Resource. Missing Registry HTTP
headers MUST NOT be interpreted as deleting the attribute. However, a Registry
HTTP headers with an empty string for its value MUST be interpreted as a
request to delete the attribute.

The request MUST be of the form:

``` meta
PUT /GROUPs/ID/RESOURCEs/ID[?epoch=EPOCH]
Registry-id: STRING ?            # If present it MUST match URL
Registry-name: STRING ?
Registry-type: STRING ?
Registry-version: STRING ?       # If present it MUST match current value
Registry-epoch: UINT ?           # If present it MUST match current value & URL
Registry-self: STRING ?          # If present it MUST be ignored?
Registry-RESOURCEURI: URI ?      # If present body MUST be empty (singular)

{ ...Resource entity... } ?      # If empty then content is erased
```

A successful response MUST be of the form:

``` meta
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: nnnn
Registry-id: STRING
Registry-name: STRING
Registry-type: STRING ?
Registry-version: STRING
Registry-epoch: UINT             # MUST be incremented
Registry-self: STRING
Registry-RESOURCEURI: URI ?      # singular
Content-Location: URL

{ ...Resource entity... } ?
```

Note: if some of the Registry attributes are shared with the Resource itself
then those values MUST appear in both the Registry HTTP headers as well as in
the Resource itself when retrieving the Resource. However, in this "update"
case, if the attribute only appears in the HTTP body and the corresponding
Registry HTTP header is missing then the Registry attribute MUST be updated to
match the Resource's attribute. If both are present on the request and do not
have the same value then an error MUST be generated.

**Examples:**

Request:

``` meta
TODO
```

Response:

``` meta
TODO
```

TODO: make a note that empty string and attribute missing are the same thing.
Which error is to be returned?

##### Updating a Resource's metadata

This will update the metadata of the latest version of a Resource without
creating a new version.

The request MUST be of the form:

``` meta
PUT /GROUPs/ID/RESOURCEs/ID?meta[&epoch=EPOCH]

{
  "id": "STRING",
  "name": "STRING",
  "versionId": "STRING", ?     # If present it MUST match current value
  "epoch": UINT, ?             # If present it MUST match current value & URL
  "self": "URL", ?             # If present it MUST be ignored
  "RESOURCEUri": "URI" ?       # singular
}
```

A successful response MUST be of the form:

``` meta
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: nnnn

{
  "id": "STRING",
  "name": "STRING",
  "versionId": "STRING",
  "epoch": UINT,               # MUST be incremented
  "self": "URL",
  "RESOURCEUri": "URI" ?       # singular
}
```

**Examples:**

Request:

``` meta
TODO
```

Response:

``` meta
TODO
```

##### Deleting Resources

To delete a single Resource the following API can be used.

The request MUST be of the form:

``` meta
DELETE /GROUPs/ID/RESOURCEs/ID[?epoch=EPOCH]
```

If `epoch` is present then it MUST match the current value.

A successful response MUST be of the form:

``` meta
HTTP/1.1 200 OK                  # 202 or 204 are ok
Content-Type: application/json; charset=utf-8
Content-Length: nnnn
Registry-id: STRING
Registry-name: STRING
Registry-type: STRING ?
Registry-version: STRING
Registry-epoch: UINT
Registry-self: STRING
Registry-RESOURCEURI: URI ?        # singular
Content-Location: URL              # Does this make sense if it's been deleted?

{ ...Resource entity... } ?
```

**Examples:**

Request:

``` meta
TODO
```

To delete multiple Resources the following API can be used.

The request MUST be of the form:

``` meta
DELETE /GROUPs/ID/RESOURCEs

[
  {
    "id": "STRING",
    "epoch": UINT ?     # If present it MUST match current value
  } *
]
```

A successful response MUST be of the form:

``` meta
HTTP/1.1 200 OK                  # 202 or 204 are ok
Content-Type: application/json; charset=utf-8
Content-Length: nnnn

{ "ID": { ... } * } ?   # RECOMMENDED
```

If any of the individual deletes fails then the entire request MUST fail
and none of the Resources are deleted.

A `DELETE /GROUPs/ID/RESOURCEs` without a body MUST delete all Resources in the
Group.

#### Managing versions of a Resource

##### Retrieving all versions of a Resource

This will retrieve all versions of a Resource.

The request MUST be of the form:

``` meta
GET /GROUPs/ID/RESOURCEs/ID/versions
```

A successful response MUST be of the form:

``` meta
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: nnnn
Link: <URL>;rel=next;count=INT  # If pagination is needed

{
  "ID": {                            # Versions ID/string
    "id": "STRING",
    "name": "STRING",
    "versionId": "STRING",
    "epoch": UINT,
    "self": "URL",
    "RESOURCEUri": "URI", ?          # If not locally stored (singular)
    "RESOURCE": {} ?,                # If ?inline present & JSON (singular)
    "RESOURCEBase64": "STRING" ?     # If ?inline present & ~JSON (singular)
  } *
}
```

**Examples:**

Request:

``` meta
TODO
```

##### Creating a new version of a Resource

This will create a new version of a Resource. Any metadata not present will be
inherited from latest version. To delete any metadata include its HTTP Header
with an empty value.

The request MUST be of the form:

``` meta
POST /GROUPs/ID/RESOURCEs/ID[?epoch=EPOCH]
Registry-id: STRING ?            # If present it MUST match URL
Registry-name: STRING ?
Registry-type: STRING ?
Registry-version: STRING ?       # MUST NOT be present
Registry-epoch: UINT ?           # If present it MUST match current value & URL
Registry-self: STRING ?          # If present it MUST be ignored?
Registry-RESOURCEURI: URI ?      # If present body MUST be empty (singular)

{ ...Resource entity... } ?      # If empty then content is erased
```

A successful response MUST be of the form:

``` meta
HTTP/1.1 201 Created
Content-Type: application/json; charset=utf-8
Content-Length: nnnn
Registry-id: STRING
Registry-name: STRING
Registry-type: STRING ?
Registry-version: STRING
Registry-epoch: UINT
Registry-self: STRING
Registry-RESOURCEURI: URI ?       # singular
Content-Location: URL            # Same as self
Location: .../GROUPs/ID/RESOURCEs/ID   # or self?

{ ...Resource entity... } ?
```

**Examples:**

Request:

``` meta
TODO
```

Response:

``` meta
TODO
```

##### Retrieving a version of a Resource

This will retrieve a particular version of a Resource.

The request MUST be of the form:

``` meta
GET /GROUPs/ID/RESOURCEs/ID/versions/VERSION
```

A successful response MUST be of the form:

``` meta
HTTP/1.1 200 OK  or 307 Temporary Redirect    # 307 if RESOURCEURI is present
Content-Type: application/json; charset=utf-8
Content-Length: nnnn
Registry-id: STRING
Registry-name: STRING
Registry-type: STRING ?
Registry-version: STRING
Registry-epoch: UINT
Registry-self: STRING            # URL to the specific version
Registry-RESOURCEURI: URI ?      # If present body MUST be empty (singular)
Content-Location: URL            # Same as Registry-self value
Location: URL                    # If 307. Same a Registry-RESOURCEURI

{ ...Resource entity... } ?
```

**Examples:**

Request:

``` meta
TODO
```

##### Retrieving a version of a Resource's metadata

This will retrieve the metadata for a particular version of a Resource.

The request MUST be of the form:

``` meta
GET /GROUPs/ID/RESOURCEs/ID/versions/ID?meta
```

A successful response MUST be of the form:

``` meta
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: nnnn

{
  "id": "STRING",
  "name": "STRING",
  "epoch": UINT,
  "self": "URL",
  "RESOURCEUri": "URI" ?          # singular
}
```

**Examples:**

Request:

``` meta
TODO
```

##### Updating a version of a Resource

This will update a particular version of a Resource. Missing Registry HTTP
headers MUST NOT be interpreted as deleting the attribute. However, a Registry
HTTP headers with an empty string for its value MUST be interpreted as a
request to delete the attribute.

The request MUST be of the form:

``` meta
PUT /GROUPs/ID/RESOURCEs/ID/versions/VERSION[?epoch=EPOCH]
Registry-id: STRING ?            # If present it MUST match URL
Registry-name: STRING ?
Registry-type: STRING ?
Registry-version: STRING ?       # If present it MUST match current value & URL
Registry-epoch: UINT ?           # If present it MUST match current value & URL
Registry-self: STRING ?          # If present it MUST be ignored?
Registry-RESOURCEURI: URI ?      # If present body MUST be empty (singular)

{ ...Resource entity... } ?      # If empty then content is erased
```

A successful response MUST be of the form:

``` meta
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: nnnn
Registry-id: STRING
Registry-name: STRING
Registry-type: STRING ?
Registry-version: STRING
Registry-epoch: UINT             # MUST be incremented
Registry-self: STRING
Registry-RESOURCEURI: URI ?      # singular
Content-Location: URL

{ ...Resource entity... } ?
```

Note: if some of the Registry attributes are shared with the Resource itself
then those values MUST appear in both the Registry HTTP headers as well as in
the Resource itself when retrieving the Resource. However, in this "update"
case, if the attribute only appears in the HTTP body and the corresponding
Registry HTTP header is missing then the Registry attribute MUST be updated to
match the Resource's attribute. If both are present on the request and do not
have the same value then an error MUST be generated.

**Examples:**

Request:

``` meta
TODO
```

##### Updating a version of a Resource's metadata

This will update the metadata of a particular version of a Resource without
creating a new version.

The request MUST be of the form:

``` meta
PUT /GROUPs/ID/RESOURCEs/ID/versions/ID?meta[&epoch=EPOCH]

{
  "id": "STRING",
  "name": "STRING",
  "epoch": UINT, ?             # If present it MUST match current value & URL
  "self": "URL", ?             # If present it MUST be ignored
  "RESOURCEUri": "URI" ?       # singular
}
```

A successful response MUST be of the form:

``` meta
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: nnnn

{
  "id": "STRING",
  "name": "STRING",
  "epoch": UINT,               # MUST be incremented
  "self": "URL",
  "RESOURCEUri": "URI" ?       # singular
}
```

**Examples:**

Request:

``` meta
TODO
```

Response:

``` meta
TODO
```

##### Deleting versions of a Resource

To delete a single version of a Resource the following API can be used.

The request MUST be of the form:

``` meta
DELETE /GROUPs/ID/RESOURCEs/ID/versions/VERSION[?epoch=EPOCH]
```

If `epoch` is present then it MUST match the current value.

A successful response MUST be of the form:

``` meta
HTTP/1.1 200 OK                  # 202 or 204 are ok
Content-Type: application/json; charset=utf-8
Content-Length: nnnn
Registry-id: STRING
Registry-name: STRING
Registry-type: STRING ?
Registry-version: STRING
Registry-epoch: UINT
Registry-self: STRING
Registry-RESOURCEURI: URI ?        # singular
Content-Location: URL              # Does this make sense if it's been deleted?

{ ...Resource entity... } ?
```

**Examples:**

Request:

``` meta
TODO
```

Response:

``` meta
TODO
```

To delete multiple versions of a Resource the following API can be used.

The request MUST be of the form:

``` meta
DELETE /GROUPs/ID/RESOURCEs/ID/versions

[
  {
    "id": "STRING",
    "epoch": UINT ?     # If present it MUST match current value
  } *
]
```

A successful response MUST be of the form:

``` meta
HTTP/1.1 200 OK                  # 202 or 204 are ok
Content-Type: application/json; charset=utf-8
Content-Length: nnnn

{ "ID": { ... } * } ?   # RECOMMENDED
```

If any of the individual deletes fails then the entire request MUST fail
and none of the Resources are deleted.

If the latest version is deleted then the remaining version with the largest
`versionId` value MUST become the latest.

An attempt to delete all versions MUST generate an error.

A `DELETE /GROUPs/ID/RESOURCEs/ID/versions` without a body MUST delete all
versions (except the latest) of the Resource.

### Inlining Collections

The `inline` query parameter on a request indicates that the response
MUST include the contents of all specified collections, in addition to the
`URL` and `Count` values of the collections. See
[Registry Collections](#registry-collections) for more information. This
is useful for cases where the contents of the Registry are to be represented
as a single (self-contained) document.

The format of the `inline` query parameter is:

``` meta
inline[=PATH[,...]]
```

Where `PATH` is a string indicating which collections of Groups, Resources
or `versions` to include in the response. References to nested collections are
represented using a dot(`.`) notation - for example `GROUPs.RESOURCEs`.

There MAY be multiple `PATH`s specified, either as comma separated values on
a single `inline` parameter or via multiple `inline` query parameters. Absence
of a value, or a value of an empty string, indicates that all nested
collections MUST be inlined.

The specific value of `PATH` will vary based on where the request is directed.
For example, a request to the root of the Registry would start with a `GROUPs`
name, while a request directed at a Group would start with a `RESOURCEs` name.

For example:

Given a Registry with a model that has "endpoints" as a Group and "definitions"
as a Resource within "endpoints":

| HTTP GET Path | Example ?inline=PATH values |
| --- | --- |
| / | ?inline=endpoints |
| / | ?inline=endpoints.definitions.versions |
| /endpoints | ?inline=definitions |
| /endpoints/myendpoint | ?inline=definitions.versions |
| /endpoints/myendpoint | ?inline=endpoints # Invalid, already in 'endpoints' |

Note that asking for a collection to be inlined will implicitly causes all of
its parent collections to be inlined as well.

Each collection MUST be specified using the plural name for the collection
in its defined case.

A request to inline an unknown collection MUST NOT return an error and
MUST continue as if that inline PATH was not specified.

Note: If the Registry can not return all expected data in one response then it
MUST generate an error. In those cases, the client will need to query the
individual collection via the appropriate `xxxsUrl` API so the Registry can
leverage pagination of the response.

TODO: define the error
TODO: add pagination

### Filtering

TODO

