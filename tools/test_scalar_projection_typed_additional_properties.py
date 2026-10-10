"""Published-profile codec regressions without generator or Registry dependencies."""

import copy
from decimal import Decimal
import json

import pytest

from scalar_projection import (
    JsonNumber, ProfileMismatchError, ProjectionCodec, ProjectionError,
    dump_core_json, projection_profile, scalar_schema,
)


def contract(additional, definitions=None):
    return {
        "$schema": "https://json-structure.org/meta/extended/v0/#",
        "$uses": ["JSONStructureAlternateNames"],
        "name": "TypedAdditionalProperties", "type": "object",
        "properties": {
            "displayName": {"type": "string", "altnames": {"json": "display-name"}},
        },
        "required": ["displayName"],
        "additionalProperties": copy.deepcopy(additional),
        "definitions": copy.deepcopy(definitions or {}),
        "x-xregistryProjection": projection_profile(),
    }


def scalar(kind):
    return scalar_schema({"type": kind}, "json-structure")


@pytest.mark.parametrize("kind, token", [
    ("integer", "9007199254740993"),
    ("integer", "100e-2"),
    ("uinteger", "18446744073709551616"),
    ("decimal", "0.123456789012345678901234567890"),
    ("decimal", "1e1000"),
])
def test_numeric_extras_roundtrip_as_core_numbers_beside_named_strings(kind, token):
    schema = contract(scalar(kind))
    source = {"display-name": token, "extra": JsonNumber(token)}
    schema_before, source_before = copy.deepcopy(schema), copy.deepcopy(source)
    codec = ProjectionCodec(schema, "json-structure")
    encoded = codec.write(source)
    envelope = json.loads(encoded)
    assert envelope["data"] == {"display-name": token, "extra": token}
    reader = ProjectionCodec.from_artifact(envelope["contract"])
    restored = reader.read(encoded)
    assert type(restored["display-name"]) is str and restored["display-name"] == token
    assert isinstance(restored["extra"], JsonNumber) and restored["extra"].token == token
    core = json.loads(dump_core_json(restored), parse_float=Decimal)
    assert type(core["extra"]) in (int, Decimal) and core["extra"] == Decimal(token)
    assert type(core["display-name"]) is str and core["display-name"] == token
    assert dump_core_json(restored, sort_keys=True) == dump_core_json(source, sort_keys=True)
    assert schema == schema_before and source == source_before


@pytest.mark.parametrize("kind, bad_core, bad_wire", [
    pytest.param("integer", "7", 7, id="string-core-number-wire"),
    pytest.param("integer", True, True, id="boolean-is-not-integer"),
    pytest.param("integer", JsonNumber("1.5"), "1.5", id="fraction-is-not-integer"),
    pytest.param("uinteger", JsonNumber("-1"), "-1", id="unsigned-lower-bound"),
    pytest.param("decimal", "0.1", "not-a-number", id="decimal-kind-and-token"),
    pytest.param("timestamp", 7, "not-a-timestamp", id="timestamp-kind-and-token"),
])
def test_typed_extras_reject_wrong_core_kinds_and_physical_read_values(kind, bad_core, bad_wire):
    codec = ProjectionCodec(contract(scalar(kind)), "json-structure")
    valid = (
        "2026-01-01T00:00:00.123456789012345678901234567890Z"
        if kind == "timestamp" else JsonNumber("7")
    )
    encoded = codec.write({"display-name": "7", "extra": valid})
    restored = codec.read(encoded)
    assert restored["display-name"] == "7"
    assert dump_core_json(restored["extra"]) == dump_core_json(valid)
    invalid = {"display-name": "7", "extra": bad_core}
    before = copy.deepcopy(invalid)
    with pytest.raises(ProjectionError):
        codec.write(invalid)
    assert invalid == before
    envelope = json.loads(encoded)
    envelope["data"]["extra"] = bad_wire
    with pytest.raises(ProjectionError):
        codec.read(json.dumps(envelope).encode("utf-8"))


def test_named_string_required_and_alternate_name_contracts_are_not_retyped():
    codec = ProjectionCodec(contract(scalar("integer")), "json-structure")
    valid = {"display-name": "7", "extra": JsonNumber("7")}
    encoded = codec.write(valid)
    assert codec.read(encoded)["display-name"] == "7"
    for invalid in (
        {"extra": JsonNumber("7")},
        {"display-name": JsonNumber("7"), "extra": JsonNumber("7")},
        {"displayName": "7", "extra": JsonNumber("7")},
    ):
        with pytest.raises(ProjectionError):
            codec.write(invalid)
    for invalid in ({"extra": "7"}, {"display-name": 7, "extra": "7"}):
        envelope = json.loads(encoded)
        envelope["data"] = invalid
        with pytest.raises(ProjectionError):
            codec.read(json.dumps(envelope).encode("utf-8"))


@pytest.mark.parametrize("container", ["object", "array", "map"])
def test_nested_typed_extra_references_enforce_value_kinds_required_and_closed_members(container):
    counter = {
        "type": "object", "properties": {"count": scalar("integer")},
        "required": ["count"], "additionalProperties": False,
    }
    reference = {"type": {"$ref": "#/definitions/Values/Counter"}}
    additional = reference if container == "object" else {
        "type": container, "items" if container == "array" else "values": reference,
    }
    schema = contract(additional, {"Values": {"Counter": counter}})
    before_schema = copy.deepcopy(schema)
    codec = ProjectionCodec(schema, "json-structure")

    def wrap(leaf):
        return leaf if container == "object" else [leaf] if container == "array" else {"item": leaf}

    source = {"display-name": "7", "extra": wrap({"count": 7})}
    before = copy.deepcopy(source)
    encoded = codec.write(source)
    assert json.loads(encoded)["data"] == {"display-name": "7", "extra": wrap({"count": "7"})}
    assert json.loads(dump_core_json(codec.read(encoded))) == source
    for leaf in ({"count": "7"}, {}, {"count": 7, "unmodeled": True}):
        with pytest.raises(ProjectionError):
            codec.write({"display-name": "7", "extra": wrap(leaf)})
    for leaf in ({"count": 7}, {}, {"count": "7", "unmodeled": True}):
        envelope = json.loads(encoded)
        envelope["data"]["extra"] = wrap(leaf)
        with pytest.raises(ProjectionError):
            codec.read(json.dumps(envelope).encode("utf-8"))
    assert source == before and schema == before_schema


@pytest.mark.parametrize("open_object", [False, True])
def test_untyped_open_and_closed_extra_boundaries_remain_distinct(open_object):
    codec = ProjectionCodec(contract(open_object), "json-structure")
    minimal = {"display-name": "7"}
    encoded = codec.write(minimal)
    assert json.loads(dump_core_json(codec.read(encoded))) == minimal
    value = {"display-name": "7", "extra": {"items": [None, True, JsonNumber("1e1000")]}}
    envelope = json.loads(encoded)
    envelope["data"] = value
    if open_object:
        restored = codec.read(codec.write(value))
        assert dump_core_json(restored, sort_keys=True) == dump_core_json(value, sort_keys=True)
        assert isinstance(restored["extra"]["items"][2], JsonNumber)
        assert restored["extra"]["items"][2].token == "1e1000"
    else:
        with pytest.raises(ProjectionError):
            codec.write(value)
        with pytest.raises(ProjectionError):
            codec.read(dump_core_json(envelope).encode("utf-8"))


def test_additional_value_type_is_part_of_full_writer_identity_even_with_identical_wire_data():
    integer_schema = contract(scalar("integer"))
    decimal_schema = contract(scalar("decimal"))
    changed = copy.deepcopy(integer_schema)
    changed["additionalProperties"]["x-xregistryScalar"]["coreType"] = "decimal"
    assert changed == decimal_schema
    assert integer_schema["additionalProperties"]["type"] == decimal_schema["additionalProperties"]["type"] == "string"
    integer = ProjectionCodec(integer_schema, "json-structure")
    decimal = ProjectionCodec(decimal_schema, "json-structure")
    value = {"display-name": "7", "extra": JsonNumber("7")}
    encoded = integer.write(value)
    assert json.loads(encoded)["data"] == json.loads(decimal.write(value))["data"]
    assert integer.fingerprint != decimal.fingerprint
    with pytest.raises(ProfileMismatchError):
        decimal.read(encoded)
    tampered = json.loads(dump_core_json(integer.artifact))
    tampered["schema"]["additionalProperties"]["x-xregistryScalar"]["coreType"] = "decimal"
    with pytest.raises(ProfileMismatchError):
        ProjectionCodec.from_artifact(tampered)
