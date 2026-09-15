import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit


HTTP = Path(__file__).resolve().parents[1] / "core" / "http.md"
RESOURCE = "/<GROUPS>/<GID>/<RESOURCES>/<RID>"
COLLECTION = RESOURCE + "/versions"
VERSION = COLLECTION + "/<VID>"


def _section(route):
    return HTTP.read_text(encoding="utf-8").split(
        f"#### `DELETE {route}`\n", 1
    )[1].split("\n#", 1)[0]


def _delete_blocks(section):
    return [
        block for block in re.findall(r"```yaml\n(.*?)\n```", section, re.DOTALL)
        if block.startswith("DELETE ")
    ]


def _url(block):
    return block.splitlines()[0].removeprefix("DELETE ")


def _instantiate(template, resource_id="msg1", version_id="1.0"):
    for name, value in {
        "<GROUPS>": "endpoints", "<GID>": "ep1", "<RESOURCES>": "messages",
        "<RID>": resource_id, "<VID>": version_id,
    }.items():
        template = template.replace(name, value)
    assert "<" not in template
    return template


def _route(url):
    parts = urlsplit(url).path.removeprefix("/").split("/")
    if any(not part for part in parts):
        raise ValueError("Empty path segment")
    if len(parts) == 4:
        return "resource", parts[3], None
    if len(parts) == 5 and parts[4] == "versions":
        return "versions", parts[3], None
    if len(parts) == 6 and parts[4] == "versions":
        return "version", parts[3], parts[5]
    raise ValueError("Not a Resource, Versions collection or Version route")


def test_versions_delete_sketch_matches_heading_and_concrete_collection_route():
    sketch, example = _delete_blocks(_section(COLLECTION))
    assert _url(sketch) == COLLECTION
    assert _instantiate(_url(sketch)) == _url(example)
    assert _route(_url(example)) == ("versions", "msg1", None)


def test_single_version_epoch_example_targets_the_same_version_as_unguarded():
    examples = _delete_blocks(_section(VERSION).split("**Examples:**", 1)[1])
    assert len(examples) == 2
    unguarded, guarded = map(_url, examples)
    assert urlsplit(guarded).path == urlsplit(unguarded).path
    assert parse_qs(urlsplit(guarded).query) == {"epoch": ["5"]}
    assert _route(guarded) == ("version", "msg1", "1.0")


def test_single_version_epoch_example_is_labeled_version_deletion():
    section = _section(VERSION)
    label = re.search(
        r"([^\n]+)\n\n```yaml\nDELETE [^\n]+\?epoch=5\n", section
    ).group(1)
    assert label == "Delete a Version, verifying its `epoch` value:"


def test_resource_named_versions_is_not_a_versions_collection():
    sketch = _delete_blocks(_section(RESOURCE))[0]
    url = _instantiate(_url(sketch), resource_id="versions")
    assert url.endswith("/messages/versions")
    assert _route(url) == ("resource", "versions", None)


def test_version_subroutes_below_resource_named_versions_remain_distinct():
    collection_sketch = _delete_blocks(_section(COLLECTION))[0]
    version_sketch = _delete_blocks(_section(VERSION))[0]
    collection = _instantiate(_url(collection_sketch), resource_id="versions")
    version = _instantiate(
        _url(version_sketch), resource_id="versions", version_id="versions"
    )
    assert _route(collection) == ("versions", "versions", None)
    assert _route(version) == ("version", "versions", "versions")
    assert version == collection + "/versions"


def test_missing_resource_segment_is_not_inferred():
    example = _delete_blocks(_section(COLLECTION))[1]
    collection = _url(example)
    missing_resource = collection.replace("/msg1/", "/")
    assert _route(collection)[0] == "versions"
    assert _route(missing_resource) == ("resource", "versions", None)


def test_epoch_query_does_not_infer_a_missing_version_segment():
    example = _delete_blocks(_section(VERSION).split("**Examples:**", 1)[1])[0]
    collection = _url(example).rsplit("/", 1)[0] + "?epoch=5"
    assert parse_qs(urlsplit(collection).query) == {"epoch": ["5"]}
    assert _route(collection) == ("versions", "msg1", None)


def test_epoch_queries_keep_resource_and_version_targets_distinct():
    resource = _url(_delete_blocks(_section(RESOURCE))[-1])
    version = _url(_delete_blocks(_section(VERSION))[-1])
    assert parse_qs(urlsplit(resource).query) == parse_qs(urlsplit(version).query) == {
        "epoch": ["5"]
    }
    assert _route(resource) == ("resource", "msg1", None)
    assert _route(version) == ("version", "msg1", "1.0")


def test_collection_body_epoch_is_attached_to_the_individual_version_id():
    example = _delete_blocks(_section(COLLECTION))[1]
    body = json.loads(example[example.index("{"):])
    assert set(body) == {"v1.0", "v2.0"}
    assert body["v1.0"] == {"epoch": 5}
    assert body["v2.0"] == {}
    for version_id in body:
        assert _route(_url(example) + "/" + version_id) == (
            "version", "msg1", version_id
        )
