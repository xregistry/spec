"""Scalar `item.enum` on array elements and map values.

The reviewed Endpoint directive moves a role value set from the owning array
onto the element definition. These tests exercise the real source meta-schema,
the real `jsonschema`/OpenAPI validators, the emitted JSON Structure contract
and the real Avro parser, reader and writer.

Membership, `strict`, the advisory form and the absent or empty set reuse the
attribute rules. Only scalar items carry `enum`; `strict` without an enum is
ineffective even on a container item. Declared values must have the item's
scalar kind whether or not membership is enforced. Owning-container enums are
rejected. Avro carries string symbol sets only; other sets keep the plain type.
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
from openapi_schema_validator import OAS30ReadValidator, OAS30Validator, OAS30WriteValidator
from openapi_spec_validator import validate


ROOT = Path(__file__).resolve().parent.parent


def _load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GENERATOR = _load("schema_generator", "tools/schema-generator.py")
VALIDATE_MODELS = _load("validate_models", "tools/validate-models.py")
MODEL_SCHEMA = json.loads((ROOT / "core" / "model.schema.json").read_text(encoding="utf-8"))
SOURCE = VALIDATE_MODELS.source_validator(MODEL_SCHEMA)
EXPANDED = VALIDATE_MODELS.expanded_validator(MODEL_SCHEMA)

STAMP = "2026-01-01T00:00:00Z"
DIALECTS = ["json-schema", "openapi"]
ROLES = ["subscriber", "consumer", "producer"]
SCALAR_ITEM_TYPES = ["string", "uri", "xid", "timestamp", "uritemplate"]
NON_SCALAR_ITEM_TYPES = ["array", "map", "object", "any"]
EMITTERS = [
    "generate_json_schema", "generate_openapi", "generate_json_structure",
    "generate_avro_schema",
]


def non_scalar_item(item_type, **aspects):
    item = {"type": item_type, **aspects}
    if item_type in ("array", "map"):
        item["item"] = {"type": "string"}
    return item


def base_model():
    return {
        "attributes": {},
        "groups": {"catalogs": {
            "singular": "catalog",
            "attributes": {},
            "resources": {"entries": {
                "singular": "entry", "hasdocument": False, "maxversions": 0,
                "attributes": {}, "metaattributes": {},
            }},
        }},
    }


def entry_meta():
    resource = "/catalogs/c/entries/e"
    return {
        "entryid": "e", "readonly": False,
        "self": f"https://example.com{resource}/meta",
        "xid": f"{resource}/meta", "epoch": 1,
        "createdat": STAMP, "modifiedat": STAMP,
        "defaultversionid": "v1",
        "defaultversionurl": f"https://example.com{resource}/versions/v1",
        "defaultversionsticky": False,
    }


def base_document():
    return {
        "registryid": "r", "specversion": "1.0", "self": "https://example.com/",
        "xid": "/", "epoch": 1, "createdat": STAMP, "modifiedat": STAMP,
        "catalogs": {"c": {
            "catalogid": "c",
            "entries": {"e": {
                "entryid": "e", "meta": entry_meta(),
                "versions": {"v1": {"entryid": "e", "versionid": "v1"}},
            }},
        }},
    }


def model_with(definition, name="usage"):
    model = base_model()
    model["attributes"][name] = copy.deepcopy(definition)
    return model


def group_model_with(definition, name="usage", plural="catalogs"):
    """The Avro and JSON Structure emitters project Group-owned attributes."""
    model = base_model()
    if plural != "catalogs":
        model["groups"][plural] = copy.deepcopy(model["groups"]["catalogs"])
        model["groups"][plural]["singular"] = plural[:-1]
    model["groups"][plural]["attributes"][name] = copy.deepcopy(definition)
    return model


def document_with(value, name="usage"):
    document = base_document()
    document[name] = value
    return document


def roles_array(**item_extra):
    return {"type": "array", "item": {"type": "string", **item_extra}}


ROLE_ARRAY = roles_array(enum=list(ROLES))
ROLE_MAP = {"type": "map", "item": {"type": "string", "enum": list(ROLES)}}


# --- source meta-schema: the admitted and rejected item vocabulary ----------


def accepts_source(instance, validator=SOURCE):
    before = copy.deepcopy(instance)
    validator.validate(instance)
    assert instance == before


def rejects_source(instance, validator=SOURCE):
    before = copy.deepcopy(instance)
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(instance)
    assert instance == before


@pytest.mark.parametrize("carrier", ["array", "map"])
def test_source_admits_a_string_item_enum_on_an_array_or_map(carrier):
    accepts_source(model_with(
        {"type": carrier, "item": {"type": "string", "enum": list(ROLES)}}
    ))


@pytest.mark.parametrize("item_type", SCALAR_ITEM_TYPES)
def test_source_admits_an_item_enum_on_every_scalar_item_type(item_type):
    accepts_source(model_with(
        {"type": "array", "item": {"type": item_type, "enum": ["a"]}}
    ))


@pytest.mark.parametrize("strict", [True, False])
def test_source_admits_an_explicit_item_strict_flag(strict):
    accepts_source(model_with(roles_array(enum=list(ROLES), strict=strict)))


def test_source_admits_an_empty_item_enum_like_an_attribute_enum():
    accepts_source(model_with(roles_array(enum=[])))


@pytest.mark.parametrize("item_type", NON_SCALAR_ITEM_TYPES)
def test_source_rejects_an_item_enum_on_a_non_scalar_item_type(item_type):
    rejects_source(model_with(
        {"type": "array", "item": non_scalar_item(item_type, enum=["a"])}))


@pytest.mark.parametrize("item_type", NON_SCALAR_ITEM_TYPES)
@pytest.mark.parametrize("strict", [True, False])
def test_source_accepts_an_inert_item_strict_on_a_non_scalar(item_type, strict):
    accepts_source(model_with(
        {"type": "array", "item": non_scalar_item(item_type, strict=strict)}))
    rejects_source(model_with({
        "type": "array",
        "item": non_scalar_item(item_type, enum=["a"], strict=strict),
    }))


@pytest.mark.parametrize("strict", [True, False])
def test_source_admits_a_scalar_item_strict_without_an_enum(strict):
    accepts_source(model_with(roles_array(strict=strict)))


@pytest.mark.parametrize("value", ["subscriber", {"0": "subscriber"}, 3])
def test_source_rejects_an_item_enum_that_is_not_an_array(value):
    rejects_source(model_with(roles_array(enum=value)))


@pytest.mark.parametrize("value", ["true", 1, [True]])
def test_source_rejects_a_non_boolean_item_strict(value):
    rejects_source(model_with(roles_array(enum=list(ROLES), strict=value)))


def test_source_admits_an_item_enum_inside_a_nested_container():
    accepts_source(model_with({
        "type": "array",
        "item": {"type": "map", "item": {"type": "string", "enum": list(ROLES)}},
    }))
    accepts_source(model_with({
        "type": "map",
        "item": {"type": "array", "item": {"type": "string", "enum": list(ROLES)}},
    }))


def test_source_still_rejects_an_unknown_item_keyword():
    rejects_source(model_with(roles_array(symbols=list(ROLES))))


def test_the_expanded_stage_accepts_a_completed_item_enum():
    accepts_source(model_with(ROLE_ARRAY), validator=EXPANDED)


def test_the_expanded_stage_still_requires_an_item_type_beside_an_enum():
    rejects_source(model_with({"type": "array", "item": {"enum": list(ROLES)}}),
                   validator=EXPANDED)


# --- JSON Schema and OpenAPI: real membership at the element and value ------


def generated_validator(definition, dialect):
    SOURCE.validate(definition)
    source = copy.deepcopy(definition)
    if dialect == "json-schema":
        schema = GENERATOR.generate_json_schema(copy.deepcopy(definition))
        jsonschema.Draft7Validator.check_schema(schema)
    else:
        openapi = GENERATOR.generate_openapi(copy.deepcopy(definition))
        validate(openapi)
        reference = openapi["paths"]["/"]["get"]["responses"]["200"][
            "content"]["application/json"]["schema"]
        schema = {**reference, "components": openapi["components"]}
    assert definition == source, "the generator must not mutate its input model"
    return jsonschema.Draft7Validator(schema)


def accepts(validator, instance):
    validator.validate(instance)


def rejects(validator, instance):
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(instance)


@pytest.mark.parametrize("dialect", DIALECTS)
@pytest.mark.parametrize("strict", [None, True])
def test_array_elements_are_restricted_to_the_item_enum(dialect, strict):
    item_extra = {"enum": list(ROLES)}
    if strict is not None:
        item_extra["strict"] = strict
    checker = generated_validator(model_with(roles_array(**item_extra)), dialect)
    accepts(checker, document_with([]))
    accepts(checker, document_with(list(ROLES)))
    accepts(checker, document_with(["producer", "producer"]))
    rejects(checker, document_with(["publisher"]))
    rejects(checker, document_with(["subscriber", "publisher"]))


@pytest.mark.parametrize("dialect", DIALECTS)
def test_map_values_are_restricted_to_the_item_enum(dialect):
    checker = generated_validator(model_with(ROLE_MAP), dialect)
    accepts(checker, document_with({"a": "subscriber", "b": "producer"}))
    rejects(checker, document_with({"a": "publisher"}))
    rejects(checker, document_with({"a": "subscriber", "b": "publisher"}))


@pytest.mark.parametrize("dialect", DIALECTS)
def test_item_membership_stays_case_sensitive(dialect):
    checker = generated_validator(model_with(ROLE_ARRAY), dialect)
    accepts(checker, document_with(["subscriber"]))
    rejects(checker, document_with(["Subscriber"]))
    rejects(checker, document_with(["SUBSCRIBER"]))


@pytest.mark.parametrize("dialect", DIALECTS)
def test_string_and_boolean_item_kinds_keep_their_own_values(dialect):
    strings = generated_validator(
        model_with(roles_array(enum=["true", "false"])), dialect)
    accepts(strings, document_with(["true"]))
    rejects(strings, document_with([True]))
    booleans = generated_validator(
        model_with({"type": "array", "item": {"type": "boolean", "enum": [True]}}),
        dialect)
    accepts(booleans, document_with([True]))
    rejects(booleans, document_with(["true"]))
    rejects(booleans, document_with([False]))


@pytest.mark.parametrize("dialect", DIALECTS)
def test_integer_item_enums_reject_a_matching_string_spelling(dialect):
    checker = generated_validator(
        model_with({"type": "array", "item": {"type": "uinteger", "enum": [0, 1, 2]}}),
        dialect)
    accepts(checker, document_with([0, 2]))
    rejects(checker, document_with([3]))
    rejects(checker, document_with(["1"]))
    rejects(checker, document_with([True]))


@pytest.mark.parametrize("dialect", DIALECTS)
def test_an_advisory_item_enum_admits_a_non_member(dialect):
    checker = generated_validator(
        model_with(roles_array(enum=list(ROLES), strict=False)), dialect)
    accepts(checker, document_with(["publisher"]))


@pytest.mark.parametrize("dialect", DIALECTS)
@pytest.mark.parametrize("item_extra", [{}, {"enum": []}, {"enum": [], "strict": True}])
def test_an_empty_or_absent_item_enum_adds_no_membership_restriction(
    dialect, item_extra
):
    checker = generated_validator(model_with(roles_array(**item_extra)), dialect)
    accepts(checker, document_with(["publisher"]))
    rejects(checker, document_with([3]))


@pytest.mark.parametrize("dialect", DIALECTS)
@pytest.mark.parametrize("strict", [True, False])
def test_a_scalar_item_strict_without_an_enum_adds_no_restriction(dialect, strict):
    checker = generated_validator(model_with(roles_array(strict=strict)), dialect)
    accepts(checker, document_with(["publisher"]))
    rejects(checker, document_with([3]))


@pytest.mark.parametrize("dialect", DIALECTS)
def test_an_array_of_maps_projects_the_inner_value_enum(dialect):
    checker = generated_validator(model_with({
        "type": "array",
        "item": {"type": "map", "item": {"type": "string", "enum": list(ROLES)}},
    }), dialect)
    accepts(checker, document_with([{"a": "consumer"}]))
    rejects(checker, document_with([{"a": "publisher"}]))


@pytest.mark.parametrize("dialect", DIALECTS)
def test_a_map_of_arrays_projects_the_inner_element_enum(dialect):
    checker = generated_validator(model_with({
        "type": "map",
        "item": {"type": "array", "item": {"type": "string", "enum": list(ROLES)}},
    }), dialect)
    accepts(checker, document_with({"a": ["consumer"]}))
    rejects(checker, document_with({"a": ["publisher"]}))


@pytest.mark.parametrize("dialect", DIALECTS)
def test_object_items_keep_their_own_named_scalar_enums(dialect):
    checker = generated_validator(model_with({
        "type": "array",
        "item": {"type": "object", "attributes": {
            "role": {"name": "role", "type": "string", "enum": list(ROLES)},
        }},
    }), dialect)
    accepts(checker, document_with([{"role": "producer"}]))
    rejects(checker, document_with([{"role": "publisher"}]))


@pytest.mark.parametrize("dialect", DIALECTS)
def test_an_item_enum_at_a_group_and_version_attribute(dialect):
    model = base_model()
    model["groups"]["catalogs"]["attributes"]["usage"] = copy.deepcopy(ROLE_ARRAY)
    model["groups"]["catalogs"]["resources"]["entries"]["attributes"]["usage"] = (
        copy.deepcopy(ROLE_ARRAY)
    )
    checker = generated_validator(model, dialect)
    document = base_document()
    document["catalogs"]["c"]["usage"] = ["producer"]
    document["catalogs"]["c"]["entries"]["e"]["versions"]["v1"]["usage"] = ["consumer"]
    accepts(checker, document)
    document["catalogs"]["c"]["usage"] = ["publisher"]
    rejects(checker, document)


def openapi_body_validators(model):
    openapi = GENERATOR.generate_openapi(copy.deepcopy(model))
    validate(openapi)
    components = openapi["components"]

    def build(schema, read):
        implementation = OAS30ReadValidator if read else OAS30WriteValidator
        return implementation({**schema, "components": components},
                              format_checker=OAS30Validator.FORMAT_CHECKER)

    return openapi, build


def registry_body(**extra):
    body = {"registryid": "r", "specversion": "1.0", "self": "https://example.com/",
            "xid": "/", "epoch": 1, "createdat": STAMP, "modifiedat": STAMP}
    body.update(extra)
    return body


def test_a_request_may_omit_or_reset_the_array_but_not_smuggle_a_non_member():
    openapi, build = openapi_body_validators(model_with(ROLE_ARRAY))
    checker = build(openapi["paths"]["/"]["put"]["requestBody"]["content"][
        "application/json"]["schema"], read=False)
    checker.validate(registry_body())
    checker.validate(registry_body(usage=None))
    checker.validate(registry_body(usage=["subscriber"]))
    with pytest.raises(jsonschema.ValidationError):
        checker.validate(registry_body(usage=["publisher"]))
    with pytest.raises(jsonschema.ValidationError):
        checker.validate(registry_body(usage=[None]))


def test_a_response_still_requires_members_of_the_item_enum():
    openapi, build = openapi_body_validators(model_with(ROLE_ARRAY))
    checker = build(openapi["paths"]["/"]["get"]["responses"]["200"]["content"][
        "application/json"]["schema"], read=True)
    checker.validate(registry_body(usage=["consumer"]))
    with pytest.raises(jsonschema.ValidationError):
        checker.validate(registry_body(usage=["publisher"]))


# --- source aspects the generator itself rejects ---------------------------


@pytest.mark.parametrize("enum", [[1], [True], [None], [["subscriber"]], [{}]])
def test_the_generator_rejects_a_wrong_kind_item_enum_value(enum):
    with pytest.raises(ValueError, match="not a valid string"):
        GENERATOR.generate_json_schema(model_with(roles_array(enum=enum)))


def test_the_generator_rejects_a_wrong_kind_value_for_a_numeric_item():
    with pytest.raises(ValueError, match="not a valid uinteger"):
        GENERATOR.generate_json_schema(model_with(
            {"type": "array", "item": {"type": "uinteger", "enum": ["1"]}}))


@pytest.mark.parametrize("generate", EMITTERS)
@pytest.mark.parametrize("item_type", NON_SCALAR_ITEM_TYPES)
def test_every_emitter_rejects_an_item_enum_on_a_non_scalar_item(generate, item_type):
    with pytest.raises(ValueError, match="scalar item types only"):
        getattr(GENERATOR, generate)(group_model_with(
            {"type": "array", "item": non_scalar_item(item_type, enum=["a"])}))


@pytest.mark.parametrize("generate", EMITTERS)
@pytest.mark.parametrize("item_type", NON_SCALAR_ITEM_TYPES)
@pytest.mark.parametrize("strict", [True, False])
def test_inert_item_strict_does_not_change_emitted_schema(
    generate, item_type, strict
):
    baseline = group_model_with(
        {"type": "array", "item": non_scalar_item(item_type)}
    )
    candidate = group_model_with(
        {"type": "array", "item": non_scalar_item(item_type, strict=strict)}
    )
    assert getattr(GENERATOR, generate)(candidate) == getattr(
        GENERATOR, generate
    )(baseline)


@pytest.mark.parametrize("generate", EMITTERS)
@pytest.mark.parametrize("strict", ["true", 1, None])
def test_every_emitter_rejects_a_non_boolean_item_strict(generate, strict):
    with pytest.raises(ValueError, match="must be a Boolean"):
        getattr(GENERATOR, generate)(group_model_with(
            {"type": "array", "item": non_scalar_item("map", strict=strict)}))


@pytest.mark.parametrize("generate", EMITTERS)
def test_an_advisory_item_enum_still_requires_its_own_value_kinds(generate):
    """`strict` false makes membership advisory; it does not relax the declared
    `item.type` of each value."""
    with pytest.raises(ValueError, match="not a valid string"):
        getattr(GENERATOR, generate)(
            group_model_with(roles_array(enum=[1], strict=False)))


@pytest.mark.parametrize("strict", [None, True, False])
def test_an_advisory_or_strict_wrong_kind_item_enum_is_rejected_when_nested(strict):
    item = {"type": "string", "enum": [1]}
    if strict is not None:
        item["strict"] = strict
    with pytest.raises(ValueError, match="not a valid string"):
        GENERATOR.generate_json_schema(model_with({
            "type": "map", "item": {"type": "array", "item": item},
        }))


@pytest.mark.parametrize("generate", EMITTERS)
def test_an_empty_advisory_item_enum_stays_a_legal_source_model(generate):
    getattr(GENERATOR, generate)(
        group_model_with(roles_array(enum=[], strict=False)))


def test_a_wrong_kind_item_enum_is_rejected_inside_a_nested_container():
    with pytest.raises(ValueError, match="not a valid string"):
        GENERATOR.generate_json_schema(model_with({
            "type": "map",
            "item": {"type": "array", "item": {"type": "string", "enum": [1]}},
        }))


# --- JSON Structure: the emitted contract, not an SDK claim -----------------


def structure_of(model, path):
    structure = GENERATOR.generate_json_structure(copy.deepcopy(model),
                                                  schema_name="Doc")
    node = structure["definitions"]["Catalogs"]["Catalog"]["properties"]
    for segment in path:
        node = node[segment]
    return node


def test_json_structure_array_items_carry_the_item_enum():
    items = structure_of(group_model_with(ROLE_ARRAY), ["usage", "items"])
    assert items["type"] == "string"
    assert items["enum"] == ROLES


def test_json_structure_map_values_carry_the_item_enum():
    values = structure_of(group_model_with(ROLE_MAP), ["usage", "values"])
    assert values["type"] == "string"
    assert values["enum"] == ROLES


def test_json_structure_omits_an_advisory_or_empty_item_enum():
    advisory = structure_of(
        group_model_with(roles_array(enum=list(ROLES), strict=False)),
        ["usage", "items"])
    assert "enum" not in advisory
    empty = structure_of(group_model_with(roles_array(enum=[])), ["usage", "items"])
    assert "enum" not in empty


def test_json_structure_carries_a_nested_item_enum():
    values = structure_of(group_model_with({
        "type": "array",
        "item": {"type": "map", "item": {"type": "string", "enum": list(ROLES)}},
    }), ["usage", "items", "values"])
    assert values["enum"] == ROLES


# --- Avro: the real parser, reader and writer ------------------------------


def avro_of(model):
    return GENERATOR.generate_avro_schema(copy.deepcopy(model))


def avro_usage(schema_data, plural="catalogs"):
    group = next(field for field in schema_data["fields"]
                 if field["name"] == plural)["type"]["values"]
    return next(field for field in group["fields"]
                if field["name"] == "usage")["type"]


def parsed(schema_data):
    return avro.schema.parse(json.dumps(schema_data))


def round_trip(schema, datum):
    buffer = io.BytesIO()
    avro.io.DatumWriter(schema).write(datum, avro.io.BinaryEncoder(buffer))
    buffer.seek(0)
    return avro.io.DatumReader(schema).read(avro.io.BinaryDecoder(buffer))


def usage_schema(schema_data, plural="catalogs"):
    document = parsed(schema_data)
    group = document.fields_dict[plural].type.values
    return group.fields_dict["usage"].type


def test_avro_names_a_string_item_enum_after_its_owning_attribute():
    schema_data = avro_of(group_model_with(ROLE_ARRAY))
    items = avro_usage(schema_data)["items"]
    assert items["type"] == "enum"
    assert items["name"] == "UsageEnumType"
    assert items["namespace"] == "io.xregistry"
    assert items["symbols"] == ROLES
    assert json.dumps(schema_data).count('"UsageEnumType"') == 1


def test_avro_accepts_the_declared_roles_and_rejects_an_unknown_one():
    schema = usage_schema(avro_of(group_model_with(ROLE_ARRAY)))
    assert avro.io.validate(schema, list(ROLES))
    assert not avro.io.validate(schema, ["publisher"])
    assert not avro.io.validate(schema, ["Subscriber"])


def test_avro_round_trips_every_declared_role():
    schema = usage_schema(avro_of(group_model_with(ROLE_ARRAY)))
    assert round_trip(schema, list(ROLES)) == ROLES


@pytest.mark.parametrize("datum", [[1], [True], [None], [{"role": "producer"}]])
def test_avro_rejects_a_wrong_kind_datum_for_the_enum(datum):
    schema = usage_schema(avro_of(group_model_with(ROLE_ARRAY)))
    assert not avro.io.validate(schema, datum)


def test_avro_projects_a_map_value_item_enum():
    schema_data = avro_of(group_model_with(ROLE_MAP))
    values = avro_usage(schema_data)["values"]
    assert values["type"] == "enum"
    assert values["symbols"] == ROLES
    schema = usage_schema(schema_data)
    assert avro.io.validate(schema, {"a": "consumer"})
    assert not avro.io.validate(schema, {"a": "publisher"})


@pytest.mark.parametrize("enum", [
    ["with-dash"], ["9lives"], ["with space"], [""],
])
def test_avro_falls_back_when_the_value_set_is_not_a_legal_symbol_set(enum):
    """Avro enums carry named string symbols only; a set Avro cannot name is
    projected as the plain mapped type instead of an invented codec."""
    schema_data = avro_of(group_model_with(roles_array(enum=enum)))
    assert avro_usage(schema_data)["items"] == {"type": "string"}
    assert avro.io.validate(usage_schema(schema_data), ["anything"])


def test_avro_deduplicates_repeated_legal_symbols_in_first_occurrence_order():
    """A repeated legal value names the same symbol, so the set stays fully
    representable and keeps enforcing membership."""
    schema_data = avro_of(group_model_with(
        roles_array(enum=["producer", "consumer", "producer", "subscriber"])))
    items = avro_usage(schema_data)["items"]
    assert items["name"] == "UsageEnumType"
    assert items["symbols"] == ["producer", "consumer", "subscriber"]
    schema = usage_schema(schema_data)
    assert round_trip(schema, ["producer", "subscriber"]) == ["producer", "subscriber"]
    assert not avro.io.validate(schema, ["publisher"])


def test_avro_falls_back_for_a_non_string_scalar_item_enum():
    schema_data = avro_of(group_model_with(
        {"type": "array", "item": {"type": "uinteger", "enum": [0, 1, 2]}}))
    assert avro_usage(schema_data)["items"] == {"type": "int"}
    assert avro.io.validate(usage_schema(schema_data), [7])


def test_avro_omits_an_advisory_or_empty_item_enum():
    for definition in (roles_array(enum=list(ROLES), strict=False),
                       roles_array(enum=[]), roles_array()):
        schema_data = avro_of(group_model_with(definition))
        assert avro_usage(schema_data)["items"] == {"type": "string"}


def two_group_model(first, second):
    model = group_model_with(first)
    model["groups"]["indexes"] = copy.deepcopy(base_model()["groups"]["catalogs"])
    model["groups"]["indexes"]["singular"] = "index"
    model["groups"]["indexes"]["resources"]["indexentries"] = (
        model["groups"]["indexes"]["resources"].pop("entries")
    )
    model["groups"]["indexes"]["resources"]["indexentries"]["singular"] = "indexentry"
    model["groups"]["indexes"]["attributes"]["usage"] = copy.deepcopy(second)
    return model


def test_avro_shares_one_named_enum_across_declaring_groups():
    schema_data = avro_of(two_group_model(ROLE_ARRAY, ROLE_ARRAY))
    assert parsed(schema_data) is not None
    assert json.dumps(schema_data).count('"symbols"') == 1
    assert avro_usage(schema_data)["items"]["name"] == "UsageEnumType"
    assert avro_usage(schema_data, "indexes")["items"] == "io.xregistry.UsageEnumType"
    for plural in ("catalogs", "indexes"):
        schema = usage_schema(schema_data, plural)
        assert round_trip(schema, list(ROLES)) == ROLES
        assert not avro.io.validate(schema, ["publisher"])


def test_avro_keeps_strict_membership_for_a_second_different_value_set():
    """Avro admits a name once, so a different legal set takes the next
    deterministic name in the same convention rather than losing membership."""
    other = ["auditor"]
    schema_data = avro_of(two_group_model(ROLE_ARRAY, roles_array(enum=other)))
    assert parsed(schema_data) is not None
    first = avro_usage(schema_data)["items"]
    second = avro_usage(schema_data, "indexes")["items"]
    assert first["name"] == "UsageEnumType" and first["symbols"] == ROLES
    assert second["name"] == "UsageEnumType2" and second["symbols"] == other
    catalogs = usage_schema(schema_data)
    indexes = usage_schema(schema_data, "indexes")
    assert round_trip(catalogs, list(ROLES)) == ROLES
    assert round_trip(indexes, other) == other
    assert not avro.io.validate(catalogs, other)
    assert not avro.io.validate(indexes, ["producer"])
    assert not avro.io.validate(indexes, ["publisher"])


def test_avro_reuses_a_renamed_definition_for_a_later_identical_set():
    other = ["auditor"]
    model = two_group_model(ROLE_ARRAY, roles_array(enum=other))
    model["groups"]["ledgers"] = copy.deepcopy(model["groups"]["indexes"])
    model["groups"]["ledgers"]["singular"] = "ledger"
    model["groups"]["ledgers"]["resources"]["ledgerentries"] = (
        model["groups"]["ledgers"]["resources"].pop("indexentries")
    )
    model["groups"]["ledgers"]["resources"]["ledgerentries"]["singular"] = "ledgerentry"
    schema_data = avro_of(model)
    assert parsed(schema_data) is not None
    assert json.dumps(schema_data).count('"symbols"') == 2
    assert avro_usage(schema_data, "ledgers")["items"] == "io.xregistry.UsageEnumType2"
    ledgers = usage_schema(schema_data, "ledgers")
    assert round_trip(ledgers, other) == other
    assert not avro.io.validate(ledgers, ["producer"])


# --- the shipped models keep their existing generated identities -----------


def endpoint_model():
    source = json.loads((ROOT / "endpoint" / "model.json").read_text(encoding="utf-8"))
    return GENERATOR.resolve_imports(str(ROOT / "endpoint"), source)


def composite_model():
    merged = {}
    for directory in ("endpoint", "message", "schema"):
        source = json.loads(
            (ROOT / directory / "model.json").read_text(encoding="utf-8"))
        resolved = GENERATOR.resolve_imports(str(ROOT / directory), source)
        merged.setdefault("groups", {}).update(resolved.get("groups", {}))
        for key, value in resolved.items():
            if key != "groups":
                merged.setdefault(key, value)
    return merged


@pytest.mark.parametrize("build", [endpoint_model, composite_model])
def test_the_shipped_endpoint_usage_enum_stays_a_single_avro_definition(build):
    schema_data = avro_of(build())
    assert parsed(schema_data) is not None
    assert json.dumps(schema_data).count('"UsageEnumType"') == 1
