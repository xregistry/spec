"""Executable deployment examples against a reduced, single-threaded store."""

import base64
from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re

from jsonschema import Draft202012Validator
import pytest

from workingdrafts.federation.tools.federation_examples import FederationError, xid_parts
from workingdrafts.publication.tools.publication_examples import Channels, check_snapshot


FEDERATION = Path(__file__).resolve().parents[1]
DEPLOYMENT_SECTIONS = {
    "https": ("http-federation.md", "## Downstream Deployment"),
    "opcua": ("opcua.md", "### 10.7. Downstream deployment"),
    "mqtt": ("mqtt.md", "## Downstream Deployment"),
}
V1 = "/documents/main/assets/item/versions/v1"
V2 = "/documents/main/assets/item/versions/v2"


def describe(data):
    return {
        "size": str(len(data)),
        "digest": "sha256:" + hashlib.sha256(data).hexdigest(),
        "contenttype": "text/plain",
    }


def reject(code):
    raise FederationError(code, code)


@dataclass
class Stage:
    target: str
    mode: str
    descriptor: dict | None
    grant: int
    expires: int
    data: bytearray = field(default_factory=bytearray)


class ExampleReceiver:
    """Atomic transitions are single steps here; no transport or persistence."""

    def __init__(self, *, hasdocument=True, maxversions=0):
        self.hasdocument = hasdocument
        self.maxversions = maxversions
        self.clock = 0
        self.grant = 1
        self.stages = {}
        self.next_stage = 0
        self.versions = {}
        self.managed = set()
        self.generation = 0
        self.default = None
        self.sticky = False

    def authorize(self, target):
        path = xid_parts(target)
        if len(path) != 6 or path[:4] != ("documents", "main", "assets", "item"):
            reject("policy_denied")
        if any(other.casefold() == target.casefold() and other != target for other in self.versions):
            reject("conflict")
        if any(other not in self.managed for other in self.versions):
            reject("policy_denied")

    def inspect(self, target):
        self.authorize(target)
        mode = "replace" if target in self.versions else "create"
        return (self.grant, target, mode, self.generation)

    def begin(self, target, mode, descriptor):
        if self.inspect(target)[2] != mode:
            reject("conflict")
        if (descriptor is not None) != self.hasdocument:
            reject("validation_error")
        if descriptor is not None and int(descriptor["size"]) > 64:
            reject("limit_exceeded")
        if mode == "create" and self.maxversions and len(self.versions) >= self.maxversions:
            reject("validation_error")
        for stage_id, stage in self.stages.items():
            if stage.target == target and stage.grant == self.grant and stage.expires > self.clock:
                if (stage.mode, stage.descriptor) != (mode, descriptor):
                    reject("conflict")
                return stage_id
        self.next_stage += 1
        stage_id = f"upload-{self.next_stage}"
        self.stages[stage_id] = Stage(target, mode, descriptor, self.grant, self.clock + 5)
        return stage_id

    def live(self, stage_id):
        stage = self.stages.get(stage_id)
        if stage is None or stage.expires <= self.clock:
            reject("stage_unavailable")
        if stage.grant != self.grant:
            reject("policy_denied")
        self.authorize(stage.target)
        return stage

    def append(self, stage_id, offset, data):
        stage = self.live(stage_id)
        if offset != len(stage.data):
            raise FederationError("offset_mismatch", str(len(stage.data)))
        if not data or len(data) > 2:
            reject("limit_exceeded")
        if stage.descriptor is None or offset + len(data) > int(stage.descriptor["size"]):
            reject("integrity_error")
        stage.data.extend(data)
        return {"nextOffset": str(len(stage.data))}

    def abort(self, target, stage_id):
        self.authorize(target)
        stage = self.stages.get(stage_id)
        if not stage or (stage.target, stage.grant) != (target, self.grant) or stage.expires <= self.clock:
            return {"removed": False}
        del self.stages[stage_id]
        return {"removed": True}

    def commit(self, stage_id, expected, metadata=None):
        stage = self.live(stage_id)
        if expected != self.inspect(stage.target) or expected[2] != stage.mode:
            reject("stale_precondition")
        if stage.descriptor is not None and describe(stage.data) != stage.descriptor:
            reject("integrity_error")
        metadata = metadata or {}
        if set(metadata) - {"name"}:
            reject("validation_error")
        previous = self.versions.get(stage.target)
        data = bytes(stage.data) if stage.descriptor is not None else None
        result = (data, {**(previous[1] if previous else {}), **metadata})
        self.versions[stage.target] = result
        self.managed.add(stage.target)
        if previous is None and (not self.sticky or self.default is None):
            self.default = stage.target
        self.generation += 1
        del self.stages[stage_id]
        return result

    def write(self, target, data, **metadata):
        token = self.inspect(target)
        stage = self.begin(target, token[2], describe(data) if data is not None else None)
        for offset in range(0, len(data or b""), 2):
            self.append(stage, offset, data[offset:offset + 2])
        return self.commit(stage, token, metadata)


@pytest.mark.parametrize("binding", ["https", "opcua", "mqtt"])
def test_published_append_has_the_same_observable_behavior(binding):
    filename, heading = DEPLOYMENT_SECTIONS[binding]
    draft = (FEDERATION.parent / "bindings" / filename).read_text(encoding="utf-8")
    draft = draft.split(f"\n{heading}\n", 1)[1].split("\n## ", 1)[0]
    if binding == "mqtt":
        request, response = [
            json.loads(snippet) for snippet in re.findall(r"^```json\n(.*?)\n```$", draft, re.M | re.S)
        ]
        schema = json.loads((FEDERATION / "schemas" / "deployment-request.json").read_text())
        validator = Draft202012Validator(schema)
        validator.check_schema(schema)
        validator.validate(request)
        args = request["arguments"]
        stage, offset = args["stage"], int(args["offset"])
        data = base64.b64decode(args["data"], validate=True)
        expected = response["result"]
        for wrong in ("0\n", "00", "-1"):
            assert not validator.is_valid({**request, "arguments": {**args, "offset": wrong}})
        assert not validator.is_valid({**request, "profile": "mrpc/1.0"})
        assert not validator.is_valid({**request, "arguments": {**args, "target": V1}})
    elif binding == "https":
        exchange = re.search(
            r"POST /deployment/v1/plant/stages/([^/]+)/chunks\?offset=(\d+) HTTP/1.1\n"
            r".*?Content-Length: (\d+)\n\n([^\n]+)\n\nHTTP/1.1 200 OK\n.*?\n\n({[^\n]+})",
            draft, re.S,
        )
        stage, offset = exchange[1], int(exchange[2])
        data, expected = exchange[4].encode(), json.loads(exchange[5])
        assert len(data) == int(exchange[3])
    else:
        call = re.search(
            r'`Append\("([^"]+)", (\d+), ByteString\(([^)]+)\)\)`'
            r"\nreturns operation status `Good` with `({[^`]+})`", draft,
        )
        stage, offset = call[1], int(call[2])
        data = bytes(int(byte, 16) for byte in call[3].split())
        expected = json.loads(call[4])

    assert data == b"ab"
    receiver = ExampleReceiver()
    receiver.write(V1, b"")
    assert receiver.begin(V2, "create", describe(b"abc")) == stage
    assert receiver.append(stage, offset, data) == expected
    with pytest.raises(FederationError, match="2") as duplicate:
        receiver.append(stage, offset, data)
    assert duplicate.value.code == "offset_mismatch"
    assert V2 not in receiver.versions
    receiver.append(stage, 2, b"c")
    assert receiver.commit(stage, receiver.inspect(V2)) == (b"abc", {})


def test_replacement_guard_covers_absence_and_same_xid_recreation():
    receiver = ExampleReceiver()
    token = receiver.inspect(V1)
    create = receiver.begin(V1, "create", describe(b""))
    assert receiver.begin(V1, "create", describe(b"")) == create
    receiver.commit(create, token)
    replacement = receiver.begin(V1, "replace", describe(b""))
    stale = receiver.inspect(V1)
    receiver.versions.clear()
    receiver.managed.clear()
    receiver.generation += 1  # An administrative deletion.
    with pytest.raises(FederationError, match="stale_precondition"):
        receiver.commit(replacement, stale)
    assert receiver.abort(V1, replacement) == {"removed": True}
    create = receiver.begin(V1, "create", describe(b""))
    with pytest.raises(FederationError, match="stale_precondition"):
        receiver.commit(create, token)
    receiver.commit(create, receiver.inspect(V1))
    stage = receiver.begin(V1, "replace", describe(b""))
    with pytest.raises(FederationError, match="stale_precondition"):
        receiver.commit(stage, stale)
    assert receiver.versions[V1] == (b"", {})


def test_concurrent_append_requires_a_new_inspection_without_reuploading():
    receiver = ExampleReceiver()
    receiver.write(V1, b"one", name="first")
    stage = receiver.begin(V2, "create", describe(b"two"))
    receiver.append(stage, 0, b"tw")
    receiver.append(stage, 2, b"o")
    token = receiver.inspect(V2)
    third = "/documents/main/assets/item/versions/v3"
    receiver.write(third, b"three")
    with pytest.raises(FederationError, match="stale_precondition"):
        receiver.commit(stage, token)
    assert set(receiver.versions) == {V1, third}
    assert receiver.commit(stage, receiver.inspect(V2)) == (b"two", {})

    replacement = receiver.begin(V1, "replace", describe(b"hi"))
    receiver.append(replacement, 0, b"hi")
    assert receiver.commit(replacement, receiver.inspect(V1)) == (b"hi", {"name": "first"})
    assert receiver.versions[V2] == (b"two", {})


@pytest.mark.parametrize("committed,expires,removed", [
    (False, False, True), (True, False, False), (False, True, False),
])
def test_lost_create_reply_requires_live_stage_removal_for_safe_absent_retry(committed, expires, removed):
    receiver = ExampleReceiver()
    stage = receiver.begin(V1, "create", describe(b""))
    token = receiver.inspect(V1)
    if committed:
        receiver.commit(stage, token)
    if expires:
        receiver.clock = 5
    assert receiver.abort(V1, stage) == {"removed": removed}
    assert receiver.abort(V1, stage) == {"removed": False}
    with pytest.raises(FederationError, match="stage_unavailable"):
        receiver.commit(stage, token)
    assert (V1 in receiver.versions) == committed


def test_invalid_or_disallowed_deployment_has_no_visible_effect():
    receiver = ExampleReceiver()
    with pytest.raises(FederationError, match="policy_denied"):
        receiver.inspect("/documents/main/assets2/item/versions/v1")
    stage = receiver.begin(V1, "create", describe(b"abc"))
    with pytest.raises(FederationError, match="limit_exceeded"):
        receiver.append(stage, 0, b"abc")
    receiver.append(stage, 0, b"xy")
    receiver.append(stage, 2, b"z")
    with pytest.raises(FederationError, match="integrity_error"):
        receiver.commit(stage, receiver.inspect(V1))
    receiver.grant += 1
    with pytest.raises(FederationError, match="policy_denied"):
        receiver.commit(stage, receiver.inspect(V1))
    assert receiver.versions == {}
    receiver.versions[V1] = (b"local", {})
    with pytest.raises(FederationError, match="policy_denied"):
        receiver.begin(V1, "replace", describe(b""))
    assert receiver.versions[V1] == (b"local", {})


def test_metadata_only_and_empty_documents_are_distinct():
    receiver = ExampleReceiver(hasdocument=False)
    with pytest.raises(FederationError, match="validation_error"):
        receiver.begin(V1, "create", describe(b""))
    assert receiver.write(V1, None, name="first") == (None, {"name": "first"})
    assert receiver.write(V1, None) == (None, {"name": "first"})
    assert ExampleReceiver().write(V1, b"") == (b"", {})


@pytest.mark.parametrize("sticky", [False, True])
def test_append_preserves_core_default_rules_and_does_not_prune(sticky):
    receiver = ExampleReceiver(maxversions=2)
    receiver.write(V1, b"one")
    receiver.sticky = sticky
    receiver.write(V2, b"two")
    assert receiver.default == (V1 if sticky else V2)
    with pytest.raises(FederationError, match="validation_error"):
        receiver.write("/documents/main/assets/item/versions/v3", b"three")
    assert set(receiver.versions) == {V1, V2}


def test_deployment_uses_the_open_publication_after_the_channel_moves():
    samples = FEDERATION.parent / "publication" / "samples"
    bundle = json.loads((samples / "publication-package.json").read_text())
    context = deepcopy(bundle["context"])
    objects = {
        json.dumps(entry["reference"], sort_keys=True): (samples / entry["path"]).read_bytes()
        for entry in bundle["objects"]
    }

    def read(reference):
        return objects[json.dumps(reference, sort_keys=True)]

    channels = Channels()
    first = context["snapshot"]
    channels.create("stable", context["scope"], first, read)
    pinned = deepcopy(channels.records["stable"]["head"])
    snapshot = check_snapshot(pinned, read)
    descriptor = snapshot["documents"][0]["content"]
    data = read(descriptor["reference"])
    receiver = ExampleReceiver()
    assert describe(data)["digest"] == descriptor["digest"]
    assert len(data) == descriptor["size"]
    stage = receiver.begin(V1, "create", describe(data))
    receiver.append(stage, 0, data[:2])

    new_manifest = json.dumps({**snapshot, "parent": first}).encode()
    new_digest = hashlib.sha256(new_manifest).hexdigest()
    second = deepcopy(first)
    second["reference"]["version"] = f"/publications/team/snapshots/{new_digest}/versions/manifest"
    second.update(digest="sha256:" + new_digest, size=len(new_manifest))
    objects[json.dumps(second["reference"], sort_keys=True)] = new_manifest
    channels.move("stable", 1, second, read)

    for offset in range(2, len(data), 2):
        receiver.append(stage, offset, data[offset:offset + 2])
    assert receiver.commit(stage, receiver.inspect(V1))[0] == data
    assert channels.records["stable"]["head"] == second
    assert check_snapshot(pinned, read) == snapshot


def test_deployment_capability_is_independent_of_resolution_owner():
    schema = json.loads((FEDERATION / "schemas" / "capabilities.json").read_text())
    validator = Draft202012Validator(schema)
    draft = (FEDERATION / "spec.md").read_text(encoding="utf-8")
    example = next(
        json.loads(snippet) for snippet in re.findall(r"^```json\n(.*?)\n```$", draft, re.M | re.S)
        if '"federationdeployment"' in snippet
    )
    validator.validate(example)
    validator.validate({**example, "federation": {"resolution": "producer"}})
    validator.validate({"federation": {"resolution": "consumer"}})
    assert not validator.is_valid({
        **example, "federationdeployment": {"profiles": ["https-deploy/1", "https-deploy/1"]},
    })
