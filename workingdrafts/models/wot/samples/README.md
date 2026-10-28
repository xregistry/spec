# WoT Registry Samples

<!-- words: WoT thingdescriptiongroups thingmodelgroups fabrikam wotid derivedfrom byom contoso standardsbody maturity affordance minversion versionorigin -->
<!-- words: factoryfloor inletpressure -->

[registry.json](registry.json) combines the lamp and vendor-model scenarios
in one document using the [WoT Registry model](../model.json).

| Group | Content |
| --- | --- |
| `Fabrikam.Lighting` | A complete dimmable lamp Thing Model. Its authored `urn:fabrikam:lamp:v1` appears in `wotid`; its client-chosen Resource id is `urn.fabrikam.lamp.v1`. |
| `Fabrikam.FactoryFloor.01` | Lamp #42, a Thing Description with an absolute `rel: "type"` link to the lamp model and its authored identifier in `derivedfrom`. |
| `Contoso.Pumps` | Vendor-supplied pump and device Thing Models, including two compatible pump Versions. |

A Consumer holding an authored identifier finds the Resource by querying
`wotid`. The combined document includes both the lamp model and the Thing
Description that conforms to it. It uses the full lamp documents rather than
a second, shortened representation of the same identities.

Contoso stores its models as authored. Their `id` members and the pump's
`tm:extends` link remain unchanged. Both models have `"maturity": "Vendor"`
and omit `standardsbody`: Contoso publishes them, while `standardsbody`
records an organization that defines or endorses a document, not its author.

The pump defaults to `1.1.0`. Its explicit `versions` collection also retains
`1.0.0`, with maturity and other metadata on each Version. The device has
one implicit Version and keeps those attributes on the Resource. The
OPTIONAL `inletPressure` affordance first appears in pump revision `1.1.0`;
that revision adds no mandatory member.

Each TM's `versionid` matches its document's SemVer `version.model`, and its
identifier includes the major version. The lamp TD's `versionid` instead
matches `version.instance`. The pump's `tm:minVersion: "1.0.0"` requires a
device-model revision at or above 1.0.0. This is a proposed WoT extension,
not a member defined by the published WoT 1.1 Recommendation.

The publication requests omit `versionorigin` because the model initializes
it to `authored`. The registry remains responsible for assignment.

[publication-closure.json](publication-closure.json) is a separate example
of the [proposed closure envelope](../publication-design.md), not Registry
content or a complete snapshot. Its checks validate shape only.
