# Descriptor Registry Service - Version 1.0-rc4

<!-- words: describedby entityid entitytype schemaref -->
<!-- words: opc ua prebuilt TDs USD affordance OpenUSD -->
<!-- words: marcschier workingdrafts opcf -->

See the [Descriptor Registry specification](spec.md), its
[design rationale](design/design.md) and [model](model.json). This working
draft describes assets, devices, actors and shared processing context
through one metadata-only Resource shape. The companion
[CloudEvents proposal](https://github.com/cloudevents/spec/pull/1406) owns
`describedby` and the WoT/OPC UA event bindings.

The [sample](samples/descriptor.json) is a Core create/update input, not a
complete response. It contains an Asset Descriptor with a TD and USD asset,
an Actor Descriptor with empty `references`, and a Context Descriptor with
two TDs, explicit schema selection and typed OPC UA metadata. The Context
does not inherit metadata from the Asset. Group IDs and entity types are
illustrative catalog choices. Example URLs are not deployed services.

The generated [JSON Schema](schemas/document-schema.json),
[JSON Structure](schemas/document-schema.struct.json),
[Avro](schemas/document-schema.avsc) and [OpenAPI](schemas/openapi.json)
describe selected Registry metadata. They do not replace the domain rules:
absolute identity URI syntax, Reference names and classes, selector
existence/class, `entitytype` requiring `entityid`, specialization
requirements and publication stability need additional validation.
The base model permits profile extensions. The
[WoT Descriptor profile][WoT profile] owns projection provenance and TD/TM
selection, including subject Descriptors that annotate an affordance pointer.
The [OpenUSD Descriptor profile][OpenUSD profile] defines asset References.
These profiles define URI class identifiers; the generic base defines only
the `schema` bare class.
The [CloudEvents OPC UA extension][OPC profile] defines how native identity
and shared metadata are conveyed through events and Descriptors.
The OPC UA sample attributes are illustrative extensions.

Ordinary TD storage and WoT event processing can operate without
Descriptors. A route or processing profile that relies on Descriptor
inputs requires one. A subject Descriptor identifies the subject and its
annotations; it does not supply missing processing schema or native metadata
unless it is also explicitly selected in that processing role.

The Descriptor Avro generation command uses the opt-in
`--avro-nullable-optionals` in [tools/Makefile](../../../tools/Makefile).
It represents absent OPTIONAL fields through nullable field types and
defaults, including nested References. The generator's default output and
the published Schema, Message, Endpoint and CloudEvents Avro artifacts are
unchanged. Avro null values are serialization details, not a change to
Core JSON response or write semantics.
The option does not change integer widths; a profile's encoding needs to
support the value ranges that profile declares.

Ordinary GET returns metadata. The OPTIONAL
[Descriptor bundle](spec.md#74-descriptor-bundle) needs additional
resolver/serving behavior; generic Core does not assemble it. A configured
static endpoint can serve a prebuilt bundle subject to the same completeness,
authorization, freshness and Version-selection rules. It is not a snapshot.

## Scope and Deferred Work

The [comparison with other drafts][draft boundaries] separates Descriptors
from federation contexts, publication snapshots and runtime readiness.
The [document alternative][document alternative] remains recorded as a
trade-off, not the selected model.

Message definitions are not standard References: the Message model retains
only one Version, so replacing it changes the metadata at the same URL.
Descriptors reference the payload schema directly.

The CloudEvents extension owns event-link and schema selection. The WoT
draft and OPC UA companion specification own their profile rules.

Digest schemes, transitive packaging, a universal entity vocabulary and new
lifecycle or execution APIs are outside this draft.

[draft boundaries]: design/design.md#6-relationship-to-federation-publication-and-wot
[document alternative]: design/design.md#71-descriptor-document-alternative
[WoT profile]: https://github.com/marcschier/xregistry-drafts/pull/8
[OpenUSD profile]: ../openusd/descriptor-profile.md
[OPC profile]: https://github.com/cloudevents/spec/pull/1406
