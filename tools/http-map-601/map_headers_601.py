"""Reference field-name codec and duplicate detection for issue601."""

from collections.abc import Callable, Iterable
import re
from urllib.parse import unquote_to_bytes


PREFIX = "xRegistry-"
_TOKEN = re.compile(r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+")
_SAFE_KEY = frozenset("abcdefghijklmnopqrstuvwxyz0123456789!#$&'*+-.^_`|~")
_SAFE_ATTRIBUTE = _SAFE_KEY - {"."}


def _encode_component(value: str, *, key: bool) -> str:
    if not value:
        raise ValueError("Empty metadata name component")
    safe = _SAFE_KEY if key else _SAFE_ATTRIBUTE
    return "".join(
        chr(byte) if chr(byte) in safe else f"%{byte:02X}"
        for byte in value.encode("utf-8", errors="strict")
    )


def encode_field_name(attribute: str, key: str | None = None) -> str:
    name = PREFIX + _encode_component(attribute, key=False)
    if key is not None:
        name += "." + _encode_component(key, key=True)
    return name


def _decode_component(value: str) -> str:
    if not value:
        raise ValueError("Empty metadata name component")
    if re.search(r"%(?![0-9A-Fa-f]{2})", value):
        raise ValueError("Malformed field-name percent escape")
    return unquote_to_bytes(value.lower()).decode("utf-8", errors="strict")


def decode_field_name(name: str) -> tuple[str, str | None]:
    if not _TOKEN.fullmatch(name) or not name.lower().startswith(PREFIX.lower()):
        raise ValueError("Invalid xRegistry HTTP field name")
    attribute, separator, key = name[len(PREFIX):].partition(".")
    return _decode_component(attribute), _decode_component(key) if separator else None


def core_names(attribute: str, key: str) -> bool:
    return (
        re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", attribute) is not None
        and re.fullmatch(r"[a-z0-9][a-z0-9:_.-]{0,62}", key) is not None
    )


def decode_map_fields(
    fields: Iterable[tuple[str, str]],
    *,
    admitted: Callable[[str, str], bool] = core_names,
) -> dict[str, dict[str, str]]:
    maps: dict[str, dict[str, str]] = {}
    for name, value in fields:
        attribute, key = decode_field_name(name)
        if key is None:
            raise ValueError("Expected a map-entry field")
        if not admitted(attribute, key):
            raise ValueError("Metadata name not admitted by the model")
        entries = maps.setdefault(attribute, {})
        if key in entries:
            raise ValueError("Duplicate decoded metadata map key")
        entries[key] = value
    return maps
