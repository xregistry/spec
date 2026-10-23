"""Keep the federation selection walkthrough executable and byte-accurate."""

import json
import re
from pathlib import Path

import pytest

from workingdrafts.federation.tools.federation_examples import (
    FederationError, select_label, select_version,
)
from workingdrafts.federation.tools.federation_resolution_examples import Source, resolve_resource_read


ROOT = Path(__file__).resolve().parents[1]


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
    text = (ROOT / "spec.md").read_text(encoding="utf-8")
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
