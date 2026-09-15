# Specification tooling notes

<!-- no verify-specs -->
<!-- words: py pytest powershell -->

## Compatibility-claim contract

The [compatibility-claim contract](compatibility_claim_contract.py) illustrates
[stored claim admission](../core/spec.md#compatibility-attribute) and
[per-Version validation status](../core/spec.md#compatibilityvalidated-attribute).

Callers supply the complete staged Version set, a model-admission predicate,
and a deferred checker. Model admission includes the applicable attribute
constraints, not just membership in an enumeration: an empty or advisory
enumeration is not a restrictive list. The surrounding implementation also
owns format validation, capability lookup, document access, and pair selection
according to ancestry and the claimed compatibility strategy.

The checker returns `true` for a completed successful check, `false` for an
actual violation, or a typed unchecked result with an unavailable-check error
and an explanation. The helper keeps unavailable checks distinct from failed
checks, clears stale status fields, and plans changes on a copy. Unexpected
checker errors propagate; they are not converted to unchecked success.
A checked compatibility outcome cannot override an existing unchecked format
status; contradictory checker output is rejected.

This is an abstract decision-stage illustration, not a server, schema
compatibility validator, capability wildcard resolver, or transaction engine.
Returning a plan does not certify that the claim is true. Final publication,
rollback, authorization, and all other model constraints remain the caller's
responsibility.

Run the focused examples from the repository root:

```powershell
python -m pytest tools\test_compatibility_claim_policy.py -q
```
