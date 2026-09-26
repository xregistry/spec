# Schema generator and model validation tooling

<!-- no verify-specs -->
<!-- words: additionalproperties altnames avsc codecs enums expandedmodel -->
<!-- words: ifvalues itemdefinition jsonschemavalidation maxentries openapi -->
<!-- words: jsonstructurealternatenames jsonstructurevalidation metapatchinput -->
<!-- words: metawriteinput modelsource namecharset patchinput py pytest -->
<!-- words: readonly registryentity registrypatchinput registrywriteinput rfc -->
<!-- words: sdk siblingattributes standalone typemap usageenumtype validators -->
<!-- words: ximportresources writeinput xref -->

Notes on what [`schema-generator.py`](schema-generator.py) and
[`validate-models.py`](validate-models.py) actually do, and on the boundaries of
what their tests prove. These are tooling notes, not specification text.

## Contents

- [Running the tests](#running-the-tests)
- [Model source schema: what each validation stage proves](#model-source-schema-what-each-validation-stage-proves)
- [Local model includes](#local-model-includes)
- [Conditional selector matching](#conditional-selector-matching)
- [Scalar item value sets](#scalar-item-value-sets)
- [JSON Structure dynamic object projection](#json-structure-dynamic-object-projection)
- [Typed wildcards on named JSON Structure objects](#typed-wildcards-on-named-json-structure-objects)
- [OpenAPI request roles and Resource Meta schemas](#openapi-request-roles-and-resource-meta-schemas)

## Running the tests

Every topic below is covered by one module,
[`test_schema_generator_projections.py`](test_schema_generator_projections.py).
Run it from the repository root:

```sh
python -B -m pytest tools/test_schema_generator_projections.py -q
```

The tests drive the production generator, resolver and validators. They do not
assert specification prose and they do not re-implement the behavior they check.

## Model source schema: what each validation stage proves

`core/model.schema.json` describes the **`modelsource`** document - the model
exactly as an author writes it - and `tools/validate-models.py` reports which
stage produced each result. Neither stage is a conformance statement about a
completed xRegistry model.

### Source structure

The root schema validates the document as written:

- `$include` and `$includes` are accepted in any model Object or Map, including
  the Registry root, the `groups` and `resources` maps, Group and Resource
  definitions, every attribute map and attribute definition, nested `item`
  definitions, `ifvalues` maps, their branches and `siblingattributes`,
  `labels`, `typemap`, and the Group `constraints` map and its entries. The two
  directives are typed and mutually exclusive at any one level, and an
  include-only Group or Resource definition needs no local `singular`.
- A definition MAY omit `type`, because the type can arrive from an include or
  from the specification-defined attribute it overlays. For example,
  `{"attributes": {"name": {"required": true}}}` is a legal source overlay.
- Attribute names use the strict character set, lowercase letters, digits and
  underscore, not starting with a digit, unless the owning `object` or `item`
  declares `namecharset: extended`, which selects the map key character set
  described in `core/spec.md`. The owning object's
  character set also applies to the top-level `siblingattributes` of its
  attributes' `ifvalues`; it does not change a nested object's own character
  set.
- Group plural, Resource singular and Resource plural names - as map keys and as
  explicit fields - are limited to 57 characters. Group singular follows the
  current `core/model.md` text of 63 characters.
- `namecharset`, `versionmode` and `typemap` values are matched
  case-insensitively. Type names, attribute names and `enum` members are not.

### Expanded structure

`#/definitions/ExpandedModel` validates the same document after
`tools/schema-generator.py::resolve_imports` - the real resolver, with its
existing local-file-only, cycle, depth, precedence and non-mutation behavior -
has resolved the directives. At that stage no directive MAY remain and every
attribute, wildcard and item definition MUST carry a `type`.

Admission at the source stage therefore does not imply that a definition is
complete, and admission at the expanded stage does not imply that the model is
semantically valid.

### Not checked here

`tools/validate-models.py` explicitly reports that it does not perform semantic
conformance: overlaying the specification-defined attributes, rejecting an
incompatible Core `type`/`required`/`readonly` change or an unknown untyped
extension, key/`name` identity, `target` and `ximportresources` type existence
and depth, case-duplicate `ifvalues` selector keys, and cross-entity graph rules
all require a real xRegistry implementation. The grammar for `target` checks the
shape of the type-name components only.

### Recorded dependencies

- **Group singular of 61 characters** is proposed in xregistry/spec#677 and is
  not adopted here; the schema keeps the 63 characters that `core/model.md`
  currently states.
- **`cloudevents/model.json`** still uses three `#groups` include fragments that
  are not RFC 6901 JSON Pointers, so its expanded stage cannot pass. Repairing
  those fragments is tracked separately as a model-consistency correction.
- **Scalar-only `enum` applicability** is enforced wherever the declared type
  is known. Endpoint now uses `usage.item.enum` following
  [xregistry/spec#732](https://github.com/xregistry/spec/pull/732), so there is
  no array-level compatibility exception. Includes can still supply an omitted
  source type; the expanded stage resolves it before applying the same rule.

## Local model includes

The [schema generator](schema-generator.py) expands `$include` and `$includes`
using local JSON files. Local sibling keys win over included keys; earlier
includes win over later ones. Values are replaced as a whole, not merged
recursively. Nested paths and fragment-only pointers use the document that
declared them. The source dictionaries, lists, and files remain unchanged.

References use JSON Pointer fragments, including pointer escapes and percent
encoding. The tool rejects conflicting directives, invalid references, missing
files, non-object targets, cycles, and chains longer than 64 includes. It does
not acquire include documents through URLs or network paths.

These checks exercise the production include resolver and schema generation,
not a replacement resolver. They do not qualify Core metadata, cross-group
resource imports, scalar codecs, or generated client behavior. The separate
CloudEvents source fragment correction is not part of this change.

## Conditional selector matching

The [schema generator](schema-generator.py) projects `ifvalues` into connected
JSON Schema and OpenAPI validation branches. Known string selectors match
exactly, ignoring single-character case differences, without changing the
supplied spelling. Literal punctuation remains literal. The expressions use
portable case alternatives, not regular expression flags, prefix matching, or
Unicode normalization. Native Boolean and integer selectors retain their JSON
kinds, including integers larger than machine precision.

The unknown-selector branch is the complement of all known guards. It cannot
hide invalid known-branch data, and the original selector type and presence
rules still apply. Empty and nested branches work without losing independent
selector conditions. Unknown selectors do not activate conditional members;
extra members still need model admission, such as an explicit wildcard.

OpenAPI uses the same schema guards rather than a discriminator: a discriminator
mapping is case-sensitive and cannot describe arbitrary case variants and
unknown extension selectors. The previous disconnected named conditional
components are replaced by conditions at the actual containing schema.

The tests use actual JSON Schema and OpenAPI schema validators, not a translated
schema or a replacement selector matcher. This change does not implement source
aliases, strict scalar enums, missing scalar kinds, lossless alternate
encodings, object closure, or client SDK codecs.

Published Message, Endpoint, and CloudEvents validators are also checked against
valid and invalid HTTP query values and MQTT expiry intervals with different
selector case, plus unknown extension selectors. Completed response cases
include required defaulted members; model admission remains independent of
selector matching.

## Scalar item value sets

The [schema generator](schema-generator.py) projects a scalar `item.enum` onto
the array element or map value it belongs to. The reviewed Endpoint directive
moves a role value set off the owning array and onto the element definition, so
the [source meta-schema](../core/model.schema.json) admits `enum` and `strict`
on an `ItemDefinition`. Core defines `enum` for scalar items only; a container
restricts its scalar elements through its own `item`. A Boolean `strict` without
an enum has no effect, even on a container. Core does not permit `enum` on the
owning `array` or `map` attribute itself.

Membership reuses the attribute rules. Values must have the item's own scalar
kind, matching is case-sensitive, `strict` defaults to true, `strict` false
makes membership advisory, and an absent or empty set adds no membership
restriction. Advisory does not relax the declared kind: a value of the wrong
kind is rejected whether or not `strict` enforces membership, and `strict`
alone has no effect. Selector activation stays a separate case-insensitive
rule. An item value set does not make the owning array required, non-empty, or
unique, and it does not decide which role combinations a protocol permits.

JSON Schema, OpenAPI, and JSON Structure carry the restriction directly at the
element or value, including a nested array of maps or map of arrays. Object
items keep their own named scalar attribute sets.

Avro restricts a value only through a named `enum` of string symbols. A set of
legal symbol names becomes one shared named definition, `UsageEnumType` for a
`usage` attribute. A repeated value names the same symbol, so it is folded in
first-occurrence order rather than losing the restriction. An identical set
reuses the first definition by its qualified name, and a different set under
the same base name takes the next name in the same convention, `UsageEnumType2`,
so both keep enforcing membership.

Two Core value sets remain genuinely unrepresentable as Avro symbols: a
non-string scalar kind, and a value that is not a legal Avro name, such as
`with-dash`, `9lives`, `with space`, or the empty string. Those are projected
as the plain mapped type, the restriction remains expressed in the dialects
that can carry it, and no codec is invented to fake it. The generated `.avsc`
states the mapping that exists, not a wire guarantee.

The tests use the actual source meta-schema, JSON Schema and OpenAPI validators,
and the actual Avro parser, reader, and writer. The emitted JSON Structure
contract is asserted directly rather than through an SDK claim.

This change adds no item defaults, model policy, general declaration validator,
or client SDK codec. Core's
[item aspects](../core/model.md#attributesstringitemenum) and Endpoint's
item-level declaration are now on main following
[xregistry/spec#732](https://github.com/xregistry/spec/pull/732). The obsolete
owning-array projection is removed; source validation and all emitters reject
that placement rather than silently moving its value set onto the items.

## JSON Structure dynamic object projection

The generator projects a Core object with only a wildcard definition as a
JSON Structure `map`, not an `object` with empty `properties`. The dialect
requires at least one named property for a structured object.

For a wildcard of type `any`, the physical schema is:

```json
{
  "type": "map",
  "values": { "type": "any" }
}
```

Typed wildcards use their projected value schema instead. Nested object
values use the generator's existing reusable definition/reference mechanism.
Named objects retain their properties, required members and alternate names;
their typed wildcard behavior is described in
[Typed wildcards on named JSON Structure objects](#typed-wildcards-on-named-json-structure-objects).

### Closed-empty objects

A closed object with no named properties is not an open dynamic map. Its
precise representation is an empty map:

```json
{
  "type": "map",
  "values": { "type": "any" },
  "maxEntries": 0
}
```

This accepts the JSON object `{}` and rejects every nonempty object and every
non-object value. The generator adds `JSONStructureValidation` to the root
`$uses` list only when a zero-entry constraint is emitted. Consumers must
support that feature to enforce the closed-empty contract; a Core-only
validator that ignores the constraint does not qualify.

An optional property can still be absent. A required property must be present,
even when its only allowed value is `{}`. Null is not an empty object. A named
object whose properties are all optional can also accept `{}`, but retains
its named object schema rather than becoming a map.

### Data and semantic boundaries

These are derived type/API changes, not changes to serialized Core object
data. Empty/nonempty maps remain JSON objects, nested dynamic values retain
their JSON kinds, and generation does not mutate the supplied model.

JSON Structure map keys can be any JSON string. That is not permission to use
Core-invalid parameter names. Core model/runtime admission, including the
object's `namecharset`, remains responsible for name validation. The source
model is unchanged; a dialect instance check is not a substitute for that
semantic validation.

This correction does not add scalar encodings, conditional case folding,
general enum/closure changes, or other model-admission rules.

### Primary references and qualification

The implementation and bounded tests use these immutable primary revisions:

- JSON Structure Core:
  `7371ab90b6cc5bed72df95bd35c715ee11304b82`
- JSON Structure validation specification:
  `257073e3c168f5d5486593a20848d6fbf1830889`
- Published meta-schemas:
  `6153fbd42be106cccbbe42184216b3906327f3c7`
- Official SDK source, inspected but not installed or executed:
  `a4e751a6f18185dffdee10ae10ecdbf3be4e0e11`

Core's object, map, `any`, dynamic-structure and `values` clauses establish
the schema shape. The validation specification's `maxEntries` clause
explicitly permits a nonnegative limit, including zero.

The generated feature identifier is the actual `JSONStructureValidation`
offered by the pinned extended meta-schema and used by the SDK. The pinned
validation prose's enabling example spells it `JSONSchemaValidation`; that
spelling does not identify the feature offered by the referenced dialect.

The meta-schema documents are themselves JSON Structure documents, not
JSON Schema validator inputs. The local environment has no JSON Structure
SDK. Tests therefore check the relevant pinned structural rules and translate
only the exercised map/object/array/reference/required/entry-limit subset into
JSON Schema for instance assertions. This is bounded contract evidence, not
full SDK or full Core semantic qualification. No claim is made that the
published meta-schemas were successfully executed as a full validator.

References:

- [Core language source][core]
- [Validation specification source][validation]
- [Published extended dialect][meta]
- [Official SDK source][sdk]
- [Core attribute names](../core/model.md#attributesstringname)

## Typed wildcards on named JSON Structure objects

A modeled object with named properties and a typed `*` retains both contracts.
The generator emits the wildcard's value schema in `additionalProperties`;
the named properties keep their own types, alternate names and required flags.
Object wildcard values use the existing named-definition/reference mechanism,
including their nested field constraints.

For example, an object with required string `name` and integer `*` accepts
`{"name":"http","count":7}` but rejects a string `count`, a non-string `name`,
or a missing `name`. No wildcard still means a closed object. An `any`
wildcard retains its existing open boundary.

This follows the [primary additional-properties contract][additional].
It changes generated type descriptions for previously rejected, model-admitted
values. Consumers should regenerate their types and enforce the wildcard value
schema, not treat its presence as permission for arbitrary values.

The tests exercise a bounded translation of these Core dialect constructs,
not a complete JSON Structure SDK. Core name admission, conditional activation
and numeric representation policies remain separate. This change does not
redefine wholly dynamic or closed-empty objects.

## OpenAPI request roles and Resource Meta schemas

The generator separates client request structures from completed response
structures. This changes generated request/Meta type APIs, not the Core
protocol. Clients should regenerate their OpenAPI types rather than populate
server fields to satisfy a response schema.

### Registry requests and responses

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

### Effective model and retained state

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

### Resource routes, metadata and domain documents

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

### Model-specific Meta types

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

### Alias and complete response forms

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

### Scalar value sets and Group constraints

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

A container restricts its elements through
[`item.enum`](#scalar-item-value-sets); an `enum` on the owning array or map
itself is rejected rather than projected onto the items.

### Scope

Apart from the Resource `$details` writes above, these corrections do not add
routes, and they do not change scalar encodings, native headers,
administrative APIs, concurrency flags or Problem Details. Domain document
media handling is clarified by route, not rewritten by content type.
Tests exercise actual generator route schemas, not only selected fragments.

### Core references

- [Entity update semantics](../core/http.md#creating-or-updating-entities)
- [Meta entity](../core/spec.md#meta-entity)
- [Cross references](../core/spec.md#cross-referencing-resources)
- [Required model attributes](../core/model.md#attributesstringrequired)
- [Model defaults](../core/model.md#attributesstringdefault)
- [Scalar value sets](../core/model.md#attributesstringenum)
- [Group constraints](../core/model.md#groupsstringconstraints)

[additional]: https://github.com/json-structure/core/blob/7371ab90b6cc5bed72df95bd35c715ee11304b82/draft-vasters-json-structure-core.md#L1338-L1355
[core]: https://github.com/json-structure/core/tree/7371ab90b6cc5bed72df95bd35c715ee11304b82
[validation]: https://github.com/json-structure/validation/tree/257073e3c168f5d5486593a20848d6fbf1830889
[meta]: https://github.com/json-structure/meta/tree/6153fbd42be106cccbbe42184216b3906327f3c7
[sdk]: https://github.com/json-structure/sdk/tree/a4e751a6f18185dffdee10ae10ecdbf3be4e0e11
