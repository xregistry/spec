# WoT Registry: Versioning and Versioned Reference Resolution

This note is informative. It describes versioning in an xRegistry WoT
Registry and how a reference resolves to one document version. The normative
rules are in [spec.md](spec.md). The W3C proposal
`td-versioned-references` and the OPC UA WoT Connectivity specification
(OPC 10100) use the same design, so a document resolves to the same version
in each.

## Problem

A Thing Model (TM) states its own version in `version.model`. The registry
keeps a separate `versionid` for every stored Version. A reference inside a
WoT document (`tm:extends`, `tm:submodel`, `tm:ref`, or a Thing Description's
`rel:type` link) names only the target's identifier and no version. That
leaves three questions open:

1. When a document is published, which `versionid` does it get?
2. When a reference is followed, which Version does it resolve to?
3. How does a consumer reproduce the exact bytes it resolved last time?

Without answers, a late patch release (`1.0.1` published after `1.1.0`) can
become the default Version, and a Thing Description that was built from model
`1.1.0` silently resolves to `1.0.1`.

## Design

Four rules, R1–R4.

**R1. The major version is part of the identity.** A breaking change publishes
a new document identifier (`wotid`), for example `urn:example:pump:v2`. The
previous Resource is marked `deprecated` and names its successor. Every
Version of one `wotid` is therefore backward compatible with every earlier
Version of it, and `compatibility` defaults to `backward` for Thing Models.

**R2. `versionid` equals `version.model`.** For Thing Models the registry
uses `versionmode: semver` with `singleversionroot: true`. A write whose
`versionid` differs from the document's `version.model` is rejected, just as
a mismatch between `wotid` and the document `id` is rejected. SemVer build
metadata (`+…`) is rejected because `versionid` cannot carry `+`.

A Thing Model without a version, or with a version that is not SemVer, gets a
registry-generated `versionid` of the form `0.0.0-N`. N is the lowest positive
integer whose id is not already in use. The Version is marked
`versionorigin: generated`. A generated id is a prerelease, so it sorts below
every release, and it MUST NOT be used as a floor. A Version whose `versionid`
came from `version.model` is marked `versionorigin: authored`.

Thing Descriptions keep `versionmode: manual`. Their `versionid` is chosen
freely, because a TD's version describes an instance revision, not a
compatibility contract.

**R3. A reference carries a floor, never a range.** A reference MAY state the
minimum Version it needs:

| Reference | Floor |
|---|---|
| `tm:extends`, `tm:submodel` link | `tm:minVersion` member on the link |
| `tm:ref` | `tm:minVersion` member beside `tm:ref` |
| TD `rel:type` link, exactly one in the TD | Greater of its explicit `tm:minVersion` and the TD's implicit `version.model` by SemVer precedence; if only one is present, use it; otherwise no floor |
| TD `rel:type` links, several, with `version.model` | Every link MUST have `tm:minVersion`, or resolution fails as `ambiguous-floor`; each link uses the greater of its own floor and `version.model` |
| TD `rel:type` links, several, without `version.model` | Each link uses its own `tm:minVersion` if present; otherwise no floor, without error |

Because R1 puts the major in the identity, an upper bound is never needed.

**R4. Keep the resolved tuple outside the document.** A resolution returns
`(wotid, versionid, contentdigest, origin)`. A caller that needs to reproduce
the selection stores that tuple and supplies a digest or `versionid` pin on a
later request. The document contains no registry identifiers or content
digests, so it remains portable between registries.

## Resolver

```text
resolve(reference, pin?, allowPrerelease = false):
  R := the Resource whose wotid equals the reference target           else FAIL not-found
  if pin.digest:     return the Version of R with that contentdigest  else FAIL pin-mismatch
  if pin.versionid:  return that Version of R                         else FAIL not-found
  floor := reference.tm:minVersion                                 (absent if unset)
  if reference is a TD rel:type link:
      links := all rel:type links in that TD
      model := TD.version.model                                   (absent if unset)
      if model is present and count(links) > 1 and any link lacks tm:minVersion:
          FAIL ambiguous-floor
      validate every explicit link floor                          else FAIL invalid-version
      if model is present:
          validate model as a floor                               else FAIL invalid-version
          floor := greater by SemVer precedence of floor and model (use model if floor absent)
  validate floor if present                                       else FAIL invalid-version
  # Generated 0.0.0-N ids and invalid SemVer are never valid floors.
  if R.defaultversionsticky:
      V := R.default                                   # operator pin is honoured, never bypassed
  else:
      eligible := Versions of R, excluding prereleases
                  unless allowPrerelease or floor is itself a prerelease
      V := highest eligible Version by SemVer precedence    else FAIL unsatisfied
  if floor and V < floor: FAIL unsatisfied (have V, need floor)
  return (R.wotid, V.versionid, V.contentdigest, registry origin)
```

A resolver never selects a Version below the floor or falls back to a lower
one. If the sticky default is below the floor, resolution fails; the resolver
does not select a different Version.

## User flows

| Flow | Result |
|---|---|
| Author publishes TM `1.0.0`, then `1.1.0` | `versionid` `1.0.0`, then `1.1.0`. The default is `1.1.0`. |
| Late patch `1.0.1` after `1.1.0` | SemVer order keeps `1.1.0` the default. |
| TD built from model `1.1.0` | The implicit floor is `1.1.0`, so `1.0.x` can never be chosen. |
| TM extends a parent and needs `≥1.2.0` | `tm:minVersion: "1.2.0"`. Resolution fails if only `1.1.x` exists. |
| Breaking change | New `wotid` `…:v2`. The old Resource is `deprecated` with a successor link. Old references keep resolving. |
| Audit or reproducible build | Store the R4 tuple and resolve with the digest pin. |
| Document copied to another registry | The `wotid` and `version.model` are unchanged, so references resolve there as well. Only `origin` differs. |
| TM without a version | Gets `0.0.0-1`, `0.0.0-2`, …. It is reachable by default only when nothing authored exists or the caller opts in, and it cannot be a floor. |
| Prerelease `1.3.0-rc.1` published | Not selected by default until `1.3.0` exists, unless the caller opts in. |

## Alternatives not taken

| Alternative | Reason |
|---|---|
| Full version in the identifier (`…;1.2`) | Every reference has to be rewritten on every revision, and `wotid` stops being stable. |
| Registry `versionid` in links | Binds the document to one registry's numbering and breaks copying between registries. |
| Version ranges (`^1.2`) | With the major in the identity only a lower bound carries information. |
| Lock file only | Reproducible, but it never records what the author needed, so a mis-composition is not detected. |
| `0.0.N` for generated ids | Collides with authored `0.0.x` releases. |

## Impact on each specification

| Specification | Change |
|---|---|
| W3C WoT (proposal `td-versioned-references`) | Defines `tm:minVersion`, the implicit `rel:type` floor, the multiple-link rule, and the `successor-version` / `latest-version` link relations. |
| xRegistry WoT Registry | `versionmode: semver` and `singleversionroot: true` for Thing Models, the `versionid` = `version.model` rule, `versionorigin`, generated `0.0.0-N`, prerelease eligibility, the resolver, and the resolution test vectors in [tests/resolution](tests/resolution). |
| OPC 10100 WoT Binding | Maps `tm:minVersion` and TD `version.model` to the information model. |
| OPC 10100 WoT Connectivity | `WoTDependencyDataType.RequiredVersion`, the authored version and its origin on `WoTDocumentType`, and the same resolution order. |
| Implementations (xregistry-dotnet, UA-.NETStandard) | Implement the resolver and run the shared vectors byte for byte. |
