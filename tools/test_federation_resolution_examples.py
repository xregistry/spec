"""Concrete local shadow and ordered-source examples without network access."""

from unittest.mock import Mock

import pytest

from federation_examples import FederationError
from federation_resolution_examples import Source, resolve_resource_read


XID = "/documents/main/assets/item"
RESOURCE = {"xid": XID, "assetid": "item"}


def missing():
    return FederationError("not_found", "Resource absent")


def test_local_resource_shadows_all_remote_versions():
    local = Mock(side_effect=[RESOURCE, b"local default"])
    remote = Mock(side_effect=AssertionError("Shadowed source must not be read"))
    result = resolve_resource_read(XID, "document", Source("local", local), [Source("supplier", remote)])
    assert result == {"origin": "local", "target": XID, "value": b"local default"}
    assert local.call_args_list == [(("entity", XID),), (("document", XID),)]
    remote.assert_not_called()


def test_source_resource_absence_advances_in_explicit_order():
    calls = []

    def read(name, value):
        def execute(operation, target):
            calls.append((name, operation, target))
            if isinstance(value, Exception):
                raise value
            return value
        return execute

    result = resolve_resource_read(
        XID, "entity", Source("local", read("local", missing())),
        [Source("first", read("first", missing())), Source("second", read("second", RESOURCE))],
    )
    assert result["origin"] == "second"
    assert result["value"] == RESOURCE
    assert calls == [
        ("local", "entity", XID), ("first", "entity", XID), ("second", "entity", XID),
    ]


def test_first_found_source_wins_without_testing_lower_priority_sources():
    lower = Mock(side_effect=AssertionError("Lower priority source must not be read"))
    result = resolve_resource_read(
        XID, "entity", Source("local", Mock(side_effect=missing())),
        [Source("chosen", Mock(return_value=RESOURCE)), Source("lower", lower)],
    )
    assert result == {"origin": "chosen", "target": XID, "value": RESOURCE}
    lower.assert_not_called()


@pytest.mark.parametrize("local_present", [True, False])
def test_missing_version_does_not_mix_resource_origins(local_present):
    chosen = Mock(side_effect=[RESOURCE, FederationError("not_found", "Version absent")])
    lower = Mock(side_effect=AssertionError("Must not borrow a Version"))
    local = Source("local", chosen if local_present else Mock(side_effect=missing()))
    sources = [Source("lower", lower)] if local_present else [
        Source("chosen", chosen), Source("lower", lower),
    ]
    with pytest.raises(FederationError) as error:
        resolve_resource_read(XID + "/versions/v2", "document", local, sources)
    assert error.value.code == "not_found"
    assert str(error.value) == "Version absent"
    assert chosen.call_args_list == [(("entity", XID),), (("document", XID + "/versions/v2"),)]
    lower.assert_not_called()


@pytest.mark.parametrize("code", [
    "policy_denied", "unsupported_binding", "unsupported_version",
    "integrity_error", "invalid_package", "inconsistent_snapshot",
])
def test_source_failures_are_not_treated_as_absence(code):
    failure = FederationError(code, "Source read failed")
    lower = Mock(side_effect=AssertionError("No fallback after failure"))
    with pytest.raises(FederationError) as error:
        resolve_resource_read(
            XID, "entity", Source("local", Mock(side_effect=missing())),
            [Source("first", Mock(side_effect=failure)), Source("second", lower)],
        )
    assert error.value is failure
    lower.assert_not_called()


def test_resource_not_found_requires_exhausting_configured_sources():
    local, remote = Mock(side_effect=missing()), Mock(side_effect=missing())
    with pytest.raises(FederationError) as error:
        resolve_resource_read(XID, "entity", Source("local", local), [Source("remote", remote)])
    assert error.value.code == "not_found"
    local.assert_called_once_with("entity", XID)
    remote.assert_called_once_with("entity", XID)


@pytest.mark.parametrize("value", [{}, [], {"xid": "/documents/main/assets/other"}])
def test_reachable_endpoint_without_requested_resource_is_not_found_success(value):
    with pytest.raises(FederationError) as error:
        resolve_resource_read(XID, "entity", Source("local", Mock(return_value=value)), [])
    assert error.value.code == "invalid_package"


def test_source_policy_rejects_unordered_candidates_before_reading():
    read = Mock()
    with pytest.raises(FederationError) as error:
        resolve_resource_read(
            XID, "entity", Source("local", read), {Source("first", read), Source("second", read)}
        )
    assert error.value.code == "invalid_package"
    read.assert_not_called()
