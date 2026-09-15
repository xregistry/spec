# Specification tooling notes

<!-- no verify-specs -->
<!-- words: py pytest powershell -->

## Default-selection contract

The [executable candidate-stage contract](default_selection_contract.py)
illustrates the
[default selection rules](../core/spec.md#defaultversionid-attribute) after the
surrounding processing has resolved whether a candidate is the effective sticky
selection. It does not replace Meta processing, Version creation or default
selection.

The caller supplies the final Version IDs and indicates whether the candidate
remains the effective sticky selection after Meta processing, model defaults,
patch inference and flag overrides. The helper checks candidate syntax and
the applicable existence obligation without selecting or mutating Versions.
It is an abstract illustration, not a server or transaction implementation.

Run the focused examples from the repository root:

```powershell
python -m pytest tools\test_default_selection_policy.py -q
```
