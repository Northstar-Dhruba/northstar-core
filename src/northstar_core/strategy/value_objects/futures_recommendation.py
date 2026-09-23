"""Directional research view on one futures contract.

What BUY, HOLD and SELL mean here
----------------------------------
They are directional research views and nothing more. A FuturesRecommendation
is a statement about which way the analysis leans, produced so that its
subsequent accuracy can be measured.

In particular SELL does **not** mean any of the following, because none of them
exists in this domain yet:

- open a short futures position
- reduce or close a long position
- create an executable order of any kind

The distinction matters because the equity paper-trading model reads SELL as
"reduce or close a long", that model being long-only by design. For futures the
same word would naturally mean "go short", which is a different action against
a different exposure. Nothing here settles that question, and a reader must not
carry the equity reading across. When futures execution arrives, the meaning of
SELL has to be decided explicitly rather than inherited from either side.

There is correspondingly no quantity, no contract multiplier, no tick, no
margin, no exposure and no profit or loss. A recommendation carries a direction
and the analysis that produced it.

RecommendationAction is reused rather than duplicated: it already represents
exactly the three directional states, and a second enum with identical members
would be a second vocabulary to keep in agreement.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime
from northstar_core.futures import FuturesContract
from northstar_core.strategy.value_objects.futures_asset_analysis import FuturesAssetAnalysis
from northstar_core.strategy.value_objects.recommendation import RecommendationAction
from northstar_core.strategy.value_objects.strategy_identity import StrategyIdentity


class InvalidFuturesRecommendationError(ValidationError):
    """Raised when a FuturesRecommendation value is invalid."""


def _validate_action(value: RecommendationAction) -> RecommendationAction:
    if value is None:
        raise InvalidFuturesRecommendationError("FuturesRecommendation action cannot be None.")
    if not isinstance(value, RecommendationAction):
        raise InvalidFuturesRecommendationError(
            "FuturesRecommendation action must be a RecommendationAction value."
        )
    return value


def _validate_asset_analysis(value: FuturesAssetAnalysis) -> FuturesAssetAnalysis:
    if value is None:
        raise InvalidFuturesRecommendationError(
            "FuturesRecommendation asset analysis cannot be None."
        )
    if not isinstance(value, FuturesAssetAnalysis):
        raise InvalidFuturesRecommendationError(
            "FuturesRecommendation asset analysis must be a FuturesAssetAnalysis value."
        )
    return value


def _validate_strategy_identity(value: StrategyIdentity) -> StrategyIdentity:
    if value is None:
        raise InvalidFuturesRecommendationError(
            "FuturesRecommendation strategy identity cannot be None."
        )
    if not isinstance(value, StrategyIdentity):
        raise InvalidFuturesRecommendationError(
            "FuturesRecommendation strategy identity must be a StrategyIdentity value."
        )
    return value


def _validate_point_in_time(value: PointInTime) -> PointInTime:
    if value is None:
        raise InvalidFuturesRecommendationError(
            "FuturesRecommendation point-in-time context cannot be None."
        )
    if not isinstance(value, PointInTime):
        raise InvalidFuturesRecommendationError(
            "FuturesRecommendation point-in-time context must be a PointInTime value."
        )
    return value


@dataclass(frozen=True, slots=True)
class FuturesRecommendation:
    """Immutable directional research view derived from a FuturesAssetAnalysis.

    ``point_in_time`` is the decision instant. For daily futures research it is
    the completion instant of the session the decision was made on, which is
    also the earliest instant at which the decision could have been acted upon
    had any execution existed. It must equal the analysis's own instant: a view
    derived from one analysis cannot have been decided at a different moment
    than the evidence it rests on.

    The subject is one concrete expiring contract, carried by the analysis.
    """

    action: RecommendationAction
    asset_analysis: FuturesAssetAnalysis
    strategy_identity: StrategyIdentity
    point_in_time: PointInTime

    def __post_init__(self) -> None:
        object.__setattr__(self, "action", _validate_action(self.action))
        object.__setattr__(self, "asset_analysis", _validate_asset_analysis(self.asset_analysis))
        object.__setattr__(
            self, "strategy_identity", _validate_strategy_identity(self.strategy_identity)
        )
        object.__setattr__(self, "point_in_time", _validate_point_in_time(self.point_in_time))

        # A recommendation is derived from one analysis, so it cannot claim a
        # decision instant the analysis did not observe. Compared semantically:
        # two spellings of one instant are one instant.
        if self.point_in_time.compare(self.asset_analysis.point_in_time):
            raise InvalidFuturesRecommendationError(
                f"FuturesRecommendation point-in-time {self.point_in_time} must equal its "
                f"analysis point-in-time {self.asset_analysis.point_in_time}."
            )

    @property
    def contract(self) -> FuturesContract:
        """Return the contract this view is about, owned by the analysis."""
        return self.asset_analysis.contract

    def __str__(self) -> str:
        return (
            f"{self.action} {self.asset_analysis.contract} "
            f"by {self.strategy_identity} at {self.point_in_time}"
        )

    def __repr__(self) -> str:
        return (
            "FuturesRecommendation("
            f"action={self.action!r}, "
            f"asset_analysis={self.asset_analysis!r}, "
            f"strategy_identity={self.strategy_identity!r}, "
            f"point_in_time={self.point_in_time!r}"
            ")"
        )
