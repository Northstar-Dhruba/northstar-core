"""Tests for the pure futures trade recommendation lifecycle.

Every scenario uses synthetic NIFTY daily bars stamped at their completion
instant (10:00Z, the 15:30 IST close). The levels are:

    LONG : stop 24800 | entry 25000-25100 | target 25500
    SHORT: target 24600 | entry 25000-25100 | stop 25300

Events are observations and documented modeling rules. No test, and no event,
claims a fill, an entry or exit price, or an intraday order of prices.
"""

from __future__ import annotations

import dataclasses
from decimal import Decimal

import pytest

from northstar_core.derivatives import ExpirationDate, QuoteValue
from northstar_core.foundation.exceptions.validation import ValidationError
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
    FuturesResearchDecisionReference,
    FuturesTradeRecommendation,
    FuturesTradeRecommendationEvent,
    FuturesTradeRecommendationIdentity,
    FuturesTradeRecommendationLifecycle,
    IntrabarOrdering,
    InvalidFuturesTradeRecommendationLifecycleError,
    InvalidFuturesTradeRecommendationObservationError,
    PriceTarget,
    RecommendationBoundary,
    RecommendationEventKind,
    RecommendationExpiryReason,
    RecommendationPolicyVersion,
    RecommendationStatus,
    RecommendationValidity,
    StopLoss,
    TradeDirection,
)
from northstar_core.strategy import ExplanationReason, StrategyIdentity

_NIFTY = FuturesProductReference(Symbol("NIFTY"), ExchangeCode("NSE"))
_OCT = FuturesContract(_NIFTY, ExpirationDate("2026-10-27"))
_NOV = FuturesContract(_NIFTY, ExpirationDate("2026-11-24"))
_DAILY = Timeframe("1d")

_ENTRY = RecommendationBoundary.ENTRY
_STOP = RecommendationBoundary.STOP
_TARGET = RecommendationBoundary.TARGET

Status = RecommendationStatus
Kind = RecommendationEventKind


def _instant(day: int) -> PointInTime:
    return PointInTime(f"2026-10-{day:02d}T10:00:00Z")


def _quote(value: str) -> QuoteValue:
    return QuoteValue(Decimal(value))


def _recommendation(
    direction: TradeDirection = TradeDirection.LONG,
    *,
    eligible_from: PointInTime | None = None,
    valid_through: PointInTime | None = None,
    contract_cutoff: PointInTime | None = None,
    identity: str = "rec-1",
) -> FuturesTradeRecommendation:
    long = direction is TradeDirection.LONG
    return FuturesTradeRecommendation(
        identity=FuturesTradeRecommendationIdentity(identity),
        contract=_OCT,
        direction=direction,
        entry=EntryZone(_quote("25000"), _quote("25100")),
        stop=StopLoss(_quote("24800" if long else "25300")),
        target=PriceTarget(_quote("25500" if long else "24600")),
        validity=RecommendationValidity(
            eligible_from or _instant(6),
            valid_through or _instant(16),
            contract_cutoff or _instant(27),
        ),
        source=FuturesResearchDecisionReference(
            _OCT, _DAILY, _instant(5), StrategyIdentity("directional-mvp-v1")
        ),
        policy_version=RecommendationPolicyVersion("levels-v1"),
        issued_at=PointInTime("2026-10-05T12:00:00Z"),
        thesis=(ExplanationReason("Synthetic thesis"),),
    )


_LONG = _recommendation(TradeDirection.LONG)
_SHORT = _recommendation(TradeDirection.SHORT)


def _bar(
    day: int,
    low: str,
    high: str,
    *,
    contract: FuturesContract = _OCT,
    timeframe: Timeframe = _DAILY,
    point_in_time: PointInTime | None = None,
    close: str | None = None,
) -> FuturesOHLCVBar:
    return FuturesOHLCVBar(
        contract=contract,
        point_in_time=point_in_time or _instant(day),
        timeframe=timeframe,
        open=_quote(low),
        high=_quote(high),
        low=_quote(low),
        close=_quote(close or high),
        volume=Quantity(Decimal("1000")),
    )


def _start(
    recommendation: FuturesTradeRecommendation = _LONG,
) -> FuturesTradeRecommendationLifecycle:
    return FuturesTradeRecommendationLifecycle(recommendation)


def _fold(
    recommendation: FuturesTradeRecommendation, *bars: FuturesOHLCVBar
) -> FuturesTradeRecommendationLifecycle:
    lifecycle = _start(recommendation)
    for bar in bars:
        lifecycle = lifecycle.advance(bar)
    return lifecycle


def _kinds(lifecycle: FuturesTradeRecommendationLifecycle) -> list[RecommendationEventKind]:
    return [event.kind for event in lifecycle.events]


# Representative bars ------------------------------------------------------------------

# LONG
_L_QUIET_ABOVE = ("25200", "25400")  # gap above the zone, below target
_L_QUIET_BELOW = ("24850", "24990")  # gap below the zone, above stop
_L_ENTRY = ("25050", "25300")
_L_STOP = ("24700", "25200")
_L_TARGET = ("25200", "25600")
_L_BOTH = ("24700", "25600")
_L_ENTRY_STOP = ("24700", "25050")
_L_ENTRY_TARGET = ("25050", "25600")
_L_INSIDE = ("25200", "25300")  # active, nothing touched

# SHORT
_S_ENTRY = ("24800", "25050")
_S_STOP = ("24900", "25350")
_S_TARGET = ("24500", "24900")
_S_BOTH = ("24500", "25350")
_S_ENTRY_STOP = ("25050", "25350")
_S_ENTRY_TARGET = ("24500", "25050")
_S_INSIDE = ("24700", "24900")


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------


def test_a_new_lifecycle_is_waiting_with_no_events() -> None:
    lifecycle = _start()

    assert lifecycle.status is Status.WAITING_FOR_ENTRY
    assert lifecycle.events == ()
    assert lifecycle.last_observation is None
    assert not lifecycle.is_terminal


# ---------------------------------------------------------------------------
# 1. Waiting, entry not touched; 15-16. gaps past the zone
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bounds", [_L_QUIET_ABOVE, _L_QUIET_BELOW], ids=["above", "below"])
def test_a_bar_that_misses_the_entry_zone_changes_nothing_but_the_cursor(
    bounds: tuple[str, str],
) -> None:
    bar = _bar(6, *bounds)
    lifecycle = _start().advance(bar)

    assert lifecycle.status is Status.WAITING_FOR_ENTRY
    assert lifecycle.events == ()
    assert lifecycle.last_observation == bar


def test_a_gap_above_the_zone_is_not_an_entry_even_across_several_bars() -> None:
    lifecycle = _fold(_LONG, _bar(6, "25150", "25400"), _bar(7, "25101", "25450"))

    assert lifecycle.status is Status.WAITING_FOR_ENTRY


def test_a_gap_below_the_zone_is_not_an_entry_for_a_short() -> None:
    lifecycle = _fold(_SHORT, _bar(6, "24700", "24999.95"))

    assert lifecycle.status is Status.WAITING_FOR_ENTRY


def test_a_long_bar_through_the_stop_but_not_the_zone_changes_nothing() -> None:
    """Invalidation before entry is not an approved rule; the setup keeps waiting."""
    lifecycle = _fold(_LONG, _bar(6, "24500", "24990"))

    assert lifecycle.status is Status.WAITING_FOR_ENTRY
    assert lifecycle.events == ()


# ---------------------------------------------------------------------------
# 2-3. Activation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("recommendation", "bounds"), [(_LONG, _L_ENTRY), (_SHORT, _S_ENTRY)], ids=["long", "short"]
)
def test_touching_only_the_entry_zone_activates(
    recommendation: FuturesTradeRecommendation, bounds: tuple[str, str]
) -> None:
    bar = _bar(6, *bounds)
    lifecycle = _fold(recommendation, bar)

    assert lifecycle.status is Status.ACTIVE
    (event,) = lifecycle.events
    assert event == FuturesTradeRecommendationEvent(
        recommendation=recommendation.identity,
        kind=Kind.ENTRY_ACTIVATED,
        observation=bar,
        touched=(_ENTRY,),
        ordering=IntrabarOrdering.NOT_REQUIRED,
    )


@pytest.mark.parametrize(
    ("low", "high"),
    [("24900", "25000"), ("25100", "25200"), ("25050", "25050")],
    ids=["high-equals-zone-low", "low-equals-zone-high", "inside"],
)
def test_entry_touch_is_inclusive_at_both_bounds(low: str, high: str) -> None:
    assert _fold(_LONG, _bar(6, low, high)).status is Status.ACTIVE


def test_a_single_price_zone_activates_on_an_exact_touch() -> None:
    recommendation = dataclasses.replace(_LONG, entry=EntryZone(_quote("25050"), _quote("25050")))

    assert _fold(recommendation, _bar(6, "24900", "25050")).status is Status.ACTIVE
    assert _fold(recommendation, _bar(6, "25050.05", "25200")).status is Status.WAITING_FOR_ENTRY


# ---------------------------------------------------------------------------
# 4-7. Stop and target while active
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("recommendation", "entry", "exit_bounds", "kind", "status", "touched"),
    [
        (_LONG, _L_ENTRY, _L_STOP, Kind.STOP_REACHED, Status.CLOSED_STOP, (_STOP,)),
        (_SHORT, _S_ENTRY, _S_STOP, Kind.STOP_REACHED, Status.CLOSED_STOP, (_STOP,)),
        (_LONG, _L_ENTRY, _L_TARGET, Kind.TARGET_REACHED, Status.CLOSED_TARGET, (_TARGET,)),
        (_SHORT, _S_ENTRY, _S_TARGET, Kind.TARGET_REACHED, Status.CLOSED_TARGET, (_TARGET,)),
    ],
    ids=["long-stop", "short-stop", "long-target", "short-target"],
)
def test_one_exit_boundary_closes_the_active_recommendation(
    recommendation: FuturesTradeRecommendation,
    entry: tuple[str, str],
    exit_bounds: tuple[str, str],
    kind: RecommendationEventKind,
    status: RecommendationStatus,
    touched: tuple[RecommendationBoundary, ...],
) -> None:
    exit_bar = _bar(7, *exit_bounds)
    lifecycle = _fold(recommendation, _bar(6, *entry), exit_bar)

    assert lifecycle.status is status
    assert lifecycle.is_terminal
    assert _kinds(lifecycle) == [Kind.ENTRY_ACTIVATED, kind]
    closing = lifecycle.events[-1]
    assert closing.observation == exit_bar
    assert closing.touched == touched
    assert closing.ordering is IntrabarOrdering.NOT_REQUIRED


@pytest.mark.parametrize(
    ("recommendation", "low", "high", "status"),
    [
        (_LONG, "24800", "25200", Status.CLOSED_STOP),
        (_LONG, "25200", "25500", Status.CLOSED_TARGET),
        (_SHORT, "24900", "25300", Status.CLOSED_STOP),
        (_SHORT, "24600", "24900", Status.CLOSED_TARGET),
    ],
    ids=["long-stop", "long-target", "short-stop", "short-target"],
)
def test_exit_touch_is_inclusive(
    recommendation: FuturesTradeRecommendation, low: str, high: str, status: RecommendationStatus
) -> None:
    entry = _L_ENTRY if recommendation is _LONG else _S_ENTRY
    assert _fold(recommendation, _bar(6, *entry), _bar(7, low, high)).status is status


@pytest.mark.parametrize(
    ("recommendation", "entry", "inside"),
    [(_LONG, _L_ENTRY, _L_INSIDE), (_SHORT, _S_ENTRY, _S_INSIDE)],
    ids=["long", "short"],
)
def test_an_active_bar_touching_neither_exit_changes_nothing(
    recommendation: FuturesTradeRecommendation,
    entry: tuple[str, str],
    inside: tuple[str, str],
) -> None:
    lifecycle = _fold(recommendation, _bar(6, *entry), _bar(7, *inside), _bar(8, *inside))

    assert lifecycle.status is Status.ACTIVE
    assert len(lifecycle.events) == 1
    assert lifecycle.last_observation == _bar(8, *inside)


# ---------------------------------------------------------------------------
# 8-9. Active both-touch: conservative stop-first
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("recommendation", "entry", "both"),
    [(_LONG, _L_ENTRY, _L_BOTH), (_SHORT, _S_ENTRY, _S_BOTH)],
    ids=["long", "short"],
)
def test_an_active_bar_touching_stop_and_target_closes_at_the_stop_by_policy(
    recommendation: FuturesTradeRecommendation,
    entry: tuple[str, str],
    both: tuple[str, str],
) -> None:
    lifecycle = _fold(recommendation, _bar(6, *entry), _bar(7, *both))

    assert lifecycle.status is Status.CLOSED_STOP
    closing = lifecycle.events[-1]
    assert closing.kind is Kind.STOP_REACHED
    assert closing.touched == (_STOP, _TARGET)
    assert closing.ordering is IntrabarOrdering.MODELED_STOP_FIRST


# ---------------------------------------------------------------------------
# 10-14. Ambiguous entry bars
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("recommendation", "bounds", "touched"),
    [
        (_LONG, _L_ENTRY_STOP, (_ENTRY, _STOP)),
        (_SHORT, _S_ENTRY_STOP, (_ENTRY, _STOP)),
        (_LONG, _L_ENTRY_TARGET, (_ENTRY, _TARGET)),
        (_SHORT, _S_ENTRY_TARGET, (_ENTRY, _TARGET)),
        (_LONG, _L_BOTH, (_ENTRY, _STOP, _TARGET)),
        (_SHORT, _S_BOTH, (_ENTRY, _STOP, _TARGET)),
    ],
    ids=[
        "long-entry-stop",
        "short-entry-stop",
        "long-entry-target",
        "short-entry-target",
        "long-all-three",
        "short-all-three",
    ],
)
def test_an_entry_bar_that_also_touches_an_exit_is_indeterminate(
    recommendation: FuturesTradeRecommendation,
    bounds: tuple[str, str],
    touched: tuple[RecommendationBoundary, ...],
) -> None:
    bar = _bar(6, *bounds)
    lifecycle = _fold(recommendation, bar)

    assert lifecycle.status is Status.INDETERMINATE_ENTRY
    assert lifecycle.is_terminal
    (event,) = lifecycle.events
    assert event.kind is Kind.ENTRY_INDETERMINATE
    assert event.touched == touched
    assert event.ordering is IntrabarOrdering.UNKNOWN
    assert event.observation == bar


def test_an_indeterminate_entry_is_neither_closed_at_target_nor_at_stop() -> None:
    """Stop-first is never applied to an entry bar."""
    lifecycle = _fold(_LONG, _bar(6, *_L_BOTH))

    assert Kind.STOP_REACHED not in _kinds(lifecycle)
    assert Kind.TARGET_REACHED not in _kinds(lifecycle)
    assert Kind.ENTRY_ACTIVATED not in _kinds(lifecycle)


def test_an_indeterminate_entry_never_reopens() -> None:
    lifecycle = _fold(_LONG, _bar(6, *_L_ENTRY_TARGET), _bar(7, *_L_ENTRY), _bar(8, *_L_TARGET))

    assert lifecycle.status is Status.INDETERMINATE_ENTRY
    assert len(lifecycle.events) == 1


# ---------------------------------------------------------------------------
# 17. Bars before or at issuance
# ---------------------------------------------------------------------------


def test_the_decision_bar_completed_before_issuance_is_ineligible() -> None:
    """Same session date as issuance, but completed before it: never applied."""
    decision_bar = _bar(5, *_L_ENTRY)
    lifecycle = _start()

    assert lifecycle.advance(decision_bar) is lifecycle


def test_a_bar_completing_exactly_at_issuance_is_ineligible() -> None:
    bar = _bar(5, *_L_ENTRY, point_in_time=PointInTime("2026-10-05T17:30:00+05:30"))
    lifecycle = _start()

    assert lifecycle.advance(bar) is lifecycle


def test_a_bar_completing_after_issuance_but_before_eligible_from_is_ignored() -> None:
    """B1: completing after issuance is not enough; its session began before issuance."""
    bar = _bar(5, *_L_ENTRY, point_in_time=PointInTime("2026-10-05T12:00:00.000001Z"))
    lifecycle = _start()

    assert lifecycle.advance(bar) is lifecycle


# ---------------------------------------------------------------------------
# 18-20. Validity and contract cutoff
# ---------------------------------------------------------------------------


def test_an_untouched_bar_at_valid_through_expires_before_entry() -> None:
    recommendation = _recommendation(valid_through=_instant(8))
    lifecycle = _fold(recommendation, _bar(6, *_L_QUIET_ABOVE), _bar(8, *_L_QUIET_ABOVE))

    assert lifecycle.status is Status.EXPIRED_BEFORE_ENTRY
    (event,) = lifecycle.events
    assert event.kind is Kind.VALIDITY_EXPIRED
    assert event.touched == ()
    assert event.expiry_reason is RecommendationExpiryReason.VALIDITY_WINDOW_ENDED
    assert event.observation.point_in_time == _instant(8)


def test_a_bar_at_valid_through_is_still_evaluated() -> None:
    recommendation = _recommendation(valid_through=_instant(8))
    lifecycle = _fold(recommendation, _bar(6, *_L_ENTRY), _bar(8, *_L_TARGET))

    assert lifecycle.status is Status.CLOSED_TARGET
    assert Kind.VALIDITY_EXPIRED not in _kinds(lifecycle)


def test_activation_on_the_last_eligible_bar_then_expires_after_activation() -> None:
    recommendation = _recommendation(valid_through=_instant(8))
    lifecycle = _fold(recommendation, _bar(8, *_L_ENTRY))

    assert lifecycle.status is Status.EXPIRED_AFTER_ACTIVATION
    assert _kinds(lifecycle) == [Kind.ENTRY_ACTIVATED, Kind.VALIDITY_EXPIRED]
    assert lifecycle.events[0].observation == lifecycle.events[1].observation


def test_an_active_untouched_bar_at_valid_through_expires_after_activation() -> None:
    recommendation = _recommendation(valid_through=_instant(8))
    lifecycle = _fold(recommendation, _bar(6, *_L_ENTRY), _bar(8, *_L_INSIDE))

    assert lifecycle.status is Status.EXPIRED_AFTER_ACTIVATION


def test_a_bar_after_valid_through_expires_without_evaluating_its_prices() -> None:
    """A target touched after the window does not count."""
    recommendation = _recommendation(valid_through=_instant(8))
    late = _bar(9, *_L_TARGET)
    lifecycle = _fold(recommendation, _bar(6, *_L_ENTRY), late)

    assert lifecycle.status is Status.EXPIRED_AFTER_ACTIVATION
    expiry = lifecycle.events[-1]
    assert expiry.kind is Kind.VALIDITY_EXPIRED
    assert expiry.touched == ()
    assert expiry.observation == late


def test_a_waiting_bar_after_valid_through_expires_before_entry_even_if_it_touches_entry() -> None:
    recommendation = _recommendation(valid_through=_instant(8))
    lifecycle = _fold(recommendation, _bar(9, *_L_ENTRY))

    assert lifecycle.status is Status.EXPIRED_BEFORE_ENTRY


def test_validity_ending_at_the_contract_cutoff_records_that_reason() -> None:
    recommendation = _recommendation(valid_through=_instant(27), contract_cutoff=_instant(27))
    lifecycle = _fold(recommendation, _bar(6, *_L_ENTRY), _bar(27, *_L_INSIDE))

    assert lifecycle.status is Status.EXPIRED_AFTER_ACTIVATION
    assert lifecycle.events[-1].expiry_reason is (
        RecommendationExpiryReason.CONTRACT_CUTOFF_REACHED
    )


def test_a_bar_after_the_contract_cutoff_expires_the_recommendation() -> None:
    recommendation = _recommendation(valid_through=_instant(27), contract_cutoff=_instant(27))
    lifecycle = _fold(recommendation, _bar(28, *_L_ENTRY))

    assert lifecycle.status is Status.EXPIRED_BEFORE_ENTRY
    assert lifecycle.events[-1].expiry_reason is (
        RecommendationExpiryReason.CONTRACT_CUTOFF_REACHED
    )


def test_a_bar_of_another_contract_is_refused() -> None:
    with pytest.raises(InvalidFuturesTradeRecommendationObservationError, match="not for"):
        _start().advance(_bar(6, *_L_ENTRY, contract=_NOV))


@pytest.mark.parametrize("timeframe", ["1h", "1w"])
def test_a_bar_of_another_timeframe_is_refused(timeframe: str) -> None:
    with pytest.raises(InvalidFuturesTradeRecommendationObservationError, match="not for"):
        _start().advance(_bar(6, *_L_ENTRY, timeframe=Timeframe(timeframe)))


@pytest.mark.parametrize("value", [None, "bar", (25000, 25100)])
def test_only_a_futures_bar_can_advance_a_lifecycle(value: object) -> None:
    with pytest.raises(InvalidFuturesTradeRecommendationObservationError, match="FuturesOHLCVBar"):
        _start().advance(value)  # type: ignore[arg-type]


def test_observation_errors_are_validation_errors() -> None:
    assert issubclass(InvalidFuturesTradeRecommendationObservationError, ValidationError)
    assert issubclass(InvalidFuturesTradeRecommendationLifecycleError, ValidationError)


# ---------------------------------------------------------------------------
# 21-22. Duplicate, revised and out-of-order bars
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bounds", [_L_QUIET_ABOVE, _L_ENTRY, _L_INSIDE], ids=["no-event", "event", "active"]
)
def test_the_same_bar_twice_is_a_no_op(bounds: tuple[str, str]) -> None:
    lifecycle = _fold(_LONG, _bar(6, *_L_QUIET_ABOVE), _bar(7, *bounds))

    assert lifecycle.advance(_bar(7, *bounds)) is lifecycle


def test_a_revised_bar_at_the_last_instant_is_refused() -> None:
    lifecycle = _fold(_LONG, _bar(6, *_L_QUIET_ABOVE))

    with pytest.raises(InvalidFuturesTradeRecommendationObservationError, match="differs"):
        lifecycle.advance(_bar(6, *_L_QUIET_ABOVE, close="25300"))


def test_the_same_instant_in_another_offset_is_the_same_observation() -> None:
    lifecycle = _fold(_LONG, _bar(6, *_L_ENTRY))
    same = _bar(6, *_L_ENTRY, point_in_time=PointInTime("2026-10-06T15:30:00+05:30"))

    assert lifecycle.advance(same) is lifecycle


@pytest.mark.parametrize("bounds", [_L_QUIET_ABOVE, _L_STOP], ids=["quiet", "would-stop"])
def test_an_earlier_bar_after_a_later_one_is_refused(bounds: tuple[str, str]) -> None:
    """An event-less later bar still fixes the order: the earlier bar was skipped."""
    lifecycle = _fold(_LONG, _bar(6, *_L_ENTRY), _bar(8, *_L_INSIDE))

    with pytest.raises(InvalidFuturesTradeRecommendationObservationError, match="earlier"):
        lifecycle.advance(_bar(7, *bounds))


def test_an_earlier_bar_is_refused_even_while_waiting_with_no_events() -> None:
    lifecycle = _fold(_LONG, _bar(8, *_L_QUIET_ABOVE))

    with pytest.raises(InvalidFuturesTradeRecommendationObservationError, match="earlier"):
        lifecycle.advance(_bar(7, *_L_ENTRY))


# ---------------------------------------------------------------------------
# 25. Terminal reprocessing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bars",
    [
        (_bar(6, *_L_ENTRY), _bar(7, *_L_TARGET)),
        (_bar(6, *_L_ENTRY), _bar(7, *_L_STOP)),
        (_bar(6, *_L_ENTRY_STOP),),
    ],
    ids=["closed-target", "closed-stop", "indeterminate"],
)
def test_a_terminal_lifecycle_never_changes_again(bars: tuple[FuturesOHLCVBar, ...]) -> None:
    terminal = _fold(_LONG, *bars)

    for later in (_bar(9, *_L_ENTRY), _bar(10, *_L_STOP), _bar(20, *_L_TARGET)):
        assert terminal.advance(later) is terminal
    assert terminal.advance(bars[-1]) is terminal


def test_an_expired_lifecycle_never_changes_again() -> None:
    expired = _fold(_recommendation(valid_through=_instant(8)), _bar(9, *_L_QUIET_ABOVE))

    assert expired.advance(_bar(10, *_L_ENTRY)) is expired


def test_a_terminal_lifecycle_still_refuses_an_earlier_bar() -> None:
    terminal = _fold(_LONG, _bar(6, *_L_ENTRY), _bar(8, *_L_TARGET))

    with pytest.raises(InvalidFuturesTradeRecommendationObservationError, match="earlier"):
        terminal.advance(_bar(7, *_L_STOP))


# ---------------------------------------------------------------------------
# 26-27. Determinism, replay and immutability
# ---------------------------------------------------------------------------

_PATH = (
    _bar(6, *_L_QUIET_ABOVE),
    _bar(7, *_L_ENTRY),
    _bar(8, *_L_INSIDE),
    _bar(9, *_L_BOTH),
)


def test_folding_the_same_bars_twice_gives_equal_lifecycles() -> None:
    first = _fold(_LONG, *_PATH)
    second = _fold(_LONG, *_PATH)

    assert first == second
    assert hash(first.events) == hash(second.events)
    assert _kinds(first) == [Kind.ENTRY_ACTIVATED, Kind.STOP_REACHED]


def test_a_lifecycle_rebuilt_from_its_parts_equals_the_advanced_one() -> None:
    advanced = _fold(_LONG, *_PATH)
    rebuilt = FuturesTradeRecommendationLifecycle(
        advanced.recommendation, advanced.events, advanced.last_observation
    )

    assert rebuilt == advanced
    assert rebuilt.status is Status.CLOSED_STOP


def test_reapplying_every_bar_after_a_full_fold_changes_nothing() -> None:
    lifecycle = _fold(_LONG, *_PATH)

    assert lifecycle.advance(_PATH[-1]) is lifecycle


def test_advance_never_mutates_its_input() -> None:
    before = _fold(_LONG, _bar(6, *_L_ENTRY))
    snapshot = (before.events, before.last_observation, before.status)

    after = before.advance(_bar(7, *_L_TARGET))

    assert (before.events, before.last_observation, before.status) == snapshot
    assert before.status is Status.ACTIVE
    assert after.status is Status.CLOSED_TARGET
    assert after.events[: len(before.events)] == before.events


def test_lifecycle_and_events_are_frozen() -> None:
    lifecycle = _fold(_LONG, _bar(6, *_L_ENTRY))

    with pytest.raises(dataclasses.FrozenInstanceError):
        lifecycle.events = ()  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        lifecycle.events[0].kind = Kind.TARGET_REACHED  # type: ignore[misc]


def test_the_same_path_produces_mirror_results_for_long_and_short() -> None:
    long = _fold(_LONG, _bar(6, *_L_ENTRY), _bar(7, *_L_BOTH))
    short = _fold(_SHORT, _bar(6, *_S_ENTRY), _bar(7, *_S_BOTH))

    assert long.status is short.status is Status.CLOSED_STOP
    assert [event.touched for event in long.events] == [event.touched for event in short.events]


# ---------------------------------------------------------------------------
# 28. No inferred intraday ordering and no execution claim
# ---------------------------------------------------------------------------


def test_events_carry_no_fill_price_quantity_or_profit() -> None:
    names = {field.name for field in dataclasses.fields(FuturesTradeRecommendationEvent)}

    assert names == {
        "recommendation",
        "kind",
        "observation",
        "touched",
        "ordering",
        "expiry_reason",
        "time_evidence",
    }


def test_only_two_orderings_ever_involve_more_than_one_boundary() -> None:
    lifecycle_events = [
        *_fold(_LONG, _bar(6, *_L_ENTRY), _bar(7, *_L_BOTH)).events,
        *_fold(_LONG, _bar(6, *_L_BOTH)).events,
        *_fold(_LONG, _bar(6, *_L_ENTRY), _bar(7, *_L_TARGET)).events,
    ]

    for event in lifecycle_events:
        if len(event.touched) > 1:
            assert event.ordering in (
                IntrabarOrdering.MODELED_STOP_FIRST,
                IntrabarOrdering.UNKNOWN,
            )
        else:
            assert event.ordering is IntrabarOrdering.NOT_REQUIRED


def test_the_activation_bar_never_also_closes_the_recommendation() -> None:
    for bounds in (_L_ENTRY, _L_ENTRY_STOP, _L_ENTRY_TARGET, _L_BOTH):
        lifecycle = _fold(_LONG, _bar(6, *bounds))
        assert len(lifecycle.events) == 1


# ---------------------------------------------------------------------------
# 23-24. Contradictory and forged histories
# ---------------------------------------------------------------------------


def _event(
    kind: RecommendationEventKind,
    bar: FuturesOHLCVBar,
    touched: tuple[RecommendationBoundary, ...],
    ordering: IntrabarOrdering = IntrabarOrdering.NOT_REQUIRED,
    *,
    identity: FuturesTradeRecommendationIdentity = _LONG.identity,
    expiry_reason: RecommendationExpiryReason | None = None,
) -> FuturesTradeRecommendationEvent:
    return FuturesTradeRecommendationEvent(identity, kind, bar, touched, ordering, expiry_reason)


_ENTRY_BAR = _bar(6, *_L_ENTRY)
_TARGET_BAR = _bar(7, *_L_TARGET)
_ACTIVATED = _event(Kind.ENTRY_ACTIVATED, _ENTRY_BAR, (_ENTRY,))
_TARGET_HIT = _event(Kind.TARGET_REACHED, _TARGET_BAR, (_TARGET,))


def _rebuild(
    events: tuple[FuturesTradeRecommendationEvent, ...],
    last: FuturesOHLCVBar | None,
    recommendation: FuturesTradeRecommendation = _LONG,
) -> FuturesTradeRecommendationLifecycle:
    return FuturesTradeRecommendationLifecycle(recommendation, events, last)


def test_a_valid_stored_history_is_accepted() -> None:
    assert _rebuild((_ACTIVATED, _TARGET_HIT), _TARGET_BAR).status is Status.CLOSED_TARGET


def test_a_close_without_an_activation_is_rejected() -> None:
    with pytest.raises(InvalidFuturesTradeRecommendationLifecycleError, match="not what"):
        _rebuild((_event(Kind.TARGET_REACHED, _TARGET_BAR, (_TARGET,)),), _TARGET_BAR)


def test_two_activations_are_rejected() -> None:
    second = _event(Kind.ENTRY_ACTIVATED, _bar(7, *_L_ENTRY), (_ENTRY,))

    with pytest.raises(InvalidFuturesTradeRecommendationLifecycleError, match="not what"):
        _rebuild((_ACTIVATED, second), second.observation)


def test_events_after_a_terminal_event_are_rejected() -> None:
    after = _event(Kind.STOP_REACHED, _bar(8, *_L_STOP), (_STOP,))

    with pytest.raises(InvalidFuturesTradeRecommendationLifecycleError, match="terminal"):
        _rebuild((_ACTIVATED, _TARGET_HIT, after), after.observation)


def test_events_out_of_chronological_order_are_rejected() -> None:
    later_activation = _event(Kind.ENTRY_ACTIVATED, _bar(8, *_L_ENTRY), (_ENTRY,))
    earlier_close = _event(Kind.TARGET_REACHED, _bar(7, *_L_TARGET), (_TARGET,))

    with pytest.raises(InvalidFuturesTradeRecommendationLifecycleError, match="increasing"):
        _rebuild((later_activation, earlier_close), later_activation.observation)


def test_a_history_is_never_re_sorted() -> None:
    with pytest.raises(InvalidFuturesTradeRecommendationLifecycleError):
        _rebuild((_TARGET_HIT, _ACTIVATED), _TARGET_BAR)


def test_an_event_of_another_recommendation_is_rejected() -> None:
    forged = _event(
        Kind.ENTRY_ACTIVATED,
        _ENTRY_BAR,
        (_ENTRY,),
        identity=FuturesTradeRecommendationIdentity("rec-other"),
    )

    with pytest.raises(InvalidFuturesTradeRecommendationLifecycleError, match="belong"):
        _rebuild((forged,), _ENTRY_BAR)


def test_an_event_whose_bar_did_not_touch_its_boundary_is_rejected() -> None:
    forged = _event(Kind.ENTRY_ACTIVATED, _bar(6, *_L_QUIET_ABOVE), (_ENTRY,))

    with pytest.raises(InvalidFuturesTradeRecommendationLifecycleError, match="not what"):
        _rebuild((forged,), forged.observation)


def test_a_stop_first_closure_relabelled_as_target_is_rejected() -> None:
    both = _bar(7, *_L_BOTH)
    forged = _event(Kind.TARGET_REACHED, both, (_TARGET,))

    with pytest.raises(InvalidFuturesTradeRecommendationLifecycleError, match="not what"):
        _rebuild((_ACTIVATED, forged), both)


def test_an_indeterminate_entry_relabelled_as_activation_is_rejected() -> None:
    ambiguous = _bar(6, *_L_ENTRY_STOP)
    forged = _event(Kind.ENTRY_ACTIVATED, ambiguous, (_ENTRY,))

    with pytest.raises(InvalidFuturesTradeRecommendationLifecycleError, match="not what"):
        _rebuild((forged,), ambiguous)


def test_a_wrong_expiry_reason_is_rejected() -> None:
    recommendation = _recommendation(valid_through=_instant(8))
    bar = _bar(9, *_L_QUIET_ABOVE)
    forged = _event(
        Kind.VALIDITY_EXPIRED,
        bar,
        (),
        expiry_reason=RecommendationExpiryReason.CONTRACT_CUTOFF_REACHED,
    )

    with pytest.raises(InvalidFuturesTradeRecommendationLifecycleError, match="not what"):
        _rebuild((forged,), bar, recommendation)


@pytest.mark.parametrize(
    "bar",
    [
        _bar(6, *_L_ENTRY, contract=_NOV),
        _bar(6, *_L_ENTRY, timeframe=Timeframe("1h")),
        _bar(5, *_L_ENTRY),
    ],
    ids=["other-contract", "other-timeframe", "before-issuance"],
)
def test_an_event_on_an_ineligible_observation_is_rejected(bar: FuturesOHLCVBar) -> None:
    forged = _event(Kind.ENTRY_ACTIVATED, bar, (_ENTRY,))

    with pytest.raises(InvalidFuturesTradeRecommendationLifecycleError):
        _rebuild((forged,), bar)


def test_events_require_a_last_observation() -> None:
    with pytest.raises(InvalidFuturesTradeRecommendationLifecycleError, match="last observation"):
        _rebuild((_ACTIVATED,), None)


def test_a_last_observation_earlier_than_the_last_event_is_rejected() -> None:
    with pytest.raises(InvalidFuturesTradeRecommendationLifecycleError, match="earlier"):
        _rebuild((_ACTIVATED, _TARGET_HIT), _ENTRY_BAR)


def test_a_last_observation_differing_from_the_last_event_bar_is_rejected() -> None:
    revised = _bar(7, *_L_TARGET, close="25550")

    with pytest.raises(InvalidFuturesTradeRecommendationLifecycleError, match="differs"):
        _rebuild((_ACTIVATED, _TARGET_HIT), revised)


def test_a_last_observation_after_a_terminal_event_is_rejected() -> None:
    with pytest.raises(InvalidFuturesTradeRecommendationLifecycleError, match="terminal"):
        _rebuild((_ACTIVATED, _TARGET_HIT), _bar(8, *_L_INSIDE))


def test_a_last_observation_that_would_have_produced_events_is_rejected() -> None:
    """A cursor past an unrecorded entry would hide an activation."""
    with pytest.raises(InvalidFuturesTradeRecommendationLifecycleError, match="unrecorded"):
        _rebuild((), _bar(6, *_L_ENTRY))


def test_a_waiting_cursor_with_no_events_is_accepted() -> None:
    assert _rebuild((), _bar(6, *_L_QUIET_ABOVE)).status is Status.WAITING_FOR_ENTRY


@pytest.mark.parametrize(
    ("recommendation", "events", "last", "message"),
    [
        ("not a recommendation", (), None, "FuturesTradeRecommendation"),
        (_LONG, [_ACTIVATED], _ENTRY_BAR, "tuple"),
        (_LONG, ("event",), None, "FuturesTradeRecommendationEvent"),
        (_LONG, (), "bar", "FuturesOHLCVBar"),
    ],
    ids=["recommendation", "events-list", "event-type", "last-observation"],
)
def test_lifecycle_parts_must_have_their_domain_types(
    recommendation: object, events: object, last: object, message: str
) -> None:
    with pytest.raises(InvalidFuturesTradeRecommendationLifecycleError, match=message):
        FuturesTradeRecommendationLifecycle(recommendation, events, last)  # type: ignore[arg-type]


def test_lifecycle_text() -> None:
    lifecycle = _fold(_LONG, _bar(6, *_L_ENTRY))

    assert str(lifecycle) == "rec-1 ACTIVE"
    assert repr(lifecycle).startswith("FuturesTradeRecommendationLifecycle(recommendation=")
