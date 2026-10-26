# WoT Channels, Snapshots and Dependency Bindings

<!-- words: bytewise jsonld namespace opcfoundation prerelease prereleases -->
<!-- words: submodel subthing tds tms ua uav unversioned versionid xids -->
<!-- words: workflow workflows lockfile marcschier compatibilityline -->
<!-- words: href nodeids opc REQUIREDEXTENSIONS standalone -->
<!-- words: workingdrafts -->

## Decision and status

Use the [generic xRegistry publication extension][Publication] for channels and
immutable snapshots. WoT defines dependency closure and compatibility
validation, not another channel API or another Group hierarchy.
This is an informative implementation design, not an implemented WoT
profile. The current SemVer specification and its vectors remain unchanged.

The generic proposal supplies a reusable model, manifest schema, conditional
head semantics, HTTP open context and offline byte bundle. Its executable
examples demonstrate synthetic state transitions and integrity only.
The WoT profile below still needs resolver/provider integration and
cross-repository fixtures before deployed conformance can be claimed.

## What is versioned?

| Entity | Identity and behavior |
| --- | --- |
| Document revision | Exact bytes and fixed metadata in one Resource history. |
| Compatibility line | Domain declaration of compatible incremental revisions. |
| Snapshot | Exact model/metadata, revisions and dependency bindings. |
| Channel | Mutable scoped name selecting a snapshot. |
| Source release | Capture provenance, not a revision or snapshot ID. |

An unchanged document revision can appear in many snapshots. Each channel
can cross compatibility lines as its publisher decides. A consumer's
compatibility requirement still applies to the selected head.
No Group stands for a channel, snapshot or compatibility line.

A channel resembles a Git branch only as a mutable head with cheap forks.
The manifest's OPTIONAL parent records preparation history. There is no
automatic merge, rebase, working tree or Git protocol. Reconciliation
produces another complete validated snapshot.

## A complete WoT publication

A domain-complete snapshot includes every entry document, the transitive
TM/TD dependencies used to interpret it, their fixed metadata, original
reference bases, and one exact binding for every recognized external
reference occurrence. Domain bytes remain unchanged.

The closure extension URI is:

`http://opcfoundation.org/UA/WoT-Binding/publication-closure/1`

Its value in the generic manifest's `extensions` map is a checked descriptor
of a `wot-publication-closure/1` JSON document. A domain-complete publication
lists that URI in `requiredExtensions`. A generic reader that does not
understand it fails rather than claiming WoT-complete interpretation.
The [schema](schemas/publication-closure.schema.json) defines its shape.

`entries` lists Version XIDs from the captured Registry view.
Each `bindings` record contains:

| Field | Meaning |
| --- | --- |
| `source` | Exact source Version XID in the captured view. |
| `pointer` | RFC 6901 pointer to the authored reference object. |
| `operator` | WoT relation/operator in the source's captured contexts. |
| `href` | Exact authored reference string, including any fragment. |
| `target` | Exact target Version XID in the same captured view. |

Document digests, originating Registry/Version identities and original bases
come from the generic manifest's document associations. Profile and line
expectations come from the captured trusted metadata. Duplicating them in
each binding would introduce competing authorities.

The profile recognizes `tm:extends`, `tm:submodel`, `tm:ref`,
`td:extends`, `td:subthing`, `td:ref`, TD `type` links and projection-source
references already defined by the WoT draft. The schema deliberately permits
operator strings so the existing vocabulary/contexts remain authoritative;
an unknown operator cannot satisfy closure validation.
Interaction endpoints, documentation and arbitrary application links are not
dependencies merely because they are URLs.

The producer enumerates references independently from the emitted binding
table, applying the WoT draft's context, fragment and composition rules.
Local fragment references stay within their source document and need no
external binding. Every external occurrence needs exactly one binding.
For a `links` item, `pointer` identifies that item. For `tm:ref`/`td:ref`,
it identifies the object containing that member. Source bytes need to contain
the stated operator and exact `href` at that object.

The producer materializes external dependencies as exact Versions in the
captured view, preserving their source associations. Binding identity is
`(source, pointer)`, not the authored target ID. Two occurrences can resolve
the same logical authored ID to different exact revisions.
The target's bytes and fragment need to satisfy the actual source reference;
an existing Version with unrelated bytes is not a valid binding.

Entries, sources and targets need to exist in the generic document associations.
Bindings need to be unique and cover the complete reachable closure from the
entries, without unreachable or invented edges. Graph traversal tracks visited
Version/reference pairs; acceptance of a cycle follows the composition
operator's existing rules. Traversal is bounded even when a cycle exists.
All JSON-LD context material needed to interpret captured documents is also
retained immutably or resolved through a supported immutable context set;
offline interpretation does not fetch live contexts.

## Selection and acceptance

Opening a channel selects its current immutable manifest once. Every entry,
dependency read and page in that operation stays in that snapshot.
Missing closure data fails; it never causes live highest-version resolution.

Snapshot-bound composition first selects the bound exact revision, then
validates the source reference's requirement and caller acceptance policy.
Incremental targets need the declared compatibility line and any numeric
floor. SemVer targets retain their target-kind floors, next-major bounds
and prerelease rules. Conflicting trusted declarations fail.
The snapshot determines content; it does not waive those requirements.

The standalone live resolver still selects the highest qualifying revision
under [D7](versioning-design.md#d7-selection-defaults-and-exact-pins), including
its sticky-default rule. A captured default describes that snapshot's raw
Resource read; it cannot replace an explicit dependency binding.
The existing raw exact-pin retrieval path still bypasses live floor/default
selection. It is not compatibility-validated snapshot composition.

For example, entry E in snapshot S12 binds a line-A dependency to revision 42.
The author publishes revision 43/B. Opening S12 still reads 42/A.
Channel `preview` can advance to S13 with 43/B, but a caller requiring A
rejects that head. It does not search earlier snapshots for an A candidate.
Changing the authored requirement or choosing another channel is explicit.

## Publication and user workflows

The existing [63 workflows](versioning-design.md#publisher-workflows)
continue to define per-document publication, selection, exact replay and
migration. These additional workflows explain set publication and its
relationship to compatibility. Each uses the generic publication contract.

### N01. Convert a versioned companion specification

Record the standard's release as provenance. Reuse unchanged document
revisions; allocate only changed ones. Resolve/validate the complete set,
persist a manifest, then conditionally move the channel. Conversion failure
leaves the old head.

### N02. Capture a server model revision

Record the server identity/model revision and capture method. Verify a real
consistency mechanism or disclose best-effort observation. Immutable output
does not prove atomic source capture. Reject capture if the caller demands
a guarantee the server lacks.

### N03. Publish an individual edit

Start from S12; replace one entry or dependency revision and retain other
exact associations. Validate every affected edge and publish S13.
Unrelated document revision IDs do not change.

### N04. Change one document incompatibly

Assign its new compatibility line and revision. Bind accepting entries to
it in a new snapshot; keep other entries' exact dependencies. Consumer
requirements can reject the new head. Publication does not redefine them.

### N05. Fork development

Create `preview` pointing to S12. Both channels initially share the same
manifest and bytes. Later head changes are independent; deleting a channel
never authorizes reuse of its old Resource identity.

### N06. Reconcile two publishers

Both read epoch 12. One publishes S13; the other's conditional update fails.
Read the new head, reconcile deliberately and create another complete
snapshot. Do not overwrite the winner or silently merge JSON.

### N07. Promote a reviewed set

Conditionally point `stable` at the exact reviewed manifest. No new document
revisions or snapshot are needed. A concurrent stable-head change fails
promotion until reviewed again.

### N08. Roll back activation

Conditionally restore S12 and advance the channel epoch. Ongoing operations
remain on their already pinned snapshots. Existing deployment activation
is still a separate caller operation.

### N09. Recover a timed-out head update

Read back head/epoch and reconcile. A matching head can satisfy the objective
without proving which request wrote it. Reuse the immutable manifest rather
than repeating anonymous document uploads.

### N10. Export and replay offline

Retain manifest, Registry metadata, context material, closure and exact bytes.
Use the byte bundle's URL map without origin network access. Missing,
corrupt or unsupported material fails; raw cached documents alone are
insufficient.

### N11. Federate a channel

Open each moving source once and retain its pin/context. Apply whole-Resource
precedence without replacing binding targets. Reproducible combination needs
exact source pins, model/policy, or a materialized combined snapshot.
Distinct source captures are not simultaneous.

### N12. Refresh, retain or revoke

Refresh opens a new head for review; old pins stay exact. Retain reachable
content under policy. Explicit revocation/deletion can make replay unavailable;
report it instead of substituting new content.

For N01/N02, a source's simple incremental model revision is sufficient as
provenance. It is neither forced into SemVer nor copied into every changed
document's registry revision. Individual authors use the same publication
protocol without manufacturing a product-wide release number.

## Validation and implementation boundary

The closure schema checks shape only. Adapter/resolver integration needs to
independently rediscover edges from source bytes, verify context expansion,
match pointers/operators/targets, check compatibility, and enforce bounded
transitive traversal. Planned negative fixtures include omitted/replaced
edges with all digests recomputed, wrong source bases, conflicting declarations,
missing context material and a dependency smuggled into an unrelated entry.

The generic proposal's tests do not establish those WoT semantics. The
existing 64 SemVer vectors also do not establish them. OPC UA mappings need
the same context and closure semantics, with append-only generated NodeIds;
this design pass does not change the `1.1-draft` model or either .NET runtime.

The [shape example](samples/publication-closure.json) illustrates one binding,
not an independently complete snapshot. Five schema checks cover its shape
and malformed pointers/missing targets. They do not validate authored bytes
or prove dependency closure.

[Publication]: https://github.com/xregistry/spec/blob/3d3f261bb8741df9dbdac1db4e8f64569de7a0cf/workingdrafts/publication/spec.md
