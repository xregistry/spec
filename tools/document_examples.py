"""Offline document-tree fixtures and reads, not a production resolver."""

import argparse
import base64
import copy
import errno
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import unicodedata
from pathlib import Path
from urllib.parse import quote, unquote_to_bytes, urlsplit

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError
from referencing import Registry, Resource

from federation_examples import (
    FederationError,
    resource_type,
    select_label,
    validate_profile,
    validate_xid,
)


FORMAT = "xregistry-document-tree"
FORMAT_VERSION = "1"
CORE_VERSION = "1.0-rc4"
_SCHEMAS = Path(__file__).parent.parent / "workingdrafts" / "bindings" / "schemas"
_DEVICE = re.compile(r"(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)", re.I)
_OID = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})\Z")
_STAMP_FIELDS = ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns")
if os.name != "nt":
    # Windows stat/fstat do not consistently use the same meaning of ctime.
    _STAMP_FIELDS += ("st_ctime_ns",)


def _require(condition, message, code="invalid_package"):
    if not condition:
        raise FederationError(code, message)


def _json_bytes(value):
    try:
        text = json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise FederationError("invalid_package", "Fixture value is not JSON") from error
    return (text + "\n").encode("utf-8")


def _parse_json(data, name):
    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result, f"Duplicate JSON key in {name}: {key}")
            result[key] = value
        return result

    def constant(value):
        raise FederationError("invalid_package", f"Non-JSON number in {name}: {value}")

    try:
        result = json.loads(
            data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant
        )
    except FederationError:
        raise
    except (UnicodeDecodeError, ValueError) as error:
        raise FederationError("invalid_package", f"Invalid JSON in {name}") from error
    except RecursionError as error:
        raise FederationError("limit_exceeded", "JSON nesting limit") from error
    _require(isinstance(result, dict), f"Expected JSON object in {name}")
    return result


def storage_path(namespace, number):
    """Allocate an opaque portable name. Never encode or sanitize a Core ID."""
    _require(namespace in ("records", "indexes", "documents"), "Unknown namespace")
    _require(type(number) is int and number >= 0, "Invalid storage allocation")
    digits = format(number, "x")
    chunks = ["n" + digits[i:i + 32] for i in range(0, len(digits), 32)]
    suffix = ".bin" if namespace == "documents" else ".json"
    return namespace + "/" + "/".join(chunks) + suffix


def _storage_name(value, namespace=None):
    _require(isinstance(value, str), "Storage name must be a string", "policy_denied")
    _require(len(value) <= 4096, "Storage path length limit", "limit_exceeded")
    _require(namespace is None or namespace in ("records", "indexes", "documents"),
             "Unknown storage role")
    _require(
        value
        and not any(c in '\\<>:"|?*' or unicodedata.category(c) in ("Cc", "Cs") for c in value)
        and not re.search(r"%(?:2e|2f|5c)", value, re.I)
        and all(
            part and part not in (".", "..")
            and not part.endswith((" ", ".")) and not _DEVICE.match(part)
            for part in value.split("/")
        ),
        "Unsafe storage name", "policy_denied",
    )
    return value


def _uri(value, *, absolute=True):
    _require(isinstance(value, str) and value, "URI must be a nonempty string")
    _require(not any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value),
             "Whitespace or control character in URI")
    _require(not re.search(r"%(?![0-9a-fA-F]{2})", value), "Invalid URI escape")
    try:
        parsed = urlsplit(value)
        parsed.port
    except ValueError as error:
        raise FederationError("invalid_package", "Malformed URI") from error
    _require(not absolute or bool(parsed.scheme), "Absolute URI required")
    _require(parsed.username is None and parsed.password is None,
             "Embedded credentials prohibited", "policy_denied")
    return parsed


def _git_path(value):
    _require(isinstance(value, str), "Git path must be a string")
    if value:
        for part in value.split("/"):
            _require(
                re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}", part) is not None
                and not part.endswith(".") and not _DEVICE.match(part),
                "Unsafe or nonportable Git root", "policy_denied",
            )
    return value


def _revision(value):
    _require(isinstance(value, str) and value, "Missing Git revision")
    if _OID.fullmatch(value):
        return value.lower()
    _require(
        value.startswith("refs/")
        and not re.search(r"[\x00-\x20\x7f~^:?*\[\\]|\.\.|@\{|//", value)
        and all(
            part and not part.startswith(".")
            and not part.endswith((".", ".lock"))
            for part in value.split("/")
        ),
        "Revision must be a full ref or complete object ID",
    )
    return value


def git_locator(profile):
    """Validate an advertisement. Return endpoint, revision, selected root."""
    validate_profile(profile)
    _require(profile["name"] == "git", "Not a Git profile", "unsupported_binding")
    _uri(profile["endpoint"])
    parameters = profile.get("parameters", {})
    return (
        profile["endpoint"],
        _revision(parameters.get("revision")),
        _git_path(parameters.get("path", "xregistry")),
    )


def _io_error(error, name, missing="invalid_package"):
    if error.errno in (errno.EACCES, errno.EPERM, errno.ELOOP):
        code = "policy_denied"
    elif error.errno == errno.ENAMETOOLONG or getattr(error, "winerror", None) == 206:
        code = "limit_exceeded"
    elif error.errno == errno.ENOENT:
        code = missing
    else:
        code = "unavailable"
    return FederationError(code, f"Cannot access {name}: {error.strerror}")


def _checked_path(path, *, directory=False, missing="invalid_package"):
    path = Path(path).absolute()
    _require(not path.drive.startswith("\\\\"), "UNC access prohibited", "policy_denied")
    for component in [*reversed(path.parents), path]:
        try:
            info = component.lstat()
        except OSError as error:
            raise _io_error(error, component.name, missing) from error
        _require(
            not stat.S_ISLNK(info.st_mode)
            and not getattr(info, "st_file_attributes", 0) & 0x400,
            "Symlink or reparse point prohibited", "policy_denied",
        )
        expected_directory = component != path or directory
        _require(
            stat.S_ISDIR(info.st_mode) if expected_directory
            else stat.S_ISREG(info.st_mode),
            "Expected regular directory or file", "policy_denied",
        )
    return info


def file_root(profile, boundary):
    """Parse a local File advertisement and enforce the caller's boundary."""
    validate_profile(profile)
    _require(profile["name"] == "file", "Not a File profile", "unsupported_binding")
    _require(profile["parameters"]["layout"] == "document-tree",
             "Use the OCI helper for oci-layout", "unsupported_operation")
    parsed = _uri(profile["endpoint"])
    raw = parsed.path
    _require(not re.search(r"%(?:2f|5c)", raw, re.I),
             "Encoded separator prohibited", "policy_denied")
    try:
        decoded = unquote_to_bytes(raw).decode("utf-8")
    except UnicodeDecodeError as error:
        raise FederationError("invalid_package", "File URI is not UTF-8") from error
    _require(
        "\\" not in decoded
        and not any(ord(c) < 32 or ord(c) == 127 for c in decoded),
        "Unsafe file URI character", "policy_denied",
    )
    components = decoded[1:].split("/")
    if components and components[-1] == "":
        components.pop()
    _require(all(p not in ("", ".", "..") for p in components),
             "Empty or dot file URI component", "policy_denied")
    windows = bool(components and re.fullmatch(r"[A-Za-z]:", components[0]))
    if os.name == "nt":
        _require(windows, "Windows requires an absolute drive URI",
                 "unsupported_operation")
        for part in components[1:]:
            _require(
                not re.search(r'[:<>"|?*]', part)
                and not part.endswith((" ", ".")) and not _DEVICE.match(part),
                "Unsafe Windows file URI component", "policy_denied",
            )
        root = Path(components[0] + "\\" + "\\".join(components[1:]))
    else:
        _require(not windows and not (components and components[0].endswith("|")),
                 "Windows file URI on a non-Windows host", "unsupported_operation")
        root = Path("/").joinpath(*components)
    boundary = Path(boundary).absolute()
    _checked_path(boundary, directory=True, missing="not_found")
    try:
        root.relative_to(boundary)
    except ValueError as error:
        raise FederationError("policy_denied", "Root is outside boundary") from error
    _checked_path(root, directory=True, missing="not_found")
    return root


class _Store:
    def __init__(self, *, max_file_bytes=16 * 1024 * 1024,
                 max_total_bytes=128 * 1024 * 1024, max_files=4096):
        for limit in (max_file_bytes, max_total_bytes, max_files):
            _require(type(limit) is int and limit > 0, "Limits must be positive integers")
        self.max_file_bytes = max_file_bytes
        self.max_total_bytes = max_total_bytes
        self.max_files = max_files
        self.reads = []
        self.total_bytes = 0
        self.pin = None

    def _record_read(self, name, data):
        _require(len(data) <= self.max_file_bytes, "File byte limit", "limit_exceeded")
        _require(len(self.reads) < self.max_files, "File count limit", "limit_exceeded")
        _require(self.total_bytes + len(data) <= self.max_total_bytes,
                 "Aggregate byte limit", "limit_exceeded")
        self.reads.append(name)
        self.total_bytes += len(data)
        return data

    def finish(self):
        """Immutable stores need no pathname freshness check."""


class MemoryStore(_Store):
    """In-memory example input, useful for constructing negative vectors."""

    def __init__(self, files, **limits):
        super().__init__(**limits)
        self.files = dict(files)

    def read(self, name):
        _storage_name(name)
        try:
            data = self.files[name]
        except KeyError as error:
            code = "not_found" if name == "registry.json" else "invalid_package"
            raise FederationError(code, f"Missing {name}") from error
        _require(isinstance(data, bytes), "MemoryStore files must be bytes")
        return self._record_read(name, data)


class FileStore(_Store):
    """Static containment and mutation checks, not a hostile-race sandbox."""

    def __init__(self, root, **limits):
        super().__init__(**limits)
        self.root = Path(root).absolute()
        _checked_path(self.root, directory=True, missing="not_found")
        self._observed = {}

    @staticmethod
    def _stamp(info):
        return tuple(getattr(info, field) for field in _STAMP_FIELDS)

    def read(self, name):
        _storage_name(name)
        path = self.root.joinpath(*name.split("/"))
        before = _checked_path(
            path, missing="not_found" if name == "registry.json" else "invalid_package"
        )
        stamp = self._stamp(before)
        _require(before.st_size <= self.max_file_bytes, "File byte limit",
                 "limit_exceeded")
        _require(name not in self._observed or self._observed[name] == stamp,
                 "File changed between reads", "inconsistent_snapshot")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            with os.fdopen(os.open(path, flags), "rb") as stream:
                _require(self._stamp(os.fstat(stream.fileno())) == stamp,
                         "File replaced during open", "inconsistent_snapshot")
                _checked_path(path)
                data = stream.read(before.st_size + 1)
                _require(self._stamp(os.fstat(stream.fileno())) == stamp,
                         "File changed during read", "inconsistent_snapshot")
        except OSError as error:
            raise _io_error(error, name, "inconsistent_snapshot") from error
        _require(len(data) == before.st_size, "File read was not stable",
                 "inconsistent_snapshot")
        _require(self._stamp(_checked_path(path)) == stamp,
                 "File replaced after read", "inconsistent_snapshot")
        self._observed[name] = stamp
        return self._record_read(name, data)

    def finish(self):
        for name, stamp in self._observed.items():
            path = self.root.joinpath(*name.split("/"))
            info = _checked_path(path, missing="inconsistent_snapshot")
            _require(self._stamp(info) == stamp, "Snapshot changed during operation",
                     "inconsistent_snapshot")


class GitStore(_Store):
    """Read an explicit isolated local Git object directory without checkout."""

    def __init__(self, git_dir, revision, path="xregistry", **limits):
        super().__init__(**limits)
        self.git_dir = Path(git_dir).absolute()
        self.path = _git_path(path)
        self.revision = _revision(revision)
        _checked_path(self.git_dir, directory=True, missing="not_found")
        _checked_path(self.git_dir / "objects", directory=True, missing="not_found")
        info = _checked_path(self.git_dir / "config")
        _require(info.st_size <= self.max_file_bytes, "Git config byte limit",
                 "limit_exceeded")
        try:
            config = (self.git_dir / "config").read_bytes()
        except OSError as error:
            raise _io_error(error, "Git config") from error
        _require(not re.search(rb"(?im)^\s*\[\s*include(?:if)?(?=\s|\])", config),
                 "Git configuration includes prohibited", "policy_denied")
        for relative in (
            ("commondir",), ("info", "grafts"), ("objects", "info", "alternates"),
            ("objects", "info", "http-alternates"),
        ):
            _require(not (self.git_dir.joinpath(*relative)).exists(),
                     "Git alternate/common stores and grafts prohibited",
                     "policy_denied")
        pack_dir = self.git_dir / "objects" / "pack"
        if pack_dir.exists():
            _checked_path(pack_dir, directory=True)
            for entry in pack_dir.iterdir():
                _checked_path(entry)
        self._environment = {
            key: value for key, value in os.environ.items()
            if not key.upper().startswith("GIT_")
        }
        self._environment.update({
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_ATTR_NOSYSTEM": "1",
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_OPTIONAL_LOCKS": "0",
            "LC_ALL": "C",
        })
        object_format = self._git("rev-parse", "--show-object-format").strip()
        _require(object_format in (b"sha1", b"sha256"), "Unsupported Git object format",
                 "unsupported_version")
        self._algorithm = object_format.decode("ascii")
        self._oid_bytes = 20 if object_format == b"sha1" else 32
        self._objects = {}
        self.object_reads = []
        self._object_bytes = 0
        if self.revision.startswith("refs/"):
            self._git("check-ref-format", self.revision, code="invalid_package")
        else:
            _require(len(self.revision) == self._oid_bytes * 2,
                     "Revision OID does not match repository object format")
        oid = self._git(
            "rev-parse", "--verify", "--end-of-options", self.revision,
            code="not_found",
        ).strip().decode("ascii")
        self._git("cat-file", "-e", oid, code="not_found")
        for _ in range(32):
            kind, data = self._object(oid)
            if kind == "commit":
                self.pin = oid
                match = re.match(rb"tree ([0-9a-f]+)\n", data)
                _require(match is not None, "Commit has no tree")
                tree = match[1].decode("ascii")
                break
            _require(kind == "tag", "Selected revision does not resolve to a commit")
            match = re.match(rb"object ([0-9a-f]+)\n", data)
            _require(match is not None, "Malformed annotated tag")
            oid = match[1].decode("ascii")
        else:
            raise FederationError("limit_exceeded", "Annotated tag depth limit")
        for part in self.path.split("/") if self.path else []:
            mode, tree = self._entry(tree, part, missing="not_found")
            self._mode(mode, directory=True)
        self._root_tree = tree

    def _git(self, *arguments, code="inconsistent_snapshot"):
        command = [
            "git", "--no-pager", "--no-replace-objects",
            "--git-dir=" + str(self.git_dir),
            "-c", "core.hooksPath=" + os.devnull,
            "-c", "core.fsmonitor=false",
            "-c", "protocol.allow=never",
            "-c", "core.attributesFile=" + os.devnull,
            *arguments,
        ]
        try:
            result = subprocess.run(
                command, cwd=self.git_dir, env=self._environment,
                capture_output=True, timeout=30, check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise FederationError("limit_exceeded", "Git command time limit") from error
        except OSError as error:
            raise FederationError("unavailable", "Git executable unavailable") from error
        if result.returncode != 0:
            diagnostic = result.stderr.decode("utf-8", errors="replace").strip()
            diagnostic = re.sub(
                r"([A-Za-z][A-Za-z0-9+.-]*://)[^/@\s]+@", r"\1[redacted]@",
                diagnostic,
            )
            raise FederationError(
                code, f"Git {arguments[0]} failed (exit {result.returncode}): "
                + diagnostic[:400],
            )
        return result.stdout

    def _object(self, oid):
        _require(re.fullmatch(r"[0-9a-f]+", oid) is not None
                 and len(oid) == self._oid_bytes * 2, "Invalid Git object ID")
        if oid not in self._objects:
            loose = self.git_dir / "objects" / oid[:2] / oid[2:]
            if loose.exists():
                _checked_path(loose)
            kind = self._git("cat-file", "-t", oid).strip().decode("ascii")
            _require(kind in ("commit", "tag", "tree", "blob"), "Unknown Git object type")
            size = int(self._git("cat-file", "-s", oid).strip())
            _require(0 <= size <= self.max_file_bytes, "Git object byte limit",
                     "limit_exceeded")
            _require(len(self._objects) < self.max_files
                     and self._object_bytes + size <= self.max_total_bytes,
                     "Git object traversal limit", "limit_exceeded")
            data = self._git("cat-file", kind, oid)
            digest = hashlib.new(
                self._algorithm, f"{kind} {len(data)}\0".encode("ascii") + data
            ).hexdigest()
            _require(len(data) == size and digest == oid,
                     "Git object identity mismatch", "integrity_error")
            self._objects[oid] = (kind, data)
            self.object_reads.append(oid)
            self._object_bytes += size
        return self._objects[oid]

    def _entry(self, tree, name, *, missing="invalid_package"):
        kind, data = self._object(tree)
        _require(kind == "tree", "Expected Git tree")
        offset = 0
        found = None
        while offset < len(data):
            space = data.find(b" ", offset)
            end = data.find(b"\0", space + 1)
            _require(space > offset and end > space
                     and end + 1 + self._oid_bytes <= len(data),
                     "Malformed Git tree entry")
            mode = data[offset:space]
            entry_name = data[space + 1:end]
            oid = data[end + 1:end + 1 + self._oid_bytes].hex()
            if entry_name == name.encode("utf-8"):
                _require(found is None, "Duplicate Git tree entry")
                found = (mode, oid)
            offset = end + 1 + self._oid_bytes
        _require(found is not None, f"Missing Git tree entry: {name}", missing)
        return found

    @staticmethod
    def _mode(mode, *, directory):
        _require(mode != b"120000", "Git symlink prohibited", "policy_denied")
        _require(mode != b"160000", "Git submodule unsupported", "unsupported_operation")
        _require(mode == b"40000" if directory else mode in (b"100644", b"100755"),
                 "Unexpected Git tree mode")

    def read(self, name):
        _storage_name(name)
        parts = name.split("/")
        tree = self._root_tree
        for part in parts[:-1]:
            mode, tree = self._entry(tree, part)
            self._mode(mode, directory=True)
        mode, oid = self._entry(
            tree, parts[-1],
            missing="not_found" if name == "registry.json" else "invalid_package",
        )
        self._mode(mode, directory=False)
        kind, data = self._object(oid)
        _require(kind == "blob", "Expected Git blob")
        signature = b"version https://git-lfs.github.com/spec/v1"
        _require(not (data == signature or data.startswith(signature + b"\n")
                      or data.startswith(signature + b"\r\n")),
                 "Git LFS pointer unsupported", "unsupported_operation")
        return self._record_read(name, data)


def _validators():
    schemas = [
        _parse_json((_SCHEMAS / f"document-{kind}.schema.json").read_bytes(), kind)
        for kind in ("record", "index")
    ]
    registry = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas
    )
    for schema in schemas:
        Draft202012Validator.check_schema(schema)
    return {
        kind: Draft202012Validator(
            schema, registry=registry, format_checker=FormatChecker()
        )
        for kind, schema in zip(("record", "index"), schemas)
    }


def _includes(value):
    pending = [value]
    while pending:
        current = pending.pop()
        if isinstance(current, dict):
            if {"$include", "$includes"} & current.keys():
                return True
            pending.extend(current.values())
        elif isinstance(current, list):
            pending.extend(current)
    return False


def _pointer(path, token):
    return path + "/" + quote(token.replace("~", "~0").replace("/", "~1"), safe="")


class DocumentTree:
    """Schema-checked selective reads and explicit Core metadata assembly."""

    def __init__(self, store):
        self.store = store
        self._validators = _validators()
        self._cache = {}
        self._allocations = {}
        data = store.read("registry.json")
        self.root_sha256 = hashlib.sha256(data).hexdigest()
        self.root = self._decode(data, "registry.json")
        _require(self.root["kind"] == "registry", "Root is not a Registry record")
        entity = self.root["entity"]
        _require(entity["specversion"] == CORE_VERSION, "Unsupported Core version",
                 "unsupported_version")
        original = entity["modelsource"]
        resolved = self.root.get("resolvedmodelsource")
        if _includes(original):
            _require(resolved is not None and "modelbase" in self.root,
                     "Model includes require resolved source and original base")
        elif resolved is not None:
            _require(resolved == original, "Unexpected resolved model source")
        self.modelsource = resolved if resolved is not None else original
        _require(not _includes(self.modelsource), "Unresolved captured model include")
        self.groups = self.modelsource.get("groups", {})
        _require(isinstance(self.groups, dict), "Invalid model Group map")
        for name, group in self.groups.items():
            validate_xid("/" + name, collection=True)
            _require(isinstance(group, dict) and isinstance(group.get("singular"), str),
                     "Group needs a singular model name")
            resources = group.get("resources", {})
            _require(isinstance(resources, dict), "Invalid model Resource map")
            _require(
                all(isinstance(value, dict) for value in resources.values()),
                "Resource model definition must be an object",
            )
            imports = group.get("ximportresources", [])
            _require(isinstance(imports, list)
                     and all(isinstance(value, str) for value in imports),
                     "Invalid Resource imports")
        for name in self.groups:
            self._resources(name)
        self._check_record(self.root)
        self._cache["registry.json"] = (data, self.root)

    @property
    def reads(self):
        return self.store.reads

    def _decode(self, data, name):
        value = _parse_json(data, name)
        _require(value.get("format") == FORMAT, "Unknown document-tree format")
        _require(value.get("formatversion") == FORMAT_VERSION,
                 "Unknown document-tree version", "unsupported_version")
        references = []
        for field in ("entries", "collections"):
            if isinstance(value.get(field), list):
                references.extend(value[field])
        references.extend(value.get(field) for field in ("meta", "document"))
        for reference in references:
            if isinstance(reference, dict) and "href" in reference:
                _storage_name(reference["href"])
        schema = "index" if value.get("kind") == "collection" else "record"
        try:
            self._validators[schema].validate(value)
        except ValidationError as error:
            location = "/".join(str(part) for part in error.absolute_path)
            raise FederationError(
                "invalid_package", f"Schema violation in {name} at /{location}: "
                f"{error.validator}"
            ) from error
        return value

    def _resources(self, group_name):
        group = self.groups[group_name]
        resources = group.get("resources", {})
        _require(isinstance(resources, dict), "Invalid model Resource map")
        names = set(resources)
        imports = group.get("ximportresources", [])
        _require(isinstance(imports, list), "Invalid Resource imports")
        for imported in imports:
            _require(isinstance(imported, str), "Resource import must be a string")
            parts = imported.split("/")
            _require(len(parts) == 3 and parts[0] == "" and all(parts[1:]),
                     "Invalid Resource import")
            _require(parts[2] not in names, "Duplicate imported Resource name")
            names.add(parts[2])
        for name in names:
            definition = self._definition(f"/{group_name}/_/{name}/_")
            _require(isinstance(definition.get("singular"), str),
                     "Resource needs a singular model name")
            _require(type(definition.get("hasdocument", True)) is bool,
                     "Invalid hasdocument aspect")
        return sorted(names)

    def _definition(self, xid):
        origin_group, origin_resource = resource_type(self.modelsource, xid)
        return self.groups[origin_group]["resources"][origin_resource]

    def _typed(self, xid, *, collection=False):
        validate_xid(xid, collection=collection)
        if xid == "/":
            return "registry"
        parts = xid[1:].split("/")
        _require(parts[0] in self.groups, "Unknown Group model type")
        if len(parts) >= 3:
            _require(parts[2] in self._resources(parts[0]), "Unknown Resource model type")
        if collection:
            return {1: "group", 3: "resource", 5: "version"}[len(parts)]
        return {2: "group", 4: "resource", 5: "meta", 6: "version"}[len(parts)]

    def _allocate(self, reference, namespace):
        href = _storage_name(reference["href"], namespace)
        key = href.casefold()
        identity = (
            href, namespace,
            None if namespace == "documents" else reference.get("kind"),
            None if namespace == "documents" else reference.get("xid"),
            reference["size"], reference["sha256"],
        )
        _require(key not in self._allocations or self._allocations[key] == identity,
                 "Conflicting storage allocation")
        self._allocations[key] = identity

    @staticmethod
    def _ordered(references):
        xids = [reference["xid"] for reference in references]
        _require(xids == sorted(set(xids), key=lambda value: value.encode("utf-8")),
                 "References must be unique and sorted by full XID")

    def _check_record(self, record):
        entity, kind = record["entity"], record["kind"]
        xid = entity["xid"]
        _require(self._typed(xid) == kind, "Entity kind and XID disagree")
        parts = xid[1:].split("/")
        names = []
        if kind == "registry":
            names = sorted(self.groups)
            if "source" in record:
                _uri(record["source"]["uri"])
            if "modelbase" in record:
                _uri(record["modelbase"])
            capabilities = entity["capabilities"]
            for value in capabilities["available"].values():
                _require(isinstance(value, dict) and value.get("mutable") is False,
                         "Snapshot capabilities must be read-only")
            _require(not capabilities.get("mutable"), "Mutable snapshot capabilities")
        elif kind == "group":
            id_name = self.groups[parts[0]]["singular"] + "id"
            _require(entity.get(id_name) == parts[1], "Group ID disagrees with XID")
            names = self._resources(parts[0])
        else:
            resource_xid = "/" + "/".join(parts[:4])
            definition = self._definition(resource_xid)
            id_name = definition["singular"] + "id"
            _require(entity.get(id_name) == parts[3], "Resource ID disagrees with XID")
            if kind == "resource":
                _require(set(entity) == {"xid", id_name},
                         "Resource contains inherited or extra metadata")
                _require(record["meta"]["xid"] == xid + "/meta",
                         "Wrong Meta reference")
                self._allocate(record["meta"], "records")
                names = ["versions"] if record["collections"] else []
            elif kind == "meta" and "xref" in entity:
                _require(set(entity) == {"xid", id_name, "xref"},
                         "Alias Meta contains target attributes")
                _require(resource_type(self.modelsource, entity["xref"])
                         == resource_type(self.modelsource, resource_xid),
                         "xref Resource model type mismatch")
            elif kind == "version":
                _require(entity["versionid"] == parts[5], "Version ID disagrees with XID")
                self._check_document(record, definition)
            for forbidden in ("meta", "versions", "versionsurl", "versionscount"):
                _require(forbidden not in entity, "Storage contains derived navigation")
        if "collections" in record:
            self._ordered(record["collections"])
            prefix = "" if xid == "/" else xid
            _require(
                [r["xid"] for r in record["collections"]]
                == sorted(prefix + "/" + name for name in names),
                "Missing or unexpected modeled collection",
            )
            for reference in record["collections"]:
                self._allocate(reference, "indexes")
        for name in names:
            _require(not {name, name + "url", name + "count"} & entity.keys(),
                     "Storage contains inline collection or navigation")

    def _check_document(self, record, definition):
        document, entity = record["document"], record["entity"]
        singular = definition["singular"]
        _require(singular not in entity and singular + "base64" not in entity,
                 "Document bytes must be detached")
        url = entity.get(singular + "url")
        has_document = definition.get("hasdocument", True)
        _require((document["kind"] == "none") == (has_document is False),
                 "Document state disagrees with hasdocument")
        if document["kind"] == "external":
            _require(self.root["snapshot"]["completeness"] == "linked",
                     "External document in offline-complete snapshot")
            _require(url == document["uri"], "External document and metadata URI disagree")
            parsed = _uri(document["uri"], absolute=False)
            _require(parsed.scheme or "base" in document,
                     "Relative external document has no explicit base")
        else:
            _require(url is None, "Non-external Version has a document URL")
        if document["kind"] == "local":
            self._allocate(
                {**document, "xid": entity["xid"]}, "documents"
            )
        for name in ("base", "origin"):
            if name in document:
                _uri(document[name])

    def _check_index(self, index):
        expected = self._typed(index["xid"], collection=True)
        entries = index["entries"]
        _require(index["count"] == len(entries), "Index count disagrees with entries")
        self._ordered(entries)
        folded = set()
        for reference in entries:
            parts = reference["xid"].rsplit("/", 1)
            _require(parts[0] == index["xid"] and reference["kind"] == expected
                     and self._typed(reference["xid"]) == expected,
                     "Index entry is not an immediate typed member")
            _require(parts[1].casefold() not in folded, "Case-insensitive sibling collision")
            folded.add(parts[1].casefold())
            self._allocate(reference, "records")

    def _bytes(self, reference):
        name = reference["href"]
        data = self._cache[name][0] if name in self._cache else self.store.read(name)
        _require(
            len(data) == reference["size"]
            and hashlib.sha256(data).hexdigest() == reference["sha256"],
            f"Descriptor mismatch: {name}", "integrity_error",
        )
        return data

    def _read_ref(self, reference):
        data = self._bytes(reference)
        name = reference["href"]
        if name not in self._cache:
            value = self._decode(data, name)
            if value["kind"] == "collection":
                self._check_index(value)
            else:
                self._check_record(value)
            self._cache[name] = (data, value)
        value = self._cache[name][1]
        xid = value["xid"] if value["kind"] == "collection" else value["entity"]["xid"]
        _require(value["kind"] == reference["kind"] and xid == reference["xid"],
                 "Reference and stored object disagree")
        return value

    def _index(self, xid):
        self._typed(xid, collection=True)
        parent_xid = xid.rsplit("/", 1)[0] or "/"
        parent = self.read_record(parent_xid)
        if parent["kind"] == "resource":
            meta = self._read_ref(parent["meta"])
            _require("xref" not in meta["entity"], "cannot_doc_xref",
                     "unsupported_operation")
        reference = next((r for r in parent["collections"] if r["xid"] == xid), None)
        _require(reference is not None, "Missing modeled collection")
        return self._read_ref(reference)

    def read_record(self, xid):
        """Read a storage fragment. Unlike metadata(), it has no Core URLs."""
        kind = self._typed(xid)
        if xid == "/":
            return self.root
        if kind == "meta":
            owner = self.read_record(xid.rsplit("/", 1)[0])
            return self._read_ref(owner["meta"])
        collection_xid = xid.rsplit("/", 1)[0]
        index = self._index(collection_xid)
        reference = next((r for r in index["entries"] if r["xid"] == xid), None)
        _require(reference is not None, f"XID not found: {xid}", "not_found")
        record = self._read_ref(reference)
        if kind == "version":
            owner = xid.rsplit("/versions/", 1)[0]
            _, meta, versions = self._state(owner)
            entity = record["entity"]
            _require(entity["isdefault"]
                     == (entity["versionid"] == meta["entity"]["defaultversionid"]),
                     "Version default flag disagrees with Meta")
            _require(owner + "/versions/" + entity["ancestorid"]
                     in {r["xid"] for r in versions["entries"]},
                     "Missing Version ancestor")
        return record

    def _state(self, xid):
        resource = self.read_record(xid)
        _require(resource["kind"] == "resource", "Expected Resource")
        meta = self._read_ref(resource["meta"])
        if "xref" in meta["entity"]:
            _require(resource["collections"] == [], "Alias owns local Versions")
            return resource, meta, None
        _require(len(resource["collections"]) == 1, "Ordinary Resource lacks Versions")
        versions = self._read_ref(resource["collections"][0])
        default_xid = xid + "/versions/" + meta["entity"]["defaultversionid"]
        _require(any(r["xid"] == default_xid for r in versions["entries"]),
                 "Default Version is missing from index")
        return resource, meta, versions

    def _one_hop(self, xid):
        _, meta, _ = self._state(xid)
        target = meta["entity"].get("xref")
        if target is None:
            return xid
        try:
            _, target_meta, _ = self._state(target)
        except FederationError as error:
            if error.code == "not_found":
                return None
            raise
        return None if "xref" in target_meta["entity"] else target

    def _selected_version(self, xid):
        kind = self._typed(xid)
        _require(kind in ("resource", "version"), "Document requires Resource or Version",
                 "unsupported_operation")
        explicit = xid.rsplit("/", 1)[1] if kind == "version" else None
        owner = xid.rsplit("/versions/", 1)[0] if kind == "version" else xid
        _require(self._definition(owner).get("hasdocument", True),
                 "Resource hasdocument is false", "unsupported_operation")
        target = self._one_hop(owner)
        _require(target is not None, "No one-hop alias document", "not_found")
        _, meta, _ = self._state(target)
        version = explicit if explicit is not None else meta["entity"]["defaultversionid"]
        return self.read_record(target + "/versions/" + version)

    def document_descriptor(self, xid):
        descriptor = copy.deepcopy(self._selected_version(xid)["document"])
        self.store.finish()
        return descriptor

    def document(self, xid):
        """Return exact local bytes. External retrieval is never implicit."""
        record = self._selected_version(xid)
        descriptor = record["document"]
        _require(descriptor["kind"] == "local", "External content is not fetched",
                 "unsupported_operation")
        data = self._bytes(descriptor)
        self.store.finish()
        return data

    def _materialize(self, xid, pointer):
        record = self.read_record(xid)
        entity = copy.deepcopy(record["entity"])
        entity["self"] = "#" + pointer
        if record["kind"] in ("registry", "group"):
            for reference in record["collections"]:
                name = reference["xid"].rsplit("/", 1)[1]
                index = self._read_ref(reference)
                child_pointer = _pointer(pointer, name)
                entity[name] = {
                    child["xid"].rsplit("/", 1)[1]: self._materialize(
                        child["xid"], _pointer(child_pointer, child["xid"].rsplit("/", 1)[1])
                    ) for child in index["entries"]
                }
                entity[name + "url"] = "#" + child_pointer
                entity[name + "count"] = index["count"]
        elif record["kind"] == "resource":
            _, meta, versions = self._state(xid)
            meta_pointer = _pointer(pointer, "meta")
            entity["meta"] = copy.deepcopy(meta["entity"])
            entity["meta"]["self"] = "#" + meta_pointer
            entity["metaurl"] = "#" + meta_pointer
            if versions is not None:
                version_pointer = _pointer(pointer, "versions")
                entity["versions"] = {
                    child["xid"].rsplit("/", 1)[1]: self._materialize(
                        child["xid"],
                        _pointer(version_pointer, child["xid"].rsplit("/", 1)[1]),
                    ) for child in versions["entries"]
                }
                entity["versionsurl"] = "#" + version_pointer
                entity["versionscount"] = versions["count"]
                default = entity["meta"]["defaultversionid"]
                entity["meta"]["defaultversionurl"] = "#" + _pointer(version_pointer, default)
        return entity

    def metadata(self, xid):
        kind = self._typed(xid)
        result = {"kind": kind, "entity": self._materialize(xid, "/entity")}
        if kind == "registry":
            result["snapshot"] = copy.deepcopy(self.root["snapshot"])
            if "source" in self.root:
                result["source"] = copy.deepcopy(self.root["source"])
        if kind == "meta" and "xref" not in result["entity"]:
            owner = xid.rsplit("/", 1)[0]
            self._state(owner)
            default = result["entity"]["defaultversionid"]
            pointer = "/related/defaultversion"
            result["related"] = {
                "defaultversion": self._materialize(owner + "/versions/" + default, pointer)
            }
            result["entity"]["defaultversionurl"] = "#" + pointer
        self.store.finish()
        return result

    def _effective(self, reference):
        record = self.read_record(reference["xid"])
        entity = copy.deepcopy(record["entity"])
        if record["kind"] == "resource":
            target = self._one_hop(entity["xid"])
            if target is not None:
                _, meta, _ = self._state(target)
                version = self.read_record(
                    target + "/versions/" + meta["entity"]["defaultversionid"]
                )
                entity = {**copy.deepcopy(version["entity"]), **entity}
        return entity

    def collection(self, xid, selector=None):
        index = self._index(xid)
        entries = index["entries"]
        if selector is not None:
            _require(isinstance(selector, dict) and set(selector) == {"label", "value"},
                     "Selector needs exactly label and value")
            match = select_label(
                [self._effective(reference) for reference in entries],
                selector["label"], selector["value"],
            )
            entries = [r for r in entries if r["xid"] == match["xid"]]
        result = {
            "kind": "collection", "xid": xid, "complete": True,
            "entities": {
                reference["xid"].rsplit("/", 1)[1]: self._materialize(
                    reference["xid"],
                    _pointer("/entities", reference["xid"].rsplit("/", 1)[1]),
                ) for reference in entries
            },
        }
        self.store.finish()
        return result

    def model(self):
        result = {"modelsource": copy.deepcopy(self.root["entity"]["modelsource"])}
        if "model" in self.root["entity"]:
            result["model"] = copy.deepcopy(self.root["entity"]["model"])
        if "resolvedmodelsource" in self.root:
            result["resolvedmodelsource"] = copy.deepcopy(self.root["resolvedmodelsource"])
        if "modelbase" in self.root:
            result["modelbase"] = self.root["modelbase"]
        self.store.finish()
        return result

    def capabilities(self):
        self.store.finish()
        return copy.deepcopy(self.root["entity"]["capabilities"])

    def validate(self):
        """Walk complete closure. Selective APIs deliberately do not do this."""
        counts = {"records": 0, "indexes": 0, "documents": 0}

        def walk(record):
            counts["records"] += 1
            xid = record["entity"]["xid"]
            if record["kind"] == "resource":
                _, meta, versions = self._state(xid)
                walk(meta)
                if versions is not None:
                    ancestors = {}
                    for child in versions["entries"]:
                        version = self.read_record(child["xid"])["entity"]
                        ancestors[version["versionid"]] = version["ancestorid"]
                    for version in ancestors:
                        visited = set()
                        current = version
                        while ancestors[current] != current:
                            _require(current not in visited, "Version ancestor cycle")
                            visited.add(current)
                            current = ancestors[current]
            if record["kind"] == "version" and record["document"]["kind"] == "local":
                self._bytes(record["document"])
                counts["documents"] += 1
            for reference in record.get("collections", []):
                index = self._read_ref(reference)
                counts["indexes"] += 1
                for child in index["entries"]:
                    walk(self.read_record(child["xid"]))

        walk(self.root)
        self.store.finish()
        return {
            **counts, "rootsha256": self.root_sha256,
            "completeness": self.root["snapshot"]["completeness"],
            "pin": self.store.pin,
        }


def encode_tree(records, documents):
    """Generate descriptor-linked fixture files from full metadata fragments."""
    source = {}
    for record in records:
        xid = record["entity"]["xid"]
        _require(xid not in source, "Duplicate fixture record")
        source[xid] = copy.deepcopy(record)
    _require("/" in source, "Fixture needs a Registry record")
    files = {".gitattributes": b"*.json text eol=lf\ndocuments/** -text\n"}
    paths = {
        xid: storage_path("records", number)
        for number, xid in enumerate(sorted(x for x in source if x != "/"))
    }
    paths["/"] = "registry.json"
    document_paths = {
        xid: storage_path("documents", number)
        for number, xid in enumerate(sorted(documents))
    }
    model = source["/"].get("resolvedmodelsource", source["/"]["entity"]["modelsource"])
    next_index = 0

    def reference(kind, xid, path, data):
        return {
            "kind": kind, "xid": xid, "href": path, "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }

    def index(xid):
        nonlocal next_index
        path = storage_path("indexes", next_index)
        next_index += 1
        children = [
            child for child in sorted(source)
            if child.rsplit("/", 1)[0] == xid and source[child]["kind"] != "meta"
        ]
        value = {
            "format": FORMAT, "formatversion": FORMAT_VERSION, "kind": "collection",
            "xid": xid, "count": len(children),
            "entries": [record(child) for child in children],
        }
        data = _json_bytes(value)
        files[path] = data
        return reference("collection", xid, path, data)

    def record(xid):
        _require(xid in source, "Missing fixture Meta record")
        value = copy.deepcopy(source[xid])
        kind = value["kind"]
        value = {"format": FORMAT, "formatversion": FORMAT_VERSION, **value}
        if kind == "registry":
            value["collections"] = [index("/" + name) for name in sorted(model.get("groups", {}))]
        elif kind == "group":
            group = model["groups"][xid.split("/")[1]]
            names = set(group.get("resources", {}))
            names.update(item.rsplit("/", 1)[1] for item in group.get("ximportresources", []))
            value["collections"] = [index(xid + "/" + name) for name in sorted(names)]
        elif kind == "resource":
            meta_xid = xid + "/meta"
            value["meta"] = record(meta_xid)
            value["collections"] = (
                [] if "xref" in source[meta_xid]["entity"]
                else [index(xid + "/versions")]
            )
        elif kind == "version" and xid in documents:
            content = documents[xid]
            _require(isinstance(content, bytes), "Fixture documents must be bytes")
            path = document_paths[xid]
            files[path] = content
            value["document"] = {
                **value.get("document", {}), "kind": "local", "href": path,
                "size": len(content), "sha256": hashlib.sha256(content).hexdigest(),
            }
        data = _json_bytes(value)
        files[paths[xid]] = data
        return reference(kind, xid, paths[xid], data)

    record("/")
    _require(all(path in files for path in paths.values()), "Unreachable fixture record")
    _require(all(path in files for path in document_paths.values()),
             "Unreachable fixture document")
    DocumentTree(MemoryStore(files)).validate()
    return files


def sample_records():
    """Return the deterministic shared oracle input and exact document bytes."""
    records = []
    timestamp = "2026-09-04T00:00:00Z"

    def add(kind, xid, entity, **extra):
        value = {"xid": xid, **entity}
        if kind in ("registry", "group", "version") or kind == "meta" and "xref" not in value:
            value = {"epoch": 1, "createdat": timestamp, "modifiedat": timestamp, **value}
        records.append({"kind": kind, "entity": value, **extra})

    model = {
        "attributes": {"fixture": {"type": "string"}},
        "groups": {
            "categories": {
                "singular": "category",
                "resources": {"registries": {
                    "singular": "registry", "hasdocument": False,
                    "attributes": {"weburl": {"type": "url"}},
                }},
            },
            "documents": {
                "singular": "document",
                "resources": {
                    "assets": {
                        "singular": "asset",
                        "attributes": {"purpose": {"type": "string"}},
                    },
                    "notes": {"singular": "note", "hasdocument": False},
                },
            },
            "independent": {
                "singular": "independent",
                "resources": {"assets": {"singular": "asset"}},
            },
            "mirrors": {
                "singular": "mirror", "ximportresources": ["/documents/assets"],
            },
        },
    }
    add("registry", "/", {
        "registryid": "first", "specversion": CORE_VERSION,
        "fixture": "document-tree", "modelsource": model,
        "capabilities": {
            "available": {
                name: {"mutable": False} for name in
                ("capabilities", "entities", "model", "modelsource")
            },
            "flags": ["doc", "inline"], "pagination": False,
            "shortself": False, "specversions": [CORE_VERSION],
        },
    }, snapshot={"scope": "/", "completeness": "offline-complete"},
        source={"uri": "https://example.com/registry", "revision": "fixture-1"})
    for group_type, group_id in (
        ("categories", "main"), ("documents", "main"),
        ("independent", "MAIN"), ("mirrors", "local"),
    ):
        add("group", f"/{group_type}/{group_id}", {
            model["groups"][group_type]["singular"] + "id": group_id,
        })

    for xid, singular, default in (
        ("/documents/main/assets/item", "asset", "v1"),
        ("/documents/main/assets/CON", "asset", "a:b@c."),
        ("/documents/main/notes/item", "note", "v1"),
        ("/categories/main/registries/site", "registry", "v1"),
    ):
        identity = {singular + "id": xid.rsplit("/", 1)[1]}
        add("resource", xid, identity)
        add("meta", xid + "/meta", {
            **identity, "readonly": True,
            "defaultversionid": default, "defaultversionsticky": True,
        })
    for alias, target in (
        ("copy", "/documents/main/assets/item"),
        ("dangling", "/documents/main/assets/missing"),
        ("chain", "/mirrors/local/assets/copy"),
    ):
        xid = "/mirrors/local/assets/" + alias
        add("resource", xid, {"assetid": alias})
        add("meta", xid + "/meta", {"assetid": alias, "xref": target})

    for version, default, ancestor, labels in (
        ("v1", True, "v1", {"stage": "production", "note": ""}),
        ("v2", False, "v1", {"stage": "development"}),
    ):
        add("version", "/documents/main/assets/item/versions/" + version, {
            "assetid": "item", "versionid": version, "isdefault": default,
            "ancestorid": ancestor, "labels": labels,
            "contenttype": "application/json" if version == "v1" else "application/octet-stream",
            "purpose": "primary" if default else "empty",
        })
    binary_xid = "/documents/main/assets/CON/versions/a:b@c."
    add("version", binary_xid, {
        "assetid": "CON", "versionid": "a:b@c.", "isdefault": True,
        "ancestorid": "a:b@c.", "contenttype": "application/octet-stream",
    })
    add("version", "/documents/main/notes/item/versions/v1", {
        "noteid": "item", "versionid": "v1", "isdefault": True,
        "ancestorid": "v1", "labels": {"note": ""},
    }, document={"kind": "none"})
    add("version", "/categories/main/registries/site/versions/v1", {
        "registryid": "site", "versionid": "v1", "isdefault": True,
        "ancestorid": "v1", "weburl": "https://example.com/cataloged-registry",
    }, document={"kind": "none"})
    documents = {
        "/documents/main/assets/item/versions/v1": b'{"hello":"world"}\n',
        "/documents/main/assets/item/versions/v2": b"",
        binary_xid: b"\x00\x01\xff\x7f\n",
    }
    return records, documents


def write_sample(root):
    """Write generated fixture bytes. Refuse to overwrite different content."""
    files = encode_tree(*sample_records())
    root = Path(root).absolute()
    root.mkdir(parents=True, exist_ok=True)
    _checked_path(root, directory=True)
    for name, data in files.items():
        path = root.joinpath(*name.split("/"))
        if path.exists():
            _checked_path(path)
            _require(path.read_bytes() == data, "Existing fixture differs; use an empty root")
    for name, data in files.items():
        path = root.joinpath(*name.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        _checked_path(path.parent, directory=True)
        if not path.exists():
            with path.open("xb") as output:
                output.write(data)
    return DocumentTree(FileStore(root)).validate()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=(
        "build-sample", "validate", "entity", "collection", "document",
        "descriptor", "model", "capabilities",
    ))
    parser.add_argument("root", nargs="?")
    parser.add_argument("target", nargs="?", default="/")
    parser.add_argument("--target", dest="selected_target")
    parser.add_argument("--git-dir")
    parser.add_argument("--revision")
    parser.add_argument("--path", default="xregistry")
    parser.add_argument("--label")
    parser.add_argument("--value")
    parser.add_argument("--max-file-bytes", type=int, default=16 * 1024 * 1024)
    args = parser.parse_args(argv)
    try:
        if args.operation == "build-sample":
            _require(args.root is not None and args.git_dir is None,
                     "build-sample needs a filesystem destination")
            result = write_sample(args.root)
        else:
            if args.git_dir:
                _require(args.revision is not None and args.root is None,
                         "Git reads need --revision and no filesystem root")
                store = GitStore(
                    args.git_dir, args.revision, args.path,
                    max_file_bytes=args.max_file_bytes,
                )
            else:
                _require(args.root is not None, "Missing document-tree directory")
                _require(args.revision is None, "File reads do not accept --revision")
                store = FileStore(args.root, max_file_bytes=args.max_file_bytes)
            tree = DocumentTree(store)
            _require(args.selected_target is None or args.target == "/",
                     "Specify the target only once")
            target = args.selected_target if args.selected_target is not None else args.target
            _require((args.label is None) == (args.value is None),
                     "Both --label and --value are needed")
            _require(args.label is None or args.operation == "collection",
                     "Label selector only applies to collections")
            if args.operation in ("model", "capabilities"):
                _require(target == "/", "Model/capabilities target must be /")
                result = (
                    tree.model() if args.operation == "model"
                    else {"capabilities": tree.capabilities()}
                )
            elif args.operation == "entity":
                result = tree.metadata(target)
            elif args.operation == "collection":
                selector = None if args.label is None else {
                    "label": args.label, "value": args.value,
                }
                result = tree.collection(target, selector)
            elif args.operation in ("document", "descriptor"):
                descriptor = tree.document_descriptor(target)
                result = {"document": descriptor}
                if args.operation == "document" and descriptor["kind"] == "local":
                    result["base64"] = base64.b64encode(tree.document(target)).decode("ascii")
            else:
                result = tree.validate()
            result["reads"] = tree.reads
            result["origin"] = {
                "pin": store.pin, "rootsha256": tree.root_sha256,
                "immutable": isinstance(store, GitStore),
                "target": target,
            }
            if isinstance(store, GitStore):
                result["origin"].update(
                    objectstore=str(store.git_dir),
                    requestedrevision=store.revision, path=store.path,
                )
            else:
                result["origin"].update(
                    endpoint=store.root.as_uri(), layout="document-tree",
                )
        print(json.dumps(result, indent=2))
        return 0
    except FederationError as error:
        print(json.dumps({"error": error.code, "message": str(error)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
