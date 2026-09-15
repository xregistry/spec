import json
import re
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from test_samples import _unique_json_object


ROOT = Path(__file__).resolve().parents[1]


class AdmissionError(ValueError):
    pass


def _primer_section(start, end):
    text = (ROOT / "core" / "primer.md").read_text(encoding="utf-8")
    return text.split(start, 1)[1].split(end, 1)[0]


def _walkthrough():
    section = _primer_section(
        "### 11.8. Default Version and Maximum Versions\n", "\n### 11.9."
    )
    lines = [line for line in section.splitlines() if line.startswith("| ")]
    assert len(lines) == 12
    assert "versionmode: createdat" in section
    assert "performs no optional pruning" in " ".join(section.split())
    assert "/dirs/d1/files/f1/meta" in section
    return [
        [cell.strip().replace("`", "") for cell in line.strip("|").split("|")]
        for line in lines[2:]
    ]


def _model_definition():
    section = _primer_section(
        "## 15. Why are some (conditional) read-only attributes not ignored?\n",
        "\n## 16.",
    )
    block = re.search(r"```yaml\n(.*?)\n```", section, re.S)[1]
    return json.loads(block, object_pairs_hook=_unique_json_object)[
        "metaattributes"
    ]["defaultversionsticky"]


def _instant(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class _DefaultsCapture:
    def __init__(self):
        self.state = {
            "maxversions": 2,
            "sticky_definition": {"enum": [False, True], "default": False},
            "resources": {
                "f1": {
                    "meta": {
                        "defaultversionid": "v2",
                        "defaultversionsticky": True,
                        "epoch": 7,
                    },
                    "versions": {
                        "v2": {"createdat": "2030-01-01T00:00:00Z", "epoch": 1, "payload": "two"},
                        "v4": {"createdat": "2030-01-01T00:00:01Z", "epoch": 1, "payload": "four"},
                    },
                },
            },
        }

    @staticmethod
    def _ordered(resource):
        return sorted(
            resource["versions"],
            key=lambda version: _instant(resource["versions"][version]["createdat"]),
            reverse=True,
        )

    @classmethod
    def _prune(cls, resource, limit):
        if limit == 0:
            return
        for version in reversed(cls._ordered(resource)):
            if len(resource["versions"]) <= limit:
                break
            if version != resource["meta"]["defaultversionid"]:
                del resource["versions"][version]

    def set_limit(self, limit):
        if type(limit) is not int or limit < 0:
            raise AdmissionError("invalid_attribute")
        if limit == 1 and any(
            resource["meta"]["defaultversionsticky"]
            for resource in self.state["resources"].values()
        ):
            raise AdmissionError("setdefaultversionsticky_false")
        staged = deepcopy(self.state)
        staged["maxversions"] = limit
        for resource in staged["resources"].values():
            self._prune(resource, limit)
        self.state = staged

    def create(self, version):
        staged = deepcopy(self.state)
        resource = staged["resources"]["f1"]
        if version in resource["versions"]:
            raise AdmissionError("expected_a_new_version")
        latest = max(_instant(value["createdat"]) for value in resource["versions"].values())
        resource["versions"][version] = {
            "createdat": (latest + timedelta(seconds=1)).isoformat().replace("+00:00", "Z"),
            "epoch": 1,
            "payload": version,
        }
        if not resource["meta"]["defaultversionsticky"]:
            resource["meta"]["defaultversionid"] = self._ordered(resource)[0]
        resource["meta"]["epoch"] += 1
        self._prune(resource, staged["maxversions"])
        self.state = staged

    def patch_meta(self, body):
        staged = deepcopy(self.state)
        resource = staged["resources"]["f1"]
        meta = resource["meta"]
        sticky = body.get("defaultversionsticky", meta["defaultversionsticky"])
        if "defaultversionsticky" not in body and "defaultversionid" in body:
            sticky = body["defaultversionid"] is not None
        if sticky is None:
            sticky = False
        if type(sticky) is not bool or sticky not in staged["sticky_definition"]["enum"]:
            raise AdmissionError("invalid_attribute")
        if sticky and staged["maxversions"] == 1:
            raise AdmissionError("setdefaultversionsticky_false")
        if not sticky and body.get("defaultversionid") is not None:
            raise NotImplementedError("combined non-sticky ID requests are outside this capture")
        selected = body.get("defaultversionid", meta["defaultversionid"])
        if sticky and selected not in resource["versions"]:
            raise AdmissionError("unknown_id")
        meta["defaultversionsticky"] = sticky
        meta["defaultversionid"] = selected if sticky else self._ordered(resource)[0]
        meta["epoch"] += 1
        self.state = staged

    def constrain_stickiness(self, definition):
        allowed, default = definition["enum"], definition["default"]
        if (
            not allowed
            or any(type(value) is not bool for value in allowed)
            or type(default) is not bool
            or default not in allowed
            or any(
                resource["meta"]["defaultversionsticky"] not in allowed
                for resource in self.state["resources"].values()
            )
        ):
            raise AdmissionError("invalid_attribute")
        staged = deepcopy(self.state)
        staged["sticky_definition"] = deepcopy(definition)
        self.state = staged

    def write_isdefault(self, version, value):
        # The flag is a projection, but a write still touches the Version.
        resource = self.state["resources"]["f1"]
        resource["versions"][version]["epoch"] += 1
        return version == resource["meta"]["defaultversionid"]

    def view(self):
        resource = self.state["resources"]["f1"]
        return (
            self._ordered(resource),
            resource["meta"]["defaultversionid"],
            resource["meta"]["defaultversionsticky"],
            self.state["maxversions"],
        )


def test_primer_612_walkthrough_applies_meta_controls_and_atomic_rejection():
    capture = _DefaultsCapture()
    rejected = 0
    for index, (action, result, versions, default, sticky, limit) in enumerate(_walkthrough()):
        before = deepcopy(capture.state)
        actual_result = "OK"
        try:
            if action == "Initial state":
                assert index == 0
            elif match := re.fullmatch(r"Set maxversions to (\d+)", action):
                capture.set_limit(int(match[1]))
            elif match := re.fullmatch(r"Create (v\d+)", action):
                capture.create(match[1])
            else:
                body = json.loads(action, object_pairs_hook=_unique_json_object)
                assert set(body) <= {"defaultversionid", "defaultversionsticky"}
                capture.patch_meta(body)
        except AdmissionError as error:
            actual_result = str(error)
            rejected += 1
            assert capture.state == before
        assert actual_result == result, action
        assert capture.view() == (
            versions.split(", "), default, json.loads(sticky), int(limit),
        ), action
    assert rejected == 1
    assert capture.view() == (["v8"], "v8", False, 1)


def test_primer_612_unstick_selects_newest_without_modifying_versions():
    capture = _DefaultsCapture()
    capture.set_limit(0)
    capture.create("v5")
    capture.patch_meta({"defaultversionid": "v5", "defaultversionsticky": True})
    capture.create("v6")
    capture.create("v7")
    before = deepcopy(capture.state["resources"]["f1"])
    capture.patch_meta({"defaultversionsticky": False})
    after = capture.state["resources"]["f1"]
    assert after["versions"] == before["versions"]
    assert after["meta"] == {
        "defaultversionid": "v7", "defaultversionsticky": False,
        "epoch": before["meta"]["epoch"] + 1,
    }
    assert capture.state["maxversions"] == 0


def test_primer_612_limit_one_checks_every_resource_before_pruning():
    capture = _DefaultsCapture()
    capture.set_limit(0)
    capture.state["resources"]["f2"] = deepcopy(capture.state["resources"]["f1"])
    capture.patch_meta({"defaultversionsticky": False})
    before = deepcopy(capture.state)
    with pytest.raises(AdmissionError, match="setdefaultversionsticky_false"):
        capture.set_limit(1)
    assert capture.state == before
    assert all(len(resource["versions"]) == 2 for resource in capture.state["resources"].values())


def test_primer_612_positive_limit_preserves_the_sticky_default():
    capture = _DefaultsCapture()
    original = deepcopy(capture.state["resources"]["f1"]["versions"]["v2"])
    capture.create("v5")
    assert capture.view() == (["v5", "v2"], "v2", True, 2)
    assert capture.state["resources"]["f1"]["versions"]["v2"] == original
    assert "v4" not in capture.state["resources"]["f1"]["versions"]


def test_primer_612_createdat_order_is_not_identifier_order():
    capture = _DefaultsCapture()
    capture.state["maxversions"] = 0
    resource = capture.state["resources"]["f1"]
    resource["versions"] = {
        "v100": {"createdat": "2030-01-01T00:00:00Z"},
        "v20": {"createdat": "2030-01-01T00:00:01Z"},
        "v1": {"createdat": "2030-01-01T00:00:02Z"},
    }
    resource["meta"].update(defaultversionid="v1", defaultversionsticky=False)
    capture.set_limit(2)
    assert capture.view() == (["v1", "v20"], "v1", False, 2)


def test_primer_612_metaattribute_enum_and_default_are_real_constraints():
    definition = _model_definition()
    core = (ROOT / "core" / "spec.md").read_text(encoding="utf-8")
    core_section = core.split("#### `defaultversionsticky` Attribute\n", 1)[1].split(
        "\n### Version Entity", 1
    )[0]
    core_fragment = re.search(r"```yaml\n(.*?)\n```", core_section, re.S)[1]
    assert definition == json.loads("{" + core_fragment + "}")["defaultversionsticky"]
    assert definition["enum"] == [False]
    assert definition["default"] is False
    capture = _DefaultsCapture()
    capture.patch_meta({"defaultversionsticky": False})
    capture.constrain_stickiness(definition)
    before = deepcopy(capture.state)
    for body in ({"defaultversionsticky": True}, {"defaultversionid": "v2"}):
        with pytest.raises(AdmissionError, match="invalid_attribute"):
            capture.patch_meta(body)
        assert capture.state == before
    capture.patch_meta({"defaultversionsticky": False})
    assert capture.view() == (["v4", "v2"], "v4", False, 2)


def test_primer_612_isdefault_is_read_only_not_a_selection_control():
    capture = _DefaultsCapture()
    before = deepcopy(capture.state["resources"]["f1"])
    assert capture.write_isdefault("v4", True) is False
    after = capture.state["resources"]["f1"]
    assert after["meta"] == before["meta"]
    assert after["versions"]["v4"]["epoch"] == before["versions"]["v4"]["epoch"] + 1
    assert after["versions"]["v4"]["payload"] == before["versions"]["v4"]["payload"]
    assert "isdefault" not in after["versions"]["v4"]
    core = (ROOT / "core" / "spec.md").read_text(encoding="utf-8")
    section = core.split("#### `isdefault` Attribute\n", 1)[1].split("\n#### ", 1)[0]
    assert "MUST be a [read-only]" in section
    primer = (ROOT / "core" / "primer.md").read_text(encoding="utf-8")
    assert "`setdefaultversionsticky`" not in primer
    assert "default=true" not in primer
    assert "isdefault=true" not in primer


@pytest.mark.parametrize("candidate", ["v2", "missing"])
def test_primer_612_capture_does_not_decide_discarded_id_policy(candidate):
    capture = _DefaultsCapture()
    before = deepcopy(capture.state)
    with pytest.raises(NotImplementedError, match="outside this capture"):
        capture.patch_meta({"defaultversionid": candidate, "defaultversionsticky": False})
    assert capture.state == before


@pytest.mark.parametrize("limit", [-1, True])
def test_primer_612_invalid_model_limit_is_rejected_without_mutation(limit):
    capture = _DefaultsCapture()
    before = deepcopy(capture.state)
    with pytest.raises(AdmissionError, match="invalid_attribute"):
        capture.set_limit(limit)
    assert capture.state == before


def test_primer_612_invalid_selection_and_stickiness_preserve_state():
    capture = _DefaultsCapture()
    before = deepcopy(capture.state)
    with pytest.raises(AdmissionError, match="unknown_id"):
        capture.patch_meta({"defaultversionid": "missing", "defaultversionsticky": True})
    assert capture.state == before
    capture.patch_meta({"defaultversionsticky": False})
    capture.set_limit(1)
    before = deepcopy(capture.state)
    with pytest.raises(AdmissionError, match="setdefaultversionsticky_false"):
        capture.patch_meta({"defaultversionsticky": True})
    assert capture.state == before
