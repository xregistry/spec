# Specification tooling notes

<!-- no verify-specs -->
<!-- words: py pytest powershell -->

## Manual-pruning contract

The [manual-pruning contract](manual_pruning_contract.py) illustrates the
[Version retention ordering](../core/model.md#groupsstringresourcesstringmaxversions)
when a manual ancestry tree contains a protected default Version.

The helper returns a finite deletion plan without changing the supplied graph.
It visits the protected default only to make its children eligible; the visit
does not itself delete or change any Version. A separate helper projects the
ancestry effects of actual deletions. For example, pruning `a <- b <- c` to
two Versions with sticky default `a` deletes `b`, keeps `a`, and makes `c` a
root under the existing manual ancestry rules.

Callers provide timestamp comparison keys and independently applicable
per-Version deletion restrictions. This is an abstract ordering illustration,
not a server or retention-policy engine. Final model constraints, including
the single-root policy, can still reject a plan. Request rollback, attribute
maintenance, authorization, removal-time promises, and event delivery remain
the surrounding implementation's responsibility.

Run the focused examples from the repository root:

```powershell
python -m pytest tools\test_manual_pruning_policy.py -q
```
