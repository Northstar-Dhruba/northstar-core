"""The single target price of one trade recommendation.

The target is a QuoteValue, compared exactly and never rounded or tick-aligned.
A recommendation has exactly one target; target sequences, partial exits and
allocations are not modelled. Whether it sits on the winning side of the entry
zone depends on the trade direction, which FuturesTradeRecommendation checks.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.derivatives import QuoteValue
from northstar_core.foundation.exceptions.validation import ValidationError


class InvalidPriceTargetError(ValidationError):
    """Raised when a PriceTarget value is invalid."""


def _validate_price(value: QuoteValue) -> QuoteValue:
    if not isinstance(value, QuoteValue):
        raise InvalidPriceTargetError("PriceTarget price must be a QuoteValue.")
    return value


@dataclass(frozen=True, slots=True)
class PriceTarget:
    """Immutable fixed price at which an active recommendation reaches its target."""

    price: QuoteValue

    def __post_init__(self) -> None:
        object.__setattr__(self, "price", _validate_price(self.price))

    def __str__(self) -> str:
        return str(self.price)

    def __repr__(self) -> str:
        return f"PriceTarget(price={self.price!r})"
