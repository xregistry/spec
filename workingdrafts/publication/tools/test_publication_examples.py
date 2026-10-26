"""Independent mutations of authored bytes and publication state transitions."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

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
    content = result["documents"][0]["content"]
    assert objects[content["url"]] == (SAMPLES / "intro.txt").read_bytes()
    validate("channel", json.loads((SAMPLES / "channel.json").read_text(encoding="utf-8")))


@pytest.mark.parametrize("mutation", ["bytes", "size", "missing"])
def test_corrupt_or_unavailable_content_fails(publication, mutation):
    context, objects = publication
    manifest = json.loads(objects[context["snapshot"]["url"]])
    content = manifest["documents"][0]["content"]
    if mutation == "bytes":
        objects[content["url"]] = b"X" * content["size"]
    elif mutation == "size":
        objects[content["url"]] += b"\n"
    else:
        del objects[content["url"]]
    with pytest.raises(PublicationError) as caught:
        open_context(context, objects)
    assert caught.value.code == ("unavailable" if mutation == "missing" else "integrity_error")


@pytest.mark.parametrize("field,value", [
    ("scope", "urn:another:scope"),
    ("completeness", "linked"),
    ("registry", {"url": "https://other.example.test/view", "digest": "sha256:" + "0" * 64, "size": 0}),
])
def test_context_cannot_claim_a_different_manifest_state(publication, field, value):
    context, objects = publication
    context[field] = value
    with pytest.raises(PublicationError, match=field):
        open_context(context, objects)


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "absent", "default"])
def test_rehashed_invalid_graph_fails(publication, mutation):
    context, objects = publication
    pin = context["snapshot"]
    manifest = json.loads(objects[pin["url"]])
    if mutation == "missing":
        manifest["documents"] = []
    elif mutation == "duplicate":
        duplicate = deepcopy(manifest["documents"][0])
        duplicate["viewVersion"] = duplicate["viewVersion"].replace("/intro/", "/INTRO/")
        manifest["documents"].append(duplicate)
    elif mutation == "absent":
        manifest["documents"][0]["viewVersion"] = "/sets/manual/documents/missing/versions/7"
    else:
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


def test_schema_rejects_credentials_and_invalid_digest(publication):
    context, _ = publication
    context["snapshot"]["url"] = "https://user:secret@example.test/manifest"
    with pytest.raises(jsonschema.ValidationError):
        validate("open", context)
    context["snapshot"]["url"] = "https://example.test/manifest"
    context["snapshot"]["digest"] = "sha256:short"
    with pytest.raises(jsonschema.ValidationError):
        validate("open", context)


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


def test_invalid_head_and_deleted_identity_do_not_change_channel(publication):
    context, objects = publication
    channels = Channels()
    pin = context["snapshot"]
    channels.create("stable", context["scope"], pin, objects)
    before = deepcopy(channels.records)
    with pytest.raises(PublicationError):
        channels.move("stable", 1, {**pin, "digest": "sha256:" + "0" * 64}, objects)
    assert channels.records == before
    with pytest.raises(PublicationError):
        channels.delete("stable", 0)
    assert channels.records == before
    channels.delete("stable", 1)
    with pytest.raises(PublicationError) as caught:
        channels.create("stable", context["scope"], pin, objects)
    assert caught.value.code == "conflict"


def test_rehashed_duplicate_json_keys_fail(publication):
    context, objects = publication
    pin = deepcopy(context["snapshot"])
    raw = objects[pin["url"]].replace(b'"format":', b'"scope":"urn:duplicate","format":', 1)
    objects[pin["url"]] = raw
    pin.update(digest="sha256:" + hashlib.sha256(raw).hexdigest(), size=len(raw))
    with pytest.raises(PublicationError, match="duplicate JSON key"):
        check_snapshot(pin, objects)


def test_model_accepted_by_core_schema_generator(tmp_path):
    repository = ROOT.parents[1]
    output = tmp_path / "publication-schema.json"
    subprocess.run([
        sys.executable, str(repository / "tools" / "schema-generator.py"),
        "--type", "json-schema", "--output", str(output), str(ROOT / "model.json"),
    ], check=True, capture_output=True, text=True)
    generated = json.loads(output.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator.check_schema(generated)


def test_package_replays_offline_without_network():
    result = open_package(SAMPLES)
    assert result["scope"] == "urn:example:manual-publication"
    assert result["completeness"] == "offline-complete"


@pytest.mark.parametrize("path", ["../intro.txt", "/intro.txt", "dir\\intro.txt", "a/../intro.txt"])
def test_package_rejects_unsafe_paths(path):
    package = json.loads((SAMPLES / "publication-package.json").read_text(encoding="utf-8"))
    package["objects"]["https://content.example.test/intro.txt"] = path
    with pytest.raises(jsonschema.ValidationError):
        validate("package", package)


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
