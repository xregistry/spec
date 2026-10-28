"""Build checked descriptors around the independently authored sample inputs."""

import hashlib
import json
from pathlib import Path
import re


SAMPLES = Path(__file__).resolve().parents[1] / "samples"
HTTP = {"name": "http", "endpoint": "https://publisher.example.test"}
OPCUA = {
    "name": "opcua",
    "endpoint": "opc.tcp://ua.example.test:4840",
    "parameters": {"registryroot": "nsu=urn:example:publication;s=Registry"},
}


def write(name, value):
    path = SAMPLES / name
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")


def descriptor(name, access, version):
    raw = (SAMPLES / name).read_bytes()
    return {
        "reference": {"registry": access, "version": version},
        "digest": "sha256:" + hashlib.sha256(raw).hexdigest(),
        "size": len(raw),
    }


def build_view(access, prefix=""):
    manifest = {
        "format": "xregistry-publication/1",
        "scope": "urn:example:manual-publication",
        "capture": "assembled",
        "completeness": "offline-complete",
        "registry": descriptor(
            "registry.json", access,
            "/publications/team/objects/registry-capture/versions/content",
        ),
        "documents": [{
            "viewVersion": "/sets/manual/documents/intro/versions/7",
            "originRegistry": "https://author.example.test/registry",
            "originVersion": "/sets/manual/documents/intro/versions/7",
            "base": "https://author.example.test/manual/intro.txt",
            "content": descriptor(
                "intro.txt", access, "/sets/manual/documents/intro/versions/7",
            ),
        }],
    }
    manifest_name = prefix + "manifest.json"
    write(manifest_name, manifest)
    digest = hashlib.sha256((SAMPLES / manifest_name).read_bytes()).hexdigest()
    head = descriptor(
        manifest_name, access,
        f"/publications/team/snapshots/{digest}/versions/manifest",
    )
    write(prefix + "channel.json", {"scope": manifest["scope"], "epoch": 12, "head": head})
    context = {
        "format": "xregistry-open/1",
        "scope": manifest["scope"],
        "snapshot": head,
        "registry": manifest["registry"],
        "completeness": manifest["completeness"],
        "channel": {
            "reference": {
                "registry": access,
                "resource": "/publications/team/channels/stable",
            },
            "epoch": 12,
        },
    }
    write(prefix + "open.json", context)
    return context, [
        {"reference": head["reference"], "path": manifest_name},
        {"reference": manifest["registry"]["reference"], "path": "registry.json"},
        {"reference": manifest["documents"][0]["content"]["reference"], "path": "intro.txt"},
    ]


def build():
    context, objects = build_view(HTTP)
    _, native_objects = build_view(OPCUA, "opcua-")
    write("publication-package.json", {
        "format": "xregistry-publication-package/1",
        "context": context,
        "objects": objects + native_objects,
    })
    spec = SAMPLES.parent / "spec.md"
    newline = "\r\n" if b"\r\n" in spec.read_bytes() else "\n"

    def example(match):
        value = json.loads(match[1])
        filename = {
            "xregistry-publication/1": "manifest.json",
            "xregistry-open/1": "open.json",
        }.get(value.get("format"))
        if set(value) == {"scope", "epoch", "head"}:
            filename = "channel.json"
        if filename is None:
            return match[0]
        return "```json\n" + (SAMPLES / filename).read_text(encoding="utf-8").rstrip() + "\n```"

    spec.write_text(
        re.sub(r"```json\n(.*?)\n```", example, spec.read_text(encoding="utf-8"), flags=re.S),
        encoding="utf-8", newline=newline,
    )


if __name__ == "__main__":
    build()
