# Committed-event boundary captures

<!-- no verify-specs -->
<!-- words: py pytest powershell -->

[The boundary helper](events_commit_619.py) illustrates the
[Events commitment/publication rules](../../core/events.md#commitment-and-publication)
with separate in-memory captures for committed state, queued notifications, and
consumer delivery. Candidate occurrences are combined by subject and action,
using final interaction state rather than a later read at delivery time.

[The regressions](test_events_commit_619.py) parse existing Registry-update and
implicit-parent examples. They inspect state and notification visibility during
response generation and at enqueue, exercise pre-commit failures, and check
coalescing for implicit creation, cascades, and deprecation. An enqueue failure
in the path without a profile is reported explicitly with committed state preserved;
it is not silently turned into a successful notification.

The explicitly selected atomic recording profile models joint state/event recording
using one capture replacement. A recording failure leaves both unchanged.
Dispatch and consumer delivery remain separate and can fail after commitment.
This illustrative profile is not a normative transport profile, and an in-memory
replacement is not proof of durable storage, crash recovery, atomic database
writes, or broker guarantees.

This is not an HTTP server, a Core validation engine, or a subscription service.
Callers supply valid mutations, occurrence records, interaction context, and
response generation. Cancellation cases model cancellation before commitment;
they do not decide protocol-specific disconnect behavior after commitment.
No live-server, exactly-once, replay, or delivery-order claim is made.

Run from the repository root:

```powershell
python -B -m pytest tools\spec619\test_events_commit_619.py -q
```
