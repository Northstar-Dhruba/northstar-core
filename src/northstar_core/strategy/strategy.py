"""Reference Strategy aggregate root.

Strategy is a mutable decision-policy aggregate root. Version 1.0 composes
only StrategyIdentity; Market Data, Portfolio, Trades, and Orders remain
external contexts consumed or influenced by Strategy.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.strategy.value_objects import (
    AssetAnalysis,
    Recommendation,
    RecommendationAction,
    StrategyIdentity,
)

_STRONG_BULLISH_SIGNAL = "strong bullish"
_STRONG_BEARISH_SIGNAL = "strong bearish"


class InvalidStrategyError(ValidationError):
    """Raised when a Strategy aggregate is invalid."""


def _validate_strategy_identity(value: StrategyIdentity) -> StrategyIdentity:
    if value is None:
        raise InvalidStrategyError("Strategy identity cannot be None.")
    if not isinstance(value, StrategyIdentity):
        raise InvalidStrategyError("Strategy identity must be a StrategyIdentity value.")
    return value


@dataclass(slots=True, eq=False)
class Strategy:
    """Reference Aggregate Root for the Strategy bounded context.

    Strategy owns decision policy, strategy consistency, and strategy lifecycle.
    Version 1.0 deliberately introduces no policy representation, workflow,
    execution, risk, performance, or consumed-context composition.
    """

    strategy_identity: StrategyIdentity

    def __post_init__(self) -> None:
        self.strategy_identity = _validate_strategy_identity(self.strategy_identity)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Strategy):
            return NotImplemented
        return self.strategy_identity == other.strategy_identity

    def __hash__(self) -> int:
        return hash(self.strategy_identity)

    def evaluate(self, asset_analysis: AssetAnalysis) -> Recommendation:
        """Produce the MVP recommendation for one AssetAnalysis.

        A strong bullish signal produces BUY, a strong bearish signal produces
        SELL, and conflicting or all other signal sets produce HOLD.
        """
        if asset_analysis is None:
            raise InvalidStrategyError("Strategy asset analysis cannot be None.")
        if not isinstance(asset_analysis, AssetAnalysis):
            raise InvalidStrategyError("Strategy asset analysis must be an AssetAnalysis value.")

        action = RecommendationAction(self._select_action(asset_analysis))
        return Recommendation(
            action=action,
            asset_analysis=asset_analysis,
            strategy_identity=self.strategy_identity,
            point_in_time=asset_analysis.point_in_time,
        )

    @staticmethod
    def _select_action(asset_analysis: AssetAnalysis) -> str:
        normalized_signals = {signal.casefold() for signal in asset_analysis.summarized_signals}
        has_strong_bullish_signal = _STRONG_BULLISH_SIGNAL in normalized_signals
        has_strong_bearish_signal = _STRONG_BEARISH_SIGNAL in normalized_signals

        if has_strong_bullish_signal and not has_strong_bearish_signal:
            return "BUY"
        if has_strong_bearish_signal and not has_strong_bullish_signal:
            return "SELL"
        return "HOLD"

    def __str__(self) -> str:
        return str(self.strategy_identity)

    def __repr__(self) -> str:
        return f"Strategy(strategy_identity={self.strategy_identity!r})"
