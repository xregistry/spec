from copy import deepcopy
import json
from pathlib import Path
import re

import pytest

from message_history_637 import check_retained_history, match_versions, select_version


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def history():
    source = (ROOT / "message" / "spec.md").read_text(encoding="utf-8")
    section = source.split("A customized model with `maxversions` set to `2`", 1)[1]
    return json.loads(re.search(r"```json\n(.*?)\n```", section, re.S)[1])


def test_default_model_retains_singleton_but_custom_histories_are_valid(history):
    model = json.loads((ROOT / "message" / "model.json").read_text(encoding="utf-8"))
    limit = model["groups"]["messagegroups"]["resources"]["messages"]["maxversions"]
    assert limit == 1
    singleton = deepcopy(history)
    singleton["versions"] = {"v2": singleton["versions"]["v2"]}
    check_retained_history(singleton, limit)
    check_retained_history(history, 2)
    check_retained_history(history, 0)
    with pytest.raises(ValueError, match="retained Version limit"):
        check_retained_history(history, limit)


def test_precise_reference_stays_on_its_version_when_default_changes(history):
    xid = history["xid"]
    assert select_version(history, xid)["versionid"] == "v2"
    assert select_version(history, xid + "/versions/v1")["datacontenttype"] == "application/json"
    assert select_version(history, xid + "/versions/v2")["datacontenttype"] == "application/xml"
    history["meta"]["defaultversionid"] = "v1"
    assert select_version(history, xid)["versionid"] == "v1"
    assert select_version(history, xid + "/versions/v2")["versionid"] == "v2"


def test_missing_precise_version_is_not_replaced_with_default(history):
    original = deepcopy(history)
    assert select_version(history, history["xid"] + "/versions/not-retained") is None
    assert history == original
    selected = select_version(history, history["xid"])
    selected["datacontenttype"] = "text/plain"
    assert history == original


def test_type_only_matching_reports_both_versions_not_the_default(history):
    result = match_versions(history, "com.example.order")
    assert result.status == "ambiguous"
    assert set(result.version_ids) == {"v1", "v2"}
    history["meta"]["defaultversionid"] = "v1"
    assert match_versions(history, "com.example.order") == result


def test_explicit_payload_discriminator_resolves_example_ambiguity(history):
    result = match_versions(history, "com.example.order", "application/json")
    assert result.status == "unique"
    assert result.version_ids == ("v1",)
    result = match_versions(history, "com.example.order", "application/xml")
    assert result.status == "unique"
    assert result.version_ids == ("v2",)
    result = match_versions(history, "com.example.order", "text/plain")
    assert result.status == "unmatched"
    assert result.version_ids == ()
    assert match_versions(history, "com.example.other").status == "unmatched"


@pytest.mark.parametrize("invalid_limit", [-1, True, "2"])
def test_invalid_history_limits_are_not_treated_as_unlimited(history, invalid_limit):
    with pytest.raises(ValueError, match="unsigned integer"):
        check_retained_history(history, invalid_limit)


@pytest.mark.parametrize("mutation", ["empty", "missing-default", "wrong-identity"])
def test_invalid_retained_snapshots_report_specific_errors(history, mutation):
    if mutation == "empty":
        history["versions"] = {}
        error = "retained Version"
    elif mutation == "missing-default":
        history["meta"]["defaultversionid"] = "gone"
        error = "default Version"
    else:
        history["versions"]["v1"]["versionid"] = "v2"
        error = "identity disagree"
    with pytest.raises(ValueError, match=error):
        check_retained_history(history, 2)


@pytest.mark.parametrize("suffix", ["/versions/", "/versions/v1/other", "/other"])
def test_invalid_reference_is_not_a_resource_default_lookup(history, suffix):
    with pytest.raises(ValueError, match="reference"):
        select_version(history, history["xid"] + suffix)
