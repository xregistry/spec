import asyncio
import json
import re
from copy import deepcopy
from pathlib import Path

import pytest

from events_commit_619 import (
    AtomicOutboxProfile,
    BoundaryCapture,
    CommittedEnqueueFailure,
    EnqueueUnavailable,
    Occurrence,
    RecordingUnavailable,
    TransportCapture,
    commit_interaction,
)


ROOT = Path(__file__).resolve().parents[2]
TIME = "2025-09-01T12:01:02Z"
CONTEXT = {"occurred_at": TIME, "correlation_id": "interaction-619"}
INITIAL = {"/": {"epoch": 4, "name": "old"}}


def _registry_mutation(state):
    example = (ROOT / "core" / "events.md").read_text(encoding="utf-8").split(
        "### Update a Registry attribute\n", 1
    )[1].split("\n### ", 1)[0]
    assert "`PATCH /`" in example
    request = json.loads(re.search(r"Body: `([^`]+)`", example)[1])
    changed = {key for key, value in request.items() if state["/"].get(key) != value}
    state["/"].update(request)
    state["/"]["epoch"] += 1
    state["/"]["modifiedat"] = TIME
    return [
        Occurrence("registry", "updated", "/", frozenset(changed | {"epoch", "modifiedat"}))
    ]


def test_events_619_registry_example_is_visible_only_after_commit():
    capture, transport = BoundaryCapture(INITIAL), TransportCapture()
    observations = []

    def render(staged):
        observations.append(deepcopy(capture.committed.state))
        assert transport.enqueued == transport.delivered == []
        assert staged["/"]["name"] == "foo"
        return deepcopy(staged["/"])

    class ObservingTransport(TransportCapture):
        def enqueue(self, events):
            assert capture.committed.state["/"]["name"] == "foo"
            assert events[0]["data"]["epoch"] == capture.committed.state["/"]["epoch"]
            super().enqueue(events)

    transport = ObservingTransport()
    response = commit_interaction(
        capture, _registry_mutation, render, transport, **CONTEXT
    )
    assert observations == [INITIAL]
    assert response == {"epoch": 5, "name": "foo", "modifiedat": TIME}
    assert transport.enqueued == [{
        "type": "io.xregistry.registry.updated",
        "subject": "/",
        "time": TIME,
        "xregcorrelationid": "interaction-619",
        "data": {"epoch": 5, "changed": ["epoch", "modifiedat", "name"]},
    }]
    assert capture.committed.outbox == ()
    assert transport.delivered == []
    first_event = deepcopy(transport.enqueued[0])

    def later_mutation(staged):
        occurrences = _registry_mutation(staged)
        staged["/"]["modifiedat"] = "2025-09-01T12:02:02Z"
        return occurrences

    commit_interaction(
        capture, later_mutation, deepcopy, transport,
        occurred_at="2025-09-01T12:02:02Z", correlation_id="next-interaction-619",
    )
    assert capture.committed.state["/"]["epoch"] == 6
    assert transport.enqueued[0] == first_event
    transport.deliver()
    assert transport.enqueued == []
    assert transport.delivered[0] == first_event
    assert transport.delivered[1]["data"]["epoch"] == 6


@pytest.mark.parametrize(
    "failure, error, message",
    [
        ("validation", ValueError, "unsigned epoch"),
        ("response-inlining", KeyError, "/dirs/missing"),
        ("response-size", OverflowError, "response-size"),
        ("cancellation", asyncio.CancelledError, "cancellation"),
    ],
)
def test_events_619_precommit_failure_leaves_state_and_events_invisible(failure, error, message):
    capture, transport = BoundaryCapture(INITIAL), TransportCapture()
    before = deepcopy(capture.committed)

    def mutate(staged):
        occurrences = _registry_mutation(staged)
        if failure == "validation":
            staged["/"]["epoch"] = -1
            if staged["/"]["epoch"] < 0:
                raise ValueError("an unsigned epoch is needed")
        return occurrences

    def render(staged):
        assert staged["/"]["epoch"] == 5
        assert capture.committed == before
        assert transport.enqueued == []
        if failure == "response-inlining":
            return deepcopy(staged["/dirs/missing"])
        if failure == "response-size":
            limit = len(json.dumps(INITIAL).encode("utf-8"))
            encoded = json.dumps(staged).encode("utf-8")
            if len(encoded) > limit:
                raise OverflowError("response-size limit exceeded")
            return encoded
        raise asyncio.CancelledError("cancellation")

    with pytest.raises(error, match=message):
        commit_interaction(capture, mutate, render, transport, **CONTEXT)
    assert capture.committed == before
    assert transport.enqueued == transport.delivered == []


def test_events_619_unprofiled_enqueue_failure_is_reported_after_commit():
    capture, transport = BoundaryCapture(INITIAL), TransportCapture(False)
    with pytest.raises(CommittedEnqueueFailure, match="state committed") as failure:
        commit_interaction(capture, _registry_mutation, deepcopy, transport, **CONTEXT)
    assert failure.value.committed is True
    assert isinstance(failure.value.__cause__, EnqueueUnavailable)
    assert failure.value.events[0]["data"]["epoch"] == 5
    assert capture.committed.state["/"] == {
        "epoch": 5, "name": "foo", "modifiedat": TIME,
    }
    assert capture.committed.outbox == ()
    assert transport.enqueued == transport.delivered == []


def test_events_619_atomic_profile_record_failure_rolls_back_both_records():
    capture, transport = BoundaryCapture(INITIAL), TransportCapture()
    before = deepcopy(capture.committed)
    with pytest.raises(RecordingUnavailable, match="profile event recording"):
        commit_interaction(
            capture, _registry_mutation, deepcopy, transport,
            profile=AtomicOutboxProfile(False), **CONTEXT,
        )
    assert capture.committed == before
    assert transport.enqueued == transport.delivered == []


def test_events_619_unknown_profile_is_not_a_successful_fallback():
    capture, transport = BoundaryCapture(INITIAL), TransportCapture()
    before = deepcopy(capture.committed)
    with pytest.raises(ValueError, match="explicit supported profile"):
        commit_interaction(
            capture, _registry_mutation, deepcopy, transport,
            profile="unspecified-guarantees", **CONTEXT,
        )
    assert capture.committed == before
    assert transport.enqueued == transport.delivered == []


def test_events_619_explicit_profile_records_before_separate_dispatch():
    capture, transport = BoundaryCapture(INITIAL), TransportCapture(False)
    commit_interaction(
        capture, _registry_mutation, deepcopy, transport,
        profile=AtomicOutboxProfile(), **CONTEXT,
    )
    committed = deepcopy(capture.committed)
    assert committed.state["/"]["epoch"] == 5
    assert len(committed.outbox) == 1
    assert committed.outbox[0]["data"]["epoch"] == committed.state["/"]["epoch"]
    assert transport.enqueued == transport.delivered == []
    with pytest.raises(EnqueueUnavailable, match="transport enqueue"):
        transport.enqueue(committed.outbox)
    assert capture.committed == committed
    transport.enqueue_available = True
    transport.enqueue(committed.outbox)
    assert transport.enqueued == list(committed.outbox)
    assert transport.delivered == []
    transport.deliver()
    assert transport.delivered == list(committed.outbox)


def test_events_619_implicit_parent_example_coalesces_final_state():
    text = (ROOT / "core" / "events.md").read_text(encoding="utf-8")
    example = text.split("### Create a tree of entities\n", 1)[1].split("\n### ", 1)[0]
    path = re.search(r"`PUT ([^`]+)`", example)[1]
    assert json.loads(re.search(r"Body: `([^`]+)`", example)[1]) == {}
    expected_types = re.findall(r"  - `(io\.xregistry\.[^`]+)`", example)
    version = path
    resource = path.rsplit("/versions/", 1)[0]
    group = resource.rsplit("/files/", 1)[0]
    capture, transport = BoundaryCapture({"/": {"epoch": 1}}), TransportCapture()

    def mutate(staged):
        staged.update({
            "/": {"epoch": 2},
            group: {"epoch": 1},
            resource: {"epoch": 1, "meta": {"epoch": 1}},
            version: {"epoch": 1},
        })
        return [
            Occurrence("registry", "updated", "/", frozenset({"dirs", "dirscount"})),
            Occurrence("registry", "updated", "/", frozenset({"epoch", "modifiedat"})),
            Occurrence("group", "created", group),
            Occurrence("group", "updated", group, frozenset({"files", "filescount"})),
            Occurrence("resource", "created", resource),
            Occurrence("resource", "updated", resource, frozenset({"versionscount"})),
            Occurrence("version", "created", version),
            Occurrence("version", "updated", version, frozenset({"epoch"})),
        ]

    commit_interaction(capture, mutate, deepcopy, transport, **CONTEXT)
    assert len(transport.enqueued) == len(expected_types) == 4
    assert {event["type"] for event in transport.enqueued} == set(expected_types)
    assert {event["subject"] for event in transport.enqueued} == {"/", group, resource, version}
    for event in transport.enqueued:
        assert event["data"]["epoch"] == capture.committed.state[event["subject"]]["epoch"]
        assert event["time"] == TIME
        assert event["xregcorrelationid"] == CONTEXT["correlation_id"]
        if event["type"].endswith(".created"):
            assert "changed" not in event["data"]
    root = next(event for event in transport.enqueued if event["subject"] == "/")
    assert set(root["data"]["changed"]) == {"dirs", "dirscount", "epoch", "modifiedat"}
    resource_event = next(event for event in transport.enqueued if event["subject"] == resource)
    assert resource_event["data"]["meta.epoch"] == 1


def test_events_619_cascade_deletion_overrides_updates_without_duplicate_events():
    group = "/dirs/d1"
    resource = f"{group}/files/f1"
    version = f"{resource}/versions/v1"
    capture = BoundaryCapture({
        "/": {"epoch": 4}, group: {"epoch": 1},
        resource: {"epoch": 1, "meta": {"epoch": 1}}, version: {"epoch": 1},
    })
    transport = TransportCapture()

    def mutate(staged):
        staged.clear()
        staged["/"] = {"epoch": 5}
        occurrences = [Occurrence("registry", "updated", "/", frozenset({"dirs", "dirscount"}))]
        for entity, subject in (("group", group), ("resource", resource), ("version", version)):
            occurrences.extend([
                Occurrence(entity, "updated", subject, frozenset({"name"})),
                Occurrence(entity, "deleted", subject),
                Occurrence(entity, "deleted", subject),
            ])
        return occurrences

    commit_interaction(capture, mutate, deepcopy, transport, **CONTEXT)
    assert capture.committed.state == {"/": {"epoch": 5}}
    assert {(event["type"], event["subject"]) for event in transport.enqueued} == {
        ("io.xregistry.registry.updated", "/"),
        ("io.xregistry.group.deleted", group),
        ("io.xregistry.resource.deleted", resource),
        ("io.xregistry.version.deleted", version),
    }
    assert len(transport.enqueued) == 4
    assert all("data" not in event for event in transport.enqueued if event["subject"] != "/")


def test_events_619_deprecation_coalesces_separately_from_updated_event():
    group = "/dirs/d1"
    capture, transport = BoundaryCapture({group: {"epoch": 1}}), TransportCapture()

    def mutate(staged):
        staged[group] = {"epoch": 3, "deprecated": {}}
        return [
            Occurrence("group", "updated", group, frozenset({"epoch", "modifiedat"})),
            Occurrence("group", "deprecated", group),
            Occurrence("group", "updated", group, frozenset({"deprecated"})),
            Occurrence("group", "deprecated", group),
        ]

    commit_interaction(capture, mutate, deepcopy, transport, **CONTEXT)
    assert len(transport.enqueued) == 2
    updated = next(event for event in transport.enqueued if event["type"].endswith(".updated"))
    deprecated = next(event for event in transport.enqueued if event["type"].endswith(".deprecated"))
    assert updated["data"] == {"epoch": 3, "changed": ["deprecated", "epoch", "modifiedat"]}
    assert "data" not in deprecated
    assert updated["subject"] == deprecated["subject"] == group


def test_events_619_spec_separates_commit_enqueue_and_delivery_guarantees():
    text = " ".join((ROOT / "core" / "events.md").read_text(encoding="utf-8").split())
    assert "MUST NOT expose them as successful-state notifications before the interaction commits" in text
    assert "does not require durable enqueue to be part of commitment" in text
    assert "MUST be defined by an explicit profile" in text
    assert "exactly-once delivery, durable replay, ordering between parent and child events" in text
    assert "Event data describes the state at the end of that committed interaction" in text
