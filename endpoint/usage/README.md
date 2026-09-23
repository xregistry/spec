# Endpoint usage projection and migration

<!-- no verify-specs -->
<!-- words: avsc datumreader datumwriter py pytest usageenumtype -->

The [Endpoint specification](../spec.md#usage) defines the domain role
constraints, and explains why generated schema admission alone is not a
complete domain check. The source model and generated artifacts describe only
the structural portion of that contract.

## What the source model declares

`usage` is a REQUIRED array whose element definition now carries the role value
set:

```json
"usage": {
  "type": "array",
  "required": true,
  "item": { "type": "string", "enum": [ "subscriber", "consumer", "producer" ] }
}
```

The value set sits on `item`, not on the array. Core defines `enum` for
scalar types only, so an array or map restricts its elements
through `item.enum`; a value set on the owning array is not a Core declaration
and is rejected by both the source meta-schema and every emitter.

`item.strict` is absent, so it defaults to `true` and membership is enforced.
An absent or empty `item.enum`, or `"strict": false`, adds no membership
restriction, and declared values must still have the item's own scalar kind in
every case.
An otherwise valid Boolean `strict` without an enum has no effect, including
on a container definition.

## What changed for readers

Readers generated from the older artifacts saw `usage` as an unrestricted array
of strings. They now see an element value set in each dialect that can express
one:

| Artifact | Element projection |
| --- | --- |
| `document-schema.json` | `usage.items.enum` |
| `openapi.json` | `usage.items.enum` |
| `document-schema.struct.json` | `usage.items.enum` |
| `document-schema.avsc` | named `enum` `io.xregistry.UsageEnumType` |

The Avro change is the one that requires action. The array items move from
`"string"` to a named `enum` whose fully qualified name is
`io.xregistry.UsageEnumType`. Avro resolves readers and writers by that
qualified name, so regenerate Avro readers from the new `.avsc`; a reader built
from the previous string-item schema does not match the new writer schema. The
three symbols and their order are unchanged, and each declared role round-trips
through `DatumWriter` and `DatumReader`. One definition is emitted and shared,
so declaring the same set again reuses it rather than colliding.

Readers must still honor the now-required `usage` array. No role is inferred or
inserted for an existing declaration that omits `usage`; the author supplies the
intended role. The permitted role combinations have not changed.

## What the artifacts still do not express

The generated value set is a structural restriction on each element. It is not
the domain contract, and the following remain separate checks that every
generated artifact accepts:

- the array being nonempty;
- the members being unique;
- the rule that `producer` MUST NOT be combined with another role;
- the rule that `subscriber` and `consumer` MAY be combined, and only for
  AMQP/1.0, MQTT/3.1.1, MQTT/5.0 or NATS.

Avro can name only legal string symbols, so a value set that is numeric or that
contains a value which is not a legal Avro name keeps its restriction in the
other three dialects and is projected as the plain mapped type in Avro. No
encoding is invented to work around that.

## Core contract

The normative [item enum](../../core/model.md#attributesstringitemenum) and
[item strict](../../core/model.md#attributesstringitemstrict) rules are part
of Core following [xregistry/spec#732](https://github.com/xregistry/spec/pull/732). This
repository carries the source meta-schema aspect and the four emitter
projections; the Core prose is not duplicated here.

## Tests

The [focused regressions](../../tools/test_issue_626_endpoint_usage.py) exercise
the source model and all four generated representations for both the Endpoint
and CloudEvents consumers, including the Avro round trip of every declared role
and the documents that prove the domain rules are still separate. The
[projection contract](../../tools/test_issue_723_item_enum.py) covers the
meta-schema admission and rejection cases, the four-emitter rejection of an
illegal non-scalar item enum, ineffective strict flags, nested projections and Avro
naming, reuse and mapping limits.

```console
python -B -m pytest tools/test_issue_626_endpoint_usage.py tools/test_issue_723_item_enum.py -q
```
