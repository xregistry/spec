"""The OpenUSD draft defines one shared usdasset type, not equivalent copies."""

import json
from pathlib import Path


def test_plugin_group_imports_the_declared_common_usdasset_resource():
    root = Path(__file__).resolve().parents[1]
    model = json.loads((root / "model.json").read_text(encoding="utf-8"))
    asset = model["groups"]["usdassetgroups"]["resources"]["usdassets"]
    plugin = model["groups"]["usdschemaplugingroups"]
    assert plugin["ximportresources"] == ["/usdassetgroups/usdassets"]
    assert not plugin.get("resources"), "A duplicate definition does not preserve Core Resource type identity"
    assert asset["attributes"]["assetidentifier"]["required"] is True
    assert {"SchemaPlugin", "GeneratedSchema"} <= set(asset["attributes"]["assetkind"]["enum"])
