"""The fixed stop price of one trade recommendation.

The stop is a QuoteValue, compared exactly and never rounded or tick-aligned.
It is fixed for the life of the recommendation: there is no trailing, moving or
revisable stop. Whether it sits on the losing side of the entry zone depends on
the trade direction, which FuturesTradeRecommendation checks.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.derivatives import QuoteValue
from northstar_core.foundation.exceptions.validation import ValidationError


class InvalidStopLossError(ValidationError):
    """Raised when a StopLoss value is invalid."""


def _validate_price(value: QuoteValue) -> QuoteValue:
    if not isinstance(value, QuoteValue):
        raise InvalidStopLossError("StopLoss price must be a QuoteValue.")
    return value


@dataclass(frozen=True, slots=True)
class StopLoss:
    """Immutable fixed price at which an active recommendation is stopped out."""

    price: QuoteValue

    def __post_init__(self) -> None:
        object.__setattr__(self, "price", _validate_price(self.price))

    def __str__(self) -> str:
        return str(self.price)

    def __repr__(self) -> str:
        return f"StopLoss(price={self.price!r})"
