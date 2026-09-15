import json
from pathlib import Path
import re
from urllib.parse import urlsplit

import pytest

from test_samples import _unique_json_object


ROOT = Path(__file__).resolve().parents[1]
RESOURCE_GET = "#### `GET /<GROUPS>/<GID>/<RESOURCES>/<RID>`"
VERSION_PATCH = "#### `PATCH` and `POST /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions`"


def _json(body):
    return json.loads(body, object_pairs_hook=_unique_json_object)


def _resource_requests():
    text = (ROOT / "core" / "resource.md").read_text(encoding="utf-8")
    return re.findall(
        r"^```\n((?:PUT|POST|PATCH) /[^\n]+)\n\n(.*?)\n```",
        text, re.MULTILINE | re.DOTALL,
    )


def _resource_request(number):
    return _resource_requests()[number - 1]


def _http_examples(heading):
    text = (ROOT / "core" / "http.md").read_text(encoding="utf-8")
    section = text.split(heading + "\n", 1)[1].split("\n#### ", 1)[0]
    section = section.split("**Examples:**", 1)[1]
    blocks = re.findall(r"```yaml\n(.*?)\n```", section, re.DOTALL)
    assert len(blocks) == 2
    return blocks


def _http_body(block):
    return block.split("\n\n", 1)[1]


def _version_map_body():
    response = _http_examples(VERSION_PATCH)[1]
    body, omissions = re.subn(
        r",\n\s*# Remainder of Version entity excluded for brevity\n",
        "\n", _http_body(response),
    )
    assert omissions == 3, "Only the three designated omitted-field markers are removed"
    return body


def test_resource_request_inventory_contains_all_29_literal_bodies():
    text = (ROOT / "core" / "resource.md").read_text(encoding="utf-8")
    assert len(_resource_requests()) == 29
    assert len(re.findall(r"^\*\*Request:\*\*$", text, re.MULTILINE)) == 29


@pytest.mark.parametrize(
    "exchange", _resource_requests(),
    ids=[f"request-{number:02d}" for number in range(1, len(_resource_requests()) + 1)],
)
def test_literal_resource_request_body_is_json(exchange):
    route, body = exchange
    method, url = route.split(" ", 1)
    assert method in {"PUT", "POST", "PATCH"}
    assert urlsplit(url).path.startswith("/dirs/d1/files")
    assert type(_json(body)) is dict


@pytest.mark.parametrize(
    "number, method, expected_meta",
    [
        (19, "PUT", {"defaultversionsticky": True}),
        (20, "PATCH", {"defaultversionsticky": True}),
        (22, "PATCH", {"defaultversionid": "foo"}),
        (23, "PUT", {"defaultversionid": "foo", "defaultversionsticky": True}),
    ],
    ids=["request-19", "request-20", "request-22", "request-23"],
)
def test_resource_meta_member_repairs_preserve_request_shape(number, method, expected_meta):
    route, body = _resource_request(number)
    assert route == method + " /dirs/d1/files/f1"
    parsed = _json(body)
    assert set(parsed) == {"meta"}
    assert parsed["meta"] == expected_meta
    if "defaultversionsticky" in expected_meta:
        assert parsed["meta"]["defaultversionsticky"] is True


def test_resource_comma_repair_preserves_abbreviated_years_and_version_map():
    route, body = _resource_request(24)
    assert route == "PUT /dirs/d1/files/f1"
    parsed = _json(body)
    assert parsed == {
        "name": "foo",
        "createdat": "1999",
        "meta": {"defaultversionsticky": True},
        "versions": {"v2": {"createdat": "1998"}},
    }
    text = (ROOT / "core" / "resource.md").read_text(encoding="utf-8")
    assert 'Timestamps will only use a year or "now"' in text


def test_http_resource_get_response_is_json_without_punctuation_repair():
    request, response = _http_examples(RESOURCE_GET)
    body = _json(_http_body(response))
    request_path = urlsplit(request.splitlines()[0].split()[1]).path.removesuffix("$details")
    assert body["messageid"] == request_path.rsplit("/", 1)[1]
    assert body["xid"] == request_path
    assert urlsplit(body["self"]).path.removesuffix("$details") == request_path


def test_http_version_patch_response_is_a_json_id_map_matching_the_request():
    request, _ = _http_examples(VERSION_PATCH)
    response = _json(_version_map_body())
    assert type(response) is dict
    requested = {
        key: _json(labels)
        for key, labels in re.findall(
            r'^  "([^"]+)": \{\n    "labels": (\{[^\n]+\})',
            request, re.MULTILINE,
        )
    }
    assert len(requested) == 3
    assert set(response) == set(requested)
    resource_id = request.splitlines()[0].split()[1].split("/")[-2]
    for version_id, version in response.items():
        assert version["versionid"] == version_id
        assert version["messageid"] == resource_id
        assert version["labels"] == requested[version_id]


@pytest.mark.parametrize(
    "mutation", ["meta-quote", "member-comma", "self-quote", "map-delimiter", "trailing-comma"]
)
def test_source_derived_punctuation_errors_are_rejected_by_json_parser(mutation):
    if mutation == "meta-quote":
        body = _resource_request(19)[1].replace('"meta":', '"meta:', 1)
    elif mutation == "member-comma":
        body = _resource_request(24)[1].replace('"1999",', '"1999"', 1)
    elif mutation == "self-quote":
        body = _http_body(_http_examples(RESOURCE_GET)[1]).replace(
            '",\n  "xid"', '","\n  "xid"', 1
        )
    elif mutation == "map-delimiter":
        body = _version_map_body().rstrip()[:-1] + "]"
    else:
        body = _resource_request(19)[1].rstrip()[:-1] + ",\n}"
    with pytest.raises(json.JSONDecodeError):
        _json(body)
