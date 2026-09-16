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
from openapi_schema_validator import OAS30ReadValidator, OAS30WriteValidator
from openapi_spec_validator import validate


ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("schema_generator", ROOT / "tools" / "schema-generator.py")
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)
MODEL_SCHEMA = json.loads((ROOT / "core" / "model.schema.json").read_text(encoding="utf-8"))
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


def validate_model(model):
    jsonschema.Draft7Validator(MODEL_SCHEMA).validate(model)


def operation_validator(openapi, representation, request=False):
    validator = OAS30WriteValidator if request else OAS30ReadValidator
    return validator(
        {**representation, "components": openapi["components"]},
        format_checker=jsonschema.FormatChecker(),
    )


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


def generate_version_openapi(hasdocument, maxversions):
    model = copy.deepcopy(MODEL)
    resource = model["groups"]["catalogs"]["resources"]["entries"]
    resource.update(hasdocument=hasdocument, maxversions=maxversions)
    model["groups"]["mirrors"] = {
        "singular": "mirror",
        "ximportresources": ["/catalogs/entries"],
    }
    validate_model(model)
    return GENERATOR.generate_openapi(model)


def ordinary_version(group, hasdocument):
    xid = f"/{group}/c/entries/e/versions/v1"
    return {
        "entryid": "e",
        "versionid": "v1",
        "self": "https://example.com" + xid + (
            "$details" if hasdocument else ""
        ),
        "xid": xid,
        "epoch": 1,
        "createdat": "2026-01-01T00:00:00Z",
        "modifiedat": "2026-01-01T00:00:00Z",
        "ancestorid": "v1",
        "isdefault": True,
        "endpoints": [{"uri": "https://example.com", "priority": 0}],
    }


def assert_version_metadata(
    openapi, representation, version, collection=False, request=False,
    allow_resource_readonly=False,
):
    validator = operation_validator(openapi, representation, request)

    def body(value):
        return {"v1": value} if collection else value

    validator.validate(body(version))
    for name, value in (
        ("versionid", 7),
        ("entryid", 7),
        ("isdefault", "true"),
        ("endpoints", "https://example.com"),
    ):
        with pytest.raises(jsonschema.ValidationError) as error:
            validator.validate(body({**version, name: value}))
        assert error.value.validator == "type"
        assert list(error.value.absolute_path) == (
            ["v1", name] if collection else [name]
        )

    for value in (7, [], "v1"):
        with pytest.raises(jsonschema.ValidationError) as error:
            validator.validate(body(value))
        assert error.value.validator == "type"
        assert list(error.value.absolute_path) == (["v1"] if collection else [])

    for name, value in (
        ("meta", {}),
        ("metaurl", "https://example.com/catalogs/c/entries/e/meta"),
        ("versions", {}),
        ("versionsurl", "https://example.com/catalogs/c/entries/e/versions"),
        ("versionscount", 1),
    ):
        if allow_resource_readonly:
            validator.validate(body({**version, name: value}))
        else:
            with pytest.raises(jsonschema.ValidationError):
                validator.validate(body({**version, name: value}))

    if collection:
        with pytest.raises(jsonschema.ValidationError) as error:
            validator.validate([version])
        assert error.value.validator == "type"


@pytest.mark.parametrize("hasdocument", [False, True])
@pytest.mark.parametrize("maxversions", [0, 1])
@pytest.mark.parametrize("group", ["catalogs", "mirrors"])
def test_openapi_version_routes_use_version_metadata(
    hasdocument, maxversions, group
):
    schema = generate_version_openapi(hasdocument, maxversions)
    validate(schema)
    version = ordinary_version(group, hasdocument)
    base = f"/{group}/{{groupid}}/entries/{{resourceid}}"
    reference = {"$ref": "#/components/schemas/entryVersion"}
    collection = {"type": "object", "additionalProperties": reference}
    versions = schema["paths"][base + "/versions"]
    for content, request in (
        (versions["get"]["responses"]["200"]["content"], False),
        (versions["post"]["requestBody"]["content"], True),
        (versions["post"]["responses"]["200"]["content"], False),
    ):
        assert set(content) == {"application/json"}
        representation = content["application/json"]["schema"]
        assert representation == collection
        assert_version_metadata(
            schema, representation, version, collection=True, request=request
        )

    for suffix in ("/versions/{versionid}", "/versions/{versionid}$details"):
        path = schema["paths"][base + suffix]
        assert all(
            parameter.get("name") != "meta"
            for parameter in path.get("parameters", [])
        )
        content = path["get"]["responses"]["200"]["content"]
        if not hasdocument or suffix.endswith("$details"):
            assert set(content) == {"application/json"}
            representation = content["application/json"]["schema"]
            assert representation == reference
            assert_version_metadata(schema, representation, version)

    properties = schema["components"]["schemas"]["entryVersion"]["properties"]
    assert properties["versionid"]["type"] == "string"
    assert not {
        "meta", "metaurl", "versions", "versionsurl", "versionscount"
    } & properties.keys()
    resource_schema = schema["components"]["schemas"]["entry"]
    assert {"meta", "metaurl"} <= resource_schema["properties"].keys()
    resource = {
        "entryid": "e",
        "meta": {"defaultversionid": "v1", "deprecated": {}},
        "metaurl": f"https://example.com/{group}/c/entries/e/meta",
    }
    if maxversions != 1:
        resource["versionsurl"] = (
            f"https://example.com/{group}/c/entries/e/versions"
        )
    jsonschema.Draft7Validator(resource_schema).validate(resource)
    resource_path = schema["paths"][base]
    resource_reference = {"$ref": "#/components/schemas/entry"}
    if not hasdocument:
        assert resource_path["get"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"] == resource_reference
    if hasdocument:
        post = resource_path["post"]
        for content in (
            post["requestBody"]["content"],
            post["responses"]["201"]["content"],
        ):
            assert set(content) == {
                "application/json", "application/octet-stream"
            }
            assert "$ref" not in content["application/json"]["schema"]


@pytest.mark.parametrize("message", ["request", "response"])
@pytest.mark.parametrize("maxversions", [0, 1])
@pytest.mark.parametrize("group", ["catalogs", "mirrors"])
def test_openapi_metadata_only_resource_post_uses_version_metadata(
    message, maxversions, group
):
    schema = generate_version_openapi(False, maxversions)
    validate(schema)
    base = f"/{group}/{{groupid}}/entries/{{resourceid}}"
    post = schema["paths"][base]["post"]
    content = (
        post["requestBody"]["content"] if message == "request"
        else post["responses"]["201"]["content"]
    )
    assert set(content) == {"application/json"}
    representation = content["application/json"]["schema"]
    assert_version_metadata(
        schema, representation, ordinary_version(group, False),
        request=message == "request", allow_resource_readonly=message == "request",
    )
    component = "entryVersionInput" if message == "request" else "entryVersion"
    assert representation == {"$ref": f"#/components/schemas/{component}"}


@pytest.mark.parametrize("maxversions", [0, 1])
@pytest.mark.parametrize("group", ["catalogs", "mirrors"])
def test_openapi_resource_post_ignores_resource_readonly_fields(maxversions, group):
    schema = generate_version_openapi(False, maxversions)
    validate(schema)
    post = schema["paths"][f"/{group}/{{groupid}}/entries/{{resourceid}}"]["post"]
    write = operation_validator(
        schema, post["requestBody"]["content"]["application/json"]["schema"],
        request=True,
    )
    read = operation_validator(
        schema, post["responses"]["201"]["content"]["application/json"]["schema"]
    )
    version = ordinary_version(group, False)
    write.validate(version)
    read.validate(version)
    for name in ("versionscount", "versionsurl", "versions", "metaurl", "meta"):
        for ignored in (7, "ignored", False, [], {}, None):
            body = {**version, name: ignored}
            write.validate(body)
            with pytest.raises(jsonschema.ValidationError) as error:
                read.validate(body)
            assert error.value.validator == "not"
    with pytest.raises(jsonschema.ValidationError) as error:
        write.validate({**version, "versionscount": [], "endpoints": "invalid"})
    assert error.value.validator == "type"
    assert list(error.value.absolute_path) == ["endpoints"]


@pytest.mark.parametrize("maxversions", [0, 1])
@pytest.mark.parametrize("group", ["catalogs", "mirrors"])
@pytest.mark.parametrize(
    "suffix,method,message",
    [
        ("", "get", "200"),
        ("", "put", "request"),
        ("", "put", "200"),
        ("", "post", "request"),
        ("", "post", "201"),
        ("/versions/{versionid}", "get", "200"),
    ],
    ids=[
        "resource-get", "resource-put-request", "resource-put-response",
        "resource-post-request", "resource-post-response", "version-get",
    ],
)
def test_openapi_document_routes_keep_json_domain_content(
    maxversions, group, suffix, method, message,
):
    schema = generate_version_openapi(True, maxversions)
    validate(schema)
    base = f"/{group}/{{groupid}}/entries/{{resourceid}}"
    operation = schema["paths"][base + suffix][method]
    content = (
        operation["requestBody"]["content"] if message == "request"
        else operation["responses"][message]["content"]
    )
    validator = operation_validator(
        schema, content["application/json"]["schema"], request=message == "request"
    )
    business_document = {"entry": "opaque business field", "versionid": 7}
    for value in (business_document, {}, [business_document], "text", 7, False, None):
        validator.validate(value)

    metadata = schema["paths"][base + "/versions/{versionid}$details"]["get"]
    read = operation_validator(
        schema, metadata["responses"]["200"]["content"]["application/json"]["schema"]
    )
    version = ordinary_version(group, True)
    read.validate(version)
    with pytest.raises(jsonschema.ValidationError) as error:
        read.validate({**version, "versionid": 7})
    assert error.value.validator == "type"
    assert list(error.value.absolute_path) == ["versionid"]
    with pytest.raises(jsonschema.ValidationError):
        read.validate(business_document)

    assert set(schema["paths"][base + "/versions/{versionid}"]) == {
        "parameters", "get", "delete",
    }
    assert set(schema["paths"][base + "$details"]) == {"parameters", "get"}
