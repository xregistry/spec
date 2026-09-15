# Primer default and pruning example

<!-- no verify-specs -->
<!-- words: py pytest powershell -->

[The regressions](../test_primer_defaults_612.py) parse every row and both
Meta PATCH bodies in the [Primer example](../../core/primer.md#118-default-version-and-maximum-versions).
The state capture applies the actions and compares the resulting Version set,
default selection, sticky state, model limit, and rejection outcome with the
actual table. The rejected model update is also compared with its complete
before-state, not just a list of expected IDs.

Additional cases check the all-Resources admission barrier, retained sticky
defaults, explicit clearing of stickiness without Version changes, chronological
rather than ID ordering, and read-only default reporting. The model
customization is parsed and compared with Core's existing Meta attribute
definition; forbidden sticky requests and invalid model/selection input cannot
silently mutate state.

This is a bounded offline capture for normal, locally owned Resources with
distinct second-precision creation times. The example explicitly selects
created-time ordering, client-selected IDs, configurable stickiness, and no
optional pruning while the model limit is zero. It is not a complete Core
write/ancestry engine or timestamp comparator, and does not implement the
separate manual-pruning or discarded-ID proposals. It makes no live-server,
retention, durability or event-delivery claim. Combined non-sticky ID requests
are explicitly outside this capture rather than selecting a policy for them.

Run from the repository root:

```powershell
python -B -m pytest tools\test_primer_defaults_612.py -q
pytest tools\test_primer_defaults_612.py -q
```
