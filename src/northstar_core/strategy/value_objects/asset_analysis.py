"""Asset-specific interpreted market understanding for Strategy input."""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.domain.value_objects import ListingReference
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime


class InvalidAssetAnalysisError(ValidationError):
    """Raised when an AssetAnalysis value is invalid."""


def _validate_listing_reference(value: ListingReference) -> ListingReference:
    if value is None:
        raise InvalidAssetAnalysisError("AssetAnalysis listing reference cannot be None.")
    if not isinstance(value, ListingReference):
        raise InvalidAssetAnalysisError(
            "AssetAnalysis listing reference must be a ListingReference value."
        )
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
    """Immutable interpreted understanding of one listed asset at one point in time.

    AssetAnalysis summarizes signals derived from Market Data without owning the
    underlying observations. It is Strategy input, not a recommendation,
    confidence assessment, risk assessment, or execution instruction.
    """

    listing_reference: ListingReference
    point_in_time: PointInTime
    summarized_signals: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "listing_reference", _validate_listing_reference(self.listing_reference)
        )
        object.__setattr__(self, "point_in_time", _validate_point_in_time(self.point_in_time))
        object.__setattr__(
            self,
            "summarized_signals",
            _validate_summarized_signals(self.summarized_signals),
        )

    def __str__(self) -> str:
        signals = ", ".join(self.summarized_signals)
        return f"{self.listing_reference} {self.point_in_time} [{signals}]"

    def __repr__(self) -> str:
        return (
            "AssetAnalysis("
            f"listing_reference={self.listing_reference!r}, "
            f"point_in_time={self.point_in_time!r}, "
            f"summarized_signals={self.summarized_signals!r}"
            ")"
        )
