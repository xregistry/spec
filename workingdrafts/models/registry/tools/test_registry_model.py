"""Offline conformance checks for the versioned Registry catalog model."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from workingdrafts.federation.tools.federation_examples import (
    FederationError, select_profile, select_version,
)


REGISTRY_DIR = Path(__file__).resolve().parents[1]
BUILTINS = {"http", "oci", "git", "file", "opcua"}
HTTP = {"binding": "http", "endpoint": "https://registry.example.test/root"}
OCI = {
    "binding": "oci",
    "endpoint": "oci://artifacts.example.test/team/catalog",
    "parameters": {"reference": "stable"},
}
GIT = {
    "binding": "git",
    "endpoint": "https://git.example.test/team/catalog.git",
    "parameters": {"revision": "0123456789abcdef0123456789abcdef01234567"},
}
FILE = {
    "binding": "file",
    "endpoint": "file:///C:/catalog-cache/registry/",
    "parameters": {"layout": "document-tree"},
}
UA = {
    "binding": "opcua",
    "endpoint": "opc.tcp://ua.example.test:4840/xregistry",
    "parameters": {
        "registryroot": "nsu=urn:example:xregistry;s=Registries/Catalog",
        "applicationuri": "urn:example:ua:catalog-server",
    },
}
EXTENSION = {
    "binding": "com.example.discovery",
    "endpoint": "urn:example:catalog:discovery",
    "parameters": {"exampleextension": {"mode": "KeepCase", "values": [0, False, ""]}},
}


def _sample(filename):
    return json.loads((REGISTRY_DIR / "samples" / filename).read_text(encoding="utf-8"))


def _assert_federation_error(entry, code, message, supported=BUILTINS, binding=None):
    with pytest.raises(FederationError) as caught:
        select_profile(entry, supported, binding=binding)
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
    "weburl",
    [
        pytest.param("https://catalog.example.test/page", id="absolute-website"),
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
            {"federationprofiles": [EXTENSION]}, BUILTINS, None,
            ("unsupported_binding", "No supported advertisement"), id="unknown-only",
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
            {"federationprofiles": [UA]}, BUILTINS, None, 0, id="opcua-portable-root",
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
            {"federationprofiles": [
                dict(HTTP, endpoint="https://reader@registry.example.test/root")
            ]},
            BUILTINS, None, ("policy_denied", "Embedded credentials prohibited"),
            id="credential-bearing-endpoint",
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
        _assert_federation_error(version, *outcome, supported=supported, binding=choice)
    else:
        selected = select_profile(version, supported, binding=choice)
        assert selected == attributes["federationprofiles"][outcome]
        assert selected is version["federationprofiles"][outcome]
    assert base_catalog == before


def test_registry_version_and_profile_selection_over_sample_catalog():
    catalog = _sample("multi-profile-catalog.json")
    before = deepcopy(catalog)
    resource = catalog["categories"]["public"]["registries"]["schemas"]
    default = select_version(resource)
    earlier = select_version(resource, "1")

    assert default is resource["versions"]["2"]
    assert earlier is resource["versions"]["1"]
    assert select_profile(default, BUILTINS) == {
        "binding": "oci",
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
        "binding": "http", "endpoint": "https://schemas.example.com/xregistry"
    }
    assert select_profile(earlier, BUILTINS, binding="oci")["parameters"] == {"reference": "stable"}
    _assert_federation_error(
        earlier, "unsupported_binding", "No supported advertisement", binding="git"
    )
    git = select_profile(default, BUILTINS, binding="git")
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
