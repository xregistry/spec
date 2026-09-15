"""Abstract document-field round trips and source contracts for issue 592."""

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
PROCESSING = SPEC.split("##### `<RESOURCE>*` Attribute Processing\n", 1)[1].split(
    "\n#### ", 1
)[0]
TYPEMAP = MODEL.split(
    "### `groups.<STRING>.resources.<STRING>.typemap`\n", 1
)[1].split("\n### ", 1)[0]
MODES = [
    pytest.param({}, id="ordinary-json"),
    pytest.param({"typemap_value": "json"}, id="json-typemap"),
    pytest.param({"binary": True}, id="binary-flag"),
    pytest.param({"typemap_value": "binary"}, id="binary-typemap"),
]


class _NonJsonConstant(ValueError):
    pass


def _reject_constant(value):
    raise _NonJsonConstant(value)


def _base64_form(document):
    return json.dumps(
        {"filebase64": base64.b64encode(document).decode("ascii")},
        separators=(",", ":"),
    )


def _export_json(document, *, typemap_value=None, binary=False):
    if typemap_value not in (None, "json", "binary"):
        raise ValueError("this example accepts only resolved json or binary mappings")
    if not document or binary or typemap_value == "binary":
        return _base64_form(document)
    try:
        text = document.decode("utf-8")
        value = json.loads(text, parse_int=str, parse_float=str,
                           parse_constant=_reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, _NonJsonConstant):
        return _base64_form(document)
    if value is None:
        return _base64_form(document)
    return '{"file":' + text + "}"


def _import_document(wire, *, previous=b"previous document"):
    metadata = json.loads(wire, parse_constant=_reject_constant)
    fields = [name for name in ("file", "filebase64", "fileurl")
              if name in metadata]
    if len(fields) > 1:
        raise ValueError("one_resource")
    if not fields:
        return previous
    field = fields[0]
    value = metadata[field]
    if value is None:
        return b""
    if field == "filebase64":
        return base64.b64decode(value, validate=True)
    if field == "file":
        return json.dumps(value, separators=(",", ":"), ensure_ascii=True,
                          allow_nan=False).encode("ascii")
    raise NotImplementedError("external document retrieval is not modeled")


def test_json_null_store_export_import_needs_no_binary_flag():
    stored = _import_document('{"filebase64":"bnVsbA=="}')
    assert stored == b"null"
    exported = _export_json(stored)
    reimported = _import_document(exported)
    assert reimported == stored
    assert json.loads(exported) == {"filebase64": "bnVsbA=="}


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(
    "document",
    [b"null", b" null ", b"\r\n\t null \t\r\n"],
    ids=["four-bytes", "spaces", "json-whitespace"],
)
def test_json_null_bytes_round_trip_in_every_output_mode(mode, document):
    wire = _export_json(document, **mode)
    metadata = json.loads(wire)
    assert metadata == {
        "filebase64": base64.b64encode(document).decode("ascii")
    }
    assert _import_document(wire) == document


@pytest.mark.parametrize("mode", MODES)
def test_empty_document_is_distinct_from_json_null_in_every_mode(mode):
    empty = _export_json(b"", **mode)
    null_document = _export_json(b"null", **mode)
    assert json.loads(empty) == {"filebase64": ""}
    assert json.loads(null_document) == {"filebase64": "bnVsbA=="}
    assert _import_document(empty) == b""
    assert _import_document(null_document) == b"null"


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(
    "document",
    [b'"null"', b"false", b"0", b'""', b"[]", b"{}"],
    ids=["string-null", "false", "zero", "empty-string", "empty-array",
         "empty-object"],
)
def test_json_string_null_and_other_falsy_values_are_not_reset(mode, document):
    wire = _export_json(document, **mode)
    metadata = json.loads(wire)
    expected = json.loads(document)
    if mode.get("binary") or mode.get("typemap_value") == "binary":
        assert set(metadata) == {"filebase64"}
        assert base64.b64decode(metadata["filebase64"], validate=True) == document
    else:
        assert set(metadata) == {"file"}
        assert type(metadata["file"]) is type(expected)
        assert metadata["file"] == expected
    imported = _import_document(wire)
    assert imported == document
    assert type(json.loads(imported)) is type(expected)
    assert json.loads(imported) == expected


@pytest.mark.parametrize("typemap_value", [None, "json"])
def test_nested_null_is_not_a_top_level_null_document(typemap_value):
    document = b'{"value":null,"items":[null]}'
    wire = _export_json(document, typemap_value=typemap_value)
    assert json.loads(wire) == {
        "file": {"value": None, "items": [None]}
    }
    assert _import_document(wire) == document


@pytest.mark.parametrize("field", ["file", "filebase64", "fileurl"])
def test_explicit_request_null_still_resets_every_document_field(field):
    wire = json.dumps({field: None, "contenttype": "application/json"})
    assert _import_document(wire, previous=b"null") == b""


@pytest.mark.parametrize("previous", [b"", b"null", b"\x00\xff"])
def test_absent_document_fields_and_unrelated_null_leave_bytes_unchanged(previous):
    assert _import_document('{"description":null}', previous=previous) == previous


def test_base64_input_still_stores_literal_json_null_instead_of_resetting():
    wire = '{"contenttype":"application/json","filebase64":"bnVsbA=="}'
    assert _import_document(wire) == b"null"


def test_multiple_document_fields_are_rejected_before_applying_null_reset():
    with pytest.raises(ValueError, match="one_resource"):
        _import_document('{"file":null,"filebase64":"bnVsbA=="}')


@pytest.mark.parametrize("document", [b"NULL", b"null x", b"NaN", b"\xff"])
def test_invalid_json_still_uses_exact_base64_fallback(document):
    wire = _export_json(document)
    assert json.loads(wire) == {
        "filebase64": base64.b64encode(document).decode("ascii")
    }
    assert _import_document(wire) == document


def test_core_null_document_example_round_trips_the_original_bytes():
    example = re.search(
        r"For example, the four document bytes `null`.*?```json\n(.*?)\n```",
        RESOURCE, flags=re.S,
    )
    assert example is not None, "Core needs a lossless null-document example"
    wire = example.group(1)
    assert json.loads(wire) == {"filebase64": "bnVsbA=="}
    assert _import_document(wire) == b"null"


def test_core_source_requires_lossless_null_output_without_binary_opt_in():
    text = " ".join(RESOURCE.split())
    assert (
        "MUST NOT be used to represent a non-empty document as the JSON value `null`"
        in text
    )
    assert "`<RESOURCE>base64` MUST carry the original document bytes" in text
    assert "even when a `json` mapping selects the representation" in text
    assert "does not require the `binary` flag" in text


def test_model_json_mapping_has_an_explicit_null_exception():
    json_rule = TYPEMAP.split("A value of `json`", 1)[1].split(
        "A value of `string`", 1
    )[0]
    text = " ".join(json_rule.split())
    assert "except when its value is `null`" in text
    assert "MUST use `<RESOURCE>base64` with the original document bytes" in text
    assert "even when the `binary` flag is absent" in text
    assert "syntax error" in text and "MUST treat the document as `binary`" in text


def test_source_request_null_reset_rule_is_preserved():
    text = " ".join(PROCESSING.split())
    assert (
        "An explicit value of `null` for any of the 3 attributes MUST result in "
        "same net effect as defining the entity's domain-specific document to be "
        "an empty document."
    ) in text
    assert "then absence of all 3 attributes MUST leave all 3 unchanged" in text
