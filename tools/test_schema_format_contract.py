"""Check Schema format aspects in the authoritative source model."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL = json.loads((ROOT / "schema" / "model.json").read_text(encoding="utf-8"))
GROUP_MODEL = MODEL["groups"]["schemagroups"]
VERSION_FORMAT = GROUP_MODEL["resources"]["schemas"]["attributes"]["format"]


def test_group_format_is_optional_and_constrains_schema_formats():
    assert GROUP_MODEL["attributes"]["format"] == {"type": "string"}
    assert GROUP_MODEL["constraints"]["schemas.format"] == {"equals": "format"}


def test_version_format_is_required_and_matches_across_versions():
    assert VERSION_FORMAT == {
        "type": "string", "required": True, "matchversions": True
    }


def test_format_and_group_equality_have_no_model_default():
    assert "default" not in VERSION_FORMAT
    assert "default" not in GROUP_MODEL["constraints"]["schemas.format"]
