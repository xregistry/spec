from copy import deepcopy
import json
from pathlib import Path
import re

import pytest

from envelope_binding_641 import check_binding


ROOT = Path(__file__).resolve().parents[2]


def _cloud_event(envelope="CloudEvents/1.0"):
    return {"envelope": envelope, "envelopemetadata": {}}


def test_actual_unbound_group_preserves_payload_only_and_protocol_only_forms():
    source = (ROOT / "message" / "spec.md").read_text(encoding="utf-8")
    section = source.split("An unbound Message Group can contain", 1)[1]
    group = json.loads(re.search(r"```json\n(.*?)\n```", section, re.S)[1])
    assert "envelope" not in group
    payload = group["messages"]["payload"]
    protocol = group["messages"]["protocol"]
    assert "envelope" not in payload and "protocol" not in payload
    assert payload["dataschemaformat"] == "JSONSchema/draft-07"
    assert payload["dataschema"] == {"type": "object"}
    assert "envelope" not in protocol and protocol["protocol"] == "HTTP/1.1"
    assert protocol["protocoloptions"] == {}
    assert check_binding(group, payload) == "compatible"
    assert check_binding(group, protocol) == "compatible"


def test_endpoint_embedded_example_obeys_its_applicable_binding_context():
    source = (ROOT / "endpoint" / "spec.md").read_text(encoding="utf-8")
    section = source.split("#### `messages`\n", 1)[1]
    endpoint = json.loads(re.search(r"```yaml\n(.*?)\n```", section, re.S)[1])
    message = endpoint["messages"]["myevent"]
    assert check_binding(endpoint, message, kind="endpoint") == "compatible"
    endpoint["envelope"] = "CloudEvents"
    assert check_binding(endpoint, message, kind="endpoint") == "compatible"
    endpoint["envelope"] = "Other/1.0"
    with pytest.raises(ValueError, match="conflicting envelope names"):
        check_binding(endpoint, message, kind="endpoint")


@pytest.mark.parametrize("kind", ["messagegroup", "endpoint"])
def test_bound_context_rejects_missing_effective_envelope_without_inheriting_it(kind):
    context = {"envelope": "CloudEvents/1.0"}
    message = {"datacontenttype": "application/json"}
    original = deepcopy(message)
    with pytest.raises(ValueError, match="requires an effective Message envelope"):
        check_binding(context, message, kind=kind)
    assert message == original
    assert check_binding({}, message, kind=kind) == "compatible"


def test_unbound_context_does_not_prohibit_message_envelope_or_invent_one():
    assert check_binding({}, _cloud_event()) == "compatible"
    assert check_binding({}, {"protocol": "HTTP/1.1", "protocoloptions": {}}) == "compatible"
    assert check_binding({}, {"datacontenttype": "application/xml"}) == "compatible"


@pytest.mark.parametrize("kind", ["messagegroup", "endpoint"])
def test_matching_envelope_is_case_insensitive_and_other_envelope_conflicts(kind):
    assert check_binding(
        {"envelope": "CLOUDEVENTS/1.0"}, _cloud_event("cloudevents/1.0"), kind=kind
    ) == "compatible"
    with pytest.raises(ValueError, match="conflicting envelope names"):
        check_binding({"envelope": "Other/1.0"}, _cloud_event(), kind=kind)


def test_group_version_is_exact_and_endpoint_name_only_can_be_refined():
    with pytest.raises(ValueError, match="conflicting Message Group envelope versions"):
        check_binding({"envelope": "CloudEvents/1.0"}, _cloud_event("CloudEvents/2.0"))
    assert check_binding(
        {"envelope": "CloudEvents"}, _cloud_event(), kind="endpoint"
    ) == "compatible"
    with pytest.raises(NotImplementedError, match="envelope-specific rules"):
        check_binding(
            {"envelope": "Other/1.0"}, _cloud_event("Other/1.0.1"), kind="endpoint"
        )


def test_borrowed_message_must_satisfy_each_owning_or_referencing_context():
    target = _cloud_event()
    original = deepcopy(target)
    assert check_binding({"envelope": "CloudEvents/1.0"}, target) == "compatible"
    assert check_binding({"envelope": "CloudEvents"}, target, kind="endpoint") == "compatible"
    with pytest.raises(ValueError, match="conflicting envelope names"):
        check_binding({"envelope": "Other/1.0"}, target, kind="endpoint")
    assert target == original


def test_resolved_base_selector_is_checked_but_unavailable_target_stays_unresolved():
    context = {"envelope": "CloudEvents/1.0"}
    effective = _cloud_event()
    effective["basemessage"] = "/messagegroups/shared/messages/base"
    original = deepcopy(effective)
    assert check_binding(context, effective) == "compatible"
    assert check_binding(context, None) == "unresolved"
    assert check_binding({}, None) == "unresolved"
    assert effective == original


def test_selected_envelope_keeps_its_existing_metadata_obligation():
    with pytest.raises(ValueError, match="requires metadata"):
        check_binding({}, {"envelope": "CloudEvents/1.0"})
    with pytest.raises(ValueError, match="requires metadata"):
        check_binding({}, {"envelope": "CloudEvents/1.0", "envelopemetadata": None})


@pytest.mark.parametrize("selector", [None, "", 1, "CloudEvents/", "/1.0", "CloudEvents"])
def test_invalid_message_selectors_fail_instead_of_becoming_unbound(selector):
    with pytest.raises(ValueError, match="selector"):
        check_binding({}, _cloud_event(selector))
