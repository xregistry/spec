import json
import re
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import pytest

from test_samples import _unique_json_object


ROOT = Path(__file__).resolve().parents[1]
NOW = "2030-12-18T00:00:00Z"


def _primer_section():
    text = (ROOT / "core" / "primer.md").read_text(encoding="utf-8")
    return text.split("### 11.25. Deprecation of entities in an xRegistry\n", 1)[1].split(
        "\n### 11.26.", 1
    )[0]


def _examples():
    blocks = re.findall(r"```yaml\n(.*?)\n```", _primer_section(), re.S)
    assert len(blocks) == 2
    return dict(zip(
        ("group", "resource"),
        (json.loads(block, object_pairs_hook=_unique_json_object) for block in blocks),
    ))


def _actions(entity):
    text = (ROOT / "core" / "events.md").read_text(encoding="utf-8")
    section = text.split(f"### `{entity}` Events\n", 1)[1].split("\n##", 1)[0]
    return set(re.findall(r"- Action: `([^`]+)`", section))


def _instant(value):
    instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if instant.utcoffset() is None:
        raise ValueError("deprecation timestamps need a time zone")
    return instant


class _DeprecationCapture:
    def __init__(self, entity, snapshot):
        if entity not in {"group", "resource"}:
            raise ValueError("only Group and Resource deprecation is built in")
        self.entity = entity
        self.snapshot = deepcopy(snapshot)
        self.events = []

    def _metadata(self):
        return self.snapshot if self.entity == "group" else self.snapshot["meta"]

    def change(self, value):
        if value is not None:
            if not isinstance(value, dict):
                raise ValueError("deprecated metadata must be an object")
            if "effective" in value:
                _instant(value["effective"])
            if "removal" in value:
                removal = _instant(value["removal"])
                if "effective" in value and removal < _instant(value["effective"]):
                    raise ValueError("removal precedes effective")
        metadata = self._metadata()
        if value is None:
            del metadata["deprecated"]
        else:
            metadata["deprecated"] = deepcopy(value)
        metadata["epoch"] += 1
        metadata["modifiedat"] = NOW
        prefix = "" if self.entity == "group" else "meta."
        data = {
            "epoch": self.snapshot["epoch"],
            "changed": [
                prefix + "epoch", prefix + "modifiedat", prefix + "deprecated",
            ],
        }
        if self.entity == "resource":
            data["meta.epoch"] = metadata["epoch"]
        self.events.extend([
            {
                "type": f"io.xregistry.{self.entity}.deprecated",
                "subject": self.snapshot["xid"],
            },
            {
                "type": f"io.xregistry.{self.entity}.updated",
                "subject": self.snapshot["xid"],
                "data": data,
            },
        ])

    def deprecated_at(self, now):
        metadata = self._metadata()
        if "deprecated" not in metadata:
            return False
        effective = metadata["deprecated"].get("effective")
        return effective is None or _instant(now) >= _instant(effective)


def _capture(entity):
    if entity == "group":
        return _DeprecationCapture("group", {
            "dirid": "d1", "xid": "/dirs/d1", "epoch": 4,
            "files": {"f1": {"meta": {"epoch": 7}, "versions": {"v1": {"epoch": 2}}}},
        })
    return _DeprecationCapture("resource", {
        "fileid": "f1", "xid": "/dirs/d1/files/f1", "epoch": 2,
        "meta": {"epoch": 7}, "versions": {"v1": {"epoch": 2}},
    })


def _deprecation(example, entity):
    return example["deprecated"] if entity == "group" else example["meta"]["deprecated"]


def test_primer_611_examples_use_existing_builtin_locations():
    examples = _examples()
    assert set(examples["group"]) == {"deprecated"}
    assert set(examples["resource"]) == {"meta"}
    assert set(examples["resource"]["meta"]) == {"deprecated"}
    assert examples["group"]["deprecated"] == {}
    core = " ".join((ROOT / "core" / "spec.md").read_text(encoding="utf-8").split())
    assert "This attribute can appear on Groups and Resources" in core
    assert "Neither requires a model extension" in " ".join(_primer_section().split())


@pytest.mark.parametrize("entity", ["group", "resource"])
def test_primer_611_example_mutations_use_existing_event_matrix(entity):
    value = _deprecation(_examples()[entity], entity)
    capture = _capture(entity)
    before = deepcopy(capture.snapshot)
    capture.change(value)
    assert {event["type"] for event in capture.events} == {
        f"io.xregistry.{entity}.deprecated", f"io.xregistry.{entity}.updated",
    }
    assert len(capture.events) == 2
    assert all(event["type"].rsplit(".", 1)[1] in _actions(entity) for event in capture.events)
    assert all(event["subject"] == before["xid"] for event in capture.events)
    metadata = capture.snapshot if entity == "group" else capture.snapshot["meta"]
    old_metadata = before if entity == "group" else before["meta"]
    assert metadata["epoch"] == old_metadata["epoch"] + 1
    assert metadata["deprecated"] == value
    assert metadata["modifiedat"] == NOW
    updated = next(event for event in capture.events if event["type"].endswith(".updated"))
    assert updated["data"]["epoch"] == capture.snapshot["epoch"]
    if entity == "resource":
        assert updated["data"]["meta.epoch"] == metadata["epoch"]
    else:
        assert "meta.epoch" not in updated["data"]
    assert capture.deprecated_at(NOW) is (entity == "group")
    child_key = "files" if entity == "group" else "versions"
    assert capture.snapshot[child_key] == before[child_key]
    if entity == "resource":
        assert capture.snapshot["epoch"] == before["epoch"]


@pytest.mark.parametrize("entity", ["group", "resource"])
def test_primer_611_future_clock_boundary_does_not_add_notifications(entity):
    value = _examples()["resource"]["meta"]["deprecated"]
    capture = _capture(entity)
    capture.change(value)
    before = deepcopy(capture.snapshot)
    notifications = deepcopy(capture.events)
    effective = value["effective"]
    assert capture.deprecated_at(NOW) is False
    assert capture.deprecated_at("2030-12-18T23:59:59Z") is False
    assert capture.deprecated_at(effective) is True
    assert capture.deprecated_at("2030-12-19T00:00:01Z") is True
    assert capture.snapshot == before
    assert capture.events == notifications


@pytest.mark.parametrize("entity", ["group", "resource"])
def test_primer_611_metadata_change_and_removal_notify_without_version_events(entity):
    capture = _capture(entity)
    value = deepcopy(_examples()["resource"]["meta"]["deprecated"])
    capture.change(value)
    value["documentation"] = "https://example.com/deprecation"
    capture.change(value)
    assert capture.deprecated_at(NOW) is False
    capture.change(None)
    assert capture.deprecated_at(NOW) is False
    assert len(capture.events) == 6
    prefix = "" if entity == "group" else "meta."
    epoch_key = "epoch" if entity == "group" else "meta.epoch"
    start_epoch = 4 if entity == "group" else 7
    assert [event["data"][epoch_key] for event in capture.events[1::2]] == [
        start_epoch + 1, start_epoch + 2, start_epoch + 3,
    ]
    for event in capture.events:
        if event["type"].endswith(".deprecated"):
            assert "data" not in event
        else:
            assert event["type"] == f"io.xregistry.{entity}.updated"
            assert set(event["data"]["changed"]) == {
                prefix + "epoch", prefix + "modifiedat", prefix + "deprecated",
            }
    metadata = capture.snapshot if entity == "group" else capture.snapshot["meta"]
    assert "deprecated" not in metadata
    assert "deprecated" not in _actions("version")


@pytest.mark.parametrize(
    "value, error",
    [
        (True, "must be an object"),
        ({"effective": "2030-12-19T00:00:00"}, "time zone"),
        ({
            "effective": "2030-12-19T00:00:00Z",
            "removal": "2030-12-18T00:00:00Z",
        }, "removal precedes effective"),
    ],
)
def test_primer_611_invalid_metadata_cannot_publish_success(value, error):
    capture = _capture("resource")
    before = deepcopy(capture.snapshot)
    with pytest.raises(ValueError, match=error):
        capture.change(value)
    assert capture.snapshot == before
    assert capture.events == []


def test_primer_611_version_deprecation_remains_a_custom_design():
    assert "deprecated" not in _actions("version")
    with pytest.raises(ValueError, match="only Group and Resource"):
        _DeprecationCapture("version", {"epoch": 1})
    text = " ".join(_primer_section().split())
    assert "Version-level deprecation remains a possible custom-model extension" in text
    assert "does not introduce a standard `io.xregistry.version.deprecated` event" in text
