"""The lifecycle of one trade recommendation, and its pure transitions.

A lifecycle is the immutable recommendation, its ordered lifecycle events and
the latest completed bar it has evaluated. Its status is derived from the
events and never stored. ``last_observation`` exists because a bar that changes
nothing leaves no event: without it, a history could not show that a later bar
had already been consumed, so neither ordering nor idempotence could be proven.

Two pure, deterministic transitions read no clock, generate no identifier,
perform no I/O and mutate nothing.

``advance(bar)`` returns the lifecycle after one completed bar. Steps, in order:

1. The bar must be for the recommendation's contract and timeframe.
2. A bar completing before ``validity.eligible_from`` is ineligible: it is
   ignored and not consumed, and nothing changes. Its session began before the
   recommendation was issued, so its prices may predate the recommendation.
3. A bar earlier than ``last_observation`` is refused as out of order. The same
   bar again changes nothing; a different bar at that instant is refused as a
   revised observation.
4. A terminal lifecycle never changes again.
5. Otherwise the bar is evaluated and becomes ``last_observation``.

Evaluation asks only which boundaries the bar's inclusive range [low, high]
touched; a daily bar does not show the order of its high and low.

- After ``valid_through`` the window has passed: prices are not evaluated and
  the recommendation expires.
- Waiting: an untouched entry zone, including a gap past it, changes nothing.
  Entry alone activates. Entry with the stop or target is indeterminate and
  terminal, because the order cannot be known; no exit is evaluated on an
  activation bar and stop-first is never applied to one.
- Active: the stop alone closes at the stop and the target alone at the
  target. Both close at the stop under the conservative stop-first policy,
  recorded as MODELED_STOP_FIRST.
- At ``valid_through``, a recommendation still open after evaluation expires.

``expire(evidence)`` expires an open recommendation by time, for when no bar at
or after ``valid_through`` will arrive -- after a contract's last session none
can. Steps, in order:

1. A terminal lifecycle never changes again.
2. ``evidence.evaluated_through`` must be the completion instant of
   ``last_observation`` (both absent if no bar was evaluated), so the evidence
   describes this lifecycle's evaluated history; otherwise it is refused.
3. Before ``valid_through`` nothing changes: expiry is never premature.
4. Otherwise a VALIDITY_EXPIRED_BY_TIME event records the evidence. With
   complete verified coverage the status is EXPIRED_BEFORE_ENTRY or
   EXPIRED_AFTER_ACTIVATION; otherwise EXPIRED_WITH_INCOMPLETE_COVERAGE.

A bar available at ``valid_through`` should be advanced before expiring by time,
so its prices are evaluated; complete verified coverage asserts exactly that.
Once expired, a late bar never reopens or reclassifies the recommendation.

Building a lifecycle from stored parts replays its history and refuses anything
the transitions would not have produced.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime
from northstar_core.futures import FuturesOHLCVBar
from northstar_core.recommendations.futures.lifecycle.recommendation_event import (
    FuturesTradeRecommendationEvent,
    IntrabarOrdering,
    RecommendationBoundary,
    RecommendationEventKind,
    RecommendationExpiryReason,
)
from northstar_core.recommendations.futures.lifecycle.recommendation_status import (
    RecommendationStatus,
)
from northstar_core.recommendations.futures.lifecycle.time_expiry_evidence import (
    TimeExpiryEvidence,
)
from northstar_core.recommendations.futures.value_objects import (
    FuturesTradeRecommendation,
    TradeDirection,
)


class InvalidFuturesTradeRecommendationLifecycleError(ValidationError):
    """Raised when a lifecycle's history is not one its transitions produce."""


class InvalidFuturesTradeRecommendationObservationError(ValidationError):
    """Raised when advance refuses a bar for a recommendation's lifecycle."""


class InvalidFuturesTradeRecommendationExpiryError(ValidationError):
    """Raised when expire refuses time evidence for a recommendation's lifecycle."""


_ENTRY = RecommendationBoundary.ENTRY
_STOP = RecommendationBoundary.STOP
_TARGET = RecommendationBoundary.TARGET
_BY_TIME = RecommendationEventKind.VALIDITY_EXPIRED_BY_TIME


# -- observation tests ----------------------------------------------------------------


def _touches_entry(recommendation: FuturesTradeRecommendation, bar: FuturesOHLCVBar) -> bool:
    return bar.low <= recommendation.entry.high and bar.high >= recommendation.entry.low


def _touches_stop(recommendation: FuturesTradeRecommendation, bar: FuturesOHLCVBar) -> bool:
    if recommendation.direction is TradeDirection.LONG:
        return bar.low <= recommendation.stop.price
    return bar.high >= recommendation.stop.price


def _touches_target(recommendation: FuturesTradeRecommendation, bar: FuturesOHLCVBar) -> bool:
    if recommendation.direction is TradeDirection.LONG:
        return bar.high >= recommendation.target.price
    return bar.low <= recommendation.target.price


def _is_for_recommendation(
    recommendation: FuturesTradeRecommendation, bar: FuturesOHLCVBar
) -> bool:
    return bar.contract == recommendation.contract and (
        bar.timeframe == recommendation.source.timeframe
    )


def _is_eligible(recommendation: FuturesTradeRecommendation, bar: FuturesOHLCVBar) -> bool:
    return bar.point_in_time.compare(recommendation.validity.eligible_from) >= 0


def _same_instant(first: PointInTime | None, second: PointInTime | None) -> bool:
    if first is None or second is None:
        return first is None and second is None
    return first.compare(second) == 0


# -- transitions ----------------------------------------------------------------------


def _event(
    recommendation: FuturesTradeRecommendation,
    kind: RecommendationEventKind,
    bar: FuturesOHLCVBar,
    touched: tuple[RecommendationBoundary, ...],
    ordering: IntrabarOrdering = IntrabarOrdering.NOT_REQUIRED,
    expiry_reason: RecommendationExpiryReason | None = None,
) -> FuturesTradeRecommendationEvent:
    return FuturesTradeRecommendationEvent(
        recommendation=recommendation.identity,
        kind=kind,
        observation=bar,
        touched=touched,
        ordering=ordering,
        expiry_reason=expiry_reason,
    )


def _expiry_reason(recommendation: FuturesTradeRecommendation) -> RecommendationExpiryReason:
    if recommendation.validity.ends_at_contract_cutoff:
        return RecommendationExpiryReason.CONTRACT_CUTOFF_REACHED
    return RecommendationExpiryReason.VALIDITY_WINDOW_ENDED


def _expiry(
    recommendation: FuturesTradeRecommendation, bar: FuturesOHLCVBar
) -> FuturesTradeRecommendationEvent:
    return _event(
        recommendation,
        RecommendationEventKind.VALIDITY_EXPIRED,
        bar,
        (),
        expiry_reason=_expiry_reason(recommendation),
    )


def _time_expiry(
    recommendation: FuturesTradeRecommendation, evidence: TimeExpiryEvidence
) -> FuturesTradeRecommendationEvent:
    return FuturesTradeRecommendationEvent(
        recommendation=recommendation.identity,
        kind=_BY_TIME,
        observation=None,
        touched=(),
        ordering=IntrabarOrdering.NOT_REQUIRED,
        expiry_reason=_expiry_reason(recommendation),
        time_evidence=evidence,
    )


def _status_after(
    status: RecommendationStatus, event: FuturesTradeRecommendationEvent
) -> RecommendationStatus:
    if event.kind is RecommendationEventKind.ENTRY_ACTIVATED:
        return RecommendationStatus.ACTIVE
    if event.kind is RecommendationEventKind.ENTRY_INDETERMINATE:
        return RecommendationStatus.INDETERMINATE_ENTRY
    if event.kind is RecommendationEventKind.TARGET_REACHED:
        return RecommendationStatus.CLOSED_TARGET
    if event.kind is RecommendationEventKind.STOP_REACHED:
        return RecommendationStatus.CLOSED_STOP
    if event.kind is _BY_TIME and not (
        event.time_evidence is not None and event.time_evidence.is_verified
    ):
        return RecommendationStatus.EXPIRED_WITH_INCOMPLETE_COVERAGE
    if status is RecommendationStatus.ACTIVE:
        return RecommendationStatus.EXPIRED_AFTER_ACTIVATION
    return RecommendationStatus.EXPIRED_BEFORE_ENTRY


def _evaluate_waiting(
    recommendation: FuturesTradeRecommendation, bar: FuturesOHLCVBar
) -> tuple[FuturesTradeRecommendationEvent, ...]:
    if not _touches_entry(recommendation, bar):
        return ()
    exits = tuple(
        boundary
        for boundary, touched in (
            (_STOP, _touches_stop(recommendation, bar)),
            (_TARGET, _touches_target(recommendation, bar)),
        )
        if touched
    )
    if exits:
        return (
            _event(
                recommendation,
                RecommendationEventKind.ENTRY_INDETERMINATE,
                bar,
                (_ENTRY, *exits),
                IntrabarOrdering.UNKNOWN,
            ),
        )
    return (_event(recommendation, RecommendationEventKind.ENTRY_ACTIVATED, bar, (_ENTRY,)),)


def _evaluate_active(
    recommendation: FuturesTradeRecommendation, bar: FuturesOHLCVBar
) -> tuple[FuturesTradeRecommendationEvent, ...]:
    stop = _touches_stop(recommendation, bar)
    target = _touches_target(recommendation, bar)
    if stop and target:
        return (
            _event(
                recommendation,
                RecommendationEventKind.STOP_REACHED,
                bar,
                (_STOP, _TARGET),
                IntrabarOrdering.MODELED_STOP_FIRST,
            ),
        )
    if stop:
        return (_event(recommendation, RecommendationEventKind.STOP_REACHED, bar, (_STOP,)),)
    if target:
        return (_event(recommendation, RecommendationEventKind.TARGET_REACHED, bar, (_TARGET,)),)
    return ()


def _evaluate(
    recommendation: FuturesTradeRecommendation,
    status: RecommendationStatus,
    bar: FuturesOHLCVBar,
) -> tuple[FuturesTradeRecommendationEvent, ...]:
    """Return the events one eligible bar produces from a non-terminal status."""
    position_in_window = bar.point_in_time.compare(recommendation.validity.valid_through)
    if position_in_window > 0:
        return (_expiry(recommendation, bar),)

    if status is RecommendationStatus.WAITING_FOR_ENTRY:
        events = _evaluate_waiting(recommendation, bar)
    else:
        events = _evaluate_active(recommendation, bar)

    for event in events:
        status = _status_after(status, event)
    if position_in_window == 0 and not status.is_terminal:
        events = (*events, _expiry(recommendation, bar))
    return events


# -- history validation ---------------------------------------------------------------


def _lifecycle_error(message: str) -> InvalidFuturesTradeRecommendationLifecycleError:
    return InvalidFuturesTradeRecommendationLifecycleError(
        f"FuturesTradeRecommendationLifecycle {message}"
    )


def _require_observation_for(
    recommendation: FuturesTradeRecommendation, bar: FuturesOHLCVBar, what: str
) -> None:
    if not _is_for_recommendation(recommendation, bar):
        raise _lifecycle_error(f"{what} is not for the recommendation's contract and timeframe.")
    if not _is_eligible(recommendation, bar):
        raise _lifecycle_error(
            f"{what} completed before the recommendation's first eligible observation."
        )


def _split_time_expiry(
    events: tuple[FuturesTradeRecommendationEvent, ...],
) -> tuple[tuple[FuturesTradeRecommendationEvent, ...], FuturesTradeRecommendationEvent | None]:
    """Separate a trailing time expiry from the bar-evidenced events before it."""
    if events and events[-1].kind is _BY_TIME:
        bar_events, time_event = events[:-1], events[-1]
    else:
        bar_events, time_event = events, None
    if any(event.kind is _BY_TIME for event in bar_events):
        raise _lifecycle_error("can record a time expiry only as its last event.")
    return bar_events, time_event


def _replay(
    recommendation: FuturesTradeRecommendation,
    events: tuple[FuturesTradeRecommendationEvent, ...],
) -> tuple[RecommendationStatus, FuturesOHLCVBar | None]:
    """Replay bar events grouped by observation; return the status and last event bar."""
    status = RecommendationStatus.WAITING_FOR_ENTRY
    previous: FuturesOHLCVBar | None = None
    index = 0
    while index < len(events):
        bar = events[index].observation
        if bar is None:
            raise _lifecycle_error("can record a time expiry only as its last event.")
        end = index
        while end < len(events) and events[end].observation == bar:
            end += 1

        _require_observation_for(recommendation, bar, "event observation")
        if previous is not None and bar.point_in_time.compare(previous.point_in_time) <= 0:
            raise _lifecycle_error("events must follow strictly increasing observations.")
        if status.is_terminal:
            raise _lifecycle_error("cannot record events after a terminal event.")
        if _evaluate(recommendation, status, bar) != events[index:end]:
            raise _lifecycle_error(
                f"events at {bar.point_in_time} are not what that observation produces."
            )

        for event in events[index:end]:
            status = _status_after(status, event)
        previous = bar
        index = end
    return status, previous


def _validate_last_observation(
    recommendation: FuturesTradeRecommendation,
    status: RecommendationStatus,
    last_event_bar: FuturesOHLCVBar | None,
    last_observation: FuturesOHLCVBar | None,
) -> None:
    if last_observation is None:
        if last_event_bar is not None:
            raise _lifecycle_error("with events must record its last observation.")
        return

    _require_observation_for(recommendation, last_observation, "last observation")
    if last_event_bar is not None:
        position = last_observation.point_in_time.compare(last_event_bar.point_in_time)
        if position < 0:
            raise _lifecycle_error("last observation is earlier than its last event.")
        if position == 0:
            if last_observation != last_event_bar:
                raise _lifecycle_error("last observation differs from its last event's bar.")
            return
        if status.is_terminal:
            raise _lifecycle_error("cannot observe anything after a terminal event.")
    if _evaluate(recommendation, status, last_observation):
        raise _lifecycle_error("last observation would have produced unrecorded events.")


def _evaluated_through(last_observation: FuturesOHLCVBar | None) -> PointInTime | None:
    return None if last_observation is None else last_observation.point_in_time


def _validate_time_expiry(
    recommendation: FuturesTradeRecommendation,
    status: RecommendationStatus,
    last_observation: FuturesOHLCVBar | None,
    time_event: FuturesTradeRecommendationEvent,
) -> None:
    evidence = time_event.time_evidence
    if evidence is None:
        raise _lifecycle_error("time expiry must carry its time evidence.")
    if status.is_terminal:
        raise _lifecycle_error("cannot record a time expiry after a terminal event.")
    if evidence.as_of.compare(recommendation.validity.valid_through) < 0:
        raise _lifecycle_error("cannot record a time expiry before validity ends.")
    if not _same_instant(evidence.evaluated_through, _evaluated_through(last_observation)):
        raise _lifecycle_error("time expiry evidence does not match its last observation.")
    if _time_expiry(recommendation, evidence) != time_event:
        raise _lifecycle_error("time expiry is not what its evidence produces.")


def _validate_recommendation(value: FuturesTradeRecommendation) -> FuturesTradeRecommendation:
    if not isinstance(value, FuturesTradeRecommendation):
        raise _lifecycle_error("recommendation must be a FuturesTradeRecommendation value.")
    return value


def _validate_events(
    value: tuple[FuturesTradeRecommendationEvent, ...],
    recommendation: FuturesTradeRecommendation,
) -> tuple[FuturesTradeRecommendationEvent, ...]:
    if not isinstance(value, tuple):
        raise _lifecycle_error("events must be a tuple.")
    for event in value:
        if not isinstance(event, FuturesTradeRecommendationEvent):
            raise _lifecycle_error("events must be FuturesTradeRecommendationEvent values.")
        if event.recommendation != recommendation.identity:
            raise _lifecycle_error("events must belong to its recommendation.")
    return value


def _validate_last_observation_type(value: FuturesOHLCVBar | None) -> FuturesOHLCVBar | None:
    if value is not None and not isinstance(value, FuturesOHLCVBar):
        raise _lifecycle_error("last observation must be a FuturesOHLCVBar value or None.")
    return value


@dataclass(frozen=True, slots=True)
class FuturesTradeRecommendationLifecycle:
    """Immutable recommendation, ordered events and last evaluated observation."""

    recommendation: FuturesTradeRecommendation
    events: tuple[FuturesTradeRecommendationEvent, ...] = ()
    last_observation: FuturesOHLCVBar | None = None

    def __post_init__(self) -> None:
        recommendation = _validate_recommendation(self.recommendation)
        events = _validate_events(self.events, recommendation)
        last_observation = _validate_last_observation_type(self.last_observation)
        bar_events, time_event = _split_time_expiry(events)
        status, last_event_bar = _replay(recommendation, bar_events)
        _validate_last_observation(recommendation, status, last_event_bar, last_observation)
        if time_event is not None:
            _validate_time_expiry(recommendation, status, last_observation, time_event)

    @property
    def status(self) -> RecommendationStatus:
        """Return the state derived from the recorded events."""
        status = RecommendationStatus.WAITING_FOR_ENTRY
        for event in self.events:
            status = _status_after(status, event)
        return status

    @property
    def is_terminal(self) -> bool:
        """Return whether nothing can change this lifecycle any more."""
        return self.status.is_terminal

    def advance(self, bar: FuturesOHLCVBar) -> FuturesTradeRecommendationLifecycle:
        """Return this lifecycle after evaluating one completed bar."""
        if not isinstance(bar, FuturesOHLCVBar):
            raise InvalidFuturesTradeRecommendationObservationError(
                "FuturesTradeRecommendationLifecycle can only advance on a FuturesOHLCVBar."
            )
        recommendation = self.recommendation
        if not _is_for_recommendation(recommendation, bar):
            raise InvalidFuturesTradeRecommendationObservationError(
                f"Bar {bar.contract} {bar.timeframe} is not for recommendation "
                f"{recommendation.identity} on {recommendation.contract} "
                f"{recommendation.source.timeframe}."
            )
        if not _is_eligible(recommendation, bar):
            return self

        last = self.last_observation
        if last is not None:
            position = bar.point_in_time.compare(last.point_in_time)
            if position < 0:
                raise InvalidFuturesTradeRecommendationObservationError(
                    f"Bar at {bar.point_in_time} is earlier than the last evaluated "
                    f"observation at {last.point_in_time}."
                )
            if position == 0:
                if bar == last:
                    return self
                raise InvalidFuturesTradeRecommendationObservationError(
                    f"Bar at {bar.point_in_time} differs from the observation already "
                    "evaluated at that instant."
                )

        status = self.status
        if status.is_terminal:
            return self
        return FuturesTradeRecommendationLifecycle(
            recommendation=recommendation,
            events=(*self.events, *_evaluate(recommendation, status, bar)),
            last_observation=bar,
        )

    def expire(self, evidence: TimeExpiryEvidence) -> FuturesTradeRecommendationLifecycle:
        """Return this lifecycle expired by time, once validity has ended."""
        if not isinstance(evidence, TimeExpiryEvidence):
            raise InvalidFuturesTradeRecommendationExpiryError(
                "FuturesTradeRecommendationLifecycle can only expire on TimeExpiryEvidence."
            )
        if self.is_terminal:
            return self
        evaluated_through = _evaluated_through(self.last_observation)
        if not _same_instant(evidence.evaluated_through, evaluated_through):
            raise InvalidFuturesTradeRecommendationExpiryError(
                f"Time expiry evidence evaluated through {evidence.evaluated_through} does not "
                f"match the last evaluated observation at {evaluated_through}."
            )
        if evidence.as_of.compare(self.recommendation.validity.valid_through) < 0:
            return self
        return FuturesTradeRecommendationLifecycle(
            recommendation=self.recommendation,
            events=(*self.events, _time_expiry(self.recommendation, evidence)),
            last_observation=self.last_observation,
        )

    def __str__(self) -> str:
        return f"{self.recommendation.identity} {self.status}"

    def __repr__(self) -> str:
        return (
            "FuturesTradeRecommendationLifecycle("
            f"recommendation={self.recommendation!r}, "
            f"events={self.events!r}, "
            f"last_observation={self.last_observation!r}"
            ")"
        )
