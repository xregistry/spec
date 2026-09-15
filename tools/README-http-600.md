# Version deletion route example checks

<!-- no spellcheck -->
<!-- no verify specs -->

`test_http_delete_routes_600.py` reads the actual Resource, Versions collection
and single-Version DELETE sketches and exchanges in `core/http.md`. It compares
the collection sketch with its heading and concrete example, and the guarded
single-Version route with its unguarded counterpart and entity label.

The positional route checker keeps Resource ID `versions` distinct from a
Versions collection and from a Version. Source-derived substitutions show that
missing Resource or Version segments are not inferred, even with an epoch
query. The existing collection body is parsed as JSON to associate each guard
with its Version map key.

These are static route/identity checks, not an HTTP router or server test.
They neither send DELETE requests nor qualify concurrency, persistence or
interoperability. Resource collection Meta-epoch repairs are a separate issue.

Run from the repository root:

```console
python -B -m pytest tools/test_http_delete_routes_600.py -q -p no:cacheprovider
```
