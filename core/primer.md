# xRegistry Primer

<!-- no verify-specs -->

## Abstract

This non-normative document provides an overview of the [xRegistry
specification](https://github.com/xregistry/spec/blob/main/core/spec.md). It is
meant to complement the xRegistry specification to provide additional background
and insight into the history and design decisions made during the development of
the specification. This allows the specification itself to focus on the
normative technical details.

## Table of Contents

- [History](#history)
- [Motivation](#motivation)
- [Design Goals](#design-goals)
- [Representations](#representations)
- [Possible Use Cases](#possible-use-cases)
- [Design decisions or topics of
  interest](#design-decisions-or-topics-of-interest)

## History

The CNCF Serverless Working group was originally created by the CNCF's Technical
Oversight Committee to investigate Serverless Technology and to recommend some
possible next steps for some CNCF related activities in this space. After
creating [CloudEvents](https://github.com/cloudevents) as a foundation for an
interoperable ecosystem for event-driven applications the next step was to
create a metadata model for declaring CloudEvents, their payloads and
associating those declarations with application endpoints. As a result, the
xRegistry (extensible registry) specification was created.

xRegistry was initially part of CloudEvents, called "CloudEvents Discovery" but
later moved into it's own repository.

## Motivation

While CloudEvents are harmonizing different event structures across event
providers and increase interoperability between different brokers and their
protocols, they do not address:

- **Discovery:** Where to produce/consume events? What endpoints exist?
- **Validation:** How to validate event structures?
- **Versioning:** How to version metadata describing events – and see which
  versions exist?
- **Serialization:** How are events serialized? How do their envelope (if any)
  and formats (XML / JSON Schema) look like?
- **Extension Discovery:** How to identify which events using which specific
  extensions?

Schema registries can provide an answer to these questions, but just like event
brokers, there are multiple registries, such as the Confluent Schema Registry,
the Azure Event Hubs Registry or the Apicurio Registry. When an event travels
through multiple brokers, its schema has to be introduced to the broker's
registry and clients later have to deal with the implementation differences
between different registries, for example when trying to validate an event
structure. This hinders the interoperability of event brokers CloudEvents had in
mind. xRegistry therefore comes in with a similar motivation to CloudEvents:
Harmonize another piece of technology in the messaging / eventing ecosystem to
increase interoperability and decouple event handling from broker products and
protocols.

Even though xRegistry was built with eventing in mind, the concept of this
registry specification is far more powerful and can be used for the exchange for
any type of message. Take a look at the [Possible Use
Cases](#possible-use-cases) for examples outside the eventing world.

## Design Goals

- **Interoperability:** Enable effortless discovery, validation and versioning
  of resources.
- **Standardization:** Establish a high level structure for managing resource
  metadata behind which vendors can unite.
- **Extensibility:** Accommodate future innovations by allowing for the
  definition of custom attributes and extensions tailored to specific needs
  – not only for the happy path, but errors as well.
- **Flexibility:** Support various resource types, protocols (MQTT, AMQP, Kafka,
  NATS, HTTP..) and schema languages (JSON Schema, Avro Schema, Protobuf..)
  – not just CloudEvents.
- **Simplicity:** Allow simple use cases that do not need versioning of
  resources or a full blown schema registry on the server.

### Non-Goals

- **Authentication and Authorization:** Rely on established security standards
  depending on the registry representation.
- **Relationships between event channels:** Focus on precisely describing a
  single event channel before standardizing the relationships between event
  channels.

## Representations

An xRegistry can be represented in the different ways: a JSON file, a static
file server and an API server. When building up this spec the API server had the
highest priority, followed by the file representation and the static file server
as an option to transition between the first two. To enable this transition, one
of the design goals is the symmetry between all representations.

Whenever registries get large, you will realistically want to use the API server
or CLI to create the registry and then use its export function to generate files
for the file or static file server representation.

### File

The registry is represented as a single JSON file.

The primary use case for this representation is a registry whose purpose is to
be used in cases where file-based access is preferred over network-based access.
This could be a project on your local machine or a public git repository, where
the registry basically becomes a declaration manifest of the application(s). If
you are new to xRegistry and are just trying to get the idea of the project,
this is a great point to start.

Writing up a registry by hand can be a great way of getting the idea, but it can
get tedious quickly. This is when you want to use the API server.

### Static File Server

The registry is represented by multiple JSON files, where each one represents a
single entity within the registry, served via a static file server (e.g. S3 or
similar) that follows the folder and file structure of the API server.

The primary use case for this representation is the transition between File and
API Server representation. To allow for sharing of individual entities of the
registry rather than the entire registry as a single JSON document, splitting up
your single JSON file into multiple ones and structuring them in different
folders can keep things easy.

Another benefit of this representation is that you only have to rent storage,
but no compute units. You could spin up an xRegistry using GitHub Pages, just
like a Helm registry. You save money and don't have to worry about maintaining a
compute unit.

Since the static file server is read-only, adding resources to the registry is
only possible by rebuilding the server and file structure, e.g. via pipelines.
If you want to directly write to the server or need sophisticated searching and
filtering, you might consider using the API server instead. Adding server logic
to the static file server to make up for the features of the API server is
considered an anti pattern.

### API Server

The API server is the most sophisticated representation of xRegistry. When you
have multiple teams that are using the same registry with distributed ownership
of the managed resources, therefore differentiated authorization – then the API
server is your way to go. This could apply to large organizations, enterprises
etc.

The primary use case of the API server is sharing resources with multiple
end-users and allowing direct write access to the server. You won't have to
generate files and split them up in directories like in the static file server
and can make use of the server-side logic like searching, filtering and export
options.

Running the API server requires you to set up a compute unit and a persistence
layer and maintain both. In exchange you get all the benefits listed above.
While starting with the API server might be a little more work upfront, it saves
you from migrating representations as your registry grows.

## Possible Use Cases

### CloudEvents

Since xRegistry emerged from the CloudEvents project and initially was called
"CloudEvents Discovery" the obvious use case is to manage all the CloudEvents of
your event-driven architecture inside xRegistry. The spec supports "CloudEvents"
as a format and allows you to define further restrictions on how your
CloudEvents look, what extensions they use or which fields are required for your
specific use-case even though the original spec marks them as optional. In
addition, the `dataschema` attribute of a CloudEvent can then point to a
xRegistry schema document making this two projects that work hand in hand.

### Business objects

When defining the schemas of business objects in an enterprise, xRegistry can be
the schema store for these definitions. One can then reference them in a data
catalogue as well as in OpenAPI and AsyncAPI documents without repeating the
schemas for the actual business objects.

### Metadata files in repositories

Open source repositories could provide an xRegistry represented as a simple JSON
file on the top level of the folder structure and list all metadata files this
repository contains like a `package.json`. This would allow machine-readable
access to project dependencies and configurations as well as consistent
management of metadata across different tools and environments.

## Design decisions or topics of interest

### Resource.ID vs Resource.Version.ID

Resources, like all xRegistry entities, have unique `id` values. Resource
`id`s are often user-friendly values that often have an implied semantic
meaning of the purpose of the underlying Resource document. Also, since they
are static values and as the Resource changes over time (meaning, new Versions
are created), it's important for end-users to have a static URL reference to
the default Version of the Resource.

Versions of a Resource, on the other hand, might change quite often and the
`id` isn't meant to convey the purpose of the underlying entity, rather it is
meant to uniquely specify its "version number". As such, the semantics
meaning and usage of the two `id` values are quite different. This means that
there might be times when they are the same value. However, while this is
allowable, it has no influence on any specification defined semantics of the
xRegistry model. As a result, implementations might want to avoid using `id`
values that could appear on a Resource and one of its Versions simply to avoid
potential confusion for their end-users.

### Valid Characters

The xRegistry specification restricts the allowable characters for attribute
and map key names. While it can be considered overly restrictive, for example
uppercase characters are not permitted, this was done because considerations
had to be made to take into account where these names might appear.

Some of the challenges:

- attribute and key name might appear as HTTP headers, which are
  case insensitive. On the surface this would mean that simply not allowing
  more than one name of different cases would suffice. However, in the case
  of the name being part of a open-ended extension (e.g. allowable due to a
  `*` defined attribute), the server has no way of knowing its proper case.
  And when they're serialized in the HTTP body, case then matters.
- some network proxying software limit the allowable characters that can
  appear in HTTP header names by default. For example, nginx will drop all
  HTTP headers that include underscore (`_`) characters. While there are most
  likely configuration flags to disable this behavior, it might not always
  be possible (or easy) for xRegistry implementations to modify those
  networking components.
- often attribute names, or object property names, are mapped into code
  variable or properties within code structures. While many programming
  languages allow for a mapping from those names to their serialization
  names, often these mapping can introduce pain - either because they require
  additional work/configuration or simply due to errors being introduced
  by not using the language specific default mapping.

So rather than raising the bar for installation, maintenance, and debugging
(detecting the possible issues mentioned above), it was deemed better to
simply avoid the problem (and hopefully increase interoperability) by just
limiting the allowable characters.

Note though, map key names allow more characters than well-define object
attribute names because map key names are not usually mapped to well defined
variable or structure property names - they're usually just stored as
"strings" a map data structure.

### Extensions

- it's RECOMMENDED that all extensions be defined in advance as part of the
  model. However, the spec does support an extension of "\*" to allow for
  unknown/runtime-provided extensions. Since extensions can appear in case-
  insensitive situations (e.g. http header) we can't know the case of them
  when storing in the backend. As a result, all attributes and key names MUST
  be lowercase.

- "default" Resource is just a pointer, NOT a set of default values
- we allow for implicit creation of a resource's tree rather than requiring
  multiple create operations - just for convenience
- if/when we support serializing in non-json formats, we'll need to define
  the serialization rules. E.g. when attributes appear as xml attributes vs
  nested elements
- when hasdocument=false, we might need to talk about when ?meta appears on the
  various URLs (self, defaultversionurl, location,...). Right now its presence
  will match what was used in the request (either explicitly or implicity).
  So GET resource?meta or GET group?inline both ask for metadata
- xRegistry- headers: first "-" separates xRegistry from attribute name,
  next "-" separates attribute name from key, any subsequent "-" is part
  of the key name. E.g xRegistry-labels-abc-def:xxx => labels["abc-def"]=xxx
- impact of "\*required" flags at multiple levels
- why we don't use underscore in our property names, tho legal to do so
  - not all http proxies (e.g. nginx) pass them along by default
  - so, while spec allows underscores, use at your own risk
- discuss any potential semantic gotchas when one attribute is required
  but a nested attribute is optional, or also required (and visa-versa)
  - reminder: clientrequired=true means serverrequired=true as well, else error
- how MIGHT someone implement multi-tenancy with xRegistry
  - and layers of xRegistries to get multi-level grouping ??

### Deleting entities

The "delete" operation typically has two variants:

- DELETE .../ID[?setdefaultversionid=vID]
- DELETE .../COLLECTION[?setdefaultversionid=vID]

where the first will delete a single entity, and the second can be used to
delete multiple entities. In the second case there are a couple of design
points worth noting:

- if the HTTP body is empty, then the entire collection will be deleted.
  If the collection is `versions`, then the owning Resource must also be
  deleted since a Resource must always have at least one Version
- if the HTTP contain an array, then an empty (zero item) array is valid,
  but it will have no change on the server since there are not items listed
  to be deleted
- if the array is not empty and one of the items in there is already deleted,
  or never existed at all, then rather than generating an error (e.g. a `404`),
  the server will ignore this condition and continue processing the list.
  This is because the net result will be what the user is asking for.
  Note, that this is different from `DELETE ../ID` case where if the
  referenced entity can not be found then a `404` must be generated.
- when the `?setdefaultversionid` query parameter is specified (when
  deleting Version) then it will be applied after all requested items have
  been deleted successfully. It can be used even if the current "default"
  Version isn't being deleted. Note that a `404` in the `DELETE .../ID` case
  is an error and no changes to the "default" Version will occur.

### Detection of Referenced Resources

The xRegistry specification allows for Resources to appear in multiple Groups
via use of the `xref` feature. This could lead to situations where a user
deletes a Resource without knowing that other Resources reference it -
resulting in "dangling pointers". The specification does not define any
mechanism by which a user can determine if a Resource is the target of an
`xref`, or how many other Resources might reference it, in order to avoid
this situation. However, implementations may choose to take some action to
help users if they wish. For example, provide some kind of "warning" of the
impending "dangling pointer" state prior to doing the delete, or providing
some kind of "xref counter" extension on the target Resource. The specification
might consider adding some feature to address this in the future, but as of now
it is left as an implementation choice.

### Shared/Referenced Resources

As discussed above, Resource may appear in multiple Groups via use of the
`xref` feature. Users of the Registry may wish to consider how best to manage
these "shared" Resources within their associated Groups. For example, if a
Resource might be removed from any of the Groups it is a member of, then it
might be best to create a dedicated "shared resources" type of Group so that
it can have a lifecycle that is independent of its association of any other
Group. Similarly, choosing an initial Group for the Resource could be a
critical decision as it can not be changed later on, and that Group ID will
be part of the Resource's unique identifier forever.

Additionally, how the implementation of the xRegistry manages
access-control-rights of Resources (often via Groups) might influence the
initial placement into a Group of a new Resource.

# Default Version and Maximum Versions

Each Resource type can specify the maximum number of Versions that the
server must save. Once that limit is reached then it must delete Versions
to stay within the limit - by deleting oldest Versions first. However, since
tagging a Version as "default" marks that Version as special, this pruning
logic must skip the "default" Version. There is one exception to this rule.
If the maximum Versions is set to 1 then when a new Version is created, that
Version will become the "default" Version regardless of whether or not the
user asked for it to be.

In general, during an operation that creates, updates or deletes the Versions
of a Resource, the following logic is applied:

- Modify the Versions collection as requested
- Apply the "default" processing logic by setting (or not) which Version is the
  "default"
- If the number of Versions exceeds the maximum allowed Versions then, starting
  with the oldest, keep deleting until the collection is within the limit.
  Except if the limit is 1, in which case if a new Version is created then it
  it tagged as "default"

Let's walk through a complex example:

- Max allowed Versions is 2
- Initially the following Versions exist: v4, v2 (default)
- Max allowed Versions is now set to 0 (meaning unlimited)
- New Versions are created in this order: v5 (default=true), v6, v7
- The resulting Versions are (newest to oldest): v7, v6, v5 (default), v4, v2
- The maximum allowed Version is now set to 1, this will cause pruning
- The result is: v5. Note that it is not v7 because v5 was tagged as "default"
- A new Version (v8) is created
- The result is: v8 regardless of whether v8 was created with isdefault=true or
  not

# Potential Extensions

- `createdby`, `modifiedby`<br>
  These are related to the `createdat` and `modifiedat` attributes in that
  they would normally be updated at the same time as their corresponding
  `*at` attribute, and are use to track the identity of the person or
  component that performed the related operation.

  The xRegistry specification does not define these since it does not define
  any authentication mechanisms, or even manage tracking of these identities.
  However, if an implementation does track this information, these attributes
  might be of interest.

# Why Epoch?

Why such an unusual name? As the specification describes, `epoch` is used as a
way to help detect when an entity has been modified. It is very similar to
HTTP's [ETag](https://datatracker.ietf.org/doc/html/rfc9110#name-etag)
header.

When choosing a name for this attribute the most obvious choices revolved
the word `version`. However, the potential overlapping naming and differing
semantics conflicts with the Version entity of the model could lead to
confusion. We decided to use `epoch` because "epoch" is about "time",
which is indirectly related to what this attribute is meant to convey: has
this entity's history changed?

Additionally, the word is unique enough that the chances of people assuming
they know what it means due to some other usage in this technology space
seemed unlikely. In fact, use of this word might pique people's curiosity
and cause them to look it up in the specification to find out more about it.

# Naming and Case Sensitivity

The following explains some of the reasoning behind the casing and case
sensitivity rules in the specification.

- Attributes must be lower case.
  Attributes, include extensions attributes, can appear in many different
  locations. When serialized as part of the xRegistry metadata for an entity,
  they would appear in a JSON object as an attribute name and in those cases
  the case of the name matters. However, that same name might also appear in
  an HTTP header name - where its case is not relevant, and can be freely
  changed by middleware.

  Since it is possible for unknown attributes to appear in case insensitive
  locations, it would then be impossible for implementations of the
  specification to know what the true/intended case of the attribute name
  should be. To avoid mismatches, confusion and interoperability issues, the
  specification requires all attribute names to be in lower case. This avoids
  complicated logic to guess as to the proper case of these names.

- Groups and Resources must be lower case.
  The plural version of the Group and Resource type names can appear in URLs
  (which is case sensitive). Additionally, the plural variant can also appear
  in attribute names (e.g. COLLECTION attributes), and as discussed above,
  attributes must be lower case.

  The singular version of the Group and Resource type names, can also appear
  in the RESOURCE attributes, which (again) means they must be lower case.

  For these reasons, both the plural and singular names of Group and Resource
  types must be defined as lower case.

- IDs are case sensitive and case insensitive.
  Entity identifiers (`id`s), never appear as attribute or HTTP header
  names. Meaning, they never appear in case insensitive locations, so they
  do not have the same constraints that attributes, Groups or Resources do.
  For this reason, IDs are not restricted to using just lower case letters.
  This then also means that when there is a "look-up" done by an ID, it must
  be done in a case sensitive way.

  However, there is another aspect of IDs that needs to be taken into account:
  the human factor. Despite them being case sensitive, if the specification
  allowed for two entities at the same location in the data model to exist
  where they had the same IDs except for their case, it could make things very
  error prone for users and leave them with a bad user experience.

  For this reason, while the processing of IDs is treated as case sensitive
  values, the specification requires that IDs must be case insensitive unique
  within the scope of its parent entity.

  While it may have been more consistent to just require IDs to be lower case
  like many of the other names in the specification, it was deemed unnecessary
  from a technical perspective. Additionally, IDs are often exposed to end
  users as unique identifiers (almost as a "name"), allowing mixed case can
  provider a better user experience.

  Additionally, treating them in a case insensitive way could lead to
  inconsistencies and frustration for users. If a user purposely used a certain
  casing pattern, but then someone else use a different pattern for the same
  entity, it is possible that one of those users would end up seeing an
  unexpected casing and could be confused or believe there was an error.

  All of these concerns are avoided by requiring IDs to be stored and compared
  in case insensitively.

# Why the 58 character limit on Group and Resource names?

Attribute names and key names are limited to 63 characters, so why are
Group and Resource names limited to only 58? Because when they appear as
Collection attributes and we append `url` or `count` to them they still have
to fit within the 63 character limit, and so we need to take into account
the length of the word `count`.

# Why must Group type and Resource type names be valid attribute names?

Since Group type and Resource type names will appear as attribute names (e.g.
`GROUPScount` and `RESOURCEurl`), the character set (and length) of their
names need to be restricted in the same way as a attribute names.

# Choosing unique Group and Resource names

Aside from choosing names that give some descriptive meaning to the purpose
of these entities, care should be taken when choosing names for entities that
might be imported into other Registries. For example, Group names are often
suffixed (or prefixed) with domain (or company) specific words to avoid
name collisions with other similarly named entities. This might be useful
for Resource names too (if they might co-exist under shared Groups), but
normally ensuring uniqueness at the Group level is sufficient.

# Are `self` and `shortself` attributes static?

In general any URL reference to an entity in the Registry should remain
static for the lifetime of the entity, otherwise anything persisting that
reference will break when it attempts to use it. So, in this sense, yes
these attributes should be static in general. However, the specification
can not mandate this because there may be times when the risk of breaking
existing references becomes necessary.

For example, perhaps a Registry needs to move to a new host, and the old
one is no longer available, even to offer a redirect. Or, if the server
needs to switch to a new "URL shortener" service and so all of the "shortself"
values need to change.

Obviously, situations like these should be rare but the specification needs
to allow for them.

# Why does an unknown query parameter not generate an error?

People have identified cases where query parameters might be added to request
URLs without the client (or developer) having control to prevent it. It might
be client-side tooling or intermediaries (e.g. proxies) that might modify
the URL - for example to add tracking or end-to-end tracing information.

To avoid these clients not being able interact with an xRegistry deployment,
the authors chose to have the server ignore unknown query parameters. It is
worth noting that the specification says they SHOULD be ignored, not that they
MUST be ignored. So there is room for an implementation to be very picky if
needed, but at the risk of potentially causing interoperability problems.
