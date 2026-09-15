from copy import deepcopy
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

import pytest


ROOT = Path(__file__).resolve().parents[1]
RESOURCE_POST = "#### `POST /<GROUPS>/<GID>/<RESOURCES>/<RID>`"
VERSIONS_GET = "#### `GET /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions`"
VERSION_GET = "#### `GET /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>`"
VERSION_PUT = "#### `PATCH` and `PUT /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>`"


def _section(heading):
    text = (ROOT / "core" / "http.md").read_text(encoding="utf-8")
    return text.split(heading + "\n", 1)[1].split("\n#### ", 1)[0]


def _blocks(text):
    return re.findall(r"```yaml\n(.*?)\n```", text, re.DOTALL)


def _examples(heading):
    return _blocks(_section(heading).split("**Examples:**", 1)[1])


def _json_body(block):
    return json.loads(block[block.index("{"):])


def _identity_fields(block):
    pairs = re.findall(
        r'^  "(messageid|schemaid|versionid|self|xid)": ("[^"\n]*")',
        block, re.MULTILINE,
    )
    fields = {name: json.loads(value) for name, value in pairs}
    assert len(fields) == len(pairs), "Duplicate identity fields"
    return fields


def _entity_path(url):
    return urlsplit(url).path.partition("$details")[0]


def _assert_version_identity(path, body):
    parts = path.removeprefix("/").split("/")
    assert len(parts) == 6 and parts[-2] == "versions"
    resource_id_field = {"messages": "messageid", "schemas": "schemaid"}[parts[2]]
    assert body[resource_id_field] == parts[3], "Resource ID differs from route"
    assert body["versionid"] == parts[5], "Version ID differs from route"
    assert body["xid"] == path, "XID differs from route"
    assert "$details" not in body["xid"]
    assert _entity_path(body["self"]) == path, "Self identifies another entity"


@pytest.mark.parametrize("index", [0, 1], ids=["request", "response"])
def test_message_collection_examples_use_message_ids_matching_map_keys(index):
    heading = "#### `PATCH` and `POST /<GROUPS>/<GID>/<RESOURCES>`"
    block = _examples(heading)[index]
    body, omitted = re.subn(
        r",\n\s*\.\.\. remainder of msg[12] definition excluded for brevity \.\.\.\n",
        "\n", block[block.index("{"):],
    )
    assert omitted == 2
    resources = json.loads(body)
    assert set(resources) == {"msg1", "msg2"}
    for key, resource in resources.items():
        assert resource["messageid"] == key
        assert "endpointid" not in resource


def test_version_collection_map_body_self_and_xid_identify_each_version():
    request, response = _examples(VERSIONS_GET)
    collection = request.splitlines()[0].split()[1]
    versions = _json_body(response)
    assert len(versions) == 1
    for key, body in versions.items():
        _assert_version_identity(collection + "/" + key, body)


def test_resource_post_metadata_response_identifies_the_requested_version():
    request, response = _examples(RESOURCE_POST)[-2:]
    resource = _entity_path(request.splitlines()[0].split()[1])
    version_id = _identity_fields(request)["versionid"]
    _assert_version_identity(
        resource + "/versions/" + version_id, _identity_fields(response)
    )


def test_schema_version_metadata_and_document_headers_match_requested_entity():
    metadata_request, metadata_response, document_request, document_response = (
        _examples(VERSION_GET)
    )
    path = _entity_path(metadata_request.splitlines()[0].split()[1])
    assert document_request.splitlines()[0].split()[1] == path
    metadata = _json_body(metadata_response)
    headers = dict(re.findall(r"^xRegistry-([^:]+): (.+)$", document_response, re.MULTILINE))
    _assert_version_identity(path, metadata)
    _assert_version_identity(path, headers)
    for field in ("schemaid", "versionid", "xid"):
        assert metadata[field] == headers[field]


def test_single_version_update_response_matches_requested_version_id():
    request, response = _examples(VERSION_PUT)[-2:]
    path = _entity_path(request.splitlines()[0].split()[1])
    _assert_version_identity(path, _identity_fields(response))


def test_version_identity_is_independent_of_the_default_flag():
    request, response = _examples(VERSION_GET)[:2]
    path = _entity_path(request.splitlines()[0].split()[1])
    body = _json_body(response)
    body["isdefault"] = False
    _assert_version_identity(path, body)
    assert body["versionid"] == path.rsplit("/", 1)[1]


def test_identity_comparison_does_not_accept_case_folded_aliases():
    request, response = _examples(VERSION_GET)[:2]
    path = _entity_path(request.splitlines()[0].split()[1])
    body = deepcopy(_json_body(response))
    body["schemaid"] = body["schemaid"].upper()
    assert body["schemaid"].casefold() == path.split("/")[4].casefold()
    with pytest.raises(AssertionError, match="Resource ID differs from route"):
        _assert_version_identity(path, body)


def test_version_collection_key_comments_use_versionid_not_groupid():
    heading = "#### `PATCH` and `POST /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions`"
    sketch = _section(heading).split("**Examples:**", 1)[0]
    comments = re.findall(r'"<KEY>": \{\s*# ([^\n]+)', sketch)
    assert comments == ["versionid", "versionid"]


def test_version_header_sketch_distinguishes_requested_and_default_versions():
    section = _section("##### Serializing Resource Domain-Specific Documents")
    sketches = [
        block for block in _blocks(section)
        if "xRegistry-versionid: <STRING>" in block
    ]
    assert len(sketches) == 2
    comments = [
        re.search(r"^xRegistry-versionid:.*# (.+)$", block, re.MULTILINE).group(1)
        for block in sketches
    ]
    assert comments == ["ID of the default Version", "ID of the requested Version"]
    assert "default Version" not in sketches[1]
    assert "Scalar extension attributes of the serialized Version MUST also appear" in section


def test_primer_preserves_case_with_sensitive_lookup_and_insensitive_uniqueness():
    primer = (ROOT / "core" / "primer.md").read_text(encoding="utf-8")
    section = primer.split("### 11.11. Naming and Case Sensitivity\n", 1)[1]
    section = section.split("\n### ", 1)[0]
    closing = " ".join(section.strip().split("\n\n")[-1].split())
    assert "preserving the original case of IDs" in closing
    assert "case-sensitive lookups" in closing
    assert "case-insensitive uniqueness" in closing

    core = (ROOT / "core" / "spec.md").read_text(encoding="utf-8")
    identity = core.split("##### `<SINGULAR>id` (`id`) Attribute\n", 1)[1]
    identity = " ".join(identity.split("\n##### ", 1)[0].split())
    assert "MUST be unique (case-insensitively)" in identity
    assert "MUST be treated as case-sensitive for look-up purposes" in identity
    assert 'MUST be treated as "not found"' in identity
