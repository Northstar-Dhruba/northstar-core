"""Tests for the futures replay snapshot.

The look-ahead guarantee lives here: a snapshot may hold nothing later than its
replay instant. The other invariants exist so that a snapshot cannot silently
describe more than one contract, more than one timeframe, or a history whose
order was quietly repaired.
"""

from __future__ import annotations

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
from northstar_core.futures import (
    FuturesContract,
    FuturesOHLCVBar,
    FuturesProductReference,
    FuturesReplaySnapshot,
    InvalidFuturesReplaySnapshotError,
)

_CME = ExchangeCode("CME")
_ES = FuturesProductReference(Symbol("ES"), _CME)
_MES = FuturesProductReference(Symbol("MES"), _CME)

_ES_DEC = FuturesContract(_ES, ExpirationDate("2026-12-18"))
_ES_MAR = FuturesContract(_ES, ExpirationDate("2027-03-19"))
_MES_DEC = FuturesContract(_MES, ExpirationDate("2026-12-18"))

_DAILY = Timeframe("1d")
_HOURLY = Timeframe("1h")


def _instant(day: int) -> PointInTime:
    return PointInTime(f"2026-09-{day:02d}T22:00:00Z")


def _bar(
    day: int,
    *,
    contract: FuturesContract = _ES_DEC,
    timeframe: Timeframe = _DAILY,
    point_in_time: PointInTime | None = None,
    close: str = "7663",
) -> FuturesOHLCVBar:
    return FuturesOHLCVBar(
        contract=contract,
        point_in_time=point_in_time if point_in_time is not None else _instant(day),
        timeframe=timeframe,
        open=QuoteValue(Decimal("7660")),
        high=QuoteValue(Decimal("7700")),
        low=QuoteValue(Decimal("7500")),
        close=QuoteValue(Decimal(close)),
        volume=Quantity(Decimal("1000")),
    )


def _snapshot(**overrides: object) -> FuturesReplaySnapshot:
    members: dict[str, object] = {
        "contract": _ES_DEC,
        "timeframe": _DAILY,
        "replay_instant": _instant(17),
        "observations": (_bar(15), _bar(16), _bar(17)),
    }
    members.update(overrides)
    return FuturesReplaySnapshot(**members)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_a_snapshot_preserves_its_members() -> None:
    snapshot = _snapshot()

    assert snapshot.contract == _ES_DEC
    assert snapshot.timeframe == _DAILY
    assert snapshot.replay_instant == _instant(17)
    assert len(snapshot.observations) == 3


def test_an_empty_snapshot_is_rejected() -> None:
    """A replay boundary exists only because an observation completed.

    A history with nothing in it is an empty tuple of snapshots, which is the
    replay use case's concern, not a snapshot of nothing.
    """
    with pytest.raises(InvalidFuturesReplaySnapshotError, match="at least one observation"):
        _snapshot(observations=())


def test_a_single_observation_snapshot_is_accepted_when_the_instant_matches() -> None:
    snapshot = _snapshot(replay_instant=_instant(17), observations=(_bar(17),))

    assert snapshot.observations == (_bar(17),)
    assert snapshot.replay_instant == snapshot.latest_observation.point_in_time


def test_a_single_observation_snapshot_with_an_earlier_instant_is_rejected() -> None:
    with pytest.raises(InvalidFuturesReplaySnapshotError):
        _snapshot(replay_instant=_instant(16), observations=(_bar(17),))


def test_a_single_observation_snapshot_with_a_later_instant_is_rejected() -> None:
    with pytest.raises(
        InvalidFuturesReplaySnapshotError, match="must equal its latest observation"
    ):
        _snapshot(replay_instant=_instant(18), observations=(_bar(17),))


def test_a_multi_observation_cumulative_snapshot_is_accepted() -> None:
    snapshot = _snapshot(replay_instant=_instant(17), observations=(_bar(15), _bar(16), _bar(17)))

    assert [bar.point_in_time for bar in snapshot.observations] == [
        _instant(15),
        _instant(16),
        _instant(17),
    ]
    assert snapshot.replay_instant == snapshot.latest_observation.point_in_time


def test_the_latest_observation_is_the_newest_visible_bar() -> None:
    snapshot = _snapshot()

    assert snapshot.latest_observation.point_in_time == _instant(17)


# ---------------------------------------------------------------------------
# Look-ahead
# ---------------------------------------------------------------------------


def test_an_observation_after_the_replay_instant_is_rejected() -> None:
    """The whole look-ahead guarantee, checked rather than assumed."""
    with pytest.raises(InvalidFuturesReplaySnapshotError, match="after the replay instant"):
        _snapshot(replay_instant=_instant(16), observations=(_bar(15), _bar(16), _bar(17)))


def test_an_observation_exactly_at_the_replay_instant_is_visible() -> None:
    snapshot = _snapshot(replay_instant=_instant(16), observations=(_bar(15), _bar(16)))

    assert len(snapshot.observations) == 2


def test_visibility_is_compared_semantically_not_textually() -> None:
    """'.5Z' sorts before 'Z' as text while being the later instant."""
    later = PointInTime("2026-09-17T22:00:00.5Z")
    boundary = _instant(17)

    assert later.value < boundary.value  # the text trap
    with pytest.raises(InvalidFuturesReplaySnapshotError, match="after the replay instant"):
        _snapshot(replay_instant=boundary, observations=(_bar(17, point_in_time=later),))


def test_the_replay_instant_equals_the_latest_observation() -> None:
    snapshot = _snapshot(replay_instant=_instant(16), observations=(_bar(15), _bar(16)))

    assert snapshot.replay_instant == snapshot.latest_observation.point_in_time


def test_a_replay_instant_after_the_latest_observation_is_rejected() -> None:
    """A snapshot dated past its newest bar is a decision on no new evidence."""
    with pytest.raises(
        InvalidFuturesReplaySnapshotError, match="must equal its latest observation"
    ):
        _snapshot(replay_instant=_instant(20), observations=(_bar(15), _bar(16)))


def test_a_replay_instant_before_the_latest_observation_is_rejected() -> None:
    """Caught by the look-ahead rule: the newest bar would sit after the instant."""
    with pytest.raises(InvalidFuturesReplaySnapshotError):
        _snapshot(replay_instant=_instant(15), observations=(_bar(15), _bar(16)))


def test_an_offset_equivalent_replay_instant_is_accepted() -> None:
    """Two spellings of one instant are one instant; no text equality is used."""
    utc = PointInTime("2026-09-16T22:00:00Z")
    offset = PointInTime("2026-09-17T03:30:00+05:30")

    assert offset.value == utc.value  # canonicalised to the same UTC text
    snapshot = _snapshot(replay_instant=offset, observations=(_bar(15), _bar(16)))

    assert snapshot.replay_instant.compare(_instant(16)) == 0


def test_a_sub_second_replay_instant_must_match_exactly() -> None:
    """'.5Z' sorts before 'Z' as text but is the later instant."""
    fractional = PointInTime("2026-09-16T22:00:00.5Z")

    with pytest.raises(
        InvalidFuturesReplaySnapshotError, match="must equal its latest observation"
    ):
        _snapshot(replay_instant=fractional, observations=(_bar(15), _bar(16)))


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------


def test_unordered_observations_are_rejected_not_sorted() -> None:
    with pytest.raises(InvalidFuturesReplaySnapshotError, match="strictly ordered"):
        _snapshot(observations=(_bar(16), _bar(15), _bar(17)))


def test_duplicate_completion_instants_are_rejected() -> None:
    """Contract and timeframe are fixed, so one instant is one natural key."""
    with pytest.raises(InvalidFuturesReplaySnapshotError, match="strictly ordered"):
        _snapshot(observations=(_bar(15), _bar(15, close="7664"), _bar(17)))


def test_an_identical_repeated_observation_is_rejected() -> None:
    repeated = _bar(15)

    with pytest.raises(InvalidFuturesReplaySnapshotError, match="strictly ordered"):
        _snapshot(observations=(repeated, repeated, _bar(17)))


def test_the_snapshot_never_reorders_its_input() -> None:
    ordered = (_bar(15), _bar(16), _bar(17))
    snapshot = _snapshot(observations=ordered)

    assert snapshot.observations == ordered
    assert [bar.point_in_time for bar in snapshot.observations] == [
        _instant(15),
        _instant(16),
        _instant(17),
    ]


def test_sparse_observations_are_valid() -> None:
    """Consecutive observations need not be one timeframe apart."""
    snapshot = _snapshot(observations=(_bar(1), _bar(9), _bar(17)))

    assert len(snapshot.observations) == 3


def test_a_single_observation_snapshot_is_valid() -> None:
    assert len(_snapshot(observations=(_bar(17),)).observations) == 1


# ---------------------------------------------------------------------------
# Contract and timeframe agreement
# ---------------------------------------------------------------------------


def test_an_observation_for_another_contract_is_rejected() -> None:
    with pytest.raises(InvalidFuturesReplaySnapshotError, match="does not belong to"):
        _snapshot(observations=(_bar(15), _bar(16, contract=_ES_MAR)))


def test_march_cannot_leak_into_a_december_snapshot() -> None:
    with pytest.raises(InvalidFuturesReplaySnapshotError, match="does not belong to"):
        FuturesReplaySnapshot(_ES_DEC, _DAILY, _instant(17), (_bar(17, contract=_ES_MAR),))


def test_a_micro_contract_cannot_leak_into_a_standard_snapshot() -> None:
    with pytest.raises(InvalidFuturesReplaySnapshotError, match="does not belong to"):
        FuturesReplaySnapshot(_ES_DEC, _DAILY, _instant(17), (_bar(17, contract=_MES_DEC),))


def test_a_standard_contract_cannot_leak_into_a_micro_snapshot() -> None:
    with pytest.raises(InvalidFuturesReplaySnapshotError, match="does not belong to"):
        FuturesReplaySnapshot(_MES_DEC, _DAILY, _instant(17), (_bar(17, contract=_ES_DEC),))


def test_an_observation_with_another_timeframe_is_rejected() -> None:
    with pytest.raises(InvalidFuturesReplaySnapshotError, match="does not match the snapshot"):
        _snapshot(observations=(_bar(15), _bar(16, timeframe=_HOURLY)))


def test_a_rebuilt_equal_contract_is_accepted_by_value() -> None:
    rebuilt = FuturesContract(
        FuturesProductReference(Symbol("ES"), ExchangeCode("CME")),
        ExpirationDate("2026-12-18"),
    )

    assert rebuilt is not _ES_DEC
    assert len(_snapshot(contract=rebuilt).observations) == 3


# ---------------------------------------------------------------------------
# Type validation
# ---------------------------------------------------------------------------


def test_wrong_member_types_are_rejected() -> None:
    with pytest.raises(InvalidFuturesReplaySnapshotError, match="must be a FuturesContract"):
        _snapshot(contract=_ES)
    with pytest.raises(InvalidFuturesReplaySnapshotError, match="must be a Timeframe value"):
        _snapshot(timeframe="1d")
    with pytest.raises(InvalidFuturesReplaySnapshotError, match="must be a PointInTime value"):
        _snapshot(replay_instant="2026-09-17T22:00:00Z")
    with pytest.raises(InvalidFuturesReplaySnapshotError, match="must be a tuple"):
        _snapshot(observations=[_bar(15)])
    with pytest.raises(InvalidFuturesReplaySnapshotError, match="must contain FuturesOHLCVBar"):
        _snapshot(observations=("not a bar",))


def test_the_error_is_a_validation_error() -> None:
    assert issubclass(InvalidFuturesReplaySnapshotError, ValidationError)


# ---------------------------------------------------------------------------
# Value semantics and quotes
# ---------------------------------------------------------------------------


def test_the_snapshot_is_immutable() -> None:
    snapshot = _snapshot()

    with pytest.raises(AttributeError):
        snapshot.replay_instant = _instant(20)


def test_equality_follows_value() -> None:
    assert _snapshot() == _snapshot()
    assert _snapshot() != _snapshot(replay_instant=_instant(16), observations=(_bar(15), _bar(16)))


def test_negative_quotations_survive_a_snapshot() -> None:
    negative = FuturesOHLCVBar(
        contract=_ES_DEC,
        point_in_time=_instant(17),
        timeframe=_DAILY,
        open=QuoteValue(Decimal("-14.00")),
        high=QuoteValue(Decimal("-10.50")),
        low=QuoteValue(Decimal("-40.32")),
        close=QuoteValue(Decimal("-37.63")),
        volume=Quantity(Decimal("248000")),
    )

    snapshot = _snapshot(observations=(negative,))

    assert snapshot.observations[0].close == QuoteValue(Decimal("-37.63"))


def test_the_snapshot_carries_no_currency_or_deferred_concept() -> None:
    snapshot = _snapshot()

    for absent in ("currency", "multiplier", "tick_size", "open_interest", "settlement"):
        assert not hasattr(snapshot, absent)


def test_string_and_repr_forms() -> None:
    snapshot = _snapshot()

    assert str(snapshot) == ("ES@CME 2026-12-18 1d @ 2026-09-17T22:00:00Z (3 observations)")
    assert repr(snapshot).startswith("FuturesReplaySnapshot(contract=")
