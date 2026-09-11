# xRegistry Directory Mapping Format

<!-- words: modelbase resolvedmodelsource sha256 symlinks reparse xids -->
<!-- words: modelsource hasdocument defaultversionid defaultversionsticky -->
<!-- words: ancestorid isdefault formatversion href readonly ximportresources -->
<!-- words: casefold subtrees filesystem filenames bytecode smudge -->
<!-- words: federationerror namespace namespaces py reserialized -->
<!-- words: standalone workingdrafts -->
<!-- words: gitattributes checkout -->
<!-- words: formatvalidated compatibilityvalidated -->
<!-- words: filesystems readme -->
<!-- words: assetid documentid walkthrough -->

## Abstract

This specification maps an existing directory to a read-only xRegistry for
the [Git](git.md) and [File](file.md) federation bindings. Add `registry.json`
and the referenced metadata documents without reorganizing the directory's
existing files. Versions reference those files through paths inside the
selected root. Storage paths are not entity identifiers.

**Status:** Unreleased working draft, format version `1`. This document is
not part of a released xRegistry specification.

## Table of Contents

- [Scope and Conventions](#scope-and-conventions)
- [Motivation and Use](#motivation-and-use)
- [Worked Example: Map One Existing File](#worked-example-map-one-existing-file)
- [Root and Storage Paths](#root-and-storage-paths)
- [Record and Index Documents](#record-and-index-documents)
- [Model and Capabilities](#model-and-capabilities)
- [Documents](#documents)
- [Reads and Core Document View](#reads-and-core-document-view)
- [Completeness and Integrity](#completeness-and-integrity)
- [Security and Conformance](#security-and-conformance)
- [Executable Example](#executable-example)
- [References](#references)

## Scope and Conventions

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this
document are to be interpreted as described in
[RFC2119](https://www.rfc-editor.org/rfc/rfc2119).

[Core 1.0-rc4](../../core/spec.md), its
[model language](../../core/model.md) and [federation](../federation/spec.md) define entity
semantics, selection and errors. This format does not define a server,
write-through interface, global identifier or synchronization protocol.
Normative schemas describe storage, not another domain model:

- [Entity record schema](schemas/document-record.schema.json).
- [Collection index schema](schemas/document-index.schema.json).

Both schemas use JSON Schema Draft 2020-12. Their URNs identify this draft's
schemas. They are not network retrieval endpoints. Producers and consumers
MUST also implement the semantic constraints below. Schema validity alone
does not establish Core model compliance or graph completeness.

## Motivation and Use

This format is a storage representation for the Git and File bindings.
A publisher can capture one Registry once and make the same directory tree
available in a Git commit, an offline bundle or a local filesystem. A
consumer-side resolver or a federating API server then reads the selected
metadata and document bytes from that tree.

Core already defines [single-document](../../core/spec.md#single-document-view)
and [multiple-document](../../core/spec.md#multiple-document-view) views.
An ordinary Core JSON export is appropriate when one document is sufficient.
A [no-code HTTP server](../../core/http.md#no-code-servers) can serve files
whose paths implement the HTTP binding. Neither requires this format.

The mapping adds complete typed collection indexes and exact size/digest
references. These permit selective reads and integrity checks while leaving
existing file names and directory structure unchanged. Stored records are
not Core API responses. The reader assembles them into the Core document
view defined below.

For example, a project can already contain `source/specs/widget.json`,
`engineering/assets/image.dat`, its application code and a README. Adding
the mapping can produce:

```text
project/
  registry.json
  registry-metadata/
    groups.json
    assets.json
    item.json
    item-meta.json
    versions.json
  source/
    main.py
    specs/
      widget.json
      widget.registry.json
  engineering/
    assets/
      image.dat
  README.md
```

`registry.json` identifies the Registry and its modeled collections. Added
indexes and records associate `/documents/main/assets/item` with its Meta
and Versions. A Version record in `source/specs/widget.registry.json` can
contain a local document descriptor whose `href` is
`source/specs/widget.json`. This path is relative to the selected root, not
to the Version record. Its `size` and `sha256` describe the existing file's
exact bytes. Neither `widget.json` nor `image.dat` needs to move or change.

The illustration omits some metadata records. The directory names and
metadata locations are choices, not a prescribed layout. Metadata can sit
beside the described files or in a separate directory. Unreferenced files
such as `source/main.py` and the README do not become Resources automatically
and are not part of the Registry's declared content closure.

The [worked example](#worked-example-map-one-existing-file) below shows
every file needed to map one existing document and the resulting reads.
The [larger sample](samples/mapping/registry.json) demonstrates multiple
Resource types, aliases and binary content.

Git chooses the directory through `parameters.path` and pins its commit.
File selects that same directory through a file URI. The shared
[hosting and resolution model](../federation/spec.md#design-hosting-models)
determines whether the consumer or an API server performs these reads.

## Worked Example: Map One Existing File

<!-- mapping-walkthrough:start -->

This example maps one existing file to Resource
`/documents/main/assets/widget`, with default Version `v1`.
The selected root is the `project` directory. No file outside that
directory is read.

The complete files are also available in the
[walkthrough directory](samples/mapping-example). You can save the JSON
blocks below directly. Use UTF-8, two-space indentation, LF line endings
and one final newline in each file. The size and digest values describe
those exact bytes. If you change a file, recalculate its size and digest
in the referring metadata, continuing up to `registry.json`.

### 1. Keep the Existing Document

`source/specs/widget.json` already contains:

```json
{"type":"string"}
```

It is 18 bytes, including the final newline. Its SHA-256 is
`85803e087e684bdab3e5d6c2dd1af627da83382db625be9a42aea3d4d06539be`.
Leave this file unchanged.

### 2. Add the Mapping Files

Add the following eight JSON files. They are shown from the Version
record up to the root, so each reference names a file already shown.
The directory names are example choices, not format requirements.

**`source/specs/widget.registry.json`**

```json
{
  "format": "xregistry-document-tree",
  "formatversion": "1",
  "kind": "version",
  "entity": {
    "xid": "/documents/main/assets/widget/versions/v1",
    "assetid": "widget",
    "versionid": "v1",
    "epoch": 1,
    "createdat": "2026-01-01T00:00:00Z",
    "modifiedat": "2026-01-01T00:00:00Z",
    "ancestorid": "v1",
    "isdefault": true,
    "contenttype": "application/schema+json"
  },
  "document": {
    "kind": "local",
    "href": "source/specs/widget.json",
    "size": 18,
    "sha256": "85803e087e684bdab3e5d6c2dd1af627da83382db625be9a42aea3d4d06539be"
  }
}
```

**`registry-metadata/versions.json`**

```json
{
  "format": "xregistry-document-tree",
  "formatversion": "1",
  "kind": "collection",
  "xid": "/documents/main/assets/widget/versions",
  "count": 1,
  "entries": [
    {
      "kind": "version",
      "xid": "/documents/main/assets/widget/versions/v1",
      "href": "source/specs/widget.registry.json",
      "size": 580,
      "sha256": "6587872b270d75ecaa6be1028518d47bff4ac282379d89f1c34c6efce8c1b70f"
    }
  ]
}
```

**`registry-metadata/widget-meta.json`**

```json
{
  "format": "xregistry-document-tree",
  "formatversion": "1",
  "kind": "meta",
  "entity": {
    "xid": "/documents/main/assets/widget/meta",
    "assetid": "widget",
    "epoch": 1,
    "createdat": "2026-01-01T00:00:00Z",
    "modifiedat": "2026-01-01T00:00:00Z",
    "readonly": true,
    "defaultversionid": "v1",
    "defaultversionsticky": true
  }
}
```

**`registry-metadata/widget.json`**

```json
{
  "format": "xregistry-document-tree",
  "formatversion": "1",
  "kind": "resource",
  "entity": {
    "xid": "/documents/main/assets/widget",
    "assetid": "widget"
  },
  "meta": {
    "kind": "meta",
    "xid": "/documents/main/assets/widget/meta",
    "href": "registry-metadata/widget-meta.json",
    "size": 361,
    "sha256": "9a34e98106eef18aa64b07c5878d75c0a5dfd96f3823750584709365b2681895"
  },
  "collections": [
    {
      "kind": "collection",
      "xid": "/documents/main/assets/widget/versions",
      "href": "registry-metadata/versions.json",
      "size": 423,
      "sha256": "08a43de17e9d6630a57b315a47583e1b1c785b965df05c91823900807cbe2010"
    }
  ]
}
```

**`registry-metadata/assets.json`**

```json
{
  "format": "xregistry-document-tree",
  "formatversion": "1",
  "kind": "collection",
  "xid": "/documents/main/assets",
  "count": 1,
  "entries": [
    {
      "kind": "resource",
      "xid": "/documents/main/assets/widget",
      "href": "registry-metadata/widget.json",
      "size": 679,
      "sha256": "630d2ea1e6d94f89c75a3c56a74a713c4b232a81fb3fff874a83320405b9efdb"
    }
  ]
}
```

**`registry-metadata/main.json`**

```json
{
  "format": "xregistry-document-tree",
  "formatversion": "1",
  "kind": "group",
  "entity": {
    "xid": "/documents/main",
    "documentid": "main",
    "epoch": 1,
    "createdat": "2026-01-01T00:00:00Z",
    "modifiedat": "2026-01-01T00:00:00Z"
  },
  "collections": [
    {
      "kind": "collection",
      "xid": "/documents/main/assets",
      "href": "registry-metadata/assets.json",
      "size": 392,
      "sha256": "72c43f08dd89af2c16b51ab9dc21fc36b7901ab475cae7ebb9e610c6a6cc9626"
    }
  ]
}
```

**`registry-metadata/groups.json`**

```json
{
  "format": "xregistry-document-tree",
  "formatversion": "1",
  "kind": "collection",
  "xid": "/documents",
  "count": 1,
  "entries": [
    {
      "kind": "group",
      "xid": "/documents/main",
      "href": "registry-metadata/main.json",
      "size": 510,
      "sha256": "b963e9db3e1ecdebe20c78be39d0fd98b26d2beb1338e06223b92e9164666d04"
    }
  ]
}
```

**`registry.json`**

```json
{
  "format": "xregistry-document-tree",
  "formatversion": "1",
  "kind": "registry",
  "entity": {
    "xid": "/",
    "registryid": "workshop",
    "specversion": "1.0-rc4",
    "epoch": 1,
    "createdat": "2026-01-01T00:00:00Z",
    "modifiedat": "2026-01-01T00:00:00Z",
    "modelsource": {
      "groups": {
        "documents": {
          "singular": "document",
          "resources": {
            "assets": {
              "singular": "asset"
            }
          }
        }
      }
    },
    "capabilities": {
      "available": {
        "capabilities": {
          "mutable": false
        },
        "entities": {
          "mutable": false
        },
        "model": {
          "mutable": false
        },
        "modelsource": {
          "mutable": false
        }
      },
      "flags": [
        "doc",
        "inline"
      ],
      "pagination": false
    }
  },
  "snapshot": {
    "scope": "/",
    "completeness": "offline-complete"
  },
  "collections": [
    {
      "kind": "collection",
      "xid": "/documents",
      "href": "registry-metadata/groups.json",
      "size": 361,
      "sha256": "edafff00fe4486be418968a4d3b770ff40a3b60c75ddc015f34252cca1c8c330"
    }
  ]
}
```

The root declares the model and references the `documents` collection.
That collection leads to Group `main`, then its `assets` collection,
Resource `widget`, the Resource's Meta and its Versions. The Meta names
`v1` as the default. The Version record points to the unchanged file.

### 3. Read Metadata or Document Bytes

The abstract operation `entity` with target
`/documents/main/assets/widget/versions/v1` returns the following native
metadata envelope. Its local pointer selects the entity in this response,
not a file on disk:

```json
{
  "kind": "version",
  "entity": {
    "xid": "/documents/main/assets/widget/versions/v1",
    "assetid": "widget",
    "versionid": "v1",
    "epoch": 1,
    "createdat": "2026-01-01T00:00:00Z",
    "modifiedat": "2026-01-01T00:00:00Z",
    "ancestorid": "v1",
    "isdefault": true,
    "contenttype": "application/schema+json",
    "self": "#/entity"
  }
}
```

The `document` operation on that Version returns the original 18-byte
body, with the media type recorded by `contenttype`:

```json
{"type":"string"}
```

A `document` request to `/documents/main/assets/widget` returns the same
bytes because its Meta selects `v1`. These are read-operation concepts,
not additional HTTP routes. A server exposing this mapping uses its
consumer-facing binding to deliver the corresponding response.

The eight mapping files and the document form the complete declared
Registry in this example. Other project files are unaffected. If
`widget.json` later changes, its old size/digest no longer matches and
the reader reports `integrity_error` until the mapping is updated.

<!-- mapping-walkthrough:end -->

## Root and Storage Paths

The selected directory MUST contain `registry.json`. Its record MUST have
`kind: "registry"` and `entity.xid: "/"`. Git's `parameters.path` and File's
endpoint select this same directory. Neither adds an implicit extra directory.

Every internal `href` is relative to that selected root, including references
in nested records. It is NOT relative to the referring file. The `/` separator
in these serialized storage names is a format separator. Filesystem bindings
translate it to their native separator without URI decoding.

Apart from the entry-point filename, this format prescribes no directory
names, file extensions or correspondence between physical and Registry
hierarchies. Each record/index `href` identifies the complete metadata JSON
document at that location. Each local Version document `href` identifies a
regular file anywhere within the selected root, regardless of its extension
or domain format.

Paths MUST be nonempty, normalized root-relative strings with `/` separators.
They MUST NOT be absolute, contain empty components, `.` or `..` components,
backslashes, NUL/control characters or surrogate code points. URI decoding
MUST NOT be applied. Encoded separator/dot traversal tricks MUST be rejected.
Portable paths MUST NOT contain `<>:"|?*`, end a component with a space or
period, or use Windows device names such as `CON` and `NUL`.
Other Unicode names and spaces within components are permitted. Platform
path-length and access limits produce explicit errors.

Metadata files describing different records or indexes MUST have distinct
paths. Paths whose spellings differ only by case MUST NOT designate different
mapping objects, because such mappings are ambiguous on case-insensitive
filesystems. Several Versions MAY reference the same local document file
using the same path and identical size/digest values. A document path MUST
NOT also be allocated to a metadata record or index.

An index maps a full, case-sensitive XID to a storage path. That path is not
derived from the entity ID. The mapping therefore supports all Core-valid
IDs, including IDs that are not portable filesystem names. The same local ID
in different typed collections remains distinct.

Core's case-insensitive uniqueness within a parent and case-sensitive lookup
still apply. A pair differing only in case in the same collection is invalid
Core data, not a filesystem collision to repair. An ID MUST match the entire
string against `[A-Za-z0-9_](?:[A-Za-z0-9_.~:@-]){0,127}`. Whitespace and trailing
line terminators are not part of an ID. This grammar is independent of native
filename rules. An implementation unable to represent the total
path length or object count MUST report
`limit_exceeded`. It MUST NOT truncate, normalize or replace an entity ID.

The example generator uses `records/`, `indexes/` and `documents/` directories,
with opaque hexadecimal allocations such as `records/n1a.json`. This avoids
name collisions when generating a new tree. It is a producer convention, not
a restriction on existing files or on other conforming mappings.

## Record and Index Documents

All record and index documents MUST be UTF-8 JSON objects without a byte order
mark, duplicate keys or non-JSON numbers. Each has
`format: "xregistry-document-tree"` and `formatversion: "1"`.
An unknown version MUST produce `unsupported_version`.

An entity record contains `kind` and `entity`. `entity` is a storage fragment
of Core metadata, with full `xid` and explicit model-named identifiers.
These records store metadata without API navigation fields. A reader adds
the navigation links when it assembles a Core response, as described in
[Reads and Core Document View](#reads-and-core-document-view).

| Kind | REQUIRED metadata in `entity`, in addition to `xid` |
| --- | --- |
| `registry` | `registryid`, `specversion`, `epoch`, `createdat`, `modifiedat`, `modelsource`, `capabilities`. |
| `group` | `<GROUP>id`, `epoch`, `createdat`, `modifiedat`. |
| `resource` | `<RESOURCE>id`. No inherited default-Version attributes. |
| `meta`, ordinary | `<RESOURCE>id`, `epoch`, `createdat`, `modifiedat`, `readonly`, `defaultversionid`, `defaultversionsticky`. |
| `meta`, alias | Only `<RESOURCE>id`, `xid`, `xref`. |
| `version` | `<RESOURCE>id`, `versionid`, `epoch`, `createdat`, `modifiedat`, `ancestorid`, `isdefault`. |

All identifiers MUST agree with the full typed XID and model singular names.
For example, `/documents/main/assets/item/versions/v1` identifies Version
`v1` of asset `item`, not a Version globally named `v1`. `meta` and `versions`
are literal Core path components. Group and Resource type names MUST be
validated against the captured model. Resource and Version extension metadata
MUST stay on the entity to which the model assigns it.

Storage metadata MUST omit `self`, `shortself`, `metaurl`,
`defaultversionurl`, collection navigation/counts, nested entity collections,
and Version `formatvalidated`, `compatibilityvalidated`, and their reason
attributes.
It MUST NOT contain inlined `<RESOURCE>` or `<RESOURCE>base64` document
content. These omissions do not permit dropping other Core or extension data.

Registry and Group records have a `collections` array containing exactly one
reference for every modeled child collection, even an empty one. An ordinary
Resource record has exactly one reference, to its `versions` collection,
and a `meta` reference to its Meta record. An alias Resource has a `meta`
reference but an empty `collections` array: it owns no local Versions.
Meta and Version records have no `collections` or `meta` reference.

Each reference has exactly these fields:

| Field | Meaning |
| --- | --- |
| `kind` | `collection`, `group`, `resource`, `meta` or `version`. |
| `xid` | Full entity XID, or full typed collection path. |
| `href` | Normalized path relative to the selected directory root. |
| `size` | Nonnegative integer count of exact encoded file bytes. |
| `sha256` | 64 lowercase hexadecimal digits hashing those exact bytes. |

The reference's kind and XID MUST equal the referenced object's kind and XID.
Its role comes from this metadata, not its directory name or file extension.
Both `size` and `sha256` are REQUIRED, including for zero-byte content.
There is no external form of a metadata or collection reference.

A collection index has `kind: "collection"`, its full collection `xid`,
`count`, and `entries`, an array of entity references. `count` MUST equal
the array length. An empty collection has `count: 0` and `entries: []`.
Each entry MUST name an immediate member of this collection with the correct
kind. References in both `entries` and `collections` MUST be strictly sorted
by unsigned UTF-8 bytes of the full XID. Duplicate XIDs, case-insensitive
sibling ID collisions and conflicting metadata storage allocations are invalid.

For example, this complete empty index is valid:

```json
{
  "format": "xregistry-document-tree",
  "formatversion": "1",
  "kind": "collection",
  "xid": "/independent/MAIN/assets",
  "count": 0,
  "entries": []
}
```

Version indexes MUST include all locally owned Versions. An ordinary Resource
MUST have at least one Version. Exactly one MUST have `isdefault: true`,
matching its Meta's `defaultversionid`. Ancestors MUST exist in that same
index and MUST NOT form cycles other than a root's self-reference.
An alias MUST NOT own a Version index, including a fabricated empty index.

## Model and Capabilities

The Registry's `entity.modelsource` MUST preserve the captured source,
including `ximportresources` provenance. `entity.model`, when supplied, MUST
be the actual full Core model, not a compact source relabeled as a full model.
It MUST agree with the source, its resolved includes and the captured data.

If the source contains `$include` or `$includes`, the Registry record MUST
also contain `resolvedmodelsource`: the compact source after those includes
were evaluated at capture time, but before implicit Core definitions and
`ximportresources` expansion. This object MUST be self-contained and preserve
Resource type sharing. `modelbase` MUST record the absolute base of the
original source. Consumers MUST NOT re-fetch mutable includes during a read.
The producer MUST establish equivalence of the captured source, resolved
source and full model, when present. The original include directives remain
available through `entity.modelsource`. The resolved copy is storage context,
not a second authoritative domain model.

When includes are absent, `resolvedmodelsource` is OPTIONAL and, if present,
MUST equal `entity.modelsource`. Model reads expose the original source,
available resolved source and available full model. Interpreting a compact
source MUST apply Core defaults. It MUST NOT silently infer type sharing
from structural similarity.

Model results MUST preserve `modelbase` when present. Registry metadata
envelopes retain `snapshot` and available `source` outside `entity`. These
are capture context, not new Core attributes.

`entity.capabilities` MUST describe access to this snapshot, not copy claims
of upstream writes or filtering that the selected binding cannot implement.
It MUST include Core's `available` map. The bindings are read-only.
It also carries the [resolution-owner signal](../federation/spec.md#signaling-who-performs-resolution).
A stored combined view declares `federation.resolution: "producer"`, so a
consumer does not repeat its catalog resolution. Absence retains consumer
resolution. This signal is independent of linked/offline completeness.
Captured source information MAY appear in the Registry record's `source`
object with an absolute, credential-free `uri` and OPTIONAL `revision`.
This is provenance, not the operation's Git pin, an entity XID, or an implicit
base for document links.

## Documents

Each Version record MUST have exactly one `document` descriptor:

| `document.kind` | REQUIRED fields | Meaning |
| --- | --- | --- |
| `local` | `href`, `size`, `sha256` | Exact bytes in an existing or newly stored file inside the selected root. |
| `external` | `uri` | Explicit external domain-document reference. |
| `none` | No others | The Resource model has `hasdocument: false`. |

For a local document, OPTIONAL `base` supplies the base URI used to resolve
relative links inside that document. If the file was copied from an external
location, OPTIONAL `origin` records that original location. The copied
Version no longer has a `<RESOURCE>url`, because its document is now local.
Both `base` and `origin`, when present, MUST be absolute URIs without embedded
credentials.

For `external`, `uri` MUST equal the Version's `<RESOURCE>url` exactly.
A relative URI MUST have an explicit absolute `base` on this descriptor.
Neither the containing file, catalog URL, Git repository URL nor `source.uri`
is an implicit base. Known integrity is represented by OPTIONAL paired
`size` and `sha256` fields. Consumers MUST check both if they retrieve content
with these fields. An external locator is not a metadata alias.

A Version referencing a document MUST identify either local bytes or an
explicit external location. A missing referenced local file is an
`invalid_package` error, not an empty document.
A zero-byte local document MUST reference an actual zero-byte file, with
`size: 0` and SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
Binary and JSON bytes MUST NOT be decoded, reserialized, newline-converted
or replaced by an empty JSON wrapper. The Version's `contenttype`,
if present, describes the bytes independently of the file's extension.

For `hasdocument: false`, `document.kind` MUST be `none`, and all three
Core document attributes (`<RESOURCE>`, `<RESOURCE>base64`, `<RESOURCE>url`)
MUST be absent. A document request MUST produce `unsupported_operation`.
This is distinct from a present zero-byte document.

## Reads and Core Document View

An exact read walks the Registry record, the necessary typed collection
indexes and selected child records. A Version read MUST NOT require reading
unrelated domain bytes. A consumer MAY scan a collection index in memory.
The format defines one complete index per collection and no pagination.
If a configured limit prevents a consumer from reading the complete index
or the records needed for its request, the consumer MUST return
`limit_exceeded`. It MUST NOT return the subset already read as a complete
collection or use that subset to claim a unique match.

The following materialization defines the metadata result envelope. The
envelope is not a new wire API. It keeps storage and transport context outside
Core metadata:

| Operation | Envelope and materialization |
| --- | --- |
| `entity` | `kind` and `entity`. Recursively inline descendant metadata, never domain bytes. |
| `collection` | `kind: "collection"`, `xid`, `complete: true`, and `entities`, a Core collection map. |
| `model` | Original `modelsource`, available `resolvedmodelsource`, and available full `model`. |
| `capabilities` | The captured snapshot access capabilities. |
| `document` | Exact bytes, or an explicit external descriptor subject to caller policy. |

Every materialized entity's `self` MUST be a JSON Pointer fragment locating
that entity in the returned envelope. For example, a standalone Version
has `self: "#/entity"`. Collection members begin at `#/entities/<ID>`.
JSON Pointer tokens MUST escape `~` as `~0` and `/` as `~1`. URI-fragment
encoding also applies. XIDs are not rewritten.

Navigation MUST use a `#` JSON Pointer if and only if the referenced entity
or collection is included in the output. A pointer into another record file
is not document-local navigation.

Registry and Group results inline all child metadata. Ordinary Resource
results inline `meta` and all Version metadata. `metaurl`, `versionsurl`,
and the Meta's `defaultversionurl` MUST point at those actual objects.
Collection URLs and counts, when included, MUST describe the materialized
maps, including empty maps. Default-Version attributes MUST NOT also be
copied onto the Resource. No response in this format invents an API `self`.

A standalone ordinary Meta result includes its selected default Version
metadata in an envelope sibling, `related.defaultversion`. Its
`defaultversionurl` MUST be `#/related/defaultversion`, and that Version's
`self` MUST locate the same object. This explicit navigation closure avoids
an absolute URL to an undefined native API or a dangling local pointer.
An alias Meta has no such sibling and no default-Version attributes.

Core `xref` remains one-hop, same-Registry and same-Resource-model-type.
Document-view Resource and Meta reads MUST leave aliases unexpanded,
including dangling aliases and aliases whose targets are themselves aliases.
Document-view alias Versions and alias Version collections MUST produce
`unsupported_operation`, retaining Core's `cannot_doc_xref` diagnostic.
No materialized target metadata can replace the source IDs.

A logical document request to an alias MAY read the one-hop target's selected
document, independently of document-view metadata. It MUST NOT follow a
second alias. If no one-hop target document exists, the document request
returns `not_found`. That does not make the source's minimal metadata invalid.
Resource document requests use `meta.defaultversionid`. Explicit Version
requests use exactly that ID. A snapshot revision, index position or highest
Version string MUST NOT override the Core default.

Resource label selection uses effective default-Version metadata, applying
one-hop alias semantics where applicable. It does not inspect only the reduced
storage Resource object. Selection MUST use the common literal comparator and
complete collection, and return `not_found` or `ambiguous` as appropriate.
The selected metadata result still obeys document-view alias suppression.

## Completeness and Integrity

The root's `snapshot` object MUST contain `scope: "/"` and `completeness`,
either `linked` or `offline-complete`. Both classes MUST contain the complete
internal record/index/document graph. An `offline-complete` snapshot MUST NOT
contain external-only domain documents. Captured resolved model material MUST
permit offline interpretation in both classes.

Here `scope: "/"` denotes the modeled Registry, not every file physically
present in the selected directory. Only files reached through the mapping's
references participate in its completeness and integrity checks. Existing
unreferenced project files remain outside that graph.

Only the mapping's record, index and local-document references identify files
that belong to its stored Registry graph. These references are the graph's
containment edges. For example, `registry.json` links to a collection index,
and a Version record links to its local document file.

External catalog advertisements, provenance URLs and links embedded inside
domain bytes are not such references. Offline completeness does not require
copying every Registry mentioned by a catalog or following links inside
domain documents.
An OPTIONAL full-graph validator checks every referenced object. A selective
read validates its visited path but MUST NOT claim to have independently
audited unvisited graph closure.

Consumers MUST verify length and SHA-256 before parsing or returning each
internally referenced object. Root bytes are captured once per operation.
Their SHA-256 identifies that root serialization, not universal semantic
identity or publisher authenticity. Every descendant is pinned transitively
by its parent descriptor. Newly published states MUST be complete without
replaying a prior snapshot. Shared content reuse does not relax closure.

Missing indexed objects, invalid kinds, invalid model types and inconsistent
defaults are `invalid_package`. A requested absent XID is `not_found`.
Descriptor mismatch is `integrity_error`. Observed mutation during a File
read or loss of already selected Git objects is `inconsistent_snapshot`.
Consumers MUST NOT return empty collections or retry another profile to hide
these failures.

## Security and Conformance

All data in a [package](../federation/spec.md#notations-and-terminology), the
stored mapping and its referenced documents, is untrusted. Producers MUST
use regular files and real
directories, not symlinks, reparse points, parent paths, device names, alternate
data streams or OS aliases. Consumers MUST enforce selected-root containment
before reading bytes. Dot segments, empty components, backslashes, absolute
paths are not valid `href` syntax. Percent encodings that could be interpreted
as separators or parent-path components, such as `%2f`, `%5c` and `%2e%2e`,
are also rejected. The reader does not decode an `href` as a URI.

Bindings define access to the selected root and race protection. Consumers
MUST impose explicit file, byte and traversal limits. Integrity checks do not
ensure authorized filesystem access or establish publisher trust. Before
retrieving an external URI, the consumer MUST check that destination against
its access policy and use only credentials authorized for that destination.

A producer conforms by emitting schema-valid records and indexes satisfying
all semantic, byte and closure rules. A consumer conforms by implementing
the common read semantics and its selected binding's safety rules. The
offline-complete class adds local declared document content. There is no
requirement to implement a server or an API-view facade.

## Executable Example

The [shared fixture](samples/mapping/registry.json) contains typed
collections, explicit defaults, JSON, empty and binary documents, a
metadata-only catalog entry, a Windows-reserved ID, type-sharing aliases,
a dangling alias and an alias chain. An empty independent collection
demonstrates a distinct Resource model type.

The fixture's local `.gitattributes` retains LF for JSON records and disables
text conversion for domain files on checkout. This is repository integration,
not a containment edge or permission for Git readers to apply attributes.
Existing projects do not need to replace their `.gitattributes` to add a
mapping. Git readers obtain stored object bytes without checkout conversion.

[`tools/mapping_examples.py`](../../tools/mapping_examples.py) provides
offline parsing, schema/semantic validation, selective reads, document-view
assembly and an OPTIONAL local Git object-store reader. It uses the common
`FederationError`, XID validation, label selection and Resource type helper.
It does not fetch repositories or external documents.

```text
python -B tools\mapping_examples.py validate workingdrafts\bindings\samples\mapping
python -B tools\mapping_examples.py entity workingdrafts\bindings\samples\mapping /documents/main/assets/item/versions/v1
```

`read_record` exposes a storage fragment, not a Core response. `metadata`
and `collection` return the materialized envelopes above. `document` returns
`bytes`, including `b""`. `document_descriptor` exposes an external locator
without fetching it. `reads` exposes storage-file reads so tests can
distinguish full validation from selective retrieval. CLI JSON metadata
includes this trace outside `entity`, without moving the pointer root.

The helper checks the storage schemas and relevant Core semantics, not every
extension constraint in an arbitrary domain model. Full model validation
remains a separate producer/consumer responsibility. `encode_tree` and
`sample_records` provide deterministic fixture construction, not publication.
`build-sample` writes only generated fixture bytes and refuses to overwrite
different content.

The filesystem example detects ordinary concurrent modification and rejects
static symlinks/reparse points. It is not a hardened boundary against hostile
processes racing pathname lookup. Such use requires OS handle-relative,
no-follow traversal or a private immutable snapshot as described by the File
binding. This limitation is not a claim of production resolver conformance.

## References

- [xRegistry Core 1.0-rc4](../../core/spec.md).
- [xRegistry Model 1.0-rc4](../../core/model.md).
- [xRegistry HTTP document/metadata distinction](../../core/http.md#resource-metadata-vs-resource-document).
- [Shared federation contract](../federation/spec.md).
- [JSON Pointer, RFC6901](https://www.rfc-editor.org/rfc/rfc6901).
- [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12/json-schema-core).
