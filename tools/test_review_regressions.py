"""Regressions for the four actionable federation PR code-review findings."""

import copy
import importlib.util
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

import avro.io
import avro.schema
import jsonschema
import pytest

from federation_examples import FederationError, execute_selected, validate_profile


ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("schema_generator_review", ROOT / "tools" / "schema-generator.py")
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)
MODEL = {"groups": {"groups": {"singular": "group", "resources": {
    "entries": {"singular": "entry"}
}}}}


@pytest.mark.parametrize("level", ["registry", "group", "version", "meta"])
def test_avro_core_attribute_overrides_replace_instead_of_duplicate(level):
    model = copy.deepcopy(MODEL)
    if level == "registry":
        owner = model
    elif level == "group":
        owner = model["groups"]["groups"]
    else:
        owner = model["groups"]["groups"]["resources"]["entries"]
    key = "metaattributes" if level == "meta" else "attributes"
    owner[key] = {"name": {"type": "string", "required": True, "description": "Required display name"}}
    schema = avro.schema.parse(json.dumps(GENERATOR.generate_avro_schema(model)))
    records = [schema]
    seen = set()
    found = []

    def visit(node):
        if id(node) in seen:
            return
        seen.add(id(node))
        if isinstance(node, avro.schema.RecordSchema):
            names = [field.name for field in node.fields]
            assert len(names) == len(set(names))
            for field in node.fields:
                if field.name == "name" and field.get_prop("doc") == "Required display name":
                    found.append(field)
                visit(field.type)
        elif isinstance(node, avro.schema.UnionSchema):
            for branch in node.schemas:
                visit(branch)
        elif isinstance(node, avro.schema.MapSchema):
            visit(node.values)
        elif isinstance(node, avro.schema.ArraySchema):
            visit(node.items)

    visit(records[0])
    assert len(found) == 1
    assert found[0].type.type == "string"
    assert not avro.io.validate(found[0].type, None)


@pytest.mark.parametrize("deprecated", [
    {}, {"removal": datetime(2030, 1, 1, tzinfo=timezone.utc), "alternative": "https://example.com/new"},
])
def test_avro_meta_deprecation_round_trips_as_structured_data(deprecated):
    schema = avro.schema.parse(json.dumps(GENERATOR.generate_avro_schema(copy.deepcopy(MODEL))))
    group = schema.fields_dict["groups"].type.values
    entry = group.fields_dict["entries"].type.values
    meta = next(node for node in entry.fields_dict["meta"].type.schemas if node.type != "null")
    stamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    datum = {
        "entryid": "e", "name": None, "epoch": 1, "self": "#/meta",
        "xid": "/groups/g/entries/e/meta", "description": None, "documentation": None,
        "labels": {}, "createdat": stamp, "modifiedat": stamp, "xref": None,
        "readonly": False, "defaultversionid": "v1", "defaultversionurl": "#/versions/v1",
        "defaultversionsticky": True, "compatibility": None, "deprecated": deprecated,
    }
    assert avro.io.validate(meta, datum)
    output = io.BytesIO()
    avro.io.DatumWriter(meta).write(datum, avro.io.BinaryEncoder(output))
    output.seek(0)
    decoded = avro.io.DatumReader(meta).read(avro.io.BinaryDecoder(output))
    assert decoded["entryid"] == "e"
    assert {key: value for key, value in decoded["deprecated"].items() if value is not None} == deprecated
    assert not avro.io.validate(meta, {**datum, "deprecated": True})


@pytest.mark.parametrize("format_name", ["json", "openapi"])
@pytest.mark.parametrize("content", ["metadata", "inline", "base64", "url", "invalid-base64", "conflicting"])
def test_version_metadata_schema_does_not_require_domain_content(format_name, content):
    model = copy.deepcopy(MODEL)
    model["groups"]["groups"]["resources"]["entries"]["attributes"] = {
        "format": {"type": "string", "required": True}
    }
    if format_name == "json":
        document = GENERATOR.generate_json_schema(model)
        version = document["definitions"]["group-schema"]["entryVersion"]
    else:
        document = GENERATOR.generate_openapi(model)
        route = document["paths"]["/groups/{groupid}/entries/{resourceid}/versions/{versionid}$details"]
        assert route["get"]["responses"]["200"]["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/entryVersion"
        }
        version = document["components"]["schemas"]["entryVersion"]
    value = {"entryid": "e", "versionid": "v1", "format": "JSONSchema/draft-07"}
    if content == "inline":
        value["entry"] = {"type": "string"}
    elif content == "base64":
        value["entrybase64"] = ""
    elif content == "url":
        value["entryurl"] = "https://example.com/content"
    elif content == "invalid-base64":
        value["entrybase64"] = 9
    elif content == "conflicting":
        value.update(entry={}, entrybase64="")
    validator = jsonschema.Draft7Validator(version, format_checker=jsonschema.FormatChecker())
    if content in ("invalid-base64", "conflicting"):
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(value)
    else:
        validator.validate(value)
    with pytest.raises(jsonschema.ValidationError):
        validator.validate({key: item for key, item in value.items() if key != "format"})


@pytest.mark.parametrize("name", ["oci", "com.example.custom"])
@pytest.mark.parametrize("extra", [{"reference": "sha256:" + "1" * 64}, {"endpointurl": "https://other.example.com"}])
def test_advertisement_rejects_misplaced_envelope_fields_without_fallback(name, extra):
    profile = {
        "name": name, "endpoint": "oci://example.com/repo",
        "parameters": {"reference": "stable"}, **extra,
    }
    with pytest.raises(FederationError) as error:
        validate_profile(profile)
    assert error.value.code == "invalid_package"
    read = Mock()
    with pytest.raises(FederationError) as error:
        execute_selected({"federationprofiles": [profile]}, {name}, read)
    assert error.value.code == "invalid_package"
    read.assert_not_called()


def test_extension_parameters_remain_extensible_with_closed_envelope():
    profile = {
        "name": "com.example.custom", "endpoint": "custom:registry",
        "parameters": {"reference": "v1", "extra": {"mode": "pinned"}}
    }
    before = copy.deepcopy(profile)
    validate_profile(profile)
    assert profile == before
