"""Build and inspect offline OCI fixtures; not a Distribution client or server."""

from __future__ import annotations

import argparse
import base64
import binascii
import copy
import hashlib
import json
import math
import os
import re
import stat
import sys
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Iterator, Mapping, NoReturn
from urllib.parse import urlsplit

from jsonschema import Draft7Validator, Draft202012Validator, FormatChecker

if __package__:
    from .federation_examples import (
        FederationError,
        select_label,
        validate_profile,
        validate_xid,
    )
else:
    from federation_examples import (
        FederationError,
        select_label,
        validate_profile,
        validate_xid,
    )


INDEX_MEDIA_TYPE = "application/vnd.oci.image.index.v1+json"
MANIFEST_MEDIA_TYPE = "application/vnd.oci.image.manifest.v1+json"
CONFIG_MEDIA_TYPE = "application/vnd.xregistry.entity.v1+json"
DOCUMENT_MEDIA_TYPE = "application/vnd.xregistry.document.v1"
EMPTY_MEDIA_TYPE = "application/vnd.oci.empty.v1+json"
MAX_DESCRIPTORS = 256
MAX_INDEX_BYTES = 1_048_576
CORE_VERSION = "1.0-rc4"
PREFIX = "io.xregistry.oci."
ARTIFACT_TYPES = {
    kind: f"application/vnd.xregistry.{kind}.v1+json"
    for kind in (
        "registry", "group", "resource", "collections", "collection",
        "metadata", "version",
    )
}
_ROOT = Path(__file__).resolve().parent.parent
_SCHEMAS = _ROOT / "workingdrafts" / "bindings" / "schemas"
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
_TAG = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}\Z")
_MEDIA_TYPE = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}/"
    r"[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}\Z"
)


def _fail(code: str, message: str) -> NoReturn:
    raise FederationError(code, message)


def _object(value: object, name: str) -> dict:
    if not isinstance(value, dict):
        _fail("invalid_package", f"{name} must be an object")
    return value


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            _fail("invalid_package", f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        _fail("invalid_package", "Non-finite JSON number")
    return number


def _bad_constant(value: str) -> NoReturn:
    _fail("invalid_package", f"Not a JSON number: {value}")


def decode_json(data: bytes) -> object:
    """Strict UTF-8 JSON, rejecting duplicate keys and non-finite numbers."""
    if not isinstance(data, bytes):
        _fail("invalid_package", "JSON input must be bytes")
    try:
        value = json.loads(
            data.decode("utf-8"), object_pairs_hook=_unique_object,
            parse_float=_finite_float, parse_constant=_bad_constant,
        )
        json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
        return value
    except FederationError:
        raise
    except RecursionError as error:
        raise FederationError("limit_exceeded", "JSON nesting budget exhausted") from error
    except (UnicodeError, ValueError) as error:
        raise FederationError("invalid_package", f"Invalid UTF-8 JSON: {error}") from error


def encode_json(value: object) -> bytes:
    """This fixture producer's encoding, not a global canonicalization rule."""
    try:
        return (
            json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2,
                       sort_keys=True) + "\n"
        ).encode("utf-8")
    except RecursionError as error:
        raise FederationError("limit_exceeded", "JSON nesting budget exhausted") from error
    except (TypeError, ValueError, UnicodeError) as error:
        raise FederationError("invalid_package", f"Cannot encode JSON: {error}") from error


def sha256_digest(data: bytes) -> str:
    if not isinstance(data, bytes):
        _fail("invalid_package", "Digest input must be bytes")
    return "sha256:" + hashlib.sha256(data).hexdigest()


@lru_cache(maxsize=3)
def _validator(filename: str) -> Draft202012Validator:
    schema = decode_json((_SCHEMAS / filename).read_bytes())
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _schema(value: object, filename: str) -> None:
    error = next(_validator(filename).iter_errors(value), None)
    if error is not None:
        path = "/".join(str(part) for part in error.absolute_path)
        _fail("invalid_package", f"{filename} at /{path}: {error.message}")


@lru_cache(maxsize=1)
def _core_model_validator() -> Draft7Validator:
    schema = decode_json((_ROOT / "core" / "model.schema.json").read_bytes())
    Draft7Validator.check_schema(schema)
    return Draft7Validator(schema)


def _annotation(item: dict, name: str) -> str:
    value = item.get("annotations", {}).get(PREFIX + name)
    if not isinstance(value, str):
        _fail("invalid_package", f"Missing string annotation: {PREFIX + name}")
    return value


def _annotations(**values: str) -> dict:
    return {PREFIX + key: value for key, value in values.items()}


def _annotation_fields(item: dict, names: set[str]) -> None:
    annotations = _object(item.get("annotations"), "annotations")
    actual = {key[len(PREFIX):] for key in annotations if key.startswith(PREFIX)}
    if actual != names:
        _fail("invalid_package", f"Unexpected routing annotations: {sorted(actual)}")


def _descriptor(value: object, *, internal: bool = True) -> dict:
    item = _object(value, "descriptor")
    if not isinstance(item.get("digest"), str) or not _DIGEST.fullmatch(item["digest"]):
        _fail("invalid_package", "Descriptor needs a lowercase SHA-256 digest")
    if type(item.get("size")) is not int or not 0 <= item["size"] < 2**63:
        _fail("invalid_package", "Descriptor size must be a nonnegative int64")
    if not isinstance(item.get("mediaType"), str) or not _MEDIA_TYPE.fullmatch(
        item["mediaType"]
    ):
        _fail("invalid_package", "Invalid descriptor mediaType")
    if "artifactType" in item and not isinstance(item["artifactType"], str):
        _fail("invalid_package", "Invalid descriptor artifactType")
    annotations = item.get("annotations", {})
    if not isinstance(annotations, dict) or any(
        not isinstance(key, str) or not isinstance(value, str)
        for key, value in annotations.items()
    ):
        _fail("invalid_package", "Annotations must be a string map")
    if internal:
        if item.keys() - {"mediaType", "digest", "size", "artifactType", "annotations"}:
            _fail("invalid_package", "Unsupported internal descriptor fields")
        if "artifactType" in item and item["mediaType"] not in (
            INDEX_MEDIA_TYPE, MANIFEST_MEDIA_TYPE
        ):
            _fail("invalid_package", "A blob descriptor does not have an artifactType")
        role = _annotation(item, "role")
        _annotation(item, "xid")
        fields = {"role", "xid"}
        if role == "shard":
            fields |= {"lower", "upper"}
        _annotation_fields(item, fields)
        if "org.opencontainers.image.ref.name" in annotations:
            _fail("invalid_package", "Tags belong on layout entries, not internal edges")
    return item


def _node_header(node: dict) -> tuple[str, str]:
    annotations = _object(node.get("annotations"), "node annotations")
    if annotations.get(PREFIX + "version") != "1":
        _fail("unsupported_version", "Unsupported OCI profile version")
    kind = _annotation(node, "kind")
    xid = _annotation(node, "xid")
    if node.get("mediaType") == INDEX_MEDIA_TYPE:
        if kind not in ("registry", "group", "resource", "collections", "collection"):
            _fail("unsupported_version", "Unsupported index kind")
        artifact = ARTIFACT_TYPES[kind]
    elif node.get("mediaType") == MANIFEST_MEDIA_TYPE:
        if kind not in ("registry", "group", "resource", "meta", "version"):
            _fail("unsupported_version", "Unsupported manifest kind")
        artifact = ARTIFACT_TYPES["version" if kind == "version" else "metadata"]
    else:
        _fail("unsupported_version", "Unsupported OCI node media type")
    if node.get("artifactType") != artifact:
        _fail("invalid_package", "artifactType disagrees with the node kind")
    fields = {"version", "kind", "xid"}
    if kind in ("collections", "collection"):
        fields |= {"mode", "lower", "upper"}
    _annotation_fields(node, fields)
    return kind, xid


def check_index(data: bytes, *, profile: bool = True) -> dict:
    """Check actual encoded bounds; profile=False checks a layout entry point."""
    if not isinstance(data, bytes):
        _fail("invalid_package", "Index input must be bytes")
    if len(data) > MAX_INDEX_BYTES:
        _fail("limit_exceeded", "Index exceeds 1048576 encoded bytes")
    node = _object(decode_json(data), "index")
    if (
        type(node.get("schemaVersion")) is not int or node["schemaVersion"] != 2
        or node.get("mediaType") != INDEX_MEDIA_TYPE
    ):
        _fail("invalid_package", "Not an OCI image index")
    entries = node.get("manifests")
    if not isinstance(entries, list):
        _fail("invalid_package", "Index manifests must be an array")
    if len(entries) > MAX_DESCRIPTORS:
        _fail("limit_exceeded", "Index exceeds 256 descriptors")
    if profile:
        _node_header(node)
        _schema(node, "oci-graph.schema.json")
        for entry in entries:
            _descriptor(entry)
    else:
        for entry in entries:
            _object(entry, "layout descriptor")
            if not isinstance(entry.get("mediaType"), str) or not _MEDIA_TYPE.fullmatch(
                entry["mediaType"]
            ):
                _fail("invalid_package", "Invalid layout descriptor mediaType")
            if not isinstance(entry.get("digest"), str) or not re.fullmatch(
                r"[a-z0-9]+(?:[+._-][a-z0-9]+)*:[A-Za-z0-9=_-]+", entry["digest"]
            ):
                _fail("invalid_package", "Invalid layout descriptor digest")
            if type(entry.get("size")) is not int or not 0 <= entry["size"] < 2**63:
                _fail("invalid_package", "Invalid layout descriptor size")
            annotations = entry.get("annotations", {})
            if not isinstance(annotations, dict) or any(
                not isinstance(k, str) or not isinstance(v, str)
                for k, v in annotations.items()
            ):
                _fail("invalid_package", "Invalid layout annotations")
    return node


def distribution_url(endpoint: str, reference: str, *, blob: bool = False) -> str:
    """Map a locator to a native URL without making a network request."""
    validate_profile(
        {"name": "oci", "endpoint": endpoint, "parameters": {"reference": reference}}
    )
    if blob and not _DIGEST.fullmatch(reference):
        _fail("invalid_package", "A blob reference must be a digest")
    uri = urlsplit(endpoint)
    route = "blobs" if blob else "manifests"
    return f"https://{uri.netloc}/v2{uri.path}/{route}/{reference}"


def _safe_path(root: Path, relative: Path) -> Path:
    path = root
    for part in relative.parts:
        if part in ("", ".", "..") or Path(part).is_absolute():
            _fail("policy_denied", "Unsafe layout path")
        path = path / part
        try:
            info = path.lstat()
        except FileNotFoundError:
            continue
        except PermissionError as error:
            raise FederationError("policy_denied", f"Cannot inspect: {path}") from error
        except OSError as error:
            raise FederationError("unavailable", f"Cannot inspect {path}: {error}") from error
        if stat.S_ISLNK(info.st_mode) or (
            getattr(info, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        ):
            _fail("policy_denied", f"Link or reparse point in layout: {path}")
    return path


def _layout_root(path: str | Path) -> Path:
    if not isinstance(path, (str, Path)) or "\0" in str(path):
        _fail("invalid_package", "Layout path must be a string or Path without NUL")
    root = Path(path).absolute()
    # Check ancestors before resolving, so a junction cannot silently change scope.
    _safe_path(Path(root.anchor), Path(*root.parts[1:]))
    return root


def _read_file(
    path: Path, *, missing: str = "invalid_package", max_bytes: int | None = None
) -> bytes:
    try:
        with path.open("rb") as stream:
            data = stream.read() if max_bytes is None else stream.read(max_bytes + 1)
        if max_bytes is not None and len(data) > max_bytes:
            _fail("limit_exceeded", f"File exceeds {max_bytes} bytes: {path}")
        return data
    except FileNotFoundError as error:
        raise FederationError(missing, f"Missing file: {path}") from error
    except PermissionError as error:
        raise FederationError("policy_denied", f"Cannot read: {path}") from error
    except OSError as error:
        raise FederationError("unavailable", f"Cannot read {path}: {error}") from error


def _check_external_url(value: object) -> None:
    if not isinstance(value, str) or any(char.isspace() for char in value):
        _fail("invalid_package", "Document URL must be an absolute URI")
    try:
        uri = urlsplit(value)
        uri.port
    except ValueError as error:
        raise FederationError("invalid_package", "Malformed document URL") from error
    if not uri.scheme or not (uri.netloc or uri.path):
        _fail("invalid_package", "Document URL must be absolute")
    if uri.username is not None or uri.password is not None:
        _fail("policy_denied", "Document URL contains credentials")


def _has_directive(value: object, names: set[str]) -> bool:
    if isinstance(value, dict):
        return bool(value.keys() & names) or any(
            _has_directive(child, names) for child in value.values()
        )
    return isinstance(value, list) and any(_has_directive(v, names) for v in value)


class _Model:
    """Only the Core type provenance needed by these fixture operations."""

    def __init__(self, registry: dict):
        self.source = _object(registry["modelresolved"], "modelresolved")
        self.groups = _object(self.source.get("groups", {}), "model groups")
        self.full = _object(registry["entity"]["model"], "full model")
        full_groups = _object(self.full.get("groups", {}), "full model groups")
        for value in (self.source, self.full, registry["entity"]["modelsource"]):
            error = next(_core_model_validator().iter_errors(value), None)
            if error is not None:
                _fail("invalid_package", f"Core model schema: {error.message}")
        if _has_directive(self.source, {"$include", "$includes"}):
            _fail("invalid_package", "modelresolved contains unresolved includes")
        if _has_directive(self.full, {"$include", "$includes", "ximportresources"}):
            _fail("invalid_package", "Full model is not expanded")
        if set(full_groups) != set(self.groups):
            _fail("invalid_package", "Full and resolved model Group types disagree")
        self._resources: dict[str, dict[str, tuple[str, str]]] = {}
        for name, definition in self.groups.items():
            validate_xid("/" + name, collection=True)
            definition = _object(definition, "Group definition")
            self._singular(definition)
            origins = self.resources(name)
            expanded = _object(full_groups[name], "expanded Group")
            if expanded.get("singular") != definition["singular"]:
                _fail("invalid_package", "Full model Group singular disagrees")
            expanded_resources = _object(expanded.get("resources", {}), "expanded Resources")
            if set(expanded_resources) != set(origins):
                _fail("invalid_package", "Full model Resource types disagree")
            singulars = set()
            for resource, (group, original) in origins.items():
                definition = self.groups[group]["resources"][original]
                singular = self._singular(definition)
                if singular in singulars:
                    _fail("invalid_package", "Duplicate Resource singular")
                singulars.add(singular)
                actual = _object(expanded_resources[resource], "expanded Resource")
                if (
                    actual.get("singular") != singular
                    or actual.get("hasdocument", True)
                    != definition.get("hasdocument", True)
                ):
                    _fail("invalid_package", "Full model Resource definition disagrees")

    @staticmethod
    def _singular(definition: dict) -> str:
        singular = definition.get("singular")
        if not isinstance(singular, str):
            _fail("invalid_package", "Missing model singular")
        validate_xid("/" + singular, collection=True)
        return singular

    def _declarations(self, group: str) -> tuple[dict, dict[str, str]]:
        if group not in self.groups:
            _fail("invalid_package", "Unknown Group type")
        definition = _object(self.groups[group], "Group definition")
        local = _object(definition.get("resources", {}), "Resource definitions")
        for name, resource in local.items():
            validate_xid(f"/{group}/id/{name}", collection=True)
            resource = _object(resource, "Resource definition")
            self._singular(resource)
            if "hasdocument" in resource and type(resource["hasdocument"]) is not bool:
                _fail("invalid_package", "hasdocument must be boolean")
        imports = definition.get("ximportresources", [])
        if not isinstance(imports, list):
            _fail("invalid_package", "ximportresources must be an array")
        imported_from = {}
        for imported in imports:
            if not isinstance(imported, str) or not imported.startswith("/"):
                _fail("invalid_package", "Malformed Resource type import")
            parts = imported[1:].split("/")
            if len(parts) != 2 or parts[0] == group:
                _fail("invalid_package", "Malformed or self Resource type import")
            other, resource = parts
            if resource in local or resource in imported_from:
                _fail("invalid_package", "Duplicate imported Resource")
            imported_from[resource] = other
        return local, imported_from

    def _origin(
        self, group: str, resource: str,
        active: frozenset[tuple[str, str]] = frozenset(),
    ) -> tuple[str, str]:
        seen = set(active)
        while True:
            pair = (group, resource)
            if pair in seen:
                _fail("invalid_package", "Circular Resource type import")
            seen.add(pair)
            local, imported_from = self._declarations(group)
            if resource in local:
                return pair
            if resource not in imported_from:
                _fail("invalid_package", "Unknown imported Resource type")
            group = imported_from[resource]

    def resources(self, group: str) -> dict[str, tuple[str, str]]:
        if group in self._resources:
            return self._resources[group]
        local, imported_from = self._declarations(group)
        origins = {name: (group, name) for name in local}
        for resource, other in imported_from.items():
            origins[resource] = self._origin(other, resource, frozenset({(group, resource)}))
        self._resources[group] = origins
        return origins

    def resource_type(self, xid: str) -> tuple[str, str]:
        validate_xid(xid)
        parts = xid[1:].split("/")
        if len(parts) != 4:
            _fail("invalid_package", "Resource type lookup needs a Resource XID")
        origins = self.resources(parts[0])
        if parts[2] not in origins:
            _fail("invalid_package", "Unknown Resource type")
        return origins[parts[2]]

    def resource(self, xid: str) -> dict:
        group, resource = self.resource_type(xid)
        return self.groups[group]["resources"][resource]

    def identifier(self, kind: str, xid: str) -> tuple[str, str]:
        validate_xid(xid)
        parts = xid[1:].split("/")
        if kind == "registry" and xid == "/":
            return "registryid", ""
        if kind == "group" and len(parts) == 2:
            if parts[0] not in self.groups:
                _fail("invalid_package", "Unknown Group type")
            return self.groups[parts[0]]["singular"] + "id", parts[1]
        lengths = {"resource": 4, "meta": 5, "version": 6}
        if kind not in lengths or len(parts) != lengths[kind]:
            _fail("invalid_package", "Record kind does not match XID depth")
        if kind == "meta" and parts[4] != "meta":
            _fail("invalid_package", "Meta XID suffix")
        if kind == "version" and parts[4] != "versions":
            _fail("invalid_package", "Version XID suffix")
        resource = self.resource("/" + "/".join(parts[:4]))
        return resource["singular"] + "id", parts[3]

    def collections(self, kind: str, xid: str, *, alias: bool = False) -> list[str]:
        if kind == "registry":
            return ["/" + name for name in sorted(self.groups)]
        if kind == "group":
            return [xid + "/" + name for name in sorted(self.resources(xid.split("/")[1]))]
        return [] if alias else [xid + "/versions"]


def _record_shape(value: object) -> dict:
    record = _object(value, "entity config")
    if type(record.get("formatversion")) is not int or record["formatversion"] != 1:
        _fail("unsupported_version", "Unsupported entity config version")
    _schema(record, "oci-record.schema.json")
    if record["kind"] == "registry" and record["entity"]["specversion"] != CORE_VERSION:
        _fail("unsupported_version", "Fixture helper supports Core 1.0-rc4")
    return record


def _record_context(record: dict, model: _Model) -> None:
    kind, entity = record["kind"], record["entity"]
    xid = entity["xid"]
    id_key, expected = model.identifier(kind, xid)
    if id_key not in entity or (kind != "registry" and entity[id_key] != expected):
        _fail("invalid_package", f"Singular ID does not match {xid}")
    if kind in ("registry", "group"):
        for path in model.collections(kind, xid):
            name = path.rsplit("/", 1)[1]
            if entity.keys() & {name, name + "url", name + "count"}:
                _fail("invalid_package", "Core collections belong in descriptor edges")
    if kind == "resource" and set(entity) != {"xid", id_key}:
        _fail("invalid_package", "Resource config must not project Version metadata")
    if kind == "meta" and "xref" in entity:
        if set(entity) != {"xid", id_key, "xref"}:
            _fail("invalid_package", "xref Meta contains target attributes")
        if model.resource_type(entity["xref"]) != model.resource_type(xid[:-5]):
            _fail("invalid_package", "xref Resource model types differ")
    if kind == "version":
        if entity["versionid"] != xid.rsplit("/", 1)[1]:
            _fail("invalid_package", "versionid does not match XID")
        resource_xid = xid.rsplit("/versions/", 1)[0]
        definition = model.resource(resource_xid)
        singular = definition["singular"]
        if entity.keys() & {singular, singular + "base64"}:
            _fail("invalid_package", "Domain bytes must not be in metadata")
        mode = record["document"]["mode"]
        has_document = definition.get("hasdocument", True)
        if (mode == "metadata-only") != (not has_document):
            _fail("invalid_package", "Document mode disagrees with hasdocument")
        url_key = singular + "url"
        if url_key in entity:
            _check_external_url(entity[url_key])
        if mode == "external" and url_key not in entity:
            _fail("invalid_package", "External document has no Core document URL")
        if mode != "external" and url_key in entity:
            _fail("invalid_package", "Only external mode has a Core document URL")
        for key in ("origin", "base"):
            if key in record["document"]:
                _check_external_url(record["document"][key])


def _records(
    records: list[dict], documents: Mapping[str, bytes] | None = None
) -> tuple[dict[str, dict], _Model]:
    if not isinstance(records, list):
        _fail("invalid_package", "Records must be an array")
    by_xid = {}
    sibling_ids = set()
    for value in records:
        record = _record_shape(value)
        xid = record["entity"]["xid"]
        if xid in by_xid:
            _fail("invalid_package", f"Duplicate entity XID: {xid}")
        if record["kind"] in ("group", "resource", "version"):
            parent, identifier = xid.rsplit("/", 1)
            key = (parent, identifier.casefold())
            if key in sibling_ids:
                _fail("invalid_package", "Case-insensitive sibling ID collision")
            sibling_ids.add(key)
        by_xid[xid] = record
    registry = by_xid.get("/")
    if registry is None or registry["kind"] != "registry":
        _fail("invalid_package", "Exactly one Registry record is required")
    model = _Model(registry)
    embedded = set()
    versions: dict[str, dict[str, dict]] = {}
    for xid, record in by_xid.items():
        _record_context(record, model)
        kind = record["kind"]
        if kind == "registry":
            parent = None
        elif kind == "group":
            parent = "/"
        elif kind == "resource":
            parent = "/" + "/".join(xid.split("/")[1:3])
        elif kind == "meta":
            parent = xid[:-5]
        else:
            parent = xid.rsplit("/versions/", 1)[0]
            versions.setdefault(parent, {})[record["entity"]["versionid"]] = record
            mode = record["document"]["mode"]
            if mode == "embedded":
                embedded.add(xid)
            if mode == "external" and registry["snapshot"] == "offline-complete":
                _fail("invalid_package", "Offline-complete snapshot has external content")
        if parent is not None and parent not in by_xid:
            _fail("invalid_package", f"Missing parent record: {parent}")
    for xid, record in by_xid.items():
        if record["kind"] != "resource":
            continue
        meta = by_xid.get(xid + "/meta")
        if meta is None or meta["kind"] != "meta":
            _fail("invalid_package", f"Missing Meta: {xid}")
        entries = versions.get(xid, {})
        if "xref" in meta["entity"]:
            if entries:
                _fail("invalid_package", "xref Resource owns Versions")
            continue
        default = meta["entity"]["defaultversionid"]
        if not entries or default not in entries:
            _fail("invalid_package", f"Missing default Version: {xid}")
        for versionid, version in entries.items():
            entity = version["entity"]
            if entity["isdefault"] != (versionid == default):
                _fail("invalid_package", "isdefault disagrees with Meta")
            if entity["ancestorid"] not in entries:
                _fail("invalid_package", "Version ancestor is missing")
            seen = set()
            cursor = versionid
            while entries[cursor]["entity"]["ancestorid"] != cursor:
                if cursor in seen:
                    _fail("invalid_package", "Circular Version ancestry")
                seen.add(cursor)
                cursor = entries[cursor]["entity"]["ancestorid"]
                if cursor not in entries:
                    _fail("invalid_package", "Version ancestor is missing")
    if documents is not None:
        if not isinstance(documents, Mapping) or any(
            not isinstance(key, str) or not isinstance(value, bytes)
            for key, value in documents.items()
        ):
            _fail("invalid_package", "Documents must map Version XIDs to bytes")
        if set(documents) != embedded:
            _fail("invalid_package", "Document bytes do not match embedded Version records")
    return by_xid, model


def _node(kind: str, xid: str, entries: list[dict], **annotations: str) -> dict:
    return {
        "schemaVersion": 2,
        "mediaType": INDEX_MEDIA_TYPE,
        "artifactType": ARTIFACT_TYPES[kind],
        "annotations": _annotations(version="1", kind=kind, xid=xid, **annotations),
        "manifests": entries,
    }


def _edge(descriptor: dict, role: str, xid: str, **annotations: str) -> dict:
    return {
        "mediaType": descriptor["mediaType"],
        "digest": descriptor["digest"],
        "size": descriptor["size"],
        "annotations": _annotations(role=role, xid=xid, **annotations),
    }


class _Builder:
    def __init__(self, root: Path, page_size: int, byte_limit: int):
        self.root = root
        self.page_size = page_size
        self.byte_limit = byte_limit

    def put(self, data: bytes, media_type: str, artifact: str | None = None) -> dict:
        digest = sha256_digest(data)
        path = _safe_path(self.root, Path("blobs") / "sha256" / digest[7:])
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("xb") as output:
                output.write(data)
        except FileExistsError:
            if _read_file(path) != data:
                _fail("integrity_error", "Existing content-addressed blob has wrong bytes")
        descriptor = {"mediaType": media_type, "digest": digest, "size": len(data)}
        if artifact is not None:
            descriptor["artifactType"] = artifact
        return descriptor

    def index(self, node: dict) -> dict:
        data = encode_json(node)
        check_index(data)
        if len(data) > self.byte_limit:
            _fail("limit_exceeded", "Index cannot fit the requested fixture byte budget")
        return self.put(data, INDEX_MEDIA_TYPE, node["artifactType"])

    def route(
        self, kind: str, xid: str, entries: list[dict], lower: str = "", upper: str = ""
    ) -> dict:
        node = _node(kind, xid, entries, mode="leaf", lower=lower, upper=upper)
        if len(entries) <= self.page_size and len(encode_json(node)) <= self.byte_limit:
            return self.index(node)
        if len(entries) < 2:
            _fail("limit_exceeded", "A routing entry cannot fit in one index")
        middle = len(entries) // 2
        boundary = _annotation(entries[middle], "xid")
        left = self.route(kind, xid, entries[:middle], lower, boundary)
        right = self.route(kind, xid, entries[middle:], boundary, upper)
        return self.index(_node(
            kind, xid, [
                _edge(left, "shard", xid, lower=lower, upper=boundary),
                _edge(right, "shard", xid, lower=boundary, upper=upper),
            ], mode="branch", lower=lower, upper=upper,
        ))

    def manifest(self, record: dict, documents: Mapping[str, bytes]) -> dict:
        kind, xid = record["kind"], record["entity"]["xid"]
        config = self.put(encode_json(record), CONFIG_MEDIA_TYPE)
        if kind == "version" and record["document"]["mode"] == "embedded":
            layer = _edge(self.put(documents[xid], DOCUMENT_MEDIA_TYPE), "document", xid)
        else:
            layer = _edge(self.put(b"{}", EMPTY_MEDIA_TYPE), "empty", xid)
        artifact = ARTIFACT_TYPES["version" if kind == "version" else "metadata"]
        manifest = {
            "schemaVersion": 2, "mediaType": MANIFEST_MEDIA_TYPE,
            "artifactType": artifact,
            "annotations": _annotations(version="1", kind=kind, xid=xid),
            "config": _edge(config, "config", xid), "layers": [layer],
        }
        _schema(manifest, "oci-graph.schema.json")
        return self.put(encode_json(manifest), MANIFEST_MEDIA_TYPE, artifact)


def _atomic_write(path: Path, data: bytes) -> None:
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".oci-", delete=False) as f:
            temporary = Path(f.name)
            f.write(data)
        temporary.replace(path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def build_layout(
    path: str | Path,
    records: list[dict],
    documents: Mapping[str, bytes] | None = None,
    *,
    reference: str = "snapshot",
    page_size: int = MAX_DESCRIPTORS,
    max_index_bytes: int = MAX_INDEX_BYTES,
) -> dict:
    """Append/update one tagged root, retaining other roots and existing blobs."""
    if not isinstance(reference, str) or not _TAG.fullmatch(reference):
        _fail("invalid_package", "Builder reference must be a Distribution tag")
    if type(page_size) is not int or not 2 <= page_size <= MAX_DESCRIPTORS:
        _fail("limit_exceeded", "Fixture page_size must be between 2 and 256")
    if type(max_index_bytes) is not int or not 1 <= max_index_bytes <= MAX_INDEX_BYTES:
        _fail("limit_exceeded", "Invalid fixture index byte budget")
    documents = {} if documents is None else documents
    by_xid, model = _records(records, documents)
    root = _layout_root(path)
    root.mkdir(parents=True, exist_ok=True)
    entry_path = _safe_path(root, Path("index.json"))
    layout_path = _safe_path(root, Path("oci-layout"))
    if entry_path.exists() != layout_path.exists():
        _fail("invalid_package", "Incomplete preexisting layout entry point")
    if entry_path.exists():
        header = _object(decode_json(_read_file(layout_path)), "oci-layout")
        if header.get("imageLayoutVersion") != "1.0.0":
            _fail("unsupported_version", "Unsupported image layout version")
        head = check_index(_read_file(entry_path, max_bytes=MAX_INDEX_BYTES), profile=False)
    else:
        head = {"schemaVersion": 2, "mediaType": INDEX_MEDIA_TYPE, "manifests": []}
    matching = [
        entry for entry in head["manifests"]
        if entry.get("annotations", {}).get("org.opencontainers.image.ref.name") == reference
    ]
    if len(matching) > 1:
        _fail("ambiguous", "Existing layout has duplicate tag entries")
    builder = _Builder(root, page_size, max_index_bytes)
    members: dict[str, list[str]] = {}
    for xid, record in by_xid.items():
        if record["kind"] not in ("registry", "meta"):
            members.setdefault(xid.rsplit("/", 1)[0], []).append(xid)

    def entity(xid: str) -> dict:
        record = by_xid[xid]
        kind = record["kind"]
        metadata = builder.manifest(record, documents)
        if kind == "version":
            return metadata
        entries = [_edge(metadata, "metadata", xid)]
        alias = False
        if kind == "resource":
            meta = by_xid[xid + "/meta"]
            alias = "xref" in meta["entity"]
            entries.append(_edge(builder.manifest(meta, documents), "meta", xid + "/meta"))
        collections = []
        for collection_xid in model.collections(kind, xid, alias=alias):
            children = [
                _edge(entity(child), "entity", child)
                for child in sorted(members.get(collection_xid, []))
            ]
            collection = builder.route("collection", collection_xid, children)
            collections.append(_edge(collection, "collection", collection_xid))
        directory = builder.route("collections", xid, collections)
        entries.append(_edge(directory, "collections", xid))
        return builder.index(_node(kind, xid, entries))

    descriptor = entity("/")
    descriptor["annotations"] = {"org.opencontainers.image.ref.name": reference}
    head["manifests"] = [
        entry for entry in head["manifests"]
        if entry.get("annotations", {}).get("org.opencontainers.image.ref.name") != reference
    ] + [descriptor]
    head_data = encode_json(head)
    check_index(head_data, profile=False)
    if len(head_data) > max_index_bytes:
        _fail("limit_exceeded", "Layout entry point exceeds fixture byte budget")
    _atomic_write(layout_path, encode_json({"imageLayoutVersion": "1.0.0"}))
    _atomic_write(entry_path, head_data)
    return copy.deepcopy(descriptor)


class FixtureLayout:
    """A pinned, offline graph reader with an observable, verified fetch cache."""

    def __init__(
        self,
        path: str | Path,
        reference: str | None = None,
        *,
        trace: list[dict] | None = None,
        max_depth: int = 64,
        max_objects: int = 100_000,
    ):
        if type(max_depth) is not int or max_depth < 1:
            _fail("limit_exceeded", "max_depth must be positive")
        if type(max_objects) is not int or max_objects < 1:
            _fail("limit_exceeded", "max_objects must be positive")
        self.path = _layout_root(path)
        self.trace = [] if trace is None else trace
        if not isinstance(self.trace, list):
            _fail("invalid_package", "trace must be a list")
        self.max_depth = max_depth
        self.max_objects = max_objects
        self._bytes: dict[str, bytes] = {}
        self._inventory: dict[str, dict] = {}
        self._registry: dict | None = None
        self._model: _Model | None = None
        header = _object(decode_json(self._bootstrap("oci-layout")), "oci-layout")
        if header.get("imageLayoutVersion") != "1.0.0":
            _fail("unsupported_version", "Unsupported image layout version")
        head = check_index(self._bootstrap("index.json"), profile=False)
        if reference is not None and (
            not isinstance(reference, str)
            or not (_DIGEST.fullmatch(reference) or _TAG.fullmatch(reference))
        ):
            _fail("invalid_package", "Invalid layout reference")
        if reference is not None and _DIGEST.fullmatch(reference):
            candidates = [d for d in head["manifests"] if d["digest"] == reference]
            if candidates:
                descriptor = candidates[0]
                if any(
                    d["size"] != descriptor["size"]
                    or d["mediaType"] != descriptor["mediaType"] for d in candidates
                ):
                    _fail("invalid_package", "Conflicting descriptors for root digest")
            else:
                relative = Path("blobs") / "sha256" / reference[7:]
                data = _read_file(
                    _safe_path(self.path, relative), missing="not_found",
                    max_bytes=MAX_INDEX_BYTES,
                )
                descriptor = {
                    "mediaType": INDEX_MEDIA_TYPE, "digest": reference, "size": len(data),
                }
                self._accept(descriptor, data)
        elif reference is not None:
            candidates = [
                d for d in head["manifests"]
                if d.get("annotations", {}).get("org.opencontainers.image.ref.name") == reference
            ]
            if not candidates:
                _fail("not_found", "Layout tag not found")
            if len(candidates) != 1:
                _fail("ambiguous", "More than one entry has the selected tag")
            descriptor = candidates[0]
            if descriptor.get("artifactType") != ARTIFACT_TYPES["registry"]:
                _fail("invalid_package", "Selected tag entry lacks the Registry artifactType")
        else:
            candidates = {}
            for entry in head["manifests"]:
                if (
                    entry.get("artifactType") != ARTIFACT_TYPES["registry"]
                    or entry["mediaType"] != INDEX_MEDIA_TYPE
                ):
                    continue
                previous = candidates.get(entry["digest"])
                if previous is not None and previous["size"] != entry["size"]:
                    _fail("invalid_package", "Conflicting descriptors for root digest")
                candidates[entry["digest"]] = entry
            if not candidates:
                _fail("not_found", "No eligible Registry root")
            if len(candidates) != 1:
                _fail("ambiguous", "Select one Registry snapshot root explicitly")
            descriptor = next(iter(candidates.values()))
        self.root_descriptor = copy.deepcopy(_descriptor(descriptor, internal=False))
        self.root_digest = self.root_descriptor["digest"]
        self._entity_node(self.root_descriptor, "registry", "/")

    def _bootstrap(self, name: str) -> bytes:
        data = _read_file(
            _safe_path(self.path, Path(name)),
            max_bytes=MAX_INDEX_BYTES if name == "index.json" else None,
        )
        self.trace.append({"path": name, "route": "layout", "size": len(data)})
        return data

    def _accept(self, descriptor: dict, data: bytes) -> bytes:
        _descriptor(descriptor, internal=False)
        if len(data) != descriptor["size"] or sha256_digest(data) != descriptor["digest"]:
            _fail("integrity_error", f"Descriptor mismatch: {descriptor['digest']}")
        digest = descriptor["digest"]
        if digest not in self._bytes:
            if len(self._bytes) >= self.max_objects:
                _fail("limit_exceeded", "Fixture object budget exhausted")
            self._bytes[digest] = data
            item = {key: descriptor[key] for key in ("digest", "mediaType", "size")}
            self._inventory[digest] = item
            self.trace.append({
                **item, "path": f"blobs/sha256/{digest[7:]}",
                "route": "manifests" if descriptor["mediaType"] in (
                    INDEX_MEDIA_TYPE, MANIFEST_MEDIA_TYPE
                ) else "blobs",
            })
        return data

    def fetch(self, descriptor: dict) -> bytes:
        """Fetch and verify one descriptor; cached bytes are checked for each edge."""
        _descriptor(descriptor, internal=False)
        is_index = descriptor["mediaType"] == INDEX_MEDIA_TYPE
        if is_index and descriptor["size"] > MAX_INDEX_BYTES:
            _fail("limit_exceeded", "Index descriptor exceeds 1048576 bytes")
        digest = descriptor["digest"]
        data = self._bytes.get(digest)
        if data is None:
            if len(self._bytes) >= self.max_objects:
                _fail("limit_exceeded", "Fixture object budget exhausted")
            data = _read_file(
                _safe_path(self.path, Path("blobs") / "sha256" / digest[7:]),
                max_bytes=MAX_INDEX_BYTES if is_index else None,
            )
        return self._accept(descriptor, data)

    @property
    def inventory(self) -> list[dict]:
        """Only actually fetched objects; validate() populates the entire closure."""
        return [copy.deepcopy(self._inventory[key]) for key in sorted(self._inventory)]

    def _read_node(self, descriptor: dict, kind: str, xid: str) -> dict:
        data = self.fetch(descriptor)
        if descriptor["mediaType"] == INDEX_MEDIA_TYPE:
            node = check_index(data)
        elif descriptor["mediaType"] == MANIFEST_MEDIA_TYPE:
            node = _object(decode_json(data), "manifest")
            if type(node.get("schemaVersion")) is not int or node["schemaVersion"] != 2:
                _fail("invalid_package", "Manifest schemaVersion must be integer 2")
            _node_header(node)
            _schema(node, "oci-graph.schema.json")
            _descriptor(node["config"])
            for layer in node["layers"]:
                _descriptor(layer)
        else:
            _fail("invalid_package", "A graph node must be an index or manifest")
        if node["mediaType"] != descriptor["mediaType"]:
            _fail("invalid_package", "Descriptor and node media types differ")
        if "artifactType" in descriptor and descriptor["artifactType"] != node["artifactType"]:
            _fail("invalid_package", "Descriptor and node artifact types differ")
        if _node_header(node) != (kind, xid):
            _fail("invalid_package", "Descriptor path or kind disagrees with target")
        return node

    @staticmethod
    def _require_edge(descriptor: dict, role: str, xid: str, media_type: str) -> None:
        _descriptor(descriptor)
        if (
            _annotation(descriptor, "role") != role
            or _annotation(descriptor, "xid") != xid
            or descriptor["mediaType"] != media_type
        ):
            _fail("invalid_package", f"Wrong {role} edge at {xid}")

    def _entity_node(self, descriptor: dict, kind: str, xid: str) -> dict:
        if descriptor["mediaType"] != INDEX_MEDIA_TYPE:
            _fail("invalid_package", "Entity containment must be an OCI index")
        node = self._read_node(descriptor, kind, xid)
        expected = [("metadata", xid, MANIFEST_MEDIA_TYPE)]
        if kind == "resource":
            expected.append(("meta", xid + "/meta", MANIFEST_MEDIA_TYPE))
        expected.append(("collections", xid, INDEX_MEDIA_TYPE))
        if len(node["manifests"]) != len(expected):
            _fail("invalid_package", "Wrong entity index descriptor count")
        for edge, (role, target, media_type) in zip(node["manifests"], expected):
            self._require_edge(edge, role, target, media_type)
        return node

    def _record(self, descriptor: dict, kind: str, xid: str) -> tuple[dict, dict]:
        if descriptor["mediaType"] != MANIFEST_MEDIA_TYPE:
            _fail("invalid_package", "Metadata leaf must be an OCI manifest")
        manifest = self._read_node(descriptor, kind, xid)
        self._require_edge(manifest["config"], "config", xid, CONFIG_MEDIA_TYPE)
        record = _record_shape(decode_json(self.fetch(manifest["config"])))
        if record["kind"] != kind or record["entity"]["xid"] != xid:
            _fail("invalid_package", "Config identity disagrees with manifest")
        layer = manifest["layers"][0]
        embedded = kind == "version" and record["document"]["mode"] == "embedded"
        if embedded:
            self._require_edge(layer, "document", xid, DOCUMENT_MEDIA_TYPE)
        else:
            self._require_edge(layer, "empty", xid, EMPTY_MEDIA_TYPE)
            if layer["digest"] != sha256_digest(b"{}") or layer["size"] != 2:
                _fail("invalid_package", "Incorrect unused-layer placeholder")
        if self._model is not None:
            _record_context(record, self._model)
        return record, manifest

    def _context(self) -> tuple[dict, _Model]:
        if self._registry is None:
            node = self._entity_node(self.root_descriptor, "registry", "/")
            registry, _ = self._record(node["manifests"][0], "registry", "/")
            model = _Model(registry)
            _record_context(registry, model)
            self._registry, self._model = registry, model
        if self._model is None:
            _fail("invalid_package", "Incomplete model bootstrap")
        return self._registry, self._model

    @staticmethod
    def _key(key: str, kind: str, xid: str) -> None:
        validate_xid(key, collection=kind == "collections")
        parent = key.rsplit("/", 1)[0] or "/"
        if parent != xid:
            _fail("invalid_package", "Routing key is outside its typed collection")

    @staticmethod
    def _inside(key: str, lower: str, upper: str) -> bool:
        return (not lower or lower <= key) and (not upper or key < upper)

    def _routing(
        self, descriptor: dict, kind: str, xid: str,
        lower: str = "", upper: str = "", depth: int = 0,
    ) -> dict:
        if depth >= self.max_depth:
            _fail("limit_exceeded", "Routing depth budget exhausted")
        if descriptor["mediaType"] != INDEX_MEDIA_TYPE:
            _fail("invalid_package", "Routing requires a standard image index")
        node = self._read_node(descriptor, kind, xid)
        if (_annotation(node, "lower"), _annotation(node, "upper")) != (lower, upper):
            _fail("invalid_package", "Shard bounds disagree with parent descriptor")
        for bound in (lower, upper):
            if bound:
                self._key(bound, kind, xid)
        if lower and upper and lower >= upper:
            _fail("invalid_package", "Empty or inverted range")
        entries = node["manifests"]
        mode = _annotation(node, "mode")
        if mode == "leaf":
            if not entries and (lower or upper):
                _fail("invalid_package", "Empty non-root shard")
            previous = None
            identifiers = set()
            for edge in entries:
                key = _annotation(edge, "xid")
                self._key(key, kind, xid)
                identifier = key.rsplit("/", 1)[-1].casefold()
                if identifier in identifiers:
                    _fail("invalid_package", "Case-insensitive sibling ID collision")
                identifiers.add(identifier)
                if not self._inside(key, lower, upper) or (
                    previous is not None and previous >= key
                ):
                    _fail("invalid_package", "Unsorted, duplicate or out-of-range key")
                role = "collection" if kind == "collections" else "entity"
                media = INDEX_MEDIA_TYPE
                if kind == "collection" and xid.endswith("/versions"):
                    media = MANIFEST_MEDIA_TYPE
                self._require_edge(edge, role, key, media)
                previous = key
        else:
            if mode != "branch" or len(entries) < 2:
                _fail("invalid_package", "Branch must have at least two shards")
            previous = lower
            for number, edge in enumerate(entries):
                self._require_edge(edge, "shard", xid, INDEX_MEDIA_TYPE)
                start, end = _annotation(edge, "lower"), _annotation(edge, "upper")
                for bound in (start, end):
                    if bound:
                        self._key(bound, kind, xid)
                if start != previous or (start and end and start >= end):
                    _fail("invalid_package", "Overlapping or gapped shard ranges")
                if number < len(entries) - 1 and not end:
                    _fail("invalid_package", "Unbounded nonfinal shard")
                if number > 0 and not start:
                    _fail("invalid_package", "Unbounded nonfirst shard")
                previous = end
            if previous != upper:
                _fail("invalid_package", "Shards do not cover the parent range")
        return node

    def _entries(
        self, descriptor: dict, kind: str, xid: str, lower: str = "", upper: str = "",
        depth: int = 0, active: frozenset[str] = frozenset(),
    ) -> Iterator[dict]:
        digest = descriptor["digest"]
        if digest in active:
            _fail("invalid_package", "Circular routing graph")
        node = self._routing(descriptor, kind, xid, lower, upper, depth)
        if _annotation(node, "mode") == "leaf":
            yield from node["manifests"]
            return
        identifiers = set()
        for edge in node["manifests"]:
            found = False
            for entry in self._entries(
                edge, kind, xid, _annotation(edge, "lower"), _annotation(edge, "upper"),
                depth + 1, active | {digest},
            ):
                found = True
                identifier = _annotation(entry, "xid").rsplit("/", 1)[-1].casefold()
                if identifier in identifiers:
                    _fail("invalid_package", "Case-insensitive sibling ID collision")
                identifiers.add(identifier)
                yield entry
            if not found:
                _fail("invalid_package", "Shard contains no eventual entries")

    def _find(self, descriptor: dict, kind: str, xid: str, key: str) -> dict:
        self._key(key, kind, xid)
        lower, upper = "", ""
        active = set()
        for depth in range(self.max_depth):
            if descriptor["digest"] in active:
                _fail("invalid_package", "Circular routing graph")
            active.add(descriptor["digest"])
            node = self._routing(descriptor, kind, xid, lower, upper, depth)
            if _annotation(node, "mode") == "leaf":
                for edge in node["manifests"]:
                    if _annotation(edge, "xid") == key:
                        return edge
                _fail("not_found", f"No entity or collection at {key}")
            selected = [
                edge for edge in node["manifests"]
                if self._inside(key, _annotation(edge, "lower"), _annotation(edge, "upper"))
            ]
            if len(selected) != 1:
                _fail("invalid_package", "Key has no unique range")
            descriptor = selected[0]
            lower, upper = _annotation(descriptor, "lower"), _annotation(descriptor, "upper")
        _fail("limit_exceeded", "Routing depth budget exhausted")

    def _locate(self, xid: str) -> tuple[dict, str]:
        validate_xid(xid)
        self._context()
        if xid == "/":
            return self.root_descriptor, "registry"
        parts = xid[1:].split("/")
        descriptor, kind, current = self.root_descriptor, "registry", "/"
        for offset in (0, 2, 4):
            if offset >= len(parts):
                break
            node = self._entity_node(descriptor, kind, current)
            if offset == 4:
                meta, _ = self._record(node["manifests"][1], "meta", current + "/meta")
                if parts[4] == "meta":
                    return node["manifests"][1], "meta"
                if "xref" in meta["entity"]:
                    _fail("unsupported_operation", "cannot_doc_xref")
            collection_xid = "/" + "/".join(parts[:offset + 1])
            collection = self._required_collection(node, kind, current, collection_xid)
            current = "/" + "/".join(parts[:offset + 2])
            descriptor = self._find(collection, "collection", collection_xid, current)
            kind = ("group", "resource", "version")[offset // 2]
        return descriptor, kind

    def _required_collection(self, node: dict, kind: str, owner: str, xid: str) -> dict:
        _, model = self._context()
        if xid not in model.collections(kind, owner):
            _fail("not_found", f"Unknown collection type: {xid}")
        try:
            return self._find(node["manifests"][-1], "collections", owner, xid)
        except FederationError as error:
            if error.code != "not_found":
                raise
            raise FederationError("invalid_package", f"Missing model collection: {xid}") from error

    def _collection(self, xid: str) -> dict:
        validate_xid(xid, collection=True)
        parent = xid.rsplit("/", 1)[0] or "/"
        descriptor, kind = self._locate(parent)
        node = self._entity_node(descriptor, kind, parent)
        if kind == "resource":
            meta, _ = self._record(node["manifests"][1], "meta", parent + "/meta")
            if "xref" in meta["entity"]:
                _fail("unsupported_operation", "cannot_doc_xref")
        return self._required_collection(node, kind, parent, xid)

    def _resource_state(self, xid: str) -> tuple[dict, dict, dict]:
        descriptor, kind = self._locate(xid)
        if kind != "resource":
            _fail("invalid_package", "Expected a Resource")
        node = self._entity_node(descriptor, kind, xid)
        resource, _ = self._record(node["manifests"][0], "resource", xid)
        meta, _ = self._record(node["manifests"][1], "meta", xid + "/meta")
        return node, resource, meta

    def _document_source(self, xid: str) -> tuple[str, dict, dict]:
        node, _, meta = self._resource_state(xid)
        target = meta["entity"].get("xref")
        if target is not None:
            node, _, meta = self._resource_state(target)
            if "xref" in meta["entity"]:
                _fail("not_found", "One-hop target is itself an alias")
            xid = target
        return xid, node, meta

    def _version(
        self, resource_xid: str, node: dict, meta: dict, versionid: str
    ) -> tuple[dict, dict, str]:
        collection_xid = resource_xid + "/versions"
        collection = self._required_collection(node, "resource", resource_xid, collection_xid)
        xid = collection_xid + "/" + versionid
        try:
            descriptor = self._find(collection, "collection", collection_xid, xid)
        except FederationError as error:
            if error.code != "not_found" or versionid != meta["entity"]["defaultversionid"]:
                raise
            raise FederationError("invalid_package", "Default Version is missing") from error
        record, manifest = self._record(descriptor, "version", xid)
        if record["entity"]["isdefault"] != (versionid == meta["entity"]["defaultversionid"]):
            _fail("invalid_package", "Version isdefault disagrees with Meta")
        registry, _ = self._context()
        if record["document"]["mode"] == "external" and registry["snapshot"] == "offline-complete":
            _fail("invalid_package", "Offline-complete snapshot has external content")
        return record, manifest, xid

    @staticmethod
    def _pointer(path: str) -> str:
        return "#" + path

    def _metadata(self, descriptor: dict, kind: str, xid: str, pointer: str = "") -> dict:
        if kind == "version":
            resource_xid = xid.rsplit("/versions/", 1)[0]
            node, _, meta = self._resource_state(resource_xid)
            record, _, _ = self._version(resource_xid, node, meta, xid.rsplit("/", 1)[1])
            result = copy.deepcopy(record["entity"])
            result["self"] = self._pointer(pointer)
            return result
        node = self._entity_node(descriptor, kind, xid)
        record, _ = self._record(node["manifests"][0], kind, xid)
        result = copy.deepcopy(record["entity"])
        result["self"] = self._pointer(pointer)
        alias = False
        if kind == "resource":
            meta, _ = self._record(node["manifests"][1], "meta", xid + "/meta")
            result["meta"] = copy.deepcopy(meta["entity"])
            result["meta"]["self"] = self._pointer(pointer + "/meta")
            result["metaurl"] = self._pointer(pointer + "/meta")
            alias = "xref" in meta["entity"]
            if not alias:
                version_key = meta["entity"]["defaultversionid"].replace("~", "~0")
                result["meta"]["defaultversionurl"] = self._pointer(
                    pointer + "/versions/" + version_key
                )
        _, model = self._context()
        collection_edges = list(self._entries(node["manifests"][-1], "collections", xid))
        expected = model.collections(kind, xid, alias=alias)
        if [_annotation(edge, "xid") for edge in collection_edges] != expected:
            _fail("invalid_package", "Directory does not match model or xref state")
        for collection in collection_edges:
            path = _annotation(collection, "xid")
            name = path.rsplit("/", 1)[1]
            items = {}
            child_kind = {"registry": "group", "group": "resource", "resource": "version"}[kind]
            for edge in self._entries(collection, "collection", path):
                child_xid = _annotation(edge, "xid")
                key = child_xid.rsplit("/", 1)[1]
                escaped = key.replace("~", "~0").replace("/", "~1")
                items[key] = self._metadata(edge, child_kind, child_xid, pointer + "/" + name + "/" + escaped)
            result[name] = items
            result[name + "count"] = len(items)
            result[name + "url"] = self._pointer(pointer + "/" + name)
        if kind == "resource" and not alias:
            if result["meta"]["defaultversionid"] not in result["versions"]:
                _fail("invalid_package", "Default Version does not exist")
        return result

    def _selection_entity(self, descriptor: dict, kind: str, xid: str) -> dict:
        if kind != "resource":
            if kind == "version":
                owner = xid.rsplit("/versions/", 1)[0]
                node, _, meta = self._resource_state(owner)
                record, _, _ = self._version(owner, node, meta, xid.rsplit("/", 1)[1])
            else:
                descriptor = self._entity_node(descriptor, kind, xid)["manifests"][0]
                record, _ = self._record(descriptor, kind, xid)
            return copy.deepcopy(record["entity"])
        _, resource, _ = self._resource_state(xid)
        try:
            target, node, meta = self._document_source(xid)
        except FederationError as error:
            if error.code != "not_found":
                raise
            return copy.deepcopy(resource["entity"])
        record, _, _ = self._version(target, node, meta, meta["entity"]["defaultversionid"])
        return {**copy.deepcopy(record["entity"]), **copy.deepcopy(resource["entity"])}

    def lookup(
        self, target: str, *, operation: str = "entity", selector: dict | None = None
    ) -> dict:
        """Return a metadata document + pointer, or exact document bytes in data."""
        if operation not in ("entity", "collection", "document", "model", "capabilities"):
            _fail("unsupported_operation", "Unknown fixture read operation")
        if selector is not None and operation != "collection":
            _fail("unsupported_operation", "Selectors apply only to collections")
        registry, _ = self._context()
        result = {"snapshot": self.root_digest, "operation": operation, "target": target}
        if operation in ("model", "capabilities"):
            if target != "/":
                _fail("unsupported_operation", "Model/capabilities target must be /")
            value = registry["entity"]["capabilities"] if operation == "capabilities" else {
                "model": registry["entity"]["model"],
                "modelsource": registry["entity"]["modelsource"],
                "resolvedmodelsource": registry["modelresolved"],
            }
            return {**result, "value": copy.deepcopy(value), "pointer": ""}
        validate_xid(target, collection=operation == "collection")
        if operation == "document":
            parts = target[1:].split("/")
            if len(parts) not in (4, 6):
                _fail("unsupported_operation", "Only Resources and Versions have documents")
            resource_xid = "/" + "/".join(parts[:4])
            source, node, meta = self._document_source(resource_xid)
            versionid = parts[5] if len(parts) == 6 else meta["entity"]["defaultversionid"]
            record, manifest, version_xid = self._version(source, node, meta, versionid)
            mode = record["document"]["mode"]
            if mode == "metadata-only":
                _fail("unsupported_operation", "Resource is metadata-only")
            if mode == "external":
                _fail("unavailable", "Offline fixture helper does not fetch external documents")
            return {
                **result, "resolved": version_xid,
                "mediaType": record["entity"].get("contenttype", "application/octet-stream"),
                "data": self.fetch(manifest["layers"][0]),
                **{
                    key: record["document"][key] for key in ("origin", "base")
                    if key in record["document"]
                },
            }
        if operation == "collection":
            descriptor = self._collection(target)
            kind = {1: "group", 3: "resource", 5: "version"}[len(target[1:].split("/"))]
            entries = list(self._entries(descriptor, "collection", target))
            if selector is not None:
                if not isinstance(selector, dict) or set(selector) != {"label", "value"}:
                    _fail("invalid_package", "Selector needs exactly label and value")
                entities = [
                    self._selection_entity(edge, kind, _annotation(edge, "xid"))
                    for edge in entries
                ]
                selected = select_label(entities, selector["label"], selector["value"])
                target = selected["xid"]
                edge = next(edge for edge in entries if _annotation(edge, "xid") == target)
                return {
                    **result, "target": target,
                    "value": self._metadata(edge, kind, target), "pointer": "",
                }
            value = {}
            for edge in entries:
                xid = _annotation(edge, "xid")
                key = xid.rsplit("/", 1)[1]
                escaped = key.replace("~", "~0").replace("/", "~1")
                value[key] = self._metadata(edge, kind, xid, "/" + escaped)
            return {**result, "value": value, "pointer": ""}
        descriptor, kind = self._locate(target)
        pointer = ""
        if kind == "meta":
            owner = target[:-5]
            descriptor, kind = self._locate(owner)
            value = self._metadata(descriptor, kind, owner)
            pointer = "/meta"
        else:
            value = self._metadata(descriptor, kind, target)
        return {**result, "value": value, "pointer": pointer}

    def validate(self) -> dict:
        """Walk all required edges; unlike lookup, this deliberately reads payloads."""
        self._context()
        records = []
        seen = set()
        index_sizes = []
        index_counts = []
        document_count = 0

        def leaf(descriptor: dict, kind: str, xid: str) -> dict:
            nonlocal document_count
            if xid in seen:
                _fail("invalid_package", "Duplicate structural entity")
            seen.add(xid)
            record, manifest = self._record(descriptor, kind, xid)
            records.append(record)
            data = self.fetch(manifest["layers"][0])
            if kind != "version" or record["document"]["mode"] != "embedded":
                if data != b"{}":
                    _fail("integrity_error", "Unused layer is not the OCI placeholder")
            else:
                document_count += 1
            return record

        def walk(descriptor: dict, kind: str, xid: str) -> None:
            if kind == "version":
                leaf(descriptor, kind, xid)
                return
            node = self._entity_node(descriptor, kind, xid)
            leaf(node["manifests"][0], kind, xid)
            alias = False
            if kind == "resource":
                meta = leaf(node["manifests"][1], "meta", xid + "/meta")
                alias = "xref" in meta["entity"]
            edges = list(self._entries(node["manifests"][-1], "collections", xid))
            if [_annotation(edge, "xid") for edge in edges] != self._model.collections(
                kind, xid, alias=alias
            ):
                _fail("invalid_package", "Directory does not enumerate model collections")
            child_kind = {"registry": "group", "group": "resource", "resource": "version"}[kind]
            for collection in edges:
                path = _annotation(collection, "xid")
                for child in self._entries(collection, "collection", path):
                    walk(child, child_kind, _annotation(child, "xid"))

        walk(self.root_descriptor, "registry", "/")
        _records(records)
        for item in self.inventory:
            if item["mediaType"] == INDEX_MEDIA_TYPE:
                data = self._bytes[item["digest"]]
                index_sizes.append(len(data))
                index_counts.append(len(check_index(data)["manifests"]))
        return {
            "root": self.root_digest, "snapshot": self._registry["snapshot"],
            "objects": len(self._inventory), "records": len(records),
            "indexes": len(index_sizes),
            "manifests": sum(i["mediaType"] == MANIFEST_MEDIA_TYPE for i in self.inventory),
            "documents": document_count,
            "max_index_descriptors": max(index_counts),
            "max_index_bytes": max(index_sizes),
        }


def validate_layout(path: str | Path, reference: str | None = None, **limits) -> dict:
    return FixtureLayout(path, reference, **limits).validate()


def lookup_layout(
    path: str | Path, target: str, *, reference: str | None = None,
    operation: str = "entity", selector: dict | None = None,
    trace: list[dict] | None = None,
) -> dict:
    return FixtureLayout(path, reference, trace=trace).lookup(
        target, operation=operation, selector=selector
    )


def _rename_template(value: object, names: dict[str, str]) -> object:
    if isinstance(value, dict):
        return {names.get(k, k): _rename_template(v, names) for k, v in value.items()}
    if isinstance(value, list):
        return [_rename_template(v, names) for v in value]
    return names.get(value, value) if isinstance(value, str) else value


def sample_records(*, linked: bool = False) -> tuple[list[dict], dict[str, bytes]]:
    """Synthetic Core dirs/files fixtures, using the repository's full-model example."""
    source = {
        "groups": {
            "dirs": {
                "singular": "dir",
                "resources": {
                    "files": {
                        "singular": "file",
                        "attributes": {"extra": {"type": "object", "attributes": {"*": {"type": "any"}}}},
                    },
                    "notes": {"singular": "note", "hasdocument": False},
                },
            },
            "emptygroups": {"singular": "emptygroup"},
            "imports": {"singular": "import", "ximportresources": ["/dirs/files"]},
        }
    }
    full = _object(decode_json(_read_file(_ROOT / "core" / "sample-model-full.json")), "Core full model")
    dirs = full["groups"]["dirs"]
    files = dirs["resources"]["files"]
    files["metaattributes"]["xref"]["type"] = "xid"
    files["attributes"]["extra"] = {
        "name": "extra", "type": "object", "attributes": {"*": {"type": "any"}},
    }
    notes = _object(_rename_template(files, {
        "files": "notes", "file": "note", "fileid": "noteid",
        "fileurl": "noteurl", "filebase64": "notebase64",
    }), "sample metadata-only model")
    notes["hasdocument"] = False
    notes["attributes"].pop("extra")
    for key in ("note", "noteurl", "notebase64"):
        notes["attributes"].pop(key)
    dirs["resources"]["notes"] = notes
    for name in ("files", "filesurl", "filescount"):
        renamed = name.replace("files", "notes")
        dirs["attributes"][renamed] = _rename_template(dirs["attributes"][name], {name: renamed})
    for plural, singular in (("emptygroups", "emptygroup"), ("imports", "import")):
        group = _object(_rename_template(
            dirs, {"dirs": plural, "dir": singular, "dirid": singular + "id"}
        ), "sample Group model")
        group["resources"] = {} if plural == "emptygroups" else {"files": copy.deepcopy(files)}
        for collection in ("files", "notes"):
            if collection not in group["resources"]:
                for suffix in ("", "url", "count"):
                    group["attributes"].pop(collection + suffix)
        full["groups"][plural] = group
        for suffix in ("", "url", "count"):
            name = "dirs" + suffix
            replacement = plural + suffix
            full["attributes"][replacement] = _rename_template(
                full["attributes"][name], {name: replacement}
            )
    timestamp = "2026-09-01T12:00:00Z"
    common = {"epoch": 1, "createdat": timestamp, "modifiedat": timestamp}
    registry = {
        "formatversion": 1, "kind": "registry",
        "snapshot": "linked" if linked else "offline-complete",
        "modelresolved": copy.deepcopy(source),
        "entity": {
            "xid": "/", "registryid": "fixture-linked" if linked else "fixture-offline",
            "specversion": CORE_VERSION, **common,
            "modelsource": source, "model": full,
            "capabilities": {
                "available": {
                    name: {"mutable": False}
                    for name in ("capabilities", "entities", "model", "modelsource")
                },
                "mutable": [], "flags": [], "pagination": False,
            },
        },
    }
    records = [registry]
    documents = {}

    def record(kind: str, entity: dict, mode: str | None = None) -> None:
        item = {"formatversion": 1, "kind": kind, "entity": entity}
        if mode is not None:
            item["document"] = {"mode": mode}
        records.append(item)

    for xid, key, value in (
        ("/dirs/main", "dirid", "main"),
        ("/dirs/empty", "dirid", "empty"),
        ("/imports/shared", "importid", "shared"),
    ):
        entity = {"xid": xid, key: value, **common}
        if value == "main":
            entity["labels"] = {"stage": "Ready", "empty": ""}
        record("group", entity)

    def resource(
        xid: str, versions: list[tuple[str, str, bytes | None, dict]],
        *, default: str = "v1", xref: str | None = None, singular: str = "file",
    ) -> None:
        resource_id = xid.rsplit("/", 1)[1]
        identity = {singular + "id": resource_id}
        record("resource", {"xid": xid, **identity})
        meta = {"xid": xid + "/meta", **identity}
        if xref is not None:
            meta["xref"] = xref
        else:
            meta.update({
                **common, "readonly": False, "defaultversionid": default,
                "defaultversionsticky": True,
            })
        record("meta", meta)
        for versionid, mode, data, extra in versions:
            version_xid = xid + "/versions/" + versionid
            record("version", {
                "xid": version_xid, **identity, **common, "versionid": versionid,
                "ancestorid": "v1", "isdefault": versionid == default, **extra,
            }, mode)
            if data is not None:
                documents[version_xid] = data

    sample = "/dirs/main/files/sample"
    resource(sample, [
        ("v1", "embedded", b'{"type":"string"}\n', {
            "contenttype": "application/schema+json", "labels": {"stage": "Ready", "empty": ""},
            "extra": {"nested": {"self": "extension data, not navigation"}, "enabled": True},
        }),
        ("v2", "external" if linked else "embedded", None if linked else b'{"type":"number"}\n', {
            "contenttype": "application/schema+json",
            **({"fileurl": "https://documents.example.org/sample-v2.json"} if linked else {}),
        }),
    ])
    resource("/dirs/main/files/binary", [
        ("v1", "embedded", b"\x00\x01\x7f\x80\xff\r\n", {"contenttype": "application/octet-stream"}),
    ])
    resource("/dirs/main/files/empty", [
        ("v1", "embedded", b"", {"contenttype": "text/plain; charset=utf-8"}),
    ])
    resource("/dirs/main/notes/info", [("v1", "metadata-only", None, {})], singular="note")
    resource("/dirs/main/files/alias", [], xref=sample)
    resource("/dirs/main/files/dangling", [], xref="/dirs/missing/files/sample")
    resource("/dirs/main/files/chain", [], xref="/dirs/main/files/alias")
    resource("/imports/shared/files/alias", [], xref=sample)
    return records, documents


def _fixture_input(path: Path) -> tuple[list[dict], dict[str, bytes]]:
    value = _object(decode_json(_read_file(path)), "fixture input")
    if value.keys() - {"records", "documents"} or "records" not in value:
        _fail("invalid_package", "Fixture input needs records and optional documents")
    encoded = _object(value.get("documents", {}), "fixture documents")
    documents = {}
    for xid, data in encoded.items():
        if not isinstance(data, str):
            _fail("invalid_package", "Fixture document must be a base64 string")
        try:
            documents[xid] = base64.b64decode(data, validate=True)
        except (binascii.Error, ValueError) as error:
            raise FederationError("invalid_package", "Invalid fixture base64") from error
    return value["records"], documents


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="Construct one snapshot in a local layout")
    build.add_argument("layout", type=Path)
    inputs = build.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--sample", action="store_true")
    inputs.add_argument("--input", type=Path)
    build.add_argument("--linked", action="store_true", help="Use the linked sample variant")
    build.add_argument("--reference", default="snapshot")
    build.add_argument("--page-size", type=int, default=MAX_DESCRIPTORS)
    build.add_argument("--max-index-bytes", type=int, default=MAX_INDEX_BYTES)
    for name in ("validate", "lookup"):
        command = commands.add_parser(name)
        command.add_argument("layout", type=Path)
        command.add_argument("--reference")
        command.add_argument("--trace", type=Path)
        if name == "validate":
            command.add_argument("--inventory", type=Path)
        else:
            command.add_argument("target")
            command.add_argument("--operation", default="entity",
                                 choices=("entity", "collection", "document", "model", "capabilities"))
            command.add_argument("--label")
            command.add_argument("--value")
    args = parser.parse_args(argv)
    trace = []
    failure = None
    try:
        if args.command == "build":
            if args.linked and not args.sample:
                _fail("unsupported_operation", "--linked applies only to --sample")
            records, documents = sample_records(linked=args.linked) if args.sample else _fixture_input(args.input)
            result = build_layout(
                args.layout, records, documents, reference=args.reference,
                page_size=args.page_size, max_index_bytes=args.max_index_bytes,
            )
        else:
            layout = FixtureLayout(args.layout, args.reference, trace=trace)
            if args.command == "validate":
                result = layout.validate()
                if args.inventory is not None:
                    args.inventory.write_bytes(encode_json(layout.inventory))
            else:
                if (args.label is None) != (args.value is None):
                    _fail("invalid_package", "--label and --value must be supplied together")
                selector = None if args.label is None else {"label": args.label, "value": args.value}
                result = layout.lookup(args.target, operation=args.operation, selector=selector)
                if "data" in result:
                    data = result.pop("data")
                    result["base64"] = base64.b64encode(data).decode("ascii")
                    result["size"] = len(data)
    except FederationError as error:
        failure = {"error": error.code, "message": str(error)}
    except OSError as error:
        failure = {"error": "unavailable", "message": str(error)}
    try:
        if getattr(args, "trace", None) is not None:
            args.trace.write_bytes(encode_json(trace))
    except OSError as error:
        if failure is not None:
            print(json.dumps(failure), file=sys.stderr)
        failure = {"error": "unavailable", "message": f"Cannot save trace: {error}"}
    if failure is not None:
        print(json.dumps(failure), file=sys.stderr)
        return 1
    print(encode_json(result).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
