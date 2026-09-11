# Registry-of-Registries Service - Version 1.0-rc1

<!-- words: applicationuri federationprofiles nodeid nsu opcua registryroot -->
<!-- words: registrytypes transportprofileuri weburl xregurl -->
<!-- words: categoryid curated docx mcp namespace nfc nodeset opc opcfoundation -->
<!-- words: opencontainers parametersreference publicschemas readme -->
<!-- words: registrygroups registryurl ssh ua uabinary uasc uatcp unversioned -->
<!-- words: website websites -->
<!-- words: compatibilityvalidated formatvalidated -->

## Abstract

This specification defines a Registry-of-Registries domain for xRegistry.
A catalog contains versioned descriptions of independently administered
Registries, human-facing websites and OPTIONAL federation advertisements.
Consumers can discover an entry without fetching or copying its contents.

**Status:** Unreleased working draft, Version 1.0-rc1. This specification uses
[xRegistry Core][Core] and the [Core model language][Model], Version
1.0-rc4. It is not part of a released xRegistry specification.

## Table of Contents

- [1. Overview](#1-overview)
  - [1.1. Scope](#11-scope)
- [2. Notations and Terminology](#2-notations-and-terminology)
- [3. Registry Model](#3-registry-model)
  - [3.1. Hierarchy](#31-hierarchy)
  - [3.2. Versions and References](#32-versions-and-references)
  - [3.3. Document View](#33-document-view)
- [4. Catalog Attributes](#4-catalog-attributes)
  - [4.1. `xregurl`](#41-xregurl)
  - [4.2. `weburl`](#42-weburl)
  - [4.3. `registrytypes`](#43-registrytypes)
  - [4.4. `authority`](#44-authority)
  - [4.5. `federationprofiles`](#45-federationprofiles)
  - [4.6. `relationships`](#46-relationships)
  - [4.7. Core Labels](#47-core-labels)
- [5. Federation Advertisements](#5-federation-advertisements)
  - [5.1. Common Fields](#51-common-fields)
  - [5.2. HTTP](#52-http)
  - [5.3. OCI](#53-oci)
  - [5.4. Git](#54-git)
  - [5.5. File](#55-file)
  - [5.6. OPC UA](#56-opc-ua)
  - [5.7. Extensions](#57-extensions)
- [6. Discovery and Selection](#6-discovery-and-selection)
  - [6.1. Entry Selection](#61-entry-selection)
  - [6.2. Advertisement Selection](#62-advertisement-selection)
  - [6.3. Consistency and Failure](#63-consistency-and-failure)
- [7. Descriptive Relationships](#7-descriptive-relationships)
- [8. Error Handling](#8-error-handling)
- [9. Security Considerations](#9-security-considerations)
- [10. Conformance](#10-conformance)
- [11. Examples and Derived Schemas](#11-examples-and-derived-schemas)
- [References](#references)

## 1. Overview

### 1.1. Scope

A Registry of Registries is itself an xRegistry Registry, called the
catalog. Its `category` Groups organize `registry` Resources. Each
Resource describes one Registry, or a website listed for
discovery. Its Versions record successive descriptions, not copies of the
described Registry.

The catalog MAY advertise HTTP, OCI, Git, File, OPC UA or extension
bindings. [Shared federation][Federation] defines the read operations and
Registry context established after selection. A catalog does not have to
implement those bindings, serve an HTTP facade for them, proxy their
contents or provide a materialized view.

This specification does not define replication, synchronization, automatic
dependency traversal, write-through, conflict resolution or credential
storage. It does not change domain document formats or require remote
Registries to adopt the catalog's model.

## 2. Notations and Terminology

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this
document are to be interpreted as described in [RFC 2119][RFC2119].

Core defines Registry, Group, Resource, Meta, Version, XID, API view and
document view. This specification uses these additional distinctions:

- **Catalog:** An xRegistry containing entries that describe independently
  administered Registries or discovery-only websites.
- **Category:** A Group organizing Registry entries in the catalog.
  A Category does not define a registry domain, transport
  or authority.
- **Catalog entry:** A `registry` Resource within a Category.
- **Catalog-description Version:** A Version of that entry's description.
- **Target Registry:** The independently administered Registry described
  by a Catalog entry. It has its own root, model, capabilities and ID scopes.
- **Advertisement:** An access method for the target Registry.
- **Registry context:** The selected logical Registry and access context
  within which a target XID is interpreted.
- **Revision pin:** A binding-specific immutable snapshot reference,
  distinct from both catalog and target Resource Version IDs.

The catalog root's `registryid`, an entry's `registryid` and the target
Registry root's `registryid` have different scopes. They need not match.
No URI, Category membership, label or equal XID across separate Registries
establishes global entity identity.

All attribute names introduced here are lowercase Core attribute names.
Profile identifiers and relationship types are string values, not new
Group or Resource type names.

## 3. Registry Model

The authoritative xRegistry extension model resides in [model.json](model.json).
It is a compact `modelsource`, not a second definition of Core metadata.
Core supplies entity IDs, navigation, labels, Version management and Meta
attributes. An implementation MUST apply this model together with Core and
the semantic constraints in this specification.

The model defines all six domain attributes in the Resource's `attributes`
map. They belong to catalog-description Versions. No domain attribute is
placed in Core's reserved `resourceattributes` map, and this revision adds
no `metaattributes`. Genuine Resource-wide extensions belong in
`metaattributes`, as defined by [the model language][Model attributes].

The following is illustrative pseudo JSON. Core attributes are omitted.
The `?` notation means OPTIONAL and `*` means zero or more occurrences.

```yaml
{
  "categories": {
    "<categoryid>": {
      "registries": {
        "<registryid>": {
          "versions": {
            "<versionid>": {
              "xregurl": "<URL>", ?
              "weburl": "<URL>", ?
              "registrytypes": [ "<STRING>" * ], ?
              "authority": "<URI>", ?
              "federationprofiles": [
                {
                  "name": "<STRING>",
                  "endpoint": "<URI>",
                  "priority": <UINTEGER>, ?
                  "parameters": { ... } ?
                } *
              ], ?
              "relationships": [
                {
                  "type": "<STRING>",
                  "target": "<URI>",
                  "labels": { "<STRING>": "<STRING>" * } ?
                } *
              ] ?
            } *
          }
        } *
      }
    } *
  }
}
```

### 3.1. Hierarchy

The Group singular name MUST be `category` and its collection name MUST
be `categories`. The Resource singular name MUST be `registry` and its
collection name MUST be `registries`. Canonical entry XIDs have the form:

```text
/categories/<categoryid>/registries/<registryid>
```

A catalog-description Version appends `/versions/<versionid>`. Its Meta
entity appends `/meta` to the entry XID. All identifiers MUST follow
[Core ID rules][Core IDs]. IDs MUST be unique case-insensitively within
their parent scope, but lookups MUST be case-sensitive. For example,
`Catalog` and `catalog` MUST NOT identify different siblings. A lookup
using the wrong case MUST be treated as not found, not normalized to an
existing ID.

IDs MUST contain 1 to 128 ASCII characters. The first character MUST be a
letter, digit or `_`. Subsequent characters MUST be letters, digits,
`_`, `.`, `~`, `:`, `@` or `-`. Core IDs are not raw filesystem names:
an ID such as `schema:main` is valid even on a platform that prohibits `:`
in a filename. Storage mappings MUST preserve the original IDs and their
scopes, without weakening this grammar or introducing case-only duplicate
siblings. Equal IDs in distinct parent or model-type scopes do not imply
identity.

Every catalog entry MUST belong to a Category. Category IDs are open-ended.
A producer MUST NOT assume that a Category ID selects a protocol, grants
trust or proves a target model. Empty Categories are valid. A catalog MAY
host other Group types in addition to this domain.

Registry Resources MUST have `hasdocument: false`. Their metadata is their
document. This domain does not define a separate `registry` document,
`registrybase64` content or `registryurl` document locator. `xregurl` is a
distinct domain attribute, not a renamed Core document locator.

### 3.2. Versions and References

Each non-alias entry MUST have at least one catalog-description Version.
Core determines its default Version through `meta.defaultversionid`. A
consumer MUST NOT select a description by sorting Version IDs, endpoint
tags or timestamps instead.

Changing an endpoint, authority, type assertion or relationship changes
description data. Core permits updating a Version or creating another
Version. This domain does not mandate immutable descriptions or a target
snapshot for every catalog Version. A consumer that needs a stable
snapshot MUST use the selected binding's revision rules.

The following values MUST NOT be substituted for one another:

- The `versionid` of a catalog description.
- The `versionid` of a Resource in the target Registry.
- A Git commit or an OCI snapshot digest.
- The `modelversion` of a Group or Resource model.

An entry MAY use Core `meta.xref` to alias another same-typed Resource in
the same catalog. Core's one-hop processing, source-relative identity,
document-view serialization and dangling-reference behavior MUST remain
unchanged. An absolute endpoint MUST NOT be placed in `meta.xref`.
Consumers MUST NOT transitively follow a target Resource's own `xref`.
Following an advertisement establishes a separate Registry context. It
does not convert a remote document or remote Resource into a Core alias.

### 3.3. Document View

Document-view serialization MUST follow the [Core `doc` flag][Core doc].
In particular, it MUST:

- Suppress inherited default-Version attributes on Resources.
- Suppress `formatvalidated` and `compatibilityvalidated` on Versions.
- Suppress `shortself` on every entity.
- Exclude alias-target attributes from the source Resource and its Meta
  entity, even if the target is separately included elsewhere in the
  document. The source retains its own identity and Core `xref`.
- Serialize Resources and Versions as xRegistry metadata, not as separate
  domain document bytes.

The Core navigation attributes `self`, `<COLLECTION>url`, `metaurl` and
`defaultversionurl` MUST become `#JSON-POINTER` references if, and only if,
the referenced entity or collection is included in the serialized output.
The pointer MUST locate it within the current response document, with
JSON Pointer escaping, and MUST NOT include a protocol suffix such as
`$details`. It is not necessarily relative to the catalog Registry root.
If the referenced entity or collection is not included, the applicable
absolute Core API URL MUST be retained rather than inventing a pointer to
absent data.

This conversion MUST NOT rewrite `xid`, `meta.xref` or catalog-root
`relationships.target` values as document-local pointers. Their catalog
scope remains unchanged. A storage filename is not a replacement base.

A document-view request directed to an alias's `versions` collection or
one of its Versions MUST generate [Core `cannot_doc_xref`][Core alias doc],
not resolve the target or chase an alias chain. Reading the alias Resource
itself in document view remains valid and MUST preserve Core's
non-expanding serialization.

## 4. Catalog Attributes

Unless stated otherwise, the attributes in this section are OPTIONAL,
Version-specific, and can change between catalog-description Versions.
The normal Core extension rules apply to additional attributes permitted
by the model.

### 4.1. `xregurl`

- Type: URL.
- Description: The xRegistry *HTTP* API root of the described Registry.
- Constraints:
  - OPTIONAL.
  - MUST be an absolute HTTP or HTTPS Registry root URL without user
    information, a query or a fragment.
  - MUST NOT be interpreted as a catalog entry XID or a document URL.
  - When supplied with explicit `http` advertisements, at least one
    explicit endpoint MUST match it exactly, as specified in
    [advertisement selection](#62-advertisement-selection).
  - Its presence is not evidence that the target is reachable or supports
    the consumer's Core version.
- Examples:
  - `https://schemas.example.com/xregistry`

### 4.2. `weburl`

- Type: URL.
- Description: A human-facing website associated with the entry.
- Constraints:
  - OPTIONAL.
  - MUST be a URL, not an instruction to discover an API automatically.
  - A relative URL MUST be resolved against the catalog Registry root URL,
    treated as a directory. It MUST NOT be resolved against the entry's
    Version URL, an advertised endpoint or a document's storage path.
  - Without that external catalog URL context, a relative value MAY be
    retained and displayed as a reference, but MUST NOT be guessed.
  - MUST NOT contribute a federation candidate, even if its scheme is
    HTTP or HTTPS.
- Examples:
  - `https://hub.docker.com/`
  - `about/registries`

### 4.3. `registrytypes`

- Type: Array of strings.
- Description: URI identifiers of domain specifications or models that
  the target Registry claims to expose.
- Constraints:
  - OPTIONAL. An empty array makes no type assertion.
  - Each item MUST be a nonempty absolute URI identifying a domain or a
    model, rather than a display name such as `schema`.
  - No fixed set of domains is imposed. Multiple domain identifiers MAY
    be advertised for one target.
  - An identifier denotes only the specification or model it identifies.
    An unversioned URI MUST NOT imply a particular `modelversion`.
  - To identify a particular revision, producers SHOULD use a URI that
    identifies that revision explicitly. Consumers MUST inspect the target
    model for its actual version and compatibility claims.
  - Array order and duplicate identifiers MUST NOT affect binding
    selection. The list is not a target capability response or proof of
    model compatibility.
- Examples:
  - `https://xregistry.io/xreg/domains/schema/specs/model.json`
  - `https://models.example.com/events/1.0/model.json`

### 4.4. `authority`

- Type: URI.
- Description: An identifier for the target Registry's administrative
  authority, such as an organization responsible for its contents.
- Constraints:
  - OPTIONAL.
  - MUST identify an administrative party, not convey credentials.
  - An absolute URI is RECOMMENDED. A relative URI uses the catalog-root
    base and unavailable-base rules defined for `weburl`.
  - MUST NOT be treated as authentication, authorization, a certificate,
    a trust anchor or proof that the named party endorsed the entry.
  - A shared value MUST NOT establish that two Registries are identical.
- Examples:
  - `urn:example:organization:platform-team`
  - `https://example.com/organizations/platform`

### 4.5. `federationprofiles`

- Type: Array of objects.
- Description: Ordered advertisements of access methods for the claimed
  logical target Registry.
- Constraints:
  - OPTIONAL. An empty array advertises no explicit access methods.
  - Each object MUST satisfy [Section 5](#5-federation-advertisements).
  - Multiple advertisements MAY use the same profile name or endpoint.
  - Producers MUST preserve array order. It determines preference when
    priorities are equal.
  - Multiple advertisements assert access to the same logical Registry,
    but MUST NOT be taken as a guarantee of identical instantaneous
    snapshots or interchangeable revision identifiers.
- Examples:
  - The advertisements in
    [multi-profile-catalog.json](samples/multi-profile-catalog.json).

### 4.6. `relationships`

- Type: Array of objects.
- Description: Typed, descriptive links from this entry to catalog entries.
- Constraints:
  - OPTIONAL. An empty array asserts no relationships.
  - Each object MUST satisfy [Section 7](#7-descriptive-relationships).
  - Relationship order MUST NOT control profile preference.
  - Relationships MUST NOT imply synchronization, automatic traversal,
    write propagation or trust.
- Examples:
  - The relationships in
    [relationships-catalog.json](samples/relationships-catalog.json).

### 4.7. Core Labels

Labels retain their [Core definition][Core labels]. They are OPTIONAL maps
of ordinary key/value strings, not mandatory localized names. An absent
map, an empty map and an empty string value are valid. Keys MUST follow
Core map-key rules. This specification assigns no language-tag meaning.

Version labels describe that catalog-description Version. Meta labels
remain Resource-wide Core metadata and MUST NOT silently replace Version
labels during selection. An application MAY use language-like keys by
agreement without changing Core comparison rules.

## 5. Federation Advertisements

### 5.1. Common Fields

An advertisement contains `name`, `endpoint`, OPTIONAL `priority` and
OPTIONAL `parameters`. The object MUST NOT contain other fields.
Parameter names MUST follow the model's Core attribute-name rules.
Profile-specific extensions belong inside `parameters`.

#### 5.1.1. `name`

- Type: String.
- Description: The binding discriminator.
- Constraints:
  - REQUIRED and MUST be nonempty.
  - MUST be compared case-sensitively, without normalization.
  - This revision defines `http`, `oci`, `git`, `file` and `opcua`.
    Other strings remain valid catalog data.
  - An unknown name MUST NOT be executed as a known binding. For example,
    `HTTP` is not an alias for `http`.
- Examples:
  - `http`
  - `com.example.discovery`

#### 5.1.2. `endpoint`

- Type: URI.
- Description: The serving location interpreted by the selected binding.
- Constraints:
  - REQUIRED.
  - MUST be an absolute URI satisfying the named binding's endpoint rules.
  - MUST NOT contain user information or embedded credentials.
  - MUST NOT be interpreted as a global entity identifier or an XID.
  - A snapshot selector belongs in the binding parameters when so defined.
    Consumers MUST NOT infer one from an unrelated URL component.
- Examples:
  - `https://schemas.example.com/xregistry`
  - `oci://artifacts.example.com/team/schemas`

#### 5.1.3. `priority`

- Type: Unsigned integer.
- Description: The producer's preference among advertisements.
- Constraints:
  - OPTIONAL. Absence MUST be interpreted as `0`.
  - MUST be an integer greater than or equal to zero, not a string,
    fractional number or boolean.
  - Lower values MUST sort before higher values after caller selection
    and policy are applied. Equal values retain original array order.
  - The absence rule is a selection default, not a Core model `default`
    that mandates serialization of this attribute.
- Examples:
  - `0`
  - `20`

#### 5.1.4. `parameters`

- Type: Object.
- Description: Binding-specific access and revision parameters.
- Constraints:
  - OPTIONAL. Absence MUST be interpreted as an empty object.
  - Built-in profiles MUST supply the parameters marked REQUIRED below.
  - Unknown parameters MAY be retained in catalog metadata. If a built-in
    profile containing an unknown parameter is selected, the resolver MUST
    report `unsupported_operation` before accessing the endpoint.
  - Credentials, bearer tokens, passwords and private keys MUST NOT be
    included. Authentication configuration is external to the catalog.
  - The empty-object default is a processing rule, not a non-scalar Core
    model default.
- Examples:
  - `{}`
  - `{"reference": "stable"}`

### 5.2. HTTP

The profile name is `http`. Its endpoint MUST be an absolute HTTP or HTTPS
URL of the target Registry root, with no query or fragment. It MUST NOT
point to a Group, Resource, Version, website or domain document in place of
that root. This revision defines no HTTP parameters. `parameters`, if
present in a supported advertisement, MUST be empty.

The target uses the [Core HTTP binding][HTTP]. A resolver still needs to
retrieve its model and capabilities and check Core version support.
An endpoint's URL scheme alone is not sufficient evidence of that support.

```json
{
  "name": "http",
  "endpoint": "https://schemas.example.com/xregistry"
}
```

### 5.3. OCI

The profile name is `oci`. Its endpoint MUST have the form
`oci://host/repository`, naming an OCI Distribution repository. A port MAY
be included in the authority. The endpoint MUST NOT embed a tag, digest,
query or fragment. The `oci` scheme here is this draft's binding locator,
not a claim that Core defines a new HTTP endpoint.

#### 5.3.1. `parameters.reference`

- Type: String.
- Description: The tag or SHA-256 digest selecting a Registry snapshot root.
- Constraints:
  - REQUIRED.
  - MUST be an OCI tag or `sha256:` followed by 64 lowercase hexadecimal
    digits, using [OCI Distribution][OCI Distribution] reference syntax.
  - A tag MUST contain 1 to 128 ASCII characters. Its first character
    MUST be alphanumeric or `_`. Subsequent characters MUST be
    alphanumeric, `_`, `.` or `-`.
  - A tag is mutable. A resolver MUST pin the resolved root digest for
    the operation. The digest identifies exact published bytes.
  - MUST NOT replace a target XID or target Resource `versionid`.
- Examples:
  - `stable`
  - The digest-pinned advertisement in
    [multi-profile-catalog.json](samples/multi-profile-catalog.json).

Native OCI access does not require an xRegistry HTTP facade. Packaging,
graph completeness and content verification belong to the OCI federation
binding, not to the catalog. The [OCI image specification][OCI Image] alone
does not establish conformance to that binding.

### 5.4. Git

The profile name is `git`. Its endpoint MUST be an absolute HTTPS
repository URL without a query or fragment. It MUST NOT be a hosting
website's file-view URL. This revision does not advertise shell commands,
SSH credentials or arbitrary repository execution.

#### 5.4.1. `parameters.revision`

- Type: String.
- Description: The input revision from which the Registry snapshot is read.
- Constraints:
  - REQUIRED.
  - MUST be a complete `refs/...` reference satisfying Git reference-name
    rules, or a complete 40-digit SHA-1 or 64-digit SHA-256 hexadecimal
    object ID.
  - Abbreviated object IDs, unqualified branch names such as `main`,
    `HEAD` and revision expressions MUST NOT be used.
  - A reference or tag MUST be resolved to one commit before traversal.
    The commit MUST remain pinned for the complete operation.
  - A Git object ID MUST NOT be substituted for an OCI content digest or
    an xRegistry Version ID.
- Examples:
  - `refs/heads/main`
  - `refs/tags/catalog-2026-09`

#### 5.4.2. `parameters.path`

- Type: String.
- Description: The directory containing the Registry document-tree root
  within the selected commit.
- Constraints:
  - OPTIONAL. Absence MUST select `xregistry`.
  - The empty string MUST select the repository root.
  - A nonempty value MUST be a portable relative directory path using `/`
    as its segment separator. It MUST NOT contain an empty, `.` or `..`
    segment, a backslash, a drive prefix or an absolute-path prefix.
  - The selected path MUST remain within the repository tree. Consumers
    MUST NOT reinterpret it as an operating-system command or a URL.
- Examples:
  - `xregistry`
  - `catalogs/public`
  - `""`

Git and File document-tree access select the same logical document format
defined by the federation family. The repository path is not an XID and
does not remove Group or Resource type names from entity identities.

### 5.5. File

The profile name is `file`. Its endpoint MUST be an absolute
[file URI][File URI] identifying a directory, with no query or fragment.
Filesystem authority, containment and access policy remain the
responsibility of the selected binding and caller. A locator does not
grant permission to read a local or network path.

#### 5.5.1. `parameters.layout`

- Type: String.
- Description: The representation found at the selected directory root.
- Constraints:
  - REQUIRED.
  - MUST be exactly `document-tree` or `oci-layout`.
  - `document-tree` selects a directory with the shared Registry document
    tree. `oci-layout` selects an OCI image layout.
  - A consumer MUST NOT guess a layout by trying one interpretation after
    another fails.
- Examples:
  - `document-tree`
  - `oci-layout`

#### 5.5.2. `parameters.reference`

- Type: String.
- Description: The selected Registry snapshot root in an OCI image layout.
- Constraints:
  - REQUIRED when `layout` is `oci-layout`.
  - MUST be absent when `layout` is `document-tree`.
  - MUST use the tag or SHA-256 digest syntax defined for
    [OCI `reference`](#531-parametersreference).
  - The File and OCI bindings determine root selection within the layout.
    A layout containing multiple roots MUST NOT cause an arbitrary choice.
- Examples:
  - `stable`

```json
{
  "name": "file",
  "endpoint": "file:///C:/catalog-cache/schemas/",
  "parameters": {
    "layout": "document-tree"
  }
}
```

### 5.6. OPC UA

The profile name is `opcua`. Its endpoint MUST be a native OPC UA endpoint
URL, as defined by the [native binding][OPC UA]. It is a serving location,
not the Server Application URI or Namespace URI. The native binding
defines supported transport profiles and endpoint discovery.

#### 5.6.1. `parameters.registryroot`

- Type: String.
- Description: A portable NodeId string identifying the Registry root in
  the selected OPC UA Server.
- Constraints:
  - REQUIRED.
  - MUST use the OPC UA portable NodeId string representation.
  - A nonstandard namespace MUST be identified with `nsu=`, not a
    persisted `ns=` index. The resolver maps that Namespace URI to the
    selected Server's namespace table.
  - Standard namespace identifiers MAY omit the namespace component.
  - A Server table index or an Application URI MUST NOT be substituted
    for the endpoint or the Registry root.
- Examples:
  - `nsu=urn:example:xregistry;s=Registries/PublicSchemas`

#### 5.6.2. `parameters.applicationuri`

- Type: URI.
- Description: The expected identity of the Server application.
- Constraints:
  - OPTIONAL.
  - MUST be an absolute Application URI, not an endpoint URL inferred
    from its spelling.
  - When present, the selected Server application MUST match this
    identity under the native binding's verification rules.
  - This assertion MUST NOT replace certificate and trust verification.
- Examples:
  - `urn:example:ua:catalog-server`

#### 5.6.3. `parameters.transportprofileuri`

- Type: URI.
- Description: The requested OPC UA transport profile.
- Constraints:
  - OPTIONAL.
  - MUST be an absolute transport-profile URI recognized by the consumer.
  - An unsupported requested profile MUST produce `unsupported_operation`.
    It MUST NOT be silently dropped to select a weaker transport.
- Examples:
  - `http://opcfoundation.org/UA-Profile/Transport/uatcp-uasc-uabinary`

The native binding's companion model is a proposal, not an adopted OPC
Foundation xRegistry standard. This domain does not define a Cloud Library
bridge, NodeSet export domain or additional OPC UA Services.

### 5.7. Extensions

Profile names are extensible. The model's `enum` is advisory rather than
closed. An extension SHOULD use a collision-resistant name under its
publisher's control and document its endpoint, parameters, version rules,
security properties and conformance requirements.

Unknown profiles remain valid catalog descriptions when their common
fields are valid. A consumer that does not implement their semantics MUST
exclude them from supported resolution candidates. It MUST NOT infer a
known binding from their endpoints. Parameters in an extension profile are
owned by that extension. Their names do not activate built-in semantics.

## 6. Discovery and Selection

### 6.1. Entry Selection

A consumer MUST select the containing catalog, Category and catalog entry
before interpreting advertisements. XIDs are resolved within that catalog
only. When selecting by a label, the consumer MUST name the collection and
use [Core string matching][Core filter] and the
[shared selector rules][Selectors].

Label values are literal strings, including the empty string. An absent
label does not match. String matching is case-insensitive under Core. This
domain MUST NOT impose NFC normalization, language-key selection or a
case-sensitive alternate default. A consumer MUST examine every necessary
page before claiming a unique match. Zero matches yield `not_found`.
Multiple matches yield `ambiguous`, not an arbitrary first entry.

The consumer MUST select an explicit catalog-description Version if the
caller supplied one. Otherwise it MUST use the Core default Version.
In document view, the consumer obtains that Version through the entry's
Meta entity and Versions collection. It MUST NOT merge advertisements
from different description Versions.

### 6.2. Advertisement Selection

Selection MUST use the following procedure:

1. Read the explicit `federationprofiles` array in its original order.
   An absent array is empty. Validate common advertisement fields and
   preserve unknown profile names as catalog data.
2. If `xregurl` is present, validate it as an HTTP root. If explicit
   `http` advertisements also exist, at least one endpoint MUST equal
   `xregurl` exactly. Otherwise the entry is contradictory and resolution
   MUST fail. Comparison here is exact string comparison, not URI
   normalization or a global identity rule.
3. A present `xregurl` contributes a implicit `http` candidate with that
   endpoint, priority `0` and empty parameters, ordered after the explicit
   advertisements. Its selection defaults MUST NOT be inherited from a
   different explicit candidate.
4. Apply the caller's explicit advertisement choice, including a selected
   profile name or original array position, and the caller's access
   policy. The producer's priority MUST NOT override that choice.
5. Exclude profile names the consumer does not support. If no supported
   candidate remains, report `unsupported_binding`. If policy rejects
   the selection, report `policy_denied`.
6. Order eligible candidates by ascending priority, treating an absent
   value as `0`. Preserve original array order for equal priorities,
   including the appended implicit candidate.
7. Select the first candidate. Validate its binding parameters, establish
   the target Registry context and perform the shared federation
   operation. Unknown parameters of a selected built-in profile produce
   `unsupported_operation`, not a retry with those parameters removed.

Repeated advertisements are permitted. Exact duplicates do not create
ambiguous Registry selection: the first equally ranked candidate wins.
Candidates with the same endpoint but different parameters or priorities
MUST retain those distinctions. In particular, a matching explicit HTTP
advertisement does not change the implicit candidate's zero priority.
Map iteration order MUST NOT be used to rank advertisements.

### 6.3. Consistency and Failure

Advertisements of one entry assert a common logical target, not identical
contents at every instant. A consumer MUST record the chosen catalog entry,
description Version, advertisement and binding revision separately from
target entity IDs. It MUST NOT equate two target snapshots solely because
their endpoint URLs, labels or `registryid` values match.

A consumer MUST check the target's model, Core version and applicable
capabilities rather than relying on `registrytypes` or successful endpoint
connection. If advertisements demonstrably identify different logical
Registries, the consumer MUST report an inconsistent selection rather
than merge them silently.

An integrity error, policy rejection, unsupported version, ambiguous
selection or inconsistent snapshot MUST NOT trigger silent fallback to a
different candidate. A caller MAY initiate a new operation with an explicit
alternative after inspecting the failure. This specification does not
authorize automatic retries through weaker trust or integrity mechanisms.

## 7. Descriptive Relationships

A relationship contains REQUIRED `type` and `target` fields and OPTIONAL
Core `labels`. No other fields are defined in the relationship object.

### 7.1. `type`

- Type: String.
- Description: The asserted relationship from this entry to the target.
- Constraints:
  - REQUIRED and MUST be nonempty.
  - Defined values MUST be recognized case-sensitively. Other values
    remain valid extensions and MUST NOT acquire a built-in meaning.
  - The following built-in meanings are descriptive assertions, not
    resolution or synchronization instructions.
- Examples:
  - `derived-from`
  - `com.example.curated-with`

| Value | Meaning |
| --- | --- |
| `depends-on` | Source contents can refer to target contents. |
| `derived-from` | The target is asserted to be a source of provenance. |
| `supersedes` | The source is the publisher's suggested replacement. |
| `mirrors` | The source is asserted to be a copy of target contents. |
| `federates-with` | Source and target are intended for a consuming view. |

`mirrors` MUST NOT be treated as proof of matching bytes, revision,
completeness or freshness. `supersedes` MUST NOT automatically redirect
selection, and `depends-on` does not enumerate all transitive dependencies.

### 7.2. `target`

- Type: URI.
- Description: The catalog entry about which the relationship is asserted.
- Constraints:
  - REQUIRED.
  - A leading `/` MUST denote a catalog-root Resource XID of the form
    `/categories/<categoryid>/registries/<registryid>`. It MUST NOT be a
    network-path reference beginning `//`.
  - An absolute URI MUST identify a catalog entry in another catalog,
    not merely a target Registry's serving endpoint.
  - Other relative references, including `../`, bare IDs and document
    fragments, MUST NOT be used.
  - The local base remains the containing catalog Registry, even when
    the relationship is read from a stand-alone Version document.
  - The target need not be available or present in the serialized
    document. A dangling descriptive link is valid catalog data.
- Examples:
  - `/categories/public/registries/canonical`
  - `https://catalog.example.net/categories/shared/registries/events`

### 7.3. `labels`

- Type: Map of strings to strings.
- Description: Ordinary Core labels describing this relationship.
- Constraints:
  - OPTIONAL and MAY be empty.
  - Keys and values MUST follow [Core label rules][Core labels],
    including permitting an empty string value.
  - MUST NOT select an endpoint, imply a language-key comparison rule or
    establish trust.
- Examples:
  - `{"purpose": "discovery", "note": ""}`

Relationships MAY contain cycles and duplicate assertions. Consumers MUST
NOT traverse them automatically as part of ordinary entry selection.
An application explicitly traversing them MUST apply access policy,
cycle detection and finite depth and size limits, and MUST report limits
rather than presenting truncated results as complete.

## 8. Error Handling

Catalog writers and servers MUST apply Core model, attribute and entity
errors. For example, a value that violates an attribute constraint
generates Core `invalid_attribute`. A field not permitted by the model
generates `unknown_attribute`. This domain does not add Core error codes.

Resolution uses the [shared federation error vocabulary][Errors].
Malformed or contradictory catalog input encountered by an offline
resolver is `invalid_package`. Absence of a supported binding is
`unsupported_binding`. Unknown selected built-in parameters are
`unsupported_operation`. An unreadable selected endpoint is not a
successful empty Registry.

Normal dangling Core `xref` serialization is not a new federation error.
A dangling descriptive relationship also does not invalidate its source
entry. If a caller explicitly requests the missing target, that separate
operation reports `not_found`.

## 9. Security Considerations

A catalog is untrusted input unless independently authenticated. A URI,
`authority`, label or relationship is an assertion, not authorization.
Consumers MUST establish endpoint trust and credentials independently.
Producers MUST NOT store credentials in URLs, parameters, labels or other
catalog metadata.

Before resolving an advertisement or explicitly following a relationship,
consumers MUST apply policy to the selected scheme, destination and
operation. They MUST protect against requests to unintended local or
private services, filesystem escape, redirect loops and resource
exhaustion. Redirects MUST NOT cause credentials to be forwarded to an
unauthorized destination.

Names, descriptions, labels and websites MUST be treated as untrusted
display data. Consumers MUST NOT execute catalog strings, repository hooks
or commands derived from them. Merely displaying `weburl` does not
authorize fetching it.

Digest and commit pins establish particular published bytes or repository
objects, not publisher authorization. Consumers MUST validate integrity
and publisher trust separately, including native OPC UA application and
certificate checks. Catalog mutation, mutable tags and changing endpoints
can make previously observed descriptions stale.

## 10. Conformance

### 10.1. Base Catalog

A base catalog implementation MUST conform to Core 1.0-rc4, implement the
authoritative domain model and preserve this specification's hierarchy,
metadata-only Resources and Version semantics. It MUST accept conforming
entries without labels, `registrytypes`, `authority`, `relationships`,
`federationprofiles`, `xregurl` or `weburl`.

When a domain attribute is supplied, its types and semantic constraints
apply. Unknown profile names and relationship types MUST remain valid
catalog data if their common fields are valid. A base catalog is not
REQUIRED to implement any advertised transport or reachability check.

A base entry MAY describe only a website, or have no endpoint at all.
Failure to resolve such an entry MUST NOT retroactively invalidate its
base catalog conformance.

### 10.2. Federation-Resolvable Entry

A federation-resolvable entry MUST first be a conforming base entry. In
its selected description Version it MUST provide at least one valid
advertisement for a binding supported by the consumer, either explicitly
or through `xregurl`, with all parameters needed to identify the target.
Any xregurl/explicit HTTP consistency constraint MUST also hold.

This is relative to a consumer's supported bindings and policy. A
well-formed extension-only entry can be resolvable by an extension-aware
consumer and unsupported by another. Website-only data never satisfies
this class. No conformance claim guarantees current endpoint availability.

### 10.3. Catalog Consumer

A catalog consumer claiming resolution conformance MUST implement the
selection procedure, preserve origin and revision distinctions, and
conform to [shared federation][Federation] and each binding it claims to
support. It MUST report unsupported operations and failures explicitly.
It is not REQUIRED to implement every built-in binding.

Read-only federation consumption does not prohibit independent,
authorized catalog editing under Core. Such editing MUST NOT cause
write-through to a target Registry.

## 11. Examples and Derived Schemas

The [sample directory](samples/README.md) contains complete Core document
views with inlined Categories, Resources, Meta entities and Versions.
It includes unchanged base vocabulary, multiple access methods, distinct
description Versions and descriptive relationships.

The [schema directory](schemas/README.md) contains descriptions derived
from `model.json` using the repository's existing generator: JSON Schema,
JSON Structure, Avro and HTTP OpenAPI. The OpenAPI description concerns the
catalog's HTTP API, not the wire APIs of all advertised bindings.

The authoritative model is not duplicated in a hand-maintained full
Resource schema. Generation does not replace semantic validation:
nonempty identifiers, absolute credential-free endpoints, binding-specific
parameters, Core metadata completeness, URI bases, HTTP consistency and
deterministic selection need their stated checks. JSON object order cannot
encode advertisement preference.

Derived artifacts MUST NOT override Core or this specification when a
generator omits a constraint or produces an incompatible description.
Current limitations and reproduction commands are documented alongside the
generated files rather than changing the domain model to accommodate them.

## References

Normative dependencies for this working draft are the repository's Core
1.0-rc4 specifications and the companion unreleased federation contract.
External references below provide the named URI and transport syntax.
They do not imply that this domain is a published transport standard.

- [xRegistry Core 1.0-rc4][Core]
- [xRegistry Service Model 1.0-rc4][Model]
- [xRegistry HTTP Binding 1.0-rc4][HTTP]
- [xRegistry Federation working draft][Federation]
- [OPC UA native binding working draft][OPC UA]
- [RFC 2119][RFC2119]
- [RFC 3986][RFC3986]
- [RFC 8089: File URI Scheme][File URI]
- [OCI Image Specification 1.1.1][OCI Image]
- [OCI Distribution Specification 1.1.0][OCI Distribution]

The [hub root][Hub] and [observed hub model][Hub model] are informative
deployment evidence.

[Core]: ../../../core/spec.md
[Model]: ../../../core/model.md
[HTTP]: ../../../core/http.md
[Core IDs]: ../../../core/spec.md#singularid-id-attribute
[Core labels]: ../../../core/spec.md#labels-attribute
[Core xref]: ../../../core/spec.md#cross-referencing-resources
[Core doc]: ../../../core/spec.md#doc-flag
[Core alias doc]: ../../../core/spec.md#cannot_doc_xref
[Core filter]: ../../../core/spec.md#filter-flag
[Model attributes]: ../../../core/model.md#groupsstringresourcesstringattributes
[Federation]: ../../federation/spec.md
[Selectors]: ../../federation/spec.md#selectors
[Errors]: ../../federation/spec.md#errors
[OPC UA]: ../../bindings/opcua.md
[RFC2119]: https://www.rfc-editor.org/rfc/rfc2119
[RFC3986]: https://www.rfc-editor.org/rfc/rfc3986
[File URI]: https://www.rfc-editor.org/rfc/rfc8089
[OCI Image]: https://github.com/opencontainers/image-spec/tree/v1.1.1
[OCI Distribution]: https://github.com/opencontainers/distribution-spec/blob/v1.1.0/spec.md
[Hub]: https://hub.xregistry.io/xreg/
[Hub model]: https://hub.xregistry.io/xreg/model
