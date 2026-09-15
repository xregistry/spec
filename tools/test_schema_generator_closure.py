"""Model admission through complete generated JSON Schema/OpenAPI entities."""

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest
from openapi_spec_validator import validate


ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "schema_generator", ROOT / "tools" / "schema-generator.py"
)
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)


def model(definition):
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


def document(value):
    return {
        "registryid": "r", "specversion": "1.0",
        "self": "https://example.com/", "xid": "/", "epoch": 1,
        "createdat": "2026-01-01T00:00:00Z",
        "modifiedat": "2026-01-01T00:00:00Z",
        "catalogs": {
            "c": {"catalogid": "c", "name": "catalog", "payload": value}
        },
    }


def entry_meta(default_version="v1"):
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


def generated_validator(definition, dialect):
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
    validator = generated_validator(model(copy.deepcopy(definition)), dialect)
    valid = document(copy.deepcopy(value))
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
    validator = generated_validator(model(copy.deepcopy(definition)), dialect)
    assert validator.is_valid(document(copy.deepcopy(value)))
    assert validator.is_valid(document({}))


@pytest.mark.parametrize("dialect", ["json-schema", "openapi"])
def test_typed_wildcard_does_not_restrict_named_properties(dialect):
    definition = {
        "type": "object",
        "attributes": {
            "name": {"type": "string"},
            "*": {"type": "integer"},
        },
    }
    validator = generated_validator(model(definition), dialect)
    validator.validate(document({"name": "http", "first": 7, "second": 8}))
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(document({"name": "http", "first": "wrong"}))


@pytest.mark.parametrize("dialect", ["json-schema", "openapi"])
def test_wildcard_object_values_keep_their_own_closed_boundary(dialect):
    definition = {"type": "object", "attributes": {
        "*": {"type": "object", "attributes": {"value": {"type": "string"}}},
    }}
    validator = generated_validator(model(definition), dialect)
    validator.validate(document({"first": {"value": "ok"}, "second": {}}))
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(document({"first": {"value": "ok", "extra": 7}}))


@pytest.mark.parametrize("dialect", ["json-schema", "openapi"])
def test_schema_generation_does_not_mutate_caller_model(dialect):
    definition = model(copy.deepcopy(CLOSED_LEAF))
    original = copy.deepcopy(definition)
    generated_validator(definition, dialect)
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
    validator = generated_validator(definition, dialect)
    value = document({})
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
    validator = generated_validator(model({"type": "decimal"}), dialect)
    for value in (0, -1, 1.25):
        validator.validate(document(value))
    for invalid in ("1.25", True, {"value": 1.25}):
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(document(invalid))


@pytest.mark.parametrize("dialect", ["json-schema", "openapi"])
def test_common_epochs_preserve_unsigned_integer_values(dialect):
    validator = generated_validator(model({"type": "object"}), dialect)
    value = document({})
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
    validator = generated_validator(model(conditional_definition()), dialect)
    for value in (
        {}, {"fixed": "ok"}, {"kind": "other"}, {"kind": "ALPHA"},
        {"kind": "alpha", "fixed": "ok", "alpha": {"name": "http"}},
        {"kind": "ALPHA", "alpha": {"name": "http"}},
        {"kind": "beta", "fixed": "ok", "beta": 7},
    ):
        validator.validate(document(value))
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
            validator.validate(document(value))


@pytest.mark.parametrize("dialect", ["json-schema", "openapi"])
def test_inactive_conditional_names_use_the_declared_wildcard(dialect):
    validator = generated_validator(
        model(conditional_definition({"type": "integer"})), dialect
    )
    validator.validate(document({"kind": "alpha", "alpha": {"name": "http"}, "extra": 7}))
    validator.validate(document({"kind": "other", "alpha": 7, "extra": 8}))
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(document({"kind": "other", "alpha": {"name": "http"}}))
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(document({"kind": "alpha", "alpha": {"name": "http"}, "extra": "bad"}))


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
    validator = generated_validator(model(definition), dialect)
    validator.validate(document({"kind": "open", "fixed": "ok", "extra": 7}))
    validator.validate(document({"kind": "closed", "fixed": "ok"}))
    validator.validate(document({}))
    for value in ({"extra": 7}, {"kind": "other", "extra": 7},
                  {"kind": "closed", "extra": 7}):
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(document(value))
    if wildcard["type"] == "integer":
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(document({"kind": "open", "extra": "bad"}))
    else:
        validator.validate(document({"kind": "open", "extra": {"anything": [7]}}))


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
    validator = generated_validator(model(definition), dialect)
    value = {
        "kind": "alpha", "alpha": {"name": "http"}, "sub": "on",
        "leaf": {"name": "nested"}, "mode": "on", "enabled": True,
    }
    validator.validate(document(value))
    for mutation in (
        {"sub": "off"}, {"kind": "other"}, {"mode": "off"},
        {"leaf": {"name": "nested", "extra": True}},
    ):
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(document({**value, **mutation}))


@pytest.mark.parametrize("dialect", ["json-schema", "openapi"])
def test_full_entity_closure_preserves_core_overlays_and_collection_maps(dialect):
    definition = model(copy.deepcopy(CLOSED_LEAF))
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
    validator = generated_validator(definition, dialect)
    value = document({"name": "http"})
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
    definition = model({"type": "any"})
    definition["groups"]["catalogs"]["resources"] = {"entries": {
        "singular": "entry", "maxversions": maxversions, "hasdocument": False,
        "attributes": {"data": copy.deepcopy(CLOSED_LEAF)},
        "metaattributes": {"custom": copy.deepcopy(CLOSED_LEAF)},
    }}
    validator = generated_validator(definition, dialect)
    value = document({})
    value["catalogs"]["c"]["entries"] = {"e": {
        "entryid": "e", "metaurl": "https://example.com/meta",
        "meta": {**entry_meta("first"), "custom": {"name": "meta"}},
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
    definition = model({"type": "any"})
    definition["attributes"] = {"*": {"type": "integer"}}
    validator = generated_validator(definition, dialect)
    value = document({"open": True})
    value["extra"] = 7
    validator.validate(value)
    value["extra"] = "bad"
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(value)


@pytest.mark.parametrize("dialect", ["json-schema", "openapi"])
def test_closure_keeps_enum_scope_and_case_insensitive_selection(dialect):
    definition = conditional_definition()
    definition["attributes"]["kind"]["enum"] = ["alpha"]
    definition["attributes"]["kind"]["strict"] = True
    definition["attributes"]["kind"]["ifvalues"].pop("beta")
    validator = generated_validator(model(definition), dialect)
    # Scalar enum enforcement is outside these combined fixes.
    validator.validate(document({"kind": "other"}))
    validator.validate(document({"kind": "ALPHA"}))
    validator.validate(document({"kind": "ALPHA", "alpha": {"name": "http"}}))
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(document({"kind": "ALPHAX", "alpha": {"name": "http"}}))


@pytest.mark.parametrize("dialect", ["json-schema", "openapi"])
def test_conditional_alternatives_can_declare_the_same_name_with_distinct_types(dialect):
    definition = {"type": "object", "attributes": {
        "kind": {"type": "string", "ifvalues": {
            "text": {"siblingattributes": {"detail": {"type": "string"}}},
            "count": {"siblingattributes": {"detail": {"type": "integer"}}},
        }},
    }}
    validator = generated_validator(model(definition), dialect)
    validator.validate(document({"kind": "text", "detail": "ok"}))
    validator.validate(document({"kind": "count", "detail": 7}))
    for value in (
        {"kind": "text", "detail": 7},
        {"kind": "count", "detail": "bad"},
        {"kind": "other", "detail": 7},
    ):
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(document(value))


@pytest.mark.parametrize("dialect", ["json-schema", "openapi"])
def test_cli_root_model_attributes_participate_in_full_document_closure(tmp_path, dialect):
    definition = model(copy.deepcopy(CLOSED_LEAF))
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
    value = document({"name": "http"})
    value["rootdata"] = {"name": "root"}
    validator.validate(value)
    value["rootdata"]["unmodeled"] = True
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(value)


@pytest.mark.parametrize("dialect", ["json-schema", "openapi"])
def test_closure_does_not_close_opaque_resource_document_content(dialect):
    definition = model({"type": "any"})
    definition["groups"]["catalogs"]["resources"] = {"entries": {
        "singular": "entry", "hasdocument": True, "maxversions": 0,
        "attributes": {"data": copy.deepcopy(CLOSED_LEAF)},
    }}
    validator = generated_validator(definition, dialect)
    value = document({})
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
    definition = model(copy.deepcopy(CLOSED_LEAF))
    group = definition["groups"]["catalogs"]
    group["attributes"]["*"] = {"type": "any"}
    group["resources"] = {"entries": {
        "singular": "entry", "hasdocument": False, "maxversions": maxversions,
        "attributes": {"*": {"type": "any"}},
    }}
    validator = generated_validator(definition, dialect)
    value = document({"name": "closed"})
    value["catalogs"]["c"].update({
        "group_extension": {"nested": [7, True]},
        "entries": {"e": {
            "entryid": "e", "resource_extension": {"nested": True},
            "meta": entry_meta(),
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
