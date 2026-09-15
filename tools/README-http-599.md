# Resource collection deletion example checks

<!-- no spellcheck -->
<!-- no verify specs -->

`test_http_resource_delete_599.py` parses the actual HTTP deletion request and
compares the HTTP sketch with the existing Core Resource deletion sketch.
Only the sketch's declared key/integer placeholders and optional/repetition
markers are instantiated; concrete request JSON is parsed without repairs.

The issue's unequal-epoch counterexample (Meta 5, default Version 9) drives a
small, read-only guard/target checker. Mutations of the actual request check
top-level-only guards, both planes, missing/null Meta guards, nonexistent IDs,
empty maps versus absent bodies, and rejection without a partial result or
snapshot mutation. The Primer terminology is checked against Core's unchanged
deletion and epoch rules.

This is a bounded example-contract checker, not a server or full request
validator. It neither performs deletion nor tests transactional persistence,
HTTP error encoding, default selection, access control, or interoperability.
In particular, its no-mutation check is not evidence of server atomicity.

Run from the repository root:

```console
python -B -m pytest tools/test_http_resource_delete_599.py -q -p no:cacheprovider
```
