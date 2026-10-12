"""A validated futures trade setup that has not yet been given an identity.

A FuturesRecommendationProposal holds every field of a FuturesTradeRecommendation
except its identity, together with the price and risk evidence it was generated
from: the reference close, the movement unit and the worst-entry reward and
risk. It is not published, not monitored and not a recommendation.

Core never generates an identity (F-2). ``to_recommendation(identity)`` takes a
caller-supplied FuturesTradeRecommendationIdentity -- derived deterministically
by the Application (F-5) -- and returns the F-2 recommendation unchanged. The
proposal enforces the F-2 invariants itself, so that conversion cannot fail:

- LONG:  stop < entry.low <= entry.high < target
- SHORT: target < entry.low <= entry.high < stop
- the source decision is for this contract, on the daily timeframe;
- decision instant <= issued_at < validity.eligible_from;
- at least one thesis reason;

and adds one of its own: the reward and risk are exactly those measured from
the worst entry in the zone. A reward or risk that cannot be represented exactly
in twenty-eight significant digits is refused with
InvalidFuturesRecommendationProposalError; it is never rounded. Generated
proposals are unvalidated trading-policy prototypes; nothing here claims a
trading edge or tradability on the exchange.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Inexact, Rounded

from northstar_core.derivatives import QuoteValue
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime, Timeframe
from northstar_core.futures import FuturesContract
from northstar_core.recommendations.futures.generation._price_levels import (
    fixed_point,
    worst_entry_reward_and_risk,
)
from northstar_core.recommendations.futures.generation.reward_to_risk import (
    PriceMovementUnit,
    RewardToRisk,
)
from northstar_core.recommendations.futures.value_objects import (
    EntryZone,
    FuturesResearchDecisionReference,
    FuturesTradeRecommendation,
    FuturesTradeRecommendationIdentity,
    PriceTarget,
    RecommendationPolicyVersion,
    RecommendationValidity,
    StopLoss,
    TradeDirection,
)
from northstar_core.strategy import ExplanationReason, StrategyIdentity

_DAILY = Timeframe("1d")


class InvalidFuturesRecommendationProposalError(ValidationError):
    """Raised when a FuturesRecommendationProposal value is invalid."""


def _require(value: object, expected: type, field_name: str) -> None:
    if not isinstance(value, expected):
        raise InvalidFuturesRecommendationProposalError(
            f"FuturesRecommendationProposal {field_name} must be a {expected.__name__} value."
        )


def _validate_thesis(value: tuple[ExplanationReason, ...]) -> None:
    if not isinstance(value, tuple) or not value:
        raise InvalidFuturesRecommendationProposalError(
            "FuturesRecommendationProposal thesis must be a non-empty tuple."
        )
    if not all(isinstance(reason, ExplanationReason) for reason in value):
        raise InvalidFuturesRecommendationProposalError(
            "FuturesRecommendationProposal thesis must contain only ExplanationReason values."
        )


def _validate_price_order(
    direction: TradeDirection, entry: EntryZone, stop: StopLoss, target: PriceTarget
) -> None:
    if direction is TradeDirection.LONG:
        ordered = stop.price < entry.low and entry.high < target.price
    else:
        ordered = target.price < entry.low and entry.high < stop.price
    if not ordered:
        raise InvalidFuturesRecommendationProposalError(
            f"A {direction} FuturesRecommendationProposal must keep its stop and target on "
            "opposite sides of the entry zone."
        )


def _validate_reward_to_risk(
    direction: TradeDirection,
    entry: EntryZone,
    stop: StopLoss,
    target: PriceTarget,
    reward_to_risk: RewardToRisk,
) -> None:
    try:
        _, reward, risk = worst_entry_reward_and_risk(
            direction, entry.low.value, entry.high.value, stop.price.value, target.price.value
        )
    except (Inexact, Rounded) as exc:
        raise InvalidFuturesRecommendationProposalError(
            "FuturesRecommendationProposal reward and risk cannot be represented exactly in "
            "twenty-eight significant digits."
        ) from exc
    if reward_to_risk != RewardToRisk(reward, risk):
        raise InvalidFuturesRecommendationProposalError(
            "FuturesRecommendationProposal reward to risk must be measured from the worst "
            "entry in its zone."
        )


def _validate_source_and_timing(
    source: FuturesResearchDecisionReference,
    contract: FuturesContract,
    issued_at: PointInTime,
    validity: RecommendationValidity,
) -> None:
    if source.contract != contract:
        raise InvalidFuturesRecommendationProposalError(
            "FuturesRecommendationProposal source decision must be for the proposed contract."
        )
    if source.timeframe != _DAILY:
        raise InvalidFuturesRecommendationProposalError(
            "FuturesRecommendationProposal source decision must be on the 1d timeframe."
        )
    if issued_at.compare(source.decision_instant) < 0:
        raise InvalidFuturesRecommendationProposalError(
            "FuturesRecommendationProposal cannot be issued before its source decision."
        )
    if issued_at.compare(validity.eligible_from) >= 0:
        raise InvalidFuturesRecommendationProposalError(
            "FuturesRecommendationProposal must be issued before its first eligible observation."
        )


@dataclass(frozen=True, slots=True)
class FuturesRecommendationProposal:
    """Immutable validated trade setup awaiting a caller-supplied identity."""

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
    reference_price: QuoteValue
    movement_unit: PriceMovementUnit
    reward_to_risk: RewardToRisk

    def __post_init__(self) -> None:
        _require(self.contract, FuturesContract, "contract")
        _require(self.direction, TradeDirection, "direction")
        _require(self.entry, EntryZone, "entry")
        _require(self.stop, StopLoss, "stop")
        _require(self.target, PriceTarget, "target")
        _require(self.validity, RecommendationValidity, "validity")
        _require(self.source, FuturesResearchDecisionReference, "source")
        _require(self.policy_version, RecommendationPolicyVersion, "policy version")
        _require(self.issued_at, PointInTime, "issued at")
        _validate_thesis(self.thesis)
        _require(self.reference_price, QuoteValue, "reference price")
        _require(self.movement_unit, PriceMovementUnit, "movement unit")
        _require(self.reward_to_risk, RewardToRisk, "reward to risk")

        _validate_price_order(self.direction, self.entry, self.stop, self.target)
        _validate_reward_to_risk(
            self.direction, self.entry, self.stop, self.target, self.reward_to_risk
        )
        _validate_source_and_timing(self.source, self.contract, self.issued_at, self.validity)

    @property
    def strategy_identity(self) -> StrategyIdentity:
        """Return the strategy whose research decision this setup came from."""
        return self.source.strategy_identity

    def to_recommendation(
        self, identity: FuturesTradeRecommendationIdentity
    ) -> FuturesTradeRecommendation:
        """Return the F-2 recommendation for this setup under a caller-supplied identity."""
        if not isinstance(identity, FuturesTradeRecommendationIdentity):
            raise InvalidFuturesRecommendationProposalError(
                "FuturesRecommendationProposal identity must be a "
                "FuturesTradeRecommendationIdentity value supplied by the caller."
            )
        return FuturesTradeRecommendation(
            identity=identity,
            contract=self.contract,
            direction=self.direction,
            entry=self.entry,
            stop=self.stop,
            target=self.target,
            validity=self.validity,
            source=self.source,
            policy_version=self.policy_version,
            issued_at=self.issued_at,
            thesis=self.thesis,
        )

    def __str__(self) -> str:
        """Return fixed-point text; entry bounds are bracketed so signed bounds stay readable."""
        return (
            f"proposal {self.direction} {self.contract} "
            f"entry [{fixed_point(self.entry.low.value)}, {fixed_point(self.entry.high.value)}] "
            f"stop {fixed_point(self.stop.price.value)} "
            f"target {fixed_point(self.target.price.value)} "
            f"reward:risk {self.reward_to_risk} under {self.policy_version}"
        )

    def __repr__(self) -> str:
        return (
            "FuturesRecommendationProposal("
            f"contract={self.contract!r}, "
            f"direction={self.direction!r}, "
            f"entry={self.entry!r}, "
            f"stop={self.stop!r}, "
            f"target={self.target!r}, "
            f"validity={self.validity!r}, "
            f"source={self.source!r}, "
            f"policy_version={self.policy_version!r}, "
            f"issued_at={self.issued_at!r}, "
            f"thesis={self.thesis!r}, "
            f"reference_price={self.reference_price!r}, "
            f"movement_unit={self.movement_unit!r}, "
            f"reward_to_risk={self.reward_to_risk!r}"
            ")"
        )
