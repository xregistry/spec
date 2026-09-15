import json
from pathlib import Path
import re

import jsonpointer


SPEC = Path(__file__).resolve().parents[2] / "message" / "spec.md"


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, f"duplicate JSON key: {key}"
        result[key] = value
    return result


def _block_after(marker, language):
    section = SPEC.read_text(encoding="utf-8").split(marker, 1)[1]
    return re.search(r"```" + language + r"\n(.*?)\n```", section, re.S)[1]


def _without_comment_lines(fragment):
    return "\n".join(
        line for line in fragment.splitlines() if not line.lstrip().startswith("#")
    )


def _borrowed_fragment():
    fragment = _block_after("#### `envelope`\n", "yaml")
    return json.loads(
        "{\n" + _without_comment_lines(fragment) + "\n}",
        object_pairs_hook=_unique_object,
    )


def test_complete_context_example_is_strict_json_and_preserves_mqtt_fields():
    message = json.loads(
        _block_after("### Context Attributes\n", "json"),
        object_pairs_hook=_unique_object,
    )
    assert message["protocol"] == "MQTT/5.0"
    assert message["protocoloptions"]["topic_name"] == "/store/{storeid}/cashierdesk/{cdid}"
    assert message["protocoloptions"]["user_properties"] == [
        {"name": "eventType", "type": "uritemplate", "value": "{eventType}"}
    ]
    assert message["envelope"] == "CloudEvents/1.0"


def test_borrowed_fragment_nesting_counts_and_map_identities_agree():
    document = _borrowed_fragment()
    groups = document["messagegroups"]
    assert document["messagegroupscount"] == len(groups) == 2
    for group_id, group in groups.items():
        assert group["messagegroupid"] == group_id
        assert group["messagescount"] == len(group["messages"])
        for message_id, message in group["messages"].items():
            assert message["messageid"] == message_id
    assert set(groups["com.example.abc"]["messages"]) == {
        "com.example.abc.event1", "com.example.abc.event2"
    }
    assert groups["com.example.abc"]["messages"]["com.example.abc.event2"][
        "messageid"
    ] == "com.example.abc.event2"


def test_borrowed_message_uses_existing_one_hop_same_type_meta_xref():
    document = _borrowed_fragment()
    group = document["messagegroups"]["com.example.def"]
    borrowed = group["messages"]["com.example.abc.event1"]
    assert set(borrowed) == {"messageid", "meta"}
    reference = borrowed["meta"]["xref"]
    assert reference == "/messagegroups/com.example.abc/messages/com.example.abc.event1"
    assert reference.split("/")[1::2] == ["messagegroups", "messages"]
    target = jsonpointer.resolve_pointer(document, reference)
    assert "xref" not in target.get("meta", {})
    assert target["messageid"] == borrowed["messageid"]
    assert target["envelope"] == group["envelope"]


def test_declared_cloudevents_format_notation_normalizes_to_json_structure():
    fragment = _block_after(
        'The following shows the format of a CloudEvents "envelopemetadata" section',
        "yaml",
    )
    fragment = _without_comment_lines(fragment)
    fragment = re.sub(r"[ \t]+\?(?=[ \t]*$)", "", fragment, flags=re.M)
    fragment = fragment.replace(": <ANY>", ': "<ANY>"')
    definition = json.loads(
        "{\n" + fragment + "\n}", object_pairs_hook=_unique_object
    )
    assert definition["envelope"] == "CloudEvents/1.0"
    metadata = definition["envelopemetadata"]
    assert metadata["specversion"] == {"value": "1.0", "type": "string"}
    assert metadata["time"]["type"] == "timestamp"
    assert metadata["dataschema"]["type"] == "uritemplate"
    assert metadata["*"] == {"value": "<ANY>", "type": "<TYPE>"}
