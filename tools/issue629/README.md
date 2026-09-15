# Flat envelope metadata source checks

<!-- words: pytest py cacheprovider SDK -->

`test_flat_envelope_metadata_629.py` checks the CloudEvents declaration
locations in the Message and Endpoint prose against the flat
[Message model](../../message/model.json). The Endpoint example is parsed as
complete JSON with duplicate-key rejection. The Message context example is
checked by decoding only its envelope metadata/options object members, and
its actual templates are exercised with sample application context values.

```shell
python -B -m pytest tools/issue629 -q -p no:cacheprovider
```

This is deliberately a placement check. The context example's separate
punctuation correction belongs to issue 642; this test neither repairs its
missing comma nor claims the enclosing document parses. The CloudEvents
format sketch remains an abbreviated sketch, not a complete Registry.
Declaration value types and presets are independently tracked model concerns.
These checks provide abstract/source evidence, not complete model admission
or real server/SDK interoperability.
