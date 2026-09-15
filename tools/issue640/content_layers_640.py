"""Offline admission checks for the two CloudEvents content-type layers."""

from dataclasses import dataclass
from email.message import Message
import re


@dataclass(frozen=True)
class ContentLayers:
    payload: str | None
    envelope: str | None
    wire: str | None


def _media_key(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+/[!#$%&'*+\-.^_`|~0-9A-Za-z]+",
        value.partition(";")[0].strip(),
    ) or "\r" in value or "\n" in value:
        raise ValueError("invalid media type")
    header = Message()
    header["Content-Type"] = value
    parameters = {}
    for name, parameter in header.get_params()[1:]:
        name = name.lower()
        if name in parameters:
            raise ValueError("duplicate media type parameter")
        parameters[name] = parameter.lower() if name == "charset" else parameter
    return header.get_content_type(), parameters


def _same_layer(*values):
    specified = [value for value in values if value is not None]
    keys = [_media_key(value) for value in specified]
    if any(key != keys[0] for key in keys[1:]):
        raise ValueError("conflicting content types for the same layer")
    return specified[0] if specified else None


def content_layers(message, *, event_media=None, wire_media=None):
    options = message.get("envelopeoptions", {})
    mode = options.get("mode")
    if mode not in ("binary", "structured"):
        raise ValueError("this example checker needs an explicit content mode")
    metadata = message.get("envelopemetadata", {}).get("datacontenttype", {})
    for owner, key in ((message, "datacontenttype"), (metadata, "value")):
        if key in owner:
            _media_key(owner[key])
    payload = _same_layer(
        message.get("datacontenttype"), metadata.get("value"), event_media
    )
    if mode == "binary":
        if "format" in options:
            raise ValueError("binary mode cannot specify an envelope format")
        return ContentLayers(payload, None, _same_layer(payload, wire_media))
    envelope = options.get("format")
    if "format" in options:
        _media_key(envelope)
    return ContentLayers(payload, envelope, _same_layer(envelope, wire_media))
