from fractions import Fraction
from pathlib import Path
import re

import pytest

from day_time_duration_632 import parse_duration


SPEC = Path(__file__).resolve().parents[2] / "message" / "spec.md"


def test_documented_duration_vectors_use_selected_grammar_and_value_space():
    source = SPEC.read_text(encoding="utf-8")
    rows = re.findall(
        r"^\| `([^`]+)`\s*\| (Valid|Invalid)\s*\| ([^|]+)\|$",
        source,
        re.MULTILINE,
    )
    assert len(rows) >= 16, "the selected duration profile needs concrete vectors"
    for literal, admission, seconds in rows:
        if admission == "Valid":
            assert parse_duration(literal) == Fraction(seconds.strip()), literal
        else:
            with pytest.raises(ValueError, match="invalid XML Schema"):
                parse_duration(literal)
    assert "RFC3339 Duration" not in source
    assert "xmlschema11-2#dayTimeDuration" in source


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("P1D", "PT24H"),
        ("PT1H", "PT60M"),
        ("PT1M", "PT60S"),
        ("PT0S", "-PT0S"),
        ("PT0001.500S", "PT1.5S"),
        ("PT.5S", "PT0.5S"),
        ("PT1.S", "PT1S"),
    ],
)
def test_duration_equivalent_spellings_compare_by_seconds(left, right):
    assert parse_duration(left) == parse_duration(right)


def test_duration_order_retains_arbitrary_fractional_precision():
    tiny = parse_duration("PT0.000000000000000000000000000001S")
    assert tiny == Fraction(1, 10**30)
    assert parse_duration("-PT0.000000000000000000000000000001S") < 0 < tiny
    assert parse_duration("P100000000000000000000D") == 86400 * 10**20
    assert parse_duration("PT1.000000000000000000000000000001S") > 1


def test_duration_applies_xml_whitespace_collapse_only():
    assert parse_duration(" \tPT1.5S\r\n") == Fraction(3, 2)
    for invalid in ("PT 1S", "P1D T1H", "\u00a0PT1S", "PT1S\u00a0"):
        with pytest.raises(ValueError, match="invalid XML Schema"):
            parse_duration(invalid)


@pytest.mark.parametrize(
    "literal",
    [
        "", "P", "PT", "P1DT", "P1Y", "P0Y", "P1M", "P0M", "P1W",
        "+PT1S", "P-1D", "PT-1S", "PT+1S", "PT1M1H", "PT1H1H",
        "P1.5D", "PT1.5H", "PT1.5M", "PT.S", "PT1e3S",
        "pt1s", "PT\u0661S", "PT1S\njunk", "2026-09-15T12:00:00Z",
    ],
)
def test_duration_rejects_calendar_mixed_sign_and_malformed_forms(literal):
    with pytest.raises(ValueError, match="invalid XML Schema"):
        parse_duration(literal)


@pytest.mark.parametrize("value", [None, 1, True, {}, []])
def test_duration_does_not_coerce_other_json_kinds(value):
    with pytest.raises(TypeError, match="must be a string"):
        parse_duration(value)


def test_field_range_is_separate_from_duration_lexical_validity():
    assert parse_duration("-PT0.5S") == Fraction(-1, 2)
    with pytest.raises(ValueError, match="field minimum"):
        parse_duration("-PT0.5S", minimum=Fraction(0))
    assert parse_duration("PT0S", minimum=Fraction(0)) == 0
    assert parse_duration("PT0.000000001S", minimum=Fraction(0)) > 0
    assert parse_duration("PT59.999999999S", maximum=Fraction(60)) < 60
    assert parse_duration("PT60S", maximum=Fraction(60)) == 60
    with pytest.raises(ValueError, match="field maximum"):
        parse_duration("PT60.000000001S", maximum=Fraction(60))
    with pytest.raises(ValueError, match="minimum exceeds maximum"):
        parse_duration("PT1S", minimum=Fraction(2), maximum=Fraction(1))
