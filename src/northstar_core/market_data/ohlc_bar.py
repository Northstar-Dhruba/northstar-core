"""Reference Interval Market Observation: OHLC Bar.

OHLCBar is an immutable interval observation of market state associated with
one Listing, one PointInTime context, and one Timeframe context.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.domain.listing import Listing
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime, Timeframe
from northstar_core.market_data.value_objects import BarState


class InvalidOHLCBarError(ValidationError):
    """Raised when an OHLCBar value is invalid."""


def _validate_listing(value: Listing) -> Listing:
    if value is None:
        raise InvalidOHLCBarError("OHLCBar listing cannot be None.")
    if not isinstance(value, Listing):
        raise InvalidOHLCBarError("OHLCBar listing must be a Listing entity.")
    return value


def _validate_point_in_time(value: PointInTime) -> PointInTime:
    if value is None:
        raise InvalidOHLCBarError("OHLCBar point-in-time context cannot be None.")
    if not isinstance(value, PointInTime):
        raise InvalidOHLCBarError("OHLCBar point-in-time context must be a PointInTime value.")
    return value


def _validate_timeframe(value: Timeframe) -> Timeframe:
    if value is None:
        raise InvalidOHLCBarError("OHLCBar timeframe context cannot be None.")
    if not isinstance(value, Timeframe):
        raise InvalidOHLCBarError("OHLCBar timeframe context must be a Timeframe value.")
    return value


def _validate_bar_state(value: BarState) -> BarState:
    if value is None:
        raise InvalidOHLCBarError("OHLCBar bar state cannot be None.")
    if not isinstance(value, BarState):
        raise InvalidOHLCBarError("OHLCBar bar state must be a BarState value.")
    return value


@dataclass(frozen=True, slots=True)
class OHLCBar:
    """Reference Interval Market Observation for the Market Data bounded context.

    OHLCBar is an immutable interval observation of market state. It composes
    Listing context, PointInTime temporal context, Timeframe interval context,
    and BarState interval observation meaning.
    """

    listing: Listing
    point_in_time: PointInTime
    timeframe: Timeframe
    bar_state: BarState

    def __post_init__(self) -> None:
        object.__setattr__(self, "listing", _validate_listing(self.listing))
        object.__setattr__(self, "point_in_time", _validate_point_in_time(self.point_in_time))
        object.__setattr__(self, "timeframe", _validate_timeframe(self.timeframe))
        object.__setattr__(self, "bar_state", _validate_bar_state(self.bar_state))

    def __str__(self) -> str:
        return (
            f"{self.listing.instrument.symbol}@{self.listing.exchange.exchange_code} "
            f"{self.point_in_time} {self.timeframe} {self.bar_state}"
        )

    def __repr__(self) -> str:
        return (
            "OHLCBar("
            f"listing={self.listing!r}, "
            f"point_in_time={self.point_in_time!r}, "
            f"timeframe={self.timeframe!r}, "
            f"bar_state={self.bar_state!r}"
            ")"
        )
