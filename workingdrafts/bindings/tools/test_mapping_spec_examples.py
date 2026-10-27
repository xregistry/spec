"""Keep the complete directory mapping walkthrough executable and byte-accurate."""

import hashlib
import shutil

import pytest

from workingdrafts.bindings.tools.mapping_examples import (
    DocumentTree, FileStore, MemoryStore, encode_tree,
)
from workingdrafts.federation.tools.federation_examples import FederationError


RESOURCE = "/documents/main/assets/widget"
VERSIONS = RESOURCE + "/versions"
VERSION = VERSIONS + "/v1"
DOCUMENT_HREF = "source/specs/widget.json"
DOCUMENT = b'{"type":"string"}\n'
DOCUMENT_SHA256 = "85803e087e684bdab3e5d6c2dd1af627da83382db625be9a42aea3d4d06539be"
TIMESTAMP = "2026-01-01T00:00:00Z"
SPLIT_PATHS = {
    "/documents": "registry-metadata/groups.json",
    "/documents/main": "registry-metadata/main.json",
    "/documents/main/assets": "registry-metadata/assets.json",
    RESOURCE: "registry-metadata/widget.json",
    RESOURCE + "/meta": "registry-metadata/widget-meta.json",
    VERSIONS: "registry-metadata/versions.json",
    VERSION: "source/specs/widget.registry.json",
}
# Sizes and digests of the earlier one-file-per-object walkthrough.
PREVIOUS_SPLIT = {
    "registry.json": (1215, "cd37736cd5ac0476d8fae3bf04967c1e317b818d11e146e2bdcba5c6bb748888"),
    "registry-metadata/groups.json": (361, "edafff00fe4486be418968a4d3b770ff40a3b60c75ddc015f34252cca1c8c330"),
    "registry-metadata/main.json": (510, "b963e9db3e1ecdebe20c78be39d0fd98b26d2beb1338e06223b92e9164666d04"),
    "registry-metadata/assets.json": (392, "72c43f08dd89af2c16b51ab9dc21fc36b7901ab475cae7ebb9e610c6a6cc9626"),
    "registry-metadata/widget.json": (679, "630d2ea1e6d94f89c75a3c56a74a713c4b232a81fb3fff874a83320405b9efdb"),
    "registry-metadata/widget-meta.json": (361, "9a34e98106eef18aa64b07c5878d75c0a5dfd96f3823750584709365b2681895"),
    "registry-metadata/versions.json": (423, "08a43de17e9d6630a57b315a47583e1b1c785b965df05c91823900807cbe2010"),
    "source/specs/widget.registry.json": (580, "6587872b270d75ecaa6be1028518d47bff4ac282379d89f1c34c6efce8c1b70f"),
    DOCUMENT_HREF: (18, DOCUMENT_SHA256),
}


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


def encode_walkthrough(inline=True, **options):
    """Encode the walkthrough beside its existing document, without .gitattributes."""
    records, documents = walkthrough_source()
    return encode_tree(
        records, documents, inline=inline, document_paths={VERSION: DOCUMENT_HREF},
        gitattributes=None, **options,
    )


def digests(files):
    return {name: (len(data), hashlib.sha256(data).hexdigest()) for name, data in files.items()}


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
    assert digests({"registry.json": generated["registry.json"]}) == {"registry.json": (
        6131, "cf679704edd89c2364b3163c063d9d8f6a5361e0cf54acf2ae0bd90987fa3ccb",
    )}


def test_walkthrough_split_form_reproduces_the_previous_one_file_per_object_mapping(walkthrough_root):
    files = encode_walkthrough(inline=False, paths=SPLIT_PATHS)
    assert digests(files) == PREVIOUS_SPLIT
    split = DocumentTree(MemoryStore(files))
    aggregated = DocumentTree(FileStore(walkthrough_root))
    for xid in ("/", "/documents/main", RESOURCE, RESOURCE + "/meta", VERSION):
        assert split.metadata(xid) == aggregated.metadata(xid)
    assert split.document(RESOURCE) == aggregated.document(RESOURCE) == DOCUMENT
    expected = {key: value for key, value in aggregated.validate().items() if key != "rootsha256"}
    assert {key: value for key, value in split.validate().items() if key != "rootsha256"} == expected
    metadata_reads = [name for name in split.reads if name != DOCUMENT_HREF]
    assert sorted(metadata_reads) == sorted(set(PREVIOUS_SPLIT) - {DOCUMENT_HREF})


def test_walkthrough_mixed_form_keeps_one_collection_in_its_own_file(walkthrough_root):
    files = encode_walkthrough(
        inline=lambda kind, xid: xid != VERSIONS,
        paths={VERSIONS: SPLIT_PATHS[VERSIONS]},
    )
    assert sorted(files) == [SPLIT_PATHS[VERSIONS], "registry.json", DOCUMENT_HREF]
    mixed = DocumentTree(MemoryStore(files))
    aggregated = DocumentTree(FileStore(walkthrough_root))
    for xid in ("/documents/main", RESOURCE, RESOURCE + "/meta"):
        assert mixed.read_record(xid)["entity"] == aggregated.read_record(xid)["entity"]
    assert mixed.reads == ["registry.json"]
    assert mixed.metadata(VERSION) == aggregated.metadata(VERSION)
    assert mixed.reads == ["registry.json", SPLIT_PATHS[VERSIONS]]
    assert mixed.document(RESOURCE) == DOCUMENT
    assert mixed.reads == ["registry.json", SPLIT_PATHS[VERSIONS], DOCUMENT_HREF]


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
