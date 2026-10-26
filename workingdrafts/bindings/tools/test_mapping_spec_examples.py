"""Keep the complete directory mapping walkthrough executable and byte-accurate."""

import shutil
from pathlib import Path

import pytest

from workingdrafts.bindings.tools.mapping_examples import DocumentTree, FileStore
from workingdrafts.federation.tools.federation_examples import FederationError


ROOT = Path(__file__).resolve().parents[1]
WALKTHROUGH = ROOT / "samples" / "mapping-example"
RESOURCE = "/documents/main/assets/widget"
VERSION = RESOURCE + "/versions/v1"


def test_complete_mapping_walkthrough_reads_the_document_and_version_metadata():
    reader = DocumentTree(FileStore(WALKTHROUGH))
    result = reader.validate()
    assert (result["records"], result["indexes"], result["documents"]) == (5, 3, 1)
    assert reader.document(RESOURCE) == reader.document(VERSION) == b'{"type":"string"}\n'
    metadata = reader.metadata(VERSION)
    assert metadata["entity"]["self"] == "#/entity"
    assert metadata["entity"]["xid"] == VERSION
    assert metadata["entity"]["versionid"] == "v1"
    assert metadata["entity"]["contenttype"] == "application/schema+json"
    assert "asset" not in metadata["entity"]
    assert reader.document_descriptor(VERSION) == {
        "kind": "local", "href": "source/specs/widget.json", "size": 18,
        "sha256": "85803e087e684bdab3e5d6c2dd1af627da83382db625be9a42aea3d4d06539be",
    }


def test_mapping_walkthrough_reports_modified_existing_content(tmp_path):
    copied = tmp_path / "project"
    shutil.copytree(WALKTHROUGH, copied)
    (copied / "source" / "specs" / "widget.json").write_bytes(b'{"type":"number"}\n')
    reader = DocumentTree(FileStore(copied))
    with pytest.raises(FederationError) as error:
        reader.document(VERSION)
    assert error.value.code == "integrity_error"
