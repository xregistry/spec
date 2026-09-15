"""Reference pagination Link/count policy for issue617, without server state."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import re


RELATIONS = ("next", "prev", "first", "last")
MAX_COUNT = (1 << 64) - 1
_TOKEN = r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+"
_QUOTED = r'"(?:[\t !#-\[\]-~]|\\[\t !-~])*"'
_PARAMETER = re.compile(rf"[ \t]*;[ \t]*({_TOKEN})(?:[ \t]*=[ \t]*({_QUOTED}|{_TOKEN}))?")
_TARGET = re.compile(r"<([A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]*)>")


@dataclass(frozen=True)
class Link:
    target: str
    relations: tuple[str, ...]
    count: int | None


def _check_count(value: int | None) -> None:
    if value is not None and (type(value) is not int or not 0 <= value <= MAX_COUNT):
        raise ValueError("Count must be an unsigned 64-bit integer")


def parse_link_field(value: str) -> tuple[Link, ...]:
    wire = value.encode("ascii")
    if any(byte < 32 and byte != 9 or byte == 127 for byte in wire):
        raise ValueError("Invalid HTTP field-value control byte")
    links = []
    offset = 0
    while offset < len(value):
        while offset < len(value) and value[offset] in " \t,":
            offset += 1
        if offset == len(value):
            break
        target = _TARGET.match(value, offset)
        if target is None or re.search(r"%(?![0-9A-Fa-f]{2})", target.group(1)):
            raise ValueError("Malformed Link target")
        offset = target.end()
        parameters: list[tuple[str, str | None]] = []
        while parameter := _PARAMETER.match(value, offset):
            name, text = parameter.groups()
            if text is not None and text.startswith('"'):
                text = re.sub(r"\\(.)", r"\1", text[1:-1])
            parameters.append((name.lower(), text))
            offset = parameter.end()
        if any(name == "anchor" for name, _ in parameters):
            raise ValueError("Anchored links are outside this reference profile")
        relation = next((text for name, text in parameters if name == "rel"), None)
        if relation is None or not re.fullmatch(r"(?:next|prev|first|last)(?: +(?:next|prev|first|last))*", relation):
            raise ValueError("Missing or unsupported pagination relation")
        counts = []
        for name, text in parameters:
            if name == "count":
                if text is None or not re.fullmatch(r"[0-9]+", text):
                    raise ValueError("Invalid count parameter")
                count = int(text)
                _check_count(count)
                counts.append(count)
        if len(set(counts)) > 1:
            raise ValueError("Inconsistent count")
        links.append(Link(target.group(1), tuple(relation.split()), counts[0] if counts else None))
        while offset < len(value) and value[offset] in " \t":
            offset += 1
        if offset < len(value) and value[offset] != ",":
            raise ValueError("Malformed Link field")
    return tuple(links)


def pagination_headers(
    *,
    more_results: bool,
    at_start: bool,
    targets: Mapping[str, str],
    count: int | None = None,
) -> tuple[tuple[str, str], ...]:
    _check_count(count)
    if more_results != ("next" in targets):
        raise ValueError("Next is required exactly when more results remain")
    if at_start and "prev" in targets:
        raise ValueError("Previous is forbidden at the start")
    if set(targets) - set(RELATIONS):
        raise ValueError("Relation is outside this reference profile")
    if count == 0 and more_results:
        raise ValueError("A zero count cannot describe remaining records")
    headers = []
    for relation in RELATIONS:
        if relation in targets:
            target = targets[relation]
            if not isinstance(target, str):
                raise ValueError("Link target must be a URI-reference string")
            value = f"<{target}>;rel={relation}"
            if count is not None:
                value += f";count={count}"
            parsed = parse_link_field(value)
            if parsed != (Link(target, (relation,), count),):
                raise ValueError("Target cannot be serialized as one Link")
            headers.append(("Link", value))
    return tuple(headers)


def read_page(
    headers: Iterable[tuple[str, str]],
    *,
    known_count: int | None = None,
) -> tuple[str | None, int | None]:
    _check_count(known_count)
    next_targets = set()
    for name, value in headers:
        if name.lower() != "link":
            continue
        for link in parse_link_field(value):
            if link.count is not None:
                if known_count is not None and known_count != link.count:
                    raise ValueError("Inconsistent count")
                known_count = link.count
            if "next" in link.relations:
                next_targets.add(link.target)
    if len(next_targets) > 1:
        raise ValueError("Ambiguous next links")
    if known_count == 0 and next_targets:
        raise ValueError("A zero count cannot describe remaining records")
    return next(iter(next_targets), None), known_count
