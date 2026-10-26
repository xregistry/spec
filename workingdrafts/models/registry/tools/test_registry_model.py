"""Offline conformance checks for the versioned Registry catalog model."""

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from workingdrafts.federation.tools.federation_examples import (
    FederationError, select_profile, select_version,
)


ROOT = Path(__file__).resolve().parents[4]
REGISTRY_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = REGISTRY_DIR / "model.json"
SCHEMA_BASE = "https://xregistry.io/workingdrafts/models/registry/schemas/"
FORMATS = {
    "json-schema": "document-schema.json",
    "json-structure": "document-schema.struct.json",
    "openapi": "openapi.json",
}
BUILTINS = {"http", "oci", "git", "file", "opcua"}
HTTP = {"name": "http", "endpoint": "https://registry.example.test/root"}
OCI = {
    "name": "oci",
    "endpoint": "oci://artifacts.example.test/team/catalog",
    "parameters": {"reference": "stable"},
}
GIT = {
    "name": "git",
    "endpoint": "https://git.example.test/team/catalog.git",
    "parameters": {"revision": "0123456789abcdef0123456789abcdef01234567"},
}
FILE = {
    "name": "file",
    "endpoint": "file:///C:/catalog-cache/registry/",
    "parameters": {"layout": "document-tree"},
}
UA = {
    "name": "opcua",
    "endpoint": "opc.tcp://ua.example.test:4840/xregistry",
    "parameters": {
        "registryroot": "nsu=urn:example:xregistry;s=Registries/Catalog",
        "applicationuri": "urn:example:ua:catalog-server",
    },
}
EXTENSION = {
    "name": "com.example.discovery",
    "endpoint": "urn:example:catalog:discovery",
    "parameters": {"exampleextension": {"mode": "KeepCase", "values": [0, False, ""]}},
}


def _sample(filename):
    return json.loads((REGISTRY_DIR / "samples" / filename).read_text(encoding="utf-8"))


def _run_generator(directory, schema_type, model_path=MODEL_PATH):
    directory.mkdir(parents=True, exist_ok=True)
    output = directory / FORMATS[schema_type]
    command = [
        sys.executable, "-B", str(ROOT / "tools" / "schema-generator.py"),
        "--type", schema_type, "--output", str(output),
    ]
    if schema_type in ("json-schema", "json-structure"):
        command.extend(["--schema-id", SCHEMA_BASE + FORMATS[schema_type]])
    if schema_type == "json-structure":
        command.extend(["--schema-name", "RegistryOfRegistriesDocument"])
    command.append(str(model_path))
    result = subprocess.run(
        command,
        cwd=ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result, output


def _generate(directory, schema_type, model_path=MODEL_PATH):
    result, output = _run_generator(directory, schema_type, model_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    assert result.stdout == f"> {model_path} as '{schema_type}'\n"
    raw = output.read_bytes()
    return json.loads(raw), raw


def _assert_federation_error(entry, code, message, supported=BUILTINS, name=None):
    with pytest.raises(FederationError) as caught:
        select_profile(entry, supported, name=name)
    assert caught.value.code == code
    assert str(caught.value) == message


def _base_resource(catalog):
    return catalog["categories"]["tools"]["registries"]["base"]


@pytest.fixture
def base_catalog():
    return {
        "registryid": "phase2-catalog",
        "specversion": "1.0-rc4",
        "self": "#",
        "xid": "/",
        "epoch": 3,
        "createdat": "2026-09-04T00:00:00Z",
        "modifiedat": "2026-09-10T00:00:00Z",
        "categoriesurl": "#/categories",
        "categoriescount": 1,
        "categories": {
            "tools": {
                "categoryid": "tools",
                "self": "#/categories/tools",
                "xid": "/categories/tools",
                "epoch": 2,
                "createdat": "2026-09-04T00:00:00Z",
                "modifiedat": "2026-09-10T00:00:00Z",
                "registriesurl": "#/categories/tools/registries",
                "registriescount": 1,
                "registries": {
                    "base": {
                        "registryid": "base",
                        "self": "#/categories/tools/registries/base",
                        "xid": "/categories/tools/registries/base",
                        "metaurl": "#/categories/tools/registries/base/meta",
                        "meta": {
                            "registryid": "base",
                            "self": "#/categories/tools/registries/base/meta",
                            "xid": "/categories/tools/registries/base/meta",
                            "epoch": 2,
                            "createdat": "2026-09-04T00:00:00Z",
                            "modifiedat": "2026-09-10T00:00:00Z",
                            "readonly": True,
                            "defaultversionid": "description-1",
                            "defaultversionurl": (
                                "#/categories/tools/registries/base/versions/description-1"
                            ),
                            "defaultversionsticky": True,
                        },
                        "versions": {
                            "description-1": {
                                "registryid": "base",
                                "versionid": "description-1",
                                "self": (
                                    "#/categories/tools/registries/base/versions/description-1"
                                ),
                                "xid": (
                                    "/categories/tools/registries/base/versions/description-1"
                                ),
                                "epoch": 1,
                                "createdat": "2026-09-04T00:00:00Z",
                                "modifiedat": "2026-09-10T00:00:00Z",
                                "ancestorid": "description-1",
                                "isdefault": True,
                            }
                        },
                    }
                },
            }
        },
    }


@pytest.mark.parametrize(
    "filename,category_id,resource_id,version_id,choice,expected_index,expected",
    [
        pytest.param(
            "hub-compatible.json", "dev", "schema-bridge", "1", None, None,
            {"name": "http", "endpoint": "https://bridge.example.com/xregistry"},
            id="hub-xregurl-only",
        ),
        pytest.param(
            "multi-profile-catalog.json", "public", "schemas", "1", None, None,
            {"name": "http", "endpoint": "https://schemas.example.com/xregistry"},
            id="xregurl-zero-beats-matching-http20-and-oci10",
        ),
        pytest.param(
            "multi-profile-catalog.json", "public", "schemas", "2", "http", 3,
            {"name": "http", "endpoint": "https://schemas.example.com/xregistry"},
            id="explicit-http-zero-precedes-appended-xregurl",
        ),
        pytest.param(
            "multi-profile-catalog.json", "public", "schemas", "2", None, 1,
            {
                "name": "oci",
                "endpoint": "oci://artifacts.example.com/team/schemas",
                "priority": 0,
                "parameters": {
                    "reference": (
                        "sha256:0123456789abcdef0123456789abcdef"
                        "0123456789abcdef0123456789abcdef"
                    )
                },
            },
            id="explicit-oci-zero-precedes-appended-xregurl",
        ),
    ],
)
def test_registry_xregurl_xregurl_entry_remains_valid(
    filename, category_id, resource_id, version_id, choice, expected_index, expected,
):
    catalog = _sample(filename)
    before = deepcopy(catalog)
    resource = catalog["categories"][category_id]["registries"][resource_id]
    version = select_version(resource, version_id)

    selected = select_profile(version, BUILTINS, name=choice)

    assert selected == expected
    if expected_index is None:
        assert all(selected is not item for item in version.get("federationprofiles", []))
        assert set(selected) == {"name", "endpoint"}
    else:
        assert selected is version["federationprofiles"][expected_index]
    assert catalog == before


@pytest.mark.parametrize(
    "weburl",
    [
        pytest.param("https://catalog.example.test/page", id="absolute-website"),
        pytest.param("about/registries", id="relative-website-without-base"),
    ],
)
def test_registry_website_only_entry_is_valid_but_not_resolvable(
    weburl, base_catalog
):
    version = select_version(_base_resource(base_catalog))
    version["weburl"] = weburl
    before = deepcopy(base_catalog)

    _assert_federation_error(version, "unsupported_binding", "No supported advertisement")

    assert base_catalog == before


@pytest.mark.parametrize(
    "attributes,supported,choice,outcome",
    [
        pytest.param(
            {"federationprofiles": []}, BUILTINS, None,
            ("unsupported_binding", "No supported advertisement"), id="empty-profiles",
        ),
        pytest.param(
            {"federationprofiles": [EXTENSION]}, BUILTINS, None,
            ("unsupported_binding", "No supported advertisement"), id="unknown-only",
        ),
        pytest.param(
            {"federationprofiles": [dict(HTTP, name="HTTP")]}, BUILTINS, None,
            ("unsupported_binding", "No supported advertisement"), id="case-sensitive-name",
        ),
        pytest.param(
            {"federationprofiles": [EXTENSION]}, {"com.example.discovery"}, None, 0,
            id="extension-aware-consumer",
        ),
        pytest.param(
            {"federationprofiles": [HTTP]}, BUILTINS, None, 0, id="http-defaults",
        ),
        pytest.param(
            {"federationprofiles": [OCI]}, BUILTINS, None, 0, id="oci-tag",
        ),
        pytest.param(
            {"federationprofiles": [GIT]}, BUILTINS, None, 0, id="git-full-commit",
        ),
        pytest.param(
            {"federationprofiles": [FILE]}, BUILTINS, None, 0, id="file-document-tree",
        ),
        pytest.param(
            {"federationprofiles": [
                dict(FILE, parameters={"layout": "oci-layout", "reference": "stable"})
            ]},
            BUILTINS, None, 0, id="file-oci-layout",
        ),
        pytest.param(
            {"federationprofiles": [UA]}, BUILTINS, None, 0, id="opcua-portable-root",
        ),
        pytest.param(
            {"federationprofiles": [HTTP]}, {"oci"}, None,
            ("unsupported_binding", "No supported advertisement"), id="unsupported-valid-binding",
        ),
        pytest.param(
            {"federationprofiles": [HTTP]}, set(), None,
            ("unsupported_binding", "No supported advertisement"), id="empty-supported-set",
        ),
        pytest.param(
            {"federationprofiles": [OCI]}, BUILTINS, "http",
            ("unsupported_binding", "No supported advertisement"), id="unavailable-explicit-choice",
        ),
        pytest.param(
            {"federationprofiles": [
                dict(HTTP, priority=20), dict(OCI, priority=0), dict(GIT, priority=1)
            ]},
            BUILTINS, None, 1, id="priority-zero-before-one-and-twenty",
        ),
        pytest.param(
            {"federationprofiles": [EXTENSION, dict(OCI, priority=0), GIT, HTTP]},
            BUILTINS, None, 1, id="stable-tie-after-unsupported-filter",
        ),
        pytest.param(
            {"federationprofiles": [HTTP, dict(GIT, priority=20)]},
            BUILTINS, "git", 1, id="caller-choice-before-priority",
        ),
        pytest.param(
            {"federationprofiles": [dict(HTTP), dict(HTTP)]}, BUILTINS, None, 0,
            id="identical-advertisements-preserve-first-identity",
        ),
        pytest.param(
            {"federationprofiles": [dict(OCI, parameters={})]}, BUILTINS, None,
            ("invalid_package", "Missing or invalid OCI reference"), id="missing-oci-reference",
        ),
        pytest.param(
            {"federationprofiles": [dict(GIT, parameters={})]}, BUILTINS, None,
            ("invalid_package", "Git revision is not pinned input"), id="missing-git-revision",
        ),
        pytest.param(
            {"federationprofiles": [dict(FILE, parameters={})]}, BUILTINS, None,
            ("invalid_package", "Unknown file layout"), id="missing-file-layout",
        ),
        pytest.param(
            {"federationprofiles": [dict(UA, parameters={})]}, BUILTINS, None,
            ("invalid_package", "NodeId must be a string"), id="missing-opcua-root",
        ),
        pytest.param(
            {"federationprofiles": [dict(HTTP, endpoint="/relative"), dict(OCI, priority=10)]},
            BUILTINS, None, ("invalid_package", "Endpoint must be absolute"),
            id="relative-selected-endpoint-no-fallback",
        ),
        pytest.param(
            {"federationprofiles": [
                dict(HTTP, endpoint="https://reader@registry.example.test/root")
            ]},
            BUILTINS, None, ("policy_denied", "Embedded credentials prohibited"),
            id="credential-bearing-endpoint",
        ),
        pytest.param(
            {"federationprofiles": [dict(HTTP, endpoint=HTTP["endpoint"] + "?view=all")]},
            BUILTINS, None, ("invalid_package", "Endpoint has query or fragment"),
            id="http-query-is-not-a-root",
        ),
        pytest.param(
            {"federationprofiles": [dict(HTTP, endpoint="ftp://registry.example.test/root")]},
            BUILTINS, None, ("invalid_package", "HTTP endpoint scheme"), id="wrong-http-scheme",
        ),
        pytest.param(
            {"federationprofiles": [dict(HTTP, name="")]}, BUILTINS, None,
            ("invalid_package", "Missing profile name"), id="empty-profile-discriminator",
        ),
        pytest.param(
            {"federationprofiles": [dict(HTTP, priority=0.0)]}, BUILTINS, None,
            0, id="integral-value-is-valid-priority",
        ),
        pytest.param(
            {"federationprofiles": [
                dict(HTTP, parameters={"unrecognized": True}), dict(OCI, priority=10)
            ]},
            BUILTINS, None, ("unsupported_operation", "Unknown profile parameter"),
            id="unknown-selected-parameter-no-fallback",
        ),
        pytest.param(
            {"xregurl": HTTP["endpoint"] + "/", "federationprofiles": [HTTP]},
            BUILTINS, None, ("invalid_package", "Conflicting xregurl"),
            id="xregurl-consistency-is-exact-not-normalized",
        ),
        pytest.param(
            {
                "xregurl": HTTP["endpoint"],
                "federationprofiles": [
                    dict(HTTP, priority=1, parameters={"unrecognized": True}), OCI
                ],
            },
            {"http"}, None, "xregurl",
            id="matching-explicit-does-not-supply-xregurl-parameters",
        ),
    ],
)
def test_registry_resolvable_entry_requires_supported_valid_advertisement(
    attributes, supported, choice, outcome,
    base_catalog,
):
    version = select_version(_base_resource(base_catalog))
    version.update(deepcopy(attributes))
    before = deepcopy(base_catalog)

    if isinstance(outcome, tuple):
        _assert_federation_error(version, *outcome, supported=supported, name=choice)
    else:
        selected = select_profile(version, supported, name=choice)
        if outcome == "xregurl":
            assert selected == HTTP
            assert all(selected is not item for item in version["federationprofiles"])
        else:
            assert selected == attributes["federationprofiles"][outcome]
            assert selected is version["federationprofiles"][outcome]
    assert base_catalog == before


@pytest.mark.parametrize("case", ["absent-profiles", "empty-profiles", "cycle-and-dangling-sample"])
def test_registry_website_relationship_and_authority_never_supply_endpoints(
    case, base_catalog
):
    catalog = base_catalog
    if case == "cycle-and-dangling-sample":
        catalog = _sample("relationships-catalog.json")
        resource = catalog["categories"]["public"]["registries"]["aggregate"]
    else:
        resource = _base_resource(catalog)
    version = select_version(resource)
    version.update({
        "weburl": "https://catalog.example.test/page",
        "authority": "https://authority.example.test/organizations/platform",
        "registrytypes": ["urn:example:domain:schema", "https://models.example.test/events"],
    })
    if case != "cycle-and-dangling-sample":
        version["relationships"] = [
            {"type": "depends-on", "target": "/categories/tools/registries/base"},
            {
                "type": "supersedes",
                "target": "https://other.example.test/categories/tools/registries/replacement",
                "labels": {},
            },
        ]
    if case == "empty-profiles":
        version["federationprofiles"] = []
    before = deepcopy(catalog)

    _assert_federation_error(version, "unsupported_binding", "No supported advertisement")

    assert catalog == before


def test_registry_version_and_profile_selection_over_sample_catalog():
    catalog = _sample("multi-profile-catalog.json")
    before = deepcopy(catalog)
    resource = catalog["categories"]["public"]["registries"]["schemas"]
    default = select_version(resource)
    earlier = select_version(resource, "1")

    assert default is resource["versions"]["2"]
    assert earlier is resource["versions"]["1"]
    assert select_profile(default, BUILTINS) == {
        "name": "oci",
        "endpoint": "oci://artifacts.example.com/team/schemas",
        "priority": 0,
        "parameters": {
            "reference": (
                "sha256:0123456789abcdef0123456789abcdef"
                "0123456789abcdef0123456789abcdef"
            )
        },
    }
    assert select_profile(earlier, BUILTINS) == {
        "name": "http", "endpoint": "https://schemas.example.com/xregistry"
    }
    assert select_profile(earlier, BUILTINS, name="oci")["parameters"] == {"reference": "stable"}
    _assert_federation_error(
        earlier, "unsupported_binding", "No supported advertisement", name="git"
    )
    git = select_profile(default, BUILTINS, name="git")
    assert git is default["federationprofiles"][2]
    assert git["parameters"] == {
        "revision": "0123456789abcdef0123456789abcdef01234567", "path": "xregistry"
    }

    target_resource = {
        "meta": {"defaultversionid": "target-17"},
        "versions": {
            "target-18": {"versionid": "target-18", "labels": {"stage": "preview"}},
            "target-17": {"versionid": "target-17", "labels": {"stage": "production"}},
        },
    }
    assert select_version(target_resource) == {
        "versionid": "target-17", "labels": {"stage": "production"}
    }
    assert catalog == before


@pytest.mark.parametrize("schema_type", FORMATS, ids=FORMATS)
def test_registry_generated_outputs_match_authoritative_model(schema_type, tmp_path):
    before = MODEL_PATH.read_bytes()
    first, first_bytes = _generate(tmp_path / "first", schema_type)
    second, second_bytes = _generate(tmp_path / "second", schema_type)

    assert first_bytes == second_bytes
    assert MODEL_PATH.read_bytes() == before
    # Mainline tools/schema-generator.py does not emit the Resource meta/versions
    # envelope, so only generator-agnostic identity is pinned here.
    if schema_type == "json-schema":
        assert first["$id"] == SCHEMA_BASE + "document-schema.json"
    elif schema_type == "json-structure":
        assert first["name"] == "RegistryOfRegistriesDocument"
    assert second == first
