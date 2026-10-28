"""Independent mutations of authored bytes and publication state transitions."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import jsonschema
import pytest

from workingdrafts.publication.tools.publication_examples import (
    Channels, PublicationError, SCHEMA, check_snapshot, open_context, open_package, validate,
)


ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"


@pytest.fixture
def publication():
    objects = {
        "https://content.example.test/" + path.name: path.read_bytes()
        for path in SAMPLES.glob("*") if path.suffix in (".json", ".txt")
    }
    context = json.loads((SAMPLES / "open.json").read_text(encoding="utf-8"))
    return context, objects


def replace(objects, pin, value):
    raw = (json.dumps(value, indent=2) + "\n").encode()
    objects[pin["url"]] = raw
    return {**pin, "digest": "sha256:" + hashlib.sha256(raw).hexdigest(), "size": len(raw)}


def test_checked_authored_bytes_and_context(publication):
    context, objects = publication
    jsonschema.Draft202012Validator.check_schema(SCHEMA)
    result = open_context(context, objects)
    assert result["documents"][0]["viewVersion"] == "/sets/manual/documents/intro/versions/7"
    validate("channel", json.loads((SAMPLES / "channel.json").read_text(encoding="utf-8")))


@pytest.mark.parametrize("mutation", ["bytes", "missing"])
def test_corrupt_or_unavailable_content_fails(publication, mutation):
    context, objects = publication
    manifest = json.loads(objects[context["snapshot"]["url"]])
    content = manifest["documents"][0]["content"]
    if mutation == "bytes":
        objects[content["url"]] = b"X" * content["size"]
    else:
        del objects[content["url"]]
    with pytest.raises(PublicationError) as caught:
        open_context(context, objects)
    assert caught.value.code == ("unavailable" if mutation == "missing" else "integrity_error")


@pytest.mark.parametrize("field,value", [
    ("scope", "urn:another:scope"),
])
def test_context_cannot_claim_a_different_manifest_state(publication, field, value):
    context, objects = publication
    context[field] = value
    with pytest.raises(PublicationError, match=field):
        open_context(context, objects)


def test_rehashed_invalid_graph_fails(publication):
    context, objects = publication
    pin = context["snapshot"]
    manifest = json.loads(objects[pin["url"]])
    registry_pin = manifest["registry"]
    registry = json.loads(objects[registry_pin["url"]])
    registry["sets"]["manual"]["documents"]["intro"]["meta"]["defaultversionid"] = "99"
    manifest["registry"] = replace(objects, registry_pin, registry)
    new_pin = replace(objects, pin, manifest)
    with pytest.raises(PublicationError) as caught:
        check_snapshot(new_pin, objects)
    assert caught.value.code == "invalid_package"


def test_unsupported_required_extension_fails(publication):
    context, objects = publication
    pin = context["snapshot"]
    manifest = json.loads(objects[pin["url"]])
    manifest["requiredExtensions"] = ["urn:example:unknown-closure"]
    new_pin = replace(objects, pin, manifest)
    with pytest.raises(PublicationError) as caught:
        check_snapshot(new_pin, objects)
    assert caught.value.code == "unsupported_operation"


def test_fork_promotion_rollback_and_stale_writer(publication):
    context, objects = publication
    first = context["snapshot"]
    manifest = json.loads(objects[first["url"]])
    manifest["parent"] = deepcopy(first)
    second = replace(objects, {**first, "url": "https://content.example.test/next.json"}, manifest)
    channels = Channels()
    channels.create("stable", context["scope"], first, objects)
    channels.create("preview", context["scope"], first, objects)
    channels.move("preview", 1, second, objects)
    assert channels.records["stable"]["head"] == first
    channels.move("stable", 1, second, objects)
    with pytest.raises(PublicationError) as caught:
        channels.move("stable", 1, first, objects)
    assert caught.value.code == "mismatched_epoch"
    assert channels.records["stable"]["head"] == second
    channels.move("stable", 2, first, objects)
    assert channels.records["stable"] == {"scope": context["scope"], "head": first, "epoch": 3}
    assert check_snapshot(second, objects)["parent"] == first
    assert check_snapshot(first, objects)["documents"] == manifest["documents"]


def test_package_replays_offline_without_network():
    result = open_package(SAMPLES)
    assert result["scope"] == "urn:example:manual-publication"
    assert result["completeness"] == "offline-complete"


def test_wrong_scope_head_preserves_channel(publication):
    context, objects = publication
    channels = Channels()
    pin = context["snapshot"]
    channels.create("stable", context["scope"], pin, objects)
    manifest = json.loads(objects[pin["url"]])
    manifest["scope"] = "urn:another:scope"
    other = replace(objects, {**pin, "url": "https://content.example.test/other.json"}, manifest)
    before = deepcopy(channels.records)
    with pytest.raises(PublicationError, match="scope"):
        channels.move("stable", 1, other, objects)
    assert channels.records == before
