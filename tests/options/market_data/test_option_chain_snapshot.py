"""Contract tests for OptionChainEntry and OptionChainSnapshot."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from decimal import Decimal

import pytest

from northstar_core.derivatives import ExpirationDate
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import (
    ExchangeCode,
    PointInTime,
    Quantity,
    Symbol,
    Timeframe,
)
from northstar_core.options import (
    InvalidOptionChainEntryError,
    InvalidOptionChainSnapshotError,
    OptionChainEntry,
    OptionChainSnapshot,
    OptionContract,
    OptionOHLCVBar,
    OptionPremium,
    OptionProductReference,
    OptionRight,
    OptionStrike,
)

_NIFTY = OptionProductReference(Symbol("NIFTY"), ExchangeCode("NSE"))
_BANKNIFTY = OptionProductReference(Symbol("BANKNIFTY"), ExchangeCode("NSE"))
_EXPIRY = ExpirationDate("2026-10-27")
_AS_OF = PointInTime("2026-10-08T10:10:00Z")
_CALL, _PUT = OptionRight.CALL, OptionRight.PUT


def _contract(
    strike: str = "22600",
    right: OptionRight = _CALL,
    expiration: ExpirationDate = _EXPIRY,
    product: OptionProductReference = _NIFTY,
) -> OptionContract:
    return OptionContract(product, expiration, OptionStrike(Decimal(strike)), right)


def _bar(
    contract: OptionContract,
    instant: PointInTime = _AS_OF,
    timeframe: str = "1d",
    close: str = "132.6",
) -> OptionOHLCVBar:
    return OptionOHLCVBar(
        contract=contract,
        point_in_time=instant,
        timeframe=Timeframe(timeframe),
        open=OptionPremium(Decimal("191.8")),
        high=OptionPremium(Decimal("226.05")),
        low=OptionPremium(Decimal("122.45")),
        close=OptionPremium(Decimal(close)),
        volume=Quantity(Decimal("40")),
    )


def _entry(strike: str = "22600", right: OptionRight = _CALL, observed: bool = True):
    contract = _contract(strike, right)
    return OptionChainEntry(contract, _bar(contract) if observed else None)


def _snapshot(*entries: OptionChainEntry) -> OptionChainSnapshot:
    return OptionChainSnapshot(_NIFTY, _EXPIRY, _AS_OF, entries)


_CANONICAL = (
    _entry("22550", _CALL, observed=False),
    _entry("22550", _PUT),
    _entry("22600", _CALL),
    _entry("22600", _PUT, observed=False),
    _entry("22650", _PUT),
)


# ---------------------------------------------------------------------------
# OptionChainEntry
# ---------------------------------------------------------------------------


def test_an_entry_has_exactly_a_contract_and_an_optional_daily_bar() -> None:
    assert [field.name for field in fields(OptionChainEntry)] == ["contract", "daily_bar"]
    assert not hasattr(OptionChainEntry(_contract(), None), "__dict__")


def test_an_entry_without_a_bar_is_accepted() -> None:
    entry = OptionChainEntry(_contract(), None)

    assert entry.daily_bar is None
    assert str(entry) == "NIFTY@NSE 2026-10-27 22600 CALL: no daily bar"


def test_an_entry_with_its_own_bar_is_accepted() -> None:
    contract = _contract()
    entry = OptionChainEntry(contract, _bar(contract))

    assert entry.daily_bar == _bar(contract)
    assert str(entry) == "NIFTY@NSE 2026-10-27 22600 CALL: C=132.6 V=40"


@pytest.mark.parametrize(
    "other",
    [_contract(right=_PUT), _contract(strike="22650"),
     _contract(expiration=ExpirationDate("2026-11-24")), _contract(product=_BANKNIFTY)],
    ids=["right", "strike", "expiration", "product"],
)  # fmt: skip
def test_an_entry_rejects_another_contracts_bar(other: OptionContract) -> None:
    with pytest.raises(InvalidOptionChainEntryError, match="daily bar is for"):
        OptionChainEntry(_contract(), _bar(other))


@pytest.mark.parametrize(
    ("contract", "bar"),
    [(None, None), ("NIFTY 22600 CALL", None), (_contract(), "132.6"), (_contract(), object())],
)
def test_an_entry_rejects_foreign_values(contract, bar) -> None:
    with pytest.raises(InvalidOptionChainEntryError):
        OptionChainEntry(contract, bar)


def test_an_entry_is_immutable_and_a_validation_error() -> None:
    entry = OptionChainEntry(_contract(), None)

    with pytest.raises(FrozenInstanceError):
        entry.daily_bar = _bar(_contract())  # type: ignore[misc]
    assert issubclass(InvalidOptionChainEntryError, ValidationError)


def test_entries_compare_by_value() -> None:
    assert _entry() == _entry()
    assert _entry() != _entry(observed=False)
    assert hash(_entry()) == hash(_entry())


# ---------------------------------------------------------------------------
# OptionChainSnapshot
# ---------------------------------------------------------------------------


def test_a_snapshot_has_exactly_its_four_fields() -> None:
    assert [field.name for field in fields(OptionChainSnapshot)] == [
        "product",
        "expiration_date",
        "as_of",
        "entries",
    ]
    assert not hasattr(_snapshot(*_CANONICAL), "__dict__")


def test_a_canonical_snapshot_is_accepted() -> None:
    snapshot = _snapshot(*_CANONICAL)

    assert snapshot.entries == _CANONICAL
    assert [(e.contract.strike.value, e.contract.right) for e in snapshot.entries] == [
        (Decimal("22550"), _CALL),
        (Decimal("22550"), _PUT),
        (Decimal("22600"), _CALL),
        (Decimal("22600"), _PUT),
        (Decimal("22650"), _PUT),
    ]
    assert str(snapshot) == "NIFTY@NSE 2026-10-27 as of 2026-10-08T10:10:00Z: 5 contracts"


def test_a_snapshot_may_hold_only_entries_without_bars() -> None:
    snapshot = _snapshot(_entry(observed=False), _entry(right=_PUT, observed=False))

    assert all(entry.daily_bar is None for entry in snapshot.entries)


def test_a_snapshot_is_immutable() -> None:
    snapshot = _snapshot(*_CANONICAL)

    with pytest.raises(FrozenInstanceError):
        snapshot.entries = ()  # type: ignore[misc]
    assert issubclass(InvalidOptionChainSnapshotError, ValidationError)


def test_a_snapshot_needs_at_least_one_entry() -> None:
    with pytest.raises(InvalidOptionChainSnapshotError, match="at least one entry"):
        _snapshot()


@pytest.mark.parametrize(
    "entries",
    [list(_CANONICAL), (_CANONICAL[0], _contract()), None],
    ids=["list", "foreign", "none"],
)
def test_the_entries_must_be_a_tuple_of_entries(entries) -> None:
    with pytest.raises(InvalidOptionChainSnapshotError, match="tuple of OptionChainEntry"):
        OptionChainSnapshot(_NIFTY, _EXPIRY, _AS_OF, entries)


@pytest.mark.parametrize(
    ("product", "expiration", "as_of"),
    [
        ("NIFTY@NSE", _EXPIRY, _AS_OF),
        (_NIFTY, "2026-10-27", _AS_OF),
        (_NIFTY, _EXPIRY, "2026-10-08T10:10:00Z"),
    ],
    ids=["product", "expiration", "as-of"],
)
def test_the_coordinates_must_be_core_values(product, expiration, as_of) -> None:
    with pytest.raises(InvalidOptionChainSnapshotError):
        OptionChainSnapshot(product, expiration, as_of, _CANONICAL)


def test_an_entry_of_another_product_is_rejected() -> None:
    other = _contract(product=_BANKNIFTY)

    with pytest.raises(InvalidOptionChainSnapshotError, match="is not a NIFTY@NSE contract"):
        _snapshot(_entry("22550"), OptionChainEntry(other, None))


def test_an_entry_of_another_expiration_is_rejected() -> None:
    other = _contract(strike="22650", expiration=ExpirationDate("2026-11-24"))

    with pytest.raises(InvalidOptionChainSnapshotError, match="does not expire on 2026-10-27"):
        _snapshot(_entry("22550"), OptionChainEntry(other, None))


def test_a_duplicate_contract_is_rejected_even_with_a_different_bar_state() -> None:
    with pytest.raises(InvalidOptionChainSnapshotError, match="more than once"):
        _snapshot(_entry("22600"), _entry("22600", observed=False))


@pytest.mark.parametrize(
    "entries",
    [
        (_entry("22600", _PUT), _entry("22600", _CALL)),
        (_entry("22650"), _entry("22600")),
        (_entry("22600", _PUT), _entry("22550", _CALL)),
        (_entry("22550", _CALL), _entry("22600", _CALL), _entry("22550", _PUT)),
    ],
    ids=["put-before-call", "strike-descending", "put-then-lower-call", "rights-grouped"],
)
def test_entries_out_of_canonical_order_are_rejected(entries) -> None:
    with pytest.raises(InvalidOptionChainSnapshotError, match="strike ascending, then CALL"):
        _snapshot(*entries)


def test_strikes_order_numerically_not_textually() -> None:
    snapshot = _snapshot(_entry("9950"), _entry("10000"), _entry("10000.5"))

    assert [e.contract.strike.value for e in snapshot.entries] == [
        Decimal("9950"),
        Decimal("10000"),
        Decimal("10000.5"),
    ]


@pytest.mark.parametrize(
    "instant",
    [PointInTime("2026-10-07T10:10:00Z"), PointInTime("2026-10-09T10:10:00Z"),
     PointInTime("2026-10-08T10:09:59Z")],
    ids=["earlier-session", "later-session", "second-early"],
)  # fmt: skip
def test_a_bar_not_stamped_exactly_at_as_of_is_rejected(instant: PointInTime) -> None:
    contract = _contract()

    with pytest.raises(InvalidOptionChainSnapshotError, match="is stamped"):
        _snapshot(OptionChainEntry(contract, _bar(contract, instant=instant)))


def test_an_equal_instant_in_another_spelling_is_the_same_as_of() -> None:
    contract = _contract()
    bar = _bar(contract, instant=PointInTime("2026-10-08T15:40:00+05:30"))

    assert _snapshot(OptionChainEntry(contract, bar)).entries[0].daily_bar == bar


@pytest.mark.parametrize("timeframe", ["1h", "1m", "1w"])
def test_a_bar_that_is_not_daily_is_rejected(timeframe: str) -> None:
    contract = _contract()

    with pytest.raises(InvalidOptionChainSnapshotError, match="not 1d"):
        _snapshot(OptionChainEntry(contract, _bar(contract, timeframe=timeframe)))


def test_the_snapshot_carries_no_selection_or_reference_data() -> None:
    names = {field.name for field in fields(OptionChainSnapshot)} | {
        field.name for field in fields(OptionChainEntry)
    }
    for forbidden in (
        "open_interest", "provider", "underlying", "underlying_value", "trading_date",
        "selected", "selectable", "score", "moneyness", "dte", "implied_volatility",
        "delta", "bid", "ask", "established_at", "instrument_key", "lot_size",
    ):  # fmt: skip
        assert forbidden not in names
