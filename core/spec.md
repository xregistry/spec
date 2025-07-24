# xRegistry Service - Version 1.0-rc2

## Abstract

A Registry Service exposes Resources and their metadata, for the purpose
of enabling discovery of those Resources for either end-user consumption or
automation and tooling.

## Table of Contents

- [Overview](#overview)
- [Notations and Terminology](#notations-and-terminology)
  - [Notational Conventions](#notational-conventions)
  - [Terminology](#terminology)
- [Registry Design](#registry-design)
- [Registry Attributes and APIs](#registry-attributes-and-apis)
  - [Implementation Customizations](#implementation-customizations)
  - [Attributes and Extensions](#attributes-and-extensions)
  - [Registry HTTP APIs](#registry-http-apis)
    - [Registry Collections](#registry-collections)
    - [Entity Processing Rules](#entity-processing-rules)
  - [Registry Root APIs](#registry-root-apis)
    - [Retrieving the Registry](#retrieving-the-registry)
    - [Updating the Registry Entity](#updating-the-registry-entity)
  - [Registry Capabilities](#registry-capabilities)
  - [Registry Model](#registry-model)
    - [Retrieving the Registry Model](#retrieving-the-registry-model)
    - [Creating or Updating the
      Registry Model](#creating-or-updating-the-registry-model)
  - [Groups APIs](#groups-apis)
    - [Retrieving a Group Collection](#retrieving-a-group-collection)
    - [Creating or Updating Groups](#creating-or-updating-groups)
    - [Retrieving a Group](#retrieving-a-group)
    - [Deleting Groups](#deleting-groups)
  - [Resources APIs](#resources-apis)
    - [Retrieving a Resource Collection](#retrieving-a-resource-collection)
    - [Creating or Updating Resources and
       Versions](#creating-or-updating-resources-and-versions)
    - [Retrieving a Resource](#retrieving-a-resource)
    - [Deleting Resources](#deleting-resources)
  - [Versions APIs](#versions-apis)
    - [Retrieving all Versions](#retrieving-all-versions)
    - [Creating or Updating Versions](#creating-or-updating-versions)
    - [Retrieving a Version](#retrieving-a-version)
    - [Deleting Versions](#deleting-versions)
  - [Configuring Responses](#configuring-responses)
    - [Binary Flag](#binary-flag)
    - [Collections Flag](#collections-flag)
    - [Doc Flag](#doc-flag)
    - [Filter Flag](#filter-flag)
    - [Inline Flag](#inline-flag)
  - [HTTP Header Values](#http-header-values)
  - [Error Processing](#error-processing)
  - [Events](#events)

## Overview

A Registry Service is one that manages metadata about Resources. At its core,
the management of an individual Resource is simply a REST-based interface for
creating, modifying, and deleting the Resource. However, many Resource models
share a common pattern of grouping Resources and can optionally support
versioning of those Resources. This specification aims to provide a common
interaction pattern for these types of services with the goal of providing an
interoperable framework that will enable common tooling and automation.

This document is meant to be a framework from which additional specifications
can be defined that expose model-specific Resources and metadata.

As of today, this specification only specifies an HTTP-based interaction model.
This is not meant to imply that other protocols cannot be supported, and
other protocols will likely be added in the future. When that happens, this
specification will be restructured to have clean separation between a
protocol-agnostic core and protocol-specific requirements.

A Registry consists of two main types of entities: Resources and Groups.

Resources typically represent the main data of interest for users of the
Registry, while Groups, as the name implies, is a mechanism by which related
Resources are arranged together under a single collection.

This specification defines a set of common metadata that can appear on both
Resources and Groups, and allows for domain-specific extensions to be added.

See the [Registry Design](#registry-design) section for a more complete
discussion of the xRegistry concepts.

The following 3 diagrams show (from left to right):<br>
1 - The core concepts of the Registry in its most abstract form.<br>
2 - A Registry concept model with multiple types of Groups/Resources.<br>
3 - A concrete sample usage of Registry that includes the use of an attribute
    on "Message Definition" that is a reference to a "Schema" document - all
    within the same Registry instance.

<img src="./xregbasicmodel.png"
 height="300">&nbsp;&nbsp;&nbsp;<img
 src="./xregfullmodel.png" height="300">&nbsp;&nbsp;&nbsp;<img
 src="./xregsample.png" height="300">

For easy reference, the JSON serialization of a Registry adheres to this
pseudo JSON form:

```yaml
{
  "specversion": "<STRING>",
  "registryid": "<STRING>",
  "self": "<URL>",
  "shortself": "<URL>", ?
  "xid": "<XID>",
  "epoch": <UINTEGER>,
  "name": "<STRING>", ?
  "description": "<STRING>", ?
  "documentation": "<URL>", ?
  "icon": "<URL>", ?
  "labels": { "<STRING>": "<STRING>" * }, ?
  "createdat": "<TIMESTAMP>",
  "modifiedat": "<TIMESTAMP>",

  "capabilities": {                     # Supported capabilities/options
    "apis": [ "/capabilities", "/export", "/model" ],
    "flags": [                          # Query parameters
      "collections",? "doc",? "epoch",? "filter",?
      "ignoredefaultversionid",? "ignoredefaultversionsticky",? "ignoreepoch",?
      "ignorereadonly",?  "inline", ? "offered",?
      "setdefaultversionid",?  "sort",? "specversion",?
      "<STRING>" *
    ],
    "mutable": [                        # What is mutable in the Registry
      "capabilities",? "entities",? "model",? "<STRING>"*
    ], ?
    "pagination": <BOOLEAN>, ?
    "shortself": <BOOLEAN>, ?
    "specversions": [ "1.0-rc2", "<STRING>"* ], ?
    "stickyversions": <BOOLEAN>, ?
    "versionmodes": [ "manual", "createdat",? "modifiedat",? "semver",
      "<STRING>"* ],

    "<STRING>": ... *                   # Extension capabilities
  }, ?

  "model": {                            # Full model. Only if inlined
    "description": "<STRING>", ?
    "documentation": "<URL>", ?
    "labels": { "<STRING>": "<STRING>" * }, ?
    "attributes": {                     # Registry-level attributes/extensions
      "<STRING>": {                     # Attribute name (case-sensitive)
        "name": "<STRING>",             # Same as attribute's key
        "type": "<TYPE>",                 # string, decimal, array, object, ...
        "target": "<XIDTYPE>", ?        # If "type" is "xid" or "url"
        "namecharset": "<STRING>", ?    # If "type" is "object"
        "description": "<STRING>", ?
        "enum": [ <VALUE> * ], ?        # Array of scalars of type "<TYPE>"
        "strict": <BOOLEAN>, ?          # Just "enum" values? Default=true
        "readonly": <BOOLEAN>, ?        # From client's POV. Default=false
        "immutable": <BOOLEAN>, ?       # Once set, can't change. Default=false
        "required": <BOOLEAN>, ?        # Default=false
        "default": <VALUE>, ?           # Scalar attribute's default value

        "attributes": { ... }, ?        # If "type" above is object
        "item": {                       # If "type" above is map,array
          "type": "<TYPE>", ?           # map value type, or array type
          "target": "<XIDTYPE>", ?      # If this item "type" is xid/url
          "namecharset": "<STRING>", ?  # If this item "type" is object
          "attributes": { ... }, ?      # If this item "type" is object
          "item": { ... } ?             # If this item "type" is map,array
        } ?

        "ifvalues": {                   # If "type" is scalar
          "<STRING>": {                 # Possible attribute value
            "siblingattributes": { ... } # See "attributes" above
          } *
        } ?
      } *
    },

    "groups": {
      "<STRING>": {                       # Key=plural name, e.g. "endpoints"
        "plural": "<STRING>",             # e.g. "endpoints"
        "singular": "<STRING>",           # e.g. "endpoint"
        "description": "<STRING>", ?
        "documentation": "<URL>", ?
        "icon": "<URL>", ?
        "labels": { "<STRING>": "<STRING>" * }, ?
        "modelversion": "<STRING>", ?     # Version of the group model
        "compatiblewith": "<URI>", ?      # Statement of compatibility
        "attributes": { ... }, ?          # Group-level attributes/extensions
        "ximportresources": [ "<XIDTYPE>", * ], ?   # Include these Resources

        "resources": {
          "<STRING>": {                   # Key=plural name, e.g. "messages"
            "plural": "<STRING>",         # e.g. "messages"
            "singular": "<STRING>",       # e.g. "message"
            "description": "<STRING>", ?
            "documentation": "<URL>", ?
            "icon": "<URL>", ?
            "labels": { "<STRING>": "<STRING>" * }, ?
            "modelversion": "<STRING>", ? # Version of the resource model
            "compatiblewith": "<URI>", ?  # Statement of compatibility
            "maxversions": <UINTEGER>, ?  # Num Vers(>=0). Default=0(unlimited)
            "setversionid": <BOOLEAN>, ?  # vid settable? Default=true
            "setdefaultversionsticky": <BOOLEAN>, ? # sticky settable? Default=true
            "hasdocument": <BOOLEAN>, ?   # Has separate document. Default=true
            "versionmode": "<STRING>", ?  # 'ancestor' processing algorithm
            "singleversionroot": <BOOLEAN>, ? # Default=false"
            "typemap": <MAP>, ?               # contenttype mappings
            "attributes": { ... }, ?          # Version attributes/extensions
            "resourceattributes": { ... }, ?  # Resource attributes/extensions
            "metaattributes": { ... } ?       # Meta attributes/extensions
          } *
        } ?
      } *
    } ?
  }, ?
  "modelsource": { ... }, ?                        # Input model, if inlined

  # Repeat for each Group type
  "<GROUPS>url": "<URL>",                          # e.g. "endpointsurl"
  "<GROUPS>count": <UINTEGER>,                     # e.g. "endpointscount"
  "<GROUPS>": {                                    # Only if inlined
    "<KEY>": {                                     # Key=the Group id
      "<GROUP>id": "<STRING>",                     # The Group ID
      "self": "<URL>",
      "shortself": "<URL>", ?
      "xid": "<XID>",
      "epoch": <UINTEGER>,
      "name": "<STRING>", ?
      "description": "<STRING>", ?
      "documentation": "<URL>", ?
      "icon": "<URL>", ?
      "labels": { "<STRING>": "<STRING>" * }, ?
      "createdat": "<TIMESTAMP>",
      "modifiedat": "<TIMESTAMP>",

      # Repeat for each Resource type in the Group
      "<RESOURCES>url": "<URL>",                   # e.g. "messagesurl"
      "<RESOURCES>count": <UINTEGER>,              # e.g. "messagescount"
      "<RESOURCES>": {                             # Only if inlined
        "<KEY>": {                                 # The Resource id
          "<RESOURCE>id": "<STRING>",
          "versionid": "<STRING>",                 # Default Version's ID
          "self": "<URL>",                         # Resource URL, not Version
          "shortself": "<URL>", ?
          "xid": "<XID>",                          # Resource XID, not Version
          "epoch": <UINTEGER>,                     # Start of default Ver attrs
          "name": "<STRING>", ?
          "isdefault": true,
          "description": "<STRING>", ?
          "documentation": "<URL>", ?
          "icon": "<URL>", ?
          "labels": { "<STRING>": "<STRING>" * }, ?
          "createdat": "<TIMESTAMP>",
          "modifiedat": "<TIMESTAMP>",
          "ancestor": "<STRING>",                  # Ancestor's versionid
          "contenttype": "<STRING>, ?              # Add default Ver extensions

          "<RESOURCE>url": "<URL>", ?              # If not local
          "<RESOURCE>": ... Resource document ..., ? # If local & inlined & JSON
          "<RESOURCE>base64": "<STRING>", ?        # If local & inlined & ~JSON
                                                   # End of default Ver attrs
          # Resource-level helper attributes
          "metaurl": "<URL>",
          "meta": {                                # Only if inlined
            "<RESOURCE>id": "<STRING>",
            "self": "<URL>",                       # URL to "meta" object
            "shortself": "<URL>", ?
            "xid": "<XID>",
            "xref": "<XID>", ?                     # xid of linked Resource
            "epoch": <UINTEGER>,                   # Resource's epoch
            "createdat": "<TIMESTAMP>",            # Resource's
            "modifiedat": "<TIMESTAMP>",           # Resource's
            "readonly": <BOOLEAN>,                 # Default=false
            "compatibility": "<STRING>",           # Default=none
            "compatibilityauthority": "<STRING>", ?  # Default=external
            "deprecated": {
              "effective": "<TIMESTAMP>", ?
              "removal": "<TIMESTAMP>", ?
              "alternative": "<URL>", ?
              "documentation": "<URL>"?
            }, ?

            "defaultversionid": "<STRING>",
            "defaultversionurl": "<URL>",
            "defaultversionsticky": <BOOLEAN>      # Default=false
          }, ?
          "versionsurl": "<URL>",
          "versionscount": <UINTEGER>,
          "versions": {                            # Only if inlined
            "<KEY>": {                             # The Version's versionid
              "<RESOURCE>id": "<STRING>",          # The Resource id
              "versionid": "<STRING>",             # The Version id
              "self": "<URL>",                     # Version URL
              "shortself": "<URL>", ?
              "xid": "<XID>",
              "epoch": <UINTEGER>,                 # Version's epoch
              "name": "<STRING>", ?
              "isdefault": <BOOLEAN>,              # Default=false
              "description": "<STRING>", ?
              "documentation": "<URL>", ?
              "icon": "<URL>", ?
              "labels": { "<STRING>": "<STRING>" * }, ?
              "createdat": "<TIMESTAMP>",
              "modifiedat": "<TIMESTAMP>",
              "ancestor": "<STRING>",              # Ancestor's versionid
              "contenttype": "<STRING>", ?

              "<RESOURCE>url": "<URL>", ?                # If not local
              "<RESOURCE>": ... Resource document ..., ? # If inlined & JSON
              "<RESOURCE>base64": "<STRING>" ?           # If inlined & ~JSON
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

For clarity, OPTIONAL attributes (specification-defined and extensions) are
OPTIONAL for clients to use, but the servers' responsibility will vary.
Server-unknown extension attributes MUST be silently stored in the backing
datastore. Specification-defined, and server-known extension attributes, MUST
generate an error if the corresponding feature is not supported or enabled.
However, as with all attributes, if accepting the attribute results in a
bad state (such as exceeding a size limit, or results in a security issue),
then the server MAY choose to reject the request.

In the pseudo JSON format snippets `?` means the preceding item is OPTIONAL,
`*` means the preceding item MAY appear zero or more times, and `+` means the
preceding item MUST appear at least once. The presence of the `#` character
means the remaining portion of the line is a comment. Whitespace characters in
the JSON snippets are used for readability and are not normative.

Use of `<...>` the notation indicates a substitutable value where that is
meant to be replaced with a runtime situational-specific value as defined by
the word/phrase in the angled brackets. For example `<NAME>` would be expected
to be replaced by the "name" of the item being discussed.

When HTTP query parameters are discussed, they are presented as `?<NAME>` where
`<NAME>` is the name of the query parameter.

Use of `<GROUP>` and `<RESOURCE>` are meant to represent the singular
name of a Group and Resource type used, while `<GROUPS>` and
`<RESOURCES>` are the plural name of those respective types. Use of
`<SINGULAR>` represents the singular name of the entity referenced. For
example, for a "schema document" Resource type where its plural name is
defined as `schemas` and its singular name is defined as `schema`, the
`<SINGULAR>` value would be `schema`.

Additionally, the following acronyms are defined:
- `<GID>` is the `<SINGULAR>id` of a Group.
- `<RID>` is the `<SINGULAR>id` of a Resource.
- `<VID>` is the `versionid` of a Version of a Resource.

The following are used to denote an instance of one of the associated data
types (see [Attributes and Extensions](#attributes-and-extensions) for more
information about each data type):
- `<ARRAY>`
- `<BOOLEAN>`
- `<DECIMAL>`
- `<INTEGER>`
- `<MAP>`
- `<OBJECT>`
- `<STRING>`
- `<TIMESTAMP>`
- `<UINTEGER>`
- `<URI>`
- `<URIABSOLUTE>`
- `<URIRELATIVE>`
- `<URITEMPLATE>`
- `<URL>`
- `<URLABSOLUTE>`
- `<URLRELATIVE>`
- `<XID>`
- `<XIDTYPE>`
- `<TYPE>` - one of the allowable data type names (MUST be in lower case)
  listed in [Attributes and Extensions](#attributes-and-extensions)
- `<VALUE>` - an instance of one of the above data types

### Terminology

This specification defines the following terms:

- **Group**

Groups, as the name implies, is a mechanism by which related Resources are
arranged together under a single collection - the Group. The reason for the
grouping is not defined by this specification, so the owners of the Registry
can choose to define (or enforce) any pattern they wish. In this sense, a
Group is similar to a "directory" on a filesystem.

An additional common use for Groups, aside from the contained Resources being
related, is for access control. Managing access control on individual
Resources, while possible, might be cumbersome, so moving it up to the Group
could be a more manageable, and user-friendly, implementation choice.

- **Registry**

A server-side implementation of this specification. Typically, the
implementation would include model-specific Groups, Resources and extension
attributes.

- **Resource**

Resources, typically, represent the main data of interest for the Registry. In
the filesystem analogy, these would be the "files". Each Resource exist under
a single Group and, similar to Groups, have a set of Registry metadata.
However, unlike a Group, which only has Registry metadata, each Resource can
also have a "document" associated with it. For example, a "schema" Resource
might have a "schema document" as its "document". This specification places no
restriction on the type of content stored in the Resource's document.
Additionally, Resources (unlike Groups) MAY be versioned.

- **Version**

A Version is an instance of a Resource that represents a particular state of
the Resource. Each Version of a Resource has its own set of xRegistry metadata
and possibly a domain-specific document associated with it. Each Resource MUST
have at least one Version associated with it.

Clients MAY interact with specific Versions or with the Resource itself, which
is equivalent to interacting with the Resource's "default" Version. While in
many cases the "default" Version will be the "newest" Version, this
specification allows for the "default" Version to be explicitly chosen and
unaffected as other Versions are added or removed.

If versioning is not important for the use case in which the Resource is used,
the default Version can be evolved without creating new ones.

This specification places no requirements on the lifecycle of Versions.
Implementations, or users of the Registry, determine when new Versions are
created, as opposed to updating existing Versions, and how many Versions are
allowed per Resource type.

## Registry Design

As discussed in the [Overview](#overview) section, an xRegistry consists of
two main entities related to the data being managed: Groups and Resources.
However, there are other concepts that make up the overall design and this
section will cover them all in more detail.

**Registry**
An xRegistry instance, or a "Registry", can be thought of as a single rooted
tree of entities as shown in the "xRegistry Core Spec" diagram in the
[Overview](#overview) section. At the root is the Registry entity itself.
This entity is meant to serve a few key purposes:

  - Expose high-level metadata about the Registry itself, such as its creation
    and modified timestamps, name, link to additional documentation, etc.
  - The set of [capabilities](#registry-capabilities) (features) that are
    supported. For example, does this Registry support filtering of query
    results?
  - The domain-specific ["model"](#registry-model) that defines the types of
    entities being managed by the Registry. For example, the model might
    define a Group called `schemagroups` that has `schemas` as the Resources
    within those Groups.

**Groups**
Traversing down the tree structure, below the Registry entity, there will be
a (potentially empty) set of Groups for the entities managed by the Registry.
Each Group is meant to be a logical grouping of related Resources, much like a
directory acts as a grouping of "files". Groups, like the Registry entity,
does have similar high-level metadata that can be set and can have
domain-specific extension attributes defined.

It's worth noting that a Registry is not mandated to have any Groups. It is
permissible to have a Registry with just its top-level metadata, if that's all
that's needed for a particular use case.

As hinted at with the "directory" analogy, a common use for Groups will be
for them to be light-weight collections without much additional semantics
associated with them. However, this is not a requirement. Because Groups
allow for user-defined extension attributes to be defined, Groups might be
quite rich with respect to managing domain-specific data. See the
[Endpoint](../endpoint/spec.md) as an example.

**Resources**
Below, or within, each Group will be a (potentially empty) set of Resources.
Typically, Resources are the main pieces of data managed by the Registry. Like
the Registry and Group entities that have a set of xRegistry defined "common"
metadata that can be set, and user-defined extension attributes can be defined.
However, Resources also support the concept of a domain-specific "document"
that can be associated with it. This document can be stored within the
Registry itself (like another attribute on the Resource), or stored external
to the Registry and a URL to the document will be stored within the xRegistry
metadata. This allows for the definition of the model to support cases where
domain-specific data needs to be managed, and exposed, as xRegistry metadata
or the data needs to be completely separate from the Registry's metadata.

Typically, the domain-specific document will be used when a pre-existing
document definition already exists and an xRegistry is used as the
mechanism to expose those documents in a consistent and interoperable way.
For example, the [Schema Registry](../schema/spec.md) only has a few
xRegistry Resource extension attributes defined because most of the data of
interest will be in the Schema Documents associated with the Resources.

**Versions**
While "Resources" are presented as the most significant entities within
a Registry, technically Resources themselves are very light-weight entities
and are there to act as a grouping mechanism for another entity: Versions.

Often, as Resources change over time, it is desirable to maintain a
historical set of instances (i.e. "versions") of those Resources so they
can be referenced and accessed as independent (but related) pieces of
data. Each Version of a Resource will have its own set of xRegistry
metadata and instance of the domain-specific "document".

However, while each Version is independently accessible, the Resource itself
has the concept of a "default Version" for which the Resource will act as
a proxy (or alias). Meaning, accessing the Resource (or its document) will
actually access one of its Versions. This allows end-users to
not be concerned with keeping track of which Version is the "default" one as
Versions are added or removed. This is sometimes configured to be the "newest"
Version, however, xRegistry does not mandate that the "default" Version always
be the "newest".

While not a requirement, the collection of Versions within a Resource
typically form a directed graph with respect to how they are related.
Meaning, a Version is usually "derived" from another Version known as its
"ancestor". For example, "version 2" might have "version 1" as its
"ancestor". By default, xRegistry assumes that each new Version will have
the current "newest" Version as its ancestor, but this is configurable.
See the [Version Mode](#--model-groupsstringresourcesstringversionmode) section
for more information.

**Next Steps**
In summary, the xRegistry design itself is relatively simple and consists
of 4 main concepts to form a tree of entities. However, with these, along
with the extensibility of the xRegistry metadata model, a wide range of
metadata can be categorized, managed, and exposed, in a consistent way, thus
allowing for a dynamically discoverable, yet interoperable, programmatic access
to what might otherwise be a domain-specific set of APIs.

The following sections will define the technical details of those xRegistry
entities and the APIs to access them.

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
will be used to indicate whether the serialization of the entity in a response
is meant for use as a stand-alone document or as part of a REST API message
exchange. The most notable differences are that in document view:

- References (e.g. URLs) between entities within responses will use relative
  references rather than absolute ones. This is an indication to tooling that
  the entity in question can be found within the current document and does not
  need an additional HTTP `GET` to retrieve it.
- Duplicate data will be removed. In particular, Resources will not include
  attributes from the "default" Version as part of their serialization. This is
  done with the assumption the nested `versions` collection will most likely
  include the "default" Version, so duplicating that information is redundant.

Most of these differences are to make it easier for tooling to use the
"stand-alone" document view of the Registry. For a complete list of the
differences in "document view" see the [Doc Flag](#doc-flag) flag and the
[Exporting](#exporting) sections.

Note that "document view" only refers to response messages. There is no
"document view" concept for requests. However, "document view" responses
are designed such that they can be used in request messages as they still
convey the same information as an "API view" response.

One final note, if the processing of a request fails then an error MUST be
generated and the entire request MUST be undone. See the
[Error Processing](#error-processing) section for more information.

### Implementation Customizations

This specification only defines the core APIs, and their semantics, of a
Registry service. It does not address many of the details that would need to
be added for a live instance of a service; as often times these aspects are
very specific to the environment in which the service is running. For example,
this specification does not address authentication or authorization levels of
users, nor how to securely protect the APIs (aside from the implied use of
`https`), clients or servers from attacks. Implementations of this
specification are expected to add these various features as needed.

Additionally, implementations MAY choose to customize the data and behavior on
a per-user basis as needed. For example, the following customizations might be
implemented:
- User-specific capabilities - e.g. admin users might see more features than
  a non-admin user.
- User-specific attribute aspects - e.g. admin users might be able to
  edit a `readonly` Resource. Note that in this case the Resource's `readonly`
  aspect will likely appear with a value of `true` even for the admin.

The goal of these customizations is not to allow for implementations to
violate the specification, rather it is to allow for real-world requirements
to be met while maintaining the interoperability goals of the specification.

Implementations are encouraged to contact the xRegistry community if it is
unclear if certain customizations would violate the specification.

### Attributes and Extensions

Unless otherwise noted, all attributes and extensions MUST be mutable and MUST
be one of the following data types:
- `any` - an attribute of this type is one whose type is not known in advance
   and MUST be one of the concrete types listed here.
- `array` - an ordered list of values that are all of the same data type - one
   of the types listed here.
   - Some serializations, such as JSON, allow for a `null` type of value to
     appear in an array (e.g. `[ null, 2, 3 ]` in an array of integers). In
     these cases, while it is valid for the serialization being used, it is
     not valid for xRegistry since `null` is not a valid `integer`. Meaning,
     the serialization of an array that is syntactically valid for the
     format being used, but not semantically valid per the xRegistry model
     definition MUST NOT be accepted and MUST generate an error
     ([invalid_data](#invalid_data)).
- `boolean` - case-sensitive `true` or `false`.
- `decimal` - number (integer or floating point).
- `integer` - signed integer.
- `map` - set of key/value pairs, where the key MUST be of type string. The
   value MUST be of one of the types defined here.
  - Each key MUST be a non-empty string consisting of only lowercase
    alphanumeric characters (`[a-z0-9]`), `:`, `-`, `_` or a `.`; be no longer
    than 63 characters; start with an alphanumeric character and be unique
    within the scope of this map.
  - See [Serializing Resource Documents](#serializing-resource-documents)
    for more information about serializing maps as HTTP headers.
- `object` - a nested entity made up of a set of attributes of these data
  types.
- `xid` - MUST be a URL (xid) reference to another entity defined within
  the Registry. The actual entity attribute value MAY reference a non-existing
  entity (i.e. dangling pointer), but the syntax MUST reference a
  defined/valid type in the Registry. This type of attribute is used in
  place of `url` so that the Registry can do "type checking" to ensure the
  value references the correct type of Registry entity. See the definition of
  the [`target` model attribute](#--model-attributesstringtarget) for more
  information.  Its value MUST start with a `/`.
- `xidtype` - MUST be a URL reference to an xRegistry model type. The
   reference MUST point to one of: the Registry itself (`/`), a Group type
   (`/<GROUPS>`), a Resource type (`/<GROUPS>/<RESOURCE>`) or Version type for
   a Resource (`/<GROUPS>/<RESOURCES>/versions`). Its value MUST reference a
   defined/valid type in the Registry.
- `string` - sequence of Unicode characters.
- `timestamp` - an [RFC3339](https://tools.ietf.org/html/rfc3339) timestamp.
  Use of a `time-zone` notation is RECOMMENDED. All timestamps returned by
  a server MUST be normalized to UTC to allow for easy (and consistent)
  comparisons.
- `uinteger` - unsigned integer.
- `uri` - a URI as defined in [RFC 3986](https://tools.ietf.org/html/rfc3986).
   Note that it can be absolute or relative.
- `uriabsolute` - absolute URI as defined in [RFC 3986 Section
  4.3](https://tools.ietf.org/html/rfc3986#section-4.3).
- `urirelative` - relative URI as defined in [RFC 3986 Section
  4.2](https://tools.ietf.org/html/rfc3986#section-4.2).
- `uritemplate` - URI Template as defined in
  [RFC 6570 Section 3.2.1](https://tools.ietf.org/html/rfc6570#section-3.2.1).
- `url` - an absolute URL (`urlabsolute`) or relative URL (`urlrelative`).
- `urlabsolute` - an absolute URI as defined in [RFC 3986 Section
  4.3](https://datatracker.ietf.org/doc/html/rfc3986#section-4.3) with the
  added "URL" constraints mentioned in [RFC 3986 Section
  1.1.3](https://datatracker.ietf.org/doc/html/rfc3986#section-1.1.3).
- `urlrelative` - a relative URI as defined in [RFC 3986 Section
  4.2](https://datatracker.ietf.org/doc/html/rfc3986#section-4.2) with the
  added "URL" constraints mentioned in [RFC 3986 Section
  1.1.3](https://datatracker.ietf.org/doc/html/rfc3986#section-1.1.3).

The 6 variants of URI/URL are provided to allow for strict type adherence
when needed. However, for attributes that are simply "pointers" that might
in practice be any of those 6 types, it is RECOMMENDED that `uri` be used.

Attributes that are defined to be relative URIs or URLs MUST state what they
are relative to and any constraints on their values, if any.

The root path of a Registry service MAY be at the root of a host or have a
`PATH` portion in its URL (e.g. `http://example.com/myregistry`).

The "scalar" data types are: `boolean`, `decimal`, `integer`, `string`,
`timestamp`, `uinteger`, `uri`, `uriabsolute`, `urirelative`, `uritemplate`,
`url`, `urlabsolute`, `urlrelative`, `xid`, `xidtype`.
Note that `any` is not a "scalar" type as its runtime value could be a complex
type such as `object`.

All attributes (specification-defined and extensions) MUST adhere to the
following rules:
- Their names MUST be between 1 and 63 characters in length.
- Their names MUST only contain lowercase alphanumeric characters or an
  underscore (`[a-z0-9_]`) and MUST NOT start with a digit (`[0-9]`).
- For string attributes, an empty string is a valid value and MUST NOT be
  treated the same as an attribute with no value (or absence of the attribute).
- For scalar attributes, the string serialization of the attribute name and
  its value MUST NOT exceed 4096 bytes. This is to ensure that it can appear
  in an HTTP header without exceeding implementation limits (see
  [RFC6265/Limits](https://datatracker.ietf.org/doc/html/rfc6265#section-6.1)).
  In cases where larger amounts of data are needed, it is RECOMMENDED that
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
- Attribute instances that have no value (and have no default value defined)
  are semantically equivalent to having a value of `null` or not being present
  at all, and for the sake of brevity, SHOULD NOT be serialized as part of its
  owning entity in server responses. Likewise, specifying them with a value of
  `null` in client requests SHOULD be reserved for cases where the client
  needs to indicate a request to delete an attribute value (`null` in the
  request) rather than to leave the attribute untouched (absent in the
  request), such as when `PATCH` is used.

Implementations of this specification MAY define additional (extension)
attributes. However, they MUST adhere to the following rules:

- All attributes MUST conform to the model definition of the Registry. This
  means that they MUST satisfy at least one of the following:
  - Be explicitly defined (by name) as part of the model.
  - Be permitted due to the presence of the `*` (undefined) extension attribute
    name at that level in the model.
  - Be permitted due to the presence of an `any` type for one of its parent
    attribute definitions.
- They MUST NOT conflict with the name of an attribute defined by this
  specification, including the `<RESOURCE>*` and `<COLLECTION>*` attributes
  that are implicitly defined. Note that if a Resource type has the
  `hasdocument` attribute set the `false` then this rule does not apply for
  the `<RESOURCE>*` attributes as those attributes are not used for that
  Resource type.
- It is RECOMMENDED that extension attributes on different entities do not
  use the same name unless they have the exact same semantic meaning.
- It is STRONGLY RECOMMENDED that they be named in such a way as to avoid
  potential conflicts with future xRegistry specification-defined attributes.
  For example, use of a model (or domain) specific prefix could be used to help
  avoid possible future conflicts.

#### Common Attributes

The following attributes are used by one or more entities defined by this
specification. They are defined here once rather than repeating them
throughout the specification.

For easy reference, the JSON serialization of these attributes adheres to this
form:
- `"<SINGULAR>id": "<STRING>"`
- `"self": "<URL>"`
- `"shortself": "<URL>"`
- `"xid": "<XID>"`
- `"epoch": <UINTEGER>`
- `"name": "<STRING>"`
- `"description": "<STRING>"`
- `"documentation": "<URL>"`
- `"icon": "<URL>"`
- `"labels": { "<STRING>": "<STRING>" * }`
- `"createdat": "<TIMESTAMP>"`
- `"modifiedat": "<TIMESTAMP>"`

The definition of each attribute is defined below:

##### `<SINGULAR>id` (`id`) Attribute

- Type: String
- Description: An immutable unique identifier of the Registry, Group, Resource
  or Version. The actual name of this attribute will vary based on the entity
  it identifies. For example, a `schema` Resource would use an attribute name
  of `schemaid`. This attribute MUST be named `registryid` for the Registry
  itself, and MUST be named `versionid` for all Version entities.

- Constraints:
  - REQUIRED.
  - MUST be immutable.
  - MUST be a non-empty string consisting of [RFC3986 `unreserved`
    characters](https://datatracker.ietf.org/doc/html/rfc3986#section-2.3)
    (ALPHA / DIGIT / `-` / `.` / `_` / `~`), `:` and `@`, MUST start with
    ALPHA, DIGIT or `_` and MUST be between 1 and 128 characters in length.
  - MUST be case-insensitive and unique within the scope of the entity's
    parent.
  - This attribute MUST be treated as case-sensitive for look-up purposes.
    This means that an HTTP request to an entity with the wrong case for its
    `<SINGULAR>id` MUST be treated as "not found".
  - In cases where an entity's `<SINGULAR>id` is specified outside of the
    serialization of the entity (e.g. part of a request URL, or a map key), its
    presence within the serialization of the entity is OPTIONAL. However, if
    present, it MUST be the same as any other specification of the
    `<SINGULAR>id` outside of the entity, and it MUST be the same as the
    entity's existing `<SINGULAR>id` if one exists, otherwise an error
    ([mismatched_id](#mismatched_id)) MUST be generated.

- Examples:
  - `a183e0a9-abf8-4763-99bc-e6b7fcc9544b`
  - `myEntity`
  - `myEntity.example.com`

While `<SINGULAR>id` can be something like a UUID, when possible, it is
RECOMMENDED that it be something human friendly as these values will often
appear in user-facing situations such as URLs or as command-line parameters.
In cases where [`name`](#name-attribute) is absent, the `<SINGULAR>id` might
be used as the display name.

Note, since `<SINGULAR>id` is immutable, in order to change its value, a new
entity would need to be created with the new `<SINGULAR>id` that is a deep-copy
of the existing entity. Then the existing entity would be deleted.

##### `self` Attribute

- Type: URL
- Description: A server-generated unique URL referencing the current entity.
  - Each entity in the Registry MUST have a unique `self` URL value that
    locates the entity in the Registry hierarchy and from where the entity can
    be retrieved.
  - When specified as an absolute URL, it MUST be based on the URL of the
    Registry root appended with the hierarchy path of the Registry
    entities/collections leading to the entity (its `xid` value).

    In the case of pointing to an entity that has a `<SINGULAR>id` attribute,
    the URL MUST be a combination of the URL used to retrieve its parent
    appended with its `<SINGULAR>id` value.

- API View Constraints:
  - REQUIRED.
  - MUST be immutable.
  - MUST be a non-empty absolute URL based on the URL of the Registry.
  - When serializing Resources or Versions, if the `hasdocument` aspect is set
    to `true`, then this URL MUST include the `$details` suffix to its
    `<SINGULAR>id` if it is serialized in the HTTP body response. If the aspect
    is set to `false`, then this URL's `<SINGULAR>id` MUST NOT include it.
  - MUST be a read-only attribute.

- Document View Constraints:
  - REQUIRED.
  - MUST be immutable.
  - MUST be a relative URL of the form `#JSON-POINTER` where the `JSON-POINTER`
    locates this entity within the current document. See [Doc Flag](#doc-flag)
    for more information.
  - This URL MUST NOT include the `$details` suffix after its `<SINGULAR>id`.

- Examples:
  - `https://example.com/registry/endpoints/ep1` (API View)
  - `#/endpoints/ep1` (Document View)

##### `shortself` Attribute

- Type: URL
- Description: A server-generated unique absolute URL for an entity. This
  attribute MUST be an alternative URL for the owning entity's `self`
  attribute. The intention is that `shortself` SHOULD be shorter in length
  than `self` such that it MAY be used when the length of the URL referencing
  the owning entity is important. For example, in cases where the size of a
  message needs to be as small as possible.

  This specification makes no statement as to how this URL is constructed,
  to which host/path it references, or whether a request to this URL
  will directly perform the desired operation or whether it returns a
  redirect to the full `self` URL requiring the client to resend the request.

  If an entity is deleted and then a new entity is created that results in
  the same `self` URL, this specification does not mandate that the same
  `shorturl` be generated, but it MAY do so.

  This attribute MUST only appear in the serialization if the `shortself`
  capability is enabled. However, if this capability is enabled, then disabled,
  and then re-enabled, the `shortself` values MUST retain their original
  values. In this sense, implementations might create a `shortself` that is
  known for the lifetime of the entity and the capability controls whether
  the attribute is serialized or not.

- Constraints:
  - REQUIRED if the `shortself` capability is enabled.
  - MUST be immutable for the lifetime of the entity.
  - MUST NOT appear in responses if the `shortself` capability is disabled.
  - MUST be unique across all entities in the Registry.
  - MUST be a non-empty absolute URL referencing the same entity as the `self`
    URL, either directly or indirectly via an HTTP redirect.
  - MUST be a read-only attribute.

- Examples:
  - `https://tinyurl.com/xreg123` redirects to
    `https://example.com/endpoints/e1`

##### `xid` Attribute

- Type: XID
- Description: An immutable server-generated unique identifier of the entity.
  Unlike `<SINGULAR>id`, which is unique within the scope of its parent, `xid`
  MUST be unique across the entire Registry, and as such is defined to be a
  relative URL from the root of the Registry. This value MUST be the same as
  the `<PATH>` portion of its `self` URL, after the Registry's base URL, without
  any `$` suffix (e.g. `$details`). Unlike some other relative URIs, `xid`
  values MUST NOT be shortened based on the incoming request's URL; `xid`s
  are always relative to the root path of the Registry.

  This attribute is provided as a convenience for users who need a reference
  to the entity without running the risk of incorrectly extracting it from
  the `self` URL, which might be ambiguous at times. The `xid` value is also
  meant to be used as a `xref` value (see [Cross Referencing
  Resources](#cross-referencing-resources), or as the value for attributes of
  type `xid` (see [`target` model attribute](#--model-attributesstringtarget)).

- Constraints:
  - REQUIRED.
  - MUST be immutable.
  - MUST be a non-empty relative URL to the current entity.
  - MUST be of the form:
    `/[<GROUPS>/<GID>[/<RESOURCES>/<RID>[/meta | /versions/<VID>]]]`.
  - MUST start with the `/` character.
  - MUST be a read-only attribute.

- Examples:
  - `/endpoints/ep1`

##### `epoch` Attribute

- Type: Unsigned Integer
- Description: A numeric value used to determine whether an entity has been
  modified. Each time the associated entity is updated, this value MUST be
  set to a new value that is greater than the current one. This attribute
  MUST be updated for every update operation, even if no attributes were
  explicitly updated, such as a `PATCH` with no attributes. This then acts
  like a `touch` type of operation.

  During a single write operation, whether this value is incremented for
  each modified attribute of the entity, or updated just once for the entire
  operation is an implementation choice.

  During a create operation, if this attribute is present in the request, then
  it MUST be silently ignored by the server.

  During an update operation, if this attribute is present in the request, then
  an error ([mismatched_epoch](#mismatched_epoch)) MUST be generated if the
  request includes a non-null value that differs from the existing value.
  This allows for the detection of concurrent, but conflicting, updates to the
  same entity to be detected. A value of `null` MUST be treated the same as a
  request with no `epoch` attribute at all, in which case a check MUST NOT
  be performed.

  If an entity has a nested xRegistry collection, its `epoch` value MUST
  be updated each time an entity in that collection is added or removed.
  However, its `epoch` value MUST NOT be updated solely due to modifications of
  an existing entity in the collection.

- Constraints:
  - REQUIRED.
  - MUST be a read-only attribute.
  - MUST be an unsigned integer equal to or greater than zero.
  - MUST increase in value each time the entity is updated.

- Examples:
  - `0`, `1`, `2`, `3`

##### `name` Attribute

- Type: String
- Description: A human-readable name of the entity. This is often used
  as the "display name" for an entity rather than the `<SINGULAR>id` especially
  when the `<SINGULAR>id` might be something that isn't human friendly, like a
  UUID. In cases where `name` is absent, the `<SINGULAR>id` value SHOULD be
  displayed in its place.

  This specification places no uniqueness constraints on this attribute.
  This means that two sibling entities MAY have the same value. Therefore,
  this value MUST NOT be used for unique identification purposes, the
  `<SINGULAR>id` MUST be used instead.

  Note that implementations MAY choose to enforce additional constraints on
  this value. For example, they could mandate that `<SINGULAR>id` and `name` be
  the same value. Or, it could mandate that `name` be unique within the scope
  of a parent entity. How any such requirement is shared with all parties is
  out of scope of this specification.

- Constraints:
  - OPTIONAL.
  - If present, MUST be non-empty.

- Examples:
  - `My Cool Endpoint`

##### `description` Attribute

- Type: String
- Description: A human-readable summary of the purpose of the entity.

- Constraints:
  - OPTIONAL.

- Examples:
  - `A queue of the sensor-generated messages`

##### `documentation` Attribute

- Type: URL
- Description: A URL to additional information about this entity.
  This specification does not place any constraints on the data returned from
  an HTTP `GET` to this URL.

- Constraints:
  - OPTIONAL.
  - If present, MUST be a non-empty URL.
  - MUST support an HTTP(s) `GET` to this URL.

- Examples:
  - `https://example.com/docs/myQueue`

##### `icon` Attribute

- Type: URL
- Description: A URL to a graphical icon for the owning entity.

- Constraints:
  - OPTIONAL.
  - If present, MUST be a non-empty URL.
  - MUST support an HTTP(s) `GET` to this URL.
  - STRONGLY RECOMMENDED that the icon be in SVG or PNG format and square.

- Examples:
  - `https://example.com/myRegistry.svg`

##### `labels` Attribute

- Type: Map of name/value string pairs
- Description: A mechanism in which additional metadata about the entity can
  be stored without changing the model definition of the entity.

- Constraints:
  - OPTIONAL.
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
  semicolon(`;`) is used instead of colon(`:`). So, this might be something
  to consider when choosing to use labels that can be empty strings.

##### `createdat` Attribute

- Type: Timestamp
- Description: The date/time of when the entity was created.

- Constraints:
  - REQUIRED.
  - MUST be a [RFC3339](https://tools.ietf.org/html/rfc3339) timestamp.
  - This specification places no restrictions on the value of this attribute,
    nor on its value relative to its `modifiedat` value or the current
    date/time. Implementations MAY choose to restrict its values if necessary.
  - If present in a write operation request, the value MUST override any
    existing value, however a value of `null` MUST use the current date/time
    as the new value.
  - When absent in an update request, any existing value MUST remain
    unchanged, or if not already set, set to the current date/time.
  - During the processing of a single request, all entities that have their
    `createdat` or `modifiedat` attributes set to the current date/time MUST
    use the same value in all cases.

- Examples:
  - `2030-12-19T06:00:00Z`

##### `modifiedat` Attribute

- Type: Timestamp
- Description: The date/time of when the entity was last updated.

- Constraints:
  - REQUIRED.
  - MUST be a [RFC3339](https://tools.ietf.org/html/rfc3339) timestamp
    representing the time when the entity was last updated.
  - This specification places no restrictions on the value of this attribute,
    nor on its value relative to its `createdat` value or the current
    date/time. Implementations MAY choose to restrict its values if necessary.
  - Any update operation (even one that does not change any attribute, such as
    a `PATCH` with no attributes provided), MUST update this attribute. This
    then acts like a `touch` type of operation.
  - Updates to an existing entity in an xRegistry collection MUST NOT cause an
    update to its parent entity's `modifiedat` value. However, adding or
    removing an entity from a nested xRegistry collection MUST update the
    `modifiedat` value of the parent entity.
  - If present in a write operation request, the following applies:
    - If the request value is `null` or the same as the existing value, then
      the current date/time MUST be used as its new value.
    - If the request value is different than the existing value, then the
      request value MUST be used as its new value.
  - When absent in a write operation request, it MUST be set to the current
    date/time.
  - During the processing of a single request, all entities that have their
    `createdat` or `modifiedat` attributes set to the current date/time MUST
    use the same value in all cases.

- Examples:
  - `2030-12-19T06:00:00Z`

---

### Registry HTTP APIs

This specification defines the following API patterns:

```yaml
/                                                # Access the Registry
/capabilities                                    # Access available features
/model                                           # Access full model definitions
/modelsource                                     # Access model customizations
/export                                          # Retrieve Registry as a doc
/<GROUPS>                                        # Access a Group Type
/<GROUPS>/<GID>                                  # Access a Group
/<GROUPS>/<GID>/<RESOURCES>                      # Access a Resource Type
/<GROUPS>/<GID>/<RESOURCES>/<RID>                # Default Version of Resource
/<GROUPS>/<GID>/<RESOURCES>/<RID>/meta           # Access a Resource's metadata
/<GROUPS>/<GID>/<RESOURCES>/<RID>/versions       # Versions of a Resource
/<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID> # Access Version of Resource
```

While these APIs are shown to be at the root path of a host,
implementations MAY choose to prefix them as necessary. However, the same
prefix MUST be used consistently for all APIs in the same Registry instance.

Support for any particular API defined by this specification is OPTIONAL,
however, it is STRONGLY RECOMMENDED that server-side implementations support at
least the "read" (e.g. HTTP `GET`) operations. Implementations MAY choose to
incorporate authentication and/or authorization mechanisms for the APIs.

If an OPTIONAL HTTP path is not supported by an implementation, then any
use of that API MUST generate an error ([api_not_found](#api_not_found)).

If an HTTP method is not supported for a supported HTTP path, then an error
([method_not_allowed](#method_not_allowed)) MUST be generated.

Implementations MAY support extension APIs, however, the following rules MUST
apply:
- New HTTP paths that extend non-root paths MUST NOT be defined.
- New root HTTP paths MAY be defined as long as they do not use Registry-level
  HTTP paths or attribute names. This includes extension and Groups collection
  attribute names.
- Additional HTTP methods for specification-defined HTTP paths MUST NOT be
  defined.

For example, a new API with an HTTP path of `/my-api` is allowed, but APIs with
`/model/my-api` or `/name` HTTP paths are not.

This specification leans on the
[RFC9110 HTTP Semantics model](https://www.rfc-editor.org/rfc/rfc9110.html)
with the
[RFC5789 PATCH extension](https://www.rfc-editor.org/rfc/rfc5789.html).
The following key aspects are called out to help understand the overall
pattern of the APIs:
- A `PUT` or `POST` operation is a full replacement of the entities
  processed. Any missing attributes MUST be interpreted as a request for them
  to be deleted. However, attributes that are managed by the server might have
  specialized processing in those cases, in particular, mandatory attributes
  as well as ones that have default values defined, MUST be reset to their
  default values rather than deleted.
- A `PATCH` operation MUST only modify the attributes explicitly mentioned
  in the request. Any attribute with a value of `null` MUST be interpreted
  as a request to delete the attribute, and as with `PUT`/`POST`, server
  managed attributes might have specialized processing.
- `PUT` MUST NOT be targeted at xRegistry collections. A `POST` or `PATCH`
  MUST be used instead to add entities to the collection, and a
  `DELETE` MUST be used to delete unwanted entities.
- `POST` operations MUST only be targeted at xRegistry collections, not
  individual entities - with the exception of a Resource entity. In that case
  a `POST` to a Resource URL MUST be treated as an alias for a `POST` to the
  Resource's `versions` collection.
- Unknown query parameters SHOULD be silently ignored by servers. This
  includes specification-defined but unsupported query parameters.
- Despite the
  [HTTP specification](https://datatracker.ietf.org/doc/html/rfc9110#name-idempotent-methods)
  saying that the `PUT` method is idempotent, this specification does not
  adhere to that rule when it comes to the `epoch` and `modifiedat` attributes.
  While multiple identical `PUT` requests will yield the same semantic effect
  as single `PUT` for all other attributes, the `epoch` and `modifiedat`
  attributes are designed to always be updated on each write operation to that
  entity.

In general, if a server is unable to retrieve all of the data intended to be
sent in a response, then an error
([data_retrieval_error](#data_retrieval_error)) MUST be generated and the
request rejected without any changes being made. However, it is permissible
for a server to attempt some creative processing. For example, if while
processing a `GET` the server can only retrieve half of the entities to be
returned at the current point in time, then it could return those with an
indication of there being more (via the [pagination
specification](../pagination/spec.md)). Then during the next `GET` request it
could return the remainder of the data - or an error if it is still not
available. Note that if an entity is to be sent, then it MUST be serialized in
its entirety (all attributes, and requested child entities) or an error MUST
be generated.

There might be situations where someone will do a `GET` to retrieve data
from a Registry, and then do an update operation to a Registry with that data.
Depending on the use case, they might not want some of the retrieved data
to be applied during the update - for example, they might not want the
`epoch` validation checking to occur. Rather than forcing the user to edit
the data to remove the potentially problematic attributes, the following
query parameters MAY be included on write operations to control certain
aspects of the processing:
- `?ignoreepoch` - presence of this query parameter indicates that any `epoch`
  attribute included in the request MUST be ignored.
- `?ignoredefaultversionid` - presence of this query parameter indicates that
  any `defaultversionid` attribute included in the request MUST be ignored.
- `?ignoredefaultversionsticky` - presence of this query parameter indicates
  that any `defaultversionsticky` attribute included in the request MUST be
  ignored.
- `?ignorereadonly` - presence of this query parameter indicates that any
  attempt to update a read-only Resource MUST be silently ignored.

Any JSON xRegistry metadata message that represents a single entity (i.e. not
a map) MAY include a top-level "$schema" attribute that points to a JSON Schema
document that describes the message contents. These notations can be used or
ignored by receivers of these messages. There is no requirement for
implementations of this specification to persist these values, to include them
in responses or to use this information.

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
such that all of the APIs are OPTIONAL, and all of the query parameters are
OPTIONAL (typically specified by saying that they `SHOULD` be supported).
However, it is STRONGLY RECOMMENDED that full API servers support the query
parameters when possible to enable a better user experience, and increase
interoperability.

Note that simple file servers SHOULD support exposing Resources where the HTTP
body response contains the Resource's associated "document" as well as the
case where the HTTP response body contains a JSON serialization of the
Resource via the `$details` suffix on the URL path. This can be achieved by
creating a secondary sibling file on disk with `$details` at the end of its
filename.

---

The remainder of this specification mainly focuses on the successful
interaction patterns of the APIs. For example, most examples will show an
HTTP "200 OK" as the response. Each implementation MAY choose to return a more
appropriate response based on the specific situation. For example, in the case
of an authentication error the server could return `401 Unauthorized`.

The following sections define the APIs in more detail.

---

#### Registry Collections

Registry collections (`<GROUPS>`, `<RESOURCES>` and `versions`) that are
defined by the [Registry Model](#registry-model) MUST be serialized according
to the rules defined below.

The serialization of a collection is done as 3 attributes and they MUST adhere
to their respective forms as follows:

```yaml
"<COLLECTION>url": "<URL>",
"<COLLECTION>count": <UINTEGER>,
"<COLLECTION>": {
  # Map of entities in the collection, key is the "<SINGULAR>id" of the entity
}
```

Where:
- The term `<COLLECTION>` MUST be the plural name of the collection
  (e.g. `endpoints`, `versions`).
- The `<COLLECTION>url` attribute MUST be a URL that can be used to retrieve
  the `<COLLECTION>` map via an HTTP(s) `GET` (including any necessary
  [filtering](#filter-flag)) and MUST be a read-only attribute that MUST
  be silently ignored by a server during a write operation. An empty
  collection MUST return an HTTP 200 with an empty map (`{}`). This attribute
  MUST be an absolute URL except in document view and the collection
  is inlined, in which case it MUST be a relative URL.
- The `<COLLECTION>count` attribute MUST contain the number of entities in the
  `<COLLECTION>` map (after any necessary [filtering](#filter-flag)) and MUST
  be a read-only attribute that MUST be silently ignored by a server during
  a write operation.
- The `<COLLECTION>` attribute is a map and MUST contain the entities of the
  collection (after any necessary [filtering](#filter-flag)), and MUST use
  the `<SINGULAR>id` of each entity as its map key.
- The key of each entity in the collection MUST be unique within the scope of
  the collection.
- The specifics of whether each `<COLLECTION>*` attribute is REQUIRED or
  OPTIONAL will be based on whether the document- or API-view is used - see
  the next section.

When the `<COLLECTION>` attribute is expected to be present in the
serialization, but the number of entities in the collection is zero, it MUST
still be included as an empty map (e.g. `{}`).

The set of entities that are part of the `<COLLECTION>` attribute is a
point-in-time view of the Registry. There is no guarantee that a future `GET`
to the `<COLLECTION>url` will return the exact same collection since the
contents of the Registry might have changed. This specification makes no
statement as to whether a subsequent `GET` that is missing previously returned
entities is an indication of those entities being deleted or not.

Since collections could be too large to retrieve in a single request, when
retrieving a collection, the client MAY request a subset by using the
[pagination specification](../pagination/spec.md). Likewise, the server
MAY choose to return a subset of the collection using the same mechanism
defined in that specification even if the request didn't ask for pagination.
The pagination specification MUST only be used when the request is directed at
a collection, not at its owning entity (such as the root of the Registry,
or at an individual Group or Resource).

In the remainder of the specification, the presence of the `Link` HTTP header
indicates the use of the [pagination specification](../pagination/spec.md)
MAY be used for that API.

The requirements on the presence of the 3 `<COLLECTION>` attributes varies
between document and API views, and is defined below:

##### Collections in Document View

In document view:
- `<COLLECTION>url` and `<COLLECTION>count` are OPTIONAL.
- `<COLLECTION>` is conditional in responses based on the values in the
  [Inline Flag](#inline-flag). If a collection is part of the flag's value then
  `<COLLECTION>` MUST be present in the response even if it is empty
  (e.g. `{}`). If the collection is not part of the flag value then
  `<COLLECTION>` MUST NOT be included in the response.

##### Collections in API View

In API view:
- `<COLLECTION>url` is REQUIRED for responses even if there are no entities
  in the collection.
- `<COLLECTION>count` is STRONGLY RECOMMENDED for responses even if
  there are no entities in the collection. This requirement is not mandated
  to allow for cases where calculating the exact count is too costly.
- `<COLLECTION>url` and `<COLLECTION>count` are OPTIONAL in requests and MUST
  be silently ignored by the server if present.
- `<COLLECTION>` is conditional in responses based on the values in the
  [Inline Flag](#inline-flag). If a collection is part of the flag's value then
  `<COLLECTION>` MUST be present in the response even if it is empty
  (e.g. `{}`). If the collection is not part of the flag value then
  `<COLLECTION>` MUST NOT be included in the response.
- `<COLLECTION>` is OPTIONAL for requests. See [Updating Nested Registry
  Collections](#updating-nested-registry-collections) for more details.

##### Updating Nested Registry Collections

When updating an entity that can contain Registry collections, the request
MAY contain the 3 collection attributes. The `<COLLECTION>url` and
`<COLLECTION>count` attributes MUST be silently ignored by the server.

If the `<COLLECTION>` attribute is present, the server MUST process each entity
in the collection map as a request to create or update that entity according to
the semantics of the HTTP method used. An entry in the map that isn't a valid
entity (e.g. is `null`) MUST generate an error ([bad_request](#bad_request)).

For example:

```yaml
PUT https://example.com/endpoints/ep1

{
  "endpointid": "ep1",
  "name": "A cool endpoint",

  "messages": {
    "mymsg1": { ... },
    "mymsg2:" { ... }
  }
}
```

will not only create/update an `endpoint` Group with an `endpointid` of `ep1`
but will also create/update its `message` Resources (`mymsg1` and `mymsg2`).

Any error while processing a nested collection entity MUST result in the entire
request being rejected.

An absent `<COLLECTION>` attribute MUST be interpreted as a request to not
modify the collection at all.

If a client wishes to delete an entity from the collection, or replace the
entire collection, the client MUST use one of the `DELETE` operations on the
collection. This means that delete operations on these entities would need
to be handled in dedicated operations.

In cases where an update operation includes attributes meant to be applied
to the "default" Version of a Resource, and the incoming inlined `versions`
collections includes that "default" Version, the Resource's default Version
attributes MUST be silently ignored. This is to avoid any possible conflicting
data between the two sets of data for that Version. In other words, the
Version attributes in the incoming `versions` collection wins.

To better understand this scenario, consider the following HTTP request to
update a Message where the `defaultversionid` is `v1`:

```yaml
PUT http://example.com/endpoints/ep1/messages/msg1

{
  "messageid": "msg1",
  "versionid": "v1",
  "name": "Blob Created"

  "versions": {
    "v1": {
      "messageid": "msg1",
      "versionid": "v1",
      "name": "Blob Created Message Definition"
    }
  }
}
```

If the `versions` collection were not present with the `v1` entity then the
top-level attributes would be used to update the default Version (`v1` in this
case). However, because it is present, the request to update `v1` becomes
ambiguous because it is not clear if the server is meant to use the top-level
attributes or if it is to use the attributes under the `v1` entity of the
`versions` collection. When both sets of attributes are the same, then it does
not matter. However, in these cases, the `name` attributes have different
values. The paragraph above mandates that in these potentially ambiguous cases
the entity in the `versions` collection is to be used and the top-level
attributes are to be ignored - for the purposes of updating the "default"
Version's attributes. So, in this case the `name` of the default (`v1`)
Version will be `Blob Created Message Definition`.

---

#### Entity Processing Rules

Rather than repeating the processing rules for each type of xRegistry
entity or Registry collection, the overall pattern is defined once in this
section and any entity-, or collection-specific rules will be detailed in the
appropriate section in the specification.

##### Creating or Updating Entities
This defines the general rules for how to update entities.

Creating or updating entities MAY be done using HTTP `PUT`, `PATCH` or `POST`
methods:
- `PUT    <PATH-TO-ENTITY>[?<OPTIONS>`]          # Process a single entity
- `PATCH  <PATH-TO-ENTITY>[?<OPTIONS>`]          # Process a single entity
- `PATCH  <PATH-TO-COLLECTION>[?<OPTIONS>`]      # Process a set of entities
- `POST   <PATH-TO-COLLECTION>[?<OPTIONS>`]      # Process a set of entities

Based on the entity being processed, the `<OPTIONS>` available will vary.

The `PUT` variant MUST adhere to the following:
  - The URL MUST be of the form: `<PATH-TO-ENTITY>`.
  - The HTTP body MUST contain the full updated serialization of the entity to
    be processed.
  - The entity processed MUST either be created (if it does not already
    exist), or updated (if it does exist).
  - Any mutable attribute which is either missing or present with a value of
    `null`, MUST be interpreted as a request to delete the attribute.
  - Excluding any Registry collection attributes, all mutable attributes
    specified MUST be a full serialization of the attribute. Any missing
    nested attribute MUST be interpreted as a request to delete the attribute.
  - After processing the request, if there are any missing REQUIRED attributes
    then an error ([required_attribute_missing](#required_attribute_missing))
    MUST be generated.

The `POST` variant MUST adhere to the following:
  - The HTTP body MUST contain a JSON map where the key MUST be the
    `<SINGULAR>id` of each entity in the map. Note, that in the case of a map
    of Versions, the `versionid` is used.
  - Each value in the map MUST be the full serialization of the entity to be
    either added or updated. Note that `POST` does not support deleting
    entities from a collection, so a separate delete operation might be needed
    if there are entities that need to be removed.
  - The processing of each individual entity in the map MUST follow the same
    rules as defined for `PUT` above.

The `PATCH` variant when directed at a single entity, MUST adhere to the `PUT`
semantics defined above with the following exceptions:
  - Any mutable attribute which is missing MUST be interpreted as a request to
    leave it unchanged. However, modifying some other attribute (or some other
    server semantics) MAY modify it. A value of `null` MUST be interpreted as
    a request to delete the attribute.
  - When processing a Resource or Version, that has its `hasdocument` model
    aspect set to `true`, the URL accessing the entity MUST include the
    `$details` suffix, and MUST generate an error
    ([details_required](#details_required)) in the absence of the
    `$details` suffix. This is because when it is absent, the processing of
    the HTTP `xRegistry-` headers are already defined with "PATCH" semantics
    so a normal `PUT` or `POST` can be used instead. Using `PATCH` in this
    case would mean that the request is also trying to "patch" the Resource's
    "document", which this specification does not support at this time.
  - `PATCH` MAY be used to create new entities, but as with any of the create
    operations, any missing REQUIRED attributes MUST generate an error
    ([required_attribute_missing](#required_attribute_missing)).

The `PATCH`, variant when directed at an xRegistry collection, MUST adhere to
the following:
  - The HTTP body MUST contain a JSON map where the key MUST be the
    `<SINGULAR>id` of each entity in the map. Note, that in the case of a map
    of Versions, the `versionid` is used instead.
  - Each value in the map MUST contain just the attributes that are to be
    updated for that entity.
  - The processing of each individual entity in the map MUST follow the same
    rules as defined for `PATCH` of a single entity above.

The processing of each individual entity follows the same set of rules:
- If an entity with the specified `<SINGULAR>id` already exists then it MUST be
  interpreted as a request to update the existing entity. Otherwise, it MUST
  be interpreted as a request to create a new entity with that `<SINGULAR>id`.
- See the definition of each attribute for the rules governing how it is
  processed.
- Unless otherwise noted, all non-xRegistry collection attributes present MUST
  be a full representation of their values. This means any complex attributes
  (e.g. objects, maps), MUST be fully replaced by the incoming value.
- A request to update, or delete, a read-only attribute MUST be silently
  ignored. However, a request that includes a `<SINGULAR>id` MUST be compared
  with the entity's current value and if it differs then an error
  ([mismatched_id](#mismatched_id)) MUST be generated. This includes both
  `<RESOURCE>id` and `versionid` in the case of Resources and Versions. This is
  to prevent accidentally updating the wrong entity.
- A request to update a mutable attribute with an invalid value MUST generate
  an error ([invalid_data](#invalid_data)) (this includes deleting a
  mandatory mutable attribute that has no default value defined).
- Registry collection attributes MUST be processed per the rules specified
  in the [Updating Nested Registry
  Collections](#updating-nested-registry-collections) section.
- Any error during the processing of an entity, or its nested entities, MUST
  result in the entire request being rejected and no updates performed.

A successful response MUST return the same response as a `GET` to the entity
(or entities) processed, showing their current representation, with the
following exceptions:
- In the `POST` case, or a `PATCH` directed to an xRegistry collection, the
  result MUST contain only the entities processed,
  not the entire Registry collection.
- In the `PUT` or `PATCH` cases that are directed to a single entity, for a
  newly created entity, the HTTP status MUST be `201 Created`, and it MUST
  include an HTTP `Location` header with a URL to the newly created entity.
  Note that this URL MUST be the same as the `self` attribute of that entity.

Otherwise an HTTP `200 OK` without an HTTP `Location` header MUST be returned.

Note that the response MUST be generated applying the semantics of any
query parameters specified on the request URL (e.g. `?inline`). If an error
occurs while generating the response (e.g. invalid `?filter`), then
an error MUST be generated and the entire operation MUST be undone.

##### Retrieving a Registry Collection

To retrieve a Registry collection, an HTTP `GET` MAY be used. The request
MUST be of the form:

```yaml
GET <PATH-TO-COLLECTION>
```

A successful response MUST be of the form:

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Link: <URL>;rel=next;count=<UINTEGER> ?

{
  "<KEY>": {                                         # <SINGULAR>id value
    "<SINGULAR>id": "<STRING>",
    ... remaining entity attributes ...
  } *
}
```

##### Retrieving an Entity from a Registry Collection

To retrieve an entity, an HTTP `GET` MAY be used. The request MUST be of the
form:

```yaml
GET <PATH-TO-COLLECTION>/<ID-OF-ENTITY>
```

A successful response MUST be of the form:

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "<SINGULAR>id": "<STRING>",
  ... remaining entity attributes ...
}
```

##### Deleting Entities in a Registry Collection

There are two ways to delete entities from a Registry collection:

1. to delete a single entity, an HTTP `DELETE` MAY be used. The request MUST
be of the form:

```yaml
DELETE <PATH-TO-COLLECTION>/<ID-OF-ENTITY>[?epoch=<UINTEGER>]
```

Where:
- The request body SHOULD be empty.
- If the entity cannot be found, then an error ([not_found](#not_found)) MUST
  be generated.
- In the case of deleting Resources, a `DELETE` directed to the `meta`
  sub-object is not supported and MUST generate an error
  ([method_not_allowed](#method_not_allowed)).

The following query parameter SHOULD be supported by servers:
- `epoch`<br>
  The presence of this query parameter indicates that the server MUST check
  to ensure that the `epoch` value matches the entity's current `epoch` value
  and if it differs then an error ([mismatched_epoch](#mismatched_epoch)) MUST
  be generated.

2. to delete multiple entities within a Registry collection, the request MUST
be in one of two forms:

For non-Resource entities:
```yaml
DELETE <PATH-TO-COLLECTION>

{
  "<KEY>": {                                          # <SINGULAR>id of entity
    "epoch": <UINTEGER> ?
  } *
} ?
```

or

For Resource entities (see below for more details):
```yaml
DELETE <PATH-TO-COLLECTION>

{
  "<KEY>": {                                          # <SINGULAR>id of entity
    "meta": {
      "epoch": <UINTEGER> ?
    } ?
  } *
} ?
```

Where:
- If the request body is empty (no map), then all entities in the collection
  MUST be deleted.
- If the request body is not empty, then it MUST be a map containing zero or
  more entries where the key of each entry is the `<SINGULAR>id` of the entity.
- When an `epoch` value is specified for an entity then the server MUST check
  to ensure that the value matches the entity's current `epoch` value and if it
  differs then an error ([mismatched_epoch](#mismatched_epoch)) MUST be
  generated.
- When deleting Resources, since the `epoch` attribute is located under the
  `meta` sub-object (and not as a top-level entity attribute), if included
  in the `DELETE` request, it MUST appear under a `meta` sub-object.
  Additionally, `DELETE` requests of Resources that only have `epoch` as a
  top-level attribute, but not as a `meta` attribute, MUST generate an error
  ([misplaced_epoch](#misplaced_epoch)) as it is likely that the client is
  using the Resource's default Version `epoch` value by mistake. A top-level
  `epoch` in the presence of a `meta` `epoch` MUST be silently ignored.
- If the entity's `<SINGULAR>id` is present in the object, then it MUST
  match its corresponding `<KEY>` value.
- Any other entity attributes that are present in the request MUST be silently
  ignored, even if their values are invalid.
- If one of the referenced entities cannot be found, then the server MUST
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

and the server MAY choose to return additional data in the HTTP body.

---

### Registry Root APIs

The Registry entity represents the root of a Registry and is the main
entry-point for traversal and discovery.

The serialization of the Registry entity adheres to this form:

```yaml
{
  "specversion": "<STRING>",
  "registryid": "<STRING>",
  "self": "<URL>",
  "shortself": "<URL>", ?
  "xid": "<XID>",
  "epoch": <UINTEGER>,
  "name": "<STRING>", ?
  "description": "<STRING>", ?
  "documentation": "<URL>", ?
  "icon": "<URL>", ?
  "labels": { "<STRING>": "<STRING>" * }, ?
  "createdat": "<TIMESTAMP>",
  "modifiedat": "<TIMESTAMP>",

  "capabilities": { Registry capabilities }, ?   # Only if inlined
  "model": { Registry model }, ?                 # Only if inlined
  "modelsource": { Registry model }, ?           # Only if inlined

  # Repeat for each Group type
  "<GROUPS>url": "<URL>",                        # e.g. "endpointsurl"
  "<GROUPS>count": <UINTEGER>,                   # e.g. "endpointscount"
  "<GROUPS>": { Groups collection } ?            # Only if inlined
}
```

The Registry entity includes the following
[common attributes](#common-attributes):
- [`registryid`](#singularid-id-attribute) - REQUIRED in API and document
  views. OPTIONAL in requests.
- [`self`](#self-attribute) - REQUIRED in API and document views.
  OPTIONAL/ignored in requests.
- [`shortself`](#shortself-attribute) - OPTIONAL in API and document views,
  based on the `shortself` capability. OPTIONAL/ignored in requests.
- [`xid`](#xid-attribute) - REQUIRED in API and document views.
  OPTIONAL/ignored in requests.
- [`epoch`](#epoch-attribute) - REQUIRED in API and document views. OPTIONAL
  in requests.
- [`name`](#name-attribute) - OPTIONAL.
- [`description`](#description-attribute) - OPTIONAL.
- [`documentation`](#documentation-attribute) - OPTIONAL.
- [`icon`](#icon-attribute) - OPTIONAL.
- [`labels`](#labels-attribute) - OPTIONAL.
- [`createdat`](#createdat-attribute) - REQUIRED in API and document views.
  OPTIONAL in requests.
- [`modifiedat`](#modifiedat-attribute) - REQUIRED in API and document views.
  OPTIONAL in requests.

and the following Registry-level attributes:

##### `specversion` Attribute
- Type: String.
- Description: The version of this specification that the document
  adheres to.

- Constraints:
  - REQUIRED.
  - MUST be a read-only attribute.
  - MUST be non-empty.

- Examples:
  - `1.0`

##### `model` Attribute
- Type: Registry Model.
- Description: A full description of the Groups, Resources and attributes
  (specification-defined and extensions) as defined by the current model
  associated with this Registry. See [Registry Model](#registry-model).

  This view of the model is useful for tooling that needs a complete view of
  what will be part of any message exchange with the server.

  Note that any ["include"](#includes-in-the-xregistry-model-data) directives
  that were included in the model definition MUST NOT be present in this
  view of the model.

- Constraints:
  - MUST NOT be included in API and document views unless requested.
  - MUST be included in API and document views if requested.
  - MUST be a read-only attribute.

##### `modelsource` Attribute
- Type: Registry Model
- Description: The "model" definition that was last used to define this
  Registry's model. Unlike `model`, which includes all aspects of the model,
  this is meant to represent just the customizations, or extensions, to the
  base xRegistry model as defined this specification. This allows for users to
  view (and edit) just the custom aspects of the model without the "noise" of
  the specification-defined parts.

  If the implementation supports modifying the model, then this attribute,
  or the `/modelsource` API are the mechanisms by which it MAY be done.

  The serialization of this attribute MUST be semantically equivalent to
  what was used to create the model, but it is NOT REQUIRED to be syntactically
  equivalent. In other words, it might be "pretty-printed", but it MUST NOT
  include additional aspects even if those are defined/mandated by the
  specification.

- Constraints:
  - MUST NOT be included in API and document views unless requested.
  - MUST be included in API and document views if requested.
  - MAY be mutable based on the capabilities of the implementation.

##### `<GROUPS>` Collections
- Type: Set of [Registry Collections](#registry-collections)
- Description: A list of Registry collections that contain the set of Groups
  supported by the Registry.

- Constraints:
  - REQUIRED.
  - It MUST include all nested Group Collection types in the
    Registry, even if some of the collections are empty.

#### Retrieving the Registry

To retrieve the Registry, its metadata attributes, and Groups, an HTTP `GET`
MAY be used.

The request MUST be of the form:

```yaml
GET /[?specversion=...]
```

The following query parameter SHOULD be supported by servers:
- `specversion`<br>
  The presence of this OPTIONAL query parameter indicates that the response
  MUST adhere to the xRegistry specification version specified
  (case-insensitive). If the version is not supported, then an error
  ([unsupported_specversion](#unsupported_specversion)) MUST be generated.
  Note that this query parameter MAY be included on any API request to the
  server, not just the root of the Registry. When not specified, the default
  value MUST be the newest version of this specification supported by the
  server.

  When comparing `specversion` strings, the server MUST silently ignore the
  "patch" version number and only consider the "major.minor" version numbers.
  This is because any "patch" version updates will only contain clarifications
  and ought not require any code changes for server implementations. Therefore,
  all patch versions of the same "major.minor" version MUST be forwards and
  backwards compatible.

  However, due to the potential for semantics changes of versions with suffix
  values (e.g. `v2.0.0-rc1`), the suffix value MUST be part of the
  `specversion` comparison checking.

A successful response MUST be of the form:

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "specversion": "<STRING>",
  "registryid": "<STRING>",
  "self": "<URL>",
  "shortself": "<URL>", ?
  "xid": "<XID>",
  "epoch": <UINTEGER>,
  "name": "<STRING>", ?
  "description": "<STRING>", ?
  "documentation": "<URL>", ?
  "icon": "<URL>", ?
  "labels": { "<STRING>": "<STRING>" * }, ?
  "createdat": "<TIMESTAMP>",
  "modifiedat": "<TIMESTAMP>",

  "capabilities": { Registry capabilities }, ?   # Only if inlined
  "model": { Registry model }, ?                 # Only if inlined
  "modelsource": { Registry model }, ?           # Only if inlined

  # Repeat for each Group type
  "<GROUPS>url": "<URL>",               # e.g. "endpointsurl"
  "<GROUPS>count": <UINTEGER>,          # e.g. "endpointscount"
  "<GROUPS>": { Groups collection } ?   # Only if inlined
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
  "specversion": "1.0-rc2",
  "registryid": "myRegistry",
  "self": "https://example.com/",
  "xid": "/",
  "epoch": 1,
  "createdat": "2024-04-30T12:00:00Z",
  "modifiedat": "2024-04-30T12:00:01Z",

  "endpointsurl": "https://example.com/endpoints",
  "endpointscount": 42,

  "schemagroupsurl": "https://example.com/schemagroups",
  "schemagroupscount": 1
}
```

Another example where:
- The request asks for the model to be included in the response.
- The request asks for the `schemagroups` Group to be inlined in the response.
- The `endpoints` Group has one extension attribute defined.

```yaml
GET /?inline=schemagroups,model

HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "specversion": "1.0-rc2",
  "registryid": "myRegistry",
  "self": "https://example.com/",
  "xid": "/",
  "epoch": 1,
  "createdat": "2024-04-30T12:00:00Z",
  "modifiedat": "2024-04-30T12:00:01Z",

  "model": {
    ... xRegistry spec-defined attributes excluded for brevity ...
    "groups": {
      "endpoints": {
        "plural": "endpoints",
        "singular": "endpoint",
        "attributes": {
          ... xRegistry spec-defined attributes excluded for brevity ...
          "shared": {
            "name": "shared",
            "type": "boolean"
          }
        },

        "resources": {
          "messages": {
            "plural": "messages",
            "singular": "message",
            "attributes": {
              ... xRegistry spec-defined attributes excluded for brevity ...
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
        ... xRegistry spec-defined attributes excluded for brevity ...

        "resources": {
          "schemas": {
            "plural": "schemas",
            "singular": "schema",
            ... xRegistry spec-defined attributes excluded for brevity ...
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
      "schemaid": "mySchemas",
      # Remainder of schemagroup is excluded for brevity
    }
  }
}
```

#### Updating the Registry Entity

To update the Registry entity, an HTTP `PUT` or `PATCH` MAY be used.

The request MUST be of the form:

```yaml
PUT /
or
PATCH /
Content-Type: application/json; charset=utf-8

{
  "registryid": "<STRING>", ?
  "epoch": <UINTEGER>, ?
  "name": "<STRING>", ?
  "description": "<STRING>", ?
  "documentation": "<URL>", ?
  "icon": "<URL>", ?
  "labels": { "<STRING>": "<STRING>" * }, ?
  "createdat": "<TIMESTAMP>", ?
  "modifiedat": "<TIMESTAMP>", ?

  "capabilities": { Registry capabilities }, ?
  "modelsource": { Registry model }, ?

  # Repeat for each Group type that has a Group to be updated
  "<GROUPS>": { Groups collection } ?
}
```

Where:
- The HTTP body MUST contain the full JSON representation of the Registry
  entity's mutable attributes that are to be set, the rest will be deleted.
- The request MAY include the `'modelsource` attribute if the Registry model
  definitions are to be updated as part of the request. See [Creating or
  Updating the Registry Model](#creating-or-updating-the-registry-model) for
  more information.
  If present, the Registry's model MUST be updated prior to any entities being
  updated. A value of `null` MUST generate an error
  ([invalid_data](#invalid_data)).
- When `PATCH /` is used, the `modelsource` attribute (if specified) MUST be a
  complete replacement representation of the model definition. In the case of
  the `capabilities` attribute however, it is a "patch" operation and only the
  top-level capabilities specified in the request MUST be updated. Each
  capability present MUST be specified in its entirety.

A successful response MUST include the same content that an HTTP `GET`
on the Registry would return, and be of the form:

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "specversion": "<STRING>",
  "registryid": "<STRING>",
  "self": "<URL>",
  "shortself": "<URL>", ?
  "xid": "<XID>",
  "epoch": <UINTEGER>,
  "name": "<STRING>", ?
  "description": "<STRING>", ?
  "documentation": "<URL>", ?
  "icon": "<URL>", ?
  "labels": { "<STRING>": "<STRING>" * }, ?
  "createdat": "<TIMESTAMP>",
  "modifiedat": "<TIMESTAMP>",

  "capabilities": { Registry capabilities }, ?   # Only if inlined
  "model": { Registry model }, ?                 # Only if inlined
  "modelsource": { Registry model }, ?           # Only if inlined

  # Repeat for each Group type
  "<GROUPS>url": "<URL>",
  "<GROUPS>count": <UINTEGER>,
  "<GROUPS>": { Groups collection }              # Only if inlined
}
```

**Examples:**

Updating a Registry's metadata

```yaml
PUT /
Content-Type: application/json; charset=utf-8

{
  "registryid": "myRegistry",
  "name": "My Registry",
  "description": "An even cooler registry!"
}
```

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "specversion": "1.0-rc2",
  "registryid": "myRegistry",
  "self": "https://example.com/",
  "xid": "/",
  "epoch": 2,
  "name": "My Registry",
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

### Registry Capabilities

In order to programmatically discover which capabilities are supported by an
implementation, servers MUST support exposing this information via a
"capabilities" map that lists each supported feature along with any related
configuration detail that will help in successful usage of that feature.

The "key" of the capabilities-map is the "name" of each feature, and the
"value" is a feature-specific set of configuration values, with the most basic
being a `<BOOLEAN>` value of `true` to indicate support for the feature.

The capabilities-map MAY be retrieved via two mechanisms:
- An HTTP `GET` request to the `/capabilities` API SHOULD be supported
  by all compliant implementations. However, as with all defined APIs,
  security/access controls MAY be mandated.
- The Registry `capabilities` attribute MAY be requested via the `?inline`
  query parameter. Note that support for the `?inline` query parameter itself
  is OPTIONAL. The `capabilities` attribute MUST only appear when explicitly
  requested by the client via the `?inline` query parameter.

Regardless of the retrieval mechanism, the format of the capabilities-map MUST
be of the form:

```
{
  "apis": [ "<STRING>" * ], ?
  "flags": [ "<STRING>" * ], ?
  "mutable": [ "<STRING>" * ], ?
  "pagination": <BOOLEAN>, ?
  "shortself": <BOOLEAN>, ?
  "specversions": [ "<STRING>" ], ?
  "stickyversions": <BOOLEAN>, ?
  "versionmodes": [ "<STRING>" ], ?

  "<STRING>": ... capability configuration ... *   // Extension capabilities
}
```

Where:
- `"<STRING>"`, as a key, MUST be the name of the capability. This
  specification places no restriction on the `"<STRING>"` value, other than it
  MUST be unique across all capabilities and not be an empty string. It is
  RECOMMENDED that extensions use some domain-specific name to avoid possible
  conflicts with other extensions.

All capability values, including extensions, MUST be defined as one of the
following:
- Numeric (one of: integer, uinteger, decimal)
- Boolean
- String
- Array of one of the above

The absence of a capability in the capability map is an indication that the
feature is not supported. All supported extensions MUST be included in the list.

Absence, presence, or configuration values of a feature in the map MAY vary
based on the authorization level of the client making the request.

The following defines the specification-defined capabilities:

#### `apis`
- Name: `apis`
- Type: Array of strings
- Description: The list of APIs (beyond the APIs for the data model) that
  are supported for read (`HTTP GET`) operations. This list is meant to allow
  for clients/tooling to easily discover which of the APIs, that are not
  related to the data model, are supported. Whether any of the APIs listed
  are supported for write operations can be discovered via the
  `mutable` capability.
- Note that it is allowable for the data that is available via more than one
  mechanism to not be available via all mechanisms. For example, it is
  possible for an implementation to support `GET /model` but not
  `GET /?inline=model`.
- Defined values:
  - `/capabilities`
  - `/export`
  - `/model`
  - `/modelsource`
- Values MUST start with `/`.
- When not specified, the default value MUST be an empty list and no APIs
  beyond those for the data model are supported.
- Implementations MAY define their own values but they MUST NOT conflict with
  specification-defined APIs, Registry-level attributes or Group collection
  attribute names.
- It is STRONGLY RECOMMENDED that implementations support at least
  `/capabilities` and `/model`.

#### `flags`
- Name: `flags`
- Type: Array of strings
- Description: The list of supported flags (query parameters). Absence in the
  map indicates no support for that flag, and if included in a request,
  it SHOULD be silently ignored by servers.
- Defined values:
    `collections`, `doc`, `epoch`, `filter`, `ignoredefaultversionid`,
    `ignoredefaultversionsticky`, `ignoreepoch`, `ignorereadonly`, `inline`,
    `offered`, `setdefaultversionid`, `specversion`.
- When not specified, the default value MUST be an empty list and no query
  parameters are supported.
- Examples:
  - `"flags": [ "filter", "inline" ]`    # Just these 2
  - `"flags": [ "*" ]                    # All server-supported flags

#### `mutable`
- Name `mutable`
- Type: Array of strings
- Description: The list of items in the Registry that can be edited by the
  client. `entities` refers to Groups, Resources, Versions and the Registry
  itself. `modelsource` refers to the ability to modify the Registry model.
  `capabilities` refers to the ability to modify (and configure) the
  server. Presence in this list does not guarantee that a client can edit
  all items of that type. For example, some Resources might still be read-only
  even if the client has the ability to edit Resources in general.
- Supported values:
  - `capabilities`
  - `entities`
  - `modelsource`
- When not specified, the default value MUST be an empty list and the Registry
  is read-only.

#### `pagination`
- Name: `pagination`
- Type: Boolean
- Description: Indicates whether the server supports the use of the
  [pagination](../pagination/spec.md) specification (value of `true`).
- When not specified, the default value MUST be `false`.

#### `shortself`
- Name: `shortself`
- Type: Boolean
- Description: Indicates whether the `shortself` attribute MUST be included
  in the server serialization of the entities within the Registry (value of
  `true`).
- When not specified, the default value MUST be `false`.

#### `specversions`
- Name: `specversions`
- Type: Array of strings
- Description: List of xRegistry specification versions supported.
- Supported values include:
  - `1.0-rc2`
- A value of `1.0-rc2` MUST be included in the list.
- When not specified, the default value MUST be `1.0-rc2`.

#### `stickyversions`
- Name: `stickyversions`
- Type: Boolean
- Description: Indicates whether the server supports clients choosing which
  Version of a Resource is to be the "default" Version. In other words, this
  capability indicates whether a request to set a Resource's
  `setdefaultversionsticky` attribute to `true` is allowed.
- When not specified, the default value MUST be `true`.

The list of values for the arrays MUST be case-insensitive and MAY include
extension values.

For clarity, servers MUST include all known capabilities in the serialization,
even if they are set to their default values or have empty lists.

#### Updating the Capabilities of a Server

If supported, updates to the server's capabilities MAY be done via an HTTP
`PUT`, or `PATCH`, to the `/capabilities` API, or by updating the
`capabilities` attribute on the root of the Registry. As with other APIs, a
`PUT` MUST be interpreted as a request to update the entire set of
capabilities and any missing capability MUST be interpreted as a request to
reset it to its default value. If a `PATCH` is used then each capability
included MUST be fully specified, and only those specified in the request MUST
be fully replaced by the incoming values. In other words, `PATCH` is done at a
capability level, not any deeper within the JSON structure.

The request to the `/capabilities` API MUST be of the form:

```yaml
PUT /capabilities
or
PATCH /capabilities
Content-Type: application/json; charset=utf-8

{ ... Capabilities map ...  }
```

Where:
- The HTTP body MUST contain the full representation of all capabilities
  in the case of `PUT`, or the full representation of just the modified
  capabilities in the case of `PATCH`.
- Any change to the configuration of the server that is not supported MUST
  result in an error ([capability_error](#capability_error)) and no changes
  applied. Likewise, any unknown capability keys specified MUST generate an
  error ([capability_error](#capability_error)).

A successful response MUST include a full representation of all of the
capabilities of the Registry and be of the form:

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{ ... Capabilities map ... }
```

Updates via the `capabilities` attribute follows the same attribute
update semantics as the other Registry-level attributes. Note that using
an HTTP `PATCH` to update the Registry's attributes MAY include the
`capabilities` attribute, and, if present, it MUST be processed with the
`PATCH` semantics as well.

When processing a request to update the capabilities, the semantic
change MUST NOT take effect until after the processing of the current
request. Note that if the response includes the serialization of the
Registry's capabilities, then the changes MUST appear in that serialization.

For any capability that is an array of strings, a value of `"*"` MAY be used to
indicate that the server MUST replace `"*"` with the full set of items that
are available. An error ([capability_error](#capability_error)) MUST be
generated if `"*"` appears with any other value in the list. `"*"` MUST NOT
appear in the serialization in any server's response.

Regardless of the mechanism used to update the capabilities, the Registry's
`epoch` value MUST be incremented.

For a client to discover the list of available values for each
capability, an HTTP `GET` MAY be sent to the `/capabilities` API with the
`?offered` query parameter and the response MUST adhere to the following
(which borrows much of the same structure from the model definition language):

```yaml
GET /capabilities?offered

{
  "<STRING>": {
    "type": "<TYPE>",
    "item": {
      "type": "<TYPE>"
    }, ?
    "enum": [ <VALUE>, * ], ?
    "min": <VALUE>, ?
    "max": <VALUE>, ?
    "documentation": "<URL>" ?
  }, *
}
```

Where:
- `<STRING>` MUST be the capability name.
- `<TYPE>` MUST be one of `boolean`, `string`, `integer`, `decimal`,
  `uinteger`, `array` as defined in [Attributes and
  Extensions](#attributes-and-extensions).
- When `"type"` is `array`, `"item.type"` MUST be one of `boolean`, `string`,
  `integer`, `decimal`, `uinteger`, otherwise `"item"` MUST be absent.
- `"enum"`, when specified, contains a list of zero or more `<VALUE>`s whose
  type MUST match either `"type"` or `"item.type"` if `"item"` is `"array"`.
  This indicates the list of allowable values for this capability.
- `"min"` and `"max"`, when specified, MUST match the same type as either
  `"type"` or `"item.type"` if `"item"` is `"array"`. These indicate the
  minimum or maximum (inclusive) value range of this capability. When not
  specified, there is no stated lower (or upper) limit. These MUST only be
  used when "type" is a numeric type.
- `"documentation"` provides a URL with additional information about the
  capability.

For example:

```yaml
GET /capabilities?offered

{
  "apis": {
    "type": "string",
    "enum": [ "/capabilities", "/export", "/model", /"modelsource" ]
  },
  "flags": {
    "type": "string",
    "enum": [ "collections", "doc", "epoch", "filter",
      "ignoredefaultversionid", "ignoredefaultversionsticky", "ignoreepoch",
      "ignorereadonly", "inline", "offered", "setdefaultversionid",
      "sort", "specversion" ]
  },
  "pagination": {
    "type": "boolean",
    "enum": [ false, true ]
  },
  "shortself": {
    "type": "boolean",
    "enum": [ false, true ]
  },
  "specversions": {
    "type": "string",
    "enum": [ "1.0-rc2" ]
  },
  "stickyversions": {
    "type": "boolean",
    "enum": [ true ]
  },
  "versionmodes": [ "manual" ]
}
```

The enum of values allows for some special cases:
- String capabilities MAY include `*` as a wildcard character in a value
  to indicate zero or more unspecified characters MAY appear at that location
  in the value string.

A request to update a capability with a value that is compliant with the
output of the `/capabilities?offered` MAY still generate an error
([capability_error](#capability_error)) if the server determines it cannot
support the request. For example, due to authorization concerns or the value,
while syntactically valid, isn't allowed in certain situations.

For clarity, even in cases where there is no variability allowed with certain
capabilities, they SHOULD still be listed in both the `/capabilities` API
and the `/capabilities?offered` API to maximize discoverability. For example,
if `pagination` is not supported, then a server SHOULD still include:

```yaml
  "pagination": false
```

in the `/capabilities` output, and

```yaml
  "pagination": {
    "type": "boolean",
    "enum": [ false ]
  }
```

in the `/capabilities?offered` output (assuming the API and flag are supported).

### Registry Model

The Registry model defines the Groups, Resources, attributes and changes to
specification-defined attributes that define what a Registry instance supports.
This information is intended to be used by tooling that does not have
knowledge of the structure of the Registry in advance and therefore will need
to dynamically discover it.

The following sections will go into the details of how to create, retrieve
and edit the model of a Registry.

The overall format of a model definition is as follows:

```yaml
{
  "description": "<STRING>", ?
  "documentation": "<URL>", ?
  "labels": { "<STRING>": "<STRING>" * }, ?
  "attributes": {                      # Registry-level extensions
    "<STRING>": {                      # Attribute name
      "name": "<STRING>",              # Same as attribute's key
      "type": "<TYPE>",                # boolean, string, array, object, ...
      "target": "<XIDTYPE>", ?         # If "type" is "xid" or "url"
      "namecharset": "<STRING>", ?     # If "type" is "object"
      "description": "<STRING>", ?
      "enum": [ <VALUE> * ], ?         # Array of scalars of type "<TYPE>"
      "strict": <BOOLEAN>, ?           # Just "enum" values or not. Default=true
      "readonly": <BOOLEAN>, ?         # From client's POV. Default=false
      "immutable": <BOOLEAN>, ?        # Once set, can't change. Default=false
      "required": <BOOLEAN>, ?         # Default=false
      "default": <VALUE>, ?            # Scalar attribute's default value

      "attributes": { ... }, ?         # If "type" above is object
      "item": {                        # If "type" above is map,array
        "type": "<TYPE>", ?            # map value type, or array type
        "target": "<XIDTYPE>", ?       # If this item "type" is xid/url
        "namecharset": "<STRING>", ?   # If this item "type" is object
        "attributes": { ... }, ?       # If this item "type" is object
        "item": { ... } ?              # If this item "type" is map,array
      } ?

      "ifvalues": {                    # If "type" is scalar
        "<STRING>": {
          "siblingattributes": { ... } # Siblings to this "attribute"
        } *
      } ?
    } *
  },

  "groups": {
    "<STRING>": {                      # Key=plural name, e.g. "endpoints"
      "plural": "<STRING>",            # e.g. "endpoints"
      "singular": "<STRING>",          # e.g. "endpoint"
      "description": "<STRING>", ?
      "documentation": "<URL>", ?
      "icon": "<URL>", ?
      "labels": { "<STRING>": "<STRING>" * }, ?
      "modelversion": "<STRING>", ?    # Version of the group model
      "compatiblewith": "<URI>", ?     # Statement of compatibility
      "attributes": { ... }, ?         # See "attributes" above
      "ximportresources": [ "<XIDTYPE>", * ], ?   # Include these Resources

      "resources": {
        "<STRING>": {                  # Key=plural name, e.g. "messages"
          "plural": "<STRING>",        # e.g. "messages"
          "singular": "<STRING>",      # e.g. "message"
          "description": "<STRING>", ?
          "documentation": "<URL>", ?
          "icon": "<URL>", ?
          "labels": { "<STRING>": "<STRING>" * }, ?
          "modelversion": "<STRING>", ?  # Version of the resource model
          "compatiblewith": "<URI>"`, ?  # Statement of compatibility
          "maxversions": <UINTEGER>, ?   # Num Vers(>=0). Default=0, 0=unlimited
          "setversionid": <BOOLEAN>, ?   # vid settable? Default=true
          "setdefaultversionsticky": <BOOLEAN>, ? # sticky settable?Default=true
          "hasdocument": <BOOLEAN>, ?       # Has separate document.Default=true
          "versionmode": "<STRING>", ?      # 'ancestor' processing algorithm
          "singleversionroot": <BOOLEAN>, ? # enforce single root. Default=false
          "typemap": <MAP>, ?               # contenttype mappings
          "attributes": { ... }, ?          # Version attributes/extensions
          "resourceattributes": { ... }, ?  # Resource attributes/extensions
          "metaattributes": { ... } ?       # Meta attributes/extensions
        } *
      } ?
    } *
  } ?
}
```

The following describes the attributes of the Registry model:

##### - Model: `description`
  - Type: String.
  - OPTIONAL
  - A human-readable description of the model.

##### - Model: `labels`
  - Type: Map of string-string.
  - OPTIONAL.
  - A set of name/value pairs that allows for additional metadata about the
    Registry to be stored without changing the schema of the model.
  - If present, MUST be a map of zero or more name/value string pairs.
    See [Attributes and Extensions](#attributes-and-extensions) for more
    information.
  - Keys MUST be non-empty strings.
  - Values MAY be empty strings.

##### - Model: `attributes`
  - Type: Map of attribute definitions where each attribute's name MUST match
    the key of the map.
  - OPTIONAL.
  - A set of zero or more attributes. This includes extensions and
    specification-defined/modified attributes.
  - REQUIRED at specification-defined locations, otherwise OPTIONAL for
    extensions Objects.

##### - Model: `attributes."<STRING>"`
  - Type: String.
  - REQUIRED.
  - The name of the attribute being defined. See `attributes."<STRING>".name`
    for more information.

##### - Model: `attributes."<STRING>".name`
  - Type: String.
  - REQUIRED.
  - The name of the attribute. MUST be the same as the key used in the owning
    `attributes` map. A value of `*` indicates support for undefined
    extension names. Absence of a `*` attribute indicates lack of support for
    undefined extensions and an error ([unknown_attribute](#unknown_attribute))
    MUST be generated if one is present in a request to update the Registry
    attributes.

    Often `*` is used with a `type` of `any` to allow for any undefined
    extension name of any supported data type. By default, the model
    does not support undefined extensions. Note that undefined extensions, if
    supported, MUST adhere to the same rules as
    [defined extensions](#attributes-and-extensions).

    An attribute of `*` MUST NOT use the `ifvalues` feature, but a non-`*`
    attribute MAY define an `ifvalues` attribute named `*` as long as there
    isn't already one defined for this level in the entity.

    An extension attribute MUST NOT use a name that conflicts with any
    specification-defined attribute, sub-object attribute or
    collection-related attribute names defined at the same level in the
    hierarchy. For Resource/Version attributes, this applies for both
    levels - e.g. a Version-level extension MUST NOT use a name that conflicts
    with its Resource-level attribute names.

##### - Model: `attributes."<STRING>".type`
  - Type: `TYPE`.
  - REQUIRED.
  - The "TYPE" of the attribute being defined. MUST be one of the data types
    (in lower case) defined in [Attributes and
    Extensions](#attributes-and-extensions).

##### - Model: `attributes."<STRING>".target`
  - Type: String.
  - OPTIONAL.
  - The type of entity that this attribute points to when `type` is set to
    `url-reference`, `uri-reference` or `xid`. `target` MUST NOT be used
    for any other type of attribute.
  - The value of this model attribute MUST be an "xid template" of one of the
    following forms:
    - `/<GROUPS>` - a plural Group type name. An entity attribute of this
      type/target MUST reference an instance of this Group type.
    - `/<GROUPS>/<RESOURCES>` - a plural Resource type name. An entity
      attribute of this type/target MUST reference an instance of this
      Resource type, not a specific Version of the Resource.
    - `/<GROUPS>/<RESOURCES>[/versions]`. An entity attribute of this
      type/target MUST reference either an instance of this Resource type or
      an instance of a Version of this Resource type. Note the `[/versions]`
      portion of the `target` value is that exact string, including the
      square brackets.
    - `/GROUPS/<RESOURCES>/versions` - a Version of a Resource type. An entity
      attribute of this type/target MUST reference an instance of a Version
      of this Resource type, not the Resource itself.
  - An `xid` entity attribute that includes a `target` value as part of
    its model definition MUST match the `target` entity type specified. An
    `xid` attribute that does not include `target` definition has no
    such restriction and MAY be any valid `xid` value.
  - A URI/URL-reference entity attribute MAY include `target` as part of its
    definition. If so, then any runtime value that is a relative URI/URL
    (begins with `/`) MUST be an `xid` and MUST adhere to the `target` entity
    type specified, if specified. Absolute URIs/URLs are not constrained by
    the presence of a `target` value.
  - Example: `/endpoints/messages`

##### - Model: `attributes."<STRING>".namecharset`
  - Type: String.
  - OPTIONAL, and MUST only be used when `type` is `object`.
  - Specifies the name of the character set that defines the allowable
    characters that can be used for the object's top-level attribute names.
    Any attempt to define a top-level attribute for this object that does
    not adhere to the characters defined by the character set name MUST
    generate an error ([invalid_character](#invalid_character)).
  - Per the [Attributes and Extensions](#attributes-and-extensions) section,
    attribute names are normally limited to just the set of characters that
    ensure they can reliably be used in cases such as code variable names
    without the need for some escaping mechanism. However, there are
    situations where object-typed attribute names need to support additional
    characters, such as a dash (`-`), and it is known that they will never be
    used in those restricted character set situations. By setting the
    `namecharset` aspect to `extended` the server MUST allow for an extended
    set of valid characters in attribute names for this object.

    The allowed character set for attribute names within an `object` MUST also
    apply to the top-level `siblingattributes` of any `ifvalues` defined
    for those attributes.
  - This specification defines two character sets:
    - `strict` - this character set is the same as the set of characters
      defined for all attribute names - see [Attributes and
      Extensions](#attributes-and-extensions).
    - `extended` - this character set is the same as the set of characters
      defined for all map key names - see [Attributes and
      Extensions](#attributes-and-extensions).
  - When not specified, the default value is `strict`.
  - Implementations MAY define additional character sets, however, an attempt
    to define a model that uses an unknown character set name MUST generate an
    error ([model_error](#model_error)). There is currently no mechanism
    defined by this specification to discover the list (or definition) of
    additional `namecharset` values supported by an implementation.
    Implementations SHOULD use their documentation to advertise this extension.

##### - Model: `attributes."<STRING>".description`
  - Type: String.
  - OPTIONAL.
  - A human-readable description of the attribute.

##### - Model: `attributes."<STRING>".enum`
  - Type: Array of values of type `attributes."<STRING>".type`..
  - OPTIONAL.
  - A list of possible values for this attribute. Each item in the array MUST
    be of type defined by `type`. When not specified, or an empty array, there
    are no restrictions on the value set of this attribute. This MUST only be
    used when the `type` is a scalar. See the `strict` attribute below.

    When specified without `strict` being `true`, this list is just a
    suggested set of values and the attribute is NOT REQUIRED to use one of
    them.

##### - Model: `attributes."<STRING>".strict`
  - Type: Boolean.
  - OPTIONAL.
  - Indicates whether the attribute restricts its values to just the array of
    values specified in `enum` or not. A value of `true` means that any
    values used that are not part of the `enum` set MUST generate an error
    ([invalid_data](#invalid_data)).
    This attribute has no impact when `enum` is absent or an empty array.
  - When not specified, the default value MUST be `true`.

##### - Model: `attributes."<STRING>".readonly`
  - Type: Boolean.
  - OPTIONAL.
  - Indicates whether this attribute is modifiable by a client. During
    creation, or update, of an entity if this attribute is specified, then
    its value MUST be silently ignored by the server even if the value is
    invalid.

    Typically, attributes that are completely under the server's control
    will be `readonly` - e.g. `self`.

  - When not specified, the default value MUST be `false`.
  - When the attribute name is `*` then `readonly` MUST NOT be set to `true`.

##### - Model: `attributes."<STRING>".immutable`
  - Type: Boolean.
  - OPTIONAL.
  - Indicates whether this attribute's value can be changed once it is set.
    This MUST ONLY be used for server-controlled specification-defined
    attributes, such as `specversion` and `<SINGULAR>id`, and MUST NOT be used
    for extension attributes. As such, it is only for informational purposes
    for clients.

    Once set, any attempt to update the value MUST be silently ignored by
    the server.

  - When not specified, the default value MUST be `false`.

##### - Model: `attributes."<STRING>".required`
  - Type: Boolean
  - OPTIONAL.
  - Indicates whether this attribute is REQUIRED to have a non-null value.
  - When set to `true`, this specification does not mandate how this
    attribute's value is populated (i.e. by a client, the server or via a
    default value), just that by the end of processing any request it MUST
    have a non-null value, and generate an error
    ([invalid_data](#invalid_data)) if not.
  - A `true` value also implies that this attribute MUST be serialized in any
    response from the server - with the exception of the optimizations
    specified for document view.
  - When not specified the default value MUST be `false`.
  - When the attribute name is `*` then `required` MUST NOT be set to `true`.
  - MUST NOT be `false` if a default value (`attributes."<STRING>".default`)
    is defined.

##### - Model: `attributes."<STRING>".default`
  - Type: MUST be a non-`null` value of the type specified by the
    `attributes."<STRING>".type` model attribute and MUST only be used for
    scalar types.
  - OPTIONAL.
  - This value MUST be used to populate this attribute's value if one was
    not provided by a client. An attribute with a default value does not mean
    that its owning Object is mandated to be present, rather the attribute
    would only appear when the owning Object is present. By default,
    attributes have no default values.
  - When not specified, this attribute has no default value and has the same
    semantic meaning as being absent or set to `null`.
  - When a default value is specified, this attribute MUST be serialized in
    responses from servers as part of its owning entity, even if it is set to
    its default value. This means that any attribute that has a default value
    defined MUST also have its `required` aspect set to `true`.
  - If the default value of an attribute changes over time, all existing
    instances of that attribute MUST retain their current values and not
    be automatically changed to the new default value. In other words, a new
    default value MUST only apply to new, or subsequent updates (when set to
    `null`, which would reset it to the current default value) of existing,
    instances of the attribute.

##### - Model: `attributes."<STRING>".attributes`
  - Type: Object, see `attributes` above.
  - OPTIONAL.
  - This contains the list of attributes defined as part of a nested entity.
  - MAY be present when the owning attribute's `type` is `object`, otherwise it
    MUST NOT be present. It MAY be absent or an empty list if there are no
    defined attributes for the nested `object`.

##### - Model: `attributes."<STRING>".item`
  - Type: Object.
  - REQUIRED when owning attribute's `type` is `map` or `array`.
  - Defines the nested entity that this attribute references. This
    attribute MUST only be used when the owning attribute's `type` value is
    `map` or `array`.

##### - Model: `attributes."<STRING>".item.type`
  - Type: `TYPE`.
  - REQUIRED.
  - The "TYPE" of this nested entity.

##### - Model: `attributes."<STRING>".item.target`
  - Type: String.
  - OPTIONAL, and MUST only be used when `item.type` is `url-reference`,
    `uri-reference` or `xid`.
  - See [`attributes."<STRING>".target`](#--model-attributesstringtarget) above.

##### - Model: `attributes."<STRING>".item.namecharset`
  - See [`namecharset`](#--model-attributesstringnamecharset) above.
  - OPTIONAL, and MUST only be used when `item.type` is `object`.

##### - Model: `attributes."<STRING>".item.attributes`
  - See [`attributes`](#--model-attributes) above.
  - OPTIONAL, and MUST ONLY be used when `item.type` is `object`.

##### - Model: `attributes."<STRING>".item.item`
  - See [`attributes."<STRING>".item`](#--model-attributesstringitem) above.
  - REQUIRED when `item.type` is `map` or `array`.

##### - Model: `attributes."<STRING>".ifvalues`
  - Type: Map where potential runtime values of the attribute are the keys of
    the map.
  - OPTIONAL.
  - This map can be used to conditionally include additional
    attribute definitions based on the runtime value of the current attribute.
    If the string serialization of the runtime value of this attribute matches
    the `ifvalues` key (case-sensitive), then the `siblingattributes` MUST be
    included in the model as siblings to this attribute.

    If `enum` is not empty and `strict` is `true` then this map MUST NOT
    contain any value that is not specified in the `enum` array.

    This aspect MUST only be used for scalar attributes.

    All attributes defined for this `ifvalues` MUST be unique within the scope
    of this `ifvalues` and MUST NOT match a named attribute defined at this
    level of the entity. If multiple `ifvalues` sections, at the same entity
    level, are active at the same time then there MUST NOT be duplicate
    `ifvalues` attributes names between those `ifvalues` sections.
  - `ifvalues` `"<STRING>"` MUST NOT be an empty string.
  - `ifvalues` `"<STRING>"` MUST NOT start with the `^` (caret) character as
    its presence at the beginning of `"<STRING>"` is reserved for future use.
  - `ifvalues` `siblingattributes` MAY include additional `ifvalues`
    definitions.

##### - Model: `groups`
  - Type: Map where the key MUST be the plural name (`groups.plural`) of the
    Group type (`<GROUPS>`).
  - REQUIRED if there are any Group types defined for the Registry.
  - A set of zero or more Group types supported by the Registry.

##### - Model: `groups."<STRING>"`
  - Type: String.
  - REQUIRED.
  - The name of the Group being defined. See `groups."<STRING>".plural`
    for more information.

##### - Model: `groups."<STRING>".plural`
  - Type: String.
  - REQUIRED.
  - MUST be immutable.
  - The plural name of the Group type e.g. `endpoints` (`<GROUPS>`).
  - MUST be unique across all Group types (plural and singular names) in the
    Registry.
  - MUST be non-empty and MUST be a valid attribute name with the exception
    that it MUST NOT exceed 58 characters (not 63).

##### - Model: `groups."<STRING>".singular`
  - Type: String.
  - REQUIRED.
  - MUST be immutable.
  - The singular name of a Group type e.g. `endpoint` (`<GROUP>`).
  - MUST be unique across all Group types (plural and singular names) in the
    Registry.
  - MUST be non-empty and MUST be a valid attribute name. For clarity, it
    MUST NOT exceed 63 characters.

##### - Model: `groups."<STRING>".description`
  - Type: String.
  - OPTIONAL
  - A human-readable description of the Group type.

##### - Model: `groups."<STRING>".icon`
  - Type: URL.
  - OPTIONAL
  - A URL to the icon for the Group type.
  - See [`icon`](#icon-attribute) for more information.

##### - Model: `groups."<STRING>".labels`
  - See [`labels`]((#--model-labels) above.
  - OPTIONAL.

##### - Model: `groups."<STRING>".modelversion`
  - Type: String.
  - OPTIONAL.
  - The version of the model of the Group type.
  - It is common to use a combination of major and minor version numbers.
  - Example: `1.2`

##### - Model: `groups."<STRING>".compatiblewith`
  - Type: URI.
  - OPTIONAL.
  - References / represents an xRegistry model definition that
    the Group type is compatible with. This is meant to express
    interoperability between models in different xRegistries via using a
    shared compatible model.
  - Does not imply runtime validation of the claim.
  - Example: `https://xregistry.io/xreg/xregistryspecs/schema-v1/docs/model.json`

##### - Model: `groups."<STRING>".attributes`
  - See [`attributes`](#--model-attributes) above.
  - OPTIONAL.

##### - Model: `groups."<STRING>".ximportresources`
  - OPTIONAL.
  - See [Reuse of Resource Definitions](#reuse-of-resource-definitions) for
    more information.

##### - Model: `groups."<STRING>".resources`
  - Type: Map where the key MUST be the plural name (`groups.resources.plural`)
    of the Resource type (`<RESOURCES>`).
  - REQUIRED if there are any Resource types defined for the Group type.
  - A set of zero or more Resource types defined for the Group type.

##### - Model: `groups."<STRING>"`.resources."<STRING>"`
  - Type: String.
  - REQUIRED.
  - The name of the Resource being defined. See
    `groups."<STRING>".resources."<STRING>".plural` for more information.

##### - Model: `groups."<STRING>".resources."<STRING>".plural`
  - Type: String.
  - REQUIRED.
  - MUST be immutable.
  - The plural name of the Resource type e.g. `messages` (`<RESOURCES>`).
  - MUST be non-empty and MUST be a valid attribute name with the exception
    that it MUST NOT exceed 58 characters (not 63).
  - MUST be unique across all Resources (plural and singular names) within the
    scope of its owning Group type.

##### - Model: `groups."<STRING>".resources."<STRING>".singular`
  - Type: String.
  - REQUIRED.
  - MUST be immutable.
  - The singular name of the Resource type e.g. `message` (`<RESOURCE>`).
  - MUST be non-empty and MUST be a valid attribute name with the exception
    that it MUST NOT exceed 57 characters (not 63).
  - MUST be unique across all Resources (plural and singular names) within the
    scope of its owning Group type.

##### - Model: `groups."<STRING>".resources."<STRING>".description`
  - Type: String.
  - OPTIONAL
  - A human-readable description of the Resource type.

##### - Model: `groups."<STRING>".resources."<STRING>".icon`
  - Type: URL.
  - OPTIONAL
  - A URL to the icon for the Resource type.
  - See [`icon`](#icon-attribute) for more information.

##### - Model: `groups."<STRING>".resources."<STRING>".labels`
  - See [`attributes`](#--model-attributes) above.
  - OPTIONAL.

##### - Model: `groups."<STRING>".resources."<STRING>".modelversion`
  - See [`modelversion`](#--model-groupsstringmodelversion) above.
  - OPTIONAL.

##### - Model: `groups."<STRING>".resources."<STRING>".compatiblewith`
  - See [`modelversion`](#--model-groupsstringcompatiblewith) above.
  - OPTIONAL.

##### - Model: `groups."<STRING>".resources."<STRING>".maxversions`
  - Type: Unsigned Integer.
  - OPTIONAL.
  - Number of Versions that will be stored in the Registry for this Resource
    type.
  - When not specified, the default value MUST be zero (`0`).
  - A value of zero (`0`) indicates there is no stated limit, and
    implementations MAY prune non-default Versions at any time. This means
    it is valid for an implementation to only support one (`1`) Version when
    `maxversions` is set to `0`.
  - When the limit is exceeded, implementations MUST prune Versions by
    deleting the oldest Version first (based on the Resource's
    [`versionmode`](#--model-groupsstringresourcesstringversionmode)
    algorithm), skipping the Version marked as "default".
    Once the single oldest Version is determined, delete it.
    A special case for the pruning rules is that if `maxversions` is set to
    one (1), then the "default" Version is not skipped, which means it will be
    deleted and the new Version will become "default".

##### - Model: `groups."<STRING>".resources."<STRING>".setversionid`
  - Type: Boolean (`true` or `false`, case-sensitive).
  - OPTIONAL.
  - Indicates whether support for client-side setting of a Version's
    `versionid` is supported.
  - When not specified, the default value MUST be `true`.
  - A value of `true` indicates the client MAY specify the `versionid` of a
    Version during its creation process.
  - A value of `false` indicates that the server MUST choose an appropriate
    `versionid` value during creation of the Version.
  - During the creation of a new Version, if `setversionid` is `false` and
    a `versionid` is provided then the server MUST generate an error
    ([versionid_not_allowed](#versionid_not_allowed)).

##### - Model: `groups."<STRING>".resources."<STRING>".setdefaultversionsticky`
  - Type: Boolean (`true` or `false`, case-sensitive).
  - OPTIONAL.
  - Indicates whether support for client-side selection of the "default"
    Version is supported for Resources of this type. Once set, the default
    Version MUST NOT change unless there is some explicit action by a client
    to change it - hence the term "sticky".
  - When not specified, the default value MUST be `true`.
  - A value of `true` indicates a client MAY select the default Version of
    a Resource via one of the methods described in this specification rather
    than the server always choosing the default Version.
  - A value of `false` indicates the server MUST choose which Version is the
    default Version.
  - An attempt to set the `defaultversionid` attribute when this aspect is
    `false` MUST generate an error
    ([defaultversionid_not_allowed](#defaultversionid_not_allowed)).
  - This attribute MUST NOT be `true` if `maxversions` is one (`1`).

##### - Model: `groups."<STRING>".resources."<STRING>".hasdocument`
  - Type: Boolean (`true` or `false`, case-sensitive).
  - OPTIONAL.
  - Indicates whether or not Resources of this type can have a document
    associated with it. If `false` then the xRegistry metadata becomes "the
    document". Meaning, an HTTP `GET` to the Resource's URL will return the
    xRegistry metadata in the HTTP body. The `xRegistry-` HTTP headers,
    representing the Resource metadata, MUST NOT be used for requests or
    response messages for these Resources. Use of `$details` on the request
    URLs MAY be used to provide consistency with the cases where this
    attribute is set to `true` - but the output remains the same.

    A value of `true` does not mean that these Resources are guaranteed to
    have a non-empty document, and an HTTP `GET` to the Resource MAY return an
    empty HTTP body.
  - When not specified, the default value MUST be `true`.
  - A value of `true` indicates that Resource of this type supports a separate
    document to be associated with it.

##### - Model: `groups."<STRING>".resources."<STRING>".versionmode`
  - Type: String
  - OPTIONAL.
  - Indicates the algorithm that MUST be used when determining how Versions
    are managed with respect to aspects such as:
    - Which Version is the "newest"?
    - Which Version is the "oldest"?
    - How a Version's `ancestor` attribute will be populated when not
      explicitly set by a client.
  - Implementations MAY defined additional algorithms and MAY defined
    additional aspects that they control, as long as those aspects do not
    conflict with specification-defined semantics.
  - Regardless of the algorithm used, implementations MUST ensure that
    the `ancestor` attribute of all Versions of a Resource accurately
    represent the relationship of the Versions prior to the completion of
    any operation. For example, when the `createdat` algorithm is used and
    the `createdat` timestamp of a Version is modified, this might cause a
    reordering of the Versions and the `ancestor` attributes might need to
    be changed accordingly. Similarly, the `defaultversionid` of the
    Resource might change if its `defaultversionsticky` attribute is `false`.
  - When not specified, the default value MUST be `manual`.
  - Implementations MUST support at least `manual`.
  - This specification defines the following `versionmode` algorithms:
    - `manual`
      - Newest Version: MUST be determined by finding all Versions that are
        not referenced as an `ancestor` of another Version, then
        finding the one with the newest `createdat` timestamp. If there is
        more than one, then the one with the highest alphabetically
        case-insensitive `versionid` value MUST be chosen.
      - Oldest Version: MUST be determined by finding all root Versions (ones
        that have an `ancestor` value that points to itself), then finding
        the one with the oldest `createdat` timestamp. If there is more than
        one, then the one with the lowest alphabetically case-insensitive
        `versionid` MUST be chosen.
      - Ancestor Processing: typically provided by clients. During a "create"
        operation, all Versions that do not have an `ancestor` value
        provided MUST be sorted/processed by `versionid` (in case-insensitive
        ascending order) and the `ancestor` value of each MUST be set to the
        current "newest version" per the above semantics. Note that as
        each new Version is created, it MUST become the "newest". If there
        is no existing Version then the new Version becomes a root and its
        `ancestor` value MUST be its `versionid` attribute value.
      - Invalid Ancestor: if a Version's `ancestor` value is no longer
        valid (i.e. the ancestor Version was deleted), then this Version
        MUST become a root, and it's `ancestor` value MUST is its `versionid`
        attribute value.

    - `createdat`
      - Newest Version: MUST be determined by finding the Version with the
        newest `createdat` timestamp. If there is more than one, then the
        one with the highest alphabetically case-insensitive `versionid`
        value MUST be chosen.
      - Oldest Version: MUST be determined by finding the Version with the
        oldest `createdat` timestamp. If there is more than one, then the
        one with the lowest alphabetically case-insensitive `versionid`
        value MUST be chosen. Note that this MUST also be the one and only
        "root" Version.
      - Ancestor Processing: The `ancestor` value of each Version MUST be
        determined via examination of the `createdat` timestamp of each
        Version and the Versions sorted in ascending order, where the first
        one will be the "root" (oldest) Version and its `ancestor` value
        MUST be its `versionid`. If there is more than one Version with the
        same `createdat` timestamp then those MUST be ordered in ascending
        case-insensitive ordered based on their `versionid` values.
      - Invalid Ancestor: When a Version is deleted then the "ancestor
        processing" logic as stated above MUST be applied.
      - When this `versionmode` is used, the `singleversionroot` aspect
        MUST be set to `true`.

    - `modifiedat`
      - This is the same as the `createdat` algorithm except that the
        `modifiedat` attribute of each Version MUST be used instead of the
        `createdat` attribute.

    - `semver`
      - Newest Version: MUST be the Version with the highest `versionid`
        value per the [Semantic Versioning](https://semver.org/)
        specification's "precedence" ordering rules.
      - Oldest Version: MUST be the Version with the lowest `versionid`
        value per the [Semantic Versioning](https://semver.org/)
        specification's "precedence" ordering rules. Note that this MUST also
        be the one and only "root" Version.
      - Ancestor Processing: The `ancestor` value of each Version MUST either
        be its `versionid` value (if it it the oldest Version), or the
        `versionid` of the next oldest Version per the
        [Semantic Versioning](https://semver.org/) specification's
        "precedence" ordering rules.
      - Invalid Ancestor: When a Version is deleted then the "ancestor
        processing" logic as stated above MUST be applied.
      - When this `versionmode` is used, the `singleversionroot` aspect
        MUST be set to `true`.

##### - Model: `groups."<STRING>".resources."<STRING>".singleversionroot`
  - Type: Boolean (`true` or `false`, case-sensitive).
  - OPTIONAL.
  - Indicates whether Resources of this type can have multiple Versions
    that represent roots of an ancestor tree, as indicated by the
    Version's `ancestor` attribute value being the same as its `versionid`
    attribute.
  - When not specified, the default value MUST be `false`.
  - A value of `true` indicates that only one Version of the Resource can
    be a root, and the server MUST generate an error
    ([multiple_roots](#multiple_roots)) if any request results in a state
    where more than one Version of a Resource is a root of an ancestor tree.
  - Note that if the Resource's `versionmode` value might influence
    the permissible values of this aspect.
  - See the
    [`singleversionroot` Policy Enforcement](primer.md#singleversionroot-policy-enforcement)
    section of the Primer for more information.

##### - Model: `groups."<STRING>".resources."<STRING>".typemap`
  - Type: Map where the keys and values MUST be non-empty strings. The key
    MAY include at most one `*` to act as a wildcard to mean zero or more
    instance of any character at that position in the string - similar to a
    `.*` in a regular expression. The key MUST be a case-insensitive string.
  - OPTIONAL.
  - When a Resource's metadata is serialized in a response and the
    `?inline=<RESOURCE>` feature is enabled, the server will attempt to
    serialize the Resource's "document" under the `<RESOURCE>` attribute.
    However, this can only happen under two situations:<br>
    1 - The Resource document's bytes are already in the same format as
        the xRegistry metadata - in other words JSON, or<br>
    2 - The Resource's document can be considered a "string" and therefore
        can be serialized as a "string", possibly with some escaping.<br>

    For some well-known `contenttype` values (e.g. `application/json`), the
    first case can be easily determined by the server. However, for custom
    `contenttype` values the server will need to be explicitly told how to
    interpret its value (e.g. to know if it is a string or JSON).
    The `typemap` attribute allows for this by defining a mapping of
    `contenttype` values to well-known xRegistry format types.

    Since the `contenttype` value is a "media-type" per
    [RFC9110](https://datatracker.ietf.org/doc/html/rfc9110#media.type),
    for purposes of looking it up in the `typemap`, just the `type/subtype`
    portion of the value (case-insensitively) MUST be used. Meaning, any
    `parameters` MUST be excluded.

    If more than one entry in the `typemap` matches the `contenttype`, but
    they all have the same value, then that value MUST be used. If they are
    not all the same, then `binary` MUST be used.

  - This specification defines the following values (case-insensitive):
    - `binary`
    - `json`
    - `string`

    Implementations MAY define additional values.

    A value of `binary` indicates that the Resource's document is to be treated
    as an array of bytes and serialized under the `<RESOURCE>base64` attribute,
    even if the `contenttype` is of the same type of the xRegistry metadata
    (e.g. `application/json`). This is useful when it is desirable to not
    have the server potentially modify the document (e.g. "pretty-print" it).

    A value of `json` indicates that the Resource's document is JSON and MUST
    be serialized under the `<RESOURCE>` attribute if it is valid JSON. Note
    that if there is a syntax error in the JSON then the server MUST treat the
    document as `binary` to avoid sending invalid JSON to the client. The
    server MAY choose to modify the formatting of the document (e.g. to
    "pretty-print" it).

    A value of `string` indicates that the Resource's document is to be treated
    as a string and serialized using the default string serialization rules
    for the format being used to serialize the Resource's metadata. For
    example, when using JSON, this means escaping all non-printable characters.

    Specifying an unknown (or unsupported) value MUST generate an error
    ([model_error](#model_error)) during the update of the xRegistry model.

    By default, the following
    [RFC9110](https://datatracker.ietf.org/doc/html/rfc9110#media.type)
    `typemap` keys MUST be implicitly defined as follows, unless overridden
    by an explicit `typemap` entry:
    - `application/json`: mapped to `json`
    - `*+json`: mapped to `json`
    - `text/plain`: mapped to `string`

  - Example:<br>
    ```yaml
    "typemap": {
      "text/*": "string",
      "text/mine": "json"
    }
    ```

##### - Model: `groups."<STRING>".resources."<STRING>".attributes`
  - See [`attributes`](#--model-attributes) above,
    as well as
    [`resourceattributes`](#--model-groupsstringresourcesstringresourceattributes)
    and [`metaattributes`](#--model-groupsstringresourcesstringmetaattributes)
    below.
  - OPTIONAL.
  - The list of attributes associated with each Version of the Resource.
  - Extension attribute names at this level MUST NOT overlap with extension
    attributes defined at the `groups.resources.resourceattributes` level.
    The only duplicate names allowed are specification-defined attributes
    such as `self` and `xid`, and the Version-specific values MUST be
    overridden by the Resource-level values when serialized.

##### - Model: `groups."<STRING>".resources."<STRING>".resourceattributes`
  - See [`attributes`](#--model-attributes) above.
  - OPTIONAL.
  - The list of attributes associated with the Resource, not its Versions,
    that will appear in the Resource itself (as siblings to the "default"
    Version attributes).
  - These attributes are reserved for system-managed attributes, such as
    `metaurl`, that exist to help in the navigation of the entities. Users
    MUST NOT define additional attributes for this list. Extension
    Resource-level attributes would appear in the `metaattributes` list, while
    Version-level extensions would appear in the `attributes` list.
  - While it is NOT RECOMMENDED, implementations MAY add additional attributes
    to this list if they are necessary to help with model traversal. Otherwise
    the other 2 attribute lists SHOULD be used. The goal is to make the
    Resource entity look at much like the "default" Version as possible,
    adding additional attributes at the Resource level violates that goal.

##### - Model: `groups."<STRING>".resources."<STRING>".metaattributes`
  - See [`attributes`](#--model-attributes) above.
  - OPTIONAL.
  - The list of attributes associated with the Resource, not its Versions,
    that will appear in the `meta` sub-object of the Resource.

Clarifying the  usage of the `attributes`, `resourceattributes` and
`metaattributes`:
- The serialization of the Resource is meant to be (almost) interchangeable
  with the serialization of a Version of that Resource. This will allow users
  to process either entity without needing to know if they were provided the
  Resource itself or a specific Version in most cases.
- To enable this, most of the Resource-specific data (e.g. its
  `defaultversionid`), is serialized under the `meta` sub-object. This avoids
  potential name conflicts between Version and Resource-level attributes, as
  well as avoiding making the serialization of the Resource too verbose/noisy.
- However, there are some Resource-level attributes, that if placed in the
  `meta` sub-object, would appear to be misplaced. For example, the `versions`
  collection attributes could be confusing to users since `meta` is not
  the direct parent/owner of the "versions" collection, the Resource is.
  Especially when considering the URL path to the "versions" collection would
  not have `/meta/` in it.
- Additionally, some common attributes (e.g. `self`) need to appear on both
  Resources as well as Versions but the values need to be different in each
  case. This is why the same attribute names can appear both the
  `resourceattributes` and `attributes` lists, but only specification-defined
  attributes are allowed to have this naming conflict. Extensions are not, as
  that could lead to confusion for users.
- Finally, in the vast majority of cases it is expected that models will only
  need to define Version-level attributes, leaving the more advanced uses of
  Resource and Meta-level attributes to default to the specification-defined
  sets. For this reason, the Version-level attributes use a list called
  `attributes` in order to make user creation of the model easier, leaving
  the edge cases of Resource or Meta-level extension attributes to use more
  verbosely named lists.

#### Retrieving the Registry Model

The Registry model is available in two forms:
- The full "model" with all possible aspects of the model defined.
- The "modelsource" form represents just the model aspects as specified when
  the model was defined or last updated.

The full "model" view can be thought of as a full schema definition of what the
message exchanges with the server might look like. As such, it includes
the Groups, Resources, model-specific attributes, extension attributes,
specification-defined attributes and overrides to those specification-defined
attributes.

The "modelsource" view of the model is just what was provided by the user when
the model was defined, or last edited. It is expected that this view of the
model is much smaller than the full model and only includes
domain-specific information. While specification-defined attributes MAY appear
in this document, they are NOT RECOMMENDED since the server will automatically
add them so users do not need to concern themselves with those details.

The modelsource document is always a semantic subset of the full model
document.

To retrieve either of the model views as a stand-alone entity, an HTTP `GET`
MAY be used. In the case of retrieving the full model, the result MUST include
the full Registry model - meaning all specification-defined attributes,
extension attributes, Group types, and Resource types.

For the sake of brevity, this specification doesn't include the full definition
of the specification-defined attributes as part of the snippets of output.
However, an example of a full model definition of a sample Registry can be
can be found in this sample [sample-model-full.json](sample-model-full.json).

The full model MAY be retrieved via:
- `GET /model`
- `GET /?inline=model`                      # as part of Registry entity

Where a successful response MUST include the full model definition, adhering
to the model format specified above.

The modelsource MAY be retrieved via:
- `GET /modelsource`
- `GET /?inline=modelsource`                # as part of Registry entity

Where a successful response MUST include the model definition last used when
updating the model.

Additionally:
- The `/model` API  and `model` attribute MUST be a read-only.
- The `/modelsource` API  and `modelsource` attribute MAY be used to retrieve
  the model specification last used to update the model.

In the case of using the `/model` and `/modelsource` APIs, the response MUST
adhere to:

```yaml
HTTP/1.1 200 OK
Content-Type: ...

... xRegistry model ...
```

Where:
- The HTTP body MUST be representation of the Registry model.
- The full model MUST include the definition of all top-level attributes,
  whether they are defined by the user or this specification. This includes
  `capabilities`, `model`,`<RESOURCE>` attributes, `meta`, `metaurl` and
  `<COLLECTION>*` attributes. This means that as model updates are made, the
  model MUST change to align with the new set of Groups, Resources and their
  definition (e.g. `<RESOURCE>` attributes would (dis)appear based on the
  value of the `hasdocument` aspect). While the top-level attributes MUST
  appear, their definitions MAY be shallow - meaning, as an example, `model`
  itself can be defined as just `object` with just one attribute (`*`) of
  type "any".

The response MUST be of the form:

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "labels": { "<STRING>": "<STRING>" * }, ?
  "attributes": {
    "<STRING>": {
      "name": "<STRING>",
      "type": "<TYPE>",
      "target": "<XIDTYPE>", ?
      "namecharset": "<STRING>", ?
      "description": "<STRING>", ?
      "enum": [ <VALUE> * ], ?
      "strict": <BOOLEAN>, ?
      "readonly": <BOOLEAN>, ?
      "immutable": <BOOLEAN>, ?
      "required": <BOOLEAN>, ?
      "default": <VALUE>, ?

      "attributes": { ... }, ?
      "item": { ... }, ?

      "ifvalues": {
        "<STRING>": {
          "siblingattributes": { ... }
        } *
      } ?
    } *
  },

  "groups": {
    "<STRING>": {
      "plural": "<STRING>",
      "singular": "<STRING>",
      "description": "<STRING>", ?
      "documentation": "<URL>", ?
      "icon": "<URL>", ?
      "labels": { "<STRING>": "<STRING>" * }, ?
      "modelversion": "<STRING>", ?
      "compatiblewith": "<URI>", ?
      "attributes": { ... }, ?
      "ximportresources": [ "<XIDTYPE>", * ], ?

      "resources": {
        "<STRING>": {
          "plural": "<STRING>",
          "singular": "<STRING>",
          "description": "<STRING>", ?
          "documentation": "<URL>", ?
          "icon": "<URL>", ?
          "labels": { "<STRING>": "<STRING>" * }, ?
          "modelversion": "<STRING>", ?
          "compatiblewith": "<URI>", ?
          "maxversions": <UINTEGER>, ?
          "setversionid": <BOOLEAN>, ?
          "setdefaultversionsticky": <BOOLEAN>, ?
          "hasdocument": <BOOLEAN>, ?
          "versionmode": "<STRING>", ?
          "singleversionroot": <BOOLEAN>, ?
          "typemap": <MAP>, ?
          "attributes": { ... }, ?
          "resourceattributes": { ... }, ?
          "metaattributes": { ... } ?
        } *
      } ?
    } *
  } ?
}
```

**Examples:**

Retrieve a Registry model that has one extension attribute on the
`endpoints` Group, and allow any extension on Resource Versions:

```yaml
GET /model
```

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "attributes": {
    ... xRegistry spec-defined attributes excluded for brevity ...
  },
  "groups": {
    "endpoints": {
      "plural": "endpoints",
      "singular": "endpoint",
      ... xRegistry spec-defined aspects excluded for brevity ...
      "attributes": {
        ... xRegistry spec-defined attributes excluded for brevity ...
        "shared": {
          "name": "shared",
          "type": "boolean"
        }
      },

      "resources": {
        "messages": {
          "plural": "messages",
          "singular": "message",
          "attributes": {
            ... xRegistry spec-defined attributes excluded for brevity ...
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

#### Creating or Updating the Registry Model

To create, or update, the model of a Registry, the new model definition MAY
be provided to the server via one of two mechanisms:
- The `PUT /modelsource` API.
- The `modelsource` attribute MAY be included on a `PUT /` API request.

In both cases, the input JSON object MUST align with the pseudo JSON format
of the model as specified above. It MAY include as much of the full model
as the user would like to specify, but as stated previously, it is RECOMMENDED
that it only include the domain-specific aspects that need to be added to the
specification-defined features. This will keep the input small and more easily
managed if updates need to be made.

The response of a successful `PUT /modelsource` MUST be the same as the result
of a `GET /modelsource` API call.

The following sample model definition defines one Group type (`dirs`) that
contains one Resource type (`files`), which also has one attribute called
`owner` (a string):

```yaml
"modelsource": {
  "groups": {
    "dirs": {
      "singular": "dir",
      "resources": {
        "files": {
          "singular": "file"
          "attributes": {
            "owner": {
              "type": "string"
            }
          }
        }
      }
    }
  }
}
```

To enable support for a wide range of use cases, but to also ensure
interoperability across implementations, the following rules have been defined
with respect to how models are defined or updated:
- Changes to specification-defined attributes MAY be included in the model but
  MUST NOT change them such that they become incompatible with the
  specification. For example, changes to further constrain the allowable values
  of an attribute is typically allowed, but changing its `type` from `string`
  to `int` is not.
- Specification-defined attributes that are `required` MUST NOT have this
  aspect changed to `false`.
- Specification-defined attributes that are `readonly` MUST NOT have this
  aspect changed to `false`.

Any specification attributes not included in a request to define, or update,
a model MUST be included in the resulting full model. In other words, the full
Registry's model consists of the specification-defined attributes overlaid
with the attributes that are explicitly-defined as part of a "modelsource"
update request.

Note: there is no mechanism defined to delete specification-defined attributes
from the model.

Registries MAY support extension attributes to the model language (meaning,
new attributes within the model definitions themselves), but only if
the server supports them. Servers MUST generate an error
([model_error](#model_error)) if a model definition includes unknown model
language attributes.

Once a Registry has been created, changes to the model MAY be supported by
server implementations. This specification makes no statement as to what types
of changes are allowed beyond the following requirements:
- Any model changes MUST result in a specification compliant model definition.
- Servers MUST ensure that the representation of all entities within the
  Registry adhere to the current model prior to completing the model update
  request.

Any request to update the model that does not adhere to those requirements
MUST generate an error ([model_compliance_error](#model_compliance_error)).

How the server guarantees that all entities in the Registry are compliant with
the model is an implementation detail. For example, while it is
NOT RECOMMENDED, it is valid for an implementation to modify (or even delete)
existing entities to ensure model compliance. Instead, it is RECOMMENDED that
the model update requests generate an error
([model_compliance_error](#model_compliance_error)) if existing entities are
not compliant.

For the purposes of validating that the existing entities in the Registry are
compliant with the model, the mechanisms used to define the model (e.g.
`$include` vs `ximportresources` vs defined locally) MUST NOT impact that
analysis. In other words, model updates that have no semantic changes but
rather switch between one of those 3 mechanisms MUST NOT invalidate any
existing entities in the Registry.

Additionally, it is STRONGLY RECOMMENDED that model updates be limited to
backwards compatible changes.

Implementations MAY choose to limit the types of changes made to the model,
or not support model updates at all.

The xRegistry schema (model definition) used to create a sample xRegistry can
be found [here](./sample-model.json), while the resulting "full" model (with
all of the system-defined aspects added) can be found
[here](./sample-model-full.json).

##### Reuse of Resource Definitions

When a Resource type definition is to be shared between Groups, rather than
creating a duplicate Resource definition, the `ximportresources` mechanism MAY
be used instead. The `ximportresources` attribute on a Group definition
allows for a list of `<XIDTYPE>` references to other Resource types that are
to be included within this Group.

For example, the following abbreviated model definition defines
one Resource type (`messages`) under the `messagegroups` Group, that is
also used by the `endpoints` Group.

```yaml
"modelsource": {
  "groups": {
    "messagegroups": {
      "singular": "messagegroup",
      "resources": {
        "messages": {
          "singular": "message"
        }
      }
    },
    "endpoints": {
      "singular": "endpoint",
      "ximportresources": [ "/messagegroups/messages" ]
    }
  }
}
```

The format of the `ximportresources` specification is:

```yaml
"ximportresources": [ "<XIDTYPE>", * ]
```

where:
- Each array value MUST be an `<XIDTYPE>` reference to another Group/Resource
  combination defined within the same Registry. It MUST NOT reference the
  same Group under which the `ximportresources` resides.
- An empty array MAY be specified, implying no Resources are imported.
- The definition of a Group MAY include an `ximportresources` directive
  that references a Resource from another Group that itself is defined
  via an `ximportresources`. However, transitive definitions of Resources
  MUST NOT result in a circular import chain.

Locally defined Resources MAY be defined within a Group that uses the
`ximportresources` feature, however, Resource `plural` and `singular` values
MUST be unique across all imported and locally defined Resources.

See [Cross Referencing Resources](#cross-referencing-resources) for more
additional information.

##### Includes in the xRegistry Model Data

There might be times when it is necessary for an xRegistry model to reuse
portions of another xRegistry model defined elsewhere. Rather than forcing
the duplication of the model definitions, an "include" type of JSON directive
MAY be used.

The general formats of the include are:
```yaml
"$include": "<PATH-TO-DOCUMENT>#<JSON-POINTER-IN-DOC>"
```
or
```yaml
"$includes": [ "<PATH-TO-DOCUMENT>#<JSON-POINTER-IN-DOC>" * ]
```
where the first form specifies a single reference to be included, and the
second form specifies multiple. The fragment (`#...`) portion is OPTIONAL.

For example:
```yaml
"$include": "http://example.com/xreg-model.json#/groups/mygroup/attributes"
```
is asking for the attributes of a Group called `mygroup` to be included at
this location of the current model definition.

These directives MAY be used in any JSON Object or Map entity in an
xRegistry model definition. The following rules apply for how to process the
include directive:
- The include path reference value MUST be compatible with the environment in
  which the include is being evaluated. For example, in an xRegistry server it
  would most likely always be a URL. However, in an external tool the reference
  might be to a local file on disk or a URL.
- The include MUST reference a JSON Object or Map that is consistent with
  the model definition of where the include appears, and the target attributes,
  or keys, are processed in place of the `$include` attribute.
- Any attributes already present (as siblings to the include) MUST take
  precedence over an included attribute - matching is done via comparing
  the `name` of the attributes.
- When `$includes` is used, the references MUST be processed in order and
  earlier attributes included take precedence over subsequently included
  attributes.
- Both `$include` and `$includes` MUST NOT be present at the same time at the
  same level in the model.
- Included model definitions MAY use `include` directives, but MUST NOT be
  recursive.
- Resolution of the include path MUST follow standard path resolution.
  Meaning, relative paths are relative to the document with the include
  directive.
- If present, the fragment (`#...`) part of the reference MUST adhere to the
  [JSON Pointer](https://datatracker.ietf.org/doc/html/rfc6901) specification.

When the directives are used in a request to update the model, the server MUST
resolve all includes prior to updating the model. The original (source)
model definition, with any "include" directives, MUST be available via
the `modelsource` attribute and the expanded model (after the resolution of
any includes, and after all specification-defined attributes have been added)
MUST be available via the `model` attribute. The directives MUST only be
processed once. In order to have them re-evaluated, a subsequent model
update request (with those directive) MUST be sent via the `modelsource`
attribute.

When there is tooling used outside of the server, e.g. in an xRegistry
client, if that tooling resolves the "include" directives prior to sending
the model to the server, then the directives will not appear in the
`modelsource` view of the the model. Ideally, tooling SHOULD allow users
to choose whether the resolution of the directives are done locally or by
the server.

**Examples:**

A model definition that includes xRegistry attributes from a file on a remote
server, and adds the definition of one attribute to a Group named `mygroups`
from an external Group named `group1` in another xRegistry.

```yaml
{
  "attributes": {
    "$include": "http://example.com/someattributes",
    "myattribute": {
      "name": "myattribute",
      "type": "string"
    }
  }
  "groups": {
    "mygroups": {
      "singular": "mygroup",
      "attributes": {
        "attr1": {
          "$include": "http://example.com/model#/groups/group1/attributes/attr1"
        }
        ... remainder of model excluded for brevity ...
      }
    }
  }
}
```

where `http://example.com/someattributes` might look like:

```yaml
{
  "myattr": {
    "name": "myattr",
    "type": "string"
  }
}
```

and the second include target might look like:

```yaml
{
  "name": "attr1",
  "type": "string"
}
```

---

### Exporting

The `/export` API MUST be an alias for
`GET /?doc&inline=*,capabilities,modelsource". If supported, it MUST NOT
support any HTTP update methods. This API was created:
- As a shorthand convenience syntax for clients that need to download the
  entire Registry as a single document. For example, to then be used in an
  "import" type of operation for another Registry, or for tooling that
  does not need the duplication of information that `?doc` removes.
- To allow for servers that do not support query parameters (such as
  [No-Code Servers](#no-code-servers)) to expose the entire Registry with a
  single API call.

Query parameters MAY be included on the request and any `?inline` flag
specified MUST override the default value defined above.

---

### Groups APIs

Groups represent entities that typically act as a collection mechanism for
related Resources. However, it is worth noting that Groups do not have to have
Resources associated with them. It is possible to have Groups be the main (or
only) entity of a Registry. Each Group type MAY have any number of Resource
types within it. This specification does not define how the Resources within a
Group type are related to each other.

The serialization of a Group entity adheres to this form:

```yaml
{
  "<GROUP>id": "<STRING>",
  "self": "<URL>",
  "shortself": "<URL>", ?
  "xid": "<XID>",
  "epoch": <UINTEGER>,
  "name": "<STRING>", ?
  "description": "<STRING>", ?
  "documentation": "<URL>", ?
  "icon": "<URL>", ?
  "labels": { "<STRING>": "<STRING>" * }, ?
  "createdat": "<TIMESTAMP>",
  "modifiedat": "<TIMESTAMP>",

  # Repeat for each Resource type in the Group
  "<RESOURCES>url": "<URL>",                  # e.g. "messagesurl"
  "<RESOURCES>count": <UINTEGER>,             # e.g. "messagescount"
  "<RESOURCES>": { Resources collection } ?   # If inlined
}
```

Groups include the following
[common attributes](#common-attributes):
- [`<GROUP>id`](#singularid-id-attribute) - REQUIRED in API and document views.
  OPTIONAL in requests.
- [`self`](#self-attribute) - REQUIRED in API and document views.
  OPTIONAL/ignored in requests.
- [`shortself`](#shortself-attribute) - OPTIONAL in API and document views,
  based on the `shortself` capability. OPTIONAL/ignored in requests.
- [`xid`](#xid-attribute) - REQUIRED in API and document views.
  OPTIONAL/ignored in requests.
- [`epoch`](#epoch-attribute) - REQUIRED in API and document views. OPTIONAL in
  requests.
- [`name`](#name-attribute) - OPTIONAL.
- [`description`](#description-attribute) - OPTIONAL.
- [`documentation`](#documentation-attribute) - OPTIONAL.
- [`icon`](#icon-attribute) - OPTIONAL.
- [`labels`](#labels-attribute) - OPTIONAL.
- [`createdat`](#createdat-attribute) - REQUIRED in API and document views.
  OPTIONAL in requests.
- [`modifiedat`](#modifiedat-attribute) - REQUIRED in API and document views.
  OPTIONAL in requests.

and the following Group-level attributes:

##### `<RESOURCES>` Collections
- Type: Set of [Registry Collections](#registry-collections).
- Description: A list of Registry collections that contain the set of
  Resources supported by the Group.

- Constraints:
  - REQUIRED.
  - It MUST include all nested Resource Collection types of the owning Group,
    even if some of the collections are empty.

#### Retrieving a Group Collection

To retrieve a Group collection, an HTTP `GET` MAY be used.

The request MUST be of the form:

```yaml
GET /<GROUPS>
```

A successful response MUST be of the form:

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Link: <URL>;rel=next;count=<UINTEGER> ?

{
  "<KEY>": {                                     # <GROUP>id
    "<GROUP>id": "<STRING>",
    "self": "<URL>",
    "shortself": "<URL>", ?
    "xid": "<XID>",
    "epoch": <UINTEGER>,
    "name": "<STRING>", ?
    "description": "<STRING>", ?
    "documentation": "<URL>", ?
    "icon": "<URL>", ?
    "labels": { "<STRING>": "<STRING>" * }, ?
    "createdat": "<TIMESTAMP>",
    "modifiedat": "<TIMESTAMP>",

    # Repeat for each Resource type in the Group
    "<RESOURCES>url": "<URL>",                  # e.g. "messagesurl"
    "<RESOURCES>count": <UINTEGER>,             # e.g. "messagescount"
    "<RESOURCES>": { Resources collection } ?   # If inlined
  } *
}
```

**Examples:**

Retrieve all entities in the `endpoints` Group collection:

```yaml
GET /endpoints
```

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Link: <https://example.com/endpoints&page=2>;rel=next;count=100

{
  "ep1": {
    "endpointid": "ep1",
    "self": "https://example.com/endpoints/ep1",
    "xid": "/endpoints/ep1",
    "epoch": 1,
    "name": "A cool endpoint",
    "createdat": "2024-04-30T12:00:00Z",
    "modifiedat": "2024-04-30T12:00:01Z",

    "messagesurl": "https://example.com/endpoints/ep1/messages",
    "messagescount": 5
  },
  "ep2": {
    "endpointid": "ep2",
    "self": "https://example.com/endpoints/ep2",
    "xid": "/endpoints/ep2",
    "epoch": 3,
    "name": "Redis Queue",
    "createdat": "2024-04-30T12:00:00Z",
    "modifiedat": "2024-04-30T12:00:01Z",

    "messagesurl": "https://example.com/endpoints/ep2/messages",
    "messagescount": 1
  }
}
```

Notice that the `Link` HTTP header is present, indicating that there
is a second page of results that can be retrieved via the specified URL,
and that there are a total of 100 items in this collection.

#### Creating or Updating Groups

Creating or updating Groups via HTTP MAY be done by using the HTTP `PUT`,
`PATCH` or `POST` methods:
- `PUT   /<GROUPS>/<GID>`   # Create/update a single Group
- `PATCH /<GROUPS>/<GID>`   # Create/update a single Group
- `PATCH /<GROUPS>`         # Create/update multiple Groups of type `<GROUPS>`
- `POST  /<GROUPS>`         # Create/update multiple Groups of type `<GROUPS>`

The processing of the above APIs is defined in the [Creating or Updating
Entities](#creating-or-updating-entities) section.

- `POST  /`                 # Create/update multiple Groups of varying types

This API is very similar to the `POST /<GROUPS>` above, except that the HTTP
body MUST be a map of Group types as shown in the example below:

```yaml
{
  "endpoints": {
    "endpoint1": { ... Group endpoint1's xRegistry metadata ... },
    "endpoint2": { ... Group endpoint2's xRegistry metadata ... }
  },
  "schemagroups": {
    "schemagroup1": { ... Group schemagroup1's xRegistry metadata ... },
    "schemagroup2": { ... Group schemagroup2's xRegistry metadata ... }
  }
}
```

Notice the format is almost the same as what a `PUT /` would look like if the
request wanted to update the Registry's attributes and define a set of Groups,
but without the Registry's attributes. This allows for an update of the
specified Groups without modifying the Registry's attributes.

The response in this case MUST be a map of the Group types with just the
Groups that were processed as part of the request.

For all of the above APIs, each individual Group definition in a request
MUST adhere to the following:

```yaml
{
  "<GROUP>id": "<STRING>", ?
  "self": "<URL>", ?
  "shortself": "<URL>", ?
  "xid": "<XID>", ?
  "epoch": <UINTEGER>, ?
  "name": "<STRING>", ?
  "description": "<STRING>", ?
  "documentation": "<URL>", ?
  "icon": "<URL>", ?
  "labels": { "<STRING>": "<STRING>" * }, ?
  "createdat": "<TIMESTAMP>", ?
  "modifiedat": "<TIMESTAMP>", ?

  # Repeat for each Resource type in the Group
  "<RESOURCES>": { Resources collection } ?
}
```

Each individual Group in a successful response MUST adhere to the following:

```yaml
{
  "<GROUP>id": "<STRING>",
  "self": "<URL>",
  "shortself": "<URL>", ?
  "xid": "<XID>",
  "epoch": <UINTEGER>,
  "name": "<STRING>", ?
  "description": "<STRING>", ?
  "documentation": "<URL>", ?
  "icon": "<URL>", ?
  "labels": { "<STRING>": "<STRING>" * }, ?
  "createdat": "<TIMESTAMP>",
  "modifiedat": "<TIMESTAMP>",

  # Repeat for each Resource type in the Group
  "<RESOURCES>url": "<URL>",                    # e.g. "messagesurl"
  "<RESOURCES>count": <UINTEGER>,               # e.g. "messagescount"
  "<RESOURCES>": { Resource collection }?       # If inlined
}
```

**Examples:**

Targeted request to create a specific Group by `<GROUP>id`:

```yaml
PUT /endpoints/ep1
Content-Type: application/json; charset=utf-8

{
  "endpointid": "ep1",
  ... remainder of Endpoint 'ep1' definition ...
}
```

```yaml
HTTP/1.1 201 Created
Content-Type: application/json; charset=utf-8
Location: https://example.com/endpoints/ep1

{
  "endpointid": "ep1",
  ... remainder of Endpoint 'ep1' definition ...
}
```

Multiple Groups specified in the HTTP body:

```yaml
POST /endpoints
Content-Type: application/json; charset=utf-8

{
  "ep1": {
    "endpointid": "ep1",
    ... remainder of ep1 definition ...
  },
  "ep2": {
    "endpointid": "ep2",
    ... remainder of ep2 definition ...
  }
}
```

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "ep1": {
    "endpointid": "ep1",
    ... remainder of ep1 definition ...
  },
  "ep2": {
    "endpointid": "ep2",
    ... remainder of ep2 definition ...
  }
}
```

#### Retrieving a Group

To retrieve a Group, an HTTP `GET` MAY be used.

The request MUST be of the form:

```yaml
GET /<GROUPS>/<GID>
```

A successful response MUST be of the form:

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "<GROUP>id": "<STRING>",
  "self": "<URL>",
  "shortself": "<URL>", ?
  "xid": "<XID>",
  "epoch": <UINTEGER>,
  "name": "<STRING>", ?
  "description": "<STRING>", ?
  "documentation": "<URL>", ?
  "icon": "<URL>", ?
  "labels": { "<STRING>": "<STRING>" * }, ?
  "createdat": "<TIMESTAMP>",
  "modifiedat": "<TIMESTAMP>",

  # Repeat for each Resource type in the Group
  "<RESOURCES>url": "<URL>",                   # e.g. "messagesurl"
  "<RESOURCES>count": <UINTEGER>,              # e.g. "messagescount"
  "<RESOURCES>": { Resources collection } ?    # If inlined
}
```

**Examples:**

Retrieve a single `endpoints` Group:

```yaml
GET /endpoints/ep1
```

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "endpointid": "ep1",
  "self": "https://example.com/endpoints/ep1",
  "xid": "/endpoints/ep1",
  "epoch": 1,
  "name": "myEndpoint",
  "createdat": "2024-04-30T12:00:00Z",
  "modifiedat": "2024-04-30T12:00:01Z",

  "messagesurl": "https://example.com/endpoints/ep1/messages",
  "messagescount": 5
}
```

#### Deleting Groups

To delete one or more Groups, an HTTP `DELETE` MAY be used:
- `DELETE /<GROUPS>/<GID>[?epoch=<UINTEGER>]`
- `DELETE /<GROUPS>`

The processing of these two APIs is defined in the [Deleting Entities in a
Registry Collection](#deleting-entities-in-a-registry-collection)
section.

---

### Resources APIs

Resources typically represent the main entity that the Registry is managing.
Each Resource is associated with a Group to aid in their discovery and to show
a relationship with Resources in that same Group. Resources appear within the
Group's `<RESOURCES>` collection.

Resources, like all entities in the Registry, can be modified but Resources
can also have a version history associated with them, allowing for users to
retrieve previous Versions of the Resource. In this respect, Resources have
a 2-layered definition. The first layer is the Resource entity itself,
and the second layer is its `versions` collection - the version history of
the Resource.

The Resource entity serves three purposes:
1 - It represents the collection for the historical Versions of the data being
    managed. This is true even if the Resource type is defined to not use
    versioning, meaning the number of Versions allowed is just one. The
    Versions will appear as a nested entity under the `versions` attribute.<br>
2 - It acts as an alias for the "default" Version of the Resource. Most
    operations directed at the URL of the Resource will act upon that Version,
    not the Resource itself. See
    [Default Version of a Resource](#default-version-of-a-resource) and
    [Versions](#versions-apis) for more details.<br>
3 - It has a set of attributes for Resource-level metadata - data that is not
    specific to one Version of the Resource but instead applies to the
    Resource in general. These attributes appear under a `meta`
    attribute/sub-object so as to keep them separate from any Version-level
    attributes. Note that these attributes do not appear on the Versions.

The URL of a Resource can be thought of as an alias for the "default"
Version of the Resource, and as such, most of the attributes shown when
processing the Resource will be mapped from the "default" Version.

However, there a few exceptions:
- `self` MUST be a URL to the Resource, and not to the "default"
  Version in the `versions` collection. The Resource's `defaultversionurl`
  attribute (in the `meta` sub-object) can be used to locate the "default"
  Version.
- `shortself`, if present, MUST be an alternative URL for `self`.
- `xid` MUST be a relative URI to the Resource, and not to the "default"
  Version in the `versions` collection.
- A few extra attributes will appear to help with the navigation of the
  Resource. For example, a URL to the `meta` sub-object and the `versions`
  Collection attributes.

The remainder of this section discusses the processing rules for Resources
and Versions. While it mainly uses the term "Resource" for ease of reading, in
most cases it can be assumed that the same processing applies for "Versions".
When this is not the case, it will be explicitly called out.

#### Resource Metadata vs Resource Document

Unlike Groups, which consist entirely of xRegistry managed metadata, Resources
typically have their own domain-specific data and document format that needs
to be kept distinct from the xRegistry Resource metadata. As discussed
previously, the model definition for Resources has a `hasdocument` attribute
indicating whether a Resource type defines its own separate document or not.

This specification does not define any requirements for the contents of this
separate document, and it doesn't even need to be stored within the Registry.
The Resource MAY choose to simply store a URL reference to the externally
managed document instead. When the document is stored within the Registry, it
can be managed as an opaque array of bytes.

When a Resource does have a separate document, HTTP interactions to the URL
for the Resource MUST include this document in the HTTP body as it is typically
the data of interest for end users. As a convenance, the simple (mainly
scalar) xRegistry metadata of the Resource will appear as HTTP headers.

To change this view such that the xRegistry metadata becomes the data of
interest, the request URLs MUST have `$details` appended to them. In these
cases, the HTTP body of the requests and responses MUST have a JSON
serialization of the entity's xRegistry metadata, and the separate document
MAY appear as an attribute within that metadata based on the specific
operation.

For example:

```yaml
GET https://example.com/schemagroups/mygroup/schemas/myschema
```
will retrieve the schema document associated with the `myschema` Resource,
while:

```yaml
GET https://example.com/schemagroups/mygroup/schemas/myschema$details
```
will retrieve the xRegistry metadata information for the `myschema` Resource.

When the Resource's path is appended with `$details`, the Resource's document
becomes available via a set of `<RESOURCE>*` attributes within that metadata:

- `<RESOURCE>`: this attribute MUST be used when the contents of the Resource's
  document are stored within the Registry and its "array of bytes" can be
  used directly in the serialization of the Resource metadata "as is". Meaning,
  in the JSON case, those bytes can be parsed as a JSON value without any
  additional processing (such as escaping). This is a convenience
  (optimization) attribute to make it easier to view the document when it
  happens to be in the same format as the xRegistry itself.

  The model Resource attribute `typemap` MAY be used to help the server
  determine which `contenttype` values are of the same format - see
  [Registry Model](#registry-model) for more information. If a Resource has
  a matching `contenttype` but the contents of the Resource's document do not
  successfully parse (e.g. it's `application/json` but the JSON is invalid),
  then `<RESOURCE>` MUST NOT be used and `<RESOURCE>base64` MUST be used
  instead.

- `<RESOURCE>base64`: this attribute MUST be used when the contents of the
  Resource are stored within the Registry but `<RESOURCE>` cannot be used.
  The Resource's document is base64 encoded and serialized as a string.

- `<RESOURCE>url`: this attribute MUST be used when the Resource is stored
  external to the Registry. Its value MUST be a URL that can be used to
  retrieve its contents via an HTTP(s) `GET`. There is no requirement for the
  server to validate this URL.

When accessing a Resource's metadata with `$details`, often it is to
view or update the xRegistry metadata and not the document, as such, including
the potentially large amount of data from the Resource's document in request
and response messages could be cumbersome. To address this, the `<RESOURCE>`
and `<RESOURCE>base64` attributes do not appear by default as part of the
serialization of the Resource. Rather, they MUST only appear in responses when
the [`?inline=<RESOURCE>`](#inline-flag) query parameter is used. Likewise, in
requests, these attributes are OPTIONAL and would only need to be used when a
change to the document's content is needed at the same time as updates to the
Resource's metadata. However, the `<RESOURCE>url` attribute MUST always appear
if it has a value.

Note that the serialization of a Resource MUST only use at most one of these 3
attributes at a time.

Client and server implementations MUST be prepared for any of these 3
attributes to be used. In the case of `RESOURCE` or `RESOURCEbase64`,
implementations can not assume that a previous use of one means that all
subsequent messages of that entity will use the same attribute. For example,
a client can use `RESOURCE` to populate the value, but the server is free
to use `RESOURCEbase64` when returning the data.

#### Resource Attributes

Resource attributes are non-versioned attributes associated with a Resource.
In a sense they can be considered to be global to the Resource and its
Versions, but they are not part of, or serialized in, any Version. Instead,
they are serialized in two different ways:

1 - some will appear within a `meta` attribute/sub-object to the Resource.
    This keeps them separate from the default Version attributes that might
    appear. However, the `meta` attribute itself will appear as a sibling to
    the default Version attributes. Note that `meta` will only be
    serialized when requested by the client.

2 - some will appear as siblings to the default Version attributes within the
    Resource serialization. These appear here, rather than under `meta`,
    because they are specifically designed to help with the traversal of the
    Resource's hierarchy and putting them "one level down" would reduce their
    usefulness.

When the Resource is serialized as a JSON object, the serialization of the
Resource attribute MUST adhere to the following:

```yaml
{
  "<RESOURCE>id": "<STRING>",
  "versionid": "<STRING>",
  "self": "<URL>",                           # URL to Resource, not Version
  "shortself": "<URL>", ?
  "xid": "<XID>",                            # Relative URI to Resource
  # Default Version attributes appear here

  "metaurl": "<URL>",                        # Same as "meta.self" below
  "meta": {                                  # Only if inlined
    "<RESOURCE>id": "<STRING>",
    "self": "<URL>",                         # Absolute Meta URL, not Version
    "shortself": "<URL>", ?
    "xid": "<XID>",                          # Relative Meta URI, not Version
    "xref": "<XID>", ?                       # Ptr to linked Resource
    "epoch": <UINTEGER>,                     # Resource's epoch
    "createdat": "<TIMESTAMP>",              # Resource's
    "modifiedat": "<TIMESTAMP>",             # Resource's
    "readonly": <BOOLEAN>,                   # Default=false
    "compatibility": "<STRING>",             # Default=none
    "compatibilityauthority": "<STRING>", ?  # Default=external
    "deprecated": { ... }, ?

    "defaultversionid": "<STRING>",
    "defaultversionurl": "<URL>",            # Absolute URL to default Version
    "defaultversionsticky": <BOOLEAN>        # Default=false
  }, ?
  "versionsurl": "<URL>",
  "versionscount": <UINTEGER>,
  "versions": { map of Versions }            # Only if inlined
}
```

Note that the `meta` and `versions` attributes MUST only appear when
requested by the client - for example, via the `?inline` flag.

When the Resource is serialized with its domain-specific document in the
HTTP body, then Resource-level attributes SHOULD appear as HTTP headers and
adhere to the following:

```yaml
xRegistry-<RESOURCE>id: <STRING>
xRegistry-versionid: <STRING>
xRegistry-self: <URL>
xRegistry-xid: <XID>
# Default Version attributes, and other HTTP headers, appear here
xRegistry-metaurl: <URL>
xRegistry-versionsurl: <URL>
xRegistry-versionscount: <UINTEGER>
```

Notice the `meta` and `versions` attributes are not included since they are
not complex data types.

The Resource-level attributes include the following
[common attributes](#common-attributes):
- [`<RESOURCE>id`](#singularid-id-attribute) - REQUIRED in API and document
  views. OPTIONAL in requests.
- [`self`](#self-attribute) - REQUIRED in API and document views.
  OPTIONAL/ignored in requests.
- [`shortself`](#shortself-attribute) - OPTIONAL in API and document views,
  based on the `shortself` capability. OPTIONAL/ignored in requests.
- [`xid`](#xid-attribute) - REQUIRED in API and document views.
  OPTIONAL/ignored in requests.

and the following Resource-level attributes:

##### `xref` Attribute
- Type: XID
- Description: indicates that this Resource is a reference to another Resource
  within the same Registry. See [Cross Referencing
  Resources](#cross-referencing-resources) for more information.

- Constraints:
  - OPTIONAL.
  - If present, it MUST be the `xid` of a same-typed Resource in the Registry.

##### `readonly` Attribute
- Type: Boolean
- Description: indicates whether this Resource is updateable by clients. This
  attribute is a server-controlled attribute and therefore cannot be modified
  by clients. This specification makes no statement as to when Resources are to
  be read-only.

- Constraints:
  - REQUIRED.
  - MUST be a read-only attribute.
  - When not specified, the default value MUST be `false`.
  - It MUST be a case-sensitive `true` or `false`.
  - A request to update a read-only Resource MUST generate an error
    ([readonly](#readonly)) unless the `?ignorereadonly` query parameter was
    used, in which case the error MUST be silently ignored. See
    [Registry HTTP APIs](#registry-http-apis) for more information.

##### `compatibility` Attribute
- Type: String (with Resource-specified enumeration of possible values)
- Description: States that Versions of this Resource adhere to a certain
  compatibility rule. For example, a "backward" compatibility value would
  indicate that all Versions of a Resource are backwards compatible with the
  next oldest Version, as determined by their `ancestor` attributes.

  This specification makes no statement as to which parts of the data are
  examined for compatibility (e.g. xRegistry metadata, domain-specific
  document, etc.). This SHOULD be defined by the `compatibility` values.
  The exact meaning of what each `compatibility` value means might vary based
  on the data model of the Resource, therefore this specification only defines
  a very high-level abstract meaning for each to ensure some degree of
  consistency. However, domain-specific specifications are expected to
  modify the `compatibility` enum values defined in the Resource's model to
  limit the list of available values and to define the exact meaning of each.
  Implementations MUST include `none` as one of the possible values and when
  set to `none` then compatibility checking MUST NOT be performed.

  If the `compatibilityauthority` attribute is set to `server` then
  implementations of this specification are REQUIRED to perform the proper
  compatibility checks to ensure that all Versions of a Resource adhere to the
  rules defined by the current value of this attribute.
  For `compatibility` strategies that require understanding the sequence in
  which Versions need to be compatible, the server MUST use the
  [`ancestor`](#ancestor-attribute) to determine the sequence of Versions.

  Note that, like all attributes, if a default value is defined as part of the
  model, then this attribute MUST be populated with that value if no value
  is provided.

  This specification defines the following enumeration values. Implementations
  MAY choose to extend this list, or use a subset of it.
  - `backward` - A Version is compatible with the next oldest Version.
  - `backward_transitive` - A Version is compatible with all older Versions.
  - `forward` - A Version is compatible with the next newest Version.
  - `forward_transitive` - A Version is compatible with all newer Versions.
  - `full` - A Version is compatible with the next oldest and next newest
    Versions.
  - `full_transitive` - A Version is compatible with all older and all newer
    Versions.
  - `none` - No compatibility checking is performed.

- Constraints:
  - REQUIRED.
  - It MUST be a case-sensitive value from the model-defined enumeration range.
  - When not specified, the default value MUST be `none`.
  - The enumeration range MUST include `none` as a valid value.
  - If the `compatibilityauthority` attribute is set to `server`, when
    changing the `compatibility` attribute, the server MUST validate whether
    the new `compatibility` value can be enforced across all existing
    Versions. If that's not the case, the server MUST generate an error
    ([compatibility_violation](#compatibility_violation)).

#### `compatibilityauthority` Attribute
- Name: `compatibilityauthority`
- Type: String
- Description: Indicates the authority that enforces the `compatibility`
  value defined by the owning Resource.

  This specification defines the following enumeration values. Implementations
  MAY choose to extend this list.
  - `external` - The compatibility is enforced by an external authority.
  - `server` - The compatibility is enforced by the server.

  The server MUST generate an error
  ([compatibility_violation](#compatibility_violation)) following any
  attempt to set the `compatibilityauthority` attribute to `server` if the
  server cannot enforce the compatibility for the Resource's Versions.

  When set to `server`, the server MUST generate an error
  ([compatibility_violation](#compatibility_violation)) following any
  attempt to create/update a Resource (or its Versions) that would result in
  those entities violating the stated compatibility statement.

  A value of `external` indicates that the server MUST NOT perform any
  compatibility checking and that the compatibility checking is performed by
  an external authority.

  Attempts to change this value to `server` MUST result in the validation of
  existing Versions.

- Constraints:
  - MUST be present when `compatibility` is not `none`.
  - MUST NOT be present when `compatibility` is `none`.
  - When not specified, and `compatibility` is not `none`, the default value
    MUST be `external`.
  - If present, MUST be non-empty.

#### `deprecated`

- Type: Object containing the following properties:
  - `effective`<br>
    An OPTIONAL property indicating the time when the Resource entered, or will
    enter, a deprecated state. The date MAY be in the past or future. If this
    property is not present the Resource is already in a deprecated state.
    If present, this MUST be an [RFC3339][rfc3339] timestamp.

  - `removal`<br>
    An OPTIONAL property indicating the time when the Resource MAY be removed.
    The Resource MUST NOT be removed before this time. If this property is not
    present, the client cannot make any assumptions as to when the Resource
    might be removed. Note: as with most properties, this property is mutable.
    If present, this MUST be an [RFC3339][rfc3339] timestamp and MUST NOT be
    sooner than the `effective` time if present.

  - `alternative`<br>
    An OPTIONAL property specifying the URL to an alternative Resource the
    client can consider as a replacement for this Resource. There is no
    guarantee that the referenced Resource is an exact replacement, rather the
    client is expected to investigate the Resource to determine if it is
    appropriate.

  - `docs`<br>
    An OPTIONAL property specifying the URL to additional information about
    the deprecation of the Resource. This specification does not mandate any
    particular format or information, however some possibilities include:
    reasons for the deprecation or additional information about likely
    alternative Resources. The URL MUST support an HTTP(s) GET request.

  Note that an implementation is not mandated to use this attribute in
  advance of removing a Resource, but is it RECOMMENDED that they do so.
- Constraints:
  - OPTIONAL
- Examples:
  - `"deprecated": {}`
  - ```
    "deprecated": {
      "removal": "2030-12-19T00:00:00Z",
      "alternative": "https://example.com/entities-v2/myentity"
    }
    ```

##### `defaultversionid` Attribute
- Type: String
- Description: the `versionid` of the default Version of the Resource.
  This specification makes no statement as to the format of this string or
  versioning scheme used by implementations of this specification. However, it
  is assumed that newer Versions of a Resource will have a "higher"
  value than older Versions.

- Constraints:
  - REQUIRED.
  - MUST be the `versionid` of the default Version of the Resource.
  - See the [`defaultversionsticky` Attribute](#defaultversionsticky-attribute)
    below for how to process these two attributes.

- Examples:
  - `1`, `2.0`, `v3-rc1` (v3's release candidate 1)

##### `defaultversionurl` Attribute
- Type: URL
- Description: a URL to the default Version of the Resource.

  This URL MUST NOT include the `$detail` suffix even if the Resource's
  `hasdocument` aspect is set to `true`.

- API View Constraints:
  - REQUIRED.
  - MUST be an absolute URL to the default Version of the Resource, and MUST
    be the same as the Version's `self` attribute.
  - MUST be a read-only attribute.

- Document View Constraints:
  - REQUIRED.
  - If the default Version is inlined in the document then this attribute
    MUST be a relative URL of the form `#JSON-POINTER` where the `JSON-POINTER`
    locates the default Version within the current document. See
    [Doc Flag](#doc-flag) for more information.
  - If the default Version is not inlined in the document, then this attribute
    MUST be an absolute URL per the API view constraints listed above.

- Examples:
  - `https://example.com/endpoints/ep1/messages/msg1/versions/1.0` (API View)
  - `#/endpoints/ep1/messages/msg1/versions/1.0` (Document View)

##### `defaultversionsticky` Attribute
- Type: Boolean
- Description: indicates whether or not the "default" Version has been
  explicitly set or whether the "default" Version is defaulting to the newest
  one (based on the Resource's
  [`versionmode`](#--model-groupsstringresourcesstringversionmode) algorithm).
  A value of `true` means that it has been explicitly set and the value of
  `defaultversionid` MUST NOT automatically change if Versions are added or
  removed. A value of `false` means the default Version MUST be the newest
  Version, as defined by the Resource's
  [`versionmode`](#--model-groupsstringresourcesstringversionmode) algorithm.

  When set to `true`, if the default Version is deleted, then without any
  indication of which Version is to become the new default Version, the
  sticky aspect MUST be disabled and the default Version MUST be the newest
  Version. See [Default Version of a Resource](#default-version-of-a-resource)
  for more information.

- Constraints:
  - REQUIRED.
  - When not specified, the default value MUST be `false`.
  - When specified, it MUST be a case-sensitive `true` or `false`.
  - When specified in a request, a value of `null` MUST be interpreted as a
    request to delete the attribute, implicitly setting it to `false`.
  - The processing of the `defaultversionsticky` and `defaultversionid`
    attributes are related, and is described as follows:
    - When `PATCH` is used but only one of the two attributes is specified
      in the request, then:
      - A non-`null` `defaultversionid` MUST result in processing as if
        `defaultversionsticky` has a value of `true`.
      - A `null` `defaultversionid` MUST result in processing as if
        `defaultversionsticky` has a value of `false`.
      - A `null` or `false` `defaultversionsticky` MUST result in processing
        as if `defaultversionid` has a value of `null`.
      - The processing then continues on the patched `meta` sub-object as if
        `PUT` or `POST` was used.
    - When `PUT` or `POST` is used:
      - A `null` or absent `defaultversionid` in the request MUST result in the
        same semantics as it referencing "the newest Version".
      - A `null` or absent `defaultversionsticky` in the request MUST result in
        the same semantics as it being set to `false`.
      - A `defaultversionid` referencing a non-existing Version MUST generate
        an error ([unknown_id](#unknown_id)).
      - If `defaultversionsticky` is `false` and `defaultversionid` does not
        reference the newest Version then an error
        ([invalid_data](#invalid_data)) MUST be generated, as this
        would result in an inconsistent state.
      - For clarity, if the net result of the processing is that the sticky
        feature is turned off, then the `defaultversionid` MUST reference the
        newest Version.

- Examples:
  - `true`, `false`

##### `metaurl` Attribute
- Type: URL
- Description: a server-generated URL to the Resource's `meta` sub-object.

  When specified, it MUST appear as an attribute of the Resource as a sibling
  to the Resource's default Version attributes.

- API View Constraints:
  - REQUIRED.
  - MUST be immutable.
  - MUST be an absolute URL to the Resource's `meta` sub-object.
  - MUST be a read-only attribute.

- Document View Constraints:
  - REQUIRED.
  - If the `meta` sub-object is inlined in the document then this attribute
    MUST be a relative URL of the form `#JSON-POINTER` where the `JSON-POINTER`
    locates the `meta` sub-object within the current document. See
    [Doc Flag](#doc-flag) for more information.
  - If the `meta` sub-object is not inlined in the document then this attribute
    MUST be an absolute URL per the API view constraints listed above.

- Examples:
  - `https://example.com/endpoints/ep1/messages/msg1/meta` (API view)
  - `#/endpoints/ep1/messages/msg1/meta` (Document view)

##### `meta` Attribute/Sub-Object
- Type: Object
- Description: an object that contains most of the Resource-level attributes.

  The `meta` sub-object is an entity in its own right, meaning it supports the
  `GET`, `PUT` and `PATCH` APIs as described for all entities within the
  xRegistry. It also has its own `epoch` value which adheres to the normal
  `epoch` processing rules already described, and its value is only updated
  when the `meta` attributes are updated.

  When specified, it MUST appear as an attribute of the Resource as a sibling
  to the Resource's default Version attributes.

- Constraints:
  - REQUIRED when requested by the client.
  - MUST NOT appear unless requested by the client.

Note: doing a `PUT` to a Resource, or a `POST` to an xRegistry Collection, as
a mechanism to update the `meta` sub-object MUST include the Resource
default Version attributes in the request. When not specified, the server will
interpret it as a request to delete the default Version attributes. If
possible, an update request to the `metaurl` directly would be a better
choice, or use `PATCH` instead and only include the `meta` sub-object.

During a write operation, the absence of the `meta` attribute indicates that
no changes are to be made to the `meta` sub-object.

##### `versions` Collection
- Type: [Registry Collection](#registry-collections)
- Description: The set of xRegistry Collection attributes related to the
  Versions of the Resource.

  Note that Resources MUST have at least one Version.

- Constraints:
  - REQUIRED.

#### Serializing Resources

Serializing Resources requires some special processing due to Resources not
representing just a single set of data. In particular, the following
aspects need to be taken into account:
- Operations directed to the URL of a Resource are actually acting upon the
  "default" Version of that Resource.
- Management of the Resource's xRegistry metadata needs to be separate from the
  management of any particular Version of the Resource, as well as any
  potential domain-specific document associated with the Resource/Version.
- The actions, and learning, necessary for end-users to access the most likely
  "data of interest" needs to be minimal.

To address these aspects, the serialization of a Resource will vary based
on whether it is defined to have a domain-specific document and whether the
client wishes to focus on managing its xRegistry metadata or that secondary
document.

As discussed above, there are two ways to serialize a Resource in an HTTP
message's body:
- As its underlying domain-specific document.
- As its xRegistry metadata.

Which variant is used is most often controlled by the use of `$details` on
the URL path. The following sections go into more details about these two
serialization options.

##### Serializing Resource Documents

When a Resource is serialized as its underlying domain-specific document,
in other words `$details` is not appended to its URL path, the HTTP body of
requests and responses MUST be the exact bytes of the document. If the
document is empty, or there is no document, then the HTTP body MUST be empty
(zero length).

In this serialization mode, it might be useful for clients to have access to
the Resource's xRegistry metadata. To support this, some of the Resource's
xRegistry metadata will appear as HTTP headers in response messages.

On responses, unless otherwise stated, all top-level scalar attributes of the
Resource SHOULD appear as HTTP headers where the header name is the name of the
attribute prefixed with `xRegistry-`. Note, the optionality of this requirement
is not to allow for servers to decide whether or not to do so, rather it is to
allow for [No-Code Servers](#no-code-servers) servers than might not be able
to control the HTTP response headers.

Certain attributes do not follow this rule if a standard HTTP header name is
to be used instead (e.g. `contenttype` MUST use `Content-Type`, not
`xRegistry-contenttype`). Each attribute that falls into this category will
be identified as part of its definition.

Top-level map attributes whose values are of scalar types MUST also appear as
HTTP headers (each key having its own HTTP header) and in those cases the
HTTP header names will be of the form: `xRegistry-<ATTRIBUTENAME>-<KEYNAME>`.
Note that map keys MAY contain the `-` character, so any `-` after the 2nd `-`
is part of the key name. See
[HTTP Header Values](#http-header-values) for additional information and
[`labels`](#labels-attribute) for an example of one such attribute.

Complex top-level attributes (e.g. arrays, objects, non-scalar maps) MUST NOT
appear as HTTP headers.

On update requests, similar serialization rules apply. However, rather than
these headers being REQUIRED, the client would only need to include those
top-level attributes that they would like to change. But, including unchanged
attributes MAY be done. Any attributes not included in request messages
MUST be interpreted as a request to leave their values unchanged. Using a
value of `null` (case-sensitive) indicates a request to delete that attribute.

Any top-level map attributes that appear as HTTP headers MUST be included
in their entirety and any missing keys MUST be interpreted as a request to
delete those keys from the map.

Since only some types of attributes can appear as HTTP headers, `$details`
MUST be used to manage the others. See the next section for more details.

When a Resource (not a Version) is serialized with the Resource document
in the HTTP body, it MUST adhere to this form:

```yaml
Content-Type: <STRING> ?
xRegistry-<RESOURCE>id: <STRING>           # ID of Resource, not default Version
xRegistry-versionid: <STRING>              # ID of the default Version
xRegistry-self: <URL>                      # Resource URL, not default Version
xRegistry-xid: <URI>                       # Relative Resource URI
xRegistry-epoch: <UINTEGER>                # Start default Version's attributes
xRegistry-name: <STRING> ?
xRegistry-isdefault: true
xRegistry-description: <STRING> ?
xRegistry-documentation: <URL> ?
xRegistry-icon: <URL> ?
xRegistry-labels-<KEY>: <STRING> *
xRegistry-createdat: <TIMESTAMP>
xRegistry-modifiedat: <TIMESTAMP>
xRegistry-ancestor: <STRING>
xRegistry-<RESOURCE>url: <URL> ?           # End of default Version attributes
xRegistry-metaurl: <URL>                   # Resource-level attributes
xRegistry-versionsurl: <URL>
xRegistry-versionscount: <UINTEGER>
Location: <URL> ?
Content-Location: <URL> ?
Content-Disposition: <STRING> ?

... Resource document ... ?
```

Where:
- The `<RESOURCE>id` is the `<SINGULAR>id` of the Resource, not the default
  Version.
- The `versionid` attribute MUST be the ID of the Resource's default Version.
- The `xid` URI references the Resource, not the default Version.
- The `versionsurl` and `versionscount` Collection attributes are included,
  but not the `versions` collection itself.
- The `Location` header only appears in response to a create operation and
  MUST be the same as the `self` URL.
- The `Content-Location` header MAY appear, and if present, MUST reference
  the "default" Version.
- `Content-Disposition` SHOULD be present and if so, MUST be the `<RESOURCE>id`
  value. This allows for HTTP tooling that is not aware of xRegistry to know
  the desired filename to use if the HTTP body were to be written to a file.

Version serialization will look similar, but the set of xRegistry HTTP headers
will be slightly different (to exclude Resource-level attributes). See the
"[Retrieving a Version](#retrieving-a-version)" section for more information.

Scalar default Version extension attributes MUST also appear as
`xRegistry-` HTTP headers.

##### Serializing Resource Metadata

Appending `$details` to a Resource or Version's URL path modifies the
serialization of the entity such that, rather than the HTTP body containing
the entity's domain-specific "document" and the xRegistry metadata being
in HTTP headers, all of them are instead within the HTTP body as one JSON
object. If the entity's "document" is included within the object then it
appears under a `<RESOURCE>*` attribute (as discussed
[above](#resource-metadata-vs-resource-document)).

The advantage of this format is that the HTTP body will contain all of the
xRegistry metadata and not just the scalar values - as is the case when they
appear as HTTP headers. This allows for management of all metadata as well
as any possible domain-specific document at one time.

Note that in the case of a reference to a Resource (not a Version), the
metadata will be from the default Version, plus the extra `meta` and `versions`
related attributes.

When serialized as a JSON object, a Resource (not a Version) MUST adhere to
this form:

```yaml
{
  "<RESOURCE>id": "<STRING>",              # ID of Resource, not default Version
  "versionid": "<STRING>",                 # ID of default Version
  "self": "<URL>",                         # URL of Resource,not default Version
  "shortself": "<URL>", ?
  "xid": "<XID>",                          # Relative URI of Resource
  # These are inherited from the default Version
  "epoch": <UINTEGER>,
  "name": "<STRING>", ?
  "isdefault": true,
  "description": "<STRING>", ?
  "documentation": "<URL>", ?
  "icon": "<URL>", ?
  "labels": { "<STRING>": "<STRING>" * }, ?
  "createdat": "<TIMESTAMP>",
  "modifiedat": "<TIMESTAMP>",
  "ancestor": "<STRING>",
  "contenttype": "<STRING>", ?

  "<RESOURCE>url": "<URL>", ?                # If not local
  "<RESOURCE>": ... Resource document ..., ? # If inlined & JSON
  "<RESOURCE>base64": "<STRING>", ?          # If inlined & ~JSON

  # Resource-level helper attributes
  "metaurl": "<URL>",
  "meta": {                                  # If inlined
    "<RESOURCE>id": "<STRING>",
    "self": "<URL>",                         # URL to "meta"
    "shortself": "<URL>", ?
    "xid": "<XID>",                          # Relative URI to "meta"
    "xref": "<XID>", ?                       # Ptr to linked Resource
    "epoch": <UINTEGER>,                     # Resource's epoch
    "createdat": "<TIMESTAMP>",              # Resource's
    "modifiedat": "<TIMESTAMP>",             # Resource's
    "readonly": <BOOLEAN>,                   # Default=false
    "compatibility": "<STRING>",             # Default=none
    "compatibilityauthority": "<STRING>", ?  # Default=external
    "deprecated": { ... }, ?

    "defaultversionid": "<STRING>",
    "defaultversionurl": "<URL>",
    "defaultversionsticky": <BOOLEAN>        # Default=false
  }, ?
  "versionsurl": "<URL>",
  "versionscount": <UINTEGER>,
  "versions": { Versions collection } ?      # If inlined
}
```

The serialization of a Version will look similar except the `meta` and
`versions` related Resource-level attributes MUST NOT be present. More on this
in the next sections.

#### Cross Referencing Resources

Typically, Resources exist within the scope of a single Group, however there
might be situations where a Resource needs to be related to multiple Groups.
In these cases, there are two options. First, a copy of the Resource could be
made into the second Group. The obvious downside to this is that there's no
relationship between the two Resources and any changes to one would need to
be done in the other - running the risk of them getting out of sync.

The second, and better, option is to create a cross-reference from one
(the "source" Resource) to the other ("target" Resource). This is done
by setting the `xref` attribute on the source Resource to be the `xid`
of the target Resource.

For example: a `schema` Resource instance defined via:

```yaml
PUT /schemagroups/group1/schemas/mySchema$details

{
  "schemaid": "mySchema",
  "meta": {
    "xref": "/schemagroups/group2/schemas/sharedSchema"
  }
}
```

means that `mySchema` references `sharedSchema`, which exists in `group2`.
When this source Resource (`mySchema`) is retrieved, all of the target
Resource's attributes (except its `<RESOURCE>id`) will appear as if they were
locally defined.

So, if the target Resource (`sharedSchema`) is defined as:

```yaml
{
  "resourceid": "sharedSchema",
  "versionid": "v1",
  "self": "http://example.com/schemagroups/group2/schemas/sharedSchema",
  "xid": "/schemagroups/group2/schemas/sharedSchema",
  "epoch": 2,
  "isdefault": true,
  "createdat": "2024-01-01-T12:00:00Z",
  "modifiedat": "2024-01-01-T12:01:00Z",
  "ancestor": "v1",

  "metaurl": "http://example.com/schemagroups/group2/schemas/sharedSchema/meta",
  "versionscount": 1,
  "versionsurl": "http://example.com/schemagroups/group2/schemas/sharedSchema/versions"
}
```

then the resulting serialization of the source Resource would be:

```yaml
{
  "resourceid": "mySchema",
  "versionid": "v1",
  "self": "http://example.com/schemagroups/group1/schemas/mySchema",
  "xid": "/schemagroups/group1/schemas/mySchema",
  "epoch": 2,
  "isdefault": true,
  "createdat": "2024-01-01-T12:00:00Z",
  "modifiedat": "2024-01-01-T12:01:00Z",
  "ancestor": "v1",

  "metaurl": "http://example.com/schemagroups/group1/schemas/mySchema/meta",
  "meta": {
    "resourceid": "mySchema",
    "self": "http://example.com/schemagroups/group1/schemas/mySchema/meta",
    "xid": "/schemagroups/group1/schemas/mySchema/meta",
    "xref": "/schemagroups/group2/schemas/sharedSchema",
    "createdat": "2024-01-01-T12:00:00Z",
    "modifiedat": "2024-01-01-T12:01:00Z",
    "readonly": false,
    "compatibility": "none"
  },
  "versionscount": 1,
  "versionsurl": "http://example.com/schemagroups/group1/schemas/mySchema/versions"
}
```

Note:
- Any attributes referencing the source MUST use the source's metadata. In
  this respect, users of this serialization would never know that this is a
  cross-referenced Resource except for the presence of the `xref` attribute.
  For example, its `<RESOURCE>id` MUST be the source's `id` and not the
  target's.
- The `xref` attribute MUST appear within the `meta` sub-object so a client
  can easily determine that this Resource is a cross-referenced Resource, and
  it provides a reference to the targeted Resource.
- The `xref` XID MUST be the `xid` of the target Resource.

From a consumption (read) perspective, aside from the presence of the `xref`
attribute, the Resource appears to be a normal Resource that exists within
`group1`. All of the specification-defined features (e.g. `?inline`,
`?filter`) MAY be used when retrieving the Resource.

However, from a write perspective it is quite different. In order to update
the target Resource's attributes (or nested entities), a write operation MUST
be done on the appropriate target Resource entity directly. Write
operations on the source MAY be done, however, the changes are limited to
converting it from a "cross-reference" Resource back into a "normal"
Resource. See the following for more information:

When converting a "normal" Resource into a cross-reference Resource (adding
an `xref` value), or creating/updating a Resource that is a cross-reference
Resource, the following MUST be adhered to:
- The request MUST include an `xref` attribute with a value that is
  the `xid` of the target Resource.
- The request MAY include the `<RESOURCE>id` attribute (of the source
  Resource) on the Resource or `meta` sub-object.
- The request MAY include `epoch` within `meta` (to do an `epoch` validation
  check) only if the Resource already exists.
- The request MUST NOT include nested collections or any other attributes
  (for the Resource or its "meta" sub-object). This includes default Version
  attributes within the Resource serialization.
- If the Resource already exists, then any Versions associated with the
  Resource MUST be deleted.

When converting a cross-reference Resource back into a "normal" Resource, the
following MUST be adhered to:
- The request MUST delete the `xref` attribute or set it to `null`.
- A default Version of the Resource MUST be created.
- Any attributes specified at the Resource level MUST be interpreted as a
  request to set the default Version attributes. Absence of any attributes
  MUST result in a default Version being created with all attributes set
  to their default values. Note that normal Resource update semantics apply.
- When not specified in the request, the Resource's `meta.createdat` value
  MUST be reset to the timestamp of when this source Resource was originally
  created.
- When not specified in the request, the Resource's `meta.modifiedat` value
  MUST be set to "now".
- The Resource's `meta.epoch` value MUST be greater than the original
  Resource's previously known value (if any) and greater than the target
  Resource's `meta.epoch` value. In pseudocode this is:
    `epoch = max(original_Epoch, target_Resource_Epoch) + 1`.
  This will ensure that the Resource's `epoch` value will never decrease as a
  result of this operation. Note that going from a "normal" Resource to a
  cross-reference Resource does not have this guarantee. If the target Resource
  no longer exists then `target_Resource_Epoch` MUST be treated as zero.
- Aside from the processing rules specified above, the Resource's attributes
  that might have existed prior to the Resource being converted from a
  "normal" Resource into a cross-reference Resource MUST NOT be resurrected
  with their old values.
- Any relationship with the target Resource MUST be deleted.

If the target Resource itself is a cross-reference Resource, then including
the target Resource's attributes MUST NOT be done when serializing the
source Resource. Recursive, or transitively, following of `xref` XIDs is not
done.

Both the source and target Resources MUST be of the same Resource model type,
simply having similar Resource type definitions is not sufficient. This
implies that use of the `ximportresources` feature in the model to reference a
Resource type from another Group type definition MUST be used. See
[`ximportresources`](#reuse-of-resource-definitions) for more information.

An `xref` value that points to a non-existing Resource, either because
it was deleted or never existed, is not an error and is not a condition
that a server is REQUIRED to detect. In these "dangling xref" situations, the
serialization of the source Resource will not include any target Resource
attributes or nested collections. Rather, it will only show the `<RESOURCE>id`
and `xref` attributes.

---

#### Resource and Version APIs

For convenience, the Resource and Version create, update and delete APIs can be
summarized as:

**`POST /<GROUPS>/<GID>`**

- Creates or updates one or more collections of Resource types.

**`POST /<GROUPS>/<GID>/<RESOURCES>`**<br>
**`PATCH /<GROUPS>/<GID>/<RESOURCES>`**

- Creates or updates one or more Resources.

**`PUT   /<GROUPS>/<GID>/<RESOURCES>/<RID>[$details]`**<br>
**`PATCH /<GROUPS>/<GID>/<RESOURCES>/<RID>[$details]`**

- Creates a new Resource, or update the default Version of a Resource.

**`POST /<GROUPS>/<GID>/<RESOURCES>/<RID>[$details]`**<br>
**`PATCH /<GROUPS>/<GID>/<RESOURCES>/<RID>[$details]`**

- Creates or updates a single Version of a Resource.

**`PUT   /<GROUPS>/<GID>/<RESOURCES>/<RID>/meta`**<br>
**`PATCH /<GROUPS>/<GID>/<RESOURCES>/<RID>/meta`**

- Updates the `meta` sub-object of a Resource.

**`POST /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions`**<br>
**`PATCH /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions`**

- Creates or updates one or more Versions of a Resource.

**`PUT   /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>[$details]`**<br>
**`PATCH /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>[$details]`**

- Creates or updates a single Version of a Resource.

And the delete APIs are summarized as:

**`DELETE /<GROUPS>/<GID>/<RESOURCES>`**

- Delete a list of Resources, or all if the list is absent.

**`DELETE /<GROUPS>/<GID>/<RESOURCES>/<RID>`**

- Delete a single Resource.

**`DELETE /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions`**

- Delete a list of Versions, or all (and the Resource) if the list is absent.

**`DELETE /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>`**

- Delete a single Version of a Resource, and the Resource if last Version.

The following sections go into more detail about each API.

---

#### Retrieving a Resource Collection

To retrieve all Resources in a Resource Collection, an HTTP `GET` MAY be used.

The request MUST be of the form:

```yaml
GET /<GROUPS>/<GID>/<RESOURCES>
```

A successful response MUST be of the form:

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Link: <URL>;rel=next;count=<UINTEGER> ?

{
  "<KEY>": {                                    # The Resource ID
    "<RESOURCE>id": "<STRING>",                 # The Resource ID
    "versionid": "<STRING>",                    # Default Version ID
    "self": "<URL>",                            # URL to the Resource
    "shortself": "<URL>", ?
    "xid": "<XID>",                             # Relative URI to the Resource
    "epoch": <UINTEGER>,                        # Start of Default Ver attribs
    "name": "<STRING>", ?
    "isdefault": true,
    "description": "<STRING>", ?
    "documentation": "<URL>", ?
    "icon": "<URL>", ?
    "labels": { "<STRING>": "<STRING>" * }, ?
    "createdat": "<TIMESTAMP>",
    "modifiedat": "<TIMESTAMP>",
    "ancestor": "<STRING>",
    "contenttype": "<STRING>", ?

    "<RESOURCE>url": "<URL>", ?                 # If not local
    "<RESOURCE>": ... Resource document ..., ?  # If inlined & JSON
    "<RESOURCE>base64": "<STRING>", ?           # If inlined & ~JSON

    # Resource-level helper attributes
    "metaurl": "<URL>",
    "meta": {                                   # If inlined
      "<RESOURCE>id": "<STRING>",               # Resource ID
      "self": "<URL>",                          # URL to "meta"
      "shortself": "<URL>", ?
      "xid": "<XID>",                           # Relative URI to "meta"
      "xref": "<XID>", ?                        # Ptr to linked Resource
      "epoch": <UINTEGER>,                      # Resource's epoch
      "createdat": "<TIMESTAMP>",               # Resource's
      "modifiedat": "<TIMESTAMP>",              # Resource's
      "readonly": <BOOLEAN>,                    # Default=false
      "compatibility": "<STRING>",              # Default=none
      "compatibilityauthority": "<STRING>", ?   # Default=external
      "deprecated": { ... }, ?

      "defaultversionid": "<STRING>",
      "defaultversionurl": "<URL>",
      "defaultversionsticky": <BOOLEAN>
    }
    "versionsurl": "<URL>",
    "versionscount": <UINTEGER>,
    "versions": { Versions collection } ?       # If inlined
  } *
}
```

Where:
- The key of each item in the map MUST be the `<RESOURCE>id` of the respective
  Resource.

**Examples:**

Retrieve all `messages` of an `endpoint` whose `<RESOURCE>id` is `ep1`:

```yaml
GET /endpoints/ep1/messages
```

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Link: <https://example.com/endpoints/ep1/messages&page=2>;rel=next;count=100

{
  "msg1": {
    "messageid": "msg1",
    "versionid": "1.0",
    "self": "https://example.com/endpoints/ep1/messages/msg1",
    "xid": "/endpoints/ep1/messages/msg1",
    "epoch": 1,
    "name": "Blob Created",
    "isdefault": true,
    "createdat": "2024-04-30T12:00:00Z",
    "modifiedat": "2024-04-30T12:00:01Z",
    "ancestor": "1.0",

    "metaurl": "https://example.com/endpoints/ep1/messages/msg1/meta",
    "versionsurl": "https://example.com/endpoints/ep1/messages/msg1/versions",
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

`POST /<GROUPS>/<GID>`

Where:
- This API MUST create or update one or more Resources, of varying Resource
  types, within the specified Group.
- The HTTP body MUST contain a map of Resource types (as the map key), where
  the value of each map entry is a map of Resources of that type to be created
  or updated, serialized as xRegistry metadata.

For example:

```yaml
{
  "schemas": {
    "schema1": { ... Resource schema1's xRegistry metadata ... },
    "schema2": { ... Resource schema1's xRegistry metadata ... }
  },
  "messages": {
    "message1": { ... Resource message1's xRegistry metadata ... },
    "message2": { ... Resource message2's xRegistry metadata ... }
  }
}
```

Notice the format is almost the same as what a `PUT /<GROUPS>/<GID>` would look
like if the request wanted to update the Group's attributes and define a set
of Resources, but without the Group's attributes. This allows for an update of
the specified Resources without modifying the Group's attributes.

The response in this case MUST be a map of the Resource types with just the
Resources that were processed.

`POST  /<GROUPS>/<GID>/<RESOURCES>`<br>
`PATCH /<GROUPS>/<GID>/<RESOURCES>`

Where:
- This API MUST create or update one or more Resources within the specified
  Group and Resource type.
- The HTTP body MUST contain a map of Resources to be created or updated,
  serialized as xRegistry metadata.

`PUT   /<GROUPS>/<GID>/<RESOURCES>/<RID>[$details]`<br>
`PATCH /<GROUPS>/<GID>/<RESOURCES>/<RID>[$details]`

Where:
- These APIs MUST create or update a single Resource in the Group.
- When `$details` is present, the HTTP body MUST be an xRegistry
  serialization of the Resource.
- When `$details` is absent, the HTTP body MUST contain the Resource's
  document (an empty body means the document is to be empty).

`POST  /<GROUPS>/<GID>/<RESOURCES>/<RID>[$details][?setdefaultversionid=<VID>]`

Where:
- This API MUST create, or update, a single Version of the specified
  Resource.
- When the Resource has the `hasdocument` aspect set to `true`:
  - If `$details` is present in the URL, then the HTTP body MUST be an
    xRegistry metadata serialization of the Version that is to be created or
    updated.
  - If `$details` is absent in the URL, then the HTTP body MUST contain
    the Version's document (an empty body means the document is to be empty).
    Note that the xRegistry metadata (e.g. the Version's `versionid`) MAY be
    included as HTTP headers.
- When the Resource has the `hasdocument` aspect set to `false` then the
  HTTP body MUST be an xRegistry metadata serialization of the Version that is
  to be created or updated.

`PUT   /<GROUPS>/<GID>/<RESOURCES>/<RID>/meta`<br>
`PATCH /<GROUPS>/<GID>/<RESOURCES>/<RID>/meta`
Where:
- This API MUST update the `meta` sub-object of the specified Resource.
- As with all update operations, if the incoming request includes an `epoch`
  value that does not match the existing `meta` `epoch` value then an
  error ([mismatched_epoch](#mismatched_epoch)) MUST be generated.

`POST  /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions[?setdefaultversionid=<VID>]`<br>
`PATCH /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions[?setdefaultversionid=<VID>]`

Where:
- This API MUST create or update one or more Versions of the Resource.
- The HTTP body MUST contain a map of Versions to be created or updated,
  serialized as xRegistry metadata. Note that the map key of each entry
  MUST be the Version's `versionid` not the Resource's.
- If the Resource does not exist prior to this operation, it MUST be implicitly
  created and the following rules apply:
  - If there is only one Version created, then it MUST become the default
    Version, and use of the `?setdefaultversionid` query parameter is OPTIONAL.
  - If there is more than one Version created, then use of the
    `?setdefaultversionid` query parameter is RECOMMENDED.
  - There MUST be at least one Version specified in the HTTP body. In other
    words, an empty collection MUST generate an error
    ([missing_versions](#missing_versions)) since creating a Resource
    with no Versions would immediately delete that Resource.

See [Default Version of a Resource](#default-version-of-a-resource) for more
information about the `?setdefaultversionid` query parameter.

`PUT   /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>[$details][?setdefaultversionid=<VID>]`<br>
`PATCH /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>[$details][?setdefaultversionid=<VID>]`

Where:
- This API MUST create or update a single Version in the Resource.
- When the Resource has the `hasdocument` aspect set to `true`:
  - If `$details` is present in the URL, then the HTTP body MUST be an
    xRegistry metadata serialization of the Version that is to be created or
    updated.
  - If `$details` is absent in the URL, then the HTTP body MUST contain
    the Version's document (an empty body means the document is to be empty).
    Note that the xRegistry metadata (e.g. the Version's `versionid`) MAY be
    included as HTTP headers.
- When the Resource has the `hasdocument` aspect set to `false` then the
  HTTP body MUST be an xRegistry metadata serialization of the Version that is
  to be created or updated.

See [Default Version of a Resource](#default-version-of-a-resource) for more
information about the `?setdefaultversionid` query parameter.

---

To reduce the number of interactions needed, these APIs are designed to allow
for the implicit creation of all parent entities specified in the `<PATH>`. And
each entity not already present with the specified `<SINGULAR>id` MUST be
created with that value. Note: if any of those entities have REQUIRED
attributes, then they cannot be implicitly created, and would need to be
created directly.

When specified as an xRegistry JSON object, each individual Resource or Version
in the request MUST adhere to the following:

```yaml
{
  "<RESOURCE>id": "<STRING>", ?
  "versionid": "<STRING>", ?                   # Version-level attributes
  "epoch": <UINTEGER>,
  "name": "<STRING>", ?
  "isdefault": true,
  "description": "<STRING>", ?
  "documentation": "<URL>", ?
  "icon": "<URL>", ?
  "labels": { "<STRING>": "<STRING>" * }, ?
  "createdat": "<TIMESTAMP>", ?
  "modifiedat": "<TIMESTAMP>", ?
  "ancestor": "<STRING>",
  "contenttype": "<STRING>", ?

  "<RESOURCE>url": "<URL>", ?                  # If not local
  "<RESOURCE>": ... Resource document ..., ?   # If inlined & JSON
  "<RESOURCE>base64": "<STRING>", ?            # If inlined & ~JSON

  "metaurl": "<URL>", ?                        # Resource-only attributes
  "meta": {
    "<RESOURCE>id": "<STRING>", ?
    "xref": "<XID>", ?
    "epoch": <UINTEGER>, ?
    "createdat": "<TIMESTAMP>", ?
    "modifiedat": "<TIMESTAMP>", ?
    "compatibility": "<STRING>", ?
    "compatibilityauthority": "<STRING>", ?
    "deprecated": { ... }, ?

    "defaultversionid": "<STRING>",
    "defaultversionsticky": <BOOLEAN>
  }, ?
  "versionsurl": "<URL>",
  "versionscount": <UINTEGER>,
  "versions": { Versions collection } ?        # If inlined
}
```

When the HTTP body contains the Resource's (or Version's) document, then any
xRegistry scalar metadata MUST appear as HTTP headers and the request MUST
adhere to the following:

```yaml
<METHOD> <PATH>
Content-Type: <STRING> ?
xRegistry-<RESOURCE>id: <STRING> ?
xRegistry-versionid: <STRING> ?         # Version-level attributes
xRegistry-epoch: <UINTEGER> ?
xRegistry-name: <STRING> ?
xRegistry-isdefault: true
xRegistry-description: <STRING> ?
xRegistry-documentation: <URL> ?
xRegistry-icon: <URL> ?
xRegistry-labels-<KEY>: <STRING> *
xRegistry-createdat: <TIMESTAMP> ?
xRegistry-modifiedat: <TIMESTAMP> ?
xRegistry-ancestor: <STRING> ?
xRegistry-<RESOURCE>url: <URL> ?
xRegistry-metaurl: <URL>                 # Resource-only attributes
xRegistry-versionsurl: <URL>
xRegistry-versionscount: <UINTEGER>

... entity document ... ?
```

Where:
- In the cases where xRegistry metadata appears as HTTP headers, if the
  `<RESOURCE>url` attribute is present with a non-null value, the HTTP body
  MUST be empty. If the `<RESOURCE>url` attribute is absent, then the contents
  of the HTTP body (even if empty) are to be used as the entity's document.
- If the Resource's `hasdocument` model attribute has a value of `false` then
  the following rules apply:
  - Only the first form (serialization as a JSON Object) MUST be used.
  - Use of the `$details` suffix on the request URL is OPTIONAL, and if used
    the Resource/Version `self` URL MUST NOT include `$details`.
  - Any request that includes the xRegistry HTTP headers MUST generate an
    error ([extra_xregistry_headers](#extra_xregistry_headers)).
  - An update request with an empty HTTP body MUST be interpreted as a request
    to delete all xRegistry mutable attributes - in essence, resetting the
    entity back to its default state.
- If the `versionid` attribute is present, but it does not match the existing
  "default" Version's `versionid` (after any necessary processing of the
  `defaultversionid` attribute), then an error
  ([mismatched_id](#mismatched_id)) MUST be generated. Also see
  [Default Version of a Resource](#default-version-of-a-resource).

  If the `versionid` attribute is present while creating a new Resource, but
  a `versions` collection is not included, rather than the server generating
  the `versionid` of the newly created "default" Version, the server MUST use
  the passed-in `versionid` attribute value. This is done as a convenience
  for clients to avoid them having to include a `versions` collection just
  to set the initial default Version's `versionid`. In other words, when
  the `versions` collection is absent on a create, but `versionid` is
  present, there is an implied `"versions": { "<VID>": {} }` (where `<VID>`
  is the `versionid` value).

- When the xRegistry metadata is serialized as a JSON object, the processing
  of the 3 `<RESOURCE>` attributes MUST follow these rules:
  - At most, only one of the 3 attributes MAY be present in the request, and
    the presence of any one of them MUST delete the other 2 attributes.
  - If the entity already exists and has a document (not a `<RESOURCE>url`),
    then absence of all 3 attributes MUST leave all 3 unchanged.
  - An explicit value of `null` for any of the 3 attributes MUST delete all
    3 attributes (and any associated data).
  - When `<RESOURCE>` is present, the server MAY choose to modify non-semantic
    significant characters. For example, to remove (or add) whitespace. In
    other words, there is no requirement for the server to persist the
    document in the exact byte-for-byte format in which it was provided. If
    that is desired then `<RESOURCE>base64` MUST be used instead.
  - On a `PUT` or `POST`, when `<RESOURCE>` is present, if no `contenttype`
    value is provided then the server MUST set it to same type as the incoming
    request, e.g. `application/json`, even if the entity previous had a
    `contenttype` value.
  - On a `PATCH`, when `<RESOURCE>` or `<RESOURCE>base64` is present, if no
    `contenttype` value is provided then the server MUST set it to the same
    type as the incoming request, e.g. `application/json`, only if the entity
    does not already have a value. Otherwise, the existing value remains
    unchanged.

A successful response MUST include the current representation of the entities
created or updated and be in the same format (`$details` variant or not) as
the request.

If the request used the `PUT` or `PATCH` variants directed at a single entity,
and a new Version was created, then a successful response MUST include a
`Content-Location` HTTP header to the newly created Version entity, and it
MUST be the same as the Version's `self` attribute.

Note that the response MUST NOT include any inlineable attributes (such as
`<RESOURCE>`, `<RESOURCE>base64` or nested objects/collections) unless
requested.

**Examples:**

Create a new Resource:

```yaml
PUT /endpoints/ep1/messages/msg1
Content-Type: application/json; charset=utf-8
xRegistry-name: Blob Created

{
  # Definition of a "Blob Created" event (document) excluded for brevity
}
```

```yaml
HTTP/1.1 201 Created
Content-Type: application/json; charset=utf-8
xRegistry-messageid: msg1
xRegistry-versionid: 1
xRegistry-self: https://example.com/endpoints/ep1/messages/msg1
xRegistry-xid: /endpoints/ep1/messages/msg1
xRegistry-epoch: 1
xRegistry-name: Blob Created
xRegistry-isdefault: true
xRegistry-ancestor: 1
xRegistry-metaurl: https://example.com/endpoints/ep1/messages/msg1/meta
xRegistry-versionsurl: https://example.com/endpoints/ep1/messages/msg1/versions
xRegistry-versionscount: 1
Location: https://example.com/endpoints/ep1/messages/msg1
Content-Location: https://example.com/endpoints/ep1/messages/msg1/versions/1
Content-Disposition: msg1

{
  # Definition of a "Blob Created" event (document) excluded for brevity
}
```

Updates the default Version of a Resource as xRegistry metadata:

```yaml
PUT /endpoints/ep1/messages/msg1$details
Content-Type: application/json; charset=utf-8

{
  "epoch": 1,
  "name": "Blob Created",
  "description": "a cool event",

  "message": {
    # Updated definition of a "Blob Created" event excluded for brevity
  }
}
```

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Location: https://example.com/endpoints/ep1/messages/msg1/versions/1

{
  "messageid": "msg1",
  "versionid": "1",
  "self": "https://example.com/endpoints/ep1/messages/msg1",
  "xid": "/endpoints/ep1/messages/msg1",
  "epoch": 2,
  "name": "Blob Created",
  "isdefault": true,
  "description": "a cool event",
  "createdat": "2024-04-30T12:00:00Z",
  "modifiedat": "2024-04-30T12:00:01Z",
  "ancestor": "1",

  "message": {
    # Updated definition of a "Blob Created" event excluded for brevity
  },

  "metaurl": "https://example.com/endpoints/ep1/messages/msg1/meta",
  "versionsurl": "https://example.com/endpoints/ep1/messages/msg1/versions",
  "versionscount": 1
}
```

Update several Versions (adding a label):

```yaml
PATCH /endpoints/ep1/messages/msg1/versions
Content-Type: application/json; charset=utf-8

{
  "1": {
    "labels": { "customer": "abc" },
  },
  "2": {
    "labels": { "customer": "abc" },
  },
  "3": {
    "labels": { "customer": "abc" },
  }
}
```

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "1": {
    "messageid": "msg1",
    "versionid": "1",
    "labels": { "customer": "abc" },
    # Remainder of xRegistry metadata excluded for brevity
  },
  "2": {
    "messageid": "msg1",
    "versionid": "2",
    "labels": { "customer": "abc" },
    # Remainder of xRegistry metadata excluded for brevity
  },
  "3": {
    "messageid": "msg1",
    "versionid": "3",
    "labels": { "customer": "abc" },
    # Remainder of xRegistry metadata excluded for brevity
  }
]
```

Note that in this case, the new "label" replaces all existing labels, it is
not a "merge" operation because all attributes need to be specified in their
entirety.

#### Retrieving a Resource

To retrieve a Resource, an HTTP `GET` MAY be used.

The request MUST be of the form:

```yaml
GET /<GROUPS>/<GID>/<RESOURCES>/<RID>
```

This MUST retrieve the default Version of a Resource. Note that `<RID>` will be
the `<SINGULAR>id` of the Resource and not the `versionid` of the underlying
Version (see [Resources API](#resources-apis)).

A successful response MUST either be:
- `200 OK` with the Resource document in the HTTP body.
- `303 See Other` with the location of the Resource's document being
  returned in the HTTP `Location` header if the Resource has a `<RESOURCE>url`
  value, and the HTTP body MUST be empty.

In both cases the Resource's default Version attributes, along with the
`meta` and `versions` related scalar attributes, MUST be serialized as HTTP
`xRegistry-` headers when the Resource's `hasdocument` model attribute has a
value of `true`.

Note that if the Resource's `hasdocument` model attribute has a value of
`false` then the "Resource document" will be the xRegistry metadata for the
default Version - same as in the [Retrieving a Resource as
Metadata](#retrieving-a-resource-as-metadata) section but without the explicit
usage of `$details`.

When `hasdocument` is `true`, the response MUST be of the form:

```yaml
HTTP/1.1 200 OK|303 See Other
Content-Type: <STRING> ?
xRegistry-<RESOURCE>id: <STRING>
xRegistry-versionid: <STRING>
xRegistry-self: <URL>
xRegistry-xid: <XID>
xRegistry-epoch: <UINTEGER>
xRegistry-name: <STRING> ?
xRegistry-isdefault: true
xRegistry-description: <STRING> ?
xRegistry-documentation: <URL> ?
xRegistry-icon: <URL> ?
xRegistry-labels-<KEY>: <STRING> *
xRegistry-createdat: <TIMESTAMP>
xRegistry-modifiedat: <TIMESTAMP>
xRegistry-ancestor: <STRING>
xRegistry-<RESOURCE>url: <URL> ?  # If Resource is not in body
xRegistry-metaurl: <URL>
xRegistry-versionsurl: <URL>
xRegistry-versionscount: <UINTEGER>
Location: <URL> ?                 # If Resource is not in body
Content-Location: <URL> ?
Content-Disposition: <STRING> ?

... Resource document ...         # If <RESOURCE>url is not set
```

Where:
- `<RESOURCE>id` MUST be the `<SINGULAR>id` of the Resource, not of the default
  Version of the Resource.
- `self` MUST be a URL to the Resource, not to the default Version of the
  Resource.
- `shortself`, if present, MUST be an alternative URL for `self`.
- `xid` MUST be a relative URI to the Resource, not to the default Version of
  the Resource.
- If `<RESOURCE>url` is present then it MUST have the same value as `Location`.
- If `Content-Location` is present then it MUST be a URL to the Version of the
  Resource in the `versions` collection - same as `defaultversionurl`.
- `Content-Disposition` SHOULD be present and if so, MUST be the `<RESOURCE>id`
  value. This allows for HTTP tooling that is not aware of xRegistry to know
  the desired filename to use if the HTTP body were to be written to a file.

#### Retrieving a Resource as Metadata

When a Resource has the `hasdocument` model attribute set to `true`, to
retrieve a Resource's metadata (Resource attributes) as a JSON object, an
HTTP `GET` with `$details` appended to its URL path MAY be used.

When `$details` is present but the Resource does not have the `hasdocument`
model attribute set to `true`, the server MUST process the request as if
`$details` is not present. This allows for consistent access to the Resource
metadata without the need to check each Resource type's model definition.

The request MUST be of the form:

```yaml
GET /<GROUPS>/<GID>/<RESOURCES>/<RID>[$details]
```

A successful response MUST be of the form:

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Location: <URL> ?

{
  "<RESOURCE>id": "<STRING>",
  "versionid": "<STRING>",
  "self": "<URL>",                           # URL to Resource, not default Ver
  "shortself": "<URL>", ?
  "xid": "<XID>",                            # Relative URI to Resource
  "epoch": <UINTEGER>,                       # Start of Default Ver attribs
  "name": "<STRING>", ?
  "isdefault": true,
  "description": "<STRING>", ?
  "documentation": "<URL>", ?
  "icon": "<URL>", ?
  "labels": { "<STRING>": "<STRING>" * }, ?
  "createdat": "<TIMESTAMP>",
  "modifiedat": "<TIMESTAMP>",
  "ancestor": "<STRING>",
  "contenttype": "<STRING>", ?

  "<RESOURCE>url": "<URL>", ?                # If not local
  "<RESOURCE>": ... Resource document ..., ? # If inlined & JSON
  "<RESOURCE>base64": "<STRING>", ?          # If inlined & ~JSON

  "metaurl": "<URL>",
  "meta": {                                  # If inlined
    "<RESOURCE>id": "<STRING>", ?
    "self": "<URL>",                         # URL to "meta" sub-object
    "shortself": "<URL>", ?
    "xid": "<XID>",                          # XID of "meta" sub-object
    "xref": "<XID>", ?
    "epoch": <UINTEGER>,
    "createdat": "<TIMESTAMP>",
    "modifiedat": "<TIMESTAMP>",
    "readonly": <BOOLEAN>,
    "compatibility": "<STRING>",
    "compatibilityauthority": "<STRING>", ?
    "deprecated": { ... }, ?

    "defaultversionid": "<STRING>",
    "defaultversionurl": "<URL>",
    "defaultversionsticky": <BOOLEAN>
  },
  "versionsurl": "<URL>",
  "versionscount": <UINTEGER>,
  "versions": { Versions collection } ?      # If inlined
}
```

Where:
- The use of the `$details` suffix is REQUIRED when the Resource's
  `hasdocument` aspect is `true`.
- `<RESOURCE>id` MUST be the Resource's `<SINGULAR>id`, not the `versionid` of
  the default Version.
- `self` is a URL to the Resource (with `$details` suffix if `hasdocument`
  is `true`), not to the default Version of the Resource.
- `shortself`, if present, MUST be an alternative URL for `self`.
- `xid` is a relative URI to the Resource (without `$details`), not to the
  default Version of the Resource.
- `<RESOURCE>`, or `<RESOURCE>base64`, MUST only be included if requested via
  use of the `?inline` feature and `<RESOURCE>url` is not set.
- If `Content-Location` is present then it MUST be a URL to the Version of the
  Resource in the `versions` collection - same as `defaultversionurl`.

**Examples:**

Retrieve a `message` Resource as xRegistry metadata:

```yaml
GET /endpoints/ep1/messages/msg1$details
```

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Location: https://example.com/endpoints/ep1/messages/msg1/versions/1

{
  "messageid": "msg1",
  "versionid": "1",
  "self": "https://example.com/endpoints/ep1/messages/msg1","
  "xid": "/endpoints/ep1/messages/msg1",
  "epoch": 1,
  "name": "Blob Created",
  "isdefault": true,
  "createdat": "2024-04-30T12:00:00Z",
  "modifiedat": "2024-04-30T12:00:01Z",
  "ancestor": "1",

  "metaurl": "https://example.com/endpoints/ep1/messages/msg1/meta",
  "versionsurl": "https://example.com/endpoints/ep1/messages/msg1/versions",
  "versionscount": 1
}
```

#### Deleting Resources

To delete one or more Resources, and all of their Versions, an HTTP `DELETE`
MAY be used:
- `DELETE /<GROUPS>/<GID>/<RESOURCES>/<RID>[?epoch=<UINTEGER>]`
- `DELETE /<GROUPS>/<GID>/<RESOURCES>`

The processing of these two APIs is defined in the [Deleting Entities in a
Registry Collection](#deleting-entities-in-a-registry-collection)
section.

Deleting a Resource MUST delete all Versions within the Resource.

---

### Versions APIs

Versions represent historical instances of a Resource. When a Resource is
updated, there are two actions that might take place. First, the update can
completely replace an existing Version of the Resource. This is most typically
done when the previous state of the Resource is no longer needed, and there
is no reason to allow people to reference it. The second situation is when
both the old and new Versions of a Resource are meaningful and both might need
to be referenced. In this case, the update will cause a new Version of the
Resource to be created and will have a unique `versionid` within the scope
of the owning Resource.

For example, updating the data of Resource without creating a new Version
would make sense if there is an error in the `description` field. But, adding
additional data to the document of a Resource might require a new Version and
a new `versionid` (e.g. changing it from "1.0" to "1.1").

This specification does not mandate a particular versioning algorithm or
Version identification (`versionid`) scheme.

When serialized as a JSON object, the Version entity adheres to this form:

```yaml
{
  "<RESOURCE>id": "<STRING>",                  # <SINGULAR>id of Resource
  "versionid": "<STRING>",
  "self": "<URL>",
  "shortself": "<URL>", ?
  "xid": "<XID>",
  "epoch": <UINTEGER>,
  "name": "<STRING>", ?
  "isdefault": <BOOLEAN>,
  "description": "<STRING>", ?
  "documentation": "<URL>", ?
  "icon": "<URL>", ?
  "labels": { "<STRING>": "<STRING>" * }, ?
  "createdat": "<TIMESTAMP>",
  "modifiedat": "<TIMESTAMP>",
  "ancestor": "<STRING>",
  "contenttype": "<STRING>", ?

  "<RESOURCE>url": "<URL>", ?                  # If not local
  "<RESOURCE>": ... Resource document ..., ?   # If inlined & JSON
  "<RESOURCE>base64": "<STRING>" ?             # If inlined & ~JSON
}
```

Version extension attributes would also appear as additional top-level JSON
attributes.

Versions include the following [common attributes](#common-attributes):
- [`<RESOURCE>id`](#singularid-id-attribute) - REQUIRED in API and document
  views. OPTIONAL in requests. MUST be the `<RESOURCE>id` of the owning
  Resource.
- [`versionid`](#versionid-attribute) - REQUIRED in API and document views.
  OPTIONAL in requests.
- [`self`](#self-attribute) - REQUIRED in API and document views.
  OPTIONAL/ignored in requests. MUST be a URL to this Version, not the owning
  Resource.
- [`shortself`](#shortself-attribute) - OPTIONAL in API and document view,
  based on the `shortself` capability. OPTIONAL/ignored in requests.
- [`xid`](#xid-attribute) - REQUIRED in API and document views.
  OPTIONAL/ignored in requests. MUST be the `xid` of this Version, not the
  owning Resource.
- [`epoch`](#epoch-attribute) - REQUIRED in API and document views. OPTIONAL
  in requests. MUST be the `epoch` value of this Version, not the owning
  Resource.
- [`name`](#name-attribute) - OPTIONAL.
- [`description`](#description-attribute) - OPTIONAL.
- [`documentation`](#documentation-attribute) - OPTIONAL.
- [`icon`](#icon-attribute) - OPTIONAL.
- [`labels`](#labels-attribute) - OPTIONAL.
- [`createdat`](#createdat-attribute) - REQUIRED in API and document views.
  OPTIONAL in requests.
- [`modifiedat`](#modifiedat-attribute) - REQUIRED in API and document views.
  OPTIONAL in requests.

and the following Version-level attributes:

- [`isdefault`](#isdefault-attribute) - REQUIRED in API and document views
  when `true`, OPTIONAL when `false`. OPTIONAL in requests.
- [`ancestor`](#ancestor-attribute) - REQUIRED in API and document views.
  OPTIONAL in requests.
- [`contenttype`](#contenttype-attribute) - OPTIONAL.
- [`<RESOURCE>url`](#resourceurl-attribute) - OPTIONAL.
- [`<RESOURCE>`](#resource-attribute) - OPTIONAL.
- [`<RESOURCE>base64`](#resourcebase64-attribute) - OPTIONAL.

as defined below:

##### `versionid` Attribute

- Type: String
- Description: An immutable unique identifier of the Version.

- Constraints:
  - See [<SINGULAR>id](#singularid-id-attribute).
  - MUST NOT use a value of `null` or `request` due to these being reserved
    for use by the `?setdefaultversionid` feature.

- Examples:
  - `1.0`
  - `v2`
  - `v3-rc`

##### `isdefault` Attribute
- Type: Boolean
- Description: indicates whether this Version is the "default" Version of the
  owning Resource. This value is different from other attributes in that it
  might often be a calculated value rather than persisted in a datastore.
  Thus, when its value changes due to the default Version of a Resource
  changing, the Version itself does not change - meaning attributes such as
  `modifiedat` remains unchanged.

  See [Creating or Updating Resources and
  Versions](#creating-or-updating-resources-and-versions) for additional
  information about this attribute.

- Constraints:
  - REQUIRED.
  - MUST be a read-only attribute.
  - When not specified, the default value MUST be `false`.
  - When specified, MUST be either `true` or `false`, case-sensitive.

- Examples:
  - `true`
  - `false`

##### `ancestor` Attribute
- Type: String
- Description: The `versionid` of this Version's ancestor.

  The `ancestor` attribute MUST be set to the `versionid` of this Version's
  ancestor. If this Version is a root of an ancestor hierarchy tree then it
  MUST be set to its own `versionid` value.

  See the Resource's
  [`versionmode`](#--model-groupsstringresourcesstringversionmode) model
  aspect for more information on how this attribute value can be populated.

  If a create operation asks the server to choose the `versionid` when
  creating a root Version, the `versionid` is not yet known and therefore
  cannot be assigned the value in the `ancestor` attribute. In those cases a
  value of `request` MUST be used as a way to reference the Version being
  processed in the current request.

- Constraints:
  - REQUIRED.
  - The `ancestor` attribute MUST NOT be set to a value that
    creates circular references between Versions and it is STRONGLY RECOMMENDED
    that the server generate an error
    ([ancestor_circular_reference](#ancestor_circular_reference)) if a request
    attempts to do so. For example, an operation that makes Version A's
    ancestor B, and Version B's ancestor A, would generate an error.
  - When absent in a write operation request, it MUST be interpreted as the
    same as if it were present with its existing value.
  - Any attempt to set an `ancestor` attribute to a non-existing `versionid`
    MUST generate an error ([invalid_data](#invalid_data)).
  - For clarity, any modification to the `ancestor` attribute MUST result in
    the owning Version's `epoch` and `modifiedat` attributes be updated
    appropriately.

##### `contenttype` Attribute
- Type: String
- Description: The media type of the entity as defined by
  [RFC9110](https://datatracker.ietf.org/doc/html/rfc9110#media.type).

- Constraints:
  - OPTIONAL.
  - SHOULD be compliant with
    [RFC9110](https://datatracker.ietf.org/doc/html/rfc9110#media.type).
  - When serialized as an HTTP header, it MUST be named `Content-Type` not
    `xRegistry-contenttype` like other xRegistry headers.
  - On an update request when the xRegistry metadata appears in HTTP headers,
    unlike other attributes that will remain unchanged when not specified,
    this attribute MUST be erased if the incoming request does not include
    the `Content-Type` HTTP header.
  - This attribute MAY be specified even for Resources that use the
    `<RESOURCE>url` attribute. While this specification cannot guarantee that
    this attribute's value will match the `Content-Type` returned by an
    HTTP `GET` to the `<RESOURCE>url`, it is expected that they will match.

- Examples:
  - `application/json`

##### `<RESOURCE>url` Attribute
- Type: URI
- Description: if the Resource's document is stored outside of the
  current Registry, then this attribute MUST contain a URL to the
  location where it can be retrieved. If the value of this attribute
  is a well-known identifier that is readily understood by registry
  users and resolves to a common representation of the Resource, or
  an item in some private store/cache, rather than a networked document
  location, then it is RECOMMENDED for the value to be a uniform resource
  name ([URN](https://datatracker.ietf.org/doc/html/rfc8141)).

- Constraints:
  - REQUIRED if the Resource's document is not stored inside of the current
    Registry.
  - If the document is stored in a network-accessible endpoint then the
    referenced URL MUST support an HTTP(s) `GET` to retrieve the contents.
  - MUST NOT be present if the Resource's `hasdocument` model attribute is
    set to `false`.

##### `<RESOURCE>` Attribute
- Type: Resource Document
- Description: This attribute is a serialization of the corresponding
  Resource document's contents. If the document's bytes "as is" allows for
  them to appear as the value of this JSON attribute, then this attribute MUST
  be used if the request asked for the document to be inlined in the response.

- Constraints
  - MUST NOT be present when the Resource's Registry metadata is serialized as
    HTTP headers.
  - If the Resource's document is to be serialized and is not empty,
    then either `<RESOURCE>` or `<RESOURCE>base64` MUST be present.
  - MUST only be used if the Resource document (bytes) is in the same
    format as the Registry Resource entity.
  - MUST NOT be present if `<RESOURCE>base64` is also present.
  - MUST NOT be present if the Resource's `hasdocument` model attribute is
    set to `false.

##### `<RESOURCE>base64` Attribute
- Type: String
- Description: This attribute is a base64 serialization of the corresponding
  Resource document's contents. If the Resource document (which is stored as
  an array of bytes) is not conformant with the format being used to serialize
  the Resource entity (e.g. as a JSON value), then this attribute MUST be
  used in instead of the `<RESOURCE>` attribute.

- Constraints:
  - MUST NOT be present when the Resource's Registry metadata is serialized as
    HTTP headers.
  - If the Resource's document is to be serialized and it is not empty,
    then either `<RESOURCE>` or `<RESOURCE>base64` MUST be present.
  - MUST be a base64 encoded string of the Resource's document.
  - MUST NOT be present if `<RESOURCE>` is also present.
  - MUST NOT be present if the Resource's `hasdocument` model attribute is
    set to `false.

#### Version IDs

If a server does not support client-side specification of the `versionid` of a
new Version (see the `setversionid` attribute in the [Registry
Model](#registry-model)), or if a client chooses to not specify the
`versionid`, then the server MUST assign new Version an `versionid` that is
unique within the scope of its owning Resource.

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
it is RECOMMENDED to include a major version identifier in the Resource
`<RESOURCE>id`, like `"com.example.event.v1"` or `"com.example.event.2024-02"`,
so that incompatible, but historically related Resources can be more easily
identified by users and developers. The Version's `versionid` then functions
as the semantic minor version identifier.

#### Default Version of a Resource

As Versions of a Resource are added or removed, there needs to be a mechanism
by which the "default" one is determined. There are two options for how this
might be done:

1. Newest = Default. The newest Version (based on the Resource's
   [`versionmode`](#--model-groupsstringresourcesstringversionmode) algorithm)
   MUST be the "default" Version. This is the default choice.

1. Client explicitly chooses the "default". In this option, a client has
   explicitly chosen which Version is the "default" and it will not change
   until a client chooses another Version, or that Version is deleted (in
   which case the server MUST revert back to option 1 (newest = default), if
   the client did not use `?setdefaultversionid` to choose the next "default"
   Version - see below). This is referred to as the default Version being
   "sticky" as it will not change until explicitly requested by a client.

If supported (as determined by the `setdefaultversionsticky` model aspect),
a client MAY choose the "default" Version two ways:
1. Via the Resource `defaultversionsticky` and `defaultversionid` attributes
   in its `meta` sub-object. See [Resource Attributes](#resource-attributes)
   for more information about these attributes.
2. Via the `?setdefaultversionid` query parameter that is available on certain
   APIs, as defined below.

The `?setdefaultversionid` query parameter is defined as:

```yaml
...?setdefaultversionid=<VID>
```

Where:
- `<VID>` is the `versionid` of the Version that is to become the "default"
  Version of the referenced Resource. A value of `null` indicates that the
  client wishes to switch to the "newest = default" algorithm, in other words,
  the "sticky" aspect of the current default Version will be removed. It is
  STRONGLY RECOMMENDED that clients provide an explicit value when possible.
  However, if a Version create operation asks the server to choose the `<VID>`,
  then including that value in the query parameter is not possible. In those
  cases a value of `request` MAY be used as a way to reference the Version
  being processed in the current request, and if the request creates more than
  one Version, then an error ([too_many_versions](#too_many_versions)) MUST be
  generated.
- If a non-`null` and non-`request` `<VID>` does not reference an existing
  Version of the Resource, after all Version processing is completed, then an
  error ([unknown_id](#unknown_id)) MUST be generated.

Any use of this query parameter on a Resource that has the
`setdefaultversionsticky` aspect set to `false` MUST generate an error
([bad_flag](#bad_flag)).

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
- Choosing a new default Version for a Resource MUST NOT change any attributes
  in any Resource's Versions, for example, attributes such as `modifiedat`
  remain unchanged.
- And for clarity, the Resource's `meta` sub-object's `epoch` and `modifiedat`
  attributes MUST be updated.

#### Retrieving all Versions

To retrieve all Versions of a Resource, an HTTP `GET` MAY be used.

The request MUST be of the form:

```yaml
GET /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions
```

A successful response MUST be of the form:

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Link: <URL>;rel=next;count=<UINTEGER> ?

{
  "<KEY>": {                                    # The versionid
    "<RESOURCE>id": "<STRING>",                 # ID of Resource
    "versionid": "<STRING>",
    "self": "<URL>",
    "shortself": "<URL>", ?
    "xid": "<XID>",
    "epoch": <UINTEGER>,
    "name": "<STRING>", ?
    "isdefault": <BOOLEAN>,
    "description": "<STRING>", ?
    "documentation": "<URL>", ?
    "icon": "<URL>", ?
    "labels": { "<STRING>": "<STRING>" * }, ?
    "createdat": "<TIMESTAMP>",
    "modifiedat": "<TIMESTAMP>",
    "ancestor": "<STRING>",
    "contenttype": "<STRING>", ?

    "<RESOURCE>url": "<URL>", ?                 # If not local
    "<RESOURCE>": ... Resource document ..., ?  # If inlined & JSON
    "<RESOURCE>base64": "<STRING>" ?            # If inlined & ~JSON
  } *
}
```

Where:
- The key of each item in the map MUST be the `versionid` of the respective
  Version.

**Examples:**

Retrieve all Version of a `message` Resource:

```yaml
GET /endpoints/ep1/messages/msg1/versions
```

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Link: <https://example.com/endpoints/ep1/messages/msg1/versions&page=2>;rel=next;count=100

{
  "1.0": {
    "messageid": "msg1",
    "versionid": "1.0",
    "self": "https://example.com/endpoints/ep1/messages/msg1",
    "xid": "/endpoints/ep1/messages/msg1",
    "epoch": 1,
    "name": "Blob Created",
    "isdefault": true,
    "createdat": "2024-04-30T12:00:00Z",
    "modifiedat": "2024-04-30T12:00:01Z",
    "ancestor": "1.0"
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
GET /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>
```

A successful response MUST either return the Version or an HTTP redirect to
the `<RESOURCE>url` value if set.

In the case of returning the Version's document, the response MUST be of the
form:

```yaml
HTTP/1.1 200 OK
Content-Type: <STRING> ?
xRegistry-<RESOURCE>id: <STRING>
xRegistry-versionid: <STRING>
xRegistry-self: <URL>
xRegistry-xid: <XID>
xRegistry-epoch: <UINTEGER>
xRegistry-name: <STRING> ?
xRegistry-isdefault: <BOOLEAN> ?
xRegistry-description: <STRING> ?
xRegistry-documentation: <URL> ?
xRegistry-icon: <URL> ?
xRegistry-labels-<KEY>: <STRING> *
xRegistry-createdat: <TIMESTAMP>
xRegistry-modifiedat: <TIMESTAMP>
xRegistry-ancestor: <STRING>
Content-Disposition: <STRING> ?

... Version document ...
```

Where:
- `<RESOURCE>id` MUST be the `<SINGULAR>id` of the owning Resource.
- `versionid` MUST be the `<SINGULAR>id` of the Version.
- `self` MUST be a URL to the Version, not to the owning Resource.
- `xid` MUST be a relative URI to the Version, not to the owning Resource.
- `Content-Disposition` SHOULD be present and if so, MUST be the `<RESOURCE>id`
  value. This allows for HTTP tooling that is not aware of xRegistry to know
  the desired filename to use if the HTTP body were to be written to a file.

In the case of a redirect, the response MUST be of the form:

```yaml
HTTP/1.1 303 See Other
Content-Type: <STRING> ?
xRegistry-<RESOURCE>id: <STRING>
xRegistry-versionid: <STRING>
xRegistry-self: <URL>
xRegistry-xid: <URI>
xRegistry-epoch: <UINTEGER>
xRegistry-name: <STRING> ?
xRegistry-isdefault: <BOOLEAN> ?
xRegistry-description: <STRING> ?
xRegistry-documentation: <URL> ?
xRegistry-icon: <URL> ?
xRegistry-labels-<KEY>: <STRING> *
xRegistry-createdat: <TIMESTAMP>
xRegistry-modifiedat: <TIMESTAMP>
xRegistry-ancestor: <STRING>
xRegistry-<RESOURCE>url: <URL>
Location: <URL>
Content-Disposition: <STRING> ?
```

Where:
- `Location` and `<RESOURCE>url` MUST have the same value.

**Examples:**

Retrieve a specific Version (`1.0`) of a `message` Resource:

```yaml
GET /endpoints/ep1/messages/msg1/versions/1.0
```

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
xRegistry-messageid: msg1
xRegistry-versionid: 1.0
xRegistry-self: https://example.com/endpoints/ep1/messages/msg1/versions/1.0
xRegistry-xid: /endpoints/ep1/messages/msg1/versions/1.0
xRegistry-epoch: 2
xRegistry-name: Blob Created
xRegistry-isdefault: true
xRegistry-createdat: 2024-04-30T12:00:00Z
xRegistry-modifiedat: 2024-04-30T12:00:01Z
xRegistry-ancestor: 1.0
Content-Disposition: msg1

{
  # Definition of a "Blob Created" event excluded for brevity
}
```

#### Retrieving a Version as Metadata

To retrieve a particular Version's metadata, an HTTP `GET` with `$details`
appended to its `<RESOURCE>id` MAY be used. Note that in cases where the
Resource's `hasdocument` is `false` then the `$details` suffix is OPTIONAL.

The request MUST be of the form:

```yaml
GET /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>[$details]
```

A successful response MUST be of the form:

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "<RESOURCE>id": "<STRING>",
  "versionid": "<STRING>",
  "self": "<URL>",
  "shortself": "<URL>", ?
  "xid": "<XID>",
  "epoch": <UINTEGER>,
  "name": "<STRING>", ?
  "isdefault": <BOOLEAN>,
  "description": "<STRING>", ?
  "documentation": "<URL>", ?
  "icon": "<URL>", ?
  "labels": { "<STRING>": "<STRING>" * }, ?
  "createdat": "<TIMESTAMP>",
  "modifiedat": "<TIMESTAMP>",
  "ancestor": "<STRING>",
  "contenttype": "<STRING>", ?

  "<RESOURCE>url": "<URL>", ?                # If not local
  "<RESOURCE>": ... Resource document ..., ? # If inlined & JSON
  "<RESOURCE>base64": "<STRING>" ?           # If inlined & ~JSON
}
```

Where:
- `<RESOURCE>id` MUST be the `<SINGULAR>id` of the owning Resource.
- `versionid` MUST be the `<SINGULAR>id` of the Version.
- `self` MUST be a URL to the Version, not to the owning Resource.
- `xid` MUST be a relative URI to the Version, not to the owning Resource.

**Examples:**

Retrieve a specific Version of a `message` Resource as xRegistry metadata:

```yaml
GET /endpoints/ep1/messages/msg1/versions/1.0$details
```

```yaml
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "messageid": "msg1",
  "versionid": "1.0",
  "self": "https://example.com/endpoints/ep1/messages/msg1/versions/1.0",
  "xid": "/endpoints/ep1/messages/msg1/versions/1.0",
  "epoch": 2,
  "name": "Blob Created",
  "isdefault": true,
  "createdat": "2024-04-30T12:00:00Z",
  "modifiedat": "2024-04-30T12:00:01Z",
  "ancestor": "1.0"
}
```

#### Deleting Versions

To delete one or more Versions of a Resource, an HTTP `DELETE` MAY be used:
- `DELETE /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/vid[?epoch=<UINTEGER>&setdefaultversionid=<VID>]`
- `DELETE /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions[?setdefaultversionid=<VID>]`

The processing of these two APIs is defined in the [Deleting Entities in a
Registry Collection](#deleting-entities-in-a-registry-collection)
section. For more information about the `?setdefaultversionid` query
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

If, as an extension, the server MAY choose to return additional data in the
HTTP body.

**Examples:**

Delete a single Version of a `message` Resource:

```yaml
DELETE /endpoints/ep1/messages/msg1/versions/1.0
```

```yaml
HTTP/1.1 204 No Content
```

---

### Configuring Responses

Any request MAY include a set of query parameters (flags) to control how the
response is to be generated. The following sections defines the following
flags:
- [`?binary`](#binary-flag)
- [`?collections`](#collections-flag)
- [`?doc`](#doc-flag)
- [`?filter`](#filter-flag)
- [`?inline`](#inline-flag)
- [`?sort`](#sort-flag)

Implementations of this specification SHOULD support all flags, if support for
query parameters is possible..

#### Binary Flag

The `?binary` query parameter (flag) MAY be used on requests to indicate that
the server MUST use the `<RESOURCE>base64` attribute instead of the
`<RESOURCE>` attribute when serializing any Resource's domain document in the
response message. Note, the presence of this flag does not change when the
document is inlined, just how it is serialized if it is inlined.

This flag is intended for cases where the client wishes to avoid the server
modifying the bytes of the document in any way - such as "pretty printing" it.

#### Collections Flag

The `?collections` query parameter (flag) MAY be used on requests directed
to the Registry itself or to Group instances to indicate that the response
message MUST NOT include any attributes from the top-level entity (Registry
or Group), but instead MUST include only all of the nested Collection maps
that are defined at that level. Specifying it on a request directed to
some other part of the Registry MUST generate an error ([bad_flag](#bad_flag)).
Use of this flag MUST implicitly turn on inlining - `?inline=*`.

Servers MAY choose to include, or exclude, the sibling `<COLLECTION>url` and
`<COLLECTION>count` attributes for those top-level collections.

Note that this feature only applies to the root entity of the response and not
to any nested entities/collections.

This feature is meant to be used when the Collections of the Registry, or
Group, are of interest but not the top-level metadata. For example, this could
be used to export one or more Group types from a Registry where the resulting
JSON document is then used to import them into another Registry. If the
Registry-level attributes were present in the output then they would need to
be removed prior to the import, otherwise they would override the target
Registry's values.

The resulting JSON, when using this feature, is designed to be used on a
future `POST /` operation to either a Registry entity or to a Group instance
as appropriate.

#### Doc Flag

The `?doc` query parameter (flag) MAY be used to indicate that the response
MUST use "document view" when serializing entities and MUST be modified to do
the following:
- Remove the default Version attributes from a Resource's serialization.
- When a Resource (source) uses the `xref` feature, the target Resource's
  attributes are excluded from the source's serialization.
- Convert the following attributes into relative URLs if, and only if, the
  entities that they reference are included in the response output:
  `self`, `<COLLECTION>url`, `metaurl`, `defaultversionurl`.
- Serialize Resources and Versions as if `$details` was provided.

All of the relative URLs mentioned in the last bullet MUST begin with `#`
and be followed by a
[JSON Pointer](https://datatracker.ietf.org/doc/html/rfc6901) reference to the
entity within the response, e.g. `#/endpoints/e1`. This means that they are
relative to the root of the document (response) generated, and not necessarily
relative to the root of the Registry. Additionally, when those URLs are
relative and reference a Resource or Version, the `$details` suffix MUST NOT
be present despite the semantics of the suffix being applied (as noted below).

For clarity, if a Registry has a Schema Resource at
`/schemagroups/g1/schemas/s1`, then this entity's `self` URL (when serialized
in document view) would change based on the path specified on the `GET`
request:

| GET Path | `self` URL |
| --- | --- |
| `http://example.com/myreg` | `#/schemagroups/g1/schemas/s1` |
| `http://example.com/myreg/schemagroups` | `#/g1/schemas/s1` |
| `http://example.com/myreg/schemagroups/g1/ ` | `#/schemas/s1` |
| `http://example.com/myreg/schemagroups/g1/schemas ` | `#/s1` |
| `http://example.com/myreg/schemagroups/g1/schemas/s1` | `#/` |

This feature is useful when a client wants to minimize the amount of data
returned by a server because the duplication of that data (typically used for
human readability purposes) isn't necessary. For example, if tooling would
ignore the duplication, or if the data will be used to populate a new
Registry, then this feature might be used. It also makes the output more of a
"stand-alone" document that minimizes external references.

For clarity, the serialization of a Resource in document view will adhere to
the following:

```yaml
{
  "<RESOURCE>id": "<STRING>",
  "self": "<URL>",
  "shortself": "<URL>", ?
  "xid": "<XID>",

  "metaurl": "<URL>",
  "meta": {
    "<RESOURCE>id": "<STRING>",
    "self": "<URL>",
    "shortself": "<URL>", ?
    "xid": "<XID>",
    "xref": "<XID>" ?
    # The following attributes are absent if 'xref' is set
    "epoch": <UINTEGER>,
    "createdat": "<TIMESTAMP>",
    "modifiedat": "<TIMESTAMP>",
    "ancestor": "<STRING>",
    "readonly": <BOOLEAN>,
    "compatibility": "<STRING>",
    "compatibilityauthority": "<STRING>", ?
    "deprecated": { ... }, ?

    "defaultversionid": "<STRING>",
    "defaultversionurl": "<URL>"
    "defaultversionsticky": <BOOLEAN>
  }
}
```

Note that the attributes `epoch` through `defaultversionsticky` MUST be
excluded if `xref` is set because those would be picked-up from the target
Resource's `meta` sub-object.

If `?doc` is used on a request directed to a Resource, or Version,
that has the `hasdocument` model aspect set to `true`, then the processing
of the request MUST take place as if the `$details` suffix was specified
in the URL. Meaning, the response MUST be the xRegistry metadata view of the
Resource and not the Resource's "document".

If `?doc` is used on a request directed to a Resource's `versions`
collection, or to one of its Versions, but the Resource is defined as an
`xref` to another Resource, then the server MUST generate an error
([cannot_doc_xref](#cannot_doc_xref)) and SHOULD indicate that using `?doc`
on this part of the hierarchy is not valid - due to it not technically existing
in document view.

#### Filter Flag

The `?filter` query parameter (flag) on a request indicates that the response
MUST include only those entities that match the specified filter criteria.
This means that any Registry Collection's attributes MUST be modified
to match the resulting subset. In particular:
- If the collection is inlined, it MUST only include entities that match the
  filter expression(s).
- The collection `url` attribute MUST include the appropriate filter
  expression(s) in its query parameters such that an HTTP `GET` to that URL
  would return the same subset of entities.
- The collection `count` attribute MUST only count the entities that match the
  filter expression(s).

The format of the `?filter` query parameter is:

```yaml
filter=<EXPRESSION>[,<EXPRESSION>]
```

Where:
- All `<EXPRESSION>` values within the scope of one `?filter` query parameter
  MUST be evaluated as a logical `AND` and any matching entities MUST satisfy
  all of the specified expressions within that `?filter` query parameter.
- The `?filter` query parameter MAY appear multiple times and if so MUST
  be evaluated as a logical `OR` with the other `?filter` query parameters that
  appear and the response MUST include all entities that match any of the
  individual `?filter` query parameters.

The abstract processing logic would be:
- For each `?filter` query parameter, find all entities that satisfy all
  expressions for that `?filter`. Each will result in a sub-tree of entities.
- After processing all individual `?filter` query parameters, combine those
  sub-trees into one result set and remove any duplicates - adjusting any
  collection `url` and `count` values as needed.

The format of `<EXPRESSION>` is one of:

```yaml
[<PATH>.]<ATTRIBUTE>
[<PATH>.]<ATTRIBUTE>=null
[<PATH>.]<ATTRIBUTE>=[<VALUE>]
[<PATH>.]<ATTRIBUTE><<VALUE>
[<PATH>.]<ATTRIBUTE><=<VALUE>
[<PATH>.]<ATTRIBUTE>><VALUE>
[<PATH>.]<ATTRIBUTE>>=<VALUE>
[<PATH>.]<ATTRIBUTE>!=<VALUE>
[<PATH>.]<ATTRIBUTE><><VALUE>
```

Where:
- `<PATH>` MUST be a dot (`.`) notation traversal of the Registry to the entity
  of interest, or absent if at the top of the Registry request. Note that
  the `<PATH>` value is based on the requesting URL and not the root of the
  Registry. See the examples below. To reference an attribute with a dot as
  part of its name, the JSONPath escaping mechanism MUST be used:
  `['my.name']`. For example, `prop1.my.name.prop2` would be specified as
  `prop1['my.name'].prop2` if `my.name` is the name of one attribute.
- `<PATH>` MUST only consist of valid `<GROUPS>`, `<RESOURCES>` or `versions`,
  otherwise an error ([invalid_data](#invalid_data)) MUST be generated.
- `<ATTRIBUTE>` MUST be the attribute in the entity to be examined.
- Complex attributes (e.g. `labels`) MUST use dot (`.`) to reference nested
  attributes. For example: `labels.stage=dev`.
- A non-`null` `<VALUE>` MUST only be used when referencing scalar attributes.
- A reference to a nonexistent attribute SHOULD NOT generate an error and
  SHOULD be treated the same as a non-matching situation. For example,
  `?filter=myobj.myattr=5` would not match if: `myobj` is missing, `myattr` is
  missing, or `myattr` is not `5`.
- The operators are processed as follows:
  - No operator:
    - When no operator is specified then the response MUST include
      all entities that have the `<ATTRIBUTE>` present with any non-`null`
      value.
  - `=` operator:
    - When `<VALUE>` is `null` then only entities without the specified
      `<ATTRIBUTE>` MUST be included in the response.
    - When a non-`null` `<VALUE>` is specified then `<VALUE>` MUST be the
      desired value of the attribute being examined. Only entities whose
      specified `<ATTRIBUTE>` with this `<VALUE>` MUST be included in the
      response.
    - When `<VALUE>` is absent then the implied `<VALUE>` is an empty string
      and the matching MUST be done as specified in the previous bullet.
  - `!=`, `<>` operators:
    - When `<VALUE>` is `null` then it MUST have the same semantics as
     `?filter=<ATTRIBUTE>` as specified above (present with any non-`null`
     value).
    - When `<VALUE>` is non-`null` then only entities without the specified
      `<ATTRIBUTE>` and `<VALUE>` MUST be included in the response. This MUST
      be semantically equivalent to `NOT(<ATTRIBUTE>=<VALUE>)`, and this also
      means that if `<ATTRIBUTE>` is missing then that attribute will match
      the filter.
  - `<`, `<=`, `>`, `>=` operators:
    - `<VALUE>` MUST NOT be `null`.
    - Only entities with the specified `<ATTRIBUTE>` and `<VALUE>` that matches
      the comparison operator's semantics MUST be included in the response.
    - `<` refers to "less than".
    - `<=` refers to "less than or equal to".
    - `>` refers to "greater than".
    - `>=` refers to "greater than or equal to".
    - Wildcards (`*`) (see below) MUST NOT be present in the `<VALUE>`.

For comparing an `<ATTRIBUTE>` to the specified `<VALUE>`, and for purposes
of sorting (see the [`?sort`](#sort-flag) flag), the type of the attribute
impacts how the comparisons are done:
- For boolean attributes, comparisons MUST be an exact case-sensitive match
  (`true` or `false`). For relative comparisons, `false` is less than `true`.
- For numeric attributes, standard numeric comparisons rules apply. Note that
  numerics MUST NOT be treated as strings for comparison.
- For string attributes, the following rules apply:
  - The strings MUST be compared in a case-insensitive manner.
  - It is STRONGLY RECOMMENDED to use Unicode collation based on en-US.
  - See the next paragraph for information about use of wildcards.
- For timestamp attributes, after the values have been normalized to UTC,
  these follow the same rules as "strings" above.
- For URI/URL variants, these follow the same rules as "strings" above.

See the [`?sort`](#sort-flag) section for more details concerning sorting.

Additionally, wildcards (`*`) MAY be used in string `<VALUE>`s with the
following constraints:
- They MUST only be used when the comparison operator is `=`, `!=` or `<>`.
- The presence of a wildcard indicates that any number of characters MAY
  appear at that location in the `<VALUE>`.
- The wildcard MAY be escaped via the use of a backslash (`\\`) character
  (e.g. `abc\*def`) to mean that the `*` is to be interpreted as a normal
  character and not as a wildcard.
- A `<VALUE>` of `*` MUST be equivalent to checking for the existence of the
  attribute, with any value (even an empty string). In other words, the filter
  will only fail if the attribute has no value at all.

If the request references an entity (not a collection), and the `<EXPRESSION>`
references an attribute in that entity (i.e. there is no `<PATH>`), then if the
`<EXPRESSION>` does not match the entity, that entity MUST NOT be returned. In
other words, a `404 Not Found` would be generated in the HTTP protocol case.

**Examples:**

| Request Path | Filter query | Commentary |
| --- | --- | --- |
| / | `?filter=endpoints.description=*cool*` | Only endpoints with the word `cool` in the description |
| /endpoints | `?filter=description=*CooL*` | Similar results as previous, with a different request URL |
| / | `?filter=endpoints.messages.versions.versionid=1.0` | Only versions (and their owning parents) that have a versionid of `1.0` |
| / | `?filter=endpoints.name=myendpoint,endpoints.description=*cool*& filter=schemagroups.labels.stage=dev` | Only endpoints whose name is `myendpoint` and whose description contains the word `cool`, as well as any schemagroups with a `label` name/value pair of `stage/dev` |
| / | `?filter=description=no-match` | Returns a 404 if the Registry's `description` doesn't equal `no-match` |
| / | `?filter=endpoints.messages.meta.readonly=true` | Only messages that are `readonly` |

Specifying a filter does not imply inlining. Inlining MAY be used at
the same time but MUST NOT result in additional entities being included in
the results unless they are children of a matching leaf entity.

For example, in the following entity URL paths representing a Registry:

```yaml
mygroups/g1/myresources/r1/versions/v1
mygroups/g1/myresources/r1/versions/v2
mygroups/g1/myresources/r2/versions/v1
mygroups/g2/myresources/r3/versions/v1
```

This request:
```yaml
GET /?filter=mygroups.myresources.myresourceid=r1&inline=*
```

would result in the following entities (and their parents along the specified
paths) being returned:

```yaml
mygroups/g1/myresources/r1/versions/v1  # versions are due to inlining
mygroups/g1/myresources/r1/versions/v2
```

However, this request:

```yaml
GET /?filter=mygroups.mygroupid=g2&filter=mygroups.myresources.myresourceid=r1&inline=*
```

would result in the following returned:

```yaml
mygroups/g1/myresources/r1/versions/v1   # from 2nd ?filter
mygroups/g1/myresources/r1/versions/v2   # from 2nd ?filter
mygroups/g2/myresources/r3/versions/v1   # from 1nd ?filter
```

And, this request:

```yaml
GET /?filter=mygroups.mygroupid=g1&filter=mygroups.myresources.myresourceid=r1&inline=*
```

would result in the following being returned:

```yaml
mygroups/g1/myresources/r1/versions/v1   # from 2nd ?filter
mygroups/g1/myresources/r1/versions/v2   # from 2nd ?filter
mygroups/g1/myresources/r2/versions/v1   # from 1st ?filter
```

And, finally this request:

```yaml
GET /?filter=mygroups.mygroupid=g1,mygroups.myresources.myresourceid=r1&inline=*
```

would result in the following being returned:

```yaml
mygroups/g1/myresources/r1/versions/v1
mygroups/g1/myresources/r1/versions/v2
```

Notice the first part of the `?filter` expression (to the left of the "and"
(`,`)) has no impact on the results because the list of resulting leaves in
that subtree is not changed by that search criteria.

#### Inline Flag

The `?inline` query parameter (flag) MAY be used on requests to indicate
whether nested collections/objects, or certain (potentially large) attributes,
are to be included in the response message.

The `?inline` query parameter on a request indicates that the response
MUST include the contents of all specified inlineable attributes. Inlineable
attributes include:
- The `model` attribute on the Registry entity.
- The `modelsource` attribute on the Registry entity.
- The `capabilities` attribute on the Registry entity.
- All [Registry Collection](#registry-collections) types - e.g. `<GROUPS>`,
  `<RESOURCES>` and `versions`.
- The `<RESOURCE>` attribute in a Resource or Version.
- The `meta` attribute in a Resource.

While the `<RESOURCE>` and `<RESOURCE>base64` attributes are defined as two
separate attributes, they are technically two separate "views" of the same
underlying data. As such, the usage of each will be based on the content type
of the Resource, and specifying `<RESOURCE>` in the `?inline` query parameter
MUST be interpreted as a request for the appropriate attribute. In other words,
`<RESOURCE>base64` is not a valid inlineable attribute name.

Use of this feature is useful for cases where the contents of the Registry are
to be represented as a single (self-contained) document.

Some examples:
- `GET /?inline=model`                 # Just 'model'
- `GET /?inline=model,endpoints`       # Model and one level under `endpoints`
- `GET /?inline=*`                     # Everything except 'model','modelsource','capabilities'
- `GET /?inline=model,*`               # Everything, including 'model'
- `GET /?inline=endpoints.messages`    # One level below 'endpoints.messages'
- `GET /?inline=endpoints.*`           # Everything below 'endpoints'
- `GET /endpoints/ep1/?inline=messages.message`     # Just 'message'
- `GET /endpoints/ep1/messages/msg1?inline=message` # Just 'message'

The format of the `?inline` query parameter is:

```yaml
?inline[=<PATH>[,...]]
```

Where `<PATH>` is a string indicating which inlineable attributes to show in
the response. References to nested attributes are represented using a
dot (`.`) notation where the xRegistry collection names along the hierarchy
are concatenated. For example: `endpoints.messages.versions` will inline all
Versions of Messages. Non-leaf parts of the `<PATH>` MUST only reference
xRegistry collection names and not any specific entity IDs since `<PATH>` is
meant to be an abstract traversal of the model.

To reference an attribute with a dot as part of its name, the JSONPath
escaping mechanism MUST be used: `['my.name']`. For example,
`prop1.my.name.prop2` would be specified as `prop1['my.name'].prop2` if
`my.name` is the name of an attribute.

There MAY be multiple `<PATH>`s specified, either as comma separated values on
a single `?inline` query parameter or via multiple `?inline` query parameters.

The `*` value MAY be used to indicate that all nested inlineable attributes
at that level in the hierarchy (and below) MUST be inlined - except `model`,
`modelsource` and `capabilities` at the root of the Registry. These three are
excluded since the data associated with them are configuration related. To
include their data the request MUST include `<PATH>` values of `model`,
`modelsource` or `capabilities`. Use of `*` MUST only be used as the last part
of the `<PATH>` (in its entirety). For example, `foo*` and `*.foo` are not
valid `<PATH>` values, but `*` and `endpoints.*` are.

An `?inline` query parameter without any value MAY be supported and if so it
MUST have the same semantic meaning as `?inline=*`.

The specific value of `<PATH>` will vary based on where the request is
directed. For example, a request to the root of the Registry MUST start with a
`<GROUPS>` name, while a request directed at a Group would start with a
`<RESOURCES>` name.

For example, given a Registry with a model that has `endpoints` as a Group and
`messages` as a Resource within `endpoints`, the table below shows some
`<PATH>` values and a description of the result:

| HTTP `GET` Path | Example `?inline=<PATH>` values | Comment |
| --- | --- | --- |
| / | ?inline=endpoints | Inlines the `endpoints` collection, but just one level of it, not any nested inlineable attributes |
| / | ?inline=endpoints.messages.versions | Inlines the `versions` collection of all messages. Note that this implicitly means the parent entities (`messages` and `endpoints` would also be inlined - however any other `<GROUPS>` or `<RESOURCE>`s types would not be |
| /endpoints | ?inline=messages | Inlines just `messages` and not any nested attributes. Note we don't need to specify the parent `<GROUP>` since the URL already included it |
| /endpoints/ep1 | ?inline=messages.versions | Similar to the previous `endpoints.messages.version` example |
| /endpoints/ep1 | ?inline=messages.message | Inline the Resource document |
| /endpoints/ep1 | ?inline=endpoints | Invalid, already in `endpoints` and there is no `<RESOURCE>` called `endpoints` |
| / | ?inline=endpoints.messages.meta | Inlines the `meta` sub-object of each `message` returned. |
| / | ?inline=endpoints.* | Inlines everything for all `endpoints`. |

Note that asking for an attribute to be inlined will implicitly cause all of
its parents to be inlined as well, but just the parent's collections needed to
show the child. In other words, just the collection in the parent in which the
child appears, not all collections in the parent.

When specifying a collection to be inlined, it MUST be specified using the
plural name for the collection in its defined case.

A request to inline an unknown, or non-inlineable, attribute MUST generate an
error ([invalid_data](#invalid_data)).

Note: If the Registry cannot return all expected data in one response because
it is too large then it MUST generate an error ([too_large](#too_large)). In
those cases, the client will need to query the individual inlineable attributes
in isolation so the Registry can leverage
[pagination](../pagination/spec.md) of the response.

#### Sort Flag

When a request is directed at a collection of Groups, Resources or Versions,
the `?sort` query parameter (flag) MAY be used to indicate the order in which
the entities of that collection are to be returned (i.e. sorted).

The format of the `?sort` query parameter is:

```yaml
?sort=<ATTRIBUTE>[=asc|desc]
```

Where:
- `<ATTRIBUTE>` MUST be the JSONPath to one of the attributes defined in
  collection's entities that will be the primary sort key for the results.
  The attribute MUST only reference a scalar attribute within the top-level
  collection, it MUST NOT attempt to traverse into a nested xRegistry
  collection even if that nested collection is inlined.
- An OPTIONAL "sort order" (`asc` for ascending, `desc` for descending) MAY
  be specified to indicate whether the first entity in the returned collection
  MUST be the "lowest" values (`asc`) or whether it MUST be the "highest"
  value (`desc`). When not specified, the default value MUST be `asc`.

If the specified attribute is not found within the entities being sorted then
implementations SHOULD treat that entity's sort-key value as `NULL`.

When [pagination](../pagination/spec.md) is used to return the results, but
the `?sort` flag is not specified, then the server MUST sort the results on the
entities' `<SINGULAR>id` value in ascending order. When pagination is not used,
it is RECOMMENDED that servers still sort the results by `<SINGULAR>id` (asc)
for consistency.

Sorting MUST be done using the data type comparison rules as specified in the
[filter Flag](#filter-flag) section. However, there are certain situations
that might introduce ambiguity between implementations. For example, not all
persistent stores support `NaNs` (Not-a-Number values), or if the data type of
an attribute changes on a per-instance basis then consistent sorting across
implementations on that attribute might be challenging. While interoperability
is critical, requiring consistency in these edge cases could be excessively
burdensome for implementations. To that end, this specification does not
mandate the exact ordering in these situations, aside from the requirement
that an implementation MUST sort the result the same way each time.

Entities that do not have a value for the specified attribute MUST be treated
the same as if they had the "lowest" possible value for that attribute. If
more than one entity shares the same attribute value then the `<SINGULAR>id`
MUST be used as a secondary sorting key, using the same `asc`/`desc` value
specified for the primary sorting key.

Some examples:
- `GET /endpoints?sort=name`          # Sort (asc) on 'name', then 'endpointid'
- `GET /endpoints/e1/messages?sort=messageid=desc` # Sort (desc) on 'messageid'
- `GET /endpoints?sort=labels.stage`  # Sort (asc) on `labels.stage`, then `endpointid`

### HTTP Header Values

Some attributes can contain arbitrary UTF-8 string content,
and per [RFC7230, section 3][rfc7230-section-3], HTTP headers MUST only use
printable characters from the US-ASCII character set, and are terminated by a
CRLF sequence with OPTIONAL whitespace around the header value.

When encoding an attribute's value as an HTTP header, it MUST be
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
but decoding MUST accept lowercase values.

When performing percent-decoding, values that have been unnecessarily
percent-encoded MUST be accepted, but encoded byte sequences which are
invalid in UTF-8 MUST generate an error
([header_decoding_error](#header_decoding_error)). For example, "%C0%A0" is an
overlong encoding of U+0020, and would be rejected.

Example: a header value of "Euro &#x20AC; &#x1F600;" SHOULD be encoded as
follows:

- The characters, 'E', 'u', 'r', 'o' do not require encoding.
- Space, the Euro symbol, and the grinning face emoji require encoding.
  They are characters U+0020, U+20AC and U+1F600 respectively.
- The encoded HTTP header value is therefore "Euro%20%E2%82%AC%20%F0%9F%98%80"
  where "%20" is the encoded form of space, "%E2%82%AC" is the encoded form
  of the Euro symbol, and "%F0%9F%98%80" is the encoded form of the
  grinning face emoji.

### Error Processing

If an error occurs during the processing of a request, even if the error was
during the creation of the response (e.g. an invalid `?inline` value was
provided), then an error MUST be generated and the entire request MUST be
undone.

In general, when an error is generated, it SHOULD be sent back to the client.
However, this MAY not happen if the server determines there is a good reason
to not do so - such as due to security concerns.

Most of the error conditions mentioned in this specification will include a
reference to one of the errors listed in this section. While it is RECOMMENDED
that implementations use those errors (for consistency), they MAY choose to use
a more appropriate one (or a custom one).

When an error is transmitted back to clients, it SHOULD adhere to the format
specified in this section - which references the [Problem Details for HTTP
APIs](https://datatracker.ietf.org/doc/html/rfc9457) specification, and when
used, MUST be of the following form:

```yaml
HTTP/1.1 <CODE>
Content-Type: application/json; charset=utf-8

{
  "type": "<URI>",
  "instance": "<URL>",
  "title": "<STRING>",
  "detail": "<STRING>", ?
  ... error specific fields ...
}
```

Where:
- `<CODE>` is the HTTP response code and status text (e.g. `404 Not Found`).
- "type" is a URI to the error definition.
- "instance" is a URL to the entity being processed when the error occurred.
- "title" is a human-readable summary of the error.
- "detail" is additional information about the error. Typically will include
  suggestions for how to fix the error.

`<CODE>`, `"type"`, `"instance"` and `title` fields are REQUIRED. All other
fields are OPTIONAL unless overwise stated as part of the error definition. Any
substitutable information (as denoted by the `<...>` syntax) defined as part
of an error MUST be populated appropriately.

HTTP response codes and status text are defined in the [HTTP
Semantics](https://datatracker.ietf.org/doc/html/rfc9110#name-status-codes)
specification.

In the following list of errors, the `Code`, `Type` and `Instance` values MUST
be as specified. The other field values are recommendations and MAY be modified
as appropriate, including being specified in a language other than English.

<!-- start-err-def -->

#### ancestor_circular_reference

* Type: `https://github.com/xregistry/spec/blob/main/core/spec.md#ancestor_circular_reference`
* Code: `400 Bad Request`
* Instance: `<URL TO THE VERSION BEING PROCESSED>`
* Title: `The assigned "ancestor" value (<ANCESTOR VALUE>) creates a circular reference`

#### api_not_found

* Type: `https://github.com/xregistry/spec/blob/main/core/spec.md#api_not_found`
* Code: `404 Not Found`
* Instance: `<REQUEST URL>`
* Title: `The specified path (<INVALID PATH>) is not supported`

#### bad_flag

* Type: `https://github.com/xregistry/spec/blob/main/core/spec.md#bad_flag`
* Code: `400 Bad Request`
* Instance: `<REQUEST URL>`
* Title: `The specified query parameter (<QUERY PARAMETER>) is not allowed in this context`

#### bad_request

This error is purposely generic and can be used when there isn't a more
condition-specific error that would be more appropriate. Implementations
SHOULD attempt to use a more specific error when possible.

* Type: `https://github.com/xregistry/spec/blob/main/core/spec.md#bad_request`
* Code: `400 Bad Request`
* Instance: `<REQUEST URL>`
* Title: `The request cannot be processed as provided`

#### cannot_doc_xref

* Type: `https://github.com/xregistry/spec/blob/main/core/spec.md#cannot_doc_xref`
* Code: `400 Bad Request`
* Instance: `<URL TO THE RESOURCE BEING RETRIEVED>`
* Title: `Retrieving the document view of an xref'd Resource's Versions is not possible`

#### capability_error

* Type: `https://github.com/xregistry/spec/blob/main/core/spec.md#capability_error`
* Code: `400 Bad Request`
* Instance: `<URL TO THE XREGISTRY SERVER>`
* Title: `There was an error in the capabilities provided`

#### compatibility_violation

* Type: `https://github.com/xregistry/spec/blob/main/core/spec.md#compatibility_violation`
* Code: `400 Bad Request`
* Instance: `<URL TO THE VERSION THAT CAUSED THE VIOLATION>`
* Title: `The request would cause one or more Versions of this Resource to violate the Resource's compatibility rules (<COMPATIBILITY ATTRIBUTE VALUE>)`
* Detail: `<LIST OF versionid VALUE THAT WOULD BE IN VIOLATION>`

#### data_retrieval_error

* Type: `https://github.com/xregistry/spec/blob/main/core/spec.md#data_retrieval_error`
* Code: `500 Internal Server Error`
* Instance: `<REQUEST URL>`
* Title: `The server was unable to retrieve all of the requested data`

#### defaultversionid_not_allowed

* Type: `https://github.com/xregistry/spec/blob/main/core/spec.md#defaultversionid_not_allowed`
* Code: `400 Bad Request`
* Instance: `<URL TO THE RESOURCE BEING PROCESSED>`
* Title: `"defaultversionid" is not allowed to be specified`

#### details_required

* Type: `https://github.com/xregistry/spec/blob/main/core/spec.md#details_required`
* Code: `400 Bad Request`
* Instance: `<URL TO THE ENTITY BEING PROCESSED>`
* Title: `$details suffixed is needed when using PATCH for this Resource`

#### extra_xregistry_headers

* Type: `https://github.com/xregistry/spec/blob/main/core/spec.md#extra_xregistry_headers`
* Code: `400 Bad Request`
* Instance: `<URL TO THE ENTITY BEING PROCESSED>`
* Title: `xRegistry HTTP headers are not allowed on this request`
* Detail: `<LIST OF HEADERS>`

#### header_decoding_error

* Type: `https://github.com/xregistry/spec/blob/main/core/spec.md#header_decoding_error`
* Code: `400 Bad Request`
* Instance: `<REQUEST URL>`
* Title: `The value ("<HEADER VALUE>") of the HTTP "<HEADER NAME>" header cannot be decoded`

#### invalid_character

* Type: `https://github.com/xregistry/spec/blob/main/core/spec.md#invalid_character`
* Code: `400 Bad Request`
* Instance: `<URL TO THE ENTITY BEING PROCESSED>`
* Title: `An invalid character (<THE CHARACTER>) was specified in an attribute's name (<FULL ATTRIBUTE NAME>)`

#### invalid_data

* Type: `https://github.com/xregistry/spec/blob/main/core/spec.md#invalid_data`
* Code: `400 Bad Request`
* Instance: `<URL TO THE ENTITY BEING PROCESSED>`
* Title: `The data provided for "<ATTRIBUTE/PARAMETER NAME>" is invalid`
* Detail: `<THE INVALID DATA>`

#### method_not_allowed

* Type: `https://github.com/xregistry/spec/blob/main/core/spec.md#method_not_allowed`
* Code: `405 Method Not Allowed`
* Instance: `<REQUEST URL>`
* Title: `The specified HTTP method (<INVALID METHOD>) is not supported for: <REQUEST URL>`

#### mismatched_epoch

* Type: `https://github.com/xregistry/spec/blob/main/core/spec.md#mismatched_epoch`
* Code: `400 Bad Request`
* Instance: `<URL TO THE ENTITY BEING PROCESSED>`
* Title: `The specified epoch value (<INVALID EPOCH>) does not match its current value (<CURRENT EPOCH>)`

#### mismatched_id

* Type: `https://github.com/xregistry/spec/blob/main/core/spec.md#mismatched_id`
* Code: `400 Bad Request`
* Instance: `<URL TO THE ENTITY BEING PROCESSED>`
* Title: `The specified <SINGULAR TYPE NAME> ID value (<INVALID ID>) needs to be "<EXPECTED ID>"`

#### misplaced_epoch

* Type: `https://github.com/xregistry/spec/blob/main/core/spec.md#misplaced_epoch`
* Code: `400 Bad Request`
* Instance: `<URL TO THE ENTITY BEING PROCESSED>`
* Title: `The specified "epoch" value needs to be within a "meta" sub-object`

#### missing_versions

* Type: `https://github.com/xregistry/spec/blob/main/core/spec.md#missing_versions`
* Code: `400 Bad Request`
* Instance: `<URL TO THE ENTITY BEING PROCESSED>`
* Title: `At least one Version needs to be included in the request`

#### model_compliance_error

* Type: `https://github.com/xregistry/spec/blob/main/core/spec.md#model_compliance_error`
* Code: `400 Bad Request`
* Instance: `<URL TO THE XREGISTRY SERVER>`
* Title: `The model provided would cause one or more entities in the Registry to become non-compliant`
* Detail: `<LIST OF NON_COMPLIANT XIDs>`

#### model_error

* Type: `https://github.com/xregistry/spec/blob/main/core/spec.md#model_error`
* Code: `400 Bad Request`
* Instance: `<URL TO THE XREGISTRY SERVER>`
* Title: `There was an error in the model definition provided at <JSON PATH TO ERROR>`
* Detail: `<PROBLEMATIC JSON SNIPPET>`

#### multiple_roots

* Type: `https://github.com/xregistry/spec/blob/main/core/spec.md#multiple_roots`
* Code: `400 Bad Request`
* Instance: `<URL TO THE RESOURCE BEING PROCESSED>`
* Title: `The operation would result in multiple root Versions which is not allowed by this Resource type`

#### not_found

* Type: `https://github.com/xregistry/spec/blob/main/core/spec.md#not_found`
* Code: `404 Not Found`
* Instance: `<URL TO THE ENTITY BEING PROCESSED>`
* Title: `The specified entity cannot be found`

#### readonly

* Type: `https://github.com/xregistry/spec/blob/main/core/spec.md#readonly`
* Code: `400 Bad Request`
* Instance: `<URL TO THE ENTITY BEING PROCESSED>`
* Title: `Updating a read-only entity (<XID OF ENTITY>) is not allowed`

#### required_attribute_missing

* Type: `https://github.com/xregistry/spec/blob/main/core/spec.md#required_attribute_missing`
* Code: `400 Bad Request`
* Instance: `<URL TO THE ENTITY BEING PROCESSED>`
* Title: `One or more mandatory attributes are missing`
* Detail: `<LIST OF MANDATORY ATTRIBUTES>`

#### server_error

This error MAY be used when it appears that the incoming request was valid but
something unexpected happened in the server that caused an error condition.

* Type: `https://github.com/xregistry/spec/blob/main/core/spec.md#server_error`
* Code: `500 Internal Server Error`
* Instance: `<REQUEST URL>`
* Title: `An unexpected error occurred, please try again later`

#### too_large

* Type: `https://github.com/xregistry/spec/blob/main/core/spec.md#too_large`
* Code: `406 Not Acceptable`
* Instance: `<REQUEST URL>`
* Title: `The size of the response is too large to return in a single response`
* Detail: `<THE NAMES OF THE FIELDS THAT ARE TOO LARGE>`

#### too_many_versions

* Type: `https://github.com/xregistry/spec/blob/main/core/spec.md#too_many_versions`
* Code: `400 Bad Request`
* Instance: `<URL TO THE ENTITY BEING PROCESSED>`
* Title: `The request is only allowed to have one Version specified`

#### unknown_attribute

* Type: `https://github.com/xregistry/spec/blob/main/core/spec.md#unknown_attribute`
* Code: `400 Bad Request`
* Instance: `<URL TO THE ENTITY BEING PROCESSED>`
* Title: `An unknown attribute (<ATTRIBUTE NAME>) was specified`

#### unknown_id

* Type: `https://github.com/xregistry/spec/blob/main/core/spec.md#unknown_id`
* Code: `400 Bad Request`
* Instance: `<URL TO THE ENTITY BEING PROCESSED>`
* Title: `The "<SINGULAR NAME OF THE ENTITY TYPE>" with the ID "<UNKNOWN ID>" cannot be found`

#### unsupported_specversion

* Type: `https://github.com/xregistry/spec/blob/main/core/spec.md#unsupported_specversion`
* Code: `400 Bad Request`
* Instance: `<THE REQUEST URL>`
* Title: `The specified "specversion" value (<SPECVERSION SPECIFIED>) is not supported`

#### versionid_not_allowed

* Type: `https://github.com/xregistry/spec/blob/main/core/spec.md#versionid_not_allowed`
* Code: `400 Bad Request`
* Instance: `<URL TO THE ENTITY BEING PROCESSED>`
* Title: `A "versionid" is not allowed to be specified`
* Detail: `<versionid SPECIFIED>`


<!-- end-err-def -->

---

### Events

xRegistry defines a set of events that SHOULD be generated when changes are
made to the entities within a Registry. See the [xRegistry Events](./events.md)
specification for more information.

[rfc7230-section-3]: https://tools.ietf.org/html/rfc7230#section-3
[rfc3986-section-2-1]: https://tools.ietf.org/html/rfc3986#section-2.1
[rfc7230-section-3-2-6]: https://tools.ietf.org/html/rfc7230#section-3.2.6
[rfc3339]: https://tools.ietf.org/html/rfc3339
