# OpenAPI request roles and Resource Meta schemas

<!-- no verify-specs -->
<!-- words: registrywriteinput registrypatchinput writeinput patchinput -->
<!-- words: metawriteinput metapatchinput readonly modelsource xref -->
<!-- words: registryentity standalone validators -->

The generator separates client request structures from completed response
structures. This changes generated request/Meta type APIs, not the Core
protocol. Clients should regenerate their OpenAPI types rather than populate
server fields to satisfy a response schema.

## Registry requests and responses

Root `PUT` uses `RegistryWriteInput`; root `PATCH` uses
`RegistryPatchInput`. Root GET and update responses continue to use the
completed `RegistryEntity` response requirements. Existing Group and
metadata-only Resource writes also use input roles; Version collection writes
use Version inputs, not completed response schemas. The only added routes are
the Resource metadata writes described below.

A normal replacement/write request retains genuinely client-required model
attributes: required, writable attributes without a declared default.
Server-managed identity/navigation fields and server/default obligations are
not made mandatory client input. A PATCH can omit attributes that are retained
on the server, including required attributes. Explicit deletion of a required
mutable attribute without a default is still invalid structurally.

This is not a recursive "make everything optional" projection. An ordinary
object, map or array attribute present in PATCH is a full replacement value.
Required nested members remain required unless supplied by a declared default
or server-controlled model attribute. Nested registry collection entities use
their appropriate write/patch roles and remain non-null objects. Attribute
resets do not delete collection entities; see
[updating nested collections](../core/spec.md#updating-nested-registry-collections).

Ignored read-only inputs are described without falsely type-checking their
discarded values. IDs and epoch are exceptions: if supplied, their structural
kinds remain checked and the server performs identity/concurrency validation.
The client can supply `createdat`/`modifiedat`; their Core null/reset behavior
is not confused with an ignored read-only field.

The input envelopes include applicable Core members before closure, including
collection URL/count fields, `icon` and Version `contenttype`. Ignored
navigation values do not constrain writes; supplied mutable values retain
their types. A [schema hint](../core/spec.md#design-json-schema-keyword) is
allowed on a single-entity message, not nested entities or collection maps.

Completed response schemas keep the existing mandatory Core fields and add
required model attributes, including required defaulted and read-only values.
Use an OpenAPI read validator when checking those read-only requirements.

## Effective model and retained state

Request schemas are structural descriptions, not full Core validators.
Creation after PATCH, server provisioning, defaults, permissions, retained
selectors and final conditional/model constraints require server state.
A supplied writable selector constrains its active conditional members;
inactive names need an applicable wildcard. Omitted, reset or read-only
selectors admit possible conditional/wildcard alternatives without inventing
retained state. The server checks final activation and required attributes
against the [effective model](../core/model.md#attributesstringifvalues).

A request that supplies `modelsource` can replace/reset the model before
other attributes are processed. That request takes an explicit model-change
branch: known Core structure is checked, but old generated model properties
and requirements are not asserted against the new model. The server validates
the resulting state against its effective model.

Response model constraints describe the model used for generation. A client
changing the model must obtain the corresponding updated description or
validate model-dependent response data against that effective model. The
generator cannot infer a future model or silently certify graph semantics.

## Resource routes, metadata and domain documents

The `$details` suffix, not the media type, selects a Resource's xRegistry
metadata. When a Resource type has `hasdocument` true, the bare Resource URL
addresses its domain-specific document and `$details` addresses the metadata.
When `hasdocument` is false the suffix is optional, so the bare URL and the
`$details` URL are the same metadata route. An `application/json` body on a
document-bearing bare URL is therefore business content, not metadata: a
document whose members happen to be spelled `versionid` or `meta` is admitted
unchanged. Those requests and responses keep `application/octet-stream`, the
`xRegistry-*` metadata headers and the `xRegistry-epoch` document-view guard.
See Core's rules for
[metadata views](../core/http.md#resource-metadata-vs-resource-document).

Because metadata writes need a route, the generator emits Resource `PUT` and
`POST` operations on `$details` in addition to the existing read operation.
`PUT` replaces the Resource and uses the Resource write input. `POST` creates
or updates one Version and uses a Version write input; Core allows that body
to carry Resource-level read-only attributes such as `versionscount`, so they
are admitted and described as ignored, while Resource-only mutable members
such as `versions` and `meta` are not part of it. The `POST` response is the
Version definition, or the Resource definition for a single-Version type that
has none. Metadata epoch guards travel in the JSON body, so the document-view
`xRegistry-epoch` header is not added to these operations.

Metadata-only Resource types keep typed inputs on the bare URL as well, since
that URL is their metadata route. Meta routes, Version collections, nested
collection maps and every completed response stay typed; no route gains a
`PATCH` operation it did not already have, and existing metadata `PATCH`
operations keep their distinct partial-input role.

## Model-specific Meta types

For each Resource type, including imported types, the generator emits a
shared model-specific Meta response and separate `MetaWriteInput` and
`MetaPatchInput` request types. The standalone GET/PUT/PATCH route and nested
Resource metadata use the same response definition. Root write/patch graphs
use the corresponding Meta input definition.

The Core `deprecated` object remains closed in every role. Its defined members
are checked when supplied; an empty object remains valid. This does not open
unmodeled deprecation fields or change other model extension boundaries.

The ID member is the actual Resource singular name plus `id`, with a string
kind. The generic `RESOURCEid` placeholder is not exposed. Supplied request
IDs remain optional where the route/map supplies identity, and the server
checks that they match.

Core `xref` is a Registry-relative Resource XID, not an arbitrary absolute
URL. Meta `xref` has a URI-reference representation and a Resource-path syntax
constraint; Meta `xid` also remains Registry-relative. Meta self/default-Version
URLs admit their Core document-view relative references. Other reference
schemas are not globally widened.

The path syntax does not prove that Group/Resource types exist, that source
and target share the same Resource model type, or that a target is visible.
Those checks belong to the server. Structurally valid dangling references are
not fabricated into resolved resources.

## Alias and complete response forms

A normal or expanded Meta response requires its complete Core and model
fields. The separate identity-only alias branch also applies to the enclosing
Resource, including single-Version Resources with required defaulted target
fields. It contains only the applicable identity/navigation members and
`meta.xref`; incomplete expanded responses cannot evade their requirements.
See [cross references](../core/spec.md#cross-referencing-resources).

Alias write requests differ from read responses. An explicit non-null `xref`
request admits only the Resource ID, `xref`, and an applicable Meta epoch.
It does not require local custom creation attributes inherited from the target,
and it does not accept target attributes copied out of a GET response.
Normal Meta PUT retains client-required custom attributes; Meta PATCH retains
partial-update semantics.

Setting `xref` to null is a normal-operation reset/conversion request, not a
resolved alias. Default-Version creation, sticky/default selection, readonly
admin permissions and other state transitions remain server obligations.
Generated schemas do not decide these transitions from shape alone.

## Scalar value sets and Group constraints

A scalar attribute whose `enum` is nonempty and whose effective `strict` is
true now projects that value set into both dialects, at every entity, nested
object, map/array-of-object, typed scalar wildcard and active conditional
sibling leaf. An advisory (`strict: false`), empty or absent `enum` still
admits any otherwise-valid scalar, and the scalar type check is unchanged, so
a Boolean is not an integer and `"1"` is not an integer.

The value set is an independent restriction from `ifvalues` selection.
Selector activation stays case-insensitive; it never makes a non-member legal.
A source model whose selector key or non-null `default` falls outside an
effective strict value set is rejected at generation.

Request roles keep their reset behavior: where a writable field is nullable,
the emitted value set also admits `null`, so `nullable: true` never has to be
read as an override of membership. Read-only request values remain ignored
rather than checked, and completed responses still require an applicable
member.

A Group `constraints` entry that reaches a scalar attribute through
statically defined object attributes narrows that Group's own projection, and
the effective default is checked against the effective set. Map, array,
wildcard and `ifvalues`-defined targets are rejected. An imported Resource is
narrowed through the importing Group's reference only, so the shared Resource
definition is never altered and one Group's restrictions never reach another.
The dynamic `equals` comparison against actual Group instance values, and
xref graph enforcement, stay outside static schema generation.

Array-level `enum` keeps its existing item projection, and no `item.enum`
vocabulary is introduced.

## Scope

Apart from the Resource `$details` writes above, these corrections do not add
routes, and they do not change scalar encodings, native headers,
administrative APIs, concurrency flags or Problem Details. Domain document
media handling is clarified by route, not rewritten by content type.
Tests exercise actual generator route schemas, not only selected fragments.

For JSON Structure typed-wildcard handling, see
[Typed wildcards on named JSON Structure objects](json-structure-typed-wildcards.md).

## Core references

- [Entity update semantics](../core/http.md#creating-or-updating-entities)
- [Meta entity](../core/spec.md#meta-entity)
- [Cross references](../core/spec.md#cross-referencing-resources)
- [Required model attributes](../core/model.md#attributesstringrequired)
- [Model defaults](../core/model.md#attributesstringdefault)
- [Scalar value sets](../core/model.md#attributesstringenum)
- [Group constraints](../core/model.md#groupsstringconstraints)
