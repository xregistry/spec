"""Message definitions carry typed literals, not Core metadata attributes."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_declaration_sections_preserve_literal_nulls_and_protocol_names():
    model = json.loads((ROOT / "message" / "model.json").read_text(encoding="utf-8"))
    attributes = model["groups"]["messagegroups"]["resources"]["messages"]["attributes"]
    sections = [attributes["envelope"]["ifvalues"]["CloudEvents/1.0"]["siblingattributes"]["envelopemetadata"]]
    amqp = attributes["protocol"]["ifvalues"]["AMQP/1.0"]["siblingattributes"]["protocoloptions"]["attributes"]
    sections.extend(amqp[name] for name in ("properties", "application-properties", "message-annotations", "delivery-annotations", "footer"))
    assert len(sections) == 6
    for section in sections:
        assert section["type"] == "any"
        assert "attributes" not in section and "item" not in section
        assert "domain" in section["description"]


def test_cloudevents_declarations_are_flat_and_duration_has_a_real_standard():
    prose = (ROOT / "message" / "spec.md").read_text(encoding="utf-8")
    assert "contains a property\n`attributes`" not in prose
    assert "RFC3339 Duration" not in prose
    assert "ISO 8601" in prose
