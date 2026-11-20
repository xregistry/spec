# Descriptor Registry Service - Version 1.0-rc4

<!-- words: describedby descriptorid entityid entitytype bundleurl readonly -->
<!-- words: thingdescription usdasset opcuawriter actorinfo servicekind -->
<!-- words: OpenUSD opc ua GenericRecord -->
<!-- words: hasdocument -->

See the [specification](spec.md), [model](model.json) and
[design rationale](design/design.md). This working draft maps the portable
Descriptor fields directly to native xRegistry Version metadata. Ordinary
GET returns `descriptorid`, `versionid`, `entries`, OPTIONAL identity/bundle
fields and Core bookkeeping. No translation or Resource document view is
needed; `hasdocument` remains false.

The [CloudEvents working draft][CE] owns `describedby`, portable response
validation, the bundle object and all entry profiles, including WoT,
OPC UA, Schema, Endpoint and OpenUSD. xRegistry defines storage, writes,
identity, publication stability and single-hop bundle negotiation. Entry
profiles are reviewed through that PR; previous pinned sources are not
authority for the new shape.

Each entry has a REQUIRED `class`, an OPTIONAL absolute HTTP(S)
URL and colocated profile fields. Linked profiles require the URL; inline
profiles omit it and reject null. Repeated classes are allowed; selection
belongs to the profile, not a generic selector.

The [sample](samples/descriptor.json) contains Core create/update inputs,
not full responses. It includes entity and actor descriptions and shared
telemetry. Writer metadata is inline with its entry, without a URL.
Deployment-defined actor metadata uses a domain-qualified class.

Generated [JSON Schema](schemas/document-schema.json),
[JSON Structure](schemas/document-schema.struct.json),
[Avro](schemas/document-schema.avsc) and [OpenAPI](schemas/openapi.json)
describe the native projection. They need the portable schema and semantic
profile checks for URL schemes, class values, linked/inline admission,
profile selection and retention. Core `entitytype` is xRegistry-specific
metadata, not a portable entry selector.

`bundleurl` is OPTIONAL server-managed metadata. A supporting deployment
advertises a direct bundle URL and can negotiate the portable bundled
media type at the selected URL. Core does not assemble it automatically.
The portable bundle keeps the same fields, embedding documents only under
linked entries. [xRegistry negotiation](spec.md#55-bundled-representations)
retrieves that bundle in one request at the original Descriptor URL.

Descriptor Avro generation retains the opt-in `--avro-nullable-optionals`.
This changes field optionality, not Core JSON null semantics or integer
width. GenericRecord extension values require the existing Avro mapping;
generated formats are not substitutes for the portable JSON contract.
The existing top-level Schema, Message, Endpoint and CloudEvents artifacts
and generator behavior remain unchanged.

[CE]: https://github.com/cloudevents/spec/pull/1406
