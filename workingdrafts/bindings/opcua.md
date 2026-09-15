# xRegistry OPC UA API - Version 1.0-rc4

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
<!-- words: userwritable eventsourceurl correlationid metaepoch -->
<!-- words: eventnotifier eventtype eventtypes generatesEvent republish -->
<!-- words: monitoreditems modelsource undeprecated reconciliation -->
<!-- words: baseeventtype capabilitiesupdatedeventtype contentfilter -->
<!-- words: createmonitoreditems createsubscription deletemonitoreditems -->
<!-- words: deletesubscriptions eventfilter eventid greaterthan hasnotifier -->
<!-- words: groupcreatedeventtype groupdeletedeventtype -->
<!-- words: groupdeprecatedeventtype groupundeprecatedeventtype -->
<!-- words: groupupdatedeventtype modelsourceupdatedeventtype -->
<!-- words: modelupdatedeventtype monitoreditem oftype -->
<!-- words: registrycreatedeventtype registrydeletedeventtype -->
<!-- words: registryupdatedeventtype resourcecreatedeventtype -->
<!-- words: resourcedeletedeventtype resourcedeprecatedeventtype -->
<!-- words: resourceundeprecatedeventtype resourceupdatedeventtype -->
<!-- words: sourcename sourcenode sourceurl subscribetoevents -->
<!-- words: versioncreatedeventtype versiondeletedeventtype -->
<!-- words: versionupdatedeventtype resourceversionstype -->
<!-- words: assignedversionid incarnation -->
<!-- words: metalabels metacreatedat metamodifiedat -->
<!-- words: opcf eraseexisting monitoringmode -->

## Abstract

This specification defines an OPC UA protocol binding for the xRegistry document
format and API [specification][xRegistry Core]. It is a peer of the
[HTTP binding][xRegistry HTTP]: a registry, its groups, resources, versions,
documents and attributes are discovered, read, created, updated, deleted,
exported and federated, and their changes are reported as native OPC UA Events,
rather than by tunnelling HTTP or CloudEvents payloads over OPC UA.

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
- [9. Events](#9-events)
  - [9.1. Native event model and canonical types](#91-native-event-model-and-canonical-types)
  - [9.2. Event field mapping](#92-event-field-mapping)
  - [9.3. Event source URL](#93-event-source-url)
  - [9.4. Interaction and emission rules](#94-interaction-and-emission-rules)
  - [9.5. Event notification topology](#95-event-notification-topology)
  - [9.6. Subscription, discovery and filtering](#96-subscription-discovery-and-filtering)
  - [9.7. Delivery lifetime and replay](#97-delivery-lifetime-and-replay)
- [10. Federation](#10-federation)
- [11. Error handling](#11-error-handling)
- [12. Conformance](#12-conformance)
- [Annex A — Correspondence to the xRegistry HTTP binding (informative)](#annex-a--correspondence-to-the-xregistry-http-binding-informative)

## 1. Scope

This specification defines the OPC UA API binding for
[xRegistry](https://github.com/xregistry/spec): how a registry, its groups,
resources, versions, documents and attributes are discovered, read, created,
updated and deleted natively over OPC UA Services while realizing the xRegistry
core model on the OPC UA AddressSpace and FileTransfer model of *OPC UA —
xRegistry*.

The abstract information model is defined by *OPC UA — xRegistry*:
a registry is a `RegistryType` folder (subtype of `FolderType`), each group is
a `GroupType` folder (subtype of `FolderType`), and each logical Resource and
exact Version is a distinct `ResourceType` file (subtype of `FileType`). A
logical Resource owns a typed `ResourceVersionsType` component named
`Versions`, which contains its exact Version Objects. The hierarchy permanently
distinguishes the two roles even though both use `ResourceType` or the same
domain file subtype. This API specifies how clients interact with those nodes
using Browse, BrowseNext, Read, Write, Call,
TranslateBrowsePathsToNodeIds and the FileTransfer Methods inherited by
`ResourceType`; deletion is an xRegistry `Delete(ExpectedEpoch)` Method call on
the `GroupType` or `ResourceType` entity being deleted.

> Annex A provides an informative correspondence for readers familiar with
> sibling protocol bindings, while §10 describes federation, including references
> to registries hosted behind other APIs.

This binding is independent of any domain registry. A concrete companion
specification subtypes `RegistryType`, `GroupType` and `ResourceType`,
constrains group and resource names, and MAY add domain Properties or Methods;
the OPC UA API patterns in this document remain the same.

## 2. Normative references

- [xRegistry Core specification](../../core/spec.md) — the registry, group, resource, version, document, attribute, request-flag, operation-processing and error model.
- [xRegistry Events specification](https://github.com/xregistry/spec/blob/66ee31e47fbadff6ab982ae1516f7d9065e46b64/core/events.md) — canonical xRegistry event types, fields and emission rules, interpreted with the binding corrections in §9.1.
- [xRegistry primer](../../core/primer.md) — the xRegistry concepts, representations, request-shaping concepts and federation model.
- *OPC UA — xRegistry* — Version 0.6.0, published
  `2026-09-05T00:00:00Z`, at commit
  `d3399fca025025a73e5a6b599f850a81d985c060`. The xRegistry NodeSet SHA-256
  digest is
  `369f5f3f1814b333e4eeb52bfb4b6a730cdff372505a5f91a54c94f0016ac4cf`.
  This companion information model defines the distinct Resource and Version
  Objects, `ResourceVersionsType`, Resource Meta and the EventTypes used by §9.
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
exactly as defined by *OPC UA —
xRegistry*
Annex A and the corresponding NodeSet: `RegistryType`, `GroupType`,
`ResourceType`, `ResourceVersionsType`, `AttributesType`,
`RegistryCapabilitiesDataType`,
`RegistryId`, `SpecVersion`, `Capabilities`, `CapabilitiesInfo`, `Model`,
`GroupId`, `ResourceId`, `VersionId`, `Format`, `ContentType`,
`ExternalReference`, `ResourceUrl`, `Xid`, `Epoch`, `Name`, `Description`,
`Documentation`, `Labels`, `<Attribute>`, `CreatedAt`, `ModifiedAt`,
`MetaEpoch`, `MetaLabels`, `MetaCreatedAt`, `MetaModifiedAt`, `Versions`,
`AssignedVersionId`,
`CreateGroup`, `GetOrCreateGroup`, `CreateResource`, `GetOrCreateResource`,
`AddAttribute`, `RemoveAttribute`, `Delete` and `ExpectedEpoch`.
The event model additionally defines `EventSourceUrl`, `SourceUrl`, `Subject`,
`Changed` and `CorrelationId`, and the concrete EventTypes listed in §9.1.

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
`ResourceType` child of a group represents one logical Resource; its
`ResourceVersionsType` component named `Versions` contains distinct
`ResourceType` children representing exact Versions. Both roles use the domain
resource file subtype, but their hierarchy, BrowseName and `Xid` permanently
identify the role. xRegistry labels and extension attributes are represented by
Property Variables under `Labels` for registries, groups and exact Versions.
Resource Meta is represented on the logical Resource under `MetaLabels`.

The logical Resource is also a `FileType` view. Its normal Version Properties,
`Labels` and FileTransfer Methods delegate to the selected default Version. Its
Resource Meta Properties and `MetaLabels` remain authoritative on the logical
Resource. Changing the default Version changes the delegated values and the
target of future file opens; it does not change any NodeId, `Xid` or deletion
role.

A server MAY expose more than one registry. A client selects the registry root
by NodeId, BrowsePath, discovery metadata or domain convention before applying
this API.

The selected registry root is the API authority for the operation sequence. No
URL authority is involved in the native OPC UA API; entity identity is carried
by xRegistry identifier Properties and `Xid`, while the OPC UA session,
endpoint and NodeIds identify where those entities are currently served.

The baseline operation model is: Browse a folder to enumerate a collection,
select entities from the Browse result by BrowseName, NodeClass, TypeDefinition
and target NodeId, Read Properties and the applicable `Labels` or `MetaLabels`
container's `<Attribute>` Property Variables to obtain attributes that are not
already in the Browse result, Write writable Properties to change fixed mutable
attributes, Call `Open` /`Read`/`Write`/`Close` to read or replace document
bytes on a logical Resource view or an exact Version, Call
`CreateGroup`, `GetOrCreateGroup`, `CreateResource` or `GetOrCreateResource`
to create entities, Call the entity's `Delete(ExpectedEpoch)` Method to delete
it and everything it contains, and Call `AddAttribute` or `RemoveAttribute` on
`Labels` or `MetaLabels` for supported labels and extension attributes.

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
| `/<GROUPS>/<GID>/<RESOURCES>` | collection of logical `ResourceType` children under the group whose collection name is `<RESOURCES>` | Browse and optionally `CreateResource` or `GetOrCreateResource` on the group |
| `/<GROUPS>/<GID>/<RESOURCES>/<RID>` | logical `ResourceType` whose BrowseName and `ResourceId` are `<RID>` | Read Resource Meta; use delegated Version Properties or FileTransfer Methods for the selected default Version; Call Resource `Delete` |
| `/<GROUPS>/<GID>/<RESOURCES>/<RID>$details` | flattened Resource view on the logical `ResourceType` | Read/Write delegated default-Version Properties/`Labels` and authoritative Resource Meta Properties/`MetaLabels` |
| `/<GROUPS>/<GID>/<RESOURCES>/<RID>/meta` | Resource Meta and default-version selection state on the logical `ResourceType` | Read/Write `MetaEpoch`, `MetaCreatedAt`, `MetaModifiedAt`, `MetaLabels` and domain meta Properties |
| `/<GROUPS>/<GID>/<RESOURCES>/<RID>/versions` | logical Resource's `ResourceVersionsType` component named `Versions` | Browse exact Version children |
| `/<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>` | exact Version `ResourceType` under `Versions`, whose BrowseName and `VersionId` are `<VID>` | `Open`/`Read` document bytes, Read metadata Properties or Call Version `Delete` |
| `/<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>$details` | exact Version metadata view | Read/Write Properties and optionally `Labels.AddAttribute`/`Labels.RemoveAttribute` |

The collection names `<GROUPS>` and `<RESOURCES>` are xRegistry model names, not
mandatory OPC UA base nodes. A domain registry MAY express collection names
through subtype BrowseNames, domain Properties, folders or model metadata, but
each concrete group instance MUST be a `GroupType` or subtype. Each logical
Resource and exact Version MUST be a `ResourceType` or the same domain subtype;
the logical Resource MUST own a `ResourceVersionsType` component with
BrowseName `Versions`.

A server MUST set each group's, logical Resource's and exact Version's
BrowseName to its identifier: `groupid`, `resourceid` or `versionid`,
respectively, and each group's and logical Resource's DisplayName to its
`Name`. A `groupid` and a
`resourceid` are **symbolic identifiers** built from the entity's domain source
identity by the construction of *OPC UA —
xRegistry*
§6.9, so they are readable, safe in a URL, on a command line and as a file name,
and never derived from a document. Because Browse results carry BrowseName,
DisplayName, NodeClass, TypeDefinition and the target NodeId, a client selects
and filters entities by identity and collection directly from the Browse result
with no Read per candidate, and renders a readable list without one either; only
filters on a dynamic label value or another attribute not present in the Browse
result require reading the applicable `Labels` or `MetaLabels` container or
Properties.

The xRegistry `self` value is not a mandatory OPC UA Property in the base model.
In this API it is derived from the selected registry root and the entity's
`Xid`; an OPC UA client can reconstruct a canonical self reference as a registry
root NodeId plus the relative `Xid`, or as an implementation-defined URL or URN
for display.

`Xid` MUST always be the structural relative xRegistry path of the registry,
group, Resource or Version. The logical Resource `Xid` is its resource path.
Each exact Version `Xid` is that Resource `Xid` followed by
`/versions/<VID>`. An `Xid` MUST NOT be a content fingerprint, digest or other
document-derived identifier. A server MAY use content identity as an internal
lookup, cache or deduplication fast path, but that optimization MUST NOT change
`Xid`, `Subject`, `ResourceId`, `VersionId` or AddressSpace placement.

Here, resource is the generic xRegistry entity kind. A concrete registry uses
the domain-specific `<RESOURCES>` collection and `<RESOURCE>` singular names
declared by its model; this binding does not impose a literal `resources` path
segment.

Servers implementing Version 0.6.0 of the companion model MUST expose only the
distinct hierarchy defined in this section and MUST NOT expose group-level
legacy aliases for exact Versions. Updated clients MAY fall back to the prior
Version 0.5 companion layout only when the advertised companion model lacks a
`Versions` component: they resolve group-level `ResourceType` Objects by
`ResourceId` and `VersionId` using the Version 0.5 rules. A client MUST NOT
combine flat and distinct discovery within one registry.

### 4.3. Entity processing rules

Reading a collection is Browse over the corresponding folder. Reading an entity
metadata view is Read of the entity Properties and, when labels are needed,
Browse/Read of its `Labels` `AttributesType` container. Resource Meta instead
uses `MetaLabels` on the logical Resource. Reading a Resource document is
`Open` /`Read`/`Close` on its delegated default-Version view; reading an exact
Version document uses the exact Version `ResourceType`.

Full replacement of an entity targets the entity node or the parent from which
the entity can be created. If the entity does not exist, the server creates a
`GroupType` folder or atomically creates a logical Resource and its first exact
Version; if it exists, the server updates it. Mutable Properties, `Labels`
entries or Resource Meta `MetaLabels` entries omitted from the replacement
representation MUST be deleted, reset to default or left unchanged only where
the xRegistry core rules or server-managed semantics require that behavior.

Partial update of an entity changes only explicitly named mutable attributes and
removes explicitly null attributes where removal is supported. It is realized by
Write of writable Properties and, where extension attributes or labels are
involved, by Call of
`Labels.AddAttribute(Key: String, Value: String, ExpectedEpoch: UInt32)` or
`Labels.RemoveAttribute(Key: String, ExpectedEpoch: UInt32)` on the entity's
`Labels` `AttributesType` object. Resource Meta labels use the corresponding
Methods on `MetaLabels` with `ExpectedEpoch` matched against `MetaEpoch`.
Success/failure is conveyed by the Method Call StatusCode. Partial update MUST
NOT patch arbitrary bytes inside a resource document; document content changes
use complete replacement of the document byte stream.

Collection processing creates or updates one or more child entities under the
collection's parent. A client preferably creates or resolves groups with
`GetOrCreateGroup` on `RegistryType` and Resources or Versions with
`GetOrCreateResource` on `GroupType`; strict create operations use
`CreateGroup` and `CreateResource` when existence is an error. The resource
Methods return the exact Version NodeId, `AssignedVersionId` and a handle when
requested. The logical Resource is discovered separately under the group. After
creation or resolution the client writes mandatory and mutable Properties,
updates the applicable `Labels` or `MetaLabels` container, and writes document
bytes where supplied. A server MUST apply the xRegistry atomicity rule: if one
entity in a collection operation cannot be processed, the server SHOULD reject
the whole operation and avoid partial effects; if the server cannot guarantee
multi-node atomicity, it MUST advertise that limitation in `Capabilities`.

Nested collection processing on an entity MUST process only nested collection
entries and MUST NOT modify the owning entity's own Properties. For example,
processing resources under a selected group creates or updates `ResourceType`
children without changing the group's own Properties.

Deleting an entity is performed by Calling its `Delete(ExpectedEpoch: UInt32)`
Method on the `GroupType` or `ResourceType` node to remove. A group deletion
matches `ExpectedEpoch` against `Epoch`. A logical Resource deletion matches it
against `MetaEpoch` and removes the Resource, `Versions` container and all exact
Versions. An exact Version deletion matches it against that Version's `Epoch`
and removes only that Version. Deleting a collection subset is a sequence or
server-defined batch of `Delete(ExpectedEpoch)` Calls over selected children.

Unless otherwise stated, a request to update a read-only Property MUST be
ignored only if xRegistry says that read-only attribute updates are ignored;
otherwise the server MUST reject the Write with `Bad_NotWritable` or
`Bad_UserAccessDenied`. A request that supplies an identifier Property
(`RegistryId`, `GroupId`, `ResourceId` or `VersionId`) whose value conflicts
with the target entity MUST fail with `Bad_InvalidArgument` or
`Bad_IdentityChangeNotSupported`.

Any successful registry, group or Version create or update MUST update that
entity's `ModifiedAt` and increment its `Epoch`. A Resource Meta update instead
updates `MetaModifiedAt` and increments `MetaEpoch`; it does not change the
selected default Version's `Epoch` or `ModifiedAt` unless Version attributes
also change. Creation MUST initialize the applicable `CreatedAt`, `ModifiedAt`,
`Epoch`, `MetaCreatedAt`, `MetaModifiedAt`, `MetaEpoch`, `Xid` and identifier
Properties according to *OPC UA — xRegistry*
§6.5 and the xRegistry core rules.

### 4.4. OPC UA-specific attribute processing

OPC UA carries fixed metadata as typed Property Values. Strings are OPC UA
`String`, timestamps are `DateTime`, `ExternalReference` is `ExpandedNodeId`,
and `Epoch` and `MetaEpoch` are `UInt32`. Labels and extension attributes are
`String` Property Variables under `Labels`; Resource Meta labels and extension
attributes are under `MetaLabels`.

When a Resource document is read as bytes, accompanying metadata is obtained
from the logical Resource's delegated Version Properties and authoritative
Resource Meta Properties. For an exact Version, metadata is read from that
Version Object. A server MAY optimize this by exposing a domain Method, but the
interoperable baseline is separate `Open` /`Read`/`Close` plus Browse and Read
metadata.

The metadata view of a Resource or Version is represented by choosing Property
Reads or Writes instead of file content Reads or Writes. Resource and Version
NodeIds remain distinct.

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
| Create Resource or Version | `GroupType.CreateResource(ResourceId, VersionId, RequestFileOpen) -> (ResourceNodeId, AssignedVersionId, FileHandle)` | A Version is identified by `(ResourceId, VersionId)`; a new `ResourceId` atomically creates the logical Resource, `Versions` container and first exact Version, while an existing `ResourceId` with a new `VersionId` creates only an exact Version under `Versions`; an empty input `VersionId` lets the server assign `AssignedVersionId`; despite its retained output name, `ResourceNodeId` is the exact Version NodeId; `RequestFileOpen = true` returns a write handle for that Version; fails with `Bad_NodeIdExists` if that exact pair already exists |
| Get or create Resource or Version | `GroupType.GetOrCreateResource(ResourceId, VersionId, RequestFileOpen) -> (ResourceNodeId, AssignedVersionId, FileHandle, Created)` | Resolves the exact `(ResourceId, VersionId)` Version; an empty input `VersionId` selects the existing default Version or creates the first Version for a new Resource; the retained `ResourceNodeId` output is the exact Version NodeId, `AssignedVersionId` is the assigned Version identifier, and `RequestFileOpen = true` returns a write handle for that Version |
| Delete group, Resource or Version | `Delete(ExpectedEpoch: UInt32)` on the selected `GroupType` or `ResourceType` | `0` or omission disables the check; a group or exact Version matches against `Epoch`, while a logical Resource matches against `MetaEpoch`; a mismatch fails with `Bad_InvalidState` and deletes nothing; the Method has no output arguments |
| Read document | `ResourceType.Open(mode)` -> `Read(fileHandle, length)` -> `Close(fileHandle)` | `mode` is read-only; `length` and repeated Reads are bounded by `Size` |
| Replace document | `ResourceType.Open(mode)` -> `SetPosition(fileHandle, 0)` -> `Write(fileHandle, data)` -> `Close(fileHandle)` | `mode` allows write and stages the complete replacement byte stream; only a successful dirty `Close` updates Version `ModifiedAt` and `Epoch` |
| Read metadata | Read Service on Properties | Property BrowseNames map to xRegistry attribute names by the tables in this document and the domain model |
| Replace scalar metadata | Write Service on Properties | Value DataTypes are those in Annex A of the base model |
| Add/update registry, group or version extension attribute or label | `Labels.AddAttribute(Key: String, Value: String, ExpectedEpoch: UInt32)` | `Labels` is the entity or version's `AttributesType` object; `ExpectedEpoch` is matched against its `Epoch`; success increments `Epoch` and updates `ModifiedAt` |
| Remove registry, group or version extension attribute or label | `Labels.RemoveAttribute(Key: String, ExpectedEpoch: UInt32)` | `Labels` is the entity or version's `AttributesType` object; `ExpectedEpoch` is matched against its `Epoch`; success increments `Epoch` and updates `ModifiedAt` |
| Add/update Resource Meta extension attribute or label | `MetaLabels.AddAttribute(Key: String, Value: String, ExpectedEpoch: UInt32)` | `MetaLabels` is on the logical Resource; `ExpectedEpoch` is matched against `MetaEpoch`; success increments `MetaEpoch` and updates `MetaModifiedAt` |
| Remove Resource Meta extension attribute or label | `MetaLabels.RemoveAttribute(Key: String, ExpectedEpoch: UInt32)` | `MetaLabels` is on the logical Resource; `ExpectedEpoch` is matched against `MetaEpoch`; success increments `MetaEpoch` and updates `MetaModifiedAt` |

From the xRegistry perspective, creating a new Resource necessarily creates its
first Version in the same operation; neither can be created independently.
`CreateResource` and `GetOrCreateResource` with `Created = true` commit both
structural identities, the `Versions` container, their `Xid` values, initial
epochs and timestamps before returning. They return the exact Version NodeId,
not the logical Resource NodeId. A client discovers the logical Resource by its
`ResourceId` BrowseName under the domain resource collection. Returning a
writable `FileHandle` does not defer or merge the structural commit with a later
file write.

The base model defines `CreateGroup` and `GetOrCreateGroup` on `RegistryType`,
`CreateResource` and `GetOrCreateResource` on `GroupType`, and `AttributesType`
with `AddAttribute` / `RemoveAttribute`. Registries, groups and exact Versions
MAY expose `Labels`. `MetaLabels` belongs to Resource Meta and is authoritative
on the logical Resource. Clients call the Methods on the container that owns
the target attribute. The creation Methods are the base API create operations;
move/copy is out of scope for the base API and can be modeled by re-creating an
entity and deleting the original where permitted.

#### 4.5.1. Concurrency and locking

FileTransfer itself provides the baseline concurrency control. Opening an exact
Version for write reserves that Version incarnation. Opening a logical Resource
for write first selects its current default Version and acquires the same
reservation as an exact-node open on that Version. A second write `Open` through
either path returns `Bad_NotWritable`, and a read `Open` returns
`Bad_NotReadable` while the Version is open for writing. Optimistic concurrency
for Version content is based on that exact Version's `Epoch`.

For registry, group or version label mutation through `Labels.AddAttribute` and
`Labels.RemoveAttribute`, a client passes the entity or version's current
`Epoch` as `ExpectedEpoch`. If non-zero and unequal, the Method MUST fail with
`Bad_InvalidState` and make no change. On success, `Epoch` increments and
`ModifiedAt` is updated.

For Resource Meta label mutation through `MetaLabels.AddAttribute` and
`MetaLabels.RemoveAttribute`, a client passes the current `MetaEpoch` as
`ExpectedEpoch`. If non-zero and unequal, the Method MUST fail with
`Bad_InvalidState` and make no change. On success, `MetaEpoch` increments and
`MetaModifiedAt` is updated. For either container, `ExpectedEpoch = 0` or an
omitted argument disables the check.

For document replacement, exclusive `Open(write)` serializes writers. An
epoch-matched replacement sequence is: Read the exact Version `Epoch`, call
`Open(write)` on the exact Version or logical Resource, verify that the handle
pins the intended Version, re-Read that Version's `Epoch`, abort the staged
replacement if the value changed, otherwise `Write` the complete replacement
document and `Close`. `Write` and `EraseExisting` only stage bytes. A successful
`Close` commits once only when the final staged bytes differ from the committed
bytes at `Open`; it then increments the exact Version's `Epoch` and updates
`ModifiedAt`. A clean or rejected `Close`, an abandoned handle, or a
write-back-to-original sequence is silent.

Every logical Resource handle MUST remain pinned to the exact Version selected
at `Open`. A later default-Version switch affects only later opens. Logical and
exact opens MUST share the same exact-Version writer reservation and an
incarnation safeguard, so deletion and recreation of the same Version identity
cannot let a stale handle commit into the replacement Object.

For deletion, a client passes the current group or exact Version `Epoch`, or
the current logical Resource `MetaEpoch`, as `ExpectedEpoch`. If a non-zero
value does not equal the applicable value, the Method Call MUST fail with
`Bad_InvalidState`, delete nothing and produce no partial effects;
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
| `xid` | `Xid`; a Version uses the Resource `Xid` plus `/versions/<VID>`, and Resource Meta uses the Resource `Xid` plus `/meta` | `RegistryType`, `GroupType`, Resource, Version and Resource Meta entities |
| `epoch` | delegated `Epoch` for a Resource representation; exact `Epoch` for a Version; `MetaEpoch` for Resource Meta | `RegistryType`, `GroupType`, Resource, Version and Resource Meta entities |
| `name` | `Name` | all base entity types |
| `description` | `Description` | all base entity types |
| `documentation` | `Documentation` | all base entity types |
| `labels` | delegated `Labels` object (`AttributesType`) for a Resource representation; exact `Labels` for a Version; `MetaLabels` for Resource Meta | `RegistryType`, `GroupType`, Resource, Version and Resource Meta entities |
| `createdat` | delegated `CreatedAt` for a Resource representation; exact `CreatedAt` for a Version; `MetaCreatedAt` for Resource Meta | `RegistryType`, `GroupType`, Resource, Version and Resource Meta entities |
| `modifiedat` | delegated `ModifiedAt` for a Resource representation; exact `ModifiedAt` for a Version; `MetaModifiedAt` for Resource Meta | `RegistryType`, `GroupType`, Resource, Version and Resource Meta entities |
| event `source` URL | `EventSourceUrl` | `RegistryType`; REQUIRED only for event-capable server conformance (§9.3) |

Resource Meta is a first-class xRegistry entity, not a Version attribute or
merely a nested implementation object. The `Meta` prefix disambiguates its OPC
UA BrowseNames on the logical Resource from the normal Version Properties
delegated by that Resource. Dotted names such as `meta.epoch` are used only when
xRegistry represents a Resource and its Meta attributes in one document or in
an event `Changed` path.

The xRegistry attributes `self`, collection `url` attributes, collection
`count` attributes, `metaurl`, `versionsurl`, `versionscount`,
`defaultversionurl`, `isdefault`, `ancestor`, `<RESOURCE>` and
`<RESOURCE>base64` are serialization artifacts or domain/model attributes rather
than mandatory base Properties. A server MAY expose them as domain Properties,
but a client MUST be able to derive them from `Xid`, `ResourceId`, `VersionId`
, Browse results and the document bytes where possible.

Registry, group and version labels and extension attributes are enumerated by
Browsing `Labels` and Reading each `<Attribute>` Property Variable. Resource
Meta labels and extension attributes are enumerated through `MetaLabels`.
Clients add, update or remove values by calling the applicable container's
`AddAttribute` or `RemoveAttribute` Method with the epoch described in §4.5.1.
Both containers are deleted with their owning entity.

### 4.7. Supported operations discovery and pagination

A client discovers supported operations by browsing the target node for Methods,
by reading `Writable`, `UserWritable`, AccessLevel and UserAccessLevel
attributes of Variables, by reading the typed `CapabilitiesInfo` Variable or the
`Capabilities` `FileType` content, and by inspecting executable and
user-executable bits of Method nodes.

A server MUST NOT require a side-effecting operation for discovery. If a
FileTransfer Method, `CreateGroup`, `GetOrCreateGroup`, `CreateResource`,
`GetOrCreateResource`, an applicable `Labels` or `MetaLabels` object, or its
`AddAttribute` /`RemoveAttribute` Method is absent, non-executable or rejected
with `Bad_UserAccessDenied`, the corresponding xRegistry write capability is
not available to that client.

OPC UA Browse paginates large child sets through continuation points and
`BrowseNext`. A client that wants a page of collection entries calls Browse
with a requested maximum reference count and then calls `BrowseNext` until the
desired page is complete or no continuation point remains.

For file bytes, a client paginates through `Read(fileHandle, length)` and MAY
use `GetPosition` and `SetPosition` to implement random access. For labels, a
client browses `Labels` or `MetaLabels` and pages with normal Browse
continuation points where needed.

## 5. Registry operations

This section defines successful native OPC UA interaction patterns for xRegistry
entities. Error mapping is specified in §11.

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
preferably calls `GetOrCreateResource`, writes the document if supplied, writes
exact Version Properties or `Labels`, and writes Resource Meta Properties or
`MetaLabels` on the logical Resource according to the nested operation
semantics; strict creation uses `CreateResource`.

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
Method, where `ExpectedEpoch` can be omitted and `0` disables the check. The
Method deletes the group and everything it contains, including logical
Resources, their `Versions` containers, exact Versions, `Labels` and
`MetaLabels`. Deleting a collection subset is a sequence or server-defined
batch of `Delete(ExpectedEpoch)` Calls, one for each selected group child.

If an entity-specific `epoch` precondition is supplied for deletion, the client
MUST pass it as `ExpectedEpoch`. If `ExpectedEpoch` is non-zero and does not
equal the group's current `Epoch`, the Call MUST fail with `Bad_InvalidState`
and delete nothing; `ExpectedEpoch = 0` or omission disables the check.

### 5.10. Resource metadata and resource documents

Each resource collection entry is a logical `ResourceType`. Its normal Version
Properties, `Labels` and inherited FileTransfer Methods are a delegated view of
the selected default Version under its `Versions` component. Its
`MetaEpoch`, `MetaCreatedAt`, `MetaModifiedAt`, domain meta Properties and
`MetaLabels` are authoritative Resource Meta and are not delegated.

Each exact Version is a separate `ResourceType` under `Versions`. To access
exact Version metadata, a client uses Read or Write on `ResourceId`,
`VersionId`, `Format`, `ContentType`, `ExternalReference`, `ResourceUrl`,
`Xid`, `Epoch`, `Name`, `Description`, `Documentation`, `CreatedAt`,
`ModifiedAt`, domain Version Properties and `Labels`. To access its document,
the client uses `Open`, `Read`, optionally `GetPosition` and `SetPosition`,
`Write` when replacing the document, and `Close`.

The same FileTransfer Methods on the logical Resource select the current
default Version at `Open`. The returned handle remains pinned to that exact
Version until `Close`, even if default-version state changes meanwhile.

If a resource type's xRegistry model has `hasdocument = false`, document access
MUST be rejected with `Bad_NotReadable`, `Bad_InvalidState` or
`Bad_NotSupported`, and metadata access remains the normal entity
representation.

When a Resource or Version is serialized as its domain-specific document, the
bytes returned by `Read(fileHandle, length)` are the exact document bytes. If
the document is empty, `Read` returns zero bytes at end-of-file.

OPC UA has no need for transport headers to carry resource metadata. Clients
obtain the metadata by reading the Properties of the file before or after
reading bytes. Servers SHOULD keep `ContentType` and the inherited `MimeType`
consistent so generic FileTransfer clients can identify the media type.

If `ResourceUrl` is present and the document is external, `Open` MAY fail with
`Bad_NotReadable` or MAY return a local cached representation. In either case
the client can read `ResourceUrl` and `ExternalReference` to resolve the
external content as described in §10.

### 5.11. Listing resource collections

A client lists a resource collection by Browse over the `GroupType` folder to
return logical `ResourceType` children in the requested domain-specific
resource collection. Exact Version Objects are not children of the group and
MUST NOT appear in that collection Browse. xRegistry resource collections are
unordered maps keyed by id; OPC UA Browse returns children in a server-defined
order, so a client MUST NOT infer collection order from Browse position.

The serialized collection keys are `ResourceId` values and are available from
each logical Resource BrowseName. A client derives `versionscount` by Browsing
the Resource's `Versions` component, and derives `metaurl` and `versionsurl`
from the logical Resource `Xid`.

### 5.12. Creating and updating resources

A client creates or updates Resources through the owning `GroupType`. For each
resource key, the preferred one-shot path is
`GetOrCreateResource(ResourceId, VersionId, RequestFileOpen)` on the `GroupType`
, which returns the exact Version NodeId and `AssignedVersionId`, with
`Created = false` for an existing Version or `Created = true` for a newly
created Version. If `RequestFileOpen = true`, the returned write file handle is
already pinned to that exact Version and MAY be used immediately. A new
Resource causes its logical Resource, `Versions` component and first Version to
commit atomically in the same xRegistry operation. A new Version of an existing
Resource is created by passing its `ResourceId` with a new or server-assigned
`VersionId`. Strict create operations use
`CreateResource(ResourceId, VersionId, RequestFileOpen)` when an existing
`(ResourceId, VersionId)` MUST fail.

The retained `ResourceNodeId` output name denotes the exact Version NodeId; it
does not identify the logical Resource. `AssignedVersionId` is paired with that
NodeId and the requested `FileHandle`. A client discovers the logical Resource
separately by Browsing the domain resource collection for the child whose
BrowseName is `ResourceId`.

For default-Version metadata updates, the client MAY use the delegated
Properties and `Labels` on the logical Resource or target the selected exact
Version directly. Both paths update the exact Version using its `Epoch`. For
Resource Meta updates, the client writes Resource Meta Properties and calls
`MetaLabels.AddAttribute` /`MetaLabels.RemoveAttribute` on the logical Resource
using `MetaEpoch`. For document creation or replacement, the client writes the
complete document byte stream and sets `ContentType`, `Format`, `ResourceUrl`
and `ExternalReference` on the exact Version as applicable.

If the supplied `ResourceId` conflicts with the selected resource identifier,
the operation MUST fail with `Bad_InvalidArgument`. If supplied `VersionId`
creates a new version rather than replacing the default version, the operation
MUST follow §5.18.

### 5.13. Reading a resource document

A client reads the default resource document by resolving the logical
`ResourceType` for the selected `ResourceId`, calling `Open` for read,
repeatedly calling `Read`, and calling `Close`. At `Open`, the server selects
the current default exact Version and pins the handle to it. A later default
switch does not redirect that handle. The client MAY read the logical
Resource's delegated `Size`, `Writable`, `MimeType`, `LastModifiedTime`,
`ContentType`, `ResourceId`, `VersionId` and `Epoch` to reproduce the Resource
response metadata. Resource Meta is read from the logical Resource's
`MetaEpoch`, `MetaLabels`, `MetaCreatedAt`, `MetaModifiedAt` and domain meta
Properties.

If `ResourceUrl` or `ExternalReference` indicates external content, the server
MAY either redirect by metadata by returning readable `ResourceUrl`
/`ExternalReference` while `Open` fails with a suitable StatusCode, or serve
cached bytes from the local file. The choice MUST be documented in
`Capabilities`.

### 5.14. Reading and updating resource metadata

A client reads a Resource representation from the logical Resource. Version
attributes come from its delegated normal Properties and `Labels`; Resource
Meta comes from its authoritative `MetaEpoch`, `MetaCreatedAt`,
`MetaModifiedAt`, `MetaLabels` and domain meta Properties. Neither operation
requires reading file bytes.

A client updates default-Version attributes by Writing Version Properties and
calling `Labels.AddAttribute` or `Labels.RemoveAttribute` with the Version's
`Epoch`. It updates Resource Meta attributes by Writing meta Properties and
calling the corresponding Method on `MetaLabels` with `MetaEpoch`. A Resource
Meta label change MUST increment `MetaEpoch` and update `MetaModifiedAt`, and
MUST NOT change Version `Epoch` or `ModifiedAt` unless the same interaction also
changes Version attributes.

Updating an existing Version's Properties, `Labels` or document bytes does not
update Resource Meta. Resource Meta changes only when its own attributes change,
when a Version is added or removed, or when default-Version state changes.

The resource-level meta view is a serialization view over authoritative
Properties on the logical Resource. The base model does not define a separate
`Meta` Object; `MetaEpoch`, `MetaCreatedAt`, `MetaModifiedAt` and `MetaLabels`
separate Resource Meta from the delegated Version `Epoch`, `CreatedAt`,
`ModifiedAt` and `Labels`.

Base Properties such as `Epoch`, `CreatedAt`, `ModifiedAt`, `MetaEpoch`,
`MetaCreatedAt` and `MetaModifiedAt` are normally server-managed and MUST NOT be
directly writable unless the server explicitly allows administrative writes.

Changing default-version state uses the domain Property or Method defined for
the xRegistry `defaultversionid` meta attribute. A successful change MUST
increment `MetaEpoch` and update `MetaModifiedAt`. It changes the delegated
normal Properties and the target selected by future logical Resource opens. It
MUST NOT change the logical Resource NodeId or `Xid`, any exact Version NodeId
or `Xid`, or the deletion role of any node.

Deleting the meta view is not supported. The server MUST reject attempts to
delete the meta view with `Bad_NotSupported` or `Bad_InvalidArgument`.
Individual mutable meta attributes, including entries in `MetaLabels`, MAY be
reset through update processing if the domain model supports them.

### 5.15. Replacing a resource document

Replacing a Resource document is create-if-needed plus complete replacement of
the selected default Version. If the logical Resource does not exist, the
client preferably calls `GetOrCreateResource` on the parent group, or
`CreateResource` when existing Resources MUST fail. It then opens the logical
Resource or returned exact Version for writing, sets position to zero where
needed, writes the complete new byte stream, closes the handle, and writes or
validates exact Version metadata Properties.

Partial patching of document bytes is not defined. A client that wants to change
document content MUST provide a complete replacement document.

The FileTransfer `Write` Calls and `EraseExisting` open mode only stage the
replacement. The logical handle pins the default Version selected at `Open` and
uses that exact Version's writer reservation and incarnation safeguard. A
successful `Close` commits once only when the final staged bytes differ from
the committed bytes at `Open`; it then increments that Version's `Epoch` and
updates its `ModifiedAt`. A clean or rejected `Close`, an abandoned handle, or
a write-back-to-original sequence is silent.

### 5.16. Deleting resources

Deleting a selected resource uses the resource's own
`Delete(ExpectedEpoch: UInt32)` Method, where `ExpectedEpoch` can be omitted and
`0` disables the check. A non-zero `ExpectedEpoch` MUST equal the logical
Resource's current `MetaEpoch`, not the delegated default Version's `Epoch`.
The Method atomically deletes the logical Resource, its `Versions` component,
all exact Versions and all owned `Labels` and `MetaLabels`.

Deleting a resource collection subset is a sequence or server-defined batch of
`Delete(ExpectedEpoch)` Calls, one for each selected logical Resource. A server
MUST NOT retain any exact Version from a deleted Resource as a detached or
group-level alias.

### 5.17. Listing versions

A client lists Versions by resolving the logical Resource's
`ResourceVersionsType` component with BrowseName `Versions` and Browsing its
exact `ResourceType` children. xRegistry version collections are unordered maps
keyed by `VersionId`; OPC UA Browse returns children in a server-defined order,
and version order is conveyed by attributes such as `ancestor`, `createdat` and
`defaultversionid`, not by container position. Each exact Version BrowseName is
its `VersionId`, which supplies the serialized collection key.

### 5.18. Creating and updating versions

A client creates or updates a Version by resolving the exact `ResourceType`
under the logical Resource's `Versions` component. If absent and creation is
allowed, it calls `GetOrCreateResource` on the group with the resource and
version identifiers, or `CreateResource` for strict creation. The returned
`ResourceNodeId` is the exact Version NodeId and `AssignedVersionId` is the
assigned identifier. The exact Version BrowseName MUST be that
`versionid`.

For partial metadata updates, only named version attributes are written. For
full version representations, omitted mutable attributes are reset or removed
according to xRegistry rules. Extension attributes and labels on `ResourceType`
MAY be managed through `Labels.AddAttribute` and `Labels.RemoveAttribute` on the
exact Version's `Labels` `AttributesType` object where supported.

For document-bearing Versions, the client writes the Version document if
supplied and validates `ResourceId` and `VersionId`. The server updates
default-version state according to xRegistry rules and domain model
capabilities.

Adding a Version to an existing Resource MUST increment the Resource's
`MetaEpoch` and update `MetaModifiedAt`, whether or not the new Version becomes
the default. Modifying an existing Version updates that Version's `Epoch` and
`ModifiedAt` but MUST NOT by itself change the Resource's `MetaEpoch` or
`MetaModifiedAt`. If the same interaction also changes Resource Meta or the
default Version, those Resource Meta changes follow §5.14.

If an empty version map is supplied for a non-existent resource, the server MUST
reject it with `Bad_InvalidArgument`, corresponding to xRegistry
`missing_versions`.

The response representation is obtained by reading back the created or updated
exact Version's Properties and, for document mode, by reading back its file
bytes if needed.

### 5.19. Reading a version

A client reads a Version document with `Open` /`Read`/`Close` on the exact
`ResourceType` under the logical Resource's `Versions` component whose
BrowseName and `VersionId` are the selected version identifier.

A client reads Version metadata by Reading that exact Version's Properties. Its
`Xid` MUST be the logical Resource `Xid` plus `/versions/<VID>`.

### 5.20. Replacing a version document

Replacing a Version document is create-if-needed plus complete replacement of
the exact Version bytes using `GetOrCreateResource` or strict
`CreateResource`, `Open`, `SetPosition`, `Write` and `Close`.

Partial patching of version document bytes is not defined.

The FileTransfer `Write` Calls and `EraseExisting` open mode only stage the
replacement. Exact and logical opens share the same writer reservation and
incarnation safeguard for this Version. A successful `Close` commits once only
when the final staged bytes differ from the committed bytes at `Open`; it then
increments that Version's `Epoch` and updates its `ModifiedAt`. A clean or
rejected `Close`, an abandoned handle, or a write-back-to-original sequence is
silent.

### 5.21. Deleting versions

Deleting a selected Version uses the exact Version Object's own
`Delete(ExpectedEpoch: UInt32)` Method, where `ExpectedEpoch` can be omitted and
`0` disables the check. A non-zero value MUST equal that Version's `Epoch`.
The Method removes only that exact Version. Deleting a Versions collection
subset is a sequence or server-defined batch of `Delete(ExpectedEpoch)` Calls
targeting exact Versions selected by `VersionId`.

A server MUST reject deletion of the last remaining version of a resource if the
xRegistry model requires every resource to have at least one version. A server
MUST also reject deletion of a default version unless it can atomically select a
new default or the request explicitly sets one through a supported flag or meta
update.

If the version is the default version, the server MUST either reject the delete
with `Bad_InvalidState` or update default-version state according to xRegistry
and domain rules.

Removing a Version from a surviving Resource MUST increment the Resource's
`MetaEpoch` and update `MetaModifiedAt`. This applies whether or not deletion
selects a new default Version. It does not increment any surviving Version's
`Epoch` unless that Version's own attributes are also modified.

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
| `epoch` | Pass `ExpectedEpoch` to `Labels.AddAttribute` and `Labels.RemoveAttribute`; pass Version/group `Epoch` or Resource `MetaEpoch` to `Delete`; for document replacement, use the epoch-matched sequence in §4.5.1 |
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
Browse results require additional Reads. For a label-value predicate, the
client browses the candidate entity's applicable `Labels` or `MetaLabels`
`AttributesType` object and reads only the matching `<Attribute>` Property
Variable where present; for fixed or domain Properties such as `Name`,
`CreatedAt` or `ModifiedAt`, the client reads those Properties for the
remaining candidates and evaluates the predicate locally.

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
browsing `GroupType` children, logical `ResourceType` children and exact
Versions under each `Versions` component, then serializing them into the parent
entity representation.

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
mode. A logical Resource provides the Resource and Resource Meta views, while
an exact Version provides the Version view.

### 6.6. Pagination and ranges

Collection pagination maps to Browse continuation points. Document range
retrieval maps to the `length` argument of `Read`, to repeated reads from the
current file position, and to `SetPosition` for random access. Label enumeration
maps to Browse of `Labels` or `MetaLabels` and continuation points where needed.

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
epochs as `UInt32`, and labels as `String` Property Variables under `Labels` or
Resource Meta `MetaLabels`. Federation targets are `ExpandedNodeId`, and
document bytes are `ByteString` chunks returned by `Read` on `FileType`.

When a complete xRegistry entity is serialized for export or for a protocol
bridge, the base Property BrowseNames are converted to their xRegistry
lower-case attribute names. Domain Properties are serialized according to the
domain registry model.

A server MUST preserve unknown extension attributes that it accepts, using
domain extension Properties or Property Variables under the applicable
`Labels` or `MetaLabels` `AttributesType` object. If the server cannot preserve
an accepted extension attribute, it MUST reject the update rather than silently
losing information.

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

For a logical Resource `ResourceType`, serialization reads delegated
`ResourceId`, `VersionId`, `Format`, `ContentType`, `ExternalReference`,
`ResourceUrl`, `Epoch`, `CreatedAt`, `ModifiedAt`, `Labels` and other
default-Version Properties. It adds authoritative Resource Meta from
`MetaEpoch`, `MetaCreatedAt`, `MetaModifiedAt`, `MetaLabels` and domain meta
Properties on the logical Resource. It serializes the Versions collection by
Browsing exact `ResourceType` children under `Versions`.

For an exact Version, serialization reads the same normal Version Properties
directly from that Object. Document serialization uses FileTransfer on the
logical Resource for the selected default Version or on an exact Version, and
places the bytes in the xRegistry `<RESOURCE>` or `<RESOURCE>base64` attribute
according to the xRegistry document rules and selected encoding.

The inverse import process creates or updates the same subtree: create group
folders, atomically create each new logical Resource and first exact Version,
create later exact Versions under `Versions`, write document bytes, write
mapped Properties, update exact Version `Labels` and logical Resource
`MetaLabels`, and let the server auto-bootstrap `Xid`, Version `Epoch` /
`CreatedAt` /`ModifiedAt`, and Resource Meta `MetaEpoch` /`MetaCreatedAt` /
`MetaModifiedAt` where they are not explicitly supplied or are server-managed.

Serialization MUST preserve the three-representation symmetry described by the
xRegistry primer and by *OPC UA —
xRegistry*
§4.2 and §7: an entity has the same `Xid` and identity whether reached as a
file, through OPC UA services, or in an exported xRegistry document.

## 9. Events

### 9.1. Native event model and canonical types

An event-capable OPC UA xRegistry server reports xRegistry changes as native
OPC UA Events. It MUST NOT encapsulate a CloudEvent or another protocol payload
as the event body. The concrete EventTypes and their fields are defined by
Version 0.6.0 of the OPC UA — xRegistry companion model at commit
`d3399fca025025a73e5a6b599f850a81d985c060`. Each canonical xRegistry event
`type` maps to the following concrete leaf EventType:

| Canonical xRegistry type | OPC UA EventType | Additional fields |
|---|---|---|
| `io.xregistry.registry.created` | `RegistryCreatedEventType` | `Epoch` |
| `io.xregistry.registry.updated` | `RegistryUpdatedEventType` | `Epoch`, `Changed` |
| `io.xregistry.registry.deleted` | `RegistryDeletedEventType` | none |
| `io.xregistry.model.updated` | `ModelUpdatedEventType` | none |
| `io.xregistry.modelsource.updated` | `ModelSourceUpdatedEventType` | none |
| `io.xregistry.capabilities.updated` | `CapabilitiesUpdatedEventType` | `Changed` |
| `io.xregistry.group.created` | `GroupCreatedEventType` | `Epoch` |
| `io.xregistry.group.updated` | `GroupUpdatedEventType` | `Epoch`, `Changed` |
| `io.xregistry.group.deprecated` | `GroupDeprecatedEventType` | none |
| `io.xregistry.group.undeprecated` | `GroupUndeprecatedEventType` | none |
| `io.xregistry.group.deleted` | `GroupDeletedEventType` | none |
| `io.xregistry.resource.created` | `ResourceCreatedEventType` | `Epoch`, `MetaEpoch` |
| `io.xregistry.resource.updated` | `ResourceUpdatedEventType` | `Epoch`, `MetaEpoch`, `Changed` |
| `io.xregistry.resource.deprecated` | `ResourceDeprecatedEventType` | none |
| `io.xregistry.resource.undeprecated` | `ResourceUndeprecatedEventType` | none |
| `io.xregistry.resource.deleted` | `ResourceDeletedEventType` | none |
| `io.xregistry.version.created` | `VersionCreatedEventType` | `Epoch` |
| `io.xregistry.version.updated` | `VersionUpdatedEventType` | `Epoch`, `Changed` |
| `io.xregistry.version.deleted` | `VersionDeletedEventType` | none |

The concrete leaf EventType is the native representation of the canonical
`type`; an event consumer determines the canonical type from `EventType` and
the companion model type hierarchy.

This binding uses the merged xRegistry Events specification at merge commit
`66ee31e47fbadff6ab982ae1516f7d9065e46b64`, subject to these binding
corrections:

- The `version.update` token in the Resource `updated` rule means
  `version.updated`. A server MUST NOT define or emit a `version.update` alias.
- `resource.deprecated` is generated when `meta.deprecated` is created or
  changed. Removal generates `resource.undeprecated`, not
  `resource.deprecated`.
- `Changed` MUST NOT occur on any `deprecated` or `undeprecated` event. The
  companion group or resource `updated` event carries the changed metadata.

An event-capable server claiming the `XREG-Events` conformance unit MUST
implement every event that the xRegistry Events specification, as interpreted
by these corrections, says MUST be generated for every mutation it supports. It
SHOULD generate `registry.created` and `registry.deleted` when it exposes
registry lifecycle, and SHOULD generate descendant `deleted` events when an
entire registry is deleted, matching their status in that specification.
Recursive deletion of a group or resource is different: all REQUIRED descendant
resource and version events remain part of the applicable MUST event set.
Supporting only a subset of that MUST event set does not conform to
`XREG-Events`.

### 9.2. Event field mapping

The common event fields map as follows:

| xRegistry event field | OPC UA field | Mapping |
|---|---|---|
| `type` | `EventType` | NodeId of the concrete leaf EventType in §9.1 |
| `id` | `EventId` | The `BaseEventType.EventId`; when serialized as a CloudEvent, encode its bytes using standard Base64 as the CloudEvents string `id` |
| native source | `SourceNode`, `SourceName` | Deterministic materialized OPC UA entity defined below |
| `source` | `SourceUrl` | REQUIRED absolute xRegistry source URL copied from the registry's `EventSourceUrl` |
| `subject` | `Subject` | The subject entity's xRegistry `xid` |
| `time` | `Time` | `BaseEventType.Time`, shared by every event from one logical interaction |
| `epoch` | `Epoch` | Subject entity's final `epoch` value |
| `meta.epoch` | `MetaEpoch` | Subject resource's final `meta.epoch` value |
| `changed` | `Changed` | One-dimensional OPC UA `String` array |
| `xregcorrelationid` | `CorrelationId` | OPTIONAL interaction identifier, subject to the response rule below |

`SourceNode` and `SourceName` carry native AddressSpace provenance; they do not
replace `SourceUrl` or `Subject`. Their values are determined as follows:

- Registry, model, modelsource and capabilities events use the registry root.
  `Subject` distinguishes `/`, `/model`, `/modelsource` and `/capabilities`.
- A group event uses the corresponding `GroupType` node.
- A resource event uses the corresponding logical `ResourceType` node.
- A version event uses the corresponding exact Version `ResourceType` node.
- A Resource-created event and its REQUIRED first-Version-created event use the
  same `Time` but distinct `SourceNode`, `SourceName` and `Subject` values.

For a deleted event, `SourceNode` and `SourceName` retain the values that
identified the deleted entity immediately before commit, even though that node
is no longer present when the event is delivered. Delivery is routed after
commit through the nearest surviving notifier and does not change those source
fields.

`Epoch` MUST be present on `created` and `updated` events for registries,
groups, resources and versions, and MUST contain the subject's value at the end
of the interaction. It MUST be absent from `deleted`, `deprecated` and
`undeprecated` events and from `model.updated`, `modelsource.updated` and
`capabilities.updated`. The logical Resource delegates its normal Version
Properties, so `Epoch` on a resource event is the selected default Version's
`Epoch`, including the newly selected Version after a default-Version switch.

`MetaEpoch` MUST be present on `resource.created` and `resource.updated` and
MUST contain the distinct Resource Meta `MetaEpoch` value at the end of the
interaction. It MUST be absent from every other event. A resource `created` or
`updated` event contains both `Epoch` and `MetaEpoch` even if only one changed.
Adding or removing a Version changes `MetaEpoch`; modifying a Version does not,
unless the same interaction also changes Resource Meta.

`Changed` exists only on concrete `updated` EventTypes. When present, it MUST
contain the union of attribute names changed during the interaction, using
xRegistry dot notation for nested resource metadata. It MUST NOT be populated
on `model.updated` or `modelsource.updated`. It is OPTIONAL on other updated
events and SHOULD be populated unless disclosure is inappropriate. Document
changes use the domain resource singular attribute name, not its `base64`
serialization variant. The xRegistry Events specification defines exactly
which names are REQUIRED for parent-collection, default-version and
deprecation changes.

The base binding does not provide a response field for an interaction
correlation identifier. Therefore `CorrelationId` MUST be absent for base
operations. A domain extension MAY populate it only when the extension also
returns the same identifier in the operation response, so the initiating
client can correlate the response with resulting events.

### 9.3. Event source URL

The companion model defines `EventSourceUrl` on `RegistryType`. It is the
configuration source for the REQUIRED event `SourceUrl` and MUST be an absolute
URL to the xRegistry root such that removing a trailing `/` and appending a
`Subject` produces the absolute URL of that subject.

`EventSourceUrl` is REQUIRED only when the server claims event-capable server
conformance. It is not REQUIRED for read-only, writable or export-capable
conformance. It is independent of the OPC UA endpoint URL, `ServerUri`,
NodeIds, BrowsePaths, `ExternalReference`, `ResourceUrl`, and all native entity
identity. Changing an endpoint or moving the AddressSpace therefore does not
implicitly change `EventSourceUrl`, and the value MUST NOT be used to resolve a
native OPC UA node.

### 9.4. Interaction and emission rules

Each successful xRegistry domain mutation Method Call, excluding inherited
FileTransfer Methods, is one logical interaction. Each successful Write Service
request that changes one or more entity values is one logical interaction.
Each post-startup reconciliation batch is also one logical interaction. All
events from one interaction MUST have the same `Time`.

FileTransfer `Write` Calls and `EraseExisting` only stage document bytes. One
successful byte-different `Close` commits the staged bytes and is one logical
interaction. Byte difference is measured against the committed bytes at
`Open`. Separate Property Writes and server-managed metadata changes do not
make `Close` dirty. Only that successful dirty `Close` increments the pinned
exact Version's `Epoch` and updates `ModifiedAt`. A clean or rejected `Close`,
an abandoned handle, or a write-back-to-original sequence leaves both unchanged
and emits no event.

A logical Resource handle pins the exact Version selected at `Open`; a later
default-Version switch affects only later opens. Logical and exact paths share
the same writer reservation and Version-incarnation safeguard.

`CreateResource`, or `GetOrCreateResource` with `Created = true`, is the
interaction that atomically commits the logical Resource, `Versions` container
and first exact Version structural identities, `Xid` values, initial epochs and
timestamps. The Resource and Version `created` events have the same `Time` but
their respective logical Resource and exact Version sources and subjects. They
MUST NOT be deferred to, or coalesced with, a later FileTransfer `Close`. If the
Method also returns a writable `FileHandle`, a later dirty `Close` is a
separate interaction. It generates the applicable `version.updated` event and,
when the Version is the selected default, `resource.updated` for the document
bytes and derived fields changed by the close. It MUST NOT repeat the earlier
`created` events.

Initial projection of persisted xRegistry state into the AddressSpace is
silent. A failed operation, a no-op update, a clean FileTransfer `Close`, or an
idempotent get-or-create operation that returns an existing unchanged entity
MUST emit no event. Reconciliation after startup emits events only for changes
committed by the reconciliation batch.

Within one interaction, the server MUST emit no more than one event with the
same canonical type and `Subject`. It MUST also emit no more than one of
`created`, `updated` or `deleted` for one `Subject`; when more than one action
occurred, precedence is `deleted`, then `created`, then `updated`. Attribute
names from repeated updates are merged into the one `Changed` array.

The server MUST determine the complete event set from the committed result
before reporting any event. Recursive deletion reports version leaves before
their resource containers, resources before their group containers, and groups
before the registry event. Events are reported only after the deletion commits,
through a notifier that survives the deletion. Event payloads MUST reflect the
committed result and MUST NOT expose a partial intermediate state.

### 9.5. Event notification topology

An event-capable server MUST set the `SubscribeToEvents` bit in the
`EventNotifier` Attribute of each event-reporting registry, group and
logical Resource and exact Version Object. It MUST expose notifier paths using
`HasNotifier` from the Server Object to each `RegistryType`, from a registry to
its `GroupType` children, from a group to its logical Resource children, and
from a logical Resource to its exact Version children. `Versions` MAY be an
organizational component only and need not be an event notifier or appear in
the notifier chain. Subtypes MAY add intermediate notifier Objects if the
Server-to-Version path specified above remains available. While the registry root
exists, applicable descendant events are available to event MonitoredItems on
the Server Object and registry root. Availability remains subject to the
MonitoredItem's `EventFilter`, MonitoringMode, queue size and discard policy,
and to normal Subscription publishing and lifetime semantics.

Events caused by deletion of a monitored notifier are reported through the
nearest surviving ancestor notifier: a Version deletion uses its logical
Resource, Resource deletion uses its group, group deletion uses its registry,
and registry deletion uses the Server Object. Recursive deletion reports all
deleted events through the nearest survivor of the whole interaction. A client
that requires `registry.deleted`, or descendant `deleted` events caused by
deletion of an entire registry, MUST monitor the Server Object because the
registry root does not survive that interaction.

The companion model's `GeneratesEvent` References declare which concrete event
types can be generated by `RegistryType`, `GroupType` and `ResourceType`.
Servers MUST preserve those declarations on domain subtypes for every supported
mutation. Clients discover event capability by Browsing the notifier hierarchy,
reading `EventNotifier`, following `GeneratesEvent`, and resolving concrete
EventType NodeIds from the companion model.

### 9.6. Subscription, discovery and filtering

A client creates an event subscription with `CreateSubscription`, then calls
`CreateMonitoredItems` for the Server Object, registry root or a narrower
notifier, monitoring its `EventNotifier` Attribute in Reporting mode with an
`EventFilter`. It receives notifications with `Publish`, acknowledges sequence
numbers in subsequent Publish requests, and MAY use `Republish` while the
notification remains in the Subscription retransmission queue. The client
SHOULD call `DeleteMonitoredItems` and `DeleteSubscriptions` when finished;
closing the Session performs the standard OPC UA cleanup.

An `EventFilter` commonly selects `EventId`, `EventType`, `SourceNode`,
`SourceName`, `Time`, `SourceUrl`, `Subject`, `Epoch`, `MetaEpoch`, `Changed`
and `CorrelationId`. Example where clauses include:

- `OfType(<ResourceUpdatedEventType NodeId>)` for resource updates;
- `Equals(Subject, "/dirs/d1/files/f1")` for one xRegistry subject; and
- `GreaterThan(Epoch, 41)` combined with `OfType` for an EventType that has
  `Epoch`.

OPC UA does not define a portable ContentFilter operator for unordered array
membership. To select a change such as `name`, a client selects `Changed`,
restricts the event set with `OfType` and other scalar clauses, and tests array
membership locally. A server MAY advertise an extension for server-side array
membership filtering, but a conforming client MUST NOT depend on one. Since
`Changed` order is unspecified, an `IndexRange` is not a portable substitute.

### 9.7. Delivery lifetime and replay

This binding does not require event history, durable replay or delivery after a
Subscription is deleted or expires. Standard OPC UA Subscription queues,
sequence numbers, acknowledgements and `Republish` govern live delivery and
retransmission. `Republish` is not an xRegistry business-event replay service.
A server MAY provide Event History through standard OPC UA historical access or
a domain extension, but clients MUST discover and use that capability
separately.

## 10. Federation

Federation is realized by `ExternalReference` and `ResourceUrl` on
`ResourceType`, as defined by the xRegistry primer, xRegistry core
specification, and *OPC UA —
xRegistry*
§8 and Annex B.

`ExternalReference` is an `ExpandedNodeId`. Its `ServerUri` identifies the
remote OPC UA server that hosts the referenced registry, and its `NamespaceUri`
plus identifier identify the remote resource node independently of the server's
local namespace indexes.

`ResourceUrl` is the xRegistry `<RESOURCE>url` string. It MAY contain an OPC UA
endpoint/browse-path convention for another OPC UA registry, or another URL for
a registry hosted behind a non-OPC-UA registry API.

To resolve a federated OPC UA Resource or Version, a client reads
`ExternalReference`; if `ServerUri` is local or empty it resolves the target in
the local AddressSpace, otherwise it discovers or connects to the remote
endpoint, maps the `NamespaceUri` to the remote namespace index, resolves the
target NodeId or BrowsePath, and reads the remote logical Resource or exact
Version using the same operations as for a local node.

To resolve a Resource federated to a non-OPC-UA API-hosted registry, a client
or gateway uses `ResourceUrl` as the external locator and treats the remote
bytes and metadata as the representation of the same xRegistry identity
carried by `Xid`, `ResourceId` and, for an exact Version, `VersionId`. The
external authority identifies the serving endpoint, not the entity identity.

A server MAY expose local proxy Resource and Version Objects for a federated
Resource. Such proxies MUST preserve the distinct hierarchy and retain the
remote entity identity in `Xid`, `ResourceId` and, for exact Versions,
`VersionId`. They MUST NOT treat the local endpoint identity as part of the
entity identity.

## 11. Error handling

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
| `ExpectedEpoch` does not match `Epoch` for a group, exact Version or `Labels` Method, or does not match `MetaEpoch` for a logical Resource deletion or `MetaLabels` Method | `Bad_InvalidState` |
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

## 12. Conformance

A server conforms to the read-only OPC UA xRegistry API if it exposes a
`RegistryType` root or domain subtype, exposes groups as `GroupType` or
subtypes, exposes each logical Resource as a `ResourceType` or domain subtype,
exposes its typed `ResourceVersionsType` component named `Versions`, and
exposes each exact Version below it as the same Resource subtype. It MUST
support Browse, Read and `Open` /`Read`/`Close` sufficient to retrieve registry
metadata, collections and Resource or Version documents. A server implementing
Version 0.6.0 of the companion model MUST NOT expose server-side aliases for
the Version 0.5 flat layout.

A server conforms to the writable OPC UA xRegistry API if, in addition to
read-only conformance, it supports the applicable creation and mutation
operations (`CreateGroup`, `GetOrCreateGroup`, `CreateResource`,
`GetOrCreateResource`, `Delete`, and `AddAttribute` /`RemoveAttribute` with
`ExpectedEpoch` on each applicable `Labels` or `MetaLabels` container), writable
Properties, and `Open` /`Write`/`Close` on `ResourceType`, `Capabilities` and
`Model` where document replacement is mutable. Logical and exact Version opens
MUST share exact-Version writer reservations and incarnation safeguards, and
logical handles MUST remain pinned to the Version selected at `Open`.

A server conforms to the export-capable OPC UA xRegistry API if it implements
the request-flag mappings it advertises in `Capabilities`, including Browse
continuation point pagination, Browse-result filtering, and export serialization
that follows the xRegistry document shape.

A server conforms to the event-capable OPC UA xRegistry API by claiming the
`XREG-Events` conformance unit. It MUST expose `EventSourceUrl`, the notifier
hierarchy and `GeneratesEvent` declarations, generate every event that the
xRegistry Events specification, as interpreted by the binding corrections in
§9.1, says MUST be generated for every supported mutation, and support standard
OPC UA event subscription and delivery as specified in §9. The specification's
SHOULD events retain that status, including registry lifecycle events and
descendant events on whole-registry deletion.
REQUIRED descendants of group and resource recursive deletion remain MUST
events. `XREG-Events` is OPTIONAL and is not REQUIRED for read-only, writable
or export-capable conformance.

A baseline client conforms if it can select a `RegistryType` root, resolve
xRegistry `xid` s or relative identifiers to AddressSpace nodes, use
Browse/Read/FileTransfer operations for reading, use Write/Call operations for
advertised write capabilities, interpret StatusCodes according to §11, and
serialize or consume xRegistry document representations according to §8. An
updated client MAY implement the documented Version 0.5 flat-layout fallback,
but MUST prefer and exclusively use the distinct hierarchy when `Versions` is
present.

A client conforms to the event-capable OPC UA xRegistry API if it can discover
an event notifier, create and maintain an event MonitoredItem, resolve all
concrete EventTypes in §9.1, interpret the fields and interaction rules in §9,
and clean up or recover its Subscription using the standard OPC UA Services.
Event-capable client conformance is OPTIONAL and is not REQUIRED for baseline
client conformance.

A conforming implementation MUST NOT require any node or Method name that is not
defined by *OPC UA —
xRegistry*,
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
| Observe xRegistry changes | Create an event Subscription and MonitoredItem on the Server, registry or narrower notifier (§9) | No delivery mechanism is defined by the HTTP binding; the xRegistry Events specification is transport independent |
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
| Process resource collections under a group | Resolve/create logical Resources and exact Versions, then Write Version documents/Properties/`Labels` or logical Resource Meta Properties/`MetaLabels` (§5.7) | `POST /<GROUPS>/<GID>` |
| Delete a group | Call `Delete(ExpectedEpoch)` on the selected `GroupType` node (§5.9) | `DELETE /<GROUPS>/<GID>` |
| List a resource collection | Browse logical `ResourceType` children under the group (§5.11) | `GET /<GROUPS>/<GID>/<RESOURCES>` |
| Create or update a resource collection subset | Use `GetOrCreateResource` or strict `CreateResource`; for a new Resource the logical Resource and first exact Version commit atomically, and the Method returns the exact Version NodeId (§5.12) | `PATCH /<GROUPS>/<GID>/<RESOURCES>`, `POST /<GROUPS>/<GID>/<RESOURCES>` |
| Delete a resource collection subset | Call `Delete(ExpectedEpoch)` with each logical Resource's `MetaEpoch` (§5.16) | `DELETE /<GROUPS>/<GID>/<RESOURCES>` |
| Read a resource document | `Open`/`Read`/`Close` on the logical Resource, which pins and delegates to its selected default Version (§5.13) | `GET /<GROUPS>/<GID>/<RESOURCES>/<RID>` |
| Read resource metadata | Read delegated Version Properties/`Labels` and authoritative Resource Meta Properties/`MetaLabels` from the logical Resource (§5.14) | `GET /<GROUPS>/<GID>/<RESOURCES>/<RID>$details` |
| Replace or partially update resource metadata | Write delegated Version Properties/`Labels` with `Epoch` and logical Resource Meta Properties/`MetaLabels` with `MetaEpoch` (§5.14) | `PUT /<GROUPS>/<GID>/<RESOURCES>/<RID>$details`, `PATCH /<GROUPS>/<GID>/<RESOURCES>/<RID>$details` |
| Replace a resource document | Create if needed, then `Open`/`SetPosition`/`Write`/`Close` on the logical Resource or returned exact Version (§5.15) | `PUT /<GROUPS>/<GID>/<RESOURCES>/<RID>` |
| Create or update a resource version | Create/update an exact Version under the logical Resource's `Versions` component using `GetOrCreateResource` or strict `CreateResource` (§5.18) | `POST /<GROUPS>/<GID>/<RESOURCES>/<RID>` |
| Delete a resource | Call `Delete(ExpectedEpoch)` on the logical Resource using `MetaEpoch`, atomically deleting it and all exact Versions (§5.16) | `DELETE /<GROUPS>/<GID>/<RESOURCES>/<RID>` |
| Read resource meta entity | Read `MetaEpoch`, `MetaCreatedAt`, `MetaModifiedAt`, `MetaLabels` and domain meta Properties on the logical Resource (§5.14) | `GET /<GROUPS>/<GID>/<RESOURCES>/<RID>/meta` |
| Replace or partially update resource meta entity | Write logical Resource meta Properties or `MetaLabels` using `MetaEpoch`, or change domain default-version state (§5.14) | `PUT /<GROUPS>/<GID>/<RESOURCES>/<RID>/meta`, `PATCH /<GROUPS>/<GID>/<RESOURCES>/<RID>/meta` |
| Delete resource meta entity | Reject as unsupported or reset individual mutable meta attributes when domain-defined (§5.14) | `DELETE /<GROUPS>/<GID>/<RESOURCES>/<RID>/meta` |
| List versions | Browse exact Version `ResourceType` children under the Resource's `Versions` component (§5.17) | `GET /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions` |
| Create or update version collection subset | Resolve/create exact Versions with `GetOrCreateResource` or strict `CreateResource`, then Write Version documents, Properties or `Labels` entries (§5.18) | `PATCH /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions`, `POST /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions` |
| Delete version collection subset | Call `Delete(ExpectedEpoch)` with each selected exact Version's `Epoch` (§5.21) | `DELETE /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions` |
| Read a version document | `Open`/`Read`/`Close` on the selected exact Version (§5.19) | `GET /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>` |
| Read version metadata | Read Properties of the selected exact Version (§5.19) | `GET /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>$details` |
| Replace or partially update version metadata | Write version Properties and optionally call `Labels.AddAttribute`/`Labels.RemoveAttribute` (§5.18) | `PUT /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>$details`, `PATCH /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>$details` |
| Replace a version document | Create if needed, then `Open`/`SetPosition`/`Write`/`Close` on the exact Version (§5.20) | `PUT /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>` |
| Delete a version | Call `Delete(ExpectedEpoch)` on the exact Version using its `Epoch` (§5.21) | `DELETE /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>` |

[xRegistry Core]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html
[xRegistry HTTP]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/http.html
[xRegistry primer]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/primer.html
