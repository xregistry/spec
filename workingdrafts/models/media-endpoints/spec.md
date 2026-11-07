# Media Endpoints Compatibility and Validation - Version 0.1 (Working Draft)

## Abstract

Codec identifiers use an open vocabulary, so xRegistry validation cannot
establish receiver support. This draft defines the validation boundary and
leaves compatibility decisions to runtime; it preserves the model's
case-sensitive codec vocabulary and protocol-specific `streamformat` values
without defining a codec/format compatibility matrix.

**Status:** Unreleased working draft, dated 29 October 2026. This draft is not
part of a released xRegistry specification.

## Notational Conventions

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this
document are to be interpreted as described in [RFC 2119][rfc2119].

## Scope

The Media Endpoints model describes a protocol and its options, including
producer declarations for `videocodec`, `audiocodec`, and, where defined,
`streamformat`. This draft specifies which of those declarations an xRegistry
validator can check. It does not define codec negotiation, transport behavior,
or a list of compatible codec, protocol, and streamformat combinations.

Codec identifiers are open-vocabulary, case-sensitive strings. Implementations
MUST preserve their spelling and MUST NOT normalize their case when comparing
identifiers.

An endpoint provider MUST ensure that its producer-only codec and
`streamformat` declarations describe the media it provides. A receiving
implementation MUST decide whether it can consume those declarations.
Successful xRegistry validation does not establish that a receiver supports the
advertised media.

## Validation

An xRegistry validator MUST enforce the types and enumerations declared by the
Media Endpoints model. When the selected protocol defines `streamformat`, the
validator MUST accept only values in that protocol's declared enumeration and
MUST reject other values.

A validator that recognizes a codec identifier MUST reject it when its known
media kind conflicts with the attribute: a video codec in `audiocodec` or an
audio codec in `videocodec`. The open vocabulary does not require a validator
to recognize every codec identifier. A validator MUST NOT reject an
unrecognized codec identifier solely because it does not recognize it.

A validator MUST NOT infer codec/protocol/`streamformat` incompatibility beyond
the media-kind check and the protocol's declared `streamformat` enumeration.
This draft defines no codec/format compatibility matrix. Its validation
vectors exercise only the media-kind and declared `streamformat` checks; they
do not assert cross-property codec/format compatibility.

The [validation vectors](tests/validation-vectors.json) are executable examples
for these rules. They cover the codec identifiers explicitly used as model
defaults, an unknown codec identifier, case-sensitive codec recognition,
media-kind mismatch, and each protocol's declared `streamformat` rule. They do
not define a codec vocabulary or compatibility matrix. Run them from the
repository root with:

```powershell
python -B -m pytest workingdrafts\models\media-endpoints\tests -q
```

## Runtime Compatibility

Compatibility depends on the receiving implementation's support for the
advertised media and on protocol-specific behavior. A receiver MUST NOT treat
successful xRegistry validation as proof that it can consume an endpoint. The
provider is responsible for making its declarations accurate, and the receiver
is responsible for deciding whether it supports them. This draft does not
prescribe negotiation or failure signaling.

[rfc2119]: https://tools.ietf.org/html/rfc2119
