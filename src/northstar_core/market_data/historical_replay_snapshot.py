"""Immutable visible historical market data at one replay instant."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cmp_to_key

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime
from northstar_core.market_data.historical_ohlcv_bar import HistoricalOHLCVBar


class InvalidHistoricalReplaySnapshotError(ValidationError):
    """Raised when a historical replay snapshot violates replay invariants."""


def _compare_bars(left: HistoricalOHLCVBar, right: HistoricalOHLCVBar) -> int:
    comparison = left.point_in_time.compare(right.point_in_time)
    if comparison:
        return comparison

    left_key = (
        left.symbol.value,
        left.exchange_code.value,
        left.timeframe.value,
    )
    right_key = (
        right.symbol.value,
        right.exchange_code.value,
        right.timeframe.value,
    )
    return (left_key > right_key) - (left_key < right_key)


def _logical_identity(bar: HistoricalOHLCVBar) -> tuple[str, str, str, PointInTime]:
    return (
        bar.symbol.value,
        bar.exchange_code.value,
        bar.timeframe.value,
        bar.point_in_time,
    )


@dataclass(frozen=True, slots=True)
class HistoricalReplaySnapshot:
    """Immutable historical observations visible at one deterministic instant.

    A bar is visible when its completion instant is earlier than or equal to
    ``replay_instant``. Observations are normalized into chronological order;
    observations sharing a completion instant use symbol, exchange, and
    timeframe as deterministic secondary ordering. Duplicate logical bars are
    rejected rather than silently deduplicated.
    """

    replay_instant: PointInTime
    observations: tuple[HistoricalOHLCVBar, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.replay_instant, PointInTime):
            raise InvalidHistoricalReplaySnapshotError(
                "HistoricalReplaySnapshot replay instant must be a PointInTime value."
            )
        if not isinstance(self.observations, tuple):
            raise InvalidHistoricalReplaySnapshotError(
                "HistoricalReplaySnapshot observations must be a tuple."
            )
        if not all(isinstance(bar, HistoricalOHLCVBar) for bar in self.observations):
            raise InvalidHistoricalReplaySnapshotError(
                "HistoricalReplaySnapshot observations must contain HistoricalOHLCVBar values."
            )

        identities = {_logical_identity(bar) for bar in self.observations}
        if len(identities) != len(self.observations):
            raise InvalidHistoricalReplaySnapshotError(
                "HistoricalReplaySnapshot observations cannot contain duplicate logical bars."
            )

        for bar in self.observations:
            if bar.point_in_time.compare(self.replay_instant) > 0:
                raise InvalidHistoricalReplaySnapshotError(
                    "HistoricalReplaySnapshot cannot contain observations after the replay instant."
                )

        ordered = tuple(sorted(self.observations, key=cmp_to_key(_compare_bars)))
        object.__setattr__(self, "observations", ordered)
