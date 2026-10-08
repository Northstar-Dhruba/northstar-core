"""Tests for the OHLCV observation of one exact option contract."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
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
from northstar_core.futures import FuturesContract, FuturesOHLCVBar, FuturesProductReference
from northstar_core.options import (
    InvalidOptionOHLCVBarError,
    OptionContract,
    OptionOHLCVBar,
    OptionPremium,
    OptionProductReference,
    OptionRight,
    OptionStrike,
)

_NIFTY = OptionProductReference(Symbol("NIFTY"), ExchangeCode("NSE"))
_CLOSE_0810 = PointInTime("2026-10-08T10:10:00Z")
_CLOSE_0910 = PointInTime("2026-10-09T10:10:00Z")
_DAILY = Timeframe("1d")


def _contract(
    expiration: str = "2026-10-27", strike: str = "25000", right: OptionRight = OptionRight.CALL
) -> OptionContract:
    return OptionContract(_NIFTY, ExpirationDate(expiration), OptionStrike(Decimal(strike)), right)


def _p(value: str) -> OptionPremium:
    return OptionPremium(Decimal(value))


def _bar(
    contract: object = None,
    point_in_time: object = _CLOSE_0810,
    timeframe: object = _DAILY,
    open: object = None,
    high: object = None,
    low: object = None,
    close: object = None,
    volume: object = None,
) -> OptionOHLCVBar:
    return OptionOHLCVBar(
        contract=_contract() if contract is None else contract,
        point_in_time=point_in_time,
        timeframe=timeframe,
        open=_p("182.35") if open is None else open,
        high=_p("190") if high is None else high,
        low=_p("175.5") if low is None else low,
        close=_p("186.1") if close is None else close,
        volume=Quantity(Decimal("1200")) if volume is None else volume,
    )


# ---------------------------------------------------------------------------
# Shape and construction
# ---------------------------------------------------------------------------


def test_the_field_shape_is_exact() -> None:
    assert [field.name for field in fields(OptionOHLCVBar)] == [
        "contract",
        "point_in_time",
        "timeframe",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]
    assert OptionOHLCVBar.__slots__ == (
        "contract",
        "point_in_time",
        "timeframe",
        "open",
        "high",
        "low",
        "close",
        "volume",
    )


def test_a_bar_preserves_its_members() -> None:
    bar = _bar()

    assert bar.contract == _contract()
    assert bar.point_in_time == _CLOSE_0810
    assert bar.timeframe == _DAILY
    assert (bar.open, bar.high, bar.low, bar.close) == (
        _p("182.35"),
        _p("190"),
        _p("175.5"),
        _p("186.1"),
    )
    assert bar.volume == Quantity(Decimal("1200"))


@pytest.mark.parametrize("right", [OptionRight.CALL, OptionRight.PUT])
def test_call_and_put_bars_are_both_representable(right: OptionRight) -> None:
    assert _bar(contract=_contract(right=right)).contract.right is right


def test_a_daily_bar_uses_the_daily_timeframe() -> None:
    assert _bar(timeframe=Timeframe("1d")).timeframe == Timeframe("1d")


def test_a_zero_premium_bar_is_valid() -> None:
    """An option can trade at, or expire at, zero premium."""
    zero = _p("0")
    bar = _bar(open=zero, high=zero, low=zero, close=zero, volume=Quantity(Decimal("0")))

    assert bar.high == bar.low == zero
    assert bar.volume == Quantity(Decimal("0"))


def test_a_flat_bar_is_valid() -> None:
    flat = _p("50")

    assert _bar(open=flat, high=flat, low=flat, close=flat).high == flat


# ---------------------------------------------------------------------------
# OHLC coherence
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("open", "high", "low", "close"),
    [("191", "190", "175", "186"), ("182", "190", "175", "190.5"), ("182", "170", "175", "180")],
    ids=["open-above-high", "close-above-high", "low-above-high"],
)
def test_the_high_must_bound_open_close_and_low(open, high, low, close) -> None:
    with pytest.raises(InvalidOptionOHLCVBarError, match="high must be greater than or equal"):
        _bar(open=_p(open), high=_p(high), low=_p(low), close=_p(close))


@pytest.mark.parametrize(
    ("open", "high", "low", "close"),
    [("170", "190", "175", "186"), ("182", "190", "175", "174.95")],
    ids=["open-below-low", "close-below-low"],
)
def test_the_low_must_be_bounded_by_open_and_close(open, high, low, close) -> None:
    with pytest.raises(InvalidOptionOHLCVBarError, match="low must be less than or equal"):
        _bar(open=_p(open), high=_p(high), low=_p(low), close=_p(close))


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("contract", "NIFTY@NSE 2026-10-27 25000 CALL", "must be an OptionContract"),
        (
            "contract",
            FuturesContract(
                FuturesProductReference(Symbol("NIFTY"), ExchangeCode("NSE")),
                ExpirationDate("2026-10-27"),
            ),
            "must be an OptionContract",
        ),
        ("point_in_time", "2026-10-08T10:10:00Z", "must be a PointInTime"),
        ("timeframe", "1d", "must be a Timeframe"),
        ("open", QuoteValue(Decimal("182.35")), "open must be an OptionPremium"),
        ("high", Decimal("190"), "high must be an OptionPremium"),
        ("low", OptionStrike(Decimal("175")), "low must be an OptionPremium"),
        ("close", 186, "close must be an OptionPremium"),
        ("volume", Decimal("1200"), "volume must be a Quantity"),
        ("volume", 1200, "volume must be a Quantity"),
    ],
)
def test_wrong_member_types_are_rejected(field: str, value: object, message: str) -> None:
    with pytest.raises(InvalidOptionOHLCVBarError, match=message):
        _bar(**{field: value})


@pytest.mark.parametrize(
    "field", ["contract", "point_in_time", "timeframe", "open", "high", "low", "close", "volume"]
)
def test_none_members_are_rejected(field: str) -> None:
    with pytest.raises(InvalidOptionOHLCVBarError, match="cannot be None"):
        OptionOHLCVBar(
            **{
                "contract": _contract(),
                "point_in_time": _CLOSE_0810,
                "timeframe": _DAILY,
                "open": _p("1"),
                "high": _p("1"),
                "low": _p("1"),
                "close": _p("1"),
                "volume": Quantity(Decimal("1")),
                field: None,
            }
        )


@pytest.mark.parametrize("volume", ["1200.5", "0.1"])
def test_volume_must_be_a_whole_number_of_contracts(volume: str) -> None:
    with pytest.raises(InvalidOptionOHLCVBarError, match="whole number of option contracts"):
        _bar(volume=Quantity(Decimal(volume)))


def test_an_integral_volume_in_any_spelling_is_accepted() -> None:
    assert _bar(volume=Quantity(Decimal("1200.000"))).volume == Quantity(Decimal("1200"))


def test_the_error_is_a_validation_error() -> None:
    assert issubclass(InvalidOptionOHLCVBarError, ValidationError)


# ---------------------------------------------------------------------------
# Identity and value semantics
# ---------------------------------------------------------------------------


def test_the_natural_key_is_contract_instant_and_timeframe() -> None:
    bar = _bar()

    assert bar.natural_key == (_contract(), _CLOSE_0810, _DAILY)
    assert "natural_key" not in OptionOHLCVBar.__slots__


def test_equal_bars_compare_and_hash_equal() -> None:
    respelled = _bar(open=_p("182.350"), volume=Quantity(Decimal("1.2E+3")))

    assert respelled == _bar()
    assert hash(respelled) == hash(_bar())


@pytest.mark.parametrize(
    "other",
    [
        {"contract": _contract(strike="25050")},
        {"contract": _contract(right=OptionRight.PUT)},
        {"contract": _contract(expiration="2026-11-24")},
        {"point_in_time": _CLOSE_0910},
        {"timeframe": Timeframe("1w")},
    ],
    ids=["strike", "right", "expiry", "instant", "timeframe"],
)
def test_bars_differing_in_any_identity_component_are_distinct(other: dict) -> None:
    assert _bar(**other) != _bar()
    assert _bar(**other).natural_key != _bar().natural_key
    assert len({_bar(**other), _bar()}) == 2


def test_bars_sharing_an_identity_but_not_values_are_unequal() -> None:
    assert _bar(close=_p("186.2")) != _bar()
    assert _bar(close=_p("186.2")).natural_key == _bar().natural_key


def test_the_bar_is_immutable() -> None:
    bar = _bar()

    with pytest.raises(FrozenInstanceError):
        bar.close = _p("1")  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        bar.contract = _contract(strike="25050")  # type: ignore[misc]


def test_an_option_bar_is_never_a_futures_bar() -> None:
    assert not isinstance(_bar(), FuturesOHLCVBar)
    assert not issubclass(OptionOHLCVBar, FuturesOHLCVBar)


def test_string_and_repr_forms() -> None:
    bar = _bar()

    assert str(bar) == (
        "NIFTY@NSE 2026-10-27 25000 CALL 2026-10-08T10:10:00Z 1d "
        "O=182.35 H=190 L=175.5 C=186.1 V=1200"
    )
    assert repr(bar) == (
        "OptionOHLCVBar("
        "contract=OptionContract("
        "product=OptionProductReference("
        "product_code=Symbol(value='NIFTY'), exchange_code=ExchangeCode(value='NSE')), "
        "expiration_date=ExpirationDate(value='2026-10-27'), "
        "strike=OptionStrike(value=Decimal('25000')), "
        "right=<OptionRight.CALL: 'CALL'>), "
        "point_in_time=PointInTime(value='2026-10-08T10:10:00Z'), "
        f"timeframe={_DAILY!r}, "
        "open=OptionPremium(value=Decimal('182.35')), "
        "high=OptionPremium(value=Decimal('190')), "
        "low=OptionPremium(value=Decimal('175.5')), "
        "close=OptionPremium(value=Decimal('186.1')), "
        "volume=Quantity(value=Decimal('1200'))"
        ")"
    )


def test_the_bar_carries_no_open_interest_or_provider_data() -> None:
    bar = _bar()

    for absent in (
        "open_interest",
        "oi",
        "provider",
        "instrument_key",
        "source",
        "bid",
        "ask",
        "settlement_price",
        "implied_volatility",
        "delta",
        "trading_date",
    ):
        assert not hasattr(bar, absent)
