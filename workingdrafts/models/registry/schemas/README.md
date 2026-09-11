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
| Apache Avro | [document-schema.avsc](document-schema.avsc) |
| HTTP OpenAPI | [openapi.json](openapi.json) |

The OpenAPI description is for serving the catalog over HTTP. It is not
an HTTP wrapper around native OCI, Git, File or OPC UA resolution.

## Reproduction

Run these commands from the repository root in PowerShell. The identifiers
and root type name match the repository's schema-generation target.

```powershell
python -B tools\schema-generator.py `
  --type json-schema `
  --schema-id https://xregistry.io/workingdrafts/models/registry/schemas/document-schema.json `
  --output workingdrafts\models\registry\schemas\document-schema.json `
  workingdrafts\models\registry\model.json
python -B tools\schema-generator.py `
  --type json-structure `
  --schema-id https://xregistry.io/workingdrafts/models/registry/schemas/document-schema.struct.json `
  --schema-name RegistryOfRegistriesDocument `
  --output workingdrafts\models\registry\schemas\document-schema.struct.json `
  workingdrafts\models\registry\model.json
python -B tools\schema-generator.py `
  --type avro-schema `
  --output workingdrafts\models\registry\schemas\document-schema.avsc `
  workingdrafts\models\registry\model.json
python -B tools\schema-generator.py `
  --type openapi `
  --output workingdrafts\models\registry\schemas\openapi.json `
  workingdrafts\models\registry\model.json
```

The generator writes UTF-8 JSON with LF line endings and a final newline
on every supported host. Do not manually change generated definitions.

## Validation

All generated files are JSON documents, including the Avro description.
Parsing their JSON is only the first check. JSON Schema needs its Draft 7
schema check. Avro needs an Avro schema parser. OpenAPI needs an OpenAPI
validator. JSON Structure needs reference and schema-shape checks as well
as any available validator for its declared dialect.

No hand-maintained full Resource schema is supplied. Nonempty names,
credential-free absolute endpoints, binding-dependent parameters, label
semantics, relationship bases and candidate selection also need the
semantic checks specified in the domain.

## Format Interpretation

### JSON Schema

The schema permits collection navigation together with inlined Versions,
and includes Core root and Meta metadata. URI references accept document
pointers and catalog-root relationship targets. The domain separately
requires advertisement endpoints to be absolute. The complete catalog
samples are validated with Draft 7 and format assertions enabled.

### JSON Structure

The schema describes Core root metadata, navigation, Resource Meta objects
and Version metadata in addition to domain attributes. URI references use
strings because the model permits relative references. Names needing an
alternate JSON spelling use the declared alternate-name extension.

The repository supplies structural and fixture checks for this dialect,
not a general JSON Structure validator for every possible extension.

### Avro

The binary record projection preserves structured advertisement and
relationship arrays, Meta data and Version collections. OPTIONAL model
fields use nullable unions. Their absence does not turn a website-only
entry into an invalid catalog. The REQUIRED advertisement `name` and
`endpoint` remain non-nullable.

Avro's named records, extension maps and generic-value wrapper are not
the Core JSON wire representation. Its schema validates that binary
projection, not an unmodified JSON catalog document. Core semantics and
domain constraints still require separate validation.

### HTTP OpenAPI

The description includes `/categories`, its entities, Resource/Version
paths and the shared HTTP operations. It derives the same metadata
schemas rather than maintaining another catalog model. Structural
OpenAPI validation is supplemented by concrete path and schema checks.
It does not certify a deployed HTTP server.
