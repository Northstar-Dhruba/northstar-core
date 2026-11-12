"""The closed vocabulary of the equity recommendation lifecycle (EI5-D5, ADR-024).

Every term here is equity-local. None is a Futures type: the Futures
``MODELED_STOP_FIRST`` ordering, ``EXPIRED_AFTER_ACTIVATION`` and
``EXPIRED_WITH_INCOMPLETE_COVERAGE`` have no equity counterpart (EI0-D9,
ADR-020 section 2). ``INVALIDATED`` is outside the initial EI-5 scope: its
listing-applicability source and its materiality policy (EI0-D21) are not
approved.

"Terminal" means monitoring has ended. It does not mean the outcome is
resolved: indeterminate and unresolved terminal states record why no evidenced
result exists, and neither is ever a win or a loss.
"""

from __future__ import annotations

from enum import StrEnum


class EquityLifecycleOutcomeClass(StrEnum):
    """How a terminal lifecycle state is classified for later evaluation."""

    RESOLVED = "RESOLVED"
    RESOLVED_NO_ENTRY = "RESOLVED_NO_ENTRY"
    INDETERMINATE = "INDETERMINATE"
    UNRESOLVED = "UNRESOLVED"


class EquityLifecycleState(StrEnum):
    """The eleven approved lifecycle states (EI5-D5)."""

    RECORDED = "RECORDED"
    WAITING_FOR_ENTRY = "WAITING_FOR_ENTRY"
    ACTIVE = "ACTIVE"
    CLOSED_TARGET = "CLOSED_TARGET"
    CLOSED_STOP = "CLOSED_STOP"
    EXPIRED_BEFORE_ENTRY = "EXPIRED_BEFORE_ENTRY"
    CANCELLED_BEFORE_ENTRY = "CANCELLED_BEFORE_ENTRY"
    INDETERMINATE_ENTRY = "INDETERMINATE_ENTRY"
    INDETERMINATE_EXIT = "INDETERMINATE_EXIT"
    SESSION_CUTOFF_REACHED = "SESSION_CUTOFF_REACHED"
    INCOMPLETE_EVIDENCE = "INCOMPLETE_EVIDENCE"

    @property
    def is_terminal(self) -> bool:
        """Return whether monitoring has ended in this state."""
        return self not in _OPEN

    @property
    def outcome_class(self) -> EquityLifecycleOutcomeClass | None:
        """Return the terminal outcome class, or None for a state that is not terminal."""
        return _OUTCOME_CLASS.get(self)


_OPEN = frozenset(
    {
        EquityLifecycleState.RECORDED,
        EquityLifecycleState.WAITING_FOR_ENTRY,
        EquityLifecycleState.ACTIVE,
    }
)

_OUTCOME_CLASS = {
    EquityLifecycleState.CLOSED_TARGET: EquityLifecycleOutcomeClass.RESOLVED,
    EquityLifecycleState.CLOSED_STOP: EquityLifecycleOutcomeClass.RESOLVED,
    EquityLifecycleState.EXPIRED_BEFORE_ENTRY: EquityLifecycleOutcomeClass.RESOLVED_NO_ENTRY,
    EquityLifecycleState.CANCELLED_BEFORE_ENTRY: EquityLifecycleOutcomeClass.RESOLVED_NO_ENTRY,
    EquityLifecycleState.INDETERMINATE_ENTRY: EquityLifecycleOutcomeClass.INDETERMINATE,
    EquityLifecycleState.INDETERMINATE_EXIT: EquityLifecycleOutcomeClass.INDETERMINATE,
    EquityLifecycleState.SESSION_CUTOFF_REACHED: EquityLifecycleOutcomeClass.UNRESOLVED,
    EquityLifecycleState.INCOMPLETE_EVIDENCE: EquityLifecycleOutcomeClass.UNRESOLVED,
}


class EquityLifecycleEventKind(StrEnum):
    """The kinds of lifecycle event (ADR-024 section 8; EI-5 design section 5.3).

    ``SOURCE_REVISION_RECORDED`` is the one kind that changes no state: it records
    a later correction to evidence an earlier event cited (EI5-D8).
    """

    ENTRY_WINDOW_OPENED = "ENTRY_WINDOW_OPENED"
    ENTRY_ACTIVATED = "ENTRY_ACTIVATED"
    ENTRY_INDETERMINATE = "ENTRY_INDETERMINATE"
    ENTRY_CANCELLED = "ENTRY_CANCELLED"
    ENTRY_WINDOW_EXPIRED = "ENTRY_WINDOW_EXPIRED"
    TARGET_REACHED = "TARGET_REACHED"
    STOP_REACHED = "STOP_REACHED"
    EXIT_INDETERMINATE = "EXIT_INDETERMINATE"
    SESSION_CUTOFF_REACHED = "SESSION_CUTOFF_REACHED"
    EVIDENCE_INCOMPLETE = "EVIDENCE_INCOMPLETE"
    SOURCE_REVISION_RECORDED = "SOURCE_REVISION_RECORDED"

    @property
    def changes_state(self) -> bool:
        """Return whether an event of this kind is a state transition."""
        return self is not EquityLifecycleEventKind.SOURCE_REVISION_RECORDED

    @property
    def is_bar_driven(self) -> bool:
        """Return whether an event of this kind is decided by one acceptable bar's prices."""
        return self in _BAR_DRIVEN


_BAR_DRIVEN = frozenset(
    {
        EquityLifecycleEventKind.ENTRY_ACTIVATED,
        EquityLifecycleEventKind.ENTRY_INDETERMINATE,
        EquityLifecycleEventKind.ENTRY_CANCELLED,
        EquityLifecycleEventKind.ENTRY_WINDOW_EXPIRED,
        EquityLifecycleEventKind.TARGET_REACHED,
        EquityLifecycleEventKind.STOP_REACHED,
        EquityLifecycleEventKind.EXIT_INDETERMINATE,
        EquityLifecycleEventKind.SESSION_CUTOFF_REACHED,
    }
)


class EquityLifecycleLevel(StrEnum):
    """A modeled level a bar can touch or reach, in canonical order."""

    ENTRY = "ENTRY"
    STOP = "STOP"
    TARGET = "TARGET"


class EquityIntrabarOrdering(StrEnum):
    """What is known about the order of levels inside one bar (EI0-D9).

    There is deliberately no modeled ordering: a stop-first or target-first
    assumption belongs to later evaluation (EI-8), never to a lifecycle fact.
    """

    NOT_REQUIRED = "NOT_REQUIRED"
    UNKNOWN = "UNKNOWN"


class EquityLifecycleCancellationReason(StrEnum):
    """Why a waiting setup was cancelled before entry (EI4-D5)."""

    STOP_TOUCHED_BEFORE_ENTRY = "STOP_TOUCHED_BEFORE_ENTRY"


class EquityRevisionMateriality(StrEnum):
    """The materiality of a correction to cited evidence.

    Only ``UNASSESSED`` exists: no materiality policy is approved while EI0-D21
    is pending, so every assessment is unassessed and no revision changes a state.
    """

    UNASSESSED = "UNASSESSED"


class EquityLifecycleIntervalOutcome(StrEnum):
    """What the evidence establishes for one interval, in the EI-2A vocabulary."""

    ACCEPTABLE = "ACCEPTABLE"
    NOT_ENDED = "NOT_ENDED"
    MISSING = "MISSING"
    UNFINALIZED = "UNFINALIZED"
    CONFLICTING_VALUES = "CONFLICTING_VALUES"
    UNRESOLVED_REVISIONS = "UNRESOLVED_REVISIONS"


class EquityEvidenceDeficiencyKind(StrEnum):
    """An ended interval whose evidence cannot be used, in the EI-2A vocabulary."""

    MISSING = "MISSING"
    UNFINALIZED = "UNFINALIZED"
    CONFLICTING_VALUES = "CONFLICTING_VALUES"
    UNRESOLVED_REVISIONS = "UNRESOLVED_REVISIONS"
