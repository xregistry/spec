"""Source/catalog consistency checks, not a server validation implementation."""

import re
from pathlib import Path

import pytest


CORE = Path(__file__).resolve().parents[1] / "core"
SPEC = (CORE / "spec.md").read_text(encoding="utf-8")
MODEL = (CORE / "model.md").read_text(encoding="utf-8")


def _section(text, heading):
    level = heading.split()[0]
    return text.split(heading + "\n", 1)[1].split("\n" + level + " ", 1)[0]


def _normalized(text):
    return " ".join(text.split())


STRICT = _section(
    MODEL, "### `groups.<STRING>.resources.<STRING>.strictvalidation`"
)


def test_strict_validation_distinguishes_unavailable_checks():
    rules = STRICT.split("- A value of `true` indicates that:\n", 1)[1].split(
        "- A value of `false` indicates that:", 1
    )[0]
    assert _normalized(rules) == (
        "- The `format` validation logic MUST generate an error "
        "([format_unknown](spec.md#format_unknown)) if the Version's `format` "
        "is an unsupported value. "
        "- The `compatibility` validation logic MUST generate an error "
        "([compatibility_unknown](spec.md#compatibility_unknown)) if the "
        "Resource's `meta.compatibility` value is an unsupported value. "
        "- If validation cannot be performed because the Version uses a "
        "`<RESOURCE>url` to reference a document stored outside of the Registry, "
        "see the [`formatvalidated`](spec.md#formatvalidated-attribute) and "
        "[`compatibilityvalidated`](spec.md#compatibilityvalidated-attribute) "
        "rules ([format_external](spec.md#format_external))."
    )


def test_strict_validation_keeps_enablement_defaults_and_admission_rules():
    prefix, branches = STRICT.split("- A value of `true` indicates that:\n", 1)
    assert _normalized(prefix) == (
        "- Type: Boolean (`true` or `false`, case-sensitive) - OPTIONAL "
        "- Indicates whether an unsupported Resource `meta.compatibility` "
        "or Version `format` values are to be treated as errors or ignored. "
        "- This attribute only impacts server semantics when either "
        "`validateformat` or `validatecompatibility` are `true`. Otherwise, "
        "this attribute's value is ignored by the server. "
        "- When not specified, the default value MUST be `false`."
    )
    ignored = branches.split("- A value of `false` indicates that:\n", 1)[1]
    assert _normalized(ignored) == (
        "- If the Version's `format` value is absent, then format and "
        "compatibility validation logic MUST NOT be performed for that Version. "
        "- If the Version's `format` value is not supported, then the `format` "
        "validation logic MUST NOT generate an error. Instead, the Version's "
        "`formatvalidated` and `compatibilityvalidated` attributes MUST be "
        "set to `false`. "
        "- If the Resource's `meta.compatibility` value is unsupported, then "
        "the Version's `compatibilityvalidated` attribute MUST be set to `false`. "
        "- Regardless of the value of this aspect, if the Version's `format` "
        "value is absent, then format and compatibility validation logic MUST "
        "NOT be performed for that Version."
    )


@pytest.mark.parametrize(
    "attribute, false_literal, error",
    [
        ("formatvalidated", '`"false"`', "format_violation"),
        ("compatibilityvalidated", "`false`", "compatibility_violation"),
    ],
)
def test_actual_content_violations_are_not_unavailable_checks(
    attribute, false_literal, error
):
    section = _section(SPEC, f"#### `{attribute}` Attribute")
    failure = section.split("Note that ", 1)[1].split("\n- Constraints:", 1)[0]
    assert _normalized(failure) == (
        f"{false_literal} MUST NOT be used for validation failure. In those "
        "cases the write operation MUST generate an error "
        f"([{error}](#{error})) and reject the request regardless of the "
        "value of the "
        "[`strictvalidation`](model.md#groupsstringresourcesstringstrictvalidation)` "
        "model aspect."
    )


@pytest.mark.parametrize(
    "error, subject, expected_args",
    [
        ("format_unknown", "<version_xid>", {"format"}),
        ("format_external", "<version_xid>", set()),
        ("format_violation", "<version_xid>", {"format"}),
        ("compatibility_unknown", "<resource_xid>", {"compat", "format"}),
        ("compatibility_violation", "<resource_xid>", {"compat"}),
    ],
)
def test_validation_catalog_identity_subject_and_arguments(
    error, subject, expected_args
):
    entry = _section(SPEC, f"### {error}")
    fields = dict(re.findall(r"^\* (\w+): `([^`]+)`$", entry, re.MULTILINE))
    assert fields["Type"] == (
        f"https://github.com/xregistry/spec/blob/main/core/spec.md#{error}"
    )
    assert fields["Code"] == "400 Bad Request"
    assert fields["Subject"] == subject
    assert set(re.findall(r"^  - `(\w+)`:", entry, re.MULTILINE)) == expected_args
    assert set(re.findall(r"<(\w+)>", fields["Title"])) == expected_args | {
        "subject"
    }


def test_validation_diagnostics_keep_more_appropriate_error_permission():
    permission = SPEC.split("Most of the error conditions", 1)[1].split(
        "\n\n", 1
    )[0]
    assert _normalized(permission) == (
        "mentioned in this specification will include a reference to one of "
        "the errors listed in this section. While it is RECOMMENDED that "
        "implementations use those errors (for consistency), they MAY choose "
        "to use a more appropriate one. Implementations MAY define additional "
        "extension fields, as well as new error definitions. For new errors, "
        'it is RECOMMENDED that the "Subject" value appears within the "Title" '
        "field, when appropriate."
    )
