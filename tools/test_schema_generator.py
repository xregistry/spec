"""
Tests for schema-generator.py to validate JSON Schema and Avro output conformance.
"""
import copy
import io
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

import avro.schema
import avro.io
import avro.errors
import jsonschema
import pytest
from jsonpointer import resolve_pointer
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

    def generate_schema(self, model_path: Path, schema_type: str, tools_dir: Path, *options) -> dict:
        """Generate a schema using schema-generator.py."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                ['python', 'schema-generator.py', '--type', schema_type, str(model_path), '--output', tmp_path, *options],
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

    @pytest.fixture
    def optional_avro_model(self, tmp_path):
        model = {
            "groups": {
                "items": {
                    "singular": "item",
                    "attributes": {
                        "identity": {"type": "uri"},
                        "links": {
                            "type": "map", "required": True,
                            "item": {
                                "type": "object",
                                "attributes": {
                                    "target": {"type": "urlabsolute", "required": True},
                                    "provenance": {"type": "urlabsolute"}
                                }
                            }
                        },
                        "samples": {
                            "type": "array",
                            "item": {
                                "type": "object",
                                "attributes": {
                                    "value": {"type": "integer", "required": True},
                                    "label": {"type": "string"}
                                }
                            }
                        },
                        "choice": {
                            "type": "string",
                            "ifvalues": {
                                "one": {"siblingattributes": {
                                    "left": {"type": "integer", "required": True}
                                }},
                                "two": {"siblingattributes": {
                                    "right": {"type": "string", "required": True}
                                }}
                            }
                        },
                        "*": {"type": "any"}
                    }
                }
            }
        }
        path = tmp_path / "optional-model.json"
        path.write_text(json.dumps(model), encoding="utf-8")
        return path

    @staticmethod
    def avro_roundtrip(schema, datum, reader_schema=None):
        buffer = io.BytesIO()
        avro.io.DatumWriter(schema).write(datum, avro.io.BinaryEncoder(buffer))
        buffer.seek(0)
        return avro.io.DatumReader(schema, reader_schema).read(
            avro.io.BinaryDecoder(buffer)
        )

    @pytest.mark.parametrize("explicit_null", [False, True], ids=["omitted", "null"])
    def test_avro_nullable_optionals_encode_absent_values(
        self, optional_avro_model, tools_dir, explicit_null
    ):
        generated = self.generate_schema(
            optional_avro_model, "avro-schema", tools_dir, "--avro-nullable-optionals"
        )
        schema = avro.schema.parse(json.dumps(generated))
        item = schema.fields_dict["items"].type.values
        datum = {
            "itemid": "a", "self": "https://example.com/a", "xid": "/items/a",
            "labels": {}, "links": {"a": {"target": "https://example.com/target"}}
        }
        if explicit_null:
            datum.update(identity=None, samples=None, choice=None, Extensions=None)
            datum["links"]["a"]["provenance"] = None
        result = self.avro_roundtrip(item, datum)
        assert result["identity"] is None
        assert result["links"]["a"]["provenance"] is None
        assert result["samples"] is None
        assert result["choice"] is None
        assert result["Extensions"] is None
        assert item.fields_dict["identity"].default is None
        assert item.fields_dict["links"].type.values.fields_dict["provenance"].default is None

        legacy = avro.schema.parse(json.dumps(
            self.generate_schema(optional_avro_model, "avro-schema", tools_dir)
        )).fields_dict["items"].type.values
        with pytest.raises(avro.errors.AvroTypeException):
            self.avro_roundtrip(legacy, datum)

    def test_avro_nullable_optionals_preserve_complex_types(
        self, optional_avro_model, tools_dir
    ):
        generated = self.generate_schema(
            optional_avro_model, "avro-schema", tools_dir, "--avro-nullable-optionals"
        )
        item = avro.schema.parse(json.dumps(generated)).fields_dict["items"].type.values
        datum = {
            "itemid": "a", "self": "https://example.com/a", "xid": "/items/a",
            "labels": {}, "identity": "urn:example:a",
            "links": {"a": {
                "target": "https://example.com/target",
                "provenance": "https://example.com/plan"
            }},
            "samples": [{"value": 42, "label": "reading"}],
            "choice": {"left": 7},
            "Extensions": {"custom": {"object": {"key": "value"}}}
        }
        result = self.avro_roundtrip(item, datum)
        for name in ("identity", "links", "samples", "choice", "Extensions"):
            assert result[name] == datum[name]
        choice_types = item.fields_dict["choice"].type.schemas
        assert [branch.type for branch in choice_types] == ["null", "record", "record"]
        assert choice_types[1].fullname != choice_types[2].fullname
        datum["choice"] = {"right": "other"}
        assert self.avro_roundtrip(item, datum)["choice"] == {"right": "other"}

    @pytest.mark.parametrize("missing", [False, True], ids=["null", "omitted"])
    @pytest.mark.parametrize("field", ["links", "target"])
    def test_avro_nullable_optionals_keep_required_fields(
        self, optional_avro_model, tools_dir, field, missing
    ):
        generated = self.generate_schema(
            optional_avro_model, "avro-schema", tools_dir, "--avro-nullable-optionals"
        )
        item = avro.schema.parse(json.dumps(generated)).fields_dict["items"].type.values
        datum = {
            "itemid": "a", "self": "https://example.com/a", "xid": "/items/a",
            "labels": {}, "links": {"a": {"target": "https://example.com/target"}}
        }
        owner = datum if field == "links" else datum["links"]["a"]
        if missing:
            del owner[field]
        else:
            owner[field] = None
        with pytest.raises(avro.errors.AvroTypeException):
            self.avro_roundtrip(item, datum)

    def test_avro_nullable_optionals_preserve_scalar_defaults(self, tools_dir, tmp_path):
        model_path = tmp_path / "defaults.json"
        model_path.write_text(json.dumps({
            "groups": {"items": {"singular": "item", "attributes": {
                "retries": {"type": "integer", "required": True, "default": 0},
                "enabled": {"type": "boolean", "required": True, "default": False},
                "title": {"type": "string", "required": True, "default": "configured"},
                "note": {"type": "string"}
            }}}
        }), encoding="utf-8")
        generated = self.generate_schema(
            model_path, "avro-schema", tools_dir, "--avro-nullable-optionals"
        )
        reader = avro.schema.parse(json.dumps(generated))
        writer_data = copy.deepcopy(generated)
        fields = writer_data["fields"][0]["type"]["values"]["fields"]
        fields[:] = [f for f in fields if f["name"] not in ("retries", "enabled", "title", "note")]
        writer = avro.schema.parse(json.dumps(writer_data))
        datum = {"items": {"a": {
            "itemid": "a", "self": "https://example.com/a", "xid": "/items/a", "labels": {}
        }}}
        result = self.avro_roundtrip(writer, datum, reader)["items"]["a"]
        assert result["retries"] == 0
        assert result["enabled"] is False
        assert result["title"] == "configured"
        assert result["note"] is None
        item = reader.fields_dict["items"].type.values
        assert item.fields_dict["retries"].type.type == "int"
        assert item.fields_dict["enabled"].type.type == "boolean"
        assert item.fields_dict["title"].type.type == "string"
        self.avro_roundtrip(reader, {"items": {"a": result}})
        result["title"] = None
        with pytest.raises(avro.errors.AvroTypeException):
            self.avro_roundtrip(reader, {"items": {"a": result}})

    @pytest.mark.parametrize("domain", ["schema", "message", "endpoint", "cloudevents"])
    def test_avro_default_generation_preserves_published_bytes(self, tools_dir, tmp_path, domain):
        root = tools_dir.parent
        models = ["endpoint", "message", "schema"] if domain == "cloudevents" else [domain]
        output = tmp_path / "document-schema.avsc"
        result = subprocess.run(
            ["python", str(tools_dir / "schema-generator.py"), "--type", "avro-schema",
             "--output", str(output), *[str(root / model / "model.json") for model in models]],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0, result.stderr
        # Text-mode CLI output uses the host newline; Git stores LF on every host.
        actual = output.read_bytes().replace(b"\r\n", b"\n")
        published = (root / domain / "schemas" / output.name).read_bytes().replace(b"\r\n", b"\n")
        assert actual == published

    @pytest.mark.parametrize("schema_type", ["json-schema", "json-structure", "openapi"])
    def test_avro_nullable_optionals_reject_other_formats(
        self, schema_model, tools_dir, tmp_path, schema_type
    ):
        output = tmp_path / "unexpected.json"
        result = subprocess.run(
            ["python", str(tools_dir / "schema-generator.py"), "--type", schema_type,
             "--avro-nullable-optionals", "--output", str(output), str(schema_model)],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 2
        assert "--avro-nullable-optionals requires --type avro-schema" in result.stderr
        assert not output.exists()

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
            for path in (
                '/messagegroups/{groupid}/messages/{resourceid}',
                '/endpoints/{groupid}/messages/{resourceid}',
            ):
                operation = schema_data['paths'][path]
                assert operation['get']['responses']['200']['headers']['xRegistry-messageid'] == {
                    '$ref': '#/components/headers/xRegistry-messageid'
                }
                assert {'$ref': '#/components/parameters/xRegistry-messageid'} in operation['put']['parameters']
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
