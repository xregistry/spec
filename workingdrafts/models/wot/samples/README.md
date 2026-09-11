# WoT Registry Samples

<!-- words: WoT thingdescriptiongroups thingmodelgroups schemagroups messagegroups fabrikam lamp smartlamp -->
<!-- words: wotid derivedfrom byom contoso -->

This directory contains illustrative sample documents that exercise the
WoT Registry model defined in [../model.json](../model.json):

- [lamp-tm.xreg.json](lamp-tm.xreg.json) — a minimal `thingmodelgroups`
  document containing a single Thing Model for a generic dimmable lamp. Its
  authored identifier `urn:fabrikam:lamp` is carried in `wotid`, and the
  Resource id `urn.fabrikam.lamp` is the symbolic identifier constructed from
  it.
- [lamp-td.xreg.json](lamp-td.xreg.json) — a `thingdescriptiongroups` document
  containing a Thing Description (`urn:fabrikam:lamp:42`) that conforms to the
  lamp Thing Model above. Its `links[].rel = "type"` entry references the TM
  by registry-relative URL, and its `derivedfrom` attribute records the TM's
  authored `wotid`.
- [byom-pump-tm.xreg.json](byom-pump-tm.xreg.json) — a bring-your-own-model
  example. Two vendor-supplied Thing Models are stored exactly as authored:
  their `id` members and the `tm:extends` reference between them are
  untouched, and all registry-side identity lives outside the documents in
  `wotid` and `derivedfrom`. The pump has two Versions, with `2` as the
  default, so retrieving the Resource yields the latest while
  `.../versions/1` yields the earlier one. Because the pump supplies an
  explicit `versions` collection, its attributes — including the provenance
  attributes an agent uses to prefer an official model — are carried on each
  Version rather than on the Resource; the device, which has a single
  implicit Version, carries them on the Resource directly.

- [smartlamp-wot.xreg.json](smartlamp-wot.xreg.json) — an end-to-end scenario
  combining a Thing Model and a Thing Description that conforms to it in a
  single registry document, showing how `thingmodelgroups` and
  `thingdescriptiongroups` compose: the instance carries `derivedfrom` and a
  `links[].rel = "type"` reference to the Thing Model Resource.
