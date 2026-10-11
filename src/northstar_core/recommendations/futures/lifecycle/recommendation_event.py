"""One immutable event in the lifecycle of a trade recommendation.

An event records what its evidence showed about a recommendation, and which
documented rule decided the outcome where the evidence cannot show chronology.
It is not an order, a fill, a position or a broker execution, and it carries no
entry price, exit price, quantity or profit and loss.

Every event has exactly one kind of evidence:

- ``observation``: the completed bar that caused the event, kept whole so its
  prices stay auditable. Every kind except VALIDITY_EXPIRED_BY_TIME has one.
- ``time_evidence``: the caller-supplied TimeExpiryEvidence of a
  VALIDITY_EXPIRED_BY_TIME event, which has no bar. A non-bar event never
  borrows a bar's identity.

``touched`` lists the boundaries the bar's range touched, in the canonical
order ENTRY, STOP, TARGET. ``ordering`` states how chronology inside the bar was
treated:

- NOT_REQUIRED: at most one price boundary was involved;
- MODELED_STOP_FIRST: while active, the bar touched both stop and target, and
  the conservative stop-first policy decided the outcome -- a modeling rule,
  not an observed sequence;
- UNKNOWN: the bar touched the entry zone and an exit level, and their order
  cannot be known.

Only these combinations exist; any other is refused at construction:

    ENTRY_ACTIVATED           (ENTRY,)                      NOT_REQUIRED
    ENTRY_INDETERMINATE       (ENTRY, STOP) | (ENTRY, TARGET)
                              | (ENTRY, STOP, TARGET)       UNKNOWN
    TARGET_REACHED            (TARGET,)                     NOT_REQUIRED
    STOP_REACHED              (STOP,)                       NOT_REQUIRED
    STOP_REACHED              (STOP, TARGET)                MODELED_STOP_FIRST
    VALIDITY_EXPIRED          ()                            NOT_REQUIRED, with a reason
    VALIDITY_EXPIRED_BY_TIME  ()                            NOT_REQUIRED, with a reason

Whether an event is consistent with a particular recommendation's levels and
history is checked when a FuturesTradeRecommendationLifecycle is built, not here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime
from northstar_core.futures import FuturesOHLCVBar
from northstar_core.recommendations.futures.lifecycle.time_expiry_evidence import (
    TimeExpiryEvidence,
)
from northstar_core.recommendations.futures.value_objects import (
    FuturesTradeRecommendationIdentity,
)


class RecommendationEventKind(StrEnum):
    """Closed vocabulary for what a lifecycle event records."""

    ENTRY_ACTIVATED = "ENTRY_ACTIVATED"
    ENTRY_INDETERMINATE = "ENTRY_INDETERMINATE"
    TARGET_REACHED = "TARGET_REACHED"
    STOP_REACHED = "STOP_REACHED"
    VALIDITY_EXPIRED = "VALIDITY_EXPIRED"
    VALIDITY_EXPIRED_BY_TIME = "VALIDITY_EXPIRED_BY_TIME"


class RecommendationBoundary(StrEnum):
    """A recommendation price level that an observation's range touched."""

    ENTRY = "ENTRY"
    STOP = "STOP"
    TARGET = "TARGET"


class IntrabarOrdering(StrEnum):
    """How an event treats the unknown chronology inside its observation."""

    NOT_REQUIRED = "NOT_REQUIRED"
    MODELED_STOP_FIRST = "MODELED_STOP_FIRST"
    UNKNOWN = "UNKNOWN"


class RecommendationExpiryReason(StrEnum):
    """Which boundary ended a recommendation's validity window."""

    VALIDITY_WINDOW_ENDED = "VALIDITY_WINDOW_ENDED"
    CONTRACT_CUTOFF_REACHED = "CONTRACT_CUTOFF_REACHED"


class InvalidFuturesTradeRecommendationEventError(ValidationError):
    """Raised when a FuturesTradeRecommendationEvent value is invalid."""


_ENTRY = RecommendationBoundary.ENTRY
_STOP = RecommendationBoundary.STOP
_TARGET = RecommendationBoundary.TARGET

_EXPIRY_KINDS = frozenset(
    {RecommendationEventKind.VALIDITY_EXPIRED, RecommendationEventKind.VALIDITY_EXPIRED_BY_TIME}
)

# Every allowed (kind, touched, ordering) combination.
_ALLOWED_SHAPES: frozenset[
    tuple[RecommendationEventKind, tuple[RecommendationBoundary, ...], IntrabarOrdering]
] = frozenset(
    {
        (RecommendationEventKind.ENTRY_ACTIVATED, (_ENTRY,), IntrabarOrdering.NOT_REQUIRED),
        (RecommendationEventKind.ENTRY_INDETERMINATE, (_ENTRY, _STOP), IntrabarOrdering.UNKNOWN),
        (RecommendationEventKind.ENTRY_INDETERMINATE, (_ENTRY, _TARGET), IntrabarOrdering.UNKNOWN),
        (
            RecommendationEventKind.ENTRY_INDETERMINATE,
            (_ENTRY, _STOP, _TARGET),
            IntrabarOrdering.UNKNOWN,
        ),
        (RecommendationEventKind.TARGET_REACHED, (_TARGET,), IntrabarOrdering.NOT_REQUIRED),
        (RecommendationEventKind.STOP_REACHED, (_STOP,), IntrabarOrdering.NOT_REQUIRED),
        (
            RecommendationEventKind.STOP_REACHED,
            (_STOP, _TARGET),
            IntrabarOrdering.MODELED_STOP_FIRST,
        ),
        (RecommendationEventKind.VALIDITY_EXPIRED, (), IntrabarOrdering.NOT_REQUIRED),
        (RecommendationEventKind.VALIDITY_EXPIRED_BY_TIME, (), IntrabarOrdering.NOT_REQUIRED),
    }
)


def _require(value: object, expected: type, field_name: str) -> None:
    if not isinstance(value, expected):
        raise InvalidFuturesTradeRecommendationEventError(
            f"FuturesTradeRecommendationEvent {field_name} must be a {expected.__name__} value."
        )


def _validate_touched(
    value: tuple[RecommendationBoundary, ...],
) -> tuple[RecommendationBoundary, ...]:
    if not isinstance(value, tuple):
        raise InvalidFuturesTradeRecommendationEventError(
            "FuturesTradeRecommendationEvent touched boundaries must be a tuple."
        )
    if not all(isinstance(boundary, RecommendationBoundary) for boundary in value):
        raise InvalidFuturesTradeRecommendationEventError(
            "FuturesTradeRecommendationEvent touched boundaries must be "
            "RecommendationBoundary values."
        )
    return value


def _validate_evidence(
    kind: RecommendationEventKind,
    observation: FuturesOHLCVBar | None,
    time_evidence: TimeExpiryEvidence | None,
) -> None:
    if kind is RecommendationEventKind.VALIDITY_EXPIRED_BY_TIME:
        if observation is not None:
            raise InvalidFuturesTradeRecommendationEventError(
                "A VALIDITY_EXPIRED_BY_TIME event cannot carry an observation."
            )
        _require(time_evidence, TimeExpiryEvidence, "time evidence")
    else:
        _require(observation, FuturesOHLCVBar, "observation")
        if time_evidence is not None:
            raise InvalidFuturesTradeRecommendationEventError(
                f"A {kind} event cannot carry time evidence."
            )


def _validate_expiry_reason(
    kind: RecommendationEventKind, value: RecommendationExpiryReason | None
) -> RecommendationExpiryReason | None:
    if kind in _EXPIRY_KINDS:
        if not isinstance(value, RecommendationExpiryReason):
            raise InvalidFuturesTradeRecommendationEventError(
                f"A {kind} event must carry a RecommendationExpiryReason."
            )
    elif value is not None:
        raise InvalidFuturesTradeRecommendationEventError(
            f"A {kind} event cannot carry an expiry reason."
        )
    return value


@dataclass(frozen=True, slots=True)
class FuturesTradeRecommendationEvent:
    """Immutable record of one lifecycle occurrence and the evidence behind it."""

    recommendation: FuturesTradeRecommendationIdentity
    kind: RecommendationEventKind
    observation: FuturesOHLCVBar | None
    touched: tuple[RecommendationBoundary, ...]
    ordering: IntrabarOrdering
    expiry_reason: RecommendationExpiryReason | None = None
    time_evidence: TimeExpiryEvidence | None = None

    def __post_init__(self) -> None:
        _require(self.recommendation, FuturesTradeRecommendationIdentity, "recommendation")
        _require(self.kind, RecommendationEventKind, "kind")
        _validate_evidence(self.kind, self.observation, self.time_evidence)
        touched = _validate_touched(self.touched)
        _require(self.ordering, IntrabarOrdering, "ordering")
        if (self.kind, touched, self.ordering) not in _ALLOWED_SHAPES:
            raise InvalidFuturesTradeRecommendationEventError(
                f"A {self.kind} event cannot record touched boundaries "
                f"{tuple(str(boundary) for boundary in touched)} with {self.ordering} ordering."
            )
        expiry_reason = _validate_expiry_reason(self.kind, self.expiry_reason)

        object.__setattr__(self, "touched", touched)
        object.__setattr__(self, "expiry_reason", expiry_reason)

    @property
    def evidenced_at(self) -> PointInTime:
        """Return the bar's completion instant, or the time evidence's as-of instant."""
        if self.observation is not None:
            return self.observation.point_in_time
        # Construction guarantees time evidence whenever there is no observation.
        return self.time_evidence.as_of  # type: ignore[union-attr]

    def __str__(self) -> str:
        reason = f" ({self.expiry_reason})" if self.expiry_reason is not None else ""
        evidence = f" [{self.time_evidence.coverage}]" if self.time_evidence is not None else ""
        return f"{self.recommendation} {self.kind}{reason}{evidence} at {self.evidenced_at}"

    def __repr__(self) -> str:
        return (
            "FuturesTradeRecommendationEvent("
            f"recommendation={self.recommendation!r}, "
            f"kind={self.kind!r}, "
            f"observation={self.observation!r}, "
            f"touched={self.touched!r}, "
            f"ordering={self.ordering!r}, "
            f"expiry_reason={self.expiry_reason!r}, "
            f"time_evidence={self.time_evidence!r}"
            ")"
        )
