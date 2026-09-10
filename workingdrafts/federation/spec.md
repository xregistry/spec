# xRegistry Federation

<!-- words: applicationuri federationprofiles nfc nodeid nodeids opc opcua rebasing registrygroups registryroot reparse standalone symlinks transportprofileuri ua website weburl xregurl -->

## Abstract

This specification defines read-only resolution across independently
administered xRegistries. A Registry of Registries describes access methods;
a resolver chooses a method, establishes a Registry context and interprets
that Registry using xRegistry Core. Protocol bindings define retrieval, not a
new identity system or changes to Core cross-references.

**Status:** Unreleased working draft. This specification and its companion
bindings are not part of a released xRegistry specification.

## Table of Contents

- [Overview](#overview)
- [Notations and Terminology](#notations-and-terminology)
- [Discovery and Binding Selection](#discovery-and-binding-selection)
- [Read Operations](#read-operations)
- [Identity and References](#identity-and-references)
- [Selectors](#selectors)
- [Representations](#representations)
- [Snapshots and Completeness](#snapshots-and-completeness)
- [Errors](#errors)
- [Security Considerations](#security-considerations)
- [Conformance](#conformance)
- [Source Reconciliation](#source-reconciliation)
- [References](#references)

## Overview

Federation permits a consumer to find and read entities through a catalog
without requiring all content to be copied into that catalog. The
[Registry domain](../models/registry/spec.md) retains the deployed hub's
`categories` / `registries` hierarchy. A catalog entry is itself a
metadata-only Resource. It describes another Registry; it is not that
Registry's root.

This specification defines the shared interpretation of resolution requests.
[HTTP](../bindings/http-federation.md), [OCI](../bindings/oci.md),
[Git](../bindings/git.md), [File](../bindings/file.md) and
[OPC UA](../bindings/opcua.md) define how to perform those reads. The
[document-tree format](document-format.md) is shared by Git and File.
Native bindings do not require an HTTP facade.

This specification does not define synchronization, replication, write-through,
global entity identifiers, arbitrary merge precedence or discovery of
dependencies embedded inside domain documents. OCI publication is a separate
producer operation; describing it does not grant a reader publication rights.

## Notations and Terminology

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this
document are to be interpreted as described in
[RFC2119](https://www.rfc-editor.org/rfc/rfc2119).

This specification uses [Core terminology](../../core/spec.md) and the
[Core model language](../../core/model.md), Version 1.0-rc4. A binding's
format-version discriminator identifies its package interpretation, not a
different Core Version or a catalog-description Version.

| Term | Meaning |
| --- | --- |
| Catalog | A Registry using the Registry domain to describe other Registries. |
| Catalog entry | A `registry` Resource under a `category` Group. |
| Advertisement | One access method in a catalog-description Version. |
| Registry context | The selected logical Registry, model and access context in which an XID is interpreted. |
| Revision pin | A binding's immutable snapshot selection, when supported. |
| Origin | The catalog entry, advertisement and revision used for a result. |
| Resolver | A consumer implementing this specification and a named binding. |
| Snapshot | A captured Registry state, independent of earlier snapshots. |
| Linked snapshot | A complete internal package graph allowing explicit external document references. |
| Offline-complete snapshot | A snapshot also carrying all declared xRegistry documents in its selected scope. |

The catalog's `registryid`, its entry's `registryid` and the described
Registry root's `registryid` have different scopes. Their values need not
match. A catalog-description `versionid`, target Resource `versionid`, OCI
digest, Git commit and endpoint address MUST NOT be treated as interchangeable.

## Discovery and Binding Selection

A resolver MUST select a catalog-description Version before interpreting its
advertisements. In the absence of an explicit description Version, it MUST
use the catalog Resource's Core default Version. A resolver MUST NOT infer
an API from `weburl`, a label, a category name or a descriptive relationship.
A website-only entry is a valid catalog entry, but is not resolvable.

The domain's `federationprofiles` array contains advertisements with `name`,
`endpoint`, OPTIONAL `priority` and OPTIONAL `parameters`. Profile names
are case-sensitive. The names defined by this family are:

| Name | Endpoint | Parameters |
| --- | --- | --- |
| `http` | HTTP(S) Registry root | None. |
| `oci` | `oci://host/repository` | `reference`: tag or `sha256` digest. |
| `git` | HTTPS repository URL | `revision`: full ref or complete object ID; `path` defaults to `xregistry`, with an empty string selecting the repository root. |
| `file` | File URI selecting a directory | `layout`: `document-tree` or `oci-layout`; `reference` for OCI layout selection only. |
| `opcua` | Native UA endpoint URL | `registryroot`: portable NodeId; OPTIONAL `applicationuri` and `transportprofileuri`. |

The bindings define parameter grammars and their supported transports.
Endpoints MUST be absolute URIs and MUST NOT embed credentials. A selected
built-in advertisement with an unknown parameter MUST produce
`unsupported_operation`; silently ignoring a parameter could select a
different Registry or revision. An unknown profile name remains valid catalog
metadata, but MUST NOT be executed as a known profile.

An absent `priority` means zero; lower unsigned integer values are preferred.
An absent `parameters` means an empty object. Selection MUST proceed as follows:

1. Validate the catalog's advertised legacy/explicit HTTP consistency as
   specified by the Registry domain.
2. Apply the caller's explicit profile choice and access policy.
3. Remove unsupported profile names from consideration.
4. Order remaining advertisements by ascending priority, preserving array
   order for ties.
5. Choose the first remaining advertisement and validate its parameters.

A present `xregurl` contributes an implicit HTTP advertisement of priority
zero, after explicit advertisements for tie-breaking. This applies even if
an explicit advertisement names the same endpoint at another priority. If
explicit HTTP advertisements exist, at least one endpoint MUST equal
`xregurl` exactly. This exact comparison is a consistency rule, not a
definition of URI identity.

No candidate yields `unsupported_binding`. A caller rejection yields
`policy_denied`. An attempted binding MUST NOT silently fail over after an
integrity error, version mismatch, policy rejection, ambiguous selection or
inconsistent snapshot. A caller MAY initiate another operation with an
explicitly different advertisement after inspecting the failure. A producer's
multiple endpoints claim the same logical Registry, not necessarily the same
instantaneous state. Credentials and trust are established independently.

## Read Operations

The following abstract operations define common behavior, not new URLs,
HTTP verbs or a transport-level request envelope:

| Operation | Target | Result |
| --- | --- | --- |
| `model` | `/` | The selected Registry's interpreted model and available model source. |
| `capabilities` | `/` | Capabilities of the selected access method. |
| `collection` | Typed collection path | Collection members, with explicit completeness or continuation information. |
| `entity` | Registry, Group, Resource, Meta or Version XID | xRegistry metadata, not raw domain content. |
| `document` | Resource or Version XID | Domain bytes, or an explicit failure or external-document locator. |

A Resource document request selects its Core default Version. An explicit
Version request selects exactly that Version, case-sensitively. Neither
operation selects the greatest Version string, latest OCI tag, newest Git
commit or most recently modified file. Metadata-only Resources have no domain
document; requesting one MUST produce `unsupported_operation`.

For each operation a resolver MUST:

1. Establish the selected Registry root and any revision pin.
2. Obtain the model needed to interpret the target and check supported Core
   and binding versions before interpreting entities.
3. Obtain or derive the binding's declared capabilities without inventing
   support for filters, writes, atomic snapshots or inline representations.
4. Resolve the typed target and any selector in that Registry context.
5. Apply Core Resource, default-Version, Meta and `xref` semantics.
6. Retrieve the requested view, checking the binding's integrity and
   consistency rules.
7. Return the result with its origin and revision context, or a specific
   failure.

Origin information MUST identify the chosen advertisement, catalog-description
Version when applicable, target XID and revision pin or the absence of an
immutable pin. It MUST travel separately from Core identity attributes.
A standalone endpoint supplied by the caller MAY bypass catalog discovery,
but MUST still establish all other context.

If a model is captured, the package MUST preserve enough model source to
retain Resource type sharing. An expanded model alone can obscure
`ximportresources` provenance. Included model documents MUST be resolved
within the captured scope, or supplied with immutable checked references;
offline-complete interpretation MUST NOT fetch mutable external includes.
Unknown Core versions MUST NOT be accepted merely because a document parses.

## Identity and References

An XID identifies an entity only within one Registry. Resolvers MUST preserve
both its Registry context and typed collection path. Equal XIDs in unrelated
Registries are not evidence that the entities or their bytes are identical.
Core IDs are unique case-insensitively within their parent, but are looked up
case-sensitively. Storage bindings MUST NOT weaken either rule.

### Local Cross-References

Core [`meta.xref`](../../core/spec.md#cross-referencing-resources) remains
an intra-Registry Resource XID. It MUST NOT contain an endpoint URL, OCI
locator or remote Registry selector. Its source and target MUST have the
same Resource model type; structurally identical independent definitions
are insufficient. Sharing between Group types uses
[`ximportresources`](../../core/model.md#reuse-of-resource-definitions).

For example, this model source permits a local alias from a mirror Group
to an asset in a document Group:

```json
{
  "groups": {
    "documents": {
      "singular": "document",
      "resources": {
        "assets": {
          "singular": "asset"
        }
      }
    },
    "mirrors": {
      "singular": "mirror",
      "ximportresources": ["/documents/assets"]
    }
  }
}
```

An alias in `/mirrors/local/assets/copy` can then carry
`meta.xref: "/documents/main/assets/item"`. When Core calls for inherited
target metadata, source IDs and navigation MUST remain source-relative.
If the target is itself an alias, a resolver MUST NOT follow another `xref`.
If the target is unavailable, Core's minimal ID-like alias serialization
applies; this is not automatically `not_found` for the source.

A malformed XID or nonexistent model type is not the same as a dangling
entity instance. Core's malformed-reference rules still apply. Document
view MUST NOT expand the target. A document-view request for an alias's
Versions or an individual Version MUST retain Core's `cannot_doc_xref`
behavior. This specification does not add remote writes to aliases.

### Remote References and Composition

A Version's `<RESOURCE>url` references a domain document. It MUST NOT be
interpreted as remote Resource metadata or as a request to import Versions.
Reading its bytes does not change the identity of the describing Version.

A projected Registry MAY expose locally modeled Resources representing
external content. Any `xref` it exposes MUST satisfy Core within that
projected Registry. A projection MUST NOT equate resources solely because
their XIDs collide. Competing origins require an explicit selection or
`ambiguous`, not an undocumented winner. A shared logical-identity policy
can be defined by a domain, but does not alter XID scope.

Catalog relationships are descriptions, not instructions to walk a graph,
copy registries, establish trust or synchronize changes.

### Reference Bases

| Reference | Resolution base |
| --- | --- |
| Core XID or `meta.xref` | Selected Registry root, never the current file's directory. |
| Relationship target starting with `/` | Containing catalog Registry root. |
| Absolute relationship target | The explicitly identified external catalog. |
| Package storage reference | The selected package root or record base defined by its format. |
| Relative domain-document URI | The document's declared origin/base under its binding; not an inferred catalog URL. |
| Model include | The model source document containing the include, following Core. |
| `#` JSON Pointer navigation | The returned JSON document. |

A resolver MUST NOT substitute one of these bases for another. A binding
that cannot preserve or supply the base needed to interpret a relative
document URI MUST report `invalid_package` or `unsupported_operation`
rather than guess.

## Selectors

A label selector is scoped to one named collection. Its JSON illustration,
used by the conformance examples, is:

```json
{
  "operation": "collection",
  "target": "/documents/main/assets",
  "selector": {
    "label": "stage",
    "value": "production"
  }
}
```

The [request schema](schemas/request.json) constrains these example envelopes;
the operation table and Core constrain typed paths and semantics.

The `label` names a map key; `value` is a literal string. Labels MAY be absent,
and an empty string value is valid. An absent key does not match an empty
value. Comparison MUST follow Core's case-insensitive string filtering;
en-US Unicode collation is STRONGLY RECOMMENDED by Core. This specification
adds neither mandatory language keys nor NFC normalization. Map-key selection
remains exact; comparison applies to the selected value.

A resolver using a transport filter MUST escape its literal value and
attribute path under that binding; `*`, `\`, `.` or an operator in a selector
MUST NOT accidentally become a wildcard or another expression. Implementations
MAY instead enumerate and compare locally. An optimization MUST NOT change
the matching or ambiguity outcome.

Zero matches yields `not_found`; exactly one complete match yields the
selected entity; multiple matches yields `ambiguous`. A resolver MUST inspect
all necessary continuation pages before claiming uniqueness. It MAY report
ambiguity after a second match without reading further pages. A request
limit, incomplete page chain or unstable collection MUST NOT be reported as
a unique selection. Resource selectors examine the effective metadata of
their default Versions as defined by Core, not only the reduced Resource
object in document view.

## Representations

Metadata and domain documents are distinct results, even when both are JSON.
`self`, `metaurl` and `defaultversionurl` locate metadata under the relevant
Core binding; they MUST NOT automatically be treated as raw-byte locations.

Native snapshot access uses Core
[document view](../../core/spec.md#doc-flag), with storage descriptors and
transport context outside the Core entity. This requires removal of duplicated
default-Version attributes, Version validation-result attributes and
`shortself`, and suppression of alias-target expansion. Links to entities
included in the returned document MUST use document-local JSON Pointers.
Links to entities not included MUST NOT be rewritten to nonexistent local
pointers. Reassembling records into a larger document requires rebasing
pointers to that document, not concatenating independently relative records.

Native bindings MUST distinguish these document-view serializations from
the logical operation that retrieves an alias's target document under Core.
An unsupported view or alias-Version document view MUST be reported, not
silently converted to a different view.

A binding offering API-view results MUST define actually retrievable
Core-conforming `self` and navigation URLs. An implementation-defined URI
with no retrieval contract is insufficient. An OPTIONAL HTTP facade MUST
conform separately to [Core HTTP](../../core/http.md). Neither `oci://`
locators nor UA NodeIds become Core XIDs.

Formats MUST preserve extension attributes and domain bytes. A zero-byte
document is present content and MUST NOT be replaced by `{}`, `null` or a
missing document. Binary documents MUST NOT pass through text conversion.

## Snapshots and Completeness

Every snapshot MUST have a complete internal containment graph. A linked
snapshot MAY retain explicit external document references. An
offline-complete snapshot MUST additionally contain the declared xRegistry
document content for its selected scope and the model material needed to
interpret it. The producer MUST identify that scope and completeness class.
Missing internally referenced data is an invalid package in either class.

Offline completeness does not mean copying all cataloged Registries or
discovering arbitrary links inside every domain document. External reference
bases and known content integrity descriptors MUST survive packaging.
Materializing external content requires preserving its actual bytes.

An immutable revision MUST remain pinned throughout an operation. A moving
tag, branch or mutable directory name is not a revision pin. A live HTTP or
UA endpoint without a snapshot guarantee MUST be reported as live, not as
an atomic snapshot. Revision identifiers MUST NOT be substituted for Resource
Version IDs.

Digests identify exact bytes, not semantic equality. Equivalent publications
can have different digests. New snapshots MAY reuse unchanged content and
subtrees, but MUST be readable without replaying older snapshots.

## Errors

These are abstract resolver outcomes, not additions to Core's error catalog
or mandates for new HTTP status codes:

| Outcome | Meaning |
| --- | --- |
| `unsupported_binding` | No selected supported access method. |
| `unsupported_version` | Unsupported Core, binding or package format version. |
| `unsupported_operation` | Unsupported view, parameter or read operation. |
| `not_found` | No selected entity, Version, root or label match. |
| `ambiguous` | More than one eligible result without disambiguation. |
| `policy_denied` | Access, credential, trust or traversal policy rejected the operation. |
| `integrity_error` | Size, digest or authenticated identity check failed. |
| `invalid_package` | Malformed advertisement, metadata or containment structure. |
| `inconsistent_snapshot` | Data cannot be read as the selected state. |
| `limit_exceeded` | A resource or traversal bound prevents completion. |
| `unavailable` | A transport or backing object is temporarily unavailable. |

An error MUST retain the underlying Core error or transport diagnostic when
available, without exposing credentials. An incomplete retrieval MUST NOT
produce a success-shaped empty collection. Core's dangling-alias exception
is preserved.

## Security Considerations

Catalog data and package contents are untrusted input. Discovery is not an
authorization grant. A resolver MUST apply caller policy before contacting
endpoints, following redirects, reading local paths or retrieving external
documents. Credentials MUST be scoped to the authenticated destination and
MUST NOT be forwarded merely because a catalog entry or redirect names it.

Resolvers MUST bound traversal depth, request count and aggregate bytes,
detect discovery/redirect cycles, and surface exhausted bounds. SHA-256
integrity does not authenticate a publisher. Signature and provenance
policies are separate from containment completeness. Git readers MUST NOT
execute repository content; filesystem readers MUST enforce containment
including symlinks and reparse points.

## Conformance

A **catalog producer** conforms to the Registry domain. Its base class does
not imply usable endpoints. A **resolvable entry** satisfies the domain's
stricter advertisement requirements.

A **federation resolver** MUST implement the selection, context, Core
semantics, representations and failures above and identify each implemented
binding. Conformance to one binding does not imply support for another.

A **snapshot producer** MUST identify its format, scope and linked or
offline-complete class and produce a complete internal graph. An OPTIONAL
API facade requires separate protocol-binding conformance.

The executable examples are offline conformance aids, not production
resolvers. [Shared vectors](samples/selection.json) distinguish identity,
selection and reference cases. Binding fixtures exercise transport-specific
retrieval. Tests MUST distinguish full graph validation from selective
lookup; a validator walking everything does not demonstrate efficient
selective resolution.

## Source Reconciliation

The preliminary WG and profile proposals supplied for this work are design
inputs, not normative dependencies. The following disposition applies:

| Input requirement | Destination or correction |
| --- | --- |
| WG: independent authorities and peer bindings | Overview, read operations and binding conformance. |
| WG: discovery without universal replication | Catalog discovery and explicit snapshot scope. |
| Catalog: `registrygroups` and localized mandatory labels | Replaced by the deployed `categories` hierarchy and ordinary OPTIONAL Core labels. |
| Catalog: endpoints, model descriptions and relationships | Additive Registry domain Version attributes. |
| Profiles: remote reference resolution | Explicit Registry context, not a widening of Core `xref`. |
| Profiles: selectors and common failures | Selectors and errors in this specification. |
| OCI: packaging and selective retrieval | Bounded standard descriptor graph in the OCI binding. |
| Git/File: independently shaped directories | One shared document-tree format with separate transport selection. |
| HTTP: transport retrieval | Existing Core HTTP API, with federation selection and consistency rules. |
| OPC UA: native access | Existing draft binding, with corrected addressing and serialization. |
| Synchronization, writes and inferred payload dependencies | Outside this read-only federation specification. |

## References

- [xRegistry Core](../../core/spec.md)
- [xRegistry Model](../../core/model.md)
- [xRegistry HTTP](../../core/http.md)
- [Registry of Registries](../models/registry/spec.md)
- [RFC3986: URI Syntax](https://www.rfc-editor.org/rfc/rfc3986)
- [RFC6901: JSON Pointer](https://www.rfc-editor.org/rfc/rfc6901)
