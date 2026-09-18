#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
validate-models.py - Staged structural validation for xRegistry model.json files

Validates all xRegistry model.json files in the repository against the canonical
core/model.schema.json and reports which stage each result belongs to:

- "source structure": the model.json document exactly as written, including any
  unresolved `$include`/`$includes` directives and any partial overlay of a
  specification-defined attribute.
- "expanded structure": the same document after the include directives have been
  resolved by the generator's real resolver, validated against
  `#/definitions/ExpandedModel`, where every attribute definition must carry a
  type and no directive may remain.

Neither stage overlays the specification-defined attributes onto the model and
neither performs semantic conformance checking (Core aspect compatibility,
key/name identity, target existence and depth, cross-entity graph rules). Those
require a real xRegistry implementation and are reported as not verified.

Usage:
  python validate-models.py
"""
import importlib.util
import sys
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, List

import jsonschema
from jsonschema.validators import validator_for
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "core" / "model.schema.json"
GENERATOR_PATH = Path(__file__).resolve().parent / "schema-generator.py"
EXPANDED_POINTER = "#/definitions/ExpandedModel"

SOURCE_STAGE = "source structure"
EXPANDED_STAGE = "expanded structure"
SEMANTIC_STAGE = "semantic conformance"
SEMANTIC_NOTE = (
    f"{SEMANTIC_STAGE}: not performed here; specification-defined attribute "
    "overlay, key/name identity, target existence and depth, and cross-entity "
    "graph rules require a real xRegistry implementation"
)


@dataclass
class StageReport:
    """Which structural stages actually ran, and what they found."""

    stages: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    unverified: List[str] = field(default_factory=lambda: [SEMANTIC_NOTE])


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _generator():
    spec = importlib.util.spec_from_file_location("schema_generator", GENERATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _validator_class(schema: dict) -> Any:
    # The canonical schema declares draft-07; pin that dialect rather than
    # silently falling back to whatever the newest supported draft happens to be.
    validator_cls = validator_for(schema, default=jsonschema.Draft7Validator)
    validator_cls.check_schema(schema)
    return validator_cls


def source_validator(schema: dict) -> Any:
    """Validator for the document exactly as it was written."""
    return _validator_class(schema)(schema)


def expanded_validator(schema: dict) -> Any:
    """Validator for the document after include resolution."""
    uri = schema.get("$id") or "urn:xregistry:core-model-schema"
    registry = Registry().with_resource(
        uri, Resource(contents=schema, specification=DRAFT7)
    )
    return _validator_class(schema)(
        {"$ref": f"{uri}{EXPANDED_POINTER}"}, registry=registry
    )


def expand_model(model_path: Path, instance: dict) -> dict:
    """Resolve includes with the generator's real resolver, without mutating."""
    return _generator().resolve_imports(str(Path(model_path).parent), instance)


def _messages(stage: str, model_path: Path, validator: Any, instance: dict) -> List[str]:
    label = Path(model_path).relative_to(REPO_ROOT) if Path(
        model_path
    ).is_relative_to(REPO_ROOT) else Path(model_path).name
    return [
        f"[{stage}] {label}: {error.message} (at {list(error.path)})"
        for error in sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
    ]


def validate_model(model_path: Path, schema: dict) -> StageReport:
    """Run both structural stages and report which ones actually ran."""
    report = StageReport()
    label = Path(model_path).name
    try:
        instance = load_json(Path(model_path))
    except Exception as exc:  # noqa: BLE001 - reported, not raised, per file
        report.errors.append(f"[{SOURCE_STAGE}] {label}: cannot be read: {exc}")
        return report

    report.stages.append(SOURCE_STAGE)
    report.errors.extend(
        _messages(SOURCE_STAGE, model_path, source_validator(schema), instance)
    )
    if report.errors:
        return report

    try:
        expanded = expand_model(Path(model_path), instance)
    except Exception as exc:  # noqa: BLE001 - include failures belong to this stage
        report.stages.append(EXPANDED_STAGE)
        report.errors.append(
            f"[{EXPANDED_STAGE}] {label}: include resolution failed: {exc}"
        )
        return report

    report.stages.append(EXPANDED_STAGE)
    report.errors.extend(
        _messages(EXPANDED_STAGE, model_path, expanded_validator(schema), expanded)
    )
    return report


def find_model_json_files(root: Path) -> Iterator[Path]:
    """Recursively yield all model.json files under the given root directory."""
    yield from root.rglob("model.json")


def main() -> int:
    schema = load_json(SCHEMA_PATH)
    all_errors = []
    model_files = sorted(find_model_json_files(REPO_ROOT))
    if not model_files:
        print("No model.json files found.")
        return 0
    for model_path in model_files:
        if not model_path.exists():
            print(f"SKIP: {model_path.relative_to(REPO_ROOT)} (file not found)")
            continue
        report = validate_model(model_path, schema)
        stages = ", ".join(report.stages)
        if report.errors:
            print(f"FAIL: {model_path.relative_to(REPO_ROOT)} [{stages}]")
            for err in report.errors:
                print(f"  {err}")
            all_errors.extend(report.errors)
        else:
            print(f"PASS: {model_path.relative_to(REPO_ROOT)} [{stages}]")
    print(f"\nNot checked by this tool: {SEMANTIC_NOTE}")
    if all_errors:
        print(f"\n{len(all_errors)} validation error(s) found.")
        return 1
    print("\nAll model.json files are structurally valid at both stages.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
