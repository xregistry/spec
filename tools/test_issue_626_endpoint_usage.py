"""Exercise required Core usage declarations and actual generated projections."""

import json
import subprocess
import sys
from pathlib import Path

import avro.schema
import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module", params=["endpoint", "cloudevents"])
def projections(request, tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp(f"issue626-{request.param}")
    models = [ROOT / "endpoint" / "model.json"]
    if request.param == "cloudevents":
        models += [ROOT / "message" / "model.json", ROOT / "schema" / "model.json"]
    result = {}
    for kind in ["json-schema", "json-structure", "avro-schema", "openapi"]:
        output = tmp_path / f"{kind}.json"
        generated = subprocess.run(
            [
                sys.executable, "-B", str(ROOT / "tools" / "schema-generator.py"),
                "--type", kind, "--output", str(output), *map(str, models),
            ],
            cwd=ROOT, capture_output=True, text=True, timeout=30, check=False,
        )
        assert generated.returncode == 0, generated.stdout + generated.stderr
        result[kind] = json.loads(output.read_text(encoding="utf-8"))
    return result


def _schema_endpoint(projections):
    return projections["json-schema"]["definitions"]["endpoint-schema"]["endpoint"]


def test_source_usage_has_required_legal_string_array_aspects():
    model = json.loads((ROOT / "endpoint" / "model.json").read_text("utf-8"))
    usage = model["groups"]["endpoints"]["attributes"]["usage"]
    assert usage["type"] == "array"
    assert usage["required"] is True
    assert usage["item"] == {"type": "string"}
    assert "enum" not in usage
    assert "strict" not in usage
    assert "default" not in usage


def test_all_projections_keep_usage_a_required_string_array(projections):
    endpoint = _schema_endpoint(projections)
    assert "usage" in endpoint["required"]
    assert endpoint["properties"]["usage"]["type"] == "array"
    assert endpoint["properties"]["usage"]["items"] == {"type": "string"}

    endpoint = projections["json-structure"]["definitions"]["Endpoints"]["Endpoint"]
    assert "usage" in endpoint["required"]
    assert endpoint["properties"]["usage"]["type"] == "array"
    assert endpoint["properties"]["usage"]["items"] == {"type": "string"}

    endpoint = projections["openapi"]["components"]["schemas"]["endpoint"]
    assert "usage" in endpoint["required"]
    assert endpoint["properties"]["usage"]["type"] == "array"
    assert endpoint["properties"]["usage"]["items"] == {"type": "string"}

    document = avro.schema.parse(json.dumps(projections["avro-schema"]))
    endpoint = next(field for field in document.fields if field.name == "endpoints")
    usage = next(field for field in endpoint.type.values.fields if field.name == "usage")
    assert usage.type.type == "array"
    assert usage.type.items.type == "string"


def test_generated_schema_rejects_omitted_usage(projections):
    schema = projections["json-schema"]
    errors = list(jsonschema.Draft7Validator(schema).iter_errors({"endpoints": {"e": {}}}))
    assert errors, "required Endpoint usage must not disappear in either consumer"
    assert any(error.validator == "required" and "usage" in error.message for error in errors)


@pytest.mark.parametrize("usage", [None, "producer", True, 1, {}, [True], [1], [{}]])
def test_generated_schema_rejects_wrong_usage_kinds(projections, usage):
    document = {"endpoints": {"e": {"usage": usage}}}
    errors = list(jsonschema.Draft7Validator(projections["json-schema"]).iter_errors(document))
    assert errors, "usage must be an array of native strings"
