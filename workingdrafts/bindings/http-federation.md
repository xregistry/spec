# xRegistry HTTP Federation

<!-- words: federationprofiles modelsource weburl xregurl xid xids -->
<!-- words: revalidation revalidate revalidated etag etags nfc -->
<!-- words: readme reparsing uncacheable validators website -->

## Abstract

This specification maps the read operations of
[xRegistry Federation](../federation/spec.md) to the existing
[xRegistry HTTP binding](../../core/http.md). It adds catalog bootstrap,
binding selection and capture requirements, not another HTTP API.

**Status:** Unreleased working draft, using xRegistry Core Version 1.0-rc4.
Neither this document nor a catalog advertisement asserts compatibility
with an earlier release candidate.

## Table of Contents

- [Notations and Scope](#notations-and-scope)
- [Motivation and Example](#motivation-and-example)
- [Advertisement and Bootstrap](#advertisement-and-bootstrap)
- [Registry Root and Version Discovery](#registry-root-and-version-discovery)
- [Native Read Mapping](#native-read-mapping)
- [Metadata, Documents and Versions](#metadata-documents-and-versions)
- [Literal Label Selection](#literal-label-selection)
- [Pagination and No-Filter Fallback](#pagination-and-no-filter-fallback)
- [HTTP Validators and Partial Content](#http-validators-and-partial-content)
- [Redirects and Authorization Boundaries](#redirects-and-authorization-boundaries)
- [Live Capture and Errors](#live-capture-and-errors)
- [Conformance and Offline Examples](#conformance-and-offline-examples)
- [References](#references)

## Notations and Scope

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" are to be
interpreted as described in [RFC2119][rfc2119].

Core owns entity types, IDs, labels, default Versions, `xref`, document
view, errors and request flags. The HTTP binding owns methods, paths,
`$details`, HTTP metadata headers and the wire representation of flags.
[HTTP Semantics][http] and [HTTP Caching][cache] own HTTP processing.
Requirements here apply to federation resolvers. They do not turn an
OPTIONAL Core API into a mandatory server API or redefine CRUD operations.

In the tables, `B` is the selected Registry root URL, `G` is
`/<GROUPS>/<GID>`, `R` is `G/<RESOURCES>/<RID>`, and `V` is
`R/versions/<VID>`. Collection names come from the selected model.
`B + path` means append below the Registry base path, with one separating
slash. It does not mean resolve a leading-slash URI against the host.

## Motivation and Example

An existing xRegistry HTTP service can participate in federation without
implementing another API. A consumer-side resolver can use its catalog entry
directly, or a federating API server can access it as a source on behalf of
ordinary HTTP clients.

For example, a source advertised at
`https://first.example.com/services/xreg/` can supply
`/documents/main/assets/item`. The resolver reads metadata from that
Resource's `$details` URL, obtains the explicit default Version choice and
reads the selected document through its Version URL. The server hosting
the consumer-visible Registry can perform those steps after a local Resource
miss. A local shadow Resource takes precedence as described by the
[shared resolution model](../federation/spec.md#design-resolving-a-consumer-request).

This binding preserves the source's HTTP capabilities, pagination,
conditional requests and authorization boundaries. A catalog describes an
access method. It does not prove that a live HTTP read is an immutable
snapshot or that unsupported query flags will be honored.

## Advertisement and Bootstrap

An HTTP advertisement has `name: "http"`, an absolute HTTP(S) Registry-root
`endpoint`, and no parameters in this version. Its endpoint MUST NOT have
embedded credentials, a query or a fragment. Unknown parameters on the
selected advertisement MUST produce `unsupported_operation`.

```json
{
  "name": "http",
  "endpoint": "https://first.example.com/services/xreg/",
  "priority": 0
}
```

Selection, priorities, ties and implicit `xregurl` handling follow
[Federation discovery](../federation/spec.md#discovery-and-binding-selection).
If explicit HTTP advertisements coexist with `xregurl`, one endpoint MUST
match `xregurl` exactly. `weburl` is a website, not an API fallback.

A resolver bootstrapping from a catalog MUST read the catalog model before
interpreting its `categories` / `registries` collections. These catalog
Resources have `hasdocument: false`. Their Version metadata contains
`xregurl`, `weburl` and any `federationprofiles`. It is not a domain
document to download. An explicit catalog-description Version selects that
Version. Otherwise, the catalog Resource's Core default Version applies.
The described Registry's `registryid` need not equal the catalog entry ID.

The chosen advertisement establishes a new Registry context. The resolver
MUST discover the target's version, model and capabilities independently
of the catalog. It MUST NOT transfer catalog credentials, compatibility
assumptions or label requirements to that target.

## Registry Root and Version Discovery

The advertised root can have an arbitrary base path. For example, XID
`/documents/main/assets/item` at
`https://first.example.com/services/xreg/` is below
`/services/xreg/documents/main/assets/item`, not `/documents/main/assets/item`.
The root request uses the advertised root itself. Descendant construction
MUST retain its complete base path, preserve case-sensitive Core IDs and
encode URI path segments without double encoding. A resolver MUST NOT
derive global entity identity by splitting an arbitrary URL.

The HTTP binding's `Link` with `rel=xregistry-root` identifies the serving
Registry root when provided. A resolver MUST interpret it in the response
context and apply the same locator policy as for other links. A relocated
root does not silently authorize access to a different origin.

The resolver MUST obtain `specversion` from the Registry representation
before interpreting model-dependent entities. A known, explicitly supported
Core version is necessary. Parsing JSON is not a compatibility check.
An unsupported version MUST produce `unsupported_version`. If supported,
Core's `specversion` flag can request a compatible representation, but the
resolver MUST verify the version actually returned. Silently ignoring a
query parameter MUST NOT be mistaken for successful negotiation.

`GET B/model` retrieves the interpreted model. `GET B/modelsource`, when
available, retrieves the client-provided source and preserves information
such as shared Resource type definitions. These are different documents.
A missing model source is not an empty effective model. `{}` from a
supported `/modelsource` has its Core meaning.

`GET B/capabilities` retrieves enabled capabilities. A resolver MAY use
already inlined capabilities or request supported inlining. It MUST NOT
assume that `filter`, `inline`, pagination, `/export` or writes are enabled.
Before composing the selected view, it MUST apply the shared
[resolution-owner signal](../federation/spec.md#signaling-who-performs-resolution).
`federation.resolution: "producer"` means read the view directly without
traversing its catalog. An absent signal defaults to consumer resolution.
An absent capabilities API, an absent flag, or `flags: null` provides no
positive evidence for that flag. `/capabilitiesoffered` describes choices
that can be enabled, not what is currently enabled.

When an OPTIONAL read API is unavailable, a resolver MAY use an equivalent
already obtained representation, a supported inline request, or an
advertised Core `/export` document. It MUST preserve the requested view
and completeness. If no equivalent read exists, it MUST return
`unsupported_operation`, not an invented empty entity or collection.

## Native Read Mapping

These are mappings of the common abstract requests, not new request
envelopes sent to the server. `model` and `capabilities` use abstract target
`/`. `/model` and `/capabilities` below are HTTP API paths, not entity XIDs.

| Abstract operation and target | Native HTTP request | Result |
| --- | --- | --- |
| `entity`, `/` | `GET B` | Registry metadata. |
| `collection`, `/<GROUPS>` | `GET B/<GROUPS>` | Map keyed by Group ID. |
| `entity`, `G` | `GET B + G` | Group metadata. |
| `collection`, `G/<RESOURCES>` | `GET B + G/<RESOURCES>` | Map keyed by Resource ID, containing Resource metadata. |
| `entity`, `R`, document-bearing type | `GET B + R$details` | Resource metadata, including the default Version projection in API view. |
| `entity`, `R`, metadata-only type | `GET B + R` | Resource metadata. `$details` is also accepted by Core but is unnecessary. |
| `entity`, `R/meta` | `GET B + R/meta` | Resource Meta entity, not default Version metadata. |
| `collection`, `R/versions` | `GET B + R/versions` | Map keyed by Version ID, containing Version metadata. |
| `entity`, `V`, document-bearing type | `GET B + V$details` | That Version's metadata. |
| `entity`, `V`, metadata-only type | `GET B + V` | That Version's metadata. |
| `document`, `R`, document-bearing type | `GET B + R` | Default Version document or Core external-document redirect. |
| `document`, `V`, document-bearing type | `GET B + V` | Explicit Version document or Core external-document redirect. |
| `document`, metadata-only `R` or `V` | No document request | `unsupported_operation`. The unsuffixed URL would return metadata. |
| `model`, `/` | `GET B/model`. `GET B/modelsource` when available | Effective model and available source, kept distinct. |
| `capabilities`, `/` | `GET B/capabilities` or equivalent enabled map | Enabled capabilities for this endpoint and caller. |

Collections do not take `$details`. Meta, Group and Registry URLs do not
take it either. `Accept: application/json` does not replace `$details`:
a domain document can itself be JSON.

The existing `GET B/export` convenience path, if supported, is precisely
`GET B?doc&inline=*,capabilities,modelsource` with Core's flag semantics.
It is not a federation-specific snapshot API. A resolver consuming an
export MUST resolve document-local pointers within that returned document.

## Metadata, Documents and Versions

Resource metadata, the Meta entity and Version metadata are separate views.
In particular, a Resource's API-view `versionid` is the default Version
projection, whereas `meta.defaultversionid` records the choice. A resolver
MUST NOT choose a default by lexical order, modification time, enumeration
order or the greatest Version identifier.

An explicit Version target MUST select that exact, case-sensitive Version.
When a multi-request operation needs both default metadata and bytes, the
resolver SHOULD record the selected default Version ID and use its explicit
Version URLs for subsequent requests. It MUST detect a changed selection
when claiming a consistent capture. Version IDs themselves do not make a
live Version immutable.

For document-bearing types, body `self` links to Resource/Version metadata
include `$details` in API view, as specified by Core HTTP. Metadata-only
types' `self` links MUST NOT include it. In document view, pointers are
relative to the returned JSON and never include `$details`. The resolver
MUST preserve Core navigation semantics rather than replace `self` with an
endpoint label.

Raw document reads use the domain media type and bytes. Core's
`xRegistry-` headers carry accompanying metadata. `Content-Location`, when
present on a default read, identifies the default Version as Core specifies.
A zero-byte document is a successful empty byte sequence, not a missing
document. Absent content and metadata-only types MUST remain distinguishable.
For byte-preserving capture, raw Version reads or supported Core `binary`
serialization are appropriate. Reparsing and pretty-printing JSON is not
byte preservation.

Core `meta.xref` remains same-Registry, same Resource model type and one hop.
Source IDs and navigation remain source-relative. A dangling target or a
target that is itself an alias keeps Core's minimal source serialization.
Document view MUST NOT expand an alias. Document-view requests below its
`versions` preserve `cannot_doc_xref`. Federation MUST NOT reinterpret an
absolute remote URL as `xref`.

A Version's `<RESOURCE>url` identifies domain content, not a remote
metadata alias. Following it does not merge remote Versions, rewrite source
IDs or change the selected Registry context.

## Literal Label Selection

The common selector is an exact label-key lookup and a Core
case-insensitive comparison of string values. Labels are OPTIONAL. Values
can be empty. An absent label does not match an empty value. The resolver
MUST NOT require a language label, impose NFC normalization, infer a locale
from a category, or interpret the caller's `*` as a wildcard.

A supported HTTP filter is an optimization. The resolver MUST construct
Core dot notation relative to the requested collection and preserve literal
meaning. It MUST escape a literal wildcard using Core's backslash escape
before URI encoding. It MUST quote label keys containing dot-notation
operators using Core bracket notation. For example:

| Selector | Core expression before URI encoding |
| --- | --- |
| `{"label":"stage","value":"PRODUCTION"}` | `labels.stage=PRODUCTION` |
| `{"label":"note","value":""}` | `labels.note=` |
| `{"label":"note","value":"A*B"}` | `labels.note=A\*B` |
| `{"label":"release.channel","value":"stable"}` | `labels['release.channel']=stable` |

One encoded literal-wildcard request is:

```http
GET /services/xreg/documents/main/assets?filter=labels.note%3DA%5C%2AB HTTP/1.1
Host: first.example.com
```

The common selector is narrower than Core's filter language. For example,
the literal string `null` is not Core's missing-attribute expression.
If literal commas, quotes, backslashes or other syntax cannot be represented
unambiguously by a supported filter, the resolver MUST use local selection
over an unfiltered collection rather than invent an escaping extension.
URI encoding alone does not escape Core expression syntax.

The resolver MUST apply the same literal comparison to returned candidates
even when filtering was requested. Core permits unsupported query flags to
be ignored. A nonempty response therefore does not prove that the filter
was implemented.

## Pagination and No-Filter Fallback

A resolver MUST process collection pages according to the
[pagination specification](../../pagination/spec.md). It MUST follow each
necessary `Link` with `rel=next`, resolve a relative link against the
response request URL, and then use that link without editing its query.
It MUST NOT synthesize page numbers, reattach the original filter, or add
`limit` to subsequent links. Pagination links have the same credential and
locator policy checks as redirects.

Unique label selection requires the complete relevant candidate set. A
match on the first page is not proof of uniqueness. No match after complete
enumeration yields `not_found`. A second match yields `ambiguous`.
An unavailable later page or a traversal limit MUST NOT become either a
unique result or `not_found`. Conflicting duplicates, changed declared
totals or an incomplete capture MUST be reported, not silently merged.

If filtering is unavailable, the resolver MUST enumerate the relevant
unfiltered collection and apply the common selector locally. This applies
to no-code endpoints as well as API servers. It SHOULD use metadata already
present in collection responses and avoid unrelated document downloads.
Neither filtering nor inlining is a prerequisite for HTTP federation.

An endpoint that advertises `pagination: false` normally supplies its
complete collection in one response. If a next link is nevertheless
returned, the resolver MUST NOT claim completeness until it has handled
that link or reported the conflicting behavior. A collection `count` alone
is not a replacement for the members or next links.

## HTTP Validators and Partial Content

ETags are opaque, representation-scoped validators, not XIDs, Core epochs,
global content digests or Registry-wide revision pins. Metadata and document
URLs, query variants and content codings can have different validators.
The resolver MUST use the selected representation's validator with that
representation, respecting `Vary`, cache directives and authorization scope.

Conditional `GET` with `If-None-Match` uses HTTP's weak comparison and can
revalidate a cached response. `304 Not Modified` has no replacement body.
The resolver MUST use an applicable stored response and update it according
to RFC 9111 section 4.3.4. Without one, it needs an unconditional read or an
explicit failure. `If-Modified-Since` and `Last-Modified` have HTTP's
semantics and precedence, not Core timestamp semantics.

`If-Match` uses strong comparison. A weak ETag MUST NOT be used where a
strong validator is needed. A resolver assembling partial bytes MUST apply
RFC 9110 sections 13.1.5 and 14, validate `Content-Range` and representation
identity, and account for every byte. A weak ETag is not valid for
`If-Range`. An HTTP-date is usable there only under HTTP's strong-validator
conditions. If an `If-Range` request returns a complete `200` response,
the resolver MUST replace, not append to, its partial bytes.

A `206` response is not a complete document merely because the transfer
ended successfully. Missing ranges, truncation, changed validators or
unverified joins MUST NOT produce a complete snapshot. A failed conditional
read used to hold a capture stable, including `412`, yields
`inconsistent_snapshot`.

A gateway that transforms a representation MUST NOT blindly forward the
upstream strong ETag as the validator for different bytes. It has to preserve
HTTP validator semantics for its own representation or omit that validator.
Federation imposes no unchanged-upstream-ETag requirement.

## Redirects and Authorization Boundaries

Redirect processing follows RFC 9110 section 15.4 and Core HTTP. In
particular, a Core external document can yield `303 See Other` with an
empty body and `Location` matching `<RESOURCE>url`. The destination is
domain content, not another Registry root. Other redirects can relocate
an endpoint or representation. The resolver MUST distinguish these cases.

Every redirect, advertised endpoint, next link and external document URL
MUST pass caller policy, including scheme, destination, network access and
redirect limits. The resolver MUST reject embedded credentials and MUST NOT
automatically forward Authorization, cookies, client credentials or
origin-specific conditional headers across a trust boundary. Destination
credentials require independent authorization. HTTPS downgrade and access
to restricted network locations require explicit policy, not an implicit
fallback.

`401` and `403` MUST NOT cause silent retries against another advertisement,
a public mirror, or a weaker authentication mode. Redirect loops and
bounded traversal exhaustion produce `limit_exceeded`. Trust rejection
produces `policy_denied`.

Redirect caching follows HTTP cache rules. A temporary redirect is not
categorically uncacheable: applicable cache controls determine reuse.
Cached redirects do not waive target-policy checks. Shared caching of
authenticated responses remains subject to RFC 9111 section 3.5.

## Live Capture and Errors

Reading a live endpoint is not an atomic Registry snapshot. A root epoch or
ETag need not cover changes to descendants, and equal modification times
do not prove an unchanged subtree. Even successful per-representation
revalidation is not, by itself, a transaction spanning multiple URLs.

A capture MUST record its selected root, actual Core version, selected
Version IDs, retrieval scope, available validators and absence of an
immutable pin separately from Core IDs. It MUST distinguish a live,
best-effort observation from a producer-guaranteed snapshot. A resolver
requiring a stronger guarantee MUST fail explicitly when the endpoint cannot
provide it. If the necessary capture operation is unsupported, the outcome
is `unsupported_operation`. If an attempted capture is inconsistent or
incomplete, the outcome is `inconsistent_snapshot`.

For a multi-request capture, the resolver SHOULD recheck the default
selection and the representations on which the capture depends. A changed
default, changed representation, conflicting membership or interrupted
page/byte sequence invalidates a claim of consistent capture. It MUST
report `inconsistent_snapshot` and discard that claim. It MAY start a new,
separately identified operation. A fresh capture is not a silent continuation
using mixed old and new state.

Common errors are resolver outcomes, not additional Core HTTP errors:

| Observed condition | Resolver outcome |
| --- | --- |
| No executable HTTP advertisement | `unsupported_binding` |
| Incompatible returned `specversion` or Core `unsupported_specversion` | `unsupported_version` |
| Unsupported selected parameter, unavailable API, or document of a metadata-only type | `unsupported_operation` |
| Missing requested entity or complete selector with no match | `not_found` |
| More than one matching entity | `ambiguous` |
| Authentication, authorization or destination policy prevents the read | `policy_denied` |
| A promised digest or representation-integrity check fails | `integrity_error` |
| Malformed metadata, wrong XID/model type or invalid advertisement | `invalid_package` |
| Conflicting or incomplete multi-read capture | `inconsistent_snapshot` |
| Page, byte or redirect budget exhausted | `limit_exceeded` |
| Transport failure, rate limit or transient server failure outside a completed capture | `unavailable` |

The resolver MUST retain the HTTP status and any Core error detail.
`api_not_found` is not an absent entity. A generic `404` without enough
context MUST NOT be used to invent an empty collection. Failure of a
previously identified member during capture is also evidence of incomplete
capture, not proof of a consistent deletion history.

## Conformance and Offline Examples

A conforming resolver implements the applicable native mappings, literal
selectors, all necessary pages, no-filter fallback, Core views and version
checks. It applies HTTP validator and security rules and never claims an
immutable snapshot solely from live reads. A server remains subject to Core
HTTP conformance. This document does not require query support from a
no-code server.

[Offline examples](../federation/samples/http/README.md) contain exact
request mappings and synthetic transcripts for a full API, a no-code catalog,
a non-root base path, later-page ambiguity, literal labels, validators,
document redirects, unsupported versions and inconsistent captures. They
do not contact the public hub or establish runtime interoperability.

The observed hub's read-only capabilities and a followed Registry advertising
an older Core release motivate the compatibility examples. These observations
are not normative endpoint behavior, and a saved model-file hash is not an
observed HTTP ETag.

## References

- [xRegistry Core](../../core/spec.md).
- [xRegistry HTTP](../../core/http.md).
- [xRegistry Pagination](../../pagination/spec.md).
- [xRegistry Federation](../federation/spec.md).
- [RFC 9110, HTTP Semantics][http], particularly sections 8.8, 13.1, 14 and 15.4.
- [RFC 9111, HTTP Caching][cache], particularly sections 3, 3.5, 4 and 4.3.4.

[rfc2119]: https://www.rfc-editor.org/rfc/rfc2119
[http]: https://www.rfc-editor.org/rfc/rfc9110
[cache]: https://www.rfc-editor.org/rfc/rfc9111
