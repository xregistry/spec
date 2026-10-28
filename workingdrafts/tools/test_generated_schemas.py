"""Schema generation preserves existing outputs and converts Avro object items."""

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
        assert profile.fields_dict['name'].type.type == 'string'
        assert profile.fields_dict['endpoint'].type.type == 'string'
        parameters = profile.fields_dict['parameters'].type
        assert parameters.fullname == 'io.xregistry.GenericRecord'
        assert relationship.fields_dict['target'].type.type == 'string'
        assert relationship.fields_dict['labels'].type.values.type == 'string'

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
