"""Production include expansion regressions for issue 624."""

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import avro.schema
import jsonschema
import pytest
from openapi_spec_validator import validate_spec


@pytest.fixture
def generator():
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
def test_include_local_siblings_win_without_deep_merge(generator, tmp_path, multiple):
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
    result = generator.resolve_imports(str(tmp_path), source)
    assert result == {
        "singular": "local-wins",
        "attributes": {"local": {"type": "boolean"}},
        "description": "inherited",
    }
    assert source == original
    assert result is not source


def test_includes_order_and_local_precedence(generator, tmp_path):
    write_document(tmp_path, "first.json", {"shared": "first", "first": 1})
    write_document(tmp_path, "second.json", {"shared": "second", "second": 2})
    source = {"$includes": ["first.json", "second.json"], "first": "local"}
    assert generator.resolve_imports(str(tmp_path), source) == {
        "shared": "first", "first": "local", "second": 2,
    }
    reverse = {"$includes": ["second.json", "first.json"], "first": "local"}
    assert generator.resolve_imports(str(tmp_path), reverse)["shared"] == "second"


def test_nested_includes_use_the_declaring_document_base(generator, tmp_path):
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
    assert generator.resolve_imports(str(tmp_path), source) == {
        "resource": {"singular": "message"},
        "local": {"from": "root"},
        "sibling": {"from": "root"},
    }


def test_same_document_pointer_uses_the_included_document(generator, tmp_path):
    write_document(tmp_path, "nested/source.json", {
        "definitions": {"item": {"type": "string"}},
        "selected": {"$include": "#/definitions/item"},
    })
    source = {"$include": "nested/source.json#/selected"}
    assert generator.resolve_imports(str(tmp_path), source) == {"type": "string"}


def test_pointer_escapes_and_uri_fragment_decoding(generator, tmp_path):
    write_document(tmp_path, "source.json", {
        "a/b": {"~key": [{"space key": {"type": "string"}}]},
    })
    source = {"$include": "source.json#/a~1b/~0key/0/space%20key"}
    assert generator.resolve_imports(str(tmp_path), source) == {"type": "string"}


def test_repeated_non_cyclic_include_and_nested_input_nonmutation(generator, tmp_path):
    path = write_document(tmp_path, "base.json", {"attributes": {"value": {"type": "string"}}})
    original_bytes = path.read_bytes()
    source = {"list": [{"$include": "base.json"}, {"$include": "base.json"}]}
    original = copy.deepcopy(source)
    result = generator.resolve_imports(str(tmp_path), source)
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
def test_invalid_include_directives_fail_explicitly(generator, tmp_path, source):
    write_document(tmp_path, "source.json", {})
    original = copy.deepcopy(source)
    with pytest.raises(ValueError, match="include"):
        generator.resolve_imports(str(tmp_path), source)
    assert source == original


@pytest.mark.parametrize("pointer", [
    "groups", "/missing", "/bad~2escape", "/list/-", "/bad%GG", "/bad%FF",
])
def test_bad_json_pointers_fail_without_mutation(generator, tmp_path, pointer):
    write_document(tmp_path, "source.json", {"groups": {}, "list": [{}]})
    source = {"$include": f"source.json#{pointer}", "local": 1}
    original = copy.deepcopy(source)
    with pytest.raises(ValueError, match="pointer"):
        generator.resolve_imports(str(tmp_path), source)
    assert source == original


@pytest.mark.parametrize("target", [[], [1], "string", 1, False, None])
def test_include_target_must_be_an_object(generator, tmp_path, target):
    write_document(tmp_path, "source.json", {"target": target})
    with pytest.raises(ValueError, match="object"):
        generator.resolve_imports(str(tmp_path), {"$include": "source.json#/target"})


@pytest.mark.parametrize("indirect", [False, True])
def test_include_cycles_fail_explicitly(generator, tmp_path, indirect):
    write_document(tmp_path, "first.json", {
        "$include": "second.json" if indirect else "first.json",
    })
    write_document(tmp_path, "second.json", {"nested": {"$include": "first.json"}})
    with pytest.raises(ValueError, match="cycle"):
        generator.resolve_imports(str(tmp_path), {"$include": "first.json"})


def test_include_depth_is_bounded(generator, tmp_path):
    for index in range(66):
        write_document(tmp_path, f"{index}.json", {"$include": f"{index + 1}.json"})
    write_document(tmp_path, "66.json", {"value": "too deep"})
    with pytest.raises(ValueError, match="depth"):
        generator.resolve_imports(str(tmp_path), {"$include": "0.json"})


def test_include_depth_boundary_is_admitted(generator, tmp_path):
    for index in range(63):
        write_document(tmp_path, f"{index}.json", {"$include": f"{index + 1}.json"})
    write_document(tmp_path, "63.json", {"value": "within bound"})
    assert generator.resolve_imports(str(tmp_path), {"$include": "0.json"}) == {
        "value": "within bound",
    }


def test_same_file_path_alias_cannot_hide_a_cycle(generator, tmp_path):
    (tmp_path / "nested").mkdir()
    write_document(tmp_path, "source.json", {"$include": "nested/../source.json"})
    with pytest.raises(ValueError, match="cycle"):
        generator.resolve_imports(str(tmp_path), {"$include": "source.json"})


@pytest.mark.parametrize("reference", [
    "https://example.invalid/model.json",
    "file:///remote/model.json",
    "//remote/share/model.json",
    "\\\\remote\\share\\model.json",
])
def test_includes_do_not_acquire_network_resources(generator, tmp_path, reference, monkeypatch):
    def unexpected_open(*args, **kwargs):
        pytest.fail("A non-local include attempted file or network acquisition")

    monkeypatch.setattr("builtins.open", unexpected_open)
    with pytest.raises(ValueError, match="local"):
        generator.resolve_imports(str(tmp_path), {"$include": reference})


def test_missing_include_is_not_silently_ignored(generator, tmp_path):
    source = {"$include": "missing.json", "local": 1}
    with pytest.raises(FileNotFoundError):
        generator.resolve_imports(str(tmp_path), source)
    assert source == {"$include": "missing.json", "local": 1}


def test_invalid_include_json_is_not_silently_ignored(generator, tmp_path):
    (tmp_path / "invalid.json").write_text("{", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        generator.resolve_imports(str(tmp_path), {"$include": "invalid.json"})


def test_empty_includes_and_scalar_leaves_are_preserved(generator, tmp_path):
    source = {"$includes": [], "array": [None, False, 0, "value"], "object": {}}
    assert generator.resolve_imports(str(tmp_path), source) == {
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
        assert set(output["properties"]) == {"items", "others"}
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
