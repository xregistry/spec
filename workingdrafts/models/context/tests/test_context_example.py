"""Context model, sample and specification examples agree."""

import base64
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit

import avro.schema
import jsonschema
import pytest
from openapi_spec_validator import validate_spec

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]
MODEL = json.loads((ROOT / "model.json").read_text(encoding="utf-8"))
SCHEMA = json.loads((ROOT / "schemas" / "document-schema.json").read_text(encoding="utf-8"))
SAMPLE = json.loads((ROOT / "samples" / "context.json").read_text(encoding="utf-8"))
SPEC = (ROOT / "spec.md").read_text(encoding="utf-8")
ROLE = re.compile(r"^[a-z0-9][a-z0-9:_.-]{0,62}$")


def sample_versions():
    for group in SAMPLE["contextgroups"].values():
        for context in group["contexts"].values():
            for version in context["versions"].values():
                yield version


def sample_references(contextid):
    for version in sample_versions():
        if version["contextid"] == contextid:
            return version["references"]
    raise AssertionError(contextid)


def spec_example(*present, absent=None):
    blocks = re.findall(r"^```json\n(.*?)^```", SPEC, re.MULTILINE | re.DOTALL)
    found = [
        json.loads(block)
        for block in blocks
        if all(f'"{key}"' in block for key in present)
        and (absent is None or f'"{absent}"' not in block)
    ]
    assert len(found) == 1, present
    return found[0]


def assert_references(references):
    assert references
    for role, reference in references.items():
        assert ROLE.fullmatch(role), role
        url = reference["url"]
        parts = urlsplit(url)
        assert parts.scheme and parts.netloc and "#" not in url, url


def test_model_sample_and_spec_examples_agree():
    core = json.loads((REPO / "core" / "model.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(core).validate(MODEL)
    jsonschema.Draft7Validator(SCHEMA).validate(SAMPLE)

    self_urls = set()
    for version in sample_versions():
        assert_references(version["references"])
        self_urls.add(
            "https://registry.example/contextgroups/line1/contexts/"
            f"{version['contextid']}/versions/{version['versionid']}"
        )

    event = spec_example("contexturl", "specversion")
    assert event["contexturl"] in self_urls

    metadata = spec_example("references", absent="documents")
    assert metadata["self"] == event["contexturl"]
    assert metadata["references"] == sample_references(metadata["contextid"])

    view = spec_example("documents")
    context = view["context"]
    assert context["self"] in self_urls
    assert context["references"] == sample_references(context["contextid"])
    assert view["documents"].keys() == context["references"].keys()
    for role, document in view["documents"].items():
        assert document["url"] == context["references"][role]["url"]
        assert document["contenttype"]
        assert ("content" in document) != ("contentbase64" in document), role
        if "contentbase64" in document:
            base64.b64decode(document["contentbase64"], validate=True)


@pytest.mark.parametrize("filename", ["document-schema.json", "openapi.json"])
@pytest.mark.parametrize("url,valid", [
    ("https://registry.example/schema/1", True),
    ("https://registry.example/schema/a%23b?version=1", True),
    ("https://registry.example/schema/1#definition", False),
    ("https://registry.example/schema/1#", False),
    ("/schema/1", False),
])
def test_reference_url_validation(filename, url, valid):
    schema = json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8"))
    if filename == "openapi.json":
        version = schema["components"]["schemas"]["contextVersion"]
    else:
        version = schema["definitions"]["contextgroup-schema"]["contextVersion"]
    reference = version["properties"]["references"]["additionalProperties"]
    # The pattern must enforce urlabsolute without an optional format checker.
    assert jsonschema.Draft7Validator(reference).is_valid({"url": url}) is valid


@pytest.mark.parametrize("schema_type,filename", [
    ("json-schema", "document-schema.json"),
    ("json-structure", "document-schema.struct.json"),
    ("avro-schema", "document-schema.avsc"),
    ("openapi", "openapi.json"),
])
def test_generated_schemas_match_model(tmp_path, schema_type, filename):
    checked = json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8"))
    extra_args = []
    if schema_type in ("json-schema", "json-structure"):
        extra_args.extend(["--schema-id", checked["$id"]])
    if schema_type == "json-structure":
        extra_args.extend(["--schema-name", checked["name"]])

    output = tmp_path / filename
    result = subprocess.run(
        [
            sys.executable, str(REPO / "tools" / "schema-generator.py"),
            "--type", schema_type, "--output", str(output),
            *extra_args, str(ROOT / "model.json"),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    generated = json.loads(output.read_text(encoding="utf-8"))
    assert generated == checked
    if schema_type == "json-schema":
        jsonschema.Draft7Validator.check_schema(generated)
    elif schema_type == "avro-schema":
        avro.schema.parse(json.dumps(generated))
    elif schema_type == "openapi":
        validate_spec(generated)
