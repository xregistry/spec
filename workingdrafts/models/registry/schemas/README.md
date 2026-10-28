# Registry-of-Registries Derived Schemas

<!-- words: avsc openapi -->
<!-- words: opc powershell py registryofregistriesdocument ua workingdrafts -->
<!-- words: federationprofiles oneof schemaparseexception uri -->
<!-- words: website -->

The [repository generator](../../../../tools/schema-generator.py) derives these
schema and API descriptions from the [authoritative model](../model.json).
[Core](../../../../core/spec.md) and the [domain specification](../spec.md)
remain authoritative. The generated artifacts describe an unreleased working
draft; their identifiers are not published schema identifiers.

| Format | Generated file |
| --- | --- |
| JSON Schema, Draft 7 | [document-schema.json](document-schema.json) |
| JSON Structure | [document-schema.struct.json](document-schema.struct.json) |
| Avro | [document-schema.avsc](document-schema.avsc) |
| HTTP OpenAPI | [openapi.json](openapi.json) |

The OpenAPI description is for serving the catalog over HTTP. It is not
an HTTP wrapper around native Open Container Initiative (OCI), Git, File or
OPC Unified Architecture (OPC UA) resolution.

## Reproduction

Run these commands from the repository root in PowerShell. The identifiers
and name of the root type match the repository's schema-generation target.

```powershell
python -B tools\schema-generator.py --type json-schema --schema-id https://xregistry.io/workingdrafts/models/registry/schemas/document-schema.json --output workingdrafts\models\registry\schemas\document-schema.json workingdrafts\models\registry\model.json
python -B tools\schema-generator.py --type json-structure --schema-id https://xregistry.io/workingdrafts/models/registry/schemas/document-schema.struct.json --schema-name RegistryOfRegistriesDocument --output workingdrafts\models\registry\schemas\document-schema.struct.json workingdrafts\models\registry\model.json
python -B tools\schema-generator.py --type avro-schema --output workingdrafts\models\registry\schemas\document-schema.avsc workingdrafts\models\registry\model.json
python -B tools\schema-generator.py --type openapi --output workingdrafts\models\registry\schemas\openapi.json workingdrafts\models\registry\model.json
```

The generator writes indented UTF-8 JSON with LF line endings and no final
newline. Do not manually change generated definitions.

## Validation

Parsing the generated JSON documents confirms syntax, not schema validity.
Validate JSON Schema against Draft 7, OpenAPI with an OpenAPI validator and
the Avro definition with the Apache Avro schema parser. For JSON Structure,
check references and schema shape and use any available validator for the
declared dialect.

The repository does not supply a hand-maintained full Resource schema.
Validate the domain's semantic constraints separately:

- Nonempty names,
- Credential-free absolute endpoints,
- Binding-dependent parameters,
- Label semantics,
- Relationship bases, and
- Candidate selection.

## Format Interpretation

### JSON Schema

The schema describes the catalog collection and selected Group, Resource
and Version fields, including the Resource's Versions collection. It does
not describe a complete Core Registry root.

Navigation and relationship fields have an absolute-URI format. That format
does not define document-local pointers or catalog-root references, and
Draft 7 validation without URI format checking does not establish their
validity. The domain separately requires absolute advertisement endpoints.

### JSON Structure

The schema describes the catalog collection and selected Group, Resource
and Version fields, but not a complete Core Registry root. URI reference
fields use strings. Their syntax and base rules still come from the domain.
Names needing an alternate JSON spelling use the declared alternate-name
extension.

The repository validates this dialect's structure and fixtures. It does not
validate every possible JSON Structure extension.

### Avro

The `federationprofiles` and `relationships` arrays contain named records
with their declared fields. Binding parameters contain an extension map
using the generator's generic record representation. The generator does not
generally make OPTIONAL attributes nullable or encode their absence defaults,
so Avro validation does not establish the catalog's presence and selection
semantics.

### HTTP OpenAPI

The description includes `/categories`, its entities, Resource/Version paths
and the shared HTTP operations. It derives metadata schemas from the same
model rather than maintaining another catalog model. Concrete path and schema
checks supplement structural OpenAPI validation; neither certifies a deployed
HTTP server.
