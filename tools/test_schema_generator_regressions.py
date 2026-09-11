"""Core schema-generator regressions independent of federation working drafts."""

import copy
import importlib.util
import io
import json
from datetime import datetime, timezone
from pathlib import Path

import avro.schema
import avro.io
import jsonschema
import pytest
from openapi_spec_validator import validate


ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("schema_generator", ROOT / "tools" / "schema-generator.py")
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)
MODEL = {
    "groups": {
        "catalogs": {
            "singular": "catalog",
            "resources": {
                "entries": {
                    "singular": "entry",
                    "hasdocument": False,
                    "attributes": {
                        "endpoints": {
                            "type": "array",
                            "item": {
                                "type": "object",
                                "attributes": {
                                    "uri": {"type": "uri", "required": True},
                                    "priority": {"type": "uinteger"},
                                },
                            },
                        }
                    },
                }
            },
        }
    }
}


def generate(kind):
    model = copy.deepcopy(MODEL)
    if kind == "json":
        return GENERATOR.generate_json_schema(model)
    if kind == "structure":
        return GENERATOR.generate_json_structure(model)
    if kind == "avro":
        return GENERATOR.generate_avro_schema(model)
    return GENERATOR.generate_openapi(model)


def field(record, name):
    return next(value for value in record["fields"] if value["name"] == name)


def nonnullable(value):
    return next(item for item in value if item != "null") if isinstance(value, list) else value


@pytest.mark.parametrize("mutation", ["valid", "negative-priority", "bad-versions", "bad-url", "negative-count"])
def test_jsonschema_validates_inlined_versions_and_navigation_independently(mutation):
    schema = generate("json")
    jsonschema.Draft7Validator.check_schema(schema)
    resource = {
        "versionsurl": "#/catalogs/c/entries/e/versions",
        "versionscount": 1,
        "versions": {"v1": {"endpoints": [{"uri": "https://example.com", "priority": 0}]}},
    }
    if mutation == "negative-priority":
        resource["versions"]["v1"]["endpoints"][0]["priority"] = -1
    elif mutation == "bad-versions":
        resource["versions"] = []
    elif mutation == "bad-url":
        resource["versionsurl"] = 7
    elif mutation == "negative-count":
        resource["versionscount"] = -1
    validator = jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker())
    document = {"catalogs": {"c": {"entries": {"e": resource}}}}
    if mutation == "valid":
        validator.validate(document)
    else:
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(document)


def test_jsonschema_document_view_accepts_relative_self_and_document_uri():
    schema = generate("json")
    document = {
        "registryid": "catalog", "self": "#",
        "catalogs": {"c": {"self": "#/catalogs/c", "entries": {
            "e": {
                "self": "#/catalogs/c/entries/e", "versionsurl": "#/catalogs/c/entries/e/versions",
                "versions": {"v1": {"self": "#/catalogs/c/entries/e/versions/v1"}},
            }
        }}},
    }
    jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker()).validate(document)


def test_avro_structured_arrays_and_core_timestamps_are_valid():
    schema = generate("avro")
    avro.schema.parse(json.dumps(schema))
    group = field(schema, "catalogs")["type"]["values"]
    resource = field(group, "entries")["type"]["values"]
    versions = field(resource, "versions")["type"]["values"]
    endpoints = nonnullable(field(versions, "endpoints")["type"])
    assert endpoints["type"] == "array"
    assert endpoints["items"]["type"] == "record"
    assert field(endpoints["items"], "uri")["type"] == "string"
    for record in (schema, group, resource, versions):
        for name in ("createdat", "modifiedat"):
            assert nonnullable(field(record, name)["type"]) == {
                "type": "long", "logicalType": "timestamp-millis"
            }


def test_jsonstructure_includes_core_root_and_meta_properties():
    schema = generate("structure")
    assert {"registryid", "specversion", "self", "modelsource", "capabilities"} <= set(schema["properties"])
    resource = schema["definitions"]["Catalogs"]["Entry"]["properties"]
    assert {"meta", "metaurl", "versions", "versionsurl", "versionscount"} <= set(resource)
    assert resource["meta"]["properties"]["defaultversionid"] == {"type": "string"}


def test_openapi_exposes_collection_and_version_metadata_without_fake_documents():
    schema = generate("openapi")
    validate(schema)
    assert "/catalogs" in schema["paths"]
    base = "/catalogs/{groupid}/entries/{resourceid}"
    for suffix, expected in (
        ("", {"$ref": "#/components/schemas/entry"}),
        ("/versions", {"type": "object", "additionalProperties": {"$ref": "#/components/schemas/entryVersion"}}),
        ("/versions/{versionid}", {"$ref": "#/components/schemas/entryVersion"}),
        ("/versions/{versionid}$details", {"$ref": "#/components/schemas/entryVersion"}),
    ):
        path = schema["paths"][base + suffix]
        content = path["get"]["responses"]["200"]["content"]
        assert set(content) == {"application/json"}
        assert content["application/json"]["schema"] == expected
        assert all(parameter.get("name") != "meta" for parameter in path.get("parameters", []))


def test_avro_core_root_customization_overlays_existing_field():
    model = copy.deepcopy(MODEL)
    model["attributes"] = {
        "name": {"type": "string", "required": True, "description": "Required name"}
    }
    value = GENERATOR.generate_avro_schema(model)
    parsed = avro.schema.parse(json.dumps(value))
    assert [item["name"] for item in value["fields"]].count("name") == 1
    assert parsed.fields_dict["name"].type.type == "string"
    assert parsed.fields_dict["name"].get_prop("doc") == "Required name"
    assert not avro.io.validate(parsed.fields_dict["name"].type, None)


@pytest.mark.parametrize("state", [{}, {"alternative": "https://example.com/new"}])
def test_avro_meta_deprecation_encodes_a_structured_record(state):
    value = avro.schema.parse(json.dumps(generate("avro")))
    entry = value.fields_dict["catalogs"].type.values.fields_dict["entries"].type.values
    meta = next(part for part in entry.fields_dict["meta"].type.schemas if part.type != "null")
    stamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    data = {
        "entryid": "e", "name": None, "epoch": 1, "self": "#/meta",
        "xid": "/catalogs/c/entries/e/meta", "description": None, "documentation": None,
        "labels": {}, "createdat": stamp, "modifiedat": stamp, "xref": None,
        "readonly": False, "compatibility": None, "deprecated": state,
        "defaultversionid": "v1", "defaultversionurl": "#/versions/v1",
        "defaultversionsticky": True,
    }
    assert avro.io.validate(meta, data)
    output = io.BytesIO()
    avro.io.DatumWriter(meta).write(data, avro.io.BinaryEncoder(output))
    output.seek(0)
    decoded = avro.io.DatumReader(meta).read(avro.io.BinaryDecoder(output))
    assert {key: val for key, val in decoded["deprecated"].items() if val is not None} == state
    assert not avro.io.validate(meta, {**data, "deprecated": False})


def test_openapi_document_version_metadata_does_not_require_content():
    model = copy.deepcopy(MODEL)
    model["groups"]["catalogs"]["resources"]["entries"]["hasdocument"] = True
    schema = GENERATOR.generate_openapi(model)
    path = "/catalogs/{groupid}/entries/{resourceid}/versions/{versionid}$details"
    assert schema["paths"][path]["get"]["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/entryVersion"
    }
    validator = jsonschema.Draft7Validator(schema["components"]["schemas"]["entryVersion"])
    validator.validate({"entryid": "e", "versionid": "v1"})
    with pytest.raises(jsonschema.ValidationError):
        validator.validate({"entryid": "e", "versionid": "v1", "entrybase64": 5})
    with pytest.raises(jsonschema.ValidationError):
        validator.validate({"entryid": "e", "versionid": "v1", "entry": {}, "entrybase64": ""})
