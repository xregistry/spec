# Descriptor Registry Service - Version 1.0-rc4

<!-- words: describedby entityid entitytype schemaref endpointref thingref affordanceselector -->
<!-- words: opc ua opcua prebuilt TDs USD affordance OpenUSD -->
<!-- words: workingdrafts -->
<!-- words: thingdescription thingmodel usdasset -->
<!-- words: opcuawriter -->
<!-- words: GenericRecord -->
<!-- words: actorinfo servicekind -->

See the [Descriptor Registry specification](spec.md), its
[design rationale](design/design.md) and [model](model.json). This working
draft describes assets, devices, actors and shared processing context
through one metadata-only Resource shape. The companion
[CloudEvents proposal](https://github.com/cloudevents/spec/pull/1406) owns
the common `describedby` contract and failure boundary. Applicable profiles
define `source`/`subject` interpretation and native metadata mappings.
xRegistry defines Descriptor structure and versioning.

The [sample](samples/descriptor.json) is a Core create/update input, not a
complete response. It contains an Asset Descriptor with a TD and USD asset,
an Actor Descriptor with empty `references`, and a Context Descriptor with
two TDs, explicit schema selection and typed OPC UA metadata. The Context
does not inherit metadata from the Asset. Group IDs and entity types are
illustrative catalog choices. Example URLs are not deployed services.
The Actor's deployment-defined `acme_servicekind` string is inline under
`data.com.example.actorinfo`, not a Core attribute or top-level selector.

An Actor Descriptor describes a participant independently of the roles it
plays in conversations. Publisher, Producer and Consumer are responsibilities
that one actor can combine. Processing descriptions supply interpretation
inputs; execution observations record reported sends, receipts or processing
outcomes separately.

The generated [JSON Schema](schemas/document-schema.json),
[JSON Structure](schemas/document-schema.struct.json),
[Avro](schemas/document-schema.avsc) and [OpenAPI](schemas/openapi.json)
describe selected Registry metadata. They do not replace the domain rules:
absolute identity URI syntax, Reference names and types, selector
existence/bucket, `entitytype` requiring `entityid`, specialization
requirements, type-key syntax, globally unique Reference names and
publication stability need additional validation. The generic model uses
`references.<type>.<name>.url` for retrievable representations and OPTIONAL
`data.<type>` for profile-defined inline values. Reference records have no
`class` field; type keys use coordinated standard tokens or independently
defined reverse-DNS names within Core's map-key limits. URI type keys and
the former flat Reference shape are not aliases.

The base model permits profile extensions. The
WoT Descriptor profile owns projection provenance and TD/TM
selection. A subject Descriptor uses `thingref` to select the TD and an
OPTIONAL `affordanceselector` to select and annotate a specific affordance.
Without that selector, the subject is the whole Thing.
The [OpenUSD Descriptor profile][OpenUSD profile] defines the `usdasset`
Reference bucket.
The [Schema Descriptor profile](spec.md#9-schema-descriptor-profile) defines
the `schema` Reference bucket, `schemaref` and schema selection. The
[Endpoint Descriptor profile](spec.md#10-endpoint-descriptor-profile)
defines the `endpoint` metadata bucket and `endpointref`. Both profiles are
hosted at the end of this working draft for later relocation into their
respective specifications. The generic base defines no representation
types or profile selectors.
Standard-profile type keys use one coordinated canonical token:
`schema`, `thingdescription`, `thingmodel`, `usdasset` or `endpoint`, as
defined by the respective profile. Independently defined types use
domain-qualified keys such as `com.example.calibration`; keys are not
resolved as network addresses. Inline values follow the profile's declared
Core-compatible types rather than a universal string metadata bag.
The [CloudEvents OPC UA extension][OPC profile] defines how native identity
and shared metadata are conveyed through events and Descriptors.
The stream sample's four existing native fields and values are grouped in
`data.opcuawriter`. This inline value is not part of Reference retrieval.
Selectors remain top-level exact names, unique across all Reference buckets.

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
The existing Avro `any` projection uses `GenericRecord.object`; it is not a
direct encoding of every Core value that the generic `data` map permits.

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
The Schema Descriptor profile references the payload schema directly.

The CloudEvents extensions own event-link and schema selection and OPC UA
metadata conveyance. The WoT draft owns TD selection and affordance
annotation rules.

Digest schemes, transitive packaging, a universal entity vocabulary and new
lifecycle or execution APIs are outside this draft.

[draft boundaries]: design/design.md#6-relationship-to-federation-publication-and-wot
[document alternative]: design/design.md#71-descriptor-document-alternative
[OpenUSD profile]: ../openusd/spec.md#57-descriptor-profile
[OPC profile]: https://github.com/cloudevents/spec/blob/1c4caca73c69a7e076e75fe0727f6a216c83e500/cloudevents/extensions/opcua.md#opc-ua-descriptor-profile
