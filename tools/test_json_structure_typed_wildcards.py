"""Typed additional-property checks against a bounded JSON Structure subset."""

import copy
import importlib.util
from pathlib import Path

import jsonschema
import pytest
from jsonpointer import resolve_pointer


ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "schema_generator", ROOT / "tools" / "schema-generator.py"
)
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)


def model(wildcard):
    attributes = {
        "display-name": {"type": "string", "required": True},
    }
    if wildcard is not None:
        attributes["*"] = copy.deepcopy(wildcard)
    return {"groups": {"catalogs": {
        "singular": "catalog",
        "attributes": {"settings": {
            "type": "object", "namecharset": "extended", "attributes": attributes,
        }},
    }}}


def settings_schema(schema):
    return schema["definitions"]["Catalogs"]["Catalog"]["properties"]["settings"]


def contract_validator(schema):
    """Translate only these primary Core types; this is not a full SDK."""
    primitives = {
        "any": {}, "string": {"type": "string"}, "uri": {"type": "string"},
        "datetime": {"type": "string"}, "boolean": {"type": "boolean"},
        "integer": {"type": "integer", "minimum": -(2 ** 31), "maximum": 2 ** 31 - 1},
        "uint32": {"type": "integer", "minimum": 0, "maximum": 2 ** 32 - 1},
    }

    def convert(node):
        kind = node["type"]
        if isinstance(kind, dict):
            assert set(kind) == {"$ref"}
            resolve_pointer(schema, kind["$ref"][1:])
            result = {"$ref": kind["$ref"]}
        elif kind == "object":
            assert node["properties"], "The tested object types have named properties."
            names = {
                name: value.get("altnames", {}).get("json", name)
                for name, value in node["properties"].items()
            }
            additional = node.get("additionalProperties", False)
            result = {
                "type": "object",
                "properties": {
                    names[name]: convert(value)
                    for name, value in node["properties"].items()
                },
                "required": [names[name] for name in node.get("required", [])],
                "additionalProperties": (
                    convert(additional) if isinstance(additional, dict) else additional
                ),
            }
        elif kind == "map":
            result = {"type": "object", "additionalProperties": convert(node["values"])}
        elif kind == "array":
            result = {"type": "array", "items": convert(node["items"])}
        else:
            assert kind in primitives, f"Outside the tested subset: {kind}"
            result = copy.deepcopy(primitives[kind])
        if "enum" in node:
            result["enum"] = copy.deepcopy(node["enum"])
        return result

    translated = convert(schema)
    translated["definitions"] = {
        namespace: {name: convert(value) for name, value in entries.items()}
        for namespace, entries in schema["definitions"].items()
    }
    jsonschema.Draft7Validator.check_schema(translated)
    return jsonschema.Draft7Validator(translated)


@pytest.mark.parametrize("wildcard, valid, invalid", [
    ({"type": "integer"}, 7, "7"),
    ({"type": "string"}, "value", 7),
    ({"type": "boolean"}, True, "true"),
    ({"type": "uinteger"}, 0, -1),
    ({"type": "string", "enum": ["one", "two"]}, "one", "three"),
    ({"type": "object", "attributes": {
        "count": {"type": "integer", "required": True},
    }}, {"count": 7}, {"count": "7"}),
    ({"type": "array", "item": {
        "type": "object", "attributes": {"count": {"type": "integer", "required": True}},
    }}, [{"count": 7}], [{}]),
    ({"type": "map", "item": {
        "type": "object", "attributes": {"count": {"type": "integer", "required": True}},
    }}, {"item": {"count": 7}}, {"item": {"count": False}}),
])
def test_named_typed_wildcards_validate_values_without_retyping_named_members(
    wildcard, valid, invalid
):
    source = model(wildcard)
    source_before = copy.deepcopy(source)
    schema = GENERATOR.generate_json_structure(source)
    assert source == source_before
    settings = settings_schema(schema)
    assert settings["type"] == "object"
    assert settings["properties"]["displayName"] == {
        "type": "string", "altnames": {"json": "display-name"},
    }
    assert settings["required"] == ["displayName"]
    assert isinstance(settings["additionalProperties"], dict)
    checker = contract_validator(schema)
    value = {"catalogs": {"c": {"settings": {"display-name": "http", "extra": valid}}}}
    before = copy.deepcopy(value)
    checker.validate(value)
    assert value == before
    for replacement in (
        {"display-name": "http", "extra": invalid},
        {"display-name": 7, "extra": valid},
        {"extra": valid},
    ):
        with pytest.raises(jsonschema.ValidationError):
            checker.validate({"catalogs": {"c": {"settings": replacement}}})
    checker.validate({"catalogs": {"c": {"settings": {"display-name": "http"}}}})


@pytest.mark.parametrize("wildcard, extra, accepted", [
    (None, 7, False),
    ({"type": "any"}, None, True),
    ({"type": "any"}, {"nested": [None, True, 7]}, True),
])
def test_untyped_and_closed_named_objects_retain_their_existing_boundaries(
    wildcard, extra, accepted
):
    schema = GENERATOR.generate_json_structure(model(wildcard))
    assert settings_schema(schema)["additionalProperties"] is (wildcard is not None)
    checker = contract_validator(schema)
    value = {"catalogs": {"c": {"settings": {"display-name": "http", "extra": extra}}}}
    if accepted:
        checker.validate(value)
    else:
        with pytest.raises(jsonschema.ValidationError):
            checker.validate(value)
    with pytest.raises(jsonschema.ValidationError):
        checker.validate({"catalogs": {"c": {"settings": {"display-name": 7}}}})


def test_typed_object_wildcard_uses_a_resolved_closed_definition():
    schema = GENERATOR.generate_json_structure(model({
        "type": "object",
        "attributes": {"count": {"type": "integer", "required": True}},
    }))
    reference = settings_schema(schema)["additionalProperties"]["type"]
    assert isinstance(reference, dict) and set(reference) == {"$ref"}
    target = resolve_pointer(schema, reference["$ref"][1:])
    assert target == {
        "type": "object", "properties": {"count": {"type": "integer"}},
        "additionalProperties": False, "required": ["count"],
    }
    with pytest.raises(jsonschema.ValidationError):
        contract_validator(schema).validate({"catalogs": {"c": {"settings": {
            "display-name": "http", "extra": {"count": 7, "unmodeled": True},
        }}}})
