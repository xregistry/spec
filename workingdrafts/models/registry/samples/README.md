# Registry-of-Registries Examples

<!-- words: federationprofiles registrytypes weburl xregurl -->
<!-- words: namespace nsu opc opcua readme ua website -->
<!-- words: compatibilityvalidated formatvalidated -->
<!-- words: federationerror py -->

These are full Core 1.0-rc4 document views using the
[authoritative domain model](../model.json). Each document inlines every
Category, Resource, Meta entity and catalog-description Version it contains.
IDs, XIDs, collection counts, default-Version references and document-local
JSON Pointers are explicit. Description attributes occur on Versions, not
as duplicate default-Version fields on Resources.

IDs follow the [Core grammar](../../../../core/spec.md#singularid-id-attribute):
1 to 128 ASCII characters, starting with a letter, digit or `_`, then
using only letters, digits, `_`, `.`, `~`, `:`, `@` or `-`.
Sibling IDs are unique case-insensitively, while lookups preserve and
require exact case. Case-only duplicate siblings MUST NOT be used as valid
fixture data. Filesystem-collision examples can use distinct parent or
model-type scopes. They MUST NOT redefine Core IDs as raw filesystem names.

All navigation targets referenced by JSON Pointers in these full documents
are included in the same document. For a partial document view, Core
navigation URLs MUST become `#JSON-POINTER` references only when their
targets are included, and MUST otherwise retain their absolute API URLs.
Pointers use the current document's root and JSON Pointer escaping, not a
storage path or an assumed catalog-root pointer.

The document views omit `shortself`, Version `formatvalidated` and
`compatibilityvalidated`, and duplicated default-Version attributes on
Resources. Catalog XIDs and relationship targets retain catalog-root
scope. They are not converted to document-local pointers.

The examples omit the OPTIONAL inlined model and capabilities, rather
than claiming to capture a complete server configuration. Load the sibling
model when interpreting them. Metadata-only Resources have no detached
domain document. The sample catalog's root `registryid` is not the ID of a
described Registry.

Endpoints, commits and snapshot references are illustrative data, not
running services or packaged snapshots. Their syntax is complete. No
network access, filesystem read, artifact publication or credential is
needed to inspect these examples. The Docker Hub website is included only
as a familiar human-facing listing.

## Hub-Compatible Base Catalog

[hub-compatible.json](hub-compatible.json) uses only Core fields and the
two observed hub attributes. It adds no labels, registry types, profiles,
authority or relationships.

| Entry XID | Meaning |
| --- | --- |
| `/categories/oci/registries/docker-hub` | Website only. Base conformance. |
| `/categories/dev/registries/schema-bridge` | HTTP via `xregurl`. |
| `/categories/community/registries/directory` | No endpoint. Base conformance. |

The `community` Category demonstrates that Category IDs are not a closed
enumeration. The website-only and endpoint-free entries produce
`unsupported_binding` for resolution, not invalid catalog data.
The bridge contributes a priority-zero HTTP candidate without requiring
a `federationprofiles` attribute.

This document reproduces the hub's domain vocabulary, not an exact live
hub export or the expanded hub model's non-Core `xref` typing.

## Multiple Profiles and Description Versions

[multi-profile-catalog.json](multi-profile-catalog.json) contains
`/categories/public/registries/schemas`, with two description Versions.
Version `2` is the explicit, sticky default. Version `1` remains available.
Its `versionid` is not the Git commit, OCI root digest or a target schema's
Version ID.

Version `2` advertises an unknown extension followed by OCI, Git, HTTP,
two File layouts and OPC UA. OCI and Git have equal priority `0`.
HTTP omits both `priority` and `parameters`, demonstrating the defaults
`0` and `{}`. OPC UA uses `nsu=` and distinguishes the Registry root,
Application URI and transport-profile URI.

For a consumer supporting all five built-in bindings, with no additional
policy restriction, expected choices are:

| Caller choice | Selected advertisement |
| --- | --- |
| None | OCI at array index `1`. The unknown extension is not supported. |
| `git` | Git at index `2`, despite OCI appearing first. |
| `http` | Explicit HTTP at index `3`, before the implicit candidate. |
| `file` | Document-tree File at index `4`, ahead of OCI-layout File. |
| `opcua` | OPC UA at index `6`. |
| Original index `5` | OCI-layout File, if explicitly allowed by the caller. |

Indexes are zero-based, and refer to the original serialized array, not
an array after filtering. The unknown extension can only participate if a
consumer independently implements it. The sample does not define it.

Version `1` deliberately has explicit HTTP priority `20` and OCI priority
`10`, plus matching `xregurl`. Under the frozen catalog contract, the
appended implicit HTTP candidate retains priority `0` and wins absent a
caller override. Removing that candidate merely because explicit HTTP
exists changes the result. This is an important cross-specification
selection case, not an invitation to normalize or merge advertisements.

Version `1` also demonstrates empty `labels`, `registrytypes` and
`relationships`. Version `2` has descriptive domain/model URIs and an
administrative authority, neither of which establishes compatibility or
trust. Its empty `note` label is valid, and its `team` label matches
`platform` using Core case-insensitive string matching.

## Descriptive Relationships

[relationships-catalog.json](relationships-catalog.json) contains three
entries in `/categories/public/registries` and all five built-in
relationship types, plus an extension type.

`canonical` and `mirror` form a descriptive cycle. `aggregate` supersedes
a deliberately absent local `retired` entry and has an absolute link to an
entry in another catalog. These assertions do not cause automatic
traversal, synchronization, redirection, write-through or trust.
The website-only `aggregate` remains base-only despite its relationships.
Its explicit empty `federationprofiles` array adds no access method.

The `tier=public` label matches both `canonical` and `mirror` and is
ambiguous. `note=""` matches only `canonical`. A missing label does not
match an empty value. Relationship labels also include empty values and
an empty map without acquiring language-key semantics.

## Behavior Inventory

The three documents contain five Categories, seven Resources, eight
catalog-description Versions, ten explicit advertisements and seven
relationships. They provide the following starting points for conformance
checks without treating derived-schema acceptance as the authority.

| Area | Valid sample behavior |
| --- | --- |
| Base compatibility | No labels or new attributes in the hub-compatible file. |
| Optionality | Absent endpoints. Absent and empty maps and arrays. |
| Core serialization | Complete IDs, Meta, Version defaults and JSON Pointers. |
| ID uniqueness | No case-insensitive sibling collisions. Exact-case lookup. |
| Scope | Catalog IDs, entry IDs and binding revisions are separate. |
| Ordering | Default zero, equal-priority array order and caller choice. |
| HTTP via xregurl | Matching explicit endpoint plus independent priority-zero candidate. |
| Bindings | All five built-ins, both File layouts and unknown extension. |
| Revisions | OCI tag and digest. Full Git object ID, not a Version ID. |
| Labels | Case-insensitive values, empty value, absence and ambiguity. |
| Relationships | All built-ins, extension, local cycle and dangling target. |

Additional boundary checks follow directly from the normative constraints.
They reject empty names, invalid priorities, relative or credential-bearing
endpoints, and query or fragment violations. They cover misplaced OCI tags,
missing or unknown binding parameters, abbreviated Git revisions and unsafe
paths. They also cover File layout/reference mismatches, persisted OPC UA
namespace indexes, contradictory `xregurl`, and unknown profile names that
resemble built-ins only by case. None is an instruction to fetch a sample
endpoint.

Core boundary checks also need to reject case-only duplicate siblings and
out-of-grammar IDs, report not found for wrong-case lookups, and preserve
valid IDs across filesystem mappings. Partial-document checks need to
distinguish included navigation targets from non-included targets and
check JSON Pointer escaping.

The current samples contain no alias entries. Additional alias checks MUST
preserve source IDs and suppress target expansion in document view. Reading
an alias Resource in document view remains valid. Requesting document view
of its `versions` collection or a specific Version MUST produce Core
`cannot_doc_xref`, not transitive traversal. These requirements are
explicit in the [domain document-view rules](../spec.md#33-document-view).

Selection checks also need to cover incomplete pagination, no supported
binding, policy rejection and the prohibition on silent weaker fallback.
Catalog-schema validation alone cannot establish those operational
properties.

## Shared Helper Interfaces

This domain introduces no separate helper API. The
[shared offline helpers](../../../../tools/federation_examples.py) provide
`validate_xid`, `validate_profile`, `select_profile`, `select_label`,
`resource_type`, `resolve_local_xref` and `select_version`.
Failures expose a `FederationError.code` and a message.

For these document-view samples, first obtain the description with
`select_version(resource, versionid=None)`, then pass that Version to
`select_profile(entry, supported, name=None)`. The `name` argument is
keyword-only. Profile attributes are not duplicated on the Resource.
Collection label selection likewise uses the selected description Versions.

`resource_type(modelsource, xid)` identifies the Resource model type.
`resolve_local_xref(registry, source_xid)` requires the Registry's
`modelsource`. These catalog samples omit that OPTIONAL inline field, so
callers supply the authoritative sibling model in their in-memory context.
The helper performs one-hop lookup, not document-view serialization.
Consumers remain responsible for preserving source identity.

The shared [selection vectors](../../../federation/samples/selection.json)
exercise imported versus independent Resource model types, default-Version
selection, labels and local aliases. They are operation vectors, not
additional full Registry-of-Registries documents. Snapshot copying and
transport implementations are outside this catalog's helper surface.

## Validation Boundaries

See [schema generation and limitations](../schemas/README.md).
Validate the model, Core document-view structure and the
[domain's semantic rules](../spec.md) separately. A generated schema's
acceptance alone does not prove conformance. Equally, generator omissions
do not justify removing mandatory Core fields from these documents.
