# Generated Working-Draft Schemas

<!-- words: avsc jsonschema metaattributes openapi powershell py pytest workingdrafts -->
<!-- words: rootlayer versionorigin wotid -->
<!-- words: makeschema OpenUSD plugin -->

The [schema generator](../../tools/schema-generator.py) produces JSON Schema,
JSON Structure, Avro and OpenAPI descriptions from each working-draft model.
The model and its specification remain authoritative. Generated files describe
metadata; they do not validate the contents of an OpenUSD or WoT document.

| Model | Input | Generated files |
| --- | --- | --- |
| OpenUSD | [model.json](../models/openusd/model.json) | [JSON Schema](../models/openusd/schemas/document-schema.json), [JSON Structure](../models/openusd/schemas/document-schema.struct.json), [Avro](../models/openusd/schemas/document-schema.avsc), [OpenAPI](../models/openusd/schemas/openapi.json) |
| WoT | [model.json](../models/wot/model.json) | [JSON Schema](../models/wot/schemas/document-schema.json), [JSON Structure](../models/wot/schemas/document-schema.struct.json), [Avro](../models/wot/schemas/document-schema.avsc), [OpenAPI](../models/wot/schemas/openapi.json) |
| Publication | [model.json](../publication/model.json) | [JSON Schema](../publication/schemas/document-schema.json), [JSON Structure](../publication/schemas/document-schema.struct.json), [Avro](../publication/schemas/document-schema.avsc), [OpenAPI](../publication/schemas/openapi.json) |
| Registry of Registries | [model.json](../models/registry/model.json) | [Formats and limitations](../models/registry/schemas/README.md) |

## Generation

Run the repository's schema target from its root:

```console
make -f tools/Makefile makeschema
```

The target includes the established domains and these working drafts. Each
command also runs independently with Python. For example:

```powershell
python tools\schema-generator.py --type avro-schema --output workingdrafts\publication\schemas\document-schema.avsc workingdrafts\publication\model.json
```

The Makefile specifies the identifiers and root type names for JSON Schema
and JSON Structure. Outputs use UTF-8, LF line endings, two-space indentation
and no final newline. Do not edit generated definitions manually.

## Fidelity Checks and Limits

Run the working-draft schema checks from the repository root:

```console
python -m pytest workingdrafts/tools/test_generated_schemas.py -q
```

The checks compare fresh generator output with each checked-in artifact.
They validate schema syntax and references, then compare declared fields,
types, nested objects and Version/Meta placement with the input model.
JSON Schema and OpenAPI checks include strict enumerations and defaults.
JSON Structure checks include those annotations and REQUIRED fields.
Avro checks resolve the records and collection item types through its parser.

The OpenUSD checks include the `rootlayer` field and the imported asset
collection in schema-plugin Groups. The WoT checks include `wotid`,
`versionorigin` and Meta compatibility. Publication checks include channel
Meta `scope` and `head`, the nested URL/digest/size fields, and rejection of
missing head fields, negative sizes and incorrectly typed sizes in JSON
Schema and OpenAPI.

These are model-fidelity checks, not complete Core or deployed-service
conformance tests. The generator does not encode every Core attribute,
conditional write, immutability rule or Version-selection algorithm. Avro
does not generally encode model enumerations, OPTIONAL-field absence or
model defaults. URI strings need separate semantic validation. JSON Structure
uses structural checks rather than a complete dialect validator.

The [Publication envelope schema](../publication/schemas/publication.json)
and [WoT closure schema](../models/wot/schemas/publication-closure.schema.json)
describe different documents. They are independent of these generated
Registry metadata descriptions.
