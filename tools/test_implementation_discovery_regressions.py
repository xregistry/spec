"""Regressions identified while implementing the core HTTP discovery client."""

import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def test_http_discovery_uses_the_core_array_shape():
    http = (ROOT / "core" / "http.md").read_text(encoding="utf-8")
    section = http.split("## xRegistry Discovery\n", 1)[1].split(
        "## Request Flags / Query Parameters", 1
    )[0]
    example = re.search(r'\{\n\s+"registries":.*?\n\}', section, re.DOTALL)
    assert example is not None
    concrete = example.group().replace('"URL", *', '"https://example.test/registry"')
    assert json.loads(concrete) == {
        "registries": ["https://example.test/registry"]
    }
