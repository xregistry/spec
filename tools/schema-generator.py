import argparse
import copy
import json
import os
import re
from jsonpointer import resolve_pointer

avro_generic_record_name = "GenericRecord"
avro_generic_record_qualified_name = "io.xregistry.GenericRecord"
avro_generic_record = {
  "type": "record",
  "name": avro_generic_record_name,
  "fields": [
    {
      "name": "object",
      "type": {
        "type": "map",
        "values": [
          "null",
          "boolean",
          "int",
          "long",
          "float",
          "double",
          "bytes",
          "string",
          {
            "type": "array",
            "items": [
              "null",
              "boolean",
              "int",
              "long",
              "float",
              "double",
              "bytes",
              "string",
              avro_generic_record_qualified_name
            ]
          },
          avro_generic_record_qualified_name
        ]
      }
    }
  ]
}


avro_type_mapping = {
    "string": {"type": "string"},
    "object": {"type": "record"},
    "map": {"type": { "type": "map"}},
    "uri": {"type": "string"},
    "url": {"type": "string"},
    "datetime": {"type": {"type":"int", "logicalType": "time-millis"}},
    "integer": {"type": "int"},
    "uinteger": {"type": "int"},
    "boolean": {"type": "boolean"},
    "array": {"type":{"type": "array", "items": ""}},
    "uritemplate": {"type": "string"},
    "binary": {"type": "bytes"},
    "timestamp": {"type": {"type":"int", "logicalType": "timestamp-millis"}},
    "any": {"type": avro_generic_record_qualified_name},
    "var": {"type": avro_generic_record_qualified_name},
    "xid": {"type": "string"}
}

json_type_mapping = {
    "string": {"type": "string"},
    "object": {"type": "object"},
    "map": {"type": "object"},
    "uri": {"type": "string", "format": "uri"},
    "url": {"type": "string", "format": "uri"},
    "xid": {"type": "string", "format": "uri"},
    "datetime": {"type": "string", "format": "date-time"},
    "integer": {"type": "integer"},
    "uinteger": {"type": "integer", "minimum": 0},
    "boolean": {"type": "boolean"},
    "array": {"type": "array"},
    "uritemplate": {"type": "string", "format": "uri-template"},
    "binary": {"type": "string", "format": "base64"},
    "timestamp": {"type": "string", "format": "date-time"},
    "any": {"type": "object"},
    "var": {"type": "object"}
}

json_common_attributes = {
    "name": {"type": "string", "description": "Name of the object"},
    "epoch": {"type": "integer", "description": "Epoch time of the object creation"},
    "self": {"type": "string", "format": "uri", "description": "URL of the object"},
    "xid": {"type": "string", "format": "xid", "description": "Relative URL of the object"},
    "description": {"type": "string", "description": "Description of the object"},
    "documentation": {"type": "string", "format": "uri", "description": "URI of the documentation of the object"},
    "labels": {"type": "object", "description": "Labels for the object"},
    "createdat": {"type": "string", "format": "date-time", "description": "Time of the object creation"},
    "modifiedat": {"type": "string", "format": "date-time", "description": "Time of the object modification"}
}

avro_common_attributes = [
    {"name": "name", "type": ["string", "null"], "doc": "Name of the object"},
    {"name": "epoch", "type": ["int", "null"], "doc": "Epoch time of the object creation"},
    {"name": "self", "type": "string", "doc": "URL of the object"},
    {"name": "xid", "type": "string", "doc": "XID of the object"},
    {"name": "description", "type": ["string", "null"], "doc": "Description of the object"},
    {"name": "documentation", "type": ["string", "null"], "doc": "URI of the documentation of the object"},
    {"name": "labels", "type": { "type": "map", "values": ["string", "null"]} , "doc": "Labels for the object"},
    {"name": "createdat", "type": [{"type":"int", "logicalType": "time-millis"}, "null"], "doc": "Time of the object creation"},
    {"name": "modifiedat", "type": [{"type":"int", "logicalType": "time-millis"},"null"], "doc": "Time of the object modification"}
]


def pascal(string):
    if not string or len(string) == 0:
        return string
    words = []
    if '_' in string:
        # snake_case
        words = re.split(r'_', string)
    elif '-' in string:
        # dash-case
        words = re.split(r'-', string)
    elif string[0].isupper():
        # PascalCase
        words = re.findall(r'[A-Z][a-z0-9_]*\.?', string)
    else:
        # camelCase
        words = re.findall(r'[a-z]+\.?|[A-Z][a-z0-9_]*\.?', string)
    result = ''.join(word.capitalize() for word in words)
    return result

def camel(string):
    pascalString = pascal(string)
    return pascalString[0:1].lower() + pascalString[1:]


def generate_openapi(model_definition):

    # now recursively find all $ref attributes in the template and replace them with references to the appropriate schema
    def replace_refs(schema_fragment: dict, expression: str, reference: str):
        for k,v in schema_fragment.items():
            if k == "$ref":
                if expression in v:
                    schema_fragment[k] = v.replace(expression, reference)
            if isinstance(v, dict):
                replace_refs(v, expression, reference)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        replace_refs(item, expression, reference)

    def replace_ops(schema_fragment: dict, expression: str, reference: str):
        for k,v in schema_fragment.items():
            if k == "operationId":
                if v.find(expression) != -1:
                    schema_fragment[k] = v.replace(expression, reference)
            if isinstance(v, dict):
                replace_ops(v, expression, reference)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        replace_ops(item, expression, reference)

    try:
        template_file_name = os.path.join(os.path.dirname(__file__), '..', 'core', 'templates', 'xregistry_openapi_template.json')
        with open(template_file_name, encoding='utf-8') as file:
            openapi = json.load(file)
        json_schema = generate_json_schema(model_definition, True)
        # merge JSON schema with template
        for schema_name, schema in json_schema["components"]["schemas"].items():
            openapi["components"]["schemas"][schema_name] = schema
        # do the fixups

        path = "/"
        root_template = openapi["paths"][path]
        replace_refs(root_template, "{%-documentTypeReference-%}", f"#/components/schemas/document")

        path = "/{%-groupNamePlural-%}"
        path_template = openapi["paths"][path]
        for _, group in model_definition.get("groups", {}).items():
            path_template_copy = copy.deepcopy(path_template)
            replace_refs(path_template_copy, "{%-groupTypeReference-%}", f"#/components/schemas/{group['singular']}")
            replace_ops(path_template_copy, "{%-groupNamePlural-%}", f"{pascal(group['plural'])}")
            openapi["paths"][f"/{group['plural']}"]: path_template_copy
        openapi["paths"].pop(path)

        path = "/{%-groupNamePlural-%}/{groupid}"
        group_template = openapi["paths"][path]
        for _, group in model_definition.get("groups", {}).items():
            group_template_copy = copy.deepcopy(group_template)
            replace_refs(group_template_copy, "{%-groupTypeReference-%}", f"#/components/schemas/{group['singular']}")
            replace_ops(group_template_copy, "{%-groupNameSingular-%}", f"{pascal(group['singular'])}")
            openapi["paths"][f"/{group['plural']}/{{groupid}}"] = group_template_copy

        openapi["paths"].pop(path)
        path = "/{%-groupNamePlural-%}/{groupid}/{%-resourceNamePlural-%}"
        resource_template = openapi["paths"][path]
        for _, group in model_definition.get("groups", {}).items():
            for _, resource in group.get("resources", {}).items():
                resource = resolve_resource(group, resource)
                resource_template_copy = copy.deepcopy(resource_template)
                replace_refs(resource_template_copy, "{%-resourceTypeReference-%}", f"#/components/schemas/{resource['singular']}")
                replace_refs(resource_template_copy, "{%-groupTypeReference-%}", f"#/components/schemas/{group['singular']}")
                replace_ops(resource_template_copy, "{%-resourceNamePlural-%}", f"{pascal(group['singular'])}{pascal(resource['plural'])}")
                openapi["paths"][f"/{group['plural']}/{{groupid}}/{resource['plural']}"]= resource_template_copy
            for ximportresources_xid in group.get("ximportresources", []):
                xid_group_plural, xid_resource_plural = ximportresources_xid.split("/")[1:]
                xid_resource_singular = model_definition["groups"][xid_group_plural]["resources"][xid_resource_plural]["singular"]
                xid_group_singular = model_definition["groups"][xid_group_plural]["singular"]
                resource_template_copy = copy.deepcopy(resource_template)
                replace_refs(resource_template_copy, "{%-resourceTypeReference-%}", f"#/components/schemas/{xid_resource_singular}")
                replace_refs(resource_template_copy, "{%-groupTypeReference-%}", f"#/components/schemas/{xid_group_singular}")
                replace_ops(resource_template_copy, "{%-resourceNamePlural-%}", f"{pascal(group['singular'])}{pascal(xid_resource_plural)}")
                openapi["paths"][f"/{group['plural']}/{{groupid}}/{xid_resource_plural}"]= resource_template_copy

        openapi["paths"].pop(path)
        path = "/{%-groupNamePlural-%}/{groupid}/{%-resourceNamePlural-%}/{resourceid}/meta"
        meta_template = openapi["paths"][path]
        for _, group in model_definition.get("groups", {}).items():
            for _, resource in group.get("resources", {}).items():
                resource = resolve_resource(group, resource)
                meta_template_copy = copy.deepcopy(meta_template)
                replace_refs(meta_template_copy, "{%-resourceTypeReference-%}", f"#/components/schemas/{resource['singular']}")
                replace_refs(meta_template_copy, "{%-groupTypeReference-%}", f"#/components/schemas/{group['singular']}")
                replace_ops(meta_template_copy, "{%-resourceNameSingular-%}", f"{pascal(group['singular'])}{pascal(resource['singular'])}")
                openapi["paths"][f"/{group['plural']}/{{groupid}}/{resource['plural']}/{{resourceid}}/meta"]= meta_template_copy
            for ximportresources_xid in group.get("ximportresources", []):
                xid_group_plural, xid_resource_plural = ximportresources_xid.split("/")[1:]
                xid_resource_singular = model_definition["groups"][xid_group_plural]["resources"][xid_resource_plural]["singular"]
                xid_group_singular = model_definition["groups"][xid_group_plural]["singular"]
                meta_template_copy = copy.deepcopy(meta_template)
                replace_refs(meta_template_copy, "{%-resourceTypeReference-%}", f"#/components/schemas/{xid_resource_singular}")
                replace_refs(meta_template_copy, "{%-groupTypeReference-%}", f"#/components/schemas/{xid_group_singular}")
                replace_ops(meta_template_copy, "{%-resourceNameSingular-%}", f"{pascal(group['singular'])}{pascal(xid_resource_plural)}")
                openapi["paths"][f"/{group['plural']}/{{groupid}}/{xid_resource_plural}/meta"]= meta_template_copy

        openapi["paths"].pop(path)
        path = "/{%-groupNamePlural-%}/{groupid}/{%-resourceNamePlural-%}/{resourceid}$details"
        details_template = openapi["paths"][path]
        for _, group in model_definition.get("groups", {}).items():
            for _, resource in group.get("resources", {}).items():
                resource = resolve_resource(group, resource)
                details_template_copy = copy.deepcopy(details_template)
                replace_refs(details_template_copy, "{%-resourceTypeReference-%}", f"#/components/schemas/{resource['singular']}")
                replace_refs(details_template_copy, "{%-groupTypeReference-%}", f"#/components/schemas/{group['singular']}")
                replace_ops(details_template_copy, "{%-resourceNameSingular-%}", f"{pascal(group['singular'])}{pascal(resource['singular'])}")
                openapi["paths"][f"/{group['plural']}/{{groupid}}/{resource['plural']}/{{resourceid}}$details"]= details_template_copy
            for ximportresources_xid in group.get("ximportresources", []):
                xid_group_plural, xid_resource_plural = ximportresources_xid.split("/")[1:]
                xid_resource_singular = model_definition["groups"][xid_group_plural]["resources"][xid_resource_plural]["singular"]
                xid_group_singular = model_definition["groups"][xid_group_plural]["singular"]
                details_template_copy = copy.deepcopy(details_template)
                replace_refs(details_template_copy, "{%-resourceTypeReference-%}", f"#/components/schemas/{xid_resource_singular}")
                replace_refs(details_template_copy, "{%-groupTypeReference-%}", f"#/components/schemas/{xid_group_singular}")
                replace_ops(details_template_copy, "{%-resourceNameSingular-%}", f"{pascal(group['singular'])}{pascal(xid_resource_plural)}")
                openapi["paths"][f"/{group['plural']}/{{groupid}}/{xid_resource_plural}$details"]= details_template_copy

        openapi["paths"].pop(path)
        path = "/{%-groupNamePlural-%}/{groupid}/{%-resourceNamePlural-%}/{resourceid}"
        resourceid_template = openapi["paths"][path]
        for _, group in model_definition.get("groups", {}).items():
            for _, resource in group.get("resources", {}).items():
                resource = resolve_resource(group, resource)
                resourceid_template_copy = copy.deepcopy(resourceid_template)
                replace_refs(resourceid_template_copy, "{%-resourceTypeReference-%}", f"#/components/schemas/{resource['singular']}")
                replace_refs(resourceid_template_copy, "{%-groupTypeReference-%}", f"#/components/schemas/{group['singular']}")
                replace_ops(resourceid_template_copy, "{%-resourceNameSingular-%}", f"{pascal(group['singular'])}{pascal(resource['singular'])}")
                openapi["paths"][f"/{group['plural']}/{{groupid}}/{resource['plural']}/{{resourceid}}"]= resourceid_template_copy
            for ximportresources_xid in group.get("ximportresources", []):
                xid_group_plural, xid_resource_plural = ximportresources_xid.split("/")[1:]
                xid_resource_singular = model_definition["groups"][xid_group_plural]["resources"][xid_resource_plural]["singular"]
                xid_group_singular = model_definition["groups"][xid_group_plural]["singular"]
                resourceid_template_copy = copy.deepcopy(resourceid_template)
                replace_refs(resourceid_template_copy, "{%-resourceTypeReference-%}", f"#/components/schemas/{xid_resource_singular}")
                replace_refs(resourceid_template_copy, "{%-groupTypeReference-%}", f"#/components/schemas/{xid_group_singular}")
                replace_ops(resourceid_template_copy, "{%-resourceNameSingular-%}", f"{pascal(group['singular'])}{pascal(xid_resource_plural)}")
                openapi["paths"][f"/{group['plural']}/{{groupid}}/{xid_resource_plural}/{{resourceid}}"]= resourceid_template_copy

        openapi["paths"].pop(path)
        path = "/{%-groupNamePlural-%}/{groupid}/{%-resourceNamePlural-%}/{resourceid}/versions"
        versions_template = openapi["paths"][path]
        for _, group in model_definition.get("groups", {}).items():
            for _, resource in group.get("resources", {}).items():
                resource = resolve_resource(group, resource)
                versions_template_copy = copy.deepcopy(versions_template)
                replace_refs(versions_template_copy, "{%-resourceTypeReference-%}", f"#/components/schemas/{resource['singular']}")
                replace_refs(versions_template_copy, "{%-groupTypeReference-%}", f"#/components/schemas/{group['singular']}")
                replace_ops(versions_template_copy, "{%-resourceNameSingular-%}", f"{pascal(group['singular'])}{pascal(resource['singular'])}")
                openapi["paths"][f"/{group['plural']}/{{groupid}}/{resource['plural']}/{{resourceid}}/versions"]= versions_template_copy
            for ximportresources_xid in group.get("ximportresources", []):
                xid_group_plural, xid_resource_plural = ximportresources_xid.split("/")[1:]
                xid_resource_singular = model_definition["groups"][xid_group_plural]["resources"][xid_resource_plural]["singular"]
                xid_group_singular = model_definition["groups"][xid_group_plural]["singular"]
                versions_template_copy = copy.deepcopy(versions_template)
                replace_refs(versions_template_copy, "{%-resourceTypeReference-%}", f"#/components/schemas/{xid_resource_singular}")
                replace_refs(versions_template_copy, "{%-groupTypeReference-%}", f"#/components/schemas/{xid_group_singular}")
                replace_ops(versions_template_copy, "{%-resourceNameSingular-%}", f"{pascal(group['singular'])}{pascal(xid_resource_plural)}")
                openapi["paths"][f"/{group['plural']}/{{groupid}}/{xid_resource_plural}/versions"]= versions_template_copy

        openapi["paths"].pop(path)
        path = "/{%-groupNamePlural-%}/{groupid}/{%-resourceNamePlural-%}/{resourceid}/versions/{versionid}"
        versionid_template = openapi["paths"][path]
        for _, group in model_definition.get("groups", {}).items():
            for _, resource in group.get("resources", {}).items():
                resource = resolve_resource(group, resource)
                versionid_template_copy = copy.deepcopy(versionid_template)
                replace_refs(versionid_template_copy, "{%-resourceTypeReference-%}", f"#/components/schemas/{resource['singular']}")
                replace_refs(versionid_template_copy, "{%-groupTypeReference-%}", f"#/components/schemas/{group['singular']}")
                replace_ops(versionid_template_copy, "{%-resourceNameSingular-%}", f"{pascal(group['singular'])}{pascal(resource['singular'])}")
                openapi["paths"][f"/{group['plural']}/{{groupid}}/{resource['plural']}/{{resourceid}}/versions/{{versionid}}"]= versionid_template_copy
            for ximportresources_xid in group.get("ximportresources", []):
                xid_group_plural, xid_resource_plural = ximportresources_xid.split("/")[1:]
                xid_resource_singular = model_definition["groups"][xid_group_plural]["resources"][xid_resource_plural]["singular"]
                xid_group_singular = model_definition["groups"][xid_group_plural]["singular"]
                versionid_template_copy = copy.deepcopy(versionid_template)
                replace_refs(versionid_template_copy, "{%-resourceTypeReference-%}", f"#/components/schemas/{xid_resource_singular}")
                replace_refs(versionid_template_copy, "{%-groupTypeReference-%}", f"#/components/schemas/{xid_group_singular}")
                replace_ops(versionid_template_copy, "{%-resourceNameSingular-%}", f"{pascal(group['singular'])}{pascal(xid_resource_plural)}")
                openapi["paths"][f"/{group['plural']}/{{groupid}}/{xid_resource_plural}/versions/{{versionid}}"]= versionid_template_copy

        openapi["paths"].pop(path)

        registry_entity_schema = openapi["components"]["schemas"]["RegistryEntity"]
        for _, group in model_definition.get("groups", {}).items():
            group_plural = group["plural"]
            group_singular = group["singular"]
            registry_entity_schema["properties"][f"{group_plural}url"] = {
            "type": "string",
            "format": "uri",
            "description": f"The URL for retrieving the {group_plural} (e.g. endpointsurl)."
            }
            registry_entity_schema["properties"][f"{group_plural}count"] = {
            "type": "integer",
            "minimum": 0,
            "description": f"The count of {group_plural} in the registry."
            }
            registry_entity_schema["properties"][group_plural] = {
            "type": "object",
            "description": f"A map of {group_plural} in the registry, keyed by {group_singular} identifier. Present only if inlined.",
            "additionalProperties": {
                "$ref": f"#/components/schemas/{group_singular}"
            },
            "nullable": True
            }

        return openapi
    except:
        print(f"Error opening template file {template_file_name}")
        raise


def generate_json_schema(model_definition, for_openapi=False, schema_id='') -> dict:
    """
    Generate a JSON schema for the given model definition.

    Args:
        model_definition (dict): The model definition to generate the schema for.
        for_openapi (bool, optional): Whether the schema is being generated for OpenAPI. Defaults to False.
        schema_id (str, optional): The URI to use for the schema's $id. Defaults to ''.

    Returns:
        dict: The generated JSON schema.
    """

    def handle_item(resource_schema, type, item, enum_values=None):
        if type == "object":
            resource_schema["type"] = "object"
            if "attributes" in item:
                handle_attributes(resource_schema,  item["attributes"])
        elif type == "map":
            resource_schema["type"] = "object"
            if "type" in item:
                if item["type"] == "object":
                    attr_schema = {"type": "object", "description": "", "properties": {}}
                    if "attributes" in item:
                        handle_attributes(attr_schema, item["attributes"])
                else:
                    attr_schema = copy.deepcopy(json_type_mapping[item["type"]])
                if "description" in item:
                    attr_schema["description"] = item["description"]
                if "description" in attr_schema and attr_schema["description"] == "":
                    del attr_schema["description"]
                resource_schema["additionalProperties"] = attr_schema
                if item["type"] == "object" or item["type"] == "map" or item["type"] == "array":
                    if "item" in item:
                        handle_item(resource_schema["additionalProperties"], item["type"], item["item"])
        elif type == "array":
            resource_schema["type"] = "array"
            if "type" in item:
                if item["type"] == "object":
                    attr_schema = {"type": "object", "description": "", "properties": {}}
                    if "attributes" in item:
                        handle_attributes(attr_schema, item["attributes"])
                    else:
                        attr_schema = copy.deepcopy(attr_schema)
                else:
                    attr_schema = copy.deepcopy(json_type_mapping[item["type"]])
                if "description" in item:
                    attr_schema["description"] = item["description"]
                if "description" in attr_schema and attr_schema["description"] == "":
                    del attr_schema["description"]
                # Apply enum constraint to array items if provided
                if enum_values is not None and len(enum_values) > 0:
                    attr_schema["enum"] = enum_values
                resource_schema["items"] = attr_schema
                if item["type"] == "object" or item["type"] == "map" or item["type"] == "array":
                    if "item" in item:
                        handle_item(resource_schema["items"], item["type"], item["item"])



    def handle_attributes(resource_schema, attributes):
        """
        This function takes in a resource schema and a dictionary of attributes and their properties.
        It iterates through each attribute and creates a JSON schema for it based on its properties.
        The function also handles nested attributes and conditional attributes using the "ifvalues" property.
        The resulting schema is added to the resource schema.
        """
        for attr_name, attr_props in attributes.items():
            if attr_props["type"] == "object":
                attr_schema = {"type": "object", "description": "", "properties": {}}
                if "attributes" in attr_props:
                    handle_attributes(attr_schema, attr_props["attributes"])
            else:
                attr_schema = copy.deepcopy(json_type_mapping[attr_props["type"]])

            if "description" in attr_props:
                attr_schema["description"] = attr_props["description"]
            if "description" in attr_schema and attr_schema["description"] == "":
                del attr_schema["description"]

            if attr_props["type"] == "object" or attr_props["type"] == "map" or attr_props["type"] == "array":
                if "item" in attr_props:
                    # Pass enum values if this is an array with enum constraint
                    enum_values = attr_props.get("enum") if attr_props["type"] == "array" else None
                    handle_item(attr_schema, attr_props["type"], attr_props["item"], enum_values)

            if "required" in attr_props and attr_props["required"] == True and not "default" in attr_props:
                if "required" not in resource_schema:
                    resource_schema["required"] = []
                resource_schema["required"].append(attr_name)

            if "ifvalues" in attr_props:
                if attr_name == "*":
                    raise Exception("Can't use wild card attribute name with ifvalues")

                if for_openapi:
                    resource_schema["discriminator"] = {
                        "propertyName": attr_name,
                        "mapping": {}
                    }

                if attr_name in resource_schema["properties"]:
                    resource_schema["properties"].pop(attr_name)
                    if "required" in resource_schema and attr_name in resource_schema["required"]:
                        resource_schema["required"].remove(attr_name)

                one_of = []
                for condition_value, condition_props in attr_props["ifvalues"].items():
                    # create an identifier from condition_value, turning all spaces and special characters in to underscore
                    condition_schema_identifier = attr_name + "_" + "".join([c if c.isalnum() else "_" for c in condition_value])
                    # for openapi, add a reference to this schema in the discriminator mapping
                    if for_openapi:
                        resource_schema["discriminator"]["mapping"][condition_value] = f"#/components/schemas/{condition_schema_identifier}"

                    conditional_attr_schema = copy.deepcopy(attr_schema)
                    conditional_attr_schema.update({
                                "enum": [condition_value],
                            })
                    if "siblingattributes" in condition_props:
                        conditional_schema = {
                                    "properties": {
                                        attr_name: conditional_attr_schema
                                    },
                                    "required": [attr_name]
                                }
                        handle_attributes(conditional_schema,  condition_props.get("siblingattributes", {}))
                    else:
                        conditional_attr_schema.update({
                            "default": condition_value
                        })
                        conditional_schema = {
                            "properties": {
                                        attr_name: conditional_attr_schema
                                    },
                        }

                    if for_openapi:
                        resource_schema["discriminator"]["mapping"][condition_value] = f"#/components/schemas/{condition_schema_identifier}"
                        schema_definitions[condition_schema_identifier] = copy.deepcopy(conditional_schema)
                    else:
                        one_of.append(copy.deepcopy(conditional_schema))
                if len(one_of) > 0:
                    one_of.append({
                        "anyOf": [
                            { "not": { "required": [attr_name] } },
                            {
                                "properties": {
                                    attr_name: { "not": { "enum": list(attr_props["ifvalues"].keys()) } }
                                },
                                "required": [attr_name]
                            }
                        ]
                    })
                    if "oneOf" in resource_schema:
                        resource_schema["allOf"] = [{"oneOf" : resource_schema.pop("oneOf")}]
                        resource_schema["allOf"].append({"oneOf": one_of})
                    else:
                        resource_schema["oneOf"] = one_of
            else:
                if attr_name == "*":
                    if attr_props["type"] == "any":
                        continue
                    if "additionalProperties" in resource_schema:
                        resource_schema["additionalProperties"].update(attr_schema)
                    else:
                        resource_schema["additionalProperties"] = copy.deepcopy(attr_schema)
                else:
                    if not "properties" in resource_schema:
                        resource_schema["properties"] = {}
                    resource_schema["properties"][attr_name] = copy.deepcopy(attr_schema)

    ## body of the core function starts here
    schema_group_names = []
    for k in model_definition.get("groups", {}).keys():
        schema_group_names.append(k.lower())

    if for_openapi:
        reference_prefix = "#/components/schemas/"
        schema = {
            "components": {
                "schemas": {
                    "document": {
                        "type": "object",
                        "properties": {},
                    }
                }
            }
        }
        document_properties = schema["components"]["schemas"]["document"]["properties"]
        schema_definitions = schema["components"]["schemas"]
    else:
        reference_prefix = "#/definitions/"
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "$id": schema_id if schema_id else "http://xregistry.io/schema/"+"-".join(schema_group_names),
            "properties": {},
            "definitions": {}
        }
        document_properties = schema["properties"]
        schema_definitions = schema["definitions"]


    for key, group in model_definition.get("groups", {}).items():
        if "plural" not in group: group["plural"] = key
        groups_name = group["plural"]
        group_name = group["singular"]
        # Create a namespace folder for this group's definitions
        # For OpenAPI: use flat keys without -schema suffix
        # For JSON Schema: use nested structure with -schema suffix
        if for_openapi:
            group_definition_prefix = f"{reference_prefix}"
        else:
            group_definition_prefix = f"{reference_prefix}{group_name}-schema/"
        groups_schema = {
            "type": "object",
            "additionalProperties": {"$ref": f"{group_definition_prefix}{group_name}"}
        }

        document_properties[groups_name] = groups_schema
        resource_collection_properties = {}

        for rKey, resource in group.get("resources", {}).items():
            if "plural" not in resource: resource["plural"] = rKey
            resource = resolve_resource(group, resource)
            resource_name = resource["singular"]
            props = {}
            props[resource_name+"id"] = {"type": "string", "description": f"ID of the {resource_name} object"}
            props.update(copy.deepcopy(json_common_attributes))

            if resource.get("hasdocument", True):
                resource_schema = {
                    "type": "object",
                    "properties": props,
                    "oneOf": [
                        {
                            "properties": {
                                resource_name : {
                                    "description": f"Embedded {resource_name} object",
                                    "oneOf": [{"type": "object"},{"type": "string"}]
                                }
                            },
                            "required": [resource_name]
                        },
                        {
                            "properties": {
                                resource_name+"base64" : {
                                    "description": f"Embedded {resource_name} object as binary data",
                                    "type": "string",
                                    "format": "base64"
                                }
                            },
                            "required": [resource_name+"base64"]
                        },
                        {
                            "properties": {
                                resource_name+"url" : {
                                    "description": f"Linked {resource_name} object",
                                    "type": "string",
                                    "format": "uri"
                                }
                            },
                            "required": [resource_name+"url"]
                        }
                    ]
                }
            else:
                resource_schema = {
                    "type": "object",
                    "properties": props
                }

            attributes = resource.get("attributes", {})
            if resource.get("maxversions", -1) != 1:
                resource_version_schema = copy.deepcopy(resource_schema)
                props = {}
                props["versionid"] = {"type": "string", "description": f"ID of the {resource_name} version"}
                props.update(copy.deepcopy(resource_version_schema["properties"]))
                resource_version_schema["properties"] = props
                handle_attributes(resource_version_schema, attributes)

                resource_schema["oneOf"] = [
                        {
                            "properties": {
                                "versionsurl": {"type": "string"},
                                "versionscount": {"type": "integer"},
                            },
                            "required": ["versionsurl"]
                        },
                        {
                            "properties": {
                                "versions": {
                                "type": "object",
                                "additionalProperties": {
                                    "$ref": f"{group_definition_prefix}{resource_name}Version"
                                    }
                                }
                            },
                            "required": ["versions"]
                        }
                    ]

                # For OpenAPI: flat keys, for JSON Schema: nested structure
                if for_openapi:
                    schema_definitions[f"{resource_name}Version"] = resource_version_schema
                else:
                    if f"{group_name}-schema" not in schema_definitions:
                        schema_definitions[f"{group_name}-schema"] = {}
                    schema_definitions[f"{group_name}-schema"][f"{resource_name}Version"] = resource_version_schema
            else:
                handle_attributes(resource_schema, attributes)

            # For OpenAPI: flat keys, for JSON Schema: nested structure
            if for_openapi:
                schema_definitions[resource_name] = resource_schema
            else:
                if f"{group_name}-schema" not in schema_definitions:
                    schema_definitions[f"{group_name}-schema"] = {}
                schema_definitions[f"{group_name}-schema"][resource_name] = resource_schema
            resource_collection_properties[resource["plural"]] = {
                    "type": "object",
                    "additionalProperties": {
                        "$ref": f"{group_definition_prefix}{resource_name}",
                    }
                }

        for ximportresources_xid in group.get("ximportresources", []):
            xid_group_plural, xid_resource_plural = ximportresources_xid.split("/")[1:]
            xid_group_singular = model_definition["groups"][xid_group_plural]["singular"]
            xid_resource_singular = model_definition["groups"][xid_group_plural]["resources"][xid_resource_plural]["singular"]
            # Use the source group's namespace for imported resources
            # For OpenAPI: flat keys, for JSON Schema: nested structure
            if for_openapi:
                xid_group_definition_prefix = f"{reference_prefix}"
            else:
                xid_group_definition_prefix = f"{reference_prefix}{xid_group_singular}-schema/"
            resource_collection_properties[xid_resource_plural] = {
                    "type": "object",
                    "additionalProperties": {
                        "$ref": f"{xid_group_definition_prefix}{xid_resource_singular}",
                    }
                }

        props = {}
        props[group_name+"id"] = {"type": "string", "description": f"ID of the {group_name} object"}
        props.update(copy.deepcopy(json_common_attributes))
        group_schema = {
            "type": "object",
            "properties": props
        }
        attributes = group.get("attributes", {})
        handle_attributes(group_schema, attributes)
        for resource_collection_name, resource_collection_schema in resource_collection_properties.items():
            group_schema["properties"][resource_collection_name] = resource_collection_schema
        # For OpenAPI: flat keys, for JSON Schema: nested structure
        if for_openapi:
            schema_definitions[group_name] = group_schema
        else:
            if f"{group_name}-schema" not in schema_definitions:
                schema_definitions[f"{group_name}-schema"] = {}
            schema_definitions[f"{group_name}-schema"][group_name] = group_schema
    return schema



def generate_avro_schema(model_definition) -> dict:
    """
    Generates an Avro schema based on the given model definition.

    Args:
        model_definition (dict): The model definition to generate the schema from.

    Returns:
        dict: The generated Avro schema.
    """

    # Pre-scan to determine if GenericRecord is needed anywhere
    def needs_generic_record(attributes):
        """Check if any attribute requires GenericRecord type"""
        for attr_name, attr_props in attributes.items():
            # Check for "*" extension attributes with "any" or "var" type
            if attr_name == "*" and attr_props.get("type") in ["any", "var", "object"]:
                return True
            # Consolidated check: If attribute is an extension ("*") with type "any", "var", or "object",
            # or if attribute is type "object" without "item" or "attributes", GenericRecord is needed.
            if (attr_name == "*" and attr_props.get("type") in ["any", "var", "object"]) or \
               (attr_props.get("type") == "object" and "item" not in attr_props and "attributes" not in attr_props):
                return True
            # Check nested attributes
            if "attributes" in attr_props:
                if needs_generic_record(attr_props["attributes"]):
                    return True
            # Check ifvalues sibling attributes
            if "ifvalues" in attr_props:
                for condition_props in attr_props["ifvalues"].values():
                    if "siblingattributes" in condition_props:
                        if needs_generic_record(condition_props["siblingattributes"]):
                            return True
        return False

    # Check if GenericRecord is needed in the entire model
    generic_record_needed = False
    for _, group in model_definition.get("groups", {}).items():
        if "attributes" in group and needs_generic_record(group["attributes"]):
            generic_record_needed = True
            break
        for _, resource in group.get("resources", {}).items():
            resource = resolve_resource(group, resource)
            if "attributes" in resource and needs_generic_record(resource["attributes"]):
                generic_record_needed = True
                break
        if generic_record_needed:
            break

    avro_generic_record_emitted = False
    record_types = set()

    def handle_item(resource_schema, type, item, name, prefix, enum_values=None):
        if type == "object":
            if "attributes" in item:
                item_schema = { "type": "record", "name" : prefix+name+"Type", "fields": []}
                handle_attributes(item_schema, item["attributes"], prefix)
                resource_schema["type"] = item_schema
            else:
                # Use GenericRecord reference (it's defined at document level if needed)
                resource_schema["type"] = avro_generic_record_qualified_name
        elif type == "map":
            resource_schema["type"] =  { "type": "map", "name": prefix+name+"Type","values": "" }
            if "type" in item:
                item_schema = copy.deepcopy(avro_type_mapping[item["type"]])
                if item["type"] == "object" or item["type"] == "map" or item["type"] == "array":
                    if "item" in item:
                        handle_item(item_schema, item["type"], item["item"], name+"Item", prefix)
                resource_schema["type"]["values"] = item_schema["type"]
            else:
                raise Exception("Map item must have a type specified")
        elif type == "array":
            resource_schema["type"] = { "type": "array", "name": prefix+name+"ArrayType", "items": "" }
            if "type" in item:
                item_schema = copy.deepcopy(avro_type_mapping[item["type"]])
                if item["type"] == "object" or item["type"] == "map" or item["type"] == "array":
                    if "item" in item:
                        handle_item(item_schema, item["type"], item["item"], name, prefix)
                        resource_schema["type"]["items"] = item_schema["type"]
                else:
                    # Apply enum constraint to array items if provided
                    if enum_values is not None and len(enum_values) > 0:
                        item_schema = {
                            "type": "enum",
                            "name": prefix+name+"EnumType",
                            "symbols": enum_values
                        }
                    resource_schema["type"]["items"] = item_schema
            else:
                raise Exception("Array item must have a type specified")


    def handle_attributes(resource_schema, attributes, type_prefix=""):
        nonlocal avro_generic_record_emitted
        for attr_name, attr_props in attributes.items():
            pascal_attr_name = pascal(attr_name)
            # attribute schema is based on the type mapping
            if "type" in attr_props:
                attr_schema = copy.deepcopy(avro_type_mapping[attr_props["type"]])
            else:
                # If 'type' is missing, skip this attribute or handle as needed
                continue
            # Only add a "name" field for types that are actual inline record definitions.
            # If attr_schema["type"] is a dict and has "type" == "record", it's an inline record definition.
            # Do not add "name" for simple types or references like "any"/"var".
            if attr_name != "*" and attr_props["type"] not in ["any", "var"]:
                if isinstance(attr_schema.get("type"), dict) and attr_schema["type"].get("type") == "record":
                    attr_schema["name"] = type_prefix+pascal_attr_name+"Type"
                if isinstance(attr_schema.get("type"), dict) or attr_schema.get("type") == "record":
                    attr_schema["name"] = type_prefix+pascal_attr_name+"Type"
                if isinstance(attr_schema.get("type"), dict) or attr_schema.get("type") == "record":
                    attr_schema["name"] = type_prefix+pascal_attr_name+"Type"

            # add the description, if any, as a doc attribute
            if "description" in attr_props:
                attr_schema["doc"] = attr_props["description"]

            if attr_props["type"] == "object" or attr_props["type"] == "map" or attr_props["type"] == "array":
                if "item" in attr_props:
                    # Pass enum values if this is an array with enum constraint
                    enum_values = attr_props.get("enum") if attr_props["type"] == "array" else None
                    handle_item(attr_schema, attr_props["type"], attr_props["item"], pascal_attr_name, type_prefix, enum_values)
                else:
                    if attr_props["type"] == "object":
                        # Use GenericRecord reference (it's defined at document level if needed)
                        attr_schema["type"] = avro_generic_record_qualified_name
                    else:
                        raise Exception("array or map attribute must have an item specified")

            if "ifvalues" in attr_props:
                if attr_name == "*":
                    raise Exception("Can't use wild card attribute name with ifvalues")

                if pascal_attr_name in resource_schema["fields"]:
                    resource_schema["fields"].pop(pascal_attr_name)

                union = []
                for condition_value, condition_props in attr_props["ifvalues"].items():
                    # create an identifier from condition_value, turning all spaces and special characters in to underscore
                    condition_schema_identifier = pascal_attr_name + pascal("".join([c if c.isalnum() else "_" for c in condition_value]))
                    conditional_schema = {
                                "type": "record",
                                "namespace": group_namespace,
                                "name": type_prefix+condition_schema_identifier+"Type",
                                "fields": []
                            }
                    handle_attributes(conditional_schema,  condition_props.get("siblingattributes", {}), condition_schema_identifier)
                    union.append(conditional_schema)
                if len(union) > 0:
                    field_schema = {
                            "name": camel(pascal_attr_name),
                             "type":  union
                    }
                    if "description" in attr_props:
                        field_schema["doc"] = attr_props["description"]
                    resource_schema["fields"].append(field_schema)
            else:
                if attr_name == "*":
                    # For extension attributes, we need to handle named types properly
                    # Named types cannot be defined inline in a map's values field
                    values_type = attr_schema["type"]

                    # Handle the case where the type needs to be resolved
                    if isinstance(values_type, dict) and "name" in values_type:
                        # This is a named type (like GenericRecord) - use only the name as a reference
                        values_type_ref = values_type["name"]
                    elif isinstance(values_type, dict):
                        # This is a complex unnamed type - should not happen but use as-is
                        values_type_ref = values_type
                    elif values_type == "record":
                        # This is an incomplete object type - use GenericRecord reference
                        # (GenericRecord is defined at document level if needed)
                        values_type_ref = avro_generic_record_qualified_name
                    else:
                        # This is a simple type reference (string like "string", "int", etc.)
                        values_type_ref = values_type

                    field_schema = {
                            "name": "Extensions",
                            "type":  {
                               "type": "map",
                               "name": type_prefix+"ExtensionsType",
                               "default": {},
                               "values": values_type_ref
                             }}
                    if "description" in attr_props:
                        field_schema["doc"] = attr_props["description"]
                    resource_schema["fields"].append(field_schema)
                else:
                    attr_schema["name"] = camel(pascal_attr_name)
                    # if the attribute is not required, union the type with null
                    #if not "required" in attr_props or attr_props["required"] == False:
                    #    attr_schema = ["null", attr_schema]
                    resource_schema["fields"].append(attr_schema)



    ## body of the core function starts here
    document_type = {
        "type": "record",
        "name": "DocumentType",
        "namespace": "io.xregistry",
        "fields": [],
    }
    document_properties = document_type["fields"]

    # If GenericRecord is needed anywhere in the schema, define it first as a field
    # This ensures it's available for all references throughout the schema
    if generic_record_needed:
        # Create a version with fully qualified names for recursive references
        generic_record_with_namespace = {
            "type": "record",
            "name": avro_generic_record_name,
            "fields": [
                {
                    "name": "object",
                    "type": {
                        "type": "map",
                        "values": [
                            "null",
                            "boolean",
                            "int",
                            "long",
                            "float",
                            "double",
                            "bytes",
                            "string",
                            {
                                "type": "array",
                                "items": [
                                    "null",
                                    "boolean",
                                    "int",
                                    "long",
                                    "float",
                                    "double",
                                    "bytes",
                                    "string",
                                    avro_generic_record_qualified_name
                                ]
                            },
                            avro_generic_record_qualified_name
                        ]
                    }
                }
            ]
        }
        generic_record_field = {
            "name": "genericRecordDefinition",
            "type": {
                "type": "array",
                "items": generic_record_with_namespace
            },
            "default": [],
            "doc": "Internal field to define GenericRecord type for use in extension attributes"
        }
        document_properties.append(generic_record_field)

    for key, group in model_definition.get("groups", {}).items():
        if "plural" not in group: group["plural"] = key
        groups_name = group["plural"]
        group_name = group["singular"]
        # Create a namespace for this group to avoid type name collisions
        group_namespace = f"io.xregistry.{groups_name}"
        resource_collection_fields = []

        for rKey, resource in group.get("resources", {}).items():
            if "plural" not in resource: resource["plural"] = rKey
            resource = resolve_resource(group, resource)
            resource_name = resource["singular"]
            if resource_name in record_types:
                resource_collection_fields.append({
                    "name": camel(resource["plural"]),
                    "type" :{
                        "type": "map",
                        "values": f"{group_namespace}.{pascal(resource_name)}Type"
                    }
                    })
            else:
                record_types.add(resource_name)
                props = copy.deepcopy(avro_common_attributes)
                props.insert(0, {"name": resource_name+"id", "type": "string", "description": f"ID of the {resource_name} object"})
                resource_schema = {
                    "type": "record",
                    "name": pascal(resource_name)+"Type",
                    "namespace": group_namespace,
                    "fields": props
                }
                attributes = resource.get("attributes", {})
                if resource.get("versions", 1) != 1:
                    resource_version_schema = copy.deepcopy(resource_schema)
                    resource_version_schema["fields"].insert(0, {"name" : "versionid", "type": "string", "description": f"ID of the {resource_name} version"})
                    handle_attributes(resource_version_schema, attributes)
                    resource_version_schema["name"] = pascal(resource_name)+"VersionType"
                    resource_schema["fields"].append(
                        {
                            "name": "versions",
                            "type": [
                                {
                                    "type": "map",
                                    "values": resource_version_schema
                                },
                                {
                                    "type": "record",
                                    "name": pascal(resource_name)+"VersionInfo",
                                    "fields": [
                                        {
                                            "name": "versionsUrl",
                                            "type": "string"
                                        },
                                        {
                                            "name": "versionCount",
                                            "type": "int"
                                        }
                                    ]
                                }
                            ]
                        })
                else:
                    handle_attributes(resource_schema, attributes)

                resource_collection_fields.append({
                    "name": camel(resource["plural"]),
                    "type" :{
                        "type": "map",
                        "values": resource_schema
                    }
                })

        for ximportresources_xid in group.get("ximportresources", []):
            xid_group_plural, xid_resource_plural = ximportresources_xid.split("/")[1:]
            xid_resource_singular = model_definition["groups"][xid_group_plural]["resources"][xid_resource_plural]["singular"]
            # Use the source group's namespace for imported resources
            xid_group_namespace = f"io.xregistry.{xid_group_plural}"
            resource_collection_fields.append({
                    "name": camel(xid_resource_plural),
                    "type" :{
                        "type": "map",
                        "values": f"{xid_group_namespace}.{pascal(xid_resource_singular)}Type"
                    }
                    })
        props = copy.deepcopy(avro_common_attributes)
        props.insert(0, {"name" : group_name+"id", "type": "string", "description": f"ID of the {group_name} object"})
        group_schema = {
            "type": "record",
            "name": pascal(group_name)+"Type",
            "fields": props,
        }
        attributes = group.get("attributes", {})
        handle_attributes(group_schema, attributes)
        for resource_collection in resource_collection_fields:
            group_schema["fields"].append(resource_collection)
        groups_schema = {
            "name": camel(groups_name),
            "type": {
                "type": "map",
                "values": group_schema
            }
        }
        document_properties.append(groups_schema)

    return document_type


def resolve_resource(group, resource):
    if "uri" in resource:
        try:
            base_uri = group["$source"]
            file_uri = resource["uri"]

                    # split off the JSON pointer part, if any
            if "#" in file_uri:
                file_uri, json_pointer = file_uri.split("#", 1)
                    # find out if it is a http URL or a relative path
            if file_uri.lower().startswith('http'):
                        # it is a http URL, retrieve the file
                import requests
                response = requests.get(file_uri)
                resource_object = response.json()
            else:
                file_uri = file_uri.replace('/', os.sep)
                path = os.path.join(os.path.dirname(base_uri), file_uri)
                        # it is a file path, load the file
                with open(path, encoding='utf-8') as file:
                    resource_object = json.load(file)
            if json_pointer:
                resource = resolve_pointer(resource_object, json_pointer)
            else:
                resource = resource_object
        except:
            print(f"Error loading model definition from {file_uri}")
            raise
    return resource





# Replace this with your model definition
model_definition = {
    "schemas": ["json-schema/draft-07"],
    #... rest of your model definition
}


def resolve_imports(basedir, node):
    """
    recursively resolve all $includes in the model definition.
    This code handles two cases. The legacy case where the $include is
    relative file path (URL)
    """

    if isinstance(node, dict):
        if "$include" in node:
            obj_ref = ''
            file_ref = node["$include"]
            # strip # anchor portion from the file reference
            if "#" in file_ref:
                fr = file_ref.split("#")
                file_ref = fr[0]
                obj_ref = fr[1]
            file_ref = file_ref.replace('/', os.sep)
            import_file = os.path.join(basedir, file_ref)
            with open(import_file, encoding='utf-8') as file:
                import_definition = json.load(file)
            del node["$include"]
            if obj_ref:
                node.update(resolve_pointer(import_definition, obj_ref))
            else:
                node.update(import_definition)
        for k,v in node.items():
            node[k] = resolve_imports(basedir, v)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            node[i] = resolve_imports(basedir, item)
    return node


# read model definition from file ../schema/model.json
# make the path relative to this script file, irrespective of working directory

def main():
    parser = argparse.ArgumentParser(description='Generate JSON schema from model definition')
    parser.add_argument('--type', type=str, help='type of document to generate', choices=['json-schema', 'avro-schema', 'openapi'], default='json-schema')
    parser.add_argument('--output', type=str, help='Path for output file', default='', required=False)
    parser.add_argument('--schema-id', type=str, help='URI for the $id field in the schema', default='', required=False)
    parser.add_argument('input_files', type=str, help='Path to input files', nargs='+')

    args = parser.parse_args()

    json_schema = None
    model_definition = { "groups": {} }
    for input_file in args.input_files:
        with open(input_file, encoding='utf-8') as file:
            print(f"> {input_file} as '{args.type}'")
            input_definition = json.load(file)
            input_definition = resolve_imports(os.path.dirname(input_file), input_definition)
            if "groups" in input_definition:
                for group_name, group_definition in input_definition["groups"].items():
                    # convert file.name to using OS separators
                    file_name = file.name.replace('/', os.sep)
                    group_definition["$source"] = os.path.join(os.getcwd(),file_name)
                    if group_name not in model_definition["groups"]:
                        model_definition["groups"][group_name] = group_definition
    if (args.type == 'json-schema'):
        json_schema = generate_json_schema(model_definition, schema_id=args.schema_id)
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as of:
                json.dump(json_schema, of, indent=2)
        else:
            print(json.dumps(json_schema, indent=2))
    elif (args.type == 'avro-schema'):
        avro_schema = generate_avro_schema(model_definition)
        if args.output:
            with open(args.output, 'w') as of:
                json.dump(avro_schema, of, indent=2)
        else:
            print(json.dumps(avro_schema, indent=2))
    elif (args.type == 'openapi'):
        openapi = generate_openapi(model_definition)
        if args.output:
            with open(args.output, 'w') as of:
                json.dump(openapi, of, indent=2)
        else:
            print(json.dumps(openapi, indent=2))


if __name__ == '__main__':
    main()
