"""Exercise required Core usage declarations and actual generated projections.

The Endpoint `usage` roles now live in the element definition as
`usage.item.enum`, so every dialect that can express a value set restricts the
actual array elements. The array itself carries no `enum`: Core does not permit
one on the owning array, and the nonempty, uniqueness and protocol-combination
rules stay separate domain checks that no generated artifact expresses.
"""

import io
import json
import subprocess
import sys
from pathlib import Path

import avro.io
import avro.schema
import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
ROLES = ["subscriber", "consumer", "producer"]


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


def _avro_usage(projections):
    document = avro.schema.parse(json.dumps(projections["avro-schema"]))
    endpoint = next(field for field in document.fields if field.name == "endpoints")
    return next(
        field for field in endpoint.type.values.fields if field.name == "usage"
    )


def _avro_round_trip(schema, datum):
    buffer = io.BytesIO()
    avro.io.DatumWriter(schema).write(datum, avro.io.BinaryEncoder(buffer))
    buffer.seek(0)
    return avro.io.DatumReader(schema).read(avro.io.BinaryDecoder(buffer))


def test_source_usage_is_a_required_array_of_enumerated_role_strings():
    model = json.loads((ROOT / "endpoint" / "model.json").read_text("utf-8"))
    usage = model["groups"]["endpoints"]["attributes"]["usage"]
    assert usage["type"] == "array"
    assert usage["required"] is True
    assert usage["item"] == {"type": "string", "enum": ROLES}
    # Core does not permit a value set on the owning array, only on its item.
    assert "enum" not in usage
    assert "strict" not in usage
    assert "default" not in usage
    # The element set is enforced; `strict` is absent so it defaults to true.
    assert "strict" not in usage["item"]


def test_all_projections_restrict_usage_elements_to_the_declared_roles(projections):
    endpoint = _schema_endpoint(projections)
    assert "usage" in endpoint["required"]
    assert endpoint["properties"]["usage"]["type"] == "array"
    assert endpoint["properties"]["usage"]["items"] == {"type": "string", "enum": ROLES}
    assert "enum" not in endpoint["properties"]["usage"]

    structure = projections["json-structure"]["definitions"]["Endpoints"]["Endpoint"]
    assert "usage" in structure["required"]
    assert structure["properties"]["usage"]["type"] == "array"
    assert structure["properties"]["usage"]["items"] == {
        "type": "string", "enum": ROLES
    }
    assert "enum" not in structure["properties"]["usage"]

    openapi = projections["openapi"]["components"]["schemas"]["endpoint"]
    assert "usage" in openapi["required"]
    assert openapi["properties"]["usage"]["type"] == "array"
    assert openapi["properties"]["usage"]["items"] == {"type": "string", "enum": ROLES}
    assert "enum" not in openapi["properties"]["usage"]

    usage = _avro_usage(projections)
    assert usage.type.type == "array"
    assert usage.type.items.type == "enum"
    assert usage.type.items.name == "UsageEnumType"
    assert usage.type.items.namespace == "io.xregistry"
    assert list(usage.type.items.symbols) == ROLES


@pytest.mark.parametrize("role", ROLES)
def test_avro_round_trips_every_declared_role(projections, role):
    usage = _avro_usage(projections)
    assert _avro_round_trip(usage.type, [role]) == [role]


def test_avro_rejects_an_unknown_role(projections):
    usage = _avro_usage(projections)
    assert avro.io.validate(usage.type, list(ROLES))
    assert not avro.io.validate(usage.type, ["publisher"])


def test_avro_keeps_exactly_one_usage_enum_definition(projections):
    document = json.dumps(projections["avro-schema"])
    assert document.count('"UsageEnumType"') == 1


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


@pytest.mark.parametrize("role", ROLES)
def test_generated_schema_accepts_each_declared_role(projections, role):
    document = {"endpoints": {"e": {"usage": [role]}}}
    errors = list(
        jsonschema.Draft7Validator(projections["json-schema"]).iter_errors(document)
    )
    assert not [error for error in errors if "usage" in list(error.path)]


@pytest.mark.parametrize("unknown", ["publisher", "Consumer", "", "consumer "])
def test_generated_schema_rejects_an_unknown_role(projections, unknown):
    document = {"endpoints": {"e": {"usage": [unknown]}}}
    errors = list(
        jsonschema.Draft7Validator(projections["json-schema"]).iter_errors(document)
    )
    assert errors, f"{unknown!r} is not a declared usage role"


def test_domain_rules_stay_separate_from_the_generated_value_set(projections):
    """The value set is not the nonempty, uniqueness or combination rule.

    These documents satisfy every generated artifact and are still invalid
    Endpoints; only domain validation rejects them.
    """
    validator = jsonschema.Draft7Validator(projections["json-schema"])
    for usage in [[], ["consumer", "consumer"], ["producer", "consumer"]]:
        document = {"endpoints": {"e": {"usage": usage}}}
        assert not list(validator.iter_errors(document)), (
            f"{usage!r} must remain a domain-validation concern, "
            "not something the generated schema is claimed to catch"
        )
