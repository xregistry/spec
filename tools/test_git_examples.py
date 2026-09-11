"""Real Git object tests; all writes stay in pytest's temporary bare stores."""

import hashlib
import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

import mapping_examples as document
from federation_examples import FederationError


class GitFixture:
    def __init__(self, path, algorithm="sha1"):
        self.path = path
        self.environment = {
            k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")
        }
        self.environment.update({
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_AUTHOR_NAME": "Fixture", "GIT_COMMITTER_NAME": "Fixture",
            "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
            "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
            "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+00:00",
            "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+00:00",
        })
        result = subprocess.run(
            ["git", "init", "--bare", "--quiet", "--object-format=" + algorithm, str(path)],
            env=self.environment, capture_output=True, timeout=30,
        )
        assert result.returncode == 0, result.stderr
        self.objects = {}

    def run(self, *args, data=None):
        result = subprocess.run(
            ["git", "--no-pager", "--git-dir=" + str(self.path), *args],
            env=self.environment, input=data, capture_output=True, timeout=30,
        )
        assert result.returncode == 0, result.stderr
        return result.stdout.strip().decode("ascii")

    def blob(self, data):
        if data not in self.objects:
            self.objects[data] = self.run("hash-object", "-w", "--stdin", data=data)
        return self.objects[data]

    def commit(self, files, *, prefix="xregistry", ref="refs/heads/main"):
        tree = {}
        for name, value in files.items():
            parts = ([prefix] if prefix else []) + name.split("/")
            parts = [segment for part in parts for segment in part.split("/")]
            node = tree
            for segment in parts[:-1]:
                node = node.setdefault(segment, {})
            node[parts[-1]] = value

        def store(node):
            entries = []
            for name, value in node.items():
                if isinstance(value, dict):
                    mode, kind, oid = "040000", "tree", store(value)
                elif isinstance(value, tuple):
                    mode, oid = value
                    kind = "commit" if mode == "160000" else "blob"
                else:
                    mode, kind, oid = "100644", "blob", self.blob(value)
                entries.append(f"{mode} {kind} {oid}\t{name}\n")
            return self.run("mktree", "--missing", data="".join(sorted(entries)).encode("utf-8"))

        root = store(tree)
        commit = self.run("commit-tree", root, data=b"fixture snapshot\n")
        self.run("update-ref", ref, commit)
        return commit


@pytest.fixture(scope="module", params=["sha1", "sha256"])
def stored_fixture(tmp_path_factory, request):
    git = GitFixture(tmp_path_factory.mktemp("git-" + request.param) / "repo.git", request.param)
    files = document.encode_tree(*document.sample_records())
    oid = git.commit(files)
    return git, files, oid, request.param


def test_git_document_tree_reads_real_objects_without_checkout(stored_fixture):
    git, files, oid, algorithm = stored_fixture
    real_run = subprocess.run
    with patch.object(document.subprocess, "run", wraps=real_run) as calls:
        store = document.GitStore(git.path, "refs/heads/main")
        tree = document.DocumentTree(store)
        assert tree.document("/documents/main/assets/item") == b'{"hello":"world"}\n'
        assert tree.document("/documents/main/assets/item/versions/v2") == b""
        assert tree.document("/documents/main/assets/CON") == b"\x00\x01\xff\x7f\n"
    assert store.pin == oid
    assert len(oid) == (40 if algorithm == "sha1" else 64)
    assert tree.metadata("/documents/main/assets/item")["entity"]["meta"]["defaultversionid"] == "v1"
    assert not (git.path / "xregistry").exists()
    assert (git.path / "HEAD").exists()
    for call in calls.call_args_list:
        command = call.args[0]
        assert not {"checkout", "clone", "fetch", "reset", "submodule"} & set(command)
        assert "protocol.allow=never" in command
        assert call.kwargs["env"]["GIT_NO_LAZY_FETCH"] == "1"
        assert call.kwargs["env"]["GIT_NO_REPLACE_OBJECTS"] == "1"
    assert store.read("documents/n1.bin") == files["documents/n1.bin"]
    raw = files["documents/n1.bin"]
    git_oid = hashlib.new(algorithm, b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    assert git_oid in store.object_reads
    assert git_oid != hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize("algorithm", ["sha1", "sha256"])
def test_git_revision_resolves_once_and_pins_object_reads(tmp_path, algorithm):
    git = GitFixture(tmp_path / "repo.git", algorithm)
    first = git.commit({"registry.json": b"first\r\n", "documents/n0.bin": b"\x00\xff"})
    pinned = document.GitStore(git.path, "refs/heads/main")
    second = git.commit({"registry.json": b"second\n", "documents/n0.bin": b"changed"})
    assert first != second
    assert pinned.read("registry.json") == b"first\r\n"
    assert pinned.read("documents/n0.bin") == b"\x00\xff"
    assert pinned.pin == first
    fresh = document.GitStore(git.path, "refs/heads/main")
    assert fresh.pin == second
    assert fresh.read("registry.json") == b"second\n"


def test_git_annotated_tag_peels_to_commit_and_accepts_complete_oid(stored_fixture):
    git, _, oid, _ = stored_fixture
    git.run("tag", "--annotate", "release", oid, "-m", "fixture release")
    tag_oid = git.run("rev-parse", "refs/tags/release")
    assert tag_oid != oid
    reader = document.GitStore(git.path, "refs/tags/release")
    assert reader.pin == oid
    assert tag_oid in reader.object_reads
    assert document.GitStore(git.path, oid.upper()).pin == oid


@pytest.mark.parametrize("prefix", ["", "xregistry", "catalog/snapshots"])
def test_git_path_selects_document_tree_root(tmp_path, prefix):
    git = GitFixture(tmp_path / "repo.git")
    oid = git.commit({"registry.json": b"stored bytes\r\n"}, prefix=prefix)
    reader = document.GitStore(git.path, oid, path=prefix)
    assert reader.read("registry.json") == b"stored bytes\r\n"
    assert reader.path == prefix
    assert reader.pin == oid


@pytest.mark.parametrize("name,code", [
    ("registry.json", "not_found"), ("records/n0.json", "invalid_package"),
])
def test_git_missing_entries_are_not_empty(tmp_path, name, code):
    git = GitFixture(tmp_path / "repo.git")
    git.commit({"records/n1.json": b"valid other entry"})
    reader = document.GitStore(git.path, "refs/heads/main")
    with pytest.raises(FederationError) as error:
        reader.read(name)
    assert error.value.code == code
    assert name not in reader.reads


def test_git_missing_pinned_blob_is_inconsistent_snapshot(tmp_path):
    git = GitFixture(tmp_path / "repo.git")
    data = b"content that disappears"
    git.commit({"registry.json": data})
    reader = document.GitStore(git.path, "refs/heads/main")
    oid = git.objects[data]
    loose = git.path / "objects" / oid[:2] / oid[2:]
    assert loose.is_file()
    loose.chmod(0o600)
    loose.unlink()
    with pytest.raises(FederationError) as error:
        reader.read("registry.json")
    assert error.value.code == "inconsistent_snapshot"
    assert reader.reads == []


@pytest.mark.parametrize("mode,code", [
    ("120000", "policy_denied"), ("160000", "unsupported_operation"),
])
def test_git_rejects_symlink_and_submodule_indirections(tmp_path, mode, code):
    git = GitFixture(tmp_path / "repo.git")
    oid = git.blob(b"../../outside") if mode == "120000" else "1" * 40
    git.commit({"registry.json": (mode, oid)})
    reader = document.GitStore(git.path, "refs/heads/main")
    with pytest.raises(FederationError) as error:
        reader.read("registry.json")
    assert error.value.code == code
    assert reader.reads == []


@pytest.mark.parametrize("ending", [b"", b"\n", b"\r\n"])
def test_git_rejects_lfs_pointer_without_smudge(tmp_path, ending):
    git = GitFixture(tmp_path / "repo.git")
    pointer = b"version https://git-lfs.github.com/spec/v1" + ending
    git.commit({"registry.json": pointer})
    reader = document.GitStore(git.path, "refs/heads/main")
    with pytest.raises(FederationError) as error:
        reader.read("registry.json")
    assert error.value.code == "unsupported_operation"
    assert str(error.value) == "Git LFS pointer unsupported"
    assert reader.reads == []


def test_git_unrelated_indirections_do_not_invalidate_selected_root(tmp_path):
    git = GitFixture(tmp_path / "repo.git")
    git.commit({
        "xregistry/registry.json": b"selected",
        "unrelated-submodule": ("160000", "1" * 40),
        "unrelated-lfs": b"version https://git-lfs.github.com/spec/v1\n",
    }, prefix="")
    reader = document.GitStore(git.path, "refs/heads/main")
    assert reader.read("registry.json") == b"selected"
    assert reader.reads == ["registry.json"]


def test_git_missing_initial_revision_does_not_fallback(tmp_path):
    git = GitFixture(tmp_path / "repo.git")
    git.commit({"registry.json": b"present"})
    with pytest.raises(FederationError) as error:
        document.GitStore(git.path, "refs/heads/absent")
    assert error.value.code == "not_found"
