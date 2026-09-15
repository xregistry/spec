"""Source and deferred-check decision evidence, not live schema validation."""

from copy import deepcopy
from pathlib import Path

import pytest
from compatibility_claim_contract import Unchecked, plan_compatibility_checks


ROOT = Path(__file__).resolve().parents[1]
SPEC = (ROOT / "core" / "spec.md").read_text(encoding="utf-8")
MODEL = (ROOT / "core" / "model.md").read_text(encoding="utf-8")
NOTES = (ROOT / "tools" / "README.md").read_text(encoding="utf-8")
CLAIM = SPEC.split("#### `compatibility` Attribute\n", 1)[1].split("\n#### ", 1)[0]
CAPABILITY = SPEC.split("#### `compatibilities` Capability\n", 1)[1].split("\n#### ", 1)[0]
STATUS = SPEC.split("#### `compatibilityvalidated` Attribute\n", 1)[1].split("\n#### ", 1)[0]


def _versions():
    return {
        "v1": {
            "format": "JsonSchema/draft-07",
            "ancestorid": "v1",
            "formatvalidated": True,
            "compatibilityvalidated": True,
            "compatibilityvalidatedreason": "stale",
            "labels": {"keep": "unchanged"},
        }
    }


def _plan(versions, *, claim="backward", enabled=True, strict=False, checker=lambda *args: True):
    return plan_compatibility_checks(
        claim, versions, enabled=enabled, strict=strict,
        admit_claim=lambda value: value.casefold() in {"backward", "forward", "vendor_rule"},
        check_version=checker,
    )


def test_source_distinguishes_model_admission_from_validator_capabilities():
    text = " ".join(CLAIM.split())
    assert "A stored value is a compatibility claim, not a statement that the server has verified it." in text
    assert "non-empty string that satisfies the Resource's model constraints" in text
    assert "Lack of an applicable checker MUST NOT by itself reject a model-permitted claim" in text
    assert "when compatibility checking is disabled or `strictvalidation` is `false`" in text
    assert "When configuring this capability, an error" in " ".join(CAPABILITY.split())
    assert "not an unconditional list of allowed stored claims" in " ".join(CAPABILITY.split())
    assert "compatibility_claim_contract.py" not in SPEC
    assert "compatibility_claim_contract.py" not in MODEL
    assert "(compatibility_claim_contract.py)" in NOTES


def test_source_preserves_all_version_checks_status_presence_and_real_failure_rules():
    text = " ".join(CLAIM.split())
    assert "the new claim applies to all Versions of the Resource" in text
    assert "enabled checks MUST be evaluated for all applicable Versions, not only changed Versions" in text
    assert "An actual failed check MUST generate an error" in text
    assert "regardless of `strictvalidation`" in text
    assert "Validation status and reason attributes MUST follow their existing presence rules." in text
    assert "lack of checker support MUST NOT by itself reject a stored claim" in " ".join(MODEL.split())
    assert "validation](./model.md#groupsstringresourcesstringvalidatecompatibility)" in STATUS
    assert "compatibility validation check was not performed" in " ".join(
        SPEC.split("#### `compatibilityvalidatedreason` Attribute\n", 1)[1].split("\n#### ", 1)[0].split()
    )
    assert "When this model attribute is `true` then its sibling `validateformat` attribute MUST also be `true`." in " ".join(MODEL.split())
    assert "the entire request MUST be undone." in " ".join(SPEC.split())


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("strict", [False, True])
@pytest.mark.parametrize("unavailable", [None, "compatibility_unknown", "format_unknown", "format_external"])
def test_supported_and_unavailable_pairs_follow_enabled_and_strict_switches(enabled, strict, unavailable):
    versions = _versions()
    if unavailable == "format_unknown":
        versions["v1"]["format"] = "Unsupported/1"
    if unavailable in {"format_unknown", "format_external"}:
        versions["v1"]["formatvalidated"] = False
        versions["v1"]["formatvalidatedreason"] = "existing unavailable format check"
    before = deepcopy(versions)
    calls = []
    reason = f"Check unavailable: {unavailable}"

    def checker(name, format_name, claim):
        calls.append((name, format_name, claim))
        return Unchecked(unavailable, reason) if unavailable else True

    if enabled and strict and unavailable:
        with pytest.raises(ValueError, match=unavailable):
            _plan(versions, enabled=enabled, strict=strict, checker=checker)
    else:
        result = _plan(versions, enabled=enabled, strict=strict, checker=checker)
        expected = deepcopy(before["v1"])
        expected.pop("compatibilityvalidated")
        expected.pop("compatibilityvalidatedreason")
        if enabled:
            expected["compatibilityvalidated"] = unavailable is None
            if unavailable:
                expected["compatibilityvalidatedreason"] = reason
        assert result == {"v1": expected}
    assert calls == ([("v1", versions["v1"]["format"], "backward")] if enabled else [])
    assert versions == before


@pytest.mark.parametrize("strict", [False, True])
@pytest.mark.parametrize("absence", ["claim", "format"])
def test_absent_claim_or_format_skips_checks_and_removes_stale_status(strict, absence):
    versions = _versions()
    if absence == "format":
        versions["v1"].pop("format")
    before = deepcopy(versions)

    def forbidden_check(*args):
        pytest.fail("A disabled-by-absence check was invoked")

    result = _plan(
        versions, claim=None if absence == "claim" else "backward",
        strict=strict, checker=forbidden_check,
    )
    expected = deepcopy(before["v1"])
    expected.pop("compatibilityvalidated")
    expected.pop("compatibilityvalidatedreason")
    assert result == {"v1": expected}
    assert versions == before


@pytest.mark.parametrize("strict", [False, True])
def test_a_real_failed_check_is_rejected_in_both_modes_without_mutating_input(strict):
    versions = _versions()
    before = deepcopy(versions)
    with pytest.raises(ValueError, match="compatibility_violation"):
        _plan(versions, strict=strict, checker=lambda *args: False)
    assert versions == before


def test_checked_compatibility_cannot_override_unchecked_format_status():
    versions = _versions()
    versions["v1"]["formatvalidated"] = False
    versions["v1"]["formatvalidatedreason"] = "Format cannot be checked"
    before = deepcopy(versions)
    with pytest.raises(ValueError, match="Checked compatibility contradicts unchecked format"):
        _plan(versions, checker=lambda *args: True)
    assert versions == before


def test_mixed_formats_check_supported_versions_and_report_only_unavailable_pairs():
    versions = _versions()
    versions["v2"] = {"format": "Custom/1", "ancestorid": "v1"}
    before = deepcopy(versions)
    calls = []

    def checker(name, format_name, claim):
        calls.append((name, claim))
        if format_name == "Custom/1":
            return Unchecked("compatibility_unknown", "Backward is not implemented for Custom/1")
        return True

    result = _plan(versions, claim="BaCkWaRd", checker=checker)
    assert calls == [("v1", "BaCkWaRd"), ("v2", "BaCkWaRd")]
    assert result["v1"]["compatibilityvalidated"] is True
    assert "compatibilityvalidatedreason" not in result["v1"]
    assert result["v2"]["compatibilityvalidated"] is False
    assert result["v2"]["compatibilityvalidatedreason"] == "Backward is not implemented for Custom/1"
    assert versions == before


def test_changed_claim_rechecks_all_versions_and_later_failure_discards_earlier_results():
    versions = _versions()
    versions["v2"] = {"format": "Custom/1", "ancestorid": "v1"}
    versions["v3"] = {"format": "JsonSchema/draft-07", "ancestorid": "v2"}
    before = deepcopy(versions)
    calls = []

    def checker(name, format_name, claim):
        calls.append((name, claim))
        if name == "v2":
            return Unchecked("compatibility_unknown", "Forward is not implemented for Custom/1")
        return name != "v3"

    with pytest.raises(ValueError, match="compatibility_violation"):
        _plan(versions, claim="forward", checker=checker)
    assert calls == [("v1", "forward"), ("v2", "forward"), ("v3", "forward")]
    assert versions == before


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("strict", [False, True])
def test_model_constraints_are_not_bypassed_by_validation_settings(enabled, strict):
    calls = []
    with pytest.raises(ValueError, match="invalid_attribute"):
        plan_compatibility_checks(
            "backward", _versions(), enabled=enabled, strict=strict,
            admit_claim=lambda value: False,
            check_version=lambda *args: calls.append(args),
        )
    assert calls == []


@pytest.mark.parametrize("claim", ["", 7, True, [], {}])
def test_disabled_validation_still_rejects_invalid_claim_kinds_and_empty_values(claim):
    with pytest.raises(ValueError, match="invalid_attribute"):
        _plan(_versions(), claim=claim, enabled=False)


@pytest.mark.parametrize("enabled,strict", [("false", False), (True, 1)])
def test_invalid_switch_kinds_do_not_enable_or_disable_checks_implicitly(enabled, strict):
    with pytest.raises(ValueError, match="Validation switches must be Boolean"):
        _plan(_versions(), enabled=enabled, strict=strict)


def test_model_admission_requires_an_actual_boolean_result():
    with pytest.raises(TypeError, match="Model admission must return Boolean"):
        plan_compatibility_checks(
            "backward", _versions(), enabled=False, strict=False,
            admit_claim=lambda value: 1,
            check_version=lambda *args: pytest.fail("Model admission was bypassed"),
        )


def test_advisory_or_unrestricted_model_values_are_not_mistaken_for_hard_enumerations():
    result = plan_compatibility_checks(
        "vendor_rule", _versions(), enabled=False, strict=True,
        admit_claim=lambda value: True,
        check_version=lambda *args: pytest.fail("Disabled checker was called"),
    )
    assert "compatibilityvalidated" not in result["v1"]
    assert "compatibilityvalidatedreason" not in result["v1"]
    enumeration = MODEL.split("### `attributes.<STRING>.enum`\n", 1)[1].split("\n### ", 1)[0]
    assert "this list is just a suggested set of values" in " ".join(enumeration.split())


def test_empty_resource_has_no_fabricated_validation_results():
    assert _plan({}, checker=lambda *args: pytest.fail("Empty resource was checked")) == {}


@pytest.mark.parametrize("outcome", [None, 1, "true", {}])
def test_invalid_checker_results_are_not_accepted_as_success_or_unchecked(outcome):
    with pytest.raises(TypeError, match="Checker must return Boolean or Unchecked"):
        _plan(_versions(), checker=lambda *args: outcome)


def test_unexpected_checker_errors_propagate_without_publishing_a_partial_plan():
    versions = _versions()
    before = deepcopy(versions)

    def checker(*args):
        raise RuntimeError("validator crashed")

    with pytest.raises(RuntimeError, match="validator crashed"):
        _plan(versions, checker=checker)
    assert versions == before


@pytest.mark.parametrize("reason", ["", "   ", None])
def test_unchecked_outcome_requires_an_explanation(reason):
    with pytest.raises(ValueError, match="needs an explanation"):
        Unchecked("compatibility_unknown", reason)


def test_unchecked_outcome_cannot_mislabel_an_actual_violation():
    with pytest.raises(ValueError, match="Unknown unavailable-check error"):
        Unchecked("compatibility_violation", "Actual content is incompatible")
