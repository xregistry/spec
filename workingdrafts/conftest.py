"""Read-only generated examples shared by conformance tests for one session."""

import pytest

from workingdrafts.bindings.tools import mapping_examples as mapping
from workingdrafts.bindings.tools import oci_examples as oci


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


@pytest.fixture(scope="session")
def oci_sample_root(tmp_path_factory):
    root = tmp_path_factory.mktemp("oci")
    for reference in ("offline", "linked"):
        oci.build_layout(
            root / "layout", *oci.sample_records(linked=reference == "linked"),
            reference=reference, page_size=2,
        )
    return root
