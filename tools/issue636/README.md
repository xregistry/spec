# CloudEvents prose layout checks

<!-- words: pytest py cacheprovider SDK jsonpointer -->

`test_cloudevents_examples_636.py` reads the actual four concrete/projection
examples in the [CloudEvents specification](../../cloudevents/spec.md).
The first two are strictly parsed as complete JSON with duplicate-key
rejection. The two explicitly abbreviated remote-reference illustrations are
parsed as YAML because they retain the document's declared comment notation.
The final placeholder-only format sketch is not treated as a Registry.

```shell
python -B -m pytest tools/issue636 -q -p no:cacheprovider
```

The checks inspect native domain fields, scalar/array kinds, map-key/ID
agreement, parent-derived self/XID/Meta/Versions navigation, and compact versus
shared layouts. The existing Protobuf selector rule is exercised with
`jsonpointer` against the shown local Schema Version, followed by a check for
the selected declaration in that example's simple schema literal. This is not
a general Protobuf parser or a new selector grammar.

Timestamps are intentionally opaque here; the separate date correction is
issue 638. These tests do not validate all Core/model constraints, schema
identifiers, or unresolved domain-model defects, and do not fetch remote
references. They are abstract/source evidence, not real server/SDK
interoperability. Scenario samples covered by earlier work are not changed.
