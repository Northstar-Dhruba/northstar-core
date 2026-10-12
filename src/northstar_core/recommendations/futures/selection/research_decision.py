"""One frozen futures research decision, as candidate selection receives it.

A decision pairs the natural key under which research was frozen -- contract,
timeframe, decision instant and strategy -- with the research assessment itself.
The two must describe the same decision; a mismatch is an invalid input, never
a rejection. The timeframe lives on the reference because the assessment does
not carry one.

Core cannot verify that the decision was frozen. Application builds it from a
stored FuturesForwardResearchRecord, whose natural key gives the reference and
whose result holds the assessment. The research action is kept exactly as the
strategy produced it: nothing here maps BUY or SELL to a trade direction.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.recommendations.futures.value_objects import (
    FuturesResearchDecisionReference,
)
from northstar_core.strategy import FuturesRecommendation, RecommendationAction


class InvalidFuturesResearchDecisionError(ValidationError):
    """Raised when a FuturesResearchDecision value is invalid."""


def _validate_reference(
    value: FuturesResearchDecisionReference,
) -> FuturesResearchDecisionReference:
    if not isinstance(value, FuturesResearchDecisionReference):
        raise InvalidFuturesResearchDecisionError(
            "FuturesResearchDecision reference must be a FuturesResearchDecisionReference value."
        )
    return value


def _validate_assessment(value: FuturesRecommendation) -> FuturesRecommendation:
    if not isinstance(value, FuturesRecommendation):
        raise InvalidFuturesResearchDecisionError(
            "FuturesResearchDecision assessment must be a FuturesRecommendation value."
        )
    return value


def _validate_agreement(
    reference: FuturesResearchDecisionReference, assessment: FuturesRecommendation
) -> None:
    if reference.contract != assessment.contract:
        raise InvalidFuturesResearchDecisionError(
            f"FuturesResearchDecision reference contract {reference.contract} does not match "
            f"the assessment's contract {assessment.contract}."
        )
    if reference.decision_instant.compare(assessment.point_in_time) != 0:
        raise InvalidFuturesResearchDecisionError(
            f"FuturesResearchDecision reference instant {reference.decision_instant} does not "
            f"match the assessment's instant {assessment.point_in_time}."
        )
    if reference.strategy_identity != assessment.strategy_identity:
        raise InvalidFuturesResearchDecisionError(
            f"FuturesResearchDecision reference strategy {reference.strategy_identity} does not "
            f"match the assessment's strategy {assessment.strategy_identity}."
        )


@dataclass(frozen=True, slots=True)
class FuturesResearchDecision:
    """Immutable frozen research decision: its natural key and its assessment."""

    reference: FuturesResearchDecisionReference
    assessment: FuturesRecommendation

    def __post_init__(self) -> None:
        reference = _validate_reference(self.reference)
        assessment = _validate_assessment(self.assessment)
        _validate_agreement(reference, assessment)

    @property
    def research_action(self) -> RecommendationAction:
        """Return the research action exactly as the strategy produced it."""
        return self.assessment.action

    def __str__(self) -> str:
        return f"{self.research_action} {self.reference}"

    def __repr__(self) -> str:
        return (
            f"FuturesResearchDecision(reference={self.reference!r}, assessment={self.assessment!r})"
        )
