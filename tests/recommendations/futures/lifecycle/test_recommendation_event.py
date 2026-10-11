"""Tests for lifecycle events and the derived lifecycle status vocabulary."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from decimal import Decimal
from itertools import product

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
    CoverageDeficiency,
    FuturesTradeRecommendationEvent,
    FuturesTradeRecommendationIdentity,
    IntrabarOrdering,
    InvalidFuturesTradeRecommendationEventError,
    ObservationCoverage,
    RecommendationBoundary,
    RecommendationEventKind,
    RecommendationExpiryReason,
    RecommendationStatus,
    TimeExpiryEvidence,
)

_IDENTITY = FuturesTradeRecommendationIdentity("rec-1")
_BAR = FuturesOHLCVBar(
    contract=FuturesContract(
        FuturesProductReference(Symbol("NIFTY"), ExchangeCode("NSE")),
        ExpirationDate("2026-10-27"),
    ),
    point_in_time=PointInTime("2026-10-06T10:00:00Z"),
    timeframe=Timeframe("1d"),
    open=QuoteValue(Decimal("25050")),
    high=QuoteValue(Decimal("25300")),
    low=QuoteValue(Decimal("25050")),
    close=QuoteValue(Decimal("25300")),
    volume=Quantity(Decimal("1000")),
)

Kind = RecommendationEventKind
Ordering = IntrabarOrdering
_E = RecommendationBoundary.ENTRY
_S = RecommendationBoundary.STOP
_T = RecommendationBoundary.TARGET
_WINDOW = RecommendationExpiryReason.VALIDITY_WINDOW_ENDED
_EXPIRY_KINDS = {Kind.VALIDITY_EXPIRED, Kind.VALIDITY_EXPIRED_BY_TIME}
_EVIDENCE = TimeExpiryEvidence(
    as_of=PointInTime("2026-10-17T00:00:00Z"),
    evaluated_through=PointInTime("2026-10-06T10:00:00Z"),
    coverage=ObservationCoverage.INCOMPLETE_OR_UNVERIFIED_COVERAGE,
    attested_by="synthetic-test",
    deficiency=CoverageDeficiency.MISSING_OBSERVATIONS,
)

_ALLOWED = {
    (Kind.ENTRY_ACTIVATED, (_E,), Ordering.NOT_REQUIRED, None),
    (Kind.ENTRY_INDETERMINATE, (_E, _S), Ordering.UNKNOWN, None),
    (Kind.ENTRY_INDETERMINATE, (_E, _T), Ordering.UNKNOWN, None),
    (Kind.ENTRY_INDETERMINATE, (_E, _S, _T), Ordering.UNKNOWN, None),
    (Kind.TARGET_REACHED, (_T,), Ordering.NOT_REQUIRED, None),
    (Kind.STOP_REACHED, (_S,), Ordering.NOT_REQUIRED, None),
    (Kind.STOP_REACHED, (_S, _T), Ordering.MODELED_STOP_FIRST, None),
    (Kind.VALIDITY_EXPIRED, (), Ordering.NOT_REQUIRED, _WINDOW),
    (Kind.VALIDITY_EXPIRED_BY_TIME, (), Ordering.NOT_REQUIRED, _WINDOW),
}

_TOUCHED_CANDIDATES = [
    (),
    (_E,),
    (_S,),
    (_T,),
    (_E, _S),
    (_E, _T),
    (_S, _T),
    (_T, _S),
    (_E, _S, _T),
    (_S, _E),
]


def _event(
    kind: RecommendationEventKind,
    touched: tuple[RecommendationBoundary, ...],
    ordering: IntrabarOrdering,
    expiry_reason: RecommendationExpiryReason | None = None,
) -> FuturesTradeRecommendationEvent:
    """Build an event with the evidence its kind requires."""
    by_time = kind is Kind.VALIDITY_EXPIRED_BY_TIME
    return FuturesTradeRecommendationEvent(
        recommendation=_IDENTITY,
        kind=kind,
        observation=None if by_time else _BAR,
        touched=touched,
        ordering=ordering,
        expiry_reason=expiry_reason,
        time_evidence=_EVIDENCE if by_time else None,
    )


# ---------------------------------------------------------------------------
# Event shapes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("kind", "touched", "ordering", "reason"), sorted(_ALLOWED, key=str))
def test_every_documented_event_shape_is_accepted(kind, touched, ordering, reason) -> None:
    event = _event(kind, touched, ordering, reason)

    assert (event.kind, event.touched, event.ordering, event.expiry_reason) == (
        kind,
        touched,
        ordering,
        reason,
    )


def test_every_undocumented_shape_is_rejected() -> None:
    """Exhaustive over kinds, orderings and plausible touched tuples."""
    rejected = 0
    for kind, ordering, touched in product(Kind, Ordering, _TOUCHED_CANDIDATES):
        reason = _WINDOW if kind in _EXPIRY_KINDS else None
        if (kind, touched, ordering, reason) in _ALLOWED:
            continue
        with pytest.raises(InvalidFuturesTradeRecommendationEventError):
            _event(kind, touched, ordering, reason)
        rejected += 1

    assert rejected == len(Kind) * len(Ordering) * len(_TOUCHED_CANDIDATES) - len(_ALLOWED)


def test_a_stop_first_closure_must_say_so() -> None:
    with pytest.raises(InvalidFuturesTradeRecommendationEventError):
        _event(Kind.STOP_REACHED, (_S, _T), Ordering.NOT_REQUIRED)


def test_an_ambiguous_entry_cannot_claim_a_known_ordering() -> None:
    for ordering in (Ordering.NOT_REQUIRED, Ordering.MODELED_STOP_FIRST):
        with pytest.raises(InvalidFuturesTradeRecommendationEventError):
            _event(Kind.ENTRY_INDETERMINATE, (_E, _S), ordering)


@pytest.mark.parametrize("kind", sorted(_EXPIRY_KINDS))
def test_an_expiry_requires_a_reason(kind: RecommendationEventKind) -> None:
    with pytest.raises(InvalidFuturesTradeRecommendationEventError, match="ExpiryReason"):
        _event(kind, (), Ordering.NOT_REQUIRED, None)


def test_a_time_expiry_carries_time_evidence_and_no_bar() -> None:
    event = _event(Kind.VALIDITY_EXPIRED_BY_TIME, (), Ordering.NOT_REQUIRED, _WINDOW)

    assert event.observation is None
    assert event.time_evidence == _EVIDENCE
    assert event.evidenced_at == _EVIDENCE.as_of


def test_a_time_expiry_cannot_borrow_a_bar() -> None:
    with pytest.raises(InvalidFuturesTradeRecommendationEventError, match="cannot carry an"):
        FuturesTradeRecommendationEvent(
            _IDENTITY,
            Kind.VALIDITY_EXPIRED_BY_TIME,
            _BAR,
            (),
            Ordering.NOT_REQUIRED,
            _WINDOW,
            _EVIDENCE,
        )


def test_a_time_expiry_requires_time_evidence() -> None:
    with pytest.raises(InvalidFuturesTradeRecommendationEventError, match="time evidence"):
        FuturesTradeRecommendationEvent(
            _IDENTITY, Kind.VALIDITY_EXPIRED_BY_TIME, None, (), Ordering.NOT_REQUIRED, _WINDOW
        )


@pytest.mark.parametrize(
    ("kind", "touched", "reason"),
    [(Kind.ENTRY_ACTIVATED, (_E,), None), (Kind.VALIDITY_EXPIRED, (), _WINDOW)],
)
def test_a_bar_event_cannot_carry_time_evidence(kind, touched, reason) -> None:
    with pytest.raises(InvalidFuturesTradeRecommendationEventError, match="time evidence"):
        FuturesTradeRecommendationEvent(
            _IDENTITY, kind, _BAR, touched, Ordering.NOT_REQUIRED, reason, _EVIDENCE
        )


def test_a_bar_event_requires_its_bar() -> None:
    with pytest.raises(InvalidFuturesTradeRecommendationEventError, match="observation"):
        FuturesTradeRecommendationEvent(
            _IDENTITY, Kind.ENTRY_ACTIVATED, None, (_E,), Ordering.NOT_REQUIRED
        )


def test_a_bar_event_is_evidenced_at_its_completion_instant() -> None:
    event = _event(Kind.ENTRY_ACTIVATED, (_E,), Ordering.NOT_REQUIRED)

    assert event.evidenced_at == _BAR.point_in_time


@pytest.mark.parametrize("kind", [Kind.ENTRY_ACTIVATED, Kind.TARGET_REACHED])
def test_only_an_expiry_may_carry_a_reason(kind: RecommendationEventKind) -> None:
    touched = (_E,) if kind is Kind.ENTRY_ACTIVATED else (_T,)

    with pytest.raises(InvalidFuturesTradeRecommendationEventError, match="expiry reason"):
        _event(kind, touched, Ordering.NOT_REQUIRED, _WINDOW)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("recommendation", "rec-1"),
        ("kind", "ENTRY_ACTIVATED"),
        ("observation", None),
        ("touched", [_E]),
        ("touched", ("ENTRY",)),
        ("ordering", "NOT_REQUIRED"),
    ],
)
def test_event_fields_require_their_domain_types(field: str, value: object) -> None:
    fields: dict[str, object] = {
        "recommendation": _IDENTITY,
        "kind": Kind.ENTRY_ACTIVATED,
        "observation": _BAR,
        "touched": (_E,),
        "ordering": Ordering.NOT_REQUIRED,
    }
    fields[field] = value

    with pytest.raises(InvalidFuturesTradeRecommendationEventError):
        FuturesTradeRecommendationEvent(**fields)  # type: ignore[arg-type]


def test_events_are_immutable_comparable_and_hashable() -> None:
    event = _event(Kind.ENTRY_ACTIVATED, (_E,), Ordering.NOT_REQUIRED)

    assert event == _event(Kind.ENTRY_ACTIVATED, (_E,), Ordering.NOT_REQUIRED)
    assert hash(event) == hash(_event(Kind.ENTRY_ACTIVATED, (_E,), Ordering.NOT_REQUIRED))
    with pytest.raises(FrozenInstanceError):
        event.kind = Kind.TARGET_REACHED  # type: ignore[misc]


def test_event_text() -> None:
    expiry = _event(Kind.VALIDITY_EXPIRED, (), Ordering.NOT_REQUIRED, _WINDOW)

    assert str(expiry) == "rec-1 VALIDITY_EXPIRED (VALIDITY_WINDOW_ENDED) at 2026-10-06T10:00:00Z"
    assert repr(expiry).startswith("FuturesTradeRecommendationEvent(recommendation=")


def test_the_event_error_is_a_validation_error() -> None:
    assert issubclass(InvalidFuturesTradeRecommendationEventError, ValidationError)


# ---------------------------------------------------------------------------
# Vocabularies
# ---------------------------------------------------------------------------


def test_the_event_vocabularies_are_closed() -> None:
    assert [kind.value for kind in Kind] == [
        "ENTRY_ACTIVATED",
        "ENTRY_INDETERMINATE",
        "TARGET_REACHED",
        "STOP_REACHED",
        "VALIDITY_EXPIRED",
        "VALIDITY_EXPIRED_BY_TIME",
    ]
    assert [boundary.value for boundary in RecommendationBoundary] == ["ENTRY", "STOP", "TARGET"]
    assert [ordering.value for ordering in Ordering] == [
        "NOT_REQUIRED",
        "MODELED_STOP_FIRST",
        "UNKNOWN",
    ]
    assert [reason.value for reason in RecommendationExpiryReason] == [
        "VALIDITY_WINDOW_ENDED",
        "CONTRACT_CUTOFF_REACHED",
    ]


def test_the_status_vocabulary_and_terminality() -> None:
    terminal = {status for status in RecommendationStatus if status.is_terminal}

    assert [status.value for status in RecommendationStatus] == [
        "WAITING_FOR_ENTRY",
        "ACTIVE",
        "CLOSED_TARGET",
        "CLOSED_STOP",
        "EXPIRED_BEFORE_ENTRY",
        "EXPIRED_AFTER_ACTIVATION",
        "INDETERMINATE_ENTRY",
        "EXPIRED_WITH_INCOMPLETE_COVERAGE",
    ]
    assert terminal == set(RecommendationStatus) - {
        RecommendationStatus.WAITING_FOR_ENTRY,
        RecommendationStatus.ACTIVE,
    }
    assert RecommendationStatus.INDETERMINATE_ENTRY.is_terminal
    assert RecommendationStatus.EXPIRED_WITH_INCOMPLETE_COVERAGE.is_terminal
