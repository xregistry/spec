# Generated Working-Draft Schemas

<!-- words: avsc jsonschema metaattributes openapi powershell py pytest workingdrafts -->
<!-- words: rootlayer versionorigin wotid -->
<!-- words: makeschema OpenUSD plugin -->

Use the [schema generator](../../tools/schema-generator.py) to produce JSON
Schema, JSON Structure, Avro and OpenAPI descriptions of working-draft
metadata. Each model and its specification remain authoritative. The
generated files describe Registry metadata, not the contents of OpenUSD or
WoT documents, and do not validate those document contents.

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

The target generates schemas for both the established domains and these
working drafts. To generate one format for one model, run the corresponding
Python command directly. For example:

```powershell
python tools\schema-generator.py --type avro-schema --output workingdrafts\publication\schemas\document-schema.avsc workingdrafts\publication\model.json
```

The Makefile supplies the JSON Schema and JSON Structure identifiers and
root type names. Generated files use UTF-8, LF line endings, two-space
indentation and no final newline. Regenerate definitions rather than
editing them manually.

## Fidelity Checks and Limits

Run the working-draft schema checks from the repository root:

```console
python -m pytest workingdrafts/tools/test_generated_schemas.py -q
```

The checks regenerate each artifact and compare it with the checked-in
file. They validate schema syntax and references, then check declared
fields, types, nested objects and Version/Meta placement against the input
model.
JSON Schema and OpenAPI checks include strict enumerations and defaults.
JSON Structure checks include those annotations and REQUIRED fields.
Avro checks resolve the records and collection item types through its parser.

The OpenUSD checks include the `rootlayer` field and the imported asset
collection in schema-plugin Groups. The WoT checks include `wotid`,
`versionorigin` and Meta compatibility. Publication checks include channel
Meta `scope` and `head`, the nested URL/digest/size fields, and rejection of
missing head fields, negative sizes and incorrectly typed sizes in JSON
Schema and OpenAPI.

These checks establish fidelity to the model, not complete Core or
deployed-service conformance. The generator does not encode every Core
attribute, conditional write, immutability rule or Version-selection
algorithm. Avro does not generally encode model enumerations,
OPTIONAL-field absence or model defaults. URI strings require separate
semantic validation, and the JSON Structure checks use structural
comparisons rather than a complete dialect validator.

The [Publication envelope schema](../publication/schemas/publication.json)
and [WoT closure schema](../models/wot/schemas/publication-closure.schema.json)
describe different documents. They are independent of these generated
Registry metadata descriptions.
