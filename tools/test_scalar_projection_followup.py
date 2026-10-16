"""Codec-only regressions; no generator, Registry artifacts or SDK dependency."""

import copy
import json

import pytest

from scalar_projection import (
    JsonNumber, MigrationError, ProfileMismatchError, ProjectionCodec,
    ProjectionError, dump_core_json, projection_profile,
)


def contract(value_schema, *, validation=False):
    return {
        "$schema": "https://json-structure.org/meta/extended/v0/#",
        "$uses": ["JSONStructureValidation"] if validation else [],
        "name": "ScalarFollowup", "type": "object",
        "properties": {"value": value_schema}, "additionalProperties": False,
        "definitions": {}, "x-xregistryProjection": projection_profile(),
    }


def empty_map_contract(*, referenced=False):
    empty = {"type": "map", "values": {"type": "any"}, "maxEntries": 0}
    schema = contract(empty, validation=True)
    if referenced:
        schema["definitions"] = {"Closed": {"Empty": empty}}
        schema["properties"]["value"] = {"type": {"$ref": "#/definitions/Closed/Empty"}}
    return schema


@pytest.mark.parametrize("referenced", [False, True])
@pytest.mark.parametrize("extra_count", [1, 2])
def test_max_entries_enforced_on_write_and_read(referenced, extra_count):
    codec = ProjectionCodec(empty_map_contract(referenced=referenced), "json-structure")
    encoded = codec.write({"value": {}})
    assert json.loads(dump_core_json(codec.read(encoded))) == {"value": {}}
    assert json.loads(dump_core_json(codec.read(codec.write({})))) == {}
    extras = {f"extra{index}": None for index in range(extra_count)}
    with pytest.raises(ProjectionError, match="maxEntries"):
        codec.write({"value": extras})
    envelope = json.loads(encoded)
    envelope["data"]["value"] = extras
    with pytest.raises(ProjectionError, match="maxEntries"):
        codec.read(json.dumps(envelope).encode("utf-8"))


@pytest.mark.parametrize("mutation", [
    "missing-feature", "wrong-feature", "negative", "fraction", "string", "boolean", "null",
])
def test_map_limit_requires_valid_feature_and_integer_bound(mutation):
    schema = empty_map_contract()
    if mutation == "missing-feature":
        schema["$uses"] = []
    elif mutation == "wrong-feature":
        schema["$uses"] = ["JSONSchemaValidation"]
    else:
        schema["properties"]["value"]["maxEntries"] = {
            "negative": JsonNumber("-1"), "fraction": JsonNumber("0.5"),
            "string": "0", "boolean": True, "null": None,
        }[mutation]
    with pytest.raises(ProfileMismatchError, match="maxEntries"):
        ProjectionCodec(schema, "json-structure")


def test_entry_limit_remains_part_of_writer_identity():
    schema = empty_map_contract()
    writer = ProjectionCodec(schema, "json-structure")
    changed = copy.deepcopy(schema)
    changed["properties"]["value"].pop("maxEntries")
    reader = ProjectionCodec(changed, "json-structure")
    assert writer.fingerprint != reader.fingerprint
    with pytest.raises(ProfileMismatchError):
        reader.read(writer.write({"value": {}}))


@pytest.mark.parametrize("value", [{}, {"nested": [JsonNumber("1e1000"), "1e1000"]}])
def test_object_to_map_migration_requires_authoritative_core(value):
    previous = contract({"type": "object", "properties": {}, "additionalProperties": True})
    current = contract({"type": "map", "values": {"type": "any"}})
    writer = ProjectionCodec(previous, "json-structure")
    reader = ProjectionCodec(current, "json-structure")
    source = {"value": value}
    encoded = writer.write(source)
    with pytest.raises(ProfileMismatchError):
        reader.read(encoded)
    with pytest.raises(MigrationError, match="authoritative"):
        reader.migrate_json_structure(encoded, writer.schema)
    migrated = reader.migrate_json_structure(
        encoded, writer.schema, authoritative_core_json=dump_core_json(source),
    )
    restored = reader.read(migrated)
    assert dump_core_json(restored, sort_keys=True) == dump_core_json(source, sort_keys=True)
    assert type(restored["value"]) is dict
    if value:
        assert restored["value"]["nested"][0].token == "1e1000"
        assert restored["value"]["nested"][1] == "1e1000"
    envelope = json.loads(migrated)
    assert envelope["migration"]["strategy"] == "authoritative-core"
    assert envelope["migration"]["writerSchema"] == previous
