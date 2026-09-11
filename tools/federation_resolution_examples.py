"""In-memory Resource-origin selection for the federation composition example."""

from dataclasses import dataclass
from typing import Callable, Sequence

from federation_examples import FederationError, validate_xid


@dataclass(frozen=True)
class Source:
    context: str
    read: Callable[[str, str], object]


def resolve_resource_read(
    target: str, operation: str, local: Source, sources: Sequence[Source]
) -> dict:
    """Select an owning Resource once, then keep its Versions on that source."""
    validate_xid(target)
    parts = target[1:].split("/")
    if operation not in ("entity", "document") or len(parts) not in (4, 5, 6):
        raise FederationError("unsupported_operation", "Example resolves Resource reads")
    if operation == "document" and len(parts) == 5:
        raise FederationError("unsupported_operation", "Meta has no domain document")
    if not isinstance(sources, Sequence):
        raise FederationError("invalid_package", "Source policy must be an ordered sequence")
    candidates = [local, *sources]
    contexts = set()
    for source in candidates:
        if (
            not isinstance(source, Source)
            or not isinstance(source.context, str)
            or not source.context
            or source.context in contexts
            or not callable(source.read)
        ):
            raise FederationError("invalid_package", "Invalid or duplicate source context")
        contexts.add(source.context)
    owner = "/" + "/".join(parts[:4])
    for source in candidates:
        try:
            resource = source.read("entity", owner)
        except FederationError as error:
            if error.code == "not_found":
                continue
            raise
        if not isinstance(resource, dict) or resource.get("xid") != owner:
            raise FederationError("invalid_package", "Source did not return the requested Resource")
        value = resource if operation == "entity" and target == owner else source.read(operation, target)
        return {"origin": source.context, "target": target, "value": value}
    raise FederationError("not_found", "Resource absent from every configured source")
