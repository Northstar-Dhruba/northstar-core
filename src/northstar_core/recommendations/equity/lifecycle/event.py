"""Immutable lifecycle events and their allowed shapes (EI-5 design section 5.3).

Every event matches exactly one row of ``_SHAPES``: its kind fixes the states it
may leave and enter, the levels it may report as touched or reached, and the
intrabar ordering. Anything else is refused at construction.

An event is a lifecycle fact, never an execution. It has no price, quantity,
order, fill, account or profit field. ``touched`` names levels, not prices, and
an ``UNKNOWN`` ordering is never resolved into a modeled order (EI0-D9).

Rules that need the window or earlier events -- interval ranges, the cursor,
boundaries, citations -- are checked when a lifecycle is built from its events.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime
from northstar_core.recommendations.equity.lifecycle.evidence import (
    EquityEvidenceDeficiency,
    EquityLifecycleEvidence,
)
from northstar_core.recommendations.equity.lifecycle.vocabulary import (
    EquityIntrabarOrdering,
    EquityLifecycleCancellationReason,
    EquityLifecycleEventKind,
    EquityLifecycleLevel,
    EquityLifecycleState,
    EquityRevisionMateriality,
)


class InvalidEquityLifecycleEventError(ValidationError):
    """Raised when a lifecycle event does not match an allowed shape."""


_K = EquityLifecycleEventKind
_S = EquityLifecycleState
_L = EquityLifecycleLevel
_O = EquityIntrabarOrdering

_NONE: tuple[EquityLifecycleLevel, ...] = ()


@dataclass(frozen=True, slots=True)
class _Shape:
    sources: frozenset[EquityLifecycleState] | None  # None: any state (a non-state event)
    target: EquityLifecycleState | None  # None: the same state
    touched: frozenset[tuple[EquityLifecycleLevel, ...]]
    ordering: EquityIntrabarOrdering


_SHAPES: dict[EquityLifecycleEventKind, _Shape] = {
    _K.ENTRY_WINDOW_OPENED: _Shape(
        frozenset({_S.RECORDED}), _S.WAITING_FOR_ENTRY, frozenset({_NONE}), _O.NOT_REQUIRED
    ),
    _K.ENTRY_ACTIVATED: _Shape(
        frozenset({_S.WAITING_FOR_ENTRY}), _S.ACTIVE, frozenset({(_L.ENTRY,)}), _O.NOT_REQUIRED
    ),
    _K.ENTRY_INDETERMINATE: _Shape(
        frozenset({_S.WAITING_FOR_ENTRY}),
        _S.INDETERMINATE_ENTRY,
        frozenset({(_L.ENTRY, _L.STOP), (_L.ENTRY, _L.TARGET), (_L.ENTRY, _L.STOP, _L.TARGET)}),
        _O.UNKNOWN,
    ),
    _K.ENTRY_CANCELLED: _Shape(
        frozenset({_S.WAITING_FOR_ENTRY}),
        _S.CANCELLED_BEFORE_ENTRY,
        frozenset({(_L.STOP,)}),
        _O.NOT_REQUIRED,
    ),
    _K.ENTRY_WINDOW_EXPIRED: _Shape(
        frozenset({_S.WAITING_FOR_ENTRY}),
        _S.EXPIRED_BEFORE_ENTRY,
        frozenset({_NONE, (_L.TARGET,)}),
        _O.NOT_REQUIRED,
    ),
    _K.TARGET_REACHED: _Shape(
        frozenset({_S.ACTIVE}), _S.CLOSED_TARGET, frozenset({(_L.TARGET,)}), _O.NOT_REQUIRED
    ),
    _K.STOP_REACHED: _Shape(
        frozenset({_S.ACTIVE}), _S.CLOSED_STOP, frozenset({(_L.STOP,)}), _O.NOT_REQUIRED
    ),
    _K.EXIT_INDETERMINATE: _Shape(
        frozenset({_S.ACTIVE}),
        _S.INDETERMINATE_EXIT,
        frozenset({(_L.STOP, _L.TARGET)}),
        _O.UNKNOWN,
    ),
    _K.SESSION_CUTOFF_REACHED: _Shape(
        frozenset({_S.ACTIVE}), _S.SESSION_CUTOFF_REACHED, frozenset({_NONE}), _O.NOT_REQUIRED
    ),
    _K.EVIDENCE_INCOMPLETE: _Shape(
        frozenset({_S.WAITING_FOR_ENTRY, _S.ACTIVE}),
        _S.INCOMPLETE_EVIDENCE,
        frozenset({_NONE}),
        _O.NOT_REQUIRED,
    ),
    _K.SOURCE_REVISION_RECORDED: _Shape(None, None, frozenset({_NONE}), _O.NOT_REQUIRED),
}


@dataclass(frozen=True, slots=True)
class EquityLifecycleEvent:
    """One immutable lifecycle event.

    - ``sequence`` counts from 1 within one lifecycle.
    - ``evaluated_at`` is the evaluated snapshot's ``as_of``, never a clock reading.
    - ``evidence`` names the snapshot and the interval the event rests on.
    - ``reason`` is required for, and only for, ``ENTRY_CANCELLED``.
    - ``deficiencies`` are required for, and only for, ``EVIDENCE_INCOMPLETE``.
    - ``cited_sequence``, ``superseded_evidence`` and ``materiality`` are required
      for, and only for, ``SOURCE_REVISION_RECORDED``. ``evidence`` is then the new
      evidence for the cited interval.
    """

    sequence: int
    kind: EquityLifecycleEventKind
    from_state: EquityLifecycleState
    to_state: EquityLifecycleState
    evaluated_at: PointInTime
    evidence: EquityLifecycleEvidence
    touched: tuple[EquityLifecycleLevel, ...] = ()
    ordering: EquityIntrabarOrdering = EquityIntrabarOrdering.NOT_REQUIRED
    reason: EquityLifecycleCancellationReason | None = None
    deficiencies: tuple[EquityEvidenceDeficiency, ...] = ()
    cited_sequence: int | None = None
    superseded_evidence: EquityLifecycleEvidence | None = None
    materiality: EquityRevisionMateriality | None = None

    def __post_init__(self) -> None:
        self._validate_types()
        shape = _SHAPES[self.kind]
        self._validate_shape(shape)
        self._validate_evidence()
        self._validate_reason()
        self._validate_deficiencies()
        self._validate_revision()

    @property
    def changes_state(self) -> bool:
        """Return whether this event is a state transition."""
        return self.kind.changes_state

    def _validate_types(self) -> None:
        error = InvalidEquityLifecycleEventError
        sequence = self.sequence
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
            raise error("A lifecycle event sequence must be an integer of at least 1.")
        if not isinstance(self.kind, EquityLifecycleEventKind):
            raise error("A lifecycle event kind must be an EquityLifecycleEventKind.")
        for name in ("from_state", "to_state"):
            if not isinstance(getattr(self, name), EquityLifecycleState):
                raise error(f"A lifecycle event {name} must be an EquityLifecycleState.")
        if not isinstance(self.evaluated_at, PointInTime):
            raise error("A lifecycle event evaluated_at must be a PointInTime.")
        if not isinstance(self.evidence, EquityLifecycleEvidence):
            raise error("A lifecycle event evidence must be EquityLifecycleEvidence.")
        if not isinstance(self.touched, tuple) or not all(
            isinstance(level, EquityLifecycleLevel) for level in self.touched
        ):
            raise error("A lifecycle event touched must be a tuple of EquityLifecycleLevel.")
        if not isinstance(self.ordering, EquityIntrabarOrdering):
            raise error("A lifecycle event ordering must be an EquityIntrabarOrdering.")
        if not isinstance(self.deficiencies, tuple) or not all(
            isinstance(item, EquityEvidenceDeficiency) for item in self.deficiencies
        ):
            raise error("A lifecycle event deficiencies must be a tuple of deficiencies.")

    def _validate_shape(self, shape: _Shape) -> None:
        error = InvalidEquityLifecycleEventError
        if shape.sources is not None and self.from_state not in shape.sources:
            raise error(f"{self.kind} cannot leave {self.from_state}.")
        expected = self.from_state if shape.target is None else shape.target
        if self.to_state is not expected:
            raise error(f"{self.kind} from {self.from_state} must enter {expected}.")
        if self.touched not in shape.touched:
            raise error(f"{self.kind} cannot report touched levels {self.touched}.")
        if self.ordering is not shape.ordering:
            raise error(f"{self.kind} requires ordering {shape.ordering}.")

    def _validate_evidence(self) -> None:
        error = InvalidEquityLifecycleEventError
        evidence = self.evidence
        if self.kind.is_bar_driven:
            if not evidence.observations:
                raise error(f"{self.kind} rests on an acceptable bar and must cite its candles.")
            if evidence.closes_at.compare(self.evaluated_at) > 0:
                raise error(
                    f"{self.kind} cites a bar closing at {evidence.closes_at}, which had not "
                    f"ended at {self.evaluated_at}: no look-ahead."
                )
        elif self.kind in (_K.ENTRY_WINDOW_OPENED, _K.EVIDENCE_INCOMPLETE) and (
            evidence.observations
        ):
            raise error(f"{self.kind} does not rest on a bar's prices and cites no candle.")

    def _validate_reason(self) -> None:
        if self.kind is _K.ENTRY_CANCELLED:
            if self.reason is not EquityLifecycleCancellationReason.STOP_TOUCHED_BEFORE_ENTRY:
                raise InvalidEquityLifecycleEventError(
                    "ENTRY_CANCELLED requires the reason STOP_TOUCHED_BEFORE_ENTRY."
                )
        elif self.reason is not None:
            raise InvalidEquityLifecycleEventError(f"{self.kind} carries no reason.")

    def _validate_deficiencies(self) -> None:
        error = InvalidEquityLifecycleEventError
        if self.kind is not _K.EVIDENCE_INCOMPLETE:
            if self.deficiencies:
                raise error(f"{self.kind} carries no deficiencies.")
            return
        if not self.deficiencies:
            raise error("EVIDENCE_INCOMPLETE must list at least one deficiency.")
        previous: EquityEvidenceDeficiency | None = None
        for item in self.deficiencies:
            if previous is not None and item.opens_at.compare(previous.closes_at) < 0:
                raise error("Deficiencies must be in ascending, non-overlapping interval order.")
            if item.closes_at.compare(self.evaluated_at) > 0:
                raise error("A deficiency must be an interval that had ended when evaluated.")
            previous = item
        first = self.deficiencies[0]
        if not self.evidence.same_interval(first.opens_at, first.closes_at):
            raise error("EVIDENCE_INCOMPLETE evidence must name the first deficient interval.")

    def _validate_revision(self) -> None:
        error = InvalidEquityLifecycleEventError
        fields = (self.cited_sequence, self.superseded_evidence, self.materiality)
        if self.kind is not _K.SOURCE_REVISION_RECORDED:
            if any(value is not None for value in fields):
                raise error(f"{self.kind} carries no revision fields.")
            return
        cited = self.cited_sequence
        if isinstance(cited, bool) or not isinstance(cited, int) or not 1 <= cited < self.sequence:
            raise error("A revision must cite an earlier event's sequence.")
        superseded = self.superseded_evidence
        if not isinstance(superseded, EquityLifecycleEvidence):
            raise error("A revision must state the superseded evidence.")
        if not self.evidence.same_interval(superseded.opens_at, superseded.closes_at):
            raise error("A revision's new evidence must be for the cited interval.")
        if self.evidence == superseded:
            raise error("A revision's new evidence must differ from the superseded evidence.")
        if self.materiality is not EquityRevisionMateriality.UNASSESSED:
            raise error("Revision materiality stays UNASSESSED while EI0-D21 is pending.")
