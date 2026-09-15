"""Finite sticky-manual deletion plans; not a server or retention-policy engine.

timestamp_key and can_delete provide the existing comparison and independently
applicable deletion restrictions. The input graph is never changed.
"""


def _forest(versions):
    if len({name.lower() for name in versions}) != len(versions):
        raise ValueError("Version IDs are not unique ignoring case")
    children = {name: [] for name in versions}
    roots = set()
    for name, value in versions.items():
        parent = value["ancestorid"]
        if parent not in versions:
            raise ValueError("unknown_id")
        if parent == name:
            roots.add(name)
        else:
            children[parent].append(name)
    seen = set()
    pending = list(roots)
    while pending:
        name = pending.pop()
        if name in seen:
            raise ValueError("ancestor_circular_reference")
        seen.add(name)
        pending.extend(children[name])
    if seen != set(versions):
        raise ValueError("ancestor_circular_reference")
    return roots, children


def plan_sticky_manual_pruning(
    versions, limit, default_id, *, timestamp_key, can_delete
):
    if type(limit) is not int or limit < 0:
        raise ValueError("Invalid maxversions")
    if limit == 1:
        raise ValueError("setdefaultversionsticky_false")
    if default_id not in versions:
        raise ValueError("unknown_id")
    frontier, children = _forest(versions)
    if limit == 0 or len(versions) <= limit:
        return ()
    visited = set()
    deletions = []
    while len(versions) - len(deletions) > limit:
        eligible = [
            name for name in frontier
            if name == default_id or can_delete(name, versions[name])
        ]
        if not eligible:
            raise ValueError("bad_request: no complete legal pruning plan")
        name = min(
            eligible,
            key=lambda item: (timestamp_key(versions[item]["createdat"]), item.lower()),
        )
        frontier.remove(name)
        if name in visited:
            raise ValueError("Pruning traversal revisited a Version")
        visited.add(name)
        if name != default_id:
            deletions.append(name)
        frontier.update(children[name])
    return tuple(deletions)


def manual_ancestors_after_deletions(versions, deletions, default_id):
    """Project only Core's ancestry relation, not epoch/time or event updates."""
    if default_id in deletions:
        raise ValueError("Cannot delete the protected default")
    result = {name: value["ancestorid"] for name, value in versions.items()}
    for deleted in deletions:
        if deleted not in result:
            raise ValueError("unknown_id")
        del result[deleted]
        for name, parent in result.items():
            if parent == deleted:
                result[name] = name
    return result
