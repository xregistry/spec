"""Exercise required legal Core usage declarations and procedural role checks."""

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import avro.schema
import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "issue_626_usage", ROOT / "endpoint" / "usage" / "usage.py"
)
_helper = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_helper)
validate_usage = _helper.validate_usage
PROTOCOLS = ["HTTP", "KAFKA", "AMQP/1.0", "MQTT/3.1.1", "MQTT/5.0", "NATS"]
COMBINED_PROTOCOLS = ["AMQP/1.0", "MQTT/3.1.1", "MQTT/5.0", "NATS"]


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


@pytest.mark.parametrize("role", ["subscriber", "consumer", "producer"])
@pytest.mark.parametrize("protocol", PROTOCOLS + [None, "custom-protocol"])
def test_single_roles_remain_valid_without_changing_input(role, protocol):
    endpoint = {"usage": [role]}
    if protocol is not None:
        endpoint["protocol"] = protocol
    original = copy.deepcopy(endpoint)
    validate_usage(endpoint)
    assert endpoint == original


@pytest.mark.parametrize("protocol", COMBINED_PROTOCOLS)
@pytest.mark.parametrize("usage", [["subscriber", "consumer"], ["consumer", "subscriber"]])
def test_allowed_subscriber_consumer_combinations_preserve_role_order(protocol, usage):
    endpoint = {"protocol": protocol, "usage": usage}
    original = copy.deepcopy(endpoint)
    validate_usage(endpoint)
    assert endpoint == original


@pytest.mark.parametrize("protocol", ["HTTP", "KAFKA", None, "custom-protocol", True, [], {}])
@pytest.mark.parametrize("usage", [["subscriber", "consumer"], ["consumer", "subscriber"]])
def test_combined_roles_require_a_permitted_protocol(protocol, usage):
    with pytest.raises(ValueError, match="protocol does not permit"):
        validate_usage({"protocol": protocol, "usage": usage})


@pytest.mark.parametrize(
    "usage",
    [
        ["producer", "subscriber"], ["subscriber", "producer"],
        ["producer", "consumer"], ["consumer", "producer"],
        ["subscriber", "consumer", "producer"],
    ],
)
def test_producer_combinations_and_all_three_roles_are_errors(usage):
    for protocol in PROTOCOLS:
        with pytest.raises(ValueError, match="producer must not be combined"):
            validate_usage({"protocol": protocol, "usage": usage})


@pytest.mark.parametrize("role", ["subscriber", "consumer", "producer"])
def test_duplicate_roles_are_errors_even_for_combination_protocols(role):
    with pytest.raises(ValueError, match="must not repeat"):
        validate_usage({"protocol": "NATS", "usage": [role, role]})


@pytest.mark.parametrize("endpoint", [None, [], "producer"])
def test_domain_check_requires_an_endpoint_object(endpoint):
    with pytest.raises(ValueError, match="must be an object"):
        validate_usage(endpoint)


def test_domain_check_distinguishes_omission_from_an_empty_array():
    with pytest.raises(ValueError, match="usage is required"):
        validate_usage({})
    with pytest.raises(ValueError, match="nonempty array"):
        validate_usage({"usage": []})


@pytest.mark.parametrize("usage", [None, "producer", True, 1, {}, [True], [1], ["Producer"], ["unknown"]])
def test_domain_check_rejects_invalid_kinds_and_members(usage):
    with pytest.raises(ValueError):
        validate_usage({"usage": usage})


@pytest.mark.parametrize("usage", [[], ["unknown"], ["consumer", "consumer"]])
def test_schema_admission_does_not_replace_domain_validation(projections, usage):
    endpoint = {"protocol": "NATS", "usage": usage}
    document = {"endpoints": {"e": endpoint}}
    jsonschema.Draft7Validator(projections["json-schema"]).validate(document)
    with pytest.raises(ValueError):
        validate_usage(endpoint)
