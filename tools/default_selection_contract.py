"""Abstract candidate validation after Meta/default/flag and Version processing.

This does not select, create or mutate Versions, or implement request processing.
The caller identifies whether this candidate is the effective sticky selection.
"""

import re
from collections.abc import Collection


_VERSION_ID = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.~:@-]{0,127}", re.ASCII)


def validate_default_candidate(
    candidate: object,
    final_version_ids: Collection[str],
    *,
    effective_sticky_selection: bool,
) -> None:
    if type(effective_sticky_selection) is not bool:
        raise TypeError("effective_sticky_selection must be Boolean")
    if candidate is not None and (
        type(candidate) is not str or _VERSION_ID.fullmatch(candidate) is None
    ):
        raise ValueError("Invalid versionid kind or syntax")
    if effective_sticky_selection and candidate not in final_version_ids:
        raise ValueError("unknown_id")
