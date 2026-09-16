"""Actual JSON Schema/OpenAPI conditional validation for issue 644."""

import copy
import importlib.util
import itertools
import json
from pathlib import Path

import jsonschema
import pytest
from openapi_schema_validator import OAS30ReadValidator, OAS30Validator, OAS30WriteValidator
from openapi_spec_validator import OpenAPIV30SpecValidator, validate_spec


@pytest.fixture(scope="module")
def generator():
    path = Path(__file__).with_name("schema-generator.py")
    spec = importlib.util.spec_from_file_location("schema_generator_ifvalues_644", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(params=["json-schema", "openapi"])
def dialect(request):
    return request.param


def model_with(attributes):
    return {"groups": {"tests": {"singular": "test", "attributes": attributes}}}


def validator_for(generator, model, dialect, group="test"):
    schema = generator.generate_json_schema(copy.deepcopy(model), dialect == "openapi")
    if dialect == "openapi":
        target = {
            **schema,
            "$ref": f"#/components/schemas/{group}",
        }
        return OAS30Validator(target)
    jsonschema.Draft7Validator.check_schema(schema)
    target = {
        **schema,
        "$ref": f"#/definitions/{group}-schema/{group}",
    }
    return jsonschema.Draft7Validator(target)


def conditional(selector_type="string", key="HTTP", sibling="options"):
    return {
        "type": selector_type,
        "ifvalues": {key: {"siblingattributes": {
            sibling: {"type": "object", "attributes": {
                "limit": {"type": "uinteger", "required": True},
                "enabled": {"type": "boolean"},
            }},
        }}},
    }


@pytest.mark.parametrize("key", ["HTTP", "MQTT/5.0"])
def test_all_ascii_case_variants_activate_the_same_branch(generator, dialect, key):
    validator = validator_for(generator, model_with({"protocol": conditional(key=key)}), dialect)
    variants = itertools.product(*[
        sorted({character.upper(), character.lower()}) for character in key
    ])
    for letters in variants:
        spelling = "".join(letters)
        valid = {"protocol": spelling, "options": {"limit": 0, "enabled": True}}
        original = copy.deepcopy(valid)
        assert validator.is_valid(valid), spelling
        assert valid == original
        for invalid in ({"limit": -1}, {"limit": 0, "enabled": "true"}, {}):
            assert not validator.is_valid({"protocol": spelling, "options": invalid}), (
                spelling, invalid,
            )


@pytest.mark.parametrize("spelling", [
    "CUSTOM", "HTTP/1.1", "HTTPX", "XHTTP", " HTTP", "HTTP ", "HTTP\n",
])
def test_unknown_and_nonexact_selectors_keep_the_extension_fallback(generator, dialect, spelling):
    definition = model_with({
        "protocol": conditional(), "*": {"type": "any"},
    })
    validator = validator_for(generator, definition, dialect)
    instance = {"protocol": spelling, "options": {"limit": -1, "extension": True}}
    assert validator.is_valid(instance)
    assert instance["protocol"] == spelling
    del definition["groups"]["tests"]["attributes"]["*"]
    closed = validator_for(generator, definition, dialect)
    assert closed.is_valid({"protocol": spelling})
    assert not closed.is_valid(instance)


@pytest.mark.parametrize("spelling", [None, False, 1, [], {}])
def test_unknown_fallback_preserves_the_selector_type(generator, dialect, spelling):
    validator = validator_for(generator, model_with({"protocol": conditional()}), dialect)
    assert not validator.is_valid({"protocol": spelling})


@pytest.mark.parametrize("key", ["X.[?]+(Y)", "A B-C#D"])
def test_literal_pattern_characters_are_not_regular_expression_operators(generator, dialect, key):
    validator = validator_for(
        generator, model_with({
            "protocol": conditional(key=key), "*": {"type": "any"},
        }), dialect,
    )
    assert not validator.is_valid({"protocol": key.lower(), "options": {"limit": -1}})
    assert validator.is_valid({"protocol": "XanythingY", "options": {"limit": -1}})


@pytest.mark.parametrize(("key", "spelling"), [
    ("Caf\u00e9", "CAF\u00c9"),
    ("K", "\u212a"),
    ("\U0001e900", "\U0001e922"),
])
def test_unicode_single_character_case_variants(generator, dialect, key, spelling):
    validator = validator_for(generator, model_with({"protocol": conditional(key=key)}), dialect)
    assert validator.is_valid({"protocol": spelling, "options": {"limit": 1}})
    assert not validator.is_valid({"protocol": spelling, "options": {"limit": -1}})


@pytest.mark.parametrize(("selector_type", "key", "value", "unknown"), [
    ("boolean", "TRUE", True, False),
    ("integer", "-3", -3, -4),
    ("uinteger", str(2 ** 100), 2 ** 100, 2 ** 100 + 1),
])
def test_native_scalar_selectors_keep_their_types(generator, dialect, selector_type, key, value, unknown):
    validator = validator_for(
        generator, model_with({
            "selector": conditional(selector_type, key), "*": {"type": "any"},
        }), dialect,
    )
    assert validator.is_valid({"selector": value, "options": {"limit": 0}})
    assert not validator.is_valid({"selector": value, "options": {"limit": -1}})
    assert not validator.is_valid({"selector": str(value), "options": {"limit": 0}})
    assert validator.is_valid({"selector": unknown, "options": {"limit": -1}})


def test_empty_branches_do_not_activate_for_missing_selectors(generator, dialect):
    selector = {"type": "string", "ifvalues": {"EMPTY": {}}}
    validator = validator_for(generator, model_with({"protocol": selector}), dialect)
    assert validator.is_valid({})
    assert validator.is_valid({"protocol": "empty"})
    assert validator.is_valid({"protocol": "custom"})
    selector["required"] = True
    required = validator_for(generator, model_with({"protocol": selector}), dialect)
    assert not required.is_valid({})


def test_multiple_independent_selectors_all_remain_effective(generator, dialect):
    attributes = {
        f"selector{index}": conditional(key="KNOWN", sibling=f"options{index}")
        for index in range(3)
    }
    validator = validator_for(generator, model_with(attributes), dialect)
    valid = {
        **{f"selector{index}": "known" for index in range(3)},
        **{f"options{index}": {"limit": 0} for index in range(3)},
    }
    assert validator.is_valid(valid)
    for index in range(3):
        invalid = copy.deepcopy(valid)
        invalid[f"options{index}"]["limit"] = -1
        assert not validator.is_valid(invalid), index


def test_nested_ifvalues_apply_without_normalizing_other_values(generator, dialect):
    selector = conditional()
    selector["ifvalues"]["HTTP"]["siblingattributes"]["envelope"] = conditional(
        key="FORMAT", sibling="envelopeoptions",
    )
    validator = validator_for(generator, model_with({
        "protocol": selector, "extension": {"type": "string"},
    }), dialect)
    valid = {
        "protocol": "http", "envelope": "format",
        "options": {"limit": 0}, "envelopeoptions": {"limit": 0},
        "extension": "DoNotNormalize",
    }
    assert validator.is_valid(valid)
    assert valid["extension"] == "DoNotNormalize"
    invalid = copy.deepcopy(valid)
    invalid["envelopeoptions"]["limit"] = -1
    assert not validator.is_valid(invalid)


def test_case_duplicate_selector_keys_fail_explicitly(generator, dialect):
    selector = conditional()
    selector["ifvalues"]["http"] = {}
    with pytest.raises(ValueError, match="case"):
        validator_for(generator, model_with({"protocol": selector}), dialect)


def test_empty_ifvalues_preserves_normal_attribute_validation(generator, dialect):
    validator = validator_for(generator, model_with({
        "protocol": {"type": "string", "required": True, "ifvalues": {}},
    }), dialect)
    assert validator.is_valid({"protocol": "any"})
    assert not validator.is_valid({})
    assert not validator.is_valid({"protocol": False})


def test_openapi_conditionals_are_connected_without_case_sensitive_discriminators(generator):
    model = model_with({"protocol": conditional()})
    openapi = generator.generate_openapi(copy.deepcopy(model))
    validate_spec(openapi)
    schema = openapi["components"]["schemas"]["test"]
    assert "discriminator" not in schema
    assert schema["allOf"][0]["oneOf"]
    validator = OAS30Validator({
        "$ref": "#/components/schemas/test", "components": openapi["components"],
    })
    assert not validator.is_valid({"protocol": "http", "options": {"limit": -1}})
    assert validator.is_valid({"protocol": "http", "options": {"limit": 0}})


@pytest.mark.parametrize(("domain", "target", "namespace", "selector", "valid", "invalid"), [
    (
        "message", "message", "messagegroup", "HTTP",
        {"query": [{"name": "sample", "value": "text", "required": False}]},
        {"query": [{"name": "sample", "value": False, "required": False}]},
    ),
    (
        "endpoint", "endpoint", "endpoint", "MQTT/5.0",
        {"sessionexpiryinterval": 0, "deployed": True, "qos": 0, "retain": False},
        {"sessionexpiryinterval": -1, "deployed": True, "qos": 0, "retain": False},
    ),
    (
        "cloudevents", "message", "messagegroup", "HTTP",
        {"query": [{"name": "sample", "value": "text", "required": False}]},
        {"query": [{"name": "sample", "value": False, "required": False}]},
    ),
    (
        "cloudevents", "endpoint", "endpoint", "MQTT/5.0",
        {"sessionexpiryinterval": 0, "deployed": True, "qos": 0, "retain": False},
        {"sessionexpiryinterval": -1, "deployed": True, "qos": 0, "retain": False},
    ),
])
def test_published_case_variant_options(
    dialect, domain, target, namespace, selector, valid, invalid,
):
    filename = "openapi.json" if dialect == "openapi" else "document-schema.json"
    path = Path(__file__).parent.parent / domain / "schemas" / filename
    schema = json.loads(path.read_text(encoding="utf-8"))
    if dialect == "openapi":
        validate_spec(schema)
        validator = OAS30Validator({
            "$ref": f"#/components/schemas/{target}",
            "components": schema["components"],
        })
    else:
        jsonschema.Draft7Validator.check_schema(schema)
        validator = jsonschema.Draft7Validator({
            **schema, "$ref": f"#/definitions/{namespace}-schema/{target}",
        })
    base = {"usage": ["subscriber"]} if target == "endpoint" else {}
    for spelling in (selector, selector.lower(), selector.swapcase()):
        assert validator.is_valid({
            **base, "protocol": spelling, "protocoloptions": valid,
        }), spelling
        assert not validator.is_valid({
            **base, "protocol": spelling, "protocoloptions": invalid,
        }), spelling
    unknown = {**base, "protocol": "CUSTOM/99"}
    assert validator.is_valid(unknown)
    with_options = {**unknown, "protocoloptions": invalid}
    assert validator.is_valid(with_options) is (target == "endpoint")
    assert unknown["protocol"] == "CUSTOM/99"


def request_checkers(generator, attributes, method="patch", scope="group"):
    root = Path(__file__).resolve().parent.parent
    model = ({"attributes": attributes, "groups": {}} if scope == "root" else
             {"groups": {"catalogs": {"singular": "catalog", "attributes": attributes}}})
    jsonschema.Draft7Validator(json.loads(
        (root / "core" / "model.schema.json").read_text(encoding="utf-8")
    )).validate(model)
    original = copy.deepcopy(model)
    schema = generator.generate_openapi(model)
    assert model == original
    assert not list(OpenAPIV30SpecValidator(schema).iter_errors())
    operation = schema["paths"]["/"]
    request_schema = operation[method]["requestBody"]["content"]["application/json"]["schema"]
    response_schema = operation["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    return (
        OAS30WriteValidator({**request_schema, "components": schema["components"]}),
        OAS30ReadValidator({**response_schema, "components": schema["components"]}),
    )


def conditional_request(value, scope="group"):
    root = {
        "registryid": "r", "specversion": "1.0-rc4",
        "self": "https://example.com/", "xid": "/", "epoch": 1,
        "createdat": "2026-01-01T00:00:00Z", "modifiedat": "2026-01-01T00:00:00Z",
    }
    if scope == "root":
        root.update(value)
    else:
        root["catalogs"] = {"c": value}
    return root


@pytest.mark.parametrize("method", ["put", "patch"])
@pytest.mark.parametrize("scope", ["root", "group"])
def test_readonly_selectors_keep_writable_conditional_siblings(generator, method, scope):
    attributes = {"mode": {
        "type": "string", "readonly": True,
        "ifvalues": {"limited": {"siblingattributes": {"limit": {"type": "integer"}}}},
    }}
    checker, read = request_checkers(generator, attributes, method, scope)
    read.validate(conditional_request({"mode": "limited", "limit": 7}, scope))
    for value in (
        {"limit": 7}, {"mode": False, "limit": 7}, {"mode": {"ignored": True}, "limit": 7},
        {"mode": "other", "limit": 7}, {},
    ):
        payload = conditional_request(value, scope)
        before = copy.deepcopy(payload)
        checker.validate(payload)
        assert payload == before
    for value in ({"limit": "wrong"}, {"mode": False, "limit": "wrong"}, {"unmodeled": 7}):
        with pytest.raises(jsonschema.ValidationError):
            checker.validate(conditional_request(value, scope))
    with pytest.raises(jsonschema.ValidationError):
        read.validate(conditional_request({"mode": "other", "limit": 7}, scope))


@pytest.mark.parametrize("method", ["put", "patch"])
@pytest.mark.parametrize("wildcard", [None, "string", "any"])
def test_request_conditional_names_select_active_or_inactive_wildcard_contract(
    generator, method, wildcard
):
    attributes = {
        "mode": {"type": "string", "ifvalues": {
            "number": {"siblingattributes": {"value": {"type": "integer"}}},
        }},
    }
    if wildcard:
        attributes["*"] = {"type": wildcard}
    checker, read = request_checkers(generator, attributes, method)
    cases = [
        ({"mode": "NuMbEr", "value": 7}, True),
        ({"mode": "number", "value": "extension"}, False),
        ({"mode": "other"}, True),
        ({"mode": "other", "value": "extension"}, wildcard is not None),
        ({"mode": "other", "value": 7}, wildcard == "any"),
        ({"value": 7}, True),
        ({"value": "extension"}, wildcard is not None),
        ({"value": {"nested": True}}, wildcard == "any"),
        ({"mode": False}, False),
        ({"unmodeled": True}, wildcard == "any"),
        ({"unmodeled": "extension"}, wildcard is not None),
    ]
    for value, accepted in cases:
        payload = conditional_request(value)
        before = copy.deepcopy(payload)
        assert checker.is_valid(payload) is accepted, value
        assert payload == before
    if wildcard == "string":
        read.validate(conditional_request({"mode": "other", "value": "extension"}))


@pytest.mark.parametrize("selector", [
    {"type": "string", "required": True, "default": "number"},
    {"type": "string", "readonly": True},
])
def test_unknown_server_selectors_admit_conditional_and_wildcard_alternatives(
    generator, selector
):
    attributes = {"*": {"type": "string"}, "mode": {
        **selector, "ifvalues": {"number": {"siblingattributes": {
            "value": {"type": "integer", "required": True},
        }}},
    }}
    checker, _ = request_checkers(generator, attributes)
    for value in ({"value": 7}, {"value": "extension"}, {"value": None}, {}):
        payload = conditional_request(value)
        before = copy.deepcopy(payload)
        checker.validate(payload)
        assert payload == before
    with pytest.raises(jsonschema.ValidationError):
        checker.validate(conditional_request({"value": {"wrong": True}}))


def test_request_conditional_wildcards_remain_guarded_for_known_selectors(generator):
    attributes = {"fixed": {"type": "string"}, "mode": {
        "type": "string", "ifvalues": {
            "open": {"siblingattributes": {"*": {"type": "integer"}}},
            "closed": {"siblingattributes": {}},
        },
    }}
    checker, _ = request_checkers(generator, attributes)
    for value, accepted in (
        ({"mode": "open", "extra": 7}, True),
        ({"mode": "open", "extra": "wrong"}, False),
        ({"mode": "closed", "extra": 7}, False),
        ({"mode": "other", "extra": 7}, False),
        ({"extra": 7}, True),
        ({"extra": "wrong"}, False),
        ({"fixed": 7}, False),
    ):
        payload = conditional_request(value)
        before = copy.deepcopy(payload)
        assert checker.is_valid(payload) is accepted, value
        assert payload == before


def test_colliding_request_conditions_preserve_known_constraints_and_unknown_alternatives(generator):
    attributes = {
        "fixed": {"type": "string"},
        "mode": {"type": "string", "ifvalues": {
            "number": {"siblingattributes": {"value": {"type": "integer"}}},
            "text": {"siblingattributes": {"value": {"type": "string"}}},
        }},
        "other": {"type": "string", "ifvalues": {
            "number": {"siblingattributes": {"value": {"type": "integer"}}},
        }},
    }
    checker, _ = request_checkers(generator, attributes)
    for value, accepted in (
        ({"mode": "number", "other": "off", "value": 7}, True),
        ({"mode": "text", "other": "off", "value": "text"}, True),
        ({"mode": "number", "value": "wrong"}, False),
        ({"mode": "text", "value": 7}, False),
        ({"value": 7}, True),
        ({"value": "text"}, True),
        ({"value": False}, False),
        ({"mode": "off", "other": "off", "value": 7}, False),
        ({"mode": "number", "other": "number", "value": 7}, False),
        ({"fixed": 7}, False),
        ({"unmodeled": "text"}, False),
    ):
        payload = conditional_request(value)
        before = copy.deepcopy(payload)
        assert checker.is_valid(payload) is accepted, value
        assert payload == before


@pytest.mark.parametrize("readonly_second", [False, True])
def test_known_conditional_wildcards_are_not_widened_by_unknown_or_colliding_selectors(
    generator, readonly_second
):
    attributes = {
        "fixed": {"type": "string"},
        "text": {"type": "boolean", "ifvalues": {
            "true": {"siblingattributes": {"*": {"type": "string"}}},
        }},
        "number": {"type": "boolean", "ifvalues": {
            "true": {"siblingattributes": {"*": {"type": "integer"}}},
        }},
    }
    if readonly_second:
        attributes["number"]["readonly"] = True
    checker, _ = request_checkers(generator, attributes)
    for value, accepted in (
        ({"text": True, "extra": "text"}, True),
        ({"text": True, "extra": 7}, False),
        ({"text": False, "number": True, "extra": 7}, True),
        ({"text": True, "number": True, "extra": "text"}, readonly_second),
        ({"text": True, "number": True, "extra": 7}, False),
        ({"extra": "text"}, True),
        ({"extra": 7}, True),
        ({"extra": False}, False),
        ({"fixed": 7}, False),
    ):
        payload = conditional_request(value)
        before = copy.deepcopy(payload)
        assert checker.is_valid(payload) is accepted, value
        assert payload == before
