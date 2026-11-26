"""Generate the proposed xRegistry MQTT WoT bundle from repository model.json files."""

import argparse
from functools import lru_cache
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile, ZipInfo


ROOT = Path(__file__).resolve().parents[3]
DIALECT = "https://json-schema.org/draft/2020-12/schema"
CONTEXT = [
    "https://www.w3.org/2022/wot/td/v1.1",
    {"mqv": "https://www.w3.org/2019/wot/mqtt#", "xreg": "https://xregistry.io/vocab/mqtt#"},
]
CORE_TITLE = "XRegistry"
STRING = {"type": "string"}
TEXT = {**STRING, "minLength": 1}
UINT = {"type": "integer", "minimum": 0, "maximum": 2**64 - 1}
URI = {**STRING, "pattern": r"^[A-Za-z][A-Za-z0-9+.-]*:"}
XID = {**STRING, "pattern": r"^/(?:[^/?#]+(?:/[^/?#]+)*)?$"}
BASE64 = {**STRING, "pattern": r"^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$"}
ACTIONS = {
    "read": "Reads an entity, collection, document, or Registry service.",
    "replace": "Replaces an entity, document, or writable Registry service.",
    "update": "Partially updates metadata or a writable Registry service.",
    "upsert": "Creates or updates the items supplied for the target.",
    "delete": "Deletes an entity or collection members.",
    "options": "Lists supported native actions for the addressed target.",
}
# These domain names and media-type hints are not MQTT routing rules.
DOMAIN_PROJECTIONS = {
    ("schema/model.json", "schemagroups"): ("SchemaExtensions", "application/schema+json"),
    ("workingdrafts/models/wot/model.json", "thingdescriptiongroups"):
        ("ThingDescriptionExtensions", "application/td+json"),
    ("workingdrafts/models/wot/model.json", "thingmodelgroups"):
        ("ThingModelExtensions", "application/tm+json"),
}
TYPES = {
    "any": {}, "var": {}, "boolean": {"type": "boolean"}, "string": STRING,
    "integer": {"type": "integer"}, "decimal": {"type": "number"}, "uinteger": UINT,
    "object": {"type": "object"}, "map": {"type": "object"}, "array": {"type": "array"},
    "binary": {**BASE64, "contentEncoding": "base64"}, "xid": XID,
    **{kind: {**STRING, "format": "uri-reference"} for kind in
       ("uri", "urirelative", "url", "urlrelative", "xidtype")},
    **{kind: {**URI, "format": "uri"} for kind in ("uriabsolute", "urlabsolute")},
    "uritemplate": {**STRING, "format": "uri-template"},
    **{kind: {**STRING, "format": "date-time"} for kind in ("timestamp", "datetime")},
}


def object_schema(properties, required=(), *, closed=False):
    schema = {"type": "object", "properties": properties}
    if closed:
        schema["additionalProperties"] = False
    if required:
        schema["required"] = list(required)
    return schema


def array(items):
    return {"type": "array", "items": items}


def ref(name):
    return {"$ref": f"{name}.schema.json"}


def one_of(*names):
    return {"oneOf": [{"required": [name]} for name in names]}


def schema_path(name):
    return f"./schemas/{name}.schema.json"


def thing(title, **fields):
    return {"@context": CONTEXT, "@type": "tm:ThingModel", "title": title, **fields}


def mqtt_contract():
    def closed(properties, *required):
        return object_schema(properties, required, closed=True)

    nonempty_list = {**array(TEXT), "minItems": 1}
    document = closed({"base64": BASE64, "url": URI, "contenttype": TEXT}) | one_of("base64", "url")
    document_body = closed({"document": ref("Document"), "metadata": TYPES["object"]}, "document")
    origin_fields = {"source": TEXT, "selectedxid": XID}
    origin = closed(origin_fields | {
        "revision": {"type": ["string", "null"]},
        "catalog": closed(origin_fields | {
            "advertisement": object_schema({
                "binding": TEXT, "endpoint": URI, "parameters": TYPES["object"], "priority": UINT,
            }, ("binding", "endpoint")),
        }, "source", "selectedxid", "advertisement"),
    }, "source", "selectedxid", "revision")
    result = {
        "value": {}, "location": URI, "contentlocation": URI, "origin": ref("Origin"),
        "memberorigins": {"type": "object", "additionalProperties": ref("Origin")},
        "page": ref("PageResult"), "order": {**array(TEXT), "uniqueItems": True},
    }
    error_fields = dict.fromkeys(("message", "title", "detail", "subject", "instance", "source"), STRING)
    schemas = {
        "Document": document, "DocumentValue": document_body | {"required": ["document", "metadata"]},
        "Flags": closed(dict.fromkeys(("binary", "collections", "doc"), {"const": True}) | {
            "epoch": UINT, "filter": {**array(nonempty_list), "minItems": 1},
            "ignore": nonempty_list, "inline": nonempty_list,
            "setdefaultversionid": {"type": ["string", "null"]}, "sort": TEXT, "specversion": STRING,
        }),
        "PageRequest": closed({"limit": {**UINT, "minimum": 1}, "cursor": TEXT}) | one_of("limit", "cursor"),
        "PageResult": closed({"links": array(closed({
            "rel": TEXT, "cursor": TEXT, "count": UINT, "offset": UINT, "limit": UINT,
            "expires": TYPES["timestamp"],
        }, "rel", "cursor"))}, "links"),
        "Origin": origin,
        "Error": object_schema(error_fields | {"code": TEXT, "type": URI, "args": TYPES["object"]}, ("code",)),
        "OptionsValue": closed({"operations": {
            **array({"enum": list(ACTIONS)}), "uniqueItems": True, "contains": {"const": "options"},
        }}, "operations"),
        "Reply": closed({"result": closed(result, "value"), "error": ref("Error")}) | one_of("result", "error"),
    }
    for action, value in (("Delete", {"type": "null"}), ("Options", ref("OptionsValue"))):
        fields = dict.fromkeys(("page", "order", "memberorigins", "location", "contentlocation"), False)
        schemas[f"{action}Reply"] = ref("Reply") | {
            "properties": {"result": {"properties": fields | {"value": value}}},
        }

    actions = {}
    for action, description in ACTIONS.items():
        name = action.title()
        fields = {
            "surface": {"enum": [
                "capabilities", "capabilitiesoffered", "model", "modelsource", "export", "discovery",
            ]},
            "view": {"enum": ["metadata", "document"]}, "flags": ref("Flags"),
        }
        write = action in {"replace", "update", "upsert"}
        if write or action == "delete":
            fields["body"] = TYPES["object"]
        if action in {"update", "delete"}:
            fields["view"] = {"const": "metadata"}
        if action == "read":
            fields["page"] = ref("PageRequest")
        request = closed(fields, *(("body",) if write else ()))
        output = {"xreg:schema": schema_path(f"{name}Reply" if action in {"delete", "options"} else "Reply")}
        if action in {"read", "replace", "upsert"}:
            output["xreg:documentValueSchema"] = schema_path("DocumentValue")
        if action in {"replace", "upsert"}:
            request["if"] = {"required": ["view"], "properties": {"view": {"const": "document"}}}
            request["then"] = {"properties": {"body": document_body}}
        schemas[f"{name}Request"] = request
        actions[action] = {
            "description": description, "input": {"xreg:schema": schema_path(f"{name}Request")},
            "output": output, "forms": [{
                "op": "invokeaction", "contentType": "application/json",
                "mqv:controlPacket": "publish", "mqv:qos": "1", "mqv:retain": False,
                "xreg:binding": "mqtt", "xreg:topic": f"{{topicbase}}/{action}{{target}}",
            }],
        }
    return thing(CORE_TITLE, description="Native xRegistry actions over MQTT 5.0.", actions=actions), schemas


@lru_cache(maxsize=None)
def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def expand(value, path, chain=()):
    """Resolve local Core includes relative to the file containing each directive."""
    if isinstance(value, list):
        return [expand(item, path, chain) for item in value]
    if not isinstance(value, dict):
        return value
    if "$include" in value and "$includes" in value:
        raise ValueError(f"{path}: conflicting include directives")
    result = {}
    references = [value["$include"]] if "$include" in value else value.get("$includes", [])
    for reference in references:
        parts = urlsplit(reference)
        target = (path.parent / unquote(parts.path, errors="strict")).resolve() if parts.path else path
        pointer = unquote(parts.fragment, errors="strict")
        key = (target, pointer)
        if parts.scheme or parts.netloc or parts.query or not target.is_relative_to(ROOT) or key in chain:
            raise ValueError(f"{path}: non-local or circular include: {reference}")
        source = load(target)
        if pointer:
            if not pointer.startswith("/") or re.search(r"~(?![01])", pointer):
                raise ValueError(f"{path}: invalid JSON Pointer: {reference}")
            for token in pointer[1:].split("/"):
                token = token.replace("~1", "/").replace("~0", "~")
                if isinstance(source, list) and not re.fullmatch(r"0|[1-9][0-9]*", token):
                    raise ValueError(f"{path}: invalid JSON Pointer array index: {reference}")
                source = source[int(token) if isinstance(source, list) else token]
        source = expand(source, target, (*chain, key))
        if not isinstance(source, dict):
            raise ValueError(f"{path}: include is not an object: {reference}")
        result = source | result
    return result | {k: expand(v, path, chain) for k, v in value.items() if k not in {"$include", "$includes"}}


def attribute(definition):
    kind = definition["type"]
    result = dict(TYPES[kind])
    if "item" in definition:
        result["items" if kind == "array" else "additionalProperties"] = attribute(definition["item"])
    if "attributes" in definition:
        result |= attributes(definition["attributes"])
    for key in ("description", "default"):
        if key in definition:
            result[key] = definition[key]
    if definition.get("readonly"):
        result["readOnly"] = True
    if definition.get("enum"):
        result["enum" if definition.get("strict", True) else "xreg:suggestedValues"] = definition["enum"]
    facets = definition.keys() - {
        "type", "item", "attributes", "description", "default", "readonly",
        "enum", "strict", "name", "required", "ifvalues",
    }
    if facets:
        result["xreg:facets"] = {key: definition[key] for key in sorted(facets)}
    return result


def attributes(definitions, required=True):
    result = object_schema(
        {name: attribute(definition) for name, definition in definitions.items() if name != "*"},
        [name for name, definition in definitions.items()
         if required and definition.get("required") and name != "*"],
    )
    if "*" in definitions:
        result["additionalProperties"] = attribute(definitions["*"])
    conditions = {
        name: {value: attributes(case.get("siblingattributes", {}), required)
               for value, case in definition["ifvalues"].items()}
        for name, definition in definitions.items() if definition.get("ifvalues")
    }
    if conditions:
        # Core compares serialized values case-insensitively and activates sibling definitions.
        result["xreg:ifvalues"] = conditions
    return result


def model_schema(model, groups):
    """Describe declared metadata, not operation-dependent Core validation."""
    defs = {}
    declarations = model.get("groups", {})

    def link(key):
        return {"$ref": "#/$defs/" + key.replace("~", "~0").replace("/", "~1")}

    def collection(key):
        return {"type": "object", "additionalProperties": link(key)}

    def imported_resources(group_name):
        for path in declarations[group_name].get("ximportresources", []):
            owner, name = path.removeprefix("/").split("/")
            if not path.startswith("/") or owner == group_name:
                raise ValueError(f"Invalid resource import {path} in /{group_name}")
            yield owner, name

    def resolve_resource(group_name, name, chain=()):
        key = (group_name, name)
        if key in chain:
            raise ValueError(f"Circular resource import /{group_name}/{name}")
        local = declarations[group_name].get("resources", {})
        owners = [owner for owner, imported in imported_resources(group_name) if imported == name]
        if len(owners) + (name in local) != 1:
            raise ValueError(f"Expected one Resource declaration for /{group_name}/{name}")
        if owners:
            return resolve_resource(owners[0], name, (*chain, key))
        return group_name, local[name]

    def resource(gname, name, resource_model):
        key = f"/{gname}/{name}"
        if key not in defs:
            version = resource_model.get("attributes", {})
            # Resource API views can include attributes of the default Version.
            inherited = {name: definition | {"required": False} for name, definition in version.items()}
            defs[key] = attributes(inherited | resource_model.get("resourceattributes", {}))
            defs[key]["xreg:facets"] = {k: v for k, v in resource_model.items()
                                       if k not in {"attributes", "resourceattributes", "metaattributes"}}
            defs[key]["properties"].update({
                "meta": link(key + "/meta"), "versions": collection(key + "/versions"),
            })
            defs[key + "/meta"] = attributes(resource_model.get("metaattributes", {}))
            defs[key + "/versions"] = attributes(version)
        return key

    registry = attributes(model.get("attributes", {}))
    for group_name in groups:
        group = declarations[group_name]
        key = "/" + group_name
        defs[key] = attributes(group.get("attributes", {}))
        defs[key]["xreg:facets"] = {k: v for k, v in group.items()
                                   if k not in {"attributes", "resources", "ximportresources"}}
        registry["properties"][group_name] = collection(key)
        names = dict.fromkeys([*group.get("resources", {}), *(name for _, name in imported_resources(group_name))])
        for name in names:
            owner, declaration = resolve_resource(group_name, name)
            if name in defs[key]["properties"]:
                raise ValueError(f"Conflicting resource collection {key}/{name}")
            defs[key]["properties"][name] = collection(resource(owner, name, declaration))
    return registry | {"$defs": defs}


def bundle(paths):
    core, schemas = mqtt_contract()
    files = {f"{CORE_TITLE}.TM.json": core}

    def add_model(title, tm, model, groups):
        filename = f"{title}.TM.json"
        schema = f"{title}Types"
        if filename in files:
            raise ValueError(f"Conflicting generated model name: {filename}")
        files[filename] = tm | {"xreg:types": schema_path(schema)}
        schemas[schema] = model_schema(model, groups)

    for path in paths:
        source = path.relative_to(ROOT).as_posix()
        try:
            model = expand(load(path), path, ((path, ""),))
            groups = model.get("groups", {})
            if source == "core/model.json":
                schema = f"{CORE_TITLE}Types"
                core.update({"xreg:modelSource": source, "xreg:types": schema_path(schema)})
                schemas[schema] = model_schema(model, groups)
                continue
            for group_name in groups:
                if (source, group_name) in DOMAIN_PROJECTIONS:
                    title, media = DOMAIN_PROJECTIONS[source, group_name]
                    resources = groups[group_name]["resources"]
                    domain = {"groupType": group_name}
                    if len(resources) == 1:
                        domain["resourceType"], declaration = next(iter(resources.items()))
                        if declaration.get("hasdocument", True):
                            domain |= {"contentType": media, "documentValueSchema": schema_path("DocumentValue")}
                    tm = domain_model(title, source) | {
                        "description": "Domain specialization of the shared xRegistry MQTT actions.",
                        "xreg:domain": domain,
                    }
                    add_model(title, tm, model, [group_name])
            if len(groups) != 1 or (source, next(iter(groups))) not in DOMAIN_PROJECTIONS:
                words = re.split(r"[^a-zA-Z0-9]+", path.parent.name)
                title = "".join(word[:1].upper() + word[1:] for word in words)
                title = {"Cloudevents": "CloudEvents", "Openusd": "OpenUSD", "Wot": "WoT"}.get(title, title)
                add_model(title, domain_model(title, source), model, groups)
        except (KeyError, TypeError, IndexError, ValueError) as error:
            raise ValueError(f"{source}: {error}") from error
    return files | {f"schemas/{name}.schema.json": {"$schema": DIALECT, **data} for name, data in schemas.items()}


def domain_model(title, source):
    return thing(
        title,
        links=[{"rel": "tm:extends", "href": f"./{CORE_TITLE}.TM.json", "type": "application/tm+json"}],
        **{"xreg:modelSource": source},
    )


def generate_zip(output, files, check):
    entries = {f"xregistry-wot/{name}": content for name, content in files.items()}
    if check:
        with ZipFile(output) as archive:
            if sorted(archive.namelist()) != sorted(entries) or any(
                archive.read(name) != content for name, content in entries.items()
            ):
                raise ValueError(f"Missing, changed, or stale generated entries in {output}")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(output, "w") as archive:
            for name, content in sorted(entries.items()):
                archive.writestr(ZipInfo(name), content, compress_type=ZIP_DEFLATED)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="generated bundle directory or .zip file")
    parser.add_argument("--check", action="store_true", help="check for missing, changed, or stale output without writing")
    args = parser.parse_args()
    zip_output = args.output.suffix.lower() == ".zip"
    try:
        tracked = subprocess.check_output(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT,
        ).decode("utf-8").split("\0")
        paths = sorted({ROOT / name for name in tracked if Path(name).name == "model.json" and (ROOT / name).is_file()})
        files = {
            name: (json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
            for name, data in bundle(paths).items()
        }
        if zip_output:
            generate_zip(args.output, files, args.check)
        else:
            stale = sorted(p.relative_to(args.output).as_posix()
                           for pattern in ("*.TM.json", "*.schema.json") for p in args.output.rglob(pattern)
                           if p.is_file() and p.relative_to(args.output).as_posix() not in files)
            if stale:
                parser.error("Stale generated files; remove them or use an empty output directory: " + ", ".join(stale))
            for name, content in sorted(files.items()):
                path = args.output / name
                if args.check:
                    if not path.is_file() or path.read_bytes() != content:
                        parser.error(f"Missing or out-of-date generated file: {path}")
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(content)
    except (OSError, ValueError, BadZipFile, subprocess.CalledProcessError) as error:
        parser.exit(1, f"{error}\n")
    print(f"{'Verified' if args.check else 'Generated'} {len(files)} files from {len(paths)} models.")


if __name__ == "__main__":
    main()
