"""Regression tests for the B1 and B2 temporal corrections, and L-3 preservation.

B1: a daily bar that completes after issuance can still contain prices traded
before it. Only bars completing at or after the caller-resolved
``validity.eligible_from`` -- the close of the first session that began after
issuance -- are evaluated. Earlier bars are ignored and not consumed.

B2: after a contract's last session no later bar can arrive, and the final bar
may be missing or stamped at another instant. ``expire(evidence)`` ends an open
recommendation by time once ``valid_through`` has passed, recording whether the
caller asserted complete verified coverage or reported a deficiency.

Synthetic NIFTY bars only. Sessions close at 10:00Z (15:30 IST). The levels are:

    LONG : stop 24800 | entry 25000-25100 | target 25500
    SHORT: target 24600 | entry 25000-25100 | stop 25300
"""

from __future__ import annotations

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
from northstar_core.futures import FuturesContract, FuturesOHLCVBar, FuturesProductReference
from northstar_core.recommendations.futures import (
    CoverageDeficiency,
    EntryZone,
    FuturesResearchDecisionReference,
    FuturesTradeRecommendation,
    FuturesTradeRecommendationEvent,
    FuturesTradeRecommendationIdentity,
    FuturesTradeRecommendationLifecycle,
    IntrabarOrdering,
    InvalidFuturesTradeRecommendationExpiryError,
    InvalidFuturesTradeRecommendationLifecycleError,
    InvalidFuturesTradeRecommendationObservationError,
    ObservationCoverage,
    PriceTarget,
    RecommendationBoundary,
    RecommendationEventKind,
    RecommendationExpiryReason,
    RecommendationPolicyVersion,
    RecommendationStatus,
    RecommendationValidity,
    StopLoss,
    TimeExpiryEvidence,
    TradeDirection,
)
from northstar_core.strategy import ExplanationReason, StrategyIdentity

_OCT = FuturesContract(
    FuturesProductReference(Symbol("NIFTY"), ExchangeCode("NSE")), ExpirationDate("2026-10-27")
)
_DAILY = Timeframe("1d")
Status = RecommendationStatus
Kind = RecommendationEventKind
_ENTRY = RecommendationBoundary.ENTRY
_STOP = RecommendationBoundary.STOP
_TARGET = RecommendationBoundary.TARGET
_VERIFIED = ObservationCoverage.COMPLETE_VERIFIED_COVERAGE
_INCOMPLETE = ObservationCoverage.INCOMPLETE_OR_UNVERIFIED_COVERAGE

# Statuses a verified performance outcome could be drawn from.
_VERIFIED_OUTCOMES = {
    Status.CLOSED_TARGET,
    Status.CLOSED_STOP,
    Status.EXPIRED_BEFORE_ENTRY,
    Status.EXPIRED_AFTER_ACTIVATION,
}


def _at(day: int, time: str = "10:00:00") -> PointInTime:
    return PointInTime(f"2026-10-{day:02d}T{time}Z")


def _quote(value: str) -> QuoteValue:
    return QuoteValue(Decimal(value))


def _recommendation(
    direction: TradeDirection = TradeDirection.LONG,
    *,
    issued_at: PointInTime | None = None,
    eligible_from: PointInTime | None = None,
    valid_through: PointInTime | None = None,
    contract_cutoff: PointInTime | None = None,
) -> FuturesTradeRecommendation:
    long = direction is TradeDirection.LONG
    return FuturesTradeRecommendation(
        identity=FuturesTradeRecommendationIdentity("rec-t"),
        contract=_OCT,
        direction=direction,
        entry=EntryZone(_quote("25000"), _quote("25100")),
        stop=StopLoss(_quote("24800" if long else "25300")),
        target=PriceTarget(_quote("25500" if long else "24600")),
        validity=RecommendationValidity(
            eligible_from or _at(6), valid_through or _at(16), contract_cutoff or _at(27)
        ),
        source=FuturesResearchDecisionReference(
            _OCT, _DAILY, _at(5), StrategyIdentity("directional-mvp-v1")
        ),
        policy_version=RecommendationPolicyVersion("levels-v1"),
        issued_at=issued_at or _at(5, "12:00:00"),
        thesis=(ExplanationReason("Synthetic thesis"),),
    )


def _bar(at: PointInTime, low: str, high: str, *, close: str | None = None) -> FuturesOHLCVBar:
    return FuturesOHLCVBar(
        contract=_OCT,
        point_in_time=at,
        timeframe=_DAILY,
        open=_quote(low),
        high=_quote(high),
        low=_quote(low),
        close=_quote(close or high),
        volume=Quantity(Decimal("1000")),
    )


def _fold(
    recommendation: FuturesTradeRecommendation, *bars: FuturesOHLCVBar
) -> FuturesTradeRecommendationLifecycle:
    lifecycle = FuturesTradeRecommendationLifecycle(recommendation)
    for bar in bars:
        lifecycle = lifecycle.advance(bar)
    return lifecycle


def _evidence(
    lifecycle: FuturesTradeRecommendationLifecycle,
    as_of: PointInTime,
    *,
    verified: bool = False,
    deficiency: CoverageDeficiency = CoverageDeficiency.MISSING_OBSERVATIONS,
) -> TimeExpiryEvidence:
    """Synthetic evidence describing exactly what the lifecycle evaluated."""
    last = lifecycle.last_observation
    return TimeExpiryEvidence(
        as_of=as_of,
        evaluated_through=None if last is None else last.point_in_time,
        coverage=_VERIFIED if verified else _INCOMPLETE,
        attested_by="synthetic-test-coverage",
        deficiency=None if verified else deficiency,
    )


# Representative ranges.
_L_ENTRY = ("25050", "25300")
_L_QUIET = ("25200", "25400")
_L_TARGET = ("25200", "25600")
_L_STOP = ("24700", "25200")
_L_BOTH = ("24700", "25600")
_L_ENTRY_STOP = ("24700", "25050")
_L_ENTRY_TARGET = ("25050", "25600")
_S_ENTRY = ("24800", "25050")
_S_QUIET = ("24700", "24900")
_S_TARGET = ("24500", "24900")
_S_STOP = ("24900", "25350")
_S_BOTH = ("24500", "25350")
_S_ENTRY_STOP = ("25050", "25350")
_S_ENTRY_TARGET = ("24500", "25050")

_RANGES = {
    TradeDirection.LONG: {
        "entry": _L_ENTRY,
        "quiet": _L_QUIET,
        "target": _L_TARGET,
        "stop": _L_STOP,
        "both": _L_BOTH,
        "entry_stop": _L_ENTRY_STOP,
        "entry_target": _L_ENTRY_TARGET,
        "gap_far": ("25150", "25450"),
        "gap_near": ("24850", "24990"),
    },
    TradeDirection.SHORT: {
        "entry": _S_ENTRY,
        "quiet": _S_QUIET,
        "target": _S_TARGET,
        "stop": _S_STOP,
        "both": _S_BOTH,
        "entry_stop": _S_ENTRY_STOP,
        "entry_target": _S_ENTRY_TARGET,
        "gap_far": ("24650", "24990"),
        "gap_near": ("25110", "25290"),
    },
}

_L_RANGES = _RANGES[TradeDirection.LONG]

_DIRECTIONS = pytest.mark.parametrize(
    "direction", [TradeDirection.LONG, TradeDirection.SHORT], ids=["long", "short"]
)


# ===========================================================================
# B1 -- eligible_from
# ===========================================================================

# Issued mid-session on 10-06; the 10-06 session closes after issuance, and the
# first session that began after issuance closes on 10-07.
_MID_ISSUED = _at(6, "05:00:00")
_MID_ELIGIBLE = _at(7)


def _mid_session(direction: TradeDirection) -> FuturesTradeRecommendation:
    return _recommendation(direction, issued_at=_MID_ISSUED, eligible_from=_MID_ELIGIBLE)


@_DIRECTIONS
@pytest.mark.parametrize("shape", ["entry", "stop", "target", "both", "entry_stop"])
def test_b1_the_same_session_bar_never_activates_or_closes(
    direction: TradeDirection, shape: str
) -> None:
    """B1-1..5: completes after issuance, but its session began before it."""
    recommendation = _mid_session(direction)
    same_session = _bar(_at(6), *_RANGES[direction][shape])
    lifecycle = FuturesTradeRecommendationLifecycle(recommendation)

    after = lifecycle.advance(same_session)

    assert after is lifecycle
    assert after.status is Status.WAITING_FOR_ENTRY
    assert after.last_observation is None


@_DIRECTIONS
def test_b1_the_first_eligible_bar_at_eligible_from_activates(direction: TradeDirection) -> None:
    """B1-6, 7: eligible_from is inclusive."""
    recommendation = _mid_session(direction)
    first = _bar(_MID_ELIGIBLE, *_RANGES[direction]["entry"])

    lifecycle = _fold(recommendation, _bar(_at(6), *_RANGES[direction]["entry"]), first)

    assert lifecycle.status is Status.ACTIVE
    assert lifecycle.events[0].observation == first


@_DIRECTIONS
def test_b1_a_later_eligible_bar_closes_an_active_recommendation(
    direction: TradeDirection,
) -> None:
    """B1-8."""
    lifecycle = _fold(
        _mid_session(direction),
        _bar(_at(7), *_RANGES[direction]["entry"]),
        _bar(_at(8), *_RANGES[direction]["target"]),
    )

    assert lifecycle.status is Status.CLOSED_TARGET


def test_b1_a_bar_one_microsecond_before_eligible_from_is_ignored() -> None:
    recommendation = _mid_session(TradeDirection.LONG)
    lifecycle = FuturesTradeRecommendationLifecycle(recommendation)

    assert lifecycle.advance(_bar(_at(7, "09:59:59.999999"), *_L_ENTRY)) is lifecycle


def test_b1_an_ineligible_bar_is_not_consumed_and_does_not_block_later_bars() -> None:
    """Decision: ignored, not consumed -- it neither moves the cursor nor raises."""
    recommendation = _mid_session(TradeDirection.LONG)
    lifecycle = _fold(recommendation, _bar(_at(6), *_L_QUIET), _bar(_at(7), *_L_QUIET))

    assert lifecycle.last_observation == _bar(_at(7), *_L_QUIET)
    # An ineligible bar arriving after the cursor is still ignored, never refused.
    assert lifecycle.advance(_bar(_at(6), *_L_ENTRY)) is lifecycle


@_DIRECTIONS
def test_b1_eligible_from_equal_to_valid_through_evaluates_its_single_bar(
    direction: TradeDirection,
) -> None:
    """B1-11: the one eligible bar is evaluated, then the window has ended."""
    recommendation = _recommendation(direction, eligible_from=_at(8), valid_through=_at(8))

    activated = _fold(recommendation, _bar(_at(8), *_RANGES[direction]["entry"]))
    untouched = _fold(recommendation, _bar(_at(8), *_RANGES[direction]["quiet"]))

    assert activated.status is Status.EXPIRED_AFTER_ACTIVATION
    assert [event.kind for event in activated.events] == [
        Kind.ENTRY_ACTIVATED,
        Kind.VALIDITY_EXPIRED,
    ]
    assert untouched.status is Status.EXPIRED_BEFORE_ENTRY


@pytest.mark.parametrize(
    ("event_at", "last_at"),
    [(_at(6), _at(6)), (_at(7, "09:59:59"), _at(7, "09:59:59"))],
    ids=["same-session", "just-before"],
)
def test_b1_replay_cannot_bypass_eligibility_through_events(
    event_at: PointInTime, last_at: PointInTime
) -> None:
    """B1-12."""
    recommendation = _mid_session(TradeDirection.LONG)
    bar = _bar(event_at, *_L_ENTRY)
    forged = FuturesTradeRecommendationEvent(
        recommendation.identity,
        Kind.ENTRY_ACTIVATED,
        bar,
        (_ENTRY,),
        IntrabarOrdering.NOT_REQUIRED,
    )

    with pytest.raises(InvalidFuturesTradeRecommendationLifecycleError, match="first eligible"):
        FuturesTradeRecommendationLifecycle(recommendation, (forged,), _bar(last_at, *_L_ENTRY))


def test_b1_replay_cannot_bypass_eligibility_through_the_cursor() -> None:
    recommendation = _mid_session(TradeDirection.LONG)

    with pytest.raises(InvalidFuturesTradeRecommendationLifecycleError, match="first eligible"):
        FuturesTradeRecommendationLifecycle(recommendation, (), _bar(_at(6), *_L_QUIET))


# ===========================================================================
# B2 -- time-driven expiry
# ===========================================================================

_FINAL_DAY = _at(27)


def _to_cutoff(direction: TradeDirection = TradeDirection.LONG) -> FuturesTradeRecommendation:
    """Validity ends exactly at the contract cutoff, 15:30 IST on expiry day."""
    return _recommendation(direction, valid_through=_FINAL_DAY, contract_cutoff=_FINAL_DAY)


def _active_until_26(direction: TradeDirection = TradeDirection.LONG):
    ranges = _RANGES[direction]
    return _fold(
        _to_cutoff(direction),
        _bar(_at(6), *ranges["entry"]),
        _bar(_at(26), *ranges["quiet"]),
    )


@_DIRECTIONS
def test_b2_a_missing_final_bar_expires_with_incomplete_coverage(
    direction: TradeDirection,
) -> None:
    """B2-1, 3, 4: no bar at the cutoff; time expiry ends the recommendation."""
    lifecycle = _active_until_26(direction)
    expired = lifecycle.expire(_evidence(lifecycle, _at(28, "00:00:00")))

    assert expired.status is Status.EXPIRED_WITH_INCOMPLETE_COVERAGE
    assert expired.is_terminal
    event = expired.events[-1]
    assert event.kind is Kind.VALIDITY_EXPIRED_BY_TIME
    assert event.observation is None
    assert event.touched == ()
    assert event.expiry_reason is RecommendationExpiryReason.CONTRACT_CUTOFF_REACHED
    assert event.time_evidence.coverage is _INCOMPLETE
    assert event.time_evidence.deficiency is CoverageDeficiency.MISSING_OBSERVATIONS
    assert expired.last_observation == lifecycle.last_observation


@_DIRECTIONS
def test_b2_a_misaligned_final_bar_then_verified_expiry_is_a_normal_expiry(
    direction: TradeDirection,
) -> None:
    """B2-2, 5: the final bar completed before the cutoff; coverage is verified."""
    misaligned = _bar(_at(27, "09:00:00"), *_RANGES[direction]["quiet"])
    lifecycle = _active_until_26(direction).advance(misaligned)
    assert lifecycle.status is Status.ACTIVE

    expired = lifecycle.expire(_evidence(lifecycle, _FINAL_DAY, verified=True))

    assert expired.status is Status.EXPIRED_AFTER_ACTIVATION
    assert expired.events[-1].time_evidence.is_verified
    assert expired.events[-1].expiry_reason is RecommendationExpiryReason.CONTRACT_CUTOFF_REACHED


def test_b2_verified_time_expiry_while_waiting_is_expired_before_entry() -> None:
    recommendation = _recommendation(valid_through=_at(9, "12:00:00"))
    lifecycle = _fold(recommendation, _bar(_at(6), *_L_QUIET), _bar(_at(9), *_L_QUIET))

    expired = lifecycle.expire(_evidence(lifecycle, _at(10, "00:00:00"), verified=True))

    assert expired.status is Status.EXPIRED_BEFORE_ENTRY
    assert expired.events[-1].expiry_reason is RecommendationExpiryReason.VALIDITY_WINDOW_ENDED


def test_b2_incomplete_expiry_with_no_observation_at_all() -> None:
    lifecycle = FuturesTradeRecommendationLifecycle(_to_cutoff())

    expired = lifecycle.expire(_evidence(lifecycle, _at(28, "00:00:00")))

    assert expired.status is Status.EXPIRED_WITH_INCOMPLETE_COVERAGE
    assert expired.events[-1].time_evidence.evaluated_through is None


def test_b2_expiry_before_valid_through_changes_nothing() -> None:
    """B2-6: never premature."""
    lifecycle = _active_until_26()

    assert lifecycle.expire(_evidence(lifecycle, _at(27, "09:59:59.999999"))) is lifecycle
    assert lifecycle.expire(_evidence(lifecycle, _at(26, "12:00:00"), verified=True)) is lifecycle


@pytest.mark.parametrize("as_of", [_FINAL_DAY, _at(30, "00:00:00")], ids=["at", "after"])
def test_b2_expiry_at_or_after_valid_through_expires(as_of: PointInTime) -> None:
    """B2-7, 8."""
    lifecycle = _active_until_26()

    assert lifecycle.expire(_evidence(lifecycle, as_of)).is_terminal


def test_b2_repeated_expiry_is_idempotent() -> None:
    """B2-9: even with different evidence, a terminal lifecycle never changes."""
    lifecycle = _active_until_26()
    expired = lifecycle.expire(_evidence(lifecycle, _at(28, "00:00:00")))

    assert expired.expire(_evidence(lifecycle, _at(28, "00:00:00"))) is expired
    assert expired.expire(_evidence(lifecycle, _at(29, "00:00:00"), verified=True)) is expired
    assert len(expired.events) == 2


@pytest.mark.parametrize(
    ("bars", "status"),
    [
        (((6, "entry"), (7, "target")), Status.CLOSED_TARGET),
        (((6, "entry"), (7, "stop")), Status.CLOSED_STOP),
        (((6, "entry_stop"),), Status.INDETERMINATE_ENTRY),
        (((6, "entry"), (28, "quiet")), Status.EXPIRED_AFTER_ACTIVATION),
    ],
    ids=["closed-target", "closed-stop", "indeterminate", "expired"],
)
def test_b2_expiry_never_changes_a_terminal_lifecycle(
    bars: tuple[tuple[int, str], ...], status: RecommendationStatus
) -> None:
    """B2-10..13."""
    recommendation = _to_cutoff()
    terminal = _fold(recommendation, *(_bar(_at(day), *_L_RANGES[shape]) for day, shape in bars))
    assert terminal.status is status

    assert terminal.expire(_evidence(terminal, _at(30, "00:00:00"))) is terminal
    assert terminal.expire(_evidence(terminal, _at(30, "00:00:00"), verified=True)) is terminal


def test_b2_evidence_must_describe_the_evaluated_history() -> None:
    """A verified claim cannot contradict what the lifecycle actually evaluated."""
    lifecycle = _active_until_26()
    stale = TimeExpiryEvidence(
        as_of=_at(28, "00:00:00"),
        evaluated_through=_at(6),
        coverage=_VERIFIED,
        attested_by="synthetic-test-coverage",
    )
    missing = TimeExpiryEvidence(
        as_of=_at(28, "00:00:00"),
        evaluated_through=None,
        coverage=_INCOMPLETE,
        attested_by="synthetic-test-coverage",
        deficiency=CoverageDeficiency.UNVERIFIED_OBSERVATIONS,
    )

    for evidence in (stale, missing):
        with pytest.raises(InvalidFuturesTradeRecommendationExpiryError, match="does not match"):
            lifecycle.expire(evidence)


def test_b2_evidence_is_checked_even_when_premature() -> None:
    lifecycle = _active_until_26()
    wrong = TimeExpiryEvidence(
        as_of=_at(10),
        evaluated_through=_at(9),
        coverage=_INCOMPLETE,
        attested_by="synthetic-test-coverage",
        deficiency=CoverageDeficiency.MISSING_OBSERVATIONS,
    )

    with pytest.raises(InvalidFuturesTradeRecommendationExpiryError):
        lifecycle.expire(wrong)


@pytest.mark.parametrize("value", [None, _FINAL_DAY, "evidence"])
def test_b2_only_time_expiry_evidence_can_expire(value: object) -> None:
    with pytest.raises(InvalidFuturesTradeRecommendationExpiryError, match="TimeExpiryEvidence"):
        _active_until_26().expire(value)  # type: ignore[arg-type]


@pytest.mark.parametrize("shape", ["target", "stop", "both", "entry"])
def test_b2_a_late_bar_never_reopens_or_reclassifies_a_time_expiry(shape: str) -> None:
    """The validity-end bar arriving after time expiry changes nothing."""
    lifecycle = _active_until_26()
    expired = lifecycle.expire(_evidence(lifecycle, _at(28, "00:00:00")))

    assert expired.advance(_bar(_FINAL_DAY, *_L_RANGES[shape])) is expired
    assert expired.status is Status.EXPIRED_WITH_INCOMPLETE_COVERAGE


def test_b2_a_late_bar_earlier_than_the_cursor_is_still_refused() -> None:
    lifecycle = _active_until_26()
    expired = lifecycle.expire(_evidence(lifecycle, _at(28, "00:00:00")))

    with pytest.raises(InvalidFuturesTradeRecommendationObservationError, match="earlier"):
        expired.advance(_bar(_at(20), *_L_QUIET))


def test_b2_a_validity_end_bar_that_is_present_is_evaluated_before_any_time_expiry() -> None:
    """Its prices are never discarded: the bar closes the recommendation itself."""
    lifecycle = _active_until_26().advance(_bar(_FINAL_DAY, *_L_TARGET))

    assert lifecycle.status is Status.CLOSED_TARGET
    assert lifecycle.expire(_evidence(lifecycle, _at(28, "00:00:00"), verified=True)) is lifecycle


def test_b2_incomplete_expiry_is_never_a_verified_outcome() -> None:
    """B2-16: F-6 can exclude it by status and by its event evidence."""
    for direction in TradeDirection:
        lifecycle = _active_until_26(direction)
        for deficiency in CoverageDeficiency:
            expired = lifecycle.expire(
                _evidence(lifecycle, _at(28, "00:00:00"), deficiency=deficiency)
            )
            assert expired.status not in _VERIFIED_OUTCOMES
            assert not expired.events[-1].time_evidence.is_verified
            assert expired.events[-1].kind is not Kind.STOP_REACHED
            assert expired.events[-1].kind is not Kind.TARGET_REACHED


# -- B2-14, 15: reconstruction and forged time histories ---------------------------


def _expired_parts():
    lifecycle = _active_until_26()
    expired = lifecycle.expire(_evidence(lifecycle, _at(28, "00:00:00")))
    return expired.recommendation, expired.events, expired.last_observation


def test_b2_a_time_expiry_is_reconstructed_from_its_parts() -> None:
    recommendation, events, last = _expired_parts()

    rebuilt = FuturesTradeRecommendationLifecycle(recommendation, events, last)

    assert rebuilt.status is Status.EXPIRED_WITH_INCOMPLETE_COVERAGE
    assert rebuilt == FuturesTradeRecommendationLifecycle(recommendation, events, last)


def _time_event(
    recommendation: FuturesTradeRecommendation,
    evidence: TimeExpiryEvidence,
    reason: RecommendationExpiryReason = RecommendationExpiryReason.CONTRACT_CUTOFF_REACHED,
    identity: FuturesTradeRecommendationIdentity | None = None,
) -> FuturesTradeRecommendationEvent:
    return FuturesTradeRecommendationEvent(
        identity or recommendation.identity,
        Kind.VALIDITY_EXPIRED_BY_TIME,
        None,
        (),
        IntrabarOrdering.NOT_REQUIRED,
        reason,
        evidence,
    )


def test_b2_a_time_expiry_must_be_the_last_event() -> None:
    recommendation, events, last = _expired_parts()
    activation, time_expiry = events

    with pytest.raises(InvalidFuturesTradeRecommendationLifecycleError, match="last event"):
        FuturesTradeRecommendationLifecycle(recommendation, (time_expiry, activation), last)


def test_b2_two_time_expiries_are_rejected() -> None:
    recommendation, events, last = _expired_parts()

    with pytest.raises(InvalidFuturesTradeRecommendationLifecycleError):
        FuturesTradeRecommendationLifecycle(recommendation, (*events, events[-1]), last)


def test_b2_a_premature_time_expiry_is_rejected() -> None:
    recommendation, events, last = _expired_parts()
    premature = _time_event(recommendation, _evidence_for(last, _at(27, "09:00:00")))

    with pytest.raises(InvalidFuturesTradeRecommendationLifecycleError, match="before validity"):
        FuturesTradeRecommendationLifecycle(recommendation, (events[0], premature), last)


def _evidence_for(last: FuturesOHLCVBar | None, as_of: PointInTime) -> TimeExpiryEvidence:
    return TimeExpiryEvidence(
        as_of=as_of,
        evaluated_through=None if last is None else last.point_in_time,
        coverage=_INCOMPLETE,
        attested_by="synthetic-test-coverage",
        deficiency=CoverageDeficiency.MISSING_OBSERVATIONS,
    )


def test_b2_time_evidence_contradicting_the_cursor_is_rejected() -> None:
    recommendation, events, last = _expired_parts()
    contradicting = TimeExpiryEvidence(
        as_of=_at(28, "00:00:00"),
        evaluated_through=_at(6),
        coverage=_VERIFIED,
        attested_by="synthetic-test-coverage",
    )

    with pytest.raises(InvalidFuturesTradeRecommendationLifecycleError, match="does not match"):
        FuturesTradeRecommendationLifecycle(
            recommendation, (events[0], _time_event(recommendation, contradicting)), last
        )


def test_b2_a_wrong_time_expiry_reason_is_rejected() -> None:
    recommendation, events, last = _expired_parts()
    wrong = _time_event(
        recommendation,
        events[-1].time_evidence,
        reason=RecommendationExpiryReason.VALIDITY_WINDOW_ENDED,
    )

    with pytest.raises(InvalidFuturesTradeRecommendationLifecycleError, match="not what"):
        FuturesTradeRecommendationLifecycle(recommendation, (events[0], wrong), last)


def test_b2_a_time_expiry_after_a_terminal_event_is_rejected() -> None:
    recommendation = _to_cutoff()
    closed = _fold(recommendation, _bar(_at(6), *_L_ENTRY), _bar(_at(7), *_L_TARGET))
    after = _time_event(recommendation, _evidence_for(closed.last_observation, _at(28)))

    with pytest.raises(InvalidFuturesTradeRecommendationLifecycleError, match="terminal"):
        FuturesTradeRecommendationLifecycle(
            recommendation, (*closed.events, after), closed.last_observation
        )


def test_b2_a_time_expiry_of_another_recommendation_is_rejected() -> None:
    recommendation, events, last = _expired_parts()
    foreign = _time_event(
        recommendation,
        events[-1].time_evidence,
        identity=FuturesTradeRecommendationIdentity("rec-other"),
    )

    with pytest.raises(InvalidFuturesTradeRecommendationLifecycleError, match="belong"):
        FuturesTradeRecommendationLifecycle(recommendation, (events[0], foreign), last)


def test_b2_a_time_expiry_cannot_hide_an_unrecorded_activation() -> None:
    """The cursor still has to be consistent with the bar events before expiry."""
    recommendation = _to_cutoff()
    entry_bar = _bar(_at(6), *_L_ENTRY)
    hidden = _time_event(
        recommendation,
        _evidence_for(entry_bar, _at(28)),
    )

    with pytest.raises(InvalidFuturesTradeRecommendationLifecycleError, match="unrecorded"):
        FuturesTradeRecommendationLifecycle(recommendation, (hidden,), entry_bar)


# ===========================================================================
# L-3 preservation under the corrected eligibility window
# ===========================================================================


@_DIRECTIONS
def test_l3_normal_entry_activates_without_closing(direction: TradeDirection) -> None:
    lifecycle = _fold(_mid_session(direction), _bar(_at(7), *_RANGES[direction]["entry"]))

    assert lifecycle.status is Status.ACTIVE
    assert [event.kind for event in lifecycle.events] == [Kind.ENTRY_ACTIVATED]


@_DIRECTIONS
@pytest.mark.parametrize(
    ("shape", "touched"),
    [
        ("entry_stop", (_ENTRY, _STOP)),
        ("entry_target", (_ENTRY, _TARGET)),
        ("both", (_ENTRY, _STOP, _TARGET)),
    ],
)
def test_l3_ambiguous_entry_is_indeterminate_with_unknown_ordering(
    direction: TradeDirection, shape: str, touched: tuple[RecommendationBoundary, ...]
) -> None:
    lifecycle = _fold(_mid_session(direction), _bar(_at(7), *_RANGES[direction][shape]))

    assert lifecycle.status is Status.INDETERMINATE_ENTRY
    (event,) = lifecycle.events
    assert event.touched == touched
    assert event.ordering is IntrabarOrdering.UNKNOWN


@_DIRECTIONS
def test_l3_active_both_touch_is_modeled_stop_first(direction: TradeDirection) -> None:
    lifecycle = _fold(
        _mid_session(direction),
        _bar(_at(7), *_RANGES[direction]["entry"]),
        _bar(_at(8), *_RANGES[direction]["both"]),
    )

    assert lifecycle.status is Status.CLOSED_STOP
    assert lifecycle.events[-1].ordering is IntrabarOrdering.MODELED_STOP_FIRST


@_DIRECTIONS
@pytest.mark.parametrize("gap", ["gap_far", "gap_near"])
def test_l3_a_bar_entirely_outside_the_zone_never_activates(
    direction: TradeDirection, gap: str
) -> None:
    """Even on the economically favorable side: zone touch, not limit-order fill."""
    lifecycle = _fold(_mid_session(direction), _bar(_at(7), *_RANGES[direction][gap]))

    assert lifecycle.status is Status.WAITING_FOR_ENTRY
    assert lifecycle.events == ()


@_DIRECTIONS
def test_l3_no_same_bar_exit_after_a_normal_activation(direction: TradeDirection) -> None:
    lifecycle = _fold(_mid_session(direction), _bar(_at(7), *_RANGES[direction]["entry"]))

    assert len(lifecycle.events) == 1
    assert lifecycle.events[0].kind is Kind.ENTRY_ACTIVATED
