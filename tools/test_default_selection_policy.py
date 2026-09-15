"""Source and abstract contract evidence; no live server/defaulting simulation."""

import json
from pathlib import Path

import pytest
from default_selection_contract import validate_default_candidate
from test_samples import _unique_json_object


ROOT = Path(__file__).resolve().parents[1]
SPEC = (ROOT / "core" / "spec.md").read_text(encoding="utf-8")
GUIDE = (ROOT / "core" / "resource.md").read_text(encoding="utf-8")
MODEL_SPEC = (ROOT / "core" / "model.md").read_text(encoding="utf-8")
TOOL_NOTES = (ROOT / "tools" / "README.md").read_text(encoding="utf-8")
SECTION = SPEC.split("#### `defaultversionid` Attribute\n", 1)[1].split(
    "#### `defaultversionurl` Attribute", 1
)[0]


def _paragraph(text, start):
    return " ".join(text.split(start, 1)[1].split("\n\n", 1)[0].split())


def test_source_limits_existence_validation_to_effective_sticky_selection():
    assert _paragraph(SECTION, "Existence validation MUST use") == (
        "the effective selection after applying Meta processing, model "
        "defaults, patch inference and flag overrides, and after all Version "
        "processing for the operation. A non-null candidate that remains the "
        "effective sticky selection MUST reference an existing Version; "
        "otherwise an error ([unknown_id](#unknown_id)) MUST be generated. "
        "A candidate discarded by non-sticky selection or superseded by a "
        "flag MUST NOT cause an existence error."
    )
    assert "Any attempt to set `defaultversionid` to a non-existing Version" not in SECTION
    assert "default_selection_contract.py" not in SECTION
    assert "py" not in SPEC.split("## Abstract", 1)[0].split()
    assert "(default_selection_contract.py)" in TOOL_NOTES
    assert "(../core/spec.md#defaultversionid-attribute)" in TOOL_NOTES
    assert (
        "It does not replace Meta processing, Version creation or default selection."
        in " ".join(TOOL_NOTES.split())
    )


def test_source_keeps_syntax_creation_clues_and_whole_request_rollback():
    assert _paragraph(SECTION, "Discarding a candidate affects") == (
        "only its existence obligation, not input-kind or identifier-syntax "
        "validation. A supplied non-null candidate MUST be a string with valid "
        "[Version identifier syntax](#singularid-id-attribute). This rule MUST "
        "NOT discard a candidate before the existing "
        "[Resource creation-clue processing](#resource-processing-algorithm). "
        "An invalid effective selection fails the whole operation under "
        "[Error Processing](#error-processing), without retaining partial changes."
    )
    rollback = _paragraph(SPEC, "## Error Processing\n\n")
    assert rollback.endswith("an error MUST be generated and the entire request MUST be undone.")
    creation = SPEC.split("##### Resource Processing Algorithm\n", 1)[1]
    assert "new Version with that `versionid` MUST be created" in " ".join(creation.split())


@pytest.mark.parametrize(
    "candidate, effective, versions, error",
    [
        pytest.param("missing", False, {"v1"}, None, id="discarded-nonsticky-missing"),
        pytest.param("missing", True, {"v1"}, "unknown_id", id="effective-sticky-missing"),
        pytest.param("v1", True, {"v1"}, None, id="effective-sticky-present"),
        pytest.param("new", True, {"v1", "new"}, None, id="created-before-existence-check"),
        pytest.param("new", False, {"new"}, None, id="nonsticky-creation-clue-retained"),
        pytest.param("missing", False, {"v1"}, None, id="candidate-superseded-by-flag"),
        pytest.param("v1", True, {"v1"}, None, id="flag-effective-selection-present"),
        pytest.param(None, False, {"v1"}, None, id="null-clears-sticky"),
    ],
)
def test_effective_stage_distinguishes_discarded_and_selected_candidates(
    candidate, effective, versions, error
):
    before = set(versions)
    if error:
        with pytest.raises(ValueError, match=error):
            validate_default_candidate(candidate, versions, effective_sticky_selection=effective)
    else:
        validate_default_candidate(candidate, versions, effective_sticky_selection=effective)
    assert versions == before


@pytest.mark.parametrize("candidate", [7, True, [], {}, "", "bad/id", "bad id", ".first", "a" * 129])
def test_discarding_does_not_accept_invalid_input_kind_or_identifier(candidate):
    with pytest.raises(ValueError, match="kind or syntax"):
        validate_default_candidate(candidate, {"v1"}, effective_sticky_selection=False)


@pytest.mark.parametrize("candidate", ["v1", "_", "A" * 128, "v1.0~:_@-"])
def test_valid_identifier_boundaries_remain_accepted(candidate):
    validate_default_candidate(candidate, {candidate}, effective_sticky_selection=True)


def test_patch_inference_and_flag_override_clauses_are_preserved():
    assert _paragraph(SECTION, 'When a "patch" type of operation is used') == (
        "and this attribute is present in the request but `defaultversionsticky` "
        "is absent, then: - A non-`null` value MUST set `defaultversionsticky` "
        "to `true`. - A `null` value MUST set `defaultversionsticky` to `false`."
    )
    flags = SPEC.split("### SetDefaultVersionID Flag\n", 1)[1].split("### Sort Flag", 1)[0]
    assert "Use of this flag MUST override any `meta.defaultversionid` and `meta.defaultversionsticky` values" in " ".join(flags.split())
    assert "a string containing the case-sensitive `versionid`" in " ".join(flags.split())
    assert "`meta.defaultversionsticky` MUST be set to `false`" in " ".join(flags.split())


@pytest.mark.parametrize("model_default", [False, True])
def test_omitted_sticky_uses_model_default_before_the_existence_stage(model_default):
    defaults = MODEL_SPEC.split("### `attributes.<STRING>.default`\n", 1)[1]
    assert "This value MUST be used to populate this attribute's value if one was not provided by a client." in " ".join(defaults.split())
    sticky = SPEC.split("#### `defaultversionsticky` Attribute\n", 1)[1]
    assert "using `true` instead of `false` in the `enum` and `default` aspects" in " ".join(sticky.split())
    versions = {"v1"}
    if model_default:
        with pytest.raises(ValueError, match="unknown_id"):
            validate_default_candidate("missing", versions, effective_sticky_selection=model_default)
    else:
        validate_default_candidate("missing", versions, effective_sticky_selection=model_default)


def test_existing_nonsticky_missing_id_counterexample_remains_accepted():
    example = GUIDE.split("### Update Resource with non-sticky bad defaultversionid\n", 1)[1].split("\n### ", 1)[0]
    request = example.split("**Request:**", 1)[1].split("```\n", 1)[1].split("\n```", 1)[0]
    request = json.loads(request.split("\n\n", 1)[1])
    final = example.split("**Final State:**", 1)[1].split("```\n", 1)[1].split("\n```", 1)[0]
    final = json.loads(final.replace("{ see Resource.* attrs }", "{}"), object_pairs_hook=_unique_json_object)
    assert request["meta"] == {"defaultversionid": "abc"}
    assert final["meta"]["defaultversionsticky"] is False
    assert final["meta"]["defaultversionid"] == "v1"
    assert "abc" not in final["versions"]
    validate_default_candidate("abc", final["versions"], effective_sticky_selection=False)
    with pytest.raises(ValueError, match="unknown_id"):
        validate_default_candidate("abc", final["versions"], effective_sticky_selection=True)
