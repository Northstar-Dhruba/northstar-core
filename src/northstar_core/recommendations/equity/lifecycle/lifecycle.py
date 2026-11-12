"""The lifecycle of one issued equity recommendation, and its pure transitions.

A lifecycle is a window and its ordered events. Its state is the fold of its
events and is never stored (EI5-D2, EI5-D5): building a lifecycle from stored
events replays them and refuses any history the transitions could not have
produced, so a stream that breaks EI5-D5 cannot be rehydrated.

Core does not issue. ``RECORDED`` is the state of an empty lifecycle, which a
caller builds only for a recommendation that its issuance authority has
durably recorded (EI5-D1, EI5-D2). An EI-4 generation proposal is never a
lifecycle.

The cursor
----------
The cursor is the opening of the next interval the lifecycle needs. It is
derived from the events: ``eligible_from`` until an activation, then the close
of the activation bar. A bar that changes nothing leaves no event, so each new
observation re-reads such bars from the cursor, under the evidence of that
later snapshot. Re-reading them never fabricates an event: the same evidence
gives the same answer, and corrected evidence for a past bar is
``UNRESOLVED_REVISIONS`` under EI-2A, which blocks rather than rewrites.

``advance(observation)``
------------------------
One evaluated snapshot: its ``as_of`` (the evaluation instant), its reference,
and its intervals from the cursor through the bar that closes at
``modeled_exit_at``, strictly ascending and contiguous. Steps, in order:

1. An observation older than the last event is refused. A terminal lifecycle
   never changes again: nothing is evaluated and no event is produced.
2. The intervals must start at the cursor, end exactly at ``modeled_exit_at``,
   carry prices in the levels' currency, and place the last entry bar's close
   at ``entry_window_ends_at``. Nothing after ``modeled_exit_at`` is accepted.
3. ``RECORDED``: before ``eligible_from`` nothing happens. Otherwise
   ``ENTRY_WINDOW_OPENED`` moves it to ``WAITING_FOR_ENTRY``.
4. Intervals are read in order from the cursor:

   - ``NOT_ENDED``: evaluation stops; the evidence is not due yet.
   - deficient (``MISSING``, ``UNFINALIZED``, ``CONFLICTING_VALUES``,
     ``UNRESOLVED_REVISIONS``): evaluation stops. Before the applicable
     boundary -- ``entry_window_ends_at`` while waiting, ``modeled_exit_at``
     while active -- this is a temporary block with no event. At or after it,
     ``EVIDENCE_INCOMPLETE`` lists every deficient interval from here to the
     boundary. A later acceptable interval is never used past a deficiency.
   - exact-boundary finality (EI5-D7 clarification, owner approved
     2026-11-12): when ``as_of`` equals the boundary and the bar closing there
     is ``MISSING`` or ``UNFINALIZED``, it is not final only because its close
     has just been reached. That is a temporary block, never terminal; a later
     snapshot decides by the rules above. ``CONFLICTING_VALUES`` and
     ``UNRESOLVED_REVISIONS`` are genuine deficiencies and are not excepted,
     nor is any earlier deficient interval. No settlement allowance (O-2) is
     introduced.
   - ``ACCEPTABLE``: the bar rules below apply.

Bar rules, LONG, by exact decimal comparison (O-1)
--------------------------------------------------
The entry zone is touched when the bar's range intersects it; gap-through never
activates. The stop is reached when ``low <= stop`` and the target when
``high >= target``, including a range wholly beyond the level.

Waiting, in order:

- zone and stop (with or without target): ``INDETERMINATE_ENTRY``, ordering
  ``UNKNOWN`` -- EI0-D9 and EI4-D5's clarification;
- zone and target: ``INDETERMINATE_ENTRY``, ordering ``UNKNOWN`` -- EI0-D9;
- zone alone: ``ACTIVE``, then ``SESSION_CUTOFF_REACHED`` on the same bar if
  it closes at ``modeled_exit_at``;
- stop alone, including a range wholly below it: ``CANCELLED_BEFORE_ENTRY``,
  ``STOP_TOUCHED_BEFORE_ENTRY`` -- EI4-D5;
- otherwise, on the bar that opens at ``latest_entry_bar_opens_at``:
  ``EXPIRED_BEFORE_ENTRY``.

Active, in order: stop and target, ``INDETERMINATE_EXIT`` with ordering
``UNKNOWN``; stop alone, ``CLOSED_STOP``; target alone, ``CLOSED_TARGET``;
otherwise, on the bar that closes at ``modeled_exit_at``,
``SESSION_CUTOFF_REACHED``. A touch always takes precedence over that bar's
expiry or cutoff, and exits are evaluated from the bar after activation.

No transition infers a fill, an execution price, an exit price or a profit.
Nothing reads a clock, generates an identifier, performs I/O or mutates state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime
from northstar_core.recommendations.equity.lifecycle.event import EquityLifecycleEvent
from northstar_core.recommendations.equity.lifecycle.evidence import (
    EquityEvidenceDeficiency,
    EquityLifecycleEvidence,
    EquityLifecycleInterval,
    EquityLifecycleObservation,
    InvalidEquityLifecycleObservationError,
)
from northstar_core.recommendations.equity.lifecycle.vocabulary import (
    EquityEvidenceDeficiencyKind,
    EquityIntrabarOrdering,
    EquityLifecycleCancellationReason,
    EquityLifecycleEventKind,
    EquityLifecycleIntervalOutcome,
    EquityLifecycleLevel,
    EquityLifecycleState,
    EquityRevisionMateriality,
)
from northstar_core.recommendations.equity.lifecycle.window import EquityLifecycleWindow

_K = EquityLifecycleEventKind
_S = EquityLifecycleState
_L = EquityLifecycleLevel

_ENTRY_KINDS = frozenset(
    {_K.ENTRY_ACTIVATED, _K.ENTRY_INDETERMINATE, _K.ENTRY_CANCELLED, _K.ENTRY_WINDOW_EXPIRED}
)
_EXIT_KINDS = frozenset({_K.TARGET_REACHED, _K.STOP_REACHED, _K.EXIT_INDETERMINATE})


class InvalidEquityRecommendationLifecycleError(ValidationError):
    """Raised when a lifecycle history is not one the transitions could produce."""


class EquityLifecycleAdvanceStatus(StrEnum):
    """Where an ``advance`` stopped."""

    NOT_YET_ELIGIBLE = "NOT_YET_ELIGIBLE"
    AWAITING_EVIDENCE = "AWAITING_EVIDENCE"
    BLOCKED = "BLOCKED"
    TERMINAL = "TERMINAL"


def _before(first: PointInTime, second: PointInTime) -> bool:
    return first.compare(second) < 0


def _after(first: PointInTime, second: PointInTime) -> bool:
    return first.compare(second) > 0


_NOT_YET_FINAL = frozenset(
    {EquityEvidenceDeficiencyKind.MISSING, EquityEvidenceDeficiencyKind.UNFINALIZED}
)


def _awaiting_boundary_finality(
    kind: EquityEvidenceDeficiencyKind | None,
    closes_at: PointInTime,
    evaluated_at: PointInTime,
    boundary: PointInTime,
) -> bool:
    """Return whether a deficiency is only the boundary bar not yet final at the boundary.

    EI5-D7 exact-boundary clarification: at ``evaluated_at == boundary`` the bar
    closing at the boundary has only just ended, so ``MISSING`` or ``UNFINALIZED``
    there blocks temporarily and is never terminal.
    """
    return (
        kind in _NOT_YET_FINAL
        and evaluated_at.compare(boundary) == 0
        and closes_at.compare(boundary) == 0
    )


@dataclass(frozen=True, slots=True)
class _Replayed:
    state: EquityLifecycleState
    cursor: PointInTime | None
    last_evaluated_at: PointInTime | None


def _lifecycle_error(message: str) -> InvalidEquityRecommendationLifecycleError:
    return InvalidEquityRecommendationLifecycleError(message)


def _require_entry_interval(
    window: EquityLifecycleWindow, evidence: EquityLifecycleEvidence, cursor: PointInTime
) -> None:
    if _before(evidence.opens_at, cursor) or _after(
        evidence.opens_at, window.latest_entry_bar_opens_at
    ):
        raise _lifecycle_error(
            f"An entry event cites the bar opening {evidence.opens_at}, outside the entry "
            f"window from {cursor} to {window.latest_entry_bar_opens_at}."
        )
    if (
        evidence.opens_at == window.latest_entry_bar_opens_at
        and evidence.closes_at != window.entry_window_ends_at
    ):
        raise _lifecycle_error("The last entry bar must close at entry_window_ends_at.")


def _require_exit_interval(
    window: EquityLifecycleWindow, evidence: EquityLifecycleEvidence, cursor: PointInTime
) -> None:
    if _before(evidence.opens_at, cursor) or _after(evidence.closes_at, window.modeled_exit_at):
        raise _lifecycle_error(
            f"An exit event cites the bar opening {evidence.opens_at}, outside the exit range "
            f"from {cursor} to {window.modeled_exit_at}."
        )


def _require_revision(
    event: EquityLifecycleEvent,
    earlier: tuple[EquityLifecycleEvent, ...],
    state: EquityLifecycleState,
    recorded: set[tuple[int, EquityLifecycleEvidence]],
) -> None:
    assert event.cited_sequence is not None
    cited = earlier[event.cited_sequence - 1]
    if not cited.kind.is_bar_driven:
        raise _lifecycle_error("A revision can cite only an event resting on an acceptable bar.")
    if event.superseded_evidence != cited.evidence:
        raise _lifecycle_error("A revision's superseded evidence must be the cited event's.")
    if event.from_state is not state:
        raise _lifecycle_error("A revision must record the lifecycle's current state unchanged.")
    if (event.cited_sequence, event.evidence) in recorded:
        raise _lifecycle_error("The same revision of the same cited event is already recorded.")


def _replay(window: EquityLifecycleWindow, events: tuple[EquityLifecycleEvent, ...]) -> _Replayed:
    state = _S.RECORDED
    cursor = window.eligible_from
    last: PointInTime | None = None
    previous_state_event: EquityLifecycleEvent | None = None
    recorded: set[tuple[int, EquityLifecycleEvidence]] = set()
    for index, event in enumerate(events, start=1):
        if not isinstance(event, EquityLifecycleEvent):
            raise _lifecycle_error("A lifecycle's events must be EquityLifecycleEvents.")
        if event.sequence != index:
            raise _lifecycle_error(
                f"Event {index} has sequence {event.sequence}: sequences are contiguous from 1."
            )
        if last is not None and _before(event.evaluated_at, last):
            raise _lifecycle_error("Event evaluation instants must not decrease.")
        last = event.evaluated_at
        if not event.changes_state:
            _require_revision(event, events[: index - 1], state, recorded)
            assert event.cited_sequence is not None
            recorded.add((event.cited_sequence, event.evidence))
            continue
        if state.is_terminal:
            raise _lifecycle_error(f"{state} is terminal: no state may change after it.")
        if event.from_state is not state:
            raise _lifecycle_error(
                f"{event.kind} leaves {event.from_state}, but the state is {state}."
            )
        evidence, kind = event.evidence, event.kind
        if kind is _K.ENTRY_WINDOW_OPENED:
            if _before(event.evaluated_at, window.eligible_from):
                raise _lifecycle_error("The entry window cannot open before eligible_from.")
            if evidence.opens_at != window.eligible_from:
                raise _lifecycle_error(
                    "ENTRY_WINDOW_OPENED must cite the bar opening at eligible_from."
                )
        elif kind in _ENTRY_KINDS:
            _require_entry_interval(window, evidence, cursor)
            if (
                kind is _K.ENTRY_WINDOW_EXPIRED
                and evidence.opens_at != window.latest_entry_bar_opens_at
            ):
                raise _lifecycle_error(
                    "Expiry must cite the bar opening at the latest entry opening."
                )
            if kind is _K.ENTRY_ACTIVATED:
                cursor = evidence.closes_at
        elif kind in _EXIT_KINDS:
            _require_exit_interval(window, evidence, cursor)
        elif kind is _K.SESSION_CUTOFF_REACHED:
            if evidence.closes_at != window.modeled_exit_at:
                raise _lifecycle_error("The cutoff must cite the bar closing at modeled_exit_at.")
            on_activation_bar = (
                previous_state_event is not None
                and previous_state_event.kind is _K.ENTRY_ACTIVATED
                and previous_state_event.evidence == evidence
            )
            if not on_activation_bar:
                _require_exit_interval(window, evidence, cursor)
        else:
            boundary = (
                window.entry_window_ends_at
                if state is _S.WAITING_FOR_ENTRY
                else window.modeled_exit_at
            )
            if _before(event.evaluated_at, boundary):
                raise _lifecycle_error(
                    f"INCOMPLETE_EVIDENCE at {event.evaluated_at} precedes the boundary {boundary}."
                )
            first = event.deficiencies[0]
            if _before(first.opens_at, cursor):
                raise _lifecycle_error("A deficiency cannot precede the cursor.")
            if _awaiting_boundary_finality(
                first.kind, first.closes_at, event.evaluated_at, boundary
            ):
                raise _lifecycle_error(
                    "INCOMPLETE_EVIDENCE cannot rest on the boundary bar merely not yet final "
                    "at the boundary instant: that is a temporary block."
                )
            if any(_after(item.closes_at, boundary) for item in event.deficiencies):
                raise _lifecycle_error("A deficiency cannot lie beyond the applicable boundary.")
        state = event.to_state
        previous_state_event = event
    return _Replayed(state, None if state.is_terminal else cursor, last)


def _require_coverage(
    window: EquityLifecycleWindow, cursor: PointInTime, observation: EquityLifecycleObservation
) -> None:
    error = InvalidEquityLifecycleObservationError
    intervals = observation.intervals
    if intervals[0].opens_at != cursor:
        raise error(
            f"The observation starts at {intervals[0].opens_at}, not at the cursor {cursor}: "
            "intervals before the cursor are never re-evaluated, and none may be skipped."
        )
    if intervals[-1].closes_at != window.modeled_exit_at:
        raise error(
            f"The observation ends at {intervals[-1].closes_at}, not at modeled_exit_at "
            f"{window.modeled_exit_at}: it must reach the exit boundary and nothing after it."
        )
    currency = window.levels.currency
    for interval in intervals:
        if interval.low is not None and interval.low.currency != currency:
            raise error("An acceptable bar is not in the levels' currency.")
        if (
            interval.opens_at == window.latest_entry_bar_opens_at
            and interval.closes_at != window.entry_window_ends_at
        ):
            raise error("The last entry bar must close at entry_window_ends_at.")


class _Emitter:
    __slots__ = ("events", "evaluated_at", "next_sequence")

    def __init__(self, first_sequence: int, evaluated_at: PointInTime) -> None:
        self.events: list[EquityLifecycleEvent] = []
        self.evaluated_at = evaluated_at
        self.next_sequence = first_sequence

    def emit(
        self,
        kind: EquityLifecycleEventKind,
        from_state: EquityLifecycleState,
        to_state: EquityLifecycleState,
        evidence: EquityLifecycleEvidence,
        touched: tuple[EquityLifecycleLevel, ...] = (),
        ordering: EquityIntrabarOrdering = EquityIntrabarOrdering.NOT_REQUIRED,
        reason: EquityLifecycleCancellationReason | None = None,
        deficiencies: tuple[EquityEvidenceDeficiency, ...] = (),
    ) -> EquityLifecycleState:
        event = EquityLifecycleEvent(
            sequence=self.next_sequence,
            kind=kind,
            from_state=from_state,
            to_state=to_state,
            evaluated_at=self.evaluated_at,
            evidence=evidence,
            touched=touched,
            ordering=ordering,
            reason=reason,
            deficiencies=deficiencies,
        )
        self.events.append(event)
        self.next_sequence += 1
        return to_state


def _evaluate_waiting(
    window: EquityLifecycleWindow,
    interval: EquityLifecycleInterval,
    evidence: EquityLifecycleEvidence,
    out: _Emitter,
) -> EquityLifecycleState:
    assert interval.low is not None and interval.high is not None
    if _after(interval.opens_at, window.latest_entry_bar_opens_at):
        raise _lifecycle_error("A waiting lifecycle cannot read a bar after the entry window.")
    zone = window.entry_touched(interval.low, interval.high)
    stop = window.stop_reached(interval.low)
    target = window.target_reached(interval.high)
    waiting = _S.WAITING_FOR_ENTRY
    if zone and (stop or target):
        touched = (_L.ENTRY,) + ((_L.STOP,) if stop else ()) + ((_L.TARGET,) if target else ())
        return out.emit(
            _K.ENTRY_INDETERMINATE,
            waiting,
            _S.INDETERMINATE_ENTRY,
            evidence,
            touched,
            EquityIntrabarOrdering.UNKNOWN,
        )
    if zone:
        state = out.emit(_K.ENTRY_ACTIVATED, waiting, _S.ACTIVE, evidence, (_L.ENTRY,))
        if interval.closes_at == window.modeled_exit_at:
            state = out.emit(_K.SESSION_CUTOFF_REACHED, state, _S.SESSION_CUTOFF_REACHED, evidence)
        return state
    if stop:
        return out.emit(
            _K.ENTRY_CANCELLED,
            waiting,
            _S.CANCELLED_BEFORE_ENTRY,
            evidence,
            (_L.STOP,),
            reason=EquityLifecycleCancellationReason.STOP_TOUCHED_BEFORE_ENTRY,
        )
    if interval.opens_at == window.latest_entry_bar_opens_at:
        touched = (_L.TARGET,) if target else ()
        return out.emit(
            _K.ENTRY_WINDOW_EXPIRED, waiting, _S.EXPIRED_BEFORE_ENTRY, evidence, touched
        )
    return waiting


def _evaluate_active(
    window: EquityLifecycleWindow,
    interval: EquityLifecycleInterval,
    evidence: EquityLifecycleEvidence,
    out: _Emitter,
) -> EquityLifecycleState:
    assert interval.low is not None and interval.high is not None
    stop = window.stop_reached(interval.low)
    target = window.target_reached(interval.high)
    active = _S.ACTIVE
    if stop and target:
        return out.emit(
            _K.EXIT_INDETERMINATE,
            active,
            _S.INDETERMINATE_EXIT,
            evidence,
            (_L.STOP, _L.TARGET),
            EquityIntrabarOrdering.UNKNOWN,
        )
    if stop:
        return out.emit(_K.STOP_REACHED, active, _S.CLOSED_STOP, evidence, (_L.STOP,))
    if target:
        return out.emit(_K.TARGET_REACHED, active, _S.CLOSED_TARGET, evidence, (_L.TARGET,))
    if interval.closes_at == window.modeled_exit_at:
        return out.emit(_K.SESSION_CUTOFF_REACHED, active, _S.SESSION_CUTOFF_REACHED, evidence)
    return active


@dataclass(frozen=True, slots=True)
class EquityRecommendationLifecycle:
    """One issued recommendation's window and its ordered lifecycle events.

    Equality is by window and events. The state, cursor and last evaluation
    instant are derived by replay and are not compared separately.
    """

    window: EquityLifecycleWindow
    events: tuple[EquityLifecycleEvent, ...] = ()
    _replayed: _Replayed = field(init=False, repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.window, EquityLifecycleWindow):
            raise _lifecycle_error("A lifecycle window must be an EquityLifecycleWindow.")
        if not isinstance(self.events, tuple):
            raise _lifecycle_error("A lifecycle's events must be a tuple.")
        object.__setattr__(self, "_replayed", _replay(self.window, self.events))

    @property
    def state(self) -> EquityLifecycleState:
        """Return the state derived from the events."""
        return self._replayed.state

    @property
    def is_terminal(self) -> bool:
        """Return whether monitoring has ended."""
        return self.state.is_terminal

    @property
    def cursor(self) -> PointInTime | None:
        """Return the opening of the next interval needed, or None once terminal."""
        return self._replayed.cursor

    @property
    def last_evaluated_at(self) -> PointInTime | None:
        """Return the evaluation instant of the latest event, or None without events."""
        return self._replayed.last_evaluated_at

    def advance(self, observation: EquityLifecycleObservation) -> EquityLifecycleAdvance:
        """Return the lifecycle after evaluating one observation; see the module docstring."""
        if not isinstance(observation, EquityLifecycleObservation):
            raise InvalidEquityLifecycleObservationError(
                "advance needs an EquityLifecycleObservation."
            )
        at = observation.evaluated_at
        last = self.last_evaluated_at
        if last is not None and _before(at, last):
            raise InvalidEquityLifecycleObservationError(
                f"The observation at {at} is older than the last event at {last}."
            )
        if self.is_terminal:
            return EquityLifecycleAdvance(self, (), EquityLifecycleAdvanceStatus.TERMINAL)
        cursor = self.cursor
        assert cursor is not None
        window = self.window
        _require_coverage(window, cursor, observation)
        out = _Emitter(len(self.events) + 1, at)
        intervals = observation.intervals
        state = self.state
        halted: tuple[EquityLifecycleAdvanceStatus, EquityLifecycleInterval] | None = None
        if state is _S.RECORDED:
            if _before(at, window.eligible_from):
                return EquityLifecycleAdvance(
                    self, (), EquityLifecycleAdvanceStatus.NOT_YET_ELIGIBLE
                )
            first = intervals[0]
            state = out.emit(
                _K.ENTRY_WINDOW_OPENED,
                _S.RECORDED,
                _S.WAITING_FOR_ENTRY,
                EquityLifecycleEvidence(observation.reference, first.opens_at, first.closes_at),
            )
        for index, interval in enumerate(intervals):
            if interval.outcome is EquityLifecycleIntervalOutcome.NOT_ENDED:
                halted = (EquityLifecycleAdvanceStatus.AWAITING_EVIDENCE, interval)
                break
            if interval.deficiency_kind is not None:
                boundary = (
                    window.entry_window_ends_at
                    if state is _S.WAITING_FOR_ENTRY
                    else window.modeled_exit_at
                )
                if _before(at, boundary) or _awaiting_boundary_finality(
                    interval.deficiency_kind, interval.closes_at, at, boundary
                ):
                    halted = (EquityLifecycleAdvanceStatus.BLOCKED, interval)
                    break
                deficiencies = tuple(
                    item.deficiency()
                    for item in intervals[index:]
                    if item.deficiency_kind is not None and not _after(item.closes_at, boundary)
                )
                state = out.emit(
                    _K.EVIDENCE_INCOMPLETE,
                    state,
                    _S.INCOMPLETE_EVIDENCE,
                    EquityLifecycleEvidence(
                        observation.reference, interval.opens_at, interval.closes_at
                    ),
                    deficiencies=deficiencies,
                )
                break
            evidence = EquityLifecycleEvidence(
                observation.reference, interval.opens_at, interval.closes_at, interval.observations
            )
            if state is _S.WAITING_FOR_ENTRY:
                state = _evaluate_waiting(window, interval, evidence, out)
            else:
                state = _evaluate_active(window, interval, evidence, out)
            if state.is_terminal:
                break
        lifecycle = EquityRecommendationLifecycle(window, self.events + tuple(out.events))
        if lifecycle.is_terminal:
            return EquityLifecycleAdvance(
                lifecycle, tuple(out.events), EquityLifecycleAdvanceStatus.TERMINAL
            )
        if halted is None:
            raise _lifecycle_error(
                "An observation reaching modeled_exit_at must end the lifecycle."
            )
        return EquityLifecycleAdvance(lifecycle, tuple(out.events), halted[0], halted[1])

    def record_source_revision(
        self,
        cited_sequence: int,
        evidence: EquityLifecycleEvidence,
        evaluated_at: PointInTime,
    ) -> EquityRecommendationLifecycle:
        """Return the lifecycle with a correction to a cited bar's evidence recorded (EI5-D8).

        The state never changes, materiality stays ``UNASSESSED`` and the cited
        event is never rewritten. Recording the same correction of the same
        cited event again returns this lifecycle unchanged. Detecting a
        correction is the caller's: Core only records it.
        """
        if (
            isinstance(cited_sequence, bool)
            or not isinstance(cited_sequence, int)
            or not 1 <= cited_sequence <= len(self.events)
        ):
            raise _lifecycle_error("A revision must cite an existing event's sequence.")
        if not isinstance(evidence, EquityLifecycleEvidence):
            raise _lifecycle_error("A revision's new evidence must be EquityLifecycleEvidence.")
        for event in self.events:
            if (
                event.kind is _K.SOURCE_REVISION_RECORDED
                and event.cited_sequence == cited_sequence
                and event.evidence == evidence
            ):
                return self
        cited = self.events[cited_sequence - 1]
        revision = EquityLifecycleEvent(
            sequence=len(self.events) + 1,
            kind=_K.SOURCE_REVISION_RECORDED,
            from_state=self.state,
            to_state=self.state,
            evaluated_at=evaluated_at,
            evidence=evidence,
            cited_sequence=cited_sequence,
            superseded_evidence=cited.evidence,
            materiality=EquityRevisionMateriality.UNASSESSED,
        )
        return EquityRecommendationLifecycle(self.window, self.events + (revision,))


@dataclass(frozen=True, slots=True)
class EquityLifecycleAdvance:
    """The result of one ``advance``: the new lifecycle, the events it added, and where it stopped.

    ``halted_at`` is the interval evaluation stopped at -- present exactly when
    the status is ``AWAITING_EVIDENCE`` (not ended) or ``BLOCKED`` (deficient
    before the boundary, or the boundary bar not yet final exactly at it).
    """

    lifecycle: EquityRecommendationLifecycle
    events: tuple[EquityLifecycleEvent, ...]
    status: EquityLifecycleAdvanceStatus
    halted_at: EquityLifecycleInterval | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.lifecycle, EquityRecommendationLifecycle):
            raise _lifecycle_error(
                "An advance's lifecycle must be an EquityRecommendationLifecycle."
            )
        if not isinstance(self.status, EquityLifecycleAdvanceStatus):
            raise _lifecycle_error("An advance's status must be an EquityLifecycleAdvanceStatus.")
        count = len(self.events)
        if not isinstance(self.events, tuple) or (
            count and self.lifecycle.events[-count:] != self.events
        ):
            raise _lifecycle_error("An advance's events must be the lifecycle's latest events.")
        halts = self.status in (
            EquityLifecycleAdvanceStatus.AWAITING_EVIDENCE,
            EquityLifecycleAdvanceStatus.BLOCKED,
        )
        if halts != isinstance(self.halted_at, EquityLifecycleInterval):
            raise _lifecycle_error("halted_at is present exactly when evaluation halted.")
        if (self.status is EquityLifecycleAdvanceStatus.TERMINAL) != self.lifecycle.is_terminal:
            raise _lifecycle_error("The TERMINAL status must match a terminal lifecycle.")
