# OpenUSD Descriptor Profile

<!-- words: OpenUSD usdasset usdassetgroups usdassets affordance -->

## Abstract

This profile defines how an OpenUSD asset is referenced from a
[Descriptor](../descriptor/spec.md). It applies when a catalog, publication
or processing agreement selects this profile.

## 1. Notation

The key words "MUST", "MUST NOT", "REQUIRED", "SHOULD", "SHOULD NOT" and
"MAY" are interpreted as described in
[RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

## 2. Asset References

This profile defines the class identifier
`https://xregistry.io/classes/usdasset`. The URI is an identifier for the
class; a Consumer MUST NOT retrieve it merely to classify a Reference.

A Reference of this class MUST identify an OpenUSD asset representation at
its `url`. When an [OpenUSD Artifact Registry](spec.md) serves the asset,
the Publisher MUST provide the document-view URL. The Consumer MUST use
that URL unchanged and validate the representation using a supported
OpenUSD format.

For example, the following named Reference selects one asset Version.

```json
{
  "geometry": {
    "class": "https://xregistry.io/classes/usdasset",
    "url": "https://assets.example/usdassetgroups/line1/usdassets/pump7/versions/2"
  }
}
```

Multiple asset References MAY occur in one Descriptor. The applicable
profile MUST define selection when an operation requires a particular
asset. A Consumer MUST report a missing, unsupported or ambiguous REQUIRED
asset rather than select an arbitrary entry.

## 3. Publication and Retrieval

Descriptor identity and publication stability follow the Descriptor
specification. The Publisher MUST keep referenced representations stable
and available for the intended processing and replay period.

Asset dependencies follow the OpenUSD format and registry resolution
rules. A Descriptor bundle includes only representations named directly
by `references.*.url`; dependencies needed by the Consumer can require
additional retrieval.

An association with an asset does not define an affordance-to-prim mapping,
coordinate transform or units conversion. A profile requiring those
relations MUST define them explicitly.

Consumers MUST apply authorization, retrieval and resource-limit policies
before retrieving assets or their dependencies.
