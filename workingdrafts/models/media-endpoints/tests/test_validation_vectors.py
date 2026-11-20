"""Executable conformance vectors for the Media Endpoints validation rules."""

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "model.json"
VECTORS_PATH = ROOT / "tests" / "validation-vectors.json"
CODEC_FIELDS = {"videocodec": "video", "audiocodec": "audio"}


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def media_protocols(model):
    protocols = model["groups"]["endpoints"]["attributes"]["protocol"]["ifvalues"]
    return {name: value for name, value in protocols.items() if name != "$include"}


def protocol_options(protocol):
    return protocol["siblingattributes"]["protocoloptions"].get("attributes", {})


def default_codec_kinds(protocols):
    defaults = {}
    pattern = re.compile(r"\bdefaults to ([A-Za-z0-9._+-]+)")
    for protocol in protocols.values():
        for field, kind in CODEC_FIELDS.items():
            description = protocol_options(protocol).get(field, {}).get("description", "")
            match = pattern.search(description)
            if match:
                defaults[match.group(1)] = kind
    return defaults


def test_codec_vectors_cover_open_case_sensitive_identifiers_and_media_kind():
    model = load_json(MODEL_PATH)
    vectors = load_json(VECTORS_PATH)["codecs"]
    known_kinds = default_codec_kinds(media_protocols(model))

    assert known_kinds["H264"] == "video"
    assert known_kinds["AAC"] == "audio"
    assert {vector["id"] for vector in vectors} == {
        "default-video-codec",
        "default-audio-codec",
        "known-audio-codec-in-video-field",
        "known-video-codec-in-audio-field",
        "codec-identifier-case-is-not-normalized",
        "unknown-codec-identifier",
    }

    for vector in vectors:
        field_kind = CODEC_FIELDS[vector["field"]]
        codec_kind = known_kinds.get(vector["value"])
        result = "reject" if codec_kind and codec_kind != field_kind else "accept"
        assert result == vector["result"], vector["id"]


def test_streamformat_vectors_match_every_protocol_model_declaration():
    model = load_json(MODEL_PATH)
    protocols = media_protocols(model)
    vectors = load_json(VECTORS_PATH)["streamformats"]

    assert set(vectors) == set(protocols)
    for name, protocol in protocols.items():
        vector = vectors[name]
        declaration = protocol_options(protocol).get("streamformat", {}).get("enum")
        assert vector["declared"] == declaration, name
        if declaration is None:
            assert vector["accepted"]
            assert vector["rejected"] == []
            assert all(isinstance(value, str) for value in vector["accepted"]), name
            continue

        assert vector["accepted"] == declaration, name
        assert vector["rejected"], name
        assert all(value in declaration for value in vector["accepted"]), name
        assert all(value not in declaration for value in vector["rejected"]), name
