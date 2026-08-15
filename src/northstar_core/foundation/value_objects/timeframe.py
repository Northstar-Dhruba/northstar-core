"""Canonical temporal interval value object.

Purpose:
    Represent a standardized temporal interval label as an immutable domain value.

Note:
    Timeframe labels are intentionally case-sensitive. For example, 1m means
    one minute and 1M means one month. These are different approved business
    concepts. Case carries business meaning and MUST NOT be normalized.

Invariants:
    - A Timeframe instance is always valid.
    - A Timeframe value is always normalized by trimming surrounding whitespace.
    - A Timeframe value always matches the approved Temporal Family vocabulary.

Examples:
    1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w, 1M, 1Y
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import InvalidTimeframeError

_TIMEFRAME_VALUES = frozenset({"1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M", "1Y"})


def _normalize(value: str) -> str:
    if value is None:
        raise InvalidTimeframeError("Timeframe cannot be None.")
    if not isinstance(value, str):
        raise InvalidTimeframeError("Timeframe must be a string.")
    normalized = value.strip()
    if not normalized:
        raise InvalidTimeframeError("Timeframe cannot be empty.")
    return normalized


def _validate(value: str) -> None:
    if value not in _TIMEFRAME_VALUES:
        raise InvalidTimeframeError("Timeframe is not part of the approved vocabulary.")


@dataclass(frozen=True, slots=True, order=True)
class Timeframe:
    """Immutable representation of a canonical temporal interval.

    Purpose:
        Preserve a standardized temporal interval label as a domain value.

    Invariants:
        - The stored value is always valid.
        - The stored value is always normalized by trimming surrounding whitespace.
        - The stored value matches the approved Temporal Family vocabulary.

    Examples:
        1m
        5m
        15m
        30m
        1h
        4h
        1d
        1w
        1M
        1Y
    """

    value: str

    def __post_init__(self) -> None:
        normalized = _normalize(self.value)
        _validate(normalized)
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"Timeframe(value={self.value!r})"
