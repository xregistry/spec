# HTTP entity identity example checks

<!-- no spellcheck -->
<!-- no verify specs -->

`test_http_identity_597.py` checks the actual examples identified by issue 597:
Message collection IDs, Version collection keys, POST and PUT Version identities,
Schema metadata and document identities, and requested-versus-default wording.
The Primer's closing case rule is compared with Core's existing identity rules.

Complete JSON examples are parsed directly. For abbreviated Message maps, only
the designated omitted-field lines and their introducing commas are removed.
For metadata update blocks with separately tracked wire-syntax defects, only
their actual JSON string identity fields are projected and decoded. The URL
comparison projects the entity path before the representation marker; it does
not validate suffix or trailing-slash syntax. Those representation and literal
serialization repairs remain outside this issue.

Source-derived mutations check non-default Version identity and rejection of
case-folded identity aliases. No server, lookup implementation, full wire parser
or interoperability qualification is provided by these source checks.

Run from the repository root:

```console
python -B -m pytest tools/test_http_identity_597.py -q -p no:cacheprovider
```
