"""Structural checks for the authored protocol option and declaration boundaries.

These tests read the real source models and the schemas produced by the real
generator. They prove the representation boundary - which nodes are opaque,
which keep a declared kind, and which JSON kinds survive - and they do not
prove the procedural obligations that the specifications state for authors and
consumers. Those obligations have no executable checker in this repository,
and `test_opaque_containers_admit_structurally_invalid_data` records that
limit explicitly.
"""

import copy
import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
ENDPOINT_MODEL = ROOT / "endpoint" / "model.json"
MESSAGE_MODEL = ROOT / "message" / "model.json"
SAMPLE_ROOT = ROOT / "cloudevents" / "samples"

COMMON_MEMBERS = ("description", "required", "specurl", "type", "value")

ENDPOINT_NATIVE_NAME_CONTAINERS = [
    ("AMQP/1.0", "link-properties"),
    ("AMQP/1.0", "connection-properties"),
    ("AMQP/1.0", "source-filters"),
    ("HTTP", "query"),
    ("KAFKA", "headers"),
]

ENDPOINT_ADVISORY_ENUMS = [
    ("AMQP/1.0", "distribution-mode"),
    ("AMQP/1.0", "terminus-durability"),
    ("AMQP/1.0", "expiry-policy"),
    ("AMQP/1.0", "sender-settle-mode"),
    ("AMQP/1.0", "receiver-settle-mode"),
    ("KAFKA", "autooffsetreset"),
]

MESSAGE_NATIVE_NAME_CONTAINERS = [
    ("AMQP/1.0", "application-properties"),
    ("AMQP/1.0", "message-annotations"),
    ("AMQP/1.0", "delivery-annotations"),
    ("AMQP/1.0", "footer"),
    ("KAFKA", "headers"),
]

MESSAGE_ORDERED_ARRAYS = [
    ("HTTP", "headers"),
    ("HTTP", "query"),
    ("NATS", "headers"),
    ("MQTT/5.0", "user_properties"),
]

CLOUDEVENTS_ATTRIBUTES = (
    "specversion",
    "id",
    "type",
    "source",
    "subject",
    "time",
    "dataschema",
    "datacontenttype",
)

AMQP_FIXED_PROPERTIES = (
    "message-id",
    "user-id",
    "to",
    "subject",
    "reply-to",
    "correlation-id",
    "content-type",
    "content-encoding",
    "absolute-expiry-time",
    "creation-time",
    "group-id",
    "group-sequence",
    "reply-to-group-id",
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _generate(tmp_path_factory, kind, models, extra=()):
    output = tmp_path_factory.mktemp("generated") / f"{kind}.json"
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(ROOT / "tools" / "schema-generator.py"),
            "--type",
            kind,
            *extra,
            "--output",
            str(output),
            *(str(ROOT / model) for model in models),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return _load(output)


@pytest.fixture(scope="module")
def endpoint_schema(tmp_path_factory):
    document = _generate(
        tmp_path_factory, "json-schema", ["endpoint/model.json"]
    )
    return document["definitions"]["endpoint-schema"]["endpoint"]


@pytest.fixture(scope="module")
def message_schema(tmp_path_factory):
    document = _generate(tmp_path_factory, "json-schema", ["message/model.json"])
    return document["definitions"]["messagegroup-schema"]["message"]


@pytest.fixture(scope="module")
def endpoint_structure(tmp_path_factory):
    return _generate(
        tmp_path_factory,
        "json-structure",
        ["endpoint/model.json"],
        extra=("--schema-name", "EndpointRegistryDocument"),
    )


@pytest.fixture(scope="module")
def endpoint_model():
    return _load(ENDPOINT_MODEL)


@pytest.fixture(scope="module")
def message_model():
    return _load(MESSAGE_MODEL)


def _model_options(model, group, resource, discriminator, value, sibling):
    node = model["groups"][group]
    if resource is not None:
        node = node["resources"][resource]
    branch = node["attributes"][discriminator]["ifvalues"][value]
    return branch["siblingattributes"][sibling]["attributes"]


def endpoint_options(model, protocol):
    return _model_options(
        model, "endpoints", None, "protocol", protocol, "protocoloptions"
    )


def message_options(model, protocol):
    return _model_options(
        model, "messagegroups", "messages", "protocol", protocol, "protocoloptions"
    )


def cloudevents_metadata(model):
    return _model_options(
        model,
        "messagegroups",
        "messages",
        "envelope",
        "CloudEvents/1.0",
        "envelopemetadata",
    )


def _guarded_options(entity_schema, discriminator, value):
    matches = []

    def visit(branch):
        if not isinstance(branch, dict):
            return
        properties = branch.get("properties", {})
        guard = properties.get(discriminator)
        options = properties.get(f"{discriminator}options")
        if (
            discriminator in branch.get("required", [])
            and options is not None
            and guard is not None
            and jsonschema.Draft7Validator(guard).is_valid(value)
        ):
            matches.append(options)
        for keyword in ("allOf", "anyOf", "oneOf"):
            for child in branch.get(keyword, []):
                visit(child)

    visit(entity_schema)
    assert len(matches) == 1, f"expected one {value} branch, found {len(matches)}"
    return matches[0]


def _named_nodes(document, name):
    """Find emitted property definitions for a source attribute name.

    The JSON Structure emitter rewrites `dashed-names` to camel case and keeps
    the original under `altnames.json`, so match on either form.
    """
    found = []

    def visit(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(value, dict) and (
                    key == name or value.get("altnames", {}).get("json") == name
                ):
                    found.append(value)
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(document)
    return found


def _accepts(schema, instance, check_format=False):
    original = copy.deepcopy(instance)
    checker = jsonschema.FormatChecker() if check_format else None
    valid = jsonschema.Draft7Validator(schema, format_checker=checker).is_valid(
        instance
    )
    assert instance == original, "validation MUST NOT modify caller data"
    return valid


# --- W07: Endpoint protocol option authoring boundary ------------------------


@pytest.mark.parametrize(
    "protocol", ["AMQP/1.0", "MQTT/5.0", "MQTT/3.1.1", "HTTP", "NATS"]
)
def test_endpoint_address_is_a_template_without_a_reference_target(
    endpoint_model, protocol
):
    address = endpoint_options(endpoint_model, protocol)["endpoints"]["item"][
        "attributes"
    ]["uri"]
    assert address["type"] == "uritemplate"
    assert "target" not in address


@pytest.mark.parametrize(
    "protocol", ["AMQP/1.0", "MQTT/5.0", "MQTT/3.1.1", "HTTP", "KAFKA", "NATS"]
)
@pytest.mark.parametrize("field", ["resourceuri", "authorityuri"])
def test_endpoint_authorization_reference_is_a_template(
    endpoint_model, protocol, field
):
    entry = endpoint_options(endpoint_model, protocol)["authorization"]["item"]
    assert entry["attributes"][field]["type"] == "uritemplate"
    assert "target" not in entry["attributes"][field]


@pytest.mark.parametrize(
    "protocol", ["AMQP/1.0", "MQTT/5.0", "MQTT/3.1.1", "HTTP", "NATS"]
)
def test_generated_address_admits_an_unresolved_placeholder(
    endpoint_schema, protocol
):
    options = _guarded_options(endpoint_schema, "protocol", protocol)
    address = options["properties"]["endpoints"]["items"]["properties"]["uri"]
    assert address["format"] == "uri-template"
    templated = "https://{tenant}.example.test"
    assert _accepts(address, templated, check_format=True)
    assert _accepts(address, "https://tenant.example.test", check_format=True)
    assert not _accepts(address, 42, check_format=True)
    previous = dict(address, format="uri")
    assert not _accepts(previous, templated, check_format=True), (
        "the previous uri format is what rejected an authored placeholder"
    )


@pytest.mark.parametrize(
    ("protocol", "option"),
    ENDPOINT_NATIVE_NAME_CONTAINERS,
    ids=[f"{p}-{o}" for p, o in ENDPOINT_NATIVE_NAME_CONTAINERS],
)
def test_endpoint_native_name_container_is_whole_map_opaque(
    endpoint_model, endpoint_schema, protocol, option
):
    declared = endpoint_options(endpoint_model, protocol)[option]
    assert declared["type"] == "any"
    assert "item" not in declared

    options = _guarded_options(endpoint_schema, "protocol", protocol)
    container = options["properties"][option]
    assert "type" not in container
    assert "additionalProperties" not in container
    assert _accepts(container, {"{parameter}": "{value}"})
    assert _accepts(container, {"MyHeader": "x", "_tag": "y"})


def test_amqp_source_filters_keep_a_literal_null_value(endpoint_schema):
    options = _guarded_options(endpoint_schema, "protocol", "AMQP/1.0")
    filters = {"apache.org:selector-filter:string": None}
    assert _accepts(options["properties"]["source-filters"], filters)
    assert "apache.org:selector-filter:string" in filters
    assert filters["apache.org:selector-filter:string"] is None


@pytest.mark.parametrize(
    ("protocol", "option"),
    ENDPOINT_ADVISORY_ENUMS,
    ids=[f"{p}-{o}" for p, o in ENDPOINT_ADVISORY_ENUMS],
)
def test_string_enums_are_advisory_in_the_source_model(
    endpoint_model, protocol, option
):
    declared = endpoint_options(endpoint_model, protocol)[option]
    assert declared["type"] == "string"
    assert declared["enum"], "the documented value list is retained"
    assert declared["strict"] is False


@pytest.mark.parametrize(
    ("protocol", "option"),
    [entry for entry in ENDPOINT_ADVISORY_ENUMS if entry[0] == "AMQP/1.0"],
    ids=[o for p, o in ENDPOINT_ADVISORY_ENUMS if p == "AMQP/1.0"],
)
def test_advisory_enums_are_not_emitted_as_generated_constraints(
    endpoint_structure, endpoint_schema, protocol, option
):
    emitted = _named_nodes(endpoint_structure, option)
    assert emitted, f"{option} is projected into the JSON Structure document"
    for node in emitted:
        assert node["type"] == "string"
        assert "enum" not in node
        assert _accepts({"type": "string"}, "{mode}")

    field = _guarded_options(endpoint_schema, "protocol", protocol)["properties"][
        option
    ]
    assert field["type"] == "string"
    assert "enum" not in field
    assert _accepts(field, "{mode}")


def test_kafka_options_have_no_json_structure_projection(endpoint_structure):
    """Record where the pinned generator gives no artifact-level evidence.

    The JSON Structure emitter does not project the Kafka protocol branch, so
    `autooffsetreset` has no emitted node to inspect. The JSON Schema and
    OpenAPI emitters never projected a scalar `enum` at all, so the `strict`
    aspect is not observable there either. Correcting that emitter coverage is
    outside the scope of this proposal.
    """
    assert _named_nodes(endpoint_structure, "autooffsetreset") == []
    assert _named_nodes(endpoint_structure, "bootstrap.servers") == []


@pytest.mark.parametrize(
    ("protocol", "option", "rejected"),
    [
        ("AMQP/1.0", "deployed", "true"),
        ("AMQP/1.0", "durable", "false"),
        ("KAFKA", "acks", "1"),
        ("KAFKA", "enableautocommit", "true"),
        ("MQTT/5.0", "qos", "{qos}"),
        ("MQTT/5.0", "retain", "false"),
    ],
    ids=[
        "amqp-deployed",
        "amqp-durable",
        "kafka-acks",
        "kafka-enableautocommit",
        "mqtt-qos",
        "mqtt-retain",
    ],
)
def test_native_boolean_and_numeric_options_reject_stringified_values(
    endpoint_schema, protocol, option, rejected
):
    options = _guarded_options(endpoint_schema, "protocol", protocol)
    field = options["properties"][option]
    assert field["type"] in ("boolean", "integer")
    assert not _accepts(field, rejected)
    assert _accepts(field, False if field["type"] == "boolean" else 1)


def test_kafka_address_and_security_stay_structured_while_headers_open(
    endpoint_model,
):
    options = endpoint_options(endpoint_model, "KAFKA")
    entry = options["endpoints"]["item"]
    assert entry["type"] == "object"
    assert entry["attributes"]["bootstrap.servers"]["type"] == "array"
    assert entry["attributes"]["bootstrap.servers"]["item"] == {"type": "string"}
    assert entry["attributes"]["security.protocol"]["type"] == "string"
    assert entry["attributes"]["sasl.mechanism"]["type"] == "string"
    assert options["headers"]["type"] == "any"


# --- W12: Message property declaration boundary ------------------------------


@pytest.mark.parametrize("attribute", CLOUDEVENTS_ATTRIBUTES)
def test_cloudevents_declarations_are_opaque_records(message_model, attribute):
    declared = cloudevents_metadata(message_model)[attribute]
    assert declared["type"] == "any"
    assert "attributes" not in declared


def test_cloudevents_metadata_stays_flat_with_an_extension_wildcard(message_model):
    metadata = cloudevents_metadata(message_model)
    assert set(metadata) == set(CLOUDEVENTS_ATTRIBUTES) | {"*"}
    assert "attributes" not in metadata
    assert metadata["*"]["type"] == "any"


@pytest.mark.parametrize("name", AMQP_FIXED_PROPERTIES)
def test_amqp_fixed_property_names_survive_with_opaque_records(message_model, name):
    section = message_options(message_model, "AMQP/1.0")["properties"]
    assert section["type"] == "object"
    assert section["namecharset"] == "extended"
    assert section["attributes"][name]["type"] == "any"


def test_amqp_subject_has_no_required_preset(message_model):
    subject = message_options(message_model, "AMQP/1.0")["properties"]["attributes"][
        "subject"
    ]
    assert "attributes" not in subject
    assert "default" not in subject


def test_no_message_declaration_presets_required_to_true(message_model):
    offenders = []

    def visit(node, path):
        if isinstance(node, dict):
            if node.get("name") == "required" and node.get("default") is True:
                offenders.append(path)
            for key, value in node.items():
                visit(value, f"{path}/{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                visit(value, f"{path}[{index}]")

    visit(message_model, "")
    assert offenders == []


def test_amqp_header_section_keeps_declared_native_kinds(message_model):
    header = message_options(message_model, "AMQP/1.0")["header"]
    assert header["type"] == "object"
    kinds = {name: field["type"] for name, field in header["attributes"].items()}
    assert kinds == {
        "durable": "boolean",
        "priority": "integer",
        "ttl": "integer",
        "first-acquirer": "boolean",
        "delivery-count": "integer",
    }
    assert header["attributes"]["priority"]["default"] == 4


@pytest.mark.parametrize(
    ("protocol", "option"),
    MESSAGE_NATIVE_NAME_CONTAINERS,
    ids=[f"{p}-{o}" for p, o in MESSAGE_NATIVE_NAME_CONTAINERS],
)
def test_message_native_name_container_is_whole_map_opaque(
    message_model, message_schema, protocol, option
):
    declared = message_options(message_model, protocol)[option]
    assert declared["type"] == "any"
    assert "item" not in declared

    container = _guarded_options(message_schema, "protocol", protocol)[
        "properties"
    ][option]
    assert "type" not in container
    assert "additionalProperties" not in container
    assert _accepts(container, {"MyProperty": {"value": "x"}, "_tag": {"value": "y"}})


@pytest.mark.parametrize(
    ("protocol", "option"),
    MESSAGE_ORDERED_ARRAYS,
    ids=[f"{p}-{o}" for p, o in MESSAGE_ORDERED_ARRAYS],
)
def test_ordered_declaration_arrays_keep_order_and_duplicates(
    message_model, message_schema, protocol, option
):
    declared = message_options(message_model, protocol)[option]
    assert declared["type"] == "array"
    assert declared["item"] == {"type": "any"}

    container = _guarded_options(message_schema, "protocol", protocol)[
        "properties"
    ][option]
    assert container["type"] == "array"
    entries = [
        {"name": "Accept", "value": "application/json"},
        {"name": "Accept", "value": "application/xml"},
        {"name": "accept", "value": "text/plain"},
    ]
    assert _accepts(container, entries)
    assert [entry["value"] for entry in entries] == [
        "application/json",
        "application/xml",
        "text/plain",
    ]


def test_no_declaration_container_declares_a_partial_member_set(message_model):
    """No family may re-introduce its own partial copy of the common record."""
    partial = []

    def visit(node, path):
        if isinstance(node, dict):
            members = node.get("attributes")
            if isinstance(members, dict) and members:
                names = set(members)
                if names & set(COMMON_MEMBERS) and names < set(COMMON_MEMBERS):
                    partial.append((path, sorted(names)))
            for key, value in node.items():
                visit(value, f"{path}/{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                visit(value, f"{path}[{index}]")

    visit(message_model, "")
    assert partial == []


@pytest.mark.parametrize(
    ("protocol", "option"),
    MESSAGE_NATIVE_NAME_CONTAINERS + MESSAGE_ORDERED_ARRAYS,
    ids=[
        f"{p}-{o}"
        for p, o in MESSAGE_NATIVE_NAME_CONTAINERS + MESSAGE_ORDERED_ARRAYS
    ],
)
def test_declaration_records_admit_every_common_member(
    message_schema, protocol, option
):
    container = _guarded_options(message_schema, "protocol", protocol)[
        "properties"
    ][option]
    record = {
        "description": "a declared property",
        "required": True,
        "specurl": "https://example.test/spec#property",
        "type": "string",
        "value": "declared",
    }
    assert set(COMMON_MEMBERS) <= set(record)
    if container.get("type") == "array":
        assert _accepts(container, [dict(record, name="Declared")])
    else:
        assert _accepts(container, {"Declared": record})


@pytest.mark.parametrize(
    ("declared_type", "value"),
    [
        ("boolean", False),
        ("integer", 42),
        ("number", 1.5),
        ("string", "42"),
        ("any", None),
    ],
    ids=["boolean", "integer", "number", "string", "null"],
)
def test_declared_values_keep_their_authored_json_kind(
    message_schema, declared_type, value
):
    container = _guarded_options(message_schema, "protocol", "AMQP/1.0")[
        "properties"
    ]["application-properties"]
    section = {"my-property": {"type": declared_type, "value": value}}
    assert _accepts(container, section)
    stored = section["my-property"]["value"]
    assert stored is value or stored == value
    assert type(stored) is type(value)


def test_present_literal_null_value_differs_from_an_absent_value(message_schema):
    container = _guarded_options(message_schema, "protocol", "AMQP/1.0")[
        "properties"
    ]["application-properties"]
    section = {
        "declared-null": {"type": "any", "value": None},
        "unconstrained": {"type": "any"},
    }
    assert _accepts(container, section)
    assert "value" in section["declared-null"]
    assert section["declared-null"]["value"] is None
    assert "value" not in section["unconstrained"]


def test_kafka_headers_are_named_by_their_outer_map_key(message_model):
    headers = message_options(message_model, "KAFKA")["headers"]
    assert headers["type"] == "any"
    assert "item" not in headers
    assert "attributes" not in headers


@pytest.mark.parametrize(
    "sample",
    sorted(SAMPLE_ROOT.rglob("*.xreg.json")),
    ids=lambda path: str(path.relative_to(ROOT)),
)
def test_samples_carry_no_redundant_kafka_inner_header_name(sample):
    document = _load(sample)
    offenders = []

    def visit(node, path):
        if isinstance(node, dict):
            if node.get("protocol") == "KAFKA":
                headers = node.get("protocoloptions", {}).get("headers", {})
                if isinstance(headers, dict):
                    for key, record in headers.items():
                        if isinstance(record, dict) and "name" in record:
                            offenders.append(f"{path}/protocoloptions/headers/{key}")
            for key, value in node.items():
                visit(value, f"{path}/{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                visit(value, f"{path}[{index}]")

    visit(document, "")
    assert offenders == []


@pytest.mark.parametrize(
    ("protocol", "option", "kind"),
    [
        ("KAFKA", "partition", "integer"),
        ("KAFKA", "key_base64", "string"),
        ("MQTT/5.0", "qos", "integer"),
        ("MQTT/5.0", "retain", "boolean"),
        ("HTTP", "path", "uritemplate"),
        ("NATS", "subject", "uritemplate"),
    ],
    ids=[
        "kafka-partition",
        "kafka-key-base64",
        "mqtt-qos",
        "mqtt-retain",
        "http-path",
        "nats-subject",
    ],
)
def test_scalar_protocol_options_stay_scalar(message_model, protocol, option, kind):
    assert message_options(message_model, protocol)[option]["type"] == kind


# --- Declared coverage limit -------------------------------------------------


@pytest.mark.parametrize(
    "structurally_invalid",
    [[], "not-a-map", 7, {"": {"value": "empty name"}}, {"h": {"unknown": 1}}],
    ids=["array", "string", "number", "empty-name", "unknown-member"],
)
def test_opaque_containers_admit_structurally_invalid_data(
    message_schema, structurally_invalid
):
    """The opaque boundary is a storage contract, not a protocol validator.

    Every value below violates a MUST stated in the Message specification's
    Property Definitions section, yet the generated schema admits it. No
    executable checker for those obligations exists in this repository, so
    this test records the limit rather than asserting a rejection that the
    generated schemas cannot make.
    """
    container = _guarded_options(message_schema, "protocol", "KAFKA")["properties"][
        "headers"
    ]
    assert _accepts(container, structurally_invalid)
