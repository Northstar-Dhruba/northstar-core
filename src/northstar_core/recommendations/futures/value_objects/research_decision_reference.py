"""Reference to the frozen research decision a trade recommendation came from.

The reference is exactly the natural key under which a futures research
decision is frozen: contract, timeframe, decision instant and strategy. It
points at the decision without carrying it, so a recommendation never embeds or
re-interprets the research assessment, and research semantics stay with
FuturesRecommendation in the Strategy context.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime, Timeframe
from northstar_core.futures import FuturesContract
from northstar_core.strategy import StrategyIdentity


class InvalidFuturesResearchDecisionReferenceError(ValidationError):
    """Raised when a FuturesResearchDecisionReference value is invalid."""


def _validate_contract(value: FuturesContract) -> FuturesContract:
    if not isinstance(value, FuturesContract):
        raise InvalidFuturesResearchDecisionReferenceError(
            "FuturesResearchDecisionReference contract must be a FuturesContract value."
        )
    return value


def _validate_timeframe(value: Timeframe) -> Timeframe:
    if not isinstance(value, Timeframe):
        raise InvalidFuturesResearchDecisionReferenceError(
            "FuturesResearchDecisionReference timeframe must be a Timeframe value."
        )
    return value


def _validate_decision_instant(value: PointInTime) -> PointInTime:
    if not isinstance(value, PointInTime):
        raise InvalidFuturesResearchDecisionReferenceError(
            "FuturesResearchDecisionReference decision instant must be a PointInTime value."
        )
    return value


def _validate_strategy_identity(value: StrategyIdentity) -> StrategyIdentity:
    if not isinstance(value, StrategyIdentity):
        raise InvalidFuturesResearchDecisionReferenceError(
            "FuturesResearchDecisionReference strategy identity must be a StrategyIdentity value."
        )
    return value


@dataclass(frozen=True, slots=True)
class FuturesResearchDecisionReference:
    """Immutable natural key of one frozen futures research decision."""

    contract: FuturesContract
    timeframe: Timeframe
    decision_instant: PointInTime
    strategy_identity: StrategyIdentity

    def __post_init__(self) -> None:
        object.__setattr__(self, "contract", _validate_contract(self.contract))
        object.__setattr__(self, "timeframe", _validate_timeframe(self.timeframe))
        object.__setattr__(
            self, "decision_instant", _validate_decision_instant(self.decision_instant)
        )
        object.__setattr__(
            self, "strategy_identity", _validate_strategy_identity(self.strategy_identity)
        )

    @property
    def natural_key(self) -> tuple[FuturesContract, Timeframe, PointInTime, StrategyIdentity]:
        """Return the key under which the referenced decision is frozen."""
        return (self.contract, self.timeframe, self.decision_instant, self.strategy_identity)

    def __str__(self) -> str:
        return (
            f"{self.contract} {self.timeframe} decided at {self.decision_instant} "
            f"by {self.strategy_identity}"
        )

    def __repr__(self) -> str:
        return (
            "FuturesResearchDecisionReference("
            f"contract={self.contract!r}, "
            f"timeframe={self.timeframe!r}, "
            f"decision_instant={self.decision_instant!r}, "
            f"strategy_identity={self.strategy_identity!r}"
            ")"
        )
