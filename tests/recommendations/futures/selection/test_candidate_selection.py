"""Tests for deterministic candidate selection from frozen research decisions.

The selection session closes at 2026-10-07T10:00:00Z (15:30 IST). Approved
scope: NIFTY@NSE and strategy directional-mvp-v1. Synthetic research only.

Approved product-owner decisions under test:
D1 BUY and SELL are candidates with the action unchanged; HOLD is rejected.
D2 Only decisions made exactly at the selection session close are fresh.
D3 Any contract of an approved product may yield a candidate.
D4 Each approved strategy yields its own candidate.
"""

from __future__ import annotations

import dataclasses
from itertools import permutations

import pytest

from northstar_core.derivatives import ExpirationDate
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import ExchangeCode, PointInTime, Symbol, Timeframe
from northstar_core.futures import FuturesContract, FuturesProductReference
from northstar_core.recommendations.futures import (
    CandidateRejectionReason,
    FuturesCandidateRejection,
    FuturesCandidateSelection,
    FuturesCandidateSelectionCriteria,
    FuturesRecommendationCandidate,
    FuturesResearchDecision,
    FuturesResearchDecisionReference,
    InvalidFuturesCandidateSelectionError,
)
from northstar_core.strategy import (
    FuturesAssetAnalysis,
    FuturesRecommendation,
    RecommendationAction,
    StrategyIdentity,
)

Reason = CandidateRejectionReason

_NIFTY = FuturesProductReference(Symbol("NIFTY"), ExchangeCode("NSE"))
_BANKNIFTY = FuturesProductReference(Symbol("BANKNIFTY"), ExchangeCode("NSE"))
_OCT = FuturesContract(_NIFTY, ExpirationDate("2026-10-27"))
_NOV = FuturesContract(_NIFTY, ExpirationDate("2026-11-24"))
_BANK_OCT = FuturesContract(_BANKNIFTY, ExpirationDate("2026-10-27"))
_DAILY = Timeframe("1d")
_STRATEGY = StrategyIdentity("directional-mvp-v1")
_SECOND = StrategyIdentity("breakout-v2")
_UNAPPROVED = StrategyIdentity("experimental-v0")

_SESSION = PointInTime("2026-10-07T10:00:00Z")
_EARLIER = PointInTime("2026-10-06T10:00:00Z")
_LATER = PointInTime("2026-10-08T10:00:00Z")

_CRITERIA = FuturesCandidateSelectionCriteria(_SESSION, (_NIFTY,), (_STRATEGY,))
_TWO_STRATEGIES = FuturesCandidateSelectionCriteria(_SESSION, (_NIFTY,), (_STRATEGY, _SECOND))


def _decision(
    action: str = "BUY",
    *,
    contract: FuturesContract = _OCT,
    at: PointInTime = _SESSION,
    strategy: StrategyIdentity = _STRATEGY,
    timeframe: Timeframe = _DAILY,
    signal: str = "strong bullish",
) -> FuturesResearchDecision:
    return FuturesResearchDecision(
        FuturesResearchDecisionReference(contract, timeframe, at, strategy),
        FuturesRecommendation(
            action=RecommendationAction(action),
            asset_analysis=FuturesAssetAnalysis(contract, at, (signal,)),
            strategy_identity=strategy,
            point_in_time=at,
        ),
    )


def _select(
    *decisions: FuturesResearchDecision,
    criteria: FuturesCandidateSelectionCriteria = _CRITERIA,
) -> FuturesCandidateSelection:
    return FuturesCandidateSelection.select(criteria, decisions)


def _reasons(selection: FuturesCandidateSelection) -> list[CandidateRejectionReason]:
    return [rejection.reason for rejection in selection.rejections]


# ---------------------------------------------------------------------------
# D1 -- research actions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("action", ["BUY", "SELL"])
def test_a_fresh_approved_directional_decision_is_a_candidate(action: str) -> None:
    selection = _select(_decision(action))

    (candidate,) = selection.candidates
    assert selection.rejections == ()
    assert candidate.research_action == RecommendationAction(action)
    assert candidate.decision == _decision(action)


def test_a_sell_decision_stays_sell_and_gains_no_direction() -> None:
    """SELL is not silently reinterpreted as SHORT (ADR-017)."""
    (candidate,) = _select(_decision("SELL")).candidates

    assert candidate.research_action.value == "SELL"
    assert {field.name for field in dataclasses.fields(candidate)} == {"decision"}


def test_a_hold_decision_is_rejected_for_no_directional_view() -> None:
    selection = _select(_decision("HOLD"))

    assert selection.candidates == ()
    assert _reasons(selection) == [Reason.NO_DIRECTIONAL_VIEW]


# ---------------------------------------------------------------------------
# D2 -- freshness and look-ahead
# ---------------------------------------------------------------------------


def test_a_decision_before_the_session_is_stale() -> None:
    assert _reasons(_select(_decision(at=_EARLIER))) == [Reason.STALE_DECISION]


def test_a_decision_after_the_session_is_look_ahead() -> None:
    assert _reasons(_select(_decision(at=_LATER))) == [Reason.AFTER_SELECTION_SESSION]


@pytest.mark.parametrize(
    "at",
    ["2026-10-07T09:59:59.999999Z", "2026-10-07T10:00:00.000001Z"],
    ids=["one-microsecond-before", "one-microsecond-after"],
)
def test_freshness_is_exact_to_the_instant(at: str) -> None:
    assert _select(_decision(at=PointInTime(at))).candidates == ()


def test_the_session_close_in_another_offset_is_the_same_instant() -> None:
    selection = _select(_decision(at=PointInTime("2026-10-07T15:30:00+05:30")))

    assert len(selection.candidates) == 1


def test_a_newer_hold_supersedes_an_older_buy() -> None:
    """Only the latest session's decision counts; an older BUY never resurfaces."""
    selection = _select(_decision("BUY", at=_EARLIER), _decision("HOLD", at=_SESSION))

    assert selection.candidates == ()
    assert _reasons(selection) == [Reason.STALE_DECISION, Reason.NO_DIRECTIONAL_VIEW]


def test_a_missing_current_decision_does_not_promote_an_older_one() -> None:
    """With no decision at the session, nothing is selected: missing data is not fresh."""
    selection = _select(
        _decision("BUY", at=_EARLIER), _decision("SELL", at=PointInTime("2026-10-05T10:00:00Z"))
    )

    assert selection.candidates == ()
    assert _reasons(selection) == [Reason.STALE_DECISION, Reason.STALE_DECISION]


# ---------------------------------------------------------------------------
# Scope -- timeframe, product, strategy
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("timeframe", ["1h", "1w"])
def test_a_non_daily_decision_is_unsupported(timeframe: str) -> None:
    selection = _select(_decision(timeframe=Timeframe(timeframe)))

    assert _reasons(selection) == [Reason.UNSUPPORTED_TIMEFRAME]


def test_an_unapproved_product_is_rejected() -> None:
    assert _reasons(_select(_decision(contract=_BANK_OCT))) == [Reason.UNAPPROVED_PRODUCT]


def test_an_unapproved_strategy_is_rejected() -> None:
    assert _reasons(_select(_decision(strategy=_UNAPPROVED))) == [Reason.UNAPPROVED_STRATEGY]


def test_an_approved_second_product_is_selected() -> None:
    criteria = FuturesCandidateSelectionCriteria(_SESSION, (_NIFTY, _BANKNIFTY), (_STRATEGY,))

    assert len(_select(_decision(contract=_BANK_OCT), criteria=criteria).candidates) == 1


# ---------------------------------------------------------------------------
# Rule priority: exactly one reason, the first that applies
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("decision", "reason"),
    [
        (
            _decision("HOLD", at=_LATER, contract=_BANK_OCT, strategy=_UNAPPROVED),
            Reason.AFTER_SELECTION_SESSION,
        ),
        (
            _decision("HOLD", at=_EARLIER, timeframe=Timeframe("1h"), strategy=_UNAPPROVED),
            Reason.STALE_DECISION,
        ),
        (
            _decision("HOLD", timeframe=Timeframe("1h"), contract=_BANK_OCT),
            Reason.UNSUPPORTED_TIMEFRAME,
        ),
        (_decision("HOLD", contract=_BANK_OCT, strategy=_UNAPPROVED), Reason.UNAPPROVED_PRODUCT),
        (_decision("HOLD", strategy=_UNAPPROVED), Reason.UNAPPROVED_STRATEGY),
    ],
    ids=["look-ahead-first", "stale-second", "timeframe-third", "product-fourth", "strategy-fifth"],
)
def test_the_highest_priority_reason_is_recorded(
    decision: FuturesResearchDecision, reason: CandidateRejectionReason
) -> None:
    assert _reasons(_select(decision)) == [reason]


# ---------------------------------------------------------------------------
# D3 -- contracts, D4 -- strategies
# ---------------------------------------------------------------------------


def test_every_contract_of_an_approved_product_may_be_a_candidate() -> None:
    selection = _select(_decision("BUY", contract=_OCT), _decision("SELL", contract=_NOV))

    assert [candidate.contract for candidate in selection.candidates] == [_OCT, _NOV]
    assert [c.research_action.value for c in selection.candidates] == ["BUY", "SELL"]


def test_each_approved_strategy_yields_its_own_candidate_even_when_they_disagree() -> None:
    selection = _select(
        _decision("BUY", strategy=_STRATEGY),
        _decision("SELL", strategy=_SECOND),
        criteria=_TWO_STRATEGIES,
    )

    assert [(c.strategy_identity, c.research_action.value) for c in selection.candidates] == [
        (_SECOND, "SELL"),
        (_STRATEGY, "BUY"),
    ]


# ---------------------------------------------------------------------------
# Duplicates and contradictions
# ---------------------------------------------------------------------------


def test_identical_duplicate_decisions_are_one_decision() -> None:
    selection = _select(_decision(), _decision(), _decision())

    assert len(selection.candidates) == 1


def test_identical_duplicate_rejections_are_one_rejection() -> None:
    selection = _select(_decision("HOLD"), _decision("HOLD"))

    assert _reasons(selection) == [Reason.NO_DIRECTIONAL_VIEW]


@pytest.mark.parametrize(
    "other",
    [_decision("SELL"), _decision("BUY", signal="neutral trend")],
    ids=["different-action", "different-evidence"],
)
def test_contradictory_decisions_under_one_reference_are_refused(
    other: FuturesResearchDecision,
) -> None:
    with pytest.raises(InvalidFuturesCandidateSelectionError, match="contradictory"):
        _select(_decision("BUY"), other)


def test_contradiction_is_refused_even_when_both_would_be_rejected() -> None:
    with pytest.raises(InvalidFuturesCandidateSelectionError, match="contradictory"):
        _select(_decision("HOLD", at=_EARLIER), _decision("BUY", at=_EARLIER))


# ---------------------------------------------------------------------------
# Determinism, ordering and reproducibility
# ---------------------------------------------------------------------------

_MIXED = (
    _decision("BUY", contract=_NOV),
    _decision("SELL", contract=_OCT),
    _decision("HOLD", contract=_OCT, strategy=_SECOND),
    _decision("BUY", contract=_OCT, at=_EARLIER),
    _decision("BUY", contract=_BANK_OCT),
    _decision("SELL", contract=_OCT, at=_LATER),
)


def test_selection_does_not_depend_on_input_order() -> None:
    expected = _select(*_MIXED, criteria=_TWO_STRATEGIES)

    for ordering in permutations(_MIXED):
        assert _select(*ordering, criteria=_TWO_STRATEGIES) == expected


def test_results_are_sorted_by_product_expiry_strategy_and_instant() -> None:
    selection = _select(*_MIXED, criteria=_TWO_STRATEGIES)

    assert [(str(c.contract), c.research_action.value) for c in selection.candidates] == [
        ("NIFTY@NSE 2026-10-27", "SELL"),
        ("NIFTY@NSE 2026-11-24", "BUY"),
    ]
    assert [(str(r.decision.reference.contract), r.reason) for r in selection.rejections] == [
        ("BANKNIFTY@NSE 2026-10-27", Reason.UNAPPROVED_PRODUCT),
        ("NIFTY@NSE 2026-10-27", Reason.NO_DIRECTIONAL_VIEW),
        ("NIFTY@NSE 2026-10-27", Reason.STALE_DECISION),
        ("NIFTY@NSE 2026-10-27", Reason.AFTER_SELECTION_SESSION),
    ]


def test_rejections_are_ordered_chronologically_not_by_text() -> None:
    """'...10:00:00.5Z' sorts before '...10:00:00Z' as text but is later in time."""
    later_by_half_second = _decision("BUY", at=PointInTime("2026-10-06T10:00:00.5Z"))
    earlier = _decision("BUY", at=_EARLIER)

    selection = _select(later_by_half_second, earlier)

    assert [r.decision for r in selection.rejections] == [earlier, later_by_half_second]


def test_selecting_twice_gives_equal_results() -> None:
    assert _select(*_MIXED, criteria=_TWO_STRATEGIES) == _select(*_MIXED, criteria=_TWO_STRATEGIES)


def test_no_decisions_gives_an_empty_selection() -> None:
    selection = _select()

    assert selection.candidates == () and selection.rejections == ()
    assert str(selection) == "0 candidate(s), 0 rejection(s) for session 2026-10-07T10:00:00Z"


def test_selection_does_not_mutate_its_input() -> None:
    decisions = _MIXED
    snapshot = tuple(decisions)

    _select(*decisions, criteria=_TWO_STRATEGIES)

    assert decisions == snapshot


def test_the_selection_is_frozen() -> None:
    selection = _select(_decision())

    with pytest.raises(dataclasses.FrozenInstanceError):
        selection.candidates = ()  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Reconstruction from stored parts
# ---------------------------------------------------------------------------


def test_a_selection_rebuilt_from_its_parts_is_equal() -> None:
    selected = _select(*_MIXED, criteria=_TWO_STRATEGIES)

    rebuilt = FuturesCandidateSelection(selected.criteria, selected.candidates, selected.rejections)

    assert rebuilt == selected


def test_a_forged_candidate_is_refused() -> None:
    hold_as_stale_candidate = FuturesRecommendationCandidate(_decision("BUY", at=_EARLIER))

    with pytest.raises(InvalidFuturesCandidateSelectionError, match="not what its criteria"):
        FuturesCandidateSelection(_CRITERIA, (hold_as_stale_candidate,), ())


def test_a_wrong_rejection_reason_is_refused() -> None:
    wrong = FuturesCandidateRejection(_decision("HOLD"), Reason.UNAPPROVED_STRATEGY)

    with pytest.raises(InvalidFuturesCandidateSelectionError, match="not what its criteria"):
        FuturesCandidateSelection(_CRITERIA, (), (wrong,))


def test_a_rejected_candidate_cannot_be_hidden() -> None:
    """Dropping a candidate into the rejections, or vice versa, is refused."""
    selected = _select(_decision("BUY"))
    hidden = FuturesCandidateRejection(_decision("BUY"), Reason.NO_DIRECTIONAL_VIEW)

    with pytest.raises(InvalidFuturesCandidateSelectionError):
        FuturesCandidateSelection(selected.criteria, (), (hidden,))


def test_parts_out_of_canonical_order_are_refused() -> None:
    selected = _select(_decision(contract=_OCT), _decision(contract=_NOV))

    with pytest.raises(InvalidFuturesCandidateSelectionError, match="not what its criteria"):
        FuturesCandidateSelection(selected.criteria, selected.candidates[::-1], ())


def test_a_decision_listed_twice_is_refused() -> None:
    candidate = FuturesRecommendationCandidate(_decision())

    with pytest.raises(InvalidFuturesCandidateSelectionError, match="more than once"):
        FuturesCandidateSelection(_CRITERIA, (candidate, candidate), ())


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("criteria", "decisions", "message"),
    [
        (None, (), "FuturesCandidateSelectionCriteria"),
        ("criteria", (), "FuturesCandidateSelectionCriteria"),
        (_CRITERIA, [_decision()], "must be a tuple"),
        (_CRITERIA, (_decision(), "decision"), "FuturesResearchDecision"),
        (_CRITERIA, (_decision().assessment,), "FuturesResearchDecision"),
    ],
    ids=["no-criteria", "text-criteria", "list", "text-decision", "bare-assessment"],
)
def test_selection_inputs_require_their_domain_types(
    criteria: object, decisions: object, message: str
) -> None:
    with pytest.raises(InvalidFuturesCandidateSelectionError, match=message):
        FuturesCandidateSelection.select(criteria, decisions)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("candidates", "rejections"),
    [([], ()), ((), []), (("candidate",), ()), ((), ("rejection",))],
)
def test_stored_parts_require_their_domain_types(candidates: object, rejections: object) -> None:
    with pytest.raises(InvalidFuturesCandidateSelectionError, match="must be a tuple"):
        FuturesCandidateSelection(_CRITERIA, candidates, rejections)  # type: ignore[arg-type]


def test_the_selection_error_is_a_validation_error() -> None:
    assert issubclass(InvalidFuturesCandidateSelectionError, ValidationError)
