"""Source-bound finite-frontier vectors, not a live server pruning engine."""

from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from manual_pruning_contract import manual_ancestors_after_deletions, plan_sticky_manual_pruning


ROOT = Path(__file__).resolve().parents[1]
MODEL = (ROOT / "core" / "model.md").read_text(encoding="utf-8")
SPEC = (ROOT / "core" / "spec.md").read_text(encoding="utf-8")
TOOL_NOTES = (ROOT / "tools" / "README.md").read_text(encoding="utf-8")
LIMITS = MODEL.split("### `groups.<STRING>.resources.<STRING>.maxversions`\n", 1)[1].split("\n### ", 1)[0]


def _v(parent, year):
    return {"ancestorid": parent, "createdat": f"{year:04d}-01-01T00:00:00Z"}


def _key(value):
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")


def _plan(versions, limit=2, default="a", blocked=()):
    return plan_sticky_manual_pruning(
        versions, limit, default, timestamp_key=_key,
        can_delete=lambda name, value: name not in blocked,
    )


def test_source_defines_finite_virtual_frontier_without_deleting_default():
    text = " ".join(LIMITS.split())
    assert "For `manual` mode when the default Version is to be skipped" in text
    assert "immutable snapshot of the current ancestry links" in text
    assert "visited at most once" in text
    assert "oldest `createdat` timestamp, then the lowest case-insensitive `versionid`" in text
    assert "Visiting the default only advances this virtual ordering" in text
    assert "MUST NOT delete it, change its ancestry, or count it toward the needed deletions" in text
    assert "Non-default Versions that cannot legally be deleted are not virtually visited" in text
    assert "entire operation MUST be rejected" in text
    assert "manual_pruning_contract.py" not in MODEL
    assert "py" not in MODEL.split("## Abstract", 1)[0].split()
    assert "(manual_pruning_contract.py)" in TOOL_NOTES
    assert "(../core/model.md#groupsstringresourcesstringmaxversions)" in TOOL_NOTES
    assert "not a server or retention-policy engine" in " ".join(TOOL_NOTES.split())


def test_sole_default_root_advances_to_child_and_keeps_real_ancestry_until_deletion():
    versions = {"a": _v("a", 2020), "b": _v("a", 2021), "c": _v("b", 2022)}
    before = deepcopy(versions)
    deleted = _plan(versions)
    assert deleted == ("b",)
    assert versions == before
    assert manual_ancestors_after_deletions(versions, deleted, "a") == {"a": "a", "c": "c"}


def test_multiple_roots_and_backdated_descendant_use_eligible_frontier_order():
    versions = {
        "a": _v("a", 2030), "older": _v("older", 2025),
        "backdated": _v("a", 2000), "future": _v("older", 2040),
    }
    assert _plan(versions) == ("older", "backdated")
    assert manual_ancestors_after_deletions(versions, ("older", "backdated"), "a") == {
        "a": "a", "future": "future"
    }
    assert _plan(dict(reversed(list(versions.items())))) == ("older", "backdated")


def test_default_in_middle_is_retained_and_only_real_parent_deletion_reparents_it():
    versions = {"root": _v("root", 2020), "a": _v("root", 2021), "child": _v("a", 2022), "other": _v("other", 2023)}
    deleted = _plan(versions)
    assert deleted == ("root", "child")
    assert versions["a"]["ancestorid"] == "root"
    assert manual_ancestors_after_deletions(versions, deleted, "a") == {"a": "a", "other": "other"}


def test_equal_timestamp_candidates_use_case_insensitive_id_not_input_order():
    versions = {"a": _v("a", 2030), "z": _v("z", 2020), "B": _v("B", 2020), "c": _v("c", 2020)}
    assert _plan(versions) == ("B", "c")
    assert _plan(dict(reversed(list(versions.items())))) == ("B", "c")


def test_blocked_candidate_does_not_get_virtually_deleted_to_release_descendants():
    versions = {"a": _v("a", 2020), "b": _v("a", 2021), "c": _v("b", 2022)}
    before = deepcopy(versions)
    with pytest.raises(ValueError, match="no complete legal pruning plan"):
        _plan(versions, blocked={"b"})
    assert versions == before


def test_other_eligible_roots_can_satisfy_limit_without_breaking_deletion_restriction():
    versions = {"a": _v("a", 2020), "blocked": _v("a", 2021), "child": _v("blocked", 2022), "other": _v("other", 2023)}
    assert _plan(versions, limit=3, blocked={"blocked"}) == ("other",)
    assert "blocked" in versions and "child" in versions


def test_incomplete_plan_rejects_atomically_after_an_earlier_eligible_deletion():
    versions = {"a": _v("a", 2020), "b": _v("b", 2021), "c": _v("c", 2022), "d": _v("d", 2023)}
    before = deepcopy(versions)
    with pytest.raises(ValueError, match="no complete legal pruning plan"):
        _plan(versions, blocked={"c", "d"})
    assert versions == before


def test_repeated_prunes_progress_without_cycling_or_rewriting_skipped_default():
    versions = {"a": _v("a", 2020), "b": _v("a", 2021)}
    for index in range(8):
        last = next(name for name in versions if name != "a")
        name = f"new{index}"
        versions[name] = _v(last, 2030 + index)
        deleted = _plan(versions)
        assert deleted == (last,) and "a" not in deleted
        ancestors = manual_ancestors_after_deletions(versions, deleted, "a")
        versions = {key: {**versions[key], "ancestorid": parent} for key, parent in ancestors.items()}
        assert set(versions) == {"a", name} and versions["a"] == _v("a", 2020)


def test_long_chain_has_a_finite_plan_with_no_duplicate_visits():
    start = datetime(2020, 1, 1)
    versions = {
        f"v{index}": {
            "ancestorid": f"v{max(index - 1, 0)}",
            "createdat": (start + timedelta(days=index)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        for index in range(120)
    }
    deleted = _plan(versions, default="v0")
    assert deleted == tuple(f"v{index}" for index in range(1, 119))
    assert len(set(deleted)) == 118 and len(versions) == 120


def test_zero_limit_and_sticky_maxversions_one_constraint_are_preserved():
    versions = {"a": _v("a", 2020), "b": _v("a", 2021)}
    assert _plan(versions, limit=0) == ()
    with pytest.raises(ValueError, match="setdefaultversionsticky_false"):
        _plan(versions, limit=1)
    text = " ".join(LIMITS.split())
    assert 'if `maxversions` is set to one (1), then the "default" Version is not skipped' in text
    assert "change `maxversions` to `1`" in text and "defaultversionsticky" in text


@pytest.mark.parametrize("count", [1, 2])
def test_at_or_below_limit_preserves_every_version(count):
    versions = {"a": _v("a", 2020)}
    if count == 2:
        versions["b"] = _v("a", 2021)
    before = deepcopy(versions)
    assert _plan(versions, limit=2) == ()
    assert versions == before


@pytest.mark.parametrize("limit", [-1, True, 2.5, "2"])
def test_invalid_limits_are_rejected_without_mutating_state(limit):
    versions = {"a": _v("a", 2020), "b": _v("a", 2021)}
    before = deepcopy(versions)
    with pytest.raises(ValueError, match="Invalid maxversions"):
        _plan(versions, limit=limit)
    assert versions == before


def test_actual_deletion_does_not_override_single_root_constraint():
    versions = {"a": _v("a", 2020), "b": _v("a", 2021), "c": _v("b", 2022)}
    deleted = _plan(versions)
    ancestors = manual_ancestors_after_deletions(versions, deleted, "a")
    assert {name for name, parent in ancestors.items() if name == parent} == {"a", "c"}
    single_root = MODEL.split(
        "### `groups.<STRING>.resources.<STRING>.singleversionroot`\n", 1
    )[1].split("\n### ", 1)[0]
    assert "([multiple_roots](./spec.md#multiple_roots))" in single_root
    assert (
        "The resulting Resource MUST still satisfy all other model constraints, including "
        "[`singleversionroot`](#groupsstringresourcesstringsingleversionroot); "
        "violations MUST generate the existing errors and undo the entire request."
    ) in " ".join(LIMITS.split())


@pytest.mark.parametrize("defect", ["cycle", "missing_parent", "case_duplicate"])
def test_invalid_ancestry_is_rejected_instead_of_looping(defect):
    versions = {"a": _v("a", 2020), "b": _v("a", 2021), "c": _v("b", 2022)}
    if defect == "cycle":
        versions["b"]["ancestorid"] = "c"
    elif defect == "missing_parent":
        versions["b"]["ancestorid"] = "missing"
    else:
        versions["A"] = _v("A", 2023)
    with pytest.raises(ValueError):
        _plan(versions)


def test_source_preserves_removal_promises_real_ancestry_bookkeeping_and_rollback():
    text = " ".join(SPEC.split())
    assert "The entity MUST NOT be removed before this time." in text
    assert "Any modification to the `ancestorid` attribute MUST result in the owning Version's `epoch` and `modifiedat` attributes be updated" in text
    assert "the entire request MUST be undone." in text
    proposed = " ".join(LIMITS.split())
    assert "Existing deletion restrictions and deprecation/removal promises MUST NOT be weakened" in proposed
    assert "Only actual deletions invoke the existing ancestry and attribute-maintenance rules" in proposed
