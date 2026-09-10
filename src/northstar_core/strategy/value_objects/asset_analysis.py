"""Asset-specific interpreted market understanding for Strategy input."""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.domain.listing import Listing
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime


class InvalidAssetAnalysisError(ValidationError):
    """Raised when an AssetAnalysis value is invalid."""


def _validate_listing(value: Listing) -> Listing:
    if value is None:
        raise InvalidAssetAnalysisError("AssetAnalysis listing cannot be None.")
    if not isinstance(value, Listing):
        raise InvalidAssetAnalysisError("AssetAnalysis listing must be a Listing entity.")
    return value


def _validate_point_in_time(value: PointInTime) -> PointInTime:
    if value is None:
        raise InvalidAssetAnalysisError("AssetAnalysis point-in-time context cannot be None.")
    if not isinstance(value, PointInTime):
        raise InvalidAssetAnalysisError(
            "AssetAnalysis point-in-time context must be a PointInTime value."
        )
    return value


def _validate_summarized_signals(value: tuple[str, ...]) -> tuple[str, ...]:
    if value is None:
        raise InvalidAssetAnalysisError("AssetAnalysis summarized signals cannot be None.")
    if not isinstance(value, tuple):
        raise InvalidAssetAnalysisError("AssetAnalysis summarized signals must be a tuple.")

    normalized_signals: list[str] = []
    for signal in value:
        if not isinstance(signal, str):
            raise InvalidAssetAnalysisError("AssetAnalysis summarized signals must be strings.")
        normalized_signal = signal.strip()
        if not normalized_signal:
            raise InvalidAssetAnalysisError("AssetAnalysis summarized signals cannot be empty.")
        normalized_signals.append(normalized_signal)

    return tuple(normalized_signals)


@dataclass(frozen=True, slots=True)
class AssetAnalysis:
    """Immutable interpreted understanding of one Listing at one point in time.

    AssetAnalysis summarizes signals derived from Market Data without owning the
    underlying observations. It is Strategy input, not a recommendation,
    confidence assessment, risk assessment, or execution instruction.
    """

    listing: Listing
    point_in_time: PointInTime
    summarized_signals: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "listing", _validate_listing(self.listing))
        object.__setattr__(self, "point_in_time", _validate_point_in_time(self.point_in_time))
        object.__setattr__(
            self,
            "summarized_signals",
            _validate_summarized_signals(self.summarized_signals),
        )

    def __str__(self) -> str:
        signals = ", ".join(self.summarized_signals)
        return (
            f"{self.listing.instrument.symbol}@{self.listing.exchange.exchange_code} "
            f"{self.point_in_time} [{signals}]"
        )

    def __repr__(self) -> str:
        return (
            "AssetAnalysis("
            f"listing={self.listing!r}, "
            f"point_in_time={self.point_in_time!r}, "
            f"summarized_signals={self.summarized_signals!r}"
            ")"
        )
