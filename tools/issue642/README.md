# Message example syntax and identity checks

<!-- words: pytest py cacheprovider SDK jsonpointer -->

`test_message_examples_642.py` parses the actual Message context example
strictly as JSON, without repairing it in the test. It also checks the
borrowed-Message fragment's nesting, counts, map-key/ID agreement, and local
one-hop, same-type `meta.xref` target using `jsonpointer`.

```shell
python -B -m pytest tools/issue642 -q -p no:cacheprovider
```

Only two explicitly identified format fragments are normalized. For the
borrowed collection fragment, normalization adds the omitted outer braces and
removes whole comment lines. For the CloudEvents format fragment it also
removes the declared trailing `?` markers and quotes the `<ANY>` placeholder
as a sentinel. It does not insert missing colons/commas, remove arbitrary
trailing commas, or alter literal values. Duplicate JSON keys fail the checks.

These are syntax and source-identity checks, not full Registry admission or
real server/SDK interoperability. Ellipses and other intentionally abbreviated
material are retained. The metadata-placement correction in issue 629 is not
copied here, and envelope, history, alias and base-merge policies are not
redefined. Tool implementation details are kept here rather than in the
[Message specification](../../message/spec.md).
