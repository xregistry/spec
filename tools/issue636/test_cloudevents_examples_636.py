import json
from pathlib import Path
import re
from urllib.parse import urlsplit

import jsonpointer
import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "cloudevents" / "spec.md"
_ID = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.~:@-]{0,127}")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, f"duplicate JSON key: {key}"
        result[key] = value
    return result


@pytest.fixture
def examples():
    blocks = re.findall(
        r"```(?:json|yaml)\n(.*?)\n```", SPEC.read_text(encoding="utf-8"), re.S
    )
    assert len(blocks) == 5
    return [
        json.loads(block, object_pairs_hook=_unique_object) if index < 2
        else yaml.safe_load(block)
        for index, block in enumerate(blocks[:4])
    ]


def _entities(registry):
    yield "/", "registryid", registry["registryid"], registry
    for groups, group_id, resources, resource_id in (
        ("endpoints", "endpointid", "messages", "messageid"),
        ("messagegroups", "messagegroupid", "messages", "messageid"),
        ("schemagroups", "schemagroupid", "schemas", "schemaid"),
    ):
        for key, group in registry.get(groups, {}).items():
            group_xid = f"/{groups}/{key}"
            yield group_xid, group_id, key, group
            for key, resource in group.get(resources, {}).items():
                resource_xid = f"{group_xid}/{resources}/{key}"
                yield resource_xid, resource_id, key, resource
                for key, version in resource.get("versions", {}).items():
                    yield f"{resource_xid}/versions/{key}", "versionid", key, version


@pytest.mark.parametrize("index", range(4))
def test_current_endpoint_shapes_in_all_four_layout_examples(examples, index):
    endpoint = examples[index]["endpoints"]["com.example.telemetry"]
    assert endpoint["usage"] == ["consumer"]
    assert endpoint["envelope"] == "CloudEvents/1.0"
    assert endpoint["protocol"] == "MQTT/5.0"
    assert isinstance(endpoint["protocoloptions"], dict)
    assert not {"format", "config", "options", "metadata"} & endpoint.keys()
    if index < 2:
        assert endpoint["protocoloptions"] == {
            "endpoints": [{"uri": "mqtt://mqtt.example.com:1883"}],
            "topic": "{deviceid}/telemetry",
        }


@pytest.mark.parametrize("index", range(4))
def test_actual_parent_ids_self_xid_and_navigation_are_consistent(examples, index):
    registry = examples[index]
    origin = registry.get("self", "https://example.com").rstrip("/")
    count = 0
    for xid, id_field, key, entity in _entities(registry):
        count += 1
        assert _ID.fullmatch(key), (xid, key)
        assert entity[id_field] == key
        if "xid" in entity:
            assert entity["xid"] == xid
        if "self" in entity:
            assert entity["self"].rstrip("/") == origin + (xid if xid != "/" else "")
        if "metaurl" in entity:
            assert entity["metaurl"] == origin + xid + "/meta"
        for collection in ("endpoints", "messagegroups", "schemagroups", "messages", "schemas", "versions"):
            if collection + "url" in entity:
                expected = origin + xid.rstrip("/") + "/" + collection
                assert entity[collection + "url"] == expected
            if isinstance(entity.get(collection), dict) and collection + "count" in entity:
                assert entity[collection + "count"] == len(entity[collection])
    assert count >= 2


def test_compact_and_shared_messages_use_flat_native_declarations(examples):
    compact = examples[0]["endpoints"]["com.example.telemetry"]["messages"]["com.example.telemetry"]
    shared = examples[1]["messagegroups"]["com.example.telemetryEvents"]["messages"]["com.example.telemetry"]
    for message in (compact, shared):
        assert message["envelope"] == "CloudEvents/1.0"
        assert not {"format", "config", "options", "metadata"} & message.keys()
        metadata = message["envelopemetadata"]
        assert metadata["type"]["value"] == message["messageid"]
        assert metadata["source"]["type"] == "uritemplate"
        assert metadata["source"]["value"] == "{deploymentid}/{deviceid}"
        assert metadata["time"]["required"] is True
        assert "attributes" not in metadata
        assert message["dataschemaformat"] == "Protobuf/3"


def test_shared_reference_selects_the_actual_inline_protobuf_version_and_message(examples):
    registry = examples[1]
    message = registry["messagegroups"]["com.example.telemetryEvents"]["messages"]["com.example.telemetry"]
    reference = message["dataschemauri"]
    assert reference.startswith("#/")
    pointer, separator, name = reference[1:].rpartition(":")
    assert separator == ":" and name == "Metrics"
    version = jsonpointer.resolve_pointer(registry, pointer)
    assert version["versionid"] == "1.0"
    assert version["xid"] == pointer
    assert version["format"] == "Protobuf/3"
    declaration = re.search(
        r"\bmessage\s+" + re.escape(name) + r"\s*\{\s*float\s+metric\s*=\s*1\s*;\s*\}",
        version["schema"],
    )
    assert declaration, "selector must name a declaration in the shown schema"
    schema = registry["schemagroups"]["com.example.telemetry"]["schemas"]["com.example.telemetrydata"]
    assert version["schema"] == schema["schema"]
    compact = examples[0]["endpoints"]["com.example.telemetry"]["messages"]["com.example.telemetry"]
    assert re.sub(r"\s+", "", compact["dataschema"]) == re.sub(r"\s+", "", version["schema"])


def test_compact_shared_api_and_file_reference_layouts_remain_distinct(examples):
    compact, shared, api, file = [
        registry["endpoints"]["com.example.telemetry"] for registry in examples
    ]
    assert compact["messagescount"] == len(compact["messages"]) == 1
    assert "messagegroups" not in compact
    assert shared["messagescount"] == 0
    assert "messages" not in shared
    group_ref = shared["messagegroups"][0]
    assert group_ref.startswith("#/")
    group = jsonpointer.resolve_pointer(examples[1], group_ref[1:])
    assert group["messagegroupid"] == "com.example.telemetryEvents"
    api_ref = urlsplit(api["messagegroups"][0])
    assert api_ref.scheme == "https" and not api_ref.fragment
    assert api_ref.path == group["xid"]
    file_ref = urlsplit(file["messagegroups"][0])
    assert file_ref.scheme == "https" and file_ref.path.endswith(".cereg")
    assert file_ref.fragment == group["xid"]
