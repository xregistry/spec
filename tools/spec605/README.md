# Cross-reference event contract

<!-- no verify-specs -->
<!-- words: py pytest powershell -->

[The lifecycle helper](events_xref_605.py) illustrates the local-ownership and
projected-epoch rules in [Events](../../core/events.md) using before/after
captures. Local Version ownership is stored separately from already available
target read captures. Projected Versions never become local event subjects;
missing, inaccessible and cross-reference targets yield no projected epochs.
Each available epoch is preserved, including a genuine zero. A retained local
epoch is not a substitute for an unavailable target value.

[The focused regressions](test_events_xref_605.py) parse the actual dangling
alias request and event list, then exercise normal-to-alias conversion,
alias-to-normal conversion, changing targets, deletion, cascades, target-only updates,
unchanged state, and invalid captures. Comparison of the owned state before and
after the interaction checks event subjects independently of projected data.

This is a bounded offline contract, not a server or a complete Core write
processor. The caller supplies validated local state and authorized target read
captures; the helper does not resolve references, acquire targets, perform
authorization, or choose default Versions. It checks Resource and Version
lifecycle selection, not complete changed-attribute lists, intermediate actions,
commit timing, durable enqueue, subscriptions, or transport delivery. It does not
establish live-server conformance.

Run from the repository root:

```powershell
python -B -m pytest tools\spec605\test_events_xref_605.py -q
```
