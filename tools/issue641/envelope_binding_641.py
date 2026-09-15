"""Offline envelope-only checks on supplied effective Message definitions."""


def _selector(value, *, require_version):
    if not isinstance(value, str) or not value:
        raise ValueError("envelope selector must be a non-empty string")
    name, separator, version = value.partition("/")
    if not name or (separator and not version) or (require_version and not separator):
        raise ValueError("invalid envelope selector")
    return name.casefold(), version.casefold() if separator else None


def check_binding(context, effective_message, *, kind="messagegroup"):
    if kind not in ("messagegroup", "endpoint"):
        raise ValueError("unsupported binding context kind")
    if effective_message is None:
        return "unresolved"
    selected = None
    if "envelope" in effective_message:
        selected = _selector(effective_message["envelope"], require_version=True)
        if not isinstance(effective_message.get("envelopemetadata"), dict):
            raise ValueError("selected envelope requires metadata declarations")
    if "envelope" not in context:
        return "compatible"
    required = _selector(context["envelope"], require_version=kind == "messagegroup")
    if selected is None:
        raise ValueError("bound context requires an effective Message envelope")
    if selected[0] != required[0]:
        raise ValueError("conflicting envelope names")
    if required[1] is not None and required[1] != selected[1]:
        if kind == "endpoint":
            raise NotImplementedError("version refinement needs envelope-specific rules")
        raise ValueError("conflicting Message Group envelope versions")
    return "compatible"
