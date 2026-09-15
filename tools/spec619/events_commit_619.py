"""An in-memory capture of separate commit, enqueue, and delivery boundaries."""

from copy import deepcopy
from dataclasses import dataclass


class RecordingUnavailable(RuntimeError):
    pass


class EnqueueUnavailable(RuntimeError):
    pass


class CommittedEnqueueFailure(RuntimeError):
    def __init__(self, events):
        super().__init__("state committed, but notification enqueue failed")
        self.committed = True
        self.events = deepcopy(events)


@dataclass(frozen=True)
class Occurrence:
    entity: str
    action: str
    subject: str
    changed: frozenset = frozenset()


@dataclass(frozen=True)
class AtomicOutboxProfile:
    recording_available: bool = True


@dataclass(frozen=True)
class CommittedCapture:
    state: dict
    outbox: tuple = ()


class BoundaryCapture:
    def __init__(self, state):
        self.committed = CommittedCapture(deepcopy(state))


class TransportCapture:
    def __init__(self, enqueue_available=True):
        self.enqueue_available = enqueue_available
        self.enqueued = []
        self.delivered = []

    def enqueue(self, events):
        if not self.enqueue_available:
            raise EnqueueUnavailable("transport enqueue is unavailable")
        self.enqueued.extend(deepcopy(events))

    def deliver(self):
        self.delivered.extend(deepcopy(self.enqueued))
        self.enqueued.clear()


def _final_events(occurrences, state, occurred_at, correlation_id):
    priority = {"updated": 0, "created": 1, "deleted": 2}
    selected = {}
    for occurrence in occurrences:
        if occurrence.action not in {*priority, "deprecated"}:
            raise ValueError("unsupported occurrence action")
        key = (occurrence.subject, occurrence.action == "deprecated")
        previous = selected.get(key)
        if previous is None:
            selected[key] = occurrence
            continue
        if previous.entity != occurrence.entity:
            raise ValueError("one subject cannot have different entity types")
        action = previous.action
        if occurrence.action != "deprecated":
            action = max((action, occurrence.action), key=priority.__getitem__)
        selected[key] = Occurrence(
            occurrence.entity,
            action,
            occurrence.subject,
            previous.changed | occurrence.changed,
        )

    events = []
    for occurrence in selected.values():
        event = {
            "type": f"io.xregistry.{occurrence.entity}.{occurrence.action}",
            "subject": occurrence.subject,
            "time": occurred_at,
            "xregcorrelationid": correlation_id,
        }
        if occurrence.action in {"created", "updated"}:
            final = state[occurrence.subject]
            data = {"epoch": final["epoch"]}
            if occurrence.entity == "resource":
                data["meta.epoch"] = final["meta"]["epoch"]
            if occurrence.action == "updated":
                data["changed"] = sorted(occurrence.changed)
            event["data"] = data
        events.append(event)
    return events


def commit_interaction(
    capture, mutate, render, transport, *, occurred_at, correlation_id, profile=None
):
    staged = deepcopy(capture.committed.state)
    occurrences = mutate(staged)
    response = render(staged)
    events = _final_events(occurrences, staged, occurred_at, correlation_id)

    if profile is not None:
        if not isinstance(profile, AtomicOutboxProfile):
            raise ValueError("an explicit supported profile is needed")
        if not profile.recording_available:
            raise RecordingUnavailable("profile event recording is unavailable")
        outbox = capture.committed.outbox + tuple(deepcopy(events))
    else:
        outbox = capture.committed.outbox

    # One replacement models a logical atomic boundary, not durable storage.
    capture.committed = CommittedCapture(deepcopy(staged), outbox)
    if profile is None:
        try:
            transport.enqueue(events)
        except EnqueueUnavailable as error:
            raise CommittedEnqueueFailure(events) from error
    return response
