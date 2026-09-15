# Media Endpoints - Version 0.1 (Working Draft)

<!-- words: aac adts aomediacodec audiocodec avc avp bcp dashif demuxer -->
<!-- words: dtls etsi flv haivision hevc hls iec itu llhls metaint mpd -->
<!-- words: mpeg mpegts mtu muxer muxes opusts packetization packetized -->
<!-- words: passphrases pcma pcmu playlist playlists quic remuxing -->
<!-- words: repacketization rfcs rtcp rtmp rtmps rtp rtsp sdk sdp -->
<!-- words: sessiondescription shtml signalingreference srt srtcp srtp -->
<!-- words: ssrcs streamformat streamid streamname tcurl transcoder -->
<!-- words: transcodes transcoding tterribe udp unicast userinfo veovera -->
<!-- words: videocodec vsf webrtc websocket webtransport whep wiki xiph -->

## Abstract

This document defines a media-stream extension to the xRegistry
Endpoint Registry. It identifies where a producer can supply media and where a
consumer can receive it. It describes the connection entry point and, when
needed, constrains the stream format and codecs a producer supplies.

Media negotiation, stream descriptions, and adaptive selection remain with the
media protocol.

This document is an xRegistry working draft, dated 15 September 2026. It is
under active development and can change independently of released xRegistry
specifications. It is included for discussion and review and is not part of a
released xRegistry specification.

## Base and Scope

The base is [Endpoint Registry Service 1.0-rc3][endpoint], its
[endpoint model][endpoint-model], and [xRegistry Core][core] with its
[model rules][core-model], at xregistry/spec commit
`adf5b6a63e60c3baa78e844da8b7ce2a0d60c179` (18 August 2026).
References to the base mean that snapshot. This draft's version is independent
of Core `specversion`.

The extension supports discovery of predominantly one-way media flows. Protocol
framing, feedback, and session control are defined by the selected protocol;
they do not need xRegistry Message definitions. Bidirectional control does not
make media delivery an API. A management API can be described separately using
its native API definition format.

The registry supplies information a producer needs to configure its encoder and
connect to a receiving service. Consumers obtain media details through
offer/answer, session descriptions, stream headers, playlists, or manifests.
Where a protocol does not negotiate codecs, a consumer uses its native
descriptions or inspects the stream.

## Table of Contents

- [Abstract](#abstract)
- [Base and Scope](#base-and-scope)
- [Table of Contents](#table-of-contents)
- [Notations and Terminology](#notations-and-terminology)
- [Endpoint Model](#endpoint-model)
  - [Base-Model Integration](#base-model-integration)
- [Input Requirements](#input-requirements)
- [Connection Discovery](#connection-discovery)
- [Protocol Definitions](#protocol-definitions)
  - [SRT](#srt)
  - [WebRTC](#webrtc)
  - [RTSP](#rtsp)
  - [RTP and SRTP](#rtp-and-srtp)
  - [MPEG-TS over UDP](#mpeg-ts-over-udp)
  - [RTMP and RTMPS](#rtmp-and-rtmps)
  - [HLS](#hls)
  - [MPEG-DASH](#mpeg-dash)
  - [RIST](#rist)
  - [Other Protocols](#other-protocols)
- [Distribution Example](#distribution-example)
  - [RTMP Producer](#rtmp-producer)
  - [SRT Consumer](#srt-consumer)
  - [HLS Consumer](#hls-consumer)
  - [HTTP Payload Consumer](#http-payload-consumer)
- [Validation and Conformance](#validation-and-conformance)
- [Security Considerations](#security-considerations)
- [Open Issues](#open-issues)
- [References](#references)
  - [Normative References](#normative-references)
  - [Conditional Draft Reference](#conditional-draft-reference)
  - [Informative References](#informative-references)

## Notations and Terminology

The capitalized requirement words have the meanings in BCP 14
([RFC 2119][rfc2119] and [RFC 8174][rfc8174]). JSON types and xRegistry Group,
Resource, XID, and attribute terminology follow Core.

An Endpoint is a Group at `/endpoints/{endpointid}`, not a Resource within an
additional group. A provider exposes the endpoint; a client uses it. A producer
sends media and a consumer receives media. These media roles do not specify who
initiates a transport connection.

## Endpoint Model

The `protocol` selector identifies the media mapping. Its typed
`protocoloptions` define connection setup and producer input requirements.
OPTIONAL options have no default unless stated otherwise. Core's
null-as-deletion behavior for updates remains unchanged.

### Base-Model Integration

This extension uses one `usage` value per Endpoint, either `producer` or
`consumer`. Protocol-specific direction restrictions are stated below.
Reverse-direction control and feedback do not require a second usage value.

Media Endpoints MUST NOT associate Message Resources or message groups,
directly or by reference. They MUST NOT declare `envelope` or `envelopeoptions`.

Implementations MUST compose the protocol definitions into
the existing Endpoint Group model. The base `protocol.ifvalues` and
`siblingattributes` mechanism selects the applicable `protocoloptions`.
Common base options MUST be retained without defining colliding conditional
and unconditional attributes.

The base's message-oriented Endpoint prose needs to include protocol-defined
media flows. This does not remove Message Resources from messaging endpoints.
An empty inherited `messages` collection and generated discovery attributes
such as `messagescount: 0` do not associate a Message Resource and are allowed.
Non-empty collections and message-group associations are prohibited for media
Endpoints, including writes directly beneath an Endpoint.

## Input Requirements

A `producer` Endpoint describes the input accepted by a configured receiving path.
The following options occur directly in `protocoloptions` for the `producer`
mappings listed below. Each value is a requirement, not a preference or an
enumeration of alternatives. Consumers MUST omit these producer-only options.

| Option | Type | Meaning |
| --- | --- | --- |
| `streamformat` | String | REQUIRED carriage format. Permitted values and the default depend on the protocol. |
| `videocodec` | String | REQUIRED video encoding from an open vocabulary, or `none` to prohibit video. |
| `audiocodec` | String | REQUIRED audio encoding from an open vocabulary, or `none` to prohibit audio. |

Codec values are case-sensitive. `H264` and `H265` identify AVC and HEVC;
`VP8`, `VP9`, and `AV1` identify the respective video codecs. `AAC` identifies
MPEG-4 AAC-LC (audio object type 2); `Opus`, `PCMA`, and `PCMU` identify Opus and
G.711 A-law and mu-law. Codec identifiers form an open vocabulary; the values
listed here and in the protocol tables are examples, not exhaustive enumerations.
Additional identifiers MUST have a defined encoding and native carriage for the
selected protocol and stream format, and MUST be accepted by the receiving path.
An additional identifier MUST NOT redefine an identifier specified here.
The value `none` is available for either codec in every `producer` mapping.

A codec other than `none` requires exactly one stream of that media kind. Both
codecs MUST NOT be `none`. Thus video-only input explicitly sets `audiocodec`
to `none`; audio-only input sets `videocodec` to `none`. Omitted options take the
protocol-specific defaults, including media presence. A publisher MUST declare
an override whenever its receiving path cannot accept the default. Defaults
are conventions of this extension, not codec requirements imposed by the wire
protocol or assertions about an arbitrary server's configuration.

Codec initialization data, payload mappings, and parameters such as profile
and level are carried through the selected format or session setup. Where a
protocol does not negotiate codec parameters, producers need prior agreement
on any codec-specific restrictions imposed by the receiving path.

RTP carriage uses [RFC 6184][h264-rtp] for H.264, [RFC 7798][h265-rtp] for
H.265, [RFC 7741][vp8-rtp] for VP8, [RFC 9628][vp9-rtp] for VP9, and the
[AV1 RTP payload specification v1.0.0][av1-rtp] for AV1. AAC uses the
MPEG4-GENERIC payload of [RFC 3640][aac-rtp], Opus uses
[RFC 7587][opus-rtp], and PCMA/PCMU use [RFC 3551][rtp-avp]. SDP carries the
applicable format parameters. These references also identify the underlying
codec specifications.

For MPEG-TS, H.264 and H.265 use their native MPEG systems carriage; AAC uses
ADTS framing. Opus uses the [version 0.1.3 draft MPEG-TS mapping][opus-ts],
including its descriptors and access-unit framing. This is an explicit draft
dependency, distinct from the published [Opus codec specification][opus].

Providers MUST advertise requirements consistent with their receiving path and
intended downstream delivery. For example, forwarding audio to WebRTC without
transcoding can require Opus input even though an SRT ingest demuxer also accepts
AAC. The provider remains responsible for admission and enforcement. A registry
declaration neither configures the server nor installs a transcoder.

Producers MUST apply these requirements when configuring their encoder and
muxer, and MUST also satisfy native session setup and admission. A native
description or negotiated result that contradicts the advertised requirements
is a configuration error; the producer MUST NOT silently send a different
format. Consumers use the protocol's native media discovery.

## Connection Discovery

Clients use normal Core discovery to select an Endpoint by `usage`, `protocol`,
and optionally `channel`. Address order retains its base meaning; it does not
describe simultaneous tracks or adaptive variants. The chosen protocol then
determines connection establishment and media discovery.

For the SRT and RTMP mappings, the client connects to the advertised listener
and supplies the declared public route. For RTSP and WebRTC it uses the stated
session procedures. UDP producers send to the advertised destination. Base
authorization metadata and authorized credential provisioning govern access.

Reading an Endpoint MUST NOT initiate a media connection or start capture.
Connection, multicast membership, and signaling require a separate authorized
action.

## Protocol Definitions

These selectors extend the base selector vocabulary. They identify how to reach
and use the interface, not a fixed encoded representation. Unsupported protocol
extensions cannot be inferred from a file suffix or shared channel name.

Each `producer` mapping below defines its stream-format and codec defaults.
Native protocol versions and session features follow the selected protocol.

### SRT

Selector: `SRT`. SRT is a project-defined transport, not an IETF standard.
The [SRT v1.5.4 documentation][srt-options] is the reference for the Stream ID
option below. This selector is not an assertion of a particular SDK version or
an on-wire protocol version.

| Option | Type | REQUIRED | Meaning |
| --- | --- | --- | --- |
| `streamid` | String | No | Public routing identifier supplied by the SRT caller during setup, with native SRT Stream ID semantics. |
| `streamformat` | String | No | `mpegts`; default `mpegts`. |
| `videocodec` | String | No | Open codec identifier, for example `H264` or `H265`, or `none`; default `H264`. |
| `audiocodec` | String | No | Open codec identifier, for example `AAC` or `Opus`, or `none`; default `AAC`. |

The format and codec options apply only to producers.

The basic deployment convention is `srt://host:port`, with an explicit port.
It identifies an advertised SRT listener. The client connects to that listener
for either `producer` or `consumer` usage. This is a catalog address convention,
not a claim that SRT defines an IETF-standard URL grammar. This mapping uses
SRT live transmission mode with the client as caller.

An explicitly supplied `streamid` MUST satisfy the referenced implementation's
Stream ID syntax and size limits and MUST NOT be a secret. Providers MUST
include it when routing requires it. Omission means the caller supplies no
Stream ID. The caller passes the value unchanged; `channel` is not a substitute
for it. The [SRT access-control guidelines][srt-access] define the structured
Stream ID convention used in the examples. Credentials and security
configuration use native provisioning.

The producer sends a single-program MPEG-TS stream with 188-byte transport
packets, PAT and PMT signaling, and the declared elementary streams. SRT live
payloads carry whole transport packets, at most seven per payload (1316 bytes),
subject to a lower native transport limit. These are this mapping's carriage
conventions; SRT itself transports arbitrary bytes and does not negotiate codecs.
Consumers discover program and elementary-stream information from the stream.

### WebRTC

Selector: `WebRTC`. [RFC 8834][rtp-webrtc], [RFC 8835][transports-webrtc],
and [RFC 8827][webrtc-security] define the referenced media transport and
security architecture. WebRTC does not itself define application signaling.

| Option | Type | REQUIRED | Meaning |
| --- | --- | --- | --- |
| `signaling` | String | Yes | `WHIP/RFC9725`, `WHEP/draft-ietf-wish-whep-03`, or `external`. |
| `signalingreference` | URI | Conditional | Absolute HTTPS URI identifying the signaling specification and revision; REQUIRED for `external`, omitted for the two fixed selectors. |
| `streamformat` | String | No | Producer-only: `srtp`; default `srtp`. |
| `videocodec` | String | No | Producer-only: open codec identifier, for example `H264` or `VP8`, or `none`; default `H264`. |
| `audiocodec` | String | No | Producer-only: open codec identifier, for example `Opus`, `PCMA`, or `PCMU`, or `none`; default `Opus`. |

Producer input uses separately packetized media over WebRTC's secure RTP
transport. A WHIP producer configures
its encoder and SDP offer for the declared codecs. Offer/answer supplies the
codec parameters and transport details; the answer MUST permit the REQUIRED
media before the producer starts sending. WebRTC's mandatory codec baselines
are specified in [RFC 7742][webrtc-video] and [RFC 7874][webrtc-audio].

The address identifies the signaling entry point, not a `webrtc://` socket.
The signaling protocol determines offer/answer roles and session lifecycle.
Packetization, ICE, DTLS, and RTP/RTCP parameters follow native signaling and
negotiation. Consumer codec selection takes place in that exchange.

SDP offers and answers, ICE credentials and candidates, negotiated fingerprints,
SSRCs, session locations, and selected media details MUST NOT be stored as static
Endpoint configuration. The selected native signaling protocol's rules apply.

`WHIP/RFC9725` selects [RFC 9725][whip], a Standards Track RFC published in
March 2025. It permits only `producer` usage and an HTTPS entry point. The client
supplies media using WHIP setup, authentication, and teardown.

`WHEP/draft-ietf-wish-whep-03` selects the [18 August 2025 Internet-Draft][whep03]
for `consumer` usage, with an HTTPS entry point. That revision expired on
19 February 2026. It is an explicit draft dependency, not a claim about the
latest WHEP publication status. Implementations MUST identify that dependency
when claiming support. A successor revision does not silently replace it.
The draft's offer/counter-offer and session procedures remain authoritative.

External signaling MUST define how its entry address is used, its supported
media directions, and its security and session procedures. It does not acquire
WHIP or WHEP semantics merely because it uses HTTP.

### RTSP

Selectors: `RTSP/1.0` and `RTSP/2.0`, selecting [RFC 2326][rtsp1] and
[RFC 7826][rtsp2]. The latter obsoletes the former; the legacy selector remains
useful for deployed services.

The address is a native RTSP presentation or control URI, including the public
publishing or playback path. Consumer descriptions are obtained with DESCRIBE;
producers supply their descriptions with ANNOUNCE. SETUP establishes transport
parameters and track control addresses.

The following options apply to `RTSP/1.0` producers:

| Option | Type | REQUIRED | Meaning |
| --- | --- | --- | --- |
| `streamformat` | String | No | `rtp` for separately packetized elementary streams, or `rtp-mpegts` for a single MPEG-TS program carried in RTP; default `rtp`. |
| `videocodec` | String | No | Open codec identifier, for example `H264`, `H265`, `VP8`, `VP9`, or `AV1`, or `none`; default `H264`. |
| `audiocodec` | String | No | Open codec identifier, for example `AAC`, `Opus`, `PCMA`, or `PCMU`, or `none`; default `AAC`. |

For `rtp-mpegts`, codecs require defined MPEG-TS carriage, such as
the H.264, H.265, AAC, and Opus mappings described above. The MPEG-TS program
uses 188-byte packets with PAT and PMT signaling, wrapped in RFC 2250 RTP
payloads. The receiving path MUST be configured to demultiplex that program
when its outputs require elementary streams. For `rtp`, each supplied stream
has its own native RTP payload mapping in the producer's SDP.

`consumer` usage selects playback. `producer` usage is available for the RTSP/1.0
recording procedures where supported by the service. RTSP/2.0 removed RECORD
and ANNOUNCE, so this document defines no RTSP/2.0 `producer` mapping. Private
upload extensions require their own explicit protocol definition.

Use the selected RTSP specification's URI and security rules. A TLS deployment
convention not defined by that version needs an explicit native agreement.
Protection of the control connection does not alone imply protection of a
separate media transport.

### RTP and SRTP

Selector: `RTP/2`, for [RFC 3550][rtp] RTP without RTSP or WebRTC signaling.
RTP does not supply general session discovery or codec negotiation. Some
payload mappings require information outside the RTP packets themselves.

| Option | Type | REQUIRED | Meaning |
| --- | --- | --- | --- |
| `sessiondescription` | URI | Conditional | Absolute HTTPS URI of a native SDP session description under RFC 8866; REQUIRED for producers, OPTIONAL for consumers. |
| `streamformat` | String | No | Producer-only: `rtp` or `rtp-mpegts`; default `rtp`, with the carriage meanings defined for RTSP. |
| `videocodec` | String | No | Producer-only: open codec identifier, for example `H264`, `H265`, `VP8`, `VP9`, or `AV1`, or `none`; default `H264`. |
| `audiocodec` | String | No | Producer-only: open codec identifier, for example `AAC`, `Opus`, `PCMA`, or `PCMU`, or `none`; default `AAC`. |

The `rtp-mpegts` carriage requirements defined for RTSP also apply.
A `producer` Endpoint MUST provide `sessiondescription`.
Its SDP describes the receiver's configured RTP session, including destination
ports, payload types, clock rates, and format parameters. Producers MUST use
those mappings; codec defaults alone do not determine RTP payload numbers.
The description MUST agree with the effective input options. For example, an
H.264 input requires the receiver's payload type and RFC 6184 parameters even
when `videocodec` is omitted.

A prearranged RTP destination can use the deployment convention
`udp://host:port`. The address is the media destination, including a multicast
group when applicable; it is not necessarily a server's socket. The selected
session arrangement determines who sends to or receives at that destination.

When the address alone is insufficient, clients need a native session
description or authorized out-of-band configuration. The session description
retains payload mappings, RTP profiles, RTCP addressing, multicast source
selection, and related parameters.
A description reference does not make a dynamic payload type self-describing.
Clients MUST NOT guess missing payload or security mappings.

SRTP and SRTCP follow [RFC 3711][srtp] and the selected native key-management
agreement. Native profiles determine protection and RTCP behavior. Public
descriptions MUST NOT embed keying material; credentials and per-session keys
are supplied through authorized setup. A catalog does not replace that setup.

For MPEG-TS over RTP, the native payload mapping is [RFC 2250][mpeg-rtp].
Other RTP payload formats retain their own specifications. Multiple media
sessions and synchronized streams use native session descriptions.

### MPEG-TS over UDP

Selector: `MPEGTS-UDP`, identifying direct MPEG transport stream delivery over
[UDP][udp], without RTP headers. MPEG systems definitions, including program
signaling, remain with [ITU-T H.222.0][mpeg-systems] / ISO/IEC 13818-1 and the
deployment's applicable edition. This is a deployment selector, not a new
transport-stream specification.

The address convention is `udp://host:port` for the media destination. Multicast
membership and source selection follow the native session or deployment
arrangement. Unicast receiver addressing MUST likewise be arranged before
delivery. `usage` describes the client's media role; UDP has no caller/listener
negotiation.

| Option | Type | REQUIRED | Meaning |
| --- | --- | --- | --- |
| `streamformat` | String | No | Producer-only: `mpegts`; default `mpegts`. |
| `videocodec` | String | No | Producer-only: open codec identifier, for example `H264` or `H265`, or `none`; default `H264`. |
| `audiocodec` | String | No | Producer-only: open codec identifier, for example `AAC` or `Opus`, or `none`; default `AAC`. |

A producer sends a single-program MPEG-TS stream with PAT and PMT
signaling to the advertised destination. Each UDP payload contains whole
188-byte transport packets, at most seven (1316 bytes), further limited by
the path MTU. The receiver MUST already be listening on that destination.
Consumers read the stream's native program and elementary-stream information.

### RTMP and RTMPS

Selector: `RTMP/1.0`, referring to the [published RTMP 1.0 specification][rtmp].
RTMPS denotes RTMP carried over TLS. Neither is an IETF Standards Track protocol.

The entry URI uses `rtmp://host:port` or `rtmps://host:port`. The following
options identify the application and public stream route explicitly:

| Option | Type | REQUIRED | Meaning |
| --- | --- | --- | --- |
| `application` | String | Yes | Non-empty application name sent in the RTMP `connect` command's `app` property. |
| `streamname` | String | Yes | Non-empty public stream name passed to `publish` or `play`. |
| `streamformat` | String | No | Producer-only: `flv`; default `flv`. |
| `videocodec` | String | No | Producer-only: open codec identifier, for example `H264`, or `none`; default `H264`. |
| `audiocodec` | String | No | Producer-only: open codec identifier, for example `AAC`, or `none`; default `AAC`. |

The client builds `tcUrl` from the entry URI and the application path, and
passes `streamname` unchanged to the selected command. An application can
contain slash-separated path segments; URI construction percent-encodes each
segment. For example, application `live` and stream name `studio-main` select
the public publishing route conventionally written as
`rtmps://contribution.example.net:443/live/studio-main`. Secret publish keys
and credentials MUST be supplied separately.

The client initiates the connection for either usage. `producer` usage selects
publishing with native publish type `live`; `consumer` usage selects playback.
`flv` identifies the audio/video tag-body encoding carried in RTMP media
messages, as specified in the [FLV format][flv]. When using H.264 or AAC, the
producer sends the corresponding AVC or AAC sequence header before its coded
media. Other codecs follow their defined native carriage. It sends RTMP messages, not an FLV
file header. Consumer format information remains in the protocol and stream.

Enhanced RTMP codec signaling and other extensions are not implied by the
historical selector. Their support requires an explicit native agreement.
The protocol's command and media messages do not become xRegistry Messages.

### HLS

Selector: `HLS`. [RFC 8216][hls] supplies the published HLS baseline; it is an
Informational RFC, not an Internet Standards Track specification. Its native
playlist version and feature rules determine how a client interprets delivery.
The selector does not force a specific EXT-X-VERSION value.

Only `consumer` usage is defined. The address identifies an HTTP(S) entry playlist,
not a media segment. The client retrieves the playlist and follows native
selection, update, and media-fetch procedures. HLS does not define a general
producer upload interface; publishing to an origin requires a separate ingest
Endpoint.

Variant streams, codecs, alternate audio and subtitles, target duration, live
or on-demand state, encryption methods, and key-system information are obtained
from the playlists and media. Clients follow native playlist version and
feature handling, including low-latency extensions where supported.

### MPEG-DASH

Selector: `DASH`. The protocol is defined by ISO/IEC 23009-1; the
[2022 edition][dash-iso] is a reference point for this draft. Industry
interoperability profiles do not replace the ISO specification.

Only `consumer` usage is defined. The HTTP(S) address identifies an MPD. The client
obtains periods, adaptation sets, representations, codec information, segment
locations, timing, and content-protection information from the MPD and associated
media. Native MPD profiles and feature handling apply, including adaptive
selection, time-shift availability, low-latency operation, and content protection.

### RIST

Selectors: `RIST-Simple/2020` and `RIST-Main/2024`, identifying
[VSF TR-06-1:2020][rist-simple] and [VSF TR-06-2:2024][rist-main]. These are
Video Services Forum Technical Recommendations, not IETF RFCs. The years name
document editions, not handshake versions.

The entry address follows the deployed RIST implementation's native convention.
Native RIST setup governs recovery, encapsulation, and security.

| Option | Type | REQUIRED | Meaning |
| --- | --- | --- | --- |
| `streamformat` | String | No | Producer-only: `rtp-mpegts`; default `rtp-mpegts`. |
| `videocodec` | String | No | Producer-only: open codec identifier, for example `H264` or `H265`, or `none`; default `H264`. |
| `audiocodec` | String | No | Producer-only: open codec identifier, for example `AAC` or `Opus`, or `none`; default `AAC`. |

The producer supplies a single MPEG-TS program in RFC 2250 RTP
payloads through the selected RIST profile's native encapsulation. The program
contains PAT, PMT, and the declared elementary streams.

Both media directions are permitted where the deployment supports them. The
receiver obtains format information through the carried media and native
descriptions. The RIST address and session mapping remains subject to the
source-review work listed in [Open Issues](#open-issues).

### Other Protocols

Additional protocol mappings can use Core's extension mechanisms. A mapping
needs an identified native protocol, an address interpretation, and a statement
of supported media directions. It SHOULD add options only for information that
need to be known before native setup and cannot already be expressed by existing
Endpoint attributes.

Professional media suites such as ST 2110 and media delivery over QUIC,
WebTransport, or WebSocket require mappings that identify the applicable media
and session specifications.

## Distribution Example

This abbreviated client-input Registry document describes a generic distribution
server with SRT ingress and WebRTC egress. The configured input requires
MPEG-TS with H.264 video and Opus audio.
The server forwards these codecs to WebRTC without transcoding. Hosts are
illustrative; the public Stream ID selects the publishing path.

```json
{
  "specversion": "1.0-rc3",
  "registryid": "studio-distribution",
  "endpoints": {
    "srt-ingress": {
      "endpointid": "srt-ingress",
      "name": "Studio contribution input",
      "usage": ["producer"],
      "channel": "studio-main",
      "protocol": "SRT",
      "protocoloptions": {
        "deployed": true,
        "endpoints": [{ "uri": "srt://contribution.example.net:9000" }],
        "streamid": "#!::r=studio-main,m=publish",
        "streamformat": "mpegts",
        "videocodec": "H264",
        "audiocodec": "Opus"
      }
    },
    "webrtc-egress": {
      "endpointid": "webrtc-egress",
      "name": "Studio viewing output",
      "usage": ["consumer"],
      "channel": "studio-main",
      "protocol": "WebRTC",
      "protocoloptions": {
        "deployed": true,
        "endpoints": [{ "uri": "https://view.example.net/studio-main/whep" }],
        "signaling": "WHEP/draft-ietf-wish-whep-03"
      }
    }
  }
}
```

The producer selects SRT caller/live mode, connects to the advertised host and
port, and sends `#!::r=studio-main,m=publish` as the Stream ID. It encodes the specified
video and audio, muxes one MPEG-TS program, and uses up to 1316 bytes per SRT
payload. The audio option overrides the AAC default because the configured
egress uses Opus. For video-only contribution the publisher would instead
declare `audiocodec: "none"`.

The consumer connects through WHEP and negotiates the WebRTC session.
Credentials are provisioned outside this public example; omission does not
assert anonymous or unencrypted access.

The shared `channel` correlates the interfaces. It does not assert that their
bytes are identical or that the server transcodes. Relay, remuxing,
repacketization, and transcoding are server behavior outside this metadata
extension. The server MUST supply media that satisfies the negotiated egress
session, or reject that session when it cannot.

### RTMP Producer

A separate video-only publishing path can use the RTMP defaults. This producer
sends FLV-encoded H.264 video in RTMP
media messages. The explicit `audiocodec` value disables the default AAC audio.

```json
{
  "endpointid": "rtmp-video-ingress",
  "usage": ["producer"],
  "channel": "studio-video",
  "protocol": "RTMP/1.0",
  "protocoloptions": {
    "deployed": true,
    "endpoints": [{ "uri": "rtmps://contribution.example.net:1936" }],
    "application": "live",
    "streamname": "studio-video",
    "audiocodec": "none"
  }
}
```

### SRT Consumer

A consumer can discover an SRT listener without a codec declaration. Both the
producer in the previous example and this consumer initiate connections to their
respective advertised listeners; their media directions differ.

```json
{
  "endpointid": "srt-viewing",
  "usage": ["consumer"],
  "channel": "studio-main",
  "protocol": "SRT",
  "protocoloptions": {
    "deployed": true,
    "endpoints": [{ "uri": "srt://view.example.net:9001" }],
    "streamid": "#!::r=studio-main,m=request"
  }
}
```

The consumer discovers media details from the carried format. SRT transport
setup does not negotiate a codec on its behalf.

### HLS Consumer

An HLS Endpoint identifies the entry playlist. Adaptive selection and format
discovery need no parallel registry description.

```json
{
  "endpointid": "hls-viewing",
  "usage": ["consumer"],
  "channel": "studio-main",
  "protocol": "HLS",
  "protocoloptions": {
    "deployed": true,
    "endpoints": [{ "uri": "https://view.example.net/studio-main/master.m3u8" }]
  }
}
```

### HTTP Payload Consumer

The base `HTTP` selector can describe direct media delivery in an HTTP response
body. This example declares a continuous audio stream using the inherited
`method` and `headers` options. It explicitly sets `method` to `GET` because
the base default is `POST`. The client has `consumer` usage even though it
initiates the request.

```json
{
  "endpointid": "radio-listening",
  "usage": ["consumer"],
  "protocol": "HTTP",
  "protocoloptions": {
    "deployed": true,
    "endpoints": [{ "uri": "https://radio.example.net/live" }],
    "method": "GET",
    "headers": [
      { "name": "Icy-MetaData", "value": "1" }
    ]
  }
}
```

The response's `Content-Type` and native media headers identify the payload
format and encoding. The `Icy-MetaData` request header asks for interleaved
ICY metadata when the service supports it. If the response includes
`icy-metaint`, an ICY-aware client uses that interval and the metadata block
lengths to separate metadata from audio before decoding. Without that response
header, the client processes the body as media without ICY interleaving.
The metadata request header can be omitted for ordinary media retrieval.

The same declaration pattern applies to finite audio or video files. Range
requests, conditional requests, and caching follow [HTTP semantics][http]
where supported; a continuous stream does not imply support for seeking or
resuming. The example assumes standard HTTP responses. Legacy `ICY 200 OK`
status lines require separate client compatibility and are not implied by
the `HTTP` selector. HLS playlists and DASH manifests use their respective
mappings above.

## Validation and Conformance

A metadata publisher conforms by following Core and the selected Endpoint
mapping, excluding Message associations and secrets, and limiting declared input
requirements to `producer` Endpoints. A media-aware registry validates these known
rules and preserves extensions under Core. It need not implement media protocols.

Validation checks the resulting entity after an update, not a partial patch in
isolation. It MUST check permitted usage, attribute types, URI syntax,
message-association prohibition, and the applicable selector rules.
In particular, WHIP cannot be declared for `consumer` usage, HLS and DASH have no
`producer` mapping here, and RTSP/2.0 has no recording mapping here.

For `producer` Endpoints, validation MUST apply the selected mapping's defaults
before checking option combinations. It MUST NOT reject a codec identifier
solely because it is absent from this document or unknown to the validator.
It MUST reject known invalid format/codec combinations, both codecs set to
`none`, and producer-only options on `consumer` Endpoints. RTP producers require a
session-description URI; RTMP Endpoints require application and stream names.

A connector uses an explicitly supported protocol mapping, applies its effective
input requirements, and follows native setup and security rules. Before sending,
it MUST check any REQUIRED SDP against the declared input and its own encoder
configuration. A connector that does not support the REQUIRED codec or its
carriage MUST report that it cannot configure the session; it MUST NOT
substitute a default codec. A connector that cannot interpret a REQUIRED session description
or signaling specification MUST report that it cannot configure the session.

Successful metadata validation establishes neither reachability nor media
compatibility. Negotiation, native descriptions, and actual media determine
whether a consumer can receive and decode a stream. Implementations MUST NOT
report static end-to-end media compatibility merely because selectors or channel
names match.

Model composition and semantic validation remain necessary implementation work
before a registry claims conformance; this prose is not a machine-readable
model artifact or evidence of a working validator.

## Security Considerations

Catalog access does not authorize media access, ingestion, capture, or session
termination. Providers enforce those permissions using native mechanisms and
deployment policy. Base authorization alternatives retain their meaning; they
are not converted into a generic encryption policy.

Public metadata MUST NOT contain passwords, passphrases, bearer tokens, private
keys, secret publish keys, SRTP keying material, ICE credentials, or access URLs
whose possession authorizes a session. URI userinfo and secret-bearing path or
query values are unsuitable for advertised addresses. Authentication material
is supplied outside the catalog. Logging MUST NOT expose resolved credentials
or session URLs.

Native security remains mandatory where the selected protocol requires it.
For example, WebRTC requires secure media transport. HTTPS protects an HTTP
exchange; it does not by itself protect a separate media path. SRT encryption
and RIST protection are
configured through their native mechanisms. Clients MUST NOT disable protection
or bypass authentication merely to make an advertised address work.

Catalog and native descriptions can both contain untrusted destinations.
Authorized fetches and connections MUST apply local destination and credential
policy to redirects, playlist children, MPD references, SDP addresses, and ICE
candidates as well as the initial entry point. Static metadata validation MUST
NOT automatically fetch references or probe media services.

Clients need bounds on document size, redirects, parser work, and media resource
use. MPD parsers MUST disable external-entity processing. Displayed metadata
MUST be escaped, and connection values MUST NOT be concatenated into shell
commands. Private addresses and routing identifiers can themselves be sensitive;
publishers SHOULD limit public disclosure.

Deleting an Endpoint does not terminate a media session or revoke already issued
credentials. Native lifecycle, revocation, retention, and access-control
procedures remain necessary. `consumer` usage is not permission to activate a
camera or microphone.

## Open Issues

This section is informative. Adoption still requires a composed Core model and
semantic validation tests, plus agreement on selector names, producer defaults,
and the proposed format and codec vocabulary. Interoperability tests need to
cover default audio/video, video-only input, and constrained SRT-to-WebRTC
delivery against configured servers. Additional codec/profile combinations
require defined native carriage and admission rules.

The pinned WHEP revision is an expired draft; its current publication status
needs to be checked before choosing an adoption baseline. No current RFC number is
asserted here. The RIST editions were checked against the publisher index during
initial drafting, but clause-level RIST and RTMP PDF review and full ISO/ITU
source review remain outstanding. RIST needs a complete address and session
setup mapping before interoperable automatic connection can be claimed. The
Opus-in-MPEG-TS draft and FLV source also need clause-level review; Opus carriage
needs to be checked against deployed muxer and demuxer implementations before
adoption.

## References

### Normative References

These references govern the base model, the selected native protocol, and its
media encodings. A protocol reference is conditional on using
that protocol. Listing a vendor specification here does not make it an IETF
standard. Incorporated native dependencies retain their own requirements.

- [Endpoint Registry Service 1.0-rc3][endpoint] and [model][endpoint-model], pinned above.
- [xRegistry Core][core] and [Core model rules][core-model], same commit.
- [RFC 2119][rfc2119] and [RFC 8174][rfc8174], BCP 14 requirement language.
- [RFC 3986][uri], Uniform Resource Identifier (URI): Generic Syntax, January 2005.
- [SRT API Socket Options, v1.5.4][srt-options], project documentation; reference for Stream ID behavior, not a mandatory SDK version.
- [SRT Access Control (Stream ID) Guidelines, v1.5.4][srt-access], structured public routing identifiers.
- [RFC 8834][rtp-webrtc], Media Transport and Use of RTP in WebRTC, January 2021.
- [RFC 8835][transports-webrtc], Transports for WebRTC, January 2021.
- [RFC 8827][webrtc-security], WebRTC Security Architecture, January 2021.
- [RFC 7742][webrtc-video], WebRTC Video Processing and Codec Requirements, March 2016.
- [RFC 7874][webrtc-audio], WebRTC Audio Codec and Processing Requirements, 2016-05.
- [RFC 9725][whip], WebRTC-HTTP Ingestion Protocol (WHIP), March 2025; Standards Track.
- [RFC 2326][rtsp1], Real Time Streaming Protocol (RTSP), April 1998; legacy mapping, obsoleted by RFC 7826.
- [RFC 7826][rtsp2], Real-Time Streaming Protocol Version 2.0, December 2016.
- [RFC 3550][rtp], RTP: A Transport Protocol for Real-Time Applications, July 2003.
- [RFC 3711][srtp], The Secure Real-time Transport Protocol (SRTP), March 2004.
- [RFC 8866][sdp], SDP: Session Description Protocol, January 2021.
- [RFC 2250][mpeg-rtp], RTP Payload Format for MPEG1/MPEG2 Video, January 1998; MPEG-TS carriage where selected.
- [RFC 6184][h264-rtp], RTP Payload Format for H.264 Video.
- [RFC 7798][h265-rtp], RTP Payload Format for High Efficiency Video Coding (HEVC).
- [RFC 7741][vp8-rtp] and [RFC 9628][vp9-rtp], RTP payload formats for VP8 and VP9 video.
- [RTP Payload Format for AV1 v1.0.0][av1-rtp], Alliance for Open Media, 15 December 2024.
- [RFC 3640][aac-rtp], RTP Payload Format for Transport of MPEG-4 Elementary Streams.
- [RFC 6716][opus], Definition of the Opus Audio Codec, and [RFC 7587][opus-rtp], its RTP payload format.
- [RFC 3551][rtp-avp], RTP Profile for Audio and Video Conferences with Minimal Control; PCMA/PCMU carriage.
- [RFC 768][udp], User Datagram Protocol, August 1980.
- [ITU-T H.222.0 (06/2021)][mpeg-systems], Generic coding of moving pictures and associated audio information: Systems; reference edition for MPEG-TS, subject to the source-review limit above.
- [Adobe's Real Time Messaging Protocol][rtmp], Adobe Systems Incorporated, 21 December 2012; copy hosted by Veovera Software Organization; source-review limit above.
- [Adobe Flash Video File Format Specification, Version 10.1][flv], Adobe Systems Incorporated, August 2010; copy hosted by Veovera Software Organization. Defines FLV audio and video tag encoding, including AVC and AAC sequence headers.
- [RFC 9110][http], HTTP Semantics, June 2022.
- [RFC 8216][hls], HTTP Live Streaming, August 2017; Informational, Independent Submission stream.
- [ISO/IEC 23009-1:2022][dash-iso], Dynamic adaptive streaming over HTTP (DASH), Part 1: Media presentation description and segment formats; source-review limit above.
- [VSF TR-06-1:2020][rist-simple], Reliable Internet Stream Transport (RIST), Simple Profile, 25 June 2020.
- [VSF TR-06-2:2024][rist-main], Reliable Internet Stream Transport (RIST), Main Profile, 12 June 2024; both RIST documents are VSF Technical Recommendations, with source-review limits above.

### Conditional Draft Reference

- [draft-ietf-wish-whep-03][whep03], WebRTC-HTTP Egress Protocol (WHEP), 18 August 2025; intended Standards Track, expired 19 February 2026. REQUIRED only for the named WHEP mapping.
- [Opus-in-MPEG-TS mapping draft v0.1.3][opus-ts], draft linked by Xiph's [OpusTS page][opus-ts-index]; REQUIRED when Opus is carried in MPEG-TS, subject to the source-review limit above.

### Informative References

- [VSF Technical Recommendations][vsf], publisher's discovery index.
- [DASH-IF guidelines][dash-guidelines], industry interoperability material.
- [Enabling Low-Latency HTTP Live Streaming][llhls-guide], publisher guidance; not a version-pinned normative protocol dependency.

[endpoint]: https://github.com/xregistry/spec/blob/adf5b6a63e60c3baa78e844da8b7ce2a0d60c179/endpoint/spec.md
[endpoint-model]: https://github.com/xregistry/spec/blob/adf5b6a63e60c3baa78e844da8b7ce2a0d60c179/endpoint/model.json
[core]: https://github.com/xregistry/spec/blob/adf5b6a63e60c3baa78e844da8b7ce2a0d60c179/core/spec.md
[core-model]: https://github.com/xregistry/spec/blob/adf5b6a63e60c3baa78e844da8b7ce2a0d60c179/core/model.md
[rfc2119]: https://www.rfc-editor.org/rfc/rfc2119.html
[rfc8174]: https://www.rfc-editor.org/rfc/rfc8174.html
[uri]: https://www.rfc-editor.org/rfc/rfc3986.html
[srt-options]: https://github.com/Haivision/srt/blob/v1.5.4/docs/API/API-socket-options.md
[srt-access]: https://github.com/Haivision/srt/blob/v1.5.4/docs/features/access-control.md
[rtp-webrtc]: https://www.rfc-editor.org/rfc/rfc8834.html
[transports-webrtc]: https://www.rfc-editor.org/rfc/rfc8835.html
[webrtc-security]: https://www.rfc-editor.org/rfc/rfc8827.html
[webrtc-video]: https://www.rfc-editor.org/rfc/rfc7742.html
[webrtc-audio]: https://www.rfc-editor.org/rfc/rfc7874.html
[whip]: https://www.rfc-editor.org/rfc/rfc9725.html
[whep03]: https://www.ietf.org/archive/id/draft-ietf-wish-whep-03.html
[rtsp1]: https://www.rfc-editor.org/rfc/rfc2326.html
[rtsp2]: https://www.rfc-editor.org/rfc/rfc7826.html
[rtp]: https://www.rfc-editor.org/rfc/rfc3550.html
[srtp]: https://www.rfc-editor.org/rfc/rfc3711.html
[sdp]: https://www.rfc-editor.org/rfc/rfc8866.html
[mpeg-rtp]: https://www.rfc-editor.org/rfc/rfc2250.html
[h264-rtp]: https://www.rfc-editor.org/rfc/rfc6184.html
[h265-rtp]: https://www.rfc-editor.org/rfc/rfc7798.html
[vp8-rtp]: https://www.rfc-editor.org/rfc/rfc7741.html
[vp9-rtp]: https://www.rfc-editor.org/rfc/rfc9628.html
[av1-rtp]: https://aomediacodec.github.io/av1-rtp-spec/v1.0.0.html
[aac-rtp]: https://www.rfc-editor.org/rfc/rfc3640.html
[opus]: https://www.rfc-editor.org/rfc/rfc6716.html
[opus-rtp]: https://www.rfc-editor.org/rfc/rfc7587.html
[rtp-avp]: https://www.rfc-editor.org/rfc/rfc3551.html
[opus-ts]: https://people.xiph.org/~tterribe/opus/ETSI_TS_opus-v0.1.3-draft.doc
[opus-ts-index]: https://wiki.xiph.org/OpusTS
[udp]: https://www.rfc-editor.org/rfc/rfc768.html
[mpeg-systems]: https://www.itu.int/rec/T-REC-H.222.0-202106-I/en
[rtmp]: https://veovera.org/docs/legacy/rtmp-v1-0-spec.pdf
[flv]: https://veovera.org/docs/legacy/video-file-format-v10-1-spec.pdf
[http]: https://www.rfc-editor.org/rfc/rfc9110.html
[hls]: https://www.rfc-editor.org/rfc/rfc8216.html
[dash-iso]: https://www.iso.org/standard/83314.html
[rist-simple]: https://static.vsf.tv/download/technical_recommendations/VSF_TR-06-1_2020_06_25.pdf
[rist-main]: https://static.vsf.tv/download/technical_recommendations/VSF_TR-06-2_2024_06_12.pdf
[vsf]: https://vsf.tv/technical_recommendations.shtml
[dash-guidelines]: https://dashif.org/guidelines/
[llhls-guide]: https://developer.apple.com/documentation/http-live-streaming/enabling-low-latency-http-live-streaming-hls
