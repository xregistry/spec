"""Verify that the generated WoT bundle tracks xRegistry model sources."""

import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

from jsonschema import Draft202012Validator
import pytest
from referencing import Registry
from referencing.jsonschema import DRAFT202012

from workingdrafts.bindings.tools import generate_wot


def run_generator(output, *args):
    return subprocess.run(
        [sys.executable, "-B", str(Path(generate_wot.__file__)), str(output), *args],
        capture_output=True, text=True, cwd=output.parent,
    )


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    output = tmp_path_factory.mktemp("wot-bundle")
    result = run_generator(output)
    assert result.returncode == 0, result.stderr
    return output


def test_generates_all_repository_models_and_resolves_bundle_references(generated):
    root = generate_wot.ROOT
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
    sources = {path for path in tracked if Path(path).name == "model.json" and (root / path).is_file()}
    models = {path: json.loads(path.read_bytes()) for path in generated.glob("*.TM.json")}
    assert {"XRegistry", "SchemaExtensions", "ThingDescriptionExtensions", "ThingModelExtensions"} <= {
        model["title"] for model in models.values()
    }
    assert sources <= {model["xreg:modelSource"] for model in models.values()}
    core = models[generated / "XRegistry.TM.json"]
    assert core["xreg:types"] == "./schemas/XRegistryTypes.schema.json"
    assert any(
        isinstance(context, dict) and context.get("mqv") == "https://www.w3.org/2019/wot/mqtt#"
        for context in core["@context"]
    )
    expected_actions = {"read", "replace", "update", "upsert", "delete", "options"}
    assert core["actions"].keys() == expected_actions

    schemas = {
        path: json.loads(path.read_bytes()) for path in (generated / "schemas").glob("*.schema.json")
    }
    registry = Registry().with_resources(
        (path.as_uri(), DRAFT202012.create_resource(schema)) for path, schema in schemas.items()
    )

    def check_references(node, owner):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "$ref":
                    registry.resolver(owner.as_uri()).lookup(value)
                elif key in {"xreg:types", "xreg:schema", "xreg:documentValueSchema", "documentValueSchema"}:
                    assert (owner.parent / value).resolve() in schemas
                elif key == "href":
                    assert (owner.parent / value).resolve() in models
                check_references(value, owner)
        elif isinstance(node, list):
            for value in node:
                check_references(value, owner)

    for path, schema in schemas.items():
        Draft202012Validator.check_schema(schema)
        check_references(schema, path)
    for path, model in models.items():
        check_references(model, path)
        if model is not core:
            assert "actions" not in model
            assert any(link["rel"] == "tm:extends" and link["href"] == "./XRegistry.TM.json"
                       for link in model["links"])
    for name, action in core["actions"].items():
        form = action["forms"][0]
        assert form["mqv:controlPacket"] == "publish"
        assert form["mqv:qos"] == "1"
        assert form["mqv:retain"] is False
        assert form["xreg:binding"] == "mqtt"
        assert form["xreg:topic"] == f"{{topicbase}}/{name}{{target}}"
        assert "mqv:topic" not in form


def test_projects_composed_and_domain_types_from_repository_sources(generated):
    def schema(name):
        return json.loads((generated / "schemas" / f"{name}Types.schema.json").read_bytes())

    cloud_events = schema("CloudEvents")
    assert cloud_events["properties"].keys() == {"endpoints", "messagegroups", "schemagroups"}
    endpoint = cloud_events["$defs"]["/endpoints"]
    assert endpoint["properties"]["messages"]["additionalProperties"]["$ref"] == "#/$defs/~1messagegroups~1messages"
    options = endpoint["xreg:ifvalues"]["protocol"]["MQTT/5.0"]["properties"]["protocoloptions"]
    assert options["properties"]["topic"]["type"] == "string"
    assert schema("Message")["$defs"]["/messagegroups/messages"]["xreg:facets"]["hasdocument"] is False
    assert schema("OpenUSD")["$defs"]["/usdschemaplugingroups"]["properties"]["usdassets"] == {
        "type": "object", "additionalProperties": {"$ref": "#/$defs/~1usdassetgroups~1usdassets"},
    }


def test_model_edits_change_version_schema_constraints(tmp_path, monkeypatch):
    monkeypatch.setattr(generate_wot, "ROOT", tmp_path)
    path = tmp_path / "example" / "model.json"
    path.parent.mkdir()
    definition = {"type": "string", "enum": ["json"], "required": True}
    source = {"groups": {"groups": {"resources": {"items": {"attributes": {"format": definition}}}}}}

    def validator():
        path.write_text(json.dumps(source), encoding="utf-8")
        # The CLI starts a fresh process for each generation; clear its read cache here.
        generate_wot.load.cache_clear()
        result = generate_wot.bundle([path])["schemas/ExampleTypes.schema.json"]
        return Draft202012Validator(result["$defs"]["/groups/items/versions"])

    before = validator()
    assert before.is_valid({"format": "json"})
    assert not before.is_valid({})
    definition["enum"] = ["xml"]
    after = validator()
    assert after.is_valid({"format": "xml"})
    assert not after.is_valid({"format": "json"})


@pytest.mark.parametrize("drift", ["missing", "changed", "stale"])
def test_check_reports_drift_without_rewriting_bundle(generated, tmp_path, drift):
    for path in generated.rglob("*.json"):
        copy = tmp_path / path.relative_to(generated)
        copy.parent.mkdir(parents=True, exist_ok=True)
        copy.write_bytes(path.read_bytes())
    assert run_generator(tmp_path, "--check").returncode == 0

    core = tmp_path / "XRegistry.TM.json"
    if drift == "missing":
        core.unlink()
    elif drift == "changed":
        core.write_text("{}", encoding="utf-8")
    else:
        (tmp_path / "Stale.TM.json").write_text("{}", encoding="utf-8")
    snapshot = {p: p.read_bytes() for p in tmp_path.rglob("*.json")}
    result = run_generator(tmp_path, "--check")
    assert result.returncode != 0
    assert ("Stale generated files" if drift == "stale" else core.name) in result.stderr
    assert {p: p.read_bytes() for p in tmp_path.rglob("*.json")} == snapshot


def test_zip_contains_only_the_generated_bundle(generated, tmp_path):
    output = tmp_path / "handoff.zip"
    expected = {
        f"xregistry-wot/{file.relative_to(generated).as_posix()}": file.read_bytes()
        for file in generated.rglob("*.json")
    }
    (tmp_path / "xregistry-mqtt-design.md").write_text("# Design note\n", encoding="utf-8")

    result = run_generator(output)
    assert result.returncode == 0, result.stderr
    with ZipFile(output) as archive:
        assert sorted(archive.namelist()) == sorted(expected)
        assert {name: archive.read(name) for name in archive.namelist()} == expected

    result = run_generator(output, "--check")
    assert result.returncode == 0, result.stderr
    with ZipFile(output, "a") as archive:
        archive.writestr("xregistry-wot/Stale.TM.json", "{}")
    original = output.read_bytes()
    result = run_generator(output, "--check")
    assert result.returncode != 0
    assert "Missing, changed, or stale generated entries" in result.stderr
    assert output.read_bytes() == original
