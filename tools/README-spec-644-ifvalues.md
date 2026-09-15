# Conditional selector matching

<!-- no verify-specs -->
<!-- words: codecs enums ifvalues openapi py pytest sdk validators -->

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
selector conditions.

OpenAPI uses the same schema guards rather than a discriminator: a discriminator
mapping is case-sensitive and cannot describe arbitrary case variants and
unknown extension selectors. The previous disconnected named conditional
components are replaced by conditions at the actual containing schema.

Run the [focused regressions](test_schema_generator_ifvalues_644.py):

```sh
python -B -m pytest tools/test_schema_generator_ifvalues_644.py -q
```

The tests use actual JSON Schema and OpenAPI schema validators, not a translated
schema or a replacement selector matcher. This change does not implement source
aliases, strict scalar enums, missing scalar kinds, lossless alternate encodings,
object closure, or client SDK codecs.

Published Message, Endpoint, and CloudEvents validators are also checked against
valid and invalid HTTP query values and MQTT expiry intervals with different
selector case, plus unknown extension selectors.
