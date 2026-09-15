# Specification tooling notes

<!-- no verify-specs -->
<!-- words: py pytest powershell -->

## Manual-creation contract

The [executable creation-stage contract](manual_creation_contract.py)
illustrates the scoped checks and atomic automatic-creation plans for
[manual ancestry](../core/model.md#groupsstringresourcesstringversionmode).
Surrounding request processing remains governed by the existing Resource
processing rules.

The helper produces pure creation-stage plans using caller-supplied timestamp
keys. It does not implement a server, the surrounding request pipeline,
retention, or timestamp parsing. It neither clips timestamps nor changes the
supplied Version state.

Run the focused examples from the repository root:

```powershell
python -m pytest tools\test_manual_creation_policy.py -q
```
