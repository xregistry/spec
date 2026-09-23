"""Scalar `item.enum` and `item.strict` on array elements and map values.

The reviewed Endpoint directive moves the role value set from prose onto the
element definition. These tests exercise the real source meta-schema, the real
`jsonschema` and OpenAPI validators, the emitted JSON Structure contract and the
real Avro parser, reader and writer.

Only scalar items carry `enum`; `strict` without an enum is ineffective even
on a container item. Declared values must have the item's own scalar kind
whether or not `strict` enforces membership, and an absent or empty set adds no
membership restriction. Core does not permit an `enum` on the owning array or
map attribute itself, so that spelling is rejected rather than projected.
"""

import copy
import importlib.util
import io
import json
from pathlib import Path

import avro.io
import avro.schema
import jsonschema
import pytest
from openapi_schema_validator import OAS30Validator


ROOT = Path(__file__).resolve().parent.parent


def _load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GENERATOR = _load("schema_generator_item_enum", "tools/schema-generator.py")
MODEL_SCHEMA = json.loads(
    (ROOT / "core" / "model.schema.json").read_text(encoding="utf-8")
)
SOURCE = jsonschema.Draft7Validator(MODEL_SCHEMA)

ROLES = ["subscriber", "consumer", "producer"]
SCALAR_ITEM_TYPES = ["string", "uri", "xid", "timestamp", "uritemplate"]
NON_SCALAR_ITEM_TYPES = ["array", "map", "object", "any"]
EMITTERS = [
    "generate_json_schema",
    "generate_openapi",
    "generate_json_structure",
    "generate_avro_schema",
]


def container(item_type, **aspects):
    """A container item definition, with the nested `item` its own type needs."""
    item = {"type": item_type, **aspects}
    if item_type in ("array", "map"):
        item["item"] = {"type": "string"}
    return item


def model(attribute, group="catalogs", singular="catalog"):
    return {
        "groups": {
            group: {
                "singular": singular,
                "attributes": {"roles": dict(attribute, name="roles")},
                "resources": {
                    "entries": {
                        "singular": "entry",
                        "attributes": {"*": {"name": "*", "type": "any"}},
                    }
                },
            }
        }
    }


def array_of(item):
    return model({"type": "array", "item": copy.deepcopy(item)})


def map_of(item):
    return model({"type": "map", "item": copy.deepcopy(item)})


def emit(emitter, definition):
    """Run one emitter over its own copy, so no caller input is mutated."""
    return getattr(GENERATOR, emitter)(copy.deepcopy(definition))


def json_schema_property(definition, name="roles"):
    generated = emit("generate_json_schema", definition)
    return generated["definitions"]["catalog-schema"]["catalog"]["properties"][name]


def openapi_property(definition, name="roles"):
    generated = emit("generate_openapi", definition)
    return generated["components"]["schemas"]["catalog"]["properties"][name]


def structure_property(definition, name="roles"):
    generated = emit("generate_json_structure", definition)
    return generated["definitions"]["Catalogs"]["Catalog"]["properties"][name]


def avro_group_record(definition, group="catalogs"):
    generated = emit("generate_avro_schema", definition)
    parsed = avro.schema.parse(json.dumps(generated))
    field = next(each for each in parsed.fields if each.name == group)
    return field.type.values


def avro_field(definition, name="roles", group="catalogs"):
    record = avro_group_record(definition, group)
    return next(each for each in record.fields if each.name == name)


def avro_round_trip(schema, datum):
    """Write and read one datum through the real Avro binary codec."""
    buffer = io.BytesIO()
    avro.io.DatumWriter(schema).write(datum, avro.io.BinaryEncoder(buffer))
    buffer.seek(0)
    return avro.io.DatumReader(schema).read(avro.io.BinaryDecoder(buffer))


def source_errors(definition):
    return list(SOURCE.iter_errors(definition))


# --- source meta-schema admission -------------------------------------------


@pytest.mark.parametrize("item_type", SCALAR_ITEM_TYPES)
def test_source_admits_a_scalar_item_enum(item_type):
    values = ROLES if item_type in ("string", "uritemplate") else ["2026-01-01T00:00:00Z"]
    assert not source_errors(array_of({"type": item_type, "enum": values}))


@pytest.mark.parametrize("strict", [True, False])
def test_source_admits_a_scalar_item_strict_without_an_enum(strict):
    assert not source_errors(array_of({"type": "string", "strict": strict}))


@pytest.mark.parametrize("item_type", NON_SCALAR_ITEM_TYPES)
def test_source_rejects_an_item_enum_on_a_non_scalar_item_type(item_type):
    errors = source_errors(array_of(container(item_type, enum=["a"])))
    assert errors, f"{item_type} item must not carry an enum value set"


@pytest.mark.parametrize("item_type", NON_SCALAR_ITEM_TYPES)
@pytest.mark.parametrize("strict", [True, False])
def test_source_accepts_an_inert_item_strict_on_a_non_scalar(item_type, strict):
    assert not source_errors(array_of(container(item_type, strict=strict)))
    assert source_errors(
        array_of(container(item_type, enum=["a"], strict=strict))
    )


@pytest.mark.parametrize("strict", ["true", 1, "yes", None])
def test_source_rejects_a_non_boolean_item_strict(strict):
    errors = source_errors(array_of({"type": "string", "enum": ROLES, "strict": strict}))
    assert errors, "item.strict is a Boolean aspect"


def test_source_admits_an_empty_item_enum():
    assert not source_errors(array_of({"type": "string", "enum": []}))


@pytest.mark.parametrize("attr_type", ["array", "map"])
def test_source_rejects_an_enum_on_the_owning_container_attribute(attr_type):
    definition = model(
        {"type": attr_type, "item": {"type": "string"}, "enum": ROLES}
    )
    errors = source_errors(definition)
    assert errors, "Core does not permit an enum on the owning array or map"


@pytest.mark.parametrize("attr_type", NON_SCALAR_ITEM_TYPES)
@pytest.mark.parametrize("strict", [True, False])
def test_source_accepts_an_inert_strict_on_the_owning_container(attr_type, strict):
    definition = model(
        container(attr_type, strict=strict)
    )
    assert not source_errors(definition)


def test_source_still_admits_a_scalar_attribute_enum():
    definition = model({"type": "string", "enum": ROLES})
    assert not source_errors(definition)


def test_the_shipped_models_stay_valid_against_the_source_meta_schema():
    for relative in [
        "core/model.json",
        "endpoint/model.json",
        "message/model.json",
        "schema/model.json",
    ]:
        path = ROOT / relative
        if not path.exists():
            continue
        instance = json.loads(path.read_text(encoding="utf-8"))
        assert not source_errors(instance), relative


# --- every emitter rejects the same illegal source ---------------------------


@pytest.mark.parametrize("emitter", EMITTERS)
@pytest.mark.parametrize("item_type", NON_SCALAR_ITEM_TYPES)
def test_every_emitter_rejects_an_item_enum_on_a_non_scalar_item(emitter, item_type):
    with pytest.raises(ValueError):
        emit(emitter, array_of(container(item_type, enum=["a"])))


@pytest.mark.parametrize("emitter", EMITTERS)
@pytest.mark.parametrize("item_type", NON_SCALAR_ITEM_TYPES)
@pytest.mark.parametrize("strict", [True, False])
def test_inert_item_strict_does_not_change_emitted_schema(emitter, item_type, strict):
    baseline = array_of(container(item_type))
    candidate = array_of(container(item_type, strict=strict))
    assert emit(emitter, candidate) == emit(emitter, baseline)


@pytest.mark.parametrize("emitter", EMITTERS)
@pytest.mark.parametrize("attr_type", NON_SCALAR_ITEM_TYPES)
@pytest.mark.parametrize("strict", [True, False])
def test_inert_container_strict_does_not_change_emitted_schema(
    emitter, attr_type, strict
):
    assert emit(emitter, model(container(attr_type, strict=strict))) == emit(
        emitter, model(container(attr_type))
    )


@pytest.mark.parametrize("emitter", EMITTERS)
@pytest.mark.parametrize("strict", ["true", 1, None])
def test_every_emitter_rejects_a_non_boolean_item_strict(emitter, strict):
    with pytest.raises(ValueError, match="must be a Boolean"):
        emit(emitter, array_of(container("map", strict=strict)))


@pytest.mark.parametrize("emitter", EMITTERS)
def test_every_emitter_rejects_a_wrong_kind_item_enum(emitter):
    with pytest.raises(ValueError):
        emit(emitter, array_of({"type": "uinteger", "enum": ["not-a-number"]}))


@pytest.mark.parametrize("emitter", EMITTERS)
def test_an_advisory_item_enum_still_requires_its_own_value_kinds(emitter):
    with pytest.raises(ValueError):
        emit(
            emitter,
            array_of({"type": "uinteger", "enum": ["not-a-number"], "strict": False}),
        )


@pytest.mark.parametrize("emitter", EMITTERS)
@pytest.mark.parametrize("strict", [None, True, False])
def test_a_wrong_kind_item_enum_is_rejected_inside_a_nested_container(emitter, strict):
    inner = {"type": "string", "enum": [1]}
    if strict is not None:
        inner["strict"] = strict
    with pytest.raises(ValueError):
        emit(emitter, map_of({"type": "array", "item": inner}))


@pytest.mark.parametrize("emitter", EMITTERS)
@pytest.mark.parametrize("attr_type", ["array", "map"])
def test_every_emitter_rejects_an_enum_on_the_owning_container(emitter, attr_type):
    definition = model({"type": attr_type, "item": {"type": "string"}, "enum": ROLES})
    with pytest.raises(ValueError):
        emit(emitter, definition)


@pytest.mark.parametrize("emitter", EMITTERS)
def test_every_emitter_accepts_an_empty_or_advisory_item_enum(emitter):
    assert emit(emitter, array_of({"type": "string", "enum": []})) is not None
    assert emit(
        emitter, array_of({"type": "string", "enum": ROLES, "strict": False})
    ) is not None
    assert emit(emitter, array_of({"type": "string", "strict": True})) is not None


# --- projected restrictions --------------------------------------------------


def test_json_schema_restricts_the_actual_array_elements():
    schema = json_schema_property(array_of({"type": "string", "enum": ROLES}))
    assert schema["type"] == "array"
    assert schema["items"]["enum"] == ROLES
    validator = jsonschema.Draft7Validator(schema)
    assert not list(validator.iter_errors(ROLES))
    assert list(validator.iter_errors(["publisher"]))


def test_json_schema_restricts_the_actual_map_values():
    schema = json_schema_property(map_of({"type": "string", "enum": ROLES}))
    assert schema["type"] == "object"
    assert schema["additionalProperties"]["enum"] == ROLES
    validator = jsonschema.Draft7Validator(schema)
    assert not list(validator.iter_errors({"a": "consumer"}))
    assert list(validator.iter_errors({"a": "publisher"}))


def test_openapi_restricts_the_actual_array_elements():
    schema = openapi_property(array_of({"type": "string", "enum": ROLES}))
    assert schema["items"]["enum"] == ROLES
    validator = OAS30Validator(schema)
    assert not list(validator.iter_errors(ROLES))
    assert list(validator.iter_errors(["publisher"]))


def test_json_structure_restricts_the_actual_array_elements():
    schema = structure_property(array_of({"type": "string", "enum": ROLES}))
    assert schema["items"]["enum"] == ROLES


def test_json_structure_restricts_the_actual_map_values():
    schema = structure_property(map_of({"type": "string", "enum": ROLES}))
    assert schema["values"]["enum"] == ROLES


def test_nested_containers_project_the_inner_restriction_consistently():
    definition = map_of({"type": "array", "item": {"type": "string", "enum": ROLES}})
    schema = json_schema_property(definition)
    assert schema["additionalProperties"]["items"]["enum"] == ROLES
    validator = jsonschema.Draft7Validator(schema)
    assert not list(validator.iter_errors({"a": ["producer"]}))
    assert list(validator.iter_errors({"a": ["publisher"]}))

    structure = structure_property(definition)
    assert structure["values"]["items"]["enum"] == ROLES


@pytest.mark.parametrize("strict", [False])
def test_an_advisory_item_enum_adds_no_membership_restriction(strict):
    definition = array_of({"type": "string", "enum": ROLES, "strict": strict})
    assert "enum" not in json_schema_property(definition)["items"]
    assert "enum" not in openapi_property(definition)["items"]
    assert "enum" not in structure_property(definition)["items"]
    assert avro_field(definition).type.items.type == "string"


def test_an_empty_item_enum_adds_no_membership_restriction():
    definition = array_of({"type": "string", "enum": []})
    assert "enum" not in json_schema_property(definition)["items"]
    assert "enum" not in structure_property(definition)["items"]
    assert avro_field(definition).type.items.type == "string"


def test_a_scalar_item_strict_without_an_enum_adds_no_restriction():
    definition = array_of({"type": "string", "strict": True})
    assert "enum" not in json_schema_property(definition)["items"]
    assert "enum" not in structure_property(definition)["items"]
    assert avro_field(definition).type.items.type == "string"


def test_emitting_does_not_mutate_the_caller_model():
    definition = array_of({"type": "string", "enum": ROLES})
    before = json.dumps(definition, sort_keys=True)
    for emitter in EMITTERS:
        emit(emitter, definition)
    assert json.dumps(definition, sort_keys=True) == before


# --- Avro named enum identity ------------------------------------------------


def test_avro_projects_a_legal_string_set_as_a_named_enum():
    field = avro_field(array_of({"type": "string", "enum": ROLES}))
    items = field.type.items
    assert items.type == "enum"
    assert items.name == "RolesEnumType"
    assert items.namespace == "io.xregistry"
    assert list(items.symbols) == ROLES


@pytest.mark.parametrize("role", ROLES)
def test_avro_round_trips_every_declared_symbol(role):
    field = avro_field(array_of({"type": "string", "enum": ROLES}))
    assert avro_round_trip(field.type, [role]) == [role]


def test_avro_rejects_an_unknown_symbol():
    field = avro_field(array_of({"type": "string", "enum": ROLES}))
    assert avro.io.validate(field.type, list(ROLES))
    assert not avro.io.validate(field.type, ["publisher"])


def test_avro_projects_a_map_value_set_as_a_named_enum():
    field = avro_field(map_of({"type": "string", "enum": ROLES}))
    values = field.type.values
    assert values.type == "enum"
    assert list(values.symbols) == ROLES
    assert avro_round_trip(field.type, {"a": "consumer"}) == {"a": "consumer"}
    assert not avro.io.validate(field.type, {"a": "publisher"})


def test_avro_deduplicates_repeated_symbols_in_first_occurrence_order():
    declared = ["producer", "consumer", "producer", "subscriber"]
    field = avro_field(array_of({"type": "string", "enum": declared}))
    items = field.type.items
    assert list(items.symbols) == ["producer", "consumer", "subscriber"]
    assert avro_round_trip(field.type, ["subscriber"]) == ["subscriber"]
    assert not avro.io.validate(field.type, ["publisher"])


def _two_group_model(first, second):
    definition = model({"type": "array", "item": {"type": "string", "enum": first}})
    # A distinct resource singular keeps the two groups' record names apart;
    # cross-group record naming is not what these cases are about.
    definition["groups"]["ledgers"] = {
        "singular": "ledger",
        "attributes": {
            "roles": {
                "name": "roles",
                "type": "array",
                "item": {"type": "string", "enum": list(second)},
            }
        },
        "resources": {
            "postings": {
                "singular": "posting",
                "attributes": {"*": {"name": "*", "type": "any"}},
            }
        },
    }
    return definition


def test_avro_reuses_one_named_enum_for_an_identical_set():
    generated = emit("generate_avro_schema", _two_group_model(ROLES, list(ROLES)))
    document = json.dumps(generated)
    assert document.count('"RolesEnumType"') == 1
    parsed = avro.schema.parse(document)
    for group in ["catalogs", "ledgers"]:
        field = next(
            each
            for each in next(
                one for one in parsed.fields if one.name == group
            ).type.values.fields
            if each.name == "roles"
        )
        assert avro_round_trip(field.type, ["producer"]) == ["producer"]
        assert not avro.io.validate(field.type, ["publisher"])


def test_avro_keeps_membership_for_a_second_different_set():
    generated = emit("generate_avro_schema", _two_group_model(ROLES, ["auditor"]))
    document = json.dumps(generated)
    assert '"RolesEnumType2"' in document
    parsed = avro.schema.parse(document)
    fields = {}
    for group in ["catalogs", "ledgers"]:
        record = next(one for one in parsed.fields if one.name == group).type.values
        fields[group] = next(each for each in record.fields if each.name == "roles")
    assert list(fields["catalogs"].type.items.symbols) == ROLES
    assert list(fields["ledgers"].type.items.symbols) == ["auditor"]
    assert avro_round_trip(fields["ledgers"].type, ["auditor"]) == ["auditor"]
    assert not avro.io.validate(fields["ledgers"].type, ["producer"])
    assert not avro.io.validate(fields["catalogs"].type, ["auditor"])


def test_avro_identity_is_deterministic_across_runs():
    definition = _two_group_model(ROLES, ["auditor"])
    first = json.dumps(emit("generate_avro_schema", definition))
    second = json.dumps(emit("generate_avro_schema", definition))
    assert first == second


@pytest.mark.parametrize(
    "item_type,values", [("uinteger", [0, 1, 2]), ("integer", [-1, 1]), ("boolean", [True, False])]
)
def test_avro_carries_the_documented_limit_for_a_non_string_scalar_set(item_type, values):
    definition = array_of({"type": item_type, "enum": values})
    field = avro_field(definition)
    assert field.type.items.type != "enum"
    # The restriction stays expressed where the dialect can carry it.
    assert json_schema_property(definition)["items"]["enum"] == values


@pytest.mark.parametrize("value", ["with-dash", "9lives", "with space", ""])
def test_avro_carries_the_documented_limit_for_an_illegal_symbol(value):
    definition = array_of({"type": "string", "enum": [value]})
    field = avro_field(definition)
    assert field.type.items.type == "string"
    assert json_schema_property(definition)["items"]["enum"] == [value]
