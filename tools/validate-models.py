#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
validate-models.py - Strict JSON Schema validation for xRegistry model.json files

Validates all xRegistry model.json files in the repository against the canonical core/model.schema.json.
Outputs pass/fail results for each file. Exits nonzero if any file fails validation.

Best practices:
- Uses Python 3.12+ typing and style conventions
- Uses jsonschema for validation
- Lints itself with ruff, black, isort, pylint
- Designed for CI integration

Usage:
  python validate-models.py
"""
import sys
import json
from pathlib import Path
from typing import List, Iterator

import jsonschema
from jsonschema.validators import validator_for

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "core" / "model.schema.json"

def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def validate_model(model_path: Path, schema: dict) -> List[str]:
    errors = []
    try:
        instance = load_json(model_path)
        validator_cls = validator_for(schema)
        validator_cls.check_schema(schema)
        validator = validator_cls(schema)
        for error in sorted(validator.iter_errors(instance), key=lambda e: e.path):
            errors.append(f"{model_path.relative_to(REPO_ROOT)}: {error.message} (at {list(error.path)})")
    except Exception as exc:
        errors.append(f"{model_path.relative_to(REPO_ROOT)}: Exception during validation: {exc}")
    return errors

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
        errors = validate_model(model_path, schema)
        if errors:
            print(f"FAIL: {model_path.relative_to(REPO_ROOT)}")
            for err in errors:
                print(f"  {err}")
            all_errors.extend(errors)
        else:
            print(f"PASS: {model_path.relative_to(REPO_ROOT)}")
    if all_errors:
        print(f"\n{len(all_errors)} validation error(s) found.")
        return 1
    print("\nAll model.json files are valid.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
