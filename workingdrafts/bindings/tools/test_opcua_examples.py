"""Offline UA identity, namespace, Browse and FileTransfer conformance."""

import base64
import copy
from unittest.mock import patch

import pytest

from workingdrafts.bindings.tools import opcua_examples as ua
from workingdrafts.federation.tools.federation_examples import FederationError


from workingdrafts.federation.tools.federation_examples import load_example, example_documents

# Only captured Registry content is shared. Wire protocol and expected results
# stay literal, including transient failures, partial reads and cache headers.
_FIRST = load_example("first")
_DOCUMENTS = example_documents(_FIRST)


def _shared_bytes(version):
    return _DOCUMENTS["/documents/main/assets/item/versions/" + version]


# Protocol vectors retained independently of generated Registry content.
REFERENCES = {'format': 'xregistry-opcua-examples-v1',
 'cases': [{'name': 'advertised-root',
            'kind': 'root',
            'input': {'profile': {'name': 'opcua',
                                  'endpoint': 'opc.tcp://ua.example.com:4840',
                                  'parameters': {'registryroot': 'nsu=urn:example:registry;s=FirstRegistry',
                                                 'applicationuri': 'urn:example:ua:first',
                                                 'transportprofileuri': 'http://opcfoundation.org/UA-Profile/Transport/uatcp-uasc-uabinary'}},
                      'endpoint_description': {'endpointUrl': 'opc.tcp://ua.example.com:4840',
                                               'server': {'applicationUri': 'urn:example:ua:first'},
                                               'transportProfileUri': 'http://opcfoundation.org/UA-Profile/Transport/uatcp-uasc-uabinary'},
                      'namespace_array': ['http://opcfoundation.org/UA/',
                                          'urn:example:companion',
                                          'urn:example:other',
                                          'urn:example:registry']},
            'expected': {'endpoint': 'opc.tcp://ua.example.com:4840',
                         'applicationuri': 'urn:example:ua:first',
                         'transportprofileuri': 'http://opcfoundation.org/UA-Profile/Transport/uatcp-uasc-uabinary',
                         'registryroot': 'nsu=urn:example:registry;s=FirstRegistry',
                         'nodeId': 'ns=3;s=FirstRegistry'}},
           {'name': 'another-root-at-same-endpoint',
            'kind': 'root',
            'input': {'profile': {'name': 'opcua',
                                  'endpoint': 'opc.tcp://ua.example.com:4840',
                                  'parameters': {'registryroot': 'nsu=urn:example:registry;s=SecondRegistry'}},
                      'endpoint_description': {'endpointUrl': 'opc.tcp://ua.example.com:4840',
                                               'server': {'applicationUri': 'urn:example:ua:first'},
                                               'transportProfileUri': 'http://opcfoundation.org/UA-Profile/Transport/uatcp-uasc-uabinary'},
                      'namespace_array': ['http://opcfoundation.org/UA/', 'urn:example:registry']},
            'expected': {'endpoint': 'opc.tcp://ua.example.com:4840',
                         'applicationuri': 'urn:example:ua:first',
                         'transportprofileuri': 'http://opcfoundation.org/UA-Profile/Transport/uatcp-uasc-uabinary',
                         'registryroot': 'nsu=urn:example:registry;s=SecondRegistry',
                         'nodeId': 'ns=1;s=SecondRegistry'}},
           {'name': 'remote-source-tables-to-target-seven',
            'kind': 'reference',
            'input': {'reference': {'serverIndex': 2,
                                    'namespaceIndex': 3,
                                    'identifierType': 'String',
                                    'identifier': 'ItemV1'},
                      'source_server_array': ['urn:example:ua:first',
                                              'urn:example:ua:unrelated',
                                              'urn:example:ua:remote'],
                      'source_namespace_array': ['http://opcfoundation.org/UA/',
                                                 'urn:example:source',
                                                 'urn:example:unused',
                                                 'urn:example:registry'],
                      'target_applicationuri': 'urn:example:ua:remote',
                      'target_namespace_array': ['http://opcfoundation.org/UA/',
                                                 'urn:example:other1',
                                                 'urn:example:other2',
                                                 'urn:example:other3',
                                                 'urn:example:other4',
                                                 'urn:example:other5',
                                                 'urn:example:other6',
                                                 'urn:example:registry']},
            'expected': {'applicationuri': 'urn:example:ua:remote',
                         'namespaceUri': 'urn:example:registry',
                         'nodeId': 'ns=7;s=ItemV1',
                         'portable': 'svu=urn:example:ua:remote;nsu=urn:example:registry;s=ItemV1',
                         'local': False}},
           {'name': 'reindexed-source-and-target',
            'kind': 'reference',
            'input': {'reference': {'serverIndex': 1,
                                    'namespaceIndex': 2,
                                    'identifierType': 'String',
                                    'identifier': 'ItemV1'},
                      'source_server_array': ['urn:example:ua:first',
                                              'urn:example:ua:remote',
                                              'urn:example:ua:unrelated'],
                      'source_namespace_array': ['http://opcfoundation.org/UA/',
                                                 'urn:example:unused',
                                                 'urn:example:registry',
                                                 'urn:example:source'],
                      'target_applicationuri': 'urn:example:ua:remote',
                      'target_namespace_array': ['http://opcfoundation.org/UA/',
                                                 'urn:example:other',
                                                 'urn:example:registry']},
            'expected': {'applicationuri': 'urn:example:ua:remote',
                         'namespaceUri': 'urn:example:registry',
                         'nodeId': 'ns=2;s=ItemV1',
                         'portable': 'svu=urn:example:ua:remote;nsu=urn:example:registry;s=ItemV1',
                         'local': False}},
           {'name': 'explicit-namespace-needs-no-source-namespace-table',
            'kind': 'reference',
            'input': {'reference': {'serverIndex': 1,
                                    'namespaceUri': 'urn:example:registry',
                                    'namespaceIndex': 0,
                                    'identifierType': 'String',
                                    'identifier': 'ItemV1'},
                      'source_server_array': ['urn:example:ua:first', 'urn:example:ua:remote'],
                      'source_namespace_array': None,
                      'target_applicationuri': 'urn:example:ua:remote',
                      'target_namespace_array': ['http://opcfoundation.org/UA/',
                                                 'urn:example:registry']},
            'expected': {'applicationuri': 'urn:example:ua:remote',
                         'namespaceUri': 'urn:example:registry',
                         'nodeId': 'ns=1;s=ItemV1',
                         'portable': 'svu=urn:example:ua:remote;nsu=urn:example:registry;s=ItemV1',
                         'local': False}},
           {'name': 'server-zero-is-source',
            'kind': 'reference',
            'input': {'reference': {'serverIndex': 0,
                                    'namespaceIndex': 1,
                                    'identifierType': 'String',
                                    'identifier': 'FirstRegistry'},
                      'source_server_array': ['urn:example:ua:first', 'urn:example:ua:remote'],
                      'source_namespace_array': ['http://opcfoundation.org/UA/',
                                                 'urn:example:registry'],
                      'target_applicationuri': 'urn:example:ua:first',
                      'target_namespace_array': ['http://opcfoundation.org/UA/',
                                                 'urn:example:registry']},
            'expected': {'applicationuri': 'urn:example:ua:first',
                         'namespaceUri': 'urn:example:registry',
                         'nodeId': 'ns=1;s=FirstRegistry',
                         'portable': 'svu=urn:example:ua:first;nsu=urn:example:registry;s=FirstRegistry',
                         'local': True}},
           {'name': 'standard-namespace-numeric',
            'kind': 'reference',
            'input': {'reference': {'serverIndex': 0,
                                    'namespaceIndex': 0,
                                    'identifierType': 'Numeric',
                                    'identifier': 2255},
                      'source_server_array': ['urn:example:ua:first'],
                      'source_namespace_array': ['http://opcfoundation.org/UA/'],
                      'target_applicationuri': 'urn:example:ua:first',
                      'target_namespace_array': ['http://opcfoundation.org/UA/']},
            'expected': {'applicationuri': 'urn:example:ua:first',
                         'namespaceUri': 'http://opcfoundation.org/UA/',
                         'nodeId': 'i=2255',
                         'portable': 'svu=urn:example:ua:first;i=2255',
                         'local': True}},
           {'name': 'guid-identifier',
            'kind': 'reference',
            'input': {'reference': {'serverIndex': 0,
                                    'namespaceIndex': 1,
                                    'identifierType': 'Guid',
                                    'identifier': '09087E75-8E5E-499B-954F-F2A9603DB28A'},
                      'source_server_array': ['urn:example:ua:first'],
                      'source_namespace_array': ['http://opcfoundation.org/UA/',
                                                 'urn:example:registry'],
                      'target_applicationuri': 'urn:example:ua:first',
                      'target_namespace_array': ['http://opcfoundation.org/UA/',
                                                 'urn:example:registry']},
            'expected': {'applicationuri': 'urn:example:ua:first',
                         'namespaceUri': 'urn:example:registry',
                         'nodeId': 'ns=1;g=09087e75-8e5e-499b-954f-f2a9603db28a',
                         'portable': 'svu=urn:example:ua:first;nsu=urn:example:registry;g=09087e75-8e5e-499b-954f-f2a9603db28a',
                         'local': True}},
           {'name': 'opaque-identifier',
            'kind': 'reference',
            'input': {'reference': {'serverIndex': 0,
                                    'namespaceIndex': 1,
                                    'identifierType': 'Opaque',
                                    'identifier': 'AP8='},
                      'source_server_array': ['urn:example:ua:first'],
                      'source_namespace_array': ['http://opcfoundation.org/UA/',
                                                 'urn:example:registry'],
                      'target_applicationuri': 'urn:example:ua:first',
                      'target_namespace_array': ['http://opcfoundation.org/UA/',
                                                 'urn:example:registry']},
            'expected': {'applicationuri': 'urn:example:ua:first',
                         'namespaceUri': 'urn:example:registry',
                         'nodeId': 'ns=1;b=AP8=',
                         'portable': 'svu=urn:example:ua:first;nsu=urn:example:registry;b=AP8=',
                         'local': True}},
           {'name': 'semicolon-escaping-and-opaque-string-identity',
            'kind': 'reference',
            'input': {'reference': {'serverIndex': 0,
                                    'namespaceIndex': 0,
                                    'namespaceUri': 'urn:example:model;revision=1',
                                    'identifierType': 'String',
                                    'identifier': 'A;ns=9;B'},
                      'source_server_array': ['urn:example:ua:first'],
                      'source_namespace_array': None,
                      'target_applicationuri': 'urn:example:ua:first',
                      'target_namespace_array': ['http://opcfoundation.org/UA/',
                                                 'urn:example:model;revision=1']},
            'expected': {'applicationuri': 'urn:example:ua:first',
                         'namespaceUri': 'urn:example:model;revision=1',
                         'nodeId': 'ns=1;s=A;ns=9;B',
                         'portable': 'svu=urn:example:ua:first;nsu=urn:example:model%3Brevision=1;s=A;ns=9;B',
                         'local': True}},
           {'name': 'source-server-index-out-of-range',
            'kind': 'reference',
            'input': {'reference': {'serverIndex': 2,
                                    'namespaceIndex': 0,
                                    'identifierType': 'Numeric',
                                    'identifier': 1},
                      'source_server_array': ['urn:example:ua:first'],
                      'source_namespace_array': ['http://opcfoundation.org/UA/'],
                      'target_applicationuri': 'urn:example:ua:first',
                      'target_namespace_array': ['http://opcfoundation.org/UA/']},
            'error': 'invalid_package'},
           {'name': 'target-namespace-missing',
            'kind': 'reference',
            'input': {'reference': {'serverIndex': 0,
                                    'namespaceIndex': 1,
                                    'identifierType': 'String',
                                    'identifier': 'ItemV1'},
                      'source_server_array': ['urn:example:ua:first'],
                      'source_namespace_array': ['http://opcfoundation.org/UA/',
                                                 'urn:example:registry'],
                      'target_applicationuri': 'urn:example:ua:first',
                      'target_namespace_array': ['http://opcfoundation.org/UA/']},
            'error': 'not_found'},
           {'name': 'application-is-not-endpoint',
            'kind': 'reference',
            'input': {'reference': {'serverIndex': 1,
                                    'namespaceIndex': 0,
                                    'identifierType': 'Numeric',
                                    'identifier': 1},
                      'source_server_array': ['urn:example:ua:first', 'urn:example:ua:remote'],
                      'source_namespace_array': ['http://opcfoundation.org/UA/'],
                      'target_applicationuri': 'opc.tcp://remote.example.com:4840',
                      'target_namespace_array': ['http://opcfoundation.org/UA/']},
            'error': 'integrity_error'},
           {'name': 'fictional-serveruri-member-rejected',
            'kind': 'reference',
            'input': {'reference': {'serverIndex': 1,
                                    'namespaceIndex': 0,
                                    'ServerUri': 'opc.tcp://remote.example.com:4840',
                                    'identifierType': 'Numeric',
                                    'identifier': 1},
                      'source_server_array': ['urn:example:ua:first', 'urn:example:ua:remote'],
                      'source_namespace_array': ['http://opcfoundation.org/UA/'],
                      'target_applicationuri': 'urn:example:ua:remote',
                      'target_namespace_array': ['http://opcfoundation.org/UA/']},
            'error': 'invalid_package'},
           {'name': 'explicit-namespace-requires-zero-index',
            'kind': 'reference',
            'input': {'reference': {'serverIndex': 0,
                                    'namespaceIndex': 1,
                                    'namespaceUri': 'urn:example:registry',
                                    'identifierType': 'String',
                                    'identifier': 'ItemV1'},
                      'source_server_array': ['urn:example:ua:first'],
                      'source_namespace_array': ['http://opcfoundation.org/UA/'],
                      'target_applicationuri': 'urn:example:ua:first',
                      'target_namespace_array': ['http://opcfoundation.org/UA/',
                                                 'urn:example:registry']},
            'error': 'invalid_package'},
           {'name': 'nonportable-advertised-root',
            'kind': 'root',
            'input': {'profile': {'name': 'opcua',
                                  'endpoint': 'opc.tcp://ua.example.com:4840',
                                  'parameters': {'registryroot': 'ns=3;s=FirstRegistry'}},
                      'endpoint_description': {'endpointUrl': 'opc.tcp://ua.example.com:4840',
                                               'server': {'applicationUri': 'urn:example:ua:first'},
                                               'transportProfileUri': 'http://opcfoundation.org/UA-Profile/Transport/uatcp-uasc-uabinary'},
                      'namespace_array': ['http://opcfoundation.org/UA/', 'urn:example:registry']},
            'error': 'invalid_package'},
           {'name': 'unknown-selected-parameter',
            'kind': 'root',
            'input': {'profile': {'name': 'opcua',
                                  'endpoint': 'opc.tcp://ua.example.com:4840',
                                  'parameters': {'registryroot': 'nsu=urn:example:registry;s=FirstRegistry',
                                                 'browsepath': '/Objects/FirstRegistry'}},
                      'endpoint_description': {'endpointUrl': 'opc.tcp://ua.example.com:4840',
                                               'server': {'applicationUri': 'urn:example:ua:first'},
                                               'transportProfileUri': 'http://opcfoundation.org/UA-Profile/Transport/uatcp-uasc-uabinary'},
                      'namespace_array': ['http://opcfoundation.org/UA/', 'urn:example:registry']},
            'error': 'unsupported_operation'},
           {'name': 'root-application-mismatch',
            'kind': 'root',
            'input': {'profile': {'name': 'opcua',
                                  'endpoint': 'opc.tcp://ua.example.com:4840',
                                  'parameters': {'registryroot': 'nsu=urn:example:registry;s=FirstRegistry',
                                                 'applicationuri': 'urn:example:ua:expected'}},
                      'endpoint_description': {'endpointUrl': 'opc.tcp://ua.example.com:4840',
                                               'server': {'applicationUri': 'urn:example:ua:first'},
                                               'transportProfileUri': 'http://opcfoundation.org/UA-Profile/Transport/uatcp-uasc-uabinary'},
                      'namespace_array': ['http://opcfoundation.org/UA/', 'urn:example:registry']},
            'error': 'integrity_error'},
           {'name': 'root-transport-mismatch',
            'kind': 'root',
            'input': {'profile': {'name': 'opcua',
                                  'endpoint': 'opc.tcp://ua.example.com:4840',
                                  'parameters': {'registryroot': 'nsu=urn:example:registry;s=FirstRegistry',
                                                 'transportprofileuri': 'urn:example:unsupported-transport'}},
                      'endpoint_description': {'endpointUrl': 'opc.tcp://ua.example.com:4840',
                                               'server': {'applicationUri': 'urn:example:ua:first'},
                                               'transportProfileUri': 'http://opcfoundation.org/UA-Profile/Transport/uatcp-uasc-uabinary'},
                      'namespace_array': ['http://opcfoundation.org/UA/', 'urn:example:registry']},
            'error': 'unsupported_binding'}]}
# Protocol vectors retained independently of generated Registry content.
SEQUENCES = {'format': 'xregistry-opcua-examples-v1',
 'cases': [{'name': 'registry-metadata',
            'kind': 'sequence',
            'input': {'sequence': {'kind': 'metadata',
                                   'specversion': '1.0-rc4',
                                   'request': {'operation': 'entity', 'target': '/'},
                                   'events': [{'service': 'Read',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=FirstRegistry',
                                               'status': 'Good',
                                               'values': {'RegistryId': {'status': 'Good',
                                                                         'value': 'first'},
                                                          'SpecVersion': {'status': 'Good',
                                                                          'value': '1.0-rc4'},
                                                          'Xid': {'status': 'Good',
                                                                  'value': '/'}}}]}},
            'expected': {'values': {'RegistryId': 'first', 'SpecVersion': '1.0-rc4', 'Xid': '/'},
                         'trace': ['Read'],
                         'consistency': 'unverified'}},
           {'name': 'metadata-only-catalog',
            'kind': 'sequence',
            'note': 'xregurl and federationprofiles are typed, implementation-mapped Version '
                    'extensions, not base companion Properties or Labels strings.',
            'input': {'sequence': {'kind': 'metadata',
                                   'hasdocument': False,
                                   'specversion': '1.0-rc4',
                                   'request': {'operation': 'entity',
                                               'target': '/categories/dev/registries/bridge'},
                                   'events': [{'service': 'Read',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=CatalogBridge',
                                               'status': 'Good',
                                               'values': {'ResourceId': {'status': 'Good',
                                                                         'value': 'bridge'},
                                                          'VersionId': {'status': 'Good',
                                                                        'value': 'v1'},
                                                          'Xid': {'status': 'Good',
                                                                  'value': '/categories/dev/registries/bridge'},
                                                          'xregurl': {'status': 'Good',
                                                                      'value': 'https://first.example.com/services/xreg/'},
                                                          'federationprofiles': {'status': 'Good',
                                                                                 'value': [{'name': 'opcua',
                                                                                            'endpoint': 'opc.tcp://ua.example.com:4840',
                                                                                            'parameters': {'registryroot': 'nsu=urn:example:registry;s=FirstRegistry',
                                                                                                           'applicationuri': 'urn:example:ua:first'}}]}}}]}},
            'expected': {'values': {'ResourceId': 'bridge',
                                    'VersionId': 'v1',
                                    'Xid': '/categories/dev/registries/bridge',
                                    'xregurl': 'https://first.example.com/services/xreg/',
                                    'federationprofiles': [{'name': 'opcua',
                                                            'endpoint': 'opc.tcp://ua.example.com:4840',
                                                            'parameters': {'registryroot': 'nsu=urn:example:registry;s=FirstRegistry',
                                                                           'applicationuri': 'urn:example:ua:first'}}]},
                         'trace': ['Read'],
                         'consistency': 'unverified'}},
           {'name': 'default-v1-short-chunks',
            'kind': 'sequence',
            'input': {'sequence': {'kind': 'file',
                                   'specversion': '1.0-rc4',
                                   'request': {'operation': 'document',
                                               'target': '/documents/main/assets/item'},
                                   'selectedXid': '/documents/main/assets/item/versions/v1',
                                   'namespaceArray': ['http://opcfoundation.org/UA/',
                                                      'urn:example:other',
                                                      'urn:example:companion',
                                                      'urn:example:registry'],
                                   'expectedSize': 17,
                                   'before': {'defaultversionid': 'v1',
                                              'versionid': 'v1',
                                              'epoch': 1,
                                              'size': 17},
                                   'after': {'defaultversionid': 'v1',
                                             'versionid': 'v1',
                                             'epoch': 1,
                                             'size': 17},
                                   'events': [{'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'ns=3;s=ItemV1',
                                               'method': 'Open',
                                               'input': {'mode': 1},
                                               'status': 'Good',
                                               'output': {'fileHandle': 41}},
                                              {'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'ns=3;s=ItemV1',
                                               'method': 'Read',
                                               'input': {'fileHandle': 41, 'length': 64},
                                               'status': 'Good',
                                               'output': {'data': base64.b64encode(_shared_bytes("v1")[0:8]).decode("ascii")}},
                                              {'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'ns=3;s=ItemV1',
                                               'method': 'Read',
                                               'input': {'fileHandle': 41, 'length': 64},
                                               'status': 'Good',
                                               'output': {'data': base64.b64encode(_shared_bytes("v1")[8:17]).decode("ascii")}},
                                              {'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'ns=3;s=ItemV1',
                                               'method': 'Read',
                                               'input': {'fileHandle': 41, 'length': 64},
                                               'status': 'Good',
                                               'output': {'data': base64.b64encode(_shared_bytes("v1")[17:17]).decode("ascii")}},
                                              {'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'ns=3;s=ItemV1',
                                               'method': 'Close',
                                               'input': {'fileHandle': 41},
                                               'status': 'Good'}]}},
            'expected': {'data': 'eyJ0eXBlIjoic3RyaW5nIn0=',
                         'size': 17,
                         'complete': True,
                         'trace': ['Open', 'Read', 'Read', 'Read', 'Close'],
                         'consistency': 'observed',
                         'selectedXid': '/documents/main/assets/item/versions/v1'}},
           {'name': 'explicit-v2-binary',
            'kind': 'sequence',
            'input': {'sequence': {'kind': 'file',
                                   'request': {'operation': 'document',
                                               'target': '/documents/main/assets/item/versions/v2'},
                                   'selectedXid': '/documents/main/assets/item/versions/v2',
                                   'expectedSize': 2,
                                   'before': {'versionid': 'v2', 'epoch': 1, 'size': 2},
                                   'after': {'versionid': 'v2', 'epoch': 1, 'size': 2},
                                   'events': [{'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=ItemV2',
                                               'method': 'Open',
                                               'input': {'mode': 1},
                                               'status': 'Good',
                                               'output': {'fileHandle': 42}},
                                              {'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=ItemV2',
                                               'method': 'Read',
                                               'input': {'fileHandle': 42, 'length': 2},
                                               'status': 'Good',
                                               'output': {'data': base64.b64encode(_shared_bytes("v2")[0:2]).decode("ascii")}},
                                              {'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=ItemV2',
                                               'method': 'Read',
                                               'input': {'fileHandle': 42, 'length': 2},
                                               'status': 'Good',
                                               'output': {'data': base64.b64encode(_shared_bytes("v2")[2:2]).decode("ascii")}},
                                              {'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=ItemV2',
                                               'method': 'Close',
                                               'input': {'fileHandle': 42},
                                               'status': 'Good'}]}},
            'expected': {'data': 'AP8=',
                         'size': 2,
                         'complete': True,
                         'trace': ['Open', 'Read', 'Read', 'Close'],
                         'consistency': 'observed',
                         'selectedXid': '/documents/main/assets/item/versions/v2'}},
           {'name': 'zero-byte-v3',
            'kind': 'sequence',
            'input': {'sequence': {'kind': 'file',
                                   'request': {'operation': 'document',
                                               'target': '/documents/main/assets/item/versions/v3'},
                                   'selectedXid': '/documents/main/assets/item/versions/v3',
                                   'expectedSize': 0,
                                   'before': {'versionid': 'v3', 'epoch': 1, 'size': 0},
                                   'after': {'versionid': 'v3', 'epoch': 1, 'size': 0},
                                   'events': [{'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=ItemV3',
                                               'method': 'Open',
                                               'input': {'mode': 1},
                                               'status': 'Good',
                                               'output': {'fileHandle': 43}},
                                              {'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=ItemV3',
                                               'method': 'Read',
                                               'input': {'fileHandle': 43, 'length': 64},
                                               'status': 'Good',
                                               'output': {'data': base64.b64encode(_shared_bytes("v3")[0:0]).decode("ascii")}},
                                              {'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=ItemV3',
                                               'method': 'Close',
                                               'input': {'fileHandle': 43},
                                               'status': 'Good'}]}},
            'expected': {'data': '',
                         'size': 0,
                         'complete': True,
                         'trace': ['Open', 'Read', 'Close'],
                         'consistency': 'observed',
                         'selectedXid': '/documents/main/assets/item/versions/v3'}},
           {'name': 'metadata-only-document-rejected-before-open',
            'kind': 'sequence',
            'input': {'sequence': {'kind': 'file',
                                   'hasdocument': False,
                                   'request': {'operation': 'document',
                                               'target': '/categories/dev/registries/bridge'},
                                   'events': []}},
            'error': 'unsupported_operation'},
           {'name': 'capabilities-file-with-unknown-size',
            'kind': 'sequence',
            'note': 'Size was unavailable with Bad_NotSupported; no zero-size observation is '
                    'invented.',
            'input': {'sequence': {'kind': 'file',
                                   'request': {'operation': 'capabilities', 'target': '/'},
                                   'events': [{'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=Capabilities',
                                               'method': 'Open',
                                               'input': {'mode': 1},
                                               'status': 'Good',
                                               'output': {'fileHandle': 44}},
                                              {'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=Capabilities',
                                               'method': 'Read',
                                               'input': {'fileHandle': 44, 'length': 64},
                                               'status': 'Good',
                                               'output': {'data': 'eyJmbGFncyI6W119'}},
                                              {'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=Capabilities',
                                               'method': 'Read',
                                               'input': {'fileHandle': 44, 'length': 64},
                                               'status': 'Good',
                                               'output': {'data': ''}},
                                              {'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=Capabilities',
                                               'method': 'Close',
                                               'input': {'fileHandle': 44},
                                               'status': 'Good'}]}},
            'expected': {'data': 'eyJmbGFncyI6W119',
                         'size': 12,
                         'complete': True,
                         'trace': ['Open', 'Read', 'Read', 'Close'],
                         'consistency': 'unverified'}},
           {'name': 'three-browse-pages-with-reused-continuation-token',
            'kind': 'sequence',
            'input': {'sequence': {'kind': 'browse',
                                   'request': {'operation': 'collection',
                                               'target': '/documents/main/assets/item/versions'},
                                   'namespaceArray': ['http://opcfoundation.org/UA/',
                                                      'urn:example:registry'],
                                   'events': [{'service': 'Browse',
                                               'session': 'session-1',
                                               'nodeId': 'ns=1;s=MainGroup',
                                               'input': {'requestedMaxReferencesPerNode': 1},
                                               'status': 'Good',
                                               'output': {'references': [{'nodeId': {'serverIndex': 0,
                                                                                     'namespaceIndex': 1,
                                                                                     'identifierType': 'String',
                                                                                     'identifier': 'ItemV1'},
                                                                          'browseName': {'namespaceIndex': 1,
                                                                                         'name': 'v1'}}],
                                                          'continuationPoint': 'cDE='}},
                                              {'service': 'BrowseNext',
                                               'session': 'session-1',
                                               'nodeId': 'ns=1;s=MainGroup',
                                               'input': {'continuationPoints': ['cDE='],
                                                         'releaseContinuationPoints': False},
                                               'status': 'Good',
                                               'output': {'references': [{'nodeId': {'serverIndex': 0,
                                                                                     'namespaceIndex': 1,
                                                                                     'identifierType': 'String',
                                                                                     'identifier': 'ItemV2'},
                                                                          'browseName': {'namespaceIndex': 1,
                                                                                         'name': 'v2'}}],
                                                          'continuationPoint': 'cDE='}},
                                              {'service': 'BrowseNext',
                                               'session': 'session-1',
                                               'nodeId': 'ns=1;s=MainGroup',
                                               'input': {'continuationPoints': ['cDE='],
                                                         'releaseContinuationPoints': False},
                                               'status': 'Good',
                                               'output': {'references': [{'nodeId': {'serverIndex': 0,
                                                                                     'namespaceIndex': 1,
                                                                                     'identifierType': 'String',
                                                                                     'identifier': 'ItemV3'},
                                                                          'browseName': {'namespaceIndex': 1,
                                                                                         'name': 'v3'}}],
                                                          'continuationPoint': None}}]}},
            'expected': {'references': [{'nodeId': {'serverIndex': 0,
                                                    'namespaceIndex': 1,
                                                    'identifierType': 'String',
                                                    'identifier': 'ItemV1'},
                                         'browseName': {'namespaceIndex': 1, 'name': 'v1'}},
                                        {'nodeId': {'serverIndex': 0,
                                                    'namespaceIndex': 1,
                                                    'identifierType': 'String',
                                                    'identifier': 'ItemV2'},
                                         'browseName': {'namespaceIndex': 1, 'name': 'v2'}},
                                        {'nodeId': {'serverIndex': 0,
                                                    'namespaceIndex': 1,
                                                    'identifierType': 'String',
                                                    'identifier': 'ItemV3'},
                                         'browseName': {'namespaceIndex': 1, 'name': 'v3'}}],
                         'complete': True,
                         'trace': ['Browse', 'BrowseNext', 'BrowseNext'],
                         'consistency': 'unverified'}},
           {'name': 'read-failure-still-closes',
            'kind': 'sequence',
            'input': {'sequence': {'kind': 'file',
                                   'events': [{'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=ItemV1',
                                               'method': 'Open',
                                               'input': {'mode': 1},
                                               'status': 'Good',
                                               'output': {'fileHandle': 51}},
                                              {'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=ItemV1',
                                               'method': 'Read',
                                               'input': {'fileHandle': 51, 'length': 64},
                                               'status': 'Bad_CommunicationError'},
                                              {'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=ItemV1',
                                               'method': 'Close',
                                               'input': {'fileHandle': 51},
                                               'status': 'Good'}]}},
            'error': 'unavailable'},
           {'name': 'open-denied-no-handle',
            'kind': 'sequence',
            'input': {'sequence': {'kind': 'file',
                                   'events': [{'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=ItemV1',
                                               'method': 'Open',
                                               'input': {'mode': 1},
                                               'status': 'Bad_UserAccessDenied'}]}},
            'error': 'policy_denied'},
           {'name': 'missing-document-is-not-empty',
            'kind': 'sequence',
            'input': {'sequence': {'kind': 'file',
                                   'events': [{'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=Missing',
                                               'method': 'Open',
                                               'input': {'mode': 1},
                                               'status': 'Bad_NotFound'}]}},
            'error': 'not_found'},
           {'name': 'locked-document-is-not-redirect',
            'kind': 'sequence',
            'input': {'sequence': {'kind': 'file',
                                   'events': [{'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=ItemV1',
                                               'method': 'Open',
                                               'input': {'mode': 1},
                                               'status': 'Bad_NotReadable'}]}},
            'error': 'unavailable'},
           {'name': 'service-good-does-not-hide-datavalue-denial',
            'kind': 'sequence',
            'input': {'sequence': {'kind': 'metadata',
                                   'events': [{'service': 'Read',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=FirstRegistry',
                                               'serviceStatus': 'Good',
                                               'status': 'Good',
                                               'values': {'RegistryId': {'status': 'Bad_UserAccessDenied',
                                                                         'value': None}}}]}},
            'error': 'policy_denied'},
           {'name': 'expired-browse-continuation',
            'kind': 'sequence',
            'input': {'sequence': {'kind': 'browse',
                                   'events': [{'service': 'Browse',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=MainGroup',
                                               'status': 'Good',
                                               'output': {'references': [],
                                                          'continuationPoint': 'cDE='}},
                                              {'service': 'BrowseNext',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=MainGroup',
                                               'input': {'continuationPoints': ['cDE='],
                                                         'releaseContinuationPoints': False},
                                               'status': 'Bad_ContinuationPointInvalid'}]}},
            'error': 'inconsistent_snapshot'},
           {'name': 'wrong-handle-with-cleanup',
            'kind': 'sequence',
            'input': {'sequence': {'kind': 'file',
                                   'events': [{'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=ItemV1',
                                               'method': 'Open',
                                               'input': {'mode': 1},
                                               'status': 'Good',
                                               'output': {'fileHandle': 51}},
                                              {'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=ItemV1',
                                               'method': 'Read',
                                               'input': {'fileHandle': 52, 'length': 64},
                                               'status': 'Good',
                                               'output': {'data': ''}},
                                              {'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=ItemV1',
                                               'method': 'Close',
                                               'input': {'fileHandle': 51},
                                               'status': 'Good'}]}},
            'error': 'invalid_package'},
           {'name': 'byte-budget-still-closes',
            'kind': 'sequence',
            'input': {'max_bytes': 1,
                      'sequence': {'kind': 'file',
                                   'events': [{'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=ItemV2',
                                               'method': 'Open',
                                               'input': {'mode': 1},
                                               'status': 'Good',
                                               'output': {'fileHandle': 51}},
                                              {'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=ItemV2',
                                               'method': 'Read',
                                               'input': {'fileHandle': 51, 'length': 64},
                                               'status': 'Good',
                                               'output': {'data': 'AP8='}},
                                              {'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=ItemV2',
                                               'method': 'Close',
                                               'input': {'fileHandle': 51},
                                               'status': 'Good'}]}},
            'error': 'limit_exceeded'},
           {'name': 'premature-eof',
            'kind': 'sequence',
            'input': {'sequence': {'kind': 'file',
                                   'expectedSize': 2,
                                   'events': [{'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=ItemV2',
                                               'method': 'Open',
                                               'input': {'mode': 1},
                                               'status': 'Good',
                                               'output': {'fileHandle': 51}},
                                              {'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=ItemV2',
                                               'method': 'Read',
                                               'input': {'fileHandle': 51, 'length': 64},
                                               'status': 'Good',
                                               'output': {'data': ''}},
                                              {'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=ItemV2',
                                               'method': 'Close',
                                               'input': {'fileHandle': 51},
                                               'status': 'Good'}]}},
            'error': 'inconsistent_snapshot'},
           {'name': 'unsupported-core-version',
            'kind': 'sequence',
            'input': {'sequence': {'kind': 'metadata', 'specversion': '1.0-rc2', 'events': []}},
            'error': 'unsupported_version'},
           {'name': 'unsupported-actual-specversion-property',
            'kind': 'sequence',
            'input': {'sequence': {'kind': 'metadata',
                                   'request': {'operation': 'entity', 'target': '/'},
                                   'events': [{'service': 'Read',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=FirstRegistry',
                                               'status': 'Good',
                                               'values': {'SpecVersion': {'status': 'Good',
                                                                          'value': '1.0-rc2'}}}]}},
            'error': 'unsupported_version'},
           {'name': 'namespace-refresh-then-file-read',
            'kind': 'sequence',
            'input': {'sequence': {'kind': 'namespace-file',
                                   'refresh': True,
                                   'expectedSize': 70,
                                   'events': [{'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=NamespaceFile',
                                               'method': 'ExportNamespace',
                                               'input': {},
                                               'status': 'Good',
                                               'output': {}},
                                              {'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=NamespaceFile',
                                               'method': 'Open',
                                               'input': {'mode': 1},
                                               'status': 'Good',
                                               'output': {'fileHandle': 61}},
                                              {'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=NamespaceFile',
                                               'method': 'Read',
                                               'input': {'fileHandle': 61, 'length': 128},
                                               'status': 'Good',
                                               'output': {'data': 'PFVBTm9kZVNldCB4bWxucz0iaHR0cDovL29wY2ZvdW5kYXRpb24ub3JnL1VBLzIwMTEvMDMvVUFOb2RlU2V0LnhzZCIvPg=='}},
                                              {'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=NamespaceFile',
                                               'method': 'Read',
                                               'input': {'fileHandle': 61, 'length': 128},
                                               'status': 'Good',
                                               'output': {'data': ''}},
                                              {'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=NamespaceFile',
                                               'method': 'Close',
                                               'input': {'fileHandle': 61},
                                               'status': 'Good'}]}},
            'expected': {'data': 'PFVBTm9kZVNldCB4bWxucz0iaHR0cDovL29wY2ZvdW5kYXRpb24ub3JnL1VBLzIwMTEvMDMvVUFOb2RlU2V0LnhzZCIvPg==',
                         'size': 70,
                         'complete': True,
                         'trace': ['ExportNamespace', 'Open', 'Read', 'Read', 'Close'],
                         'consistency': 'unverified'}},
           {'name': 'namespace-refresh-not-supported',
            'kind': 'sequence',
            'input': {'sequence': {'kind': 'namespace-file',
                                   'refresh': True,
                                   'events': [{'service': 'Call',
                                               'session': 'session-1',
                                               'nodeId': 'nsu=urn:example:registry;s=NamespaceFile',
                                               'method': 'ExportNamespace',
                                               'input': {},
                                               'status': 'Bad_MethodInvalid'}]}},
            'error': 'unsupported_operation'}]}
REF = {case["name"]: case for case in REFERENCES["cases"]}
SEQ = {case["name"]: case for case in SEQUENCES["cases"]}


@pytest.mark.parametrize("case", REFERENCES["cases"], ids=lambda case: case["name"])
def test_opcua_reference_vectors_execute_native_mapping(case):
    operation = ua.map_registry_root if case["kind"] == "root" else ua.map_expanded_nodeid
    before = copy.deepcopy(case["input"])
    if "error" in case:
        with pytest.raises(FederationError) as error:
            operation(**case["input"])
        assert error.value.code == case["error"]
    else:
        assert operation(**case["input"]) == case["expected"]
    assert case["input"] == before


def test_opcua_namespace_and_server_table_remapping_preserves_portable_identity():
    first = ua.map_expanded_nodeid(**REF["remote-source-tables-to-target-seven"]["input"])
    second = ua.map_expanded_nodeid(**REF["reindexed-source-and-target"]["input"])
    assert first["nodeId"] == "ns=7;s=ItemV1"
    assert second["nodeId"] == "ns=2;s=ItemV1"
    assert first["portable"] == second["portable"] == (
        "svu=urn:example:ua:remote;nsu=urn:example:registry;s=ItemV1"
    )
    assert first["applicationuri"] == second["applicationuri"] == "urn:example:ua:remote"
    assert first["local"] is second["local"] is False


def test_opcua_explicit_registry_root_is_not_endpoint_or_application_identity():
    first = ua.map_registry_root(**REF["advertised-root"]["input"])
    second = ua.map_registry_root(**REF["another-root-at-same-endpoint"]["input"])
    assert first["endpoint"] == second["endpoint"] == "opc.tcp://ua.example.com:4840"
    assert first["applicationuri"] == second["applicationuri"] == "urn:example:ua:first"
    assert first["nodeId"] == "ns=3;s=FirstRegistry"
    assert second["nodeId"] == "ns=1;s=SecondRegistry"
    assert first["registryroot"] != second["registryroot"]


@pytest.mark.parametrize("node", [
    "i=0", "i=4294967296", "g=-", "ns=2;s=Root",
    "svu=urn:server;s=Root", "nsu=;s=Root", "b=!!", "s=",
])
def test_opcua_invalid_or_null_advertised_root_is_not_portable(node):
    with pytest.raises(FederationError) as error:
        ua.validate_registry_root(node)
    assert error.value.code == "invalid_package"


@pytest.mark.parametrize("node,identifier", [
    ("i=4294967295", 4294967295),
    ("nsu=urn:example:registry;s=a;b", "a;b"),
    ("nsu=urn:example%3Bregistry;s=Root", "Root"),
    ("b=AP8=", "AP8="),
])
def test_opcua_nodeid_identifier_bounds_and_namespace_encoding(node, identifier):
    parsed = ua.validate_registry_root(node)
    assert parsed.identifier == identifier
    assert parsed.portable() == node
    assert ua.parse_nodeid(parsed.portable()) == parsed


@pytest.mark.parametrize("field,value,code", [
    ("serverIndex", 99, "invalid_package"),
    ("namespaceIndex", 65536, "invalid_package"),
    ("identifierType", "Unknown", "invalid_package"),
    ("target_applicationuri", "opc.tcp://remote.example.com", "integrity_error"),
    ("target_namespace_array", [ua.UA_NAMESPACE, "urn:other"], "not_found"),
])
def test_opcua_remote_mapping_failures_do_not_default_to_namespace_zero(field, value, code):
    args = copy.deepcopy(REF["remote-source-tables-to-target-seven"]["input"])
    if field in args:
        args[field] = value
    else:
        args["reference"][field] = value
    with pytest.raises(FederationError) as error:
        ua.map_expanded_nodeid(**args)
    assert error.value.code == code


@pytest.mark.parametrize("case", SEQUENCES["cases"], ids=lambda case: case["name"])
def test_opcua_read_sequence_vectors_execute_services(case):
    before = copy.deepcopy(case["input"])
    if "error" in case:
        with pytest.raises(FederationError) as error:
            ua.interpret_read_sequence(**case["input"])
        assert error.value.code == case["error"]
    else:
        result = ua.interpret_read_sequence(**case["input"])
        assert result == case["expected"]
    assert case["input"] == before


@pytest.mark.parametrize("case,data,version,trace", [
    ("default-v1-short-chunks", b'{"type":"string"}', "v1",
     ["Open", "Read", "Read", "Read", "Close"]),
    ("explicit-v2-binary", b"\x00\xff", "v2", ["Open", "Read", "Read", "Close"]),
    ("zero-byte-v3", b"", "v3", ["Open", "Read", "Close"]),
])
def test_opcua_filetransfer_exact_bytes_default_and_empty_lifecycle(case, data, version, trace):
    result = ua.interpret_read_sequence(**SEQ[case]["input"])
    assert base64.b64decode(result["data"], validate=True) == data
    assert result["size"] == len(data)
    assert result["selectedXid"] == "/documents/main/assets/item/versions/" + version
    assert result["trace"] == trace
    assert result["complete"] is True
    assert result["consistency"] == "observed"


def test_opcua_metadata_only_catalog_never_opens_a_file():
    with patch.object(ua, "_file_sequence", side_effect=AssertionError("Unexpected FileType read")):
        result = ua.interpret_read_sequence(**SEQ["metadata-only-catalog"]["input"])
        with pytest.raises(FederationError) as error:
            ua.interpret_read_sequence(**SEQ["metadata-only-document-rejected-before-open"]["input"])
    assert error.value.code == "unsupported_operation"
    assert result["trace"] == ["Read"]
    assert result["values"]["ResourceId"] == "bridge"
    assert isinstance(result["values"]["federationprofiles"], list)


@pytest.mark.parametrize("change,code", [
    ("missing-close", "inconsistent_snapshot"), ("missing-eof", "inconsistent_snapshot"),
    ("wrong-handle", "invalid_package"), ("wrong-session", "invalid_package"),
    ("wrong-object", "invalid_package"), ("changed-default", "inconsistent_snapshot"),
    ("wrong-selected-version", "integrity_error"), ("unsupported-core", "unsupported_version"),
])
def test_opcua_partial_or_misdirected_capture_is_not_success(change, code):
    sequence = copy.deepcopy(SEQ["default-v1-short-chunks"]["input"]["sequence"])
    if change == "missing-close":
        sequence["events"].pop()
    elif change == "missing-eof":
        sequence["events"].pop(-2)
    elif change == "wrong-handle":
        sequence["events"][1]["input"]["fileHandle"] = 99
    elif change == "wrong-session":
        sequence["events"][1]["session"] = "another-session"
    elif change == "wrong-object":
        sequence["events"][1]["nodeId"] = "ns=3;s=Other"
    elif change == "changed-default":
        sequence["after"]["defaultversionid"] = "v2"
    elif change == "wrong-selected-version":
        sequence["selectedXid"] = "/documents/main/assets/item/versions/v2"
    else:
        sequence["specversion"] = "1.0-rc2"
    with pytest.raises(FederationError) as error:
        ua.interpret_read_sequence(sequence)
    assert error.value.code == code


@pytest.mark.parametrize("failed,cleanup", [
    ("Open", False), ("Read", False), ("Read", True), ("Close", False),
])
def test_opcua_filetransfer_failure_preserves_primary_error_and_cleanup(failed, cleanup):
    sequence = copy.deepcopy(SEQ["explicit-v2-binary"]["input"]["sequence"])
    events = sequence["events"]
    if failed == "Open":
        sequence["events"] = [events[0]]
        events[0]["status"] = "Bad_UserAccessDenied"
    elif failed == "Read":
        sequence["events"] = [events[0], events[1], events[-1]]
        events[1]["status"] = "Bad_CommunicationError"
        if cleanup:
            events[-1]["status"] = "Bad_NotSupported"
    else:
        events[-1]["status"] = "Bad_CommunicationError"
    with pytest.raises(FederationError) as error:
        ua.interpret_read_sequence(sequence)
    assert error.value.code == ("policy_denied" if failed == "Open" else "unavailable")
    assert failed + ":" in str(error.value)
    if cleanup:
        assert "Close cleanup failed: unsupported_operation" in str(error.value)
    elif failed == "Read":
        assert "cleanup" not in str(error.value)


@pytest.mark.parametrize("budget,valid", [(16, False), (17, True), (18, True)])
def test_opcua_filetransfer_byte_budget_boundary(budget, valid):
    sequence = copy.deepcopy(SEQ["default-v1-short-chunks"]["input"]["sequence"])
    if valid:
        assert ua.interpret_read_sequence(sequence, max_bytes=budget)["size"] == 17
    else:
        sequence["events"].pop(-2)
        with pytest.raises(FederationError) as error:
            ua.interpret_read_sequence(sequence, max_bytes=budget)
        assert error.value.code == "limit_exceeded"


def test_opcua_browse_consumes_reused_continuation_points_until_complete():
    sequence = SEQ["three-browse-pages-with-reused-continuation-token"]["input"]["sequence"]
    result = ua.interpret_read_sequence(sequence)
    assert result["trace"] == ["Browse", "BrowseNext", "BrowseNext"]
    assert result["complete"] is True
    assert len(result["references"]) == 3
    truncated = copy.deepcopy(sequence)
    truncated["events"].pop()
    with pytest.raises(FederationError) as error:
        ua.interpret_read_sequence(truncated)
    assert error.value.code == "inconsistent_snapshot"
    with pytest.raises(FederationError) as error:
        ua.interpret_read_sequence(sequence, max_references=2)
    assert error.value.code == "limit_exceeded"


def test_opcua_namespace_refresh_is_parameterless_then_file_transfer():
    case = next(case for case in SEQUENCES["cases"]
                if "expected" in case and case["input"]["sequence"]["kind"] == "namespace-file")
    result = ua.interpret_read_sequence(**case["input"])
    assert result["trace"][0:2] == ["ExportNamespace", "Open"]
    assert result["trace"][-1] == "Close"
    assert base64.b64decode(result["data"]).startswith(b"<")
    sequence = copy.deepcopy(case["input"]["sequence"])
    sequence["events"][0]["output"] = {"data": "PHgvPg=="}
    with pytest.raises(FederationError) as error:
        ua.interpret_read_sequence(sequence)
    assert error.value.code == "invalid_package"


@pytest.mark.parametrize("status,code", [
    ("Good", None), ("Bad_NotSupported", "unsupported_operation"),
    ("Bad_NodeIdUnknown", "not_found"), ("Bad_UserAccessDenied", "policy_denied"),
    ("Bad_InvalidArgument", "invalid_package"),
    ("Bad_ContinuationPointInvalid", "inconsistent_snapshot"),
    ("Bad_ResponseTooLarge", "limit_exceeded"), ("Bad_CommunicationError", "unavailable"),
    ("Uncertain", "unavailable"),
])
def test_opcua_statuscodes_preserve_failure_distinctions(status, code):
    assert ua.map_status(status) == code
