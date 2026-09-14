"""Lossless xRegistry scalar representations and exact Core JSON values."""

import copy
import hashlib
import io
import json
import re
from dataclasses import dataclass
from decimal import Decimal


PROFILE_KEY = "x-xregistryProjection"
SCALAR_KEY = "x-xregistryScalar"
OPTIONAL_KEY = "x-xregistryOptional"
TREE_KEY = "x-xregistryScalarTree"
JSON_CARRIER_KEY = "x-xregistryJsonCarrier"
INTERNAL_KEY = "x-xregistryInternal"
ABSENT_KEY = "x-xregistryAbsent"
PROFILE_ID = "https://xregistry.io/profiles/scalar-projection/1"
SCALAR_TYPES = frozenset(("integer", "uinteger", "decimal", "timestamp"))


class ProjectionError(ValueError):
    """A value or contract does not satisfy the scalar projection profile."""


class ResourceLimitError(ProjectionError):
    """A valid value cannot be processed within the caller's resource budget."""


class ProfileMismatchError(ProjectionError):
    """The complete writer contract differs from the reader's pinned contract."""


class MigrationError(ProjectionError):
    """Legacy data needs an explicit migration or authoritative re-encoding."""


@dataclass(frozen=True)
class Limits:
    max_bytes: int = 16 * 1024 * 1024
    max_scalar_chars: int = 1000000
    max_depth: int = 128

    def __post_init__(self):
        for name in ("max_bytes", "max_scalar_chars", "max_depth"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f"{name} must be a positive integer")


DEFAULT_LIMITS = Limits()
_NUMBER = re.compile(
    r"(?P<sign>-?)(?P<whole>0|[1-9][0-9]*)"
    r"(?:\.(?P<fraction>[0-9]+))?(?:[eE](?P<exponent>[+-]?[0-9]+))?"
)
_TIMESTAMP = re.compile(
    r"(?P<year>[0-9]{4})-(?P<month>[0-9]{2})-(?P<day>[0-9]{2})[Tt]"
    r"(?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}):(?P<second>[0-9]{2})"
    r"(?:\.(?P<fraction>[0-9]+))?"
    r"(?P<offset>[Zz]|[+-][0-9]{2}:[0-9]{2})"
)
_PROFILE_JSON = json.dumps({
    "id": PROFILE_ID,
    "version": "1",
    "numbers": "exact-json-number-token; mathematical coefficient/exponent",
    "timestamps": "rfc3339-text; exact fraction and explicit UTC normalization",
    "avroOptionalScalars": "absent-record, null, or string",
    "avroGenericValues": "GenericRecord.object.json contains exact Core JSON",
    "constraints": "typed enum and bounds; no lexical numeric comparison",
    "identity": "sha256 of complete profile, dialect and writer schema",
    "defaults": "target-typed reader defaults; not implicit writer values",
}, sort_keys=True)


def projection_profile():
    """Return an independent copy of the immutable version-1 profile."""
    return json.loads(_PROFILE_JSON)


def _integer_from_digits(text):
    sign = -1 if text.startswith("-") else 1
    text = text.lstrip("+-")
    result = 0
    for index in range(0, len(text), 9):
        part = text[index:index + 9]
        result = result * 10 ** len(part) + int(part)
    return sign * result


def _integer_text(value):
    if value == 0:
        return "0"
    sign = "-" if value < 0 else ""
    value = abs(value)
    parts = []
    while value:
        value, part = divmod(value, 1000000000)
        parts.append(part)
    return sign + str(parts[-1]) + "".join(
        f"{part:09d}" for part in reversed(parts[:-1])
    )


@dataclass(frozen=True, eq=False)
class JsonNumber:
    """An immutable JSON number token, not a Core string or binary float."""

    token: str

    def __post_init__(self):
        if type(self.token) is not str or _NUMBER.fullmatch(self.token) is None:
            raise ProjectionError("Invalid JSON number token")

    def _parts(self):
        match = _NUMBER.fullmatch(self.token)
        fraction = match["fraction"] or ""
        digits = (match["whole"] + fraction).lstrip("0")
        if not digits:
            return 0, "0", 0
        coefficient = digits.rstrip("0")
        exponent = (
            _integer_from_digits(match["exponent"] or "0") - len(fraction)
            + len(digits) - len(coefficient)
        )
        return (-1 if match["sign"] else 1), coefficient, exponent

    @property
    def is_integer(self):
        sign, _, exponent = self._parts()
        return sign == 0 or exponent >= 0

    def __eq__(self, other):
        if isinstance(other, JsonNumber) or type(other) is int:
            return compare_numbers(self, other) == 0
        if isinstance(other, Decimal) and other.is_finite():
            return compare_numbers(self, other) == 0
        return NotImplemented

    def __bool__(self):
        return self._parts()[0] != 0

    __hash__ = None


def _number(value, limits=DEFAULT_LIMITS):
    if isinstance(value, JsonNumber):
        result = value
    elif type(value) is int:
        if value.bit_length() > 4 * limits.max_scalar_chars:
            raise ResourceLimitError("Numeric scalar exceeds the text budget")
        result = JsonNumber(_integer_text(value))
    elif isinstance(value, Decimal) and value.is_finite():
        result = JsonNumber(str(value))
    else:
        raise ProjectionError(
            "Expected an exact Core JSON number; use parse_core_json, int or "
            "Decimal, never a string, boolean or binary float"
        )
    if len(result.token) > limits.max_scalar_chars:
        raise ResourceLimitError("Numeric scalar exceeds the text budget")
    return result


def compare_numbers(left, right, *, limits=DEFAULT_LIMITS):
    left_sign, left_digits, left_exponent = _number(left, limits)._parts()
    right_sign, right_digits, right_exponent = _number(right, limits)._parts()
    if left_sign != right_sign:
        return (left_sign > right_sign) - (left_sign < right_sign)
    if left_sign == 0:
        return 0
    left_size = len(left_digits) + left_exponent
    right_size = len(right_digits) + right_exponent
    if left_size != right_size:
        return left_sign * ((left_size > right_size) - (left_size < right_size))
    width = max(len(left_digits), len(right_digits))
    left_digits = left_digits.ljust(width, "0")
    right_digits = right_digits.ljust(width, "0")
    return left_sign * (
        (left_digits > right_digits) - (left_digits < right_digits)
    )


def _days_before_year(year):
    previous = year - 1
    return (
        365 * previous + previous // 4 - previous // 100 + previous // 400
    )


def _month_lengths(year):
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    return (31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def _calendar_day(ordinal):
    if not _days_before_year(0) <= ordinal < _days_before_year(10000):
        raise ProjectionError("UTC normalization exceeds RFC3339's year syntax")
    low, high = 0, 10000
    while high - low > 1:
        middle = (low + high) // 2
        if _days_before_year(middle) <= ordinal:
            low = middle
        else:
            high = middle
    remaining = ordinal - _days_before_year(low)
    for month, length in enumerate(_month_lengths(low), 1):
        if remaining < length:
            return low, month, remaining + 1
        remaining -= length
    raise ProjectionError("Invalid Gregorian day")


def _timestamp_parts(value, limits):
    if type(value) is not str:
        raise ProjectionError("A timestamp must be complete RFC3339 text")
    if len(value) > limits.max_scalar_chars:
        raise ResourceLimitError("Timestamp scalar exceeds the text budget")
    match = _TIMESTAMP.fullmatch(value)
    if match is None:
        raise ProjectionError("Invalid RFC3339 timestamp syntax")
    year, month, day, hour, minute, second = (
        int(match[name])
        for name in ("year", "month", "day", "hour", "minute", "second")
    )
    if not 1 <= month <= 12 or not 1 <= day <= _month_lengths(year)[month - 1]:
        raise ProjectionError("Invalid RFC3339 calendar date")
    if hour > 23 or minute > 59 or second > 60:
        raise ProjectionError("Invalid RFC3339 clock time")
    offset = match["offset"]
    offset_seconds = 0
    if offset not in ("Z", "z"):
        offset_hour, offset_minute = int(offset[1:3]), int(offset[4:6])
        if offset_hour > 23 or offset_minute > 59:
            raise ProjectionError("Invalid RFC3339 UTC offset")
        offset_seconds = (offset_hour * 3600 + offset_minute * 60) * (
            -1 if offset[0] == "-" else 1
        )
    ordinal = (
        _days_before_year(year) + sum(_month_lengths(year)[:month - 1]) + day - 1
    )
    seconds = (
        ordinal * 86400 + hour * 3600 + minute * 60 + min(second, 59)
        - offset_seconds
    )
    if second == 60:
        utc_day, utc_second = divmod(seconds, 86400)
        utc_year, utc_month, utc_date = _calendar_day(utc_day)
        if (utc_second != 86399
                or utc_date != _month_lengths(utc_year)[utc_month - 1]):
            raise ProjectionError("Invalid RFC3339 leap-second position")
    return seconds, second == 60, match["fraction"] or ""


def normalize_timestamp(value, *, limits=DEFAULT_LIMITS):
    """Normalize to UTC without passing fractional seconds through datetime."""
    seconds, leap_second, fraction = _timestamp_parts(value, limits)
    ordinal, clock = divmod(seconds, 86400)
    year, month, day = _calendar_day(ordinal)
    hour, clock = divmod(clock, 3600)
    minute, second = divmod(clock, 60)
    if leap_second:
        second = 60
    return (
        f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}"
        + ("." + fraction if fraction else "") + "Z"
    )


def compare_timestamps(left, right, *, limits=DEFAULT_LIMITS):
    left_seconds, left_leap, left_fraction = _timestamp_parts(left, limits)
    right_seconds, right_leap, right_fraction = _timestamp_parts(right, limits)
    left_base = left_seconds, left_leap
    right_base = right_seconds, right_leap
    if left_base != right_base:
        return (left_base > right_base) - (left_base < right_base)
    width = max(len(left_fraction), len(right_fraction))
    left_fraction = left_fraction.ljust(width, "0")
    right_fraction = right_fraction.ljust(width, "0")
    return (
        (left_fraction > right_fraction) - (left_fraction < right_fraction)
    )


def _check_tree(value, limits, depth=0):
    if depth > limits.max_depth:
        raise ResourceLimitError("JSON nesting exceeds the depth budget")
    if isinstance(value, JsonNumber):
        _number(value, limits)
    elif isinstance(value, dict):
        for child in value.values():
            _check_tree(child, limits, depth + 1)
    elif isinstance(value, list):
        for child in value:
            _check_tree(child, limits, depth + 1)


def parse_core_json(text, *, limits=DEFAULT_LIMITS):
    """Read JSON without discarding number tokens or accepting NaN/Infinity."""
    if isinstance(text, bytes):
        if len(text) > limits.max_bytes:
            raise ResourceLimitError("JSON exceeds the byte budget")
        text = text.decode("utf-8")
    if type(text) is not str:
        raise ProjectionError("Core JSON input must be text or UTF-8 bytes")
    if len(text.encode("utf-8")) > limits.max_bytes:
        raise ResourceLimitError("JSON exceeds the byte budget")

    def number(token):
        if len(token) > limits.max_scalar_chars:
            raise ResourceLimitError("Numeric scalar exceeds the text budget")
        return JsonNumber(token)

    def reject_constant(token):
        raise ProjectionError(f"Nonfinite JSON number is not permitted: {token}")

    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ProjectionError(f"Duplicate JSON member: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(
            text, parse_int=number, parse_float=number,
            parse_constant=reject_constant, object_pairs_hook=object_pairs,
        )
    except json.JSONDecodeError as error:
        raise ProjectionError(f"Invalid Core JSON: {error.msg}") from error
    except RecursionError as error:
        raise ResourceLimitError("JSON parser depth budget exceeded") from error
    _check_tree(value, limits)
    return value


def dump_core_json(value, *, indent=None, sort_keys=False, limits=DEFAULT_LIMITS):
    """Serialize exact numeric values as JSON numbers, never quoted tokens."""
    if indent is not None and (type(indent) is not int or indent < 0):
        raise ValueError("indent must be a nonnegative integer or None")

    def visit(node, depth):
        if depth > limits.max_depth:
            raise ResourceLimitError("JSON nesting exceeds the depth budget")
        if node is None or type(node) in (str, bool):
            return json.dumps(node)
        if isinstance(node, (JsonNumber, Decimal)) or type(node) is int:
            return _number(node, limits).token
        if not isinstance(node, (dict, list)):
            raise ProjectionError(f"Unsupported Core JSON kind: {type(node).__name__}")
        if isinstance(node, dict):
            if any(type(key) is not str for key in node):
                raise ProjectionError("JSON object keys must be strings")
            keys = sorted(node) if sort_keys else node
            parts = [
                json.dumps(key) + (": " if indent is not None else ":")
                + visit(node[key], depth + 1)
                for key in keys
            ]
            opening, closing = "{", "}"
        else:
            parts = [visit(child, depth + 1) for child in node]
            opening, closing = "[", "]"
        if not parts:
            return opening + closing
        if indent is None:
            return opening + ",".join(parts) + closing
        padding = " " * (indent * (depth + 1))
        return (
            opening + "\n" + padding + (",\n" + padding).join(parts)
            + "\n" + " " * (indent * depth) + closing
        )

    result = visit(value, 0)
    if len(result.encode("utf-8")) > limits.max_bytes:
        raise ResourceLimitError("JSON exceeds the byte budget")
    return result


def _contract_parts(contract):
    if type(contract) is not dict or set(contract) != {
        "coreType", "encoding", "constraints"
    }:
        raise ProfileMismatchError("Incomplete or unknown scalar contract")
    kind = contract["coreType"]
    if kind not in SCALAR_TYPES:
        raise ProfileMismatchError(f"Unknown Core scalar kind: {kind}")
    encoding = "rfc3339-text" if kind == "timestamp" else "json-number-token"
    if contract.get("encoding") != encoding:
        raise ProfileMismatchError("Unknown or inconsistent scalar encoding")
    constraints = contract["constraints"]
    if type(constraints) is not dict or set(constraints) - {
        "enum", "strict", "minimum", "maximum"
    }:
        raise ProfileMismatchError("Unknown scalar constraint")
    if type(constraints.get("strict", True)) is not bool:
        raise ProfileMismatchError("The strict constraint must be boolean")
    if "enum" in constraints and (
        type(constraints["enum"]) is not list
        or any(type(item) is not str for item in constraints["enum"])
    ):
        raise ProfileMismatchError("Scalar enum constraints must be typed text")
    if any(type(constraints[name]) is not str for name in ("minimum", "maximum")
           if name in constraints):
        raise ProfileMismatchError("Scalar bounds must be typed text")
    return kind, constraints


def _validate_scalar(value, contract, limits):
    kind, constraints = _contract_parts(contract)
    if kind == "timestamp":
        _timestamp_parts(value, limits)
        compare = lambda other: compare_timestamps(value, other, limits=limits)
        token = value
    else:
        value = _number(value, limits)
        sign, _, _ = value._parts()
        if kind in ("integer", "uinteger") and not value.is_integer:
            raise ProjectionError(f"Expected a mathematical {kind}")
        if kind == "uinteger" and sign < 0:
            raise ProjectionError("Unsigned integer must not be negative")
        compare = lambda other: compare_numbers(
            value, JsonNumber(other), limits=limits
        )
        token = value.token
    enum = constraints.get("enum", [])
    if enum and constraints.get("strict", True):
        if not any(compare(item) == 0 for item in enum):
            raise ProjectionError("Scalar is not a permitted enum value")
    for key, wanted in (("minimum", -1), ("maximum", 1)):
        if key in constraints and compare(constraints[key]) == wanted:
            raise ProjectionError(f"Scalar violates {key}")
    return token


def encode_scalar(value, contract, *, limits=DEFAULT_LIMITS):
    """Validate a Core scalar and return its lossless physical string."""
    return _validate_scalar(value, contract, limits)


def decode_scalar(value, contract, *, limits=DEFAULT_LIMITS):
    """Validate a physical string and restore its exact Core scalar kind."""
    if type(value) is not str:
        raise ProjectionError("A projected scalar must be a physical string")
    restored = value if contract.get("coreType") == "timestamp" else JsonNumber(value)
    _validate_scalar(restored, contract, limits)
    return restored


def scalar_schema(definition, dialect, *, optional=False):
    """Generate the physical scalar type and its enforced semantic contract."""
    kind = definition["type"]
    if kind not in SCALAR_TYPES:
        raise ProjectionError(f"Unsupported scalar kind: {kind}")
    if dialect not in ("avro", "json-structure"):
        raise ProjectionError(f"Unsupported scalar projection dialect: {dialect}")
    contract = {
        "coreType": kind,
        "encoding": "rfc3339-text" if kind == "timestamp" else "json-number-token",
        "constraints": {},
    }
    constraints = {}
    for name in ("enum", "minimum", "maximum"):
        if name in definition:
            value = definition[name]
            constraints[name] = (
                [encode_scalar(item, contract) for item in value]
                if name == "enum" else (
                    encode_scalar(value, contract) if kind == "timestamp"
                    else _number(value).token
                )
            )
    if "strict" in definition:
        if type(definition["strict"]) is not bool:
            raise ProjectionError("The strict constraint must be boolean")
        constraints["strict"] = definition["strict"]
    contract["constraints"] = constraints
    schema = {
        "type": "datetime" if dialect == "json-structure" and kind == "timestamp"
        else "string",
        SCALAR_KEY: contract,
    }
    if optional:
        schema[OPTIONAL_KEY] = True
        if dialect == "json-structure":
            schema["type"] = [schema["type"], "null"]
    if "description" in definition:
        schema["description" if dialect == "json-structure" else "doc"] = (
            definition["description"]
        )
    if "default" in definition:
        schema["default"] = encode_scalar(definition["default"], contract)
    return schema


def scalar_tree(definition, *, item=False):
    """Retain typed scalar rules inside legacy opaque structured values."""
    kind = definition.get("type")
    optional = not item and not definition.get("required", False)
    if kind in ("any", "var"):
        return {"type": "any", "optional": optional}
    if kind in SCALAR_TYPES:
        schema = scalar_schema(definition, "avro", optional=optional)
        result = {"scalar": schema[SCALAR_KEY], "optional": optional}
        if "default" in schema:
            result["default"] = schema["default"]
        return result
    if kind == "object":
        properties = {}
        for name, child in definition.get("attributes", {}).items():
            tree = scalar_tree(child)
            if tree is not None:
                properties[name] = tree
        if properties:
            return {"type": "object", "properties": properties, "optional": optional}
    if kind in ("map", "array"):
        child = scalar_tree(definition.get("item", {}), item=True)
        if child is not None:
            return {"type": kind, "item": child, "optional": optional}
    return None


def uses_scalar_carrier(definition):
    kind = definition.get("type")
    if kind in ("any", "var"):
        return True
    if kind == "object":
        return scalar_tree(definition) is not None
    if kind in ("map", "array"):
        return uses_scalar_carrier(definition.get("item", {}))
    return False


def finish_avro_schema(schema):
    """Bind the profile and represent missing optional scalars explicitly."""
    def visit(node, namespace=""):
        if isinstance(node, list):
            for child in node:
                visit(child, namespace)
            return
        if not isinstance(node, dict):
            return
        kind = node.get("type")
        if kind == "record":
            name = node["name"]
            full_name = (
                name if "." in name
                else ".".join(filter(None, (node.get("namespace", namespace), name)))
            )
            namespace = full_name.rpartition(".")[0]
            if full_name == "io.xregistry.GenericRecord":
                node[JSON_CARRIER_KEY] = "core-json/1"
            for field in node["fields"]:
                if field["name"] == "genericRecordDefinition":
                    field[INTERNAL_KEY] = True
                if SCALAR_KEY in field and field.get(OPTIONAL_KEY):
                    absent = {
                        "type": "record",
                        "name": full_name + "_" + field["name"] + "_AbsentV1",
                        "fields": [],
                        ABSENT_KEY: PROFILE_ID,
                    }
                    if "default" in field:
                        field["type"] = ["string", "null", absent]
                    else:
                        field["type"] = [absent, "null", "string"]
                        field["default"] = {}
                visit(field["type"], namespace)
        elif kind == "array":
            visit(node["items"], namespace)
        elif kind == "map":
            visit(node["values"], namespace)
        elif isinstance(kind, (dict, list)):
            visit(kind, namespace)

    visit(schema)
    schema[PROFILE_KEY] = projection_profile()
    return schema


_MISSING = object()
_CONTRACT_META = "xregistry.scalarProjection"


def _validate_tree(value, tree, limits, depth=0):
    if depth > limits.max_depth:
        raise ResourceLimitError("Scalar tree exceeds the depth budget")
    if value is _MISSING or value is None:
        if tree.get("optional"):
            return
        raise ProjectionError("A required scalar or owner is missing or null")
    if "scalar" in tree:
        encode_scalar(value, tree["scalar"], limits=limits)
        return
    kind = tree["type"]
    if kind == "object":
        if type(value) is not dict:
            raise ProjectionError("Expected a Core object")
        for name, child in tree["properties"].items():
            if name == "*":
                for key in value.keys() - tree["properties"].keys():
                    _validate_tree(value[key], child, limits, depth + 1)
            else:
                _validate_tree(value.get(name, _MISSING), child, limits, depth + 1)
    elif kind == "map":
        if type(value) is not dict or any(type(key) is not str for key in value):
            raise ProjectionError("Expected a Core map with string keys")
        for child in value.values():
            _validate_tree(child, tree["item"], limits, depth + 1)
    elif kind == "array":
        if type(value) is not list:
            raise ProjectionError("Expected a Core array")
        for child in value:
            _validate_tree(child, tree["item"], limits, depth + 1)
    elif kind == "any":
        dump_core_json(value, limits=limits)
    else:
        raise ProfileMismatchError(f"Unknown scalar-tree type: {kind}")


def _canonical(value, limits=DEFAULT_LIMITS):
    return dump_core_json(value, sort_keys=True, limits=limits)


def _fingerprint(body, limits=DEFAULT_LIMITS):
    return "sha256:" + hashlib.sha256(_canonical(body, limits).encode("utf-8")).hexdigest()


def _validate_contract_definition(contract, limits):
    kind, constraints = _contract_parts(contract)
    bare = {**contract, "constraints": {}}
    for token in constraints.get("enum", []):
        decode_scalar(token, bare, limits=limits)
    for name in ("minimum", "maximum"):
        if name in constraints:
            if kind == "timestamp":
                decode_scalar(constraints[name], bare, limits=limits)
            else:
                _number(JsonNumber(constraints[name]), limits)


def _validate_tree_definition(tree, limits, depth=0):
    if depth > limits.max_depth:
        raise ResourceLimitError("Scalar contract tree exceeds the depth budget")
    if type(tree) is not dict or type(tree.get("optional")) is not bool:
        raise ProfileMismatchError("Invalid scalar-tree presence contract")
    if "scalar" in tree:
        _validate_contract_definition(tree["scalar"], limits)
        if "default" in tree:
            decode_scalar(tree["default"], tree["scalar"], limits=limits)
        return
    kind = tree.get("type")
    if kind == "object" and type(tree.get("properties")) is dict:
        for child in tree["properties"].values():
            _validate_tree_definition(child, limits, depth + 1)
    elif kind in ("map", "array") and "item" in tree:
        _validate_tree_definition(tree["item"], limits, depth + 1)
    elif kind != "any":
        raise ProfileMismatchError("Unknown scalar-tree contract")


def _structure_map_max_entries(node, features, limits):
    if "maxEntries" not in node:
        return None
    if not isinstance(features, list) or "JSONStructureValidation" not in features:
        raise ProfileMismatchError("maxEntries requires JSONStructureValidation")
    try:
        bound = _number(node["maxEntries"], limits)
    except ResourceLimitError:
        raise
    except ProjectionError as error:
        raise ProfileMismatchError("maxEntries must be a nonnegative integer") from error
    if not bound.is_integer or compare_numbers(bound, 0, limits=limits) < 0:
        raise ProfileMismatchError("maxEntries must be a nonnegative integer")
    return bound


def _validate_schema_annotations(node, dialect, limits, depth=0, structure_features=None):
    if depth > limits.max_depth:
        raise ResourceLimitError("Writer schema exceeds the depth budget")
    if structure_features is None:
        structure_features = node.get("$uses", []) if isinstance(node, dict) else []
    if isinstance(node, list):
        for child in node:
            _validate_schema_annotations(child, dialect, limits, depth + 1, structure_features)
    elif isinstance(node, dict):
        if dialect == "json-structure" and node.get("type") == "map":
            _structure_map_max_entries(node, structure_features, limits)
        if SCALAR_KEY in node:
            contract = node[SCALAR_KEY]
            _validate_contract_definition(contract, limits)
            if OPTIONAL_KEY in node and type(node[OPTIONAL_KEY]) is not bool:
                raise ProfileMismatchError("Invalid optional-scalar annotation")
            optional = node.get(OPTIONAL_KEY, False)
            physical = node.get("type")
            expected = (
                "datetime" if dialect == "json-structure"
                and contract["coreType"] == "timestamp" else "string"
            )
            if dialect == "json-structure":
                if physical != expected and not (
                    optional and isinstance(physical, list) and len(physical) == 2
                    and set(physical) == {expected, "null"}
                ):
                    raise ProfileMismatchError("Scalar annotation and physical type disagree")
            elif physical != "string" and not (
                optional and isinstance(physical, list)
            ):
                raise ProfileMismatchError("Projected Avro scalar must use string")
            if "default" in node and not (
                dialect == "avro" and optional and node["default"] == {}
            ):
                decode_scalar(node["default"], contract, limits=limits)
        if TREE_KEY in node:
            _validate_tree_definition(node[TREE_KEY], limits)
        if JSON_CARRIER_KEY in node and node[JSON_CARRIER_KEY] != "core-json/1":
            raise ProfileMismatchError("Unknown generic JSON carrier annotation")
        for child in node.values():
            _validate_schema_annotations(child, dialect, limits, depth + 1, structure_features)


class ProjectionCodec:
    """A pinned, complete writer contract and its typed reader/writer adapters."""

    def __init__(self, schema, dialect, *, limits=DEFAULT_LIMITS):
        if dialect not in ("avro", "json-structure"):
            raise ProjectionError(f"Unsupported projection dialect: {dialect}")
        if type(schema) is not dict or schema.get(PROFILE_KEY) != projection_profile():
            raise ProfileMismatchError("Unknown or altered scalar projection profile")
        self._limits = limits
        self._dialect = dialect
        self._schema_json = _canonical(schema, limits)
        self._schema = parse_core_json(self._schema_json, limits=limits)
        _validate_schema_annotations(self._schema, dialect, limits)
        body = {
            "profile": projection_profile(), "dialect": dialect,
            "schema": self._schema,
        }
        self._body_json = _canonical(body, limits)
        self._fingerprint = _fingerprint(body, limits)
        if dialect == "avro":
            import avro.schema
            self._avro_schema = avro.schema.parse(self._schema_json)
            self._validate_avro_bindings(self._avro_schema, set())

    @property
    def fingerprint(self):
        return self._fingerprint

    @property
    def schema(self):
        return parse_core_json(self._schema_json, limits=self._limits)

    @property
    def artifact(self):
        body = parse_core_json(self._body_json, limits=self._limits)
        return {**body, "fingerprint": self._fingerprint}

    @classmethod
    def from_artifact(cls, artifact, *, limits=DEFAULT_LIMITS):
        if type(artifact) is not dict or set(artifact) != {
            "profile", "dialect", "schema", "fingerprint"
        }:
            raise ProfileMismatchError("A complete writer artifact is required")
        body = {key: value for key, value in artifact.items() if key != "fingerprint"}
        if artifact["profile"] != projection_profile():
            raise ProfileMismatchError("Unknown or altered semantic profile")
        if _fingerprint(body, limits) != artifact["fingerprint"]:
            raise ProfileMismatchError("Writer artifact fingerprint does not match")
        codec = cls(artifact["schema"], artifact["dialect"], limits=limits)
        if codec.fingerprint != artifact["fingerprint"]:
            raise ProfileMismatchError("Writer schema and semantic profile differ")
        return codec

    def _check_artifact(self, artifact):
        other = self.from_artifact(artifact, limits=self._limits)
        if other.fingerprint != self.fingerprint:
            raise ProfileMismatchError("Data uses a different complete writer contract")

    def _validate_avro_bindings(self, node, visited):
        identity = id(node)
        if identity in visited:
            return
        visited.add(identity)
        if node.type == "record":
            if node.get_prop(JSON_CARRIER_KEY):
                return
            for field in node.fields:
                contract = field.get_prop(SCALAR_KEY)
                if contract:
                    if field.get_prop(OPTIONAL_KEY):
                        if node.type != "record" or field.type.type != "union":
                            raise ProfileMismatchError("Optional scalar needs an absence union")
                        branches = field.type.schemas
                        absent = [part for part in branches if part.get_prop(ABSENT_KEY)]
                        if (len(branches) != 3 or len(absent) != 1
                                or absent[0].type != "record" or absent[0].fields
                                or absent[0].get_prop(ABSENT_KEY) != PROFILE_ID
                                or {part.type for part in branches} != {
                                    "record", "null", "string"
                                }):
                            raise ProfileMismatchError("Invalid scalar absence union")
                        if not field.has_default:
                            raise ProfileMismatchError("Optional scalar needs a reader default")
                    elif field.type.type != "string":
                        raise ProfileMismatchError("Projected Avro scalars must use strings")
                    if field.has_default and field.default != {}:
                        decode_scalar(field.default, contract, limits=self._limits)
                self._validate_avro_bindings(field.type, visited)
        elif node.type == "array":
            self._validate_avro_bindings(node.items, visited)
        elif node.type == "map":
            self._validate_avro_bindings(node.values, visited)
        elif node.type == "union":
            for branch in node.schemas:
                self._validate_avro_bindings(branch, visited)

    def _field_scalar(self, value, contract, optional, writing):
        if value is _MISSING:
            if writing and optional:
                return {}
            raise ProjectionError("A required scalar is missing; reader defaults are not writer values")
        if value is None:
            if optional:
                return None
            raise ProjectionError("A required scalar must not be null")
        if not writing and value == {}:
            if optional:
                return _MISSING
            raise ProjectionError("A required scalar cannot be absent")
        operation = encode_scalar if writing else decode_scalar
        return operation(value, contract, limits=self._limits)

    def _avro_value(self, node, value, writing, depth=0):
        if depth > self._limits.max_depth:
            raise ResourceLimitError("Avro value exceeds the depth budget")
        contract = node.get_prop(SCALAR_KEY)
        if contract:
            operation = encode_scalar if writing else decode_scalar
            return operation(value, contract, limits=self._limits)
        if node.get_prop(JSON_CARRIER_KEY):
            if node.get_prop(JSON_CARRIER_KEY) != "core-json/1":
                raise ProfileMismatchError("Unknown generic JSON carrier")
            if writing:
                return {"object": {"json": dump_core_json(value, limits=self._limits)}}
            if (type(value) is not dict or set(value) != {"object"}
                    or type(value["object"]) is not dict
                    or set(value["object"]) != {"json"}
                    or type(value["object"]["json"]) is not str):
                raise ProjectionError("Generic carrier requires one exact Core JSON string")
            return parse_core_json(value["object"]["json"], limits=self._limits)
        kind = node.type
        if kind == "record":
            if type(value) is not dict:
                raise ProjectionError("Expected an Avro record object")
            names = {field.name for field in node.fields}
            if set(value) - names:
                raise ProjectionError("Record contains fields absent from the writer schema")
            result = {}
            for field in node.fields:
                member = value.get(field.name, _MISSING)
                if field.get_prop(INTERNAL_KEY):
                    if writing:
                        if member is not _MISSING:
                            raise ProjectionError("Internal schema declarations are not Core data")
                        result[field.name] = []
                    elif member != []:
                        raise ProjectionError("Internal schema declaration must be empty")
                    continue
                contract = field.get_prop(SCALAR_KEY)
                if contract:
                    member = self._field_scalar(
                        member, contract, field.get_prop(OPTIONAL_KEY) is True, writing
                    )
                else:
                    tree = field.get_prop(TREE_KEY)
                    if tree and writing:
                        _validate_tree(member, tree, self._limits)
                    member = self._avro_value(field.type, member, writing, depth + 1)
                    if tree and not writing:
                        _validate_tree(member, tree, self._limits)
                if member is not _MISSING:
                    result[field.name] = member
            return result
        if kind == "array":
            if type(value) is not list:
                raise ProjectionError("Expected an Avro array")
            return [self._avro_value(node.items, item, writing, depth + 1)
                    for item in value]
        if kind == "map":
            if type(value) is not dict or any(type(key) is not str for key in value):
                raise ProjectionError("Expected an Avro map with string keys")
            return {key: self._avro_value(node.values, item, writing, depth + 1)
                    for key, item in value.items()}
        if kind == "union":
            matches = []
            for branch in node.schemas:
                try:
                    matches.append(self._avro_value(branch, value, writing, depth + 1))
                except (ResourceLimitError, ProfileMismatchError):
                    raise
                except ProjectionError:
                    continue
            if len(matches) != 1:
                raise ProjectionError("Avro union has no unique semantic representation")
            return matches[0]
        if kind == "null" and value is None:
            return None
        if kind == "boolean" and type(value) is bool:
            return value
        if kind == "string" and type(value) is str:
            return value
        if kind == "bytes" and type(value) is bytes:
            return value
        if kind == "enum" and type(value) is str and value in node.symbols:
            return value
        raise ProjectionError(f"Value does not match the projected Avro {kind}")

    def _structure_value(self, node, value, writing, depth=0, *, root=None, legacy=False):
        if depth > self._limits.max_depth:
            raise ResourceLimitError("JSON Structure value exceeds the depth budget")
        root = self._schema if root is None else root

        def visit(child, member):
            return self._structure_value(
                child, member, writing, depth + 1, root=root, legacy=legacy
            )

        if "$ref" in node:
            reference = node["$ref"]
            if not reference.startswith("#/"):
                raise ProjectionError("Writer contract must contain all referenced schemas")
            resolved = root
            for name in reference[2:].split("/"):
                resolved = resolved[name.replace("~1", "/").replace("~0", "~")]
            return visit(resolved, value)
        if SCALAR_KEY in node:
            if legacy:
                raise MigrationError("Partial scalar annotations need a complete writer profile")
            optional = node.get(OPTIONAL_KEY) is True
            if value is _MISSING:
                if optional:
                    return _MISSING
                raise ProjectionError("A required scalar is missing; defaults are not implicit writes")
            if value is None and optional:
                return None
            operation = encode_scalar if writing else decode_scalar
            return operation(value, node[SCALAR_KEY], limits=self._limits)
        kind = node["type"]
        if isinstance(kind, dict):
            return visit(kind, value)
        if legacy and kind in ("integer", "int32", "uint32", "int64", "uint64"):
            number = _number(value, self._limits)
            if re.fullmatch(r"-?(?:0|[1-9][0-9]*)", number.token) is None:
                raise MigrationError("Legacy fixed integer requires an integer literal")
            bounds = {
                "integer": (-2 ** 31, 2 ** 31 - 1),
                "int32": (-2 ** 31, 2 ** 31 - 1),
                "uint32": (0, 2 ** 32 - 1),
                "int64": (-2 ** 63, 2 ** 63 - 1),
                "uint64": (0, 2 ** 64 - 1),
            }
            lower, upper = bounds[kind]
            if compare_numbers(number, lower) < 0 or compare_numbers(number, upper) > 0:
                raise MigrationError("Value is outside the retained legacy writer's range")
            if node.get("enum") and not any(
                compare_numbers(number, candidate) == 0 for candidate in node["enum"]
            ):
                raise MigrationError("Value violates the legacy numeric enum")
            return number
        if legacy and kind in ("float", "double", "float32", "float64", "decimal", "decimal128"):
            raise MigrationError("Legacy floating/decimal projection needs authoritative Core JSON")
        if kind == "object":
            if type(value) is not dict:
                raise ProjectionError("Expected a JSON Structure object")
            result = {}
            known = set()
            for name, child in node.get("properties", {}).items():
                wire_name = child.get("altnames", {}).get("json", name)
                known.add(wire_name)
                member = value.get(wire_name, _MISSING)
                if member is _MISSING and SCALAR_KEY not in child:
                    if name in node.get("required", []):
                        raise ProjectionError(f"Required property is missing: {wire_name}")
                    continue
                member = visit(child, member)
                if member is not _MISSING:
                    result[wire_name] = member
            extra = value.keys() - known
            if extra and not node.get("additionalProperties", False):
                raise ProjectionError("Object contains properties absent from the writer schema")
            for name in extra:
                result[name] = parse_core_json(
                    dump_core_json(value[name], limits=self._limits), limits=self._limits
                )
            return result
        if kind == "map":
            if type(value) is not dict or any(type(key) is not str for key in value):
                raise ProjectionError("Expected a JSON Structure map")
            maximum = _structure_map_max_entries(node, root.get("$uses", []), self._limits)
            if maximum is not None and compare_numbers(len(value), maximum, limits=self._limits) > 0:
                raise ProjectionError("JSON Structure map exceeds maxEntries")
            return {key: visit(node["values"], item)
                    for key, item in value.items()}
        if kind == "array":
            if type(value) is not list:
                raise ProjectionError("Expected a JSON Structure array")
            return [visit(node["items"], item)
                    for item in value]
        if kind == "any":
            return parse_core_json(
                dump_core_json(value, limits=self._limits), limits=self._limits
            )
        if kind in ("string", "uri", "binary", "datetime") and type(value) is str:
            if legacy and kind == "datetime":
                _timestamp_parts(value, self._limits)
            if "enum" in node and value not in node["enum"]:
                raise ProjectionError("Value does not match the physical string enum")
            return value
        if kind == "boolean" and type(value) is bool:
            return value
        if kind == "null" and value is None:
            return None
        raise ProjectionError(f"Value does not match JSON Structure type {kind}")

    def to_derived(self, value):
        if self._dialect == "avro":
            import avro.io
            result = self._avro_value(self._avro_schema, value, True)
            avro.io.validate(self._avro_schema, result, raise_on_error=True)
            return result
        return self._structure_value(self._schema, value, True)

    def from_derived(self, value):
        if self._dialect == "avro":
            import avro.io
            avro.io.validate(self._avro_schema, value, raise_on_error=True)
            return self._avro_value(self._avro_schema, value, False)
        return self._structure_value(self._schema, value, False)

    def write(self, value):
        """Write one datum, retaining its complete writer schema/profile."""
        return self._write(value)

    def _write(self, value, migration=None):
        derived = self.to_derived(value)
        if self._dialect == "json-structure":
            envelope = {"contract": self.artifact, "data": derived}
            if migration is not None:
                envelope["migration"] = migration
            return dump_core_json(
                envelope, limits=self._limits
            ).encode("utf-8")
        import avro.datafile
        import avro.io
        output = io.BytesIO()
        with avro.datafile.DataFileWriter(
            output, avro.io.DatumWriter(), self._avro_schema, codec="null"
        ) as writer:
            writer.set_meta(
                _CONTRACT_META, dump_core_json(self.artifact, limits=self._limits).encode("utf-8")
            )
            writer.set_meta("avro.schema", self._schema_json.encode("utf-8"))
            if migration is not None:
                writer.set_meta(
                    "xregistry.scalarMigration",
                    dump_core_json(migration, limits=self._limits).encode("utf-8"),
                )
            writer.append(derived)
            writer.flush()
            encoded = output.getvalue()
        if len(encoded) > self._limits.max_bytes:
            raise ResourceLimitError("Avro container exceeds the byte budget")
        return encoded

    def read(self, encoded):
        """Read one datum only under the reader's explicitly pinned contract."""
        if type(encoded) is not bytes:
            raise ProjectionError("Encoded projection must be bytes")
        if len(encoded) > self._limits.max_bytes:
            raise ResourceLimitError("Encoded projection exceeds the byte budget")
        if self._dialect == "json-structure":
            envelope = parse_core_json(encoded, limits=self._limits)
            if (type(envelope) is not dict
                    or set(envelope) not in (
                        {"contract", "data"}, {"contract", "data", "migration"}
                    )):
                raise ProfileMismatchError("Complete contract/data envelope is required")
            self._check_artifact(envelope["contract"])
            if "migration" in envelope:
                self._check_migration(envelope["migration"])
            return self.from_derived(envelope["data"])
        import avro.datafile
        import avro.io
        with avro.datafile.DataFileReader(
            io.BytesIO(encoded), avro.io.DatumReader()
        ) as reader:
            if reader.get_meta("avro.codec") not in (None, b"null"):
                raise ResourceLimitError("Reference reader requires bounded, uncompressed Avro")
            contract = reader.get_meta(_CONTRACT_META)
            if contract is None:
                raise ProfileMismatchError("Legacy writer requires explicit migration")
            self._check_artifact(parse_core_json(contract, limits=self._limits))
            writer_schema = parse_core_json(
                reader.get_meta("avro.schema"), limits=self._limits
            )
            if _canonical(writer_schema, self._limits) != self._schema_json:
                raise ProfileMismatchError("Avro header does not match the full writer schema")
            migration = reader.get_meta("xregistry.scalarMigration")
            if migration is not None:
                self._check_migration(parse_core_json(migration, limits=self._limits))
            iterator = iter(reader)
            value = next(iterator, _MISSING)
            if value is _MISSING or next(iterator, _MISSING) is not _MISSING:
                raise ProjectionError("Expected exactly one projected Avro datum")
        return self.from_derived(value)

    def _check_migration(self, migration):
        if type(migration) is not dict or set(migration) != {
            "strategy", "writerSchema", "writerFingerprint"
        }:
            raise ProfileMismatchError("Incomplete migration provenance")
        if migration["strategy"] not in ("retained-values", "authoritative-core"):
            raise ProfileMismatchError("Unknown migration strategy")
        if _fingerprint(migration["writerSchema"], self._limits) != migration[
            "writerFingerprint"
        ]:
            raise ProfileMismatchError("Retained legacy writer schema was altered")

    @staticmethod
    def _legacy_branches(node):
        return node.schemas if node.type == "union" else [node]

    @staticmethod
    def _type_identity(node):
        return node.type, getattr(node, "fullname", "")

    def transition_reader_schema(self, writer_schema):
        """Build a read-only Avro transition, never a normal profile writer."""
        if self._dialect != "avro":
            raise MigrationError("Avro migration needs an Avro target contract")
        import avro.schema
        old = avro.schema.parse(_canonical(writer_schema, self._limits))
        target = self.schema

        def structure(previous, kind, name=None):
            if previous is None:
                return None
            matches = [
                branch for branch in self._legacy_branches(previous)
                if branch.type == kind and (
                    name is None or branch.name == name.rsplit(".", 1)[-1]
                    or getattr(branch, "fullname", None) == name
                )
            ]
            if len(matches) != 1:
                raise MigrationError("Structural changes require authoritative Core data")
            return matches[0]

        def alternatives(current, previous):
            choices = copy.deepcopy(current) if isinstance(current, list) else [current]
            primitive = {
                value for value in choices if isinstance(value, str)
            } | {
                value["type"] for value in choices
                if isinstance(value, dict) and value.get("type") != "record"
            }
            named = {
                value["name"] for value in choices
                if isinstance(value, dict) and value.get("type") == "record"
            }
            for branch in self._legacy_branches(previous):
                if branch.type in ("int", "long", "float", "double", "string", "null"):
                    if branch.type not in primitive:
                        choices.append(branch.type)
                        primitive.add(branch.type)
                elif branch.get_prop(ABSENT_KEY) == PROFILE_ID:
                    if branch.fullname not in named:
                        raise MigrationError("Presence layout changes need authoritative Core data")
                else:
                    raise MigrationError("Legacy scalar structure needs authoritative Core data")
            return choices

        def visit(node, previous):
            if not isinstance(node, dict):
                return node
            if SCALAR_KEY in node and previous is not None:
                return alternatives(node, previous)
            kind = node.get("type")
            if kind == "record":
                if node.get(JSON_CARRIER_KEY):
                    return node
                prior = structure(previous, "record", node["name"])
                old_fields = prior.fields_dict if prior else {}
                if set(old_fields) - {field["name"] for field in node["fields"]}:
                    raise MigrationError("Dropping legacy fields requires authoritative Core data")
                for field in node["fields"]:
                    old_field = old_fields.get(field["name"])
                    if old_field is None or field.get(INTERNAL_KEY):
                        continue
                    if SCALAR_KEY in field:
                        field["type"] = alternatives(field["type"], old_field.type)
                    else:
                        field["type"] = visit(field["type"], old_field.type)
            elif kind == "array":
                prior = structure(previous, "array")
                node["items"] = visit(node["items"], prior.items if prior else None)
            elif kind == "map":
                prior = structure(previous, "map")
                node["values"] = visit(node["values"], prior.values if prior else None)
            return node

        target = visit(target, old)
        target.pop(PROFILE_KEY)
        target["x-xregistryTransitionFor"] = self.fingerprint
        return target

    def _legacy_scalar(self, value, previous, contract, qualified):
        if previous is None:
            return decode_scalar(value, contract, limits=self._limits)
        old_contract = previous.get_prop(SCALAR_KEY)
        if qualified and old_contract:
            return decode_scalar(value, old_contract, limits=self._limits)
        import avro.io
        matches = [
            branch for branch in self._legacy_branches(previous)
            if avro.io.validate(branch, value)
        ]
        if (contract["coreType"] != "timestamp" and type(value) is int and matches
                and all(branch.type in ("int", "long")
                        and not branch.get_prop("logicalType") for branch in matches)):
            number = _number(value, self._limits)
            encode_scalar(number, contract, limits=self._limits)
            return number
        raise MigrationError(
            "Legacy floating-point, timestamp or unqualified string data needs "
            "authoritative Core JSON; lost precision cannot be reconstructed"
        )

    def _legacy_branch(self, node, value):
        if node.type != "union":
            return node
        import avro.io
        matches = [branch for branch in node.schemas if avro.io.validate(branch, value)]
        if len(matches) != 1:
            raise MigrationError("Ambiguous legacy union needs authoritative Core data")
        return matches[0]

    def _convert_legacy(self, current, previous, value, qualified, depth=0):
        if depth > self._limits.max_depth:
            raise ResourceLimitError("Legacy data exceeds the depth budget")
        contract = current.get_prop(SCALAR_KEY)
        if contract:
            return self._legacy_scalar(value, previous, contract, qualified)
        if previous is None:
            return self._avro_value(current, value, False, depth)
        previous = self._legacy_branch(previous, value)
        if current.get_prop(JSON_CARRIER_KEY):
            if not qualified or previous.get_prop(JSON_CARRIER_KEY) != "core-json/1":
                raise MigrationError("Legacy generic values need authoritative Core JSON")
            return self._avro_value(current, value, False, depth)
        if current.type == "record":
            if previous.type != "record" or previous.fullname != current.fullname:
                raise MigrationError("Record identity changes need authoritative Core data")
            result = {}
            for field in current.fields:
                member = value.get(field.name, _MISSING)
                if field.get_prop(INTERNAL_KEY):
                    if member != []:
                        raise MigrationError("Legacy internal declaration contains data")
                    continue
                old_field = previous.fields_dict.get(field.name)
                contract = field.get_prop(SCALAR_KEY)
                if contract:
                    optional = field.get_prop(OPTIONAL_KEY) is True
                    if member is None or member is _MISSING or member == {}:
                        member = self._field_scalar(member, contract, optional, False)
                    elif qualified and old_field and old_field.get_prop(SCALAR_KEY):
                        member = self._field_scalar(
                            member, old_field.get_prop(SCALAR_KEY),
                            old_field.get_prop(OPTIONAL_KEY) is True, False,
                        )
                    else:
                        member = self._legacy_scalar(
                            member, old_field.type if old_field else None, contract, qualified
                        )
                else:
                    member = self._convert_legacy(
                        field.type, old_field.type if old_field else None,
                        member, qualified, depth + 1,
                    )
                if member is not _MISSING:
                    result[field.name] = member
            return result
        if current.type == "array" and previous.type == "array":
            return [self._convert_legacy(
                current.items, previous.items, member, qualified, depth + 1
            ) for member in value]
        if current.type == "map" and previous.type == "map":
            return {key: self._convert_legacy(
                current.values, previous.values, member, qualified, depth + 1
            ) for key, member in value.items()}
        if current.type == "union":
            matches = [
                branch for branch in current.schemas
                if self._type_identity(branch) == self._type_identity(previous)
            ]
            if len(matches) != 1:
                raise MigrationError("Union structure changes need authoritative Core data")
            return self._convert_legacy(matches[0], previous, value, qualified, depth + 1)
        return self._avro_value(current, value, False, depth)

    def migrate_avro(self, encoded, writer_schema, *, authoritative_core_json=None):
        """Migrate retained legacy values, or explicitly re-encode Core truth."""
        if self._dialect != "avro":
            raise MigrationError("Avro migration needs an Avro target contract")
        if type(encoded) is not bytes or len(encoded) > self._limits.max_bytes:
            raise ResourceLimitError("Legacy Avro exceeds the byte budget")
        if isinstance(writer_schema, (str, bytes)):
            writer_schema = parse_core_json(writer_schema, limits=self._limits)
        if type(writer_schema) is not dict:
            raise MigrationError("The complete retained writer schema is required")
        import avro.datafile
        import avro.io
        import avro.schema
        previous = avro.schema.parse(_canonical(writer_schema, self._limits))
        with avro.datafile.DataFileReader(
            io.BytesIO(encoded), avro.io.DatumReader()
        ) as reader:
            header = parse_core_json(reader.get_meta("avro.schema"), limits=self._limits)
            if _canonical(header, self._limits) != _canonical(writer_schema, self._limits):
                raise ProfileMismatchError("Legacy header differs from the retained writer schema")
            if reader.get_meta("avro.codec") not in (None, b"null"):
                raise ResourceLimitError("Reference migrator requires uncompressed Avro")
            if authoritative_core_json is None:
                iterator = iter(reader)
                original = next(iterator, _MISSING)
                if original is _MISSING or next(iterator, _MISSING) is not _MISSING:
                    raise MigrationError("Expected exactly one legacy datum")
                avro.io.validate(previous, original, raise_on_error=True)
        provenance = {
            "strategy": "authoritative-core" if authoritative_core_json is not None
            else "retained-values",
            "writerSchema": writer_schema,
            "writerFingerprint": _fingerprint(writer_schema, self._limits),
        }
        if authoritative_core_json is not None:
            return self._write(
                parse_core_json(authoritative_core_json, limits=self._limits), provenance
            )
        qualified = writer_schema.get(PROFILE_KEY) == projection_profile()
        if PROFILE_KEY in writer_schema and not qualified:
            raise MigrationError("Unknown legacy profile needs authoritative Core data")
        if qualified:
            ProjectionCodec(writer_schema, "avro", limits=self._limits).read(encoded)
        transition = avro.schema.parse(dump_core_json(
            self.transition_reader_schema(writer_schema), limits=self._limits
        ))
        with avro.datafile.DataFileReader(
            io.BytesIO(encoded), avro.io.DatumReader(readers_schema=transition)
        ) as reader:
            iterator = iter(reader)
            value = next(iterator, _MISSING)
            if value is _MISSING or next(iterator, _MISSING) is not _MISSING:
                raise MigrationError("Expected exactly one legacy datum")
        restored = self._convert_legacy(self._avro_schema, previous, value, qualified)
        return self._write(restored, provenance)

    def migrate_json_structure(
        self, encoded, writer_schema, *, authoritative_core_json=None
    ):
        """Migrate JSON using the caller's verified archived writer schema."""
        if self._dialect != "json-structure":
            raise MigrationError("JSON Structure migration needs that target dialect")
        if isinstance(writer_schema, (str, bytes)):
            writer_schema = parse_core_json(writer_schema, limits=self._limits)
        if type(writer_schema) is not dict:
            raise MigrationError("The complete archived writer schema is required")
        provenance = {
            "strategy": "authoritative-core" if authoritative_core_json is not None
            else "retained-values",
            "writerSchema": writer_schema,
            "writerFingerprint": _fingerprint(writer_schema, self._limits),
        }
        if authoritative_core_json is not None:
            restored = parse_core_json(authoritative_core_json, limits=self._limits)
            return self._write(restored, provenance)
        if PROFILE_KEY in writer_schema:
            restored = ProjectionCodec(
                writer_schema, "json-structure", limits=self._limits
            ).read(encoded)
        else:
            restored = self._structure_value(
                writer_schema, parse_core_json(encoded, limits=self._limits),
                False, root=writer_schema, legacy=True,
            )

        def resolve(node, root):
            for _ in range(self._limits.max_depth):
                if "$ref" in node:
                    if not node["$ref"].startswith("#/"):
                        raise MigrationError("Migration requires complete local schemas")
                    reference = node["$ref"]
                    node = root
                    for part in reference[2:].split("/"):
                        node = node[part.replace("~1", "/").replace("~0", "~")]
                elif isinstance(node.get("type"), dict):
                    node = node["type"]
                else:
                    return node
            raise ResourceLimitError("Schema references exceed the depth budget")

        def defaults(current, previous, value, depth=0):
            if depth > self._limits.max_depth:
                raise ResourceLimitError("Schema evolution exceeds the depth budget")
            current = resolve(current, self._schema)
            previous = resolve(previous, writer_schema)
            if SCALAR_KEY in current:
                return
            kind = current["type"]
            if kind == "object" and isinstance(value, dict):
                old_properties = previous.get("properties", {})
                properties = current.get("properties", {})
                if set(old_properties) - properties.keys():
                    raise MigrationError("Dropping properties requires authoritative Core JSON")
                for name, child in properties.items():
                    wire_name = child.get("altnames", {}).get("json", name)
                    old_child = old_properties.get(name)
                    if old_child is None:
                        if wire_name not in value and SCALAR_KEY in child and "default" in child:
                            value[wire_name] = decode_scalar(
                                child["default"], child[SCALAR_KEY], limits=self._limits
                            )
                    elif wire_name in value:
                        defaults(child, old_child, value[wire_name], depth + 1)
            elif kind == "map" and isinstance(value, dict):
                if previous.get("type") != "map":
                    raise MigrationError("Map representation changes require authoritative Core JSON")
                for member in value.values():
                    defaults(current["values"], previous["values"], member, depth + 1)
            elif kind == "array" and isinstance(value, list):
                for member in value:
                    defaults(current["items"], previous["items"], member, depth + 1)

        defaults(self._schema, writer_schema, restored)
        return self._write(restored, provenance)
