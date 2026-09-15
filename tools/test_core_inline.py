"""Source-level consistency checks, not server conformance tests."""

import re
from pathlib import Path

import pytest


SPEC = (Path(__file__).resolve().parents[1] / "core" / "spec.md").read_text(
    encoding="utf-8"
)


def _section(heading):
    match = re.search(
        rf"(?ms)^{re.escape(heading)}\n(.*?)(?=^#{{1,3}} |\Z)", SPEC
    )
    assert match is not None, f"Missing section: {heading}"
    return match.group(1)


def _paragraphs(heading):
    return [" ".join(text.split()) for text in _section(heading).split("\n\n")]


def test_inline_error_recommendations_do_not_overlap():
    recommendations = [
        paragraph
        for paragraph in _paragraphs("### Inline Flag")
        if "(#inline_noninlineable)" in paragraph or "(#bad_inline)" in paragraph
    ]
    assert recommendations == [
        "Specifying the name of a known non-inlineable attribute MUST generate "
        "an error ([inline_noninlineable](#inline_noninlineable)).",
        "A malformed `<PATH>` value or a request to inline an unknown attribute "
        "MUST generate an error ([bad_inline](#bad_inline)).",
    ]


def test_inline_path_syntax_keeps_valid_and_invalid_examples():
    wildcard_rules = [
        paragraph
        for paragraph in _paragraphs("### Inline Flag")
        if paragraph.startswith("The `*` value MAY")
    ]
    assert len(wildcard_rules) == 1
    assert wildcard_rules[0].endswith(
        "Use of `*` MUST only be used as the last part of the `<PATH>` "
        "(in its entirety). For example, `foo*` and `*.foo` are not valid "
        "`<PATH>` values, but `*` and `endpoints.*` are."
    )


@pytest.mark.parametrize(
    "error, expected_args",
    [
        ("inline_noninlineable", {"name"}),
        ("bad_inline", {"value", "error_detail"}),
    ],
)
def test_inline_catalog_identity_subject_and_arguments(error, expected_args):
    entry = _section(f"### {error}")
    fields = dict(re.findall(r"^\* (\w+): `([^`]+)`$", entry, re.MULTILINE))
    assert fields["Type"] == (
        f"https://github.com/xregistry/spec/blob/main/core/spec.md#{error}"
    )
    assert fields["Code"] == "400 Bad Request"
    assert fields["Subject"] == "<request_path>"
    assert set(re.findall(r"^  - `(\w+)`:", entry, re.MULTILINE)) == expected_args
    assert set(re.findall(r"<(\w+)>", fields["Title"])) == expected_args | {
        "subject"
    }


def test_inline_guidance_keeps_error_choice_permission():
    permission = [
        paragraph
        for paragraph in _paragraphs("## Error Processing")
        if paragraph.startswith("Most of the error conditions")
    ]
    assert permission == [
        "Most of the error conditions mentioned in this specification will "
        "include a reference to one of the errors listed in this section. "
        "While it is RECOMMENDED that implementations use those errors "
        "(for consistency), they MAY choose to use a more appropriate one. "
        "Implementations MAY define additional extension fields, as well as "
        "new error definitions. For new errors, it is RECOMMENDED that the "
        '"Subject" value appears within the "Title" field, when appropriate.'
    ]
