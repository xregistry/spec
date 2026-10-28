"""
Tests for schema-generator.py to validate JSON Schema and Avro output conformance.
"""
import copy
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

import avro.schema
import jsonschema
import pytest
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
        schema_version = schema_data['definitions']['Schemagroups']['SchemaVersion']
        assert schema_version['properties']['format']['type'] == 'string'

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

            # Validate with OpenAPI spec validator
            validate_spec(schema_data)
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


@pytest.fixture(scope='module')
def model_validator():
    schema_path = Path(__file__).parent.parent / 'core' / 'model.schema.json'
    schema = json.loads(schema_path.read_text(encoding='utf-8'))
    jsonschema.Draft7Validator.check_schema(schema)
    return jsonschema.Draft7Validator(schema)


class TestModelSchemaValueSets:
    @pytest.fixture(params=[
        'registry', 'group', 'version', 'resource', 'meta', 'object',
        'array-object', 'map-object', 'conditional', 'wildcard'
    ])
    def attribute_location(self, request):
        model = {}
        path = ['attributes', 'values']
        if request.param in ('group', 'version', 'resource', 'meta'):
            group = {'singular': 'catalog'}
            model['groups'] = {'catalogs': group}
            path = ['groups', 'catalogs', 'attributes', 'values']
            if request.param != 'group':
                group['resources'] = {'entries': {'singular': 'entry'}}
                aspect = {
                    'version': 'attributes',
                    'resource': 'resourceattributes',
                    'meta': 'metaattributes'
                }[request.param]
                path = ['groups', 'catalogs', 'resources', 'entries', aspect, 'values']
        elif request.param in ('object', 'array-object', 'map-object'):
            parent = {'type': 'object', 'attributes': {}}
            path = ['attributes', 'parent', 'attributes', 'values']
            if request.param != 'object':
                parent = {'type': request.param.split('-')[0], 'item': parent}
                path.insert(2, 'item')
            model['attributes'] = {'parent': parent}
        elif request.param == 'conditional':
            model['attributes'] = {'selector': {
                'type': 'string',
                'ifvalues': {'active': {'siblingattributes': {}}}
            }}
            path = ['attributes', 'selector', 'ifvalues', 'active',
                    'siblingattributes', 'values']
        elif request.param == 'wildcard':
            path = ['attributes', '*']
        return model, path

    def model_with_attribute(self, location, definition):
        template, path = location
        model = copy.deepcopy(template)
        parent = model
        for key in path[:-1]:
            parent = parent.setdefault(key, {})
        parent[path[-1]] = copy.deepcopy(definition)
        return model

    def container_definition(self, kind):
        definition = {'type': kind}
        if kind in ('array', 'map'):
            definition['item'] = {'type': 'string'}
        return definition

    def assert_schema_error(self, validator, model, path, keyword):
        errors = list(validator.iter_errors(model))
        assert errors, model

        def matches(error):
            if list(error.absolute_path) == path and error.validator == keyword:
                return True
            return any(matches(child) for child in error.context)

        assert any(matches(error) for error in errors), [
            error.message for error in errors
        ]

    @pytest.mark.parametrize('value_set', [[], ['consumer']], ids=['empty', 'nonempty'])
    @pytest.mark.parametrize('strict', [{}, {'strict': False}, {'strict': True}],
                             ids=['default', 'advisory', 'strict'])
    def test_array_attribute_rejects_enum_at_attribute_level(
        self, model_validator, attribute_location, value_set, strict
    ):
        definition = {'type': 'array', 'item': {'type': 'string'}, **strict}
        model_validator.validate(self.model_with_attribute(attribute_location, definition))
        definition['enum'] = value_set
        self.assert_schema_error(
            model_validator, self.model_with_attribute(attribute_location, definition),
            attribute_location[1] + ['enum'], 'not'
        )

    @pytest.mark.parametrize('kind', ['map', 'object', 'any'])
    def test_other_non_scalar_attributes_reject_enum(
        self, model_validator, attribute_location, kind
    ):
        definition = self.container_definition(kind)
        definition['strict'] = False
        model_validator.validate(self.model_with_attribute(attribute_location, definition))
        definition['enum'] = ['consumer']
        self.assert_schema_error(
            model_validator, self.model_with_attribute(attribute_location, definition),
            attribute_location[1] + ['enum'], 'not'
        )

    @pytest.mark.parametrize('kind,value', [
        ('string', 'consumer'), ('integer', 1), ('boolean', True)
    ])
    def test_scalar_attribute_enum_remains_admissible(
        self, model_validator, attribute_location, kind, value
    ):
        definition = {'type': kind, 'enum': [value]}
        model_validator.validate(self.model_with_attribute(attribute_location, definition))

    @pytest.mark.parametrize('strict', [False, True])
    def test_empty_scalar_attribute_enum_remains_admissible(
        self, model_validator, attribute_location, strict
    ):
        definition = {'type': 'string', 'enum': [], 'strict': strict}
        model_validator.validate(self.model_with_attribute(attribute_location, definition))

    @pytest.mark.parametrize('kind,value', [
        ('string', 'consumer'), ('boolean', True), ('integer', -1),
        ('uinteger', 0), ('decimal', 1.5), ('uri', 'urn:example:role'),
        ('timestamp', '2026-10-12T10:00:00Z'), ('binary', 'YQ==')
    ])
    @pytest.mark.parametrize('owner', ['array', 'map'])
    def test_scalar_item_enum_is_admitted(
        self, model_validator, attribute_location, kind, value, owner
    ):
        definition = {'type': owner, 'item': {'type': kind, 'enum': [value]}}
        model_validator.validate(self.model_with_attribute(attribute_location, definition))

    @pytest.mark.parametrize('kind', ['array', 'map', 'object', 'any'])
    @pytest.mark.parametrize('owner', ['array', 'map'])
    def test_non_scalar_item_rejects_enum(
        self, model_validator, attribute_location, kind, owner
    ):
        item = self.container_definition(kind)
        item['strict'] = False
        definition = {'type': owner, 'item': item}
        model_validator.validate(self.model_with_attribute(attribute_location, definition))
        item['enum'] = []
        self.assert_schema_error(
            model_validator, self.model_with_attribute(attribute_location, definition),
            attribute_location[1] + ['item', 'enum'], 'not'
        )

    @pytest.mark.parametrize('aspect,value', [
        ('enum', None), ('enum', 'consumer'), ('enum', 1),
        ('enum', True), ('enum', {}),
        ('strict', None), ('strict', 'false'), ('strict', 0),
        ('strict', []), ('strict', {})
    ])
    @pytest.mark.parametrize('placement', ['attribute', 'item'])
    def test_malformed_value_set_aspects_are_rejected(
        self, model_validator, attribute_location, aspect, value, placement
    ):
        scalar = {'type': 'string'}
        definition = scalar if placement == 'attribute' else {'type': 'array', 'item': scalar}
        model_validator.validate(self.model_with_attribute(attribute_location, definition))
        scalar[aspect] = value
        path = attribute_location[1] + ([] if placement == 'attribute' else ['item'])
        self.assert_schema_error(
            model_validator, self.model_with_attribute(attribute_location, definition),
            path + [aspect], 'type'
        )

    @pytest.mark.parametrize('kind', ['array', 'map'])
    @pytest.mark.parametrize('placement', ['attribute', 'item'])
    def test_container_definition_requires_item(
        self, model_validator, attribute_location, kind, placement
    ):
        container = self.container_definition(kind)
        definition = container if placement == 'attribute' else {'type': 'array', 'item': container}
        model_validator.validate(self.model_with_attribute(attribute_location, definition))
        del container['item']
        path = attribute_location[1] + ([] if placement == 'attribute' else ['item'])
        self.assert_schema_error(
            model_validator, self.model_with_attribute(attribute_location, definition),
            path, 'required'
        )

    @pytest.mark.parametrize('item,tail,keyword', [
        (None, [], 'type'), ('string', [], 'type'), ([], [], 'type'),
        ({}, [], 'required'), ({'type': 'unknown'}, ['type'], 'enum'),
        ({'type': 1}, ['type'], 'type'),
        ({'type': 'string', 'unexpected': True}, [], 'additionalProperties')
    ])
    def test_malformed_item_definition_is_rejected(
        self, model_validator, attribute_location, item, tail, keyword
    ):
        definition = {'type': 'array', 'item': {'type': 'string'}}
        model_validator.validate(self.model_with_attribute(attribute_location, definition))
        definition['item'] = item
        self.assert_schema_error(
            model_validator, self.model_with_attribute(attribute_location, definition),
            attribute_location[1] + ['item'] + tail, keyword
        )

    @pytest.mark.parametrize('kind', ['string', 'array', 'map', 'object', 'any'])
    @pytest.mark.parametrize('strict', [False, True])
    @pytest.mark.parametrize('placement', ['attribute', 'item'])
    def test_strict_without_enum_remains_admissible(
        self, model_validator, attribute_location, kind, strict, placement
    ):
        container = self.container_definition(kind)
        container['strict'] = strict
        definition = container if placement == 'attribute' else {'type': 'array', 'item': container}
        model_validator.validate(self.model_with_attribute(attribute_location, definition))

    @pytest.mark.parametrize('owner,inner', [('array', 'map'), ('map', 'array')])
    def test_nested_scalar_item_enum_remains_admissible(
        self, model_validator, attribute_location, owner, inner
    ):
        definition = {'type': owner, 'item': {
            'type': inner, 'item': {'type': 'string', 'enum': [], 'strict': False}
        }}
        model_validator.validate(self.model_with_attribute(attribute_location, definition))

    @pytest.mark.parametrize('kind', ['object', 'array', 'map'])
    def test_wildcard_object_attributes_reuse_value_set_rules(self, model_validator, kind):
        child = {'type': 'array', 'item': {'type': 'string', 'enum': ['consumer']}}
        wildcard = {'type': 'object', 'attributes': {'values': child}}
        path = ['attributes', '*']
        if kind != 'object':
            wildcard = {'type': kind, 'item': wildcard}
            path.append('item')
        model = {'attributes': {'*': wildcard}}
        model_validator.validate(model)
        child['enum'] = ['consumer']
        self.assert_schema_error(
            model_validator, model, path + ['attributes', 'values', 'enum'], 'not'
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
