"""Build checked descriptors around the independently authored sample inputs."""

import hashlib
import json
from pathlib import Path


SAMPLES = Path(__file__).resolve().parents[1] / "samples"
ROOT = "https://content.example.test/"


def write(name, value):
    path = SAMPLES / name
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")


def descriptor(name):
    raw = (SAMPLES / name).read_bytes()
    return {
        "url": ROOT + name,
        "digest": "sha256:" + hashlib.sha256(raw).hexdigest(),
        "size": len(raw),
    }


def build():
    manifest = {
        "format": "xregistry-publication/1",
        "scope": "urn:example:manual-publication",
        "capture": "assembled",
        "completeness": "offline-complete",
        "registry": descriptor("registry.json"),
        "documents": [{
            "viewVersion": "/sets/manual/documents/intro/versions/7",
            "originRegistry": "https://author.example.test/registry",
            "originVersion": "/sets/manual/documents/intro/versions/7",
            "base": "https://author.example.test/manual/intro.txt",
            "content": descriptor("intro.txt"),
        }],
    }
    write("manifest.json", manifest)
    head = descriptor("manifest.json")
    write("channel.json", {"scope": manifest["scope"], "epoch": 12, "head": head})
    context = {
        "format": "xregistry-open/1",
        "scope": manifest["scope"],
        "snapshot": head,
        "registry": manifest["registry"],
        "completeness": manifest["completeness"],
        "channel": {
            "url": "https://publisher.example.test/publications/team/channels/stable",
            "epoch": 12,
        },
    }
    write("open.json", context)
    write("publication-package.json", {
        "format": "xregistry-publication-package/1",
        "context": context,
        "objects": {ROOT + name: name for name in ("manifest.json", "registry.json", "intro.txt")},
    })


if __name__ == "__main__":
    build()
