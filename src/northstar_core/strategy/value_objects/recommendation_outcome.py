"""Factual forward market movement following one Recommendation.

RecommendationOutcome measures what the market subsequently did after a
recommendation was produced. It is purely factual: it applies no BUY, SELL or
HOLD interpretation and models no order, fill, position, exposure, commission,
slippage or profit-and-loss concept. Interpreting an outcome as favourable or
unfavourable is a later research-metric responsibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import Percentage, PointInTime, Price
from northstar_core.strategy.value_objects.recommendation import Recommendation
from northstar_core.strategy.value_objects.research_horizon import ResearchHorizon

_PERCENT_SCALE = Decimal(100)
_RETURN_CONTEXT = Context(prec=28, rounding=ROUND_HALF_EVEN)


class InvalidRecommendationOutcomeError(ValidationError):
    """Raised when a RecommendationOutcome value is invalid."""


def _validate_recommendation(value: Recommendation) -> Recommendation:
    if value is None:
        raise InvalidRecommendationOutcomeError(
            "RecommendationOutcome recommendation cannot be None."
        )
    if not isinstance(value, Recommendation):
        raise InvalidRecommendationOutcomeError(
            "RecommendationOutcome recommendation must be a Recommendation value."
        )
    return value


def _validate_horizon(value: ResearchHorizon) -> ResearchHorizon:
    if value is None:
        raise InvalidRecommendationOutcomeError("RecommendationOutcome horizon cannot be None.")
    if not isinstance(value, ResearchHorizon):
        raise InvalidRecommendationOutcomeError(
            "RecommendationOutcome horizon must be a ResearchHorizon value."
        )
    return value


def _validate_price(value: Price, field_name: str) -> Price:
    if value is None:
        raise InvalidRecommendationOutcomeError(
            f"RecommendationOutcome {field_name} cannot be None."
        )
    if not isinstance(value, Price):
        raise InvalidRecommendationOutcomeError(
            f"RecommendationOutcome {field_name} must be a Price value."
        )
    return value


def _validate_evaluation_instant(value: PointInTime) -> PointInTime:
    if value is None:
        raise InvalidRecommendationOutcomeError(
            "RecommendationOutcome evaluation instant cannot be None."
        )
    if not isinstance(value, PointInTime):
        raise InvalidRecommendationOutcomeError(
            "RecommendationOutcome evaluation instant must be a PointInTime value."
        )
    return value


@dataclass(frozen=True, slots=True)
class RecommendationOutcome:
    """Immutable factual market movement measured after one Recommendation.

    ``decision_price`` is the market fact observed at the decision instant.
    ``evaluation_price`` is the corresponding fact observed at
    ``evaluation_instant``, which must fall strictly after the recommendation
    decision instant. Both prices must share one Currency so the measurement
    remains same-basis.

    The decision instant is not stored separately: it remains owned by
    ``recommendation.point_in_time``. ``forward_return`` is derived rather than
    stored so it can never disagree with the recorded prices.
    """

    recommendation: Recommendation
    horizon: ResearchHorizon
    decision_price: Price
    evaluation_instant: PointInTime
    evaluation_price: Price

    def __post_init__(self) -> None:
        recommendation = _validate_recommendation(self.recommendation)
        horizon = _validate_horizon(self.horizon)
        decision_price = _validate_price(self.decision_price, "decision price")
        evaluation_price = _validate_price(self.evaluation_price, "evaluation price")
        evaluation_instant = _validate_evaluation_instant(self.evaluation_instant)

        if evaluation_instant.compare(recommendation.point_in_time) <= 0:
            raise InvalidRecommendationOutcomeError(
                "RecommendationOutcome evaluation instant must be strictly after the "
                "recommendation decision instant."
            )
        if decision_price.currency != evaluation_price.currency:
            raise InvalidRecommendationOutcomeError(
                "RecommendationOutcome evaluation price currency must match the "
                "decision price currency."
            )
        if decision_price.amount == 0:
            raise InvalidRecommendationOutcomeError(
                "RecommendationOutcome decision price cannot be zero."
            )

        object.__setattr__(self, "recommendation", recommendation)
        object.__setattr__(self, "horizon", horizon)
        object.__setattr__(self, "decision_price", decision_price)
        object.__setattr__(self, "evaluation_instant", evaluation_instant)
        object.__setattr__(self, "evaluation_price", evaluation_price)

    @property
    def decision_instant(self) -> PointInTime:
        """Return the decision instant owned by the measured Recommendation."""
        return self.recommendation.point_in_time

    @property
    def forward_return(self) -> Percentage:
        """Return the same-basis forward market movement as a Percentage.

        A stored value of ``5`` represents ``+5%``. The movement is derived from
        the recorded Decimal price amounts and carries no action interpretation.

        The calculation runs inside an explicit local Decimal context so one
        outcome always yields one value, independent of the caller's ambient
        decimal context. The caller's context is restored unchanged. This fixes
        computational precision only; it is not a display or research-metric
        rounding policy.
        """
        with localcontext(_RETURN_CONTEXT):
            change = self.evaluation_price.amount - self.decision_price.amount
            return Percentage(change / self.decision_price.amount * _PERCENT_SCALE)

    def __str__(self) -> str:
        return (
            f"{self.recommendation.asset_analysis.listing_reference} "
            f"{self.recommendation.point_in_time} +{self.horizon} "
            f"{self.forward_return.value}%"
        )

    def __repr__(self) -> str:
        return (
            "RecommendationOutcome("
            f"recommendation={self.recommendation!r}, "
            f"horizon={self.horizon!r}, "
            f"decision_price={self.decision_price!r}, "
            f"evaluation_instant={self.evaluation_instant!r}, "
            f"evaluation_price={self.evaluation_price!r}"
            ")"
        )
