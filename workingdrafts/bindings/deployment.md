# xRegistry Downstream Deployment Bindings

<!-- words: base64 bytestring contenttype https maxchunkbytes maxcontrolbytes -->
<!-- words: maxdocumentbytes maxpreconditionageseconds maxstagebytes maxstages -->
<!-- words: mqtt nextoffset nodeid opcua qos signandencrypt stagelifetimeseconds -->
<!-- words: statuscode uint xid -->
<!-- words: baseobjecttype browsename comparisonunavailable coreerror -->
<!-- words: createresource encodinglimitsexceeded federationdeploymenttype -->
<!-- words: getlimits inspectstage inspecttarget invalidargument invalidstate -->
<!-- words: mrpc namespace notfound notsupported py readablefields -->
<!-- words: resourceunavailable securechannel stageid statemarker targetxid -->
<!-- words: unprocessable useraccessdenied writablefields ywi -->

## Abstract

This specification maps [xRegistry Federation downstream deployment][deploy]
to HTTPS, OPC UA, and MQTT. Each profile stages the bytes of one exact Version
and commits them with a destination precondition. None of the profiles changes
the corresponding read binding or grants access based on a catalog entry.

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" are
to be interpreted as described in [RFC2119][rfc2119].

## Operation Data

Each configured entry point identifies one live destination Registry. It
MUST support all operations defined under [Deployment Operations][operations]
for its profile. A sender selects the entry point outside the deployment
messages. No request parameter can change the selected Registry.

JSON control data MUST be [RFC8259][json] JSON encoded as UTF-8. A decoder
MUST reject duplicate object member names, unrecognized members of defined
records, and incorrect types. It MUST NOT interpret caller-supplied metadata
as transport fields. The destination model defines the members of the
`metadata` object. Names and enumerated values are case-sensitive.

The following types apply after a binding decodes its wire data:

| Type | Definition |
| --- | --- |
| Target | An exact Core Version XID in the configured destination Registry. The receiver MUST validate and resolve it using Core and the effective model. |
| Byte count | An unsigned 64-bit integer. In JSON, encode it as a decimal string with no leading zero except `"0"`, no sign, and no exponent. |
| Stage ID and token | Nonempty, opaque, case-sensitive strings of ASCII letters, digits, `-`, and `_`. A stage ID has at most 128 characters and a token at most 512. The sender MUST NOT parse or rewrite either one. |
| State marker | An opaque, case-sensitive string with the same syntax as a token, with the comparison behavior specified by [Conditional Commit][commit]. |
| Time | An [RFC3339][time] timestamp with `Z` for UTC. |
| Descriptor | `null` for a metadata-only Version, or an object containing exactly `size` (a byte count), `digest` (`sha256:` followed by 64 lowercase hexadecimal digits), and `contenttype` (an [HTTP media type][media] string or `null`). |
| Mode | `create` or `replace`. |

Fields in the following table are REQUIRED unless marked OPTIONAL. An
absent `fields` input has the same meaning as an empty array. When supplied,
`fields` MUST be an array of distinct nonempty Version field names.

| Operation | Argument object |
| --- | --- |
| `limits` | Empty. |
| `inspectTarget` | `target`, OPTIONAL `fields`. |
| `begin` | `target`, `mode`, and `descriptor`. |
| `inspectStage` | `target` and OPTIONAL `stage`. |
| `append` | `stage`, `offset`, and `data` (nonempty bytes). |
| `commit` | `stage`, `token`, and `metadata` (a JSON object, empty if no fields are supplied). |
| `abort` | `target` and `stage`. |

The following records are successful results:

- `limits`: `profile` (the entry point's profile identifier),
  `maxDocumentBytes`, `maxChunkBytes`, `maxControlBytes`, and
  `maxStageBytes` (byte counts), and `maxStages`, `stageLifetimeSeconds`,
  and `maxPreconditionAgeSeconds` (positive JSON integers at most
  4294967295). `maxStages` and `maxStageBytes` bound the active stage count
  and aggregate staged bytes for the grant. `maxChunkBytes` MUST be
  positive and at most `maxDocumentBytes` when the latter is positive.
  `maxControlBytes` MUST be positive. These limits apply to authorization
  for the selected entry point. Lower transport limits still apply.
- `inspectTarget`: `target`, `state` (`resource_absent`, `version_absent`,
  or `version_present`), `mode` (or `null` if neither mode is allowed),
  and `readableFields` and `writableFields` (distinct names from the
  requested fields that the current grant and model permit the sender
  to read and to write, respectively). If `mode` is not `null`, the result
  MUST also include `token`, `expires` (a time), and `stateMarker`.
  Otherwise it MUST NOT include them. For `version_present`, `fields`
  MUST contain the readable subset of the requested fields. Each member
  of `fields` is `{"present": false}` if that field is absent, or contains
  `present: true` and `value` if present. An omitted field is not readable.
  Its omission does not show that the field is absent. The
  `version_present` result MUST include `descriptor` unless the
  receiver cannot compare the current document fingerprint; in that case
  it MUST omit `descriptor` and include `comparisonUnavailable: true`.
  `fields`, `descriptor`, and `comparisonUnavailable` MUST NOT appear
  for an absent Version.
- `begin` and `inspectStage`: `stage`, `target`, `mode`, `descriptor`,
  `nextOffset` (a byte count), `maxChunkBytes` (a byte count), and
  `expires` (a time).
- `append`: `nextOffset`, the byte count accepted so far.
- `commit`: `outcome` (`created` or `replaced`), `target`, `epoch` (the
  destination Version epoch encoded as an unsigned decimal string), and
  `descriptor` describing the committed Version.
- `abort`: `removed` (Boolean). `true` means this operation removed a
  matching live stage. `false` means it found no matching live stage.
  Both values confirm that the stage cannot commit after this response.

### Error Data

An operation error includes `code`, one of the
[Federation deployment error codes][errors], and MAY include `message`
and `coreError`, both strings. `coreError` is the underlying Core error
name, when safe to disclose. An `offset_mismatch` error MUST also include
`nextOffset`. The error MUST NOT include that member for an unauthorized
caller.

The following table maps operation errors to binding statuses. MQTT
returns the shared code directly. A request exceeding a transport limit
can also fail before an operation result can be encoded. If the sender
dispatched `commit` and did not receive a usable result, it follows
[Recovery and Synchronization][recovery].

| Code | HTTPS status | OPC UA operation status |
| --- | --- | --- |
| `invalid_request` | `400 Bad Request` | `Bad_InvalidArgument` |
| `policy_denied` | `401 Unauthorized` for missing or invalid authentication; otherwise `403 Forbidden` | `Bad_UserAccessDenied` |
| `not_found` | `404 Not Found` | `Bad_NotFound` |
| `stage_unavailable` | `404 Not Found` | `Bad_InvalidState` |
| `stale_precondition`, `conflict`, `offset_mismatch` | `409 Conflict` | `Bad_InvalidState` |
| `unsupported_operation` | `422 Unprocessable Content` | `Bad_NotSupported` |
| `integrity_error`, `validation_error` | `422 Unprocessable Content` | `Bad_InvalidArgument` |
| `limit_exceeded` | `413 Content Too Large` for size; `429 Too Many Requests` for quota | `Bad_EncodingLimitsExceeded` for size; `Bad_ResourceUnavailable` for quota |

## HTTPS Profile

The `https-deploy/1` profile uses a configured HTTPS base URL outside
Core entity CRUD. The base URL has no user information, query, or
fragment. The sender MUST authenticate the service, use credentials
scoped to the configured destination, and reject redirects. The receiver
MUST authenticate each request. The sender MUST NOT configure automatic
transport or intermediary retries for `commit`.

The receiver MUST implement the following paths under the complete
configured base path. `{stage}` is one path segment, and `{offset}` is a
byte count. The sender MUST NOT interpret either field as another path.

| Operation | Method and path | Request body |
| --- | --- | --- |
| `limits` | `GET /limits` | None. |
| `inspectTarget` | `POST /inspect-target` | Argument object. |
| `begin` | `POST /stages` | Argument object. |
| `inspectStage` | `POST /inspect-stage` | Argument object. |
| `append` | `POST /stages/{stage}/chunks?offset={offset}` | Raw bytes. |
| `commit` | `POST /stages/{stage}/commit` | Argument object without `stage`. |
| `abort` | `POST /stages/{stage}/abort` | Argument object without `stage`. |

Control request bodies and operation replies use `application/json`.
An `append` request MUST use `application/octet-stream` and MUST NOT
apply a non-identity content coding. The receiver MUST enforce body
bounds as it reads. A declared length alone does not establish that the
sender supplied that many bytes.

A successful reply has status `200`, or `201` when `commit` creates
the destination Version. Its body is the corresponding success object.
An operation error reply uses the status in [Error Data](#error-data)
and a JSON object with one `error` member containing the error data.
Operation responses MUST include `Cache-Control: no-store`. A Core `PUT`
or a successful response outside this contract is not a deployment result.

For example, the following exchange appends the first two bytes of a
3-byte staged document. The request body is `ab`, without a newline.

```text
POST /deployment/v1/plant/stages/upload-2/chunks?offset=0 HTTP/1.1
Host: receiver.example.test
Content-Type: application/octet-stream
Content-Length: 2

ab

HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: no-store

{"nextOffset":"2"}
```

The example omits authentication. A repeat with offset `0` returns
`409 Conflict` with `{"error":{"code":"offset_mismatch","nextOffset":"2"}}`
and does not append another `ab`.

## OPC UA Profile

The `opcua-deploy/1` profile uses the configured Registry Object from the
[OPC UA binding](opcua.md). The Object exposes the OPTIONAL `Deployment`
component. Its qualified BrowseName is `Deployment` in
`urn:xregistry:federation:deployment:v1`. The component
has type `FederationDeploymentType`, a subtype of `BaseObjectType` in that
namespace. A receiver implementing the profile MUST expose the component
and its Methods. Clients MUST resolve the configured root and the qualified
component BrowseName; a server endpoint alone does not select a Registry.

Every call MUST use a `SignAndEncrypt` SecureChannel. The sender MUST
verify the server application identity. The receiver MUST authenticate
the Session's user identity, map it to the grant, and authorize each
operation. Stage ownership is bound to the principal and Registry, not
the Session ID. Reconnecting with another principal does not transfer it.

The following table defines the input arguments in order. Methods use the
deployment namespace and are components of the `Deployment` Object.

| Operation | Method and input arguments |
| --- | --- |
| `limits` | `GetLimits()` |
| `inspectTarget` | `InspectTarget(TargetXid: String, Fields: String[])` |
| `begin` | `Begin(TargetXid: String, Mode: String, Descriptor: String)` |
| `inspectStage` | `InspectStage(TargetXid: String, StageId: String)` |
| `append` | `Append(StageId: String, Offset: UInt64, Chunk: ByteString)` |
| `commit` | `Commit(StageId: String, Token: String, Metadata: String)` |
| `abort` | `Abort(TargetXid: String, StageId: String)` |

An empty `Fields` array requests no fields. An empty `StageId` in
`InspectStage` means the OPTIONAL `stage` argument is absent.
`Descriptor` and `Metadata` carry the respective JSON values in strings;
`Descriptor` carries the four-character JSON literal `null` for a
metadata-only Version. `Offset` and `Chunk` carry the native value
and bytes. The receiver MUST enforce the control and chunk limits and
applicable UA string, byte string, and message limits.

The output arguments in order are `StatusCode: StatusCode` and
`Result: String`. If a well-typed Call reaches the deployment operation,
the receiver MUST return a Good Call status and both output arguments.
The operation `StatusCode` is `Good` on success or the applicable error
status from [Error Data](#error-data). `Result` contains the same JSON
success or error object as in HTTPS. The sender MUST verify both
statuses and the result shape. A service-level rejection, timeout, or
lost Session does not supply an operation result.

For the same append, `Append("upload-2", 0, ByteString(0x61 0x62))`
returns operation status `Good` with `{"nextOffset":"2"}`. Repeating
the offset produces operation status `Bad_InvalidState` with the
`offset_mismatch` error. `CreateResource` with a file handle and ordinary
FileType `Close` do not satisfy conditional deployment commit.

## MQTT Profile

The `xreg-deploy/1` profile uses [MQTT 5.0][mqtt] and a configured
TLS broker. It does not extend the [`mrpc/1.0` binding](mqtt.md).
The sender and receiver MUST verify the broker's identity and use
separate broker credentials.

The administrator MUST configure nonempty, distinct, concrete request
and reply Topic Names for each grant generation. Only the sender
principal can publish to the request topic and subscribe to the reply
topic. Only the receiver can subscribe to the request topic and publish
to the reply topic. The broker MUST enforce those restrictions, including
against wildcard subscriptions or routing that would bypass them. The
receiver maps the exact delivered request topic to the grant. A payload,
client ID, or MQTT property supplied by the sender MUST NOT assert a
principal or grant. Revocation MUST disable the receiver's mapping.
Old topic pairs MUST NOT be assigned to a new grant generation.

Each request and reply MUST fit in one PUBLISH packet. Both use QoS 1,
`RETAIN` set to `0`, `Content Type` set to `application/json`, `Payload
Format Indicator` set to `1`, and a positive `Message Expiry Interval`.
Both subscriptions MUST set Retain Handling to `2` and Retain As Published
to `1`. The broker configuration MUST prevent storage of retained
deployment messages. A receiver MUST NOT act on a retained message.

A request MUST include the configured reply topic as `Response Topic` and
fresh, unpredictable `Correlation Data` of 16 bytes. The receiver MUST
reject a request with another Response Topic and MUST NOT publish to it.
Replies MUST omit `Response Topic`, carry the same `Correlation Data`,
and have a positive expiry no greater than the request's remaining expiry.
The receiver sends a reply only through the configured reply topic while
authorized. The sender MUST check the topic, profile, correlation, and
properties before interpreting the result. Delivery acknowledgments and
correlation are not operation results or authorization.

The UTF-8 JSON request contains exactly `profile` with value
`"xreg-deploy/1"`, `operation`, and `arguments`. The reply contains the
same `profile` and exactly one of `result` or `error`. `result` is the
success record and `error` is the error data. An `append` carries `data`
as [RFC4648][base64] standard Base64. The encoding MUST include applicable
padding and MUST NOT contain whitespace. The decoder MUST reject noncanonical
encodings. Applicable control, chunk, and maximum packet sizes MUST account
for JSON, PUBLISH overhead, and Base64 expansion. A document can span
`append` requests, but an individual control message cannot span packets.

This request and its reply carry the same append as the HTTPS and UA
examples. The payloads omit PUBLISH properties for brevity.

```json
{
  "profile": "xreg-deploy/1",
  "operation": "append",
  "arguments": {"stage": "upload-2", "offset": "0", "data": "YWI="}
}
```

```json
{
  "profile": "xreg-deploy/1",
  "result": {"nextOffset": "2"}
}
```

A repeated MQTT delivery can return `offset_mismatch` without changing
the stage. For commit, a duplicate can return `stage_unavailable` even
when the first execution committed. That reply does not supersede a
usable success for the same exchange. If no usable success is available,
the sender follows [Recovery and Synchronization][recovery]. Message
expiry and MQTT delivery order do not enforce commit atomicity.

## Conformance and Examples

A sender or receiver that declares conformance to a deployment profile MUST
implement all operations and security rules for that profile. Supporting the
[HTTP read profile](http-federation.md), [OPC UA API](opcua.md), or
[MQTT binding](mqtt.md) does not imply deployment conformance.
The [MQTT request schema](../federation/schemas/deployment-request.json)
validates JSON shape. The binding and model govern size, byte decoding,
XID, authorization, and commit behavior.

The [offline examples](../federation/tools/test_deployment_examples.py)
exercise the shared operations and representative wire mappings. These
examples do not act as a transport server or prove that a live broker
or Registry enforces the stated requirements.

[deploy]: ../federation/spec.md#downstream-deployment
[operations]: ../federation/spec.md#deployment-operations
[commit]: ../federation/spec.md#conditional-commit
[errors]: ../federation/spec.md#deployment-errors
[recovery]: ../federation/spec.md#recovery-and-synchronization
[rfc2119]: https://www.rfc-editor.org/rfc/rfc2119
[json]: https://www.rfc-editor.org/rfc/rfc8259
[time]: https://www.rfc-editor.org/rfc/rfc3339
[media]: https://www.rfc-editor.org/rfc/rfc9110#name-media-type
[mqtt]: https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html
[base64]: https://www.rfc-editor.org/rfc/rfc4648
