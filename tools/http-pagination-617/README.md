# Pagination link and count examples

<!-- no verify-specs -->
<!-- words: py pytest -->

[Reference policy and parser](pagination_links_617.py) and
[regressions](test_pagination_links_617.py) accompany
[the pagination specification](../../pagination/spec.md).

Run from the repository root:

```console
python -B -m pytest tools/http-pagination-617 -q
```

Tests parse complete HTTP examples directly from the specification, including
exact two-byte JSON bodies. They check empty, one-page and terminal responses,
independently offered previous/first/last links, mandatory next links, absent
count carriers, zero and maximum counts, consistency across omission gaps,
opaque continuation targets and quoted/native Link parameters.

The helper emits only existing Link fields; no count header or synthetic link
is created to carry a known count. Its server-side boundary facts are supplied
explicitly, not inferred from count or response size. Its reader carries known
count information across omissions without turning an unknown count into zero.

The Link parser covers repeated and combined fields, quoted/token parameters
and the four pagination relations used here. It follows
[RFC8288](https://www.rfc-editor.org/rfc/rfc8288#section-3) for these examples,
including using the first repeated relation parameter. It is not a complete
URI validator or general Web Linking implementation: additional relation
profiles and anchored links need explicit support, and URI resolution remains
the HTTP client's job. ASCII and HTTP control-byte checks apply to its example
input. It does not parse or correct the independent expiration-date example.

These are source, standard-library HTTP parser and abstract policy checks, not
live ASP.NET, backend pagination, snapshot storage or peer interoperability.
