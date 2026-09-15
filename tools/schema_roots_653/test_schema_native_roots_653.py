import base64
import io
import json
from pathlib import Path
import re
import struct

import avro.errors
import avro.io
import avro.schema
import jsonpointer
import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = (ROOT / "schema" / "spec.md").read_text(encoding="utf-8")
PROSE = " ".join(SPEC.split())
VALIDATORS = (
    jsonschema.Draft7Validator,
    jsonschema.Draft201909Validator,
    jsonschema.Draft202012Validator,
)
DOCUMENTS = (
    ("JsonSchema/draft/2020-12", "application/schema+json", b"true", bool),
    ("JsonSchema/draft/2020-12", "application/schema+json", b"false", bool),
    (
        "JsonSchema/draft/2020-12",
        "application/schema+json",
        b'{"type":"string"}',
        dict,
    ),
    ("Avro/1.12.0", "application/json", b'"string"', str),
    ("Avro/1.12.0", "application/json", b'["null","string"]', list),
    (
        "Avro/1.12.0",
        "application/json",
        b'{"type":"record","name":"Reading","fields":'
        b'[{"name":"value","type":"long"}]}',
        dict,
    ),
)


def test_documented_roots_preserve_json_kind_content_type_and_document_bytes():
    rows = re.findall(
        r"^\| `([^`]+)` \| `([^`]+)` \| `([^`]+)` \|$", SPEC, re.MULTILINE
    )
    assert len(rows) == len(DOCUMENTS)
    for (format_name, media_type, text), expected in zip(rows, DOCUMENTS):
        expected_format, expected_media_type, document, kind = expected
        assert (format_name, media_type, text.encode("utf-8")) == (
            expected_format,
            expected_media_type,
            document,
        )
        value = json.loads(text)
        assert type(value) is kind
        metadata = json.loads(
            '{"format":'
            + json.dumps(format_name)
            + ',"contenttype":'
            + json.dumps(media_type)
            + ',"schema":'
            + text
            + "}"
        )
        assert type(metadata["schema"]) is kind
        assert json.dumps(metadata["schema"], separators=(",", ":")).encode(
            "utf-8"
        ) == document
        encoded = base64.b64encode(document)
        assert base64.b64decode(encoded, validate=True) == document


@pytest.mark.parametrize("validator", VALIDATORS)
@pytest.mark.parametrize("instance", [None, True, 0, "", "text", [], {}])
def test_documented_json_schema_roots_validate_native_instances(validator, instance):
    for _, _, document, _ in DOCUMENTS[:3]:
        schema = json.loads(document)
        validator.check_schema(schema)
        expected = schema if type(schema) is bool else isinstance(instance, str)
        assert validator(schema).is_valid(instance) is expected


@pytest.mark.parametrize("validator", VALIDATORS)
@pytest.mark.parametrize("value", [None, 0, 1.5, "string", [], ["null", "string"]])
def test_json_schema_rejects_non_schema_root_kinds(validator, value):
    with pytest.raises(jsonschema.SchemaError):
        validator.check_schema(value)


@pytest.mark.parametrize("root", [True, False, {}, {"type": "string"}])
def test_json_schema_root_selection_preserves_native_kind(root):
    selected = jsonpointer.resolve_pointer(root, "")
    assert selected is root
    jsonschema.Draft202012Validator.check_schema(selected)


@pytest.mark.parametrize(
    ("pointer", "expected"),
    [("/$defs/yes", True), ("/$defs/no", False), ("/$defs/text", {"type": "string"})],
)
def test_json_schema_pointer_selects_boolean_or_object(pointer, expected):
    document = {
        "$defs": {"yes": True, "no": False, "text": {"type": "string"}},
    }
    selected = jsonpointer.resolve_pointer(document, pointer)
    assert type(selected) is type(expected)
    assert selected == expected
    jsonschema.Draft202012Validator.check_schema(selected)


def test_json_schema_pointer_rejects_missing_or_non_schema_target():
    document = {"type": "string", "$defs": {"no": False}}
    with pytest.raises(jsonpointer.JsonPointerException):
        jsonpointer.resolve_pointer(document, "/$defs/missing")
    with pytest.raises(jsonpointer.JsonPointerException):
        jsonpointer.resolve_pointer(False, "/type")
    with pytest.raises(jsonschema.SchemaError):
        jsonschema.Draft202012Validator.check_schema(
            jsonpointer.resolve_pointer(document, "/type")
        )


@pytest.mark.parametrize(
    ("text", "value", "expected_bytes", "kind"),
    [
        ('"null"', None, b"", "null"),
        ('"boolean"', True, b"\x01", "boolean"),
        ('"int"', 7, b"\x0e", "int"),
        ('"long"', 7, b"\x0e", "long"),
        ('"float"', 1.0, struct.pack("<f", 1.0), "float"),
        ('"double"', 1.0, struct.pack("<d", 1.0), "double"),
        ('"bytes"', b"\x00\xff", b"\x04\x00\xff", "bytes"),
        ('"string"', "\u00e9", b"\x04\xc3\xa9", "string"),
        ('{"type":"string"}', "ok", b"\x04ok", "string"),
        ('["null","string"]', None, b"\x00", "union"),
        ('["null","string"]', "ok", b"\x02\x04ok", "union"),
        (
            '{"type":"record","name":"Reading","fields":'
            '[{"name":"value","type":"long"}]}',
            {"value": 7},
            b"\x0e",
            "record",
        ),
        ('{"type":"enum","name":"State","symbols":["ON","OFF"]}', "OFF", b"\x02", "enum"),
        ('{"type":"fixed","name":"Id","size":2}', b"\x00\xff", b"\x00\xff", "fixed"),
        ('{"type":"array","items":"string"}', ["ok"], b"\x02\x04ok\x00", "array"),
        ('{"type":"map","values":"long"}', {"a": 7}, b"\x02\x02a\x0e\x00", "map"),
        (
            '{"type":"record","name":"Node","fields":'
            '[{"name":"next","type":["null","Node"]}]}',
            {"next": None},
            b"\x00",
            "record",
        ),
    ],
)
def test_avro_native_roots_roundtrip_with_native_codec(text, value, expected_bytes, kind):
    schema = avro.schema.parse(text)
    assert schema.type == kind
    output = io.BytesIO()
    avro.io.DatumWriter(schema).write(value, avro.io.BinaryEncoder(output))
    assert output.getvalue() == expected_bytes
    input_stream = io.BytesIO(output.getvalue())
    decoded = avro.io.DatumReader(schema).read(avro.io.BinaryDecoder(input_stream))
    assert type(decoded) is type(value)
    assert decoded == value
    assert input_stream.read() == b""


def test_avro_union_root_is_not_implicitly_its_first_branch():
    schema = avro.schema.parse(DOCUMENTS[4][2].decode("utf-8"))
    assert isinstance(schema, avro.schema.UnionSchema)
    assert [branch.type for branch in schema.schemas] == ["null", "string"]
    assert avro.io.validate(schema, None)
    assert avro.io.validate(schema, "ok")
    assert not avro.io.validate(schema, 7)
    assert "A union is not an implicit selection of its first branch." in PROSE


@pytest.mark.parametrize(
    "text",
    ["null", "true", "false", "7", '"Unknown"', '["string","string"]', '[["null","string"],"long"]'],
)
def test_avro_rejects_non_schema_roots_undefined_names_and_invalid_unions(text):
    with pytest.raises(avro.errors.SchemaParseException):
        avro.schema.parse(text)


def test_root_profile_keeps_support_optional_and_core_encoding_authoritative():
    assert "do not require a Registry to support every format or version" in PROSE
    assert "a Registry MUST admit the root categories allowed by that format" in PROSE
    assert "Parsing a document alone does not establish support for all of its semantics." in PROSE
    assert "../core/spec.md#resource-attribute" in SPEC
    assert "../core/spec.md#resourcebase64-attribute" in SPEC
    assert "Boolean roots cannot carry `$schema`; their version is supplied by `format`." in PROSE
    assert "entire root schema is used, including a boolean root" in PROSE
    assert "including primitive, array, map and union schemas" in PROSE
    assert "MUST NOT convert a primitive or union root to a record" in PROSE
