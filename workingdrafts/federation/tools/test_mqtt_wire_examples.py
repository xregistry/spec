"""Offline checks for the MQTT draft's URI and User Property rules."""

from pathlib import Path
import re
from urllib.parse import quote, unquote, urlsplit

import pytest

from workingdrafts.federation.tools.federation_examples import validate_xid


DRAFT = (Path(__file__).resolve().parents[2] / "bindings" / "mqtt.md").read_text(
    encoding="utf-8"
)
BASE = "site/100% ready"
BROKER = "mqtts://broker.example.com"


def navigation_request(uri, bases):
    """Translate a navigation example in a known broker and view context."""
    if any(ord(char) <= 32 for char in uri) or "#" in uri:
        raise ValueError("Invalid navigation URI")
    parsed = urlsplit(uri)
    if parsed.scheme != "mqtts" or parsed.netloc != "broker.example.com":
        raise ValueError("Unauthorized broker")
    raw = parsed.path
    levels = [unquote(level, errors="strict") for level in raw[1:].split("/")]
    if not raw.startswith("/") or any("/" in level or level in (".", "..") for level in levels):
        raise ValueError("Invalid topic level")
    if raw != "/" + "/".join(quote(level, safe="") for level in levels):
        normalized = re.sub(r"%[0-9a-fA-F]{2}", lambda m: m[0].upper(), raw)
        if normalized != "/" + "/".join(quote(level, safe="") for level in levels):
            raise ValueError("Noncanonical topic path")
    topic = "/".join(levels)
    if any(char in topic for char in "\x00+#") or len(topic.encode("utf-8")) > 65535:
        raise ValueError("Invalid MQTT topic")
    matches = [
        topic[len(base + "/read"):]
        for base in bases if topic.startswith(base + "/read/")
    ]
    if len(matches) != 1:
        raise ValueError("Unauthorized read route")
    target = matches[0]
    parts = target.split("/")[1:]
    if target != "/":
        validate_xid(target, collection=len(parts) in (1, 3) or parts[-1] == "versions" and len(parts) == 5)
    if "?" not in uri:
        return topic, {}
    if parsed.query == "view=document" and len(parts) in (4, 6):
        return topic, {"view": "document"}
    if target == "/" and parsed.query in {
        "surface=capabilities", "surface=capabilitiesoffered", "surface=model",
        "surface=modelsource", "surface=export", "surface=discovery",
    }:
        return topic, {"surface": parsed.query.removeprefix("surface=")}
    raise ValueError("Invalid read qualifier")


def test_direct_navigation_keeps_root_slash_exact_xid_and_escaped_base():
    uri_base = BROKER + "/site/100%25%20ready/read"
    target = "/documents/Main/assets/item/versions/V2"
    assert navigation_request(uri_base + target + "?view=document", [BASE]) == (
        BASE + "/read" + target, {"view": "document"},
    )
    assert navigation_request(uri_base + "/?surface=model", [BASE]) == (
        BASE + "/read/", {"surface": "model"},
    )


@pytest.mark.parametrize("route", [
    "site/100%25%20ready/delete/documents/Main",
    "site/100%25%20ready/read/../documents",
    "site/100%25%20ready/read/%2E%2E/documents",
    "site/100%25%20ready/read/documents%2FMain",
    "site/100%25%20ready/read/documents?surface=model",
    "site/100%25%20ready/read/?surface=model&surface=model",
    "site/100%25%20ready/read/#",
])
def test_navigation_rejects_nonread_or_ambiguous_path_and_query(route):
    with pytest.raises(ValueError):
        navigation_request(BROKER + "/" + route, [BASE])


def envelope_properties(pairs, *, reply=False):
    """Normalize the aliases listed in the draft before checking direction."""
    aliases = dict(re.findall(r"^\| `(mrpc-[^`]+)` \| `(__[^`]+)` \|", DRAFT, re.M))
    names = {alias: name for name, alias in aliases.items()}
    seen = set()
    logical = {}
    for spelling, value in pairs:
        name = names.get(spelling, spelling)
        if name not in aliases:
            continue
        if spelling in seen:
            raise ValueError("Repeated spelling")
        seen.add(spelling)
        if name == "mrpc-version":
            expected = "1.0" if spelling == "__protVer" else "mrpc/1.0"
            if value != expected:
                raise ValueError("Invalid version")
            value = "mrpc/1.0"
        if name in logical and value != logical[name]:
            raise ValueError("Conflicting aliases")
        logical[name] = value
    if "mrpc-version" not in logical:
        raise ValueError("Missing version")
    if not reply:
        if len(logical) != 1:
            raise ValueError("Unexpected request property")
        return logical
    status = logical.get("mrpc-status")
    error_status = {"400", "408", "415", "500", "503", "505"}
    if status not in error_status | {"200", "204"}:
        raise ValueError("Invalid reply status")
    if status not in error_status and logical.keys() - {"mrpc-version", "mrpc-status"}:
        raise ValueError("Unexpected diagnostic")
    if "mrpc-application-error" in logical and (
        status != "500" or logical["mrpc-application-error"] not in {"true", "false"}
    ):
        raise ValueError("Invalid application error")
    return logical


def test_alias_reply_matches_canonical_reply():
    version = ["mrpc-version", "mrpc/1.0"]
    status = ["mrpc-status", "200"]
    alias_reply = [["__protVer", "1.0"], status, ["__stat", "200"]]
    assert envelope_properties(alias_reply, reply=True) == envelope_properties([version, status], reply=True)
    assert envelope_properties([version, ["__protVer", "1.0"]]) == envelope_properties([version])
    assert envelope_properties([["__protVer", "1.0"], ["__stat", "500"], ["__apErr", "true"]], reply=True) == {
        "mrpc-version": "mrpc/1.0", "mrpc-status": "500", "mrpc-application-error": "true",
    }


@pytest.mark.parametrize(("extra", "reply"), [
    ([["__protVer", "mrpc/1.0"]], False),
    ([["mrpc-version", "mrpc/1.0"]], False),
    ([["__stat", "200"]], False),
    ([["mrpc-status", "200"], ["__stat", "500"]], True),
    ([["__stat", "200"], ["__apErr", "false"]], True),
    ([["__stat", "204"], ["__stMsg", "diagnostic"]], True),
])
def test_aliases_do_not_weaken_existing_envelope_constraints(extra, reply):
    with pytest.raises(ValueError):
        envelope_properties([["mrpc-version", "mrpc/1.0"], *extra], reply=reply)
