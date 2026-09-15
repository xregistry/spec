from copy import deepcopy
import json
from pathlib import Path
import re

import pytest


ROOT = Path(__file__).resolve().parents[1]
ID_ATTRIBUTES = {"messages": "messageid", "schemas": "schemaid"}


def _examples():
    text = (ROOT / "core" / "http.md").read_text(encoding="utf-8")
    section = text.split("#### `POST /<GROUPS>/<GID>`\n", 1)[1]
    section = section.split("\n#### ", 1)[0].split("**Examples:**", 1)[1]
    blocks = re.findall(r"```yaml\n(.*?)\n```", section, re.DOTALL)
    assert len(blocks) == 2
    assert blocks[0].startswith("POST /groups/g1\n")
    assert blocks[1].startswith("HTTP/1.1 200 OK\n")
    examples = []
    for block in blocks:
        body = block[block.index("{"):]
        body, omissions = re.subn(
            r",\n\s*\.\.\. remainder of (?:msg1|schema1) definition "
            r"excluded for brevity \.\.\.\n",
            "\n",
            body,
        )
        assert omissions == 2, "Only the two designated field omissions are removed"
        examples.append(json.loads(body))
    return examples


def _resource_entries(body):
    if type(body) is not dict or set(body) - ID_ATTRIBUTES.keys():
        raise ValueError("Expected only child Resource collections")
    entries = {}
    for collection, resources in body.items():
        if type(resources) is not dict:
            raise ValueError("Expected a Resource-ID map")
        for resource_id, resource in resources.items():
            if type(resource) is not dict:
                raise ValueError("Expected an object for each Resource")
            if resource.get(ID_ATTRIBUTES[collection]) != resource_id:
                raise ValueError("Map key and visible body ID differ")
            entries[collection, resource_id] = resource
    return entries


@pytest.mark.parametrize("index", [0, 1], ids=["request", "response"])
def test_group_post_examples_use_resource_id_maps(index):
    body = _examples()[index]
    entries = _resource_entries(body)
    assert set(body) == {"messages", "schemas"}
    assert set(entries) == {("messages", "msg1"), ("schemas", "schema1")}
    assert entries["messages", "msg1"]["messageid"] == "msg1"
    assert entries["schemas", "schema1"]["schemaid"] == "schema1"


def test_group_post_response_contains_only_submitted_child_resources():
    request, response = _examples()
    assert _resource_entries(response) == _resource_entries(request)
    assert set(response) == set(request) == set(ID_ATTRIBUTES)


def test_group_post_maps_keep_multiple_resource_ids_separate():
    request = _examples()[0]
    expanded = deepcopy(request)
    for collection, original_id, new_id in (
        ("messages", "msg1", "msg2"),
        ("schemas", "schema1", "schema2"),
    ):
        expanded[collection][new_id] = {
            **request[collection][original_id], ID_ATTRIBUTES[collection]: new_id
        }
    entries = _resource_entries(expanded)
    assert set(entries) == {
        ("messages", "msg1"), ("messages", "msg2"),
        ("schemas", "schema1"), ("schemas", "schema2"),
    }
    for key, resource in _resource_entries(request).items():
        assert entries[key] == resource


def test_group_post_maps_reject_collapsed_scalar_entity_values():
    body = deepcopy(_examples()[0])
    body["messages"] = body["messages"]["msg1"]
    with pytest.raises(ValueError, match="object for each Resource"):
        _resource_entries(body)


def test_group_post_maps_reject_visible_body_id_mismatch():
    body = deepcopy(_examples()[0])
    body["schemas"]["schema1"]["schemaid"] = "different"
    with pytest.raises(ValueError, match="Map key and visible body ID differ"):
        _resource_entries(body)


def test_group_post_examples_do_not_allow_group_attribute_updates():
    body = deepcopy(_examples()[0])
    body["name"] = "Changed Group"
    with pytest.raises(ValueError, match="only child Resource collections"):
        _resource_entries(body)
