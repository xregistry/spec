"""Executable examples for the incremental profile; not a provider."""

import importlib.util
import json
from pathlib import Path

import pytest

from workingdrafts.models.wot.tests.resolution.check_vectors import increment_numeric

ROOT = Path(__file__).resolve().parents[4]
WOT = ROOT / "workingdrafts" / "models" / "wot"


def test_incremental_model_does_not_inherit_semver_compatibility_policy():
    spec = importlib.util.spec_from_file_location(
        "schema_generator", ROOT / "tools" / "schema-generator.py"
    )
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    path = WOT / "model-incremental.json"
    model = generator.resolve_imports(str(path.parent), json.loads(path.read_bytes()))
    for plural, collection in [
        ("thingmodelgroups", "thingmodels"),
        ("thingdescriptiongroups", "thingdescriptions"),
    ]:
        resource = model["groups"][plural]["resources"][collection]
        assert resource["versionmode"] == "manual"
        assert not resource["singleversionroot"]
        assert "compatibility" not in resource.get("metaattributes", {})
        assert resource["attributes"]["compatibilityline"]["immutable"]
        assert resource["attributes"]["wotid"]["matchversions"]
    assert model["attributes"]["wotversionprofile"]["enum"] == ["incremental"]


def select(history, line, floor, sticky=None):
    if line is None:
        return "compatibility-required"
    candidates = [sticky] if sticky is not None else history
    numeric = lambda value: (len(value), value)
    return max(
        (
            revision
            for revision in candidates
            if history[revision] == line
            and (floor is None or numeric(revision) >= numeric(floor))
        ),
        key=numeric,
        default="unsatisfied",
    )


@pytest.mark.parametrize(
    "line,floor,sticky,expected",
    [
        ("A", "42", None, "44"),
        ("A", "42", "43", "unsatisfied"),
        ("A", "45", None, "unsatisfied"),
        (None, "42", None, "compatibility-required"),
    ],
)
def test_compatibility_line_examples(line, floor, sticky, expected):
    assert select({"42": "A", "43": "B", "44": "A", "45": None},
                  line, floor, sticky) == expected


def test_numeric_order_and_counter_do_not_sort_lexically():
    assert select({"9": "A", "10": "A"}, "A", "9") == "10"
    assert increment_numeric("99") == "100"
