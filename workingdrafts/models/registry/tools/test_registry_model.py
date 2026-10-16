"""Offline conformance checks for the versioned Registry catalog model."""

from collections import Counter
from copy import deepcopy
from datetime import datetime, time, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import avro.io
import avro.schema
import jsonschema
import pytest
from openapi_spec_validator import validate_spec

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
COMMON_FIELDS = {
    "name", "epoch", "self", "xid", "description", "documentation",
    "labels", "createdat", "modifiedat",
}
ROOT_FIELDS = COMMON_FIELDS | {
    "registryid", "specversion", "model", "modelsource", "capabilities",
    "categories", "categoriesurl", "categoriescount",
}
DOMAIN_FIELDS = {
    "xregurl", "weburl", "registrytypes", "authority",
    "federationprofiles", "relationships",
}
DOCUMENT_FIELDS = {"registry", "registrybase64", "registryurl"}
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


def _write_model(directory, model):
    path = directory / "model.json"
    path.write_text(json.dumps(model, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def _objects(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from _objects(child)


def _resolve_local(document, reference):
    assert reference.startswith("#/"), f"Non-local reference: {reference}"
    target = document
    for segment in reference[2:].split("/"):
        target = target[segment.replace("~1", "/").replace("~0", "~")]
    assert isinstance(target, dict), reference
    return target


def _local_references(document):
    references = Counter()
    for node in _objects(document):
        if "$ref" in node:
            reference = node["$ref"]
            _resolve_local(document, reference)
            references[reference] += 1
    return references


def _all_errors(errors):
    for error in errors:
        yield error
        yield from _all_errors(error.context)


def _assert_schema_rejects(validator, instance, path, keyword):
    errors = list(_all_errors(validator.iter_errors(instance)))
    observed = [
        (tuple(error.absolute_path), error.validator, error.message)
        for error in errors
    ]
    assert any(
        error_path == path and error_keyword == keyword
        for error_path, error_keyword, _ in observed
    ), f"Expected {keyword} at {path}; observed {observed}"


def _assert_federation_error(entry, code, message, supported=BUILTINS, name=None):
    with pytest.raises(FederationError) as caught:
        select_profile(entry, supported, name=name)
    assert caught.value.code == code
    assert str(caught.value) == message


def _base_resource(catalog):
    return catalog["categories"]["tools"]["registries"]["base"]


def _avro_fields(record):
    fields = {field["name"]: field for field in record["fields"]}
    assert len(fields) == len(record["fields"])
    return fields


@pytest.fixture
def registry_model():
    return json.loads(MODEL_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def catalog_schema(tmp_path):
    schema, _ = _generate(tmp_path, "json-schema")
    assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
    jsonschema.Draft7Validator.check_schema(schema)
    _local_references(schema)
    return schema


@pytest.fixture
def catalog_validator(catalog_schema):
    return jsonschema.Draft7Validator(
        catalog_schema, format_checker=jsonschema.FormatChecker()
    )


@pytest.fixture
def version_validator(catalog_schema):
    # Exercise the emitted Version schema directly as well as the full document.
    # Navigation must not mask invalid inline Versions. That has a separate
    # full-document regression below, rather than a fixture that removes URLs.
    return jsonschema.Draft7Validator(
        catalog_schema["definitions"]["category-schema"]["registryVersion"],
        format_checker=jsonschema.FormatChecker(),
    )


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
    "case", ["minimal-version", "empty-category", "empty-catalog", "hub-compatible"]
)
def test_registry_base_catalog_requires_no_federation_fields(
    case, base_catalog, catalog_validator, version_validator, registry_model
):
    catalog = base_catalog
    if case == "empty-category":
        catalog["categories"]["tools"]["registries"] = {}
        catalog["categories"]["tools"]["registriescount"] = 0
    elif case == "empty-catalog":
        catalog["categories"] = {}
        catalog["categoriescount"] = 0
    elif case == "hub-compatible":
        catalog = _sample("hub-compatible.json")
    before = deepcopy(catalog)

    catalog_validator.validate(catalog)

    forbidden = {"labels", "registrytypes", "authority", "relationships",
                 "federationprofiles", "endpoint"}
    assert all(forbidden.isdisjoint(node) for node in _objects(catalog))
    definitions = catalog_validator.schema["definitions"]["category-schema"]
    assert definitions["category"].get("required", []) == []
    assert definitions["registry"].get("required", []) == []
    assert definitions["registryVersion"].get("required", []) == []
    assert catalog_validator.schema.get("required", []) == []
    attributes = registry_model["groups"]["categories"]["resources"]["registries"][
        "attributes"
    ]
    assert {name for name, value in attributes.items() if value.get("required")} == set()
    for category in catalog["categories"].values():
        for resource in category["registries"].values():
            version_validator.validate(select_version(resource))
    if case == "minimal-version":
        version = select_version(_base_resource(catalog))
        assert DOMAIN_FIELDS.isdisjoint(version)
        _assert_federation_error(
            version, "unsupported_binding", "No supported advertisement"
        )
    assert catalog == before


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
    catalog_validator, version_validator,
):
    catalog = _sample(filename)
    before = deepcopy(catalog)
    resource = catalog["categories"][category_id]["registries"][resource_id]
    version = select_version(resource, version_id)
    catalog_validator.validate(catalog)
    version_validator.validate(version)

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
    weburl, base_catalog, catalog_validator, version_validator
):
    version = select_version(_base_resource(base_catalog))
    version["weburl"] = weburl
    before = deepcopy(base_catalog)

    catalog_validator.validate(base_catalog)
    version_validator.validate(version)
    _assert_federation_error(version, "unsupported_binding", "No supported advertisement")

    assert DOMAIN_FIELDS.intersection(version) == {"weburl"}
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
    base_catalog, catalog_validator, version_validator,
):
    version = select_version(_base_resource(base_catalog))
    version.update(deepcopy(attributes))
    before = deepcopy(base_catalog)
    # These inputs have valid generated *shapes*. Binding semantics below are
    # deliberately stricter than URI-reference/type validation.
    catalog_validator.validate(base_catalog)
    version_validator.validate(version)

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


@pytest.mark.parametrize(
    "attributes,error_path,keyword",
    [
        pytest.param(
            {
                "labels": {},
                "registrytypes": [
                    "urn:example:domain:schema",
                    "https://models.example.test/events/1.0/model.json",
                    "urn:example:domain:schema",
                ],
                "authority": "urn:example:organization:catalog-team",
                "relationships": [
                    {"type": "depends-on", "target": "/categories/tools/registries/base"},
                    {
                        "type": "com.example.curated-with",
                        "target": "https://other.example.test/categories/shared/registries/events",
                        "labels": {"note": ""},
                    },
                    {
                        "type": "mirrors", "target": "/categories/tools/registries/base",
                        "labels": {},
                    },
                ],
                "exampleextension": {"mode": "KeepCase", "values": [0, False, ""]},
            },
            None, None, id="combined-descriptions-labels-and-extension",
        ),
        pytest.param(
            {"registrytypes": [], "relationships": [], "labels": {}, "authority": "teams/platform"},
            None, None, id="empty-collections-relative-authority",
        ),
        pytest.param(
            {"federationprofiles": [EXTENSION]}, None, None, id="extension-parameters-object",
        ),
        pytest.param(
            {"federationprofiles": [dict(HTTP, priority=0, parameters={})]},
            None, None, id="explicit-zero-and-empty-parameters",
        ),
        pytest.param({"federationprofiles": None}, ("federationprofiles",), "type", id="profiles-null"),
        pytest.param({"federationprofiles": {}}, ("federationprofiles",), "type", id="profiles-object"),
        pytest.param({"federationprofiles": [None]}, ("federationprofiles", 0), "type", id="profile-null"),
        pytest.param(
            {"federationprofiles": [{"endpoint": HTTP["endpoint"]}]},
            ("federationprofiles", 0), "required", id="profile-name-missing",
        ),
        pytest.param(
            {"federationprofiles": [dict(HTTP, name=None)]},
            ("federationprofiles", 0, "name"), "type", id="profile-name-null",
        ),
        pytest.param(
            {"federationprofiles": [dict(HTTP, name=1)]},
            ("federationprofiles", 0, "name"), "type", id="profile-name-number",
        ),
        pytest.param(
            {"federationprofiles": [{"name": "http"}]},
            ("federationprofiles", 0), "required", id="profile-endpoint-missing",
        ),
        pytest.param(
            {"federationprofiles": [dict(HTTP, endpoint=None)]},
            ("federationprofiles", 0, "endpoint"), "type", id="profile-endpoint-null",
        ),
        pytest.param(
            {"federationprofiles": [dict(HTTP, priority=-1)]},
            ("federationprofiles", 0, "priority"), "minimum", id="priority-below-zero",
        ),
        pytest.param(
            {"federationprofiles": [dict(HTTP, priority=True)]},
            ("federationprofiles", 0, "priority"), "type", id="priority-boolean",
        ),
        pytest.param(
            {"federationprofiles": [dict(HTTP, priority="0")]},
            ("federationprofiles", 0, "priority"), "type", id="priority-string",
        ),
        pytest.param(
            {"federationprofiles": [dict(HTTP, priority=0.5)]},
            ("federationprofiles", 0, "priority"), "type", id="priority-fraction",
        ),
        pytest.param(
            {"federationprofiles": [dict(HTTP, priority=None)]},
            ("federationprofiles", 0, "priority"), "type", id="priority-null",
        ),
        pytest.param(
            {"federationprofiles": [dict(HTTP, parameters=None)]},
            ("federationprofiles", 0, "parameters"), "type", id="parameters-null",
        ),
        pytest.param(
            {"federationprofiles": [dict(HTTP, parameters=[])]},
            ("federationprofiles", 0, "parameters"), "type", id="parameters-array",
        ),
        pytest.param({"registrytypes": None}, ("registrytypes",), "type", id="registrytypes-null"),
        pytest.param({"registrytypes": "schema"}, ("registrytypes",), "type", id="registrytypes-string"),
        pytest.param({"registrytypes": [7]}, ("registrytypes", 0), "type", id="registrytype-nonstring"),
        pytest.param({"authority": False}, ("authority",), "type", id="authority-nonstring"),
        pytest.param({"xregurl": None}, ("xregurl",), "type", id="xregurl-url-null"),
        pytest.param({"weburl": []}, ("weburl",), "type", id="website-array"),
        pytest.param({"relationships": {}}, ("relationships",), "type", id="relationships-object"),
        pytest.param({"relationships": [None]}, ("relationships", 0), "type", id="relationship-null"),
        pytest.param(
            {"relationships": [{"target": "/categories/tools/registries/base"}]},
            ("relationships", 0), "required", id="relationship-type-missing",
        ),
        pytest.param(
            {"relationships": [{"type": None, "target": "/categories/tools/registries/base"}]},
            ("relationships", 0, "type"), "type", id="relationship-type-null",
        ),
        pytest.param(
            {"relationships": [{"type": "depends-on"}]},
            ("relationships", 0), "required", id="relationship-target-missing",
        ),
        pytest.param(
            {"relationships": [{"type": "depends-on", "target": 5}]},
            ("relationships", 0, "target"), "type", id="relationship-target-nonstring",
        ),
        pytest.param(
            {"relationships": [{
                "type": "mirrors", "target": "/categories/tools/registries/base", "labels": []
            }]},
            ("relationships", 0, "labels"), "type", id="relationship-labels-array",
        ),
        pytest.param(
            {"relationships": [{
                "type": "mirrors", "target": "/categories/tools/registries/base",
                "labels": {"note": None},
            }]},
            ("relationships", 0, "labels", "note"), "type", id="relationship-label-value-null",
        ),
        pytest.param({"labels": []}, ("labels",), "type", id="version-labels-array"),
    ],
)
def test_registry_profile_and_relationship_shapes_are_additive(
    attributes, error_path, keyword, base_catalog, version_validator, catalog_validator
):
    version = select_version(_base_resource(base_catalog))
    version["federationprofiles"] = [deepcopy(HTTP)]
    version.update(deepcopy(attributes))
    before = deepcopy(base_catalog)

    if error_path is None:
        version_validator.validate(version)
        catalog_validator.validate(base_catalog)
        selected = select_profile(version, BUILTINS | {"com.example.discovery"})
        assert selected is version["federationprofiles"][0]
        assert selected == attributes.get("federationprofiles", [HTTP])[0]
    else:
        _assert_schema_rejects(version_validator, version, error_path, keyword)
    profile_schema = version_validator.schema["properties"]["federationprofiles"]["items"]
    relationship_schema = version_validator.schema["properties"]["relationships"]["items"]
    assert profile_schema["required"] == ["name", "endpoint"]
    assert relationship_schema["required"] == ["type", "target"]
    assert base_catalog == before


@pytest.mark.parametrize("case", ["absent-profiles", "empty-profiles", "cycle-and-dangling-sample"])
def test_registry_website_relationship_and_authority_never_supply_endpoints(
    case, base_catalog, catalog_validator, version_validator
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

    catalog_validator.validate(catalog)
    for category in catalog["categories"].values():
        for entry in category["registries"].values():
            version_validator.validate(select_version(entry))
    _assert_federation_error(version, "unsupported_binding", "No supported advertisement")

    if case == "cycle-and-dangling-sample":
        assert [item["target"] for item in version["relationships"]] == [
            "/categories/public/registries/canonical",
            "/categories/public/registries/retired",
            "/categories/public/registries/mirror",
            "https://catalog.example.net/categories/shared/registries/events",
        ]
    assert catalog == before


def test_registry_catalog_attributes_are_versioned_and_metadata_only(
    registry_model, catalog_validator, version_validator
):
    group = registry_model["groups"]["categories"]
    resource_model = group["resources"]["registries"]
    assert set(registry_model["groups"]) == {"categories"}
    assert (group["singular"], set(group["resources"]), resource_model["singular"]) == (
        "category", {"registries"}, "registry"
    )
    assert (group["modelversion"], resource_model["modelversion"]) == ("1.0-rc1", "1.0-rc1")
    assert resource_model["hasdocument"] is False
    assert set(resource_model["attributes"]) == DOMAIN_FIELDS | {"*"}
    assert resource_model.get("resourceattributes", {}) == {}
    assert resource_model.get("metaattributes", {}) == {}

    catalog = _sample("multi-profile-catalog.json")
    before = deepcopy(catalog)
    resource = catalog["categories"]["public"]["registries"]["schemas"]
    catalog_validator.validate(catalog)
    for version in resource["versions"].values():
        version_validator.validate(version)
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
    assert (earlier["versionid"], default["versionid"], resource["meta"]["defaultversionid"]) == (
        "1", "2", "2"
    )
    definitions = catalog_validator.schema["definitions"]["category-schema"]
    assert DOMAIN_FIELDS.issubset(definitions["registryVersion"]["properties"])
    assert DOMAIN_FIELDS.isdisjoint(definitions["registry"]["properties"])
    for name in ("registry", "registryVersion"):
        assert DOCUMENT_FIELDS.isdisjoint(definitions[name]["properties"])
    assert catalog == before


@pytest.mark.parametrize(
    "case,path,value,error_keyword",
    [
        pytest.param("authoritative", (), None, None, id="authoritative-model"),
        pytest.param(
            "missing", ("groups", "categories", "singular"), None, "required",
            id="missing-category-singular",
        ),
        pytest.param(
            "set", ("groups", "categories", "resources", "registries", "hasdocument"),
            "false", "type", id="hasdocument-is-boolean",
        ),
        pytest.param(
            "set", ("groups", "categories", "resources", "registries", "maxversions"),
            -1, "minimum", id="maxversions-not-negative",
        ),
        pytest.param(
            "set",
            ("groups", "categories", "resources", "registries", "attributes",
             "federationprofiles", "item", "type"),
            "not-a-core-type", "enum", id="array-item-must-use-core-type",
        ),
        pytest.param(
            "set",
            ("groups", "categories", "resources", "registries", "attributes", "*", "required"),
            True, "enum", id="wildcard-cannot-be-required",
        ),
    ],
)
def test_registry_model_validates_with_explicit_draft7(
    case, path, value, error_keyword, registry_model
):
    core = json.loads((ROOT / "core" / "model.schema.json").read_text(encoding="utf-8"))
    assert core["$schema"] == "https://json-schema.org/draft-07/schema#"
    assert registry_model["$schema"] == core["$id"]
    jsonschema.Draft7Validator.check_schema(core)
    _local_references(core)
    validator = jsonschema.Draft7Validator(core, format_checker=jsonschema.FormatChecker())
    validator.validate(registry_model)
    candidate = deepcopy(registry_model)
    if case != "authoritative":
        parent = candidate
        for key in path[:-1]:
            parent = parent[key]
        if case == "missing":
            del parent[path[-1]]
        else:
            parent[path[-1]] = value
    before = deepcopy(candidate)

    if case == "authoritative":
        assert list(validator.iter_errors(candidate)) == []
    else:
        _assert_schema_rejects(
            validator, candidate, path[:-1] if case == "missing" else path, error_keyword
        )
    assert candidate == before
    assert registry_model["groups"]["categories"]["resources"]["registries"]["hasdocument"] is False


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
