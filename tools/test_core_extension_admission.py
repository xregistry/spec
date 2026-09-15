"""Check the actual admission prose; these are not server conformance tests."""

from pathlib import Path


CORE = Path(__file__).resolve().parents[1] / "core"
SPEC = (CORE / "spec.md").read_text(encoding="utf-8")
MODEL = (CORE / "model.md").read_text(encoding="utf-8")


def _text_between(text, start, end):
    return " ".join(text.split(start, 1)[1].split(end, 1)[0].split())


def test_unknown_extension_storage_requires_admission_and_validation():
    paragraph = _text_between(
        SPEC, "For clarity, OPTIONAL attributes", "\n\n"
    )
    assert paragraph == (
        "(specification-defined and extensions) are OPTIONAL for clients to "
        "use, but the servers' responsibility will vary. Server-unknown "
        "extension attributes MUST be silently stored in the backing "
        "datastore, provided they are permitted by the model and pass "
        "applicable validation (see [Extensions](#extensions)). "
        "Specification-defined attributes and server-known extension "
        "attributes MUST generate an error if the corresponding feature is "
        "not supported or enabled. However, as with all attributes, if "
        "accepting the attribute results in a bad state (such as exceeding "
        "a size limit or resulting in a security issue), then the server "
        "MAY choose to reject the request."
    )


def test_admission_retains_named_local_wildcard_and_enclosing_any_cases():
    admission = _text_between(
        SPEC, "- All extension attributes that appear", "\n- They MUST NOT"
    )
    assert admission == (
        "in the serialization of an entity MUST conform to the model "
        "definition of the Registry, otherwise an error "
        "([unknown_attribute](#unknown_attribute)) MUST be generated. "
        "This means that they MUST satisfy at least one of the following: "
        "- Be explicitly defined (by name) as part of the model. "
        "- Be permitted due to the presence of the `*` (undefined) extension "
        "attribute name at that level in the model. "
        "- Be permitted due to the presence of an `any` type for one of its "
        "parent attribute definitions."
    )


def test_closed_model_still_rejects_unknown_extension_names():
    definition = _text_between(
        MODEL, "### `attributes.<STRING>.name`\n", "\n\n"
    )
    assert definition == (
        "- Type: String. - REQUIRED. - The name of the attribute. MUST be the "
        "same as its key in the owning `attributes` map. A value of `*` "
        "indicates support for undefined extension names at runtime. "
        "Absence of a `*` attribute indicates lack of support for undefined "
        "extensions the presence of an unknown attribute at runtime MUST "
        "generate an ([unknown_attribute](./spec.md#unknown_attribute)) error."
    )


def test_wildcard_is_not_implicit_and_retains_validation():
    wildcard = _text_between(MODEL, "  Often `*`", "\n\n")
    assert wildcard == (
        "is used with a `type` of `any` to allow for any undefined extension "
        "name of any supported data type. By default, the model does not "
        "support undefined extensions. Note that undefined extensions, if "
        "supported, MUST adhere to the same rules as "
        "[defined extensions](./spec.md#attributes-and-extensions)."
    )


def test_enclosing_any_keeps_its_scoped_syntax_validation_boundary():
    any_scope = _text_between(
        SPEC, "This will only happen when the", "\n- Attribute instances"
    )
    assert any_scope == (
        "`any` type has been used higher-up in the model. As a result, any "
        "portion of the entity that appears under the scope of an `any` "
        "typed attribute or map-value is NOT REQUIRED to be validated "
        "except to ensure that the syntax is valid per the rules of the "
        "serialization format used."
    )


def test_model_admission_does_not_allow_invalid_attribute_values():
    invalid = _text_between(
        SPEC, "Use of an attribute (specification-defined, or extension)", "\n\n"
    )
    assert invalid == (
        "that does not conform to this specification MUST generate an error "
        "([invalid_attribute](#invalid_attribute))."
    )
