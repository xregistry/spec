"""Check MQTT field names and kinds in the authoritative Message model."""

import json
from pathlib import Path

import pytest


MESSAGE = Path(__file__).resolve().parents[1] / "message"
MODEL = json.loads((MESSAGE / "model.json").read_text(encoding="utf-8"))
PROTOCOLS = MODEL["groups"]["messagegroups"]["resources"]["messages"][
    "attributes"
]["protocol"]["ifvalues"]


def _attributes(version):
    return PROTOCOLS[version]["siblingattributes"]["protocoloptions"]["attributes"]


@pytest.mark.parametrize("name", ["payload_format", "user-properties"])
def test_legacy_spellings_are_not_modeled_aliases(name):
    for version in ("MQTT/3.1.1", "MQTT/5.0"):
        assert name not in _attributes(version)


def test_payload_format_indicator_retains_integer_zero_one_range():
    attribute = _attributes("MQTT/5.0")["payload_format_indicator"]
    assert attribute["name"] == "payload_format_indicator"
    assert attribute["type"] == "integer"
    assert attribute["enum"] == [0, 1]
    assert all(type(value) is int for value in attribute["enum"])
    assert -1 not in attribute["enum"]
    assert 2 not in attribute["enum"]


def test_user_property_items_keep_string_name_and_value():
    item = _attributes("MQTT/5.0")["user_properties"]["item"]
    assert item["type"] == "object"
    assert item["attributes"]["name"]["type"] == "string"
    assert item["attributes"]["value"]["type"] == "string"
