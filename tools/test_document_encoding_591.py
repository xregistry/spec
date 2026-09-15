"""Focused source contracts and a UTF-8 encoding illustration for issue 591."""

import base64
import json
from pathlib import Path
import re

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = (ROOT / "core" / "spec.md").read_text(encoding="utf-8")
MODEL = (ROOT / "core" / "model.md").read_text(encoding="utf-8")
RESOURCE = SPEC.split("#### `<RESOURCE>` Attribute\n", 1)[1].split(
    "\n#### Version IDs", 1
)[0]
TYPEMAP = MODEL.split(
    "### `groups.<STRING>.resources.<STRING>.typemap`\n", 1
)[1].split("\n### ", 1)[0]
DEFAULTS = dict(re.findall(r"- `([^`]+)`: mapped to `([^`]+)`", TYPEMAP))


class _NonJsonConstant(ValueError):
    pass


def _reject_constant(value):
    raise _NonJsonConstant(value)


def _json_text(document):
    try:
        text = document.decode("utf-8")
        json.loads(text, parse_int=str, parse_float=str,
                   parse_constant=_reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, _NonJsonConstant):
        return None
    return text


def _matching_values(content_type, mapping):
    media_type = (content_type or "").split(";", 1)[0].strip()
    return {
        value.lower()
        for pattern, value in mapping.items()
        if re.fullmatch(re.escape(pattern).replace(r"\*", ".*"),
                        media_type, flags=re.I)
    }


def _selection(content_type, typemap):
    matches = _matching_values(content_type, typemap)
    if not matches:
        matches = _matching_values(content_type, DEFAULTS)
    if len(matches) > 1:
        return "binary"
    return next(iter(matches)) if matches else None


def _base64_form(document):
    return json.dumps(
        {"filebase64": base64.b64encode(document).decode("ascii")},
        separators=(",", ":"),
    )


def _encode(document, content_type, typemap=None, *, binary=False,
            prefer_base64=False):
    if not document or binary:
        return _base64_form(document)
    selection = _selection(content_type, typemap or {})
    if selection == "binary":
        return _base64_form(document)
    if selection == "string":
        try:
            text = document.decode("utf-8")
        except UnicodeDecodeError:
            return _base64_form(document)
        return json.dumps({"file": text}, ensure_ascii=True,
                          separators=(",", ":"))
    if selection not in (None, "json"):
        raise ValueError(f"unsupported typemap value: {selection}")
    if selection is None and prefer_base64:
        return _base64_form(document)
    text = _json_text(document)
    if text is None:
        return _base64_form(document)
    return '{"file":' + text + "}"


def _assert_exact_base64(wire, document):
    metadata = json.loads(wire)
    assert set(metadata) == {"filebase64"}
    assert base64.b64decode(metadata["filebase64"], validate=True) == document


@pytest.mark.parametrize(
    "path",
    [
        ("dirs", "forms", "files", "1040"),
        ("dirs", "forms", "files", "1090", "versions", "v1"),
        ("dirs", "forms", "files", "1090", "versions", "v2"),
    ],
    ids=["resource", "version-v1", "version-v2"],
)
def test_existing_document_store_strings_use_the_implicit_mapping(path):
    example = json.loads(
        (ROOT / "core" / "samples" / "doc-store-data.json").read_text(
            encoding="utf-8"
        )
    )
    for key in path:
        example = example[key]
    document = example["file"].encode("utf-8")
    assert _json_text(document) is None
    assert json.loads(_encode(document, example["contenttype"])) == {
        "file": example["file"]
    }


def test_text_plain_is_a_string_even_when_raw_bytes_are_not_json():
    assert _json_text(b"Hello") is None
    assert _encode(b"Hello", "text/plain") == '{"file":"Hello"}'


def test_string_mapping_escapes_quotes_controls_backslashes_and_unicode():
    document = 'say "Hi" \\ \n\t\r\b\f\x00 caf\u00e9'.encode("utf-8")
    wire = _encode(document, "text/plain; charset=utf-8")
    assert wire == r'{"file":"say \"Hi\" \\ \n\t\r\b\f\u0000 caf\u00e9"}'
    assert json.loads(wire)["file"].encode("utf-8") == document


def test_string_mapping_takes_precedence_over_json_shaped_bytes():
    document = b'{"answer":42}'
    metadata = json.loads(_encode(document, "text/plain"))
    assert metadata == {"file": '{"answer":42}'}
    assert isinstance(metadata["file"], str)


@pytest.mark.parametrize(
    "document,expected",
    [
        (b'{"answer":42}', {"answer": 42}),
        (b"[1,2]", [1, 2]),
        (b'"hello"', "hello"),
        (b"false", False),
        (b"0", 0),
    ],
    ids=["object", "array", "string", "false", "zero"],
)
def test_json_mapping_embeds_valid_json_values(document, expected):
    assert json.loads(_encode(document, "application/json")) == {"file": expected}


@pytest.mark.parametrize(
    "document",
    [b"Hello", b'{"x":', b"[] trailing", b"NaN", b"Infinity", b"-Infinity",
     b'"\xff"'],
    ids=["text", "unfinished", "trailing-data", "nan", "infinity",
         "negative-infinity", "invalid-utf8"],
)
def test_invalid_json_falls_back_to_exact_base64(document):
    _assert_exact_base64(_encode(document, "application/json"), document)


def test_valid_json_number_spelling_is_not_limited_by_host_numeric_types():
    document = b'{"big":1e10000,"precise":1.000000000000000000001}'
    assert _encode(document, "application/json") == (
        '{"file":{"big":1e10000,"precise":1.000000000000000000001}}'
    )


@pytest.mark.parametrize(
    "content_type,typemap",
    [
        ("application/json", {}),
        ("text/plain", {}),
        ("application/custom", {"application/custom": "json"}),
        ("application/custom", {"application/custom": "string"}),
        ("application/custom", {"application/custom": "binary"}),
        ("application/octet-stream", {}),
    ],
    ids=["implicit-json", "implicit-string", "explicit-json", "explicit-string",
         "explicit-binary", "unmapped"],
)
def test_binary_flag_overrides_every_encoding_selection(content_type, typemap):
    document = b' { "answer": 42 }\n'
    _assert_exact_base64(
        _encode(document, content_type, typemap, binary=True), document
    )


def test_explicit_binary_mapping_overrides_implicit_json_and_preserves_bytes():
    document = b' { "answer": 42 }\n'
    _assert_exact_base64(
        _encode(document, "application/json", {"application/*": "BINARY"}),
        document,
    )


def test_explicit_string_mapping_overrides_implicit_json():
    assert json.loads(_encode(b'{"x":1}', "application/json",
                             {"application/*": "string"})) == {
        "file": '{"x":1}'
    }


def test_unmatched_explicit_entries_leave_implicit_defaults_in_effect():
    assert _encode(b"Hello", "text/plain", {"image/*": "binary"}) == (
        '{"file":"Hello"}'
    )
    assert json.loads(_encode(b'{"x":1}', "application/problem+json")) == {
        "file": {"x": 1}
    }


@pytest.mark.parametrize("reverse", [False, True])
def test_conflicting_typemap_matches_force_binary_regardless_of_order(reverse):
    entries = [("text/*", "string"), ("text/custom", "json")]
    if reverse:
        entries.reverse()
    document = b'{"x":1}'
    _assert_exact_base64(
        _encode(document, "text/custom", dict(entries)), document
    )


def test_agreeing_matches_ignore_case_and_content_type_parameters():
    assert _encode(
        b"Hello", "TeXt/PlAiN; charset=utf-8",
        {"TEXT/*": "STRING", "text/plain": "string"}
    ) == '{"file":"Hello"}'


@pytest.mark.parametrize(
    "content_type,typemap,expected",
    [
        ("application/json", {}, {"file": {"x": 1}}),
        ("text/plain", {}, {"file": '{"x":1}'}),
        ("text/custom", {"text/*": "json"}, {"file": {"x": 1}}),
        ("application/custom", {"application/*": "string"}, {"file": '{"x":1}'}),
    ],
    ids=["implicit-json", "implicit-string", "explicit-json", "explicit-string"],
)
def test_server_preference_cannot_override_json_or_string_mapping(
    content_type, typemap, expected
):
    assert json.loads(_encode(b'{"x":1}', content_type, typemap,
                             prefer_base64=True)) == expected


@pytest.mark.parametrize("prefer_base64", [False, True])
def test_unmapped_valid_json_allows_either_supported_form(prefer_base64):
    document = b'{"x":1}'
    wire = _encode(document, "application/custom", prefer_base64=prefer_base64)
    if prefer_base64:
        _assert_exact_base64(wire, document)
    else:
        assert json.loads(wire) == {"file": {"x": 1}}


@pytest.mark.parametrize("document", [b"Hello", b"\xff\x00", "caf\u00e9".encode()])
def test_unmapped_non_json_bytes_are_not_reinterpreted_as_text(document):
    _assert_exact_base64(_encode(document, "application/octet-stream"), document)


def test_unrepresentable_string_bytes_use_lossless_base64_not_replacement():
    document = b"Hello\xff"
    _assert_exact_base64(_encode(document, "text/plain; charset=utf-8"), document)


@pytest.mark.parametrize("mapping", ["json", "string", "binary", None])
@pytest.mark.parametrize("binary", [False, True])
def test_empty_documents_use_empty_base64_regardless_of_mapping_or_flag(
    mapping, binary
):
    typemap = {"application/custom": mapping} if mapping is not None else {}
    assert _encode(b"", "application/custom", typemap, binary=binary) == (
        '{"filebase64":""}'
    )


def test_unsupported_mapping_is_not_silently_treated_as_binary():
    with pytest.raises(ValueError, match="unsupported typemap value"):
        _encode(b"Hello", "application/custom", {"application/custom": "unknown"})


def test_core_source_allows_string_encoding_instead_of_raw_json_only():
    text = " ".join(RESOURCE.split())
    assert "A `string` mapping MUST use this attribute" in text
    assert "even when the original document bytes are not a JSON value" in text
    assert (
        "MUST only be used if the Version's document (bytes) is in the same"
        not in text
    )


def test_core_source_limits_base64_preference_and_preserves_fallback():
    text = " ".join(RESOURCE.split())
    assert "If no explicit or implicit `typemap` mapping applies" in text
    assert "MAY prefer `<RESOURCE>base64`" in text
    assert (
        "MUST NOT be converted to a string merely to fit the metadata format"
        in text
    )
    assert "invalid JSON MUST use `<RESOURCE>base64`" in text
    assert "Client and server implementations MUST be prepared" in text


def test_model_source_states_flag_mapping_and_empty_document_precedence():
    text = " ".join(TYPEMAP.split())
    assert "MUST take precedence over every `typemap` selection" in text
    assert (
        "preference for base64 MUST NOT override a `json` or `string` mapping"
        in text
    )
    assert "empty-document rule" in text
    assert "MUST NOT replace or discard invalid bytes" in text
    assert DEFAULTS == {
        "application/json": "json", "*+json": "json", "text/plain": "string"
    }
    assert "not all the same, then `binary` MUST be used" in text
