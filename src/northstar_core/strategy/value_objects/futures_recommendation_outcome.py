"""Factual forward market movement following one FuturesRecommendation.

The futures parallel of RecommendationOutcome. It is purely factual: it applies
no BUY, SELL or HOLD interpretation, so the same quotes over the same horizon
describe the same movement whichever way the recommendation leaned. SELL does
not negate anything here. There is no order, fill, position, exposure,
multiplier, margin or profit and loss -- this is what the market did after a
research decision, not what a strategy earned.

It differs from the equity outcome in three ways, each forced by futures data
rather than chosen.

Quotations, not prices. Both quotes are QuoteValue, which carries no currency
and may be zero or negative, so there is no currency to match and no positivity
to assume.

A return basis can be undefined. A percentage return divides by the decision
quote, and that is meaningful only when the decision quote is strictly
positive. At zero the division is undefined; below zero it is defined but
inverts: a quote rising from -10 to -5 would read as -50%. Neither is a
malformed quote -- WTI settled at -37.63 -- so the outcome records both quotes
and reports ``UNDEFINED_RETURN_BASIS`` instead of inventing a number. Only the
denominator is restricted: a positive decision quote followed by a zero or
negative evaluation quote is an ordinary, fully defined -100% or worse.

The horizon may not have arrived. The equity outcome exists only once it can be
measured, with its unavailable states held by an Application wrapper. Here one
value holds every state, so an outcome with no evaluation observation yet
reports ``INSUFFICIENT_FUTURE_OBSERVATIONS``.

The return and the reason are derived, never stored
---------------------------------------------------
Only the facts are fields: the recommendation, the horizon, the decision quote,
and the evaluation instant and quote when the horizon's observation exists. The
percentage and the unavailable reason are computed from them, so an outcome
cannot carry a percentage together with a reason, a measured return without an
evaluation quote, or an undefined basis for a positive decision quote. Those
contradictions are not rejected; they have no way to be expressed.

The decision instant is not stored: it is owned by the recommendation.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from enum import StrEnum

from northstar_core.derivatives import QuoteValue
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import Percentage, PointInTime
from northstar_core.strategy.value_objects.futures_recommendation import FuturesRecommendation
from northstar_core.strategy.value_objects.research_horizon import ResearchHorizon

_PERCENT_SCALE = Decimal(100)
_RETURN_CONTEXT = Context(prec=28, rounding=ROUND_HALF_EVEN)


class InvalidFuturesRecommendationOutcomeError(ValidationError):
    """Raised when a FuturesRecommendationOutcome value is invalid."""


class FuturesRecommendationOutcomeUnavailableReason(StrEnum):
    """Why a futures outcome carries no percentage return.

    Both describe normal research states, not failures.

    ``INSUFFICIENT_FUTURE_OBSERVATIONS``: the observation the horizon names does
    not exist, so there is no evaluation quote to measure against.

    ``UNDEFINED_RETURN_BASIS``: both quotes exist, but the decision quote is
    zero or negative, so a percentage of it is undefined or would invert.
    """

    INSUFFICIENT_FUTURE_OBSERVATIONS = "INSUFFICIENT_FUTURE_OBSERVATIONS"
    UNDEFINED_RETURN_BASIS = "UNDEFINED_RETURN_BASIS"


def _validate_recommendation(value: FuturesRecommendation) -> FuturesRecommendation:
    if value is None:
        raise InvalidFuturesRecommendationOutcomeError(
            "FuturesRecommendationOutcome recommendation cannot be None."
        )
    if not isinstance(value, FuturesRecommendation):
        raise InvalidFuturesRecommendationOutcomeError(
            "FuturesRecommendationOutcome recommendation must be a FuturesRecommendation value."
        )
    return value


def _validate_horizon(value: ResearchHorizon) -> ResearchHorizon:
    if value is None:
        raise InvalidFuturesRecommendationOutcomeError(
            "FuturesRecommendationOutcome horizon cannot be None."
        )
    if not isinstance(value, ResearchHorizon):
        raise InvalidFuturesRecommendationOutcomeError(
            "FuturesRecommendationOutcome horizon must be a ResearchHorizon value."
        )
    return value


def _validate_quote(value: QuoteValue, field_name: str) -> QuoteValue:
    if not isinstance(value, QuoteValue):
        raise InvalidFuturesRecommendationOutcomeError(
            f"FuturesRecommendationOutcome {field_name} must be a QuoteValue."
        )
    return value


def _validate_evaluation_instant(value: PointInTime) -> PointInTime:
    if not isinstance(value, PointInTime):
        raise InvalidFuturesRecommendationOutcomeError(
            "FuturesRecommendationOutcome evaluation instant must be a PointInTime value."
        )
    return value


@dataclass(frozen=True, slots=True)
class FuturesRecommendationOutcome:
    """Immutable factual market movement after one FuturesRecommendation.

    ``decision_quote`` is the market fact observed at the decision instant.
    ``evaluation_instant`` and ``evaluation_quote`` describe the observation
    the horizon names; they are both present or both absent, and when present
    the instant falls strictly after the decision instant.

    Exactly one of ``forward_return`` and ``unavailable_reason`` is present:

    ======================  ==========  ==============  ======================
    state                   evaluation  forward_return  unavailable_reason
    ======================  ==========  ==============  ======================
    measured                present     Percentage      None
    undefined return basis  present     None            UNDEFINED_RETURN_BASIS
    horizon not reached     absent      None            INSUFFICIENT_FUTURE_...
    ======================  ==========  ==============  ======================

    When the horizon has not been reached the reason is insufficiency whatever
    the decision quote's sign: there is nothing yet to measure, and the basis
    question arises only once an evaluation quote exists.
    """

    recommendation: FuturesRecommendation
    horizon: ResearchHorizon
    decision_quote: QuoteValue
    evaluation_instant: PointInTime | None = None
    evaluation_quote: QuoteValue | None = None

    def __post_init__(self) -> None:
        recommendation = _validate_recommendation(self.recommendation)
        horizon = _validate_horizon(self.horizon)
        decision_quote = _validate_quote(self.decision_quote, "decision quote")

        if (self.evaluation_instant is None) != (self.evaluation_quote is None):
            raise InvalidFuturesRecommendationOutcomeError(
                "FuturesRecommendationOutcome evaluation instant and evaluation quote "
                "must be both present or both absent."
            )
        if self.evaluation_instant is not None:
            evaluation_instant = _validate_evaluation_instant(self.evaluation_instant)
            _validate_quote(self.evaluation_quote, "evaluation quote")  # type: ignore[arg-type]
            if evaluation_instant.compare(recommendation.point_in_time) <= 0:
                raise InvalidFuturesRecommendationOutcomeError(
                    "FuturesRecommendationOutcome evaluation instant must be strictly after "
                    "the recommendation decision instant."
                )

        object.__setattr__(self, "recommendation", recommendation)
        object.__setattr__(self, "horizon", horizon)
        object.__setattr__(self, "decision_quote", decision_quote)

    @property
    def decision_instant(self) -> PointInTime:
        """Return the decision instant owned by the measured recommendation."""
        return self.recommendation.point_in_time

    @property
    def unavailable_reason(self) -> FuturesRecommendationOutcomeUnavailableReason | None:
        """Return why no percentage return exists, or None when one does."""
        if self.evaluation_quote is None:
            return FuturesRecommendationOutcomeUnavailableReason.INSUFFICIENT_FUTURE_OBSERVATIONS
        if self.decision_quote.value <= 0:
            return FuturesRecommendationOutcomeUnavailableReason.UNDEFINED_RETURN_BASIS
        return None

    @property
    def forward_return(self) -> Percentage | None:
        """Return the forward market movement as a Percentage, when defined.

        A stored value of ``5`` represents ``+5%``. It is
        ``(evaluation - decision) / decision * 100`` over the quotes' Decimal
        values and carries no action interpretation.

        The calculation runs in the same explicit context the equity outcome
        uses -- 28 digits, round-half-even -- so one outcome always yields one
        value whatever the caller's ambient context, and the caller's context is
        left unchanged. That is the arithmetic contract, not a claim that every
        representable quote divides exactly.
        """
        if self.unavailable_reason is not None:
            return None
        evaluation = self.evaluation_quote.value  # type: ignore[union-attr]
        decision = self.decision_quote.value
        with localcontext(_RETURN_CONTEXT):
            return Percentage((evaluation - decision) / decision * _PERCENT_SCALE)

    def __str__(self) -> str:
        movement = (
            f"{self.forward_return.value}%"
            if self.forward_return is not None
            else str(self.unavailable_reason)
        )
        return (
            f"{self.recommendation.contract} {self.recommendation.point_in_time} "
            f"+{self.horizon} {movement}"
        )

    def __repr__(self) -> str:
        return (
            "FuturesRecommendationOutcome("
            f"recommendation={self.recommendation!r}, "
            f"horizon={self.horizon!r}, "
            f"decision_quote={self.decision_quote!r}, "
            f"evaluation_instant={self.evaluation_instant!r}, "
            f"evaluation_quote={self.evaluation_quote!r}"
            ")"
        )
