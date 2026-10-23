"""SPEC005: decoded mapping identities and canonical native OCI routing keys."""

import hashlib
import json
from pathlib import Path
from urllib.parse import unquote

import pytest

from workingdrafts.federation.tools.federation_examples import FederationError, validate_xid
from workingdrafts.bindings.tools import mapping_examples as mapping
from workingdrafts.bindings.tools import oci_examples as oci


ROOT = Path(__file__).resolve().parents[3]
MAPPING = ROOT / "workingdrafts" / "bindings" / "samples" / "mapping"
OCI = ROOT / "workingdrafts" / "federation" / "samples" / "oci" / "layout"
PREFIX = "io.xregistry.oci."


def _leaf(xid, keys, lower="", upper=""):
    return {
        "schemaVersion": 2,
        "mediaType": oci.INDEX_MEDIA_TYPE,
        "artifactType": oci.ARTIFACT_TYPES["collection"],
        "annotations": {
            PREFIX + "version": "1",
            PREFIX + "kind": "collection",
            PREFIX + "xid": xid,
            PREFIX + "mode": "leaf",
            PREFIX + "lower": lower,
            PREFIX + "upper": upper,
        },
        "manifests": [
            {
                "mediaType": oci.INDEX_MEDIA_TYPE,
                "digest": "sha256:" + "0" * 64,
                "size": 1,
                "annotations": {PREFIX + "role": "entity", PREFIX + "xid": key},
            }
            for key in keys
        ],
    }


def _bytes(node):
    return json.dumps(node, ensure_ascii=True, separators=(",", ":")).encode("utf-8")


@pytest.mark.parametrize("operation", ["metadata", "document"])
def test_frozen_mapping_uri_selectors_preserve_raw_identity_and_exact_bytes(operation):
    tree = mapping.DocumentTree(mapping.FileStore(MAPPING))
    target = "/%64ocuments/%6dain/%61ssets/CON/%76ersions/a%3ab%40c."
    if operation == "document":
        assert tree.document(target) == b"\x00\x01\xff\x7f\n"
    else:
        result = tree.metadata(target)
        assert result["entity"]["xid"] == "/documents/main/assets/CON/versions/a:b@c."
        assert result["entity"]["versionid"] == "a:b@c."
        assert result["entity"]["self"] == "#/entity"
    assert tree.root_sha256 == "7e4c37ca61b2b875ee055a8fc67e5c90c48b344689823a12dc1fb0a6e33232bf"


def test_frozen_mapping_collection_keys_are_decoded_and_pointer_targets_exist():
    tree = mapping.DocumentTree(mapping.FileStore(MAPPING))
    result = tree.collection("/documents/%6dain/assets/CON/%76ersions")
    assert result["xid"] == "/documents/main/assets/CON/versions"
    assert set(result["entities"]) == {"a:b@c."}
    entity = result["entities"]["a:b@c."]
    pointer = unquote(entity["self"][1:]).split("/")[1:]
    selected = result
    for part in pointer:
        selected = selected[part.replace("~1", "/").replace("~0", "~")]
    assert selected["versionid"] == "a:b@c."


def test_byte_range_counterexample_requires_rejecting_the_legacy_leaf():
    stored = "/items/%61%3Aone"
    canonical = "/items/a%3Aone"
    boundary = "/items/a"
    assert validate_xid(stored) == stored
    assert stored.encode("utf-8") < boundary.encode("utf-8") <= canonical.encode("utf-8")
    left = _leaf("/items", [stored], upper=boundary)
    right = _leaf("/items", ["/items/z"], lower=boundary)
    assert oci.check_index(_bytes(right))["manifests"][0]["annotations"][PREFIX + "xid"] == "/items/z"
    with pytest.raises(FederationError) as failure:
        oci.check_index(_bytes(left))
    assert failure.value.code == "invalid_package"


@pytest.mark.parametrize(
    "key,lower,upper",
    [
        ("/items/a:one", "", ""),
        ("/items/a%3aone", "", ""),
        ("/items/%61%3Aone", "", ""),
        ("/items/a%3Aone", "/items/a:one", ""),
        ("/items/a%3Aone", "", "/items/z%40last"),
    ],
)
def test_oci_routing_keys_and_both_finite_endpoints_require_canonical_spelling(key, lower, upper):
    node = _leaf("/items", [key], lower, upper)
    if upper:
        node["annotations"][PREFIX + "upper"] = "/items/z@last"
    with pytest.raises(FederationError) as failure:
        oci.check_index(_bytes(node))
    assert failure.value.code == "invalid_package"


def test_canonical_uri_routing_keeps_exact_encoded_byte_count():
    data = _bytes(_leaf("/items", ["/items/a%3Aone", "/items/a0"]))
    assert oci.check_index(data)["annotations"][PREFIX + "xid"] == "/items"
    exact = data + b" " * (1_048_576 - len(data))
    assert oci.check_index(exact)["manifests"][0]["annotations"][PREFIX + "xid"] == "/items/a%3Aone"
    with pytest.raises(FederationError) as failure:
        oci.check_index(exact + b" ")
    assert failure.value.code == "limit_exceeded"


def test_fixture_documents_are_independent_of_the_uri_encoder():
    expected = b'{"type":"string"}\n'
    digest = "85803e087e684bdab3e5d6c2dd1af627da83382db625be9a42aea3d4d06539be"
    actual = (OCI / "blobs" / "sha256" / digest).read_bytes()
    assert actual == expected
    assert hashlib.sha256(actual).hexdigest() == digest
