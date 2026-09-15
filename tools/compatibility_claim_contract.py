"""Pure compatibility-status plans, not model, format, or document validators."""

from copy import deepcopy
from dataclasses import dataclass


@dataclass(frozen=True)
class Unchecked:
    error: str
    reason: str

    def __post_init__(self):
        if self.error not in {"compatibility_unknown", "format_unknown", "format_external"}:
            raise ValueError("Unknown unavailable-check error")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("An unchecked result needs an explanation")


def plan_compatibility_checks(
    claim, versions, *, enabled, strict, admit_claim, check_version
):
    if type(enabled) is not bool or type(strict) is not bool:
        raise ValueError("Validation switches must be Boolean")
    if claim is not None:
        if not isinstance(claim, str) or not claim:
            raise ValueError("invalid_attribute: compatibility must be a non-empty string")
        admitted = admit_claim(claim)
        if type(admitted) is not bool:
            raise TypeError("Model admission must return Boolean")
        if not admitted:
            raise ValueError("invalid_attribute: compatibility is not permitted by the model")

    result = deepcopy(versions)
    for version in result.values():
        version.pop("compatibilityvalidated", None)
        version.pop("compatibilityvalidatedreason", None)
    if not enabled or claim is None:
        return result

    for name, version in result.items():
        if "format" not in version:
            continue
        outcome = check_version(name, version["format"], claim)
        if outcome is True:
            if version.get("formatvalidated") is False:
                raise ValueError("Checked compatibility contradicts unchecked format")
            version["compatibilityvalidated"] = True
        elif outcome is False:
            raise ValueError("compatibility_violation")
        elif isinstance(outcome, Unchecked):
            if strict:
                raise ValueError(outcome.error)
            version["compatibilityvalidated"] = False
            version["compatibilityvalidatedreason"] = outcome.reason
        else:
            raise TypeError("Checker must return Boolean or Unchecked")
    return result
