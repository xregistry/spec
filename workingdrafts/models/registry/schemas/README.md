# Registry-of-Registries Derived Schemas

<!-- words: avsc openapi -->
<!-- words: opc powershell py registryofregistriesdocument ua workingdrafts -->
<!-- words: federationprofiles oneof schemaparseexception uri -->
<!-- words: website -->

The [repository generator](../../../../tools/schema-generator.py) derives
these artifacts. It uses the [authoritative model](../model.json) as input.
They do not replace [Core](../../../../core/spec.md). Nor do they replace
the [domain specification](../spec.md).
They remain unreleased working-draft descriptions, not published schema
identifiers.

| Format | Generated file |
| --- | --- |
| JSON Schema, Draft 7 | [document-schema.json](document-schema.json) |
| JSON Structure | [document-schema.struct.json](document-schema.struct.json) |
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
python -B tools\schema-generator.py --type openapi --output workingdrafts\models\registry\schemas\openapi.json workingdrafts\models\registry\model.json
```

The generator writes indented JSON. File output uses the host's text-mode
line endings and has no final newline. Do not manually change generated
definitions.

## Validation

All generated files are JSON documents, but parsing confirms syntax only.
Validate JSON Schema against Draft 7 and OpenAPI with an OpenAPI validator.
JSON Structure needs reference and schema-shape checks, plus any available
validator for its declared dialect.

The repository does not supply a hand-maintained full Resource schema.
Also perform the semantic checks specified in the domain for:

- nonempty names;
- credential-free absolute endpoints;
- binding-dependent parameters;
- label semantics;
- relationship bases; and
- candidate selection.

## Format Interpretation

### JSON Schema

The current schema describes the catalog collection and selected Group,
Resource and Version fields. It does not describe a complete Core Registry
root or connect the Version definition to a Resource's Versions collection.

The schema sets an absolute-URI format on navigation and relationship
fields. That format does not define document-local pointers or catalog-root
references.
Draft 7 validation without URI format checking does not establish the
validity of those references. The domain separately requires advertisement
endpoints to be absolute.

### JSON Structure

The schema describes the catalog collection and selected Group, Resource
and Version fields, but not a complete Core Registry root. URI reference
fields use strings; their syntax and base rules still come from the domain.
Names needing an alternate JSON spelling use the declared alternate-name
extension.

The repository validates this dialect's structure and fixtures. It does not
validate every possible JSON Structure extension.

### HTTP OpenAPI

The description includes `/categories`, its entities, Resource/Version
paths and the shared HTTP operations. It derives the same metadata
schemas rather than maintaining another catalog model. Concrete path and
schema checks supplement structural OpenAPI validation.
It does not certify a deployed HTTP server.
