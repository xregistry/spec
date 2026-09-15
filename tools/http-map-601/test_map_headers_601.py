from http.client import parse_headers
from io import BytesIO
from itertools import product
import json
from pathlib import Path
import re

import pytest

from map_headers_601 import (
    core_names,
    decode_field_name,
    decode_map_fields,
    encode_field_name,
)


HTTP_SPEC = Path(__file__).resolve().parents[2] / "core" / "http.md"
TOKEN = re.compile(rb"[!#$%&'*+\-.^_`|~0-9A-Za-z]+")
EXAMPLES = [
    ('"owner"', "xRegistry-labels.owner"),
    ('"a:b"', "xRegistry-labels.a%3Ab"),
    ('"a.b"', "xRegistry-labels.a.b"),
    ('"A"', "xRegistry-custommap.%41"),
    ('"a%3a"', "xRegistry-custommap.a%253a"),
    ('"a%3A"', "xRegistry-custommap.a%253%41"),
    ('"caf\\u00e9"', "xRegistry-custommap.caf%C3%A9"),
    ('"face\\ud83d\\ude00"', "xRegistry-custommap.face%F0%9F%98%80"),
]


def test_spec_codec_table_roundtrips_exact_utf8_case_and_percent():
    text = HTTP_SPEC.read_text(encoding="utf-8")
    rows = re.findall(
        r'^\| `("(?:\\.|[^"\\])*")` \| `(xRegistry-[^`]+)` \|$',
        text,
        re.MULTILINE,
    )
    assert rows == EXAMPLES
    for json_key, field in rows:
        key = json.loads(json_key)
        attribute = "labels" if field.startswith("xRegistry-labels.") else "custommap"
        assert encode_field_name(attribute, key).encode("ascii") == field.encode("ascii")
        assert decode_field_name(field.lower()) == (attribute, key)
        assert decode_field_name(field.upper()) == (attribute, key)


def test_spec_map_fields_parse_as_intended_names_and_values():
    text = HTTP_SPEC.read_text(encoding="utf-8")
    block = "xRegistry-labels.a%3Ab: value\nxRegistry-labels.a.b: other\n"
    assert "```http\n" + block + "```" in text
    parsed = parse_headers(BytesIO(block.replace("\n", "\r\n").encode("ascii") + b"\r\n"))
    assert list(parsed.raw_items()) == [
        ("xRegistry-labels.a%3Ab", "value"), ("xRegistry-labels.a.b", "other")
    ]
    assert decode_map_fields(parsed.raw_items()) == {
        "labels": {"a:b": "value", "a.b": "other"}
    }
    templates = re.findall(r"^xRegistry-labels\.<[^>]+>: <STRING> \*$", text, re.MULTILINE)
    assert templates == ["xRegistry-labels.<ENCODED_KEY>: <STRING> *"] * 10


def test_raw_colon_suffix_reproduces_the_original_http_parser_failure():
    parsed = parse_headers(BytesIO(b"xRegistry-labels.a:b: value\r\n\r\n"))
    assert list(parsed.raw_items()) == [("xRegistry-labels.a", "b: value")]
    assert list(parsed.raw_items()) != [("xRegistry-labels.a:b", "value")]


@pytest.mark.parametrize("key", ["a", "a.b-c_d", "0", "a" * 63])
def test_unambiguous_lowercase_core_names_keep_their_spelling(key):
    assert core_names("labels", key)
    assert encode_field_name("labels", key) == "xRegistry-labels." + key
    assert decode_map_fields([(encode_field_name("labels", key), "value")]) == {
        "labels": {key: "value"}
    }


@pytest.mark.parametrize(
    ("attribute", "key", "expected"),
    [
        ("labels", "a:b", "xRegistry-labels.a%3Ab"),
        ("labels", "a.b", "xRegistry-labels.a.b"),
        ("custommap", "A:a", "xRegistry-custommap.%41%3Aa"),
        ("custommap", "a@b", "xRegistry-custommap.a%40b"),
        ("custommap", "a%3A", "xRegistry-custommap.a%253%41"),
        ("custom.map", "a.b", "xRegistry-custom%2Emap.a.b"),
        ("Map", "Key", "xRegistry-%4Dap.%4Bey"),
        ("custom%map", "caf\u00e9", "xRegistry-custom%25map.caf%C3%A9"),
        ("custommap", "a\U0010ffff", "xRegistry-custommap.a%F4%8F%BF%BF"),
    ],
)
def test_exact_field_name_vectors_are_safe_and_case_independent(attribute, key, expected):
    wire = encode_field_name(attribute, key).encode("ascii")
    assert wire == expected.encode("ascii")
    assert TOKEN.fullmatch(wire)
    assert decode_field_name(expected.lower()) == (attribute, key)
    assert decode_field_name(expected.upper()) == (attribute, key)


def test_safe_extension_punctuation_including_plus_is_not_url_form_data():
    key = "a!#$&'*+-.^_`|~0z"
    field = encode_field_name("custommap", key)
    assert field == "xRegistry-custommap." + key
    assert TOKEN.fullmatch(field.encode("ascii"))
    assert decode_field_name(field.upper()) == ("custommap", key)


def test_dot_in_attribute_name_cannot_alias_the_map_separator():
    scalar = encode_field_name("labels.a")
    entry = encode_field_name("labels", "a")
    extended_map = encode_field_name("labels.a", "b.c")
    assert scalar == "xRegistry-labels%2Ea"
    assert entry == "xRegistry-labels.a"
    assert extended_map == "xRegistry-labels%2Ea.b.c"
    assert len({scalar.lower(), entry.lower(), extended_map.lower()}) == 3
    assert decode_field_name(scalar.lower()) == ("labels.a", None)
    assert decode_field_name(entry.upper()) == ("labels", "a")
    assert decode_field_name(extended_map.lower()) == ("labels.a", "b.c")


def test_uppercase_logical_keys_require_escapes_not_case_sensitive_http_names():
    assert decode_field_name("XREGISTRY-LABELS.A") == ("labels", "a")
    assert decode_field_name("xregistry-labels.%41") == ("labels", "A")
    admitted_names = {("custommap", "a"), ("custommap", "A")}
    fields = [(encode_field_name(name, key).lower(), key) for name, key in admitted_names]
    assert decode_map_fields(fields, admitted=lambda name, key: (name, key) in admitted_names) == {
        "custommap": {"a": "a", "A": "A"}
    }


def test_percent_decoding_occurs_once_without_legacy_guessing():
    assert decode_field_name("xRegistry-custommap.a%253a") == ("custommap", "a%3a")
    assert decode_field_name("xRegistry-custommap.a%253%41") == ("custommap", "a%3A")
    assert decode_field_name("xRegistry-custommap.a%3Ab") == ("custommap", "a:b")
    assert encode_field_name("custommap", "a%3Ab") == "xRegistry-custommap.a%253%41b"


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("xRegistry-labels.a", "XREGISTRY-LABELS.A"),
        ("xRegistry-labels.a", "xRegistry-labels.%61"),
        ("xRegistry-labels.a%3ab", "xRegistry-labels.a%3Ab"),
        ("xRegistry-%6Cabels.a", "xRegistry-labels.a"),
        ("xRegistry-labels.a.b", "xRegistry-labels.a%2Eb"),
    ],
)
@pytest.mark.parametrize("values", [("first", "second"), ("same", "same")])
def test_duplicate_decoded_keys_are_rejected_before_dictionary_assignment(first, second, values):
    wire = f"{first}: {values[0]}\r\n{second}: {values[1]}\r\n\r\n".encode("ascii")
    parsed = parse_headers(BytesIO(wire))
    assert len(list(parsed.raw_items())) == 2
    with pytest.raises(ValueError, match="Duplicate decoded"):
        decode_map_fields(parsed.raw_items())


def test_distinct_maps_do_not_conflict_and_values_are_not_split_or_decoded():
    fields = [("xRegistry-labels.a", "one,two"), ("xRegistry-other.a", "%20")]
    assert decode_map_fields(fields) == {
        "labels": {"a": "one,two"}, "other": {"a": "%20"}
    }


def test_absent_map_fields_do_not_invent_an_empty_map_and_scalar_fields_are_rejected():
    assert decode_map_fields([]) == {}
    with pytest.raises(ValueError, match="map-entry"):
        decode_map_fields([("xRegistry-name", "value")])


@pytest.mark.parametrize(
    "field",
    [
        "xRegistry-labels.a%", "xRegistry-labels.a%2", "xRegistry-labels.a%XZ",
        "xRegistry-labels.%C0%AE", "xRegistry-labels.%ED%A0%80",
        "xRegistry-labels.%F4%90%80%80", "xRegistry-labels.%E2%82", "xRegistry-labels.%FF",
        "xRegistry-labels.", "xRegistry-.a", "xRegistry-", "xRegistry-labels.a:b",
        "xRegistry-labels.a b", "xRegistry-labels.a\r\nInjected", "xRegistry-labels.a\x00",
        "xRegistry-labels.a\x7f", "xRegistry-labels.\u00e9", "Other-labels.a",
        "xRegistry-%GG.a", "xRegistry-%C0%AF.a",
    ],
)
def test_malformed_encoded_names_never_fall_back_to_literal_keys(field):
    with pytest.raises(ValueError):
        decode_field_name(field)


@pytest.mark.parametrize(("attribute", "key"), [("", "a"), ("labels", ""), ("\ud800", "a"), ("labels", "\udfff")])
def test_empty_names_and_invalid_unicode_cannot_be_encoded(attribute, key):
    with pytest.raises(ValueError):
        encode_field_name(attribute, key)


def test_decoded_core_admission_is_not_replaced_by_encoded_name_length():
    key = "a" + ":" * 62
    field = encode_field_name("labels", key)
    assert len(key) == 63
    assert field == "xRegistry-labels.a" + "%3A" * 62
    assert decode_map_fields([(field, "value")]) == {"labels": {key: "value"}}
    for invalid in ["a" * 64, "_first", "A", "caf\u00e9", "a%20", "a\x00"]:
        with pytest.raises(ValueError, match="not admitted"):
            decode_map_fields([(encode_field_name("labels", invalid), "value")])
    for attribute in ["x" * 64, "1bad", "custom.map"]:
        with pytest.raises(ValueError, match="not admitted"):
            decode_map_fields([(encode_field_name(attribute, "a"), "value")])


def test_extended_characters_need_explicit_model_admission_and_are_not_normalized():
    names = {("custommap", "caf\u00e9"), ("custommap", "cafe\u0301"), ("custom.map", "A%:\U0001f600")}
    fields = [(encode_field_name(name, key).lower(), key) for name, key in names]
    with pytest.raises(ValueError, match="not admitted"):
        decode_map_fields(fields)
    assert decode_map_fields(fields, admitted=lambda name, key: (name, key) in names) == {
        "custommap": {"caf\u00e9": "caf\u00e9", "cafe\u0301": "cafe\u0301"},
        "custom.map": {"A%:\U0001f600": "A%:\U0001f600"},
    }


def test_field_name_codec_has_no_collisions_after_http_case_normalization():
    seen = {}
    alphabet = "aA%:.@\u00e9\U0001f600"
    for size in (1, 2, 3):
        for chars in product(alphabet, repeat=size):
            key = "".join(chars)
            wire = encode_field_name("map", key).lower()
            assert TOKEN.fullmatch(wire.encode("ascii"))
            assert wire not in seen, (seen.get(wire), key)
            seen[wire] = key
            assert decode_field_name(wire) == ("map", key)
            assert decode_field_name(wire.upper()) == ("map", key)
