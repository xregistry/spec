"""Schema generator and OpenAPI projection tests.

Merged from the per-topic modules this change first added, so this work
contributes one test module to the tools directory. The sections are
independent; each keeps the fixtures and helpers it needs.

Contents:
  * Model source schema and validation stages
  * Local model includes ($include and $includes)
  * Conditional selector matching (ifvalues)
  * Scalar attribute value sets (enum and strict)
  * Scalar item value sets (item.enum and item.strict)
  * Generated request and response closure
  * JSON Structure dynamic object projection
  * Typed wildcards on named JSON Structure objects
  * OpenAPI request roles and Resource Meta schemas
  * OpenAPI administration surface
  * OpenAPI flag and guard parameters
  * OpenAPI problem details responses
"""

import avro.io
import avro.schema
import copy
import importlib.util
import io
import itertools
import json
import jsonschema
import pytest
import subprocess
import sys

from jsonpointer import resolve_pointer
from openapi_schema_validator import OAS30ReadValidator, OAS30Validator, OAS30WriteValidator
from openapi_schema_validator import OAS30ReadValidator, OAS30WriteValidator
from openapi_spec_validator import OpenAPIV30SpecValidator, validate
from openapi_spec_validator import OpenAPIV30SpecValidator, validate_spec
from openapi_spec_validator import validate
from openapi_spec_validator import validate_spec
from pathlib import Path


# ------------------------------------------------------------------------
# Shared locations, generator module and fixtures
# ------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "schema_generator", ROOT / "tools" / "schema-generator.py"
)
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)


def _load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATE_MODELS = _load("validate_models", "tools/validate-models.py")


MODEL_SCHEMA = json.loads((ROOT / "core" / "model.schema.json").read_text(encoding="utf-8"))


EXPANDED = VALIDATE_MODELS.expanded_validator(MODEL_SCHEMA)


STAMP = "2026-01-01T00:00:00Z"


DIALECTS = ["json-schema", "openapi"]


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


def endpoint_model():
    source = json.loads((ROOT / "endpoint" / "model.json").read_text(encoding="utf-8"))
    return GENERATOR.resolve_imports(str(ROOT / "endpoint"), source)


def registry_body(**extra):
    body = {"registryid": "r", "specversion": "1.0", "self": "https://example.com/",
            "xid": "/", "epoch": 1, "createdat": STAMP, "modifiedat": STAMP}
    body.update(extra)
    return body


MODELS = {
    "schema": ("schema",),
    "message": ("message",),
    "endpoint": ("endpoint",),
    "cloudevents": ("endpoint", "message", "schema"),
}


# ========================================================================
# Model source schema and validation stages
# Originally tools/test_model_schema_source.py
# Renamed to keep this section's bindings distinct: SOURCE -> source_SOURCE, accepts -> source_accepts, model -> source_model, rejects -> source_rejects
# ========================================================================

source_SOURCE = VALIDATE_MODELS.source_validator(MODEL_SCHEMA)


STRICT_MAX = "a" * 63


EXTENDED_NAMES = ("x-name", "9.name", "a:b", "a.b-c_d")


def source_accepts(instance, validator=source_SOURCE):
    before = copy.deepcopy(instance)
    validator.validate(instance)
    assert instance == before


def source_rejects(instance, validator=source_SOURCE):
    before = copy.deepcopy(instance)
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(instance)
    assert instance == before


def source_model(**extra):
    definition = {
        "groups": {
            "catalogs": {
                "singular": "catalog",
                "resources": {"entries": {"singular": "entry"}},
            }
        }
    }
    definition.update(extra)
    return definition


def with_attribute(definition, name="payload"):
    return source_model(attributes={name: definition})


def group_of(model_definition):
    return model_definition["groups"]["catalogs"]


def resource_of(model_definition):
    return group_of(model_definition)["resources"]["entries"]


INCLUDE_POSITIONS = {
    "root": lambda d: d,
    "groups-map": lambda d: d["groups"],
    "group-definition": lambda d: group_of(d),
    "group-attributes": lambda d: group_of(d).setdefault("attributes", {}),
    "group-labels": lambda d: group_of(d).setdefault("labels", {}),
    "group-constraints": lambda d: group_of(d).setdefault("constraints", {}),
    "group-constraint-entry": lambda d: group_of(d).setdefault(
        "constraints", {}).setdefault("entries.payload", {}),
    "resources-map": lambda d: group_of(d)["resources"],
    "resource-definition": lambda d: resource_of(d),
    "resource-typemap": lambda d: resource_of(d).setdefault("typemap", {}),
    "resource-metaattributes": lambda d: resource_of(d).setdefault(
        "metaattributes", {}),
    "root-attributes": lambda d: d.setdefault("attributes", {}),
    "attribute-definition": lambda d: d.setdefault(
        "attributes", {}).setdefault("payload", {"type": "string"}),
    "attribute-nested-attributes": lambda d: d.setdefault(
        "attributes", {}).setdefault(
            "payload", {"type": "object", "attributes": {}})["attributes"],
    "item-definition": lambda d: d.setdefault("attributes", {}).setdefault(
        "payload", {"type": "array", "item": {"type": "string"}})["item"],
    "item-attributes": lambda d: d.setdefault("attributes", {}).setdefault(
        "payload", {"type": "array", "item": {
            "type": "object", "attributes": {}}})["item"]["attributes"],
    "ifvalues-map": lambda d: d.setdefault("attributes", {}).setdefault(
        "payload", {"type": "string", "ifvalues": {}})["ifvalues"],
    "ifvalues-branch": lambda d: d.setdefault("attributes", {}).setdefault(
        "payload", {"type": "string", "ifvalues": {"one": {}}},
    )["ifvalues"]["one"],
    "ifvalues-siblings": lambda d: d.setdefault("attributes", {}).setdefault(
        "payload", {"type": "string", "ifvalues": {
            "one": {"siblingattributes": {}}}},
    )["ifvalues"]["one"]["siblingattributes"],
    "labels": lambda d: d.setdefault("labels", {}),
}


@pytest.mark.parametrize("position", sorted(INCLUDE_POSITIONS))
def test_single_include_directive_is_admitted_at_every_model_object_or_map(position):
    definition = source_model()
    INCLUDE_POSITIONS[position](definition)["$include"] = "other.json#/attributes"
    source_accepts(definition)


@pytest.mark.parametrize("position", sorted(INCLUDE_POSITIONS))
def test_ordered_includes_directive_is_admitted_at_every_model_object_or_map(position):
    definition = source_model()
    INCLUDE_POSITIONS[position](definition)["$includes"] = ["a.json", "b.json#/x"]
    source_accepts(definition)


@pytest.mark.parametrize("position", sorted(INCLUDE_POSITIONS))
def test_both_include_directives_at_one_level_are_rejected(position):
    definition = source_model()
    target = INCLUDE_POSITIONS[position](definition)
    target["$include"] = "a.json"
    target["$includes"] = ["b.json"]
    source_rejects(definition)


@pytest.mark.parametrize("position", sorted(INCLUDE_POSITIONS))
def test_include_directive_reference_shape_is_typed(position):
    for bad in ({"$include": ["a.json"]}, {"$includes": "a.json"},
                {"$includes": [7]}):
        definition = source_model()
        INCLUDE_POSITIONS[position](definition).update(copy.deepcopy(bad))
        source_rejects(definition)


def test_group_include_admits_local_sibling_members():
    definition = source_model()
    group_of(definition).update({"$include": "g.json", "description": "local"})
    source_accepts(definition)


def test_resource_include_admits_local_sibling_members():
    definition = source_model()
    resource_of(definition).update({"$include": "r.json", "maxversions": 3})
    source_accepts(definition)


def test_attribute_map_include_admits_local_sibling_definitions():
    definition = source_model(attributes={
        "$include": "attrs.json", "local": {"type": "string"},
    })
    source_accepts(definition)


def test_include_only_group_and_resource_definitions_need_no_local_singular():
    source_accepts(source_model(groups={"catalogs": {"$include": "g.json"}}))
    definition = source_model()
    group_of(definition)["resources"] = {"entries": {"$includes": ["r.json"]}}
    source_accepts(definition)


def test_group_and_resource_definitions_without_includes_still_need_singular():
    source_rejects(source_model(groups={"catalogs": {"description": "no singular"}}))
    definition = source_model()
    group_of(definition)["resources"] = {"entries": {"description": "x"}}
    source_rejects(definition)


def test_expansion_reuses_the_real_resolver_precedence_and_local_overrides(tmp_path):
    (tmp_path / "attrs.json").write_text(json.dumps({
        "shared": {"type": "integer"}, "only": {"type": "boolean"},
    }), encoding="utf-8")
    source = {"attributes": {
        "$include": "attrs.json",
        "shared": {"type": "string"},
    }}
    expanded = VALIDATE_MODELS.expand_model(tmp_path / "model.json", source)
    assert expanded["attributes"]["shared"] == {"type": "string"}
    assert expanded["attributes"]["only"] == {"type": "boolean"}
    assert "$include" not in expanded["attributes"]
    assert source["attributes"]["$include"] == "attrs.json"


def test_expansion_rejects_network_references(tmp_path):
    source = {"attributes": {"$include": "https://example.com/attrs.json"}}
    with pytest.raises(ValueError):
        VALIDATE_MODELS.expand_model(tmp_path / "model.json", source)


def test_source_admits_a_partial_overlay_of_a_specification_defined_attribute():
    source_accepts(with_attribute({"required": True}, name="name"))
    source_accepts(with_attribute({"description": "further constrained"}, name="self"))


def test_expanded_stage_rejects_a_definition_that_never_received_a_type():
    definition = with_attribute({"required": True}, name="name")
    source_accepts(definition)
    source_rejects(definition, EXPANDED)


def test_expanded_stage_rejects_unresolved_include_directives():
    definition = source_model(attributes={"$include": "attrs.json"})
    source_accepts(definition)
    source_rejects(definition, EXPANDED)


def test_expanded_stage_accepts_completed_definitions():
    source_accepts(with_attribute({"type": "string"}), EXPANDED)
    source_accepts(source_model(attributes={"*": {"type": "any"}}), EXPANDED)


def test_expanded_stage_requires_a_type_on_wildcards_and_nested_definitions():
    source_rejects(source_model(attributes={"*": {"description": "x"}}), EXPANDED)
    source_rejects(with_attribute({
        "type": "object", "attributes": {"inner": {"required": True}},
    }), EXPANDED)
    source_rejects(with_attribute({
        "type": "string", "ifvalues": {"a": {"siblingattributes": {
            "inner": {"description": "x"}}}},
    }), EXPANDED)
    source_rejects(with_attribute({"type": "array", "item": {"target": "/catalogs"}}), EXPANDED)


def test_validator_reports_each_stage_it_actually_performed(tmp_path):
    path = tmp_path / "model.json"
    path.write_text(json.dumps(with_attribute({"type": "string"})), encoding="utf-8")
    report = VALIDATE_MODELS.validate_model(path, MODEL_SCHEMA)
    assert report.errors == []
    assert report.stages == [
        VALIDATE_MODELS.SOURCE_STAGE, VALIDATE_MODELS.EXPANDED_STAGE,
    ]
    assert VALIDATE_MODELS.SEMANTIC_STAGE not in report.stages
    assert VALIDATE_MODELS.SEMANTIC_STAGE in report.unverified[0]


def test_validator_attributes_an_overlay_failure_to_the_expanded_stage(tmp_path):
    path = tmp_path / "model.json"
    path.write_text(json.dumps(with_attribute({"required": True}, name="name")),
                    encoding="utf-8")
    report = VALIDATE_MODELS.validate_model(path, MODEL_SCHEMA)
    assert report.errors
    assert all(VALIDATE_MODELS.EXPANDED_STAGE in error for error in report.errors)
    assert not any(VALIDATE_MODELS.SOURCE_STAGE in error for error in report.errors)


def test_validator_attributes_a_structural_failure_to_the_source_stage(tmp_path):
    path = tmp_path / "model.json"
    path.write_text(json.dumps(with_attribute({"type": "binary"})), encoding="utf-8")
    report = VALIDATE_MODELS.validate_model(path, MODEL_SCHEMA)
    assert report.errors
    assert any(VALIDATE_MODELS.SOURCE_STAGE in error for error in report.errors)


def test_repository_models_pass_the_source_structural_stage():
    failures = []
    for path in sorted(ROOT.rglob("model.json")):
        report = VALIDATE_MODELS.validate_model(path, MODEL_SCHEMA)
        failures.extend(
            error for error in report.errors
            if VALIDATE_MODELS.SOURCE_STAGE in error
        )
    assert failures == []


def test_expanded_stage_blocks_only_on_the_recorded_include_pointer_prerequisite():
    """cloudevents/model.json still carries the three malformed `#groups`
    fragments. Repairing them is W08, owned by the model-consistency follow-up
    on xregistry/spec#723, so this branch records the prerequisite instead of
    weakening the expanded stage. This assertion fails loudly once that
    dependency lands, which is the intended signal to tighten it."""
    blocked = {}
    for path in sorted(ROOT.rglob("model.json")):
        report = VALIDATE_MODELS.validate_model(path, MODEL_SCHEMA)
        errors = [
            error for error in report.errors
            if VALIDATE_MODELS.EXPANDED_STAGE in error
        ]
        if errors:
            blocked[path.relative_to(ROOT).as_posix()] = errors
    assert sorted(blocked) == ["cloudevents/model.json"]
    assert all(
        "Invalid include pointer" in error
        for error in blocked["cloudevents/model.json"]
    )


@pytest.mark.parametrize("name", ["a", "_private", "a_b_9", STRICT_MAX])
def test_strict_attribute_names_admit_letters_underscores_and_digits(name):
    source_accepts(source_model(attributes={name: {"type": "string"}}))
    source_accepts(source_model(attributes={name: {"type": "string", "name": name}}))


@pytest.mark.parametrize("name", ["1bad", "with-dash", "UPPER", "a" * 64, "a:b", "a.b"])
def test_strict_attribute_names_reject_digit_starts_punctuation_and_overlong(name):
    source_rejects(source_model(attributes={name: {"type": "string"}}))


@pytest.mark.parametrize("name", ["1bad", "with-dash", "a" * 64])
def test_explicitly_supplied_strict_names_are_bounded_like_their_keys(name):
    source_rejects(source_model(attributes={"payload": {"type": "string", "name": name}}))


@pytest.mark.parametrize("name", EXTENDED_NAMES)
def test_extended_names_are_admitted_only_under_an_extended_object(name):
    source_accepts(with_attribute({
        "type": "object", "namecharset": "extended",
        "attributes": {name: {"type": "string", "name": name}},
    }))
    source_rejects(source_model(attributes={name: {"type": "string"}}))


@pytest.mark.parametrize("charset", ["extended", "EXTENDED", "Extended"])
def test_extended_charset_selection_is_case_insensitive(charset):
    source_accepts(with_attribute({
        "type": "object", "namecharset": charset,
        "attributes": {"x-name": {"type": "string"}},
    }))


def test_extended_scope_does_not_leak_into_a_nested_strict_object():
    source_accepts(with_attribute({
        "type": "object", "namecharset": "extended",
        "attributes": {"x-name": {"type": "object", "attributes": {
            "inner": {"type": "string"}}}},
    }))
    source_rejects(with_attribute({
        "type": "object", "namecharset": "extended",
        "attributes": {"x-name": {"type": "object", "attributes": {
            "in-ner": {"type": "string"}}}},
    }))


def test_conditional_siblings_follow_the_charset_of_their_own_object():
    source_rejects(with_attribute({
        "type": "string",
        "ifvalues": {"a": {"siblingattributes": {"x-name": {"type": "string"}}}},
    }))
    source_accepts(with_attribute({
        "type": "object", "namecharset": "extended",
        "attributes": {"kind": {"type": "string", "ifvalues": {
            "a": {"siblingattributes": {"x-name": {"type": "string"}}}}}},
    }))


def test_extended_item_objects_carry_their_own_charset():
    source_accepts(with_attribute({
        "type": "map",
        "item": {"type": "object", "namecharset": "extended",
                 "attributes": {"x-name": {"type": "string"}}},
    }))
    source_rejects(with_attribute({
        "type": "map",
        "item": {"type": "object", "attributes": {"x-name": {"type": "string"}}},
    }))


def test_extended_names_still_respect_the_map_key_length_and_leading_character():
    source_accepts(with_attribute({
        "type": "object", "namecharset": "extended",
        "attributes": {"a" * 63: {"type": "string"}},
    }))
    source_rejects(with_attribute({
        "type": "object", "namecharset": "extended",
        "attributes": {"a" * 64: {"type": "string"}},
    }))
    source_rejects(with_attribute({
        "type": "object", "namecharset": "extended",
        "attributes": {"-lead": {"type": "string"}},
    }))


@pytest.mark.parametrize("length,valid", [(57, True), (58, False)])
def test_group_plural_and_resource_names_are_bounded_at_57(length, valid):
    name = "a" * length
    check = source_accepts if valid else source_rejects
    check(source_model(groups={name: {"singular": "catalog"}}))
    check(source_model(groups={"catalogs": {"singular": "catalog", "plural": name}}))
    check(source_model(groups={"catalogs": {"singular": "catalog", "resources": {
        name: {"singular": "entry"}}}}))
    check(source_model(groups={"catalogs": {"singular": "catalog", "resources": {
        "entries": {"singular": name}}}}))
    check(source_model(groups={"catalogs": {"singular": "catalog", "resources": {
        "entries": {"singular": "entry", "plural": name}}}}))


@pytest.mark.parametrize("length", [61, 62, 63])
def test_group_singular_follows_current_main_law_of_63(length):
    source_accepts(source_model(groups={"catalogs": {"singular": "a" * length}}))


def test_group_singular_rejects_names_above_the_current_main_bound():
    source_rejects(source_model(groups={"catalogs": {"singular": "a" * 64}}))


def test_group_and_resource_type_names_admit_leading_underscores():
    source_accepts(source_model(groups={"_catalogs": {
        "singular": "_catalog", "resources": {"_entries": {"singular": "_entry"}},
    }}))
    source_rejects(source_model(groups={"9catalogs": {"singular": "catalog"}}))


VALID_TARGETS = [
    "/catalogs", "/_groups", "/_groups/_resources", "/_groups/_resources/versions",
    "/group_a/resource_b", "/group_a/resource_b[/versions]",
    "/group_a/resource_b/versions",
]


INVALID_TARGETS = [
    "catalogs", "/9groups", "/groups/9resources", "/groups/resources/version",
    "/groups/resources[/version]", "/groups/resources/versions/extra",
    "/" + "a" * 58, "/groups/" + "a" * 58, "/groups/resources[/versions]/x",
]


@pytest.mark.parametrize("target", VALID_TARGETS)
def test_targets_admit_nested_underscores_at_every_depth(target):
    source_accepts(with_attribute({"type": "xid", "target": target}))
    source_accepts(with_attribute({"type": "array", "item": {"type": "xid", "target": target}}))
    source_accepts(with_attribute({
        "type": "array",
        "item": {"type": "array", "item": {"type": "xid", "target": target}},
    }))


@pytest.mark.parametrize("target", INVALID_TARGETS)
def test_targets_reject_malformed_type_components_and_depths(target):
    source_rejects(with_attribute({"type": "xid", "target": target}))
    source_rejects(with_attribute({"type": "array", "item": {"type": "xid", "target": target}}))


@pytest.mark.parametrize("value,valid", [
    ("/_groups/_resources", True), ("/group_a/resource_b", True),
    ("/catalogs", False), ("/9groups/resources", False),
    ("/groups/resources/versions", False), ("/groups/" + "a" * 58, False),
])
def test_ximportresources_uses_the_same_plural_name_grammar(value, valid):
    definition = source_model()
    group_of(definition)["ximportresources"] = [value]
    (source_accepts if valid else source_rejects)(definition)


@pytest.mark.parametrize("key,valid", [
    ("entries.payload", True), ("_entries.payload.inner", True),
    ("9entries.payload", False), ("entries", False),
    ("a" * 58 + ".payload", False),
])
def test_group_constraint_keys_use_the_resource_plural_name_grammar(key, valid):
    definition = source_model()
    group_of(definition)["constraints"] = {key: {"equals": "kind"}}
    (source_accepts if valid else source_rejects)(definition)


def test_documentation_and_icon_are_defined_where_the_model_shape_defines_them():
    definition = source_model(description="registry", documentation="https://example.com/d")
    group_of(definition).update({
        "documentation": "https://example.com/g", "icon": "https://example.com/g.png",
    })
    resource_of(definition).update({
        "documentation": "https://example.com/r", "icon": "https://example.com/r.png",
    })
    source_accepts(definition)


@pytest.mark.parametrize("field", ["documentation", "icon"])
def test_documentation_and_icon_reject_non_string_values(field):
    definition = source_model()
    group_of(definition)[field] = 5
    source_rejects(definition)
    definition = source_model()
    resource_of(definition)[field] = {"url": "https://example.com"}
    source_rejects(definition)


def test_root_documentation_is_typed_and_no_root_icon_is_introduced():
    source_rejects(source_model(documentation=5))
    definition = source_model(icon="https://example.com/i.png")
    assert "icon" not in MODEL_SCHEMA["properties"]
    source_accepts(definition)


@pytest.mark.parametrize("value", ["strict", "STRICT", "Extended", "extended"])
def test_namecharset_values_are_case_insensitive(value):
    source_accepts(with_attribute({"type": "object", "namecharset": value, "attributes": {}}))


def test_namecharset_rejects_unknown_character_sets():
    source_rejects(with_attribute({"type": "object", "namecharset": "loose"}))


@pytest.mark.parametrize("value", ["manual", "MANUAL", "SemVer", "createdat", "ModifiedAt"])
def test_versionmode_values_are_case_insensitive(value):
    definition = source_model()
    resource_of(definition)["versionmode"] = value
    source_accepts(definition)


def test_versionmode_rejects_unknown_algorithms():
    definition = source_model()
    resource_of(definition)["versionmode"] = "newest"
    source_rejects(definition)


@pytest.mark.parametrize("value", ["json", "JSON", "Binary", "string", "STRING"])
def test_typemap_values_are_case_insensitive_and_keep_binary(value):
    definition = source_model()
    resource_of(definition)["typemap"] = {"Application/JSON": value}
    source_accepts(definition)


def test_typemap_rejects_unknown_serialization_kinds():
    definition = source_model()
    resource_of(definition)["typemap"] = {"application/json": "yaml"}
    source_rejects(definition)


@pytest.mark.parametrize("type_name", ["String", "STRING", "Integer"])
def test_type_names_remain_case_sensitive_lowercase(type_name):
    source_rejects(with_attribute({"type": type_name}))


def test_strict_enum_members_are_not_case_folded_by_the_source_schema():
    source_accepts(with_attribute({"type": "string", "enum": ["Alpha", "alpha"]}))


@pytest.mark.parametrize("key", ["", "^reserved"])
def test_ifvalues_keys_reject_empty_and_reserved_caret_selectors(key):
    source_rejects(with_attribute({
        "type": "string", "ifvalues": {key: {"siblingattributes": {}}},
    }))


def test_ifvalues_branches_require_sibling_attributes_unless_included():
    source_rejects(with_attribute({"type": "string", "ifvalues": {"a": {}}}))
    source_accepts(with_attribute({
        "type": "string", "ifvalues": {"a": {"$include": "b.json"}},
    }))


def test_case_duplicate_selectors_remain_a_semantic_check_not_a_source_one():
    definition = with_attribute({"type": "string", "ifvalues": {
        "http": {"siblingattributes": {}},
        "HTTP": {"siblingattributes": {}},
    }})
    source_accepts(definition)
    generator = _load("schema_generator", "tools/schema-generator.py")
    with pytest.raises(ValueError, match="Duplicate case-insensitive"):
        generator.generate_openapi(copy.deepcopy(definition))


def test_empty_constraint_enum_is_admitted():
    definition = source_model()
    group_of(definition)["constraints"] = {"entries.payload": {"enum": []}}
    source_accepts(definition)
    definition = source_model()
    group_of(definition)["constraints"] = {"entries.payload": {"enum": ["a"]}}
    source_accepts(definition)


def test_empty_scalar_attribute_enum_is_admitted():
    source_accepts(with_attribute({"type": "integer", "enum": []}))


@pytest.mark.parametrize("position", ["attribute", "item", "wildcard"])
def test_the_undefined_core_binary_type_is_rejected(position):
    cases = {
        "attribute": with_attribute({"type": "binary"}),
        "item": with_attribute({"type": "array", "item": {"type": "binary"}}),
        "wildcard": source_model(attributes={"*": {"type": "binary"}}),
    }
    source_rejects(cases[position])


def test_typemap_binary_remains_legal():
    definition = source_model()
    resource_of(definition)["typemap"] = {"application/octet-stream": "binary"}
    source_accepts(definition)


@pytest.mark.parametrize("shorthand", ["string", "anything", "object"])
def test_string_attribute_definitions_are_rejected(shorthand):
    source_rejects(source_model(attributes={"payload": shorthand}))
    source_rejects(with_attribute({
        "type": "object", "attributes": {"inner": shorthand},
    }))


def test_object_form_attribute_definitions_remain_valid():
    source_accepts(with_attribute({"type": "string"}))


# ========================================================================
# Local model includes ($include and $includes)
# Originally tools/test_schema_generator_includes_624.py
# Renamed to keep this section's bindings distinct: generator -> includes_generator
# ========================================================================

@pytest.fixture
def includes_generator():
    path = Path(__file__).with_name("schema-generator.py")
    spec = importlib.util.spec_from_file_location("schema_generator_includes_624", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_document(directory, name, value):
    path = directory / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


@pytest.mark.parametrize("multiple", [False, True])
def test_include_local_siblings_win_without_deep_merge(includes_generator, tmp_path, multiple):
    write_document(tmp_path, "base.json", {
        "singular": "included",
        "attributes": {"remote": {"type": "string"}},
        "description": "inherited",
    })
    directive = {"$includes": ["base.json"]} if multiple else {"$include": "base.json"}
    source = {
        **directive,
        "singular": "local-wins",
        "attributes": {"local": {"type": "boolean"}},
    }
    original = copy.deepcopy(source)
    result = includes_generator.resolve_imports(str(tmp_path), source)
    assert result == {
        "singular": "local-wins",
        "attributes": {"local": {"type": "boolean"}},
        "description": "inherited",
    }
    assert source == original
    assert result is not source


def test_includes_order_and_local_precedence(includes_generator, tmp_path):
    write_document(tmp_path, "first.json", {"shared": "first", "first": 1})
    write_document(tmp_path, "second.json", {"shared": "second", "second": 2})
    source = {"$includes": ["first.json", "second.json"], "first": "local"}
    assert includes_generator.resolve_imports(str(tmp_path), source) == {
        "shared": "first", "first": "local", "second": 2,
    }
    reverse = {"$includes": ["second.json", "first.json"], "first": "local"}
    assert includes_generator.resolve_imports(str(tmp_path), reverse)["shared"] == "second"


def test_nested_includes_use_the_declaring_document_base(includes_generator, tmp_path):
    write_document(tmp_path, "nested/group.json", {
        "resource": {"$include": "resources.json#/message"},
        "local": {"$include": "../common.json"},
    })
    write_document(tmp_path, "nested/resources.json", {"message": {"singular": "message"}})
    write_document(tmp_path, "resources.json", {"message": {"singular": "wrong-base"}})
    write_document(tmp_path, "common.json", {"from": "root"})
    source = {
        "$include": "nested/group.json",
        "sibling": {"$include": "common.json"},
    }
    assert includes_generator.resolve_imports(str(tmp_path), source) == {
        "resource": {"singular": "message"},
        "local": {"from": "root"},
        "sibling": {"from": "root"},
    }


def test_same_document_pointer_uses_the_included_document(includes_generator, tmp_path):
    write_document(tmp_path, "nested/source.json", {
        "definitions": {"item": {"type": "string"}},
        "selected": {"$include": "#/definitions/item"},
    })
    source = {"$include": "nested/source.json#/selected"}
    assert includes_generator.resolve_imports(str(tmp_path), source) == {"type": "string"}


def test_pointer_escapes_and_uri_fragment_decoding(includes_generator, tmp_path):
    write_document(tmp_path, "source.json", {
        "a/b": {"~key": [{"space key": {"type": "string"}}]},
    })
    source = {"$include": "source.json#/a~1b/~0key/0/space%20key"}
    assert includes_generator.resolve_imports(str(tmp_path), source) == {"type": "string"}


def test_repeated_non_cyclic_include_and_nested_input_nonmutation(includes_generator, tmp_path):
    path = write_document(tmp_path, "base.json", {"attributes": {"value": {"type": "string"}}})
    original_bytes = path.read_bytes()
    source = {"list": [{"$include": "base.json"}, {"$include": "base.json"}]}
    original = copy.deepcopy(source)
    result = includes_generator.resolve_imports(str(tmp_path), source)
    assert result == {"list": [
        {"attributes": {"value": {"type": "string"}}},
        {"attributes": {"value": {"type": "string"}}},
    ]}
    result["list"][0]["attributes"]["value"]["type"] = "boolean"
    assert result["list"][1]["attributes"]["value"]["type"] == "string"
    assert source == original
    assert path.read_bytes() == original_bytes


@pytest.mark.parametrize("source", [
    {"$include": "source.json", "$includes": []},
    {"$include": 1},
    {"$includes": "source.json"},
    {"$includes": [1]},
])
def test_invalid_include_directives_fail_explicitly(includes_generator, tmp_path, source):
    write_document(tmp_path, "source.json", {})
    original = copy.deepcopy(source)
    with pytest.raises(ValueError, match="include"):
        includes_generator.resolve_imports(str(tmp_path), source)
    assert source == original


@pytest.mark.parametrize("pointer", [
    "groups", "/missing", "/bad~2escape", "/list/-", "/bad%GG", "/bad%FF",
])
def test_bad_json_pointers_fail_without_mutation(includes_generator, tmp_path, pointer):
    write_document(tmp_path, "source.json", {"groups": {}, "list": [{}]})
    source = {"$include": f"source.json#{pointer}", "local": 1}
    original = copy.deepcopy(source)
    with pytest.raises(ValueError, match="pointer"):
        includes_generator.resolve_imports(str(tmp_path), source)
    assert source == original


@pytest.mark.parametrize("target", [[], [1], "string", 1, False, None])
def test_include_target_must_be_an_object(includes_generator, tmp_path, target):
    write_document(tmp_path, "source.json", {"target": target})
    with pytest.raises(ValueError, match="object"):
        includes_generator.resolve_imports(str(tmp_path), {"$include": "source.json#/target"})


@pytest.mark.parametrize("indirect", [False, True])
def test_include_cycles_fail_explicitly(includes_generator, tmp_path, indirect):
    write_document(tmp_path, "first.json", {
        "$include": "second.json" if indirect else "first.json",
    })
    write_document(tmp_path, "second.json", {"nested": {"$include": "first.json"}})
    with pytest.raises(ValueError, match="cycle"):
        includes_generator.resolve_imports(str(tmp_path), {"$include": "first.json"})


def test_include_depth_is_bounded(includes_generator, tmp_path):
    for index in range(66):
        write_document(tmp_path, f"{index}.json", {"$include": f"{index + 1}.json"})
    write_document(tmp_path, "66.json", {"value": "too deep"})
    with pytest.raises(ValueError, match="depth"):
        includes_generator.resolve_imports(str(tmp_path), {"$include": "0.json"})


def test_include_depth_boundary_is_admitted(includes_generator, tmp_path):
    for index in range(63):
        write_document(tmp_path, f"{index}.json", {"$include": f"{index + 1}.json"})
    write_document(tmp_path, "63.json", {"value": "within bound"})
    assert includes_generator.resolve_imports(str(tmp_path), {"$include": "0.json"}) == {
        "value": "within bound",
    }


def test_same_file_path_alias_cannot_hide_a_cycle(includes_generator, tmp_path):
    (tmp_path / "nested").mkdir()
    write_document(tmp_path, "source.json", {"$include": "nested/../source.json"})
    with pytest.raises(ValueError, match="cycle"):
        includes_generator.resolve_imports(str(tmp_path), {"$include": "source.json"})


@pytest.mark.parametrize("reference", [
    "https://example.invalid/model.json",
    "file:///remote/model.json",
    "//remote/share/model.json",
    "\\\\remote\\share\\model.json",
])
def test_includes_do_not_acquire_network_resources(includes_generator, tmp_path, reference, monkeypatch):
    def unexpected_open(*args, **kwargs):
        pytest.fail("A non-local include attempted file or network acquisition")

    monkeypatch.setattr("builtins.open", unexpected_open)
    with pytest.raises(ValueError, match="local"):
        includes_generator.resolve_imports(str(tmp_path), {"$include": reference})


def test_missing_include_is_not_silently_ignored(includes_generator, tmp_path):
    source = {"$include": "missing.json", "local": 1}
    with pytest.raises(FileNotFoundError):
        includes_generator.resolve_imports(str(tmp_path), source)
    assert source == {"$include": "missing.json", "local": 1}


def test_invalid_include_json_is_not_silently_ignored(includes_generator, tmp_path):
    (tmp_path / "invalid.json").write_text("{", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        includes_generator.resolve_imports(str(tmp_path), {"$include": "invalid.json"})


def test_empty_includes_and_scalar_leaves_are_preserved(includes_generator, tmp_path):
    source = {"$includes": [], "array": [None, False, 0, "value"], "object": {}}
    assert includes_generator.resolve_imports(str(tmp_path), source) == {
        "array": [None, False, 0, "value"], "object": {},
    }


@pytest.mark.parametrize("output_type", [
    "json-schema", "openapi", "avro-schema", "json-structure",
])
def test_cli_generates_the_selected_model_in_all_formats(tmp_path, output_type):
    group = {"singular": "local", "attributes": {"value": {"type": "boolean"}}}
    other = {"singular": "other", "attributes": {"count": {"type": "integer"}}}
    write_document(tmp_path, "local.json", {**group, "singular": "overridden"})
    write_document(tmp_path, "nested/groups.json", {
        "items": {"singular": "ignored"},
        "others": {"$include": "other.json"},
    })
    write_document(tmp_path, "nested/other.json", other)
    write_document(tmp_path, "later.json", {"others": {"singular": "ignored"}})
    included = write_document(tmp_path, "included.json", {"groups": {
        "$includes": ["nested/groups.json", "later.json"],
        "items": {"$include": "local.json", "singular": "local"},
    }})
    flat = write_document(tmp_path, "flat.json", {"groups": {"items": group, "others": other}})
    original = included.read_bytes()
    outputs = []
    for source in (included, flat):
        output = tmp_path / f"{source.stem}-output.json"
        result = subprocess.run([
            sys.executable, "-B", str(Path(__file__).with_name("schema-generator.py")),
            "--type", output_type, "--output", str(output), str(source),
        ], capture_output=True, text=True, timeout=30, check=False)
        assert result.returncode == 0, result.stderr
        outputs.append(json.loads(output.read_text(encoding="utf-8")))
    assert outputs[0] == outputs[1]
    assert included.read_bytes() == original
    output = outputs[0]
    if output_type == "json-schema":
        jsonschema.Draft7Validator.check_schema(output)
        assert set(output["properties"]) == {
            "$schema", "registryid", "specversion", "self", "shortself", "xid", "epoch",
            "name", "description", "documentation", "icon", "labels",
            "createdat", "modifiedat", "capabilities", "model", "modelsource",
            "items", "itemsurl", "itemscount",
            "others", "othersurl", "otherscount",
        }
        validator = jsonschema.Draft7Validator(output)
        assert validator.is_valid({"items": {"one": {"value": True}}})
        assert not validator.is_valid({"items": {"one": {"value": "wrong"}}})
    elif output_type == "openapi":
        validate_spec(output)
        assert output["components"]["schemas"]["local"]["properties"]["value"] == {
            "type": "boolean",
        }
        assert output["components"]["schemas"]["other"]["properties"]["count"] == {
            "type": "integer",
        }
    elif output_type == "avro-schema":
        parsed = avro.schema.parse(json.dumps(output))
        assert {field.name for field in parsed.fields} == {"items", "others"}
        local = next(field for field in parsed.fields if field.name == "items")
        value = next(field for field in local.type.values.fields if field.name == "value")
        assert value.type.type == "boolean"
    else:
        assert output["$schema"] == "https://json-structure.org/meta/extended/v0/#"
        assert set(output["properties"]) == {"items", "others"}
        assert output["definitions"]["Items"]["Local"]["properties"]["value"] == {
            "type": "boolean",
        }


# ========================================================================
# Conditional selector matching (ifvalues)
# Originally tools/test_schema_generator_ifvalues_644.py
# Renamed to keep this section's bindings distinct: generator -> ifvalues_generator, model_with -> ifvalues_model_with
# ========================================================================

@pytest.fixture(scope="module")
def ifvalues_generator():
    path = Path(__file__).with_name("schema-generator.py")
    spec = importlib.util.spec_from_file_location("schema_generator_ifvalues_644", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(params=["json-schema", "openapi"])
def dialect(request):
    return request.param


def ifvalues_model_with(attributes):
    return {"groups": {"tests": {"singular": "test", "attributes": attributes}}}


def validator_for(ifvalues_generator, model, dialect, group="test"):
    schema = ifvalues_generator.generate_json_schema(copy.deepcopy(model), dialect == "openapi")
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
def test_all_ascii_case_variants_activate_the_same_branch(ifvalues_generator, dialect, key):
    validator = validator_for(ifvalues_generator, ifvalues_model_with({"protocol": conditional(key=key)}), dialect)
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
def test_unknown_and_nonexact_selectors_keep_the_extension_fallback(ifvalues_generator, dialect, spelling):
    definition = ifvalues_model_with({
        "protocol": conditional(), "*": {"type": "any"},
    })
    validator = validator_for(ifvalues_generator, definition, dialect)
    instance = {"protocol": spelling, "options": {"limit": -1, "extension": True}}
    assert validator.is_valid(instance)
    assert instance["protocol"] == spelling
    del definition["groups"]["tests"]["attributes"]["*"]
    closed = validator_for(ifvalues_generator, definition, dialect)
    assert closed.is_valid({"protocol": spelling})
    assert not closed.is_valid(instance)


@pytest.mark.parametrize("spelling", [None, False, 1, [], {}])
def test_unknown_fallback_preserves_the_selector_type(ifvalues_generator, dialect, spelling):
    validator = validator_for(ifvalues_generator, ifvalues_model_with({"protocol": conditional()}), dialect)
    assert not validator.is_valid({"protocol": spelling})


@pytest.mark.parametrize("key", ["X.[?]+(Y)", "A B-C#D"])
def test_literal_pattern_characters_are_not_regular_expression_operators(ifvalues_generator, dialect, key):
    validator = validator_for(
        ifvalues_generator, ifvalues_model_with({
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
def test_unicode_single_character_case_variants(ifvalues_generator, dialect, key, spelling):
    validator = validator_for(ifvalues_generator, ifvalues_model_with({"protocol": conditional(key=key)}), dialect)
    assert validator.is_valid({"protocol": spelling, "options": {"limit": 1}})
    assert not validator.is_valid({"protocol": spelling, "options": {"limit": -1}})


@pytest.mark.parametrize(("selector_type", "key", "value", "unknown"), [
    ("boolean", "TRUE", True, False),
    ("integer", "-3", -3, -4),
    ("uinteger", str(2 ** 100), 2 ** 100, 2 ** 100 + 1),
])
def test_native_scalar_selectors_keep_their_types(ifvalues_generator, dialect, selector_type, key, value, unknown):
    validator = validator_for(
        ifvalues_generator, ifvalues_model_with({
            "selector": conditional(selector_type, key), "*": {"type": "any"},
        }), dialect,
    )
    assert validator.is_valid({"selector": value, "options": {"limit": 0}})
    assert not validator.is_valid({"selector": value, "options": {"limit": -1}})
    assert not validator.is_valid({"selector": str(value), "options": {"limit": 0}})
    assert validator.is_valid({"selector": unknown, "options": {"limit": -1}})


def test_empty_branches_do_not_activate_for_missing_selectors(ifvalues_generator, dialect):
    selector = {"type": "string", "ifvalues": {"EMPTY": {}}}
    validator = validator_for(ifvalues_generator, ifvalues_model_with({"protocol": selector}), dialect)
    assert validator.is_valid({})
    assert validator.is_valid({"protocol": "empty"})
    assert validator.is_valid({"protocol": "custom"})
    selector["required"] = True
    required = validator_for(ifvalues_generator, ifvalues_model_with({"protocol": selector}), dialect)
    assert not required.is_valid({})


def test_multiple_independent_selectors_all_remain_effective(ifvalues_generator, dialect):
    attributes = {
        f"selector{index}": conditional(key="KNOWN", sibling=f"options{index}")
        for index in range(3)
    }
    validator = validator_for(ifvalues_generator, ifvalues_model_with(attributes), dialect)
    valid = {
        **{f"selector{index}": "known" for index in range(3)},
        **{f"options{index}": {"limit": 0} for index in range(3)},
    }
    assert validator.is_valid(valid)
    for index in range(3):
        invalid = copy.deepcopy(valid)
        invalid[f"options{index}"]["limit"] = -1
        assert not validator.is_valid(invalid), index


def test_nested_ifvalues_apply_without_normalizing_other_values(ifvalues_generator, dialect):
    selector = conditional()
    selector["ifvalues"]["HTTP"]["siblingattributes"]["envelope"] = conditional(
        key="FORMAT", sibling="envelopeoptions",
    )
    validator = validator_for(ifvalues_generator, ifvalues_model_with({
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


def test_case_duplicate_selector_keys_fail_explicitly(ifvalues_generator, dialect):
    selector = conditional()
    selector["ifvalues"]["http"] = {}
    with pytest.raises(ValueError, match="case"):
        validator_for(ifvalues_generator, ifvalues_model_with({"protocol": selector}), dialect)


def test_empty_ifvalues_preserves_normal_attribute_validation(ifvalues_generator, dialect):
    validator = validator_for(ifvalues_generator, ifvalues_model_with({
        "protocol": {"type": "string", "required": True, "ifvalues": {}},
    }), dialect)
    assert validator.is_valid({"protocol": "any"})
    assert not validator.is_valid({})
    assert not validator.is_valid({"protocol": False})


def test_openapi_conditionals_are_connected_without_case_sensitive_discriminators(ifvalues_generator):
    model = ifvalues_model_with({"protocol": conditional()})
    openapi = ifvalues_generator.generate_openapi(copy.deepcopy(model))
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


def request_checkers(ifvalues_generator, attributes, method="patch", scope="group"):
    root = Path(__file__).resolve().parent.parent
    model = ({"attributes": attributes, "groups": {}} if scope == "root" else
             {"groups": {"catalogs": {"singular": "catalog", "attributes": attributes}}})
    jsonschema.Draft7Validator(json.loads(
        (root / "core" / "model.schema.json").read_text(encoding="utf-8")
    )).validate(model)
    original = copy.deepcopy(model)
    schema = ifvalues_generator.generate_openapi(model)
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
def test_readonly_selectors_keep_writable_conditional_siblings(ifvalues_generator, method, scope):
    attributes = {"mode": {
        "type": "string", "readonly": True,
        "ifvalues": {"limited": {"siblingattributes": {"limit": {"type": "integer"}}}},
    }}
    checker, read = request_checkers(ifvalues_generator, attributes, method, scope)
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
    ifvalues_generator, method, wildcard
):
    attributes = {
        "mode": {"type": "string", "ifvalues": {
            "number": {"siblingattributes": {"value": {"type": "integer"}}},
        }},
    }
    if wildcard:
        attributes["*"] = {"type": wildcard}
    checker, read = request_checkers(ifvalues_generator, attributes, method)
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
    ifvalues_generator, selector
):
    attributes = {"*": {"type": "string"}, "mode": {
        **selector, "ifvalues": {"number": {"siblingattributes": {
            "value": {"type": "integer", "required": True},
        }}},
    }}
    checker, _ = request_checkers(ifvalues_generator, attributes)
    for value in ({"value": 7}, {"value": "extension"}, {"value": None}, {}):
        payload = conditional_request(value)
        before = copy.deepcopy(payload)
        checker.validate(payload)
        assert payload == before
    with pytest.raises(jsonschema.ValidationError):
        checker.validate(conditional_request({"value": {"wrong": True}}))


def test_request_conditional_wildcards_remain_guarded_for_known_selectors(ifvalues_generator):
    attributes = {"fixed": {"type": "string"}, "mode": {
        "type": "string", "ifvalues": {
            "open": {"siblingattributes": {"*": {"type": "integer"}}},
            "closed": {"siblingattributes": {}},
        },
    }}
    checker, _ = request_checkers(ifvalues_generator, attributes)
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


def test_colliding_request_conditions_preserve_known_constraints_and_unknown_alternatives(ifvalues_generator):
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
    checker, _ = request_checkers(ifvalues_generator, attributes)
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
    ifvalues_generator, readonly_second
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
    checker, _ = request_checkers(ifvalues_generator, attributes)
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


# ========================================================================
# Scalar attribute value sets (enum and strict)
# Originally tools/test_schema_generator_scalar_enums.py
# Renamed to keep this section's bindings distinct: SOURCE -> scalar_SOURCE, accepts -> scalar_accepts, base_document -> scalar_base_document, document_with -> scalar_document_with, entry_meta -> scalar_entry_meta, generated_validator -> scalar_generated_validator, rejects -> scalar_rejects
# ========================================================================

scalar_SOURCE = jsonschema.Draft7Validator(MODEL_SCHEMA)


QOS = {"type": "uinteger", "enum": [0, 1, 2]}


MEMBERS = [0, 1, 2]


NON_MEMBERS = [3, -1]


WRONG_TYPES = ["1", True, 1.5, None, [0], {"a": 0}]


def scalar_generated_validator(definition, dialect):
    scalar_SOURCE.validate(definition)
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


def scalar_entry_meta():
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


def scalar_base_document():
    return {
        "registryid": "r", "specversion": "1.0", "self": "https://example.com/",
        "xid": "/", "epoch": 1, "createdat": STAMP, "modifiedat": STAMP,
        "catalogs": {"c": {
            "catalogid": "c",
            "entries": {"e": {
                "entryid": "e", "meta": scalar_entry_meta(),
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


def scalar_document_with(location, value):
    document = scalar_base_document()
    LOCATIONS[location][1](document, value)
    return document


def scalar_accepts(validator, instance):
    validator.validate(instance)


def scalar_rejects(validator, instance):
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(instance)


@pytest.mark.parametrize("location", sorted(LOCATIONS))
@pytest.mark.parametrize("dialect", DIALECTS)
@pytest.mark.parametrize("strict", [None, True])
def test_strict_scalar_enum_restricts_every_scalar_leaf(location, dialect, strict):
    definition = dict(QOS) if strict is None else {**QOS, "strict": strict}
    validator = scalar_generated_validator(placed(location, definition), dialect)
    for member in MEMBERS:
        scalar_accepts(validator, scalar_document_with(location, member))
    for value in NON_MEMBERS:
        scalar_rejects(validator, scalar_document_with(location, value))


@pytest.mark.parametrize("location", sorted(LOCATIONS))
@pytest.mark.parametrize("dialect", DIALECTS)
def test_wrong_typed_values_stay_invalid_under_a_strict_enum(location, dialect):
    validator = scalar_generated_validator(placed(location, QOS), dialect)
    for value in WRONG_TYPES:
        scalar_rejects(validator, scalar_document_with(location, value))


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
    validator = scalar_generated_validator(placed(location, definition), dialect)
    for value in MEMBERS + [3]:
        scalar_accepts(validator, scalar_document_with(location, value))
    scalar_rejects(validator, scalar_document_with(location, "3"))


@pytest.mark.parametrize("dialect", DIALECTS)
def test_boolean_and_string_enums_keep_their_own_scalar_types(dialect):
    validator = scalar_generated_validator(
        placed("registry", {"type": "boolean", "enum": [True]}), dialect)
    scalar_accepts(validator, scalar_document_with("registry", True))
    scalar_rejects(validator, scalar_document_with("registry", False))
    scalar_rejects(validator, scalar_document_with("registry", "true"))
    scalar_rejects(validator, scalar_document_with("registry", 1))

    validator = scalar_generated_validator(
        placed("registry", {"type": "string", "enum": ["alpha"]}), dialect)
    scalar_accepts(validator, scalar_document_with("registry", "alpha"))
    scalar_rejects(validator, scalar_document_with("registry", "ALPHA"))
    scalar_rejects(validator, scalar_document_with("registry", "other"))


@pytest.mark.parametrize("dialect", DIALECTS)
def test_inactive_wildcard_fallback_and_declared_names_keep_their_own_rules(dialect):
    definition = base_model()
    definition["attributes"]["box"] = {"type": "object", "attributes": {
        "level": {"type": "uinteger", "enum": [0, 1, 2]},
        "*": {"name": "*", "type": "string", "enum": ["alpha"]},
    }}
    validator = scalar_generated_validator(definition, dialect)
    document = scalar_base_document()
    document["box"] = {"level": 2, "other": "alpha"}
    scalar_accepts(validator, document)
    document["box"] = {"level": 2, "other": "beta"}
    scalar_rejects(validator, document)
    document["box"] = {"level": 3, "other": "alpha"}
    scalar_rejects(validator, document)


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
    validator = scalar_generated_validator(endpoint_model(), "json-schema")
    for value in MEMBERS:
        scalar_accepts(validator, endpoint_document(protocol, value))
    for value in [3, "1", True]:
        scalar_rejects(validator, endpoint_document(protocol, value))


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
    validator = scalar_generated_validator(selector_model(), dialect)
    document = scalar_base_document()
    document.update({"kind": "ALPHA", "detail": "on"})
    scalar_accepts(validator, document)
    document.update({"kind": "ALPHAX", "detail": "on"})
    scalar_rejects(validator, document)


@pytest.mark.parametrize("dialect", DIALECTS)
def test_case_insensitive_selection_does_not_legalize_a_non_member(dialect):
    validator = scalar_generated_validator(selector_model(enum=["alpha"]), dialect)
    document = scalar_base_document()
    document.update({"kind": "alpha", "detail": "on"})
    scalar_accepts(validator, document)
    for value in ("ALPHA", "other"):
        document.update({"kind": value, "detail": "on"})
        scalar_rejects(validator, document)


@pytest.mark.parametrize("dialect", DIALECTS)
def test_an_advisory_enum_leaves_case_insensitive_selection_intact(dialect):
    validator = scalar_generated_validator(
        selector_model(enum=["alpha"], strict=False), dialect)
    document = scalar_base_document()
    document.update({"kind": "ALPHA", "detail": "on"})
    scalar_accepts(validator, document)


def test_a_selector_outside_an_effective_strict_enum_is_an_invalid_source_model():
    model = selector_model(enum=["beta"])
    scalar_SOURCE.validate(model)
    with pytest.raises(ValueError, match="ifvalues"):
        GENERATOR.generate_json_schema(copy.deepcopy(model))


def test_a_selector_outside_an_advisory_enum_remains_legal():
    GENERATOR.generate_json_schema(selector_model(enum=["beta"], strict=False))
    GENERATOR.generate_json_schema(selector_model(enum=[]))


def test_selector_membership_is_matched_case_insensitively():
    GENERATOR.generate_json_schema(selector_model(enum=["ALPHA"]))


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
    validator = scalar_generated_validator(
        constrained_model(QOS, {"enum": [1, 2]}), dialect)
    scalar_accepts(validator, constrained_document(1))
    scalar_accepts(validator, constrained_document(2))
    scalar_rejects(validator, constrained_document(0))


@pytest.mark.parametrize("dialect", DIALECTS)
def test_a_group_constraint_restricts_an_advisory_base(dialect):
    validator = scalar_generated_validator(
        constrained_model({**QOS, "strict": False}, {"enum": [1]}), dialect)
    scalar_accepts(validator, constrained_document(1))
    scalar_rejects(validator, constrained_document(2))


@pytest.mark.parametrize("dialect", DIALECTS)
def test_an_empty_constraint_enum_adds_no_restriction(dialect):
    validator = scalar_generated_validator(
        constrained_model({**QOS, "strict": False}, {"enum": []}), dialect)
    scalar_accepts(validator, constrained_document(3))


@pytest.mark.parametrize("dialect", DIALECTS)
def test_group_constraints_also_reach_the_version_definition(dialect):
    validator = scalar_generated_validator(
        constrained_model(QOS, {"enum": [1, 2]}), dialect)
    document = constrained_document(1)
    entry = document["catalogs"]["g"]["entries"]["e"]
    del entry["versionsurl"]
    entry["versions"] = {"v1": {"entryid": "e", "versionid": "v1", "level": 1}}
    scalar_accepts(validator, document)
    entry["versions"]["v1"]["level"] = 0
    scalar_rejects(validator, document)


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
    validator = scalar_generated_validator(model, dialect)
    document = constrained_document(None)
    document["catalogs"]["g"]["entries"]["e"] = {
        "entryid": "e", "box": {"level": 1}}
    scalar_accepts(validator, document)
    document["catalogs"]["g"]["entries"]["e"]["box"]["level"] = 2
    scalar_rejects(validator, document)


IMPORTERS = {
    "mirrors": {"singular": "mirror", "ximportresources": ["/catalogs/entries"],
                "constraints": {"entries.level": {"enum": [1]}}},
    "clones": {"singular": "clone", "ximportresources": ["/catalogs/entries"]},
}


@pytest.mark.parametrize("dialect", DIALECTS)
def test_an_imported_resource_keeps_each_group_s_own_constraints(dialect):
    model = constrained_model(QOS, None, extra_groups=IMPORTERS)
    validator = scalar_generated_validator(model, dialect)
    scalar_accepts(validator, constrained_document(1, "mirrors", "mirror"))
    scalar_rejects(validator, constrained_document(2, "mirrors", "mirror"))
    scalar_accepts(validator, constrained_document(2, "clones", "clone"))
    scalar_accepts(validator, constrained_document(2))


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
    validator = scalar_generated_validator(model, dialect)
    document = constrained_document("anything")
    document["catalogs"]["g"]["kind"] = "other"
    scalar_accepts(validator, document)


def test_the_real_schema_registry_model_keeps_its_equals_constraint_unprojected():
    source = json.loads((ROOT / "schema" / "model.json").read_text(encoding="utf-8"))
    model = GENERATOR.resolve_imports(str(ROOT / "schema"), source)
    schema = GENERATOR.generate_json_schema(copy.deepcopy(model))
    definition = schema["definitions"]["schemagroup-schema"]["schema"]
    assert "enum" not in definition["properties"]["format"]


@pytest.mark.parametrize("carrier", ["array", "map", "object", "any"])
@pytest.mark.parametrize("generate", [
    "generate_json_schema", "generate_openapi", "generate_json_structure",
    "generate_avro_schema",
])
def test_owning_container_enum_is_rejected(carrier, generate):
    model = base_model()
    declaration = {"type": carrier, "enum": ["a", "b"]}
    if carrier in ("array", "map"):
        declaration["item"] = {"type": "string"}
    model["groups"]["catalogs"]["attributes"]["usage"] = declaration
    with pytest.raises(jsonschema.ValidationError):
        scalar_SOURCE.validate(model)
    with pytest.raises(ValueError, match="scalar types only"):
        getattr(GENERATOR, generate)(model)


@pytest.mark.parametrize("carrier", ["array", "map", "object", "any"])
@pytest.mark.parametrize("strict", [True, False])
@pytest.mark.parametrize("generate", [
    "generate_json_schema", "generate_openapi", "generate_json_structure",
    "generate_avro_schema",
])
def test_owning_container_strict_without_enum_is_inert(carrier, strict, generate):
    baseline = base_model()
    declaration = {"type": carrier}
    if carrier in ("array", "map"):
        declaration["item"] = {"type": "string"}
    baseline["groups"]["catalogs"]["attributes"]["usage"] = declaration
    candidate = copy.deepcopy(baseline)
    candidate["groups"]["catalogs"]["attributes"]["usage"]["strict"] = strict
    scalar_SOURCE.validate(candidate)
    assert getattr(GENERATOR, generate)(candidate) == getattr(
        GENERATOR, generate
    )(baseline)


def test_item_level_enums_are_admitted_only_for_approved_scalar_item_kinds():
    """The reviewed Endpoint directive added a scalar `item.enum`; an `enum` on
    a container item stays invalid. The scalar item value set section below
    owns the projection of the admitted form."""
    model = base_model()
    model["attributes"]["usage"] = {
        "type": "array", "item": {"type": "string", "enum": ["a"]},
    }
    scalar_SOURCE.validate(model)
    nested = base_model()
    nested["attributes"]["usage"] = {
        "type": "array",
        "item": {"type": "map", "enum": ["a"], "item": {"type": "string"}},
    }
    with pytest.raises(jsonschema.ValidationError):
        scalar_SOURCE.validate(nested)


def test_json_structure_scalar_enum_annotation_is_unchanged():
    model = base_model()
    model["groups"]["catalogs"]["attributes"]["level"] = copy.deepcopy(QOS)
    structure = GENERATOR.generate_json_structure(model, schema_name="Doc")
    catalog = structure["definitions"]["Catalogs"]["Catalog"]
    assert catalog["properties"]["level"]["enum"] == [0, 1, 2]


# ========================================================================
# Scalar item value sets (item.enum and item.strict)
# Originally tools/test_schema_generator_item_enums.py
# Renamed to keep this section's bindings distinct: SOURCE -> item_SOURCE, accepts -> item_accepts, base_document -> item_base_document, document_with -> item_document_with, entry_meta -> item_entry_meta, generated_validator -> item_generated_validator, model_with -> item_model_with, rejects -> item_rejects
# ========================================================================

item_SOURCE = VALIDATE_MODELS.source_validator(MODEL_SCHEMA)


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


def item_entry_meta():
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


def item_base_document():
    return {
        "registryid": "r", "specversion": "1.0", "self": "https://example.com/",
        "xid": "/", "epoch": 1, "createdat": STAMP, "modifiedat": STAMP,
        "catalogs": {"c": {
            "catalogid": "c",
            "entries": {"e": {
                "entryid": "e", "meta": item_entry_meta(),
                "versions": {"v1": {"entryid": "e", "versionid": "v1"}},
            }},
        }},
    }


def item_model_with(definition, name="usage"):
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


def item_document_with(value, name="usage"):
    document = item_base_document()
    document[name] = value
    return document


def roles_array(**item_extra):
    return {"type": "array", "item": {"type": "string", **item_extra}}


ROLE_ARRAY = roles_array(enum=list(ROLES))


ROLE_MAP = {"type": "map", "item": {"type": "string", "enum": list(ROLES)}}


def accepts_source(instance, validator=item_SOURCE):
    before = copy.deepcopy(instance)
    validator.validate(instance)
    assert instance == before


def rejects_source(instance, validator=item_SOURCE):
    before = copy.deepcopy(instance)
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(instance)
    assert instance == before


@pytest.mark.parametrize("carrier", ["array", "map"])
def test_source_admits_a_string_item_enum_on_an_array_or_map(carrier):
    accepts_source(item_model_with(
        {"type": carrier, "item": {"type": "string", "enum": list(ROLES)}}
    ))


@pytest.mark.parametrize("item_type", SCALAR_ITEM_TYPES)
def test_source_admits_an_item_enum_on_every_scalar_item_type(item_type):
    accepts_source(item_model_with(
        {"type": "array", "item": {"type": item_type, "enum": ["a"]}}
    ))


@pytest.mark.parametrize("strict", [True, False])
def test_source_admits_an_explicit_item_strict_flag(strict):
    accepts_source(item_model_with(roles_array(enum=list(ROLES), strict=strict)))


def test_source_admits_an_empty_item_enum_like_an_attribute_enum():
    accepts_source(item_model_with(roles_array(enum=[])))


@pytest.mark.parametrize("item_type", NON_SCALAR_ITEM_TYPES)
def test_source_rejects_an_item_enum_on_a_non_scalar_item_type(item_type):
    rejects_source(item_model_with(
        {"type": "array", "item": non_scalar_item(item_type, enum=["a"])}))


@pytest.mark.parametrize("item_type", NON_SCALAR_ITEM_TYPES)
@pytest.mark.parametrize("strict", [True, False])
def test_source_accepts_an_inert_item_strict_on_a_non_scalar(item_type, strict):
    accepts_source(item_model_with(
        {"type": "array", "item": non_scalar_item(item_type, strict=strict)}))
    rejects_source(item_model_with({
        "type": "array",
        "item": non_scalar_item(item_type, enum=["a"], strict=strict),
    }))


@pytest.mark.parametrize("strict", [True, False])
def test_source_admits_a_scalar_item_strict_without_an_enum(strict):
    accepts_source(item_model_with(roles_array(strict=strict)))


@pytest.mark.parametrize("value", ["subscriber", {"0": "subscriber"}, 3])
def test_source_rejects_an_item_enum_that_is_not_an_array(value):
    rejects_source(item_model_with(roles_array(enum=value)))


@pytest.mark.parametrize("value", ["true", 1, [True]])
def test_source_rejects_a_non_boolean_item_strict(value):
    rejects_source(item_model_with(roles_array(enum=list(ROLES), strict=value)))


def test_source_admits_an_item_enum_inside_a_nested_container():
    accepts_source(item_model_with({
        "type": "array",
        "item": {"type": "map", "item": {"type": "string", "enum": list(ROLES)}},
    }))
    accepts_source(item_model_with({
        "type": "map",
        "item": {"type": "array", "item": {"type": "string", "enum": list(ROLES)}},
    }))


def test_source_still_rejects_an_unknown_item_keyword():
    rejects_source(item_model_with(roles_array(symbols=list(ROLES))))


def test_the_expanded_stage_accepts_a_completed_item_enum():
    accepts_source(item_model_with(ROLE_ARRAY), validator=EXPANDED)


def test_the_expanded_stage_still_requires_an_item_type_beside_an_enum():
    rejects_source(item_model_with({"type": "array", "item": {"enum": list(ROLES)}}),
                   validator=EXPANDED)


def item_generated_validator(definition, dialect):
    item_SOURCE.validate(definition)
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


def item_accepts(validator, instance):
    validator.validate(instance)


def item_rejects(validator, instance):
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(instance)


@pytest.mark.parametrize("dialect", DIALECTS)
@pytest.mark.parametrize("strict", [None, True])
def test_array_elements_are_restricted_to_the_item_enum(dialect, strict):
    item_extra = {"enum": list(ROLES)}
    if strict is not None:
        item_extra["strict"] = strict
    checker = item_generated_validator(item_model_with(roles_array(**item_extra)), dialect)
    item_accepts(checker, item_document_with([]))
    item_accepts(checker, item_document_with(list(ROLES)))
    item_accepts(checker, item_document_with(["producer", "producer"]))
    item_rejects(checker, item_document_with(["publisher"]))
    item_rejects(checker, item_document_with(["subscriber", "publisher"]))


@pytest.mark.parametrize("dialect", DIALECTS)
def test_map_values_are_restricted_to_the_item_enum(dialect):
    checker = item_generated_validator(item_model_with(ROLE_MAP), dialect)
    item_accepts(checker, item_document_with({"a": "subscriber", "b": "producer"}))
    item_rejects(checker, item_document_with({"a": "publisher"}))
    item_rejects(checker, item_document_with({"a": "subscriber", "b": "publisher"}))


@pytest.mark.parametrize("dialect", DIALECTS)
def test_item_membership_stays_case_sensitive(dialect):
    checker = item_generated_validator(item_model_with(ROLE_ARRAY), dialect)
    item_accepts(checker, item_document_with(["subscriber"]))
    item_rejects(checker, item_document_with(["Subscriber"]))
    item_rejects(checker, item_document_with(["SUBSCRIBER"]))


@pytest.mark.parametrize("dialect", DIALECTS)
def test_string_and_boolean_item_kinds_keep_their_own_values(dialect):
    strings = item_generated_validator(
        item_model_with(roles_array(enum=["true", "false"])), dialect)
    item_accepts(strings, item_document_with(["true"]))
    item_rejects(strings, item_document_with([True]))
    booleans = item_generated_validator(
        item_model_with({"type": "array", "item": {"type": "boolean", "enum": [True]}}),
        dialect)
    item_accepts(booleans, item_document_with([True]))
    item_rejects(booleans, item_document_with(["true"]))
    item_rejects(booleans, item_document_with([False]))


@pytest.mark.parametrize("dialect", DIALECTS)
def test_integer_item_enums_reject_a_matching_string_spelling(dialect):
    checker = item_generated_validator(
        item_model_with({"type": "array", "item": {"type": "uinteger", "enum": [0, 1, 2]}}),
        dialect)
    item_accepts(checker, item_document_with([0, 2]))
    item_rejects(checker, item_document_with([3]))
    item_rejects(checker, item_document_with(["1"]))
    item_rejects(checker, item_document_with([True]))


@pytest.mark.parametrize("dialect", DIALECTS)
def test_an_advisory_item_enum_admits_a_non_member(dialect):
    checker = item_generated_validator(
        item_model_with(roles_array(enum=list(ROLES), strict=False)), dialect)
    item_accepts(checker, item_document_with(["publisher"]))


@pytest.mark.parametrize("dialect", DIALECTS)
@pytest.mark.parametrize("item_extra", [{}, {"enum": []}, {"enum": [], "strict": True}])
def test_an_empty_or_absent_item_enum_adds_no_membership_restriction(
    dialect, item_extra
):
    checker = item_generated_validator(item_model_with(roles_array(**item_extra)), dialect)
    item_accepts(checker, item_document_with(["publisher"]))
    item_rejects(checker, item_document_with([3]))


@pytest.mark.parametrize("dialect", DIALECTS)
@pytest.mark.parametrize("strict", [True, False])
def test_a_scalar_item_strict_without_an_enum_adds_no_restriction(dialect, strict):
    checker = item_generated_validator(item_model_with(roles_array(strict=strict)), dialect)
    item_accepts(checker, item_document_with(["publisher"]))
    item_rejects(checker, item_document_with([3]))


@pytest.mark.parametrize("dialect", DIALECTS)
def test_an_array_of_maps_projects_the_inner_value_enum(dialect):
    checker = item_generated_validator(item_model_with({
        "type": "array",
        "item": {"type": "map", "item": {"type": "string", "enum": list(ROLES)}},
    }), dialect)
    item_accepts(checker, item_document_with([{"a": "consumer"}]))
    item_rejects(checker, item_document_with([{"a": "publisher"}]))


@pytest.mark.parametrize("dialect", DIALECTS)
def test_a_map_of_arrays_projects_the_inner_element_enum(dialect):
    checker = item_generated_validator(item_model_with({
        "type": "map",
        "item": {"type": "array", "item": {"type": "string", "enum": list(ROLES)}},
    }), dialect)
    item_accepts(checker, item_document_with({"a": ["consumer"]}))
    item_rejects(checker, item_document_with({"a": ["publisher"]}))


@pytest.mark.parametrize("dialect", DIALECTS)
def test_object_items_keep_their_own_named_scalar_enums(dialect):
    checker = item_generated_validator(item_model_with({
        "type": "array",
        "item": {"type": "object", "attributes": {
            "role": {"name": "role", "type": "string", "enum": list(ROLES)},
        }},
    }), dialect)
    item_accepts(checker, item_document_with([{"role": "producer"}]))
    item_rejects(checker, item_document_with([{"role": "publisher"}]))


@pytest.mark.parametrize("dialect", DIALECTS)
def test_an_item_enum_at_a_group_and_version_attribute(dialect):
    model = base_model()
    model["groups"]["catalogs"]["attributes"]["usage"] = copy.deepcopy(ROLE_ARRAY)
    model["groups"]["catalogs"]["resources"]["entries"]["attributes"]["usage"] = (
        copy.deepcopy(ROLE_ARRAY)
    )
    checker = item_generated_validator(model, dialect)
    document = item_base_document()
    document["catalogs"]["c"]["usage"] = ["producer"]
    document["catalogs"]["c"]["entries"]["e"]["versions"]["v1"]["usage"] = ["consumer"]
    item_accepts(checker, document)
    document["catalogs"]["c"]["usage"] = ["publisher"]
    item_rejects(checker, document)


def openapi_body_validators(model):
    openapi = GENERATOR.generate_openapi(copy.deepcopy(model))
    validate(openapi)
    components = openapi["components"]

    def build(schema, read):
        implementation = OAS30ReadValidator if read else OAS30WriteValidator
        return implementation({**schema, "components": components},
                              format_checker=OAS30Validator.FORMAT_CHECKER)

    return openapi, build


def test_a_request_may_omit_or_reset_the_array_but_not_smuggle_a_non_member():
    openapi, build = openapi_body_validators(item_model_with(ROLE_ARRAY))
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
    openapi, build = openapi_body_validators(item_model_with(ROLE_ARRAY))
    checker = build(openapi["paths"]["/"]["get"]["responses"]["200"]["content"][
        "application/json"]["schema"], read=True)
    checker.validate(registry_body(usage=["consumer"]))
    with pytest.raises(jsonschema.ValidationError):
        checker.validate(registry_body(usage=["publisher"]))


@pytest.mark.parametrize("enum", [[1], [True], [None], [["subscriber"]], [{}]])
def test_the_generator_rejects_a_wrong_kind_item_enum_value(enum):
    with pytest.raises(ValueError, match="not a valid string"):
        GENERATOR.generate_json_schema(item_model_with(roles_array(enum=enum)))


def test_the_generator_rejects_a_wrong_kind_value_for_a_numeric_item():
    with pytest.raises(ValueError, match="not a valid uinteger"):
        GENERATOR.generate_json_schema(item_model_with(
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
        GENERATOR.generate_json_schema(item_model_with({
            "type": "map", "item": {"type": "array", "item": item},
        }))


@pytest.mark.parametrize("generate", EMITTERS)
def test_an_empty_advisory_item_enum_stays_a_legal_source_model(generate):
    getattr(GENERATOR, generate)(
        group_model_with(roles_array(enum=[], strict=False)))


def test_a_wrong_kind_item_enum_is_rejected_inside_a_nested_container():
    with pytest.raises(ValueError, match="not a valid string"):
        GENERATOR.generate_json_schema(item_model_with({
            "type": "map",
            "item": {"type": "array", "item": {"type": "string", "enum": [1]}},
        }))


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


# ========================================================================
# Generated request and response closure
# Originally tools/test_schema_generator_closure.py
# Renamed to keep this section's bindings distinct: document -> closure_document, entry_meta -> closure_entry_meta, generated_validator -> closure_generated_validator, model -> closure_model
# ========================================================================

def closure_model(definition):
    return {
        "groups": {
            "catalogs": {
                "singular": "catalog",
                "attributes": {
                    "name": {"type": "string", "required": True},
                    "payload": definition,
                },
            }
        }
    }


def closure_document(value):
    return {
        "registryid": "r", "specversion": "1.0",
        "self": "https://example.com/", "xid": "/", "epoch": 1,
        "createdat": "2026-01-01T00:00:00Z",
        "modifiedat": "2026-01-01T00:00:00Z",
        "catalogs": {
            "c": {"catalogid": "c", "name": "catalog", "payload": value}
        },
    }


def closure_entry_meta(default_version="v1"):
    resource = "/catalogs/c/entries/e"
    return {
        "entryid": "e", "readonly": False,
        "self": f"https://example.com{resource}/meta",
        "xid": f"{resource}/meta", "epoch": 1,
        "createdat": "2026-01-01T00:00:00Z",
        "modifiedat": "2026-01-01T00:00:00Z",
        "defaultversionid": default_version,
        "defaultversionurl": f"https://example.com{resource}/versions/{default_version}",
        "defaultversionsticky": False,
    }


def closure_generated_validator(definition, dialect):
    if dialect == "json-schema":
        schema = GENERATOR.generate_json_schema(definition)
        jsonschema.Draft7Validator.check_schema(schema)
    else:
        openapi = GENERATOR.generate_openapi(definition)
        validate(openapi)
        reference = openapi["paths"]["/"]["get"]["responses"]["200"][
            "content"
        ]["application/json"]["schema"]
        schema = {**reference, "components": openapi["components"]}
    return jsonschema.Draft7Validator(schema)


CLOSED_LEAF = {
    "type": "object",
    "attributes": {"name": {"type": "string", "required": True}},
}


BOUNDARIES = [
    ({"type": "object"}, {}, ()),
    ({"type": "object", "attributes": {}}, {}, ()),
    (CLOSED_LEAF, {"name": "http"}, ()),
    (
        {"type": "object", "attributes": {"inner": CLOSED_LEAF}},
        {"inner": {"name": "http"}}, ("inner",),
    ),
    (
        {"type": "array", "item": CLOSED_LEAF},
        [{"name": "http"}], (0,),
    ),
    (
        {"type": "map", "item": CLOSED_LEAF},
        {"first": {"name": "http"}, "second": {"name": "other"}}, ("first",),
    ),
    (
        {"type": "array", "item": {"type": "map", "item": {
            "type": "array", "item": CLOSED_LEAF,
        }}},
        [{"first": [{"name": "http"}]}], (0, "first", 0),
    ),
]


@pytest.mark.parametrize("dialect", ["json-schema", "openapi"])
@pytest.mark.parametrize("definition, value, path", BOUNDARIES)
def test_closed_objects_reject_unknown_members_through_full_entity(
    dialect, definition, value, path
):
    validator = closure_generated_validator(closure_model(copy.deepcopy(definition)), dialect)
    valid = closure_document(copy.deepcopy(value))
    original = copy.deepcopy(valid)
    validator.validate(valid)
    assert valid == original
    invalid = copy.deepcopy(valid)
    leaf = invalid["catalogs"]["c"]["payload"]
    for part in path:
        leaf = leaf[part]
    leaf["unmodeled"] = True
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(invalid)
    assert valid == original


@pytest.mark.parametrize("dialect", ["json-schema", "openapi"])
@pytest.mark.parametrize("definition, value", [
    ({"type": "any"}, {"arbitrary": [{"nested": True}, 7]}),
    ({"type": "any"}, [7, {"arbitrary": True}]),
    ({"type": "object", "attributes": {"*": {"type": "any"}}},
     {"arbitrary": {"nested": [7, True]}}),
    ({"type": "map", "item": {"type": "any"}},
     {"first": {}, "second": {"arbitrary": True}}),
])
def test_explicit_any_and_map_surfaces_remain_open(dialect, definition, value):
    validator = closure_generated_validator(closure_model(copy.deepcopy(definition)), dialect)
    assert validator.is_valid(closure_document(copy.deepcopy(value)))
    assert validator.is_valid(closure_document({}))


@pytest.mark.parametrize("dialect", ["json-schema", "openapi"])
def test_typed_wildcard_does_not_restrict_named_properties(dialect):
    definition = {
        "type": "object",
        "attributes": {
            "name": {"type": "string"},
            "*": {"type": "integer"},
        },
    }
    validator = closure_generated_validator(closure_model(definition), dialect)
    validator.validate(closure_document({"name": "http", "first": 7, "second": 8}))
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(closure_document({"name": "http", "first": "wrong"}))


@pytest.mark.parametrize("dialect", ["json-schema", "openapi"])
def test_wildcard_object_values_keep_their_own_closed_boundary(dialect):
    definition = {"type": "object", "attributes": {
        "*": {"type": "object", "attributes": {"value": {"type": "string"}}},
    }}
    validator = closure_generated_validator(closure_model(definition), dialect)
    validator.validate(closure_document({"first": {"value": "ok"}, "second": {}}))
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(closure_document({"first": {"value": "ok", "extra": 7}}))


@pytest.mark.parametrize("dialect", ["json-schema", "openapi"])
def test_schema_generation_does_not_mutate_caller_model(dialect):
    definition = closure_model(copy.deepcopy(CLOSED_LEAF))
    original = copy.deepcopy(definition)
    closure_generated_validator(definition, dialect)
    assert definition == original


@pytest.mark.parametrize("dialect", ["json-schema", "openapi"])
def test_root_attributes_and_closure_apply_without_groups(dialect):
    definition = {
        "attributes": {
            "settings": {
                "type": "object", "required": True,
                "attributes": {"enabled": {"type": "boolean", "required": True}},
            },
        },
    }
    validator = closure_generated_validator(definition, dialect)
    value = closure_document({})
    del value["catalogs"]
    value["settings"] = {"enabled": True}
    validator.validate(value)
    for path in ((), ("settings",)):
        invalid = copy.deepcopy(value)
        owner = invalid
        for name in path:
            owner = owner[name]
        owner["unmodeled"] = True
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(invalid)
    del value["settings"]
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(value)


@pytest.mark.parametrize("dialect", ["json-schema", "openapi"])
def test_decimal_projection_accepts_json_numbers(dialect):
    validator = closure_generated_validator(closure_model({"type": "decimal"}), dialect)
    for value in (0, -1, 1.25):
        validator.validate(closure_document(value))
    for invalid in ("1.25", True, {"value": 1.25}):
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(closure_document(invalid))


@pytest.mark.parametrize("dialect", ["json-schema", "openapi"])
def test_common_epochs_preserve_unsigned_integer_values(dialect):
    validator = closure_generated_validator(closure_model({"type": "object"}), dialect)
    value = closure_document({})
    for epoch in (0, 2 ** 80):
        value["epoch"] = epoch
        value["catalogs"]["c"]["epoch"] = epoch
        validator.validate(value)
    for path in ((), ("catalogs", "c")):
        for invalid_epoch in (-1, 1.5, True):
            invalid = copy.deepcopy(value)
            owner = invalid
            for name in path:
                owner = owner[name]
            owner["epoch"] = invalid_epoch
            with pytest.raises(jsonschema.ValidationError):
                validator.validate(invalid)


def conditional_definition(wildcard=None):
    attributes = {
        "fixed": {"type": "string"},
        "kind": {
            "type": "string",
            "ifvalues": {
                "alpha": {"siblingattributes": {"alpha": CLOSED_LEAF}},
                "beta": {"siblingattributes": {
                    "beta": {"type": "integer", "required": True},
                }},
            },
        },
    }
    if wildcard is not None:
        attributes["*"] = wildcard
    return {"type": "object", "attributes": attributes}


@pytest.mark.parametrize("dialect", ["json-schema", "openapi"])
def test_conditional_members_are_admitted_only_in_the_active_branch(dialect):
    validator = closure_generated_validator(closure_model(conditional_definition()), dialect)
    for value in (
        {}, {"fixed": "ok"}, {"kind": "other"}, {"kind": "ALPHA"},
        {"kind": "alpha", "fixed": "ok", "alpha": {"name": "http"}},
        {"kind": "ALPHA", "alpha": {"name": "http"}},
        {"kind": "beta", "fixed": "ok", "beta": 7},
    ):
        validator.validate(closure_document(value))
    for value in (
        {"alpha": {"name": "http"}},
        {"kind": "other", "alpha": {"name": "http"}},
        {"kind": "ALPHAX", "alpha": {"name": "http"}},
        {"kind": "alpha", "beta": 7},
        {"kind": "beta"},
        {"kind": "beta", "beta": "wrong"},
        {"kind": "alpha", "alpha": {"name": "http", "extra": True}},
        {"kind": "beta", "unmodeled": True},
    ):
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(closure_document(value))


@pytest.mark.parametrize("dialect", ["json-schema", "openapi"])
def test_inactive_conditional_names_use_the_declared_wildcard(dialect):
    validator = closure_generated_validator(
        closure_model(conditional_definition({"type": "integer"})), dialect
    )
    validator.validate(closure_document({"kind": "alpha", "alpha": {"name": "http"}, "extra": 7}))
    validator.validate(closure_document({"kind": "other", "alpha": 7, "extra": 8}))
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(closure_document({"kind": "other", "alpha": {"name": "http"}}))
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(closure_document({"kind": "alpha", "alpha": {"name": "http"}, "extra": "bad"}))


@pytest.mark.parametrize("dialect", ["json-schema", "openapi"])
@pytest.mark.parametrize("wildcard", [{"type": "integer"}, {"type": "any"}])
def test_conditional_wildcards_open_only_the_active_scope(dialect, wildcard):
    definition = {
        "type": "object",
        "attributes": {
            "fixed": {"type": "string"},
            "kind": {"type": "string", "ifvalues": {
                "open": {"siblingattributes": {"*": wildcard}},
                "closed": {},
            }},
        },
    }
    validator = closure_generated_validator(closure_model(definition), dialect)
    validator.validate(closure_document({"kind": "open", "fixed": "ok", "extra": 7}))
    validator.validate(closure_document({"kind": "closed", "fixed": "ok"}))
    validator.validate(closure_document({}))
    for value in ({"extra": 7}, {"kind": "other", "extra": 7},
                  {"kind": "closed", "extra": 7}):
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(closure_document(value))
    if wildcard["type"] == "integer":
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(closure_document({"kind": "open", "extra": "bad"}))
    else:
        validator.validate(closure_document({"kind": "open", "extra": {"anything": [7]}}))


@pytest.mark.parametrize("dialect", ["json-schema", "openapi"])
def test_nested_and_independent_conditions_compose_without_allof_name_loss(dialect):
    definition = conditional_definition()
    attributes = definition["attributes"]
    attributes["kind"]["ifvalues"]["alpha"]["siblingattributes"]["sub"] = {
        "type": "string", "ifvalues": {
            "on": {"siblingattributes": {"leaf": CLOSED_LEAF}},
        },
    }
    attributes["mode"] = {"type": "string", "ifvalues": {
        "on": {"siblingattributes": {"enabled": {"type": "boolean"}}},
    }}
    validator = closure_generated_validator(closure_model(definition), dialect)
    value = {
        "kind": "alpha", "alpha": {"name": "http"}, "sub": "on",
        "leaf": {"name": "nested"}, "mode": "on", "enabled": True,
    }
    validator.validate(closure_document(value))
    for mutation in (
        {"sub": "off"}, {"kind": "other"}, {"mode": "off"},
        {"leaf": {"name": "nested", "extra": True}},
    ):
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(closure_document({**value, **mutation}))


@pytest.mark.parametrize("dialect", ["json-schema", "openapi"])
def test_full_entity_closure_preserves_core_overlays_and_collection_maps(dialect):
    definition = closure_model(copy.deepcopy(CLOSED_LEAF))
    definition["attributes"] = {
        "name": {"type": "string", "required": True},
        "rootdata": copy.deepcopy(CLOSED_LEAF),
    }
    group = definition["groups"]["catalogs"]
    group["resources"] = {"entries": {
        "singular": "entry", "hasdocument": False, "maxversions": 1,
        "attributes": {"data": copy.deepcopy(CLOSED_LEAF)},
    }}
    definition["groups"]["mirrors"] = {
        "singular": "mirror", "ximportresources": ["/catalogs/entries"],
    }
    validator = closure_generated_validator(definition, dialect)
    value = closure_document({"name": "http"})
    value.update({
        "name": "registry", "shortself": "https://example.com/r",
        "icon": "https://example.com/icon", "rootdata": {"name": "root"},
        "model": {"groups": {"anything": {}}},
        "modelsource": {"groups": {"anything": {}}},
        "capabilities": {"arbitrary": True},
        "catalogsurl": "https://example.com/catalogs", "catalogscount": 1,
        "mirrors": {"m": {"mirrorid": "m", "entries": {
            "imported": {"entryid": "imported", "data": {"name": "entry"}},
        }}},
    })
    value["catalogs"]["c"].update({
        "shortself": "https://example.com/c", "icon": "https://example.com/icon",
        "deprecated": {"alternative": "https://example.com/new"},
        "constraints": {"entries.format": {"enum": ["json"]}},
        "entriesurl": "https://example.com/catalogs/c/entries", "entriescount": 2,
        "entries": {
            "first": {"entryid": "first", "data": {"name": "entry"}},
            "second": {"entryid": "second", "data": {"name": "other"}},
        },
    })
    before = copy.deepcopy(value)
    validator.validate(value)
    assert value == before
    for path in (
        (), ("rootdata",), ("catalogs", "c"),
        ("catalogs", "c", "entries", "first"),
        ("catalogs", "c", "entries", "first", "data"),
        ("mirrors", "m", "entries", "imported", "data"),
    ):
        invalid = copy.deepcopy(value)
        target = invalid
        for part in path:
            target = target[part]
        target["unmodeled"] = True
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(invalid)

    for path in ((), ("catalogs", "c")):
        invalid = copy.deepcopy(value)
        target = invalid
        for part in path:
            target = target[part]
        target["name"] = 7
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(invalid)
        del target["name"]
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(invalid)


@pytest.mark.parametrize("dialect", ["json-schema", "openapi"])
@pytest.mark.parametrize("maxversions", [0, 1])
def test_version_and_meta_objects_close_without_closing_their_id_maps(
    dialect, maxversions
):
    definition = closure_model({"type": "any"})
    definition["groups"]["catalogs"]["resources"] = {"entries": {
        "singular": "entry", "maxversions": maxversions, "hasdocument": False,
        "attributes": {"data": copy.deepcopy(CLOSED_LEAF)},
        "metaattributes": {"custom": copy.deepcopy(CLOSED_LEAF)},
    }}
    validator = closure_generated_validator(definition, dialect)
    value = closure_document({})
    value["catalogs"]["c"]["entries"] = {"e": {
        "entryid": "e", "metaurl": "https://example.com/meta",
        "meta": {**closure_entry_meta("first"), "custom": {"name": "meta"}},
        "versions": {
            "first": {"entryid": "e", "versionid": "first",
                      "isdefault": True, "ancestorid": "first",
                      "data": {"name": "one"}},
            "second": {"entryid": "e", "versionid": "second",
                       "data": {"name": "two"}},
        },
    }}
    validator.validate(value)
    for path in (
        (), ("meta",), ("meta", "custom"), ("versions", "first"),
        ("versions", "second", "data"),
    ):
        invalid = copy.deepcopy(value)
        target = invalid["catalogs"]["c"]["entries"]["e"]
        for part in path:
            target = target[part]
        target["unmodeled"] = True
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(invalid)
    invalid = copy.deepcopy(value)
    invalid["catalogs"]["c"]["entries"]["e"]["versions"]["first"]["meta"] = {}
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(invalid)


@pytest.mark.parametrize("dialect", ["json-schema", "openapi"])
def test_root_wildcard_does_not_apply_to_core_or_declared_group_members(dialect):
    definition = closure_model({"type": "any"})
    definition["attributes"] = {"*": {"type": "integer"}}
    validator = closure_generated_validator(definition, dialect)
    value = closure_document({"open": True})
    value["extra"] = 7
    validator.validate(value)
    value["extra"] = "bad"
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(value)


@pytest.mark.parametrize("dialect", ["json-schema", "openapi"])
def test_closure_keeps_enum_scope_and_case_insensitive_selection(dialect):
    definition = conditional_definition()
    # Selector activation is a separate rule from enum membership, so this
    # fixture uses an advisory value set. Strict scalar membership itself is
    # covered by the scalar attribute value set section.
    definition["attributes"]["kind"]["enum"] = ["alpha"]
    definition["attributes"]["kind"]["strict"] = False
    definition["attributes"]["kind"]["ifvalues"].pop("beta")
    validator = closure_generated_validator(closure_model(definition), dialect)
    validator.validate(closure_document({"kind": "other"}))
    validator.validate(closure_document({"kind": "ALPHA"}))
    validator.validate(closure_document({"kind": "ALPHA", "alpha": {"name": "http"}}))
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(closure_document({"kind": "ALPHAX", "alpha": {"name": "http"}}))
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(closure_document({"kind": "alpha", "alpha": {"name": "http"},
                                     "unmodeled": True}))


@pytest.mark.parametrize("dialect", ["json-schema", "openapi"])
def test_conditional_alternatives_can_declare_the_same_name_with_distinct_types(dialect):
    definition = {"type": "object", "attributes": {
        "kind": {"type": "string", "ifvalues": {
            "text": {"siblingattributes": {"detail": {"type": "string"}}},
            "count": {"siblingattributes": {"detail": {"type": "integer"}}},
        }},
    }}
    validator = closure_generated_validator(closure_model(definition), dialect)
    validator.validate(closure_document({"kind": "text", "detail": "ok"}))
    validator.validate(closure_document({"kind": "count", "detail": 7}))
    for value in (
        {"kind": "text", "detail": 7},
        {"kind": "count", "detail": "bad"},
        {"kind": "other", "detail": 7},
    ):
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(closure_document(value))


@pytest.mark.parametrize("dialect", ["json-schema", "openapi"])
def test_cli_root_model_attributes_participate_in_full_document_closure(tmp_path, dialect):
    definition = closure_model(copy.deepcopy(CLOSED_LEAF))
    definition["attributes"] = {"rootdata": copy.deepcopy(CLOSED_LEAF)}
    source = tmp_path / "model.json"
    source.write_text(json.dumps(definition), encoding="utf-8")
    original = source.read_bytes()
    output = tmp_path / "schema.json"
    result = subprocess.run(
        [sys.executable, "-B", str(ROOT / "tools" / "schema-generator.py"),
         "--type", dialect, "--output", str(output), str(source)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert source.read_bytes() == original
    schema = json.loads(output.read_text(encoding="utf-8"))
    if dialect == "openapi":
        reference = schema["paths"]["/"]["get"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
        schema = {**reference, "components": schema["components"]}
    validator = jsonschema.Draft7Validator(schema)
    value = closure_document({"name": "http"})
    value["rootdata"] = {"name": "root"}
    validator.validate(value)
    value["rootdata"]["unmodeled"] = True
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(value)


@pytest.mark.parametrize("dialect", ["json-schema", "openapi"])
def test_closure_does_not_close_opaque_resource_document_content(dialect):
    definition = closure_model({"type": "any"})
    definition["groups"]["catalogs"]["resources"] = {"entries": {
        "singular": "entry", "hasdocument": True, "maxversions": 0,
        "attributes": {"data": copy.deepcopy(CLOSED_LEAF)},
    }}
    validator = closure_generated_validator(definition, dialect)
    value = closure_document({})
    value["catalogs"]["c"]["entries"] = {"e": {"versions": {"v1": {
        "entryid": "e", "versionid": "v1", "data": {"name": "metadata"},
        "entry": {"arbitrary": {"document": [7, {"unmodeled": True}]}},
    }}}}
    validator.validate(value)
    invalid = copy.deepcopy(value)
    invalid["catalogs"]["c"]["entries"]["e"]["versions"]["v1"]["data"]["extra"] = 7
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(invalid)


@pytest.mark.parametrize("dialect", ["json-schema", "openapi"])
@pytest.mark.parametrize("maxversions", [0, 1])
def test_group_and_version_wildcards_do_not_reopen_nested_closed_objects(
    dialect, maxversions
):
    definition = closure_model(copy.deepcopy(CLOSED_LEAF))
    group = definition["groups"]["catalogs"]
    group["attributes"]["*"] = {"type": "any"}
    group["resources"] = {"entries": {
        "singular": "entry", "hasdocument": False, "maxversions": maxversions,
        "attributes": {"*": {"type": "any"}},
    }}
    validator = closure_generated_validator(definition, dialect)
    value = closure_document({"name": "closed"})
    value["catalogs"]["c"].update({
        "group_extension": {"nested": [7, True]},
        "entries": {"e": {
            "entryid": "e", "resource_extension": {"nested": True},
            "meta": closure_entry_meta(),
            "versions": {"v1": {
                "entryid": "e", "versionid": "v1",
                "version_extension": {"nested": [7, {"anything": True}]},
            }},
        }},
    })
    validator.validate(value)
    for path in ((), ("catalogs", "c", "payload"),
                 ("catalogs", "c", "entries", "e", "meta")):
        invalid = copy.deepcopy(value)
        target = invalid
        for part in path:
            target = target[part]
        target["unmodeled"] = True
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(invalid)


@pytest.mark.parametrize("dialect", ["json-schema", "openapi"])
def test_published_root_schema_hint_is_a_message_member(dialect):
    filename = "openapi.json" if dialect == "openapi" else "document-schema.json"
    schema = json.loads((ROOT / "schema" / "schemas" / filename).read_text(encoding="utf-8"))
    if dialect == "openapi":
        reference = schema["paths"]["/"]["get"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
        checker = OAS30ReadValidator({
            **reference, "components": schema["components"],
        }, format_checker=OAS30ReadValidator.FORMAT_CHECKER)
    else:
        checker = jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker())
    value = closure_document({})
    del value["catalogs"]
    value["$schema"] = "https://example.com/schema.json"
    before = copy.deepcopy(value)
    checker.validate(value)
    with pytest.raises(jsonschema.ValidationError):
        checker.validate({**value, "$schema": 7})
    assert value == before


@pytest.mark.parametrize("method", ["get", "put"])
def test_schema_hints_follow_single_entity_message_boundaries_not_nested_objects(method):
    definition = {"groups": {"catalogs": {
        "singular": "catalog",
        "attributes": {"settings": {"type": "object", "attributes": {}}},
        "resources": {"entries": {"singular": "entry", "hasdocument": False, "maxversions": 1}},
    }}}
    jsonschema.Draft7Validator(json.loads(
        (ROOT / "core" / "model.schema.json").read_text(encoding="utf-8")
    )).validate(definition)
    schema = GENERATOR.generate_openapi(copy.deepcopy(definition))
    values = [
        ("/", {key: value for key, value in closure_document({}).items() if key != "catalogs"}),
        ("/catalogs/{groupid}", {"settings": {}}),
        ("/catalogs/{groupid}/entries/{resourceid}", {}),
        ("/catalogs/{groupid}/entries/{resourceid}/meta", closure_entry_meta() if method == "get" else {}),
    ]
    if method == "get":
        values.append(("/catalogs/{groupid}/entries/{resourceid}/versions/{versionid}", {}))
    implementation = OAS30ReadValidator if method == "get" else OAS30WriteValidator
    for path, value in values:
        operation = schema["paths"][path][method]
        message = operation["responses"]["200"] if method == "get" else operation["requestBody"]
        checker = implementation({
            **message["content"]["application/json"]["schema"], "components": schema["components"],
        }, format_checker=implementation.FORMAT_CHECKER)
        value["$schema"] = "https://example.com/message.json"
        before = copy.deepcopy(value)
        checker.validate(value)
        with pytest.raises(jsonschema.ValidationError):
            checker.validate({**value, "$schema": False})
        assert value == before
    root = values[0][1]
    root["catalogs"] = {"c": {"entries": {"e": {
        "versions": {"v1": {}}, "meta": closure_entry_meta() if method == "get" else {},
    }}}}
    operation = schema["paths"]["/"][method]
    message = operation["responses"]["200"] if method == "get" else operation["requestBody"]
    checker = implementation({
        **message["content"]["application/json"]["schema"], "components": schema["components"],
    })
    checker.validate(root)
    for path in (
        ("catalogs", "c"), ("catalogs", "c", "entries", "e"),
        ("catalogs", "c", "entries", "e", "versions", "v1"),
        ("catalogs", "c", "entries", "e", "meta"),
    ):
        invalid = copy.deepcopy(root)
        owner = invalid
        for part in path:
            owner = owner[part]
        owner["$schema"] = "https://example.com/not-a-message.json"
        with pytest.raises(jsonschema.ValidationError):
            checker.validate(invalid)
    invalid = copy.deepcopy(root)
    invalid["catalogs"]["c"]["settings"] = {"$schema": "https://example.com/not-a-message.json"}
    with pytest.raises(jsonschema.ValidationError):
        checker.validate(invalid)
    invalid = copy.deepcopy(root)
    invalid["catalogs"]["$schema"] = "https://example.com/not-a-message.json"
    with pytest.raises(jsonschema.ValidationError):
        checker.validate(invalid)
    collection = schema["paths"]["/catalogs/{groupid}/entries/{resourceid}/versions"]["post"]
    checker = OAS30WriteValidator({
        **collection["requestBody"]["content"]["application/json"]["schema"],
        "components": schema["components"],
    })
    checker.validate({"v1": {}})
    for invalid in (
        {"$schema": "https://example.com/not-a-message.json"},
        {"v1": {"$schema": "https://example.com/not-a-message.json"}},
    ):
        with pytest.raises(jsonschema.ValidationError):
            checker.validate(invalid)


# ========================================================================
# JSON Structure dynamic object projection
# Originally tools/test_json_structure_dynamic_maps.py
# Renamed to keep this section's bindings distinct: contract_validator -> dynmaps_contract_validator, document -> dynmaps_document, model -> dynmaps_model
# ========================================================================

VALIDATION = "JSONStructureValidation"


ANY_OBJECT = {"type": "object", "attributes": {"*": {"type": "any"}}}


def dynmaps_model(parameters):
    return {"groups": {"catalogs": {
        "singular": "catalog",
        "attributes": {"parameters": parameters},
    }}}


def dynmaps_document(parameters):
    return {"catalogs": {"c": {"parameters": parameters}}}


def parameter_schema(schema):
    return schema["definitions"]["Catalogs"]["Catalog"]["properties"]["parameters"]


def dynmaps_contract_validator(schema):
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
    schema = GENERATOR.generate_json_structure(dynmaps_model(copy.deepcopy(ANY_OBJECT)))
    assert parameter_schema(schema) == {"type": "map", "values": {"type": "any"}}
    assert schema["$uses"] == ["JSONStructureAlternateNames"]
    dynmaps_contract_validator(schema)


@pytest.mark.parametrize("parameters", [{}, {"mode": "read"}, {
    "nested": {"object": [7, True, None, {"items": ["x"]}]},
}])
def test_dynamic_parameters_preserve_empty_and_nested_object_data(parameters):
    definition = dynmaps_model(copy.deepcopy(ANY_OBJECT))
    original = copy.deepcopy(definition)
    schema = GENERATOR.generate_json_structure(definition)
    assert definition == original
    validator = dynmaps_contract_validator(schema)
    value = dynmaps_document(copy.deepcopy(parameters))
    before = copy.deepcopy(value)
    validator.validate(value)
    assert value == before


@pytest.mark.parametrize("parameters", [None, [], 7, "text", True])
def test_dynamic_map_rejects_non_object_instances(parameters):
    schema = GENERATOR.generate_json_structure(dynmaps_model(copy.deepcopy(ANY_OBJECT)))
    with pytest.raises(jsonschema.ValidationError):
        dynmaps_contract_validator(schema).validate(dynmaps_document(parameters))


@pytest.mark.parametrize("required", [False, True])
def test_dynamic_parameters_preserve_required_and_optional_presence(required):
    definition = {**copy.deepcopy(ANY_OBJECT), "required": required}
    schema = GENERATOR.generate_json_structure(dynmaps_model(definition))
    validator = dynmaps_contract_validator(schema)
    validator.validate(dynmaps_document({}))
    absent = {"catalogs": {"c": {}}}
    if required:
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(absent)
    else:
        validator.validate(absent)
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(dynmaps_document(None))


@pytest.mark.parametrize("definition", [
    {"type": "object"}, {"type": "object", "attributes": {}},
])
@pytest.mark.parametrize("required", [False, True])
def test_closed_empty_objects_use_zero_entry_maps_not_open_maps(definition, required):
    definition = {**definition, "required": required}
    schema = GENERATOR.generate_json_structure(dynmaps_model(definition))
    assert parameter_schema(schema) == {
        "type": "map", "values": {"type": "any"}, "maxEntries": 0,
    }
    assert VALIDATION in schema["$uses"]
    validator = dynmaps_contract_validator(schema)
    validator.validate(dynmaps_document({}))
    absent = {"catalogs": {"c": {}}}
    if required:
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(absent)
    else:
        validator.validate(absent)
    for value in ({"extra": None}, {"extra": 7}, [], None, 7):
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(dynmaps_document(value))


def test_empty_registry_projection_uses_the_same_closed_empty_contract():
    schema = GENERATOR.generate_json_structure({})
    assert schema["type"] == "map"
    assert schema["maxEntries"] == 0
    validator = dynmaps_contract_validator(schema)
    validator.validate({})
    for value in ({"extra": True}, [], None):
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(value)


@pytest.mark.parametrize("open_object", [False, True])
def test_named_objects_remain_structured_with_their_declared_members(open_object):
    attributes = {"name": {"type": "string", "required": True}}
    if open_object:
        attributes["*"] = {"type": "any"}
    schema = GENERATOR.generate_json_structure(dynmaps_model({
        "type": "object", "attributes": attributes,
    }))
    parameters = parameter_schema(schema)
    assert parameters["type"] == "object"
    assert parameters["required"] == ["name"]
    assert parameters["additionalProperties"] is open_object
    validator = dynmaps_contract_validator(schema)
    validator.validate(dynmaps_document({"name": "http"}))
    extra = dynmaps_document({"name": "http", "extra": {"arbitrary": [7]}})
    if open_object:
        validator.validate(extra)
    else:
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(extra)
    for value in ({}, {"name": 7}, []):
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(dynmaps_document(value))


def test_named_optional_properties_still_allow_an_empty_instance():
    schema = GENERATOR.generate_json_structure(dynmaps_model({
        "type": "object", "attributes": {"name": {"type": "string"}},
    }))
    assert parameter_schema(schema)["type"] == "object"
    validator = dynmaps_contract_validator(schema)
    validator.validate(dynmaps_document({}))
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(dynmaps_document({"extra": True}))


def test_typed_dynamic_values_keep_their_reusable_schema_and_constraints():
    definition = {"type": "object", "attributes": {"*": {
        "type": "object", "attributes": {
            "name": {"type": "string", "required": True},
        },
    }}}
    schema = GENERATOR.generate_json_structure(dynmaps_model(definition))
    parameters = parameter_schema(schema)
    assert parameters["type"] == "map"
    assert "$ref" in parameters["values"]["type"]
    validator = dynmaps_contract_validator(schema)
    validator.validate(dynmaps_document({"first": {"name": "one"}, "second": {"name": "two"}}))
    for value in ({"first": {}}, {"first": {"name": 7}},
                  {"first": {"name": "one", "extra": True}}):
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(dynmaps_document(value))


def test_named_plus_typed_wildcard_is_not_rewritten_as_a_dynamic_map():
    schema = GENERATOR.generate_json_structure(dynmaps_model({
        "type": "object", "attributes": {
            "name": {"type": "string", "required": True},
            "*": {"type": "integer"},
        },
    }))
    parameters = parameter_schema(schema)
    assert parameters["type"] == "object"
    assert parameters["properties"] == {"name": {"type": "string"}}
    assert parameters["required"] == ["name"]
    validator = dynmaps_contract_validator(schema)
    validator.validate(dynmaps_document({"name": "http"}))
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(dynmaps_document({"name": 7}))


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
    validator = dynmaps_contract_validator(schema)
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
    definition = dynmaps_model({**copy.deepcopy(ANY_OBJECT), "namecharset": "strict"})
    before = copy.deepcopy(definition)
    schema = GENERATOR.generate_json_structure(definition)
    assert definition == before
    parameters = parameter_schema(schema)
    assert "keyNames" not in parameters and "propertyNames" not in parameters
    dynmaps_contract_validator(schema).validate(dynmaps_document({"not a Core attribute name": 7}))


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
        dynmaps_contract_validator(schema)


def test_open_map_can_contain_independently_closed_empty_values():
    schema = GENERATOR.generate_json_structure(dynmaps_model({
        "type": "object", "attributes": {"*": {"type": "object"}},
    }))
    parameters = parameter_schema(schema)
    assert parameters["type"] == "map" and "maxEntries" not in parameters
    assert "$ref" in parameters["values"]["type"]
    validator = dynmaps_contract_validator(schema)
    validator.validate(dynmaps_document({"first": {}, "second": {}}))
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(dynmaps_document({"first": {"extra": 7}}))


@pytest.mark.parametrize("kind", ["array", "map"])
def test_dynamic_objects_as_collection_items_keep_valid_references(kind):
    schema = GENERATOR.generate_json_structure(dynmaps_model({
        "type": kind, "item": copy.deepcopy(ANY_OBJECT),
    }))
    item = parameter_schema(schema)["items" if kind == "array" else "values"]
    assert "$ref" in item["type"]
    validator = dynmaps_contract_validator(schema)
    value = [{"nested": [7]}, {}] if kind == "array" else {
        "first": {"nested": [7]}, "second": {},
    }
    validator.validate(dynmaps_document(value))
    invalid = [7] if kind == "array" else {"first": 7}
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(dynmaps_document(invalid))


def test_cli_emits_dynamic_and_closed_empty_contracts_without_mutating_source(tmp_path):
    definition = dynmaps_model({
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
    validator = dynmaps_contract_validator(schema)
    validator.validate(dynmaps_document({"open": {"extra": True}, "closed": {}}))
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(dynmaps_document({"closed": {"extra": True}}))


# ========================================================================
# Typed wildcards on named JSON Structure objects
# Originally tools/test_json_structure_typed_wildcards.py
# Renamed to keep this section's bindings distinct: contract_validator -> wildcards_contract_validator, model -> wildcards_model
# ========================================================================

def wildcards_model(wildcard):
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


def wildcards_contract_validator(schema):
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
    source = wildcards_model(wildcard)
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
    checker = wildcards_contract_validator(schema)
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
    schema = GENERATOR.generate_json_structure(wildcards_model(wildcard))
    assert settings_schema(schema)["additionalProperties"] is (wildcard is not None)
    checker = wildcards_contract_validator(schema)
    value = {"catalogs": {"c": {"settings": {"display-name": "http", "extra": extra}}}}
    if accepted:
        checker.validate(value)
    else:
        with pytest.raises(jsonschema.ValidationError):
            checker.validate(value)
    with pytest.raises(jsonschema.ValidationError):
        checker.validate({"catalogs": {"c": {"settings": {"display-name": 7}}}})


def test_typed_object_wildcard_uses_a_resolved_closed_definition():
    schema = GENERATOR.generate_json_structure(wildcards_model({
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
        wildcards_contract_validator(schema).validate({"catalogs": {"c": {"settings": {
            "display-name": "http", "extra": {"count": 7, "unmodeled": True},
        }}}})


# ========================================================================
# OpenAPI request roles and Resource Meta schemas
# Originally tools/test_openapi_operation_meta.py
# ========================================================================

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
            document = content["application/json"]["schema"]
            assert "$ref" not in document
            for reference in ("entry", "entryWriteInput", "entryResourceVersionWriteInput"):
                assert f"#/components/schemas/{reference}" not in json.dumps(document)
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


DOMAIN_DOCUMENTS = [
    {"versionid": 7},
    {"meta": "text", "versionsurl": 12, "epoch": "not a number"},
    {"unmodeled": {"nested": [1, 2]}},
    [1, 2, 3],
    "plain text",
    42,
    True,
]


IGNORED_RESOURCE_VALUES = [
    {"versionscount": 2},
    {"versionsurl": "https://example.com/catalogs/c/entries/e/versions"},
    {"metaurl": "https://example.com/catalogs/c/entries/e/meta"},
    {"versionscount": "not an integer", "versionsurl": 7, "metaurl": False},
]


def body_content(openapi, path, method):
    return openapi["paths"][path][method]["requestBody"]["content"]


def response_content(openapi, path, method, status):
    return openapi["paths"][path][method]["responses"][status]["content"]


def body_checker(openapi, path, method):
    return validator(openapi, body_content(openapi, path, method)["application/json"]["schema"])


def response_checker(openapi, path, method, status):
    return validator(
        openapi,
        response_content(openapi, path, method, status)["application/json"]["schema"],
        read=True,
    )


def route_model(group, maxversions, hasdocument):
    model = envelope_model(maxversions, hasdocument)
    if group == "catalogs":
        del model["groups"]["mirrors"]
    return model


def parameter_refs(openapi, path, method):
    return {
        parameter.get("$ref")
        for parameter in openapi["paths"][path][method].get("parameters", [])
    }


def version_response_reference(maxversions):
    return "#/components/schemas/entry" + ("" if maxversions == 1 else "Version")


def core_version(maxversions, hasdocument, versionid="v1"):
    value = {
        "entryid": "e", "versionid": versionid,
        "self": "https://example.com/catalogs/c/entries/e/versions/v1",
        "xid": "/catalogs/c/entries/e/versions/v1",
        "epoch": 1, "isdefault": True, "ancestorid": versionid,
        "createdat": STAMP, "modifiedat": STAMP,
    }
    if hasdocument:
        value["entry"] = {"example": 1}
    return value


ROUTE_CASES = [
    (group, maxversions, hasdocument)
    for group in ("catalogs", "mirrors")
    for maxversions in (0, 1)
    for hasdocument in (False, True)
]


@pytest.mark.parametrize("group, maxversions, hasdocument", ROUTE_CASES)
def test_details_routes_expose_metadata_write_operations(group, maxversions, hasdocument):
    schema = generate(route_model(group, maxversions, hasdocument))
    assert not list(OpenAPIV30SpecValidator(schema).iter_errors())
    details = schema["paths"][f"/{group}/{{groupid}}/entries/{{resourceid}}$details"]
    assert {"get", "put", "post"} <= set(details)
    assert "patch" not in details and "delete" not in details
    identifiers = [
        operation["operationId"]
        for item in schema["paths"].values()
        for method, operation in item.items()
        if method in ("get", "put", "post", "patch", "delete")
    ]
    assert len(identifiers) == len(set(identifiers))
    name = operation_name(group)
    for method in ("put", "post"):
        assert details[method]["operationId"] == f"{method}{name}Details"
        assert "#/components/parameters/ignore" in parameter_refs(schema, details_path(group), method)
        assert "#/components/parameters/version-epoch" not in parameter_refs(
            schema, details_path(group), method
        )
        assert "application/octet-stream" not in body_content(schema, details_path(group), method)


def operation_name(group):
    # Declared routes are named from the Resource singular; imported routes keep
    # the generator's existing plural-based naming.
    return "CatalogEntry" if group == "catalogs" else "MirrorEntries"


def details_path(group):
    return f"/{group}/{{groupid}}/entries/{{resourceid}}$details"


def bare_path(group):
    return f"/{group}/{{groupid}}/entries/{{resourceid}}"


@pytest.mark.parametrize("group, maxversions, hasdocument", ROUTE_CASES)
def test_details_put_uses_resource_metadata_input(group, maxversions, hasdocument):
    schema = generate(route_model(group, maxversions, hasdocument))
    path = details_path(group)
    assert body_content(schema, path, "put")["application/json"]["schema"] == {
        "$ref": "#/components/schemas/entryWriteInput",
    }
    checker = body_checker(schema, path, "put")
    checker.validate({})
    checker.validate({"entryid": "e", "name": "entry", "epoch": 1})
    checker.validate({
        "self": 7, "xid": False, "metaurl": [], "versionsurl": {}, "versionscount": "x",
        "isdefault": "ignored", "formatvalidated": 7,
    })
    for invalid in ({"name": 7}, {"contenttype": 7}, {"versionid": 7}, {"unmodeled": 1}):
        with pytest.raises(jsonschema.ValidationError):
            checker.validate(invalid)


@pytest.mark.parametrize("group, maxversions, hasdocument", ROUTE_CASES)
def test_details_post_creates_a_version_with_core_ignored_resource_values(
    group, maxversions, hasdocument
):
    schema = generate(route_model(group, maxversions, hasdocument))
    path = details_path(group)
    assert body_content(schema, path, "post")["application/json"]["schema"] == {
        "$ref": "#/components/schemas/entryResourceVersionWriteInput",
    }
    checker = body_checker(schema, path, "post")
    checker.validate({})
    checker.validate({"versionid": "1", "ancestorid": "1", "contenttype": "application/json"})
    for ignored in IGNORED_RESOURCE_VALUES:
        checker.validate({"versionid": "1", **ignored})
    for invalid in (
        {"versions": {"v1": {}}}, {"meta": {"defaultversionid": "v1"}},
        {"contenttype": 7}, {"versionid": 7}, {"unmodeled": 1},
    ):
        with pytest.raises(jsonschema.ValidationError):
            checker.validate(invalid)


@pytest.mark.parametrize("group, maxversions, hasdocument", ROUTE_CASES)
def test_details_post_returns_version_fields_not_resource_navigation(
    group, maxversions, hasdocument
):
    schema = generate(route_model(group, maxversions, hasdocument))
    path = details_path(group)
    assert response_content(schema, path, "post", "200")["application/json"]["schema"] == {
        "$ref": version_response_reference(maxversions),
    }
    checker = response_checker(schema, path, "post", "200")
    version = core_version(maxversions, hasdocument)
    checker.validate(version)
    for invalid in ({"versionid": 7}, {"unmodeled": True}):
        with pytest.raises(jsonschema.ValidationError):
            checker.validate({**version, **invalid})
    assert response_content(schema, path, "put", "200")["application/json"]["schema"] == {
        "$ref": "#/components/schemas/entry",
    }


@pytest.mark.parametrize("group", ["catalogs", "mirrors"])
@pytest.mark.parametrize("maxversions", [0, 1])
def test_bare_document_routes_carry_domain_documents_not_metadata(group, maxversions):
    schema = generate(route_model(group, maxversions, True))
    path = bare_path(group)
    messages = [
        body_content(schema, path, "put"), body_content(schema, path, "post"),
        response_content(schema, path, "get", "200"),
        response_content(schema, path, "put", "200"),
        response_content(schema, path, "post", "201"),
    ]
    for content in messages:
        assert "$ref" not in content["application/json"]["schema"]
        checker = validator(schema, content["application/json"]["schema"])
        for document in DOMAIN_DOCUMENTS:
            checker.validate(document)
    binary = [message for message in messages if "application/octet-stream" in message]
    assert len(binary) == 4
    for content in binary:
        assert content["application/octet-stream"]["schema"] == {
            "type": "string", "format": "binary",
        }
    for method in ("put", "post"):
        assert "#/components/parameters/version-epoch" in parameter_refs(schema, path, method)
    assert "resource-id" in schema["paths"][path]["get"]["responses"]["200"]["headers"]
    assert "resource-version" in schema["paths"][path]["post"]["responses"]["201"]["headers"]


@pytest.mark.parametrize("group", ["catalogs", "mirrors"])
@pytest.mark.parametrize("maxversions", [0, 1])
def test_metadata_only_resources_treat_the_bare_route_as_metadata(group, maxversions):
    schema = generate(route_model(group, maxversions, False))
    path = bare_path(group)
    assert body_content(schema, path, "put")["application/json"]["schema"] == {
        "$ref": "#/components/schemas/entryWriteInput",
    }
    assert body_content(schema, path, "post")["application/json"]["schema"] == {
        "$ref": "#/components/schemas/entryResourceVersionWriteInput",
    }
    for method in ("put", "post"):
        checker = body_checker(schema, path, method)
        with pytest.raises(jsonschema.ValidationError):
            checker.validate({"versionid": 7})
        with pytest.raises(jsonschema.ValidationError):
            checker.validate({"unmodeled": True})


@pytest.mark.parametrize("group, maxversions, hasdocument", ROUTE_CASES)
def test_metadata_routes_and_collections_remain_typed(group, maxversions, hasdocument):
    schema = generate(route_model(group, maxversions, hasdocument))
    details = details_path(group)
    meta = bare_path(group) + "/meta"
    versions = bare_path(group) + "/versions"
    assert response_content(schema, details, "get", "200")["application/json"]["schema"] == {
        "$ref": "#/components/schemas/entry",
    }
    assert body_content(schema, meta, "put")["application/json"]["schema"] == {
        "$ref": "#/components/schemas/entryMetaWriteInput",
    }
    assert body_content(schema, meta, "patch")["application/json"]["schema"] == {
        "$ref": "#/components/schemas/entryMetaPatchInput",
    }
    body_checker(schema, meta, "patch").validate({})
    with pytest.raises(jsonschema.ValidationError):
        body_checker(schema, meta, "patch").validate({"defaultversionsticky": "true"})
    assert body_content(schema, versions, "post")["application/json"]["schema"][
        "additionalProperties"
    ] == nested_reference("#/components/schemas/entryVersionWriteInput")
    with pytest.raises(jsonschema.ValidationError):
        body_checker(schema, details, "put").validate({"versionid": 7})


def nested_reference(reference):
    return GENERATOR.nested_entity_schema({"$ref": reference})


@pytest.mark.parametrize("artifact, plural, singular, document, metadata_paths", [
    ("schema", "schemas", "schema", True, ["/schemagroups/{groupid}/schemas/{resourceid}$details"]),
    ("message", "messages", "message", False, [
        "/messagegroups/{groupid}/messages/{resourceid}",
        "/messagegroups/{groupid}/messages/{resourceid}$details",
    ]),
])
def test_published_artifacts_expose_route_aware_resource_writes(
    artifact, plural, singular, document, metadata_paths
):
    schema = json.loads((ROOT / artifact / "schemas" / "openapi.json").read_text(
        encoding="utf-8"
    ))
    for path in metadata_paths:
        assert body_content(schema, path, "put")["application/json"]["schema"] == {
            "$ref": f"#/components/schemas/{singular}WriteInput",
        }
        assert body_content(schema, path, "post")["application/json"]["schema"] == {
            "$ref": f"#/components/schemas/{singular}ResourceVersionWriteInput",
        }
    if document:
        bare = metadata_paths[0].removesuffix("$details")
        content = body_content(schema, bare, "put")
        assert "$ref" not in content["application/json"]["schema"]
        assert content["application/octet-stream"]["schema"] == {
            "type": "string", "format": "binary",
        }
        validator(schema, content["application/json"]["schema"]).validate({"versionid": 7})


# ========================================================================
# OpenAPI administration surface
# Originally tools/test_openapi_administration.py
# Renamed to keep this section's bindings distinct: _parameters -> admin__parameters, document -> admin_document
# ========================================================================

HTTP_METHODS = {"get", "put", "post", "patch", "delete", "head", "options", "trace"}


AVAILABLE = {
    "capabilities": {"mutable": False},
    "entities": {"mutable": True},
    "model": {"mutable": False},
}


@pytest.fixture(scope="module", params=MODELS)
def admin_document(request, tmp_path_factory):
    name = request.param
    output = tmp_path_factory.mktemp(f"administration-{name}") / "openapi.json"
    result = subprocess.run(
        [
            sys.executable, str(ROOT / "tools" / "schema-generator.py"),
            "--type", "openapi", "--output", str(output),
            *(str(ROOT / model / "model.json") for model in MODELS[name]),
        ],
        cwd=ROOT, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    generated = json.loads(output.read_text(encoding="utf-8"))
    published = json.loads((ROOT / name / "schemas" / "openapi.json").read_text(encoding="utf-8"))
    assert generated == published
    return generated


def _schema(admin_document, name):
    if name not in admin_document["components"]["schemas"]:
        pytest.fail(f"Missing administrative schema component: {name}", pytrace=False)
    return jsonschema.Draft7Validator({
        "$ref": f"#/components/schemas/{name}",
        "components": admin_document["components"],
    })


def admin__parameters(admin_document, operation):
    return [
        admin_document["components"]["parameters"][item["$ref"].rsplit("/", 1)[1]]
        if "$ref" in item else item
        for item in operation.get("parameters", [])
    ]


def test_administrative_methods_match_the_binding(admin_document):
    expected = {
        "/capabilities": {"get", "put", "patch"},
        "/capabilitiesoffered": {"get"},
        "/model": {"get"},
        "/modelsource": {"get", "put"},
        "/export": {"get"},
    }
    for path, methods in expected.items():
        assert set(admin_document["paths"][path]) & HTTP_METHODS == methods
    assert admin_document["paths"]["/modelsource"]["put"]["operationId"] == "putRegistryModelSource"
    assert admin_document["paths"]["/modelsource"]["get"]["operationId"] == "getRegistryModelSource"


def test_obsolete_administrative_query_switches_are_not_advertised(admin_document):
    for path in ("/capabilities", "/capabilitiesoffered", "/model", "/modelsource"):
        for method in set(admin_document["paths"][path]) & HTTP_METHODS:
            names = {item["name"] for item in admin__parameters(admin_document, admin_document["paths"][path][method])}
            expected = {"specversion"}
            if method in {"put", "patch", "post", "delete"}:
                expected.add("ignore")
            assert names == expected


def test_modelsource_empty_object_is_valid_but_a_body_is_required(admin_document):
    put = admin_document["paths"]["/modelsource"]["put"]
    assert put["requestBody"]["required"] is True
    schema = put["requestBody"]["content"]["application/json"]["schema"]
    jsonschema.Draft7Validator(schema).validate({})
    for invalid in (None, [], ""):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.Draft7Validator(schema).validate(invalid)


def test_export_exposes_the_inline_parameter(admin_document):
    get = admin_document["paths"]["/export"]["get"]
    assert "inline" in {item["name"] for item in admin__parameters(admin_document, get)}


def test_capability_request_and_response_schemas_have_distinct_presence_rules(admin_document):
    expected = {"available", "compatibilities", "flags", "formats", "ignores", "mutable",
                "pagination", "shortself", "specversions", "versionmodes"}
    component = admin_document["components"]["schemas"]["RegistryCapabilities"]
    assert set(component["properties"]) == expected
    assert component["additionalProperties"] is True
    for method in ("put", "patch"):
        operation = admin_document["paths"]["/capabilities"][method]
        assert operation["requestBody"]["required"] is True
        assert operation["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith(
            "/RegistryCapabilities"
        )
    request = _schema(admin_document, "RegistryCapabilities")
    request.validate({})
    request.validate({"shortself": True})
    response = _schema(admin_document, "RegistryCapabilitiesResponse")
    with pytest.raises(jsonschema.ValidationError):
        response.validate({})
    response.validate({"available": AVAILABLE})
    for method in ("get", "put", "patch"):
        assert admin_document["paths"]["/capabilities"][method]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]["$ref"].endswith("/RegistryCapabilitiesResponse")


@pytest.mark.parametrize(
    "available",
    [[], ["/model"], {"model": False}, {"model": {}}, {"model": {"mutable": "false"}}],
)
def test_available_rejects_legacy_arrays_and_wrong_entry_types(admin_document, available):
    with pytest.raises(jsonschema.ValidationError):
        _schema(admin_document, "RegistryCapabilities").validate({"available": available})


def test_current_capabilities_preserve_extensions_and_case_insensitive_values(admin_document):
    _schema(admin_document, "RegistryCapabilitiesResponse").validate({
        "available": {
            **AVAILABLE,
            "MODELSOURCE": {"mutable": True, "vendor_hint": "allowed"},
        },
        "compatibilities": {"JsonSchema*": ["BaCkWaRd"]},
        "flags": ["INLINE", "vendorflag"],
        "formats": ["JsonSchema/draft-07"],
        "ignores": ["EPOCH"],
        "mutable": ["modelsource"],
        "pagination": False,
        "shortself": True,
        "specversions": ["1.0-rc4"],
        "versionmodes": ["MANUAL", "vendor-mode"],
        "vendor-capability": {"limit": 7},
    })


def test_offered_capabilities_are_recursive_definitions_not_current_values(admin_document):
    offered = {
        "available": {
            "type": "object",
            "attributes": {"model": {
                "type": "object",
                "attributes": {"mutable": {"type": "boolean", "enum": [False]}},
            }},
        },
        "flags": {"type": "array", "item": {"type": "string"}, "enum": ["inline"]},
        "vendor-map": {"type": "MAP", "item": {"type": "integer"}, "min": 0},
        "pagination": {"type": "boolean", "enum": [False, True]},
    }
    _schema(admin_document, "RegistryCapabilitiesOffered").validate(offered)
    reference = admin_document["paths"]["/capabilitiesoffered"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    assert reference.endswith("/RegistryCapabilitiesOffered")


@pytest.mark.parametrize(
    "definition",
    [True, [], {}, {"type": 7}, {"type": "array"}, {"type": "MAP", "item": {}},
     {"type": "object", "attributes": {"mutable": False}}],
)
def test_offered_capability_definitions_reject_value_maps_and_missing_item_types(admin_document, definition):
    with pytest.raises(jsonschema.ValidationError):
        _schema(admin_document, "RegistryCapabilitiesOffered").validate({"test": definition})


# ========================================================================
# OpenAPI flag and guard parameters
# Originally tools/test_openapi_flags_guards.py
# Renamed to keep this section's bindings distinct: _parameters -> flags__parameters, document -> flags_document
# ========================================================================

WRITE_METHODS = {"put", "patch", "post", "delete"}


METHODS = WRITE_METHODS | {"get"}


def _generate(inputs, output):
    result = subprocess.run(
        [
            sys.executable, str(ROOT / "tools" / "schema-generator.py"),
            "--type", "openapi", "--output", str(output), *map(str, inputs),
        ],
        cwd=ROOT, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(output.read_text(encoding="utf-8"))


@pytest.fixture(scope="module", params=MODELS)
def flags_document(request, tmp_path_factory):
    name = request.param
    output = tmp_path_factory.mktemp(f"flags-{name}") / "openapi.json"
    generated = _generate([ROOT / model / "model.json" for model in MODELS[name]], output)
    published = json.loads((ROOT / name / "schemas" / "openapi.json").read_text(encoding="utf-8"))
    assert generated == published
    return generated


def _operations(flags_document):
    for path, item in flags_document["paths"].items():
        for method in set(item) & METHODS:
            yield path, item, method, item[method]


def flags__parameters(flags_document, item, operation):
    parameters = [*item.get("parameters", []), *operation.get("parameters", [])]
    return [
        flags_document["components"]["parameters"][value["$ref"].rsplit("/", 1)[1]]
        if "$ref" in value else value
        for value in parameters
    ]


def test_obsolete_ignore_and_attribute_query_parameters_are_removed(flags_document):
    obsolete = {"noepoch", "nodefaultversionid", "nodefaultversionsticky", "noreadonly",
                "resource-description", "resource-documentation", "resource-labels"}
    for path, item, method, operation in _operations(flags_document):
        names = {p["name"] for p in flags__parameters(flags_document, item, operation) if p["in"] == "query"}
        assert not names & obsolete, (path, method, names & obsolete)
    assert not obsolete & set(flags_document["components"]["parameters"])


def test_ignore_is_offered_once_on_writes_and_not_on_reads(flags_document):
    for path, item, method, operation in _operations(flags_document):
        ignores = [p for p in flags__parameters(flags_document, item, operation)
                   if p["in"] == "query" and p["name"] == "ignore"]
        assert len(ignores) == (1 if method in WRITE_METHODS else 0), (path, method)
    parameter = flags_document["components"]["parameters"]["ignore"]
    assert parameter["style"] == "form" and parameter["explode"] is True
    assert parameter["allowEmptyValue"] is True
    validator = jsonschema.Draft7Validator(parameter["schema"])
    validator.validate(["epoch", "readonly", "vendor-rule"])
    validator.validate(["*"])
    validator.validate([""])


def test_epoch_query_guards_exist_only_on_optional_single_entity_deletes(flags_document):
    count = 0
    for path, item, method, operation in _operations(flags_document):
        epochs = [p for p in flags__parameters(flags_document, item, operation)
                  if p["in"] == "query" and p["name"] == "epoch"]
        if method != "delete":
            assert epochs == [], (path, method)
            continue
        count += 1
        assert len(epochs) == 1
        assert epochs[0]["required"] is False
        assert epochs[0]["schema"]["minimum"] == 0
    assert count > 0


def test_doc_parameter_accepts_only_empty_string_values(flags_document):
    parameter = flags_document["components"]["parameters"]["doc"]
    assert parameter["allowEmptyValue"] is True
    assert parameter["schema"] == {"type": "string", "enum": [""]}
    validator = jsonschema.Draft7Validator(parameter["schema"])
    validator.validate("")
    for invalid in ("true", "false", True, False):
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(invalid)


def test_epoch_header_accepts_unsigned_values_and_literal_null(flags_document):
    parameter = flags_document["components"]["parameters"].get("version-epoch")
    assert parameter is not None, "Document-view epoch carrier is missing"
    assert parameter["in"] == "header" and parameter["name"] == "xRegistry-epoch"
    assert parameter["required"] is False
    validator = jsonschema.Draft7Validator(parameter["schema"])
    for value in (0, 5, 6, 2 ** 80, "null"):
        validator.validate(value)
    for invalid in (-1, 1.5, True, "NULL", ""):
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(invalid)


def test_document_header_guard_respects_metadata_only_and_imported_resource_types(tmp_path):
    model = {
        "groups": {
            "sources": {
                "singular": "source",
                "resources": {
                    "files": {"singular": "file", "hasdocument": True},
                    "entries": {"singular": "entry", "hasdocument": False},
                },
            },
            "mirrors": {
                "singular": "mirror",
                "ximportresources": ["/sources/files", "/sources/entries"],
            },
        }
    }
    model_path = tmp_path / "model.json"
    model_path.write_text(json.dumps(model), encoding="utf-8")
    flags_document = _generate([model_path], tmp_path / "openapi.json")
    for group in ("sources", "mirrors"):
        for resource, hasdocument in (("files", True), ("entries", False)):
            path = f"/{group}/{{groupid}}/{resource}/{{resourceid}}"
            item = flags_document["paths"][path]
            for method in ("put", "post"):
                headers = [p["name"] for p in flags__parameters(flags_document, item, item[method])
                           if p["in"] == "header"]
                assert ("xRegistry-epoch" in headers) is hasdocument
                assert "xRegistry-meta.epoch" not in headers
            for suffix in ("/meta", "$details"):
                metadata_item = flags_document["paths"][path + suffix]
                for method in set(metadata_item) & METHODS:
                    assert all(
                        p["name"] != "xRegistry-epoch"
                        for p in flags__parameters(flags_document, metadata_item, metadata_item[method])
                    )


# ========================================================================
# OpenAPI problem details responses
# Originally tools/test_openapi_problem_details.py
# ========================================================================

PROBLEM = {"type": "https://example.com/problems/bad-request", "title": "Invalid input"}


@pytest.fixture(scope="module", params=MODELS)
def documents(request, tmp_path_factory):
    name = request.param
    output = tmp_path_factory.mktemp(f"problem-details-{name}") / "openapi.json"
    result = subprocess.run(
        [
            sys.executable, str(ROOT / "tools" / "schema-generator.py"),
            "--type", "openapi", "--output", str(output),
            *(str(ROOT / model / "model.json") for model in MODELS[name]),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    generated = json.loads(output.read_text(encoding="utf-8"))
    published = json.loads((ROOT / name / "schemas" / "openapi.json").read_text(encoding="utf-8"))
    return generated, published


def _validators(documents):
    checker = jsonschema.FormatChecker()
    assert "uri" in checker.checkers, "Install the format dependencies from tools/requirements.txt"
    for document in documents:
        schema = document["components"]["schemas"]["ProblemDetails"]
        yield jsonschema.Draft7Validator(schema, format_checker=checker)


def test_published_openapi_matches_the_generator(documents):
    generated, published = documents
    assert generated == published


def test_type_and_title_without_instance_are_valid(documents):
    for validator in _validators(documents):
        assert validator.schema["required"] == ["type", "title"]
        validator.validate(PROBLEM)


@pytest.mark.parametrize("field", ["type", "title"])
def test_type_and_title_remain_mandatory(documents, field):
    value = {name: item for name, item in PROBLEM.items() if name != field}
    for validator in _validators(documents):
        errors = list(validator.iter_errors(value))
        assert len(errors) == 1
        assert errors[0].validator == "required"
        assert field in errors[0].message


def test_instance_and_extension_fields_remain_optional(documents):
    value = {
        **PROBLEM,
        "instance": "https://example.com/requests/123",
        "detail": "The supplied value is invalid.",
        "subject": "/groups/example",
        "args": {"value": "bad"},
        "source": "validator",
        "extension": {"trace": "external-id"},
    }
    for validator in _validators(documents):
        validator.validate(value)
        assert set(validator.schema["required"]) == {"type", "title"}


@pytest.mark.parametrize(
    "instance,keyword",
    [(None, "type"), (7, "type"), ({}, "type"), ("not a URI", "format")],
)
def test_supplied_instance_keeps_existing_string_and_uri_validation(documents, instance, keyword):
    for validator in _validators(documents):
        errors = list(validator.iter_errors({**PROBLEM, "instance": instance}))
        assert len(errors) == 1
        assert errors[0].validator == keyword
        assert list(errors[0].path) == ["instance"]
