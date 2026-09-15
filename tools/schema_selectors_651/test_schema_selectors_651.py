import io
import json
from pathlib import Path
import re
from urllib.parse import quote
import xml.etree.ElementTree as ET

import avro.io
import avro.schema
import jsonschema
import pytest
from referencing import Registry, Resource
from referencing.exceptions import NoSuchAnchor
from referencing.jsonschema import DRAFT7, DRAFT201909, DRAFT202012

from selectors_651 import (
    AmbiguousSelection,
    Reference,
    SelectionError,
    UnresolvedSelection,
    avro_declarations,
    encode_local_owner,
    format_reference,
    select_json_structure,
    select_named,
    select_pointer,
    split_reference,
)


ROOT = Path(__file__).resolve().parents[2]
SPEC = (ROOT / "schema" / "spec.md").read_text(encoding="utf-8")
PROSE = " ".join(SPEC.split())
VERSION = "#/schemagroups/g/schemas/s/versions/1"
RESOURCE = "#/schemagroups/g/schemas/s"


@pytest.mark.parametrize(
    ("format_name", "selector"),
    [
        ("JsonSchema/draft/2020-12", "/$defs/a~1b~0c%2F +\u00e9"),
        ("JsonStructure/draft-04", "/definitions/Namespace/Type"),
        ("Avro/1.12.0", "example.Outer"),
        ("Protobuf/3", ".example.Outer.Inner"),
        ("XSD/1.1", "/xs:schema/xs:element[@name='Order']"),
        ("XSD/1.0", "/xs:schema/xs:element[@name='A~B%2F +\u00e9']"),
    ],
)
@pytest.mark.parametrize(
    "document",
    [
        "https://example.com/schemas/a%3Ab?opaque=%2F&case=A",
        "schemas/a%3Ab",
        "#/schemagroups/g/schemas/a%3Ab/versions/1",
        "https://example.com/export.json#/schemagroups/g/schemas/a%3Ab",
    ],
)
def test_all_format_encoded_selector_roundtrips_preserve_document_identity(
    format_name, selector, document
):
    uri = format_reference(document, selector, format_name)
    reference = split_reference(uri, format_name, document_candidates=[document])
    assert reference.document == document
    assert reference.selector == selector
    assert format_reference(reference.document, reference.selector, format_name) == uri


@pytest.mark.parametrize("format_name", ["Avro/1.12.0", "Protobuf/3", "XSD/1.0"])
def test_colon_owner_collision_is_rejected_not_suffix_stripped(format_name):
    literal = "#/schemagroups/g/schemas/a:B"
    prefix = "#/schemagroups/g/schemas/a"
    with pytest.raises(AmbiguousSelection, match="boundary"):
        split_reference(literal, format_name, document_candidates=[literal, prefix])
    owner = split_reference(literal, format_name, document_candidates=[literal])
    assert owner == Reference(literal, None, format_name.split("/")[0].lower())
    selection = split_reference(literal, format_name, document_candidates=[prefix])
    assert (selection.document, selection.selector) == (prefix, "B")


@pytest.mark.parametrize("format_name", ["Avro/1.12.0", "Protobuf/3", "XSD/1.0"])
def test_encoded_literal_colon_is_never_a_selector_separator(format_name):
    literal = "#/schemagroups/g/schemas/a:B"
    prefix = "#/schemagroups/g/schemas/a"
    encoded = encode_local_owner("/schemagroups/g/schemas/a:B")
    assert encoded == "#/schemagroups/g/schemas/a%3AB"
    reference = split_reference(encoded, format_name, document_candidates=[literal, prefix])
    assert (reference.document, reference.selector) == (encoded, None)


@pytest.mark.parametrize("format_name", ["JsonSchema/draft/2020-12", "JsonStructure/draft-04"])
def test_resource_version_boundary_requires_unambiguous_owner_context(format_name):
    uri = VERSION + "/definitions/T"
    with pytest.raises(AmbiguousSelection):
        split_reference(uri, format_name, document_candidates=[RESOURCE, VERSION])
    reference = split_reference(uri, format_name, document_candidates=[VERSION])
    assert (reference.document, reference.selector) == (VERSION, "/definitions/T")
    resource_reference = split_reference(
        RESOURCE + "/definitions/T", format_name, document_candidates=[RESOURCE]
    )
    assert (resource_reference.document, resource_reference.selector) == (
        RESOURCE,
        "/definitions/T",
    )


def test_percent_encoded_pointer_separators_and_tokens_are_decoded_once():
    document = {
        "$defs": {
            "a/b": True,
            "a~b": False,
            "%2F": {"type": "integer"},
            "+ \u00e9": {"type": "string"},
            "": {},
        }
    }
    for pointer, expected in [
        ("/$defs/a~1b", True),
        ("/$defs/a~0b", False),
        ("/$defs/%2F", {"type": "integer"}),
        ("/$defs/+ \u00e9", {"type": "string"}),
        ("/$defs/", {}),
    ]:
        uri = "https://example.com/schema#" + quote(pointer, safe="")
        reference = split_reference(uri, "JsonSchema/draft/2020-12")
        assert reference.selector == pointer
        selected = select_pointer(document, reference.selector)
        assert type(selected) is type(expected)
        assert selected == expected
        jsonschema.Draft202012Validator.check_schema(selected)

    encoded_owner = "#%2Fschemagroups%2Fg%2Fschemas%2Fs"
    uri = encoded_owner + "%2F$defs%2Fa~1b"
    reference = split_reference(
        uri, "JsonSchema/draft/2020-12", document_candidates=[RESOURCE]
    )
    assert reference.document == encoded_owner
    assert reference.selector == "/$defs/a~1b"
    assert select_pointer(document, reference.selector) is True


@pytest.mark.parametrize("fragment", ["%GG", "%2", "%FF", "%C0%AF", "%ED%A0%80", "[x]", "\u00e9"])
def test_invalid_uri_selector_encoding_fails_explicitly(fragment):
    with pytest.raises(SelectionError):
        split_reference("https://example.com/schema#" + fragment, "JsonSchema/draft/2020-12")


@pytest.mark.parametrize("document", ["", "#bad~2pointer", "#/a#/b", "#/a%GG"])
def test_invalid_explicit_document_context_is_not_accepted(document):
    with pytest.raises(SelectionError):
        format_reference(document, None, "JsonSchema/draft/2020-12")
    with pytest.raises(SelectionError):
        split_reference("#/a", "JsonSchema/draft/2020-12", document_candidates=[document])


def test_missing_context_and_unknown_profiles_stay_unresolved_without_acquisition():
    with pytest.raises(UnresolvedSelection, match="context"):
        split_reference(VERSION + ":Message", "Protobuf/3")
    with pytest.raises(UnresolvedSelection, match="owner"):
        split_reference(VERSION + ":Message", "Protobuf/3", document_candidates=[])
    with pytest.raises(UnresolvedSelection, match="format"):
        split_reference("https://example.com/schema#T", "Unknown/1")
    assert split_reference("https://example.com/unavailable#T", "Avro/1.12.0") == Reference(
        "https://example.com/unavailable", "T", "avro"
    )


@pytest.mark.parametrize("schema", [True, False, {}, {"type": "array", "items": {"type": "string"}}])
@pytest.mark.parametrize("pointer", [None, ""])
def test_json_schema_root_selection_preserves_native_boolean_and_object_roots(schema, pointer):
    selected = select_pointer(schema, pointer)
    assert selected is schema
    jsonschema.Draft202012Validator.check_schema(selected)


def test_json_pointer_missing_invalid_and_non_schema_targets_are_not_roots():
    with pytest.raises(SelectionError, match="does not exist"):
        select_pointer({"$defs": {}}, "/$defs/missing")
    with pytest.raises(SelectionError, match="invalid"):
        select_pointer({}, "/bad~2token")
    with pytest.raises(SelectionError, match="does not exist"):
        select_pointer(False, "/type")
    with pytest.raises(jsonschema.SchemaError):
        jsonschema.Draft202012Validator.check_schema(
            select_pointer({"type": "string"}, "/type")
        )
    assert select_pointer({"": False}, "/") is False


@pytest.mark.parametrize(
    "index", ["-", "-1", "01", "+1", "1.0", "2", "9" * 5000],
)
def test_json_pointer_array_selection_requires_an_existing_canonical_index(index):
    document = [True, False]
    assert select_pointer(document, "/0") is True
    assert select_pointer(document, "/1") is False
    with pytest.raises(SelectionError):
        select_pointer(document, "/" + index)


@pytest.mark.parametrize(
    ("format_name", "dialect", "validator", "definition"),
    [
        ("JsonSchema/draft-07", DRAFT7, jsonschema.Draft7Validator,
         {"$id": "#text", "type": "string"}),
        ("JsonSchema/draft/2019-09", DRAFT201909, jsonschema.Draft201909Validator,
         {"$anchor": "text", "type": "string"}),
        ("JsonSchema/draft/2020-12", DRAFT202012, jsonschema.Draft202012Validator,
         {"$anchor": "text", "type": "string"}),
    ],
)
def test_native_json_schema_anchors_are_not_reinterpreted_as_pointers(
    format_name, dialect, validator, definition
):
    document = {"definitions": {"Text": definition}}
    resource = Resource.from_contents(document, default_specification=dialect)
    registry = Registry().with_resource("https://example.com/schema", resource)
    reference = split_reference("https://example.com/schema#text", format_name)
    assert reference.selector == "text"
    selected = registry.resolver(reference.document).lookup("#" + reference.selector).contents
    assert selected is definition
    assert validator(selected).is_valid("ok")
    assert not validator(selected).is_valid(7)
    with pytest.raises(NoSuchAnchor):
        registry.resolver(reference.document).lookup("#missing")


@pytest.mark.parametrize(
    ("schema_text", "value"),
    [
        ('"null"', None),
        ('"boolean"', True),
        ('"string"', "ok"),
        ('{"type":"long"}', 7),
        ('["null","string"]', "ok"),
        ('{"type":"record","name":"T","fields":[]}', {}),
        ('{"type":"enum","name":"T","symbols":["A"]}', "A"),
        ('{"type":"fixed","name":"T","size":1}', b"x"),
        ('{"type":"array","items":"string"}', ["ok"]),
        ('{"type":"map","values":"long"}', {"a": 7}),
    ],
)
def test_avro_default_selection_preserves_all_native_root_categories(schema_text, value):
    schema = avro.schema.parse(schema_text)
    selected = select_named(avro_declarations(schema), None, root=schema)
    assert selected is schema
    output = io.BytesIO()
    avro.io.DatumWriter(selected).write(value, avro.io.BinaryEncoder(output))
    decoded = avro.io.DatumReader(selected).read(
        avro.io.BinaryDecoder(io.BytesIO(output.getvalue()))
    )
    assert type(decoded) is type(value)
    assert decoded == value


def test_avro_native_fullnames_nested_types_aliases_and_ambiguity():
    schema = avro.schema.parse(json.dumps({
        "type": "record", "name": "example.Outer", "namespace": "ignored",
        "fields": [
            {"name": "first", "type": {"type": "record", "name": "T", "aliases": ["Old"], "fields": []}},
            {"name": "second", "type": {"type": "record", "name": "other.T", "fields": []}},
            {"name": "state", "type": {"type": "enum", "name": "State", "symbols": ["A"]}},
            {"name": "code", "type": {"type": "fixed", "name": "Code", "size": 1}},
            {"name": "next", "type": ["null", "example.Outer"]},
        ],
    }))
    declarations = avro_declarations(schema)
    assert set(declarations) == {"example.Outer", "example.T", "other.T", "example.State", "example.Code"}
    assert select_named(declarations, "example.T") is schema.fields[0].type
    assert select_named(declarations, "other.T") is schema.fields[1].type
    assert select_named(declarations, "State").type == "enum"
    assert select_named(declarations, "Code").type == "fixed"
    with pytest.raises(AmbiguousSelection):
        select_named(declarations, "T")
    for name in ["Old", "example.Old", "t", "ignored.Outer", "missing.T"]:
        with pytest.raises(SelectionError, match="does not exist"):
            select_named(declarations, name)
    primitive = avro.schema.parse('"string"')
    with pytest.raises(SelectionError, match="does not exist"):
        select_named(avro_declarations(primitive), "string", root=primitive)


@pytest.mark.parametrize(
    ("schema_text", "name", "value", "expected_bytes"),
    [
        (
            '{"type":"array","items":{"type":"record","name":"example.Item",'
            '"fields":[{"name":"value","type":"int"}]}}',
            "example.Item", {"value": 7}, b"\x0e",
        ),
        (
            '{"type":"map","values":{"type":"enum","name":"example.State","symbols":["A","B"]}}',
            "example.State", "B", b"\x02",
        ),
        (
            '["null",{"type":"fixed","name":"example.Code","size":2}]',
            "example.Code", b"ok", b"ok",
        ),
    ],
)
def test_avro_named_selection_inside_containers_returns_native_type(
    schema_text, name, value, expected_bytes
):
    document = avro.schema.parse(schema_text)
    selected = select_named(avro_declarations(document), name, root=document)
    assert selected.fullname == name
    output = io.BytesIO()
    avro.io.DatumWriter(selected).write(value, avro.io.BinaryEncoder(output))
    assert output.getvalue() == expected_bytes
    assert avro.io.DatumReader(selected).read(
        avro.io.BinaryDecoder(io.BytesIO(expected_bytes))
    ) == value


def test_protobuf_message_index_requires_selector_and_exact_qualification():
    inner = {"kind": "message", "fields": [("value", "int32", 1)]}
    other = {"kind": "message", "fields": [("text", "string", 1)]}
    messages = {"example.Outer.Inner": inner, "example.Other.Inner": other}
    for selector in ["example.Outer.Inner", ".example.Outer.Inner"]:
        assert select_named(messages, selector, protobuf=True) is inner
    with pytest.raises(AmbiguousSelection):
        select_named(messages, "Inner", protobuf=True)
    for selector in [None, "", "Outer.Inner", ".Inner", "example.Enum", "inner"]:
        with pytest.raises(SelectionError):
            select_named(messages, selector, protobuf=True)


@pytest.mark.parametrize(
    "body",
    [
        {"type": "string"},
        {"type": "boolean"},
        {"type": "null"},
        {"type": "object", "properties": {"value": {"type": "string"}}},
        {"type": "array", "items": {"type": "string"}},
        {"type": "set", "items": {"type": "string"}},
        {"type": "map", "values": {"type": "string"}},
        {"type": "tuple", "properties": {"value": {"type": "string"}}, "tuple": ["value"]},
        {"type": "choice", "choices": {"text": {"type": "string"}, "count": {"type": "int32"}}},
        {"type": "any"},
    ],
)
def test_json_structure_inline_roots_are_not_limited_to_object_data_types(body):
    document = json.loads(json.dumps({
        "$schema": "https://json-structure.org/meta/core/v0/#",
        "$id": "https://example.com/Type",
        "name": "Type",
        **body,
    }))
    assert select_json_structure(document, None, declaration_pointers=[""]) is document
    assert document["type"] == body["type"]


def test_json_structure_root_union_nested_namespaces_and_explicit_override():
    union = {"type": ["string", "int32"]}
    text = {"type": "string"}
    document = json.loads(json.dumps({
        "$schema": "https://json-structure.org/meta/core/v0/#",
        "$id": "https://example.com/Types",
        "$root": "#/definitions/Namespace/Union",
        "definitions": {"Namespace": {"Union": union, "Text": text}},
    }))
    paths = ["/definitions/Namespace/Union", "/definitions/Namespace/Text"]
    selected = select_json_structure(document, None, declaration_pointers=paths)
    assert selected == union
    assert selected["type"] == ["string", "int32"]
    assert select_json_structure(document, paths[1], declaration_pointers=paths) == text
    for pointer in ["/definitions", "/definitions/Namespace", "/definitions/Missing", "/properties/Inline"]:
        with pytest.raises(SelectionError):
            select_json_structure(document, pointer, declaration_pointers=paths)
    document.pop("$root")
    with pytest.raises(SelectionError, match="explicit selector"):
        select_json_structure(document, None, declaration_pointers=paths)
    assert select_json_structure(document, paths[0], declaration_pointers=paths) == union
    document["$root"] = "#/definitions/Namespace/Union"
    document["type"] = "string"
    with pytest.raises(SelectionError, match="conflicting"):
        select_json_structure(document, None, declaration_pointers=paths)


def test_json_structure_namespace_named_type_is_not_inferred_to_be_a_declaration():
    document = {"definitions": {"Namespace": {"type": {"type": "string"}}}}
    paths = ["/definitions/Namespace/type"]
    assert select_json_structure(document, paths[0], declaration_pointers=paths) == {"type": "string"}
    with pytest.raises(SelectionError, match="indexed type"):
        select_json_structure(document, "/definitions/Namespace", declaration_pointers=paths)


@pytest.mark.parametrize("definitions", [{}, {"Only": {"type": "string"}}])
def test_json_structure_library_has_no_implicit_root_even_with_one_declaration(definitions):
    document = {
        "$schema": "https://json-structure.org/meta/core/v0/#",
        "$id": "https://example.com/Library",
        "definitions": definitions,
    }
    with pytest.raises(SelectionError, match="no designated root"):
        select_json_structure(
            document,
            None,
            declaration_pointers=["/definitions/" + name for name in definitions],
        )


@pytest.mark.parametrize("root", ["#", "#/type", "#/definitions/Missing", 7])
def test_json_structure_missing_or_invalid_root_is_not_a_successful_selection(root):
    with pytest.raises(SelectionError):
        select_json_structure(
            {"$root": root, "definitions": {"Text": {"type": "string"}}},
            None,
            declaration_pointers=["/definitions/Text"],
        )


def test_documented_xpath_expression_decodes_and_addresses_actual_xml():
    section = SPEC.split("#### 4.3.2. XML Schema", 1)[1].split("#### 4.3.3.", 1)[0]
    source = re.search(r"```xml\n(.*?)\n```", section, re.DOTALL).group(1)
    root = ET.fromstring(source)
    assert root.tag == "{http://www.w3.org/2001/XMLSchema}schema"
    assert [node.attrib["name"] for node in root] == ["Order", "Cancel"]
    uri = re.search(r"`(https://example.com/schemas/orders.xsd#[^`]+)`", section).group(1)
    reference = split_reference(uri, "XSD/1.0")
    assert reference.selector == "/xs:schema/xs:element[@name='Order']"
    nodes = root.findall("xs:element[@name='Order']", {"xs": "http://www.w3.org/2001/XMLSchema"})
    assert len(nodes) == 1
    assert nodes[0].attrib == {"name": "Order", "type": "xs:string"}


def test_normative_profiles_retain_prerequisite_separators_and_explicit_boundaries():
    assert "If the URI does not contain a fragment, the message name MUST be appended as a URI fragment using `#{message-name}`." in PROSE
    assert "If the URI already contains a fragment, the message name MUST be appended to the fragment using `:{message-name}`." in PROSE
    assert "reference MUST be rejected as ambiguous" in PROSE
    assert "An encoded colon MUST NOT be promoted to a separator." in PROSE
    assert "Percent-decode the selected component exactly once." in PROSE
    assert "Only the XPath core function library is available" in PROSE
    assert "default namespace does not apply to unprefixed XPath names" in PROSE
    assert "Without an explicit selection, use the document's inline root type or its `$root` designation" in PROSE
    assert "A type declaration is not limited to the `object` data type." in PROSE
    assert "Selection does not require automatic network acquisition." in PROSE
