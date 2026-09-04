"""Reference Trade aggregate root.

Trade is an immutable aggregate root that preserves the completed execution
outcome for one Listing at one execution PointInTime. Version 1.0 deliberately
provides no Order relationship, lifecycle, settlement, accounting, or workflow
behavior.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.domain.listing import Listing
from northstar_core.domain.value_objects.participant_reference import ParticipantReference
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime, Price, Quantity
from northstar_core.trades.value_objects import TradeIdentity


class InvalidTradeError(ValidationError):
    """Raised when a Trade aggregate is invalid."""


def _validate_trade_identity(value: TradeIdentity) -> TradeIdentity:
    if value is None:
        raise InvalidTradeError("Trade identity cannot be None.")
    if not isinstance(value, TradeIdentity):
        raise InvalidTradeError("Trade identity must be a TradeIdentity value.")
    return value


def _validate_listing(value: Listing) -> Listing:
    if value is None:
        raise InvalidTradeError("Trade listing cannot be None.")
    if not isinstance(value, Listing):
        raise InvalidTradeError("Trade listing must be a Listing entity.")
    return value


def _validate_point_in_time(value: PointInTime) -> PointInTime:
    if value is None:
        raise InvalidTradeError("Trade point-in-time context cannot be None.")
    if not isinstance(value, PointInTime):
        raise InvalidTradeError("Trade point-in-time context must be a PointInTime value.")
    return value


def _validate_quantity(value: Quantity) -> Quantity:
    if value is None:
        raise InvalidTradeError("Trade quantity cannot be None.")
    if not isinstance(value, Quantity):
        raise InvalidTradeError("Trade quantity must be a Quantity value.")
    return value


def _validate_price(value: Price) -> Price:
    if value is None:
        raise InvalidTradeError("Trade price cannot be None.")
    if not isinstance(value, Price):
        raise InvalidTradeError("Trade price must be a Price value.")
    return value


def _validate_participant_reference(value: ParticipantReference) -> ParticipantReference:
    if value is None:
        raise InvalidTradeError("Trade participant reference cannot be None.")
    if not isinstance(value, ParticipantReference):
        raise InvalidTradeError("Trade participant reference must be a ParticipantReference value.")
    return value


@dataclass(frozen=True, slots=True, eq=False)
class Trade:
    """Reference Aggregate Root for the Trades bounded context.

    Trade preserves one completed execution outcome and its historical context.
    It composes only the approved Version 1.0 Trade concepts and is immutable
    after creation.
    """

    trade_identity: TradeIdentity
    listing: Listing
    point_in_time: PointInTime
    quantity: Quantity
    price: Price
    participant_reference: ParticipantReference

    def __post_init__(self) -> None:
        object.__setattr__(self, "trade_identity", _validate_trade_identity(self.trade_identity))
        object.__setattr__(self, "listing", _validate_listing(self.listing))
        object.__setattr__(self, "point_in_time", _validate_point_in_time(self.point_in_time))
        object.__setattr__(self, "quantity", _validate_quantity(self.quantity))
        object.__setattr__(self, "price", _validate_price(self.price))
        object.__setattr__(
            self,
            "participant_reference",
            _validate_participant_reference(self.participant_reference),
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Trade):
            return NotImplemented
        return self.trade_identity == other.trade_identity

    def __hash__(self) -> int:
        return hash(self.trade_identity)

    def __str__(self) -> str:
        return (
            f"{self.trade_identity} "
            f"{self.listing.instrument.symbol}@{self.listing.exchange.exchange_code} "
            f"{self.point_in_time} {self.quantity} {self.price} {self.participant_reference}"
        )

    def __repr__(self) -> str:
        return (
            "Trade("
            f"trade_identity={self.trade_identity!r}, "
            f"listing={self.listing!r}, "
            f"point_in_time={self.point_in_time!r}, "
            f"quantity={self.quantity!r}, "
            f"price={self.price!r}, "
            f"participant_reference={self.participant_reference!r}"
            ")"
        )
