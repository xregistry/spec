"""Offline HTTP mappings and transcript interpretation, without network I/O."""

import base64
import binascii
import json
import re
from urllib.parse import quote, urljoin, urlsplit

from federation_examples import (
    FederationError, resource_type, select_label, validate_profile, validate_xid,
)


def _require(condition, message, code="invalid_package"):
    if not condition:
        raise FederationError(code, message)


def request_url(endpoint, modelsource, operation, target):
    """Map one typed abstract read to the existing Core HTTP API."""
    validate_profile({"name": "http", "endpoint": endpoint})
    if operation in ("model", "capabilities"):
        _require(target == "/", "Model and capabilities target must be /")
        return endpoint.rstrip("/") + "/" + operation
    _require(operation in ("entity", "collection", "document"),
             "Unknown read operation", "unsupported_operation")
    validate_xid(target, collection=operation == "collection")
    parts = [] if target == "/" else target[1:].split("/")
    groups = modelsource.get("groups", {})
    if parts:
        _require(parts[0] in groups, "Unknown Group type")
    definition = None
    if len(parts) >= 3:
        resource_xid = "/" + "/".join(parts[:3] + [parts[3] if len(parts) > 3 else "_"])
        group_name, resource_name = resource_type(modelsource, resource_xid)
        definition = groups[group_name]["resources"][resource_name]
    document_target = definition is not None and len(parts) in (4, 6)
    has_document = document_target and definition.get("hasdocument", True)
    if operation == "document":
        _require(has_document, "Target has no domain document", "unsupported_operation")
    suffix = "$details" if operation == "entity" and has_document else ""
    if not parts:
        return endpoint
    return endpoint.rstrip("/") + "/" + "/".join(
        quote(part, safe="-._~:@") for part in parts
    ) + suffix


def literal_filter(selector):
    """Return a safely expressible Core filter, or None for local comparison."""
    _require(isinstance(selector, dict) and set(selector) == {"label", "value"},
             "Selector requires label and value")
    key, value = selector["label"], selector["value"]
    _require(isinstance(key, str) and isinstance(value, str), "Selector strings required")
    if (
        not key or not key.isascii() or not value.isascii()
        or value.casefold() == "null"
        or any(c in key for c in "'\"\\[],;=")
        or any(c in value for c in "'\"\\,;")
        or any(ord(c) < 32 or ord(c) == 127 for c in key + value)
    ):
        return None
    path = "." + key if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) else "['" + key + "']"
    return "labels" + path + "=" + value.replace("*", r"\*")


def _headers(value):
    _require(isinstance(value, dict), "Headers must be an object")
    result = {}
    for name, item in value.items():
        _require(isinstance(name, str) and isinstance(item, str), "Invalid header")
        key = name.lower()
        _require(key not in result, "Duplicate case-insensitive header")
        result[key] = item
    return result


def _body(response):
    kinds = [key for key in ("json", "text", "base64") if key in response]
    _require(len(kinds) <= 1, "Conflicting response bodies")
    if not kinds:
        return b"", b""
    kind = kinds[0]
    value = response[kind]
    if kind == "json":
        try:
            return value, json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
        except (TypeError, ValueError, UnicodeError) as error:
            raise FederationError("invalid_package", "Invalid JSON response") from error
    _require(isinstance(value, str), "Body encoding must be a string")
    if kind == "text":
        try:
            data = value.encode("utf-8")
        except UnicodeError as error:
            raise FederationError("invalid_package", "Invalid UTF-8 response") from error
    else:
        try:
            data = base64.b64decode(value, validate=True)
        except (binascii.Error, ValueError) as error:
            raise FederationError("invalid_package", "Invalid Base64 response") from error
        _require(base64.b64encode(data).decode("ascii") == value, "Noncanonical Base64")
    return data, data


def _origin(url):
    _require(isinstance(url, str) and url.isascii()
             and not re.search(r"[\x00-\x20\x7f\\#]", url), "Invalid request URI")
    validate_profile({"name": "http", "endpoint": url.split("?", 1)[0]})
    parsed = urlsplit(url)
    host = parsed.hostname
    if ":" in host:
        host = "[" + host + "]"
    port = parsed.port
    suffix = "" if port in (None, 443 if parsed.scheme == "https" else 80) else ":" + str(port)
    return parsed.scheme + "://" + host + suffix


def _next_link(header, request_url):
    next_urls = []
    counts = set()
    for match in re.finditer(r"<([^>]+)>([^,]*)", header):
        relation = re.search(r';\s*rel\s*=\s*(?:"([^"]*)"|([^;\s]+))', match[2])
        if relation and "next" in (relation[1] or relation[2]).split():
            next_urls.append(urljoin(request_url, match[1]))
        count = re.search(r';\s*count\s*=\s*"?([^;"\s]+)"?', match[2])
        if count:
            _require(re.fullmatch(r"[0-9]{1,20}", count[1]) is not None, "Invalid page count")
            counts.add(int(count[1]))
    _require(len(next_urls) <= 1, "Multiple next links")
    _require(len(counts) <= 1, "Conflicting page counts", "inconsistent_snapshot")
    return (next_urls[0] if next_urls else None, next(iter(counts), None))


def _weak_etag(value):
    tag = value[2:] if value.startswith("W/") else value
    _require(re.fullmatch(r'"[^"\x00-\x20\x7f]*"', tag) is not None, "Invalid ETag")
    return tag


def _etag_matches(condition, tag):
    if condition == "*":
        return True
    token = r'(?:W/)?"[^"\x00-\x20\x7f]*"'
    _require(re.fullmatch(r"\s*" + token + r"(?:\s*,\s*" + token + r")*\s*", condition)
             is not None, "Invalid If-None-Match list")
    tokens = re.findall(token, condition)
    return any(_weak_etag(token) == _weak_etag(tag) for token in tokens)


def interpret_transcript(
    transcript, *, supported_specversions=("1.0-rc4",),
    max_requests=100, max_bytes=16 * 1024 * 1024, trace=None,
):
    """Execute normalized exchanges; never read their expected-outcome fields.

    This intentionally supports contiguous range assembly and same-URL cache
    revalidation, not a complete HTTP cache or transport implementation.
    """
    _require(isinstance(transcript, dict), "Transcript must be an object")
    _require(type(max_requests) is int and max_requests > 0
             and type(max_bytes) is int and max_bytes >= 0, "Invalid limits")
    endpoint = transcript.get("endpoint")
    validate_profile({"name": "http", "endpoint": endpoint})
    policy = transcript.get("policy", {})
    _require(isinstance(policy, dict), "Policy must be an object")
    allowed = policy.get("allowedOrigins", [_origin(endpoint)])
    _require(isinstance(allowed, list) and all(isinstance(v, str) for v in allowed),
             "Invalid allowed origins")
    allowed = {_origin(value) for value in allowed}
    exchanges = transcript.get("exchanges")
    _require(isinstance(exchanges, list) and exchanges, "No exchanges")
    trace = [] if trace is None else trace
    cache, partial, defaults, members = {}, {}, {}, {}
    next_url = None
    redirect_url = None
    redirect_origins = set()
    pages = 0
    total_bytes = 0
    cache_reused = False
    discarded = b""
    value = None
    registry = None
    last_origin = None
    selector = transcript.get("selector")
    source_xid = None
    collection_scope = None
    declared_count = None
    for position, exchange in enumerate(exchanges):
        _require(position < max_requests, "Request limit exhausted", "limit_exceeded")
        _require(isinstance(exchange, dict), "Exchange must be an object")
        request, response = exchange.get("request"), exchange.get("response")
        _require(isinstance(request, dict) and isinstance(response, dict), "Invalid exchange")
        url = request.get("url")
        origin = _origin(url)
        _require(origin in allowed, "Destination denied by policy", "policy_denied")
        pending = next_url or redirect_url
        if pending is not None:
            _require(url == pending, "Continuation URL was changed", "inconsistent_snapshot")
        request_headers = _headers(request.get("headers", {}))
        if last_origin is not None and origin != last_origin:
            protected = {"authorization", "cookie", "if-match", "if-none-match",
                         "if-modified-since", "if-unmodified-since", "if-range"}
            _require(not protected.intersection(request_headers),
                     "Origin-scoped headers crossed a trust boundary", "policy_denied")
        headers = _headers(response.get("headers", {}))
        status = response.get("status")
        _require(type(status) is int and 100 <= status <= 599, "Invalid HTTP status")
        trace.append({"url": url, "status": status})
        last_origin = origin
        was_page = next_url is not None
        next_url = redirect_url = None
        if status in (401, 403):
            raise FederationError("policy_denied", f"HTTP {status}")
        if status == 412:
            raise FederationError("inconsistent_snapshot", "HTTP 412")
        if status >= 400:
            detail = response.get("json", {})
            core_error = detail.get("type", "") if isinstance(detail, dict) else ""
            if core_error.rsplit("#", 1)[-1] in ("not_available", "api_not_found"):
                code = "unsupported_operation"
            elif core_error.rsplit("#", 1)[-1] == "unsupported_specversion":
                code = "unsupported_version"
            elif was_page:
                code = "inconsistent_snapshot"
            else:
                code = "not_found" if status == 404 else "unavailable"
            raise FederationError(code, f"HTTP {status}: {core_error}")
        body, encoded = _body(response)
        total_bytes += len(encoded)
        _require(total_bytes <= max_bytes, "Byte limit exhausted", "limit_exceeded")
        if "etag" in headers:
            _weak_etag(headers["etag"])
        if "content-length" in headers and status != 304 and "json" not in response:
            length = headers["content-length"]
            _require(re.fullmatch(r"[0-9]+", length) is not None, "Invalid Content-Length")
            _require(int(length) == len(encoded), "Truncated response", "integrity_error")
        if status in (301, 302, 303, 307, 308):
            _require("location" in headers, "Redirect lacks Location")
            redirect_url = urljoin(url, headers["location"])
            _require(_origin(redirect_url) in allowed, "Redirect denied", "policy_denied")
            _require(redirect_url not in redirect_origins, "Redirect cycle", "limit_exceeded")
            redirect_origins.add(url)
            source_xid = source_xid or headers.get("xregistry-xid")
            continue
        redirect_origins.clear()
        if status == 304:
            _require(not encoded, "304 cannot supply replacement bytes")
            cached = cache.get(url)
            _require(cached is not None, "304 has no applicable cached response",
                     "inconsistent_snapshot")
            _require(cached["headers"].get("vary") != "*", "Vary prevents cache reuse",
                     "inconsistent_snapshot")
            _require(cached["request"] == {
                k: v for k, v in request_headers.items() if not k.startswith("if-")
            }, "304 authorization or representation scope changed", "inconsistent_snapshot")
            tag = cached["headers"].get("etag")
            condition = request_headers.get("if-none-match", "")
            _require(tag and _etag_matches(condition, tag),
                     "304 does not match the cached validator", "inconsistent_snapshot")
            if "etag" in headers:
                _require(_weak_etag(headers["etag"]) == _weak_etag(tag),
                         "304 changed representation validator", "inconsistent_snapshot")
            cached["headers"].update(headers)
            value = cached["value"]
            cache_reused = True
            continue
        _require(status in (200, 206), "Unsupported success status", "unsupported_operation")
        if "if-range" in request_headers:
            _require(not request_headers["if-range"].startswith("W/"),
                     "If-Range requires a strong validator")
        if status == 206:
            _require(isinstance(body, bytes), "Range body must contain exact bytes")
            match = re.fullmatch(r"bytes ([0-9]+)-([0-9]+)/([0-9]+)",
                                headers.get("content-range", ""))
            _require(match is not None, "Invalid Content-Range")
            start, end, total = (int(item) for item in match.groups())
            _require(start <= end < total and end - start + 1 == len(body),
                     "Range length mismatch", "integrity_error")
            prior = partial.get(url)
            accumulated = b"" if prior is None else prior["data"]
            _require(start == len(accumulated), "Range gap or overlap", "inconsistent_snapshot")
            if prior is not None:
                tag = headers.get("etag")
                _require(tag and not tag.startswith("W/") and tag == prior["etag"]
                         and total == prior["total"]
                         and request_headers.get("if-range") == tag,
                         "Range representation changed", "inconsistent_snapshot")
            partial[url] = {"data": accumulated + body, "total": total,
                            "etag": headers.get("etag")}
            value = partial[url]["data"]
            if len(value) == total:
                del partial[url]
            continue
        if url in partial:
            discarded = partial.pop(url)["data"]
        if isinstance(body, dict):
            if "xid" in body:
                validate_xid(body["xid"])
                base_path = urlsplit(endpoint).path.rstrip("/")
                request_path = urlsplit(url).path
                _require(request_path == base_path or request_path.startswith(base_path + "/"),
                         "Metadata is outside selected Registry", "invalid_package")
                target = request_path[len(base_path):] or "/"
                if target.endswith("$details"):
                    target = target[:-8]
                _require(body["xid"] == target, "Response XID differs from request")
            if "specversion" in body:
                _require(body["specversion"] in supported_specversions,
                         "Unsupported Core version", "unsupported_version")
                registry = body
            if "defaultversionid" in body:
                identity = body.get("xid")
                selected = body["defaultversionid"]
                _require(identity is not None, "Meta identity is absent")
                _require(identity not in defaults or defaults[identity] == selected,
                         "Default Version changed", "inconsistent_snapshot")
                defaults[identity] = selected
            if selector is not None and "specversion" not in body and not urlsplit(url).path.endswith(
                ("/capabilities", "/model", "/modelsource")
            ):
                pages += 1
                if collection_scope is None:
                    path = urlsplit(url).path
                    base = urlsplit(endpoint).path.rstrip("/")
                    _require(path.startswith(base + "/"), "Collection is outside Registry")
                    collection_scope = path[len(base):]
                    validate_xid(collection_scope, collection=True)
                for key, entity in body.items():
                    _require(isinstance(entity, dict), "Collection member is not metadata")
                    _require(key not in members, "Repeated collection member",
                             "inconsistent_snapshot")
                    if "xid" in entity:
                        _require(entity["xid"] == collection_scope + "/" + key,
                                 "Collection member XID disagrees with its key")
                    members[key] = entity
                next_url, count = _next_link(headers.get("link", ""), url)
                if count is not None:
                    _require(declared_count is None or declared_count == count,
                             "Collection count changed", "inconsistent_snapshot")
                    declared_count = count
                if next_url is not None:
                    _require(_origin(next_url) in allowed, "Page destination denied", "policy_denied")
        value = body
        if "no-store" not in headers.get("cache-control", "").lower():
            previous = cache.get(url)
            if previous and "if-none-match" in request_headers and previous["value"] != body:
                raise FederationError("inconsistent_snapshot", "Revalidated representation changed")
            cache[url] = {
                "value": body, "headers": headers,
                "request": {k: v for k, v in request_headers.items() if not k.startswith("if-")},
            }
    _require(next_url is None and redirect_url is None and not partial,
             "Incomplete read sequence", "inconsistent_snapshot")
    if selector is not None:
        _require(pages > 0, "No collection response", "inconsistent_snapshot")
        _require(declared_count is None or len(members) == declared_count,
                 "Incomplete collection membership", "inconsistent_snapshot")
        value = select_label(list(members.values()), selector["label"], selector["value"])
    return {
        "value": value, "registry": registry, "pages": pages,
        "cache_reused": cache_reused, "discarded_partial": discarded,
        "source_xid": source_xid, "snapshot": None, "immutable": False,
        "trace": trace,
    }
