"""Regressions discovered by compiling the domain models in xregistry-dotnet."""

import json
import importlib.util
from pathlib import Path
from urllib.parse import unquote, urldefrag

from jsonpointer import resolve_pointer
import pytest


ROOT = Path(__file__).resolve().parents[1]


def generator():
    spec = importlib.util.spec_from_file_location("model_regression_generator", ROOT / "tools" / "schema-generator.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cloudevents_include_fragments_are_resolvable_json_pointers():
    source = ROOT / "cloudevents" / "model.json"
    model = json.loads(source.read_text(encoding="utf-8"))
    merged_groups = {}
    for reference in model["groups"]["$includes"]:
        relative, fragment = urldefrag(reference)
        assert not fragment or fragment.startswith("/")
        document = json.loads((source.parent / relative).read_text(encoding="utf-8"))
        groups = resolve_pointer(document, unquote(fragment))
        assert isinstance(groups, dict)
        merged_groups.update(groups)
    assert {"endpoints", "messagegroups", "schemagroups"} <= merged_groups.keys()


def test_endpoint_usage_model_uses_only_core_defined_array_aspects():
    model = json.loads((ROOT / "endpoint" / "model.json").read_text(encoding="utf-8"))
    usage = model["groups"]["endpoints"]["attributes"]["usage"]
    assert usage["type"] == "array"
    assert usage["item"] == {"type": "string"}
    assert usage["required"] is True
    assert "enum" not in usage, "Core enum is a scalar aspect; endpoint role rules are domain constraints"
    for role in ("subscriber", "consumer", "producer"):
        assert role in usage["description"]


def test_generator_expands_cloudevents_without_a_literal_includes_group():
    path = ROOT / "cloudevents" / "model.json"
    source = json.loads(path.read_text(encoding="utf-8"))
    resolved = generator().resolve_imports(path.parent, source)
    assert set(resolved["groups"]) == {"endpoints", "messagegroups", "schemagroups"}
    assert "$includes" in source["groups"]
    assert "attributes" in resolved["groups"]["messagegroups"]["resources"]["messages"]


def test_generator_include_precedence_and_nested_document_base(tmp_path):
    (tmp_path / "parts").mkdir()
    (tmp_path / "parts" / "first.json").write_text(
        '{"$include":"../shared.json","local":"from-first","earlier":1}', encoding="utf-8")
    (tmp_path / "second.json").write_text('{"earlier":2,"later":3}', encoding="utf-8")
    (tmp_path / "shared.json").write_text('{"fromshared":true}', encoding="utf-8")
    source = {"$includes": ["parts/first.json", "second.json"], "local": "local-wins"}
    result = generator().resolve_imports(tmp_path, source)
    assert result == {"local": "local-wins", "earlier": 1, "later": 3, "fromshared": True}
    assert source["$includes"] == ["parts/first.json", "second.json"]


def test_generator_rejects_include_cycles_and_nonpointer_fragments(tmp_path):
    (tmp_path / "cycle.json").write_text('{"$include":"cycle.json"}', encoding="utf-8")
    with pytest.raises(ValueError, match="Circular"):
        generator().resolve_imports(tmp_path, {"$include": "cycle.json"})
    with pytest.raises(ValueError, match="RFC6901"):
        generator().resolve_imports(tmp_path, {"$include": "#groups"})


def test_schema_registry_protobuf_examples_preserve_fields_without_unmatched_braces():
    lines = (ROOT / "schema" / "spec.md").read_text(encoding="utf-8").splitlines()
    examples = [
        json.loads(line.strip().removeprefix('"schema": ').removesuffix(","))
        for line in lines if line.strip().startswith('"schema": "')
    ]
    prefix = 'syntax = "proto3"; message Metrics { '
    first = prefix + "float metric = 1; }"
    second = prefix + "float metric = 1; string unit = 2; }"
    third = prefix + "float metric = 1; string unit = 2; string description = 3; }"
    assert examples == [third, first, second, third]
