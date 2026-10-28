"""Offline contract examples, not a Core server or durable publication store."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

import jsonschema

from workingdrafts.federation.tools.federation_examples import (
    FederationError, validate_profile, xid_parts,
)

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


def _access_key(access):
    validate("access", access)
    try:
        validate_profile(access)
    except FederationError as error:
        raise PublicationError(error.code, str(error)) from error
    name = access["name"]
    if name not in ("http", "opcua", "git", "oci", "file"):
        raise PublicationError("unsupported_binding", name)
    parameters = dict(access.get("parameters", {}))
    if name == "git":
        if not re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", parameters["revision"]):
            raise PublicationError("invalid_package", "Publication Git revision must be an object ID")
        parameters["revision"] = parameters["revision"].lower()
        parameters.setdefault("path", "xregistry")
    if name == "oci" or name == "file" and parameters.get("layout") == "oci-layout":
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", parameters["reference"]):
            raise PublicationError("invalid_package", "Publication OCI reference must be a digest")
    return name, access["endpoint"], tuple(sorted(parameters.items()))


def _xid_key(xid):
    try:
        parts = xid_parts(xid)
    except FederationError as error:
        raise PublicationError(error.code, str(error)) from error
    return tuple(part.casefold() for part in parts[:4]) + parts[4:]


def reference_key(reference):
    """Compare selected access and decoded XIDs without rewriting stored bytes."""
    validate("reference", reference)
    return _access_key(reference["registry"]), _xid_key(reference["version"])


class VersionDocuments:
    """In-memory exact-Version documents; no transport or durability claim."""

    def __init__(self):
        self.objects = {}

    def put(self, reference, raw):
        if not isinstance(raw, bytes):
            raise TypeError("Version document must be bytes")
        self.objects[reference_key(reference)] = raw

    def remove(self, reference):
        del self.objects[reference_key(reference)]

    def read(self, reference):
        key = reference_key(reference)
        if key not in self.objects:
            raise PublicationError("unavailable", reference["version"])
        return self.objects[key]


def checked_bytes(descriptor, read_document):
    validate("descriptor", descriptor)
    reference_key(descriptor["reference"])
    raw = read_document(deepcopy(descriptor["reference"]))
    if not isinstance(raw, bytes):
        raise TypeError("Version document reader must return bytes")
    if len(raw) != descriptor["size"] or (
        "sha256:" + hashlib.sha256(raw).hexdigest() != descriptor["digest"]
    ):
        raise PublicationError("integrity_error", descriptor["reference"]["version"])
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
    return _xid_key(xid)


def check_snapshot(pin, read_document, supported_extensions=()):
    """Check integrity and simple containment for the supported example graph."""
    raw = checked_bytes(pin, read_document)
    parts = _xid_key(pin["reference"]["version"])
    if parts[3] != pin["digest"][7:] or parts[-1] != "manifest":
        raise PublicationError("invalid_package", "Manifest Version or Snapshot ID mismatch")
    manifest = _json(raw)
    validate("manifest", manifest)
    extensions = manifest.get("extensions", {})
    for name in manifest.get("requiredExtensions", []):
        if name not in extensions or name not in supported_extensions:
            raise PublicationError("unsupported_operation", name)
    registry = _json(checked_bytes(manifest["registry"], read_document))
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
        checked_bytes(item["content"], read_document)
    if manifest["completeness"] == "offline-complete" and seen != expected:
        raise PublicationError("invalid_package", "missing document association")
    for descriptor in extensions.values():
        checked_bytes(descriptor, read_document)
    return manifest


def open_context(context, read_document, supported_extensions=()):
    validate("open", context)
    if "channel" in context:
        reference = context["channel"]["reference"]
        _access_key(reference["registry"])
        _xid_key(reference["resource"])
    for source in context.get("sources", []):
        _access_key(source["registry"])
        reference_key(source["snapshot"]["reference"])
    manifest = check_snapshot(context["snapshot"], read_document, supported_extensions)
    for name in ("scope", "registry", "completeness"):
        if context[name] != manifest[name]:
            raise PublicationError("inconsistent_snapshot", name)
    return manifest


def open_package(directory, *, max_bytes=16 * 1024 * 1024, max_objects=100000):
    directory = Path(directory).resolve()
    with (directory / "publication-package.json").open("rb") as stream:
        metadata = stream.read(max_bytes + 1)
    if len(metadata) > max_bytes:
        raise PublicationError("limit_exceeded", "Package metadata exceeds byte limit")
    package = _json(metadata)
    validate("package", package)
    if len(package["objects"]) > max_objects:
        raise PublicationError("limit_exceeded", "Package exceeds object limit")
    documents = VersionDocuments()
    remaining = max_bytes
    for entry in package["objects"]:
        reference, relative = entry["reference"], entry["path"]
        if reference_key(reference) in documents.objects:
            raise PublicationError("invalid_package", "Duplicate Version reference")
        path = (directory / relative).resolve()
        if not path.is_relative_to(directory):
            raise PublicationError("invalid_package", "package path escapes root")
        if not path.is_file():
            raise PublicationError("unavailable", relative)
        with path.open("rb") as stream:
            raw = stream.read(remaining + 1)
        remaining -= len(raw)
        if remaining < 0:
            raise PublicationError("limit_exceeded", relative)
        documents.put(reference, raw)
    return open_context(package["context"], documents.read)


class Channels:
    """Illustrate serialized conditional state changes; no durability claim."""

    def __init__(self):
        self.records = {}
        self.retired = set()

    def create(self, identifier, scope, head, read_document):
        if identifier in self.records or identifier in self.retired:
            raise PublicationError("conflict", "channel identity already used")
        manifest = check_snapshot(head, read_document)
        if manifest["scope"] != scope:
            raise PublicationError("inconsistent_snapshot", "scope")
        self.records[identifier] = {"scope": scope, "head": deepcopy(head), "epoch": 1}

    def move(self, identifier, epoch, head, read_document):
        record = self.records[identifier]
        if record["epoch"] != epoch:
            raise PublicationError("mismatched_epoch", identifier)
        manifest = check_snapshot(head, read_document)
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
