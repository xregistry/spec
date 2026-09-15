# Native schema root checks

<!-- words: pytest -->

[The tests in this directory](.) exercise the document examples in
the [Schema specification](../../schema/spec.md#43-schema-formats).

Run the focused checks with:

```console
python -B -m pytest tools/schema_roots_653 -q
```

The checks use the existing JSON Schema validation library for the three
documented versions, and the installed Apache Avro parser and binary reader and
writer.
They cover native JSON value kinds, document media types and bytes, boolean
subschemas, all Avro root categories, union branches, named declarations and
invalid roots. A primitive Avro schema's JSON quotation marks are document
bytes, not a request to store plain text.

These are offline document and native library checks, not evidence that a
Registry implements every format, dialect, semantic feature or compatibility
operation. The Avro library exercises its installed version; these checks do
not claim execution against every Avro release. Selection checks use JSON
Pointer and the native schema root; they are not a general reference resolver
and do not fetch, publish or rewrite any schema. Other schema families and
their selectors are unchanged by this root clarification.
