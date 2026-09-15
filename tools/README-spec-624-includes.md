# Local model includes

<!-- no verify-specs -->
<!-- words: py pytest -->

The [schema generator](schema-generator.py) expands `$include` and `$includes`
using local JSON files. Local sibling keys win over included keys; earlier
includes win over later ones. Values are replaced as a whole, not merged
recursively. Nested paths and fragment-only pointers use the document that
declared them. The source dictionaries, lists, and files remain unchanged.

References use JSON Pointer fragments, including pointer escapes and percent
encoding. The tool rejects conflicting directives, invalid references, missing
files, non-object targets, cycles, and chains longer than 64 includes. It does
not acquire include documents through URLs or network paths.

Run the focused [regressions](test_schema_generator_includes_624.py) from the
repository root:

```sh
python -B -m pytest tools/test_schema_generator_includes_624.py -q
```

These checks exercise the production include resolver and schema generation,
not a replacement resolver. They do not qualify Core metadata, cross-group
resource imports, scalar codecs, or generated client behavior. The separate
CloudEvents source fragment correction is not part of this change.
