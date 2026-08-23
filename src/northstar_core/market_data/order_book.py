"""Reference Market-Depth Observation: OrderBook.

OrderBook is an immutable market-depth observation associated with one Listing
and one PointInTime context.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.domain.listing import Listing
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime
from northstar_core.market_data.value_objects import OrderBookState


class InvalidOrderBookError(ValidationError):
    """Raised when an OrderBook value is invalid."""


def _validate_listing(value: Listing) -> Listing:
    if value is None:
        raise InvalidOrderBookError("OrderBook listing cannot be None.")
    if not isinstance(value, Listing):
        raise InvalidOrderBookError("OrderBook listing must be a Listing entity.")
    return value


def _validate_point_in_time(value: PointInTime) -> PointInTime:
    if value is None:
        raise InvalidOrderBookError("OrderBook point-in-time context cannot be None.")
    if not isinstance(value, PointInTime):
        raise InvalidOrderBookError("OrderBook point-in-time context must be a PointInTime value.")
    return value


def _validate_order_book_state(value: OrderBookState) -> OrderBookState:
    if value is None:
        raise InvalidOrderBookError("OrderBook order book state cannot be None.")
    if not isinstance(value, OrderBookState):
        raise InvalidOrderBookError("OrderBook order book state must be an OrderBookState value.")
    return value


@dataclass(frozen=True, slots=True)
class OrderBook:
    """Reference Market-Depth Observation for the Market Data bounded context.

    OrderBook is an immutable observation of market depth. It composes Listing
    context, PointInTime temporal context, and OrderBookState market-depth
    observation meaning.
    """

    listing: Listing
    point_in_time: PointInTime
    order_book_state: OrderBookState

    def __post_init__(self) -> None:
        object.__setattr__(self, "listing", _validate_listing(self.listing))
        object.__setattr__(self, "point_in_time", _validate_point_in_time(self.point_in_time))
        object.__setattr__(
            self,
            "order_book_state",
            _validate_order_book_state(self.order_book_state),
        )

    def __str__(self) -> str:
        return (
            f"{self.listing.instrument.symbol}@{self.listing.exchange.exchange_code} "
            f"{self.point_in_time} {self.order_book_state}"
        )

    def __repr__(self) -> str:
        return (
            "OrderBook("
            f"listing={self.listing!r}, "
            f"point_in_time={self.point_in_time!r}, "
            f"order_book_state={self.order_book_state!r}"
            ")"
        )
