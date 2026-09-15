"""Check the effective and published Problem Details contract."""

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
