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
WoT document (`tm:extends`, `tm:submodel`, `tm:ref`, a TD `rel:type` link,
or TD-to-TD `td:extends`, `td:subthing`, or `td:ref`) names only the target's
identifier and no version. That
leaves three questions open:

1. When a document is published, which `versionid` does it get?
2. When a reference is followed, which Version does it resolve to?
3. How does a consumer reproduce the exact bytes it resolved last time?

Without answers, a late patch release (`1.0.1` published after `1.1.0`) can
become the default Version, and a Thing Description that was built from model
`1.1.0` silently resolves to `1.0.1`.

## Design

Four rules, R1–R4.

**R1. The TM major version is part of the identity.** A breaking TM change
uses a new `wotid`, for example `urn:example:pump:v2`. The previous Resource
is marked `deprecated` and names its successor. Every Version of one TM
`wotid` is backward compatible with earlier Versions under it, and
`compatibility` defaults to `backward` for Thing Models. A TD `id` names a
concrete Thing; its major instance revision remains under that `id`.

**R2. The Version id follows the document version.** Thing Models use
`versionmode: semver` and `singleversionroot: true`; their `versionid` equals
SemVer `version.model`. Thing Descriptions use the same resource settings;
their `versionid` equals SemVer `version.instance`. Build metadata is rejected
because Core `versionid` cannot carry `+`, and a supplied mismatch is
`version-mismatch`.

If the relevant document version is absent or is not SemVer, the registry
assigns the lowest unused `0.0.0-N`. `versionorigin` is `authored` when the id
comes from `version.model` or `version.instance`, and `generated` otherwise.
Generated ids are prereleases and MUST NOT be used as floors. For a TD,
`version.model` remains an implicit floor only for its `rel:type` TM link.

**R3. A reference carries a floor, not range syntax.** A reference MAY state the
minimum Version it needs:

| Reference | Floor |
|---|---|
| `tm:extends`, `tm:submodel` link | `tm:minVersion` member on the link |
| `tm:ref` | `tm:minVersion` member beside `tm:ref` |
| `td:extends`, `td:subthing` | `td:minVersion` member on the link; target range ends before the next major |
| `td:ref` | `td:minVersion` member beside `td:ref`; target range ends before the next major |
| TD `rel:type` link, exactly one in the TD | Greater of its explicit `tm:minVersion` and the TD's implicit `version.model` by SemVer precedence; if only one is present, use it; otherwise no floor |
| TD `rel:type` links, several, with `version.model` | Every link MUST have `tm:minVersion`, or resolution fails as `ambiguous-floor`; each link uses the greater of its own floor and `version.model` |
| TD `rel:type` links, several, without `version.model` | Each link uses its own `tm:minVersion` if present; otherwise no floor, without error |

TM floors have no upper bound because their major is part of `wotid`. A TD
floor is a caret floor: `X.Y.Z` selects versions from `X.Y.Z` up to but not
including `(X+1).0.0`. A TD `id` names a concrete Thing, so a breaking major
revision remains under that id. An unfloored TD-to-TD reference can cross
majors; `td:minVersion` on `td:extends`, `td:subthing`, or beside `td:ref`
selects within the target major. There is no implicit floor for TD targets.

**R4. Keep the resolved tuple outside the document.** A resolution returns
`(wotid, versionid, contentdigest, origin)`. A caller that needs to reproduce
the selection stores that tuple and supplies a digest or `versionid` pin on a
later request. The document contains no registry identifiers or content
digests, so it remains portable between registries.

## Resolver

```text
resolve(reference, pin?, allowPrerelease = false):
  R := the Resource whose wotid equals the reference target      else FAIL not-found
  if pin.digest:     return the Version of R with that digest    else FAIL pin-mismatch
  if pin.versionid:  return that Version of R                    else FAIL not-found
  kind := TM or TD from the reference operator
  floor := reference.tm:minVersion or reference.td:minVersion   (absent if unset)
  if reference is a TD rel:type link:
      derive the existing implicit floor from TD.version.model
      apply the multiple-link ambiguous-floor rule
  validate floor syntax and reject generated 0.0.0-N floors      else FAIL invalid-version
  reject a floor term for the other target kind                  else FAIL invalid-floor
  if R.defaultversionsticky:
      V := R.default
      if floor and V < floor: FAIL unsatisfied
      if kind is TD and floor and V.major >= floor.major + 1: FAIL unsatisfied
  else:
      eligible := Versions in the target-kind floor range,
                  excluding prereleases unless opted in or floor is prerelease
      V := highest eligible Version by SemVer precedence         else FAIL unsatisfied
  return (R.wotid, V.versionid, V.contentdigest, registry origin)
```

For a TD target with floor `X.Y.Z`, the eligible range ends before
`(X+1).0.0` and excludes prereleases of that next major. With no floor, TD
selection MAY cross majors. A resolver never selects below a floor or outside
a TD caret range. If a sticky default is out of range, including in a higher
TD major, resolution fails as `unsatisfied`; it does not select a different
Version.

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
| W3C WoT (proposal `td-versioned-references`) | Defines TM and TD floors, TD instance identity, implicit `rel:type` floors, and version navigation. |
| xRegistry WoT Registry | SemVer identities for TMs and TDs, `versionorigin`, generated `0.0.0-N`, TM floors, TD caret floors, prerelease eligibility, the resolver, and shared vectors in [tests/resolution](tests/resolution). |
| OPC 10100 WoT Binding | Maps `tm:minVersion`, `td:minVersion`, and TD `version.model` to the information model. |
| OPC 10100 WoT Connectivity | `WoTDependencyDataType.RequiredVersion`, the authored version and its origin on `WoTDocumentType`, and the same resolution order. |
| Implementations (xregistry-dotnet, UA-.NETStandard) | Implement the resolver and run the shared vectors byte for byte. |
