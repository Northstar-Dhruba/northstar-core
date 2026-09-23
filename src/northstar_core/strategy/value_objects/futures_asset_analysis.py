"""Interpreted market understanding of one futures contract.

The futures parallel of AssetAnalysis, differing only where it must: the
subject is a FuturesContract rather than a ListingReference. Everything else --
the decision instant and the summarized signals -- is the same asset-agnostic
research fact, so it keeps the same shape and the same normalization rules.

AssetAnalysis is deliberately not genericized to accept either subject. Doing
so would touch every equity consumer to serve a second asset class, which is a
larger change than two small values that each say plainly what they describe.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime
from northstar_core.futures import FuturesContract


class InvalidFuturesAssetAnalysisError(ValidationError):
    """Raised when a FuturesAssetAnalysis value is invalid."""


def _validate_contract(value: FuturesContract) -> FuturesContract:
    if value is None:
        raise InvalidFuturesAssetAnalysisError("FuturesAssetAnalysis contract cannot be None.")
    if not isinstance(value, FuturesContract):
        raise InvalidFuturesAssetAnalysisError(
            "FuturesAssetAnalysis contract must be a FuturesContract value."
        )
    return value


def _validate_point_in_time(value: PointInTime) -> PointInTime:
    if value is None:
        raise InvalidFuturesAssetAnalysisError(
            "FuturesAssetAnalysis point-in-time context cannot be None."
        )
    if not isinstance(value, PointInTime):
        raise InvalidFuturesAssetAnalysisError(
            "FuturesAssetAnalysis point-in-time context must be a PointInTime value."
        )
    return value


def _validate_summarized_signals(value: tuple[str, ...]) -> tuple[str, ...]:
    if value is None:
        raise InvalidFuturesAssetAnalysisError(
            "FuturesAssetAnalysis summarized signals cannot be None."
        )
    if not isinstance(value, tuple):
        raise InvalidFuturesAssetAnalysisError(
            "FuturesAssetAnalysis summarized signals must be a tuple."
        )

    normalized_signals: list[str] = []
    for signal in value:
        if not isinstance(signal, str):
            raise InvalidFuturesAssetAnalysisError(
                "FuturesAssetAnalysis summarized signals must be strings."
            )
        normalized_signal = signal.strip()
        if not normalized_signal:
            raise InvalidFuturesAssetAnalysisError(
                "FuturesAssetAnalysis summarized signals cannot be empty."
            )
        normalized_signals.append(normalized_signal)

    return tuple(normalized_signals)


@dataclass(frozen=True, slots=True)
class FuturesAssetAnalysis:
    """Immutable interpreted understanding of one futures contract at one instant.

    This is analytical output, not execution state. It summarizes signals
    derived from observations without owning those observations, and it models
    no order, position, exposure, quantity, multiplier or margin. It is input
    to a recommendation, not an instruction.

    The subject is one concrete expiring contract. There is no continuous
    series here and no rollover: a signal derived from ES December 2026
    describes that contract and nothing else.
    """

    contract: FuturesContract
    point_in_time: PointInTime
    summarized_signals: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "contract", _validate_contract(self.contract))
        object.__setattr__(self, "point_in_time", _validate_point_in_time(self.point_in_time))
        object.__setattr__(
            self,
            "summarized_signals",
            _validate_summarized_signals(self.summarized_signals),
        )

    def __str__(self) -> str:
        signals = ", ".join(self.summarized_signals)
        return f"{self.contract} {self.point_in_time} [{signals}]"

    def __repr__(self) -> str:
        return (
            "FuturesAssetAnalysis("
            f"contract={self.contract!r}, "
            f"point_in_time={self.point_in_time!r}, "
            f"summarized_signals={self.summarized_signals!r}"
            ")"
        )
