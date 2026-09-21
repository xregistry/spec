"""The Endpoint storage model must retain unresolved protocol-option templates."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_all_protocol_options_have_an_explicit_authoring_boundary():
    model = json.loads((ROOT / "endpoint" / "model.json").read_text(encoding="utf-8"))
    variants = model["groups"]["endpoints"]["attributes"]["protocol"]["ifvalues"]
    assert set(variants) == {"AMQP/1.0", "MQTT/3.1.1", "MQTT/5.0", "HTTP", "KAFKA", "NATS"}
    for variant in variants.values():
        options = variant["siblingattributes"]["protocoloptions"]
        assert options["type"] == "any"
        assert "attributes" not in options and "item" not in options
        assert "authoring" in options["description"]


def test_prose_preserves_native_types_and_separates_storage_from_consumer_rules():
    prose = " ".join((ROOT / "endpoint" / "spec.md").read_text(encoding="utf-8").split())
    assert "opaque authoring" in prose
    assert "MUST NOT coerce" in prose
    assert "evaluating the metadata" in prose
