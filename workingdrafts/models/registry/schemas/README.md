# Registry-of-Registries Derived Schemas

<!-- words: avsc openapi -->
<!-- words: opc powershell py registryofregistriesdocument ua workingdrafts -->
<!-- words: federationprofiles oneof schemaparseexception uri -->
<!-- words: altnames genericrecord website -->

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

The OpenAPI description describes [part of the catalog's HTTP API](#http-openapi).
It is not an HTTP
wrapper around native Open Container Initiative (OCI), Git, File or OPC
Unified Architecture (OPC UA) resolution.

## Reproduction

Run these commands from the repository root in PowerShell. The identifiers
and name of the root type match the repository's schema-generation target.

```powershell
python -B tools\schema-generator.py --type json-schema --schema-id https://xregistry.io/workingdrafts/models/registry/schemas/document-schema.json --output workingdrafts\models\registry\schemas\document-schema.json workingdrafts\models\registry\model.json
python -B tools\schema-generator.py --type json-structure --schema-id https://xregistry.io/workingdrafts/models/registry/schemas/document-schema.struct.json --schema-name RegistryOfRegistriesDocument --output workingdrafts\models\registry\schemas\document-schema.struct.json workingdrafts\models\registry\model.json
python -B tools\schema-generator.py --type avro-schema --output workingdrafts\models\registry\schemas\document-schema.avsc workingdrafts\models\registry\model.json
python -B tools\schema-generator.py --type openapi --output workingdrafts\models\registry\schemas\openapi.json workingdrafts\models\registry\model.json
```

The generator writes indented JSON with no final newline. Line endings
follow the host platform; checked-in schemas use LF. When comparing
generated output on Windows with the tracked files, compare after converting
CRLF line endings to LF. Do not manually change generated definitions.

## Validation

Parsing the generated JSON documents confirms syntax, not schema validity.
Validate JSON Schema against Draft 7, OpenAPI with an OpenAPI validator and
the Avro definition with the Apache Avro schema parser. For JSON Structure,
check references and schema shape. An external validator, if used, needs
to support the extended JSON Structure dialect named by the file's
`$schema` field.

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
and Version fields. It does not describe a complete Core Registry root or
fully constrain the Resource's Versions collection.

Navigation and relationship fields use `format: uri`. With format checks
enabled, a Draft 7 validator can reject valid domain references such as
`#/categories/public` because they are not absolute URIs. Disabling URI
format checks does not prove that those references are valid; apply the
domain rules separately. Advertisement endpoints still have to be absolute.

### JSON Structure

The schema describes the catalog collection and selected Group, Resource
and Version fields, but not a complete Core Registry root. URI reference
fields use strings. Their syntax and base rules still come from the domain.
When the [generator](../../../../tools/schema-generator.py) needs an
alternate JSON spelling, it emits an `altnames` extension member in that
property's schema, with the alternate spelling under `json`.

The repository validates this dialect's structure and fixtures. It does not
validate every possible JSON Structure extension.

### Avro

The `federationprofiles` and `relationships` arrays contain named records
with their declared fields. Binding parameters use `io.xregistry.GenericRecord`,
which does not encode the parameter shapes of the individual bindings. The
existing generator does not separately encode
Resource and Version records for this model, and does not generally make
OPTIONAL attributes nullable or encode their absence defaults. Avro
validation therefore does not establish the catalog's Version, presence
or selection semantics.

### HTTP OpenAPI

The description includes category entities, Resource/Version paths and
shared HTTP operations. The existing generator omits the `/categories`
collection path. It derives metadata schemas from the same model rather
than maintaining another catalog model. Structural OpenAPI validation does
not establish complete model coverage or certify a deployed HTTP server.
