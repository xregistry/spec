# HTTP capability example checks

<!-- no spellcheck -->
<!-- no verify specs -->

`test_http_available_602.py` parses the three actual capability examples in
`core/http.md` and the default and example maps in `core/spec.md`. It checks
native object and boolean kinds, metadata names, required entries, immutable
model metadata, offered boolean possibilities, and the single-field PATCH
without changing the separate `mutable` capability.

Run from the repository root:

```console
python -B -m pytest tools/test_http_available_602.py -q -p no:cacheprovider
```

These are source-example regression checks, not an HTTP server, a capability
negotiation implementation, or interoperability qualification.
