"""Calendar-valid timestamp examples, discovered by the independent .NET validator."""

from datetime import datetime
from email.utils import format_datetime, parsedate_to_datetime
from pathlib import Path
import re


def test_cloudevents_created_and_modified_examples_are_calendar_valid():
    text = (Path(__file__).resolve().parents[1] / "cloudevents" / "spec.md").read_text(encoding="utf-8")
    pairs = re.findall(
        r'"createdat":\s*"(\d{4}-[^"]+)",\s*"modifiedat":\s*"(\d{4}-[^"]+)"',
        text,
    )
    assert len(pairs) >= 11
    for created, modified in pairs:
        created_time = datetime.fromisoformat(created.replace("Z", "+00:00"))
        modified_time = datetime.fromisoformat(modified.replace("Z", "+00:00"))
        assert modified_time > created_time


def test_pagination_expiry_references_http_date_instead_of_rfc3339():
    text = (Path(__file__).resolve().parents[1] / "pagination" / "spec.md").read_text(encoding="utf-8")
    assert 'HTTP "Expires" header. If present, it MUST use the `HTTP-date` format' in text
    assert "[RFC7234](https://tools.ietf.org/html/rfc7234#section-5.3)" in text
    assert "[RFC3339](https://tools.ietf.org/html/rfc7234#section-5.3)" not in text


def test_pagination_expiry_examples_are_canonical_http_dates():
    text = (Path(__file__).resolve().parents[1] / "pagination" / "spec.md").read_text(encoding="utf-8")
    values = re.findall(r"^Expires: (.+)$", text, re.MULTILINE)
    assert values
    for value in values:
        assert format_datetime(parsedate_to_datetime(value), usegmt=True) == value
