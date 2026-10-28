"""Executable Core HTTP mapping, pagination, cache and capture examples."""

import base64
import copy
from unittest.mock import Mock

import pytest

from workingdrafts.bindings.tools.http_examples import interpret_transcript, request_url
from workingdrafts.federation.tools.federation_examples import (
    FederationError, example_documents, execute_selected, load_example,
)

# Only captured Registry content is shared. Wire protocol and expected results
# stay literal, including transient failures, partial reads and cache headers.
_FIRST = load_example("first")
_DOCUMENTS = example_documents(_FIRST)


def _shared_bytes(version):
    return _DOCUMENTS["/documents/main/assets/item/versions/" + version]


# Protocol vectors retained independently of generated Registry content.
MAPPING = {'format': 'xregistry-http-examples-v1',
 'endpoint': 'https://first.example.com/services/xreg/',
 'modelsource': {'groups': {'documents': {'singular': 'document',
                                          'resources': {'assets': {'singular': 'asset'}}},
                            'categories': {'singular': 'category',
                                           'resources': {'registries': {'singular': 'registry',
                                                                        'hasdocument': False,
                                                                        'attributes': {'xregurl': {'type': 'url'},
                                                                                       'weburl': {'type': 'url'}}}}}}},
 'cases': [
           {'name': 'registry',
            'request': {'operation': 'entity', 'target': '/'},
            'url': 'https://first.example.com/services/xreg/',
            'view': 'metadata'},
           {'name': 'resource-metadata',
            'request': {'operation': 'entity', 'target': '/documents/main/assets/item'},
            'url': 'https://first.example.com/services/xreg/documents/main/assets/item$details',
            'view': 'metadata'},
           {'name': 'resource-meta',
            'request': {'operation': 'entity', 'target': '/documents/main/assets/item/meta'},
            'url': 'https://first.example.com/services/xreg/documents/main/assets/item/meta',
            'view': 'metadata'},
           {'name': 'version-metadata',
            'request': {'operation': 'entity', 'target': '/documents/main/assets/item/versions/v1'},
            'url': 'https://first.example.com/services/xreg/documents/main/assets/item/versions/v1$details',
            'view': 'metadata'},
           {'name': 'default-document',
            'request': {'operation': 'document', 'target': '/documents/main/assets/item'},
            'url': 'https://first.example.com/services/xreg/documents/main/assets/item',
            'view': 'document',
            'defaultversionid': 'v1',
            'availableversions': ['v1', 'v2', 'v3']},
           {'name': 'explicit-document',
            'request': {'operation': 'document',
                        'target': '/documents/main/assets/item/versions/v2'},
            'url': 'https://first.example.com/services/xreg/documents/main/assets/item/versions/v2',
            'view': 'document'},
           {'name': 'metadata-only-has-no-document',
            'request': {'operation': 'document', 'target': '/categories/dev/registries/bridge'},
            'error': 'unsupported_operation'},
            ]}
# Protocol vectors retained independently of generated Registry content.
DATA = {'format': 'xregistry-http-examples-v1',
 'transcripts': [
                 {'name': 'no-filter-catalog',
                  'endpoint': 'https://catalog.example.com/catalog',
                  'selector': {'label': 'stage', 'value': 'PRODUCTION'},
                  'exchanges': [{'request': {'url': 'https://catalog.example.com/catalog/capabilities',
                                             'headers': {}},
                                 'response': {'status': 200,
                                              'headers': {'Content-Type': 'application/json'},
                                              'json': {'available': {'capabilities': {'mutable': False},
                                                                     'entities': {'mutable': False},
                                                                     'model': {'mutable': False}},
                                                       'flags': None,
                                                       'mutable': [],
                                                       'pagination': False,
                                                       'specversions': ['1.0-rc4']}}},
                                {'request': {'url': 'https://catalog.example.com/catalog/categories/dev/registries',
                                             'headers': {}},
                                 'response': {'status': 200,
                                              'headers': {'Content-Type': 'application/json'},
                                              'json': {'bridge': {'registryid': 'bridge',
                                                                  'versionid': 'v1',
                                                                  'self': 'https://catalog.example.com/catalog/categories/dev/registries/bridge',
                                                                  'xid': '/categories/dev/registries/bridge',
                                                                  'epoch': 1,
                                                                  'isdefault': True,
                                                                  'ancestorid': 'v1',
                                                                  'createdat': '2026-09-01T00:00:00Z',
                                                                  'modifiedat': '2026-09-01T00:00:00Z',
                                                                  'labels': {'stage': 'production',
                                                                             'note': ''},
                                                                  'xregurl': 'https://first.example.com/services/xreg/',
                                                                  'metaurl': 'https://catalog.example.com/catalog/categories/dev/registries/bridge/meta',
                                                                  'versionsurl': 'https://catalog.example.com/catalog/categories/dev/registries/bridge/versions',
                                                                  'versionscount': 1},
                                                       'website': {'registryid': 'website',
                                                                   'versionid': 'v1',
                                                                   'self': 'https://catalog.example.com/catalog/categories/dev/registries/website',
                                                                   'xid': '/categories/dev/registries/website',
                                                                   'epoch': 1,
                                                                   'isdefault': True,
                                                                   'ancestorid': 'v1',
                                                                   'createdat': '2026-09-01T00:00:00Z',
                                                                   'modifiedat': '2026-09-01T00:00:00Z',
                                                                   'weburl': 'https://www.example.com/',
                                                                   'metaurl': 'https://catalog.example.com/catalog/categories/dev/registries/website/meta',
                                                                   'versionsurl': 'https://catalog.example.com/catalog/categories/dev/registries/website/versions',
                                                                   'versionscount': 1}}}}],
                  'expected': {'xid': '/categories/dev/registries/bridge',
                               'endpoint': 'https://first.example.com/services/xreg/',
                               'documentReads': 0}},
                 {'name': 'filtered-pages',
                  'endpoint': 'https://first.example.com/services/xreg/',
                  'selector': {'label': 'stage', 'value': 'PRODUCTION'},
                  'exchanges': [{'request': {'url': 'https://first.example.com/services/xreg/documents/main/assets?filter=labels.stage%3DPRODUCTION&limit=1',
                                             'headers': {}},
                                 'response': {'status': 200,
                                              'headers': {'Content-Type': 'application/json',
                                                          'Link': '<?cursor=opaque%2B2>;rel=next;count=1'},
                                              'json': {}}},
                                {'request': {'url': 'https://first.example.com/services/xreg/documents/main/assets?cursor=opaque%2B2',
                                             'headers': {}},
                                 'response': {'status': 200,
                                              'headers': {'Content-Type': 'application/json'},
                                              'json': {'item': {'assetid': 'item',
                                                                'versionid': 'v1',
                                                                'self': 'https://first.example.com/services/xreg/documents/main/assets/item$details',
                                                                'xid': '/documents/main/assets/item',
                                                                'epoch': 1,
                                                                'isdefault': True,
                                                                'ancestorid': 'v1',
                                                                'createdat': '2026-09-01T00:00:00Z',
                                                                'modifiedat': '2026-09-01T00:00:00Z',
                                                                'labels': {'stage': 'production'},
                                                                'metaurl': 'https://first.example.com/services/xreg/documents/main/assets/item/meta',
                                                                'versionsurl': 'https://first.example.com/services/xreg/documents/main/assets/item/versions',
                                                                'versionscount': 3}}}}],
                  'expected': {'xid': '/documents/main/assets/item', 'pages': 2}},
                 {'name': 'later-page-ambiguity',
                  'endpoint': 'https://first.example.com/services/xreg/',
                  'selector': {'label': 'stage', 'value': 'PRODUCTION'},
                  'exchanges': [{'request': {'url': 'https://first.example.com/services/xreg/documents/main/assets',
                                             'headers': {}},
                                 'response': {'status': 200,
                                              'headers': {'Content-Type': 'application/json',
                                                          'Link': '<https://first.example.com/services/xreg/documents/main/assets?cursor=next>;rel=next;count=2'},
                                              'json': {'item': {'assetid': 'item',
                                                                'versionid': 'v1',
                                                                'self': 'https://first.example.com/services/xreg/documents/main/assets/item$details',
                                                                'xid': '/documents/main/assets/item',
                                                                'epoch': 1,
                                                                'isdefault': True,
                                                                'ancestorid': 'v1',
                                                                'createdat': '2026-09-01T00:00:00Z',
                                                                'modifiedat': '2026-09-01T00:00:00Z',
                                                                'labels': {'stage': 'production'},
                                                                'metaurl': 'https://first.example.com/services/xreg/documents/main/assets/item/meta',
                                                                'versionsurl': 'https://first.example.com/services/xreg/documents/main/assets/item/versions',
                                                                'versionscount': 3}}}},
                                {'request': {'url': 'https://first.example.com/services/xreg/documents/main/assets?cursor=next',
                                             'headers': {}},
                                 'response': {'status': 200,
                                              'headers': {'Content-Type': 'application/json'},
                                              'json': {'other': {'assetid': 'other',
                                                                 'versionid': 'v1',
                                                                 'self': 'https://first.example.com/services/xreg/documents/main/assets/other$details',
                                                                 'xid': '/documents/main/assets/other',
                                                                 'epoch': 1,
                                                                 'isdefault': True,
                                                                 'ancestorid': 'v1',
                                                                 'createdat': '2026-09-01T00:00:00Z',
                                                                 'modifiedat': '2026-09-01T00:00:00Z',
                                                                 'labels': {'stage': 'PRODUCTION'},
                                                                 'metaurl': 'https://first.example.com/services/xreg/documents/main/assets/other/meta',
                                                                 'versionsurl': 'https://first.example.com/services/xreg/documents/main/assets/other/versions',
                                                                 'versionscount': 1}}}}],
                  'expected': {'error': 'ambiguous'}},
                 {'name': 'document-revalidation',
                  'endpoint': 'https://first.example.com/services/xreg/',
                  'exchanges': [{'request': {'url': 'https://first.example.com/services/xreg/documents/main/assets/item/versions/v1',
                                             'headers': {}},
                                 'response': {'status': 200,
                                              'headers': {'Content-Type': 'application/json',
                                                          'Content-Length': '17',
                                                          'ETag': '"document-v1"',
                                                          'Cache-Control': 'private, max-age=0',
                                                          'xRegistry-assetid': 'item',
                                                          'xRegistry-versionid': 'v1',
                                                          'xRegistry-self': 'https://first.example.com/services/xreg/documents/main/assets/item/versions/v1',
                                                          'xRegistry-xid': '/documents/main/assets/item/versions/v1',
                                                          'xRegistry-epoch': '1',
                                                          'xRegistry-isdefault': 'true',
                                                          'xRegistry-ancestorid': 'v1',
                                                          'xRegistry-createdat': '2026-09-01T00:00:00Z',
                                                          'xRegistry-modifiedat': '2026-09-01T00:00:00Z'},
                                              'text': _shared_bytes("v1").decode("utf-8")}},
                                {'request': {'url': 'https://first.example.com/services/xreg/documents/main/assets/item/versions/v1',
                                             'headers': {'If-None-Match': '"document-v1"'}},
                                 'response': {'status': 304,
                                              'headers': {'ETag': '"document-v1"',
                                                          'Cache-Control': 'private, max-age=0'}}}],
                  'expected': {'text': '{"type":"string"}', 'cacheReuse': True}},
                 {'name': 'document-redirect',
                  'endpoint': 'https://first.example.com/services/xreg/',
                  'policy': {'allowedOrigins': ['https://first.example.com',
                                                'https://content.example.com'],
                             'credentialScope': 'https://first.example.com'},
                  'exchanges': [{'request': {'url': 'https://first.example.com/services/xreg/documents/main/assets/item/versions/v2',
                                             'headers': {'Authorization': 'Bearer '
                                                                          'SYNTHETIC-NONSECRET-TOKEN',
                                                         'If-None-Match': '"source-document-locator"'}},
                                 'response': {'status': 303,
                                              'headers': {'Location': 'https://content.example.com/item-v2.bin',
                                                          'xRegistry-asseturl': 'https://content.example.com/item-v2.bin',
                                                          'xRegistry-assetid': 'item',
                                                          'xRegistry-versionid': 'v2',
                                                          'xRegistry-self': 'https://first.example.com/services/xreg/documents/main/assets/item/versions/v2',
                                                          'xRegistry-xid': '/documents/main/assets/item/versions/v2',
                                                          'xRegistry-epoch': '1',
                                                          'xRegistry-isdefault': 'false',
                                                          'xRegistry-ancestorid': 'v1',
                                                          'xRegistry-createdat': '2026-09-02T00:00:00Z',
                                                          'xRegistry-modifiedat': '2026-09-02T00:00:00Z',
                                                          'Content-Length': '0'}}},
                                {'request': {'url': 'https://content.example.com/item-v2.bin',
                                             'headers': {}},
                                 'response': {'status': 200,
                                              'headers': {'Content-Type': 'application/octet-stream',
                                                          'Content-Length': '2',
                                                          'ETag': '"external-document-v2"'},
                                              'base64': base64.b64encode(_shared_bytes("v2")).decode("ascii")}}],
                  'expected': {'base64': 'AP8=',
                               'sourceXid': '/documents/main/assets/item/versions/v2',
                               'targetIsMetadata': False,
                               'forwardedCredentials': False}},
                 {'name': 'changed-default',
                  'endpoint': 'https://first.example.com/services/xreg/',
                  'exchanges': [{'request': {'url': 'https://first.example.com/services/xreg/documents/main/assets/item/meta',
                                             'headers': {}},
                                 'response': {'status': 200,
                                              'headers': {'Content-Type': 'application/json',
                                                          'ETag': '"meta-3"'},
                                              'json': {'assetid': 'item',
                                                       'self': 'https://first.example.com/services/xreg/documents/main/assets/item/meta',
                                                       'xid': '/documents/main/assets/item/meta',
                                                       'epoch': 3,
                                                       'createdat': '2026-09-01T00:00:00Z',
                                                       'modifiedat': '2026-09-03T00:00:00Z',
                                                       'readonly': False,
                                                       'defaultversionid': 'v1',
                                                       'defaultversionurl': 'https://first.example.com/services/xreg/documents/main/assets/item/versions/v1$details',
                                                       'defaultversionsticky': True}}},
                                {'request': {'url': 'https://first.example.com/services/xreg/documents/main/assets/item/versions/v1',
                                             'headers': {}},
                                 'response': {'status': 200,
                                              'headers': {'Content-Type': 'application/json',
                                                          'Content-Length': '17',
                                                          'ETag': '"document-v1"',
                                                          'xRegistry-assetid': 'item',
                                                          'xRegistry-versionid': 'v1',
                                                          'xRegistry-self': 'https://first.example.com/services/xreg/documents/main/assets/item/versions/v1',
                                                          'xRegistry-xid': '/documents/main/assets/item/versions/v1',
                                                          'xRegistry-epoch': '1',
                                                          'xRegistry-isdefault': 'true',
                                                          'xRegistry-ancestorid': 'v1',
                                                          'xRegistry-createdat': '2026-09-01T00:00:00Z',
                                                          'xRegistry-modifiedat': '2026-09-01T00:00:00Z'},
                                              'text': '{"type":"string"}'}},
                                {'request': {'url': 'https://first.example.com/services/xreg/documents/main/assets/item/meta',
                                             'headers': {'If-None-Match': '"meta-3"'}},
                                 'response': {'status': 200,
                                              'headers': {'Content-Type': 'application/json',
                                                          'ETag': '"meta-4"'},
                                              'json': {'assetid': 'item',
                                                       'self': 'https://first.example.com/services/xreg/documents/main/assets/item/meta',
                                                       'xid': '/documents/main/assets/item/meta',
                                                       'epoch': 4,
                                                       'createdat': '2026-09-01T00:00:00Z',
                                                       'modifiedat': '2026-09-04T00:00:00Z',
                                                       'readonly': False,
                                                       'defaultversionid': 'v2',
                                                       'defaultversionurl': 'https://first.example.com/services/xreg/documents/main/assets/item/versions/v2$details',
                                                       'defaultversionsticky': True}}}],
                  'expected': {'error': 'inconsistent_snapshot'}},
                 {'name': 'range-restart',
                  'note': 'Range-processing excerpt; only representation headers are retained.',
                  'endpoint': 'https://first.example.com/services/xreg/',
                  'exchanges': [{'request': {'url': 'https://first.example.com/services/xreg/documents/main/assets/item/versions/v2',
                                             'headers': {'Range': 'bytes=0-1'}},
                                 'response': {'status': 206,
                                              'headers': {'Content-Type': 'application/octet-stream',
                                                          'Content-Length': '2',
                                                          'Content-Range': 'bytes 0-1/4',
                                                          'ETag': '"old-bytes"'},
                                              'text': 'AB'}},
                                {'request': {'url': 'https://first.example.com/services/xreg/documents/main/assets/item/versions/v2',
                                             'headers': {'Range': 'bytes=2-3',
                                                         'If-Range': '"old-bytes"'}},
                                 'response': {'status': 200,
                                              'headers': {'Content-Type': 'application/octet-stream',
                                                          'Content-Length': '4',
                                                          'ETag': '"new-bytes"'},
                                              'text': 'WXYZ'}}],
                  'expected': {'text': 'WXYZ', 'discardedPartial': 'AB'}},
                  ]}
TRANSCRIPTS = {value["name"]: value for value in DATA["transcripts"]}


@pytest.mark.parametrize("case", MAPPING["cases"], ids=lambda case: case["name"])
def test_http_native_read_mappings_preserve_nonroot_base_and_view(case):
    if "error" in case:
        with pytest.raises(FederationError) as error:
            request_url(MAPPING["endpoint"], MAPPING["modelsource"], **case["request"])
        assert error.value.code == "unsupported_operation"
    else:
        url = request_url(MAPPING["endpoint"], MAPPING["modelsource"], **case["request"])
        assert url == case["url"]
        assert url.startswith("https://first.example.com/services/xreg/")


@pytest.mark.parametrize("name,code", [
    ("later-page-ambiguity", "ambiguous"),
    ("changed-default", "inconsistent_snapshot"),
])
def test_http_failed_transcripts_keep_specific_error_and_real_trace(name, code):
    case = copy.deepcopy(TRANSCRIPTS[name])
    case["expected"] = {"invented": "success"}
    trace = []
    with pytest.raises(FederationError) as error:
        interpret_transcript(case, trace=trace)
    assert error.value.code == code
    assert trace == [
        {"url": item["request"]["url"], "status": item["response"]["status"]}
        for item in case["exchanges"]
    ]


def test_http_no_filter_catalog_resolves_metadata_without_document_download():
    case = TRANSCRIPTS["no-filter-catalog"]
    result = interpret_transcript(case)
    assert result["value"]["registryid"] == "bridge"
    assert result["value"]["xregurl"] == "https://first.example.com/services/xreg/"
    assert result["pages"] == 1
    assert result["snapshot"] is None and result["immutable"] is False
    assert [item["url"] for item in result["trace"]] == [
        "https://catalog.example.com/catalog/capabilities",
        "https://catalog.example.com/catalog/categories/dev/registries",
    ]


def test_http_opaque_next_page_is_consumed_before_unique_selection():
    result = interpret_transcript(TRANSCRIPTS["filtered-pages"])
    assert result["pages"] == 2
    assert result["value"]["assetid"] == "item"
    assert result["value"]["xid"] == "/documents/main/assets/item"
    assert result["trace"][1]["url"] == TRANSCRIPTS["filtered-pages"]["exchanges"][1]["request"]["url"]


@pytest.mark.parametrize("name,data,reused", [
    ("document-revalidation", b'{"type":"string"}', True),
    ("document-redirect", b"\x00\xff", False),
    ("range-restart", b"WXYZ", False),
])
def test_http_exact_document_bytes_cache_and_range_restart(name, data, reused):
    case = copy.deepcopy(TRANSCRIPTS[name])
    case["expected"] = {"base64": "ZmFrZQ=="}
    before = copy.deepcopy(case)
    result = interpret_transcript(case)
    assert result["value"] == data
    assert result["cache_reused"] is reused
    assert case == before
    assert result["discarded_partial"] == (b"AB" if name == "range-restart" else b"")
    if name == "document-redirect":
        assert result["source_xid"] == "/documents/main/assets/item/versions/v2"
        assert result["trace"][-1]["url"] == "https://content.example.com/item-v2.bin"


@pytest.mark.parametrize("header", ["Authorization"])
def test_http_cross_origin_redirect_rejects_forwarded_scope_headers(header):
    case = copy.deepcopy(TRANSCRIPTS["document-redirect"])
    case["exchanges"][1]["request"]["headers"][header] = "source-only"
    trace = []
    with pytest.raises(FederationError) as error:
        interpret_transcript(case, trace=trace)
    assert error.value.code == "policy_denied"
    assert len(trace) == 1


@pytest.mark.parametrize("code", [
    "policy_denied",
])
def test_selected_binding_failure_never_attempts_another_advertisement(code):
    first = {"name": "http", "endpoint": "https://first.example.com", "priority": 0}
    second = {"name": "http", "endpoint": "https://second.example.com", "priority": 1}
    failure = FederationError(code, "selected operation failed")
    read = Mock(side_effect=failure)
    with pytest.raises(FederationError) as error:
        execute_selected({"federationprofiles": [first, second]}, {"http"}, read)
    assert error.value is failure
    read.assert_called_once_with(first)
