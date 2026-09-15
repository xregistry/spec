from email import policy
from email.parser import BytesParser
from pathlib import Path
import re
from urllib.parse import urlsplit

import pytest

from native_headers_608 import (
    decode_metadata,
    disposition,
    encode_metadata,
    serialize_header,
)


HTTP_SPEC = Path(__file__).resolve().parents[2] / "core" / "http.md"


def parse_headers(wire):
    message = BytesParser(policy=policy.HTTP).parsebytes(
        wire + b"\r\n", headersonly=True
    )
    assert message.defects == []
    return message


def test_spec_concrete_dispositions_are_filename_parameters():
    values = re.findall(
        r"^Content-Disposition: (?!.*<)(.+)$",
        HTTP_SPEC.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    assert values
    filenames = []
    for value in values:
        message = parse_headers(f"Content-Disposition: {value}\r\n".encode("ascii"))
        assert message.get_content_disposition() == "attachment"
        assert message.get_filename() is not None, value
        filenames.append(message.get_filename())
    assert filenames == ["msg1", "msg1", "myschema", "msg1", "doc.txt"]


def test_spec_disposition_templates_and_repeated_rules_share_filename_contract():
    text = HTTP_SPEC.read_text(encoding="utf-8")
    templates = re.findall(r"^Content-Disposition: (.*<.*)$", text, re.MULTILINE)
    assert templates == ['attachment; filename="<RID>" ?'] * 7
    assert "MUST be the `<RESOURCE>id`\n  value." not in text
    assert text.count(
        "`<RESOURCE>id` in its `filename` parameter as specified in\n"
        "  [HTTP Header Values](#http-header-values)."
    ) == 6


def test_spec_native_and_private_example_bytes():
    text = HTTP_SPEC.read_text(encoding="utf-8")
    example = (
        'Content-Type: multipart/mixed; boundary="a b"\n'
        "Location: https://example.com/docs/doc.txt?name=a%20b\n"
        "Content-Location: https://example.com/docs/doc.txt/versions/1?name=a%20b\n"
        'Content-Disposition: attachment; filename="doc.txt"\n'
        "xRegistry-description: a%20%22quote%22%20and%20100%25\n"
    )
    assert example in text
    message = parse_headers(example.replace("\n", "\r\n").encode("ascii"))
    assert message.get_boundary() == "a b"
    assert message.get_filename() == "doc.txt"
    assert urlsplit(message["Location"]).query == "name=a%20b"
    assert urlsplit(message["Content-Location"]).query == "name=a%20b"
    assert decode_metadata(message["xRegistry-description"]) == 'a "quote" and 100%'


def test_native_multipart_boundary_parses_without_private_decoder():
    header = serialize_header("Content-Type", 'multipart/mixed; boundary="a b"')
    assert header == b'Content-Type: multipart/mixed; boundary="a b"\r\n'
    body = b"--a b\r\nContent-Type: text/plain\r\n\r\ndocument bytes\r\n--a b--\r\n"
    message = BytesParser(policy=policy.HTTP).parsebytes(header + b"\r\n" + body)
    assert message.defects == []
    assert message.get_boundary() == "a b"
    assert message.is_multipart()
    assert [part.get_payload(decode=True) for part in message.iter_parts()] == [
        b"document bytes"
    ]
    broken = parse_headers(
        b"Content-Type: "
        + encode_metadata('multipart/mixed; boundary="a b"').encode("ascii")
        + b"\r\n"
    )
    assert broken.get_boundary() != "a b"


def test_native_media_parameters_preserve_quotes_spaces_and_literal_percent():
    value = r'application/example; title="a \"quote\"; 100%"'
    wire = serialize_header("Content-Type", value)
    assert wire == b'Content-Type: application/example; title="a \\"quote\\"; 100%"\r\n'
    message = parse_headers(wire)
    assert message["Content-Type"].defects == ()
    assert message.get_param("title") == 'a "quote"; 100%'


@pytest.mark.parametrize("name", ["Location", "Content-Location"])
def test_native_uri_percent_escapes_are_not_private_encoded_or_decoded(name):
    uri = "https://example.com/docs/a%2520b?next=a%2Fb&name=a%20b"
    wire = serialize_header(name, uri)
    assert wire == name.encode("ascii") + b": " + uri.encode("ascii") + b"\r\n"
    parsed = urlsplit(parse_headers(wire)[name])
    assert parsed.path == "/docs/a%2520b"
    assert parsed.query == "next=a%2Fb&name=a%20b"


@pytest.mark.parametrize("resource_id", ["doc.txt", "a.b:c@d", "_", "x" * 128])
def test_disposition_roundtrip_keeps_core_id(resource_id):
    value = disposition(resource_id)
    wire = serialize_header("Content-Disposition", value)
    assert wire == f'Content-Disposition: attachment; filename="{resource_id}"\r\n'.encode()
    message = parse_headers(wire)
    assert message.get_content_disposition() == "attachment"
    assert message.get_filename() == resource_id
    identity = serialize_header("xRegistry-schemaid", resource_id)
    assert decode_metadata(parse_headers(identity)["xRegistry-schemaid"]) == resource_id
    assert value != resource_id


@pytest.mark.parametrize(
    "resource_id",
    ["", "x" * 129, ".hidden", "../doc", r"a\b", 'a"b', "a%b", "a b", "a\r\nb", "\u20ac"],
)
def test_disposition_rejects_non_core_ids(resource_id):
    with pytest.raises(ValueError, match="Invalid Core Resource ID"):
        disposition(resource_id)


@pytest.mark.parametrize("name", ["Content-Type", "Location", "Content-Location", "Content-Disposition"])
@pytest.mark.parametrize("control", [chr(byte) for byte in range(32) if byte != 9] + ["\x7f"])
def test_native_control_bytes_are_not_sanitized_or_private_encoded(name, control):
    with pytest.raises(ValueError, match="control byte"):
        serialize_header(name, "valid" + control + "injected")


def test_native_horizontal_tab_is_preserved_as_http_whitespace():
    wire = serialize_header("Content-Type", "text/plain;\tcharset=utf-8")
    assert wire == b"Content-Type: text/plain;\tcharset=utf-8\r\n"
    assert parse_headers(wire).get_content_charset() == "utf-8"


@pytest.mark.parametrize("name", ["bad:name", "bad name", "xRegistry-bad\r\nInjected", "xRegistry-\u20ac", ""])
def test_unsafe_field_names_are_rejected(name):
    with pytest.raises(ValueError, match="field name"):
        serialize_header(name, "safe")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ('a "quote" and 100%', "a%20%22quote%22%20and%20100%25"),
        ("Euro \u20ac \U0001f600", "Euro%20%E2%82%AC%20%F0%9F%98%80"),
        ("%20", "%2520"),
        ("a\r\nb\x00", "a%0D%0Ab%00"),
        ("", ""),
    ],
)
def test_private_metadata_exact_bytes_and_roundtrip(value, expected):
    assert encode_metadata(value) == expected
    assert serialize_header("XREGISTRY-description", value) == (
        b"XREGISTRY-description: " + expected.encode("ascii") + b"\r\n"
    )
    assert decode_metadata(expected) == value


def test_private_unquoting_precedes_exactly_one_decoding_pass():
    assert decode_metadata(r' "a\"b%2520" ') == 'a"b%20'
    assert decode_metadata("%41%e2%82%ac") == "A\u20ac"


@pytest.mark.parametrize("value", ["%C0%A0", "%ED%A0%80", "%F4%90%80%80", "%E2%82", "%FF"])
def test_private_invalid_utf8_is_rejected(value):
    with pytest.raises(UnicodeDecodeError):
        decode_metadata(value)


@pytest.mark.parametrize("value", ["%", "%2", "%GG", '"unfinished', '"closed" trailing', "a\r\nb", "a\x00b"])
def test_private_malformed_wire_value_is_rejected(value):
    with pytest.raises(ValueError):
        decode_metadata(value)
