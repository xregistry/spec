import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _model_metadata():
    model = json.loads((ROOT / "message" / "model.json").read_text(encoding="utf-8"))
    return model["groups"]["messagegroups"]["resources"]["messages"]["attributes"][
        "envelope"
    ]["ifvalues"]["CloudEvents/1.0"]["siblingattributes"]["envelopemetadata"][
        "attributes"
    ]


def test_model_has_flat_cloud_event_metadata_declarations():
    model = _model_metadata()
    assert {"type", "source", "subject"} <= model.keys()
    assert "attributes" not in model
