"""Map existing directory contents without changing their layout or bytes."""

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

import mapping_examples as document
from federation_examples import FederationError
from test_git_examples import GitFixture


ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "workingdrafts" / "bindings" / "samples" / "mapping"
ITEM = "/documents/main/assets/item"
V1 = ITEM + "/versions/v1"
BINARY = "/documents/main/assets/CON"


def relocated_files(*, shared_document=False):
    """Independently rebuild reference hashes after choosing existing paths."""
    original = {
        path.relative_to(FIXTURE).as_posix(): path.read_bytes()
        for path in FIXTURE.rglob("*") if path.is_file() and path.name != ".gitattributes"
    }
    locations = {
        name: "registry-metadata/" + name for name in original if name != "registry.json"
    }
    locations.update({
        "documents/n0.bin": "engineering/assets/image \u03b1.dat",
        "documents/n1.bin": "source/specs/widget.json",
        "documents/n2.bin": "notes/empty.txt",
        "records/na.json": "source/specs/widget.registry.json",
    })
    if shared_document:
        locations["documents/n2.bin"] = locations["documents/n1.bin"]
        original["documents/n2.bin"] = original["documents/n1.bin"]
    result = {}

    def visit(name, metadata=True):
        path = locations.get(name, name)
        data = original[name]
        if metadata:
            value = json.loads(data)
            references = value.get("entries", []) + value.get("collections", [])
            references += [value.get("meta"), value.get("document")]
            for reference in references:
                if not isinstance(reference, dict) or "href" not in reference:
                    continue
                target, content = visit(reference["href"], reference.get("kind") != "local")
                reference.update(href=target, size=len(content), sha256=hashlib.sha256(content).hexdigest())
            data = (json.dumps(value, indent=2) + "\n").encode("utf-8")
        result[path] = data
        return path, data

    visit("registry.json")
    return result


def test_existing_directory_becomes_registry_by_adding_metadata_only(tmp_path):
    mapped = relocated_files()
    existing = {
        "engineering/assets/image \u03b1.dat": b"\x00\x01\xff\x7f\n",
        "source/specs/widget.json": b'{"hello":"world"}\n',
        "notes/empty.txt": b"",
        "source/main.py": b"print('unrelated')\n",
        "README.md": b"Existing project\n",
    }
    for name, data in existing.items():
        path = tmp_path.joinpath(*name.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    for name, data in mapped.items():
        path = tmp_path.joinpath(*name.split("/"))
        if name in existing:
            assert path.read_bytes() == data
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    reader = document.DocumentTree(document.FileStore(tmp_path))
    assert reader.document(ITEM) == existing["source/specs/widget.json"]
    assert reader.document(ITEM + "/versions/v2") == b""
    assert reader.document(BINARY) == existing["engineering/assets/image \u03b1.dat"]
    assert reader.metadata(ITEM)["entity"]["meta"]["defaultversionid"] == "v1"
    assert reader.validate()["documents"] == 3
    assert all((tmp_path / name).read_bytes() == data for name, data in existing.items())
    assert not any((tmp_path / directory).exists() for directory in ("records", "indexes", "documents"))


def test_git_reads_same_mapping_from_an_unmodified_project_layout(tmp_path):
    files = relocated_files()
    files["src/application.txt"] = b"not part of Registry closure"
    git = GitFixture(tmp_path / "repo.git")
    commit = git.commit(files, prefix="")
    reader = document.DocumentTree(document.GitStore(git.path, commit, path=""))
    assert reader.document(V1) == b'{"hello":"world"}\n'
    assert reader.document(BINARY) == b"\x00\x01\xff\x7f\n"
    assert reader.store.pin == commit
    assert "src/application.txt" not in reader.reads
    assert "source/specs/widget.json" in reader.reads
    assert not (git.path / "source").exists()


def test_multiple_versions_can_reference_the_same_unchanged_existing_file():
    files = relocated_files(shared_document=True)
    reader = document.DocumentTree(document.MemoryStore(files))
    assert reader.document(V1) == b'{"hello":"world"}\n'
    assert reader.document(ITEM + "/versions/v2") == b'{"hello":"world"}\n'
    assert reader.document_descriptor(V1)["href"] == "source/specs/widget.json"
    assert reader.document_descriptor(ITEM + "/versions/v2")["href"] == "source/specs/widget.json"
    assert reader.validate()["documents"] == 3


def test_mapping_reader_keeps_integrity_checks_on_existing_files():
    files = relocated_files()
    files["source/specs/widget.json"] = b"changed after mapping"
    reader = document.DocumentTree(document.MemoryStore(files))
    with pytest.raises(FederationError) as error:
        reader.document(V1)
    assert error.value.code == "integrity_error"


def test_dotfile_does_not_replace_registry_json_entry_point(tmp_path):
    data = relocated_files()["registry.json"]
    (tmp_path / ".xregistry").write_bytes(data)
    store = document.FileStore(tmp_path)
    with pytest.raises(FederationError) as error:
        document.DocumentTree(store)
    assert error.value.code == "not_found"
    assert store.reads == []
    assert (tmp_path / ".xregistry").read_bytes() == data


@pytest.mark.parametrize("name", [
    "../outside.json", "/outside.json", "C:/outside.json",
    "data/../outside.json", "data//outside.json", r"data\outside.json",
    "data/file.json:stream", "data/%2e%2e/outside.json",
])
def test_mapping_rejects_escape_before_opening_any_existing_file(tmp_path, name):
    reader = document.FileStore(tmp_path)
    with patch.object(document.os, "open", side_effect=AssertionError("Unexpected file open")):
        with pytest.raises(FederationError) as error:
            reader.read(name)
    assert error.value.code == "policy_denied"
