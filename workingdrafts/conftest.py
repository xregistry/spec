"""Read-only generated examples shared by conformance tests for one session."""

import pytest

from workingdrafts.bindings.tools import mapping_examples as mapping


def _write_files(root, files):
    for name, data in files.items():
        path = root.joinpath(*name.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return root


@pytest.fixture(scope="session")
def mapping_sample_root(tmp_path_factory):
    # Keep the legacy root oracle: sample_records deliberately has no full model.
    return _write_files(
        tmp_path_factory.mktemp("mapping"),
        mapping.encode_tree(*mapping.sample_records()),
    )


@pytest.fixture(scope="session")
def walkthrough_root(tmp_path_factory):
    return _write_files(tmp_path_factory.mktemp("walkthrough"), mapping.walkthrough_files())
