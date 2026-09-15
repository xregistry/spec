import json
import re
from copy import deepcopy
from pathlib import Path

import pytest

from events_xref_605 import LocalResource, plan_lifecycles


ROOT = Path(__file__).resolve().parents[2]
ALIAS = "/dirs/d1/files/alias"
TARGET = "/dirs/d2/files/target"
NORMAL = LocalResource({"v1": 3, "v2": 8}, "v1", 11)


def test_events_605_dangling_example_matches_owned_state():
    text = (ROOT / "core" / "events.md").read_text(encoding="utf-8")
    example = text.split(
        "### Create a cross-reference Resource with an unavailable target\n", 1
    )[1]
    request, capture = re.findall(r"```yaml\n(.*?)\n```", example, re.S)
    headers, body = request.split("\n\n", 1)
    assert headers.splitlines()[0] == "PATCH /dirs/d1"
    payload = json.loads(body)
    assert set(payload) == {"files"}
    resources = {}
    for resource_id, attributes in payload["files"].items():
        assert set(attributes) == {"meta"}
        assert set(attributes["meta"]) == {"xref"}
        resources[f"/dirs/d1/files/{resource_id}"] = LocalResource(
            xref=attributes["meta"]["xref"]
        )
    assert set(resources) == {ALIAS}
    assert resources[ALIAS].xref not in resources
    assert resources[ALIAS].versions == {}

    events = json.loads(capture)
    assert events[1:] == plan_lifecycles({}, resources)
    assert events[0] == {
        "type": "io.xregistry.group.updated",
        "subject": "/dirs/d1",
        "data": {
            "epoch": 6 + 1,
            "changed": ["epoch", "modifiedat", "files", "filescount"],
        },
    }
    assert len(events) == 2


@pytest.mark.parametrize("availability", ["missing", "inaccessible", "xref-target"])
def test_events_605_unavailable_projection_omits_epochs_and_versions(availability):
    views = {
        "missing": {},
        "inaccessible": {},
        "xref-target": {
            TARGET: {"meta": {"xref": "/dirs/d3/files/further"}},
            "/dirs/d3/files/further": {"epoch": 3, "meta": {"epoch": 11}},
        },
    }[availability]
    target_state = {
        "missing": {},
        "inaccessible": {TARGET: NORMAL},
        "xref-target": {
            TARGET: LocalResource(xref="/dirs/d3/files/further"),
            "/dirs/d3/files/further": NORMAL,
        },
    }[availability]
    before = deepcopy(target_state)
    after = {**target_state, ALIAS: LocalResource(xref=TARGET)}
    saved = deepcopy(after)
    assert plan_lifecycles(before, after, views) == [
        {"type": "io.xregistry.resource.created", "subject": ALIAS, "data": {}}
    ]
    assert after == saved
    assert before == target_state


@pytest.mark.parametrize(
    "view, expected",
    [
        ({"epoch": 8, "meta": {"epoch": 11}}, {"epoch": 8, "meta.epoch": 11}),
        ({"epoch": 0}, {"epoch": 0}),
        ({"meta": {"epoch": 0}}, {"meta.epoch": 0}),
    ],
)
def test_events_605_live_projection_includes_only_available_values(view, expected):
    view = {**view, "versions": {"projected": {"epoch": 99}}}
    result = plan_lifecycles(
        {}, {ALIAS: LocalResource(xref=TARGET, meta_epoch=42)}, {TARGET: view}
    )
    assert result == [
        {"type": "io.xregistry.resource.created", "subject": ALIAS, "data": expected}
    ]


def test_events_605_normal_to_alias_deletes_only_owned_versions():
    before = {ALIAS: NORMAL, TARGET: NORMAL}
    after = {ALIAS: LocalResource(xref=TARGET), TARGET: NORMAL}
    events = plan_lifecycles(before, after)
    assert [(event["type"], event["subject"]) for event in events] == [
        ("io.xregistry.resource.updated", ALIAS),
        ("io.xregistry.version.deleted", f"{ALIAS}/versions/v1"),
        ("io.xregistry.version.deleted", f"{ALIAS}/versions/v2"),
    ]
    assert events[0]["data"] == {}
    assert all("data" not in event for event in events[1:])
    assert before[TARGET] == after[TARGET] == NORMAL


def test_events_605_normal_creation_announces_real_owned_versions():
    events = plan_lifecycles({}, {TARGET: NORMAL})
    assert [(event["type"], event["subject"]) for event in events] == [
        ("io.xregistry.resource.created", TARGET),
        ("io.xregistry.version.created", f"{TARGET}/versions/v1"),
        ("io.xregistry.version.created", f"{TARGET}/versions/v2"),
    ]
    assert events[0]["data"] == {"epoch": 3, "meta.epoch": 11}
    assert [event["data"]["epoch"] for event in events[1:]] == [3, 8]


def test_events_605_alias_to_normal_creates_actual_default_only():
    before = {ALIAS: LocalResource(xref=TARGET), TARGET: NORMAL}
    after = {ALIAS: LocalResource({"new": 1}, "new", 12), TARGET: NORMAL}
    assert plan_lifecycles(before, after) == [
        {
            "type": "io.xregistry.resource.updated",
            "subject": ALIAS,
            "data": {"epoch": 1, "meta.epoch": 12},
        },
        {
            "type": "io.xregistry.version.created",
            "subject": f"{ALIAS}/versions/new",
            "data": {"epoch": 1},
        },
    ]
    assert after[TARGET] == before[TARGET]


def test_events_605_retarget_and_alias_deletion_leave_targets_untouched():
    before = {ALIAS: LocalResource(xref=TARGET), TARGET: NORMAL}
    after = {**before, ALIAS: LocalResource(xref="/dirs/d2/files/missing")}
    assert plan_lifecycles(before, after) == [
        {"type": "io.xregistry.resource.updated", "subject": ALIAS, "data": {}}
    ]
    assert plan_lifecycles(after, {TARGET: NORMAL}) == [
        {"type": "io.xregistry.resource.deleted", "subject": ALIAS}
    ]
    assert before[TARGET] == after[TARGET]


def test_events_605_target_update_uses_target_subject_not_alias():
    before = {ALIAS: LocalResource(xref=TARGET), TARGET: NORMAL}
    after = {**before, TARGET: LocalResource({"v1": 4, "v2": 8}, "v1", 11)}
    events = plan_lifecycles(before, after)
    assert [(event["type"], event["subject"]) for event in events] == [
        ("io.xregistry.resource.updated", TARGET),
        ("io.xregistry.version.updated", f"{TARGET}/versions/v1"),
    ]
    assert events[0]["data"] == {"epoch": 4, "meta.epoch": 11}
    assert events[1]["data"] == {"epoch": 4}


def test_events_605_nondefault_update_does_not_update_resource_projection():
    before = {TARGET: NORMAL}
    after = {TARGET: LocalResource({"v1": 3, "v2": 9}, "v1", 11)}
    assert plan_lifecycles(before, after) == [
        {
            "type": "io.xregistry.version.updated",
            "subject": f"{TARGET}/versions/v2",
            "data": {"epoch": 9},
        }
    ]


def test_events_605_cascade_announces_each_owned_version_once():
    before = {ALIAS: LocalResource(xref=TARGET), TARGET: NORMAL}
    events = plan_lifecycles(before, {})
    assert {(event["type"], event["subject"]) for event in events} == {
        ("io.xregistry.resource.deleted", ALIAS),
        ("io.xregistry.resource.deleted", TARGET),
        ("io.xregistry.version.deleted", f"{TARGET}/versions/v1"),
        ("io.xregistry.version.deleted", f"{TARGET}/versions/v2"),
    }
    assert len(events) == 4
    assert all("data" not in event for event in events)


def test_events_605_unchanged_local_state_emits_nothing():
    state = {ALIAS: LocalResource(xref=TARGET), TARGET: NORMAL}
    assert plan_lifecycles(
        state, deepcopy(state), {TARGET: {"epoch": 999, "meta": {"epoch": 1000}}}
    ) == []


def test_events_605_rejects_fabricated_alias_ownership_and_invalid_epoch():
    with pytest.raises(ValueError, match="alias cannot own Versions"):
        LocalResource({"invented": 1}, "invented", 1, TARGET)
    with pytest.raises(ValueError, match="unsigned integer"):
        plan_lifecycles(
            {}, {ALIAS: LocalResource(xref=TARGET)}, {TARGET: {"epoch": None}}
        )


def test_events_605_spec_states_ownership_and_omission_exceptions():
    text = " ".join((ROOT / "core" / "events.md").read_text(encoding="utf-8").split())
    assert "each unavailable value MUST be omitted" in text
    assert "creation MUST NOT generate Version-created events" in text
    assert "Version events describe locally owned Versions" in text
    assert "When `changed` is included for a change to `meta.xref`" in text
    assert "Version `deleted` event for each formerly owned Version" in text
    assert "recursive cross-reference resolution" in text
