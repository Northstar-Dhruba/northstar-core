"""Canonical point-in-time value object.

Purpose:
    Represent one unique, globally unambiguous temporal location as an
    immutable domain value.

Note:
    PointInTime represents a specific temporal location. Timeframe represents
    interval identity. These temporal Foundation Value Objects complement one
    another without sharing behavior.

Examples:
    2026-08-17T09:30:00Z
    2026-08-17T14:30:00+05:00
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime

from northstar_core.foundation.exceptions.validation import InvalidPointInTimeError

_POINT_IN_TIME_PATTERN = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})T"
    r"(?P<time>\d{2}:\d{2}:\d{2})"
    r"(?:\.(?P<fraction>\d+))?"
    r"(?P<offset>Z|[+-]\d{2}:\d{2})$"
)


def _normalize(value: str) -> str:
    if value is None:
        raise InvalidPointInTimeError("PointInTime cannot be None.")
    if not isinstance(value, str):
        raise InvalidPointInTimeError("PointInTime must be a string.")
    normalized = value.strip()
    if not normalized:
        raise InvalidPointInTimeError("PointInTime cannot be empty.")
    return normalized


def _validate(value: str) -> re.Match[str]:
    match = _POINT_IN_TIME_PATTERN.fullmatch(value)
    if match is None:
        raise InvalidPointInTimeError(
            "PointInTime must include a complete date, time, and UTC offset."
        )
    return match


def _canonicalize(value: str, match: re.Match[str]) -> str:
    fraction = match.group("fraction") or ""
    if len(fraction) > 6:
        raise InvalidPointInTimeError(
            "PointInTime fractional precision cannot exceed six decimal places."
        )
    microsecond_text = fraction.ljust(6, "0")
    offset = "+00:00" if match.group("offset") == "Z" else match.group("offset")

    try:
        temporal_value = datetime.fromisoformat(
            f"{match.group('date')}T{match.group('time')}.{microsecond_text}{offset}"
        )
    except ValueError as exc:
        raise InvalidPointInTimeError("PointInTime contains an invalid temporal value.") from exc

    utc_value = temporal_value.astimezone(UTC)
    canonical_fraction = f"{utc_value.microsecond:06d}".rstrip("0")
    canonical_value = utc_value.strftime("%Y-%m-%dT%H:%M:%S")
    if canonical_fraction:
        canonical_value = f"{canonical_value}.{canonical_fraction}"
    return f"{canonical_value}Z"


def _to_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@dataclass(frozen=True, slots=True)
class PointInTime:
    """Immutable representation of a canonical specific temporal location.

    PointInTime accepts a complete temporal value with an explicit UTC
    designation or numeric UTC offset and stores its equivalent canonical UTC
    representation. It has no independent identity and does not represent an
    interval, duration, or Timeframe.
    """

    value: str
    _temporal_value: datetime = field(init=False, repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        normalized = _normalize(self.value)
        match = _validate(normalized)
        canonical_value = _canonicalize(normalized, match)
        object.__setattr__(self, "value", canonical_value)
        object.__setattr__(self, "_temporal_value", _to_datetime(canonical_value))

    def compare(self, other: object) -> int:
        """Compare two PointInTime values chronologically.

        Returns -1 when this value is earlier, 0 when equal, and 1 when later.
        PointInTime intentionally remains non-orderable through Python's
        ordering operators; consumers use this explicit temporal operation.
        """
        if not isinstance(other, PointInTime):
            raise TypeError("PointInTime can only be compared with PointInTime.")
        if self._temporal_value < other._temporal_value:
            return -1
        if self._temporal_value > other._temporal_value:
            return 1
        return 0

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"PointInTime(value={self.value!r})"
