"""Exact ordering keys, not elapsed durations or a server/filter implementation.

Positive leap dates are supplied as authoritative UTC (year, month, day) tuples.
The helper does not acquire leap announcements or validate negative leap dates.
"""

import re
from collections.abc import Collection


_TIMESTAMP = re.compile(
    r"([0-9]{4})-([0-9]{2})-([0-9]{2})[Tt]"
    r"([0-9]{2}):([0-9]{2}):([0-9]{2})"
    r"(?:\.([0-9]+))?([Zz]|[+-][0-9]{2}:[0-9]{2})",
    re.ASCII,
)


def _day_number(year: int, month: int, day: int) -> int:
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    lengths = (31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    if not (0 <= year <= 9999 and 1 <= month <= 12 and 1 <= day <= lengths[month - 1]):
        raise ValueError("Invalid RFC3339 date")
    prior = year - 1
    return (
        365 * prior + prior // 4 - prior // 100 + prior // 400
        + sum(lengths[:month - 1]) + day - 1
    )


def timestamp_key(
    value: str,
    *,
    positive_leap_days: Collection[tuple[int, int, int]] = (),
) -> tuple[int, bool, str]:
    if not isinstance(value, str):
        raise ValueError("Invalid RFC3339 timestamp")
    match = _TIMESTAMP.fullmatch(value)
    if match is None:
        raise ValueError("Invalid RFC3339 timestamp")
    year, month, day, hour, minute, second = map(int, match.groups()[:6])
    if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 60):
        raise ValueError("Invalid RFC3339 time")
    offset = match[8]
    offset_seconds = 0
    if offset.upper() != "Z":
        offset_hour, offset_minute = int(offset[1:3]), int(offset[4:6])
        if offset_hour > 23 or offset_minute > 59:
            raise ValueError("Invalid RFC3339 offset")
        offset_seconds = (offset_hour * 60 + offset_minute) * 60
        if offset[0] == "-":
            offset_seconds = -offset_seconds
    whole_second = (
        _day_number(year, month, day) * 86400
        + hour * 3600 + minute * 60 + min(second, 59) - offset_seconds
    )
    leap = second == 60
    if leap and (
        whole_second % 86400 != 86399
        or whole_second // 86400 not in {_day_number(*date) for date in positive_leap_days}
    ):
        raise ValueError("Positive leap-second date is not established")
    # A separate marker keeps a leap second after :59 and before the next :00.
    return whole_second, leap, (match[7] or "").rstrip("0")


def compare_timestamps(
    left: str,
    right: str,
    *,
    positive_leap_days: Collection[tuple[int, int, int]] = (),
) -> int:
    left_key = timestamp_key(left, positive_leap_days=positive_leap_days)
    right_key = timestamp_key(right, positive_leap_days=positive_leap_days)
    return (left_key > right_key) - (left_key < right_key)
