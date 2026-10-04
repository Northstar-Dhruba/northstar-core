"""What a broker reported about one Northstar futures order at one instant.

A FuturesBrokerOrderObservation is an external fact: the broker's order
identifier, its normalized status, how many contracts it says have executed,
and why, when it gives a reason. Northstar records observations; it never
constructs one to stand in for something the broker did not report.

The observation carries its own order, so the requested count it is checked
against is always the one Northstar actually submitted.

Filled count and status must agree
----------------------------------
With ``r`` the requested contracts and ``f`` the filled count, ``0 <= f <= r``
and:

    WORKING    f <  r      (f > 0 is a partial fill still working)
    FILLED     f == r
    CANCELLED  f <  r      (f > 0 is a partial fill that was then withdrawn)
    REJECTED   f == 0

A broker order identifier is required unless the order was REJECTED, because a
broker may refuse an order before assigning it one.

``observed_at`` is when Northstar made the observation, supplied by the caller
rather than read from a clock here. ``reason`` is the broker's optional
explanation, normalized like other optional Core text. There is no raw broker
payload and no broker-specific status.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.broker_execution.value_objects.broker_order_id import BrokerOrderId
from northstar_core.broker_execution.value_objects.broker_order_status import (
    BrokerOrderStatus,
)
from northstar_core.broker_execution.value_objects.client_order_identity import (
    ClientOrderIdentity,
)
from northstar_core.broker_execution.value_objects.futures_broker_order import (
    FuturesBrokerOrder,
)
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime


class InvalidFuturesBrokerOrderObservationError(ValidationError):
    """Raised when a FuturesBrokerOrderObservation value is invalid."""


def _validate_order(value: FuturesBrokerOrder) -> FuturesBrokerOrder:
    if value is None:
        raise InvalidFuturesBrokerOrderObservationError(
            "FuturesBrokerOrderObservation order cannot be None."
        )
    if not isinstance(value, FuturesBrokerOrder):
        raise InvalidFuturesBrokerOrderObservationError(
            "FuturesBrokerOrderObservation order must be a FuturesBrokerOrder value."
        )
    return value


def _validate_broker_order_id(value: BrokerOrderId | None) -> BrokerOrderId | None:
    if value is None:
        return None
    if not isinstance(value, BrokerOrderId):
        raise InvalidFuturesBrokerOrderObservationError(
            "FuturesBrokerOrderObservation broker order id must be a BrokerOrderId value."
        )
    return value


def _validate_status(value: BrokerOrderStatus) -> BrokerOrderStatus:
    if value is None:
        raise InvalidFuturesBrokerOrderObservationError(
            "FuturesBrokerOrderObservation status cannot be None."
        )
    if not isinstance(value, BrokerOrderStatus):
        raise InvalidFuturesBrokerOrderObservationError(
            "FuturesBrokerOrderObservation status must be a BrokerOrderStatus value."
        )
    return value


def _validate_filled_contracts(value: int) -> int:
    if value is None:
        raise InvalidFuturesBrokerOrderObservationError(
            "FuturesBrokerOrderObservation filled contracts cannot be None."
        )
    # bool is an int subclass; True must not pass as one filled contract.
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidFuturesBrokerOrderObservationError(
            "FuturesBrokerOrderObservation filled contracts must be an integer."
        )
    if value < 0:
        raise InvalidFuturesBrokerOrderObservationError(
            "FuturesBrokerOrderObservation filled contracts cannot be negative."
        )
    return value


def _validate_observed_at(value: PointInTime) -> PointInTime:
    if value is None:
        raise InvalidFuturesBrokerOrderObservationError(
            "FuturesBrokerOrderObservation observation instant cannot be None."
        )
    if not isinstance(value, PointInTime):
        raise InvalidFuturesBrokerOrderObservationError(
            "FuturesBrokerOrderObservation observation instant must be a PointInTime value."
        )
    return value


def _normalize_reason(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise InvalidFuturesBrokerOrderObservationError(
            "FuturesBrokerOrderObservation reason must be a string."
        )
    normalized = value.strip()
    if not normalized:
        raise InvalidFuturesBrokerOrderObservationError(
            "FuturesBrokerOrderObservation reason cannot be empty."
        )
    return normalized


@dataclass(frozen=True, slots=True)
class FuturesBrokerOrderObservation:
    """Immutable broker-reported state of one futures order at one instant."""

    order: FuturesBrokerOrder
    broker_order_id: BrokerOrderId | None
    status: BrokerOrderStatus
    filled_contracts: int
    observed_at: PointInTime
    reason: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "order", _validate_order(self.order))
        object.__setattr__(self, "broker_order_id", _validate_broker_order_id(self.broker_order_id))
        object.__setattr__(self, "status", _validate_status(self.status))
        object.__setattr__(
            self, "filled_contracts", _validate_filled_contracts(self.filled_contracts)
        )
        object.__setattr__(self, "observed_at", _validate_observed_at(self.observed_at))
        object.__setattr__(self, "reason", _normalize_reason(self.reason))

        self._validate_fill_agrees_with_status()
        if self.broker_order_id is None and self.status is not BrokerOrderStatus.REJECTED:
            raise InvalidFuturesBrokerOrderObservationError(
                "FuturesBrokerOrderObservation broker order id is required unless the order "
                "was rejected."
            )

    def _validate_fill_agrees_with_status(self) -> None:
        requested = self.order.intent.contracts.value
        filled = self.filled_contracts
        if filled > requested:
            raise InvalidFuturesBrokerOrderObservationError(
                "FuturesBrokerOrderObservation filled contracts cannot exceed the requested "
                "contracts."
            )
        status = self.status
        if status is BrokerOrderStatus.FILLED and filled != requested:
            raise InvalidFuturesBrokerOrderObservationError(
                "FuturesBrokerOrderObservation FILLED requires every requested contract to "
                "be filled."
            )
        if status is BrokerOrderStatus.REJECTED and filled != 0:
            raise InvalidFuturesBrokerOrderObservationError(
                "FuturesBrokerOrderObservation REJECTED requires zero filled contracts."
            )
        if status in (BrokerOrderStatus.WORKING, BrokerOrderStatus.CANCELLED) and (
            filled == requested
        ):
            raise InvalidFuturesBrokerOrderObservationError(
                f"FuturesBrokerOrderObservation {status} requires fewer filled contracts than "
                "requested; a complete fill is FILLED."
            )

    @property
    def client_order_identity(self) -> ClientOrderIdentity:
        """Return the Northstar identity of the observed order."""
        return self.order.identity

    @property
    def is_terminal(self) -> bool:
        """Return whether the broker reported a final status."""
        return self.status.is_terminal

    def __str__(self) -> str:
        return (
            f"{self.order.identity} {self.broker_order_id} {self.status} "
            f"{self.filled_contracts}/{self.order.intent.contracts} {self.observed_at}"
        )

    def __repr__(self) -> str:
        return (
            "FuturesBrokerOrderObservation("
            f"order={self.order!r}, "
            f"broker_order_id={self.broker_order_id!r}, "
            f"status={self.status!r}, "
            f"filled_contracts={self.filled_contracts!r}, "
            f"observed_at={self.observed_at!r}, "
            f"reason={self.reason!r}"
            ")"
        )
