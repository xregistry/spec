"""Check the default Message model's retained Version limit."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_default_message_model_limits_resources_to_one_version():
    model = json.loads((ROOT / "message" / "model.json").read_text(encoding="utf-8"))
    limit = model["groups"]["messagegroups"]["resources"]["messages"]["maxversions"]
    assert limit == 1
