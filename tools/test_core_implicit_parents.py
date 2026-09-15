"""Check implicit-parent rules in source, not a simulated storage transaction."""

import re
from pathlib import Path


CORE = Path(__file__).resolve().parents[1] / "core"
SPEC = (CORE / "spec.md").read_text(encoding="utf-8")
MODEL = (CORE / "model.md").read_text(encoding="utf-8")


def _between(text, start, end):
    return " ".join(text.split(start, 1)[1].split(end, 1)[0].split())


def test_implicit_creation_requires_populatable_non_null_parent_values():
    rule = _between(
        SPEC, "### Design: Implicit Creation of Parent Entities\n",
        "\n### Design: Events"
    )
    assert rule == (
        "To reduce the number of interactions needed when creating an entity, "
        "if any of its parent entities do not exist, then they MUST be "
        "implicitly created. Each of those entities MUST be created with the "
        "appropriate `<SINGULAR>id` as specified by the protocol-specific "
        "mechanism by which the nested entity is identified. For example, in "
        "HTTP the `<PATH>` would include the `<SINGULAR>id` values of the parent "
        "entities. If any of those entities have applicable REQUIRED attributes "
        "whose non-null values cannot be populated by the server or by default "
        "values (see the `required` aspect in the [model](./model.md)), "
        "then they cannot be implicitly "
        "created, and would need to be created directly. This also means that "
        "the creation of the original entity would fail and generate an error "
        "([required_attribute_missing](./spec.md#required_attribute_missing)) "
        "for the appropriate parent entity."
    )


def test_required_values_allow_server_and_defaults_but_not_missing_values():
    required = MODEL.split("### `attributes.<STRING>.required`", 1)[1]
    rule = _between(required, "- When set to `true`,", "\n- A `true` value")
    assert rule == (
        "this specification does not mandate how this attribute's value is "
        "populated (i.e. by a client, the server or via a default value), just "
        "that by the end of the server's processing of any request it MUST "
        "have a non-null value, and generate an error "
        "([invalid_attribute](./spec.md#invalid_attribute)) if not. Note that "
        "this implies that a REQUIRED attribute does not mean that clients "
        "are mandated to include that attribute in their requests. If the "
        "attribute will automatically be populated by the server (e.g. it "
        "has a default value defined) the client MAY omit it."
    )


def test_defaults_remain_typed_non_null_scalars():
    rule = _between(
        MODEL, "### `attributes.<STRING>.default`\n", "\n- OPTIONAL."
    )
    assert rule == (
        "- Type: MUST be a non-`null` value of the type specified by the "
        "`attributes.<STRING>.type` model attribute and MUST only be used for "
        "scalar types. Attempts to define a `default` value for a non-scalar "
        "type MUST generate an error "
        "([model_scalar_default](./spec.md#model_scalar_default))."
    )


def test_child_default_does_not_require_absent_owning_object():
    default = MODEL.split("### `attributes.<STRING>.default`", 1)[1]
    rule = _between(
        default, "- This value MUST be used", "\n- When not specified"
    )
    assert rule == (
        "to populate this attribute's value if one was not provided by a "
        "client. An attribute with a default value does not mean that its "
        "owning Object is mandated to be present; rather the attribute would "
        "only appear when the owning Object is present. By default, "
        "attributes have no default values."
    )


def test_missing_parent_required_values_keep_error_identity_and_arguments():
    entry = SPEC.split("### required_attribute_missing\n", 1)[1].split(
        "\n### ", 1
    )[0]
    assert dict(re.findall(r"^\* (\w+): `([^`]+)`$", entry, re.MULTILINE)) == {
        "Type": "https://github.com/xregistry/spec/blob/main/core/spec.md"
        "#required_attribute_missing",
        "Code": "400 Bad Request",
        "Title": 'One or more mandatory attributes for "<subject>" are '
        "missing: <list>.",
        "Subject": "<entity_xid>",
    }
    assert re.findall(r"^  - `(\w+)`:", entry, re.MULTILINE) == ["list"]


def test_parent_failure_keeps_whole_request_rollback():
    registry_rule = _between(
        SPEC, "Unless otherwise stated in a protocol binding specification,",
        "\n\n"
    )
    assert registry_rule == (
        "if the processing of a request fails (even during the generation of "
        "the response) then an error MUST be generated and the entire request "
        "MUST be undone. See the [Error Processing](#error-processing) section "
        "for more information."
    )
    error_rule = _between(SPEC, "## Error Processing\n\n", "\n\n")
    assert error_rule == (
        "If an error occurs during the processing of a request, even if the "
        "error was during the creation of the response (e.g. an invalid "
        "`inline` value was provided), then an error MUST be generated and "
        "the entire request MUST be undone."
    )
