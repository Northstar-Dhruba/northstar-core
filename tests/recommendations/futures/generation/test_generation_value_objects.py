"""Tests for the generation value objects: evidence, window, unit, reward-to-risk,
rejection and proposal (ADR-018). Synthetic data only."""

from __future__ import annotations

import dataclasses
from decimal import Decimal

import pytest

from northstar_core.derivatives import ExpirationDate, QuoteValue
from northstar_core.foundation.value_objects import (
    ExchangeCode,
    PointInTime,
    Quantity,
    Symbol,
    Timeframe,
)
from northstar_core.futures import FuturesContract, FuturesProductReference
from northstar_core.recommendations.futures import (
    EntryZone,
    FuturesCandidateEvidence,
    FuturesGenerationRejection,
    FuturesRecommendationCandidate,
    FuturesRecommendationProposal,
    FuturesRecommendationSessionWindow,
    FuturesResearchDecision,
    FuturesResearchDecisionReference,
    FuturesTradeRecommendation,
    FuturesTradeRecommendationIdentity,
    GenerationRejectionReason,
    InvalidFuturesCandidateEvidenceError,
    InvalidFuturesGenerationRejectionError,
    InvalidFuturesRecommendationProposalError,
    InvalidFuturesRecommendationSessionWindowError,
    InvalidFuturesTradeRecommendationIdentityError,
    InvalidPriceMovementUnitError,
    InvalidRewardToRiskError,
    PriceMovementUnit,
    PriceTarget,
    RecommendationPolicyVersion,
    RecommendationValidity,
    RewardToRisk,
    StopLoss,
    TradeDirection,
)
from northstar_core.strategy import (
    ExplanationReason,
    FuturesAssetAnalysis,
    FuturesMarketObservationContext,
    FuturesRecommendation,
    RecommendationAction,
    StrategyIdentity,
)

_NIFTY = FuturesProductReference(Symbol("NIFTY"), ExchangeCode("NSE"))
_OCT = FuturesContract(_NIFTY, ExpirationDate("2026-10-27"))
_NOV = FuturesContract(_NIFTY, ExpirationDate("2026-11-24"))
_DAILY = Timeframe("1d")
_STRATEGY = StrategyIdentity("synthetic-directional-v1")
_SESSION = PointInTime("2026-10-07T10:00:00Z")
_ISSUED = PointInTime("2026-10-07T12:00:00Z")
_ELIGIBLE = PointInTime("2026-10-08T10:00:00Z")
_THROUGH = PointInTime("2026-10-21T10:00:00Z")
_CUTOFF = PointInTime("2026-10-27T10:00:00Z")
_SOURCE = FuturesResearchDecisionReference(_OCT, _DAILY, _SESSION, _STRATEGY)
_CLOSES = tuple(str(24000 + 20 * step) for step in range(19)) + ("24383",)


def _q(value: str) -> QuoteValue:
    return QuoteValue(Decimal(value))


def _context(
    *,
    contract: FuturesContract = _OCT,
    at: PointInTime = _SESSION,
    timeframe: Timeframe = _DAILY,
    closes: tuple[str, ...] = _CLOSES,
    latest: str | None = None,
) -> FuturesMarketObservationContext:
    latest = latest or closes[-1]
    return FuturesMarketObservationContext(
        contract=contract,
        timeframe=timeframe,
        observed_at=at,
        latest_quote=_q(latest),
        previous_close=_q(closes[-2]),
        latest_volume=Quantity(Decimal("1000")),
        session_high=_q(latest),
        session_low=_q(latest),
        recent_closes=tuple(_q(close) for close in closes),
        recent_volumes=tuple(Quantity(Decimal("1000")) for _ in closes),
    )


def _candidate(action: str = "BUY") -> FuturesRecommendationCandidate:
    return FuturesRecommendationCandidate(
        FuturesResearchDecision(
            _SOURCE,
            FuturesRecommendation(
                action=RecommendationAction(action),
                asset_analysis=FuturesAssetAnalysis(_OCT, _SESSION, ("strong bullish",)),
                strategy_identity=_STRATEGY,
                point_in_time=_SESSION,
            ),
        )
    )


_PROPOSAL_FIELDS: dict[str, object] = {
    "contract": _OCT,
    "direction": TradeDirection.LONG,
    "entry": EntryZone(_q("24378"), _q("24388")),
    "stop": StopLoss(_q("24347.75")),
    "target": PriceTarget(_q("24448.45")),
    "validity": RecommendationValidity(_ELIGIBLE, _THROUGH, _CUTOFF),
    "source": _SOURCE,
    "policy_version": RecommendationPolicyVersion("f4-synthetic-fixture-v1"),
    "issued_at": _ISSUED,
    "thesis": (ExplanationReason("Synthetic thesis"),),
    "reference_price": _q("24383"),
    "movement_unit": PriceMovementUnit(Decimal("383"), 19),
    "reward_to_risk": RewardToRisk(Decimal("60.45"), Decimal("40.25")),
}


def _proposal(**overrides: object) -> FuturesRecommendationProposal:
    return FuturesRecommendationProposal(**{**_PROPOSAL_FIELDS, **overrides})  # type: ignore[arg-type]


# -- FuturesCandidateEvidence -----------------------------------------------------------


def test_evidence_pairs_a_decision_with_its_matching_context() -> None:
    evidence = FuturesCandidateEvidence(_SOURCE, _context())

    assert evidence.source == _SOURCE
    assert evidence.context.latest_quote == _q("24383")


def test_evidence_accepts_another_spelling_of_the_same_instant() -> None:
    FuturesCandidateEvidence(_SOURCE, _context(at=PointInTime("2026-10-07T15:30:00+05:30")))


@pytest.mark.parametrize(
    "context",
    [
        _context(contract=_NOV),
        _context(at=PointInTime("2026-10-06T10:00:00Z")),
        _context(at=PointInTime("2026-10-08T10:00:00Z")),
        _context(timeframe=Timeframe("1h")),
    ],
    ids=["wrong-contract", "stale-instant", "look-ahead-instant", "wrong-timeframe"],
)
def test_evidence_contradicting_its_decision_is_an_error(
    context: FuturesMarketObservationContext,
) -> None:
    with pytest.raises(InvalidFuturesCandidateEvidenceError):
        FuturesCandidateEvidence(_SOURCE, context)


def test_evidence_for_a_non_daily_decision_is_an_error() -> None:
    hourly = FuturesResearchDecisionReference(_OCT, Timeframe("1h"), _SESSION, _STRATEGY)

    with pytest.raises(InvalidFuturesCandidateEvidenceError):
        FuturesCandidateEvidence(hourly, _context())


def test_evidence_must_end_at_its_decision_close() -> None:
    """The latest quote 24380 is inside the session range but is not the last close."""
    with pytest.raises(InvalidFuturesCandidateEvidenceError):
        FuturesCandidateEvidence(_SOURCE, _context(latest="24380"))


@pytest.mark.parametrize("source, context", [(None, _context()), (_SOURCE, None)])
def test_evidence_requires_its_types(source: object, context: object) -> None:
    with pytest.raises(InvalidFuturesCandidateEvidenceError):
        FuturesCandidateEvidence(source, context)  # type: ignore[arg-type]


# -- FuturesRecommendationSessionWindow --------------------------------------------------


def test_a_fitting_window_converts_to_f2_validity() -> None:
    window = FuturesRecommendationSessionWindow(_OCT, _ELIGIBLE, _THROUGH, _CUTOFF)

    assert window.fits_contract
    assert not window.expires_before_eligibility
    assert window.to_validity() == RecommendationValidity(_ELIGIBLE, _THROUGH, _CUTOFF)


def test_a_window_may_outlive_its_contract_but_has_no_validity() -> None:
    window = FuturesRecommendationSessionWindow(
        _OCT, _ELIGIBLE, PointInTime("2026-11-04T10:00:00Z"), _CUTOFF
    )

    assert not window.fits_contract
    with pytest.raises(InvalidFuturesRecommendationSessionWindowError):
        window.to_validity()


def test_a_window_entirely_after_the_cutoff_expires_before_eligibility() -> None:
    window = FuturesRecommendationSessionWindow(
        _OCT,
        PointInTime("2026-10-28T10:00:00Z"),
        PointInTime("2026-11-04T10:00:00Z"),
        _CUTOFF,
    )

    assert window.expires_before_eligibility


def test_a_window_ending_before_it_begins_is_an_error() -> None:
    with pytest.raises(InvalidFuturesRecommendationSessionWindowError):
        FuturesRecommendationSessionWindow(_OCT, _THROUGH, _ELIGIBLE, _CUTOFF)


@pytest.mark.parametrize("field_index", [0, 1, 2, 3])
def test_a_window_requires_its_types(field_index: int) -> None:
    values: list[object] = [_OCT, _ELIGIBLE, _THROUGH, _CUTOFF]
    values[field_index] = "2026-10-08"

    with pytest.raises(InvalidFuturesRecommendationSessionWindowError):
        FuturesRecommendationSessionWindow(*values)  # type: ignore[arg-type]


# -- PriceMovementUnit and RewardToRisk --------------------------------------------------


def test_the_movement_unit_keeps_its_exact_parts_and_displays_u() -> None:
    unit = PriceMovementUnit(Decimal("383"), 19)

    assert unit.value == Decimal("20.15789473684210526315789474")
    assert str(unit) == (
        "20.15789473684210526315789474 (rounded to 28 significant digits) over 19 changes"
    )


@pytest.mark.parametrize(
    "total, changes",
    [
        (Decimal("0"), 19),
        (Decimal("-1"), 19),
        (383, 19),
        (Decimal("383"), 0),
        (Decimal("383"), True),
    ],
)
def test_the_movement_unit_rejects_invalid_parts(total: object, changes: object) -> None:
    with pytest.raises(InvalidPriceMovementUnitError):
        PriceMovementUnit(total, changes)  # type: ignore[arg-type]


def test_reward_to_risk_compares_exactly_with_a_minimum() -> None:
    ratio = RewardToRisk(Decimal("60"), Decimal("40"))

    assert ratio.meets(Decimal("1.5"))
    assert not ratio.meets(Decimal("1.5000000000000000000000000000001"))
    assert ratio.ratio == Decimal("1.5")


@pytest.mark.parametrize(
    "reward, risk",
    [
        (Decimal("0"), Decimal("1")),
        (Decimal("1"), Decimal("0")),
        (Decimal("-1"), Decimal("1")),
        (1.5, Decimal("1")),
        (Decimal("1"), "1"),
    ],
)
def test_reward_and_risk_must_be_positive_decimals(reward: object, risk: object) -> None:
    with pytest.raises(InvalidRewardToRiskError):
        RewardToRisk(reward, risk)  # type: ignore[arg-type]


def test_reward_to_risk_minimum_must_be_a_decimal() -> None:
    with pytest.raises(InvalidRewardToRiskError):
        RewardToRisk(Decimal("1"), Decimal("1")).meets(1.5)  # type: ignore[arg-type]


# -- FuturesGenerationRejection ---------------------------------------------------------


def test_a_rejection_keeps_the_whole_candidate_and_one_reason() -> None:
    rejection = FuturesGenerationRejection(
        _candidate("SELL"), GenerationRejectionReason.SHORT_NOT_ENABLED
    )

    assert rejection.source == _SOURCE
    assert rejection.candidate.research_action == RecommendationAction("SELL")
    assert rejection.reason is GenerationRejectionReason.SHORT_NOT_ENABLED


@pytest.mark.parametrize(
    "candidate, reason",
    [(None, GenerationRejectionReason.SHORT_NOT_ENABLED), (_candidate(), "SHORT_NOT_ENABLED")],
)
def test_a_rejection_requires_its_types(candidate: object, reason: object) -> None:
    with pytest.raises(InvalidFuturesGenerationRejectionError):
        FuturesGenerationRejection(candidate, reason)  # type: ignore[arg-type]


def test_the_rejection_vocabulary_is_closed_and_ordered_by_priority() -> None:
    assert [reason.value for reason in GenerationRejectionReason] == [
        "STRATEGY_NOT_APPROVED",
        "MISSING_SESSION_WINDOW",
        "CONTRACT_EXPIRED",
        "INSUFFICIENT_CONTRACT_LIFE",
        "CONTRADICTORY_PRODUCT_DIRECTION",
        "SHORT_NOT_ENABLED",
        "NOT_NEAREST_ELIGIBLE_CONTRACT",
        "CONTRADICTS_OPEN_RECOMMENDATION",
        "DUPLICATE_OPEN_RECOMMENDATION",
        "MISSING_MARKET_EVIDENCE",
        "INSUFFICIENT_HISTORY",
        "ZERO_PRICE_MOVEMENT_UNIT",
        "DEGENERATE_ENTRY_ZONE",
        "INVALID_PRICE_ORDER",
        "INSUFFICIENT_REWARD_TO_RISK",
    ]


# -- FuturesRecommendationProposal -------------------------------------------------------


def test_a_proposal_has_no_identity_field() -> None:
    names = {field.name for field in dataclasses.fields(FuturesRecommendationProposal)}

    assert "identity" not in names
    assert {field.name for field in dataclasses.fields(FuturesTradeRecommendation)} - names == {
        "identity"
    }


def test_a_proposal_converts_with_a_caller_supplied_identity() -> None:
    recommendation = _proposal().to_recommendation(FuturesTradeRecommendationIdentity("rec-7"))

    assert recommendation.identity.identity == "rec-7"
    for name in _PROPOSAL_FIELDS:
        if hasattr(recommendation, name):
            assert getattr(recommendation, name) == _PROPOSAL_FIELDS[name]


@pytest.mark.parametrize("identity", ["rec-7", None, 7])
def test_conversion_refuses_anything_but_an_f2_identity(identity: object) -> None:
    with pytest.raises(InvalidFuturesRecommendationProposalError):
        _proposal().to_recommendation(identity)  # type: ignore[arg-type]


def test_an_empty_f2_identity_is_refused_by_f2_itself() -> None:
    with pytest.raises(InvalidFuturesTradeRecommendationIdentityError):
        FuturesTradeRecommendationIdentity("  ")


def test_a_proposal_reports_its_strategy() -> None:
    assert _proposal().strategy_identity == _STRATEGY


@pytest.mark.parametrize(
    "overrides",
    [
        {"stop": StopLoss(_q("24378"))},
        {"target": PriceTarget(_q("24388"))},
        {"direction": TradeDirection.SHORT},
        {"reward_to_risk": RewardToRisk(Decimal("60.45"), Decimal("30.25"))},
        {"source": FuturesResearchDecisionReference(_NOV, _DAILY, _SESSION, _STRATEGY)},
        {"source": FuturesResearchDecisionReference(_OCT, Timeframe("1h"), _SESSION, _STRATEGY)},
        {"issued_at": PointInTime("2026-10-07T09:00:00Z")},
        {"issued_at": _ELIGIBLE},
        {"thesis": ()},
        {"thesis": ("Synthetic thesis",)},
        {"reference_price": Decimal("24383")},
        {"movement_unit": Decimal("20")},
    ],
    ids=[
        "stop-on-zone",
        "target-on-zone",
        "wrong-direction",
        "reward-to-risk-not-from-worst-entry",
        "wrong-contract-source",
        "non-daily-source",
        "issued-before-decision",
        "issued-at-eligibility",
        "empty-thesis",
        "thesis-not-reasons",
        "reference-not-quote",
        "unit-not-unit",
    ],
)
def test_an_inconsistent_proposal_is_refused(overrides: dict[str, object]) -> None:
    with pytest.raises(InvalidFuturesRecommendationProposalError):
        _proposal(**overrides)


def test_a_proposal_is_immutable() -> None:
    proposal = _proposal()

    with pytest.raises(dataclasses.FrozenInstanceError):
        proposal.direction = TradeDirection.SHORT  # type: ignore[misc]
