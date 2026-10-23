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


def nested_entity_schema(value):
    return {"allOf": [value, {"not": {"required": ["$schema"]}}]}


# The Core "scalar" data types; `any` is excluded because its runtime value may
# be a complex type. Only these carry an `enum` value set.
core_scalar_types = frozenset({
    "boolean", "decimal", "integer", "string", "timestamp", "uinteger",
    "uri", "uriabsolute", "urirelative", "uritemplate",
    "url", "urlabsolute", "urlrelative", "xid", "xidtype",
})


def _same_json_type(left, right):
    """JSON type identity that keeps Boolean distinct from integer."""
    if isinstance(left, bool) != isinstance(right, bool):
        return False
    if not isinstance(left, bool) and isinstance(left, (int, float)):
        return isinstance(right, (int, float))
    return type(left) is type(right)


def _enum_contains(values, value):
    return any(
        _same_json_type(member, value) and member == value for member in values
    )


def _is_scalar_value(type_name, value):
    if type_name == "boolean":
        return isinstance(value, bool)
    if type_name in ("integer", "uinteger"):
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "decimal":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, str)


def _selector_spelling(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def effective_enum(definition):
    """The value set a Core scalar attribute actually restricts, if any.

    An absent or empty `enum`, a non-scalar type, or `strict` other than true
    leaves the attribute unrestricted; `strict` defaults to true.
    """
    if not isinstance(definition, dict):
        return None
    if definition.get("type") not in core_scalar_types:
        return None
    values = definition.get("enum")
    if not isinstance(values, list) or not values:
        return None
    if definition.get("strict", True) is not True:
        return None
    return values


def validate_scalar_enum_aspects(name, definition, kind="attribute"):
    """Check the source aspects an effective strict enum governs."""
    if kind == "attribute":
        reject_container_value_set(name, definition)
    values = effective_enum(definition)
    if values is None:
        return None
    type_name = definition["type"]
    for value in values:
        if not _is_scalar_value(type_name, value):
            raise ValueError(
                f"enum value {value!r} of {kind} {name!r} is not a valid "
                f"{type_name}"
            )
    if definition.get("default") is not None and not _enum_contains(
        values, definition["default"]
    ):
        raise ValueError(
            f"default {definition['default']!r} of {kind} {name!r} is not one "
            "of its strict enum values"
        )
    spellings = {_selector_spelling(value).casefold() for value in values}
    for selector in definition.get("ifvalues", {}):
        if selector.casefold() not in spellings:
            raise ValueError(
                f"ifvalues selector {selector!r} of {kind} {name!r} is not one "
                "of its strict enum values"
            )
    return values


def item_enum(name, item):
    """The value set a Core array element or map value actually restricts.

    Only scalar items carry `enum`; containers recurse through their own
    `item`. A Boolean `strict` alone has no effect. Declared values must have
    the item's scalar kind even when membership is advisory.
    """
    if not isinstance(item, dict):
        return None
    if "strict" in item and not isinstance(item["strict"], bool):
        raise ValueError(f"strict of item {name!r} must be a Boolean")
    if "enum" not in item:
        return None
    type_name = item.get("type")
    if type_name not in core_scalar_types:
        raise ValueError(
            f"enum of item {name!r} is defined for scalar item types "
            f"only, not {type_name!r}"
        )
    values = item.get("enum")
    if isinstance(values, list):
        # `strict` false makes membership advisory, not the value kinds.
        for value in values:
            if not _is_scalar_value(type_name, value):
                raise ValueError(
                    f"enum value {value!r} of item {name!r} is not a valid "
                    f"{type_name}"
                )
    return validate_scalar_enum_aspects(name, item, kind="item")


def reject_container_value_set(name, definition):
    """Containers restrict their scalar elements, not their own value."""
    if not isinstance(definition, dict):
        return
    type_name = definition.get("type")
    if type_name not in core_scalar_types and "enum" in definition:
        raise ValueError(
            f"enum of attribute {name!r} is defined for scalar types "
            f"only, not {type_name!r}; an array or map restricts its "
            "elements through item.enum"
        )


# Avro restricts a value only through a named enum of unique string symbols.
avro_symbol_pattern = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def avro_enum_symbols(values):
    """The Avro `enum` symbol set a Core value set maps to, when one exists.

    Avro restricts a value only through named string symbols, so a Core value
    set that is not expressible as legal symbol names has no Avro equivalent
    and is projected as the plain mapped type, leaving the restriction
    expressed in the dialects that can carry it. A repeated value names the
    same symbol, so it is folded in place rather than losing the restriction.
    """
    if not values:
        return None
    symbols = []
    for value in values:
        if not isinstance(value, str) or not avro_symbol_pattern.match(value):
            return None
        if value not in symbols:
            symbols.append(value)
    return symbols


def _static_scalar_attribute(attributes, path, where):
    """Walk a constraint path through statically defined object attributes."""
    node = attributes
    for index, segment in enumerate(path):
        if segment == "*" or not isinstance(node, dict) or segment not in node:
            raise ValueError(
                f"Group constraint {where} does not reference a statically "
                "defined attribute"
            )
        definition = node[segment]
        if index == len(path) - 1:
            if definition.get("type") not in core_scalar_types:
                raise ValueError(
                    f"Group constraint {where} must reference a scalar attribute"
                )
            return definition
        if definition.get("type") != "object":
            raise ValueError(
                f"Group constraint {where} may only traverse object attributes"
            )
        node = definition.get("attributes", {})
    raise ValueError(f"Group constraint {where} has an empty attribute path")


def _constraint_overlay(attribute, constraint, where):
    """The static restriction a single Group constraint adds, if any."""
    type_name = attribute["type"]
    strict_base = effective_enum(attribute) or []
    values = constraint.get("enum")
    values = list(values) if isinstance(values, list) else []
    for value in values:
        if not _is_scalar_value(type_name, value):
            raise ValueError(
                f"Group constraint {where} enum value {value!r} has the wrong "
                f"type for {type_name}"
            )
    if values and strict_base:
        for value in values:
            if not _enum_contains(strict_base, value):
                raise ValueError(
                    f"Group constraint {where} enum must be a subset of the "
                    "attribute's strict enum"
                )
    overlay = {}
    if values:
        overlay["enum"] = values
    if "default" in constraint:
        default = constraint["default"]
        if default is not None and not _is_scalar_value(type_name, default):
            raise ValueError(
                f"Group constraint {where} default {default!r} has the wrong "
                f"type for {type_name}"
            )
        overlay["default"] = default
    effective_values = values or strict_base
    effective_default = (
        constraint["default"] if "default" in constraint
        else attribute.get("default")
    )
    if (effective_values and effective_default is not None
            and not _enum_contains(effective_values, effective_default)):
        raise ValueError(
            f"Group constraint {where} leaves default {effective_default!r} "
            "outside the effective enum"
        )
    return overlay


def _group_resource_by_plural(group, model_definition, plural):
    for key, resource in group.get("resources", {}).items():
        if resource.get("plural", key) == plural:
            return resolve_resource(group, resource)
    for imported in group.get("ximportresources", []):
        parts = imported.split("/")[1:]
        if len(parts) == 2 and parts[1] == plural:
            source_group = model_definition.get("groups", {}).get(parts[0], {})
            source = source_group.get("resources", {}).get(parts[1])
            if source is not None:
                return resolve_resource(source_group, source)
    return None


def static_group_constraints(group, model_definition):
    """Statically resolvable Group constraint overlays, keyed by Resource plural.

    Only scalar attributes reached through statically defined object attributes
    are eligible. The dynamic `equals` comparison against actual Group instance
    values, and xref graph enforcement, stay outside static schema generation.
    """
    overlays = {}
    for key, constraint in (group.get("constraints") or {}).items():
        plural, _, dotted = key.partition(".")
        where = repr(key)
        if not dotted:
            raise ValueError(f"Group constraint {where} has no attribute path")
        resource = _group_resource_by_plural(group, model_definition, plural)
        if resource is None:
            raise ValueError(
                f"Group constraint {where} does not reference a Resource type of "
                "this Group"
            )
        path = tuple(dotted.split("."))
        attribute = _static_scalar_attribute(
            resource.get("attributes", {}), path, where
        )
        overlay = _constraint_overlay(attribute, constraint, where)
        if overlay:
            overlays.setdefault(plural, {})[path] = overlay
    return overlays


def constraint_overlay_schema(overlays, nullable=False):
    """A narrowing schema for constrained paths of one Resource entity."""
    root = {}
    for path, overlay in overlays.items():
        node = root
        for segment in path[:-1]:
            node = node.setdefault("properties", {}).setdefault(segment, {})
        leaf = node.setdefault("properties", {}).setdefault(path[-1], {})
        if "enum" in overlay:
            values = copy.deepcopy(overlay["enum"])
            if nullable and None not in values:
                values.append(None)
            leaf["enum"] = values
        if "default" in overlay:
            leaf["default"] = copy.deepcopy(overlay["default"])
    return root


def apply_constraint_overlays(schema, overlays):
    """Narrow an entity schema this Group alone owns, in place."""
    for path, overlay in overlays.items():
        node = schema
        for segment in path:
            properties = node.get("properties")
            if not isinstance(properties, dict) or segment not in properties:
                node = None
                break
            node = properties[segment]
        if node is None:
            continue
        if "enum" in overlay:
            values = copy.deepcopy(overlay["enum"])
            if node.get("nullable") is True and None not in values:
                values.append(None)
            node["enum"] = values
        if "default" in overlay and "default" in node:
            node["default"] = copy.deepcopy(overlay["default"])


def constrained_reference(reference, overlays, nullable=False):
    """Reference a shared Resource definition without altering it."""
    if not overlays:
        return reference
    return {"allOf": [
        reference,
        constraint_overlay_schema(overlays, nullable=nullable),
        {"properties": {"versions": {"additionalProperties": constraint_overlay_schema(
            overlays, nullable=nullable
        )}}},
    ]}



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

    def version_type_reference(resource):
        # A single-Version Resource has no separate Version response definition.
        name = resource["singular"]
        suffix = "" if resource.get("maxversions", -1) == 1 else "Version"
        return f"#/components/schemas/{name}{suffix}"

    def document_body(path_item, name):
        # Core routes the domain-specific document through the bare Resource URL;
        # `$details` selects the xRegistry metadata. See core/http.md, "Resource
        # Metadata vs Resource Document".
        description = (
            f"The domain-specific {name} document. Any JSON value here is "
            "business content, not xRegistry metadata; metadata is addressed "
            "through the $details suffix."
        )
        for method in ("get", "put", "post"):
            operation = path_item.get(method, {})
            messages = [
                message for status, message in operation.get("responses", {}).items()
                if status.startswith("2")
            ]
            if "requestBody" in operation:
                messages.append(operation["requestBody"])
            for message in messages:
                content = message.get("content", {})
                if "application/json" in content:
                    content["application/json"]["schema"] = {"description": description}

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
                replace_refs(details_template_copy, "{%-resourceVersionTypeReference-%}", version_type_reference(resource))
                replace_refs(details_template_copy, "{%-resourceTypeReference-%}", f"#/components/schemas/{resource['singular']}")
                replace_refs(details_template_copy, "{%-groupTypeReference-%}", f"#/components/schemas/{group['singular']}")
                replace_ops(details_template_copy, "{%-resourceNameSingular-%}", f"{pascal(group['singular'])}{pascal(resource['singular'])}")
                openapi["paths"][f"/{group['plural']}/{{groupid}}/{resource['plural']}/{{resourceid}}$details"]= details_template_copy
            for ximportresources_xid in group.get("ximportresources", []):
                xid_group_plural, xid_resource_plural = ximportresources_xid.split("/")[1:]
                source_group = model_definition["groups"][xid_group_plural]
                source_resource = resolve_resource(
                    source_group, source_group["resources"][xid_resource_plural]
                )
                xid_resource_singular = source_resource["singular"]
                xid_group_singular = source_group["singular"]
                details_template_copy = copy.deepcopy(details_template)
                replace_refs(details_template_copy, "{%-resourceVersionTypeReference-%}", version_type_reference(source_resource))
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
            "additionalProperties": nested_entity_schema({
                "$ref": f"#/components/schemas/{group_singular}"
            }),
            "nullable": True
            }

        for method, name in (("put", "RegistryWriteInput"), ("patch", "RegistryPatchInput")):
            openapi["paths"]["/"][method]["requestBody"]["content"]["application/json"]["schema"] = {
                "$ref": f"#/components/schemas/{name}"
            }
        for group in model_definition.get("groups", {}).values():
            group_path = f"/{group['plural']}/{{groupid}}"
            openapi["paths"][group_path]["put"]["requestBody"]["content"]["application/json"]["schema"] = {
                "$ref": f"#/components/schemas/{group['singular']}WriteInput"
            }
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
                resource_path = f"{group_path}/{plural}/{{resourceid}}"
                has_document = resource.get("hasdocument", True)
                metadata_paths = [resource_path + "$details"]
                if not has_document:
                    # Core treats the suffix as absent for metadata-only types.
                    metadata_paths.append(resource_path)
                for metadata_path in metadata_paths:
                    metadata_operations = openapi["paths"][metadata_path]
                    for method, role_suffix in (
                        ("put", "WriteInput"), ("post", "ResourceVersionWriteInput"),
                    ):
                        metadata_operations[method]["requestBody"]["content"]["application/json"]["schema"] = {
                            "$ref": f"#/components/schemas/{name}{role_suffix}"
                        }
                if has_document:
                    document_body(openapi["paths"][resource_path], name)
                versions = openapi["paths"][resource_path + "/versions"]["post"]
                replace_refs(
                    versions["requestBody"],
                    f"#/components/schemas/{name}",
                    f"#/components/schemas/{name}VersionWriteInput",
                )
                version_map = versions["requestBody"]["content"]["application/json"]["schema"]
                version_map["additionalProperties"] = nested_entity_schema(
                    version_map["additionalProperties"]
                )
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

    def handle_item(resource_schema, type, item, role=None,
                    name="item"):
        restriction = item_enum(name, item)
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
                if restriction is not None:
                    attr_schema["enum"] = copy.deepcopy(restriction)
                resource_schema["additionalProperties"] = attr_schema
                if item["type"] == "object" or item["type"] == "map" or item["type"] == "array":
                    if "item" in item:
                        handle_item(resource_schema["additionalProperties"], item["type"], item["item"], role=role, name=name)
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
                if restriction is not None:
                    attr_schema["enum"] = copy.deepcopy(restriction)
                resource_schema["items"] = attr_schema
                if item["type"] == "object" or item["type"] == "map" or item["type"] == "array":
                    if "item" in item:
                        handle_item(resource_schema["items"], item["type"], item["item"], role=role, name=name)



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
        active_names = copy.deepcopy(names)
        wildcards = []
        active_wildcards = []
        resource_schema.setdefault("properties", {})
        request_role = role in ("write", "patch")
        for attr_name, attr_props in attributes.items():
            restriction = validate_scalar_enum_aspects(attr_name, attr_props)
            ignored = request_role and attr_props.get("readonly", False)
            if ignored:
                attr_schema = ignored_input()
            elif attr_props["type"] == "object":
                attr_schema = {"type": "object", "description": "", "properties": {}}
                handle_attributes(
                    attr_schema, attr_props.get("attributes", {}), closed=True, role=role
                )
            else:
                attr_schema = copy.deepcopy(json_type_mapping[attr_props["type"]])

            if restriction is not None and not ignored:
                attr_schema["enum"] = copy.deepcopy(restriction)

            if not ignored and "description" in attr_props:
                attr_schema["description"] = attr_props["description"]
            if "description" in attr_schema and attr_schema["description"] == "":
                del attr_schema["description"]

            if not ignored and attr_props["type"] in ("object", "map", "array"):
                if "item" in attr_props:
                    # Pass enum values if this is an array with enum constraint
                    handle_item(attr_schema, attr_props["type"], attr_props["item"], role=role, name=attr_name)

            if role == "response" and attr_props.get("readonly", False):
                attr_schema["readOnly"] = True
            if not ignored and role in ("response", "write") and "default" in attr_props:
                attr_schema["default"] = copy.deepcopy(attr_props["default"])
            if request_role and not ignored and (
                not attr_props.get("required", False) or "default" in attr_props
            ):
                attr_schema["nullable"] = True
                # A permitted reset must stay expressible next to the value set.
                if "enum" in attr_schema and None not in attr_schema["enum"]:
                    attr_schema["enum"] = attr_schema["enum"] + [None]
            if attr_name == "*":
                if "ifvalues" in attr_props:
                    raise ValueError("Can't use wild card attribute name with ifvalues")
                wildcards.append(({}, attr_schema))
                if request_role:
                    active_names.setdefault(attr_name, [{}])
                    active_wildcards.append(({}, attr_schema))
                continue
            names.setdefault(attr_name, []).append({})
            active_names.setdefault(attr_name, [{}])
            resource_schema["properties"][attr_name] = copy.deepcopy(attr_schema)
            if not ignored and not partial and attr_props.get("required") is True and (
                role == "response" or "default" not in attr_props
            ):
                if "required" not in resource_schema:
                    resource_schema["required"] = []
                if attr_name not in resource_schema["required"]:
                    resource_schema["required"].append(attr_name)

            if request_role:
                seen_values = set()
                for key, condition in attr_props.get("ifvalues", {}).items():
                    folded = tuple(character.casefold() for character in key)
                    if folded in seen_values:
                        raise ValueError(f"Duplicate case-insensitive ifvalues key: {key!r}")
                    seen_values.add(folded)
                    selected = {
                        "properties": {attr_name: _ifvalue_guard(attr_props["type"], key)},
                        "required": [attr_name],
                    }
                    # Omitted, reset and readonly selectors leave final state unknown.
                    possible_selection = {} if ignored else {"anyOf": [
                        selected, {"not": {"required": [attr_name]}},
                        {
                            "properties": {attr_name: {
                                "type": "string", "nullable": True, "enum": [None],
                            }},
                            "required": [attr_name],
                        },
                    ]}
                    branch = {"properties": {}}
                    child_names, child_wildcards, child_active, child_active_wildcards = handle_attributes(
                        branch, condition.get("siblingattributes", {}),
                        role=role, partial=True,
                    )
                    wildcards.extend(
                        (together(possible_selection, guard), rule)
                        for guard, rule in child_wildcards
                    )
                    for name, conditions in child_names.items():
                        value = copy.deepcopy(branch["properties"].get(name, {}))
                        if "type" in value:
                            value["nullable"] = True
                        names.setdefault(name, []).extend(
                            together(possible_selection, together(
                                guard, {"properties": {name: value}},
                            ))
                            for guard in conditions
                        )
                    if not ignored:
                        active_wildcards.extend(
                            (together(selected, guard), rule)
                            for guard, rule in child_active_wildcards
                        )
                        resource_schema.setdefault("allOf", []).append({
                            "anyOf": [{"not": selected}, branch],
                        })
                        for name, conditions in child_active.items():
                            for guard in conditions:
                                active = together(selected, guard)
                                for previous in active_names.get(name, []):
                                    resource_schema.setdefault("allOf", []).append({
                                        "not": together(previous, active),
                                    })
                                active_names.setdefault(name, []).append(active)
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
                    child_names, child_wildcards, _, _ = handle_attributes(
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
            applicable_wildcards = wildcards
            if active_wildcards and wildcards != active_wildcards:
                unknown = {"not": {"anyOf": [
                    guard for guard, _ in active_wildcards
                ]}}
                applicable_wildcards = active_wildcards + [
                    (together(unknown, guard), rule) for guard, rule in wildcards
                ]
            close_object(resource_schema, names, applicable_wildcards)
        return names, wildcards, active_names, active_wildcards

    def ignored_input():
        return {"description": "Server-controlled; ignored in requests."}

    def collection_properties(name, item, role=None):
        request_role = role in ("write", "patch")
        return {
            name: {"type": "object", "additionalProperties": nested_entity_schema(item)},
            name + "url": ignored_input() if request_role else {"type": "string"},
            name + "count": ignored_input() if request_role else {"type": "integer"},
        }

    def deprecated_schema():
        return {
            "type": "object",
            "properties": {
                "effective": {"type": "string", "format": "date-time"},
                "removal": {"type": "string", "format": "date-time"},
                "alternative": {"type": "string", "format": "uri-reference"},
                "documentation": {"type": "string", "format": "uri-reference"},
            },
            "additionalProperties": False,
        }

    def omit_required(value, excluded):
        required = [name for name in value.get("required", []) if name not in excluded]
        if required:
            value["required"] = required
        else:
            value.pop("required", None)

    def identity_alias(identity):
        return {
            "properties": {name: {} for name in (
                identity, "self", "shortself", "xid", "xref", "$schema",
            )},
            "required": [identity, "self", "xid", "xref"],
            "additionalProperties": False,
        }

    def input_core(identity):
        properties = {
            identity: {"type": "string"},
            **copy.deepcopy(common_properties),
        }
        for name in ("self", "shortself", "xid"):
            properties[name] = ignored_input()
        for name in ("name", "description", "documentation", "icon", "labels", "createdat", "modifiedat"):
            properties[name]["nullable"] = True
        properties["epoch"]["minimum"] = 0
        return properties

    server_obligations = {
        "self", "shortself", "xid", "epoch", "createdat", "modifiedat",
    }

    def required_input(attributes, identities=(), server_fields=()):
        return [
            name for name, definition in attributes.items()
            if name != "*" and definition.get("required") is True
            and not definition.get("readonly", False) and "default" not in definition
            and name not in server_obligations and name not in identities
            and name not in server_fields
        ]

    def entity_input(properties, attributes, role, identity=None, server_fields=()):
        guarded = {
            name: copy.deepcopy(properties[name])
            for name in (identity, "epoch", "versionid")
            if name in properties
        }
        ignored = {
            name: copy.deepcopy(value) for name, value in properties.items()
            if value == ignored_input()
        }
        value = {
            "type": "object", "properties": properties,
            "description": (
                "Structural request input. The server applies defaults, retained "
                "state, conditional model constraints and final creation validation."
            ),
        }
        effective_attributes = {
            name: {**definition, "readonly": True} if name in ignored else definition
            for name, definition in attributes.items()
        }
        handle_attributes(
            value, effective_attributes, closed=True, role=role, partial=role == "patch"
        )
        for name, definition in guarded.items():
            definition.pop("readOnly", None)
            value["properties"][name] = definition
        value["properties"].update(ignored)
        for name in ("createdat", "modifiedat"):
            if name in value["properties"]:
                value["properties"][name]["nullable"] = True
        supplied_by_server = server_obligations | set(server_fields) | set(ignored) | {identity}
        omit_required(value, supplied_by_server)
        return value

    def meta_schemas(resource):
        identity = resource["singular"] + "id"
        complete = copy.deepcopy(meta_template)
        properties = complete["properties"]
        properties[identity] = properties.pop("RESOURCEid")
        properties["$schema"] = copy.deepcopy(schema_hint)
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
        properties["deprecated"] = deprecated_schema()
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
            identity_alias(identity),
        ]
        complete["description"] = (
            "Completed Meta response, or the Core identity-only alias representation "
            "used for document views and inaccessible targets."
        )
        result = {"": complete}
        for role, suffix in (("write", "WriteInput"), ("patch", "PatchInput")):
            inputs = copy.deepcopy(properties)
            for name in ("self", "shortself", "xid", "defaultversionurl"):
                inputs[name] = ignored_input()
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
                    for name in (identity, "xref", "epoch", "$schema")
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


    schema_hint = {"type": "string", "format": "uri-reference"}
    common_properties = {
        **copy.deepcopy(json_common_attributes), "shortself": {},
        "icon": {"type": "string", "format": "uri"}, "$schema": schema_hint,
    }
    version_properties = {
        "versionid": {"type": "string"}, "ancestorid": {"type": "string"},
        "isdefault": {"type": "boolean"}, "contenttype": {"type": "string"},
        "format": {"type": "string"}, "formatvalidated": {"type": "boolean"},
        "formatvalidatedreason": {"type": "string"},
        "compatibilityvalidated": {"type": "boolean"},
        "compatibilityvalidatedreason": {"type": "string"},
    }
    version_readonly = (
        "isdefault", "formatvalidated", "formatvalidatedreason",
        "compatibilityvalidated", "compatibilityvalidatedreason",
    )
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
        group_constraints = static_group_constraints(group, model_definition)
        # Create a namespace folder for this group's definitions
        # For OpenAPI: use flat keys without -schema suffix
        # For JSON Schema: use nested structure with -schema suffix
        if for_openapi:
            group_definition_prefix = f"{reference_prefix}"
        else:
            group_definition_prefix = f"{reference_prefix}{group_name}-schema/"
        document_properties.update(collection_properties(
            groups_name, {"$ref": f"{group_definition_prefix}{group_name}"}
        ))
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
            resource_overlays = group_constraints.get(resource["plural"], {})
            if resource.get("maxversions", -1) != 1:
                resource_version_schema = copy.deepcopy(resource_schema)
                props = {}
                props["versionid"] = {"type": "string", "description": f"ID of the {resource_name} version"}
                props.update(copy.deepcopy(resource_version_schema["properties"]))
                props["versionid"] = {"type": "string", "description": f"ID of the {resource_name} version"}
                resource_version_schema["properties"] = props
                handle_attributes(resource_version_schema, attributes, closed=True, role=output_role)
                apply_constraint_overlays(resource_version_schema, resource_overlays)

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
                                "additionalProperties": nested_entity_schema({
                                    "$ref": f"{group_definition_prefix}{resource_name}Version"
                                    })
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
                apply_constraint_overlays(resource_version_schema, resource_overlays)
                resource_schema["properties"].update({
                    "versionsurl": {"type": "string"},
                    "versionscount": {"type": "integer"},
                    "versions": {
                        "type": "object",
                        "additionalProperties": nested_entity_schema(resource_version_schema),
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
            meta_properties["$schema"] = copy.deepcopy(schema_hint)
            meta_schema = {"type": "object", "properties": meta_properties}
            handle_attributes(
                meta_schema, resource.get("metaattributes", {}), closed=True, role=output_role
            )
            resource_schema["properties"].update({
                "meta": nested_entity_schema(meta_schema), "metaurl": {"type": "string"},
            })
            handle_attributes(
                resource_schema, attributes, closed=True, role=output_role,
                partial=resource.get("maxversions", -1) != 1,
            )
            apply_constraint_overlays(resource_schema, resource_overlays)

            # For OpenAPI: flat keys, for JSON Schema: nested structure
            if for_openapi:
                schema_definitions[resource_name] = resource_schema
            else:
                if f"{group_name}-schema" not in schema_definitions:
                    schema_definitions[f"{group_name}-schema"] = {}
                schema_definitions[f"{group_name}-schema"][resource_name] = resource_schema
            resource_collection_properties[resource["plural"]] = {
                    "type": "object",
                    "additionalProperties": nested_entity_schema({
                        "$ref": f"{group_definition_prefix}{resource_name}",
                    })
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
                    "additionalProperties": nested_entity_schema(constrained_reference(
                        {"$ref": f"{xid_group_definition_prefix}{xid_resource_singular}"},
                        group_constraints.get(xid_resource_plural, {}),
                    ))
                }

        props = {}
        props[group_name+"id"] = {"type": "string", "description": f"ID of the {group_name} object"}
        props.update(copy.deepcopy(common_properties))
        props["deprecated"] = deprecated_schema()
        props["constraints"] = {"type": "object"}
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
            group_constraints = static_group_constraints(group, model_definition)
            for resource in group.get("resources", {}).values():
                resource = resolve_resource(group, resource)
                name = resource["singular"]
                attributes = resource.get("attributes", {})
                resource_overlays = group_constraints.get(resource["plural"], {})
                for suffix, definition in meta_schemas(resource).items():
                    schema_definitions[name + "Meta" + suffix] = definition
                resource_response = schema_definitions[name]
                resource_response["properties"]["meta"] = nested_entity_schema({
                    "$ref": f"{reference_prefix}{name}Meta"
                })
                normal_response = {
                    key: resource_response.pop(key)
                    for key in ("required", "oneOf") if key in resource_response
                }
                resource_response["anyOf"] = [
                    normal_response,
                    {
                        "properties": {
                            **{field: {} for field in (
                                name + "id", "self", "shortself", "xid", "metaurl", "$schema",
                            )},
                            "meta": identity_alias(name + "id"),
                        },
                        "required": [name + "id", "self", "xid", "metaurl", "meta"],
                        "additionalProperties": False,
                    },
                ]
                for role, suffix in (("write", "WriteInput"), ("patch", "PatchInput")):
                    properties = input_core(name + "id")
                    properties.update(copy.deepcopy(version_properties))
                    for field in version_readonly:
                        properties[field] = ignored_input()
                    for field in ("contenttype", "format"):
                        properties[field]["nullable"] = True
                    if resource.get("hasdocument", True):
                        properties.update({
                            name: {},
                            name + "base64": {"type": "string"},
                            name + "url": {"type": "string", "format": "uri-reference"},
                        })
                    version = entity_input(
                        copy.deepcopy(properties), attributes, role, identity=name + "id"
                    )
                    omit_required(version, {"versionid"})
                    apply_constraint_overlays(version, resource_overlays)
                    schema_definitions[name + "Version" + suffix] = version
                    if role == "write":
                        # A POST directed at a Resource carries a single Version,
                        # but Core permits Resource-level read-only attributes in
                        # that body and requires the server to ignore them.
                        posted = copy.deepcopy(properties)
                        posted["metaurl"] = ignored_input()
                        posted["versionsurl"] = ignored_input()
                        posted["versionscount"] = ignored_input()
                        posted_version = entity_input(
                            posted, attributes, role, identity=name + "id"
                        )
                        omit_required(posted_version, {"versionid"})
                        apply_constraint_overlays(posted_version, resource_overlays)
                        posted_version["description"] = (
                            "Version input for a POST directed at the Resource. "
                            "Resource-level read-only attributes MAY be supplied "
                            "and are ignored; Resource-only mutable members are not "
                            "part of this body."
                        )
                        schema_definitions[name + "ResourceVersion" + suffix] = posted_version
                    properties.update(collection_properties(
                        "versions", {"$ref": f"{reference_prefix}{name}Version{suffix}"}, role
                    ))
                    properties["metaurl"] = ignored_input()
                    properties["meta"] = nested_entity_schema({
                        "$ref": f"{reference_prefix}{name}Meta{suffix}"
                    })
                    value = entity_input(properties, attributes, role, identity=name + "id")
                    value.pop("required", None)
                    apply_constraint_overlays(value, resource_overlays)
                    alias_selected = {
                        "properties": {"meta": {
                            "properties": {"xref": {"type": "string"}},
                            "required": ["xref"],
                        }},
                        "required": ["meta"],
                    }
                    client_required = required_input(
                        attributes, (name + "id", "versionid"),
                        [field for field, definition in properties.items() if definition == ignored_input()],
                    )
                    if role == "write" and client_required:
                        value["anyOf"] = [
                            {"required": ["versions"]},
                            alias_selected,
                            {"required": client_required},
                        ]
                    value.setdefault("allOf", []).append({"anyOf": [
                        {"not": alias_selected},
                        {
                            "properties": {name + "id": {}, "meta": {}, "$schema": {}},
                            "additionalProperties": False,
                        },
                    ]})
                    schema_definitions[name + suffix] = value

        for group in model_definition.get("groups", {}).values():
            group_constraints = static_group_constraints(group, model_definition)
            resources = dict(group.get("resources", {}))
            imported_plurals = set()
            for imported in group.get("ximportresources", []):
                source_group, plural = imported.split("/")[1:]
                resources[plural] = model_definition["groups"][source_group]["resources"][plural]
                imported_plurals.add(plural)
            for role, suffix in (("write", "WriteInput"), ("patch", "PatchInput")):
                properties = input_core(group["singular"] + "id")
                properties["deprecated"] = {**deprecated_schema(), "nullable": True}
                properties["constraints"] = {"type": "object", "nullable": True}
                for plural, definition in resources.items():
                    resource = resolve_resource(group, definition)
                    reference = {"$ref": f"{reference_prefix}{resource['singular']}{suffix}"}
                    if plural in imported_plurals:
                        reference = constrained_reference(
                            reference, group_constraints.get(plural, {}), nullable=True
                        )
                    properties.update(collection_properties(plural, reference, role))
                value = entity_input(
                    properties, group.get("attributes", {}), role,
                    identity=group["singular"] + "id",
                )
                schema_definitions[group["singular"] + suffix] = value

        for role, suffix in (("write", "WriteInput"), ("patch", "PatchInput")):
            properties = input_core("registryid")
            properties.update({
                "specversion": ignored_input(),
                "model": ignored_input(),
                "modelsource": {"type": "object", "nullable": True},
                "capabilities": {"type": "object", "nullable": True},
            })
            dynamic_properties = copy.deepcopy(properties)
            for group in model_definition.get("groups", {}).values():
                properties.update(collection_properties(
                    group["plural"], {"$ref": f"{reference_prefix}{group['singular']}{suffix}"}, role
                ))
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
        reject_container_value_set(suggested_name, definition)
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
            # Checked here; the item's own value set is annotated with its schema.
            item_enum(suggested_name, item)
            schema = {
                "type": "map",
                "values": value_schema(item, namespace, suggested_name + "Value", True)
            }
            apply_annotations(schema, definition)
            return schema
        if value_type == "array":
            item = definition.get("item", {"type": "any"})
            # Checked here; the item's own value set is annotated with its schema.
            item_enum(suggested_name, item)
            schema = {
                "type": "array",
                "items": value_schema(item, namespace, suggested_name + "Item", True)
            }
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
    enum_types = {}

    def avro_enum_type(name, symbols):
        """One shared named `enum` definition per distinct value set.

        Avro admits a named type once per schema, so an identical set reuses
        the first definition by its qualified name. A different set under the
        same base name takes the next name in the same convention, which keeps
        its membership instead of degrading to the plain mapped type.
        """
        candidate = name
        ordinal = 1
        while True:
            qualified = f"io.xregistry.{candidate}"
            known = enum_types.get(qualified)
            if known is None:
                enum_types[qualified] = symbols
                return {
                    "type": "enum",
                    "name": candidate,
                    "namespace": "io.xregistry",
                    "symbols": symbols,
                }
            if known == symbols:
                return qualified
            ordinal += 1
            candidate = f"{name}{ordinal}"

    def handle_item(resource_schema, type, item, name, prefix):
        symbols = avro_enum_symbols(item_enum(name, item))
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
                elif symbols is not None:
                    item_schema = {
                        "type": avro_enum_type(prefix+name+"EnumType", symbols)
                    }
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
                    if symbols is not None:
                        item_schema = avro_enum_type(
                            prefix+name+"EnumType", symbols)
                    resource_schema["type"]["items"] = item_schema
            else:
                raise Exception("Array item must have a type specified")


    def handle_attributes(resource_schema, attributes, type_prefix=""):
        nonlocal avro_generic_record_emitted
        for attr_name, attr_props in attributes.items():
            reject_container_value_set(attr_name, attr_props)
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
                    handle_item(attr_schema, attr_props["type"], attr_props["item"], pascal_attr_name, type_prefix)
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
            with open(args.output, 'w', encoding='utf-8', newline='\n') as of:
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
