# WoT Registry Samples

<!-- words: WoT thinggroups thingmodelgroups schemagroups messagegroups fabrikam lamp -->

This directory contains illustrative sample documents that exercise the
WoT Registry model defined in [../model.json](../model.json):

- [lamp-tm.xreg.json](lamp-tm.xreg.json) — a minimal `thingmodelgroups`
  document containing a single Thing Model (`Fabrikam.Lamp`) for a generic
  dimmable lamp.
- [lamp-td.xreg.json](lamp-td.xreg.json) — a `thinggroups` document
  containing a Thing Description (`lamp-42`) that conforms to the lamp
  Thing Model above. Its `links[].rel = "type"` entry references the TM
  by registry-relative URL.

For an end-to-end scenario combining `thinggroups`, `thingmodelgroups`,
`schemagroups`, `messagegroups`, and `endpoints`, see
[../../cloudevents/samples/scenarios/smartlamp-wot.xreg.json](../../cloudevents/samples/scenarios/smartlamp-wot.xreg.json).
