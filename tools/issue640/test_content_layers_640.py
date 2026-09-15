import base64
from copy import deepcopy
from email.parser import Parser
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import pytest

from content_layers_640 import ContentLayers, content_layers


ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "message" / "spec.md"


def _message(mode, media):
    return {
        "envelope": "CloudEvents/1.0",
        "envelopeoptions": {
            "mode": mode,
            **({"format": "application/cloudevents+json"} if mode == "structured" else {}),
        },
        "datacontenttype": media,
        "envelopemetadata": {"datacontenttype": {"value": media}},
    }


def test_documented_content_layer_matrix_covers_both_modes_and_three_payloads():
    rows = re.findall(
        r"^\| `(binary|structured)`\s*\| `([^`]+)`\s*\| `([^`]+)`\s*\|$",
        SPEC.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    assert len(rows) == 6
    assert {mode for mode, _, _ in rows} == {"binary", "structured"}
    assert {media for _, media, _ in rows} == {
        "application/json", "application/xml", "application/octet-stream"
    }
    for mode, media, wire in rows:
        layers = content_layers(_message(mode, media), event_media=media, wire_media=wire)
        assert layers.payload == media
        assert layers.wire == wire
        assert layers.envelope == (wire if mode == "structured" else None)


def test_actual_structured_xml_example_separates_data_and_http_body():
    source = SPEC.read_text(encoding="utf-8")
    section = source.split("For example, this Message declares XML event data", 1)[1]
    declaration = json.loads(re.search(r"```json\n(.*?)\n```", section, re.S)[1])
    wire = re.search(r"```http\n(.*?)\n```", section, re.S)[1]
    headers = Parser().parsestr(wire)
    event = json.loads(headers.get_payload())
    layers = content_layers(
        declaration,
        event_media=event["datacontenttype"],
        wire_media=headers["Content-Type"],
    )
    assert layers == ContentLayers(
        "application/xml", "application/cloudevents+json", "application/cloudevents+json"
    )
    assert ET.fromstring(event["data"]).tag == "order"
    assert ET.fromstring(event["data"]).attrib == {"id": "42"}
    assert event["type"] == declaration["envelopemetadata"]["type"]["value"]


def test_endpoint_envelope_option_example_uses_structured_outer_media_type():
    source = (ROOT / "endpoint" / "spec.md").read_text(encoding="utf-8")
    section = source.split("#### `envelopeoptions`", 1)[1].split(
        "This specification defines", 1
    )[0]
    options = json.loads(re.search(r"`(\{.*\})`", section)[1])
    layers = content_layers({
        "envelopeoptions": options, "datacontenttype": "application/xml"
    })
    assert layers == ContentLayers(
        "application/xml", "application/cloudevents+json", "application/cloudevents+json"
    )


@pytest.mark.parametrize(
    ("media", "wire", "expected_data"),
    [
        ("application/json", '{"datacontenttype":"application/json","data":{"id":42}}', {"id": 42}),
        ("application/xml", '{"datacontenttype":"application/xml","data":"<order/>"}', "<order/>"),
        ("application/octet-stream", '{"datacontenttype":"application/octet-stream","data_base64":"AP8Q"}', b"\x00\xff\x10"),
    ],
)
def test_json_event_payload_shapes_keep_their_own_media_types(media, wire, expected_data):
    message = _message("structured", media)
    decoded = json.loads(wire)
    if "data_base64" in decoded:
        assert "data" not in decoded
        assert base64.b64decode(decoded["data_base64"], validate=True) == expected_data
    else:
        assert decoded["data"] == expected_data
    layers = content_layers(message, event_media=decoded["datacontenttype"])
    assert layers.payload == media
    assert layers.wire == "application/cloudevents+json"


@pytest.mark.parametrize("location", ["top", "metadata"])
def test_one_explicit_payload_declaration_determines_only_the_data_layer(location):
    message = _message("structured", "application/xml")
    if location == "top":
        del message["envelopemetadata"]["datacontenttype"]
    else:
        del message["datacontenttype"]
    assert content_layers(message).payload == "application/xml"
    assert content_layers(message).envelope == "application/cloudevents+json"


def test_schema_language_and_envelope_format_do_not_invent_payload_media_type():
    message = _message("structured", "application/xml")
    del message["datacontenttype"]
    del message["envelopemetadata"]["datacontenttype"]
    message["dataschemaformat"] = "Protobuf/3"
    assert content_layers(message) == ContentLayers(
        None, "application/cloudevents+json", "application/cloudevents+json"
    )
    assert content_layers(message, event_media="application/json").payload == "application/json"
    del message["envelopeoptions"]["format"]
    assert content_layers(message) == ContentLayers(None, None, None)


@pytest.mark.parametrize("conflict", ["declaration", "event", "wire"])
def test_genuine_same_layer_conflicts_fail_without_cross_layer_equality(conflict):
    message = _message("structured", "application/xml")
    arguments = {}
    if conflict == "declaration":
        message["envelopemetadata"]["datacontenttype"]["value"] = "application/json"
    elif conflict == "event":
        arguments["event_media"] = "application/json"
    else:
        arguments["wire_media"] = "application/xml"
    with pytest.raises(ValueError, match="same layer"):
        content_layers(message, **arguments)


def test_binary_content_type_is_payload_and_format_is_not_applicable():
    message = _message("binary", "application/xml")
    assert content_layers(message, wire_media="application/xml").wire == "application/xml"
    with pytest.raises(ValueError, match="same layer"):
        content_layers(message, wire_media="application/cloudevents+json")
    message["envelopeoptions"]["format"] = "application/cloudevents+json"
    with pytest.raises(ValueError, match="binary mode"):
        content_layers(message)


def test_media_type_comparison_preserves_parameter_value_semantics_and_input():
    message = _message("structured", "text/plain; charset=utf-8")
    message["envelopemetadata"]["datacontenttype"]["value"] = "TEXT/Plain; CharSet=UTF-8"
    original = deepcopy(message)
    assert content_layers(message).payload == "text/plain; charset=utf-8"
    assert message == original
    message["datacontenttype"] = "application/example; profile=Case"
    message["envelopemetadata"]["datacontenttype"]["value"] = "application/example; profile=case"
    with pytest.raises(ValueError, match="same layer"):
        content_layers(message)


@pytest.mark.parametrize("media", [None, "", "xml", 1, "text/plain\r\nInjected: true"])
def test_invalid_explicit_media_types_do_not_become_absent_or_defaults(media):
    message = _message("structured", media)
    with pytest.raises(ValueError, match="invalid media type"):
        content_layers(message)


@pytest.mark.parametrize("mode", [None, "Binary", "batched"])
def test_checker_reports_modes_outside_its_explicit_scope(mode):
    message = _message("binary", "application/xml")
    message["envelopeoptions"]["mode"] = mode
    with pytest.raises(ValueError, match="explicit content mode"):
        content_layers(message)


def test_duplicate_parameters_are_not_silently_overwritten():
    message = _message("binary", "text/plain; charset=utf-8; charset=ascii")
    with pytest.raises(ValueError, match="duplicate media type parameter"):
        content_layers(message)
