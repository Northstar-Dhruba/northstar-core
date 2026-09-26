"""Immutable historical OHLCV observation for one canonical futures contract.

The bar records what one contract traded at over one interval, and nothing
else. Quotations are QuoteValue rather than Price because futures are not
universally quoted in currency and do go negative; see QuoteValue for why.

Why there is no adjusted close
------------------------------
An equity adjusted close corrects for splits and dividends, which are corporate
actions on a share. A futures contract has neither, so there is no adjustment
to apply. The superficially similar futures concept is back-adjustment for a
continuous series, and it is a different thing in every way that matters: it
describes a constructed research series rather than a contract observation, and
it is method-dependent -- ratio or difference -- so the number alone would not
say what it meant. Carrying the field would invite a back-adjusted value to be
stored as if it were raw contract data.

Why open interest is not here yet
---------------------------------
Open interest is an end-of-session figure, conventionally published a session
late. On a daily bar it is meaningful; on a one-minute bar it is either
meaningless or a stale daily figure repeated across every intraday bar, and
nothing in the contract would say which. Its meaning would depend on the value
of the timeframe field, which is the definition of a field without clear
semantics. It waits for a consumer that forces the definition.

The bar carries no provider symbol, listing identity, multiplier, tick size,
continuous-contract construction, rollover, margin or profit and loss.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.derivatives.value_objects import QuoteValue
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime, Quantity, Timeframe
from northstar_core.futures.value_objects import FuturesContract


class InvalidFuturesOHLCVBarError(ValidationError):
    """Raised when a futures OHLCV observation is invalid."""


def _validate_contract(value: FuturesContract) -> FuturesContract:
    if value is None:
        raise InvalidFuturesOHLCVBarError("FuturesOHLCVBar contract cannot be None.")
    if not isinstance(value, FuturesContract):
        raise InvalidFuturesOHLCVBarError(
            "FuturesOHLCVBar contract must be a FuturesContract value."
        )
    return value


def _validate_point_in_time(value: PointInTime) -> PointInTime:
    if value is None:
        raise InvalidFuturesOHLCVBarError("FuturesOHLCVBar point-in-time context cannot be None.")
    if not isinstance(value, PointInTime):
        raise InvalidFuturesOHLCVBarError(
            "FuturesOHLCVBar point-in-time context must be a PointInTime value."
        )
    return value


def _validate_timeframe(value: Timeframe) -> Timeframe:
    if value is None:
        raise InvalidFuturesOHLCVBarError("FuturesOHLCVBar timeframe cannot be None.")
    if not isinstance(value, Timeframe):
        raise InvalidFuturesOHLCVBarError("FuturesOHLCVBar timeframe must be a Timeframe value.")
    return value


def _validate_quote(value: QuoteValue, field_name: str) -> QuoteValue:
    if value is None:
        raise InvalidFuturesOHLCVBarError(f"FuturesOHLCVBar {field_name} cannot be None.")
    if not isinstance(value, QuoteValue):
        raise InvalidFuturesOHLCVBarError(f"FuturesOHLCVBar {field_name} must be a QuoteValue.")
    return value


def _validate_volume(value: Quantity) -> Quantity:
    if value is None:
        raise InvalidFuturesOHLCVBarError("FuturesOHLCVBar volume cannot be None.")
    if not isinstance(value, Quantity):
        raise InvalidFuturesOHLCVBarError("FuturesOHLCVBar volume must be a Quantity value.")
    return value


@dataclass(frozen=True, slots=True)
class FuturesOHLCVBar:
    """Immutable factual OHLCV observation for one completed futures interval.

    ``point_in_time`` is the completion instant of the interval: the earliest
    logical instant at which the completed bar may take part in deterministic
    replay. It is not provider publication, arrival, ingestion or settlement
    time.

    Identity is exactly ``(contract, point_in_time, timeframe)``. The contract
    already expands to product code, exchange and expiry, so ES and MES at one
    instant are separate bars, and March and June of one product are too.
    """

    contract: FuturesContract
    point_in_time: PointInTime
    timeframe: Timeframe
    open: QuoteValue
    high: QuoteValue
    low: QuoteValue
    close: QuoteValue
    volume: Quantity

    def __post_init__(self) -> None:
        contract = _validate_contract(self.contract)
        point_in_time = _validate_point_in_time(self.point_in_time)
        timeframe = _validate_timeframe(self.timeframe)
        open_quote = _validate_quote(self.open, "open")
        high_quote = _validate_quote(self.high, "high")
        low_quote = _validate_quote(self.low, "low")
        close_quote = _validate_quote(self.close, "close")
        volume = _validate_volume(self.volume)

        if high_quote < open_quote or high_quote < close_quote or high_quote < low_quote:
            raise InvalidFuturesOHLCVBarError(
                "FuturesOHLCVBar high must be greater than or equal to open, close, and low."
            )
        if low_quote > open_quote or low_quote > close_quote or low_quote > high_quote:
            raise InvalidFuturesOHLCVBarError(
                "FuturesOHLCVBar low must be less than or equal to open, close, and high."
            )

        object.__setattr__(self, "contract", contract)
        object.__setattr__(self, "point_in_time", point_in_time)
        object.__setattr__(self, "timeframe", timeframe)
        object.__setattr__(self, "open", open_quote)
        object.__setattr__(self, "high", high_quote)
        object.__setattr__(self, "low", low_quote)
        object.__setattr__(self, "close", close_quote)
        object.__setattr__(self, "volume", volume)

    @property
    def natural_key(self) -> tuple[FuturesContract, PointInTime, Timeframe]:
        """Return the identity under which this observation is known."""
        return (self.contract, self.point_in_time, self.timeframe)

    def __str__(self) -> str:
        return (
            f"{self.contract} {self.point_in_time} {self.timeframe} "
            f"O={self.open} H={self.high} L={self.low} C={self.close} V={self.volume}"
        )

    def __repr__(self) -> str:
        return (
            "FuturesOHLCVBar("
            f"contract={self.contract!r}, "
            f"point_in_time={self.point_in_time!r}, "
            f"timeframe={self.timeframe!r}, "
            f"open={self.open!r}, "
            f"high={self.high!r}, "
            f"low={self.low!r}, "
            f"close={self.close!r}, "
            f"volume={self.volume!r}"
            ")"
        )
