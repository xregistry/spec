import json
from pathlib import Path
import re

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _blocks(section):
    return re.findall(r"```yaml\n(.*?)\n```", section, re.DOTALL)


def _examples():
    text = (ROOT / "core" / "http.md").read_text(encoding="utf-8")
    section = text.split("### Registry Capabilities\n", 1)[1].split("\n### ", 1)[0]
    bodies = [
        json.loads(block[block.index("{"):])
        for block in _blocks(section)
        if '"available"' in block
    ]
    assert len(bodies) == 3, "Expected enabled, offered and updated examples"
    return bodies


def _core_available():
    text = (ROOT / "core" / "spec.md").read_text(encoding="utf-8")
    section = text.split("#### `available` Capability\n", 1)[1].split("\n#### ", 1)[0]
    blocks = re.findall(r"  ```yaml\n(.*?)\n  ```", section, re.DOTALL)
    assert len(blocks) == 2
    defaults = json.loads(blocks[0])
    example = json.loads("{" + blocks[1] + "}")["available"]
    return defaults, example


@pytest.mark.parametrize("index", [0, 2], ids=["enabled", "updated"])
def test_available_examples_use_core_metadata_map_and_native_booleans(index):
    available = _examples()[index]["available"]
    defaults, core_example = _core_available()

    assert type(available) is dict
    assert set(defaults) <= set(available)
    assert set(available) == set(core_example)
    for name, value in available.items():
        assert not name.startswith("/")
        assert type(value) is dict
        assert set(value) == {"mutable"}
        assert type(value["mutable"]) is bool
    assert available["model"]["mutable"] is defaults["model"]["mutable"] is False


def test_offered_available_describes_metadata_objects_not_enabled_values():
    enabled, offered, updated = _examples()
    descriptor = offered["available"]
    assert descriptor["type"] == "object"
    assert set(descriptor["attributes"]) == set(enabled["available"])

    for name, metadata in descriptor["attributes"].items():
        assert not name.startswith("/")
        assert metadata["type"] == "object"
        mutable = metadata["attributes"]["mutable"]
        assert mutable["type"] == "boolean"
        assert mutable["enum"]
        assert all(type(value) is bool for value in mutable["enum"])
        for example in (enabled, updated):
            assert example["available"][name]["mutable"] in mutable["enum"]

    assert descriptor["attributes"]["model"]["attributes"]["mutable"]["enum"] == [False]
    assert set(
        descriptor["attributes"]["entities"]["attributes"]["mutable"]["enum"]
    ) == {False, True}


def test_capability_patch_only_changes_shortself_and_preserves_separate_mutable():
    enabled, offered, updated = _examples()
    text = (ROOT / "core" / "http.md").read_text(encoding="utf-8")
    section = text.split("#### `PATCH` and `PUT /capabilities`\n", 1)[1]
    example_section = section.split("**Examples:**", 1)[1].split("\n### ", 1)[0]
    request = _blocks(example_section)[0]
    assert request.startswith("PATCH /capabilities\n")
    patch = json.loads(request[request.index("{"):])

    assert patch == {"shortself": True}
    assert updated == {**enabled, **patch}
    assert enabled["shortself"] is False
    assert set(offered["shortself"]["enum"]) == {False, True}
    assert enabled["mutable"] == updated["mutable"] == [
        "capabilities", "entities", "model"
    ]
