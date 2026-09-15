import json
from datetime import datetime
from pathlib import Path

import pytest
import yaml
from yaml.constructor import ConstructorError
from yaml.resolver import BaseResolver


ROOT = Path(__file__).parent.parent
SAMPLE_PATTERNS = ("*.cereg", "*.cereg.yaml", "*.xreg.json")


def _unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key: {key}")
        result[key] = value
    return result


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key ({key})",
                key_node.start_mark,
            )
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueKeyLoader.add_constructor(
    BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping
)


def _sample_files():
    samples = []
    for sample_root in (ROOT / "core" / "samples", ROOT / "cloudevents" / "samples"):
        for pattern in SAMPLE_PATTERNS:
            samples.extend(sample_root.rglob(pattern))
    return sorted(set(samples))


@pytest.mark.parametrize("sample", _sample_files(), ids=lambda path: str(path.relative_to(ROOT)))
def test_sample_has_unique_keys(sample):
    with sample.open(encoding="utf-8") as sample_file:
        if sample.name.endswith(".yaml"):
            yaml.load(sample_file, Loader=_UniqueKeyLoader)
        else:
            json.load(sample_file, object_pairs_hook=_unique_json_object)


def test_contoso_crm_samples_use_current_model():
    with (ROOT / "core" / "samples" / "contoso-crm.cereg").open(
        encoding="utf-8"
    ) as sample_file:
        json_sample = json.load(sample_file, object_pairs_hook=_unique_json_object)
    with (ROOT / "core" / "samples" / "contoso-crm.cereg.yaml").open(
        encoding="utf-8"
    ) as sample_file:
        yaml_sample = yaml.load(sample_file, Loader=_UniqueKeyLoader)

    assert json_sample == yaml_sample
    assert "definitionGroups" not in json_sample
    assert "schemaGroups" not in json_sample

    endpoint = json_sample["endpoints"]["Contoso.CRM.Eventing.Http"]
    assert endpoint["usage"] == ["producer"]
    assert endpoint["messagegroups"] == ["/messagegroups/Contoso.CRM.Events"]
    assert endpoint["protocoloptions"]["endpoints"] == [
        {"uri": "https://erpsystem.com/events"}
    ]

    message_group = json_sample["messagegroups"]["Contoso.CRM.Events"]
    assert len(message_group["messages"]) == 10
    for message in message_group["messages"].values():
        assert "id" not in message
        assert "metadata" not in message
        assert "schemaurl" not in message
        assert message["envelopemetadata"]["time"]["type"] == "timestamp"
        assert message["dataschemaformat"] == "JSONSchema/draft-07"
        assert message["dataschemauri"].startswith(
            "/schemagroups/Contoso.CRM.Events/schemas/"
        )

    schema_group = json_sample["schemagroups"]["Contoso.CRM.Events"]
    assert len(schema_group["schemas"]) == 11
    for schema in schema_group["schemas"].values():
        assert schema["format"] == "JSONSchema/draft-07"
        for version in schema["versions"].values():
            assert version["format"] == schema["format"]


@pytest.fixture
def xref_examples():
    spec = (ROOT / "core" / "spec.md").read_text(encoding="utf-8")
    section = spec.split("#### Cross Referencing Resources\n", 1)[1].split(
        "\n### Meta Entity\n", 1
    )[0]
    markers = {
        "target": "So, if the target Resource (`sharedSchema`) is defined as:",
        "source": "then the resulting serialization of the source Resource would be:",
    }
    examples = {}
    for name, marker in markers.items():
        block = section.split(marker, 1)[1].split("```yaml\n", 1)[1].split(
            "\n```", 1
        )[0]
        # Only these two concrete examples are JSON, not every pseudo-JSON sketch.
        examples[name] = json.loads(block, object_pairs_hook=_unique_json_object)
    examples["meta"] = examples["source"]["meta"]
    return examples


@pytest.mark.parametrize(
    "entity, attribute, minute",
    [
        ("target", "createdat", 0),
        ("target", "modifiedat", 1),
        ("source", "createdat", 0),
        ("source", "modifiedat", 1),
        ("meta", "createdat", 0),
        ("meta", "modifiedat", 1),
    ],
)
def test_xref_example_timestamp_literals(xref_examples, entity, attribute, minute):
    value = xref_examples[entity][attribute]
    parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    assert parsed == datetime(2024, 1, 1, 12, minute, 0)
    assert value == parsed.strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.mark.parametrize(
    "entity, schema_id",
    [("target", "sharedSchema"), ("source", "mySchema"), ("meta", "mySchema")],
)
def test_xref_example_schema_id_keys_match_paths(xref_examples, entity, schema_id):
    document = xref_examples[entity]
    assert "resourceid" not in document
    assert document["schemaid"] == schema_id
    assert document["xid"].split("/schemas/", 1)[1].split("/", 1)[0] == schema_id


def test_xref_example_alias_relationships_are_preserved(xref_examples):
    target = xref_examples["target"]
    source = xref_examples["source"]
    meta = xref_examples["meta"]
    target_xid = "/schemagroups/group2/schemas/sharedSchema"
    source_xid = "/schemagroups/group1/schemas/mySchema"
    assert target["xid"] == meta["xref"] == target_xid
    assert source["xid"] == source_xid
    for document, xid in [(target, target_xid), (source, source_xid)]:
        assert document["self"] == "http://example.com" + xid
        assert document["metaurl"] == document["self"] + "/meta"
        assert document["versionsurl"] == document["self"] + "/versions"
        assert {
            key: document[key]
            for key in ["versionid", "epoch", "isdefault", "ancestorid", "versionscount"]
        } == {
            "versionid": "v1",
            "epoch": 2,
            "isdefault": True,
            "ancestorid": "v1",
            "versionscount": 1,
        }
    assert meta["self"] == source["metaurl"]
    assert meta["xid"] == source_xid + "/meta"
    assert meta["defaultversionid"] == source["versionid"]
    assert meta["defaultversionurl"] == source["versionsurl"] + "/v1"
    assert meta["defaultversionsticky"] is False
    assert meta["readonly"] is False


@pytest.mark.parametrize(
    "old, invalid",
    [("T", "-T"), ("2024-01-01", "2024-02-30")],
)
def test_xref_timestamp_parser_rejects_malformed_literals(xref_examples, old, invalid):
    value = xref_examples["target"]["createdat"].replace(old, invalid, 1)
    with pytest.raises(ValueError):
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
