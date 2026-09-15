"""Concrete Metrics literal/field guards, not a general Protobuf compiler."""

from pathlib import Path

import pytest
import yaml


SPEC = (Path(__file__).resolve().parents[1] / "schema" / "spec.md").read_text(
    encoding="utf-8"
)
BLOCK = SPEC.split(
    "The following abbreviated example shows three embedded `Protobuf/3`", 1
)[1].split("```yaml\n", 1)[1].split("\n```", 1)[0]
REGISTRY = yaml.safe_load(BLOCK)
RESOURCE = REGISTRY["schemagroups"]["com.example.telemetry"]["schemas"][
    "com.example.telemetrydata"
]
FIELDS = [("float", "metric", 1), ("string", "unit", 2), ("string", "description", 3)]


def _assert_metrics_literal(document, fields):
    assert document.count("{") == document.count("}") == 1
    declarations = " ".join(
        f"{field_type} {name} = {number};"
        for field_type, name, number in fields
    )
    assert document == 'syntax = "proto3"; message Metrics { ' + declarations + " }"


@pytest.mark.parametrize("version, field_count", [("default", 3), ("1", 1), ("2", 2), ("3", 3)])
def test_each_metrics_literal_retains_fields_with_one_closing_brace(version, field_count):
    entity = RESOURCE if version == "default" else RESOURCE["versions"][version]
    assert entity["format"] == "Protobuf/3"
    _assert_metrics_literal(entity["schema"], FIELDS[:field_count])


def test_schema_versions_lineage_and_default_projection_are_preserved():
    versions = RESOURCE["versions"]
    assert set(versions) == {"1", "2", "3"}
    assert RESOURCE["versionscount"] == len(versions) == 3
    assert {key: version["ancestorid"] for key, version in versions.items()} == {
        "1": "1", "2": "1", "3": "2"
    }
    assert {key: version["isdefault"] for key, version in versions.items()} == {
        "1": False, "2": False, "3": True
    }
    assert RESOURCE["versionid"] == "3"
    for field in (
        "schemaid", "versionid", "isdefault", "description", "ancestorid", "format", "schema"
    ):
        assert RESOURCE[field] == versions["3"][field]


@pytest.mark.parametrize("defect", ["extra_closing_brace", "duplicate_field_number"])
def test_metrics_literal_guard_rejects_bad_delimiter_and_field_changes(defect):
    document = RESOURCE["versions"]["3"]["schema"]
    if defect == "extra_closing_brace":
        document += " }"
    else:
        document = document.replace("unit = 2;", "unit = 1;")
    with pytest.raises(AssertionError):
        _assert_metrics_literal(document, FIELDS)
