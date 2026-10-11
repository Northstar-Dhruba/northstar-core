"""The inclusive price range in which one trade recommendation becomes active.

Both bounds are QuoteValues in the contract's own quotation convention, so
comparisons are exact Decimal comparisons and never binary floating point.
Nothing here rounds a bound or aligns it to a tick: no tick-size model exists
yet, so a numerically valid zone is not proof that the exchange can trade it.
Whether the zone sits between the stop and the target depends on the trade
direction, which FuturesTradeRecommendation checks.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.derivatives import QuoteValue
from northstar_core.foundation.exceptions.validation import ValidationError


class InvalidEntryZoneError(ValidationError):
    """Raised when an EntryZone value is invalid."""


def _validate_bound(value: QuoteValue, field_name: str) -> QuoteValue:
    if not isinstance(value, QuoteValue):
        raise InvalidEntryZoneError(f"EntryZone {field_name} must be a QuoteValue.")
    return value


@dataclass(frozen=True, slots=True)
class EntryZone:
    """Immutable inclusive entry price range.

    Invariants:
        - ``low <= high``; a single-price zone has ``low == high``.
        - Both bounds are inclusive.
    """

    low: QuoteValue
    high: QuoteValue

    def __post_init__(self) -> None:
        low = _validate_bound(self.low, "low")
        high = _validate_bound(self.high, "high")
        if low > high:
            raise InvalidEntryZoneError("EntryZone low must be less than or equal to high.")
        object.__setattr__(self, "low", low)
        object.__setattr__(self, "high", high)

    def __str__(self) -> str:
        return f"{self.low}-{self.high}"

    def __repr__(self) -> str:
        return f"EntryZone(low={self.low!r}, high={self.high!r})"
