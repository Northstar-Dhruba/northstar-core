"""Immutable visible futures history at one replay instant.

The futures parallel of HistoricalReplaySnapshot, with two deliberate
differences.

It is bound to one contract and one timeframe. The equity snapshot may hold
bars from several listings and therefore needs symbol and exchange as secondary
ordering keys; a futures research subject is one concrete expiring contract, so
those keys collapse and every observation must agree with the snapshot's own
contract and timeframe.

It refuses unordered input rather than sorting it. The equity snapshot
normalizes observations into order, which is safe there because it may be
assembled from several series. Here a single contract at a single timeframe can
hold at most one bar per instant, so out-of-order input means the source that
produced it is wrong -- and reordering would hide that rather than report it.
This follows the same rule the daily session aggregation already applies.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime, Timeframe
from northstar_core.futures.market_data.futures_ohlcv_bar import FuturesOHLCVBar
from northstar_core.futures.value_objects.futures_contract import FuturesContract


class InvalidFuturesReplaySnapshotError(ValidationError):
    """Raised when a futures replay snapshot violates replay invariants."""


@dataclass(frozen=True, slots=True)
class FuturesReplaySnapshot:
    """Futures observations visible at one deterministic replay instant.

    A bar is visible when its completion instant is earlier than or equal to
    ``replay_instant``. Nothing later may appear: that is the whole look-ahead
    guarantee, and it is checked rather than assumed.

    A snapshot always holds at least one observation, and ``replay_instant``
    always equals the newest one's completion instant. Replay produces one
    snapshot per distinct completed observation, so a snapshot dated after its
    newest bar would describe a decision taken on no new evidence, and an empty
    snapshot would describe a decision boundary that no observation created. A
    session in which nothing traded produces no bar and therefore no snapshot;
    a history with nothing in it is an empty tuple of snapshots, not a snapshot
    of nothing.

    Observations may be sparse. A futures series has no bar for a minute or a
    session in which nothing traded, so consecutive observations need not be
    one timeframe apart and a snapshot may hold very few.
    """

    contract: FuturesContract
    timeframe: Timeframe
    replay_instant: PointInTime
    observations: tuple[FuturesOHLCVBar, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.contract, FuturesContract):
            raise InvalidFuturesReplaySnapshotError(
                "FuturesReplaySnapshot contract must be a FuturesContract value."
            )
        if not isinstance(self.timeframe, Timeframe):
            raise InvalidFuturesReplaySnapshotError(
                "FuturesReplaySnapshot timeframe must be a Timeframe value."
            )
        if not isinstance(self.replay_instant, PointInTime):
            raise InvalidFuturesReplaySnapshotError(
                "FuturesReplaySnapshot replay instant must be a PointInTime value."
            )
        if not isinstance(self.observations, tuple):
            raise InvalidFuturesReplaySnapshotError(
                "FuturesReplaySnapshot observations must be a tuple."
            )
        if not self.observations:
            raise InvalidFuturesReplaySnapshotError(
                "FuturesReplaySnapshot must hold at least one observation; a replay "
                "boundary exists only because an observation completed."
            )

        for observation in self.observations:
            if not isinstance(observation, FuturesOHLCVBar):
                raise InvalidFuturesReplaySnapshotError(
                    "FuturesReplaySnapshot observations must contain FuturesOHLCVBar values."
                )
            if observation.contract != self.contract:
                raise InvalidFuturesReplaySnapshotError(
                    f"FuturesReplaySnapshot observation for {observation.contract} "
                    f"does not belong to {self.contract}."
                )
            if observation.timeframe != self.timeframe:
                raise InvalidFuturesReplaySnapshotError(
                    f"FuturesReplaySnapshot observation timeframe {observation.timeframe} "
                    f"does not match the snapshot timeframe {self.timeframe}."
                )
            if observation.point_in_time.compare(self.replay_instant) > 0:
                raise InvalidFuturesReplaySnapshotError(
                    "FuturesReplaySnapshot cannot contain observations after the replay instant."
                )

        # Strictly increasing, compared semantically. This also rejects
        # duplicate completion instants: contract and timeframe are already
        # fixed, so two observations sharing an instant are one natural key.
        for earlier, later in zip(self.observations, self.observations[1:], strict=False):
            if earlier.point_in_time.compare(later.point_in_time) >= 0:
                raise InvalidFuturesReplaySnapshotError(
                    "FuturesReplaySnapshot observations must be strictly ordered oldest to "
                    f"newest; {earlier.point_in_time} precedes {later.point_in_time}."
                )

        # The snapshot is dated by its newest evidence, compared semantically
        # so that two spellings of one instant agree.
        if self.replay_instant.compare(self.observations[-1].point_in_time):
            raise InvalidFuturesReplaySnapshotError(
                f"FuturesReplaySnapshot replay instant {self.replay_instant} must equal its "
                f"latest observation {self.observations[-1].point_in_time}."
            )

    @property
    def latest_observation(self) -> FuturesOHLCVBar:
        """Return the newest visible observation, which always exists."""
        return self.observations[-1]

    def __str__(self) -> str:
        return (
            f"{self.contract} {self.timeframe} @ {self.replay_instant} "
            f"({len(self.observations)} observations)"
        )

    def __repr__(self) -> str:
        return (
            "FuturesReplaySnapshot("
            f"contract={self.contract!r}, "
            f"timeframe={self.timeframe!r}, "
            f"replay_instant={self.replay_instant!r}, "
            f"observations={self.observations!r}"
            ")"
        )
