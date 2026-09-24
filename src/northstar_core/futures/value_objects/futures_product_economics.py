"""The economic facts profit and loss needs about one futures product.

Economics belong to the exchange-defined product, not to a contract: every
expiry of a product shares them, so ES December and ES March both resolve to
the economics of ES@CME while remaining distinct contracts, positions and
records.

The only fact carried is the point value, which already holds both the
settlement-currency rate per quote point and the settlement currency itself.
There is deliberately no second currency field that could disagree with it, and
no tick size, tick value, notional or margin: nothing consumes them yet.

Economics are assumed constant for one product reference. A product whose
specification changes over time would need effective-dated economics, which
are deferred.
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
    """Immutable economics of one exchange-defined futures product."""

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
