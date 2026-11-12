"""EI-5B: the equity recommendation lifecycle's transitions, from synthetic evidence.

Every value is synthetic. The window is the EI-5 Decision Register's example:
entry zone [100.00, 100.50], stop 99.00, target 103.00; ``eligible_from`` 09:45,
latest entry-bar opening 11:00, entry window end 11:05, modeled exit 15:00 IST.
None is an approved cutoff or price, and the 09:15 to 15:00 IST research window
is not a trading authorization. Scenario identifiers refer to the EI-5 design
acceptance matrix; only rows owned by EI-5B are claimed here.
"""

from __future__ import annotations

from dataclasses import fields
from datetime import datetime, timedelta
from decimal import Decimal
from itertools import combinations_with_replacement

import pytest

from northstar_core.foundation.value_objects import Currency, PointInTime, Price
from northstar_core.recommendations.equity import EquityEntryZone, EquityRecommendationLevels
from northstar_core.recommendations.equity.lifecycle import (
    EquityEvidenceDeficiency,
    EquityEvidenceDeficiencyKind,
    EquityIntrabarOrdering,
    EquityLifecycleAdvance,
    EquityLifecycleAdvanceStatus,
    EquityLifecycleCancellationReason,
    EquityLifecycleEvent,
    EquityLifecycleEventKind,
    EquityLifecycleEvidence,
    EquityLifecycleInterval,
    EquityLifecycleIntervalOutcome,
    EquityLifecycleLevel,
    EquityLifecycleObservation,
    EquityLifecycleOutcomeClass,
    EquityLifecycleState,
    EquityLifecycleWindow,
    EquityRecommendationLifecycle,
    EquityRevisionMateriality,
    InvalidEquityLifecycleEventError,
    InvalidEquityLifecycleObservationError,
    InvalidEquityRecommendationLifecycleError,
)

K = EquityLifecycleEventKind
S = EquityLifecycleState
L = EquityLifecycleLevel
Outcome = EquityLifecycleIntervalOutcome
Status = EquityLifecycleAdvanceStatus

_INR = Currency("INR")
_DAY = "2026-11-02"
_NEXT_DAY = "2026-11-03"
_REF = "ecs1-sha256:synthetic-snapshot"
_QUIET = ("100.80", "101.20")  # above the zone, below the target: touches nothing


def _p(amount: str) -> Price:
    return Price(Decimal(amount), _INR)


def _t(clock: str, day: str = _DAY) -> PointInTime:
    if len(clock) == 5:
        clock = f"{clock}:00"
    return PointInTime(f"{day}T{clock}+05:30")


def _clock(value: datetime) -> str:
    return value.strftime("%H:%M")


def _openings(start: str, end: str = "15:00") -> list[str]:
    current = datetime.strptime(start, "%H:%M")
    stop = datetime.strptime(end, "%H:%M")
    found = []
    while current < stop:
        found.append(_clock(current))
        current += timedelta(minutes=5)
    return found


def _plus5(clock: str) -> str:
    return _clock(datetime.strptime(clock, "%H:%M") + timedelta(minutes=5))


_LEVELS = EquityRecommendationLevels(
    EquityEntryZone(_p("100.00"), _p("100.50")), _p("99.00"), _p("103.00")
)
_WINDOW = EquityLifecycleWindow(_LEVELS, _t("09:45"), _t("11:00"), _t("11:05"), _t("15:00"))

Spec = tuple[str, str] | EquityLifecycleIntervalOutcome


def _interval(
    opening: str, at: PointInTime, spec: Spec | None, day: str = _DAY
) -> EquityLifecycleInterval:
    opens, closes = _t(opening, day), _t(_plus5(opening), day)
    if spec is None:
        position = closes.compare(at)
        if position > 0:
            return EquityLifecycleInterval(opens, closes, Outcome.NOT_ENDED)
        if position == 0:
            return EquityLifecycleInterval(opens, closes, Outcome.UNFINALIZED)
        spec = _QUIET
    if isinstance(spec, EquityLifecycleIntervalOutcome):
        return EquityLifecycleInterval(opens, closes, spec)
    low, high = spec
    return EquityLifecycleInterval(
        opens, closes, Outcome.ACCEPTABLE, _p(low), _p(high), (f"obs-{opening}",)
    )


def _obs(
    at: str,
    start: str = "09:45",
    bars: dict[str, Spec] | None = None,
    ref: str = _REF,
    end: str = "15:00",
    day: str = _DAY,
) -> EquityLifecycleObservation:
    instant = _t(at)
    bars = bars or {}
    intervals = tuple(_interval(o, instant, bars.get(o), day) for o in _openings(start, end))
    return EquityLifecycleObservation(instant, ref, intervals)


def _new(window: EquityLifecycleWindow = _WINDOW) -> EquityRecommendationLifecycle:
    return EquityRecommendationLifecycle(window)


def _waiting() -> EquityRecommendationLifecycle:
    result = _new().advance(_obs("09:46:10"))
    assert result.lifecycle.state is S.WAITING_FOR_ENTRY
    return result.lifecycle


def _active() -> EquityRecommendationLifecycle:
    """Activated on the bar 10:00-10:05; the cursor is 10:05."""
    result = _new().advance(_obs("10:06", bars={"10:00": ("100.10", "100.60")}))
    assert result.lifecycle.state is S.ACTIVE
    assert result.lifecycle.cursor == _t("10:05")
    return result.lifecycle


def _after_waiting(bars: dict[str, Spec], at: str = "15:10") -> EquityLifecycleAdvance:
    return _waiting().advance(_obs(at, bars=bars))


def _after_active(bars: dict[str, Spec], at: str = "15:10") -> EquityLifecycleAdvance:
    return _active().advance(_obs(at, start="10:05", bars=bars))


def _kinds(result: EquityLifecycleAdvance) -> list[EquityLifecycleEventKind]:
    return [event.kind for event in result.events]


# ---------------------------------------------------------------------------
# Group A -- state-machine integrity
# ---------------------------------------------------------------------------


def test_lt01_a_recorded_lifecycle_opens_its_entry_window_at_eligible_from() -> None:
    lifecycle = _new()
    assert lifecycle.state is S.RECORDED and lifecycle.events == ()
    assert lifecycle.cursor == _t("09:45") and lifecycle.last_evaluated_at is None

    result = lifecycle.advance(_obs("09:46:10"))

    assert _kinds(result) == [K.ENTRY_WINDOW_OPENED]
    event = result.events[0]
    assert (event.from_state, event.to_state) == (S.RECORDED, S.WAITING_FOR_ENTRY)
    assert event.evaluated_at == _t("09:46:10")
    assert event.evidence == EquityLifecycleEvidence(_REF, _t("09:45"), _t("09:50"))
    assert result.status is Status.AWAITING_EVIDENCE
    assert result.halted_at is not None and result.halted_at.opens_at == _t("09:45")


def test_before_eligible_from_a_recorded_lifecycle_does_not_change() -> None:
    lifecycle = _new()
    result = lifecycle.advance(_obs("09:44:59"))
    assert result.status is Status.NOT_YET_ELIGIBLE
    assert result.events == () and result.lifecycle == lifecycle


def test_lt02_a_bar_inside_the_zone_alone_activates() -> None:
    result = _after_waiting({"10:00": ("100.10", "100.60")}, at="10:06")
    assert _kinds(result) == [K.ENTRY_ACTIVATED]
    event = result.events[0]
    assert event.touched == (L.ENTRY,)
    assert event.ordering is EquityIntrabarOrdering.NOT_REQUIRED
    assert event.evidence == EquityLifecycleEvidence(_REF, _t("10:00"), _t("10:05"), ("obs-10:00",))
    assert result.lifecycle.state is S.ACTIVE and result.status is Status.AWAITING_EVIDENCE


@pytest.mark.parametrize(
    ("bar", "touched"),
    [
        (("98.90", "100.20"), (L.ENTRY, L.STOP)),  # LT-03, AM-01: the EI4-D5 clarification
        (("100.40", "103.20"), (L.ENTRY, L.TARGET)),  # LT-04
        (("98.80", "103.30"), (L.ENTRY, L.STOP, L.TARGET)),  # LT-05
    ],
    ids=["entry-and-stop", "entry-and-target", "entry-stop-and-target"],
)
def test_lt03_to_lt05_an_ambiguous_entry_bar_is_indeterminate(
    bar: tuple[str, str], touched: tuple[EquityLifecycleLevel, ...]
) -> None:
    result = _after_waiting({"09:50": bar})
    assert _kinds(result) == [K.ENTRY_INDETERMINATE]
    event = result.events[0]
    assert event.touched == touched
    assert event.ordering is EquityIntrabarOrdering.UNKNOWN
    assert result.lifecycle.state is S.INDETERMINATE_ENTRY
    assert result.lifecycle.state.outcome_class is EquityLifecycleOutcomeClass.INDETERMINATE


def test_lt06_a_stop_only_touch_while_waiting_cancels_before_entry() -> None:
    result = _after_waiting({"09:50": ("98.95", "99.80")})
    assert _kinds(result) == [K.ENTRY_CANCELLED]
    event = result.events[0]
    assert event.touched == (L.STOP,)
    assert event.reason is EquityLifecycleCancellationReason.STOP_TOUCHED_BEFORE_ENTRY
    assert result.lifecycle.state is S.CANCELLED_BEFORE_ENTRY
    assert result.lifecycle.state.outcome_class is EquityLifecycleOutcomeClass.RESOLVED_NO_ENTRY


def test_lt07_a_complete_untouched_entry_window_expires_on_the_last_entry_bar() -> None:
    result = _after_waiting({})
    assert _kinds(result) == [K.ENTRY_WINDOW_EXPIRED]
    event = result.events[0]
    assert event.evidence.opens_at == _t("11:00") and event.evidence.closes_at == _t("11:05")
    assert event.touched == ()
    assert result.lifecycle.state is S.EXPIRED_BEFORE_ENTRY


def test_lt08_a_waiting_deficiency_at_the_entry_window_end_is_incomplete_evidence() -> None:
    result = _after_waiting({"10:30": Outcome.MISSING}, at="11:06")
    assert _kinds(result) == [K.EVIDENCE_INCOMPLETE]
    event = result.events[0]
    assert event.deficiencies == (
        EquityEvidenceDeficiency(_t("10:30"), _t("10:35"), EquityEvidenceDeficiencyKind.MISSING),
    )
    assert result.lifecycle.state is S.INCOMPLETE_EVIDENCE
    assert result.lifecycle.state.outcome_class is EquityLifecycleOutcomeClass.UNRESOLVED


@pytest.mark.parametrize(
    "bar", [("101.00", "103.00"), ("103.50", "104.00")], ids=["touch", "gap-through"]
)
def test_lt09_an_active_target_reach_closes_at_the_target(bar: tuple[str, str]) -> None:
    result = _after_active({"11:15": bar})
    assert _kinds(result) == [K.TARGET_REACHED]
    assert result.events[0].touched == (L.TARGET,)
    assert result.lifecycle.state is S.CLOSED_TARGET


@pytest.mark.parametrize(
    "bar", [("99.00", "100.20"), ("98.00", "98.50")], ids=["touch", "gap-through"]
)
def test_lt10_an_active_stop_reach_closes_at_the_stop(bar: tuple[str, str]) -> None:
    result = _after_active({"11:15": bar})
    assert _kinds(result) == [K.STOP_REACHED]
    assert result.events[0].touched == (L.STOP,)
    assert result.lifecycle.state is S.CLOSED_STOP


def test_lt11_ei0_d9_example_a_stop_and_target_bar_is_indeterminate_exit() -> None:
    result = _after_active({"10:15": ("98.90", "103.10")})
    assert _kinds(result) == [K.EXIT_INDETERMINATE]
    event = result.events[0]
    assert event.touched == (L.STOP, L.TARGET)
    assert event.ordering is EquityIntrabarOrdering.UNKNOWN
    assert result.lifecycle.state is S.INDETERMINATE_EXIT


def test_lt12_complete_active_coverage_without_a_reach_is_session_cutoff() -> None:
    result = _after_active({})
    assert _kinds(result) == [K.SESSION_CUTOFF_REACHED]
    event = result.events[0]
    assert event.evidence.opens_at == _t("14:55") and event.evidence.closes_at == _t("15:00")
    assert result.lifecycle.state is S.SESSION_CUTOFF_REACHED
    assert result.lifecycle.state.outcome_class is EquityLifecycleOutcomeClass.UNRESOLVED


def test_lt13_an_active_deficiency_at_the_exit_boundary_is_incomplete_evidence() -> None:
    result = _after_active({"13:15": Outcome.MISSING}, at="15:02")
    assert _kinds(result) == [K.EVIDENCE_INCOMPLETE]
    assert result.events[0].deficiencies == (
        EquityEvidenceDeficiency(_t("13:15"), _t("13:20"), EquityEvidenceDeficiencyKind.MISSING),
    )
    assert result.lifecycle.state is S.INCOMPLETE_EVIDENCE


def _event(
    sequence: int,
    kind: EquityLifecycleEventKind,
    from_state: EquityLifecycleState,
    to_state: EquityLifecycleState,
    opening: str,
    at: str = "15:10",
    touched: tuple[EquityLifecycleLevel, ...] = (),
    observations: tuple[str, ...] = ("obs",),
    **extra: object,
) -> EquityLifecycleEvent:
    evidence = EquityLifecycleEvidence(_REF, _t(opening), _t(_plus5(opening)), observations)
    return EquityLifecycleEvent(
        sequence, kind, from_state, to_state, _t(at), evidence, touched, **extra
    )


_OPENED = _event(1, K.ENTRY_WINDOW_OPENED, S.RECORDED, S.WAITING_FOR_ENTRY, "09:45", "09:46",
                 observations=())  # fmt: skip
_ACTIVATED = _event(2, K.ENTRY_ACTIVATED, S.WAITING_FOR_ENTRY, S.ACTIVE, "10:00", "10:06",
                    (L.ENTRY,))  # fmt: skip


def test_ft01_ft02_a_recorded_lifecycle_cannot_skip_the_entry_window() -> None:
    with pytest.raises(InvalidEquityLifecycleEventError):
        _event(1, K.ENTRY_ACTIVATED, S.RECORDED, S.ACTIVE, "10:00", touched=(L.ENTRY,))
    with pytest.raises(InvalidEquityLifecycleEventError):
        _event(1, K.STOP_REACHED, S.RECORDED, S.CLOSED_STOP, "10:00", touched=(L.STOP,))
    with pytest.raises(InvalidEquityLifecycleEventError):
        _event(1, K.ENTRY_WINDOW_OPENED, S.RECORDED, S.ACTIVE, "09:45", observations=())


def test_ft03_a_waiting_lifecycle_cannot_take_an_exit_transition() -> None:
    for kind, target, touched in (
        (K.TARGET_REACHED, S.CLOSED_TARGET, (L.TARGET,)),
        (K.STOP_REACHED, S.CLOSED_STOP, (L.STOP,)),
        (K.EXIT_INDETERMINATE, S.INDETERMINATE_EXIT, (L.STOP, L.TARGET)),
        (K.SESSION_CUTOFF_REACHED, S.SESSION_CUTOFF_REACHED, ()),
    ):
        with pytest.raises(InvalidEquityLifecycleEventError):
            _event(2, kind, S.WAITING_FOR_ENTRY, target, "10:00", touched=touched)


def test_ft04_ft05_an_active_lifecycle_cannot_go_back_or_take_an_entry_outcome() -> None:
    with pytest.raises(InvalidEquityLifecycleEventError):
        _event(3, K.ENTRY_WINDOW_OPENED, S.ACTIVE, S.WAITING_FOR_ENTRY, "10:05", observations=())
    for kind, target, touched in (
        (K.ENTRY_WINDOW_EXPIRED, S.EXPIRED_BEFORE_ENTRY, ()),
        (K.ENTRY_INDETERMINATE, S.INDETERMINATE_ENTRY, (L.ENTRY, L.STOP)),
    ):
        with pytest.raises(InvalidEquityLifecycleEventError):
            _event(3, kind, S.ACTIVE, target, "10:05", touched=touched)
    with pytest.raises(InvalidEquityLifecycleEventError):
        _event(
            3,
            K.ENTRY_CANCELLED,
            S.ACTIVE,
            S.CANCELLED_BEFORE_ENTRY,
            "10:05",
            touched=(L.STOP,),
            reason=EquityLifecycleCancellationReason.STOP_TOUCHED_BEFORE_ENTRY,
        )
    # A well-formed event that leaves a state the lifecycle is not in is refused on replay.
    stale = _event(3, K.ENTRY_ACTIVATED, S.WAITING_FOR_ENTRY, S.ACTIVE, "10:05", "10:11",
                   (L.ENTRY,))  # fmt: skip
    with pytest.raises(InvalidEquityRecommendationLifecycleError):
        EquityRecommendationLifecycle(_WINDOW, (_OPENED, _ACTIVATED, stale))


def _terminal_lifecycles() -> dict[EquityLifecycleState, EquityRecommendationLifecycle]:
    found = {
        S.CLOSED_TARGET: _after_active({"11:15": ("101.00", "103.00")}),
        S.CLOSED_STOP: _after_active({"11:15": ("98.00", "98.50")}),
        S.INDETERMINATE_EXIT: _after_active({"11:15": ("98.90", "103.10")}),
        S.SESSION_CUTOFF_REACHED: _after_active({}),
        S.EXPIRED_BEFORE_ENTRY: _after_waiting({}),
        S.CANCELLED_BEFORE_ENTRY: _after_waiting({"09:50": ("98.00", "98.50")}),
        S.INDETERMINATE_ENTRY: _after_waiting({"09:50": ("98.90", "100.20")}),
        S.INCOMPLETE_EVIDENCE: _after_waiting({"10:30": Outcome.MISSING}),
    }
    return {state: result.lifecycle for state, result in found.items()}


_TERMINALS = _terminal_lifecycles()


def test_every_terminal_state_is_covered() -> None:
    assert set(_TERMINALS) == {state for state in S if state.is_terminal}
    for state, lifecycle in _TERMINALS.items():
        assert lifecycle.state is state and lifecycle.is_terminal and lifecycle.cursor is None


@pytest.mark.parametrize("state", sorted(_TERMINALS), ids=str)
def test_ft06_a_terminal_lifecycle_is_frozen(state: EquityLifecycleState) -> None:
    lifecycle = _TERMINALS[state]
    later = EquityLifecycleObservation(
        _t("16:00"),
        "ecs1-sha256:later",
        (EquityLifecycleInterval(_t("10:00"), _t("10:05"), Outcome.MISSING),),
    )
    result = lifecycle.advance(later)
    assert result.status is Status.TERMINAL
    assert result.events == () and result.lifecycle == lifecycle
    sequence = len(lifecycle.events) + 1
    for event in (
        _event(
            sequence, K.ENTRY_ACTIVATED, S.WAITING_FOR_ENTRY, S.ACTIVE, "10:40", "16:00", (L.ENTRY,)
        ),  # fmt: skip
        _event(sequence, K.STOP_REACHED, S.ACTIVE, S.CLOSED_STOP, "14:00", "16:00", (L.STOP,)),
    ):
        with pytest.raises(InvalidEquityRecommendationLifecycleError, match="is terminal"):
            EquityRecommendationLifecycle(_WINDOW, lifecycle.events + (event,))


def test_repeated_equivalent_evaluation_never_fabricates_an_event() -> None:
    waiting = _waiting()
    observation = _obs("10:31")
    first, second = waiting.advance(observation), waiting.advance(observation)
    assert first == second and first.events == ()
    again = first.lifecycle.advance(observation)
    assert again.events == () and again.lifecycle == waiting

    active = _active()
    observation = _obs("12:01", start="10:05")
    once = active.advance(observation)
    assert once.events == () and once.lifecycle.advance(observation) == once


def test_replaying_an_advanced_history_reproduces_the_same_lifecycle() -> None:
    result = _after_active({"11:15": ("101.00", "103.00")})
    replayed = EquityRecommendationLifecycle(_WINDOW, result.lifecycle.events)
    assert replayed == result.lifecycle
    assert replayed.state is S.CLOSED_TARGET
    assert [e.sequence for e in replayed.events] == [1, 2, 3]


# ---------------------------------------------------------------------------
# Group B -- entry eligibility (EI5-D6)
# ---------------------------------------------------------------------------


def test_ew02_the_first_eligible_bar_can_activate() -> None:
    result = _new().advance(_obs("09:51", bars={"09:45": ("100.00", "100.20")}))
    assert _kinds(result) == [K.ENTRY_WINDOW_OPENED, K.ENTRY_ACTIVATED]
    assert result.events[1].evidence.opens_at == _t("09:45")


def test_ew03_the_last_eligible_bar_can_activate() -> None:
    result = _after_waiting({"11:00": ("100.30", "100.70")}, at="11:06")
    assert _kinds(result) == [K.ENTRY_ACTIVATED]
    assert result.events[0].evidence.opens_at == _t("11:00")
    assert result.lifecycle.cursor == _t("11:05")


def test_ew01_a_bar_opening_before_eligible_from_is_never_evaluated() -> None:
    early = _obs("10:00", start="09:40", bars={"09:40": ("100.10", "100.30")})
    with pytest.raises(InvalidEquityLifecycleObservationError, match="cursor"):
        _new().advance(early)
    with pytest.raises(InvalidEquityRecommendationLifecycleError):
        EquityRecommendationLifecycle(
            _WINDOW,
            (
                _OPENED,
                _event(
                    2,
                    K.ENTRY_ACTIVATED,
                    S.WAITING_FOR_ENTRY,
                    S.ACTIVE,
                    "09:40",
                    "09:50",
                    (L.ENTRY,),
                ),
            ),  # fmt: skip
        )


def test_ew04_a_bar_opening_after_the_last_entry_opening_never_activates() -> None:
    result = _after_waiting({"11:05": ("100.10", "100.30")})
    assert _kinds(result) == [K.ENTRY_WINDOW_EXPIRED]
    assert result.events[0].evidence.opens_at == _t("11:00")
    with pytest.raises(InvalidEquityRecommendationLifecycleError):
        EquityRecommendationLifecycle(
            _WINDOW,
            (
                _OPENED,
                _event(
                    2,
                    K.ENTRY_ACTIVATED,
                    S.WAITING_FOR_ENTRY,
                    S.ACTIVE,
                    "11:05",
                    "11:11",
                    (L.ENTRY,),
                ),
            ),  # fmt: skip
        )


@pytest.mark.parametrize(
    "bar",
    [("100.40", "100.60"), ("99.50", "100.00"), ("100.50", "100.90"), ("100.10", "100.40")],
    ids=["overlaps-top", "high-equals-zone-low", "low-equals-zone-high", "inside"],
)
def test_a_range_intersecting_the_zone_activates(bar: tuple[str, str]) -> None:
    result = _after_waiting({"10:00": bar}, at="10:06")
    assert _kinds(result) == [K.ENTRY_ACTIVATED]


@pytest.mark.parametrize(
    "bar",
    [("100.51", "101.20"), ("99.20", "99.99")],
    ids=["wholly-above-the-zone", "wholly-below-the-zone-above-the-stop"],
)
def test_pe02_a_range_missing_the_zone_never_activates_and_no_gap_entry_is_invented(
    bar: tuple[str, str],
) -> None:
    result = _after_waiting({"10:00": bar}, at="10:06")
    assert result.events == () and result.lifecycle.state is S.WAITING_FOR_ENTRY


def test_pe02_a_target_reach_above_the_zone_while_waiting_activates_nothing() -> None:
    result = _after_waiting({"10:00": ("103.50", "104.00")}, at="10:06")
    assert result.events == () and result.lifecycle.state is S.WAITING_FOR_ENTRY


def test_the_last_entry_bar_not_yet_ended_does_not_expire() -> None:
    result = _after_waiting({}, at="11:04")
    assert result.events == () and result.status is Status.AWAITING_EVIDENCE
    assert result.halted_at is not None and result.halted_at.opens_at == _t("11:00")


# ---------------------------------------------------------------------------
# Group C -- pre-entry invalidation (EI4-D5, PE-04)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bar",
    [("98.95", "99.80"), ("99.00", "99.50"), ("98.00", "98.50")],
    ids=["through-the-stop", "low-equals-the-stop", "pe04-wholly-below-the-stop"],
)
def test_pe01_pe04_a_stop_only_reach_while_waiting_cancels(bar: tuple[str, str]) -> None:
    result = _after_waiting({"10:20": bar})
    assert _kinds(result) == [K.ENTRY_CANCELLED]
    assert result.lifecycle.state is S.CANCELLED_BEFORE_ENTRY
    assert all(event.kind is not K.ENTRY_ACTIVATED for event in result.lifecycle.events)


def test_am01_entry_and_stop_in_one_bar_is_indeterminate_never_cancelled() -> None:
    result = _after_waiting({"10:20": ("98.90", "100.20")})
    assert _kinds(result) == [K.ENTRY_INDETERMINATE]
    assert result.lifecycle.state is S.INDETERMINATE_ENTRY


def test_an_untouched_stop_leaves_the_setup_waiting() -> None:
    result = _after_waiting({"10:20": ("99.01", "99.80")}, at="10:26")
    assert result.events == () and result.lifecycle.state is S.WAITING_FOR_ENTRY


def test_pe03_a_stop_reach_on_the_last_entry_bar_cancels_rather_than_expires() -> None:
    result = _after_waiting({"11:00": ("98.50", "99.50")})
    assert _kinds(result) == [K.ENTRY_CANCELLED]


def test_a_cancelled_setup_never_activates_later() -> None:
    cancelled = _TERMINALS[S.CANCELLED_BEFORE_ENTRY]
    later = _obs("15:30", bars={"10:00": ("100.10", "100.30")}, ref="ecs1-sha256:later")
    assert cancelled.advance(later).events == ()


# ---------------------------------------------------------------------------
# Group D -- active stop and target (O-1, EI0-D9)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("bar", "kind"),
    [
        (("99.00", "100.00"), K.STOP_REACHED),
        (("102.00", "103.00"), K.TARGET_REACHED),
        (("98.99", "103.00"), K.EXIT_INDETERMINATE),
        (("99.01", "102.99"), None),
    ],
    ids=["low-equals-stop", "high-equals-target", "both-at-threshold", "neither"],
)
def test_exact_threshold_equality_counts_as_reached(
    bar: tuple[str, str], kind: EquityLifecycleEventKind | None
) -> None:
    result = _after_active({"12:00": bar}, at="12:06")
    assert _kinds(result) == ([] if kind is None else [kind])


def test_the_activation_bar_is_not_evaluated_for_exits() -> None:
    result = _after_waiting({"10:00": ("100.10", "100.60"), "10:05": ("98.00", "98.50")})
    assert _kinds(result) == [K.ENTRY_ACTIVATED, K.STOP_REACHED]
    assert result.events[1].evidence.opens_at == _t("10:05")


# ---------------------------------------------------------------------------
# Group E -- evidence handling (EI5-D6, EI5-D7)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "outcome",
    [
        Outcome.MISSING,
        Outcome.UNFINALIZED,
        Outcome.CONFLICTING_VALUES,
        Outcome.UNRESOLVED_REVISIONS,
    ],
)
def test_ev01_to_ev04_a_deficient_interval_before_the_boundary_blocks(
    outcome: EquityLifecycleIntervalOutcome,
) -> None:
    result = _after_waiting({"10:30": outcome}, at="10:45")
    assert result.status is Status.BLOCKED and result.events == ()
    assert result.halted_at is not None and result.halted_at.outcome is outcome
    assert result.lifecycle.state is S.WAITING_FOR_ENTRY


def test_ev05_an_interval_not_ended_awaits_evidence_without_blocking() -> None:
    result = _after_waiting({}, at="10:31")
    assert result.status is Status.AWAITING_EVIDENCE
    assert result.halted_at is not None and result.halted_at.outcome is Outcome.NOT_ENDED


def test_ev06_a_later_acceptable_bar_is_never_used_past_a_deficiency() -> None:
    result = _after_waiting({"09:55": Outcome.MISSING, "10:00": ("98.00", "98.50")}, at="10:30")
    assert result.status is Status.BLOCKED and result.events == ()
    assert result.halted_at is not None and result.halted_at.opens_at == _t("09:55")


def test_ev07_every_deficiency_to_the_boundary_is_listed_with_its_ei2a_outcome() -> None:
    result = _after_active(
        {
            "12:00": Outcome.UNFINALIZED,
            "12:30": Outcome.CONFLICTING_VALUES,
            "14:55": Outcome.UNRESOLVED_REVISIONS,
        }
    )
    kinds = [(d.opens_at, d.kind) for d in result.events[0].deficiencies]
    assert kinds == [
        (_t("12:00"), EquityEvidenceDeficiencyKind.UNFINALIZED),
        (_t("12:30"), EquityEvidenceDeficiencyKind.CONFLICTING_VALUES),
        (_t("14:55"), EquityEvidenceDeficiencyKind.UNRESOLVED_REVISIONS),
    ]


def test_a_waiting_incomplete_evidence_lists_only_deficiencies_up_to_the_entry_window_end() -> None:
    result = _after_waiting({"10:30": Outcome.MISSING, "12:00": Outcome.MISSING})
    assert [d.opens_at for d in result.events[0].deficiencies] == [_t("10:30")]


def test_tb02_monitoring_resumes_once_the_blocking_interval_is_acceptable() -> None:
    blocked = _after_waiting({"10:30": Outcome.UNFINALIZED}, at="10:45")
    assert blocked.status is Status.BLOCKED
    resumed = blocked.lifecycle.advance(
        _obs("10:50", bars={"10:35": ("100.10", "100.30")}, ref="ecs1-sha256:later")
    )
    assert _kinds(resumed) == [K.ENTRY_ACTIVATED]
    assert resumed.events[0].evidence.opens_at == _t("10:35")


def _intervals(*openings: str) -> tuple[EquityLifecycleInterval, ...]:
    return tuple(
        EquityLifecycleInterval(
            _t(o), _t(_plus5(o)), Outcome.ACCEPTABLE, _p("100.8"), _p("101"), ("x",)
        )
        for o in openings
    )


@pytest.mark.parametrize(
    "openings",
    [("09:50", "09:45"), ("09:45", "09:45"), ("09:45", "09:55")],
    ids=["out-of-order", "duplicate", "skipped-interval"],
)
def test_unordered_duplicate_or_gapped_intervals_are_refused(openings: tuple[str, ...]) -> None:
    with pytest.raises(InvalidEquityLifecycleObservationError, match="contiguous"):
        EquityLifecycleObservation(_t("15:10"), _REF, _intervals(*openings))


def test_no_look_ahead_an_interval_is_not_ended_exactly_when_it_closes_after_as_of() -> None:
    at = _t("10:00")
    with pytest.raises(InvalidEquityLifecycleObservationError, match="NOT_ENDED"):
        EquityLifecycleObservation(at, _REF, _intervals("10:00"))
    with pytest.raises(InvalidEquityLifecycleObservationError, match="NOT_ENDED"):
        EquityLifecycleObservation(
            at, _REF, (EquityLifecycleInterval(_t("09:50"), _t("09:55"), Outcome.NOT_ENDED),)
        )


def test_an_interval_closing_at_as_of_has_ended_and_may_be_acceptable_or_deficient() -> None:
    # EI-2A accepts a candle received and confirmed final exactly at its close.
    at = _t("09:55")
    EquityLifecycleObservation(
        at, _REF, (EquityLifecycleInterval(_t("09:50"), _t("09:55"), Outcome.UNFINALIZED),)
    )
    EquityLifecycleObservation(at, _REF, _intervals("09:50"))
    with pytest.raises(InvalidEquityLifecycleObservationError, match="NOT_ENDED"):
        EquityLifecycleObservation(
            at, _REF, (EquityLifecycleInterval(_t("09:50"), _t("09:55"), Outcome.NOT_ENDED),)
        )
    with pytest.raises(InvalidEquityLifecycleObservationError, match="NOT_ENDED"):
        EquityLifecycleObservation(_t("09:54:59.999999"), _REF, _intervals("09:50"))


def test_an_observation_must_start_at_the_cursor_and_end_at_the_exit_boundary() -> None:
    active = _active()
    with pytest.raises(InvalidEquityLifecycleObservationError, match="cursor"):
        active.advance(_obs("15:10", start="10:00"))
    with pytest.raises(InvalidEquityLifecycleObservationError, match="cursor"):
        active.advance(_obs("15:10", start="10:10"))
    with pytest.raises(InvalidEquityLifecycleObservationError, match="modeled_exit_at"):
        active.advance(_obs("15:10", start="10:05", end="14:55"))


def test_an_observation_older_than_the_last_event_is_refused() -> None:
    active = _active()
    with pytest.raises(InvalidEquityLifecycleObservationError, match="older"):
        active.advance(_obs("10:05:59", start="10:05"))


def test_an_acceptable_bar_in_another_currency_is_refused() -> None:
    usd = Currency("USD")
    at = _t("10:12")
    intervals = list(_obs("10:12", start="10:05").intervals)
    intervals[0] = EquityLifecycleInterval(
        _t("10:05"),
        _t("10:10"),
        Outcome.ACCEPTABLE,
        Price(Decimal("100.8"), usd),
        Price(Decimal("101"), usd),
        ("x",),
    )
    with pytest.raises(InvalidEquityLifecycleObservationError, match="currency"):
        _active().advance(EquityLifecycleObservation(at, _REF, tuple(intervals)))


# ---------------------------------------------------------------------------
# Group F -- expiry, cutoff and boundaries (EI5-D7, EI5-D8)
# ---------------------------------------------------------------------------


def test_expiry_reports_a_target_reach_above_the_zone_on_the_last_entry_bar() -> None:
    result = _after_waiting({"11:00": ("103.20", "103.60")})
    assert _kinds(result) == [K.ENTRY_WINDOW_EXPIRED]
    assert result.events[0].touched == (L.TARGET,)


def test_se02_a_reach_on_the_final_exit_bar_takes_precedence_over_the_cutoff() -> None:
    for bar, kind in (
        (("98.00", "99.00"), K.STOP_REACHED),
        (("102.50", "103.40"), K.TARGET_REACHED),
    ):
        result = _after_active({"14:55": bar})
        assert _kinds(result) == [kind]
        assert result.events[0].evidence.closes_at == _t("15:00")


def test_ew07_nothing_after_the_exit_boundary_is_accepted() -> None:
    with pytest.raises(InvalidEquityLifecycleObservationError, match="modeled_exit_at"):
        _active().advance(_obs("15:20", start="10:05", end="15:10"))


def test_tb01_an_active_gap_before_the_boundary_blocks_without_an_event() -> None:
    result = _after_active({"13:15": Outcome.MISSING}, at="14:30")
    assert result.status is Status.BLOCKED and result.events == ()
    assert result.lifecycle.state is S.ACTIVE


def test_tb05_without_a_post_boundary_snapshot_nothing_is_assumed() -> None:
    blocked = _after_active({"13:15": Outcome.MISSING}, at="14:59:59")
    assert blocked.status is Status.BLOCKED and blocked.lifecycle.state is S.ACTIVE


def test_the_entry_window_boundary_is_inclusive_and_distinct_from_the_last_opening() -> None:
    # 11:00 is the last entry bar's opening; 11:05 (its close) is the boundary.
    before = _after_waiting({"10:30": Outcome.MISSING}, at="11:04:59")
    assert before.status is Status.BLOCKED
    at_boundary = _after_waiting({"10:30": Outcome.MISSING}, at="11:05")
    assert _kinds(at_boundary) == [K.EVIDENCE_INCOMPLETE]


def test_a_snapshot_exactly_at_the_entry_window_end_with_the_last_bar_not_final_blocks() -> None:
    # EI5-D7 exact-boundary clarification (owner approved 2026-11-12): the last
    # entry bar merely not yet final at as_of == 11:05 blocks temporarily. No
    # settlement allowance is introduced (O-2 and EI3-D10 stay deferred).
    result = _after_waiting({}, at="11:05")
    assert result.status is Status.BLOCKED and result.events == ()
    assert result.halted_at is not None and result.halted_at.outcome is Outcome.UNFINALIZED
    later = _after_waiting({}, at="11:06")
    assert _kinds(later) == [K.ENTRY_WINDOW_EXPIRED]


def test_ew05_activation_on_the_bar_closing_at_the_exit_is_followed_by_the_cutoff() -> None:
    window = EquityLifecycleWindow(_LEVELS, _t("09:45"), _t("14:55"), _t("15:00"), _t("15:00"))
    lifecycle = EquityRecommendationLifecycle(window)
    result = lifecycle.advance(_obs("15:10", bars={"14:55": ("100.10", "100.30")}))
    assert _kinds(result) == [K.ENTRY_WINDOW_OPENED, K.ENTRY_ACTIVATED, K.SESSION_CUTOFF_REACHED]
    assert result.events[1].evidence == result.events[2].evidence
    assert EquityRecommendationLifecycle(window, result.lifecycle.events) == result.lifecycle


def test_se03_no_overnight_carry_over_next_session_intervals_are_refused() -> None:
    next_session = _obs("15:10", start="10:05", day=_NEXT_DAY)
    with pytest.raises(InvalidEquityLifecycleObservationError):
        _active().advance(next_session)


def test_a_post_session_snapshot_of_the_same_session_is_still_evaluated() -> None:
    later = EquityLifecycleObservation(
        _t("09:00", _NEXT_DAY), _REF, _obs("15:10", start="10:05").intervals
    )
    result = _active().advance(later)
    assert _kinds(result) == [K.SESSION_CUTOFF_REACHED]


# ---------------------------------------------------------------------------
# Group G -- determinism, chronology and revisions (EI5-D8)
# ---------------------------------------------------------------------------


def test_reordered_or_renumbered_events_are_refused() -> None:
    events = _after_active({"11:15": ("101.00", "103.00")}).lifecycle.events
    with pytest.raises(InvalidEquityRecommendationLifecycleError, match="sequence"):
        EquityRecommendationLifecycle(_WINDOW, (events[1], events[0], events[2]))
    with pytest.raises(InvalidEquityRecommendationLifecycleError, match="sequence"):
        EquityRecommendationLifecycle(_WINDOW, events[1:])


def test_decreasing_evaluation_instants_are_refused() -> None:
    late_open = _event(1, K.ENTRY_WINDOW_OPENED, S.RECORDED, S.WAITING_FOR_ENTRY, "09:45",
                       "10:20", observations=())  # fmt: skip
    with pytest.raises(InvalidEquityRecommendationLifecycleError, match="decrease"):
        EquityRecommendationLifecycle(_WINDOW, (late_open, _ACTIVATED))


def _closed_target() -> EquityRecommendationLifecycle:
    lifecycle = _after_active({"11:15": ("101.00", "103.00")}).lifecycle
    assert lifecycle.events[-1].kind is K.TARGET_REACHED
    return lifecycle


_CORRECTED = EquityLifecycleEvidence(
    "ecs1-sha256:after-correction", _t("11:15"), _t("11:20"), ("obs-11:15", "obs-11:15-r2")
)


def test_rv01_a_correction_after_terminality_is_recorded_without_changing_state() -> None:
    lifecycle = _closed_target()
    cited = lifecycle.events[-1]
    revised = lifecycle.record_source_revision(cited.sequence, _CORRECTED, _t("16:00"))
    revision = revised.events[-1]
    assert revised.state is S.CLOSED_TARGET
    assert revised.events[:-1] == lifecycle.events
    assert revision.kind is K.SOURCE_REVISION_RECORDED and not revision.changes_state
    assert (revision.from_state, revision.to_state) == (S.CLOSED_TARGET, S.CLOSED_TARGET)
    assert revision.superseded_evidence == cited.evidence and revision.evidence == _CORRECTED
    assert revision.materiality is EquityRevisionMateriality.UNASSESSED
    assert EquityRecommendationLifecycle(_WINDOW, revised.events) == revised


def test_rv03_the_same_correction_is_recorded_once() -> None:
    lifecycle = _closed_target()
    once = lifecycle.record_source_revision(3, _CORRECTED, _t("16:00"))
    assert once.record_source_revision(3, _CORRECTED, _t("17:00")) == once
    duplicate = once.events[-1]
    copy = EquityLifecycleEvent(
        duplicate.sequence + 1,
        duplicate.kind,
        duplicate.from_state,
        duplicate.to_state,
        duplicate.evaluated_at,
        duplicate.evidence,
        cited_sequence=duplicate.cited_sequence,
        superseded_evidence=duplicate.superseded_evidence,
        materiality=duplicate.materiality,
    )
    with pytest.raises(InvalidEquityRecommendationLifecycleError, match="already recorded"):
        EquityRecommendationLifecycle(_WINDOW, once.events + (copy,))


def test_rv02_a_correction_while_active_does_not_rewrite_and_monitoring_continues() -> None:
    active = _active()
    activation = active.events[-1]
    corrected = EquityLifecycleEvidence(
        "ecs1-sha256:after-correction", _t("10:00"), _t("10:05"), ("obs-10:00-r2",)
    )
    revised = active.record_source_revision(activation.sequence, corrected, _t("10:20"))
    assert revised.state is S.ACTIVE and revised.events[:-1] == active.events
    result = revised.advance(_obs("15:10", start="10:05", bars={"11:15": ("98.00", "98.50")}))
    assert _kinds(result) == [K.STOP_REACHED]


def test_a_revision_can_cite_only_a_bar_driven_event_and_must_change_the_evidence() -> None:
    lifecycle = _closed_target()
    opened = lifecycle.events[0]
    with pytest.raises(InvalidEquityRecommendationLifecycleError, match="acceptable bar"):
        lifecycle.record_source_revision(
            1,
            EquityLifecycleEvidence(
                "ecs1-sha256:x", opened.evidence.opens_at, opened.evidence.closes_at
            ),  # fmt: skip
            _t("16:00"),
        )
    with pytest.raises(InvalidEquityLifecycleEventError, match="differ"):
        lifecycle.record_source_revision(3, lifecycle.events[2].evidence, _t("16:00"))
    with pytest.raises(InvalidEquityRecommendationLifecycleError, match="existing"):
        lifecycle.record_source_revision(9, _CORRECTED, _t("16:00"))


def test_rv05_no_revision_produces_invalidated_or_any_state_change() -> None:
    assert "INVALIDATED" not in {state.value for state in S}
    for state, lifecycle in _TERMINALS.items():
        bar_events = [e for e in lifecycle.events if e.kind.is_bar_driven]
        if not bar_events:
            continue
        cited = bar_events[-1]
        new = EquityLifecycleEvidence(
            "ecs1-sha256:revised", cited.evidence.opens_at, cited.evidence.closes_at, ("r",)
        )
        assert lifecycle.record_source_revision(cited.sequence, new, _t("16:00")).state is state


# ---------------------------------------------------------------------------
# Properties over a synthetic price grid (parameterized; no new dependency)
# ---------------------------------------------------------------------------

_GRID = ("97.50", "98.00", "98.90", "99.00", "99.50", "100.00", "100.20", "100.50",
         "100.80", "102.00", "103.00", "103.10", "104.00")  # fmt: skip
_RANGES = [
    (low, high)
    for low, high in combinations_with_replacement(_GRID, 2)
    if Decimal(low) <= Decimal(high)
]


@pytest.mark.parametrize("bar", _RANGES, ids="-".join)
def test_property_waiting_outcomes_follow_the_approved_precedence(bar: tuple[str, str]) -> None:
    low, high = (Decimal(value) for value in bar)
    zone = low <= Decimal("100.50") and high >= Decimal("100.00")
    stop = low <= Decimal("99.00")
    target = high >= Decimal("103.00")
    result = _after_waiting({"10:20": bar}, at="10:26")
    if zone and (stop or target):
        expected = [K.ENTRY_INDETERMINATE]
    elif zone:
        expected = [K.ENTRY_ACTIVATED]
    elif stop:
        expected = [K.ENTRY_CANCELLED]
    else:
        expected = []
    assert _kinds(result) == expected
    if stop:
        assert result.lifecycle.state is not S.ACTIVE
    for event in result.events:
        if event.ordering is EquityIntrabarOrdering.UNKNOWN:
            assert event.to_state is S.INDETERMINATE_ENTRY


@pytest.mark.parametrize("bar", _RANGES, ids="-".join)
def test_property_active_outcomes_never_resolve_an_unknown_ordering(bar: tuple[str, str]) -> None:
    low, high = (Decimal(value) for value in bar)
    stop, target = low <= Decimal("99.00"), high >= Decimal("103.00")
    result = _after_active({"12:00": bar}, at="12:06")
    if stop and target:
        assert result.lifecycle.state is S.INDETERMINATE_EXIT
        assert result.events[0].ordering is EquityIntrabarOrdering.UNKNOWN
    elif stop:
        assert result.lifecycle.state is S.CLOSED_STOP
    elif target:
        assert result.lifecycle.state is S.CLOSED_TARGET
    else:
        assert result.lifecycle.state is S.ACTIVE and result.events == ()


_FORBIDDEN_FIELD_WORDS = ("price", "fill", "quantity", "order", "broker", "pnl", "profit", "exit")


def test_nb01_nb02_no_event_field_can_hold_a_fill_execution_or_exit_price() -> None:
    for field in fields(EquityLifecycleEvent):
        name = field.name.lower().replace("ordering", "")
        for word in _FORBIDDEN_FIELD_WORDS:
            assert word not in name, field.name
    for lifecycle in _TERMINALS.values():
        for event in lifecycle.events:
            assert all(isinstance(level, EquityLifecycleLevel) for level in event.touched)
