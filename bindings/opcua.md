# xRegistry OPC UA API - Version 1.0-rc3

<!-- words: xregistry addressspace browsename browsenames browsepath -->
<!-- words: browsepaths nodeid nodeids nodeclass typedefinition opc ua -->
<!-- words: filetransfer versionid versionids groupid resourceid registryid -->
<!-- words: xid xids epoch labels createdat modifiedat defaultversionid -->
<!-- words: specversion capabilitiesinfo contenttype mimetype resourceurl -->
<!-- words: hasdocument modelsource capabilitiesoffered statuscode -->
<!-- words: statuscodes attributestype propertytype foldertype filetype -->
<!-- words: registrytype grouptype resourcetype expandednodeid namespaceuri -->
<!-- words: accesslevel addattribute breaklock browsenameduplicated -->
<!-- words: browsenameinvalid browsenext bytestring communicationerror -->
<!-- words: continuationpointinvalid creategroup createresource -->
<!-- words: diagnosticinfo displayname encodinglimitsexceeded -->
<!-- words: enforcecompatibility exitlock expectedepoch externalreference -->
<!-- words: filehandle filternotallowed getorcreategroup getorcreateresource -->
<!-- words: getposition groupnodeid identitychangenotsupported indexrange -->
<!-- words: initlock invalidargument invalidstate lastmodifiedtime -->
<!-- words: lockingservicestype marcschier methodinvalid namespace -->
<!-- words: nodeidexists nodeidunknown nodeset notfound notreadable -->
<!-- words: notsupported notwritable opcfoundation opcua outofmemory -->
<!-- words: outofrange registrycapabilitiesdatatype removeattribute -->
<!-- words: renewlock requestfileopen resourcenodeid resourceunavailable -->
<!-- words: securitychecksfailed serveruri serveruriinvalid setposition -->
<!-- words: stickyversions toomanyoperations translatebrowsepathstonodeids -->
<!-- words: typedefinitions typemismatch useraccessdenied useraccesslevel -->
<!-- words: userwritable -->

## Abstract

This specification defines an OPC UA protocol binding for the xRegistry document
format and API [specification][xRegistry Core]. It is a peer of the
[HTTP binding][xRegistry HTTP]: a registry, its groups, resources, versions,
documents and attributes are discovered, read, created, updated, deleted,
exported and federated natively over OPC UA Services, rather than by tunnelling
HTTP over OPC UA.

## Table of Contents

- [Abstract](#abstract)
- [Table of Contents](#table-of-contents)
- [1. Scope](#1-scope)
- [2. Normative references](#2-normative-references)
- [3. Terms and conventions](#3-terms-and-conventions)
- [4. The OPC UA API access model](#4-the-opc-ua-api-access-model)
  - [4.1. AddressSpace root and service model](#41-addressspace-root-and-service-model)
  - [4.2. Resolving xRegistry `xid`s to OPC UA nodes](#42-resolving-xregistry-xids-to-opc-ua-nodes)
  - [4.3. Entity processing rules](#43-entity-processing-rules)
  - [4.4. OPC UA-specific attribute processing](#44-opc-ua-specific-attribute-processing)
  - [4.5. Method signatures and argument mapping](#45-method-signatures-and-argument-mapping)
    - [4.5.1. Concurrency and locking](#451-concurrency-and-locking)
  - [4.6. Attribute mapping](#46-attribute-mapping)
  - [4.7. Supported operations discovery and pagination](#47-supported-operations-discovery-and-pagination)
- [5. Registry operations](#5-registry-operations)
  - [5.1. Reading the registry](#51-reading-the-registry)
  - [5.2. Creating and updating the registry](#52-creating-and-updating-the-registry)
  - [5.3. Exporting the registry](#53-exporting-the-registry)
  - [5.4. Reading capabilities and model documents](#54-reading-capabilities-and-model-documents)
  - [5.5. Updating capabilities and model-source information](#55-updating-capabilities-and-model-source-information)
  - [5.6. Listing group collections](#56-listing-group-collections)
  - [5.7. Creating and updating groups](#57-creating-and-updating-groups)
  - [5.8. Reading a group](#58-reading-a-group)
  - [5.9. Deleting groups](#59-deleting-groups)
  - [5.10. Resource metadata and resource documents](#510-resource-metadata-and-resource-documents)
  - [5.11. Listing resource collections](#511-listing-resource-collections)
  - [5.12. Creating and updating resources](#512-creating-and-updating-resources)
  - [5.13. Reading a resource document](#513-reading-a-resource-document)
  - [5.14. Reading and updating resource metadata](#514-reading-and-updating-resource-metadata)
  - [5.15. Replacing a resource document](#515-replacing-a-resource-document)
  - [5.16. Deleting resources](#516-deleting-resources)
  - [5.17. Listing versions](#517-listing-versions)
  - [5.18. Creating and updating versions](#518-creating-and-updating-versions)
  - [5.19. Reading a version](#519-reading-a-version)
  - [5.20. Replacing a version document](#520-replacing-a-version-document)
  - [5.21. Deleting versions](#521-deleting-versions)
- [6. Request flags](#6-request-flags)
  - [6.1. Filtering](#61-filtering)
  - [6.2. Ignore processing](#62-ignore-processing)
  - [6.3. Inlining](#63-inlining)
  - [6.4. Sorting](#64-sorting)
  - [6.5. Document and metadata modes](#65-document-and-metadata-modes)
  - [6.6. Pagination and ranges](#66-pagination-and-ranges)
- [7. Value encoding](#7-value-encoding)
- [8. Serialization / export-import](#8-serialization--export-import)
- [9. Federation](#9-federation)
- [10. Error handling](#10-error-handling)
- [11. Conformance](#11-conformance)
- [Annex A — Correspondence to the xRegistry HTTP binding (informative)](#annex-a--correspondence-to-the-xregistry-http-binding-informative)

## 1. Scope

This specification defines the OPC UA API binding for
[xRegistry](https://github.com/xregistry/spec): how a registry, its groups,
resources, versions, documents and attributes are discovered, read, created,
updated and deleted natively over OPC UA Services while realizing the xRegistry
core model on the OPC UA AddressSpace and FileTransfer model of [*OPC UA —
xRegistry*](https://github.com/marcschier/opcua-drafts/blob/main/core-specs/xregistry/OPC-UA-xRegistry.md).

The abstract information model is defined by [*OPC UA —
xRegistry*](https://github.com/marcschier/opcua-drafts/blob/main/core-specs/xregistry/OPC-UA-xRegistry.md):
a registry is a `RegistryType` folder (subtype of `FolderType`), each group is
a `GroupType` folder (subtype of `FolderType`), and each resource or resource
version document is a `ResourceType` file (subtype of `FileType`). This API
specifies how clients interact with those nodes using Browse, BrowseNext, Read,
Write, Call, TranslateBrowsePathsToNodeIds and the FileTransfer Methods
inherited by `ResourceType`; deletion is an xRegistry `Delete(ExpectedEpoch)`
Method call on the `GroupType` or `ResourceType` entity being deleted.

> Annex A provides an informative correspondence for readers familiar with
> sibling protocol bindings, while §9 describes federation, including references
> to registries hosted behind other APIs.

This binding is independent of any domain registry. A concrete companion
specification subtypes `RegistryType`, `GroupType` and `ResourceType`,
constrains group and resource names, and MAY add domain Properties or Methods;
the OPC UA API patterns in this document remain the same.

## 2. Normative references

- [xRegistry Core specification, v1.0-rc3](https://github.com/xregistry/spec/blob/v1.0-rc3/core/spec.md) — the registry, group, resource, version, document, attribute, request-flag, operation-processing and error model.
- [xRegistry primer, v1.0-rc3](https://github.com/xregistry/spec/blob/v1.0-rc3/core/primer.md) — the xRegistry concepts, representations, request-shaping concepts and federation model.
- [OPC UA — xRegistry](https://github.com/marcschier/opcua-drafts/blob/main/core-specs/xregistry/OPC-UA-xRegistry.md) — the OPC UA companion information model used by this API.
- [OPC 10000-3](https://reference.opcfoundation.org/specs/OPC-10000-3/) — Address Space Model, including NodeIds, References, TypeDefinitions and `ExpandedNodeId`.
- [OPC 10000-4](https://reference.opcfoundation.org/specs/OPC-10000-4/) — Services, including Browse, BrowseNext, Read, Write, Call, TranslateBrowsePathsToNodeIds and StatusCodes.
- [OPC 10000-5](https://reference.opcfoundation.org/specs/OPC-10000-5/) — Base Information Model, including `FolderType` and `PropertyType`.
- [OPC 10000-20](https://reference.opcfoundation.org/specs/OPC-10000-20/) — File Transfer, including `FileType` and its `Open` / `Read` / `Write` / `Close` Methods.

## 3. Terms and conventions

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD",
"SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be
interpreted as described in [RFC 2119](https://tools.ietf.org/html/rfc2119).

The xRegistry terms registry, group, resource, version, document, attributes,
collection, `xid`, `self`, `epoch`, `labels`, model, capabilities, request
flags, representation and federation have the meanings defined by the xRegistry
core specification and primer. In this document, an `xid` is the xRegistry
relative identifier of an entity within a registry, for example
`/schemagroups/g1/schemas/s1`; it is not a protocol URL and is resolved against
the selected `RegistryType` root.

OPC UA type and member names follow OPC UA naming conventions and are written
exactly as defined by [*OPC UA —
xRegistry*](https://github.com/marcschier/opcua-drafts/blob/main/core-specs/xregistry/OPC-UA-xRegistry.md)
Annex A and the corresponding NodeSet: `RegistryType`, `GroupType`,
`ResourceType`, `AttributesType`, `RegistryCapabilitiesDataType`,
`RegistryId`, `SpecVersion`, `Capabilities`, `CapabilitiesInfo`, `Model`,
`GroupId`, `ResourceId`, `VersionId`, `Format`, `ContentType`,
`ExternalReference`, `ResourceUrl`, `Xid`, `Epoch`, `Name`, `Description`,
`Documentation`, `Labels`, `<Attribute>`, `CreatedAt`, `ModifiedAt`,
`CreateGroup`, `GetOrCreateGroup`, `CreateResource`, `GetOrCreateResource`,
`AddAttribute`, `RemoveAttribute`, `Delete` and `ExpectedEpoch`.

The OPC UA Services used by this API are Browse for collection enumeration,
BrowseNext for continuation points, Read for Properties and node metadata, Write
for writable Properties, Call for FileTransfer and xRegistry Methods including
`Delete`, TranslateBrowsePathsToNodeIds for path resolution, and the
FileTransfer Methods inherited from `FileType` by `ResourceType`.

In pseudo-signatures, FileTransfer Methods are shown by their BrowseNames rather
than by numeric NodeIds because a concrete server can expose them on domain
subtypes of `ResourceType`.

## 4. The OPC UA API access model

### 4.1. AddressSpace root and service model

An OPC UA xRegistry API is an AddressSpace subtree rooted at a selected
`RegistryType` domain subtype instance. Each registry root represents one
xRegistry registry; each `GroupType` child represents a group; each
`ResourceType` child represents a resource or resource version whose document
(raw bytes) are obtained through `FileType` Methods; and xRegistry labels and
extension attributes are represented by Property Variables under each entity's
`Labels` object of type `AttributesType`.

A server MAY expose more than one registry. A client selects the registry root
by NodeId, BrowsePath, discovery metadata or domain convention before applying
this API.

The selected registry root is the API authority for the operation sequence. No
URL authority is involved in the native OPC UA API; entity identity is carried
by xRegistry identifier Properties and `Xid`, while the OPC UA session,
endpoint and NodeIds identify where those entities are currently served.

The baseline operation model is: Browse a folder to enumerate a collection,
select entities from the Browse result by BrowseName, NodeClass, TypeDefinition
and target NodeId, Read Properties and the `Labels` container's `<Attribute>`
Property Variables to obtain attributes that are not already in the Browse
result, Write writable Properties to change fixed mutable attributes, Call
`Open` /`Read`/`Write`/`Close` to read or replace document bytes, Call
`CreateGroup`, `GetOrCreateGroup`, `CreateResource` or `GetOrCreateResource`
to create entities, Call the entity's `Delete(ExpectedEpoch)` Method to delete
it and everything it contains, and Call `Labels.AddAttribute` or
`Labels.RemoveAttribute` for supported labels and extension attributes.

If an xRegistry function is not supported for an otherwise supported
node, the server MUST return `Bad_NotSupported`, `Bad_UserAccessDenied`,
`Bad_NotWritable`, `Bad_MethodInvalid` or `Bad_InvalidArgument` as appropriate.
If the requested node or Property cannot be resolved, the server MUST return an
appropriate StatusCode such as `Bad_NodeIdUnknown`, `Bad_BrowseNameInvalid` or
`Bad_NotFound` where available.

### 4.2. Resolving xRegistry `xid`s to OPC UA nodes

The following table defines the native addressing model from xRegistry `xid` or
relative identifier forms to OPC UA targets. The left column is xRegistry
identity notation from the core model, not a protocol path; clients resolve it
by Browse, TranslateBrowsePathsToNodeIds, identifier-Property matching and model
metadata starting at the selected `RegistryType` root.

| xRegistry `xid` / relative identifier | OPC UA target | Primary OPC UA operation |
|---|---|---|
| `/` | selected `RegistryType` root node | Read registry Properties and Browse group children |
| `/capabilities` | `RegistryType.CapabilitiesInfo` Variable or `RegistryType.Capabilities` `FileType` component Object | Prefer Read of `CapabilitiesInfo` as a single `RegistryCapabilitiesDataType` Variant for fixed capability fields; use `Open`/`Read`/`Close` on `Capabilities` for raw JSON, including vendor or extension keys; when writable, `Open(write)`/`Write`/`Close` replaces the JSON document |
| `/capabilitiesoffered` | offered-capabilities structure exposed by the server, if any | Read a domain Property or an offered section inside the `Capabilities` JSON document |
| `/model` | `RegistryType.Model` `FileType` component Object | `Open`/`Read`/`Close` the JSON bytes; when writable as model source, `Open(write)`/`Write`/`Close` replaces the document |
| `/modelsource` | server-specific model-source Property or operation, if exposed | Read or Write the domain-defined model-source target, or reject as unsupported |
| `/export` | selected `RegistryType` subtree serialized as an xRegistry document | Browse and Read the subtree, or use a domain export Method or Property if advertised |
| `/<GROUPS>` | collection of `GroupType` children under the registry whose collection name is `<GROUPS>` | Browse and optionally `CreateGroup` or `GetOrCreateGroup` on the registry |
| `/<GROUPS>/<GID>` | `GroupType` child whose `GroupId` is `<GID>` | Read/Write Properties, Browse resources, or Call `Delete(ExpectedEpoch)` on the group |
| `/<GROUPS>/<GID>/<RESOURCES>` | collection of `ResourceType` children under the group whose collection name is `<RESOURCES>` | Browse and optionally `CreateResource` or `GetOrCreateResource` on the group |
| `/<GROUPS>/<GID>/<RESOURCES>/<RID>` | default `ResourceType` for `ResourceId = <RID>` | `Open`/`Read` document bytes or Read metadata Properties |
| `/<GROUPS>/<GID>/<RESOURCES>/<RID>$details` | same `ResourceType`, metadata view | Read/Write Properties and optionally `Labels.AddAttribute`/`Labels.RemoveAttribute` |
| `/<GROUPS>/<GID>/<RESOURCES>/<RID>/meta` | metadata Properties of the resource and default-version selection state | Read/Write Properties; domain extensions MAY add meta Properties |
| `/<GROUPS>/<GID>/<RESOURCES>/<RID>/versions` | set of `ResourceType` files with matching `ResourceId` and distinct `VersionId` | Browse associated version files |
| `/<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>` | `ResourceType` whose `ResourceId = <RID>` and `VersionId = <VID>` | `Open`/`Read` document bytes or Read metadata Properties |
| `/<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>$details` | same version file, metadata view | Read/Write Properties and optionally `Labels.AddAttribute`/`Labels.RemoveAttribute` |

The collection names `<GROUPS>` and `<RESOURCES>` are xRegistry model names, not
mandatory OPC UA base nodes. A domain registry MAY express collection names
through subtype BrowseNames, domain Properties, folders or model metadata, but
each concrete group instance MUST be a `GroupType` or subtype and each concrete
resource or version instance MUST be a `ResourceType` or subtype.

A server MUST set each group's, resource's and version's BrowseName to its
identifier: `groupid`, `resourceid` or `versionid`, respectively, and each
group's and resource's DisplayName to its `Name`. A `groupid` and a
`resourceid` are **symbolic identifiers** built from the entity's domain source
identity by the construction of [*OPC UA —
xRegistry*](https://github.com/marcschier/opcua-drafts/blob/main/core-specs/xregistry/OPC-UA-xRegistry.md)
§6.9, so they are readable, safe in a URL, on a command line and as a file name,
and never derived from a document. Because Browse results carry BrowseName,
DisplayName, NodeClass, TypeDefinition and the target NodeId, a client selects
and filters entities by identity and collection directly from the Browse result
with no Read per candidate, and renders a readable list without one either; only
filters on a dynamic label value or another attribute not present in the Browse
result require reading the entity's `Labels` container or Properties.

The xRegistry `self` value is not a mandatory OPC UA Property in the base model.
In this API it is derived from the selected registry root and the entity's `Xid`
; an OPC UA client can reconstruct a canonical self reference as a registry root
NodeId plus the relative `Xid`, or as an implementation-defined URL or URN for
display.

### 4.3. Entity processing rules

Reading a collection is Browse over the corresponding folder. Reading an entity
metadata view is Read of the entity Properties and, when labels are needed,
Browse/Read of the entity's `Labels` `AttributesType` container. Reading a
resource or version document is `Open` /`Read`/`Close` on the `ResourceType`
file.

Full replacement of an entity targets the entity node or the parent folder from
which the entity can be created. If the entity does not exist, the server
creates a `GroupType` folder or `ResourceType` file; if it exists, the server
updates it. Mutable Properties or `Labels` entries omitted from the replacement
representation MUST be deleted, reset to default or left unchanged only where
the xRegistry core rules or server-managed semantics require that behavior.

Partial update of an entity changes only explicitly named mutable attributes and
removes explicitly null attributes where removal is supported. It is realized by
Write of writable Properties and, where extension attributes or labels are
involved, by Call of
`Labels.AddAttribute(Key: String, Value: String, ExpectedEpoch: UInt32)` or
`Labels.RemoveAttribute(Key: String, ExpectedEpoch: UInt32)` on the entity's
`Labels` `AttributesType` object; success/failure is conveyed by the Method Call
StatusCode. Partial update MUST NOT patch arbitrary bytes inside a resource
document; document content changes use complete replacement of the document byte
stream.

Collection processing creates or updates one or more child entities under the
collection's parent folder. A client preferably creates or resolves groups with
`GetOrCreateGroup` on `RegistryType` and resources or versions with
`GetOrCreateResource` on `GroupType`; strict create operations use
`CreateGroup` and `CreateResource` when existence is an error. After creation or
resolution the client writes mandatory and mutable Properties, updates the
`Labels` container where supplied, and writes document bytes where supplied. A
server MUST apply the xRegistry atomicity rule: if one entity in a collection
operation cannot be processed, the server SHOULD reject the whole operation and
avoid partial effects; if the server cannot guarantee multi-node atomicity, it
MUST advertise that limitation in `Capabilities`.

Nested collection processing on an entity MUST process only nested collection
entries and MUST NOT modify the owning entity's own Properties. For example,
processing resources under a selected group creates or updates `ResourceType`
children without changing the group's own Properties.

Deleting an entity is performed by Calling its `Delete(ExpectedEpoch: UInt32)`
Method on the `GroupType` or `ResourceType` node to remove. The Method deletes
that entity and everything it contains: a group deletes its resources, and a
resource deletes its versions and `Labels`. Deleting a collection subset is a
sequence or server-defined batch of `Delete(ExpectedEpoch)` Calls over selected
children.

Unless otherwise stated, a request to update a read-only Property MUST be
ignored only if xRegistry says that read-only attribute updates are ignored;
otherwise the server MUST reject the Write with `Bad_NotWritable` or
`Bad_UserAccessDenied`. A request that supplies an identifier Property
(`RegistryId`, `GroupId`, `ResourceId` or `VersionId`) whose value conflicts
with the target entity MUST fail with `Bad_InvalidArgument` or
`Bad_IdentityChangeNotSupported`.

Any successful create or update MUST update `ModifiedAt` and increment `Epoch`
on the modified entity. Creation MUST initialize `CreatedAt`, `ModifiedAt`,
`Epoch`, `Xid` and the appropriate identifier Properties according to [*OPC UA
—
xRegistry*](https://github.com/marcschier/opcua-drafts/blob/main/core-specs/xregistry/OPC-UA-xRegistry.md)
§6.5 and the xRegistry core rules.

### 4.4. OPC UA-specific attribute processing

OPC UA carries fixed metadata as typed Property Values. Strings are OPC UA
`String`, timestamps are `DateTime`, `ExternalReference` is `ExpandedNodeId`,
and `Epoch` is `UInt32`; labels and extension attributes are `String` Property
Variables under the entity's `Labels` object of type `AttributesType`.

When a resource document is read as bytes, accompanying metadata is obtained
from the Browse result where available and by separate Read operations on the
same `ResourceType` Properties. A server MAY optimize this by exposing a domain
Method, but the interoperable baseline is separate `Open` /`Read`/`Close` plus
Browse and Read metadata.

The metadata view of a resource or version is represented by choosing Property
Reads or Writes instead of file content Reads or Writes. The target NodeId is
the same `ResourceType`; only the operation mode differs.

The xRegistry `contenttype` attribute maps to `ContentType`, not to `MimeType`
. `MimeType` is inherited from `FileType` and MAY mirror `ContentType` for
generic FileTransfer clients; when both are present, `ContentType` is the
xRegistry attribute and `MimeType` is the FileTransfer media hint.

### 4.5. Method signatures and argument mapping

The creation and mutation Method signatures used by this API are the
domain-named `CreateGroup`, `GetOrCreateGroup`, `CreateResource` and
`GetOrCreateResource` Methods defined by the xRegistry base model, the `Delete`
Method on `GroupType` and `ResourceType`, the `AddAttribute` and
`RemoveAttribute` Methods on `AttributesType`, and the inherited `Open` /
`Read` / `Write` / `Close` Methods of `ResourceType` whose exact argument
definitions are normative in OPC 10000-20.

| xRegistry action | OPC UA Method or Service | Argument mapping |
|---|---|---|
| Create group | `RegistryType.CreateGroup(GroupId) -> (GroupNodeId)` | `GroupId` is the groupid of the `GroupType` (or subtype) to create; the server creates the group folder and bootstraps its xRegistry attributes; fails if the group already exists |
| Get or create group | `RegistryType.GetOrCreateGroup(GroupId) -> (GroupNodeId, Created)` | `GroupId` is the groupid to resolve; the server returns the existing group with `Created = false` or creates, bootstraps and returns a new group with `Created = true` |
| Create resource or version | `GroupType.CreateResource(ResourceId, VersionId, RequestFileOpen) -> (ResourceNodeId, VersionId, FileHandle)` | A version is identified by `(ResourceId, VersionId)`; a new `ResourceId` creates the resource with its first version, an existing `ResourceId` with a new `VersionId` creates a new sibling version, and an empty `VersionId` lets the server assign the next versionid (returned as the output `VersionId`); `RequestFileOpen = true` returns a write `FileHandle` when document bytes follow; fails with `Bad_NodeIdExists` if that exact `(ResourceId, VersionId)` already exists |
| Get or create resource or version | `GroupType.GetOrCreateResource(ResourceId, VersionId, RequestFileOpen) -> (ResourceNodeId, VersionId, FileHandle, Created)` | resolves the `(ResourceId, VersionId)` version (empty `VersionId` selects or creates the default version); the server returns the existing file with `Created = false` or creates and returns a new one with `Created = true`; `RequestFileOpen = true` returns a write `FileHandle` |
| Delete group/resource/version | `Delete(ExpectedEpoch: UInt32)` on the selected `GroupType` or `ResourceType` | The target node is resolved from the xRegistry `xid` or identifier Properties; `ExpectedEpoch` can be omitted; `0` or omission disables the epoch check, and a non-zero value MUST equal the entity's current `Epoch` or the Call fails with `Bad_InvalidState` and deletes nothing; the Method returns no output arguments |
| Read document | `ResourceType.Open(mode)` -> `Read(fileHandle, length)` -> `Close(fileHandle)` | `mode` is read-only; `length` and repeated Reads are bounded by `Size` |
| Replace document | `ResourceType.Open(mode)` -> `SetPosition(fileHandle, 0)` -> `Write(fileHandle, data)` -> `Close(fileHandle)` | `mode` allows write; the complete replacement byte stream is written; server updates `ModifiedAt` and `Epoch` |
| Read metadata | Read Service on Properties | Property BrowseNames map to xRegistry attribute names by the tables in this document and the domain model |
| Replace scalar metadata | Write Service on Properties | Value DataTypes are those in Annex A of the base model |
| Add/update extension attribute or label | `Labels.AddAttribute(Key: String, Value: String, ExpectedEpoch: UInt32)` | `Labels` is the entity's `AttributesType` object; `Key` is the xRegistry attribute or label key, `Value` is the canonical string representation materialized as a `<Attribute>` Property Variable, and `ExpectedEpoch` provides the optimistic-concurrency check; success/failure is conveyed by the Method Call StatusCode |
| Remove extension attribute or label | `Labels.RemoveAttribute(Key: String, ExpectedEpoch: UInt32)` | `Labels` is the entity's `AttributesType` object; `Key` is the xRegistry attribute or label key and `ExpectedEpoch` provides the optimistic-concurrency check; success/failure is conveyed by the Method Call StatusCode |

The base model defines `CreateGroup` and `GetOrCreateGroup` on `RegistryType`,
`CreateResource` and `GetOrCreateResource` on `GroupType`, and `AttributesType`
with `AddAttribute` / `RemoveAttribute`; each registry, group or resource MAY
expose a `Labels` object of type `AttributesType`, and clients call those
Methods on that `Labels` object for label or extension-attribute updates. The
creation Methods are the base API create operations; move/copy is out of scope
for the base API and can be modeled by re-creating an entity and deleting the
original where permitted.

#### 4.5.1. Concurrency and locking

FileTransfer itself provides the baseline concurrency control:
`ResourceType.Open` opens a resource document for exclusive write, so a second
write-`Open` returns `Bad_NotWritable` and a read-`Open` returns
`Bad_NotReadable` while the file is open for writing. Optimistic concurrency is
based on the owning entity's `Epoch`.

For label or metadata mutation through `Labels.AddAttribute` and
`Labels.RemoveAttribute`, a client passes the entity's current `Epoch` as
`ExpectedEpoch`. If `ExpectedEpoch` is non-zero and does not equal the entity's
current `Epoch`, the Method MUST fail with `Bad_InvalidState` and make no
change; `ExpectedEpoch = 0` or an omitted argument disables the check.
On success the owning entity's `Epoch` increments.

For document replacement, exclusive `Open(write)` serializes writers. An
epoch-matched replacement sequence is: Read `Epoch`, call `Open(write)`,
re-Read `Epoch`, abort and `Close` if the value changed, otherwise `Write` the
complete replacement document and `Close`; the server increments `Epoch` on
successful `Close`.

For deletion, a client passes the current entity `Epoch` as the
`ExpectedEpoch` input to `Delete(ExpectedEpoch)`. If `ExpectedEpoch` is
non-zero and does not equal the entity's current `Epoch`, the Method Call MUST
fail with `Bad_InvalidState`, delete nothing and produce no partial effects;
`ExpectedEpoch = 0` or omission disables the check. Deletion is therefore an
atomic epoch-matched Method call rather than a read-then-delete sequence.

Beyond this, a server MAY optionally expose coarser-grained exclusive access
using the standard OPC UA locking mechanism — a `LockingServicesType` component
(`InitLock` / `RenewLock` / `ExitLock` / `BreakLock`, OPC 10000-5) — on the
registry root, a group or a resource, so that a client can hold an explicit
exclusive lock across a multi-step create/update sequence. This API does not
require locking; when it is absent, clients rely on FileTransfer `Open`
exclusivity and `Epoch` preconditions.

### 4.6. Attribute mapping

The base model Properties map to xRegistry attributes as follows.

| xRegistry attribute | OPC UA Property or Object | Applies to |
|---|---|---|
| `registryid` | `RegistryId` | `RegistryType` |
| `specversion` | `SpecVersion` | `RegistryType` |
| `capabilities` | preferred: `CapabilitiesInfo` Variable (`RegistryCapabilitiesDataType`) for fixed fields; alternative: `Capabilities` Object (`FileType`) whose content is the raw capabilities JSON | `RegistryType` |
| `model` | `Model` Object (`FileType`) whose content is the model JSON; no structured DataType is defined because the OPC UA AddressSpace type system is the structural equivalent | `RegistryType` |
| `<GROUP>id` | `GroupId` | `GroupType` |
| `<RESOURCE>id` | `ResourceId` | `ResourceType` |
| `versionid` | `VersionId` | `ResourceType` |
| `format` | `Format` | `ResourceType` |
| `contenttype` | `ContentType` | `ResourceType` |
| `<RESOURCE>url` | `ResourceUrl` | `ResourceType` |
| federation target | `ExternalReference` | `ResourceType` |
| `xid` | `Xid` | all base entity types |
| `epoch` | `Epoch` | all base entity types |
| `name` | `Name` | all base entity types |
| `description` | `Description` | all base entity types |
| `documentation` | `Documentation` | all base entity types |
| `labels` | `Labels` object (`AttributesType`) containing `<Attribute>` Property Variables | all base entity types |
| `createdat` | `CreatedAt` | all base entity types |
| `modifiedat` | `ModifiedAt` | all base entity types |

The xRegistry attributes `self`, collection `url` attributes, collection
`count` attributes, `metaurl`, `versionsurl`, `versionscount`,
`defaultversionurl`, `isdefault`, `ancestor`, `<RESOURCE>` and
`<RESOURCE>base64` are serialization artifacts or domain/model attributes rather
than mandatory base Properties. A server MAY expose them as domain Properties,
but a client MUST be able to derive them from `Xid`, `ResourceId`, `VersionId`
, Browse results and the document bytes where possible.

Labels and extension attributes are enumerated by Browsing the `Labels` object
and Reading each `<Attribute>` Property Variable. They are added or updated with
`Labels.AddAttribute`, removed with `Labels.RemoveAttribute`, and deleted
together with the owning group or resource when that entity's
`Delete(ExpectedEpoch)` Method succeeds.

### 4.7. Supported operations discovery and pagination

A client discovers supported operations by browsing the target node for Methods,
by reading `Writable`, `UserWritable`, AccessLevel and UserAccessLevel
attributes of Variables, by reading the typed `CapabilitiesInfo` Variable or the
`Capabilities` `FileType` content, and by inspecting executable and
user-executable bits of Method nodes.

A server MUST NOT require a side-effecting operation for discovery. If a
FileTransfer Method, `CreateGroup`, `GetOrCreateGroup`, `CreateResource`,
`GetOrCreateResource`, a `Labels` object, or `Labels.AddAttribute`
/`Labels.RemoveAttribute` is absent, non-executable or rejected with
`Bad_UserAccessDenied`, the corresponding xRegistry write capability is not
available to that client.

OPC UA Browse paginates large child sets through continuation points and
`BrowseNext`. A client that wants a page of collection entries calls Browse
with a requested maximum reference count and then calls `BrowseNext` until the
desired page is complete or no continuation point remains.

For file bytes, a client paginates through `Read(fileHandle, length)` and MAY
use `GetPosition` and `SetPosition` to implement random access. For labels, a
client browses the `Labels` object and pages with normal Browse continuation
points where needed.

## 5. Registry operations

This section defines successful native OPC UA interaction patterns for xRegistry
entities. Error mapping is specified in §10.

### 5.1. Reading the registry

A client reads the selected `RegistryType` root by Reading its Properties,
Reading the typed `CapabilitiesInfo` Variable when fixed capabilities
are requested, Browsing its `Labels` object where labels are requested,
Browsing its `Capabilities` and `Model` `FileType` component Objects when those
JSON documents are requested, and Browsing its group children. The standard base
Properties are `RegistryId`, `SpecVersion`, `CapabilitiesInfo`, `Xid`,
`Epoch`, `Name`, `Description`, `Documentation`, `CreatedAt` and
`ModifiedAt` where present; `Capabilities` and `Model` are `FileType`
component Objects, and `Labels` is an `AttributesType` Object.

A serialized registry representation derives collection URL and count attributes
from the registry model and Browse results rather than from mandatory OPC UA
nodes. Domain group subtypes and the `Model` JSON document determine how browsed
groups are grouped into xRegistry collections.

### 5.2. Creating and updating the registry

A registry-level full replacement writes the full replacement set of mutable
`RegistryType` Properties; omitted mutable attributes are removed or reset
according to xRegistry rules. `Capabilities` and `Model` are `FileType`
component Objects: absence MUST NOT require a change, while presence MUST be
written as a complete replacement document with `Open(write)` /`Write`/`Close`
unless the server supports finer-grained update semantics. When the raw
`Capabilities` JSON is changed, the server MUST keep `CapabilitiesInfo`
consistent for the fixed fields it exposes.

A registry-level partial update writes only included Properties and calls
`Labels.AddAttribute` or `Labels.RemoveAttribute` for included label or
extension-attribute changes. A null attribute is represented by writing a
server-defined null/default value if the DataType permits it, by calling
`Labels.RemoveAttribute` for a dynamic label or extension attribute, or by
failing with `Bad_NotSupported` if the attribute is mandatory or cannot be
removed.

The base `RegistryType` does not define `AddAttribute` or `RemoveAttribute`
directly; label and extension-attribute updates are made by calling those
Methods on the registry's `Labels` object of type `AttributesType`.

When a registry-level operation includes nested group collections, each group
entry is resolved by BrowseName. If absent, the server creates a `GroupType` or
domain subtype instance using `GetOrCreateGroup(GroupId)` or strict
`CreateGroup(GroupId)` on the registry root, initializes `GroupId`, `Xid`,
`Epoch`, `CreatedAt` and `ModifiedAt`, and applies the supplied group
Properties and nested resource collections.

When the requested operation is explicitly limited to group collection
processing, registry-level attributes MUST be rejected with
`Bad_InvalidArgument`, corresponding to xRegistry `groups_only`.

### 5.3. Exporting the registry

Export is serialization of the selected `RegistryType` subtree into the
xRegistry JSON document shape. The interoperable baseline export algorithm is
Browse the registry subtree, Read all mapped Properties, Open/Read/Close each
inlined `ResourceType` document, and serialize the result according to §8.

A server MAY expose an optimized domain Method or Property for export, but such
an optimization MUST produce the same document shape as the baseline algorithm.
Import is an implementation capability expressed as normal create/update
operations or by a domain-defined import Method.

### 5.4. Reading capabilities and model documents

A client reads registry capabilities either by Reading the typed
`RegistryType.CapabilitiesInfo` Variable or by calling `Open` for read on the
`RegistryType.Capabilities` `FileType` component Object, repeatedly calling
`Read` until the complete JSON byte stream is returned, and calling `Close`.
`CapabilitiesInfo` is the preferred read for fixed capability fields because it
returns a single `RegistryCapabilitiesDataType` Variant value and requires no
JSON parsing. The `Capabilities` `FileType` content is the raw xRegistry
capabilities JSON and remains the source for vendor or extension keys not
represented by `RegistryCapabilitiesDataType`.

`RegistryCapabilitiesDataType` contains `Flags: String[]`, `Mutable: String[]`
, `Pagination: Boolean`, `ShortSelf: Boolean`, `SpecVersions: String[]`,
`StickyVersions: Boolean`, `EnforceCompatibility: Boolean`, `Apis: String[]`
and `Schemas: String[]`. The base information model does not define a separate
`CapabilitiesOffered` Property. If a server supports mutable capabilities, it
MUST expose the offered-capabilities information either inside the
`Capabilities` JSON, as a domain subtype Property, or through domain
documentation referenced by `Model`. If no offered-capabilities target is
exposed, the operation MUST fail with `Bad_NodeIdUnknown` or `Bad_NotSupported`
rather than inventing an unmapped base node.

A client reads the registry model by calling `Open` for read on the
`RegistryType.Model` `FileType` component Object, repeatedly calling `Read`
until the complete JSON byte stream is returned, and calling `Close`. The
content is the full xRegistry model definition, and clients MAY use it to
resolve domain collection names to `GroupType` and `ResourceType` subtype
BrowseNames before browsing entities. `Model` remains FileType JSON only; no
structured DataType is defined for the model because the OPC UA AddressSpace
type system is the structural equivalent.

The base information model does not define a distinct `ModelSource` Property. If
a server distinguishes the effective model from the client-provided model
source, it MUST expose the model source as a domain subtype Property or inside
the `Model` JSON using a documented shape. If the model source has never been
set and a model-source target exists, the server MUST return an empty JSON
object (`{}`) as the model-source JSON content, matching xRegistry semantics.

### 5.5. Updating capabilities and model-source information

Capabilities updates use `Open(write)` /`Write`/`Close` on the
`RegistryType.Capabilities` `FileType` component Object if it is writable for
the current user. A full replacement writes the complete capabilities JSON byte
stream; a partial capabilities update writes only top-level capabilities if the
server supports patch-level semantics, otherwise the client MUST perform
read-modify-write and the server MAY reject partial writes with
`Bad_NotSupported`.

Unsupported capability changes MUST fail with `Bad_InvalidArgument` or
`Bad_NotSupported`, and no capability change MUST take effect before the
current Service operation completes.

Model-source updates use the domain-defined model-source target or another
domain-defined operation. The abstract base API does not define a writable
`ModelSource` node. If a server supports model-source updates via the
`RegistryType.Model` `FileType` component Object, it MUST document that `Model`
is serving as model source and MUST apply the xRegistry full-replacement rules
using `Open(write)` /`Write`/`Close`; if the server exposes only effective
`Model`, attempts to write model source MUST fail with `Bad_NotWritable` or
`Bad_NotSupported`.

### 5.6. Listing group collections

A client lists a group collection by Browse over the selected `RegistryType`
root to return `GroupType` children that belong to the requested group
collection. xRegistry group collections are unordered maps keyed by id; OPC UA
Browse returns children in a server-defined order, so a client MUST NOT infer
collection order from Browse position.

The client filters Browse results by NodeClass, TypeDefinition (`GroupType` or
subtype), collection metadata in the `Model` JSON document, domain subtype and
BrowseName. Because each group BrowseName is its `groupid`, the serialized
collection keys are obtained directly from BrowseName without reading `GroupId`
for every candidate.

### 5.7. Creating and updating groups

A client creates or updates groups as `GroupType` children under the registry
root. For each group key, the preferred one-shot path is
`GetOrCreateGroup(GroupId)` on the `RegistryType` root, which returns the
existing group with `Created = false` or creates it with `Created = true`;
strict create operations use `CreateGroup(GroupId)` when an existing group MUST
fail. It then writes group Properties and updates the group's `Labels` container
according to the requested processing mode: partial updates write only named
attributes, while full representations reset or remove omitted mutable
attributes according to xRegistry rules.

The response representation is obtained by reading back only the groups
processed, not the entire group collection.

If a group does not exist and the operation permits creation, the server creates
it with `GetOrCreateGroup` or strict `CreateGroup` on the registry root. The
supplied group identifier MUST match `GroupId`; a mismatch fails with
`Bad_InvalidArgument`.

Processing nested resource collections under a group creates or updates resource
collections under the specified group without modifying the group's own
Properties or `Labels` container. The request representation is a map from
resource collection names to resource maps; for each resource entry, the client
preferably calls `GetOrCreateResource`, writes the document if supplied, and
writes resource Properties or updates the resource's `Labels` container
according to the nested operation semantics; strict creation uses
`CreateResource`.

If an operation attempts to update group-level attributes while it is explicitly
limited to nested resource collection processing, the server MUST reject it with
`Bad_InvalidArgument`, corresponding to xRegistry `resources_only`.

### 5.8. Reading a group

A client reads a group by resolving the `GroupType` child whose BrowseName
equals the requested `groupid`, then Reading its Properties and Browsing its
resource children as needed.

The standard base Properties are `GroupId`, `Xid`, `Epoch`, `Name`,
`Description`, `Documentation`, `CreatedAt` and `ModifiedAt`; `Labels` is an
`AttributesType` Object. Domain group subtypes MAY add mandatory
group-key Properties and extension metadata.

### 5.9. Deleting groups

Deleting a selected group uses the group's own `Delete(ExpectedEpoch: UInt32)`
Method, where `ExpectedEpoch` can be omitted and `0` disables the check. The Method
deletes the group and everything it contains, including its resources and their
versions and `Labels`. Deleting a collection subset is a sequence or
server-defined batch of `Delete(ExpectedEpoch)` Calls, one for each selected
group child.

If an entity-specific `epoch` precondition is supplied for deletion, the client
MUST pass it as `ExpectedEpoch`. If `ExpectedEpoch` is non-zero and does not
equal the group's current `Epoch`, the Call MUST fail with `Bad_InvalidState`
and delete nothing; `ExpectedEpoch = 0` or omission disables the check.

### 5.10. Resource metadata and resource documents

The xRegistry distinction between resource metadata and resource document is
made by the operation selected on the same `ResourceType` node. To access the
document, a client uses the inherited `FileType` Methods on `ResourceType`:
`Open`, `Read`, optionally `GetPosition` and `SetPosition`, `Write` when
replacing the document, and `Close`.

To access metadata, a client uses Read or Write on `ResourceType` Properties:
`ResourceId`, `VersionId`, `Format`, `ContentType`, `ExternalReference`,
`ResourceUrl`, `Xid`, `Epoch`, `Name`, `Description`, `Documentation`,
`CreatedAt` and `ModifiedAt`, plus domain Properties, and browses the
`Labels` `AttributesType` Object for labels and extension attributes.

If a resource type's xRegistry model has `hasdocument = false`, document access
MUST be rejected with `Bad_NotReadable`, `Bad_InvalidState` or
`Bad_NotSupported`, and metadata access remains the normal entity
representation.

When a resource or version is serialized as its domain-specific document, the
bytes returned by `Read(fileHandle, length)` are the exact document bytes. If
the document is empty, `Read` returns zero bytes at end-of-file.

OPC UA has no need for transport headers to carry resource metadata. Clients
obtain the metadata by reading the Properties of the file before or after
reading bytes. Servers SHOULD keep `ContentType` and the inherited `MimeType`
consistent so generic FileTransfer clients can identify the media type.

If `ResourceUrl` is present and the document is external, `Open` MAY fail with
`Bad_NotReadable` or MAY return a local cached representation. In either case
the client can read `ResourceUrl` and `ExternalReference` to resolve the
external content as described in §9.

### 5.11. Listing resource collections

A client lists a resource collection by Browse over the `GroupType` folder to
return `ResourceType` children in the requested resource collection. xRegistry
resource collections are unordered maps keyed by id; OPC UA Browse returns
children in a server-defined order, so a client MUST NOT infer collection order
from Browse position.

The serialized collection keys are `ResourceId` values and are available from
each resource BrowseName. The default version of each resource is represented by
the `ResourceType` selected by the server as the default for that `ResourceId`;
in a flat implementation with one file per resource, that file's `VersionId` is
the default version.

A client derives `versionscount` by browsing all files associated with the same
`ResourceId`, and derives `metaurl` and `versionsurl` from `Xid`.

### 5.12. Creating and updating resources

A client creates or updates resources as `ResourceType` children under the
group. For each resource key, the preferred one-shot path is
`GetOrCreateResource(ResourceId, VersionId, RequestFileOpen)` on the `GroupType`
, which returns the existing `(ResourceId, VersionId)` version with
`Created = false` or creates it with `Created = true`; if
`RequestFileOpen = true`, the returned write file handle MAY be used
immediately to write the document bytes. A new version of an existing resource
is created by passing its `ResourceId` with a new (or empty, server-assigned)
`VersionId`. Strict create operations use
`CreateResource(ResourceId, VersionId, RequestFileOpen)` when an existing
`(ResourceId, VersionId)` MUST fail.

For metadata-only updates, the client writes Properties and optionally calls
`Labels.AddAttribute` /`Labels.RemoveAttribute` on the resource's `Labels`
`AttributesType` object for extension attributes or labels. For document
creation or replacement, the client writes the complete document byte stream and
sets `ContentType`, `Format`, `ResourceUrl` and `ExternalReference` as
applicable.

If the supplied `ResourceId` conflicts with the selected resource identifier,
the operation MUST fail with `Bad_InvalidArgument`. If supplied `VersionId`
creates a new version rather than replacing the default version, the operation
MUST follow §5.17.

### 5.13. Reading a resource document

A client reads the default resource document by resolving the default
`ResourceType` for the selected `ResourceId`, calling `Open` for read,
repeatedly calling `Read`, and calling `Close`. The client MAY read `Size`,
`Writable`, `MimeType`, `LastModifiedTime`, `ContentType`, `ResourceId`,
`VersionId`, `Xid` and `Epoch` to reproduce the full xRegistry response
metadata.

If `ResourceUrl` or `ExternalReference` indicates external content, the server
MAY either redirect by metadata by returning readable `ResourceUrl`
/`ExternalReference` while `Open` fails with a suitable StatusCode, or serve
cached bytes from the local file. The choice MUST be documented in
`Capabilities`.

### 5.14. Reading and updating resource metadata

A client reads resource metadata by Reading the default resource file's
Properties and, when labels are requested, browsing and reading its `Labels`
`AttributesType` object without reading file bytes. A client updates metadata by
Writing the default `ResourceType` Properties, optionally combined with
`Labels.AddAttribute` and `Labels.RemoveAttribute` for resource extension
attributes and labels.

The resource-level meta view is a serialization view over Properties of the
resource and, where present, domain-defined Properties. The base model does not
define a separate `Meta` Object.

Base Properties such as `Epoch`, `CreatedAt` and `ModifiedAt` are normally
server-managed and MUST NOT be directly writable unless the server explicitly
allows administrative writes.

Changing default-version state is domain-defined because the base model only
defines `VersionId` on `ResourceType`; a server that supports the xRegistry
`defaultversionid` meta attribute MUST expose a writable domain Property or
Method for that state.

Deleting the meta view is not supported. The server MUST reject attempts to
delete the meta view with `Bad_NotSupported` or `Bad_InvalidArgument`.
Individual mutable meta attributes MAY be reset through update processing if the
domain model supports them.

### 5.15. Replacing a resource document

Replacing a resource document is create-if-needed plus complete file
replacement. If the resource file does not exist, the client preferably calls
`GetOrCreateResource` on the parent group, or `CreateResource` when existing
resources MUST fail. It then opens the file for writing, sets position to zero
where needed, writes the complete new byte stream, closes the file, and writes
or validates metadata Properties.

Partial patching of document bytes is not defined. A client that wants to change
document content MUST provide a complete replacement document.

### 5.16. Deleting resources

Deleting a selected resource uses the resource's own
`Delete(ExpectedEpoch: UInt32)` Method, where `ExpectedEpoch` can be omitted and
`0` disables the check, to delete the resource and everything it contains,
including versions and `Labels`, depending on the server's version
representation and xRegistry model configuration. Deleting a resource collection
subset is a sequence or server-defined batch of `Delete(ExpectedEpoch)` Calls,
one for each selected `ResourceType` or resource-version set.

If the implementation represents multiple versions as sibling files, deleting a
resource collection entry MUST delete all version files for the selected
`ResourceId` unless the request specifically targets a version entity.

A server MUST NOT leave dangling version files that remain discoverable as the
same resource unless the domain model explicitly supports detached historic
versions. If deletion of a default resource is disallowed while versions exist,
the server MUST return `Bad_InvalidState` or `Bad_NotSupported`.

### 5.17. Listing versions

A client lists versions by Browse for all `ResourceType` files associated with
the selected `ResourceId` and a non-empty `VersionId` under the owning
`GroupType`. xRegistry version collections are unordered maps keyed by
`VersionId`; OPC UA Browse returns children in a server-defined order, and
version order is conveyed by attributes such as `ancestor`, `createdat` and
`defaultversionid`, not by container position.

An implementation MAY represent the default version as the same file reached by
the resource identity and additional versions as sibling files, or it MAY expose
only one version if it does not support version history. The serialized version
collection keys are `VersionId` values.

### 5.18. Creating and updating versions

A client creates or updates a version by resolving a `ResourceType` with the
selected `ResourceId` and `VersionId`; if absent and creation is allowed, it
calls `GetOrCreateResource` on the group with the resource identifier or
`CreateResource` for strict creation, and sets the version identifier according
to the domain versioning model. The version file's BrowseName MUST be the
`versionid` when the version is materialized as its own entity.

For partial metadata updates, only named version attributes are written. For
full version representations, omitted mutable attributes are reset or removed
according to xRegistry rules. Extension attributes and labels on `ResourceType`
MAY be managed through `Labels.AddAttribute` and `Labels.RemoveAttribute` on the
version file's `Labels` `AttributesType` object where supported.

For document-bearing versions, the client writes the version document if
supplied and writes `ResourceId` and the new `VersionId`. The server updates
default-version state according to xRegistry rules and domain model
capabilities.

If an empty version map is supplied for a non-existent resource, the server MUST
reject it with `Bad_InvalidArgument`, corresponding to xRegistry
`missing_versions`.

The response representation is obtained by reading back the created or updated
version file's Properties and, for document mode, by reading back its file bytes
if needed.

### 5.19. Reading a version

A client reads a version document with `Open` /`Read`/`Close` on the
`ResourceType` whose `ResourceId` is the selected resource identifier and whose
`VersionId` is the selected version identifier.

A client reads version metadata by Reading that version file's Properties. The
`Xid` Property SHOULD identify the version path when the server materializes
versions as separate entities.

### 5.20. Replacing a version document

Replacing a version document is create-if-needed plus complete replacement of
the version file bytes using `GetOrCreateResource` or strict `CreateResource`,
`Open`, `SetPosition`, `Write` and `Close`.

Partial patching of version document bytes is not defined.

### 5.21. Deleting versions

Deleting a selected version uses the version file's own
`Delete(ExpectedEpoch: UInt32)` Method, where `ExpectedEpoch` can be omitted and
`0` disables the check. Deleting a versions collection subset is a sequence or
server-defined batch of `Delete(ExpectedEpoch)` Calls targeting the version
files selected by `VersionId`.

A server MUST reject deletion of the last remaining version of a resource if the
xRegistry model requires every resource to have at least one version. A server
MUST also reject deletion of a default version unless it can atomically select a
new default or the request explicitly sets one through a supported flag or meta
update.

If the version is the default version, the server MUST either reject the delete
with `Bad_InvalidState` or update default-version state according to xRegistry
and domain rules.

## 6. Request flags

The xRegistry core request flags defined by the xRegistry core specification and
primer are protocol-independent processing and representation controls. In OPC
UA they are represented by operation choice, service parameters, Browse result
processing, continuation points, Read `IndexRange`, Write options or server
capabilities rather than by transport-specific request parameters.

Unknown or unsupported flags SHOULD be ignored when xRegistry defines them as
response-shaping hints, and MUST be rejected with `Bad_NotSupported` or
`Bad_InvalidArgument` when they are needed for safe write semantics.

| xRegistry flag | OPC UA realization |
|---|---|
| `inline` | Browse and Read the named child collections or Properties in the same client operation sequence; a domain export MAY inline server-side |
| `filter` | Filter collection Browse results by BrowseName, NodeClass, TypeDefinition and target NodeId; read Properties or `Labels` only for predicates on values not present in the Browse result |
| `sort` | Client-side ordering of Browse results by a chosen attribute such as BrowseName, `VersionId` or `CreatedAt`, plus any additional Properties used as sort keys; OPC UA collection nodes remain unordered |
| pagination | Browse continuation points, `BrowseNext`, file `Read` length, and Read `IndexRange` |
| `doc` | Serialize using document shape, omitting redundant URL/count metadata as defined by xRegistry |
| `meta` | Read metadata Properties rather than document bytes; equivalent to metadata operation mode for resources and versions |
| `export` | Serialize the selected subtree as an xRegistry document |
| `epoch` | Pass `ExpectedEpoch` to `Labels.AddAttribute`, `Labels.RemoveAttribute` and `Delete`; for document replacement, use the epoch-matched sequence in §4.5.1 |
| `ignore` | Server-side write processing option advertised in `Capabilities`; unsupported ignore values fail with `Bad_InvalidArgument` |
| `setdefaultversionid` | Domain-defined default-version update, normally a meta Property or Method |
| `specversion` | Compare requested version against `SpecVersion` and `Capabilities`; reject incompatible processing with `Bad_InvalidArgument` |
| `binary` | Prefer raw `Open`/`Read` bytes for documents; metadata remains OPC UA typed Properties |
| `collections` | Include or omit collection members by Browse depth and serialization rules |

### 6.1. Filtering

A client applies the `filter` flag by Browsing the collection folder and
evaluating predicates directly against the Browse results where possible.
Identity and collection predicates use BrowseName, NodeClass, TypeDefinition and
target NodeId, so filtering by `groupid`, `resourceid` or a materialized
`versionid` does not require a per-result Read.

Only predicates on dynamic label values or other attributes not present in
Browse results require additional Reads. For a label-value predicate, the client
browses the candidate entity's `Labels` `AttributesType` object and reads only
the matching `<Attribute>` Property Variable where present; for fixed or domain
Properties such as `Name`, `CreatedAt` or `ModifiedAt`, the client reads those
Properties for the remaining candidates and evaluates the predicate locally.

### 6.2. Ignore processing

The `ignore` flag affects write processing. In OPC UA, ignore behavior is
advertised in `Capabilities` and applied by the server while processing Write,
Call and FileTransfer operations.

Because standard OPC UA Write and Call requests do not carry arbitrary xRegistry
option maps, a generic client that needs `ignore` semantics MUST either use a
server-defined operation that accepts write options, or MUST pre-process the
representation and omit ignored attributes before issuing standard Writes and
Calls. Unsupported ignore requirements MUST fail with `Bad_NotSupported` or
`Bad_InvalidArgument`.

### 6.3. Inlining

The `inline` flag maps to Browse depth and Property/document retrieval.
`inline=*` means the client recursively browses the selected subtree, reads each
entity's Properties, and reads document bytes where the document shape requires
them.

Inlining `capabilities` and `model` means reading the `Capabilities` and `Model`
`FileType` content on the registry root. Inlining nested collections means
browsing `GroupType` and `ResourceType` children and serializing them into the
parent entity representation.

### 6.4. Sorting

Clients sort collection entries locally. xRegistry group, resource and version
collections are unordered maps keyed by id, and OPC UA defines no
ordered-collection interface, so none is used. Sort keys available in Browse
results, such as BrowseName and DisplayName, require no per-result Read; sort
keys based on fixed Properties such as `VersionId` or `CreatedAt`, domain
Properties or label values require reading those values for the candidate
entries.

Browse order alone MUST NOT be assumed to be xRegistry sort order unless the
server explicitly documents that behavior in `Capabilities`. Version order is
conveyed by attributes such as `ancestor`, `createdat` and `defaultversionid`,
not by container position; a server MAY expose a domain index Property if it
needs deterministic order.

### 6.5. Document and metadata modes

The `doc` flag selects xRegistry document serialization and normally causes
derived URL/count attributes to be omitted where the xRegistry document shape
omits them. In OPC UA this is a serialization mode, not a different node.

The `meta` flag selects Property access for resources and versions. A client
MUST NOT attempt byte-level partial update of a document by selecting metadata
mode; metadata and document bytes are separate operation modes on the same
`ResourceType`.

### 6.6. Pagination and ranges

Collection pagination maps to Browse continuation points. Document range
retrieval maps to the `length` argument of `Read`, to repeated reads from the
current file position, and to `SetPosition` for random access. Label enumeration
maps to Browse of the `Labels` object and continuation points where needed.

Continuation points are session-scoped OPC UA state and are not serializable as
stable xRegistry identifiers. A protocol bridge MAY translate between another
binding's pagination tokens and OPC UA continuation points internally.

## 7. Value encoding

OPC UA uses typed Values and StatusCodes rather than transport headers and JSON
envelopes for every operation. JSON appears in this binding where xRegistry
defines JSON document content, namely `Capabilities`, `Model`, possible
model-source or export payloads, and resource documents whose domain media type
is JSON.

Strings MUST be encoded as OPC UA `String`, timestamps as `DateTime`, integer
epochs as `UInt32`, labels as `String` Property Variables under the `Labels`
`AttributesType` object, federation targets as `ExpandedNodeId`, and document
bytes as `ByteString` chunks returned by `Read` on `FileType`.

When a complete xRegistry entity is serialized for export or for a protocol
bridge, the base Property BrowseNames are converted to their xRegistry
lower-case attribute names. Domain Properties are serialized according to the
domain registry model.

A server MUST preserve unknown extension attributes that it accepts, using
domain extension Properties or Property Variables under the entity's `Labels`
`AttributesType` object as applicable. If the server cannot preserve an accepted
extension attribute, it MUST reject the update rather than silently losing
information.

## 8. Serialization / export-import

The document representation defined by xRegistry is produced from the OPC UA
AddressSpace by walking the selected subtree and converting nodes and Properties
to the xRegistry JSON entity shape.

For a `RegistryType`, serialization reads registry Properties, emits
`registryid`, `specversion`, common attributes and any requested
`capabilities` and `model` payloads read from the corresponding `FileType`
component Objects, then serializes group collections by browsing `GroupType`
children and grouping them by the xRegistry model's collection names.

For a `GroupType`, serialization reads `GroupId` and common Properties, emits
the domain group identifier attribute, and serializes resource collections by
browsing `ResourceType` children and grouping them by domain resource collection
names.

For a `ResourceType`, metadata serialization reads `ResourceId`, `VersionId`,
`Format`, `ContentType`, `ExternalReference`, `ResourceUrl` and common
Properties. Document serialization reads the file bytes with FileTransfer and
places them in the xRegistry `<RESOURCE>` or `<RESOURCE>base64` attribute
according to the xRegistry document rules and the selected encoding.

The inverse import process creates or updates the same subtree: create group
folders, create resource/version files, write document bytes, write mapped
Properties, update `Labels` containers, and let the server auto-bootstrap `Xid`
, `Epoch`, `CreatedAt` and `ModifiedAt` where they are not explicitly supplied
or are server-managed.

Serialization MUST preserve the three-representation symmetry described by the
xRegistry primer and by [*OPC UA —
xRegistry*](https://github.com/marcschier/opcua-drafts/blob/main/core-specs/xregistry/OPC-UA-xRegistry.md)
§4.2 and §7: an entity has the same `Xid` and identity whether reached as a
file, through OPC UA services, or in an exported xRegistry document.

## 9. Federation

Federation is realized by `ExternalReference` and `ResourceUrl` on
`ResourceType`, as defined by the xRegistry primer, xRegistry core
specification, and [*OPC UA —
xRegistry*](https://github.com/marcschier/opcua-drafts/blob/main/core-specs/xregistry/OPC-UA-xRegistry.md)
§8 and Annex B.

`ExternalReference` is an `ExpandedNodeId`. Its `ServerUri` identifies the
remote OPC UA server that hosts the referenced registry, and its `NamespaceUri`
plus identifier identify the remote resource node independently of the server's
local namespace indexes.

`ResourceUrl` is the xRegistry `<RESOURCE>url` string. It MAY contain an OPC UA
endpoint/browse-path convention for another OPC UA registry, or another URL for
a registry hosted behind a non-OPC-UA registry API.

To resolve a federated OPC UA resource, a client reads `ExternalReference`; if
`ServerUri` is local or empty it resolves the target in the local AddressSpace,
otherwise it discovers or connects to the remote endpoint, maps the
`NamespaceUri` to the remote namespace index, resolves the target NodeId or
BrowsePath, and reads the remote `ResourceType` using the same FileTransfer
operations as for a local file.

To resolve a resource federated to a non-OPC-UA API-hosted registry, a client or
gateway uses `ResourceUrl` as the external locator and treats the remote bytes
and metadata as the representation of the same xRegistry resource identity
carried by `Xid`, `ResourceId` and `VersionId`. The external authority
identifies the serving endpoint, not the resource identity.

A server MAY expose a local proxy `ResourceType` for a federated resource. Such
a proxy MUST retain the remote resource identity in `Xid`, `ResourceId` and
`VersionId`, and MUST NOT treat the local endpoint identity as part of the
resource identity.

## 10. Error handling

OPC UA errors are returned as StatusCodes on Service results, Operation results,
Method Call results, or individual input/output argument diagnostics. When an
xRegistry error includes structured details, a server SHOULD include additional
diagnostic information in the OPC UA DiagnosticInfo or in a domain-specific
error payload where available.

The following mapping is normative unless a more specific OPC UA StatusCode
applies.

| xRegistry error condition | OPC UA StatusCode |
|---|---|
| API function or entity target not supported (`api_not_found`) | `Bad_NodeIdUnknown`, `Bad_BrowseNameInvalid` or `Bad_NotSupported` |
| action not supported for an existing node | `Bad_NotSupported` or `Bad_MethodInvalid` |
| entity not found | `Bad_NodeIdUnknown` or `Bad_NotFound` where available |
| method target not found | `Bad_MethodInvalid` |
| invalid relative identifier segment or malformed identifier | `Bad_BrowseNameInvalid` or `Bad_InvalidArgument` |
| mandatory attribute missing | `Bad_InvalidArgument` |
| invalid attribute value | `Bad_InvalidArgument`, `Bad_TypeMismatch` or `Bad_OutOfRange` |
| mismatched `RegistryId`, `GroupId`, `ResourceId` or `VersionId` | `Bad_InvalidArgument` or `Bad_IdentityChangeNotSupported` |
| already exists | `Bad_BrowseNameDuplicated` or `Bad_NodeIdExists` |
| not writable or read-only attribute | `Bad_NotWritable` or `Bad_UserAccessDenied` |
| resource document not readable | `Bad_NotReadable` or `Bad_InvalidState` |
| missing body or missing document bytes | `Bad_InvalidArgument` |
| unsupported metadata mode | `Bad_NotSupported` or `Bad_InvalidArgument` |
| partial update attempted on document bytes | `Bad_NotSupported` |
| unsupported flag or ignore value | `Bad_NotSupported` or `Bad_InvalidArgument` |
| `ExpectedEpoch` on `Delete`, `Labels.AddAttribute` or `Labels.RemoveAttribute` does not match current `Epoch` | `Bad_InvalidState` |
| delete would violate version/default-version constraints | `Bad_InvalidState` |
| filter not supported | `Bad_FilterNotAllowed` or `Bad_NotSupported` |
| continuation point invalid or expired | `Bad_ContinuationPointInvalid` |
| file handle invalid | `Bad_InvalidArgument` or the FileTransfer-defined invalid-handle StatusCode |
| file is locked or concurrently modified | `Bad_InvalidState` or `Bad_ResourceUnavailable` |
| external federation target cannot be resolved | `Bad_NotFound`, `Bad_CommunicationError` or `Bad_ServerUriInvalid` |
| server cannot preserve accepted extension attribute | `Bad_NotSupported` |
| operation exceeds server limits | `Bad_TooManyOperations`, `Bad_EncodingLimitsExceeded` or `Bad_OutOfMemory` |

A batch operation MUST report failure in a way that lets the client identify the
failing entity. If the operation is represented as multiple OPC UA Service
calls, the failing call's StatusCode and diagnostics identify the entity. If a
server exposes a domain batch Method, each entity result SHOULD carry its own
StatusCode and the Method result MUST indicate whether any partial effects
occurred.

Authorization failures MUST use `Bad_UserAccessDenied` or
`Bad_SecurityChecksFailed`. Authentication and secure-channel failures are
governed by OPC 10000-4 and are not redefined by this binding.

## 11. Conformance

A server conforms to the read-only OPC UA xRegistry API if it exposes a
`RegistryType` root or domain subtype, exposes groups as `GroupType` or
subtypes, exposes resource/version documents as `ResourceType` or subtypes, and
supports Browse, Read and `Open` /`Read`/`Close` sufficient to retrieve registry
metadata, collections and resource documents.

A server conforms to the writable OPC UA xRegistry API if, in addition to
read-only conformance, it supports the applicable creation and mutation
operations (`CreateGroup`, `GetOrCreateGroup`, `CreateResource`,
`GetOrCreateResource`, `Delete`, and `Labels.AddAttribute`
/`Labels.RemoveAttribute` with `ExpectedEpoch` on each mutable entity's `Labels`
`AttributesType` container), writable Properties, and `Open` /`Write`/`Close` on
`ResourceType`, `Capabilities` and `Model` where document replacement is
mutable.

A server conforms to the export-capable OPC UA xRegistry API if it implements
the request-flag mappings it advertises in `Capabilities`, including Browse
continuation point pagination, Browse-result filtering, and export serialization
that follows the xRegistry document shape.

A client conforms if it can select a `RegistryType` root, resolve xRegistry
`xid` s or relative identifiers to AddressSpace nodes, use
Browse/Read/FileTransfer operations for reading, use Write/Call operations for
advertised write capabilities, interpret StatusCodes according to §10, and
serialize or consume xRegistry document representations according to §8.

A conforming implementation MUST NOT require any node or Method name that is not
defined by [*OPC UA —
xRegistry*](https://github.com/marcschier/opcua-drafts/blob/main/core-specs/xregistry/OPC-UA-xRegistry.md),
OPC 10000-20, or its own domain companion specification.

## Annex A — Correspondence to the xRegistry HTTP binding (informative)

This annex is informative and provides a cross-walk for readers coming from the
sibling xRegistry HTTP binding. The OPC UA API defined by this document is not
derived from these HTTP methods or paths; the table only identifies the
corresponding operation concepts in the two peer bindings.

| xRegistry operation | OPC UA operation in this document | HTTP binding method and path |
|---|---|---|
| Read registry | Read `RegistryType` Properties and Browse group children (§5.1) | `GET /` |
| Replace or partially update registry attributes | Write mutable `RegistryType` Properties, call `Labels.AddAttribute`/`Labels.RemoveAttribute` for labels, and process nested groups when supplied (§5.2) | `PUT /`, `PATCH /` |
| Process group collections at the registry root | Resolve or create `GroupType` children with `GetOrCreateGroup` or strict `CreateGroup` and Write Properties (§5.2) | `POST /` |
| Export registry document | Browse/Read the `RegistryType` subtree and serialize it (§5.3, §8) | `GET /export` or `GET /?export` |
| Read capabilities | Prefer Read of typed `RegistryType.CapabilitiesInfo`; alternatively `Open`/`Read`/`Close` on raw JSON `RegistryType.Capabilities` (§5.4) | `GET /capabilities` |
| Read offered capabilities | Read a domain offered-capabilities Property or offered section in the `Capabilities` JSON document (§5.4) | `GET /capabilitiesoffered` |
| Replace or partially update capabilities | `Open(write)`/`Write`/`Close` on `RegistryType.Capabilities` if writable (§5.5) | `PUT /capabilities`, `PATCH /capabilities` |
| Read model | `Open`/`Read`/`Close` on `RegistryType.Model` (§5.4) | `GET /model` |
| Read model source | Read a domain model-source target or documented section in the `Model` JSON document (§5.4) | `GET /modelsource` |
| Replace model source | Write the domain model-source target if supported (§5.5) | `PUT /modelsource` |
| List a group collection | Browse `GroupType` children under the registry (§5.6) | `GET /<GROUPS>` |
| Create or update a group collection subset | Resolve/create `GroupType` children and Write group Properties (§5.7) | `PATCH /<GROUPS>`, `POST /<GROUPS>` |
| Delete a group collection subset | Call `Delete(ExpectedEpoch)` for each selected `GroupType` node (§5.9) | `DELETE /<GROUPS>` |
| Read a group | Resolve the `GroupType` by BrowseName, then Read Properties and Browse resources (§5.8) | `GET /<GROUPS>/<GID>` |
| Replace or partially update a group | Create if needed with `GetOrCreateGroup` or strict `CreateGroup`, then Write mutable group Properties and optionally call `Labels.AddAttribute`/`Labels.RemoveAttribute` (§5.7) | `PUT /<GROUPS>/<GID>`, `PATCH /<GROUPS>/<GID>` |
| Process resource collections under a group | Resolve/create `ResourceType` children and Write documents, Properties or `Labels` entries (§5.7) | `POST /<GROUPS>/<GID>` |
| Delete a group | Call `Delete(ExpectedEpoch)` on the selected `GroupType` node (§5.9) | `DELETE /<GROUPS>/<GID>` |
| List a resource collection | Browse `ResourceType` children under the group (§5.11) | `GET /<GROUPS>/<GID>/<RESOURCES>` |
| Create or update a resource collection subset | Resolve/create `ResourceType` children with `GetOrCreateResource` or strict `CreateResource`, then Write documents, Properties or `Labels` entries (§5.12) | `PATCH /<GROUPS>/<GID>/<RESOURCES>`, `POST /<GROUPS>/<GID>/<RESOURCES>` |
| Delete a resource collection subset | Call `Delete(ExpectedEpoch)` for each selected `ResourceType` node (§5.16) | `DELETE /<GROUPS>/<GID>/<RESOURCES>` |
| Read a resource document | `Open`/`Read`/`Close` on the default `ResourceType` (§5.13) | `GET /<GROUPS>/<GID>/<RESOURCES>/<RID>` |
| Read resource metadata | Read Properties of the default `ResourceType` (§5.14) | `GET /<GROUPS>/<GID>/<RESOURCES>/<RID>$details` |
| Replace or partially update resource metadata | Write resource Properties and optionally call `Labels.AddAttribute`/`Labels.RemoveAttribute` (§5.14) | `PUT /<GROUPS>/<GID>/<RESOURCES>/<RID>$details`, `PATCH /<GROUPS>/<GID>/<RESOURCES>/<RID>$details` |
| Replace a resource document | Create if needed with `GetOrCreateResource` or strict `CreateResource`, then `Open`/`SetPosition`/`Write`/`Close` (§5.15) | `PUT /<GROUPS>/<GID>/<RESOURCES>/<RID>` |
| Create or update a resource version | Create/update a `ResourceType` with matching `ResourceId` and `VersionId` using `GetOrCreateResource` or strict `CreateResource` where needed (§5.18) | `POST /<GROUPS>/<GID>/<RESOURCES>/<RID>` |
| Delete a resource | Call `Delete(ExpectedEpoch)` on the selected `ResourceType` node, deleting the resource and its versions according to model rules (§5.16) | `DELETE /<GROUPS>/<GID>/<RESOURCES>/<RID>` |
| Read resource meta entity | Read resource-level Properties and domain meta Properties (§5.14) | `GET /<GROUPS>/<GID>/<RESOURCES>/<RID>/meta` |
| Replace or partially update resource meta entity | Write supported meta Properties or domain default-version state (§5.14) | `PUT /<GROUPS>/<GID>/<RESOURCES>/<RID>/meta`, `PATCH /<GROUPS>/<GID>/<RESOURCES>/<RID>/meta` |
| Delete resource meta entity | Reject as unsupported or reset individual mutable meta attributes when domain-defined (§5.14) | `DELETE /<GROUPS>/<GID>/<RESOURCES>/<RID>/meta` |
| List versions | Browse version `ResourceType` files (§5.17) | `GET /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions` |
| Create or update version collection subset | Resolve/create version files with `GetOrCreateResource` or strict `CreateResource`, then Write version documents, Properties or `Labels` entries (§5.18) | `PATCH /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions`, `POST /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions` |
| Delete version collection subset | Call `Delete(ExpectedEpoch)` for each selected version file (§5.21) | `DELETE /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions` |
| Read a version document | `Open`/`Read`/`Close` on the selected version file (§5.19) | `GET /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>` |
| Read version metadata | Read Properties of the selected version file (§5.19) | `GET /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>$details` |
| Replace or partially update version metadata | Write version Properties and optionally call `Labels.AddAttribute`/`Labels.RemoveAttribute` (§5.18) | `PUT /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>$details`, `PATCH /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>$details` |
| Replace a version document | Create if needed with `GetOrCreateResource` or strict `CreateResource`, then `Open`/`SetPosition`/`Write`/`Close` on the version file (§5.20) | `PUT /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>` |
| Delete a version | Call `Delete(ExpectedEpoch)` on the selected version `ResourceType` node (§5.21) | `DELETE /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>` |

[xRegistry Core]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html
[xRegistry HTTP]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/http.html
[xRegistry primer]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/primer.html