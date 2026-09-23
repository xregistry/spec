# OPC UA Federation Offline Examples

<!-- words: applicationuri argparse argv browsename browsenext browseresult bytestrings continuationpoint continuationpoints datavalue endpointdescription endpointurl expandednodeid expectedsize exportnamespace federationerror federationprofiles filehandle filetransfer filetype identifiertype methodids namespace namespacearray namespacefile namespaceindex namespaceuri nodeid nodeids nodeset nsu opc opcfoundation opcua powershell py registryroot releasecontinuationpoints requestedmaxreferencespernode sdk selectedxid serializer serverarray serverindex serveruri servicestatus subcommand svu transportprofileuri typedefinition ua valueerror workingdrafts xregurl -->

These synthetic examples accompany the
[OPC UA binding](../../../bindings/opcua.md). They use Python's standard
library and the shared
[`federation_examples.py`](../../tools/federation_examples.py) error/validation
interfaces. They do not connect to a UA server, install an SDK, discover
endpoints or modify an external repository.

The companion proposal remains pinned at
`ff22f224400fc8be813bf0abcbfc3cde52bc7ed3` and explicitly unadopted.
The fixtures demonstrate the binding's corrected interpretation, not proof
of OPC Foundation adoption or Server interoperability.

## Running the Examples

Run from the repository root:

```powershell
python -B -m workingdrafts.bindings.tools.opcua_examples validate workingdrafts\federation\samples\opcua\references.json workingdrafts\federation\samples\opcua\read-sequences.json
python -B -m workingdrafts.bindings.tools.opcua_examples show workingdrafts\federation\samples\opcua\references.json reindexed-source-and-target
python -B -m workingdrafts.bindings.tools.opcua_examples show workingdrafts\federation\samples\opcua\read-sequences.json default-v1-short-chunks
```

`validate` executes every case and checks its exact result or expected error
code. It prints each file's case and expected-error counts. `show` first
validates the file and then prints one named result. Invalid fixtures,
unexpected outcomes and unavailable files produce a JSON error on standard
error and exit status 1. Argument syntax errors use argparse's exit status 2.
No new test modules are part of these examples.

## Fixture Files

| File | Purpose |
| --- | --- |
| `references.json` | Portable Registry-root mapping. Source ServerArray resolution. Target namespace remapping. Numeric, String, Guid and Opaque identifiers. Specific failures. |
| `read-sequences.json` | Metadata, three-page Browse and FileType Call transcripts, including cleanup and namespace-file refresh. |
| `registry-export.json` | Core document-view oracle with a metadata-only catalog, three asset Versions, default `v1`, local same-type aliases, typed extension metadata and local navigation. |
| `independent-registry.json` | Another Registry with the same asset XID and different bytes. Equality of XID alone is not identity. |

The first two files have `format: "xregistry-opcua-examples-v1"` and a
nonempty `cases` array. Every case has unique `name`, `kind`, `input` and
exactly one of `expected` or `error`. `note` is informative. Kinds are
`root`, `reference` and `sequence`. Each input names the corresponding
helper's arguments. This is fixture notation, not a proposed OPC UA encoding
or federation wire API.

The export files are Core documents, not fixture-suite envelopes. They
are not inputs to the helper's `validate` subcommand. Their local pointers
and identity/model constraints can be inspected independently. A `self`
of `#` selects the document root by the empty RFC 6901 pointer. All other
navigation pointers name actual included objects or collections.

## Reference and Root Mapping

`ExpandedNodeId` inputs use the native Part 4 component names:
`serverIndex`, `namespaceIndex`, OPTIONAL `namespaceUri`, `identifierType`
and `identifier`. Identifier types use Part 3's enum names `Numeric`,
`String`, `Guid` and `Opaque`. Numeric identifiers are UInt32 JSON integers.
Opaque identifiers are canonical Base64 ByteStrings.

The source `ServerArray` supplies the target Application URI. Element zero
identifies the source application. A URI is not a transport endpoint.
When a reference uses a namespace index, its source namespace table is
necessary. With explicit `namespaceUri`, `namespaceIndex` is zero and
`source_namespace_array` can be null. Target lookup always maps the exact
namespace URI in the target `NamespaceArray`. No missing URI becomes index
zero. NamespaceArray element zero is `http://opcfoundation.org/UA/`.
The examples reject duplicate table entries as ambiguous fixture context.

The two remote index cases select the same portable reference:

```text
svu=urn:example:ua:remote;nsu=urn:example:registry;s=ItemV1
```

One target requires `ns=7;s=ItemV1`. The reindexed target requires
`ns=2;s=ItemV1`. Source server and namespace indexes also change. In both
cases the target application is `urn:example:ua:remote`, not a guessed
`opc.tcp` URL.

Root mapping consumes an already selected, normalized `EndpointDescription`
with `endpointUrl`, `server.applicationUri` and `transportProfileUri`.
The fixture policy requires the endpoint to equal the selected advertisement.
Real discovery or an approved relocation needs its own policy. The helper
does not discover or authenticate it. Mapping a root does not verify its
existence, TypeDefinition or membership. Those are live-client obligations
in the binding, not guarantees provided by string validation.

## Read Transcript Notation

Every sequence has a `kind` and an `events` array. Kinds are `metadata`,
`browse`, `file` and `namespace-file`. Each event records:

- `service`: `Read`, `Browse`, `BrowseNext` or `Call`.
- `session`: the fixture's opaque Session identity.
- `nodeId`: the owning entity/file's NodeId, in portable form or in
  table-index form when the sequence includes its `namespaceArray`.
- `status`: the normalized operation/Method status, and OPTIONAL
  `serviceStatus` when separately recorded.

For metadata reads, `values` maps a Property name to
`{"status":"Good","value":...}`. The helper checks each DataValue status
and preserves its JSON value. This is a normalized observation of Property
Reads, not a claim that the UA Read Service accepts a Property-name map.
`nodeId` identifies the owning entity. The underlying Property NodeIds have
already been resolved by the fixture's mapping.

The metadata-only example's `xregurl` and structured `federationprofiles`
are explicitly implementation-mapped Version attributes. They are not
claimed to be base companion Properties, labels or FileType document bytes.
The pinned proposal lacks a generic mapping for these typed extensions.
The helper returns Property observations, not a complete Core serializer.

Browse events use `input` and `output`. Each output is one normalized
BrowseResult with `references` and `continuationPoint`. The initial input
can include `requestedMaxReferencesPerNode`. BrowseNext inputs identify
one captured token in `continuationPoints` and set
`releaseContinuationPoints`. Tokens are Base64 or null/empty at completion.
The same token can be reused by a server as traversal advances. It is not
in itself a cycle. Browse references contain native addressing observations,
not label values magically returned by Browse.

File events use `service: "Call"`, the Method BrowseName in `method`,
native argument names in `input`, and normalized `output`. `Open` returns
`fileHandle`. `Read` returns Base64 `data`. `Close` and `ExportNamespace`
have no output arguments. The notation does not invent numeric MethodIds.
The example subset permits only sequential read-mode Open/Read/Close,
plus an explicitly requested namespace refresh.

An OPTIONAL abstract `request` has `operation` and `target`. A document
request additionally records `selectedXid`, obtained from the selected
Version mapping. A default-document read needs a readable
`before.defaultversionid`. An explicit Version read MUST NOT substitute
the default. The helper checks the selected full XID and observed Version ID.
It does not infer a default from the available files.

`before` and `after`, when supplied, are matching nonempty observation maps
using `size`, `epoch`, `versionid` and/or `defaultversionid`. They stand for
separate mapped observations around the file read, not new FileType
Properties. In particular, the base companion proposal does not define a
`DefaultVersionId` Property. `expectedSize` is an OPTIONAL byte count.
An unknown Size is omitted. It is never encoded as zero.

A successful file result requires an explicit empty Read marking EOF and
a successful Close. This is a deliberately stricter transcript subset than
the general Part 20 algorithm, which can also use a reliable Size.
Short nonempty chunks are not EOF. Errors retain their native status.
Recorded Close cleanup is still checked. Reads using another Session,
Object or handle, and reads after Close, are invalid.

`namespace-file` with `refresh: true` starts with the parameterless
`ExportNamespace`, then opens and reads the updated XML file. With no
refresh it reads the existing file without claiming an update.
NamespaceFile is not a generic Registry resolver. No standard `Import`
is invented. The small XML payload is illustrative namespace-file content,
not a new NodeSet catalog domain.

## Python Interfaces

All invalid inputs and failed observations use the shared
`FederationError(ValueError)`, with `.code` and a message from `str(error)`.
No error is represented as empty bytes or an empty successful collection.

| Interface | Result and constraints |
| --- | --- |
| `NodeId(namespace_uri, identifier_type, identifier)` | Frozen parsed value. `.portable()` emits identifier-only namespace zero or `nsu=` form. Obtain validated instances through `parse_nodeid`. |
| `parse_nodeid(value: str) -> NodeId` | Portable NodeId parser. Namespace indexes and server prefixes are not accepted without context. Numeric UInt32, Guid syntax, canonical Opaque Base64 and string controls/length are checked. |
| `validate_namespace_array(values) -> list[str]` | Nonempty ordered table, exact namespace-zero entry, unique absolute URI strings, maximum 65,536 entries. |
| `validate_server_array(values) -> list[str]` | Nonempty ordered table of unique Application URI strings. |
| `map_registry_root(profile, endpoint_description, namespace_array) -> dict` | `endpoint`, `applicationuri`, `transportprofileuri`, portable `registryroot` and target-local `nodeId`. Uses shared profile validation. |
| `map_expanded_nodeid(reference, source_server_array, source_namespace_array, target_applicationuri, target_namespace_array) -> dict` | `applicationuri`, `namespaceUri`, target-local `nodeId`, application-specific `portable` ExpandedNodeId and `local` Boolean. |
| `map_status(status: str) -> str or None` | Common resolver error code. Only exact `Good` returns `None`. Unhandled bad, uncertain or qualified-good statuses fail as `unavailable`, with native status retained by the caller. |
| `interpret_read_sequence(sequence, *, max_bytes=1048576, max_events=256, max_references=4096, supported_specversions=("1.0-rc4",)) -> dict` | Metadata `values`, Browse `references`, or file Base64 `data`/`size`, plus `trace` and `consistency`. Complete reads add `complete: true`. Document reads add `selectedXid`. |
| `validate_fixture(document: dict) -> list[dict]` | Executes cases, compares exact results/error codes and returns named outcomes. |
| `main(argv=None) -> int` | Offline CLI exit status. `validate` and `show` only. |

`consistency: "observed"` means only that the supplied before/after
observations agree. `"unverified"` means no such check was supplied.
Neither value asserts an atomic Registry snapshot or an immutable pin.
`trace` contains the successful normalized operations in order. Failed
sequences raise an error rather than reporting successful completion.
The byte, event and reference budgets are configurable example limits, not
new OPC UA or xRegistry document-size limits.

## Dedicated Test-Phase Inventory

The supplied fixtures contain executable positive and negative cases.
The following matrix also names boundary mutations for the later test
phase. It is not a claim that a unit-test suite has already been generated.

| Area | Edge cases |
| --- | --- |
| Root | Multiple Registries at one endpoint. Namespace reindexing. Absent root namespace. Null NodeId. Nonportable root. Unknown parameter. Endpoint/app/transport mismatch. Embedded credentials. |
| References | Local server zero. Remote source index. Source/target table permutations. Missing source context. Explicit namespace with zero index. Absent target namespace. Duplicate URIs. Exact URI case. Fictional `ServerUri` rejected. |
| NodeId | All four identifier types. UInt32/UInt16 bounds and Boolean rejection. Malformed Guid/Base64. Empty versus null identifier. Controls/surrogates. 4,096/4,097 character or byte boundary. Encoded semicolons and percent signs. Semicolons inside a String identifier. |
| Core selection | Resource/default versus explicit Version XID. Case-sensitive lookup. Missing default mapping. Wrong selected Version. Incompatible SpecVersion. Same XID in independent Registries. |
| Metadata | No fake document for metadata-only catalogs. Structured extensions. Per-DataValue denial despite Good Service. Repeated Property changes. No missing-value success fallback. |
| Browse | Empty result. Short pages. All necessary continuations. Reused token. Wrong/expired token. Early release. Changed Session. Page/reference limits. No first-page uniqueness inference. |
| FileTransfer | Short nonempty chunks. Binary/JSON/zero-byte documents. Unknown Size. Premature EOF. Overlong Read output. Missing Open/EOF/Close. Wrong/reused/cross-Session/cross-Object handle. Read mode and positive Int32 length. |
| Failure cleanup | Failed Open has no handle. Read error still closes. Cleanup error retains primary error. Limits close. Locked/denied/missing/transport statuses stay distinct. No silent redirection or fallback. |
| Capture | Changed default/Version/epoch/Size, missing after observations, incomplete sequences, exact byte/event/reference budgets, unverified versus observed state. |
| Export | Every pointer resolves locally. Resource has no default projection. Meta/Version epochs stay distinct. Same-type one-hop/dangling/chained `xref`. No remote absolute `xref`. Metadata-only Version has no document fields. |
| NamespaceFile | Refresh then inherited file read. Existing file without refresh. Missing/denied ExportNamespace. No direct document output, fake generic Registry resolver or standard Import. |

The helper intentionally does not implement live discovery, certificate or
TypeDefinition verification, general service decoding, arbitrary export
generation, write APIs, recursive federation or a production client.
