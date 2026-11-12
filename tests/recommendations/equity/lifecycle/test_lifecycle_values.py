"""EI-5B: the lifecycle vocabulary, evidence values, window and event shapes.

All values are synthetic. These tests pin the closed vocabulary of EI5-D5 and
the required-versus-forbidden field combinations of every event kind.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from decimal import Decimal

import pytest

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import Currency, PointInTime, Price
from northstar_core.recommendations.equity import EquityEntryZone, EquityRecommendationLevels
from northstar_core.recommendations.equity.lifecycle import (
    EquityEvidenceDeficiency,
    EquityEvidenceDeficiencyKind,
    EquityIntrabarOrdering,
    EquityLifecycleCancellationReason,
    EquityLifecycleEvent,
    EquityLifecycleEventKind,
    EquityLifecycleEvidence,
    EquityLifecycleInterval,
    EquityLifecycleIntervalOutcome,
    EquityLifecycleLevel,
    EquityLifecycleOutcomeClass,
    EquityLifecycleState,
    EquityLifecycleWindow,
    EquityRevisionMateriality,
    InvalidEquityLifecycleEventError,
    InvalidEquityLifecycleEvidenceError,
    InvalidEquityLifecycleWindowError,
)

K = EquityLifecycleEventKind
S = EquityLifecycleState
L = EquityLifecycleLevel
Outcome = EquityLifecycleIntervalOutcome

_INR = Currency("INR")


def _p(amount: str, currency: Currency = _INR) -> Price:
    return Price(Decimal(amount), currency)


def _t(clock: str) -> PointInTime:
    return PointInTime(f"2026-11-02T{clock}:00+05:30")


_LEVELS = EquityRecommendationLevels(
    EquityEntryZone(_p("100.00"), _p("100.50")), _p("99.00"), _p("103.00")
)
_EVIDENCE = EquityLifecycleEvidence("ecs1-sha256:s", _t("10:00"), _t("10:05"), ("obs-1",))
_PLAIN = EquityLifecycleEvidence("ecs1-sha256:s", _t("10:00"), _t("10:05"))


# ---------------------------------------------------------------------------
# Vocabulary (EI5-D5, EI0-D9, EI4-D5)
# ---------------------------------------------------------------------------


def test_the_state_model_is_exactly_the_eleven_approved_states() -> None:
    assert [state.value for state in S] == [
        "RECORDED",
        "WAITING_FOR_ENTRY",
        "ACTIVE",
        "CLOSED_TARGET",
        "CLOSED_STOP",
        "EXPIRED_BEFORE_ENTRY",
        "CANCELLED_BEFORE_ENTRY",
        "INDETERMINATE_ENTRY",
        "INDETERMINATE_EXIT",
        "SESSION_CUTOFF_REACHED",
        "INCOMPLETE_EVIDENCE",
    ]
    assert {s for s in S if not s.is_terminal} == {S.RECORDED, S.WAITING_FOR_ENTRY, S.ACTIVE}


def test_ft07_ft08_no_invalidated_futures_execution_or_repair_term_exists() -> None:
    terms = {
        member.value
        for enum in (
            S,
            K,
            L,
            EquityIntrabarOrdering,
            EquityLifecycleCancellationReason,
            EquityRevisionMateriality,
            Outcome,
            EquityEvidenceDeficiencyKind,
            EquityLifecycleOutcomeClass,
        )
        for member in enum
    }
    for forbidden in (
        "INVALIDATED",
        "MODELED_STOP_FIRST",
        "EXPIRED_AFTER_ACTIVATION",
        "EXPIRED_WITH_INCOMPLETE_COVERAGE",
        "FILLED",
        "EXECUTED",
        "REPAIRED",
        "RECOVERED",
    ):
        assert forbidden not in terms
    assert list(EquityIntrabarOrdering) == [
        EquityIntrabarOrdering.NOT_REQUIRED,
        EquityIntrabarOrdering.UNKNOWN,
    ]
    assert list(EquityRevisionMateriality) == [EquityRevisionMateriality.UNASSESSED]


def test_se04_outcome_classes_never_make_an_unresolved_state_a_win_or_loss() -> None:
    classes = {state: state.outcome_class for state in S}
    assert classes[S.RECORDED] is None and classes[S.ACTIVE] is None
    resolved = {s for s, c in classes.items() if c is EquityLifecycleOutcomeClass.RESOLVED}
    assert resolved == {S.CLOSED_TARGET, S.CLOSED_STOP}
    assert classes[S.CANCELLED_BEFORE_ENTRY] is EquityLifecycleOutcomeClass.RESOLVED_NO_ENTRY
    assert classes[S.EXPIRED_BEFORE_ENTRY] is EquityLifecycleOutcomeClass.RESOLVED_NO_ENTRY
    for state in (S.INDETERMINATE_ENTRY, S.INDETERMINATE_EXIT):
        assert classes[state] is EquityLifecycleOutcomeClass.INDETERMINATE
    for state in (S.SESSION_CUTOFF_REACHED, S.INCOMPLETE_EVIDENCE):
        assert classes[state] is EquityLifecycleOutcomeClass.UNRESOLVED


def test_deficiency_kinds_are_the_ei2a_names_and_map_from_interval_outcomes() -> None:
    assert {k.value for k in EquityEvidenceDeficiencyKind} == {
        "MISSING",
        "UNFINALIZED",
        "CONFLICTING_VALUES",
        "UNRESOLVED_REVISIONS",
    }
    for kind in EquityEvidenceDeficiencyKind:
        interval = EquityLifecycleInterval(_t("10:00"), _t("10:05"), Outcome(kind.value))
        assert interval.deficiency_kind is kind
        assert interval.deficiency() == EquityEvidenceDeficiency(_t("10:00"), _t("10:05"), kind)
    for outcome in (Outcome.NOT_ENDED,):
        assert EquityLifecycleInterval(_t("10:00"), _t("10:05"), outcome).deficiency_kind is None


# ---------------------------------------------------------------------------
# Evidence values
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("reference", ["", " ecs1", "ecs1 ", 7])
def test_an_evidence_reference_is_non_empty_text(reference: object) -> None:
    with pytest.raises(InvalidEquityLifecycleEvidenceError):
        EquityLifecycleEvidence(reference, _t("10:00"), _t("10:05"))  # type: ignore[arg-type]


def test_an_evidence_interval_opens_before_it_closes_and_cites_distinct_candles() -> None:
    with pytest.raises(InvalidEquityLifecycleEvidenceError):
        EquityLifecycleEvidence("r", _t("10:05"), _t("10:05"))
    with pytest.raises(InvalidEquityLifecycleEvidenceError):
        EquityLifecycleEvidence("r", _t("10:00"), _t("10:05"), ("a", "a"))
    with pytest.raises(InvalidEquityLifecycleEvidenceError):
        EquityLifecycleEvidence("r", _t("10:00"), _t("10:05"), ["a"])  # type: ignore[arg-type]


def test_an_acceptable_interval_carries_prices_and_candles_and_nothing_else_does() -> None:
    with pytest.raises(InvalidEquityLifecycleEvidenceError, match="low and high"):
        EquityLifecycleInterval(_t("10:00"), _t("10:05"), Outcome.ACCEPTABLE, observations=("a",))
    with pytest.raises(InvalidEquityLifecycleEvidenceError, match="observation"):
        EquityLifecycleInterval(_t("10:00"), _t("10:05"), Outcome.ACCEPTABLE, _p("1"), _p("2"))
    with pytest.raises(InvalidEquityLifecycleEvidenceError, match="exceed"):
        EquityLifecycleInterval(
            _t("10:00"), _t("10:05"), Outcome.ACCEPTABLE, _p("2"), _p("1"), ("a",)
        )
    with pytest.raises(InvalidEquityLifecycleEvidenceError, match="currency"):
        EquityLifecycleInterval(
            _t("10:00"), _t("10:05"), Outcome.ACCEPTABLE, _p("1"), _p("2", Currency("USD")), ("a",)
        )
    for outcome in Outcome:
        if outcome is Outcome.ACCEPTABLE:
            continue
        with pytest.raises(InvalidEquityLifecycleEvidenceError, match="no price"):
            EquityLifecycleInterval(_t("10:00"), _t("10:05"), outcome, _p("1"), _p("2"))
        with pytest.raises(InvalidEquityLifecycleEvidenceError, match="no price"):
            EquityLifecycleInterval(_t("10:00"), _t("10:05"), outcome, observations=("a",))
    with pytest.raises(InvalidEquityLifecycleEvidenceError, match="not deficient"):
        EquityLifecycleInterval(_t("10:00"), _t("10:05"), Outcome.NOT_ENDED).deficiency()


def test_values_are_immutable() -> None:
    with pytest.raises(FrozenInstanceError):
        _EVIDENCE.reference = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Window (EI5-D6, EI5-D7)
# ---------------------------------------------------------------------------


def test_a_window_orders_its_four_distinct_instants() -> None:
    EquityLifecycleWindow(_LEVELS, _t("09:45"), _t("11:00"), _t("11:05"), _t("15:00"))
    EquityLifecycleWindow(_LEVELS, _t("09:45"), _t("09:45"), _t("09:50"), _t("09:50"))
    for instants in (
        ("11:05", "11:00", "11:05", "15:00"),  # eligibility after the last opening
        ("09:45", "11:00", "11:00", "15:00"),  # the last bar closes as it opens
        ("09:45", "11:00", "15:05", "15:00"),  # the entry window beyond the exit
    ):
        with pytest.raises(InvalidEquityLifecycleWindowError):
            EquityLifecycleWindow(_LEVELS, *(_t(value) for value in instants))
    with pytest.raises(InvalidEquityLifecycleWindowError):
        EquityLifecycleWindow(None, _t("09:45"), _t("11:00"), _t("11:05"), _t("15:00"))  # type: ignore[arg-type]


def test_window_predicates_use_exact_decimals_and_recognize_exit_gap_through() -> None:
    window = EquityLifecycleWindow(_LEVELS, _t("09:45"), _t("11:00"), _t("11:05"), _t("15:00"))
    assert window.entry_touched(_p("99.50"), _p("100.00"))
    assert window.entry_touched(_p("100.50"), _p("101.00"))
    assert not window.entry_touched(_p("100.51"), _p("101.00"))
    assert not window.entry_touched(_p("99.10"), _p("99.99"))
    assert window.stop_reached(_p("99.00")) and window.stop_reached(_p("98.00"))
    assert not window.stop_reached(_p("99.01"))
    assert window.target_reached(_p("103.00")) and window.target_reached(_p("104.00"))
    assert not window.target_reached(_p("102.99"))


# ---------------------------------------------------------------------------
# Event shapes (EI-5 design section 5.3)
# ---------------------------------------------------------------------------


def _valid(kind: EquityLifecycleEventKind) -> EquityLifecycleEvent:
    at = _t("10:10")
    rows = {
        K.ENTRY_WINDOW_OPENED: (S.RECORDED, S.WAITING_FOR_ENTRY, _PLAIN, (), {}),
        K.ENTRY_ACTIVATED: (S.WAITING_FOR_ENTRY, S.ACTIVE, _EVIDENCE, (L.ENTRY,), {}),
        K.ENTRY_INDETERMINATE: (
            S.WAITING_FOR_ENTRY,
            S.INDETERMINATE_ENTRY,
            _EVIDENCE,
            (L.ENTRY, L.STOP),
            {"ordering": EquityIntrabarOrdering.UNKNOWN},
        ),
        K.ENTRY_CANCELLED: (
            S.WAITING_FOR_ENTRY,
            S.CANCELLED_BEFORE_ENTRY,
            _EVIDENCE,
            (L.STOP,),
            {"reason": EquityLifecycleCancellationReason.STOP_TOUCHED_BEFORE_ENTRY},
        ),
        K.ENTRY_WINDOW_EXPIRED: (S.WAITING_FOR_ENTRY, S.EXPIRED_BEFORE_ENTRY, _EVIDENCE, (), {}),
        K.TARGET_REACHED: (S.ACTIVE, S.CLOSED_TARGET, _EVIDENCE, (L.TARGET,), {}),
        K.STOP_REACHED: (S.ACTIVE, S.CLOSED_STOP, _EVIDENCE, (L.STOP,), {}),
        K.EXIT_INDETERMINATE: (
            S.ACTIVE,
            S.INDETERMINATE_EXIT,
            _EVIDENCE,
            (L.STOP, L.TARGET),
            {"ordering": EquityIntrabarOrdering.UNKNOWN},
        ),
        K.SESSION_CUTOFF_REACHED: (S.ACTIVE, S.SESSION_CUTOFF_REACHED, _EVIDENCE, (), {}),
        K.EVIDENCE_INCOMPLETE: (
            S.ACTIVE,
            S.INCOMPLETE_EVIDENCE,
            _PLAIN,
            (),
            {
                "deficiencies": (
                    EquityEvidenceDeficiency(
                        _t("10:00"), _t("10:05"), EquityEvidenceDeficiencyKind.MISSING
                    ),
                )
            },
        ),
        K.SOURCE_REVISION_RECORDED: (
            S.CLOSED_TARGET,
            S.CLOSED_TARGET,
            replace(_EVIDENCE, reference="ecs1-sha256:later"),
            (),
            {
                "cited_sequence": 1,
                "superseded_evidence": _EVIDENCE,
                "materiality": EquityRevisionMateriality.UNASSESSED,
            },
        ),
    }
    from_state, to_state, evidence, touched, extra = rows[kind]
    return EquityLifecycleEvent(2, kind, from_state, to_state, at, evidence, touched, **extra)


@pytest.mark.parametrize("kind", list(K), ids=str)
def test_every_kind_has_a_valid_shape(kind: EquityLifecycleEventKind) -> None:
    event = _valid(kind)
    assert event.kind is kind
    assert event.changes_state is (kind is not K.SOURCE_REVISION_RECORDED)


@pytest.mark.parametrize("kind", list(K), ids=str)
def test_ft09_every_other_from_state_is_refused(kind: EquityLifecycleEventKind) -> None:
    event = _valid(kind)
    if kind is K.SOURCE_REVISION_RECORDED:
        with pytest.raises(InvalidEquityLifecycleEventError):
            replace(event, to_state=S.ACTIVE)
        return
    for state in S:
        if state is event.from_state or (
            kind is K.EVIDENCE_INCOMPLETE and state is S.WAITING_FOR_ENTRY
        ):
            continue
        with pytest.raises(InvalidEquityLifecycleEventError):
            replace(event, from_state=state)


@pytest.mark.parametrize("kind", list(K), ids=str)
def test_ft09_a_wrong_target_touched_set_or_ordering_is_refused(
    kind: EquityLifecycleEventKind,
) -> None:
    event = _valid(kind)
    if kind is not K.SOURCE_REVISION_RECORDED:
        with pytest.raises(InvalidEquityLifecycleEventError):
            replace(event, to_state=S.RECORDED)
    with pytest.raises(InvalidEquityLifecycleEventError):
        replace(event, touched=(L.TARGET, L.STOP, L.ENTRY, L.ENTRY))
    flipped = (
        EquityIntrabarOrdering.NOT_REQUIRED
        if event.ordering is EquityIntrabarOrdering.UNKNOWN
        else EquityIntrabarOrdering.UNKNOWN
    )
    with pytest.raises(InvalidEquityLifecycleEventError):
        replace(event, ordering=flipped)


def test_touched_levels_must_be_in_canonical_order() -> None:
    with pytest.raises(InvalidEquityLifecycleEventError):
        replace(_valid(K.EXIT_INDETERMINATE), touched=(L.TARGET, L.STOP))
    with pytest.raises(InvalidEquityLifecycleEventError):
        replace(_valid(K.ENTRY_ACTIVATED), touched=(L.ENTRY, L.STOP))


def test_a_reason_is_required_for_and_only_for_a_cancellation() -> None:
    with pytest.raises(InvalidEquityLifecycleEventError, match="STOP_TOUCHED_BEFORE_ENTRY"):
        replace(_valid(K.ENTRY_CANCELLED), reason=None)
    with pytest.raises(InvalidEquityLifecycleEventError, match="no reason"):
        replace(
            _valid(K.STOP_REACHED),
            reason=EquityLifecycleCancellationReason.STOP_TOUCHED_BEFORE_ENTRY,
        )


def test_deficiencies_are_required_for_and_only_for_incomplete_evidence() -> None:
    incomplete = _valid(K.EVIDENCE_INCOMPLETE)
    with pytest.raises(InvalidEquityLifecycleEventError, match="at least one"):
        replace(incomplete, deficiencies=())
    with pytest.raises(InvalidEquityLifecycleEventError, match="no deficiencies"):
        replace(_valid(K.STOP_REACHED), deficiencies=incomplete.deficiencies)
    late = EquityEvidenceDeficiency(_t("10:10"), _t("10:15"), EquityEvidenceDeficiencyKind.MISSING)
    with pytest.raises(InvalidEquityLifecycleEventError, match="ended"):
        replace(incomplete, deficiencies=incomplete.deficiencies + (late,))
    earlier = EquityEvidenceDeficiency(
        _t("09:50"), _t("09:55"), EquityEvidenceDeficiencyKind.MISSING
    )
    with pytest.raises(InvalidEquityLifecycleEventError, match="ascending"):
        replace(incomplete, deficiencies=incomplete.deficiencies + (earlier,))
    with pytest.raises(InvalidEquityLifecycleEventError, match="first deficient"):
        replace(incomplete, evidence=EquityLifecycleEvidence("r", _t("09:00"), _t("09:05")))
    with pytest.raises(InvalidEquityLifecycleEventError, match="cites no candle"):
        replace(incomplete, evidence=_EVIDENCE)


def test_revision_fields_are_required_for_and_only_for_a_revision() -> None:
    revision = _valid(K.SOURCE_REVISION_RECORDED)
    with pytest.raises(InvalidEquityLifecycleEventError, match="no revision fields"):
        replace(_valid(K.STOP_REACHED), cited_sequence=1)
    with pytest.raises(InvalidEquityLifecycleEventError, match="earlier event"):
        replace(revision, cited_sequence=2)
    with pytest.raises(InvalidEquityLifecycleEventError, match="superseded"):
        replace(revision, superseded_evidence=None)
    with pytest.raises(InvalidEquityLifecycleEventError, match="UNASSESSED"):
        replace(revision, materiality=None)
    with pytest.raises(InvalidEquityLifecycleEventError, match="differ"):
        replace(revision, evidence=_EVIDENCE)
    with pytest.raises(InvalidEquityLifecycleEventError, match="cited interval"):
        replace(revision, evidence=EquityLifecycleEvidence("x", _t("10:05"), _t("10:10")))


def test_a_bar_driven_event_cites_its_candles_and_never_looks_ahead() -> None:
    activated = _valid(K.ENTRY_ACTIVATED)
    with pytest.raises(InvalidEquityLifecycleEventError, match="cite its candles"):
        replace(activated, evidence=_PLAIN)
    with pytest.raises(InvalidEquityLifecycleEventError, match="look-ahead"):
        replace(activated, evaluated_at=PointInTime("2026-11-02T10:04:59.999999+05:30"))
    assert replace(activated, evaluated_at=_t("10:05")).evaluated_at == _t("10:05")
    with pytest.raises(InvalidEquityLifecycleEventError, match="cites no candle"):
        replace(_valid(K.ENTRY_WINDOW_OPENED), evidence=_EVIDENCE)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("sequence", 0),
        ("sequence", True),
        ("kind", "ENTRY_ACTIVATED"),
        ("from_state", "WAITING_FOR_ENTRY"),
        ("evaluated_at", "2026-11-02T10:10:00Z"),
        ("evidence", None),
        ("touched", [L.ENTRY]),
        ("ordering", "UNKNOWN"),
        ("deficiencies", [None]),
    ],
)
def test_event_field_types_are_enforced(name: str, value: object) -> None:
    with pytest.raises(InvalidEquityLifecycleEventError):
        replace(_valid(K.ENTRY_ACTIVATED), **{name: value})


def test_every_lifecycle_error_is_a_core_validation_error() -> None:
    for error in (
        InvalidEquityLifecycleEventError,
        InvalidEquityLifecycleEvidenceError,
        InvalidEquityLifecycleWindowError,
    ):
        assert issubclass(error, ValidationError)
