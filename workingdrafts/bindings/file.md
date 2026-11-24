# xRegistry File Federation Binding

<!-- words: filesystem symlinks reparse unc sha256 percent-encoded -->
<!-- words: filenames href uri oid oci modelsource hasdocument -->
<!-- words: documenttree filestore localhost posix py realpath symlink -->
<!-- words: mnt nas -->
<!-- words: powershell workingdrafts -->

## Abstract

This binding defines how a consumer reads a Registry snapshot from a selected
filesystem directory. The directory contains either a document-tree mapping
or an OCI image layout. Neither format requires an xRegistry server.

**Status:** Unreleased working draft. This binding is not part of a released
xRegistry specification.

## Table of Contents

- [Scope and Conventions](#scope-and-conventions)
- [Motivation and Example](#motivation-and-example)
- [Advertisement and File URI](#advertisement-and-file-uri)
- [Layout Selection and Reads](#layout-selection-and-reads)
- [Containment and Concurrent Changes](#containment-and-concurrent-changes)
- [Errors and Conformance](#errors-and-conformance)
- [References](#references)

## Scope and Conventions

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this
document are to be interpreted as described in
[RFC2119](https://www.rfc-editor.org/rfc/rfc2119).

The [federation contract](../federation/spec.md#read-operations),
[Core 1.0-rc4](../../core/spec.md) and
[Model 1.0-rc4](../../core/model.md) define the read semantics.
Filesystem mutation, synchronization, file watchers, and HTTP facades are
outside the scope of this binding.

## Motivation and Example

A local snapshot supplies metadata and documents when a consumer cannot
reach a remote service. Deployment tooling can use the same snapshot as a
fixed input. The File binding reads it from an existing directory without
requiring an xRegistry server to interpret requests.

For example, `file:///D:/registry-snapshots/first` with
`layout: "document-tree"` selects that directory's `registry.json`.
A `document` request for `/documents/main/assets/item/versions/v1` follows
the record and index references and reads the selected document bytes.
An `entity` request for the same XID reads metadata. Alternatively,
`layout: "oci-layout"` and `reference: "release-1"` select one snapshot
from an OCI layout at the same kind of local location.

The directory can reside on local storage, network-attached storage (NAS),
or another file share exposed by the operating system as a mounted
filesystem. For example, `file:///mnt/team-registry` can select a mounted
share on a POSIX host, while `file:///R:/team-registry` can select a Windows
mapped drive. Mounting the share and configuring its credentials are
operating-system tasks, not operations defined by this binding.

These paths select shares that the operating system has already mounted.
They do not enable remote-authority URIs such as `file://nas/team-registry`.
The authority and containment rules in the "Advertisement and File URI" and
"Containment and Concurrent Changes" sections also apply to mounted shares,
including the restrictions on symlinks and reparse points.

Consumers can read either format directly. A federating API server can also
read the directory as a source and return ordinary xRegistry responses to its
client. The shared [hosting models](../federation/spec.md#design-hosting-models)
describe both arrangements.

In either arrangement, the directory remains mutable unless its storage
provides an immutable snapshot. The containment, digest, and concurrent-change
rules in the "Containment and Concurrent Changes" section therefore apply to both.

To read a local example, generate the `portable` Registry from the
[shared source](../federation/samples/examples.json). Run from the repository root
with a new or empty destination outside the checkout:

```powershell
python -B -m workingdrafts.federation.tools.generate_examples file --example portable --output D:\temp\xregistry-file-portable
python -B -m workingdrafts.bindings.tools.mapping_examples validate D:\temp\xregistry-file-portable
python -B -m workingdrafts.bindings.tools.mapping_examples document D:\temp\xregistry-file-portable /documents/main/assets/item/versions/v1
```

The selected File root is `file:///D:/temp/xregistry-file-portable`, with
`layout: "document-tree"` and no extra `xregistry` directory. The generator
reports the root hash, but the output directory remains mutable. The hash
identifies the root bytes; it does not establish an immutable filesystem pin.
A selective read checks only the bytes it references; the `validate` command
checks the complete declared graph. For local OCI output, use the
[OCI generation and reading commands](oci.md#generate-and-read-a-layout)
with `layout: "oci-layout"` and the chosen reference.

The [shared example instructions](../README.md#generating-and-reading-examples)
list the other examples, dependencies, and Linux path equivalents.

## Advertisement and File URI

`binding` MUST be `file`. The `endpoint` MUST be an absolute
[RFC8089](https://www.rfc-editor.org/rfc/rfc8089) file URI identifying the
selected directory. It MUST NOT contain credentials, a query or fragment.
An absent authority or `localhost` means local access. Other authorities,
including Universal Naming Convention (UNC) servers, MUST produce
`policy_denied` in this binding.
A separately named extension can define a remote filesystem access policy.
An implementation MUST NOT infer such a policy from this profile.

`parameters` contains only:

| Parameter | Constraint |
| --- | --- |
| `layout` | REQUIRED, exactly `document-tree` or `oci-layout`. |
| `reference` | REQUIRED for `oci-layout`, forbidden for `document-tree`. An OCI tag or `sha256` digest under the OCI binding. |

An unknown selected parameter MUST produce `unsupported_operation`.
The resolver MUST NOT infer a layout from the directory's files or switch
layouts after a failure. When an OCI layout contains several snapshots,
`reference` selects the root; directory-entry order does not.

```json
{
  "binding": "file",
  "endpoint": "file:///D:/registry-snapshots/first",
  "parameters": {
    "layout": "document-tree"
  }
}
```

```json
{
  "binding": "file",
  "endpoint": "file:///var/lib/xregistry/layout",
  "parameters": {
    "layout": "oci-layout",
    "reference": "release-1"
  }
}
```

The first example selects an absolute Windows drive path; the second selects
an absolute POSIX path. If a host cannot interpret the selected native path,
it MUST report `unsupported_operation` rather than reinterpret the path as
a different filesystem root.
For a Windows root, the initial path component is an absolute drive
designator, as in `/D:/registry-snapshots/first`; it is not an internal
mapping path. Windows drive-relative paths and older `C|` spellings are not
accepted. It is not permissible to add a drive designator to an internal
root-relative `href`.

URI parsing MUST:

- Validate escapes and reject encoded separators before decoding.
- Decode UTF-8 exactly once and reject NUL/control characters, backslashes,
  and dot/parent segments, including those introduced by an escape.

After decoding, URI parsing MUST reject:

- `.` and `..`.
- Empty interior components.
- Nested drive designators or device prefixes. The initial drive designator
  in an absolute Windows root is not a nested designator.
- Alternate data streams.
- Trailing spaces and dots.
- Windows-reserved component names.

The restrictions on alternate data streams, trailing spaces or dots, and
Windows-reserved component names apply when interpreting the root as a
Windows path. A single terminal slash is permitted for a directory URI.
Decoding a second time MUST NOT turn a literal percent sequence into traversal.
Malformed URI escapes or a path that does not decode as UTF-8 make the
advertisement `invalid_package`.

The selected directory's spelling locates the snapshot; it does not restrict
Core IDs. Directory mappings keep entity IDs separate from existing native
filenames, while OCI layouts use digest-based storage names.

## Layout Selection and Reads

For `document-tree`, the selected directory MUST contain `registry.json`.
The [directory mapping format](mapping.md#record-and-index-documents)
defines the record and index schemas and exact-byte representation. It also
defines model and capabilities reads, label selection, Core document view,
defaults and `xref`. Every internal `href` is
[relative to this directory](mapping.md#root-and-storage-paths), including
references in nested records. The selected root has no implicit
`xregistry` directory.

Both layout modes carry the selected Registry's
[resolution-owner capability](../federation/spec.md#signaling-who-performs-resolution).
A consumer MUST NOT repeat catalog resolution for a `producer` view.
Absence of the signal retains the default consumer-side process.

A producer can add the mapping without moving existing files. It can embed
metadata records and indexes in `registry.json`, place them alongside existing
files, or keep them in a separate metadata directory. A local document
reference can point anywhere inside the selected root. The format requires no
`records/`, `indexes/`, or `documents/` directory, and
unreferenced files remain outside the Registry view.

For `oci-layout`, consumers MUST use the
[OCI binding's image-layout selection](oci.md#22-image-layout-selection)
and [descriptor-graph rules](oci.md#4-containment-and-range-shards).

The directory contains OCI `oci-layout`, `index.json`
and `blobs`. `index.json` can advertise multiple Registry snapshot roots.
A tag selects only among eligible entries advertised in `index.json`.
A digest can select a stored Registry index directly, even if `index.json`
does not advertise it. The resolver verifies the selected root and retains
its digest under the OCI binding's image-layout selection rules.

The OCI binding's rules apply unchanged to:

- Tag ambiguity.
- Root artifact validation.
- Nested indexes.
- Descriptor bounds.
- Range selection.
- Size/digest verification.
- Complete containment closure.

This binding uses OCI's image-layout selection, not its remote Distribution
operations. The layout index is a local entry point, not a server endpoint.

The selected OCI root identifies one Registry; other roots in the directory
are separate snapshots. Local layout access does not imply network blob
retrieval. A missing internal blob causes failure even in a linked snapshot,
because the base OCI layout's allowance for omitted blobs does not relax
xRegistry closure.

Both modes return the same logical Core metadata and document bytes, subject
to the selected snapshot. Resource defaults come from Core metadata, not
file modification time. See
[Core default selection](../../core/spec.md#default-version-of-a-resource).
Equal XIDs in different directories remain scoped
to different Registry contexts.

External domain-document links remain explicit. Retrieving one requires
separate caller authorization and the selected format's locator and
integrity checks. A relative external locator in the
[directory mapping](mapping.md#documents) uses the descriptor's absolute
`base`; the [OCI layout](oci.md#53-version-documents-and-placeholders)
stores an absolute external locator.
Relative links MUST NOT silently become paths outside the selected root.

Linked snapshots permit external-only domain documents. Offline-complete
snapshots do not. Neither class implies following catalog advertisements,
rewriting `xref` into a filesystem link, or fetching arbitrary domain links.

## Containment and Concurrent Changes

The caller MUST authorize a filesystem boundary before the resolver opens
the selected directory. The resolver MUST verify that the directory is
within that boundary, then constrain all internal reads to that selected
root. A string prefix test is insufficient: `root-other` is not inside
`root`.

The resolver MUST check every directory component, including components of
the selected root, for symlinks and Windows reparse points. Internal objects
MUST be regular files. Consumers MUST NOT follow symlinks, junctions,
mount-point reparse records, or other path redirections. Consumers MUST NOT
read device files, pipes, sockets, and alternate data streams as snapshot
content.
Case folding, short-name aliases, and reserved OS names MUST NOT select a
different internal object. This check concerns the selected storage path,
not the spelling of a Core ID, which is looked up case-sensitively.

Before interpreting bytes, consumers MUST establish that the actual opened
objects are contained within the selected root. When a hostile process can
change paths concurrently, containment requires directory/handle-relative
no-follow access, equivalent platform protection, or a private immutable
copy made before resolution. Checking `realpath` before opening a mutable
pathname is insufficient. Hard links also provide no immutability guarantee:
a writer outside the directory can still change shared content.

For document-tree reads, consumers MUST capture the root record once and
retain its exact-byte SHA-256. Descendant references pin every consumed
external record, index and document. The bytes of the containing file pin
each inline record and index. For OCI reads, consumers MUST pin the
selected root digest and verify every descriptor under the OCI binding.

A directory that is read-only to the resolver can still change through
another writer. Read-only access therefore does not establish an atomic
snapshot.

Consumers MUST detect incomplete logical reads and changes during open/read
operations or to already captured selection state. A nonempty
operating-system read that returns fewer bytes than requested is progress.
The consumer MUST continue as needed to complete the logical read. Reaching
normal end of file on a stable file completes the read, even if the file is
shorter than the descriptor declares. An interrupted or otherwise
incomplete logical read, or an observed change, MUST produce
`inconsistent_snapshot`. If a read yields complete, stable bytes, a
mismatch with the descriptor's size or digest MUST produce `integrity_error`.

The resolver MUST establish that all bytes used by the operation are
coherent with the selected root. If it can establish coherence without an
immutable filesystem snapshot guarantee, it MAY return the result and MUST
report it as live with no immutable filesystem pin.

If the resolver cannot establish coherence, it MUST capture a private stable
snapshot that establishes coherence or return a failure. It MUST NOT return
incomplete or unverifiable bytes as a successful read.

Coherence for one operation does not establish an immutable filesystem
snapshot or an atomic capture of the upstream Registry. The consumer MUST
NOT use consistent file timestamps alone to advertise such an atomic
capture.

For example, after capturing a root and its referenced descriptor:

| Observed read | Outcome |
| --- | --- |
| All bytes used by the operation are coherent with the captured root, but the filesystem provides no immutable snapshot guarantee | The resolver can return a live result with no immutable filesystem pin. |
| Coherence cannot be established, and no more specific failure applies | Capture a private stable snapshot that establishes coherence or return a failure. |
| The read reaches normal end of file after 80 bytes from a stable file, but the descriptor declares 100 bytes | `integrity_error`. |
| A complete, stable file differs from the descriptor's size or digest | `integrity_error`. |
| The file changes during the read or the logical read is incomplete | `inconsistent_snapshot`. |

The resolver MUST NOT select a newer root in response to these outcomes.

A producer SHOULD construct a complete snapshot separately and then make
it available atomically using platform-appropriate synchronization. Updating
files in place while readers traverse them does not establish completeness.
Retaining immutable old files can let readers with an older pinned root
complete without mixing revisions.

The [origin context](../federation/spec.md#read-operations) MUST identify
the file URI, layout, and selected root hash or digest,
plus whether an immutable filesystem snapshot guarantee is present.
It MUST NOT replace entity XIDs, Resource Version IDs, or Core navigation.

## Errors and Conformance

| Condition | Outcome |
| --- | --- |
| Selected directory or initial document-tree root absent | `not_found`. |
| Internally referenced file/blob absent | `invalid_package`. |
| Complete, stable bytes do not match the descriptor's byte length or digest | `integrity_error`. |
| Observed concurrent mutation or an incomplete logical read | `inconsistent_snapshot`. |
| Unauthorized root, traversal, symlink or reparse point | `policy_denied`. |
| Unsupported layout operation or platform path form | `unsupported_operation`. |
| Unsupported Core or package version | `unsupported_version`. |
| Exhausted path, count or byte limit | `limit_exceeded`. |

OCI layout root selection follows the [OCI binding](oci.md#22-image-layout-selection).
Entity absence and selector ambiguity follow the
[common federation outcomes](../federation/spec.md#errors).
Other I/O failures produce `unavailable` unless a more specific
outcome applies. A failure does not authorize switching layouts, retrying
another profile or reporting a successful empty collection.

A producer MUST provide a complete internal graph in one explicitly
declared layout. This applies to both linked and offline-complete snapshots.
A consumer MUST implement that layout's metadata/document semantics
and all applicable containment and consistency rules. A consumer MUST
identify which layouts it implements. Support for one does not imply the
other. An offline-complete claim also requires the selected layout's
offline content closure.

The [document helper](tools/mapping_examples.py) implements only
`document-tree`. `file_root(profile, boundary)` parses and checks a local
advertisement, and `FileStore(root)` supplies exact bytes to `DocumentTree`.
The fixture helper rejects `oci-layout` with `unsupported_operation`; the
OCI helper implements that layout. The fixture helper does not provide a
race-hardened production filesystem security boundary.

## References

- [Shared federation](../federation/spec.md).
- [Directory mapping format](mapping.md).
- [OCI layout and native binding](../bindings/oci.md).
- [File URI scheme, RFC8089](https://www.rfc-editor.org/rfc/rfc8089).
- [URI syntax, RFC3986](https://www.rfc-editor.org/rfc/rfc3986).
