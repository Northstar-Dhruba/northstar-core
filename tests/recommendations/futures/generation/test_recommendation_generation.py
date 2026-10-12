"""Tests for deterministic futures recommendation generation (ADR-018, F-4).

Synthetic data only. Every multiplier, threshold and price increment below is a
NON-PRODUCTION calibration fixture: kE 0.25, kS 1.5, kT 3, increment 0.05,
minimum reward-to-risk 1.5. None is a validated NSE tick or an approved trading
parameter, and no generated proposal here is a trading recommendation.

The selection session closes at 2026-10-07T10:00:00Z; proposals are issued at
12:00Z that day and become eligible on the next session close.

Golden closes: twenty values 24000, 24020, ..., 24360 then 24383, so the total
absolute change is 18 * 20 + 23 = 383 over N = 19 changes (U = 383/19).
"""

from __future__ import annotations

from decimal import Decimal
from itertools import permutations

import pytest

from northstar_core.derivatives import ExpirationDate, QuoteValue
from northstar_core.foundation.value_objects import (
    ExchangeCode,
    PointInTime,
    Quantity,
    Symbol,
    Timeframe,
)
from northstar_core.futures import FuturesContract, FuturesOHLCVBar, FuturesProductReference
from northstar_core.recommendations.futures import (
    EntryZone,
    FuturesCandidateEvidence,
    FuturesCandidateSelection,
    FuturesCandidateSelectionCriteria,
    FuturesRecommendationGeneration,
    FuturesRecommendationGenerationPolicy,
    FuturesRecommendationProposal,
    FuturesRecommendationSessionWindow,
    FuturesResearchDecision,
    FuturesResearchDecisionReference,
    FuturesTradeRecommendation,
    FuturesTradeRecommendationIdentity,
    FuturesTradeRecommendationLifecycle,
    GenerationRejectionReason,
    InvalidFuturesRecommendationGenerationError,
    PriceTarget,
    RecommendationPolicyVersion,
    RecommendationStatus,
    RecommendationValidity,
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

Reason = GenerationRejectionReason
LONG = TradeDirection.LONG
SHORT = TradeDirection.SHORT

_NIFTY = FuturesProductReference(Symbol("NIFTY"), ExchangeCode("NSE"))
_BANKNIFTY = FuturesProductReference(Symbol("BANKNIFTY"), ExchangeCode("NSE"))
_OCT = FuturesContract(_NIFTY, ExpirationDate("2026-10-27"))
_NOV = FuturesContract(_NIFTY, ExpirationDate("2026-11-24"))
_DEC = FuturesContract(_NIFTY, ExpirationDate("2026-12-29"))
_BANK_OCT = FuturesContract(_BANKNIFTY, ExpirationDate("2026-10-27"))
_DAILY = Timeframe("1d")
_STRATEGY = StrategyIdentity("synthetic-directional-v1")
_OTHER = StrategyIdentity("synthetic-other-v1")

_PREVIOUS = PointInTime("2026-10-06T10:00:00Z")
_SESSION = PointInTime("2026-10-07T10:00:00Z")
_ISSUED = PointInTime("2026-10-07T12:00:00Z")
_ELIGIBLE = PointInTime("2026-10-08T10:00:00Z")
_VALID_THROUGH = PointInTime("2026-10-21T10:00:00Z")
_CUTOFFS = {
    _OCT: PointInTime("2026-10-27T10:00:00Z"),
    _NOV: PointInTime("2026-11-24T10:00:00Z"),
    _DEC: PointInTime("2026-12-29T10:00:00Z"),
    _BANK_OCT: PointInTime("2026-10-27T10:00:00Z"),
}

_RISING = tuple(str(24000 + 20 * step) for step in range(19)) + ("24383",)
_FALLING = tuple(reversed(_RISING))
_FLAT = ("24000",) * 20

_CRITERIA = FuturesCandidateSelectionCriteria(_SESSION, (_NIFTY, _BANKNIFTY), (_STRATEGY, _OTHER))


def _policy(**overrides: object) -> FuturesRecommendationGenerationPolicy:
    values: dict[str, object] = {
        "version": RecommendationPolicyVersion("f4-synthetic-fixture-v1"),
        "approved_strategies": (_STRATEGY,),
        "lookback_changes": 19,
        "entry_multiplier": Decimal("0.25"),
        "stop_multiplier": Decimal("1.5"),
        "target_multiplier": Decimal("3"),
        "price_increment": Decimal("0.05"),
        "min_reward_to_risk": Decimal("1.5"),
        "short_enabled": True,
    }
    values.update(overrides)
    return FuturesRecommendationGenerationPolicy(**values)  # type: ignore[arg-type]


def _decision(
    action: str = "BUY",
    contract: FuturesContract = _OCT,
    strategy: StrategyIdentity = _STRATEGY,
) -> FuturesResearchDecision:
    signal = "strong bearish" if action == "SELL" else "strong bullish"
    return FuturesResearchDecision(
        FuturesResearchDecisionReference(contract, _DAILY, _SESSION, strategy),
        FuturesRecommendation(
            action=RecommendationAction(action),
            asset_analysis=FuturesAssetAnalysis(contract, _SESSION, (signal,)),
            strategy_identity=strategy,
            point_in_time=_SESSION,
        ),
    )


def _context(
    contract: FuturesContract,
    closes: tuple[str, ...],
    *,
    at: PointInTime = _SESSION,
    timeframe: Timeframe = _DAILY,
) -> FuturesMarketObservationContext:
    return FuturesMarketObservationContext(
        contract=contract,
        timeframe=timeframe,
        observed_at=at,
        latest_quote=QuoteValue(Decimal(closes[-1])),
        previous_close=QuoteValue(Decimal(closes[-2])),
        latest_volume=Quantity(Decimal("1000")),
        session_high=QuoteValue(Decimal(closes[-1])),
        session_low=QuoteValue(Decimal(closes[-1])),
        recent_closes=tuple(QuoteValue(Decimal(close)) for close in closes),
        recent_volumes=tuple(Quantity(Decimal("1000")) for _ in closes),
    )


def _evidence(
    decision: FuturesResearchDecision, closes: tuple[str, ...] | None = None
) -> FuturesCandidateEvidence:
    if closes is None:
        closes = _FALLING if decision.research_action.value == "SELL" else _RISING
    return FuturesCandidateEvidence(
        decision.reference, _context(decision.reference.contract, closes)
    )


def _window(
    contract: FuturesContract,
    *,
    eligible_from: PointInTime = _ELIGIBLE,
    valid_through: PointInTime = _VALID_THROUGH,
    cutoff: PointInTime | None = None,
) -> FuturesRecommendationSessionWindow:
    return FuturesRecommendationSessionWindow(
        contract, eligible_from, valid_through, cutoff or _CUTOFFS[contract]
    )


def _generate(
    *decisions: FuturesResearchDecision,
    policy: FuturesRecommendationGenerationPolicy | None = None,
    evidence: tuple[FuturesCandidateEvidence, ...] | None = None,
    windows: tuple[FuturesRecommendationSessionWindow, ...] | None = None,
    open_recommendations: tuple[FuturesTradeRecommendationLifecycle, ...] = (),
    issued_at: PointInTime = _ISSUED,
) -> FuturesRecommendationGeneration:
    selection = FuturesCandidateSelection.select(_CRITERIA, decisions)
    if evidence is None:
        evidence = tuple(_evidence(candidate.decision) for candidate in selection.candidates)
    if windows is None:
        windows = tuple(
            _window(contract) for contract in {c.contract for c in selection.candidates}
        )
    return FuturesRecommendationGeneration.generate(
        policy or _policy(), selection, evidence, windows, open_recommendations, issued_at
    )


def _reasons(generation: FuturesRecommendationGeneration) -> dict[FuturesContract, Reason]:
    return {rejection.candidate.contract: rejection.reason for rejection in generation.rejections}


def _only_proposal(generation: FuturesRecommendationGeneration) -> FuturesRecommendationProposal:
    (proposal,) = generation.proposals
    return proposal


def _only_reason(generation: FuturesRecommendationGeneration) -> Reason:
    assert generation.proposals == ()
    (rejection,) = generation.rejections
    return rejection.reason


def _open(
    direction: TradeDirection,
    contract: FuturesContract = _OCT,
    identity: str = "open-1",
) -> FuturesTradeRecommendationLifecycle:
    long = direction is LONG
    recommendation = FuturesTradeRecommendation(
        identity=FuturesTradeRecommendationIdentity(identity),
        contract=contract,
        direction=direction,
        entry=EntryZone(QuoteValue(Decimal("24300")), QuoteValue(Decimal("24310"))),
        stop=StopLoss(QuoteValue(Decimal("24250" if long else "24360"))),
        target=PriceTarget(QuoteValue(Decimal("24400" if long else "24200"))),
        validity=RecommendationValidity(_SESSION, _VALID_THROUGH, _CUTOFFS[contract]),
        source=FuturesResearchDecisionReference(contract, _DAILY, _PREVIOUS, _STRATEGY),
        policy_version=RecommendationPolicyVersion("f4-synthetic-fixture-v1"),
        issued_at=PointInTime("2026-10-06T12:00:00Z"),
        thesis=(ExplanationReason("Synthetic open recommendation"),),
    )
    return FuturesTradeRecommendationLifecycle(recommendation)


def _q(value: str) -> QuoteValue:
    return QuoteValue(Decimal(value))


# ---------------------------------------------------------------------------
# F4-D1 -- research action to direction; golden LONG and SHORT levels
# ---------------------------------------------------------------------------


def test_buy_becomes_a_long_proposal_with_the_golden_levels() -> None:
    proposal = _only_proposal(_generate(_decision("BUY")))

    assert proposal.direction is LONG
    assert proposal.contract == _OCT
    assert proposal.reference_price == _q("24383")
    assert proposal.movement_unit.total_absolute_change == Decimal("383")
    assert proposal.movement_unit.changes == 19
    assert proposal.movement_unit.value == Decimal("20.15789473684210526315789474")
    assert proposal.entry == EntryZone(_q("24378"), _q("24388"))
    assert proposal.stop == StopLoss(_q("24347.75"))
    assert proposal.target == PriceTarget(_q("24448.45"))
    assert proposal.reward_to_risk.reward == Decimal("60.45")
    assert proposal.reward_to_risk.risk == Decimal("40.25")
    assert proposal.reward_to_risk.ratio == Decimal("1.501863354037267080745341615")


def test_sell_becomes_a_mirrored_short_proposal() -> None:
    proposal = _only_proposal(_generate(_decision("SELL")))

    assert proposal.direction is SHORT
    assert proposal.reference_price == _q("24000")
    assert proposal.movement_unit.total_absolute_change == Decimal("383")
    assert proposal.entry == EntryZone(_q("23995"), _q("24005"))
    assert proposal.stop == StopLoss(_q("24035.25"))
    assert proposal.target == PriceTarget(_q("23934.55"))
    assert proposal.reward_to_risk.reward == Decimal("60.45")
    assert proposal.reward_to_risk.risk == Decimal("40.25")


def test_sell_is_rejected_when_short_is_not_enabled() -> None:
    generation = _generate(_decision("SELL"), policy=_policy(short_enabled=False))

    assert _only_reason(generation) is Reason.SHORT_NOT_ENABLED


def test_buy_is_unaffected_when_short_is_not_enabled() -> None:
    generation = _generate(_decision("BUY"), policy=_policy(short_enabled=False))

    assert _only_proposal(generation).direction is LONG


def test_the_candidates_research_action_is_kept_unchanged() -> None:
    """Generation reads BUY and SELL; it never rewrites the research decision."""
    sell = _decision("SELL")
    generation = _generate(sell)

    assert sell.research_action == RecommendationAction("SELL")
    assert "Research SELL" in _only_proposal(generation).thesis[0].rationale


@pytest.mark.parametrize("action", ["BUY", "SELL"])
def test_every_level_is_on_the_price_increment_grid(action: str) -> None:
    proposal = _only_proposal(_generate(_decision(action)))
    increment = Decimal("0.05")

    for level in (
        proposal.entry.low,
        proposal.entry.high,
        proposal.stop.price,
        proposal.target.price,
    ):
        assert level.value % increment == 0


def test_a_coarser_increment_aligns_inward_and_conservatively() -> None:
    """Increment 1: entry [24377.96.., 24388.03..] -> [24378, 24388]; stop 24347.76.. -> 24347
    (away); target 24448.47.. -> 24448 (toward). Risk 41, reward 60."""
    policy = _policy(price_increment=Decimal("1"), min_reward_to_risk=Decimal("1.4"))
    proposal = _only_proposal(_generate(_decision("BUY"), policy=policy))

    assert proposal.entry == EntryZone(_q("24378"), _q("24388"))
    assert proposal.stop == StopLoss(_q("24347"))
    assert proposal.target == PriceTarget(_q("24448"))
    assert (proposal.reward_to_risk.reward, proposal.reward_to_risk.risk) == (
        Decimal("60"),
        Decimal("41"),
    )


def test_alignment_never_improves_the_worst_entry_ratio() -> None:
    """The same setup at increment 1 has 60:41 -- below the 1.5 minimum -- not a better ratio."""
    generation = _generate(_decision("BUY"), policy=_policy(price_increment=Decimal("1")))

    assert _only_reason(generation) is Reason.INSUFFICIENT_REWARD_TO_RISK


def test_a_zero_entry_multiplier_on_a_grid_reference_gives_a_single_price_zone() -> None:
    proposal = _only_proposal(
        _generate(_decision("BUY"), policy=_policy(entry_multiplier=Decimal("0")))
    )

    assert proposal.entry == EntryZone(_q("24383"), _q("24383"))


def test_a_zero_entry_multiplier_off_the_grid_is_a_degenerate_zone() -> None:
    """24383 is not a multiple of 2: ceil gives 24384 and floor 24382."""
    generation = _generate(
        _decision("BUY"),
        policy=_policy(entry_multiplier=Decimal("0"), price_increment=Decimal("2")),
    )

    assert _only_reason(generation) is Reason.DEGENERATE_ENTRY_ZONE


def test_inward_alignment_that_empties_the_zone_is_rejected() -> None:
    """kE 0.1, increment 10: raw [24380.98.., 24385.01..] aligns to 24390 > 24380."""
    generation = _generate(
        _decision("BUY"),
        policy=_policy(entry_multiplier=Decimal("0.1"), price_increment=Decimal("10")),
    )

    assert _only_reason(generation) is Reason.DEGENERATE_ENTRY_ZONE


def test_negative_and_zero_crossing_quotations_generate_exact_levels() -> None:
    """Closes -0.95, -0.90, ..., then 0.03: U = (18 * 0.05 + 0.08) / 19 = 0.98 / 19."""
    closes = tuple(str(Decimal("-0.95") + Decimal("0.05") * step) for step in range(19)) + ("0.03",)
    decision = _decision("BUY")
    proposal = _only_proposal(
        _generate(
            decision,
            policy=_policy(
                entry_multiplier=Decimal("1"),
                stop_multiplier=Decimal("1"),
                target_multiplier=Decimal("2"),
                price_increment=Decimal("0.01"),
                min_reward_to_risk=Decimal("0.5"),
            ),
            evidence=(_evidence(decision, closes),),
        )
    )

    # U = 0.0515789..; entry [0.03 - U, 0.03 + U] = [-0.02157.., 0.08157..] -> [-0.02, 0.08]
    assert proposal.entry == EntryZone(_q("-0.02"), _q("0.08"))
    # stop floor(-0.02 - 0.05157..) = floor(-0.07157..) = -0.08 (true floor, not truncation)
    assert proposal.stop == StopLoss(_q("-0.08"))
    # target floor(0.08 + 0.10315..) = floor(0.18315..) = 0.18
    assert proposal.target == PriceTarget(_q("0.18"))


# ---------------------------------------------------------------------------
# F4-D5 -- price and risk validation
# ---------------------------------------------------------------------------


def test_reward_to_risk_exactly_at_the_minimum_is_accepted() -> None:
    """Steady +20 closes give U = 20 exactly: risk 2*5 + 30 = 40, reward 60, ratio 1.5."""
    closes = tuple(str(24000 + 20 * step) for step in range(20))
    decision = _decision("BUY")
    proposal = _only_proposal(_generate(decision, evidence=(_evidence(decision, closes),)))

    assert proposal.reward_to_risk.reward == Decimal("60")
    assert proposal.reward_to_risk.risk == Decimal("40")
    assert proposal.reward_to_risk.meets(Decimal("1.5"))


def test_reward_to_risk_one_hair_below_the_minimum_is_rejected() -> None:
    closes = tuple(str(24000 + 20 * step) for step in range(20))
    decision = _decision("BUY")
    generation = _generate(
        decision,
        policy=_policy(min_reward_to_risk=Decimal("1.5000000000000000000000000000001")),
        evidence=(_evidence(decision, closes),),
    )

    assert _only_reason(generation) is Reason.INSUFFICIENT_REWARD_TO_RISK


@pytest.mark.parametrize("action", ["BUY", "SELL"])
def test_a_minimum_above_the_worst_entry_ratio_is_rejected(action: str) -> None:
    """60.45 < 1.6 * 40.25 = 64.4."""
    generation = _generate(_decision(action), policy=_policy(min_reward_to_risk=Decimal("1.6")))

    assert _only_reason(generation) is Reason.INSUFFICIENT_REWARD_TO_RISK


@pytest.mark.parametrize("action", ["BUY", "SELL"])
def test_a_target_collapsing_onto_the_zone_is_an_invalid_price_order(action: str) -> None:
    """kT * U ~ 0.02 is less than one increment, so the target aligns onto the zone."""
    generation = _generate(_decision(action), policy=_policy(target_multiplier=Decimal("0.001")))

    assert _only_reason(generation) is Reason.INVALID_PRICE_ORDER


def test_equal_closes_have_zero_price_movement() -> None:
    decision = _decision("BUY")
    generation = _generate(decision, evidence=(_evidence(decision, _FLAT),))

    assert _only_reason(generation) is Reason.ZERO_PRICE_MOVEMENT_UNIT


def test_only_the_trailing_twenty_closes_are_read() -> None:
    """Older history beyond N + 1 closes cannot change the unit."""
    decision = _decision("BUY")
    longer = ("1", "99999") + _RISING
    proposal = _only_proposal(_generate(decision, evidence=(_evidence(decision, longer),)))

    assert proposal.movement_unit.total_absolute_change == Decimal("383")


def test_missing_evidence_is_rejected() -> None:
    generation = _generate(_decision("BUY"), evidence=())

    assert _only_reason(generation) is Reason.MISSING_MARKET_EVIDENCE


def test_generation_is_repeatable_and_equal_by_value() -> None:
    assert _generate(_decision("BUY")) == _generate(_decision("BUY"))


# ---------------------------------------------------------------------------
# Temporal boundaries and contract life
# ---------------------------------------------------------------------------


def test_issuance_exactly_at_the_session_close_is_accepted() -> None:
    proposal = _only_proposal(_generate(_decision("BUY"), issued_at=_SESSION))

    assert proposal.issued_at == _SESSION


def test_issuance_before_the_session_close_is_an_error() -> None:
    with pytest.raises(InvalidFuturesRecommendationGenerationError):
        _generate(_decision("BUY"), issued_at=PointInTime("2026-10-07T09:59:59Z"))


def test_eligibility_not_strictly_after_issuance_is_an_error() -> None:
    with pytest.raises(InvalidFuturesRecommendationGenerationError):
        _generate(_decision("BUY"), windows=(_window(_OCT, eligible_from=_ISSUED),))


def test_a_window_ending_exactly_at_the_cutoff_is_accepted() -> None:
    cutoff = _CUTOFFS[_OCT]
    proposal = _only_proposal(
        _generate(_decision("BUY"), windows=(_window(_OCT, valid_through=cutoff),))
    )

    assert proposal.validity == RecommendationValidity(_ELIGIBLE, cutoff, cutoff)
    assert proposal.validity.ends_at_contract_cutoff


def test_eligibility_exactly_at_the_cutoff_is_accepted() -> None:
    cutoff = _CUTOFFS[_OCT]
    window = _window(_OCT, eligible_from=cutoff, valid_through=cutoff)

    proposal = _only_proposal(_generate(_decision("BUY"), windows=(window,)))
    assert proposal.validity.eligible_from == cutoff


def test_a_window_one_microsecond_past_the_cutoff_is_insufficient_contract_life() -> None:
    window = _window(_OCT, valid_through=PointInTime("2026-10-27T10:00:00.000001Z"))

    assert _only_reason(_generate(_decision("BUY"), windows=(window,))) is (
        Reason.INSUFFICIENT_CONTRACT_LIFE
    )


def test_a_contract_ending_before_eligibility_is_expired() -> None:
    window = _window(
        _OCT,
        eligible_from=PointInTime("2026-10-28T10:00:00Z"),
        valid_through=PointInTime("2026-11-10T10:00:00Z"),
    )

    assert _only_reason(_generate(_decision("BUY"), windows=(window,))) is Reason.CONTRACT_EXPIRED


def test_a_missing_window_is_rejected() -> None:
    assert _only_reason(_generate(_decision("BUY"), windows=())) is Reason.MISSING_SESSION_WINDOW


def test_the_proposal_converts_to_an_f2_recommendation_with_a_caller_identity() -> None:
    proposal = _only_proposal(_generate(_decision("BUY")))

    recommendation = proposal.to_recommendation(FuturesTradeRecommendationIdentity("caller-id-1"))

    assert isinstance(recommendation, FuturesTradeRecommendation)
    assert recommendation.identity == FuturesTradeRecommendationIdentity("caller-id-1")
    assert recommendation.direction is LONG
    assert recommendation.entry == proposal.entry
    assert recommendation.issued_at == _ISSUED
    assert recommendation.source == _decision("BUY").reference
    assert FuturesTradeRecommendationLifecycle(recommendation).status is (
        RecommendationStatus.WAITING_FOR_ENTRY
    )


# ---------------------------------------------------------------------------
# F4-D2 and F4-D3 -- strategy and contract arbitration
# ---------------------------------------------------------------------------


def test_one_candidate_yields_one_proposal() -> None:
    generation = _generate(_decision("BUY"))

    assert len(generation.proposals) == 1
    assert generation.rejections == ()


def test_the_nearest_eligible_expiry_is_selected() -> None:
    generation = _generate(_decision("BUY", _NOV), _decision("BUY", _OCT), _decision("BUY", _DEC))

    assert _only_proposal(generation).contract == _OCT
    assert _reasons(generation) == {
        _NOV: Reason.NOT_NEAREST_ELIGIBLE_CONTRACT,
        _DEC: Reason.NOT_NEAREST_ELIGIBLE_CONTRACT,
    }


def test_a_nearer_contract_with_insufficient_life_is_skipped_for_the_next() -> None:
    windows = (
        _window(_OCT, valid_through=PointInTime("2026-11-04T10:00:00Z")),
        _window(_NOV, valid_through=PointInTime("2026-11-04T10:00:00Z")),
    )
    generation = _generate(_decision("BUY", _OCT), _decision("BUY", _NOV), windows=windows)

    assert _only_proposal(generation).contract == _NOV
    assert _reasons(generation) == {_OCT: Reason.INSUFFICIENT_CONTRACT_LIFE}


def test_contradictory_directions_across_expiries_reject_the_whole_product() -> None:
    generation = _generate(_decision("BUY", _OCT), _decision("SELL", _NOV))

    assert generation.proposals == ()
    assert _reasons(generation) == {
        _OCT: Reason.CONTRADICTORY_PRODUCT_DIRECTION,
        _NOV: Reason.CONTRADICTORY_PRODUCT_DIRECTION,
    }


def test_contradiction_takes_precedence_over_short_disabled() -> None:
    """A LONG is never issued against bearish research on another eligible expiry."""
    generation = _generate(
        _decision("BUY", _OCT), _decision("SELL", _NOV), policy=_policy(short_enabled=False)
    )

    assert set(_reasons(generation).values()) == {Reason.CONTRADICTORY_PRODUCT_DIRECTION}


def test_an_ineligible_contract_does_not_contradict_an_eligible_one() -> None:
    windows = (
        _window(_OCT),
        _window(_NOV, valid_through=PointInTime("2026-11-30T10:00:00Z")),
    )
    generation = _generate(_decision("BUY", _OCT), _decision("SELL", _NOV), windows=windows)

    assert _only_proposal(generation).contract == _OCT
    assert _reasons(generation) == {_NOV: Reason.INSUFFICIENT_CONTRACT_LIFE}


def test_there_is_no_fallback_to_another_expiry_after_a_price_failure() -> None:
    near, far = _decision("BUY", _OCT), _decision("BUY", _NOV)
    evidence = (_evidence(near, _FLAT), _evidence(far))
    generation = _generate(near, far, evidence=evidence)

    assert generation.proposals == ()
    assert _reasons(generation) == {
        _OCT: Reason.ZERO_PRICE_MOVEMENT_UNIT,
        _NOV: Reason.NOT_NEAREST_ELIGIBLE_CONTRACT,
    }


def test_a_strategy_outside_the_policy_is_rejected() -> None:
    generation = _generate(_decision("BUY", strategy=_OTHER))

    assert _only_reason(generation) is Reason.STRATEGY_NOT_APPROVED


def test_unapproved_strategy_research_neither_conflicts_nor_duplicates() -> None:
    """Only the approved strategy's research takes part in arbitration."""
    approved = _decision("BUY", _OCT)
    other = _decision("SELL", _OCT, strategy=_OTHER)
    generation = _generate(approved, other, evidence=(_evidence(approved),))

    assert _only_proposal(generation).source == approved.reference
    (rejection,) = generation.rejections
    assert rejection.source == other.reference
    assert rejection.reason is Reason.STRATEGY_NOT_APPROVED


def test_unrelated_products_are_arbitrated_independently() -> None:
    generation = _generate(_decision("BUY", _OCT), _decision("SELL", _BANK_OCT))

    assert {(p.contract, p.direction) for p in generation.proposals} == {
        (_OCT, LONG),
        (_BANK_OCT, SHORT),
    }
    assert generation.rejections == ()


def test_an_open_same_direction_recommendation_is_a_duplicate() -> None:
    generation = _generate(_decision("BUY"), open_recommendations=(_open(LONG),))

    assert _only_reason(generation) is Reason.DUPLICATE_OPEN_RECOMMENDATION


def test_an_open_opposite_recommendation_is_contradicted() -> None:
    generation = _generate(_decision("BUY"), open_recommendations=(_open(SHORT),))

    assert _only_reason(generation) is Reason.CONTRADICTS_OPEN_RECOMMENDATION


def test_contradiction_outranks_duplication_among_open_recommendations() -> None:
    generation = _generate(
        _decision("BUY"),
        open_recommendations=(_open(LONG, identity="a"), _open(SHORT, identity="b")),
    )

    assert _only_reason(generation) is Reason.CONTRADICTS_OPEN_RECOMMENDATION


def test_an_open_recommendation_on_another_expiry_of_the_product_blocks() -> None:
    """P-1: exclusivity is per product, not per contract."""
    generation = _generate(_decision("BUY"), open_recommendations=(_open(LONG, _NOV),))

    assert _only_reason(generation) is Reason.DUPLICATE_OPEN_RECOMMENDATION


def test_every_candidate_has_exactly_one_disposition() -> None:
    decisions = (
        _decision("BUY", _OCT),
        _decision("BUY", _NOV),
        _decision("BUY", _DEC),
        _decision("SELL", _BANK_OCT),
        _decision("BUY", _OCT, strategy=_OTHER),
    )
    generation = _generate(*decisions)

    disposed = [p.source for p in generation.proposals] + [r.source for r in generation.rejections]
    assert sorted(map(str, disposed)) == sorted(str(d.reference) for d in decisions)


def test_generation_does_not_depend_on_input_order() -> None:
    decisions = (
        _decision("BUY", _OCT),
        _decision("BUY", _NOV),
        _decision("SELL", _BANK_OCT),
        _decision("BUY", _DEC, strategy=_OTHER),
    )
    selection = FuturesCandidateSelection.select(_CRITERIA, decisions)
    evidence = tuple(_evidence(candidate.decision) for candidate in selection.candidates)
    windows = tuple(_window(contract) for contract in (_OCT, _NOV, _DEC, _BANK_OCT))
    opened = (_open(SHORT, _DEC, "x"), _open(LONG, _NOV, "y"))

    results = {
        FuturesRecommendationGeneration.generate(_policy(), selection, ev, win, op, _ISSUED)
        for ev in permutations(evidence)
        for win in permutations(windows)
        for op in permutations(opened)
    }

    assert len(results) == 1


def test_proposals_and_rejections_are_in_canonical_order() -> None:
    generation = _generate(
        _decision("BUY", _DEC),
        _decision("SELL", _BANK_OCT),
        _decision("BUY", _OCT),
        _decision("BUY", _NOV),
    )

    assert [p.contract for p in generation.proposals] == [_BANK_OCT, _OCT]
    assert [r.candidate.contract for r in generation.rejections] == [_NOV, _DEC]


def test_generation_does_not_mutate_its_selection() -> None:
    selection = FuturesCandidateSelection.select(_CRITERIA, (_decision("BUY"),))
    before = repr(selection)

    FuturesRecommendationGeneration.generate(
        _policy(), selection, (_evidence(_decision("BUY")),), (_window(_OCT),), (), _ISSUED
    )

    assert repr(selection) == before


# ---------------------------------------------------------------------------
# Input validation -- errors, never rejections
# ---------------------------------------------------------------------------


def _select(*decisions: FuturesResearchDecision) -> FuturesCandidateSelection:
    return FuturesCandidateSelection.select(_CRITERIA, decisions)


def test_evidence_for_a_decision_that_is_not_a_candidate_is_an_error() -> None:
    with pytest.raises(InvalidFuturesRecommendationGenerationError):
        _generate(_decision("BUY", _OCT), evidence=(_evidence(_decision("BUY", _NOV)),))


def test_two_different_evidence_values_for_one_decision_are_an_error() -> None:
    decision = _decision("BUY")
    evidence = (_evidence(decision), _evidence(decision, _FLAT))

    with pytest.raises(InvalidFuturesRecommendationGenerationError):
        _generate(decision, evidence=evidence)


def test_identical_repeated_inputs_are_one_value() -> None:
    decision = _decision("BUY")
    repeated = _generate(
        decision,
        evidence=(_evidence(decision), _evidence(decision)),
        windows=(_window(_OCT), _window(_OCT)),
    )

    assert repeated == _generate(decision)


def test_two_different_windows_for_one_contract_are_an_error() -> None:
    windows = (_window(_OCT), _window(_OCT, valid_through=PointInTime("2026-10-22T10:00:00Z")))

    with pytest.raises(InvalidFuturesRecommendationGenerationError):
        _generate(_decision("BUY"), windows=windows)


def test_a_window_for_a_contract_without_a_candidate_is_an_error() -> None:
    with pytest.raises(InvalidFuturesRecommendationGenerationError):
        _generate(_decision("BUY", _OCT), windows=(_window(_OCT), _window(_NOV)))


def test_a_terminal_lifecycle_does_not_block_a_new_proposal() -> None:
    lifecycle = _open(LONG)
    bar = FuturesOHLCVBar(
        contract=_OCT,
        point_in_time=_SESSION,
        timeframe=_DAILY,
        open=_q("24200"),
        high=_q("24305"),
        low=_q("24200"),
        close=_q("24305"),
        volume=Quantity(Decimal("1000")),
    )
    terminal = lifecycle.advance(bar)
    assert terminal.status is RecommendationStatus.INDETERMINATE_ENTRY

    generation = _generate(_decision("BUY"), open_recommendations=(terminal,))

    assert _only_proposal(generation).contract == _OCT


def test_an_open_recommendation_issued_after_this_issuance_is_an_error() -> None:
    """The open recommendation is issued at 11:00Z; this generation issues at 10:00Z."""
    with pytest.raises(InvalidFuturesRecommendationGenerationError):
        _generate(_decision("BUY"), issued_at=_SESSION, open_recommendations=(_later_open(),))


def _later_open() -> FuturesTradeRecommendationLifecycle:
    recommendation = _open(LONG).recommendation
    return FuturesTradeRecommendationLifecycle(
        FuturesTradeRecommendation(
            identity=recommendation.identity,
            contract=recommendation.contract,
            direction=recommendation.direction,
            entry=recommendation.entry,
            stop=recommendation.stop,
            target=recommendation.target,
            validity=RecommendationValidity(_ELIGIBLE, _VALID_THROUGH, _CUTOFFS[_OCT]),
            source=FuturesResearchDecisionReference(_OCT, _DAILY, _SESSION, _STRATEGY),
            policy_version=recommendation.policy_version,
            issued_at=PointInTime("2026-10-07T11:00:00Z"),
            thesis=recommendation.thesis,
        )
    )


def test_two_different_lifecycles_with_one_identity_are_an_error() -> None:
    with pytest.raises(InvalidFuturesRecommendationGenerationError):
        _generate(
            _decision("BUY"),
            open_recommendations=(_open(LONG, identity="same"), _open(SHORT, identity="same")),
        )


@pytest.mark.parametrize(
    "field_name, value",
    [
        ("policy", "policy"),
        ("selection", ()),
        ("evidence", [None]),
        ("windows", "windows"),
        ("open_recommendations", (None,)),
        ("issued_at", "2026-10-07T12:00:00Z"),
    ],
)
def test_wrong_argument_types_are_errors(field_name: str, value: object) -> None:
    arguments: dict[str, object] = {
        "policy": _policy(),
        "selection": _select(_decision("BUY")),
        "evidence": (),
        "windows": (),
        "open_recommendations": (),
        "issued_at": _ISSUED,
    }
    arguments[field_name] = value

    with pytest.raises(InvalidFuturesRecommendationGenerationError):
        FuturesRecommendationGeneration.generate(**arguments)  # type: ignore[arg-type]


def test_an_unrepresentable_level_is_an_error_not_a_rounded_level() -> None:
    """Thirty significant digits cannot be held exactly in the 28-digit level context."""
    decision = _decision("BUY")
    generation_policy = _policy(price_increment=Decimal("0.000000000000000000000000001"))

    with pytest.raises(InvalidFuturesRecommendationGenerationError):
        _generate(decision, policy=generation_policy)


# ---------------------------------------------------------------------------
# A stored generation validates its own structure
# ---------------------------------------------------------------------------


def test_a_generation_can_be_rebuilt_from_its_parts() -> None:
    generation = _generate(_decision("BUY", _OCT), _decision("BUY", _NOV))

    rebuilt = FuturesRecommendationGeneration(
        generation.policy, generation.issued_at, generation.proposals, generation.rejections
    )

    assert rebuilt == generation


def test_a_stored_generation_refuses_a_candidate_disposed_twice() -> None:
    generation = _generate(_decision("BUY", _OCT), _decision("BUY", _NOV))
    (rejection,) = generation.rejections

    with pytest.raises(InvalidFuturesRecommendationGenerationError):
        FuturesRecommendationGeneration(
            generation.policy,
            generation.issued_at,
            generation.proposals,
            (rejection, rejection),
        )


def test_a_stored_generation_refuses_non_canonical_order() -> None:
    generation = _generate(_decision("BUY", _OCT), _decision("SELL", _BANK_OCT))

    with pytest.raises(InvalidFuturesRecommendationGenerationError):
        FuturesRecommendationGeneration(
            generation.policy,
            generation.issued_at,
            tuple(reversed(generation.proposals)),
            generation.rejections,
        )


def test_a_stored_generation_refuses_a_proposal_from_another_policy() -> None:
    generation = _generate(_decision("BUY"))
    other_policy = _policy(version=RecommendationPolicyVersion("f4-synthetic-fixture-v2"))

    with pytest.raises(InvalidFuturesRecommendationGenerationError):
        FuturesRecommendationGeneration(
            other_policy, generation.issued_at, generation.proposals, generation.rejections
        )


def test_a_stored_generation_refuses_a_proposal_from_another_issuance() -> None:
    generation = _generate(_decision("BUY"))

    with pytest.raises(InvalidFuturesRecommendationGenerationError):
        FuturesRecommendationGeneration(
            generation.policy,
            PointInTime("2026-10-07T13:00:00Z"),
            generation.proposals,
            generation.rejections,
        )
