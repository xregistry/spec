from copy import deepcopy
import json
from pathlib import Path
import re

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _http_section():
    text = (ROOT / "core" / "http.md").read_text(encoding="utf-8")
    heading = "#### `DELETE /<GROUPS>/<GID>/<RESOURCES>`\n"
    return text.split(heading, 1)[1].split("\n#### ", 1)[0]


def _blocks(text):
    return re.findall(r"```yaml\n(.*?)\n```", text, re.DOTALL)


def _request():
    blocks = _blocks(_http_section().split("**Examples:**", 1)[1])
    assert len(blocks) == 1
    assert blocks[0].startswith("DELETE /endpoints/ep1/messages\n")
    return json.loads(blocks[0][blocks[0].index("{"):])


def _instantiate_guard_sketch(block):
    body = block[block.index("{"):]
    body = "\n".join(line.split("#", 1)[0] for line in body.splitlines())
    body = body.replace('"<KEY>"', '"msg1"').replace("<UINTEGER>", "5")
    body = re.sub(r"(?<=[5}])\s+[?*]", "", body)
    return json.loads(body)


def _snapshot():
    return {
        "msg1": {"meta": {"epoch": 5}, "epoch": 9},
        "msg2": {"meta": {"epoch": 7}, "epoch": 11},
        "untouched": {"meta": {"epoch": 2}, "epoch": 3},
    }


def _guarded_targets(body, snapshot):
    if body is None:
        return set(snapshot)
    if type(body) is not dict:
        raise ValueError("id_map_required")
    targets = set()
    for resource_id, request in body.items():
        if type(request) is not dict:
            raise ValueError("resource_object_required")
        if resource_id not in snapshot:
            continue
        meta = request.get("meta", {})
        if type(meta) is not dict:
            raise ValueError("meta_object_required")
        if "epoch" in request and "epoch" not in meta:
            raise ValueError("misplaced_epoch")
        guard = meta.get("epoch")
        if guard is not None and guard != snapshot[resource_id]["meta"]["epoch"]:
            raise ValueError("mismatched_epoch")
        targets.add(resource_id)
    return targets


def test_resource_delete_sketch_matches_core_meta_epoch_shape():
    http_sketch = _blocks(_http_section())[0]
    core = (ROOT / "core" / "spec.md").read_text(encoding="utf-8")
    section = core.split(
        "3 - Deleting multiple Resource entities with `epoch` value checking", 1
    )[1].split("\n---", 1)[0]
    core_sketch = _blocks(section)[0]
    assert _instantiate_guard_sketch(http_sketch) == _instantiate_guard_sketch(core_sketch)
    assert _instantiate_guard_sketch(http_sketch)["msg1"] == _request()["msg1"]


def test_resource_delete_example_checks_meta_not_unequal_version_epoch():
    body = _request()
    snapshot = _snapshot()
    assert set(body) == {"msg1", "msg2"}
    assert body["msg1"]["meta"]["epoch"] == snapshot["msg1"]["meta"]["epoch"]
    assert body["msg1"]["meta"]["epoch"] != snapshot["msg1"]["epoch"]
    assert "epoch" not in body["msg1"]
    assert body["msg2"] == {}
    assert _guarded_targets(body, snapshot) == {"msg1", "msg2"}


@pytest.mark.parametrize("epoch", [5, 9], ids=["meta-value", "version-value"])
def test_top_level_epoch_is_not_a_resource_guard_alias(epoch):
    body = deepcopy(_request())
    body["msg1"] = {"epoch": epoch}
    with pytest.raises(ValueError, match="misplaced_epoch"):
        _guarded_targets(body, _snapshot())


def test_both_epoch_planes_use_meta_and_ignore_version_epoch():
    body = deepcopy(_request())
    body["msg1"]["epoch"] = 999
    assert _guarded_targets(body, _snapshot()) == {"msg1", "msg2"}


def test_both_epoch_planes_cannot_hide_a_meta_mismatch():
    body = deepcopy(_request())
    body["msg1"] = {"meta": {"epoch": 9}, "epoch": 5}
    with pytest.raises(ValueError, match="mismatched_epoch"):
        _guarded_targets(body, _snapshot())


@pytest.mark.parametrize(
    "unguarded", [{}, {"meta": {}}, {"meta": {"epoch": None}}],
    ids=["no-meta", "no-epoch", "null-epoch"],
)
def test_missing_and_null_meta_guards_do_not_check_version_epoch(unguarded):
    body = deepcopy(_request())
    body["msg1"] = unguarded
    assert _guarded_targets(body, _snapshot()) == {"msg1", "msg2"}


def test_resource_delete_ignores_missing_ids():
    body = deepcopy(_request())
    body["already-deleted"] = {"meta": {"epoch": 999}}
    assert _guarded_targets(body, _snapshot()) == {"msg1", "msg2"}


def test_empty_map_and_absent_body_have_different_targets():
    snapshot = _snapshot()
    assert _guarded_targets({}, snapshot) == set()
    assert _guarded_targets(None, snapshot) == set(snapshot)
    assert _guarded_targets(_request(), snapshot) == {"msg1", "msg2"}
    assert "untouched" not in _guarded_targets(_request(), snapshot)


def test_failed_guard_produces_no_partial_deletion_or_snapshot_mutation():
    example = _request()
    body = {"msg2": example["msg2"], "msg1": {"meta": {"epoch": 9}}}
    snapshot = _snapshot()
    before = deepcopy(snapshot)
    with pytest.raises(ValueError, match="mismatched_epoch"):
        _guarded_targets(body, snapshot)
    assert snapshot == before
    assert set(snapshot) == {"msg1", "msg2", "untouched"}


def test_resource_delete_body_is_an_id_map_not_an_array():
    with pytest.raises(ValueError, match="id_map_required"):
        _guarded_targets(list(_request()), _snapshot())


def test_primer_id_map_and_epoch_explanation_match_core():
    primer = (ROOT / "core" / "primer.md").read_text(encoding="utf-8")
    deletion = primer.split("### 11.5. Deleting entities\n", 1)[1].split("\n### ", 1)[0]
    assert "array" not in deletion
    assert "ID map" in deletion and "`{}`" in deletion
    assert "HTTP body is absent" in deletion
    assert "`meta.epoch`" in _http_section()

    core = (ROOT / "core" / "spec.md").read_text(encoding="utf-8")
    deletion = " ".join(core.split("### Deleting Entities\n", 1)[1].split("\n## ", 1)[0].split())
    assert "A map with no entities MUST NOT delete any entities" in deletion
    assert "If the request body is absent (does not include a map)" in deletion
    assert "Any error MUST result in the entire request being rejected" in deletion
    epoch = " ".join(core.split("##### `epoch` Attribute\n", 1)[1].split("\n##### ", 1)[0].split())
    assert "A value of `null` MUST be treated the same as a request with no `epoch`" in epoch
