# xRegistry File Federation Binding

<!-- words: filesystem symlinks reparse unc sha256 percent-encoded -->
<!-- words: filenames href uri oid oci modelsource hasdocument -->
<!-- words: documenttree filestore localhost posix py realpath symlink -->
<!-- words: mnt nas -->

## Abstract

This binding reads a Registry snapshot from an explicitly selected filesystem
directory, using either the document-tree mapping format or an OCI image
layout. It is suitable for filesystem access without an xRegistry server.

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

The [federation contract](../federation/spec.md), Core 1.0-rc4 and
Model 1.0-rc4 define the read semantics. This binding does not define
filesystem mutation, synchronization, a file watcher or an HTTP facade.

## Motivation and Example

A local Registry snapshot is useful when the consumer cannot reach a remote
service, or when deployment tooling needs a fixed set of metadata and
documents. The File binding uses an already available directory rather than
requiring an xRegistry server to interpret each request.

For example, `file:///D:/registry-snapshots/first` with
`layout: "document-tree"` selects that directory's `registry.json`.
A request for `/documents/main/assets/item/versions/v1` follows its
record/index references and reads the selected bytes. Alternatively,
`layout: "oci-layout"` and `reference: "release-1"` select one snapshot
from an OCI layout at the same kind of local location.

The directory can reside on local storage, network-attached storage (NAS)
or another file share exposed by the operating system as a mounted
filesystem. For example, `file:///mnt/team-registry` can select a mounted
share on a POSIX host, while `file:///R:/team-registry` can select a Windows
mapped drive. Mounting the share and configuring its credentials are
operating-system tasks, not operations defined by this binding.

These examples use local filesystem paths to an already mounted share.
They do not enable remote-authority URIs such as `file://nas/team-registry`.
The authority and containment rules below still apply, including the
restrictions on symlinks and reparse points.

Consumers can read these formats directly. A federating API server can also
use the directory as a source and return a normal xRegistry response to its
client. The shared [hosting models](../federation/spec.md#design-hosting-models)
describe both arrangements. A local directory is not automatically immutable,
so the containment, digest and concurrent-change rules below apply in either
arrangement.

## Advertisement and File URI

The profile name MUST be `file`. `endpoint` MUST be an absolute
[RFC8089](https://www.rfc-editor.org/rfc/rfc8089) file URI identifying the
selected directory. It MUST NOT contain credentials, a query or fragment.
An absent authority or `localhost` means local access. Other authorities,
including UNC servers, MUST produce `policy_denied` in this binding.
A separately named extension can define remote filesystem access policy.
It MUST NOT be inferred from this profile.

`parameters` contains only:

| Parameter | Constraint |
| --- | --- |
| `layout` | REQUIRED, exactly `document-tree` or `oci-layout`. |
| `reference` | REQUIRED for `oci-layout`, forbidden for `document-tree`. An OCI tag or `sha256` digest under the OCI binding. |

An unknown selected parameter MUST produce `unsupported_operation`.
The layout MUST NOT be guessed from files in the directory or used as a
fallback after a failure. Selecting a root among several OCI snapshots
requires `reference`, not the first directory entry.

```json
{
  "name": "file",
  "endpoint": "file:///D:/registry-snapshots/first",
  "parameters": {
    "layout": "document-tree"
  }
}
```

```json
{
  "name": "file",
  "endpoint": "file:///var/lib/xregistry/layout",
  "parameters": {
    "layout": "oci-layout",
    "reference": "release-1"
  }
}
```

The first form is an absolute Windows drive path. The second is an absolute
POSIX path. A host unable to interpret a selected native path MUST report
`unsupported_operation`, not reinterpret it as a different filesystem root.
Windows drive-relative paths and older `C|` spellings are not accepted.

URI parsing MUST validate escapes before decoding, decode UTF-8 exactly once,
and reject NUL/control characters, backslashes, encoded separators and
encoded dot/parent segments. After decoding, `.` and `..`, empty interior
components, drive or device prefixes, alternate data streams, trailing
spaces/dots and Windows-reserved component names MUST be rejected where
applicable. A single terminal slash is permitted for a directory URI.
Decoding a second time MUST NOT turn a literal percent sequence into traversal.

The selected directory's spelling is a locator, not a new restriction on
Core IDs. Directory mappings separate entity IDs from existing native
filenames. The OCI layout uses its own digest-based names.

## Layout Selection and Reads

For `document-tree`, the selected directory MUST contain `registry.json`.
The [directory mapping format](mapping.md) defines
all record/index schemas, exact bytes, model and capabilities reads,
label selection, Core document view, defaults and `xref`. Every internal
`href` is relative to this directory, not to a nested record's directory.
No extra `xregistry` directory is implied.

Both layout modes carry the selected Registry's
[resolution-owner capability](../federation/spec.md#signaling-who-performs-resolution).
A consumer MUST NOT repeat catalog resolution for a `producer` view.
Absence of the signal retains the default consumer-side process.

The mapping can be added to an existing directory. Metadata records and
indexes can be placed alongside existing files or in a separate metadata
directory. Local document references can point anywhere inside the selected
root. No `records/`, `indexes/` or `documents/` directory is mandatory.
Unreferenced files remain outside the Registry view.

For `oci-layout`, consumers MUST use the
[OCI binding](../bindings/oci.md)'s normative image-layout selection and
descriptor-graph rules. The directory contains OCI `oci-layout`, `index.json`
and `blobs`. `index.json` can advertise multiple Registry snapshot roots.
`reference` selects and pins exactly one eligible root under that binding.
Tag ambiguity, root artifact validation, nested indexes, descriptor bounds,
range selection, size/digest verification and complete containment closure
are unchanged. This binding neither invents another OCI root-selection
algorithm nor treats a layout index as a Distribution endpoint.

The chosen OCI root identifies one Registry, not every root in the directory.
No network blob retrieval is implied by local layout access. Missing internal
blobs fail even for a linked snapshot. The base OCI layout's ability to
omit blobs does not relax xRegistry closure.

Both modes return the same logical Core metadata and document bytes, subject
to the selected snapshot. Resource defaults come from Core metadata, not
file modification time. Equal XIDs in different directories remain scoped
to different Registry contexts.

External domain-document links remain explicit. Retrieving one requires
separate caller authorization, URI-base handling and integrity checking.
Relative links MUST NOT silently become paths outside the selected root.
Linked snapshots permit external-only domain documents. Offline-complete
snapshots do not. Neither class implies following catalog advertisements,
rewriting `xref` into a filesystem link, or fetching arbitrary domain links.

## Containment and Concurrent Changes

The caller MUST authorize a filesystem boundary before the resolver opens
the selected directory. The resolver MUST verify that the directory is
within that boundary, then constrain all internal reads to that selected
root. A mere string prefix test is insufficient: `root-other` is not
inside `root`.

Every directory component, including components of the selected root, MUST
be checked for symlinks and Windows reparse points. Internal objects MUST be
regular files. Consumers MUST NOT follow symlinks, junctions, mount-point
reparse records or other path redirections. Device files, pipes, sockets and
alternate data streams MUST NOT be read as snapshot content.
Case folding, short-name aliases and reserved OS names MUST NOT select a
different internal object. Git/File storage portability does not permit
case-insensitive Core XID lookup.

Before interpreting bytes, consumers MUST establish containment of the
actual opened objects. Against concurrently hostile processes, this requires
directory/handle-relative no-follow access, equivalent platform protection,
or copying into a private immutable snapshot before resolution. Checking
`realpath` and then opening a mutable pathname alone is insufficient.
Hard links do not supply an immutability guarantee: shared writable content
outside the directory can still change its bytes.

For document-tree reads, consumers MUST capture the root record once and
retain its exact-byte SHA-256. Descendant descriptors pin every consumed
record and document. For OCI reads, consumers MUST pin the selected root
digest and verify every descriptor under the OCI binding.

A mutable directory is not an atomic snapshot just because it is read-only
to the resolver. Consumers MUST detect changes during open/read operations,
short reads and changes to already captured selection state. An observed
change MUST produce `inconsistent_snapshot`. A stable descriptor mismatch
is `integrity_error`. Where the environment cannot guarantee a coherent read,
the consumer MUST either capture a private stable snapshot or explicitly
report the lack of an immutable filesystem pin. It MUST NOT advertise an
atomic capture of a live upstream Registry based only on consistent file
timestamps.

A producer SHOULD construct an entire complete snapshot separately, then
make it available atomically with platform-appropriate synchronization.
Updating files in place while readers are traversing them is not a valid
substitute for completeness. Retaining immutable old files can allow readers
with an older pinned root to complete without mixing revisions.

Origin MUST identify the file URI, layout and selected root hash/digest,
plus the presence or absence of an immutable filesystem snapshot guarantee.
It MUST NOT replace entity XIDs, Resource Version IDs or Core navigation.

## Errors and Conformance

| Condition | Outcome |
| --- | --- |
| Selected directory or initial document-tree root absent | `not_found`. |
| Internally referenced file/blob absent | `invalid_package`. |
| Byte length or digest mismatch | `integrity_error`. |
| Observed concurrent mutation or truncated read | `inconsistent_snapshot`. |
| Unauthorized root, traversal, symlink or reparse point | `policy_denied`. |
| Unsupported layout operation or platform path form | `unsupported_operation`. |
| Unsupported Core or package version | `unsupported_version`. |
| Exhausted path, count or byte limit | `limit_exceeded`. |

OCI root selection, entity absence and ambiguity retain the OCI/common
definitions. Other I/O failures are `unavailable` unless a more specific
outcome applies. No failure silently switches layouts, retries another
profile or reports a failed retrieval as a successful empty collection.

A producer MUST provide a complete snapshot in one explicitly declared
layout. A consumer MUST implement that layout's metadata/document semantics
and all applicable containment and consistency rules. A consumer MUST
identify which layouts it implements. Support for one does not imply the
other. An offline-complete claim additionally requires the selected layout's
offline content closure.

The [document helper](../../tools/mapping_examples.py) implements only
`document-tree`. `file_root(profile, boundary)` parses and checks a local
advertisement, and `FileStore(root)` supplies exact bytes to `DocumentTree`.
The fixture helper rejects `oci-layout` with `unsupported_operation`.
The OCI helper owns that implementation. The helper is not a race-hardened
production filesystem security boundary.

## References

- [Shared federation](../federation/spec.md).
- [Directory mapping format](mapping.md).
- [OCI layout and native binding](../bindings/oci.md).
- [File URI scheme, RFC8089](https://www.rfc-editor.org/rfc/rfc8089).
- [URI syntax, RFC3986](https://www.rfc-editor.org/rfc/rfc3986).
