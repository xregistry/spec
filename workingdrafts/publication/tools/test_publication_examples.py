"""Independent mutations of authored bytes and publication state transitions."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import socket

import jsonschema
import pytest

from workingdrafts.publication.tools.publication_examples import (
    Channels, PublicationError, SCHEMA, VersionDocuments, checked_bytes,
    check_snapshot, open_context, open_package, reference_key, validate,
)


ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"


@pytest.fixture
def publication():
    objects = VersionDocuments()
    package = json.loads((SAMPLES / "publication-package.json").read_text(encoding="utf-8"))
    for entry in package["objects"]:
        objects.put(entry["reference"], (SAMPLES / entry["path"]).read_bytes())
    context = json.loads((SAMPLES / "open.json").read_text(encoding="utf-8"))
    return context, objects


def replace(objects, pin, value):
    raw = (json.dumps(value, indent=2) + "\n").encode()
    digest = hashlib.sha256(raw).hexdigest()
    pin = {**deepcopy(pin), "digest": "sha256:" + digest, "size": len(raw)}
    if pin["reference"]["version"].endswith("/versions/manifest"):
        pin["reference"]["version"] = f"/publications/team/snapshots/{digest}/versions/manifest"
    objects.put(pin["reference"], raw)
    return pin


def test_checked_authored_bytes_and_context(publication):
    context, objects = publication
    jsonschema.Draft202012Validator.check_schema(SCHEMA)
    result = open_context(context, objects.read)
    assert result["documents"][0]["viewVersion"] == "/sets/manual/documents/intro/versions/7"
    validate("channel", json.loads((SAMPLES / "channel.json").read_text(encoding="utf-8")))


@pytest.mark.parametrize("mutation", ["bytes", "missing"])
def test_corrupt_or_unavailable_content_fails(publication, mutation):
    context, objects = publication
    manifest = json.loads(objects.read(context["snapshot"]["reference"]))
    content = manifest["documents"][0]["content"]
    if mutation == "bytes":
        objects.put(content["reference"], b"X" * content["size"])
    else:
        objects.remove(content["reference"])
    with pytest.raises(PublicationError) as caught:
        open_context(context, objects.read)
    assert caught.value.code == ("unavailable" if mutation == "missing" else "integrity_error")


@pytest.mark.parametrize("field,value", [
    ("scope", "urn:another:scope"),
])
def test_context_cannot_claim_a_different_manifest_state(publication, field, value):
    context, objects = publication
    context[field] = value
    with pytest.raises(PublicationError, match=field):
        open_context(context, objects.read)


def test_rehashed_invalid_graph_fails(publication):
    context, objects = publication
    pin = context["snapshot"]
    manifest = json.loads(objects.read(pin["reference"]))
    registry_pin = manifest["registry"]
    registry = json.loads(objects.read(registry_pin["reference"]))
    registry["sets"]["manual"]["documents"]["intro"]["meta"]["defaultversionid"] = "99"
    manifest["registry"] = replace(objects, registry_pin, registry)
    new_pin = replace(objects, pin, manifest)
    with pytest.raises(PublicationError) as caught:
        check_snapshot(new_pin, objects.read)
    assert caught.value.code == "invalid_package"


def test_unsupported_required_extension_fails(publication):
    context, objects = publication
    pin = context["snapshot"]
    manifest = json.loads(objects.read(pin["reference"]))
    manifest["requiredExtensions"] = ["urn:example:unknown-closure"]
    new_pin = replace(objects, pin, manifest)
    with pytest.raises(PublicationError) as caught:
        check_snapshot(new_pin, objects.read)
    assert caught.value.code == "unsupported_operation"


def test_fork_promotion_rollback_and_stale_writer(publication):
    context, objects = publication
    first = context["snapshot"]
    manifest = json.loads(objects.read(first["reference"]))
    manifest["parent"] = deepcopy(first)
    second = replace(objects, first, manifest)
    channels = Channels()
    channels.create("stable", context["scope"], first, objects.read)
    channels.create("preview", context["scope"], first, objects.read)
    channels.move("preview", 1, second, objects.read)
    assert channels.records["stable"]["head"] == first
    channels.move("stable", 1, second, objects.read)
    with pytest.raises(PublicationError) as caught:
        channels.move("stable", 1, first, objects.read)
    assert caught.value.code == "mismatched_epoch"
    assert channels.records["stable"]["head"] == second
    reader = deepcopy(channels.records["stable"]["head"])
    channels.move("stable", 2, first, objects.read)
    assert channels.records["stable"] == {"scope": context["scope"], "head": first, "epoch": 3}
    assert check_snapshot(reader, objects.read)["parent"] == first
    assert check_snapshot(first, objects.read)["documents"] == manifest["documents"]


def test_package_replays_offline_without_network():
    result = open_package(SAMPLES)
    assert result["scope"] == "urn:example:manual-publication"
    assert result["completeness"] == "offline-complete"


def test_wrong_scope_head_preserves_channel(publication):
    context, objects = publication
    channels = Channels()
    pin = context["snapshot"]
    channels.create("stable", context["scope"], pin, objects.read)
    manifest = json.loads(objects.read(pin["reference"]))
    manifest["scope"] = "urn:another:scope"
    other = replace(objects, pin, manifest)
    before = deepcopy(channels.records)
    with pytest.raises(PublicationError, match="scope"):
        channels.move("stable", 1, other, objects.read)
    assert channels.records == before


@pytest.mark.parametrize("name", ["http", "opcua"])
def test_exact_version_binding_dispatch(publication, name):
    _, documents = publication
    prefix = "opcua-" if name == "opcua" else ""
    context = json.loads((SAMPLES / (prefix + "open.json")).read_text())
    reads = []

    def read(reference):
        reads.append(deepcopy(reference))
        assert reference["registry"]["name"] == name
        return documents.read(reference)

    result = open_context(context, read)
    assert reads == [
        context["snapshot"]["reference"], result["registry"]["reference"],
        result["documents"][0]["content"]["reference"],
    ]
    assert reads[-1]["version"] == "/sets/manual/documents/intro/versions/7"
    if name == "opcua":
        assert all(r["registry"]["endpoint"] == "opc.tcp://ua.example.test:4840" for r in reads)
        assert all(r["registry"]["parameters"]["registryroot"] ==
                   "nsu=urn:example:publication;s=Registry" for r in reads)


@pytest.mark.parametrize("raw", [b"", b"\x00\xff\r\n", b'{ "n": 1 }\r\n', b'{"n":1}\n'])
def test_document_reader_checks_exact_raw_bytes(publication, raw):
    context, documents = publication
    pin = deepcopy(context["snapshot"])
    pin.update(digest="sha256:" + hashlib.sha256(raw).hexdigest(), size=len(raw))
    documents.put(pin["reference"], raw)
    assert checked_bytes(pin, documents.read) == raw
    documents.put(pin["reference"], raw + b" ")
    with pytest.raises(PublicationError) as caught:
        checked_bytes(pin, documents.read)
    assert caught.value.code == "integrity_error"


@pytest.mark.parametrize("change", ["default", "url-only", "credentials"])
def test_rejects_non_version_or_url_only_reference(publication, change):
    context, documents = publication
    pin = deepcopy(context["snapshot"])
    if change == "default":
        pin["reference"]["version"] = "/sets/manual/documents/intro"
    elif change == "url-only":
        del pin["reference"]
        pin["url"] = "https://content.example.test/manifest.json"
    else:
        pin["reference"]["registry"]["endpoint"] = "https://user:secret@example.test"
    with pytest.raises(jsonschema.ValidationError):
        checked_bytes(pin, documents.read)


@pytest.mark.parametrize("access,code", [
    ({"name": "unknown", "endpoint": "urn:unknown:binding"}, "unsupported_binding"),
    ({"name": "http", "endpoint": "https://example.test",
      "parameters": {"registryroot": "i=85"}}, "unsupported_operation"),
    ({"name": "opcua", "endpoint": "opc.tcp://example.test:4840",
      "parameters": {"registryroot": "ns=2;s=Registry"}}, "invalid_package"),
    ({"name": "opcua", "endpoint": "opc.tcp://example.test:4840"}, "invalid_package"),
    ({"name": "git", "endpoint": "https://example.test/repo",
      "parameters": {"revision": "refs/heads/main"}}, "invalid_package"),
    ({"name": "oci", "endpoint": "oci://example.test/repo",
      "parameters": {"reference": "latest"}}, "invalid_package"),
])
def test_invalid_access_never_dispatches(publication, access, code):
    context, _ = publication
    pin = deepcopy(context["snapshot"])
    pin["reference"]["registry"] = access
    reads = []
    with pytest.raises(PublicationError) as caught:
        checked_bytes(pin, lambda reference: reads.append(reference))
    assert caught.value.code == code
    assert reads == []


def test_wrong_registry_never_falls_back(publication):
    context, documents = publication
    pin = deepcopy(context["snapshot"])
    pin["reference"]["registry"]["endpoint"] = "https://other.example.test"
    reads = []

    def read(reference):
        reads.append(reference)
        return documents.read(reference)

    with pytest.raises(PublicationError) as caught:
        checked_bytes(pin, read)
    assert caught.value.code == "unavailable"
    assert reads == [pin["reference"]]


def test_policy_denial_preserves_head(publication):
    context, documents = publication
    channels = Channels()
    channels.create("stable", context["scope"], context["snapshot"], documents.read)
    before = deepcopy(channels.records)

    def denied(reference):
        raise PublicationError("policy_denied", reference["version"])

    with pytest.raises(PublicationError) as caught:
        channels.move("stable", 1, context["snapshot"], denied)
    assert caught.value.code == "policy_denied"
    assert channels.records == before


def test_missing_prepared_content_preserves_head(publication):
    context, documents = publication
    channels = Channels()
    channels.create("stable", context["scope"], context["snapshot"], documents.read)
    before = deepcopy(channels.records)
    manifest = json.loads(documents.read(context["snapshot"]["reference"]))
    manifest["parent"] = context["snapshot"]
    second = replace(documents, context["snapshot"], manifest)
    documents.remove(manifest["documents"][0]["content"]["reference"])
    with pytest.raises(PublicationError) as caught:
        channels.move("stable", 1, second, documents.read)
    assert caught.value.code == "unavailable"
    assert channels.records == before


def test_duplicate_view_version_fails_after_rehash(publication):
    context, documents = publication
    manifest = json.loads(documents.read(context["snapshot"]["reference"]))
    other = deepcopy(manifest["documents"][0])
    other["viewVersion"] = "/SETS/MANUAL/DOCUMENTS/INTRO/versions/7"
    manifest["documents"].append(other)
    pin = replace(documents, context["snapshot"], manifest)
    with pytest.raises(PublicationError) as caught:
        check_snapshot(pin, documents.read)
    assert caught.value.code == "invalid_package"


@pytest.mark.parametrize("version", [
    "/publications/team/snapshots/wrong/versions/manifest",
    "/publications/team/snapshots/{digest}/versions/content",
])
def test_manifest_storage_identity_is_checked(publication, version):
    context, documents = publication
    pin = deepcopy(context["snapshot"])
    raw = documents.read(pin["reference"])
    pin["reference"]["version"] = version.format(digest=pin["digest"][7:])
    documents.put(pin["reference"], raw)
    with pytest.raises(PublicationError) as caught:
        check_snapshot(pin, documents.read)
    assert caught.value.code == "invalid_package"


def test_reference_comparison_preserves_version_case(publication):
    context, _ = publication
    first = context["snapshot"]["reference"]
    equivalent = deepcopy(first)
    equivalent["registry"]["parameters"] = {}
    equivalent["version"] = equivalent["version"].replace("/publications/team/", "/%70ublications/TEAM/")
    assert reference_key(first) == reference_key(equivalent)
    equivalent["version"] = equivalent["version"].replace("/manifest", "/Manifest")
    assert reference_key(first) != reference_key(equivalent)
    with pytest.raises(jsonschema.ValidationError):
        reference_key({**first, "version": first["version"] + "/extra"})


def test_git_reference_comparison_uses_commit_and_default_path():
    first = {
        "registry": {
            "name": "git", "endpoint": "https://example.test/repo",
            "parameters": {"revision": "a" * 40},
        },
        "version": "/sets/manual/documents/intro/versions/7",
    }
    other = deepcopy(first)
    other["registry"]["parameters"] = {"path": "xregistry", "revision": "A" * 40}
    assert reference_key(first) == reference_key(other)
    other["registry"]["parameters"]["revision"] = "b" * 40
    assert reference_key(first) != reference_key(other)


def test_extension_is_an_exact_version_document(publication):
    context, documents = publication
    manifest = json.loads(documents.read(context["snapshot"]["reference"]))
    extension = deepcopy(manifest["registry"])
    extension["reference"]["version"] = "/publications/team/objects/provenance/versions/content"
    extension = replace(documents, extension, {"source": "urn:example:captured"})
    manifest["extensions"] = {"urn:example:provenance": extension}
    manifest["requiredExtensions"] = ["urn:example:provenance"]
    manifest["documents"][0]["originRegistry"] = "urn:example:original-registry"
    pin = replace(documents, context["snapshot"], manifest)
    assert check_snapshot(pin, documents.read, ("urn:example:provenance",)) == manifest
    documents.remove(extension["reference"])
    with pytest.raises(PublicationError) as caught:
        check_snapshot(pin, documents.read, ("urn:example:provenance",))
    assert caught.value.code == "unavailable"


@pytest.fixture
def package_dir(tmp_path):
    target = tmp_path / "package"
    shutil.copytree(SAMPLES, target)
    return target


def edit_package(directory, edit):
    path = directory / "publication-package.json"
    package = json.loads(path.read_text())
    edit(package)
    path.write_text(json.dumps(package), encoding="utf-8")


def test_package_replays_native_references_without_network(package_dir, monkeypatch):
    def no_network(*args, **kwargs):
        pytest.fail("Offline replay attempted networking")

    monkeypatch.setattr(socket, "create_connection", no_network)
    native = json.loads((package_dir / "opcua-open.json").read_text())
    edit_package(package_dir, lambda p: p.update(context=native))
    result = open_package(package_dir)
    assert result["documents"][0]["content"]["reference"]["registry"]["name"] == "opcua"
    (package_dir / "intro.txt").unlink()
    with pytest.raises(PublicationError) as caught:
        open_package(package_dir)
    assert caught.value.code == "unavailable"


def test_package_rejects_duplicate_equivalent_reference(package_dir):
    def duplicate(package):
        other = deepcopy(package["objects"][0])
        other["reference"]["registry"]["parameters"] = {}
        other["reference"]["version"] = other["reference"]["version"].replace("/team/", "/TEAM/")
        other["path"] = "intro.txt"
        package["objects"].append(other)

    edit_package(package_dir, duplicate)
    with pytest.raises(PublicationError) as caught:
        open_package(package_dir)
    assert caught.value.code == "invalid_package"


@pytest.mark.parametrize("path", ["../intro.txt", "/intro.txt", "a\\intro.txt", "%2e%2e/intro.txt"])
def test_package_rejects_unsafe_paths(package_dir, path):
    edit_package(package_dir, lambda p: p["objects"][0].update(path=path))
    with pytest.raises(jsonschema.ValidationError):
        open_package(package_dir)


def test_package_enforces_byte_and_object_limits(package_dir):
    package = json.loads((package_dir / "publication-package.json").read_text())
    count = len(package["objects"])
    assert open_package(package_dir, max_objects=count)["scope"] == package["context"]["scope"]
    with pytest.raises(PublicationError) as caught:
        open_package(package_dir, max_objects=count - 1)
    assert caught.value.code == "limit_exceeded"
    total = sum((package_dir / entry["path"]).stat().st_size for entry in package["objects"])
    assert open_package(package_dir, max_bytes=total)["scope"] == package["context"]["scope"]
    with pytest.raises(PublicationError) as caught:
        open_package(package_dir, max_bytes=total - 1)
    assert caught.value.code == "limit_exceeded"


def test_deleted_channel_identity_cannot_be_reused(publication):
    context, documents = publication
    channels = Channels()
    channels.create("stable", context["scope"], context["snapshot"], documents.read)
    channels.delete("stable", 1)
    with pytest.raises(PublicationError) as caught:
        channels.create("stable", context["scope"], context["snapshot"], documents.read)
    assert caught.value.code == "conflict"
    assert channels.records == {}


def test_builder_reproduces_authored_samples(tmp_path):
    from workingdrafts.publication.tools import build_samples

    original = build_samples.SAMPLES
    target = tmp_path / "samples"
    target.mkdir()
    for name in ("registry.json", "intro.txt"):
        shutil.copyfile(SAMPLES / name, target / name)
    spec = target.parent / "spec.md"
    spec.write_text("```json\n{\"format\": \"xregistry-publication/1\"}\n```\n", encoding="utf-8")
    try:
        build_samples.SAMPLES = target
        build_samples.build()
    finally:
        build_samples.SAMPLES = original
    for name in (
        "manifest.json", "channel.json", "open.json", "publication-package.json",
        "opcua-manifest.json", "opcua-channel.json", "opcua-open.json",
    ):
        assert (target / name).read_bytes() == (SAMPLES / name).read_bytes(), name
    assert (target / "manifest.json").read_text().rstrip() in spec.read_text()
