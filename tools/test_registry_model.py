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

from federation_examples import FederationError, select_profile, select_version


ROOT = Path(__file__).resolve().parent.parent
REGISTRY_DIR = ROOT / "workingdrafts" / "models" / "registry"
MODEL_PATH = REGISTRY_DIR / "model.json"
SCHEMA_BASE = "https://xregistry.io/workingdrafts/models/registry/schemas/"
FORMATS = {
    "json-schema": "document-schema.json",
    "json-structure": "document-schema.struct.json",
    "avro-schema": "document-schema.avsc",
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
                        "versionsurl": "#/categories/tools/registries/base/versions",
                        "versionscount": 1,
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
    assert definitions["registry"]["properties"]["meta"].get("required", []) == []
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
            ("invalid_package", "Invalid candidate priority"), id="integral-float-is-not-priority",
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
            {"relationships": [{"type": "depends-on", "target": "not a URI"}]},
            ("relationships", 0, "target"), "format", id="relationship-target-invalid-uri",
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
    assert DOMAIN_FIELDS.isdisjoint(definitions["registry"]["properties"]["meta"]["properties"])
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


@pytest.mark.parametrize(
    "case",
    [
        "sample-hub-compatible", "sample-multi-profile", "sample-relationships",
        "navigation-and-inline", "inline-only", "url-only",
        "same-type-alias-versioned-extensions",
        "categories-array", "registries-array", "registry-null", "missing-version-state",
        "invalid-inline-version-with-url", "invalid-inline-version-without-url",
        "versions-array-with-url", "versionsurl-number-with-inline",
        "negative-root-count", "negative-group-count", "negative-version-count",
    ],
)
def test_registry_generated_jsonschema_preserves_catalog_semantics_draft7(
    case, base_catalog, catalog_validator, version_validator
):
    schema = catalog_validator.schema
    assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
    assert schema["$id"] == SCHEMA_BASE + "document-schema.json"
    assert set(schema["properties"]) == ROOT_FIELDS
    definitions = schema["definitions"]["category-schema"]
    assert set(definitions) == {"category", "registry", "registryVersion"}
    assert schema["properties"]["categories"] == {
        "type": "object",
        "additionalProperties": {"$ref": "#/definitions/category-schema/category"},
    }
    assert definitions["category"]["properties"]["registries"] == {
        "type": "object",
        "additionalProperties": {"$ref": "#/definitions/category-schema/registry"},
    }
    assert definitions["registryVersion"]["properties"]["xregurl"]["format"] == "uri-reference"
    assert definitions["registryVersion"]["properties"]["relationships"]["items"][
        "properties"
    ]["target"]["format"] == "uri-reference"
    assert DOCUMENT_FIELDS.isdisjoint(definitions["registryVersion"]["properties"])

    samples = {
        "sample-hub-compatible": ("hub-compatible.json", (3, 3, 3)),
        "sample-multi-profile": ("multi-profile-catalog.json", (1, 1, 2)),
        "sample-relationships": ("relationships-catalog.json", (1, 3, 3)),
    }
    if case in samples:
        filename, expected_counts = samples[case]
        catalog = _sample(filename)
        resources = [
            resource for category in catalog["categories"].values()
            for resource in category["registries"].values()
        ]
        versions = [version for resource in resources for version in resource["versions"].values()]
        catalog_validator.validate(catalog)
        for version in versions:
            version_validator.validate(version)
        assert (len(catalog["categories"]), len(resources), len(versions)) == expected_counts
        return
    if case == "same-type-alias-versioned-extensions":
        catalog = _sample("multi-profile-catalog.json")
        category = catalog["categories"]["public"]
        resource = category["registries"]["schemas"]
        category["exampleextension"] = {"mode": "KeepCase", "values": [0, False, ""]}
        resource["versions"]["2"]["exampleextension"] = {
            "mode": "KeepCase", "values": [0, False, ""]
        }
        resource["meta"]["labels"] = {"stage": "resource-wide"}
        alias = {
            "registryid": "alias",
            "self": "#/categories/public/registries/alias",
            "xid": "/categories/public/registries/alias",
            "metaurl": "#/categories/public/registries/alias/meta",
            "meta": {
                "registryid": "alias",
                "self": "#/categories/public/registries/alias/meta",
                "xid": "/categories/public/registries/alias/meta",
                "xref": "/categories/public/registries/schemas",
                "epoch": 1,
                "createdat": "2026-09-10T00:00:00Z",
                "modifiedat": "2026-09-10T00:00:00Z",
                "readonly": True,
            },
        }
        category["registries"]["alias"] = alias
        category["registriescount"] = 2
        before = deepcopy(catalog)
        catalog_validator.validate(catalog)
        for version in resource["versions"].values():
            version_validator.validate(version)
        assert select_version(resource) is resource["versions"]["2"]
        assert select_profile(select_version(resource), BUILTINS) is resource["versions"]["2"][
            "federationprofiles"
        ][1]
        with pytest.raises(FederationError) as caught:
            select_version(alias)
        assert (caught.value.code, str(caught.value)) == ("unsupported_operation", "cannot_doc_xref")
        assert catalog == before
        return

    catalog = base_catalog
    resource = _base_resource(catalog)
    version = select_version(resource)
    resource_path = ("categories", "tools", "registries", "base")
    expected_error = None
    if case == "inline-only":
        del resource["versionsurl"]
    elif case == "url-only":
        del resource["versions"]
        resource["versionsurl"] = "https://catalog.example.test/categories/tools/registries/base/versions"
        resource["meta"]["defaultversionurl"] = resource["versionsurl"] + "/description-1"
    elif case == "categories-array":
        catalog["categories"] = []
        expected_error = (("categories",), "type")
    elif case == "registries-array":
        catalog["categories"]["tools"]["registries"] = []
        expected_error = (("categories", "tools", "registries"), "type")
    elif case == "registry-null":
        catalog["categories"]["tools"]["registries"]["base"] = None
        expected_error = (resource_path, "type")
    elif case == "missing-version-state":
        del resource["versions"]
        del resource["versionsurl"]
        expected_error = (resource_path, "anyOf")
    elif case in ("invalid-inline-version-with-url", "invalid-inline-version-without-url"):
        version["federationprofiles"] = [dict(HTTP, priority=-1)]
        if case == "invalid-inline-version-without-url":
            del resource["versionsurl"]
        expected_error = (
            resource_path + ("versions", "description-1", "federationprofiles", 0, "priority"),
            "minimum",
        )
    elif case == "versions-array-with-url":
        resource["versions"] = []
        expected_error = (resource_path + ("versions",), "type")
    elif case == "versionsurl-number-with-inline":
        resource["versionsurl"] = 5
        expected_error = (resource_path + ("versionsurl",), "type")
    elif case == "negative-root-count":
        catalog["categoriescount"] = -1
        expected_error = (("categoriescount",), "minimum")
    elif case == "negative-group-count":
        catalog["categories"]["tools"]["registriescount"] = -1
        expected_error = (("categories", "tools", "registriescount"), "minimum")
    elif case == "negative-version-count":
        resource["versionscount"] = -1
        expected_error = (resource_path + ("versionscount",), "minimum")
    before = deepcopy(catalog)

    if expected_error is None:
        catalog_validator.validate(catalog)
    else:
        _assert_schema_rejects(catalog_validator, catalog, *expected_error)
    assert catalog == before


@pytest.mark.parametrize(
    "variant", ["authoritative", "extended-alternate-names", "alternate-name-collision"]
)
def test_registry_generated_jsonstructure_preserves_references_and_alternate_names(
    variant, registry_model, tmp_path
):
    model_path = MODEL_PATH
    if variant != "authoritative":
        attributes = {
            "model-uri": {"type": "uri", "required": True},
            "1st-label": {"type": "string"},
            "example.timestamp": {"type": "timestamp"},
        }
        if variant == "alternate-name-collision":
            attributes["model_uri"] = {"type": "string"}
        registry_model["groups"]["categories"]["resources"]["registries"]["attributes"][
            "exampleextension"
        ] = {"type": "object", "namecharset": "extended", "attributes": attributes}
        core = json.loads((ROOT / "core" / "model.schema.json").read_text(encoding="utf-8"))
        jsonschema.Draft7Validator(core).validate(registry_model)
        model_path = _write_model(tmp_path, registry_model)
    before = model_path.read_bytes()
    if variant == "alternate-name-collision":
        result, output = _run_generator(tmp_path / "generated", "json-structure", model_path)
        assert result.returncode == 1
        assert (
            "JSON Structure name collision: 'model_uri' and 'model-uri' both map to 'modelUri'"
        ) in result.stderr
        assert result.stdout == f"> {model_path} as 'json-structure'\n"
        assert not output.exists()
        assert model_path.read_bytes() == before
        return
    schema, _ = _generate(tmp_path / "generated", "json-structure", model_path)

    assert schema["$schema"] == "https://json-structure.org/meta/extended/v0/#"
    assert schema["$id"] == SCHEMA_BASE + "document-schema.struct.json"
    assert schema["$uses"] == ["JSONStructureAlternateNames"]
    assert schema["name"] == "RegistryOfRegistriesDocument"
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert set(schema["properties"]) == ROOT_FIELDS
    assert _local_references(schema) == Counter({
        "#/definitions/Categories/Category": 1,
        "#/definitions/Categories/Registry": 1,
        "#/definitions/Categories/RegistryVersion": 1,
        "#/definitions/Categories/RegistryVersionFederationprofilesItem": 1,
        "#/definitions/Categories/RegistryVersionRelationshipsItem": 1,
    })
    for node in _objects(schema):
        for collection in ("properties", "definitions"):
            for name in node.get(collection, {}):
                assert re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", name), name
    definitions = schema["definitions"]["Categories"]
    assert set(definitions) == {
        "Category", "Registry", "RegistryVersion",
        "RegistryVersionFederationprofilesItem", "RegistryVersionRelationshipsItem",
    }
    assert schema["properties"]["categories"] == {
        "type": "map", "values": {"type": {"$ref": "#/definitions/Categories/Category"}}
    }
    category = definitions["Category"]
    resource = definitions["Registry"]
    version = definitions["RegistryVersion"]
    assert set(category["properties"]) == COMMON_FIELDS | {
        "categoryid", "registries", "registriesurl", "registriescount"
    }
    assert set(resource["properties"]) == COMMON_FIELDS | {
        "registryid", "meta", "metaurl", "versions", "versionsurl", "versionscount"
    }
    assert resource["properties"]["versions"] == {
        "type": "map",
        "values": {"type": {"$ref": "#/definitions/Categories/RegistryVersion"}},
    }
    assert resource["properties"]["versionscount"] == {"type": "uint32"}
    assert set(resource["properties"]["meta"]["properties"]) == COMMON_FIELDS | {
        "registryid", "xref", "readonly", "compatibility", "deprecated",
        "defaultversionid", "defaultversionurl", "defaultversionsticky",
    }
    assert resource["properties"]["meta"]["properties"]["defaultversionsticky"] == {
        "type": "boolean"
    }
    assert version["properties"]["labels"] == {"type": "map", "values": {"type": "string"}}
    assert version["properties"]["createdat"]["type"] == "datetime"
    assert version["additionalProperties"] is True
    assert category["additionalProperties"] is True
    assert DOCUMENT_FIELDS.isdisjoint(resource["properties"])
    assert DOCUMENT_FIELDS.isdisjoint(version["properties"])
    assert DOMAIN_FIELDS.isdisjoint(resource["properties"])
    expected_version_fields = COMMON_FIELDS | DOMAIN_FIELDS | {
        "versionid", "registryid", "isdefault", "ancestorid", "contenttype",
        "readonly", "compatibility", "deprecated",
    }
    if variant == "extended-alternate-names":
        expected_version_fields.add("exampleextension")
        extension = version["properties"]["exampleextension"]
        assert set(extension["properties"]) == {"modelUri", "value1stLabel", "exampleTimestamp"}
        assert extension["required"] == ["modelUri"]
        assert extension["properties"]["modelUri"]["altnames"] == {"json": "model-uri"}
        assert extension["properties"]["value1stLabel"]["altnames"] == {"json": "1st-label"}
        assert extension["properties"]["exampleTimestamp"] == {
            "type": "datetime", "altnames": {"json": "example.timestamp"}
        }
    assert set(version["properties"]) == expected_version_fields
    profile = definitions["RegistryVersionFederationprofilesItem"]
    relationship = definitions["RegistryVersionRelationshipsItem"]
    assert profile["required"] == ["name", "endpoint"]
    assert set(profile["properties"]) == {"name", "endpoint", "priority", "parameters"}
    assert profile["properties"]["priority"]["type"] == "uint32"
    assert "enum" not in profile["properties"]["name"]
    assert profile["properties"]["parameters"]["additionalProperties"] is True
    assert relationship["required"] == ["type", "target"]
    assert set(relationship["properties"]) == {"type", "target", "labels"}
    assert "enum" not in relationship["properties"]["type"]
    assert relationship["properties"]["labels"]["values"] == {"type": "string"}
    assert model_path.read_bytes() == before


@pytest.mark.parametrize(
    "variant",
    [
        "authoritative", "maxversions-zero", "maxversions-one", "maxversions-two",
        "timestamp-attribute", "core-createdat", "core-modifiedat",
    ],
)
def test_registry_generated_avro_preserves_catalog_fields(variant, registry_model, tmp_path):
    model_path = MODEL_PATH
    resource_model = registry_model["groups"]["categories"]["resources"]["registries"]
    if variant.startswith("maxversions-"):
        resource_model["maxversions"] = {
            "maxversions-zero": 0, "maxversions-one": 1, "maxversions-two": 2
        }[variant]
        model_path = _write_model(tmp_path, registry_model)
    elif variant == "timestamp-attribute":
        resource_model["attributes"]["catalogupdatedat"] = {"type": "timestamp"}
        model_path = _write_model(tmp_path, registry_model)
    core = json.loads((ROOT / "core" / "model.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(core).validate(registry_model)
    schema, _ = _generate(tmp_path / "generated", "avro-schema", model_path)
    parsed = avro.schema.parse(json.dumps(schema))
    assert (parsed.type, parsed.fullname) == ("record", "io.xregistry.DocumentType")
    category = _avro_fields(schema)["categories"]["type"]["values"]
    resource = _avro_fields(category)["registries"]["type"]["values"]
    assert category["name"] == "CategoryType"
    assert (resource["name"], resource["namespace"]) == ("RegistryType", "io.xregistry.categories")
    resource_fields = _avro_fields(resource)
    parsed_category = parsed.fields_dict["categories"].type.values
    parsed_resource = parsed_category.fields_dict["registries"].type.values
    meta = resource_fields["meta"]["type"][1]
    assert meta["name"] == "RegistryMetaType"
    assert _avro_fields(meta)["defaultversionid"]["type"] == ["null", "string"]
    assert _avro_fields(meta)["defaultversionsticky"]["type"] == ["null", "boolean"]
    if variant == "maxversions-one":
        assert {"versions", "versionsurl", "versionscount"}.isdisjoint(resource_fields)
        version = resource
        parsed_version = parsed_resource
    else:
        version = resource_fields["versions"]["type"]["values"]
        parsed_version = parsed_resource.fields_dict["versions"].type.values
        assert (version["name"], version["namespace"]) == (
            "RegistryVersionType", "io.xregistry.categories"
        )
        assert resource_fields["versions"]["default"] == {}
        assert resource_fields["versionscount"]["type"] == ["null", "long"]
        assert DOMAIN_FIELDS.isdisjoint(resource_fields)
    fields = _avro_fields(version)
    assert DOCUMENT_FIELDS.isdisjoint(fields)
    assert DOCUMENT_FIELDS.isdisjoint(resource_fields)
    assert _avro_fields(category)["registriescount"]["type"] == ["null", "long"]
    for name in ("xregurl", "weburl", "authority"):
        assert fields[name]["type"] == ["null", "string"]
        assert fields[name]["default"] is None
    assert fields["registrytypes"]["type"][0] == "null"
    assert fields["registrytypes"]["type"][1]["items"] == {"type": "string"}
    profiles = fields["federationprofiles"]["type"]
    assert profiles[0] == "null"
    assert profiles[1]["type"] == "array"
    profile = profiles[1]["items"]
    assert profile["name"] == "FederationprofilesItemType"
    profile_fields = _avro_fields(profile)
    assert set(profile_fields) == {"name", "endpoint", "priority", "parameters"}
    assert profile_fields["name"]["type"] == "string"
    assert profile_fields["endpoint"]["type"] == "string"
    assert profile_fields["priority"]["type"] == ["null", "int"]
    assert profile_fields["priority"]["default"] is None
    parameters = profile_fields["parameters"]["type"]
    assert parameters[0] == "null"
    assert parameters[1]["name"] == "FederationprofilesItemParametersType"
    assert _avro_fields(parameters[1])["Extensions"]["type"]["values"] == "io.xregistry.GenericRecord"
    relationships = fields["relationships"]["type"]
    assert relationships[0] == "null"
    assert relationships[1]["type"] == "array"
    relationship_fields = _avro_fields(relationships[1]["items"])
    assert set(relationship_fields) == {"type", "target", "labels"}
    assert relationship_fields["type"]["type"] == "string"
    assert relationship_fields["target"]["type"] == "string"
    assert relationship_fields["labels"]["type"][1]["values"] == "string"

    # This is the documented Avro record projection, not the Core JSON wire
    # document. Validate concrete values against the actual parsed nested type.
    datum = {
        "registryid": "directory", "self": "#/categories/tools/registries/directory",
        "xid": "/categories/tools/registries/directory", "labels": {}, "Extensions": {},
    }
    if variant != "maxversions-one":
        datum.update({"versionid": "description-7", "ancestorid": "description-7", "isdefault": True})
    assert avro.io.validate(parsed_version, datum)
    described = dict(
        datum,
        weburl="https://catalog.example.test/page",
        registrytypes=["urn:example:domain:schema"],
        federationprofiles=[dict(HTTP, priority=20)],
        relationships=[{
            "type": "depends-on", "target": "/categories/tools/registries/base",
            "labels": {"note": ""},
        }],
    )
    assert avro.io.validate(parsed_version, described)
    invalid = deepcopy(described)
    invalid["federationprofiles"][0]["name"] = None
    assert not avro.io.validate(parsed_version, invalid)
    invalid = deepcopy(described)
    invalid["relationships"][0]["labels"]["note"] = 7
    assert not avro.io.validate(parsed_version, invalid)

    instant = datetime(2000, 1, 1, tzinfo=timezone.utc)
    if variant == "timestamp-attribute":
        assert fields["catalogupdatedat"]["type"] == [
            "null", {"type": "long", "logicalType": "timestamp-millis"}
        ]
        timestamp_schema = parsed_version.fields_dict["catalogupdatedat"].type
        assert avro.io.validate(timestamp_schema, instant)
        assert not avro.io.validate(timestamp_schema, time(12, 30))
    elif variant in ("core-createdat", "core-modifiedat"):
        field = variant.removeprefix("core-")
        records = {
            "Registry": schema, "Category": category, "Resource": resource,
            "Meta": meta, "Version": version,
        }
        actual = {name: _avro_fields(record)[field]["type"] for name, record in records.items()}
        assert actual == {
            name: [{"type": "long", "logicalType": "timestamp-millis"}, "null"]
            for name in ("Registry", "Category", "Resource", "Meta", "Version")
        }
        timestamp_schema = parsed_version.fields_dict[field].type
        assert avro.io.validate(timestamp_schema, instant)
        assert not avro.io.validate(timestamp_schema, time(12, 30))


@pytest.mark.parametrize(
    "path,operation_id,response_schema,methods",
    [
        pytest.param(
            "/categories", "getCategoriesAll",
            {"type": "object", "additionalProperties": {"$ref": "#/components/schemas/category"}},
            {"get"}, id="categories-collection",
        ),
        pytest.param(
            "/categories/{groupid}", "getCategory",
            {"$ref": "#/components/schemas/category"}, {"get", "put", "delete"},
            id="category-entity",
        ),
        pytest.param(
            "/categories/{groupid}/registries", "getCategoryRegistriesAll",
            {"type": "object", "additionalProperties": {"$ref": "#/components/schemas/registry"}},
            {"get"}, id="registries-collection",
        ),
        pytest.param(
            "/categories/{groupid}/registries/{resourceid}", "getCategoryRegistry",
            {"$ref": "#/components/schemas/registry"}, {"get", "put", "post", "delete"},
            id="metadata-only-resource",
        ),
        pytest.param(
            "/categories/{groupid}/registries/{resourceid}/meta", "getCategoryRegistryMeta",
            {"$ref": "#/components/schemas/Meta"}, {"get", "put", "patch"},
            id="resource-meta",
        ),
        pytest.param(
            "/categories/{groupid}/registries/{resourceid}$details", "getCategoryRegistryDetails",
            {"$ref": "#/components/schemas/registry"}, {"get"}, id="resource-details",
        ),
        pytest.param(
            "/categories/{groupid}/registries/{resourceid}/versions",
            "getCategoryRegistryVersionsAll",
            {"type": "object", "additionalProperties": {"$ref": "#/components/schemas/registryVersion"}},
            {"get", "post"}, id="versions-collection",
        ),
        pytest.param(
            "/categories/{groupid}/registries/{resourceid}/versions/{versionid}",
            "getCategoryRegistryVersion", {"$ref": "#/components/schemas/registryVersion"},
            {"get", "delete"}, id="metadata-only-version",
        ),
        pytest.param(
            "/categories/{groupid}/registries/{resourceid}/versions/{versionid}$details",
            "getCategoryRegistryVersionMetadata",
            {"$ref": "#/components/schemas/registryVersion"},
            {"get"}, id="version-details",
        ),
    ],
)
def test_registry_generated_openapi_preserves_metadata_only_paths(
    path, operation_id, response_schema, methods, tmp_path
):
    schema, _ = _generate(tmp_path, "openapi")
    assert schema["openapi"] == "3.0.3"
    _local_references(schema)
    validate_spec(schema)
    assert set(schema["paths"]) == {
        "/", "/capabilities", "/model", "/export",
        "/categories", "/categories/{groupid}", "/categories/{groupid}/registries",
        "/categories/{groupid}/registries/{resourceid}",
        "/categories/{groupid}/registries/{resourceid}$details",
        "/categories/{groupid}/registries/{resourceid}/meta",
        "/categories/{groupid}/registries/{resourceid}/versions",
        "/categories/{groupid}/registries/{resourceid}/versions/{versionid}",
        "/categories/{groupid}/registries/{resourceid}/versions/{versionid}$details",
    }
    definitions = schema["components"]["schemas"]
    assert set(definitions["document"]["properties"]) == ROOT_FIELDS
    assert definitions["category"]["properties"]["registries"] == {
        "type": "object", "additionalProperties": {"$ref": "#/components/schemas/registry"}
    }
    assert DOMAIN_FIELDS.issubset(definitions["registryVersion"]["properties"])
    assert DOMAIN_FIELDS.isdisjoint(definitions["registry"]["properties"])
    for entity in ("registry", "registryVersion"):
        assert DOCUMENT_FIELDS.isdisjoint(definitions[entity]["properties"])
    operation = schema["paths"][path]
    assert set(operation) - {"parameters"} == methods
    assert operation["get"]["operationId"] == operation_id
    assert all(parameter.get("name") != "meta" for parameter in operation.get("parameters", []))
    assert operation["get"]["responses"]["404"] == {
        "$ref": "#/components/responses/NotFound"
    }
    content = operation["get"]["responses"]["200"]["content"]
    assert content["application/json"]["schema"] == response_schema
    assert set(content) == {"application/json"}, (
        "hasdocument:false must not advertise a detached binary document"
    )


@pytest.mark.parametrize("schema_type", FORMATS, ids=FORMATS)
def test_registry_generated_outputs_match_authoritative_model(schema_type, tmp_path):
    before = MODEL_PATH.read_bytes()
    first, first_bytes = _generate(tmp_path / "first", schema_type)
    second, second_bytes = _generate(tmp_path / "second", schema_type)

    assert first_bytes == second_bytes
    assert first_bytes.endswith(b"\n")
    assert not first_bytes.endswith(b"\n\n")
    assert b"\r" not in first_bytes
    assert MODEL_PATH.read_bytes() == before
    # Repeatability is not a semantic oracle: pin model-specific output as well.
    if schema_type == "json-schema":
        assert first["$id"] == SCHEMA_BASE + "document-schema.json"
        assert first["definitions"]["category-schema"]["registryVersion"]["properties"][
            "federationprofiles"
        ]["items"]["required"] == ["name", "endpoint"]
    elif schema_type == "json-structure":
        assert first["name"] == "RegistryOfRegistriesDocument"
        assert first["definitions"]["Categories"]["Registry"]["properties"]["versions"] == {
            "type": "map",
            "values": {"type": {"$ref": "#/definitions/Categories/RegistryVersion"}},
        }
    elif schema_type == "avro-schema":
        category = _avro_fields(first)["categories"]["type"]["values"]
        resource = _avro_fields(category)["registries"]["type"]["values"]
        assert _avro_fields(resource)["versions"]["type"]["values"]["name"] == "RegistryVersionType"
    else:
        assert first["paths"]["/categories"]["get"]["operationId"] == "getCategoriesAll"
        assert first["paths"]["/categories"]["get"]["responses"]["200"]["content"] == {
            "application/json": {
                "schema": {
                    "type": "object", "additionalProperties": {"$ref": "#/components/schemas/category"}
                }
            }
        }
    assert second == first
