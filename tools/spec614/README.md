# Event HTTP example captures

<!-- no verify-specs -->
<!-- words: py pytest powershell -->

[The focused regressions](../test_events_exchange_614.py) parse the actual model,
all three Resource/Version metadata PATCH examples, and the complete Group
exchange in [Events](../../core/events.md). JSON parsing rejects duplicate keys
using the existing sample-validation helper.
The test is beside that helper so both the module and console forms of the
test runner work without depending on the working directory being an import
package.

The narrow state captures exercise metadata updates under the declared model,
compare event subjects and epochs with the affected default or other Version,
and verify that raw-document PATCH rejection leaves state and events unchanged.
They also retain the legal metadata-only `$details` variant and its canonical
response URL, rather than introducing a new rejection rule.

The Group capture constructs creation state from the actual request and model.
It checks the response body, creation status and Location, identity, timestamp,
correlation, and event data against that state. A subsequent write checks that
an existing Group still returns 200 without Location.

These are bounded offline examples, not an HTTP server, complete model
validator, wire-framing implementation, or transport. They do not prove event
delivery, allocate IDs, or change protocol policy. Other event-name and
commit-publication proposals remain outside this correction.

Run from the repository root:

```powershell
python -B -m pytest tools\test_events_exchange_614.py -q
pytest tools\test_events_exchange_614.py -q
```
