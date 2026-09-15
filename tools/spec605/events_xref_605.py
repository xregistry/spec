"""Bounded lifecycle planning from local state and already available projections."""

from dataclasses import dataclass, field
from typing import Mapping, Optional


def _epoch(value):
    if type(value) is not int or value < 0:
        raise ValueError("an available epoch must be an unsigned integer")
    return value


@dataclass(frozen=True)
class LocalResource:
    versions: Mapping[str, int] = field(default_factory=dict)
    default: Optional[str] = None
    meta_epoch: Optional[int] = None
    xref: Optional[str] = None

    def __post_init__(self):
        if self.xref is not None:
            if self.versions or self.default is not None:
                raise ValueError("an alias cannot own Versions")
        else:
            if self.default not in self.versions:
                raise ValueError("a normal Resource needs an owned default Version")
            _epoch(self.meta_epoch)
        for value in self.versions.values():
            _epoch(value)


def _resource_signature(resource):
    if resource is None:
        return None
    return (
        resource.xref,
        resource.meta_epoch,
        resource.default,
        frozenset(resource.versions),
        resource.versions.get(resource.default),
    )


def _event_data(resource, target_views):
    if resource.xref is None:
        return {
            "epoch": resource.versions[resource.default],
            "meta.epoch": resource.meta_epoch,
        }

    # These are supplied read captures, not a resolver or an instruction to fetch.
    target = target_views.get(resource.xref)
    if target is None:
        return {}
    meta = target.get("meta", {})
    if "xref" in meta:
        return {}
    result = {}
    if "epoch" in target:
        result["epoch"] = _epoch(target["epoch"])
    if "epoch" in meta:
        result["meta.epoch"] = _epoch(meta["epoch"])
    return result


def plan_lifecycles(before, after, target_views=None):
    """Plan Resource/Version events, never treating projected Versions as owned."""
    if target_views is None:
        target_views = {}
    events = []
    for subject in sorted(before.keys() | after.keys()):
        old, new = before.get(subject), after.get(subject)
        if _resource_signature(old) != _resource_signature(new):
            action = "created" if old is None else "deleted" if new is None else "updated"
            event = {"type": f"io.xregistry.resource.{action}", "subject": subject}
            if new is not None:
                event["data"] = _event_data(new, target_views)
            events.append(event)

        old_versions = {} if old is None else old.versions
        new_versions = {} if new is None else new.versions
        for version in sorted(old_versions.keys() | new_versions.keys()):
            if version not in old_versions:
                action = "created"
            elif version not in new_versions:
                action = "deleted"
            elif old_versions[version] != new_versions[version]:
                action = "updated"
            else:
                continue
            event = {
                "type": f"io.xregistry.version.{action}",
                "subject": f"{subject}/versions/{version}",
            }
            if action != "deleted":
                event["data"] = {"epoch": new_versions[version]}
            events.append(event)
    return events
