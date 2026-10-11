"""One actionable futures trade setup.

A FuturesTradeRecommendation states a LONG or SHORT setup on one contract: an
inclusive entry zone, a fixed stop, a single target and a validity window,
issued at a known instant on the strength of one frozen research decision and
produced by one versioned generation policy.

It is not the research assessment (FuturesRecommendation, whose BUY, SELL and
HOLD are research actions), not a target exposure, and not an order, fill or
position. It carries no quantity, contract count, margin, risk amount, price
rounding, return or profit and loss, and no status: its lifecycle is derived
from immutable events by FuturesTradeRecommendationLifecycle (ADR-017).

Every invariant is enforced at construction, so an inconsistent setup cannot
exist:

- LONG:  stop < entry.low <= entry.high < target
- SHORT: target < entry.low <= entry.high < stop
- the source decision is for this contract, on the daily timeframe;
- it is issued no earlier than its source decision, and strictly before its
  first eligible observation (``validity.eligible_from``), which in turn is no
  later than the end of its validity window;
- it carries at least one thesis reason.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime, Timeframe
from northstar_core.futures import FuturesContract
from northstar_core.recommendations.futures.value_objects.entry_zone import EntryZone
from northstar_core.recommendations.futures.value_objects.price_target import PriceTarget
from northstar_core.recommendations.futures.value_objects.recommendation_identity import (
    FuturesTradeRecommendationIdentity,
)
from northstar_core.recommendations.futures.value_objects.recommendation_policy_version import (
    RecommendationPolicyVersion,
)
from northstar_core.recommendations.futures.value_objects.recommendation_validity import (
    RecommendationValidity,
)
from northstar_core.recommendations.futures.value_objects.research_decision_reference import (
    FuturesResearchDecisionReference,
)
from northstar_core.recommendations.futures.value_objects.stop_loss import StopLoss
from northstar_core.recommendations.futures.value_objects.trade_direction import TradeDirection
from northstar_core.strategy import ExplanationReason, StrategyIdentity

# The only timeframe whose candle semantics F-2 defines.
_DAILY = Timeframe("1d")


class InvalidFuturesTradeRecommendationError(ValidationError):
    """Raised when a FuturesTradeRecommendation value is invalid."""


def _require(value: object, expected: type, field_name: str) -> None:
    if not isinstance(value, expected):
        raise InvalidFuturesTradeRecommendationError(
            f"FuturesTradeRecommendation {field_name} must be a {expected.__name__} value."
        )


def _validate_direction(value: TradeDirection) -> TradeDirection:
    if not isinstance(value, TradeDirection):
        raise InvalidFuturesTradeRecommendationError(
            "FuturesTradeRecommendation direction must be a TradeDirection value."
        )
    return value


def _validate_thesis(value: tuple[ExplanationReason, ...]) -> tuple[ExplanationReason, ...]:
    if not isinstance(value, tuple):
        raise InvalidFuturesTradeRecommendationError(
            "FuturesTradeRecommendation thesis must be a tuple."
        )
    if not value:
        raise InvalidFuturesTradeRecommendationError(
            "FuturesTradeRecommendation thesis must contain at least one ExplanationReason."
        )
    if not all(isinstance(reason, ExplanationReason) for reason in value):
        raise InvalidFuturesTradeRecommendationError(
            "FuturesTradeRecommendation thesis must contain only ExplanationReason values."
        )
    return value


def _validate_price_order(
    direction: TradeDirection, entry: EntryZone, stop: StopLoss, target: PriceTarget
) -> None:
    if direction is TradeDirection.LONG:
        if not stop.price < entry.low:
            raise InvalidFuturesTradeRecommendationError(
                "A LONG FuturesTradeRecommendation stop must be below the entry zone."
            )
        if not entry.high < target.price:
            raise InvalidFuturesTradeRecommendationError(
                "A LONG FuturesTradeRecommendation target must be above the entry zone."
            )
    else:
        if not target.price < entry.low:
            raise InvalidFuturesTradeRecommendationError(
                "A SHORT FuturesTradeRecommendation target must be below the entry zone."
            )
        if not entry.high < stop.price:
            raise InvalidFuturesTradeRecommendationError(
                "A SHORT FuturesTradeRecommendation stop must be above the entry zone."
            )


def _validate_source(source: FuturesResearchDecisionReference, contract: FuturesContract) -> None:
    if source.contract != contract:
        raise InvalidFuturesTradeRecommendationError(
            "FuturesTradeRecommendation source decision must be for the recommended contract."
        )
    if source.timeframe != _DAILY:
        raise InvalidFuturesTradeRecommendationError(
            "FuturesTradeRecommendation source decision must be on the 1d timeframe."
        )


def _validate_timing(
    source: FuturesResearchDecisionReference,
    issued_at: PointInTime,
    validity: RecommendationValidity,
) -> None:
    if issued_at.compare(source.decision_instant) < 0:
        raise InvalidFuturesTradeRecommendationError(
            "FuturesTradeRecommendation cannot be issued before its source decision."
        )
    if issued_at.compare(validity.eligible_from) >= 0:
        raise InvalidFuturesTradeRecommendationError(
            "FuturesTradeRecommendation must be issued before its first eligible observation."
        )


@dataclass(frozen=True, slots=True)
class FuturesTradeRecommendation:
    """Immutable actionable trade setup for one futures contract."""

    identity: FuturesTradeRecommendationIdentity
    contract: FuturesContract
    direction: TradeDirection
    entry: EntryZone
    stop: StopLoss
    target: PriceTarget
    validity: RecommendationValidity
    source: FuturesResearchDecisionReference
    policy_version: RecommendationPolicyVersion
    issued_at: PointInTime
    thesis: tuple[ExplanationReason, ...]

    def __post_init__(self) -> None:
        _require(self.identity, FuturesTradeRecommendationIdentity, "identity")
        _require(self.contract, FuturesContract, "contract")
        direction = _validate_direction(self.direction)
        _require(self.entry, EntryZone, "entry")
        _require(self.stop, StopLoss, "stop")
        _require(self.target, PriceTarget, "target")
        _require(self.validity, RecommendationValidity, "validity")
        _require(self.source, FuturesResearchDecisionReference, "source")
        _require(self.policy_version, RecommendationPolicyVersion, "policy version")
        _require(self.issued_at, PointInTime, "issued at")
        thesis = _validate_thesis(self.thesis)

        _validate_price_order(direction, self.entry, self.stop, self.target)
        _validate_source(self.source, self.contract)
        _validate_timing(self.source, self.issued_at, self.validity)

        object.__setattr__(self, "direction", direction)
        object.__setattr__(self, "thesis", thesis)

    @property
    def strategy_identity(self) -> StrategyIdentity:
        """Return the strategy whose research decision this setup came from."""
        return self.source.strategy_identity

    def __str__(self) -> str:
        return (
            f"{self.identity}: {self.direction} {self.contract} "
            f"entry {self.entry} stop {self.stop} target {self.target} "
            f"issued {self.issued_at} valid {self.validity.valid_through}"
        )

    def __repr__(self) -> str:
        return (
            "FuturesTradeRecommendation("
            f"identity={self.identity!r}, "
            f"contract={self.contract!r}, "
            f"direction={self.direction!r}, "
            f"entry={self.entry!r}, "
            f"stop={self.stop!r}, "
            f"target={self.target!r}, "
            f"validity={self.validity!r}, "
            f"source={self.source!r}, "
            f"policy_version={self.policy_version!r}, "
            f"issued_at={self.issued_at!r}, "
            f"thesis={self.thesis!r}"
            ")"
        )
