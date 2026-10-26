"""Shape checks only; these do not establish WoT closure semantics."""

from copy import deepcopy
import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas" / "publication-closure.schema.json").read_text())
EXAMPLE = json.loads((ROOT / "samples" / "publication-closure.json").read_text())


def test_proposed_closure_shape():
    jsonschema.Draft202012Validator.check_schema(SCHEMA)
    jsonschema.validate(EXAMPLE, SCHEMA)


@pytest.mark.parametrize("pointer", ["links/0", "/links/~2", "#/links/0"])
def test_invalid_json_pointer_rejected(pointer):
    example = deepcopy(EXAMPLE)
    example["bindings"][0]["pointer"] = pointer
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(example, SCHEMA)


def test_missing_exact_target_rejected():
    example = deepcopy(EXAMPLE)
    del example["bindings"][0]["target"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(example, SCHEMA)
