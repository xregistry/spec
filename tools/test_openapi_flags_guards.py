"""Check effective flag/guard carriers without claiming server concurrency tests."""

import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
WRITE_METHODS = {"put", "patch", "post", "delete"}
METHODS = WRITE_METHODS | {"get"}
MODELS = {
    "schema": ("schema",),
    "message": ("message",),
    "endpoint": ("endpoint",),
    "cloudevents": ("endpoint", "message", "schema"),
}


def _generate(inputs, output):
    result = subprocess.run(
        [
            sys.executable, str(ROOT / "tools" / "schema-generator.py"),
            "--type", "openapi", "--output", str(output), *map(str, inputs),
        ],
        cwd=ROOT, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(output.read_text(encoding="utf-8"))


@pytest.fixture(scope="module", params=MODELS)
def document(request, tmp_path_factory):
    name = request.param
    output = tmp_path_factory.mktemp(f"flags-{name}") / "openapi.json"
    generated = _generate([ROOT / model / "model.json" for model in MODELS[name]], output)
    published = json.loads((ROOT / name / "schemas" / "openapi.json").read_text(encoding="utf-8"))
    assert generated == published
    return generated


def _operations(document):
    for path, item in document["paths"].items():
        for method in set(item) & METHODS:
            yield path, item, method, item[method]


def _parameters(document, item, operation):
    parameters = [*item.get("parameters", []), *operation.get("parameters", [])]
    return [
        document["components"]["parameters"][value["$ref"].rsplit("/", 1)[1]]
        if "$ref" in value else value
        for value in parameters
    ]


def test_obsolete_ignore_and_attribute_query_parameters_are_removed(document):
    obsolete = {"noepoch", "nodefaultversionid", "nodefaultversionsticky", "noreadonly",
                "resource-description", "resource-documentation", "resource-labels"}
    for path, item, method, operation in _operations(document):
        names = {p["name"] for p in _parameters(document, item, operation) if p["in"] == "query"}
        assert not names & obsolete, (path, method, names & obsolete)
    assert not obsolete & set(document["components"]["parameters"])


def test_ignore_is_offered_once_on_writes_and_not_on_reads(document):
    for path, item, method, operation in _operations(document):
        ignores = [p for p in _parameters(document, item, operation)
                   if p["in"] == "query" and p["name"] == "ignore"]
        assert len(ignores) == (1 if method in WRITE_METHODS else 0), (path, method)
    parameter = document["components"]["parameters"]["ignore"]
    assert parameter["style"] == "form" and parameter["explode"] is True
    assert parameter["allowEmptyValue"] is True
    validator = jsonschema.Draft7Validator(parameter["schema"])
    validator.validate(["epoch", "readonly", "vendor-rule"])
    validator.validate(["*"])
    validator.validate([""])
    assert "comma-separated" in parameter["description"]
    assert "repeated" in parameter["description"]


def test_epoch_query_guards_exist_only_on_optional_single_entity_deletes(document):
    count = 0
    for path, item, method, operation in _operations(document):
        epochs = [p for p in _parameters(document, item, operation)
                  if p["in"] == "query" and p["name"] == "epoch"]
        if method != "delete":
            assert epochs == [], (path, method)
            continue
        count += 1
        assert len(epochs) == 1
        assert epochs[0]["required"] is False
        assert epochs[0]["schema"]["minimum"] == 0
        role = "version" if "/versions/" in path else "meta" if "{resourceid}" in path else "group"
        assert role in epochs[0]["description"].lower()
        assert "equal" in epochs[0]["description"].lower()
        assert "optional" in operation["description"].lower()
    assert count > 0


def test_doc_uses_bare_presence_serialization_not_true_or_false(document):
    parameter = document["components"]["parameters"]["doc"]
    assert parameter["allowEmptyValue"] is True
    assert parameter["schema"] == {"type": "string", "enum": [""]}
    assert "bare ?doc" in parameter["description"]
    assert "?doc=true" in parameter["description"] and "?doc=false" in parameter["description"]
    validator = jsonschema.Draft7Validator(parameter["schema"])
    validator.validate("")
    for invalid in ("true", "false", True, False):
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(invalid)


def test_epoch_header_preserves_unsigned_values_and_literal_null_reset(document):
    parameter = document["components"]["parameters"].get("version-epoch")
    assert parameter is not None, "Document-view epoch carrier is missing"
    assert parameter["in"] == "header" and parameter["name"] == "xRegistry-epoch"
    assert parameter["required"] is False
    validator = jsonschema.Draft7Validator(parameter["schema"])
    for value in (0, 5, 6, 2 ** 80, "null"):
        validator.validate(value)
    for invalid in (-1, 1.5, True, "NULL", ""):
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(invalid)
    description = parameter["description"].lower()
    assert "default version, not the resource meta" in description
    assert "absent" in description and "null" in description and "create" in description
    assert "metadata" in description and "json" in description


def test_conflict_means_inequality_and_retains_absent_null_and_create_rules(document):
    description = document["components"]["responses"]["Conflict"]["description"].lower()
    assert "non-null" in description and "not equal" in description
    assert "not greater" not in description
    source = (ROOT / "core" / "spec.md").read_text(encoding="utf-8")
    epoch = " ".join(source.split("##### `epoch` Attribute\n", 1)[1].split("\n##### ", 1)[0].split())
    assert "a non-null value that differs from the existing value" in epoch
    assert "A value of `null` MUST be treated the same as a request with no `epoch` attribute at all" in epoch
    assert "During a create operation, if this attribute is present in the request, then it MUST be silently ignored" in epoch


def test_document_header_guard_respects_metadata_only_and_imported_resource_types(tmp_path):
    model = {
        "groups": {
            "sources": {
                "singular": "source",
                "resources": {
                    "files": {"singular": "file", "hasdocument": True},
                    "entries": {"singular": "entry", "hasdocument": False},
                },
            },
            "mirrors": {
                "singular": "mirror",
                "ximportresources": ["/sources/files", "/sources/entries"],
            },
        }
    }
    model_path = tmp_path / "model.json"
    model_path.write_text(json.dumps(model), encoding="utf-8")
    document = _generate([model_path], tmp_path / "openapi.json")
    for group in ("sources", "mirrors"):
        for resource, hasdocument in (("files", True), ("entries", False)):
            path = f"/{group}/{{groupid}}/{resource}/{{resourceid}}"
            item = document["paths"][path]
            for method in ("put", "post"):
                headers = [p["name"] for p in _parameters(document, item, item[method])
                           if p["in"] == "header"]
                assert ("xRegistry-epoch" in headers) is hasdocument
                assert "xRegistry-meta.epoch" not in headers
            for suffix in ("/meta", "$details"):
                metadata_item = document["paths"][path + suffix]
                for method in set(metadata_item) & METHODS:
                    assert all(
                        p["name"] != "xRegistry-epoch"
                        for p in _parameters(document, metadata_item, metadata_item[method])
                    )


def test_primer_uses_details_and_metadata_only_resource_rules():
    primer = (ROOT / "core" / "primer.md").read_text(encoding="utf-8")
    section = " ".join(primer.split("### 11.3. Extensions\n", 1)[1].split("\n### ", 1)[0].split())
    assert "GET resource?meta" not in section
    assert "hasdocument=false" in section and "$details" in section
    assert "response URLs MUST NOT include that suffix" in section
