"""Source examples and an abstract link projection for Core issue 580."""

from copy import deepcopy
from pathlib import Path
import re
from urllib.parse import quote, unquote, urlsplit

from jsonpointer import resolve_pointer
import pytest


SPEC = (Path(__file__).resolve().parents[1] / "core" / "spec.md").read_text(
    encoding="utf-8"
)
DOC_FLAG = SPEC.split("### Doc Flag\n", 1)[1].split("\n### ", 1)[0]
SELF = SPEC.split("##### `self` Attribute\n", 1)[1].split("\n##### ", 1)[0]
BASE = "http://example.com/myreg"
LINKS = {
    "self", "schemagroupsurl", "schemasurl", "versionsurl",
    "metaurl", "defaultversionurl",
}
EXAMPLES = re.findall(r"^\| `(http[^`]+)` \| `([^`]+)` \|$", DOC_FLAG, re.M)


def _fragment(tokens):
    pointer = "".join("/" + token.replace("~", "~0").replace("/", "~1")
                      for token in tokens)
    return "#" + quote(pointer, safe="/~")


def _resolve(document, fragment):
    assert fragment.startswith("#")
    return resolve_pointer(document, unquote(fragment[1:], errors="strict"))


def _at(document, tokens):
    for token in tokens:
        document = document[token]
    return document


def _registry(group_id="g1", schema_id="s1", version_id="v1"):
    group_path = ("schemagroups", group_id)
    resource_path = group_path + ("schemas", schema_id)
    version_path = resource_path + ("versions", version_id)
    group_url = BASE + "/" + "/".join(group_path)
    resource_url = BASE + "/" + "/".join(resource_path)
    version_url = BASE + "/" + "/".join(version_path)
    version = {
        "versionid": version_id,
        "xid": "/" + "/".join(version_path),
        "self": version_url + "$details",
    }
    meta = {
        "schemaid": schema_id,
        "self": resource_url + "/meta",
        "defaultversionurl": version_url + "$details",
    }
    resource = {
        "schemaid": schema_id,
        "xid": "/" + "/".join(resource_path),
        "self": resource_url + "$details",
        "metaurl": resource_url + "/meta",
        "meta": meta,
        "versionsurl": resource_url + "/versions",
        "versions": {version_id: version},
    }
    group = {
        "schemagroupid": group_id,
        "self": group_url,
        "schemasurl": group_url + "/schemas",
        "schemas": {schema_id: resource},
    }
    registry = {
        "registryid": "myreg",
        "self": BASE,
        "schemagroupsurl": BASE + "/schemagroups",
        "schemagroups": {group_id: group},
    }
    targets = {
        BASE: (),
        BASE + "/schemagroups": ("schemagroups",),
        group_url: group_path,
        group_url + "/schemas": group_path + ("schemas",),
        resource_url + "$details": resource_path,
        resource_url + "/meta": resource_path + ("meta",),
        resource_url + "/versions": resource_path + ("versions",),
        version_url + "$details": version_path,
    }
    return registry, targets


def _links(document, path=()):
    for key, value in document.items():
        if key in LINKS:
            yield path + (key,), value
        if isinstance(value, dict):
            yield from _links(value, path + (key,))


def _project_links(document, locations):
    result = deepcopy(document)
    for path, url in _links(result):
        if url in locations:
            _at(result, path[:-1])[path[-1]] = _fragment(locations[url])
    return result


@pytest.mark.parametrize("request_url,fragment", EXAMPLES)
def test_spec_doc_examples_resolve_at_their_response_roots(request_url, fragment):
    registry, _ = _registry()
    root = tuple(part for part in urlsplit(request_url.strip()).path.split("/")[2:]
                 if part)
    response = _at(registry, root)
    resource = registry["schemagroups"]["g1"]["schemas"]["s1"]
    assert _resolve(response, fragment) is resource


def test_root_fragment_does_not_address_an_empty_member():
    assert len(EXAMPLES) == 5
    fragment = dict(EXAMPLES)[BASE + "/schemagroups/g1/schemas/s1"]
    resource = {"schemaid": "s1", "": {"not": "the resource"}}
    assert fragment == "#"
    assert _resolve(resource, fragment) is resource
    assert _resolve(resource, "#/") is resource[""]


@pytest.mark.parametrize(
    "root",
    [
        (),
        ("schemagroups",),
        ("schemagroups", "g~1"),
        ("schemagroups", "g~1", "schemas"),
        ("schemagroups", "g~1", "schemas", "s~1"),
        ("schemagroups", "g~1", "schemas", "s~1", "meta"),
        ("schemagroups", "g~1", "schemas", "s~1", "versions"),
        ("schemagroups", "g~1", "schemas", "s~1", "versions", "v~1"),
    ],
    ids=["registry", "groups", "group", "resources", "resource", "meta",
         "versions", "version"],
)
def test_response_local_links_resolve_at_every_response_root(root):
    registry, targets = _registry("g~1", "s~1", "v~1")
    original = deepcopy(registry)
    response = _at(registry, root)
    locations = {
        url: path[len(root):]
        for url, path in targets.items()
        if path[:len(root)] == root
    }
    projected = _project_links(response, locations)
    for path, original_url in _links(response):
        actual = _at(projected, path)
        if original_url in locations:
            assert actual == _fragment(locations[original_url])
            assert _resolve(projected, actual) is _at(
                projected, locations[original_url]
            )
            assert "$details" not in actual
        else:
            assert actual == original_url
            assert actual.startswith(BASE)
    assert registry == original


def test_rfc6901_token_escaping_precedes_uri_fragment_encoding():
    target = {"value": 42}
    document = {"a/b": {"m~n": {"c% d": {"\u00e9": target}}}}
    fragment = _fragment(("a/b", "m~n", "c% d", "\u00e9"))
    assert fragment == "#/a~1b/m~0n/c%25%20d/%C3%A9"
    assert _resolve(document, fragment) is target
    assert _resolve({"~1": target, "/": "wrong"}, _fragment(("~1",))) is target


def test_response_local_self_is_not_an_api_xid_suffix():
    registry, targets = _registry("g~1", "s~1")
    resource_path = ("schemagroups", "g~1", "schemas", "s~1")
    api_resource = _at(registry, resource_path)
    api_self = api_resource["self"]
    assert api_self == BASE + api_resource["xid"] + "$details"
    projected = _project_links(registry, targets)
    local_self = _at(projected, resource_path)["self"]
    assert local_self == "#/schemagroups/g~01/schemas/s~01"
    assert not local_self.endswith(api_resource["xid"])
    assert _resolve(projected, local_self) is _at(projected, resource_path)
    resource_response = _project_links(api_resource, {
        url: path[len(resource_path):]
        for url, path in targets.items()
        if path[:len(resource_path)] == resource_path
    })
    assert resource_response["self"] == "#"
    assert api_resource["self"] == api_self


def test_missing_targets_keep_absolute_urls_and_protocol_suffixes():
    registry, _ = _registry()
    root = ("schemagroups", "g1", "schemas", "s1")
    resource = _at(registry, root)
    del resource["meta"]
    del resource["versions"]
    projected = _project_links(resource, {
        resource["self"]: (),
    })
    assert projected["self"] == "#"
    assert projected["metaurl"] == BASE + "/" + "/".join(root) + "/meta"
    assert projected["versionsurl"] == BASE + "/" + "/".join(root) + "/versions"
    meta = {"self": resource["metaurl"],
            "defaultversionurl": BASE + "/" + "/".join(root)
            + "/versions/v1$details"}
    projected_meta = _project_links(meta, {meta["self"]: ()})
    assert projected_meta["self"] == "#"
    assert projected_meta["defaultversionurl"] == meta["defaultversionurl"]


def test_self_source_contract_distinguishes_api_and_response_local_identity():
    text = " ".join(SELF.split())
    assert "relative URL other than a document-view fragment pointer" in text
    assert "not subject to this suffix requirement" in text
    api, document = SELF.split("- API View Constraints:", 1)[1].split(
        "- Document View Constraints:", 1
    )
    assert "MUST be immutable." in api
    assert "MUST be immutable." not in document
    assert "MAY differ between responses with different document roots" in (
        " ".join(document.split())
    )


def test_doc_source_contract_requires_fragment_encoding_and_root_distinction():
    text = " ".join(DOC_FLAG.split())
    assert "rfc6901#section-6" in DOC_FLAG
    assert "`~` as `~0` and `/` as `~1`" in text
    assert "UTF-8" in text and "percent-encoding" in text
    assert "root MUST be `#`" in text
    assert "`#/` instead refers to a member whose name is the empty string" in text
