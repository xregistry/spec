"""Schema generation preserves existing outputs and converts Avro object items."""

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import avro.schema
import jsonpointer
import jsonschema
import pytest
from openapi_spec_validator import validate_spec


FORMATS = [
    ('json-schema', 'document-schema.json'),
    ('json-structure', 'document-schema.struct.json'),
    ('avro-schema', 'document-schema.avsc'),
    ('openapi', 'openapi.json'),
]


class TestGeneratedSchemas:
    @pytest.fixture
    def tools_dir(self):
        return Path(__file__).resolve().parents[2] / "tools"

    def generate_schema(self, model_paths, schema_type, tools_dir, tmp_path, extra_args=()):
        output = tmp_path / 'generated.json'
        result = subprocess.run(
            [
                sys.executable, str(tools_dir / 'schema-generator.py'),
                '--type', schema_type, '--output', str(output),
                *extra_args, *map(str, model_paths),
            ],
            cwd=tools_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stderr
        return json.loads(output.read_text(encoding='utf-8'))

    def assert_valid_schema(self, data, schema_type):
        if schema_type == 'avro-schema':
            return avro.schema.parse(json.dumps(data))
        if schema_type == 'json-schema':
            jsonschema.Draft7Validator.check_schema(data)
        elif schema_type == 'openapi':
            validate_spec(data)
        else:
            assert data['$schema'] == 'https://json-structure.org/meta/extended/v0/#'
            assert data['$uses'] == ['JSONStructureAlternateNames']
            assert data['type'] == 'object'
            assert data['additionalProperties'] is False
            identifier = re.compile(r'^[A-Za-z][A-Za-z0-9]*$')

            def visit(node):
                if isinstance(node, dict):
                    if '$ref' in node:
                        jsonpointer.resolve_pointer(data, node['$ref'][1:])
                    for collection in ('properties', 'definitions'):
                        for name in node.get(collection, {}):
                            assert identifier.fullmatch(name), name
                    for value in node.values():
                        visit(value)
                elif isinstance(node, list):
                    for value in node:
                        visit(value)

            visit(data)
        return data

    def generation_args(self, checked, schema_type):
        if schema_type == 'json-schema':
            return ['--schema-id', checked['$id']]
        if schema_type == 'json-structure':
            return ['--schema-id', checked['$id'], '--schema-name', checked['name']]
        return []

    @pytest.mark.parametrize('domain', ['schema', 'message', 'endpoint', 'cloudevents'])
    @pytest.mark.parametrize('schema_type,filename', FORMATS)
    def test_existing_domain_schema_output_unchanged(
        self, tools_dir, tmp_path, domain, schema_type, filename
    ):
        root = tools_dir.parent
        domains = ['endpoint', 'message', 'schema'] if domain == 'cloudevents' else [domain]
        checked = json.loads((root / domain / 'schemas' / filename).read_text(encoding='utf-8'))
        data = self.generate_schema(
            [root / source / 'model.json' for source in domains],
            schema_type, tools_dir, tmp_path, self.generation_args(checked, schema_type),
        )
        assert data == checked
        self.assert_valid_schema(data, schema_type)

    @pytest.mark.parametrize('relative_path', [
        'workingdrafts/models/registry',
        'workingdrafts/models/openusd',
        'workingdrafts/models/wot',
        'workingdrafts/models/media-endpoints',
        'workingdrafts/publication',
    ])
    @pytest.mark.parametrize('schema_type,filename', FORMATS)
    def test_workingdraft_schema_reproduction(
        self, tools_dir, tmp_path, relative_path, schema_type, filename
    ):
        model = tools_dir.parent / relative_path / 'model.json'
        checked = json.loads((model.parent / 'schemas' / filename).read_text(encoding='utf-8'))
        data = self.generate_schema(
            [model], schema_type, tools_dir, tmp_path,
            self.generation_args(checked, schema_type),
        )
        assert data == checked
        self.assert_valid_schema(data, schema_type)

    def test_registry_model_avro_schema_valid(self, tools_dir, tmp_path):
        model = tools_dir.parent / 'workingdrafts' / 'models' / 'registry' / 'model.json'
        data = self.generate_schema([model], 'avro-schema', tools_dir, tmp_path)
        schema = self.assert_valid_schema(data, 'avro-schema')
        category = schema.fields_dict['categories'].type.values
        registry = category.fields_dict['registries'].type.values
        profile = registry.fields_dict['federationprofiles'].type.items
        relationship = registry.fields_dict['relationships'].type.items
        assert profile.fields_dict['binding'].type.type == 'string'
        assert profile.fields_dict['endpoint'].type.type == 'string'
        parameters = profile.fields_dict['parameters'].type
        assert parameters.fullname == 'io.xregistry.GenericRecord'
        assert relationship.fields_dict['target'].type.type == 'string'
        assert relationship.fields_dict['labels'].type.values.type == 'string'

    def test_media_endpoints_source_provenance_matches_artifacts(self, tools_dir):
        root = tools_dir.parent / 'workingdrafts' / 'models' / 'media-endpoints'
        source = json.loads((root / 'source.json').read_text(encoding='utf-8'))
        assert source['draft']['revision'] == '9613f002c82c9568fbefc5f1f0cf0490d6df572a'
        assert source['draft']['gitBlob'] == '8e7e6d46c21e391c4dd611dbea92f40acf0231d3'
        assert source['base']['revision'] == 'adf5b6a63e60c3baa78e844da8b7ce2a0d60c179'

        for model in source['base']['models']:
            content = (root / model['snapshot']).read_bytes()
            assert hashlib.sha256(content).hexdigest() == model['sha256']

        for filename, artifact in source['artifacts'].items():
            content = (root / filename).read_bytes()
            assert hashlib.sha256(content).hexdigest() == artifact['sha256']

        model_path = root / 'model.json'
        generator_spec = importlib.util.spec_from_file_location(
            'media_endpoints_schema_generator', tools_dir / 'schema-generator.py'
        )
        generator = importlib.util.module_from_spec(generator_spec)
        generator_spec.loader.exec_module(generator)
        resolved_model = generator.resolve_imports(str(root), json.loads(
            model_path.read_text(encoding='utf-8')
        ))
        core_schema = json.loads(
            (tools_dir.parent / 'core' / 'model.schema.json').read_text(encoding='utf-8')
        )
        jsonschema.Draft7Validator(core_schema).validate(resolved_model)

    def test_media_endpoints_model_composes_base_protocols_without_codec_enums(
        self, tools_dir, tmp_path
    ):
        root = tools_dir.parent / 'workingdrafts' / 'models' / 'media-endpoints'
        model = json.loads((root / 'model.json').read_text(encoding='utf-8'))
        media_protocols = model['groups']['endpoints']['attributes']['protocol']['ifvalues']
        media_protocols = {
            name: value for name, value in media_protocols.items() if name != '$include'
        }
        expected_streamformats = {
            'SRT': ['mpegts'],
            'WebRTC': ['srtp'],
            'RTSP/1.0': ['rtp', 'rtp-mpegts'],
            'RTP/2': ['rtp', 'rtp-mpegts'],
            'MPEGTS-UDP': ['mpegts'],
            'RTMP/1.0': ['flv'],
            'RIST-Simple/2020': ['rtp-mpegts'],
            'RIST-Main/2024': ['rtp-mpegts'],
        }
        assert set(media_protocols) == {
            'SRT', 'WebRTC', 'RTSP/1.0', 'RTSP/2.0', 'RTP/2', 'MPEGTS-UDP',
            'RTMP/1.0', 'HLS', 'DASH', 'RIST-Simple/2020', 'RIST-Main/2024',
        }
        assert model['groups']['endpoints']['attributes']['usage']['item']['enum'] == [
            'subscriber', 'consumer', 'producer'
        ]

        for name, values in expected_streamformats.items():
            attributes = media_protocols[name]['siblingattributes']['protocoloptions']['attributes']
            assert attributes['streamformat']['enum'] == values
            for codec in ('videocodec', 'audiocodec'):
                assert attributes[codec]['type'] == 'string'
                assert 'enum' not in attributes[codec]

        options = media_protocols['WebRTC']['siblingattributes']['protocoloptions']['attributes']
        assert options['signaling']['required'] is True
        assert options['signalingreference']['type'] == 'uri'
        options = media_protocols['RTMP/1.0']['siblingattributes']['protocoloptions']['attributes']
        assert options['application']['required'] is True
        assert options['streamname']['required'] is True

        schema = self.generate_schema(
            [root / 'model.json'],
            'json-schema',
            tools_dir,
            tmp_path,
            ['--schema-id', 'https://xregistry.io/workingdrafts/models/media-endpoints/schemas/document-schema.json'],
        )
        usage = schema['definitions']['endpoint-schema']['endpoint']['properties']['usage']
        assert usage['items']['enum'] == ['subscriber', 'consumer', 'producer']
        json_structure = self.generate_schema(
            [root / 'model.json'],
            'json-structure',
            tools_dir,
            tmp_path,
            [
                '--schema-id',
                'https://xregistry.io/workingdrafts/models/media-endpoints/schemas/document-schema.struct.json',
                '--schema-name',
                'MediaEndpointRegistryDocument',
            ],
        )
        usage = json_structure['definitions']['Endpoints']['Endpoint']['properties']['usage']
        assert usage['items']['enum'] == ['subscriber', 'consumer', 'producer']
        endpoint = schema['definitions']['endpoint-schema']['endpoint']
        branches = {}
        for conditional in endpoint['allOf']:
            for branch in conditional.get('oneOf', []):
                properties = branch.get('properties', {})
                protocol = properties.get('protocol', {})
                for selector in protocol.get('enum', []):
                    branches[selector] = properties

        base = json.loads((root / 'sources' / 'endpoint-model.source.json').read_text(encoding='utf-8'))
        base_protocols = base['groups']['endpoints']['attributes']['protocol']['ifvalues']
        assert set(branches) == set(base_protocols) | set(media_protocols)
        for selector in media_protocols:
            properties = branches[selector]['protocoloptions']['properties']
            actual = set(properties)
            assert {'endpoints', 'authorization', 'deployed'} <= actual
            for codec in ('videocodec', 'audiocodec'):
                if codec in properties:
                    assert properties[codec]['type'] == 'string'
                    assert 'enum' not in properties[codec]

        for selector in expected_streamformats:
            options = branches[selector]['protocoloptions']['properties']
            assert options['streamformat']['type'] == 'string'

        for selector, value in base_protocols.items():
            expected = set(value['siblingattributes']['protocoloptions']['attributes']) - {'*'}
            actual = set(branches[selector]['protocoloptions']['properties'])
            assert actual == expected

    @pytest.mark.parametrize('containers', [
        ('array',), ('map',), ('array', 'map'), ('map', 'array'),
    ])
    @pytest.mark.parametrize('typed', [True, False], ids=['typed-object', 'generic-object'])
    def test_avro_nested_object_items(self, tools_dir, tmp_path, containers, typed):
        attribute = {'type': 'object'}
        if typed:
            attribute['attributes'] = {'name': {'type': 'string'}}
        for container in reversed(containers):
            attribute = {'type': container, 'item': attribute}
        model = {'groups': {'groups': {
            'singular': 'group', 'attributes': {'entries': attribute},
        }}}
        model_path = tmp_path / 'model.json'
        model_path.write_text(json.dumps(model), encoding='utf-8')
        data = self.generate_schema([model_path], 'avro-schema', tools_dir, tmp_path)
        schema = self.assert_valid_schema(data, 'avro-schema')
        item = schema.fields_dict['groups'].type.values.fields_dict['entries'].type
        for container in containers:
            assert item.type == container
            item = item.items if container == 'array' else item.values
        if typed:
            assert item.fields_dict['name'].type.type == 'string'
        else:
            assert item.fullname == 'io.xregistry.GenericRecord'
