"""Offline value-space model of the Message dayTimeDuration profile."""

import re
from fractions import Fraction


_DURATION = re.compile(
    r"(?P<negative>-)?P(?:(?P<days>[0-9]+)D)?"
    r"(?:T(?:(?P<hours>[0-9]+)H)?(?:(?P<minutes>[0-9]+)M)?"
    r"(?:(?P<seconds>[0-9]+(?:\.[0-9]*)?|\.[0-9]+)S)?)?"
)


def parse_duration(
    value: str,
    *,
    minimum: Fraction | None = None,
    maximum: Fraction | None = None,
) -> Fraction:
    if not isinstance(value, str):
        raise TypeError("duration must be a string")
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValueError("minimum exceeds maximum")
    collapsed = re.sub(r"[ \t\r\n]+", " ", value).strip(" ")
    match = _DURATION.fullmatch(collapsed)
    if match is None or not any(
        match[name] is not None for name in ("days", "hours", "minutes", "seconds")
    ) or collapsed.endswith("T"):
        raise ValueError("invalid XML Schema dayTimeDuration")
    seconds = sum(
        (
            Fraction(match[name] or "0") * scale
            for name, scale in (
                ("days", 86400),
                ("hours", 3600),
                ("minutes", 60),
                ("seconds", 1),
            )
        ),
        Fraction(0),
    )
    if match["negative"]:
        seconds = -seconds
    if minimum is not None and seconds < minimum:
        raise ValueError("duration is below the field minimum")
    if maximum is not None and seconds > maximum:
        raise ValueError("duration exceeds the field maximum")
    return seconds
