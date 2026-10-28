# Generated Working-Draft Schemas

<!-- words: avsc jsonschema metaattributes openapi powershell py pytest workingdrafts -->
<!-- words: rootlayer versionorigin wotid -->
<!-- words: makeschema OpenUSD plugin -->
<!-- words: federationprofiles -->

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
root type names. Generated files use two-space indentation and no final
newline. Output line endings follow the host platform; repository schema
files use LF. Regenerate definitions rather than editing them manually.

## Fidelity Checks and Limits

Run the working-draft schema checks from the repository root:

```console
python -m pytest workingdrafts/tools/test_generated_schemas.py -q
```

The checks regenerate each artifact and compare its parsed content with the
checked-in file. They validate JSON Schema and OpenAPI syntax, check JSON
Structure names and references, and parse Avro records and collection item
types. They also check that the established Schema, Message, Endpoint and
CloudEvents outputs remain unchanged.

The Avro regression checks use the Registry model's `federationprofiles`
and `relationships` arrays. Their object items retain their declared
fields rather than becoming empty or incomplete types. Additional cases
cover typed and generic object items in arrays, maps and nested collections.
This fix does not change generation for the established models.

Reproduction and parsing do not establish complete fidelity to a model or
Core conformance. The existing generator does not preserve every Meta
extension, typed object, default or enumeration in every format. In
particular, the generated publication descriptions do not validate channel
Meta `scope` and `head`, and generated WoT descriptions do not validate Meta
compatibility. Avro does not generally encode OPTIONAL-field absence or
model defaults. Conditional writes, immutability and Version selection need
separate checks against the specifications. URI strings require semantic
validation, and the JSON Structure checks are not a complete dialect
validator.

The [Publication envelope schema](../publication/schemas/publication.json)
and [WoT closure schema](../models/wot/schemas/publication-closure.schema.json)
describe different documents. They are independent of these generated
Registry metadata descriptions.
