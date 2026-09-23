"""Core XIDs are relative URI paths, not undecoded identifier strings."""

import pytest

from workingdrafts.federation.tools.federation_examples import FederationError, validate_xid


@pytest.mark.parametrize("target", [
    "/groups/group:one/resources/item@stable/versions/v:1",
    "/groups/group%3Aone/resources/item%40stable/versions/v%3A1",
    "/groups/group%3aone/resources/%69tem/versions/v%3a1",
])
def test_core_xid_uri_escapes_are_valid_without_changing_the_original_value(target):
    assert validate_xid(target) == target


@pytest.mark.parametrize("identifier", [
    "item%2fother", "item%5cother", "item%252fother", "item%00",
    "item%20", "item%zz", "item%", "item%C0%AE", "item%ff",
])
def test_xid_decoding_is_strict_and_never_turns_a_second_decode_into_an_identifier(identifier):
    with pytest.raises(FederationError) as captured:
        validate_xid("/groups/group/resources/" + identifier)
    assert captured.value.code == "invalid_package"
