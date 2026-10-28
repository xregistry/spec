"""The approved single-source CLI, tested through native readers and literal oracles."""

from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
from unittest.mock import patch
from uuid import uuid4
from urllib.parse import urlsplit

import pytest

from workingdrafts.bindings.tools import mapping_examples as mapping
from workingdrafts.bindings.tools import oci_examples as oci
from workingdrafts.federation.tools import federation_examples as federation
from workingdrafts.federation.tools import generate_examples as generate


NAMES = ("walkthrough", "portable", "offline", "linked", "first", "second")
SELECTED_PAIRS = (
    ("walkthrough", "file"),
    ("portable", "file"),
    ("portable", "git"),
    ("portable", "oci"),
    ("offline", "oci"),
    ("linked", "oci"),
    ("first", "file"),
    ("second", "file"),
)
ITEM = "/documents/main/assets/item"
OCI_ITEM = "/dirs/main/files/sample"
ORACLES = {
    "walkthrough": ("workshop", "/documents/main/assets/widget", b'{"type":"string"}\n', 5),
    "portable": ("first", ITEM, b'{"hello":"world"}\n', 24),
    "offline": ("fixture-offline", OCI_ITEM, b'{"type":"string"}\n', 25),
    "linked": ("fixture-linked", OCI_ITEM, b'{"type":"string"}\n', 25),
    "first": ("first", ITEM, b'{"type":"string"}', 18),
    "second": ("second", ITEM, b'{"type":"number"}', 5),
}
SOURCE = Path(__file__).resolve().parents[1] / "examples.json"


def _invoke(args):
    output = io.StringIO()
    with redirect_stdout(output):
        status = generate.main([str(arg) for arg in args])
    assert status == 0, output.getvalue()
    return json.loads(output.getvalue())


def _git(path, *args):
    environment = {k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")}
    environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    completed = subprocess.run(
        ["git", "--no-pager", "--git-dir=" + str(path), *args],
        capture_output=True, env=environment, timeout=30,
    )
    assert completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace")
    return completed.stdout


def _reader(binding, root):
    if binding == "oci":
        return oci.FixtureLayout(root, "snapshot")
    store = (
        mapping.GitStore(root, "refs/tags/snapshot", path="xregistry")
        if binding == "git" else mapping.FileStore(root)
    )
    return mapping.DocumentTree(store)


def _entity(reader, xid):
    if isinstance(reader, oci.FixtureLayout):
        result = reader.lookup(xid)
        value = result["value"]
        for component in result["pointer"].strip("/").split("/") if result["pointer"] else []:
            value = value[component.replace("~1", "/").replace("~0", "~")]
        return value
    return reader.metadata(xid)["entity"]


def _document(reader, xid):
    return (
        reader.lookup(xid, operation="document")["data"]
        if isinstance(reader, oci.FixtureLayout) else reader.document(xid)
    )


def _collection(reader, xid):
    return (
        reader.lookup(xid, operation="collection")["value"]
        if isinstance(reader, oci.FixtureLayout) else reader.collection(xid)["entities"]
    )


def _files(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


@pytest.fixture(scope="session")
def generated_examples(tmp_path_factory):
    """One generation per dataset/binding; mutation tests generate private copies."""
    before = SOURCE.read_bytes()
    outputs = {}
    for name, binding in SELECTED_PAIRS:
        root = tmp_path_factory.mktemp(f"{binding}-{name}")
        result = _invoke([binding, "--example", name, "--output", root])
        outputs[name, binding] = (root, result)
    assert SOURCE.read_bytes() == before
    return outputs


@pytest.mark.parametrize(
    "name,binding", SELECTED_PAIRS,
    ids=[f"{name}-{binding}" for name, binding in SELECTED_PAIRS],
)
def test_selected_bindings_read_back_metadata_models_defaults_and_bytes(generated_examples, name, binding):
    root, result = generated_examples[name, binding]
    reader = _reader(binding, root)
    registryid, resource, content, count = ORACLES[name]
    assert result["example"] == name
    assert result["binding"] == binding
    assert reader.validate()["records"] == count
    registry = _entity(reader, "/")
    assert registry["registryid"] == registryid
    assert registry["xid"] == "/"
    assert registry["specversion"] == "1.0-rc4"
    assert registry["epoch"] == 1
    meta = _entity(reader, resource + "/meta")
    assert meta["defaultversionid"] == "v1"
    assert meta["defaultversionsticky"] is True
    version = _entity(reader, resource + "/versions/v1")
    assert version["versionid"] == version["ancestorid"] == "v1"
    assert version["isdefault"] is True
    assert version["xid"] == resource + "/versions/v1"
    assert _document(reader, resource) == content
    assert _document(reader, resource + "/versions/v1") == content
    versions = _collection(reader, resource + "/versions")
    assert set(versions) == (
        {"v1", "v2", "v3"} if name == "first"
        else {"v1", "v2"} if name in ("portable", "offline", "linked")
        else {"v1"}
    )
    model = reader.lookup("/", operation="model")["value"] if binding == "oci" else reader.model()
    caps = reader.lookup("/", operation="capabilities")["value"] if binding == "oci" else reader.capabilities()
    group, _, collection = resource.strip("/").split("/")[:3]
    definition = model["model"]["groups"][group]["resources"][collection]
    assert definition["metaattributes"]["xref"]["type"] == "xid"
    assert definition["attributes"]["versionid"]["type"] == "string"
    assert model["modelsource"]["groups"][group]["singular"] == ("dir" if group == "dirs" else "document")
    assert caps["pagination"] is False
    assert caps["available"] == {
        "capabilities": {"mutable": False}, "entities": {"mutable": False},
        "model": {"mutable": False}, "modelsource": {"mutable": False},
    }
    if binding == "git":
        commit = _git(root, "rev-parse", "refs/heads/main").decode().strip()
        assert reader.store.pin == commit
        assert result["pin"] == commit
        assert result["root"] == "xregistry"
        assert result["revision"] == "refs/heads/main"
        assert result["tag"] == "refs/tags/snapshot"
        assert _git(root, "rev-parse", "refs/tags/snapshot^{}").decode().strip() == commit
        assert _git(root, "cat-file", "-t", "refs/tags/snapshot") == b"tag\n"
        assert len(commit) == 40
        assert _git(root, "remote") == b""
        assert not (root / "xregistry").exists()
        pinned = mapping.DocumentTree(mapping.GitStore(root, commit, path="xregistry"))
        assert pinned.document(resource) == content
    elif binding == "oci":
        entry = json.loads((root / "index.json").read_bytes())["manifests"]
        assert len(entry) == 1
        assert entry[0]["annotations"]["org.opencontainers.image.ref.name"] == "snapshot"
        assert reader.root_digest == entry[0]["digest"]
        assert result["pin"] == reader.root_digest
        assert result["reference"] == "snapshot"
        assert all(item["mediaType"] != "application/vnd.oci.image.layer.v1.tar" for item in reader.inventory)
    else:
        assert reader.root_sha256 == hashlib.sha256((root / "registry.json").read_bytes()).hexdigest()
        assert result["pin"] == reader.root_sha256


@pytest.mark.parametrize("binding", ['file', 'oci'])
def test_generated_portable_aliases_empty_binary_metadata_only_and_imports(generated_examples, binding):
    reader = _reader(binding, generated_examples["portable", binding][0])
    assert _document(reader, "/documents/main/assets/CON/versions/a%3Ab%40c.") == b"\x00\x01\xff\x7f\n"
    assert _document(reader, ITEM + "/versions/v2") == b""
    assert _document(reader, "/mirrors/local/assets/copy") == b'{"hello":"world"}\n'
    assert _entity(reader, "/mirrors/local/assets/copy")["meta"]["xref"] == ITEM
    for alias in ("dangling", "chain"):
        with pytest.raises(federation.FederationError) as failure:
            _document(reader, "/mirrors/local/assets/" + alias)
        assert failure.value.code == "not_found"
    with pytest.raises(federation.FederationError) as metadata_only:
        _document(reader, "/documents/main/notes/item")
    assert metadata_only.value.code == "unsupported_operation"
    assert _collection(reader, "/independent/MAIN/assets") == {}
    assert _entity(reader, ITEM + "/versions/v1")["labels"] == {"stage": "production", "note": ""}
    model = reader.lookup("/", operation="model")["value"] if binding == "oci" else reader.model()
    assert model["modelsource"]["groups"]["mirrors"]["ximportresources"] == ["/documents/assets"]
    assert "ximportresources" not in model["modelsource"]["groups"]["independent"]
    assert model["model"]["groups"]["mirrors"]["resources"]["assets"]["attributes"]["purpose"]["type"] == "string"


@pytest.mark.parametrize("binding", ["file"])
def test_inline_option_stores_every_record_and_index_in_the_root(tmp_path, binding):
    split, inline = tmp_path / "split", tmp_path / "inline"
    _invoke([binding, "--example", "portable", "--output", split])
    result = _invoke([binding, "--example", "portable", "--output", inline, "--inline"])
    readers = [_reader(binding, root) for root in (split, inline)]
    assert readers[1].validate()["records"] == readers[0].validate()["records"] == 24
    assert readers[1].reads == ["registry.json"] + [
        name for name in readers[0].reads if name.startswith("documents/")
    ]
    for xid in ("/", ITEM, ITEM + "/versions/v1", "/documents/main/assets/CON"):
        assert readers[1].metadata(xid) == readers[0].metadata(xid)
    assert readers[1].document(ITEM) == b'{"hello":"world"}\n'
    if binding == "file":
        assert sorted(_files(inline)) == [
            ".gitattributes", "documents/n0.bin", "documents/n1.bin", "documents/n2.bin", "registry.json",
        ]
        assert result["root"] == str(inline / "registry.json")


def test_validate_is_read_only_and_default_input_is_not_cwd(tmp_path, monkeypatch):
    before = SOURCE.read_bytes()
    monkeypatch.chdir(tmp_path)
    result = _invoke(["validate"])
    assert set(result["examples"]) == set(NAMES)
    assert {
        name: (value["records"], value["documents"])
        for name, value in result["examples"].items()
    } == {
        "walkthrough": (5, 1), "portable": (24, 3), "offline": (25, 4),
        "linked": (25, 3), "first": (18, 3), "second": (5, 1),
    }
    # Counts match what `file` writes: the walkthrough keeps its inline project layout.
    assert result["examples"]["walkthrough"]["mapping_files"] == 3
    assert result["examples"]["portable"]["mapping_files"] == 41
    assert list(tmp_path.iterdir()) == []
    assert SOURCE.read_bytes() == before


@pytest.mark.parametrize("binding", ['file'])
def test_nonempty_destination_is_rejected_without_changes(tmp_path, capsys, binding):
    sentinel = tmp_path / "keep.bin"
    sentinel.write_bytes(b"do not replace\x00\xff")
    before = _files(tmp_path)
    status = generate.main([binding, "--example", "first", "--output", str(tmp_path)])
    captured = capsys.readouterr()
    assert status != 0
    assert "policy_denied" in captured.err
    assert _files(tmp_path) == before


def test_portable_git_snapshot_has_independent_fixed_identity_and_pin(generated_examples):
    root, result = generated_examples["portable", "git"]
    assert result["pin"] == "d3fd1b8c6ee742dc95b01b5f37e28e8214082fd3"
    commit = _git(root, "cat-file", "commit", result["pin"])
    assert b"author xRegistry example <example@example.invalid> 946684800 +0000\n" in commit
    assert b"committer xRegistry example <example@example.invalid> 946684800 +0000\n" in commit
    assert commit.endswith(b"\n\nRegistry example snapshot\n")
    assert b"\nparent " not in commit
    tag = _git(root, "cat-file", "tag", "refs/tags/snapshot")
    assert tag.startswith(b"object d3fd1b8c6ee742dc95b01b5f37e28e8214082fd3\ntype commit\ntag snapshot\n")
    assert tag.endswith(b"\n\nRegistry example snapshot\n")


def test_custom_source_preserves_utf8_crlf_and_origin_base_without_reserializing(tmp_path):
    example = federation.load_example("second")
    example["documents"][ITEM + "/versions/v1"] = {
        "text": ' { "snow": "\u96ea" }\r\n',
        "origin": "https://example.invalid/source/spec.json",
        "base": "https://example.invalid/source/",
    }
    source = tmp_path / "source.json"
    source.write_text(json.dumps({"exampleformat": 1, "examples": {"custom": example}}), encoding="utf-8")
    for binding in ("file", "oci"):
        output = tmp_path / binding
        _invoke([binding, "--example", "custom", "--input", source, "--output", output])
        reader = _reader(binding, output)
        assert _document(reader, ITEM) == b' { "snow": "\xe9\x9b\xaa" }\r\n'
        descriptor = (
            reader.lookup(ITEM, operation="document") if binding == "oci"
            else reader.document_descriptor(ITEM)
        )
        assert descriptor["origin"] == "https://example.invalid/source/spec.json"
        assert descriptor["base"] == "https://example.invalid/source/"


def test_failed_push_retains_valid_layout_and_reports_failure_not_publication(tmp_path, capsys):
    output = tmp_path / "layout"
    with patch.object(generate.shutil, "which", return_value="oras"), patch.object(
        generate.subprocess, "run", return_value=subprocess.CompletedProcess(
            ["oras"], 9, b"", b"denied https://user:secret@registry.invalid/repo",
        ),
    ):
        status = generate.main([
            "oci", "--example", "second", "--output", str(output),
            "--push", "registry.invalid/test/catalog:tag",
        ])
    captured = capsys.readouterr()
    assert status == 1
    assert captured.out == ""
    error = json.loads(captured.err)
    assert error["error"] == "unavailable"
    assert "denied" in error["message"] and "9" in error["message"]
    assert "user:secret" not in error["message"]
    assert _document(oci.FixtureLayout(output, "snapshot"), ITEM) == b'{"type":"number"}'


def test_oras_registry_roundtrip_preserves_digest_closure_and_survives_moved_tag(tmp_path):
    repository = os.environ.get("XREGISTRY_TEST_REGISTRY")
    if not repository:
        pytest.skip("Set XREGISTRY_TEST_REGISTRY to an isolated test registry/repository to exercise ORAS")
    executable = shutil.which("oras")
    assert executable is not None, "XREGISTRY_TEST_REGISTRY is configured but ORAS is unavailable"
    hostname = urlsplit("https://" + repository).hostname
    plain_http = hostname in ("localhost", "127.0.0.1", "::1")
    destination = repository.rstrip("/") + ":pytest-" + uuid4().hex
    push_flags = ["--plain-http"] if plain_http else []
    original = tmp_path / "original"
    first = _invoke([
        "oci", "--example", "offline", "--output", original, "--reference", "offline",
        "--page-size", "2", "--push", destination, *push_flags,
    ])
    digest = first["pin"]
    assert digest == "sha256:c937f902c54ca9c63e510bab3b4ec07ec3775ad338ac030ac93d916a736efba6"
    assert first["publication"] == {"destination": destination, "digest": digest}

    def pull(source, output):
        command = [executable, "cp", "--to-oci-layout"]
        if plain_http:
            command.append("--from-plain-http")
        completed = subprocess.run(
            [*command, source, str(output) + ":snapshot"],
            capture_output=True, timeout=300,
        )
        assert completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace")

    pulled = tmp_path / "pulled"
    pull(repository + "@" + digest, pulled)
    # ORAS rewrites index.json; explicit root-digest reads preserve strict typing.
    reader = oci.FixtureLayout(pulled, digest)
    assert reader.validate()["objects"] == 99
    assert _files(original / "blobs") == _files(pulled / "blobs")
    assert _document(reader, "/dirs/main/files/binary") == b"\x00\x01\x7f\x80\xff\r\n"
    assert _document(reader, "/dirs/main/files/empty") == b""
    assert _document(reader, OCI_ITEM) == b'{"type":"string"}\n'
    second = _invoke([
        "oci", "--example", "second", "--output", tmp_path / "replacement",
        "--push", destination, *push_flags,
    ])
    assert second["pin"] != digest
    moved = tmp_path / "moved"
    pull(destination, moved)
    assert _document(oci.FixtureLayout(moved, second["pin"]), ITEM) == b'{"type":"number"}'
    again = tmp_path / "pinned-again"
    pull(repository + "@" + digest, again)
    assert _files(original / "blobs") == _files(again / "blobs")
    assert _document(reader, OCI_ITEM) == b'{"type":"string"}\n'
    assert oci.FixtureLayout(again, digest).validate()["objects"] == 99
