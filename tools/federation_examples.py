"""Offline examples of federation selection, not a network resolver."""

import re
from urllib.parse import urlsplit


class FederationError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


_ID = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.~:@-]{0,127}\Z")
_PROFILE_PARAMETERS = {
    "http": set(),
    "oci": {"reference"},
    "git": {"revision", "path"},
    "file": {"layout", "reference"},
    "opcua": {"registryroot", "applicationuri", "transportprofileuri"},
}


def validate_xid(value, *, collection=False):
    """Validate syntax. Callers also validate collection names against a model."""
    if not isinstance(value, str) or not value.startswith("/"):
        raise FederationError("invalid_package", "XID must start with /")
    if value == "/" and not collection:
        return value
    parts = value[1:].split("/")
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
    return value


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
    if type(priority) is not int or priority < 0:
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
        from opcua_examples import validate_registry_root

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
        if type(priority) is not int or priority < 0:
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
    validate_xid(xid)
    parts = xid[1:].split("/")
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
