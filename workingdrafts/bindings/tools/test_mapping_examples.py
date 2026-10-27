"""Offline conformance tests for the authored shared document-tree fixture."""

import copy
import errno
import hashlib
import json
import os
import shutil
import stat
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from urllib.parse import unquote

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from workingdrafts.bindings.tools import mapping_examples as document
from workingdrafts.bindings.tools.test_git_examples import GitFixture
from workingdrafts.bindings.tools.test_mapping_spec_examples import (
    DOCUMENT_HREF as WALKTHROUGH_DOCUMENT, walkthrough_source,
)
from workingdrafts.federation.tools.federation_examples import FederationError, load_example


SCHEMA_ROOT = Path(__file__).resolve().parents[1] / "schemas"


def test_neutral_mapping_adapter_keeps_full_model_separate_from_legacy_root():
    example = load_example("portable")
    before = copy.deepcopy(example)
    records, documents = document.example_records(example)
    root = next(record for record in records if record["kind"] == "registry")
    assert root["entity"]["model"]["groups"]["documents"]["resources"]["assets"]["metaattributes"]["xref"]["type"] == "xid"
    assert root["snapshot"] == {"scope": "/", "completeness": "offline-complete"}
    assert documents == {
        "/documents/main/assets/item/versions/v1": b'{"hello":"world"}\n',
        "/documents/main/assets/item/versions/v2": b"",
        "/documents/main/assets/CON/versions/a:b@c.": b"\x00\x01\xff\x7f\n",
    }
    records[0]["entity"]["registryid"] = "changed"
    documents["/documents/main/assets/item/versions/v1"] = b"changed"
    assert example == before
    legacy, _ = document.sample_records()
    assert "model" not in next(record for record in legacy if record["kind"] == "registry")["entity"]
    assert hashlib.sha256(document.encode_tree(*document.sample_records())["registry.json"]).hexdigest() == ROOT_SHA256
    generated = document.example_files()
    reader = document.DocumentTree(document.MemoryStore(generated))
    assert reader.metadata("/")["entity"]["registryid"] == "first"
    assert reader.model()["model"]["groups"]["mirrors"]["resources"]["assets"]["attributes"]["purpose"]["type"] == "string"
    assert reader.document("/documents/main/assets/item") == b'{"hello":"world"}\n'


@pytest.mark.parametrize("name", ["walkthrough", "portable", "offline", "linked", "first", "second"])
def test_neutral_mapping_example_files_select_each_capture_without_mutating_source(name):
    before = load_example(name)
    files = document.example_files(name)
    reader = document.DocumentTree(document.MemoryStore(files))
    assert reader.validate()["records"] == {
        "walkthrough": 5, "portable": 24, "offline": 25, "linked": 25, "first": 18, "second": 5,
    }[name]
    assert reader.metadata("/")["entity"]["registryid"] == {
        "walkthrough": "workshop", "portable": "first", "offline": "fixture-offline",
        "linked": "fixture-linked", "first": "first", "second": "second",
    }[name]
    assert load_example(name) == before


ITEM = "/documents/main/assets/item"
V1 = ITEM + "/versions/v1"
V2 = ITEM + "/versions/v2"
BINARY = "/documents/main/assets/CON/versions/a:b@c."
NOTE = "/documents/main/notes/item"
CATALOG = "/categories/main/registries/site"
COPY = "/mirrors/local/assets/copy"
CHAIN = "/mirrors/local/assets/chain"
DANGLING = "/mirrors/local/assets/dangling"
TIMESTAMPS = {
    "epoch": 1,
    "createdat": "2026-09-04T00:00:00Z",
    "modifiedat": "2026-09-04T00:00:00Z",
}
ROOT_SHA256 = "7e4c37ca61b2b875ee055a8fc67e5c90c48b344689823a12dc1fb0a6e33232bf"
EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
JSON_SHA256 = "c23110513472a63bd0ab22e37d6f9cdb95807fe31caad2f37d3abfde2ee7eec6"
AUTHORED_JSON = b'{"hello":"world"}\n'
FORMATTED_JSON = b' { "value": 1 }\r\n'
EXACT_BINARY = b"\x00\xff\x10\r\n"
ITEM_RECORD_READS = [
    "registry.json", "indexes/n3.json", "records/n4.json",
    "indexes/n4.json", "records/n8.json",
]
ITEM_STATE_READS = ITEM_RECORD_READS + ["records/n9.json", "indexes/n6.json"]
V1_READS = ITEM_STATE_READS + ["records/na.json"]
V2_READS = ITEM_STATE_READS + ["records/nb.json"]
BINARY_READS = [
    "registry.json", "indexes/n3.json", "records/n4.json",
    "indexes/n4.json", "records/n5.json", "records/n6.json",
    "indexes/n5.json", "records/n7.json",
]
COPY_READS = [
    "registry.json", "indexes/nb.json", "records/n10.json",
    "indexes/nc.json", "records/n13.json", "records/n14.json",
]
V1_ENTITY = {
    **TIMESTAMPS,
    "xid": V1,
    "assetid": "item",
    "versionid": "v1",
    "isdefault": True,
    "ancestorid": "v1",
    "labels": {"stage": "production", "note": ""},
    "contenttype": "application/json",
    "purpose": "primary",
}
V2_ENTITY = {
    **TIMESTAMPS,
    "xid": V2,
    "assetid": "item",
    "versionid": "v2",
    "isdefault": False,
    "ancestorid": "v1",
    "labels": {"stage": "development"},
    "contenttype": "application/octet-stream",
    "purpose": "empty",
}
META_ENTITY = {
    **TIMESTAMPS,
    "xid": ITEM + "/meta",
    "assetid": "item",
    "readonly": True,
    "defaultversionid": "v1",
    "defaultversionsticky": True,
}
EXPECTED_CAPABILITIES = {
    "available": {
        "capabilities": {"mutable": False},
        "entities": {"mutable": False},
        "model": {"mutable": False},
        "modelsource": {"mutable": False},
    },
    "flags": ["doc", "inline"],
    "pagination": False,
    "shortself": False,
    "specversions": ["1.0-rc4"],
}
EXPECTED_MODEL = {
    "attributes": {"fixture": {"type": "string"}},
    "groups": {
        "categories": {
            "singular": "category",
            "resources": {
                "registries": {
                    "singular": "registry",
                    "hasdocument": False,
                    "attributes": {"weburl": {"type": "url"}},
                },
            },
        },
        "documents": {
            "singular": "document",
            "resources": {
                "assets": {
                    "singular": "asset",
                    "attributes": {"purpose": {"type": "string"}},
                },
                "notes": {"singular": "note", "hasdocument": False},
            },
        },
        "independent": {
            "singular": "independent",
            "resources": {"assets": {"singular": "asset"}},
        },
        "mirrors": {
            "singular": "mirror",
            "ximportresources": ["/documents/assets"],
        },
    },
}


@pytest.fixture
def authored_files(mapping_sample_root):
    return {
        path.relative_to(mapping_sample_root).as_posix(): path.read_bytes()
        for path in mapping_sample_root.rglob("*") if path.is_file()
    }


@pytest.fixture
def tree(mapping_sample_root):
    return document.DocumentTree(document.FileStore(mapping_sample_root))


@pytest.fixture
def copied_tree(tmp_path, mapping_sample_root):
    return Path(shutil.copytree(mapping_sample_root, tmp_path / "tree"))


@pytest.fixture
def byte_state_records():
    """Explicit byte partitions on the owner's logical multi-domain dataset."""
    records, documents = document.sample_records()
    documents[V1] = FORMATTED_JSON
    documents[BINARY] = EXACT_BINARY
    for version, content, purpose in (
        ("v10", b"{}", "object"),
        ("v11", b"null", "null"),
    ):
        xid = ITEM + "/versions/" + version
        records.append({
            "kind": "version",
            "entity": {
                **TIMESTAMPS,
                "createdat": "2026-09-05T00:00:00Z",
                "modifiedat": "2026-09-05T00:00:00Z",
                "xid": xid,
                "assetid": "item",
                "versionid": version,
                "isdefault": False,
                "ancestorid": "v1",
                "labels": {"stage": purpose},
                "contenttype": "application/json",
                "purpose": purpose,
            },
        })
        documents[xid] = content
    return records, documents


@pytest.fixture
def byte_state_files(byte_state_records):
    return document.encode_tree(*byte_state_records)


def assert_error(caught, code, message):
    assert caught.value.code == code
    assert str(caught.value) == message


def follow_pointer(envelope, pointer):
    """Resolve output pointers independently of the helper's pointer encoder."""
    assert pointer.startswith("#/")
    current = envelope
    for token in unquote(pointer[2:]).split("/"):
        current = current[token.replace("~1", "/").replace("~0", "~")]
    return current


def assert_metadata_only_reads(reads):
    assert reads[0] == "registry.json"
    assert not any(name.startswith("documents/") for name in reads)
    assert len(reads) == len(set(reads))


def stat_with(info, **changes):
    fields = {
        name: getattr(info, name)
        for name in document._STAMP_FIELDS
    }
    fields["st_file_attributes"] = getattr(info, "st_file_attributes", 0)
    fields.update(changes)
    return SimpleNamespace(**fields)


@pytest.mark.parametrize(
    "kind,xid,expected,descendants,expected_reads",
    [
        pytest.param(
            "registry", "/",
            {
                **TIMESTAMPS, "xid": "/", "registryid": "first",
                "specversion": "1.0-rc4", "fixture": "document-tree",
                "modelsource": EXPECTED_MODEL, "capabilities": EXPECTED_CAPABILITIES,
                "self": "#/entity",
            },
            {"categories", "documents", "independent", "mirrors"}, None,
            id="registry",
        ),
        pytest.param(
            "group", "/documents/main",
            {**TIMESTAMPS, "xid": "/documents/main", "documentid": "main",
             "self": "#/entity"},
            {"assets", "notes"}, None, id="group",
        ),
        pytest.param(
            "resource", ITEM,
            {"xid": ITEM, "assetid": "item", "self": "#/entity",
             "metaurl": "#/entity/meta"},
            {"meta", "versions"},
            ITEM_STATE_READS + ["records/na.json", "records/nb.json"],
            id="resource",
        ),
        pytest.param(
            "meta", ITEM + "/meta",
            {**META_ENTITY, "self": "#/entity",
             "defaultversionurl": "#/related/defaultversion"},
            set(), V1_READS, id="meta",
        ),
        pytest.param(
            "version", V1, {**V1_ENTITY, "self": "#/entity"},
            set(), V1_READS, id="version",
        ),
    ],
)
def test_document_metadata_kinds_preserve_identity_and_extensions(
    tree, kind, xid, expected, descendants, expected_reads
):
    with patch.object(tree.store, "read", wraps=tree.store.read) as read:
        result = tree.metadata(xid)
    assert result["kind"] == kind
    assert descendants <= result["entity"].keys()
    navigation = descendants | {
        name + suffix for name in descendants for suffix in ("url", "count")
    }
    # metaurl is an explicit part of the Resource's expected scalar metadata.
    navigation.discard("metaurl")
    assert {
        key: value for key, value in result["entity"].items()
        if key not in navigation
    } == expected
    assert_metadata_only_reads(tree.reads)
    assert all(not call.args[0].startswith("documents/") for call in read.call_args_list)
    if expected_reads is not None:
        assert tree.reads == expected_reads
    if kind == "registry":
        assert result["snapshot"] == {"scope": "/", "completeness": "offline-complete"}
        assert result["source"] == {
            "uri": "https://example.com/registry", "revision": "fixture-1",
        }
        assert result["entity"]["categories"]["main"]["registries"]["site"][
            "versions"
        ]["v1"]["weburl"] == "https://example.com/cataloged-registry"
    if kind == "resource":
        assert result["entity"]["versions"]["v1"] == {
            **V1_ENTITY, "self": "#/entity/versions/v1",
        }
        assert result["entity"]["versions"]["v2"] == {
            **V2_ENTITY, "self": "#/entity/versions/v2",
        }
        assert "purpose" not in result["entity"]
    if kind == "group":
        assert list(result["entity"]["assets"]) == ["CON", "item"]
        assert list(result["entity"]["notes"]) == ["item"]
        assert result["entity"]["assetscount"] == 2
        assert result["entity"]["notescount"] == 1
    if kind == "meta":
        assert result["related"] == {
            "defaultversion": {**V1_ENTITY, "self": "#/related/defaultversion"},
        }
    assert tree.root_sha256 == ROOT_SHA256
    assert tree.store.pin is None


@pytest.mark.parametrize(
    "xid",
    [pytest.param("/", id="registry"),
     pytest.param("/documents/main", id="group"),
     pytest.param(ITEM + "/meta", id="meta"),
     pytest.param(V1, id="version")],
)
def test_document_extension_values_are_preserved_and_results_are_detached(xid):
    records, documents = document.sample_records()
    source = next(record for record in records if record["entity"]["xid"] == xid)
    source["entity"]["xfixture"] = {
        "region": "München", "values": [0, False, None, {"case": "MiXeD"}],
    }
    before = copy.deepcopy((records, documents))
    files = document.encode_tree(records, documents)
    store = document.MemoryStore(files)
    result_tree = document.DocumentTree(store)
    result = result_tree.metadata(xid)
    assert result["entity"]["xfixture"] == {
        "region": "München", "values": [0, False, None, {"case": "MiXeD"}],
    }
    assert result["entity"]["xid"] == xid
    result["entity"]["xfixture"]["values"][3]["case"] = "client edit"
    assert result_tree.metadata(xid)["entity"]["xfixture"]["values"][3] == {
        "case": "MiXeD",
    }
    assert (records, documents) == before
    assert store.files == files
    assert_metadata_only_reads(store.reads)


def test_document_metadata_and_json_document_are_separate(byte_state_files):
    store = document.MemoryStore(byte_state_files)
    result_tree = document.DocumentTree(store)
    metadata = result_tree.metadata(V1)
    assert metadata == {"kind": "version", "entity": {**V1_ENTITY, "self": "#/entity"}}
    # v10 sorts between v1 and v2: the selected v1 is still records/na.json.
    assert result_tree.reads == V1_READS
    before = list(result_tree.reads)
    data = result_tree.document(V1)
    assert data == b' { "value": 1 }\r\n'
    assert len(data) == 17
    assert hashlib.sha256(data).hexdigest() == JSON_SHA256
    assert result_tree.reads == before + ["documents/n1.bin"]
    assert set(metadata["entity"]).isdisjoint({"asset", "assetbase64", "document", "value"})


@pytest.mark.parametrize(
    "xid,expected,length,digest,href",
    [
        pytest.param(
            V1, b' { "value": 1 }\r\n', 17, JSON_SHA256,
            "documents/n1.bin", id="formatting-sensitive-json",
        ),
        pytest.param(
            BINARY, b"\x00\xff\x10\r\n", 5,
            "1151e4df6045153a472d1444fa216651a6c8bd93002410147de4ad3a4399ee0c",
            "documents/n0.bin", id="binary",
        ),
        pytest.param(V2, b"", 0, EMPTY_SHA256, "documents/n4.bin", id="zero-bytes"),
        pytest.param(
            ITEM + "/versions/v10", b"{}", 2,
            "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a",
            "documents/n2.bin", id="json-object",
        ),
        pytest.param(
            ITEM + "/versions/v11", b"null", 4,
            "74234e98afe7498fb5daf1f36ac2d78acc339464f950703b8c019892f982b90b",
            "documents/n3.bin", id="json-null",
        ),
    ],
)
def test_document_json_binary_and_empty_bytes_are_exact(
    byte_state_files, xid, expected, length, digest, href
):
    store = document.MemoryStore(byte_state_files)
    result_tree = document.DocumentTree(store)
    descriptor = result_tree.document_descriptor(xid)
    assert descriptor == {"kind": "local", "href": href, "size": length, "sha256": digest}
    assert_metadata_only_reads(store.reads)
    before = list(store.reads)
    data = result_tree.document(xid)
    assert data == expected
    assert type(data) is bytes
    assert len(data) == length
    assert hashlib.sha256(data).hexdigest() == digest
    assert store.reads == before + [href]
    assert result_tree.metadata(xid)["entity"]["xid"] == xid
    assert store.files == byte_state_files


@pytest.mark.parametrize(
    "xid,expected,length,href",
    [
        pytest.param(V2, b"", 0, "documents/n4.bin", id="present-zero"),
        pytest.param(ITEM + "/versions/v10", b"{}", 2, "documents/n2.bin", id="object"),
        pytest.param(ITEM + "/versions/v11", b"null", 4, "documents/n3.bin", id="null"),
    ],
)
def test_document_metadata_only_missing_and_zero_byte_states_are_distinct(
    byte_state_files, xid, expected, length, href
):
    present = document.DocumentTree(document.MemoryStore(byte_state_files))
    assert present.document(xid) == expected
    assert present.document_descriptor(xid)["size"] == length
    assert [name for name in present.reads if name.startswith("documents/")] == [href]

    missing_files = dict(byte_state_files)
    del missing_files[href]
    missing = document.DocumentTree(document.MemoryStore(missing_files))
    # Metadata does not need the missing domain blob.
    assert missing.metadata(xid)["entity"]["versionid"] == xid.rsplit("/", 1)[1]
    before = list(missing.reads)
    with pytest.raises(FederationError) as caught:
        missing.document(xid)
    assert_error(caught, "invalid_package", "Missing " + href)
    assert missing.reads == before

    metadata_only = document.DocumentTree(document.MemoryStore(byte_state_files))
    result = metadata_only.metadata(NOTE + "/versions/v1")
    assert result == {
        "kind": "version",
        "entity": {
            **TIMESTAMPS, "xid": NOTE + "/versions/v1", "noteid": "item",
            "versionid": "v1", "isdefault": True, "ancestorid": "v1",
            "labels": {"note": ""}, "self": "#/entity",
        },
    }
    before = list(metadata_only.reads)
    with pytest.raises(FederationError) as caught:
        metadata_only.document(NOTE)
    assert_error(caught, "unsupported_operation", "Resource hasdocument is false")
    assert metadata_only.reads == before
    assert_metadata_only_reads(metadata_only.reads)


@pytest.mark.parametrize(
    "xid,expected,version",
    [
        pytest.param(ITEM, FORMATTED_JSON, "v1", id="default-v1-not-newest"),
        pytest.param(V1, FORMATTED_JSON, "v1", id="explicit-v1"),
        pytest.param(V2, b"", "v2", id="explicit-v2"),
        pytest.param(ITEM + "/versions/v10", b"{}", "v10", id="explicit-v10"),
    ],
)
def test_document_default_and_explicit_versions_preserve_separate_pins(
    byte_state_files, xid, expected, version
):
    result_tree = document.DocumentTree(document.MemoryStore(byte_state_files))
    before_files = dict(byte_state_files)
    assert result_tree.document(xid) == expected
    resource = result_tree.metadata(ITEM)["entity"]
    assert resource["meta"]["defaultversionid"] == "v1"
    assert resource["versions"][version]["versionid"] == version
    assert resource["versions"][version]["xid"] == ITEM + "/versions/" + version
    assert resource["versions"]["v11"]["createdat"] > resource["versions"]["v1"]["createdat"]
    assert list(resource["versions"]) == ["v1", "v10", "v11", "v2"]
    catalog = result_tree.metadata(CATALOG + "/versions/v1")["entity"]
    assert catalog["registryid"] == "site"
    assert catalog["xid"] == CATALOG + "/versions/v1"
    assert catalog["weburl"] == "https://example.com/cataloged-registry"
    assert result_tree.root["source"] == {
        "uri": "https://example.com/registry", "revision": "fixture-1",
    }
    # File/Memory origin honestly has no immutable Git pin.
    assert result_tree.store.pin is None
    assert result_tree.root_sha256 == hashlib.sha256(
        byte_state_files["registry.json"]
    ).hexdigest()
    assert byte_state_files == before_files
    assert len([name for name in result_tree.reads if name.startswith("documents/")]) == 1


@pytest.mark.parametrize("version", ["V1", "v0", "v100"], ids=["wrong-case", "absent", "not-latest"])
def test_document_explicit_version_absence_never_falls_back(tree, version):
    xid = ITEM + "/versions/" + version
    with pytest.raises(FederationError) as caught:
        tree.document(xid)
    assert_error(caught, "not_found", "XID not found: " + xid)
    assert tree.reads == ITEM_STATE_READS
    assert tree.store.pin is None


@pytest.mark.parametrize(
    "xid",
    [pytest.param("/", id="registry"), pytest.param("/documents/main", id="group"),
     pytest.param(ITEM, id="resource"), pytest.param(ITEM + "/meta", id="meta"),
     pytest.param(V1, id="version")],
)
def test_document_view_navigation_and_suppression(tree, xid):
    envelope = tree.metadata(xid)
    entity = envelope["entity"]
    assert entity["self"] == "#/entity"
    assert follow_pointer(envelope, entity["self"]) is entity

    # Every generated navigation fragment must resolve inside this output.
    pending = [envelope]
    seen_xids = []
    while pending:
        current = pending.pop()
        if not isinstance(current, dict):
            continue
        pending.extend(value for value in current.values() if isinstance(value, dict))
        if "xid" not in current or "self" not in current:
            continue
        seen_xids.append(current["xid"])
        assert follow_pointer(envelope, current["self"]) is current
        assert "shortself" not in current
        assert "formatvalidated" not in current
        assert "formatvalidatedreason" not in current
        assert "compatibilityvalidated" not in current
        assert "compatibilityvalidatedreason" not in current
        for name in ("meta", "versions", "assets", "notes", "registries",
                     "categories", "documents", "independent", "mirrors"):
            if name in current:
                assert follow_pointer(envelope, current[name + "url"]) is current[name]
                if name != "meta":
                    assert current[name + "count"] == len(current[name])
        if "defaultversionurl" in current:
            selected = follow_pointer(envelope, current["defaultversionurl"])
            assert selected["versionid"] == current["defaultversionid"]
            assert selected["isdefault"] is True
        if "meta" in current:
            assert "defaultversionid" not in current
            assert "defaultversionsticky" not in current
            assert "isdefault" not in current
            assert "versionid" not in current
            assert "purpose" not in current
    assert xid in seen_xids
    assert_metadata_only_reads(tree.reads)
    if xid == ITEM:
        assert entity["metaurl"] == "#/entity/meta"
        assert entity["versionsurl"] == "#/entity/versions"
        assert entity["versionscount"] == 2
        assert entity["meta"]["defaultversionurl"] == "#/entity/versions/v1"
        assert entity["meta"] == {
            **META_ENTITY, "self": "#/entity/meta",
            "defaultversionurl": "#/entity/versions/v1",
        }
    if xid == ITEM + "/meta":
        assert entity["defaultversionurl"] == "#/related/defaultversion"
        assert envelope["related"]["defaultversion"]["self"] == "#/related/defaultversion"


@pytest.mark.parametrize(
    "container,expected_pointer",
    [
        pytest.param("/", "#/entity/documents/main/assets/item/versions/v1", id="registry-nested"),
        pytest.param("/documents/main", "#/entity/assets/item/versions/v1", id="group-nested"),
        pytest.param(ITEM, "#/entity/versions/v1", id="resource-nested"),
        pytest.param(ITEM + "/meta", "#/related/defaultversion", id="meta-singleton"),
    ],
)
def test_document_view_rebases_included_entity_pointers(tree, container, expected_pointer):
    standalone = tree.metadata(V1)
    assert standalone == {"kind": "version", "entity": {**V1_ENTITY, "self": "#/entity"}}
    assembled = tree.metadata(container)
    included = follow_pointer(assembled, expected_pointer)
    assert included == {**V1_ENTITY, "self": expected_pointer}
    assert follow_pointer(assembled, included["self"]) is included
    assert included["self"] != standalone["entity"]["self"]
    assert standalone["entity"]["self"] == "#/entity"
    assert_metadata_only_reads(tree.reads)


def test_document_collection_rebases_reserved_id_fragments(tree):
    envelope = tree.collection("/documents/main/assets")
    assert envelope["kind"] == "collection"
    assert envelope["xid"] == "/documents/main/assets"
    assert envelope["complete"] is True
    assert list(envelope["entities"]) == ["CON", "item"]
    binary = envelope["entities"]["CON"]
    assert binary["self"] == "#/entities/CON"
    assert binary["metaurl"] == "#/entities/CON/meta"
    assert binary["meta"]["defaultversionurl"] == "#/entities/CON/versions/a%3Ab%40c."
    version = follow_pointer(envelope, binary["meta"]["defaultversionurl"])
    assert version["xid"] == BINARY
    assert version["versionid"] == "a:b@c."
    assert version["self"] == "#/entities/CON/versions/a%3Ab%40c."
    assert_metadata_only_reads(tree.reads)


def test_document_view_never_points_to_absent_or_unretrievable_entities(tree):
    version = tree.metadata(V1)
    assert version == {"kind": "version", "entity": {**V1_ENTITY, "self": "#/entity"}}
    assert "metaurl" not in version["entity"]
    assert "defaultversionurl" not in version["entity"]
    assert "versionsurl" not in version["entity"]
    assert "asseturl" not in version["entity"]
    alias = tree.metadata(COPY)
    assert alias["entity"] == {
        "xid": COPY, "assetid": "copy", "self": "#/entity",
        "meta": {
            "xid": COPY + "/meta", "assetid": "copy", "xref": ITEM,
            "self": "#/entity/meta",
        },
        "metaurl": "#/entity/meta",
    }
    assert "related" not in alias
    assert "versions" not in alias["entity"]
    assert "versionsurl" not in alias["entity"]
    assert "defaultversionurl" not in alias["entity"]["meta"]
    empty = tree.metadata("/independent/MAIN")
    assert empty["entity"]["assets"] == {}
    assert empty["entity"]["assetscount"] == 0
    assert empty["entity"]["assetsurl"] == "#/entity/assets"
    assert follow_pointer(empty, "#/entity/assets") == {}
    assert_metadata_only_reads(tree.reads)


def test_document_alias_view_preserves_source_identity_one_hop(tree):
    with patch.object(tree.store, "read", wraps=tree.store.read) as read:
        view = tree.metadata(COPY)
    assert view == {
        "kind": "resource",
        "entity": {
            "xid": COPY, "assetid": "copy", "self": "#/entity",
            "meta": {
                "xid": COPY + "/meta", "assetid": "copy", "xref": ITEM,
                "self": "#/entity/meta",
            },
            "metaurl": "#/entity/meta",
        },
    }
    assert tree.reads == COPY_READS
    assert [call.args[0] for call in read.call_args_list] == COPY_READS[1:]

    # Effective metadata is used to select the alias, not to expand its view.
    selection = tree.collection(
        "/mirrors/local/assets", {"label": "stage", "value": "PRODUCTION"}
    )
    assert list(selection["entities"]) == ["copy"]
    assert selection["entities"]["copy"] == {
        "xid": COPY, "assetid": "copy", "self": "#/entities/copy",
        "meta": {
            "xid": COPY + "/meta", "assetid": "copy", "xref": ITEM,
            "self": "#/entities/copy/meta",
        },
        "metaurl": "#/entities/copy/meta",
    }
    assert_metadata_only_reads(tree.reads)
    before = list(tree.reads)
    assert tree.document(COPY) == AUTHORED_JSON
    assert tree.reads == before + ["documents/n1.bin"]
    assert "records/nb.json" not in tree.reads
    assert "documents/n2.bin" not in tree.reads


@pytest.mark.parametrize(
    "xid,identity,target,record,meta",
    [
        pytest.param(DANGLING, "dangling", "/documents/main/assets/missing",
                     "records/n15.json", "records/n16.json", id="dangling"),
        pytest.param(CHAIN, "chain", COPY,
                     "records/n11.json", "records/n12.json", id="alias-target"),
    ],
)
def test_document_dangling_alias_has_minimal_unexpanded_view(
    tree, xid, identity, target, record, meta
):
    result = tree.metadata(xid)
    assert result == {
        "kind": "resource",
        "entity": {
            "xid": xid, "assetid": identity, "self": "#/entity",
            "meta": {
                "xid": xid + "/meta", "assetid": identity,
                "xref": target, "self": "#/entity/meta",
            },
            "metaurl": "#/entity/meta",
        },
    }
    assert tree.reads == [
        "registry.json", "indexes/nb.json", "records/n10.json",
        "indexes/nc.json", record, meta,
    ]
    with pytest.raises(FederationError) as caught:
        tree.document(xid)
    assert_error(caught, "not_found", "No one-hop alias document")
    assert_metadata_only_reads(tree.reads)
    assert "records/na.json" not in tree.reads
    assert "records/n8.json" not in tree.reads


@pytest.mark.parametrize("operation", ["collection", "version"], ids=["versions-collection", "individual-version"])
def test_document_alias_versions_document_view_reports_cannot_doc_xref(tree, operation):
    with pytest.raises(FederationError) as caught:
        if operation == "collection":
            tree.collection(COPY + "/versions")
        else:
            tree.metadata(COPY + "/versions/v1")
    assert_error(caught, "unsupported_operation", "cannot_doc_xref")
    assert tree.reads == COPY_READS
    assert "records/na.json" not in tree.reads


@pytest.mark.parametrize(
    "target,message",
    [
        pytest.param("/independent/MAIN/assets/item", "xref Resource model type mismatch", id="independent-type"),
        pytest.param(NOTE, "xref Resource model type mismatch", id="wrong-type"),
        pytest.param(
            "https://example.com/registry/documents/main/assets/item",
            "Schema violation in records/n14.json at /entity/xref: pattern",
            id="absolute-xref",
        ),
    ],
)
def test_document_alias_renderer_rejects_wrong_type_and_absolute_targets(target, message):
    records, documents = document.sample_records()
    alias = next(record for record in records if record["entity"]["xid"] == COPY + "/meta")
    alias["entity"]["xref"] = target
    # Build the negative input only; all consumer validation/rendering below is real.
    with patch.object(document.DocumentTree, "validate", return_value=None):
        files = document.encode_tree(records, documents)
    before = dict(files)
    result_tree = document.DocumentTree(document.MemoryStore(files))
    with pytest.raises(FederationError) as caught:
        result_tree.metadata(COPY)
    assert_error(caught, "invalid_package", message)
    assert result_tree.reads == COPY_READS
    assert result_tree.store.files == before


def test_document_sibling_ids_are_case_insensitively_unique():
    records, documents = document.sample_records()
    records = [
        record for record in records
        if not record["entity"]["xid"].startswith("/documents/main/assets/CON")
    ]
    del documents[BINARY]
    for record in records:
        entity = record["entity"]
        for old in (ITEM, NOTE):
            if entity["xid"] == old or entity["xid"].startswith(old + "/"):
                entity["xid"] = old[:-4] + "Item" + entity["xid"][len(old):]
                entity["assetid" if old == ITEM else "noteid"] = "Item"
        if entity.get("xref") == ITEM:
            entity["xref"] = ITEM[:-4] + "Item"
    documents = {
        xid.replace("/assets/item/", "/assets/Item/"): data
        for xid, data in documents.items()
    }
    before = copy.deepcopy((records, documents))
    valid = document.DocumentTree(document.MemoryStore(document.encode_tree(records, documents)))
    exact = ITEM[:-4] + "Item"
    assert list(valid.collection("/documents/main/assets")["entities"]) == ["Item"]
    assert valid.metadata(exact)["entity"]["assetid"] == "Item"
    assert valid.metadata(NOTE[:-4] + "Item")["entity"]["noteid"] == "Item"
    with pytest.raises(FederationError) as caught:
        valid.metadata(ITEM)
    assert_error(caught, "not_found", "XID not found: " + ITEM)
    assert_metadata_only_reads(valid.reads)
    assert (records, documents) == before

    for record in before[0]:
        if record["entity"]["xid"] == exact or record["entity"]["xid"].startswith(exact + "/"):
            duplicate = copy.deepcopy(record)
            duplicate["entity"]["xid"] = duplicate["entity"]["xid"].replace(
                "/assets/Item", "/assets/item"
            )
            duplicate["entity"]["assetid"] = "item"
            records.append(duplicate)
    for xid, data in before[1].items():
        if xid.startswith(exact + "/"):
            documents[xid.replace("/assets/Item/", "/assets/item/")] = data
    with patch.object(document.DocumentTree, "validate", return_value=None):
        duplicate_files = document.encode_tree(records, documents)
    invalid = document.DocumentTree(document.MemoryStore(duplicate_files))
    with pytest.raises(FederationError) as caught:
        invalid.collection("/documents/main/assets")
    assert_error(caught, "invalid_package", "Case-insensitive sibling collision")
    assert invalid.reads == [
        "registry.json", "indexes/n3.json", "records/n4.json", "indexes/n4.json",
    ]


@pytest.mark.parametrize(
    "identity",
    ["asset-2", "CON", "con.txt", "NUL", "COM1", "LPT9", "a.", "A:B", "a@b", "a~b", "A" * 128],
    ids=["ordinary", "CON", "con-extension", "NUL", "COM1", "LPT9",
         "trailing-dot", "colon", "at", "tilde", "128-chars"],
)
def test_document_portable_path_mapping_is_injective(tmp_path, identity):
    records, documents = document.sample_records()
    old = "/documents/main/assets/CON"
    new = "/documents/main/assets/" + identity
    for record in records:
        entity = record["entity"]
        if entity["xid"] == old or entity["xid"].startswith(old + "/"):
            entity["xid"] = new + entity["xid"][len(old):]
            entity["assetid"] = identity
    binary = new + "/versions/a:b@c."
    documents[binary] = documents.pop(BINARY)
    before = copy.deepcopy((records, documents))
    files = document.encode_tree(records, documents)
    assert (records, documents) == before
    assert len({name.casefold() for name in files}) == len(files)
    for name, data in files.items():
        path = tmp_path.joinpath(*name.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    result_tree = document.DocumentTree(document.FileStore(tmp_path))
    assert result_tree.read_record(new)["entity"] == {"xid": new, "assetid": identity}
    assert result_tree.document_descriptor(binary) == {
        "kind": "local", "href": "documents/n0.bin", "size": 5,
        "sha256": "9c4c17b54893625385fa1d9c9ca1aa6ddc67917a22d6936afcad1dd9dab50f04",
    }
    assert result_tree.document(binary) == b"\x00\x01\xff\x7f\n"
    assert result_tree.reads == BINARY_READS + ["documents/n0.bin"]
    assert result_tree.metadata(ITEM)["entity"]["assetid"] == "item"
    assert result_tree.store.pin is None


@pytest.mark.parametrize(
    "mutation,code,message",
    [
        pytest.param("duplicate-allocation", "invalid_package", "Conflicting storage allocation", id="duplicate-allocation"),
        pytest.param("case-collision", "invalid_package", "Conflicting storage allocation", id="case-collision"),
    ],
)
def test_document_conflicting_portable_allocations_are_rejected_before_reads(
    authored_files, mutation, code, message
):
    root = json.loads(authored_files["registry.json"])
    if mutation == "duplicate-allocation":
        root["collections"][1]["href"] = root["collections"][0]["href"]
    else:
        root["collections"][1]["href"] = "indexes/N0.json"
    files = {**authored_files, "registry.json": json.dumps(root).encode("utf-8")}
    store = document.MemoryStore(files)
    with pytest.raises(FederationError) as caught:
        document.DocumentTree(store)
    assert_error(caught, code, message)
    assert store.reads == ["registry.json"]
    assert store.files == files


@pytest.mark.parametrize(
    "name,code,message",
    [
        pytest.param("../outside", "policy_denied", "Unsafe storage name", id="parent"),
        pytest.param("a/../../outside", "policy_denied", "Unsafe storage name", id="nested-parent"),
        pytest.param("/documents/n1.bin", "policy_denied", "Unsafe storage name", id="absolute-posix"),
        pytest.param("C:/outside", "policy_denied", "Unsafe storage name", id="absolute-drive"),
        pytest.param("//server/share/file", "policy_denied", "Unsafe storage name", id="unc"),
        pytest.param(r"documents\n1.bin", "policy_denied", "Unsafe storage name", id="backslash"),
        pytest.param("documents/%2e%2e/outside", "policy_denied", "Unsafe storage name", id="encoded-parent"),
        pytest.param("documents%2fn1.bin", "policy_denied", "Unsafe storage name", id="encoded-slash"),
        pytest.param("documents%5cn1.bin", "policy_denied", "Unsafe storage name", id="encoded-backslash"),
        pytest.param("documents//n1.bin", "policy_denied", "Unsafe storage name", id="empty-component"),
        pytest.param("documents/./n1.bin", "policy_denied", "Unsafe storage name", id="dot-component"),
        pytest.param("documents/n1.bin:stream", "policy_denied", "Unsafe storage name", id="alternate-stream"),
        pytest.param("documents/n1.bin\n", "policy_denied", "Unsafe storage name", id="trailing-newline"),
        pytest.param(None, "policy_denied", "Storage name must be a string", id="not-string"),
    ],
)
def test_file_document_tree_rejects_traversal_and_path_escape(
    copied_tree, tmp_path, name, code, message
):
    outside = tmp_path / "outside"
    outside.write_bytes(b"outside poison must never be opened")
    store = document.FileStore(copied_tree)
    with patch.object(document.os, "open", wraps=document.os.open) as opened:
        with pytest.raises(FederationError) as caught:
            store.read(name)
    assert_error(caught, code, message)
    opened.assert_not_called()
    assert store.reads == []
    assert store.total_bytes == 0
    assert outside.read_bytes() == b"outside poison must never be opened"


@pytest.mark.parametrize("name", ["documents/n01.bin", "documents/n1.json"])
def test_existing_document_paths_need_not_use_the_example_allocation_scheme(tmp_path, name):
    path = tmp_path.joinpath(*name.split("/"))
    path.parent.mkdir(parents=True)
    path.write_bytes(b"existing bytes")
    reader = document.FileStore(tmp_path)
    assert reader.read(name) == b"existing bytes"
    assert reader.reads == [name]
    assert reader.total_bytes == 14


def test_file_document_tree_rejects_symlink_escape(copied_tree, tmp_path):
    store = document.FileStore(copied_tree)
    assert store.read("documents/n2.bin") == b""
    link = copied_tree / "documents" / "n1.bin"
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"outside poison")
    link.unlink()
    original_lstat = Path.lstat
    observations = []
    try:
        link.symlink_to(outside)
        policy_metadata = nullcontext()
    except OSError as error:
        # Windows often denies unprivileged symlink creation. Still execute the
        # real helper guard, mocking only the stdlib metadata it consumes.
        assert error.errno in (errno.EACCES, errno.EPERM) or error.winerror == 1314
        link.write_bytes(str(outside).encode("utf-8"))

        def linked_lstat(path, *args, **kwargs):
            info = original_lstat(path, *args, **kwargs)
            if path == link:
                observations.append("symlink metadata")
                return stat_with(info, st_mode=stat.S_IFLNK | 0o777)
            return info

        policy_metadata = patch.object(Path, "lstat", autospec=True, side_effect=linked_lstat)
    with policy_metadata, patch.object(document.os, "open", wraps=document.os.open) as opened:
        with pytest.raises(FederationError) as caught:
            store.read("documents/n1.bin")
    assert_error(caught, "policy_denied", "Symlink or reparse point prohibited")
    opened.assert_not_called()
    assert store.reads == ["documents/n2.bin"]
    assert store.total_bytes == 0
    assert outside.read_bytes() == b"outside poison"
    # In fallback mode the observation proves this was not a test-only checker.
    assert link.is_symlink() or observations == ["symlink metadata"]


@pytest.mark.parametrize("location", ["directory", "file"], ids=["ancestor-junction", "leaf-reparse"])
def test_file_document_tree_rejects_reparse_escape(copied_tree, tmp_path, location):
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"outside reparse target")
    store = document.FileStore(copied_tree)
    assert store.read("documents/n2.bin") == b""
    target = copied_tree / "documents"
    if location == "file":
        target = target / "n1.bin"
    original_lstat = Path.lstat
    observations = []

    def reparse_lstat(path, *args, **kwargs):
        info = original_lstat(path, *args, **kwargs)
        if path == target:
            observations.append(path)
            return stat_with(info, st_file_attributes=0x400)
        return info

    with patch.object(Path, "lstat", autospec=True, side_effect=reparse_lstat):
        with patch.object(document.os, "open", wraps=document.os.open) as opened:
            with pytest.raises(FederationError) as caught:
                store.read("documents/n1.bin")
    assert_error(caught, "policy_denied", "Symlink or reparse point prohibited")
    assert observations == [target]
    opened.assert_not_called()
    assert store.reads == ["documents/n2.bin"]
    assert store.total_bytes == 0
    assert outside.read_bytes() == b"outside reparse target"


@pytest.mark.parametrize(
    "missing,code,reads",
    [
        pytest.param("registry.json", "not_found", [], id="registry"),
        pytest.param("records/n8.json", "invalid_package", ITEM_RECORD_READS[:-1], id="indexed-record"),
        pytest.param("indexes/n6.json", "invalid_package", ITEM_STATE_READS[:-1], id="versions-index"),
        pytest.param("documents/n1.bin", "invalid_package", V1_READS, id="document"),
    ],
)
def test_file_document_tree_missing_content_is_not_empty(copied_tree, missing, code, reads):
    present = document.DocumentTree(document.FileStore(copied_tree))
    assert present.document(V2) == b""
    assert present.reads == V2_READS + ["documents/n2.bin"]
    copied_tree.joinpath(*missing.split("/")).unlink()
    store = document.FileStore(copied_tree)
    with pytest.raises(FederationError) as caught:
        selected = document.DocumentTree(store)
        selected.document(ITEM)
    assert caught.value.code == code
    cause = caught.value.__cause__
    assert isinstance(cause, FileNotFoundError)
    assert cause.errno == errno.ENOENT
    # Keep the frozen diagnostic prefix exact without depending on OS locale.
    assert str(caught.value) == f"Cannot access {Path(missing).name}: {cause.strerror}"
    assert store.reads == reads
    assert "documents/n2.bin" not in store.reads


def test_file_document_tree_absent_xid_is_distinct_from_missing_storage(tree):
    with pytest.raises(FederationError) as caught:
        tree.document("/documents/main/assets/absent")
    assert_error(caught, "not_found", "XID not found: /documents/main/assets/absent")
    assert tree.reads == ITEM_RECORD_READS[:-1]
    assert tree.document(V2) == b""
    assert tree.reads == V2_READS + ["documents/n2.bin"]


@pytest.mark.parametrize(
    "changed_call,message,expected_trace",
    [
        pytest.param(
            1, "File replaced during open",
            ["lstat", "open", "fstat:changed", "close"],
            id="replaced-during-open",
        ),
        pytest.param(
            2, "File changed during read",
            ["lstat", "open", "fstat:stable", "lstat", "read:19", "fstat:changed", "close"],
            id="changed-during-read",
        ),
    ],
)
def test_file_document_tree_change_during_read_is_inconsistent_snapshot(
    copied_tree, changed_call, message, expected_trace
):
    store = document.FileStore(copied_tree)
    target = copied_tree / "documents" / "n1.bin"
    original_lstat = Path.lstat
    original_open = document.os.open
    original_fdopen = document.os.fdopen
    original_fstat = document.os.fstat
    trace = []
    streams = []
    fstat_calls = 0

    def checked_lstat(path, *args, **kwargs):
        if path == target:
            trace.append("lstat")
        return original_lstat(path, *args, **kwargs)

    def traced_open(path, flags):
        assert path == target
        assert flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC) == 0
        trace.append("open")
        return original_open(path, flags)

    def changing_fstat(fd):
        nonlocal fstat_calls
        fstat_calls += 1
        info = original_fstat(fd)
        if fstat_calls == changed_call:
            trace.append("fstat:changed")
            return stat_with(info, st_mtime_ns=info.st_mtime_ns + 1)
        trace.append("fstat:stable")
        return info

    def traced_fdopen(fd, mode):
        stream = original_fdopen(fd, mode)
        streams.append(stream)
        proxy = MagicMock(wraps=stream)
        proxy.__enter__.return_value = proxy

        def read(size):
            trace.append(f"read:{size}")
            return stream.read(size)

        def close(*args):
            trace.append("close")
            return stream.__exit__(*args)

        proxy.read.side_effect = read
        proxy.__exit__.side_effect = close
        return proxy

    with patch.object(Path, "lstat", autospec=True, side_effect=checked_lstat):
        with patch.object(document.os, "open", side_effect=traced_open):
            with patch.object(document.os, "fdopen", side_effect=traced_fdopen):
                with patch.object(document.os, "fstat", side_effect=changing_fstat):
                    with pytest.raises(FederationError) as caught:
                        store.read("documents/n1.bin")
    assert_error(caught, "inconsistent_snapshot", message)
    assert trace == expected_trace
    assert len(streams) == 1 and streams[0].closed
    assert store.reads == []
    assert store.total_bytes == 0
    assert store._observed == {}
    assert target.read_bytes() == AUTHORED_JSON


@pytest.mark.parametrize(
    "operation,message",
    [
        pytest.param("reread", "File changed between reads", id="between-reads"),
        pytest.param("finish", "Snapshot changed during operation", id="finish-checks-cached-file"),
    ],
)
def test_file_document_tree_detects_change_to_previously_observed_file(
    copied_tree, operation, message
):
    store = document.FileStore(copied_tree)
    target = copied_tree / "documents" / "n1.bin"
    assert store.read("documents/n1.bin") == AUTHORED_JSON
    original_lstat = Path.lstat
    trace = []

    def changed_lstat(path, *args, **kwargs):
        info = original_lstat(path, *args, **kwargs)
        if path == target:
            trace.append("lstat:changed")
            return stat_with(info, st_ino=info.st_ino + 1)
        return info

    with patch.object(Path, "lstat", autospec=True, side_effect=changed_lstat):
        with patch.object(document.os, "open", wraps=document.os.open) as opened:
            with pytest.raises(FederationError) as caught:
                if operation == "reread":
                    store.read("documents/n1.bin")
                else:
                    store.finish()
    assert_error(caught, "inconsistent_snapshot", message)
    assert trace == ["lstat:changed"]
    opened.assert_not_called()
    assert store.reads == ["documents/n1.bin"]
    assert store.total_bytes == 18


def test_file_document_tree_short_read_does_not_become_empty_content(copied_tree):
    store = document.FileStore(copied_tree)
    original_fdopen = document.os.fdopen
    proxies = []

    def short_fdopen(fd, mode):
        stream = original_fdopen(fd, mode)
        proxy = MagicMock(wraps=stream)
        proxy.__enter__.return_value = proxy
        proxy.__exit__.side_effect = stream.__exit__
        proxy.read.return_value = b""
        proxies.append(proxy)
        return proxy

    with patch.object(document.os, "fdopen", side_effect=short_fdopen):
        with pytest.raises(FederationError) as caught:
            store.read("documents/n1.bin")
    assert_error(caught, "inconsistent_snapshot", "File read was not stable")
    assert len(proxies) == 1
    proxies[0].read.assert_called_once_with(19)
    assert store.reads == []
    assert store.total_bytes == 0
    assert (copied_tree / "documents" / "n1.bin").read_bytes() == AUTHORED_JSON


@pytest.mark.parametrize("terminal_slash", [False, True], ids=["plain", "terminal-slash"])
def test_file_root_decodes_once_and_preserves_explicit_boundary(tmp_path, terminal_slash):
    root = tmp_path / "café %2e%2e"
    root.mkdir()
    endpoint = root.as_uri() + ("/" if terminal_slash else "")
    profile = {"name": "file", "endpoint": endpoint, "parameters": {"layout": "document-tree"}}
    before = copy.deepcopy(profile)
    with patch.object(Path, "read_bytes", autospec=True) as read:
        selected = document.file_root(profile, tmp_path)
    assert selected == root
    assert selected.name == "café %2e%2e"
    assert profile == before
    read.assert_not_called()


def test_file_root_boundary_is_not_a_string_prefix(tmp_path):
    boundary = tmp_path / "safe"
    outside = tmp_path / "safe-other"
    boundary.mkdir()
    outside.mkdir()
    profile = {
        "name": "file", "endpoint": outside.as_uri(),
        "parameters": {"layout": "document-tree"},
    }
    before = copy.deepcopy(profile)
    original_lstat = Path.lstat
    observed = []

    def traced_lstat(path, *args, **kwargs):
        observed.append(path)
        return original_lstat(path, *args, **kwargs)

    with patch.object(Path, "lstat", autospec=True, side_effect=traced_lstat):
        with pytest.raises(FederationError) as caught:
            document.file_root(profile, boundary)
    assert_error(caught, "policy_denied", "Root is outside boundary")
    assert boundary in observed
    assert outside not in observed
    assert profile == before


@pytest.mark.parametrize(
    "suffix,message",
    [
        pytest.param("/../outside", "Empty or dot file URI component", id="parent"),
        pytest.param("/%2e%2e/outside", "Empty or dot file URI component", id="encoded-parent"),
        pytest.param("/a/../../outside", "Empty or dot file URI component", id="nested-parent"),
        pytest.param("//outside", "Empty or dot file URI component", id="empty-component"),
        pytest.param("/a%2fb", "Encoded separator prohibited", id="encoded-slash"),
        pytest.param("/a%5Cb", "Encoded separator prohibited", id="encoded-backslash"),
        pytest.param("/%00bad", "Unsafe file URI character", id="encoded-nul"),
        pytest.param("/%ff", "File URI is not UTF-8", id="non-utf8"),
    ],
)
def test_file_root_rejects_unsafe_decoded_components_before_filesystem_access(
    tmp_path, suffix, message
):
    profile = {
        "name": "file", "endpoint": tmp_path.as_uri() + suffix,
        "parameters": {"layout": "document-tree"},
    }
    before = copy.deepcopy(profile)
    with patch.object(Path, "lstat", autospec=True) as lstat:
        with pytest.raises(FederationError) as caught:
            document.file_root(profile, tmp_path)
    code = "invalid_package" if suffix == "/%ff" else "policy_denied"
    assert_error(caught, code, message)
    lstat.assert_not_called()
    assert profile == before


@pytest.mark.parametrize(
    "path",
    ["../outside", "/absolute", "a/../../outside", r"a\b", "a//b",
     "a/", "C:/tree", "%2e%2e", "CON", "con.txt", "NUL", "COM1", "LPT9", "a.", "a" * 65],
    ids=["parent", "absolute", "nested-parent", "backslash", "empty-component",
         "terminal-slash", "drive", "encoded-parent", "CON", "con-extension",
         "NUL", "COM1", "LPT9", "trailing-dot", "65-char-component"],
)
def test_git_root_path_policy_rejects_escape_before_object_access(tmp_path, path):
    with patch.object(document.subprocess, "run") as invoked:
        with patch.object(Path, "lstat", autospec=True) as lstat:
            with pytest.raises(FederationError) as caught:
                document.GitStore(tmp_path / "no-object-store", "refs/heads/main", path)
    assert_error(caught, "policy_denied", "Unsafe or nonportable Git root")
    invoked.assert_not_called()
    lstat.assert_not_called()


@pytest.mark.parametrize(
    "revision,message",
    [
        pytest.param("", "Missing Git revision", id="empty"),
        pytest.param(None, "Missing Git revision", id="none"),
        pytest.param("HEAD", "Revision must be a full ref or complete object ID", id="HEAD"),
        pytest.param("main", "Revision must be a full ref or complete object ID", id="shorthand"),
        pytest.param("a" * 39, "Revision must be a full ref or complete object ID", id="abbreviated-oid"),
        pytest.param("refs/heads/main~1", "Revision must be a full ref or complete object ID", id="ancestor"),
        pytest.param("refs/heads/main^{}", "Revision must be a full ref or complete object ID", id="peeling-expression"),
        pytest.param("refs/heads/main:registry.json", "Revision must be a full ref or complete object ID", id="tree-expression"),
        pytest.param("refs/heads/main@{1}", "Revision must be a full ref or complete object ID", id="reflog"),
        pytest.param("refs/heads/a.lock", "Revision must be a full ref or complete object ID", id="lock-suffix"),
        pytest.param("refs/heads//main", "Revision must be a full ref or complete object ID", id="empty-component"),
    ],
)
def test_git_revision_validation_precedes_local_store_access(tmp_path, revision, message):
    with patch.object(document.subprocess, "run") as invoked:
        with patch.object(Path, "lstat", autospec=True) as lstat:
            with pytest.raises(FederationError) as caught:
                document.GitStore(tmp_path / "no-object-store", revision)
    assert_error(caught, "invalid_package", message)
    invoked.assert_not_called()
    lstat.assert_not_called()


@pytest.mark.parametrize(
    "parameters,revision,root",
    [
        pytest.param({"revision": "refs/heads/main"}, "refs/heads/main", "xregistry", id="omitted-default"),
        pytest.param({"revision": "refs/heads/main", "path": ""}, "refs/heads/main", "", id="empty-root"),
        pytest.param({"revision": "refs/tags/release-1", "path": "catalogs/main"},
                     "refs/tags/release-1", "catalogs/main", id="nested-root"),
        pytest.param({"revision": "A" * 40}, "a" * 40, "xregistry", id="complete-sha1-normalized"),
        pytest.param({"revision": "B" * 64}, "b" * 64, "xregistry", id="complete-sha256-normalized"),
        pytest.param({"revision": "refs/heads/main", "path": "a" * 64},
                     "refs/heads/main", "a" * 64, id="64-char-component"),
    ],
)
def test_git_locator_keeps_endpoint_revision_and_root_separate(parameters, revision, root):
    profile = {
        "name": "git", "endpoint": "https://example.com/registries.git",
        "parameters": parameters,
    }
    before = copy.deepcopy(profile)
    with patch.object(document.subprocess, "run") as invoked:
        result = document.git_locator(profile)
    assert result == ("https://example.com/registries.git", revision, root)
    assert profile == before
    invoked.assert_not_called()


@pytest.mark.parametrize("location", ["store", "objects"], ids=["store-reparse", "object-directory-reparse"])
def test_git_store_rejects_reparse_before_any_git_command(tmp_path, location):
    root = tmp_path / "store"
    objects = root / "objects"
    objects.mkdir(parents=True)
    target = root if location == "store" else objects
    original_lstat = Path.lstat
    observations = []

    def reparse_lstat(path, *args, **kwargs):
        info = original_lstat(path, *args, **kwargs)
        if path == target:
            observations.append(path)
            return stat_with(info, st_file_attributes=0x400)
        return info

    with patch.object(Path, "lstat", autospec=True, side_effect=reparse_lstat):
        with patch.object(document.subprocess, "run") as invoked:
            with pytest.raises(FederationError) as caught:
                document.GitStore(root, "refs/heads/main")
    assert_error(caught, "policy_denied", "Symlink or reparse point prohibited")
    assert observations == [target]
    invoked.assert_not_called()


@pytest.mark.parametrize(
    "namespace,number,expected",
    [
        pytest.param("records", 0, "records/n0.json", id="zero"),
        pytest.param("indexes", 26, "indexes/n1a.json", id="interior"),
        pytest.param("documents", 15, "documents/nf.bin", id="last-single-digit"),
        pytest.param("documents", 16, "documents/n10.bin", id="first-two-digits"),
        pytest.param("records", 2 ** 128 - 1, "records/n" + "f" * 32 + ".json", id="full-chunk"),
        pytest.param("records", 2 ** 128, "records/n1" + "0" * 31 + "/n0.json", id="next-chunk"),
    ],
)
def test_document_storage_allocations_are_minimal_opaque_hex(namespace, number, expected):
    actual = document.storage_path(namespace, number)
    assert actual == expected
    assert document._storage_name(actual, namespace) == expected
    assert document.storage_path(namespace, number + 1) != actual


@pytest.mark.parametrize("number", [-1, True, 1.0, None], ids=["negative", "bool", "float", "none"])
def test_document_storage_allocation_rejects_noninteger_ordinals(number):
    with pytest.raises(FederationError) as caught:
        document.storage_path("records", number)
    assert_error(caught, "invalid_package", "Invalid storage allocation")
    assert document.storage_path("records", 1) == "records/n1.json"


def test_document_storage_name_length_limit_is_inclusive():
    at_limit = document.storage_path("documents", int("1" + "0" * 3840, 16))
    over_limit = document.storage_path("documents", int("1" + "0" * 3841, 16))
    assert len(at_limit) == 4096
    assert len(over_limit) == 4097
    store = document.MemoryStore({at_limit: b"boundary bytes", over_limit: b"forbidden"})
    assert store.read(at_limit) == b"boundary bytes"
    with pytest.raises(FederationError) as caught:
        store.read(over_limit)
    assert_error(caught, "limit_exceeded", "Storage path length limit")
    assert store.reads == [at_limit]
    assert store.total_bytes == 14


@pytest.mark.parametrize(
    "schema_name,fixture_name,required_field",
    [
        pytest.param("record", "registry.json", "entity", id="registry-record"),
        pytest.param("record", "records/n4.json", "entity", id="group-record"),
        pytest.param("record", "records/n8.json", "meta", id="resource-record"),
        pytest.param("record", "records/n9.json", "entity", id="meta-record"),
        pytest.param("record", "records/na.json", "document", id="version-record"),
        pytest.param("index", "indexes/n6.json", "count", id="collection-index"),
    ],
)
def test_document_fixtures_validate_and_missing_required_field_fails(
    authored_files, schema_name, fixture_name, required_field
):
    schemas = {
        name: json.loads((SCHEMA_ROOT / f"document-{name}.schema.json").read_bytes())
        for name in ("record", "index")
    }
    registry = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas.values()
    )
    validator = Draft202012Validator(
        schemas[schema_name], registry=registry, format_checker=FormatChecker()
    )
    instance = json.loads(authored_files[fixture_name])
    before = copy.deepcopy(instance)
    assert list(validator.iter_errors(instance)) == []
    invalid = copy.deepcopy(instance)
    del invalid[required_field]
    errors = list(validator.iter_errors(invalid))
    assert any(
        error.validator == "required"
        and error.message == f"'{required_field}' is a required property"
        and list(error.path) == []
        for error in errors
    )
    assert instance == before


def test_document_authored_multidomain_fixture_has_complete_exact_closure(tree):
    assert tree.validate() == {
        "records": 24, "indexes": 13, "documents": 3,
        "rootsha256": ROOT_SHA256, "completeness": "offline-complete", "pin": None,
    }
    assert len(tree.reads) == len(set(tree.reads)) == 40
    assert [name for name in tree.reads if name.startswith("documents/")] == [
        "documents/n0.bin", "documents/n1.bin", "documents/n2.bin",
    ]
    assert ".gitattributes" not in tree.reads
    assert tree.root["entity"]["modelsource"] == EXPECTED_MODEL
    assert tree.document(V1) == b'{"hello":"world"}\n'
    assert hashlib.sha256(tree.document(BINARY)).hexdigest() == (
        "9c4c17b54893625385fa1d9c9ca1aa6ddc67917a22d6936afcad1dd9dab50f04"
    )
    assert tree.document(V2) == b""


def test_document_model_and_capabilities_reads_are_detached_and_root_only(tree):
    model = tree.model()
    capabilities = tree.capabilities()
    assert model == {"modelsource": EXPECTED_MODEL}
    assert capabilities == EXPECTED_CAPABILITIES
    assert tree.reads == ["registry.json"]
    model["modelsource"]["groups"]["mirrors"]["ximportresources"].clear()
    capabilities["available"]["entities"]["mutable"] = True
    assert tree.model() == {"modelsource": EXPECTED_MODEL}
    assert tree.capabilities() == EXPECTED_CAPABILITIES
    assert tree.reads == ["registry.json"]
    assert tree.root_sha256 == ROOT_SHA256


def test_document_captured_model_includes_preserve_base_without_retrieval(authored_files):
    root = json.loads(authored_files["registry.json"])
    original = {"$include": "parts/model.json", "attributes": {"fixture": {"type": "string"}}}
    root["entity"]["modelsource"] = original
    root["resolvedmodelsource"] = copy.deepcopy(EXPECTED_MODEL)
    root["modelbase"] = "https://example.com/captured/models/"
    files = {**authored_files, "registry.json": json.dumps(root).encode("utf-8")}
    before = copy.deepcopy(root)
    with patch.object(document.subprocess, "run") as invoked:
        result_tree = document.DocumentTree(document.MemoryStore(files))
        model = result_tree.model()
    assert model == {
        "modelsource": original,
        "resolvedmodelsource": EXPECTED_MODEL,
        "modelbase": "https://example.com/captured/models/",
    }
    assert root == before
    assert result_tree.reads == ["registry.json"]
    invoked.assert_not_called()
    assert result_tree.metadata(V1)["entity"] == {**V1_ENTITY, "self": "#/entity"}
    assert result_tree.reads == V1_READS


@pytest.mark.parametrize(
    "field,value",
    [
        pytest.param("self", "https://example.com/not-an-api", id="self"),
        pytest.param("shortself", "v1", id="shortself"),
        pytest.param("metaurl", "#/absent", id="metaurl"),
        pytest.param("defaultversionurl", "#/absent", id="defaultversionurl"),
        pytest.param("formatvalidated", True, id="formatvalidated"),
        pytest.param("formatvalidatedreason", "unchecked", id="formatvalidatedreason"),
        pytest.param("compatibilityvalidated", True, id="compatibilityvalidated"),
        pytest.param("compatibilityvalidatedreason", "unchecked", id="compatibilityvalidatedreason"),
    ],
)
def test_document_storage_cannot_smuggle_suppressed_navigation_or_validation(field, value):
    records, documents = document.sample_records()
    version = next(record for record in records if record["entity"]["xid"] == V1)
    version["entity"][field] = value
    with patch.object(document.DocumentTree, "validate", return_value=None):
        files = document.encode_tree(records, documents)
    result_tree = document.DocumentTree(document.MemoryStore(files))
    with pytest.raises(FederationError) as caught:
        result_tree.metadata(V1)
    assert_error(caught, "invalid_package", "Schema violation in records/na.json at /entity: None")
    assert result_tree.reads == V1_READS
    assert result_tree.store.files == files


@pytest.mark.parametrize(
    "identity,fragment",
    [
        pytest.param("a~b", "a~0b", id="json-pointer-tilde"),
        pytest.param("a:b", "a%3Ab", id="uri-fragment-colon"),
        pytest.param("a@b", "a%40b", id="uri-fragment-at"),
    ],
)
def test_document_renderer_escapes_included_ids_without_rewriting_xids(identity, fragment):
    records, documents = document.sample_records()
    old = "/documents/main/assets/CON"
    new = "/documents/main/assets/" + identity
    for record in records:
        if record["entity"]["xid"] == old or record["entity"]["xid"].startswith(old + "/"):
            record["entity"]["xid"] = new + record["entity"]["xid"][len(old):]
            record["entity"]["assetid"] = identity
    documents[new + "/versions/a:b@c."] = documents.pop(BINARY)
    result_tree = document.DocumentTree(document.MemoryStore(document.encode_tree(records, documents)))
    view = result_tree.collection("/documents/main/assets")
    entity = view["entities"][identity]
    assert entity["xid"] == new
    assert entity["assetid"] == identity
    assert entity["self"] == "#/entities/" + fragment
    assert follow_pointer(view, entity["self"]) is entity
    assert entity["metaurl"] == "#/entities/" + fragment + "/meta"
    assert entity["meta"]["defaultversionurl"] == (
        "#/entities/" + fragment + "/versions/a%3Ab%40c."
    )
    assert follow_pointer(view, entity["meta"]["defaultversionurl"])["xid"] == (
        new + "/versions/a:b@c."
    )
    assert_metadata_only_reads(result_tree.reads)


def test_document_structurally_equal_resource_types_still_cannot_alias():
    records, documents = document.sample_records()
    model = records[0]["entity"]["modelsource"]
    model["groups"]["independent"]["resources"]["assets"] = copy.deepcopy(
        model["groups"]["documents"]["resources"]["assets"]
    )
    alias = next(record for record in records if record["entity"]["xid"] == COPY + "/meta")
    alias["entity"]["xref"] = "/independent/MAIN/assets/item"
    with patch.object(document.DocumentTree, "validate", return_value=None):
        files = document.encode_tree(records, documents)
    result_tree = document.DocumentTree(document.MemoryStore(files))
    with pytest.raises(FederationError) as caught:
        result_tree.metadata(COPY)
    assert_error(caught, "invalid_package", "xref Resource model type mismatch")
    assert result_tree.reads == COPY_READS
    assert "records/nf.json" not in result_tree.reads
    assert "indexes/na.json" not in result_tree.reads


def test_document_external_descriptor_retains_explicit_base_and_never_fetches():
    records, documents = document.sample_records()
    records[0]["snapshot"]["completeness"] = "linked"
    version = next(record for record in records if record["entity"]["xid"] == V1)
    version["entity"]["asseturl"] = "contents/payload.json"
    version["document"] = {
        "kind": "external", "uri": "contents/payload.json",
        "base": "https://example.com/original/", "size": 17, "sha256": JSON_SHA256,
    }
    del documents[V1]
    files = document.encode_tree(records, documents)
    before_files = dict(files)
    result_tree = document.DocumentTree(document.MemoryStore(files))
    descriptor = result_tree.document_descriptor(ITEM)
    assert descriptor == {
        "kind": "external", "uri": "contents/payload.json",
        "base": "https://example.com/original/", "size": 17, "sha256": JSON_SHA256,
    }
    assert result_tree.reads == V1_READS
    metadata = result_tree.metadata(V1)
    assert metadata == {
        "kind": "version",
        "entity": {
            **V1_ENTITY, "asseturl": "contents/payload.json", "self": "#/entity",
        },
    }
    with patch.object(result_tree.store, "read", wraps=result_tree.store.read) as read:
        with pytest.raises(FederationError) as caught:
            result_tree.document(ITEM)
    assert_error(caught, "unsupported_operation", "External content is not fetched")
    read.assert_not_called()
    descriptor["base"] = "https://example.com/client-change/"
    assert result_tree.document_descriptor(V1)["base"] == "https://example.com/original/"
    assert result_tree.store.files == before_files
    assert_metadata_only_reads(result_tree.reads)


@pytest.mark.parametrize(
    "state,message",
    [
        pytest.param("none-on-document-type", "Document state disagrees with hasdocument", id="none-on-document-type"),
        pytest.param("local-on-metadata-only", "Document state disagrees with hasdocument", id="local-on-metadata-only"),
        pytest.param("external-offline", "External document in offline-complete snapshot", id="external-offline-complete"),
        pytest.param("external-no-base", "Relative external document has no explicit base", id="relative-external-no-base"),
        pytest.param("external-url-mismatch", "External document and metadata URI disagree", id="external-url-mismatch"),
    ],
)
def test_document_renderer_rejects_inconsistent_document_states(state, message):
    records, documents = document.sample_records()
    xid = NOTE + "/versions/v1" if state == "local-on-metadata-only" else V1
    version = next(record for record in records if record["entity"]["xid"] == xid)
    if state == "none-on-document-type":
        version["document"] = {"kind": "none"}
        del documents[V1]
    elif state == "local-on-metadata-only":
        documents[xid] = b"not permitted on metadata-only type"
    else:
        del documents[V1]
        version["entity"]["asseturl"] = "payload.json"
        version["document"] = {
            "kind": "external", "uri": "payload.json", "base": "https://example.com/base/",
        }
        if state != "external-offline":
            records[0]["snapshot"]["completeness"] = "linked"
        if state == "external-no-base":
            del version["document"]["base"]
        if state == "external-url-mismatch":
            version["entity"]["asseturl"] = "different.json"
    with patch.object(document.DocumentTree, "validate", return_value=None):
        files = document.encode_tree(records, documents)
    before = dict(files)
    result_tree = document.DocumentTree(document.MemoryStore(files))
    with pytest.raises(FederationError) as caught:
        result_tree.metadata(xid)
    assert_error(caught, "invalid_package", message)
    assert_metadata_only_reads(result_tree.reads)
    assert result_tree.reads[-1] == ("records/ne.json" if xid != V1 else "records/na.json")
    assert result_tree.store.files == before


@pytest.mark.parametrize(
    "xid,message",
    [
        pytest.param("/", "Document requires Resource or Version", id="registry"),
        pytest.param("/documents/main", "Document requires Resource or Version", id="group"),
        pytest.param(ITEM + "/meta", "Document requires Resource or Version", id="meta"),
        pytest.param(NOTE, "Resource hasdocument is false", id="metadata-only-resource"),
        pytest.param(NOTE + "/versions/v1", "Resource hasdocument is false", id="metadata-only-version"),
    ],
)
def test_document_requests_reject_wrong_kinds_before_reading_descendants(tree, xid, message):
    with pytest.raises(FederationError) as caught:
        tree.document(xid)
    assert_error(caught, "unsupported_operation", message)
    assert tree.reads == ["registry.json"]
    with pytest.raises(FederationError) as descriptor_error:
        tree.document_descriptor(xid)
    assert_error(descriptor_error, "unsupported_operation", message)
    assert tree.reads == ["registry.json"]


@pytest.mark.parametrize(
    "xid,message",
    [
        pytest.param("/unknown/main", "Unknown Group model type", id="unknown-group-type"),
        pytest.param("/documents/main/unknown/item", "Unknown Resource model type", id="unknown-resource-type"),
    ],
)
def test_document_unknown_model_type_is_not_an_absent_instance(tree, xid, message):
    with pytest.raises(FederationError) as caught:
        tree.metadata(xid)
    assert_error(caught, "invalid_package", message)
    assert tree.reads == ["registry.json"]
    assert tree.root["entity"]["modelsource"] == EXPECTED_MODEL


@pytest.mark.parametrize(
    "payload,message",
    [
        pytest.param(b"", "Invalid JSON in registry.json", id="empty-file-not-empty-registry"),
        pytest.param(b"\xff", "Invalid JSON in registry.json", id="invalid-utf8"),
        pytest.param(b"\xef\xbb\xbf{}", "Invalid JSON in registry.json", id="utf8-bom"),
        pytest.param(b"[]", "Expected JSON object in registry.json", id="array"),
        pytest.param(b"null", "Expected JSON object in registry.json", id="null"),
        pytest.param(b'"registry"', "Expected JSON object in registry.json", id="string"),
        pytest.param(b'{"value":1,"value":2}', "Duplicate JSON key in registry.json: value", id="duplicate-key"),
        pytest.param(b'{"value":NaN}', "Non-JSON number in registry.json: NaN", id="nan"),
        pytest.param(b'{"value":Infinity}', "Non-JSON number in registry.json: Infinity", id="infinity"),
        pytest.param(b'{"value":-Infinity}', "Non-JSON number in registry.json: -Infinity", id="negative-infinity"),
    ],
)
def test_document_root_json_parser_rejects_noncanonical_json(payload, message):
    files = {"registry.json": payload, "documents/n0.bin": b"unrelated poison"}
    store = document.MemoryStore(files)
    with pytest.raises(FederationError) as caught:
        document.DocumentTree(store)
    assert_error(caught, "invalid_package", message)
    assert store.reads == ["registry.json"]
    assert store.total_bytes == len(payload)
    assert store.files == files


@pytest.mark.parametrize(
    "field,value,code,message",
    [
        pytest.param("format", "other", "invalid_package", "Unknown document-tree format", id="format"),
        pytest.param("formatversion", "2", "unsupported_version", "Unknown document-tree version", id="format-version"),
        pytest.param("specversion", "2.0", "unsupported_version", "Unsupported Core version", id="core-version"),
        pytest.param("kind", "group", "invalid_package", "Root is not a Registry record", id="root-kind"),
    ],
)
def test_document_root_requires_supported_format_core_and_registry(
    authored_files, field, value, code, message
):
    root = json.loads(authored_files["registry.json"])
    if field == "specversion":
        root["entity"][field] = value
    elif field == "kind":
        root = json.loads(authored_files["records/n4.json"])
    else:
        root[field] = value
    files = {**authored_files, "registry.json": json.dumps(root).encode("utf-8")}
    store = document.MemoryStore(files)
    with pytest.raises(FederationError) as caught:
        document.DocumentTree(store)
    assert_error(caught, code, message)
    assert store.reads == ["registry.json"]
    assert store.files == files


@pytest.mark.parametrize(
    "name,expected_reads",
    [
        pytest.param("indexes/n6.json", ITEM_STATE_READS, id="index"),
        pytest.param("records/na.json", V1_READS, id="record"),
        pytest.param("documents/n1.bin", V1_READS + ["documents/n1.bin"], id="document"),
    ],
)
@pytest.mark.parametrize("mutation", ["same-size", "truncated", "extended"])
def test_document_integrity_is_checked_before_decode_or_return(
    authored_files, name, expected_reads, mutation
):
    original = authored_files[name]
    damaged = {
        "same-size": original[:-1] + b"x",
        "truncated": original[:-1],
        "extended": original + b"x",
    }[mutation]
    files = {**authored_files, name: damaged}
    result_tree = document.DocumentTree(document.MemoryStore(files))
    with patch.object(result_tree, "_decode", wraps=result_tree._decode) as decode:
        with pytest.raises(FederationError) as caught:
            result_tree.document(ITEM)
    assert_error(caught, "integrity_error", "Descriptor mismatch: " + name)
    assert result_tree.reads == expected_reads
    assert name not in [call.args[1] for call in decode.call_args_list]
    assert result_tree.store.files == files
    assert authored_files[name] == original
    assert "documents/n2.bin" not in result_tree.reads


@pytest.mark.parametrize(
    "mutation,message,expected_reads",
    [
        pytest.param("count", "Index count disagrees with entries",
                     ["registry.json", "indexes/n3.json"], id="count-disagrees"),
        pytest.param("duplicate", "References must be unique and sorted by full XID",
                     ["registry.json", "indexes/n3.json"], id="duplicate-xid"),
        pytest.param("wrong-kind", "Index entry is not an immediate typed member",
                     ["registry.json", "indexes/n3.json"], id="wrong-member-kind"),
        pytest.param("wrong-parent", "Index entry is not an immediate typed member",
                     ["registry.json", "indexes/n3.json"], id="wrong-member-parent"),
        pytest.param("reference-identity", "Reference and stored object disagree",
                     ["registry.json", "indexes/n3.json", "records/n4.json"], id="reference-identity"),
    ],
)
def test_document_index_semantics_are_validated_by_real_collection_reads(
    authored_files, mutation, message, expected_reads
):
    index = json.loads(authored_files["indexes/n3.json"])
    if mutation == "count":
        index["count"] = 2
    elif mutation == "duplicate":
        index["entries"].append(copy.deepcopy(index["entries"][0]))
        index["count"] = 2
    elif mutation == "wrong-kind":
        index["entries"][0]["kind"] = "resource"
    elif mutation == "wrong-parent":
        index["entries"][0]["xid"] = "/categories/main"
    else:
        index["entries"][0]["xid"] = "/documents/MAIN"
    data = json.dumps(index).encode("utf-8")
    root = json.loads(authored_files["registry.json"])
    root["collections"][1]["size"] = len(data)
    root["collections"][1]["sha256"] = hashlib.sha256(data).hexdigest()
    files = {
        **authored_files, "registry.json": json.dumps(root).encode("utf-8"),
        "indexes/n3.json": data,
    }
    result_tree = document.DocumentTree(document.MemoryStore(files))
    with pytest.raises(FederationError) as caught:
        result_tree.collection("/documents")
    assert_error(caught, "invalid_package", message)
    assert result_tree.reads == expected_reads
    assert result_tree.store.files == files


@pytest.mark.parametrize(
    "mutation,message,expected_reads",
    [
        pytest.param("absent-default", "Default Version is missing from index",
                     ITEM_STATE_READS, id="missing-default"),
        pytest.param("wrong-default-flag", "Version default flag disagrees with Meta",
                     V1_READS, id="default-flag"),
        pytest.param("absent-ancestor", "Missing Version ancestor",
                     V1_READS, id="missing-ancestor"),
    ],
)
def test_document_renderer_rejects_invalid_default_and_ancestor_state(
    mutation, message, expected_reads
):
    records, documents = document.sample_records()
    meta = next(record for record in records if record["entity"]["xid"] == ITEM + "/meta")
    version = next(record for record in records if record["entity"]["xid"] == V1)
    if mutation == "absent-default":
        meta["entity"]["defaultversionid"] = "absent"
    elif mutation == "wrong-default-flag":
        version["entity"]["isdefault"] = False
    else:
        version["entity"]["ancestorid"] = "missing"
    with patch.object(document.DocumentTree, "validate", return_value=None):
        files = document.encode_tree(records, documents)
    result_tree = document.DocumentTree(document.MemoryStore(files))
    with pytest.raises(FederationError) as caught:
        result_tree.metadata(ITEM + "/meta" if mutation == "absent-default" else V1)
    assert_error(caught, "invalid_package", message)
    assert result_tree.reads == expected_reads
    assert result_tree.store.files == files


def test_document_full_validation_rejects_nonroot_ancestor_cycle():
    records, documents = document.sample_records()
    version = next(record for record in records if record["entity"]["xid"] == V1)
    version["entity"]["ancestorid"] = "v2"
    with patch.object(document.DocumentTree, "validate", return_value=None):
        files = document.encode_tree(records, documents)
    result_tree = document.DocumentTree(document.MemoryStore(files))
    with pytest.raises(FederationError) as caught:
        result_tree.validate()
    assert_error(caught, "invalid_package", "Version ancestor cycle")
    assert [name for name in result_tree.reads if name.startswith("documents/")] == ["documents/n0.bin"]
    assert "records/na.json" in result_tree.reads
    assert "records/nb.json" in result_tree.reads
    assert "documents/n1.bin" not in result_tree.reads


@pytest.mark.parametrize(
    "limit",
    ["max_file_bytes", "max_total_bytes", "max_files"],
)
@pytest.mark.parametrize("value", [0, -1, True, 1.5], ids=["zero", "negative", "boolean", "float"])
def test_document_store_limits_require_positive_integers(limit, value):
    files = {"documents/n0.bin": b"untouched"}
    with pytest.raises(FederationError) as caught:
        document.MemoryStore(files, **{limit: value})
    assert_error(caught, "invalid_package", "Limits must be positive integers")
    assert files == {"documents/n0.bin": b"untouched"}


@pytest.mark.parametrize(
    "limits,contents,accepted,message",
    [
        pytest.param(
            {"max_file_bytes": 18}, [AUTHORED_JSON, AUTHORED_JSON + b"!"],
            1, "File byte limit", id="per-file-exact-limit-then-over",
        ),
        pytest.param(
            {"max_total_bytes": 17}, [b"12345678", b"123456789", b"x"],
            2, "Aggregate byte limit", id="aggregate-exact-limit-then-over",
        ),
        pytest.param(
            {"max_files": 2}, [b"abcdefgh", b"ijklmnop", b"qrstuvwx"],
            2, "File count limit", id="count-exact-limit-then-over",
        ),
    ],
)
def test_document_store_limits_fail_without_successful_accounting(
    limits, contents, accepted, message
):
    names = ["documents/n0.bin", "documents/n1.bin", "documents/n2.bin"]
    files = dict(zip(names, contents))
    store = document.MemoryStore(files, **limits)
    for index in range(accepted):
        assert store.read(names[index]) == contents[index]
    before_bytes = sum(len(content) for content in contents[:accepted])
    with pytest.raises(FederationError) as caught:
        store.read(names[accepted])
    assert_error(caught, "limit_exceeded", message)
    assert store.reads == names[:accepted]
    assert store.total_bytes == before_bytes
    assert store.files == files


def test_file_document_tree_size_limit_precedes_open(copied_tree):
    store = document.FileStore(copied_tree, max_file_bytes=17)
    with patch.object(document.os, "open", wraps=document.os.open) as opened:
        with pytest.raises(FederationError) as caught:
            store.read("documents/n1.bin")
    assert_error(caught, "limit_exceeded", "File byte limit")
    opened.assert_not_called()
    assert store.reads == []
    assert store.total_bytes == 0
    assert document.FileStore(copied_tree, max_file_bytes=18).read("documents/n1.bin") == AUTHORED_JSON


def test_document_encoder_is_deterministic_and_does_not_mutate_authored_input(authored_files):
    records, documents = document.sample_records()
    before = copy.deepcopy((records, documents))
    files = document.encode_tree(list(reversed(records)), dict(reversed(list(documents.items()))))
    assert files == authored_files
    assert files["registry.json"] == authored_files["registry.json"]
    assert files[".gitattributes"] == b"*.json text eol=lf\ndocuments/** -text\n"
    assert files["documents/n1.bin"] == b'{"hello":"world"}\n'
    assert hashlib.sha256(files["registry.json"]).hexdigest() == ROOT_SHA256
    assert (records, documents) == before


@pytest.mark.parametrize(
    "mutation,message",
    [
        pytest.param("duplicate", "Duplicate fixture record", id="duplicate-record"),
        pytest.param("registry", "Fixture needs a Registry record", id="missing-registry"),
        pytest.param("document-type", "Fixture documents must be bytes", id="document-not-bytes"),
        pytest.param("unreachable-document", "Unreachable fixture document", id="unreachable-document"),
    ],
)
def test_document_encoder_rejects_invalid_inputs_without_mutating_them(mutation, message):
    records, documents = document.sample_records()
    if mutation == "duplicate":
        records.append(copy.deepcopy(records[0]))
    elif mutation == "registry":
        records.pop(0)
    elif mutation == "document-type":
        documents[V1] = bytearray(AUTHORED_JSON)
    else:
        documents[ITEM + "/versions/absent"] = b"unreachable"
    before = copy.deepcopy((records, documents))
    with pytest.raises(FederationError) as caught:
        document.encode_tree(records, documents)
    assert_error(caught, "invalid_package", message)
    assert (records, documents) == before


def test_document_sample_writer_refuses_overwrite_before_any_creation(tmp_path):
    root = tmp_path / "sample"
    root.mkdir()
    existing = root / "registry.json"
    existing.write_bytes(b"owner content")
    original_open = Path.open
    created = []

    def traced_open(path, mode="r", *args, **kwargs):
        if mode == "xb":
            created.append(path)
        return original_open(path, mode, *args, **kwargs)

    with patch.object(Path, "open", autospec=True, side_effect=traced_open):
        with pytest.raises(FederationError) as caught:
            document.write_sample(root)
    assert_error(caught, "invalid_package", "Existing fixture differs; use an empty root")
    assert created == []
    assert existing.read_bytes() == b"owner content"
    assert list(root.iterdir()) == [existing]


def test_document_cli_entity_keeps_origin_outside_core_navigation(capsys, mapping_sample_root):
    status = document.main(["entity", str(mapping_sample_root), V1])
    output = capsys.readouterr()
    assert status == 0
    assert output.err == ""
    result = json.loads(output.out)
    assert result == {
        "kind": "version",
        "entity": {**V1_ENTITY, "self": "#/entity"},
        "reads": V1_READS,
        "origin": {
            "pin": None, "rootsha256": ROOT_SHA256, "immutable": False,
            "target": V1, "endpoint": mapping_sample_root.as_uri(), "layout": "document-tree",
        },
    }
    assert follow_pointer(result, result["entity"]["self"]) is result["entity"]


@pytest.mark.parametrize(
    "arguments,message",
    [
        pytest.param(["entity", V1, "--target", V2], "Specify the target only once", id="duplicate-target"),
        pytest.param(["collection", "/documents/main/assets", "--label", "stage"],
                     "Both --label and --value are needed", id="incomplete-selector"),
        pytest.param(["entity", V1, "--label", "stage", "--value", "production"],
                     "Label selector only applies to collections", id="selector-wrong-operation"),
        pytest.param(["model", V1], "Model/capabilities target must be /", id="model-nonroot"),
        pytest.param(["capabilities", V1], "Model/capabilities target must be /", id="capabilities-nonroot"),
        pytest.param(["entity", V1, "--revision", "refs/heads/main"],
                     "File reads do not accept --revision", id="file-git-revision"),
    ],
)
def test_document_cli_argument_errors_are_explicit_not_success_shaped(capsys, arguments, message, mapping_sample_root):
    operation, *rest = arguments
    with patch.object(document.subprocess, "run") as invoked:
        status = document.main([operation, str(mapping_sample_root), *rest])
    output = capsys.readouterr()
    assert status == 1
    assert output.out == ""
    assert json.loads(output.err) == {"error": "invalid_package", "message": message}
    invoked.assert_not_called()


@pytest.mark.parametrize(
    "xid,identity,target,record,meta",
    [
        pytest.param(COPY, "copy", ITEM, "records/n13.json", "records/n14.json", id="one-hop"),
        pytest.param(DANGLING, "dangling", "/documents/main/assets/missing",
                     "records/n15.json", "records/n16.json", id="dangling"),
        pytest.param(CHAIN, "chain", COPY, "records/n11.json", "records/n12.json", id="alias-target"),
    ],
)
def test_document_alias_meta_view_is_minimal_and_source_relative(
    tree, xid, identity, target, record, meta
):
    result = tree.metadata(xid + "/meta")
    assert result == {
        "kind": "meta",
        "entity": {
            "xid": xid + "/meta", "assetid": identity, "xref": target,
            "self": "#/entity",
        },
    }
    assert tree.reads == [
        "registry.json", "indexes/nb.json", "records/n10.json",
        "indexes/nc.json", record, meta,
    ]
    assert follow_pointer(result, result["entity"]["self"]) is result["entity"]
    assert "related" not in result
    assert "defaultversionurl" not in result["entity"]


@pytest.mark.parametrize(
    "xid,expected,reads",
    [
        pytest.param(COPY, AUTHORED_JSON,
                     COPY_READS + V1_READS[1:] + ["documents/n1.bin"], id="default-v1"),
        pytest.param(COPY + "/versions/v2", b"",
                     COPY_READS + V2_READS[1:] + ["documents/n2.bin"], id="explicit-v2"),
    ],
)
def test_document_logical_alias_document_is_separate_from_alias_version_view(
    tree, xid, expected, reads
):
    data = tree.document(xid)
    assert data == expected
    assert len(data) == (18 if xid == COPY else 0)
    assert tree.reads == reads
    assert tree.metadata(COPY)["entity"]["xid"] == COPY
    assert tree.metadata(COPY)["entity"]["meta"]["xref"] == ITEM
    before = list(tree.reads)
    with pytest.raises(FederationError) as caught:
        tree.metadata(COPY + "/versions/v2")
    assert_error(caught, "unsupported_operation", "cannot_doc_xref")
    assert tree.reads == before


def test_document_resource_view_keeps_meta_extensions_on_the_meta():
    records, documents = document.sample_records()
    meta = next(record for record in records if record["entity"]["xid"] == ITEM + "/meta")
    meta["entity"]["xfixture"] = {"classification": "internal", "retention": [7, 30]}
    before = copy.deepcopy((records, documents))
    result_tree = document.DocumentTree(document.MemoryStore(document.encode_tree(records, documents)))
    result = result_tree.metadata(ITEM)["entity"]
    assert result["xid"] == ITEM
    assert result["meta"]["xfixture"] == {"classification": "internal", "retention": [7, 30]}
    assert "xfixture" not in result
    assert "xfixture" not in result["versions"]["v1"]
    assert result["versions"]["v1"]["purpose"] == "primary"
    assert result["metaurl"] == "#/entity/meta"
    assert result_tree.reads == ITEM_STATE_READS + ["records/na.json", "records/nb.json"]
    assert (records, documents) == before


def test_document_empty_collection_is_complete_without_invented_members(tree):
    assert tree.collection("/independent/MAIN/assets") == {
        "kind": "collection", "xid": "/independent/MAIN/assets",
        "complete": True, "entities": {},
    }
    assert tree.reads == [
        "registry.json", "indexes/n9.json", "records/nf.json", "indexes/na.json",
    ]
    group = tree.metadata("/independent/MAIN")["entity"]
    assert group["assetscount"] == 0
    assert group["assetsurl"] == "#/entity/assets"
    assert group["independentid"] == "MAIN"
    assert_metadata_only_reads(tree.reads)


WIDGET = "/documents/main/assets/widget"
WIDGET_V1 = WIDGET + "/versions/v1"
FORMS = ("split", "inline", "mixed")
MIXED_V1_READS = [
    "registry.json", "indexes/n3.json", "indexes/n4.json", "records/n8.json", "indexes/n6.json",
]
SELECTIONS = (
    ("/mirrors/local/assets", {"label": "stage", "value": "PRODUCTION"}),
    (ITEM + "/versions", {"label": "stage", "value": "development"}),
    (WIDGET + "/versions", {"label": "stage", "value": "production"}),
)


def mixed_sample(kind, xid):
    """Inline Groups, Metas, Versions and the mirrors subtree; keep the rest external."""
    return kind in ("group", "meta", "version") or xid.startswith("/mirrors")


def mapping_source(dataset):
    """Return records, documents, encoder options and the mixed selection of a dataset."""
    if dataset == "walkthrough":
        records, documents = walkthrough_source()
        options = {"document_paths": {WIDGET_V1: WALKTHROUGH_DOCUMENT}, "gitattributes": None}
        mixed = {"/documents", "/documents/main", "/documents/main/assets", WIDGET + "/meta", WIDGET_V1}
        return records, documents, options, mixed
    records, documents = document.sample_records()
    return records, documents, {}, mixed_sample


def encode_form(dataset, form):
    records, documents, options, mixed = mapping_source(dataset)
    inline = {"split": False, "inline": True, "mixed": mixed}[form]
    return document.encode_tree(records, documents, inline=inline, **options)


def nested_dicts(value):
    pending = [value]
    while pending:
        current = pending.pop()
        if isinstance(current, dict):
            yield current
            pending.extend(current.values())
        elif isinstance(current, list):
            pending.extend(current)


def collection_xids(inline_files):
    root = json.loads(inline_files["registry.json"])
    return sorted(
        value["xid"] for value in nested_dicts(root)
        if value.get("kind") == "collection" and "entries" in value
    )


def inline_reference(root, xid):
    return next(
        value for value in nested_dicts(root) if value.get("xid") == xid and "inline" in value
    )


def serialized(value):
    return (json.dumps(value, indent=2) + "\n").encode("utf-8")


def repin(files, name, data):
    """Replace one metadata file and recompute every ancestor descriptor up to the root."""
    original, files = files, {**files, name: data}
    while name != "registry.json":
        for parent, content in original.items():
            if parent == name or not parent.endswith(".json"):
                continue
            if any(item.get("href") == name for item in nested_dicts(json.loads(content))):
                break
        else:
            raise AssertionError("No parent descriptor for " + name)
        value = json.loads(files[parent])
        references = [item for item in nested_dicts(value) if item.get("href") == name]
        for reference in references:
            reference.update(size=len(data), sha256=hashlib.sha256(data).hexdigest())
        name, data = parent, serialized(value)
        files[name] = data
    return files


def observe(operation, *args):
    try:
        return "ok", operation(*args)
    except FederationError as error:
        return "error", error.code, str(error)


def metadata_observations(reader, records, collections):
    """Every read that must not touch domain payloads."""
    results = {"model": observe(reader.model), "capabilities": observe(reader.capabilities)}
    for record in records:
        xid = record["entity"]["xid"]
        results["metadata " + xid] = observe(reader.metadata, xid)
        if record["kind"] in ("resource", "version"):
            results["descriptor " + xid] = observe(reader.document_descriptor, xid)
    for xid in collections:
        results["collection " + xid] = observe(reader.collection, xid)
    for xid, selector in SELECTIONS:
        if xid in collections:
            results["selection " + xid] = observe(reader.collection, xid, selector)
    return results


def observations(reader, records, collections):
    results = metadata_observations(reader, records, collections)
    for record in records:
        if record["kind"] in ("resource", "version"):
            xid = record["entity"]["xid"]
            results["document " + xid] = observe(reader.document, xid)
    validation = observe(reader.validate)
    if validation[0] == "ok":
        validation = "ok", {
            key: value for key, value in validation[1].items() if key not in ("rootsha256", "pin")
        }
    results["validate"] = validation
    return results


def open_store(kind, files, location):
    if kind == "memory":
        return document.MemoryStore(files)
    if kind == "file":
        for name, data in files.items():
            path = location.joinpath(*name.split("/"))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return document.FileStore(location)
    git = GitFixture(location.with_suffix(".git"))
    commit = git.commit(files)
    store = document.GitStore(git.path, "refs/heads/main")
    assert store.pin == commit
    return store


@pytest.mark.parametrize("store", ["memory", "file", "git"])
@pytest.mark.parametrize("dataset", ["walkthrough", "sample"])
def test_split_inline_and_mixed_mappings_return_identical_reads(tmp_path, dataset, store):
    records = mapping_source(dataset)[0]
    encoded = {form: encode_form(dataset, form) for form in FORMS}
    collections = collection_xids(encoded["inline"])
    if dataset == "sample":
        collections.append(COPY + "/versions")
    expected = observations(
        document.DocumentTree(document.MemoryStore(encoded["split"])), records, collections
    )
    for form, files in encoded.items():
        reader = document.DocumentTree(open_store(store, files, tmp_path / form))
        assert observations(reader, records, collections) == expected, form
    assert set(encoded["mixed"]) < set(encoded["split"])
    assert len(encoded["inline"]) < len(encoded["mixed"])
    if dataset == "walkthrough":
        assert sorted(encoded["inline"]) == ["registry.json", WALKTHROUGH_DOCUMENT]
        assert expected["validate"] == ("ok", {
            "records": 5, "indexes": 3, "documents": 1, "completeness": "offline-complete",
        })
        assert expected["document " + WIDGET] == ("ok", b'{"type":"string"}\n')
        assert expected["selection " + WIDGET + "/versions"] == (
            "error", "not_found", "No label match",
        )
        return
    assert sorted(encoded["inline"]) == [
        ".gitattributes", "documents/n0.bin", "documents/n1.bin", "documents/n2.bin",
        "registry.json",
    ]
    assert expected["validate"] == ("ok", {
        "records": 24, "indexes": 13, "documents": 3, "completeness": "offline-complete",
    })
    assert expected["document " + V1] == expected["document " + COPY] == ("ok", AUTHORED_JSON)
    assert expected["document " + V2] == ("ok", b"")
    assert expected["document " + BINARY] == ("ok", b"\x00\x01\xff\x7f\n")
    assert expected["document " + NOTE][:2] == ("error", "unsupported_operation")
    assert expected["document " + DANGLING] == ("error", "not_found", "No one-hop alias document")
    assert expected["collection " + COPY + "/versions"] == (
        "error", "unsupported_operation", "cannot_doc_xref",
    )
    assert list(expected["selection " + ITEM + "/versions"][1]["entities"]) == ["v2"]
    assert list(expected["selection /mirrors/local/assets"][1]["entities"]) == ["copy"]
    assert expected["metadata " + V1][1]["entity"] == {**V1_ENTITY, "self": "#/entity"}
    assert expected["model"] == ("ok", {"modelsource": EXPECTED_MODEL})
    assert expected["capabilities"] == ("ok", EXPECTED_CAPABILITIES)


def test_fully_inline_root_is_read_once_and_metadata_never_reads_documents():
    files = encode_form("sample", "inline")
    poisoned = {
        name: b"unrelated poison" if name.startswith("documents/") else data
        for name, data in files.items()
    }
    records = document.sample_records()[0]
    collections = collection_xids(files)
    split = document.DocumentTree(document.MemoryStore(encode_form("sample", "split")))
    reader = document.DocumentTree(document.MemoryStore(poisoned))
    assert reader.reads == ["registry.json"]
    assert reader.objects == 37
    assert metadata_observations(reader, records, collections) == metadata_observations(
        split, records, collections
    )
    assert reader.reads == ["registry.json"]
    assert reader.store.total_bytes == len(files["registry.json"])
    with pytest.raises(FederationError) as caught:
        reader.document(V1)
    assert_error(caught, "integrity_error", "Descriptor mismatch: documents/n1.bin")
    assert reader.reads == ["registry.json", "documents/n1.bin"]


def test_mixed_mapping_reads_only_its_external_files_along_the_split_path():
    split, mixed = encode_form("sample", "split"), encode_form("sample", "mixed")
    operations = [("metadata", record["entity"]["xid"]) for record in document.sample_records()[0]]
    operations += [("collection", xid) for xid in collection_xids(encode_form("sample", "inline"))]
    operations += [("document", xid) for xid in (ITEM, V2, BINARY, COPY, DANGLING)]
    for operation, xid in operations:
        traces = []
        for files in (split, mixed):
            reader = document.DocumentTree(document.MemoryStore(files))
            observe(getattr(reader, operation), xid)
            traces.append(reader.reads)
        assert traces[1] == [name for name in traces[0] if name in mixed], (operation, xid)
        if operation != "document":
            assert_metadata_only_reads(traces[1])
    reader = document.DocumentTree(document.MemoryStore(mixed))
    assert reader.metadata(V1)["entity"] == {**V1_ENTITY, "self": "#/entity"}
    assert reader.reads == MIXED_V1_READS


def test_file_store_detects_a_replaced_inline_root_without_rereading_it(tmp_path):
    files = encode_form("sample", "inline")
    reader = document.DocumentTree(open_store("file", files, tmp_path / "inline"))
    (tmp_path / "inline" / "registry.json").write_bytes(files["registry.json"] + b"\n")
    with pytest.raises(FederationError) as caught:
        reader.metadata(V1)
    assert_error(caught, "inconsistent_snapshot", "Snapshot changed during operation")
    assert reader.reads == ["registry.json"]


def mutate_inline(root, mutation):
    """Damage one object of the fully inline sample while keeping the root parseable."""
    meta = inline_reference(root, ITEM + "/meta")
    version = inline_reference(root, V1)
    model = root["entity"]["modelsource"]["groups"]["documents"]["resources"]
    if mutation == "inline-kind":
        meta["inline"] = copy.deepcopy(version["inline"])
    elif mutation == "inline-xid":
        version["inline"] = copy.deepcopy(inline_reference(root, V2)["inline"])
    elif mutation == "member-kind":
        inline_reference(root, "/documents/main")["kind"] = "resource"
    elif mutation == "duplicate-member":
        index = inline_reference(root, ITEM + "/versions")["inline"]
        index["entries"].append(copy.deepcopy(index["entries"][0]))
        index["count"] += 1
    elif mutation == "unordered-members":
        inline_reference(root, "/documents/main/assets")["inline"]["entries"].reverse()
    elif mutation == "case-collision":
        index = inline_reference(root, "/documents")["inline"]
        twin = copy.deepcopy(inline_reference(root, "/documents/main"))
        twin["xid"] = twin["inline"]["entity"]["xid"] = "/documents/MAIN"
        twin["inline"]["entity"]["documentid"] = "MAIN"
        index["entries"].insert(0, twin)
        index["count"] += 1
    elif mutation == "missing-member":
        index = inline_reference(root, ITEM + "/versions")["inline"]
        index["entries"].pop(0)
        index["count"] -= 1
    elif mutation == "group-id":
        inline_reference(root, "/documents/main")["inline"]["entity"]["documentid"] = "other"
    elif mutation == "version-id":
        version["inline"]["entity"]["versionid"] = "v3"
    elif mutation == "mixed-form":
        meta.update(href="records/n9.json", size=1, sha256=EMPTY_SHA256)
    elif mutation == "incomplete-external":
        del meta["inline"]
        meta["href"] = "records/n9.json"
    elif mutation == "no-form":
        del meta["inline"]
    elif mutation == "inline-format":
        meta["inline"]["format"] = "other"
    elif mutation == "inline-version":
        meta["inline"]["formatversion"] = "2"
    elif mutation == "inline-not-object":
        meta["inline"] = []
    elif mutation == "extra-field":
        meta["note"] = "unexpected"
    elif mutation == "missing-document":
        del version["inline"]["document"]
    elif mutation == "invalid-default":
        meta["inline"]["entity"]["defaultversionid"] = "absent"
    elif mutation == "default-flag":
        version["inline"]["entity"]["isdefault"] = False
    elif mutation == "missing-ancestor":
        version["inline"]["entity"]["ancestorid"] = "missing"
    elif mutation == "ancestor-cycle":
        version["inline"]["entity"]["ancestorid"] = "v2"
    elif mutation == "unmodeled-collection":
        del model["notes"]
    elif mutation == "model-hasdocument":
        model["assets"]["hasdocument"] = False
    elif mutation == "alias-type":
        inline_reference(root, COPY + "/meta")["inline"]["entity"]["xref"] = NOTE
    elif mutation == "unsafe-document":
        version["inline"]["document"]["href"] = "../outside.bin"
    elif mutation == "encoded-parent":
        version["inline"]["document"]["href"] = "documents/%2e%2e/n1.bin"
    elif mutation == "document-root-collision":
        version["inline"]["document"]["href"] = "registry.json"
    else:
        descriptor = version["inline"]["document"]
        del meta["inline"]
        meta.update(href=descriptor["href"], size=descriptor["size"], sha256=descriptor["sha256"])


ITEM_LOCATION = "/collections/1/inline/entries/0/inline/collections/0/inline/entries/1/inline"


@pytest.mark.parametrize(
    "mutation,operation,code,message",
    [
        pytest.param("inline-kind", None, "invalid_package",
                     "Reference and stored object disagree", id="inline-kind"),
        pytest.param("inline-xid", None, "invalid_package",
                     "Reference and stored object disagree", id="inline-xid"),
        pytest.param("member-kind", None, "invalid_package",
                     "Index entry is not an immediate typed member", id="member-kind"),
        pytest.param("duplicate-member", None, "invalid_package",
                     "References must be unique and sorted by full XID", id="duplicate-member"),
        pytest.param("unordered-members", None, "invalid_package",
                     "References must be unique and sorted by full XID", id="unordered-members"),
        pytest.param("case-collision", None, "invalid_package",
                     "Case-insensitive sibling collision", id="case-collision"),
        pytest.param("missing-member", ("metadata", ITEM), "invalid_package",
                     "Default Version is missing from index", id="missing-member"),
        pytest.param("group-id", None, "invalid_package",
                     "Group ID disagrees with XID", id="conflicting-group-id"),
        pytest.param("version-id", None, "invalid_package",
                     "Version ID disagrees with XID", id="conflicting-version-id"),
        pytest.param("mixed-form", None, "invalid_package",
                     "Reference mixes inline and external forms", id="mixed-form"),
        pytest.param("incomplete-external", None, "invalid_package",
                     "Incomplete external reference", id="incomplete-external"),
        pytest.param("no-form", None, "invalid_package",
                     "Reference has no inline or external form", id="no-form"),
        pytest.param("inline-format", None, "invalid_package",
                     "Inline format or version differs from container", id="inline-format"),
        pytest.param("inline-version", None, "invalid_package",
                     "Inline format or version differs from container", id="inline-formatversion"),
        pytest.param("inline-not-object", None, "invalid_package",
                     "Inline reference target must be an object", id="inline-not-object"),
        pytest.param("extra-field", None, "invalid_package",
                     f"Schema violation in registry.json at {ITEM_LOCATION}/meta: "
                     "additionalProperties", id="extra-reference-field"),
        pytest.param("missing-document", None, "invalid_package",
                     f"Schema violation in registry.json at {ITEM_LOCATION}/collections/0"
                     "/inline/entries/0/inline: required", id="inline-schema"),
        pytest.param("invalid-default", ("metadata", ITEM + "/meta"), "invalid_package",
                     "Default Version is missing from index", id="invalid-default"),
        pytest.param("default-flag", ("metadata", V1), "invalid_package",
                     "Version default flag disagrees with Meta", id="default-flag"),
        pytest.param("missing-ancestor", ("metadata", V1), "invalid_package",
                     "Missing Version ancestor", id="missing-ancestor"),
        pytest.param("ancestor-cycle", ("validate",), "invalid_package",
                     "Version ancestor cycle", id="ancestor-cycle"),
        pytest.param("unmodeled-collection", None, "invalid_package",
                     "Missing or unexpected modeled collection", id="unmodeled-collection"),
        pytest.param("model-hasdocument", None, "invalid_package",
                     "Document state disagrees with hasdocument", id="model-hasdocument"),
        pytest.param("alias-type", None, "invalid_package",
                     "xref Resource model type mismatch", id="alias-model-type"),
        pytest.param("unsafe-document", None, "policy_denied",
                     "Unsafe storage name", id="unsafe-document-path"),
        pytest.param("encoded-parent", None, "policy_denied",
                     "Unsafe storage name", id="encoded-parent-path"),
        pytest.param("document-root-collision", None, "invalid_package",
                     "Conflicting storage allocation", id="document-is-root"),
        pytest.param("metadata-document-collision", None, "invalid_package",
                     "Conflicting storage allocation", id="metadata-is-document"),
    ],
)
def test_inline_graph_is_rejected_by_the_same_semantic_checks(mutation, operation, code, message):
    files = encode_form("sample", "inline")
    root = json.loads(files["registry.json"])
    mutate_inline(root, mutation)
    store = document.MemoryStore({**files, "registry.json": serialized(root)})
    if operation is None:
        with pytest.raises(FederationError) as caught:
            document.DocumentTree(store)
    else:
        reader = document.DocumentTree(store)
        with pytest.raises(FederationError) as caught:
            getattr(reader, operation[0])(*operation[1:])
    assert_error(caught, code, message)
    assert store.reads.count("registry.json") == 1
    if operation != ("validate",):
        assert store.reads == ["registry.json"]


@pytest.mark.parametrize(
    "original,replacement,message",
    [
        pytest.param(b'"versionid": "v1",', b'"versionid": "v1", "versionid": "v1",',
                     "Duplicate JSON key in registry.json: versionid", id="duplicate-key"),
        pytest.param(b'"readonly": true,', b'"readonly": NaN,',
                     "Non-JSON number in registry.json: NaN", id="nan"),
        pytest.param(b'"inline": {', b'"inline": {,', "Invalid JSON in registry.json", id="syntax"),
    ],
)
def test_inline_objects_use_the_containing_file_json_rules(original, replacement, message):
    files = encode_form("walkthrough", "inline")
    data = files["registry.json"].replace(original, replacement, 1)
    assert data != files["registry.json"]
    store = document.MemoryStore({**files, "registry.json": data})
    with pytest.raises(FederationError) as caught:
        document.DocumentTree(store)
    assert_error(caught, "invalid_package", message)
    assert store.reads == ["registry.json"]


@pytest.mark.parametrize(
    "mutation,message",
    [
        pytest.param("kind", "Reference and stored object disagree", id="inline-kind"),
        pytest.param("xid", "Reference and stored object disagree", id="inline-xid"),
        pytest.param("id", "Version ID disagrees with XID", id="conflicting-id"),
        pytest.param("format", "Inline format or version differs from container", id="inline-format"),
        pytest.param("mixed", "Reference mixes inline and external forms", id="mixed-form"),
        pytest.param("count", "Index count disagrees with entries", id="incomplete-index"),
        pytest.param("default", "Version default flag disagrees with Meta", id="default-flag"),
        pytest.param("json", "Invalid JSON in indexes/n6.json", id="malformed-json"),
        pytest.param("duplicate-key", "Duplicate JSON key in indexes/n6.json: count",
                     id="duplicate-key"),
    ],
)
def test_repinned_external_file_with_invalid_inline_graph_is_still_rejected(mutation, message):
    files = encode_form("sample", "mixed")
    name = "indexes/n6.json"
    control = document.DocumentTree(document.MemoryStore(repin(files, name, files[name])))
    assert control.metadata(V1)["entity"] == {**V1_ENTITY, "self": "#/entity"}
    value = json.loads(files[name])
    entries = value["entries"]
    if mutation == "kind":
        entries[0]["inline"] = json.loads(files["records/n8.json"])["meta"]["inline"]
    elif mutation == "xid":
        entries[0]["inline"] = copy.deepcopy(entries[1]["inline"])
    elif mutation == "id":
        entries[0]["inline"]["entity"]["versionid"] = "v3"
    elif mutation == "format":
        entries[0]["inline"]["formatversion"] = "2"
    elif mutation == "mixed":
        entries[0]["href"] = "records/na.json"
    elif mutation == "count":
        value["count"] = 3
    elif mutation == "default":
        entries[0]["inline"]["entity"]["isdefault"] = False
    data = serialized(value)
    if mutation == "json":
        data = data[:-2]
    elif mutation == "duplicate-key":
        data = data.replace(b'"count": 2,', b'"count": 2, "count": 2,')
    assert data != files[name]
    changed = repin(files, name, data)
    assert changed[name] == data
    reader = document.DocumentTree(document.MemoryStore(changed))
    with pytest.raises(FederationError) as caught:
        reader.metadata(V1)
    assert_error(caught, "invalid_package", message)
    assert reader.reads == MIXED_V1_READS


def test_mixed_mapping_verifies_external_bytes_before_decoding_inline_targets():
    files = encode_form("sample", "mixed")
    name = "indexes/n6.json"
    damaged = {**files, name: files[name][:-1] + b"x"}
    reader = document.DocumentTree(document.MemoryStore(damaged))
    assert reader.metadata(CATALOG)["entity"]["xid"] == CATALOG
    with patch.object(reader, "_decode", wraps=reader._decode) as decode:
        with pytest.raises(FederationError) as caught:
            reader.metadata(V1)
    assert_error(caught, "integrity_error", "Descriptor mismatch: " + name)
    assert [call.args[1] for call in decode.call_args_list] == MIXED_V1_READS[1:-1]
    assert reader.reads[-1] == name
    assert_metadata_only_reads(reader.reads)


@pytest.mark.parametrize(
    "href,code,message",
    [
        pytest.param("../indexes/n6.json", "policy_denied", "Unsafe storage name", id="parent"),
        pytest.param("indexes/%2E%2E/n6.json", "policy_denied", "Unsafe storage name",
                     id="encoded-parent"),
        pytest.param("indexes\\n6.json", "policy_denied", "Unsafe storage name", id="backslash"),
        pytest.param("indexes/n3.json", "invalid_package", "Conflicting storage allocation",
                     id="reused-metadata-path"),
        pytest.param("registry.json", "invalid_package", "Conflicting storage allocation",
                     id="root-path"),
    ],
)
def test_external_reference_nested_in_an_external_file_keeps_path_policy(href, code, message):
    files = encode_form("sample", "mixed")
    resource = json.loads(files["records/n8.json"])
    resource["collections"][0]["href"] = href
    store = document.MemoryStore(repin(files, "records/n8.json", serialized(resource)))
    reader = document.DocumentTree(store)
    with pytest.raises(FederationError) as caught:
        reader.metadata(ITEM)
    assert_error(caught, code, message)
    assert store.reads == MIXED_V1_READS[:-1]


def test_inline_depth_and_object_bounds_are_limit_errors():
    files = encode_form("walkthrough", "inline")
    for options, message in (
        ({"max_inline_depth": 5}, "Inline nesting depth limit"),
        ({"max_objects": 7}, "Metadata object limit"),
    ):
        store = document.MemoryStore(files)
        with pytest.raises(FederationError) as caught:
            document.DocumentTree(store, **options)
        assert_error(caught, "limit_exceeded", message)
        assert store.reads == ["registry.json"]
    reader = document.DocumentTree(document.MemoryStore(files), max_inline_depth=6, max_objects=8)
    assert reader.validate()["records"] == 5
    assert reader.objects == 8


def test_object_bound_is_cumulative_across_files_and_never_partial():
    files = encode_form("walkthrough", "mixed")
    assert sorted(files) == [
        "indexes/n2.json", "records/n1.json", "registry.json", WALKTHROUGH_DOCUMENT,
    ]
    with pytest.raises(FederationError) as caught:
        document.DocumentTree(document.MemoryStore(files), max_inline_depth=2)
    assert_error(caught, "limit_exceeded", "Inline nesting depth limit")
    reader = document.DocumentTree(
        document.MemoryStore(files), max_inline_depth=3, max_objects=7
    )
    assert reader.objects == 4
    assert reader.read_record(WIDGET)["entity"] == {"xid": WIDGET, "assetid": "widget"}
    assert reader.objects == 6
    with pytest.raises(FederationError) as caught:
        reader.metadata(WIDGET)
    assert_error(caught, "limit_exceeded", "Metadata object limit")
    assert reader.reads == ["registry.json", "records/n1.json", "indexes/n2.json"]
    complete = document.DocumentTree(document.MemoryStore(files), max_inline_depth=3, max_objects=8)
    assert complete.validate()["records"] == 5


@pytest.mark.parametrize(
    "limit,message",
    [
        pytest.param("max_files", "File count limit", id="files"),
        pytest.param("max_total_bytes", "Aggregate byte limit", id="bytes"),
    ],
)
def test_inline_root_counts_once_against_store_limits(limit, message):
    files = encode_form("sample", "inline")
    size = len(files["registry.json"])
    store = document.MemoryStore(files, max_file_bytes=size - 1)
    with pytest.raises(FederationError) as caught:
        document.DocumentTree(store)
    assert_error(caught, "limit_exceeded", "File byte limit")
    assert store.reads == []
    limits = {"max_file_bytes": size, limit: 1 if limit == "max_files" else size}
    reader = document.DocumentTree(document.MemoryStore(files, **limits))
    for record in document.sample_records()[0]:
        reader.metadata(record["entity"]["xid"])
    assert reader.collection(ITEM + "/versions")["complete"] is True
    assert reader.reads == ["registry.json"]
    assert reader.store.total_bytes == size
    with pytest.raises(FederationError) as caught:
        reader.document(V1)
    assert_error(caught, "limit_exceeded", message)
    assert reader.reads == ["registry.json"]


def test_split_tree_counts_each_metadata_file_against_the_file_limit():
    files = encode_form("sample", "split")
    store = document.MemoryStore(files, max_files=4)
    reader = document.DocumentTree(store)
    with pytest.raises(FederationError) as caught:
        reader.metadata(V1)
    assert_error(caught, "limit_exceeded", "File count limit")
    assert store.reads[:3] == ["registry.json", "indexes/n3.json", "records/n4.json"]
    assert len(store.reads) == 4


@pytest.mark.parametrize("limit", ["max_inline_depth", "max_objects"])
@pytest.mark.parametrize("value", [0, -1, True, 1.5], ids=["zero", "negative", "boolean", "float"])
def test_document_tree_inline_bounds_require_positive_integers(limit, value):
    store = document.MemoryStore({"registry.json": b"unread"})
    with pytest.raises(FederationError) as caught:
        document.DocumentTree(store, **{limit: value})
    assert_error(caught, "invalid_package", "Limits must be positive integers")
    assert store.reads == []


def test_document_encoder_inline_selection_keeps_split_paths_for_external_targets():
    records, documents = document.sample_records()
    before = copy.deepcopy((records, documents))
    calls = []

    def choose(kind, xid):
        calls.append((kind, xid))
        return kind == "meta"

    files = document.encode_tree(records, documents, inline=choose)
    assert (records, documents) == before
    collections = collection_xids(encode_form("sample", "inline"))
    assert sorted(calls) == sorted(
        [(record["kind"], record["entity"]["xid"]) for record in records if record["kind"] != "registry"]
        + [("collection", xid) for xid in collections]
    )
    split = encode_form("sample", "split")
    metas = {
        name for name, data in split.items()
        if name.startswith("records/") and json.loads(data)["kind"] == "meta"
    }
    assert len(metas) == sum(record["kind"] == "meta" for record in records)
    assert set(files) == set(split) - metas
    assert all(files[name] == split[name] for name in files if name.startswith("documents/"))
    single = document.encode_tree(records, documents, inline={ITEM + "/meta"})
    assert set(single) == set(split) - {"records/n9.json"}


@pytest.mark.parametrize(
    "options,code,message",
    [
        pytest.param({"inline": "yes"}, "invalid_package",
                     "Inline selection must be a boolean, a predicate or a set of XIDs", id="string"),
        pytest.param({"inline": 1}, "invalid_package",
                     "Inline selection must be a boolean, a predicate or a set of XIDs", id="number"),
        pytest.param({"inline": {1}}, "invalid_package",
                     "Inline selection must be a boolean, a predicate or a set of XIDs",
                     id="non-string"),
        pytest.param({"inline": {"/"}}, "invalid_package",
                     "Registry record cannot be inline", id="root-inline"),
        pytest.param({"inline": {ITEM + "/absent"}}, "invalid_package",
                     "Unknown inline fixture XID", id="unknown-inline"),
        pytest.param({"inline": lambda kind, xid: "yes"}, "invalid_package",
                     "Inline selector must return a boolean", id="predicate-result"),
        pytest.param({"paths": {"/": "root.json"}}, "invalid_package",
                     "Registry record path is fixed", id="root-path"),
        pytest.param({"paths": {ITEM + "/absent": "absent.json"}}, "invalid_package",
                     "Unused fixture path", id="unknown-path"),
        pytest.param({"inline": True, "paths": {ITEM: "item.json"}}, "invalid_package",
                     "Unused fixture path", id="inline-path"),
        pytest.param({"paths": {ITEM: "../item.json"}}, "policy_denied",
                     "Unsafe storage name", id="unsafe-path"),
        pytest.param({"paths": {ITEM: "item.json", V1: "ITEM.json"}}, "invalid_package",
                     "Duplicate fixture path", id="case-collision"),
        pytest.param({"paths": {ITEM: "documents/n1.bin"}}, "invalid_package",
                     "Duplicate fixture path", id="metadata-on-document"),
        pytest.param({"document_paths": {ITEM + "/absent": "absent.bin"}}, "invalid_package",
                     "Unknown fixture document path", id="unknown-document"),
        pytest.param({"document_paths": {V1: "registry.json"}}, "invalid_package",
                     "Duplicate fixture path", id="document-on-root"),
        pytest.param({"gitattributes": "*.json text"}, "invalid_package",
                     "Fixture .gitattributes must be bytes", id="gitattributes"),
    ],
)
def test_document_encoder_rejects_invalid_layout_options(options, code, message):
    records, documents = document.sample_records()
    before = copy.deepcopy((records, documents))
    with pytest.raises(FederationError) as caught:
        document.encode_tree(records, documents, **options)
    assert_error(caught, code, message)
    assert (records, documents) == before


def test_document_sample_writer_and_cli_build_the_inline_form(tmp_path, capsys):
    expected = encode_form("sample", "inline")
    root = tmp_path / "written"
    result = document.write_sample(root, inline=True)
    assert result == {
        "records": 24, "indexes": 13, "documents": 3,
        "rootsha256": hashlib.sha256(expected["registry.json"]).hexdigest(),
        "completeness": "offline-complete", "pin": None,
    }
    written = {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*") if path.is_file()
    }
    assert written == expected
    cli_root = tmp_path / "cli"
    assert document.main(["build-sample", str(cli_root), "--inline"]) == 0
    output = capsys.readouterr()
    assert output.err == ""
    assert json.loads(output.out) == result
    assert document.main(["entity", str(cli_root), V1]) == 0
    entity = json.loads(capsys.readouterr().out)
    assert entity["entity"] == {**V1_ENTITY, "self": "#/entity"}
    assert entity["reads"] == ["registry.json"]
    assert entity["origin"]["rootsha256"] == result["rootsha256"]
    assert document.main(["entity", str(cli_root), V1, "--inline"]) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert json.loads(output.err) == {
        "error": "invalid_package", "message": "--inline only applies to build-sample",
    }


@pytest.mark.parametrize("form", FORMS)
def test_document_schemas_accept_every_generated_form(form):
    schemas = {
        name: json.loads((SCHEMA_ROOT / f"document-{name}.schema.json").read_bytes())
        for name in ("record", "index")
    }
    registry = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas.values()
    )
    validators = {
        name: Draft202012Validator(schema, registry=registry, format_checker=FormatChecker())
        for name, schema in schemas.items()
    }
    for dataset in ("walkthrough", "sample"):
        for name, data in encode_form(dataset, form).items():
            if name.endswith(".json") and name != WALKTHROUGH_DOCUMENT:
                value = json.loads(data)
                schema = "index" if value["kind"] == "collection" else "record"
                assert list(validators[schema].iter_errors(value)) == [], (dataset, name)
    reference = Draft202012Validator(
        {"$ref": schemas["record"]["$id"] + "#/$defs/reference"},
        registry=registry, format_checker=FormatChecker(),
    )
    inline = json.loads(encode_form("walkthrough", "inline")["registry.json"])["collections"][0]
    external = json.loads(encode_form("walkthrough", "split")["registry.json"])["collections"][0]
    assert reference.is_valid(inline) and reference.is_valid(external)
    rejected = [
        {**inline, "href": external["href"]},
        {**external, "inline": inline["inline"]},
        {key: value for key, value in external.items() if key != "sha256"},
        {"kind": "collection", "xid": "/documents"},
        {**inline, "inline": []},
        {**inline, "inline": {**inline["inline"], "formatversion": "2"}},
        {**inline, "kind": "group"},
    ]
    assert [reference.is_valid(value) for value in rejected] == [False] * len(rejected)
