"""Offline examples of federation selection, not a network resolver."""

from decimal import Decimal
import base64
import binascii
import copy
import json
import math
from pathlib import Path
import re
from urllib.parse import quote, unquote_to_bytes, urlsplit


class FederationError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


EXAMPLE_SOURCE = Path(__file__).resolve().parents[1] / "examples.json"
MAX_EXAMPLE_BYTES = 16 * 1024 * 1024
EXAMPLE_SCHEMA = {
    "type": "object", "required": ["exampleformat", "examples"],
    "additionalProperties": False,
    "properties": {
        "exampleformat": {"type": "integer", "const": 1},
        "examples": {
            "type": "object", "minProperties": 1,
            "propertyNames": {"pattern": "^[a-z][a-z0-9-]*$"},
            "additionalProperties": {"$ref": "#/$defs/example"},
        },
    },
    "$defs": {
        "example": {
            "type": "object", "required": ["snapshot", "records", "documents"],
            "additionalProperties": False,
            "properties": {
                "snapshot": {"enum": ["offline-complete", "linked"]},
                "resolvedmodelsource": {"type": "object"},
                "modelbase": {"type": "string", "format": "uri"},
                "source": {
                    "type": "object", "required": ["uri"],
                    "additionalProperties": False,
                    "properties": {
                        "uri": {"type": "string", "format": "uri"},
                        "revision": {"type": "string", "minLength": 1},
                    },
                },
                "records": {
                    "type": "array", "minItems": 1, "maxItems": 100000,
                    "items": {
                        "type": "object", "required": ["kind", "entity"],
                        "additionalProperties": False,
                        "properties": {
                            "kind": {"enum": ["registry", "group", "resource", "meta", "version"]},
                            "entity": {
                                "type": "object", "required": ["xid"],
                                "properties": {"xid": {"type": "string"}},
                            },
                        },
                    },
                },
                "documents": {
                    "type": "object",
                    "additionalProperties": {"$ref": "#/$defs/document"},
                },
            },
        },
        "document": {
            "type": "object", "additionalProperties": False,
            "properties": {
                "text": {"type": "string"},
                "base64": {"type": "string"},
                "url": {"type": "string", "format": "uri"},
                "none": {"const": True},
                "origin": {"type": "string", "format": "uri"},
                "base": {"type": "string", "format": "uri"},
            },
            "oneOf": [{"required": [field]} for field in ("text", "base64", "url", "none")],
        },
    },
}


def _example_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise FederationError("invalid_package", f"Duplicate example key: {key}")
            result[key] = value
        return result

    def bad_number(value):
        raise FederationError("invalid_package", f"Non-finite example number: {value}")

    def number(value):
        result = float(value)
        return result if math.isfinite(result) else bad_number(value)

    try:
        value = json.loads(
            data.decode("utf-8"), object_pairs_hook=pairs,
            parse_constant=bad_number, parse_float=number,
        )
        json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
        return value
    except (UnicodeError, ValueError) as error:
        if isinstance(error, FederationError):
            raise
        raise FederationError("invalid_package", f"Invalid example JSON: {error}") from error
    except RecursionError as error:
        raise FederationError("limit_exceeded", "Example JSON nesting limit") from error


def example_documents(example):
    """Decode captured payloads without reserializing domain JSON or adding LF."""
    documents = {}
    for xid, value in example["documents"].items():
        try:
            if "text" in value:
                documents[xid] = value["text"].encode("utf-8")
            elif "base64" in value:
                data = base64.b64decode(value["base64"], validate=True)
                if base64.b64encode(data).decode("ascii") != value["base64"]:
                    raise ValueError("Noncanonical Base64")
                documents[xid] = data
        except (UnicodeError, binascii.Error, ValueError) as error:
            raise FederationError("invalid_package", f"Invalid document bytes at {xid}") from error
    return documents


def validate_example_source(value):
    """Check source structure and identity; binding adapters check their contracts."""
    from jsonschema import Draft202012Validator, FormatChecker

    try:
        error = next(Draft202012Validator(
            EXAMPLE_SCHEMA, format_checker=FormatChecker(),
        ).iter_errors(value), None)
    except RecursionError as error:
        raise FederationError("limit_exceeded", "Example schema nesting limit") from error
    if error is not None:
        location = "/".join(str(p) for p in error.absolute_path)
        raise FederationError("invalid_package", f"Example schema at /{location}: {error.message}")
    for name, example in value["examples"].items():
        seen, versions, roots = set(), set(), []
        for record in example["records"]:
            xid, kind = record["entity"]["xid"], record["kind"]
            parts = xid_parts(xid)
            expected = (
                "registry" if not parts else "group" if len(parts) == 2 else
                "resource" if len(parts) == 4 else "meta" if len(parts) == 5 else "version"
            )
            key = canonical_xid(xid)
            if kind != expected or key in seen:
                raise FederationError("invalid_package", f"Duplicate or mistyped entity in {name}: {xid}")
            seen.add(key)
            if kind == "registry":
                roots.append(record["entity"])
            if kind == "version":
                versions.add(xid)
        if len(roots) != 1 or any(
            not isinstance(roots[0].get(field), dict)
            for field in ("modelsource", "model", "capabilities")
        ):
            raise FederationError("invalid_package", f"{name} needs one Registry with model and capabilities")
        if set(example["documents"]) != versions:
            raise FederationError("invalid_package", f"{name} document states must match its Version XIDs")
        for xid, document in example["documents"].items():
            if "url" in document:
                _absolute_uri(document["url"])
                if example["snapshot"] == "offline-complete":
                    raise FederationError("invalid_package", "Offline-complete example has external content")
            if ("url" in document or "none" in document) and document.keys() & {"origin", "base"}:
                raise FederationError("invalid_package", f"Only captured documents carry origin/base: {xid}")
        example_documents(example)
    return value["examples"]


def load_examples(path=None):
    """Load fresh source values; never keep shared mutable fixture state."""
    source = EXAMPLE_SOURCE if path is None else Path(path)
    try:
        with source.open("rb") as stream:
            data = stream.read(MAX_EXAMPLE_BYTES + 1)
    except OSError as error:
        raise FederationError("unavailable", f"Cannot read example source: {error}") from error
    if len(data) > MAX_EXAMPLE_BYTES:
        raise FederationError("limit_exceeded", "Example source byte limit")
    return validate_example_source(_example_json(data))


def load_example(name, path=None):
    examples = load_examples(path)
    if name not in examples:
        raise FederationError("not_found", f"Unknown example: {name}")
    return copy.deepcopy(examples[name])


_ID = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.~:@-]{0,127}\Z")
_PROFILE_PARAMETERS = {
    "http": set(),
    "oci": {"reference"},
    "git": {"revision", "path"},
    "file": {"layout", "reference"},
    "opcua": {"registryroot", "applicationuri", "transportprofileuri"},
}


def xid_parts(value, *, collection=False):
    """Decode a typed Core URI exactly once; model names remain caller-checked."""
    if not isinstance(value, str) or not value.startswith("/"):
        raise FederationError("invalid_package", "XID must start with /")
    if value == "/" and not collection:
        return ()
    encoded = value[1:].split("/")
    if any(len(part) > 384 or re.search(r"%(?![0-9a-fA-F]{2})", part) for part in encoded):
        raise FederationError("invalid_package", "Invalid XID component")
    try:
        parts = [unquote_to_bytes(part).decode("utf-8", errors="strict") for part in encoded]
    except UnicodeError as error:
        raise FederationError("invalid_package", "Invalid XID component") from error
    if not all(_ID.fullmatch(part) for part in parts):
        raise FederationError("invalid_package", "Invalid XID component")
    valid = (
        len(parts) in (1, 3) or len(parts) == 5 and parts[4] == "versions"
        if collection
        else len(parts) in (2, 4)
        or len(parts) == 5 and parts[4] == "meta"
        or len(parts) == 6 and parts[4] == "versions"
    )
    if not valid:
        raise FederationError("invalid_package", "Invalid XID hierarchy")
    return tuple(parts)


def validate_xid(value, *, collection=False):
    """Validate syntax while retaining the original serialized URI spelling."""
    xid_parts(value, collection=collection)
    return value


def canonical_xid(value, *, collection=False):
    """A comparison/routing key, not permission to rewrite stored metadata."""
    return "/" + "/".join(quote(part, safe="-._~") for part in xid_parts(value, collection=collection))


def same_xid(left, right, *, collection=False):
    return xid_parts(left, collection=collection) == xid_parts(right, collection=collection)


def _absolute_uri(value):
    if (
        not isinstance(value, str)
        or not value.isascii()
        or any(c.isspace() or ord(c) < 32 or ord(c) == 127 or c in '\\<>"{}|^`' for c in value)
        or re.search(r"%(?![0-9a-fA-F]{2})", value)
    ):
        raise FederationError("invalid_package", "Endpoint must be a URI")
    try:
        uri = urlsplit(value)
        uri.port
    except ValueError as error:
        raise FederationError("invalid_package", "Malformed endpoint") from error
    if not uri.scheme:
        raise FederationError("invalid_package", "Endpoint must be absolute")
    if uri.username is not None or uri.password is not None:
        raise FederationError("policy_denied", "Embedded credentials prohibited")
    return uri


def _unsigned_integer(value):
    if type(value) is int:
        return value >= 0
    if type(value) is float:
        return math.isfinite(value) and value >= 0 and value.is_integer()
    if type(value) is Decimal:
        return value.is_finite() and value >= 0 and value == value.to_integral_value()
    return False


def validate_profile(profile):
    if not isinstance(profile, dict):
        raise FederationError("invalid_package", "Advertisement must be an object")
    if profile.keys() - {"name", "endpoint", "priority", "parameters"}:
        raise FederationError("invalid_package", "Unknown advertisement field")
    name = profile.get("name")
    if not isinstance(name, str) or not name:
        raise FederationError("invalid_package", "Missing profile name")
    uri = _absolute_uri(profile.get("endpoint"))
    priority = profile.get("priority", 0)
    if not _unsigned_integer(priority):
        raise FederationError("invalid_package", "Priority must be unsigned integer")
    parameters = profile.get("parameters", {})
    if not isinstance(parameters, dict):
        raise FederationError("invalid_package", "Parameters must be an object")
    if name not in _PROFILE_PARAMETERS:
        return
    if parameters.keys() - _PROFILE_PARAMETERS[name]:
        raise FederationError("unsupported_operation", "Unknown profile parameter")
    if "#" in profile["endpoint"] or "?" in profile["endpoint"]:
        raise FederationError("invalid_package", "Endpoint has query or fragment")
    if name in ("http", "git", "oci", "opcua") and not uri.hostname:
        raise FederationError("invalid_package", "Missing endpoint host")
    if name == "http" and uri.scheme not in ("http", "https"):
        raise FederationError("invalid_package", "HTTP endpoint scheme")
    if name == "git":
        if uri.scheme != "https":
            raise FederationError("unsupported_operation", "Git transport not HTTPS")
        revision = parameters.get("revision", "")
        if not isinstance(revision, str) or not (
            re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", revision)
            or revision.startswith("refs/")
            and not re.search(r"[\x00-\x20\x7f~^:?*\[\\]|\.\.|@\{|//", revision)
            and all(
                part and not part.startswith(".")
                and not part.endswith((".", ".lock"))
                for part in revision.split("/")
            )
        ):
            raise FederationError("invalid_package", "Git revision is not pinned input")
        path = parameters.get("path", "xregistry")
        if not isinstance(path, str) or (
            path and any(
                not part or part in (".", "..") or "\\" in part or ":" in part
                for part in path.split("/")
            )
        ):
            raise FederationError("policy_denied", "Unsafe Git format root")
    if name == "oci":
        if uri.scheme != "oci" or not re.fullmatch(
            r"/[a-z0-9]+(?:(?:[._]|__|-+)[a-z0-9]+)*"
            r"(?:/[a-z0-9]+(?:(?:[._]|__|-+)[a-z0-9]+)*)*",
            uri.path,
        ):
            raise FederationError("invalid_package", "OCI repository locator")
    if name == "oci" or name == "file" and parameters.get("layout") == "oci-layout":
        reference = parameters.get("reference")
        if not isinstance(reference, str) or not re.fullmatch(
            r"sha256:[0-9a-f]{64}|[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}", reference
        ):
            raise FederationError("invalid_package", "Missing or invalid OCI reference")
    if name == "file":
        if uri.scheme != "file" or not uri.path.startswith("/"):
            raise FederationError("invalid_package", "File endpoint must be absolute")
        if uri.hostname not in (None, "", "localhost"):
            raise FederationError("policy_denied", "Non-local file authority")
        if parameters.get("layout") not in ("document-tree", "oci-layout"):
            raise FederationError("invalid_package", "Unknown file layout")
        if parameters["layout"] == "document-tree" and "reference" in parameters:
            raise FederationError("unsupported_operation", "Document tree has no tag")
    if name == "opcua":
        if uri.scheme not in ("opc.tcp", "https", "opc.wss"):
            raise FederationError("unsupported_operation", "Unsupported UA transport")
        from workingdrafts.bindings.tools.opcua_examples import validate_registry_root

        validate_registry_root(parameters.get("registryroot"))
        for parameter in ("applicationuri", "transportprofileuri"):
            if parameter in parameters:
                _absolute_uri(parameters[parameter])


def select_profile(entry, supported, *, name=None):
    """Choose once. Validation failures never trigger a weaker fallback."""
    if not isinstance(entry, dict):
        raise FederationError("invalid_package", "Catalog entry must be an object")
    candidates = entry.get("federationprofiles", [])
    if not isinstance(candidates, list):
        raise FederationError("invalid_package", "Profiles must be an array")
    if any(not isinstance(item, dict) for item in candidates):
        raise FederationError("invalid_package", "Advertisement must be an object")
    if any(
        not isinstance(item.get("name"), str) or not item["name"]
        for item in candidates
    ):
        raise FederationError("invalid_package", "Missing profile name")
    candidates = list(candidates)
    xregurl = entry.get("xregurl")
    explicit_http = [p for p in candidates if p.get("name") == "http"]
    if xregurl is not None:
        validate_profile({"name": "http", "endpoint": xregurl})
        if explicit_http and not any(p.get("endpoint") == xregurl for p in explicit_http):
            raise FederationError("invalid_package", "Conflicting xregurl")
        candidates.append({"name": "http", "endpoint": xregurl})
    eligible = [
        p for p in candidates
        if p.get("name") in supported and (name is None or p.get("name") == name)
    ]
    if not eligible:
        raise FederationError("unsupported_binding", "No supported advertisement")
    for profile in eligible:
        priority = profile.get("priority", 0)
        if not _unsigned_integer(priority):
            raise FederationError("invalid_package", "Invalid candidate priority")
    selected = min(eligible, key=lambda p: p.get("priority", 0))
    validate_profile(selected)
    return selected


def execute_selected(entry, supported, read, *, name=None):
    """Exercise one selected read. Failures propagate without another candidate."""
    return read(select_profile(entry, supported, name=name))


def select_label(entities, key, value):
    """Fixture comparator: Unicode case folding, without normalization."""
    if not isinstance(key, str) or not isinstance(value, str):
        raise FederationError("invalid_package", "Selector requires string key/value")
    matches = []
    for entity in entities:
        if not isinstance(entity, dict):
            raise FederationError("invalid_package", "Collection member must be an object")
        labels = entity.get("labels", {})
        if not isinstance(labels, dict) or any(
            not isinstance(k, str) or not isinstance(v, str)
            for k, v in labels.items()
        ):
            raise FederationError("invalid_package", "Invalid label map")
        if key in labels and labels[key].casefold() == value.casefold():
            matches.append(entity)
    if not matches:
        raise FederationError("not_found", "No label match")
    if len(matches) > 1:
        raise FederationError("ambiguous", "Multiple label matches")
    return matches[0]


def resource_type(modelsource, xid):
    parts = xid_parts(xid)
    if len(parts) != 4:
        raise FederationError("invalid_package", "Reference must name a Resource")

    def origin(group_name, resource_name, visited):
        pair = (group_name, resource_name)
        if pair in visited:
            raise FederationError("invalid_package", "Circular Resource type import")
        group = modelsource.get("groups", {}).get(group_name)
        if group is None:
            raise FederationError("invalid_package", "Unknown Group type")
        if resource_name in group.get("resources", {}):
            return pair
        for imported in group.get("ximportresources", []):
            segments = imported.strip("/").split("/")
            if len(segments) == 2 and segments[1] == resource_name:
                return origin(*segments, visited | {pair})
        raise FederationError("invalid_package", "Unknown Resource type")

    return origin(parts[0], parts[2], set())


def resolve_local_xref(registry, source_xid):
    """Return a one-hop target or None for Core's non-expanded alias cases."""
    modelsource = registry.get("modelsource")
    if not isinstance(modelsource, dict):
        raise FederationError("invalid_package", "Missing Resource type provenance")
    source_type = resource_type(modelsource, source_xid)

    def lookup(xid):
        group_type, group_id, resource_name, resource_id = xid[1:].split("/")
        return (
            registry.get(group_type, {}).get(group_id, {})
            .get(resource_name, {}).get(resource_id)
        )

    source = lookup(source_xid)
    if source is None:
        raise FederationError("not_found", "Source Resource does not exist")
    target_xid = source.get("meta", {}).get("xref")
    if target_xid is None:
        return source
    if resource_type(modelsource, target_xid) != source_type:
        raise FederationError("invalid_package", "xref Resource type mismatch")
    target = lookup(target_xid)
    if target is None or "xref" in target.get("meta", {}):
        return None
    return target


def select_version(resource, versionid=None):
    if not isinstance(resource, dict):
        raise FederationError("invalid_package", "Resource must be an object")
    meta = resource.get("meta", {})
    versions = resource.get("versions", {})
    if not isinstance(meta, dict) or not isinstance(versions, dict):
        raise FederationError("invalid_package", "Meta and Versions must be objects")
    if "xref" in meta:
        raise FederationError("unsupported_operation", "cannot_doc_xref")
    selected = versionid if versionid is not None else meta.get("defaultversionid")
    if not isinstance(selected, str) or not _ID.fullmatch(selected):
        raise FederationError("invalid_package", "Invalid default or explicit Version ID")
    try:
        result = versions[selected]
    except KeyError as error:
        raise FederationError("not_found", "Selected Version does not exist") from error
    if not isinstance(result, dict):
        raise FederationError("invalid_package", "Version must be an object")
    return result
