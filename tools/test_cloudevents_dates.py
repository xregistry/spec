"""Validate literal calendar pairs only, not the examples' legacy model shapes."""

import re
from datetime import datetime, timedelta
from pathlib import Path

import pytest


SPEC = (Path(__file__).resolve().parents[1] / "cloudevents" / "spec.md").read_text(
    encoding="utf-8"
)
PAIRS = list(re.finditer(
    r'^(?P<indent> *)"createdat": "(?P<created>[^"]+)",\n'
    r'(?P=indent)"modifiedat": "(?P<modified>[^"]+)"',
    SPEC,
    re.MULTILINE,
))


def test_every_modification_literal_is_in_one_of_eleven_actual_pairs():
    assert len(PAIRS) == 11
    assert len(re.findall(r'^\s*"modifiedat":', SPEC, re.MULTILINE)) == 11


@pytest.mark.parametrize(
    "created, modified",
    [
        pytest.param(
            pair["created"],
            pair["modified"],
            id=f"modified-line-{SPEC.count(chr(10), 0, pair.start()) + 2}",
        )
        for pair in PAIRS
    ],
)
def test_actual_creation_modification_pair_preserves_april30_then_may1(
    created, modified
):
    created_time = datetime.strptime(created, "%Y-%m-%dT%H:%M:%SZ")
    modified_time = datetime.strptime(modified, "%Y-%m-%dT%H:%M:%SZ")
    assert created_time == datetime(2024, 4, 30, 12, 0, 0)
    assert modified_time == datetime(2024, 5, 1, 12, 0, 0)
    assert modified_time - created_time == timedelta(days=1)
    assert created == created_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert modified == modified_time.strftime("%Y-%m-%dT%H:%M:%SZ")


def test_impossible_april31_is_not_accepted_by_calendar_parser():
    with pytest.raises(ValueError):
        datetime.strptime("2024-04-31T12:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
