# Specification tooling notes

<!-- no verify-specs -->
<!-- words: py pytest powershell -->

## Timestamp-ordering contract

The [timestamp-ordering contract](timestamp_ordering_contract.py) illustrates
[timestamp comparisons](../core/spec.md#filter-flag) and the comparison keys
used for [sorting](../core/spec.md#sort-flag).

It normalizes numeric UTC offsets with integer calendar arithmetic and keeps
fractional seconds as digit strings. Removing trailing zeroes makes equivalent
fractions equal without floating-point conversion, rounding, or a fixed
precision limit. These are equality and ordering keys, not elapsed durations.

Positive leap seconds use a separate ordering marker between the preceding
ordinary second and the following second. Callers supply established positive
leap dates in UTC; the helper rejects a positive leap second without that
information. The examples use the 1990 leap second from
[RFC3339 Section 5.8](https://www.rfc-editor.org/rfc/rfc3339.html#section-5.8),
including its equivalent numeric-offset form.

This is an abstract comparator, not a server, complete filter or pagination
implementation, or an authority on leap announcements. Callers remain
responsible for complete RFC3339 validation, including any negative leap
dates, and the surrounding null, existence, wildcard, and model semantics.

Run the focused examples from the repository root:

```powershell
python -m pytest tools\test_timestamp_ordering_policy.py -q
```
