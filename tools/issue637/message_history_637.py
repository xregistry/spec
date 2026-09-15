"""Offline snapshot/reference example for customized Message histories."""

from copy import deepcopy
from dataclasses import dataclass
from typing import Literal


def check_retained_history(resource, maxversions):
    if type(maxversions) is not int or maxversions < 0:
        raise ValueError("maxversions must be an unsigned integer")
    versions = resource["versions"]
    if not versions:
        raise ValueError("owned Message needs a retained Version")
    if maxversions and len(versions) > maxversions:
        raise ValueError("snapshot exceeds the retained Version limit")
    if resource["meta"]["defaultversionid"] not in versions:
        raise ValueError("default Version is not retained")
    for key, version in versions.items():
        if key != version["versionid"]:
            raise ValueError("Version map key and identity disagree")


def select_version(resource, reference):
    xid = resource["xid"]
    if reference == xid:
        version_id = resource["meta"]["defaultversionid"]
    elif reference.startswith(xid + "/versions/"):
        version_id = reference[len(xid + "/versions/"):]
        if not version_id or "/" in version_id:
            raise ValueError("invalid precise Version reference")
    else:
        raise ValueError("reference does not identify this Message")
    selected = resource["versions"].get(version_id)
    return deepcopy(selected) if selected is not None else None


@dataclass(frozen=True)
class MatchResult:
    status: Literal["unmatched", "unique", "ambiguous"]
    version_ids: tuple[str, ...]


def match_versions(resource, event_type, payload_media=None):
    matches = tuple(
        key for key, version in resource["versions"].items()
        if version["envelopemetadata"]["type"]["value"] == event_type
        and (payload_media is None or version["datacontenttype"] == payload_media)
    )
    status = "unmatched" if not matches else "unique" if len(matches) == 1 else "ambiguous"
    return MatchResult(status, matches)
