# xRegistry Git Federation Binding

<!-- words: fullref oid oids sha256 symlinks reparse gitlink gitlinks -->
<!-- words: submodule submodules lfs smudge checkout filesystem filenames -->
<!-- words: modelsource hasdocument xids worktree refspec -->
<!-- words: documenttree filestore gitattributes gitrepository gitrevisions -->
<!-- words: gitstore href py scm ssh workingdrafts -->
<!-- words: powershell -->

## Abstract

This binding defines how a consumer reads one xRegistry snapshot from a Git
repository. The consumer selects and pins a commit, then reads the
[directory mapping format](mapping.md) directly from Git objects.

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
[federation](../federation/spec.md#read-operations), using
[Core](../../core/spec.md) and [Model](../../core/model.md) Version 1.0-rc4.
Write-through, synchronization, checkout, builds and repository execution
are outside its scope. Publishing a Package is a separate operation from
consuming a federation.

## Motivation and Example

A Git repository can store a Registry alongside the project metadata that
defines or consumes it. A release can pin the approved Registry state to a
commit and retain that state even if the branch or tag later moves. Within
the commit, the [directory mapping format](mapping.md) keeps Registry
metadata separate from domain bytes.

For example, a repository at `https://example.com/registries.git` can store
the mapping under `xregistry`. Selecting `refs/tags/release-1` and requesting
`/documents/main/assets/item/versions/v1` causes the resolver to pin the tag's
commit before reading the corresponding Git blobs. The resolver reads no
working-tree files and does not use a Git timestamp to select the newest
Resource Version.

The resolver can run in the consumer or in a federating API server. When it
runs in the server, the consumer uses a standard xRegistry API and the server
reads the source through this binding. The shared
[hosting models](../federation/spec.md#design-hosting-models) define that
choice. Repository acquisition and source policy remain separate from the
Core metadata returned to the consumer.

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
The resolver MUST NOT accept:

- `HEAD`.
- Branch shorthand.
- Abbreviated object IDs (OIDs).
- Reflog selectors.
- Revision ranges.
- `~` or `^` expressions.
- `:<path>` expressions.

A complete object ID consists of exactly 40 or 64 hexadecimal characters,
according to the repository's object format. Readers normalize the spelling
to lowercase when recording the pin. A full ref, by contrast, selects an
object but does not itself provide an immutable pin.

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
endpoint and the caller's access policy. It can fetch into an isolated
object store, but MUST NOT create or execute a working tree. Any acquisition
MUST be explicit, bounded and complete for the requested operation.

The resolver MUST resolve `revision` once. Lightweight tags and branches
select their referenced object. The resolver MUST peel annotated tags to a
commit. An object that cannot resolve to a commit is invalid selection input.

The resolver MUST record the resulting complete commit OID and retain that
pin for the entire operation, including model, label and document reads.
If the original ref moves, that movement MUST NOT change the pin or trigger
a second resolution.
Consumers MUST NOT substitute a currently reachable or newer commit when
the selected commit is inaccessible.

For example, let `A` and `B` denote different complete commit OIDs
(symbolic placeholders, not valid command arguments):

| Time | Selection and reads |
| --- | --- |
| Start | `refs/tags/release-1` resolves to `A`. The operation pins `A`. |
| Ref moves | The tag now resolves to `B`. Metadata and document reads still use `A`. |
| A pinned object becomes unavailable | `inconsistent_snapshot`. The operation does not substitute `B`. |

Starting at the pinned commit's tree, the resolver MUST walk `path` with
case-sensitive Git tree-name comparison. Every component MUST be a tree.
The selected tree MUST contain the format root `registry.json`.
Every format `href` is resolved inside that same selected tree.

A producer can turn an existing repository tree into a Registry by committing
`registry.json` and any metadata files it references. Existing content keeps
its paths. The mapping defines the Group, Resource and Version hierarchy
independently of the physical directory layout. Files outside that mapping's
references do not participate in the Registry's closure.

Consumers MUST read `registry.json`, external records and indexes, and
documents as blob payloads. An inline record or index is read as part of its
containing file's blob.
Consumers MUST NOT use checkout bytes, text conversion, clean/smudge filters
or attributes. They MUST NOT use LFS downloads, hooks, external diff
commands, build steps or repository code.
Blob modes `100644` and `100755` both denote data; executable permission does
not authorize execution. Consumers MUST verify Git object type and identity
as well as the format's descriptor size and SHA-256.

A Git OID hashes the typed Git object representation, rather than the raw
document bytes. It is distinct from a document SHA-256 and a Core `versionid`.
The result origin MUST distinguish the repository endpoint, selected root
path, requested revision and resolved commit. These values neither become
`self` nor modify the selected entity XID.

## Read Operations

All logical reads follow the shared format's rules for
[exact indexes and records](mapping.md#record-and-index-documents), model,
capabilities and documents. Registry, Group, Resource, Meta and Version
metadata use its
[Core document-view assembly](mapping.md#reads-and-core-document-view).
This binding defines no checkout-specific or Git-specific entity
serialization.

The mapped Registry's enabled capabilities identify
[who performs federation resolution](../federation/spec.md#signaling-who-performs-resolution).
Consumers read a `producer` view directly. They use consumer-side resolution
when the signal is absent or explicitly `consumer`.

Explicit XID traversal MUST NOT retrieve unrelated domain documents.
Collection selection MUST apply the common literal label comparison and
inspect the complete necessary index/member metadata before asserting
uniqueness. Neither tree ordering nor a Git tag determines the default
Resource Version, whose choice follows
[Core default selection](../../core/spec.md#default-version-of-a-resource).

Both linked and offline-complete snapshots MUST contain every internal graph
object in the selected commit. Linked external document locators require a
separate caller-authorized retrieval, not an implicit Git fetch. Relative
domain links use the format's explicit document base, not the repository URL.
Core [`xref`](../../core/spec.md#cross-referencing-resources) is resolved
only inside this captured Registry and remains
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

In this binding, a blob starting with the Git LFS v1 signature line
`version https://git-lfs.github.com/spec/v1` is an unsupported LFS path,
including a CRLF-terminated signature. If a domain document needs those
literal bytes, its producer needs a different binding. `.gitattributes`
does not override this rule.

Submodules and LFS files outside the selected graph do not invalidate the
selected tree. A full snapshot validator traverses the entire declared
closure, whereas a selective reader encounters only objects on its visited
paths.

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

The resolver MUST apply explicit resource limits to acquisition, tag peeling,
tree traversal and object reads. It MUST NOT report an exhausted limit or
incomplete acquisition as a successful empty result, or use either condition
to justify fallback to another profile.

A Git content identity verifies content, not the publisher's identity.
Signature and repository trust policies are separate.

## Conformance

A producer MUST publish a complete document-tree mapping at the advertised
path in one commit. A native resolver MUST implement locator validation,
commit pinning, object-only reads, the common operations and the rejection
rules above. An offline-complete snapshot additionally contains all declared
document bytes locally.

The [shared generator](../federation/tools/generate_examples.py) creates a
new bare repository from a named Registry in
[examples.json](../federation/samples/examples.json). It stores the directory mapping
under `xregistry`, creates a deterministic synthetic commit at
`refs/heads/main`, and creates the annotated tag `refs/tags/snapshot`.
It reports the full commit ID and selected tree path. Author identity,
timestamps and object bytes are fixed example data, not the contributor's
identity or working-tree state. No remote is configured, and generation
does not fetch or push.

Run from the repository root with Git available and a new or empty output
directory outside the checkout:

```powershell
python -B -m workingdrafts.federation.tools.generate_examples git --example portable --output D:\temp\xregistry-git-portable
python -B -m workingdrafts.bindings.tools.mapping_examples validate --git-dir D:\temp\xregistry-git-portable --revision refs/heads/main --path xregistry
python -B -m workingdrafts.bindings.tools.mapping_examples document --git-dir D:\temp\xregistry-git-portable --revision refs/tags/snapshot --path xregistry --target /documents/main/assets/item/versions/v1
```

The [offline helper](tools/mapping_examples.py) peels the annotated tag and
pins its commit before reading. To read the same state in a later operation,
regardless of ref movement, pass the generator's complete commit ID as
`--revision`. The synthetic local repository exercises object reads without
providing an HTTPS advertisement or a remote publication. The
[shared instructions](../README.md#generating-and-reading-examples) include
Linux paths and the other named examples.

`GitStore(git_dir, revision, path="xregistry")` exposes the resolved `pin`,
exact `read` bytes and visited storage paths. The same `DocumentTree` API
accepts `FileStore` or `GitStore`. The [Git tests](tools/test_git_examples.py)
exercise moving refs and unavailable objects while an opened reader retains
its original pin. These operations use isolated repositories, not commits
or branch changes in the source checkout.

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
