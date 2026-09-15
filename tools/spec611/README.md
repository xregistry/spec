# Primer deprecation examples

<!-- no verify-specs -->
<!-- words: py pytest powershell -->

[The regressions](../test_primer_deprecation_611.py) parse the two actual
deprecation excerpts in the [Primer](../../core/primer.md#1125-deprecation-of-entities-in-an-xregistry)
and compare their attribute locations with current Core semantics. The event
actions are checked against the existing [Events](../../core/events.md) matrix,
not a new Version-deprecation event or an Endpoint-specific extension.

The bounded metadata captures exercise an empty object, a future effective
time, metadata edits and removal. They distinguish the notification at mutation
time from the deprecation state observed before, at and after the effective
time. Nested Resources and Versions are retained unchanged; no propagation
policy is introduced. Invalid metadata leaves both state and notifications
unchanged.

These are offline, second-precision fixture checks, not a full timestamp
implementation, an HTTP server, a complete model validator, or live delivery
evidence. They model explicit changes to built-in deprecation metadata, not
every no-op write or a custom Version-level extension.

Run from the repository root:

```powershell
python -B -m pytest tools\test_primer_deprecation_611.py -q
pytest tools\test_primer_deprecation_611.py -q
```
