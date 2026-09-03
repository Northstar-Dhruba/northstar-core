"""Reference Order aggregate root.

Order is an immutable-identity, lifecycle-oriented aggregate root that
preserves participant intent and transaction commitment for one Listing.
Version 1.0 deliberately provides no lifecycle transitions, workflow, or
execution behavior.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.domain.listing import Listing
from northstar_core.domain.value_objects.participant_reference import ParticipantReference
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime, Price, Quantity
from northstar_core.orders.value_objects import OrderIdentity, OrderStatus


class InvalidOrderError(ValidationError):
    """Raised when an Order aggregate is invalid."""


def _validate_order_identity(value: OrderIdentity) -> OrderIdentity:
    if value is None:
        raise InvalidOrderError("Order identity cannot be None.")
    if not isinstance(value, OrderIdentity):
        raise InvalidOrderError("Order identity must be an OrderIdentity value.")
    return value


def _validate_listing(value: Listing) -> Listing:
    if value is None:
        raise InvalidOrderError("Order listing cannot be None.")
    if not isinstance(value, Listing):
        raise InvalidOrderError("Order listing must be a Listing entity.")
    return value


def _validate_point_in_time(value: PointInTime) -> PointInTime:
    if value is None:
        raise InvalidOrderError("Order point-in-time context cannot be None.")
    if not isinstance(value, PointInTime):
        raise InvalidOrderError("Order point-in-time context must be a PointInTime value.")
    return value


def _validate_quantity(value: Quantity) -> Quantity:
    if value is None:
        raise InvalidOrderError("Order quantity cannot be None.")
    if not isinstance(value, Quantity):
        raise InvalidOrderError("Order quantity must be a Quantity value.")
    return value


def _validate_price(value: Price) -> Price:
    if value is None:
        raise InvalidOrderError("Order price cannot be None.")
    if not isinstance(value, Price):
        raise InvalidOrderError("Order price must be a Price value.")
    return value


def _validate_participant_reference(value: ParticipantReference) -> ParticipantReference:
    if value is None:
        raise InvalidOrderError("Order participant reference cannot be None.")
    if not isinstance(value, ParticipantReference):
        raise InvalidOrderError("Order participant reference must be a ParticipantReference value.")
    return value


def _validate_order_status(value: OrderStatus) -> OrderStatus:
    if value is None:
        raise InvalidOrderError("Order status cannot be None.")
    if not isinstance(value, OrderStatus):
        raise InvalidOrderError("Order status must be an OrderStatus value.")
    return value


@dataclass(slots=True, eq=False)
class Order:
    """Reference Aggregate Root for the Orders bounded context.

    Order preserves one participant's intent and transaction commitment for a
    Listing. It composes only the approved Version 1.0 Order concepts.

    Order identity remains stable across lifecycle changes. Lifecycle
    transitions, workflow behavior, and execution behavior are intentionally
    outside this implementation.
    """

    order_identity: OrderIdentity
    listing: Listing
    point_in_time: PointInTime
    quantity: Quantity
    price: Price
    participant_reference: ParticipantReference
    order_status: OrderStatus

    def __post_init__(self) -> None:
        self.order_identity = _validate_order_identity(self.order_identity)
        self.listing = _validate_listing(self.listing)
        self.point_in_time = _validate_point_in_time(self.point_in_time)
        self.quantity = _validate_quantity(self.quantity)
        self.price = _validate_price(self.price)
        self.participant_reference = _validate_participant_reference(self.participant_reference)
        self.order_status = _validate_order_status(self.order_status)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Order):
            return NotImplemented
        return self.order_identity == other.order_identity

    def __hash__(self) -> int:
        return hash(self.order_identity)

    def __str__(self) -> str:
        return (
            f"{self.order_identity} "
            f"{self.listing.instrument.symbol}@{self.listing.exchange.exchange_code} "
            f"{self.point_in_time} {self.quantity} {self.price} "
            f"{self.participant_reference} {self.order_status}"
        )

    def __repr__(self) -> str:
        return (
            "Order("
            f"order_identity={self.order_identity!r}, "
            f"listing={self.listing!r}, "
            f"point_in_time={self.point_in_time!r}, "
            f"quantity={self.quantity!r}, "
            f"price={self.price!r}, "
            f"participant_reference={self.participant_reference!r}, "
            f"order_status={self.order_status!r}"
            ")"
        )
