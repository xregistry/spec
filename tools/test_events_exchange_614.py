import json
import re
from copy import deepcopy
from datetime import timezone
from email.utils import format_datetime, parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from test_samples import _unique_json_object


ROOT = Path(__file__).resolve().parents[1]
PATCH_EXAMPLES = (
    "Update a Resource attribute (a default Version attribute)",
    "Update a Version attribute (the default Version)",
    "Update a Version attribute (not the default Version)",
)


def _text():
    return (ROOT / "core" / "events.md").read_text(encoding="utf-8")


def _json(value):
    return json.loads(value, object_pairs_hook=_unique_json_object)


def _section(title):
    return _text().split(f"### {title}\n", 1)[1].split("\n### ", 1)[0]


def _model():
    section = _text().split("## Sample xRegistry Interactions\n", 1)[1]
    return _json(re.search(r"```yaml\n(.*?)\n```", section, re.S)[1])


def _base():
    section = _text().split("## Sample xRegistry Interactions\n", 1)[1]
    return re.search(r"base URL `([^`]+)`", section)[1]


def _patch_example(title):
    section = _section(title)
    path = re.search(r"`PATCH ([^`]+)`", section)[1]
    body = _json(re.search(r"Body: `([^`]+)`", section)[1])
    events = re.findall(
        r"  - `(io\.xregistry\.[^`]+)`\n    - `subject`: `([^`]+)`", section
    )
    return path, body, events


def _message(block):
    head, body = block.split("\n\n", 1)
    start, *lines = head.splitlines()
    headers = {}
    for line in lines:
        key, value = line.split(":", 1)
        key = key.lower()
        assert key not in headers, f"duplicate HTTP header: {key}"
        headers[key] = value.strip()
    return start, headers, _json(body)


def _exchange():
    section = _section("Creating a Group with a complete client HTTP message exchange")
    blocks = re.findall(r"```yaml\n(.*?)\n```", section, re.S)
    assert len(blocks) == 4
    return _message(blocks[0]), _message(blocks[1]), [_json(block) for block in blocks[2:]]


class _PatchCapture:
    def __init__(self, model):
        self.model = model
        self.base = _base()
        self.versions = {
            version: {
                "epoch": epoch, "name": "before",
                "modifiedat": "2025-09-01T12:00:00Z",
            }
            for version, epoch in (("v1", 3), ("v2", 8))
        }
        self.default = "v1"
        self.meta_epoch = 7
        self.now = "2025-09-01T12:01:02Z"
        self.events = []

    def patch(self, path, body):
        details = path.endswith("$details")
        canonical = path.removesuffix("$details")
        parts = canonical.strip("/").split("/")
        resource_model = self.model["groups"][parts[0]]["resources"][parts[2]]
        hasdocument = resource_model.get("hasdocument", True)
        if hasdocument and not details:
            raise ValueError("details_required")
        assert len(parts) in (4, 6)
        if len(parts) == 6:
            assert parts[4] == "versions"
        version = self.default if len(parts) == 4 else parts[5]
        changed = {key for key, value in body.items() if self.versions[version].get(key) != value}
        self.versions[version].update(body)
        self.versions[version]["epoch"] += 1
        self.versions[version]["modifiedat"] = self.now
        data = {
            "epoch": self.versions[version]["epoch"],
            "changed": sorted(changed | {"epoch", "modifiedat"}),
        }
        resource = "/" + "/".join(parts[:4])
        if version == self.default:
            self.events.append({
                "type": "io.xregistry.resource.updated", "subject": resource,
                "data": {**deepcopy(data), "meta.epoch": self.meta_epoch},
            })
        self.events.append({
            "type": "io.xregistry.version.updated",
            "subject": f"{resource}/versions/{version}", "data": data,
        })
        suffix = "$details" if hasdocument else ""
        return {"self": self.base + canonical + suffix}


def _put_group(model, groups, path, body, base, instant):
    collection, group_id = path.strip("/").split("/")
    group_model = model["groups"][collection]
    previous = groups.get(group_id)
    created = previous is None
    timestamp = instant.isoformat().replace("+00:00", "Z")
    result = {
        f"{group_model['singular']}id": group_id,
        "self": base + path,
        "xid": path,
        "epoch": 1 if created else previous["epoch"] + 1,
        "createdat": timestamp if created else previous["createdat"],
        "modifiedat": timestamp,
    }
    result.update(body)
    for resource_collection in group_model["resources"]:
        result[f"{resource_collection}url"] = f"{base}{path}/{resource_collection}"
        result[f"{resource_collection}count"] = 0
    groups[group_id] = deepcopy(result)
    headers = {"location": result["self"]} if created else {}
    return (201 if created else 200), headers, result


def test_events_614_sample_model_is_explicitly_metadata_only():
    assert _model()["groups"]["dirs"]["resources"]["files"]["hasdocument"] is False


@pytest.mark.parametrize("title", PATCH_EXAMPLES)
def test_events_614_actual_metadata_patches_match_state_and_event_subjects(title):
    path, body, expected = _patch_example(title)
    capture = _PatchCapture(_model())
    before = deepcopy(capture.versions)
    response = capture.patch(path, body)
    assert [(event["type"], event["subject"]) for event in capture.events] == expected
    version = path.rsplit("/", 1)[-1] if "/versions/" in path else capture.default
    assert capture.versions[version]["name"] == body["name"] == "foo"
    assert capture.versions[version]["epoch"] == before[version]["epoch"] + 1
    assert capture.versions[version]["modifiedat"] == capture.now
    for other in before.keys() - {version}:
        assert capture.versions[other] == before[other]
    for event in capture.events:
        assert event["data"]["epoch"] == capture.versions[version]["epoch"]
        assert set(event["data"]["changed"]) == {"epoch", "modifiedat", *body}
        if event["type"] == "io.xregistry.resource.updated":
            assert event["data"]["meta.epoch"] == 7
    assert response["self"] == _base() + path


@pytest.mark.parametrize("title", PATCH_EXAMPLES)
@pytest.mark.parametrize("explicit", [True, False], ids=["explicit-document", "default-document"])
def test_events_614_raw_document_patch_is_rejected_without_state_or_events(title, explicit):
    path, body, _ = _patch_example(title)
    model = _model()
    resource_model = model["groups"]["dirs"]["resources"]["files"]
    if explicit:
        resource_model["hasdocument"] = True
    else:
        resource_model.pop("hasdocument", None)
    capture = _PatchCapture(model)
    before = deepcopy(capture.versions)
    with pytest.raises(ValueError, match="details_required"):
        capture.patch(path, body)
    assert capture.versions == before
    assert capture.events == []


@pytest.mark.parametrize("title", PATCH_EXAMPLES)
@pytest.mark.parametrize("hasdocument", [True, False])
def test_events_614_details_variant_preserves_model_dependent_response_urls(title, hasdocument):
    path, body, expected = _patch_example(title)
    model = _model()
    model["groups"]["dirs"]["resources"]["files"]["hasdocument"] = hasdocument
    capture = _PatchCapture(model)
    response = capture.patch(path + "$details", body)
    assert [(event["type"], event["subject"]) for event in capture.events] == expected
    assert response["self"] == _base() + path + ("$details" if hasdocument else "")


def test_events_614_complete_group_exchange_matches_creation_capture():
    request, response, events = _exchange()
    method, path, *protocol = request[0].split()
    assert method == "PUT"
    assert protocol == ["HTTP/1.1"]
    assert request[1]["content-type"] == response[1]["content-type"] == "application/json"
    assert request[2] == {}
    instant = parsedate_to_datetime(response[1]["date"]).astimezone(timezone.utc)
    assert format_datetime(instant, usegmt=True) == response[1]["date"]
    base = _base()
    assert urlsplit(base).scheme in {"http", "https"}
    assert urlsplit(base).netloc == request[1]["host"]
    assert urlsplit(base).path == ""
    groups = {}
    status, headers, body = _put_group(_model(), groups, path, request[2], base, instant)
    assert response[0] == f"HTTP/1.1 {status} Created"
    assert response[1]["location"] == headers["location"] == body["self"]
    assert response[2] == body == groups["d1"]
    assert body["filescount"] == 0
    assert body["filesurl"] == body["self"] + "/files"
    assert body["xid"] == path
    assert body["epoch"] == 1
    assert len(events) == len({event["id"] for event in events}) == 2
    assert {event["type"] for event in events} == {
        "io.xregistry.registry.updated", "io.xregistry.group.created",
    }
    for event in events:
        assert event["specversion"] == "1.0"
        assert event["source"] == base
        assert event["time"] == body["createdat"] == body["modifiedat"]
        assert event["xregcorrelationid"] == response[1]["xregistry-xregcorrelationid"]
    group = next(event for event in events if event["type"] == "io.xregistry.group.created")
    registry = next(event for event in events if event["type"] == "io.xregistry.registry.updated")
    assert base + group["subject"] == response[1]["location"]
    assert group["data"] == {"epoch": body["epoch"]}
    assert registry["subject"] == "/"
    precondition = _section("Creating a Group with a complete client HTTP message exchange")
    initial_epoch = int(re.search(r"Registry's `epoch` is (\d+)", precondition)[1])
    assert registry["data"]["epoch"] == initial_epoch + len(groups)
    assert set(registry["data"]["changed"]) == {"dirs", "dirscount", "epoch", "modifiedat"}


def test_events_614_existing_group_update_stays_200_without_location():
    request, response, events = _exchange()
    path = request[0].split()[1]
    instant = parsedate_to_datetime(response[1]["date"]).astimezone(timezone.utc)
    base = _base()
    groups = {}
    _put_group(_model(), groups, path, request[2], base, instant)
    before = deepcopy(groups["d1"])
    status, headers, body = _put_group(_model(), groups, path, {"name": "renamed"}, base, instant)
    assert status == 200
    assert headers == {}
    assert body["name"] == "renamed"
    assert body["epoch"] == before["epoch"] + 1
    assert body["self"] == before["self"]
    assert body["createdat"] == before["createdat"]
    assert set(groups) == {"d1"}
