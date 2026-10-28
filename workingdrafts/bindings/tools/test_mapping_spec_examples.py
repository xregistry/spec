"""Keep the complete directory mapping walkthrough executable and byte-accurate."""

import hashlib
import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from workingdrafts.bindings.tools import mapping_examples as document
from workingdrafts.bindings.tools.mapping_examples import DocumentTree, FileStore, encode_tree
from workingdrafts.federation.tools.federation_examples import FederationError


RESOURCE = "/documents/main/assets/widget"
VERSIONS = RESOURCE + "/versions"
VERSION = VERSIONS + "/v1"
DOCUMENT_HREF = "source/specs/widget.json"
DOCUMENT = b'{"type":"string"}\n'
DOCUMENT_SHA256 = "85803e087e684bdab3e5d6c2dd1af627da83382db625be9a42aea3d4d06539be"
TIMESTAMP = "2026-01-01T00:00:00Z"


def walkthrough_source():
    """Return the walkthrough Registry as encoder input: records and document bytes."""
    stamp = {"epoch": 1, "createdat": TIMESTAMP, "modifiedat": TIMESTAMP}
    readonly = {"mutable": False}
    records = [
        {
            "kind": "registry",
            "entity": {
                "xid": "/", "registryid": "workshop", "specversion": "1.0-rc4", **stamp,
                "modelsource": {"groups": {"documents": {
                    "singular": "document",
                    "resources": {"assets": {"singular": "asset"}},
                }}},
                "capabilities": {
                    "available": {
                        name: dict(readonly)
                        for name in ("capabilities", "entities", "model", "modelsource")
                    },
                    "flags": ["doc", "inline"],
                    "pagination": False,
                },
            },
            "snapshot": {"scope": "/", "completeness": "offline-complete"},
        },
        {"kind": "group", "entity": {"xid": "/documents/main", "documentid": "main", **stamp}},
        {"kind": "resource", "entity": {"xid": RESOURCE, "assetid": "widget"}},
        {
            "kind": "meta",
            "entity": {
                "xid": RESOURCE + "/meta", "assetid": "widget", **stamp, "readonly": True,
                "defaultversionid": "v1", "defaultversionsticky": True,
            },
        },
        {
            "kind": "version",
            "entity": {
                "xid": VERSION, "assetid": "widget", "versionid": "v1", **stamp,
                "ancestorid": "v1", "isdefault": True,
                "contenttype": "application/schema+json",
            },
        },
    ]
    return records, {VERSION: DOCUMENT}


def encode_walkthrough():
    """Encode the walkthrough beside its existing document, without .gitattributes."""
    records, documents = walkthrough_source()
    return encode_tree(
        records, documents, inline=True, document_paths={VERSION: DOCUMENT_HREF},
        gitattributes=None,
    )


def test_complete_mapping_walkthrough_reads_the_document_and_version_metadata(walkthrough_root):
    reader = DocumentTree(FileStore(walkthrough_root))
    result = reader.validate()
    assert (result["records"], result["indexes"], result["documents"]) == (5, 3, 1)
    assert reader.reads == ["registry.json", DOCUMENT_HREF]
    assert reader.objects == 8
    assert reader.document(RESOURCE) == reader.document(VERSION) == DOCUMENT
    metadata = reader.metadata(VERSION)
    assert metadata["entity"]["self"] == "#/entity"
    assert metadata["entity"]["xid"] == VERSION
    assert metadata["entity"]["versionid"] == "v1"
    assert metadata["entity"]["contenttype"] == "application/schema+json"
    assert "asset" not in metadata["entity"]
    assert reader.document_descriptor(VERSION) == {
        "kind": "local", "href": DOCUMENT_HREF, "size": 18, "sha256": DOCUMENT_SHA256,
    }
    assert reader.reads == ["registry.json"] + [DOCUMENT_HREF] * 3


def test_walkthrough_adds_one_generated_metadata_file_beside_the_unchanged_document(walkthrough_root):
    present = sorted(
        path.relative_to(walkthrough_root).as_posix()
        for path in walkthrough_root.rglob("*") if path.is_file()
    )
    assert present == [".gitattributes", "registry.json", DOCUMENT_HREF]
    assert (walkthrough_root / ".gitattributes").read_bytes() == (
        b'*.json text eol=lf\n"/' + DOCUMENT_HREF.encode() + b'" -text\n'
    )
    existing = (walkthrough_root / DOCUMENT_HREF).read_bytes()
    assert (len(existing), hashlib.sha256(existing).hexdigest()) == (18, DOCUMENT_SHA256)
    # The shared example source must reproduce the independently authored walkthrough.
    generated = encode_walkthrough()
    assert generated == {
        "registry.json": (walkthrough_root / "registry.json").read_bytes(),
        DOCUMENT_HREF: existing,
    }
    metadata = generated["registry.json"]
    assert (len(metadata), hashlib.sha256(metadata).hexdigest()) == (
        6131, "cf679704edd89c2364b3163c063d9d8f6a5361e0cf54acf2ae0bd90987fa3ccb",
    )


def test_mapping_walkthrough_reports_modified_existing_content(tmp_path, walkthrough_root):
    copied = tmp_path / "project"
    shutil.copytree(walkthrough_root, copied)
    (copied / "source" / "specs" / "widget.json").write_bytes(b'{"type":"number"}\n')
    reader = DocumentTree(FileStore(copied))
    with pytest.raises(FederationError) as error:
        reader.document(VERSION)
    assert error.value.code == "integrity_error"
    assert str(error.value) == "Descriptor mismatch: " + DOCUMENT_HREF
    assert reader.reads == ["registry.json", DOCUMENT_HREF]


ITEM = "/documents/main/assets/item"
V1 = ITEM + "/versions/v1"
V2 = ITEM + "/versions/v2"
BINARY = "/documents/main/assets/CON/versions/a:b@c."
NOTE = "/documents/main/notes/item"
CATALOG = "/categories/main/registries/site"
COPY = "/mirrors/local/assets/copy"
DANGLING = "/mirrors/local/assets/dangling"
TIMESTAMPS = {
    "epoch": 1,
    "createdat": "2026-09-04T00:00:00Z",
    "modifiedat": "2026-09-04T00:00:00Z",
}
AUTHORED_JSON = b'{"hello":"world"}\n'
FORMATTED_JSON = b' { "value": 1 }\r\n'
EXACT_BINARY = b"\x00\xff\x10\r\n"
ITEM_RECORD_READS = [
    "registry.json", "indexes/n3.json", "records/n4.json",
    "indexes/n4.json", "records/n8.json",
]
ITEM_STATE_READS = ITEM_RECORD_READS + ["records/n9.json", "indexes/n6.json"]
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


def assert_metadata_only_reads(reads):
    assert reads[0] == "registry.json"
    assert not any(name.startswith("documents/") for name in reads)
    assert len(reads) == len(set(reads))


@pytest.mark.parametrize(
    "xid,expected,length,href",
    [
        pytest.param(V2, b"", 0, "documents/n4.bin", id="present-zero"),
    ],
)
def test_document_zero_byte_content_is_distinct_from_missing_and_metadata_only(
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
        pytest.param(V2, b"", "v2", id="explicit-v2"),
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


@pytest.mark.parametrize("version", ["v0"], ids=["absent"])
def test_document_explicit_version_absence_never_falls_back(tree, version):
    xid = ITEM + "/versions/" + version
    with pytest.raises(FederationError) as caught:
        tree.document(xid)
    assert_error(caught, "not_found", "XID not found: " + xid)
    assert tree.reads == ITEM_STATE_READS
    assert tree.store.pin is None


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
    "name,code,message",
    [
        pytest.param("../outside", "policy_denied", "Unsafe storage name", id="parent"),
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


FORMS = ("split", "inline", "mixed")
SELECTIONS = (
    ("/mirrors/local/assets", {"label": "stage", "value": "PRODUCTION"}),
    (ITEM + "/versions", {"label": "stage", "value": "development"}),
)


def mixed_sample(kind, xid):
    """Inline Groups, Metas, Versions and the mirrors subtree; keep the rest external."""
    return kind in ("group", "meta", "version") or xid.startswith("/mirrors")


def encode_form(form):
    inline = {"split": False, "inline": True, "mixed": mixed_sample}[form]
    return document.encode_tree(*document.sample_records(), inline=inline)


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


def test_split_inline_and_mixed_mappings_return_identical_reads(tmp_path):
    records, _ = document.sample_records()
    encoded = {form: encode_form(form) for form in FORMS}
    collections = collection_xids(encoded["inline"])
    collections.append(COPY + "/versions")
    expected = observations(
        document.DocumentTree(document.MemoryStore(encoded["split"])), records, collections
    )
    for form, files in encoded.items():
        location = tmp_path / form
        for name, data in files.items():
            path = location.joinpath(*name.split("/"))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        reader = document.DocumentTree(document.FileStore(location))
        assert observations(reader, records, collections) == expected, form
    assert set(encoded["mixed"]) < set(encoded["split"])
    assert len(encoded["inline"]) < len(encoded["mixed"])
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
