"""Actual-route request/response role regressions for the OpenAPI generator."""

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest
from openapi_schema_validator import OAS30ReadValidator, OAS30Validator
from openapi_spec_validator import validate


ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "schema_generator", ROOT / "tools" / "schema-generator.py"
)
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)
STAMP = "2026-01-01T00:00:00Z"
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
    return GENERATOR.generate_openapi(copy.deepcopy(MODEL if model is None else model))


def validator(openapi, schema, read=False):
    implementation = OAS30ReadValidator if read else OAS30Validator
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
    assert nested == read
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


def test_patch_collection_deletion_and_xref_reset_are_distinct_from_missing_values():
    schema = generate()
    request(schema, "/", "patch").validate({"catalogs": {"c": None}})
    request(schema, "/", "patch").validate({
        "catalogs": {"c": {"entries": {"e": None}}},
    })
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
