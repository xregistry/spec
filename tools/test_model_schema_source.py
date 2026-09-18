"""Source-stage admission rules of the canonical xRegistry model meta-schema.

These tests exercise `core/model.schema.json` and the staged validator in
`tools/validate-models.py` with real JSON Schema fixtures. They deliberately do
not assert specification prose, and they do not re-implement include resolution
or Core overlay semantics: the expanded stage reuses the generator's real
resolver.
"""

import copy
import importlib.util
import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parent.parent


def _load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATE_MODELS = _load("validate_models", "tools/validate-models.py")
MODEL_SCHEMA = json.loads((ROOT / "core" / "model.schema.json").read_text(encoding="utf-8"))
SOURCE = VALIDATE_MODELS.source_validator(MODEL_SCHEMA)
EXPANDED = VALIDATE_MODELS.expanded_validator(MODEL_SCHEMA)

STRICT_MAX = "a" * 63
EXTENDED_NAMES = ("x-name", "9.name", "a:b", "a.b-c_d")


def accepts(instance, validator=SOURCE):
    before = copy.deepcopy(instance)
    validator.validate(instance)
    assert instance == before


def rejects(instance, validator=SOURCE):
    before = copy.deepcopy(instance)
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(instance)
    assert instance == before


def model(**extra):
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
    return model(attributes={name: definition})


def group_of(model_definition):
    return model_definition["groups"]["catalogs"]


def resource_of(model_definition):
    return group_of(model_definition)["resources"]["entries"]


# --- W03-a: include directives at every permitted Object/Map position --------

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
    definition = model()
    INCLUDE_POSITIONS[position](definition)["$include"] = "other.json#/attributes"
    accepts(definition)


@pytest.mark.parametrize("position", sorted(INCLUDE_POSITIONS))
def test_ordered_includes_directive_is_admitted_at_every_model_object_or_map(position):
    definition = model()
    INCLUDE_POSITIONS[position](definition)["$includes"] = ["a.json", "b.json#/x"]
    accepts(definition)


@pytest.mark.parametrize("position", sorted(INCLUDE_POSITIONS))
def test_both_include_directives_at_one_level_are_rejected(position):
    definition = model()
    target = INCLUDE_POSITIONS[position](definition)
    target["$include"] = "a.json"
    target["$includes"] = ["b.json"]
    rejects(definition)


@pytest.mark.parametrize("position", sorted(INCLUDE_POSITIONS))
def test_include_directive_reference_shape_is_typed(position):
    for bad in ({"$include": ["a.json"]}, {"$includes": "a.json"},
                {"$includes": [7]}):
        definition = model()
        INCLUDE_POSITIONS[position](definition).update(copy.deepcopy(bad))
        rejects(definition)


# --- W03-b: local siblings, overrides and include-only partial definitions ---


def test_group_include_admits_local_sibling_members():
    definition = model()
    group_of(definition).update({"$include": "g.json", "description": "local"})
    accepts(definition)


def test_resource_include_admits_local_sibling_members():
    definition = model()
    resource_of(definition).update({"$include": "r.json", "maxversions": 3})
    accepts(definition)


def test_attribute_map_include_admits_local_sibling_definitions():
    definition = model(attributes={
        "$include": "attrs.json", "local": {"type": "string"},
    })
    accepts(definition)


def test_include_only_group_and_resource_definitions_need_no_local_singular():
    accepts(model(groups={"catalogs": {"$include": "g.json"}}))
    definition = model()
    group_of(definition)["resources"] = {"entries": {"$includes": ["r.json"]}}
    accepts(definition)


def test_group_and_resource_definitions_without_includes_still_need_singular():
    rejects(model(groups={"catalogs": {"description": "no singular"}}))
    definition = model()
    group_of(definition)["resources"] = {"entries": {"description": "x"}}
    rejects(definition)


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


# --- W03-c/o: source overlays versus completed definitions -------------------


def test_source_admits_a_partial_overlay_of_a_specification_defined_attribute():
    accepts(with_attribute({"required": True}, name="name"))
    accepts(with_attribute({"description": "further constrained"}, name="self"))


def test_expanded_stage_rejects_a_definition_that_never_received_a_type():
    definition = with_attribute({"required": True}, name="name")
    accepts(definition)
    rejects(definition, EXPANDED)


def test_expanded_stage_rejects_unresolved_include_directives():
    definition = model(attributes={"$include": "attrs.json"})
    accepts(definition)
    rejects(definition, EXPANDED)


def test_expanded_stage_accepts_completed_definitions():
    accepts(with_attribute({"type": "string"}), EXPANDED)
    accepts(model(attributes={"*": {"type": "any"}}), EXPANDED)


def test_expanded_stage_requires_a_type_on_wildcards_and_nested_definitions():
    rejects(model(attributes={"*": {"description": "x"}}), EXPANDED)
    rejects(with_attribute({
        "type": "object", "attributes": {"inner": {"required": True}},
    }), EXPANDED)
    rejects(with_attribute({
        "type": "string", "ifvalues": {"a": {"siblingattributes": {
            "inner": {"description": "x"}}}},
    }), EXPANDED)
    rejects(with_attribute({"type": "array", "item": {"target": "/catalogs"}}), EXPANDED)


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


# --- W03-d: strict names, underscores, digit starts and length --------------


@pytest.mark.parametrize("name", ["a", "_private", "a_b_9", STRICT_MAX])
def test_strict_attribute_names_admit_letters_underscores_and_digits(name):
    accepts(model(attributes={name: {"type": "string"}}))
    accepts(model(attributes={name: {"type": "string", "name": name}}))


@pytest.mark.parametrize("name", ["1bad", "with-dash", "UPPER", "a" * 64, "a:b", "a.b"])
def test_strict_attribute_names_reject_digit_starts_punctuation_and_overlong(name):
    rejects(model(attributes={name: {"type": "string"}}))


@pytest.mark.parametrize("name", ["1bad", "with-dash", "a" * 64])
def test_explicitly_supplied_strict_names_are_bounded_like_their_keys(name):
    rejects(model(attributes={"payload": {"type": "string", "name": name}}))


# --- W03-e: contextual extended names, including conditional siblings -------


@pytest.mark.parametrize("name", EXTENDED_NAMES)
def test_extended_names_are_admitted_only_under_an_extended_object(name):
    accepts(with_attribute({
        "type": "object", "namecharset": "extended",
        "attributes": {name: {"type": "string", "name": name}},
    }))
    rejects(model(attributes={name: {"type": "string"}}))


@pytest.mark.parametrize("charset", ["extended", "EXTENDED", "Extended"])
def test_extended_charset_selection_is_case_insensitive(charset):
    accepts(with_attribute({
        "type": "object", "namecharset": charset,
        "attributes": {"x-name": {"type": "string"}},
    }))


def test_extended_scope_does_not_leak_into_a_nested_strict_object():
    accepts(with_attribute({
        "type": "object", "namecharset": "extended",
        "attributes": {"x-name": {"type": "object", "attributes": {
            "inner": {"type": "string"}}}},
    }))
    rejects(with_attribute({
        "type": "object", "namecharset": "extended",
        "attributes": {"x-name": {"type": "object", "attributes": {
            "in-ner": {"type": "string"}}}},
    }))


def test_conditional_siblings_follow_the_charset_of_their_own_object():
    rejects(with_attribute({
        "type": "string",
        "ifvalues": {"a": {"siblingattributes": {"x-name": {"type": "string"}}}},
    }))
    accepts(with_attribute({
        "type": "object", "namecharset": "extended",
        "attributes": {"kind": {"type": "string", "ifvalues": {
            "a": {"siblingattributes": {"x-name": {"type": "string"}}}}}},
    }))


def test_extended_item_objects_carry_their_own_charset():
    accepts(with_attribute({
        "type": "map",
        "item": {"type": "object", "namecharset": "extended",
                 "attributes": {"x-name": {"type": "string"}}},
    }))
    rejects(with_attribute({
        "type": "map",
        "item": {"type": "object", "attributes": {"x-name": {"type": "string"}}},
    }))


def test_extended_names_still_respect_the_map_key_length_and_leading_character():
    accepts(with_attribute({
        "type": "object", "namecharset": "extended",
        "attributes": {"a" * 63: {"type": "string"}},
    }))
    rejects(with_attribute({
        "type": "object", "namecharset": "extended",
        "attributes": {"a" * 64: {"type": "string"}},
    }))
    rejects(with_attribute({
        "type": "object", "namecharset": "extended",
        "attributes": {"-lead": {"type": "string"}},
    }))


# --- W03-f/g: Group and Resource name bounds --------------------------------


@pytest.mark.parametrize("length,valid", [(57, True), (58, False)])
def test_group_plural_and_resource_names_are_bounded_at_57(length, valid):
    name = "a" * length
    check = accepts if valid else rejects
    check(model(groups={name: {"singular": "catalog"}}))
    check(model(groups={"catalogs": {"singular": "catalog", "plural": name}}))
    check(model(groups={"catalogs": {"singular": "catalog", "resources": {
        name: {"singular": "entry"}}}}))
    check(model(groups={"catalogs": {"singular": "catalog", "resources": {
        "entries": {"singular": name}}}}))
    check(model(groups={"catalogs": {"singular": "catalog", "resources": {
        "entries": {"singular": "entry", "plural": name}}}}))


@pytest.mark.parametrize("length", [61, 62, 63])
def test_group_singular_follows_current_main_law_of_63(length):
    accepts(model(groups={"catalogs": {"singular": "a" * length}}))


def test_group_singular_rejects_names_above_the_current_main_bound():
    rejects(model(groups={"catalogs": {"singular": "a" * 64}}))


def test_group_and_resource_type_names_admit_leading_underscores():
    accepts(model(groups={"_catalogs": {
        "singular": "_catalog", "resources": {"_entries": {"singular": "_entry"}},
    }}))
    rejects(model(groups={"9catalogs": {"singular": "catalog"}}))


# --- W03-h: target and import grammar ---------------------------------------


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
    accepts(with_attribute({"type": "xid", "target": target}))
    accepts(with_attribute({"type": "array", "item": {"type": "xid", "target": target}}))
    accepts(with_attribute({
        "type": "array",
        "item": {"type": "array", "item": {"type": "xid", "target": target}},
    }))


@pytest.mark.parametrize("target", INVALID_TARGETS)
def test_targets_reject_malformed_type_components_and_depths(target):
    rejects(with_attribute({"type": "xid", "target": target}))
    rejects(with_attribute({"type": "array", "item": {"type": "xid", "target": target}}))


@pytest.mark.parametrize("value,valid", [
    ("/_groups/_resources", True), ("/group_a/resource_b", True),
    ("/catalogs", False), ("/9groups/resources", False),
    ("/groups/resources/versions", False), ("/groups/" + "a" * 58, False),
])
def test_ximportresources_uses_the_same_plural_name_grammar(value, valid):
    definition = model()
    group_of(definition)["ximportresources"] = [value]
    (accepts if valid else rejects)(definition)


@pytest.mark.parametrize("key,valid", [
    ("entries.payload", True), ("_entries.payload.inner", True),
    ("9entries.payload", False), ("entries", False),
    ("a" * 58 + ".payload", False),
])
def test_group_constraint_keys_use_the_resource_plural_name_grammar(key, valid):
    definition = model()
    group_of(definition)["constraints"] = {key: {"equals": "kind"}}
    (accepts if valid else rejects)(definition)


# --- W03-i: defined documentation and icon placements -----------------------


def test_documentation_and_icon_are_defined_where_the_model_shape_defines_them():
    definition = model(description="registry", documentation="https://example.com/d")
    group_of(definition).update({
        "documentation": "https://example.com/g", "icon": "https://example.com/g.png",
    })
    resource_of(definition).update({
        "documentation": "https://example.com/r", "icon": "https://example.com/r.png",
    })
    accepts(definition)


@pytest.mark.parametrize("field", ["documentation", "icon"])
def test_documentation_and_icon_reject_non_string_values(field):
    definition = model()
    group_of(definition)[field] = 5
    rejects(definition)
    definition = model()
    resource_of(definition)[field] = {"url": "https://example.com"}
    rejects(definition)


def test_root_documentation_is_typed_and_no_root_icon_is_introduced():
    rejects(model(documentation=5))
    definition = model(icon="https://example.com/i.png")
    assert "icon" not in MODEL_SCHEMA["properties"]
    accepts(definition)


# --- W03-j: case-insensitive known aspect values -----------------------------


@pytest.mark.parametrize("value", ["strict", "STRICT", "Extended", "extended"])
def test_namecharset_values_are_case_insensitive(value):
    accepts(with_attribute({"type": "object", "namecharset": value, "attributes": {}}))


def test_namecharset_rejects_unknown_character_sets():
    rejects(with_attribute({"type": "object", "namecharset": "loose"}))


@pytest.mark.parametrize("value", ["manual", "MANUAL", "SemVer", "createdat", "ModifiedAt"])
def test_versionmode_values_are_case_insensitive(value):
    definition = model()
    resource_of(definition)["versionmode"] = value
    accepts(definition)


def test_versionmode_rejects_unknown_algorithms():
    definition = model()
    resource_of(definition)["versionmode"] = "newest"
    rejects(definition)


@pytest.mark.parametrize("value", ["json", "JSON", "Binary", "string", "STRING"])
def test_typemap_values_are_case_insensitive_and_keep_binary(value):
    definition = model()
    resource_of(definition)["typemap"] = {"Application/JSON": value}
    accepts(definition)


def test_typemap_rejects_unknown_serialization_kinds():
    definition = model()
    resource_of(definition)["typemap"] = {"application/json": "yaml"}
    rejects(definition)


@pytest.mark.parametrize("type_name", ["String", "STRING", "Integer"])
def test_type_names_remain_case_sensitive_lowercase(type_name):
    rejects(with_attribute({"type": type_name}))


def test_strict_enum_members_are_not_case_folded_by_the_source_schema():
    accepts(with_attribute({"type": "string", "enum": ["Alpha", "alpha"]}))


# --- W03-k: ifvalues selector key shape --------------------------------------


@pytest.mark.parametrize("key", ["", "^reserved"])
def test_ifvalues_keys_reject_empty_and_reserved_caret_selectors(key):
    rejects(with_attribute({
        "type": "string", "ifvalues": {key: {"siblingattributes": {}}},
    }))


def test_ifvalues_branches_require_sibling_attributes_unless_included():
    rejects(with_attribute({"type": "string", "ifvalues": {"a": {}}}))
    accepts(with_attribute({
        "type": "string", "ifvalues": {"a": {"$include": "b.json"}},
    }))


def test_case_duplicate_selectors_remain_a_semantic_check_not_a_source_one():
    definition = with_attribute({"type": "string", "ifvalues": {
        "http": {"siblingattributes": {}},
        "HTTP": {"siblingattributes": {}},
    }})
    accepts(definition)
    generator = _load("schema_generator", "tools/schema-generator.py")
    with pytest.raises(ValueError, match="Duplicate case-insensitive"):
        generator.generate_openapi(copy.deepcopy(definition))


# --- W03-l/m/n: constraint enums, undefined types and definition shapes ------


def test_empty_constraint_enum_is_admitted():
    definition = model()
    group_of(definition)["constraints"] = {"entries.payload": {"enum": []}}
    accepts(definition)
    definition = model()
    group_of(definition)["constraints"] = {"entries.payload": {"enum": ["a"]}}
    accepts(definition)


def test_empty_scalar_attribute_enum_is_admitted():
    accepts(with_attribute({"type": "integer", "enum": []}))


@pytest.mark.parametrize("position", ["attribute", "item", "wildcard"])
def test_the_undefined_core_binary_type_is_rejected(position):
    cases = {
        "attribute": with_attribute({"type": "binary"}),
        "item": with_attribute({"type": "array", "item": {"type": "binary"}}),
        "wildcard": model(attributes={"*": {"type": "binary"}}),
    }
    rejects(cases[position])


def test_typemap_binary_remains_legal():
    definition = model()
    resource_of(definition)["typemap"] = {"application/octet-stream": "binary"}
    accepts(definition)


@pytest.mark.parametrize("shorthand", ["string", "anything", "object"])
def test_string_attribute_definitions_are_rejected(shorthand):
    rejects(model(attributes={"payload": shorthand}))
    rejects(with_attribute({
        "type": "object", "attributes": {"inner": shorthand},
    }))


def test_object_form_attribute_definitions_remain_valid():
    accepts(with_attribute({"type": "string"}))
