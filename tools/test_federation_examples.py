"""Offline conformance tests for the common federation example primitives."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from federation_examples import (
    FederationError,
    resolve_local_xref,
    resource_type,
    select_label,
    select_profile,
    select_version,
    validate_profile,
    validate_xid,
)


FIXTURE_ROOT = Path(__file__).parent.parent / "workingdrafts" / "federation"


@pytest.fixture
def selection_sample():
    return json.loads(
        (FIXTURE_ROOT / "samples" / "selection.json").read_text(encoding="utf-8")
    )


@pytest.fixture
def request_schema():
    return json.loads(
        (FIXTURE_ROOT / "schemas" / "request.json").read_text(encoding="utf-8")
    )


@pytest.fixture(params=["http", "oci", "git", "file", "opcua"])
def builtin_profile(request):
    profiles = {
        "http": {
            "name": "http",
            "endpoint": "https://example.test/nonroot/registry",
        },
        "oci": {
            "name": "oci",
            "endpoint": "oci://registry.example.test/team/catalog",
            "parameters": {"reference": "v1"},
        },
        "git": {
            "name": "git",
            "endpoint": "https://git.example.test/team/catalog.git",
            "parameters": {"revision": "refs/heads/main"},
        },
        "file": {
            "name": "file",
            "endpoint": "file:///catalog",
            "parameters": {"layout": "document-tree"},
        },
        "opcua": {
            "name": "opcua",
            "endpoint": "opc.tcp://ua.example.test:4840",
            "parameters": {"registryroot": "nsu=urn:example:registry;s=Root"},
        },
    }
    return profiles[request.param]


@pytest.mark.parametrize(
    ("code", "message"),
    [
        pytest.param("invalid_package", "bad fixture", id="invalid-package"),
        pytest.param("integrity_error", "digest mismatch", id="integrity-error"),
    ],
)
def test_federation_error_preserves_code_and_message(code, message):
    error = FederationError(code, message)

    assert isinstance(error, ValueError)
    assert error.code == code
    assert str(error) == message
    assert error.args == (message,)


@pytest.mark.parametrize(
    "xid",
    [
        pytest.param("/", id="registry"),
        pytest.param("/documents/main", id="group"),
        pytest.param("/documents/main/assets/item", id="resource"),
        pytest.param("/documents/main/assets/item/meta", id="meta"),
        pytest.param("/documents/main/assets/item/versions/v1", id="version"),
    ],
)
def test_validate_xid_accepts_entity_shapes(xid):
    assert validate_xid(xid) == xid
    assert validate_xid(xid, collection=False) == xid


@pytest.mark.parametrize(
    "xid",
    [
        pytest.param("/documents", id="groups"),
        pytest.param("/documents/main/assets", id="resources"),
        pytest.param("/documents/main/assets/item/versions", id="versions"),
    ],
)
def test_validate_xid_accepts_collection_shapes(xid):
    assert validate_xid(xid, collection=True) == xid

    with pytest.raises(FederationError) as raised:
        validate_xid(xid)

    assert raised.value.code == "invalid_package"
    assert str(raised.value) == "Invalid XID hierarchy"


@pytest.mark.parametrize(
    "identifier",
    [
        pytest.param("A", id="uppercase-initial"),
        pytest.param("_", id="underscore-initial"),
        pytest.param("0", id="digit-initial"),
        pytest.param("A_0.~:@-", id="legal-punctuation"),
        pytest.param("item", id="lowercase"),
        pytest.param("Item", id="case-distinct"),
    ],
)
def test_validate_xid_preserves_case_and_legal_characters(identifier):
    xid = f"/Documents/Main/assets/{identifier}"

    assert validate_xid(xid) == f"/Documents/Main/assets/{identifier}"
    with pytest.raises(FederationError) as raised:
        validate_xid(xid + "/")

    assert raised.value.code == "invalid_package"
    assert str(raised.value) == "Invalid XID component"


@pytest.mark.parametrize(
    ("length", "valid"),
    [
        pytest.param(1, True, id="minimum-1"),
        pytest.param(127, True, id="below-maximum-127"),
        pytest.param(128, True, id="maximum-128"),
        pytest.param(129, False, id="over-maximum-129"),
    ],
)
def test_validate_xid_component_length_boundaries(length, valid):
    xid = "/documents/main/assets/" + "i" * length

    if valid:
        assert validate_xid(xid) == "/documents/main/assets/" + "i" * length
        assert len(validate_xid(xid).rsplit("/", 1)[1]) == length
    else:
        with pytest.raises(FederationError) as raised:
            validate_xid(xid)
        assert raised.value.code == "invalid_package"
        assert str(raised.value) == "Invalid XID component"


@pytest.mark.parametrize(
    ("value", "collection", "message"),
    [
        pytest.param(None, False, "XID must start with /", id="null"),
        pytest.param(False, False, "XID must start with /", id="boolean"),
        pytest.param(0, False, "XID must start with /", id="number"),
        pytest.param([], False, "XID must start with /", id="array"),
        pytest.param({}, False, "XID must start with /", id="object"),
        pytest.param("", False, "XID must start with /", id="empty"),
        pytest.param("documents/main", False, "XID must start with /", id="relative"),
        pytest.param("//", False, "Invalid XID component", id="empty-components"),
        pytest.param("/documents/main/", False, "Invalid XID component", id="trailing-slash"),
        pytest.param("/documents//assets/item", False, "Invalid XID component", id="internal-empty"),
        pytest.param("/documents/-main", False, "Invalid XID component", id="invalid-initial"),
        pytest.param("/documents/it%65m", False, "Invalid XID component", id="percent-encoding"),
        pytest.param("/documents/main item", False, "Invalid XID component", id="space"),
        pytest.param("/documents/main\\item", False, "Invalid XID component", id="backslash"),
        pytest.param("/documents/main\n", False, "Invalid XID component", id="newline"),
        pytest.param("/documents/main\x7f", False, "Invalid XID component", id="del"),
        pytest.param("/documents/caf\u00e9", False, "Invalid XID component", id="non-ascii"),
        pytest.param("/documents", False, "Invalid XID hierarchy", id="entity-depth-1"),
        pytest.param("/documents/main/assets", False, "Invalid XID hierarchy", id="entity-depth-3"),
        pytest.param("/documents/main/assets/item/Meta", False, "Invalid XID hierarchy", id="meta-case"),
        pytest.param("/documents/main/assets/item/versions", False, "Invalid XID hierarchy", id="entity-depth-5-collection"),
        pytest.param("/documents/main/assets/item/Versions/v1", False, "Invalid XID hierarchy", id="versions-case"),
        pytest.param("/documents/main/assets/item/meta/v1", False, "Invalid XID hierarchy", id="version-wrong-marker"),
        pytest.param("/documents/main/assets/item/versions/v1/extra", False, "Invalid XID hierarchy", id="entity-depth-7"),
        pytest.param("/", True, "Invalid XID component", id="collection-root"),
        pytest.param("/documents/main", True, "Invalid XID hierarchy", id="collection-depth-2"),
        pytest.param("/documents/main/assets/item", True, "Invalid XID hierarchy", id="collection-depth-4"),
        pytest.param("/documents/main/assets/item/meta", True, "Invalid XID hierarchy", id="collection-wrong-marker"),
        pytest.param("/documents/main/assets/item/Versions", True, "Invalid XID hierarchy", id="collection-marker-case"),
        pytest.param("/documents/main/assets/item/versions/v1", True, "Invalid XID hierarchy", id="collection-depth-6"),
    ],
)
def test_validate_xid_rejects_invalid_shapes(value, collection, message):
    before = deepcopy(value)

    with pytest.raises(FederationError) as raised:
        validate_xid(value, collection=collection)

    assert raised.value.code == "invalid_package"
    assert str(raised.value) == message
    assert value == before


def test_validate_profile_accepts_builtin_profiles(builtin_profile):
    before = deepcopy(builtin_profile)

    assert validate_profile(builtin_profile) is None
    assert builtin_profile == before
    assert "priority" not in builtin_profile


@pytest.mark.parametrize(
    "attributes",
    [
        pytest.param({"parameters": {}}, id="explicit-empty-http-parameters"),
        pytest.param({"priority": 0}, id="explicit-zero"),
        pytest.param({"priority": 7}, id="positive-priority"),
    ],
)
def test_validate_profile_preserves_explicit_optional_fields(attributes):
    profile = {
        "name": "http",
        "endpoint": "https://example.test/nonroot/registry",
        **attributes,
    }
    before = deepcopy(profile)

    assert validate_profile(profile) is None
    assert profile == before
    assert profile["endpoint"] == "https://example.test/nonroot/registry"


@pytest.mark.parametrize(
    "profile",
    [
        pytest.param(
            {
                "name": "example.extension",
                "endpoint": "urn:example:catalog",
                "parameters": {"future": {"enabled": True}},
            },
            id="extension-defined-parameters",
        ),
        pytest.param(
            {"name": "HTTP", "endpoint": "urn:example:catalog", "parameters": {"future": True}},
            id="case-distinct-name",
        ),
        pytest.param(
            {"name": "example.extension", "endpoint": "https://example.test/catalog?view=full#entry"},
            id="extension-query-fragment",
        ),
    ],
)
def test_validate_profile_accepts_unknown_profile_as_catalog_data(profile):
    before = deepcopy(profile)

    assert validate_profile(profile) is None
    assert profile == before
    with pytest.raises(FederationError) as raised:
        select_profile({"federationprofiles": [profile]}, {"http", "oci", "git", "file", "opcua"})

    assert raised.value.code == "unsupported_binding"
    assert str(raised.value) == "No supported advertisement"


@pytest.mark.parametrize(
    ("profile", "message"),
    [
        pytest.param(None, "Advertisement must be an object", id="null-profile"),
        pytest.param([], "Advertisement must be an object", id="array-profile"),
        pytest.param("http", "Advertisement must be an object", id="string-profile"),
        pytest.param({"endpoint": "https://example.test"}, "Missing profile name", id="missing-name"),
        pytest.param({"name": "", "endpoint": "https://example.test"}, "Missing profile name", id="empty-name"),
        pytest.param({"name": 7, "endpoint": "https://example.test"}, "Missing profile name", id="numeric-name"),
        pytest.param({"name": "http"}, "Endpoint must be a URI", id="missing-endpoint"),
        pytest.param({"name": "http", "endpoint": None}, "Endpoint must be a URI", id="null-endpoint"),
        pytest.param({"name": "http", "endpoint": 7}, "Endpoint must be a URI", id="numeric-endpoint"),
        pytest.param({"name": "http", "endpoint": ""}, "Endpoint must be absolute", id="empty-endpoint"),
        pytest.param({"name": "http", "endpoint": "/registry"}, "Endpoint must be absolute", id="relative-endpoint"),
        pytest.param({"name": "http", "endpoint": "https://example.test/a b"}, "Endpoint must be a URI", id="endpoint-space"),
        pytest.param({"name": "http", "endpoint": "https://example.test/\n"}, "Endpoint must be a URI", id="endpoint-newline"),
        pytest.param({"name": "http", "endpoint": "https://example.test:abc"}, "Malformed endpoint", id="nonnumeric-port"),
        pytest.param({"name": "http", "endpoint": "https://example.test:65536"}, "Malformed endpoint", id="out-of-range-port"),
        pytest.param({"name": "http", "endpoint": "https://[::1"}, "Malformed endpoint", id="unclosed-ipv6"),
        pytest.param({"name": "http", "endpoint": "https://example.test", "priority": -1}, "Priority must be unsigned integer", id="negative-priority"),
        pytest.param({"name": "http", "endpoint": "https://example.test", "priority": True}, "Priority must be unsigned integer", id="boolean-priority"),
        pytest.param({"name": "http", "endpoint": "https://example.test", "priority": 0.0}, "Priority must be unsigned integer", id="float-priority"),
        pytest.param({"name": "http", "endpoint": "https://example.test", "priority": "0"}, "Priority must be unsigned integer", id="string-priority"),
        pytest.param({"name": "http", "endpoint": "https://example.test", "priority": None}, "Priority must be unsigned integer", id="null-priority"),
        pytest.param({"name": "http", "endpoint": "https://example.test", "parameters": None}, "Parameters must be an object", id="null-parameters"),
        pytest.param({"name": "http", "endpoint": "https://example.test", "parameters": []}, "Parameters must be an object", id="array-parameters"),
        pytest.param({"name": "http", "endpoint": "https://example.test", "parameters": "none"}, "Parameters must be an object", id="string-parameters"),
        pytest.param({"name": "example.extension", "endpoint": "/catalog"}, "Endpoint must be absolute", id="unknown-relative-endpoint"),
        pytest.param({"name": "example.extension", "endpoint": "urn:example:catalog", "priority": False}, "Priority must be unsigned integer", id="unknown-invalid-priority"),
        pytest.param({"name": "example.extension", "endpoint": "urn:example:catalog", "parameters": []}, "Parameters must be an object", id="unknown-invalid-parameters"),
    ],
)
def test_validate_profile_rejects_generic_shapes(profile, message):
    before = deepcopy(profile)

    with pytest.raises(FederationError) as raised:
        validate_profile(profile)

    assert raised.value.code == "invalid_package"
    assert str(raised.value) == message
    assert profile == before


@pytest.mark.parametrize("name", ["http", "example.extension"])
@pytest.mark.parametrize(
    "endpoint",
    [
        pytest.param("https://reader@example.test/registry", id="username-only"),
        pytest.param("https://reader:synthetic@example.test/registry", id="username-password"),
        pytest.param("https://@example.test/registry", id="empty-username"),
    ],
)
def test_validate_profile_rejects_embedded_credentials(name, endpoint):
    profile = {"name": name, "endpoint": endpoint}
    before = deepcopy(profile)

    with pytest.raises(FederationError) as raised:
        validate_profile(profile)

    assert raised.value.code == "policy_denied"
    assert str(raised.value) == "Embedded credentials prohibited"
    assert profile == before


def test_validate_profile_rejects_unknown_builtin_parameters(builtin_profile):
    builtin_profile.setdefault("parameters", {})["future"] = True
    before = deepcopy(builtin_profile)

    with pytest.raises(FederationError) as raised:
        validate_profile(builtin_profile)

    assert raised.value.code == "unsupported_operation"
    assert str(raised.value) == "Unknown profile parameter"
    assert builtin_profile == before


@pytest.mark.parametrize(
    ("profile", "code", "message"),
    [
        pytest.param(
            {"name": "http", "endpoint": "https://example.test", "priority": -1, "parameters": {"future": True}},
            "invalid_package", "Priority must be unsigned integer", id="priority-before-unknown-parameter",
        ),
        pytest.param(
            {"name": "http", "endpoint": "https://reader@example.test", "parameters": {"future": True}},
            "policy_denied", "Embedded credentials prohibited", id="credentials-before-unknown-parameter",
        ),
        pytest.param(
            {"name": "http", "endpoint": "ftp://example.test", "parameters": {"future": True}},
            "unsupported_operation", "Unknown profile parameter", id="unknown-parameter-before-transport",
        ),
    ],
)
def test_validate_profile_generic_errors_precede_builtin_errors(profile, code, message):
    before = deepcopy(profile)

    with pytest.raises(FederationError) as raised:
        validate_profile(profile)

    assert raised.value.code == code
    assert str(raised.value) == message
    assert profile == before


@pytest.mark.parametrize(
    "suffix",
    [
        pytest.param("?", id="empty-query"),
        pytest.param("?view=full", id="query"),
        pytest.param("#", id="empty-fragment"),
        pytest.param("#item", id="fragment"),
    ],
)
def test_validate_profile_rejects_query_and_fragment(builtin_profile, suffix):
    builtin_profile["endpoint"] += suffix
    before = deepcopy(builtin_profile)

    with pytest.raises(FederationError) as raised:
        validate_profile(builtin_profile)

    assert raised.value.code == "invalid_package"
    assert str(raised.value) == "Endpoint has query or fragment"
    assert builtin_profile == before


@pytest.mark.parametrize(
    "profile",
    [
        pytest.param({"name": "http", "endpoint": "https:/registry"}, id="http"),
        pytest.param(
            {"name": "git", "endpoint": "https:/catalog.git", "parameters": {"revision": "refs/heads/main"}},
            id="git",
        ),
        pytest.param(
            {"name": "oci", "endpoint": "oci:/team/catalog", "parameters": {"reference": "v1"}},
            id="oci",
        ),
        pytest.param(
            {"name": "opcua", "endpoint": "opc.tcp:/registry", "parameters": {"registryroot": "i=2253"}},
            id="opcua",
        ),
    ],
)
def test_validate_profile_rejects_missing_host(profile):
    before = deepcopy(profile)

    with pytest.raises(FederationError) as raised:
        validate_profile(profile)

    assert raised.value.code == "invalid_package"
    assert str(raised.value) == "Missing endpoint host"
    assert profile == before


@pytest.mark.parametrize(
    ("endpoint", "valid"),
    [
        pytest.param("http://Example.test:8080/NonRoot/Registry", True, id="http-nonroot"),
        pytest.param("https://Example.test/NonRoot/Registry/", True, id="https-nonroot-trailing-slash"),
        pytest.param("https://example.test:0/registry", True, id="port-minimum-0"),
        pytest.param("https://example.test:65535/registry", True, id="port-maximum-65535"),
        pytest.param("http://[::1]:8080/registry", True, id="ipv6-literal"),
        pytest.param("ftp://example.test/nonroot/registry", False, id="wrong-scheme"),
    ],
)
def test_validate_http_profile_schemes_and_nonroot_path(endpoint, valid):
    profile = {"name": "http", "endpoint": endpoint}
    before = deepcopy(profile)

    if valid:
        assert validate_profile(profile) is None
    else:
        with pytest.raises(FederationError) as raised:
            validate_profile(profile)
        assert raised.value.code == "invalid_package"
        assert str(raised.value) == "HTTP endpoint scheme"
    assert profile == before
    assert "parameters" not in profile


@pytest.mark.parametrize(
    ("parameters", "valid"),
    [
        pytest.param({"reference": "v"}, True, id="tag-minimum-1"),
        pytest.param({"reference": "t" * 127}, True, id="tag-below-maximum-127"),
        pytest.param({"reference": "t" * 128}, True, id="tag-maximum-128"),
        pytest.param({"reference": "t" * 129}, False, id="tag-over-maximum-129"),
        pytest.param({"reference": "_"}, True, id="tag-underscore-initial"),
        pytest.param({"reference": "Release.1-rc_2"}, True, id="tag-case-and-punctuation"),
        pytest.param({"reference": ".release"}, False, id="tag-dot-initial"),
        pytest.param({"reference": "-release"}, False, id="tag-dash-initial"),
        pytest.param({"reference": "release/one"}, False, id="tag-slash"),
        pytest.param({"reference": "release one"}, False, id="tag-space"),
        pytest.param({"reference": ""}, False, id="empty-reference"),
        pytest.param({}, False, id="missing-reference"),
        pytest.param({"reference": None}, False, id="null-reference"),
        pytest.param({"reference": 7}, False, id="numeric-reference"),
        pytest.param({"reference": "sha256:" + "a" * 63}, False, id="digest-below-64"),
        pytest.param({"reference": "sha256:" + "a" * 64}, True, id="digest-exact-64-lowercase"),
        pytest.param({"reference": "sha256:" + "a" * 65}, False, id="digest-over-64"),
        pytest.param({"reference": "sha256:" + "A" * 64}, False, id="digest-uppercase-hex"),
        pytest.param({"reference": "sha512:" + "a" * 128}, False, id="digest-unsupported-algorithm"),
    ],
)
def test_validate_oci_profile_reference_boundaries(parameters, valid):
    profile = {
        "name": "oci",
        "endpoint": "oci://registry.example.test/team/catalog",
        "parameters": deepcopy(parameters),
    }
    before = deepcopy(profile)

    if valid:
        assert validate_profile(profile) is None
    else:
        with pytest.raises(FederationError) as raised:
            validate_profile(profile)
        assert raised.value.code == "invalid_package"
        assert str(raised.value) == "Missing or invalid OCI reference"
    assert profile == before
    assert profile["endpoint"] == "oci://registry.example.test/team/catalog"


@pytest.mark.parametrize(
    ("endpoint", "valid"),
    [
        pytest.param("oci://registry.example.test/team/catalog", True, id="nested-lowercase"),
        pytest.param(
            "oci://registry.example.test/team_v2/catalog.name--final__2",
            True, id="legal-repository-separators",
        ),
        pytest.param("https://registry.example.test/team/catalog", False, id="wrong-scheme"),
        pytest.param("oci://registry.example.test", False, id="missing-repository"),
        pytest.param("oci://registry.example.test/", False, id="empty-repository"),
        pytest.param("oci://registry.example.test/team/Catalog", False, id="uppercase-repository"),
        pytest.param("oci://registry.example.test/.catalog", False, id="leading-separator"),
        pytest.param("oci://registry.example.test/catalog-", False, id="trailing-separator"),
        pytest.param("oci://registry.example.test/team//catalog", False, id="empty-segment"),
        pytest.param("oci://registry.example.test/team/catalog/", False, id="trailing-slash"),
        pytest.param("oci://registry.example.test/team/catalog:v1", False, id="embedded-tag"),
        pytest.param(
            "oci://registry.example.test/team/catalog@sha256:" + "a" * 64,
            False, id="embedded-digest",
        ),
    ],
)
def test_validate_oci_profile_repository_locator(endpoint, valid):
    profile = {"name": "oci", "endpoint": endpoint, "parameters": {"reference": "v1"}}
    before = deepcopy(profile)

    if valid:
        assert validate_profile(profile) is None
    else:
        with pytest.raises(FederationError) as raised:
            validate_profile(profile)
        assert raised.value.code == "invalid_package"
        assert str(raised.value) == "OCI repository locator"
    assert profile == before
    assert profile["parameters"] == {"reference": "v1"}


@pytest.mark.parametrize(
    ("parameters", "valid"),
    [
        pytest.param({"revision": "refs/heads/main"}, True, id="full-branch-ref"),
        pytest.param({"revision": "refs/tags/release-1"}, True, id="full-tag-ref"),
        pytest.param({"revision": "0123456789abcdef" * 2 + "01234567"}, True, id="object-id-40-lowercase"),
        pytest.param({"revision": "ABCDEF0123456789" * 4}, True, id="object-id-64-uppercase"),
        pytest.param({"revision": "A" * 40}, True, id="object-id-40-uppercase"),
        pytest.param({"revision": "a" * 64}, True, id="object-id-64-lowercase"),
        pytest.param({"revision": "a" * 39}, False, id="object-id-39"),
        pytest.param({"revision": "a" * 41}, False, id="object-id-41"),
        pytest.param({"revision": "a" * 63}, False, id="object-id-63"),
        pytest.param({"revision": "a" * 65}, False, id="object-id-65"),
        pytest.param({"revision": "g" * 40}, False, id="object-id-nonhex"),
        pytest.param({"revision": "HEAD"}, False, id="symbolic-head"),
        pytest.param({"revision": "main"}, False, id="short-branch"),
        pytest.param({"revision": ""}, False, id="empty-revision"),
        pytest.param({}, False, id="missing-revision"),
        pytest.param({"revision": None}, False, id="null-revision"),
        pytest.param({"revision": 7}, False, id="numeric-revision"),
        pytest.param({"revision": "refs/heads/main/"}, False, id="ref-trailing-slash"),
        pytest.param({"revision": "refs//main"}, False, id="ref-empty-segment"),
        pytest.param({"revision": "refs/.heads/main"}, False, id="ref-dot-prefix"),
        pytest.param({"revision": "refs/heads/main."}, False, id="ref-dot-suffix"),
        pytest.param({"revision": "refs/heads/main.lock"}, False, id="ref-lock-suffix"),
        pytest.param({"revision": "refs/heads/to..pic"}, False, id="ref-double-dot"),
        pytest.param({"revision": "refs/heads/topic one"}, False, id="ref-whitespace"),
        pytest.param({"revision": "refs/heads/topic~1"}, False, id="ref-tilde"),
        pytest.param({"revision": "refs/heads/topic^"}, False, id="ref-caret"),
        pytest.param({"revision": "refs/heads/topic:one"}, False, id="ref-colon"),
        pytest.param({"revision": "refs/heads/topic?"}, False, id="ref-question"),
        pytest.param({"revision": "refs/heads/topic*"}, False, id="ref-star"),
        pytest.param({"revision": "refs/heads/to[pic"}, False, id="ref-bracket"),
        pytest.param({"revision": "refs/heads/topic\\one"}, False, id="ref-backslash"),
        pytest.param({"revision": "refs/heads/topic@{1}"}, False, id="ref-reflog-syntax"),
    ],
)
def test_validate_git_profile_revision_forms(parameters, valid):
    profile = {
        "name": "git",
        "endpoint": "https://git.example.test/team/catalog.git",
        "parameters": deepcopy(parameters),
    }
    before = deepcopy(profile)

    if valid:
        assert validate_profile(profile) is None
    else:
        with pytest.raises(FederationError) as raised:
            validate_profile(profile)
        assert raised.value.code == "invalid_package"
        assert str(raised.value) == "Git revision is not pinned input"
    assert profile == before
    assert "path" not in profile["parameters"]


@pytest.mark.parametrize(
    ("path_fields", "valid"),
    [
        pytest.param({}, True, id="omitted-default"),
        pytest.param({"path": ""}, True, id="empty-repository-root"),
        pytest.param({"path": "xregistry"}, True, id="explicit-default"),
        pytest.param({"path": "nested/xregistry"}, True, id="nested-root"),
        pytest.param({"path": "/xregistry"}, False, id="absolute-root"),
        pytest.param({"path": "xregistry/"}, False, id="trailing-slash"),
        pytest.param({"path": "."}, False, id="dot"),
        pytest.param({"path": ".."}, False, id="parent"),
        pytest.param({"path": "../xregistry"}, False, id="leading-parent"),
        pytest.param({"path": "a/./b"}, False, id="internal-dot"),
        pytest.param({"path": "a/../b"}, False, id="internal-parent"),
        pytest.param({"path": "a//b"}, False, id="internal-empty"),
        pytest.param({"path": "a\\b"}, False, id="backslash"),
        pytest.param({"path": "a:b"}, False, id="colon"),
        pytest.param({"path": "C:/xregistry"}, False, id="windows-absolute"),
        pytest.param({"path": None}, False, id="null"),
        pytest.param({"path": 7}, False, id="numeric"),
    ],
)
def test_validate_git_profile_path_boundaries(path_fields, valid):
    profile = {
        "name": "git",
        "endpoint": "https://git.example.test/team/catalog.git",
        "parameters": {"revision": "refs/heads/main", **path_fields},
    }
    before = deepcopy(profile)

    if valid:
        assert validate_profile(profile) is None
    else:
        with pytest.raises(FederationError) as raised:
            validate_profile(profile)
        assert raised.value.code == "policy_denied"
        assert str(raised.value) == "Unsafe Git format root"
    assert profile == before
    assert profile["parameters"]["revision"] == "refs/heads/main"


@pytest.mark.parametrize(
    ("scheme", "valid"),
    [
        pytest.param("https", True, id="https"),
        pytest.param("http", False, id="http"),
        pytest.param("ssh", False, id="ssh"),
        pytest.param("git", False, id="git"),
    ],
)
def test_validate_git_profile_requires_https(scheme, valid):
    profile = {
        "name": "git",
        "endpoint": f"{scheme}://git.example.test/team/catalog.git",
        "parameters": {"revision": "refs/heads/main", "path": "nested/xregistry"},
    }
    before = deepcopy(profile)

    if valid:
        assert validate_profile(profile) is None
    else:
        with pytest.raises(FederationError) as raised:
            validate_profile(profile)
        assert raised.value.code == "unsupported_operation"
        assert str(raised.value) == "Git transport not HTTPS"
    assert profile == before


@pytest.mark.parametrize(
    ("endpoint", "parameters", "code", "message"),
    [
        pytest.param("file:///catalog", {"layout": "document-tree"}, None, None, id="empty-authority"),
        pytest.param("file:/catalog", {"layout": "document-tree"}, None, None, id="absent-authority"),
        pytest.param("file://localhost/catalog", {"layout": "document-tree"}, None, None, id="localhost"),
        pytest.param("file:///catalog", {"layout": "oci-layout", "reference": "release-1"}, None, None, id="oci-layout-tag"),
        pytest.param(
            "file:///catalog", {"layout": "oci-layout", "reference": "sha256:" + "a" * 64},
            None, None, id="oci-layout-digest",
        ),
        pytest.param(
            "file://other.example.test/catalog", {"layout": "document-tree"},
            "policy_denied", "Non-local file authority", id="remote-authority",
        ),
        pytest.param(
            "file:catalog", {"layout": "document-tree"},
            "invalid_package", "File endpoint must be absolute", id="relative-path",
        ),
        pytest.param(
            "file://localhost", {"layout": "document-tree"},
            "invalid_package", "File endpoint must be absolute", id="missing-path",
        ),
        pytest.param(
            "https://localhost/catalog", {"layout": "document-tree"},
            "invalid_package", "File endpoint must be absolute", id="wrong-scheme",
        ),
        pytest.param("file:///catalog", {}, "invalid_package", "Unknown file layout", id="missing-layout"),
        pytest.param(
            "file:///catalog", {"layout": "packed"},
            "invalid_package", "Unknown file layout", id="unknown-layout",
        ),
        pytest.param(
            "file:///catalog", {"layout": None},
            "invalid_package", "Unknown file layout", id="null-layout",
        ),
        pytest.param(
            "file:///catalog", {"layout": "oci-layout"},
            "invalid_package", "Missing or invalid OCI reference", id="oci-missing-reference",
        ),
        pytest.param(
            "file:///catalog", {"layout": "oci-layout", "reference": ""},
            "invalid_package", "Missing or invalid OCI reference", id="oci-invalid-reference",
        ),
        pytest.param(
            "file:///catalog", {"layout": "document-tree", "reference": "v1"},
            "unsupported_operation", "Document tree has no tag", id="document-tree-reference",
        ),
        pytest.param(
            "file:///catalog", {"layout": "document-tree", "reference": None},
            "unsupported_operation", "Document tree has no tag", id="document-tree-null-reference",
        ),
    ],
)
def test_validate_file_profile_layout_authority_and_reference_rules(
    endpoint, parameters, code, message
):
    profile = {"name": "file", "endpoint": endpoint, "parameters": deepcopy(parameters)}
    before = deepcopy(profile)

    if code is None:
        assert validate_profile(profile) is None
    else:
        with pytest.raises(FederationError) as raised:
            validate_profile(profile)
        assert raised.value.code == code
        assert str(raised.value) == message
    assert profile == before


@pytest.mark.parametrize(
    ("parameters", "message"),
    [
        pytest.param({"registryroot": "i=0"}, "Null NodeId is not a Registry root", id="numeric-zero"),
        pytest.param({"registryroot": "i=2253"}, None, id="numeric"),
        pytest.param({"registryroot": "s=Registry"}, None, id="string"),
        pytest.param(
            {"registryroot": "g=12345678-1234-1234-1234-123456789abc"},
            None, id="canonical-guid",
        ),
        pytest.param({"registryroot": "b=AQID"}, None, id="bytes"),
        pytest.param({"registryroot": "b=+/8="}, None, id="bytes-alphabet-padding"),
        pytest.param(
            {"registryroot": "nsu=urn:example:registry;s=Root"},
            None, id="namespace-uri-string",
        ),
        pytest.param(
            {"registryroot": "nsu=urn:example:registry;i=2253"},
            None, id="namespace-uri-numeric",
        ),
        pytest.param({}, "NodeId must be a string", id="missing-root"),
        pytest.param({"registryroot": ""}, "NodeId must be a string", id="empty-root"),
        pytest.param({"registryroot": None}, "NodeId must be a string", id="null-root"),
        pytest.param({"registryroot": 2253}, "NodeId must be a string", id="numeric-not-string"),
        pytest.param({"registryroot": "ns=2;s=Root"}, "Missing NodeId identifier", id="namespace-index"),
        pytest.param({"registryroot": "nsu=;s=Root"}, "Namespace URI must be a string", id="empty-namespace-uri"),
        pytest.param({"registryroot": "i=-1"}, "Invalid Numeric identifier", id="negative-numeric-id"),
        pytest.param({"registryroot": "s="}, "Null NodeId is not a Registry root", id="empty-string-id"),
        pytest.param({"registryroot": "g="}, "Invalid Guid identifier", id="empty-guid-id"),
        pytest.param({"registryroot": "b="}, "Null NodeId is not a Registry root", id="empty-bytes-id"),
        pytest.param({"registryroot": "b=not_base64"}, "Invalid Opaque identifier Base64", id="invalid-base64-alphabet"),
    ],
)
def test_validate_opcua_profile_portable_root_forms(parameters, message):
    profile = {
        "name": "opcua",
        "endpoint": "opc.tcp://ua.example.test:4840",
        "parameters": deepcopy(parameters),
    }
    before = deepcopy(profile)

    if message is None:
        assert validate_profile(profile) is None
    else:
        with pytest.raises(FederationError) as raised:
            validate_profile(profile)
        assert raised.value.code == "invalid_package"
        assert str(raised.value) == message
    assert profile == before


@pytest.mark.parametrize(
    ("endpoint", "valid"),
    [
        pytest.param("opc.tcp://ua.example.test:4840", True, id="opc-tcp"),
        pytest.param("https://ua.example.test/registry", True, id="https"),
        pytest.param("opc.wss://ua.example.test/registry", True, id="opc-wss"),
        pytest.param("ftp://ua.example.test/registry", False, id="unsupported-transport"),
    ],
)
def test_validate_opcua_profile_endpoint_and_identity_uris(endpoint, valid):
    profile = {
        "name": "opcua",
        "endpoint": endpoint,
        "parameters": {
            "registryroot": "nsu=urn:example:registry;s=Root",
            "applicationuri": "urn:example:server",
            "transportprofileuri": "https://profiles.example.test/ua/transport",
        },
    }
    before = deepcopy(profile)

    if valid:
        assert validate_profile(profile) is None
    else:
        with pytest.raises(FederationError) as raised:
            validate_profile(profile)
        assert raised.value.code == "unsupported_operation"
        assert str(raised.value) == "Unsupported UA transport"
    assert profile == before
    assert profile["parameters"]["applicationuri"] == "urn:example:server"
    assert profile["parameters"]["applicationuri"] != profile["endpoint"]


@pytest.mark.parametrize("parameter", ["applicationuri", "transportprofileuri"])
@pytest.mark.parametrize(
    ("value", "code", "message"),
    [
        pytest.param("/relative", "invalid_package", "Endpoint must be absolute", id="relative-uri"),
        pytest.param(None, "invalid_package", "Endpoint must be a URI", id="null-uri"),
        pytest.param(
            "https://reader@profiles.example.test/ua", "policy_denied",
            "Embedded credentials prohibited", id="embedded-credentials",
        ),
    ],
)
def test_validate_opcua_profile_rejects_invalid_identity_uris(parameter, value, code, message):
    profile = {
        "name": "opcua",
        "endpoint": "opc.tcp://ua.example.test:4840",
        "parameters": {"registryroot": "i=2253", parameter: value},
    }
    before = deepcopy(profile)

    with pytest.raises(FederationError) as raised:
        validate_profile(profile)

    assert raised.value.code == code
    assert str(raised.value) == message
    assert profile == before


def test_select_profile_returns_supported_original_profile():
    profile = {"name": "http", "endpoint": "https://example.test/nonroot/registry"}
    entry = {"name": "Catalog", "federationprofiles": [profile]}
    before = deepcopy(entry)

    selected = select_profile(entry, {"http"})

    assert selected is profile
    assert selected == {"name": "http", "endpoint": "https://example.test/nonroot/registry"}
    assert entry == before


@pytest.mark.parametrize(
    ("entry", "supported", "name"),
    [
        pytest.param({}, {"http"}, None, id="absent-advertisements"),
        pytest.param({"federationprofiles": []}, {"http"}, None, id="empty-advertisements"),
        pytest.param({"url": "https://website.example.test"}, {"http"}, None, id="website-only"),
        pytest.param(
            {
                "labels": {"binding": "http"},
                "relationships": {"registry": {"url": "https://example.test"}},
                "category": "registry",
            },
            {"http"}, None, id="descriptive-metadata-only",
        ),
        pytest.param(
            {"federationprofiles": [{"name": "example.extension", "endpoint": "urn:example:catalog"}]},
            {"http"}, None, id="unknown-profile-only",
        ),
        pytest.param(
            {"federationprofiles": [{"name": "http", "endpoint": "https://example.test"}]},
            {"file"}, None, id="excluded-supported-set",
        ),
        pytest.param(
            {"federationprofiles": [{"name": "http", "endpoint": "https://example.test"}]},
            set(), None, id="empty-supported-set",
        ),
        pytest.param(
            {"federationprofiles": [{"name": "http", "endpoint": "https://example.test"}]},
            {"HTTP"}, None, id="supported-name-case",
        ),
        pytest.param(
            {"federationprofiles": [{"name": "http", "endpoint": "https://example.test"}]},
            {"http"}, "HTTP", id="caller-name-case",
        ),
    ],
)
def test_select_profile_rejects_no_eligible_candidate(entry, supported, name):
    before = deepcopy(entry)
    supported_before = supported.copy()

    with pytest.raises(FederationError) as raised:
        select_profile(entry, supported, name=name)

    assert raised.value.code == "unsupported_binding"
    assert str(raised.value) == "No supported advertisement"
    assert entry == before
    assert supported == supported_before


@pytest.mark.parametrize(
    ("candidates", "message"),
    [
        pytest.param(None, "Profiles must be an array", id="null-array"),
        pytest.param({}, "Profiles must be an array", id="mapping-array"),
        pytest.param((), "Profiles must be an array", id="tuple-array"),
        pytest.param("http", "Profiles must be an array", id="string-array"),
        pytest.param([None], "Advertisement must be an object", id="null-advertisement"),
        pytest.param(["http"], "Advertisement must be an object", id="string-advertisement"),
        pytest.param([{}], "Missing profile name", id="missing-name"),
        pytest.param([{"name": ""}], "Missing profile name", id="empty-name"),
        pytest.param([{"name": None}], "Missing profile name", id="null-name"),
        pytest.param([{"name": 7}], "Missing profile name", id="numeric-name"),
        pytest.param(
            [{"name": "http", "endpoint": "https://example.test"}, {"endpoint": "urn:example:other"}],
            "Missing profile name", id="malformed-after-eligible-candidate",
        ),
    ],
)
def test_select_profile_validates_candidate_shapes_before_filtering(candidates, message):
    entry = {"federationprofiles": deepcopy(candidates)}
    before = deepcopy(entry)

    with pytest.raises(FederationError) as raised:
        select_profile(entry, {"http"})

    assert raised.value.code == "invalid_package"
    assert str(raised.value) == message
    assert entry == before


@pytest.mark.parametrize(
    ("other", "supported", "name", "message"),
    [
        pytest.param(
            {"name": "example.extension", "endpoint": "/invalid", "priority": -1, "parameters": []},
            {"http"}, None, "Endpoint must be absolute", id="unsupported-malformed-fields",
        ),
        pytest.param(
            {"name": "git", "endpoint": "https://git.example.test/catalog", "priority": -1, "parameters": []},
            {"http", "git"}, "http", "Priority must be unsigned integer", id="caller-filter-before-priority",
        ),
        pytest.param(
            {"name": "http", "endpoint": "https://loser.example.test", "priority": 9, "parameters": []},
            {"http"}, None, "Parameters must be an object", id="eligible-loser-parameters-not-validated",
        ),
    ],
)
def test_select_profile_filters_before_priority_and_parameter_validation(other, supported, name, message):
    winner = {"name": "http", "endpoint": "https://selected.example.test/nonroot/registry"}
    entry = {"federationprofiles": [deepcopy(other), winner]}
    before = deepcopy(entry)

    selected = select_profile(entry, supported, name=name)

    assert selected is winner
    assert selected == {"name": "http", "endpoint": "https://selected.example.test/nonroot/registry"}
    assert entry == before
    # Real validation would reject the other entry. Selection must not validate it.
    with pytest.raises(FederationError) as raised:
        validate_profile(other)
    assert raised.value.code == "invalid_package"
    assert str(raised.value) == message


@pytest.mark.parametrize(
    "priority",
    [
        pytest.param(-1, id="negative"),
        pytest.param(True, id="boolean"),
        pytest.param(0.0, id="float"),
        pytest.param("0", id="string"),
        pytest.param(None, id="null"),
    ],
)
def test_select_profile_rejects_invalid_eligible_priority(priority):
    entry = {
        "federationprofiles": [
            {"name": "http", "endpoint": "https://first.example.test", "priority": 0},
            {"name": "http", "endpoint": "https://second.example.test", "priority": priority},
        ]
    }
    before = deepcopy(entry)

    with pytest.raises(FederationError) as raised:
        select_profile(entry, {"http"})

    assert raised.value.code == "invalid_package"
    assert str(raised.value) == "Invalid candidate priority"
    assert entry == before


@pytest.mark.parametrize(
    ("first_fields", "second_fields", "reverse", "expected"),
    [
        pytest.param({}, {"priority": 5}, False, "first", id="omitted-versus-positive"),
        pytest.param({"priority": 0}, {"priority": 5}, False, "first", id="zero-versus-positive"),
        pytest.param({}, {"priority": 0}, False, "first", id="omitted-first-zero-tie"),
        pytest.param({}, {"priority": 0}, True, "second", id="explicit-zero-first-reversed-tie"),
        pytest.param({"priority": 7}, {"priority": 7}, False, "first", id="positive-tie-original-order"),
        pytest.param({"priority": 7}, {"priority": 7}, True, "second", id="positive-tie-reversed-order"),
        pytest.param({"priority": 7}, {"priority": 2}, False, "second", id="lower-priority-later"),
    ],
)
def test_select_profile_priority_default_zero_and_array_ties(
    first_fields, second_fields, reverse, expected
):
    first = {"name": "http", "endpoint": "https://first.example.test/registry", **first_fields}
    second = {"name": "http", "endpoint": "https://second.example.test/registry", **second_fields}
    profiles = [second, first] if reverse else [first, second]
    entry = {"federationprofiles": profiles}
    before = deepcopy(entry)
    expected_profile = {"first": first, "second": second}[expected]
    expected_endpoint = {
        "first": "https://first.example.test/registry",
        "second": "https://second.example.test/registry",
    }[expected]

    selected = select_profile(entry, {"http"})

    assert selected is expected_profile
    assert (selected["name"], selected["endpoint"]) == ("http", expected_endpoint)
    assert entry == before


@pytest.mark.parametrize(
    ("name", "valid"),
    [pytest.param("http", True, id="caller-preference"), pytest.param("HTTP", False, id="case-mismatch")],
)
def test_select_profile_caller_name_precedes_ranking_and_is_case_sensitive(name, valid):
    file_profile = {
        "name": "file", "endpoint": "file:///catalog", "priority": 0,
        "parameters": {"layout": "document-tree"},
    }
    http_profile = {"name": "http", "endpoint": "https://preferred.example.test/registry", "priority": 7}
    entry = {"federationprofiles": [file_profile, http_profile]}
    before = deepcopy(entry)

    if valid:
        selected = select_profile(entry, {"file", "http"}, name=name)
        assert selected is http_profile
        assert selected == {
            "name": "http", "endpoint": "https://preferred.example.test/registry", "priority": 7,
        }
    else:
        with pytest.raises(FederationError) as raised:
            select_profile(entry, {"file", "http"}, name=name)
        assert raised.value.code == "unsupported_binding"
        assert str(raised.value) == "No supported advertisement"
    assert entry == before


@pytest.mark.parametrize(
    ("file_priority", "expected_name"),
    [
        pytest.param(None, "http", id="xregurl-only"),
        pytest.param(0, "file", id="explicit-file-ties-xregurl"),
        pytest.param(1, "http", id="xregurl-priority-zero-wins"),
    ],
)
def test_select_profile_xregurl_http_is_appended_after_explicit_profiles(file_priority, expected_name):
    file_profile = {
        "name": "file", "endpoint": "file:///catalog", "priority": file_priority,
        "parameters": {"layout": "document-tree"},
    }
    entry = {"xregurl": "https://xregurl.example.test/nonroot/registry"}
    if file_priority is not None:
        entry["federationprofiles"] = [file_profile]
    before = deepcopy(entry)

    selected = select_profile(entry, {"http", "file"})

    assert selected["name"] == expected_name
    if expected_name == "file":
        assert selected is file_profile
        assert selected["endpoint"] == "file:///catalog"
    else:
        assert selected == {"name": "http", "endpoint": "https://xregurl.example.test/nonroot/registry"}
        assert "priority" not in selected
    assert entry == before


@pytest.mark.parametrize(
    "include_other_http",
    [
        pytest.param(False, id="matching-explicit-retains-implicit-zero"),
        pytest.param(True, id="one-matching-http-is-sufficient"),
    ],
)
def test_select_profile_matching_explicit_http_preserves_xregurl_candidate(include_other_http):
    matching = {"name": "http", "endpoint": "https://xregurl.example.test/registry", "priority": 5}
    file_profile = {
        "name": "file", "endpoint": "file:///catalog", "priority": 2,
        "parameters": {"layout": "document-tree"},
    }
    other_http = {"name": "http", "endpoint": "https://other.example.test/registry", "priority": 1}
    profiles = [matching, file_profile, other_http] if include_other_http else [matching, file_profile]
    entry = {"xregurl": "https://xregurl.example.test/registry", "federationprofiles": profiles}
    before = deepcopy(entry)

    selected = select_profile(entry, {"http", "file"})

    assert selected == {"name": "http", "endpoint": "https://xregurl.example.test/registry"}
    assert selected.get("priority", 0) == 0
    assert all(selected is not profile for profile in profiles)
    assert entry == before


@pytest.mark.parametrize(
    "explicit_endpoint",
    [
        pytest.param("https://other.example.test/registry", id="different-endpoint"),
        pytest.param("https://xregurl.example.test/registry/", id="trailing-slash-only"),
        pytest.param("https://LEGACY.example.test/registry", id="host-case-only"),
    ],
)
def test_select_profile_rejects_xregurl_http_conflicts(explicit_endpoint):
    entry = {
        "xregurl": "https://xregurl.example.test/registry",
        "federationprofiles": [{"name": "http", "endpoint": explicit_endpoint}],
    }
    before = deepcopy(entry)

    with pytest.raises(FederationError) as raised:
        select_profile(entry, {"http"})

    assert raised.value.code == "invalid_package"
    assert str(raised.value) == "Conflicting xregurl"
    assert entry == before


@pytest.mark.parametrize(
    ("xregurl", "code", "message"),
    [
        pytest.param("/registry", "invalid_package", "Endpoint must be absolute", id="relative-xregurl"),
        pytest.param("ftp://xregurl.example.test/registry", "invalid_package", "HTTP endpoint scheme", id="non-http-xregurl"),
        pytest.param(
            "https://reader@xregurl.example.test/registry", "policy_denied",
            "Embedded credentials prohibited", id="credential-bearing-xregurl",
        ),
    ],
)
def test_select_profile_validates_xregurl_http_even_if_not_selected(xregurl, code, message):
    entry = {
        "xregurl": xregurl,
        "federationprofiles": [
            {"name": "file", "endpoint": "file:///catalog", "priority": 0, "parameters": {"layout": "document-tree"}},
        ],
    }
    before = deepcopy(entry)

    with pytest.raises(FederationError) as raised:
        select_profile(entry, {"http", "file"})

    assert raised.value.code == code
    assert str(raised.value) == message
    assert entry == before


@pytest.mark.parametrize(
    ("selected_profile", "code", "message"),
    [
        pytest.param(
            {
                "name": "git", "endpoint": "https://git.example.test/catalog.git", "priority": 0,
                "parameters": {"revision": "refs/heads/main", "path": "../outside"},
            },
            "policy_denied", "Unsafe Git format root", id="selected-policy-error",
        ),
        pytest.param(
            {"name": "http", "endpoint": "https://first.example.test", "priority": 0, "parameters": {"future": True}},
            "unsupported_operation", "Unknown profile parameter", id="selected-unsupported-parameter",
        ),
        pytest.param(
            {"name": "oci", "endpoint": "oci://registry.example.test/catalog", "priority": 0},
            "invalid_package", "Missing or invalid OCI reference", id="selected-missing-reference",
        ),
    ],
)
def test_select_profile_does_not_fallback_after_selected_validation_error(selected_profile, code, message):
    alternate = {"name": "http", "endpoint": "https://alternate.example.test/registry", "priority": 5}
    entry = {"federationprofiles": [deepcopy(selected_profile), alternate]}
    before = deepcopy(entry)
    assert validate_profile(alternate) is None

    with pytest.raises(FederationError) as raised:
        select_profile(entry, {"git", "http", "oci"})

    assert raised.value.code == code
    assert str(raised.value) == message
    assert entry == before
    assert alternate == {"name": "http", "endpoint": "https://alternate.example.test/registry", "priority": 5}
