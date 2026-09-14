"""Lossless scalar projection regressions on the actual generator."""

import copy
import importlib.util
import io
import json
import subprocess
import sys
from decimal import Decimal
from datetime import time
from pathlib import Path

import avro.datafile
import avro.io
import avro.errors
import avro.schema
import pytest

from scalar_projection import (
    JsonNumber,
    MigrationError,
    ProfileMismatchError,
    ProjectionCodec,
    ProjectionError,
    decode_scalar,
    dump_core_json,
    parse_core_json,
)
from test_scalar_projection import INTEGER_TOKENS, TIMESTAMPS


ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "schema_generator", ROOT / "tools" / "schema-generator.py"
)
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)
PROFILE_ID = "https://xregistry.io/profiles/scalar-projection/1"


def scalar_model(kind):
    return {
        "groups": {
            "samples": {
                "singular": "sample",
                "attributes": {"value": {"type": kind, "required": True}},
            }
        }
    }


def avro_group(schema):
    return next(
        field["type"]["values"]
        for field in schema["fields"] if field["name"] == "samples"
    )


@pytest.mark.parametrize("kind", ["integer", "uinteger", "decimal", "timestamp"])
def test_generated_avro_scalar_uses_lossless_string(kind):
    schema = GENERATOR.generate_avro_schema(scalar_model(kind))
    field = next(
        field for field in avro_group(schema)["fields"]
        if field["name"] == "value"
    )
    assert field["type"] == "string"
    assert field["x-xregistryScalar"]["coreType"] == kind
    assert "logicalType" not in field
    assert schema["x-xregistryProjection"]["id"] == PROFILE_ID


@pytest.mark.parametrize(
    "kind, expected",
    [
        ("integer", "string"),
        ("uinteger", "string"),
        ("decimal", "string"),
        ("timestamp", "datetime"),
    ],
)
def test_generated_structure_scalar_uses_standard_type(kind, expected):
    schema = GENERATOR.generate_json_structure(scalar_model(kind))
    value = schema["definitions"]["Samples"]["Sample"]["properties"]["value"]
    assert value["type"] == expected
    assert value["x-xregistryScalar"]["coreType"] == kind
    assert schema["x-xregistryProjection"]["id"] == PROFILE_ID


@pytest.mark.parametrize(
    "kind, expected",
    [("integer", "integer"), ("uinteger", "integer"), ("decimal", "number")],
)
def test_json_schema_keeps_numeric_source_types(kind, expected):
    schema = GENERATOR.generate_json_schema(copy.deepcopy(scalar_model(kind)))
    value = schema["definitions"]["sample-schema"]["sample"]["properties"][
        "value"
    ]
    assert value["type"] == expected


def document(value):
    return {"samples": {"s": {
        "sampleid": "s",
        "name": "sample",
        "epoch": JsonNumber("18446744073709551616"),
        "self": "https://example.com/samples/s",
        "xid": "/samples/s",
        "description": "sample",
        "documentation": "https://example.com/docs",
        "labels": {"kind": "sample"},
        "createdat": "2026-01-01T00:00:00.123456789012345678901234567890Z",
        "modifiedat": "2026-01-01T00:00:00.123456789012345678901234567891Z",
        "value": value,
    }}}


def generated_codec(definition, dialect):
    model = scalar_model(definition["type"])
    model["groups"]["samples"]["attributes"]["value"] = definition
    schema = (
        GENERATOR.generate_avro_schema(model) if dialect == "avro"
        else GENERATOR.generate_json_structure(model)
    )
    return ProjectionCodec(schema, dialect)


def write_physical_avro(
    codec, value, *, artifact=None, header_schema=None, records=None
):
    schema = avro.schema.parse(dump_core_json(codec.schema))
    output = io.BytesIO()
    with avro.datafile.DataFileWriter(output, avro.io.DatumWriter(), schema) as writer:
        writer.set_meta(
            "xregistry.scalarProjection",
            dump_core_json(codec.artifact if artifact is None else artifact).encode(),
        )
        writer.set_meta(
            "avro.schema",
            dump_core_json(codec.schema if header_schema is None else header_schema).encode(),
        )
        for record in [value] if records is None else records:
            writer.append(record)
        writer.flush()
        return output.getvalue()


ROUND_TRIPS = (
    [("integer", token) for token in INTEGER_TOKENS]
    + [("uinteger", token) for token in INTEGER_TOKENS if not token.startswith("-")]
    + [("decimal", token) for token in (
        "1e1000", "1e-1000", "-0.0",
        "0.100000000000000000000000000001",
        "0.100000000000000000000000000002",
    )]
    + [("timestamp", token) for token in TIMESTAMPS]
)


@pytest.mark.parametrize("dialect", ["avro", "json-structure"])
@pytest.mark.parametrize("kind, token", ROUND_TRIPS)
def test_generated_schema_round_trips_exact_scalars_and_core_kinds(
    dialect, kind, token
):
    codec = generated_codec({"type": kind, "required": True}, dialect)
    value = token if kind == "timestamp" else parse_core_json(token)
    source = document(value)
    encoded = codec.write(source)
    restored = codec.read(encoded)
    result = restored["samples"]["s"]
    if dialect == "avro":
        assert encoded.startswith(b"Obj\x01")
        with avro.datafile.DataFileReader(
            io.BytesIO(encoded), avro.io.DatumReader()
        ) as reader:
            physical = next(reader)["samples"]["s"]
            assert physical["value"] == token
            assert physical["epoch"] == "18446744073709551616"
    else:
        physical = json.loads(encoded)["data"]["samples"]["s"]
        assert physical["value"] == token
        assert physical["epoch"] == "18446744073709551616"
    assert result["createdat"] == source["samples"]["s"]["createdat"]
    assert result["modifiedat"] == source["samples"]["s"]["modifiedat"]
    assert result["createdat"] != result["modifiedat"]
    if kind == "timestamp":
        assert result["value"] == token
    else:
        assert isinstance(result["value"], JsonNumber)
        assert result["value"].token == token
        restored_json = dump_core_json(restored)
        native = json.loads(restored_json, parse_float=Decimal)["samples"]["s"]["value"]
        assert isinstance(native, (int, Decimal)) and not isinstance(native, bool)
        assert '"value":' + token in restored_json
    assert result["epoch"].token == "18446744073709551616"


@pytest.mark.parametrize("dialect", ["avro", "json-structure"])
@pytest.mark.parametrize("kind", ["integer", "timestamp"])
def test_generated_optional_scalars_distinguish_absence_null_and_value(
    dialect, kind
):
    codec = generated_codec({"type": kind}, dialect)
    value = JsonNumber("7") if kind == "integer" else TIMESTAMPS[3]
    for state in ("absent", "null", "value"):
        source = document(value)
        if state == "absent":
            del source["samples"]["s"]["value"]
        elif state == "null":
            source["samples"]["s"]["value"] = None
        restored = codec.read(codec.write(source))["samples"]["s"]
        if state == "absent":
            assert "value" not in restored
        elif state == "null":
            assert "value" in restored and restored["value"] is None
        elif kind == "integer":
            assert restored["value"].token == "7"
        else:
            assert restored["value"] == value


@pytest.mark.parametrize("dialect", ["avro", "json-structure"])
def test_generated_required_scalar_defaults_are_not_implicit_write_values(dialect):
    codec = generated_codec(
        {"type": "decimal", "required": True, "default": JsonNumber("1e1000")},
        dialect,
    )
    for state in ("missing", "null"):
        source = document(None)
        if state == "missing":
            del source["samples"]["s"]["value"]
        with pytest.raises(ProjectionError):
            codec.write(source)


@pytest.mark.parametrize("dialect", ["avro", "json-structure"])
def test_generated_maps_arrays_and_structured_scalar_constraints_round_trip(dialect):
    codec = generated_codec({
        "type": "array", "required": True,
        "item": {"type": "map", "item": {"type": "decimal"}},
    }, dialect)
    source = document([{
        "huge": JsonNumber("1e1000"),
        "precise": JsonNumber("0.100000000000000000000000000001"),
    }])
    result = codec.read(codec.write(source))["samples"]["s"]["value"]
    assert result[0]["huge"].token == "1e1000"
    assert result[0]["precise"].token == "0.100000000000000000000000000001"
    with pytest.raises(ProjectionError):
        codec.write(document([{"bad": True}]))
    with pytest.raises(ProjectionError):
        codec.write(document([{"bad": None}]))


@pytest.mark.parametrize("dialect", ["avro", "json-structure"])
@pytest.mark.parametrize("container", ["object", "array", "map"])
def test_generated_structured_values_enforce_nested_numeric_rules(dialect, container):
    item = {
        "type": "object", "required": True,
        "attributes": {
            "amount": {
                "type": "decimal", "required": True,
                "enum": [JsonNumber("1"), JsonNumber("1e1000")],
            },
            "ranks": {"type": "array", "item": {"type": "uinteger"}},
        },
    }
    definition = (
        item if container == "object"
        else {"type": container, "item": item, "required": True}
    )
    codec = generated_codec(definition, dialect)
    value = {"amount": JsonNumber("1.0"),
             "ranks": [JsonNumber("18446744073709551616"), JsonNumber("-0")]}
    wrap = (
        (lambda value: value) if container == "object"
        else (lambda value: [value]) if container == "array"
        else (lambda value: {"entry": value})
    )
    restored = codec.read(codec.write(document(wrap(value))))["samples"]["s"]["value"]
    leaf = restored if container == "object" else (
        restored[0] if container == "array" else restored["entry"]
    )
    assert leaf["amount"].token == "1.0"
    assert [item.token for item in leaf["ranks"]] == ["18446744073709551616", "-0"]
    for mutation in ({"amount": JsonNumber("2")}, {"amount": True},
                     {"ranks": [JsonNumber("-1")]}, {"ranks": [None]}):
        with pytest.raises(ProjectionError):
            codec.write(document(wrap({**value, **mutation})))


def test_generated_generic_values_preserve_recursive_numbers_and_string_kinds():
    codec = generated_codec({"type": "any", "required": True}, "avro")
    for value in (
        JsonNumber("1e1000"), "1e1000",
        {"nested": [[JsonNumber("1e1000")], {
            "value": JsonNumber("0.100000000000000000000000000001"),
            "text": "1e1000",
        }]},
    ):
        restored = codec.read(codec.write(document(value)))["samples"]["s"]["value"]
        assert dump_core_json(restored) == dump_core_json(value)
        if isinstance(value, JsonNumber):
            assert isinstance(restored, JsonNumber) and restored.token == "1e1000"
        elif isinstance(value, str):
            assert type(restored) is str and restored == "1e1000"
        else:
            assert restored["nested"][0][0].token == "1e1000"
            assert restored["nested"][1]["value"].token.endswith("001")
            assert restored["nested"][1]["text"] == "1e1000"


@pytest.mark.parametrize("dialect", ["avro", "json-structure"])
def test_generated_scalar_reader_rejects_physically_valid_semantic_violations(dialect):
    codec = generated_codec(
        {"type": "uinteger", "required": True, "enum": [1]}, dialect
    )
    with pytest.raises(ProjectionError):
        codec.write(document(True))
    physical = codec.to_derived(document(JsonNumber("1e0")))
    for token in ("NaN", "-1", "1.5", "2", "01"):
        physical["samples"]["s"]["value"] = token
        if dialect == "avro":
            parsed = avro.schema.parse(dump_core_json(codec.schema))
            assert avro.io.validate(parsed, physical)
            encoded = write_physical_avro(codec, physical)
        else:
            encoded = dump_core_json(
                {"contract": codec.artifact, "data": physical}
            ).encode()
        with pytest.raises(ProjectionError):
            codec.read(encoded)


def test_full_contract_identity_survives_canonical_fingerprint_collisions():
    codec = generated_codec({"type": "integer", "required": True}, "avro")
    altered = codec.schema
    field = next(field for field in avro_group(altered)["fields"]
                 if field["name"] == "value")
    field["x-xregistryScalar"]["constraints"]["minimum"] = "2"
    other = ProjectionCodec(altered, "avro")
    assert avro.schema.parse(dump_core_json(codec.schema)).fingerprint() == (
        avro.schema.parse(dump_core_json(other.schema)).fingerprint()
    )
    assert codec.fingerprint != other.fingerprint
    encoded = codec.write(document(JsonNumber("7")))
    with pytest.raises(ProfileMismatchError):
        other.read(encoded)
    artifact = codec.artifact
    artifact["schema"] = altered
    with pytest.raises(ProfileMismatchError):
        ProjectionCodec.from_artifact(artifact)
    artifact = codec.artifact
    artifact["profile"]["version"] = "2"
    with pytest.raises(ProfileMismatchError):
        ProjectionCodec.from_artifact(artifact)
    physical = codec.to_derived(document(JsonNumber("7")))
    with pytest.raises(ProfileMismatchError):
        codec.read(write_physical_avro(codec, physical, header_schema=altered))


@pytest.mark.parametrize("dialect", ["avro", "json-structure"])
def test_codec_captures_immutable_full_schema_and_profile(dialect):
    codec = generated_codec({"type": "integer", "required": True}, dialect)
    artifact = codec.artifact
    artifact["schema"]["name"] = "Changed"
    artifact["profile"]["numbers"] = "float"
    assert codec.artifact["profile"]["numbers"].startswith("exact-json-number")
    assert codec.schema["name"] != "Changed"
    restored = ProjectionCodec.from_artifact(codec.artifact)
    value = restored.read(codec.write(document(JsonNumber("1e1000"))))
    assert value["samples"]["s"]["value"].token == "1e1000"


@pytest.mark.parametrize("dialect", ["avro-schema", "json-structure"])
def test_cli_preserves_actual_source_default_and_constraint_tokens(tmp_path, dialect):
    model = tmp_path / "model.json"
    output = tmp_path / "schema.json"
    model.write_text(
        '{"groups":{"samples":{"singular":"sample","attributes":{"value":'
        '{"type":"decimal","required":true,"default":1e1000,"enum":'
        '[1e1000,0.100000000000000000000000000001]}}}}}',
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, "-B", str(ROOT / "tools" / "schema-generator.py"),
         "--type", dialect, "--output", str(output), str(model)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    schema = json.loads(output.read_text(encoding="utf-8"))
    field = (
        next(field for field in avro_group(schema)["fields"]
             if field["name"] == "value")
        if dialect == "avro-schema"
        else schema["definitions"]["Samples"]["Sample"]["properties"]["value"]
    )
    assert field["default"] == "1e1000"
    assert field["x-xregistryScalar"]["constraints"]["enum"] == [
        "1e1000", "0.100000000000000000000000000001"
    ]
    assert decode_scalar(field["default"], field["x-xregistryScalar"]).token == "1e1000"


def legacy_schema(codec, primitive="int"):
    schema = codec.schema
    schema.pop("x-xregistryProjection")
    for field in avro_group(schema)["fields"]:
        contract = field.pop("x-xregistryScalar", None)
        if contract:
            optional = field.pop("x-xregistryOptional", False)
            if contract["coreType"] == "timestamp":
                field["type"] = [
                    {"type": "int", "logicalType": "time-millis"}, "null"
                ]
            else:
                field["type"] = [primitive, "null"] if optional else primitive
            field.pop("default", None)
    return schema


def legacy_document(value):
    source = document(value)
    source["samples"]["s"].update(epoch=5, createdat=None, modifiedat=None)
    return source


def write_legacy_avro(schema, source):
    parsed = avro.schema.parse(dump_core_json(schema))
    output = io.BytesIO()
    with avro.datafile.DataFileWriter(output, avro.io.DatumWriter(), parsed) as writer:
        writer.set_meta("avro.schema", dump_core_json(schema).encode())
        writer.append(source)
        writer.flush()
        return output.getvalue()


@pytest.mark.parametrize("primitive, value", [
    ("int", -2147483648), ("int", 2147483647),
    ("long", 9007199254740993), ("long", 9223372036854775807),
])
def test_actual_legacy_avro_integer_writer_migrates_to_profile(primitive, value):
    codec = generated_codec({"type": "integer", "required": True}, "avro")
    old_schema = legacy_schema(codec, primitive)
    encoded = write_legacy_avro(old_schema, legacy_document(value))
    with pytest.raises(ProfileMismatchError, match="migration"):
        codec.read(encoded)
    transition = codec.transition_reader_schema(old_schema)
    value_field = next(field for field in avro_group(transition)["fields"]
                       if field["name"] == "value")
    assert "string" in value_field["type"]
    assert primitive in value_field["type"]
    assert "x-xregistryProjection" not in transition
    migrated = codec.migrate_avro(encoded, old_schema)
    restored = codec.read(migrated)["samples"]["s"]
    assert restored["value"].token == str(value)
    assert restored["epoch"].token == "5"
    assert restored["createdat"] is None
    with avro.datafile.DataFileReader(io.BytesIO(migrated), avro.io.DatumReader()) as reader:
        provenance = parse_core_json(reader.get_meta("xregistry.scalarMigration"))
        assert provenance["writerSchema"] == old_schema
        assert provenance["strategy"] == "retained-values"


def test_actual_reader_schema_applies_converted_numeric_default():
    codec = generated_codec({
        "type": "decimal", "required": True, "default": JsonNumber("1e1000")
    }, "avro")
    old_schema = legacy_schema(codec)
    group = avro_group(old_schema)
    group["fields"] = [field for field in group["fields"] if field["name"] != "value"]
    source = legacy_document(None)
    del source["samples"]["s"]["value"]
    encoded = write_legacy_avro(old_schema, source)
    reader_schema = avro.schema.parse(dump_core_json(
        codec.transition_reader_schema(old_schema)
    ))
    with avro.datafile.DataFileReader(
        io.BytesIO(encoded), avro.io.DatumReader(readers_schema=reader_schema)
    ) as reader:
        assert next(reader)["samples"]["s"]["value"] == "1e1000"
    restored = codec.read(codec.migrate_avro(encoded, old_schema))
    assert restored["samples"]["s"]["value"].token == "1e1000"
    assert '"value":1e1000' in dump_core_json(restored)


@pytest.mark.parametrize("state", ["absent", "null", "value"])
def test_qualified_string_writer_migrates_without_losing_presence(state):
    codec = generated_codec({"type": "integer"}, "avro")
    source = document(JsonNumber("-0.000e1000"))
    if state == "absent":
        del source["samples"]["s"]["value"]
    elif state == "null":
        source["samples"]["s"]["value"] = None
    migrated = codec.migrate_avro(codec.write(source), codec.schema)
    restored = codec.read(migrated)["samples"]["s"]
    if state == "absent":
        assert "value" not in restored
    elif state == "null":
        assert restored["value"] is None
    else:
        assert restored["value"].token == "-0.000e1000"
    assert restored["createdat"] == source["samples"]["s"]["createdat"]


@pytest.mark.parametrize("primitive, value", [
    ("float", 0.1), ("double", 0.1), ("string", "1e1000")
])
def test_legacy_loss_or_unqualified_strings_require_authoritative_core(primitive, value):
    codec = generated_codec({"type": "decimal", "required": True}, "avro")
    old_schema = legacy_schema(codec)
    field = next(field for field in avro_group(old_schema)["fields"]
                 if field["name"] == "value")
    field["type"] = primitive
    encoded = write_legacy_avro(old_schema, legacy_document(value))
    with pytest.raises(MigrationError, match="authoritative"):
        codec.migrate_avro(encoded, old_schema)
    authoritative = document(JsonNumber("0.100000000000000000000000000001"))
    migrated = codec.migrate_avro(
        encoded, old_schema, authoritative_core_json=dump_core_json(authoritative)
    )
    result = codec.read(migrated)["samples"]["s"]
    assert result["value"].token == "0.100000000000000000000000000001"
    assert result["createdat"] == authoritative["samples"]["s"]["createdat"]


def test_legacy_clock_cannot_reconstruct_date_or_fractional_precision():
    codec = generated_codec({"type": "integer", "required": True}, "avro")
    old_schema = legacy_schema(codec)
    source = legacy_document(7)
    source["samples"]["s"]["createdat"] = time(1, 2, 3, 456000)
    encoded = write_legacy_avro(old_schema, source)
    with pytest.raises(MigrationError, match="authoritative"):
        codec.migrate_avro(encoded, old_schema)
    authoritative = document(JsonNumber("7"))
    migrated = codec.migrate_avro(
        encoded, old_schema, authoritative_core_json=dump_core_json(authoritative)
    )
    assert codec.read(migrated)["samples"]["s"]["createdat"] == (
        "2026-01-01T00:00:00.123456789012345678901234567890Z"
    )


def test_old_avro_reader_rejects_new_string_encoding():
    codec = generated_codec({"type": "integer", "required": True}, "avro")
    old = avro.schema.parse(dump_core_json(legacy_schema(codec)))
    encoded = codec.write(document(JsonNumber("1")))
    with pytest.raises(avro.errors.SchemaResolutionException):
        with avro.datafile.DataFileReader(
            io.BytesIO(encoded), avro.io.DatumReader(readers_schema=old)
        ) as reader:
            next(reader)


def test_legacy_migration_rejects_an_altered_retained_writer_schema():
    codec = generated_codec({"type": "integer", "required": True}, "avro")
    old_schema = legacy_schema(codec)
    encoded = write_legacy_avro(old_schema, legacy_document(7))
    altered = copy.deepcopy(old_schema)
    altered["doc"] = "Different semantic writer"
    assert avro.schema.parse(dump_core_json(altered)).fingerprint() == (
        avro.schema.parse(dump_core_json(old_schema)).fingerprint()
    )
    with pytest.raises(ProfileMismatchError, match="retained"):
        codec.migrate_avro(encoded, altered)


def legacy_structure_schema(codec):
    schema = codec.schema
    schema.pop("x-xregistryProjection")

    def visit(node):
        if isinstance(node, dict):
            contract = node.pop("x-xregistryScalar", None)
            if contract:
                node["type"] = {
                    "integer": "integer", "uinteger": "uint32",
                    "decimal": "float64", "timestamp": "datetime",
                }[contract["coreType"]]
                node.pop("x-xregistryOptional", None)
                node.pop("default", None)
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(schema)
    return schema


def test_legacy_json_structure_migration_keeps_numbers_and_timestamp_text():
    codec = generated_codec({"type": "uinteger", "required": True}, "json-structure")
    old_schema = legacy_structure_schema(codec)
    source = document(JsonNumber("4294967295"))
    source["samples"]["s"]["epoch"] = JsonNumber("5")
    encoded = dump_core_json(source).encode()
    with pytest.raises(ProfileMismatchError):
        codec.read(encoded)
    migrated = codec.migrate_json_structure(encoded, old_schema)
    restored = codec.read(migrated)["samples"]["s"]
    assert restored["value"].token == "4294967295"
    assert restored["createdat"] == source["samples"]["s"]["createdat"]
    envelope = parse_core_json(migrated)
    assert envelope["migration"]["writerSchema"] == old_schema
    assert envelope["migration"]["strategy"] == "retained-values"
    source["samples"]["s"]["value"] = JsonNumber("4294967296")
    with pytest.raises(MigrationError, match="range"):
        codec.migrate_json_structure(dump_core_json(source).encode(), old_schema)
    assert codec.read(codec.write(source))["samples"]["s"]["value"].token == "4294967296"


def test_json_structure_evolution_applies_a_target_typed_scalar_default():
    codec = generated_codec({
        "type": "decimal", "required": True, "default": JsonNumber("1e1000")
    }, "json-structure")
    old_schema = legacy_structure_schema(codec)
    old_schema["definitions"]["Samples"]["Sample"]["properties"].pop("value")
    source = document(None)
    source["samples"]["s"]["epoch"] = JsonNumber("5")
    del source["samples"]["s"]["value"]
    migrated = codec.migrate_json_structure(dump_core_json(source).encode(), old_schema)
    restored = codec.read(migrated)
    assert restored["samples"]["s"]["value"].token == "1e1000"
    assert json.loads(migrated)["data"]["samples"]["s"]["value"] == "1e1000"
    assert '"value":1e1000' in dump_core_json(restored)


def test_legacy_json_float_migration_requires_authoritative_core():
    codec = generated_codec({"type": "decimal", "required": True}, "json-structure")
    old_schema = legacy_structure_schema(codec)
    source = document(JsonNumber("0.1"))
    source["samples"]["s"]["epoch"] = JsonNumber("5")
    encoded = dump_core_json(source).encode()
    with pytest.raises(MigrationError, match="authoritative"):
        codec.migrate_json_structure(encoded, old_schema)
    authoritative = document(JsonNumber("0.100000000000000000000000000001"))
    migrated = codec.migrate_json_structure(
        encoded, old_schema, authoritative_core_json=dump_core_json(authoritative)
    )
    assert codec.read(migrated)["samples"]["s"]["value"].token.endswith("001")


@pytest.mark.parametrize("dialect", ["avro-schema", "json-structure"])
@pytest.mark.parametrize("source_kind", ["include", "resource-uri"])
def test_cli_imported_scalar_source_tokens_remain_exact(tmp_path, dialect, source_kind):
    definition = (
        '{"singular":"entry","plural":"entries","maxversions":1,'
        '"hasdocument":false,"attributes":{"value":{"type":"decimal",'
        '"required":true,"default":0.100000000000000000000000000001}}}'
    )
    external = tmp_path / "resource.json"
    external.write_text('{"entry":' + definition + "}", encoding="utf-8")
    reference = (
        '{"$include":"resource.json#/entry"}' if source_kind == "include"
        else '{"uri":"resource.json#/entry"}'
    )
    model = tmp_path / "model.json"
    model.write_text(
        '{"groups":{"samples":{"singular":"sample","resources":{"entries":'
        + reference + "}}}}", encoding="utf-8",
    )
    output = tmp_path / "schema.json"
    result = subprocess.run(
        [sys.executable, "-B", str(ROOT / "tools" / "schema-generator.py"),
         "--type", dialect, "--output", str(output), str(model)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    schema = json.loads(output.read_text(encoding="utf-8"))
    if dialect == "avro-schema":
        entry = next(field["type"]["values"] for field in avro_group(schema)["fields"]
                     if field["name"] == "entries")
        value = next(field for field in entry["fields"] if field["name"] == "value")
    else:
        value = schema["definitions"]["Samples"]["Entry"]["properties"]["value"]
    assert value["default"] == "0.100000000000000000000000000001"


def test_epoch_description_and_unsigned_kind_are_correct_in_every_projection():
    model = scalar_model("integer")
    avro = GENERATOR.generate_avro_schema(copy.deepcopy(model))
    epoch = next(field for field in avro_group(avro)["fields"] if field["name"] == "epoch")
    assert epoch["doc"] == "Optimistic concurrency update counter"
    assert epoch["x-xregistryScalar"]["coreType"] == "uinteger"
    structure = GENERATOR.generate_json_structure(copy.deepcopy(model))
    epoch = structure["definitions"]["Samples"]["Sample"]["properties"]["epoch"]
    assert epoch["description"] == "Optimistic concurrency update counter"
    assert epoch["x-xregistryScalar"]["coreType"] == "uinteger"
    for openapi in (False, True):
        schema = GENERATOR.generate_json_schema(copy.deepcopy(model), openapi)
        group = (
            schema["components"]["schemas"]["sample"] if openapi
            else schema["definitions"]["sample-schema"]["sample"]
        )
        assert group["properties"]["epoch"] == {
            "type": "integer", "minimum": 0,
            "description": "Optimistic concurrency update counter",
        }


@pytest.mark.parametrize("dialect", ["avro", "json-structure"])
@pytest.mark.parametrize("mutation", [
    "empty-contract", "encoding", "enum-kind", "physical-type", "default-kind"
])
def test_codec_rejects_inconsistent_scalar_bindings(dialect, mutation):
    codec = generated_codec({"type": "integer", "required": True}, dialect)
    schema = codec.schema
    field = (
        next(field for field in avro_group(schema)["fields"] if field["name"] == "value")
        if dialect == "avro"
        else schema["definitions"]["Samples"]["Sample"]["properties"]["value"]
    )
    if mutation == "empty-contract":
        field["x-xregistryScalar"] = {}
    elif mutation == "encoding":
        field["x-xregistryScalar"]["encoding"] = "float64"
    elif mutation == "enum-kind":
        field["x-xregistryScalar"]["constraints"]["enum"] = ["1.5"]
    elif mutation == "physical-type":
        field["type"] = "double" if dialect == "avro" else "float64"
    else:
        field["default"] = 7
    with pytest.raises(ProjectionError):
        ProjectionCodec(schema, dialect)


@pytest.mark.parametrize("count", [0, 2])
def test_avro_reader_rejects_missing_or_extra_datums(count):
    codec = generated_codec({"type": "integer", "required": True}, "avro")
    physical = codec.to_derived(document(JsonNumber("7")))
    encoded = write_physical_avro(codec, physical, records=[physical] * count)
    with pytest.raises(ProjectionError, match="exactly one"):
        codec.read(encoded)


@pytest.mark.parametrize("mutation", ["profile", "schema"])
def test_json_structure_reader_rejects_changed_writer_contract(mutation):
    codec = generated_codec({"type": "integer", "required": True}, "json-structure")
    envelope = parse_core_json(codec.write(document(JsonNumber("7"))))
    if mutation == "profile":
        envelope["contract"]["profile"]["version"] = "2"
    else:
        field = envelope["contract"]["schema"]["definitions"]["Samples"][
            "Sample"
        ]["properties"]["value"]
        field["x-xregistryScalar"]["constraints"]["minimum"] = "2"
    with pytest.raises(ProfileMismatchError):
        codec.read(dump_core_json(envelope).encode())
