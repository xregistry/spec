"""Exercise the effective administrative API and capability schema contracts."""

import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
MODELS = {
    "schema": ("schema",),
    "message": ("message",),
    "endpoint": ("endpoint",),
    "cloudevents": ("endpoint", "message", "schema"),
}
HTTP_METHODS = {"get", "put", "post", "patch", "delete", "head", "options", "trace"}
AVAILABLE = {
    "capabilities": {"mutable": False},
    "entities": {"mutable": True},
    "model": {"mutable": False},
}


@pytest.fixture(scope="module", params=MODELS)
def document(request, tmp_path_factory):
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


def _schema(document, name):
    if name not in document["components"]["schemas"]:
        pytest.fail(f"Missing administrative schema component: {name}", pytrace=False)
    return jsonschema.Draft7Validator({
        "$ref": f"#/components/schemas/{name}",
        "components": document["components"],
    })


def _parameters(document, operation):
    return [
        document["components"]["parameters"][item["$ref"].rsplit("/", 1)[1]]
        if "$ref" in item else item
        for item in operation.get("parameters", [])
    ]


def test_administrative_methods_match_the_binding(document):
    expected = {
        "/capabilities": {"get", "put", "patch"},
        "/capabilitiesoffered": {"get"},
        "/model": {"get"},
        "/modelsource": {"get", "put"},
        "/export": {"get"},
    }
    for path, methods in expected.items():
        assert set(document["paths"][path]) & HTTP_METHODS == methods
    assert document["paths"]["/modelsource"]["put"]["operationId"] == "putRegistryModelSource"
    assert document["paths"]["/modelsource"]["get"]["operationId"] == "getRegistryModelSource"


def test_obsolete_administrative_query_switches_are_not_advertised(document):
    for path in ("/capabilities", "/capabilitiesoffered", "/model", "/modelsource"):
        for method in set(document["paths"][path]) & HTTP_METHODS:
            names = {item["name"] for item in _parameters(document, document["paths"][path][method])}
            assert names == {"specversion"}


def test_modelsource_empty_object_is_valid_but_a_body_is_required(document):
    put = document["paths"]["/modelsource"]["put"]
    assert put["requestBody"]["required"] is True
    schema = put["requestBody"]["content"]["application/json"]["schema"]
    jsonschema.Draft7Validator(schema).validate({})
    for invalid in (None, [], ""):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.Draft7Validator(schema).validate(invalid)
    assert "{}" in document["paths"]["/modelsource"]["get"]["description"]
    assert "read-only" in document["paths"]["/model"]["get"]["description"]


def test_optional_apis_are_not_implied_by_the_template(document):
    assert "optional" in document["paths"]["/modelsource"]["get"]["description"].lower()
    assert "when supported" in document["paths"]["/capabilitiesoffered"]["get"]["description"].lower()
    assert "when supported" in document["paths"]["/export"]["get"]["description"].lower()
    assert "mutable" in document["paths"]["/modelsource"]["put"]["description"]


def test_export_uses_the_current_alias_and_keeps_inline_override(document):
    get = document["paths"]["/export"]["get"]
    assert "GET /?doc&inline=*,capabilities,modelsource" in get["description"]
    assert "*,model,capabilities" not in get["description"]
    assert "override" in get["description"]
    assert "inline" in {item["name"] for item in _parameters(document, get)}


def test_capability_request_and_response_schemas_have_distinct_presence_rules(document):
    expected = {"available", "compatibilities", "flags", "formats", "ignores", "mutable",
                "pagination", "shortself", "specversions", "versionmodes"}
    component = document["components"]["schemas"]["RegistryCapabilities"]
    assert set(component["properties"]) == expected
    assert component["additionalProperties"] is True
    for method in ("put", "patch"):
        operation = document["paths"]["/capabilities"][method]
        assert operation["requestBody"]["required"] is True
        assert operation["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith(
            "/RegistryCapabilities"
        )
    request = _schema(document, "RegistryCapabilities")
    request.validate({})
    request.validate({"shortself": True})
    response = _schema(document, "RegistryCapabilitiesResponse")
    with pytest.raises(jsonschema.ValidationError):
        response.validate({})
    response.validate({"available": AVAILABLE})
    for method in ("get", "put", "patch"):
        assert document["paths"]["/capabilities"][method]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]["$ref"].endswith("/RegistryCapabilitiesResponse")


@pytest.mark.parametrize(
    "available",
    [[], ["/model"], {"model": False}, {"model": {}}, {"model": {"mutable": "false"}}],
)
def test_available_rejects_legacy_arrays_and_wrong_entry_types(document, available):
    with pytest.raises(jsonschema.ValidationError):
        _schema(document, "RegistryCapabilities").validate({"available": available})


def test_current_capabilities_preserve_extensions_and_case_insensitive_values(document):
    _schema(document, "RegistryCapabilitiesResponse").validate({
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
    patch = document["paths"]["/capabilities"]["patch"]["description"]
    assert "whole" in patch and "recursive" in patch
    assert "default" in document["paths"]["/capabilities"]["put"]["description"]


def test_offered_capabilities_are_recursive_definitions_not_current_values(document):
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
    _schema(document, "RegistryCapabilitiesOffered").validate(offered)
    reference = document["paths"]["/capabilitiesoffered"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    assert reference.endswith("/RegistryCapabilitiesOffered")


@pytest.mark.parametrize(
    "definition",
    [True, [], {}, {"type": 7}, {"type": "array"}, {"type": "MAP", "item": {}},
     {"type": "object", "attributes": {"mutable": False}}],
)
def test_offered_capability_definitions_reject_value_maps_and_missing_item_types(document, definition):
    with pytest.raises(jsonschema.ValidationError):
        _schema(document, "RegistryCapabilitiesOffered").validate({"test": definition})
