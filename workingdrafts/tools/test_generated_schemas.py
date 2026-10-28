"""Generated working-draft schemas preserve their model fields and scopes."""

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import avro.schema
import jsonpointer
import jsonschema
import pytest
from openapi_spec_validator import validate_spec


class TestGeneratedSchemas:
    @pytest.fixture
    def tools_dir(self):
        return Path(__file__).resolve().parents[2] / "tools"

    def generate_schema(self, model_path: Path, schema_type: str, tools_dir: Path, extra_args=()) -> dict:
        """Generate a schema using schema-generator.py."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                [sys.executable, 'schema-generator.py', '--type', schema_type, str(model_path), '--output', tmp_path, *extra_args],
                cwd=str(tools_dir),
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                pytest.fail(f"Schema generation failed: {result.stderr}")

            output = Path(tmp_path).read_bytes()
            schema = json.loads(output.decode('utf-8'))
            assert output == json.dumps(schema, indent=2).encode('utf-8')
            return schema
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def assert_json_structure(self, schema_data: dict):
        """Validate the structural invariants of generated JSON Structure."""
        assert schema_data['$schema'] == 'https://json-structure.org/meta/extended/v0/#'
        assert schema_data['$uses'] == ['JSONStructureAlternateNames']
        assert schema_data['type'] == 'object'
        assert schema_data['additionalProperties'] is False

        identifier_pattern = re.compile(r'^[A-Za-z][A-Za-z0-9]*$')

        def resolve_reference(reference):
            assert reference.startswith('#/definitions/')
            target = schema_data
            for segment in reference[2:].split('/'):
                target = target[segment]
            return target

        def visit(node):
            if isinstance(node, dict):
                if '$ref' in node:
                    resolve_reference(node['$ref'])
                for collection_name in ('properties', 'definitions'):
                    for name in node.get(collection_name, {}):
                        assert identifier_pattern.fullmatch(name), name
                for value in node.values():
                    visit(value)
            elif isinstance(node, list):
                for value in node:
                    visit(value)

        visit(schema_data)

    def test_registry_model_avro_schema_valid(self, tools_dir):
        model = tools_dir.parent / "workingdrafts" / "models" / "registry" / "model.json"
        schema_data = self.generate_schema(model, 'avro-schema', tools_dir)
        checked_schema = model.parent / 'schemas' / 'document-schema.avsc'
        assert schema_data == json.loads(checked_schema.read_text(encoding='utf-8'))
        schema = avro.schema.parse(json.dumps(schema_data))
        category = schema.fields_dict['categories'].type.values
        registry = category.fields_dict['registries'].type.values
        registry = registry.fields_dict['versions'].type.schemas[0].values
        profile = registry.fields_dict['federationprofiles'].type.items
        relationship = registry.fields_dict['relationships'].type.items
        assert profile.fields_dict['name'].type.type == 'string'
        assert profile.fields_dict['endpoint'].type.type == 'string'
        parameters = profile.fields_dict['parameters'].type
        assert parameters.fields_dict['Extensions'].type.values.fullname == 'io.xregistry.GenericRecord'
        assert relationship.fields_dict['target'].type.type == 'string'
        assert relationship.fields_dict['labels'].type.values.type == 'string'

    @pytest.mark.parametrize("domain,relative_path", [
        ('openusd', 'workingdrafts/models/openusd'),
        ('wot', 'workingdrafts/models/wot'),
        ('publication', 'workingdrafts/publication'),
    ])
    @pytest.mark.parametrize("schema_type,filename", [
        ('json-schema', 'document-schema.json'),
        ('json-structure', 'document-schema.struct.json'),
        ('avro-schema', 'document-schema.avsc'),
        ('openapi', 'openapi.json'),
    ])
    def test_workingdraft_schema_fidelity(
        self, tools_dir, domain, relative_path, schema_type, filename
    ):
        model_path = tools_dir.parent / relative_path / 'model.json'
        model = json.loads(model_path.read_text(encoding='utf-8'))
        extra_args = []
        if schema_type in ('json-schema', 'json-structure'):
            extra_args = ['--schema-id', f'https://xregistry.io/{relative_path}/schemas/{filename}']
        if schema_type == 'json-structure':
            extra_args += ['--schema-name', {
                'openusd': 'OpenUsdRegistryDocument',
                'wot': 'WoTRegistryDocument',
                'publication': 'PublicationRegistryDocument',
            }[domain]]
        data = self.generate_schema(model_path, schema_type, tools_dir, extra_args)
        if schema_type == 'avro-schema':
            root = avro.schema.parse(json.dumps(data))
        elif schema_type == 'json-structure':
            self.assert_json_structure(data)
            root = data
        elif schema_type == 'openapi':
            validate_spec(data)
            root = data['components']['schemas']['document']
        else:
            jsonschema.Draft7Validator.check_schema(data)
            root = data

        def resolve(node):
            while isinstance(node, dict):
                if '$ref' in node:
                    node = jsonpointer.resolve_pointer(data, node['$ref'][1:])
                elif isinstance(node.get('type'), dict):
                    node = node['type']
                else:
                    break
            return node

        def properties(node):
            node = resolve(node)
            if schema_type == 'avro-schema':
                return {field.name: field.type for field in node.fields}
            return node['properties']

        def collection(node):
            node = resolve(node)
            if schema_type == 'avro-schema':
                assert node.type == 'map'
                return node.values
            key = 'values' if schema_type == 'json-structure' else 'additionalProperties'
            return resolve(node[key])

        def assert_attributes(node, attributes):
            fields = properties(node)
            for name, definition in attributes.items():
                if name == '*':
                    continue
                assert name in fields, name
                actual = resolve(fields[name])
                kind = definition['type']
                if schema_type == 'avro-schema':
                    expected_type = {
                        'uri': 'string', 'url': 'string', 'uinteger': 'int',
                        'object': 'record',
                    }.get(kind, kind)
                    assert actual.type == expected_type, name
                else:
                    expected_type = {
                        'uri': 'uri' if schema_type == 'json-structure' else 'string',
                        'url': 'uri' if schema_type == 'json-structure' else 'string',
                        'uinteger': 'uint32' if schema_type == 'json-structure' else 'integer',
                        'map': 'map' if schema_type == 'json-structure' else 'object',
                    }.get(kind, kind)
                    assert actual['type'] == expected_type, name
                    if definition.get('required') and 'default' not in definition:
                        assert name in resolve(node).get('required', [])
                    if 'default' in definition:
                        assert actual['default'] == definition['default']
                    if definition.get('enum') and definition.get('strict', True):
                        assert actual['enum'] == definition['enum']
                    elif 'enum' in definition:
                        assert 'enum' not in actual
                if kind == 'object':
                    assert_attributes(actual, definition.get('attributes', {}))
                elif kind == 'array':
                    item = actual.items if schema_type == 'avro-schema' else actual['items']
                    item_type = item.type if schema_type == 'avro-schema' else item['type']
                    assert item_type == definition['item']['type']

        for group_name, group in model['groups'].items():
            group_schema = collection(properties(root)[group_name])
            assert_attributes(group_schema, group.get('attributes', {}))
            for resource_name, resource in group.get('resources', {}).items():
                resource_schema = collection(properties(group_schema)[resource_name])
                resource_fields = properties(resource_schema)
                if resource.get('maxversions', -1) != 1:
                    version_field = resource_fields['versions']
                    if schema_type == 'avro-schema':
                        version_field = version_field.schemas[0]
                    version_schema = collection(version_field)
                    assert 'versionid' in properties(version_schema)
                else:
                    version_schema = resource_schema
                assert_attributes(version_schema, resource.get('attributes', {}))
                if resource.get('metaattributes'):
                    meta_schema = resource_fields['meta']
                    assert_attributes(meta_schema, resource['metaattributes'])
                    assert not (set(resource['metaattributes']) & set(resource_fields))
                    if version_schema is not resource_schema:
                        assert 'meta' not in properties(version_schema)
                    if schema_type == 'openapi':
                        path = f'/{group_name}/{{groupid}}/{resource_name}/{{resourceid}}/meta'
                        response = data['paths'][path]['get']['responses']['200']['content']['application/json']['schema']
                        assert properties(response) == properties(meta_schema)
                if schema_type == 'openapi':
                    assert f'/{group_name}' in data['paths']
                    path = f'/{group_name}/{{groupid}}/{resource_name}/{{resourceid}}/versions/{{versionid}}'
                    response = data['paths'][path]['get']['responses']['200']['content']['application/json']['schema']
                    assert properties(response) == properties(version_schema)
            for imported in group.get('ximportresources', []):
                source_group, resource_name = imported.strip('/').split('/')
                source = collection(properties(root)[source_group])
                expected = collection(properties(source)[resource_name])
                actual = collection(properties(group_schema)[resource_name])
                assert actual == expected
                if schema_type == 'openapi':
                    resource = model['groups'][source_group]['resources'][resource_name]
                    expected_version = expected
                    if resource.get('maxversions', -1) != 1:
                        expected_version = collection(properties(expected)['versions'])
                    path = f'/{group_name}/{{groupid}}/{resource_name}/{{resourceid}}/versions/{{versionid}}'
                    response = data['paths'][path]['get']['responses']['200']['content']['application/json']['schema']
                    assert properties(response) == properties(expected_version)

        if domain == 'publication':
            group = collection(properties(root)['publications'])
            channel = collection(properties(group)['channels'])
            meta = properties(channel)['meta']
            assert {'scope', 'head'} <= properties(meta).keys()
            head = properties(meta)['head']
            assert set(properties(head)) == {'url', 'digest', 'size'}
            if schema_type in ('json-schema', 'openapi'):
                head_schema = resolve(head)
                validator = jsonschema.Draft7Validator(head_schema)
                valid_head = {'url': 'https://example.test/manifest', 'digest': 'abc', 'size': 0}
                validator.validate(valid_head)
                for missing in ('url', 'digest', 'size'):
                    invalid = dict(valid_head)
                    invalid.pop(missing)
                    assert not validator.is_valid(invalid)
                assert not validator.is_valid({**valid_head, 'size': -1})
                assert not validator.is_valid({**valid_head, 'size': '0'})
        elif domain == 'wot':
            group = collection(properties(root)['thingmodelgroups'])
            resource = collection(properties(group)['thingmodels'])
            assert 'compatibility' in properties(properties(resource)['meta'])
        else:
            group = collection(properties(root)['usdassetgroups'])
            assert 'rootlayer' in properties(group)

        checked = model_path.parent / 'schemas' / filename
        assert checked.read_bytes() == json.dumps(data, indent=2).encode('utf-8')

    @pytest.mark.parametrize("containers", [
        ('array',), ('map',), ('array', 'map'), ('map', 'array'),
    ])
    @pytest.mark.parametrize("typed", [True, False], ids=['typed-object', 'generic-object'])
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
        schema_data = self.generate_schema(model_path, 'avro-schema', tools_dir)
        schema = avro.schema.parse(json.dumps(schema_data))
        item = schema.fields_dict['groups'].type.values.fields_dict['entries'].type
        for container in containers:
            assert item.type == container
            item = item.items if container == 'array' else item.values
        if typed:
            assert item.fields_dict['name'].type.type == 'string'
        else:
            assert item.fullname == 'io.xregistry.GenericRecord'
