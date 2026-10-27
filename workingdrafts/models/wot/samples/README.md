# WoT Registry Samples

<!-- words: WoT thingdescriptiongroups thingmodelgroups schemagroups messagegroups fabrikam lamp smartlamp -->
<!-- words: wotid derivedfrom byom contoso standardsbody maturity -->
<!-- words: affordance inletpressure minversion versionorigin -->

These samples exercise the WoT Registry model in
[../model.json](../model.json):

- [lamp-tm.xreg.json](lamp-tm.xreg.json): a minimal `thingmodelgroups`
  document with one Thing Model for a generic dimmable lamp. The document's
  authored identifier `urn:fabrikam:lamp:v1` appears in `wotid`; the client
  chose `urn.fabrikam.lamp.v1` as the Resource id. A Consumer holding the
  authored identifier finds the Resource by querying `wotid`.
- [lamp-td.xreg.json](lamp-td.xreg.json): a `thingdescriptiongroups` document
  with a Thing Description. The Thing Description has the identifier
  `urn:fabrikam:lamp:42`. It conforms to the lamp Thing Model above. Its
  `links[].rel = "type"` entry references the TM by absolute document-view
  URL. The `derivedfrom` attribute records the TM's authored `wotid`.
- [byom-pump-tm.xreg.json](byom-pump-tm.xreg.json): a bring-your-own-model
  example with two vendor-supplied Thing Models. Contoso stores both as
  authored. Their `id` members and the pump's `tm:extends` link remain
  unchanged. The pump carries its authored identifier in `wotid` and the
  device identifier in `derivedfrom`; the device carries its own wotid.

  Both Thing Models have `"maturity": "Vendor"` and omit `standardsbody`.
  Contoso publishes them. The `standardsbody` attribute records the
  organization that defines or endorses a document, not its author.

  The pump's default Version is `1.1.0`, the latest. A Consumer can retrieve
  it from the Resource or request `.../versions/1.0.0` for the earlier
  Version. Its explicit `versions` collection stores attributes such as maturity
  on each Version; a Consumer can use maturity to prefer an official model.
  The device has one implicit Version, so its attributes appear on the
  Resource. A Resource needs an explicit `versions` collection only when it
  has multiple Versions. The pump has multiple Versions and uses that
  collection.

- [smartlamp-wot.xreg.json](smartlamp-wot.xreg.json): a scenario that combines
  a Thing Model and a Thing Description that conforms to it in one registry
  document. The document uses `thingmodelgroups` and
  `thingdescriptiongroups`; the Thing Description carries `derivedfrom` and a
  `links[].rel = "type"` reference to the Thing Model Resource.

Each Thing Model's `versionid` matches the document's SemVer `version.model`,
and its identifier includes the major version. The pump's `tm:extends` links
set `tm:minVersion: "1.0.0"`, so a resolver requires a device-model revision
at or above 1.0.0. This member comes from a proposed extension to the W3C
WoT Thing Description; the published WoT 1.1 Recommendation does not define it.

The publication requests omit `versionorigin` because the registry sets its
default to `authored`. The optional `inletPressure` affordance first appears
in revision `1.1.0`, which adds no mandatory member.
