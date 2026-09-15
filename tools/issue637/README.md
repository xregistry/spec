# Message model default check

<!-- no verify-specs -->
<!-- words: pytest py cacheprovider -->

`test_message_history_637.py` reads the actual
[Message model](../../message/model.json) and checks that its default
`maxversions` value remains `1`.

```shell
python -B -m pytest tools/issue637 -q -p no:cacheprovider
```

This is an artifact check, not a simulation of customized history, reference
selection, matching, pruning or server behavior. It does not read specification
text.
