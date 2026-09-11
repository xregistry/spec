"""Concrete local shadow and ordered-source examples without network access."""

import json
import re
from pathlib import Path
from unittest.mock import Mock

import pytest
from jsonschema import Draft202012Validator

from federation_examples import FederationError
from federation_resolution_examples import Source, resolution_owner, resolve_resource_read


XID = "/documents/main/assets/item"
RESOURCE = {"xid": XID, "assetid": "item"}


@pytest.fixture(scope="module")
def capability_validator():
    root = Path(__file__).resolve().parent.parent / "workingdrafts" / "federation"
    schema = json.loads((root / "schemas" / "capabilities.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


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


@pytest.mark.parametrize("capabilities", [
    None, {}, {"flags": []}, {"federation": {"resolution": "consumer"}},
])
def test_absent_or_consumer_resolution_signal_preserves_catalog_resolution(
    capabilities, capability_validator
):
    capability_validator.validate(capabilities if capabilities is not None else {})
    local = Mock(side_effect=missing())
    remote = Mock(return_value=RESOURCE)
    result = resolve_resource_read(
        XID, "entity", Source("local", local, capabilities), [Source("remote", remote)]
    )
    assert result == {"origin": "remote", "target": XID, "value": RESOURCE}
    local.assert_called_once_with("entity", XID)
    remote.assert_called_once_with("entity", XID)


@pytest.mark.parametrize("operation,target,value", [
    ("entity", XID, RESOURCE),
    ("entity", XID + "/meta", {"xid": XID + "/meta", "defaultversionid": "v1"}),
    ("entity", XID + "/versions/v1", {"xid": XID + "/versions/v1", "versionid": "v1"}),
    ("document", XID, b"combined document"),
    ("document", XID + "/versions/v1", b""),
])
def test_producer_resolved_view_is_read_once_without_catalog_traversal(operation, target, value):
    read = Mock(return_value=value)
    source = Source("combined", read, {"federation": {"resolution": "producer"}})
    catalog = Mock(side_effect=AssertionError("Catalog must not be traversed"))
    result = resolve_resource_read(target, operation, source, catalog)
    assert result == {"origin": "combined", "target": target, "value": value}
    read.assert_called_once_with(operation, target)
    catalog.assert_not_called()


@pytest.mark.parametrize("code", [
    "not_found", "policy_denied", "integrity_error", "unavailable", "inconsistent_snapshot",
])
def test_producer_view_errors_do_not_trigger_consumer_fallback(code):
    failure = FederationError(code, "Producer read failed")
    local = Mock(side_effect=failure)
    remote = Mock(side_effect=AssertionError("No retry in another Registry"))
    with pytest.raises(FederationError) as error:
        resolve_resource_read(
            XID, "document",
            Source("combined", local, {"federation": {"resolution": "producer"}}),
            [Source("remote", remote)],
        )
    assert error.value is failure
    local.assert_called_once_with("document", XID)
    remote.assert_not_called()


@pytest.mark.parametrize("capabilities,code", [
    ([], "invalid_package"),
    ({"federation": None}, "invalid_package"),
    ({"federation": True}, "invalid_package"),
    ({"federation": {}}, "invalid_package"),
    ({"federation": {"resolution": 1}}, "invalid_package"),
    ({"federation": {"resolution": "producer", "fallback": True}}, "unsupported_operation"),
    ({"federation": {"resolution": "server"}}, "unsupported_operation"),
    ({"federation": {"resolution": "Producer"}}, "unsupported_operation"),
])
def test_invalid_resolution_signals_fail_before_reading_sources(
    capabilities, code, capability_validator
):
    assert not capability_validator.is_valid(capabilities)
    read = Mock()
    with pytest.raises(FederationError) as error:
        resolve_resource_read(XID, "entity", Source("root", read, capabilities), [])
    assert error.value.code == code
    read.assert_not_called()


@pytest.mark.parametrize("value", [None, {}, {"xid": XID + "/versions/wrong"}])
def test_producer_mode_still_validates_returned_entity_identity(value):
    read = Mock(return_value=value)
    remote = Mock()
    with pytest.raises(FederationError) as error:
        resolve_resource_read(
            XID, "entity",
            Source("combined", read, {"federation": {"resolution": "producer"}}),
            [Source("remote", remote)],
        )
    assert error.value.code == "invalid_package"
    read.assert_called_once_with("entity", XID)
    remote.assert_not_called()


def test_published_resolution_signals_match_the_capability_schema(capability_validator):
    root = Path(__file__).resolve().parent.parent / "workingdrafts" / "federation"
    text = (root / "spec.md").read_text(encoding="utf-8")
    examples = [json.loads(block) for block in re.findall(r"```json\n(.*?)```", text, re.S)]
    capabilities = [value for value in examples if "federation" in value]
    assert len(capabilities) == 2
    assert [resolution_owner(value) for value in capabilities] == ["producer", "consumer"]
    for value in capabilities:
        capability_validator.validate(value)


@pytest.mark.parametrize("binding", ["file", "oci"])
def test_snapshot_capabilities_preserve_producer_resolution_without_catalog_reads(tmp_path, binding):
    if binding == "file":
        from mapping_examples import DocumentTree, MemoryStore, encode_tree, sample_records
        records, documents = sample_records()
        records[0]["entity"]["capabilities"]["federation"] = {"resolution": "producer"}
        reader = DocumentTree(MemoryStore(encode_tree(records, documents)))
        capabilities = reader.capabilities()
        target = "/documents/main/assets/item"
        expected = b'{"hello":"world"}\n'
        read = Mock(side_effect=lambda operation, xid: reader.document(xid))
    else:
        from oci_examples import FixtureLayout, build_layout, sample_records
        records, documents = sample_records()
        records[0]["entity"]["capabilities"]["federation"] = {"resolution": "producer"}
        build_layout(tmp_path, records, documents)
        reader = FixtureLayout(tmp_path)
        capabilities = reader.lookup("/", operation="capabilities")["value"]
        target = "/dirs/main/files/sample"
        expected = b'{"type":"string"}\n'
        read = Mock(side_effect=lambda operation, xid: reader.lookup(xid, operation=operation)["data"])
    assert capabilities["federation"] == {"resolution": "producer"}
    catalog = Mock(side_effect=AssertionError("Do not resolve the stored view again"))
    result = resolve_resource_read(target, "document", Source(binding, read, capabilities), catalog)
    assert result == {"origin": binding, "target": target, "value": expected}
    read.assert_called_once_with("document", target)
    catalog.assert_not_called()
