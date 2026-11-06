# Lossless scalar projection profile, version 1

<!-- no verify-specs -->
<!-- words: enums genericrecord iers millis pathlib powershell -->
<!-- words: py resourcelimiterror sdk xregistryabsent xregistryjsoncarrier -->
<!-- words: xregistryprojection xregistryscalar xregistryscalartree -->
<!-- words: projectioncodec -->
<!-- words: additionalproperties jsonstructurevalidation maxentries -->
<!-- words: migrationerror -->

This profile is identified by
`https://xregistry.io/profiles/scalar-projection/1`. It describes derived
encodings and their semantic adapters, not new Core types or an HTTP wire
format. Core JSON numbers remain numbers. Core calls its general numeric
type `decimal`; using that name does not require binary floating point.

The reference implementation is [scalar_projection.py](scalar_projection.py).
Generated Avro and JSON Structure documents contain the complete profile
descriptor in `x-xregistryProjection`. Individual converted scalars carry an
`x-xregistryScalar` contract with the source Core kind, encoding and typed
constraints. Unknown profile versions or inconsistent bindings are rejected.

## Physical representations

Avro `integer`, `uinteger` and `decimal` projections use standard `string`
values containing exact JSON number tokens. A timestamp uses a standard Avro
`string` containing complete RFC3339 text. There is no custom Avro logical
type, fixed precision, fixed numeric maximum, or timestamp-millis conversion.

JSON Structure uses standard `string` for numeric tokens and standard
`datetime` for timestamps. Its custom annotations describe the same adapter
contract. The annotations do not redefine those standard physical types.

A generic Avro value uses the existing `GenericRecord` physical shape:

```json
{"object":{"json":"1e1000"}}
```

The single `json` string contains exact Core JSON. Thus a Core string
`"1e1000"` has different carrier text from the Core number `1e1000`. Objects,
maps, arrays and recursive generic values retain their JSON kinds and number
tokens. The carrier is marked `x-xregistryJsonCarrier: "core-json/1"`.
Scalar-bearing structured values that the legacy Avro emitter represents
opaquely also retain their typed scalar rules in `x-xregistryScalarTree`.
Those rules are checked before writing and after reading the carrier.

This carrier does not claim that arbitrary bare legacy GenericRecord data
already conforms to the new profile. Its semantic representation has changed
even where the Avro parsing-canonical schema has not.

## Numeric and timestamp semantics

The numeric token grammar is JSON's number grammar: an optional minus sign,
an integer part without leading zeros (except zero itself), an optional
decimal point followed by one or more digits, and an optional `e` or `E`
exponent with an optional sign and one or more digits. Digits are ASCII.

The adapter retains the token and compares normalized coefficient/exponent
values without expanding exponent notation. `1e1000` stays a six-character
token. Integral decimal/exponent spellings and negative zero are retained.
An `integer` value must be mathematically integral; a `uinteger` must also be
nonnegative. Nonfinite values, booleans, numeric Core strings, invalid tokens
and binary floating-point inputs are rejected rather than rounded.

`parse_core_json` preserves numeric tokens, including in nested JSON and
source model files. `dump_core_json` restores their unquoted JSON numeric
kinds. Applications can also supply exact Python integers or finite
`Decimal` values. A value already converted to a Python `float` is not
accepted as evidence of its original JSON value.

Numeric enums compare mathematical values: `1`, `1.0`, and `1e0` are equal.
Bounds use exact numeric ordering, not lexical string ordering. A fractional
bound can constrain an integer domain. Enum members still have to satisfy
their declared source kind. Non-strict enum lists remain suggestions.

Timestamps retain every fractional digit and the supplied offset/text.
`normalize_timestamp` converts explicitly to UTC without passing fractional
seconds through a host `datetime`; `compare_timestamps` compares exact
instants, including offset-equivalent spellings and unequal 30-digit
fractions. Calendar dates, offsets, clock ranges and leap-second placement
are checked. The implementation is not an IERS leap-second authority and
does not calculate elapsed leap-second durations.

Core's server-side UTC normalization and other Core/Model validation still
apply at the Core boundary. The storage adapter neither weakens those rules
nor claims to implement a complete registry/server validator.

## Absence, null and defaults

For an optional projected Avro scalar, the physical union distinguishes:

- An empty, named `AbsentV1` record: the attribute was absent.
- Avro `null`: an explicit optional null/reset state.
- A string: the actual numeric token or timestamp.

The empty record is identified by `x-xregistryAbsent` and has a unique name
derived from the owning record and field. An explicit Core object is not
accepted as a numeric value or confused with this encoding on write.
JSON Structure naturally preserves missing properties; optional projected
scalars have an explicit standard null alternative.

Required scalar absence/null is rejected. A declared numeric default becomes
a target string default, for example `1e1000` becomes `"1e1000"`. A timestamp
default remains complete timestamp text. Defaults are validated against the
source kind and semantic constraints.

Avro defaults are reader-schema evolution defaults, not permission to omit a
required field during encoding. The writer does not silently apply defaults.
An optional scalar with no model default uses the absence record as its
Avro read default. Nested defaults do not require an absent owner object to
be created. Operation-specific null/reset processing remains a server concern.

## Reader and writer interfaces

Use the generator's existing CLI to produce the writer schema. For example:

```powershell
$model = "schema\model.json"
$out = "schema\schemas\document-schema.avsc"
python -B tools\schema-generator.py --type avro-schema --output $out $model
```

The following Python code assumes `tools` is on the import path and that
`core_json` contains data for the generated structural contract:

```python
from pathlib import Path
from scalar_projection import (
    ProjectionCodec, dump_core_json, parse_core_json,
)

schema = parse_core_json(
    Path(r"schema\schemas\document-schema.avsc").read_bytes()
)
codec = ProjectionCodec(schema, "avro")
encoded = codec.write(parse_core_json(core_json))
restored_json = dump_core_json(codec.read(encoded))
artifact_json = dump_core_json(codec.artifact)
```

`ProjectionCodec(schema, "json-structure")` exposes the same interface.
`to_derived` and `from_derived` provide checked in-memory adaptation, but those
bare data values do not carry writer identity and are not durable envelopes.

`write` produces one Avro object-container datum using the standard null
compression codec, or a JSON Structure contract/data envelope. Both retain
the complete writer schema and immutable semantic profile. `read` requires
the codec's pinned contract, validates identity and physical/semantic values,
and restores exact Core scalar kinds.

For JSON Structure maps, `maxEntries` requires the root `$uses` list to enable
`JSONStructureValidation` and a nonnegative integer bound. Codec construction
rejects invalid or unenabled limits. Valid limits are enforced on writes and
reads, including referenced map definitions. A zero limit admits an empty
object, not extra entries; an absent optional property remains absent. The
limit and feature declaration remain part of the complete writer identity.

For named JSON Structure objects, schema-valued `additionalProperties` uses
the same bounded value adapter as named fields and map values, on writes and
reads. Numeric extras retain their Core numeric kind even when projected as
strings; named string fields are not retyped. Referenced objects, arrays and
maps traverse that adapter as well. Boolean open/closed boundaries remain
unchanged. The complete additional value schema participates in writer identity,
independently of map entry limits. This is not full JSON Structure SDK or
validation-feature qualification.

`ProjectionCodec.from_artifact` verifies a retained artifact. Applications
still have to obtain and pin that artifact through a trusted channel. Its
SHA-256 identity covers the complete schema and profile, including semantic
annotations, defaults and constraints. An Avro parsing-canonical fingerprint
alone is insufficient because it strips relevant annotations. These hashes
are identity checks, not authentication.

## Schema and reader migration

This is an intentional generated-type and binary compatibility change.
Existing int/long, time-of-day and timestamp primitive readers do not become
compatible with string data automatically. JSON Structure consumers must
likewise update their generated types and use the semantic adapter.

Keep the actual complete writer schema with every stored representation.
Changing a model, schema description, constraint or profile produces a new
full contract identity. An old schema must not be silently relabeled as
version 1.

For Avro:

```python
migrated = codec.migrate_avro(old_bytes, retained_writer_schema)
```

This uses an actual transitional Avro reader schema that can resolve the
relevant old int/long and new string alternatives. It validates original
writer data before applying reader defaults. New scalar fields can receive
their correctly typed reader defaults. Transition schemas are read-only
migration artifacts, not valid version-1 writers.

Plain legacy int/long values migrate exactly as the retained mathematical
values. Their original lexical spelling, negative-zero spelling or
pre-existing absence/null ambiguity cannot be recovered. Qualified string
writers retain their exact tokens and presence states.

Old floating-point values, old time-of-day/timestamp primitives, unqualified
numeric strings and legacy generic representations can lack indispensable
source information. The reference migrator rejects unsafe inference. Supply
authoritative Core JSON explicitly when re-encoding those values:

```python
migrated = codec.migrate_avro(
    old_bytes, retained_writer_schema,
    authoritative_core_json=authoritative_json,
)
```

That path validates and writes the supplied authoritative data. It does not
reconstruct lost fractions, dates, coefficients or spellings from old bytes.
Record identity/layout changes and ambiguous legacy unions require explicit
application migration or authoritative re-encoding as well.

For JSON Structure:

```python
migrated = codec.migrate_json_structure(
    old_json_bytes, retained_writer_schema,
)
```

Pre-profile JSON does not itself identify its writer. The caller must supply
the verified archived schema; the adapter cannot infer it from the payload.
Legacy fixed-width integer ranges/literal grammar are checked as properties
of that old representation, not as new Core limits. Exact stored datetime
text is retained. Unsafe old floating/decimal projections require the same
explicit `authoritative_core_json` path.

Changing a legacy object representation to a map also requires that explicit
path, even for an empty object. Otherwise migration raises `MigrationError`;
identical empty JSON does not establish a compatible writer contract.

Migrated envelopes retain the complete old writer schema, its full
fingerprint, and whether the strategy was retained-value migration or
authoritative re-encoding. The original archived data should also be retained
according to the application's migration/retention policy.

## Limits and qualification

`Limits` controls byte, scalar-text and nesting budgets. The reference
defaults are 16 MiB, 1,000,000 scalar characters and depth 128. Budget failures
raise `ResourceLimitError`; they are not schema value limits. No maximum
numeric magnitude or fixed fractional precision is declared by the profile.
The reference Avro reader/migrator requires uncompressed containers so that
its input byte budget does not hide unbounded decompression.

The adapter follows the existing generator's structural contract. It does
not repair unrelated missing Core metadata, Version/navigation/API routes,
general enum/conditional projection, object-closure or dynamic-map defects.
It rejects unrepresentable data, ambiguous unions, and unsupported structural
migrations rather than dropping fields or claiming full Core conformance.

Tests exercise actual Avro serialization/resolution, generated schemas,
source-file parsing, exact JSON restoration, defaults, constraints, identity
and migration. JSON Structure scalar types and schema structure are checked
against its published contracts and the repository's structural checks.
No complete JSON Structure SDK or benchmark qualification is claimed.

## References

- [Core value types](../core/spec.md#data-types)
- [Core defaults and constraints](../core/model.md#attributesstringdefault)
- [Avro specification](https://avro.apache.org/docs/1.12.0/specification/)
- [JSON Structure Core](https://json-structure.github.io/core/)
- [RFC3339](https://www.rfc-editor.org/rfc/rfc3339)
