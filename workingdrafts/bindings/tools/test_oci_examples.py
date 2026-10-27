"""Offline conformance tests for the native OCI snapshot fixture APIs."""

import copy
import base64
import hashlib
import json
from collections import Counter
from pathlib import Path
from unittest.mock import Mock, call, patch

import pytest
from jsonschema import Draft7Validator, Draft202012Validator, FormatChecker

from workingdrafts.bindings.tools import oci_examples as oci
from workingdrafts.bindings.tools.mapping_examples import (
    DocumentTree, MemoryStore, encode_tree,
    sample_records as document_sample_records,
)
from workingdrafts.federation.tools.federation_examples import FederationError, load_example


ROOT = Path(__file__).resolve().parents[3]
SCHEMAS = ROOT / "workingdrafts" / "bindings" / "schemas"
INDEX = "application/vnd.oci.image.index.v1+json"
MANIFEST = "application/vnd.oci.image.manifest.v1+json"
CONFIG = "application/vnd.xregistry.entity.v1+json"
DOCUMENT = "application/vnd.xregistry.document.v1"
EMPTY = "application/vnd.oci.empty.v1+json"
PREFIX = "io.xregistry.oci."


@pytest.mark.parametrize("name", ["offline", "linked"])
def test_neutral_oci_adapter_preserves_document_modes_full_model_and_input(name):
    example = load_example(name)
    before = copy.deepcopy(example)
    records, documents = oci.example_records(example)
    indexed = {record["entity"]["xid"]: record for record in records}
    assert indexed["/"]["entity"]["registryid"] == "fixture-" + name
    assert indexed["/"]["snapshot"] == ("linked" if name == "linked" else "offline-complete")
    assert indexed["/"]["entity"]["model"]["groups"]["dirs"]["resources"]["files"]["metaattributes"]["xref"]["type"] == "xid"
    assert indexed["/"]["modelresolved"]["groups"]["imports"]["ximportresources"] == ["/dirs/files"]
    assert indexed["/dirs/main/notes/info/versions/v1"]["document"]["mode"] == "metadata-only"
    second = indexed["/dirs/main/files/sample/versions/v2"]
    assert second["document"]["mode"] == ("external" if name == "linked" else "embedded")
    assert documents["/dirs/main/files/binary/versions/v1"] == b"\x00\x01\x7f\x80\xff\r\n"
    assert documents["/dirs/main/files/empty/versions/v1"] == b""
    if name == "linked":
        assert second["entity"]["fileurl"] == "https://documents.example.org/sample-v2.json"
        assert "/dirs/main/files/sample/versions/v2" not in documents
    else:
        assert documents["/dirs/main/files/sample/versions/v2"] == b'{"type":"number"}\n'
    indexed["/"]["entity"]["registryid"] = "mutated"
    documents["/dirs/main/files/binary/versions/v1"] = b"mutated"
    assert example == before


def test_generated_legacy_oci_replaces_all_115_blobs_byte_for_byte(oci_sample_root):
    layout = oci_sample_root / "layout"
    blobs = {path.name: path.read_bytes() for path in (layout / "blobs" / "sha256").iterdir()}
    assert len(blobs) == 115
    assert set(blobs) == set(LEGACY_BLOB_HASHES)
    for digest, data in blobs.items():
        assert hashlib.sha256(data).hexdigest() == digest
    for reference, expected in LEGACY_EXPECTED["roots"].items():
        reader = oci.FixtureLayout(layout, reference)
        summary = reader.validate()
        assert reader.root_digest == expected["digest"]
        assert reader.lookup("/")["value"]["registryid"] == expected["registryid"]
        assert len(blobs[expected["digest"].removeprefix("sha256:")]) == expected["size"]
        for field in ("snapshot", "objects", "indexes", "manifests", "records", "documents"):
            assert summary[field] == expected[field]
    offline = oci.FixtureLayout(layout, "offline")
    for expected in LEGACY_EXPECTED["documents"]:
        result = offline.lookup(expected["xid"], operation="document")
        assert result["data"] == base64.b64decode(expected["base64"], validate=True)
        assert len(result["data"]) == expected["size"]
        assert "sha256:" + hashlib.sha256(result["data"]).hexdigest() == expected["digest"]


ITEM = "/documents/main/assets/item"
V1 = ITEM + "/versions/v1"
V2 = ITEM + "/versions/v2"
BINARY = "/documents/main/assets/CON/versions/a:b@c."
NOTES = "/documents/main/notes/item"
CATALOG = "/categories/main/registries/site"
MIRRORS = "/mirrors/local/assets"
STAMP = {
    "epoch": 1,
    "createdat": "2026-09-04T00:00:00Z",
    "modifiedat": "2026-09-04T00:00:00Z",
}
EXTRA = {
    "mode": "KeepCase",
    "values": [0, False, ""],
    "nested": {"self": "extension data", "shortself": "keep this"},
}
MODEL_SOURCE = {
    "attributes": {"fixture": {"type": "string"}},
    "groups": {
        "categories": {
            "singular": "category",
            "resources": {
                "registries": {
                    "singular": "registry",
                    "hasdocument": False,
                    "attributes": {"weburl": {"type": "url"}},
                }
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
# Graph-unit input expands only Resource imports. The separately published
# fixture and cross-format test carry the complete Core metadata model.
MODEL = {
    "attributes": {"fixture": {"type": "string"}},
    "groups": {
        "categories": copy.deepcopy(MODEL_SOURCE["groups"]["categories"]),
        "documents": copy.deepcopy(MODEL_SOURCE["groups"]["documents"]),
        "independent": copy.deepcopy(MODEL_SOURCE["groups"]["independent"]),
        "mirrors": {
            "singular": "mirror",
            "resources": {
                "assets": {
                    "singular": "asset",
                    "attributes": {"purpose": {"type": "string"}},
                }
            },
        },
    },
}
CAPABILITIES = {
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
REGISTRY_ENTITY = {
    **STAMP,
    "xid": "/",
    "registryid": "first",
    "specversion": "1.0-rc4",
    "fixture": "document-tree",
    "modelsource": MODEL_SOURCE,
    "model": MODEL,
    "capabilities": CAPABILITIES,
}
VERSION_ENTITIES = {
    V1: {
        **STAMP,
        "xid": V1,
        "assetid": "item",
        "versionid": "v1",
        "isdefault": True,
        "ancestorid": "v1",
        "labels": {"stage": "production", "note": ""},
        "contenttype": "application/json",
        "purpose": "primary",
    },
    V2: {
        **STAMP,
        "xid": V2,
        "assetid": "item",
        "versionid": "v2",
        "isdefault": False,
        "ancestorid": "v1",
        "labels": {"stage": "development"},
        "contenttype": "application/octet-stream",
        "purpose": "empty",
    },
    BINARY: {
        **STAMP,
        "xid": BINARY,
        "assetid": "CON",
        "versionid": "a:b@c.",
        "isdefault": True,
        "ancestorid": "a:b@c.",
        "contenttype": "application/octet-stream",
    },
    NOTES + "/versions/v1": {
        **STAMP,
        "xid": NOTES + "/versions/v1",
        "noteid": "item",
        "versionid": "v1",
        "isdefault": True,
        "ancestorid": "v1",
        "labels": {"note": ""},
    },
    CATALOG + "/versions/v1": {
        **STAMP,
        "xid": CATALOG + "/versions/v1",
        "registryid": "site",
        "versionid": "v1",
        "isdefault": True,
        "ancestorid": "v1",
        "weburl": "https://example.com/cataloged-registry",
    },
}
BASE_BYTES = {
    V1: b'{"hello":"world"}\n',
    V2: b"",
    BINARY: b"\x00\x01\xff\x7f\n",
}
BYTE_STATES = {
    V1: (
        b' { "value": 1 }\r\n',
        17,
        "c23110513472a63bd0ab22e37d6f9cdb95807fe31caad2f37d3abfde2ee7eec6",
    ),
    V2: (
        b"",
        0,
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    ),
    BINARY: (
        b"\x00\xff\x10\r\n",
        5,
        "1151e4df6045153a472d1444fa216651a6c8bd93002410147de4ad3a4399ee0c",
    ),
    ITEM + "/versions/v10": (
        b"{}",
        2,
        "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a",
    ),
    ITEM + "/versions/v11": (
        b"null",
        4,
        "74234e98afe7498fb5daf1f36ac2d78acc339464f950703b8c019892f982b90b",
    ),
}
RANGE_IDS = ("a", "k", "l", "m", "n", "z", "zz")


def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _digest(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _error(action, code, message):
    with pytest.raises(FederationError) as caught:
        action()
    assert caught.value.code == code
    assert str(caught.value) == message
    return caught.value


def _schema_error(action, filename, location="/"):
    with pytest.raises(FederationError) as caught:
        action()
    assert caught.value.code == "invalid_package"
    assert str(caught.value).startswith(f"{filename} at {location}: ")
    return caught.value


def _record(records, xid):
    return next(record for record in records if record["entity"]["xid"] == xid)


def _blob_path(path, descriptor):
    return path / "blobs" / "sha256" / descriptor["digest"][7:]


def _write_blob(path, data, media_type, artifact=None):
    descriptor = {"digest": _digest(data), "size": len(data), "mediaType": media_type}
    if artifact is not None:
        descriptor["artifactType"] = artifact
    target = _blob_path(path, descriptor)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return descriptor


def _standard_edges(node):
    if node["mediaType"] == INDEX:
        return node["manifests"]
    return [node["config"], *node["layers"]]


def _graph(path, reference="snapshot"):
    """Independent byte/edge oracle, not a substitute for FixtureLayout.validate."""
    head = json.loads((path / "index.json").read_bytes())
    root = next(
        edge for edge in head["manifests"]
        if edge.get("annotations", {}).get("org.opencontainers.image.ref.name") == reference
    )
    objects = {}
    nodes = {}
    edges = []

    def inspect(descriptor):
        raw = _blob_path(path, descriptor).read_bytes()
        assert len(raw) == descriptor["size"]
        assert _digest(raw) == descriptor["digest"]
        edges.append(copy.deepcopy(descriptor))
        if descriptor["digest"] in objects:
            return
        objects[descriptor["digest"]] = (copy.deepcopy(descriptor), raw)
        if descriptor["mediaType"] not in (INDEX, MANIFEST):
            return
        node = json.loads(raw)
        annotations = node["annotations"]
        key = (
            node["mediaType"], annotations[PREFIX + "kind"],
            annotations[PREFIX + "xid"], annotations.get(PREFIX + "lower", ""),
            annotations.get(PREFIX + "upper", ""),
        )
        assert key not in nodes
        nodes[key] = (copy.deepcopy(descriptor), node)
        for child in _standard_edges(node):
            inspect(child)

    inspect(root)
    return {"path": path, "root": root, "objects": objects, "nodes": nodes, "edges": edges}


def _node(graph, kind, xid, media=INDEX, lower="", upper=""):
    return graph["nodes"][(media, kind, _fixture_routing_key(xid), lower, upper)]


def _fixture_routing_key(xid):
    # These independently authored fixture IDs contain only literal ASCII Core characters.
    return xid.replace(":", "%3A").replace("@", "%40")


def _index(graph, kind, xid, lower="", upper=""):
    return _node(graph, kind, xid, INDEX, lower, upper)[0]


def _metadata_pair(graph, kind, xid):
    descriptor, node = _node(graph, kind, xid, MANIFEST)
    return [descriptor, node["config"]]


def _document_edge(graph, xid):
    return _node(graph, "version", xid, MANIFEST)[1]["layers"][0]


def _resource_path(graph, xid, *, sharded=False):
    parts = xid.strip("/").split("/")
    group_collection = "/" + parts[0]
    group = "/" + "/".join(parts[:2])
    collection = "/" + "/".join(parts[:3])
    result = [
        graph["root"], *_metadata_pair(graph, "registry", "/"),
        _index(graph, "collections", "/"),
    ]
    if sharded:
        result.append(_index(graph, "collections", "/", "", "/independent"))
    result.extend([
        _index(graph, "collection", group_collection),
        _index(graph, "group", group),
        _index(graph, "collections", group),
        _index(graph, "collection", collection),
        _index(graph, "resource", xid),
    ])
    return result


def _version_trace(graph, xid, *, operation="document", ranges=(), sharded=False):
    resource = xid.rsplit("/versions/", 1)[0]
    result = _resource_path(graph, resource, sharded=sharded)
    identity = _metadata_pair(graph, "resource", resource)
    meta = _metadata_pair(graph, "meta", resource + "/meta")
    result.extend(identity + meta if operation == "document" else meta)
    result.extend([
        _index(graph, "collections", resource),
        _index(graph, "collection", resource + "/versions"),
    ])
    result.extend(
        _index(graph, "collection", resource + "/versions", lower, upper)
        for lower, upper in ranges
    )
    if operation == "entity":
        result.extend(identity)
    result.extend(_metadata_pair(graph, "version", xid))
    if operation == "document":
        result.append(_document_edge(graph, xid))
    return result


def _subtree_descriptors(graph, descriptor, *, payloads=False):
    result = [descriptor]
    if descriptor["mediaType"] not in (INDEX, MANIFEST):
        return result
    node = json.loads(graph["objects"][descriptor["digest"]][1])
    children = node["manifests"] if descriptor["mediaType"] == INDEX else [node["config"]]
    if payloads and descriptor["mediaType"] == MANIFEST:
        children += node["layers"]
    for child in children:
        result.extend(_subtree_descriptors(graph, child, payloads=payloads))
    return result


def _expected_trace(path, descriptors):
    result = [
        {"path": name, "route": "layout", "size": len((path / name).read_bytes())}
        for name in ("oci-layout", "index.json")
    ]
    seen = set()
    for descriptor in descriptors:
        digest = descriptor["digest"]
        if digest in seen:
            continue
        seen.add(digest)
        result.append({
            "digest": digest,
            "mediaType": descriptor["mediaType"],
            "size": descriptor["size"],
            "path": f"blobs/sha256/{digest[7:]}",
            "route": "manifests" if descriptor["mediaType"] in (INDEX, MANIFEST) else "blobs",
        })
    return result


def _assert_trace(path, actual, descriptors, read_spy):
    expected = _expected_trace(path, descriptors)
    assert actual == expected
    assert read_spy.call_args_list == [
        call(
            path / entry["path"],
            max_bytes=1_048_576 if (
                entry["path"] == "index.json" or entry.get("mediaType") == INDEX
            ) else None,
        )
        for entry in expected
    ]


def _rewrite_graph(graph, replacements):
    """Corrupt only private fixture bytes and repair their standard ancestors."""
    path = graph["path"]
    rewritten = {}

    def rewrite(edge):
        old_digest = edge["digest"]
        if old_digest not in rewritten:
            raw = replacements.get(old_digest, graph["objects"][old_digest][1])
            if edge["mediaType"] in (INDEX, MANIFEST):
                node = json.loads(raw)
                for child in _standard_edges(node):
                    if child["digest"] in graph["objects"]:
                        replacement = rewrite(child)
                        if replacement["digest"] != child["digest"]:
                            child.update({key: replacement[key] for key in ("digest", "size")})
                raw = _json_bytes(node)
            rewritten[old_digest] = _write_blob(path, raw, edge["mediaType"])
        result = copy.deepcopy(edge)
        result.update({key: rewritten[old_digest][key] for key in ("digest", "size")})
        return result

    root = rewrite(graph["root"])
    head = json.loads((path / "index.json").read_bytes())
    for entry in head["manifests"]:
        if entry["digest"] == graph["root"]["digest"]:
            entry.update({key: root[key] for key in ("digest", "size")})
    (path / "index.json").write_bytes(_json_bytes(head))
    return root


def _edit_node(graph, descriptor, mutate):
    node = json.loads(graph["objects"][descriptor["digest"]][1])
    mutate(node)
    return _rewrite_graph(graph, {descriptor["digest"]: _json_bytes(node)})


def _ordinary_view(xid, id_key, identifier, versions, prefix="", *, default="v1", extra=False):
    meta = {
        **STAMP,
        "xid": xid + "/meta",
        id_key: identifier,
        "readonly": True,
        "defaultversionid": default,
        "defaultversionsticky": True,
        "self": "#" + prefix + "/meta",
        "defaultversionurl": "#" + prefix + "/versions/" + default.replace("~", "~0"),
    }
    if extra and xid == ITEM:
        meta["exampleextension"] = copy.deepcopy(EXTRA)
    return {
        "xid": xid,
        id_key: identifier,
        "self": "#" + prefix,
        "meta": meta,
        "metaurl": "#" + prefix + "/meta",
        "versions": {
            entity["versionid"]: {
                **copy.deepcopy(entity),
                **({"exampleextension": copy.deepcopy(EXTRA)} if extra and entity["xid"] == V1 else {}),
                "self": "#" + prefix + "/versions/" + entity["versionid"].replace("~", "~0"),
            }
            for entity in versions
        },
        "versionscount": len(versions),
        "versionsurl": "#" + prefix + "/versions",
    }


def _item_view(prefix="", *, extra=False):
    return _ordinary_view(
        ITEM, "assetid", "item", [VERSION_ENTITIES[V1], VERSION_ENTITIES[V2]],
        prefix, extra=extra,
    )


def _alias_view(name, prefix=""):
    targets = {
        "copy": ITEM,
        "dangling": "/documents/main/assets/missing",
        "chain": MIRRORS + "/copy",
    }
    xid = MIRRORS + "/" + name
    return {
        "xid": xid,
        "assetid": name,
        "self": "#" + prefix,
        "meta": {
            "xid": xid + "/meta", "assetid": name,
            "xref": targets[name], "self": "#" + prefix + "/meta",
        },
        "metaurl": "#" + prefix + "/meta",
    }


def _documents_view(prefix="", *, extra=False):
    return {
        **STAMP, "xid": "/documents/main", "documentid": "main", "self": "#" + prefix,
        **({"exampleextension": copy.deepcopy(EXTRA)} if extra else {}),
        "assets": {
            "CON": _ordinary_view(
                "/documents/main/assets/CON", "assetid", "CON",
                [VERSION_ENTITIES[BINARY]], prefix + "/assets/CON", default="a:b@c.",
            ),
            "item": _item_view(prefix + "/assets/item", extra=extra),
        },
        "assetscount": 2,
        "assetsurl": "#" + prefix + "/assets",
        "notes": {
            "item": _ordinary_view(
                NOTES, "noteid", "item", [VERSION_ENTITIES[NOTES + "/versions/v1"]],
                prefix + "/notes/item",
            )
        },
        "notescount": 1,
        "notesurl": "#" + prefix + "/notes",
    }


def _registry_view(*, extra=False):
    return {
        **copy.deepcopy(REGISTRY_ENTITY), "self": "#",
        **({"exampleextension": copy.deepcopy(EXTRA)} if extra else {}),
        "categories": {
            "main": {
                **STAMP, "xid": "/categories/main", "categoryid": "main",
                "self": "#/categories/main",
                "registries": {
                    "site": _ordinary_view(
                        CATALOG, "registryid", "site",
                        [VERSION_ENTITIES[CATALOG + "/versions/v1"]],
                        "/categories/main/registries/site",
                    )
                },
                "registriescount": 1,
                "registriesurl": "#/categories/main/registries",
            }
        },
        "categoriescount": 1,
        "categoriesurl": "#/categories",
        "documents": {"main": _documents_view("/documents/main", extra=extra)},
        "documentscount": 1,
        "documentsurl": "#/documents",
        "independent": {
            "MAIN": {
                **STAMP, "xid": "/independent/MAIN", "independentid": "MAIN",
                "self": "#/independent/MAIN", "assets": {}, "assetscount": 0,
                "assetsurl": "#/independent/MAIN/assets",
            }
        },
        "independentcount": 1,
        "independenturl": "#/independent",
        "mirrors": {
            "local": {
                **STAMP, "xid": "/mirrors/local", "mirrorid": "local",
                "self": "#/mirrors/local",
                "assets": {
                    name: _alias_view(name, "/mirrors/local/assets/" + name)
                    for name in ("chain", "copy", "dangling")
                },
                "assetscount": 3, "assetsurl": "#/mirrors/local/assets",
            }
        },
        "mirrorscount": 1,
        "mirrorsurl": "#/mirrors",
    }


@pytest.fixture(scope="module")
def shared_records():
    authored, documents = document_sample_records()
    records = []
    for source in authored:
        record = {
            "formatversion": 1,
            "kind": source["kind"],
            "entity": copy.deepcopy(source["entity"]),
        }
        if source["kind"] == "registry":
            record["snapshot"] = source["snapshot"]["completeness"]
            record["modelresolved"] = copy.deepcopy(source["entity"]["modelsource"])
            record["entity"]["model"] = copy.deepcopy(MODEL)
        elif source["kind"] == "version":
            record["document"] = {
                "mode": "metadata-only" if source.get("document") == {"kind": "none"} else "embedded"
            }
        records.append(record)
    return records, documents


@pytest.fixture(scope="module")
def shared_layout(tmp_path_factory, shared_records):
    path = tmp_path_factory.mktemp("oci-shared")
    oci.build_layout(path, *copy.deepcopy(shared_records))
    return _graph(path)


@pytest.fixture
def private_layout(tmp_path, shared_records):
    oci.build_layout(tmp_path, *copy.deepcopy(shared_records))
    return _graph(tmp_path)


@pytest.fixture(scope="module")
def byte_state_records(shared_records):
    records, documents = copy.deepcopy(shared_records)
    for xid in (V1, V2, BINARY):
        documents[xid] = BYTE_STATES[xid][0]
    for versionid, purpose in (("v10", "object"), ("v11", "null")):
        record = copy.deepcopy(_record(records, V1))
        record["entity"].update({
            "xid": ITEM + "/versions/" + versionid,
            "versionid": versionid,
            "isdefault": False,
            "createdat": "2026-09-05T00:00:00Z",
            "modifiedat": "2026-09-05T00:00:00Z",
            "labels": {"stage": purpose},
            "purpose": purpose,
        })
        records.append(record)
        documents[record["entity"]["xid"]] = BYTE_STATES[record["entity"]["xid"]][0]
    return records, documents


@pytest.fixture(scope="module")
def byte_layout(tmp_path_factory, byte_state_records):
    path = tmp_path_factory.mktemp("oci-byte-states")
    oci.build_layout(path, *copy.deepcopy(byte_state_records))
    return _graph(path)


@pytest.fixture(scope="module")
def extension_layout(tmp_path_factory, shared_records):
    records, documents = copy.deepcopy(shared_records)
    for xid in ("/", "/documents/main", ITEM + "/meta", V1):
        _record(records, xid)["entity"]["exampleextension"] = copy.deepcopy(EXTRA)
    path = tmp_path_factory.mktemp("oci-extensions")
    oci.build_layout(path, records, documents)
    return _graph(path)


def _group_records(names):
    model = {"groups": {"emptygroups": {"singular": "emptygroup"}}}
    registry = {
        "formatversion": 1, "kind": "registry", "snapshot": "offline-complete",
        "modelresolved": copy.deepcopy(model),
        "entity": {
            **STAMP, "xid": "/", "registryid": "bounded",
            "specversion": "1.0-rc4", "model": copy.deepcopy(model),
            "modelsource": copy.deepcopy(model),
            "capabilities": {"available": {"entities": {"mutable": False}}},
        },
    }
    return [registry] + [
        {
            "formatversion": 1, "kind": "group",
            "entity": {**STAMP, "xid": "/emptygroups/" + name, "emptygroupid": name},
        }
        for name in names
    ]


@pytest.fixture(scope="module")
def count_layout(tmp_path_factory):
    path = tmp_path_factory.mktemp("oci-count")
    oci.build_layout(path, _group_records([f"n{i:04d}" for i in range(257)]))
    reader = oci.FixtureLayout(path)
    summary = reader.validate()
    assert summary["records"] == 258
    assert summary["documents"] == 0
    graph = _graph(path)
    graph["members"] = [
        {
            **{key: _index(graph, "group", f"/emptygroups/n{i:04d}")[key]
               for key in ("mediaType", "size", "digest")},
            "annotations": {
                PREFIX + "role": "entity", PREFIX + "xid": f"/emptygroups/n{i:04d}",
            },
        }
        for i in range(257)
    ]
    return graph


def _raw_collection(entries, *, mode="leaf", lower="", upper=""):
    return {
        "schemaVersion": 2,
        "mediaType": INDEX,
        "artifactType": "application/vnd.xregistry.collection.v1+json",
        "annotations": {
            PREFIX + "version": "1", PREFIX + "kind": "collection",
            PREFIX + "xid": "/emptygroups", PREFIX + "mode": mode,
            PREFIX + "lower": lower, PREFIX + "upper": upper,
        },
        "manifests": copy.deepcopy(entries),
    }


def _limit_index(graph, count, roles):
    members = graph["members"][:count]
    if roles == "entities":
        return _raw_collection(members)
    shards = []
    for number, member in enumerate(members):
        lower = "" if number == 0 else member["annotations"][PREFIX + "xid"]
        upper = members[number + 1]["annotations"][PREFIX + "xid"] if number + 1 < count else ""
        raw = _json_bytes(_raw_collection([member], lower=lower, upper=upper))
        descriptor = _write_blob(graph["path"], raw, INDEX)
        descriptor["annotations"] = {
            PREFIX + "role": "shard", PREFIX + "xid": "/emptygroups",
            PREFIX + "lower": lower, PREFIX + "upper": upper,
        }
        shards.append(descriptor)
    return _raw_collection(shards, mode="branch")


def _padded_index(node, size, non_ascii=False):
    node = copy.deepcopy(node)
    node["annotations"]["org.example.padding"] = ""
    remaining = size - len(_json_bytes(node))
    assert remaining > 0
    node["annotations"]["org.example.padding"] = (
        "é" * (remaining // 2) + " " * (remaining % 2) if non_ascii else " " * remaining
    )
    encoded = _json_bytes(node)
    assert len(encoded) == size
    if non_ascii:
        assert len(encoded.decode("utf-8")) < size
        assert b"\xc3\xa9" in encoded
    return encoded, node


@pytest.fixture(scope="module")
def range_layout(tmp_path_factory, shared_records):
    records, documents = copy.deepcopy(shared_records)
    template = copy.deepcopy(_record(records, V1))
    records = [record for record in records if record["entity"]["xid"] not in (V1, V2)]
    documents.pop(V1)
    documents.pop(V2)
    _record(records, ITEM + "/meta")["entity"]["defaultversionid"] = "a"
    for versionid in RANGE_IDS:
        record = copy.deepcopy(template)
        record["entity"].update({
            "xid": ITEM + "/versions/" + versionid, "versionid": versionid,
            "ancestorid": "a", "isdefault": versionid == "a",
        })
        records.append(record)
        documents[record["entity"]["xid"]] = f'{{"version":"{versionid}"}}\n'.encode("ascii")
    path = tmp_path_factory.mktemp("oci-ranges")
    oci.build_layout(path, records, documents, page_size=2)
    return _graph(path)


def test_oci_shared_authored_dataset_has_independent_native_oracle(shared_records, shared_layout, mapping_sample_root):
    records, documents = shared_records
    assert len(records) == 24
    assert documents == BASE_BYTES
    assert _record(records, "/")["entity"] == REGISTRY_ENTITY
    assert _record(records, "/")["modelresolved"] == MODEL_SOURCE
    authored_root = (mapping_sample_root / "registry.json").read_bytes()
    assert hashlib.sha256(authored_root).hexdigest() == (
        "7e4c37ca61b2b875ee055a8fc67e5c90c48b344689823a12dc1fb0a6e33232bf"
    )
    assert (mapping_sample_root / "documents" / "n1.bin").read_bytes() == BASE_BYTES[V1]
    assert (mapping_sample_root / "documents" / "n2.bin").read_bytes() == b""
    assert (mapping_sample_root / "documents" / "n0.bin").read_bytes() == BASE_BYTES[BINARY]
    reader = oci.FixtureLayout(shared_layout["path"])
    summary = reader.validate()
    assert summary == {
        "root": shared_layout["root"]["digest"], "snapshot": "offline-complete",
        "objects": 89, "records": 24, "indexes": 37, "manifests": 24, "documents": 3,
        "max_index_descriptors": 4,
        "max_index_bytes": max(
            len(data) for descriptor, data in shared_layout["objects"].values()
            if descriptor["mediaType"] == INDEX
        ),
    }
    assert {item["digest"] for item in reader.inventory} == set(shared_layout["objects"])
    assert reader.lookup("/") == {
        "snapshot": shared_layout["root"]["digest"], "operation": "entity",
        "target": "/", "value": _registry_view(), "pointer": "",
    }


@pytest.mark.parametrize("reference,objects,documents", [
    pytest.param("offline", 99, 4, id="offline-complete"),
    pytest.param("linked", 98, 3, id="linked"),
])
def test_oci_standard_graph_roles_and_media_types(reference, objects, documents, oci_sample_root):
    path = oci_sample_root / "layout"
    graph = _graph(path, reference)
    reader = oci.FixtureLayout(path, reference)
    summary = reader.validate()
    expected_root = {
        "offline": "sha256:c937f902c54ca9c63e510bab3b4ec07ec3775ad338ac030ac93d916a736efba6",
        "linked": "sha256:dff871378d2678ee851fb7d97bae5a6b69b05c3d668f224a2f97127e8e8dee88",
    }[reference]
    assert reader.root_digest == expected_root
    assert summary["objects"] == objects
    assert (summary["indexes"], summary["manifests"], summary["records"], summary["documents"]) == (
        44, 25, 25, documents,
    )
    assert {item["digest"] for item in reader.inventory} == set(graph["objects"])
    roles = Counter(edge.get("annotations", {}).get(PREFIX + "role") for edge in graph["edges"][1:])
    assert set(roles) == {
        "metadata", "meta", "collections", "collection", "entity", "shard",
        "config", "document", "empty",
    }
    assert roles["config"] == 25
    assert roles["document"] == documents
    assert roles["empty"] == 25 - documents
    for descriptor, node in graph["nodes"].values():
        assert node["schemaVersion"] == 2
        assert node["mediaType"] == descriptor["mediaType"]
        kind = node["annotations"][PREFIX + "kind"]
        if node["mediaType"] == INDEX and kind in ("registry", "group", "resource"):
            assert [edge["annotations"][PREFIX + "role"] for edge in node["manifests"]] == (
                ["metadata", "meta", "collections"] if kind == "resource"
                else ["metadata", "collections"]
            )
        if node["mediaType"] == MANIFEST:
            assert node["config"]["mediaType"] == CONFIG
            assert node["config"]["annotations"][PREFIX + "role"] == "config"
            assert len(node["layers"]) == 1
        assert not (node.keys() & {"subject", "referrers", "children"})
    for descriptor in graph["edges"]:
        data = reader.fetch(descriptor)
        assert (len(data), _digest(data)) == (descriptor["size"], descriptor["digest"])
    assert len(reader.inventory) == objects


@pytest.mark.parametrize("count", [0, 1, 37, 255, 256, 257], ids=lambda value: f"count-{value}")
def test_oci_descriptor_count_boundaries(count_layout, count):
    node = _limit_index(count_layout, count, "entities")
    raw = _json_bytes(node)
    assert len(node["manifests"]) == count
    assert len({edge["digest"] for edge in node["manifests"]}) == count
    assert len(raw) < 1_048_576
    if count == 257:
        _error(lambda: oci.check_index(raw), "limit_exceeded", "Index exceeds 256 descriptors")
    else:
        assert oci.check_index(raw) == node
        assert [edge["annotations"][PREFIX + "xid"] for edge in node["manifests"]] == [
            f"/emptygroups/n{i:04d}" for i in range(count)
        ]


@pytest.mark.parametrize("count", [256, 257], ids=lambda value: f"control-count-{value}")
def test_oci_descriptor_count_includes_shard_control_descriptors(count_layout, count):
    node = _limit_index(count_layout, count, "controls")
    raw = _json_bytes(node)
    assert len(raw) < 1_048_576
    assert len({edge["digest"] for edge in node["manifests"]}) == count
    assert {edge["annotations"][PREFIX + "role"] for edge in node["manifests"]} == {"shard"}
    reader = oci.FixtureLayout(count_layout["path"])
    for edge in node["manifests"]:
        child = oci.check_index(reader.fetch(edge))
        assert len(child["manifests"]) == 1
        member = child["manifests"][0]
        assert oci.check_index(reader.fetch(member))["annotations"][PREFIX + "xid"] == (
            member["annotations"][PREFIX + "xid"]
        )
    if count == 257:
        _error(lambda: oci.check_index(raw), "limit_exceeded", "Index exceeds 256 descriptors")
    else:
        assert oci.check_index(raw) == node


@pytest.mark.parametrize("size", [1_048_575, 1_048_576, 1_048_577], ids=lambda value: f"bytes-{value}")
@pytest.mark.parametrize("non_ascii", [False, True], ids=["ascii", "utf8-nonascii"])
def test_oci_encoded_byte_boundaries(count_layout, size, non_ascii):
    raw, node = _padded_index(_limit_index(count_layout, 37, "entities"), size, non_ascii)
    assert len(node["manifests"]) == 37
    assert len({edge["digest"] for edge in node["manifests"]}) == 37
    if size > 1_048_576:
        _error(lambda: oci.check_index(raw), "limit_exceeded", "Index exceeds 1048576 encoded bytes")
    else:
        assert oci.check_index(raw) == node
        assert raw.endswith(b"\n")


@pytest.mark.parametrize("roles", ["entities", "controls"])
@pytest.mark.parametrize("count,size", [
    pytest.param(256, 1_048_576, id="count-256-bytes-1048576"),
    pytest.param(257, 1_048_576, id="count-257-bytes-1048576"),
    pytest.param(256, 1_048_577, id="count-256-bytes-1048577"),
    pytest.param(257, 1_048_577, id="count-257-bytes-1048577"),
])
def test_oci_index_limits_are_independent(count_layout, roles, count, size):
    raw, node = _padded_index(_limit_index(count_layout, count, roles), size, non_ascii=True)
    assert len(node["manifests"]) == count
    assert len({edge["digest"] for edge in node["manifests"]}) == count
    if size > 1_048_576:
        _error(lambda: oci.check_index(raw), "limit_exceeded", "Index exceeds 1048576 encoded bytes")
    elif count > 256:
        _error(lambda: oci.check_index(raw), "limit_exceeded", "Index exceeds 256 descriptors")
    else:
        assert oci.check_index(raw) == node


@pytest.mark.parametrize("xid", [V1, BINARY, V2], ids=["formatted-json", "binary", "present-empty"])
def test_oci_json_binary_and_empty_bytes_are_exact(byte_layout, xid):
    expected, size, digest = BYTE_STATES[xid]
    trace = []
    with patch.object(oci, "_read_file", wraps=oci._read_file) as read:
        result = oci.lookup_layout(byte_layout["path"], xid, operation="document", trace=trace)
    assert result == {
        "snapshot": byte_layout["root"]["digest"], "operation": "document",
        "target": xid, "resolved": xid,
        "mediaType": "application/json" if xid == V1 else "application/octet-stream",
        "data": expected,
    }
    assert len(result["data"]) == size
    assert hashlib.sha256(result["data"]).hexdigest() == digest
    _assert_trace(byte_layout["path"], trace, _version_trace(byte_layout, xid), read)


def test_oci_metadata_and_json_document_are_separate(byte_layout):
    metadata_trace = []
    with patch.object(oci, "_read_file", wraps=oci._read_file) as metadata_reads:
        metadata = oci.lookup_layout(byte_layout["path"], V1, trace=metadata_trace)
    document_trace = []
    with patch.object(oci, "_read_file", wraps=oci._read_file) as document_reads:
        document = oci.lookup_layout(
            byte_layout["path"], V1, operation="document", trace=document_trace,
        )
    assert metadata == {
        "snapshot": byte_layout["root"]["digest"], "operation": "entity",
        "target": V1, "value": {**VERSION_ENTITIES[V1], "self": "#"}, "pointer": "",
    }
    assert document["data"] == b' { "value": 1 }\r\n'
    assert document["resolved"] == V1
    assert json.loads(document["data"]) == {"value": 1}
    assert metadata["value"] != json.loads(document["data"])
    _assert_trace(
        byte_layout["path"], metadata_trace,
        _version_trace(byte_layout, V1, operation="entity"), metadata_reads,
    )
    _assert_trace(byte_layout["path"], document_trace, _version_trace(byte_layout, V1), document_reads)
    assert not ({entry.get("digest") for entry in metadata_trace} & {
        "sha256:" + item[2] for item in BYTE_STATES.values()
    })


@pytest.mark.parametrize("kind,target", [
    pytest.param("registry", "/", id="registry"),
    pytest.param("group", "/documents/main", id="group"),
    pytest.param("resource", ITEM, id="resource"),
    pytest.param("meta", ITEM + "/meta", id="meta"),
    pytest.param("version", V1, id="version"),
])
def test_oci_metadata_kinds_preserve_identity_and_extensions(extension_layout, kind, target):
    graph = extension_layout
    trace = []
    with patch.object(oci, "_read_file", wraps=oci._read_file) as read:
        result = oci.lookup_layout(graph["path"], target, trace=trace)
    expected = {
        "registry": _registry_view(extra=True),
        "group": _documents_view(extra=True),
        "resource": _item_view(extra=True),
        "meta": _item_view(extra=True),
        "version": {**VERSION_ENTITIES[V1], "exampleextension": EXTRA, "self": "#"},
    }[kind]
    assert result == {
        "snapshot": graph["root"]["digest"], "operation": "entity",
        "target": target, "value": expected, "pointer": "/meta" if kind == "meta" else "",
    }
    if kind == "version":
        descriptors = _version_trace(graph, V1, operation="entity")
    elif kind == "registry":
        descriptors = [
            graph["root"], *_metadata_pair(graph, "registry", "/"),
            *_subtree_descriptors(graph, graph["root"]),
        ]
    else:
        resource_path = _resource_path(graph, ITEM)
        if kind == "group":
            descriptors = resource_path[:6] + _subtree_descriptors(
                graph, _index(graph, "group", "/documents/main"),
            )
        else:
            descriptors = resource_path
            if kind == "meta":
                descriptors += _metadata_pair(graph, "meta", ITEM + "/meta")
            descriptors += _subtree_descriptors(graph, _index(graph, "resource", ITEM))
    _assert_trace(graph["path"], trace, descriptors, read)
    assert not ({entry.get("digest") for entry in trace} & {_digest(data) for data in BASE_BYTES.values()})
    assert all(entry.get("mediaType") != EMPTY for entry in trace)


@pytest.mark.parametrize("operation", ["entity", "document"])
def test_oci_selective_xid_read_skips_unrelated_payloads(shared_layout, operation):
    graph = shared_layout
    forbidden = {_blob_path(graph["path"], _document_edge(graph, xid)) for xid in (V2, BINARY)}
    if operation == "entity":
        forbidden.add(_blob_path(graph["path"], _document_edge(graph, V1)))
    real_read = oci._read_file

    def guarded_read(path, **kwargs):
        assert path not in forbidden, f"Unrelated payload fetched: {path}"
        return real_read(path, **kwargs)

    trace = []
    with patch.object(oci, "_read_file", side_effect=guarded_read) as read:
        result = oci.lookup_layout(graph["path"], V1, operation=operation, trace=trace)
    expected = {
        "snapshot": graph["root"]["digest"], "operation": operation, "target": V1,
        **(
            {"resolved": V1, "mediaType": "application/json", "data": BASE_BYTES[V1]}
            if operation == "document"
            else {"value": {**VERSION_ENTITIES[V1], "self": "#"}, "pointer": ""}
        ),
    }
    assert result == expected
    _assert_trace(graph["path"], trace, _version_trace(graph, V1, operation=operation), read)
    assert len(trace) < len(graph["objects"]) + 2


def test_oci_full_validation_is_distinct_from_selective_read(shared_layout):
    graph = shared_layout
    selective_trace = []
    with patch.object(oci, "_read_file", wraps=oci._read_file) as selective_reads:
        selected = oci.lookup_layout(
            graph["path"], V1, operation="document", trace=selective_trace,
        )
    full_trace = []
    with patch.object(oci, "_read_file", wraps=oci._read_file) as full_reads:
        reader = oci.FixtureLayout(graph["path"], trace=full_trace)
        summary = reader.validate()
    assert selected["data"] == BASE_BYTES[V1]
    assert (summary["objects"], summary["records"], summary["documents"]) == (89, 24, 3)
    _assert_trace(graph["path"], selective_trace, _version_trace(graph, V1), selective_reads)
    _assert_trace(
        graph["path"], full_trace,
        [graph["root"], *_metadata_pair(graph, "registry", "/"),
         *_subtree_descriptors(graph, graph["root"], payloads=True)],
        full_reads,
    )
    assert {entry["digest"] for entry in full_trace[2:]} == set(graph["objects"])
    assert {entry["digest"] for entry in selective_trace[2:]} < set(graph["objects"])
    assert {_digest(data) for data in BASE_BYTES.values()} <= {
        entry["digest"] for entry in full_trace[2:]
    }


def test_oci_multilevel_shards_reach_selected_entity(range_layout):
    graph = range_layout
    collection = ITEM + "/versions"
    xid = collection + "/m"
    ranges = [(collection + "/m", ""), (collection + "/m", collection + "/z")]
    trace = []
    with patch.object(oci, "_read_file", wraps=oci._read_file) as read:
        result = oci.lookup_layout(graph["path"], xid, operation="document", trace=trace)
    assert result == {
        "snapshot": graph["root"]["digest"], "operation": "document",
        "target": xid, "resolved": xid, "mediaType": "application/json",
        "data": b'{"version":"m"}\n',
    }
    _assert_trace(
        graph["path"], trace, _version_trace(graph, xid, ranges=ranges, sharded=True), read,
    )
    assert [
        _node(graph, "collection", collection, INDEX, lower, upper)[1]["annotations"][PREFIX + "mode"]
        for lower, upper in [("", ""), *ranges]
    ] == ["branch", "branch", "leaf"]


@pytest.mark.parametrize("versionid,bounds", [
    pytest.param("a", [("", "m"), ("", "k")], id="first-singleton-leaf"),
    pytest.param("k", [("", "m"), ("k", "m")], id="interior-lower-inclusive"),
    pytest.param("l", [("", "m"), ("k", "m")], id="before-m"),
    pytest.param("m", [("m", ""), ("m", "z")], id="at-m-lower-inclusive-upper-exclusive"),
    pytest.param("n", [("m", ""), ("m", "z")], id="after-m"),
    pytest.param("z", [("m", ""), ("z", "")], id="at-z"),
    pytest.param("zz", [("m", ""), ("z", "")], id="last"),
])
def test_oci_shard_boundaries_route_exactly_once(range_layout, versionid, bounds):
    graph = range_layout
    collection = ITEM + "/versions"
    xid = collection + "/" + versionid
    ranges = [
        (collection + "/" + lower if lower else "", collection + "/" + upper if upper else "")
        for lower, upper in bounds
    ]
    trace = []
    with patch.object(oci, "_read_file", wraps=oci._read_file) as read:
        result = oci.lookup_layout(graph["path"], xid, operation="document", trace=trace)
    assert result["data"] == f'{{"version":"{versionid}"}}\n'.encode("ascii")
    assert result["resolved"] == xid
    assert result["snapshot"] == graph["root"]["digest"]
    _assert_trace(
        graph["path"], trace, _version_trace(graph, xid, ranges=ranges, sharded=True), read,
    )
    visited = [entry["digest"] for entry in trace[2:]]
    assert visited.count(_index(graph, "collection", collection, *ranges[-1])["digest"]) == 1
    leaf_digests = {
        descriptor["digest"]
        for (media, kind, path, lower, upper), (descriptor, node) in graph["nodes"].items()
        if (media, kind, path) == (INDEX, "collection", collection)
        and node["annotations"][PREFIX + "mode"] == "leaf"
    }
    assert set(visited) & leaf_digests == {
        _index(graph, "collection", collection, *ranges[-1])["digest"]
    }


@pytest.mark.parametrize("case", [
    "zero", "one", "many", "explicit-digest-many", "explicit-tag-many",
    "missing-tag", "duplicate-root-digest", "duplicate-tag", "unrelated-artifacts",
])
def test_oci_root_selection_zero_one_and_many(private_layout, shared_records, case):
    graph = private_layout
    path = graph["path"]
    first = graph["root"]
    records, documents = copy.deepcopy(shared_records)
    _record(records, "/")["entity"]["registryid"] = "second"
    documents[V1] = b'{"origin":"second"}\n'
    second = oci.build_layout(path, records, documents, reference="second")
    head = json.loads((path / "index.json").read_bytes())
    reference = None
    expected_error = None
    expected_digest = first["digest"]
    expected_bytes = BASE_BYTES[V1]
    if case == "zero":
        head["manifests"] = []
        expected_error = ("not_found", "No eligible Registry root")
    elif case == "one":
        head["manifests"] = [first]
    elif case == "many":
        expected_error = ("ambiguous", "Select one Registry snapshot root explicitly")
    elif case == "explicit-digest-many":
        reference = second["digest"]
        expected_digest, expected_bytes = second["digest"], b'{"origin":"second"}\n'
    elif case == "explicit-tag-many":
        reference = "snapshot"
    elif case == "missing-tag":
        reference = "absent"
        expected_error = ("not_found", "Layout tag not found")
    elif case == "duplicate-root-digest":
        duplicate = copy.deepcopy(first)
        duplicate["annotations"] = {"org.opencontainers.image.ref.name": "another-name"}
        head["manifests"] = [first, duplicate]
    elif case == "duplicate-tag":
        head["manifests"] = [first, copy.deepcopy(first)]
        reference = "snapshot"
        expected_error = ("ambiguous", "More than one entry has the selected tag")
    else:
        head["manifests"] = [first, _index(graph, "group", "/documents/main")]
    (path / "index.json").write_bytes(_json_bytes(head))
    trace = []
    with patch.object(oci, "_read_file", wraps=oci._read_file) as read:
        if expected_error:
            _error(lambda: oci.FixtureLayout(path, reference, trace=trace), *expected_error)
            assert trace == _expected_trace(path, [])
            assert [item.args[0] for item in read.call_args_list] == [
                path / "oci-layout", path / "index.json",
            ]
        else:
            reader = oci.FixtureLayout(path, reference, trace=trace)
            result = reader.lookup(ITEM, operation="document")
            assert result == {
                "snapshot": expected_digest, "operation": "document",
                "target": ITEM, "resolved": V1, "mediaType": "application/json",
                "data": expected_bytes,
            }
            assert reader.root_descriptor["digest"] == expected_digest
            other = first["digest"] if expected_digest == second["digest"] else second["digest"]
            assert other not in {entry.get("digest") for entry in trace}
            assert [entry["path"] for entry in trace[:2]] == ["oci-layout", "index.json"]


@pytest.mark.parametrize("case,message", [
    pytest.param("artifact-type", "artifactType disagrees with the node kind", id="artifact-type"),
    pytest.param("media-type", "Not an OCI image index", id="media-type"),
    pytest.param("metadata-edge-media", "Wrong metadata edge at /", id="metadata-edge-media"),
    pytest.param("control-role", "Wrong metadata edge at /", id="explicit-control-role"),
])
def test_oci_wrong_artifact_and_media_type_are_rejected(private_layout, case, message):
    graph = private_layout
    descriptor = graph["root"]

    def mutate(node):
        if case == "artifact-type":
            node["artifactType"] = "application/vnd.xregistry.group.v1+json"
        elif case == "media-type":
            node["mediaType"] = MANIFEST
        elif case == "metadata-edge-media":
            node["manifests"][0]["mediaType"] = INDEX
        else:
            node["manifests"][0]["annotations"][PREFIX + "role"] = "collections"

    if case == "media-type":
        node = json.loads(graph["objects"][descriptor["digest"]][1])
        mutate(node)
        raw = _json_bytes(node)
        replacement = _write_blob(graph["path"], raw, INDEX)
        head = json.loads((graph["path"] / "index.json").read_bytes())
        head["manifests"][0].update({key: replacement[key] for key in ("size", "digest")})
        (graph["path"] / "index.json").write_bytes(_json_bytes(head))
    else:
        replacement = _edit_node(graph, descriptor, mutate)
    raw = _blob_path(graph["path"], replacement).read_bytes()
    assert (len(raw), _digest(raw)) == (replacement["size"], replacement["digest"])
    trace = []
    _error(lambda: oci.FixtureLayout(graph["path"], trace=trace), "invalid_package", message)
    assert trace[-1]["digest"] == replacement["digest"]
    assert len(trace) == 3


@pytest.mark.parametrize("case,message", [
    pytest.param("overlap", "Overlapping or gapped shard ranges", id="overlap"),
    pytest.param("duplicate-range", "Overlapping or gapped shard ranges", id="duplicate-range"),
    pytest.param("gap", "Overlapping or gapped shard ranges", id="gap"),
    pytest.param("uncovered-end", "Shards do not cover the parent range", id="uncovered-parent-end"),
    pytest.param("duplicate-entry", "Case-insensitive sibling ID collision", id="duplicate-entry"),
    pytest.param("unsorted-entry", "Unsorted, duplicate or out-of-range key", id="unsorted-entry"),
    pytest.param("child-bounds", "Shard bounds disagree with parent descriptor", id="child-bound-disagreement"),
])
def test_oci_shards_reject_overlap_and_duplicate_ranges_or_entries(tmp_path, case, message):
    names = ["a", "k", "l", "m", "n", "z", "zz"]
    oci.build_layout(tmp_path, _group_records(names), page_size=2)
    graph = _graph(tmp_path)
    oci.validate_layout(tmp_path)
    descriptor = _index(graph, "collection", "/emptygroups")
    if case in ("duplicate-entry", "unsorted-entry"):
        descriptor = _index(graph, "collection", "/emptygroups", "/emptygroups/k", "/emptygroups/m")
    elif case == "child-bounds":
        descriptor = _index(graph, "collection", "/emptygroups", "/emptygroups/m", "")

    def mutate(node):
        entries = node["manifests"]
        if case == "overlap":
            entries[1]["annotations"][PREFIX + "lower"] = "/emptygroups/l"
        elif case == "duplicate-range":
            entries[1]["annotations"][PREFIX + "lower"] = ""
            entries[1]["annotations"][PREFIX + "upper"] = "/emptygroups/m"
        elif case == "gap":
            entries[1]["annotations"][PREFIX + "lower"] = "/emptygroups/n"
        elif case == "uncovered-end":
            entries[-1]["annotations"][PREFIX + "upper"] = "/emptygroups/zzz"
        elif case == "duplicate-entry":
            entries.append(copy.deepcopy(entries[0]))
        elif case == "unsorted-entry":
            entries.reverse()
        else:
            node["annotations"][PREFIX + "lower"] = "/emptygroups/n"

    changed_root = _edit_node(graph, descriptor, mutate)
    assert changed_root["digest"] != graph["root"]["digest"]
    trace = []
    with patch.object(oci, "_read_file", wraps=oci._read_file) as read:
        reader = oci.FixtureLayout(tmp_path, trace=trace)
        _error(reader.validate, "invalid_package", message)
    assert trace[2]["digest"] == changed_root["digest"]
    assert all(entry.args[0].is_relative_to(tmp_path) for entry in read.call_args_list)
    assert not any(entry.get("mediaType") == DOCUMENT for entry in trace)


@pytest.mark.parametrize("role", ["subtree", "manifest", "config", "payload"])
def test_oci_missing_required_descendants_are_rejected(private_layout, role):
    graph = private_layout
    path = graph["path"]
    descriptor = {
        "subtree": _index(graph, "collection", "/documents/main/assets"),
        "manifest": _metadata_pair(graph, "version", V1)[0],
        "config": _metadata_pair(graph, "version", V1)[1],
        "payload": _document_edge(graph, V1),
    }[role]
    missing = _blob_path(path, descriptor)
    assert _digest(missing.read_bytes()) == descriptor["digest"]
    missing.unlink()
    trace = []
    with patch.object(oci, "_read_file", wraps=oci._read_file) as read:
        reader = oci.FixtureLayout(path, trace=trace)
        _error(reader.validate, "invalid_package", f"Missing file: {missing}")
    assert read.call_args_list[-1].args[0] == missing
    assert descriptor["digest"] not in {entry.get("digest") for entry in trace}
    assert reader.root_digest == graph["root"]["digest"]
    _error(
        lambda: oci.lookup_layout(path, V1, operation="document"),
        "invalid_package", f"Missing file: {missing}",
    )


@pytest.mark.parametrize("case", ["size-only", "digest-only"])
def test_oci_descriptor_size_and_digest_mismatches_are_rejected(private_layout, case):
    graph = private_layout
    payload = _document_edge(graph, V1)
    path = _blob_path(graph["path"], payload)
    original = path.read_bytes()
    if case == "size-only":
        manifest = _metadata_pair(graph, "version", V1)[0]
        _edit_node(
            graph, manifest,
            lambda node: node["layers"][0].__setitem__("size", len(original) + 1),
        )
        assert path.read_bytes() == original
        assert _digest(path.read_bytes()) == payload["digest"]
    else:
        changed = b"!" + original[1:]
        assert len(changed) == payload["size"]
        assert _digest(changed) != payload["digest"]
        path.write_bytes(changed)
    trace = []
    with patch.object(oci, "_read_file", wraps=oci._read_file) as read:
        _error(
            lambda: oci.lookup_layout(graph["path"], V1, operation="document", trace=trace),
            "integrity_error", f"Descriptor mismatch: {payload['digest']}",
        )
    assert read.call_args_list[-1].args[0] == path
    assert payload["digest"] not in {entry.get("digest") for entry in trace}
    assert _document_edge(graph, BINARY)["digest"] not in {entry.get("digest") for entry in trace}


@pytest.mark.parametrize("size", [0, 1, 17, 256, 257, 4097], ids=lambda value: f"members-{value}")
def test_oci_collection_sizes_keep_root_bounded(tmp_path, size):
    names = [f"n{i:04d}" for i in range(size)]
    root = oci.build_layout(tmp_path, _group_records(names))
    graph = _graph(tmp_path)
    root_node = json.loads(_blob_path(tmp_path, root).read_bytes())
    assert [entry["annotations"][PREFIX + "role"] for entry in root_node["manifests"]] == [
        "metadata", "collections",
    ]
    assert len(root_node["manifests"]) == 2
    assert root["size"] == len(_json_bytes(root_node)) == 902
    full = oci.FixtureLayout(tmp_path)
    summary = full.validate()
    assert (summary["records"], summary["manifests"], summary["documents"]) == (size + 1, size + 1, 0)
    assert {entry["digest"] for entry in full.inventory} == set(graph["objects"])
    for descriptor in full.inventory:
        if descriptor["mediaType"] == INDEX:
            raw = full.fetch(descriptor)
            assert len(raw) <= 1_048_576
            assert len(json.loads(raw)["manifests"]) <= 256
    trace = []
    with patch.object(oci, "_read_file", wraps=oci._read_file) as read:
        reader = oci.FixtureLayout(tmp_path, trace=trace)
        if not names:
            result = reader.lookup("/emptygroups", operation="collection")
            assert result == {
                "snapshot": root["digest"], "operation": "collection",
                "target": "/emptygroups", "value": {}, "pointer": "",
            }
        else:
            result = reader.lookup("/emptygroups/n0000")
            assert result == {
                "snapshot": root["digest"], "operation": "entity",
                "target": "/emptygroups/n0000",
                "value": {**STAMP, "xid": "/emptygroups/n0000", "emptygroupid": "n0000", "self": "#"},
                "pointer": "",
            }
    # First-key lookup visits exactly one shard per level. Expected paths are
    # the independently known producer bisections, not a cleared full-walk trace.
    descriptors = [
        root, *_metadata_pair(graph, "registry", "/"),
        _index(graph, "collections", "/"), _index(graph, "collection", "/emptygroups"),
    ]
    remaining = size
    while remaining > 256:
        remaining //= 2
        descriptors.append(_index(graph, "collection", "/emptygroups", "", f"/emptygroups/n{remaining:04d}"))
    if names:
        descriptors += [
            _index(graph, "group", "/emptygroups/n0000"),
            *_metadata_pair(graph, "group", "/emptygroups/n0000"),
            _index(graph, "collections", "/emptygroups/n0000"),
        ]
    _assert_trace(tmp_path, trace, descriptors, read)
    assert len(trace) == (7 if size == 0 else 11 + (size > 256) + (size > 512) + (size > 1024) + (size > 2048))
    assert all(entry.get("mediaType") not in (DOCUMENT, EMPTY) for entry in trace)


@pytest.mark.parametrize("page_size,byte_budget", [
    pytest.param(2, 1_048_576, id="descriptor-driven"),
    pytest.param(256, 2100, id="byte-driven-before-count-limit"),
])
def test_oci_producer_splits_and_preserves_complete_sorted_membership(tmp_path, page_size, byte_budget):
    names = [f"n{i:04d}" for i in range(37)]
    oci.build_layout(tmp_path, _group_records(names), page_size=page_size, max_index_bytes=byte_budget)
    reader = oci.FixtureLayout(tmp_path)
    summary = reader.validate()
    result = reader.lookup("/emptygroups", operation="collection")
    assert result == {
        "snapshot": reader.root_digest, "operation": "collection", "target": "/emptygroups",
        "value": {
            name: {
                **STAMP, "xid": "/emptygroups/" + name,
                "emptygroupid": name, "self": "#/" + name,
            }
            for name in names
        },
        "pointer": "",
    }
    assert (summary["records"], summary["documents"]) == (38, 0)
    graph = _graph(tmp_path)
    leaves = []
    for descriptor, node in graph["nodes"].values():
        if descriptor["mediaType"] != INDEX:
            continue
        assert len(_blob_path(tmp_path, descriptor).read_bytes()) <= byte_budget
        assert len(node["manifests"]) <= 256
        if node["annotations"][PREFIX + "xid"] == "/emptygroups":
            if node["annotations"][PREFIX + "mode"] == "leaf":
                leaves.append(node)
                assert len(node["manifests"]) <= page_size
    leaves.sort(key=lambda node: node["annotations"][PREFIX + "lower"])
    assert len(leaves) > 1
    assert leaves[0]["annotations"][PREFIX + "lower"] == ""
    assert leaves[-1]["annotations"][PREFIX + "upper"] == ""
    assert [node["annotations"][PREFIX + "upper"] for node in leaves[:-1]] == [
        node["annotations"][PREFIX + "lower"] for node in leaves[1:]
    ]
    assert [
        edge["annotations"][PREFIX + "xid"]
        for leaf in leaves for edge in leaf["manifests"]
    ] == ["/emptygroups/" + name for name in names]


def _changed_snapshot(shared_records):
    records, documents = copy.deepcopy(shared_records)
    _record(records, V1)["entity"].update({
        "epoch": 2, "modifiedat": "2026-09-06T00:00:00Z",
    })
    documents[V1] = b' { "value": 2 }\r\n'
    return records, documents


def test_oci_new_root_reuses_unchanged_subtrees(private_layout, shared_records):
    first = private_layout
    next_root = oci.build_layout(first["path"], *_changed_snapshot(shared_records))
    second = _graph(first["path"])
    assert next_root["digest"] != first["root"]["digest"]
    for kind, xid in [
        ("collection", "/categories"), ("collection", "/independent"),
        ("collection", "/mirrors"), ("resource", "/documents/main/assets/CON"),
        ("collection", "/documents/main/notes"),
    ]:
        assert _index(first, kind, xid)["digest"] == _index(second, kind, xid)["digest"]
    for kind, xid in [
        ("collections", "/"), ("collection", "/documents"),
        ("group", "/documents/main"), ("collection", "/documents/main/assets"),
        ("resource", ITEM), ("collection", ITEM + "/versions"),
    ]:
        assert _index(first, kind, xid)["digest"] != _index(second, kind, xid)["digest"]
    assert _document_edge(first, V2)["digest"] == _document_edge(second, V2)["digest"]
    assert _metadata_pair(first, "meta", ITEM + "/meta") == _metadata_pair(second, "meta", ITEM + "/meta")
    reader = oci.FixtureLayout(first["path"])
    assert reader.lookup(ITEM, operation="document") == {
        "snapshot": next_root["digest"], "operation": "document", "target": ITEM,
        "resolved": V1, "mediaType": "application/json", "data": b' { "value": 2 }\r\n',
    }
    assert reader.lookup(MIRRORS + "/copy", operation="document")["data"] == b' { "value": 2 }\r\n'
    assert reader.lookup(V1)["value"] == {
        **VERSION_ENTITIES[V1], "epoch": 2,
        "modifiedat": "2026-09-06T00:00:00Z", "self": "#",
    }


def test_oci_new_root_reads_without_delta_replay(tmp_path, shared_records):
    history = tmp_path / "history"
    first_root = oci.build_layout(history, *copy.deepcopy(shared_records))
    updated_root = oci.build_layout(history, *_changed_snapshot(shared_records))
    standalone = tmp_path / "standalone"
    root = oci.build_layout(standalone, *_changed_snapshot(shared_records))
    assert root == updated_root
    assert not _blob_path(standalone, first_root).exists()
    reader = oci.FixtureLayout(standalone, root["digest"])
    summary = reader.validate()
    assert (summary["objects"], summary["records"], summary["documents"]) == (89, 24, 3)
    assert {path.name for path in (standalone / "blobs" / "sha256").iterdir()} == {
        descriptor["digest"][7:] for descriptor in reader.inventory
    }
    expected = {V1: b' { "value": 2 }\r\n', V2: b"", BINARY: BASE_BYTES[BINARY]}
    for xid, data in expected.items():
        result = reader.lookup(xid, operation="document")
        assert result["data"] == data
        assert result["resolved"] == xid
        assert result["snapshot"] == root["digest"]
    assert reader.lookup(CATALOG + "/versions/v1")["value"] == {
        **VERSION_ENTITIES[CATALOG + "/versions/v1"], "self": "#",
    }
    assert all("delta" not in entry["path"] and "history" not in entry["path"] for entry in reader.trace)


@pytest.mark.parametrize("state", ["metadata-only", "missing-blob", "missing-layer", "empty", "object", "null"])
def test_oci_metadata_only_missing_and_zero_byte_states_are_distinct(tmp_path, byte_state_records, state):
    oci.build_layout(tmp_path, *copy.deepcopy(byte_state_records))
    graph = _graph(tmp_path)
    if state == "metadata-only":
        result = oci.lookup_layout(tmp_path, NOTES + "/versions/v1")
        assert result["value"] == {**VERSION_ENTITIES[NOTES + "/versions/v1"], "self": "#"}
        assert result["snapshot"] == graph["root"]["digest"]
        _error(
            lambda: oci.lookup_layout(tmp_path, NOTES, operation="document"),
            "unsupported_operation", "Resource is metadata-only",
        )
        assert _document_edge(graph, NOTES + "/versions/v1")["mediaType"] == EMPTY
    elif state == "missing-blob":
        missing = _blob_path(tmp_path, _document_edge(graph, V1))
        missing.unlink()
        _error(
            lambda: oci.lookup_layout(tmp_path, V1, operation="document"),
            "invalid_package", f"Missing file: {missing}",
        )
        assert oci.lookup_layout(tmp_path, V1)["value"] == {**VERSION_ENTITIES[V1], "self": "#"}
    elif state == "missing-layer":
        manifest = _metadata_pair(graph, "version", V1)[0]
        _edit_node(graph, manifest, lambda node: node.__setitem__("layers", []))
        _schema_error(
            lambda: oci.lookup_layout(tmp_path, V1, operation="document"), "oci-graph.schema.json",
        )
        assert _blob_path(tmp_path, _document_edge(graph, V1)).read_bytes() == BYTE_STATES[V1][0]
    else:
        xid = {"empty": V2, "object": ITEM + "/versions/v10", "null": ITEM + "/versions/v11"}[state]
        data, size, digest = BYTE_STATES[xid]
        result = oci.lookup_layout(tmp_path, xid, operation="document")
        assert result == {
            "snapshot": graph["root"]["digest"], "operation": "document",
            "target": xid, "resolved": xid,
            "mediaType": "application/octet-stream" if state == "empty" else "application/json",
            "data": data,
        }
        assert (len(result["data"]), _digest(result["data"])) == (size, "sha256:" + digest)
        assert _document_edge(graph, xid)["mediaType"] == DOCUMENT


def _linked_records(shared_records):
    records, documents = copy.deepcopy(shared_records)
    _record(records, "/")["snapshot"] = "linked"
    _record(records, V2)["document"] = {"mode": "external"}
    _record(records, V2)["entity"]["asseturl"] = "https://documents.example.test/unrecorded-v2"
    documents.pop(V2)
    return records, documents


def test_oci_linked_snapshot_requires_complete_internal_graph(tmp_path, shared_records):
    oci.build_layout(tmp_path, *_linked_records(shared_records))
    graph = _graph(tmp_path)
    reader = oci.FixtureLayout(tmp_path)
    summary = reader.validate()
    assert (summary["snapshot"], summary["objects"], summary["documents"]) == ("linked", 88, 2)
    assert {entry["digest"] for entry in reader.inventory} == set(graph["objects"])
    missing = _blob_path(tmp_path, _metadata_pair(graph, "version", V1)[1])
    missing.unlink()
    _error(
        lambda: oci.validate_layout(tmp_path), "invalid_package", f"Missing file: {missing}",
    )
    _error(
        lambda: oci.lookup_layout(tmp_path, V2, operation="document"),
        "unavailable", "Offline fixture helper does not fetch external documents",
    )


def test_oci_offline_complete_requires_complete_internal_graph(private_layout):
    graph = private_layout
    summary = oci.validate_layout(graph["path"])
    assert (summary["snapshot"], summary["objects"], summary["documents"]) == ("offline-complete", 89, 3)
    missing = _blob_path(graph["path"], _index(graph, "collection", "/independent/MAIN/assets"))
    missing.unlink()
    _error(
        lambda: oci.validate_layout(graph["path"]), "invalid_package", f"Missing file: {missing}",
    )
    assert oci.lookup_layout(graph["path"], V1, operation="document")["data"] == BASE_BYTES[V1]


def test_oci_external_only_document_cannot_be_offline_complete(tmp_path, shared_records):
    records, documents = _linked_records(shared_records)
    oci.build_layout(tmp_path, records, documents)
    graph = _graph(tmp_path)
    trace = []
    with patch.object(oci, "_read_file", wraps=oci._read_file) as read:
        linked = oci.FixtureLayout(tmp_path, trace=trace)
        assert linked.validate()["snapshot"] == "linked"
        _error(
            lambda: linked.lookup(V2, operation="document"),
            "unavailable", "Offline fixture helper does not fetch external documents",
        )
    assert all(item.args[0].is_relative_to(tmp_path) for item in read.call_args_list)
    assert _document_edge(graph, V2)["mediaType"] == EMPTY
    registry_config = _metadata_pair(graph, "registry", "/")[1]
    _edit_node(graph, registry_config, lambda record: record.__setitem__("snapshot", "offline-complete"))
    _error(
        lambda: oci.validate_layout(tmp_path), "invalid_package",
        "Offline-complete snapshot has external content",
    )
    _error(
        lambda: oci.lookup_layout(tmp_path, V2, operation="document"), "invalid_package",
        "Offline-complete snapshot has external content",
    )
    _record(records, "/")["snapshot"] = "offline-complete"
    _error(
        lambda: oci.build_layout(tmp_path / "rejected", records, documents),
        "invalid_package", "Offline-complete snapshot has external content",
    )
    assert not (tmp_path / "rejected").exists()


def _assert_required_closure(reader, graph):
    summary = reader.validate()
    assert summary["root"] == graph["root"]["digest"]
    assert summary["objects"] == len(graph["objects"])
    assert {item["digest"] for item in reader.inventory} == set(graph["objects"])
    for edge in graph["edges"]:
        data = reader.fetch(edge)
        assert data == graph["objects"][edge["digest"]][1]
        assert (len(data), _digest(data)) == (edge["size"], edge["digest"])
    return summary


def test_oci_offline_complete_closure_contains_exact_required_bytes(byte_layout):
    graph = byte_layout
    reader = oci.FixtureLayout(graph["path"])
    summary = _assert_required_closure(reader, graph)
    assert (summary["snapshot"], summary["records"], summary["documents"]) == ("offline-complete", 26, 5)
    observed = {}
    for xid, (data, size, digest) in BYTE_STATES.items():
        result = reader.lookup(xid, operation="document")
        assert result["snapshot"] == graph["root"]["digest"]
        assert result["resolved"] == xid
        assert result["data"] == data
        observed[xid] = (len(result["data"]), hashlib.sha256(result["data"]).hexdigest())
        assert _document_edge(graph, xid)["mediaType"] == DOCUMENT
    assert observed == {xid: (state[1], state[2]) for xid, state in BYTE_STATES.items()}
    placeholder = _node(graph, "registry", "/", MANIFEST)[1]["layers"][0]
    assert placeholder["mediaType"] == EMPTY
    assert reader.fetch(placeholder) == b"{}"
    assert placeholder["digest"] != _document_edge(graph, V2)["digest"]


def test_oci_federation_and_relationship_targets_are_not_implicitly_copied(tmp_path, shared_records):
    records, documents = copy.deepcopy(shared_records)
    foreign = {
        "xregurl": "https://foreign.example.test/registry",
        "federationprofiles": [{
            "name": "oci", "endpoint": "oci://foreign.example.test/team/catalog",
            "parameters": {"reference": "moving"},
        }],
        "relationship": {
            "registry": "https://foreign.example.test/registry",
            "target": "/documents/main/assets/remote",
        },
    }
    _record(records, CATALOG + "/versions/v1")["entity"].update(copy.deepcopy(foreign))
    oci.build_layout(tmp_path, records, documents)
    graph = _graph(tmp_path)
    trace = []
    with patch.object(oci, "_read_file", wraps=oci._read_file) as read:
        reader = oci.FixtureLayout(tmp_path, trace=trace)
        summary = _assert_required_closure(reader, graph)
        result = reader.lookup(CATALOG + "/versions/v1")
    assert result == {
        "snapshot": graph["root"]["digest"], "operation": "entity",
        "target": CATALOG + "/versions/v1", "pointer": "",
        "value": {**VERSION_ENTITIES[CATALOG + "/versions/v1"], **foreign, "self": "#"},
    }
    assert (summary["objects"], summary["records"], summary["documents"]) == (89, 24, 3)
    assert all(item.args[0].is_relative_to(tmp_path) for item in read.call_args_list)
    assert {key[2] for key in graph["nodes"]} == (
        {_fixture_routing_key(record["entity"]["xid"]) for record in records}
        | {
            "/categories", "/documents", "/independent", "/mirrors",
            "/categories/main/registries", "/documents/main/assets", "/documents/main/notes",
            "/independent/MAIN/assets", MIRRORS, ITEM + "/versions",
            "/documents/main/assets/CON/versions", NOTES + "/versions", CATALOG + "/versions",
        }
    )
    assert all("foreign.example.test" not in entry["path"] for entry in trace)


def test_oci_and_document_tree_share_a_captured_registry(tmp_path):
    records, documents = oci.sample_records()
    tree_records = []
    for original in records:
        record = copy.deepcopy(original)
        record.pop("formatversion")
        if record["kind"] == "registry":
            record["snapshot"] = {"scope": "/", "completeness": record["snapshot"]}
            record["resolvedmodelsource"] = record.pop("modelresolved")
        elif record["kind"] == "version":
            mode = record["document"]["mode"]
            record["document"] = {
                "kind": "none" if mode == "metadata-only" else "local"
            }
        tree_records.append(record)
    tree = DocumentTree(MemoryStore(encode_tree(tree_records, documents)))
    oci.build_layout(tmp_path, records, documents)
    native = oci.FixtureLayout(tmp_path)
    assert tree.model() == native.lookup("/", operation="model")["value"]
    assert tree.capabilities() == native.lookup("/", operation="capabilities")["value"]
    assert tree.metadata("/")["entity"]["registryid"] == "fixture-offline"
    assert native.lookup("/")["value"]["registryid"] == "fixture-offline"
    expected = {
        "/dirs/main/files/sample": b'{"type":"string"}\n',
        "/dirs/main/files/sample/versions/v2": b'{"type":"number"}\n',
        "/dirs/main/files/binary": b"\x00\x01\x7f\x80\xff\r\n",
        "/dirs/main/files/empty": b"",
        "/imports/shared/files/alias": b'{"type":"string"}\n',
    }
    for target, data in expected.items():
        assert tree.document(target) == data
        assert native.lookup(target, operation="document")["data"] == data
    for target in ("/dirs/main/files/chain", "/dirs/main/files/dangling"):
        with pytest.raises(FederationError) as document_error:
            tree.document(target)
        with pytest.raises(FederationError) as oci_error:
            native.lookup(target, operation="document")
        assert document_error.value.code == oci_error.value.code == "not_found"
    metadata_only = "/dirs/main/notes/info"
    for read in (lambda: tree.document(metadata_only),
                 lambda: native.lookup(metadata_only, operation="document")):
        with pytest.raises(FederationError) as error:
            read()
        assert error.value.code == "unsupported_operation"


def test_oci_tag_moves_but_existing_reader_keeps_immutable_pin(tmp_path):
    records, documents = oci.sample_records()
    first = oci.build_layout(tmp_path, records, documents, reference="moving")
    pinned = oci.FixtureLayout(tmp_path, "moving")
    documents["/dirs/main/files/sample/versions/v1"] = b"changed\n"
    second = oci.build_layout(tmp_path, records, documents, reference="moving")
    assert first["digest"] != second["digest"]
    target = "/dirs/main/files/sample"
    result = pinned.lookup(target, operation="document")
    assert result["data"] == b'{"type":"string"}\n'
    assert result["snapshot"] == first["digest"]
    assert result["resolved"] == target + "/versions/v1"
    assert sum(item["route"] == "layout" for item in pinned.trace) == 2
    fresh = oci.FixtureLayout(tmp_path, "moving").lookup(target, operation="document")
    assert fresh["data"] == b"changed\n"
    assert fresh["snapshot"] == second["digest"]


@pytest.mark.parametrize("reference", ["offline", "linked"])
def test_oci_registry_context_survives_colliding_xids(reference, oci_sample_root):
    reader = oci.FixtureLayout(oci_sample_root / "layout", reference)
    model = reader.lookup("/", operation="model")["value"]
    assert set(model) == {"model", "modelsource", "resolvedmodelsource"}
    assert model["modelsource"]["groups"]["imports"]["ximportresources"] == ["/dirs/files"]
    assert model["model"]["groups"]["dirs"]["resources"]["files"]["metaattributes"]["xref"]["type"] == "xid"
    root = reader.lookup("/")["value"]
    assert root["registryid"] == "fixture-" + reference
    result = reader.lookup("/dirs/main/files/sample/versions/v1", operation="document")
    assert result["data"] == b'{"type":"string"}\n'
    assert result["target"] == "/dirs/main/files/sample/versions/v1"
    assert result["snapshot"] == reader.root_digest
    other = oci.FixtureLayout(oci_sample_root / "layout", "linked" if reference == "offline" else "offline")
    assert reader.root_digest != other.root_digest


@pytest.mark.parametrize("target", [
    "/dirs/main/files/alias", "/imports/shared/files/alias",
    "/dirs/main/files/dangling", "/dirs/main/files/chain",
])
def test_oci_alias_metadata_is_unexpanded_and_source_relative(target, oci_sample_root):
    reader = oci.FixtureLayout(oci_sample_root / "layout", "offline")
    metadata = reader.lookup(target)["value"]
    assert set(metadata) == {"fileid", "self", "xid", "meta", "metaurl"}
    assert metadata["fileid"] == target.rsplit("/", 1)[1]
    assert metadata["xid"] == target
    assert metadata["self"] == "#"
    assert metadata["metaurl"] == "#/meta"
    assert metadata["meta"]["xid"] == target + "/meta"
    assert set(metadata["meta"]) == {"fileid", "self", "xid", "xref"}
    for operation, suffix in (("entity", "/versions/v1"), ("collection", "/versions")):
        with pytest.raises(FederationError) as error:
            reader.lookup(target + suffix, operation=operation)
        assert error.value.code == "unsupported_operation"
        assert "cannot_doc_xref" in str(error.value)


@pytest.mark.parametrize("selector,target,code", [
    ({"label": "stage", "value": "rEaDy"}, "/dirs/main", None),
    ({"label": "empty", "value": ""}, "/dirs/main", None),
    ({"label": "missing", "value": ""}, None, "not_found"),
    ({"label": "stage", "value": "R*"}, None, "not_found"),
])
def test_oci_label_selection_preserves_literal_core_comparison(selector, target, code, oci_sample_root):
    trace = []
    reader = oci.FixtureLayout(oci_sample_root / "layout", "offline", trace=trace)
    if code:
        with pytest.raises(FederationError) as error:
            reader.lookup("/dirs", operation="collection", selector=selector)
        assert error.value.code == code
    else:
        result = reader.lookup("/dirs", operation="collection", selector=selector)
        assert result["target"] == target
        assert result["value"]["dirid"] == "main"
    assert all(entry.get("mediaType") not in (DOCUMENT, EMPTY) for entry in trace)


def test_oci_label_ambiguity_on_later_shard_is_not_first_match_success(tmp_path):
    records = _group_records(["a", "b", "c", "d", "e"])
    for record in records:
        if record["entity"]["xid"] in ("/emptygroups/a", "/emptygroups/e"):
            record["entity"]["labels"] = {"stage": "ready"}
    oci.build_layout(tmp_path, records, page_size=2)
    reader = oci.FixtureLayout(tmp_path)
    with pytest.raises(FederationError) as error:
        reader.lookup("/emptygroups", operation="collection",
                      selector={"label": "stage", "value": "READY"})
    assert error.value.code == "ambiguous"
    last = _graph(tmp_path)
    last_config = _metadata_pair(last, "group", "/emptygroups/e")[1]
    assert last_config["digest"] in {entry.get("digest") for entry in reader.trace}


@pytest.mark.parametrize("source,target,code", [
    ("/dirs/main/files/alias", "https://other.example.com/registry", "invalid_package"),
    ("/dirs/main/files/alias", "/dirs/main/notes/info", "invalid_package"),
])
def test_oci_rejects_remote_and_wrong_model_type_xref(tmp_path, source, target, code):
    records, documents = oci.sample_records()
    _record(records, source + "/meta")["entity"]["xref"] = target
    with pytest.raises(FederationError) as error:
        oci.build_layout(tmp_path, records, documents)
    assert error.value.code == code
    assert not (tmp_path / "index.json").exists()


def test_oci_case_insensitive_sibling_collision_is_rejected_before_publication(tmp_path):
    with pytest.raises(FederationError) as error:
        oci.build_layout(tmp_path, _group_records(["A", "a"]))
    assert error.value.code == "invalid_package"
    assert str(error.value) == "Case-insensitive sibling ID collision"
    assert not (tmp_path / "index.json").exists()


@pytest.mark.parametrize("max_depth,max_objects", [(1, 100_000), (64, 1)])
def test_oci_traversal_limits_fail_without_partial_success(max_depth, max_objects, oci_sample_root):
    reader = oci.FixtureLayout(
        oci_sample_root / "layout", "offline", max_depth=max_depth, max_objects=max_objects
    )
    with pytest.raises(FederationError) as error:
        reader.lookup("/dirs/main/files/sample/versions/v2", operation="document")
    assert error.value.code == "limit_exceeded"
    assert all(entry.get("mediaType") != DOCUMENT for entry in reader.trace)


@pytest.mark.parametrize("invalid", [
    b'{"duplicate":1,"duplicate":2}', b'{"a":NaN}', b'{"a":Infinity}',
    b'{"a":1e10000}', b"\xef\xbb\xbf{}", b'{"a":"\xff"}',
])
def test_oci_invalid_json_is_rejected_before_interpretation(invalid):
    with pytest.raises(FederationError) as error:
        oci.decode_json(invalid)
    assert error.value.code == "invalid_package"


def test_oci_embedded_content_retains_origin_and_relative_document_base(tmp_path):
    records, documents = oci.sample_records()
    version = _record(records, "/dirs/main/files/sample/versions/v1")
    version["document"].update({
        "origin": "https://source.example.com/files/main.json",
        "base": "https://source.example.com/files/",
    })
    oci.build_layout(tmp_path, records, documents)
    result = oci.FixtureLayout(tmp_path).lookup("/dirs/main/files/sample", operation="document")
    assert result["origin"] == "https://source.example.com/files/main.json"
    assert result["base"] == "https://source.example.com/files/"
    assert result["data"] == b'{"type":"string"}\n'
    assert "fileurl" not in version["entity"]


@pytest.mark.parametrize("field,value", [
    ("formatversion", 2), ("specversion", "1.0-rc2"),
])
def test_oci_unknown_format_and_core_versions_fail_before_publication(tmp_path, field, value):
    records, documents = oci.sample_records()
    if field == "formatversion":
        records[0][field] = value
    else:
        records[0]["entity"][field] = value
    with pytest.raises(FederationError) as error:
        oci.build_layout(tmp_path, records, documents)
    assert error.value.code == "unsupported_version"
    assert not (tmp_path / "index.json").exists()


@pytest.mark.parametrize("limit,value", [
    ("max_depth", 0), ("max_depth", -1),
    ("max_objects", 0), ("max_objects", -1),
])
def test_oci_nonpositive_budgets_reject_before_storage_access(limit, value, oci_sample_root):
    with patch.object(oci, "_read_file", side_effect=AssertionError("Unexpected I/O")):
        with pytest.raises(FederationError) as error:
            oci.FixtureLayout(oci_sample_root / "layout", "offline", **{limit: value})
    assert error.value.code == "limit_exceeded"


@pytest.mark.parametrize("blob,reference,expected", [
    (False, "release-1", "https://registry.example.com:5443/v2/team/catalog/manifests/release-1"),
    (False, "sha256:" + "1" * 64, "https://registry.example.com:5443/v2/team/catalog/manifests/sha256:" + "1" * 64),
    (True, "sha256:" + "2" * 64, "https://registry.example.com:5443/v2/team/catalog/blobs/sha256:" + "2" * 64),
])
def test_oci_distribution_routes_preserve_native_manifest_blob_distinction(blob, reference, expected):
    assert oci.distribution_url("oci://registry.example.com:5443/team/catalog",
                                reference, blob=blob) == expected


# Independent baseline retained before sample-tree removal.
LEGACY_EXPECTED = {'roots': {'offline': {'registryid': 'fixture-offline',
                       'snapshot': 'offline-complete',
                       'digest': 'sha256:c937f902c54ca9c63e510bab3b4ec07ec3775ad338ac030ac93d916a736efba6',
                       'size': 903,
                       'objects': 99,
                       'indexes': 44,
                       'manifests': 25,
                       'records': 25,
                       'documents': 4},
           'linked': {'registryid': 'fixture-linked',
                      'snapshot': 'linked',
                      'digest': 'sha256:dff871378d2678ee851fb7d97bae5a6b69b05c3d668f224a2f97127e8e8dee88',
                      'size': 903,
                      'objects': 98,
                      'indexes': 44,
                      'manifests': 25,
                      'records': 25,
                      'documents': 3}},
 'documents': [{'xid': '/dirs/main/files/binary/versions/v1',
                'size': 7,
                'digest': 'sha256:47a8404dd5bb287e70354f4aa0f7bf250e4fefe66a72cf2ac5475a802fd45968',
                'base64': 'AAF/gP8NCg==',
                'mediaType': 'application/octet-stream'},
               {'xid': '/dirs/main/files/empty/versions/v1',
                'size': 0,
                'digest': 'sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
                'base64': '',
                'mediaType': 'text/plain; charset=utf-8'},
               {'xid': '/dirs/main/files/sample/versions/v1',
                'size': 18,
                'digest': 'sha256:85803e087e684bdab3e5d6c2dd1af627da83382db625be9a42aea3d4d06539be',
                'base64': 'eyJ0eXBlIjoic3RyaW5nIn0K',
                'mediaType': 'application/schema+json'},
               {'xid': '/dirs/main/files/sample/versions/v2',
                'size': 18,
                'digest': 'sha256:e562cc019db9f5cb554d77b7cdd6b0e0640c1fd7a045e36b1b164879a24ac87d',
                'base64': 'eyJ0eXBlIjoibnVtYmVyIn0K',
                'mediaType': 'application/schema+json'}],
 'defaultversionid': 'v1',
 'document_expectations_apply_to': 'offline',
 'linked_external_version': '/dirs/main/files/sample/versions/v2',
 'empty_collection': '/emptygroups',
 'metadata_only': '/dirs/main/notes/info',
 'local_alias': '/dirs/main/files/alias',
 'imported_type_alias': '/imports/shared/files/alias',
 'dangling_alias': '/dirs/main/files/dangling',
 'nontransitive_alias': '/dirs/main/files/chain'}


# Independent baseline retained before sample-tree removal.
LEGACY_BLOB_HASHES = ('00e22b0a556fdea2f7f40d5e739069bd3b4d1ccc5838c7d0645deddd0b15dc34',
 '05a2ca64985bd015891690b0f1f01f4425ed4aefe7be33da08509a92afe585aa',
 '0a0e6bece3e0c61f0a1b2c494545275833723d9b02019a018279d3bf90dba0c4',
 '0a4baca4050fae26fcf8d3e59b83cf9c3309fe4d9ea14de6663f98033881b38a',
 '0d31b1695f909e69da301ea224cef8e4e62f2c3804258a787f1bf5c59d0e0e6c',
 '0fd794bad67501005c0b85a58a3583db86b4ffd88858f247f87cea121513657d',
 '143776b1f87d62ba6189799fd8355b2485a8e0d4c64ed191323dceee486275e5',
 '16583c91dab71e6bd9a17c7bb0b09087a40d2bacd9b12d18a9ee3f244430830b',
 '1a5dfdbd8b9526d85d6d5218c249cd5d24ec3a6fda4e59ed6be11489a1a93f98',
 '1c27b4aaa33dd535030759871e6ab834c009cfae539f716ebcb9ce83d43de5e0',
 '1df66cd6db777093af77f65f41980e8afb1f83b45ff0c2854d54fab06e081371',
 '245b36682117da9ba2bdf3eec67db51fdb0a9203116dc6390f4170f1b68d3561',
 '26ce2dcae73545a27dc162e0b34af35dc19838d738eb451315bed641d2151d7c',
 '277207f15b1951090e9ee7ee999b81c4bbcab5bebfe624abba1e99bc43e310c1',
 '27c8676b2435c3f0e34465a1d43ed2176743b504991bd6beefa23680f88088a0',
 '27eea50d50157aa67ba451c20c0edd0ce64c68ce0c968e394009e69825290d36',
 '295a081643d334f73d00466295e37aa2c92c0347a8932529828a568df7e6b4a3',
 '29bb2c1054f8a7a401d8294f111102190135910d0bd7e97f56652822d3e69373',
 '2a7e0fb137f41cd97ed41cb53ba4d795580863beca07f18f8925e6501e313639',
 '2eb19679df02288f3e66e53eba56fab491244b301550e010d4114061d04aecf5',
 '2f2daaf07deb62b104575e14bb630ecd8f866e56f0dc47edd681526f50606ec1',
 '3311d4b1bb8e790703c637d1cd0d12f482b34f94f927e97b97d1a1978491ab22',
 '353e1cbf3f3ffc146fc18c7606b5656e6a009e614674b269d96ca3e6c1ea37db',
 '3b47f8f5d33b39000113881c987370486f6e7b708d45544392618e6261ff3b0c',
 '3ece5ed6bce0ab666c3c4a72625dba1b589233cdd28f14653a90f6948c2f6dc8',
 '3fd9f557e3ccfc24ea18c4f6ee5a5ef24464f05743c02e1327eadbdb40f93dfb',
 '40b170246a762f0a0088d52a048b5533bceaf35285323486410e67686c85047a',
 '44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a',
 '451cb49adc8484d1c6e065b7adb86300351758b170dc6643faac4c548c3bd5c0',
 '47a8404dd5bb287e70354f4aa0f7bf250e4fefe66a72cf2ac5475a802fd45968',
 '48304a2f5296fd7a0d3a02ce8ade5d70eebb9e63aff0d20e3fde2be91f373d19',
 '4c34fe21f8878bd389481b63f4e7824c3126133a54e44e29f840befcbcf300fe',
 '5412b2c8b0b83e0aba36a830cb0a920170916f13752568a33f9c75cc55d293b6',
 '5615c98e76459e1f3415f04a279669deabeb3a5c7960d4ee38e645872c4aec2c',
 '59357baeb9e4bb9572a86a9cce6d62cff33e95dc71334e458a881d1ee94c9331',
 '59565c6202213f07406e48408e1ec92faca7e8461e2fcbb5124bbf2063b0f7b9',
 '5993ec37018140b07970bebf1f2f4064343c282f3d0741e9e7508936bdfc9d4d',
 '609242d9f54c622392108028bcf2a5256200f36718d92622950bd36bb4604462',
 '617c2781bd191aa0397f99ed92715a79bb0ba061ae6693d045b35b969f35e1d2',
 '63495a05486a49c7877f949dcd602eddc40e848329a64d00d6bdc11b76ae7d79',
 '643cfb6ca41afe6c0440ce8b210987e7a3b90955b3596f2a1635c1a75f0d6768',
 '6590f275badf5c393defd68535e391b58739e399cd543aaff1905bd86e3a76ae',
 '673f0ed44ef9a11dadd3396667600a7aade32d30e161e63a34fffa4f4c2eb6e1',
 '69d6d98ee306291fa28c4438090636ee83524b3794bf5b1c8034053681777947',
 '6b26127ebdd01140a16b0a6900863411bd083bf41519799462f1fada1b78fb37',
 '6ccb4af7cd65c2059d090f10d4d1b083eb27215ffaa41dfaa80c3895b51db9da',
 '7321cbe88ee2dca9c70fb3f4020cb6811676547a5f688befdc6f7e153a4b91c6',
 '77038f6d97d9eb75c6936fa3bcb8c540f87f4c4154f9afadd40671ddc7e1aa08',
 '792822629fffa09fc45efd1281aadb88d502d9cfd596407be3fcd16a4f729030',
 '7a38613fc602394aa1f2973ebb73cb52f563632d270bc82f1777eea0e6e23d39',
 '7a38fb5df71c413fdf16d14a9388e5e179b9a60422875b3a159934b26881c6ea',
 '7ac0374e78ccd6c7ec36772c108587623c68134e46cbd052f7bc36759f8f9ceb',
 '7c9437a2acb55dfd866aa6198d70be51021b12744d71e505d332c1ab8f79ab60',
 '7d234cc5817981ad09a1358b72362305de557db3cf4fc4fbbd480f610c9fdd44',
 '7d56303bc79a61149292dfec347d2e64ae6e090afb5e498ebc197a32aa5568d4',
 '82b0ac671cb79692f3b369cb0967b43fe50ecc61bd1dbd0915afdde08f75d473',
 '85803e087e684bdab3e5d6c2dd1af627da83382db625be9a42aea3d4d06539be',
 '869e958dca095889542f43143be8ec85148267bda38a01780d12d24b695bdf3e',
 '8743420cf07b85c514b41d385d8be1aaa76e0af17a31c9ae23c62436f4c6727b',
 '89e6bd896f4d8a474873e3f816fa0f4e151ecd4168b06c607f93a1f59c1dfbd2',
 '8b12b7aede7c57cede44697e325f2936960583fa02ef734194a493749872df06',
 '8f0fb9081580ad0291b2230b69dd47b3aba4efa0237d770d6f75e89370b195e2',
 '8fc7d555f4467708b46ae97678d5e32528fcd92ce278a7b5d97aaa57096d5eea',
 '942d27ec939867e4ece6b98daf49aa5145b89efba8fe3c3e17892db768892eae',
 '96babed201dede192612b134d0b83cc90a8d9e5c8a52e1fb724bec3351781566',
 '975db55338a8c3bbd22ead5a2079451c3c11909da04762339977edb530de0837',
 '9eb6e111e1fa7792207be842512705a7bc20e08d77c3550d71d779640e463fe1',
 'a2af5f6eea9081df414adc1dccc1f6fd32ecefb8c6d644cf126591d94ff97fa3',
 'a84e6bf8af44eeeded17d3c628c8ec762e5ce34ef1570f316afd4305e7fd9db7',
 'a8bca48ffd091851fcc32a73e4c06992db948d8dcead9550c4cbc3ce67399635',
 'ab4e0c7a9da03192c16b3b148277085f0fa1431f7fea91ae020f38cb4a6aad99',
 'af6422ebdc770ab37ab3bbaaa1e7469146dbc3acc2523cb87cc554aa00cb8713',
 'b0d8c81408e7e037cf3da95cfc2257783a71cdbd693e8701cdb1c1b2ff4ff2e8',
 'b4c432b24f90db7afc9264b73d71f8a9045a08717c248043a6a8cd8cf7b75f39',
 'b6906b2727d8912451fd6f74422269aed1b03976e16cf76c6dd49641ab59bf44',
 'b6be2114974b3057496715c3818c9f2100ef21344a2e5f28e9ef74c73344151c',
 'b780a08f29e401e46ab8bb495c82ea4c4aafa0590ae04d4ef6f7a43108792c52',
 'b8545a900728c0125fb092cdc5f2a8333cbc1a4596d7c2d95a088999ea31a3d7',
 'b8786ba073b0998562c0d16fc74cf55856c2ddc2587bdfc864dd2a5ed7828fc9',
 'bbb8431c731d4be5db0dda92683801758a2dc25a2fc7e9908630eccdcd4d5adf',
 'bd619a454c1060773adbd6a0613b1d26fc451d1f5720e8345d0b96c47af23c37',
 'bd73dd742e5c16089d2b72a92d4a1e2a01dae79216c7f234c294a58ba9bfeefd',
 'c1812842e586a27ae9d1037349bcd4c5ae4a819bdb07017dc3d0bb8b5187d119',
 'c525b1845cc29437930fa72781e0a1603f3259d4626afb4d14d9b02410f5e7dd',
 'c59c80b59db1c9fd817e354425704933d30718b3958023b81e095f409a86bf7f',
 'c8fab8ed1186fae51a4c2d12f6a0b9bcd1835d2d3d70100262f5bff9a6368bd5',
 'c937f902c54ca9c63e510bab3b4ec07ec3775ad338ac030ac93d916a736efba6',
 'cc3a2eb3ab0b35f2a8309aed0851c4735c0f37cf601c79ce98f968162172fe6b',
 'd5f2a537003f14c58cb65ada4a6d8b6cec7178af9192733afd2edf639ae5098c',
 'd7bc2f306e167fa86b0e6f64b62e0ccdeb91b50c99eba2e1c6a49d4846d582a1',
 'dab7faf03ac8e7ea11f6ffa3db448d742432fc9ed09dcbc7ca3a5f97c5475bfa',
 'dc7b31ff81ea06249dabed96309c2749848f060df2408eedd5da90ff6ea2bf7e',
 'dda3965e8f06b6136e89a96fb4f100c94e7ca2f134cdf92bbd3565e65ace7e29',
 'dff871378d2678ee851fb7d97bae5a6b69b05c3d668f224a2f97127e8e8dee88',
 'e00b8e129803ca40c4b35a1db081ddede5ec668bc166680350dbd90a0d84bf28',
 'e1def65f2d844f818e0af6d974abb8d48f6812a56fada333c472f6e709e72787',
 'e2b7f1dfdb131ccd547802766a7dbbc86162e188ec1ad281668021e23173a928',
 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
 'e562cc019db9f5cb554d77b7cdd6b0e0640c1fd7a045e36b1b164879a24ac87d',
 'e570e63cb5b54b80fa10bfbffde792a4a99d9539e4848c9faa242eaccd4472e4',
 'e594a3de4fd8587d20544d4a4719ef8e76084482983aea623e2a3f00a3bcda61',
 'e7bdec4d110824ef20c3e23fd08949fd473a05ff1d6b99c56e218cb2a3906b7f',
 'e9380249b79341b160c89e893213792a26793e8186ac8f848ec84ec60706e578',
 'ece9374b3c5cf08f6018f70a947cc26845d6b6bc5cd5dfb458a936d10eb683dd',
 'eebb063319204754b9460f9a59f70e5a188108910f4d311b4bca6b5def0c2754',
 'efdc9a345050733e94352c11c97d10a6611182ee7b4fe18b73155bed0b4fe28f',
 'f13787d09bfaf2c363bb85a0fa10ccf2eea60ee192bef88235dc7c11ea1f4cb2',
 'f2ec9eb4ca89c231b6240992b8ded217105388d87532b6777b8ae2d769211976',
 'f5ec1d6f6dd01943e9c5f43ae196bdf0aeb9ed58aacacb0e97f1fbd5c51dd4e0',
 'f86a54fd29327feca1af033dbaf76ce7191573da03fe163c6896dcff449adc72',
 'fa6ab41734d3578c6dca43f37880a3510cd725ab6ec481ed90acbecca2f6a149',
 'fb35bdd05670b835f1c50cc1876922e659d9c3818ec095e22abc89ff69a2fb18',
 'fb9d956868e21959e7d1048552d2feccda06b3a76ea50f77a70974ab4520467b',
 'fc9fb8244eea107277f53ecfcea6c7f38808f273c449e803f39a30f0b2a8a82b',
 'fd6b1499e8732efdc575ef3df04b8288f646fe2effee07c80e7ccd3f2e540cc6')
