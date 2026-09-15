# Envelope binding context checks

<!-- words: pytest py cacheprovider SDK -->

`envelope_binding_641.py` checks only envelope obligations on an already
available, effective Message definition. `test_envelope_binding_641.py`
parses the actual unbound Group example in the
[Message specification](../../message/spec.md) and the embedded Message in
the [Endpoint specification](../../endpoint/spec.md), then exercises bound and
unbound Groups/Endpoints, borrowed definitions, effective inherited selectors,
missing/conflicting selectors, and the existing metadata obligation.

```shell
python -B -m pytest tools/issue641 -q -p no:cacheprovider
```

The checker does not resolve references, merge bases, fetch remote resources,
or validate the complete domain model. `None` represents an unavailable
effective definition and yields an unresolved result, never a compatibility
claim. An incomplete stored overlay is not an effective definition.

The example oracle covers exact Group selectors and Endpoint refinement from
a name without a version to a name with a version. It reports unsupported
Endpoint version-to-version refinement: arbitrary version strings cannot be
interpreted by a generic prefix test. Envelope-specific profiles can define
those rules. This limit is not a claim that all other refinements are invalid.

The tests are offline abstract/source evidence, not real server/SDK
interoperability. They do not incorporate the separate borrowed-example
syntax, history, or base-merge patches.
