"""Resolve only the guide's declared shorthand and check its example graph."""

import json
import re
from copy import deepcopy
from pathlib import Path

import pytest
from test_samples import _unique_json_object


SOURCE = (Path(__file__).resolve().parents[1] / "core" / "resource.md").read_text(
    encoding="utf-8"
)
UPDATE = "Update Resource with new Versions and sticky default Version"


def _section(title):
    return SOURCE.split(f"\n### {title}\n", 1)[1].split("\n### ", 1)[0]


def _block(section, label):
    return section.split(label, 1)[1].split("```\n", 1)[1].split("\n```", 1)[0]


def _final_state(title):
    block = _block(_section(title), "**Final State:**")
    aliases = re.findall(r'"([^"]+)": \{ see Resource\.\* attrs \}', block)
    state = json.loads(
        block.replace("{ see Resource.* attrs }", "{}"),
        object_pairs_hook=_unique_json_object,
    )
    assert aliases == [state["versionid"]]
    projection = {key: value for key, value in state.items() if key not in {"meta", "versions"}}
    state["versions"][aliases[0]] = projection
    return state


def _assert_closed_acyclic_ancestry(versions):
    assert set(versions) == {"v0", "v1", "v2"}
    for start in versions:
        seen = set()
        current = start
        while True:
            assert current in versions, f"Unknown ancestor: {current}"
            assert current not in seen, f"Ancestry cycle from {start}"
            seen.add(current)
            parent = versions[current]["ancestorid"]
            if parent == current:
                break
            current = parent
    assert {key for key, value in versions.items() if value["ancestorid"] == key} == {"v1"}


def test_sticky_final_state_has_all_expected_edges_and_one_acyclic_self_root():
    state = _final_state(UPDATE)
    versions = state["versions"]
    assert {key: value["ancestorid"] for key, value in versions.items()} == {
        "v1": "v1", "v0": "v1", "v2": "v0"
    }
    assert {key: value["createdat"] for key, value in versions.items()} == {
        "v1": "2020", "v0": "2021", "v2": "now"
    }
    _assert_closed_acyclic_ancestry(versions)
    setup = json.loads(_block(_section("The Setup"), "- Has a model defined as:"))
    assert setup["groups"]["dirs"]["resources"]["files"]["versionmode"] == "createdat"


def test_sticky_selection_and_original_attribute_update_target_are_preserved():
    request = json.loads(_block(_section(UPDATE), "**Request:**").split("\n\n", 1)[1])
    state = _final_state(UPDATE)
    assert request["meta"] == {"defaultversionid": "v1", "defaultversionsticky": True}
    assert state["versionid"] == state["meta"]["defaultversionid"] == "v1"
    assert state["meta"]["defaultversionsticky"] is True
    assert state["meta"]["epoch"] == 2
    assert state["versions"]["v0"]["name"] == request["name"] == "foo"
    assert state["versions"]["v0"]["epoch"] == 2
    assert state["versions"]["v1"]["epoch"] == state["versions"]["v2"]["epoch"] == 1
    assert "name" not in state


def test_earlier_ancestry_note_references_only_existing_versions():
    title = "Create Resource with Versions, no defaultversionid"
    section = _section(title)
    note = re.search(r"^- Ancestor order: (.+)$", section, re.MULTILINE).group(1)
    identifiers = re.findall(r"`([^`]+)`", note)
    assert identifiers == ["v1", "v2"]
    assert set(identifiers) == set(_final_state(title)["versions"])


def test_sticky_creation_note_uses_v0_explicit_2021_date():
    section = _section("Create Resource with Versions and sticky default Version")
    block = _block(section, "**Final State:**")
    v0 = json.loads(re.search(r'"v0": (\{[^{}]*\})', block).group(1))
    assert v0["createdat"] == "2021"
    note = re.search(r"^- Ancestor order: (.+)$", section, re.MULTILINE).group(1)
    assert note == "`v1` (2020) <- `v0` (2021) <- `v2` (now)."


@pytest.mark.parametrize("defect", ["cycle", "missing_ancestor", "extra_root"])
def test_example_graph_guard_rejects_invalid_topology(defect):
    versions = deepcopy(_final_state(UPDATE)["versions"])
    if defect == "cycle":
        versions["v0"]["ancestorid"] = "v2"
    elif defect == "missing_ancestor":
        versions["v2"]["ancestorid"] = "1"
    else:
        versions["v0"]["ancestorid"] = "v0"
    with pytest.raises(AssertionError):
        _assert_closed_acyclic_ancestry(versions)
