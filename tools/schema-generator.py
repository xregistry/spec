import argparse
import copy
import json
import os
import re
from functools import lru_cache
from urllib.parse import unquote, urlsplit

from jsonpointer import EndOfList, JsonPointerException, resolve_pointer

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
    "decimal": {"type": "number"},
    "boolean": {"type": "boolean"},
    "array": {"type": "array"},
    "uritemplate": {"type": "string", "format": "uri-template"},
    "binary": {"type": "string", "format": "base64"},
    "timestamp": {"type": "string", "format": "date-time"},
    "any": {},
    "var": {"type": "object"}
}

json_structure_type_mapping = {
    "string": "string",
    "uri": "uri",
    "url": "uri",
    "xid": "uri",
    "datetime": "datetime",
    "integer": "integer",
    "uinteger": "uint32",
    "boolean": "boolean",
    "uritemplate": "string",
    "binary": "binary",
    "timestamp": "datetime",
    "any": "any",
    "var": "any"
}

json_common_attributes = {
    "name": {"type": "string", "description": "Name of the object"},
    "epoch": {"type": "integer", "minimum": 0, "description": "Optimistic concurrency update counter"},
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
    {"name": "epoch", "type": ["int", "null"], "doc": "Optimistic concurrency update counter"},
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


def model_with_names(model_definition):
    model = copy.deepcopy(model_definition)
    for plural, group in model.get("groups", {}).items():
        group.setdefault("plural", plural)
        for resource_plural, resource in group.get("resources", {}).items():
            resource.setdefault("plural", resource_plural)
    return model


def generate_openapi(model_definition):
    model_definition = model_with_names(model_definition)

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
        json_schema = generate_json_schema(
            model_definition, True,
            meta_template=openapi["components"]["schemas"]["Meta"],
        )
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
        document_resource_paths = set()
        path = "/{%-groupNamePlural-%}/{groupid}/{%-resourceNamePlural-%}"
        resource_template = openapi["paths"][path]
        for _, group in model_definition.get("groups", {}).items():
            for _, resource in group.get("resources", {}).items():
                resource = resolve_resource(group, resource)
                if resource.get("hasdocument", True):
                    document_resource_paths.add(
                        f"/{group['plural']}/{{groupid}}/{resource['plural']}/{{resourceid}}"
                    )
                resource_template_copy = copy.deepcopy(resource_template)
                replace_refs(resource_template_copy, "{%-resourceTypeReference-%}", f"#/components/schemas/{resource['singular']}")
                replace_refs(resource_template_copy, "{%-groupTypeReference-%}", f"#/components/schemas/{group['singular']}")
                replace_ops(resource_template_copy, "{%-resourceNamePlural-%}", f"{pascal(group['singular'])}{pascal(resource['plural'])}")
                openapi["paths"][f"/{group['plural']}/{{groupid}}/{resource['plural']}"]= resource_template_copy
            for ximportresources_xid in group.get("ximportresources", []):
                xid_group_plural, xid_resource_plural = ximportresources_xid.split("/")[1:]
                source_group = model_definition["groups"][xid_group_plural]
                source_resource = resolve_resource(
                    source_group, source_group["resources"][xid_resource_plural]
                )
                if source_resource.get("hasdocument", True):
                    document_resource_paths.add(
                        f"/{group['plural']}/{{groupid}}/{xid_resource_plural}/{{resourceid}}"
                    )
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
                openapi["paths"][f"/{group['plural']}/{{groupid}}/{xid_resource_plural}/{{resourceid}}/meta"]= meta_template_copy

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
                openapi["paths"][f"/{group['plural']}/{{groupid}}/{xid_resource_plural}/{{resourceid}}$details"]= details_template_copy

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
                openapi["paths"][f"/{group['plural']}/{{groupid}}/{xid_resource_plural}/{{resourceid}}/versions"]= versions_template_copy

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
                openapi["paths"][f"/{group['plural']}/{{groupid}}/{xid_resource_plural}/{{resourceid}}/versions/{{versionid}}"]= versionid_template_copy

        openapi["paths"].pop(path)

        for path, path_item in openapi["paths"].items():
            for method in ("put", "post", "patch", "delete"):
                if method not in path_item:
                    continue
                operation = path_item[method]
                parameters = operation.setdefault("parameters", [])
                ignore = {"$ref": "#/components/parameters/ignore"}
                if ignore not in parameters:
                    parameters.append(ignore)
                resource_path = path.removesuffix("/versions/{versionid}")
                if method in ("put", "post") and resource_path in document_resource_paths:
                    parameters.append({"$ref": "#/components/parameters/version-epoch"})

        registry_entity_schema = openapi["components"]["schemas"]["RegistryEntity"]
        document_schema = openapi["components"]["schemas"]["document"]
        for name in model_definition.get("attributes", {}):
            if name in document_schema["properties"]:
                registry_entity_schema["properties"][name] = copy.deepcopy(
                    document_schema["properties"][name]
                )
        for name in document_schema.get("required", []):
            if name not in registry_entity_schema["required"]:
                registry_entity_schema["required"].append(name)
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

        for method, name in (("put", "RegistryWriteInput"), ("patch", "RegistryPatchInput")):
            openapi["paths"]["/"][method]["requestBody"]["content"]["application/json"]["schema"] = {
                "$ref": f"#/components/schemas/{name}"
            }
        for group in model_definition.get("groups", {}).values():
            resources = dict(group.get("resources", {}))
            for imported in group.get("ximportresources", []):
                source_group, plural = imported.split("/")[1:]
                resources[plural] = model_definition["groups"][source_group]["resources"][plural]
            for plural, definition in resources.items():
                resource = resolve_resource(group, definition)
                name = resource["singular"]
                path = f"/{group['plural']}/{{groupid}}/{plural}/{{resourceid}}/meta"
                operation = openapi["paths"][path]
                replace_refs(operation, "#/components/schemas/Meta", f"#/components/schemas/{name}Meta")
                for method, suffix in (("put", "WriteInput"), ("patch", "PatchInput")):
                    operation[method]["requestBody"]["content"]["application/json"]["schema"] = {
                        "$ref": f"#/components/schemas/{name}Meta{suffix}"
                    }
        openapi["components"]["schemas"].pop("Meta")
        registry_entity_schema.setdefault("allOf", []).append({
            "$ref": "#/components/schemas/document"
        })
        return openapi
    except:
        print(f"Error opening template file {template_file_name}")
        raise


@lru_cache(maxsize=1)
def _selector_case_variants():
    variants = {}
    for codepoint in range(0x110000):
        character = chr(codepoint)
        folded = character.casefold()
        if folded != character:
            variants.setdefault(folded, set()).add(character)
    return variants


def _ifvalue_guard(type_name, value):
    scalar_type = json_type_mapping[type_name].get("type")
    if scalar_type == "string":
        variants = _selector_case_variants()
        parts = []
        for character in value:
            folded = character.casefold()
            spellings = {character} | variants.get(folded, set())
            if len(folded) == 1:
                spellings.add(folded)
            alternatives = [
                re.sub(r"([\\^$.|?*+(){}\[\]])", r"\\\1", spelling)
                for spelling in sorted(spellings)
            ]
            parts.append(
                alternatives[0] if len(alternatives) == 1
                else "(?:" + "|".join(alternatives) + ")"
            )
        # Unlike $, this end assertion cannot match before a final newline.
        return {"type": "string", "pattern": "^" + "".join(parts) + r"(?![\s\S])"}
    if scalar_type == "boolean" and value.lower() in ("true", "false"):
        return {"enum": [value.lower() == "true"]}
    if scalar_type == "integer" and re.fullmatch(r"-?(?:0|[1-9][0-9]*)", value):
        return {"enum": [int(value)]}
    raise ValueError(f"Unsupported ifvalues key {value!r} for scalar type {type_name!r}")


def generate_json_schema(
    model_definition, for_openapi=False, schema_id='', meta_template=None
) -> dict:
    """
    Generate a JSON schema for the given model definition.

    Args:
        model_definition (dict): The model definition to generate the schema for.
        for_openapi (bool, optional): Whether the schema is being generated for OpenAPI. Defaults to False.
        schema_id (str, optional): The URI to use for the schema's $id. Defaults to ''.

    Returns:
        dict: The generated JSON schema.
    """
    model_definition = model_with_names(model_definition)

    def handle_item(resource_schema, type, item, enum_values=None, role=None):
        if type == "object":
            resource_schema["type"] = "object"
            handle_attributes(resource_schema, item.get("attributes", {}), closed=True, role=role)
        elif type == "map":
            resource_schema["type"] = "object"
            if "type" in item:
                if item["type"] == "object":
                    attr_schema = {"type": "object", "description": "", "properties": {}}
                    handle_attributes(attr_schema, item.get("attributes", {}), closed=True, role=role)
                else:
                    attr_schema = copy.deepcopy(json_type_mapping[item["type"]])
                if "description" in item:
                    attr_schema["description"] = item["description"]
                if "description" in attr_schema and attr_schema["description"] == "":
                    del attr_schema["description"]
                resource_schema["additionalProperties"] = attr_schema
                if item["type"] == "object" or item["type"] == "map" or item["type"] == "array":
                    if "item" in item:
                        handle_item(resource_schema["additionalProperties"], item["type"], item["item"], role=role)
        elif type == "array":
            resource_schema["type"] = "array"
            if "type" in item:
                if item["type"] == "object":
                    attr_schema = {"type": "object", "description": "", "properties": {}}
                    handle_attributes(attr_schema, item.get("attributes", {}), closed=True, role=role)
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
                        handle_item(resource_schema["items"], item["type"], item["item"], role=role)



    def declared_names(value):
        names = set(value.get("properties", {}))
        for keyword in ("allOf", "anyOf", "oneOf"):
            for child in value.get(keyword, []):
                names.update(declared_names(child))
        return names

    def together(left, right):
        if not left:
            return copy.deepcopy(right)
        if not right:
            return copy.deepcopy(left)
        return {"allOf": [copy.deepcopy(left), copy.deepcopy(right)]}

    def close_object(value, names, wildcards):
        # Draft 7 closure cannot see declarations in sibling allOf branches.
        properties = value.setdefault("properties", {})
        for name in names:
            properties.setdefault(name, {})
        if any(not condition and not rule for condition, rule in wildcards):
            return
        declarations = {name: {} for name in names}
        if not wildcards:
            value["additionalProperties"] = False
        elif len(wildcards) == 1 and not wildcards[0][0]:
            value["additionalProperties"] = copy.deepcopy(wildcards[0][1])
        else:
            choices = [{"properties": declarations, "additionalProperties": False}]
            for condition, rule in wildcards:
                choices.append(together(condition, {
                    "properties": declarations, "additionalProperties": rule,
                }))
            value.setdefault("allOf", []).append({"anyOf": choices})
        for name, conditions in names.items():
            if any(not condition for condition in conditions):
                continue
            choices = [{"not": {"required": [name]}}, *conditions]
            choices.extend(
                together(condition, {"properties": {name: rule}})
                for condition, rule in wildcards
            )
            value.setdefault("allOf", []).append({"anyOf": choices})

    def handle_attributes(resource_schema, attributes, closed=False, role=None, partial=False):
        names = {name: [{}] for name in sorted(declared_names(resource_schema))}
        wildcards = []
        resource_schema.setdefault("properties", {})
        request_role = role in ("write", "patch")
        for attr_name, attr_props in attributes.items():
            if request_role and attr_props.get("readonly", False):
                if attr_name == "*":
                    wildcards.append(({}, {}))
                    continue
                names.setdefault(attr_name, []).append({})
                resource_schema["properties"][attr_name] = {
                    "description": "Server-controlled attribute; ignored in requests."
                }
                continue
            if attr_props["type"] == "object":
                attr_schema = {"type": "object", "description": "", "properties": {}}
                handle_attributes(
                    attr_schema, attr_props.get("attributes", {}), closed=True, role=role
                )
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
                    handle_item(attr_schema, attr_props["type"], attr_props["item"], enum_values, role=role)

            if role == "response" and attr_props.get("readonly", False):
                attr_schema["readOnly"] = True
            if role in ("response", "write") and "default" in attr_props:
                attr_schema["default"] = copy.deepcopy(attr_props["default"])
            if request_role and (
                not attr_props.get("required", False) or "default" in attr_props
            ):
                attr_schema["nullable"] = True
            if attr_name == "*":
                if "ifvalues" in attr_props:
                    raise ValueError("Can't use wild card attribute name with ifvalues")
                wildcards.append(({}, attr_schema))
                continue
            names.setdefault(attr_name, []).append({})
            resource_schema["properties"][attr_name] = copy.deepcopy(attr_schema)
            if not partial and attr_props.get("required") is True and (
                role == "response" or "default" not in attr_props
            ):
                if "required" not in resource_schema:
                    resource_schema["required"] = []
                if attr_name not in resource_schema["required"]:
                    resource_schema["required"].append(attr_name)

            if request_role:
                properties = resource_schema["properties"]
                # Retained selectors are server state, not facts in a partial request.
                for condition in attr_props.get("ifvalues", {}).values():
                    possible = {"type": "object", "properties": {}}
                    _, possible_wildcards = handle_attributes(
                        possible, condition.get("siblingattributes", {}),
                        role=role, partial=True,
                    )
                    wildcards.extend(possible_wildcards)
                    for name, value in possible["properties"].items():
                        names.setdefault(name, []).append({})
                        if "type" in value:
                            value["nullable"] = True
                        if name not in properties:
                            properties[name] = value
                        elif properties[name] != value:
                            properties[name] = {"anyOf": [properties[name], value]}
                continue

            if "ifvalues" in attr_props:
                one_of = []
                guards = []
                seen_values = set()
                for condition_value, condition_props in attr_props["ifvalues"].items():
                    folded_value = tuple(character.casefold() for character in condition_value)
                    if folded_value in seen_values:
                        raise ValueError(f"Duplicate case-insensitive ifvalues key: {condition_value!r}")
                    seen_values.add(folded_value)
                    guard = _ifvalue_guard(attr_props["type"], condition_value)
                    guards.append(guard)
                    conditional_attr_schema = copy.deepcopy(attr_schema)
                    conditional_attr_schema.update(guard)
                    conditional_schema = {
                        "properties": {attr_name: conditional_attr_schema},
                        "required": [attr_name],
                    }
                    child_names, child_wildcards = handle_attributes(
                        conditional_schema, condition_props.get("siblingattributes", {}),
                        role=role,
                    )
                    selected = {
                        "properties": {attr_name: guard},
                        "required": [attr_name],
                    }
                    for name, conditions in child_names.items():
                        names.setdefault(name, []).extend(
                            together(selected, condition) for condition in conditions
                        )
                    wildcards.extend(
                        (together(selected, condition), rule)
                        for condition, rule in child_wildcards
                    )
                    one_of.append(conditional_schema)
                if one_of:
                    one_of.append({
                        "not": {
                            "properties": {attr_name: {"anyOf": guards}},
                            "required": [attr_name],
                        }
                    })
                    resource_schema.setdefault("allOf", []).append({"oneOf": one_of})
        if closed:
            close_object(resource_schema, names, wildcards)
        return names, wildcards

    def input_core(identity):
        properties = {
            identity: {"type": "string"},
            **copy.deepcopy(json_common_attributes),
        }
        for name in ("self", "shortself", "xid"):
            properties[name] = {"description": "Server-controlled; ignored in requests."}
        for name in ("name", "description", "documentation", "labels", "createdat", "modifiedat"):
            properties[name]["nullable"] = True
        properties["epoch"]["minimum"] = 0
        return properties

    server_obligations = {
        "self", "shortself", "xid", "epoch", "createdat", "modifiedat",
    }

    def required_input(attributes, identities=()):
        return [
            name for name, definition in attributes.items()
            if name != "*" and definition.get("required") is True
            and not definition.get("readonly", False) and "default" not in definition
            and name not in server_obligations and name not in identities
        ]

    def entity_input(properties, attributes, role, identity=None, server_fields=()):
        guarded = {
            name: copy.deepcopy(properties[name])
            for name in (identity, "epoch", "versionid")
            if name in properties
        }
        ignored = {
            name: copy.deepcopy(value) for name, value in properties.items()
            if name in ("self", "shortself", "xid", "model", "specversion", "defaultversionurl")
            and "type" not in value
        }
        value = {
            "type": "object", "properties": properties,
            "description": (
                "Structural request input. The server applies defaults, retained "
                "state, conditional model constraints and final creation validation."
            ),
        }
        handle_attributes(value, attributes, closed=True, role=role, partial=role == "patch")
        for name, definition in guarded.items():
            definition.pop("readOnly", None)
            value["properties"][name] = definition
        value["properties"].update(ignored)
        for name in ("createdat", "modifiedat"):
            if name in value["properties"]:
                value["properties"][name]["nullable"] = True
        supplied_by_server = server_obligations | set(server_fields) | {identity}
        if "required" in value:
            value["required"] = [
                name for name in value["required"] if name not in supplied_by_server
            ]
        return value

    def meta_schemas(resource):
        identity = resource["singular"] + "id"
        complete = copy.deepcopy(meta_template)
        properties = complete["properties"]
        properties[identity] = properties.pop("RESOURCEid")
        properties["self"].update({
            "format": "uri-reference",
            "description": "Meta URL, including a relative document-view reference.",
        })
        properties["shortself"]["format"] = "uri-reference"
        properties["xid"].update({"format": "uri-reference", "pattern": "^/(?!/)"})
        properties["xref"].update({
            "format": "uri-reference",
            "pattern": "^/[^/?#]+/[^/?#]+/[^/?#]+/[^/?#]+$",
            "description": (
                "Registry-relative Resource XID. The server validates the effective "
                "model, same Resource type, visibility and target resolution."
            ),
        })
        properties["xref"].pop("nullable", None)
        properties["defaultversionurl"]["format"] = "uri-reference"
        properties["deprecated"] = {
            "type": "object",
            "properties": {
                "effective": {"type": "string", "format": "date-time"},
                "removal": {"type": "string", "format": "date-time"},
                "alternative": {"type": "string", "format": "uri-reference"},
                "documentation": {"type": "string", "format": "uri-reference"},
            },
            "additionalProperties": False,
        }
        for name in (
            identity, "readonly", "defaultversionid",
            "defaultversionurl", "defaultversionsticky",
        ):
            if name not in complete["required"]:
                complete["required"].append(name)
        attributes = resource.get("metaattributes", {})
        xid_contracts = {
            name: copy.deepcopy(properties[name]) for name in ("xid", "xref")
        }
        handle_attributes(complete, attributes, closed=True, role="response")
        properties[identity]["type"] = "string"
        for name, definition in xid_contracts.items():
            properties[name].update(definition)
        complete_required = complete.pop("required")
        complete["oneOf"] = [
            {"required": complete_required},
            {
                "properties": {name: {} for name in (
                    identity, "self", "shortself", "xid", "xref"
                )},
                "required": [identity, "self", "xid", "xref"],
                "additionalProperties": False,
            },
        ]
        complete["description"] = (
            "Completed Meta response, or the Core identity-only alias representation "
            "used for document views and inaccessible targets."
        )
        result = {"": complete}
        for role, suffix in (("write", "WriteInput"), ("patch", "PatchInput")):
            inputs = copy.deepcopy(properties)
            for name in ("self", "shortself", "xid", "defaultversionurl"):
                inputs[name] = {"description": "Server-controlled; ignored in normal requests."}
            for name in (
                "labels", "createdat", "modifiedat", "xref", "readonly",
                "compatibility", "deprecated", "defaultversionid", "defaultversionsticky",
            ):
                inputs[name]["nullable"] = True
            normal = entity_input(
                inputs, attributes, role, identity=identity,
                server_fields=("readonly", "defaultversionid", "defaultversionurl", "defaultversionsticky"),
            )
            normal["properties"]["xref"] = {
                **copy.deepcopy(properties["xref"]), "nullable": True,
            }
            normal["properties"]["xref"].pop("readOnly", None)
            for name in ("readonly", "defaultversionid", "defaultversionsticky"):
                normal["properties"][name]["nullable"] = True
            normal.setdefault("allOf", []).append({
                "not": {
                    "properties": {"xref": {"type": "string"}},
                    "required": ["xref"],
                }
            })
            alias = {
                "type": "object",
                "properties": {
                    name: copy.deepcopy(properties[name])
                    for name in (identity, "xref", "epoch")
                },
                "required": ["xref"],
                "additionalProperties": False,
                "description": (
                    "Alias creation/update accepts only the Resource ID, xref and "
                    "an applicable Meta epoch. Graph and transition checks are server-side."
                ),
            }
            for definition in alias["properties"].values():
                definition.pop("readOnly", None)
            result[suffix] = {
                "type": "object", "oneOf": [normal, alias],
                "description": normal["description"],
            }
        return result

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


    common_properties = {
        **copy.deepcopy(json_common_attributes), "shortself": {}, "icon": {},
    }
    version_properties = {name: {} for name in (
        "versionid", "ancestorid", "isdefault", "contenttype", "format",
        "formatvalidated", "formatvalidatedreason",
        "compatibilityvalidated", "compatibilityvalidatedreason",
    )}
    root_schema = schema["components"]["schemas"]["document"] if for_openapi else schema
    root_schema["type"] = "object"
    document_properties.update(copy.deepcopy(common_properties))
    document_properties.update({
        "registryid": {"type": "string"}, "specversion": {"type": "string"},
        "capabilities": {}, "model": {}, "modelsource": {},
    })
    output_role = "response" if for_openapi else None

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
        document_properties[groups_name + "url"] = {"type": "string"}
        document_properties[groups_name + "count"] = {"type": "integer"}
        resource_collection_properties = {}

        for rKey, resource in group.get("resources", {}).items():
            if "plural" not in resource: resource["plural"] = rKey
            resource = resolve_resource(group, resource)
            resource_name = resource["singular"]
            props = {}
            props[resource_name+"id"] = {"type": "string", "description": f"ID of the {resource_name} object"}
            props.update(copy.deepcopy(common_properties))
            props.update(copy.deepcopy(version_properties))

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
                props["versionid"] = {"type": "string", "description": f"ID of the {resource_name} version"}
                resource_version_schema["properties"] = props
                handle_attributes(resource_version_schema, attributes, closed=True, role=output_role)

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
                resource_version_schema = copy.deepcopy(resource_schema)
                handle_attributes(resource_version_schema, attributes, closed=True, role=output_role)
                resource_schema["properties"].update({
                    "versionsurl": {"type": "string"},
                    "versionscount": {"type": "integer"},
                    "versions": {
                        "type": "object",
                        "additionalProperties": resource_version_schema,
                    },
                })

            meta_properties = {
                name: copy.deepcopy(json_common_attributes[name])
                for name in ("self", "xid", "epoch", "labels", "createdat", "modifiedat")
            }
            meta_properties.update({name: {} for name in (
                resource_name + "id", "shortself", "xref", "readonly",
                "compatibility", "deprecated", "defaultversionid",
                "defaultversionurl", "defaultversionsticky",
            )})
            meta_schema = {"type": "object", "properties": meta_properties}
            handle_attributes(
                meta_schema, resource.get("metaattributes", {}), closed=True, role=output_role
            )
            resource_schema["properties"].update({
                "meta": meta_schema, "metaurl": {"type": "string"},
            })
            handle_attributes(
                resource_schema, attributes, closed=True, role=output_role,
                partial=resource.get("maxversions", -1) != 1,
            )

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
        props.update(copy.deepcopy(common_properties))
        props["deprecated"] = {}
        props["constraints"] = {}
        group_schema = {
            "type": "object",
            "properties": props
        }
        for resource_collection_name, resource_collection_schema in resource_collection_properties.items():
            group_schema["properties"][resource_collection_name] = resource_collection_schema
            group_schema["properties"][resource_collection_name + "url"] = {"type": "string"}
            group_schema["properties"][resource_collection_name + "count"] = {"type": "integer"}
        attributes = group.get("attributes", {})
        handle_attributes(group_schema, attributes, closed=True, role=output_role)
        # For OpenAPI: flat keys, for JSON Schema: nested structure
        if for_openapi:
            schema_definitions[group_name] = group_schema
        else:
            if f"{group_name}-schema" not in schema_definitions:
                schema_definitions[f"{group_name}-schema"] = {}
            schema_definitions[f"{group_name}-schema"][group_name] = group_schema
    handle_attributes(
        root_schema, model_definition.get("attributes", {}), closed=True, role=output_role
    )
    if for_openapi:
        if meta_template is None:
            path = os.path.join(
                os.path.dirname(__file__), "..", "core", "templates",
                "xregistry_openapi_template.json",
            )
            with open(path, encoding="utf-8") as source:
                meta_template = json.load(source)["components"]["schemas"]["Meta"]
        for group in model_definition.get("groups", {}).values():
            for resource in group.get("resources", {}).values():
                resource = resolve_resource(group, resource)
                name = resource["singular"]
                attributes = resource.get("attributes", {})
                for suffix, definition in meta_schemas(resource).items():
                    schema_definitions[name + "Meta" + suffix] = definition
                schema_definitions[name]["properties"]["meta"] = {
                    "$ref": f"{reference_prefix}{name}Meta"
                }
                for role, suffix in (("write", "WriteInput"), ("patch", "PatchInput")):
                    properties = input_core(name + "id")
                    properties["versionid"] = {"type": "string"}
                    if resource.get("hasdocument", True):
                        properties.update({
                            name: {},
                            name + "base64": {"type": "string"},
                            name + "url": {"type": "string", "format": "uri-reference"},
                        })
                    version = entity_input(
                        copy.deepcopy(properties), attributes, role, identity=name + "id"
                    )
                    if "required" in version:
                        version["required"] = [
                            field for field in version["required"] if field != "versionid"
                        ]
                    schema_definitions[name + "Version" + suffix] = version
                    properties["versions"] = {
                        "type": "object",
                        "additionalProperties": {
                            "$ref": f"{reference_prefix}{name}Version{suffix}"
                        },
                    }
                    properties["meta"] = {
                        "$ref": f"{reference_prefix}{name}Meta{suffix}"
                    }
                    value = entity_input(properties, attributes, role, identity=name + "id")
                    value.pop("required", None)
                    alias_selected = {
                        "properties": {"meta": {
                            "properties": {"xref": {"type": "string"}},
                            "required": ["xref"],
                        }},
                        "required": ["meta"],
                    }
                    client_required = required_input(attributes, (name + "id", "versionid"))
                    if role == "write" and client_required:
                        value["anyOf"] = [
                            {"required": ["versions"]},
                            alias_selected,
                            {"required": client_required},
                        ]
                    value.setdefault("allOf", []).append({"anyOf": [
                        {"not": alias_selected},
                        {
                            "properties": {name + "id": {}, "meta": {}},
                            "additionalProperties": False,
                        },
                    ]})
                    if role == "patch":
                        value["nullable"] = True
                        version["nullable"] = True
                    schema_definitions[name + suffix] = value

        for group in model_definition.get("groups", {}).values():
            resources = dict(group.get("resources", {}))
            for imported in group.get("ximportresources", []):
                source_group, plural = imported.split("/")[1:]
                resources[plural] = model_definition["groups"][source_group]["resources"][plural]
            for role, suffix in (("write", "WriteInput"), ("patch", "PatchInput")):
                properties = input_core(group["singular"] + "id")
                for plural, definition in resources.items():
                    resource = resolve_resource(group, definition)
                    properties[plural] = {
                        "type": "object",
                        "additionalProperties": {
                            "$ref": f"{reference_prefix}{resource['singular']}{suffix}"
                        },
                    }
                value = entity_input(
                    properties, group.get("attributes", {}), role,
                    identity=group["singular"] + "id",
                )
                if role == "patch":
                    value["nullable"] = True
                schema_definitions[group["singular"] + suffix] = value

        for role, suffix in (("write", "WriteInput"), ("patch", "PatchInput")):
            properties = input_core("registryid")
            properties.update({
                "specversion": {"description": "Server-controlled; ignored in requests."},
                "model": {"description": "Server-controlled; ignored in requests."},
                "modelsource": {"type": "object", "nullable": True},
                "capabilities": {"type": "object", "nullable": True},
            })
            dynamic_properties = copy.deepcopy(properties)
            for group in model_definition.get("groups", {}).values():
                properties[group["plural"]] = {
                    "type": "object",
                    "additionalProperties": {
                        "$ref": f"{reference_prefix}{group['singular']}{suffix}"
                    },
                }
            normal = entity_input(
                properties, model_definition.get("attributes", {}), role,
                identity="registryid", server_fields=("specversion", "model"),
            )
            normal.setdefault("allOf", []).append({
                "not": {"required": ["modelsource"]}
            })
            schema_definitions["Registry" + suffix] = {
                "type": "object",
                "description": normal["description"],
                "oneOf": [
                    normal,
                    {
                        "type": "object", "properties": dynamic_properties,
                        "required": ["modelsource"],
                        "description": (
                            "The request changes or resets the model. The server "
                            "validates all model-dependent data against the resulting "
                            "model; the old generated model is not authoritative."
                        ),
                    },
                ],
            }
    return schema



def generate_json_structure(model_definition, schema_id='', schema_name='') -> dict:
    """Generate a native JSON Structure schema for an xRegistry document."""
    definitions = {}
    requires_validation = False

    def closed_empty_schema():
        nonlocal requires_validation
        requires_validation = True
        return {"type": "map", "values": {"type": "any"}, "maxEntries": 0}

    def identifier(wire_name):
        words = [word for word in re.split(r'[^A-Za-z0-9]+', wire_name) if word]
        logical_name = words[0] + ''.join(
            word[:1].upper() + word[1:] for word in words[1:]
        ) if words else "value"
        if logical_name[0].isdigit():
            logical_name = "value" + logical_name
        return logical_name

    def type_identifier(wire_name):
        logical_name = identifier(wire_name)
        return logical_name[:1].upper() + logical_name[1:]

    def reference(namespace, type_name):
        return {"type": {"$ref": f"#/definitions/{namespace}/{type_name}"}}

    def add_definition(namespace, suggested_name, schema):
        namespace_definitions = definitions.setdefault(namespace, {})
        type_name = type_identifier(suggested_name)
        existing = namespace_definitions.get(type_name)
        if existing is not None and existing != schema:
            raise ValueError(
                f"Conflicting JSON Structure definition: {namespace}/{type_name}"
            )
        if existing is None:
            namespace_definitions[type_name] = schema
        return type_name

    def apply_annotations(schema, definition):
        if definition.get("description"):
            schema["description"] = definition["description"]
        if definition.get("enum") and definition.get("strict", True):
            schema["enum"] = copy.deepcopy(definition["enum"])

    def value_schema(definition, namespace, suggested_name, require_reference=False):
        value_type = definition["type"]
        if value_type == "object":
            schema = object_schema(
                definition.get("attributes", {}), namespace, suggested_name
            )
            apply_annotations(schema, definition)
            if require_reference:
                type_name = add_definition(namespace, suggested_name, schema)
                return reference(namespace, type_name)
            return schema
        if value_type == "map":
            item = definition.get("item", {"type": "any"})
            schema = {
                "type": "map",
                "values": value_schema(item, namespace, suggested_name + "Value", True)
            }
            apply_annotations(schema, definition)
            return schema
        if value_type == "array":
            item = definition.get("item", {"type": "any"})
            schema = {
                "type": "array",
                "items": value_schema(item, namespace, suggested_name + "Item", True)
            }
            if definition.get("enum"):
                schema["items"]["enum"] = copy.deepcopy(definition["enum"])
            apply_annotations(schema, definition)
            return schema
        if value_type not in json_structure_type_mapping:
            raise ValueError(f"Unsupported JSON Structure type: {value_type}")
        schema = {"type": json_structure_type_mapping[value_type]}
        apply_annotations(schema, definition)
        return schema

    def collect_attributes(attributes):
        collected = dict(attributes)
        for definition in attributes.values():
            for condition in definition.get("ifvalues", {}).values():
                for sibling_name, sibling_definition in condition.get(
                    "siblingattributes", {}
                ).items():
                    collected.setdefault(sibling_name, sibling_definition)
        return collected

    def object_schema(attributes, namespace, owner_name):
        attributes = collect_attributes(attributes)
        properties = {}
        required = []
        used_names = {}
        wildcard = attributes.get("*")
        for wire_name, definition in attributes.items():
            if wire_name == "*":
                continue
            logical_name = identifier(wire_name)
            if logical_name in used_names and used_names[logical_name] != wire_name:
                raise ValueError(
                    f"JSON Structure name collision: '{wire_name}' and "
                    f"'{used_names[logical_name]}' both map to '{logical_name}'"
                )
            used_names[logical_name] = wire_name
            property_schema = value_schema(
                definition, namespace, owner_name + type_identifier(logical_name)
            )
            if logical_name != wire_name:
                property_schema["altnames"] = {"json": wire_name}
            properties[logical_name] = property_schema
            if definition.get("required") is True and "default" not in definition:
                required.append(logical_name)
        if not properties:
            if wildcard is None:
                return closed_empty_schema()
            return {
                "type": "map",
                "values": value_schema(wildcard, namespace, owner_name + "Value", True),
            }
        additional_properties = wildcard is not None and wildcard["type"] == "any"
        if wildcard is not None and not additional_properties:
            additional_properties = value_schema(
                wildcard, namespace, owner_name + "AdditionalProperty", True
            )
        schema = {
            "type": "object",
            "properties": properties,
            "additionalProperties": additional_properties
        }
        if required:
            schema["required"] = required
        return schema

    common_attributes = {
        "name": {"type": "string", "description": "Name of the object"},
        "epoch": {"type": "uinteger", "description": "Optimistic concurrency update counter"},
        "self": {"type": "url", "description": "URL of the object"},
        "xid": {"type": "xid", "description": "XID of the object"},
        "description": {"type": "string", "description": "Description of the object"},
        "documentation": {"type": "url", "description": "Documentation URL"},
        "labels": {"type": "map", "item": {"type": "string"}},
        "createdat": {"type": "timestamp", "description": "Creation time"},
        "modifiedat": {"type": "timestamp", "description": "Modification time"}
    }
    root_properties = {}
    group_metadata = {}
    groups = model_definition.get("groups", {})

    for group_key, group in groups.items():
        group_plural = group.get("plural", group_key)
        namespace = type_identifier(group_plural)
        resource_collections = {}
        for resource_key, unresolved_resource in group.get("resources", {}).items():
            resource = resolve_resource(group, unresolved_resource)
            resource_plural = resource.get("plural", resource_key)
            resource_singular = resource["singular"]
            resource_type_name = type_identifier(resource_singular)
            identity_attributes = {
                resource_singular + "id": {
                    "type": "string",
                    "description": f"ID of the {resource_singular} object"
                },
                **common_attributes
            }
            resource_attributes = dict(identity_attributes)
            if resource.get("maxversions", -1) == 1:
                resource_attributes.update(resource.get("attributes", {}))
            resource_schema = object_schema(
                resource_attributes, namespace, resource_type_name
            )
            if resource.get("hasdocument", True):
                resource_schema["properties"].update({
                    resource_singular: {
                        "type": "any",
                        "description": f"Embedded {resource_singular} document"
                    },
                    resource_singular + "base64": {
                        "type": "binary",
                        "description": f"Base64-encoded {resource_singular} document"
                    },
                    resource_singular + "url": {
                        "type": "uri",
                        "description": f"URL of the {resource_singular} document"
                    }
                })
            if resource.get("maxversions", -1) != 1:
                version_type_name = resource_type_name + "Version"
                version_schema = object_schema(
                    {
                        "versionid": {
                            "type": "string",
                            "description": f"ID of the {resource_singular} version"
                        },
                        **identity_attributes,
                        **resource.get("attributes", {})
                    },
                    namespace,
                    version_type_name
                )
                if resource.get("hasdocument", True):
                    version_schema["properties"].update({
                        resource_singular: {"type": "any"},
                        resource_singular + "base64": {"type": "binary"},
                        resource_singular + "url": {"type": "uri"}
                    })
                add_definition(namespace, version_type_name, version_schema)
                resource_schema["properties"].update({
                    "versionsurl": {"type": "uri"},
                    "versionscount": {"type": "uint32"},
                    "versions": {
                        "type": "map",
                        "values": reference(namespace, version_type_name)
                    }
                })
            add_definition(namespace, resource_type_name, resource_schema)
            resource_collections[resource_plural] = {
                "type": "map",
                "values": reference(namespace, resource_type_name)
            }
        group_metadata[group_plural] = {
            "group": group,
            "namespace": namespace,
            "resource_collections": resource_collections
        }

    for group_plural, metadata in group_metadata.items():
        group = metadata["group"]
        namespace = metadata["namespace"]
        group_singular = group["singular"]
        group_type_name = type_identifier(group_singular)
        group_schema = object_schema(
            {
                group_singular + "id": {
                    "type": "string",
                    "description": f"ID of the {group_singular} object"
                },
                **common_attributes,
                **group.get("attributes", {})
            },
            namespace,
            group_type_name
        )
        group_schema["properties"].update(metadata["resource_collections"])
        for resource_xid in group.get("ximportresources", []):
            source_group_plural, source_resource_plural = resource_xid.split("/")[1:]
            source_metadata = group_metadata[source_group_plural]
            source_resource = resolve_resource(
                groups[source_group_plural],
                groups[source_group_plural]["resources"][source_resource_plural]
            )
            source_resource_type = type_identifier(source_resource["singular"])
            group_schema["properties"][source_resource_plural] = {
                "type": "map",
                "values": reference(source_metadata["namespace"], source_resource_type)
            }
        add_definition(namespace, group_type_name, group_schema)
        root_properties[group_plural] = {
            "type": "map",
            "values": reference(namespace, group_type_name)
        }

    root_schema = {
        "type": "object", "properties": root_properties,
        "additionalProperties": False,
    } if root_properties else closed_empty_schema()
    extensions = ["JSONStructureAlternateNames"]
    if requires_validation:
        extensions.append("JSONStructureValidation")
    return {
        "$schema": "https://json-structure.org/meta/extended/v0/#",
        "$id": schema_id or "https://xregistry.io/schemas/xregistry.struct.json",
        "$uses": extensions,
        "name": type_identifier(schema_name or "xRegistryDocument"),
        **root_schema,
        "definitions": definitions
    }


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
    """Expand local includes without mutating source data; limit chains to 64."""
    documents = {}

    def expand(value, directory, document, document_id, active):
        if isinstance(value, list):
            return [
                expand(item, directory, document, document_id, active)
                for item in value
            ]
        if not isinstance(value, dict):
            return value

        if "$include" in value and "$includes" in value:
            raise ValueError("$include and $includes cannot be used together")
        references = []
        if "$include" in value:
            references = [value["$include"]]
        elif "$includes" in value:
            references = value["$includes"]
            if not isinstance(references, list):
                raise ValueError("$includes must be an array of local references")
        if any(not isinstance(reference, str) for reference in references):
            raise ValueError("Each include reference must be a string")

        result = {
            key: expand(item, directory, document, document_id, active)
            for key, item in value.items()
            if key not in ("$include", "$includes")
        }
        for reference in references:
            file_ref, _, fragment = reference.partition("#")
            # URI schemes and UNC paths would leave the local-file environment.
            drive, _ = os.path.splitdrive(file_ref)
            if (file_ref.startswith(("//", "\\\\"))
                    or (not drive and urlsplit(file_ref).scheme)):
                raise ValueError(f"Include requires a local file: {reference!r}")
            target_document = document
            target_id = document_id
            target_directory = directory
            if file_ref:
                target_id = os.path.normcase(os.path.realpath(
                    os.path.join(directory, file_ref.replace("/", os.sep))
                ))
                target_directory = os.path.dirname(target_id)
                if target_id not in documents:
                    with open(target_id, encoding="utf-8") as source:
                        documents[target_id] = json.load(source)
                target_document = documents[target_id]
            try:
                if re.search(r"%(?![0-9A-Fa-f]{2})", fragment):
                    raise ValueError("Invalid percent escape")
                pointer = unquote(fragment, encoding="utf-8", errors="strict")
                target = resolve_pointer(target_document, pointer)
                if isinstance(target, EndOfList):
                    raise ValueError("Array append position is not a value")
            except (JsonPointerException, ValueError) as error:
                raise ValueError(
                    f"Invalid include pointer in {reference!r}: {error}"
                ) from error
            if not isinstance(target, dict):
                raise ValueError(f"Include target must be an object: {reference!r}")
            key = (target_id, pointer)
            if key in active:
                raise ValueError(f"Include cycle at {reference!r}")
            if len(active) >= 64:
                raise ValueError(f"Maximum include depth of 64 exceeded: {reference!r}")
            included = expand(
                target, target_directory, target_document, target_id,
                active + (key,),
            )
            for name, item in included.items():
                result.setdefault(name, item)
        return result

    return expand(node, os.path.realpath(basedir), node, None, ())


# read model definition from file ../schema/model.json
# make the path relative to this script file, irrespective of working directory

def main():
    parser = argparse.ArgumentParser(description='Generate JSON schema from model definition')
    parser.add_argument('--type', type=str, help='type of document to generate', choices=['json-schema', 'json-structure', 'avro-schema', 'openapi'], default='json-schema')
    parser.add_argument('--output', type=str, help='Path for output file', default='', required=False)
    parser.add_argument('--schema-id', type=str, help='URI for the $id field in the schema', default='', required=False)
    parser.add_argument('--schema-name', type=str, help='Root type name for JSON Structure output', default='', required=False)
    parser.add_argument('input_files', type=str, help='Path to input files', nargs='+')

    args = parser.parse_args()

    json_schema = None
    model_definition = { "groups": {} }
    for input_file in args.input_files:
        with open(input_file, encoding='utf-8') as file:
            print(f"> {input_file} as '{args.type}'")
            input_definition = json.load(file)
            input_definition = resolve_imports(os.path.dirname(input_file), input_definition)
            for name, definition in input_definition.get("attributes", {}).items():
                model_definition.setdefault("attributes", {}).setdefault(name, definition)
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
            with open(args.output, 'w', encoding='utf-8', newline='\n') as of:
                json.dump(json_schema, of, indent=2)
                of.write('\n')
        else:
            print(json.dumps(json_schema, indent=2))
    elif (args.type == 'json-structure'):
        json_structure = generate_json_structure(
            model_definition,
            schema_id=args.schema_id,
            schema_name=args.schema_name
        )
        if args.output:
            with open(args.output, 'w', encoding='utf-8', newline='\n') as of:
                json.dump(json_structure, of, indent=2)
        else:
            print(json.dumps(json_structure, indent=2))
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
            with open(args.output, 'w', encoding='utf-8', newline='\n') as of:
                json.dump(openapi, of, indent=2)
                of.write('\n')
        else:
            print(json.dumps(openapi, indent=2))


if __name__ == '__main__':
    main()
