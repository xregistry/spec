# JSON Structure dynamic object projection

<!-- no verify-specs -->
<!-- words: additionalproperties maxentries sdk jsonstructurevalidation -->
<!-- words: jsonschemavalidation jsonstructurealternatenames -->

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
Named objects remain structured objects: their existing properties, required
members, alternate names and wildcard projection are retained. This change
does not repair the separate admission behavior of typed wildcards on named
objects; it does not claim that existing behavior fully implements Core.

## Closed-empty objects

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

## Data and semantic boundaries

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

## Primary references and qualification

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

[core]: https://github.com/json-structure/core/tree/7371ab90b6cc5bed72df95bd35c715ee11304b82
[validation]: https://github.com/json-structure/validation/tree/257073e3c168f5d5486593a20848d6fbf1830889
[meta]: https://github.com/json-structure/meta/tree/6153fbd42be106cccbbe42184216b3906327f3c7
[sdk]: https://github.com/json-structure/sdk/tree/a4e751a6f18185dffdee10ae10ecdbf3be4e0e11
