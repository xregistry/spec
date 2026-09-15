"""Bounded Core/Validation contract checks, not full JSON Structure SDK tests.

The primary revisions and supported subset are documented in
json-structure-dynamic-maps.md. No network or SDK installation is used here.
"""

import copy
import importlib.util
import json
import subprocess
import sys
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
VALIDATION = "JSONStructureValidation"
ANY_OBJECT = {"type": "object", "attributes": {"*": {"type": "any"}}}


def model(parameters):
    return {"groups": {"catalogs": {
        "singular": "catalog",
        "attributes": {"parameters": parameters},
    }}}


def document(parameters):
    return {"catalogs": {"c": {"parameters": parameters}}}


def parameter_schema(schema):
    return schema["definitions"]["Catalogs"]["Catalog"]["properties"]["parameters"]


def contract_validator(schema):
    """Translate only the tested primary-contract subset to a JSON validator."""
    primitive = {
        "string": {"type": "string"},
        "uri": {"type": "string"},
        "datetime": {"type": "string"},
        "boolean": {"type": "boolean"},
        "integer": {
            "type": "integer", "minimum": -(2 ** 31), "maximum": 2 ** 31 - 1,
        },
        "uint32": {"type": "integer", "minimum": 0, "maximum": 2 ** 32 - 1},
        "any": {},
    }

    def convert(node):
        kind = node["type"]
        if isinstance(kind, dict):
            assert set(kind) == {"$ref"}
            reference = kind["$ref"]
            assert reference.startswith("#/")
            resolve_pointer(schema, reference[1:])
            return {"$ref": reference}
        if kind == "object":
            assert node.get("properties"), "Core 3.4.4 requires named properties"
            assert "values" not in node and "maxEntries" not in node
            properties = {}
            for name, child in node["properties"].items():
                wire_name = child.get("altnames", {}).get("json", name)
                properties[wire_name] = convert(child)
            additional = node.get("additionalProperties", False)
            required = [
                node["properties"][name].get("altnames", {}).get("json", name)
                for name in node.get("required", [])
            ]
            return {
                "type": "object", "properties": properties, "required": required,
                "additionalProperties": (
                    convert(additional) if isinstance(additional, dict) else additional
                ),
            }
        if kind == "map":
            assert isinstance(node.get("values"), dict), "Core values schema is required"
            assert not {"properties", "additionalProperties", "maxProperties", "const"} & node.keys()
            result = {"type": "object", "additionalProperties": convert(node["values"])}
            if "maxEntries" in node:
                assert VALIDATION in schema["$uses"], "Validation feature must be enabled"
                assert type(node["maxEntries"]) is int and node["maxEntries"] >= 0
                result["maxProperties"] = node["maxEntries"]
            return result
        if kind == "array":
            assert isinstance(node.get("items"), dict)
            return {"type": "array", "items": convert(node["items"])}
        assert kind in primitive, f"Outside this contract-check subset: {kind}"
        return copy.deepcopy(primitive[kind])

    translated = convert(schema)
    translated["definitions"] = {
        namespace: {name: convert(value) for name, value in declarations.items()}
        for namespace, declarations in schema["definitions"].items()
    }
    jsonschema.Draft7Validator.check_schema(translated)
    return jsonschema.Draft7Validator(translated)


def test_wildcard_only_parameters_use_the_primary_map_of_any_shape():
    schema = GENERATOR.generate_json_structure(model(copy.deepcopy(ANY_OBJECT)))
    assert parameter_schema(schema) == {"type": "map", "values": {"type": "any"}}
    assert schema["$uses"] == ["JSONStructureAlternateNames"]
    contract_validator(schema)


@pytest.mark.parametrize("parameters", [{}, {"mode": "read"}, {
    "nested": {"object": [7, True, None, {"items": ["x"]}]},
}])
def test_dynamic_parameters_preserve_empty_and_nested_object_data(parameters):
    definition = model(copy.deepcopy(ANY_OBJECT))
    original = copy.deepcopy(definition)
    schema = GENERATOR.generate_json_structure(definition)
    assert definition == original
    validator = contract_validator(schema)
    value = document(copy.deepcopy(parameters))
    before = copy.deepcopy(value)
    validator.validate(value)
    assert value == before


@pytest.mark.parametrize("parameters", [None, [], 7, "text", True])
def test_dynamic_map_rejects_non_object_instances(parameters):
    schema = GENERATOR.generate_json_structure(model(copy.deepcopy(ANY_OBJECT)))
    with pytest.raises(jsonschema.ValidationError):
        contract_validator(schema).validate(document(parameters))


@pytest.mark.parametrize("required", [False, True])
def test_dynamic_parameters_preserve_required_and_optional_presence(required):
    definition = {**copy.deepcopy(ANY_OBJECT), "required": required}
    schema = GENERATOR.generate_json_structure(model(definition))
    validator = contract_validator(schema)
    validator.validate(document({}))
    absent = {"catalogs": {"c": {}}}
    if required:
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(absent)
    else:
        validator.validate(absent)
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(document(None))


@pytest.mark.parametrize("definition", [
    {"type": "object"}, {"type": "object", "attributes": {}},
])
@pytest.mark.parametrize("required", [False, True])
def test_closed_empty_objects_use_zero_entry_maps_not_open_maps(definition, required):
    definition = {**definition, "required": required}
    schema = GENERATOR.generate_json_structure(model(definition))
    assert parameter_schema(schema) == {
        "type": "map", "values": {"type": "any"}, "maxEntries": 0,
    }
    assert VALIDATION in schema["$uses"]
    validator = contract_validator(schema)
    validator.validate(document({}))
    absent = {"catalogs": {"c": {}}}
    if required:
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(absent)
    else:
        validator.validate(absent)
    for value in ({"extra": None}, {"extra": 7}, [], None, 7):
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(document(value))


def test_empty_registry_projection_uses_the_same_closed_empty_contract():
    schema = GENERATOR.generate_json_structure({})
    assert schema["type"] == "map"
    assert schema["maxEntries"] == 0
    validator = contract_validator(schema)
    validator.validate({})
    for value in ({"extra": True}, [], None):
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(value)


@pytest.mark.parametrize("open_object", [False, True])
def test_named_objects_remain_structured_with_their_declared_members(open_object):
    attributes = {"name": {"type": "string", "required": True}}
    if open_object:
        attributes["*"] = {"type": "any"}
    schema = GENERATOR.generate_json_structure(model({
        "type": "object", "attributes": attributes,
    }))
    parameters = parameter_schema(schema)
    assert parameters["type"] == "object"
    assert parameters["required"] == ["name"]
    assert parameters["additionalProperties"] is open_object
    validator = contract_validator(schema)
    validator.validate(document({"name": "http"}))
    extra = document({"name": "http", "extra": {"arbitrary": [7]}})
    if open_object:
        validator.validate(extra)
    else:
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(extra)
    for value in ({}, {"name": 7}, []):
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(document(value))


def test_named_optional_properties_still_allow_an_empty_instance():
    schema = GENERATOR.generate_json_structure(model({
        "type": "object", "attributes": {"name": {"type": "string"}},
    }))
    assert parameter_schema(schema)["type"] == "object"
    validator = contract_validator(schema)
    validator.validate(document({}))
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(document({"extra": True}))


def test_typed_dynamic_values_keep_their_reusable_schema_and_constraints():
    definition = {"type": "object", "attributes": {"*": {
        "type": "object", "attributes": {
            "name": {"type": "string", "required": True},
        },
    }}}
    schema = GENERATOR.generate_json_structure(model(definition))
    parameters = parameter_schema(schema)
    assert parameters["type"] == "map"
    assert "$ref" in parameters["values"]["type"]
    validator = contract_validator(schema)
    validator.validate(document({"first": {"name": "one"}, "second": {"name": "two"}}))
    for value in ({"first": {}}, {"first": {"name": 7}},
                  {"first": {"name": "one", "extra": True}}):
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(document(value))


def test_named_plus_typed_wildcard_is_not_rewritten_as_a_dynamic_map():
    schema = GENERATOR.generate_json_structure(model({
        "type": "object", "attributes": {
            "name": {"type": "string", "required": True},
            "*": {"type": "integer"},
        },
    }))
    parameters = parameter_schema(schema)
    assert parameters["type"] == "object"
    assert parameters["properties"] == {"name": {"type": "string"}}
    assert parameters["required"] == ["name"]
    validator = contract_validator(schema)
    validator.validate(document({"name": "http"}))
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(document({"name": 7}))


def test_full_model_references_preserve_recursive_dynamic_and_empty_values():
    definition = {"groups": {
        "catalogs": {"singular": "catalog", "resources": {"entries": {
            "singular": "entry", "maxversions": 0, "hasdocument": False,
            "attributes": {
                "parameters": copy.deepcopy(ANY_OBJECT),
                "items": {"type": "array", "item": {
                    "type": "object", "attributes": {
                        "settings": copy.deepcopy(ANY_OBJECT),
                        "empty": {"type": "object"},
                    },
                }},
            },
        }}},
        "mirrors": {"singular": "mirror", "ximportresources": ["/catalogs/entries"]},
    }}
    before = copy.deepcopy(definition)
    schema = GENERATOR.generate_json_structure(definition)
    assert definition == before
    validator = contract_validator(schema)
    version = {
        "parameters": {"nested": [{"value": True}]},
        "items": [{"settings": {"mode": "read"}, "empty": {}}],
    }
    value = {"catalogs": {"c": {"entries": {"e": {"versions": {"v1": version}}}}},
             "mirrors": {"m": {"entries": {"e": {"versions": {"v2": version}}}}}}
    original = copy.deepcopy(value)
    validator.validate(value)
    assert value == original
    invalid = copy.deepcopy(value)
    invalid["mirrors"]["m"]["entries"]["e"]["versions"]["v2"]["items"][0]["empty"]["extra"] = True
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(invalid)


def test_dialect_map_keys_do_not_claim_core_parameter_name_admission():
    definition = model({**copy.deepcopy(ANY_OBJECT), "namecharset": "strict"})
    before = copy.deepcopy(definition)
    schema = GENERATOR.generate_json_structure(definition)
    assert definition == before
    parameters = parameter_schema(schema)
    assert "keyNames" not in parameters and "propertyNames" not in parameters
    contract_validator(schema).validate(document({"not a Core attribute name": 7}))


@pytest.mark.parametrize("invalid", [
    {"type": "object", "properties": {}, "additionalProperties": True},
    {"type": "map", "items": {"type": "any"}},
    {"type": "map", "values": {"type": "any"}, "maxEntries": 0},
    {"type": "map", "values": {"type": "any"}, "const": {}},
])
def test_contract_checker_rejects_invalid_or_unenabled_dialect_shapes(invalid):
    schema = {
        "$uses": ["JSONStructureAlternateNames"], "definitions": {},
        **invalid,
    }
    with pytest.raises(AssertionError):
        contract_validator(schema)


def test_open_map_can_contain_independently_closed_empty_values():
    schema = GENERATOR.generate_json_structure(model({
        "type": "object", "attributes": {"*": {"type": "object"}},
    }))
    parameters = parameter_schema(schema)
    assert parameters["type"] == "map" and "maxEntries" not in parameters
    assert "$ref" in parameters["values"]["type"]
    validator = contract_validator(schema)
    validator.validate(document({"first": {}, "second": {}}))
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(document({"first": {"extra": 7}}))


@pytest.mark.parametrize("kind", ["array", "map"])
def test_dynamic_objects_as_collection_items_keep_valid_references(kind):
    schema = GENERATOR.generate_json_structure(model({
        "type": kind, "item": copy.deepcopy(ANY_OBJECT),
    }))
    item = parameter_schema(schema)["items" if kind == "array" else "values"]
    assert "$ref" in item["type"]
    validator = contract_validator(schema)
    value = [{"nested": [7]}, {}] if kind == "array" else {
        "first": {"nested": [7]}, "second": {},
    }
    validator.validate(document(value))
    invalid = [7] if kind == "array" else {"first": 7}
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(document(invalid))


def test_cli_emits_dynamic_and_closed_empty_contracts_without_mutating_source(tmp_path):
    definition = model({
        "type": "object", "attributes": {
            "open": copy.deepcopy(ANY_OBJECT),
            "closed": {"type": "object"},
        },
    })
    source = tmp_path / "model.json"
    output = tmp_path / "structure.json"
    source.write_text(json.dumps(definition), encoding="utf-8")
    before = source.read_bytes()
    result = subprocess.run(
        [sys.executable, "-B", str(ROOT / "tools" / "schema-generator.py"),
         "--type", "json-structure", "--output", str(output), str(source)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert source.read_bytes() == before
    schema = json.loads(output.read_text(encoding="utf-8"))
    properties = parameter_schema(schema)["properties"]
    assert properties["open"] == {"type": "map", "values": {"type": "any"}}
    assert properties["closed"]["maxEntries"] == 0
    validator = contract_validator(schema)
    validator.validate(document({"open": {"extra": True}, "closed": {}}))
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(document({"closed": {"extra": True}}))
