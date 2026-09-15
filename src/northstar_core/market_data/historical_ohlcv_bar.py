"""Immutable historical OHLCV market observation for one Listing."""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import (
    ExchangeCode,
    PointInTime,
    Price,
    Quantity,
    Symbol,
    Timeframe,
)


class InvalidHistoricalOHLCVBarError(ValidationError):
    """Raised when a historical OHLCV observation is invalid."""


def _validate_point_in_time(value: PointInTime) -> PointInTime:
    if value is None:
        raise InvalidHistoricalOHLCVBarError(
            "HistoricalOHLCVBar point-in-time context cannot be None."
        )
    if not isinstance(value, PointInTime):
        raise InvalidHistoricalOHLCVBarError(
            "HistoricalOHLCVBar point-in-time context must be a PointInTime value."
        )
    return value


def _validate_timeframe(value: Timeframe) -> Timeframe:
    if value is None:
        raise InvalidHistoricalOHLCVBarError("HistoricalOHLCVBar timeframe cannot be None.")
    if not isinstance(value, Timeframe):
        raise InvalidHistoricalOHLCVBarError(
            "HistoricalOHLCVBar timeframe must be a Timeframe value."
        )
    return value


def _validate_symbol(value: Symbol) -> Symbol:
    if value is None:
        raise InvalidHistoricalOHLCVBarError("HistoricalOHLCVBar symbol cannot be None.")
    if not isinstance(value, Symbol):
        raise InvalidHistoricalOHLCVBarError("HistoricalOHLCVBar symbol must be a Symbol value.")
    return value


def _validate_exchange_code(value: ExchangeCode) -> ExchangeCode:
    if value is None:
        raise InvalidHistoricalOHLCVBarError("HistoricalOHLCVBar exchange code cannot be None.")
    if not isinstance(value, ExchangeCode):
        raise InvalidHistoricalOHLCVBarError(
            "HistoricalOHLCVBar exchange code must be an ExchangeCode value."
        )
    return value


def _validate_price(value: Price, field_name: str, currency: object) -> Price:
    if value is None:
        raise InvalidHistoricalOHLCVBarError(f"HistoricalOHLCVBar {field_name} cannot be None.")
    if not isinstance(value, Price):
        raise InvalidHistoricalOHLCVBarError(
            f"HistoricalOHLCVBar {field_name} must be a Price value."
        )
    if value.currency != currency:
        raise InvalidHistoricalOHLCVBarError(
            f"HistoricalOHLCVBar {field_name} currency must match the listing currency."
        )
    return value


def _validate_volume(value: Quantity) -> Quantity:
    if value is None:
        raise InvalidHistoricalOHLCVBarError("HistoricalOHLCVBar volume cannot be None.")
    if not isinstance(value, Quantity):
        raise InvalidHistoricalOHLCVBarError("HistoricalOHLCVBar volume must be a Quantity value.")
    return value


def _validate_adjusted_close(value: Price | None, currency: object) -> Price | None:
    if value is None:
        return None
    return _validate_price(value, "adjusted close", currency)


@dataclass(frozen=True, slots=True)
class HistoricalOHLCVBar:
    """Immutable factual OHLCV observation for one historical interval.

    ``point_in_time`` represents the completion or end instant of the
    represented market interval: the earliest logical instant at which the
    completed OHLCV bar may participate in deterministic historical replay. It
    does not represent provider publication time, network arrival time,
    ingestion time, clearing time, or settlement time. ``timeframe`` remains
    generic; Story 6.1 initially uses daily bars, while other intervals remain
    valid.

    ``close`` is the reported raw close. ``adjusted_close``, when present, is
    an alternate financially adjusted closing value for research use and is
    never treated as the raw close.
    """

    symbol: Symbol
    exchange_code: ExchangeCode
    point_in_time: PointInTime
    timeframe: Timeframe
    open: Price
    high: Price
    low: Price
    close: Price
    volume: Quantity
    adjusted_close: Price | None = None

    def __post_init__(self) -> None:
        symbol = _validate_symbol(self.symbol)
        exchange_code = _validate_exchange_code(self.exchange_code)
        currency = self.open.currency if isinstance(self.open, Price) else None
        point_in_time = _validate_point_in_time(self.point_in_time)
        timeframe = _validate_timeframe(self.timeframe)
        if currency is None:
            raise InvalidHistoricalOHLCVBarError("HistoricalOHLCVBar open must be a Price value.")
        open_price = _validate_price(self.open, "open", currency)
        high_price = _validate_price(self.high, "high", currency)
        low_price = _validate_price(self.low, "low", currency)
        close_price = _validate_price(self.close, "close", currency)
        volume = _validate_volume(self.volume)
        adjusted_close = _validate_adjusted_close(self.adjusted_close, currency)

        if high_price < open_price or high_price < close_price or high_price < low_price:
            raise InvalidHistoricalOHLCVBarError(
                "HistoricalOHLCVBar high must be greater than or equal to open, close, and low."
            )
        if low_price > open_price or low_price > close_price or low_price > high_price:
            raise InvalidHistoricalOHLCVBarError(
                "HistoricalOHLCVBar low must be less than or equal to open, close, and high."
            )

        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "exchange_code", exchange_code)
        object.__setattr__(self, "point_in_time", point_in_time)
        object.__setattr__(self, "timeframe", timeframe)
        object.__setattr__(self, "open", open_price)
        object.__setattr__(self, "high", high_price)
        object.__setattr__(self, "low", low_price)
        object.__setattr__(self, "close", close_price)
        object.__setattr__(self, "volume", volume)
        object.__setattr__(self, "adjusted_close", adjusted_close)

    def __hash__(self) -> int:
        return hash(
            (
                self.symbol,
                self.exchange_code,
                self.point_in_time,
                self.timeframe,
                self.open,
                self.high,
                self.low,
                self.close,
                self.volume,
                self.adjusted_close,
            )
        )

    def __str__(self) -> str:
        return (
            f"{self.symbol}@{self.exchange_code} "
            f"{self.point_in_time} {self.timeframe} "
            f"O={self.open} H={self.high} L={self.low} C={self.close} V={self.volume}"
        )

    def __repr__(self) -> str:
        return (
            "HistoricalOHLCVBar("
            f"symbol={self.symbol!r}, "
            f"exchange_code={self.exchange_code!r}, "
            f"point_in_time={self.point_in_time!r}, "
            f"timeframe={self.timeframe!r}, "
            f"open={self.open!r}, "
            f"high={self.high!r}, "
            f"low={self.low!r}, "
            f"close={self.close!r}, "
            f"volume={self.volume!r}, "
            f"adjusted_close={self.adjusted_close!r}"
            ")"
        )
