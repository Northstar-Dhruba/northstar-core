"""EI-5B: the EI5-D7 exact-boundary finality clarification (owner approved 2026-11-12).

When an evaluation's ``as_of`` equals the applicable boundary -- the close of the
last entry bar while waiting, ``modeled_exit_at`` while active -- and the bar
closing there is ``MISSING`` or ``UNFINALIZED`` only because its close has just
been reached, monitoring stays temporarily blocked. It does not become terminal
``INCOMPLETE_EVIDENCE``. A later snapshot decides by the existing rules. No
finality-latency or settlement policy (O-2) is introduced.

EI-2A at ``closes_at == as_of``: the interval has ended, so it is never
``NOT_ENDED``. A candle received exactly at the close, with finality confirmed
exactly at the close, is ``ACCEPTABLE``; otherwise it is ``MISSING``,
``UNFINALIZED``, ``CONFLICTING_VALUES`` or ``UNRESOLVED_REVISIONS``.

All values are synthetic (EI-5 Decision Register, section 4.1).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from northstar_core.foundation.value_objects import Currency, PointInTime, Price
from northstar_core.recommendations.equity import EquityEntryZone, EquityRecommendationLevels
from northstar_core.recommendations.equity.lifecycle import (
    EquityEvidenceDeficiency,
    EquityEvidenceDeficiencyKind,
    EquityLifecycleAdvance,
    EquityLifecycleAdvanceStatus,
    EquityLifecycleEvent,
    EquityLifecycleEventKind,
    EquityLifecycleEvidence,
    EquityLifecycleInterval,
    EquityLifecycleIntervalOutcome,
    EquityLifecycleObservation,
    EquityLifecycleState,
    EquityLifecycleWindow,
    EquityRecommendationLifecycle,
    InvalidEquityLifecycleObservationError,
    InvalidEquityRecommendationLifecycleError,
)

K = EquityLifecycleEventKind
S = EquityLifecycleState
Outcome = EquityLifecycleIntervalOutcome
Status = EquityLifecycleAdvanceStatus
Deficiency = EquityEvidenceDeficiencyKind

_INR = Currency("INR")
_REF = "ecs1-sha256:boundary"
_QUIET = ("100.80", "101.20")


def _p(amount: str) -> Price:
    return Price(Decimal(amount), _INR)


def _t(clock: str) -> PointInTime:
    if len(clock) == 5:
        clock = f"{clock}:00"
    return PointInTime(f"2026-11-02T{clock}+05:30")


def _plus5(clock: str) -> str:
    return (datetime.strptime(clock, "%H:%M") + timedelta(minutes=5)).strftime("%H:%M")


def _openings(start: str) -> list[str]:
    current, end = datetime.strptime(start, "%H:%M"), datetime.strptime("15:00", "%H:%M")
    found = []
    while current < end:
        found.append(current.strftime("%H:%M"))
        current += timedelta(minutes=5)
    return found


_LEVELS = EquityRecommendationLevels(
    EquityEntryZone(_p("100.00"), _p("100.50")), _p("99.00"), _p("103.00")
)
_WINDOW = EquityLifecycleWindow(_LEVELS, _t("09:45"), _t("11:00"), _t("11:05"), _t("15:00"))

Spec = tuple[str, str] | EquityLifecycleIntervalOutcome


def _obs(
    at: str, start: str = "09:45", bars: dict[str, Spec] | None = None
) -> EquityLifecycleObservation:
    """Bars default to quiet acceptable candles; a bar closing after ``at`` is NOT_ENDED."""
    instant = _t(at)
    bars = bars or {}
    intervals = []
    for opening in _openings(start):
        opens, closes = _t(opening), _t(_plus5(opening))
        spec = bars.get(opening)
        if closes.compare(instant) > 0:
            assert spec is None, f"{opening} has not ended at {at}"
            intervals.append(EquityLifecycleInterval(opens, closes, Outcome.NOT_ENDED))
            continue
        spec = _QUIET if spec is None else spec
        if isinstance(spec, EquityLifecycleIntervalOutcome):
            intervals.append(EquityLifecycleInterval(opens, closes, spec))
        else:
            low, high = spec
            intervals.append(
                EquityLifecycleInterval(
                    opens, closes, Outcome.ACCEPTABLE, _p(low), _p(high), (f"obs-{opening}",)
                )
            )
    return EquityLifecycleObservation(instant, _REF, tuple(intervals))


def _waiting() -> EquityRecommendationLifecycle:
    result = EquityRecommendationLifecycle(_WINDOW).advance(_obs("09:46"))
    assert result.lifecycle.state is S.WAITING_FOR_ENTRY
    return result.lifecycle


def _active() -> EquityRecommendationLifecycle:
    result = EquityRecommendationLifecycle(_WINDOW).advance(
        _obs("10:06", bars={"10:00": ("100.10", "100.60")})
    )
    assert result.lifecycle.state is S.ACTIVE and result.lifecycle.cursor == _t("10:05")
    return result.lifecycle


def _kinds(result: EquityLifecycleAdvance) -> list[EquityLifecycleEventKind]:
    return [event.kind for event in result.events]


def _assert_blocked_at(result: EquityLifecycleAdvance, opening: str) -> None:
    assert result.status is Status.BLOCKED
    assert result.events == ()
    assert result.halted_at is not None and result.halted_at.opens_at == _t(opening)
    assert not result.lifecycle.is_terminal


# ---------------------------------------------------------------------------
# Entry-window boundary: the last entry bar is 11:00-11:05
# ---------------------------------------------------------------------------


def test_entry_one_microsecond_before_the_boundary_the_last_bar_has_not_ended() -> None:
    result = _waiting().advance(_obs("11:04:59.999999"))
    assert result.status is Status.AWAITING_EVIDENCE and result.events == ()
    assert result.halted_at is not None and result.halted_at.outcome is Outcome.NOT_ENDED


@pytest.mark.parametrize("outcome", [Outcome.UNFINALIZED, Outcome.MISSING])
def test_entry_exactly_at_the_boundary_a_not_yet_final_last_bar_blocks_temporarily(
    outcome: EquityLifecycleIntervalOutcome,
) -> None:
    waiting = _waiting()
    result = waiting.advance(_obs("11:05:00.000000", bars={"11:00": outcome}))
    _assert_blocked_at(result, "11:00")
    assert result.halted_at is not None and result.halted_at.outcome is outcome
    assert result.lifecycle == waiting and result.lifecycle.state is S.WAITING_FOR_ENTRY


def test_entry_exactly_at_the_boundary_an_acceptable_last_bar_is_legitimate_and_expires() -> None:
    # EI-2A: received at 11:05 and confirmed final at 11:05 is ACCEPTABLE at as_of 11:05.
    result = _waiting().advance(_obs("11:05", bars={"11:00": _QUIET}))
    assert _kinds(result) == [K.ENTRY_WINDOW_EXPIRED]
    assert result.events[0].evaluated_at == result.events[0].evidence.closes_at == _t("11:05")


@pytest.mark.parametrize(
    ("bar", "kind", "state"),
    [
        (("100.10", "100.30"), K.ENTRY_ACTIVATED, S.ACTIVE),
        (("98.20", "98.70"), K.ENTRY_CANCELLED, S.CANCELLED_BEFORE_ENTRY),
        (("98.90", "100.20"), K.ENTRY_INDETERMINATE, S.INDETERMINATE_ENTRY),
        (("100.40", "103.20"), K.ENTRY_INDETERMINATE, S.INDETERMINATE_ENTRY),
    ],
    ids=["entry", "pre-entry-stop", "entry-and-stop", "entry-and-target"],
)
def test_entry_exactly_at_the_boundary_an_acceptable_last_bar_keeps_the_approved_outcomes(
    bar: tuple[str, str], kind: EquityLifecycleEventKind, state: EquityLifecycleState
) -> None:
    result = _waiting().advance(_obs("11:05", bars={"11:00": bar}))
    assert _kinds(result)[0] is kind and result.lifecycle.state is state


def test_entry_one_microsecond_after_the_boundary_a_deficiency_is_terminal() -> None:
    result = _waiting().advance(_obs("11:05:00.000001", bars={"11:00": Outcome.UNFINALIZED}))
    assert _kinds(result) == [K.EVIDENCE_INCOMPLETE]
    assert result.events[0].deficiencies == (
        EquityEvidenceDeficiency(_t("11:00"), _t("11:05"), Deficiency.UNFINALIZED),
    )


def test_entry_a_later_acceptable_snapshot_after_an_exact_boundary_block_expires() -> None:
    blocked = _waiting().advance(_obs("11:05", bars={"11:00": Outcome.UNFINALIZED}))
    later = blocked.lifecycle.advance(_obs("11:06"))
    assert _kinds(later) == [K.ENTRY_WINDOW_EXPIRED]
    assert later.lifecycle.state is S.EXPIRED_BEFORE_ENTRY


@pytest.mark.parametrize(
    ("bar", "state"),
    [(("100.10", "100.30"), S.ACTIVE), (("98.00", "98.50"), S.CANCELLED_BEFORE_ENTRY)],
    ids=["entry", "pre-entry-stop"],
)
def test_entry_a_later_snapshot_can_establish_entry_or_cancellation(
    bar: tuple[str, str], state: EquityLifecycleState
) -> None:
    blocked = _waiting().advance(_obs("11:05", bars={"11:00": Outcome.MISSING}))
    later = blocked.lifecycle.advance(_obs("11:07", bars={"11:00": bar}))
    assert later.lifecycle.state is state


def test_entry_a_later_still_deficient_snapshot_is_terminal_incomplete_evidence() -> None:
    blocked = _waiting().advance(_obs("11:05", bars={"11:00": Outcome.UNFINALIZED}))
    later = blocked.lifecycle.advance(_obs("11:20", bars={"11:00": Outcome.UNFINALIZED}))
    assert _kinds(later) == [K.EVIDENCE_INCOMPLETE]
    assert later.lifecycle.state is S.INCOMPLETE_EVIDENCE


# ---------------------------------------------------------------------------
# Modeled-exit boundary: the last bar is 14:55-15:00
# ---------------------------------------------------------------------------


def _active_at(at: str, bars: dict[str, Spec] | None = None) -> EquityLifecycleAdvance:
    return _active().advance(_obs(at, start="10:05", bars=bars))


def test_exit_one_microsecond_before_the_boundary_the_last_bar_has_not_ended() -> None:
    result = _active_at("14:59:59.999999")
    assert result.status is Status.AWAITING_EVIDENCE and result.events == ()


@pytest.mark.parametrize("outcome", [Outcome.UNFINALIZED, Outcome.MISSING])
def test_exit_exactly_at_the_boundary_a_not_yet_final_last_bar_blocks_temporarily(
    outcome: EquityLifecycleIntervalOutcome,
) -> None:
    result = _active_at("15:00:00.000000", {"14:55": outcome})
    _assert_blocked_at(result, "14:55")
    assert result.lifecycle.state is S.ACTIVE


@pytest.mark.parametrize(
    ("bar", "kind"),
    [
        (_QUIET, K.SESSION_CUTOFF_REACHED),
        (("98.00", "98.50"), K.STOP_REACHED),
        (("103.50", "104.00"), K.TARGET_REACHED),
        (("98.90", "103.10"), K.EXIT_INDETERMINATE),
    ],
    ids=["cutoff", "stop-gap", "target-gap", "both"],
)
def test_exit_exactly_at_the_boundary_an_acceptable_last_bar_decides_normally(
    bar: tuple[str, str], kind: EquityLifecycleEventKind
) -> None:
    assert _kinds(_active_at("15:00", {"14:55": bar})) == [kind]


def test_exit_one_microsecond_after_the_boundary_a_deficiency_is_terminal() -> None:
    result = _active_at("15:00:00.000001", {"14:55": Outcome.UNFINALIZED})
    assert _kinds(result) == [K.EVIDENCE_INCOMPLETE]


@pytest.mark.parametrize(
    ("bar", "kind"),
    [
        (_QUIET, K.SESSION_CUTOFF_REACHED),
        (("99.00", "100.00"), K.STOP_REACHED),
        (("102.50", "103.40"), K.TARGET_REACHED),
    ],
    ids=["cutoff", "stop-precedence", "target-precedence"],
)
def test_exit_a_later_acceptable_snapshot_after_an_exact_boundary_block_decides(
    bar: tuple[str, str], kind: EquityLifecycleEventKind
) -> None:
    blocked = _active_at("15:00", {"14:55": Outcome.UNFINALIZED})
    later = blocked.lifecycle.advance(_obs("15:03", start="10:05", bars={"14:55": bar}))
    assert _kinds(later) == [kind]
    assert later.events[0].evidence.closes_at == _t("15:00")


def test_exit_a_later_still_deficient_snapshot_is_terminal_incomplete_evidence() -> None:
    blocked = _active_at("15:00", {"14:55": Outcome.MISSING})
    later = blocked.lifecycle.advance(_obs("15:30", start="10:05", bars={"14:55": Outcome.MISSING}))
    assert _kinds(later) == [K.EVIDENCE_INCOMPLETE]
    assert later.events[0].deficiencies[0].kind is Deficiency.MISSING


def test_exit_no_bar_closing_after_the_boundary_is_consumed() -> None:
    intervals = _obs("15:10", start="10:05").intervals + (
        EquityLifecycleInterval(_t("15:00"), _t("15:05"), Outcome.MISSING),
    )
    with pytest.raises(InvalidEquityLifecycleObservationError, match="modeled_exit_at"):
        _active().advance(EquityLifecycleObservation(_t("15:10"), _REF, intervals))


# ---------------------------------------------------------------------------
# Genuine deficiencies are unchanged (Case D)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("outcome", [Outcome.CONFLICTING_VALUES, Outcome.UNRESOLVED_REVISIONS])
def test_a_genuine_deficiency_of_the_boundary_bar_at_the_boundary_stays_terminal(
    outcome: EquityLifecycleIntervalOutcome,
) -> None:
    entry = _waiting().advance(_obs("11:05", bars={"11:00": outcome}))
    assert _kinds(entry) == [K.EVIDENCE_INCOMPLETE]
    exit_ = _active_at("15:00", {"14:55": outcome})
    assert _kinds(exit_) == [K.EVIDENCE_INCOMPLETE]


def test_an_earlier_genuine_gap_at_the_entry_boundary_is_still_terminal() -> None:
    result = _waiting().advance(
        _obs("11:05", bars={"10:30": Outcome.MISSING, "11:00": Outcome.UNFINALIZED})
    )
    assert _kinds(result) == [K.EVIDENCE_INCOMPLETE]
    assert [(d.opens_at, d.kind) for d in result.events[0].deficiencies] == [
        (_t("10:30"), Deficiency.MISSING),
        (_t("11:00"), Deficiency.UNFINALIZED),
    ]


def test_an_earlier_genuine_gap_at_the_exit_boundary_is_still_terminal() -> None:
    result = _active_at("15:00", {"13:15": Outcome.UNFINALIZED, "14:55": Outcome.MISSING})
    assert _kinds(result) == [K.EVIDENCE_INCOMPLETE]
    assert result.events[0].evidence.opens_at == _t("13:15")


def test_a_stored_incomplete_evidence_decided_only_by_boundary_finality_is_refused() -> None:
    waiting = _waiting()
    forged = EquityLifecycleEvent(
        2,
        K.EVIDENCE_INCOMPLETE,
        S.WAITING_FOR_ENTRY,
        S.INCOMPLETE_EVIDENCE,
        _t("11:05"),
        EquityLifecycleEvidence(_REF, _t("11:00"), _t("11:05")),
        deficiencies=(EquityEvidenceDeficiency(_t("11:00"), _t("11:05"), Deficiency.UNFINALIZED),),
    )
    with pytest.raises(InvalidEquityRecommendationLifecycleError, match="boundary"):
        EquityRecommendationLifecycle(_WINDOW, waiting.events + (forged,))


def test_exact_boundary_evaluation_is_deterministic_and_fabricates_no_event() -> None:
    waiting = _waiting()
    observation = _obs("11:05", bars={"11:00": Outcome.UNFINALIZED})
    first, second = waiting.advance(observation), waiting.advance(observation)
    assert first == second and first.events == ()
    assert first.lifecycle.advance(observation) == first
