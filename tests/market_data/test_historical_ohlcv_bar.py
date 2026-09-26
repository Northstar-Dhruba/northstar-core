"""Contract tests for the historical OHLCV market observation."""

import pytest

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import (
    Currency,
    ExchangeCode,
    PointInTime,
    Price,
    Quantity,
    Symbol,
    Timeframe,
)
from northstar_core.market_data import (
    HistoricalOHLCVBar,
    InvalidHistoricalOHLCVBarError,
)


def _build_bar(
    symbol: Symbol | None = None,
    exchange_code: ExchangeCode | None = None,
    *,
    open_value: str = "100",
    high_value: str = "110",
    low_value: str = "95",
    close_value: str = "105",
    volume: str = "1000",
    adjusted_close: str | None = None,
) -> HistoricalOHLCVBar:
    currency = Currency("USD")
    return HistoricalOHLCVBar(
        symbol or Symbol("AAPL"),
        exchange_code or ExchangeCode("NASDAQ"),
        PointInTime("2026-09-15T00:00:00Z"),
        Timeframe("1d"),
        Price(open_value, currency),
        Price(high_value, currency),
        Price(low_value, currency),
        Price(close_value, currency),
        Quantity(volume),
        Price(adjusted_close, currency) if adjusted_close is not None else None,
    )


def test_creates_valid_historical_ohlcv_bar() -> None:
    bar = _build_bar(adjusted_close="104")

    assert bar.symbol == Symbol("AAPL")
    assert bar.exchange_code == ExchangeCode("NASDAQ")
    assert bar.timeframe == Timeframe("1d")
    assert bar.close == Price("105", Currency("USD"))
    assert bar.adjusted_close == Price("104", Currency("USD"))


def test_timeframe_remains_generic_for_future_intraday_observations() -> None:
    bar = HistoricalOHLCVBar(
        Symbol("AAPL"),
        ExchangeCode("NASDAQ"),
        PointInTime("2026-09-15T10:00:00Z"),
        Timeframe("1h"),
        Price("100", Currency("USD")),
        Price("110", Currency("USD")),
        Price("95", Currency("USD")),
        Price("105", Currency("USD")),
        Quantity("1000"),
    )

    assert bar.timeframe == Timeframe("1h")


@pytest.mark.parametrize(
    ("open_value", "high_value", "low_value", "close_value"),
    [("111", "110", "95", "105"), ("100", "110", "106", "105")],
)
def test_rejects_invalid_ohlc_relationships(
    open_value: str,
    high_value: str,
    low_value: str,
    close_value: str,
) -> None:
    with pytest.raises(InvalidHistoricalOHLCVBarError):
        _build_bar(
            open_value=open_value,
            high_value=high_value,
            low_value=low_value,
            close_value=close_value,
        )


def test_rejects_negative_volume() -> None:
    with pytest.raises(ValidationError):
        _build_bar(volume="-1")


def test_rejects_currency_mismatch() -> None:
    with pytest.raises(InvalidHistoricalOHLCVBarError, match="currency must match"):
        HistoricalOHLCVBar(
            Symbol("AAPL"),
            ExchangeCode("NASDAQ"),
            PointInTime("2026-09-15T00:00:00Z"),
            Timeframe("1d"),
            Price("100", Currency("EUR")),
            Price("110", Currency("USD")),
            Price("95", Currency("USD")),
            Price("105", Currency("USD")),
            Quantity("1000"),
        )


def test_is_immutable_equal_hashable_and_deterministically_represented() -> None:
    left = _build_bar()
    right = _build_bar()

    assert left == right
    assert hash(left) == hash(right)
    assert "HistoricalOHLCVBar" in repr(left)
    assert "O=100 USD" in str(left)
    with pytest.raises(AttributeError):
        left.close = Price("106", Currency("USD"))


def test_independently_reconstructed_listing_identity_values_compare_equal() -> None:
    left = _build_bar()
    right = _build_bar(Symbol("AAPL"), ExchangeCode("NASDAQ"))

    assert left == right
    assert hash(left) == hash(right)


def test_adjusted_close_is_optional_and_distinct_from_raw_close() -> None:
    bar = _build_bar(adjusted_close="104")

    assert bar.close != bar.adjusted_close
    assert bar.adjusted_close == Price("104", Currency("USD"))


def test_point_in_time_represents_interval_completion_for_lookahead_free_replay() -> None:
    # An arbitrary bar completed at 20:00:00Z must compare as later than an
    # earlier query instant at 14:00:00Z during deterministic replay
    completion_pit = PointInTime("2026-09-15T20:00:00Z")
    earlier_query_pit = PointInTime("2026-09-15T14:00:00Z")

    bar = HistoricalOHLCVBar(
        Symbol("AAPL"),
        ExchangeCode("NASDAQ"),
        completion_pit,
        Timeframe("1d"),
        Price("100", Currency("USD")),
        Price("110", Currency("USD")),
        Price("95", Currency("USD")),
        Price("105", Currency("USD")),
        Quantity("1000"),
    )

    # An instant prior to bar completion cannot observe the completed bar
    assert earlier_query_pit.compare(bar.point_in_time) == -1
    # At or after the completion instant, the completed bar is available
    assert completion_pit.compare(bar.point_in_time) == 0


def test_sequential_bars_are_strictly_ordered_by_completion_point_in_time() -> None:
    bar_1 = HistoricalOHLCVBar(
        Symbol("AAPL"),
        ExchangeCode("NASDAQ"),
        PointInTime("2026-09-15T10:00:00Z"),
        Timeframe("1h"),
        Price("100", Currency("USD")),
        Price("105", Currency("USD")),
        Price("98", Currency("USD")),
        Price("102", Currency("USD")),
        Quantity("500"),
    )
    bar_2 = HistoricalOHLCVBar(
        Symbol("AAPL"),
        ExchangeCode("NASDAQ"),
        PointInTime("2026-09-15T11:00:00Z"),
        Timeframe("1h"),
        Price("102", Currency("USD")),
        Price("108", Currency("USD")),
        Price("101", Currency("USD")),
        Price("107", Currency("USD")),
        Quantity("600"),
    )

    assert bar_1.point_in_time.compare(bar_2.point_in_time) == -1
    assert bar_2.point_in_time.compare(bar_1.point_in_time) == 1
