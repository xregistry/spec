"""
Tests for schema generation and model validation.
"""
import importlib.util
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

import avro.io
import avro.schema
import jsonschema
import pytest
from jsonpointer import resolve_pointer
from openapi_schema_validator import OAS30ReadValidator, OAS30Validator, OAS30WriteValidator
from openapi_spec_validator import validate_spec


class TestSchemaGenerator:
    """Test suite for schema generator output validation."""

    @pytest.fixture
    def tools_dir(self):
        """Get the tools directory path."""
        return Path(__file__).parent

    @pytest.fixture
    def message_model(self, tools_dir):
        """Path to the message model.json."""
        return tools_dir.parent / "message" / "model.json"

    @pytest.fixture
    def endpoint_model(self, tools_dir):
        """Path to the endpoint model.json."""
        return tools_dir.parent / "endpoint" / "model.json"

    @pytest.fixture
    def schema_model(self, tools_dir):
        """Path to the schema model.json."""
        return tools_dir.parent / "schema" / "model.json"

    def generate_schema(self, model_path: Path, schema_type: str, tools_dir: Path) -> dict:
        """Generate a schema using schema-generator.py."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                ['python', 'schema-generator.py', '--type', schema_type, str(model_path), '--output', tmp_path],
                cwd=str(tools_dir),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                pytest.fail(f"Schema generation failed: {result.stderr}")

            with open(tmp_path, 'r') as f:
                return json.load(f)
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

    def test_schema_model_json_structure(self, schema_model, tools_dir):
        """Test native JSON Structure shape for a registry model."""
        schema_data = self.generate_schema(schema_model, 'json-structure', tools_dir)

        self.assert_json_structure(schema_data)
        assert schema_data['properties']['schemagroups']['type'] == 'map'
        schema_resource = schema_data['definitions']['Schemagroups']['Schema']
        assert schema_resource['properties']['format']['type'] == 'string'
        assert schema_resource['properties']['meta']['properties']['shortself']['type'] == 'uri'
        schema_version = schema_data['definitions']['Schemagroups']['SchemaVersion']
        assert schema_version['properties']['format']['type'] == 'string'

    def test_json_structure_resource_conditional_attributes_remain_optional(
        self, schema_model, tools_dir, tmp_path
    ):
        model = json.loads(schema_model.read_text(encoding='utf-8'))
        attributes = model['groups']['schemagroups']['resources']['schemas']['attributes']
        attributes['format']['ifvalues'] = {
            'custom': {
                'siblingattributes': {
                    'fieldrequired': {'type': 'string', 'required': True}
                }
            }
        }
        model_path = tmp_path / 'model.json'
        model_path.write_text(json.dumps(model), encoding='utf-8')
        schema = self.generate_schema(model_path, 'json-structure', tools_dir)
        definitions = schema['definitions']['Schemagroups']
        resource = definitions['Schema']
        version = definitions['SchemaVersion']
        assert resource['properties']['fieldrequired']['type'] == 'string'
        assert 'fieldrequired' not in resource.get('required', [])
        assert 'fieldrequired' in version['required']

    def test_cloudevents_multi_model_json_structure(
        self, endpoint_model, message_model, schema_model, tools_dir
    ):
        """Test namespaced JSON Structure composition for all extension models."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                [
                    'python', 'schema-generator.py', '--type', 'json-structure',
                    str(endpoint_model), str(message_model), str(schema_model),
                    '--output', tmp_path
                ],
                cwd=str(tools_dir),
                capture_output=True,
                text=True,
                timeout=30
            )
            assert result.returncode == 0, result.stderr
            with open(tmp_path, 'r', encoding='utf-8') as schema_file:
                schema_data = json.load(schema_file)
            self.assert_json_structure(schema_data)
            assert set(schema_data['properties']) == {
                'endpoints', 'messagegroups', 'schemagroups'
            }
            assert set(schema_data['definitions']) == {
                'Endpoints', 'Messagegroups', 'Schemagroups'
            }
            message = schema_data['definitions']['Messagegroups']['Message']
            protocol_properties = message['properties']['protocoloptions'][
                'properties'
            ]['properties']['properties']
            assert protocol_properties['messageId']['altnames'] == {
                'json': 'message-id'
            }
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    @pytest.mark.parametrize('strict', [True, False], ids=['strict-default', 'advisory'])
    def test_array_item_enum_is_projected_to_schema_formats(self, tools_dir, tmp_path, strict):
        item = {
            "type": "string",
            "enum": ["subscriber", "producer"]
        }
        if not strict:
            item["strict"] = False
        model_path = tmp_path / 'model.json'
        model_path.write_text(json.dumps({
            "groups": {
                "endpoints": {
                    "singular": "endpoint",
                    "attributes": {
                        "usage": {
                            "type": "array",
                            "item": item
                        }
                    }
                }
            }
        }), encoding='utf-8')

        json_schema = self.generate_schema(model_path, 'json-schema', tools_dir)
        usage = json_schema['definitions']['endpoint-schema']['endpoint']['properties']['usage']
        if strict:
            assert usage['items']['enum'] == ['subscriber', 'producer']
        else:
            assert 'enum' not in usage['items']

        json_structure = self.generate_schema(model_path, 'json-structure', tools_dir)
        usage = json_structure['definitions']['Endpoints']['Endpoint']['properties']['usage']
        if strict:
            assert usage['items']['enum'] == ['subscriber', 'producer']
        else:
            assert 'enum' not in usage['items']

        openapi = self.generate_schema(model_path, 'openapi', tools_dir)
        usage = openapi['components']['schemas']['endpoint']['properties']['usage']
        if strict:
            assert usage['items']['enum'] == ['subscriber', 'producer']
        else:
            assert 'enum' not in usage['items']

        avro_data = self.generate_schema(model_path, 'avro-schema', tools_dir)
        schema = avro.schema.parse(json.dumps(avro_data))
        usage = schema.fields_dict['endpoints'].type.values.fields_dict['usage'].type.items
        if strict:
            assert usage.type == 'enum'
            assert usage.symbols == ['subscriber', 'producer']
        else:
            assert usage.type == 'string'

    def test_avro_preserves_distinct_value_sets_for_same_named_array_items(self, tools_dir, tmp_path):
        model_path = tmp_path / 'model.json'
        value_sets = {
            'catalogs': ('catalog', ['producer', 'subscriber']),
            'indexes': ('index', ['auditor']),
        }
        model_path.write_text(json.dumps({'groups': {
            plural: {'singular': singular, 'attributes': {
                'usage': {'type': 'array', 'item': {'type': 'string', 'enum': values}},
            }}
            for plural, (singular, values) in value_sets.items()
        }}), encoding='utf-8')
        schema_data = self.generate_schema(model_path, 'avro-schema', tools_dir)
        schema = avro.schema.parse(json.dumps(schema_data))

        for plural, (_, values) in value_sets.items():
            usage = schema.fields_dict[plural].type.values.fields_dict['usage'].type
            assert usage.items.symbols == values
            assert avro.io.validate(usage, values)
            assert not avro.io.validate(usage, ['publisher'])

    def test_message_model_avro_schema_valid(self, message_model, tools_dir):
        """Test that message model generates valid Avro schema."""
        schema_data = self.generate_schema(message_model, 'avro-schema', tools_dir)
        
        # Validate with Apache Avro library
        try:
            schema = avro.schema.parse(json.dumps(schema_data))
            assert schema is not None
            assert schema.type == 'record'
            assert schema.namespace == 'io.xregistry'
            assert schema.name == 'DocumentType'
        except Exception as e:
            pytest.fail(f"Avro schema validation failed: {e}")

    def test_message_model_avro_has_generic_record(self, message_model, tools_dir):
        """Test that message model with extensions includes GenericRecord definition."""
        schema_data = self.generate_schema(message_model, 'avro-schema', tools_dir)
        
        # Check for genericRecordDefinition field
        fields = schema_data.get('fields', [])
        generic_record_field = next((f for f in fields if f['name'] == 'genericRecordDefinition'), None)
        
        assert generic_record_field is not None, "GenericRecord definition field should be present"
        assert generic_record_field['type']['type'] == 'array'
        assert generic_record_field['type']['items']['type'] == 'record'
        assert generic_record_field['type']['items']['name'] == 'GenericRecord'

    def test_message_model_avro_extensions_field(self, message_model, tools_dir):
        """Test that Extensions field uses GenericRecord reference, not inline definition."""
        schema_data = self.generate_schema(message_model, 'avro-schema', tools_dir)
        
        # Navigate to messagegroups -> MessagegroupType -> Extensions field
        messagegroups_field = next(f for f in schema_data['fields'] if f['name'] == 'messagegroups')
        messagegroup_type = messagegroups_field['type']['values']
        extensions_field = next((f for f in messagegroup_type['fields'] if f['name'] == 'Extensions'), None)
        
        assert extensions_field is not None, "Extensions field should exist"
        assert extensions_field['type']['type'] == 'map'
        
        # Critical: values should be a string reference, not an inline definition
        values_type = extensions_field['type']['values']
        assert isinstance(values_type, str), "Extensions map values should be a type reference string"
        assert values_type == 'io.xregistry.GenericRecord', "Should reference GenericRecord by qualified name"

    def test_message_model_json_schema_valid(self, message_model, tools_dir):
        """Test that message model generates valid JSON Schema."""
        schema_data = self.generate_schema(message_model, 'json-schema', tools_dir)
        
        # Validate it's a proper JSON Schema
        assert '$schema' in schema_data or 'type' in schema_data
        
        # Try to validate against JSON Schema meta-schema
        try:
            jsonschema.Draft7Validator.check_schema(schema_data)
        except jsonschema.SchemaError as e:
            pytest.fail(f"JSON Schema validation failed: {e}")

    def test_endpoint_model_avro_schema_valid(self, endpoint_model, tools_dir):
        """Test that endpoint model generates valid Avro schema."""
        schema_data = self.generate_schema(endpoint_model, 'avro-schema', tools_dir)
        
        # Validate with Apache Avro library
        try:
            schema = avro.schema.parse(json.dumps(schema_data))
            assert schema is not None
            assert schema.type == 'record'
        except Exception as e:
            pytest.fail(f"Endpoint Avro schema validation failed: {e}")

    def test_endpoint_model_json_schema_valid(self, endpoint_model, tools_dir):
        """Test that endpoint model generates valid JSON Schema."""
        schema_data = self.generate_schema(endpoint_model, 'json-schema', tools_dir)
        
        try:
            jsonschema.Draft7Validator.check_schema(schema_data)
        except jsonschema.SchemaError as e:
            pytest.fail(f"Endpoint JSON Schema validation failed: {e}")

    def test_schema_model_avro_schema_valid(self, schema_model, tools_dir):
        """Test that schema model generates valid Avro schema."""
        schema_data = self.generate_schema(schema_model, 'avro-schema', tools_dir)
        
        # Validate with Apache Avro library
        try:
            schema = avro.schema.parse(json.dumps(schema_data))
            assert schema is not None
            assert schema.type == 'record'
        except Exception as e:
            pytest.fail(f"Schema model Avro schema validation failed: {e}")

    def test_schema_model_json_schema_valid(self, schema_model, tools_dir):
        """Test that schema model generates valid JSON Schema."""
        schema_data = self.generate_schema(schema_model, 'json-schema', tools_dir)
        
        try:
            jsonschema.Draft7Validator.check_schema(schema_data)
        except jsonschema.SchemaError as e:
            pytest.fail(f"Schema model JSON Schema validation failed: {e}")

    def test_avro_generic_record_qualified_names(self, message_model, tools_dir):
        """Test that GenericRecord uses fully qualified names for recursive references."""
        schema_data = self.generate_schema(message_model, 'avro-schema', tools_dir)
        
        # Get GenericRecord definition
        generic_def_field = next(f for f in schema_data['fields'] if f['name'] == 'genericRecordDefinition')
        generic_record = generic_def_field['type']['items']
        
        # Check recursive references use qualified names
        object_field = generic_record['fields'][0]
        map_values = object_field['type']['values']
        
        # Find the array type in the union
        array_type = next(t for t in map_values if isinstance(t, dict) and t.get('type') == 'array')
        array_items = array_type['items']
        
        # Check for qualified GenericRecord reference in array items
        assert 'io.xregistry.GenericRecord' in array_items, \
            "Array items should contain qualified GenericRecord reference"
        
        # Check for qualified GenericRecord reference in map values union
        assert 'io.xregistry.GenericRecord' in map_values, \
            "Map values should contain qualified GenericRecord reference"

    def test_avro_any_type_uses_generic_record(self, message_model, tools_dir):
        """Test that 'any' type fields use GenericRecord reference."""
        schema_data = self.generate_schema(message_model, 'avro-schema', tools_dir)
        
        # Navigate to message -> dataschema field (which has type 'any' in model)
        messagegroups_field = next(f for f in schema_data['fields'] if f['name'] == 'messagegroups')
        messagegroup_type = messagegroups_field['type']['values']
        messages_field = next(f for f in messagegroup_type['fields'] if f['name'] == 'messages')
        message_type = messages_field['type']['values']
        dataschema_field = next((f for f in message_type['fields'] if f['name'] == 'dataschema'), None)
        
        if dataschema_field:
            # Should be a reference to GenericRecord, not an inline definition
            field_type = dataschema_field['type']
            assert field_type == 'io.xregistry.GenericRecord', \
                "'any' type should map to GenericRecord reference"

    # Tests matching Makefile schema generation commands
    def test_makefile_schema_json_schema_with_schema_id(self, schema_model, tools_dir):
        """Test schema model JSON Schema generation with schema-id (matches Makefile)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                ['python', 'schema-generator.py', '--type', 'json-schema',
                 '--schema-id', 'https://xregistry.io/xreg/xregistryspecs/schema-v1/schemas/document-schema.json',
                 '--output', tmp_path, str(schema_model)],
                cwd=str(tools_dir),
                capture_output=True,
                text=True,
                timeout=30
            )

            assert result.returncode == 0, f"Schema generation failed: {result.stderr}"

            with open(tmp_path, 'r', encoding='utf-8') as f:
                schema_data = json.load(f)

            # Validate it's valid JSON Schema
            jsonschema.Draft7Validator.check_schema(schema_data)
            
            # Check that schema-id is set correctly
            assert schema_data.get('$id') == 'https://xregistry.io/xreg/xregistryspecs/schema-v1/schemas/document-schema.json'
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_makefile_schema_avro_schema(self, schema_model, tools_dir):
        """Test schema model Avro schema generation (matches Makefile)."""
        schema_data = self.generate_schema(schema_model, 'avro-schema', tools_dir)
        # Validate with Avro library
        avro.schema.parse(json.dumps(schema_data))

    def test_makefile_schema_openapi(self, schema_model, tools_dir):
        """Test schema model OpenAPI generation (matches Makefile)."""
        schema_data = self.generate_schema(schema_model, 'openapi', tools_dir)
        self.assert_published_openapi(schema_data, schema_model.parent)
        # Validate with OpenAPI spec validator
        validate_spec(schema_data)
        # Check nested structure in components.schemas
        if 'components' in schema_data and 'schemas' in schema_data['components']:
            schemas = schema_data['components']['schemas']
            # Check for nested group structures
            nested_groups = [k for k in schemas.keys() if k.endswith('-schema')]
            if nested_groups:
                for group_key in nested_groups:
                    assert isinstance(schemas[group_key], dict), f"'{group_key}' should be a nested object"

    def test_openapi_document_media_types_follow_hasdocument(
        self, schema_model, tools_dir, tmp_path
    ):
        model = json.loads(schema_model.read_text(encoding='utf-8'))
        group_key, group = next(iter(model['groups'].items()))
        resource_key, resource = next(iter(group['resources'].items()))
        resource['hasdocument'] = True
        group_plural = group.get('plural', group_key)
        resource_plural = resource.get('plural', resource_key)
        resource_path = (
            f"/{group_plural}/{{groupid}}/"
            f"{resource_plural}/{{resourceid}}"
        )
        paths = (
            resource_path,
            f"{resource_path}/versions/{{versionid}}",
        )
        model_path = tmp_path / 'model.json'
        model_path.write_text(json.dumps(model), encoding='utf-8')

        document_openapi = self.generate_schema(model_path, 'openapi', tools_dir)
        for path in paths:
            response = document_openapi['paths'][path]['get']['responses']['200']
            content = response['content']
            assert set(content) == {'application/json', 'application/octet-stream'}
            for name in ('xRegistry-schemaid', 'xRegistry-format'):
                reference = response['headers'][name]['$ref']
                assert resolve_pointer(document_openapi, reference[1:])['schema']['type'] == 'string'

        resource['hasdocument'] = False
        model_path.write_text(json.dumps(model), encoding='utf-8')
        metadata_openapi = self.generate_schema(model_path, 'openapi', tools_dir)
        for path in paths:
            content = metadata_openapi['paths'][path]['get']['responses']['200']['content']
            assert set(content) == {'application/json'}

    def test_openapi_document_headers_share_components(self, schema_model, tools_dir, tmp_path):
        model = json.loads(schema_model.read_text(encoding='utf-8'))
        group = model['groups']['schemagroups']
        schema = group['resources']['schemas']
        schema['attributes'].update({
            'shared': {'type': 'string'},
            'schemaonly': {'type': 'string'},
            'locked': {'type': 'string', 'readonly': True},
        })
        group['resources']['artifacts'] = {
            'singular': 'artifact',
            'attributes': {
                'shared': {'type': 'string'},
                'artifactonly': {'type': 'string'},
            },
        }
        model_path = tmp_path / 'model.json'
        model_path.write_text(json.dumps(model), encoding='utf-8')
        api = self.generate_schema(model_path, 'openapi', tools_dir)
        validate_spec(api)

        schema_path = '/schemagroups/{groupid}/schemas/{resourceid}'
        artifact_path = '/schemagroups/{groupid}/artifacts/{resourceid}'
        schema_get = api['paths'][schema_path]['get']['responses']['200']['headers']
        artifact_get = api['paths'][artifact_path]['get']['responses']['200']['headers']
        version_path = schema_path + '/versions/{versionid}'
        version_get = api['paths'][version_path]['get']['responses']['200']['headers']
        shared_ref = schema_get['xRegistry-shared']['$ref']
        assert shared_ref == artifact_get['xRegistry-shared']['$ref']
        assert shared_ref == version_get['xRegistry-shared']['$ref']
        assert resolve_pointer(api, shared_ref[1:]) == {
            'description': 'The shared attribute.',
            'schema': {'type': 'string'},
        }
        assert 'xRegistry-schemaonly' in schema_get
        assert 'xRegistry-schemaonly' not in artifact_get
        assert 'xRegistry-artifactonly' in artifact_get
        assert 'xRegistry-locked' in schema_get
        assert 'xRegistry-metaurl' in schema_get
        assert 'xRegistry-metaurl' not in version_get

        def request_headers(path, method):
            parameters = api['paths'][path][method]['parameters']
            resolved = [
                resolve_pointer(api, p['$ref'][1:]) if '$ref' in p else p
                for p in parameters
            ]
            return {p['name']: p for p in resolved if p['in'] == 'header'}

        schema_put = request_headers(schema_path, 'put')
        artifact_post = request_headers(artifact_path, 'post')
        assert schema_put['xRegistry-shared'] == artifact_post['xRegistry-shared'] == {
            'name': 'xRegistry-shared',
            'in': 'header',
            'required': False,
            'description': 'The shared attribute.',
            'schema': {'type': 'string'},
        }
        assert 'xRegistry-schemaonly' in schema_put
        assert 'xRegistry-schemaonly' not in artifact_post
        assert 'xRegistry-locked' not in schema_put
        shared_parameter_ref = '#/components/parameters/xRegistry-shared'
        assert {'$ref': shared_parameter_ref} in api['paths'][schema_path]['put']['parameters']
        assert {'$ref': shared_parameter_ref} in api['paths'][artifact_path]['post']['parameters']

    def test_openapi_single_version_paths_preserve_imports_and_media_types(
        self, schema_model, tools_dir, tmp_path
    ):
        model = json.loads(schema_model.read_text(encoding='utf-8'))
        group_plural, group = next(iter(model['groups'].items()))
        resource_plural, resource = next(iter(group['resources'].items()))
        resource['maxversions'] = 1
        model['groups']['mirrors'] = {
            'singular': 'mirror',
            'ximportresources': [f'/{group_plural}/{resource_plural}'],
        }
        paths = (
            f'/{group_plural}/{{groupid}}/{resource_plural}/{{resourceid}}/versions/{{versionid}}',
            f'/mirrors/{{groupid}}/{resource_plural}/{{resourceid}}/versions/{{versionid}}',
        )
        model_path = tmp_path / 'model.json'
        for hasdocument in (True, False):
            resource['hasdocument'] = hasdocument
            model_path.write_text(json.dumps(model), encoding='utf-8')
            openapi = self.generate_schema(model_path, 'openapi', tools_dir)
            for path in paths:
                content = openapi['paths'][path]['get']['responses']['200']['content']
                expected_types = {'application/json'}
                if hasdocument:
                    expected_types.add('application/octet-stream')
                assert set(content) == expected_types
                assert content['application/json']['schema']['$ref'] == (
                    f"#/components/schemas/{resource['singular']}Version"
                )

    def test_makefile_message_json_schema_with_schema_id(self, message_model, tools_dir):
        """Test message model JSON Schema generation with schema-id (matches Makefile)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                ['python', 'schema-generator.py', '--type', 'json-schema',
                 '--schema-id', 'https://xregistry.io/xreg/xregistryspecs/message-v1/schemas/document-schema.json',
                 '--output', tmp_path, str(message_model)],
                cwd=str(tools_dir),
                capture_output=True,
                text=True,
                timeout=30
            )

            assert result.returncode == 0, f"Schema generation failed: {result.stderr}"

            with open(tmp_path, 'r', encoding='utf-8') as f:
                schema_data = json.load(f)

            jsonschema.Draft7Validator.check_schema(schema_data)
            assert schema_data.get('$id') == 'https://xregistry.io/xreg/xregistryspecs/message-v1/schemas/document-schema.json'
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_makefile_message_avro_schema(self, message_model, tools_dir):
        """Test message model Avro schema generation (matches Makefile)."""
        schema_data = self.generate_schema(message_model, 'avro-schema', tools_dir)
        avro.schema.parse(json.dumps(schema_data))

    def test_makefile_message_openapi(self, message_model, tools_dir):
        """Test message model OpenAPI generation (matches Makefile)."""
        schema_data = self.generate_schema(message_model, 'openapi', tools_dir)
        self.assert_published_openapi(schema_data, message_model.parent)
        # Validate with OpenAPI spec validator
        validate_spec(schema_data)
        # Check nested structure
        if 'components' in schema_data and 'schemas' in schema_data['components']:
            schemas = schema_data['components']['schemas']
            nested_groups = [k for k in schemas.keys() if k.endswith('-schema')]
            if nested_groups:
                for group_key in nested_groups:
                    assert isinstance(schemas[group_key], dict), f"'{group_key}' should be a nested object"

    def test_makefile_endpoint_json_schema_with_schema_id(self, endpoint_model, tools_dir):
        """Test endpoint model JSON Schema generation with schema-id (matches Makefile)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                ['python', 'schema-generator.py', '--type', 'json-schema',
                 '--schema-id', 'https://xregistry.io/xreg/xregistryspecs/endpoint-v1/schemas/document-schema.json',
                 '--output', tmp_path, str(endpoint_model)],
                cwd=str(tools_dir),
                capture_output=True,
                text=True,
                timeout=30
            )

            assert result.returncode == 0, f"Schema generation failed: {result.stderr}"

            with open(tmp_path, 'r', encoding='utf-8') as f:
                schema_data = json.load(f)

            jsonschema.Draft7Validator.check_schema(schema_data)
            assert schema_data.get('$id') == 'https://xregistry.io/xreg/xregistryspecs/endpoint-v1/schemas/document-schema.json'
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_makefile_endpoint_avro_schema(self, endpoint_model, tools_dir):
        """Test endpoint model Avro schema generation (matches Makefile)."""
        schema_data = self.generate_schema(endpoint_model, 'avro-schema', tools_dir)
        avro.schema.parse(json.dumps(schema_data))

    def test_makefile_endpoint_openapi(self, endpoint_model, tools_dir):
        """Test endpoint model OpenAPI generation (matches Makefile)."""
        schema_data = self.generate_schema(endpoint_model, 'openapi', tools_dir)
        self.assert_published_openapi(schema_data, endpoint_model.parent)
        # Validate with OpenAPI spec validator
        validate_spec(schema_data)
        # Check nested structure
        if 'components' in schema_data and 'schemas' in schema_data['components']:
            schemas = schema_data['components']['schemas']
            nested_groups = [k for k in schemas.keys() if k.endswith('-schema')]
            if nested_groups:
                for group_key in nested_groups:
                    assert isinstance(schemas[group_key], dict), f"'{group_key}' should be a nested object"

    def test_makefile_cloudevents_multi_model_json_schema(self, endpoint_model, message_model, schema_model, tools_dir):
        """Test CloudEvents JSON Schema generation with multiple models (matches Makefile)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                ['python', 'schema-generator.py', '--type', 'json-schema',
                 '--schema-id', 'https://xregistry.io/xreg/xregistryspecs/cloudevents-v1/schemas/document-schema.json',
                 '--output', tmp_path, str(endpoint_model), str(message_model), str(schema_model)],
                cwd=str(tools_dir),
                capture_output=True,
                text=True,
                timeout=30
            )

            assert result.returncode == 0, f"Schema generation failed: {result.stderr}"

            with open(tmp_path, 'r', encoding='utf-8') as f:
                schema_data = json.load(f)

            jsonschema.Draft7Validator.check_schema(schema_data)
            assert schema_data.get('$id') == 'https://xregistry.io/xreg/xregistryspecs/cloudevents-v1/schemas/document-schema.json'
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_makefile_cloudevents_multi_model_avro_schema(self, endpoint_model, message_model, schema_model, tools_dir):
        """Test CloudEvents Avro schema generation with multiple models (matches Makefile)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                ['python', 'schema-generator.py', '--type', 'avro-schema',
                 '--output', tmp_path, str(endpoint_model), str(message_model), str(schema_model)],
                cwd=str(tools_dir),
                capture_output=True,
                text=True,
                timeout=30
            )

            assert result.returncode == 0, f"Schema generation failed: {result.stderr}"

            with open(tmp_path, 'r', encoding='utf-8') as f:
                schema_data = json.load(f)

            # Validate with Avro library
            avro.schema.parse(json.dumps(schema_data))
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_makefile_cloudevents_multi_model_openapi(self, endpoint_model, message_model, schema_model, tools_dir):
        """Test CloudEvents OpenAPI generation with multiple models (matches Makefile)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                ['python', 'schema-generator.py', '--type', 'openapi',
                 '--output', tmp_path, str(endpoint_model), str(message_model), str(schema_model)],
                cwd=str(tools_dir),
                capture_output=True,
                text=True,
                timeout=30
            )

            assert result.returncode == 0, f"Schema generation failed: {result.stderr}"

            with open(tmp_path, 'r', encoding='utf-8') as f:
                schema_data = json.load(f)

            self.assert_published_openapi(schema_data, tools_dir.parent / 'cloudevents')
            # Validate with OpenAPI spec validator
            validate_spec(schema_data)
            for path in (
                '/messagegroups/{groupid}/messages/{resourceid}',
                '/endpoints/{groupid}/messages/{resourceid}',
            ):
                operation = schema_data['paths'][path]
                assert operation['get']['responses']['200']['content']['application/json']['schema'] == {
                    '$ref': '#/components/schemas/message'
                }
                assert 'xRegistry-messageid' not in operation['get']['responses']['200'].get('headers', {})
                assert {'$ref': '#/components/parameters/xRegistry-messageid'} not in operation['put']['parameters']
            # For OpenAPI, check that we have flat keys (no nested structure)
            if 'components' in schema_data and 'schemas' in schema_data['components']:
                schemas = schema_data['components']['schemas']
                # OpenAPI should have flat keys like 'message', 'messagegroup', 'endpoint', 'schema'
                # Should NOT have nested keys like 'messagegroup-schema'
                flat_keys = [k for k in schemas.keys() if not k.endswith('-schema')]
                nested_keys = [k for k in schemas.keys() if k.endswith('-schema')]
                assert len(flat_keys) > 0, "Should have flat schema keys for OpenAPI"
                assert len(nested_keys) == 0, "Should NOT have nested -schema keys in OpenAPI"
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


    def assert_published_openapi(self, schema, domain_dir):
        path = domain_dir / 'schemas' / 'openapi.json'
        assert schema == json.loads(path.read_text(encoding='utf-8')), f'{path} is out of date'

    @pytest.fixture
    def model_validation(self, tools_dir):
        spec = importlib.util.spec_from_file_location(
            'validate_models', tools_dir / 'validate-models.py'
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        schema_path = tools_dir.parent / 'core' / 'model.schema.json'
        return module, json.loads(schema_path.read_text(encoding='utf-8'))

    @pytest.mark.parametrize(('attribute', 'stage'), [
        ({'type': 'unknown-type'}, 'source'),
        ({'required': True}, 'expanded'),
    ])
    def test_model_validation_reports_the_failed_structural_stage(
        self, model_validation, tmp_path, attribute, stage
    ):
        validator, schema = model_validation
        model_path = tmp_path / 'model.json'
        model_path.write_text(json.dumps({'attributes': {'payload': attribute}}), encoding='utf-8')

        report = validator.validate_model(model_path, schema)

        failed_stage = validator.SOURCE_STAGE if stage == 'source' else validator.EXPANDED_STAGE
        expected_stages = [validator.SOURCE_STAGE]
        if stage == 'expanded':
            expected_stages.append(validator.EXPANDED_STAGE)
        assert report.stages == expected_stages
        assert report.errors
        assert all(error.startswith(f'[{failed_stage}]') for error in report.errors)

    def test_ordered_includes_use_the_declaring_document_and_local_precedence(
        self, model_validation, tmp_path
    ):
        validator, schema = model_validation
        documents = {
            'model.json': {'attributes': {
                '$includes': ['first.json', 'nested/second.json'],
                'label': {'type': 'boolean'},
            }},
            'first.json': {'level': {'type': 'integer'}, 'label': {'type': 'integer'}},
            'nested/second.json': {
                '$include': 'attribute-types.json#/overrides',
                'label': {'type': 'string'},
            },
            'nested/attribute-types.json': {'overrides': {
                'level': {'type': 'string'}, 'mode': {'type': 'string'},
            }},
        }
        for name, document in documents.items():
            path = tmp_path / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(document), encoding='utf-8')

        source = documents['model.json']
        model_path = tmp_path / 'model.json'
        assert validator.validate_model(model_path, schema).errors == []
        assert validator.expand_model(model_path, source)['attributes'] == {
            'level': {'type': 'integer'}, 'label': {'type': 'boolean'},
            'mode': {'type': 'string'},
        }

    @pytest.mark.parametrize('dialect', ['json-schema', 'openapi'])
    def test_ifvalues_match_whole_selectors_case_insensitively(self, tools_dir, tmp_path, dialect):
        model_path = tmp_path / 'model.json'
        model_path.write_text(json.dumps({'groups': {'catalogs': {
            'singular': 'catalog',
            'attributes': {'protocol': {'type': 'string', 'ifvalues': {
                'HTTP': {'siblingattributes': {'options': {'type': 'uinteger'}}},
            }}},
        }}}), encoding='utf-8')
        document = self.generate_schema(model_path, dialect, tools_dir)
        if dialect == 'openapi':
            validator = OAS30Validator({**document, '$ref': '#/components/schemas/catalog'})
        else:
            validator = jsonschema.Draft7Validator({
                **document, '$ref': '#/definitions/catalog-schema/catalog',
            })

        validator.validate({'protocol': 'hTtP', 'options': 1})
        validator.validate({'protocol': 'HTTP/1.1'})
        assert not validator.is_valid({'protocol': 'hTtP', 'options': -1})
        assert not validator.is_valid({'protocol': 'HTTP/1.1', 'options': 1})

    @pytest.mark.parametrize('dialect', ['json-schema', 'openapi'])
    def test_group_constraint_narrows_the_resource_scalar_enum(self, tools_dir, tmp_path, dialect):
        model_path = tmp_path / 'model.json'
        model_path.write_text(json.dumps({'groups': {'catalogs': {
            'singular': 'catalog',
            'constraints': {'entries.level': {'enum': [1, 2]}},
            'resources': {'entries': {
                'singular': 'entry', 'hasdocument': False,
                'attributes': {'level': {'type': 'uinteger', 'enum': [0, 1, 2]}},
            }},
        }}}), encoding='utf-8')
        document = self.generate_schema(model_path, dialect, tools_dir)
        if dialect == 'openapi':
            body = document['paths']['/']['get']['responses']['200']['content']['application/json']['schema']
            validator = OAS30ReadValidator({**body, 'components': document['components']})
        else:
            validator = jsonschema.Draft7Validator(document)
        entry = {'entryid': 'e', 'level': 1, 'versionsurl': 'https://example.com/versions'}
        catalog = {'catalogid': 'c', 'entries': {'e': entry}}
        value = {
            'registryid': 'r', 'specversion': '1.0', 'self': 'https://example.com/',
            'xid': '/', 'epoch': 1, 'createdat': '2026-01-01T00:00:00Z',
            'modifiedat': '2026-01-01T00:00:00Z', 'catalogs': {'c': catalog},
        }

        validator.validate(value)
        entry['level'] = 0
        assert not validator.is_valid(value)

    def test_json_structure_projects_empty_open_and_typed_objects(self, tools_dir, tmp_path):
        model_path = tmp_path / 'model.json'
        model_path.write_text(json.dumps({'groups': {'catalogs': {
            'singular': 'catalog',
            'attributes': {
                'dynamic': {'type': 'object', 'attributes': {'*': {'type': 'any'}}},
                'closed': {'type': 'object'},
                'named': {'type': 'object', 'attributes': {
                    'label': {'type': 'string', 'required': True},
                    '*': {'type': 'string', 'enum': ['one', 'two']},
                }},
            },
        }}}), encoding='utf-8')
        document = self.generate_schema(model_path, 'json-structure', tools_dir)
        properties = document['definitions']['Catalogs']['Catalog']['properties']

        assert properties['dynamic'] == {'type': 'map', 'values': {'type': 'any'}}
        assert properties['closed']['type'] == 'map'
        assert properties['closed']['maxEntries'] == 0
        assert 'JSONStructureValidation' in document['$uses']
        named = properties['named']
        assert named['type'] == 'object'
        assert named['properties']['label'] == {'type': 'string'}
        assert named['required'] == ['label']
        assert named['additionalProperties'] == {'type': 'string', 'enum': ['one', 'two']}

    def test_openapi_registry_and_meta_distinguish_writes_from_responses(self, tools_dir, tmp_path):
        required = {'type': 'string', 'required': True}
        model_path = tmp_path / 'model.json'
        model_path.write_text(json.dumps({
            'attributes': {'tenant': required, 'region': {**required, 'default': 'global'}},
            'groups': {'catalogs': {'singular': 'catalog', 'resources': {
                'entries': {'singular': 'entry', 'metaattributes': {
                    'owner': required, 'policy': {**required, 'default': 'local'},
                }},
            }}},
        }), encoding='utf-8')
        api = self.generate_schema(model_path, 'openapi', tools_dir)
        paths = api['paths']
        meta_path = '/catalogs/{groupid}/entries/{resourceid}/meta'
        meta = paths[meta_path]
        stamp = '2026-01-01T00:00:00Z'
        common = {'epoch': 1, 'createdat': stamp, 'modifiedat': stamp}
        meta_id = '/catalogs/c/entries/e/meta'
        registry_response = {
            **common, 'registryid': 'r', 'specversion': '1.0', 'xid': '/',
            'self': 'https://example.com/', 'tenant': 'team', 'region': 'global',
        }
        meta_response = {
            **common, 'entryid': 'e', 'readonly': False, 'xid': meta_id,
            'self': f'https://example.com{meta_id}', 'owner': 'team', 'policy': 'local',
            'defaultversionid': 'v1', 'defaultversionsticky': False,
            'defaultversionurl': 'https://example.com/catalogs/c/entries/e/versions/v1',
        }

        for operations, field, defaulted, complete in (
            (paths['/'], 'tenant', 'region', registry_response),
            (meta, 'owner', 'policy', meta_response),
        ):
            put = operations['put']['requestBody']['content']['application/json']['schema']
            patch = operations['patch']['requestBody']['content']['application/json']['schema']
            get = operations['get']['responses']['200']['content']['application/json']['schema']
            components = {'components': api['components']}
            put_validator = OAS30WriteValidator({**put, **components})
            patch_validator = OAS30WriteValidator({**patch, **components})
            put_validator.validate({field: 'team'})
            assert not put_validator.is_valid({})
            patch_validator.validate({})
            response_validator = OAS30ReadValidator({**get, **components})
            response_validator.validate(complete)
            incomplete = {name: value for name, value in complete.items() if name != defaulted}
            assert not response_validator.is_valid(incomplete)

        meta_schema = meta['get']['responses']['200']['content']['application/json']['schema']
        nested_meta = api['components']['schemas']['entry']['properties']['meta']
        assert nested_meta['allOf'][0] == meta_schema
        assert 'entryid' in resolve_pointer(api, meta_schema['$ref'][1:])['properties']

    def test_openapi_details_suffix_selects_metadata_for_document_writes(
        self, schema_model, tools_dir
    ):
        api = self.generate_schema(schema_model, 'openapi', tools_dir)
        path = '/schemagroups/{groupid}/schemas/{resourceid}'
        for method, metadata_type in (
            ('put', 'schemaWriteInput'), ('post', 'schemaResourceVersionWriteInput')
        ):
            document = api['paths'][path][method]['requestBody']['content']
            details = api['paths'][path + '$details'][method]['requestBody']['content']
            assert 'application/octet-stream' in document
            assert document['application/json']['schema'].get('$ref') is None
            assert set(details) == {'application/json'}
            assert details['application/json']['schema']['$ref'] == f'#/components/schemas/{metadata_type}'

    def test_openapi_administration_methods_and_write_guards(self, schema_model, tools_dir):
        api = self.generate_schema(schema_model, 'openapi', tools_dir)
        methods = {'get', 'put', 'patch', 'post', 'delete'}
        for path, expected in {
            '/capabilities': {'get', 'put', 'patch'},
            '/capabilitiesoffered': {'get'},
            '/model': {'get'},
            '/modelsource': {'get', 'put'},
            '/export': {'get'},
        }.items():
            assert set(api['paths'][path]) & methods == expected

        for item in api['paths'].values():
            for method in set(item) & methods:
                parameters = [*item.get('parameters', []), *item[method].get('parameters', [])]
                names = [
                    (resolve_pointer(api, ref['$ref'][1:]) if '$ref' in ref else ref)['name']
                    for ref in parameters
                ]
                assert names.count('ignore') == (0 if method == 'get' else 1)
                assert names.count('epoch') == (1 if method == 'delete' else 0)

    def test_openapi_problem_details_accepts_an_omitted_instance(self, schema_model, tools_dir):
        api = self.generate_schema(schema_model, 'openapi', tools_dir)
        checker = jsonschema.FormatChecker()
        assert 'uri' in checker.checkers, 'Install the format dependencies from tools/requirements.txt'
        validator = jsonschema.Draft7Validator(
            api['components']['schemas']['ProblemDetails'], format_checker=checker,
        )
        problem = {'type': 'https://example.com/problems/bad-request', 'title': 'Invalid input'}
        validator.validate(problem)
        assert not validator.is_valid({'title': problem['title']})
        assert not validator.is_valid({'type': problem['type']})
        assert not validator.is_valid({**problem, 'instance': 'not a URI'})


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
