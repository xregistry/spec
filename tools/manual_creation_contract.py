"""Pure manual-ancestry creation plans, not a server transaction engine.

timestamp_key is supplied by the caller using the specification's timestamp
comparison. No timestamp is parsed, clipped or changed here. Existing versions
are the staged state at the automatic-creation step.
"""

from copy import deepcopy


def manual_newest(versions, *, timestamp_key):
    if not versions:
        return None
    referenced = {
        value["ancestorid"]
        for name, value in versions.items()
        if value["ancestorid"] != name
    }
    terminals = set(versions) - referenced
    if not terminals:
        raise ValueError("ancestor_circular_reference: no terminal Version")
    return max(terminals, key=lambda name: (timestamp_key(versions[name]["createdat"]), name.lower()))


def plan_manual_creation(versions, name, attributes, *, timestamp_key):
    if name.lower() in {existing.lower() for existing in versions}:
        raise ValueError("Version ID already exists ignoring case")
    result = deepcopy(versions)
    created = deepcopy(attributes)
    automatic = "ancestorid" not in created
    if automatic:
        created["ancestorid"] = manual_newest(result, timestamp_key=timestamp_key) or name
    elif created["ancestorid"] != name and created["ancestorid"] not in result:
        raise ValueError("unknown_id")
    result[name] = created
    if automatic and manual_newest(result, timestamp_key=timestamp_key) != name:
        raise ValueError("bad_request: automatically linked Version would not become newest")
    return result


def plan_automatic_creations(versions, creations, *, timestamp_key):
    """Plan only the already-defined ordered automatic-creation pass atomically."""
    if len({name.lower() for name in creations}) != len(creations):
        raise ValueError("New Version IDs are not unique ignoring case")
    if any("ancestorid" in attributes for attributes in creations.values()):
        raise ValueError("This pass accepts only automatically linked creations")
    result = deepcopy(versions)
    for name in sorted(creations, key=str.lower):
        result = plan_manual_creation(
            result, name, creations[name], timestamp_key=timestamp_key
        )
    return result
