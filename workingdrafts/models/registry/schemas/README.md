# Registry-of-Registries Derived Schemas

<!-- words: avsc openapi -->
<!-- words: opc powershell py registryofregistriesdocument ua workingdrafts -->
<!-- words: federationprofiles oneof schemaparseexception uri -->
<!-- words: website -->

These artifacts are derived from the [authoritative model](../model.json)
by [the repository generator](../../../../tools/schema-generator.py).
They do not replace [Core](../../../../core/spec.md) or the
[domain specification](../spec.md), and are unreleased working-draft
descriptions rather than published schema identifiers.

| Format | Generated file |
| --- | --- |
| JSON Schema, Draft 7 | [document-schema.json](document-schema.json) |
| JSON Structure | [document-schema.struct.json](document-schema.struct.json) |
| HTTP OpenAPI | [openapi.json](openapi.json) |

The OpenAPI description is for serving the catalog over HTTP. It is not
an HTTP wrapper around native OCI, Git, File or OPC UA resolution.

## Reproduction

Run these commands from the repository root in PowerShell. The identifiers
and root type name match the repository's schema-generation target.

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

No hand-maintained full Resource schema is supplied. Nonempty names,
credential-free absolute endpoints, binding-dependent parameters, label
semantics, relationship bases and candidate selection also need the
semantic checks specified in the domain.

## Format Interpretation

### JSON Schema

The current schema describes the catalog collection and selected Group,
Resource and Version fields. It does not describe a complete Core Registry
root or connect the Version definition to a Resource's Versions collection.

Navigation and relationship fields use absolute-URI format declarations,
which do not describe document-local pointers or catalog-root references.
Draft 7 validation without URI format checking does not establish the
validity of those references. The domain separately requires advertisement
endpoints to be absolute.

### JSON Structure

The schema describes the catalog collection and selected Group, Resource
and Version fields, but not a complete Core Registry root. URI reference
fields use strings; their syntax and base rules still come from the domain.
Names needing an alternate JSON spelling use the declared alternate-name
extension.

The repository supplies structural and fixture checks for this dialect,
not a general JSON Structure validator for every possible extension.

### HTTP OpenAPI

The description includes `/categories`, its entities, Resource/Version
paths and the shared HTTP operations. It derives the same metadata
schemas rather than maintaining another catalog model. Structural
OpenAPI validation is supplemented by concrete path and schema checks.
It does not certify a deployed HTTP server.
