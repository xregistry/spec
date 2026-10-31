"""Representative resolution cases and proposed closure-shape examples."""

from copy import deepcopy
import json
from pathlib import Path
import re
from urllib.parse import quote, unquote, urlsplit

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


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("entries", "/thingmodelgroups/acme/thingmodels/pump"),
        ("source", "urn:example:pump:v1"),
        ("target", "https://example.test/thingmodels/base"),
    ],
)
def test_closure_requires_exact_version_xids(field, value):
    example = deepcopy(EXAMPLE)
    if field == "entries":
        example[field][0] = value
    else:
        example["bindings"][0][field] = value

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(example, SCHEMA)


@pytest.mark.parametrize(
    ("index", "expected_query", "expected_subject"),
    [
        (
            0,
            {"wotid": "urn:fabrikam:lamp:42", "wotversion": "1.0.0"},
            "#/events/overheated",
        ),
        (1, {"wotid": "urn:fabrikam:lamp:42"}, "#"),
    ],
    ids=["exact-version-affordance", "current-default-whole-td"],
)
def test_cloudevents_source_and_subject_match_lamp_td(
    index, expected_query, expected_subject
):
    events = json.loads((ROOT / "samples" / "cloudevents.json").read_bytes())
    assert len(events) == 2
    event = events[index]
    assert set(event) == {
        "specversion",
        "id",
        "source",
        "type",
        "subject",
        "datacontenttype",
        "data",
    }
    assert event["specversion"] == "1.0"
    assert event["id"] == f"lamp-42-overheated-{index + 1}"
    assert event["type"] == "com.fabrikam.lamp.overheated"
    assert re.fullmatch(
        r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+",
        event["type"],
    )
    assert event["datacontenttype"] == "application/json"

    source = urlsplit(event["source"])
    assert source.scheme == "wot-td"
    assert source.netloc == "factory-floor-01"
    assert source.path == source.fragment == ""
    parameters = source.query.split(";")
    assert len(parameters) == len(expected_query)
    query = dict(unquote(value).split("=", 1) for value in parameters)
    assert query == expected_query
    assert source.query == ";".join(
        f"{key}={quote(value, safe='', encoding='utf-8', errors='strict')}"
        for key, value in expected_query.items()
    )
    assert "#" not in event["source"]
    assert "wotid=urn%3Afabrikam%3Alamp%3A42" in source.query

    registry = json.loads((ROOT / "samples" / "registry.json").read_bytes())
    resources = registry["thingdescriptiongroups"]["Fabrikam.FactoryFloor.01"][
        "thingdescriptions"
    ]
    matches = [
        value for value in resources.values() if value["wotid"] == query["wotid"]
    ]
    assert len(matches) == 1
    resource = matches[0]
    assert resource is resources["urn.fabrikam.lamp.42"]
    td = resource["thingdescription"]
    assert td["id"] == query["wotid"]
    assert resource["versionid"] == td["version"]["instance"] == "1.0.0"
    if "wotversion" in query:
        assert query["wotversion"] == resource["versionid"]

    assert event["subject"] == expected_subject
    selected = td
    pointer = unquote(event["subject"][1:])
    for token in pointer.split("/")[1:]:
        selected = selected[token.replace("~1", "/").replace("~0", "~")]
    if index == 0:
        assert selected is td["events"]["overheated"]
    else:
        assert selected is td
    jsonschema.validate(event["data"], td["events"]["overheated"]["data"])
