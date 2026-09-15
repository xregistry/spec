"""Exact comparator and source-policy evidence, not a live query engine."""

import operator
from pathlib import Path

import pytest
from timestamp_ordering_contract import compare_timestamps, timestamp_key


ROOT = Path(__file__).resolve().parents[1]
SPEC = (ROOT / "core" / "spec.md").read_text(encoding="utf-8")
NOTES = (ROOT / "tools" / "README.md").read_text(encoding="utf-8")
FILTER = SPEC.split("### Filter Flag\n", 1)[1].split("\n### ", 1)[0]
SORT = SPEC.split("### Sort Flag\n", 1)[1].split("\n### ", 1)[0]
LEAP_DAYS = ((1990, 12, 31),)


def test_source_uses_exact_instants_without_requiring_uniform_serialization():
    text = " ".join(FILTER.split())
    types = SPEC.split("#### Data Types\n", 1)[1].split("- `uinteger`", 1)[0]
    assert "Timestamp comparisons MUST use the [instant comparison rules](#filter-flag)." in " ".join(types.split())
    assert "timestamps MUST be compared by the instants they represent" in text
    assert "arbitrary permitted fractional-second precision" in text
    assert "MUST NOT round or truncate fractions for comparison" in text
    assert "An absent fraction is zero, and trailing fractional zeroes do not change the instant." in text
    assert "This rule does not impose a uniform number of fractional digits on stored or returned values." in text
    assert 'these follow the same rules as "strings" above' not in text.split(
        "- For timestamp attributes,", 1
    )[1].split("- For URI/URL variants,", 1)[0]
    assert "timestamp_ordering_contract.py" not in SPEC
    assert "(timestamp_ordering_contract.py)" in NOTES


def test_source_preserves_presence_null_existence_and_secondary_sorting_rules():
    text = " ".join(FILTER.split())
    assert "Presence, `null`, and whole-value `*` existence tests retain their existing semantics." in text
    assert "Other string-wildcard patterns are not timestamp operands." in text
    assert "Invalid filter expressions MUST generate an error ([bad_filter](#bad_filter))." in text
    assert (
        "Different timestamp representations of the same instant MUST use "
        "this secondary key, not their serialized spellings."
    ) in " ".join(SORT.split())
    assert "using the same `asc`/`desc` value" in " ".join(SORT.split())


@pytest.mark.parametrize(
    "left,right,expected",
    [
        ("2030-01-01T00:00:00Z", "2030-01-01T00:00:00.1Z", -1),
        ("2030-01-01T00:00:00.0Z", "2030-01-01T00:00:00Z", 0),
        ("2030-01-01T00:00:00.10Z", "2030-01-01T00:00:00.1Z", 0),
        ("2030-01-01T00:00:00.1001Z", "2030-01-01T00:00:00.1Z", 1),
        ("2030-01-01T00:00:00.001Z", "2030-01-01T00:00:00.0009Z", 1),
        ("2030-01-01T00:00:00.99999999999999999999Z", "2030-01-01T00:00:01Z", -1),
        ("1969-12-31T23:59:59.9999999999Z", "1970-01-01T00:00:00Z", -1),
        ("1996-12-19T16:39:57-08:00", "1996-12-20T00:39:57Z", 0),
        ("2030-01-01T00:15:00+00:30", "2029-12-31T23:45:00Z", 0),
        ("2030-01-01T01:30:00.10+01:30", "2030-01-01T00:00:00.1Z", 0),
        ("2000-02-29T23:30:00-00:30", "2000-03-01T00:00:00Z", 0),
        ("2030-01-01T00:00:00-00:00", "2030-01-01T00:00:00Z", 0),
        ("2030-01-01t00:00:00z", "2030-01-01T00:00:00+00:00", 0),
        ("0000-01-01T00:00:00+23:59", "0000-01-01T00:00:00Z", -1),
        ("9999-12-31T23:59:59-23:59", "9999-12-31T23:59:59Z", 1),
        ("0000-02-29T23:59:59Z", "0000-03-01T00:00:00Z", -1),
    ],
)
def test_exact_order_and_equivalence_across_fraction_and_calendar_forms(left, right, expected):
    assert compare_timestamps(left, right) == expected
    assert compare_timestamps(right, left) == -expected
    assert compare_timestamps(left, left) == 0


@pytest.mark.parametrize("digits", [7, 9, 28, 50, 5000])
def test_arbitrary_fractional_precision_is_not_reduced_to_native_ticks_or_decimal_context(digits):
    first = "2030-01-01T00:00:00." + "0" * digits + "1Z"
    second = "2030-01-01T00:00:00." + "0" * digits + "2Z"
    zero = "2030-01-01T00:00:00Z"
    assert compare_timestamps(zero, first) == -1
    assert compare_timestamps(first, second) == -1
    assert compare_timestamps(first, first[:-1] + "000Z") == 0


def test_comparison_is_transitive_across_offsets_and_deep_fractions():
    first = "2029-12-31T23:59:59.999999999999999Z"
    second = "2030-01-01T01:00:00.000000000000001+01:00"
    third = "2030-01-01T00:00:00.000000000000002Z"
    assert compare_timestamps(first, second) == -1
    assert compare_timestamps(second, third) == -1
    assert compare_timestamps(first, third) == -1


@pytest.mark.parametrize(
    "operation,expected",
    [
        (operator.eq, [False, True, False]),
        (operator.ne, [True, False, True]),
        (operator.lt, [True, False, False]),
        (operator.le, [True, True, False]),
        (operator.gt, [False, False, True]),
        (operator.ge, [False, True, True]),
    ],
    ids=["equals", "not-equals-or-angle-not-equals", "less", "less-equal", "greater", "greater-equal"],
)
def test_temporal_filter_relations_use_instants_at_before_and_after_boundary(operation, expected):
    boundary = "2030-01-01T00:00:00.1Z"
    operands = [
        "2030-01-01T00:00:00.09999999999999999999Z",
        "2030-01-01T01:00:00.1000+01:00",
        "2030-01-01T00:00:00.10000000000000000001Z",
    ]
    assert [operation(compare_timestamps(value, boundary), 0) for value in operands] == expected


@pytest.mark.parametrize("descending", [False, True])
def test_equal_instants_use_id_ties_in_both_directions_and_page_slices(descending):
    rows = [
        ("z", "2030-01-01T00:00:00Z"),
        ("B", "2030-01-01T01:00:00.000+01:00"),
        ("later", "2030-01-01T00:00:00.000000001Z"),
        ("earlier", "2029-12-31T23:59:59.999999999Z"),
    ]
    expected = ["earlier", "B", "z", "later"]
    if descending:
        expected.reverse()
    key = lambda item: (timestamp_key(item[1]), item[0].lower())
    ordered = sorted(rows, key=key, reverse=descending)
    assert [item[0] for item in ordered] == expected
    assert sorted(reversed(rows), key=key, reverse=descending) == ordered
    pages = [ordered[index:index + 2] for index in range(0, len(ordered), 2)]
    assert [[item[0] for item in page] for page in pages] == [expected[:2], expected[2:]]


def test_announced_leap_second_is_between_ordinary_seconds_and_normalizes_offsets():
    values = [
        "1990-12-31T23:59:59.999999999999Z",
        "1990-12-31T23:59:60Z",
        "1990-12-31T23:59:60.000000000001Z",
        "1991-01-01T00:00:00Z",
    ]
    keys = [timestamp_key(value, positive_leap_days=LEAP_DAYS) for value in values]
    assert all(left < right for left, right in zip(keys, keys[1:]))
    assert compare_timestamps(
        "1990-12-31T15:59:60.10-08:00", "1990-12-31T23:59:60.1Z",
        positive_leap_days=LEAP_DAYS,
    ) == 0
    assert timestamp_key("1990-12-31T23:59:60Z", positive_leap_days=LEAP_DAYS) != timestamp_key(
        "1991-01-01T00:00:00Z"
    )


@pytest.mark.parametrize(
    "value,leap_days",
    [
        ("1990-12-31T23:59:60Z", ()),
        ("1990-12-30T23:59:60Z", LEAP_DAYS),
        ("1990-12-31T12:00:60Z", LEAP_DAYS),
    ],
)
def test_missing_or_wrong_leap_authority_fails_instead_of_collapsing_to_next_second(value, leap_days):
    with pytest.raises(ValueError, match="leap-second date is not established"):
        timestamp_key(value, positive_leap_days=leap_days)


@pytest.mark.parametrize(
    "value",
    [
        None, 2030, "", "*", "2030-*", "2030-01-01T00:00:00",
        "2030-01-01 00:00:00Z", "2030-01-01T00:00:00.Z",
        "2030-01-01T00:00:00,1Z", "2030-01-01T24:00:00Z",
        "2030-01-01T00:60:00Z", "2030-01-01T00:00:61Z",
        "2030-01-01T00:00:00+24:00", "2030-01-01T00:00:00+00:60",
        "2030-00-01T00:00:00Z", "2030-13-01T00:00:00Z",
        "2030-01-00T00:00:00Z", "2030-04-31T00:00:00Z",
        "1900-02-29T00:00:00Z", "2030-02-29T00:00:00Z",
        "2030-01-01T00:00:00Zjunk",
    ],
)
def test_invalid_temporal_operands_are_not_coerced(value):
    with pytest.raises(ValueError, match="Invalid RFC3339"):
        timestamp_key(value)
