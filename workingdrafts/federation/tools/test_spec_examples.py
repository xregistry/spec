"""Keep the federation selection walkthrough executable and byte-accurate."""

import pytest

from workingdrafts.federation.tools.federation_examples import (
    FederationError, select_label, select_version,
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
 'registry': {'registryid': 'first',
              'modelsource': {'groups': {'documents': {'singular': 'document',
                                                       'resources': {'assets': {'singular': 'asset'}}},
                                         'mirrors': {'singular': 'mirror',
                                                     'ximportresources': ['/documents/assets']},
                                         'independent': {'singular': 'independent',
                                                         'resources': {'assets': {'singular': 'asset'}}}}},
              'documents': {'main': {'assets': {'item': {'assetid': 'item',
                                                         'meta': {'defaultversionid': 'v1'},
                                                         'versions': {'v1': {'versionid': 'v1',
                                                                             'labels': {'stage': 'production'}},
                                                                      'v2': {'versionid': 'v2',
                                                                             'labels': {'stage': 'development'}}}}}}},
              'mirrors': {'local': {'assets': {'copy': {'meta': {'xref': '/documents/main/assets/item'}},
                                               'dangling': {'meta': {'xref': '/documents/main/assets/missing'}},
                                               'chain': {'meta': {'xref': '/mirrors/local/assets/copy'}}}}}}}
