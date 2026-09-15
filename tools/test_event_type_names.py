"""Check event-name references against the source entity/action catalog."""

import re
from pathlib import Path

import pytest


SOURCE = (Path(__file__).resolve().parents[1] / "core" / "events.md").read_text(
    encoding="utf-8"
)
ENTITIES = dict(re.findall(
    r"^### `(\w+)` Events\n(.*?)(?=^#{2,3} |\Z)",
    SOURCE, re.MULTILINE | re.DOTALL,
))
CATALOG = {
    f"io.xregistry.{entity}.{action}"
    for entity, body in ENTITIES.items()
    for action in re.findall(r"^- Action: `(\w+)`", body, re.MULTILINE)
}


def _types(text):
    return [
        backtick or quoted
        for backtick, quoted in re.findall(
            r'`(io\.xregistry\.[\w.-]+)`|"(io\.xregistry\.[\w.-]+)"', text
        )
    ]


def _sample(title):
    return SOURCE.split(f"### {title}\n", 1)[1].split("\n### ", 1)[0]


def test_all_concrete_event_type_references_are_declared():
    assert set(ENTITIES) == {
        "registry", "model", "modelsource", "capabilities", "group", "resource", "version"
    }
    assert {"io.xregistry.version.updated", "io.xregistry.resource.deprecated"} <= CATALOG
    references = set(_types(SOURCE))
    assert references
    assert references <= CATALOG, references - CATALOG


def test_default_version_attribute_update_uses_defined_event_pair():
    rule = ENTITIES["resource"].split("- A Resource's attribute", 1)[1].split(
        "\n\n", 1
    )[0]
    assert " ".join(rule.split()) == (
        "(from the default Version entity) is updated, where `changed`, if "
        "present, MUST include each modified attribute. Note that a "
        "`io.xregistry.version.updated` event MUST also be generated."
    )
    assert _types(_sample("Update a Resource attribute (a default Version attribute)")) == [
        "io.xregistry.resource.updated", "io.xregistry.version.updated"
    ]


def test_resource_deprecation_rule_matches_defined_sample_types():
    rule = ENTITIES["resource"].split(
        "This MUST include any updates to the `deprecated` sub-object,", 1
    )[1].split("\n\n", 1)[0]
    assert " ".join(rule.split()) == (
        "even though a `io.xregistry.resource.deprecated` event is also "
        "generated. And in that situation `meta.deprecated` MUST be included "
        "in the `io.xregistry.resource.updated` event's `changed` list, if present."
    )
    assert _types(_sample("Update a Resource's meta sub-object and deprecate the Resource")) == [
        "io.xregistry.resource.updated", "io.xregistry.resource.deprecated"
    ]


@pytest.mark.parametrize("invalid", ["io.xregistry.version.update", "io.xregistry.deprecated"])
def test_undefined_spellings_are_not_catalog_aliases(invalid):
    assert invalid not in CATALOG


def test_default_pointer_change_still_does_not_emit_version_updated():
    pointer = ENTITIES["resource"].split(
        "In the case of changing a Resource's `meta.defaultversionid` attribute,", 1
    )[1].split("\n\n", 1)[0]
    assert " ".join(pointer.split()).endswith(
        "Note that a `io.xregistry.version.updated` event MUST NOT be generated "
        "for either the prior or new default Version due to the default Version changing."
    )


def test_event_coalescing_and_precedence_rules_are_unchanged():
    rules = SOURCE.split("following constraints apply:\n", 1)[1].split(
        "\n\n", 1
    )[0]
    assert " ".join(rules.split()) == (
        "- Only one `created`, `updated` or `deleted` event MUST be generated "
        "per `subject`. - If the interaction involved more than one of those "
        "actions, then the single event generated MUST be chosen in the "
        "following order of precedence: `deleted`, `created`, `updated`. "
        "- Only one event with the same `type` and `subject` combination "
        "MUST be generated."
    )
