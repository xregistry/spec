"""The approved single-source CLI, tested through native readers and literal oracles."""

from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
from unittest.mock import Mock, patch
from uuid import uuid4
from urllib.parse import urlsplit

import pytest

from workingdrafts.bindings.tools import mapping_examples as mapping
from workingdrafts.bindings.tools import oci_examples as oci
from workingdrafts.federation.tools import federation_examples as federation
from workingdrafts.federation.tools import generate_examples as generate


NAMES = ("walkthrough", "portable", "offline", "linked", "first", "second")
BINDINGS = ("file", "git", "oci")
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
    for name in NAMES:
        for binding in BINDINGS:
            root = tmp_path_factory.mktemp(f"{binding}-{name}")
            result = _invoke([binding, "--example", name, "--output", root])
            outputs[name, binding] = (root, result)
    assert SOURCE.read_bytes() == before
    return outputs


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("binding", BINDINGS)
def test_all_six_examples_read_back_metadata_models_defaults_and_bytes(generated_examples, name, binding):
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


@pytest.mark.parametrize("binding", BINDINGS)
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


@pytest.mark.parametrize("binding", BINDINGS)
def test_generated_oci_datasets_preserve_imported_aliases_external_content_and_empty_collections(generated_examples, binding):
    for name in ("offline", "linked"):
        reader = _reader(binding, generated_examples[name, binding][0])
        assert _document(reader, "/dirs/main/files/binary") == b"\x00\x01\x7f\x80\xff\r\n"
        assert _document(reader, "/dirs/main/files/empty") == b""
        assert _document(reader, "/dirs/main/files/alias") == b'{"type":"string"}\n'
        assert _document(reader, "/imports/shared/files/alias") == b'{"type":"string"}\n'
        assert _collection(reader, "/emptygroups") == {}
        assert _collection(reader, "/dirs/empty/files") == {}
        assert _entity(reader, "/dirs/main")["labels"] == {"stage": "Ready", "empty": ""}
        with pytest.raises(federation.FederationError) as metadata_only:
            _document(reader, "/dirs/main/notes/info")
        assert metadata_only.value.code == "unsupported_operation"
        if name == "offline":
            assert _document(reader, OCI_ITEM + "/versions/v2") == b'{"type":"number"}\n'
        else:
            with pytest.raises(federation.FederationError) as external:
                _document(reader, OCI_ITEM + "/versions/v2")
            assert external.value.code == ("unavailable" if binding == "oci" else "unsupported_operation")


@pytest.mark.parametrize("binding", BINDINGS)
def test_generated_independent_registries_keep_colliding_xids_separate(generated_examples, binding):
    first = _reader(binding, generated_examples["first", binding][0])
    second = _reader(binding, generated_examples["second", binding][0])
    assert _entity(first, "/")["registryid"] == "first"
    assert _entity(second, "/")["registryid"] == "second"
    assert _entity(first, ITEM)["xid"] == _entity(second, ITEM)["xid"] == ITEM
    assert _document(first, ITEM) == b'{"type":"string"}'
    assert _document(second, ITEM) == b'{"type":"number"}'
    assert _document(first, ITEM + "/versions/v2") == b"\x00\xff"
    assert _document(first, ITEM + "/versions/v3") == b""


@pytest.mark.parametrize("binding", BINDINGS)
def test_generation_is_deterministic_across_empty_destinations(generated_examples, tmp_path, binding):
    first, _ = generated_examples["offline", binding]
    second = tmp_path / "second"
    _invoke([binding, "--example", "offline", "--output", second])
    if binding != "git":
        assert _files(first) == _files(second)
    else:
        assert _git(first, "show-ref") == _git(second, "show-ref")
        objects = _git(first, "cat-file", "--batch-all-objects", "--batch-check")
        assert objects == _git(second, "cat-file", "--batch-all-objects", "--batch-check")
        for line in objects.decode().splitlines():
            oid, kind, _ = line.split()
            assert _git(first, "cat-file", kind, oid) == _git(second, "cat-file", kind, oid)
    assert _document(_reader(binding, second), OCI_ITEM) == b'{"type":"string"}\n'


def test_file_walkthrough_keeps_the_inline_project_layout_and_exact_byte_attributes(generated_examples):
    root, _ = generated_examples["walkthrough", "file"]
    assert sorted(_files(root)) == [".gitattributes", "registry.json", "source/specs/widget.json"]
    assert (root / "source/specs/widget.json").read_bytes() == b'{"type":"string"}\n'
    assert mapping.DocumentTree(mapping.FileStore(root)).validate()["records"] == 5
    attributes = (root / ".gitattributes").read_text()
    assert '"/source/specs/widget.json" -text' in attributes
    assert "eol=lf" in attributes


@pytest.mark.parametrize("binding", ["file", "git"])
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


def test_inline_option_is_not_offered_for_oci(tmp_path):
    with pytest.raises(SystemExit) as failure:
        generate.main(["oci", "--example", "offline", "--output", str(tmp_path / "out"), "--inline"])
    assert failure.value.code == 2
    assert not (tmp_path / "out").exists()


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


@pytest.mark.parametrize("args", [
    ["file"], ["file", "--example", "first"], ["file", "--output", "unused"],
    ["git"], ["oci"],
])
def test_cli_requires_explicit_example_and_output(args):
    with pytest.raises(SystemExit) as failure:
        generate.main(args)
    assert failure.value.code == 2


@pytest.mark.parametrize("binding", BINDINGS)
def test_nonempty_destination_is_rejected_without_changes(tmp_path, capsys, binding):
    sentinel = tmp_path / "keep.bin"
    sentinel.write_bytes(b"do not replace\x00\xff")
    before = _files(tmp_path)
    status = generate.main([binding, "--example", "first", "--output", str(tmp_path)])
    captured = capsys.readouterr()
    assert status != 0
    assert "policy_denied" in captured.err
    assert _files(tmp_path) == before


@pytest.mark.parametrize("destination", ["checkout", "descendant", "ancestor", "root"])
def test_unsafe_destination_is_rejected_before_output(destination, capsys):
    root = Path(__file__).resolve().parents[3]
    output = {
        "checkout": root, "descendant": root / "not-a-generated-directory",
        "ancestor": root.parent, "root": Path(root.anchor),
    }[destination]
    before = SOURCE.read_bytes()
    status = generate.main(["file", "--example", "first", "--output", str(output)])
    assert status != 0
    assert "policy_denied" in capsys.readouterr().err
    assert SOURCE.read_bytes() == before
    assert not (root / "not-a-generated-directory").exists()


def test_unknown_example_and_missing_input_do_not_create_destination(tmp_path, capsys):
    for extra, code in ((["--example", "absent"], "not_found"),
                        (["--example", "first", "--input", str(tmp_path / "absent.json")], "unavailable")):
        output = tmp_path / "output"
        assert generate.main(["file", "--output", str(output), *extra]) != 0
        assert code in capsys.readouterr().err
        assert not output.exists()


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


def test_git_generation_ignores_ambient_identity_config_and_object_format(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_AUTHOR_NAME", "must not be used")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "must-not-be-used@example.invalid")
    monkeypatch.setenv("GIT_DEFAULT_HASH", "sha256")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.autocrlf")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "true")
    result = _invoke(["git", "--example", "portable", "--output", tmp_path / "repo.git"])
    assert result["pin"] == "d3fd1b8c6ee742dc95b01b5f37e28e8214082fd3"
    assert _git(tmp_path / "repo.git", "rev-parse", "--show-object-format") == b"sha1\n"
    assert _git(tmp_path / "repo.git", "remote") == b""


@pytest.mark.parametrize("binding", ["file", "oci"])
def test_offline_generation_needs_no_git_or_oras(tmp_path, binding):
    with patch.object(generate.shutil, "which", side_effect=AssertionError("Unexpected executable lookup")):
        result = _invoke([binding, "--example", "second", "--output", tmp_path])
    assert result["binding"] == binding
    assert _document(_reader(binding, tmp_path), ITEM) == b'{"type":"number"}'
    assert "publication" not in result


@pytest.mark.parametrize("binding,extra,tool", [
    ("git", [], "git"), ("oci", ["--push", "localhost:5000/test/catalog:sample"], "oras"),
])
def test_missing_tools_fail_before_creating_destination(tmp_path, capsys, binding, extra, tool):
    destination = tmp_path / "not-created"
    with patch.object(generate.shutil, "which", return_value=None) as lookup:
        assert generate.main([binding, "--example", "second", "--output", str(destination), *extra]) == 1
    lookup.assert_called_once_with(tool)
    error = json.loads(capsys.readouterr().err)
    assert error["error"] == "unavailable"
    assert tool in error["message"]
    assert not destination.exists()


@pytest.mark.parametrize("failure", ["exit", "timeout", "oserror"])
def test_git_subprocess_failures_keep_diagnostics_and_do_not_report_success(tmp_path, capsys, failure):
    destination = tmp_path / "not-created"
    if failure == "exit":
        run = Mock(return_value=subprocess.CompletedProcess(["git"], 17, b"", b"synthetic failure"))
    elif failure == "timeout":
        run = Mock(side_effect=subprocess.TimeoutExpired(["git"], 30))
    else:
        run = Mock(side_effect=OSError("synthetic launch failure"))
    with patch.object(generate.shutil, "which", return_value="git"), patch.object(generate.subprocess, "run", run):
        assert generate.main(["git", "--example", "second", "--output", str(destination)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err)["error"] == "unavailable"
    assert ("17" if failure == "exit" else "could not complete") in captured.err
    assert not destination.exists()
    assert run.call_count == 1
    command = run.call_args.args[0]
    assert isinstance(command, list)
    assert "--bare" in command
    assert "--template=" in command
    assert "--object-format=sha1" in command


@pytest.mark.parametrize("change", [
    "orphan", "missing-default", "unknown-ancestor", "incomplete-model",
    "missing-group-collection", "missing-metaattributes", "missing-document-attribute",
    "unknown-model-type", "metadata-only-lie", "inline-and-document", "wrong-import",
])
def test_invalid_semantic_source_never_creates_output(tmp_path, capsys, change):
    example = federation.load_example("second")
    root = example["records"][0]["entity"]
    version = example["records"][-1]["entity"]
    if change == "orphan":
        example["records"] = [r for r in example["records"] if r["kind"] != "group"]
    elif change == "missing-default":
        next(r for r in example["records"] if r["kind"] == "meta")["entity"]["defaultversionid"] = "absent"
    elif change == "unknown-ancestor":
        version["ancestorid"] = "absent"
    elif change == "incomplete-model":
        root["model"] = {"groups": deepcopy(root["modelsource"]["groups"])}
    elif change == "missing-group-collection":
        del root["model"]["groups"]["documents"]["attributes"]["assetscount"]
    elif change == "missing-metaattributes":
        del root["model"]["groups"]["documents"]["resources"]["assets"]["metaattributes"]
    elif change == "missing-document-attribute":
        del root["model"]["groups"]["documents"]["resources"]["assets"]["attributes"]["assetbase64"]
    elif change == "unknown-model-type":
        root["modelsource"]["groups"]["documents"]["resources"] = {}
    elif change == "metadata-only-lie":
        example["documents"][ITEM + "/versions/v1"] = {"none": True}
    elif change == "inline-and-document":
        version["assetbase64"] = "dW5leHBlY3RlZA=="
    else:
        root["modelsource"]["groups"]["documents"]["ximportresources"] = ["/missing/assets"]
    source = tmp_path / "invalid.json"
    payload = json.dumps({"exampleformat": 1, "examples": {"second": example}}).encode()
    source.write_bytes(payload)
    output = tmp_path / "output"
    status = generate.main(["file", "--example", "second", "--input", str(source), "--output", str(output)])
    assert status == 1
    assert json.loads(capsys.readouterr().err)["error"] == "invalid_package"
    assert not output.exists()
    assert source.read_bytes() == payload


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


@pytest.mark.parametrize("kind", ["symlink", "reparse"])
def test_destination_symlink_or_reparse_is_rejected_before_writes(tmp_path, capsys, kind):
    # Simulate the filesystem attribute so Windows needs no symlink privilege.
    original = Path.lstat

    def lstat(path, *args, **kwargs):
        value = original(path, *args, **kwargs)
        if path == tmp_path:
            result = Mock(wraps=value)
            result.st_mode = stat.S_IFLNK if kind == "symlink" else value.st_mode
            result.st_file_attributes = 0x400 if kind == "reparse" else 0
            return result
        return value

    with patch.object(Path, "lstat", lstat):
        assert generate.main(["file", "--example", "second", "--output", str(tmp_path / "child")]) == 1
    assert json.loads(capsys.readouterr().err)["error"] == "policy_denied"
    assert list(tmp_path.iterdir()) == []


def test_existing_output_file_is_not_replaced(tmp_path, capsys):
    output = tmp_path / "file"
    output.write_bytes(b"original")
    assert generate.main(["file", "--example", "second", "--output", str(output)]) == 1
    assert json.loads(capsys.readouterr().err)["error"] == "policy_denied"
    assert output.read_bytes() == b"original"


def test_output_storage_failure_is_reported_without_success(tmp_path, capsys):
    output = tmp_path / "unwritable"
    with patch.object(generate, "_write_files", side_effect=PermissionError("synthetic storage denial")):
        assert generate.main(["file", "--example", "second", "--output", str(output)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err) == {"error": "unavailable", "message": "synthetic storage denial"}
    assert not output.exists()


@pytest.mark.parametrize("extra,code", [
    (["--page-size", "-1"], "limit_exceeded"),
    (["--page-size", "0"], "limit_exceeded"),
    (["--page-size", "1"], "limit_exceeded"),
    (["--page-size", "257"], "limit_exceeded"),
    (["--reference", "not/a/tag"], "invalid_package"),
])
def test_invalid_oci_builder_options_leave_no_output(tmp_path, capsys, extra, code):
    output = tmp_path / "output"
    assert generate.main(["oci", "--example", "second", "--output", str(output), *extra]) == 1
    assert json.loads(capsys.readouterr().err)["error"] == code
    assert not output.exists()


@pytest.mark.parametrize("target,plain_http,code", [
    ("https://registry.example/test/catalog:tag", False, "invalid_package"),
    ("user:password@registry.example/test/catalog:tag", False, "invalid_package"),
    ("registry.example/test/catalog", False, "invalid_package"),
    ("registry.example/Test/catalog:tag", False, "invalid_package"),
    ("registry.example/test/catalog:tag", True, "policy_denied"),
])
def test_invalid_push_target_is_rejected_without_tool_or_output(tmp_path, capsys, target, plain_http, code):
    output = tmp_path / "output"
    args = ["oci", "--example", "second", "--output", str(output), "--push", target]
    if plain_http:
        args.append("--plain-http")
    with patch.object(generate.shutil, "which", side_effect=AssertionError("Unexpected executable lookup")):
        assert generate.main(args) == 1
    assert json.loads(capsys.readouterr().err)["error"] == code
    assert not output.exists()


@pytest.mark.parametrize("extra", [["--plain-http"], ["--registry-config", "unused.json"]])
def test_registry_options_require_explicit_push(tmp_path, capsys, extra):
    output = tmp_path / "output"
    assert generate.main(["oci", "--example", "second", "--output", str(output), *extra]) == 1
    assert json.loads(capsys.readouterr().err)["error"] == "invalid_package"
    assert not output.exists()


@pytest.mark.parametrize("destination,plain_http", [
    ("localhost:5000/test/catalog:tag", True),
    ("127.0.0.1:5000/test/catalog:tag", True),
    ("[::1]:5000/test/catalog:tag", True),
    ("registry.invalid/test/catalog:tag", False),
])
def test_explicit_oras_push_uses_validated_layout_argument_array_and_caller_config(tmp_path, destination, plain_http):
    output = tmp_path / "layout with spaces"
    config = tmp_path / "caller config.json"
    config.write_bytes(b'{"auths":{}}')
    with patch.object(generate.shutil, "which", return_value="oras"), patch.object(
        generate.subprocess, "run", return_value=subprocess.CompletedProcess(["oras"], 0, b"copied", b""),
    ) as run:
        result = _invoke([
            "oci", "--example", "offline", "--output", output, "--reference", "offline",
            "--page-size", "2", "--push", destination,
            *(["--plain-http"] if plain_http else []), "--registry-config", config,
        ])
    run.assert_called_once_with(
        ["oras", "cp", "--from-oci-layout", *(["--to-plain-http"] if plain_http else []),
         "--to-registry-config", str(config), "--", str(output.absolute()) + ":offline", destination],
        input=None, env=None, capture_output=True, timeout=300,
    )
    assert result["pin"] == "sha256:c937f902c54ca9c63e510bab3b4ec07ec3775ad338ac030ac93d916a736efba6"
    assert result["publication"] == {"destination": destination, "digest": result["pin"]}
    assert oci.FixtureLayout(output, "offline").validate()["objects"] == 99
    assert config.read_bytes() == b'{"auths":{}}'


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


def test_push_validates_corrupted_layout_before_oras(generated_examples, tmp_path):
    original, _ = generated_examples["offline", "oci"]
    layout = tmp_path / "copy"
    shutil.copytree(original, layout)
    digest = hashlib.sha256(b"\x00\x01\x7f\x80\xff\r\n").hexdigest()
    (layout / "blobs/sha256" / digest).write_bytes(b"corrupted")
    with patch.object(generate.shutil, "which", return_value="oras"), patch.object(
        generate.subprocess, "run", side_effect=AssertionError("Corrupt content must not be pushed"),
    ) as run:
        with pytest.raises(federation.FederationError) as failure:
            generate.push_layout(layout, "snapshot", "registry.invalid/test/catalog:tag")
    assert failure.value.code == "integrity_error"
    run.assert_not_called()


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
