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
- [Registry Attributes and APIs](#registry-attributes-and-apis)
  - [Attributes and Extensions](#attributes-and-extensions)
  - [Registry APIs](#registry-apis)
    - [Registry Collections](#registry-collections)
    - [Entity Processing Rules](#entity-processing-rules)
  - [Registry Entity](#registry-entity)
    - [Retrieving the Registry](#retrieving-the-registry)
    - [Updating the Registry Entity](#updating-the-registry-entity)
  - [Registry Model](#registry-model)
    - [Retrieving the Registry Model](#retrieving-the-registry-model)
    - [Updating the Registry Model](#updating-the-registry-model)
  - [Groups](#groups)
    - [Retrieving a Group Collection](#retrieving-a-group-collection)
    - [Creating or Updating Groups](#creating-or-updating-groups)
    - [Retrieving a Group](#retrieving-a-group)
    - [Deleting Groups](#deleting-groups)
  - [Resources](#resources)
    - [Retrieving a Resource Collection](#retrieving-a-resource-collection)
    - [Creating or Updating Resources and
       Versions](#creating-or-updating-resources-and-versions)
    - [Retrieving a Resource](#retrieving-a-resource)
    - [Deleting Resources](#deleting-resources)
  - [Versions](#versions)
    - [Retrieving all Versions](#retrieving-all-versions)
    - [Creating or Updating Versions](#creating-or-updating-versions)
    - [Retrieving a Version](#retrieving-a-version)
    - [Deleting Versions](#deleting-versions)
  - [Inlining](#inlining)
  - [Filtering](#filtering)
  - [HTTP Header Values](#http-header-values)

## Overview

A Registry Service is one that manages metadata about Resources. At its core,
the management of an individual Resource is simply a REST-based interface for
creating, modifying, and deleting the Resource. However, many Resource models
share a common pattern of grouping Resources and can optionally support
versioning of those Resources. This specification aims to provide a common
interaction pattern for these types of services with the goal of providing an
interoperable framework that will enable common tooling and automation to be
created.

This document is meant to be a framework from which additional specifications
can be defined that expose model specific Resources and metadata.

A Registry consists of two main types of entities: Groups and Resources.

Groups, as the name implies, is a mechanism by which related Resources are
arranged together under a single collection - the Group. The reason for the
grouping is not defined by this specification, so the owners of the Registry
can choose to define (or enforce) any pattern they wish. In this sense, a
Group is similar to a "directory" on a filesystem.

Resources represent the main data of interest for the Registry. In the
filesystem analogy, these would be the "files". A Resource exists under a
single Group and, similar to Groups, has a set of Registry metadata.
However, unlike a Group which only has Registry metadata, each Resource can
have a "document" associated with it. For example, a "schema" Resource might
have a "schema document" as its "document". This specification places no
restriction on the type of content stored in the Resource's document.

This specification defines a set of common metadata that can appear on both
Groups and Resources, and allows for domain-specific extensions to be added.

The following 3 diagrams show (from left to right): 1) the core concepts of the
Registry in its most abstract form, 2) a Registry concept model with multiple
types of Groups/Resources, and 3) a concrete sample usage of Registry that
includes the use of an attribute on "Message Definitions" that is a reference
to a "Schema" document - all within the same Registry instance:

<img src="./xregbasicmodel.png"
 height="300">&nbsp;&nbsp;&nbsp;<img
 src="./xregfullmodel.png" height="300">&nbsp;&nbsp;&nbsp;<img
 src="./sample.png" height="300">

For easy reference, the JSON serialization of a Registry adheres to this form:

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
  "createdat": "TIME",
  "modifiedat": "TIME",

  "model": {                            # Only if requested
    "schemas": [ "STRING" * ], ?        # Available schema formats
    "attributes": {                     # Registry level extensions
      "STRING": {                       # Attribute name (case sensitive)
        "name": "STRING",               # Same as attribute's key
        "type": "TYPE",                 # string, decimal, array, object, ...
        "description": "STRING", ?
        "enum": [ VALUE * ], ?          # Array of scalar values of type "TYPE"
        "strict": BOOLEAN, ?            # Just "enum" values or not.Default=true
        "readonly": BOOLEAN, ?          # From client's POV. Default: false
        "immutable": BOOLEAN, ?         # Once set, can't change. Default=false
        "clientrequired": BOOLEAN, ?    # Default: false
        "serverrequired": BOOLEAN, ?    # Default: false
        "exportrequired": BOOLEAN, ?    # Default: false
        "default": VALUE, ?             # Attribute's default value, scalars

        "attributes": { ... }, ?        # If "type" above is object
        "item": {                       # If "type" above is map,array
          "type": "TYPE", ?             # map value type, or array type
          "attributes": { ... }, ?      # If this item "type" is object
          "item": { ... } ?             # If this item "type" is map,array
        } ?

        "ifvalues": {                   # If "type" is scalar
          "VALUE": {                    # Possible attribute value
            "siblingattributes": { ... } # See "attributes" above
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
            "maxversions": UINTEGER, ?  # Num Vers(>=0). Default=0, 0=unlimited
            "setversionid": BOOLEAN, ?  # Supports client specified Version IDs
            "setdefaultversionsticky": BOOLEAN, ?    # Supports client "default" selection
            "hasdocument": BOOLEAN, ?   # Has a separate document. Default=true
            "readonly": BOOLEAN, ?      # From client's POV. Default=false
            "typemap": MAP, ?           # contenttype mappings
            "attributes": { ... }, ?    # See "attributes" above
          } *
        } ?
      } *
    } ?
  } ?

  # Repeat for each Group type
  "GROUPsurl": "URL",                              # e.g. "endpointsurl"
  "GROUPscount": UINTEGER,                         # e.g. "endpointscount"
  "GROUPs": {                                      # Only if inlined/nested
    "ID": {                                        # Key=the Group id
      "id": "STRING",                              # The Group ID
      "name": "STRING", ?
      "epoch": UINTEGER,
      "self": "URL",
      "description": "STRING", ?
      "documentation": "URL", ?
      "labels": { "STRING": "STRING" * }, ?
      "origin": "URI", ?
      "createdat": "TIME",
      "modifiedat": "TIME",

      # Repeat for each Resource type in the Group
      "RESOURCEsurl": "URL",                       # e.g. "definitionsurl"
      "RESOURCEscount": UINTEGER,                  # e.g. "definitionscount"
      "RESOURCEs": {                               # Only if inlined/nested
        "ID": {                                    # The Resource id
          "id": "STRING",                          # The Resource id
          "self": "URL",                           # Resource URL, not Version

          # These are inherited from the default Version (excluded on export)
          "versionid": "STRING",                   # Same a defaultversionid
          "name": "STRING", ?
          "epoch": UINTEGER,
          "isdefault": true,
          "description": "STRING", ?
          "documentation": "URL", ?
          "labels": { "STRING": "STRING" * }, ?
          "origin": "URI", ?
          "createdat": "TIME",
          "modifiedat": "TIME",
          "contenttype": "STRING, ?

          "RESOURCEurl": "URL", ?                  # If not local
          "RESOURCE": ... Resource document ..., ? # If local & inlined & JSON
          "RESOURCEbase64": "STRING", ?            # If local & inlined & ~JSON

          # These are Resource-only attributes
          "xref": "URL", ?                         # Ptr to other Resource

          "defaultversionsticky": BOOLEAN, ?
          "defaultversionid": "STRING",            # Same as versionid above
          "defaultversionurl": "URL",

          "versionsurl": "URL",
          "versionscount": UINTEGER,
          "versions": {                            # Only if inlined/nested
            "ID": {                                # The Version's versionid
              "id": "STRING",                      # The Resource id
              "self": "URL",                       # Version URL
              "versionid": "STRING",
              "name": "STRING", ?
              "epoch": UINTEGER,
              "isdefault": BOOLEAN, ?
              "description": "STRING", ?
              "documentation": "URL", ?
              "labels": { "STRING": "STRING" * }, ?
              "origin": "URI", ?
              "createdat": "TIME",
              "modifiedat": "TIME",
              "contenttype": "STRING", ?

              "RESOURCEurl": "URL", ?                  # If not local
              "RESOURCE": ... Resource document ..., ? # If inlined & JSON
              "RESOURCEbase64": "STRING" ?             # If inlined & ~JSON
            } *
          } ?
        } *
      } ?
    } *
  } ?
}
```

Note: the cardinality/optionality of a Resource's attributes are specified
to indicate which are to be present when the Resource's attributes are
included in its serialization. For example, when `?export` is used, the
Resource's default Version attributes will not be present at all, which means
listing `epoch` as mandatory in the above serialization is technically
incorrect in general, but when the attributes do appear then `epoch` is
mandatory. Since listing all attributes as OPTIONAL would reduce the
usefulness of the above example, this inconsistency is deliberate.

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

In the pseudo JSON format snippets `?` means the preceding item is OPTIONAL,
`*` means the preceding item MAY appear zero or more times, and `+` means the
preceding item MUST appear at least once. The presence of the `#` character
means the remaining portion of the line is a comment. Whitespace characters in
the JSON snippets are used for readability and are not normative.

Use of the words `GROUP` and `RESOURCE` are meant to represent the singular
form of a Group and Resource type being used. While `GROUPs` and `RESOURCEs`
are the plural form of those respective types.

Use of acronyms and words in all capital letters (e.g. `ID`, `KEY`) typically
represent a field that will be replaced by its real value at runtime.

The following are used to denote an instance of one of the associated data
types (see [Attributes and Extensions](#attributes-and-extensions) for more
information about each data type):
- `ARRAY`
- `BOOLEAN`
- `DECIMAL`
- `INTEGER`
- `MAP`
- `OBJECT`
- `STRING`
- `TIME`
- `UINTEGER`
- `URI`
- `URIREFERENCE`
- `URITEMPLATE`
- `URL`
- `TYPE` - one of the allowable data type names (MUST be in lower case) listed
  in [Attributes and Extensions](#attributes-and-extensions)

### Terminology

This specification defines the following terms:

#### Group

An entity that acts as a collection of related Resources.

#### Registry

An implementation of this specification. Typically, the implementation would
include model specific Groups, Resources and extension attributes.

#### Resource

A Resource is typically the main entity that is stored within a Registry
Service. A Resource MUST exist within the scope of a Group and it MAY be
versioned.

## Registry Attributes and APIs

This section defines common Registry metadata attributes and APIs. It is an
explicit goal for this specification that metadata can be created and managed
in files in a file system, for instance in a Git repository, and also managed
in a Registry service that implements the API described here.

For instance, during development of a module, the metadata about the events
raised by the modules will best be managed in a file that resides alongside the
module's source code. When the module is ready to be deployed into a concrete
system, the metadata about the events will be registered in a Registry service
along with the endpoints where those events can be subscribed to or consumed
from, and which allows discovery of the endpoints and all related metadata by
other systems at runtime.

Therefore, the hierarchical structure of the Registry model is defined in such
a way that it can be represented in a single file, including but not limited
to JSON, or via the entity graph of a REST API.

In the remainder of this specification, in particular when defining the
attributes of the Registry entities, the terms "document view" or "API view"
will be used to indicate whether the serialization of the entity in question
is meant for use as a stand-alone document or as part of a REST API message
exchange - if there is a difference between the two usages.

### Attributes and Extensions

Unless otherwise noted, all attributes and extensions MUST be mutable and MUST
be one of the following data types:
- `any` - an attribute of this type is one whose type is not known in advance
   and MUST be one of the concrete types listed here.
- `array` - an ordered list of values that are all of the same data type - one
   of the types listed here.
   - Some serializations, such as JSON, allow for a `null` type of value to
     appear in array (e.g. `[ null, 2, 3 ]` in an array of integers). In these
     cases, while it is valid for the serialization being used, it is not
     valid for the xRegistry since `null` is not a valid `integer`. Meaning,
     the serialization of an array that is syntactically valid for the
     format being used, but not semantically valid per the xRegistry model
     definition MUST NOT be accepted and MUST generate an error.
- `boolean` - case sensitive `true` or `false`.
- `decimal` - number (integer or floating point).
- `integer` - signed integer.
- `map` - set of key/value pairs, where the key MUST be of type string. The
   value MUST be of one of the types defined here.
  - Each key MUST be a non-empty string consisting of only lowercase
    alphanumeric characters (`[a-z0-9]`), `-`, `_` or a `.`; be no longer
    than 63 characters; start with an alphanumeric character and be unique
    within the scope of this map.
  - See [Serializing Resource Documents](#serializing-resource-documents)
    for more information about serializing maps as HTTP headers.
- `object` - a nested entity made up of a set of attributes of these data types.
- `string` - sequence of Unicode characters.
- `time` - an [RFC3339](https://tools.ietf.org/html/rfc3339) timestamp.
- `uinteger` - unsigned integer.
- `uri` - absolute URI as defined in [RFC 3986 Section
  4.3](https://tools.ietf.org/html/rfc3986#section-4.3).
- `urireference` - URI-reference as defined in [RFC 3986
  Section 4.1](https://tools.ietf.org/html/rfc3986#section-4.1).
- `uritemplate` - URI Template as defined in
  [RFC 6570 Section 3.2.1](https://tools.ietf.org/html/rfc6570#section-3.2.1).
- `url` - URL as defined in
  [RFC 1738](https://datatracker.ietf.org/doc/html/rfc1738).

The "scalar" data types are: `boolean`, `decimal`, `integer`, `string`,
`time`, `uinteger`, `uri`, `urireference`, `uritemplate`, `url`.
Note that `any` is not a "scalar" type as its runtime value could be a complex
type such as `object`.

All attributes (specification defined and extensions) MUST adhere to the
following rules:
- Their names MUST be between 1 and 63 characters in length.
- Their names MUST only contain lowercase alphanumeric characters or an
  underscore (`[a-z0-9_]`) and MUST NOT start with a digit (`[0-9]`).
- For STRING attributes, an empty string is a valid value and MUST NOT be
  treated the same as an attribute with no value (or absence of the attribute).
- For scalar attributes, the string serialization of the attribute name and
  its value MUST NOT exceed 4096 bytes. This is to ensure that it can appear
  in an HTTP header without exceeding implementation limits (see
  [RFC6265/Limits](https://datatracker.ietf.org/doc/html/rfc6265#section-6.1)).
  In cases where larger amounts of data is needed, it is RECOMMENDED that
  an attribute (of type URL) be defined that references a separate
  document. For example, `documentation` can be considered such an attribute
  for `description`.
- If an attribute's type is not fully defined (i.e. it is defined as an `any`
  type) but a concrete type is needed to successfully process it, then the
  server SHOULD default it to type `string`. For example, if an extension is
  defined as a map whose values are of type `any`, but it appears in an HTTP
  header with a value of `5` (and it is not clear if this would be an integer
  or a string), if the server needs to convert this to a concrete data type,
  then `string` is the default choice.
- There might be cases when it is not possible to know whether a field name is
  part of an object (in which case it is an "attribute name"), or is part of
  a map (in which case it is a "key name"). This decision would impact
  verification of the field since key names allow for a superset of the
  characters allowed for attribute names. This will only happen when the
  `any` type has been used higher-up in the model. As a result, any portion of
  the entity that appears under the scope of an `any` typed attribute or
  map-value is NOT REQUIRED to be validated except to ensure that the syntax
  is valid per the rules of the serialization format used.

Implementations of this specification MAY define additional (extension)
attributes. However they MUST adhere to the following rules:

- All attributes MUST conform to the model definition of the Registry. This
  means that they MUST satisfy at least one of the following:
  - Be explicitly defined (by name) as part of the model.
  - Be permitted due to the presence of the `*` (undefined) extension attribute
    name at that level in the model.
  - Be permitted due to the presence of an `any` type for one of its parent
    attribute definitions.
- They MUST NOT change the semantics of the Registry - they MUST only be
  additional metadata to be persisted in the Registry since servers MUST
  persist all valid extensions.
  TODO is this really ok?
- They MUST NOT conflict with the name of an attribute defined by this
  specification, including the `RESOURCE*` and `COLLECTION*` attributes that
  are implicitly defined. Note that if a Resource type has the `hasdocument`
  attribute set the `false` then this rule does not apply for the `RESOURCE*`
  attributes as those attributes are not used for that Resource type.
- It is RECOMMENDED that extension attributes on different entities not use the
  same name unless they have the exact same semantic meaning
- It is STRONGLY RECOMMENDED that they be named in such a way as to avoid
  potential conflicts with future Registry specification attributes. For
  example, use of a model (or domain) specific prefix could be used.

#### Common Attributes

The following attributes are used by one or more entities defined by this
specification. They are defined here once rather than repeating them
throughout the specification.

For easy reference, the JSON serialization these attributes adheres to this
form:
- `"id": "STRING"`
- `"name": "STRING"`
- `"epoch": UINTEGER`
- `"self": "URL"`
- `"description": "STRING"`
- `"documentation": "URL"`
- `"labels": { "STRING": "STRING" * }`
- `"origin": "URI"`
- `"createdat": "TIME"`
- `"modifiedat": "TIME"`

The definition of each attribute is defined below:

##### `id` Attribute

- Type: String
- Description: An immutable unique identifier of the Registry, Group or
  Resource
- Constraints:
  - MUST be a non-empty string consisting of [RFC3986 `unreserved`
    characters](https://datatracker.ietf.org/doc/html/rfc3986#section-2.3)
    (ALPHA / DIGIT / "-" / "." / "_" / "~").
  - Note that in Versions, the `id` will be the `id` of the owning Resource
    and there will be a `versionid` that uniquely identifies the Version within
    the scope of its owning Resource. See the definition of `versionid` for
    additional information.
  - MUST be case insensitive unique within the scope of the entity's parent.
    In the case of the `id` for the Registry itself, the uniqueness scope will
    be based on where the Registry is used. For example, a publicly accessible
    Registry might want to consider using a UUID, while a private Registry
    does not need to be so widely unique.
  - This attribute MUST be treated as case sensitive for look-up purposes.
    This means that an HTTP request to an entity with the wrong case for its
    `id` MUST be treated as "not found".
  - In cases where an entity's `id` is specified outside of the serialization
    of the entity (e.g. part of a request URL, or a map key), its
    presence within the serialization of the entity is OPTIONAL. However, if
    present, it MUST be the same as any other specification of the `id`
    outside of the entity, and it MUST be the same as the entity's existing
    `id` if one exists, otherwise an HTTP `400 Bad Request` error MUST be
    generated.
  - MUST be immutable.
- Examples:
  - `a183e0a9-abf8-4763-99bc-e6b7fcc9544b`
  - `myEntity`
  - `myEntity.example.com`

Note, since `id` is immutable, in order to change its value a new entity would
need to be created with the new `id` that is a deep-copy of the existing entity.
Then the existing entity can be deleted.

##### `name` Attribute

- Type: String
- Description: A human readable name of the entity. This is often used
  as the "display name" for an entity rather than the `id` especially when
  the `id` might be something like a UUID. In cases where `name` is OPTIONAL
  and absent, the `id` value SHOULD be displayed in its place.

  Note that implementations MAY choose to enforce constraints on this value.
  For example, they could mandate that `id` and `name` be the same value.
  How any such requirement is shared with all parties is out of scope of this
  specification.
- Constraints:
  - If present, MUST be non-empty.
- Examples:
  - `My Endpoints`

##### `epoch` Attribute

- Type: Unsigned Integer
- Description: A numeric value used to determine whether an entity has been
  modified. Each time the associated entity is updated, this value MUST be
  set to a new value that is greater than the current one. This attribute
  MUST be updated for every update operation, even if no attributes were
  explicitly updated, such as a `PATCH` with no attributes. This then acts
  like a `touch` type of operation.

  Note, if a new Version of a Resource is created that is based on an
  existing Version of that Resource, then the new Version's `epoch` value MAY
  be reset (e.g. to zero) since the scope of its values is the Version and not
  the entire Resource.

  During a single write operation, whether this value is incremented for
  each modified attribute of an entity, or updated just once for the entire
  operation is an implementation choice.

  During a create operation, if this attribute is present in the request then
  it MUST be silently ignored by the server.

  During an update operation, if this attribute is present in the request then
  an error MUST be generated if the request includes a non-null value that
  differs from the existing value. A value of `null` MUST be treated the same
  as a request with no `epoch` attribute at all.
- Constraints:
  - MUST be an unsigned integer equal to or greater than zero.
  - MUST increase in value each time the entity is updated.
- Examples:
  - `0`, `1`, `2`, `3`

##### `self` Attribute

- Type: URL
- Description: A unique absolute URL for an entity. In the case of pointing
  to an entity in a [Registry Collection](#registry-collections), the URL MUST
  be a combination of the base URL for the collection appended with the `id`
  of the entity.

  When this URL references a Resource or Version, it MUST include `$meta`
  appended to its `id` if the request asked for the serialization of the
  xRegistry metadata. This would happen when `$meta` was used in the request,
  or when the Resource (or Version) is included in the serialization of a
- Constraints:
  - MUST be a non-empty absolute URL.
  - MUST be a read-only attribute in API view.
- Examples:
  - `https://example.com/registry/endpoints/123`

##### `description` Attribute

- Type: String
- Description: A human readable summary of the purpose of the entity.
- Constraints:
  - None
- Examples:
  - `A queue of the sensor generated messages`

##### `documentation` Attribute

- Type: URL
- Description: A URL to additional information about this entity.
  This specification does not place any constraints on the data returned from
  an HTTP `GET` to this URL.
- Constraints:
  - If present, MUST be a non-empty URL.
  - MUST support an HTTP(s) `GET` to this URL.
- Examples:
  - `https://example.com/docs/myQueue`

##### `labels` Attribute

- Type: Map of name/value string pairs
- Description: A mechanism in which additional metadata about the entity can
  be stored without changing the schema of the entity.
- Constraints:
  - If present, MUST be a map of zero or more name/value string pairs. See
    [Attributes and Extensions](#attributes-and-extensions) for more
    information.
  - Keys MUST be non-empty strings.
  - Values MAY be empty strings.
- Examples:
  - `"labels": { "owner": "John", "verified": "" }` when in the HTTP body
  - `xRegistry-labels-owner: John` <br>
    `xRegistry-labels-verified:`  when in HTTP headers

  Note: HTTP header values can be empty strings but some client-side tooling
  might make it challenging to produce them. For example, `curl` requires
  the header to be specified as `-HxRegistry-labels-verified;` - notice the
  semi-colon(`;`) is used instead of colon(`:`). So, this might be something
  to consider when choosing to use labels that can be empty strings.

##### `origin` Attribute

- Type: URI
- Description: A URI reference to the original source of the entity. This
  can be used to locate the true authority owner of the entity in cases of
  distributed Registries. If this attribute is absent its default value
  is the value of the `self` attribute and in those cases its presence in the
  serialization of the entity is OPTIONAL.
- Constraints:
  - OPTIONAL if this Registry is the authority owner.
  - REQUIRED if this Registry is not the authority owner.
  - If present, MUST be a non-empty URI.
- Examples:
  - `https://example2.com/myregistry/endpoints/9876`

##### `createdat` Attribute

- Type: Timestamp
- Description: The date/time of when the entity was created.
- Constraints:
  - MUST be a [RFC3339](https://tools.ietf.org/html/rfc3339) timestamp.
  - When present in a write operation request, the value MUST override any
    existing value, however a value of `null` MUST use the current date/time
    as the new value.
  - When absent in a write operation request, any existing value MUST remain
    unchanged, or if not present, set to the current date/time
  - In cases where the `createdat` attribute is set to the current date/time
    on multiple entities within the same operation, the same value MUST be
    applied to all of the entities.
- Examples:
  - `2030-12-19T06:00:00Z`

##### `modifiedat` Attribute

- Type: Timestamp
- Description: The date/time of when the entity was last updated
- Constraints:
  - MUST be a [RFC3339](https://tools.ietf.org/html/rfc3339) timestamp
    representing the time when the entity was last updated.
  - Any update operation (even one that does not change any attribute, such as
    a `PATCH` with no attributes provided), MUST update this attribute. This
    then acts like a `touch` type of operation.
  - Upon creation of a new entity, this attribute MUST match the `createdat`
    attribute's value.
  - Setting an entity's `modifiedat` value MUST NOT update any parent
    entity's `modifiedat` value.
  - When present in a write operation request, the following applies:
    - If the request value is the same as the existing value, then the
      current date/time MUST be used as its new value.
    - If the request value is different than the existing value, then the
      request value MUST be used as its new value.
    - If the request value is `null` then the current date/time MUST be used
      as the new value.
  - When absent in a write operation request, it MUST be set to the current
    date/time.
  - In cases where the `modifiedat` attribute is set to the current date/time
    on multiple entities within the same operation, the same value MUST be
    applied to all of the entities.
- Examples:
  - `2030-12-19T06:00:00Z`

---

### Registry APIs

This specification defines the following API patterns:

```yaml
/                                               # Access the Registry
/model                                          # Access the model definitions
/GROUPs                                         # Access a Group Type
/GROUPs/gID                                     # Access a Group
/GROUPs/gID/RESOURCEs                           # Access a Resource Type
/GROUPs/gID/RESOURCEs/rID                       # Default Version of a Resource
/GROUPs/gID/RESOURCEs/rID/versions              # Versions of a Resource
/GROUPs/gID/RESOURCEs/rID/versions/vID          # Access a Version of a Resource
```

Where:
- `GROUPs` is a Group type name (plural). e.g. `endpoints`.
- `GROUP`, not shown, is the singular name of a Group type.
- `gID` is the `id` of a single Group.
- `RESOURCEs` is a Resource type name (plural). e.g. `definitions`.
- `RESOURCE`, not shown, is the singular name of a Resource type.
- `rID` is the `id` of a single Resource.
- `vID` is the `versionid` of a single Version of a Resource.

These acronym definitions apply to the remainder of this specification.

While these APIs are shown to be at the root path of a Registry Service,
implementation MAY choose to prefix them as necessary. However, the same
prefix MUST be used consistently for all APIs in the same Registry instance.

Support for any particular API defined by this specification is OPTIONAL,
however it is STRONGLY RECOMMENDED that server-side implementations support at
least the "read" (e.g. HTTP `GET`) operations. Implementations MAY choose to
incorporate authentication and/or authorization mechanisms for the APIs.
If an API is not supported by the server then a `405 Method Not Allowed`
HTTP response MUST be generated.

This specification attempts to follow a standard REST/HTTP processing model.
The following key aspects are called out to help understand the overall
pattern of the APIs:
- A `PUT` or `POST` operation is a full replacement of the entities being
  processed. Any missing attributes will be interpreted as a request for them
  to be deleted. However, attributes that are managed by the server might have
  specialized processing in those cases.
- A `PATCH` operation will only modify the attributes explicitly mentioned
  in the request. Any attribute with a value of `null` will be interpreted
  as a request to delete the attribute, and as with `PUT`/`POST`, server
  managed attributes might have specialized processing.
- On write operations, without a
  [`nested`](#updating-nested-registry-collections) query parameter,
  any included xRegistry collections are ignored. In other words, the
  operation will only modify the targeted entities, not any nested
  collections/entities.
- `PUT` or `PATCH ` can not be targeted at xRegistry collections. A `POST`
  would need to be used instead to add entities to the collection, and a
  `DELETE` might also be needed to delete unwanted entities.
- `POST` operations can only be targeted at xRegistry collections, not
  individual entities - with the exception of a Resource entity. In that case
  a `POST` to a Resource URL is treated as an alias for a `POST` to the
  Resource's `versions` collection.

There might be situations where someone will do a `GET` to retrieve data
from a Registry, and then do an update operation to a Registry with that data.
Depending on the use case, they might not want some of the retrieved data
to be applied during the update - for example, they might not want the
`epoch` validation checking to occur. Rather than forcing the user to edit
the data to remove the potentially problematic attributes, the following
query parameters MAY be included on write operations to control certain
aspects of the processing:
- `noepoch` - presence of this query parameter indicates that any `epoch`
  attribute included in the request MUST be ignored.
- `nodefaultversionid` - presence of this query parameter indicates that any
  `defaultversionid` attribute included in the request MUST be ignored.
- `nodefaultversionsticky` - presence of this query parameter indicates that
  any `defaultversionsticky` attribute included in the request MUST be ignored.

#### No-Code Servers

One of the goals of xRegistry is to be as broadly supported as possible.
Requiring all xRegistry endpoints to support the full range of APIs defined
in this specification might not be feasible in all cases. In particular, there
might be cases where someone wishes to host a read-only xRegistry server to
only expose their documents (and metadata) and therefore the write operations
or advanced features (such as inlining or filtering) might not be needed.
In those cases, simple file serving HTTP servers, such as blob stores, ought
to be sufficient, and in those cases requiring support for query parameters
and other advanced features (that could require code) might not always be
possible.

To support these simple (no-code) scenarios, this specification is written
such that all of the APIs are OPTIONAL, and all of the query parameters on
the read operations are OPTIONAL (typically specified by saying that they
`SHOULD` be supported). However, it is STRONGLY RECOMMENDED that full API
servers support the query parameters when possible to enable a better user
experience, and increase interoperability.

---

The remainder of this specification mainly focuses on the successful interaction
patterns of the APIs. For example, most examples will show an HTTP "200 OK"
as the response. Each implementation MAY choose to return a more appropriate
response based on the specific situation. For example, in the case of an
authentication error the server could return `401 Unauthorized`.

The following sections define the APIs in more detail.

---

#### Registry Collections

Registry collections (`GROUPs`, `RESOURCEs` and `versions`) that are defined
by the [Registry Model](#registry-model) MUST be serialized according to the
rules defined below.

The serialization of a collection is done as 3 attributes and adheres to this
form:

```yaml
"COLLECTIONsurl": "URL",
"COLLECTIONscount": UINTEGER,
"COLLECTIONs": {
  # Map of entities in the collection, key is the "id" for Groups and
  # Resources, and "versionid" for Versions
}
```

Where:
- The term `COLLECTIONs` MUST be the plural name of the collection
  (e.g. `endpoints`, `versions`).
- The `COLLECTIONsurl` attribute MUST be an absolute URL that can be used to
  retrieve the `COLLECTIONs` map via an HTTP(s) `GET` (including any necessary
  [filter](#filtering)) and MUST be a read-only attribute that MUST be silently
  ignored by a server during a write operation. An empty collection MUST
  return an HTTP 200 with an empty map (`{}`).
- The `COLLECTIONscount` attribute MUST contain the number of entities in the
  `COLLECTIONs` map (after any necessary [filtering](#filtering)) and MUST
  be a read-only attribute that MUST be silently ignored by a server during
  an write operation.
- The `COLLECTIONs` attribute is a map and MUST contain the entities of the
  collection (after any necessary [filtering](#filtering)), and MUST use
  the Group's `id`, Resource's `id` or Version's `versionid` as the key for
  that map entry.
- The key of each entity in the collection MUST be unique within the scope of
  the collection.
- The specifics of whether each attribute is REQUIRED or OPTIONAL will be
  based whether document or API view is being used - see the next section.

When the `COLLECTIONs` attribute is expected to be present in the
serialization, but the number of entities in the collection is zero, it MUST
still be included as an empty map (e.g. `{}`).

The set of entities that are part of the `COLLECTIONs` attribute is a
point-in-time view of the Registry. There is no guarantee that a future `GET`
to the `COLLECTIONsurl` will return the exact same collection since the
contents of the Registry might have changed.

Since collections could be too large to retrieve in one request, when
retrieving a collection the client MAY request a subset by using the
[pagination specification](../pagination/spec.md). Likewise, the server
MAY choose to return a subset of the collection using the same mechanism
defined in that specification even if the request didn't ask for pagination.
The pagination specification MUST only be used when the request is directed at
a collection, not at its owning entity (such as the root of the Registry,
or at an individual Group or Resource).

In the remainder of the specification, the presence of the `Link` HTTP header
indicates the use of the [pagination specification](../pagination/spec.md)
MAY be used for that API.

The requirements on the presence of the 3 `COLLECTIONs` attributes varies
between Document and API views, and is defined below:

##### Document view

In document view:
- `COLLECTIONsurl` and `COLLECTIONscount` are OPTIONAL.
- `COLLECTIONs` is REQUIRED.

##### API view

In API view:
- `COLLECTIONsurl` and `COLLECTIONscount` are REQUIRED for responses even if
  there are no entities in the collection.
- `COLLECTIONsurl` and `COLLECTIONscount` are OPTIONAL for requests and MUST
   be silently ignored by the server if present.
- `COLLECTIONs` is OPTIONAL for responses and MUST only be included if the
  request included the [`inline`](#inlining) query parameter indicating that
  this collection's entities are to be returned.
- `COLLECTIONs` is OPTIONAL for requests and MUST be silently ignored if
  the [`nested`](#updating-nested-registry-collections) query parameter is not
  present. See [Updating Nested Registry
  Collections](#updating-nested-registry-collections) for more details.

##### Updating Nested Registry Collections

When updating an entity that can contain Registry collections, the request
MAY contain the 3 collection attributes. The `COLLECTIONsurl` and
`COLLECTIONscount` attributes MUST be silently ignored by the server.
By default, in the absence of a `nested` query parameter, the server MUST
ignore the `COLLECTIONs` attribute as well.

If the `nested` query parameter and the `COLLECTIONs` attribute are both
present, the server MUST process each entity in the collection map as a
request to create or update that entity according to the semantics of the HTTP
method used. An entry in the map that isn't a valid entity (e.g. is `null`)
MUST generate an error.

The `nested` semantics MUST be applied to all nested `COLLECTIONs` attributes
within the request regardless of the level in the hierarchy in which they
appear.

For example:

```yaml
PUT https://example.com/endpoints/123?nested

{
  "id": "123",
  "name": "A cool endpoint",

  "definitions": {
    "mydef1": { ... },
    "mydef2:" { ... }
  }
}
```

Will not only create/update an `endpoint` Group with an `id` of `123` but will
also create/update its `definition` Resources (`mydef1` and `mydef2`).

Any error while processing a nested collection entity MUST result in the entire
request being rejected.

An absent `COLLECTIONs` attribute MUST be interpreted as a request to not
modify the collection at all, regardless of the presence (or absence) of the
`nested` query parameter.

If a client wishes to replace an entire collection, rather than just add new
entities, the client MUST use one of the `DELETE` operations on the collection
first.

In cases where an update operation includes attributes meant to be applied
to the "default" Version, and the incoming inlined `versions` collections
includes that "default" Version, the Resource's default Version attributes MUST
be silently ignored. This is to avoid any possible conflicting data between
the two sets of data for that Version. In other words, the Version attributes
in the incoming `versions` collection wins. Note that Resource specific
attributes (e.g. `defaultversionsticky`) are not affected by this rule as
they are not Version attributes.

To better understand this scenario, consider the following HTTP request to
update a Definition where the `defaultversionid` is `v1`:

```yaml
PUT http://example.com/endpoints/123/definitions/456?nested

{
  "id": "456",
  "versionid": "v1",
  "name": "Blob Created",
  "defaultversionid": "v1",
  "createdat": "2024-04-30T12:00:00Z",
  "modifiedat": "2024-04-30T12:00:01Z",
  "versions": {
    "v1": {
      "id": "456"
      "versionid": "v1",
      "name": "Blob Created Definition",
      "createdat": "2024-04-30T12:00:00Z",
      "modifiedat": "2024-04-30T12:00:01Z"
    }
  }
}
```

If the `versions` collection were not present with the `v1` entity, or if the
`nested` query parameter was not provided, then the top-level attributes would
be used to update the default Version (`v1` in this case). However, because
they are present, the request to update `v1` becomes ambiguous because it is
not clear if the server is meant to use the top-level attributes or if it
is to use the attributes under the `v1` entity of the `versions` collection.
When both sets of attributes are the same then it does not matter. However, in
this cases the `name` attributes have different values. The paragraph above
mandates that in these potentially ambiguous cases the entity in the
`versions` collection is to be used and the top-level attributes are to be
ignored - for the purposes of updating the "default" Version's attributes.
So, in this case the `name` of the default(`v1`) Version will be
`Blob Created Definition`.

---

#### Entity Processing Rules

Rather than repeating the processing rules for each type of xRegistry
entity or Registry collection, the overall pattern is defined once in this
section and any entity, or collection, specific rules will be detailed in the
appropriate section in the specification.

##### Creating or Updating Entities
This defines the general rules for how to update entities.

Creating or updating entities MAY be done using HTTP `PUT`, `PATCH` or `POST`
methods:
- `PUT    PATH-TO-ENTITY[?OPTIONS]`           # Process a single entity
- `PATCH  PATH-TO-ENTITY[?OPTIONS]`           # Process a single entity
- `POST   PATH-TO-COLLECTION[?OPTIONS]`       # Process a set of entities

Based on the entity being processed, the `OPTIONS` available will vary.

The `PUT` variant MUST adhere to the following:
  - The URL MUST be of the form: `PATH-TO-ENTITY`.
  - The HTTP body MUST contain the full updated serialization of the entity to
    be processed.
  - The entity processed MUST either be created (if it does not already
    exist), or updated (if it does exist).
  - Any mutable attribute which is either missing or present with a value of
    `null`, MUST be interpreted as a request to delete the attribute.
  - Excluding any Registry collection attributes, all mutable attributes
    specified MUST be a full serialization of the attribute. Any missing
    attribute MUST be interpreted as a request to delete the attribute.

The `POST` variant MUST adhere to the following:
  - The HTTP body MUST contain a JSON map where the key MUST be the `id` of
    each entity in the map. Note, that in the case of a map of Versions, the
    `versionid` is used instead.
  - Each value in the map MUST be the full serialization of the entity to be
    either added or updated. Note that `POST` does not support deleting
    entities from a collection, so a separate delete operation might be needed
    if there are entities that need to be removed.
  - The processing of each individual entity in the map MUST follow the same
    rules as defined for `PUT` above.

The `PATCH` variant MUST adhere to the `PUT` semantics defined above with the
following exceptions:
  - Any mutable attribute which is missing MUST be interpreted as a request to
    leave it unchanged. However, modifying some other attribute (or some other
    server semantics) MAY modify it. A value of `null` MUST be interpreted as
    a request to delete the attribute.
  - When using `PATCH` for a Resource or Version, `$meta` MUST be appended
    to the path of the URL since, when it is absent, the processing of the HTTP
    `xRegistry-` headers is already defined with "patch" semantics.
  - `PATCH` MAY be used to create new entities, but as with any of the create
    operations, any missing REQUIRED attributes MUST generate an error.

Note: when processing Resources and Versions, based on the presence of `$meta`
(see the [Resource Metadata vs Resource
Document](#resource-metadata-vs-resource-document) section), the HTTP body MAY
contain the serialization of the entity's xRegistry metadata, or that metadata
MAY appear as HTTP headers. For the remainder of this section any discussion
of the entity's xRegistry attributes applies regardless of where the
attribute appears.

When serialized as JSON, each individual entity's serialization MUST adhere to
the following:

```yaml
{
  "id": "ID", ?
  # Note that Versions will also (optionally) have "versionid"
  ... remaining entity attributes ...

  # Repeat for each nested Registry collection in the entity
  "COLLECTIONsurl": "URL", ?                       # e.g. "endpointsurl"
  "COLLECTIONscount": UINTEGER", ?                 # e.g. "endpointscount"
  "COLLECTIONs": { map of COLLECTION entities } ?  # If inlined/nested
}
```

The processing of each individual entity follows the same set of rules:
- If an entity with the specified `id` (or `versionid` in the case of Versions)
  already exists then it MUST be interpreted as a request to update the
  existing entity. Otherwise, it MUST be interpreted as a request to create a
  new entity with that value.
- See the definition of each attribute for the rules governing how it is
  processed.
- All attributes present MUST be a full representation of its value. This means
  any complex attributes (e.g. object, maps), MUST be fully replaced by the
  incoming value.
- A request to update, or delete, a read-only attribute MUST be silently
  ignored.
- A request to update a mutable attribute with an invalid value MUST generate
  an error (this includes deleting a mandatory mutable attribute).
- Any Registry collection attributes MUST be processed per the rules specified
  in the [Updating Nested Registry
  Collections](#updating-nested-registry-collections) section.
- Any error during the processing of an entity, or its nested entities, MUST
  result in the entire request being rejected and no updates performed.

A successful response MUST be the same as a `GET` to the entity (or entities)
processed without any query parameters, showing their current representation,
with the following exceptions:
- In the `POST` case, the result MUST contain only the entities processed,
  not the entire Registry collection, nor any entities deleted as a result
  of processing the request.
- In the `PUT` or `PATCH` cases, for a newly created entity, the HTTP status
  MUST be `201 Created`, and it MUST include an HTTP `Location` header with a
  URL to the newly created entity. Note that this URL MUST be the same as the
  `self` attribute of that entity.

Otherwise an HTTP `200 OK` without an HTTP `Location` header MUST be returned.

When serialized in the HTTP body, each individual entity's serialization in a
successful response MUST adhere to the following:

```yaml
{
  "id": "ID",
  # Note that Versions will also (optionally) have "versionid"
  ... remaining entity attributes ...

  # Repeat for each nested Registry collection in the entity
  "COLLECTIONsurl": "URL",                          # e.g. "endpointsurl"
  "COLLECTIONscount": UINTEGER"                     # e.g. "endpointscount"
}
```

Note that the response MUST NOT include any inlinable attributes (such as
nested Registry collections, or `RESOURCE`/`RESOURECEbase64` attributes).

##### Retrieving a Registry Collection

To retrieve a Registry collection, an HTTP `GET` MAY be used. The request
MUST be of the form:

```yaml
GET PATH-TO-COLLECTION[?inline=...&filter=...&export]
```

The following query parameters SHOULD be supported by servers:
- `inline` - See [inlining](#inlining) for more information.
- `filter` - See [filtering](#filtering) for more information.
- `export` - See [exporting](#exporting) for more information.

A successful response MUST be of the form:

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Link: <URL>;rel=next;count=UINTEGER ?

{
  "ID": {
    "id": "ID",
    # Note that Versions will also have "versionid"
    ... remaining entity attributes ...

    # Repeat for each nested Registry collection in the entity
    "COLLECTIONsurl": "URL",                         # e.g. "endpointsurl"
    "COLLECTIONscount": UINTEGER",                   # e.g. "endpointscount"
    "COLLECTIONs": { map of COLLECTION entities } ?  # If inlined
  } *
}
```

##### Retrieving an Entity from a Registry Collection

To retrieve an entity, an HTTP `GET` MAY be used. The request MUST be of the
form:

```yaml
GET PATH-TO-COLLECTION/ID-OF-ENTITY[?inline=...&filter=...&export]
```

The following query parameters SHOULD be supported by servers:
- `inline` - See [inlining](#inlining) for more information.
- `filter` - See [filtering](#filtering) for more information.
- `export` - See [exporting](#exporting) for more information.

A successful response MUST be of the form:

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "id": "STRING",
  # Note that Versions will also have "versionid"
  ... remaining entity attributes ...

  # Repeat for each nested Registry collection in the entity
  "COLLECTIONsurl": "URL",                         # e.g. "endpointsurl"
  "COLLECTIONscount": UINTEGER",                   # e.g. "endpointscount"
  "COLLECTIONs": { map of COLLECTION entities } ?  # If inlined
}

##### Deleting Entities in a Registry Collection

There are two ways to delete entities from a Registry collection:

1. to delete a single entity, an HTTP `DELETE` MAY be used. The request MUST
be of the form:

```yaml
DELETE PATH-TO-COLLECTION/ID-OF-ENTITY[?epoch=UINTEGER]
```

Where:
- The request body SHOULD be empty.
- If the entity can not be found, then an HTTP `404 Not Found` error MUST
  be generated.

The following query parameter MUST be supported by servers:
- `epoch`<br>
  The presence of this query parameter indicates that the server MUST check
  to ensure that the `epoch` value matches the entity's current `epoch` value
  and if it differs then an error MUST be generated.

2. to delete multiple entities the request MUST be of the form:

```yaml
DELETE PATH-TO-COLLECTION

{
  "KEY": {
    "epoch": UINTEGER ?
    # Remainder of entity serialization is OPTIONAL
  } *
} ?
```

Where:
- If the request body is empty (no map), then all entities in this collection
  MUST be deleted.
- If the request body is not empty, then it MUST be a map containing zero or
  more entries where the key of each entity is each entity's unique
  identifier - which is the `id` for Groups and Resources, and the `versionid`
  for Versions.
- If an `epoch` value is specified for an entity then the server MUST check
  to ensure that the value matches the entity's current `epoch` value and if it
  differs then an error MUST be generated.
- If the entity's unique identifier is present in the object, then it MUST
  match its corresponding key value. And for Versions, if `id` is present
  then it MUST match the Resource ID specified in the URL.
- Any other entity attributes that are present in the request MUST be silently
  ignored.
- If one of the referenced entities can not be found then the server MUST
  silently ignore this condition and not treat it as an error.

Whether the request is to delete a single entity or multiple, deleting an
entity MUST delete all children entities as well - meaning, any entities
within any nested Registry collections.

Any error MUST result in the entire request being rejected.

A successful response MUST return either:

```yaml
HTTP/1.1 204 No Content
```

with an empty HTTP body, or:

```yaml
HTTP/1.1 200 OK
```

if, as an extension, the server chooses to return additional data in the
HTTP body.

---

### Registry Entity

The Registry entity represents the root of a Registry and is the main
entry-point for traversal and discovery.

The serialization of the Registry entity adheres to this form:

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
  "createdat": "TIME",
  "modifiedat": "TIME",

  "model": { Registry model }, ?      # Only if "?model" is on request

  # Repeat for each Group type
  "GROUPsurl": "URL",                 # e.g. "endpointsurl"
  "GROUPscount": UINTEGER,            # e.g. "endpointscount"
  "GROUPs": { GROUPs collection } ?   # Only if inlined
}
```

The Registry entity includes the following common attributes:
- [`id`](#id-attribute) - REQUIRED in responses and document view, otherwise
  OPTIONAL
- [`name`](#name-attribute) - OPTIONAL
- [`epoch`](#epoch-attribute) - REQUIRED in responses, otherwise OPTIONAL
- [`self`](#self-attribute) - REQUIRED in responses, otherwise OPTIONAL
- [`description`](#description-attribute) - OPTIONAL
- [`documentation`](#documentation-attribute) - OPTIONAL
- [`labels`](#labels-attribute) - OPTIONAL
- [`createdat`](#createdat-attribute) - REQUIRED in responses, otherwise
  OPTIONAL
- [`modifiedat`](#modifiedat-attribute) - REQUIRED in responses, otherwise
  OPTIONAL

and the following Registry specific attributes:

##### `specversion` Attribute
- Type: String
- Description: The version of this specification that the serialization
  adheres to
- Constraints:
  - REQUIRED in responses, OPTIONAL in requests.
  - REQUIRED in document view.
  - MUST be a read-only attribute in API view.
  - If present, MUST be non-empty.
- Examples:
  - `1.0`

##### `model` Attribute
- Type: Registry Model
- Description: A description of the features, extension attributes, Groups and
  Resources supported by this Registry. See [Registry Model](#registry-model)
- Constraints:
  - OPTIONAL.
  - MUST NOT be included in responses unless requested.
  - MUST be included in responses if requested.
  - SHOULD be included in document view when the model is not known in advance.

##### `GROUPs` Collections
- Type: Set of [Registry Collections](#registry-collections)
- Description: A list of Registry collections that contain the set of Groups
  supported by the Registry.
- Constraints:
  - REQUIRED in responses, MAY be present in requests.
  - REQUIRED in document view.
  - If present, it MUST include all nested Group Collection types in the
    Registry, even if some of the collections are empty.

#### Retrieving the Registry

To retrieve the Registry, its metadata attributes and Groups, an HTTP `GET`
MAY be used.

The request MUST be of the form:

```yaml
GET /[?model&specversion=...&inline=...&filter=...&export]
```

The following query parameters SHOULD be supported by servers:
- `model`<br>
  The presence of this OPTIONAL query parameter indicates that the request is
  asking for the Registry model to be included in the response. See
  [Registry Model](#registry-model) for more information.
- `specversion`<br>
  The presence of this OPTIONAL query parameter indicates that the response
  MUST adhere to the xRegistry specification version specified. If the
  version is not supported then an error MUST be generated. Note that this
  query parameter MAY be included on any API request to the server not just the
  root of the Registry. When not present, the default value is the newest
  version of this specification supported by the server.
- `inline` - See [inlining](#inlining) for more information.
- `filter` - See [filtering](#filtering) for more information.
- `export` - See [exporting](#exporting) for more information.

A successful response MUST be of the form:

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "specversion": "STRING",
  "id": "STRING",
  "name": "STRING", ?
  "epoch": UINTEGER,
  "self": "URL",
  "description": "STRING", ?
  "documentation": "URL", ?
  "labels": { "STRING": "STRING" * }, ?
  "createdat": "TIME",
  "modifiedat": "TIME",

  "model": { Registry model }, ?      # Only if "?model" is present

  # Repeat for each Group type
  "GROUPsurl": "URL",                 # e.g. "endpointsurl"
  "GROUPscount": UINTEGER,            # e.g. "endpointscount"
  "GROUPs": { GROUPs collection } ?   # Only if inlined
}
```

**Examples:**

Retrieve a Registry that has 2 types of Groups (`endpoints` and
`schemagroups`):

```yaml
GET /
```

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "specversion": "0.5",
  "id": "987654321",
  "epoch": 1,
  "self": "https://example.com/",
  "createdat": "2024-04-30T12:00:00Z",
  "modifiedat": "2024-04-30T12:00:01Z",

  "endpointsurl": "https://example.com/endpoints",
  "endpointscount": 42,

  "schemagroupsurl": "https://example.com/schemagroups",
  "schemagroupscount": 1
}
```

Another example where:
- The request asks for the model to included in the response.
- The `endpoints` Group has one extension attribute defined.
- The request asks for the `schemagroups` Group to be inlined in the response.

```yaml
GET /?model&inline=schemagroups

HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "specversion": "0.5",
  "id": "987654321",
  "epoch": 1,
  "self": "https://example.com/",
  "createdat": "2024-04-30T12:00:00Z",
  "modifiedat": "2024-04-30T12:00:01Z",

  "model": {
    "schemas": [ "xRegistry-json", "jsonSchema/2020-12" ],
    ... xRegistry spec defined attributes excluded for brevity ...
    "groups": {
      "endpoints": {
        "plural": "endpoints",
        "singular": "endpoint",
        "attributes": {
          ... xRegistry spec defined attributes excluded for brevity ...
          "shared": {
            "name": "shared",
            "type": "boolean"
          }
        },

        "resources": {
          "definitions": {
            "plural": "definitions",
            "singular": "definition",
            "attributes": {
              ... xRegistry spec defined attributes excluded for brevity ...
              "*": {
                type: "any"
              }
            },
            "maxversions": 1
          }
        }
      },
      "schemagroups": {
        "plural": "schemagroups",
        "singular": "schemagroup",
        ... xRegistry spec defined attributes excluded for brevity ...

        "resources": {
          "schemas": {
            "plural": "schemas",
            "singular": "schema",
            ... xRegistry spec defined attributes excluded for brevity ...
            "maxversions": 1
          }
        }
      }
    }
  },

  "endpointsurl": "https://example.com/endpoints",
  "endpointscount": 42,

  "schemagroupsurl": "https://example.com/schemagroups",
  "schemagroupscount": 1,
  "schemagroups": {
    "mySchemas": {
      "id": "mySchemas",
      # Remainder of schemagroup is excluded for brevity
    }
  }
}
```

#### Updating the Registry Entity

To update the Registry entity, an HTTP `PUT` or `PATCH` MAY be used.

The request MUST be of the form:

```yaml
PUT /[?nested&model]
or
PATCH /[?nested&model]
Content-Type: application/json; charset=utf-8

{
  "id": "STRING", ?
  "epoch": UINTEGER, ?
  "name": "STRING", ?
  "description": "STRING", ?
  "documentation": "URL", ?
  "labels": { "STRING": "STRING" * }, ?
  "createdat": "TIME", ?
  "modifiedat": "TIME", ?

  "model": { Registry model }, ?

  # Repeat for each Group type
  "GROUPs": { GROUPs collection } ?   # Only if "?nested" is present
}
```

Where:
- The HTTP body MUST contain the full JSON representation of the Registry
  entity's mutable attributes.
- The request MAY include the `'model` attribute if the Registry model
  definitions are to be updated as part of the request. See [Updating the
  Registry Model](#updating-the-registry-model) for more information.

The following query parameter SHOULD be supported by servers:
- `nested` - See
   [Updating Nested Registry
   Collections](#updating-nested-registry-collections) for more information.
- `model` - when present, if the `model` attribute is also present then the
  Registry's model MUST be updated prior to any entities being updated. A
  value of `null` MUST generate an error. If the `model` attribute is present
  but the `model` query parameter is not, then the `model` attribute MUST be
  silently ignored.

A successful response MUST include the same content that an HTTP `GET`
on the Registry would return, and be of the form:

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "specversion": "STRING",
  "id": "STRING",
  "name": "STRING", ?
  "epoch": UINTEGER,
  "self": "URL",
  "description": "STRING", ?
  "documentation": "URL", ?
  "labels": { "STRING": "STRING" * }, ?
  "createdat": "TIME",
  "modifiedat": "TIME",

  # Repeat for each Group type
  "GROUPsurl": "URL",
  "GROUPscount": UINTEGER
}
```

Note that the response MUST NOT include the `model` attribute, nor any
inlined GROUPs collections.

**Examples:**

Updating a Registry's metadata

```yaml
PUT /
Content-Type: application/json; charset=utf-8

{
  "id": "987654321",
  "name": "My Registry",
  "description": "An even cooler registry!"
}
```

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "specversion": "0.5",
  "id": "987654321",
  "name": "My Registry",
  "epoch": 2,
  "self": "https://example.com/",
  "description": "An even cooler registry!",
  "createdat": "2024-04-30T12:00:00Z",
  "modifiedat": "2024-04-30T12:00:01Z",

  "endpointsurl": "https://example.com/endpoints",
  "endpointscount": 42,

  "schemagroupsurl": "https://example.com/schemagroups",
  "schemagroupscount": 1
}
```

---

### Registry Model

The Registry model defines the Groups, Resources, extension attributes and
changes to specification defined attributes. This information is
intended to be used by tooling that does not have knowledge of the structure of
the Registry in advance and therefore will need to dynamically discover it.

To enable support for a wide range of use cases, but to also ensure
interoperability across implementations, the following rules have been defined
with respect to how models are defined or updated:
- Specification defined attributes that are `serverrequired` MUST NOT have
  this aspect changed to `false`.
- Specification defined attributes that are `readonly` and `serverrequired`
  MUST NOT have the `readonly` aspect changed to `false`.
- The `name` and `type` aspects of attributes MUST NOT be changed.

Changes to specification defined attributes MAY be included in the request.
Any specification attributes not included in the request MUST be included in
the resulting model. In other words, the Registry's model consists of the
specification defined attributes overlaid with the attributes that are
explicitly defined as part of an update request.

Note: there is no mechanism defined to delete specification defined attributes
from the model.

Registries MAY support extensions to the model (meaning, new attributes within
the model definitions themselves, e.g. a sibling to `schemas`), but only if
the server supports it. Servers MUST reject model definitions that include
unknown model extensions.

Once a Registry has been created, implementations MAY choose to limit the
types of changes made to the model - for example, to ensure backwards
compatibility of clients or to ensure existing entities do not need to be
changed to be consistent with the new model.

Implementations are REQUIRED to ensure that after any model changes are made,
all of the entities in the Registry are valid with respect to the new model
definition (including all Versions of Resources). How this is achieved will
be implementation specific. For example, implementations can choose to
automatically modify existing entities, or even to delete non-conforming
entities (such as when Groups or Resource types are removed). However, it is
STRONGLY RECOMMENDED that implementations not delete entities due to attribute
modifications.

When model changes are made, it might be necessary to modify existing entity's
attributes to ensure they are conformant with the new model. The following
ordered suggestions are defined to provide consistency across implementations,
but it is NOT REQUIRED for implementations to follow these rules if a
different set of changes are more appropriate:
- If a `default` value is defined for the attribute, then it SHOULD be used.
- If the attribute is OPTIONAL, then the attribute SHOULD be deleted.
- If an enum defined and `strict` is `true`, the first `enum` value SHOULD be
  used.
- If valid, the zero value for the attribute's type SHOULD be used:
  - Array, Map, Object: empty value (e.g. `[]`, `{}`, `{}` respectively).
  - Boolean: false.
  - Numeric: zero.
  - String, URI, URIReference, URI-Template, URL: empty string (`""`).
  - Time: zero (00:00:00 UTC Jan 1, 1970).
- If valid, String attributes SHOULD use `"undefined"`.

If a backwards incompatible change is needed, and the existing entities need
to be preserved, then it is RECOMMENDED that a new Group or Resource be
defined for future instances of those entities.

The xRegistry schema for an empty Registry can be found [here](./model.json),
while a schema for a sample xRegistry (with Groups and Resources) can be
found [here](./sample-model.json).

The Registry model can be retrieved two ways:

1. as a stand-alone entity. This is useful when management of the Registry's
   model is needed independent of the entities within the Registry.
   See [Retrieving the Registry Model](#retrieving-the-registry-model) for
   more information.
2. as part of the Registry contents. This is useful when it is desirable to
   view the entire Registry as a single document - such as an "export" type
   of scenario. See the [Retrieving the Registry](#retrieving-the-registry)
   section (the `model` query parameter) for more information on this option.

Regardless of how the model is retrieved, the overall format is as follows:

```yaml
{
  "schemas": [ "STRING" * ], ?         # Available schema formats
  "attributes": {                      # Registry level extensions
    "STRING": {                        # Attribute name
      "name": "STRING",                # Same as attribute's key
      "type": "TYPE",                  # boolean, string, array, object, ...
      "description": "STRING",
      "enum": [ VALUE * ], ?           # Array of values of type "TYPE"
      "strict": BOOLEAN, ?             # Just "enum" values or not. Default=true
      "readonly": BOOLEAN, ?           # From client's POV. Default: false
      "immutable": BOOLEAN, ?          # Once set, can't change. Default: false
      "clientrequired": BOOLEAN, ?     # Default: false
      "serverrequired": BOOLEAN, ?     # Default: false
      "exportrequired": BOOLEAN, ?     # Default: false
      "default": VALUE, ?              # Attribute's default value, scalars

      "attributes": { ... }, ?         # If "type" above is object
      "item": {                        # If "type" above is map,array
        "type": "TYPE", ?              # map value type, or array type
        "attributes": { ... }, ?       # If this item "type" is object
        "item": { ... } ?              # If this item "type" is map,array
      } ?

      "ifvalues": {                    # If "type" is scalar
        "VALUE": {
          "siblingattributes": { ... } # Siblings to this "attribute"
        } *
      } ?
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
          "maxversions": UINTEGER, ?   # Num Vers(>=0). Default=0, 0=unlimited
          "setversionid": BOOLEAN, ?   # Supports client specified Version IDs
          "setdefaultversionsticky": BOOLEAN, ?     # Supports client "default" selection
          "hasdocument": BOOLEAN, ?    # Has a separate document. Default=true
          "readonly": BOOLEAN, ?       # From client's POV. Default=false
          "immutable": BOOLEAN, ?      # Once set, can't change. Default=false
          "attributes": { ... } ?      # See "attributes" above
        } *
      } ?
    } *
  } ?
}
```

The following describes the attributes of Registry model:
- `schemas`
  - A list of schema formats in which the Registry model can be returned. Each
    value MUST be a schema document format name (e.g. `jsonSchema/2020-12`),
    and SHOULD be of the form `NAME[/VERSION]`. All implementations of this
    specification MUST support `xRegistry-json` (the JSON serialization as
    defined by this specification), and SHOULD include it in the list.
  - Type: String.
  - OPTIONAL.
  - MUST be case insensitive.
  - MUST be a read-only attribute in API view.

- `attributes`
  - The set of attributes defined at the indicated level of the Registry. This
    includes extensions and specification defined/modified attributes.
  - Type: Map where each attribute's name MUST match the key of the map.
  - REQUIRED at specification defined locations, otherwise OPTIONAL for
    extensions Objects.

- `attributes."STRING"`
  - The name of the attribute being defined. See `attributes."STRING".name`
    for more information.
  - Type: String.
  - REQUIRED.

- `attributes."STRING".name`
  - The name of the attribute. MUST be the same as the key used in the owning
    `attributes` attribute. A value of `*` indicates support for undefined
    extension names. Absence of a `*` attribute indicates lack of support for
    undefined extensions and an error MUST be generated if one is present in
    a request.

    Often `*` is used with a `type` of `any` to allow for any undefined
    extension name of any supported data type. By default, the model
    does not support undefined extensions. Note that undefined extensions, if
    supported, MUST adhere to the same rules as
    [defined extensions](#attributes-and-extensions).

    An attribute of `*` MUST NOT use the `ifvalues` feature, but a non-`*`
    attribute MAY define an `ifvalues` attribute named `*` as long as there
    isn't already one defined for this level in the entity
  - Type: String.
  - REQUIRED.

- `attributes."STRING".type`
  - The "TYPE" of the attribute being defined. MUST be one of the data types
    (in lower case) defined in [Attributes and
    Extensions](#attributes-and-extensions).
  - Type: TYPE.
  - REQUIRED.

- `attributes."STRING".description`
  - A human readable description of the attribute.
  - Type: String.
  - OPTIONAL.

- `attributes."STRING".enum`
  - A list of possible values for this attribute. Each item in the array MUST
    be of type defined by `type`. When not specified, or an empty array, there
    are no restrictions on the value set of this attribute. This MUST only be
    used when the `type` is a scalar. See the `strict` attribute below.

    When specified without `strict` being `true`, this list is just a
    suggested set of values and the attribute is NOT REQUIRED to use one of
    them.
  - Type: Array.
  - OPTIONAL.

- `attributes."STRING".strict`
  - Indicates whether the attribute restricts its values to just the array of
    values specified in `enum` or not. A value of `true` means that any
    values used that is not part of the `enum` set MUST generate an error.
    This attribute has no impact when `enum` is absent or an empty array.
  - When not specified, the default value is `true`.
  - Type: Boolean.
  - OPTIONAL.

- `attributes."STRING".readonly`
  - Indicates whether this attribute is modifiable by a client. During
    creation, or update, of an entity if this attribute is specified then
    its value MUST be silently ignored by the server even if the value is
    invalid.

    Typically, attributes that are completely under the server's control
    will be `readonly` - e.g. `self`.

    When not specified the default value is `false`. When the attribute name is
    `*` then `readonly` MUST NOT be set to `true`. Note, both `clientrequired`
    and `readonly` MUST NOT be set to `true` at the same time.
  - Type: Boolean.
  - OPTIONAL.

- `attributes."STRING".immutable`
  - Indicates whether this attribute's value can be changed once it is set.
    This MUST ONLY be used for server controlled specification defined
    attributes, such as `specversion` and `id`, and MUST NOT be used for
    extension attributes. As such, it is only for informational purposes for
    clients.

    Once set, any attempt to update the value MUST be silently ignored by
    the server.

    When not specified, the default value is `false`.
  - Type: Boolean.
  - OPTIONAL.

- `attributes."STRING".clientrequired`
  - Indicates whether this attribute is a REQUIRED field for a client when
    creating or updating an entity. When not specified the default value is
    `false`. When the attribute name is `*` then `clientrequired` MUST NOT be
    set to `true`.

    During creation or update of an entity if this attribute is not
    specified then an error MUST be generated.

  - Type: Boolean.
  - OPTIONAL.

- `attributes."STRING".serverrequired`
  - Indicates whether this attribute is a REQUIRED field for a server when
    serializing an entity. When not specified the default value is `false`.
    When the attribute name is `*` then `serverrequired` MUST NOT be set to
    `true`. When `clientrequired` is `true` then `serverrequired` MUST also be
    `true`.

    In cases where the `?export` flag is specified, when a Resource attribute
    has `serverrequired` set to `true` but has `exportrequired` set to `false`,
    then `exportrequired` takes precedence and the attribute MUST NOT be
    serialized as part of the Resource. For example, `versionid` has
    `serverrequired` set to `true` because it will always be present in a
    Version's serialization, but when `?export` is used that attribute will
    not appear in the Resource's serialization because it has `exportrequired`
    set to `false`.

    TODO can remove this if we add issue 134

  - Type: Boolean
  - OPTIONAL

- `attributes."STRING".exportrequired`
  - Indicates whether this Resource attribute would be included
    in the serialization of the Resource even when `?export` is used.
  - This aspect is for specification defined attributes and MUST NOT be used
    on extension attributes. Its specification defined value MUST NOT be
    changed by model updates.
  - When not present, the default value is `false`.
  - Type: Boolean
  - OPTIONAL

- `attributes."STRING".default`
  - This value MUST be used to populate this attribute's value if one was
    not provided by a client. An attribute with a default value does not mean
    that its owning Object is mandated to be present, rather the attribute
    would only appear when the owning Object is present. By default,
    attributes have no default values.
  - Type: MUST be the same type as the `type` of this attribute and MUST
    only be used for scalar types.
  - OPTIONAL.

- `attributes."STRING".attributes`
  - This contains the list of attributes defined as part of a nested resource.
  - Type: Object, see `attributes` above.
  - MAY be present when the owning attribute's `type` is `object`, otherwise it
    MUST NOT be present. It MAY be absent or an empty list if there are no
    defined attributes for the nested `object`.

- `attributes."STRING".item`
  - Defines the nested resource that this attribute references. This
    attribute MUST only be used when the owning attribute's `type` value is
    `map` or `array`.
  - Type: Object.
  - REQUIRED when owning attribute's `type` is `map` or `array`.

- `attributes."STRING".item.type`
  - The "TYPE" of this nested resource.
  - Type: TYPE.
  - REQUIRED.

- `attributes."STRING".item.attributes`
  - See `attributes` above.
  - OPTIONAL, and MUST ONLY be used when `item.type` is `object`.

- `attributes."STRING".item.item`
  - See `attributes."STRING".item` above.
  - REQUIRED when `item.type` is `map` or `array`.

- `attributes."STRING".ifvalues`
  - This map can be used to conditionally include additional
    attribute definitions based on the runtime value of the current attribute.
    If the string serialization of the runtime value of this attribute matches
    the `ifvalues` `"VALUE"` (case sensitive) then the `siblingattributes` MUST
    be included in the model as siblings to this attribute.

    If `enum` is not empty and `strict` is `true` then this map MUST NOT
    contain any value that is not specified in the `enum` array.

    This aspect MUST only be used for scalar attributes.

    All attributes defined for this `ifvalues` MUST be unique within the scope
    of this `ifvalues` and MUST NOT match a named attributed defined at this
    level of the entity. If multiple `ifvalues` sections, at the same entity
    level, are active at the same time then there MUST NOT be duplicate
    `ifvalues` attributes names between those `ifvalues` sections.
  - `ifvalues` `"VALUE"` MUST NOT be an empty string.
  - `ifvalues` `siblingattributes` MAY include additional `ifvalues`
    definitions.
  - Type: Map where each value of the attribute is the key of the map.
  - OPTIONAL.

- `groups`
  - The set of Group types supported by the Registry.
  - Type: Map where the key MUST be the plural name (`groups.plural`) of the
    Group type (`GROUPs`).
  - REQUIRED if there are any Group types defined for the Registry.

- `groups.singular`
  - The singular name of a Group type e.g. `endpoint` (`GROUP`).
  - Type: String.
  - REQUIRED.
  - MUST be unique across all Group types in the Registry.
  - MUST be non-empty and MUST be a valid attribute name with the exception
    that it MUST NOT exceed 58 characters (not 63).

- `groups.plural`
  - The plural name of the Group type e.g. `endpoints` (`GROUPs`).
  - Type: String.
  - REQUIRED.
  - MUST be unique across all Group types in the Registry.
  - MUST be non-empty and MUST be a valid attribute name with the exception
    that it MUST NOT exceed 58 characters (not 63).

- `groups.attributes`
  - See `attributes` above.

- `groups.resources`
  - The set of Resource types defined for the Group type.
  - Type: Map where the key MUST be the plural name (`groups.resources.plural`)
    of the Resource type (`RESOURCEs`).
  - REQUIRED if there are any Resource types defined for the Group type.

- `groups.resources.singular`
  - The singular name of the Resource type e.g. `definition` (`RESOURCE`).
  - Type: String.
  - REQUIRED.
  - MUST be non-empty and MUST be a valid attribute name with the exception
    that it MUST NOT exceed 58 characters (not 63).
  - MUST be unique within the scope of its owning Group type.

- `groups.resources.plural`
  - The plural name of the Resource type e.g. `definitions` (`RESOURCEs`).
  - Type: String.
  - REQUIRED.
  - MUST be non-empty and MUST be a valid attribute name with the exception
    that it MUST NOT exceed 58 characters (not 63).
  - MUST be unique within the scope of its owning Group type.

- `groups.resources.maxversions`
  - Number of Versions that will be stored in the Registry for this Resource
    type.
  - Type: Unsigned Integer.
  - OPTIONAL.
  - The default value is zero (`0`).
  - A value of zero (`0`) indicates there is no stated limit, and
    implementations MAY prune non-default Versions at any time.
  - When the limit is exceeded, implementations MUST prune Versions by
    deleting the oldest Version (based on creation times) first, skipping the
    Version marked as "default". An exception to this pruning rule is if
    `maxversions` value is one (`1`) then the newest Version of the Resource
    MUST always be the "default" and the `setdefaultversionsticky` aspect
    MUST be `false`.

- `groups.resources.setversionid`
  - Indicates whether support for client-side setting of a Version's
    `versionid` is supported.
  - Type: Boolean (`true` or `false`, case sensitive).
  - OPTIONAL.
  - The default value is `true`.
  - A value of `true` indicates the client MAY specify the `versionid` of a
    Version during its creation process.
  - A value of `false` indicates that the server MUST choose an appropriate
    `versionid` value during creation of the Version.

- `groups.resources.setdefaultversionsticky`
  - Indicates whether support for client-side selection of the "default"
    Version is supported for Resources of this type. Once set, the default
    Version MUST NOT change unless there is some explicit action by a client
    to change it - hence the term "sticky".
  - Type: Boolean (`true` or `false`, case sensitive).
  - OPTIONAL.
  - The default value is `true`.
  - A value of `true` indicates a client MAY select the default Version of
    a Resource via one of the methods described in this specification rather
    than the server always choosing the default Version.
  - A value of `false` indicates the server MUST choose which Version is the
    default Version.
  - This attribute MUST NOT be `true` if `maxversions` is one (`1`).

- `groups.resources.hasdocument`
  - Indicates whether or not Resources of this type can have a document
    associated with it. If `false` then the xRegistry metadata becomes "the
    document". Meaning, an HTTP `GET` to the Resource's URL will return the
    xRegistry metadata in the HTTP body. The `xRegistry-` HTTP headers MUST
    NOT be used for requests or response messages for these Resources.
    Likewise, use of `$meta` URL path suffix in these cases MUST generate an
    error.

    A value of `true` does not mean that these Resources are guaranteed to
    have a non-empty document, and an HTTP `GET` to the Resource MAY return an
    empty HTTP body.
  - Type: Boolean (`true` or `false`, case sensitive).
  - OPTIONAL.
  - The default value is `true`.
  - A value of `true` indicates that Resource of this type supports a separate
    document to be associated with it.

- `groups.resources.readonly`
  - Indicates if Resources of this type are updateable by a client. A value of
    `false` means that the server MUST support write operations on Resources
    of this type in general, even if not all clients or specific situations
    are supported. A value of `true` means that all `PUT`, `POST`, `PATCH` and
    `DELETE` operations on Resources of this type MUST generate an error.
  - Type: Boolean (`true` or `false`, case sensitive).
  - OPTIONAL.
  - The default value is `false`.

- `groups.resources.typemap`
  - When a Resource's metadata is serialized in a response and the `inline`
    feature is enabled, the server will attempt to serialize the Resource's
    "document" under the `RESOURCE` attribute. However, this can
    only happen under two situations:<br>
    1 - The Resource document's bytes are already in the same format as
        the xRegistry metadata - in other words JSON, or<br>
    2 - The Resource's document can be considered a "string" and therefore
        can be serialized as a "string", possibly with some escaping.<br>

    For some well-known `contenttype` values (e.g. `application/json`) the
    first case can be easily determined by the server. However, for custom
    `contenttype` values the server will need to be explicitly told how to
    interpret its value (e.g. to know if it is a string or JSON).
    The `typemap` attribute allows for this by defining a mapping of
    `contenttype` values to well-known xRegistry format types.

    Since the `contenttype` value is a "media-type" per
    [RFC9110](https://datatracker.ietf.org/doc/html/rfc9110#media.type),
    for purposes of looking it up in the `typemap`, just the `type/subtype`
    portion of the value (case insensitively) MUST be used. Meaning, any
    `parameters` MUST be excluded.

    If more than one entry in the `typemap` matches the `contenttype`, but
    they all have the same value, then that value MUST be used. If they are
    not all the same, then `binary` MUST be used.

  - This specification defines the following values (case insensitive):
    - `binary`
    - `json`
    - `string`

    Implementations MAY define additional values.

    A value of `binary` indicates that the Resource's document is to be treated
    as an array of bytes and serialized under the `RESOURCEbase64` attribute,
    even if the `contenttype` is of the same type of the xRegistry metadata
    (e.g. `application/json`). This is useful when it is desireable to not
    have the server potentially modify the document (e.g. "pretty-print" it).

    A value of `json` indicates that the Resource's document is JSON and MUST
    be serialized under the `RESOURCE` attribute if it is valid JSON. Note that
    if there is a syntax error in the JSON then the server MUST treat the
    document as `binary` to avoid sending invalid JSON to the client. The
    server MAY choose to modify the formating of the document (e.g. to
    "pretty-print" it).

    A value of `string` indicates that the Resource's document is to be treated
    as a string and serialized using the default string serialization rules
    for the format being used to serialize the Resource's metadata. For example,
    when using JSON, this means escaping all non-printable characters.

    Specifying an unknown (or unsupported) value MUST generate an error during
    the update of the xRegistry model.

    By default, the following
    [RFC9110](https://datatracker.ietf.org/doc/html/rfc9110#media.type)
    `typemap` keys MUST be implicitly defined as follows, unless overridden
    by an explicit `typemap` entry:
    - `application/json`: mapped to `json`
    - `*+json`: mapped to `json`
    - `text/plain`: mapped to `string`

  - Type: Map where the keys and values MUST be non-empty strings. The key
    MAY include at most one `*` to act as a wildcard to mean zero or more
    instance of any character at that position in the string - similar to a
    `.*` in a regular expression. The key MUST be a case insensitive string.

  - OPTIONAL.
  - Example:<br>
    ```yaml
    "typemap": {
      "text/*": "string",
      "text/mine": "json"
    }
    ```

- `groups.resources.attributes`
  - See `attributes` above.
  - Note that Resources only have a few attributes, and most of the attributes
    listed here would be for the Versions. However, they would appear on the
    Resource when asking for the default Version of the Resource.

#### Retrieving the Registry Model

To retrieve the Registry Model as a stand-alone entity, an HTTP `GET` MAY be
used.

Registries MAY support exposing the model in a variety of well-defined schema
formats. The `model.schemas` attribute (discussed above) SHOULD expose the set
of schema formats available.

The resulting schema document MUST include the full Registry model - meaning
all specification defined attributes, extension attributes, Group types and
Resource types.

For the sake of brevity, this specification doesn't include the full definition
of the specification defined attributes as part of the snippets of output.
However, the full model definition of the Registry-level attributes can be
found in [model.json](model.json), and the Group and Resource-level attributes
can be found in this sample [sample-model.json](sample-model.json).

The request MUST be of the form:

```yaml
GET /model[?schema=NAME[/VERSION]]
```

Where:
- If specified, the `schema` query parameter SHOULD be one of the valid
  `model.schema` values (case insensitive). Note that an implementation MAY
  choose to support a value that is not specified within the `model.schema`
  attribute. If not specified, the default value MUST be `xRegistry-json`.

Implementations of this specification MUST support `xRegistry-json`.

A successful response MUST be of the form:

```yaml
HTTP/1.1 200 OK
Content-Type: ...

... xRegistry model in a schema specific format ...
```

Where:
- The HTTP body MUST be a schema representation of the Registry model
  in the format requested by the `schema` query parameter.
- If a `VERSION` is not specified as part of the `schema` query parameter then
  the server MAY choose any schema version of the specified schema format.
  However, it is RECOMMENDED that the newest supported version be used.

If the specified schema format is not supported then an HTTP `400 Bad Request`
error MUST be generated.

When the `schema` is `xRegistry-json` then the response MUST be of the form:

```yaml
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
      "readonly": BOOLEAN, ?
      "immutable": BOOLEAN, ?
      "clientrequired": BOOLEAN, ?
      "serverrequired": BOOLEAN, ?
      "default": VALUE, ?

      "attributes": { ... }, ?
      "item": { ... }, ?

      "ifvalues": {
        "VALUE": {
          "siblingattributes": { ... }
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
          "maxversions": UINTEGER, ?
          "setversionid": BOOLEAN, ?
          "setdefaultversionsticky": BOOLEAN, ?
          "hasdocument": BOOLEAN, ?
          "readonly": BOOLEAN, ?
          "immutable": BOOLEAN, ?
          "attributes": { ... } ?
        } *
      } ?
    } *
  } ?
}
```

**Examples:**

Retrieve a Registry model that has one extension attribute on the
`endpoints` Group, and supports returning the schema of the Registry
as JSON Schema:

```yaml
GET /model
```

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "schemas": [ "xRegistry-json", "jsonSchema/2020-12" ],
  "attributes": {
    ... xRegistry spec defined attributes excluded for brevity ...
  },
  "groups": {
    "endpoints": {
      "plural": "endpoints",
      "singular": "endpoint",
      "attributes": {
        ... xRegistry spec defined attributes excluded for brevity ...
        "shared": {
          "name": "shared",
          "type": "boolean"
        }
      },

      "resources": {
        "definitions": {
          "plural": "definitions",
          "singular": "definition",
          "attributes": {
            ... xRegistry spec defined attributes excluded for brevity ...
            "*": {
              type: "any"
            }
          }
        }
      }
    }
  }
}
```

#### Updating the Registry Model

To update the Registry model, the new full representation of the model
MAY be included on an HTTP `PUT` to the Registry Entity in the `model`
attribute, or a `PUT` MAY be done to the `/model` API. Note that `PATCH`
is not supported via the `/model` API.

While the remainder of this section is presented within the scope of the
`/model` API, the processing rules of the model definition MUST also apply
when it is updated via the `model` attribute on the Registry entity.

The request MUST be of the form:

```yaml
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
      "readonly": BOOLEAN, ?
      "immutable": BOOLEAN, ?
      "clientrequired": BOOLEAN, ?
      "serverrequired": BOOLEAN, ?
      "default": VALUE, ?

      "attributes": { ... }, ?               # For nested object
      "item": { ... }, ?                     # For nested map, array

      "ifvalues": {
        "VALUE": {
          "siblingattributes": { ... }
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
          "maxversions": UINTEGER, ?
          "setversionid": BOOLEAN, ?
          "setdefaultversionsticky": BOOLEAN, ?
          "hasdocument": BOOLEAN, ?
          "readonly": BOOLEAN, ?
          "immutable": BOOLEAN, ?
          "attributes": { ... } ?            # See "attributes" above
        } *
      } ?
    } *
  } ?
}
```

Where:
- The HTTP body MUST contain all of the attributes, Groups and Resources that
  the client wishes to define.
- Group and Resource types that are not present in the request MUST be
  interpreted as a request to delete them and all entities of those types MUST
  be deleted.
- Attributes not present in the request MUST be interpreted as a request to
  delete the attribute, and if the attribute is a specification defined
  attribute then it MUST be added back with its default definition.

A successful response MUST include a full representation of the Registry model
and be of the form:

```yaml
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
      "readonly": BOOLEAN, ?
      "immutable": BOOLEAN, ?
      "clientrequired": BOOLEAN, ?
      "serverrequired": BOOLEAN, ?
      "default": VALUE, ?

      "attributes": { ... }, ?
      "item": { ... }, ?

      "ifvalues": {
        "VALUE": {
          "siblingattributes": { ... }
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
          "maxversions": UINTEGER, ?
          "setversionid": BOOLEAN, ?
          "setdefaultversionsticky": BOOLEAN, ?
          "hasdocument": BOOLEAN, ?
          "readonly": BOOLEAN, ?
          "immutable": BOOLEAN, ?
          "attributes": { ... } ?
        } *
      } ?
    } *
  } ?
}
```

**Examples:**

Update a Registry's model to add a new Group type:

```yaml
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
          "type": "boolean"
        }
      },

      "resources": {
        "definitions": {
          "plural": "definitions",
          "singular": "definition",
          "attributes": {
            "*": {
              type: "any"
            }
          }
        }
      }
    },
    "schemagroups": {
      "plural": "schemagroups",
      "singular": "schemagroup",

      "resources": {
        "schemas": {
          "plural": "schemas",
          "singular": "schema"
        }
      }
    }
  }
}
```

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "schemas": [ "xRegistry-json", "jsonSchema/2020-12" ],
  "attributes": {
    ... xRegistry spec defined attributes excluded for brevity ...
  },
  "groups": {
    "endpoints" {
      "plural": "endpoints",
      "singular": "endpoint",
      "attributes": {
        ... xRegistry spec defined attributes excluded for brevity ...
        "shared": {
          "name": "shared",
          "type": "boolean"
        }
      },

      "resources": {
        "definitions": {
          "plural": "definitions",
          "singular": "definition",
          ... xRegistry spec defined attributes excluded for brevity ...
          "attributes": {
            "*": {
              type: "any"
            }
          }
          "maxversions": 1
        }
      }
    },
    "schemagroups": {
      "plural": "schemagroups",
      "singular": "schemagroup",

      "resources": {
        "schemas": {
          "plural": "schemas",
          "singular": "schema"
        }
      }
    }
  }
}
```

##### Reuse of Resource Definitions

When a Resource type definition is to be shared between Groups, rather than
creating a duplicate Resource definition, the `ximport` mechanism MAY be used
instead. When defining the Resources of a Group, a special Resource "plural"
name MAY be used to reference other Resource definitions from within the same
Registry. For example the following abbreviated model definition defines
one Resource type (`definitions`) under the `messagegroups` Group, that is
also used by the `endpoints` Group.

```yaml
"model": {
  "groups": {
    "messagegroups": {
      "plural": "messagegroups",
      "singular": "messagegroup",
      "resources": {
        "definitions": {
          "plural": "definitions",
          "singular": "definition"
        }
      }
    },
    "endpoints": {
      "plural": "endpoints",
      "singular": "endpoint",
      "resources": {
        "ximport": [ "messagegroups/definitions" ]
      }
    }
  }
}
```

The format of the `ximport` specification is:

```yaml
"ximport": [ "GROUPs/RESOURCEs", * ]
```

where:
- Each array value MUST be a reference to another Group/Resource plural
combination defined within the same Registry. It MUST NOT reference the
same Group under which the `ximport` resides.
- An empty array MAY be specified, implying no Resources are imported.

Use of the `ximport` feature MUST only be used once per Group definition.

Additional locally defined Resources MAY be defined within a Group that uses
the `ximport` feature, however, Resource `plural` and `singular` values
MUST be unique across all imported and locally defined Resources.

See [Cross Referencing Resources](#cross-referencing-resources) for more
additional information.

---

### Groups

Groups represent entities that typically act as a collection mechanism for
related Resources. However, it is worth noting that Groups do not have to have
Resources associated with them. It is possible to have Groups be the main (or
only) entity of a Registry. Each Group type MAY have any number of Resource
types within it. This specification does not define how the Resources within a
Group type are related to each other.

The serialization of a Group entity adheres to this form:

```yaml
{
  "id": "STRING",
  "name": "STRING", ?
  "epoch": UINTEGER,
  "self": "URL",
  "description": "STRING", ?
  "documentation": "URL", ?
  "labels": { "STRING": "STRING" * }, ?
  "origin": "URI", ?
  "createdat": "TIME",
  "modifiedat": "TIME",

  # Repeat for each Resource type in the Group
  "RESOURCEsurl": "URL",                    # e.g. "definitionsurl"
  "RESOURCEscount": UINTEGER,               # e.g. "definitionscount"
  "RESOURCEs": { RESOURCEs collection } ?   # If inlined/nested
}
```

Groups include the following common attributes:
- [`id`](#id-attribute) - REQUIRED in responses and document view, otherwise
  OPTIONAL.
- [`name`](#name-attribute) - OPTIONAL.
- [`epoch`](#epoch-attribute) - REQUIRED in responses, otherwise OPTIONAL.
- [`self`](#self-attribute) - REQUIRED in responses, otherwise OPTIONAL.
- [`description`](#description-attribute) - OPTIONAL.
- [`documentation`](#documentation-attribute) - OPTIONAL.
- [`labels`](#labels-attribute) - OPTIONAL.
- [`origin`](#origin-attribute) - OPTIONAL.
- [`createdat`](#createdat-attribute) - REQUIRED in responses, otherwise
  OPTIONAL.
- [`modifiedat`](#modifiedat-attribute) - REQUIRED in responses, otherwise
  OPTIONAL.

and the following Group specific attributes:

##### `RESOURCEs` Collections
- Type: Set of [Registry Collections](#registry-collections).
- Description: A list of Registry collections that contain the set of
  Resources supported by the Group.
- Constraints:
  - REQUIRED in responses, MAY be present in requests.
  - REQUIRED in document view.
  - If present in a response, it MUST include all nested Resource Collection
    types of the owning Group, even if some of the collections are empty.

#### Retrieving a Group Collection

To retrieve a Group collection, an HTTP `GET` MAY be used.

The request MUST be of the form:

```yaml
GET /GROUPs[?inline=...&filter=...&export]
```

The following query parameters SHOULD be supported by servers:
- `inline` - See [inlining](#inlining) for more information.
- `filter` - See [filtering](#filtering) for more information.
- `export` - See [exporting](#exporting) for more information.

A successful response MUST be of the form:

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Link: <URL>;rel=next;count=UINTEGER ?

{
  "ID": {
    "id": "STRING",
    "name": "STRING", ?
    "epoch": UINTEGER,
    "self": "URL",
    "description": "STRING", ?
    "documentation": "URL", ?
    "labels": { "STRING": "STRING" * }, ?
    "origin": "URI", ?
    "createdat": "TIME",
    "modifiedat": "TIME",

    # Repeat for each Resource type in the Group
    "RESOURCEsurl": "URL",                    # e.g. "definitionsurl"
    "RESOURCEscount": UINTEGER,               # e.g. "definitionscount"
    "RESOURCEs": { RESOURCEs collection } ?   # If inlined
  } *
}
```

**Examples:**

Retrieve all entities in the `endpoints` Group:

```yaml
GET /endpoints
```

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Link: <https://example.com/endpoints&page=2>;rel=next;count=100

{
  "123": {
    "id": "123",
    "name": "A cool endpoint",
    "epoch": 1,
    "self": "https://example.com/endpoints/123",
    "createdat": "2024-04-30T12:00:00Z",
    "modifiedat": "2024-04-30T12:00:01Z",

    "definitionsurl": "https://example.com/endpoints/123/definitions",
    "definitionscount": 5
  },
  "124": {
    "id": "124",
    "name": "Redis Queue",
    "epoch": 3,
    "self": "https://example.com/endpoints/124",
    "createdat": "2024-04-30T12:00:00Z",
    "modifiedat": "2024-04-30T12:00:01Z",

    "definitionsurl": "https://example.com/endpoints/124/definitions",
    "definitionscount": 1
  }
}
```

Notice that the `Link` HTTP header is present, indicating that there
is a second page of results that can be retrieved via the specified URL,
and that there are total of 100 items in this collection.

#### Creating or Updating Groups

Creating or updating Groups via HTTP MAY be done by using the HTTP `PUT`
or `POST` methods:
- `PUT   /GROUPs/gID[?nested]`.
- `PATCH /GROUPs/gID[?nested]`.
- `POST  /GROUPs[?nested]`.

The following query parameter SHOULD be supported by servers:
- `nested` - See
   [Updating Nested Registry
   Collections](#updating-nested-registry-collections) for more information.

The overall processing of these two APIs is defined in the [Creating or
Updating Entities](#creating-or-updating-entities) section.

Each individual Group definition MUST adhere to the following:

```yaml
{
  "id": "STRING", ?
  "name": "STRING", ?
  "epoch": UINTEGER, ?
  "description": "STRING", ?
  "documentation": "URL", ?
  "labels": { "STRING": "STRING" * }, ?
  "origin": "URI" ?
  "createdat": "TIME", ?
  "modifiedat": "TIME", ?

  # Repeat for each Resource type in the Group
  "RESOURCEsurl": "URL",                     # e.g. "definitionsurl"
  "RESOURCEscount": UINTEGER,                # e.g. "definitionscount"
  "RESOURCEs": { RESOURCEs collection } ?    # If "?nested" is present
}
```

Each individual Group in a successful response MUST adhere to the following:

```yaml
{
  "id": "STRING",
  "name": "STRING", ?
  "epoch": UINTEGER,
  "self": "URL",
  "description": "STRING", ?
  "documentation": "URL", ?
  "labels": { "STRING": "STRING" * }, ?
  "origin": "URI", ?
  "createdat": "TIME",
  "modifiedat": "TIME",

  # Repeat for each Resource type in the Group
  "RESOURCEsurl": "URL",                    # e.g. "definitionsurl"
  "RESOURCEscount": UINTEGER                # e.g. "definitionscount"
}
```

**Examples:**

Targeted request to a create a specific Group `id`:

```yaml
PUT /endpoints/456
Content-Type: application/json; charset=utf-8

{
  "id": "456",
  ... remainder of Group 456 definition ...
}
```

```yaml
HTTP/1.1 201 Created
Content-Type: application/json; charset=utf-8
Location: https://example.com/endpoints/456

{
  "id": "456",
  ... remainder of Group 456 definition ...
}
```

Multiple Groups specified in the HTTP body:

```yaml
POST /endpoints
Content-Type: application/json; charset=utf-8

{
  "group1": {
    "id": "group1",
    ... remainder of group1 definition ...
  },
  "group2": {
    "id": "group2",
    ... remainder of group2 definition ...
  }
}
```

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "group1": {
    "id": "group1",
    ... remainder of group1 definition ...
  },
  "group2": {
    "id": "group2",
    ... remainder of group2 definition ...
  }
}
```

#### Retrieving a Group

To retrieve a Group, an HTTP `GET` MAY be used.

The request MUST be of the form:

```yaml
GET /GROUPs/gID[?inline=...&filter=...&export]
```

The following query parameters SHOULD be supported by servers:
- `inline` - See [inlining](#inlining) for more information.
- `filter` - See [filtering](#filtering) for more information.
- `export` - See [exporting](#exporting) for more information.

A successful response MUST be of the form:

```yaml
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
  "origin": "URI", ?
  "createdat": "TIME",
  "modifiedat": "TIME",

  # Repeat for each Resource type in the Group
  "RESOURCEsurl": "URL",                     # e.g. "definitionsurl"
  "RESOURCEscount": UINTEGER,                # e.g. "definitionscount"
  "RESOURCEs": { RESOURCEs collection } ?    # If inlined
}
```

**Examples:**

Retrieve a single `endpoints` Group:

```yaml
GET /endpoints/123
```

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "id": "123",
  "name": "myEndpoint",
  "epoch": 1,
  "self": "https://example.com/endpoints/123",
  "createdat": "2024-04-30T12:00:00Z",
  "modifiedat": "2024-04-30T12:00:01Z",

  "definitionsurl": "https://example.com/endpoints/123/definitions",
  "definitionscount": 5
}
```

#### Deleting Groups

To delete one or more Groups, an HTTP `DELETE` MAY be used:
- `DELETE /GROUPs/gID[?epoch=UINTEGER]`.
- `DELETE /GROUPs`.

The processing of these two APIs is defined in the [Deleting Entities in a
Registry Collection](#deleting-entities-in-a-registry-collection)
section.

---

### Resources

Resources typically represent the main entity that the Registry is managing.
Each Resource is associated with a Group to aid in their discovery and to show
a relationship with Resources in that same Group. Resources appear within the
Group's `RESOURCEs` collection.

Resources, like all entities in the Registry, can be modified but Resources
can also have a version history associated with them, allowing for users to
retrieve previous Versions of the Resource. In this respect, Resources have
a 2-layered definition. The first layer is the Resource entity itself,
and the second layer is its `versions` collection - the version history of
the Resource. The Resource entity can be thought of as an alias for the
"default" Version of the Resource, and as such, most of the attributes shown
when processing the Resource will be mapped from the "default" Version.

However, there is one exception:
- `self` MUST be an absolute URL to the Resource, and not to the "default"
  Version in the `versions` collection. The Resource's `defaultversionurl`
  attribute can be used to access the "default" Version.

All other Version attributes, including extensions, are inherited from the
"default" Version.

The remainder of this section discusses the processing rules for Resources
and Versions. While it mainly uses the term "Resource" for ease of reading, in
most cases it can be assumed that the same applies for "Versions". When this
is not the case it will be explicitly called out.

#### Resource Metadata vs Resource Document

Unlike Groups, which consist entirely of xRegistry managed metadata, Resources
typically have their own domain specific data and document format that needs
to be kept distinct from the xRegistry Resource metadata. As discussed
previously, the model definition for Resource has a `hasdocument` attribute
indicating whether a Resource has its own separate document or not.

This specification does not define any requirements for the contents of this
document, and it doesn't even need to be stored within the Registry itself.
The Resource MAY choose to simply store a URL reference to the externally
managed document instead. When the document is stored within the Registry, it
can be managed as an opaque array of bytes.

When a Resource does have a separate document, the URL for the Resource
references this document and not the Resource's xRegistry metadata. This
allows for easy access to the data of interest by end users. In order to
manage the Resource's xRegistry metadata, the URL to the Resource MUST
have `$meta` appended to the Resource's URL path. For example:

```yaml
GET https://example.com/schemagroups/mygroup/schemas/myschema$meta
```
will retrieve the xRegistry metadata information for the `myschema` Resource.

When the Resource's path is appended with `$meta`, the Resource's document
becomes available via a set of `RESOURCE*` attributes within that metadata:

- `RESOURCE`: this attribute MUST be used when the contents of the Resource's
  document are stored within the Registry and its "array of bytes" can be
  used directly in the serialization of the Resource metadata "as is". Meaning,
  in the JSON case, those bytes can be parsed as a JSON value without any
  additional processing (such as escaping) being done. This is a convenience
  (optimization) attribute to make it easier to view the document when it
  happens to be in the same format as the xRegistry itself.

  The model Resource attribute `typemap` MAY be used to help the server
  determine which `contenttype` values are of the same format - see
  [Registry Model](#registry-model) for more information.  If a Resource has
  a matching `contenttype` but the contents of the Resource's document do not
  successfully parse (e.g. it `application/json` but the JSON is invalid), then
  `RESOURCE` MUST NOT be used and `RESOURCEbase64` MUST be used instead.

- `RESOURCEurl`: this attribute MUST be used when the contents of the
  Resource's are stored within the Registry but `RESOURCE` can not be used.
  The Resource's document is base64 encoded and serialized as a string.

- `RESOURCEurl`: this attribute MUST be used when the Resource is stored
  external to the Registry and its value MUST be a URL that can be used to
  retrieve its contents via an HTTP(s) `GET`.

When accessing a Resource's metadata via `$meta`, often it is to
view or update the xRegistry metadata and not the document, as such, including
the potentially large amount of data from the Resource's document in request
and response messages could be cumbersome. To address this, the `RESOURCE` and
`RESOURECEbase64` attributes do not appear by default as part of the
serialization of the Resource. Rather, they MUST only appear in responses when
the [`inline`](#inlining) query parameter is used. Likewise, in requests, these
attributes are OPTIONAL and would only need to be used when a change to the
document's content is needed at the same time as updates to the Resource's
metadata. However, the `RESOURCEurl` attribute MUST always appear if it has a
value.

Note that the serialization of a Resource MUST only use at most one of these 3
attributes at a time.

#### Resource Attributes

Resources (not Versions) include the following common attributes:

(these values are from the Resource, not the default Version)
- [`id`](#id-attribute) - REQUIRED in responses and document view, otherwise
  OPTIONAL.
- [`self`](#self-attribute) - REQUIRED in responses, otherwise OPTIONAL.

(these values are inherited from the default Version and only present when
the Resource's default attributes are serialized as part of the Resource)
- [`versionid`](#versionid-attribute) - REQUIRED.
- [`name`](#name-attribute) - OPTIONAL.
- [`epoch`](#epoch-attribute) - REQUIRED in responses, otherwise OPTIONAL.
- [`description`](#description-attribute) - OPTIONAL.
- [`documentation`](#documentation-attribute) - OPTIONAL.
- [`labels`](#labels-attribute) - OPTIONAL.
- [`origin`](#origin-attribute) - OPTIONAL.
- [`createdat`](#createdat-attribute) - REQUIRED in responses, otherwise
  OPTIONAL.
- [`modifiedat`](#modifiedat-attribute) - REQUIRED in responses, otherwise
  OPTIONAL.
- [`contenttype`](#contenttype-attribute) - STRONGLY RECOMMENDED.

and the following Resource specific attributes:

##### `xref` Attribute
- Type: Relative URL from base URL of Registry
- Description: indicates that this Resource is a reference to another Resource
  owned by another Group within the same Registry. See [Cross Referencing
  Resources](#cross-referencing-resources) for more information.

##### `defaultversionsticky` Attribute
- Type: Boolean
- Description: indicates whether or not the "default" Version has been
  explicitly set or whether the "default" Version is always the newest one
  based on the `createdat` timestamp. A value of `true` means that it has been
  explicitly set and the value of `defaultversionid` MUST NOT automatically
  change if newer Versions are added. A value of `false` means the default
  Version MUST be the newest Version based on `createdat` timestamps.

  When set to `true`, if the default Version is deleted, then without any
  indication of which Version is to become the new default Version, the
  sticky aspect MUST be disabled and the default Version MUST be the newest
  Version.

  Note: if there is more than one Version with the newest `createdat` value,
  then the Version chosen by the server will be indeterminate.

- Constraints:
  - When not present, the default value is `false`.
  - REQUIRED when `true`, otherwise OPTIONAL.
  - When present, it MUST be a case sensitive `true` or `false`.
  - If present in a request, a value of `null` has the same meaning as
    deleting the attribute, implicitly setting it to `false`.
  - Since this attribute and `defaultversionid` are closely related, the
    processing of them in a request message MUST adhere to the following:
    - The `defaultversionsticky` attribute is applied first. As a reminder,
      in the `PATCH` case, if this attribute is missing in the request then
      this attribute remains unchanged in the Resource.
    - If the resulting value of this attribute is `false` then the sticky
      aspect MUST be turned off, and any `defaultversionid` in the request
      MUST be ignored. The newest Version MUST be the default Version.
    - If the resulting value of this attribute is `true` then the sticky
      aspect MUST be turned on, and any `defaultversionid` attribute from
      the request is applied - where a value of `null` means "newest".
      If the request was a `PUT` or `POST` and did not have a
      `defaultversionid` then the implicit value of `null` MUST be used,
      resulting in "newest". If the request was a `PATCH` and did not have a
      `defaultversionid` then the current default Version MUST be used.
      A reference to a Version that does not exist MUST generate an error.
- Examples:
  - `true`, `false`

##### `defaultversionid` Attribute
- Type: String
- Description: the `versionid` of the default Version of the Resource.
  This specification makes no statement as to the format of this string or
  versioning scheme used by implementations of this specification. However, it
  is assumed that newer Versions of a Resource will have a "higher"
  value than older Versions. Also see [`epoch`](#epoch-attribute).
- Constraints:
  - REQUIRED in responses and document view, OPTIONAL in requests.
  - If present, MUST be non-empty.
  - MUST be the `versionid` of the default Version of the Resource.
  - See the `defaultversionsticky` section above for how to process these two
    attributes.
- Examples:
  - `1`, `2.0`, `v3-rc1`

##### `defaultversionurl` Attribute
- Type: URL
- Description: an absolute URL to the default Version of the Resource.

  The Version URL path MUST include `$meta` if the request asked for
  the serialization of the Resource metadata. This would happen when `$meta`
  was used in the request, or when the Resource is included in the
  serialization of a Group, such as when the `inline` feature is used.
- Constraints:
  - REQUIRED in responses, OPTIONAL in requests.
  - OPTIONAL in document view.
  - MUST be a read-only attribute in API view.
  - MUST be an absolute URL to the default Version of the Resource, and MUST.
    be the same as the Version's `self` attribute.
- Examples:
  - `https://example.com/endpoints/123/definitions/456/versions/1.0`

##### `versions` Collection
- Type: [Registry Collection](#registry-collections)
- Description: A map of Versions of the Resource.
- Constraints:
  - REQUIRED in responses, MAY be present in requests.
  - REQUIRED in document view.
  - If present, it MUST always have at least one Version.

The following Version specific attributes will appear on both Resources and
Versions:

#### Serializing Resources

As discussed above, there are two ways to serialize a Resource in an HTTP
message's body:
- As its underlying domain specific document.
- As its xRegistry metadata.

Which variant is used is controlled by the use of `$meta` on the URL path.
This section goes into more details about these two serialization options.

##### Serializing Resource Documents

When a Resource is serialized as its underlying domain specific document,
in other words `$meta` is not appended to its URL path, the HTTP body of
requests and responses MUST be the exact bytes of the document. If the
document is empty, or there is no document, then the HTTP body MUST be empty
(zero length).

In this serialization mode it might be useful for clients to have access to
Resource's xRegistry metadata. To support this, some of the Resource's
xRegistry metadata will appear as HTTP headers in response messages.

On responses, unless otherwise stated, all top-level scalar attributes of the
Resource MUST appear as HTTP headers where the header name is the name of the
attribute prefixed with `xRegistry-`. Certain attributes do not follow this
rule if a standard HTTP header name is to be used instead (e.g. `contenttype`
MUST use `Content-Type`, not `xRegistry-contenttype`).

Top-level map attributes whose values are of scalar types MUST also appear as
HTTP headers (each key having it's own HTTP header) and in those cases the
HTTP header names will be of the form: `xRegistry-ATTRIBUTENAME-KEYNAME`. Note
that map keys MAY contain the `-` character, so any `-` after the 2nd `-` is
part of the key name. See
[HTTP Header Values](#http-header-values) for additional information and
[`labels`](#labels-attribute) for an example of one such attribute.

Complex top-level attributes (e.g. arrays, objects, non-scalar maps) MUST NOT
appear as HTTP headers.

On update requests, similar serialization rules apply. However, rather than
these headers being REQUIRED, the client would only need to include those
top-level attributes that they would like to change. But, including unchanged
attributes MAY be done. Any attributes not included in request messages
MUST be interpreted as a request to leave their values unchanged. Using a
value of `null` (case sensitive) indicates a request to delete that attribute.

Any top-level map attributes that appear as HTTP headers MUST be included
in their entirety and any missing keys MUST be interpreted as a request to
delete those keys from the map.

Since only some types of attributes can appear as HTTP headers, `$meta` MUST
be used to manage the others. See the next section for more details.

When a Resource (not a Version) is serialized with the Resource document
in the HTTP body, it MUST adhere to this form:

```yaml
Content-Type: STRING ?
xRegistry-id: STRING                       # ID of Resource, not default Version
xRegistry-versionid: STRING                # versionid of default Version
xRegistry-self: URL                        # Resource URL, not default Version
xRegistry-name: STRING ?
xRegistry-epoch: UINT
xRegistry-isdefault: true
xRegistry-description: STRING ?
xRegistry-documentation: URL ?
xRegistry-labels-KEY: STRING *
xRegistry-origin: STRING ?
xRegistry-createdat: TIME
xRegistry-modifiedat: TIME
xRegistry-RESOURCEurl: URL ?
xRegistry-xref: URL ?
xRegistry-defaultversionsticky: BOOLEAN ?
xRegistry-defaultversionid: STRING
xRegistry-defaultversionurl: URL
xRegistry-versionsurl: URL
xRegistry-versionscount: UINTEGER
Location: URL
Content-Location: URL ?

... Resource document ... ?
```

Where:
- The `id` is the `id` of the Resource, not the default Version.
- The `versionid` is the `versionid` of the default Version.
- The `self` URL references the Resource, not the default Version.
- The serialization of the `labels` attribute is split into separate HTTP
  headers (one per label name).
- The `versionsurl` and `versionscount` attributes are included, but not
  the `versions` collection itself.
- The `Content-Location` header MAY appear, and if present, MUST reference
  the "default" Version.

Version serialization will look similar, but the set of xRegistry HTTP headers
will be slightly different (to exclude Resource specific attributes). See the
next sections for more information.

##### Serializing Resource Metadata

Appending `$meta` to a Resource's URL path indicates a request to
manage the xRegistry metadata about a Resource rather than its "document".
When `$meta` appears then the HTTP body of the message
MUST contain a serialization of the xRegistry metadata of that Resource.

When serialized as a JSON object, a Resource (not a Version) MUST adhere to
this form:

```yaml
{
  "id": "STRING",                          # ID of Resource, not default Version
  "self": "URL",                           # URL of Resource,not default Version

  # Attributes inherited from the default Version
  "versionid": STRING",
  "name": "STRING", ?
  "epoch": UINTEGER,
  "isdefault": true,
  "description": "STRING", ?
  "documentation": "URL", ?
  "labels": { "STRING": "STRING" * }, ?
  "origin": "URI", ?
  "createdat": "TIME",
  "modifiedat": "TIME",
  "contenttype": "STRING", ?

  "RESOURCEurl": "URL", ?                  # If not local
  "RESOURCE": ... Resource document ..., ? # If inlined & JSON
  "RESOURCEbase64": "STRING", ?            # If inlined & ~JSON

  # Resource specific attributes
  "xref": "URL", ?

  "defaultversionsticky": BOOLEAN, ?
  "defaultversionid": "STRING",
  "defaultversionurl": "URL",

  "versionsurl": "URL",
  "versionscount": UINTEGER,
  "versions": { Versions collection } ?    # If inlined/nested
}
```

As before, Version's serialization will look similar but the set of attributes
will be slightly different (to exclude Resource specific attributes). More
information on this in the next sections.

#### Cross Referencing Resources

Typically, Resources exist within the scope of a single Group, however there
might be situations where a Resource needs to be related to multiple Groups.
In these cases there are two options. First, a copy of the Resource could be
made in the second Group. The obvious downside to this is that there's no
relationship between the two Resources and any changes to one would need to
be done in the other - running the risk of them getting out of sync.

The second, and better option, is to create a cross-reference from one
(the "source" Resource) to the other ("target" Resource). This is done
by setting the `xref` attribute on the source Resource to be the relative
URL to the target Resource. For example, a source Resource defined as:

```yaml
{
  "id": "sourceresource",
  "xref": "groups/group2/resources/targetresource"
}
```

means that this "sourceresource" references the "targetresource" from
"group2". When the source Resource is serialized (e.g. as a result of a
`GET`), then all of the target Resource's attributes (except its `id`) will
appear as if they were locally defined. So, if the target Resource was defined
as:

```yaml
{
  "id": "targetresource",
  "self": "http://example.com/groups/group2/resources/targetresource$meta",
  "versionid": "v1",
  "epoch": 2,
  "isdefault": true,
  "createdat": "2024-01-01-T12:00:00",
  "modifiedat": "2024-01-01-T12:01:00",
  "defaultversionid": "v1",
  "defaultversionurl": "http://example.com/groups/group2/resources/targetresource/versions/v1",
  "versionscount": 1,
  "versionsurl": "http://example.com/groups/group2/resources/targetresource/versions"
}
```

then the resulting serialization of the source Resource would be:

```yaml
{
  "id": sourceresource",
  "self": "http://example.com/groups/group1/resources/sourceresource$meta",
  "versionid": "v1",
  "epoch": 2,
  "isdefault": true,
  "createdat": "2024-01-01-T12:00:00",
  "modifiedat": "2024-01-01-T12:01:00",
  "xref": "groups/group2/resources/targetresource",
  "defaultversionid": "v1",
  "defaultversionurl": "http://example.com/groups/group1/resources/sourceresource/versions/v1",
  "versionscount": 1,
  "versionsurl": "http://example.com/groups/group1/resources/sourceresource/versions"
}
```

Note:
- The `id` of the source Resource MAY be different from the `id` of the target
  Resource.
- The `xref` attribute MUST appear so a client can easily determine that this
  Resource is actually a cross-referenced Resource, and provide a URL to that
  targeted Resource (if ever needed).
- All calculated attributes (such as the `defaultversionurl` and `versionsurl`)
  MUST use the `id` of the source Resource not the target Resource. In this
  respect, users of this serialization would never know that this is a cross-
  referenced Resource except for the presence of the `xref` attribute.
- The URL of the target Resource MUST be a relative URL of the form:
  `GROUPs/gID/RESOURCEs/rID`, and MUST reference a Resource within the same
  Registry. However, it MUST NOT point to itself.

From a consumption (read) perspective, aside from the presence of the `xref`
attribute, the Resource appears to be a normal Resource that exists within
`group1`. All of the specification defined features (e.g. `?inline`,
`?filter`) MAY be used when retrieving the Resource.

However, from a write perspective it is quite different. Only the
`id` and `xref` attributes are persisted for the source Resource, the
target Resource's attributes are inherited and not meant to be persisted
with the source Resource. This means that a write-operation on the source
Resource that includes the `xref` attribute SHOULD NOT include any target
Resource attributes (or nested collections) and if present they MUST be
ignored. In order to update the target Resource's attributes (or nested
entities), a write operation MUST be done on the appropriate target Resource
entity directly.

A request that deletes the `xref` attribute MUST be interpreted as a request
to convert the Resource from a cross-reference Resource into a normal
Resource - in which case the normal semantics of updating the mutable
attributes applies. And any relationship with the target Resource is deleted.
Likewise, the presence of `xref` on a write request can be used to convert a
normal Resource into a cross reference one, and in which case any existing
attributes on the source Resource MUST be deleted (except for `id` and `xref`).

The `xref` attribute MUST be a relative URL from the base URL of the Registry,
and MUST NOT start with a `/`, while the base URL of the Registry MUST end
with a `/`. This allows for simple concatenation of the two URLs to derive
the full URL of the target Resource.

If the target Resource itself is a cross reference Resource, then inlining
of the target Resource's attributes MUST NOT be done when serializing the
source Resource. Recursive, or transitively, following of `xref` URLs it not
done.

Both the source and target Resources MUST be of the same Resource model type,
simply having similar Resource type definitions is not sufficient. This
implies that use of the `ximport` feature in the model to reference a
Resource type from another Group type definition MUST be used. See
[`ximport`](#reuse-of-resource-definitions) for more information.

An `xref` value that points to a non-existing Resource, either because
it was deleted or never existed, is not an error and is not a condition
that a server is REQUIRED to detect. In these "dangling xref" situations the
serialization of the source Resource will not include any target Resource
attributes, or nested collections. Rather, it will only show the `id` and
`xref` attributes.

---

#### Resource and Version APIs

For convenience, the Resource and Version create, update and delete APIs can be
summarized as:

**`POST /GROUPs/gID/RESOURCEs`**

- Creates or updates one or more Resources.

**`PUT   /GROUPs/gID/RESOURCEs/rID[$meta]`**<br>
**`PATCH /GROUPs/gID/RESOURCEs/rID$meta`**

- Creates a new Resource, or update the default Version of a Resource.

**`POST /GROUPs/gID/RESOURCEs/rID[$meta]`**

- Creates or updates a single Version of a Resource.

**`POST /GROUPs/gID/RESOURCEs/rID/versions`**

- Creates or updates one or more Versions of a Resource.

**`PUT   /GROUPs/gID/RESOURCEs/rID/versions/vID[$meta]`**<br>
**`PATCH /GROUPs/gID/RESOURCEs/rID/versions/vID$meta`**

- Creates or updates a single Version of a Resource.

And the delete APIs are summarized as:

**`DELETE /GROUPs/gID/RESOURCEs`**

- Delete a list of Resources, or all if the list is absent.

**`DELETE /GROUPs/gID/RESOURCEs/rID`**

- Delete a single Resource.

**`DELETE /GROUPs/gID/RESOURCEs/rID/versions`**

- Delete a list of Versions, or all (and the Resource) if the list is absent.

**`DELETE /GROUPs/gID/RESOURCEs/rID/versions/vID`**

- Delete a single Version of a Resource, and the Resource if last Version.

The following sections go into more detail about each API.

---

#### Retrieving a Resource Collection

To retrieve all Resources in a Resource Collection, an HTTP `GET` MAY be used.

The request MUST be of the form:

```yaml
GET /GROUPs/gID/RESOURCEs[?inline=...&filter=...&export]
```

The following query parameters SHOULD be supported by servers:
- `inline` - See [inlining](#inlining) for more information.
- `filter` - See [filtering](#filtering) for more information.
- `export` - See [exporting](#exporting) for more information.

A successful response MUST be of the form:

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Link: <URL>;rel=next;count=UINTEGER ?

{
  "ID": {                                     # The Resource id
    "id": "STRING",                           # The Resource id
    "self": "URL",                            # URL to the Resource

    "versionid": "STRING",
    "name": "STRING", ?
    "epoch": UINTEGER,
    "isdefault": true,
    "description": "STRING", ?
    "documentation": "URL", ?
    "labels": { "STRING": "STRING" * }, ?
    "origin": "URI", ?
    "createdat": "TIME",
    "modifiedat": "TIME",
    "contenttype": "STRING", ?

    "RESOURCEurl": "URL", ?                  # If not local
    "RESOURCE": ... Resource document ..., ? # If inlined & JSON
    "RESOURCEbase64": "STRING", ?            # If inlined & ~JSON

    "xref": "URL", ?

    "defaultversionsticky": BOOLEAN, ?
    "defaultversionid": "STRING",
    "defaultversionurl": "URL",

    "versionsurl": "URL",
    "versionscount": UINTEGER,
    "versions": { Versions collection } ?    # If inlined
  } *
}
```

Where:
- The key (`ID`) of each item in the map MUST be the `id` of the respective
  Resource.

**Examples:**

Retrieve all `definitions` of an `endpoint` whose `id` is `123`:

```yaml
GET /endpoints/123/definitions
```

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Link: <https://example.com/endpoints/123/definitions&page=2>;rel=next;count=100

{
  "456": {
    "id": "456",
    "self": "https://example.com/endpoints/123/definitions/456$meta",

    "name": "Blob Created",
    "epoch": 1,
    "isdefault": true,
    "origin": "http://example.com",
    "createdat": "2024-04-30T12:00:00Z",
    "modifiedat": "2024-04-30T12:00:01Z",

    "defaultversionid": "1.0",
    "defaultversionurl": "https://example.com/endpoints/123/definitions/456/versions/1.0$meta",

    "versionsurl": "https://example.com/endpoints/123/definitions/456/versions",
    "versionscount": 1
  }
}
```

#### Creating or Updating Resources and Versions

These APIs follow the overall pattern described in the [Creating or Updating
Entities](#creating-or-updating-entities) section. Any variations will be
called out.

Creating and updating of Resources via HTTP MAY be done using the HTTP `POST`,
`PUT` or `PATCH` methods as described below:

`POST /GROUPs/gID/RESOURCEs[?nested]`

Where:
- This API MUST create or update one or more Resources within the specified
  Group.
- The HTTP body MUST contain a map of Resources to be created or updated,
  serialized as xRegistry metadata.

`PUT   /GROUPs/gID/RESOURCEs/rID[$meta][?nested]`<br>
`PATCH /GROUPs/gID/RESOURCEs/rID[$meta][?nested]`

Where:
- These APIs MUST create or update a single Resource in the Group.
- When `$meta` is present, the HTTP body MUST be an xRegistry serialization of
  the Resource.
- When `$meta` is absent, the HTTP body MUST contain the Resource's document
  (an empty body means the document is to be empty).

`POST /GROUPs/gID/RESOURCEs/rID[$meta][?setdefaultversionid=vID]`

Where:
- This API MUST create, or update, a single new Version of the specified
  Resource.
- When `$meta` is present, the HTTP body MUST be an xRegistry serialization
  of the Version that is to be created or updated.
- When the `$meta` is absent, the HTTP body MUST contain the Version's document
  (an empty body means the document is to be empty). Note that the xRegistry
  metadata (e.g. the Version's `versionid`) MAY be included as HTTP headers.

`POST /GROUPs/gID/RESOURCEs/rID/versions[?setdefaultversionid=vID]`

Where:
- This API MUST create or update one or more Versions of the Resource.
- The HTTP body MUST contain a map of Versions to be create or updated,
  serialized as xRegistry metadata. Note that the map key of each entry
  MUST be the Version's `versionid` not the Resource's.
- If the Resource does not exist prior to this operation, it MUST be implicitly
  created, the following rules apply:
  - If there is only one Version created, then it MUST become the default
    Version, and use of the `setdefaultversionid` query parameter is OPTIONAL.
  - If there is more than one Version created, then use of the
    `setdefaultversionid` is REQUIRED and MUST be set to the `versionid` of
    one of the specified Versions.
  - There MUST be at least one Version specified in the HTTP body. In other
    words, an empty collection MUST generate an error since creating a Resource
    with no Versions would immediate delete that Resource.

See [Default Version of a Resource](#default-version-of-a-resource) for more
information about the `setdefaultversionid` query parameter.

`PUT   /GROUPs/gID/RESOURCEs/rID/versions/vID[$meta][?setdefaultversionid=vID]`<br>
`PATCH /GROUPs/gID/RESOURCEs/rID/versions/vID[$meta][?setdefaultversionid=vID]`

Where:
- This API MUST create or update single Version in the Resource.
- When `meta` is present, the HTTP body MUST contain the xRegistry metadata
  serialization of the Version.
- When `meta` is absent, the HTTP body MUST contain the Version's document.

See [Default Version of a Resource](#default-version-of-a-resource) for more
information about the `setdefaultversionid` query parameter.

---

To reduce the number of interactions needed, these APIs are designed to allow
for the implicit creation of all parent entities specified in the PATH. And
each entity not already present with the specified `ID` MUST be created with
that `ID`. Note: if any of those entities have REQUIRED attributes then they
can not be implicitly created, and would need to be created manually.

When specified as an xRegistry JSON object, each individual Resource or
Version in the request MUST adhere to the following:

```yaml
{
  "id": "STRING", ?                        # ID of Resource
  "versionid": "STRING", ?                 # ID of Version
  "name": "STRING", ?
  "epoch": UINTEGER, ?
  "isdefault": BOOLEAN, ?
  "description": "STRING", ?
  "documentation": "URL", ?
  "labels": { "STRING": "STRING" * }, ?
  "origin": "URI", ?
  "createdat": "TIME", ?
  "modifiedat": "TIME", ?
  "contenttype": "STRING", ?

  "RESOURCEurl": "URL", ?                  # If not local
  "RESOURCE": ... Resource document ..., ? # If inlined & JSON
  "RESOURCEbase64": "STRING", ?            # If inlined & ~JSON

  "xref": "URL", ?                         # For Resources

  "defaultversionsticky": BOOLEAN, ?       # For Resources
  "defaultversionid": "STRING", ?          # For Resources

  "versions": { Versions collection } ?    # For Resources, if nested
}
```

When the HTTP body contains the Resource's document, then any xRegistry
metadata MUST appear as HTTP headers and the request MUST adhere to the
following:

```yaml
[METHOD] [PATH]
Content-Type: STRING ?
xRegistry-id: STRING ?                     # ID of Resource
xRegistry-versionid: STRING ?              # ID of Version
xRegistry-name: STRING ?
xRegistry-epoch: UINTEGER ?
xRegistry-isdefault: BOOLEAN ?
xRegistry-description: STRING ?
xRegistry-documentation: URL ?
xRegistry-labels-KEY: STRING *
xRegistry-origin: STRING ?
xRegistry-createdat: TIME ?
xRegistry-modifiedat: TIME ?
xRegistry-RESOURCEurl: URL ?
xRegistry-xref: URL ?
xRegistry-defaultversionsticky: BOOLEAN ?  # For Resources
xRegistry-defaultversionid: STRING ?       # For Resources

... entity document ... ?
```

Where:
- In the cases where xRegistry metadata appears as HTTP headers, if the
  `RESOURCEurl` attribute is present with a non-null value, the HTTP body
  MUST be empty. If the `RESOURCEurl` attribute is absent, then the contents
  of the HTTP body (even if empty) are to be used as the entity's document.
- If the Resource's `hasdocument` model attribute has a value of `false` then
  the following rules apply:
  - Any use of the `$meta` suffix MUST generate an error.
  - Any request that includes the xRegistry HTTP headers MUST generate an
    error.
  - An update request with an empty HTTP body MUST be interpreted as a request
    to delete all xRegistry mutable attributes - in essence, resetting the
    entity back to its default state.
- When the xRegistry metadata is serialized as a JSON object, the processing
  of the 3 `RESOURCE` attributes MUST follow these rules:
  - At most only one of the 3 attributes MAY be present in the request, and the
    presence of any one of them MUST delete the other 2 attributes.
  - If the entity already exists and has a document (not a `RESOURCEurl`),
    then absence of all 3 attributes MUST leave all 3 unchanged.
  - An explicit value of `null` for any of the 3 attributes MUST delete all
    3 attributes (and any associated data).
  - When `RESOURCE` is present, the server MAY choose to modify non-semantic
    significant characters. For example, to remove (or add) whitespace. In
    other words, there is no requirement for the server to persist the
    document in the exact byte-for-byte format in which it was provided. If
    that is desired then `RESOURCEbase64` MUST be used instead.
  - On a `PUT` or `POST`, when `RESOURCE` is present, if no `contenttype`
    value is provided then the server MUST set it to same type as the incoming
    request, e.g. `application/json`, even if the entity previous had a
    `contenttype` value.
  - On a `PATCH`, when `RESOURCE` or `RESOURCEbase64` is present, if no
    `contenttype` value is provided then the server MUST set it to the same
    type as the incoming request, e.g. `application/json`, only if the entity
    does not already have a value. Otherwise, the existing value remains
    unchanged.

A successful response MUST include the current representation of the entities
created or updated and be in the same format (`$meta` variant or not) as the
request.

If the request used the `PUT` or `PATCH` variants and a new Version was
created, then a successful response MUST include a `Content-Location` HTTP
header to the newly created Version entity, and if present, it MUST be the
same as the Version's `self` attribute.

Note that the response MUST NOT include any inlinable attributes (such as
`RESOURCE`, `RESOURCEbase64` or nested collections).

**Examples:**

Create a new Resource:

```yaml
PUT /endpoints/123/definitions/456
Content-Type: application/json; charset=utf-8
xRegistry-name: Blob Created

{
  # Definition of a "Blob Created" event excluded for brevity
}
```

```yaml
HTTP/1.1 201 Created
Content-Type: application/json; charset=utf-8
xRegistry-id: 456
xRegistry-versionid: 1.0
xRegistry-self: https://example.com/endpoints/123/definitions/456
xRegistry-name: Blob Created
xRegistry-epoch: 1
xRegistry-defaultversionid: 1.0
xRegistry-defaultversionurl: https://example.com/endpoints/123/definitions/456/versions/1.0
xRegistry-versionsurl: https://example.com/endpoints/123/definitions/456/versions
xRegistry-versionscount: 1
Location: https://example.com/endpoints/123/definitions/456
Content-Location: https://example.com/endpoints/123/definitions/456/versions/1.0

{
  # Definition of a "Blob Created" event excluded for brevity
}
```

Update default Version of a Resource as xRegistry metadata:

```yaml
PUT /endpoints/123/definitions/456$meta
Content-Type: application/json; charset=utf-8

{
  "id": "456",
  "name": "Blob Created",
  "epoch": 1,
  "description": "a cool event",

  "definition": {
    # Updated definition of a "Blob Created" event excluded for brevity
  }
}
```

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Location: https://example.com/endpoints/123/definitions/456/versions/1.0

{
  "id": "456",
  "self": "https://example.com/endpoints/123/definitions/456$meta",

  "versionid": "1.0",
  "name": "Blob Created",
  "epoch": 2,
  "description": "a cool event",
  "createdat": "2024-04-30T12:00:00Z",
  "modifiedat": "2024-04-30T12:00:01Z",

  "definition": {
    # Updated definition of a "Blob Created" event excluded for brevity
  },

  "defaultversionid": "1.0",
  "defaultversionurl": "https://example.com/endpoints/123/definitions/456/versions/1.0$meta",
  "versionsurl": "https://example.com/endpoints/123/definitions/456/versions",
  "versionscount": 1
}
```

Update several Versions (adding a label):

```yaml
POST /endpoints/123/definitions/456/versions
Content-Type: application/json; charset=utf-8

{
  "1.0": {
    "labels": { "customer": "abc" },
    # Remainder of xRegistry metadata excluded for brevity
  },
  "2.0": {
    "labels": { "customer": "abc" },
    # Remainder of xRegistry metadata excluded for brevity
  },
  "3.0": {
    "labels": { "customer": "abc" },
    # Remainder of xRegistry metadata excluded for brevity
  }
}
```

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "1.0": {
    "id": "456",
    "versionid": "1.0",
    "labels": { "customer": "abc" },
    # Remainder of xRegistry metadata excluded for brevity
  },
  "2.0": {
    "id": "456",
    "versionid": "2.0",
    "labels": { "customer": "abc" },
    # Remainder of xRegistry metadata excluded for brevity
  },
  "3.0": {
    "id": "456",
    "versionid": "3.0",
    "labels": { "customer": "abc" },
    # Remainder of xRegistry metadata excluded for brevity
  }
]
```

#### Retrieving a Resource

To retrieve a Resource, an HTTP `GET` MAY be used.

The request MUST be of the form:

```yaml
GET /GROUPs/gID/RESOURCEs/rID
```

This MUST retrieve the default Version of a Resource. Note that `rID` will be
for the Resource and not the `versionid` of the underlying Version (see
[Resources](#resources)).

A successful response MUST either be:
- `200 OK` with the Resource document in the HTTP body.
- `303 See Other` with the location of the Resource's document being
  returned in the HTTP `Location` header if the Resource has a `RESOURCEurl`
  value, and the HTTP body MUST be empty.

And in both cases the Resource's metadata attributes MUST be serialized as HTTP
`xRegistry-` headers when the Resource's `hasdocument` model attribute has a
value of `true`.

Note that if the Resource's `hasdocument` model attribute has a value of
`false` then the "Resource document" will be the xRegistry metadata for the
default Version - same as in the [Retrieving a Resource as
Metadata](#retrieving-a-resource-as-metadata) section but without the explicit
usage of `$meta`.

When `hasdocument` is `true`, the response MUST be of the form:

```yaml
HTTP/1.1 200 OK|303 See Other
Content-Type: STRING ?
xRegistry-id: STRING
xRegistry-versionid: STRING
xRegistry-self: URL
xRegistry-name: STRING ?
xRegistry-epoch: UINT
xRegistry-isdefault: true
xRegistry-description: STRING ?
xRegistry-documentation: URL ?
xRegistry-labels-KEY: STRING *
xRegistry-origin: STRING ?
xRegistry-createdat: TIME
xRegistry-modifiedat: TIME
xRegistry-RESOURCEurl: URL      # If Resource is not in body
xRegistry-xref: URL ?
xRegistry-defaultversionsticky: BOOLEAN ?
xRegistry-defaultversionid: STRING
xRegistry-defaultversionurl: URL
xRegistry-versionsurl: URL
xRegistry-versionscount: UINTEGER
Location: URL ?                 # If Resource is not in body
Content-Location: URL ?

... Resource document ...       # If RESOURCEurl is not set
```

Where:
- `id` MUST be the ID of the Resource, not of the default Version of the
  Resource.
- `versionid` MUST be the `versionid` of the default Version of the Resource.
- `self` MUST be a URL to the Resource, not to the default Version of the
  Resource.
- If `RESOURCEurl` is present then it MUST have the same value as `Location`.
- If `Content-Location` is present then it MUST be a URL to the Version of the
  Resource in the `versions` collection - same as `defaultversionurl`.

#### Retrieving a Resource as Metadata

To retrieve a Resource's metadata (Resource attributes) as a JSON object, an
HTTP `GET` with `$meta` appended to its URL path MAY be used.

The request MUST be of the form:

```yaml
GET /GROUPs/gID/RESOURCEs/rID$meta[?inline=...&filter=...&export]
```

A successful response MUST be of the form:

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Location: URL ?

{
  "id": "STRING",
  "self": "URL",

  "versionid": "STRING",
  "name": "STRING", ?
  "epoch": UINTEGER,
  "isdefault": true,
  "description": "STRING", ?
  "documentation": "URL", ?
  "labels": { "STRING": "STRING" * }, ?
  "origin": "URI", ?
  "createdat": "TIME",
  "modifiedat": "TIME",
  "contenttype": "STRING", ?

  "RESOURCEurl": "URL", ?                  # If not local
  "RESOURCE": ... Resource document ..., ? # If inlined & JSON
  "RESOURCEbase64": "STRING", ?            # If inlined & ~JSON

  "xref": "URL", ?

  "defaultversionsticky": BOOLEAN, ?
  "defaultversionid": "STRING",
  "defaultversionurl": "URL",

  "versionsurl": "URL",
  "versionscount": UINTEGER,
  "versions": { Versions collection } ?    # If inlined
}
```

Where:
- `id` MUST be the Resource's `id`, not the `id` of the default Version,
  appended with `$meta`.
- `self` is a URL to the Resource (with `$meta`), not to the default
  Version of the Resource.
- `RESOURCE`, or `RESOURCEbase64`, MUST only be included if requested via the
  `inline` query parameter and `RESOURCEurl` is not set.
- If `Content-Location` is present then it MUST be a URL to the Version of the
  Resource in the `versions` collection - same as `defaultversionurl`.

The following query parameters SHOULD be supported by servers:
- `inline` - See [inlining](#inlining) for more information.
- `filter` - See [filtering](#filtering) for more information.
- `export` - See [exporting](#exporting) for more information.

**Examples:**

Retrieve a `definition` Resource as xRegistry metadata:

```yaml
GET /endpoints/123/definitions/456$meta
```

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Location: https://example.com/endpoints/123/definitions/456/versions/1.0

{
  "id": "456",
  "self": "https://example.com/endpoints/123/definitions/456$meta,

  "versionid": "1.0",
  "name": "Blob Created",
  "epoch": 1,
  "isdefault": true,
  "createdat": "2024-04-30T12:00:00Z",
  "modifiedat": "2024-04-30T12:00:01Z",

  "defaultversionid": "1.0",
  "defaultversionurl": "https://example.com/endpoints/123/definitions/456/versions/1.0$meta",
  "versionsurl": "https://example.com/endpoints/123/definitions/456/versions",
  "versionscount": 1
}
```

#### Deleting Resources

To delete one or more Resources, and all of their Versions, an HTTP `DELETE`
MAY be used:
- `DELETE /GROUPs/gID/RESOURCEs/rID[?epoch=UINTEGER]`
- `DELETE /GROUPs/gID/RESOURCEs`

The processing of these two APIs is defined in the [Deleting Entities in a
Registry Collection](#deleting-entities-in-a-registry-collection)
section.

Deleting a Resource MUST delete all Versions within the Resource.

---

### Versions

Versions represent historical instances of a Resource. When a Resource is
updated, there are two actions that might take place. First, the update can
completely replace an existing Version of the Resource. This is most typically
done when the previous state of the Resource is no longer needed and there
is no reason to allow people to reference it. The second situation is when
both the old and new Versions of a Resource are meaningful and both might need
to be referenced. In this case the update will cause a new Version of the
Resource to be created and will be have a unique `versionid` within the scope
of the owning Resource.

For example, updating the state of Resource without creating a new Version
would make sense if there is a typo in the `description` field. But, adding
additional data to the document of a Resource might require a new Version and
a new `versionid` (e.g. changing it from "1.0" to "1.1").

This specification does not mandate a particular versioning algorithm or
Version identification (`versionid`) scheme.

When serialized as a JSON object, the Version entity adheres to this form:

```yaml
{
  "id": "STRING",                         # ID of Resource
  "self": "URL",

  "versionid": "STRING",
  "name": "STRING", ?
  "epoch": UINTEGER,
  "isdefault": BOOLEAN, ?
  "description": "STRING", ?
  "documentation": "URL", ?
  "labels": { "STRING": "STRING" * }, ?
  "origin": "URI", ?
  "createdat": "TIME",
  "modifiedat": "TIME",
  "contenttype": "STRING", ?

  "RESOURCEurl": "URL", ?                  # If not local
  "RESOURCE": ... Resource document ..., ? # If inlined & JSON
  "RESOURCEbase64": "STRING" ?             # If inlined & ~JSON
}
```

Versions include the following attributes:
- [`id`](#id-attribute) - REQUIRED in responses and document view, otherwise
  OPTIONAL.
- [`self`](#self-attribute) - REQUIRED in responses, otherwise OPTIONAL - URL
  to this Version, not the Resource.
- [`name`](#name-attribute) - OPTIONAL.
- [`epoch`](#epoch-attribute) - REQUIRED in responses, otherwise OPTIONAL.
- [`description`](#description-attribute) - OPTIONAL.
- [`documentation`](#documentation-attribute) - OPTIONAL.
- [`labels`](#labels-attribute) - OPTIONAL.
- [`origin`](#origin-attribute) - OPTIONAL.
- [`createdat`](#createdat-attribute) - REQUIRED in responses, otherwise
  OPTIONAL.
- [`modifiedat`](#modifiedat-attribute) - REQUIRED in responses, otherwise
  OPTIONAL.
- [`contenttype`](#contenttype-attribute) - OPTIONAL.

and the following Version specific attributes:

- [`versionid`](#versionid-attribute) - REQUIRED in responses and document view,
  otherwise OPTIONAL.
- [`isdefault`](#isdefault-attribute) - REQUIRED when `true`, otherwise
  OPTIONAL.
- [`RESOURCEurl`](#resourceurl-attribute) - OPTIONAL.
- [`RESOURCE`](#resource-attribute) - OPTIONAL.
- [`RESOURCEbase64`](#resourcebase64-attribute) - OPTIONAL.

as defined below:

##### `versionid` Attribute

- Type: String
- Description: An immutable unique identifier of the Version.
- Constraints:
  - MUST be a non-empty string consisting of [RFC3986 `unreserved`
    characters](https://datatracker.ietf.org/doc/html/rfc3986#section-2.3)
    (ALPHA / DIGIT / "-" / "." / "_" / "~").
  - MUST NOT use a value of `null` or `request` due to these being reserved
    for use by the `setdefaultversionid` operation.
  - MUST be case insensitive unique within the scope of the owning Resource.
  - This attribute MUST be treated as case sensitive for look-up purposes.
    This means that an HTTP URL request to an entity with the wrong case for its
    `versionid` MUST be treated as "not found".
  - In cases where the `versionid` is specified outside of the serialization
    of the Version (e.g. part of a request URL, or a map key), its
    presence within the serialization of the entity is OPTIONAL. However, if
    present, it MUST be the same as any other specification of the `versionid`
    outside of the entity, and it MUST be the same as the entity's existing
    `versionid` if one exists, otherwise an error MUST be generated.
  - MUST be immutable.
- Examples:
  - `1.0`
  - `v2`
  - `v3-rc`

Note, since `versionid` is immutable, in order to change its value a new
Version would need to be created with the new `versionid` that is a deep-copy
of the existing Version. Then the existing Version can be deleted.

##### `isdefault` Attribute
- Type: Boolean
- Description: indicates whether this Version is the "default" Version of the
  owning Resource. This value is different from other attributes in that it
  might often be a calculated value rather than persisted in a datastore.
  Thus, when its value changes due to the default Version of a Resource
  changing, the Version itself does not change - meaning the `epoch`, and
  `modifiedat` values remains unchanged.

  See [Creating or Updating Resources and
  Versions](#creating-or-updating-resources-and-versions) for additional
  information about this attribute.

- Constraints:
  - REQUIRED in responses when the value is `true`, OPTIONAL when `false`.
  - REQUIRED in document view when the value is `true`, OPTIONAL when `false`.
  - If present, MUST be either `true` or `false`, case sensitive.
  - If not present in responses, the default value MUST be `false`.
  - If present in requests, it MUST be silently ignored.
- Examples:
  - `true`
  - `false`

##### `contenttype` Attribute
- Type: String
- Description: The media type of the entity as defined by
  [RFC9110](https://datatracker.ietf.org/doc/html/rfc9110#media.type).
- Constraints:
  - SHOULD be compliant with
    [RFC9110](https://datatracker.ietf.org/doc/html/rfc9110#media.type).
  - When serialized as an HTTP header, it MUST be named `Content-Type` not
    `xRegistry-contenttype` like other xRegistry headers.
  - On an update request when the xRegistry metadata appears in HTTP headers,
    unlike other attributes that will remain unchanged when not specified,
    this attribute MUST be erased if the incoming request does not include
    the `Content-Type` HTTP header.
  - This attribute MAY be specified even for Resources that use the
    `RESOURCEurl` attribute. While this specification can not guarantee that
    this attribute's value will match the `Content-Type` returned by an
    HTTP `GET` to the `RESOURCEurl`, it is expected that they will match.
- Examples:
  - `application/json`

##### `RESOURCEurl` Attribute
- Type: URI
- Description: if the Resources document is stored outside of the
  current Registry then this attribute MUST contain a URL to the
  location where it can be retrieved. If the value of this attribute
  is a well-known identifier that is readily understood by all registry
  users and resolves to a common representation of the Resource, or
  an item in some private store/cache, rather than a networked document
  location, then it is RECOMMENDED for the value to be a uniform resource
  name ([URN](https://datatracker.ietf.org/doc/html/rfc8141)).
- Constraints:
  - REQUIRED if the Resource's document is not stored inside of the current
    Registry.
  - If the document is stored in a network accessible endpoint then the
    referenced URL MUST support an HTTP(s) `GET` to retrieve the contents.
  - MUST NOT be present if the Resource's `hasdocument` model attribute is
    set to `false`.

##### `RESOURCE` Attribute
- Type: Resource Document
- Description: This attribute is a serialization of the corresponding
  Resource document's contents. If the document bytes "as is" allow for them to
  appear as the value of this attribute, then this attribute MUST be used if
  the request asked for the document to be inlined in the response.
- Constraints
  - MUST NOT be present when the Resource's Registry metadata is being
    serialized as HTTP headers.
  - If the Resource's document is to be serialized and is not empty,
    then either `RESOURCE` or `RESOURCEbase64` MUST be present.
  - MUST only be used if the Resource document (bytes) is in the same
    format as the Registry Resource entity.
  - MUST NOT be present if `RESOURCEbase64` is also present.
  - MUST NOT be present if the Resource's `hasdocument` model attribute is
    set to `false.

##### `RESOURCEbase64` Attribute
- Type: String
- Description: This attribute is a base64 serialization of the corresponding
  Resource document's contents. If the Resource document (which is stored as
  an array of bytes) are not conformant with the format being used to serialize
  with the Resource object (i.e. as a JSON value), then this attribute MUST be
  used in instead of the `RESOURCE` attribute.
- Constraints:
  - MUST NOT be present when the Resource's Registry metadata is being
    serialized as HTTP headers.
  - If the Resource's document is to be serialized and it is not empty,
    then either `RESOURCE` or `RESOURCEbase64` MUST be present.
  - MUST be a base64 encoded string of the Resource's document.
  - MUST NOT be present if `RESOURCE` is also present.
  - MUST NOT be present if the Resource's `hasdocument` model attribute is
    set to `false.

#### Version IDs

If a server does not support client-side specification of the `versionid` of a
new Version (see the `setversionid` attribute in the [Registry
Model](#registry-model), or if a client chooses to not specify the `versionid`,
then the server MUST assign new Version an `versionid` that is unique within
the scope of its owning Resource.

Servers MAY have their own algorithm for the creation of new Version
`versionid` values, but the default algorithm is as follows:
- `versionid` MUST be a string serialization of a monotonically increasing
  (by `1`) unsigned integer starting with `1` and is scoped to the owning
  Resource.
- Each time a new `versionid` is needed, if an existing Version already has
  that `versionid` then the server MUST generate the next `versionid` value
  and try again.
- The search for the next value does not restart with `1` each time, it MUST
  continue from the highest previously generated value.

With this default versioning algorithm, when semantic versioning is needed,
it is RECOMMENDED to include a major version identifier in the Resource `id`,
like `"com.example.event.v1"` or `"com.example.event.2024-02"`, so that
incompatible, but historically related Resources can be more easily identified
by users and developers. The Version's `versionid` then functions as the
semantic minor version identifier.

#### Default Version of a Resource

As Versions of a Resource are added or removed there needs to be a mechanism
by which the "default" one is determined. There are three options for how this
might be determined:

1. Server's choice. If the Resource's model has the `setdefaultversionsticky`
   aspect set to `false` then the server will always choose which Version is
   the "default" and any attempt by the client to control it MUST result in the
   generation of an error.

   This specification does not mandate the algorithm that the server uses,
   however the default choice SHOULD be "newest = default" (option 2).

2. Newest = Default. The newest Version created (based on `createdat` timestamp)
   is always the "default" Version. This is the default choice. If more than
   one Version has the same "newest" `createdat` timestamp, then the choice
   is indeterminate.

3. Client explicitly chooses the "default". In this option, a client has
   explicitly chosen which Version is the "default" and it will not change
   until a client chooses another Version, or that Version is deleted (in
   which case the server MUST revert back to option 2 (newest = default)).
   This is referred to as the default Version being "sticky" as it will not
   change until explicitly requested by a client.

If supported (as determined by the `setdefaultversionsticky` model attribute),
a client MAY choose the "default" Version two ways:
1. Via the Resource `defaultversionsticky` and `defaultversionid` attributes.
   See [Resource Attributes](#resource-attributes) for more information
   about these attributes.
2. Via the `setdefaultversionid` query parameter that is available on certain
   APIs, as defined below.

The `setdefaultversionid` query parameter is defined as:

```yaml
...?setdefaultversionid=vID
```

Where:
- `vID` is the `versionid` of the Version that is to become the "default"
  version of the referenced Resource. A value of `null` indicates that the
  client wishes to switch to the "newest = default" algorithm, in other words,
  the "sticky" aspect of the current default Version will be removed. It is
  STRONGLY RECOMMENDED that clients provide an explicit value when possible.
  However, if a Version create operation asks the server to choose the value,
  then including that value in the query parameter is not possible. In those
  cases a value of `request` MAY be used as a way to reference the Version
  being processed in the current request, and if the request creates more than
  one Version then an error MUST be generated.
- If a non-null and non-request `vID` does not reference an existing Version of
  the Resource, after all Version processing is completed, then an HTTP
  `400 Bad Request` error MUST be generated.

Any use of this query parameter on a Resource that has the
`setdefaultversionsticky` aspect set to `false` MUST generate an error.

Updating a Resource's `defaultversionid`, regardless of the mechanism used to
do so, MUST adhere to the following rules:
- Aside from the special values of `null` and `request`, its value MUST be
  the `versionid` of a Version for the specified Resource after all Version
  processing is completed (i.e. after any Versions are added or removed). Its
  value is not limited to the Versions involved in the current operation.
- When the operation also involves updating a Resource's "default" Version's
  attributes, the update to the default Version pointer MUST be done before
  the attributes are updated. In other words, the Version updated is the new
  default Version, not the old one.
- Changing the default Version of a Resource MUST NOT increment the `epoch`
  or `modifiedat` values of any Version of the Resource.

#### Retrieving all Versions

To retrieve all Versions of a Resource, an HTTP `GET` MAY be used.

The request MUST be of the form:

```yaml
GET /GROUPs/gID/RESOURCEs/rID/versions[?inline=...&filter=...&export]
```

The following query parameters SHOULD be supported by servers:
- `inline` - See [inlining](#inlining) for more information.
- `filter` - See [filtering](#filtering) for more information.
- `export` - See [exporting](#exporting) for more information.

A successful response MUST be of the form:

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Link: <URL>;rel=next;count=UINTEGER ?

{
  "ID": {                                     # The versionid
    "id": "STRING",                           # ID of Resource
    "self": "URL",

    "versionid": "STRING",
    "name": "STRING", ?
    "epoch": UINTEGER,
    "isdefault": BOOLEAN,
    "description": "STRING", ?
    "documentation": "URL", ?
    "labels": { "STRING": "STRING" * }, ?
    "origin": "URI", ?
    "createdat": "TIME",
    "modifiedat": "TIME",
    "contenttype": "STRING", ?

    "RESOURCEurl": "URL", ?                  # If not local
    "RESOURCE": ... Resource document ..., ? # If inlined & JSON
    "RESOURCEbase64": "STRING" ?             # If inlined & ~JSON
  } *
}
```

Where:
- The key (`ID`) of each item in the map MUST be the `versionid` of the
  respective Version.

**Examples:**

Retrieve all Version of a `definition` Resource:

```yaml
GET /endpoints/123/definitions/456/versions
```

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Link: <https://example.com/endpoints/123/definitions/456/versions&page=2>;rel=next;count=100

{
  "1.0": {
    "id": "456",
    "self": "https://example.com/endpoints/123/definitions/456$meta",

    "versionid": "1.0",
    "name": "Blob Created",
    "epoch": 1,
    "isdefault": true,
    "createdat": "2024-04-30T12:00:00Z",
    "modifiedat": "2024-04-30T12:00:01Z",
  }
}
```

#### Creating or Updating Versions

See [Creating or Updating Resources and
Versions](#creating-or-updating-resources-and-versions).

#### Retrieving a Version

To retrieve a particular Version of a Resource, an HTTP `GET` MAY be used.

The request MUST be of the form:

```yaml
GET /GROUPs/gID/RESOURCEs/rID/versions/vID
```

A successful response MUST either return the Version or an HTTP redirect to
the `RESOURCEurl` value if set.

In the case of returning the Version's document, the response MUST be of the
form:

```yaml
HTTP/1.1 200 OK
Content-Type: STRING ?
xRegistry-id: STRING
xRegistry-versionid: STRING
xRegistry-self: URL
xRegistry-name: STRING ?
xRegistry-epoch: UINT
xRegistry-isdefault: BOOLEAN ?
xRegistry-description: STRING ?
xRegistry-documentation: URL ?
xRegistry-labels-KEY: STRING *
xRegistry-origin: STRING ?
xRegistry-createdat: TIME
xRegistry-modifiedat: TIME

... Version document ...
```

Where:
- `id` MUST be the ID of the owning Resource
- `self` MUST be a URL to the Version, not to the owning Resource.

In the case of a redirect, the response MUST be of the form:

```yaml
HTTP/1.1 303 See Other
Content-Type: STRING ?
xRegistry-id: STRING
xRegistry-versionid: STRING
xRegistry-self: URL
xRegistry-name: STRING ?
xRegistry-epoch: UINT
xRegistry-isdefault: BOOLEAN ?
xRegistry-description: STRING ?
xRegistry-documentation: URL ?
xRegistry-labels-KEY: STRING *
xRegistry-origin: STRING ?
xRegistry-createdat: TIME
xRegistry-modifiedat: TIME
xRegistry-RESOURCEurl: URL
Location: URL
```

Where:
- `id` MUST be the ID of the owning Resource
- `self` MUST be a URL to the Version, not to the owning Resource.
- `Location` and `RESOURCEurl` MUST have the same value.

**Examples:**

Retrieve a specific Version (`1.0`) of a `definition` Resource:

```yaml
GET /endpoints/123/definitions/456/versions/1.0
```

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
xRegistry-id: 456
xRegistry-id: 1.0
xRegistry-self: https://example.com/endpoints/123/definitions/456/versions/1.0
xRegistry-name: Blob Created
xRegistry-epoch: 2
xRegistry-isdefault: true

{
  # Definition of a "Blob Created" event excluded for brevity
}
```

#### Retrieving a Version as Metadata

To retrieve a particular Version's metadata, an HTTP `GET` with `$meta`
appended to its `id` MAY be used.

The request MUST be of the form:

```yaml
GET /GROUPs/gID/RESOURCEs/rID/versions/vID$meta[?inline=...]
```

The following query parameter SHOULD be supported by servers:
- `inline` - See [inlining](#inlining) for more information.
- `export` - See [exporting](#exporting) for more information.

A successful response MUST be of the form:

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "id": "STRING",
  "self": "URL",
  "versionid": "STRING",
  "name": "STRING", ?
  "epoch": UINTEGER,
  "isdefault": BOOLEAN,
  "description": "STRING", ?
  "documentation": "URL", ?
  "labels": { "STRING": "STRING" * }, ?
  "origin": "URI", ?
  "createdat": "TIME",
  "modifiedat": "TIME",
  "contenttype": "STRING", ?

  "RESOURCEurl": "URL", ?                  # If not local
  "RESOURCE": ... Resource document ..., ? # If inlined & JSON
  "RESOURCEbase64": "STRING" ?             # If inlined & ~JSON
}
```

Where:
- `id` MUST be the Version's `id` and not the `id` of the owning Resource.
- `self` MUST be a URL to the Version, not to the owning Resource.

**Examples:**

Retrieve a specific Version of a `definition` Resource as xRegistry metadata:

```yaml
GET /endpoints/123/definitions/456/versions/1.0$meta
```

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "id": "456",
  "self": "https://example.com/endpoints/123/definitions/456/versions/1.0$meta",
  "versionid": "1.0",
  "name": "Blob Created",
  "epoch": 2,
  "isdefault": true,
  "createdat": "2024-04-30T12:00:00Z",
  "modifiedat": "2024-04-30T12:00:01Z",
}
```

#### Deleting Versions

To delete one or more Versions of a Resource, an HTTP `DELETE` MAY be used:
- `DELETE /GROUPs/gID/RESOURCEs/rID/versions/vid[?epoch=UINTEGER&setdefaultversionid=vID]`
- `DELETE /GROUPs/gID/RESOURCEs/rID/versions[?setdefaultversionid=vID]`

The processing of these two APIs is defined in the [Deleting Entities in a
Registry Collection](#deleting-entities-in-a-registry-collection)
section. For more information about the `setdefaultversionid` query
parameter see the [Default Version of a
Resource](#default-version-of-a-resource) section.

If as a result of one of these operations a Resource has no Versions, then the
Resource MUST also be deleted.

A successful response MUST return either:

```yaml
HTTP/1.1 204 No Content
```

with an empty HTTP body, or:

```yaml
HTTP/1.1 200 OK
```

If, as an extension, the server chooses to return additional data in the
HTTP body.

**Examples:**

Delete a single Version of a `definition` Resource:

```yaml
DELETE /endpoints/123/definitions/456/versions/1.0
```

```yaml
HTTP/1.1 204 No Content
```

---

### Inlining

The `inline` query parameter MAY be used on read requests to indicate how
nested collections, or certain (potentially large) attributes, are to be
exposed in the response message.

The `inline` query parameter on a `GET` request indicates that the response
MUST include the contents of all specified inlinable attributes. Inlinable
attributes include:
- All [Registry Collection](#registry-collections) types - e.g. `GROUPs`,
  `RESOURCEs` and `versions`.
- The `RESOURCE` attribute in a Resource or Version.

While the `RESOURCE` and `RESOURCEbase64` attributes are defined as two
separate attributes, they are technically two separate "views" of the same
underlying data. As such, the usage of each will be based on the content type
of the Resource, specifying `RESOURCE` in the `inline` query parameter MUST
be interpreted as a request for the appropriate attribute. In other words,
`RESOURCEbase64` is not a valid inlinable attribute name.

Use of this feature is useful for cases where the contents of the Registry are
to be represented as a single (self-contained) document.

Some examples:
- `GET /?inline=endpoints`
- `GET /?inline=endpoints.definitions`
- `GET /endpoints/123/?inline=definitions.definition`
- `GET /endpoints/123/definitions/456?inline=definition`

The format of the `inline` query parameter is:

```yaml
inline[=PATH[,...]]
```

Where `PATH` is a string indicating which inlinable attributes to show in
in the response. References to nested attributes are represented using a
dot(`.`) notation - for example `GROUPs.RESOURCEs`. To reference an attribute
with a dot as part of its name, the JSON PATH escaping mechanism MUST be
used: `['my.name']`. For example, `prop1.my.name.prop2` would be specified
as `prop1['my.name'].prop2` if `my.name` is the name of one attribute.

There MAY be multiple `PATH`s specified, either as comma separated values on
a single `inline` query parameter or via multiple `inline` query parameters.
Absence of a `PATH`, or a `PATH` value of `*` indicates that all nested
inlinable attributes MUST be inlined on all levels of the data returned.

The specific value of `PATH` will vary based on where the request is directed.
For example, a request to the root of the Registry MUST start with a `GROUPs`
name, while a request directed at a Group would start with a `RESOURCEs` name.

For example, given a Registry with a model that has `endpoints` as a Group and
`definitions` as a Resource within `endpoints`, the table below shows some
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
its parents to be inlined as well, but just the parent's attributes needed to
show the child's attribute. In other words, just the child's Registry
Collection in the parent, not all of them.

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
- If the collection is inlined it MUST only include entities that match the
  filter expression(s).
- The collection `url` attribute MUST include the appropriate filter
  expression(s) in its query parameters such that an HTTP `GET` to that URL
  would return the same subset of entities.
- The collection `count` attribute MUST only count the entities that match the
  filter expression(s).

The format of the `filter` query parameter is:

```yaml
filter=EXPRESSION[,EXPRESSION]
```

Where:
- All `EXPRESSION` values within the scope of one `filter` query parameter
  MUST be evaluated as a logical `AND` and any matching entities MUST satisfy
  all of the specified expressions within that `filter` query parameter.
- The `filter` query parameter can appear multiple times and if so MUST
  be evaluated as a logical `OR` and the response MUST include all entities
  that match any of the individual filter query parameters.

The abstract processing logic would be:
- For each `filter` query parameter, find all entities that satisfy all
  expressions for that `filter`.
- After processing all individual `filter` query parameters, combine those
  individual results into one result set and remove any duplicates - adjusting
  any collection `url` and `count` values as needed.

The format of `EXPRESSION` is:

```yaml
[PATH.]ATTRIBUTE[=[VALUE]]
```

Where:
- `PATH` MUST be a dot(`.`) notation traversal of the Registry to the entity
  of interest, or absent if at the top of the Registry request. Note that
  the `PATH` value is based on the requesting URL and not the root of the
  Registry. See the examples below. To reference an attribute with a dot as
  part of its name, the JSON PATH escaping mechanism MUST be used:
  `['my.name']`. For example, `prop1.my.name.prop2` would be specified as
  `prop1['my.name'].prop2` if `my.name` is the name of one attribute.
- `PATH` MUST only consist of valid `GROUPs`, `RESOURCEs` or `versions`,
  otherwise an error MUST be generated.
- `ATTRIBUTE` MUST be the attribute in the entity to be examined.
- Complex attributes (e.g. `labels`) MUST use dot(`.`) to reference nested
  attributes. For example: `labels.stage=dev` for a filter.
- A reference to a nonexistent attribute SHOULD NOT generate an error and
  SHOULD be treated the same as a non-matching situation.
- When the equals sign (`=`) is present with a `VALUE` then `VALUE` MUST be
  the desired value of the attribute being examined. Only entities whose
  specified `ATTRIBUTE` with this `VALUE` MUST be included in the response.
- When the equals sign (`=`) is present without a `VALUE` then the implied
  value is an empty string, and the matching MUST be as specified in the
  previous bullet.
- When the equals sign (`=`) is not present then the response MUST include all
  entities that have the `ATTRIBUTE` present with any value. In database terms
  this is equivalent to checking for entities with a non-NULL value.

When comparing an `ATTRIBUTE` to the specified `VALUE` the following rules
MUST apply for an entity to be considered a match of the filter expression:
- For numeric attributes, it MUST be an exact match.
- For string attributes, its value MUST contain the `VALUE` within it but
  does not need to be an exact case match.
- For boolean attributes, its value MUST be an exact case sensitive match
  (`true` or `false`).

If the request references an entity (not a collection), and the `EXPRESSION`
references an attribute in that entity (i.e. there is no `PATH`), then if the
`EXPRESSION` does not match the entity, that entity MUST NOT be returned. In
other words, a `404 Not Found` would be generated in the HTTP protocol case.

**Examples:**

| Request PATH | Filter query | Commentary |
| --- | --- | --- |
| / | `filter=endpoints.description=cool` | Only endpoints with the word `cool` in the description |
| /endpoints | `filter=description=CooL` | Same results as previous, with a different request URL |
| / | `filter=endpoints.definitions.versions.versionid=1.0` | Only versions (and their owning endpoints.definitions) that have a versionid of `1.0` |
| / | `filter=endpoints.name=myendpoint,endpoints.description=cool& filter=schemagroups.labels.stage=dev` | Only endpoints whose name is `myendpoint` and whose description contains the word `cool`, as well as any schemagroups with a `label` name/value pair of `stage/dev` |
| / | `filter=description=no-match` | Returns a 404 if the Registry's `description` doesn't contain `no-match` |

Specifying a filter does not imply inlining.

### Exporting

The `export` query parameter MAY be used on read requests to indicate that the
response processing MUST be modified in the following ways:
- All possible inlining MUST be performed. In other words, an implied
  `?inlining=*` MUST be in effect. The presence of the `?inline` query
  parameter, even if set to `*` MUST generate an error.
- No filtering of the response entities is to be done. The presence of the
  `filter` query parameter MUST generate an error.
- The serialization of a Resource MUST NOT include the default Version
  attributes as they MUST appear in the serialization of the default Version
  within the `versions` collection. This includes the `versionid` attribute.
- Resources that are cross references (i.e. they have the `xref` attribute
  defined), MUST NOT include the target Resource's attributes or nested
  collections in its serialization.
- Resource attributes (not Version attributes) with the `exportrequired`
  aspect set to `false` MUST NOT be serialized as part of the Resource.
  However, attributes with `exportrequired` set to `true` MUST appear.

The `export` semantics are designed to optimize the output for use by clients
that want to retrieve a complete portion of the Registry's hierarchy with
minimal duplication of information. Note that the `export` output can be
used on a subsequent update/create operation.

The `?export` query parameter MAY be used on any level of the Registry's
hierarchy.

As noted above, `export` changes the serialization rules of Resources by
removing the Version specific attributes. For clarity, the serialization of a
Resource when `export` is used will adhere to the following:

```yaml
{
  "id": "STRING",
  "self": "URL",

  "xref": "URL", ?

  "defaultversionsticky": BOOLEAN, ?
  "defaultversionid": "STRING",
  "defaultversionurl": "URL",

  "versionsurl": "URL",
  "versionscount": UINTEGER,
  "versions": { ... }
}
```

### HTTP Header Values

Some attributes can contain arbitrary UTF-8 string content,
and per [RFC7230, section 3][rfc7230-section-3], HTTP headers MUST only use
printable characters from the US-ASCII character set, and are terminated by a
CRLF sequence with OPTIONAL whitespace around the header value.

When encoding an attribute's value as an HTTP header it MUST be
percent-encoded as described below. This is compatible with [RFC3986, section
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

- Space (U+0020).
- Double-quote (U+0022).
- Percent (U+0025).
- Any characters outside the printable ASCII range of U+0021-U+007E
  inclusive.

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

- The characters, 'E', 'u', 'r', 'o' do not require encoding.
- Space, the Euro symbol, and the grinning face emoji require encoding.
  They are characters U+0020, U+20AC and U+1F600 respectively.
- The encoded HTTP header value is therefore "Euro%20%E2%82%AC%20%F0%9F%98%80"
  where "%20" is the encoded form of space, "%E2%82%AC" is the encoded form
  of the Euro symbol, and "%F0%9F%98%80" is the encoded form of the
  grinning face emoji.

[rfc7230-section-3]: https://tools.ietf.org/html/rfc7230#section-3
[rfc3986-section-2-1]: https://tools.ietf.org/html/rfc3986#section-2.1
[rfc7230-section-3-2-6]: https://tools.ietf.org/html/rfc7230#section-3.2.6
