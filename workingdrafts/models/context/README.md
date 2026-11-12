# Event Context Registry Service - Version 1.0-rc4

<!-- words: contexturl eventdefinition mediatype standalone -->

See the [Event Context Registry specification](spec.md), its
[design rationale](design/design.md) and [model](model.json). The
[sample](samples/context.json) contains one Context Group with two Contexts.

The generated [JSON Schema](schemas/document-schema.json),
[JSON Structure](schemas/document-schema.struct.json),
[Avro](schemas/document-schema.avsc) and [OpenAPI](schemas/openapi.json)
describe selected Registry metadata.

In particular, Core has no model aspect for a minimum map size. Generated
schemas do not enforce the non-empty `references` rule in the specification.
Role-name constraints and URL constraints also need checks beyond formats
that cannot express them, such as Avro. Passing schema validation alone is
not proof of conformance.

The [design note's comparison with xregistry/spec#571][draft-boundaries]
distinguishes event Contexts from federation contexts, publication snapshots
and the proposed WoT event profile.

## Open Questions

1. **Attribute name.** `contexturl` might be confused with the CloudEvents
   term "context attributes". It also matches the Core `<RESOURCE>url`
   naming pattern for a Resource named `context`; that Core attribute never
   appears because Contexts have no document. The relationship to the
   attribute that [#792][issue792] proposes and to the `eventdefinition`
   attribute proposed in [#314][issue314-proposal] needs to be settled.
2. **Role registration.** Where Roles are registered, and whether `emitter`
   and `target` need domain-specific variants.
3. **Reference attributes.** Whether References gain a `digest` for
   integrity or a `mediatype`. Selecting one definition within a schema
   document needs a fragment, which `urlabsolute` excludes.
4. **Same-Registry references.** Whether `url` gains an [`xid`][Core xid]
   alternative so that a server can check the Target type. A Consumer would
   then resolve the `xid` against the Registry root, which is a URL
   derivation this specification avoids.
5. **Server enforcement.** How a server can enforce Version stability and
   retention. The Core `immutable` aspect applies only to
   specification-defined attributes.
6. **Other profile precedence.** How profiles other than the proposed WoT
   CloudEvents profile handle a `source` interpretation that differs from
   the Context's `emitter` Reference.
7. **Placement.** Whether the Context model is a standalone domain or part of
   the [CloudEvents Registry](../../../cloudevents/spec.md) composite.
8. **Context document.** Whether a Context has a document that contains its
   Targets' content, with the metadata at the `$details` URL, instead of the
   Registry-specific resolved Context view. That view requires custom
   server-side resolution and is not supported by generic xRegistry or static
   document servers. The [design note][context-document] compares the
   alternatives.

[issue792]: https://github.com/xregistry/spec/issues/792
[issue314-proposal]: https://github.com/xregistry/spec/issues/314#issuecomment-2880321588
[Core xid]: ../../../core/spec.md#xid-attribute
[draft-boundaries]: design/design.md#71-relationship-to-federation-publication-and-wot
[context-document]: design/design.md#81-context-document-alternative
