# Descriptor Registry - Design

<!-- words: describedby entityid bundleurl GenericRecord -->
<!-- words: OpenUSD opc ua opcuawriter actorinfo -->
<!-- words: hasdocument matchversions nullability prebuilt -->

Expose the portable Descriptor fields as native xRegistry Version metadata.
CloudEvents defines the portable representation and entry profiles;
xRegistry stores and versions those fields and adds Core bookkeeping.
An ordinary GET therefore needs no adapter or alternate document view.

This rationale explains the [working draft](../spec.md). It does not add
requirements to the [portable CloudEvents contract][CE].

## 1. Why separate description from the event?

Several messages can use the same participant description, payload schema
and processing configuration. Listing every representation in every event
repeats that configuration and couples the envelope to its inventory.
An independently versioned description lets Consumers retrieve the inputs
selected by the event profile.

A catalog has the same need without messages: describe one entity through
several representations. Actor identity remains independent of conversation
roles. Processing descriptions do not become execution traces merely
because several actors use them.

## 2. One named entry map

The portable `entries` map names each representation or inline description.
An entry has a class, an OPTIONAL URL and profile fields at that same level.
A profile defines how to select an entry or report ambiguity when classes
repeat. The base Registry does not select schemas, Things or native writers.

Linked profiles require an absolute HTTP(S) URL. Inline profiles omit it.
Null is not an alternative inline marker. This distinction fits Core
metadata: an OPTIONAL URL can be absent, while a null write follows deletion
semantics. No nullable REQUIRED Core field is needed.

The shared stream retains its pump and gateway TD URLs, schema and OpenUSD
asset Version URLs and native writer values. The writer entry is inline,
so ordinary interpretation does not fetch another configuration URL.

## 3. Native metadata rather than a stored document

A Resource document would preserve an opaque portable JSON body, but it
would introduce separate metadata and document views and require comparison
of document IDs with enclosing Registry IDs. Native metadata uses the same
Core IDs in the response and ordinary write processing.

The chosen Resource remains `hasdocument: false`. `entries` is a REQUIRED
map; `class` is REQUIRED within each entry; `url` is OPTIONAL. Profile
extensions remain Core-compatible attributes. The portable schema imposes
additional URL and profile constraints that the generic generator cannot
fully express.

Core properties describe the Registry entity, not extra interpretation
inputs. Epochs, lineage and default-Version selection retain Core semantics.
`entityid` uses `matchversions` for retained-Version comparison, while
publication policy prevents historical reassignment after deletion or
simultaneous updates.

## 4. Publication and replay

A Publisher makes REQUIRED representations available before releasing a
Descriptor for use. Once published, processing-significant metadata at
that Version remains stable. Changes create new Versions; they do not
repurpose an existing URL for another entity or interpretation.

Replay needs retained Descriptors and retained linked content. A Registry
Version URL alone cannot preserve content at another origin or establish
its authenticity. A missing historical input is reported rather than
replaced by current configuration.

Metadata writes follow Core replacement and PATCH rules. Inline URL
omission is not an instruction to recursively merge profile fields.
Consumers and Publishers apply the profile's linked/inline requirements;
deleting a linked entry's URL does not make it an inline entry.

## 5. Bundled response capability

CloudEvents defines the bundle object and OPTIONAL direct GET through
`bundleurl`. This working draft adds negotiation at the original
`describedby` URL to retrieve that same bundle in one request. Clients
follow advertised URLs; they do not derive paths or add/remove `$details`.

A bundle keeps the same Descriptor fields and embeds a `document` under
each linked entry. Inline entries omit both URL and document. The bundle
does not fetch transitive dependencies or define another stored Registry
document.

Supporting deployments need resolver or prebuilt-response behavior beyond
generic Core metadata serving. Authorization, outbound policy, limits,
combined freshness and caller isolation apply regardless of where assembly
occurs. Arriving in one response does not make the content an atomic snapshot.

## 6. Ownership and limits

CloudEvents owns the common selection/failure contract, portable schema
and all entry definitions. Profiles define source/subject interpretation,
schema precedence and native metadata conveyance. This draft owns native
Registry storage, Core writes, publication stability and single-hop bundle
negotiation. CloudEvents retains the bundle representation and direct
retrieval contract.

The [OpenUSD working draft](../../openusd/spec.md) provisions artifact
representations; its portable entry definition belongs to CloudEvents.
Schema and Endpoint standards are unchanged by this working draft.

The generated formats describe a projection, not full portable conformance.
The existing Avro GenericRecord mapping has its own extension encoding and
integer-width constraints. Neither the field-nullability opt-in nor this
domain changes Core or repairs unrelated generator behavior.

Execution provenance, runtime admission, orchestration, cryptographic
attestation and transitive packaging are separate capabilities. A published
description is not evidence that a message was delivered or processed.

[CE]: https://github.com/cloudevents/spec/pull/1406
