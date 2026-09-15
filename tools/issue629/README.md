# Flat envelope metadata model checks

<!-- no verify-specs -->
<!-- words: pytest py cacheprovider -->

`test_flat_envelope_metadata_629.py` checks the actual
[Message model](../../message/model.json). It verifies that the CloudEvents
metadata declarations include `type`, `source` and `subject` directly, without
an intervening `attributes` wrapper.

```shell
python -B -m pytest tools/issue629 -q -p no:cacheprovider
```

These checks cover only the model's flat declaration surface. They do not
check specification prose, examples, templates, declaration values or server
interoperability.
