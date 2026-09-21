"""Offline UA identity, namespace, Browse and FileTransfer conformance."""

import base64
import copy
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from workingdrafts.bindings.tools import opcua_examples as ua
from workingdrafts.federation.tools.federation_examples import FederationError


ROOT = Path(__file__).resolve().parents[2] / "federation" / "samples" / "opcua"
REFERENCES = json.loads((ROOT / "references.json").read_text(encoding="utf-8"))
SEQUENCES = json.loads((ROOT / "read-sequences.json").read_text(encoding="utf-8"))
REF = {case["name"]: case for case in REFERENCES["cases"]}
SEQ = {case["name"]: case for case in SEQUENCES["cases"]}


@pytest.mark.parametrize("case", REFERENCES["cases"], ids=lambda case: case["name"])
def test_opcua_reference_vectors_execute_native_mapping(case):
    operation = ua.map_registry_root if case["kind"] == "root" else ua.map_expanded_nodeid
    before = copy.deepcopy(case["input"])
    if "error" in case:
        with pytest.raises(FederationError) as error:
            operation(**case["input"])
        assert error.value.code == case["error"]
    else:
        assert operation(**case["input"]) == case["expected"]
    assert case["input"] == before


def test_opcua_namespace_and_server_table_remapping_preserves_portable_identity():
    first = ua.map_expanded_nodeid(**REF["remote-source-tables-to-target-seven"]["input"])
    second = ua.map_expanded_nodeid(**REF["reindexed-source-and-target"]["input"])
    assert first["nodeId"] == "ns=7;s=ItemV1"
    assert second["nodeId"] == "ns=2;s=ItemV1"
    assert first["portable"] == second["portable"] == (
        "svu=urn:example:ua:remote;nsu=urn:example:registry;s=ItemV1"
    )
    assert first["applicationuri"] == second["applicationuri"] == "urn:example:ua:remote"
    assert first["local"] is second["local"] is False


def test_opcua_explicit_registry_root_is_not_endpoint_or_application_identity():
    first = ua.map_registry_root(**REF["advertised-root"]["input"])
    second = ua.map_registry_root(**REF["another-root-at-same-endpoint"]["input"])
    assert first["endpoint"] == second["endpoint"] == "opc.tcp://ua.example.com:4840"
    assert first["applicationuri"] == second["applicationuri"] == "urn:example:ua:first"
    assert first["nodeId"] == "ns=3;s=FirstRegistry"
    assert second["nodeId"] == "ns=1;s=SecondRegistry"
    assert first["registryroot"] != second["registryroot"]


@pytest.mark.parametrize("node", [
    "i=0", "i=4294967296", "g=-", "ns=2;s=Root",
    "svu=urn:server;s=Root", "nsu=;s=Root", "b=!!", "s=",
])
def test_opcua_invalid_or_null_advertised_root_is_not_portable(node):
    with pytest.raises(FederationError) as error:
        ua.validate_registry_root(node)
    assert error.value.code == "invalid_package"


@pytest.mark.parametrize("node,identifier", [
    ("i=4294967295", 4294967295),
    ("nsu=urn:example:registry;s=a;b", "a;b"),
    ("nsu=urn:example%3Bregistry;s=Root", "Root"),
    ("b=AP8=", "AP8="),
])
def test_opcua_nodeid_identifier_bounds_and_namespace_encoding(node, identifier):
    parsed = ua.validate_registry_root(node)
    assert parsed.identifier == identifier
    assert parsed.portable() == node
    assert ua.parse_nodeid(parsed.portable()) == parsed


@pytest.mark.parametrize("field,value,code", [
    ("serverIndex", 99, "invalid_package"),
    ("namespaceIndex", 65536, "invalid_package"),
    ("identifierType", "Unknown", "invalid_package"),
    ("target_applicationuri", "opc.tcp://remote.example.com", "integrity_error"),
    ("target_namespace_array", [ua.UA_NAMESPACE, "urn:other"], "not_found"),
])
def test_opcua_remote_mapping_failures_do_not_default_to_namespace_zero(field, value, code):
    args = copy.deepcopy(REF["remote-source-tables-to-target-seven"]["input"])
    if field in args:
        args[field] = value
    else:
        args["reference"][field] = value
    with pytest.raises(FederationError) as error:
        ua.map_expanded_nodeid(**args)
    assert error.value.code == code


@pytest.mark.parametrize("case", SEQUENCES["cases"], ids=lambda case: case["name"])
def test_opcua_read_sequence_vectors_execute_services(case):
    before = copy.deepcopy(case["input"])
    if "error" in case:
        with pytest.raises(FederationError) as error:
            ua.interpret_read_sequence(**case["input"])
        assert error.value.code == case["error"]
    else:
        result = ua.interpret_read_sequence(**case["input"])
        assert result == case["expected"]
    assert case["input"] == before


@pytest.mark.parametrize("case,data,version,trace", [
    ("default-v1-short-chunks", b'{"type":"string"}', "v1",
     ["Open", "Read", "Read", "Read", "Close"]),
    ("explicit-v2-binary", b"\x00\xff", "v2", ["Open", "Read", "Read", "Close"]),
    ("zero-byte-v3", b"", "v3", ["Open", "Read", "Close"]),
])
def test_opcua_filetransfer_exact_bytes_default_and_empty_lifecycle(case, data, version, trace):
    result = ua.interpret_read_sequence(**SEQ[case]["input"])
    assert base64.b64decode(result["data"], validate=True) == data
    assert result["size"] == len(data)
    assert result["selectedXid"] == "/documents/main/assets/item/versions/" + version
    assert result["trace"] == trace
    assert result["complete"] is True
    assert result["consistency"] == "observed"


def test_opcua_metadata_only_catalog_never_opens_a_file():
    with patch.object(ua, "_file_sequence", side_effect=AssertionError("Unexpected FileType read")):
        result = ua.interpret_read_sequence(**SEQ["metadata-only-catalog"]["input"])
        with pytest.raises(FederationError) as error:
            ua.interpret_read_sequence(**SEQ["metadata-only-document-rejected-before-open"]["input"])
    assert error.value.code == "unsupported_operation"
    assert result["trace"] == ["Read"]
    assert result["values"]["ResourceId"] == "bridge"
    assert isinstance(result["values"]["federationprofiles"], list)


@pytest.mark.parametrize("change,code", [
    ("missing-close", "inconsistent_snapshot"), ("missing-eof", "inconsistent_snapshot"),
    ("wrong-handle", "invalid_package"), ("wrong-session", "invalid_package"),
    ("wrong-object", "invalid_package"), ("changed-default", "inconsistent_snapshot"),
    ("wrong-selected-version", "integrity_error"), ("unsupported-core", "unsupported_version"),
])
def test_opcua_partial_or_misdirected_capture_is_not_success(change, code):
    sequence = copy.deepcopy(SEQ["default-v1-short-chunks"]["input"]["sequence"])
    if change == "missing-close":
        sequence["events"].pop()
    elif change == "missing-eof":
        sequence["events"].pop(-2)
    elif change == "wrong-handle":
        sequence["events"][1]["input"]["fileHandle"] = 99
    elif change == "wrong-session":
        sequence["events"][1]["session"] = "another-session"
    elif change == "wrong-object":
        sequence["events"][1]["nodeId"] = "ns=3;s=Other"
    elif change == "changed-default":
        sequence["after"]["defaultversionid"] = "v2"
    elif change == "wrong-selected-version":
        sequence["selectedXid"] = "/documents/main/assets/item/versions/v2"
    else:
        sequence["specversion"] = "1.0-rc2"
    with pytest.raises(FederationError) as error:
        ua.interpret_read_sequence(sequence)
    assert error.value.code == code


@pytest.mark.parametrize("failed,cleanup", [
    ("Open", False), ("Read", False), ("Read", True), ("Close", False),
])
def test_opcua_filetransfer_failure_preserves_primary_error_and_cleanup(failed, cleanup):
    sequence = copy.deepcopy(SEQ["explicit-v2-binary"]["input"]["sequence"])
    events = sequence["events"]
    if failed == "Open":
        sequence["events"] = [events[0]]
        events[0]["status"] = "Bad_UserAccessDenied"
    elif failed == "Read":
        sequence["events"] = [events[0], events[1], events[-1]]
        events[1]["status"] = "Bad_CommunicationError"
        if cleanup:
            events[-1]["status"] = "Bad_NotSupported"
    else:
        events[-1]["status"] = "Bad_CommunicationError"
    with pytest.raises(FederationError) as error:
        ua.interpret_read_sequence(sequence)
    assert error.value.code == ("policy_denied" if failed == "Open" else "unavailable")
    assert failed + ":" in str(error.value)
    if cleanup:
        assert "Close cleanup failed: unsupported_operation" in str(error.value)
    elif failed == "Read":
        assert "cleanup" not in str(error.value)


@pytest.mark.parametrize("budget,valid", [(16, False), (17, True), (18, True)])
def test_opcua_filetransfer_byte_budget_boundary(budget, valid):
    sequence = copy.deepcopy(SEQ["default-v1-short-chunks"]["input"]["sequence"])
    if valid:
        assert ua.interpret_read_sequence(sequence, max_bytes=budget)["size"] == 17
    else:
        sequence["events"].pop(-2)
        with pytest.raises(FederationError) as error:
            ua.interpret_read_sequence(sequence, max_bytes=budget)
        assert error.value.code == "limit_exceeded"


def test_opcua_browse_consumes_reused_continuation_points_until_complete():
    sequence = SEQ["three-browse-pages-with-reused-continuation-token"]["input"]["sequence"]
    result = ua.interpret_read_sequence(sequence)
    assert result["trace"] == ["Browse", "BrowseNext", "BrowseNext"]
    assert result["complete"] is True
    assert len(result["references"]) == 3
    truncated = copy.deepcopy(sequence)
    truncated["events"].pop()
    with pytest.raises(FederationError) as error:
        ua.interpret_read_sequence(truncated)
    assert error.value.code == "inconsistent_snapshot"
    with pytest.raises(FederationError) as error:
        ua.interpret_read_sequence(sequence, max_references=2)
    assert error.value.code == "limit_exceeded"


def test_opcua_namespace_refresh_is_parameterless_then_file_transfer():
    case = next(case for case in SEQUENCES["cases"]
                if "expected" in case and case["input"]["sequence"]["kind"] == "namespace-file")
    result = ua.interpret_read_sequence(**case["input"])
    assert result["trace"][0:2] == ["ExportNamespace", "Open"]
    assert result["trace"][-1] == "Close"
    assert base64.b64decode(result["data"]).startswith(b"<")
    sequence = copy.deepcopy(case["input"]["sequence"])
    sequence["events"][0]["output"] = {"data": "PHgvPg=="}
    with pytest.raises(FederationError) as error:
        ua.interpret_read_sequence(sequence)
    assert error.value.code == "invalid_package"


@pytest.mark.parametrize("status,code", [
    ("Good", None), ("Bad_NotSupported", "unsupported_operation"),
    ("Bad_NodeIdUnknown", "not_found"), ("Bad_UserAccessDenied", "policy_denied"),
    ("Bad_InvalidArgument", "invalid_package"),
    ("Bad_ContinuationPointInvalid", "inconsistent_snapshot"),
    ("Bad_ResponseTooLarge", "limit_exceeded"), ("Bad_CommunicationError", "unavailable"),
    ("Uncertain", "unavailable"),
])
def test_opcua_statuscodes_preserve_failure_distinctions(status, code):
    assert ua.map_status(status) == code
