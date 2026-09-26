"""Reference High-Frequency Point Market Observation: Tick.

Tick is an immutable high-frequency point observation associated with one
Listing and one PointInTime context.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.domain.listing import Listing
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime
from northstar_core.market_data.value_objects import TickState


class InvalidTickError(ValidationError):
    """Raised when a Tick value is invalid."""


def _validate_listing(value: Listing) -> Listing:
    if value is None:
        raise InvalidTickError("Tick listing cannot be None.")
    if not isinstance(value, Listing):
        raise InvalidTickError("Tick listing must be a Listing entity.")
    return value


def _validate_point_in_time(value: PointInTime) -> PointInTime:
    if value is None:
        raise InvalidTickError("Tick point-in-time context cannot be None.")
    if not isinstance(value, PointInTime):
        raise InvalidTickError("Tick point-in-time context must be a PointInTime value.")
    return value


def _validate_tick_state(value: TickState) -> TickState:
    if value is None:
        raise InvalidTickError("Tick state cannot be None.")
    if not isinstance(value, TickState):
        raise InvalidTickError("Tick state must be a TickState value.")
    return value


@dataclass(frozen=True, slots=True)
class Tick:
    """Reference High-Frequency Point Market Observation.

    Tick is an immutable high-frequency point market observation. It composes
    Listing context, PointInTime temporal context, and TickState
    high-frequency point business meaning.
    """

    listing: Listing
    point_in_time: PointInTime
    tick_state: TickState

    def __post_init__(self) -> None:
        object.__setattr__(self, "listing", _validate_listing(self.listing))
        object.__setattr__(self, "point_in_time", _validate_point_in_time(self.point_in_time))
        object.__setattr__(self, "tick_state", _validate_tick_state(self.tick_state))

    def __str__(self) -> str:
        return (
            f"{self.listing.instrument.symbol}@{self.listing.exchange.exchange_code} "
            f"{self.point_in_time} {self.tick_state}"
        )

    def __repr__(self) -> str:
        return (
            "Tick("
            f"listing={self.listing!r}, "
            f"point_in_time={self.point_in_time!r}, "
            f"tick_state={self.tick_state!r}"
            ")"
        )
