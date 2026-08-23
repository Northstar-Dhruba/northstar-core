"""Reference Market Observation: Quote.

Quote is an immutable observation of quoted market state associated with one
Listing and one PointInTime context.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.domain.listing import Listing
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime
from northstar_core.market_data.value_objects import QuotedMarketState


class InvalidQuoteError(ValidationError):
    """Raised when a Quote value is invalid."""


def _validate_listing(value: Listing) -> Listing:
    if value is None:
        raise InvalidQuoteError("Quote listing cannot be None.")
    if not isinstance(value, Listing):
        raise InvalidQuoteError("Quote listing must be a Listing entity.")
    return value


def _validate_point_in_time(value: PointInTime) -> PointInTime:
    if value is None:
        raise InvalidQuoteError("Quote point-in-time context cannot be None.")
    if not isinstance(value, PointInTime):
        raise InvalidQuoteError("Quote point-in-time context must be a PointInTime value.")
    return value


def _validate_quoted_market_state(value: QuotedMarketState) -> QuotedMarketState:
    if value is None:
        raise InvalidQuoteError("Quote quoted market state cannot be None.")
    if not isinstance(value, QuotedMarketState):
        raise InvalidQuoteError("Quote quoted market state must be a QuotedMarketState value.")
    return value


@dataclass(frozen=True, slots=True)
class Quote:
    """Reference Market Observation for the Market Data bounded context.

    Quote is an immutable observation of quoted market state. It composes
    Listing context, PointInTime temporal context, and QuotedMarketState
    quote-specific business meaning.
    """

    listing: Listing
    point_in_time: PointInTime
    quoted_market_state: QuotedMarketState

    def __post_init__(self) -> None:
        object.__setattr__(self, "listing", _validate_listing(self.listing))
        object.__setattr__(self, "point_in_time", _validate_point_in_time(self.point_in_time))
        object.__setattr__(
            self,
            "quoted_market_state",
            _validate_quoted_market_state(self.quoted_market_state),
        )

    def __str__(self) -> str:
        return (
            f"{self.listing.instrument.symbol}@{self.listing.exchange.exchange_code} "
            f"{self.point_in_time} {self.quoted_market_state}"
        )

    def __repr__(self) -> str:
        return (
            "Quote("
            f"listing={self.listing!r}, "
            f"point_in_time={self.point_in_time!r}, "
            f"quoted_market_state={self.quoted_market_state!r}"
            ")"
        )
