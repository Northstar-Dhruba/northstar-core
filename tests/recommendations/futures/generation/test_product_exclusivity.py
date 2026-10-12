"""Tests for one open recommendation per futures product (ADR-018, P-1).

Across every expiry of one product, at most one non-terminal recommendation may
exist. A new candidate is rejected DUPLICATE_OPEN_RECOMMENDATION when an open
recommendation on the product has its direction, and
CONTRADICTS_OPEN_RECOMMENDATION when one has the other. Terminal lifecycles
block nothing. Synthetic data only; the multipliers and increment are
non-production calibration fixtures.

Open recommendations below were decided 2026-09-28 and issued that day; the new
research session closes 2026-10-07.
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
    CoverageDeficiency,
    EntryZone,
    FuturesCandidateEvidence,
    FuturesCandidateSelection,
    FuturesCandidateSelectionCriteria,
    FuturesRecommendationGeneration,
    FuturesRecommendationGenerationPolicy,
    FuturesRecommendationSessionWindow,
    FuturesResearchDecision,
    FuturesResearchDecisionReference,
    FuturesTradeRecommendation,
    FuturesTradeRecommendationIdentity,
    FuturesTradeRecommendationLifecycle,
    GenerationRejectionReason,
    InvalidFuturesRecommendationGenerationError,
    ObservationCoverage,
    PriceTarget,
    RecommendationPolicyVersion,
    RecommendationStatus,
    RecommendationValidity,
    StopLoss,
    TimeExpiryEvidence,
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
Status = RecommendationStatus
LONG = TradeDirection.LONG
SHORT = TradeDirection.SHORT

_NIFTY = FuturesProductReference(Symbol("NIFTY"), ExchangeCode("NSE"))
_BANKNIFTY = FuturesProductReference(Symbol("BANKNIFTY"), ExchangeCode("NSE"))
_OCT = FuturesContract(_NIFTY, ExpirationDate("2026-10-27"))
_NOV = FuturesContract(_NIFTY, ExpirationDate("2026-11-24"))
_DEC = FuturesContract(_NIFTY, ExpirationDate("2026-12-29"))
_BANK_OCT = FuturesContract(_BANKNIFTY, ExpirationDate("2026-10-27"))
_CUTOFFS = {
    _OCT: PointInTime("2026-10-27T10:00:00Z"),
    _NOV: PointInTime("2026-11-24T10:00:00Z"),
    _DEC: PointInTime("2026-12-29T10:00:00Z"),
    _BANK_OCT: PointInTime("2026-10-27T10:00:00Z"),
}
_DAILY = Timeframe("1d")
_STRATEGY = StrategyIdentity("synthetic-directional-v1")
_VERSION = RecommendationPolicyVersion("f4-synthetic-fixture-v1")

_OPEN_DECIDED = PointInTime("2026-09-28T10:00:00Z")
_OPEN_ISSUED = PointInTime("2026-09-28T12:00:00Z")
_OPEN_ELIGIBLE = PointInTime("2026-09-29T10:00:00Z")
_OPEN_SHORT_VALIDITY_END = PointInTime("2026-10-02T10:00:00Z")
_SESSION = PointInTime("2026-10-07T10:00:00Z")
_ISSUED = PointInTime("2026-10-07T12:00:00Z")
_ELIGIBLE = PointInTime("2026-10-08T10:00:00Z")
_VALID_THROUGH = PointInTime("2026-10-21T10:00:00Z")

_RISING = tuple(str(24000 + 20 * step) for step in range(19)) + ("24383",)
_FALLING = tuple(reversed(_RISING))

_POLICY = FuturesRecommendationGenerationPolicy(
    version=_VERSION,
    approved_strategies=(_STRATEGY,),
    lookback_changes=19,
    entry_multiplier=Decimal("0.25"),
    stop_multiplier=Decimal("1.5"),
    target_multiplier=Decimal("3"),
    price_increment=Decimal("0.05"),
    min_reward_to_risk=Decimal("1.5"),
    short_enabled=True,
)
_CRITERIA = FuturesCandidateSelectionCriteria(_SESSION, (_NIFTY, _BANKNIFTY), (_STRATEGY,))


def _q(value: str) -> QuoteValue:
    return QuoteValue(Decimal(value))


# -- new research ----------------------------------------------------------------------


def _decision(direction: TradeDirection, contract: FuturesContract) -> FuturesResearchDecision:
    action = "BUY" if direction is LONG else "SELL"
    return FuturesResearchDecision(
        FuturesResearchDecisionReference(contract, _DAILY, _SESSION, _STRATEGY),
        FuturesRecommendation(
            action=RecommendationAction(action),
            asset_analysis=FuturesAssetAnalysis(contract, _SESSION, ("synthetic",)),
            strategy_identity=_STRATEGY,
            point_in_time=_SESSION,
        ),
    )


def _evidence(decision: FuturesResearchDecision) -> FuturesCandidateEvidence:
    closes = _FALLING if decision.research_action.value == "SELL" else _RISING
    quotes = tuple(_q(close) for close in closes)
    context = FuturesMarketObservationContext(
        contract=decision.reference.contract,
        timeframe=_DAILY,
        observed_at=_SESSION,
        latest_quote=quotes[-1],
        previous_close=quotes[-2],
        latest_volume=Quantity(Decimal("1000")),
        session_high=quotes[-1],
        session_low=quotes[-1],
        recent_closes=quotes,
        recent_volumes=tuple(Quantity(Decimal("1000")) for _ in quotes),
    )
    return FuturesCandidateEvidence(decision.reference, context)


def _generate(
    *decisions: FuturesResearchDecision,
    open_recommendations: tuple[FuturesTradeRecommendationLifecycle, ...] = (),
) -> FuturesRecommendationGeneration:
    selection = FuturesCandidateSelection.select(_CRITERIA, decisions)
    evidence = tuple(_evidence(candidate.decision) for candidate in selection.candidates)
    windows = tuple(
        FuturesRecommendationSessionWindow(contract, _ELIGIBLE, _VALID_THROUGH, _CUTOFFS[contract])
        for contract in {candidate.contract for candidate in selection.candidates}
    )
    return FuturesRecommendationGeneration.generate(
        _POLICY, selection, evidence, windows, open_recommendations, _ISSUED
    )


def _only_reason(generation: FuturesRecommendationGeneration) -> Reason:
    assert generation.proposals == ()
    (rejection,) = generation.rejections
    return rejection.reason


# -- existing recommendations in every lifecycle status ----------------------------------


def _recommendation(
    direction: TradeDirection,
    contract: FuturesContract = _OCT,
    *,
    identity: str = "open-1",
    valid_through: PointInTime = _VALID_THROUGH,
) -> FuturesTradeRecommendation:
    long = direction is LONG
    return FuturesTradeRecommendation(
        identity=FuturesTradeRecommendationIdentity(identity),
        contract=contract,
        direction=direction,
        entry=EntryZone(_q("24300"), _q("24310")),
        stop=StopLoss(_q("24250" if long else "24360")),
        target=PriceTarget(_q("24400" if long else "24200")),
        validity=RecommendationValidity(
            _OPEN_ELIGIBLE, valid_through, _CUTOFFS.get(contract, _CUTOFFS[_OCT])
        ),
        source=FuturesResearchDecisionReference(contract, _DAILY, _OPEN_DECIDED, _STRATEGY),
        policy_version=_VERSION,
        issued_at=_OPEN_ISSUED,
        thesis=(ExplanationReason("Synthetic open recommendation"),),
    )


def _bar(contract: FuturesContract, at: str, low: str, high: str) -> FuturesOHLCVBar:
    return FuturesOHLCVBar(
        contract=contract,
        point_in_time=PointInTime(at),
        timeframe=_DAILY,
        open=_q(low),
        high=_q(high),
        low=_q(low),
        close=_q(high),
        volume=Quantity(Decimal("1000")),
    )


def _lifecycle(
    status: RecommendationStatus,
    direction: TradeDirection = LONG,
    contract: FuturesContract = _OCT,
    identity: str = "open-1",
) -> FuturesTradeRecommendationLifecycle:
    """Drive a synthetic recommendation (entry 24300-24310) into ``status``.

    LONG stop 24250 / target 24400; SHORT stop 24360 / target 24200. The quiet
    bar (24320-24350) touches neither the entry nor an exit for either side.
    """
    short_window = status in {
        Status.EXPIRED_BEFORE_ENTRY,
        Status.EXPIRED_AFTER_ACTIVATION,
        Status.EXPIRED_WITH_INCOMPLETE_COVERAGE,
    }
    end = _OPEN_SHORT_VALIDITY_END if short_window else _VALID_THROUGH
    lifecycle = FuturesTradeRecommendationLifecycle(
        _recommendation(direction, contract, identity=identity, valid_through=end)
    )
    day1, day2, last = "2026-09-29T10:00:00Z", "2026-09-30T10:00:00Z", "2026-10-02T10:00:00Z"
    long = direction is LONG
    activate = _bar(contract, day1, "24295", "24320")
    if status is Status.ACTIVE:
        lifecycle = lifecycle.advance(activate)
    elif status is Status.CLOSED_TARGET:
        exit_bar = ("24300", "24410") if long else ("24190", "24310")
        lifecycle = lifecycle.advance(activate).advance(_bar(contract, day2, *exit_bar))
    elif status is Status.CLOSED_STOP:
        exit_bar = ("24240", "24320") if long else ("24300", "24370")
        lifecycle = lifecycle.advance(activate).advance(_bar(contract, day2, *exit_bar))
    elif status is Status.INDETERMINATE_ENTRY:
        both = ("24240", "24320") if long else ("24300", "24370")
        lifecycle = lifecycle.advance(_bar(contract, day1, *both))
    elif status is Status.EXPIRED_BEFORE_ENTRY:
        lifecycle = lifecycle.advance(_bar(contract, last, "24320", "24350"))
    elif status is Status.EXPIRED_AFTER_ACTIVATION:
        lifecycle = lifecycle.advance(activate).advance(_bar(contract, last, "24320", "24350"))
    elif status is Status.EXPIRED_WITH_INCOMPLETE_COVERAGE:
        lifecycle = lifecycle.expire(
            TimeExpiryEvidence(
                as_of=PointInTime("2026-10-05T10:00:00Z"),
                evaluated_through=None,
                coverage=ObservationCoverage.INCOMPLETE_OR_UNVERIFIED_COVERAGE,
                attested_by="synthetic test",
                deficiency=CoverageDeficiency.MISSING_OBSERVATIONS,
            )
        )
    assert lifecycle.status is status
    return lifecycle


_TERMINAL = sorted(status for status in Status if status.is_terminal)
_NON_TERMINAL = sorted(status for status in Status if not status.is_terminal)


def test_the_status_partition_under_test_is_the_actual_lifecycle_vocabulary() -> None:
    """Guards the parametrized cases below against a status being added silently."""
    assert set(_NON_TERMINAL) == {Status.WAITING_FOR_ENTRY, Status.ACTIVE}
    assert set(_TERMINAL) | set(_NON_TERMINAL) == set(Status)
    assert len(_TERMINAL) == 6


# ---------------------------------------------------------------------------
# The approved P-1 matrix
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "existing_status, existing_direction, new_contract, new_direction, expected",
    [
        (Status.WAITING_FOR_ENTRY, LONG, _NOV, LONG, Reason.DUPLICATE_OPEN_RECOMMENDATION),
        (Status.ACTIVE, LONG, _NOV, LONG, Reason.DUPLICATE_OPEN_RECOMMENDATION),
        (Status.ACTIVE, LONG, _NOV, SHORT, Reason.CONTRADICTS_OPEN_RECOMMENDATION),
        (Status.ACTIVE, SHORT, _NOV, LONG, Reason.CONTRADICTS_OPEN_RECOMMENDATION),
        (Status.WAITING_FOR_ENTRY, SHORT, _DEC, SHORT, Reason.DUPLICATE_OPEN_RECOMMENDATION),
        (Status.WAITING_FOR_ENTRY, SHORT, _NOV, LONG, Reason.CONTRADICTS_OPEN_RECOMMENDATION),
        (Status.ACTIVE, SHORT, _DEC, SHORT, Reason.DUPLICATE_OPEN_RECOMMENDATION),
        (Status.WAITING_FOR_ENTRY, LONG, _DEC, SHORT, Reason.CONTRADICTS_OPEN_RECOMMENDATION),
    ],
)
def test_an_open_recommendation_on_another_expiry_blocks_the_product(
    existing_status: RecommendationStatus,
    existing_direction: TradeDirection,
    new_contract: FuturesContract,
    new_direction: TradeDirection,
    expected: Reason,
) -> None:
    existing = _lifecycle(existing_status, existing_direction, _OCT)
    decision = _decision(new_direction, new_contract)

    generation = _generate(decision, open_recommendations=(existing,))

    assert _only_reason(generation) is expected
    (rejection,) = generation.rejections
    assert rejection.source == decision.reference
    assert generation.exclusivity_breaches == ()


@pytest.mark.parametrize("existing_direction", [LONG, SHORT])
@pytest.mark.parametrize("new_direction", [LONG, SHORT])
@pytest.mark.parametrize("status", _NON_TERMINAL)
def test_same_contract_open_recommendations_still_block_symmetrically(
    status: RecommendationStatus,
    existing_direction: TradeDirection,
    new_direction: TradeDirection,
) -> None:
    existing = _lifecycle(status, existing_direction, _OCT)

    generation = _generate(_decision(new_direction, _OCT), open_recommendations=(existing,))

    expected = (
        Reason.DUPLICATE_OPEN_RECOMMENDATION
        if existing_direction is new_direction
        else Reason.CONTRADICTS_OPEN_RECOMMENDATION
    )
    assert _only_reason(generation) is expected


@pytest.mark.parametrize("existing_direction", [LONG, SHORT])
@pytest.mark.parametrize("status", _TERMINAL)
def test_a_terminal_recommendation_never_blocks_the_product(
    status: RecommendationStatus, existing_direction: TradeDirection
) -> None:
    existing = _lifecycle(status, existing_direction, _OCT)

    generation = _generate(_decision(LONG, _NOV), open_recommendations=(existing,))

    (proposal,) = generation.proposals
    assert proposal.contract == _NOV
    assert generation.rejections == ()
    assert generation.exclusivity_breaches == ()


def test_an_open_recommendation_on_another_product_is_independent() -> None:
    existing = _lifecycle(Status.ACTIVE, SHORT, _OCT)

    generation = _generate(_decision(LONG, _BANK_OCT), open_recommendations=(existing,))

    (proposal,) = generation.proposals
    assert proposal.contract == _BANK_OCT


def test_the_same_symbol_on_another_exchange_is_another_product() -> None:
    """Products compare by FuturesProductReference equality, never by symbol text."""
    nifty_elsewhere = FuturesProductReference(Symbol("NIFTY"), ExchangeCode("SGX"))
    elsewhere = FuturesContract(nifty_elsewhere, ExpirationDate("2026-10-27"))
    existing = FuturesTradeRecommendationLifecycle(_recommendation(LONG, elsewhere))

    generation = _generate(_decision(LONG, _NOV), open_recommendations=(existing,))

    assert generation.proposals[0].contract == _NOV


def test_an_equal_but_separately_built_product_is_the_same_product() -> None:
    rebuilt = FuturesContract(
        FuturesProductReference(Symbol("NIFTY"), ExchangeCode("NSE")), ExpirationDate("2026-10-27")
    )
    assert rebuilt.product == _NIFTY and rebuilt.product is not _NIFTY
    existing = FuturesTradeRecommendationLifecycle(_recommendation(LONG, rebuilt))

    generation = _generate(_decision(LONG, _NOV), open_recommendations=(existing,))

    assert _only_reason(generation) is Reason.DUPLICATE_OPEN_RECOMMENDATION


def test_without_open_recommendations_generation_is_unchanged() -> None:
    (proposal,) = _generate(_decision(LONG, _OCT)).proposals

    assert proposal.entry == EntryZone(_q("24378"), _q("24388"))
    assert proposal.stop == StopLoss(_q("24347.75"))
    assert proposal.target == PriceTarget(_q("24448.45"))


def test_the_nearest_contract_is_checked_and_the_others_stay_not_nearest() -> None:
    """P-1 does not replace same-session arbitration, and there is still no fallback."""
    existing = _lifecycle(Status.WAITING_FOR_ENTRY, LONG, _DEC)

    generation = _generate(
        _decision(LONG, _OCT), _decision(LONG, _NOV), open_recommendations=(existing,)
    )

    assert generation.proposals == ()
    assert {r.candidate.contract: r.reason for r in generation.rejections} == {
        _OCT: Reason.DUPLICATE_OPEN_RECOMMENDATION,
        _NOV: Reason.NOT_NEAREST_ELIGIBLE_CONTRACT,
    }


def test_same_session_contradiction_still_precedes_open_checks() -> None:
    existing = _lifecycle(Status.ACTIVE, LONG, _DEC)

    generation = _generate(
        _decision(LONG, _OCT), _decision(SHORT, _NOV), open_recommendations=(existing,)
    )

    assert {r.reason for r in generation.rejections} == {Reason.CONTRADICTORY_PRODUCT_DIRECTION}


# ---------------------------------------------------------------------------
# Supplied state that already breaks exclusivity fails closed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "new_direction, expected",
    [(LONG, Reason.DUPLICATE_OPEN_RECOMMENDATION), (SHORT, Reason.CONTRADICTS_OPEN_RECOMMENDATION)],
)
def test_several_same_direction_open_recommendations_reject_and_are_reported(
    new_direction: TradeDirection, expected: Reason
) -> None:
    opened = (
        _lifecycle(Status.WAITING_FOR_ENTRY, LONG, _OCT, "a"),
        _lifecycle(Status.ACTIVE, LONG, _NOV, "b"),
    )

    generation = _generate(_decision(new_direction, _DEC), open_recommendations=opened)

    assert _only_reason(generation) is expected
    assert generation.exclusivity_breaches == (_NIFTY,)


@pytest.mark.parametrize("new_direction", [LONG, SHORT])
def test_contradictory_open_state_fails_closed_for_either_new_direction(
    new_direction: TradeDirection,
) -> None:
    opened = (
        _lifecycle(Status.ACTIVE, LONG, _OCT, "a"),
        _lifecycle(Status.WAITING_FOR_ENTRY, SHORT, _NOV, "b"),
    )

    for ordering in permutations(opened):
        generation = _generate(_decision(new_direction, _DEC), open_recommendations=ordering)
        assert _only_reason(generation) is Reason.CONTRADICTS_OPEN_RECOMMENDATION
        assert generation.exclusivity_breaches == (_NIFTY,)


def test_a_breach_is_reported_even_for_a_product_without_candidates() -> None:
    opened = (
        _lifecycle(Status.ACTIVE, LONG, _OCT, "a"),
        _lifecycle(Status.ACTIVE, LONG, _NOV, "b"),
    )

    generation = _generate(_decision(LONG, _BANK_OCT), open_recommendations=opened)

    assert generation.proposals[0].contract == _BANK_OCT
    assert generation.exclusivity_breaches == (_NIFTY,)


def test_a_terminal_recommendation_beside_an_open_one_is_not_a_breach() -> None:
    opened = (
        _lifecycle(Status.CLOSED_STOP, LONG, _OCT, "a"),
        _lifecycle(Status.ACTIVE, LONG, _NOV, "b"),
    )

    generation = _generate(_decision(LONG, _DEC), open_recommendations=opened)

    assert _only_reason(generation) is Reason.DUPLICATE_OPEN_RECOMMENDATION
    assert generation.exclusivity_breaches == ()


def test_identical_repeated_open_entries_are_one_recommendation() -> None:
    existing = _lifecycle(Status.ACTIVE, LONG, _OCT)

    generation = _generate(_decision(LONG, _NOV), open_recommendations=(existing, existing))

    assert _only_reason(generation) is Reason.DUPLICATE_OPEN_RECOMMENDATION
    assert generation.exclusivity_breaches == ()


def test_two_different_lifecycles_under_one_identity_are_an_error() -> None:
    waiting = _lifecycle(Status.WAITING_FOR_ENTRY, LONG, _OCT, "same")
    active = _lifecycle(Status.ACTIVE, LONG, _OCT, "same")

    with pytest.raises(InvalidFuturesRecommendationGenerationError):
        _generate(_decision(LONG, _NOV), open_recommendations=(waiting, active))


def test_a_terminal_lifecycle_is_still_validated() -> None:
    """Excluded from blocking, but an identity collision is still contradictory input."""
    closed = _lifecycle(Status.CLOSED_TARGET, LONG, _OCT, "same")
    waiting = _lifecycle(Status.WAITING_FOR_ENTRY, LONG, _OCT, "same")

    with pytest.raises(InvalidFuturesRecommendationGenerationError):
        _generate(_decision(LONG, _NOV), open_recommendations=(closed, waiting))


def test_results_do_not_depend_on_the_order_of_open_recommendations() -> None:
    opened = (
        _lifecycle(Status.ACTIVE, LONG, _OCT, "a"),
        _lifecycle(Status.WAITING_FOR_ENTRY, LONG, _NOV, "b"),
        _lifecycle(Status.CLOSED_TARGET, SHORT, _DEC, "c"),
        _lifecycle(Status.ACTIVE, SHORT, _BANK_OCT, "d"),
    )
    decisions = (_decision(LONG, _DEC), _decision(LONG, _BANK_OCT))

    results = {
        _generate(*decisions, open_recommendations=ordering) for ordering in permutations(opened)
    }

    assert len(results) == 1
    (result,) = results
    assert {r.candidate.contract: r.reason for r in result.rejections} == {
        _DEC: Reason.DUPLICATE_OPEN_RECOMMENDATION,
        _BANK_OCT: Reason.CONTRADICTS_OPEN_RECOMMENDATION,
    }
    assert result.exclusivity_breaches == (_NIFTY,)


def test_open_lifecycle_inputs_are_not_mutated() -> None:
    opened = (_lifecycle(Status.ACTIVE, LONG, _OCT, "a"), _lifecycle(Status.CLOSED_STOP))
    before = repr(opened)

    _generate(_decision(SHORT, _NOV), open_recommendations=opened)

    assert repr(opened) == before


# ---------------------------------------------------------------------------
# The stored result's breach report
# ---------------------------------------------------------------------------


def test_a_stored_generation_keeps_its_breach_report() -> None:
    opened = (
        _lifecycle(Status.ACTIVE, LONG, _OCT, "a"),
        _lifecycle(Status.ACTIVE, LONG, _NOV, "b"),
    )
    generation = _generate(_decision(LONG, _DEC), open_recommendations=opened)

    rebuilt = FuturesRecommendationGeneration(
        generation.policy,
        generation.issued_at,
        generation.proposals,
        generation.rejections,
        generation.exclusivity_breaches,
    )

    assert rebuilt == generation


@pytest.mark.parametrize(
    "breaches",
    [(_NIFTY, _NIFTY), (_NIFTY, _BANKNIFTY), ("NIFTY@NSE",)],
    ids=["duplicate", "unsorted", "not-a-product"],
)
def test_a_stored_breach_report_must_be_distinct_sorted_products(breaches: tuple) -> None:
    generation = _generate(_decision(LONG, _OCT))

    with pytest.raises(InvalidFuturesRecommendationGenerationError):
        FuturesRecommendationGeneration(
            generation.policy, generation.issued_at, generation.proposals, (), breaches
        )


# ---------------------------------------------------------------------------
# J-1 -- a stored result never pairs a proposal with a breached product
# ---------------------------------------------------------------------------


def _with_breaches(
    generation: FuturesRecommendationGeneration, breaches: tuple
) -> FuturesRecommendationGeneration:
    return FuturesRecommendationGeneration(
        generation.policy,
        generation.issued_at,
        generation.proposals,
        generation.rejections,
        breaches,
    )


@pytest.mark.parametrize("contract", [_OCT, _NOV], ids=["same-expiry", "other-expiry"])
def test_a_proposal_on_a_breached_product_cannot_be_stored(contract: FuturesContract) -> None:
    generation = _generate(_decision(LONG, contract))
    assert generation.proposals[0].contract == contract

    with pytest.raises(InvalidFuturesRecommendationGenerationError, match="break exclusivity"):
        _with_breaches(generation, (_NIFTY,))


def test_an_equal_separately_built_product_reference_is_the_same_breach() -> None:
    generation = _generate(_decision(LONG, _OCT))
    rebuilt = FuturesProductReference(Symbol("NIFTY"), ExchangeCode("NSE"))
    assert rebuilt == _NIFTY and rebuilt is not _NIFTY

    with pytest.raises(InvalidFuturesRecommendationGenerationError):
        _with_breaches(generation, (rebuilt,))


def test_a_breach_on_another_product_beside_a_proposal_is_permitted() -> None:
    generation = _generate(_decision(LONG, _OCT))

    stored = _with_breaches(generation, (_BANKNIFTY,))

    assert stored.exclusivity_breaches == (_BANKNIFTY,)
    assert stored.proposals == generation.proposals


def test_a_breach_without_any_proposal_is_permitted() -> None:
    generation = _generate(
        _decision(LONG, _NOV),
        open_recommendations=(
            _lifecycle(Status.ACTIVE, LONG, _OCT, "a"),
            _lifecycle(Status.ACTIVE, LONG, _DEC, "b"),
        ),
    )

    assert generation.proposals == ()
    assert _with_breaches(generation, (_NIFTY,)) == generation


def test_an_empty_breach_collection_keeps_existing_behaviour() -> None:
    generation = _generate(_decision(LONG, _OCT))

    assert _with_breaches(generation, ()) == generation
    assert (
        FuturesRecommendationGeneration(
            generation.policy, generation.issued_at, generation.proposals, generation.rejections
        )
        == generation
    )


def test_refusing_an_inconsistent_result_is_deterministic_and_mutates_nothing() -> None:
    generation = _generate(_decision(LONG, _OCT))
    before = repr(generation)

    for _ in range(3):
        with pytest.raises(InvalidFuturesRecommendationGenerationError):
            _with_breaches(generation, (_NIFTY,))

    assert repr(generation) == before
