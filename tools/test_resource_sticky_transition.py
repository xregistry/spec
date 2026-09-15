"""Check the same-request example against Core, without simulating a server."""

import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import pytest
from test_samples import _unique_json_object


CORE = Path(__file__).resolve().parents[1] / "core"
GUIDE = (CORE / "resource.md").read_text(encoding="utf-8")
SPEC = (CORE / "spec.md").read_text(encoding="utf-8")
PATCH = "Patch Resource with Versions and defaultversionsticky"
PUT = "Update Resource with sticky non-specified defaultversionid"


def _section(title):
    return GUIDE.split(f"\n### {title}\n", 1)[1].split("\n### ", 1)[0]


def _block(title, label):
    return _section(title).split(label, 1)[1].split("```\n", 1)[1].split("\n```", 1)[0]


def _request(title):
    header, body = _block(title, "**Request:**").split("\n\n", 1)
    return header, json.loads(body, object_pairs_hook=_unique_json_object)


def _state(title, label):
    block = _block(title, label)
    aliases = re.findall(r'"([^"]+)": \{ see Resource\.\* attrs \}', block)
    state = json.loads(
        block.replace("{ see Resource.* attrs }", "{}"),
        object_pairs_hook=_unique_json_object,
    )
    assert aliases == [state["versionid"]]
    state["versions"][aliases[0]] = {
        key: value for key, value in state.items() if key not in {"meta", "versions"}
    }
    return state


def _transition_initial_fragments():
    # The initial block has an unrelated extra brace; no whole-block repair is made.
    block = _block(PATCH, "**Initial State:**")
    pairs = re.findall(
        r'^  "([^"]+)": ("(?:\\.|[^"\\])*"|true|false|\d+),?$', block, re.MULTILINE
    )
    root = _unique_json_object((name, json.loads(value)) for name, value in pairs)
    assert set(root) == {
        "fileid", "versionid", "epoch", "isdefault", "createdat", "modifiedat", "ancestorid"
    }
    meta = re.search(r'^  "meta": (\{.*?^  \})', block, re.MULTILINE | re.DOTALL)
    v1 = re.search(r'^    "v1": (\{.*?^    \})', block, re.MULTILINE | re.DOTALL)
    assert meta is not None and v1 is not None
    assert re.findall(r'^    "(v[^"]+)":', block, re.MULTILINE) == ["v1", "v2"]
    assert '"v2": { see Resource.* attrs }' in block
    return {
        **root,
        "meta": json.loads(meta.group(1), object_pairs_hook=_unique_json_object),
        "versions": {"v1": json.loads(v1.group(1)), "v2": dict(root)},
    }


def _year_instant(value):
    # Representative UTC instants are used only to compare the guide's year shorthand.
    return datetime.strptime(value, "%Y").replace(tzinfo=timezone.utc)


def _assert_transition_result(state):
    assert state["isdefault"] is True
    assert state["meta"]["defaultversionsticky"] is True
    assert {key: state[key] for key in (
        "fileid", "versionid", "epoch", "isdefault", "createdat", "modifiedat", "ancestorid"
    )} == {
        "fileid": "f1", "versionid": "v1", "epoch": 2, "isdefault": True,
        "createdat": "2025", "modifiedat": "now", "ancestorid": "v2",
    }
    assert state["meta"] == {
        "epoch": 2, "createdat": "2025", "modifiedat": "now",
        "defaultversionid": "v1", "defaultversionsticky": True,
    }
    assert set(state["versions"]) == {"v1", "v2"}
    assert state["versions"]["v2"] == {
        "epoch": 2, "createdat": "2020", "modifiedat": "now", "ancestorid": "v2",
    }
    assert "name" not in state
    assert all("name" not in version for version in state["versions"].values())


def test_same_patch_backdates_initial_target_v2_and_selects_newest_v1():
    initial = _transition_initial_fragments()
    header, request = _request(PATCH)
    final = _state(PATCH, "**Final State:**")
    assert header == "PATCH /dirs/d1/files/f1"
    assert initial["versionid"] == initial["meta"]["defaultversionid"] == "v2"
    assert initial["meta"]["defaultversionsticky"] is False
    assert {value["createdat"] for value in initial["versions"].values()} == {"2025"}
    assert request == {
        "name": "foo", "meta": {"defaultversionsticky": True},
        "versions": {"v2": {"createdat": "2020"}},
    }
    assert request["meta"]["defaultversionsticky"] is True
    assert _year_instant(final["versions"]["v2"]["createdat"]) < _year_instant(
        final["versions"]["v1"]["createdat"]
    )
    _assert_transition_result(final)


def test_core_reselection_conditions_distinguish_transition_put_and_already_sticky():
    conditions = SPEC.split("At the end of an update operation,", 1)[1].split(
        "\n\nRegardless of the reason", 1
    )[0]
    assert " ".join(conditions.split()) == (
        "this attribute MUST be set according to the "
        "[`versionmode`](./model.md#groupsstringresourcesstringversionmode) "
        "value of the Resource in any of the following situations: "
        "- The resulting `defaultversionsticky` value is `false`. "
        "- The processing fully replaced the `meta` sub-object and the request "
        "included `defaultversionsticky` with a value of `true`, but no "
        "`defaultversionid` was provided. "
        "- The processing patched the `meta` sub-object and the request modified "
        "`defaultversionsticky` from `false` to `true`, but no "
        "`defaultversionid` was provided."
    )
    sticky = SPEC.split("#### `defaultversionsticky` Attribute\n", 1)[1].split(
        "\n- Constraints:", 1
    )[0]
    assert " ".join(sticky.split()) == (
        "- Type: Boolean - Description: A value of `true` means that "
        "`defaultversionid` has been explicitly set and its value MUST NOT "
        "automatically change if other Versions are added or removed. A value "
        "of `false` means the default Version MUST be the newest Version, as "
        "defined by the Resource's "
        "[`versionmode`](./model.md#groupsstringresourcesstringversionmode) algorithm."
    )


def test_existing_put_reorder_control_still_selects_v1():
    header, request = _request(PUT)
    assert header == "PUT /dirs/d1/files/f1"
    assert request["meta"] == {"defaultversionsticky": True}
    assert request["versions"]["v2"]["createdat"] == "2020"
    _assert_transition_result(_state(PUT, "**Final State:**"))


def test_explicit_id_control_overrides_unchanged_version_order():
    title = "Patch Resource with sticky defaultversionid"
    initial = _state(title, "**Initial State:**")
    header, request = _request(title)
    final = _state(title, "**Final State:**")
    assert header == "PATCH /dirs/d1/files/f1/meta"
    assert initial["meta"]["defaultversionid"] == "v2"
    assert request == {"defaultversionid": "v1", "defaultversionsticky": True}
    assert final["versionid"] == final["meta"]["defaultversionid"] == "v1"
    for version in ("v1", "v2"):
        assert final["versions"][version]["createdat"] == initial["versions"][version]["createdat"] == "2025"


def test_unchanged_order_source_states_keep_the_only_version():
    # Only the source states are checked; this control's request has unrelated JSON defects.
    title = "Patch Resource with defaultversionsticky"
    initial = _state(title, "**Initial State:**")
    final = _state(title, "**Final State:**")
    assert initial["meta"]["defaultversionsticky"] is False
    assert final["meta"]["defaultversionsticky"] is True
    assert initial["versionid"] == final["versionid"] == "v1"
    assert set(initial["versions"]) == set(final["versions"]) == {"v1"}
    assert initial["createdat"] == final["createdat"] == "2025"


def test_patch_and_preceding_put_notes_describe_reselection_consistently():
    notes = _section(PATCH).split("**Notes:**", 1)[1].split("<hr>", 1)[0]
    assert " ".join(notes.split()) == (
        "- Resource.name is ignored due to `v2` (the initial default Version) "
        "being in the request's `versions` collection. "
        "- Since this `PATCH` changes `meta.defaultversionsticky` from `false` "
        "to `true` without specifying `meta.defaultversionid`, the default "
        "Version is recalculated after the update using `versionmode`. Moving "
        "`v2`'s `createdat` to `2020` makes `v1` (`2025`) the newest Version, "
        "so `v1` becomes the sticky default. "
        "- Ancestor order: `v2` (2020) <- `v1` (2025)."
    )
    preceding = " ".join(_section(PUT).split("**Notes:**", 1)[1].split())
    assert "the next example also recalculates the default for a `PATCH`" in preceding
    assert "changes this semantics" not in preceding


@pytest.mark.parametrize("defect", ["retained_old_default", "stale_projection"])
def test_transition_result_guard_rejects_old_default_or_stale_projection(defect):
    final = deepcopy(_state(PATCH, "**Final State:**"))
    if defect == "retained_old_default":
        final["versionid"] = final["meta"]["defaultversionid"] = "v2"
    final["createdat"] = "2020"
    with pytest.raises(AssertionError):
        _assert_transition_result(final)
