# Registry-of-Registries Examples

<!-- words: federationprofiles registrytypes weburl xregurl -->
<!-- words: namespace nsu opc opcua readme ua website -->
<!-- words: compatibilityvalidated formatvalidated -->
<!-- words: federationerror publicschemas py -->

These examples show the [authoritative domain model](../model.json) as full
Core 1.0-rc4 document views. Each document inlines all of its Categories,
Resources, Meta entities and catalog-description Versions, with explicit IDs,
XIDs, collection counts, default-Version references and document-local JSON
Pointers. Description attributes appear on Versions rather than as duplicate
default-Version fields on Resources.

Core IDs follow the [Core grammar](../../../../core/spec.md#singularid-id-attribute):
they contain 1 to 128 ASCII characters. The first character is a letter,
digit or `_`. Remaining characters are limited to letters, digits, `_`, `.`,
`~`, `:`, `@` or `-`.
Sibling IDs are unique case-insensitively, while lookups preserve and
require exact case. Case-only duplicate siblings MUST NOT be used as valid
fixture data. A test of a storage mapping can place the IDs that would
collide as filenames in distinct parent or model-type scopes. The mapping
MUST preserve Core IDs and MUST NOT redefine them as raw filesystem names.

All navigation targets referenced by JSON Pointers in these full documents
are included in the same document. For a partial document view, Core
navigation URLs MUST become `#JSON-POINTER` references only when their
targets are included, and MUST otherwise retain their absolute API URLs.
Pointers use the current document's root and JSON Pointer escaping, not a
storage path or an assumed catalog-root pointer.
The checked full-document examples follow the
[domain document-view rules](../spec.md#33-document-view). They also follow
Core's [Multiple Document View](../../../../core/spec.md#multiple-document-view).
The linked domain section includes an abbreviated Category response that
shows both local pointers and absolute URLs for their omitted targets.

The document views omit `shortself`, Version `formatvalidated` and
`compatibilityvalidated`, and duplicated default-Version attributes on
Resources. Catalog XIDs and relationship targets retain catalog-root
scope. They are not converted to document-local pointers.

The examples omit the OPTIONAL inlined model and capabilities. Load the
sibling model to interpret them; they are not complete server configurations.
Their metadata-only Resources have no detached domain document. The sample
catalog's root `registryid` does not identify a described Registry.

The endpoints, commits and snapshot references have complete syntax but are
illustrative, not running services or packaged snapshots. Reading the
sample files does not require following those references, accessing an
external snapshot, publishing artifacts, or using credentials.
Docker Hub appears only as a familiar human-facing website
listing.

## Hub-Compatible Base Catalog

[hub-compatible.json](hub-compatible.json) uses only Core fields and the
`weburl` and `xregurl` attributes observed in the
[xRegistry Hub](https://hub.xregistry.io/xreg/). It adds no labels, registry
types, profiles, authority or relationships.

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

This document uses the Hub's domain vocabulary. It is not a live export,
and does not reproduce the
[expanded Hub model](https://hub.xregistry.io/xreg/model)'s non-Core `xref`
typing.

## Multiple Profiles and Description Versions

[multi-profile-catalog.json](multi-profile-catalog.json) contains
`/categories/public/registries/schemas`, with two description Versions.
Version `2` is the explicit, sticky default. Version `1` remains available.
A catalog-description `versionid` is not a Git commit, OCI root digest
or target schema's Version ID. The expected results below apply the
[domain selection procedure](../spec.md#62-advertisement-selection).

Version `2` advertises an unknown extension, then OCI, Git, HTTP, two File
layouts and OPC Unified Architecture (OPC UA). OCI and Git both have priority
`0`. HTTP omits `priority` and `parameters` to demonstrate the defaults
`0` and `{}`. Version `2` also supplies an `xregurl` equal to the explicit
HTTP endpoint, which adds an implicit priority-zero candidate. The OPC UA
advertisement uses `registryroot: "nsu=urn:example:xregistry;s=Registries/PublicSchemas"`.
The `nsu=` form identifies the namespace by URI rather than by a session
index. The Registry root, Application URI, and transport-profile URI are
separate inputs. See [OPC UA advertisement selection](../../../bindings/opcua.md#101-advertisement-and-registry-selection).

For a consumer supporting all five built-in bindings, with no additional
policy restriction, expected choices are:

| Caller choice | Selected advertisement |
| --- | --- |
| None | OCI at array index `1`. This consumer does not support the unknown extension. |
| `git` | Git at index `2`, despite OCI appearing first. |
| `http` | Explicit HTTP at index `3`, before the implicit candidate. |
| `file` | Document-tree File at index `4`, ahead of OCI-layout File. |
| `opcua` | OPC UA at index `6`. |
| Original index `5` | OCI-layout File. |

Indexes are zero-based, and refer to the original serialized array, not
an array after filtering. The unknown extension can only participate if a
consumer independently implements it. The sample does not define it.

For the same consumer, if policy denies OCI but permits Git and the caller
has not made a choice, Git at index `2` is selected. If the caller explicitly
selects index `1` under that policy, the result is `policy_denied`. A choice
of `oci` also yields `policy_denied` if policy denies every matching
supported candidate. A choice of the unknown extension yields
`unsupported_binding` if the consumer does not support it and has not
explicitly selected a denied advertisement. These policy cases illustrate
the selection rules; the offline helper does not evaluate access policy.

Version `1` has explicit HTTP priority `20`, OCI priority `10` and a matching
`xregurl`. The catalog rules give the appended implicit HTTP candidate
priority `0`, so that candidate wins unless the caller overrides the selection.
Removing it because an explicit HTTP advertisement exists would change the
result.

Version `1` also demonstrates empty `labels`, `registrytypes` and
`relationships`. Version `2` has descriptive domain/model URIs and an
administrative authority. None of these assertions establishes compatibility
or trust. Its empty `note` label is valid, and its `team` label matches
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
an empty map. A label key is not a language tag by definition.

## Behavior Inventory

The three documents contain five Categories, seven Resources, eight
catalog-description Versions, ten explicit advertisements and seven
relationships. Use them as conformance-check inputs. Acceptance by a derived
schema does not establish conformance.

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

The normative constraints also call for boundary checks beyond these examples:
empty names, invalid priorities, relative or credential-bearing endpoints,
and prohibited queries or fragments. Binding checks cover misplaced OCI tags,
missing or unknown parameters, abbreviated Git revisions, unsafe paths,
File layout/reference mismatches and persisted OPC UA namespace indexes.
Additional cases cover contradictory `xregurl` and unknown `binding` values that
differ from built-ins only by case. These checks do not instruct a caller to
fetch a sample endpoint.

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

Test whether selection reports incomplete pagination rather than claiming
uniqueness, distinguishes `unsupported_binding` from `policy_denied`,
never contacts an endpoint denied by policy, and does not retry another
binding after the selected advertisement fails. See
[Consistency and Failure](../spec.md#63-consistency-and-failure).
Catalog-schema validation alone cannot establish these operational properties.

## Shared Helper Interfaces

This domain introduces no separate helper API. The
[shared offline helpers](../../../federation/tools/federation_examples.py) provide
`validate_xid`, `validate_profile`, `select_profile`, `select_label`,
`resource_type`, `resolve_local_xref` and `select_version`.
Failures expose a `FederationError.code` and a message.

To select an advertisement in these document-view samples:

1. Set `description = select_version(resource, versionid=None)`.
2. Call `select_profile(description, supported, binding=None)`.
   The `binding` argument is keyword-only.

Profile attributes are not duplicated on the Resource. For a label lookup
over one Category, collect the selected description Version of each entry
first. `select_label(descriptions, "note", "")` returns the one matching
Version, reports `not_found` for no match, or reports `ambiguous` if more
than one Version matches.

`resource_type(modelsource, xid)` identifies the Resource model type using
Core [Resource definition reuse](../../../../core/model.md#reuse-of-resource-definitions).
`resolve_local_xref(registry, source_xid)` requires the Registry's
`modelsource`. These catalog samples omit that OPTIONAL inline field, so
callers supply the authoritative sibling model in their in-memory context.
The helper performs one-hop lookup, not document-view serialization.
Consumers remain responsible for preserving source identity.

The shared [selection vectors](../../../federation/tools/test_spec_examples.py)
exercise source ownership, default-Version selection and labels. They are
operation vectors, not additional full Registry-of-Registries documents.
The helpers do not copy snapshots or implement transports.

## Validation Boundaries

See [schema generation and limitations](../schemas/README.md).
Validate the model, Core document-view structure and the
[domain's semantic rules](../spec.md) separately. Acceptance by a generated
schema does not prove conformance, and generator omissions do not justify
removing mandatory Core fields from the documents.
