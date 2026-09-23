# Scalar item value sets

<!-- no verify-specs -->
<!-- words: avsc enums itemdefinition openapi py pytest sdk usageenumtype validators -->

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

Run the [focused regressions](test_schema_generator_item_enums.py):

```sh
python -B -m pytest tools/test_schema_generator_item_enums.py -q
```

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
