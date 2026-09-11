"""Executable Core HTTP mapping, pagination, cache and capture examples."""

import copy
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from federation_examples import FederationError, execute_selected, select_label
from http_examples import interpret_transcript, literal_filter, request_url


FIXTURES = Path(__file__).resolve().parent.parent / "workingdrafts" / "federation" / "samples" / "http"
MAPPING = json.loads((FIXTURES / "read-mapping.json").read_text(encoding="utf-8"))
DATA = json.loads((FIXTURES / "transcripts.json").read_text(encoding="utf-8"))
TRANSCRIPTS = {value["name"]: value for value in DATA["transcripts"]}


@pytest.mark.parametrize("case", MAPPING["cases"], ids=lambda case: case["name"])
def test_http_native_read_mappings_preserve_nonroot_base_and_view(case):
    if "error" in case:
        with pytest.raises(FederationError) as error:
            request_url(MAPPING["endpoint"], MAPPING["modelsource"], **case["request"])
        assert error.value.code == "unsupported_operation"
    else:
        url = request_url(MAPPING["endpoint"], MAPPING["modelsource"], **case["request"])
        assert url == case["url"]
        assert url.startswith("https://first.example.com/services/xreg/")


@pytest.mark.parametrize("case", DATA["selectors"], ids=lambda case: case["name"])
def test_http_literal_filters_and_local_comparison(case):
    assert literal_filter(case["selector"]) == case["filter"]
    if "error" in case:
        with pytest.raises(FederationError) as error:
            select_label(case["entities"], case["selector"]["label"], case["selector"]["value"])
        assert error.value.code == "not_found"
    else:
        result = select_label(case["entities"], case["selector"]["label"], case["selector"]["value"])
        assert result["assetid"] == "item"


@pytest.mark.parametrize("name,code", [
    ("later-page-ambiguity", "ambiguous"),
    ("redirect-policy-denial", "policy_denied"),
    ("changed-default", "inconsistent_snapshot"),
    ("incompatible-target", "unsupported_version"),
    ("incomplete-page", "inconsistent_snapshot"),
    ("authorization-stops-resolution", "policy_denied"),
])
def test_http_failed_transcripts_keep_specific_error_and_real_trace(name, code):
    case = copy.deepcopy(TRANSCRIPTS[name])
    case["expected"] = {"invented": "success"}
    trace = []
    with pytest.raises(FederationError) as error:
        interpret_transcript(case, trace=trace)
    assert error.value.code == code
    assert trace == [
        {"url": item["request"]["url"], "status": item["response"]["status"]}
        for item in case["exchanges"]
    ]


def test_http_no_filter_catalog_resolves_metadata_without_document_download():
    case = TRANSCRIPTS["no-filter-catalog"]
    result = interpret_transcript(case)
    assert result["value"]["registryid"] == "bridge"
    assert result["value"]["xregurl"] == "https://first.example.com/services/xreg/"
    assert result["pages"] == 1
    assert result["snapshot"] is None and result["immutable"] is False
    assert [item["url"] for item in result["trace"]] == [
        "https://catalog.example.com/catalog/capabilities",
        "https://catalog.example.com/catalog/categories/dev/registries",
    ]


def test_http_bootstrap_keeps_identity_and_live_snapshot_separate():
    result = interpret_transcript(TRANSCRIPTS["full-api-bootstrap"])
    assert result["registry"]["registryid"] == "first"
    assert result["registry"]["specversion"] == "1.0-rc4"
    assert result["snapshot"] is None
    assert result["immutable"] is False
    assert len(result["trace"]) == 3


def test_http_opaque_next_page_is_consumed_before_unique_selection():
    result = interpret_transcript(TRANSCRIPTS["filtered-pages"])
    assert result["pages"] == 2
    assert result["value"]["assetid"] == "item"
    assert result["value"]["xid"] == "/documents/main/assets/item"
    assert result["trace"][1]["url"] == TRANSCRIPTS["filtered-pages"]["exchanges"][1]["request"]["url"]


@pytest.mark.parametrize("name,data,reused", [
    ("document-revalidation", b'{"type":"string"}', True),
    ("zero-byte-document", b"", False),
    ("document-redirect", b"\x00\xff", False),
    ("range-restart", b"WXYZ", False),
])
def test_http_exact_document_bytes_cache_and_range_restart(name, data, reused):
    case = copy.deepcopy(TRANSCRIPTS[name])
    case["expected"] = {"base64": "ZmFrZQ=="}
    before = copy.deepcopy(case)
    result = interpret_transcript(case)
    assert result["value"] == data
    assert result["cache_reused"] is reused
    assert case == before
    assert result["discarded_partial"] == (b"AB" if name == "range-restart" else b"")
    if name == "document-redirect":
        assert result["source_xid"] == "/documents/main/assets/item/versions/v2"
        assert result["trace"][-1]["url"] == "https://content.example.com/item-v2.bin"


@pytest.mark.parametrize("header", ["Authorization", "Cookie", "If-None-Match", "If-Range"])
def test_http_cross_origin_redirect_rejects_forwarded_scope_headers(header):
    case = copy.deepcopy(TRANSCRIPTS["document-redirect"])
    case["exchanges"][1]["request"]["headers"][header] = "source-only"
    trace = []
    with pytest.raises(FederationError) as error:
        interpret_transcript(case, trace=trace)
    assert error.value.code == "policy_denied"
    assert len(trace) == 1


@pytest.mark.parametrize("change,code", [
    ("next-url", "inconsistent_snapshot"), ("count", "inconsistent_snapshot"),
    ("missing-page", "inconsistent_snapshot"), ("member-xid", "invalid_package"),
])
def test_http_incomplete_or_changed_collection_cannot_look_unique(change, code):
    case = copy.deepcopy(TRANSCRIPTS["filtered-pages"])
    if change == "next-url":
        case["exchanges"][1]["request"]["url"] += "&invented=1"
    elif change == "missing-page":
        case["exchanges"].pop()
    elif change == "count":
        case["exchanges"][1]["response"]["headers"]["Link"] = "<.?end>;rel=prev;count=99"
    else:
        for exchange in case["exchanges"]:
            for entity in exchange["response"].get("json", {}).values():
                entity["xid"] = "/documents/other/assets/item"
    with pytest.raises(FederationError) as error:
        interpret_transcript(case)
    assert error.value.code == code


@pytest.mark.parametrize("budget,ok", [(16, False), (17, True), (18, True)])
def test_http_exact_byte_budget_boundary(budget, ok):
    case = copy.deepcopy(TRANSCRIPTS["document-revalidation"])
    case["exchanges"] = case["exchanges"][:1]
    if ok:
        assert interpret_transcript(case, max_bytes=budget)["value"] == b'{"type":"string"}'
    else:
        with pytest.raises(FederationError) as error:
            interpret_transcript(case, max_bytes=budget)
        assert error.value.code == "limit_exceeded"


def test_http_request_budget_never_returns_first_page_as_unique():
    with pytest.raises(FederationError) as error:
        interpret_transcript(TRANSCRIPTS["filtered-pages"], max_requests=1)
    assert error.value.code == "limit_exceeded"


@pytest.mark.parametrize("change", ["no-cache", "wrong-tag", "wrong-scope", "vary-star", "body"])
def test_http_304_needs_matching_cached_representation(change):
    case = copy.deepcopy(TRANSCRIPTS["document-revalidation"])
    if change == "no-cache":
        case["exchanges"].pop(0)
    elif change == "wrong-tag":
        case["exchanges"][1]["request"]["headers"]["If-None-Match"] = '"different"'
    elif change == "wrong-scope":
        case["exchanges"][1]["request"]["headers"]["Authorization"] = "different-scope"
    elif change == "vary-star":
        case["exchanges"][0]["response"]["headers"]["Vary"] = "*"
    else:
        case["exchanges"][1]["response"]["text"] = "replacement"
    with pytest.raises(FederationError) as error:
        interpret_transcript(case)
    assert error.value.code == ("invalid_package" if change == "body" else "inconsistent_snapshot")


def test_http_weak_etag_revalidation_and_quoted_comma_are_opaque():
    case = copy.deepcopy(TRANSCRIPTS["document-revalidation"])
    for exchange in case["exchanges"]:
        exchange["response"]["headers"]["ETag"] = 'W/"tag,one"'
    case["exchanges"][1]["request"]["headers"]["If-None-Match"] = '"another", "tag,one"'
    result = interpret_transcript(case)
    assert result["value"] == b'{"type":"string"}'
    assert result["cache_reused"] is True


@pytest.mark.parametrize("change,code", [
    ("truncate", "integrity_error"), ("weak-if-range", "invalid_package"),
    ("missing-range", "inconsistent_snapshot"), ("range-gap", "inconsistent_snapshot"),
])
def test_http_partial_or_corrupt_content_is_not_a_complete_document(change, code):
    case = copy.deepcopy(TRANSCRIPTS["range-restart"])
    if change == "truncate":
        case["exchanges"][1]["response"]["headers"]["Content-Length"] = "9"
    elif change == "weak-if-range":
        case["exchanges"][1]["request"]["headers"]["If-Range"] = 'W/"old-bytes"'
    elif change == "missing-range":
        case["exchanges"].pop()
    else:
        case["exchanges"][0]["response"]["headers"]["Content-Range"] = "bytes 1-2/4"
    with pytest.raises(FederationError) as error:
        interpret_transcript(case)
    assert error.value.code == code


@pytest.mark.parametrize("code", [
    "policy_denied", "integrity_error", "unsupported_version", "ambiguous", "inconsistent_snapshot",
])
def test_selected_binding_failure_never_attempts_another_advertisement(code):
    first = {"name": "http", "endpoint": "https://first.example.com", "priority": 0}
    second = {"name": "http", "endpoint": "https://second.example.com", "priority": 1}
    failure = FederationError(code, "selected operation failed")
    read = Mock(side_effect=failure)
    with pytest.raises(FederationError) as error:
        execute_selected({"federationprofiles": [first, second]}, {"http"}, read)
    assert error.value is failure
    read.assert_called_once_with(first)
