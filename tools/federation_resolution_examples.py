"""Resolution ownership and Resource-origin selection without network access."""

from dataclasses import dataclass
from typing import Callable, Sequence

from federation_examples import FederationError, validate_xid


@dataclass(frozen=True)
class Source:
    context: str
    read: Callable[[str, str], object]
    capabilities: dict | None = None


def resolution_owner(capabilities: dict | None) -> str:
    """Read the enabled resolution-owner capability. Absence means consumer."""
    if capabilities is None:
        return "consumer"
    if not isinstance(capabilities, dict):
        raise FederationError("invalid_package", "Capabilities must be an object")
    if "federation" not in capabilities:
        return "consumer"
    federation = capabilities["federation"]
    if not isinstance(federation, dict) or not isinstance(federation.get("resolution"), str):
        raise FederationError("invalid_package", "Federation capability requires a resolution string")
    if federation.keys() - {"resolution"}:
        raise FederationError("unsupported_operation", "Unknown federation capability field")
    if federation["resolution"] not in ("consumer", "producer"):
        raise FederationError("unsupported_operation", "Unknown federation resolution owner")
    return federation["resolution"]


def _check_source(source: Source) -> None:
    if (
        not isinstance(source, Source)
        or not isinstance(source.context, str)
        or not source.context
        or not callable(source.read)
    ):
        raise FederationError("invalid_package", "Invalid or duplicate source context")


def resolve_resource_read(
    target: str, operation: str, local: Source, sources: Sequence[Source]
) -> dict:
    """Read a producer view directly, or select one Resource origin as a consumer."""
    validate_xid(target)
    parts = target[1:].split("/")
    if operation not in ("entity", "document") or len(parts) not in (4, 5, 6):
        raise FederationError("unsupported_operation", "Example resolves Resource reads")
    if operation == "document" and len(parts) == 5:
        raise FederationError("unsupported_operation", "Meta has no domain document")
    _check_source(local)
    if resolution_owner(local.capabilities) == "producer":
        value = local.read(operation, target)
        if operation == "entity" and (
            not isinstance(value, dict) or value.get("xid") != target
        ):
            raise FederationError("invalid_package", "Producer returned different entity metadata")
        return {"origin": local.context, "target": target, "value": value}
    if not isinstance(sources, Sequence):
        raise FederationError("invalid_package", "Source policy must be an ordered sequence")
    candidates = [local, *sources]
    contexts = set()
    for source in candidates:
        _check_source(source)
        if source.context in contexts:
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
