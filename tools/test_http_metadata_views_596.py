import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit

import pytest


ROOT = Path(__file__).resolve().parents[1]
RESOURCE_COLLECTION = "#### `GET /<GROUPS>/<GID>/<RESOURCES>`"
RESOURCE_GET = "#### `GET /<GROUPS>/<GID>/<RESOURCES>/<RID>`"
RESOURCE_PUT = "#### `PATCH` and `PUT /<GROUPS>/<GID>/<RESOURCES>/<RID>`"
RESOURCE_POST = "#### `POST /<GROUPS>/<GID>/<RESOURCES>/<RID>`"
META_GET = "#### `GET /<GROUPS>/<GID>/<RESOURCES>/<RID>/meta`"
META_PATCH = "#### `PATCH` and `PUT /<GROUPS>/<GID>/<RESOURCES>/<RID>/meta`"
VERSION_GET = "#### `GET /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>`"
VERSION_PUT = "#### `PATCH` and `PUT /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>`"


def _section(heading):
    text = (ROOT / "core" / "http.md").read_text(encoding="utf-8")
    return text.split(heading + "\n", 1)[1].split("\n#### ", 1)[0]


def _examples(heading):
    section = _section(heading).split("**Examples:**", 1)[1]
    return re.findall(r"```yaml\n(.*?)\n```", section, re.DOTALL)


def _request_url(block):
    return block.splitlines()[0].split()[1]


def _headers(block):
    return dict(
        line.split(": ", 1)
        for line in block.split("\n\n", 1)[0].splitlines()[1:]
    )


def _scalar_fields(block):
    pairs = re.findall(
        r'^  "(self|xid|versionid|defaultversionid|defaultversionurl|readonly)"'
        r': ("[^"\n]*"|true|false)',
        block, re.MULTILINE,
    )
    fields = {name: json.loads(value) for name, value in pairs}
    assert len(fields) == len(pairs), "Duplicate projected fields"
    return fields


def _has_document_member(block):
    return bool(re.search(r'^  "message": \{', block, re.MULTILINE))


def _assert_metadata_url(url, hasdocument):
    parsed = urlsplit(url)
    assert parsed.scheme == "https" and parsed.netloc == "example.com"
    assert parsed.path.endswith("$details") is hasdocument
    assert not parsed.query and not parsed.fragment


def _hasdocument(heading):
    section = " ".join(_section(heading).split("**Examples:**", 1)[1].split())
    match = re.search(
        r"the `(message|schema)` Resource type has `hasdocument` set to `(true|false)`",
        section,
    )
    assert match, "The example's document-type precondition is missing"
    assert match.group(1) == ("schema" if heading == VERSION_GET else "message")
    return match.group(2) == "true"


def test_document_type_preconditions_are_explicit_and_scoped():
    assert _hasdocument(RESOURCE_COLLECTION) is False
    for heading in (
        RESOURCE_GET, RESOURCE_PUT, RESOURCE_POST, META_GET, META_PATCH,
        VERSION_GET, VERSION_PUT,
    ):
        assert _hasdocument(heading) is True


@pytest.mark.parametrize(
    "heading", [RESOURCE_GET, RESOURCE_PUT, RESOURCE_POST, VERSION_GET, VERSION_PUT],
    ids=["resource-get", "resource-put", "resource-post", "schema-version-get", "version-put"],
)
def test_document_bearing_metadata_urls_and_content_location_use_details(heading):
    blocks = _examples(heading)
    request, response = blocks[:2] if heading in (RESOURCE_GET, VERSION_GET) else blocks[-2:]
    request_path = urlsplit(_request_url(request)).path
    body = _scalar_fields(response)
    _assert_metadata_url(body["self"], True)
    assert request_path.endswith("$details")
    assert "$details" not in body["xid"]

    expected_self = request_path
    if heading == RESOURCE_POST:
        version_id = _scalar_fields(request)["versionid"]
        expected_self = request_path.removesuffix("$details") + "/versions/" + version_id + "$details"
    assert urlsplit(body["self"]).path == expected_self

    headers = _headers(response)
    if heading != VERSION_GET:
        location = headers["Content-Location"]
        _assert_metadata_url(location, True)
        expected_location = expected_self
        if heading in (RESOURCE_GET, RESOURCE_PUT):
            expected_location = (
                request_path.removesuffix("$details")
                + "/versions/" + body["versionid"] + "$details"
            )
        assert urlsplit(location).path == expected_location


@pytest.mark.parametrize(
    "heading", [RESOURCE_PUT, RESOURCE_POST, VERSION_PUT, VERSION_GET],
    ids=["resource-put", "resource-post", "version-put", "schema-version-get"],
)
def test_document_view_headers_keep_document_urls_without_details(heading):
    blocks = _examples(heading)
    request, response = blocks[-2:] if heading == VERSION_GET else blocks[:2]
    headers = _headers(response)
    assert "$details" not in _request_url(request)
    assert "$details" not in headers["xRegistry-self"]
    assert "$details" not in headers["xRegistry-xid"]
    assert urlsplit(headers["xRegistry-self"]).path == headers["xRegistry-xid"]
    for name in ("Location", "Content-Location"):
        if name in headers:
            assert "$details" not in headers[name]
    if "Location" in headers:
        assert headers["Location"] == headers["xRegistry-self"]
    assert "xRegistry-message" not in headers


def test_document_in_put_body_does_not_implicitly_request_inline_response():
    request, response = _examples(RESOURCE_PUT)[-2:]
    assert _has_document_member(request)
    assert "inline" not in parse_qs(urlsplit(_request_url(request)).query)
    assert not _has_document_member(response)
    body = json.loads(response[response.index("{"):])
    assert "message" not in body and "messagebase64" not in body
    assert body["self"].endswith("$details")


@pytest.mark.parametrize(
    "heading", [RESOURCE_POST, VERSION_PUT], ids=["resource-post", "version-put"]
)
def test_inline_document_responses_are_explicitly_requested(heading):
    request, response = _examples(heading)[-2:]
    assert parse_qs(urlsplit(_request_url(request)).query) == {"inline": ["message"]}
    assert _has_document_member(request)
    assert _has_document_member(response)
    _assert_metadata_url(_scalar_fields(response)["self"], True)


@pytest.mark.parametrize("heading", [META_GET, META_PATCH], ids=["get", "patch"])
def test_meta_responses_include_false_readonly_and_metadata_default_version_url(heading):
    request, response = _examples(heading)
    body = json.loads(response[response.index("{"):])
    assert "readonly" in body and body["readonly"] is False
    assert urlsplit(body["self"]).path == urlsplit(_request_url(request)).path
    assert "$details" not in body["self"] and "$details" not in body["xid"]
    _assert_metadata_url(body["defaultversionurl"], True)
    resource = urlsplit(body["self"]).path.removesuffix("/meta")
    assert urlsplit(body["defaultversionurl"]).path == (
        resource + "/versions/" + body["defaultversionid"] + "$details"
    )
    if heading == META_PATCH:
        patch = json.loads(request[request.index("{"):])
        assert body["defaultversionid"] == patch["defaultversionid"]
        assert body["defaultversionsticky"] is True
    else:
        assert body["defaultversionsticky"] is False


def test_metadata_only_collection_example_preserves_bare_entity_urls():
    request, response = _examples(RESOURCE_COLLECTION)
    resources = json.loads(response[response.index("{"):])
    assert len(resources) == 1
    for key, body in resources.items():
        _assert_metadata_url(body["self"], False)
        path = _request_url(request) + "/" + key
        assert urlsplit(body["self"]).path == body["xid"] == path
        assert "$details" not in body["metaurl"]
        assert "$details" not in body["versionsurl"]
        assert "message" not in body


def test_suffix_checker_distinguishes_document_and_metadata_only_types():
    document_body = _scalar_fields(_examples(RESOURCE_PUT)[-1])
    metadata_only = json.loads(_examples(RESOURCE_COLLECTION)[-1].split("\n\n", 1)[1])["msg1"]
    _assert_metadata_url(document_body["self"], True)
    _assert_metadata_url(metadata_only["self"], False)
    with pytest.raises(AssertionError):
        _assert_metadata_url(document_body["self"], False)
    with pytest.raises(AssertionError):
        _assert_metadata_url(metadata_only["self"], True)


def test_core_default_version_url_allows_bare_metadata_only_urls():
    core = (ROOT / "core" / "spec.md").read_text(encoding="utf-8")
    section = core.split("#### `defaultversionurl` Attribute\n", 1)[1].split("\n#### ", 1)[0]
    api_url = re.search(r"`(https://[^`]+)` \(API View\)", section).group(1)
    _assert_metadata_url(api_url, False)
    assert "is set to `true`" in section
    assert "this means using the `$details` suffix" in section
