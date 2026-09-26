"""Tests for deterministic historical replay visibility."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

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
    HistoricalReplaySnapshot,
    InvalidHistoricalReplaySnapshotError,
)


def _bar(
    timestamp: str,
    *,
    symbol: str = "AAPL",
    exchange: str = "NASDAQ",
    timeframe: str = "1d",
) -> HistoricalOHLCVBar:
    currency = Currency("USD")
    return HistoricalOHLCVBar(
        symbol=Symbol(symbol),
        exchange_code=ExchangeCode(exchange),
        point_in_time=PointInTime(timestamp),
        timeframe=Timeframe(timeframe),
        open=Price("100", currency),
        high=Price("105", currency),
        low=Price("95", currency),
        close=Price("102", currency),
        volume=Quantity("1000"),
    )


def test_replay_instant_is_canonical_and_completed_bar_is_visible() -> None:
    replay_instant = PointInTime("2026-09-15T14:00:00-06:00")
    completed_bar = _bar("2026-09-15T19:00:00Z")

    snapshot = HistoricalReplaySnapshot(replay_instant, (completed_bar,))

    assert snapshot.replay_instant.value == "2026-09-15T20:00:00Z"
    assert snapshot.observations == (completed_bar,)


def test_bar_exactly_at_replay_instant_is_visible_inclusively() -> None:
    bar = _bar("2026-09-15T20:00:00Z")

    snapshot = HistoricalReplaySnapshot(PointInTime("2026-09-15T20:00:00Z"), (bar,))

    assert snapshot.observations == (bar,)


def test_future_bar_is_rejected() -> None:
    future_bar = _bar("2026-09-15T20:00:01Z")

    with pytest.raises(
        InvalidHistoricalReplaySnapshotError,
        match="after the replay instant",
    ):
        HistoricalReplaySnapshot(PointInTime("2026-09-15T20:00:00Z"), (future_bar,))


def test_snapshot_is_immutable_and_uses_an_immutable_collection() -> None:
    bar = _bar("2026-09-15T20:00:00Z")
    snapshot = HistoricalReplaySnapshot(PointInTime("2026-09-15T20:00:00Z"), (bar,))

    assert isinstance(snapshot.observations, tuple)
    with pytest.raises(FrozenInstanceError):
        snapshot.replay_instant = PointInTime("2026-09-15T21:00:00Z")  # type: ignore[misc]


def test_multiple_observations_are_ordered_by_completion_then_identity() -> None:
    later = _bar("2026-09-15T20:00:00Z", symbol="MSFT")
    same_time_lower_symbol = _bar("2026-09-15T20:00:00Z", symbol="AAPL")
    earlier = _bar("2026-09-15T19:00:00Z", symbol="TSLA")

    snapshot = HistoricalReplaySnapshot(
        PointInTime("2026-09-15T20:00:00Z"),
        (later, same_time_lower_symbol, earlier),
    )

    assert [bar.symbol.value for bar in snapshot.observations] == ["TSLA", "AAPL", "MSFT"]


def test_duplicate_logical_observations_are_rejected() -> None:
    first = _bar("2026-09-15T20:00:00Z")
    duplicate = first

    with pytest.raises(
        InvalidHistoricalReplaySnapshotError,
        match="duplicate logical bars",
    ):
        HistoricalReplaySnapshot(
            PointInTime("2026-09-15T20:00:00Z"),
            (first, duplicate),
        )


def test_snapshot_requires_tuple_of_historical_bars() -> None:
    replay_instant = PointInTime("2026-09-15T20:00:00Z")

    with pytest.raises(InvalidHistoricalReplaySnapshotError, match="must be a tuple"):
        HistoricalReplaySnapshot(replay_instant, [_bar("2026-09-15T20:00:00Z")])  # type: ignore[arg-type]

    with pytest.raises(InvalidHistoricalReplaySnapshotError, match="must contain"):
        HistoricalReplaySnapshot(replay_instant, (object(),))  # type: ignore[arg-type]
