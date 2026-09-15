"""Reference examples for the native/private field-value boundary in issue608."""

import re
from urllib.parse import unquote_to_bytes


_TOKEN = re.compile(r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+")
_RESOURCE_ID = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.~:@-]{0,127}")
_NATIVE = {"content-type", "location", "content-location", "content-disposition"}


def _field_value(value: str) -> bytes:
    wire = value.encode("ascii")
    if any(byte < 32 and byte != 9 or byte == 127 for byte in wire):
        raise ValueError("Invalid HTTP field-value control byte")
    return wire


def encode_metadata(value: str) -> str:
    return "".join(
        chr(byte) if 0x21 <= byte <= 0x7E and byte not in (0x22, 0x25)
        else f"%{byte:02X}"
        for byte in value.encode("utf-8")
    )


def decode_metadata(value: str) -> str:
    _field_value(value)
    value = value.strip(" \t")
    if value.startswith('"'):
        if not re.fullmatch(r'"(?:[\t !#-\[\]-~]|\\[\t !-~])*"', value):
            raise ValueError("Invalid quoted field value")
        value = re.sub(r"\\(.)", r"\1", value[1:-1])
    elif '"' in value:
        raise ValueError("Invalid unquoted field value")
    if re.search(r"%(?![0-9A-Fa-f]{2})", value):
        raise ValueError("Malformed percent escape")
    return unquote_to_bytes(value).decode("utf-8", errors="strict")


def disposition(resource_id: str) -> str:
    if not _RESOURCE_ID.fullmatch(resource_id):
        raise ValueError("Invalid Core Resource ID")
    return f'attachment; filename="{resource_id}"'


def serialize_header(name: str, value: str) -> bytes:
    if not _TOKEN.fullmatch(name):
        raise ValueError("Invalid HTTP field name")
    if name.lower().startswith("xregistry-"):
        value = encode_metadata(value)
    elif name.lower() not in _NATIVE:
        raise ValueError("Field is outside this reference example")
    return name.encode("ascii") + b": " + _field_value(value) + b"\r\n"
