"""Check Schema format documentation against source models, not server defaulting."""

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = (ROOT / "schema" / "spec.md").read_text(encoding="utf-8")
CORE_MODEL = (ROOT / "core" / "model.md").read_text(encoding="utf-8")
MODEL = json.loads((ROOT / "schema" / "model.json").read_text(encoding="utf-8"))
GROUP_MODEL = MODEL["groups"]["schemagroups"]
VERSION_FORMAT = GROUP_MODEL["resources"]["schemas"]["attributes"]["format"]
GROUPS = SPEC.split("### 4.1. Schema Groups\n", 1)[1].split(
    "### 4.2. Schema Resources", 1
)[0]
FORMATS = SPEC.split("### 4.3. Schema Formats\n", 1)[1]


def _paragraph(text, start):
    return " ".join(text.split(start, 1)[1].split("\n\n", 1)[0].split())


def test_group_format_extension_is_optional_and_matches_authoritative_model():
    assert GROUP_MODEL["attributes"]["format"] == {"type": "string"}
    assert GROUP_MODEL["constraints"]["schemas.format"] == {"equals": "format"}
    assert _paragraph(GROUPS, "The Group (`<GROUP>`)") == (
        "name for the Schema Registry is `schemagroup` (singular). The plural, "
        "used as the collection name, is `schemagroups`. The Schema Group "
        "defines an OPTIONAL `format` extension attribute of type `string`."
    )
    assert "does not have any specific extension attributes" not in GROUPS
    assert _paragraph(SPEC, "### 2.3. Schema Group\n\n") == (
        "A Schema Group is a container for schemas that are related to each "
        "other in some application-defined way. Its OPTIONAL `format` "
        "attribute can constrain the formats of its schemas, as described in "
        "[Schema Groups](#41-schema-groups)."
    )


def test_group_format_absence_and_equality_follow_core_constraint_rules():
    assert _paragraph(GROUPS, "A schema group is") == (
        "a collection of schemas that are related to each other in some "
        "application-defined way. Without a value for the Group's `format`, a "
        "Schema Group MAY contain Schema Resources of different formats. When "
        "the Group's `format` has a value, the model's `schemas.format` "
        "constraint (`equals` set to `format`) requires every Version of "
        "every Schema Resource in that Group to use that value."
    )
    assert _paragraph(CORE_MODEL, "If the referenced Group attribute") == (
        "does not have a value at runtime, then the `equals` constraint "
        "enforcement for the Resource attribute MUST be silently ignored."
    )


def test_completed_version_format_is_required_and_matches_across_versions():
    assert VERSION_FORMAT == {
        "type": "string", "required": True, "matchversions": True
    }
    assert _paragraph(FORMATS, "Every completed Schema Version") == (
        "MUST have a non-null `format` value, including the default Version "
        "projection on a Schema Resource. The model sets `required` and "
        "`matchversions` to `true` for `format`, so all Versions of a Schema "
        "Resource MUST use the same `format` value."
    )


def test_serialization_requires_completed_format_but_not_group_format():
    sketch = SPEC.split("## 3. Schema Registry Model\n", 1)[1].split(
        "## 4. Schema Registry\n", 1
    )[0]
    annotations = re.findall(
        r'^( *)"format": "<STRING>",( \?)?$', sketch, re.MULTILINE
    )
    assert [(len(indent), marker == " ?") for indent, marker in annotations] == [
        (6, True), (10, False)
    ]


def test_group_default_can_supply_input_omission_not_a_missing_completed_value():
    block = GROUPS.split(
        "Additionally, if desired, a schemagroup-instance level constraint MAY be added:",
        1,
    )[1].split("```yaml\n", 1)[1].split("\n```", 1)[0]
    assert json.loads("{" + block + "}") == {
        "constraints": {"schemas.format": {"default": "JsonSchema/draft-07"}}
    }
    assert "default" not in VERSION_FORMAT
    assert "default" not in GROUP_MODEL["constraints"]["schemas.format"]
    assert "This equality constraint does not itself define a default value." in GROUPS
    assert _paragraph(FORMATS, "Client input MAY omit `format`") == (
        "when an applicable Group-instance default supplies it (see "
        "[Schema Groups](#41-schema-groups)). This does not make the completed "
        "value OPTIONAL: a completed Version without `format` is invalid."
    )
