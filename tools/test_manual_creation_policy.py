"""Source-bound abstract creation vectors, not live server execution."""

from copy import deepcopy
from datetime import datetime
from pathlib import Path

import pytest
from manual_creation_contract import manual_newest, plan_automatic_creations, plan_manual_creation


ROOT = Path(__file__).resolve().parents[1]
MODEL = (ROOT / "core" / "model.md").read_text(encoding="utf-8")
SPEC = (ROOT / "core" / "spec.md").read_text(encoding="utf-8")
MANUAL = MODEL.split("  - `manual`\n", 1)[1].split("\n  - `createdat`\n", 1)[0]


def _time(value):
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")


def _roots():
    return {
        "a": {"ancestorid": "a", "createdat": "2030-01-01T00:00:00Z", "name": "keep-a"},
        "b": {"ancestorid": "b", "createdat": "2029-01-01T00:00:00Z", "name": "keep-b"},
    }


def test_source_preserves_selector_and_newest_claim_but_adds_atomic_admission():
    text = " ".join(MANUAL.split())
    assert "all Versions that are not referenced as an `ancestor` of another Version" in text
    assert "highest alphabetically case-insensitive `versionid` value MUST be chosen" in text
    assert 'each new Version is created, it MUST become the "newest"' in text
    assert (
        'Immediately after each automatically linked creation, the "Newest '
        'Version" selector MUST be evaluated on the resulting staged Versions. '
        'If it does not select that new Version, the entire operation MUST be '
        'rejected ([bad_request](./spec.md#bad_request)), without retaining partial '
        'state or changing the supplied timestamp.'
    ) in text
    assert "../tools/manual_creation_contract.py" in MANUAL
    assert (
        "The check belongs to each existing creation step in the case-insensitive "
        "Version-ID order above, not JSON member order, and precedes subsequent "
        "retention and default processing."
    ) in text
    assert "Earlier new Versions need not remain newest after later creations." in text
    assert 'The invariant concerns "newest", not which Version is the final default.' in text
    assert "Explicitly supplied `ancestorid` values retain their existing semantics" in text
    assert "Backdated timestamps are not categorically rejected." in text


def test_original_multi_root_counterexample_rejects_without_mutating_state():
    initial = _roots()
    before = deepcopy(initial)
    candidate = {"createdat": "2000-01-01T00:00:00Z", "description": "preserve"}
    with pytest.raises(ValueError, match="bad_request"):
        plan_manual_creation(initial, "c", candidate, timestamp_key=_time)
    assert initial == before
    assert candidate == {"createdat": "2000-01-01T00:00:00Z", "description": "preserve"}
    assert manual_newest(initial, timestamp_key=_time) == "a"


def test_single_terminal_backdated_creation_is_still_valid():
    initial = {"a": _roots()["a"]}
    result = plan_manual_creation(initial, "c", {"createdat": "2000-01-01T00:00:00Z"}, timestamp_key=_time)
    assert result["c"] == {"ancestorid": "a", "createdat": "2000-01-01T00:00:00Z"}
    assert result["a"] == initial["a"]
    assert manual_newest(result, timestamp_key=_time) == "c"
    assert set(initial) == {"a"}


@pytest.mark.parametrize("name, accepted", [("A0", False), ("c", True)])
def test_resulting_terminal_timestamp_ties_use_existing_case_insensitive_id_rule(name, accepted):
    candidate = {"createdat": "2029-01-01T00:00:00Z"}
    if accepted:
        result = plan_manual_creation(_roots(), name, candidate, timestamp_key=_time)
        assert manual_newest(result, timestamp_key=_time) == name
    else:
        with pytest.raises(ValueError, match="bad_request"):
            plan_manual_creation(_roots(), name, candidate, timestamp_key=_time)


def test_explicit_ancestor_is_not_subject_to_automatic_newest_admission():
    result = plan_manual_creation(
        _roots(), "c", {"ancestorid": "a", "createdat": "2000-01-01T00:00:00Z"},
        timestamp_key=_time,
    )
    assert result["c"]["ancestorid"] == "a"
    assert manual_newest(result, timestamp_key=_time) == "b"


def test_explicit_root_and_empty_automatic_creation_keep_existing_semantics():
    explicit = plan_manual_creation(_roots(), "c", {"ancestorid": "c", "createdat": "2000-01-01T00:00:00Z"}, timestamp_key=_time)
    assert explicit["c"]["ancestorid"] == "c"
    assert manual_newest(explicit, timestamp_key=_time) == "a"
    empty = plan_manual_creation({}, "c", {"createdat": "2000-01-01T00:00:00Z"}, timestamp_key=_time)
    assert empty["c"]["ancestorid"] == manual_newest(empty, timestamp_key=_time) == "c"


def test_multiple_creations_use_id_order_not_mapping_order_or_simultaneous_newest():
    initial = {"a": _roots()["a"]}
    reverse_order = {
        "z": {"createdat": "2000-01-01T00:00:00Z"},
        "B": {"createdat": "2001-01-01T00:00:00Z"},
    }
    first = plan_automatic_creations(initial, reverse_order, timestamp_key=_time)
    second = plan_automatic_creations(initial, dict(reversed(list(reverse_order.items()))), timestamp_key=_time)
    assert first == second
    assert first["B"]["ancestorid"] == "a" and first["z"]["ancestorid"] == "B"
    assert manual_newest(first, timestamp_key=_time) == "z"
    assert "B" != manual_newest(first, timestamp_key=_time)


def test_later_creation_failure_discards_the_whole_staged_plan():
    initial = _roots()
    before = deepcopy(initial)
    additions = {
        "c": {"createdat": "2031-01-01T00:00:00Z"},
        "d": {"createdat": "2000-01-01T00:00:00Z"},
    }
    with pytest.raises(ValueError, match="bad_request"):
        plan_automatic_creations(initial, additions, timestamp_key=_time)
    assert initial == before and "c" not in initial and "d" not in initial
    assert additions["d"]["createdat"] == "2000-01-01T00:00:00Z"


def test_later_retention_cannot_rescue_an_invalid_creation_step():
    initial = _roots()
    with pytest.raises(ValueError, match="bad_request"):
        plan_manual_creation(initial, "c", {"createdat": "2000-01-01T00:00:00Z"}, timestamp_key=_time)
    after_hypothetical_pruning = {
        "a": initial["a"],
        "c": {"ancestorid": "a", "createdat": "2000-01-01T00:00:00Z"},
    }
    assert manual_newest(after_hypothetical_pruning, timestamp_key=_time) == "c"
    assert set(initial) == {"a", "b"}


def test_whole_request_rollback_and_later_default_retention_stages_are_unchanged():
    rule = " ".join(SPEC.split("## Error Processing\n\n", 1)[1].split("\n\n", 1)[0].split())
    assert rule.endswith("the entire request MUST be undone.")
    stages = SPEC.split("The overall processing of the request message is as follows:", 1)[1].split("The following provides additional details:", 1)[0]
    assert stages.index("1.  Process the Versions") < stages.index("5.  Update")
    assert stages.index("5.  Update") < stages.index("10. Enforce")
