"""Document-like spellings are ordinary metadata when hasdocument is false."""

import copy

import pytest

from workingdrafts.bindings.tools import mapping_examples as document
from workingdrafts.federation.tools.federation_examples import FederationError


VERSION = "/categories/main/registries/site/versions/v1"


@pytest.mark.parametrize("name,value", [
    ("registry", {"nested": None, "value": 42}),
    ("registrybase64", "not a document encoding"),
    ("registryurl", "https://must-not-fetch.invalid/blob"),
])
def test_modeled_metadata_only_names_roundtrip_without_document_acquisition(name, value):
    records, documents = document.sample_records()
    root = next(record for record in records if record["entity"]["xid"] == "/")
    definition = root["entity"]["modelsource"]["groups"]["categories"]["resources"]["registries"]
    definition["attributes"][name] = {"type": "any"}
    version = next(record for record in records if record["entity"]["xid"] == VERSION)
    version["entity"][name] = copy.deepcopy(value)
    tree = document.DocumentTree(document.MemoryStore(document.encode_tree(records, documents)))
    assert tree.metadata(VERSION)["entity"][name] == value
    assert not any(path.startswith("documents/") for path in tree.store.reads)
    with pytest.raises(FederationError) as error:
        tree.document(VERSION)
    assert error.value.code == "unsupported_operation"
    tree.validate()
