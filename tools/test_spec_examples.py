"""Keep the complete specification walkthroughs executable and byte-accurate."""

import json
import re
import shutil
from pathlib import Path

import pytest

from federation_examples import FederationError, select_label, select_version
from federation_resolution_examples import Source, resolve_resource_read
from mapping_examples import DocumentTree, FileStore


ROOT = Path(__file__).resolve().parent.parent
WALKTHROUGH = ROOT / "workingdrafts" / "bindings" / "samples" / "mapping-example"
RESOURCE = "/documents/main/assets/widget"
VERSION = RESOURCE + "/versions/v1"


def test_complete_mapping_walkthrough_reads_the_document_and_version_metadata():
    reader = DocumentTree(FileStore(WALKTHROUGH))
    result = reader.validate()
    assert (result["records"], result["indexes"], result["documents"]) == (5, 3, 1)
    assert reader.document(RESOURCE) == reader.document(VERSION) == b'{"type":"string"}\n'
    metadata = reader.metadata(VERSION)
    assert metadata["entity"]["self"] == "#/entity"
    assert metadata["entity"]["xid"] == VERSION
    assert metadata["entity"]["versionid"] == "v1"
    assert metadata["entity"]["contenttype"] == "application/schema+json"
    assert "asset" not in metadata["entity"]
    assert reader.document_descriptor(VERSION) == {
        "kind": "local", "href": "source/specs/widget.json", "size": 18,
        "sha256": "85803e087e684bdab3e5d6c2dd1af627da83382db625be9a42aea3d4d06539be",
    }


def test_mapping_walkthrough_contains_every_metadata_file_verbatim():
    text = (ROOT / "workingdrafts" / "bindings" / "mapping.md").read_text(encoding="utf-8")
    walkthrough = text.split("<!-- mapping-walkthrough:start -->")[1].split(
        "<!-- mapping-walkthrough:end -->"
    )[0]
    blocks = re.findall(r"\*\*`([^`]+)`\*\*\s+```json\n(.*?)```", walkthrough, re.S)
    files = {
        path.relative_to(WALKTHROUGH).as_posix()
        for path in WALKTHROUGH.rglob("*.json")
    } - {"source/specs/widget.json"}
    assert len(blocks) == 8
    assert {name for name, _ in blocks} == files
    for name, content in blocks:
        assert content.encode("utf-8") == (WALKTHROUGH / name).read_bytes()
    result_blocks = [
        json.loads(content)
        for content in re.findall(r"```json\n(.*?)```", walkthrough, re.S)
    ]
    metadata = next(value for value in result_blocks if value.get("kind") == "version" and "self" in value.get("entity", {}))
    assert metadata == DocumentTree(FileStore(WALKTHROUGH)).metadata(VERSION)


def test_mapping_walkthrough_reports_modified_existing_content(tmp_path):
    copied = tmp_path / "project"
    shutil.copytree(WALKTHROUGH, copied)
    (copied / "source" / "specs" / "widget.json").write_bytes(b'{"type":"number"}\n')
    reader = DocumentTree(FileStore(copied))
    with pytest.raises(FederationError) as error:
        reader.document(VERSION)
    assert error.value.code == "integrity_error"


@pytest.mark.parametrize("local_shadow", [True, False], ids=["unique-after-shadowing", "ambiguous-without-shadow"])
def test_published_selection_example_filters_after_resource_shadowing(local_shadow):
    collection = "/documents/main/assets"
    calls = []

    def resource(identifier, version, stage):
        return {
            "xid": collection + "/" + identifier, "assetid": identifier,
            "meta": {"defaultversionid": version},
            "versions": {version: {"versionid": version, "labels": {"stage": stage}}},
        }

    def source(name, entities):
        def read(operation, target):
            calls.append((name, operation, target))
            if target not in entities:
                raise FederationError("not_found", "Resource absent")
            entity = entities[target]
            if operation == "document":
                selected = select_version(entity)["versionid"]
                return f"source {name} version {selected}\n".encode()
            return entity
        return Source(name, read)

    local = source("Local", {collection + "/item": resource("item", "v1", "development")} if local_shadow else {})
    sources = [
        source("A", {collection + "/item": resource("item", "v2", "production")}),
        source("B", {collection + "/other": resource("other", "v7", "production")}),
    ]
    visible = [
        resolve_resource_read(collection + "/" + identifier, "entity", local, sources)
        for identifier in ("item", "other")
    ]
    effective = [{**select_version(item["value"]), **item["value"]} for item in visible]
    assert [item["origin"] for item in visible] == (["Local", "B"] if local_shadow else ["A", "B"])
    assert [select_version(item["value"])["versionid"] for item in visible] == (
        ["v1", "v7"] if local_shadow else ["v2", "v7"]
    )
    if local_shadow:
        selected = select_label(effective, "stage", "production")
        assert selected["assetid"] == "other"
        assert ("A", "entity", collection + "/item") not in calls
        document = resolve_resource_read(selected["xid"], "document", local, sources)
        assert document == {
            "origin": "B", "target": collection + "/other", "value": b"source B version v7\n"
        }
    else:
        with pytest.raises(FederationError) as error:
            select_label(effective, "stage", "production")
        assert error.value.code == "ambiguous"


def test_selection_example_keeps_public_metadata_separate_from_source_context():
    text = (ROOT / "workingdrafts" / "federation" / "spec.md").read_text(encoding="utf-8")
    section = text.split("### Example: Select After Applying Shadows")[1].split(
        "## Discovery and Binding Selection"
    )[0]
    values = [json.loads(block) for block in re.findall(r"```json\n(.*?)```", section, re.S)]
    assert values[0] == {"label": "stage", "value": "production"}
    metadata, origin = values[1:]
    xid = "/documents/main/assets/other/versions/v7"
    assert metadata["xid"] == origin["selectedxid"] == xid
    assert metadata["self"] == "https://registry.example.com" + xid + "$details"
    assert metadata["versionid"] == "v7"
    assert metadata["labels"] == {"stage": "production"}
    assert metadata["contenttype"] == "text/plain"
    assert origin["endpoint"] == "https://b.example.com/registry"
    assert origin["revision"] is None and origin["consistency"] == "live"
    assert "origin" not in metadata and "registryid" not in metadata
