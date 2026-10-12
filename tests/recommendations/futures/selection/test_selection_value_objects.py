"""Tests for the candidate selection inputs and outcomes.

FuturesResearchDecision, FuturesCandidateSelectionCriteria,
FuturesRecommendationCandidate and FuturesCandidateRejection. Synthetic NIFTY
research only.
"""

from __future__ import annotations

import dataclasses
from dataclasses import FrozenInstanceError

import pytest

from northstar_core.derivatives import ExpirationDate
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import ExchangeCode, PointInTime, Symbol, Timeframe
from northstar_core.futures import FuturesContract, FuturesProductReference
from northstar_core.recommendations.futures import (
    CandidateRejectionReason,
    FuturesCandidateRejection,
    FuturesCandidateSelectionCriteria,
    FuturesRecommendationCandidate,
    FuturesResearchDecision,
    FuturesResearchDecisionReference,
    InvalidFuturesCandidateRejectionError,
    InvalidFuturesCandidateSelectionCriteriaError,
    InvalidFuturesRecommendationCandidateError,
    InvalidFuturesResearchDecisionError,
)
from northstar_core.strategy import (
    FuturesAssetAnalysis,
    FuturesRecommendation,
    RecommendationAction,
    StrategyIdentity,
)

_NIFTY = FuturesProductReference(Symbol("NIFTY"), ExchangeCode("NSE"))
_BANKNIFTY = FuturesProductReference(Symbol("BANKNIFTY"), ExchangeCode("NSE"))
_OCT = FuturesContract(_NIFTY, ExpirationDate("2026-10-27"))
_NOV = FuturesContract(_NIFTY, ExpirationDate("2026-11-24"))
_DAILY = Timeframe("1d")
_STRATEGY = StrategyIdentity("directional-mvp-v1")
_OTHER_STRATEGY = StrategyIdentity("breakout-v2")
_AT = PointInTime("2026-10-05T10:00:00Z")


def _assessment(
    action: str = "BUY",
    *,
    contract: FuturesContract = _OCT,
    at: PointInTime = _AT,
    strategy: StrategyIdentity = _STRATEGY,
) -> FuturesRecommendation:
    return FuturesRecommendation(
        action=RecommendationAction(action),
        asset_analysis=FuturesAssetAnalysis(contract, at, ("strong bullish",)),
        strategy_identity=strategy,
        point_in_time=at,
    )


def _reference(
    *,
    contract: FuturesContract = _OCT,
    at: PointInTime = _AT,
    strategy: StrategyIdentity = _STRATEGY,
    timeframe: Timeframe = _DAILY,
) -> FuturesResearchDecisionReference:
    return FuturesResearchDecisionReference(contract, timeframe, at, strategy)


def _decision(action: str = "BUY") -> FuturesResearchDecision:
    return FuturesResearchDecision(_reference(), _assessment(action))


# ---------------------------------------------------------------------------
# FuturesResearchDecision
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("action", ["BUY", "SELL", "HOLD"])
def test_a_decision_keeps_its_research_action_unchanged(action: str) -> None:
    decision = _decision(action)

    assert decision.research_action == RecommendationAction(action)
    assert decision.assessment.action == RecommendationAction(action)


def test_the_same_instant_in_another_offset_agrees() -> None:
    reference = _reference(at=PointInTime("2026-10-05T15:30:00+05:30"))

    assert FuturesResearchDecision(reference, _assessment()).reference == reference


@pytest.mark.parametrize(
    ("reference", "message"),
    [
        (_reference(contract=_NOV), "contract"),
        (_reference(at=PointInTime("2026-10-06T10:00:00Z")), "instant"),
        (_reference(strategy=_OTHER_STRATEGY), "strategy"),
    ],
    ids=["contract", "instant", "strategy"],
)
def test_a_reference_that_disagrees_with_its_assessment_is_invalid(
    reference: FuturesResearchDecisionReference, message: str
) -> None:
    with pytest.raises(InvalidFuturesResearchDecisionError, match=message):
        FuturesResearchDecision(reference, _assessment())


@pytest.mark.parametrize(
    ("reference", "assessment", "message"),
    [
        (None, _assessment(), "FuturesResearchDecisionReference"),
        (_OCT, _assessment(), "FuturesResearchDecisionReference"),
        (_reference(), None, "FuturesRecommendation"),
        (_reference(), RecommendationAction("BUY"), "FuturesRecommendation"),
    ],
)
def test_decision_parts_require_their_domain_types(
    reference: object, assessment: object, message: str
) -> None:
    with pytest.raises(InvalidFuturesResearchDecisionError, match=message):
        FuturesResearchDecision(reference, assessment)  # type: ignore[arg-type]


def test_decisions_are_immutable_comparable_and_hashable() -> None:
    decision = _decision()

    assert decision == _decision()
    assert hash(decision) == hash(_decision())
    assert decision != _decision("SELL")
    with pytest.raises(FrozenInstanceError):
        decision.reference = _reference(contract=_NOV)  # type: ignore[misc]


def test_decision_text() -> None:
    assert str(_decision("SELL")).startswith("SELL NIFTY@NSE 2026-10-27 1d decided at")
    assert repr(_decision()).startswith("FuturesResearchDecision(reference=")


# ---------------------------------------------------------------------------
# FuturesCandidateSelectionCriteria
# ---------------------------------------------------------------------------


def _criteria(**overrides: object) -> FuturesCandidateSelectionCriteria:
    fields: dict[str, object] = {
        "session_close": _AT,
        "products": (_NIFTY,),
        "strategies": (_STRATEGY,),
    }
    fields.update(overrides)
    return FuturesCandidateSelectionCriteria(**fields)  # type: ignore[arg-type]


def test_criteria_are_canonical_whatever_the_input_order() -> None:
    first = _criteria(products=(_NIFTY, _BANKNIFTY), strategies=(_STRATEGY, _OTHER_STRATEGY))
    second = _criteria(products=(_BANKNIFTY, _NIFTY), strategies=(_OTHER_STRATEGY, _STRATEGY))

    assert first == second
    assert hash(first) == hash(second)
    assert first.products == (_BANKNIFTY, _NIFTY)
    assert first.strategies == (_OTHER_STRATEGY, _STRATEGY)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("session_close", "2026-10-05T10:00:00Z", "PointInTime"),
        ("session_close", None, "PointInTime"),
        ("products", (), "at least one product"),
        ("products", [_NIFTY], "must be a tuple"),
        ("products", (_NIFTY, _NIFTY), "cannot repeat"),
        ("products", ("NIFTY@NSE",), "FuturesProductReference"),
        ("products", (_OCT,), "FuturesProductReference"),
        ("strategies", (), "at least one strategy"),
        ("strategies", frozenset({_STRATEGY}), "must be a tuple"),
        ("strategies", (_STRATEGY, StrategyIdentity(" directional-mvp-v1 ")), "cannot repeat"),
        ("strategies", ("directional-mvp-v1",), "StrategyIdentity"),
    ],
)
def test_invalid_criteria_are_rejected(field: str, value: object, message: str) -> None:
    with pytest.raises(InvalidFuturesCandidateSelectionCriteriaError, match=message):
        _criteria(**{field: value})


def test_criteria_are_immutable_and_textual() -> None:
    criteria = _criteria()

    with pytest.raises(FrozenInstanceError):
        criteria.products = ()  # type: ignore[misc]
    assert str(criteria) == (
        "session 2026-10-05T10:00:00Z; products NIFTY@NSE; strategies directional-mvp-v1"
    )
    assert repr(criteria).startswith("FuturesCandidateSelectionCriteria(session_close=")


# ---------------------------------------------------------------------------
# FuturesRecommendationCandidate and FuturesCandidateRejection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("action", ["BUY", "SELL"])
def test_a_candidate_keeps_its_research_action_and_provenance(action: str) -> None:
    candidate = FuturesRecommendationCandidate(_decision(action))

    assert candidate.research_action == RecommendationAction(action)
    assert candidate.source == _reference()
    assert candidate.contract == _OCT
    assert candidate.strategy_identity == _STRATEGY
    assert candidate.decision.assessment.asset_analysis.summarized_signals == ("strong bullish",)


def test_a_hold_decision_can_never_be_a_candidate() -> None:
    with pytest.raises(InvalidFuturesRecommendationCandidateError, match="no direction"):
        FuturesRecommendationCandidate(_decision("HOLD"))


def test_a_candidate_has_no_direction_or_trade_fields() -> None:
    """A candidate is not a recommendation: no LONG/SHORT, levels or validity."""
    assert {field.name for field in dataclasses.fields(FuturesRecommendationCandidate)} == {
        "decision"
    }
    assert not hasattr(FuturesRecommendationCandidate(_decision()), "direction")


@pytest.mark.parametrize("value", [None, _reference(), _assessment()])
def test_a_candidate_requires_a_research_decision(value: object) -> None:
    with pytest.raises(InvalidFuturesRecommendationCandidateError, match="FuturesResearchDecision"):
        FuturesRecommendationCandidate(value)  # type: ignore[arg-type]


@pytest.mark.parametrize("reason", list(CandidateRejectionReason))
def test_a_rejection_keeps_its_decision_and_one_reason(reason: CandidateRejectionReason) -> None:
    rejection = FuturesCandidateRejection(_decision("HOLD"), reason)

    assert rejection.reason is reason
    assert rejection.decision == _decision("HOLD")


@pytest.mark.parametrize(
    ("decision", "reason", "message"),
    [
        (None, CandidateRejectionReason.STALE_DECISION, "FuturesResearchDecision"),
        (_decision(), "STALE_DECISION", "CandidateRejectionReason"),
        (_decision(), None, "CandidateRejectionReason"),
    ],
)
def test_rejection_parts_require_their_domain_types(
    decision: object, reason: object, message: str
) -> None:
    with pytest.raises(InvalidFuturesCandidateRejectionError, match=message):
        FuturesCandidateRejection(decision, reason)  # type: ignore[arg-type]


def test_the_rejection_reasons_are_closed_and_in_priority_order() -> None:
    assert [reason.value for reason in CandidateRejectionReason] == [
        "AFTER_SELECTION_SESSION",
        "STALE_DECISION",
        "UNSUPPORTED_TIMEFRAME",
        "UNAPPROVED_PRODUCT",
        "UNAPPROVED_STRATEGY",
        "NO_DIRECTIONAL_VIEW",
    ]


def test_candidate_and_rejection_text() -> None:
    candidate = FuturesRecommendationCandidate(_decision())
    rejection = FuturesCandidateRejection(
        _decision("HOLD"), CandidateRejectionReason.NO_DIRECTIONAL_VIEW
    )

    assert str(candidate).startswith("candidate BUY NIFTY@NSE")
    assert str(rejection).endswith(": NO_DIRECTIONAL_VIEW")
    assert repr(rejection).startswith("FuturesCandidateRejection(decision=")


def test_all_selection_errors_are_validation_errors() -> None:
    for error in (
        InvalidFuturesResearchDecisionError,
        InvalidFuturesCandidateSelectionCriteriaError,
        InvalidFuturesRecommendationCandidateError,
        InvalidFuturesCandidateRejectionError,
    ):
        assert issubclass(error, ValidationError)
