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
  - [Registry Entity](#registry-entity)
  - [Registry Model](#registry-model)
  - [Groups](#groups)
    - [Retrieving a Group Collection](#retrieving-a-group-collection)
    - [Creating or Updating Groups](#creating-or-updating-groups)
    - [Retrieving a Group](#retrieving-a-group)
    - [Deleting Group](#deleting-groups)
  - [Resources](#resources)
    - [Retrieving a Resource Collection](#retrieving-a-resource-collection)
    - [Creating or Updating Resources and Versions](#creating-or-updating-resources-and-versions)
    - [Retrieving a Resource](#retrieving-a-resource)
    - [Deleting a Resource](#deleting-resources)
  - [Versions](#versions)
    - [Retrieving all Versions](#retrieving-all-versions)
    - [Creating or Updating Versions](#creating-or-updating-versions)
    - [Retrieving a Version](#retrieving-a-version)
    - [Deleting Version](#deleting-versions)
  - [Inlining](#inlining)
  - [Filtering](#filtering)
  - [HTTP Header Values](#http-header-values)

## Overview

A Registry Service is one that manages metadata about Resources. At its core,
the management of an individual Resource is simply a REST-based interface for
creating, modifying and deleting the Resource. However, many Resource models
share a common pattern of grouping Resources (e.g. by their "format") and can
optionally support versioning of the Resources. This specification aims to
provide a common interaction pattern for these types of services with the goal
of providing an interoperable framework that will enable common tooling and
automation to be created.

This document is meant to be a framework from which additional specifications
can be defined that expose model specific Resources and metadata.

A Registry consists of two main types of entities: Groups and Resources.

Groups, as the name implies, is a mechanism by which related Resources are
arranged together under a single collection - the Group. The reason for the
grouping is not defined by this specification, so the owners of the Registry
can choose to define (or enforce) any pattern they wish.  In this sense, a
Group is similar to a "directory" on a filesystem.

Resources represent the main data of interest for the Registry. In the
filesystem analogy, these would be the "files". A Resource exist under a
single Group and will have content (a document) associated with it. This
specification places no restriction on the type of content in the Resource.

This specification defines a set of common metadata that can appear on both
Groups and Resources, and allows for Registry (domain-specific) extensions to
be added.

The following 3 diagrams show (from left to right): 1) the core concepts of
the Registry in its most basic form, 2) a Registry concept model with multiple
types of Groups/Resources, and 3) a concrete sample usage of Registry that
includes an extension attribute on "Message Definitions" that is a reference
to a "Schema" document - all within the same Registry instance:

<img src="./xregbasicmodel.png"
 height="300">&nbsp;&nbsp;&nbsp;<img
 src="./xregfullmodel.png" height="300">&nbsp;&nbsp;&nbsp;<img
 src="./sample.png" height="300">

For easy reference, the JSON serialization of a Registry adheres to this form:

``` text
{
  "specVersion": "STRING",
  "id": "STRING",
  "name": "STRING", ?
  "epoch": UINTEGER,
  "self": "URL",
  "description": "STRING", ?
  "documentation": "URL", ?
  "labels": { "STRING": "STRING" * }, ?

  "model": {                            # Only if inlined
    "schemas": [ "STRING" * ], ?        # Available schema formats
    "attributes": {                     # Registry level extensions
      "STRING": {                       # Attribute name (case sensitive)
        "name": "STRING",               # Same as attribute's key
        "type": "TYPE",                 # string, decimal, array, object, ...
        "description": "STRING", ?
        "enum": [ VALUE * ], ?          # Array of scalar values of type "TYPE"
        "strict": BOOLEAN, ?            # Just "enum" values or not.Default=true
        "required": BOOLEAN, ?          # Default: false, from a CLI POV?

        "item": {                       # If "type" above is non-scalar
          "attributes": { ... } ?       # If "type" above is object
          "type": "TYPE", ?             # Type of this item,default is "object"
          "item": { ... } ?             # If this item "type" is map or array
        } ?

        "ifValue": {                    # If "type" is scalar
          VALUE: {                      # Possible attribute value
            "siblingAttributes": { ... } # See "attributes" above
          } *
        } ?
      } *
    },

    "groups": {
      "STRING": {                       # Key=plural name, e.g. "endpoints"
        "plural": "STRING",             # e.g. "endpoints"
        "singular": "STRING",           # e.g. "endpoint"
        "attributes": { ... }, ?        # See "attributes" above

        "resources": {
          "STRING": {                   # Key=plural name, e.g. "definitions"
            "plural": "STRING",         # e.g. "definitions"
            "singular": "STRING",       # e.g. "definition"
            "versions": UINTEGER ?      # Num Vers(>=0). Default=1, 0=unlimited
            "versionId": BOOLEAN, ?     # Supports client specified Version IDs
            "latest": BOOLEAN, ?        # Supports client "latest" selection
            "hasDocument": BOOLEAN, ?   # Has a separate document. Default=true
            "attributes": { ... } ?     # See "attributes" above
          } *
        } ?
      } *
    } ?
  } ?

  # Repeat for each Group type
  "GROUPsUrl": "URL",                              # e.g. "endpointsUrl"
  "GROUPsCount": INT                               # e.g. "endpointsCount"
  "GROUPs": {                                      # Only if inlined
    "ID": {                                        # Key=the Group id
      "id": "STRING",                              # The Group ID
      "name": "STRING", ?
      "epoch": UINTEGER,
      "self": "URL",
      "description": "STRING", ?
      "documentation": "URL", ?
      "labels": { "STRING": "STRING" * }, ?
      "format": "STRING", ?
      "createdBy": "STRING", ?
      "createdOn": "TIME", ?
      "modifiedBy": "STRING", ?
      "modifiedOn": "TIME", ?

      # Repeat for each Resource type in the Group
      "RESOURCEsUrl": "URL",                       # e.g. "definitionsUrl"
      "RESOURCEsCount": INT,                       # e.g. "definitionsCount"
      "RESOURCEs": {                               # Only if inlined
        "ID": {                                    # The Resource id
          "id": "STRING",
          "name": "STRING", ?
          "epoch": UINTEGER,
          "self": "URL",
          "latestVersionId": "STRING",
          "latestVersionUrl": "URL",
          "description": "STRING", ?
          "documentation": "URL", ?
          "labels": { "STRING": "STRING" * }, ?
          "format": "STRING", ?
          "createdBy": "STRING", ?
          "createdOn": "TIME", ?
          "modifiedBy": "STRING", ?
          "modifiedOn": "TIME", ?

          "RESOURCEUrl": "URL", ?                  # If not local
          "RESOURCE": { Resource contents }, ?     # If inlined & JSON
          "RESOURCEBase64": "STRING", ?            # If inlined & ~JSON

          "versionsUrl": "URL",
          "versionsCount": INT,
          "versions": {                            # Only if inlined
            "ID": {                                # The Version id
              "id": "STRING",
              "name": "STRING", ?
              "epoch": UINTEGER,
              "self": "URL",
              "description": "STRING", ?
              "documentation": "URL", ?
              "labels": { "STRING": "STRING" * }, ?
              "format": "STRING", ?
              "createdBy": "STRING", ?
              "createdOn": "TIME", ?
              "modifiedBy": "STRING", ?
              "modifiedOn": "TIME", ?

              "RESOURCEUrl": "URL", ?              # If not local
              "RESOURCE": { Resource contents }, ? # If inlined & JSON
              "RESOURCEBase64": "STRING" ?         # If inlined & ~JSON
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
and `+` means the preceding attribute MUST appear at least once. The presence
of the `#` character means the remaining portion of the line is a comment.

Use of the words `GROUP` and `RESOURCE` are meant to represent the singular
form of a Group and Resource type being used. While `GROUPs` and `RESOURCEs`
are the plural form of those respective types.

The following are used to denote data types:
- `ARRAY` - an ordered set of values whose values are all of the same data
   type - one of the types listed here
- `BOOLEAN` - case sensitive `true` or `false`
- `DECIMAL` - number (integer or floating point)
- `INT` - signed integer
- `MAP` - set of key/value pairs, where the key MUST be of type string
- `OBJECT` - a nested entity made up of a set of attributes of these data types
- `STRING` - sequence of Unicode characters
- `TIME` - an [RFC3339](https://tools.ietf.org/html/rfc3339) timestamp
- `UINTEGER` - unsigned integer
- `URI` - absolute URI as defined in [RFC 3986 Section
  4.3](https://tools.ietf.org/html/rfc3986#section-4.3)
- `URI-Reference` - URI-reference as defined in [RFC 3986
  Section 4.1](https://tools.ietf.org/html/rfc3986#section-4.1)
- `URI-Template` - ...
- `URL` - URL as defined in
  [RFC 1738](https://datatracker.ietf.org/doc/html/rfc1738)
- `TYPE` - one of the above data type values in lower case (`array`, `boolean`,
  `decimal`, `integer`, `map`, `object`, `string`, `time`, `uinteger`, `uri`,
  `urireference`, `uritemplate`, `url` )

TODO: which uritemplate language?

### Terminology

This specification defines the following terms:

#### Group

An entity that acts as a collection of related Resources.

#### Registry

An implementation of this specification. Typically, the implementation would
include model specific Groups, Resources and extension attributes.

#### Resource

A Resource is typically the main entity that is stored within a Registry
Service. It MAY be versioned and grouped as needed.

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

Unless otherwise noted, all attributes and extensions MUST be mutable and MUST
be one of the data types defined in the
[Notational Conventions](#notational-conventions) section. In other words, one
of: array, boolean, decimal, map, object, string, time, uinteger, uri,
urireference, uritempalte, url.

Implementations of this specification MAY define additional (extension)
attributes. However they MUST adhere to the following rules:

- they MUST be defined as part of the [Registry Model](#registry-model)
- the presence of an undefined attribute in a request MUST generate an error
- they MUST NOT use the name of an attribute defined by this specification,
  regardless of which entity the attribute is defined for. In other words,
  a spec defined attribute for GROUPs can not be reused as an extension for
  a RESOURCE
- it is RECOMMENDED that extension attributes on different objects not use the
  same name unless they have the exact same semantic meaning
- their names MUST be between 1 and 63 characters in length
- their names MUST only contain alphanumeric characters (`[a-zA-Z0-9]`) or an
  underscore (`_`) and MUST NOT start with a digit (`[0-9]`)
- it is STRONGLY RECOMMENDED that they be named in such a way as to avoid
  potential conflicts with future Registry specification attributes. For
  example, use of a model (or domain) specific prefix SHOULD be used
- they MUST differ from sibling attributes irrespective of case. This avoids
  potential conflicts if the attributes are serialized in a case-insensitive
  situation, such as HTTP headers
- for case sensitive serializations, it is RECOMMENDED that attribute names
  be defined in camelCase and acronyms have only their first letter
  capitalized. For example, `Id` not `ID`
- in situations where an attribute is serialized in a case-sensitive situation,
  then the case specified by this specification, or the defining extension
  specification, MUST be adhere to
- for STRING attributes, and empty string is a valid value and MUST NOT be
  treated the same as an attribute with no value (or absence of the attribute)
- the string serialization of the attribute name and its value MUST NOT exceed
  4096 bytes. This is to ensure that it can appear in an HTTP header without
  exceeding implementation limits (see
  [RFC6265/Limits](https://datatracker.ietf.org/doc/html/rfc6265#section-6.1)).
  In cases where larger amounts of data is needed, it is RECOMMENDED that
  an attribute (defined as a URL) be defined that references a separate
  document. For example, `documentation` can be considered such an attribute
  for `description`

#### Common Attributes

The following attributes are used by one or more entities defined by this
specification. They are defined here once rather than repeating them
throughout the specification.

For easy reference, the serialization these attributes adheres to this form:
- `"id": "STRING"`
- `"name": "STRING"`
- `"epoch": UINTEGER`
- `"self": "URL"`
- `"description": "STRING"`
- `"documentation": "URL"`
- `"labels": { "STRING": "STRING" * }`
- `"format": "STRING"`
- `"createdBy": "STRING"`
- `"createdOn": "TIME"`
- `"modifiedBy": "STRING"`
- `"modifiedOn": "TIME"`

The definition of each attribute is defined below.

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
  - if present, MUST be non-empty
- Examples:
  - `My Endpoints`

#### `epoch`

- Type: Unsigned Integer
- Description: A numeric value used to determine whether an entity has been
  modified. Each time the associated entity is updated, this value MUST be
  set to a new value that is greater than the current one.
  Note, this attribute is most often managed by the Registry itself.
  Note, if a new Version of a Resource is created that is based on
  existing Version of that Resource, then the new Version's `epoch` value MAY
  be reset (e.g. to zero) since the scope of its values is the Version and not
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
  - None
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

#### `labels`

- Type: Map of name/value string pairs
- Description: A mechanism in which additional metadata about the entity can
  be stored without changing the schema of the entity
- Constraints:
  - MUST be a map of zero or more name/value string pairs
  - each name MUST be a non-empty string consisting of only lowercase
    alphanumeric characters (`[a-zA-Z0-9]`), `-`, `_` or a `.`; be no longer
    than 63 characters; start with an alphanumeric character and be unique
    within the scope of this map
  - Values MAY be empty strings
  - when serialized as an HTTP header, each "name" MUST appear as a separate
    HTTP header prefixed with `xRegistry-labels-` and the header value
    MUST be the label's "value". See [HTTP Header Values](#http-header-values)
- Examples:
  - `"labels": { "owner": "John", "verified": "" }` when in the HTTP body
  - `xRegistry-labels-owner: John` <br>
    `xRegistry-labels-verified:`  when in HTTP headers

Note: HTTP header values can be empty strings but some client-side tooling
might make it challenging to produce them. For example, `curl` requires
the header to be specified as `-HxRegistry-labels-verified;` - notice the
semi-colon(`;`) is used instead of colon(`:`). So, this might be something
to consider when choosing to use labels that can be empty strings.

#### `format`

- Type: String
- Description: The name of the specification that defines the Resource
  stored in the registry. Often it is difficult to unambiguously determine
  what a Resource is via simple inspect of its serialization. This attribute
  provides a mechanism by which it can be determined without examination of
  the Resource at all
- Constraints:
  - if present, MUST be a non-empty string of the form `SPEC[/VERSION]`,
    where `SPEC` is the non-empty string name of the specification that
    defines the Resource. An OPTIONAL `VERSION` value SHOULD be included if
    there are multiple versions of the specification available
  - for comparison purposes, this attribute MUST be considered case sensitive
  - If a `VERSION` is specified at the Group level, all Resources within that
    Group MUST have a `VERSION` value that is at least as precise as its
    Group, and MUST NOT expand it. For example, if a Group had a
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
  - if present, MUST be non-empty
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
  - if present, MUST be non-empty
  - MUST be a read-only attribute in API view
  - upon creation of a new entity, this attribute MUST match the `createdBy`
    attribute's value
- Examples:
  - `John Smith`
  - `john.smith@example.com`

#### `modifiedOn`

- Type: Timestamp
- Description: The date/time of when the entity was last updated
- Constraints:
  - MUST be a [RFC3339](https://tools.ietf.org/html/rfc3339) timestamp
  - MUST be a read-only attribute in API view
  - upon creation of a new entity, this attribute MUST match the `createdOn`
    attribute's value
- Examples:
  - `2030-12-19T06:00:00Z`

---

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
- `GROUPs` is a Group name (plural). e.g. `endpoints`
- `gID` is the `id` of a single Group
- `RESOURCEs` is the type of Resource (plural). e.g. `definitions`
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

---

#### Registry Collections

Registry collections (`GROUPs`, `RESOURCEs` and `versions`) that are defined
by the [Registry Model](#registry-model) MUST be serialized according to the
rules defined below.

The serialization of a collection is done as 3 attributes and adheres to this
form:

``` text
"COLLECTIONsUrl": "URL, ?
"COLLECTIONsCount": UINTEGER, ?
"COLLECTIONs": {
  # Map of entities in the collection, key is the "id" of each entity
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
- the `id` for each entity in the collection MUST be unique within the scope
  of the collection
- the specifics of whether each attribute is REQUIRED or OPTIONAL will be
  based whether document or API view is being used - see below

When the `COLLECTIONs` attribute is expected to be present in the
serialization, but the number of entities is zero, it MUST still be included
as an empty map.

The set of entities that are part of the `COLLECTIONs` attribute is a
point-in-time view of the Registry. There is no guarantee that a future `GET`
to the `COLLECTIONsUrl` will return the exact same collection since the
contents of the Registry might have changed.

Since collections could be too large to retrieve in one request, when
retrieving a collection the client MAY request a subset by using the
[pagination specification](../pagination/spec.md). Likewise, the server
MAY choose to return a subset of the collection using the same mechanism
defined in that specification even if the request didn't use pagination.
The pagination specification MUST only be used when the request is directed at
a collection, not at a stand-alone entity (such as the root of the Registry,
or at an individual Group, Resource or Version).

In the remainder of the specification, the presence of the `Link` HTTP header
indicates the use of the [pagination specification](../pagination/spec.md)
MAY be used for that API.

The requirements on the presence of the 3 `COLLECTIONs` attributes varies
between Document and API views, and is defined below:

#### Document view

In document view:
- `COLLECTIONsUrl` and `COLLECTIONsCount` are OPTIONAL
- `COLLECTIONs` is REQUIRED

#### API view

In API view:
- `COLLECTIONsUrl` and `COLLECTIONsCount` are REQUIRED
- `COLLECTIONs` is OPTIONAL and MUST only be included in a response if the
  request included the [`inline`](#inlining) flag indicating that thisi
  collection's values are to be returned
- all 3 attributes MUST be read-only and MUST NOT be updated directly via
  an API call. Rather, to modify them the collection specific APIs MUST be used
  (e.g. an HTTP `POST` to the collection's URL to add a new entity). The
  presence of the collection attributes in a write operation MUST be silently
  ignored by the server

---

### Registry Entity

The Registry entity represents the root of a Registry and is the main
entry-point for traversal and discovery.

The serialization of the Registry entity adheres to this form:

``` text
{
  "specVersion": "STRING",
  "id": "STRING",
  "name": "STRING", ?
  "epoch": UINTEGER,
  "self": "URL",
  "description": "STRING", ?
  "documentation": "URL", ?
  "labels": { "STRING": "STRING" * }, ?

  "model": { Registry model } ?       # Only if  "?model" is present

  # Repeat for each Group type
  "GROUPsUrl": "URL",                 # e.g. "endpointsUrl"
  "GROUPsCount": INT                  # e.g. "endpointsCount"
  "GROUPs": { GROUPs collection } ?   # Only if inlined
}
```

The Registry entity includes the following common attributes:
- [`id`](#id) - REQUIRED
- [`name`](#name) - OPTIONAL
- [`epoch`](#epoch) - REQUIRED in responses, otherwise OPTIONAL
- [`self`](#self) - REQUIRED in responses, OPTIONAL in requests and in
  document view
- [`description`](#description) - OPTIONAL
- [`documentation`](#documentation) - OPTIONAL
- [`labels`](#labels) - OPTIONAL

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
- Description: A description of the features, extension attributes, Groups and
  Resources supported by this Registry. See [Registry Model](#registry-model)
- Constraints:
  - OPTIONAL
  - MUST NOT be included in responses unless requested
  - MUST be included in responses if requested
  - SHOULD be included in document view when the model is not known in advance
  - MUST be a read-only attribute, use the `/model` API to update

**`GROUPs` collections**
- Type: Set of [Registry Collections](#registry-collections)
- Description: A list of Registry collections that contain the set of Groups
  supported by the Registry
- Constraints:
  - REQUIRED in responses, SHOULD NOT be included in requests
  - REQUIRED in document view
  - MUST be a read-only attribute in API view
  - if present, MUST include all nested Group Collection types

#### Retrieving the Registry

To retrieve the Registry, its metadata attributes and Groups, an HTTP `GET`
MAY be used.

The request MUST be of the form:

``` text
GET /[?model&specVersion=...&inline=...&filter=...]
```

The following query parameters MUST be supported by servers:
- `model`<br>
  The presence of this OPTIONAL query parameter indicates that the request is
  asking for the Registry model to be included in the response. See
  [Registry Model](#registry-model) for more information
- `specVersion`<br>
  The presence of this OPTIONAL query parameter indicates that the response
  MUST adhere to the xRegistry specification version specified. If the
  version is not supported then an error MUST be generated. Note that this
  query parameter MAY be included on any API request to the server not just the
  root of the Registry.
- `inline` - See [inlining](#inlining) for more information
- `filter` - See [filtering](#filtering) for more information

A successful response MUST be of the form:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "specVersion": "STRING",
  "id": "STRING",
  "name": "STRING", ?
  "epoch": UINTEGER,
  "self": "URL",
  "description": "STRING", ?
  "documentation": "URL", ?
  "labels": { "STRING": "STRING" * }, ?

  "model": { Registry model }, ?      # Only if  "?model" is present

  # Repeat for each Group type
  "GROUPsUrl": "URL",                 # e.g. "endpointsUrl"
  "GROUPsCount": INT                  # e.g. "endpointsCount"
  "GROUPs": { GROUPs collection } ?   # Only if inlined
}
```

**Examples:**

Retrieve a Registry that has 2 types of Groups (endpoints and schemaGroups):

``` text
GET /

---

HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "specVersion": "0.5",
  "id": "987654321",
  "epoch": 1,
  "self": "https://example.com/",

  "endpointsUrl": "https://example.com/endpoints",
  "endpointsCount": 42,

  "schemaGroupsUrl": "https://example.com/schemaGroups",
  "schemaGroupsCount": 1
}
```

Another example where:
- the request asks for the model to included in the response
- the "endpoints" Group has one extension attribute defined
- the request asks for the "schemaGroups" Group to be inlined in the response:

``` text
GET /?model&inline=schemaGroups

---

HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "specVersion": "0.5",
  "id": "987654321",
  "epoch": 1,
  "self": "https://example.com/",

  "model": {
    "schemas": [ "jsonSchema/2020-12" ],
    "groups": {
      "endpoints": {
        "plural": "endpoints",
        "singular": "endpoint",
        "attributes": {
          "shared": {
            "name": "shared",
            "type": "boolean",
            "required": false
          }
        },

        "resources": {
          "definitions": {
            "plural": "definitions",
            "singular": "definition",
            "versions": 1
          }
        }
      },
      "schemaGroups": {
        "plural": "schemaGroups",
        "singular": "schemaGroup",

        "resources": {
          "schemas": {
            "plural": "schemas",
            "singular": "schema",
            "versions": 1
          }
        }
      }
    }
  },

  "endpointsUrl": "https://example.com/endpoints",
  "endpointsCount": 42,

  "schemaGroupsUrl": "https://example.com/schemaGroups",
  "schemaGroupsCount": 1,
  "schemaGroups": {
    "mySchemas": {
      "id": "mySchemas",
      # Remainder of schemaGroup is excluded for brevity
    }
  }
}
```

#### Updating the Registry

To update a Registry's metadata attributes, an HTTP `PUT` MAY be used.

The request MUST be of the form:

``` text
PUT /
Content-Type: application/json; charset=utf-8

{
  "id": "STRING", ?
  "epoch": UINTEGER, ?
  "name": "STRING", ?
  "description": "STRING", ?
  "documentation": "URL" ?
  "labels": { "STRING": "STRING" * } ?
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
- complex attributes that have nested values (e.g. `labels`) MUST be specified
  in their entirety
- if `epoch` is present then the server MUST reject the request if the
  Registry's current `epoch` value is different from the one in the request
- the request SHOULD NOT include the `model` and if it does, then the
  server MUST silently ignore it. Updating the model MUST only be done via the
  `/model` API. See [Updating the Registry Model](#updating-the-registry-model)
  for more information

A successful response MUST include the same content that an HTTP `GET`
on the Registry would return, and be of the form:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "specVersion": "STRING",
  "id": "STRING",
  "name": "STRING", ?
  "epoch": UINTEGER,
  "self": "URL",
  "description": "STRING", ?
  "documentation": "URL", ?
  "labels": { "STRING": "STRING" * }, ?

  # Repeat for each Group type
  "GROUPsUrl": "URL",
  "GROUPsCount": INT
}
```

**Examples:**

Updating a Registry's metadata

``` text
PUT /
Content-Type: application/json; charset=utf-8

{
  "id": "987654321",
  "name": "My Registry",
  "description": "An even cooler registry!"
}

---

HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "specVersion": "0.5",
  "id": "987654321",
  "name": "My Registry",
  "epoch": 2,
  "self": "https://example.com/",
  "description": "An even cooler registry!",

  "endpointsUrl": "https://example.com/endpoints",
  "endpointsCount": 42,

  "schemaGroupsUrl": "https://example.com/schemaGroups",
  "schemaGroupsCount": 1
}
```

---

### Registry Model

The Registry model defines the extension attributes, constraints on the
specification defined attributes, Groups and Resources supported by the
Registry Service. This information will usually be used by tooling that does
not have advance knowledge of the type of data stored within the Registry.

Typically, the attributes defined within the model are extensions to the
specification, however, specification defined attributes MAY be included as
well in order to constrain their definitions. See `attributes."STRING"` below
for more information.

The Registry model can be retrieved two ways:

1. as a stand-alone entity. This is useful when management of the Registry's
   model is needed independent of the entities within the Registry.
   See [Retrieving the Registry Model](#retrieving-the-registry-model) for
   more information
2. as part of the Registry itself. This is useful when it is desirable to
   view the entire Registry as a single document - such as an "export" type
   of scenario. See the [Retrieving the Registry](#retrieving-the-registry)
   section (the `model` query parameter) for more information on this option

Regardless of how the model is retrieved, the overall format is as follows:

``` text
{
  "schemas": [ "STRING" * ], ?         # Available schema formats
  "attributes": {                      # Registry level extensions
    "STRING": {                        # Attribute name
      "name": "STRING",                # Same as attribute's key
      "type": "TYPE",                  # boolean, string, array, object, ...
      "description": "STRING",
      "enum": [ VALUE * ], ?           # Array of values of type "TYPE"
      "strict": BOOLEAN, ?             # Just "enum" values or not. Default=true
      "required": BOOLEAN, ?           # Default: false

      "item": {                        # If "type" above is non-scalar
        "attributes": { ... } ?        # If "type" above object
        "type": "TYPE", ?              # Type of this item,default is "object"
        "item": { ... } ?              # If this item "type" is map or array
      } ?

      "ifValue": {                     # If "type" is scalar
        VALUE: {
          "siblingAttributes": { ... } # Siblings to this "attribute"
        } *
      }
    } *
  },
  "groups": {
    "STRING": {                        # Key=plural name, e.g. "endpoints"
      "plural": "STRING",              # e.g. "endpoints"
      "singular": "STRING",            # e.g. "endpoint"
      "attributes": { ... }, ?         # See "attributes" above

      "resources": {
        "STRING": {                    # Key=plural name, e.g. "definitions"
          "plural": "STRING",          # e.g. "definitions"
          "singular": "STRING",        # e.g. "definition"
          "versions": UINTEGER, ?      # Num Vers(>=0). Default=1, 0=unlimited
          "versionId": BOOLEAN, ?      # Supports client specified Version IDs
          "latest": BOOLEAN ?          # Supports client "latest" selection
          "hasDocument": BOOLEAN, ?    # Has no separate document. Default=true
          "attributes": { ... } ?      # See "attributes" above
        } *
      } ?
    } *
  } ?
}
```

The following describes the attributes of Registry model:
- `schemas`
  - A list of schema formats that that Registry model can be returned. Each
    value MUST be a schema document format name (e.g. `jsonSchema/2020-12`),
    and SHOULD be of the form `NAME[/VERSION]`
  - Type: String
  - OPTIONAL
  - MUST be a read-only attribute in API view
- `attributes`
  - The set of extension, or constrained specification-defined, attributes
    defined for the indicated level of the Registry
  - Type: Map where each attribute's name is the key of the map
  - OPTIONAL
- `attributes."STRING"`
  - The name of the attribute being defined. If this entry is constraining
    a specification defined attribute then it MUST match the existing
    attribute's name exactly (include its case) and MUST only constrain the
    definition of the attribute, not expand it. For example:
    - defining a fixed list of STRING values via an `enum` - valid
    - changing a STRING attribute to a TIMESTAMP - valid
    - changing a REQUIRED attribute to be OPTIONAL - valid
    - changing a OPTIONAL attribute to be REQUIRED - invalid
    - changing a STRING attribute to a DECIMAL - invalid
  - Type: String
  - REQUIRED

TODO: check the above example list

- `attributes."STRING".name`
  - The name of the attribute. MUST be the same as the key used in the owning
    `attributes` attribute.
  - Type: String
  - REQUIRED
- `attributes."STRING".type`
  - The "TYPE" of the attribute being defined. MUST be one of the data types
    (in lower case) defined in [Attributes and
    Extensions](#attributes-and-extensions)
  - Type: TYPE
  - REQUIRED
- `attributes."STRING".description
  - A human readable description of the attribute
  - Type: String
  - OPTIONAL
- `attributes."STRING".enum`
  - A list of possible values for this attribute. Each item in the array MUST
    be of type defined by `type`. When not specified, or an empty array, there
    are no restrictions on the value set of this attribute. See the `strict`
    attribute below
  - Type: Array
  - OPTIONAL
- `attributes."STRING".strict`
  - Indicates whether the attribute restricts its values to just the array of
    values specified in `enum` or not. A value of `true` means that any
    values used that is not part of the `enum` set MUST generate an error.
    When not specified the default value is `true`. This attribute has no
    impact when `enum` is absent or an empty array
  - Type: Boolean
  - OPTIONAL
- `attributes."STRING".required`
  - Indicates whether this attribute is a REQUIRED attribute or not. When not
    specified the default value is `false`
  - Type: Boolean
  - OPTIONAL

- `attributes."STRING".item`
  - Defines the nested resources that this attribute references.
    This attribute MUST only be used when the `type` value is non-scalar
  - Type: Object
  - REQUIRED when `type` is non-scalar
- `attributes."STRING".item.attributes`
  - This attribute MUST only be used when the `type` value is `object`. This
    contains the list of attributes defined as part of a nested resource
  - Type: Object, see `attributes` above
  - REQUIRED when `type` is `object`, otherwise it MUST NOT be present
- `attributes."STRING".item.type`
  - The "TYPE" of this nested resource. Note, this attribute MAY be absent if
    owning attribute's `type` is `object` as that is its default value.
  - Type: TYPE
  - REQUIRED if the nested resource is not `object`, otherwise it MAY be
    present
- `attributes."STRING".item.item`
  - See `attributes."STRING".item` above.
  - REQUIRED when `type` is non-scalar

- `attributes."STRING".ifValue`
  - This attribute can be used to conditionally include additional attribute
    definitions to the list based on the value of the current attribute.
    If the value of this attribute matches the `ifValue` (case sensitive)
    then the `siblingAttributes` MUST be included in the model as siblings
    to this attribute.
    If `enum` is not empty and `strict` is `true` then this map MUST NOT
    contain any value that is not specified in the `enum` array
  - Type: Map where each value of the attribute is the key of the map
  - OPTIONAL

- `groups`
  - The set of Groups supported by the Registry
  - Type: Map where the key MUST be the plural name of the Group
  - REQUIRED if there are any Groups defined for the Registry
- `groups.singular`
  - The singular name of a Group. e.g. `endpoint`
  - Type: String
  - REQUIRED
  - MUST be unique across all Groups in the Registry
  - MUST be non-empty and MUST be a valid attribute name
- `groups.plural`
  - The plural name of a Group. e.g. `endpoints`
  - Type: String
  - REQUIRED
  - MUST be unique across all Groups in the Registry
  - MUST be non-empty and MUST be a valid attribute name
- `groups.attributes`
  - see `attributes` above

- `groups.resources`
  - The set of Resource entities defined for the Group
  - Type: Map where the key MUST be the plural name of the Resource
  - REQUIRED if there are any Resources defined for the Group
- `groups.resources.singular`
  - The singular name of the Resource. e.g. `definition`
  - Type: String
  - REQUIRED
  - MUST be non-empty and MUST be a valid attribute name
  - MUST be unique within the scope of its owning Group
- `groups.resources.plural`
  - The plural name of the Resource. e.g. `definitions`
  - Type: String
  - REQUIRED
  - MUST be non-empty and MUST be a valid attribute name
  - MUST be unique within the scope of its owning Group
- `groups.resources.versions`
  - Number of Versions per Resource that will be stored in the Registry
  - Type: Unsigned Integer
  - OPTIONAL
  - The default value is one (`1`), meaning only the latest Version will
    be stored
  - A value of zero (`0`) indicates there is no stated limit, and
    implementations MAY prune non-latest Versions at any time. Implementations
    MUST prune Versions by deleting the oldest Version (based on creation
    times) first
- `groups.resources.versionId`
  - Indicates whether support for client-side selection of a Version's `id` is
    supported
  - Type: Boolean (`true` or `false`, case sensitive)
  - OPTIONAL
  - The default value is `true`
  - A value of `true` indicates the client MAY specify the `id` of a Version
    during its creation process
- `groups.resources.latest`
  - Indicates whether support for client-side selection of the "latest"
    Version of a Resource is supported
  - Type: Boolean (`true` or `false`, case sensitive)
  - OPTIONAL
  - The default value is `true`
  - A value of `true` indicates the client MAY select the latest Version of
    a Resource via one of the methods described in this specification
- `groups.resources.hasDocument`
  - Indicates whether or not this Resource can have a document associated with
    it. If `false` then the xRegistry metadata becomes the "document". Meaning,
    an HTTP `GET` to the Resource's URL or its `?meta` URL will both return
    the same information in the HTTP body. An HTTP `GET` to the Resource
    without a `?meta` query parameter in the request MUST still include the
    `xRegistry-` HTTP headers for consistency.
    A value of `true` does not mean that these Resources are
    guaranteed to have a non-empty document, and an HTTP `GET` to the Resource
    MAY return an empty HTTP body.
  - Type: Boolean (`true` or `false`, case sensitive)
  - OPTIONAL
  - The default value if `true`
  - A value of `true` indicates that the Resource supports a separate document
    to be associated with the Resource.
- `groups.resources.attributes`
  - see `attributes` above
  - Note that Resources themselves don't actually have extensions, rather
    the extensions would technically be on the Versions, but would appear
    on the Resource when asking for the latest version

#### Retrieving the Registry Model

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

{
  "attributes": {
    "STRING": {
      "name": "STRING",
      "type": "TYPE",
      "description": "STRING", ?
      "enum": [ VALUE * ], ?
      "strict": BOOLEAN, ?
      "required": BOOLEAN, ?
      "attributes": { ... }, ?               # Nested attributes
      "item": { ... }, ?                     # Nested resource

      "ifValue": {
        VALUE: {
          "siblingAttributes": { ... }
        } *
      } ?
    } *
  },

  "groups": {
    "STRING": {
      "plural": "STRING",
      "singular": "STRING",
      "attributes": { ... }, ?               # See "attributes" above

      "resources": {
        "STRING": {
          "plural": "STRING",
          "singular": "STRING",
          "versions": UINTEGER ?
          "versionId": BOOLEAN, ?
          "latest": BOOLEAN, ?
          "hasDocument": BOOLEAN, ?
          "attributes": { ... } ?            # See "attributes" above
        } *
      } ?
    } *
  } ?
}
```

**Examples:**

Retrieve a Registry model that has one extension attribute on the
"endpoints" Group, and supports returning the schema of the Registry
as JSON Schema:

``` text
GET /model

---

HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "schemas": [ "jsonSchema/2020-12" ],
  "groups": {
    "endpoints": {
      "plural": "endpoints",
      "singular": "endpoint",
      "attributes": {
        "shared": {
          "name": "shared",
          "type": "boolean",
          "required": false
        }
      },

      "resources": {
        "definitinons": {
          "plural": "definitions",
          "singular": "definition",
          "versions": 1
        }
      }
    }
  }
}
```

#### Updating the Registry Model

To update the Registry Model, an HTTP `PUT` MAY be used.

The request MUST be of the form:

``` text
PUT /model
Content-Type: application/json; charset=utf-8

{
  "attributes": {
    "STRING": {
      "name": "STRING",
      "type": "TYPE",
      "description": "STRING", ?
      "enum": [ VALUE * ], ?
      "strict": BOOLEAN, ?
      "required": BOOLEAN, ?
      "attributes": { ... }, ?                    # Nested attributes
      "item": { ... }, ?                          # Nested resource

      "ifValue": {
        VALUE: {
          "siblingAttributes": { ... }
        } *
      } ?
    } *
  },

  "groups": {
    "STRING": {
      "plural": "STRING",
      "singular": "STRING",
      "attributes": { ... }, ?                    # See "attributes" above

      "resources": {
        "STRING": {
          "plural": "STRING",
          "singular": "STRING",
          "versions": UINTEGER ?
          "versionId": BOOLEAN, ?
          "latest": BOOLEAN, ?
          "hasDocument": BOOLEAN, ?
          "attributes": { ... } ?                 # See "attributes" above
        } *
      } ?
    } *
  } ?
}
```

Where:
- the HTTP body MUST contain the full representation of the Registry model's
  mutable attributes
- attributes not present in the request, or present with a value of `null`,
  MUST be interpreted as a request to delete the attribute

The deletion of a Group or Resource from the model MUST change the underlying
datastore of the implementation to match the request.

A successful response MUST include a full representation of the Registry model
and be of the form:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "schemas": [ "STRING" * ], ?
  "attributes": {
    "STRING": {
      "name": "STRING",
      "type": "TYPE",
      "description": "STRING", ?
      "enum": [ VALUE * ], ?
      "strict": BOOLEAN, ?
      "required": BOOLEAN, ?
      "attributes": { ... }, ?
      "item": { ... }, ?

      "ifValue": {
        VALUE: {
          "siblingAttributes": { ... }
        } *
      } ?
    } *
  },

  "groups": {
    "STRING": {
      "plural": "STRING",
      "singular": "STRING",
      "attributes": { ... }, ?

      "resources": {
        "STRING": {
          "plural": "STRING",
          "singular": "STRING",
          "versions": UINTEGER ?
          "versionId": BOOLEAN, ?
          "latest": BOOLEAN, ?
          "hasDocument": BOOLEAN, ?
          "attributes": { ... } ?
        } *
      } ?
    } *
  } ?
}
```

**Examples:**

Update a Registry's model to add a new Group type:

``` text
PUT /model
Content-Type: application/json; charset=utf-8

{
  "groups": {
    "endpoints": {
      "plural": "endpoints",
      "singular": "endpoint",
      "attributes": {
        "shared": {
          "name": "shared",
          "type": "boolean",
          "required": false
        }
      },

      "resources": {
        "definitions": {
          "plural": "definitions",
          "singular": "definition",
          "versions": 1
        }
      }
    },
    "schemaGroups": {
      "plural": "schemaGroups",
      "singular": "schemaGroup",

      "resources": {
        "schemas": {
          "plural": "schemas",
          "singular": "schema",
        }
      }
    }
  }
}

---

HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "schemas": [ "jsonSchema/2020-12" ],
  "groups": {
    "endpoints" {
      "plural": "endpoints",
      "singular": "endpoint",
      "attributes": {
        "shared": {
          "name": "shared",
          "type": "boolean",
          "required": false
        }
      },

      "resources": {
        "definitinons": {
          "plural": "definitions",
          "singular": "definition",
          "versions": 1
        }
      }
    },
    "schemaGroups": {
      "plural": "schemaGroups",
      "singular": "schemaGroup",

      "resources": {
        "schemas": {
          "plural": "schemas",
          "singular": "schema",
        }
      }
    }
  }
}
```

#### Retrieving the Registry Schema

Registries MAY support exposing their model using a well-defined schema
document format. The `model/schemas` attribute (discussed above) SHOULD expose
the set of schema formats available. To retrieve the mode in one of those
formats the following API can be used:

The request MUST be of the form:

``` text
GET /model?schema=STRING
```

Where:
- `STRING` is one of the valid `model.schema` values

A successful response MUST be of the form:

``` text
HTTP/1.1 200 OK
Content-Type: ...

...                          # Schema specific format
```

Where:
- the HTTP body MUST be a schema representation of the Registry model
  in the format requested by the `schema` query parameter
- if a `VERSION` is not specified as part of the `schema` query parameterthen
  the server MAY choose any schema version of the specified schema format.
  However, it is RECOMMENDED that the newest supported version be used

If the specified schema format is not supported then an HTTP `400 Bad Request`
error MUST be generated.

---

### Groups

Groups represent top-level entities in a Registry that typically act as a
collection mechanism for related Resources. However, it is worth noting that
Groups do not have to have Resources associated with them. It is possible to
have Groups be the main (or only) entity of a Registry. Each Group type MAY
have any number of Resource types within it. This specification does not
define how the Resources within a Group type are related to each other.

The serialization of a Group entity adheres to this form:

``` text
{
  "id": "STRING",
  "name": "STRING", ?
  "epoch": UINTEGER,
  "self": "URL",
  "description": "STRING", ?
  "documentation": "URL", ?
  "labels": { "STRING": "STRING" * }, ?
  "format": "STRING", ?
  "createdBy": "STRING", ?
  "createdOn": "TIME", ?
  "modifiedBy": "STRING", ?
  "modifiedOn": "TIME", ?

  # Repeat for each Resource type in the Group
  "RESOURCEsUrl": "URL",                    # e.g. "definitionsUrl"
  "RESOURCEsCount": INT,                    # e.g. "definitionsCount"
  "RESOURCEs": { RESOURCEs collection } ?   # If inlined
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
- [`labels`](#labels) - OPTIONAL
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

#### Retrieving a Group Collection

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
Link: <URL>;rel=next;count=INT ?

{
  "ID": {
    "id": "STRING",
    "name": "STRING", ?
    "epoch": UINTEGER,
    "self": "URL",
    "description": "STRING", ?
    "documentation": "URL", ?
    "labels": { "STRING": "STRING" * }, ?
    "format": "STRING", ?
    "createdBy": "STRING", ?
    "createdOn": "TIME", ?
    "modifiedBy": "STRING", ?
    "modifiedOn": "TIME", ?

    # Repeat for each Resource type in the Group
    "RESOURCEsUrl": "URL",                    # e.g. "definitionsUrl"
    "RESOURCEsCount": INT,                    # e.g. "definitionsCount"
    "RESOURCEs": { RESOURCEs collection } ?   # If inlined
  } *
}
```

**Examples:**

Retrieve all entities in the `endpoints` group:

``` text
GET /endpoints

---

HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
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

Notice that the `Link` HTTP header is present, indicating that there
is a second page of results that can be retrieved via the specified URL,
and that there are total of 100 items in this collection.

#### Creating or Updating Groups

Creating or updating Groups via HTTP MAY be done by using the HTTP `POST`
or `PUT` methods:
- `POST /GROUPs`
- `PUT  /GROUPs/gID`

The HTTP body in the `POST` variant MUST contain either a single Group
definition (as a JSON object), or a list of Group definitions (as a JSON
array). While the HTTP body in the `PUT` variant MUST contain a single Group
definition as a JSON object.

Each individual Group definition MUST adhere to the following:

``` text
{
  "id": "STRING", ?
  "name": "STRING", ?
  "epoch": UINTEGER, ?
  "description": "STRING", ?
  "documentation": "URL", ?
  "labels": { "STRING": "STRING" * }, ?
  "format": "STRING" ?
}
```

The following rules apply:
- for any one Group specified in the HTTP body, if the Group does not include
  an `id` attribute then the server MUST assign it a value that is unique
  across all entities in the Group, unless the `PUT` variant is used, in
  which case the `gID` value from the URL MUST be used
- for the `PUT` variant, if both a Group `id` and `gID` are present then they
  MUST be the same value
- an incoming request MUST NOT include duplicate Groups as specified by their
  `id` values
- if a Group already exists with a specified `id` then the processing of that
  Group MUST be interpreted as a request to update the existing Group.
  Otherwise, it MUST be interpreted as a request to create a new Group
- the `epoch` attribute is OPTIONAL and if present on a create request, MUST
  be silently ignored. For an update request, if it does not match the
  existing Group's `epoch` value then an error MUST be generated
- a request to update an existing Group MUST increment its `epoch` value
- the `createdBy`, `createdOn`, `modifiedBy` and `modifiedOn` attributes MUST
  be updated appropriated if they are supported by the server.
- a Group's definition MUST be a full representation of the Group's mutable
  attributes (including complex attributes). This means that any missing
  mutable attribute MUST be interpreted as a request to delete the attribute
- a request to update, or delete, a nested Resource collection or a read-only
  attribute MUST be silently ignored
- a request to update a mutable attribute with an invalid value MUST generate
  an error (this includes deleting a mandatory mutable attribute)
- any error during the processing of a Group definition MUST result in the
  entire HTTP request being rejected and no updates performed

A successful response MUST include the current representation of the Groups
created or updated in the same order and cardinality (single object vs array)
as the request.

Note that the response MUST NOT include any inlinable attributes (such as
any Registry nested collections).

If the request used the `PUT` variant, or it used the `POST` variant with
a JSON object (not array) in the HTTP body, and the request resulted in a new
Group being created, then a successful response MUST:
- include an HTTP `201 Created` response code
- include an HTTP `Location` header with a URL to the newly create Group, and
  MUST be the same as the Group's `self` attribute

otherwise an HTTP `200 OK` without an HTTP `Location` header MUST be returned.

Each individual Group in a successful response MUST adhere to the following:

``` text
{
  "id": "STRING",
  "name": "STRING", ?
  "epoch": UINTEGER,
  "self": "URL",
  "description": "STRING", ?
  "documentation": "URL", ?
  "labels": { "STRING": "STRING" * }, ?
  "format": "STRING", ?
  "createdBy": "STRING", ?
  "createdOn": "TIME", ?
  "modifiedBy": "STRING", ?
  "modifiedOn": "TIME", ?

  # Repeat for each Resource type in the Group
  "RESOURCEsUrl": "URL",                    # e.g. "definitionsUrl"
  "RESOURCEsCount": INT                     # e.g. "definitionsCount"
}
```

**Examples:**

New Group specified in the HTTP body:

``` text
POST /endpoints
Content-Type: application/json; charset=utf-8

{ GROUP definition }

---

HTTP/1.1 201 Created
Content-Type: application/json; charset=utf-8
Location: https://example.com/endpoints/456

{ GROUP456 definition }
```

Multiple Groups specified in the HTTP body:

``` text
POST /endpoints
Content-Type: application/json; charset=utf-8

[ { GROUP1 definition }, { GROUP2 definition } ]

---

HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Location: https://example.com/endpoints/123

[ { GROUP1 definition }, { GROUP2 definition } ]
```

Targeted request to a create a specific Group `id`:

``` text
PUT /endpoints/123
Content-Type: application/json; charset=utf-8

{ GROUP123 definition }

---

HTTP/1.1 201 Created
Content-Type: application/json; charset=utf-8
Location: https://example.com/endpoints/123

{ GROUP123 definition }
```

#### Retrieving a Group

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

{
  "id": "STRING",
  "name": "STRING", ?
  "epoch": UINTEGER,
  "self": "URL",
  "description": "STRING", ?
  "documentation": "URL", ?
  "labels": { "STRING": "STRING" * }, ?
  "format": "STRING", ?
  "createdBy": "STRING", ?
  "createdOn": "TIME", ?
  "modifiedBy": "STRING", ?
  "modifiedOn": "TIME", ?

  # Repeat for each Resource type in the Group
  "RESOURCEsUrl": "URL",                     # e.g. "definitionsUrl"
  "RESOURCEsCount": INT,                     # e.g. "definitionsCount"
  "RESOURCEs": { RESOURCEs collection } ?    # If inlined
}
```

**Examples:**

Retrieve a single `endpoints` Group:

``` text
GET /endpoints/123

---

HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "id": "123",
  "name": "myEndpoint",
  "epoch": 1,
  "self": "https://example.com/endpoints/123",

  "definitionsUrl": "https://example.com/endpoints/123/definitions",
  "definitionsCount": 5
}
```

#### Deleting Groups

To delete a single Group, an HTTP `DELETE` MAY be used.

The request MUST be of the form:

``` text
DELETE /GROUPs/gID[?epoch=UINTEGER]
```

Where:
- the request body SHOULD be empty

The following query parameters MUST be supported by servers:
- `epoch`<br>
  The presence of this query parameter indicates that the server MUST check
  to ensure that the `epoch` value matches the Group's current `epoch` value
  and if it differs then an error MUST be generated

A successful response MUST return either:

``` text
HTTP/1.1 204 No Content
```

with an empty HTTP body, or:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "id": "STRING",
  "name": "STRING", ?
  "epoch": UINTEGER,
  "self": "URL",
  "description": "STRING", ?
  "documentation": "URL", ?
  "labels": { "STRING": "STRING" * }, ?
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
- the response MUST NOT include any inlinable attributes (such as Registry
  nested collection)

To delete multiple Groups an HTTP `DELETE` MAY be used.

The request MUST be of the form:

``` text
DELETE /GROUPs

[
  {
    "id": "STRING",
    "epoch": UINTEGER ?
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
Link: <URL>;rel=next;count=INT ?

{
  {
    "id": "STRING",
    "name": "STRING", ?
    "epoch": UINTEGER,
    "self": "URL",
    "description": "STRING", ?
    "documentation": "URL", ?
    "labels": { "STRING": "STRING" * }, ?
    "format": "STRING", ?
    "createdBy": "STRING", ?
    "createdOn": "TIME", ?
    "modifiedBy": "STRING", ?
    "modifiedOn": "TIME" ?
  } *
} ?
```

Where:
- the HTTP body SHOULD contain the latest representation of each Group prior
  prior to being deleted. If present, the order and size of the array MUST
  match the order of the request's array
- the response MUST NOT include any inlinable attributes (such as Registry
  nested collection)

---

### Resources

Resources typically represent the main entity that the Registry is managing.
Each Resource is associated with a Group to aid in their discovery and to show
a relationship with related Resources in that same Group. Those Resources
appear within the Group's `RESOURCEs` collection.

Resources, like all entities in the Registry, can be modified but Resources
can also have a version history associated with them, allowing for users to
retrieve previous Versions of the Resource. In this respect, Resources have
a 2-layered definition. The first layer is the Resource entity itself,
while the second layer is its `versions` collection - the version history of
the Resource. The Resource entity can be thought of as an alias for the
"latest" Version of the Resource, and as such, most of the attributes shown
when processing the Resource will be associated with the "latest" Version.
However, there are a few exceptions:
- `id` MUST be for the Resource itself and not the `id` from the "latest"
  Version. The `id` of each Version MUST be unique within the scope of the
  Resource, but to ensure the Resource itself has a consistent `id` value
  it is distinct from any Version's `id`. There MUST be a `latestVersionId`
  and `latestVersionUrl` attribute
  in the serialization of a Resource that references the "latest" Version
  of the Resource (meaning, which Version this Resource is an alias for).

  Additionally, Resource `id` values are often human readable (e.g. `mySchema`),
  while Version `id` values are meant to be versions string values
  (e.g. `1.0`).
- `self` MUST be an absolute URL to the Resource, and not to the "latest"
  Version in the `versions` collection. The Resource's `latestVersionUrl`
  attribute can be used to access the "latest" Version

All other attributes, including extensions, are associated with the Versions.

Unlike Groups, Resources are typically defined by domain-specific data
and as such the Registry defined attributes are not present in the Resources
themselves. This means the Registry metadata needs to be managed separately
from the contents of the Resource. There are two ways to serialize Resources
in HTTP:
- the contents of the Resource appears in the HTTP body, and each Registry
  attribute (along with its value) appears as an HTTP header with its name
  prefixed with `xRegistry-`. See [HTTP Header Values](#http-header-values)
  and [`labels`](#labels) for additional information
- similar to Groups, the Registry attributes are serialized as a single JSON
  object that appears in the HTTP body. The Resource contents will either
  appear as an attribute (`RESOURCE` or `RESOURCEBase64`), or there will be
  a `RESOURCEUrl` reference to the location of its contents.

When serialized as a JSON object, a Resource MUST adhere to this form:

``` text
{
  "id": "STRING",
  "name": "STRING", ?
  "epoch": UINTEGER,
  "self": "URL",
  "latestVersionId": "STRING",
  "latestVersionUrl": "URL",
  "description": "STRING", ?
  "documentation": "URL", ?
  "labels": { "STRING": "STRING" * }, ?
  "format": "STRING", ?
  "createdBy": "STRING", ?
  "createdOn": "TIME", ?
  "modifiedBy": "STRING", ?
  "modifiedOn": "TIME", ?

  "RESOURCEUrl": "URL", ?                  # If not local
  "RESOURCE": { Resource contents }, ?     # If inlined & JSON
  "RESOURCEBase64": "STRING", ?            # If inlined & ~JSON

  "versionsUrl": "URL",
  "versionsCount": INT,
  "versions": { Versions collection } ?    # If inlined
}
```

When serialized with the Resource contents in the HTTP body, it MUST adhere
to this form:

``` text
Content-Type: ... ?
xRegistry-id: STRING
xRegistry-name: STRING ?
xRegistry-epoch: UINT
xRegistry-self: URL
xRegistry-latestVersionId: STRING
xRegistry-latestVersionUrl: URL
xRegistry-description: STRING ?
xRegistry-documentation: URL ?
xRegistry-labels-KEY: STRING ?
xRegistry-labels-...: STRING ?
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

Notes:
- the `versionsUrl` and `versionsCount` attributes are included, but not
  the `versions` collection itself
- the serialization of the `labels` attribute is split into separate HTTP
  headers (one per label name)
- any non-scalar attribute (aside from `labels`), for example arrays or
  objects, MUST NOT be serialized as HTTP headers due to their complexity.
  Instead, clients wishing to retrieve or update those values MUST use
  the `?meta` APIs and use the HTTP body to serialize their values

Resources include the following common attributes:

(these are Resource defined)
- [`id`](#id) - REQUIRED, except on create request where it is OPTIONAL
- [`self`](#self) - REQUIRED in responses, OPTIONAL in requests and in
  document view

(these values are picked-up from the latest version)
- [`name`](#name) - OPTIONAL
- [`epoch`](#epoch) - REQUIRED in responses, otherwise OPTIONAL
- [`description`](#description) - OPTIONAL
- [`documentation`](#documentation) - OPTIONAL
- [`labels`](#labels) - OPTIONAL
- [`format`](#format) - OPTIONAL
- [`createdBy`](#createdby) - OPTIONAL
- [`createdOn`](#createdon) - OPTIONAL
- [`modifiedBy`](#modifiedby) - OPTIONAL
- [`modifiedOn`](#modifiedon) - OPTIONAL

and the following Resource specific attributes:

**`latestVersionId`**
- Type: String
- Description: the `id` of the latest Version of the Resource.
  This specification makes no statement as to the format of this string or
  versioning scheme used by implementations of this specification. However, it
  is assumed that newer Versions of a Resource will have a "higher"
  `id` value than older Versions. Also see [`epoch`](#epoch)
- Constraints:
  - REQUIRED in responses, OPTIONAL on requests
  - REQUIRED in document view
  - MUST be a read-only attribute in API view
  - MUST be non-empty
  - MUST be the `id` of the latest Version of the Resource
- Examples:
  - `1`, `2.0`, `v3-rc1`

**`latestVersionUrl`**
- Type: URL
- Description: an absolute URL to the latest Version of the Resource
- Constraints:
  - REQUIRED in responses, OPTIONAL in requests
  - OPTIONAL in document view
  - MUST be a read-only attribute in API view
  - MUST be an absolute URL to the latest Version of the Resource, and MUST
    be the same as the Version's `self` attribute
- Examples:
  - `https://example.com/endpoints/123/definitions/456/versions/1.0`

**`versions` collection**
- Type: [Registry Collection](#registry-collections)
- Description: A list of Versions of the Resource
- Constraints:
  - REQUIRED in responses, SHOULD NOT be present in requests
  - REQUIRED in document view
  - MUST always have at least one Version (the "latest" Version)

and, finally, the following Version specific attributes:

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
  - if the Resource's contents are to be serialized and they are not empty,
    then either `RESOURCE` or `RESOURCEBase64` MUST be present
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
  serialized as a Registry Resource (e.g. via `?meta`).
- Constraints:
  - MUST NOT be present when the Resource's Registry metadata are being
    serialized as HTTP headers
  - if the Resource's contents are to be serialized and they are not empty,
    then either `RESOURCE` or `RESOURCEBase64` MUST be present
  - MUST be a base64 encoded string of the Resource's contents
  - MUST NOT be present if `RESOURCE` is also present

---

#### Resource and Version APIs

For convenience, the Resource and Version create/update APIs can be summarized
as:

**`POST /GROUPs/gID/RESOURCEs`**

- creates or updates one or more Resources
- if the Resource does not already exist then the first (latest) Version will
  be created
- if a new Version is created then its `vID` (Version ID) will be system
  generated
- if the `rID` of the Resource is not part of its serialziation then it will
  be system generated

**`PUT /GROUPs/gID/RESOURCEs/rID`**

- If Resource does not exist then it will be created with the
  specified `rID` and the first (latest) Version will be created with a system
  generated `vID`
- If Resource exists then the "latest" Version of the Resource will be
  updated

**`POST /GROUPs/gID/RESOURCEs/rID`**

- Same as `POST /GROUPs/gID/RESOURCEs/rID/versions`

**`POST /GROUPs/gID/RESOURCEs/rID/versions`**

- If Resource does not exist then it will be created with the specified
  `rID` and the first (latest) Version will be created with a system
  generated `vID`
- If Resource exists then a new Version will be created with a system generated
  `vID`, and it will become the latest Version.

**`PUT /GROUPs/gID/RESOURCEs/rID/versions/vID`**

- If Resource does not exist then it will be created with the specified
  `rID` and the first (latest) Version will be created with the specified `vID`
- If Resource exists and the Version does not then a new Version will be
  created with the specified `vID` and it will become the latest Version
- If the Resource and Version exist then the Version will be updated

And the delete APIs are summarized as:

**`DELETE /GROUPs/gID/RESOURCEs`**

- If a list of `rID`s are specified in the HTTP body then those Resources
  will be deleted
- If a list of `rID`s are not specified, then it will delete all Resources in
  the specified Group

**`DELETE /GROUPs/gID/RESOURCEs/rID`**

- will delete the specified Resource

**`DELETE /GROUPs/gID/RESOURCEs/rID/versions`**

- If a list of `vID`s are specified in the HTTP body then those Versions will
  be deleted. If there are no other Versions remaining, the Resource will be
  deleted
- If a list of `vID`s are not specified, then it will delete the Resource

**`DELETE /GROUPs/gID/RESOURCEs/rID/versions/vID`**

- will delete the specified Version, and the Resource if it's the last Version

---

#### Retrieving a Resource Collection

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
Link: <URL>;rel=next;count=INT ?

{
  "ID": {                                     # The Resource id
    "id": "STRING",
    "name": "STRING", ?
    "epoch": UINTEGER,
    "self": "URL",
    "latestVersionId": "STRING",
    "latestVersionUrl": "URL",
    "description": "STRING", ?
    "documentation": "URL", ?
    "labels": { "STRING": "STRING" * }, ?
    "format": "STRING", ?
    "createdBy": "STRING", ?
    "createdOn": "TIME", ?
    "modifiedBy": "STRING", ?
    "modifiedOn": "TIME", ?

    "RESOURCEUrl": "URL", ?                  # If not local
    "RESOURCE": { Resource contents }, ?     # If inlined & JSON
    "RESOURCEBase64": "STRING", ?            # If inlined & ~JSON

    "versionsUrl": "URL",
    "versionsCount": INT,
    "versions": { Versions collection } ?    # If inlined
  } *
}
```

Where:
- the key (`ID`) of each item in the map MUST be the `id` of the
  respective Resource

**Examples:**

Retrieve all `definitions` of an `endpoint` whose `id` is `123`:

``` text
GET /endpoints/123/definitions

---

HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Link: <https://example.com/endpoints/123/definitions&page=2>;rel=next;count=100

{
  "456": {
    "id": "456",
    "name": "Blob Created",
    "epoch": 1,
    "self": "https://example.com/endpoints/123/definitions/456",
    "latestVersionId": "1.0",
    "latestVersionUrl": "https://example.com/endpoints/123/definitions/456/versions/1.0",
    "format": "CloudEvents/1.0",

    "versionsUrl": "https://example.com/endpoints/123/definitions/456/versions",
    "versionsCount": 1
  }
}
```

#### Creating or Updating Resources and Versions

Creating or updating Resources via HTTP MAY be done using the HTTP `POST`
or `PUT` methods. Since there is a tight relationship between Resources
and their Versions, these actions can be done either on the Resource itself
(implying the action is being done on the 'latest' Version), or on a specific
Version of a Resource. The full list of HTTP APIs are:

- `POST /GROUPs/gID/RESOURCEs`
- `PUT  /GROUPs/gID/RESOURCEs/rID`
- `POST /GROUPs/gID/RESOURCEs/rID`  (Note: this is an alias for the next one)
- `POST /GROUPs/gID/RESOURCEs/rID/versions`
- `PUT  /GROUPs/gID/RESOURCEs/rID/versions/vID`

To reduce the number of interactions needed, these APIs are designed to allow
for the implicit creation of all entities specified in the PATH with one
request. And each entity not already present with the specified `ID` MUST be
created with that `ID`.

In the remainder of this section, the term `entity` applies to either a
Resource or Version of a Resource based on the API being used.

The HTTP body in the `POST` variants MUST contain either a single entity or
a list of entities (as a JSON array) with each entity expressed as xRegistry
metadata. While the HTTP body in the `PUT` variants MUST contain a single
entity.

When the request format only supports a single entity (in other words, the
`PUT` variants or `POST` with a JSON object (not array) in the HTTP body),
the `?meta` query parameter MAY be specified to indicate that the HTTP body of
the request contains the xRegistry metadata view of the entity. When the
`?meta` query parameter is not present, then any xRegistry metadata MUST be
placed into HTTP headers (prefixed with `xRegistry-`).

When the request results in the creation of a new Version, by default that
Version will become the "latest" Version of the owning Resource. This MAY
be changed by including the `latest` attribute as part of the entity's
representation with a value of `false` - in which case the current latest
Version does not change. If `latest` is present but the server does not support
this feature then an error MUST be generated - see `latest` in the
[Registry Model](#registry-model) section. If there are multiple new Versions
of the same Resource being created within one request, and none of them
inlcude `latest` with a value of `true`, then the last new Version specified
in the request array MUST become the latest Version.

When the request format supports multiple entities (in other words, `POST`
and a JSON array in the HTTP body, even if there is just one item in the
array), the entity MUST be specified as xRegistry metadata in the HTTP body
regardless of whether the `?meta` query parameter is present or not.

When specified as an xRegistry JSON object, each individual entity MUST
adhere to the following:

``` text
{
  "id": "STRING", ?
  "name": "STRING", ?
  "description": "STRING", ?
  "documentation": "URL", ?
  "labels": { "STRING": "STRING" * }, ?
  "format": "STRING", ?

  "RESOURCEUrl": "URL", ?                  # If not local
  "RESOURCE": { Resource contents }, ?     # If inlined & JSON
  "RESOURCEBase64": "STRING" ?             # If inlined & ~JSON
}
```

When the HTTP body contains the Resource Verion's contents, then any xRegistry
metadata MUST appear as HTTP headers and the request MUST adhere to the
following:

``` text
[METHOD] [PATH]
Content-Type: ... ?
xRegistry-id: STRING ?
xRegistry-name: STRING ?
xRegistry-description: STRING ?
xRegistry-documentation: URL ?
xRegistry-labels-KEY: STRING ?
xRegistry-labels-...: STRING ?
xRegistry-format: STRING ?
xRegistry-RESOURCEUrl: URL ?

...entity contents... ?
```

Regardless of how the entity is represented, the following rules apply:
- for any one entity specified, if the entity does not include an `id`
  attribute then the server MUST assign it a value that is unique across all
  entities in that collection, unless the `PUT` variants are used, in which
  case the `id` specified at the end of the URL MUST be used
- for the `PUT` variants, if both an entity `id` and URL `id` are present
  then they MUST be the same value
- an incoming request MUST NOT include duplicate entities as defined by their
  `id` values
- if an entity already exists with a specified `id` then the processing of that
  entity MUST be interpreted as a request to update the existing entity.
  Otherwise, it MUST be interpreted as a request to create a new entity
- the `epoch` attribute is OPTIONAL and if present on a create request, MUST
  be silently ignored. For an update request, if it does not match the existing
  entity's `epoch` value then an error MUST be generated
- a request to update an existing entity MUST increment its `epoch` value
- the `createdBy`, `createdOn`, `modifiedBy` and `modifiedOn` attributes MUST
  be set appropriately if they are supported by the server.
- when the entity's xRegistry metadata is specified in the HTTP body, then
  it MUST be a full representation of the mutable attributes (including
  complex attributes). This means that any missing mutable attributes MUST
  be interpreted as a request to delete the attribute
- when the entity's xRegistry metadata is specified as HTTP headers, then
  it MUST be interpreted as a request to update only the specified attributes
  and any attribute not specified will remain unchanged. To delete an attribute
  it MUST be specified with a value of `null`
- a request to update, or delete, a nested Versions collection or a read-only
  attribute MUST be silently ignored
- a request to update a mutable attribute with an invalid value MUST generate
  an error (this includes deleting a mandatory mutable attribute)
- any error during the processing of an entity MUST result in the entire HTTP
  request being rejected and no updates performed
- in the cases where xRegistry metadata appears as HTTP headers, if the
  `RESOURCEUrl` attribute is present with a non-null value, the HTTP body
  MUST be empty. If the `RESOURCEUrl` attribute is absent, then the contents
  of the HTTP body (even if empty) are to be used as the entity's contents
- a request that would result in the entity missing a mandatory attribute
  MUST generate an error
- if the Resource's model `hasDocument` attribute has a value of `false` then
  the following rules apply:
  - the request MUST NOT contain both xRegistry HTTP headers and the entity's
    xRegistry metadata in the HTTP body. In other words, the presence of any
    xRegistry HTTP header and a non-empty HTTP body MUST generate an error
  - An update request with no xRegistry HTTP headers and an empty HTTP body
    MUST be interpreted as a request to delete all xRegistry mutable
    attributes - in essence, resetting the entity back to its default state
  - when the xRegistry metadata appears in the HTTP body, any missing mutable
    attribute MUST be interpreted as a request to delete that attribute -
    similar to when the `?meta` variant of the APIs are used.
- when the xRegistry metadata is serialized as a JSON object, the processing
  of the 3 `RESOURCE` attributes MUST follow these rules:
  - at most only one of the 3 attributes MAY be present in the request
  - if the entity has content (not a `RESOURCEUrl`), then absence of all 3
    attributes MUST leave it unchanged
  - the presence of `RESOURCE` or `RESOURCEBase64` attributes MUST set the
    contents of the entity
  - the presence of a non-null value for any 3 of the attributes MUST delete
    the other 2 attributes (and any associated data)
  - an explicit value of `null` for any of the 3 attributes MUST delete all
    3 attributes (and any associated data)
- if `format` is present and changing it would result in the entity becoming
  invalid with respect to the `format` of the owning Group, then an error MUST
  be generated

Note: an HTTP `POST` is usually directed to a collection or "factory", in the
case of `POST /GROUPs/gID/RESOURCEs/rID`, while the PATH references a single
Resource, the use of `POST` (rather than `PUT`) MUST be interpreted as a
reference to the Resource's `versions` collection. This also means that any
`id` value in an HTTP xRegistry header or in the HTTP body is for the
Version and not the Resource.

A successful response MUST include the current representation of the entities
created or updated in the same order, cardinality (single object vs array)
and format (`?meta` variant or not) as the request.

Note that the response MUST NOT include any inlinable attributes (such as
`RESOURCE`, `RESOURCEBase64` or any Registry nested collections).

If the request used the `PUT` variant, or it used the `POST` variant with
a single entity in the HTTP body (not an array of entities), and the request
resulted in a new entity being created, then a successful response:
- MUST include an HTTP `201 Created` response code
- MUST include an HTTP `Location` header with a URL to the newly create
  entity, and MUST be the same as the entity's `self` attribute
- MAY include a `Content-Location` HTTP header to the newly create Version
  entity, and it MUST be the same as the Version's `self` attribute

**Examples:**

Create a new Resource:

``` text
PUT /endpoints/123/definitions/456
Content-Type: application/json; charset=utf-8
xRegistry-name: Blob Created
xRegistry-format: CloudEvents/1.0

{
  # Definition of a "Blob Created" event excluded for brevity
}

---

HTTP/1.1 201 Created
Content-Type: application/json; charset=utf-8
xRegistry-id: 456
xRegistry-name: Blob Created
xRegistry-epoch: 1
xRegistry-self: https://example.com/endpoints/123/definitions/456
xRegistry-latestVersionId: 1.0
xRegistry-latestVersionUrl: https://example.com/endpoints/123/definitions/456/versions/1.0
xRegistry-format: CloudEvents/1.0
xRegistry-versionsUrl: https://example.com/endpoints/123/definitions/456/versions
xRegistry-versionsCount: 1
Location: https://example.com/endpoints/123/definitions/456
Content-Location: https://example.com/endpoints/123/definitions/456/versions/1.0

{
  # Definition of a "Blob Created" event excluded for brevity
}
```

Update latest version of a Resource as xRegistry metadata:

``` text
PUT /endpoints/123/definitions/456?meta
Content-Type: application/json; charset=utf-8

{
  "id": "456",
  "name": "Blob Created",
  "epoch": 1,
  "description": "a cool event",
  "format": "CloudEvents/1.0",

  "definition": {
    # Updated definition of a "Blob Created" event excluded for brevity
  }
}

---

HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Location: https://example.com/endpoints/123/definitions/456/versions/1.0

{
  "id": "456",
  "name": "Blob Created",
  "epoch": 2,
  "self": "https://example.com/endpoints/123/definitions/456",
  "latestVersionId": "1.0",
  "latestVersionUrl": "https://example.com/endpoints/123/definitions/456/versions/1.0",
  "description": "a cool event",
  "format": "CloudEvents/1.0",

  "definition": {
    # Updated definition of a "Blob Created" event excluded for brevity
  },

  "versionsUrl": "https://example.com/endpoints/123/definitions/456/versions",
  "versionsCount": 1
}
```

Update several Versions (adding a label):

``` text
POST /endpoints/123/definitions/456/versions
Content-Type: application/json; charset=utf-8

[
  {
    "id": "1.0",
    "labels": { "customer": "abc" },
    # Remainder of xRegistry metadata excluded for brevity
  },
  {
    "id": "2.0",
    "labels": { "customer": "abc" },
    # Remainder of xRegistry metadata excluded for brevity
  },
  {
    "id": "3.0",
    "labels": { "customer": "abc" },
    # Remainder of xRegistry metadata excluded for brevity
  }
]

---

HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

[
  {
    "id": "1.0",
    "labels": { "customer": "abc" },
    # Remainder of xRegistry metadata excluded for brevity
  },
  {
    "id": "2.0",
    "labels": { "customer": "abc" },
    # Remainder of xRegistry metadata excluded for brevity
  },
  {
    "id": "3.0",
    "labels": { "customer": "abc" },
    # Remainder of xRegistry metadata excluded for brevity
  }
]
```

#### Retrieving a Resource

To retrieve a Resource, an HTTP `GET` MAY be used.

The request MUST be of the form:

``` text
GET /GROUPs/gID/RESOURCEs/rID
```

This MUST retrieve the latest Version of a Resource. Note that `rID` will be
for the Resource and not the `id` of the underlying Version (see
[Resources](#resources)).

A successful response MUST either be:
- `200 OK` with the Resource contents in the HTTP body
- `303 See Other` with the location of the Resource's contents being
  returned in the HTTP `Location` header

And in both cases the Resource's metadata attributes MUST be serialized as HTTP
`xRegistry-` headers.

Note that if the Resource's model `hasDocument` attribute has a value of
`false` then the "Resource contents" will be the xRegistry metadata for the
latest Version, duplicating the HTTP `xRegistry-` headers.

The response MUST be of the form:

``` text
HTTP/1.1 200 OK|303 See Other
Content-Type: ... ?            # If Resource is in body
xRegistry-id: STRING
xRegistry-name: STRING ?
xRegistry-epoch: UINT
xRegistry-self: URL
xRegistry-latestVersionId: STRING
xRegistry-latestVersionUrl: URL
xRegistry-description: STRING ?
xRegistry-documentation: URL ?
xRegistry-labels-KEY: STRING ?
xRegistry-labels-...: STRING ?
xRegistry-format: STRING ?
xRegistry-createdBy: STRING ?
xRegistry-createdOn: TIME ?
xRegistry-modifiedBy: STRING ?
xRegistry-modifiedOn: TIME ?
xRegistry-versionsUrl: URL
xRegistry-versionsCount: INT
xRegistry-RESOURCEUrl: URL      # If Resource is not in body
Location: URL ?                 # If Resource is not in body
Content-Location: URL ?

...Resource contents...
```
Where:
- `id` MUST be the ID of the Resource, not of the latest Version of the
  Resource
- `self` MUST be a URL to the Resource, not to the latest Version of the
  Resource
- if `RESOURCEUrl` is present then it MUST have the same value as `Location`
- if `Content-Location` is present then it MUST be a URL to the Version of the
  Resource in the `versions` collection - same as `latestVersionUrl`

#### Retrieving a Resource as Metadata

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
Content-Location: URL ?

{
  "id": "STRING",
  "name": "STRING", ?
  "epoch": UINTEGER,
  "self": "URL",
  "latestVersionId": "STRING",
  "latestVersionUrl": "URL",
  "description": "STRING", ?
  "documentation": "URL", ?
  "labels": { "STRING": "STRING" * }, ?
  "format": "STRING", ?
  "createdBy": "STRING", ?
  "createdOn": "TIME", ?
  "modifiedBy": "STRING", ?
  "modifiedOn": "TIME", ?

  "RESOURCEUrl": "URL", ?                  # If not local
  "RESOURCE": { Resource contents }, ?     # If inlined & JSON
  "RESOURCEBase64": "STRING", ?            # If inlined & ~JSON

  "versionsUrl": "URL",
  "versionsCount": INT,
  "versions": { Versions collection } ?    # If inlined
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
  Resource in the `versions` collection - same as `latestVersionUrl`

The following query parameters MUST be supported by servers:
- `inline` - See [inlining](#inlining) for more information
- `filter` - See [filtering](#filtering) for more information

**Examples:**

Retrieve a `definition` Resource as xRegistry metadata:

``` text
GET /endpoints/123/definitions/456?meta

---

HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Location: https://example.com/endpoints/123/definitions/456/versions/1.0

{
  "id": "456",
  "name": "Blob Created",
  "epoch": 1,
  "self": "https://example.com/endpoints/123/definitions/456i?meta,
  "latestVersionId": "1.0",
  "latestVersionUrl": "https://example.com/endpoints/123/definitions/456/versions/1.0",
  "format": "CloudEvents/1.0",

  "versionsUrl": "https://example.com/endpoints/123/definitions/456/versions",
  "versionsCount": 1
}
```

#### Deleting Resources

To delete a single Resource, and all of its Versions, an HTTP `DELETE` MAY be
used.

The request MUST be of the form:

``` text
DELETE /GROUPs/gID/RESOURCEs/rID[?epoch=UINTEGER]
```

Where:
- the request body SHOULD be empty

The following query parameters MUST be supported by servers:
- `epoch`<br>
  The presence of this query parameter indicates that the server MUST check
  to ensure that the `epoch` value matches the Resource's latest Version's
  `epoch` value and if it differs then an error MUST be generated

A successful response MUST return either:

``` text
HTTP/1.1 204 No Content
```

with an empty HTTP body, or:

``` text
HTTP/1.1 200 OK
Content-Type: ... ?
xRegistry-id: STRING
xRegistry-name: STRING ?
xRegistry-epoch: UINT
xRegistry-self: URL
xRegistry-latestVersionId: STRING ?
xRegistry-description: STRING ?
xRegistry-documentation: URL ?
xRegistry-labels-KEY: STRING ?
xRegistry-labels-...: STRING ?
xRegistry-format: STRING ?
xRegistry-createdBy: STRING ?
xRegistry-createdOn: TIME ?
xRegistry-modifiedBy: STRING ?
xRegistry-modifiedOn: TIME ?
xRegistry-RESOURCEUrl: URI ?

...Resource contents... ?
```

Where:
- the HTTP body SHOULD contain the latest representation of the Resource prior
  to being deleted
- the response MUST NOT include any inlinable attributes (such as Registry
  nested collection), as well as the `latestVersionUrl`

**Examples:**

Delete a `definition` Resource, and all its Versions:

``` text
DELETE /endpoints/123/definitions/456

---

HTTP/1.1 204 No Content
```

To delete multiple Resources, and all of their Versions, an HTTP `DELETE` MAY
be used.

The request MUST be of the form:

``` text
DELETE /GROUPs/gID/RESOURCEs

[
  {
    "id": "STRING",
    "epoch": UINTEGER ?
  } *
]
```

Where:
- the request body MUST contain the list of Resource IDs to be deleted, however
  an empty list or an empty body MUST be interpreted as a request to delete
  all Resources of the specified Group
- if an `epoch` value is specified for a Resource then the server MUST check
  to ensure that the value matches the Resource's latest Version `epoch` value
  and if it differs then an error MUST be generated

Any error MUST result in the entire request being rejected.

A successful response MUST return either:

``` text
HTTP/1.1 204 No Content
```

with an empty HTTP body, or:

``` text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Link: <URL>;rel=next;count=INT ?

{
  {
    "id": "STRING",
    "name": "STRING", ?
    "epoch": UINTEGER,
    "self": "URL",
    "latestVersionId": "STRING", ?
    "description": "STRING", ?
    "documentation"": "URL", ?
    "labels": { "STRING": "STRING" * }, ?
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
- the HTTP body SHOULD contain the latest representation of each Group prior
  prior to being deleted. If present, the order and size of the array MUST
  match the order of the request's array
- the response MUST NOT include any inlinable attributes (such as Registry
  nested collection), as well as the `latestVersionUrl`

A `DELETE /GROUPs/gID/RESOURCEs` without a body MUST delete all Resources in
the Group.

---

### Versions

Versions represent historical instances of a Resource. When a Resource is
updated, there are two ways this might happen. First, the update can completely
replace an existing Version of the Resource. This is most typically
done when the previous state of the Resource is no longer valid and there
is no reason to allow people to reference it. The second situation is when
both the old and new Versions of a Resource are meaningful and both might need
to be referenced. In this case the update will cause a new Version of the
Resource to be created and will be have a unique `id` within the scope of
the owning Resource.

For example, updating the state of Resource without creating a new Version
would make sense if there is a typo in the `description` field. But, adding
additional data to the content of a Resource might require a new Version and
a new ID (e.g. changing it from "1.0" to "1.1").

This specification does not mandate a particular versioning scheme.

The serialization of a Version entity adheres to this form:

``` text
{
  "id": "STRING",
  "name": "STRING", ?
  "epoch": UINTEGER,
  "self": "URL",
  "latest": BOOLEAN, ?
  "description": "STRING", ?
  "documentation"": "URL", ?
  "labels": { "STRING": "STRING" * }, ?
  "format": "STRING", ?
  "createdBy": "STRING", ?
  "createdOn": "TIME", ?
  "modifiedBy": "STRING", ?
  "modifiedOn": "TIME", ?

  "RESOURCEUrl": "URL", ?                  # If not local
  "RESOURCE": { Resource contents }, ?     # If inlined & JSON
  "RESOURCEBase64": "STRING" ?             # If inlined & ~JSON
}
```

Versions include the following attributes as defined by the
[Resource](#resources) entity:
- [`id`](#id) - Version's `id`, not the Resource's
- [`name`](#name)
- [`epoch`](#epoch)
- [`self`](#self) - URL to this Version, not the Resource
- [`description`](#description)
- [`documentation`](#documentation)
- [`labels`](#labels)
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
  - if present, MUST be either `true` or `false`, case sensitive
  - if not present, the default value MUST be `false`
- Examples:
  - `true`
  - `false`

#### Version IDs

If a server does not support client-side specification of the `id` of a new
Version, or if a client choose to not specify the `id`, then the server MUST
create a new `id` that is unique within the scope of its owning Resource.

Servers MAY have their own algorithm for creation of new Version `id` values,
but the default algorithm is as follows:
- `id` MUST be a string serialization of a monotonically increasing (by `1`)
  unsigned integer starting with `1` and is scoped to the owning Resource
- each time a new `id` is generated, if an existing Version already has that
  `id` then the server MUST generate the next `id` in the sequence and try
  again

#### Latest Version of a Resource

As Versions of a Resource are added or removed there needs to be a mechanism
by which the "latest" one is known. This can be determined by the client
explicitly indicating which one is the latest, or it can be determined by the
server.

Servers MAY have their own algorithm for determining which Version is the latest
but the default algorithm is to choose the newest Version based on the time
each Version was created. Note, this applies even if the `createdBy` attribute
is not supported or exposed to clients.

There are several ways in which the "latest" Version of a Resource can be
modified by a client:
- during the deletion of a Version(s), a new "latest" MAY be specified
  as a query parameter (`?setLatestVersionId=vID`). See [Deleting Versions of
  a Resource](#deleting-versions)
- during the creation of a new Version, the `latest` attribute MAY be
  specified to indicate if the new Version is to become
  the "latest" Version or not. See [Creating or Updating
  Resources and Versions](#creating-or-updating-resources-and-versions)
- a dedicated API for updating the `latestVersionId` of a Resource can be used,
  and is defined below

To update the `latestVersionId` of a Resource, the following API MAY be used:
```
POST /GROUPs/gID/RESOURCEs/rID?setLatestVersionId=vID
```

Where:
- `vID` is the `id` of the Version that MUST become the "latest" version
  of the referenced Resource
- if the `vID` does not reference an existing Version of the Resource then an
  HTTP `400 Bad Request` error MUST be generated

While this API looks similar to other operations of a Resource,
the presence of the `?setLatestVersionId` query parameter MUST be
interpreted by the server as a request to update just the `latestVersionId`
value and nothing else. Any other Registry data provided (as HTTP headers or
in the HTTP body) SHOULD NOT be present and MUST be silently ignored by the
server.

Upon successful completion of the request, the response MUST return the same
response as a `GET` to the targeted Resource.

#### Retrieving all Versions

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
Link: <URL>;rel=next;count=INT ?

{
  "ID": {                                     # The Version id
    "id": "STRING",
    "name": "STRING", ?
    "epoch": UINTEGER,
    "self": "URL",
    "latest": BOOLEAN,
    "description": "STRING", ?
    "documentation"": "URL", ?
    "labels": { "STRING": "STRING" * }, ?
    "format": "STRING", ?
    "createdBy": "STRING", ?
    "createdOn": "TIME", ?
    "modifiedBy": "STRING", ?
    "modifiedOn": "TIME", ?

    "RESOURCEUrl": "URL", ?                  # If not local
    "RESOURCE": { Resource contents }, ?     # If inlined & JSON
    "RESOURCEBase64": "STRING" ?             # If inlined & ~JSON
  } *
}
```

Where:
- the key (`ID`) of each item in the map MUST be the `id` of the
  respective Version

**Examples:**

Retrieve all Version of a `definition` Resource:

``` text
GET /endpoints/123/definitions/456/versions

---

HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
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

#### Creating or Updating Versions

See [Creating or Updating Resources and
Versions](#creating-or-updating-resources-and-versions).

#### Retrieving a Version

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
Content-Type: ... ?
xRegistry-id: STRING
xRegistry-name: STRING ?
xRegistry-epoch: UINT
xRegistry-self: URL
xRegistry-latest: BOOL
xRegistry-description: STRING ?
xRegistry-documentation: URL ?
xRegistry-labels-KEY: STRING ?
xRegistry-labels-...: STRING ?
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
HTTP/1.1 303 See Other
xRegistry-id: STRING
xRegistry-name: STRING ?
xRegistry-epoch: UINT
xRegistry-self: URL
xRegistry-latest: BOOL
xRegistry-description: STRING ?
xRegistry-documentation: URL ?
xRegistry-labels-KEY: STRING ?
xRegistry-labels-...: STRING ?
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

Retrieve a specific Version (`1.0`) of a `definition` Resource:

``` text
GET /endpoints/123/definitions/456/versions/1.0

---

HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
xRegistry-id: 1.0
xRegistry-name: Blob Created
xRegistry-epoch: 2
xRegistry-self: https://example.com/endpoints/123/definitions/456/versions/1.0
xRegistry-latest: true
xRegistry-format: CloudEvents/1.0

{
  # Definition of a "Blob Created" event excluded for brevity
}
```

#### Retrieving a Version as Metadata

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

{
  "id": "STRING",
  "name": "STRING", ?
  "epoch": UINTEGER,
  "self": "URL",
  "latest": BOOLEAN,
  "description": "STRING", ?
  "documentation"": "URL", ?
  "labels": { "STRING": "STRING" * }, ?
  "format": "STRING", ?
  "createdBy": "STRING", ?
  "createdOn": "TIME", ?
  "modifiedBy": "STRING", ?
  "modifiedOn": "TIME", ?

  "RESOURCEUrl": "URL", ?                  # If not local
  "RESOURCE": { Resource contents }, ?     # If inlined & JSON
  "RESOURCEBase64": "STRING" ?             # If inlined & ~JSON
}
```

Where:
- `id` MUST be the Version's `id` and not the `id` of the owning Resource
- `self` MUST be a URL to the Version, not to the owning Resource

**Examples:**

Retrieve a specific Version of a `definition` Resource as xRegistry metadata:

``` text
GET /endpoints/123/definitions/456/versions/1.0?meta

---

HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "id": "1.0",
  "name": "Blob Created",
  "epoch": 2,
  "self": "https://example.com/endpoints/123/definitions/456/versions/1.0",
  "latest": true,
  "format": "CloudEvents/1.0"
}
```

#### Deleting Versions
To delete a single Version of a Resource, an HTTP `DELETE` MAY be used.

The request MUST be of the form:

``` text
DELETE /GROUPs/gID/RESOURCEs/rID/versions/vID[?epoch=UINTEGER][&latestVersionId=vID]
```

Where:
- the request body SHOULD be empty

The following query parameters MUST be supported by servers:
- `epoch`<br>
  The presence of this query parameter indicates that the server MUST check
  to ensure that the `epoch` value matches the Resource's current `epoch` value
  and if it differs then an error MUST be generated

If the server supports client-side selection of the latest Version of a
Resource (see the [Registry Model](#registry-model)), then the following
applies:
- `latestVersionId` query parameter MUST be supported and its value (`vID`) is
  the `id` of Version which is the become the latest Version of the owning
  Resource
- `latestVersionId` MAY be specified even if the Version being delete is not
  currently the latest Version
- if `latestVersionId` is present but its value does not match any Version
  (after the delete operation is completed) then an error MUST be generated
  and the entire delete MUST be rejected
- if the latest Version of a Resource is being deleted but `latestVersionId` was
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
Content-Type: ... ?
xRegistry-id: STRING
xRegistry-name: STRING ?
xRegistry-epoch: UINT
xRegistry-self: URL
xRegistry-latest: BOOL
xRegistry-description: STRING ?
xRegistry-documentation: URL ?
xRegistry-labels-KEY: STRING ?
xRegistry-labels-...: STRING ?
xRegistry-format: STRING ?
xRegistry-createdBy: STRING ?
xRegistry-createdOn: TIME ?
xRegistry-modifiedBy: STRING ?
xRegistry-modifiedOn: TIME ?
xRegistry-RESOURCEUrl: URL ?

...Resource contents... ?
```

Where:
- the HTTP body SHOULD contain the latest representation of the Version prior
  to being deleted

**Examples:**

Delete a single Version of a `definition` Resource:

``` text
DELETE /endpoints/123/definitions/456/versions/1.0

---

HTTP/1.1 204 No Content
```

To delete multiple Versions, an HTTP `DELETE` MAY be used.

The request MUST be of the form:

``` text
DELETE /GROUPs/gID/RESOURCEs/rID/versions[?setLatestVersionId=vID]

[
  {
    "id": "STRING",
    "epoch": UINTEGER ?
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
- `latestVersionId` query parameter MUST be supported and its value (`vID`) is
  the `id` of Version which is the become the latest Version of the owning
  Resource
- `latestVersionId` MAY be specified even if the Version being delete is not
  currently the latest Version
- if `latestVersionId` is present but its value does not match any Version
  (after the delete operation is completed) then an error MUST be generated
  and the entire delete MUST be rejected
- if the latest Version of a Resource is being deleted but `latestVersionId` was
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
Link: <URL>;rel=next;count=INT ?

{
  {
    "id": "STRING",
    "name": "STRING", ?
    "epoch": UINTEGER,
    "self": "URL",
    "latest": BOOLEAN,
    "description": "STRING", ?
    "documentation"": "URL", ?
    "labels": { "STRING": "STRING" * }, ?
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
- the HTTP body SHOULD contain the latest representation of each Group prior
  prior to being deleted. If present, the order and size of the array MUST
  match the order of the request's array
- the response MUST NOT include any inlinable attributes (such as Registry
  nested collection)

---

### Inlining

The `inline` query parameter on a request indicates that the response
MUST include the contents of all specified inlinable attributes. Inlinable
attributes include:
- all [Registry Collection](#registry-collections) types - e.g. `GROUPs`,
  `RESOURCEs` and `versions`
- the `RESOURCE` attribute in a Resource

While the `RESOURCE` and `RESOURCEBase64` attributes are defined as two
separate attributes, they are technically two separate "views" of the same
underlying data. As such, the usage of each will be based on the content type
of the Resource, specifying `RESOURCE` in the `inline` query parameter MUST
be interpreted as a request for the appropriate attribute. In other words,
`RESOURCEBase64` is not a valid inlinable attribute name.

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

Where `PATH` is a string indicating which inlinable attributes to show in
in the response. References to nested attributes are represented using a
dot(`.`) notation - for example `GROUPs.RESOURCEs`.

There MAY be multiple `PATH`s specified, either as comma separated values on
a single `inline` query parameter or via multiple `inline` query parameters.
Absence of a `PATH` indicates that all nested inlinable attributes MUST be
inlined.

The specific value of `PATH` will vary based on where the request is directed.
For example, a request to the root of the Registry MUST start with a `GROUPs`
name, while a request directed at a Group would start with a `RESOURCEs` name.

For example, given a Registry with a model that has "endpoints" as a Group and
"definitions" as a Resource within "endpoints", the table below shows some
`PATH` values and a description of the result:

| HTTP `GET` Path | Example ?inline=PATH values | Comment |
| --- | --- | --- |
| / | ?inline=endpoints | Inlines the `endpoints` collection, but just one level of it, not any nested inlinable attributes |
| / | ?inline=endpoints.definitions.versions | Inlines the `versions` collection of all definitions. Note that this implicitly means the parent attributes (`definitions` and `endpoints` would also be inlined - however any other `GROUPs` or `RESOURCE`s types would not be |
| /endpoints | ?inline=definitions | Inlines just `definitions` and not any nested attributes. Note we don't need to specify the parent `GROUP` since the URL already included it |
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

---

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
[PATH.]ATTRIBUTE[=[VALUE]]
```

Where:
- `PATH` MUST be a dot(`.`) notation traversal of the Registry to the entity
  of interest, or absent if at the top of the Registry request. Note that
  the `PATH` value is based on the requesting URL and not the root of the
  Registry. See the examples below
- `PATH` MUST only consist of valid `GROUPs`, `RESOURCEs` or `versions`,
  otherwise an error MUST be generated
- `ATTRIBUTE` MUST be the attribute in the entity to be examined
- complex attributes (e.g. `labels`) MUST use dot(`.`) to reference nested
  attributes. For example: `labels.stage=dev` for a filter
- a reference to a nonexistent attribute SHOULD NOT generate an error and
  SHOULD be treated the same as a non-matching situation
- when the equals sign (`=`) is present with a `VALUE` then `VALUE` MUST be
  the desired value of the attribute being examined. Only entities whose
  specified `ATTRIBUTE` with this `VALUE` MUST be included in the response
- when the equals sign (`=`) is present without a `VALUE` then the implied
  value is an empty string, and the matching MUST be as specified in the
  previous bullet.
- when the equals sign (`=`) is not present then the response MUST include all
  entities that have the `ATTRIBUTE` present with any value. In database terms
  this is equivalent to checking for entities with a non-NULL value.

When comparing an `ATTRIBUTE` to the specified `VALUE` the following rules
MUST apply for an entity to be considered a match of the filter expression:
- for numeric attributes, it MUST be an exact match.
- for string attributes, its value MUST contain the `VALUE` within it but
  does not need to be an exact case match.
- for boolean attributes, its value MUST be an exact case-sensitive match
  (`true` or `false`).

If the request references an entity (not a collection), and the `EXPRESSION`
references an attribute in that entity (i.e. there is no `PATH`), then if the
`EXPRESSION` does not match the entity, that entity MUST NOT be returned. In
other words, a `404 Not Found` would be generated in the HTTP protocol case.

At this time, this specification only supports filtering over scalar attributes
defined at the root of the xRegistry entities (the Registry itself, Groups,
Resources and Versions). The one exception to this is support for filtering on
on maps (such as `labels`)
where the value type of the map is a scalar. Implementations, and extension
specifications, MAY define additional filtering capabilities. "Scalar" is
defined as one of the variants of: boolean, numeric, string. If an
implementation would like to enable filtering over a non-root attribute then it
could consider duplicating that attribute's value into a new root attribute or
as a `label`.

**Examples:**

| Request PATH | Filter query | Commentary |
| --- | --- | --- |
| / | `filter=endpoints.description=cool` | Only endpoints with the word `cool` in the description |
| /endpoints | `filter=description=CooL` | Same results as previous, with a different request URL |
| / | `filter=endpoints.definitions.versions.id=1.0` | Only versions (and their owning endpoints.definitions) that have an ID of `1.0` |
| / | `filter=endpoints.format=CloudEvents/1.0,endpoints.description=cool&filter=schemaGroups.modifiedBy=John` | Only endpoints whose format is `CloudEvents/1.0` and whose description contains the word `cool`, as well as any schemaGroups that were modified by 'John' |
| / | `filter=description=no-match` | Returns a 404 if the Registry's `description` doesn't contain `no-match` |

Specifying a filter does not imply inlining.

### HTTP Header Values

Some attributes can contain arbitrary UTF-8 string content,
and per [RFC7230, section 3][rfc7230-section-3], HTTP headers MUST only use
printable characters from the US-ASCII character set, and are terminated by a
CRLF sequence with OPTIONAL whitespace around the header value.

When encoding an attribute's value as an HTTP header it MUST be
precent-encoded as described below. This is compatible with [RFC3986, section
2.1][rfc3986-section-2-1] but is more specific about what needs
encoding. The resulting string SHOULD NOT be further encoded.
(Rationale: quoted string escaping is unnecessary when every space
and double-quote character is already percent-encoded.)

When decoding an HTTP header into an attribute's value, any HTTP header
value MUST first be unescaped with respect to double-quoted strings,
as described in [RFC7230, section 3.2.6][rfc7230-section-3-2-6]. A single
round of percent-decoding MUST then be performed as described
below. HTTP headers for attribute values do not support
parenthetical comments, so the initial unescaping only needs to handle
double-quoted values, including processing backslash escapes within
double-quoted values. Header values produced via the
percent-encoding described here will never include double-quoted
values, but they MUST be supported when receiving events, for
compatibility with older versions of this specification which did
not require double-quote and space characters to be percent-encoded.

Percent encoding is performed by considering each Unicode character
within the attribute's canonical string representation. Any
character represented in memory as a [Unicode surrogate
pair][surrogate-pair] MUST be treated as a single Unicode character.
The following characters MUST be percent-encoded:

- Space (U+0020)
- Double-quote (U+0022)
- Percent (U+0025)
- Any characters outside the printable ASCII range of U+0021-U+007E
  inclusive

Space and double-quote are encoded to avoid requiring any further
quoting. Percent is encoded to avoid ambiguity with percent-encoding
itself.

Steps to encode a Unicode character:

- Encode the character using UTF-8, to obtain a byte sequence.
- Encode each byte within the sequence as `%xy` where `x` is a
  hexadecimal representation of the most significant 4 bits of the byte,
  and `y` is a hexadecimal representation of the least significant 4
  bits of the byte.

Percent-encoding SHOULD be performed using upper-case for values A-F,
but decoding MUST accept lower-case values.

When performing percent-decoding, values that have been unnecessarily
percent-encoded MUST be accepted, but encoded byte sequences which are
invalid in UTF-8 MUST be rejected. (For example, "%C0%A0" is an overlong
encoding of U+0020, and MUST be rejected.)

Example: a header value of "Euro &#x20AC; &#x1F600;" SHOULD be encoded as
follows:

- The characters, 'E', 'u', 'r', 'o' do not require encoding
- Space, the Euro symbol, and the grinning face emoji require encoding.
  They are characters U+0020, U+20AC and U+1F600 respectively.
- The encoded HTTP header value is therefore "Euro%20%E2%82%AC%20%F0%9F%98%80"
  where "%20" is the encoded form of space, "%E2%82%AC" is the encoded form
  of the Euro symbol, and "%F0%9F%98%80" is the encoded form of the
  grinning face emoji.

[rfc7230-section-3]: https://tools.ietf.org/html/rfc7230#section-3
[rfc3986-section-2-1]: https://tools.ietf.org/html/rfc3986#section-2.1
[rfc7230-section-3-2-6]: https://tools.ietf.org/html/rfc7230#section-3.2.6
