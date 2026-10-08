"""Immutable OHLCV observation for one exact option contract.

The bar records what one option contract traded at over one interval, and
nothing else. Prices are OptionPremium values -- zero or greater, in premium
points, with no currency -- rather than QuoteValue, because an option premium
can never be negative and must not be confused with an underlying or futures
quotation.

Volume is a whole number of option contracts, held as a Quantity. Providers
that report volume in underlying units are converted at the edge; a fractional
contract count is not evidence and is refused here.

A daily bar's ``point_in_time`` is the close of its resolved option trading
session, never a provider timestamp, and the trading date is not stored
separately: it is the session the instant closes.

The bar carries no open interest, provider instrument, source, bid or ask,
settlement price, implied volatility or Greeks. Open interest in particular has
no established units or revision semantics, so it is not canonical market data.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime, Quantity, Timeframe
from northstar_core.options.value_objects import OptionContract, OptionPremium


class InvalidOptionOHLCVBarError(ValidationError):
    """Raised when an option OHLCV observation is invalid."""


def _validate_contract(value: OptionContract) -> OptionContract:
    if value is None:
        raise InvalidOptionOHLCVBarError("OptionOHLCVBar contract cannot be None.")
    if not isinstance(value, OptionContract):
        raise InvalidOptionOHLCVBarError("OptionOHLCVBar contract must be an OptionContract value.")
    return value


def _validate_point_in_time(value: PointInTime) -> PointInTime:
    if value is None:
        raise InvalidOptionOHLCVBarError("OptionOHLCVBar point-in-time context cannot be None.")
    if not isinstance(value, PointInTime):
        raise InvalidOptionOHLCVBarError(
            "OptionOHLCVBar point-in-time context must be a PointInTime value."
        )
    return value


def _validate_timeframe(value: Timeframe) -> Timeframe:
    if value is None:
        raise InvalidOptionOHLCVBarError("OptionOHLCVBar timeframe cannot be None.")
    if not isinstance(value, Timeframe):
        raise InvalidOptionOHLCVBarError("OptionOHLCVBar timeframe must be a Timeframe value.")
    return value


def _validate_premium(value: OptionPremium, field_name: str) -> OptionPremium:
    if value is None:
        raise InvalidOptionOHLCVBarError(f"OptionOHLCVBar {field_name} cannot be None.")
    if not isinstance(value, OptionPremium):
        raise InvalidOptionOHLCVBarError(f"OptionOHLCVBar {field_name} must be an OptionPremium.")
    return value


def _validate_volume(value: Quantity) -> Quantity:
    if value is None:
        raise InvalidOptionOHLCVBarError("OptionOHLCVBar volume cannot be None.")
    if not isinstance(value, Quantity):
        raise InvalidOptionOHLCVBarError("OptionOHLCVBar volume must be a Quantity value.")
    if value.value != value.value.to_integral_value():
        raise InvalidOptionOHLCVBarError(
            f"OptionOHLCVBar volume must be a whole number of option contracts; "
            f"received {value.value}."
        )
    return value


@dataclass(frozen=True, slots=True)
class OptionOHLCVBar:
    """Immutable factual OHLCV observation for one completed option interval.

    ``point_in_time`` is the completion instant of the interval: for a daily
    bar, the close of the resolved option trading session. It is not provider
    publication, arrival or ingestion time.

    Identity is exactly ``(contract, point_in_time, timeframe)``. The contract
    already expands to product, exchange, expiration, strike and right, so a
    call and a put, two strikes and two expiries at one instant are separate
    bars.
    """

    contract: OptionContract
    point_in_time: PointInTime
    timeframe: Timeframe
    open: OptionPremium
    high: OptionPremium
    low: OptionPremium
    close: OptionPremium
    volume: Quantity

    def __post_init__(self) -> None:
        contract = _validate_contract(self.contract)
        point_in_time = _validate_point_in_time(self.point_in_time)
        timeframe = _validate_timeframe(self.timeframe)
        open_premium = _validate_premium(self.open, "open")
        high_premium = _validate_premium(self.high, "high")
        low_premium = _validate_premium(self.low, "low")
        close_premium = _validate_premium(self.close, "close")
        volume = _validate_volume(self.volume)

        if (
            high_premium < open_premium
            or high_premium < close_premium
            or high_premium < low_premium
        ):
            raise InvalidOptionOHLCVBarError(
                "OptionOHLCVBar high must be greater than or equal to open, close, and low."
            )
        if low_premium > open_premium or low_premium > close_premium or low_premium > high_premium:
            raise InvalidOptionOHLCVBarError(
                "OptionOHLCVBar low must be less than or equal to open, close, and high."
            )

        object.__setattr__(self, "contract", contract)
        object.__setattr__(self, "point_in_time", point_in_time)
        object.__setattr__(self, "timeframe", timeframe)
        object.__setattr__(self, "open", open_premium)
        object.__setattr__(self, "high", high_premium)
        object.__setattr__(self, "low", low_premium)
        object.__setattr__(self, "close", close_premium)
        object.__setattr__(self, "volume", volume)

    @property
    def natural_key(self) -> tuple[OptionContract, PointInTime, Timeframe]:
        """Return the identity under which this observation is known."""
        return (self.contract, self.point_in_time, self.timeframe)

    def __str__(self) -> str:
        return (
            f"{self.contract} {self.point_in_time} {self.timeframe} "
            f"O={self.open} H={self.high} L={self.low} C={self.close} V={self.volume}"
        )

    def __repr__(self) -> str:
        return (
            "OptionOHLCVBar("
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
