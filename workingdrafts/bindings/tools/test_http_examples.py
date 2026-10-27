"""Executable Core HTTP mapping, pagination, cache and capture examples."""

import copy
from unittest.mock import Mock

import pytest

from workingdrafts.federation.tools.federation_examples import (
    FederationError, execute_selected, select_label,
)
from workingdrafts.bindings.tools.http_examples import interpret_transcript, literal_filter, request_url


import base64
from workingdrafts.federation.tools.federation_examples import load_example, example_documents

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
 'cases': [{'name': 'registry',
            'request': {'operation': 'entity', 'target': '/'},
            'url': 'https://first.example.com/services/xreg/',
            'view': 'metadata'},
           {'name': 'groups',
            'request': {'operation': 'collection', 'target': '/documents'},
            'url': 'https://first.example.com/services/xreg/documents',
            'view': 'metadata'},
           {'name': 'group',
            'request': {'operation': 'entity', 'target': '/documents/main'},
            'url': 'https://first.example.com/services/xreg/documents/main',
            'view': 'metadata'},
           {'name': 'resources',
            'request': {'operation': 'collection', 'target': '/documents/main/assets'},
            'url': 'https://first.example.com/services/xreg/documents/main/assets',
            'view': 'metadata'},
           {'name': 'resource-metadata',
            'request': {'operation': 'entity', 'target': '/documents/main/assets/item'},
            'url': 'https://first.example.com/services/xreg/documents/main/assets/item$details',
            'view': 'metadata'},
           {'name': 'resource-meta',
            'request': {'operation': 'entity', 'target': '/documents/main/assets/item/meta'},
            'url': 'https://first.example.com/services/xreg/documents/main/assets/item/meta',
            'view': 'metadata'},
           {'name': 'versions',
            'request': {'operation': 'collection',
                        'target': '/documents/main/assets/item/versions'},
            'url': 'https://first.example.com/services/xreg/documents/main/assets/item/versions',
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
           {'name': 'metadata-only-resource',
            'request': {'operation': 'entity', 'target': '/categories/dev/registries/bridge'},
            'url': 'https://first.example.com/services/xreg/categories/dev/registries/bridge',
            'view': 'metadata'},
           {'name': 'metadata-only-version',
            'request': {'operation': 'entity',
                        'target': '/categories/dev/registries/bridge/versions/v1'},
            'url': 'https://first.example.com/services/xreg/categories/dev/registries/bridge/versions/v1',
            'view': 'metadata'},
           {'name': 'metadata-only-has-no-document',
            'request': {'operation': 'document', 'target': '/categories/dev/registries/bridge'},
            'error': 'unsupported_operation'},
           {'name': 'model',
            'request': {'operation': 'model', 'target': '/'},
            'url': 'https://first.example.com/services/xreg/model',
            'modelsourceurl': 'https://first.example.com/services/xreg/modelsource',
            'view': 'model'},
           {'name': 'capabilities',
            'request': {'operation': 'capabilities', 'target': '/'},
            'url': 'https://first.example.com/services/xreg/capabilities',
            'view': 'capabilities'}]}
# Protocol vectors retained independently of generated Registry content.
DATA = {'format': 'xregistry-http-examples-v1',
 'supportedSpecversions': ['1.0-rc4'],
 'selectors': [{'name': 'case-insensitive-value',
                'selector': {'label': 'stage', 'value': 'PRODUCTION'},
                'entities': [{'assetid': 'item', 'labels': {'stage': 'production'}},
                             {'assetid': 'other', 'labels': {'stage': 'development'}}],
                'expected': 'item',
                'filter': 'labels.stage=PRODUCTION'},
               {'name': 'empty-is-not-absent',
                'selector': {'label': 'note', 'value': ''},
                'entities': [{'assetid': 'item', 'labels': {'note': ''}}, {'assetid': 'unlabeled'}],
                'expected': 'item',
                'filter': 'labels.note='},
               {'name': 'literal-star',
                'selector': {'label': 'note', 'value': 'A*B'},
                'entities': [{'assetid': 'item', 'labels': {'note': 'a*b'}},
                             {'assetid': 'other', 'labels': {'note': 'axxb'}}],
                'expected': 'item',
                'filter': 'labels.note=A\\*B'},
               {'name': 'dot-in-label-key',
                'selector': {'label': 'release.channel', 'value': 'stable'},
                'entities': [{'assetid': 'item', 'labels': {'release.channel': 'STABLE'}},
                             {'assetid': 'other', 'labels': {'channel': 'stable'}}],
                'expected': 'item',
                'filter': "labels['release.channel']=stable"},
               {'name': 'literal-null-fallback',
                'selector': {'label': 'note', 'value': 'null'},
                'entities': [{'assetid': 'item', 'labels': {'note': 'NULL'}},
                             {'assetid': 'unlabeled'}],
                'expected': 'item',
                'filter': None},
               {'name': 'comma-fallback',
                'selector': {'label': 'note', 'value': 'a,b'},
                'entities': [{'assetid': 'item', 'labels': {'note': 'A,B'}}],
                'expected': 'item',
                'filter': None},
               {'name': 'no-unicode-normalization',
                'selector': {'label': 'note', 'value': 'é'},
                'entities': [{'assetid': 'item', 'labels': {'note': 'É'}},
                             {'assetid': 'other', 'labels': {'note': 'é'}}],
                'expected': 'item',
                'filter': None},
               {'name': 'no-match',
                'selector': {'label': 'note', 'value': ''},
                'entities': [{'assetid': 'unlabeled'}],
                'error': 'not_found',
                'filter': 'labels.note='}],
 'transcripts': [{'name': 'full-api-bootstrap',
                  'note': 'Discovery excerpt; native /model access is specified in '
                          'read-mapping.json. The compact /modelsource below is not an expanded '
                          '/model response.',
                  'endpoint': 'https://first.example.com/services/xreg/',
                  'exchanges': [{'request': {'url': 'https://first.example.com/services/xreg/',
                                             'headers': {}},
                                 'response': {'status': 200,
                                              'headers': {'Content-Type': 'application/json',
                                                          'Link': '<https://first.example.com/services/xreg/>;rel=xregistry-root',
                                                          'ETag': '"root-1"'},
                                              'json': {'specversion': '1.0-rc4',
                                                       'registryid': 'first',
                                                       'self': 'https://first.example.com/services/xreg/',
                                                       'xid': '/',
                                                       'epoch': 1,
                                                       'createdat': '2026-09-01T00:00:00Z',
                                                       'modifiedat': '2026-09-01T00:00:00Z',
                                                       'documentsurl': 'https://first.example.com/services/xreg/documents',
                                                       'documentscount': 1,
                                                       'categoriesurl': 'https://first.example.com/services/xreg/categories',
                                                       'categoriescount': 1}}},
                                {'request': {'url': 'https://first.example.com/services/xreg/capabilities',
                                             'headers': {}},
                                 'response': {'status': 200,
                                              'headers': {'Content-Type': 'application/json'},
                                              'json': {'available': {'capabilities': {'mutable': False},
                                                                     'entities': {'mutable': False},
                                                                     'model': {'mutable': False},
                                                                     'modelsource': {'mutable': False},
                                                                     'export': {'mutable': False}},
                                                       'flags': ['filter',
                                                                 'inline',
                                                                 'doc',
                                                                 'binary',
                                                                 'specversion'],
                                                       'mutable': [],
                                                       'pagination': True,
                                                       'shortself': False,
                                                       'specversions': ['1.0-rc4']}}},
                                {'request': {'url': 'https://first.example.com/services/xreg/modelsource',
                                             'headers': {}},
                                 'response': {'status': 200,
                                              'headers': {'Content-Type': 'application/json'},
                                              'json': {'groups': {'documents': {'singular': 'document',
                                                                                'resources': {'assets': {'singular': 'asset'}}},
                                                                  'categories': {'singular': 'category',
                                                                                 'resources': {'registries': {'singular': 'registry',
                                                                                                              'hasdocument': False,
                                                                                                              'attributes': {'xregurl': {'type': 'url'},
                                                                                                                             'weburl': {'type': 'url'}}}}}}}}}],
                  'expected': {'registryid': 'first',
                               'specversion': '1.0-rc4',
                               'immutable': False}},
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
                 {'name': 'zero-byte-document',
                  'endpoint': 'https://first.example.com/services/xreg/',
                  'exchanges': [{'request': {'url': 'https://first.example.com/services/xreg/documents/main/assets/item/versions/v3',
                                             'headers': {}},
                                 'response': {'status': 200,
                                              'headers': {'Content-Type': 'application/octet-stream',
                                                          'Content-Length': '0',
                                                          'ETag': '"document-v3-empty"',
                                                          'xRegistry-assetid': 'item',
                                                          'xRegistry-versionid': 'v3',
                                                          'xRegistry-self': 'https://first.example.com/services/xreg/documents/main/assets/item/versions/v3',
                                                          'xRegistry-xid': '/documents/main/assets/item/versions/v3',
                                                          'xRegistry-epoch': '1',
                                                          'xRegistry-isdefault': 'false',
                                                          'xRegistry-ancestorid': 'v2',
                                                          'xRegistry-createdat': '2026-09-03T00:00:00Z',
                                                          'xRegistry-modifiedat': '2026-09-03T00:00:00Z'},
                                              'base64': base64.b64encode(_shared_bytes("v3")).decode("ascii")}}],
                  'expected': {'base64': '', 'size': 0}},
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
                 {'name': 'redirect-policy-denial',
                  'note': 'Redirect-policy excerpt; only representation and destination headers '
                          'are retained.',
                  'endpoint': 'https://first.example.com/services/xreg/',
                  'policy': {'allowedOrigins': ['https://first.example.com']},
                  'exchanges': [{'request': {'url': 'https://first.example.com/services/xreg/documents/main/assets/item/versions/v2',
                                             'headers': {}},
                                 'response': {'status': 303,
                                              'headers': {'Location': 'http://restricted.example.com/item.bin',
                                                          'xRegistry-asseturl': 'http://restricted.example.com/item.bin',
                                                          'Content-Length': '0'}}}],
                  'expected': {'error': 'policy_denied', 'fallbackAttempts': 0}},
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
                 {'name': 'incompatible-target',
                  'endpoint': 'https://older.example.com/xreg',
                  'exchanges': [{'request': {'url': 'https://older.example.com/xreg',
                                             'headers': {}},
                                 'response': {'status': 200,
                                              'headers': {'Content-Type': 'application/json'},
                                              'json': {'specversion': '1.0-rc2',
                                                       'registryid': 'older',
                                                       'self': 'https://older.example.com/xreg',
                                                       'xid': '/',
                                                       'epoch': 1,
                                                       'createdat': '2026-09-01T00:00:00Z',
                                                       'modifiedat': '2026-09-01T00:00:00Z',
                                                       'documentsurl': 'https://older.example.com/xreg/documents',
                                                       'documentscount': 1}}}],
                  'expected': {'error': 'unsupported_version', 'subsequentEntityReads': 0}},
                 {'name': 'incomplete-page',
                  'endpoint': 'https://first.example.com/services/xreg/',
                  'selector': {'label': 'stage', 'value': 'PRODUCTION'},
                  'exchanges': [{'request': {'url': 'https://first.example.com/services/xreg/documents/main/assets',
                                             'headers': {}},
                                 'response': {'status': 200,
                                              'headers': {'Content-Type': 'application/json',
                                                          'Link': '<?cursor=remaining>;rel=next;count=1'},
                                              'json': {}}},
                                {'request': {'url': 'https://first.example.com/services/xreg/documents/main/assets?cursor=remaining',
                                             'headers': {}},
                                 'response': {'status': 503, 'headers': {'Retry-After': '30'}}}],
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
                 {'name': 'authorization-stops-resolution',
                  'endpoint': 'https://first.example.com/services/xreg/',
                  'exchanges': [{'request': {'url': 'https://first.example.com/services/xreg/documents/main/assets',
                                             'headers': {}},
                                 'response': {'status': 403, 'headers': {}}}],
                  'expected': {'error': 'policy_denied', 'fallbackAttempts': 0}}]}
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


@pytest.mark.parametrize("case", DATA["selectors"], ids=lambda case: case["name"])
def test_http_literal_filters_and_local_comparison(case):
    assert literal_filter(case["selector"]) == case["filter"]
    if "error" in case:
        with pytest.raises(FederationError) as error:
            select_label(case["entities"], case["selector"]["label"], case["selector"]["value"])
        assert error.value.code == "not_found"
    else:
        result = select_label(case["entities"], case["selector"]["label"], case["selector"]["value"])
        assert result["assetid"] == "item"


@pytest.mark.parametrize("name,code", [
    ("later-page-ambiguity", "ambiguous"),
    ("redirect-policy-denial", "policy_denied"),
    ("changed-default", "inconsistent_snapshot"),
    ("incompatible-target", "unsupported_version"),
    ("incomplete-page", "inconsistent_snapshot"),
    ("authorization-stops-resolution", "policy_denied"),
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


def test_http_bootstrap_keeps_identity_and_live_snapshot_separate():
    result = interpret_transcript(TRANSCRIPTS["full-api-bootstrap"])
    assert result["registry"]["registryid"] == "first"
    assert result["registry"]["specversion"] == "1.0-rc4"
    assert result["snapshot"] is None
    assert result["immutable"] is False
    assert len(result["trace"]) == 3


def test_http_opaque_next_page_is_consumed_before_unique_selection():
    result = interpret_transcript(TRANSCRIPTS["filtered-pages"])
    assert result["pages"] == 2
    assert result["value"]["assetid"] == "item"
    assert result["value"]["xid"] == "/documents/main/assets/item"
    assert result["trace"][1]["url"] == TRANSCRIPTS["filtered-pages"]["exchanges"][1]["request"]["url"]


@pytest.mark.parametrize("name,data,reused", [
    ("document-revalidation", b'{"type":"string"}', True),
    ("zero-byte-document", b"", False),
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


@pytest.mark.parametrize("header", ["Authorization", "Cookie", "If-None-Match", "If-Range"])
def test_http_cross_origin_redirect_rejects_forwarded_scope_headers(header):
    case = copy.deepcopy(TRANSCRIPTS["document-redirect"])
    case["exchanges"][1]["request"]["headers"][header] = "source-only"
    trace = []
    with pytest.raises(FederationError) as error:
        interpret_transcript(case, trace=trace)
    assert error.value.code == "policy_denied"
    assert len(trace) == 1


@pytest.mark.parametrize("change,code", [
    ("next-url", "inconsistent_snapshot"), ("count", "inconsistent_snapshot"),
    ("missing-page", "inconsistent_snapshot"), ("member-xid", "invalid_package"),
])
def test_http_incomplete_or_changed_collection_cannot_look_unique(change, code):
    case = copy.deepcopy(TRANSCRIPTS["filtered-pages"])
    if change == "next-url":
        case["exchanges"][1]["request"]["url"] += "&invented=1"
    elif change == "missing-page":
        case["exchanges"].pop()
    elif change == "count":
        case["exchanges"][1]["response"]["headers"]["Link"] = "<.?end>;rel=prev;count=99"
    else:
        for exchange in case["exchanges"]:
            for entity in exchange["response"].get("json", {}).values():
                entity["xid"] = "/documents/other/assets/item"
    with pytest.raises(FederationError) as error:
        interpret_transcript(case)
    assert error.value.code == code


@pytest.mark.parametrize("budget,ok", [(16, False), (17, True), (18, True)])
def test_http_exact_byte_budget_boundary(budget, ok):
    case = copy.deepcopy(TRANSCRIPTS["document-revalidation"])
    case["exchanges"] = case["exchanges"][:1]
    if ok:
        assert interpret_transcript(case, max_bytes=budget)["value"] == b'{"type":"string"}'
    else:
        with pytest.raises(FederationError) as error:
            interpret_transcript(case, max_bytes=budget)
        assert error.value.code == "limit_exceeded"


def test_http_request_budget_never_returns_first_page_as_unique():
    with pytest.raises(FederationError) as error:
        interpret_transcript(TRANSCRIPTS["filtered-pages"], max_requests=1)
    assert error.value.code == "limit_exceeded"


@pytest.mark.parametrize("change", ["no-cache", "wrong-tag", "wrong-scope", "vary-star", "body"])
def test_http_304_needs_matching_cached_representation(change):
    case = copy.deepcopy(TRANSCRIPTS["document-revalidation"])
    if change == "no-cache":
        case["exchanges"].pop(0)
    elif change == "wrong-tag":
        case["exchanges"][1]["request"]["headers"]["If-None-Match"] = '"different"'
    elif change == "wrong-scope":
        case["exchanges"][1]["request"]["headers"]["Authorization"] = "different-scope"
    elif change == "vary-star":
        case["exchanges"][0]["response"]["headers"]["Vary"] = "*"
    else:
        case["exchanges"][1]["response"]["text"] = "replacement"
    with pytest.raises(FederationError) as error:
        interpret_transcript(case)
    assert error.value.code == ("invalid_package" if change == "body" else "inconsistent_snapshot")


def test_http_weak_etag_revalidation_and_quoted_comma_are_opaque():
    case = copy.deepcopy(TRANSCRIPTS["document-revalidation"])
    for exchange in case["exchanges"]:
        exchange["response"]["headers"]["ETag"] = 'W/"tag,one"'
    case["exchanges"][1]["request"]["headers"]["If-None-Match"] = '"another", "tag,one"'
    result = interpret_transcript(case)
    assert result["value"] == b'{"type":"string"}'
    assert result["cache_reused"] is True


@pytest.mark.parametrize("change,code", [
    ("truncate", "integrity_error"), ("weak-if-range", "invalid_package"),
    ("missing-range", "inconsistent_snapshot"), ("range-gap", "inconsistent_snapshot"),
])
def test_http_partial_or_corrupt_content_is_not_a_complete_document(change, code):
    case = copy.deepcopy(TRANSCRIPTS["range-restart"])
    if change == "truncate":
        case["exchanges"][1]["response"]["headers"]["Content-Length"] = "9"
    elif change == "weak-if-range":
        case["exchanges"][1]["request"]["headers"]["If-Range"] = 'W/"old-bytes"'
    elif change == "missing-range":
        case["exchanges"].pop()
    else:
        case["exchanges"][0]["response"]["headers"]["Content-Range"] = "bytes 1-2/4"
    with pytest.raises(FederationError) as error:
        interpret_transcript(case)
    assert error.value.code == code


@pytest.mark.parametrize("code", [
    "policy_denied", "integrity_error", "unsupported_version", "ambiguous", "inconsistent_snapshot",
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
