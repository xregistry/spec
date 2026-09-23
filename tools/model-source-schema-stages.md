# Model source schema: what each validation stage actually proves

<!-- words: expandedmodel modelsource namecharset py siblingattributes -->
<!-- words: typemap ximportresources ifvalues rfc -->

`core/model.schema.json` describes the **`modelsource`** document - the model
exactly as an author writes it - and `tools/validate-models.py` reports which
stage produced each result. Neither stage is a conformance statement about a
completed xRegistry model.

## Source structure

The root schema validates the document as written:

- `$include` and `$includes` are accepted in any model Object or Map, including
  the Registry root, the `groups` and `resources` maps, Group and Resource
  definitions, every attribute map and attribute definition, nested `item`
  definitions, `ifvalues` maps, their branches and `siblingattributes`,
  `labels`, `typemap`, and the Group `constraints` map and its entries. The two
  directives are typed and mutually exclusive at any one level, and an
  include-only Group or Resource definition needs no local `singular`.
- A definition MAY omit `type`, because the type can arrive from an include or
  from the specification-defined attribute it overlays. For example,
  `{"attributes": {"name": {"required": true}}}` is a legal source overlay.
- Attribute names use the strict character set, lowercase letters, digits and
  underscore, not starting with a digit, unless the owning `object` or `item`
  declares `namecharset: extended`, which selects the map key character set
  described in `core/spec.md`. The owning object's
  character set also applies to the top-level `siblingattributes` of its
  attributes' `ifvalues`; it does not change a nested object's own character
  set.
- Group plural, Resource singular and Resource plural names - as map keys and as
  explicit fields - are limited to 57 characters. Group singular follows the
  current `core/model.md` text of 63 characters.
- `namecharset`, `versionmode` and `typemap` values are matched
  case-insensitively. Type names, attribute names and `enum` members are not.

## Expanded structure

`#/definitions/ExpandedModel` validates the same document after
`tools/schema-generator.py::resolve_imports` - the real resolver, with its
existing local-file-only, cycle, depth, precedence and non-mutation behavior -
has resolved the directives. At that stage no directive MAY remain and every
attribute, wildcard and item definition MUST carry a `type`.

Admission at the source stage therefore does not imply that a definition is
complete, and admission at the expanded stage does not imply that the model is
semantically valid.

## Not checked here

`tools/validate-models.py` explicitly reports that it does not perform semantic
conformance: overlaying the specification-defined attributes, rejecting an
incompatible Core `type`/`required`/`readonly` change or an unknown untyped
extension, key/`name` identity, `target` and `ximportresources` type existence
and depth, case-duplicate `ifvalues` selector keys, and cross-entity graph rules
all require a real xRegistry implementation. The grammar for `target` checks the
shape of the type-name components only.

## Recorded dependencies

- **Group singular of 61 characters** is proposed in xregistry/spec#677 and is
  not adopted here; the schema keeps the 63 characters that `core/model.md`
  currently states.
- **`cloudevents/model.json`** still uses three `#groups` include fragments that
  are not RFC 6901 JSON Pointers, so its expanded stage cannot pass. Repairing
  those fragments is tracked separately as a model-consistency correction.
- **Scalar-only `enum` applicability** is enforced wherever the declared type
  is known. Endpoint now uses `usage.item.enum` following
  [xregistry/spec#732](https://github.com/xregistry/spec/pull/732), so there is
  no array-level compatibility exception. Includes can still supply an omitted
  source type; the expanded stage resolves it before applying the same rule.
