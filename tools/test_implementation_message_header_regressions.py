"""Common header declarations and binary protocol fields retain their types."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _protocols():
    model = json.loads((ROOT / "message" / "model.json").read_text(encoding="utf-8"))
    return model["groups"]["messagegroups"]["resources"]["messages"]["attributes"]["protocol"]["ifvalues"]


def test_binary_correlation_data_is_not_a_uri_template():
    fields = _protocols()["MQTT/5.0"]["siblingattributes"]["protocoloptions"]["attributes"]
    assert fields["correlation_data"]["type"] == "string"
    assert "base64" in fields["correlation_data"]["description"].lower()


def test_mqtt_content_type_represents_media_type_strings_with_parameters():
    fields = _protocols()["MQTT/5.0"]["siblingattributes"]["protocoloptions"]["attributes"]
    assert fields["content_type"]["type"] == "string"
    prose = (ROOT / "message" / "spec.md").read_text(encoding="utf-8")
    assert "| `content_type`            | `string`" in prose


def test_every_header_declaration_has_the_common_specification_reference():
    protocols = _protocols()
    for protocol, name in (("HTTP", "headers"), ("NATS", "headers"), ("MQTT/5.0", "user_properties"), ("KAFKA", "headers")):
        field = protocols[protocol]["siblingattributes"]["protocoloptions"]["attributes"][name]
        assert field["item"]["type"] == "any"
        assert "specurl" in field["description"]
    prose = (ROOT / "message" / "spec.md").read_text(encoding="utf-8")
    assert "relative or absolute URI" in prose
