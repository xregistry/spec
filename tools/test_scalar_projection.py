"""Exact scalar semantics, independent of a host numeric/date representation."""

from decimal import Decimal

import pytest

from scalar_projection import (
    JsonNumber,
    Limits,
    ProjectionError,
    ResourceLimitError,
    compare_numbers,
    compare_timestamps,
    decode_scalar,
    dump_core_json,
    encode_scalar,
    normalize_timestamp,
    parse_core_json,
    scalar_schema,
)


INTEGER_TOKENS = [
    "-2147483649", "-2147483648", "-2147483647",
    "2147483646", "2147483647", "2147483648",
    "4294967294", "4294967295", "4294967296",
    "9007199254740991", "9007199254740992", "9007199254740993",
    "18446744073709551614", "18446744073709551615",
    "18446744073709551616", "9" * 256,
    "1.0", "1e0", "10e-1", "-0", "-0.000e1000", "1e1000",
]


def annotation(kind, **constraints):
    return scalar_schema({"type": kind, **constraints}, "avro")[
        "x-xregistryScalar"
    ]


@pytest.mark.parametrize("token", INTEGER_TOKENS)
def test_integer_tokens_round_trip_without_fixed_width_or_float(token):
    source = parse_core_json('{"value":' + token + "}")
    contract = annotation("integer")
    physical = encode_scalar(source["value"], contract)
    assert physical == token
    restored = decode_scalar(physical, contract)
    assert isinstance(restored, JsonNumber)
    assert dump_core_json({"value": restored}) == '{"value":' + token + "}"


@pytest.mark.parametrize(
    "token", [value for value in INTEGER_TOKENS if not value.startswith("-")]
    + ["0", "-0", "-0.0"]
)
def test_unsigned_tokens_keep_all_nonnegative_integral_values(token):
    contract = annotation("uinteger")
    assert encode_scalar(JsonNumber(token), contract) == token
    assert dump_core_json(decode_scalar(token, contract)) == token


@pytest.mark.parametrize(
    "token",
    [
        "0.100000000000000000000000000001",
        "0.100000000000000000000000000002",
        "1e1000", "1e-1000", "-0.0", "12345.678901234567890123456789",
    ],
)
def test_decimal_tokens_and_core_numeric_kinds_are_exact(token):
    contract = annotation("decimal")
    value = parse_core_json(token)
    assert encode_scalar(value, contract) == token
    assert dump_core_json(decode_scalar(token, contract)) == token
    assert isinstance(value, JsonNumber)
    assert not isinstance(value, (str, float, bool))


def test_json_parser_and_writer_preserve_nested_tokens_and_string_kinds():
    source = (
        '{"items":[1e1000,{"amount":0.100000000000000000000000000001}],'
        '"text":"1e1000","flag":true,"empty":null}'
    )
    value = parse_core_json(source)
    assert value["items"][0].token == "1e1000"
    assert value["items"][1]["amount"].token.endswith("001")
    assert value["text"] == "1e1000"
    assert value["flag"] is True
    assert value["empty"] is None
    assert dump_core_json(value) == source


def test_large_coefficient_and_exponent_do_not_use_host_integer_string_caps():
    coefficient = "8" * 10000
    exponent = "9" * 5000
    for token in (coefficient, "1e" + exponent):
        value = parse_core_json(token)
        assert dump_core_json(value) == token
        assert encode_scalar(value, annotation("integer")) == token
    assert compare_numbers(JsonNumber("1e" + exponent), JsonNumber("1e1000")) > 0


@pytest.mark.parametrize(
    "left, right, expected",
    [
        ("1", "1.0", 0), ("1.0", "1e0", 0), ("10e-1", "1", 0),
        ("-0.00", "0", 0), ("9e999", "1e1000", -1),
        ("100e998", "1e1000", 0), ("-1e1000", "-9e999", -1),
        ("1.000000000000000000000000000001", "1", 1),
        ("0.100000000000000000000000000001",
         "0.100000000000000000000000000002", -1),
    ],
)
def test_number_comparison_is_mathematical_without_exponent_expansion(
    left, right, expected
):
    assert compare_numbers(JsonNumber(left), JsonNumber(right)) == expected


def test_numeric_enums_and_bounds_use_values_not_token_spelling():
    schema = scalar_schema(
        {
            "type": "decimal", "enum": [JsonNumber("1"), JsonNumber("1e1000")],
            "minimum": JsonNumber("1"), "maximum": JsonNumber("1e1000"),
            "default": JsonNumber("1.0"), "required": True,
        },
        "avro",
    )
    assert schema["default"] == "1.0"
    assert "enum" not in schema
    contract = schema["x-xregistryScalar"]
    for token in ("1", "1.0", "1e0", "1e1000", "10e999"):
        assert encode_scalar(JsonNumber(token), contract) == token
        assert decode_scalar(token, contract).token == token
    for token in ("0.9", "2", "1e1001"):
        with pytest.raises(ProjectionError):
            encode_scalar(JsonNumber(token), contract)
        with pytest.raises(ProjectionError):
            decode_scalar(token, contract)


def test_non_strict_numeric_enum_does_not_restrict_other_valid_numbers():
    contract = annotation("decimal", enum=[1], strict=False)
    assert encode_scalar(JsonNumber("2.25"), contract) == "2.25"
    assert decode_scalar("2.25", contract).token == "2.25"


@pytest.mark.parametrize("value", [True, False, "1", 1.0, float("inf"),
                                   float("-inf"), float("nan"), None, [], {}])
def test_scalar_writer_rejects_wrong_kinds_and_binary_floats(value):
    with pytest.raises(ProjectionError):
        encode_scalar(value, annotation("integer"))


@pytest.mark.parametrize(
    "token",
    ["", "+1", "01", ".1", "1.", "1e", "1e+", " 1", "1 ", "NaN",
     "Infinity", "-Infinity", "true", "null", "1_000", "\u0661"],
)
def test_numeric_reader_rejects_invalid_json_number_lexemes(token):
    with pytest.raises(ProjectionError):
        decode_scalar(token, annotation("decimal"))


@pytest.mark.parametrize("value", [True, 1, 1.0, None, [], {}])
def test_numeric_reader_requires_a_physical_string(value):
    with pytest.raises(ProjectionError):
        decode_scalar(value, annotation("decimal"))


@pytest.mark.parametrize("kind, token", [
    ("integer", "0.1"), ("integer", "1e-1000"),
    ("uinteger", "-1"), ("uinteger", "-1e1000"), ("uinteger", "1.5"),
])
def test_source_integer_and_unsigned_constraints_are_enforced(kind, token):
    with pytest.raises(ProjectionError):
        encode_scalar(JsonNumber(token), annotation(kind))
    with pytest.raises(ProjectionError):
        decode_scalar(token, annotation(kind))


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity"])
def test_core_json_rejects_nonfinite_numbers(token):
    with pytest.raises(ProjectionError):
        parse_core_json('{"value":' + token + "}")


def test_native_integers_and_decimals_are_exact_but_float_json_is_rejected():
    assert dump_core_json({"n": 2 ** 64, "d": Decimal("1e1000")}) == (
        '{"n":18446744073709551616,"d":1E+1000}'
    )
    with pytest.raises(ProjectionError):
        dump_core_json({"n": 0.1})
    with pytest.raises(ProjectionError):
        dump_core_json({"n": Decimal("NaN")})


def test_budgets_fail_explicitly_without_a_numeric_value_cap():
    value = JsonNumber("1e1000")
    contract = annotation("integer")
    with pytest.raises(ResourceLimitError, match="scalar"):
        encode_scalar(value, contract, limits=Limits(max_scalar_chars=5))
    assert encode_scalar(
        value, contract, limits=Limits(max_scalar_chars=6)
    ) == "1e1000"
    with pytest.raises(ResourceLimitError, match="depth"):
        dump_core_json([[[1]]], limits=Limits(max_depth=1))


FRACTION = "123456789012345678901234567890"
TIMESTAMPS = [
    "2026-01-01T00:00:00Z",
    "2026-01-01T00:00:00.000001Z",
    "2026-01-01T00:00:00.000999Z",
    "2026-01-01T00:00:00." + FRACTION + "Z",
    "2026-01-01T01:00:00." + FRACTION + "+01:00",
    "2025-12-31T19:00:00." + FRACTION + "-05:00",
    "2024-02-29T23:45:00.123456789+05:45",
    "2016-12-31T23:59:60.123456789Z",
    "0000-02-29T00:00:00.000000000000000000000000000001Z",
]


@pytest.mark.parametrize("token", TIMESTAMPS)
def test_timestamp_strings_round_trip_with_all_fraction_digits(token):
    contract = annotation("timestamp")
    assert encode_scalar(token, contract) == token
    assert decode_scalar(token, contract) == token


@pytest.mark.parametrize("offset", [
    "2026-01-01T01:00:00." + FRACTION + "+01:00",
    "2025-12-31T19:00:00." + FRACTION + "-05:00",
    "2026-01-01T05:45:00." + FRACTION + "+05:45",
])
def test_offset_normalization_preserves_exact_fraction_and_instant(offset):
    utc = "2026-01-01T00:00:00." + FRACTION + "Z"
    assert normalize_timestamp(offset) == utc
    assert compare_timestamps(offset, utc) == 0
    assert normalize_timestamp(utc) == utc


def test_timestamp_comparison_distinguishes_thirtieth_fractional_digit():
    earlier = "2026-01-01T00:00:00.123456789012345678901234567890Z"
    later = "2026-01-01T00:00:00.123456789012345678901234567891Z"
    assert compare_timestamps(earlier, later) == -1
    assert compare_timestamps(
        "2026-01-01T00:00:00.1Z", "2026-01-01T00:00:00.1000Z"
    ) == 0
    assert compare_timestamps(
        "2016-12-31T23:59:60.9Z", "2017-01-01T00:00:00Z"
    ) == -1


def test_timestamp_constraints_and_defaults_use_exact_instants():
    utc = "2026-01-01T00:00:00." + FRACTION + "Z"
    offset = "2026-01-01T01:00:00." + FRACTION + "+01:00"
    schema = scalar_schema(
        {"type": "timestamp", "enum": [utc], "default": offset},
        "json-structure",
    )
    assert schema["type"] == "datetime"
    assert schema["default"] == offset
    assert "enum" not in schema
    contract = schema["x-xregistryScalar"]
    assert encode_scalar(offset, contract) == offset
    with pytest.raises(ProjectionError, match="enum"):
        decode_scalar(
            "2026-01-01T00:00:00.123456789012345678901234567891Z", contract
        )


@pytest.mark.parametrize("value", [
    "2026-02-29T00:00:00Z", "2026-01-01T24:00:00Z",
    "2026-01-01T00:00:61Z", "2026-01-01T00:00:60Z",
    "2026-01-01T00:00:00.Z", "2026-01-01T00:00:00+24:00",
    "2026-01-01T00:00:00", "2026-01-01", "NaN",
    "2026-01-01T00:00:00Z trailing", True, 0, None,
])
def test_timestamp_reader_and_writer_reject_invalid_text_and_kinds(value):
    contract = annotation("timestamp")
    with pytest.raises(ProjectionError):
        encode_scalar(value, contract)
    with pytest.raises(ProjectionError):
        decode_scalar(value, contract)


def test_scalar_contract_rejects_invalid_enum_kinds_and_encodings():
    with pytest.raises(ProjectionError):
        scalar_schema({"type": "uinteger", "enum": [-1]}, "avro")
    with pytest.raises(ProjectionError):
        scalar_schema({"type": "integer", "enum": [JsonNumber("0.1")]}, "avro")
    contract = annotation("integer")
    contract["encoding"] = "float"
    with pytest.raises(ProjectionError, match="encoding"):
        encode_scalar(1, contract)


def test_integer_bounds_can_be_exact_fractional_thresholds():
    contract = annotation(
        "integer", minimum=JsonNumber("0.1"), maximum=JsonNumber("2.9")
    )
    assert encode_scalar(1, contract) == "1"
    assert encode_scalar(2, contract) == "2"
    for value in (0, 3):
        with pytest.raises(ProjectionError):
            encode_scalar(value, contract)


def test_core_json_limits_and_duplicate_members_fail_explicitly():
    source = '{"n":1e1000}'
    assert parse_core_json(
        source, limits=Limits(max_bytes=len(source))
    )["n"].token == "1e1000"
    with pytest.raises(ResourceLimitError, match="byte"):
        parse_core_json(source, limits=Limits(max_bytes=len(source) - 1))
    with pytest.raises(ProjectionError, match="Duplicate"):
        parse_core_json('{"n":1,"n":2}')
