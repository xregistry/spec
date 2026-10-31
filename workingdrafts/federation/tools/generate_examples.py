"""Generate File, Git and OCI representations of the shared Registry examples."""

import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import urlsplit

from workingdrafts.bindings.tools import mapping_examples as mapping
from workingdrafts.bindings.tools import oci_examples as oci
from workingdrafts.federation.tools.federation_examples import (
    EXAMPLE_SOURCE, FederationError, load_example, load_examples,
)


ROOT = Path(__file__).resolve().parents[3]
GIT_PATH = "xregistry"
GIT_REF = "refs/heads/main"
GIT_TAG = "refs/tags/snapshot"


def _tool(name):
    executable = shutil.which(name)
    if executable is None:
        raise FederationError("unavailable", f"Required executable not found: {name}")
    return executable


def _run(command, *, data=None, env=None, timeout=30):
    try:
        result = subprocess.run(
            command, input=data, env=env, capture_output=True, timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise FederationError("unavailable", f"{Path(command[0]).name} could not complete: {error}") from error
    if result.returncode:
        diagnostic = result.stderr.decode("utf-8", errors="replace").strip()
        diagnostic = re.sub(
            r"([A-Za-z][A-Za-z0-9+.-]*://)[^/@\s]+@", r"\1[redacted]@", diagnostic,
        )
        raise FederationError(
            "unavailable", f"{Path(command[0]).name} exited {result.returncode}: {diagnostic[:1000]}",
        )
    return result.stdout


def _destination(value):
    path = Path(value).absolute()
    existing = path
    while not existing.exists() and not existing.is_symlink():
        existing = existing.parent
    mapping._checked_path(existing, directory=True)
    path = path.resolve()
    if path == ROOT or ROOT in path.parents or path in ROOT.parents or path == path.parent:
        raise FederationError("policy_denied", "Output must be outside the source checkout and not a filesystem root")
    if path.exists():
        mapping._checked_path(path, directory=True)
        if any(path.iterdir()):
            raise FederationError("policy_denied", "Output directory must be empty")
    return path


def _write_files(root, files):
    root.mkdir(parents=True, exist_ok=True)
    mapping._checked_path(root, directory=True)
    for name, data in sorted(files.items()):
        mapping._storage_name(name)
        path = root.joinpath(*name.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        mapping._checked_path(path.parent, directory=True)
        with path.open("xb") as output:
            output.write(data)


def build_file(example, output, *, name=None, inline=False):
    files = mapping.example_tree(example, name, inline=inline)
    root = _destination(output)
    _write_files(root, files)
    summary = mapping.DocumentTree(mapping.FileStore(root)).validate()
    return {"output": str(root), "root": str(root / "registry.json"), "pin": summary["rootsha256"]}


def _git_environment():
    environment = {
        key: value for key, value in os.environ.items()
        if not key.upper().startswith("GIT_")
    }
    environment.update({
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_AUTHOR_NAME": "xRegistry example", "GIT_COMMITTER_NAME": "xRegistry example",
        "GIT_AUTHOR_EMAIL": "example@example.invalid", "GIT_COMMITTER_EMAIL": "example@example.invalid",
        "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+00:00",
        "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+00:00",
    })
    return environment


def build_git(example, output, *, name=None, inline=False):
    files = mapping.example_tree(example, name, inline=inline)
    root = _destination(output)
    executable = _tool("git")
    environment = _git_environment()

    def git(*args, data=None):
        return _run(
            [executable, "--no-pager", "--git-dir=" + str(root),
             "-c", "core.autocrlf=false", "-c", "commit.gpgsign=false",
             "-c", "tag.gpgsign=false", *args],
            data=data, env=environment,
        ).strip().decode("ascii")

    root.parent.mkdir(parents=True, exist_ok=True)
    mapping._checked_path(root.parent, directory=True)
    _run(
        [executable, "init", "--bare", "--quiet", "--template=", "--object-format=sha1",
         "--initial-branch=main", str(root)], env=environment,
    )
    tree = {}
    for path, data in files.items():
        node = tree.setdefault(GIT_PATH, {})
        parts = path.split("/")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = data

    def store(node):
        entries = []
        for key, value in node.items():
            if isinstance(value, dict):
                mode, kind, oid = "040000", "tree", store(value)
            else:
                mode, kind, oid = "100644", "blob", git("hash-object", "-w", "--stdin", data=value)
            entries.append(f"{mode} {kind} {oid}\t{key}\n")
        return git("mktree", data="".join(sorted(entries)).encode("utf-8"))

    commit = git("commit-tree", store(tree), data=b"Registry example snapshot\n")
    git("update-ref", GIT_REF, commit)
    tag = git("mktag", data=(
        f"object {commit}\ntype commit\ntag snapshot\n"
        "tagger xRegistry example <example@example.invalid> 946684800 +0000\n\n"
        "Registry example snapshot\n"
    ).encode("ascii"))
    git("update-ref", GIT_TAG, tag)
    for revision in (commit, GIT_TAG):
        reader = mapping.DocumentTree(mapping.GitStore(root, revision, GIT_PATH))
        reader.validate()
        if reader.store.pin != commit:
            raise FederationError("integrity_error", "Generated Git tag does not select the snapshot commit")
    return {"output": str(root), "root": GIT_PATH, "pin": commit, "revision": GIT_REF, "tag": GIT_TAG}


def _push_target(value, plain_http=False):
    if not isinstance(value, str) or "://" in value or "@" in value or any(c.isspace() for c in value):
        raise FederationError("invalid_package", "Push needs registry/repository:tag without credentials")
    host, separator, target = value.partition("/")
    repository, tag_separator, tag = target.rpartition(":")
    if not separator or not tag_separator or not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}", tag):
        raise FederationError("invalid_package", "Push needs registry/repository:tag")
    if not re.fullmatch(r"[a-z0-9]+(?:(?:[._]|__|[-]+)[a-z0-9]+)*(?:/[a-z0-9]+(?:(?:[._]|__|[-]+)[a-z0-9]+)*)*", repository):
        raise FederationError("invalid_package", "Invalid Distribution repository")
    try:
        uri = urlsplit("https://" + host)
        uri.port
    except ValueError as error:
        raise FederationError("invalid_package", "Invalid registry authority") from error
    if (
        not uri.hostname or uri.username is not None or uri.password is not None
        or uri.query or uri.fragment or uri.path
        or re.fullmatch(r"(?:[A-Za-z0-9][A-Za-z0-9.-]*|\[[0-9A-Fa-f:]+\])(?::[0-9]+)?", host) is None
    ):
        raise FederationError("invalid_package", "Invalid registry authority")
    if plain_http:
        try:
            loopback = ipaddress.ip_address(uri.hostname).is_loopback
        except ValueError:
            loopback = uri.hostname == "localhost"
        if not loopback:
            raise FederationError("policy_denied", "Plain HTTP is restricted to loopback registries")
    return value


def push_layout(layout, reference, destination, *, plain_http=False, registry_config=None):
    _push_target(destination, plain_http)
    executable = _tool("oras")
    reader = oci.FixtureLayout(layout, reference)
    reader.validate()
    command = [executable, "cp", "--from-oci-layout"]
    if plain_http:
        command.append("--to-plain-http")
    if registry_config is not None:
        command.extend(["--to-registry-config", str(registry_config)])
    command.extend(["--", str(Path(layout).absolute()) + ":" + reference, destination])
    _run(command, timeout=300)
    return {"destination": destination, "digest": reader.root_digest}


def build_oci(example, output, *, reference="snapshot", page_size=oci.MAX_DESCRIPTORS,
              push=None, plain_http=False, registry_config=None):
    records, documents = oci.example_records(example)
    root = _destination(output)
    if push is not None:
        _push_target(push, plain_http)
        _tool("oras")
    elif plain_http or registry_config is not None:
        raise FederationError("invalid_package", "Registry options require --push")
    descriptor = oci.build_layout(root, records, documents, reference=reference, page_size=page_size)
    oci.FixtureLayout(root, reference).validate()
    (root / ".gitattributes").write_bytes(b"index.json text eol=lf\noci-layout text eol=lf\nblobs/** -text\n")
    result = {"output": str(root), "root": str(root / "index.json"),
              "pin": descriptor["digest"], "reference": reference}
    if push is not None:
        result["publication"] = push_layout(
            root, reference, push, plain_http=plain_http, registry_config=registry_config,
        )
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="binding", required=True)
    for binding in ("file", "git", "oci", "validate"):
        command = commands.add_parser(binding)
        command.add_argument("--input", type=Path, default=EXAMPLE_SOURCE)
        if binding == "validate":
            continue
        command.add_argument("--example", required=True, help="Named example in the input document")
        command.add_argument("--output", required=True, type=Path, help="New or empty directory outside this checkout")
        if binding != "oci":
            command.add_argument(
                "--inline", action="store_true",
                help="Store every record and index inline in registry.json (the walkthrough always is)",
            )
        if binding == "oci":
            command.add_argument("--reference", default="snapshot")
            command.add_argument("--page-size", type=int, default=oci.MAX_DESCRIPTORS)
            command.add_argument("--push", metavar="REGISTRY/REPOSITORY:TAG")
            command.add_argument("--plain-http", action="store_true", help="Loopback registry only")
            command.add_argument("--registry-config", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.binding == "validate":
            result = {"examples": {}}
            for name, example in load_examples(args.input).items():
                files = mapping.example_tree(example, name)
                records, documents = oci.example_records(example)
                result["examples"][name] = {
                    "records": len(records), "documents": len(documents),
                    "mapping_files": len(files),
                }
        else:
            example = load_example(args.example, args.input)
            # Both adapters validate before any output is published.
            oci.example_records(example)
            mapping.encode_tree(*mapping.example_records(example))
            if args.binding == "oci":
                result = build_oci(
                    example, args.output, reference=args.reference, page_size=args.page_size,
                    push=args.push, plain_http=args.plain_http, registry_config=args.registry_config,
                )
            else:
                result = (build_file if args.binding == "file" else build_git)(
                    example, args.output, name=args.example, inline=args.inline,
                )
            result.update(example=args.example, binding=args.binding)
        print(json.dumps(result, indent=2))
        return 0
    except FederationError as error:
        print(json.dumps({"error": error.code, "message": str(error)}), file=sys.stderr)
    except OSError as error:
        print(json.dumps({"error": "unavailable", "message": str(error)}), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
