# Scalar item value sets

<!-- no verify-specs -->
<!-- words: avsc enums itemdefinition openapi py pytest sdk usageenumtype validators -->

The [schema generator](schema-generator.py) projects a scalar `item.enum` onto
the array element or map value it belongs to. The reviewed Endpoint directive
moves a role value set off the owning array and onto the element definition, so
the [source meta-schema](../core/model.schema.json) admits `enum` and `strict`
on an `ItemDefinition` and rejects an `enum` on a container item: an array, map,
object, or `any` item recurses through its own `item` instead.

Membership reuses the attribute rules. Values must have the item's own scalar
kind, matching is case-sensitive, `strict` defaults to true, `strict` false is
advisory, and an absent or empty set adds no membership restriction. Selector
activation stays a separate case-insensitive rule. An item value set does not
make the owning array required, non-empty, or unique, and it does not decide
which role combinations a protocol permits.

JSON Schema, OpenAPI, and JSON Structure carry the restriction directly at the
element or value, including a nested array of maps or map of arrays. Object
items keep their own named scalar attribute sets.

Avro restricts a value only through a named `enum` of string symbols. A legal
symbol set becomes one shared named definition, `UsageEnumType` for a `usage`
attribute, which a repeated declaration references by its qualified name rather
than redefining. A value set Avro cannot name is projected as the plain mapped
type: a non-string scalar kind, a symbol that is not an Avro name, a repeated
value, or a second different set under one name. The restriction then remains
expressed in the dialects that can carry it, and no codec is invented to fake
it. The generated `.avsc` states the mapping that exists, not a wire guarantee.

Run the [focused regressions](test_schema_generator_item_enums.py):

```sh
python -B -m pytest tools/test_schema_generator_item_enums.py -q
```

The tests use the actual source meta-schema, JSON Schema and OpenAPI validators,
and the actual Avro parser, reader, and writer. The emitted JSON Structure
contract is asserted directly rather than through an SDK claim.

This change adds no item defaults, model policy, general declaration validator,
or client SDK codec. The separate array-level `enum` keeps its existing
projection until the source cleanup that removes it, and the earlier strict
scalar attribute work is unchanged.
