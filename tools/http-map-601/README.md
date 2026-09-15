# Metadata map field-name examples

<!-- no verify-specs -->
<!-- words: py pytest roundtrip -->

[Reference codec](map_headers_601.py) and
[regressions](test_map_headers_601.py) accompany
[the HTTP field-name rules](../../core/http.md#http-header-names).

Run from the repository root:

```console
python -B -m pytest tools/http-map-601 -q
```

The examples use percent-encoded UTF-8 bytes in field-name components, not the
field-value codec. Uppercase logical characters and literal percent signs are
escaped. The attribute component also escapes its dots; literal dots after
the first separator belong to the key. This preserves identity even when an
HTTP stack changes all field-name letter casing.

Tests check exact field-name bytes, native HTTP parsing, decoded-key duplicates,
malformed escapes and UTF-8, raw control bytes, Unicode normalization differences,
Core length boundaries and a deterministic collision/roundtrip matrix. The
header table in the actual specification is parsed as JSON key strings and
checked against the codec. Values remain opaque here; their existing codec
and update semantics are separate.

The default admission function enforces existing Core attribute and map-key
rules. An explicit test admission function represents an applicable model or
extension that admits additional characters; the codec itself does not grant
that permission. It is not a model evaluator or a registry server.

Duplicate detection requires separate field occurrences, as exposed by the
standard library HTTP parser. Frameworks or proxies that irreversibly combine
duplicate fields need a different input path or JSON metadata; splitting on
commas cannot reconstruct the original occurrences. HTTP transport size limits
remain implementation-specific, and names are never truncated.

These are source, parser and abstract codec checks, not live ASP.NET, HTTP/2,
HTTP/3, proxy or peer interoperability tests. No dependency, native-field value
grammar, header-null policy or Core name admission is changed.
