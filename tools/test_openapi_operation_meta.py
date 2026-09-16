"""Actual-route request/response role regressions for the OpenAPI generator."""

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest
from openapi_schema_validator import OAS30ReadValidator, OAS30Validator, OAS30WriteValidator
from openapi_spec_validator import OpenAPIV30SpecValidator, validate


ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "schema_generator", ROOT / "tools" / "schema-generator.py"
)
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)
STAMP = "2026-01-01T00:00:00Z"
MODEL_SCHEMA = json.loads((ROOT / "core" / "model.schema.json").read_text(encoding="utf-8"))
MODEL = {
    "attributes": {
        "tenant": {"type": "string", "required": True},
        "region": {"type": "string", "required": True, "default": "global"},
        "serverstamp": {"type": "string", "required": True, "readonly": True},
        "settings": {"type": "object", "attributes": {
            "endpoint": {"type": "string", "required": True},
            "timeout": {"type": "integer", "required": True, "default": 10},
            "servervalue": {"type": "string", "required": True, "readonly": True},
        }},
    },
    "groups": {"catalogs": {
        "singular": "catalog",
        "attributes": {"kind": {"type": "string", "required": True}},
        "resources": {"entries": {
            "singular": "entry", "hasdocument": False, "maxversions": 0,
            "attributes": {"payload": {"type": "string", "required": True}},
            "metaattributes": {
                "owner": {"type": "string", "required": True},
                "policy": {"type": "string", "required": True, "default": "local"},
                "managed": {"type": "string", "required": True, "readonly": True},
            },
        }},
    }},
}


def generate(model=None):
    definition = MODEL if model is None else model
    jsonschema.Draft7Validator(MODEL_SCHEMA).validate(definition)
    return GENERATOR.generate_openapi(copy.deepcopy(definition))


def validator(openapi, schema, read=False):
    implementation = OAS30ReadValidator if read else OAS30WriteValidator
    return implementation(
        {**schema, "components": openapi["components"]},
        format_checker=OAS30Validator.FORMAT_CHECKER,
    )


def request(openapi, path, method):
    return validator(openapi, openapi["paths"][path][method]["requestBody"][
        "content"
    ]["application/json"]["schema"])


def response(openapi, path, method="get"):
    return validator(openapi, openapi["paths"][path][method]["responses"]["200"][
        "content"
    ]["application/json"]["schema"], read=True)


def registry_response():
    return {
        "registryid": "r", "specversion": "1.0",
        "self": "https://example.com/", "xid": "/", "epoch": 1,
        "createdat": STAMP, "modifiedat": STAMP,
        "tenant": "t", "region": "global", "serverstamp": "ready",
    }


@pytest.mark.parametrize("value", [{}, {"name": "foo"}, {"tenant": "other"}])
def test_root_patch_accepts_partial_input_without_response_fields(value):
    schema = generate()
    validate(schema)
    before = copy.deepcopy(value)
    request(schema, "/", "patch").validate(value)
    assert value == before


@pytest.mark.parametrize("method", ["get", "put", "patch"])
def test_root_completed_responses_keep_core_and_custom_requirements(method):
    schema = generate()
    checker = response(schema, "/", method)
    complete = registry_response()
    checker.validate(complete)
    for name in (
        "registryid", "specversion", "self", "xid", "epoch",
        "createdat", "modifiedat", "tenant", "region", "serverstamp",
    ):
        invalid = {key: value for key, value in complete.items() if key != name}
        with pytest.raises(jsonschema.ValidationError):
            checker.validate(invalid)


def test_root_put_preserves_client_required_but_not_server_or_default_obligations():
    schema = generate()
    checker = request(schema, "/", "put")
    checker.validate({"tenant": "t"})
    checker.validate({"tenant": "t", "region": None, "createdat": None})
    with pytest.raises(jsonschema.ValidationError):
        checker.validate({})
    with pytest.raises(jsonschema.ValidationError):
        checker.validate({"tenant": None})


@pytest.mark.parametrize("method", ["put", "patch"])
def test_readonly_input_is_ignored_without_inventing_server_fields(method):
    schema = generate()
    request(schema, "/", method).validate({
        "tenant": "t", "self": 7, "xid": False, "specversion": 7,
        "model": False, "serverstamp": 7,
    })
    with pytest.raises(jsonschema.ValidationError):
        request(schema, "/", method).validate({"tenant": "t", "createdat": 7})


@pytest.mark.parametrize("method", ["put", "patch"])
def test_provided_complex_attributes_are_complete_replacements_not_recursive_patches(method):
    schema = generate()
    checker = request(schema, "/", method)
    checker.validate({"tenant": "t", "settings": {"endpoint": "https://example.com"}})
    with pytest.raises(jsonschema.ValidationError):
        checker.validate({"tenant": "t", "settings": {}})
    with pytest.raises(jsonschema.ValidationError):
        checker.validate({"tenant": "t", "settings": {"endpoint": None}})
    request(schema, "/", "patch").validate({})


def test_root_collection_inputs_distinguish_replacement_and_patch_entity_roles():
    schema = generate()
    request(schema, "/", "put").validate({
        "tenant": "t", "catalogs": {"c": {"kind": "custom"}},
    })
    with pytest.raises(jsonschema.ValidationError):
        request(schema, "/", "put").validate({"tenant": "t", "catalogs": {"c": {}}})
    request(schema, "/", "patch").validate({"catalogs": {"c": {}}})
    request(schema, "/", "patch").validate({"catalogs": {"c": {"kind": "custom"}}})


@pytest.mark.parametrize("method", ["put", "patch"])
def test_request_wildcard_closure_preserves_declared_entity_members(method):
    selector = {"type": "string", "ifvalues": {
        "text": {"siblingattributes": {"*": {"type": "string"}}},
        "number": {"siblingattributes": {"*": {"type": "integer"}}},
    }}
    model = {"groups": {"catalogs": {
        "singular": "catalog",
        "attributes": {"mode": copy.deepcopy(selector)},
        "resources": {"entries": {
            "singular": "entry", "hasdocument": True,
            "attributes": {"mode": copy.deepcopy(selector)},
        }},
    }}}
    value = {"catalogs": {"c": {
        "mode": "text", "entries": {"e": {
            "mode": "text", "meta": {},
            "versions": {"v1": {
                "versionid": "v1", "mode": "text", "entry": {"content": "value"},
            }},
        }},
    }}}
    checker = request(generate(model), "/", method)
    before = copy.deepcopy(value)
    checker.validate(value)
    for path in (
        ("catalogs", "c"),
        ("catalogs", "c", "entries", "e"),
        ("catalogs", "c", "entries", "e", "versions", "v1"),
    ):
        invalid = copy.deepcopy(value)
        entity = invalid
        for name in path:
            entity = entity[name]
        entity["unmodeled"] = True
        with pytest.raises(jsonschema.ValidationError):
            checker.validate(invalid)
    assert value == before


def test_openapi_generation_preserves_the_caller_model():
    model = copy.deepcopy(MODEL)
    before = copy.deepcopy(model)
    GENERATOR.generate_openapi(model)
    assert model == before


META_PATH = "/catalogs/{groupid}/entries/{resourceid}/meta"


def meta_response(identity="entryid"):
    return {
        identity: "alias",
        "self": "https://example.com/catalogs/c/entries/alias/meta",
        "xid": "/catalogs/c/entries/alias/meta",
        "epoch": 2, "createdat": STAMP, "modifiedat": STAMP,
        "readonly": False, "compatibility": "none", "deprecated": {},
        "defaultversionid": "v1",
        "defaultversionurl": "https://example.com/catalogs/c/entries/alias/versions/v1",
        "defaultversionsticky": False,
        "owner": "team", "policy": "local", "managed": "server",
    }


@pytest.mark.parametrize("value", [
    {}, {"defaultversionsticky": True}, {"defaultversionid": "v1"},
    {"defaultversionsticky": None}, {"createdat": None},
])
def test_meta_patch_accepts_legal_partial_input_without_response_fields(value):
    schema = generate()
    validate(schema)
    request(schema, META_PATH, "patch").validate(value)
    with pytest.raises(jsonschema.ValidationError):
        request(schema, META_PATH, "patch").validate({"defaultversionsticky": "true"})


@pytest.mark.parametrize("method", ["get", "put", "patch"])
def test_meta_completed_responses_keep_core_and_model_requirements(method):
    schema = generate()
    checker = response(schema, META_PATH, method)
    complete = meta_response()
    checker.validate(complete)
    for name in (
        "entryid", "self", "xid", "epoch", "createdat", "modifiedat",
        "readonly", "defaultversionid", "defaultversionurl",
        "defaultversionsticky", "owner", "policy", "managed",
    ):
        invalid = {key: value for key, value in complete.items() if key != name}
        with pytest.raises(jsonschema.ValidationError):
            checker.validate(invalid)


@pytest.mark.parametrize("method, role", [
    ("get", "response"), ("put", "response"), ("patch", "response"),
    ("put", "request"), ("patch", "request"), ("get", "nested"),
])
def test_meta_deprecation_rejects_unmodeled_members_in_every_role(method, role):
    schema = generate()
    if role == "request":
        checker = request(schema, META_PATH, method)
        value = {"owner": "team"} if method == "put" else {}
    else:
        checker = response(schema, META_PATH, method) if role == "response" else validator(
            schema, schema["components"]["schemas"]["entry"]["properties"]["meta"],
            read=True,
        )
        value = meta_response()
    for deprecated in ({}, {
        "effective": STAMP, "removal": "2027-01-01T00:00:00Z",
        "alternative": "../replacement", "documentation": "https://example.com/docs",
    }):
        value["deprecated"] = deprecated
        before = copy.deepcopy(value)
        checker.validate(value)
        invalid = copy.deepcopy(value)
        invalid["deprecated"]["unmodeled"] = True
        with pytest.raises(jsonschema.ValidationError):
            checker.validate(invalid)
        assert value == before


def test_meta_put_retains_client_required_fields_and_server_default_obligations():
    schema = generate()
    checker = request(schema, META_PATH, "put")
    checker.validate({"owner": "team"})
    checker.validate({"owner": "team", "policy": None, "createdat": None})
    checker.validate({"owner": "team", "managed": 7, "self": 7, "xid": False,
                      "defaultversionurl": 7})
    for invalid in ({}, {"owner": None}, {"owner": "team", "createdat": 7}):
        with pytest.raises(jsonschema.ValidationError):
            checker.validate(invalid)


def test_alias_meta_uses_the_same_model_specific_definition_nested_and_standalone():
    schema = generate()
    nested = schema["components"]["schemas"]["entry"]["properties"]["meta"]
    read = schema["paths"][META_PATH]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    assert nested["allOf"][0] == read
    full_alias = {**meta_response(), "xref": "/catalogs/c/entries/canonical"}
    validator(schema, nested, read=True).validate(full_alias)
    response(schema, META_PATH).validate(full_alias)
    root = registry_response()
    root["catalogs"] = {"c": {
        "catalogid": "c", "kind": "custom", "entries": {"alias": {
            "entryid": "alias", "versionsurl": "https://example.com/versions",
            "meta": full_alias,
        }},
    }}
    response(schema, "/").validate(root)
    identity_alias = {key: full_alias[key] for key in ("entryid", "self", "xid", "xref")}
    validator(schema, nested, read=True).validate(identity_alias)
    response(schema, META_PATH).validate(identity_alias)
    identity_alias["self"] = "#/catalogs/c/entries/alias/meta"
    response(schema, META_PATH).validate(identity_alias)
    alias_input = {key: full_alias[key] for key in ("entryid", "xref")}
    for method in ("put", "patch"):
        request(schema, META_PATH, method).validate(alias_input)
        with pytest.raises(jsonschema.ValidationError):
            request(schema, META_PATH, method).validate({
                **alias_input, "defaultversionsticky": True,
            })
    assert "RESOURCEid" not in str(schema["components"]["schemas"])


@pytest.mark.parametrize("xref", [
    "https://example.com/catalogs/c/entries/e",
    "//example.com/catalogs/c/entries/e",
    "#/catalogs/c/entries/e",
    "catalogs/c/entries/e",
    "/catalogs/c/entries/e/versions/v1",
])
def test_meta_xref_rejects_non_resource_xid_syntax_in_every_role(xref):
    schema = generate()
    for method in ("put", "patch"):
        with pytest.raises(jsonschema.ValidationError):
            request(schema, META_PATH, method).validate({"xref": xref})
    with pytest.raises(jsonschema.ValidationError):
        response(schema, META_PATH).validate({**meta_response(), "xref": xref})


def test_xref_shape_validation_does_not_claim_graph_or_same_type_resolution():
    schema = generate()
    request(schema, META_PATH, "patch").validate({
        "xref": "/unknown/g/otherresources/id",
    })
    descriptor = schema["components"]["schemas"]["entryMeta"]["properties"]["xref"]
    assert descriptor["format"] == "uri-reference"


@pytest.mark.parametrize("group, plural, singular", [
    ("catalogs", "entries", "entry"), ("mirrors", "entries", "entry"),
    ("catalogs", "files", "file"), ("mirrors", "files", "file"),
])
def test_declared_and_imported_meta_routes_keep_their_resource_id_types(
    group, plural, singular
):
    model = copy.deepcopy(MODEL)
    model["groups"]["catalogs"]["resources"]["files"] = {
        "singular": "file", "hasdocument": False, "maxversions": 0,
        "metaattributes": {
            "owner": {"type": "string", "required": True},
            "policy": {"type": "string", "required": True, "default": "local"},
            "managed": {"type": "string", "required": True, "readonly": True},
        },
    }
    model["groups"]["mirrors"] = {
        "singular": "mirror",
        "ximportresources": ["/catalogs/entries", "/catalogs/files"],
    }
    schema = generate(model)
    path = f"/{group}/{{groupid}}/{plural}/{{resourceid}}/meta"
    identity = singular + "id"
    complete = meta_response(identity)
    response(schema, path).validate(complete)
    for method in ("put", "patch"):
        request(schema, path, method).validate({identity: "alias", "owner": "team"})
        with pytest.raises(jsonschema.ValidationError):
            request(schema, path, method).validate({identity: 7, "owner": "team"})
    with pytest.raises(jsonschema.ValidationError):
        response(schema, path).validate({**complete, identity: 7})
    properties = schema["components"]["schemas"][singular + "Meta"]["properties"]
    assert identity in properties and "RESOURCEid" not in properties
    assert ("fileid" if singular == "entry" else "entryid") not in properties


def test_root_nested_creation_and_meta_patch_use_the_correct_input_roles():
    schema = generate()
    create = {
        "tenant": "t", "catalogs": {"c": {
            "kind": "custom", "entries": {"e": {
                "payload": "data", "meta": {"owner": "team"},
            }},
        }},
    }
    request(schema, "/", "put").validate(create)
    invalid = copy.deepcopy(create)
    invalid["catalogs"]["c"]["entries"]["e"]["meta"] = {}
    with pytest.raises(jsonschema.ValidationError):
        request(schema, "/", "put").validate(invalid)
    invalid = copy.deepcopy(create)
    del invalid["catalogs"]["c"]["entries"]["e"]["payload"]
    with pytest.raises(jsonschema.ValidationError):
        request(schema, "/", "put").validate(invalid)
    explicit_versions = copy.deepcopy(create)
    entry = explicit_versions["catalogs"]["c"]["entries"]["e"]
    del entry["payload"]
    entry["versions"] = {"v1": {"payload": "data"}}
    request(schema, "/", "put").validate(explicit_versions)
    request(schema, "/", "patch").validate({
        "catalogs": {"c": {"entries": {"e": {"meta": {"defaultversionsticky": True}}}}},
    })
    alias = copy.deepcopy(create)
    alias["catalogs"]["c"]["entries"]["e"] = {
        "meta": {"xref": "/catalogs/c/entries/canonical"},
    }
    request(schema, "/", "put").validate(alias)
    alias["catalogs"]["c"]["entries"]["e"]["payload"] = "forbidden on alias"
    with pytest.raises(jsonschema.ValidationError):
        request(schema, "/", "put").validate(alias)


def test_retained_conditional_state_is_not_invented_by_request_inference():
    model = copy.deepcopy(MODEL)
    model["attributes"]["mode"] = {"type": "string", "ifvalues": {
        "limited": {"siblingattributes": {
            "limit": {"type": "integer", "required": True},
        }},
    }}
    schema = generate(model)
    request(schema, "/", "patch").validate({"limit": 7})
    request(schema, "/", "patch").validate({"limit": None})
    request(schema, "/", "patch").validate({"mode": "limited"})
    with pytest.raises(jsonschema.ValidationError):
        request(schema, "/", "patch").validate({"limit": "wrong"})
    descriptor = schema["components"]["schemas"]["RegistryPatchInput"]
    assert "limit" not in descriptor.get("required", [])


def test_core_model_overlays_do_not_turn_server_obligations_into_client_requirements():
    model = copy.deepcopy(MODEL)
    model["attributes"].update({
        "registryid": {"type": "string", "required": True, "readonly": True},
        "epoch": {"type": "uinteger", "required": True, "readonly": True},
        "createdat": {"type": "timestamp", "required": True},
        "modifiedat": {"type": "timestamp", "required": True},
    })
    metadata = model["groups"]["catalogs"]["resources"]["entries"]["metaattributes"]
    metadata.update({
        "entryid": {"type": "string", "required": True, "readonly": True},
        "epoch": {"type": "uinteger", "required": True, "readonly": True},
        "createdat": {"type": "timestamp", "required": True},
        "modifiedat": {"type": "timestamp", "required": True},
        "defaultversionid": {"type": "string", "required": True},
        "defaultversionsticky": {"type": "boolean", "required": True},
        "xref": {"type": "xid"},
    })
    schema = generate(model)
    request(schema, "/", "put").validate({"tenant": "t", "createdat": None})
    request(schema, "/", "patch").validate({})
    request(schema, META_PATH, "put").validate({"owner": "team"})
    request(schema, META_PATH, "patch").validate({
        "xref": "/catalogs/c/entries/canonical",
    })
    for path, body, identity in (
        ("/", {"tenant": "t"}, "registryid"),
        (META_PATH, {"owner": "team"}, "entryid"),
    ):
        with pytest.raises(jsonschema.ValidationError):
            request(schema, path, "put").validate({**body, identity: 7})
        with pytest.raises(jsonschema.ValidationError):
            request(schema, path, "put").validate({**body, "epoch": "wrong"})


def test_actual_cli_preserves_root_required_and_default_input_constraints(tmp_path):
    source = tmp_path / "model.json"
    output = tmp_path / "openapi.json"
    source.write_text(json.dumps(MODEL), encoding="utf-8")
    original = source.read_bytes()
    result = subprocess.run(
        [sys.executable, "-B", str(ROOT / "tools" / "schema-generator.py"),
         "--type", "openapi", "--output", str(output), str(source)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert source.read_bytes() == original
    schema = json.loads(output.read_text(encoding="utf-8"))
    request(schema, "/", "put").validate({"tenant": "t"})
    with pytest.raises(jsonschema.ValidationError):
        request(schema, "/", "put").validate({})
    request(schema, "/", "patch").validate({})
    response(schema, "/").validate(registry_response())


@pytest.mark.parametrize("method", ["put", "patch"])
def test_modelsource_changes_do_not_validate_against_a_stale_generated_model(method):
    schema = generate()
    request(schema, "/", method).validate({
        "modelsource": {"attributes": {"tenant": {"type": "integer", "required": True}}},
        "tenant": 7,
    })
    request(schema, "/", method).validate({"modelsource": None})
    with pytest.raises(jsonschema.ValidationError):
        request(schema, "/", method).validate({"modelsource": False})
    with pytest.raises(jsonschema.ValidationError):
        request(schema, "/", method).validate({"tenant": 7})


def test_completed_nested_model_objects_keep_default_and_readonly_requirements():
    schema = generate()
    value = registry_response()
    value["settings"] = {
        "endpoint": "https://example.com", "timeout": 10, "servervalue": "ready",
    }
    response(schema, "/").validate(value)
    for name in ("endpoint", "timeout", "servervalue"):
        invalid = copy.deepcopy(value)
        del invalid["settings"][name]
        with pytest.raises(jsonschema.ValidationError):
            response(schema, "/").validate(invalid)


def test_patch_collection_null_entries_are_errors_but_attribute_resets_remain_valid():
    schema = generate()
    checker = request(schema, "/", "patch")
    for name in ("catalogPatchInput", "entryPatchInput", "entryVersionPatchInput"):
        assert schema["components"]["schemas"][name].get("nullable") is not True
    for value in (
        {"catalogs": {"c": None}},
        {"catalogs": {"c": {"entries": {"e": None}}}},
        {"catalogs": {"c": {"entries": {"e": {"versions": {"v1": None}}}}}},
    ):
        before = copy.deepcopy(value)
        with pytest.raises(jsonschema.ValidationError):
            checker.validate(value)
        assert value == before
    for value in (
        {"catalogs": {"c": {}}},
        {"catalogs": {"c": {"entries": {"e": {}}}}},
        {"catalogs": {"c": {"entries": {"e": {"versions": {"v1": {}}}}}}},
        {"catalogs": {"c": {"name": None, "createdat": None}}},
    ):
        before = copy.deepcopy(value)
        checker.validate(value)
        assert value == before
    request(schema, META_PATH, "patch").validate({"xref": None})
    request(schema, META_PATH, "put").validate({"owner": "team", "xref": None})
    with pytest.raises(jsonschema.ValidationError):
        request(schema, META_PATH, "patch").validate({"owner": None})


def test_alias_response_does_not_weaken_incomplete_expanded_response_validation():
    schema = generate()
    alias = {**meta_response(), "xref": "/catalogs/c/entries/canonical"}
    response(schema, META_PATH).validate(alias)
    del alias["epoch"]
    with pytest.raises(jsonschema.ValidationError):
        response(schema, META_PATH).validate(alias)
    minimal = {key: alias[key] for key in ("entryid", "self", "xid", "xref")}
    response(schema, META_PATH).validate(minimal)
    del minimal["xref"]
    with pytest.raises(jsonschema.ValidationError):
        response(schema, META_PATH).validate(minimal)


@pytest.mark.parametrize("attributes", [
    {"createdat": {"type": "timestamp", "required": True}},
    {"registryid": {"type": "string", "required": True}},
    {"note": {"type": "string"}},
    {
        "tenant": {"type": "string", "required": True},
        "createdat": {"type": "timestamp", "required": True},
        "managed": {"type": "string", "required": True, "readonly": True},
    },
], ids=["server-only", "identity-only", "optional-only", "client-and-server"])
def test_filtered_input_requirements_produce_valid_openapi_documents(attributes):
    model = {"attributes": attributes, "groups": {}}
    before = copy.deepcopy(model)
    schema = generate(model)
    assert not list(OpenAPIV30SpecValidator(schema).iter_errors())
    checker = request(schema, "/", "put")
    value = {"tenant": "t"} if "tenant" in attributes else {}
    checker.validate(value)
    with pytest.raises(jsonschema.ValidationError):
        checker.validate({**value, "createdat": 7})
    with pytest.raises(jsonschema.ValidationError):
        checker.validate({**value, "registryid": 7})
    if "tenant" in attributes:
        with pytest.raises(jsonschema.ValidationError):
            checker.validate({})
    assert model == before


def envelope_model(maxversions=1, hasdocument=False):
    return {"groups": {"catalogs": {
        "singular": "catalog",
        "resources": {"entries": {
            "singular": "entry", "hasdocument": hasdocument, "maxversions": maxversions,
        }},
    }, "mirrors": {
        "singular": "mirror", "ximportresources": ["/catalogs/entries"],
    }}}


def core_registry():
    return {key: value for key, value in registry_response().items()
            if key not in ("tenant", "region", "serverstamp")}


def core_meta():
    return {key: value for key, value in meta_response().items()
            if key not in ("owner", "policy", "managed")}


def test_version_identity_filter_drops_empty_required_without_losing_client_fields():
    for attributes in (
        {"versionid": {"type": "string", "required": True}},
        {
            "versionid": {"type": "string", "required": True},
            "payload": {"type": "string", "required": True},
        },
    ):
        model = envelope_model()
        model["groups"]["catalogs"]["resources"]["entries"]["attributes"] = attributes
        before = copy.deepcopy(model)
        schema = generate(model)
        assert not list(OpenAPIV30SpecValidator(schema).iter_errors())
        version = {"payload": "data"} if "payload" in attributes else {}
        value = {"catalogs": {"c": {"entries": {"e": {"versions": {"v1": version}}}}}}
        request(schema, "/", "put").validate(value)
        if "payload" in attributes:
            invalid = copy.deepcopy(value)
            invalid["catalogs"]["c"]["entries"]["e"]["versions"]["v1"] = {}
            with pytest.raises(jsonschema.ValidationError):
                request(schema, "/", "put").validate(invalid)
        assert model == before


@pytest.mark.parametrize("method", ["put", "patch"])
@pytest.mark.parametrize("extension", [
    {"schemagroupsurl": "https://example.com/schemagroups", "schemagroupscount": 0},
    {"icon": "https://example.com/icon.png"},
], ids=["navigation", "icon"])
def test_published_registry_get_to_write_roundtrip_keeps_core_navigation(method, extension):
    schema = json.loads((ROOT / "schema" / "schemas" / "openapi.json").read_text(
        encoding="utf-8"
    ))
    value = {
        **core_registry(), "specversion": "1.0-rc4", **extension,
    }
    before = copy.deepcopy(value)
    response(schema, "/").validate(value)
    request(schema, "/", method).validate(value)
    assert value == before


def test_closed_version_contenttype_is_core_input_not_an_extension():
    model = {"groups": {"catalogs": {"singular": "catalog", "resources": {
        "entries": {"singular": "entry", "hasdocument": True, "maxversions": 0},
    }}}}
    schema = generate(model)
    value = {**core_registry(), "specversion": "1.0-rc4", "catalogs": {"c": {
        "entries": {"e": {"versions": {"v1": {
            "entry": {"example": 1}, "contenttype": "application/json",
        }}}},
    }}}
    before = copy.deepcopy(value)
    checker = request(schema, "/", "patch")
    checker.validate(value)
    for field, invalid_value in (("contenttype", 7), ("unmodeled", True), ("metaurl", "ignored")):
        invalid = copy.deepcopy(value)
        invalid["catalogs"]["c"]["entries"]["e"]["versions"]["v1"][field] = invalid_value
        with pytest.raises(jsonschema.ValidationError):
            checker.validate(invalid)
    assert value == before


def test_published_patch_rejects_null_group_entries_without_rejecting_objects():
    schema = json.loads((ROOT / "schema" / "schemas" / "openapi.json").read_text(
        encoding="utf-8"
    ))
    checker = request(schema, "/", "patch")
    value = {**core_registry(), "specversion": "1.0-rc4", "schemagroups": {"g": None}}
    before = copy.deepcopy(value)
    with pytest.raises(jsonschema.ValidationError):
        checker.validate(value)
    checker.validate({**value, "schemagroups": {"g": {}}})
    assert value == before


@pytest.mark.parametrize("method", ["put", "patch"])
@pytest.mark.parametrize("maxversions", [0, 1])
@pytest.mark.parametrize("hasdocument", [False, True])
def test_core_request_inventory_keeps_nested_fields_and_rejects_unknowns(
    method, maxversions, hasdocument
):
    model = envelope_model(maxversions, hasdocument)
    before_model = copy.deepcopy(model)
    schema = generate(model)
    common = {
        "name": "entry", "description": "description",
        "documentation": "https://example.com/docs", "icon": "https://example.com/icon",
        "labels": {"owner": "team"}, "createdat": STAMP, "modifiedat": STAMP,
        "epoch": 1, "self": "https://example.com/entity", "shortself": "https://example.com/e",
        "xid": "/catalogs/c/entries/e",
    }
    version = {
        **common, "entryid": "e", "versionid": "v1", "ancestorid": "v1",
        "contenttype": "application/json", "format": "example/1", "isdefault": True,
        "formatvalidated": False, "formatvalidatedreason": "not supported",
        "compatibilityvalidated": False, "compatibilityvalidatedreason": "not supported",
    }
    if hasdocument:
        version["entry"] = {"domain": {"unmodeled": [True, 7]}}
    entry = {
        **version, "metaurl": "https://example.com/meta", "meta": core_meta(),
        "versionsurl": "https://example.com/versions", "versionscount": 1,
        "versions": {"v1": copy.deepcopy(version)},
    }
    group = {
        **common, "catalogid": "c", "deprecated": {}, "constraints": {},
        "entriesurl": "https://example.com/entries", "entriescount": 1,
        "entries": {"e": entry},
    }
    value = {
        **core_registry(), "icon": common["icon"],
        "catalogsurl": "https://example.com/catalogs", "catalogscount": 1,
        "mirrorsurl": "https://example.com/mirrors", "mirrorscount": 1,
        "catalogs": {"c": group},
        "mirrors": {"m": {
            "mirrorid": "m", "entriesurl": "https://example.com/mirrors/m/entries",
            "entriescount": 1, "entries": {"e": copy.deepcopy(entry)},
        }},
    }
    before = copy.deepcopy(value)
    checker = request(schema, "/", method)
    checker.validate(value)
    paths = (
        (), ("catalogs", "c"), ("catalogs", "c", "entries", "e"),
        ("catalogs", "c", "entries", "e", "versions", "v1"),
        ("mirrors", "m", "entries", "e"),
    )
    for path in paths:
        for name, bad in (("unmodeled", True), ("icon", 7), ("name", False)):
            invalid = copy.deepcopy(value)
            owner = invalid
            for part in path:
                owner = owner[part]
            owner[name] = bad
            with pytest.raises(jsonschema.ValidationError):
                checker.validate(invalid)
    for name in ("contenttype", "format", "ancestorid"):
        invalid = copy.deepcopy(value)
        invalid["catalogs"]["c"]["entries"]["e"]["versions"]["v1"][name] = 7
        with pytest.raises(jsonschema.ValidationError):
            checker.validate(invalid)
    for name in ("deprecated", "constraints"):
        invalid = copy.deepcopy(value)
        invalid["catalogs"]["c"][name] = 7
        with pytest.raises(jsonschema.ValidationError):
            checker.validate(invalid)
    assert value == before
    assert model == before_model


@pytest.mark.parametrize("method", ["put", "patch"])
@pytest.mark.parametrize("ignored", [None, True, 7, "not a URL", [], {"anything": False}])
def test_core_readonly_navigation_is_ignored_regardless_of_supplied_kind(method, ignored):
    schema = generate(envelope_model())
    value = {
        "catalogsurl": ignored, "catalogscount": ignored,
        "mirrorsurl": ignored, "mirrorscount": ignored,
        "catalogs": {"c": {
            "entriesurl": ignored, "entriescount": ignored,
            "entries": {"e": {
                "metaurl": ignored, "versionsurl": ignored, "versionscount": ignored,
                "isdefault": ignored, "formatvalidated": ignored,
                "formatvalidatedreason": ignored, "compatibilityvalidated": ignored,
                "compatibilityvalidatedreason": ignored,
                "versions": {"v1": {
                    "isdefault": ignored, "formatvalidated": ignored,
                    "formatvalidatedreason": ignored, "compatibilityvalidated": ignored,
                    "compatibilityvalidatedreason": ignored,
                }},
            }},
        }},
    }
    before = copy.deepcopy(value)
    request(schema, "/", method).validate(value)
    invalid = copy.deepcopy(value)
    invalid["catalogs"]["c"]["entries"]["e"]["versions"]["v1"]["contenttype"] = False
    with pytest.raises(jsonschema.ValidationError):
        request(schema, "/", method).validate(invalid)
    assert value == before


@pytest.mark.parametrize("group", ["catalogs", "mirrors"])
@pytest.mark.parametrize("maxversions", [0, 1])
def test_existing_metadata_write_routes_use_inputs_not_defaulted_responses(group, maxversions):
    model = envelope_model(maxversions)
    defaulted = {"region": {"type": "string", "required": True, "default": "global"}}
    for definition in model["groups"].values():
        definition["attributes"] = copy.deepcopy(defaulted)
    model["groups"]["catalogs"]["resources"]["entries"]["attributes"] = copy.deepcopy(defaulted)
    schema = generate(model)
    assert not list(OpenAPIV30SpecValidator(schema).iter_errors())
    group_path = f"/{group}/{{groupid}}"
    resource_path = group_path + "/entries/{resourceid}"
    routes = [
        (group_path, "put", {}),
        (resource_path, "put", {}),
        (resource_path, "post", {}),
        (resource_path + "/versions", "post", {"v1": {}}),
    ]
    for path, method, value in routes:
        before = copy.deepcopy(value)
        checker = request(schema, path, method)
        checker.validate(value)
        bad = {"v1": {"region": 7}} if path.endswith("/versions") else {"region": 7}
        with pytest.raises(jsonschema.ValidationError):
            checker.validate(bad)
        assert value == before
    response(schema, group_path).validate({"region": "global"})
    with pytest.raises(jsonschema.ValidationError):
        response(schema, group_path).validate({})
    assert f"/{group}" not in schema["paths"]
    assert "patch" not in schema["paths"][group_path]


def test_document_bearing_raw_requests_are_not_rewired_as_metadata_inputs():
    schema = generate(envelope_model(hasdocument=True))
    for group in ("catalogs", "mirrors"):
        path = f"/{group}/{{groupid}}/entries/{{resourceid}}"
        for method in ("put", "post"):
            content = schema["paths"][path][method]["requestBody"]["content"]
            assert content["application/json"]["schema"] == {
                "$ref": "#/components/schemas/entry",
            }
            assert content["application/octet-stream"]["schema"] == {
                "type": "string", "format": "binary",
            }


@pytest.mark.parametrize("group", ["catalogs", "mirrors"])
@pytest.mark.parametrize("maxversions", [0, 1])
@pytest.mark.parametrize("hasdocument", [False, True])
def test_identity_only_resource_aliases_do_not_require_target_defaults(
    group, maxversions, hasdocument
):
    model = envelope_model(maxversions, hasdocument)
    if group == "catalogs":
        del model["groups"]["mirrors"]
    model["groups"]["catalogs"]["resources"]["entries"]["attributes"] = {
        "region": {"type": "string", "required": True, "default": "global"},
    }
    schema = generate(model)
    assert not list(OpenAPIV30SpecValidator(schema).iter_errors())
    alias = {
        "entryid": "alias", "self": "https://example.com/catalogs/c/entries/alias",
        "xid": "/catalogs/c/entries/alias",
        "metaurl": "https://example.com/catalogs/c/entries/alias/meta",
        "meta": {
            "entryid": "alias", "self": "https://example.com/catalogs/c/entries/alias/meta",
            "xid": "/catalogs/c/entries/alias/meta", "xref": "/catalogs/c/entries/missing",
        },
    }
    before = copy.deepcopy(alias)
    resource_path = f"/{group}/{{groupid}}/entries/{{resourceid}}"
    paths = ([resource_path] if not hasdocument else []) + [resource_path + "$details"]
    for path in paths:
        checker = response(schema, path)
        checker.validate(alias)
        for mutation in (
            {"meta": {key: value for key, value in alias["meta"].items() if key != "xref"}},
            {"meta": {**alias["meta"], "xref": "https://example.com/not-an-xid"}},
            {"epoch": 1}, {"region": 7}, {"entryid": 7},
        ):
            with pytest.raises(jsonschema.ValidationError):
                checker.validate({**alias, **mutation})
        normal = {
            **alias, "region": "global", "meta": core_meta(),
            "versionsurl": "https://example.com/versions",
        }
        if hasdocument and maxversions == 1:
            normal["entry"] = {"example": 1}
        checker.validate(normal)
        if maxversions == 1:
            invalid = copy.deepcopy(normal)
            del invalid["region"]
            with pytest.raises(jsonschema.ValidationError):
                checker.validate(invalid)
    root = {**core_registry(), group: {"c": {"entries": {"alias": alias}}}}
    response(schema, "/").validate(root)
    assert alias == before
