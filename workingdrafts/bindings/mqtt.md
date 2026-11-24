# xRegistry MQTT 5.0 RPC Binding

<!-- words: djik mqtt mqtts mrpc requesttopic uuids xids memberorigins selectedxid -->
<!-- words: applicationerror correlationdata messageexpiryinterval payloadformatindicator qos responsetopic userproperties -->

## Abstract

This binding defines the MQTT 5.0 PUBLISH properties and JSON payloads for
[xRegistry Federation](../federation/spec.md) reads of a Registry's model,
capabilities, collections, entity metadata, and documents.

**Status:** Unreleased working draft using xRegistry Core Version 1.0-rc4.

## Scope and Terminology

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" are to be
interpreted as described in [RFC 2119][rfc2119].

The client sends the request; the serving Registry sends the reply. Each
message fits in one MQTT 5.0 PUBLISH packet. This binding does not define
writes, continuation requests, or multi-packet transfer. Session
management, retries, duplicate handling, deadline calculation, and
agreements between the parties are outside its scope.

## Advertisement

An advertisement MUST set `binding` to `mqtt`. The `endpoint` MUST use
the absolute URI form `mqtts://host[:port]`, with no user information,
path, query, or fragment. An explicit port MUST fall between 1 and 65535
inclusive. If omitted, the client uses port 8883. The endpoint identifies
the broker, not an xRegistry entity or a document retrieval URL.

The `parameters` object MUST contain a `requesttopic` string. Its value
MUST be a concrete MQTT Topic Name: nonempty, representable as an MQTT
UTF-8 Encoded String, and containing neither `+` nor `#`. The client uses
the string as supplied, without percent-decoding or treating it as a Topic
Filter or XID. The broker and request topic select one exposed Registry
view. A selected advertisement with any other parameter MUST
produce `unsupported_operation` before access. Discovery, priority and
selection failures follow the [Registry catalog rules][selection].

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

Both publications MUST use QoS 1 and MUST set `RETAIN` to `0`. A
receiver MUST NOT use a delivery whose QoS is not 1 or whose `RETAIN`
flag is set to `1`.

| Property | Request | Reply |
| --- | --- | --- |
| Response Topic | REQUIRED. An authorized concrete Topic Name different from the request topic. | MUST be absent. Publish the reply to the request's Response Topic. |
| Correlation Data | REQUIRED. A fresh UUID version 4 ([RFC 9562][uuid]) encoded as 16 octets in network byte order, not as UUID text. | REQUIRED. The same 16 octets, unchanged. |
| Message Expiry Interval | REQUIRED. The requested lifetime in whole seconds, from 1 through 4294967295. | REQUIRED. The remaining reply lifetime in whole seconds, in the same range. |
| Content Type | REQUIRED: `application/json`. | REQUIRED for `200`: `application/json`. MUST be absent for every other status. |
| Payload Format Indicator | REQUIRED: `1` for UTF-8 character data. | REQUIRED for `200`: `1`. MUST be absent for every other status. |
| User Property `mrpc-version` | Exactly one, with value `mrpc/1.0`. | Exactly one, with value `mrpc/1.0`. |
| User Property `mrpc-status` | MUST be absent. | Exactly one, with one of the values below. |

Replies use three decimal digits for `mrpc-status`:
`200`, `204`, `400`, `408`, `415`, `500`, `503`, or `505`. Only `200`
carries a nonempty payload. The others have an empty payload and are not
xRegistry outcomes; even `204` does not complete an xRegistry read with a
result. This binding does not assign envelope failure conditions to
individual non-`200` statuses.

A reply with an error status MAY carry `mrpc-status-message`,
`mrpc-property-name`, and `mrpc-property-value`, at most once each. A
`500` reply MAY also carry at most one `mrpc-application-error`, with
value `true` for a handler failure to produce a normal result and `false`
otherwise. Diagnostics do not replace `mrpc-status`. Requests and
successful replies MUST NOT carry those diagnostic properties.

The `mrpc-` prefix is reserved for envelope properties. Implementations
MUST disregard unrecognized properties under that prefix after checking
MQTT encoding and size limits. Such properties do not supply xRegistry
fields. A publication with `mrpc-chunk` is outside this binding and
MUST NOT be interpreted as a single-packet read or result. The client
MUST NOT interpret a reply as an xRegistry result unless the actual Topic
Name matches the request's Response Topic, the Correlation Data matches,
and the reply properties conform to this section. The serving Registry
MUST NOT process a request with an invalid envelope as a
Federation read. This binding does not require an envelope error reply in
cases where the serving Registry cannot send one.

## Read Requests

The request payload MUST be a UTF-8 JSON object with `operation` and
`target`, both strings. The only other member is `selector`, which MAY
appear with `collection` only. If present, `selector` MUST contain exactly
two string members, `label` and `value`. `label` is the literal label key
and `value` the literal comparison value under [Federation Selectors][selectors].
The MQTT envelope does not supply an operation name or a target.

| `operation` | `target` | Value on success |
| --- | --- | --- |
| `model` | `/` | An object containing `model`, the interpreted Core model, and `modelsource` if the serving Registry makes it available. |
| `capabilities` | `/` | The enabled Core capabilities object for the exposed view, not offered capabilities. |
| `collection` | A typed Group, Resource, or Version collection path. | The complete Core collection object, keyed by member ID. With a selector, the object contains the one matching member. |
| `entity` | A Registry, Group, Resource, Meta, or Version XID. | Core metadata for that entity. |
| `document` | A Resource or Version XID. | An object containing `base64`, the domain document's bytes, and `contenttype` if it is available for the selected document. |

The serving Registry MUST resolve targets against the exposed view and its
model. An operation outside the table MUST produce `unsupported_operation`.
An invalid request shape or target syntax MUST produce `invalid_package`.
Core determines default Version selection, exact Version lookup and
alias handling. A request for an explicit Version MUST NOT select the
default or any other Version. A read of a metadata-only Resource's
document MUST produce `unsupported_operation`.

The serving Registry MUST apply [Federation read semantics][reads],
including selector outcomes and the resolution-owner boundary. A
collection without a selector MAY be empty if it is a complete result.
Neither an incomplete read nor an inaccessible source is an empty
collection. A selector with no match produces `not_found`; multiple
distinct visible matches produce `ambiguous`. If a read cannot produce its
complete result within the binding's configured limits, it MUST fail, not
return a partial success or a continuation token. If the serving Registry
can return a conforming reply for a limit failure, it returns
`limit_exceeded`.

## Read Replies

A `200` reply MUST contain one UTF-8 JSON object with exactly one member,
`result` or `error`, whose value is an object. `error` MUST contain `code`,
a string naming a [Federation error][errors] or a Core error applicable to
the operation. It MAY contain `message`, a diagnostic string that does
not disclose credentials. A `200` envelope with an `error` reports a
failed xRegistry read. A non-`200` reply, invalid envelope or absent
reply does not establish a Federation outcome such as `not_found`.

The `result` object MUST contain `value` with the shape in the request
operation table and `origin`. For `collection`, it MUST also contain
`memberorigins`, an object keyed by the same member IDs as `value`, with
one origin per returned member. The collection's own `origin` describes
the exposed collection view; it does not replace the origin of each
member. `memberorigins` MUST be absent for other operations.

An origin object contains `source`, `selectedxid`, and `revision`.
`source` is a nonempty string identifying the selected Registry access
context within the serving Registry's origin reporting. It is not a
global identifier or a trust assertion. `selectedxid` is the selected
entity XID or typed collection path in that context. For a document result
it identifies the exact Version that supplied the bytes.
`revision` is the immutable revision identifier as a string, or `null`
when the source has no such pin. When selection used a catalog, origin
also includes a `catalog` object with the catalog access context `source`,
its description Version `selectedxid`, and the selected `advertisement`
object. A client that selected the serving Registry through its own
catalog retains that selection separately. Origin data is not part of a
Core entity's metadata. MQTT correlation and expiry do not establish an
immutable snapshot.

Metadata in `value` MUST use [Core document view][doc], as specialized by
[Federation representations][representations]. The metadata `value` is
the document root for any document-local JSON Pointer; the reply envelope
and origin objects are outside that document. This binding does not
introduce an MQTT URL form for individual Core entities. If the serving
Registry cannot supply a navigation URL that Core requires, it MUST fail
with `unsupported_operation` rather than invent a URL or return a pointer
to an omitted target.

Encode document bytes as standard [RFC 4648][base64] Base64, with padding
where applicable and no line breaks. `""` denotes zero bytes, not a
missing document. A document reply MUST NOT substitute an external
locator for the bytes. If the bytes cannot be retrieved under the
serving Registry's policy, the read fails.

## Example

The following JSON is notation for two MQTT publications, not an
additional wire format. `correlationdata` is shown as hexadecimal octets,
`userproperties` is an ordered list of pairs, and only the objects under
`payload` are UTF-8 JSON payloads. The example uses the Registry advertised
above and does not assume an immutable revision.

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

Clients MUST verify the broker's identity and apply caller policy before
contacting it or using either topic. Before sending a reply, the serving
Registry MUST establish that policy permits the requested reply route;
Correlation Data and User Properties do not establish that permission.
Broker authentication, topic authorization, and connection credentials are
configured outside catalog metadata.

Implementations MUST enforce applicable MQTT packet limits and local
bounds on request and reply processing. A packet that cannot be sent or
received within those limits is not an xRegistry response. A resolver
MUST NOT try another advertisement in the same read after the selected
binding fails. Conformance to this draft covers the defined properties,
payloads and read behavior; it does not imply support for writes, chunking
or another RPC protocol.

## References

- [xRegistry Federation][reads]
- [xRegistry Core document view][doc]
- [MQTT Version 5.0][mqtt5]
- [RFC 2119: Requirement Levels][rfc2119]
- [RFC 4648: Base-N Encodings][base64]
- [RFC 9562: UUIDs][uuid]

[reads]: ../federation/spec.md#read-operations
[selectors]: ../federation/spec.md#selectors
[errors]: ../federation/spec.md#errors
[representations]: ../federation/spec.md#representations
[selection]: ../models/registry/spec.md#62-advertisement-selection
[doc]: ../../core/spec.md#doc-flag
[mqtt5]: https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html
[rfc2119]: https://www.rfc-editor.org/rfc/rfc2119
[base64]: https://www.rfc-editor.org/rfc/rfc4648#section-4
[uuid]: https://www.rfc-editor.org/rfc/rfc9562#section-5.4
