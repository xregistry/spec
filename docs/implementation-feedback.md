# Implementation feedback

## Built-in model compilation: 2026-09-11

The independent xregistry-dotnet model compiler found invalid artifacts while
compiling all published domain models, rather than only parsing their JSON.

- CloudEvents model include fragments used `#groups` instead of the RFC6901
  `#/groups` required by Core. The fragments were corrected.
- Endpoint `usage` used the Core scalar `enum` aspect on an array and omitted
  its required flag. Its model now declares a required array of strings;
  allowed roles and their protocol-specific combinations remain normative
  domain rules, not a new Core array aspect.
- Schema regeneration exposed incomplete `$includes` handling and incorrect
  local/nested include precedence in the generator. The local resolver now
  preserves source values, ordered includes and each included document's base,
  rejects cycles and invalid fragments, and has explicit expansion bounds.

The affected Endpoint/CloudEvents JSON Schema, JSON Structure, Avro and OpenAPI
artifacts were regenerated. `tools/test_implementation_model_regressions.py`
reproduces the model and generator issues; the focused generator/regression suite
passes. The .NET implementation keeps original and corrected byte hashes and
checks all seven models through an explicit packaged resolver.

No OPC UA specification was changed. These are model-artifact and generator
corrections, not changes to the rc4 HTTP protocol or Endpoint role semantics.

## Calendar-valid examples: 2026-09-11

Eleven CloudEvents modification timestamps used April 31 after an April 30
creation timestamp. The .NET validator and Python calendar parser independently
rejected them. The examples now use May 1, preserving next-day ordering.
`tools/test_implementation_timestamp_regressions.py` guards valid dates and
ordering without relaxing the Core timestamp rules.

## HTTP discovery response shape: 2026-09-11

The HTTP discovery response sketch used object braces around a list of URL
strings. Replacing its repetition metavariable with a concrete URL still
produced invalid JSON. Core's Host-based and Registry-based discovery sections
both require an array. The HTTP sketch now uses that same array shape.
`tools/test_implementation_discovery_regressions.py` reproduced the JSON parser
failure before correction and verifies the concrete payload afterward.

The .NET client independently exercises both distinct discovery locations:
Registry-relative `.xregistry` and host-origin `/.well-known/xregistry`. The
latter already exists in Core; recognizing it corrects an implementation-plan
assumption, not the specification. Advertisements are data, not authorization
to follow their URLs.

## Escaped Core XID components: 2026-09-12

A clean .NET package consumer exposed a mismatch when a live HTTP Registry
serialized valid `:` and `@` identifier characters as `%3A` and `%40` in its
`self`/`xid` paths. Core defines `xid` as the corresponding relative URI path;
the offline federation example validator incorrectly applied the decoded ID
grammar directly to escaped components.

The validator now validates escapes, decodes each component exactly once with
strict UTF-8, and applies the unchanged Core ID grammar to the decoded value.
It preserves the original XID string and still rejects encoded separators,
controls, malformed UTF-8 and second-decode candidates. The .NET reader now
compares typed identities without rewriting source wire metadata.
`workingdrafts/federation/tools/test_implementation_xid_regressions.py`
reproduces the rejected valid paths and guards invalid partitions. The old
regression treating a valid escape as an invalid ID now checks a genuinely
invalid second-decode candidate. No OPC-UA-specific file was changed.

## Canonical native routing keys and decoded mapping identities: 2026-09-12

The native OCI implementation exposed a bounded-lookup ambiguity in the
unreleased draft: `/items/%61%3Aone` sorts before a split at `/items/a`, while
its URI-equivalent selector `/items/a%3Aone` sorts after that split. No bounded
choice of alternate spellings can guarantee complete lookup of arbitrary
percent-escaped keys without changing the byte-order contract or scanning the
whole graph.

The corrected version-1 draft requires canonical URI-component spelling for
internal graph identity annotations and finite routing bounds: strict one-pass
decoding, unchanged case-sensitive Core IDs, literal unreserved characters and
uppercase escapes for the other allowed characters. Selectors normalize before
routing. Portable config XIDs may keep a URI-equivalent spelling; config bytes,
domain URLs, document bases and Document bytes remain unchanged. Old
noncanonical draft graphs require explicit regeneration/migration, never a
silent relabeling or an alternate-spelling fallback.

The complete directory-mapping indexes have no such shard ambiguity. Their
interpreter and schema now accept valid URI escapes, compare decoded typed
identities, and use decoded map keys and resolving fragment pointers while
preserving stored XIDs and exact descriptor commitments. Tests exercise the
same interpreter through File and managed Git.

`workingdrafts/bindings/tools/test_implementation_uri_key_regressions.py`
contains the independent range counterexample and decoding/schema cases. The .NET
`NoncanonicalRoutingKeysAndBoundsAreRejectedWithoutRewritingPinnedObjects`
regression failed before the canonical-key guard, then passed along with
bounded one-leaf routing and retained Document bytes. Full validation remains
distinct from a selective lookup's evidence about its consumed path.

## Pagination HTTP expiry format: 2026-09-12

The pagination HTTP binding labelled its expiry-format reference as RFC3339
while linking to RFC7234 section 5.3. The linked HTTP specification defines
`Expires` as `HTTP-date`, not an RFC3339 timestamp. A raw HTTP integration case
now checks the literal value `Tue, 01 Jan 2030 00:01:00 GMT`, its unchanged
deadline on later pages, and cursor expiry at that deadline. The implementation
already emitted the correct HTTP format; this was a citation/wording defect.

The example's `Thu, 01 Dec 2021` also had the wrong weekday. The corrected
example keeps the same UTC date/time and uses Wednesday. Independent Python
regressions in `tools/test_implementation_timestamp_regressions.py` failed on
both original defects before the prose change. No wire format, cursor lifetime,
count semantics, or OPC-UA-specific source was changed.

## Schema Registry Protobuf example declarations: 2026-09-12

All four inline Protobuf strings in the Schema Registry's three-Version
example ended with an unmatched second closing brace. The .NET Protobuf
validator rejected each independently with `protobuf.brace`; eight executions
across the two target frameworks reproduced the error before any correction.
The example now removes only that unmatched brace, preserving the `Metrics`
message name, field types/names/numbers, Version lineage and default projection.

The independent model-regression script pins the intended four declarations.
The .NET example tests read and validate the captured successor text, while
retaining the original invalid strings as negative cases. This corrects the
example, not the schema language or validator. For metadata-body requests,
text Documents still require the appropriate non-JSON `contenttype`; the
abbreviated example omits other Version attributes rather than defining a new
format-based media-type inference rule.

## Message declaration names and shapes: 2026-09-13

Compiled model calls rejected several declarations that the normative Message
and Endpoint prose explicitly permits. Independent Python source regressions
and twelve .NET executions reproduced the inconsistencies before correction:

- Message Model Source now declares `basemessage`, matching its normative
  attribute, rather than the otherwise undocumented `basemessageuri`.
- HTTP options include `status` and represent `query` as a string map. The
  contradictory array-shaped example now matches the table and normative prose.
- NATS uses the normative `reply-to` name, not `reply`.
- AMQP's optional `subject` declaration defaults `required` to false. This
  does not change CloudEvents' distinct mandatory attributes.
- Endpoint `messagegroups` targets the Message Group type, not individual
  Messages. A declaration remains data, not authorization to fetch that target.
- The MQTT table now uses the already-modeled `payload_format_indicator`
  spelling for the MQTT 5 Payload Format Indicator property.

The affected Message, Endpoint and CloudEvents schema outputs are regenerated
from those source models. `tools/test_implementation_message_contracts.py`
guards the reconciled contracts. Existing typed-property/template representation
issues are separate; these corrections neither loosen generic Core validation
nor add undocumented effective-model aliases.

## OpenUSD shared Resource identity: 2026-09-13

Section 4.4 defines plugin `usdassets` as the same Resource type as asset-container
`usdassets`, and Section 5.3 permits Core one-hop aliases of that type. The model
instead contained two similar independent definitions. Under Core, structural
similarity does not establish Resource type identity, so compiled .NET models
rejected cross-Group aliases before reaching the OpenUSD manifest checks.

The plugin Group now uses `ximportresources` to import
`/usdassetgroups/usdassets`. This is the existing Core type-sharing mechanism;
the compiler and alias validator were not weakened. Plugin-specific role,
format and manifest-name rules remain domain constraints on the containing
Group. There are no checked-in OpenUSD derived schemas to regenerate.

The independent
`workingdrafts/models/openusd/tools/test_implementation_openusd_model_regressions.py`
and public .NET type-identity/alias cases reproduced the defect before
correction. The original duplicated model is retained in the implementation's
immutable baseline, with the import represented as a successor artifact.

## Typed Message property declarations

The Message model represented literal property values as Core strings. This
rejected boolean/numeric/structured constraints and `specurl`, constrained URI
refinements incorrectly, and applied Core metadata-name rules to AMQP symbols.
Changing only `value` to Core `any` would still remove an explicit null during
Core attribute completion, making a required literal-null constraint impossible.

CloudEvents envelope declarations and the five AMQP property-declaration
sections are now opaque domain objects in the Core model. Their object shape,
names, typed literals, required/type defaults and fixed-property constraints
remain mandatory procedural Message rules. This preserves literal null and
protocol names without weakening Core deletion, identifier or scalar semantics.
The .NET implementation validates and completes those declarations explicitly.

The CloudEvents text now agrees with its model/examples that declarations are
flat, without an `attributes` wrapper. The nonexistent "RFC3339 Duration"
reference is replaced with an explicit ISO 8601/XML Schema duration profile;
AMQP UUID/unsigned integer representations and media-symbol text are clarified.
The original artifacts and independently failing .NET/Python examples remain
retained by the implementation. Derived Message/Endpoint/CloudEvents schemas
are regenerated as structural projections, not substitutes for domain checks.

## OpenUSD collision assignment and bounded resolution

The closed-form lookup claim could not coexist with sibling-dependent
disambiguation: an assigned fallback can survive deletion of its competitor,
and adding a nine-character suffix to an untruncated 120-128 character candidate
exceeds Core's ID limit. Eight hexadecimal hash characters also do not guarantee
uniqueness; two independently verified URI sources collide at `df41192b`.

The draft now separates unchanged candidate construction from stable assignment
against explicit sibling reservations. It defines one suffix-reserved fallback,
preserves published source-to-ID bindings, rejects secondary collisions and
forbids JSON member order as a tie-breaker. Consumers probe at most the candidate
and fallback, verify exact authoritative metadata, and do not confuse policy,
transport, parse or quota failures with absence. No artifact acquisition is
implicit in this lookup.

Independent prose/example guards reproduce the old ambiguity, and .NET public
assignment, lookup and Server tests cover real collisions, boundary lengths,
restart, retargeting, atomic reservations and no-overwrite behavior. These
corrections preserve noncolliding published examples, exact-source hashing and
one-pass identifier decoding; they do not claim publisher authenticity.

## Endpoint authoring and consumer materialization

The Endpoint draft permits Level-1 placeholders in protocol-option string
values and Map keys, but the model rejected templated URI values, Map keys
and string enums before an evaluating client could substitute them. Merely
changing a URI leaf could not represent templated keys; changing Core's shared
grammar would incorrectly weaken every model.

The six known protocol-option Maps now have opaque authoring boundaries.
Known JSON types, object shapes and structural record names remain checked;
quoted Boolean/Number placeholders are not coerced. Consumer-only protocol,
address and enum semantics remain separate from passive storage validation.
The .NET consumer preserves authored and resolved metadata independently,
uses bounded RFC6570 Level-1 expansion, and performs no implicit acquisition.
The source-model rejection cases are retained and Endpoint/CloudEvents
structural schemas are regenerated from the corrected source.

## Message header references and binary protocol values

The four HTTP, NATS, MQTT and Kafka header/property declaration records omitted
the common `specurl` attribute. It is now an optional Core URI in each record.
The MQTT model also represented binary `correlation_data` as a URI template and
represented the MIME `content_type` as a URI template while its prose called it
a symbol. A valid `application/json; charset=utf-8` declaration was rejected.
Binary data now uses a base64 string, and media types use strings with the
existing procedural content-type checks and permitted placeholders.

The .NET Server reproductions cover common-reference round trips, exact and
empty binary values, malformed/noncanonical base64 rejection before publication,
and the normal MIME parameter case. Structural schemas are regenerated from the
corrected Message source and the active Endpoint authoring source.

## Metadata-only Resource names do not become Document fields

Directory mapping prohibited `<RESOURCE>`, `<RESOURCE>base64` and
`<RESOURCE>url` by spelling even for `hasdocument: false`. Core allows those
names as ordinary model-admitted metadata when the Document feature does not
apply. Both the .NET reader and the independent mapping writer/reader rejected
legal captured values before correction.

Mapping now applies Document detachment/URL rules only to document-bearing
Resources. Metadata-only Resources still require `document.kind: none`; their
ordinary fields remain subject to the captured model and are neither decoded
nor dereferenced. Actual Document fields remain forbidden in detached local
Version metadata, and Document requests on metadata-only types remain
`unsupported_operation`. No generic Core field rule was weakened.

The native OCI binding had the equivalent conflict, including silent omission
of required defaults for ordinary singular/base64-named fields. Its producer,
reader and independent oracle now apply these reservations only to
document-bearing types. Captured nulls remain metadata unless Core supplies an
effective default. All existing placeholder, mode, routing, digest, closure and
credential checks remain in force; metadata-only Document operations remain
unsupported. The generic OCI record schema required no change.

The three negative OCI field controls are separate test methods rather than
`unittest.subTest` cases. Pytest 9 counted successful subtests in its XML total
without emitting corresponding testcase records, defeating exact independent
case accounting. Splitting the controls preserves every assertion and gives
each control an auditable test identity; the .NET repository's fail-closed
oracle accounting was not relaxed.

## Catalog priority uses Core unsigned-integer values

The Catalog model declares `priority` as Core `uinteger`, but procedural checks
treated it as a digits-only JSON token. This rejected `0.0`, `1e0` and negative
zero even though the compiled model and JSON Schema admit their nonnegative
integer values. It also prevented exact decimal/exponent priorities from
participating in stable numerical ordering.

The prose now makes its existing numeric-value constraint explicit. .NET
validation and selection use the shared bounded exact-number implementation;
the independent oracle accepts exact `Decimal` inputs as well as integer-valued
finite numeric inputs. Fractional, negative, nonfinite, string and boolean values
remain invalid. No numerical token is rewritten, and priority never overrides
caller selection or policy. The raw model and generated schemas need no change.

The Registry model's existing resolvable-description vector now also treats
`priority: 0.0` as a successful selection. Its generated-schema checks and exact
selected-object assertions are retained; only the obsolete lexical-rejection
expectation changes. The full oracle run exposed this remaining coupled fixture
after the focused priority and federation suites had passed.

## Common Message header declarations

The header records of HTTP, NATS, MQTT and Kafka omitted the common `type`
field; MQTT also omitted `required`. Core object normalization could delete
invalid null members before domain validation, and Kafka could not retain a
literal null byte-value constraint. The item boundaries are now opaque logical
declarations with explicit domain validation and defaults, retaining the outer
array/map kinds and order.

The prose distinguishes a native string refinement from an invented wire codec.
Textual headers cannot silently coerce booleans, numbers or objects to strings;
Kafka's binary and nullable byte values have explicit JSON representations.
The .NET Server and materializer share the declaration validator, including
required-name, member/type checks, defaults, refinement syntax and canonical
base64. The four common fields and raw/null failure cases have public regression
coverage. Core's generic object/null semantics remain unchanged.
