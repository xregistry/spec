# xRegistry Git Federation Binding

<!-- words: fullref oid oids sha256 symlinks reparse gitlink gitlinks -->
<!-- words: submodule submodules lfs smudge checkout filesystem filenames -->
<!-- words: modelsource hasdocument xids worktree refspec -->
<!-- words: documenttree filestore gitattributes gitrepository gitrevisions -->
<!-- words: gitstore href py scm ssh -->

## Abstract

This binding reads one xRegistry snapshot from a Git repository. It selects
and pins a commit, then reads the [directory mapping
format](mapping.md) directly from Git objects.

**Status:** Unreleased working draft. This binding is not part of a released
xRegistry specification.

## Table of Contents

- [Scope and Conventions](#scope-and-conventions)
- [Motivation and Example](#motivation-and-example)
- [Advertisement](#advertisement)
- [Revision and Object Selection](#revision-and-object-selection)
- [Read Operations](#read-operations)
- [Unsupported Indirections](#unsupported-indirections)
- [Errors and Security](#errors-and-security)
- [Conformance](#conformance)
- [References](#references)

## Scope and Conventions

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this
document are to be interpreted as described in
[RFC2119](https://www.rfc-editor.org/rfc/rfc2119).

This binding implements the read contract of
[federation](../federation/spec.md), using Core and Model Version 1.0-rc4.
It defines no write-through, synchronization, checkout, build or repository
execution. Package publication is separate from federation consumption.

## Motivation and Example

Git lets a team review and version a Registry alongside its project metadata.
An application can use the exact approved Registry state from a release
commit even after a branch or tag moves. The [directory mapping format](mapping.md)
preserves separate metadata and domain bytes inside that commit.

For example, a repository at `https://example.com/registries.git` can store
the tree below `xregistry`. Selecting `refs/tags/release-1` and requesting
`/documents/main/assets/item/versions/v1` first pins the tag's commit, then
reads the corresponding Git blobs. It does not read working-tree files or
choose the newest Resource Version from a Git timestamp.

The resolver can be part of the consumer or a federating API server.
In the latter case, the consumer uses a standard xRegistry API while the
server uses this binding as a source. The shared
[hosting models](../federation/spec.md#design-hosting-models) define that
choice. Git repository acquisition and source policy are separate from
the Core metadata representation returned to the consumer.

## Advertisement

The profile name MUST be `git`. `endpoint` MUST be an absolute HTTPS
repository URL with a host, and MUST NOT contain credentials, a query or
fragment. Native Git, SSH, `file:`, `git+https:` and remote-helper transports
are not part of this binding. A web page URL is not implicitly a repository.

`parameters` has these fields and no others:

| Parameter | Constraint |
| --- | --- |
| `revision` | REQUIRED string: full Git ref or complete SHA-1/SHA-256 object ID. |
| `path` | OPTIONAL portable relative directory. Default `xregistry`. `""` selects the repository tree root. |

A full ref MUST begin with `refs/` and pass Git's
[`check-ref-format`](https://git-scm.com/docs/git-check-ref-format) rules.
For example, `refs/heads/main` and `refs/tags/release-1` are valid.
`HEAD`, branch shorthand, abbreviated OIDs, reflog selectors, revision ranges,
`~`, `^` expressions and `:<path>` expressions MUST NOT be accepted.
A complete object ID consists of exactly 40 or 64 hexadecimal characters,
matching the repository's object format. Readers normalize its spelling to
lowercase for the pin. A full ref is a selection input, not an immutable pin.

A nonempty `path` MUST use `/`-separated portable directory components.
Components MUST be 1 to 64 ASCII letters, digits, `_`, `-` or `.`, begin with
a letter, digit or `_`, and MUST NOT end in `.`. A component MUST NOT have a
case-insensitive Windows device name (`CON`, `PRN`, `AUX`, `NUL`, `COM1`
through `COM9`, or `LPT1` through `LPT9`, including before an extension).
Leading/trailing separators, empty components, `.` and `..`, backslashes,
colon/drive names, URI escapes and OS aliases are forbidden. This constraint
applies to the storage root locator, not to Core entity IDs.

```json
{
  "name": "git",
  "endpoint": "https://example.com/registries.git",
  "parameters": {
    "revision": "refs/tags/release-1",
    "path": "xregistry"
  }
}
```

An unknown selected parameter MUST produce `unsupported_operation`.
Authentication and endpoint authorization are supplied by caller policy,
never by embedded metadata credentials.

## Revision and Object Selection

The resolver MUST establish one repository context using the selected HTTPS
endpoint and caller access policy. Fetching into an isolated object store is
permitted, but MUST NOT create or execute a working tree. Any acquisition
MUST be explicit, bounded and complete for the requested operation.

The resolver MUST resolve `revision` once. Lightweight tags and branches
select their referenced object. Annotated tags MUST be peeled to a commit.
An object that cannot resolve to a commit is invalid selection input.
The resulting complete commit OID MUST be recorded and remain pinned for the
entire operation, including model, label and document reads. Movement of the
original ref MUST NOT change that pin or trigger a second resolution.
Consumers MUST NOT substitute a currently reachable or newer commit when
the selected commit is inaccessible.

Starting at the pinned commit's tree, the resolver MUST walk `path` with
case-sensitive Git tree-name comparison. Every component MUST be a tree.
The selected tree MUST contain the format root `registry.json`.
Every format `href` is resolved inside that same selected tree.

An existing repository tree can become a Registry by adding `registry.json`
and the referenced metadata/index documents in a commit. Existing content
stays at its current paths. The mapping, rather than the physical directory
layout, determines its Group, Resource and Version hierarchy. Files not
referenced by that mapping do not participate in the Registry's closure.

Records, indexes and documents MUST be read as blob payloads. Consumers MUST
NOT use checkout bytes, text conversion, clean/smudge filters, attributes,
LFS downloads, hooks, external diff commands, build steps or repository code.
Blob mode `100644` or `100755` denotes data. Executable permission does not
authorize execution. Git object type and identity MUST be verified, in
addition to the format's descriptor size and SHA-256.

A Git OID hashes a typed Git object representation. It is neither a raw
document SHA-256 nor a Core `versionid`. The result origin MUST distinguish
repository endpoint, selected root path, requested revision and resolved
commit. None becomes `self` or modifies the selected entity XID.

## Read Operations

All logical reads use the shared format's exact indexes, records, model,
capabilities and document rules. Registry, Group, Resource, Meta and Version
metadata use its Core document-view assembly. No checkout-specific or
Git-specific entity serialization is defined.

The mapped Registry's enabled capabilities identify
[who performs federation resolution](../federation/spec.md#signaling-who-performs-resolution).
Consumers read a `producer` view directly. They use consumer-side resolution
when the signal is absent or explicitly `consumer`.

Explicit XID traversal MUST NOT retrieve unrelated domain documents.
Collection selection MUST apply the common literal label comparison and
inspect the complete necessary index/member metadata before asserting
uniqueness. Neither tree ordering nor a Git tag determines the default
Resource Version.

Both linked and offline-complete snapshots MUST contain every internal graph
object in the selected commit. Linked external document locators require a
separate caller-authorized retrieval, not an implicit Git fetch. Relative
domain links use the format's explicit document base, not the repository URL.
Core `xref` is resolved only inside this captured Registry and remains
one-hop. It is not a link to another repository.

## Unsupported Indirections

When encountered on the selected root or traversed internal graph:

| Git object or indirection | REQUIRED outcome |
| --- | --- |
| Mode `120000`, a symbolic link | `policy_denied`. Do not follow or treat its target string as metadata. |
| Mode `160000`, a submodule gitlink | `unsupported_operation`. No submodule initialization or fetch. |
| Git LFS pointer blob | `unsupported_operation`. No smudge or network content substitution. |
| Missing pinned tree/blob | `inconsistent_snapshot`. No implicit lazy fetch or ref re-resolution. |
| Wrong tree/blob type or malformed tree entry | `invalid_package`. |

For this binding, a blob starting with the Git LFS v1 signature line
`version https://git-lfs.github.com/spec/v1` is an unsupported LFS path,
including a CRLF-terminated signature. A producer needing those literal bytes
as a domain document needs a different binding. `.gitattributes` does not
override this rule.

Unrelated submodules or LFS files elsewhere in the repository do not invalidate
the selected tree. A full snapshot validator traverses its entire declared
closure. A selective reader only encounters objects on its visited paths.

## Errors and Security

An unknown ref or unavailable initial commit selection is `not_found`.
Missing `registry.json` at the selected root is `not_found`. A selected
internal reference missing from an otherwise readable Git tree is an
`invalid_package`. A tree entry whose pinned object is unavailable is
`inconsistent_snapshot`. Descriptor or Git object identity mismatch is
`integrity_error`. Unsupported Core/format versions are `unsupported_version`.
Resource, label and document failures retain the common distinctions.

Resolvers MUST enforce HTTPS authentication, certificate, redirect and
credential-scoping policy during acquisition. They MUST disable unsupported
protocols, repository-controlled execution and implicit lazy fetching.
Local object-store alternates, replacement objects, grafts, untrusted
configuration includes and filesystem indirections MUST NOT silently change
the selected object graph or bypass the permitted storage boundary.
Readers using Git subprocesses MUST pass validated arguments directly without
shell evaluation, and MUST isolate unsafe configuration/environment settings.

Acquisition, tag peeling, tree traversal and object reads MUST have explicit
resource limits. Limits or incomplete acquisition MUST NOT be reported as
successful empty results or used to justify fallback to another profile.
Git content identity alone does not authenticate the publisher. Signature
and repository trust policies are independent.

## Conformance

A producer MUST publish a complete document-tree mapping in one
commit at the advertised path. A native resolver MUST implement locator
validation, commit pinning, object-only reads, the common operations and
the rejection rules above. Offline-complete conformance additionally requires
all declared document bytes locally in that snapshot.

The shared [offline helper](../../tools/mapping_examples.py) accepts an
explicit local Git object directory and a revision:

```text
python -B tools\mapping_examples.py validate --git-dir STORE --revision refs/heads/main --path xregistry
```

`GitStore(git_dir, revision, path="xregistry")` exposes the resolved `pin`,
exact `read` bytes and visited storage paths. The same `DocumentTree` API
accepts `FileStore` or `GitStore`. Temporary bare object stores can exercise
this interface without commits in the user's repository, checkout, network
access or publication.

For selective CLI reads, `--target` supplies the Core XID independently of
`--git-dir`. No filesystem-root positional argument is used in Git mode.
`git_locator` validates the HTTPS advertisement separately from opening a
caller-provided, isolated local object store.

## References

- [Shared federation](../federation/spec.md).
- [Directory mapping format](mapping.md).
- [Git objects](https://git-scm.com/book/en/v2/Git-Internals-Git-Objects).
- [Git revision syntax](https://git-scm.com/docs/gitrevisions).
- [Git repository layout](https://git-scm.com/docs/gitrepository-layout).
- [Git LFS pointer specification](https://github.com/git-lfs/git-lfs/blob/v3.7.0/docs/spec.md).
