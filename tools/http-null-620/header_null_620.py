"""Reference updates for one optional string metadata attribute (issue620)."""

import json
import re
from urllib.parse import unquote_to_bytes


def encode_response_value(value: str) -> str:
    return "".join(
        chr(byte) if 0x21 <= byte <= 0x7E and byte not in (0x22, 0x25)
        else f"%{byte:02X}"
        for byte in value.encode("utf-8")
    )


def decode_header_update(value: str) -> str | None:
    wire = value.encode("ascii")
    if any(byte < 32 and byte != 9 or byte == 127 for byte in wire):
        raise ValueError("Invalid HTTP field-value control byte")
    value = value.strip(" \t")
    if value.startswith('"'):
        if not re.fullmatch(r'"(?:[\t !#-\[\]-~]|\\[\t !-~])*"', value):
            raise ValueError("Invalid quoted field value")
        value = re.sub(r"\\(.)", r"\1", value[1:-1])
    elif '"' in value:
        raise ValueError("Invalid unquoted field value")
    if re.search(r"%(?![0-9A-Fa-f]{2})", value):
        raise ValueError("Malformed percent escape")
    decoded = unquote_to_bytes(value).decode("utf-8", errors="strict")
    return None if decoded == "null" else decoded


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON metadata key")
        result[key] = value
    return result


def apply_name_update(metadata: dict, update: str | None) -> dict:
    if update is not None and not isinstance(update, str):
        raise ValueError("Expected a string or deletion")
    result = metadata.copy()
    if update is None:
        result.pop("name", None)
    else:
        result["name"] = update
    return result


def apply_json_patch(metadata: dict, body: bytes) -> dict:
    patch = json.loads(body.decode("utf-8"), object_pairs_hook=_unique_object)
    if not isinstance(patch, dict) or set(patch) - {"name"}:
        raise ValueError("Reference patch supports only the name attribute")
    if "name" not in patch:
        return metadata.copy()
    return apply_name_update(metadata, patch["name"])
