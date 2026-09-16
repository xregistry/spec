"""Regression checks for Kafka client bootstrap declarations, not broker I/O."""

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = ROOT / "endpoint" / "kafka_bootstrap.py"
SAMPLE_PATH = (
    ROOT / "cloudevents" / "samples" / "scenarios" / "contoso-erp-jsons07.xreg.json"
)
_spec = importlib.util.spec_from_file_location("issue_625_kafka", HELPER_PATH)
_helper = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_helper)
validate_bootstrap_servers = _helper.validate_bootstrap_servers


def _kafka_options(node):
    matches = []

    def visit(branch):
        if not isinstance(branch, dict):
            return
        properties = branch.get("properties", {})
        guard = properties.get("protocol")
        if (
            "protocol" in branch.get("required", [])
            and "protocoloptions" in properties
            and guard is not None
            and jsonschema.Draft7Validator(guard).is_valid("KAFKA")
        ):
            matches.append(properties["protocoloptions"])
        for keyword in ("allOf", "anyOf", "oneOf"):
            for child in branch.get(keyword, []):
                visit(child)

    visit(node)
    if len(matches) != 1:
        raise ValueError(
            f"Expected one Kafka protocoloptions branch, found {len(matches)}"
        )
    return matches[0]


@pytest.fixture(params=["endpoint", "cloudevents"])
def endpoint_schema(request, tmp_path):
    output = tmp_path / "document-schema.json"
    models = [ROOT / "endpoint" / "model.json"]
    if request.param == "cloudevents":
        models += [ROOT / "message" / "model.json", ROOT / "schema" / "model.json"]
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(ROOT / "tools" / "schema-generator.py"),
            "--type",
            "json-schema",
            "--output",
            str(output),
            *map(str, models),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    schema = json.loads(output.read_text(encoding="utf-8"))
    return schema["definitions"]["endpoint-schema"]["endpoint"]


@pytest.fixture
def options_schema(endpoint_schema):
    options = _kafka_options(endpoint_schema)
    jsonschema.Draft7Validator.check_schema(options)
    return options


@pytest.fixture(params=["enum", "pattern"])
def kafka_artifact(request, endpoint_schema):
    endpoint = copy.deepcopy(endpoint_schema)
    candidates = []
    for part in endpoint["allOf"]:
        for branch in part.get("oneOf", []):
            options = branch.get("properties", {}).get("protocoloptions", {})
            addresses = options.get("properties", {}).get("endpoints", {})
            fields = addresses.get("items", {}).get("properties", {})
            if "bootstrap.servers" in fields:
                candidates.append(branch)
    assert len(candidates) == 1
    branch = candidates[0]
    if request.param == "enum":
        guard = {"type": "string", "enum": ["KAFKA"]}
    else:
        guard = {
            "type": "string",
            "pattern": r"^[Kk][Aa][Ff][Kk][Aa](?![\s\S])",
        }
    branch["properties"]["protocol"] = guard
    jsonschema.Draft7Validator.check_schema(endpoint)
    return endpoint, branch


def test_kafka_selector_selects_matching_generated_branch(kafka_artifact):
    endpoint, branch = kafka_artifact
    options = _kafka_options(endpoint)
    assert options is branch["properties"]["protocoloptions"]
    validator = jsonschema.Draft7Validator(options)
    sample = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    for entry in sample["endpoints"].values():
        if entry["protocol"] == "KAFKA":
            validator.validate(entry["protocoloptions"])
    assert not validator.is_valid(
        {"endpoints": [{"bootstrap.servers": [9092]}]}
    )


def test_kafka_selector_ignores_unguarded_options(kafka_artifact):
    endpoint, branch = kafka_artifact
    endpoint["properties"]["protocol"] = {"type": "string"}
    endpoint["properties"]["protocoloptions"] = {"not": {}}
    assert _kafka_options(endpoint) is branch["properties"]["protocoloptions"]


@pytest.mark.parametrize("position", ["first", "last"])
def test_kafka_selector_is_independent_of_branch_order(kafka_artifact, position):
    endpoint, branch = kafka_artifact
    alternatives = next(
        part["oneOf"]
        for part in endpoint["allOf"]
        if any(candidate is branch for candidate in part.get("oneOf", []))
    )
    alternatives.remove(branch)
    alternatives.insert(0 if position == "first" else len(alternatives), branch)
    assert _kafka_options(endpoint) is branch["properties"]["protocoloptions"]


def test_kafka_selector_rejects_missing_branch(kafka_artifact):
    endpoint, branch = kafka_artifact
    branch.clear()
    with pytest.raises(ValueError, match="found 0"):
        _kafka_options(endpoint)


def test_kafka_selector_rejects_ambiguous_branches(kafka_artifact):
    endpoint, branch = kafka_artifact
    endpoint["allOf"].append(copy.deepcopy(branch))
    with pytest.raises(ValueError, match="found 2"):
        _kafka_options(endpoint)


@pytest.mark.parametrize(
    "guard",
    [
        {"type": "string", "enum": ["HTTP"]},
        {"type": "string", "pattern": r"^HTTP(?![\s\S])"},
        {"not": {"enum": ["KAFKA"]}},
    ],
    ids=["other-enum", "other-pattern", "fallback"],
)
def test_kafka_selector_rejects_nonmatching_guards(kafka_artifact, guard):
    endpoint, branch = kafka_artifact
    branch["properties"]["protocol"] = guard
    with pytest.raises(ValueError, match="found 0"):
        _kafka_options(endpoint)


def test_kafka_selector_requires_protocol_discriminator(kafka_artifact):
    endpoint, branch = kafka_artifact
    branch["required"].remove("protocol")
    with pytest.raises(ValueError, match="found 0"):
        _kafka_options(endpoint)


def test_kafka_selector_ignores_negated_branches(kafka_artifact):
    endpoint, branch = kafka_artifact
    endpoint["not"] = copy.deepcopy(branch)
    branch.clear()
    with pytest.raises(ValueError, match="found 0"):
        _kafka_options(endpoint)


def test_kafka_selector_requires_protocol_options(kafka_artifact):
    endpoint, branch = kafka_artifact
    del branch["properties"]["protocoloptions"]
    with pytest.raises(ValueError, match="found 0"):
        _kafka_options(endpoint)


def test_contoso_kafka_samples_preserve_ssl_without_listener_urls(options_schema):
    sample = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    kafka = [
        endpoint
        for endpoint in sample["endpoints"].values()
        if endpoint["protocol"] == "KAFKA"
    ]
    assert {tuple(endpoint["usage"]) for endpoint in kafka} == {
        ("producer",),
        ("consumer",),
    }
    for endpoint in kafka:
        options = endpoint["protocoloptions"]
        assert options["endpoints"] == [
            {
                "bootstrap.servers": ["cediscoveryinterop.example.com:9093"],
                "security.protocol": "SSL",
            }
        ]
        jsonschema.Draft7Validator(options_schema).validate(options)
        assert validate_bootstrap_servers(
            options["endpoints"][0]["bootstrap.servers"]
        ) == [("cediscoveryinterop.example.com", 9093)]
        assert options["deployed"] is False
        assert "endpoints" not in endpoint


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (["broker1:9092", "broker2:9092"], [("broker1", 9092), ("broker2", 9092)]),
        (["127.0.0.1:8000"], [("127.0.0.1", 8000)]),
        (["[::1]:8000"], [("::1", 8000)]),
        (["host:0", "host:65535"], [("host", 0), ("host", 65535)]),
    ],
)
def test_resolved_host_port_and_bracketed_ipv6(value, expected):
    original = copy.deepcopy(value)
    assert validate_bootstrap_servers(value) == expected
    assert value == original


@pytest.mark.parametrize(
    "value",
    [
        [],
        "host:9092",
        [None],
        [True],
        [9092],
        ["host"],
        [":9092"],
        ["host:"],
        ["host:port"],
        ["host:-1"],
        ["host:65536"],
        ["2001:db8::1:9092"],
        ["[not-ipv6]:9092"],
        ["host:9092/path"],
        ["user@host:9092"],
        ["host:9092,other:9092"],
        [" host:9092"],
        ["SSL://host:9093"],
        ["PLAINTEXT://host:9092"],
        ["CUSTOM://host:9092"],
    ],
)
def test_invalid_resolved_address_shapes_are_errors(value):
    with pytest.raises(ValueError):
        validate_bootstrap_servers(value)


def test_authoring_placeholders_remain_strings_until_consumer_resolution(
    options_schema,
):
    options = {
        "endpoints": [
            {
                "bootstrap.servers": ["{broker}:{port}", "[{ipv6}]:{port}"],
                "security.protocol": "{security}",
            }
        ]
    }
    original = copy.deepcopy(options)
    jsonschema.Draft7Validator(options_schema).validate(options)
    assert options == original
    with pytest.raises(ValueError, match="resolved bootstrap address"):
        validate_bootstrap_servers(options["endpoints"][0]["bootstrap.servers"])
    resolved = ["broker:9093", "[2001:db8::1]:9093"]
    assert validate_bootstrap_servers(resolved) == [
        ("broker", 9093),
        ("2001:db8::1", 9093),
    ]
    assert options == original


@pytest.mark.parametrize("resolved", ["SSL://host:9093", "PLAINTEXT://host:9092"])
def test_listener_urls_remain_invalid_after_out_of_band_resolution(resolved):
    authoring = "{bootstrap}"
    with pytest.raises(ValueError, match="resolved bootstrap address"):
        validate_bootstrap_servers([authoring.replace("{bootstrap}", resolved)])
    assert authoring == "{bootstrap}"


@pytest.mark.parametrize("value", [None, True, 9092, 1.5, {}, []])
def test_generated_schema_rejects_nonstring_addresses(options_schema, value):
    options = {"endpoints": [{"bootstrap.servers": [value]}]}
    assert not jsonschema.Draft7Validator(options_schema).is_valid(options)


def test_kafka_source_model_keeps_address_and_security_separate():
    model = json.loads((ROOT / "endpoint" / "model.json").read_text("utf-8"))
    options = model["groups"]["endpoints"]["attributes"]["protocol"]["ifvalues"][
        "KAFKA"
    ]["siblingattributes"]["protocoloptions"]
    entry = options["attributes"]["endpoints"]["item"]["attributes"]
    assert entry["bootstrap.servers"]["type"] == "array"
    assert entry["bootstrap.servers"]["item"] == {"type": "string"}
    assert entry["security.protocol"]["type"] == "string"
    assert entry["security.protocol"]["default"] == "PLAINTEXT"
