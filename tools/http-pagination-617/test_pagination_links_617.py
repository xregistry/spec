from http.client import HTTPResponse
from io import BytesIO
from pathlib import Path
import re

import pytest

from pagination_links_617 import MAX_COUNT, Link, pagination_headers, parse_link_field, read_page


PAGINATION_SPEC = Path(__file__).resolve().parents[2] / "pagination" / "spec.md"
OPAQUE_NEXT = "https://example.com/people?cursor=A%2fb%2Bc%3D,+;part=1&limit=7"


class MemorySocket:
    def __init__(self, wire):
        self.wire = wire

    def makefile(self, *args, **kwargs):
        return BytesIO(self.wire)


def source_response(number):
    text = PAGINATION_SPEC.read_text(encoding="utf-8")
    match = re.search(rf"Example {number}:\n```http\n(.*?)\n```", text, re.DOTALL)
    assert match is not None, f"Missing complete HTTP example {number}"
    head, body = match.group(1).split("\n\n", 1)
    wire = head.replace("\n", "\r\n").encode("ascii") + b"\r\n\r\n" + body.encode("utf-8")
    response = HTTPResponse(MemorySocket(wire))
    response.begin()
    return response


def test_spec_empty_and_optional_count_carriers_have_exact_http_bodies():
    empty = source_response(4)
    assert empty.status == 200
    assert empty.getheader("Content-Length") == "2"
    assert empty.read() == b"[]"
    assert empty.getheader("Link") is None
    assert read_page(empty.getheaders()) == (None, None)
    offered = source_response(5)
    assert offered.status == 200
    assert offered.read() == b"[]"
    assert offered.getheader("Link") == "<https://example.com/people?resultset=empty>;rel=first;count=0"
    assert read_page(offered.getheaders()) == (None, 0)


def test_spec_empty_intermediate_page_still_provides_opaque_next():
    response = source_response(6)
    assert response.status == 200 and response.read() == b"[]"
    assert response.getheader("Link") == f"<{OPAQUE_NEXT}>;rel=next"
    assert read_page(response.getheaders()) == (OPAQUE_NEXT, None)


def test_spec_generic_and_http_rules_make_only_next_mandatory():
    text = PAGINATION_SPEC.read_text(encoding="utf-8")
    link_rules = text.split("#### link\n", 1)[1].split("#### rel\n", 1)[0]
    assert "MUST be present if there are more records for the `rel` type" not in link_rules
    assert "`next` is the only relation REQUIRED when more records remain" in text
    assert "no separate HTTP count header is defined" in text
    assert "An omitted count does not mean zero" in text


@pytest.mark.parametrize(
    ("at_start", "count"),
    [(True, 0), (True, 1), (True, 17), (False, 17), (False, None)],
)
def test_empty_one_page_and_terminal_results_without_links_omit_count(at_start, count):
    assert pagination_headers(
        more_results=False, at_start=at_start, targets={}, count=count
    ) == ()


def test_more_results_require_next_even_when_count_is_unknown():
    with pytest.raises(ValueError, match="Next is required"):
        pagination_headers(more_results=True, at_start=True, targets={}, count=None)
    headers = pagination_headers(
        more_results=True, at_start=True, targets={"next": OPAQUE_NEXT}, count=None
    )
    assert headers == (("Link", f"<{OPAQUE_NEXT}>;rel=next"),)
    assert read_page(headers) == (OPAQUE_NEXT, None)


def test_terminal_next_and_start_prev_are_rejected():
    with pytest.raises(ValueError, match="Next is required"):
        pagination_headers(more_results=False, at_start=False, targets={"next": "/next"})
    with pytest.raises(ValueError, match="Previous is forbidden"):
        pagination_headers(more_results=False, at_start=True, targets={"prev": "/prev"})


@pytest.mark.parametrize("relation", ["prev", "first", "last"])
def test_optional_relations_can_be_offered_independently(relation):
    target = "/people?resultset=one"
    headers = pagination_headers(
        more_results=False, at_start=False, targets={relation: target}, count=7
    )
    assert headers == (("Link", f"<{target}>;rel={relation};count=7"),)
    assert read_page(headers) == (None, 7)


@pytest.mark.parametrize("relation", ["first", "last"])
def test_first_and_last_can_refer_to_an_empty_or_one_page_result(relation):
    headers = pagination_headers(
        more_results=False, at_start=True, targets={relation: "/people"}, count=0
    )
    assert headers == (("Link", f"</people>;rel={relation};count=0"),)
    assert read_page(headers) == (None, 0)


def test_count_must_agree_within_and_across_pages_including_omission_gaps():
    first = (("Link", "</two>;rel=next;count=3"),)
    gap = (("Link", "</three>;rel=next"),)
    terminal = (("Link", "</one>;rel=first;count=\"3\""),)
    assert read_page(first) == ("/two", 3)
    assert read_page(gap, known_count=3) == ("/three", 3)
    assert read_page(terminal, known_count=3) == (None, 3)
    with pytest.raises(ValueError, match="Inconsistent count"):
        read_page((("Link", "</one>;rel=first;count=4"),), known_count=3)
    with pytest.raises(ValueError, match="Inconsistent count"):
        read_page((("Link", "</two>;rel=next;count=3, </one>;rel=prev;count=4"),))


def test_zero_count_and_remaining_records_are_an_error_not_a_termination_hint():
    with pytest.raises(ValueError, match="zero count"):
        pagination_headers(
            more_results=True, at_start=True, targets={"next": "/next"}, count=0
        )
    with pytest.raises(ValueError, match="zero count"):
        read_page((("Link", "</next>;rel=next;count=0"),))
    with pytest.raises(ValueError, match="zero count"):
        read_page((("Link", "</next>;rel=next"),), known_count=0)


def test_opaque_targets_and_native_quoted_parameters_survive_list_parsing():
    field = f'<{OPAQUE_NEXT}>;rel="next";title="a, b; c";count="3", </last>;rel=last;count=3'
    assert parse_link_field(field) == (
        Link(OPAQUE_NEXT, ("next",), 3), Link("/last", ("last",), 3)
    )
    assert read_page((("Link", field),)) == (OPAQUE_NEXT, 3)


@pytest.mark.parametrize("count", [0, MAX_COUNT])
def test_count_zero_and_unsigned_64_bit_maximum_have_exact_carrier_bytes(count):
    headers = pagination_headers(
        more_results=False, at_start=True, targets={"first": "/people"}, count=count
    )
    assert headers == (("Link", f"</people>;rel=first;count={count}"),)
    assert read_page(headers) == (None, count)


@pytest.mark.parametrize("count", [-1, MAX_COUNT + 1, True, 1.5, "0"])
def test_invalid_count_values_are_errors_not_success_shaped_omissions(count):
    with pytest.raises(ValueError, match="unsigned 64-bit"):
        pagination_headers(more_results=False, at_start=True, targets={}, count=count)


@pytest.mark.parametrize("count", ["-1", str(MAX_COUNT + 1), "null", "1.0", "%30", '""'])
def test_invalid_native_count_parameters_are_rejected(count):
    with pytest.raises(ValueError):
        parse_link_field(f"</people>;rel=first;count={count}")


def test_omitted_count_keeps_known_information_without_inventing_zero_or_a_header():
    assert read_page(()) == (None, None)
    assert read_page((), known_count=0) == (None, 0)
    assert read_page((), known_count=9) == (None, 9)
    assert read_page((("Count", "0"), ("X-Total-Count", "0"))) == (None, None)


def test_empty_relative_target_is_not_confused_with_missing_next():
    headers = pagination_headers(more_results=True, at_start=True, targets={"next": ""})
    assert headers == (("Link", "<>;rel=next"),)
    assert read_page(headers) == ("", None)


@pytest.mark.parametrize(
    "value",
    [
        "not-a-link", "</people>", "</people>;rel=next;count",
        "</people>;rel=next;count=1;count=2", '</people>;rel="next',
        "</bad target>;rel=next", "</bad%XZ>;rel=next",
        "</people>;rel=next\r\nInjected: value", "</people>;rel=next\x00",
        "</people>;rel=next\x7f", "</people>;rel=next;anchor=/other",
    ],
)
def test_malformed_or_unsupported_link_inputs_are_explicit_errors(value):
    with pytest.raises(ValueError):
        parse_link_field(value)


def test_duplicate_rel_uses_first_value_per_link_syntax_and_next_targets_are_not_guessed():
    assert parse_link_field("</next>;rel=next;rel=prev;count=0;count=\"0\"") == (
        Link("/next", ("next",), 0),
    )
    with pytest.raises(ValueError, match="Ambiguous next"):
        read_page((("Link", "</a>;rel=next, </b>;rel=next"),))
