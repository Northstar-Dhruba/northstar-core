"""Product-level futures economics, retained for historical reference.

This value states one point value for every expiry of an exchange-defined
product, so ES December and ES March both resolve to the economics of ES@CME.
It was the profit and loss authority of the original ES reference MVP, and it
is kept unchanged so that history recorded under that model stays readable.

It is no longer the profit and loss authority. A product does not determine
its point value: an exchange can revise a contract size so that expiries of one
product trade side by side with different sizes. Profit and loss now resolves
FuturesContractEconomics, keyed by the individual contract, and product
economics are never read in its place or as a fallback for it.

The only fact carried is the point value, which already holds both the
settlement-currency rate per quote point and the settlement currency itself.
There is deliberately no second currency field that could disagree with it, and
no tick size, tick value, notional or margin.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import Currency
from northstar_core.futures.value_objects.futures_point_value import FuturesPointValue
from northstar_core.futures.value_objects.futures_product_reference import (
    FuturesProductReference,
)


class InvalidFuturesProductEconomicsError(ValidationError):
    """Raised when a FuturesProductEconomics value is invalid."""


def _validate_reference(value: FuturesProductReference) -> FuturesProductReference:
    if value is None:
        raise InvalidFuturesProductEconomicsError(
            "FuturesProductEconomics reference cannot be None."
        )
    if not isinstance(value, FuturesProductReference):
        raise InvalidFuturesProductEconomicsError(
            "FuturesProductEconomics reference must be a FuturesProductReference value."
        )
    return value


def _validate_point_value(value: FuturesPointValue) -> FuturesPointValue:
    if value is None:
        raise InvalidFuturesProductEconomicsError(
            "FuturesProductEconomics point value cannot be None."
        )
    if not isinstance(value, FuturesPointValue):
        raise InvalidFuturesProductEconomicsError(
            "FuturesProductEconomics point value must be a FuturesPointValue value."
        )
    return value


@dataclass(frozen=True, slots=True)
class FuturesProductEconomics:
    """Immutable product-level economics; superseded by FuturesContractEconomics for P&L."""

    reference: FuturesProductReference
    point_value: FuturesPointValue

    def __post_init__(self) -> None:
        object.__setattr__(self, "reference", _validate_reference(self.reference))
        object.__setattr__(self, "point_value", _validate_point_value(self.point_value))

    @property
    def settlement_currency(self) -> Currency:
        """Return the currency the product settles in, owned by the point value."""
        return self.point_value.currency

    def __str__(self) -> str:
        return f"{self.reference} {self.point_value}"

    def __repr__(self) -> str:
        return (
            "FuturesProductEconomics("
            f"reference={self.reference!r}, "
            f"point_value={self.point_value!r}"
            ")"
        )
