# xRegistry MQTT 5.0 RPC Binding

<!-- words: djik mqtt mqtts mrpc requesttopic uuids xids memberorigins selectedxid -->
<!-- words: applicationerror correlationdata messageexpiryinterval payloadformatindicator puback qos responsetopic userproperties -->
<!-- words: capabilitiesoffered contentlocation setdefaultversionid -->

## Abstract

This binding defines remote procedure calls (RPC) for the xRegistry API
using MQTT 5.0 PUBLISH properties and JSON payloads. It supports direct
access to a Registry without a Federation catalog or an HTTP endpoint,
and provides short read requests for
[xRegistry Federation](../federation/spec.md).

**Status:** Unreleased working draft using xRegistry Core Version 1.0-rc4.

## Scope and Terminology

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" are to be
interpreted as described in [RFC 2119][rfc2119].

The client sends the request; the serving Registry sends the reply. Each
message uses one MQTT 5.0 PUBLISH packet and is subject to the
[packet and processing limits](#security-and-conformance). Only the
Annex A `read` operation on a collection can request
[pages](#a4-native-collection-pagination) as separate operations. The
[short read forms](#short-read-requests), including those used by
Federation, do not support continuation.

[MQTT 5.0][mqtt5] QoS 1 allows duplicate delivery; it does not guarantee
that the Registry executes an operation only once. This binding does not
define multi-packet transfer, session management, retries, duplicate
handling, deadline calculation, or deployment agreements between the
parties, such as credential provisioning.

## Advertisement

An MQTT binding advertisement in the [Registry catalog][advertisements]
MUST set `binding` to `mqtt`. The `endpoint` MUST use the absolute URI
form `mqtts://host[:port]`, with no user information, path, query, or
fragment. An explicit port MUST fall between 1 and 65535 inclusive. If
omitted, the client uses port 8883. The endpoint identifies the broker,
not an xRegistry entity or a document retrieval URL. `mqtts` requires
MQTT over TLS; see [Security and Conformance](#security-and-conformance).

The `parameters` object MUST contain a `requesttopic` string. Its value
MUST be a concrete MQTT Topic Name: nonempty, representable as an MQTT
UTF-8 Encoded String, and containing neither `+` nor `#`. The client uses
the string as supplied, without percent-decoding or treating it as a Topic
Filter or XID. The broker and request topic select one exposed Registry
view: the entities and collections made available at that broker and
topic, interpreted under that view's model. The native request's
[`view` member](#a1-native-requests-and-targets) instead selects
metadata or a domain document within that Registry.

The resolver MUST validate common advertisement fields and apply caller
policy as part of [catalog selection][selection]. After selecting an
advertisement and before contacting the broker, the resolver MUST check
the parameter names. A key other than `requesttopic` produces
`unsupported_operation`. If there are no unknown parameter names, a
missing or invalid `requesttopic` produces `invalid_package` under the
[Registry catalog error rules][catalog-errors]. These are selection
failures, not PUBLISH replies.

A client can also obtain the broker URI and request topic through local
configuration. Both the [short reads](#short-read-requests) and the
[native API](#annex-a-correspondence-to-the-xregistry-http-binding-normative)
work without catalog discovery.

```json
{
  "binding": "mqtt",
  "endpoint": "mqtts://broker.example.com",
  "parameters": {
    "requesttopic": "registries/supplier/reads"
  }
}
```

## MQTT PUBLISH Properties

The table uses PUBLISH properties from [MQTT 5.0][mqtt5]. Fields with the
`mrpc-` prefix are MQTT User Properties, not MQTT Reason Codes. Their names
and literal values are case-sensitive.

Both senders MUST publish with QoS 1 and set `RETAIN` to `0`. A receiver
MUST silently discard a delivery whose QoS is not 1 or whose `RETAIN`
flag is set to `1`. The serving Registry MUST NOT execute or reply to
such a request, even with an envelope error. The client MUST NOT use
such a reply as an xRegistry outcome. This check uses the values in the
delivered packet. The binding does not require subscriptions to
preserve the publisher's `RETAIN` flag. The delivered flag does not
establish what the publisher set. For the exchange to work, the serving
Registry needs a matching subscription that permits QoS 1 delivery on
the request topic, and the client needs one on the Response Topic.

| Property | Request | Reply |
| --- | --- | --- |
| Response Topic | REQUIRED. A concrete Topic Name different from the request topic, authorized as described in [Security and Conformance](#security-and-conformance). | MUST be absent. Publish the reply to the request's Response Topic. |
| Correlation Data | REQUIRED. For each newly initiated logical request, the client MUST generate a fresh UUID version 4 ([RFC 9562][uuid]) and encode it as 16 octets in network byte order, not as UUID text. | REQUIRED. The same 16 octets, unchanged. |
| Message Expiry Interval | REQUIRED. The requested lifetime in whole seconds, from 1 through 4294967295. | REQUIRED. The reply lifetime in whole seconds, in the same range. |
| Content Type | REQUIRED: `application/json`. | REQUIRED for `200`: `application/json`. MUST be absent for every other status. |
| Payload Format Indicator | REQUIRED: `1` for UTF-8 character data. | REQUIRED for `200`: `1`. MUST be absent for every other status. |
| User Property `mrpc-version` | REQUIRED, exactly once, with value `mrpc/1.0`. | REQUIRED, exactly once, with value `mrpc/1.0`. |
| User Property `mrpc-status` | MUST be absent. | Exactly one, with one of the values below. |

Replies use three decimal digits for `mrpc-status`:
`200`, `204`, `400`, `408`, `415`, `500`, `503`, or `505`. Only `200`
carries a nonempty payload. The others have an empty payload and are not
xRegistry outcomes. In particular, `204` does not report a successful
xRegistry operation. This binding does not specify when to send it;
clients cannot rely on receiving it.
This binding does not assign envelope failure conditions to individual
non-`200` statuses. Such a status alone does not identify a specific
failure cause.

The serving Registry MUST validate the request's Correlation Data length,
UUID version and variant. It does not have to verify freshness or detect
replay. Correlation Data is not a request deduplication key.

The sender MUST include a positive Message Expiry Interval in both
request and reply publications. The receiver MUST validate the property
as delivered by MQTT, not reconstruct the lifetime as published. An
absent interval or a delivered interval of zero makes the envelope
invalid. A Registry handles such a request under the invalid-envelope
rule below; a client MUST NOT interpret such a reply as an xRegistry
outcome.

Under [MQTT 5.0][mqtt5] §3.3.2.3.3, the broker decrements Message Expiry
Interval when forwarding a PUBLISH and discards a pending delivery if
the interval expires before onward delivery begins. The property
governs message delivery; it does not tell the client whether an
xRegistry operation ran.

This binding does not specify how to calculate the reply interval or
how it relates to the request interval.

The envelope error statuses are `400`, `408`, `415`, `500`, `503`, and
`505`. Only replies with these statuses MAY carry `mrpc-status-message`,
`mrpc-property-name`, and `mrpc-property-value`, at most once each.
`mrpc-status-message` supplies diagnostic text. The other two properties
can identify a field or show a value for diagnostic purposes. They are
independently OPTIONAL and do not define a standard field path. The
serving Registry MUST redact sensitive values from envelope diagnostics.

A `500` reply MAY also carry at most one `mrpc-application-error`.
If present, its value MUST be the string `true` when application
processing fails to supply a conforming xRegistry `result` or `error`,
including when it supplies an invalid outcome. The value MUST be the
string `false` for other causes, including
serialization or reply construction failure at the binding layer after
application processing supplies a valid outcome. That property MUST be
absent from all other replies. Requests, `204` replies, and `200`
replies (including those carrying an xRegistry
`error`) MUST NOT carry envelope diagnostic properties. Diagnostics do
not replace `mrpc-status`.

After checking MQTT encoding and size limits, implementations MUST
ignore MQTT User Properties outside the `mrpc-` prefix, whether supplied
by the publisher or the broker. These properties do not affect envelope
conformance or supply xRegistry fields. The `mrpc-` prefix is reserved
for envelope properties. Implementations MUST disregard unrecognized
properties under that prefix after the same checks. A publication with
`mrpc-chunk` is outside this binding. The receiver MUST discard it
without processing or replying; it is not eligible for the
invalid-envelope reply described below. A client MUST NOT derive an
xRegistry outcome from such a publication.

The client MUST NOT interpret a reply as an xRegistry outcome unless
the actual Topic Name matches the request's Response Topic, the
Correlation Data matches, and the reply properties conform to this
section.

The serving Registry MUST NOT execute a request with an invalid envelope.
It MAY send a conforming empty reply with an envelope error status
only if all of the following hold:

- The original request's Response Topic is a valid, concrete MQTT Topic
  Name different from the topic on which the request was published.
- The reply route passes the same
  [authorization check](#security-and-conformance) as an operation
  request.
- The serving Registry can supply all mandatory reply fields.

Otherwise, the serving Registry MUST discard the request without replying.

An empty error reply can echo the original 16 Correlation Data octets
unchanged even if the request fails UUID version or variant validation.
If Correlation Data is absent or not 16 octets long, the Registry cannot
supply a conforming echo and MUST discard the request without replying.

After admitting a valid envelope to request validation, the serving
Registry MAY send a conforming empty reply with an envelope error
status only if it cannot construct or submit a conforming `200` reply
with a `result` or `error`. The same Response Topic, authorization,
Correlation Data echo, and mandatory-field conditions apply. The
empty reply MUST fit the applicable packet and reply bounds. Requests
that require silent discard are not eligible.

Use the applicable `200` reply if it can be sent, including for a
validation, limit, or application error. Submission occurs when the
Registry's MQTT publishing side accepts the conforming `200` PUBLISH
for sending, not when the broker acknowledges it. Refusal before that
acceptance can qualify for the fallback under the conditions above.
After acceptance, the Registry MUST NOT send an empty envelope error
as a fallback. It does not wait for `PUBACK` to close the fallback;
a later negative `PUBACK` or delivery failure does not reopen it.

## Request Validation

In request and reply payloads, the receiver MUST reject duplicate member
names in JSON objects defined by this binding before collapsing object
members. This applies to the top-level objects and to nested objects
such as `selector`, `flags`, `page`, the document wrappers, `result`,
`error`, and origin objects. It does not redefine Core processing of
entity metadata or Core mutation objects, and does not apply to opaque
domain document bytes. For a request, apply the malformed-request
rules below. For a reply, follow the
[invalid-reply rule](#reply-payload).

The MQTT envelope does not supply an operation name or target. The
serving Registry MUST validate the envelope before processing the
xRegistry payload. For a valid envelope and an authorized reply route,
apply these checks in order. Report the named xRegistry errors in a
conforming `200` [error reply](#reply-payload) if one can be sent.

1. The payload MUST be one UTF-8 JSON object with exactly one
   `operation` member, whose value is a nonempty string. If either
   check fails, return Core `bad_request`.
2. The object MUST have a string `target` and no duplicate member
   names. If either check fails, return `invalid_package` only if
   the unique `operation` value is a known short read name; otherwise
   return Core `bad_request`.
3. If the operation name is not defined by either request form, return
   `unsupported_operation`. For a known operation, apply the
   family-specific checks in [Short Read Requests](#short-read-requests)
   or [Section A.1](#a1-native-requests-and-targets).
   A duplicate in a nested object defined by the request form is a
   malformed request under that form's rules.

Both forms address the exposed Registry by Registry-relative
[entity XID][xid] or [typed collection path][collections]. For example,
`/documents` identifies a Group collection, `/documents/main/assets` a
Resource collection, and `/documents/main/assets/item/versions` a
Version collection. Resolve names against the selected model and use
Core's [case-sensitive ID lookup][ids]. The `target` string is not a
broker or retrieval URI; it does not contain an HTTP method, `$details`,
query, or fragment.

<a id="read-requests"></a>

## Short Read Requests

This section defines only the short read forms, including those used by
Federation. The `operation` name identifies the form: the table below
lists the short read names, and
[Annex A](#annex-a-correspondence-to-the-xregistry-http-binding-normative)
lists the distinct native operation names.

The request payload MUST be a UTF-8 JSON object with `operation` and
`target`, both strings. The only other member is `selector`, which MAY
appear with `collection` only. If present, `selector` MUST be an object
with exactly `label` and `value`, both strings. `label` is the literal
label key and `value` is the literal comparison value under
[Federation Selectors][selectors].

| `operation` | `target` | `result.value` on success |
| --- | --- | --- |
| `model` | `/` | An object containing `model`, the interpreted Core model, and `modelsource` if the serving Registry makes it available. |
| `capabilities` | `/` | The enabled Core capabilities object for the exposed view, not offered capabilities. |
| `collection` | A typed Group, Resource, or Version collection path, such as `/documents/main/assets` for a Resource collection. | The complete Core collection object, keyed by member ID. With a selector, the object contains the unique visible matching member. |
| `entity` | A Registry, Group, Resource, Meta, or Version XID. | Core metadata for that entity. |
| `document` | A Resource or Version XID. | For a document-bearing type, an object with only `base64` for the [document bytes](#document-bytes) and, if available, a `contenttype` string. For a metadata-only type, the same Core metadata as an `entity` read at that target. |

For a known short read, the serving Registry MUST return `invalid_package`
for malformed request members, malformed target syntax, or a target of
a kind not allowed for that operation. Check target syntax and kind
before looking up the entity. For example, a Group XID is not a valid
target for `document`. A missing target of the correct kind produces
`not_found`.

Core determines default Version selection, exact Version lookup and
alias handling. A request for an explicit Version MUST NOT select the
default or any other Version. If the target's Resource type has
[`hasdocument: false`][hasdocument], the serving Registry MUST return the
same Core metadata for `document` as for `entity` at that target. The
Resource type determines the result shape, not the presence of a `base64`
member. A missing or unreadable document on a document-bearing type does
not cause a metadata result.

Before accepting a successful short `document` result, the client MUST
establish that its model applies to the exposed Registry view and the
reply, using one of these means:

- A deployment guarantee that covers the selected view and the reply.
  The guarantee can cover an authoritative configured model or a model
  response.
- An independently verified shared [immutable snapshot pin][snapshots]
  that scopes the model and reply to the same exposed Registry view,
  source Registry, and binding.

Otherwise, the client MUST NOT accept the result. A model read from
the same broker and topic, even immediately before the document read,
is not sufficient on its own. Reply member names, Correlation Data,
Message Expiry Interval, a Core Version ID, or a revision value outside
the verified context do not establish which model applies.

When these short forms are used for Federation, the serving Registry
MUST apply [Federation read semantics][reads], including the
[resolution-owner boundary][resolution]: a consumer reads a
producer-resolved view without repeating its resolution; with
consumer-side resolution, the consumer applies its composition policy
outside the single-source read. This is the role of the Registry in
Federation, not a separate MQTT request type. Direct short reads work
against the addressed Registry and do not initiate catalog traversal.

Without a selector, a complete read MAY return an empty collection.
Neither an incomplete read nor an inaccessible source is an empty
collection. A selector with no match produces `not_found`; multiple
distinct visible matches produce `ambiguous`. If a read cannot produce its
complete result within the binding's configured limits, it MUST fail, not
return a partial success or a continuation token. See the `limit_exceeded`
rule in [Security and Conformance](#security-and-conformance).

<a id="read-replies"></a>

## Reply Payload

These payload rules apply to both short and native operations. To
treat a `200` reply as an xRegistry outcome, the client MUST validate
its payload against these rules. For a `result`, the client MUST also
apply all applicable binding-defined result shape rules in
[Short Read Requests](#short-read-requests) and
[Short Read Results](#short-read-results) for short reads, or throughout
[Annex A](#annex-a-correspondence-to-the-xregistry-http-binding-normative)
for native operations.

The client MUST check member presence, absence, and constraints when
it can determine which rules apply from the request, the reply, and
other facts available to it. For example, a `200` result
without `page` for an explicitly paginated native collection read, or
without `order` for a paginated or explicitly sorted native collection
read, does not establish an xRegistry outcome. The client does not
have to establish unobservable facts unless a specific rule requires
evidence, as for the applicable model on a short `document` result.
Apply the rules on duplicate members separately from the allowed
member names.

The client MUST reject unlisted members in binding-defined reply
objects. These include `result`, origin and `catalog` objects, the
short `model` and document-bytes wrappers, native `options` and document
wrappers, `page`, and its link objects. Use the members specified for the
operation and object; `error` also permits the extensions described
below. This rule does not restrict Core-defined objects or metadata
extensions, member IDs used as map keys, catalog
advertisement fields governed by the Registry catalog, or opaque
document bytes. An object in a map still follows its own shape rules.

A `200` reply MUST contain one UTF-8 JSON object with exactly one member,
`result` or `error`, whose value is an object. `error` MUST contain `code`,
the string name of an applicable [Federation error][errors] or
[Core error][core-errors], not an HTTP status code. For example, this
binding uses the Federation error name `unsupported_operation` for an
unsupported operation. Core uses `mismatched_epoch` for a failed epoch
check. The `error` object MAY contain `message`, a diagnostic string
that does not disclose credentials. It MAY also include the Core error
fields `type`, `title`, `detail`, `subject`, `args`, `instance`, and
`source`, and extension fields permitted by
[Core error processing][core-errors].

A conforming `200` reply with an `error` reports a failed xRegistry
operation. A non-`200` reply, invalid envelope, invalid `200` payload,
or absent reply does not establish an xRegistry outcome, such as a
Federation `not_found`. For a mutation, without a valid xRegistry
outcome the client cannot determine from the exchange whether the
change took effect.

## Short Read Results

For a short read, `result` MUST contain `value` with the shape in the
request operation table and a provenance `origin` object as described
below. For `collection`, it MUST also contain `memberorigins`, an
object with one origin per returned
member, keyed by the same member IDs as `value`. The collection's own
`origin` describes the exposed collection view; it does not replace
the origin of each member. `memberorigins` MUST be absent for other operations.

An origin object contains `source`, `selectedxid`, and `revision`.
`source` is a nonempty opaque label for the selected Registry access
context, scoped to the serving Registry's origin reporting. It is not
a retrieval URI, a transferable or persistent identifier, or a trust
assertion. `selectedxid` is the selected entity XID or typed collection
path in that context. If the result carries document bytes, it
identifies the exact Version that supplied them.
`revision` is a string identifying the
[pinned immutable snapshot][snapshots] of the source Registry, or `null`
when the source has no such pin. Compare revision identifiers only after
independently establishing the same source Registry and binding. A
revision identifier is not a Core Version ID, a catalog-description
Version ID, or a global equality test.

Each origin object, including each member origin, MUST contain `catalog`
if the serving Registry used a catalog to select that origin's source.
Otherwise `catalog` MUST be absent.
In that object, `source` MUST be a nonempty opaque string identifying
the catalog access context. It has the same serving-Registry reporting
scope and constraints as the outer `source`: it is not a retrieval URI,
a transferable or persistent identifier, or a trust assertion.
`selectedxid` is the XID of the catalog entry's description Version, and
`advertisement` is the selected
[Registry catalog advertisement][advertisements]. A client that selected
the serving Registry through its own catalog retains that selection
separately. Origin data is not part of a Core entity's metadata. MQTT
correlation and expiry do not establish an immutable snapshot.

For short and native results, the client MUST validate the origin
fields it can check and reject a reply if known facts about the serving
Registry's catalog selection contradict the presence, absence, or
contents of `catalog`. The client does not have to prove catalog use
it cannot observe. Opaque `source` labels do not establish identity
or trust.

For both direct and Federation short reads, metadata in `value` MUST
use [Core document view][doc] as specialized by
[Federation representations][representations]. `value` is the document
root for any document-local JSON Pointer; in a
collection it is the entire member map, not an individual member. For
example, `#/item` locates the member keyed by `item` in that map. The
reply envelope and origin objects are outside that document. If the
serving Registry cannot supply a navigation URL that Core requires, it
MUST fail with `unsupported_operation` rather than invent a URL or return
a pointer to an omitted target. See [Navigation URIs](#navigation-uris).

A short `document` reply MUST NOT substitute an external locator for the
bytes. An absent target produces `not_found`. For an existing Version
of a document-bearing type, the serving Registry MUST report
`policy_denied` if policy denies retrieval. If policy permits retrieval
but the bytes are unobtainable, it MUST report `unavailable` unless a
more specific Core or Federation integrity or consistency error applies.
Failure to retrieve bytes does not establish that the Version is missing.
For a metadata-only target, the reply carries the metadata object
directly in `value`, not a Base64 encoding of that object or an empty
document.

## Document Bytes

In short read replies and native requests and replies, encode document
bytes in `base64` as standard [RFC 4648][base64] Base64, with padding
where applicable and no line breaks. `""` denotes zero bytes, not a
missing document.

If the media type is available to the serving Registry, it MUST include
`contenttype` in a short document-bytes result. A client MUST NOT reject
such a result solely because `contenttype` is absent. In native
`document` objects, `contenttype` is OPTIONAL.

When present in either form, `contenttype` MUST be a JSON string with
the media-type semantics of [Core `contenttype`][media-type]. `null` and
numbers are not valid. A malformed native request produces
`bad_request`; a reply with a malformed `contenttype` does not establish
an xRegistry outcome.

<a id="example"></a>

## Short Read Examples

The following JSON is notation for two MQTT publications, not an
additional wire format. `correlationdata` is shown as hexadecimal octets,
`userproperties` is an ordered list of pairs, and only the objects under
`payload` are UTF-8 JSON payloads. The example uses the Registry advertised
above. Assume the client has an authoritative configured model and the
deployment guarantees that it applies to the selected view and this
reply. The example does not assume an immutable revision.

```json
{
  "request": {
    "topic": "registries/supplier/reads",
    "qos": 1,
    "retain": 0,
    "responsetopic": "example/replies/client-7",
    "correlationdata": "d6a64e76047a4395bc88184f8061bd59",
    "messageexpiryinterval": 10,
    "contenttype": "application/json",
    "payloadformatindicator": 1,
    "userproperties": [["mrpc-version", "mrpc/1.0"]],
    "payload": {
      "operation": "document",
      "target": "/documents/main/assets/item/versions/v2"
    }
  },
  "reply": {
    "topic": "example/replies/client-7",
    "qos": 1,
    "retain": 0,
    "correlationdata": "d6a64e76047a4395bc88184f8061bd59",
    "messageexpiryinterval": 8,
    "contenttype": "application/json",
    "payloadformatindicator": 1,
    "userproperties": [["mrpc-version", "mrpc/1.0"], ["mrpc-status", "200"]],
    "payload": {
      "result": {
        "value": {"base64": "djIK", "contenttype": "text/plain"},
        "origin": {
          "source": "supplier",
          "selectedxid": "/documents/main/assets/item/versions/v2",
          "revision": null
        }
      }
    }
  }
}
```

The request and reply use example expiry intervals of 10 and 8 seconds.
These values do not imply that the reply interval is derived from the
request interval.

The document bytes are `v2` followed by a line feed. If the same request
instead addresses a missing explicit Version, the reply uses the same
property rules, including `mrpc-status=200`, with this payload:

```json
{"error": {"code": "not_found"}}
```

If an existing collection does not fit in one reply, the serving Registry
does not return a truncated collection. If it can send a conforming
reply, the payload is:

```json
{"error": {"code": "limit_exceeded"}}
```

## Security and Conformance

Before contacting the broker, the client MUST check that caller policy
permits the broker endpoint. The client MUST use TLS and verify the
broker's identity before using the connection for MQTT. The client MUST
check that caller policy permits the request and response topics before
using them.

The serving Registry MUST check that its policy authorizes the
requested reply route before executing any xRegistry operation. If
the route is not authorized, the Registry MUST discard the request without
executing the operation, changing Registry state, or sending a reply.
The same authorization check applies before any reply to an invalid
envelope. Correlation Data and User Properties do not establish
permission. Broker authentication, topic authorization, and connection
credentials are configured outside catalog metadata.

Implementations MUST enforce applicable MQTT packet limits and local
bounds on request and reply processing. If the serving Registry
declines a valid envelope before xRegistry request validation under
reply-route policy or a local admission bound, it MUST discard the
request without validating the xRegistry payload, executing the
operation, or replying. A packet not admitted to xRegistry request
validation produces no confirmed xRegistry outcome. If the packet is
admitted but the request fails validation, the serving Registry
reports the applicable error in a conforming `200` reply if it can
send one.

If a known processing or output bound prevents an operation from
completing or its success result from fitting in a conforming reply, the
serving Registry MUST fail the operation and report `limit_exceeded`
if it can send a conforming `200` error reply.

Before committing a mutation or making its changes visible, the
serving Registry MUST establish that the final conforming success
reply, including the serialized payload and MQTT packet envelope,
fits within the applicable request-processing and reply bounds. If
limits prevent the Registry from establishing that fit, it MUST reject
the mutation without changing Registry state and report
`limit_exceeded` if it can send a conforming `200` error reply.
[Core Error Processing][core-errors] still requires undoing the
request if response construction fails. This binding does not
prescribe a storage or transaction mechanism.

Establishing fit does not guarantee delivery after commit. Delivery
loss and a failure to construct a conforming reply discovered after
commit are distinct: the latter violates the pre-commit requirement.
The Registry MUST NOT report a mutation whose changes remain committed
as a confirmed xRegistry failure. Without a valid reply, the client
cannot determine whether the mutation took effect.

After any unsuccessful read, the resolver MUST NOT try another
advertisement for the same catalog entry in that read. This includes a
confirmed `not_found` as well as an MQTT failure or no confirmed
xRegistry outcome. Under
[Federation Discovery and Binding Selection][binding-selection], a
genuine Resource miss can advance to the next source entry, not to
another advertisement for the same entry. The caller MAY initiate a
separate read with an explicitly different advertisement.

Conformance to this draft covers the defined properties, payloads, and
Core operation behavior. A conforming serving Registry MUST implement:

- Native `read` at `/` without `surface`, at `/` with `surface: "model"`,
  and at `/` with `surface: "capabilities"`.
- All five short read forms: `model`, `capabilities`, `collection`,
  `entity`, and `document`.

These mappings do not require Federation. Implementing them does not
grant access or guarantee success for every view, model, target, or
packet size. Other native operations and features retain Core's
optionality and applicable requirements. `options` is OPTIONAL.
This binding does not grant write access to a read-only Registry or
imply support for chunking or another RPC protocol.

## Annex A: Correspondence to the xRegistry HTTP Binding (normative)

This annex defines the native Registry API over MQTT. The client addresses
the Registry selected by the broker and request topic, whether or not that
Registry uses Federation. For every operation it implements, including
the [minimum native reads](#security-and-conformance), the serving
Registry MUST apply the [Core processing rules][core] and preserve the
xRegistry semantics of the corresponding [HTTP API][http-api] operation.
This includes creation, replacement, partial update, bulk processing,
deletion, version selection, conditional changes, and atomicity. No
HTTP endpoint, proxy, or tunnel is needed. Beyond the minimum mappings,
Core's optionality and applicable obligations remain in effect. The server
MUST report an unsupported operation or feature rather than substitute
a different one. Native operations use
the common [reply payload](#reply-payload).

### A.1. Native Requests and Targets

A native request follows the common
[request validation rules](#request-validation). Its only members
besides `operation` and `target` are `surface`, `view`, `flags`, `body`,
and `page`, as defined below. The native operation names are
`read`, `replace`, `update`, `process`, `delete`, and `options`. They are
distinct from the forms in [Short Read Requests](#short-read-requests).

- `target` is `/`, an entity XID, or a typed collection path, as defined
  under [Request Validation](#request-validation).
- `surface` selects a Registry service instead of an entity at `/`: use
  `capabilities`, `capabilitiesoffered`, `model`, `modelsource`, `export`,
  or `discovery`. It MUST be absent for other targets.
- `view` is `metadata` (the default) or `document`. An explicit
  `view: "metadata"` MUST be accepted wherever omission of `view` is
  legal. The serving Registry MUST treat both forms as the same
  default before checking allowed qualifier combinations. Use
  `document` only for operations mapped to the domain-document path of a
  Resource or Version, including `options` on that address. The only
  exception for a metadata-only Resource or Version is `read`: either
  view returns the same metadata. Use the metadata address for `options` or a
  mutation on a metadata-only type; a metadata-only write takes a
  metadata body. `delete` addresses the entity and does not take
  `view: "document"` on any type. The `doc` flag, not `view`, requests
  Core document-view serialization of metadata.
- `flags` is an object containing the [Core request flags][flags] in
  Section A.3. A flag does not change the legal target or operation.
- `body` carries the operation input in Section A.2. If the operation
  does not take input, `body` MUST be absent.
- `page` applies only to native collection reads. See
  [Section A.4](#a4-native-collection-pagination) for its shape and
  applicability errors. The `selector` member is not part of a native
  request.

The table gives the allowed operation and target combinations. HTTP
paths are relative to the HTTP Registry root. `G` is
`/<GROUPS>/<GID>`, `R` is `G/<RESOURCES>/<RID>`, and `V` is
`R/versions/<VID>`. A surface or view shown in the table is a JSON member
of the native request, not part of `target`.

For a known native operation, the serving Registry MUST validate in
this order:

1. Check binding-defined member types and shapes. A malformed member
   produces `bad_request`. The `read` and `options` operations never
   take input. Any `body` member on either operation, even `{}` or
   `null`, fails this check before the Registry checks target syntax.
   For example, a malformed document wrapper or `page` object produces
   `bad_request` even if a well-formed flag does not apply to the
   operation. Check for unknown flag names here, as described in
   [Section A.3](#a3-request-flags).
2. Check target syntax and kind, qualifier combinations, and
   applicability under Core. Malformed entity XIDs and typed target
   paths produce `malformed_xid`. An invalid combination of operation,
   target, `surface`, or `view` produces `bad_request` unless a specific
   Core error applies. Check target-dependent `body` absence rules here
   once the target kind is known. For example, `body` MUST be absent on
   a single-entity `delete`. Use `bad_flag` where Core defines it for
   an inapplicable flag. See Section A.4 for `page` applicability.
3. Check support for the requested operation and features. An
   otherwise valid request for a mapping or feature that is not
   implemented produces `unsupported_operation`. A Registry that omits
   a minimum mapping is not conforming. If supported, process the
   operation under Core rules.

If independent checks fail in the same validation stage, the serving
Registry MAY report any applicable error from that stage. A
later-stage error MUST NOT override an earlier-stage error.

| HTTP API | MQTT `operation` | MQTT `target` and qualifiers |
| --- | --- | --- |
| `GET /` | `read` | `/` |
| `PUT /`, `PATCH /`, `POST /` | `replace`, `update`, `process`, respectively | `/` |
| `GET /export` or its Core export flags on `GET /` | `read` | `/` with `surface: "export"`, or a root read with the export flags and no `surface` |
| `GET /capabilities`, `PUT /capabilities`, `PATCH /capabilities` | `read`, `replace`, `update`, respectively | `/`, `surface: "capabilities"` |
| `GET /capabilitiesoffered` | `read` | `/`, `surface: "capabilitiesoffered"` |
| `GET /model` | `read` | `/`, `surface: "model"` |
| `GET /modelsource`, `PUT /modelsource` | `read`, `replace`, respectively | `/`, `surface: "modelsource"` |
| `GET`, `PATCH`, `POST`, `DELETE` on `/<GROUPS>`, `G/<RESOURCES>`, or `R/versions` | `read`, `update`, `process`, `delete`, respectively | The typed collection path |
| `GET G`, `PUT G`, `PATCH G`, `POST G`, `DELETE G` | `read`, `replace`, `update`, `process`, `delete`, respectively | `G`; `process` addresses its child Resource collections |
| `GET`, `PUT`, `PATCH` on `R$details` or `V$details` (also bare `PUT` or `PATCH` for a metadata-only type) | `read`, `replace`, `update`, respectively | `R` or `V`, `view: "metadata"` |
| `GET` or `PUT` on bare `R` or `V` for a document-bearing type | `read` or `replace`, respectively | `R` or `V`, `view: "document"` |
| `GET` on bare `R` or `V` for a metadata-only type | `read` | `R` or `V`, either view; returns metadata |
| `POST R$details` (or bare `POST R` for a metadata-only type) | `process` | `R`, `view: "metadata"`; creates or updates one Version |
| Bare `POST R` for a document-bearing type | `process` | `R`, `view: "document"`; creates or updates one Version |
| `DELETE R` or `DELETE V` | `delete` | `R` or `V`, metadata address; deletes the entity, not just its bytes |
| `GET`, `PUT`, or `PATCH` on `R/meta` | `read`, `replace`, `update`, respectively | `R/meta`; deletion is not supported |
| `OPTIONS` on a supported API target | `options` | A qualified address with another implemented native operation. Use its `target` and applicable `surface` and `view`; for a metadata-only type, use the metadata address. |
| `GET /.xregistry` | `read` | `/`, `surface: "discovery"` |

For a metadata-only Resource, the `process` request at `R` takes the
Version metadata body described in Section A.2.

By default, `surface: "export"` has the semantics of a Registry read
with `flags: {"doc": true, "inline": ["*", "capabilities", "modelsource"]}`.
A native read at `/` using those flags can request the same result
without `surface`. As for [HTTP export][http-export], a supported
explicit `inline` overrides the corresponding default. `doc` is implicit
and cannot be disabled: `doc: false` is malformed. Apply the validation
rules in [Section A.3](#a3-request-flags) to explicitly supplied flags,
including `inline`. Other valid, supported flags apply normally.
`discovery` returns the Core Registry discovery document with its
`registries` array; it is not Federation catalog selection.

`options` is OPTIONAL and does not modify data. Determine support
from the native operation mappings implemented for the same `target`
and applicable `surface` and `view`, not from whether the target entity
exists. `options` applies only if at least one other native operation
is implemented at that address. Operations at other addresses,
including another view of the same target, do not count. After request
validation, a valid `options` request at an address with no other
implemented native operation produces `unsupported_operation`.

The serving Registry MUST NOT make a lookup for entity presence a
condition of `options` support. Normal validation and access policy
still apply, and each listed operation retains its own rules for
looking up or creating an entity.

On success, `result.value` is an object with an `operations` array
that MUST list each supported native operation name for the queried
address exactly once, including `options`. The array MUST NOT include
operations supported only at other addresses. HTTP method and
cross-origin policy headers are not returned.

### A.2. Inputs and Results

For metadata and service mutations, `body` MUST have the shape of the
corresponding Core input. For example, collection `process` and `update`
take a map keyed by member ID; `process` at `/` or `G` takes only the
named nested collections. The `process` operation at `R` takes the
input for one Version; the presence or absence of `versionid` has the
same effect as in the corresponding HTTP operation. Omitted mutable fields,
explicit `null`, and nested values have their existing replace or update
semantics. A collection `delete` accepts the same OPTIONAL map of member
IDs to objects with an OPTIONAL `epoch`; omission requests deletion of
the entire collection under Core's rules. A single-entity `delete` uses
`flags.epoch` for a precondition, not a body.

For `replace`, `update`, and `process`, put an epoch precondition in the
Core mutation body, including the applicable per-member body, or in
`body.metadata` for a domain-document write. `flags.epoch` is valid only
on a single-entity `delete`. Specifying it elsewhere produces `bad_flag`;
the server does not choose between it and a body epoch.

For a domain-document `replace` or `process`, `body` MUST be an object
with `document` and at most one other member, the OPTIONAL `metadata`
object. The `document` object MUST contain exactly one of `base64`
(exact bytes) or `url` (a Core external document reference). It MAY
also contain `contenttype`, but no other member. An unknown member in
either wrapper makes the request malformed (`bad_request`). Core
extension attributes in `metadata` are governed by Core, not by these
wrapper rules. Use the shared [byte and media-type rules](#document-bytes).
An empty Base64 string supplies a zero-byte document, not a URL or
missing input. The `metadata` object
carries the xRegistry attributes accompanying the document,
including any supplied IDs and epoch, in their Core JSON types. Document
content, content type, and external document URL belong in `document`,
not in `metadata`. A partial update of domain bytes is not supported.

For example, the following replaces the bytes of an exact Version, provided
its epoch is still `3`:

```json
{
  "operation": "replace",
  "target": "/documents/main/assets/item/versions/v2",
  "view": "document",
  "body": {
    "metadata": {"epoch": 3},
    "document": {"base64": "djIK", "contenttype": "text/plain"}
  }
}
```

For every native success, the `200` reply's `result` MUST contain `value`.
Reads of metadata use Core API view unless the `doc` flag requests
document view. If metadata is returned directly in `value`, then
`value` is the root for any document-local JSON Pointers.
The `model`, `modelsource`, `capabilities`, and
`capabilitiesoffered` surfaces return the corresponding objects, not a
combined result. For a domain-document success, `result.value` MUST be
an object with exactly two members: `document`, with the same shape
as document input, and `metadata`, the Core metadata object that
accompanies the document. An unknown member in `result.value` or
its `document` object makes the reply invalid; the client MUST NOT
interpret it as an xRegistry outcome. The wrapper rules do not
restrict Core extension attributes in `metadata`.
In these read or write results, `metadata` uses Core API view unless
`flags.doc` requests document view. The flag affects only `metadata`,
which is the root for any document-local JSON Pointers. The `metadata`
object MUST NOT also inline the document returned in `document`.
Other applicable Core serialization rules still apply.
For external content, the native reply carries the URL HTTP would use
as its redirect destination. This does not authorize retrieval. The
short `document` read still returns bytes only for document-bearing
targets.

For a successful native `read` of a Resource or Version with
`view: "document"`, the serving Registry MUST return the document
wrapper for a document-bearing type or direct Core metadata for a
metadata-only type. If the client has no model known to apply to the
reply, either otherwise conforming form is acceptable. If a model
known to apply rules out the returned form, the client MUST reject
the reply. Do not infer the model from the reply members. The
[short-read model proof rule](#short-read-requests) does not apply to
this native read; the other reply and Core validation rules still apply.

For example, the following shows the placement of the document and
metadata in a `200` reply payload for the native Version document
operation above. Other Core metadata attributes are omitted.

```json
{
  "result": {
    "value": {
      "document": {"base64": "djIK", "contenttype": "text/plain"},
      "metadata": {
        "versionid": "v2",
        "xid": "/documents/main/assets/item/versions/v2"
      }
    }
  }
}
```

Successful mutations return the corresponding result after processing;
collection `update` and `process` return only the processed members, not
the entire collection. A successful `delete` returns `value: null`.

- `location` MUST be present if the corresponding HTTP mutation
  would report entity creation with `Location`. Its value is the new
  entity's API-view `self` URI, even when `value` uses document view.
- `contentlocation` MUST be present if the corresponding HTTP
  mutation would report Version creation with `Content-Location`. Its
  value is the exact new Version's API-view `self` URI.

Otherwise, the corresponding member MUST be absent. A client MUST
reject a reply whose inclusion or omission of either member violates
these rules when the violation can be established from the operation
or known outcome. The client does not have to infer whether a mutation
created an entity or Version when that fact is not observable.

Before committing a mutation, the serving Registry MUST ensure it can
produce any creation and Version navigation URIs the result requires.
If it cannot, it MUST reject the mutation with `unsupported_operation`
rather than commit and then report failure to construct the result.
These members describe Core results; they do not set `mrpc-status` or
carry HTTP headers. Use `error` instead of `result` when the operation
fails. For example, if the Version's epoch does not match the one in
the native replace request above, the `200` reply can carry this payload:

```json
{"error": {"code": "mismatched_epoch"}}
```

`origin` and `memberorigins` are OPTIONAL in native results and use the
object shapes in [Short Read Results](#short-read-results). Each origin
that is included, whether for the result or a member, MUST contain
`catalog` if and only if the serving Registry used a catalog to select
that origin's source. The client's own catalog selection does not
affect this condition. The client follows the origin validation rules
in [Short Read Results](#short-read-results).

If supplied, `memberorigins` MUST contain exactly the keys in the
returned collection `value`. For an operation that returns a page or
only processed members, that means the returned subset, not the entire
collection.
`memberorigins` MUST be absent from non-collection results.

#### Navigation URIs

An MQTT-only Registry MUST use retrievable MQTT URIs for Core
API-view navigation. A Registry that supports another binding MAY use
that binding's URI scheme if lookup is defined and the URI is retrievable.
The client MUST apply caller policy before following a URI for either
binding. A Core [`self` URI][self] locates retrievable metadata.

If no supported binding can represent a Core-required navigation URI
in a retrievable form for a native read, the serving Registry MUST
fail the read with `unsupported_operation` rather than supply a
placeholder URI. This rule does not override applicable access-policy,
transient-failure, size-limit, or more specific errors.

The MQTT form of a native read URI is
`mqtts://host[:port]/<encoded-request-topic><target>`. The broker
authority follows the [advertisement rules](#advertisement). Encode
the request topic as one path segment, percent-encoding its UTF-8
octets except [URI unreserved characters][rfc3986]. The topics `.` and
`..` MUST instead use the literal segments `!.` and `!..`, respectively,
so URI processing does not remove them as dot segments. A literal `!`
in any other topic is encoded as `%21`.

In the encoded URI path, split at the first `/` after the initial `/`.
Interpret the exact segments `!.` and `!..` as `.` and `..` before
normal decoding. For any other segment, percent-decode that segment
once. Check that the decoded topic meets the
[Topic Name requirements for `requesttopic`](#advertisement), then
re-encode it using the rules above. The original segment MUST match
the re-encoded segment, except that either case of the hexadecimal
digits in percent escapes is accepted. Do not ignore case elsewhere.
The client MUST NOT follow a URI with an invalid encoded topic segment.

Use the remaining path verbatim as `target`, including the leading
`/`. Do not percent-decode or normalize that path at the URI layer.
The same Core target processing then applies as for a `target` supplied
directly in a request. `/` names the Registry.

An MQTT navigation URI MUST NOT contain a fragment. Its query takes
one of these forms for a valid native read address:

- No query for a Registry, entity, or collection metadata URI.
- Exactly `?view=document` for a Resource or Version document URI.
- Exactly `?surface=<name>` for a Registry service URI with `target: "/"`.

The client MUST NOT use a URI with any other query, including repeated
members or a combination of `view` and `surface`. The query is not part
of `target`.

For example, `mqtts://broker.example.com/registries%2Fsupplier%2Freads/`
locates the Registry. The URI
`mqtts://broker.example.com/registries%2Fsupplier%2Freads/documents/main/assets/item`
locates Resource metadata. Adding `?view=document` selects its domain
document for the native `read` operation. Broker and topic authorization
apply before following a URI. Core's document-view pointers retain their
usual meaning. An MQTT `self` URI is not an HTTP URL.

For the request topic `..`, the Registry root is
`mqtts://broker.example.com/!../`. For the literal topic `!..`, it is
`mqtts://broker.example.com/%21../`.

### A.3. Request Flags

Only the flag names defined in this section are valid in a native
request's `flags` object. An unknown name makes the request malformed
and produces `bad_request` during shape validation. `limit` in enabled
capabilities advertises pagination support; in a request use `page.limit`,
not `flags.limit`.

Each supported flag MUST follow Core's rules for what it means and where
it can be used. To request a presence-only flag (`binary`, `collections`,
or `doc`), set it to JSON `true`; otherwise omit it. The
value `false` is a malformed flag value and produces `bad_request`.
The [Core `binary` flag][binary] selects the `<RESOURCE>base64` attribute
instead of `<RESOURCE>` for an inlined domain document; it does not
cause an inline or change the JSON reply payload format. Use a Core
unsigned integer for `epoch` and a string for `specversion`. These
values are not HTTP query parameters. For `epoch` placement, see
[Section A.2](#a2-inputs-and-results).

| Flag | JSON form in `flags` |
| --- | --- |
| `filter` | Nonempty array of nonempty arrays of Core filter expressions as strings. Each inner array is an AND; the outer array is an OR. |
| `ignore` | Nonempty array of Core ignore values as strings; `["*"]` requests all supported values. |
| `inline` | Nonempty array of Core inline paths as strings; `"*"` is a path value. |
| `setdefaultversionid` | A Version ID string, `"request"`, or `null` as defined by Core. |
| `sort` | One string in Core's sort attribute and direction notation, such as `"labels.stage=desc"`. |

Array entries are individual values, not HTTP comma-separated query
strings. If a recognized flag is inapplicable, the server MUST report
the applicable Core error, such as `bad_flag` for `collections` on a
Resource. If it is valid and applicable but unsupported, the server
MUST report `unsupported_operation`. See
[Section A.1](#a1-native-requests-and-targets) for validation order.
The short read forms retain their literal selector semantics; the
`filter` flag does not require a unique match on a native collection read.

A native collection result MUST include `order` if it is paginated or
sorted, whether sorted by default or by the `sort` flag. An unsorted,
unpaginated native collection result MAY include `order`. It MUST be
absent from other results.

When present, `order` is an array of member IDs in returned order, with
exactly one entry for each key in `value`. The array preserves ordering
for clients that do not retain JSON object member order. It does not
guarantee the same order across reads. The
[Core Sort Flag][sort] defines default sorting; this rule does not
require default sorting of unpaginated results.

### A.4. Native Collection Pagination

A server supporting the [Pagination extension][pagination] over MQTT
advertises `limit` in its enabled `flags`. A `page` object MUST contain
exactly one member: `limit` for an initial native collection read, or
`cursor` for a continuation. For example, use `page: {"limit": 100}`.

The request's `page.limit` and the reply links' `count`, `offset`, and
`limit` MUST use unsigned decimal JSON number tokens: `0` or a token
matching `[1-9][0-9]*` in its entirety. Signs, fractions, exponents, and
JSON strings are not valid. The values MUST be represented exactly,
without rounding. The request's `page.limit` ranges from 1 through
18446744073709551615.

To obtain another page, the client sends the same read with
`page: {"cursor": "<token>"}` in place of the initial `page` object.
After request validation, the `target` string MUST match the original
read's `target` exactly. The applicable effective `surface` and `view`
and all applicable effective flags, including `filter` and `sort`,
MUST also match. Compare these flags even if they have no effect on
the particular data being read. For this comparison, omitted `flags` and
`flags: {}` are equivalent. Omitted `view` and `view: "metadata"` are
equivalent wherever omission is legal, as specified in
[Section A.1](#a1-native-requests-and-targets).

Compare the effective flag values structurally after validation and
application of existing defaults. Ignore object member order, JSON
whitespace outside strings, and differences in JSON escape spelling.
Array elements MUST match in order, and decoded strings MUST match
exactly. Do not rewrite filter expressions to test logical equivalence.
For example, reversing two distinct conjuncts in a `filter` group
makes the continuation out of scope even if they select the same
members.

The cursor is an opaque nonempty string provided by the server. It
is scoped to those read parameters, the initial `limit`, and the
authorized caller and Registry context. Serving Registry policy
determines the caller context. The continuation uses the original
limit without sending it again.

Check the `page` object during native shape validation. A malformed
object produces `bad_request`. For a well-formed `page` object, check
applicability before checking support. For this check, first rule out
collection mutations, including a collection `delete`: return
`bad_request` because `page` is for reads. For other operations with
a non-collection result, return Core `pagination_noncollection`.

An otherwise valid request for pagination when the Registry does not
support it produces `unsupported_operation`. When processing a
continuation, the server MUST reject an invalid, expired, or
out-of-scope cursor with `bad_request`. It MUST NOT silently start a
new sequence.

The serving Registry MUST NOT start pagination unless the client
requests it. A successful native collection read with `page.limit`
or `page.cursor` MUST return a `page` object in `result`, even for
an empty or one-page sequence. `result.page` MUST be absent from all
other results. A collection read without a `page` request returns the
complete collection or the limit failure defined in this binding.

For a paginated result, `value` contains the members on that page.
The number of members MUST NOT exceed the original `limit`, including
on continuations. `page` contains `links`, an array of objects with a
string `rel` and `cursor`. A `next` link MUST be present if another
page exists and MUST be absent on the last page. Use the
[Pagination link relations and attributes][page-links].
Link objects MAY also contain `count`, `offset`, `limit`, and
`expires`. When present, `count`, `offset`, and `limit` use the decimal
token syntax above and MUST be in the unsigned 64-bit range, subject to
the applicable Pagination constraints. `expires`, if present, is a
JSON string in the [Core timestamp][core-types] format. The server
does not send an HTTP `Link` header, and a cursor does not imply an
immutable snapshot. Single messages still obey MQTT packet limits,
including document and export requests.
HTTP byte ranges and HTTP conditional headers have no MQTT counterpart
here; Core epoch preconditions still apply.

## References

- [xRegistry Federation][reads]
- [xRegistry Core document view][doc]
- [MQTT Version 5.0][mqtt5]
- [RFC 2119: Requirement Levels][rfc2119]
- [RFC 4648: Base-N Encodings][base64]
- [RFC 9562: UUIDs][uuid]

[reads]: ../federation/spec.md#read-operations
[binding-selection]: ../federation/spec.md#discovery-and-binding-selection
[resolution]: ../federation/spec.md#signaling-who-performs-resolution
[snapshots]: ../federation/spec.md#snapshots-and-completeness
[core]: ../../core/spec.md
[http-api]: ../../core/http.md#registry-http-apis
[http-export]: ../../core/http.md#get-export
[core-errors]: ../../core/spec.md#error-processing
[core-types]: ../../core/spec.md#data-types
[self]: ../../core/spec.md#self-attribute
[xid]: ../../core/spec.md#xid-attribute
[ids]: ../../core/spec.md#singularid-id-attribute
[collections]: ../../core/spec.md#registry-collections
[flags]: ../../core/spec.md#request-flags
[binary]: ../../core/spec.md#binary-flag
[sort]: ../../core/spec.md#sort-flag
[pagination]: ../../pagination/spec.md
[page-links]: ../../pagination/spec.md#server-attributes
[selectors]: ../federation/spec.md#selectors
[errors]: ../federation/spec.md#errors
[representations]: ../federation/spec.md#representations
[advertisements]: ../models/registry/spec.md#51-common-fields
[selection]: ../models/registry/spec.md#62-advertisement-selection
[catalog-errors]: ../models/registry/spec.md#8-error-handling
[doc]: ../../core/spec.md#doc-flag
[hasdocument]: ../../core/model.md#groupsstringresourcesstringhasdocument
[media-type]: ../../core/spec.md#contenttype-attribute
[mqtt5]: https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html
[rfc2119]: https://www.rfc-editor.org/rfc/rfc2119
[rfc3986]: https://www.rfc-editor.org/rfc/rfc3986#section-2.3
[base64]: https://www.rfc-editor.org/rfc/rfc4648#section-4
[uuid]: https://www.rfc-editor.org/rfc/rfc9562#section-5.4
