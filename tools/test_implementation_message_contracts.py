"""Source regressions reproduced through compiled .NET Message/Endpoint models."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def message_attributes():
    source = json.loads((ROOT / "message" / "model.json").read_text(encoding="utf-8"))
    return source["groups"]["messagegroups"]["resources"]["messages"]["attributes"]


def protocol_options(protocol):
    return message_attributes()["protocol"]["ifvalues"][protocol]["siblingattributes"]["protocoloptions"]["attributes"]


def test_base_message_has_the_normative_name_and_target():
    attributes = message_attributes()
    assert "basemessageuri" not in attributes
    assert attributes["basemessage"]["name"] == "basemessage"
    assert attributes["basemessage"]["type"] == "uri"
    assert attributes["basemessage"]["target"] == "/messagegroups/messages[/versions]"


def test_http_query_is_a_string_map_and_status_is_declared():
    options = protocol_options("HTTP")
    assert options["query"]["type"] == "map"
    assert options["query"]["item"] == {"type": "string"}
    assert options["status"]["type"] == "string"
    assert options["status"]["name"] == "status"
    prose = (ROOT / "message" / "spec.md").read_text(encoding="utf-8")
    assert '"query": [' not in prose
    assert '"query": {' in prose


def test_nats_uses_the_normative_reply_to_field():
    options = protocol_options("NATS")
    assert "reply" not in options
    assert options["reply-to"]["name"] == "reply-to"
    assert options["reply-to"]["type"] == "uritemplate"


def test_amqp_optional_subject_is_not_required_by_default():
    properties = protocol_options("AMQP/1.0")["properties"]
    assert properties["type"] == "any"
    prose = (ROOT / "message" / "spec.md").read_text(encoding="utf-8")
    assert "Default value MUST be `false`." in prose
    assert "As in AMQP, all sections and properties are OPTIONAL." in prose


def test_endpoint_messagegroups_target_is_a_group_type():
    source = json.loads((ROOT / "endpoint" / "model.json").read_text(encoding="utf-8"))
    references = source["groups"]["endpoints"]["attributes"]["messagegroups"]
    assert references["item"] == {"type": "uri", "target": "/messagegroups"}


def test_mqtt_payload_indicator_name_is_consistent_in_table_and_model():
    assert protocol_options("MQTT/5.0")["payload_format_indicator"]["type"] == "integer"
    prose = (ROOT / "message" / "spec.md").read_text(encoding="utf-8")
    assert "| `payload_format` " not in prose
    assert "| `payload_format_indicator` " in prose
