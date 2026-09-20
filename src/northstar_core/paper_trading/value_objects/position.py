"""Held quantity of one listed asset in a paper portfolio.

Position states a holding; it does not compute one. Deriving a position from a
sequence of fills -- accumulating quantity and recalculating cost basis -- is
orchestration that needs an explicit Decimal context and belongs to the later
portfolio-fold use case, not to this value.

A Position is long-only and strictly non-empty: a flat holding is represented
by the absence of a Position, never by a zero quantity. Storing zero would make
"holds nothing" indistinguishable from "was never held", the same absence-is-
not-zero rule research metrics already follow.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.domain.value_objects import ListingReference
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import Price, Quantity


class InvalidPositionError(ValidationError):
    """Raised when a paper-trading Position value is invalid."""


def _validate_listing_reference(value: ListingReference) -> ListingReference:
    if value is None:
        raise InvalidPositionError("Position listing reference cannot be None.")
    if not isinstance(value, ListingReference):
        raise InvalidPositionError("Position listing reference must be a ListingReference value.")
    return value


def _validate_quantity(value: Quantity) -> Quantity:
    if value is None:
        raise InvalidPositionError("Position quantity cannot be None.")
    if not isinstance(value, Quantity):
        raise InvalidPositionError("Position quantity must be a Quantity value.")
    if value.value <= 0:
        raise InvalidPositionError("Position quantity must be greater than zero.")
    return value


def _validate_average_price(value: Price) -> Price:
    if value is None:
        raise InvalidPositionError("Position average price cannot be None.")
    if not isinstance(value, Price):
        raise InvalidPositionError("Position average price must be a Price value.")
    if value.amount <= 0:
        raise InvalidPositionError("Position average price must be greater than zero.")
    return value


@dataclass(frozen=True, slots=True)
class Position:
    """Immutable held quantity of one listed asset at one average price.

    ``average_price`` is the cost basis per unit and fixes the position's
    currency. Position carries no market value, unrealised profit and loss,
    valuation instant, leverage or margin meaning.
    """

    listing_reference: ListingReference
    quantity: Quantity
    average_price: Price

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "listing_reference", _validate_listing_reference(self.listing_reference)
        )
        object.__setattr__(self, "quantity", _validate_quantity(self.quantity))
        object.__setattr__(self, "average_price", _validate_average_price(self.average_price))

    def __str__(self) -> str:
        return f"{self.listing_reference} {self.quantity} @ {self.average_price}"

    def __repr__(self) -> str:
        return (
            "Position("
            f"listing_reference={self.listing_reference!r}, "
            f"quantity={self.quantity!r}, "
            f"average_price={self.average_price!r}"
            ")"
        )
