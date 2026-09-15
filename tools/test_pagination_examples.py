"""Check the concrete Expires example and its source binding, not a server."""

import re
from datetime import datetime, timezone
from email.utils import format_datetime, parsedate_to_datetime
from pathlib import Path

import pytest


SPEC = (Path(__file__).resolve().parents[1] / "pagination" / "spec.md").read_text(
    encoding="utf-8"
)


def _assert_expiry_example(value):
    parsed = parsedate_to_datetime(value)
    assert parsed == datetime(2021, 12, 1, 16, 0, 0, tzinfo=timezone.utc)
    assert format_datetime(parsed, usegmt=True) == value


def test_expires_binding_names_http_date_and_current_definition():
    binding = SPEC.split("- The response MAY include the `expires`", 1)[1].split(
        "\n- It is STRONGLY", 1
    )[0]
    assert " ".join(binding.split()) == (
        'attribute in any response as an HTTP "Expires" header. If present, '
        "it MUST adhere to the HTTP-date format specified for "
        "[Expires in RFC9111]"
        "(https://www.rfc-editor.org/rfc/rfc9111.html#section-5.3)."
    )


def test_expires_example_has_correct_weekday_and_original_deadline():
    headers = re.findall(r"^Expires: (.+)$", SPEC, re.MULTILINE)
    assert len(headers) == 1
    _assert_expiry_example(headers[0])


@pytest.mark.parametrize(
    "value, error",
    [
        ("Thu, 01 Dec 2021 16:00:00 GMT", AssertionError),
        ("2021-12-01T16:00:00Z", ValueError),
    ],
)
def test_expiry_example_guard_rejects_wrong_weekday_and_rfc3339(value, error):
    with pytest.raises(error):
        _assert_expiry_example(value)


def test_expiry_still_describes_the_complete_result_set():
    expiry = SPEC.split("#### expires\n", 1)[1].split("\n#### count\n", 1)[0]
    assert " ".join(expiry.split()) == (
        "- Type: `Timestamp` "
        "- Description: Indicates when the complete set of records referenced "
        "by the `link` will no longer be available. When not specified, the "
        "availability of the data is undefined by this specification. However, "
        "it is RECOMMENDED that this attribute only be excluded when the data "
        "being iterated over is not expected to change very often and therefore "
        "the server will typically not need to save any state related to this "
        "client's requests. - Constraints: - OPTIONAL."
    )
