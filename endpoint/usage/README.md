# Endpoint usage projection and migration

<!-- no verify-specs -->
<!-- words: py pytest -->

The [Endpoint specification](../spec.md#usage) defines the domain role
constraints, and explains why generated schema admission alone is not a
complete domain check. The source model and generated artifacts describe only
the structural portion of that contract.

Readers generated from the old artifacts need to migrate Avro enum items to
string items and honor the now-required `usage` array. They must apply the
domain checks rather than treating an unrestricted string array as the full
contract. No role is inferred or inserted for an existing declaration that
omits `usage`; the author supplies the intended role. The permitted role
combinations have not changed.

The [focused regressions](../../tools/test_issue_626_endpoint_usage.py) exercise
the source model and all four generated representations for both the Endpoint
and CloudEvents consumers:

```console
python -B -m pytest tools/test_issue_626_endpoint_usage.py -q
```
