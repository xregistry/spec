"""Offline conformance tests for the native OCI snapshot fixture APIs."""

import copy
import hashlib
import json
from unittest.mock import call, patch

import pytest

from workingdrafts.bindings.tools import oci_examples as oci
from workingdrafts.bindings.tools.mapping_examples import sample_records as document_sample_records
from workingdrafts.federation.tools.federation_examples import FederationError


INDEX = "application/vnd.oci.image.index.v1+json"
MANIFEST = "application/vnd.oci.image.manifest.v1+json"
EMPTY = "application/vnd.oci.empty.v1+json"
PREFIX = "io.xregistry.oci."


def test_generated_offline_oci_preserves_fixed_pin_closure_and_document_bytes(tmp_path):
    oci.build_layout(tmp_path, *oci.sample_records(), reference="offline", page_size=2)
    reader = oci.FixtureLayout(tmp_path, "offline")
    summary = reader.validate()
    digest = "sha256:c937f902c54ca9c63e510bab3b4ec07ec3775ad338ac030ac93d916a736efba6"
    assert reader.root_digest == digest
    assert reader.lookup("/")["value"]["registryid"] == "fixture-offline"
    assert len((tmp_path / "blobs" / "sha256" / digest[7:]).read_bytes()) == 903
    assert {key: summary[key] for key in (
        "root", "snapshot", "objects", "indexes", "manifests", "records", "documents",
    )} == {
        "root": digest, "snapshot": "offline-complete", "objects": 99,
        "indexes": 44, "manifests": 25, "records": 25, "documents": 4,
    }
    graph = _graph(tmp_path, "offline")
    assert {item["digest"] for item in reader.inventory} == set(graph["objects"])
    for name, data, size, expected_digest in (
        ("sample", b'{"type":"string"}\n', 18,
         "sha256:85803e087e684bdab3e5d6c2dd1af627da83382db625be9a42aea3d4d06539be"),
        ("binary", b"\x00\x01\x7f\x80\xff\r\n", 7,
         "sha256:47a8404dd5bb287e70354f4aa0f7bf250e4fefe66a72cf2ac5475a802fd45968"),
        ("empty", b"", 0,
         "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
    ):
        xid = f"/dirs/main/files/{name}/versions/v1"
        result = reader.lookup(xid, operation="document")
        assert result["data"] == data
        assert len(result["data"]) == size
        assert _digest(result["data"]) == expected_digest


ITEM = "/documents/main/assets/item"
V1 = ITEM + "/versions/v1"
V2 = ITEM + "/versions/v2"
BINARY = "/documents/main/assets/CON/versions/a:b@c."
STAMP = {
    "epoch": 1,
    "createdat": "2026-09-04T00:00:00Z",
    "modifiedat": "2026-09-04T00:00:00Z",
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
BASE_BYTES = {
    V1: b'{"hello":"world"}\n',
    V2: b"",
    BINARY: b"\x00\x01\xff\x7f\n",
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


def _record(records, xid):
    return next(record for record in records if record["entity"]["xid"] == xid)


def _blob_path(path, descriptor):
    return path / "blobs" / "sha256" / descriptor["digest"][7:]


def _write_blob(path, data, media_type):
    descriptor = {"digest": _digest(data), "size": len(data), "mediaType": media_type}
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


@pytest.mark.parametrize("versionid,bounds", [
    pytest.param("m", [("m", ""), ("m", "z")], id="at-m-lower-inclusive-upper-exclusive"),
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


def test_oci_document_digest_mismatch_is_rejected(private_layout):
    graph = private_layout
    payload = _document_edge(graph, V1)
    path = _blob_path(graph["path"], payload)
    original = path.read_bytes()
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


def _linked_records(shared_records):
    records, documents = copy.deepcopy(shared_records)
    _record(records, "/")["snapshot"] = "linked"
    _record(records, V2)["document"] = {"mode": "external"}
    _record(records, V2)["entity"]["asseturl"] = "https://documents.example.test/unrecorded-v2"
    documents.pop(V2)
    return records, documents


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


# Independent baseline retained before sample-tree removal.


# Independent baseline retained before sample-tree removal.
