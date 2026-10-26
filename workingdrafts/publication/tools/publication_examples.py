"""Offline contract examples, not a Core server or durable publication store."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas" / "publication.json").read_text(encoding="utf-8"))


class PublicationError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def validate(kind, value):
    schema = {**SCHEMA, "$ref": "#/$defs/" + kind}
    schema.pop("oneOf")
    jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker(),
    ).validate(value)


def checked_bytes(descriptor, objects):
    validate_descriptor = {
        **SCHEMA, "$ref": "#/$defs/descriptor",
    }
    validate_descriptor.pop("oneOf")
    jsonschema.Draft202012Validator(
        validate_descriptor, format_checker=jsonschema.FormatChecker(),
    ).validate(descriptor)
    if descriptor["url"] not in objects:
        raise PublicationError("unavailable", descriptor["url"])
    raw = objects[descriptor["url"]]
    if len(raw) != descriptor["size"] or (
        "sha256:" + hashlib.sha256(raw).hexdigest() != descriptor["digest"]
    ):
        raise PublicationError("integrity_error", descriptor["url"])
    return raw


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise PublicationError("invalid_package", "duplicate JSON key: " + key)
        result[key] = value
    return result


def _json(raw):
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)


def _view_key(xid):
    parts = xid.split("/")
    return tuple(part.casefold() for part in parts[:6]) + (parts[6],)


def check_snapshot(pin, objects, supported_extensions=()):
    """Check integrity and simple containment for the supported example graph."""
    manifest = _json(checked_bytes(pin, objects))
    validate("manifest", manifest)
    extensions = manifest.get("extensions", {})
    for name in manifest.get("requiredExtensions", []):
        if name not in extensions or name not in supported_extensions:
            raise PublicationError("unsupported_operation", name)
    registry = _json(checked_bytes(manifest["registry"], objects))
    expected = set()
    for group_type, group_model in registry["model"]["groups"].items():
        for group_id, group in registry.get(group_type, {}).items():
            for resource_type, resource_model in group_model["resources"].items():
                for resource_id, resource in group.get(resource_type, {}).items():
                    versions = resource["versions"]
                    if resource["meta"]["defaultversionid"] not in versions:
                        raise PublicationError("invalid_package", "missing default Version")
                    if "xref" in resource["meta"]:
                        raise PublicationError("unsupported_operation", "example has no xref reader")
                    if resource_model.get("hasdocument", True):
                        for version in versions:
                            expected.add(_view_key(
                                f"/{group_type}/{group_id}/{resource_type}/{resource_id}"
                                f"/versions/{version}"
                            ))
    seen = set()
    for item in manifest["documents"]:
        key = _view_key(item["viewVersion"])
        if key in seen or key not in expected:
            raise PublicationError("invalid_package", "duplicate or absent view Version")
        seen.add(key)
        checked_bytes(item["content"], objects)
    if manifest["completeness"] == "offline-complete" and seen != expected:
        raise PublicationError("invalid_package", "missing document association")
    for descriptor in extensions.values():
        checked_bytes(descriptor, objects)
    return manifest


def open_context(context, objects, supported_extensions=()):
    validate("open", context)
    manifest = check_snapshot(context["snapshot"], objects, supported_extensions)
    for name in ("scope", "registry", "completeness"):
        if context[name] != manifest[name]:
            raise PublicationError("inconsistent_snapshot", name)
    return manifest


def open_package(directory):
    directory = Path(directory).resolve()
    package = _json((directory / "publication-package.json").read_bytes())
    validate("package", package)
    objects = {}
    for url, relative in package["objects"].items():
        path = (directory / relative).resolve()
        if not path.is_relative_to(directory):
            raise PublicationError("invalid_package", "package path escapes root")
        if not path.is_file():
            raise PublicationError("unavailable", relative)
        objects[url] = path.read_bytes()
    return open_context(package["context"], objects)


class Channels:
    """Illustrate serialized conditional state changes; no durability claim."""

    def __init__(self):
        self.records = {}
        self.retired = set()

    def create(self, identifier, scope, head, objects):
        if identifier in self.records or identifier in self.retired:
            raise PublicationError("conflict", "channel identity already used")
        manifest = check_snapshot(head, objects)
        if manifest["scope"] != scope:
            raise PublicationError("inconsistent_snapshot", "scope")
        self.records[identifier] = {"scope": scope, "head": deepcopy(head), "epoch": 1}

    def move(self, identifier, epoch, head, objects):
        record = self.records[identifier]
        if record["epoch"] != epoch:
            raise PublicationError("mismatched_epoch", identifier)
        manifest = check_snapshot(head, objects)
        if record["scope"] != manifest["scope"]:
            raise PublicationError("inconsistent_snapshot", "scope")
        self.records[identifier] = {
            "scope": record["scope"], "head": deepcopy(head), "epoch": epoch + 1,
        }

    def delete(self, identifier, epoch):
        if self.records[identifier]["epoch"] != epoch:
            raise PublicationError("mismatched_epoch", identifier)
        del self.records[identifier]
        self.retired.add(identifier)
