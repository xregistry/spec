# Message history profile checks

<!-- words: pytest py cacheprovider SDK -->

`message_history_637.py` checks a retained owned-Message snapshot, selects a
Resource's default or an explicitly referenced Version, and demonstrates the
example's type/payload-media matching strategy.
`test_message_history_637.py` parses the actual customized-history example
in the [Message specification](../../message/spec.md) and reads the unchanged
default limit from the [Message model](../../message/model.json).

```shell
python -B -m pytest tools/issue637 -q -p no:cacheprovider
```

The snapshot check is not a Core write/pruning implementation. In particular,
a zero limit permits history but does not promise indefinite retention.
Reference selection uses only the provided local snapshot, returns no Version
for a missing target, and does not acquire anything or substitute the default.
The sample matcher reports unmatched, unique, or ambiguous results; it is not
a mandatory general matching algorithm. Precise identity does not make
Version contents immutable.

These are offline abstract/source checks, not real server/SDK interoperability.
They do not change models, native wire encoding, envelope binding obligations,
or base-message merge behavior.
