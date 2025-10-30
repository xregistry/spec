"""
Tests for schema-generator.py to validate JSON Schema and Avro output conformance.
"""
import json
import os
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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
