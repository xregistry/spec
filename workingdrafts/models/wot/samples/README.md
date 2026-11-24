# WoT Registry Samples

<!-- words: WoT thingdescriptiongroups thingmodelgroups fabrikam wotid derivedfrom byom contoso standardsbody maturity affordance minversion versionorigin -->
<!-- words: factoryfloor inletpressure py -->
<!-- words: cloudevents descriptorid describedby thingdescription thingdescriptions affordances standalone affordanceselector -->

[registry.json](registry.json) illustrates document identity, compatible
Versions and provenance metadata using the [WoT Registry model](../model.json).
It contains the following lamp and vendor-model examples:

| Group | Content |
| --- | --- |
| `Fabrikam.Lighting` | A complete dimmable lamp Thing Model. Its authored `urn:fabrikam:lamp:v1` appears in `wotid`; its client-chosen Resource id is `urn.fabrikam.lamp.v1`. |
| `Fabrikam.FactoryFloor.01` | Lamp #42, a Thing Description with an absolute `rel: "type"` link to the lamp model. The TD's `derivedfrom` records the model's `wotid`. |
| `Contoso.Pumps` | Vendor-supplied pump and device Thing Models, including two compatible pump Versions. |

The Registry contains both the complete lamp model and its conforming Thing
Description. A Consumer holding either document's authored identifier queries
`wotid` to find the Resource.

Contoso stores its models as authored. Their `id` members and the pump's
`tm:extends` link remain unchanged. Both models have `"maturity": "Vendor"`
and omit `standardsbody`: Contoso publishes them, while `standardsbody`
records an organization that defines or endorses a document, not its author.

The pump defaults to `1.1.0` and retains `1.0.0` in its explicit `versions`
collection. Maturity and other metadata appear on each Version. The device has
one implicit Version, so those attributes appear on the Resource. Pump revision
`1.1.0` adds the OPTIONAL `inletPressure` affordance and no mandatory member.

Each TM's `versionid` matches its document's SemVer `version.model`, and its
`wotid` includes the major version. The lamp TD's `versionid` instead
matches `version.instance`. The pump's `tm:minVersion: "1.0.0"` requires a
device-model revision at or above 1.0.0. This is a proposed WoT extension,
not a member defined by the published WoT 1.1 Recommendation.

The [registry sample](registry.json) illustrates document and Version
metadata, not a series of write requests. Clients can omit `versionorigin`
from a write: the Registry assigns it under the
[versioning rules](../spec.md#13-versioning).

[publication-closure.json](publication-closure.json) separately illustrates the
[proposed closure envelope](../../../publication/design/design.md#selection-and-acceptance).
It is neither Registry content nor a complete snapshot.
[Checking the sample against the closure schema](../tests/test_wot_examples.py)
establishes its shape, not snapshot coverage or correct target selection.

[cloudevents.json](cloudevents.json) contains two standalone CloudEvents as
sample data, not a transport batch. Using the
[proposed WoT profile](../spec.md#531-cloudevents-wot-source-resolution),
they identify the same lamp TD Version and optionally an event affordance.
The first event's `source` is absolute and the second event's `source` is
relative. The profile does not prescribe a URI scheme. Their `subject` values
label the Thing for filtering, not document selection. Each event's
`describedby` URL selects the exact Version of `lamp-42-temperature` or
`lamp-42`, respectively. The Descriptor examples omit other Core metadata:

```json
[
  {
    "descriptorid": "lamp-42-temperature",
    "versionid": "1",
    "entries": {
      "lamp42": {
        "class": "thingdescription",
        "url": "https://registry.example/thingdescriptiongroups/Fabrikam.FactoryFloor.01/thingdescriptions/urn.fabrikam.lamp.42/versions/1.0.0",
        "affordanceselector": "/events/overheated"
      }
    }
  },
  {
    "descriptorid": "lamp-42",
    "versionid": "1",
    "entries": {
      "lamp42": {
        "class": "thingdescription",
        "url": "https://registry.example/thingdescriptiongroups/Fabrikam.FactoryFloor.01/thingdescriptions/urn.fabrikam.lamp.42/versions/1.0.0"
      }
    }
  }
]
```

Each entry's `url` identifies the lamp TD Version's document. The first
Descriptor's plain JSON Pointer selects `/events/overheated`; the second
omits the selector for the whole Thing. The sample TD declares that event
affordance directly.

Both events use `com.fabrikam.lamp.overheated.v1` as their `type`. Their payload contract
defines a numeric `temperature` member; the different values and TD selection
do not change that contract. The example's naming convention uses the final
`v1` for the payload contract revision, independently of the TD's
`version.instance` or Registry `versionid`. Under that convention, adding a
payload member, even one whose presence is not mandatory, would use a new
contract revision.

The samples do not claim that the proposed closure envelope can reconstruct
a composed TD or that an event version proves content integrity.
