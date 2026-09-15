# Schema selector profile checks

<!-- words: pytest pwsh noprofile namespace powershell -->

[This directory](.) contains the bounded reference helpers and regressions for
[Schema Object Selection](../../schema/spec.md#436-schema-object-selection).

```console
python -B -m pytest tools/schema_selectors_651 -q
pwsh -NoProfile -File tools/schema_selectors_651/test_xpath_profile_651.ps1
```

The helpers separate a document locator from its selector, retain encoded
literal identifiers, and reject multiple candidate boundaries. Local and
external xRegistry document references require caller-supplied owner context;
the helpers do not discover entities, resolve a default Version or fetch
documents. A caller supplies an explicit owner when a Resource/Version prefix
would otherwise admit multiple interpretations. Relative document URIs remain
relative; the helper does not assign a base URI or invent an inline schema URI.

JSON Pointer checks preserve native JSON kinds and enforce concrete array
indices, not append positions. JSON Schema validation and anchor lookup use
the installed libraries for the three advertised dialects. Avro declaration
indexes come from the installed native parser, including nested names and
recursive types; selected roots are exercised with its binary codec.

The PowerShell checks parse the actual XML example, compile it with the native
XSD 1.0 processor and evaluate its selector with a native XPath 1.0 engine.
They cover namespace context, distinct declarations, zero and multiple roots,
wrong result kinds and unavailable functions. The script demonstrates that
XSD 1.1 validation is not supplied by that runtime. The portable Python XML
check uses only its documented path subset, not a full XPath engine.

The portable suite does not depend on a Protobuf compiler or JSON Structure
validation library. Protobuf tests consume a message-only declaration index,
not a parsed source file. JSON Structure tests consume explicit type indexes
and check concrete JSON Structure root values, including a designated union.
Those indexes are inputs from schema processing, not substitutes for native
schema validation; the helpers do not prove an arbitrary document valid or
implement every language feature. A missing facility is not evidence that the
native format forbids it. These offline checks are not claims of live server,
complete format, automatic acquisition or cross-format semantic conformance.
