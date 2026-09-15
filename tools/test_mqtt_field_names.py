"""Compare MQTT documentation with the authoritative model, not wire codecs."""

import json
import re
from pathlib import Path

import pytest


MESSAGE = Path(__file__).resolve().parents[1] / "message"
SPEC = (MESSAGE / "spec.md").read_text(encoding="utf-8")
MQTT = SPEC.split('##### "MQTT/3.1.1" and "MQTT/5.0" protocols\n', 1)[1].split(
    '##### "KAFKA" protocol', 1
)[0]
MODEL = json.loads((MESSAGE / "model.json").read_text(encoding="utf-8"))
PROTOCOLS = MODEL["groups"]["messagegroups"]["resources"]["messages"][
    "attributes"
]["protocol"]["ifvalues"]


def _attributes(version):
    return PROTOCOLS[version]["siblingattributes"]["protocoloptions"]["attributes"]


@pytest.mark.parametrize("version, column", [("MQTT/3.1.1", 2), ("MQTT/5.0", 3)])
def test_mqtt_table_names_and_version_availability_match_model(version, column):
    rows = [
        [cell.strip().strip("`") for cell in line.strip("|").split("|")]
        for line in MQTT.splitlines()
        if line.startswith("| `")
    ]
    assert len(rows) == 9
    assert {row[0] for row in rows if row[column] == "yes"} == set(
        _attributes(version)
    )
    assert {row[0] for row in rows if row[column] == "no"}.isdisjoint(
        _attributes(version)
    )


def test_mqtt_user_properties_prose_names_the_modeled_array():
    names = re.findall(r"with the `([^`]+)` element corresponding", MQTT)
    assert names == ["user_properties"]
    assert _attributes("MQTT/5.0")[names[0]]["type"] == "array"


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


def test_duplicate_user_property_guidance_and_array_example_are_preserved():
    duplicate_rule = MQTT.split("Like HTTP,", 1)[1].split("\n\n", 1)[0]
    assert " ".join(duplicate_rule.split()) == (
        "MQTT allows for multiple user properties with the same name, so the "
        "`user_properties` property is an array of objects, each of which "
        "contains a single property name and value."
    )
    example = json.loads(MQTT.split("```yaml\n", 1)[1].split("\n```", 1)[0])
    assert example["protocol"] == "MQTT/5.0"
    assert example["protocoloptions"]["user_properties"] == [
        {"name": "My Application Property", "value": "Value 1"}
    ]
    item = _attributes("MQTT/5.0")["user_properties"]["item"]
    assert item["type"] == "object"
    assert item["attributes"]["name"]["type"] == "string"
    assert item["attributes"]["value"]["type"] == "string"
