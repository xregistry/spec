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


def avro_nonnullable(schema):
    if isinstance(schema, avro.schema.UnionSchema):
        return next(branch for branch in schema.schemas if branch.type != "null")
    return schema


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


@pytest.mark.parametrize("maxversions", [0, 1])
@pytest.mark.parametrize("distinct_fields", [False, True], ids=["same-fields", "different-fields"])
@pytest.mark.parametrize(
    "containers",
    [(), ("array",), ("map",), ("array", "map"), ("map", "array"), ("object",)],
    ids=["direct", "array", "map", "array-map", "map-array", "nested-object"],
)
def test_avro_structured_records_keep_resource_ownership(
    maxversions, distinct_fields, containers,
):
    model = {
        "groups": {
            "catalogs": {
                "plural": "catalogs", "singular": "catalog",
                "attributes": {"*": {"name": "*", "type": "any"}},
                "resources": {},
            },
            "mirrors": {
                "plural": "mirrors", "singular": "mirror",
                "ximportresources": ["/catalogs/entries", "/catalogs/pages"],
            },
        }
    }
    samples = {}
    for plural, singular in (("entries", "entry"), ("pages", "page")):
        different = distinct_fields and plural == "pages"
        definition = {
            "type": "object",
            "attributes": {
                "enabled" if different else "value": {
                    "type": "boolean" if different else "string", "required": True,
                }
            },
        }
        sample = {"enabled": True} if different else {"value": "owner value"}
        for container in reversed(containers):
            if container == "object":
                definition = {
                    "type": "object",
                    "attributes": {"nested": {**definition, "required": True}},
                }
                sample = {"nested": sample}
            else:
                definition = {"type": container, "item": definition}
                sample = [sample] if container == "array" else {"primary": sample}
        model["groups"]["catalogs"]["resources"][plural] = {
            "plural": plural, "singular": singular,
            "hasdocument": False, "maxversions": maxversions,
            "attributes": {"settings": {**definition, "required": True}},
        }
        samples[plural] = sample
    validate_model(model)
    schema = GENERATOR.generate_avro_schema(copy.deepcopy(model))
    parsed = avro.schema.parse(json.dumps(schema))
    assert schema == GENERATOR.generate_avro_schema(copy.deepcopy(model))
    catalog = parsed.fields_dict["catalogs"].type.values
    mirror = parsed.fields_dict["mirrors"].type.values
    fullnames = []
    for plural in ("entries", "pages"):
        resource = catalog.fields_dict[plural].type.values
        assert mirror.fields_dict[plural].type.values is resource
        version = resource if maxversions == 1 else resource.fields_dict["versions"].type.values
        settings = version.fields_dict["settings"].type
        assert avro.io.validate(settings, samples[plural])
        assert not avro.io.validate(settings, None)
        leaf = settings
        for container in containers:
            if container == "object":
                assert leaf.type == "record"
                leaf = leaf.fields_dict["nested"].type
            elif container == "array":
                assert leaf.type == "array"
                leaf = leaf.items
            else:
                assert leaf.type == "map"
                leaf = leaf.values
        assert leaf.type == "record"
        assert leaf.namespace == "io.xregistry.catalogs"
        fullnames.append(leaf.fullname)
        if distinct_fields and plural == "pages":
            assert set(leaf.fields_dict) == {"enabled"}
            assert leaf.fields_dict["enabled"].type.type == "boolean"
            assert not avro.io.validate(leaf, {"value": "wrong owner"})
        else:
            assert set(leaf.fields_dict) == {"value"}
            assert leaf.fields_dict["value"].type.type == "string"
            assert not avro.io.validate(leaf, {"value": 7})
    assert len(set(fullnames)) == 2


@pytest.mark.parametrize("owner", ["registry", "group", "singleton", "version", "meta"])
@pytest.mark.parametrize("container", ["object", "array", "map"])
def test_avro_structured_wildcards_keep_value_definitions(owner, container):
    leaf = {
        "type": "object",
        "attributes": {
            "value": {"type": "string", "required": True},
            "options": {
                "type": "object", "required": True,
                "attributes": {"enabled": {"type": "boolean", "required": True}},
            },
        },
    }
    wildcard = leaf if container == "object" else {"type": container, "item": leaf}
    attributes = {"*": {"name": "*", **wildcard}}
    model = {"groups": {}}
    if owner == "registry":
        model["attributes"] = attributes
    else:
        group = {"plural": "catalogs", "singular": "catalog", "resources": {}}
        model["groups"]["catalogs"] = group
        if owner == "group":
            group["attributes"] = attributes
        else:
            resource = {
                "plural": "entries", "singular": "entry", "hasdocument": False,
                "maxversions": 1 if owner == "singleton" else 0,
            }
            group["resources"]["entries"] = resource
            resource["metaattributes" if owner == "meta" else "attributes"] = attributes
    validate_model(model)
    parsed = avro.schema.parse(json.dumps(GENERATOR.generate_avro_schema(model)))
    record = parsed
    if owner != "registry":
        record = record.fields_dict["catalogs"].type.values
    if owner in ("singleton", "version", "meta"):
        record = record.fields_dict["entries"].type.values
    if owner == "version":
        record = record.fields_dict["versions"].type.values
    elif owner == "meta":
        record = avro_nonnullable(record.fields_dict["meta"].type)
    extensions = record.fields_dict["Extensions"].type
    value = extensions.values
    if container == "array":
        value = value.items
    elif container == "map":
        value = value.values
    assert value.type == "record"
    assert set(value.fields_dict) == {"value", "options"}
    assert value.namespace == ("io.xregistry" if owner == "registry" else "io.xregistry.catalogs")
    assert value.fields_dict["value"].type.type == "string"
    options = value.fields_dict["options"].type
    assert set(options.fields_dict) == {"enabled"}
    assert options.fields_dict["enabled"].type.type == "boolean"
    good = {"value": "x", "options": {"enabled": True}}
    bad = {"value": 7, "options": {"enabled": True}}
    if container == "array":
        good, bad = [good], [bad]
    elif container == "map":
        good, bad = {"primary": good}, {"primary": bad}
    assert avro.io.validate(extensions, {"settings": good})
    assert not avro.io.validate(extensions, {"settings": bad})
    assert not avro.io.validate(options, {"enabled": "true"})


@pytest.mark.parametrize("maxversions", [0, 1, 2])
@pytest.mark.parametrize(
    "name,type_name,required,good,bad",
    [
        ("isdefault", "boolean", True, True, "true"),
        ("ancestorid", "string", False, "v1", 7),
        ("contenttype", "string", True, "application/json", []),
    ],
    ids=["isdefault", "ancestorid", "contenttype"],
)
def test_avro_version_core_overlays_emit_one_field(
    maxversions, name, type_name, required, good, bad,
):
    model = copy.deepcopy(MODEL)
    model["groups"]["catalogs"]["resources"]["entries"].update({
        "maxversions": maxversions,
        "attributes": {
            name: {
                "name": name, "type": type_name, "required": required,
                "readonly": True, "description": "Modeled Core field",
            }
        },
    })
    validate_model(model)
    parsed = avro.schema.parse(json.dumps(GENERATOR.generate_avro_schema(model)))
    resource = parsed.fields_dict["catalogs"].type.values.fields_dict["entries"].type.values
    version = resource if maxversions == 1 else resource.fields_dict["versions"].type.values
    assert [item.name for item in version.fields].count(name) == 1
    overlay = version.fields_dict[name]
    assert overlay.get_prop("doc") == "Modeled Core field"
    assert avro_nonnullable(overlay.type).type == type_name
    assert avro.io.validate(overlay.type, good)
    assert not avro.io.validate(overlay.type, bad)
    assert avro.io.validate(overlay.type, None) is (not required)


@pytest.mark.parametrize("later_groups", [False, True], ids=["no-groups", "later-groups"])
def test_avro_registry_ifvalues_uses_root_namespace(later_groups):
    attributes = {
        "kind": {
            "name": "kind", "type": "string",
            "ifvalues": {
                "external": {
                    "siblingattributes": {
                        "location": {"name": "location", "type": "uri"},
                        "settings": {
                            "type": "object",
                            "attributes": {"enabled": {"type": "boolean", "required": True}},
                        },
                    }
                }
            },
        }
    }
    model = {"attributes": copy.deepcopy(attributes), "groups": {}}
    if later_groups:
        model["groups"]["catalogs"] = {
            "plural": "catalogs", "singular": "catalog",
            "attributes": copy.deepcopy(attributes),
            "resources": {
                "entries": {
                    "plural": "entries", "singular": "entry",
                    "hasdocument": False, "maxversions": 0,
                    "attributes": copy.deepcopy(attributes),
                    "metaattributes": copy.deepcopy(attributes),
                },
                "pages": {
                    "plural": "pages", "singular": "page",
                    "hasdocument": False, "maxversions": 1,
                    "attributes": copy.deepcopy(attributes),
                },
            },
        }
    validate_model(model)
    parsed = avro.schema.parse(json.dumps(GENERATOR.generate_avro_schema(model)))
    owners = [(parsed, "io.xregistry")]
    if later_groups:
        group = parsed.fields_dict["catalogs"].type.values
        resource = group.fields_dict["entries"].type.values
        owners.extend((record, "io.xregistry.catalogs") for record in (
            group,
            resource.fields_dict["versions"].type.values,
            avro_nonnullable(resource.fields_dict["meta"].type),
            group.fields_dict["pages"].type.values,
        ))
    fullnames = []
    for owner, namespace in owners:
        conditional = owner.fields_dict["kind"].type.schemas[0]
        assert conditional.type == "record"
        assert conditional.namespace == namespace
        fullnames.append(conditional.fullname)
        settings = avro_nonnullable(conditional.fields_dict["settings"].type)
        assert settings.namespace == namespace
        assert avro.io.validate(conditional, {
            "location": "https://example.com/catalog", "settings": {"enabled": True},
        })
        assert not avro.io.validate(conditional, {"location": 7})
        assert not avro.io.validate(conditional, {"settings": {"enabled": "true"}})
    assert len(set(fullnames)) == len(owners)
