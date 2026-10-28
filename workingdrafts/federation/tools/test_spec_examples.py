"""Keep the federation selection walkthrough executable and byte-accurate."""

from copy import deepcopy
from unittest.mock import Mock

import pytest

from workingdrafts.federation.tools.federation_examples import (
    FederationError, select_label, select_profile, select_version, validate_profile,
)
from workingdrafts.federation.tools.federation_resolution_examples import Source, resolve_resource_read


def test_retained_selection_requests_labels_and_independent_contexts():
    request = SELECTION["requests"][0]
    assert request == {
        "operation": "collection", "target": "/documents/main/assets",
        "selector": {"label": "stage", "value": "PRODUCTION"},
    }
    assert select_label(
        SELECTION["labels"], request["selector"]["label"], request["selector"]["value"],
    )["assetid"] == "item"
    assert select_label(SELECTION["labels"], "note", "")["assetid"] == "item"
    with pytest.raises(FederationError) as missing:
        select_label(SELECTION["labels"], "stage", "prod*")
    assert missing.value.code == "not_found"
    assert SELECTION["requests"][1] == {
        "operation": "document", "target": "/documents/main/assets/item/versions/v1",
    }
    assert [(c["registryid"], c["endpoint"], c["xid"]) for c in SELECTION["contexts"]] == [
        ("first", "https://first.example.com/registry", "/documents/main/assets/item"),
        ("second", "https://second.example.com/registry", "/documents/main/assets/item"),
    ]
    resource = SELECTION["registry"]["documents"]["main"]["assets"]["item"]
    assert select_version(resource)["versionid"] == "v1"
    assert select_version(resource, "v2")["labels"] == {"stage": "development"}


@pytest.mark.parametrize("local_shadow", [True, False], ids=["unique-after-shadowing", "ambiguous-without-shadow"])
def test_published_selection_example_filters_after_resource_shadowing(local_shadow):
    collection = "/documents/main/assets"
    calls = []

    def resource(identifier, version, stage):
        return {
            "xid": collection + "/" + identifier, "assetid": identifier,
            "meta": {"defaultversionid": version},
            "versions": {version: {"versionid": version, "labels": {"stage": stage}}},
        }

    def source(name, entities):
        def read(operation, target):
            calls.append((name, operation, target))
            if target not in entities:
                raise FederationError("not_found", "Resource absent")
            entity = entities[target]
            if operation == "document":
                selected = select_version(entity)["versionid"]
                return f"source {name} version {selected}\n".encode()
            return entity
        return Source(name, read)

    local = source("Local", {collection + "/item": resource("item", "v1", "development")} if local_shadow else {})
    sources = [
        source("A", {collection + "/item": resource("item", "v2", "production")}),
        source("B", {collection + "/other": resource("other", "v7", "production")}),
    ]
    visible = [
        resolve_resource_read(collection + "/" + identifier, "entity", local, sources)
        for identifier in ("item", "other")
    ]
    effective = [{**select_version(item["value"]), **item["value"]} for item in visible]
    assert [item["origin"] for item in visible] == (["Local", "B"] if local_shadow else ["A", "B"])
    assert [select_version(item["value"])["versionid"] for item in visible] == (
        ["v1", "v7"] if local_shadow else ["v2", "v7"]
    )
    if local_shadow:
        selected = select_label(effective, "stage", "production")
        assert selected["assetid"] == "other"
        assert ("A", "entity", collection + "/item") not in calls
        document = resolve_resource_read(selected["xid"], "document", local, sources)
        assert document == {
            "origin": "B", "target": collection + "/other", "value": b"source B version v7\n"
        }
    else:
        with pytest.raises(FederationError) as error:
            select_label(effective, "stage", "production")
        assert error.value.code == "ambiguous"


# Independent baseline retained before sample-tree removal.
SELECTION = {'requests': [{'operation': 'collection',
               'target': '/documents/main/assets',
               'selector': {'label': 'stage', 'value': 'PRODUCTION'}},
              {'operation': 'document', 'target': '/documents/main/assets/item/versions/v1'}],
 'contexts': [{'registryid': 'first',
               'endpoint': 'https://first.example.com/registry',
               'xid': '/documents/main/assets/item'},
              {'registryid': 'second',
               'endpoint': 'https://second.example.com/registry',
               'xid': '/documents/main/assets/item'}],
 'labels': [{'assetid': 'item', 'labels': {'stage': 'production', 'note': ''}},
            {'assetid': 'other', 'labels': {'stage': 'development'}},
            {'assetid': 'unlabeled'}],
 'registry': {'documents': {'main': {'assets': {'item': {'assetid': 'item',
                                                         'meta': {'defaultversionid': 'v1'},
                                                         'versions': {'v1': {'versionid': 'v1',
                                                                             'labels': {'stage': 'production'}},
                                                                      'v2': {'versionid': 'v2',
                                                                             'labels': {'stage': 'development'}}}}}}}}}


@pytest.mark.parametrize(
    ("other", "supported", "name", "message"),
    [
        pytest.param(
            {"name": "example.extension", "endpoint": "/invalid", "priority": -1, "parameters": []},
            {"http"}, None, "Endpoint must be absolute", id="unsupported-malformed-fields",
        ),
    ],
)
def test_select_profile_filters_before_priority_and_parameter_validation(other, supported, name, message):
    winner = {"name": "http", "endpoint": "https://selected.example.test/nonroot/registry"}
    entry = {"federationprofiles": [deepcopy(other), winner]}
    before = deepcopy(entry)

    selected = select_profile(entry, supported, name=name)

    assert selected is winner
    assert selected == {"name": "http", "endpoint": "https://selected.example.test/nonroot/registry"}
    assert entry == before
    # Real validation would reject the other entry. Selection must not validate it.
    with pytest.raises(FederationError) as raised:
        validate_profile(other)
    assert raised.value.code == "invalid_package"
    assert str(raised.value) == message


@pytest.mark.parametrize(
    ("selected_profile", "code", "message"),
    [
        pytest.param(
            {"name": "oci", "endpoint": "oci://registry.example.test/catalog", "priority": 0},
            "invalid_package", "Missing or invalid OCI reference", id="selected-missing-reference",
        ),
    ],
)
def test_select_profile_does_not_fallback_after_selected_validation_error(selected_profile, code, message):
    alternate = {"name": "http", "endpoint": "https://alternate.example.test/registry", "priority": 5}
    entry = {"federationprofiles": [deepcopy(selected_profile), alternate]}
    before = deepcopy(entry)
    assert validate_profile(alternate) is None

    with pytest.raises(FederationError) as raised:
        select_profile(entry, {"git", "http", "oci"})

    assert raised.value.code == code
    assert str(raised.value) == message
    assert entry == before
    assert alternate == {"name": "http", "endpoint": "https://alternate.example.test/registry", "priority": 5}


XID = "/documents/main/assets/item"
RESOURCE = {"xid": XID, "assetid": "item"}


def missing():
    return FederationError("not_found", "Resource absent")


def test_missing_version_does_not_mix_resource_origins():
    chosen = Mock(side_effect=[RESOURCE, FederationError("not_found", "Version absent")])
    lower = Mock(side_effect=AssertionError("Must not borrow a Version"))
    local = Source("local", Mock(side_effect=missing()))
    sources = [Source("chosen", chosen), Source("lower", lower)]
    with pytest.raises(FederationError) as error:
        resolve_resource_read(XID + "/versions/v2", "document", local, sources)
    assert error.value.code == "not_found"
    assert str(error.value) == "Version absent"
    assert chosen.call_args_list == [(("entity", XID),), (("document", XID + "/versions/v2"),)]
    lower.assert_not_called()


@pytest.mark.parametrize("code", [
    "policy_denied",
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


@pytest.mark.parametrize("code", [
    "not_found",
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


@pytest.mark.parametrize("binding", ["file", "oci"])
def test_snapshot_capabilities_preserve_producer_resolution_without_catalog_reads(tmp_path, binding):
    if binding == "file":
        from workingdrafts.bindings.tools.mapping_examples import (
            DocumentTree, MemoryStore, encode_tree, sample_records,
        )
        records, documents = sample_records()
        records[0]["entity"]["capabilities"]["federation"] = {"resolution": "producer"}
        reader = DocumentTree(MemoryStore(encode_tree(records, documents)))
        capabilities = reader.capabilities()
        target = "/documents/main/assets/item"
        expected = b'{"hello":"world"}\n'
        read = Mock(side_effect=lambda operation, xid: reader.document(xid))
    else:
        from workingdrafts.bindings.tools.oci_examples import FixtureLayout, build_layout, sample_records
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
