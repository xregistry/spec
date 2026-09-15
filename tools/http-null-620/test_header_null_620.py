import json
from pathlib import Path
import re

import pytest

from header_null_620 import (
    apply_json_patch,
    apply_name_update,
    decode_header_update,
    encode_response_value,
)


HTTP_SPEC = Path(__file__).resolve().parents[2] / "core" / "http.md"


def test_spec_json_fallback_examples_preserve_string_and_delete_null():
    text = HTTP_SPEC.read_text(encoding="utf-8")
    bodies = re.findall(r'```json\n(\{"name":(?:"null"|null)\})\n```', text)
    assert bodies == ['{"name":"null"}', '{"name":null}']
    original = {"name": "old", "description": "keep"}
    assert apply_json_patch(original, bodies[0].encode("utf-8")) == {
        "name": "null", "description": "keep"
    }
    assert apply_json_patch(original, bodies[1].encode("utf-8")) == {
        "description": "keep"
    }
    assert "clients MUST use the JSON metadata view" in text


def test_spec_header_table_is_a_parsed_update_contract():
    text = HTTP_SPEC.read_text(encoding="utf-8")
    fields = re.findall(r"^\| `(xRegistry-name:[^`]*)` \|", text, re.MULTILINE)
    assert fields == [
        "xRegistry-name: null",
        'xRegistry-name: "null"',
        "xRegistry-name: %6E%75%6C%6C",
        "xRegistry-name:",
        "xRegistry-name: Null",
        "xRegistry-name: %22null%22",
    ]
    expected = [{}, {}, {}, {"name": ""}, {"name": "Null"}, {"name": '"null"'}]
    for field, result in zip(fields, expected):
        name, separator, value = field.partition(":")
        assert name == "xRegistry-name" and separator == ":"
        assert apply_name_update({"name": "old"}, decode_header_update(value)) == result


@pytest.mark.parametrize(
    "wire",
    ["null", '"null"', "%6e%75%6c%6c", "%6Eull", '"%6E%75%6C%6C"', r'"\n\u\l\l"', " \tnull\t "],
)
def test_bare_quoted_and_percent_encoded_null_all_delete(wire):
    assert decode_header_update(wire) is None
    assert apply_name_update({"name": "old", "description": "keep"}, decode_header_update(wire)) == {
        "description": "keep"
    }


@pytest.mark.parametrize(
    ("wire", "value"),
    [
        ("", ""),
        ('""', ""),
        ("Null", "Null"),
        ("NULL", "NULL"),
        ("%20null%20", " null "),
        ("%22null%22", '"null"'),
        ("%256e%2575%256c%256c", "%6e%75%6c%6c"),
        ("null+", "null+"),
    ],
)
def test_non_sentinel_strings_are_not_deleted_or_redecoded(wire, value):
    assert decode_header_update(wire) == value
    assert apply_name_update({}, decode_header_update(wire)) == {"name": value}


def test_read_to_write_copy_deletes_literal_null_but_json_roundtrip_preserves_it():
    stored = {"name": "null", "description": "unchanged"}
    response_header = encode_response_value(stored["name"])
    assert response_header.encode("ascii") == b"null"
    assert apply_name_update(stored, decode_header_update(response_header)) == {
        "description": "unchanged"
    }
    body = json.dumps({"name": stored["name"]}, separators=(",", ":")).encode("utf-8")
    assert body == b'{"name":"null"}'
    assert apply_json_patch(stored, body) == stored
    assert apply_json_patch(stored, b"{}") == stored
    assert stored == {"name": "null", "description": "unchanged"}


def test_json_null_is_deletion_and_empty_string_is_a_value():
    original = {"name": "null", "description": "keep"}
    assert apply_json_patch(original, b'{"name":null}') == {"description": "keep"}
    assert apply_json_patch(original, b'{"name":""}') == {
        "name": "", "description": "keep"
    }
    assert apply_name_update({}, None) == {}


def test_private_unicode_and_encoded_controls_remain_data():
    value = "Euro \u20ac \U0001f600\r\n\x00"
    wire = encode_response_value(value)
    assert wire == "Euro%20%E2%82%AC%20%F0%9F%98%80%0D%0A%00"
    assert decode_header_update(wire) == value


@pytest.mark.parametrize(
    "wire",
    ["%C0%A0", "%ED%A0%80", "%F4%90%80%80", "%E2%82", "%FF", "%", "%0", "%XZ",
     '"null', '"null" extra', "nu\r\nll", "nu\x00ll", "nu\x7fll"],
)
def test_malformed_headers_are_errors_not_deletions_or_literal_null_escapes(wire):
    with pytest.raises(ValueError):
        decode_header_update(wire)


@pytest.mark.parametrize(
    "body",
    [b"null", b'{"name":true}', b'{"name":0}', b'{"name":[]}', b'{"name":{}}',
     b'{"name":"null","name":null}', b'{"name":null', b'{"other":"null"}', b"\xff"],
)
def test_invalid_json_patch_does_not_silently_become_a_string_or_deletion(body):
    original = {"name": "keep"}
    with pytest.raises(ValueError):
        apply_json_patch(original, body)
    assert original == {"name": "keep"}
