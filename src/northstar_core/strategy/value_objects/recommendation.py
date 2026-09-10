"""Strategy-produced recommendation values for the current MVP.

Recommendation is implemented within the Strategy package because Strategy is
its sole producer in the MVP.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime
from northstar_core.strategy.value_objects.asset_analysis import AssetAnalysis
from northstar_core.strategy.value_objects.strategy_identity import StrategyIdentity

_ALLOWED_ACTIONS = frozenset({"BUY", "HOLD", "SELL"})


class InvalidRecommendationActionError(ValidationError):
    """Raised when a RecommendationAction value is invalid."""


class InvalidRecommendationError(ValidationError):
    """Raised when a Recommendation value is invalid."""


def _normalize_action(value: str) -> str:
    if value is None:
        raise InvalidRecommendationActionError("RecommendationAction cannot be None.")
    if not isinstance(value, str):
        raise InvalidRecommendationActionError("RecommendationAction must be a string.")

    normalized = value.strip().upper()
    if normalized not in _ALLOWED_ACTIONS:
        raise InvalidRecommendationActionError(
            "RecommendationAction must be one of: BUY, HOLD, SELL."
        )
    return normalized


def _validate_asset_analysis(value: AssetAnalysis) -> AssetAnalysis:
    if value is None:
        raise InvalidRecommendationError("Recommendation asset analysis cannot be None.")
    if not isinstance(value, AssetAnalysis):
        raise InvalidRecommendationError(
            "Recommendation asset analysis must be an AssetAnalysis value."
        )
    return value


def _validate_strategy_identity(value: StrategyIdentity) -> StrategyIdentity:
    if value is None:
        raise InvalidRecommendationError("Recommendation strategy identity cannot be None.")
    if not isinstance(value, StrategyIdentity):
        raise InvalidRecommendationError(
            "Recommendation strategy identity must be a StrategyIdentity value."
        )
    return value


def _validate_point_in_time(value: PointInTime) -> PointInTime:
    if value is None:
        raise InvalidRecommendationError("Recommendation point-in-time context cannot be None.")
    if not isinstance(value, PointInTime):
        raise InvalidRecommendationError(
            "Recommendation point-in-time context must be a PointInTime value."
        )
    return value


@dataclass(frozen=True, slots=True)
class RecommendationAction:
    """Immutable Value Object for the approved recommendation vocabulary."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _normalize_action(self.value))

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"RecommendationAction(value={self.value!r})"


@dataclass(frozen=True, slots=True)
class Recommendation:
    """Immutable advised action derived by one Strategy from an AssetAnalysis."""

    action: RecommendationAction
    asset_analysis: AssetAnalysis
    strategy_identity: StrategyIdentity
    point_in_time: PointInTime

    def __post_init__(self) -> None:
        if self.action is None:
            raise InvalidRecommendationError("Recommendation action cannot be None.")
        if not isinstance(self.action, RecommendationAction):
            raise InvalidRecommendationError(
                "Recommendation action must be a RecommendationAction value."
            )
        object.__setattr__(self, "asset_analysis", _validate_asset_analysis(self.asset_analysis))
        object.__setattr__(
            self, "strategy_identity", _validate_strategy_identity(self.strategy_identity)
        )
        object.__setattr__(self, "point_in_time", _validate_point_in_time(self.point_in_time))

    def __str__(self) -> str:
        return (
            f"{self.action} {self.asset_analysis.listing.instrument.symbol} "
            f"by {self.strategy_identity} at {self.point_in_time}"
        )

    def __repr__(self) -> str:
        return (
            "Recommendation("
            f"action={self.action!r}, "
            f"asset_analysis={self.asset_analysis!r}, "
            f"strategy_identity={self.strategy_identity!r}, "
            f"point_in_time={self.point_in_time!r}"
            ")"
        )
