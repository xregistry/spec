"""Check source rules and example relationships, not runtime xref behavior."""

import json
import re
from pathlib import Path


CORE = Path(__file__).resolve().parents[1] / "core"
SPEC = (CORE / "spec.md").read_text(encoding="utf-8")
MODEL = (CORE / "model.md").read_text(encoding="utf-8")


def _example_after(text, marker):
    return text.split(marker, 1)[1].split("```yaml\n", 1)[1].split("\n```", 1)[0]


def test_import_requirement_distinguishes_group_types_from_instances():
    rule = SPEC.split(
        "Both the source and target Resources MUST be", 1
    )[1].split("\n\n", 1)[0]
    assert " ".join(rule.split()) == (
        "of the same Resource model type, simply having similar Resource type "
        "definitions is not sufficient. When the source and target Resources "
        "belong to different Group types, the "
        "[`ximportresources`](./model.md#groupsstringximportresources) feature "
        "MUST be used to share the Resource type definition. Resources in "
        "different instances of the same Group type already share the "
        "Resource type definition and do not require an import."
    )


def test_same_group_type_alias_example_retains_distinct_instances():
    alias = json.loads(_example_after(
        SPEC, "For example: a `schema` Resource instance defined as:"
    ))
    target = json.loads(_example_after(
        SPEC, "So, if the target Resource (`sharedSchema`) is defined as:"
    ))
    source = _example_after(
        SPEC, "then the resulting serialization of the source Resource would be:"
    )
    source_xids = re.findall(r'^  "xid": "([^"]+)"', source, re.MULTILINE)
    assert alias == {
        "schemaid": "mySchema",
        "meta": {"xref": "/schemagroups/group2/schemas/sharedSchema"},
    }
    assert target["xid"] == alias["meta"]["xref"]
    assert source_xids == ["/schemagroups/group1/schemas/mySchema"]
    source_parts = source_xids[0].strip("/").split("/")
    target_parts = target["xid"].strip("/").split("/")
    assert source_parts[::2] == target_parts[::2] == ["schemagroups", "schemas"]
    assert (source_parts[1], target_parts[1]) == ("group1", "group2")


def test_cross_group_import_example_reuses_one_resource_declaration():
    example = _example_after(
        MODEL, "one Resource type (`messages`) under the `messagegroups` Group"
    )
    modelsource = json.loads("{" + example + "}")["modelsource"]
    assert modelsource["groups"] == {
        "messagegroups": {
            "singular": "messagegroup",
            "resources": {"messages": {"singular": "message"}},
        },
        "endpoints": {
            "singular": "endpoint",
            "ximportresources": ["/messagegroups/messages"],
        },
    }


def test_import_rules_allow_transitive_reuse_but_reject_self_and_cycles():
    section = MODEL.split("### `groups.<STRING>.ximportresources`", 1)[1]
    rules = section.split("where:\n", 1)[1].split("\n\n", 1)[0]
    assert " ".join(rules.split()) == (
        "- Each array value MUST be an `<XIDTYPE>` reference to another "
        "Group/Resource combination defined within the same Registry. "
        "It MUST NOT reference the same Group under which the "
        "`ximportresources` resides. "
        "- An empty array MAY be specified, implying no Resources are imported. "
        "- The definition of a Group MAY include an `ximportresources` "
        "directive that references a Resource from another Group that itself "
        "is defined via an `ximportresources`. However, transitive definitions "
        "of Resources MUST NOT result in a circular import chain."
    )
