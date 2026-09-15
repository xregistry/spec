"""Arithmetic/source-clause checks for the proposed Group naming contract."""

import re
from pathlib import Path

import pytest


CORE = Path(__file__).resolve().parents[1] / "core"
MODEL = (CORE / "model.md").read_text(encoding="utf-8")
SPEC = (CORE / "spec.md").read_text(encoding="utf-8")


def _section(name):
    return MODEL.split(f"### `{name}`\n", 1)[1].split("\n### ", 1)[0]


def _maximum(name):
    return int(re.search(r"MUST NOT exceed (\d+) characters", _section(name)).group(1))


ATTRIBUTE_LIMIT = int(re.search(
    r"Their names MUST be between 1 and (\d+) characters in length", SPEC
).group(1))
ID_SUFFIX = re.search(r"^##### `<SINGULAR>([a-z]+)` ", SPEC, re.MULTILINE).group(1)


def test_group_singular_bound_is_exactly_the_derived_id_name_budget():
    assert ATTRIBUTE_LIMIT == 63
    assert ID_SUFFIX == "id"
    assert _maximum("groups.<STRING>.singular") == ATTRIBUTE_LIMIT - len(ID_SUFFIX) == 61


@pytest.mark.parametrize(
    "length, accepted, derived_length",
    [(60, True, 62), (61, True, 63), (62, False, 64), (63, False, 65)],
)
def test_group_singular_boundaries_and_derived_names(length, accepted, derived_length):
    name = "g" * length
    derived = name + ID_SUFFIX
    assert len(derived) == derived_length
    assert (len(name) <= _maximum("groups.<STRING>.singular")) is accepted
    assert (len(derived) <= ATTRIBUTE_LIMIT) is accepted
    assert derived == name + "id"


@pytest.mark.parametrize(
    "name",
    [
        "groups.<STRING>.plural",
        "groups.<STRING>.resources.<STRING>.plural",
        "groups.<STRING>.resources.<STRING>.singular",
    ],
)
def test_other_type_name_limits_are_unchanged(name):
    assert _maximum(name) == 57


def test_existing_immutable_names_require_explicit_migration_not_renaming():
    section = " ".join(_section("groups.<STRING>.singular").split())
    assert "- MUST be immutable." in section
    assert (
        "This limit leaves room for the `id` suffix in the `<GROUP>id` "
        "attribute within the [63-character attribute-name limit]"
        "(./spec.md#attributes). Models using the previously stated 62- or "
        "63-character Group singular names do not satisfy this bound. "
        "Existing immutable Group types MUST NOT be silently truncated or "
        "renamed; adopting this bound requires an explicit migration."
    ) in section
