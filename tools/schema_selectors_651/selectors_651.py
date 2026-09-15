from collections.abc import Collection, Mapping
from dataclasses import dataclass
import re
from urllib.parse import quote, unquote

import avro.schema
import jsonpointer


class SelectionError(ValueError):
    pass


class AmbiguousSelection(SelectionError):
    pass


class UnresolvedSelection(SelectionError):
    pass


@dataclass(frozen=True)
class Reference:
    document: str
    selector: str | None
    family: str


_POINTER_FAMILIES = {"jsonschema", "jsonstructure"}
_FAMILIES = _POINTER_FAMILIES | {"avro", "protobuf", "xsd"}
_NO_ROOT = object()


def _family(format_name: str) -> str:
    name, separator, version = format_name.partition("/")
    if not separator or not version or name.lower() not in _FAMILIES:
        raise UnresolvedSelection("unsupported format profile")
    return name.lower()


def _decode(encoded: str) -> str:
    if re.search(r"%(?![0-9A-Fa-f]{2})", encoded):
        raise SelectionError("invalid percent escape")
    if re.search(r"[^A-Za-z0-9._~!$&'()*+,;=:@/?%\-]", encoded):
        raise SelectionError("character requires URI fragment encoding")
    try:
        return unquote(encoded, encoding="utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise SelectionError("invalid UTF-8") from error


def _pointer_parts(pointer: str) -> tuple[str, ...]:
    try:
        return tuple(jsonpointer.JsonPointer(pointer).parts)
    except jsonpointer.JsonPointerException as error:
        raise SelectionError("invalid JSON Pointer") from error


def _selector(encoded: str, family: str, *, local: bool = False) -> str:
    result = _decode(encoded)
    if family == "jsonstructure" or (
        family == "jsonschema" and (local or not result or result.startswith("/"))
    ):
        _pointer_parts(result)
    return result


def encode_local_owner(pointer: str) -> str:
    _pointer_parts(pointer)
    return "#" + quote(pointer, safe="/~", encoding="utf-8", errors="strict")


def _document_parts(document: str) -> tuple[str, str, str]:
    if not document or document.count("#") > 1:
        raise SelectionError("invalid document locator")
    base, marker, fragment = document.partition("#")
    if marker:
        _pointer_parts(_decode(fragment))
    return base, marker, fragment


def format_reference(document: str, selector: str | None, format_name: str) -> str:
    family = _family(format_name)
    _, owner_marker, _ = _document_parts(document)
    if selector is None:
        return document
    local = bool(owner_marker)
    encoded = quote(selector, safe="/~" if family in _POINTER_FAMILIES else "")
    _selector(encoded, family, local=local)
    separator = "" if local and family in _POINTER_FAMILIES else ":" if local else "#"
    return document + separator + encoded


def split_reference(
    uri: str,
    format_name: str,
    *,
    document_candidates: Collection[str] | None = None,
) -> Reference:
    family = _family(format_name)
    if not uri or uri.count("#") > 1:
        raise SelectionError("invalid schema reference")
    base, marker, fragment = uri.partition("#")
    if marker:
        _decode(fragment)
    if document_candidates is None:
        if not base:
            raise UnresolvedSelection("local document owner context is required")
        return Reference(
            base,
            _selector(fragment, family) if marker else None,
            family,
        )

    matches = set()
    for document in document_candidates:
        owner_base, owner_marker, owner_fragment = _document_parts(document)
        if not owner_marker:
            if base == document:
                matches.add(
                    Reference(
                        base,
                        _selector(fragment, family) if marker else None,
                        family,
                    )
                )
            continue
        if not marker or owner_base != base:
            continue
        owner_parts = _pointer_parts(_decode(owner_fragment))
        boundaries = [(len(fragment), None)]
        if family in _POINTER_FAMILIES:
            boundaries.extend(
                (match.start(), fragment[match.start():])
                for match in re.finditer(r"/|%2[fF]", fragment)
            )
        else:
            boundaries.extend(
                (match.start(), fragment[match.end():])
                for match in re.finditer(":", fragment)
            )
        for end, tail in boundaries:
            prefix = fragment[:end]
            try:
                prefix_parts = _pointer_parts(_decode(prefix))
            except SelectionError:
                continue
            if prefix_parts == owner_parts:
                matches.add(
                    Reference(
                        base + "#" + prefix,
                        _selector(tail, family, local=True) if tail is not None else None,
                        family,
                    )
                )
    if not matches:
        raise UnresolvedSelection("no supplied document owner matches")
    if len(matches) != 1:
        raise AmbiguousSelection("more than one document/selector boundary")
    return matches.pop()


def select_pointer(document: object, selector: str | None) -> object:
    pointer = "" if selector is None else selector
    current = document
    for part in _pointer_parts(pointer):
        if isinstance(current, dict):
            if part not in current:
                raise SelectionError("JSON Pointer target does not exist")
            current = current[part]
        elif isinstance(current, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", part):
                raise SelectionError("JSON Pointer array index is invalid")
            if len(part) > len(str(len(current))) or int(part) >= len(current):
                raise SelectionError("JSON Pointer target does not exist")
            current = current[int(part)]
        else:
            raise SelectionError("JSON Pointer target does not exist")
    return current


def avro_declarations(schema: avro.schema.Schema) -> dict[str, avro.schema.NamedSchema]:
    declarations = {}
    pending = [schema]
    seen = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, avro.schema.NamedSchema):
            declarations[current.fullname] = current
        if isinstance(current, avro.schema.RecordSchema):
            pending.extend(field.type for field in current.fields)
        elif isinstance(current, avro.schema.UnionSchema):
            pending.extend(current.schemas)
        elif isinstance(current, avro.schema.ArraySchema):
            pending.append(current.items)
        elif isinstance(current, avro.schema.MapSchema):
            pending.append(current.values)
    return declarations


def select_named(
    declarations: Mapping[str, object],
    selector: str | None,
    *,
    root: object = _NO_ROOT,
    protobuf: bool = False,
) -> object:
    if selector is None or selector == "":
        if protobuf or root is _NO_ROOT:
            raise SelectionError("an explicit name selector is required")
        return root
    absolute = protobuf and selector.startswith(".")
    name = selector[1:] if absolute else selector
    if "." in name or absolute:
        matches = [declarations[name]] if name in declarations else []
    else:
        matches = [
            value
            for fullname, value in declarations.items()
            if fullname.rsplit(".", 1)[-1] == name
        ]
    if not matches:
        raise SelectionError("named declaration does not exist")
    if len(matches) != 1:
        raise AmbiguousSelection("name requires qualification")
    return matches[0]


def select_json_structure(
    document: object,
    selector: str | None,
    *,
    declaration_pointers: Collection[str],
) -> object:
    if not isinstance(document, dict):
        raise SelectionError("JSON Structure document must be an object")
    if "$root" in document and "type" in document:
        raise SelectionError("conflicting root declarations")
    if not selector:
        if "$root" in document:
            root = document["$root"]
            if not isinstance(root, str):
                raise SelectionError("$root must be a pointer")
            selector = _selector(root[1:], "jsonstructure") if root.startswith("#") else root
            root_parts = _pointer_parts(selector)
            if len(root_parts) < 2 or root_parts[0] != "definitions":
                raise SelectionError("$root must identify a reusable declaration")
        elif "type" in document:
            selector = ""
        else:
            raise SelectionError("no designated root; explicit selector required")
    parts = _pointer_parts(selector)
    if parts and (len(parts) < 2 or parts[0] != "definitions"):
        raise SelectionError("selector must identify a reusable declaration")
    if selector not in declaration_pointers:
        raise SelectionError("target is not an indexed type declaration")
    return select_pointer(document, selector)
