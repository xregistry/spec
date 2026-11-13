import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).parent.parent
SCHEMA_PATH = ROOT / "core" / "model.schema.json"


@pytest.fixture(scope="module")
def validator():
    with SCHEMA_PATH.open(encoding="utf-8") as schema_file:
        schema = json.load(schema_file)
    validator_class = jsonschema.validators.validator_for(schema)
    validator_class.check_schema(schema)
    return validator_class(schema)


def _model(typemap):
    """Build a minimal model whose only Resource carries the given typemap."""
    return {
        "groups": {
            "dirs": {
                "plural": "dirs",
                "singular": "dir",
                "resources": {
                    "files": {
                        "plural": "files",
                        "singular": "file",
                        "typemap": typemap,
                    }
                },
            }
        }
    }


def _errors(validator, typemap):
    return list(validator.iter_errors(_model(typemap)))


@pytest.mark.parametrize("value", ["binary", "json", "string"])
def test_typemap_accepts_defined_values(validator, value):
    assert _errors(validator, {"application/octet-stream": value}) == []


def test_typemap_accepts_binary_for_json_content_type(validator):
    # 'binary' forces byte-for-byte serialization even for JSON documents.
    typemap = {"application/json": "binary", "*+json": "binary"}
    assert _errors(validator, typemap) == []


def test_typemap_accepts_wildcard_keys_with_mixed_values(validator):
    typemap = {"text/*": "string", "text/mine": "json", "*": "binary"}
    assert _errors(validator, typemap) == []


@pytest.mark.parametrize("value", ["bytes", "base64", "xml", ""])
def test_typemap_rejects_unknown_values(validator, value):
    # The same model is valid with a defined value (see the accept tests
    # above), so the typemap value is the only possible cause of the error.
    assert _errors(validator, {"application/json": value}), (
        f"typemap value {value!r} should have been rejected"
    )


def test_typemap_rejects_non_string_values(validator):
    assert _errors(validator, {"application/json": True})


def test_typemap_rejects_empty_key(validator):
    assert _errors(validator, {"": "binary"})
