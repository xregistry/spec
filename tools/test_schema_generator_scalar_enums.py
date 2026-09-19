"""Strict scalar enum projection into the generated JSON Schema and OpenAPI.

The generator previously dropped every scalar `enum`, so a strict Core value set
was never expressed in either dialect. These tests exercise the real emitter and
the real `jsonschema`/OpenAPI validators across the entity, nesting, wildcard and
conditional paths, the role-aware request/response behavior, and the statically
resolvable Group constraint overlays.

Selector activation (`ifvalues`) stays a separate rule: it is case-insensitive,
and it never makes a non-member legal. Array-level `enum` keeps its existing
behavior here; removing that plumbing depends on the source cleanup owned by the
model-consistency work. The separately approved scalar `item.enum` is projected
and tested in `test_schema_generator_item_enums.py`.
"""

import copy
import importlib.util
import json
from pathlib import Path

import jsonschema
import pytest
from openapi_schema_validator import OAS30ReadValidator, OAS30Validator, OAS30WriteValidator
from openapi_spec_validator import validate


ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "schema_generator", ROOT / "tools" / "schema-generator.py"
)
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)

MODEL_SCHEMA = json.loads((ROOT / "core" / "model.schema.json").read_text(encoding="utf-8"))
SOURCE = jsonschema.Draft7Validator(MODEL_SCHEMA)
STAMP = "2026-01-01T00:00:00Z"
DIALECTS = ["json-schema", "openapi"]

QOS = {"type": "uinteger", "enum": [0, 1, 2]}
MEMBERS = [0, 1, 2]
NON_MEMBERS = [3, -1]
WRONG_TYPES = ["1", True, 1.5, None, [0], {"a": 0}]


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
            "content"
        ]["application/json"]["schema"]
        schema = {**reference, "components": openapi["components"]}
    assert definition == source, "the generator must not mutate its input model"
    return jsonschema.Draft7Validator(schema)


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


def _resource(model):
    return model["groups"]["catalogs"]["resources"]["entries"]


def _entry(document):
    return document["catalogs"]["c"]["entries"]["e"]


def _object_carrier(inner):
    return {"type": "object", "attributes": {"level": inner}}


LOCATIONS = {
    "registry": (
        lambda m, d: m["attributes"].update({"level": d}),
        lambda doc, v: doc.update({"level": v}),
    ),
    "group": (
        lambda m, d: m["groups"]["catalogs"]["attributes"].update({"level": d}),
        lambda doc, v: doc["catalogs"]["c"].update({"level": v}),
    ),
    "version": (
        lambda m, d: _resource(m)["attributes"].update({"level": d}),
        lambda doc, v: _entry(doc)["versions"]["v1"].update({"level": v}),
    ),
    "resource-default-version": (
        lambda m, d: _resource(m)["attributes"].update({"level": d}),
        lambda doc, v: _entry(doc).update({"level": v}),
    ),
    "meta": (
        lambda m, d: _resource(m)["metaattributes"].update({"level": d}),
        lambda doc, v: _entry(doc)["meta"].update({"level": v}),
    ),
    "nested-object": (
        lambda m, d: m["attributes"].update({"box": _object_carrier(d)}),
        lambda doc, v: doc.update({"box": {"level": v}}),
    ),
    "map-of-object": (
        lambda m, d: m["attributes"].update({
            "box": {"type": "map", "item": _object_carrier(d)}}),
        lambda doc, v: doc.update({"box": {"k": {"level": v}}}),
    ),
    "array-of-object": (
        lambda m, d: m["attributes"].update({
            "box": {"type": "array", "item": _object_carrier(d)}}),
        lambda doc, v: doc.update({"box": [{"level": v}]}),
    ),
    "typed-wildcard": (
        lambda m, d: m["attributes"].update({
            "box": {"type": "object", "attributes": {"*": {**d, "name": "*"}}}}),
        lambda doc, v: doc.update({"box": {"anything": v}}),
    ),
    "conditional-sibling": (
        lambda m, d: m["attributes"].update({"kind": {
            "type": "string",
            "ifvalues": {"on": {"siblingattributes": {"level": d}}},
        }}),
        lambda doc, v: doc.update({"kind": "on", "level": v}),
    ),
    "nested-conditional": (
        lambda m, d: m["attributes"].update({"kind": {
            "type": "string",
            "ifvalues": {"on": {"siblingattributes": {"mode": {
                "type": "string",
                "ifvalues": {"deep": {"siblingattributes": {"level": d}}},
            }}}},
        }}),
        lambda doc, v: doc.update({"kind": "on", "mode": "deep", "level": v}),
    ),
}


def placed(location, definition):
    model = base_model()
    LOCATIONS[location][0](model, copy.deepcopy(definition))
    return model


def document_with(location, value):
    document = base_document()
    LOCATIONS[location][1](document, value)
    return document


def accepts(validator, instance):
    validator.validate(instance)


def rejects(validator, instance):
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(instance)


# --- W14-a/b/d/e: strict membership at every legal scalar leaf --------------


@pytest.mark.parametrize("location", sorted(LOCATIONS))
@pytest.mark.parametrize("dialect", DIALECTS)
@pytest.mark.parametrize("strict", [None, True])
def test_strict_scalar_enum_restricts_every_scalar_leaf(location, dialect, strict):
    definition = dict(QOS) if strict is None else {**QOS, "strict": strict}
    validator = generated_validator(placed(location, definition), dialect)
    for member in MEMBERS:
        accepts(validator, document_with(location, member))
    for value in NON_MEMBERS:
        rejects(validator, document_with(location, value))


@pytest.mark.parametrize("location", sorted(LOCATIONS))
@pytest.mark.parametrize("dialect", DIALECTS)
def test_wrong_typed_values_stay_invalid_under_a_strict_enum(location, dialect):
    validator = generated_validator(placed(location, QOS), dialect)
    for value in WRONG_TYPES:
        rejects(validator, document_with(location, value))


@pytest.mark.parametrize("location", sorted(LOCATIONS))
@pytest.mark.parametrize("dialect", DIALECTS)
@pytest.mark.parametrize("definition", [
    {"type": "uinteger", "enum": [0, 1, 2], "strict": False},
    {"type": "uinteger", "enum": []},
    {"type": "uinteger"},
], ids=["advisory", "empty", "absent"])
def test_advisory_empty_and_absent_enums_admit_any_valid_scalar(
    location, dialect, definition
):
    validator = generated_validator(placed(location, definition), dialect)
    for value in MEMBERS + [3]:
        accepts(validator, document_with(location, value))
    rejects(validator, document_with(location, "3"))


@pytest.mark.parametrize("dialect", DIALECTS)
def test_boolean_and_string_enums_keep_their_own_scalar_types(dialect):
    validator = generated_validator(
        placed("registry", {"type": "boolean", "enum": [True]}), dialect)
    accepts(validator, document_with("registry", True))
    rejects(validator, document_with("registry", False))
    rejects(validator, document_with("registry", "true"))
    rejects(validator, document_with("registry", 1))

    validator = generated_validator(
        placed("registry", {"type": "string", "enum": ["alpha"]}), dialect)
    accepts(validator, document_with("registry", "alpha"))
    rejects(validator, document_with("registry", "ALPHA"))
    rejects(validator, document_with("registry", "other"))


@pytest.mark.parametrize("dialect", DIALECTS)
def test_inactive_wildcard_fallback_and_declared_names_keep_their_own_rules(dialect):
    definition = base_model()
    definition["attributes"]["box"] = {"type": "object", "attributes": {
        "level": {"type": "uinteger", "enum": [0, 1, 2]},
        "*": {"name": "*", "type": "string", "enum": ["alpha"]},
    }}
    validator = generated_validator(definition, dialect)
    document = base_document()
    document["box"] = {"level": 2, "other": "alpha"}
    accepts(validator, document)
    document["box"] = {"level": 2, "other": "beta"}
    rejects(validator, document)
    document["box"] = {"level": 3, "other": "alpha"}
    rejects(validator, document)


# --- W14-c: the real Endpoint MQTT QoS leaves ------------------------------


def endpoint_model():
    source = json.loads((ROOT / "endpoint" / "model.json").read_text(encoding="utf-8"))
    return GENERATOR.resolve_imports(str(ROOT / "endpoint"), source)


def endpoint_document(protocol, qos):
    return {
        "registryid": "r", "specversion": "1.0", "self": "https://example.com/",
        "xid": "/", "epoch": 1, "createdat": STAMP, "modifiedat": STAMP,
        "endpoints": {"e": {
            "endpointid": "e", "protocol": protocol,
            "protocoloptions": {"qos": qos},
        }},
    }


@pytest.mark.parametrize("protocol", ["MQTT/5.0", "MQTT/3.1.1"])
def test_real_endpoint_mqtt_qos_admits_zero_to_two_and_rejects_three(protocol):
    validator = generated_validator(endpoint_model(), "json-schema")
    for value in MEMBERS:
        accepts(validator, endpoint_document(protocol, value))
    for value in [3, "1", True]:
        rejects(validator, endpoint_document(protocol, value))


def _qos_leaves(node, path=()):
    if isinstance(node, dict):
        if path and path[-1] == "qos":
            yield node
        for key, value in node.items():
            yield from _qos_leaves(value, path + (key,))
    elif isinstance(node, list):
        for value in node:
            yield from _qos_leaves(value, path)


@pytest.mark.parametrize("dialect", DIALECTS)
def test_generated_endpoint_qos_leaves_enforce_the_source_value_set(dialect):
    """Endpoint declares its MQTT QoS as `uinteger` with `enum [0,1,2]`; the
    Message model declares a plain unconstrained `integer` QoS. Only the former
    may gain a value set."""
    if dialect == "json-schema":
        output = GENERATOR.generate_json_schema(endpoint_model())
    else:
        output = GENERATOR.generate_openapi(endpoint_model())
    constrained = [leaf for leaf in _qos_leaves(output) if leaf.get("minimum") == 0]
    unconstrained = [leaf for leaf in _qos_leaves(output) if "minimum" not in leaf]
    assert constrained, f"no Endpoint qos leaf in the generated {dialect} output"
    assert unconstrained, f"no Message qos leaf in the generated {dialect} output"
    for leaf in unconstrained:
        assert "enum" not in leaf, leaf
    for leaf in constrained:
        assert "enum" in leaf, leaf
        assert [value for value in leaf["enum"] if value is not None] == [0, 1, 2]
        checker = jsonschema.Draft7Validator(
            {key: value for key, value in leaf.items() if key != "nullable"}
        )
        for value in MEMBERS:
            checker.validate(value)
        for value in (3, "1", True):
            with pytest.raises(jsonschema.ValidationError):
                checker.validate(value)


# --- W14-f: selector activation versus enum membership ----------------------


def selector_model(enum=None, strict=None):
    definition = {"type": "string", "ifvalues": {
        "alpha": {"siblingattributes": {"detail": {"type": "string"}}},
    }}
    if enum is not None:
        definition["enum"] = enum
    if strict is not None:
        definition["strict"] = strict
    model = base_model()
    model["attributes"]["kind"] = definition
    return model


@pytest.mark.parametrize("dialect", DIALECTS)
def test_selector_activation_stays_case_insensitive_without_a_strict_enum(dialect):
    validator = generated_validator(selector_model(), dialect)
    document = base_document()
    document.update({"kind": "ALPHA", "detail": "on"})
    accepts(validator, document)
    document.update({"kind": "ALPHAX", "detail": "on"})
    rejects(validator, document)


@pytest.mark.parametrize("dialect", DIALECTS)
def test_case_insensitive_selection_does_not_legalize_a_non_member(dialect):
    validator = generated_validator(selector_model(enum=["alpha"]), dialect)
    document = base_document()
    document.update({"kind": "alpha", "detail": "on"})
    accepts(validator, document)
    for value in ("ALPHA", "other"):
        document.update({"kind": value, "detail": "on"})
        rejects(validator, document)


@pytest.mark.parametrize("dialect", DIALECTS)
def test_an_advisory_enum_leaves_case_insensitive_selection_intact(dialect):
    validator = generated_validator(
        selector_model(enum=["alpha"], strict=False), dialect)
    document = base_document()
    document.update({"kind": "ALPHA", "detail": "on"})
    accepts(validator, document)


def test_a_selector_outside_an_effective_strict_enum_is_an_invalid_source_model():
    model = selector_model(enum=["beta"])
    SOURCE.validate(model)
    with pytest.raises(ValueError, match="ifvalues"):
        GENERATOR.generate_json_schema(copy.deepcopy(model))


def test_a_selector_outside_an_advisory_enum_remains_legal():
    GENERATOR.generate_json_schema(selector_model(enum=["beta"], strict=False))
    GENERATOR.generate_json_schema(selector_model(enum=[]))


def test_selector_membership_is_matched_case_insensitively():
    GENERATOR.generate_json_schema(selector_model(enum=["ALPHA"]))


# --- W14-g: defaults, request roles, resets and ignored input ---------------


def role_model(level, required=True, readonly=False):
    definition = {**level, "required": required}
    if readonly:
        definition["readonly"] = True
    model = base_model()
    model["attributes"]["level"] = definition
    return model


def openapi_validators(model):
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


def request_validator(model, method="put"):
    openapi, build = openapi_validators(model)
    return build(openapi["paths"]["/"][method]["requestBody"]["content"][
        "application/json"]["schema"], read=False)


def response_validator(model, method="get"):
    openapi, build = openapi_validators(model)
    return build(openapi["paths"]["/"][method]["responses"]["200"]["content"][
        "application/json"]["schema"], read=True)


def test_a_model_default_must_belong_to_its_effective_strict_enum():
    GENERATOR.generate_json_schema(role_model({**QOS, "default": 0}))
    with pytest.raises(ValueError, match="default"):
        GENERATOR.generate_json_schema(role_model({**QOS, "default": 3}))


def test_advisory_and_empty_enums_do_not_restrict_a_model_default():
    GENERATOR.generate_json_schema(
        role_model({**QOS, "strict": False, "default": 3}))
    GENERATOR.generate_json_schema(
        role_model({"type": "uinteger", "enum": [], "default": 3}))


def test_requests_may_omit_or_reset_a_defaulted_enum_field():
    checker = request_validator(role_model({**QOS, "default": 0}))
    checker.validate(registry_body())
    checker.validate(registry_body(level=None))
    checker.validate(registry_body(level=2))
    with pytest.raises(jsonschema.ValidationError):
        checker.validate(registry_body(level=3))


def test_nullable_alone_does_not_override_enum_membership():
    checker = request_validator(role_model(QOS, required=False))
    checker.validate(registry_body(level=None))
    checker.validate(registry_body(level=1))
    with pytest.raises(jsonschema.ValidationError):
        checker.validate(registry_body(level=3))
    with pytest.raises(jsonschema.ValidationError):
        checker.validate(registry_body(level="1"))


def test_read_only_request_values_remain_ignored_rather_than_enum_checked():
    checker = request_validator(role_model(QOS, readonly=True))
    checker.validate(registry_body(level=3))
    checker.validate(registry_body(level="anything"))


def test_completed_responses_still_require_a_member_of_the_effective_enum():
    checker = response_validator(role_model({**QOS, "default": 0}))
    checker.validate(registry_body(level=0))
    with pytest.raises(jsonschema.ValidationError):
        checker.validate(registry_body(level=3))
    with pytest.raises(jsonschema.ValidationError):
        checker.validate(registry_body())


def test_conditional_request_copies_keep_the_enum_on_both_branches():
    model = base_model()
    model["attributes"]["kind"] = {"type": "string", "ifvalues": {
        "on": {"siblingattributes": {"level": copy.deepcopy(QOS)}},
    }}
    checker = request_validator(model, method="patch")
    checker.validate(registry_body(kind="on", level=2))
    checker.validate(registry_body())
    with pytest.raises(jsonschema.ValidationError):
        checker.validate(registry_body(kind="on", level=3))


# --- W14-h: statically resolvable Group constraint overlays -----------------


def constrained_model(base, constraint, extra_groups=None):
    model = {"groups": {"catalogs": {
        "singular": "catalog",
        "constraints": {"entries.level": constraint} if constraint else {},
        "resources": {"entries": {
            "singular": "entry", "hasdocument": False, "maxversions": 0,
            "attributes": {"level": copy.deepcopy(base)},
        }},
    }}}
    if not constraint:
        del model["groups"]["catalogs"]["constraints"]
    model["groups"].update(copy.deepcopy(extra_groups or {}))
    return model


def constrained_document(value, group_plural="catalogs", singular="catalog",
                         resource_plural="entries"):
    return {
        "registryid": "r", "specversion": "1.0", "self": "https://example.com/",
        "xid": "/", "epoch": 1, "createdat": STAMP, "modifiedat": STAMP,
        group_plural: {"g": {
            f"{singular}id": "g",
            resource_plural: {"e": {
                "entryid": "e", "level": value,
                "versionsurl": "https://example.com/versions",
            }},
        }},
    }


@pytest.mark.parametrize("dialect", DIALECTS)
def test_a_group_constraint_narrows_a_strict_base_enum(dialect):
    validator = generated_validator(
        constrained_model(QOS, {"enum": [1, 2]}), dialect)
    accepts(validator, constrained_document(1))
    accepts(validator, constrained_document(2))
    rejects(validator, constrained_document(0))


@pytest.mark.parametrize("dialect", DIALECTS)
def test_a_group_constraint_restricts_an_advisory_base(dialect):
    validator = generated_validator(
        constrained_model({**QOS, "strict": False}, {"enum": [1]}), dialect)
    accepts(validator, constrained_document(1))
    rejects(validator, constrained_document(2))


@pytest.mark.parametrize("dialect", DIALECTS)
def test_an_empty_constraint_enum_adds_no_restriction(dialect):
    validator = generated_validator(
        constrained_model({**QOS, "strict": False}, {"enum": []}), dialect)
    accepts(validator, constrained_document(3))


@pytest.mark.parametrize("dialect", DIALECTS)
def test_group_constraints_also_reach_the_version_definition(dialect):
    validator = generated_validator(
        constrained_model(QOS, {"enum": [1, 2]}), dialect)
    document = constrained_document(1)
    entry = document["catalogs"]["g"]["entries"]["e"]
    del entry["versionsurl"]
    entry["versions"] = {"v1": {"entryid": "e", "versionid": "v1", "level": 1}}
    accepts(validator, document)
    entry["versions"]["v1"]["level"] = 0
    rejects(validator, document)


@pytest.mark.parametrize("dialect", DIALECTS)
def test_a_group_constraint_reaches_a_nested_static_object_path(dialect):
    model = {"groups": {"catalogs": {
        "singular": "catalog",
        "constraints": {"entries.box.level": {"enum": [1]}},
        "resources": {"entries": {
            "singular": "entry", "hasdocument": False, "maxversions": 1,
            "attributes": {"box": _object_carrier(copy.deepcopy(QOS))},
        }},
    }}}
    validator = generated_validator(model, dialect)
    document = constrained_document(None)
    document["catalogs"]["g"]["entries"]["e"] = {
        "entryid": "e", "box": {"level": 1}}
    accepts(validator, document)
    document["catalogs"]["g"]["entries"]["e"]["box"]["level"] = 2
    rejects(validator, document)


IMPORTERS = {
    "mirrors": {"singular": "mirror", "ximportresources": ["/catalogs/entries"],
                "constraints": {"entries.level": {"enum": [1]}}},
    "clones": {"singular": "clone", "ximportresources": ["/catalogs/entries"]},
}


@pytest.mark.parametrize("dialect", DIALECTS)
def test_an_imported_resource_keeps_each_group_s_own_constraints(dialect):
    model = constrained_model(QOS, None, extra_groups=IMPORTERS)
    validator = generated_validator(model, dialect)
    accepts(validator, constrained_document(1, "mirrors", "mirror"))
    rejects(validator, constrained_document(2, "mirrors", "mirror"))
    accepts(validator, constrained_document(2, "clones", "clone"))
    accepts(validator, constrained_document(2))


def test_projecting_group_constraints_does_not_mutate_the_shared_definition():
    model = constrained_model(QOS, None, extra_groups=IMPORTERS)
    before = copy.deepcopy(model)
    GENERATOR.generate_json_schema(model)
    assert model == before


@pytest.mark.parametrize("constraint,message", [
    ({"enum": [3]}, "subset"),
    ({"enum": ["1"]}, "type"),
    ({"enum": [1, 2]}, "default"),
    ({"default": 3}, "default"),
], ids=["widening", "wrong-type", "incompatible-default", "non-member-default"])
def test_invalid_group_constraints_are_rejected(constraint, message):
    model = constrained_model({**QOS, "default": 0, "required": True}, constraint)
    with pytest.raises(ValueError, match=message):
        GENERATOR.generate_json_schema(model)


def test_a_constraint_default_may_legally_override_the_model_default():
    model = constrained_model({**QOS, "default": 0, "required": True},
                              {"enum": [1, 2], "default": 1})
    openapi = GENERATOR.generate_openapi(copy.deepcopy(model))
    level = openapi["components"]["schemas"]["entry"]["properties"]["level"]
    assert level["default"] == 1
    assert level["enum"] == [1, 2]


@pytest.mark.parametrize("path,attributes", [
    ("entries.bag.level", {"bag": {"type": "map", "item": _object_carrier(dict(QOS))}}),
    ("entries.bag.level", {"bag": {"type": "array", "item": _object_carrier(dict(QOS))}}),
    ("entries.box", {"box": _object_carrier(dict(QOS))}),
    ("entries.missing", {"level": dict(QOS)}),
    ("entries.kind.level", {"kind": {"type": "string", "ifvalues": {
        "on": {"siblingattributes": {"level": dict(QOS)}}}}}),
], ids=["map", "array", "object-leaf", "unknown", "conditional"])
def test_constraints_reject_non_static_or_non_scalar_targets(path, attributes):
    model = {"groups": {"catalogs": {
        "singular": "catalog",
        "constraints": {path: {"enum": [1]}},
        "resources": {"entries": {
            "singular": "entry", "hasdocument": False, "maxversions": 1,
            "attributes": copy.deepcopy(attributes),
        }},
    }}}
    with pytest.raises(ValueError):
        GENERATOR.generate_json_schema(model)


def test_constraints_reject_a_wildcard_target():
    model = {"groups": {"catalogs": {
        "singular": "catalog",
        "constraints": {"entries.*": {"enum": [1]}},
        "resources": {"entries": {
            "singular": "entry", "hasdocument": False, "maxversions": 1,
            "attributes": {"*": {"name": "*", "type": "uinteger"}},
        }},
    }}}
    with pytest.raises(ValueError):
        GENERATOR.generate_json_schema(model)


def test_constraints_reject_an_unknown_resource_plural():
    model = {"groups": {"catalogs": {
        "singular": "catalog",
        "constraints": {"absent.level": {"enum": [1]}},
        "resources": {"entries": {
            "singular": "entry", "hasdocument": False, "maxversions": 1,
            "attributes": {"level": dict(QOS)},
        }},
    }}}
    with pytest.raises(ValueError):
        GENERATOR.generate_json_schema(model)


@pytest.mark.parametrize("dialect", DIALECTS)
def test_a_dynamic_equals_constraint_adds_no_static_restriction(dialect):
    """`equals` compares runtime Group and Resource values, which ordinary JSON
    Schema cannot express; it is deliberately left unqualified here."""
    model = constrained_model({"type": "string"}, {"equals": "kind"})
    model["groups"]["catalogs"]["attributes"] = {"kind": {"type": "string"}}
    validator = generated_validator(model, dialect)
    document = constrained_document("anything")
    document["catalogs"]["g"]["kind"] = "other"
    accepts(validator, document)


def test_the_real_schema_registry_model_keeps_its_equals_constraint_unprojected():
    source = json.loads((ROOT / "schema" / "model.json").read_text(encoding="utf-8"))
    model = GENERATOR.resolve_imports(str(ROOT / "schema"), source)
    schema = GENERATOR.generate_json_schema(copy.deepcopy(model))
    definition = schema["definitions"]["schemagroup-schema"]["schema"]
    assert "enum" not in definition["properties"]["format"]


# --- W14-i/j: array plumbing and the JSON Structure adapter are unchanged ---


def test_array_level_enum_keeps_its_existing_item_projection():
    """Removing this legacy delegation depends on the source cleanup owned by
    the model-consistency work; `endpoint/model.json` still declares one."""
    model = base_model()
    model["attributes"]["usage"] = {
        "type": "array", "enum": ["a", "b"], "item": {"type": "string"},
    }
    schema = GENERATOR.generate_json_schema(model)
    assert schema["properties"]["usage"]["items"]["enum"] == ["a", "b"]
    assert "enum" not in schema["properties"]["usage"]


def test_item_level_enums_are_admitted_only_for_approved_scalar_item_kinds():
    """The reviewed Endpoint directive added a scalar `item.enum`; an `enum` on
    a container item stays invalid. `test_schema_generator_item_enums.py` owns
    the projection of the admitted form."""
    model = base_model()
    model["attributes"]["usage"] = {
        "type": "array", "item": {"type": "string", "enum": ["a"]},
    }
    SOURCE.validate(model)
    nested = base_model()
    nested["attributes"]["usage"] = {
        "type": "array",
        "item": {"type": "map", "enum": ["a"], "item": {"type": "string"}},
    }
    with pytest.raises(jsonschema.ValidationError):
        SOURCE.validate(nested)


def test_json_structure_scalar_enum_annotation_is_unchanged():
    model = base_model()
    model["groups"]["catalogs"]["attributes"]["level"] = copy.deepcopy(QOS)
    structure = GENERATOR.generate_json_structure(model, schema_name="Doc")
    catalog = structure["definitions"]["Catalogs"]["Catalog"]
    assert catalog["properties"]["level"]["enum"] == [0, 1, 2]
