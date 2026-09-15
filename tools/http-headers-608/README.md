# Native HTTP header examples

<!-- no verify-specs -->
<!-- words: aspnet multipart py pytest roundtrip -->

[Reference helper](native_headers_608.py) and
[regressions](test_native_headers_608.py) accompany
[the HTTP binding](../../core/http.md#http-header-values).

Run from the repository root:

```console
python -B -m pytest tools/http-headers-608 -q
```

The tests parse actual specification examples with the standard library HTTP
policy, parse a multipart body with a spaced boundary, and check exact URI and
metadata bytes. They cover native parameter quoting, literal percent signs,
Core Resource IDs, private decoding order, invalid UTF-8, malformed escapes
and HTTP control-byte rejection.

The helper models the native/private serialization boundary, not a complete
HTTP implementation. Native examples accept ASCII values with HTTP horizontal
tab whitespace and reject other control bytes; callers still need each native
field's grammar validation. This does not define a broader native character
restriction. Resource ID admission follows the existing Core grammar. Encoded
control characters in private metadata are data, never raw wire controls.

These are source and reference-parser regressions, not live ASP.NET, proxy,
browser download or peer interoperability tests. Filenames are advisory, not
safe filesystem paths; applications still need the precautions in
[RFC6266 section4.3](https://www.rfc-editor.org/rfc/rfc6266#section-4.3).
