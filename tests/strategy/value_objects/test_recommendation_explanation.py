"""Contract tests for RecommendationExplanation and ExplanationReason."""

import pytest

from northstar_core.domain.value_objects import ListingReference
from northstar_core.foundation.value_objects import ExchangeCode, PointInTime, Symbol
from northstar_core.strategy import (
    AssetAnalysis,
    ExplanationReason,
    InvalidExplanationReasonError,
    InvalidRecommendationExplanationError,
    RecommendationExplanation,
    Strategy,
    StrategyIdentity,
)


def _build_recommendation():
    listing_reference = ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ"))
    analysis = AssetAnalysis(
        listing_reference, PointInTime("2026-09-14T10:00:00Z"), ("strong bullish",)
    )
    return Strategy(StrategyIdentity("test-strategy")).evaluate(analysis)


def test_reason_normalizes_text_and_supporting_signals() -> None:
    reason = ExplanationReason("  Rising demand  ", (" strong bullish ",))

    assert reason.rationale == "Rising demand"
    assert reason.supporting_signals == ("strong bullish",)


@pytest.mark.parametrize("value", [None, "", "   ", 1])
def test_reason_rejects_invalid_rationale(value: object) -> None:
    with pytest.raises(InvalidExplanationReasonError):
        ExplanationReason(value)


def test_explanation_requires_recommendation_and_reason() -> None:
    recommendation = _build_recommendation()

    with pytest.raises(InvalidRecommendationExplanationError):
        RecommendationExplanation(None, (ExplanationReason("Reason"),))
    with pytest.raises(InvalidRecommendationExplanationError):
        RecommendationExplanation(recommendation, ())


def test_explanation_is_immutable_equal_and_deterministic() -> None:
    recommendation = _build_recommendation()
    reason = ExplanationReason("Reason", ("signal",))
    left = RecommendationExplanation(recommendation, (reason,))
    right = RecommendationExplanation(recommendation, (reason,))

    assert left == right
    assert hash(left) == hash(right)
    assert str(left) == "Reason"
    assert "RecommendationExplanation" in repr(left)
    with pytest.raises(AttributeError):
        left.reasons = ()
