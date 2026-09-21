"""Header declarations need an opaque item boundary and a defined native-value contract."""

import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("protocol,field", [("HTTP", "headers"), ("NATS", "headers"),
                                          ("MQTT/5.0", "user_properties"), ("KAFKA", "headers")])
def test_header_items_preserve_common_declaration_fields(protocol, field):
    model = json.loads((ROOT / "message" / "model.json").read_text(encoding="utf-8"))
    options = model["groups"]["messagegroups"]["resources"]["messages"]["attributes"]["protocol"]["ifvalues"]
    definition = options[protocol]["siblingattributes"]["protocoloptions"]["attributes"][field]
    assert definition["type"] == ("map" if protocol == "KAFKA" else "array")
    assert definition["item"]["type"] == "any"
    assert set(definition["item"]) == {"type"}
    for name in ("name", "type", "required", "specurl", "value"):
        assert name in definition["description"]


def test_header_refinements_do_not_invent_wire_coercion():
    prose = " ".join((ROOT / "message" / "spec.md").read_text(encoding="utf-8").split())
    assert "MUST NOT coerce" in prose
    assert "Kafka header" in prose and "base64" in prose
    assert "logical declaration" in prose
