"""Representative resolution cases and proposed closure-shape examples."""

from copy import deepcopy
import json
from pathlib import Path

import jsonschema
import pytest

from workingdrafts.models.wot.tests.resolution import check_vectors

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas" / "publication-closure.schema.json").read_text())
EXAMPLE = json.loads((ROOT / "samples" / "publication-closure.json").read_text())
VECTORS = check_vectors.load_vectors()
VECTOR_SCHEMA = json.loads((check_vectors.HERE / "schema.json").read_bytes())


@pytest.mark.parametrize("name", VECTORS)
def test_resolution_vector(name):
    jsonschema.validate({name: VECTORS[name]}, VECTOR_SCHEMA)
    check_vectors.check_case(name, VECTORS[name])


def test_proposed_closure_shape():
    jsonschema.Draft202012Validator.check_schema(SCHEMA)
    jsonschema.validate(EXAMPLE, SCHEMA)


@pytest.mark.parametrize("pointer", ["links/0"])
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
