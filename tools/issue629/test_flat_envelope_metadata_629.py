import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, f"duplicate JSON key: {key}"
        result[key] = value
    return result


def _context_members():
    source = (ROOT / "message" / "spec.md").read_text(encoding="utf-8")
    section = source.split("### Context Attributes\n", 1)[1].split(
        "### Reusing Message Definitions", 1
    )[0]
    example = re.search(r"```json\n(.*?)\n```", section, re.S)[1]
    decoder = json.JSONDecoder(object_pairs_hook=_unique_object)
    members = {}
    for match in re.finditer(r'"(envelopeoptions|envelopemetadata)"\s*:\s*', example):
        name = match[1]
        assert name not in members
        members[name], _ = decoder.raw_decode(example[match.end():])
    return members


def _model_metadata():
    model = json.loads((ROOT / "message" / "model.json").read_text(encoding="utf-8"))
    return model["groups"]["messagegroups"]["resources"]["messages"]["attributes"][
        "envelope"
    ]["ifvalues"]["CloudEvents/1.0"]["siblingattributes"]["envelopemetadata"][
        "attributes"
    ]


def test_context_member_uses_flat_modelled_declarations_not_serialization_options():
    members = _context_members()
    metadata = members["envelopemetadata"]
    assert set(metadata) == {"type", "source", "subject"}
    model = _model_metadata()
    for name, declaration in metadata.items():
        assert name in model
        assert set(declaration) == {"type", "value"}
        assert declaration["type"] == "uritemplate"
        assert isinstance(declaration["value"], str) and declaration["value"]
    assert not ({"attributes", "type", "source", "subject"} & set(
        members.get("envelopeoptions", {})
    ))


def test_context_declarations_render_actual_source_type_and_subject_templates():
    metadata = _context_members()["envelopemetadata"]
    context = {"eventType": "com.example.receipt", "storeid": "store17", "cdid": "desk3"}
    rendered = {
        name: re.sub(r"\{(\w+)\}", lambda match: context[match[1]], definition["value"])
        for name, definition in metadata.items()
    }
    assert rendered == {
        "type": "com.example.receipt", "source": "store17", "subject": "desk3"
    }


def test_endpoint_complete_example_uses_flat_cloud_event_type_declaration():
    source = (ROOT / "endpoint" / "spec.md").read_text(encoding="utf-8")
    section = source.split("#### `messages`\n", 1)[1]
    example = re.search(r"```yaml\n(.*?)\n```", section, re.S)[1]
    endpoint = json.loads(example, object_pairs_hook=_unique_object)
    assert endpoint["messagescount"] == len(endpoint["messages"]) == 1
    message = endpoint["messages"]["myevent"]
    assert message["envelope"] == "CloudEvents/1.0"
    assert message["envelopemetadata"] == {"type": {"value": "myevent"}}
    assert "type" in _model_metadata()


def test_prose_uses_the_same_flat_surface_as_the_authoritative_model():
    model = _model_metadata()
    assert {"type", "source", "subject"} <= model.keys()
    assert "attributes" not in model
    source = (ROOT / "message" / "spec.md").read_text(encoding="utf-8")
    section = source.split("##### CloudEvents/1.0\n", 1)[1].split(
        "The base attributes are defined", 1
    )[0]
    assert "envelopemetadata.source" in section
    assert "envelopeoptions" in section
    assert "object contains a property\n`attributes`" not in section
