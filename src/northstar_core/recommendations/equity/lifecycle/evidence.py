"""Lifecycle evidence: provenance, interval assessments and one observation (EI5-D6).

Core never reads evidence itself. The Application assesses EI-2B snapshots and
hands Core plain facts; Core keeps their provenance and enforces the rules that
make a decision reproducible:

- **Opaque references.** An evidence reference names where evidence came from:
  an EI-2B snapshot identity. Observation references name the acceptable
  candles used. Core requires them to be non-empty text and never interprets
  them.
- **Contiguity.** An observation's intervals are strictly ascending and
  contiguous: each opens exactly where the previous one closed. A duplicate,
  out-of-order or skipped interval is refused, never filled.
- **No look-ahead.** An interval is ``NOT_ENDED`` exactly when it closes after
  the evaluation instant, as EI-2A decides; every other outcome, including
  ``ACCEPTABLE``, belongs to an interval that has ended. EI-2A refuses a candle
  received, or finality confirmed, *before* the interval's close, but accepts
  both *at* the close: an interval closing exactly at the evaluation instant
  may therefore be ``ACCEPTABLE``, or ``MISSING``, ``UNFINALIZED``,
  ``CONFLICTING_VALUES`` or ``UNRESOLVED_REVISIONS``, never ``NOT_ENDED``.
- **No invented prices.** Only an ``ACCEPTABLE`` interval carries its candle's
  low and high. Every other outcome carries none.

Nothing here reads a clock, a store or a provider.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime, Price
from northstar_core.recommendations.equity.lifecycle.vocabulary import (
    EquityEvidenceDeficiencyKind,
    EquityLifecycleIntervalOutcome,
)


class InvalidEquityLifecycleEvidenceError(ValidationError):
    """Raised when an evidence reference, interval or deficiency is invalid."""


class InvalidEquityLifecycleObservationError(ValidationError):
    """Raised when an observation is incomplete, unordered or looks ahead."""


def _instant(value: object, name: str) -> PointInTime:
    if not isinstance(value, PointInTime):
        raise InvalidEquityLifecycleEvidenceError(f"{name} must be a PointInTime.")
    return value


def _reference(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise InvalidEquityLifecycleEvidenceError(
            f"{name} must be non-empty text without surrounding whitespace."
        )
    return value


def _references(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise InvalidEquityLifecycleEvidenceError(f"{name} must be a tuple.")
    for item in value:
        _reference(item, name)
    if len(set(value)) != len(value):
        raise InvalidEquityLifecycleEvidenceError(f"{name} must be distinct.")
    return value


def _interval(opens_at: object, closes_at: object, subject: str) -> None:
    opens = _instant(opens_at, f"{subject} opens_at")
    closes = _instant(closes_at, f"{subject} closes_at")
    if opens.compare(closes) >= 0:
        raise InvalidEquityLifecycleEvidenceError(f"{subject} must open before it closes.")


@dataclass(frozen=True, slots=True)
class EquityLifecycleEvidence:
    """The provenance of one lifecycle event.

    ``reference`` is an opaque evidence reference, an EI-2B snapshot identity.
    ``opens_at`` and ``closes_at`` name one interval. ``observations`` are the
    opaque references of the acceptable candles a bar-driven event used, and
    are empty when the event does not rest on a bar's prices.
    """

    reference: str
    opens_at: PointInTime
    closes_at: PointInTime
    observations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _reference(self.reference, "EquityLifecycleEvidence reference")
        _interval(self.opens_at, self.closes_at, "EquityLifecycleEvidence interval")
        _references(self.observations, "EquityLifecycleEvidence observations")

    def same_interval(self, opens_at: PointInTime, closes_at: PointInTime) -> bool:
        """Return whether this evidence names the interval [opens_at, closes_at)."""
        return self.opens_at == opens_at and self.closes_at == closes_at


@dataclass(frozen=True, slots=True)
class EquityEvidenceDeficiency:
    """One ended interval whose evidence cannot be used, and why (EI5-D7)."""

    opens_at: PointInTime
    closes_at: PointInTime
    kind: EquityEvidenceDeficiencyKind

    def __post_init__(self) -> None:
        _interval(self.opens_at, self.closes_at, "EquityEvidenceDeficiency interval")
        if not isinstance(self.kind, EquityEvidenceDeficiencyKind):
            raise InvalidEquityLifecycleEvidenceError(
                "EquityEvidenceDeficiency kind must be an EquityEvidenceDeficiencyKind."
            )


@dataclass(frozen=True, slots=True)
class EquityLifecycleInterval:
    """One interval as one evaluated snapshot assessed it.

    An ``ACCEPTABLE`` interval carries its candle's ``low`` and ``high`` -- one
    currency, low at or below high -- and at least one observation reference.
    Any other outcome carries no price and no observation reference.
    """

    opens_at: PointInTime
    closes_at: PointInTime
    outcome: EquityLifecycleIntervalOutcome
    low: Price | None = None
    high: Price | None = None
    observations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _interval(self.opens_at, self.closes_at, "EquityLifecycleInterval")
        if not isinstance(self.outcome, EquityLifecycleIntervalOutcome):
            raise InvalidEquityLifecycleEvidenceError(
                "EquityLifecycleInterval outcome must be an EquityLifecycleIntervalOutcome."
            )
        _references(self.observations, "EquityLifecycleInterval observations")
        if self.outcome is EquityLifecycleIntervalOutcome.ACCEPTABLE:
            if not isinstance(self.low, Price) or not isinstance(self.high, Price):
                raise InvalidEquityLifecycleEvidenceError(
                    "An ACCEPTABLE interval needs its candle's low and high as Prices."
                )
            if self.low.currency != self.high.currency:
                raise InvalidEquityLifecycleEvidenceError(
                    "An ACCEPTABLE interval's low and high differ in currency."
                )
            if self.low.amount > self.high.amount:
                raise InvalidEquityLifecycleEvidenceError(
                    "An ACCEPTABLE interval's low must not exceed its high."
                )
            if not self.observations:
                raise InvalidEquityLifecycleEvidenceError(
                    "An ACCEPTABLE interval needs at least one observation reference."
                )
        elif self.low is not None or self.high is not None or self.observations:
            raise InvalidEquityLifecycleEvidenceError(
                f"A {self.outcome} interval carries no price and no observation reference."
            )

    @property
    def deficiency_kind(self) -> EquityEvidenceDeficiencyKind | None:
        """Return the deficiency this interval represents, or None if it has none."""
        if self.outcome in (
            EquityLifecycleIntervalOutcome.ACCEPTABLE,
            EquityLifecycleIntervalOutcome.NOT_ENDED,
        ):
            return None
        return EquityEvidenceDeficiencyKind(self.outcome.value)

    def deficiency(self) -> EquityEvidenceDeficiency:
        """Return this interval as an explicit deficiency; it must be deficient."""
        kind = self.deficiency_kind
        if kind is None:
            raise InvalidEquityLifecycleEvidenceError(
                f"A {self.outcome} interval is not deficient."
            )
        return EquityEvidenceDeficiency(self.opens_at, self.closes_at, kind)


@dataclass(frozen=True, slots=True)
class EquityLifecycleObservation:
    """One evaluated snapshot: its instant, its reference and its ordered intervals.

    ``evaluated_at`` is the snapshot's ``as_of`` and the evaluation instant
    (EI5-D8). No clock is consulted. The intervals are strictly ascending and
    contiguous, and consistent with ``evaluated_at`` (no look-ahead): see the
    module docstring.
    """

    evaluated_at: PointInTime
    reference: str
    intervals: tuple[EquityLifecycleInterval, ...]

    def __post_init__(self) -> None:
        error = InvalidEquityLifecycleObservationError
        if not isinstance(self.evaluated_at, PointInTime):
            raise error("EquityLifecycleObservation evaluated_at must be a PointInTime.")
        try:
            _reference(self.reference, "EquityLifecycleObservation reference")
        except InvalidEquityLifecycleEvidenceError as exc:
            raise error(str(exc)) from exc
        if not isinstance(self.intervals, tuple) or not self.intervals:
            raise error("EquityLifecycleObservation needs a non-empty tuple of intervals.")
        previous: EquityLifecycleInterval | None = None
        for interval in self.intervals:
            if not isinstance(interval, EquityLifecycleInterval):
                raise error(
                    "EquityLifecycleObservation intervals must be EquityLifecycleIntervals."
                )
            if previous is not None and interval.opens_at != previous.closes_at:
                raise error(
                    f"Interval opening {interval.opens_at} does not follow the interval closing "
                    f"{previous.closes_at}: intervals must be strictly ascending and contiguous."
                )
            ended = interval.closes_at.compare(self.evaluated_at) <= 0
            not_ended = interval.outcome is EquityLifecycleIntervalOutcome.NOT_ENDED
            if ended == not_ended:
                raise error(
                    f"Interval closing {interval.closes_at} is {interval.outcome} at "
                    f"{self.evaluated_at}: an interval is NOT_ENDED exactly when it closes "
                    "after the evaluation instant."
                )
            previous = interval
