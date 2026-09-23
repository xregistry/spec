"""Offline OPC UA reference mapping and normalized read-transcript examples.

No SDK, discovery, connection, certificate validation or network I/O is used.
The JSON transcript notation is documented beside the fixtures.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
from uuid import UUID

from workingdrafts.federation.tools.federation_examples import (
    FederationError, validate_profile, validate_xid,
)


UA_NAMESPACE = "http://opcfoundation.org/UA/"
FIXTURE_FORMAT = "xregistry-opcua-examples-v1"
UINT16_MAX = (1 << 16) - 1
UINT32_MAX = (1 << 32) - 1
UINT64_MAX = (1 << 64) - 1
INT32_MAX = (1 << 31) - 1
_ID_TYPES = {"i": "Numeric", "s": "String", "g": "Guid", "b": "Opaque"}
_URI_SAFE = ":/?#[]@!$&'()*+,-._~="


def _object(value, name):
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise FederationError("invalid_package", f"{name} must be an object")
    return value


def _fields(value, required, optional=(), *, name="object"):
    value = _object(value, name)
    missing = set(required) - value.keys()
    extra = value.keys() - set(required) - set(optional)
    if missing or extra:
        raise FederationError(
            "invalid_package",
            f"{name}: missing fields {sorted(missing)}, unknown fields {sorted(extra)}",
        )
    return value


def _uint(value, maximum, name):
    if type(value) is not int or not 0 <= value <= maximum:
        raise FederationError("invalid_package", f"{name} is out of range")
    return value


def _text(value, name, *, empty=False):
    if not isinstance(value, str) or (not empty and not value):
        raise FederationError("invalid_package", f"{name} must be a string")
    if any(unicodedata.category(character) in ("Cc", "Cs") for character in value):
        raise FederationError("invalid_package", f"{name} contains a control character")
    return value


def _uri(value, name):
    value = _text(value, name)
    if (
        not value.isascii()
        or any(character.isspace() or character in '\\<>"{}|^`' for character in value)
        or re.search(r"%(?![0-9A-Fa-f]{2})", value)
        or not re.match(r"[A-Za-z][A-Za-z0-9+.-]*:", value)
    ):
        raise FederationError("invalid_package", f"{name} is not an absolute URI")
    try:
        parsed = urlsplit(value)
        parsed.port
    except ValueError as error:
        raise FederationError("invalid_package", f"Malformed {name}") from error
    if parsed.username is not None or parsed.password is not None:
        raise FederationError("policy_denied", f"Credentials are prohibited in {name}")
    return value


def _decode_uri(value):
    if re.search(r"%(?![0-9A-Fa-f]{2})", value):
        raise FederationError("invalid_package", "Invalid URI percent encoding")
    try:
        return _uri(unquote(value, errors="strict"), "Namespace URI")
    except UnicodeDecodeError as error:
        raise FederationError("invalid_package", "Invalid encoded URI") from error


def _base64(value, name):
    _text(value, name, empty=True)
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as error:
        raise FederationError("invalid_package", f"Invalid {name} Base64") from error
    if base64.b64encode(decoded).decode("ascii") != value:
        raise FederationError("invalid_package", f"Noncanonical {name} Base64")
    return decoded


def _json_text(value):
    try:
        return json.dumps(value, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise FederationError("invalid_package", "Value is not finite JSON data") from error


def _table(values, name, maximum):
    if not isinstance(values, list) or not 0 < len(values) <= maximum:
        raise FederationError("invalid_package", f"Missing or oversized {name}")
    result = [_uri(value, name) for value in values]
    if len(set(result)) != len(result):
        raise FederationError("invalid_package", f"Duplicate URI in {name}")
    return result


def validate_namespace_array(values: object) -> list[str]:
    """Validate the fixture's complete, ordered namespace table."""
    result = _table(values, "NamespaceArray", UINT16_MAX + 1)
    if result[0] != UA_NAMESPACE:
        raise FederationError("invalid_package", "NamespaceArray[0] is not namespace zero")
    return result


def validate_server_array(values: object) -> list[str]:
    """Validate the source ServerArray; element zero identifies the source."""
    return _table(values, "ServerArray", UINT32_MAX + 1)


def _identifier(kind, value):
    if kind == "Numeric":
        return _uint(value, UINT32_MAX, "Numeric identifier")
    if kind == "String":
        value = _text(value, "String identifier", empty=True)
        if len(value) > 4096:
            raise FederationError("invalid_package", "String identifier exceeds 4096 characters")
        return value
    if kind == "Guid":
        if not isinstance(value, str) or not re.fullmatch(
            r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", value
        ):
            raise FederationError("invalid_package", "Invalid Guid identifier")
        return str(UUID(value))
    if kind == "Opaque":
        if len(_base64(value, "Opaque identifier")) > 4096:
            raise FederationError("invalid_package", "Opaque identifier exceeds 4096 bytes")
        return value
    raise FederationError("invalid_package", "Unknown identifierType")


@dataclass(frozen=True)
class NodeId:
    namespace_uri: str
    identifier_type: str
    identifier: int | str

    def __post_init__(self):
        _uri(self.namespace_uri, "Namespace URI")
        object.__setattr__(
            self, "identifier", _identifier(self.identifier_type, self.identifier)
        )

    def portable(self) -> str:
        prefix = ""
        if self.namespace_uri != UA_NAMESPACE:
            prefix = "nsu=" + quote(self.namespace_uri, safe=_URI_SAFE) + ";"
        return prefix + _identifier_text(self)


def _identifier_text(node):
    prefix = next(key for key, value in _ID_TYPES.items() if value == node.identifier_type)
    return f"{prefix}={node.identifier}"


def _is_null(node):
    if node.namespace_uri != UA_NAMESPACE:
        return False
    if node.identifier_type == "Numeric":
        return node.identifier == 0
    if node.identifier_type == "Guid":
        return node.identifier == "00000000-0000-0000-0000-000000000000"
    return node.identifier == ""


def _parse_identifier(text, namespace_uri):
    if len(text) < 2 or text[1] != "=" or text[0] not in _ID_TYPES:
        raise FederationError("invalid_package", "Missing NodeId identifier")
    value = text[2:]
    kind = _ID_TYPES[text[0]]
    if kind == "Numeric":
        if not re.fullmatch(r"[0-9]+", value):
            raise FederationError("invalid_package", "Invalid Numeric identifier")
        significant = value.lstrip("0") or "0"
        if len(significant) > 10:
            raise FederationError("invalid_package", "Numeric identifier is out of range")
        value = int(significant)
    return NodeId(namespace_uri, kind, value)


def parse_nodeid(value: str) -> NodeId:
    """Parse a portable NodeId, never a context-free ns=/svr=/svu= address."""
    value = _text(value, "NodeId")
    namespace_uri = UA_NAMESPACE
    if value.startswith("nsu="):
        uri, separator, value = value[4:].partition(";")
        if not separator:
            raise FederationError("invalid_package", "Missing namespace separator")
        namespace_uri = _decode_uri(uri)
        if namespace_uri == UA_NAMESPACE:
            raise FederationError("invalid_package", "Namespace zero uses identifier-only form")
    return _parse_identifier(value, namespace_uri)


def validate_registry_root(value: str) -> NodeId:
    """Validate a portable, non-null NodeId advertised as a Registry root."""
    node = parse_nodeid(value)
    if _is_null(node):
        raise FederationError("invalid_package", "Null NodeId is not a Registry root")
    return node


def _nodeid_in_session(value, namespace_array):
    value = _text(value, "NodeId")
    if not value.startswith("ns="):
        return parse_nodeid(value)
    index, separator, identifier = value[3:].partition(";")
    if not separator or not re.fullmatch(r"[0-9]+", index) or len(index) > 5:
        raise FederationError("invalid_package", "Invalid namespace index")
    index = _uint(int(index), UINT16_MAX, "namespaceIndex")
    if index == 0:
        raise FederationError("invalid_package", "Namespace zero uses identifier-only form")
    if namespace_array is None or index >= len(namespace_array):
        raise FederationError("invalid_package", "NodeId lacks its namespace-table context")
    return _parse_identifier(identifier, namespace_array[index])


def _mapped_nodeid(node, namespace_array):
    if _is_null(node):
        raise FederationError("invalid_package", "Null NodeId does not identify a target")
    try:
        index = namespace_array.index(node.namespace_uri)
    except ValueError as error:
        raise FederationError("not_found", "Target namespace URI is absent") from error
    prefix = f"ns={index};" if index else ""
    return prefix + _identifier_text(node)


def map_registry_root(
    profile: dict, endpoint_description: dict, namespace_array: list
) -> dict:
    """Map an advertisement against one already selected endpoint description.

    Exact endpoint matching is a fixture policy. This function does not
    discover endpoints, inspect certificates or certify a RegistryType node.
    """
    validate_profile(profile)
    if profile["name"] != "opcua":
        raise FederationError("unsupported_binding", "Not an OPC UA advertisement")
    endpoint = _object(endpoint_description, "EndpointDescription")
    server = _object(endpoint.get("server"), "EndpointDescription.server")
    endpoint_url = _uri(endpoint.get("endpointUrl"), "Endpoint URL")
    application_uri = _uri(server.get("applicationUri"), "Application URI")
    transport_uri = _uri(endpoint.get("transportProfileUri"), "Transport profile URI")
    if endpoint_url != profile["endpoint"]:
        raise FederationError("policy_denied", "Endpoint differs from the selected advertisement")
    parameters = profile.get("parameters", {})
    if parameters.get("applicationuri", application_uri) != application_uri:
        raise FederationError("integrity_error", "Application identity mismatch")
    if parameters.get("transportprofileuri", transport_uri) != transport_uri:
        raise FederationError("unsupported_binding", "Transport profile mismatch")
    root = validate_registry_root(parameters.get("registryroot"))
    namespaces = validate_namespace_array(namespace_array)
    return {
        "endpoint": endpoint_url,
        "applicationuri": application_uri,
        "transportprofileuri": transport_uri,
        "registryroot": root.portable(),
        "nodeId": _mapped_nodeid(root, namespaces),
    }


def map_expanded_nodeid(
    reference: dict,
    source_server_array: list,
    source_namespace_array: list | None,
    target_applicationuri: str,
    target_namespace_array: list,
) -> dict:
    """Resolve source table indexes, then map the URI in the target table."""
    reference = _fields(
        reference,
        ("serverIndex", "namespaceIndex", "identifierType", "identifier"),
        ("namespaceUri",),
        name="ExpandedNodeId",
    )
    servers = validate_server_array(source_server_array)
    source_namespaces = (
        validate_namespace_array(source_namespace_array)
        if source_namespace_array is not None else None
    )
    target_namespaces = validate_namespace_array(target_namespace_array)
    server_index = _uint(reference["serverIndex"], UINT32_MAX, "serverIndex")
    namespace_index = _uint(reference["namespaceIndex"], UINT16_MAX, "namespaceIndex")
    if server_index >= len(servers):
        raise FederationError("invalid_package", "serverIndex is outside the source ServerArray")
    application_uri = servers[server_index]
    if _uri(target_applicationuri, "Target Application URI") != application_uri:
        raise FederationError("integrity_error", "Target application does not match ServerArray")
    namespace_uri = reference.get("namespaceUri")
    if namespace_uri is None or namespace_uri == "":
        if source_namespaces is None or namespace_index >= len(source_namespaces):
            raise FederationError("invalid_package", "namespaceIndex is outside its source table")
        namespace_uri = source_namespaces[namespace_index]
    else:
        namespace_uri = _uri(namespace_uri, "Namespace URI")
        if namespace_index != 0:
            raise FederationError("invalid_package", "namespaceIndex must be zero with namespaceUri")
    kind = reference["identifierType"]
    node = NodeId(namespace_uri, kind, reference["identifier"])
    return {
        "applicationuri": application_uri,
        "namespaceUri": namespace_uri,
        "nodeId": _mapped_nodeid(node, target_namespaces),
        "portable": "svu=" + quote(application_uri, safe=_URI_SAFE) + ";" + node.portable(),
        "local": server_index == 0,
    }


def map_status(status: str) -> str | None:
    """Map normalized symbolic statuses; only exact Good denotes success."""
    _text(status, "StatusCode")
    if status == "Good":
        return None
    groups = {
        "unsupported_operation": {"Bad_NotSupported", "Bad_MethodInvalid"},
        "not_found": {"Bad_NodeIdUnknown", "Bad_NotFound"},
        "policy_denied": {
            "Bad_UserAccessDenied", "Bad_SecurityChecksFailed",
            "Bad_CertificateUntrusted", "Bad_IdentityTokenRejected",
        },
        "invalid_package": {
            "Bad_InvalidArgument", "Bad_TypeMismatch", "Bad_OutOfRange",
            "Bad_NodeIdInvalid", "Bad_BrowseNameInvalid",
        },
        "inconsistent_snapshot": {"Bad_ContinuationPointInvalid"},
        "limit_exceeded": {
            "Bad_TooManyOperations", "Bad_EncodingLimitsExceeded",
            "Bad_ResponseTooLarge", "Bad_OutOfMemory",
        },
    }
    for code, statuses in groups.items():
        if status in statuses:
            return code
    if status.startswith(("Bad_", "Uncertain_", "Good_")) or status == "Uncertain":
        return "unavailable"
    raise FederationError("invalid_package", "Unknown StatusCode notation")


def _check_status(event):
    for status in (event.get("serviceStatus", "Good"), event.get("status")):
        code = map_status(status)
        if code:
            raise FederationError(code, f"{event.get('method', event.get('service'))}: {status}")


def _observations(sequence):
    before = sequence.get("before")
    after = sequence.get("after")
    if "before" not in sequence and "after" not in sequence:
        return "unverified"
    for value in (before, after):
        _fields(value, (), ("size", "epoch", "versionid", "defaultversionid"),
                name="capture observations")
        if not value:
            raise FederationError("invalid_package", "Empty capture observations")
        for key, item in value.items():
            if key in ("size", "epoch"):
                _uint(item, UINT64_MAX if key == "size" else UINT32_MAX, key)
            else:
                _text(item, key)
                validate_xid("/groups/g/resources/r/versions/" + item)
    if before != after:
        raise FederationError("inconsistent_snapshot", "Capture observations changed")
    return "observed"


def _request(sequence):
    request = sequence.get("request")
    if request is None:
        if "request" in sequence or "selectedXid" in sequence:
            raise FederationError("invalid_package", "Missing document request context")
        return None
    request = _fields(request, ("operation", "target"), name="read request")
    operation, target = request["operation"], request["target"]
    if operation not in ("entity", "collection", "document", "model", "capabilities"):
        raise FederationError("unsupported_operation", "Unknown read operation")
    validate_xid(target, collection=operation == "collection")
    if operation in ("model", "capabilities") and target != "/":
        raise FederationError("invalid_package", "Model/capabilities target must be /")
    if operation in ("model", "capabilities") and sequence["kind"] not in ("metadata", "file"):
        raise FederationError("invalid_package", "Model/capabilities require mapped reads")
    if operation == "collection" and sequence["kind"] != "browse":
        raise FederationError("invalid_package", "Collection requires a Browse sequence")
    if operation == "entity" and sequence["kind"] != "metadata":
        raise FederationError("invalid_package", "Entity requires metadata reads")
    if operation != "document":
        return None
    if sequence["kind"] != "file":
        raise FederationError("invalid_package", "Document requires a file sequence")
    parts = target[1:].split("/")
    if len(parts) not in (4, 6):
        raise FederationError("unsupported_operation", "Document target is not a Resource/Version")
    selected = sequence.get("selectedXid")
    if selected is None:
        raise FederationError("invalid_package", "Missing selected Version XID observation")
    validate_xid(selected)
    expected = target
    if len(parts) == 4:
        default = _object(sequence.get("before", {}), "default selection").get("defaultversionid")
        if not isinstance(default, str) or not default:
            raise FederationError("unsupported_operation", "No readable default-Version mapping")
        expected += "/versions/" + default
        validate_xid(expected)
    if selected != expected:
        raise FederationError("integrity_error", "Selected Version does not match requested Version")
    before = _object(sequence.get("before", {}), "Version observation")
    if "versionid" in before and before["versionid"] != selected.rsplit("/", 1)[1]:
        raise FederationError("integrity_error", "VersionId Property differs from selected XID")
    return selected


def _contexts(events, namespace_array):
    context = None
    for event in events:
        event = _object(event, "event")
        service = _text(event.get("service"), "Service")
        members = {
            "Read": ("values",),
            "Browse": ("input", "output"),
            "BrowseNext": ("input", "output"),
            "Call": ("method", "input", "output"),
        }
        if service not in members:
            raise FederationError("unsupported_operation", "Unsupported read Service")
        _fields(
            event, ("service", "session", "nodeId", "status"),
            ("serviceStatus",) + members[service], name="event",
        )
        session = _text(event.get("session"), "Session")
        node = _nodeid_in_session(event.get("nodeId"), namespace_array)
        if _is_null(node):
            raise FederationError("invalid_package", "Null NodeId does not identify an Object")
        if namespace_array is not None:
            _mapped_nodeid(node, namespace_array)
        current = (session, node)
        if context is not None and context != current:
            raise FederationError("invalid_package", "Sequence changed its Session or Object")
        context = current


def _metadata_sequence(events):
    values, trace = {}, []
    for event in events:
        if event.get("service") != "Read":
            raise FederationError("unsupported_operation", "Metadata uses the Read Service")
        _check_status(event)
        for name, result in _object(event.get("values"), "Read values").items():
            _text(name, "Property name")
            result = _fields(result, ("status", "value"), name="DataValue")
            code = map_status(result["status"])
            if code:
                raise FederationError(code, f"Read {name}: {result['status']}")
            current = _json_text(result["value"])
            if name in values and _json_text(values[name]) != current:
                raise FederationError("inconsistent_snapshot", f"Property {name} changed")
            values[name] = result["value"]
        trace.append("Read")
    if not values:
        raise FederationError("inconsistent_snapshot", "No metadata values were read")
    return {"values": values, "trace": trace}


def _browse_sequence(events, max_references):
    references, trace, continuation = [], [], None
    maximum = 0
    for index, event in enumerate(events):
        expected = "Browse" if index == 0 else "BrowseNext"
        if event.get("service") != expected:
            raise FederationError("invalid_package", f"Expected {expected}")
        arguments = _object(event.get("input", {}), "Browse input")
        if index:
            _fields(arguments, ("continuationPoints", "releaseContinuationPoints"),
                    name="BrowseNext input")
            if continuation is None:
                raise FederationError("invalid_package", "BrowseNext after complete Browse")
            if arguments.get("continuationPoints") != [continuation]:
                raise FederationError("invalid_package", "Wrong continuation point")
            if type(arguments.get("releaseContinuationPoints")) is not bool:
                raise FederationError("invalid_package", "Missing continuation release choice")
            if arguments["releaseContinuationPoints"]:
                _check_status(event)
                raise FederationError("inconsistent_snapshot", "Browse was released before completion")
        else:
            _fields(arguments, (), ("requestedMaxReferencesPerNode",), name="Browse input")
            maximum = _uint(
                arguments.get("requestedMaxReferencesPerNode", 0),
                UINT32_MAX, "requestedMaxReferencesPerNode",
            )
        _check_status(event)
        output = _fields(event.get("output"), ("references", "continuationPoint"),
                         name="Browse result")
        if not isinstance(output["references"], list):
            raise FederationError("invalid_package", "References must be an array")
        if maximum and len(output["references"]) > maximum:
            raise FederationError("invalid_package", "Browse returned more than requested")
        for reference in output["references"]:
            _object(reference, "Browse reference")
        if len(references) + len(output["references"]) > max_references:
            raise FederationError("limit_exceeded", "Browse reference budget exceeded")
        references.extend(output["references"])
        continuation = output["continuationPoint"]
        if continuation not in (None, ""):
            _base64(continuation, "continuationPoint")
        else:
            continuation = None
        trace.append(expected)
    if continuation is not None:
        raise FederationError("inconsistent_snapshot", "Missing BrowseNext response")
    return {"references": references, "complete": True, "trace": trace}


def _file_sequence(sequence, events, max_bytes):
    if type(sequence.get("hasdocument", True)) is not bool:
        raise FederationError("invalid_package", "hasdocument must be Boolean")
    if sequence.get("hasdocument") is False:
        raise FederationError("unsupported_operation", "Metadata-only Resource has no document")
    refresh = sequence.get("refresh", False)
    if type(refresh) is not bool or (refresh and sequence["kind"] != "namespace-file"):
        raise FederationError("invalid_package", "Refresh is only for NamespaceFile")
    handle, opened, closed, eof = None, False, False, False
    data, trace, primary, cleanup = bytearray(), [], None, None
    for index, event in enumerate(events):
        method = event.get("method")
        is_close = method == "Close"
        if primary is not None and (handle is None or not is_close):
            raise FederationError("invalid_package", "Only Close cleanup can follow a failed Call")
        try:
            if event.get("service") != "Call":
                raise FederationError("unsupported_operation", "File access requires Call")
            arguments = _object(event.get("input"), "Method input")
            if refresh and index == 0:
                if method != "ExportNamespace" or arguments:
                    raise FederationError("invalid_package", "Expected parameterless ExportNamespace")
                _check_status(event)
                if event.get("output", {}) != {}:
                    raise FederationError("invalid_package", "ExportNamespace has no document output")
                trace.append(method)
                continue
            if method == "Open":
                if opened or closed:
                    raise FederationError("invalid_package", "Repeated Open in one read")
                _fields(arguments, ("mode",), name="Open input")
                if type(arguments["mode"]) is not int or arguments["mode"] != 1:
                    raise FederationError("unsupported_operation", "Only Open(mode=1) is supported")
                _check_status(event)
                output = _fields(event.get("output"), ("fileHandle",), name="Open result")
                handle = _uint(output["fileHandle"], UINT32_MAX, "fileHandle")
                opened = True
            elif method in ("Read", "Close"):
                if handle is None or closed:
                    raise FederationError("invalid_package", "File handle is not open")
                keys = ("fileHandle", "length") if method == "Read" else ("fileHandle",)
                _fields(arguments, keys, name=f"{method} input")
                if _uint(arguments["fileHandle"], UINT32_MAX, "fileHandle") != handle:
                    raise FederationError("invalid_package", "File handle does not match Open")
                if method == "Read":
                    length = _uint(arguments["length"], INT32_MAX, "Read length")
                    if length == 0 or eof:
                        raise FederationError("invalid_package", "Read length is zero or EOF was reached")
                _check_status(event)
                if method == "Close":
                    if event.get("output", {}) != {}:
                        raise FederationError("invalid_package", "Close has no output arguments")
                    closed, handle = True, None
                else:
                    output = _fields(event.get("output"), ("data",), name="Read result")
                    encoded = _text(output["data"], "Read data", empty=True)
                    if len(encoded) > 4 * ((length + 2) // 3):
                        raise FederationError("invalid_package", "Read returned more than requested")
                    if len(encoded) > 4 * ((max_bytes - len(data) + 2) // 3):
                        raise FederationError("limit_exceeded", "Encoded chunk exceeds read budget")
                    chunk = _base64(encoded, "Read data")
                    if len(chunk) > length:
                        raise FederationError("invalid_package", "Read returned more than requested")
                    if len(data) + len(chunk) > max_bytes:
                        raise FederationError("limit_exceeded", "Document byte budget exceeded")
                    data.extend(chunk)
                    eof = not chunk
            else:
                raise FederationError("unsupported_operation", f"Unsupported read Method: {method}")
            trace.append(method)
        except FederationError as error:
            if primary is None:
                primary = error
            elif is_close:
                cleanup = error
            else:
                raise
    if primary is not None:
        detail = str(primary)
        if cleanup is not None:
            detail += f"; Close cleanup failed: {cleanup.code}: {cleanup}"
        elif opened and not closed:
            detail += "; handle cleanup was not confirmed"
        raise FederationError(primary.code, detail)
    if not opened or not closed or not eof:
        raise FederationError("inconsistent_snapshot", "Incomplete Open/Read/EOF/Close capture")
    expected_size = sequence.get("expectedSize")
    if "expectedSize" in sequence:
        _uint(expected_size, UINT64_MAX, "expectedSize")
        if len(data) != expected_size:
            raise FederationError("inconsistent_snapshot", "File size does not match captured bytes")
    for observation in ("before", "after"):
        values = sequence.get(observation, {})
        if isinstance(values, dict) and "size" in values and values["size"] != len(data):
            raise FederationError("inconsistent_snapshot", "Observed Size differs from captured bytes")
    return {
        "data": base64.b64encode(data).decode("ascii"),
        "size": len(data),
        "complete": True,
        "trace": trace,
    }


def interpret_read_sequence(
    sequence: dict,
    *,
    max_bytes: int = 1048576,
    max_events: int = 256,
    max_references: int = 4096,
    supported_specversions: tuple[str, ...] = ("1.0-rc4",),
) -> dict:
    """Interpret metadata, Browse or sequential FileType fixture observations.

    File sequences deliberately require observed EOF, even with known Size.
    Call errors are retained while the recorded Close cleanup is inspected.
    """
    sequence = _fields(
        sequence, ("kind", "events"),
        ("namespaceArray", "specversion", "request", "selectedXid", "before",
         "after", "expectedSize", "hasdocument", "refresh"),
        name="read sequence",
    )
    _uint(max_bytes, UINT64_MAX, "max_bytes")
    _uint(max_events, UINT32_MAX, "max_events")
    _uint(max_references, UINT32_MAX, "max_references")
    if sequence["kind"] not in ("metadata", "browse", "file", "namespace-file"):
        raise FederationError("unsupported_operation", "Unknown sequence kind")
    if not isinstance(supported_specversions, (tuple, list)) or not supported_specversions:
        raise FederationError("invalid_package", "Missing supported Core versions")
    for version in supported_specversions:
        _text(version, "Supported Core version")
    if "hasdocument" in sequence and (
        type(sequence["hasdocument"]) is not bool
        or sequence["kind"] not in ("metadata", "file")
    ):
        raise FederationError("invalid_package", "Invalid hasdocument observation")
    if "refresh" in sequence and sequence["kind"] != "namespace-file":
        raise FederationError("invalid_package", "Refresh is only for NamespaceFile")
    if "selectedXid" in sequence and sequence["kind"] != "file":
        raise FederationError("invalid_package", "Selected Version requires a document read")
    if "expectedSize" in sequence and sequence["kind"] not in ("file", "namespace-file"):
        raise FederationError("invalid_package", "expectedSize requires a file read")
    if "specversion" in sequence:
        _text(sequence["specversion"], "specversion")
        if sequence["specversion"] not in supported_specversions:
            raise FederationError("unsupported_version", "Unsupported Core SpecVersion")
    if sequence.get("hasdocument") is False and sequence["kind"] == "file":
        raise FederationError("unsupported_operation", "Metadata-only Resource has no document")
    selected_xid = _request(sequence)
    events = sequence["events"]
    if not isinstance(events, list):
        raise FederationError("invalid_package", "events must be an array")
    if len(events) > max_events:
        raise FederationError("limit_exceeded", "Event budget exceeded")
    if not events:
        raise FederationError("inconsistent_snapshot", "No completed read observations")
    namespaces = None
    if "namespaceArray" in sequence:
        namespaces = validate_namespace_array(sequence["namespaceArray"])
    _contexts(events, namespaces)
    if sequence["kind"] == "metadata":
        result = _metadata_sequence(events)
        if "SpecVersion" in result["values"]:
            version = _text(result["values"]["SpecVersion"], "SpecVersion Property")
            if version not in supported_specversions:
                raise FederationError("unsupported_version", "Unsupported read SpecVersion")
            if "specversion" in sequence and sequence["specversion"] != version:
                raise FederationError("inconsistent_snapshot", "SpecVersion observation changed")
    elif sequence["kind"] == "browse":
        result = _browse_sequence(events, max_references)
    else:
        result = _file_sequence(sequence, events, max_bytes)
    result["consistency"] = _observations(sequence)
    if selected_xid is not None:
        result["selectedXid"] = selected_xid
    return result


def _run_case(case):
    kind, arguments = case["kind"], _object(case["input"], "case input")
    if kind == "root":
        _fields(arguments, ("profile", "endpoint_description", "namespace_array"))
        return map_registry_root(**arguments)
    if kind == "reference":
        _fields(arguments, (
            "reference", "source_server_array", "source_namespace_array",
            "target_applicationuri", "target_namespace_array",
        ))
        return map_expanded_nodeid(**arguments)
    if kind == "sequence":
        _fields(arguments, ("sequence",), ("max_bytes", "max_events", "max_references"))
        return interpret_read_sequence(**arguments)
    raise FederationError("unsupported_operation", f"Unknown fixture case kind: {kind}")


def validate_fixture(document: dict) -> list[dict]:
    """Execute every named case, checking exact results or expected error codes."""
    document = _fields(document, ("format", "cases"), name="fixture")
    if document["format"] != FIXTURE_FORMAT:
        raise FederationError("unsupported_version", "Unsupported OPC UA fixture format")
    if not isinstance(document["cases"], list) or not document["cases"]:
        raise FederationError("invalid_package", "Fixture cases must be a nonempty array")
    names, results = set(), []
    for case in document["cases"]:
        _fields(case, ("name", "kind", "input"), ("expected", "error", "note"), name="case")
        name = _text(case["name"], "Case name")
        if name in names or ("expected" in case) == ("error" in case):
            raise FederationError("invalid_package", "Duplicate case or missing/dual expectation")
        names.add(name)
        try:
            actual = _run_case(case)
        except FederationError as error:
            if error.code != case.get("error"):
                raise FederationError(error.code, f"{name}: {error}") from error
            results.append({"name": name, "error": error.code})
            continue
        if "error" in case or _json_text(actual) != _json_text(case["expected"]):
            raise FederationError("invalid_package", f"{name}: result differs: {actual!r}")
        results.append({"name": name, "result": actual})
    return results


def _json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise FederationError("invalid_package", f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _json_constant(value):
    raise FederationError("invalid_package", f"Non-JSON number: {value}")


def _load(path):
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_json_object, parse_constant=_json_constant,
        )
    except FederationError:
        raise
    except ValueError as error:
        raise FederationError("invalid_package", f"{path}: {error}") from error
    except OSError as error:
        raise FederationError("unavailable", f"{path}: {error}") from error


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="Execute offline fixture expectations")
    validate.add_argument("files", type=Path, nargs="+")
    show = commands.add_parser("show", help="Print one validated case result")
    show.add_argument("file", type=Path)
    show.add_argument("case")
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            for path in args.files:
                results = validate_fixture(_load(path))
                print(json.dumps({
                    "file": str(path), "cases": len(results),
                    "expected_errors": sum("error" in item for item in results),
                }))
        else:
            results = validate_fixture(_load(args.file))
            selected = [item for item in results if item["name"] == args.case]
            if not selected:
                raise FederationError("not_found", f"Unknown case: {args.case}")
            print(json.dumps(selected[0], indent=2))
    except FederationError as error:
        print(json.dumps({"error": error.code, "message": str(error)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
