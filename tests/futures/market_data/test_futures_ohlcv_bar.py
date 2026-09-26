"""Tests for the futures OHLCV observation."""

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
    InvalidFuturesOHLCVBarError,
)

_CME = ExchangeCode("CME")
_NYMEX = ExchangeCode("NYMEX")

_ES = FuturesProductReference(Symbol("ES"), _CME)
_MES = FuturesProductReference(Symbol("MES"), _CME)
_CL = FuturesProductReference(Symbol("CL"), _NYMEX)

_MARCH = ExpirationDate("2026-03-20")
_JUNE = ExpirationDate("2026-06-19")

_ES_MARCH = FuturesContract(_ES, _MARCH)
_MES_MARCH = FuturesContract(_MES, _MARCH)
_ES_JUNE = FuturesContract(_ES, _JUNE)
_CL_MAY = FuturesContract(_CL, ExpirationDate("2020-05-19"))

_INSTANT = PointInTime("2026-01-15T21:00:00Z")
_DAILY = Timeframe("1d")


def _quote(value: str) -> QuoteValue:
    return QuoteValue(Decimal(value))


def _bar(
    contract: FuturesContract = _ES_MARCH,
    point_in_time: PointInTime = _INSTANT,
    timeframe: Timeframe = _DAILY,
    open_quote: str = "5430.00",
    high: str = "5450.25",
    low: str = "5425.50",
    close: str = "5442.75",
    volume: str = "1250000",
) -> FuturesOHLCVBar:
    return FuturesOHLCVBar(
        contract=contract,
        point_in_time=point_in_time,
        timeframe=timeframe,
        open=_quote(open_quote),
        high=_quote(high),
        low=_quote(low),
        close=_quote(close),
        volume=Quantity(Decimal(volume)),
    )


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_a_bar_preserves_its_members() -> None:
    bar = _bar()

    assert bar.contract == _ES_MARCH
    assert bar.point_in_time == _INSTANT
    assert bar.timeframe == _DAILY
    assert bar.open == _quote("5430.00")
    assert bar.high == _quote("5450.25")
    assert bar.low == _quote("5425.50")
    assert bar.close == _quote("5442.75")
    assert bar.volume == Quantity(Decimal("1250000"))


def test_a_flat_bar_where_every_quote_is_equal_is_valid() -> None:
    bar = _bar(open_quote="5430", high="5430", low="5430", close="5430")

    assert bar.high == bar.low == bar.open == bar.close


def test_zero_volume_is_allowed() -> None:
    """A session with no trades is a fact, not an invalid observation."""
    assert _bar(volume="0").volume == Quantity(Decimal("0"))


@pytest.mark.parametrize("timeframe", ["1m", "1h", "1d", "1w", "1M"])
def test_any_approved_timeframe_is_accepted(timeframe: str) -> None:
    assert _bar(timeframe=Timeframe(timeframe)).timeframe == Timeframe(timeframe)


# ---------------------------------------------------------------------------
# Negative quotations
# ---------------------------------------------------------------------------


def test_an_entirely_negative_session_is_representable() -> None:
    """The session a Price-based bar could not have recorded at all."""
    bar = _bar(
        contract=_CL_MAY,
        point_in_time=PointInTime("2020-04-20T18:30:00Z"),
        open_quote="-14.00",
        high="-10.50",
        low="-40.32",
        close="-37.63",
        volume="248000",
    )

    assert bar.close == _quote("-37.63")
    assert bar.low == _quote("-40.32")
    assert bar.high > bar.low


def test_a_session_crossing_zero_is_valid() -> None:
    bar = _bar(
        contract=_CL_MAY,
        open_quote="10.50",
        high="11.00",
        low="-5.25",
        close="-2.00",
        volume="100",
    )

    assert bar.low < _quote("0") < bar.high
    assert bar.close < _quote("0") < bar.open


def test_ordering_is_numeric_and_not_lexicographic_for_negatives() -> None:
    """-40.32 is below -5.25; a text comparison would say the opposite."""
    bar = _bar(
        contract=_CL_MAY,
        open_quote="-5.25",
        high="-5.25",
        low="-40.32",
        close="-40.32",
        volume="1",
    )

    assert bar.low == _quote("-40.32")
    assert bar.high == _quote("-5.25")


def test_a_negative_high_below_a_negative_low_is_rejected() -> None:
    with pytest.raises(InvalidFuturesOHLCVBarError, match="high must be greater than or equal"):
        _bar(contract=_CL_MAY, open_quote="-40", high="-40", low="-10", close="-40")


# ---------------------------------------------------------------------------
# OHLC invariants
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("open_quote", "high", "low", "close"),
    [
        ("5460.00", "5450.25", "5425.50", "5442.75"),
        ("5430.00", "5450.25", "5425.50", "5460.00"),
        ("5430.00", "5420.00", "5425.50", "5422.00"),
    ],
    ids=["high_below_open", "high_below_close", "high_below_low"],
)
def test_a_high_below_another_quote_is_rejected(
    open_quote: str, high: str, low: str, close: str
) -> None:
    with pytest.raises(InvalidFuturesOHLCVBarError, match="high must be greater than or equal"):
        _bar(open_quote=open_quote, high=high, low=low, close=close)


@pytest.mark.parametrize(
    ("open_quote", "high", "low", "close"),
    [
        ("5420.00", "5450.25", "5425.50", "5442.75"),
        ("5430.00", "5450.25", "5425.50", "5424.00"),
    ],
    ids=["low_above_open", "low_above_close"],
)
def test_a_low_above_another_quote_is_rejected(
    open_quote: str, high: str, low: str, close: str
) -> None:
    with pytest.raises(InvalidFuturesOHLCVBarError, match="low must be less than or equal"):
        _bar(open_quote=open_quote, high=high, low=low, close=close)


def test_equivalent_quote_spellings_do_not_break_the_invariants() -> None:
    """5430 and 5430.0000 are one quotation, so neither bound is violated."""
    bar = _bar(open_quote="5430.0000", high="5430", low="5430.00", close="5.43E+3")

    assert bar.open == bar.high == bar.low == bar.close


# ---------------------------------------------------------------------------
# Type validation
# ---------------------------------------------------------------------------


def test_none_members_are_rejected() -> None:
    with pytest.raises(InvalidFuturesOHLCVBarError, match="contract cannot be None"):
        _bar(contract=None)
    with pytest.raises(InvalidFuturesOHLCVBarError, match="point-in-time context cannot be None"):
        _bar(point_in_time=None)
    with pytest.raises(InvalidFuturesOHLCVBarError, match="timeframe cannot be None"):
        _bar(timeframe=None)


@pytest.mark.parametrize("field_name", ["open", "high", "low", "close"])
def test_a_missing_quote_is_rejected_by_name(field_name: str) -> None:
    members = {
        "contract": _ES_MARCH,
        "point_in_time": _INSTANT,
        "timeframe": _DAILY,
        "open": _quote("5430"),
        "high": _quote("5450"),
        "low": _quote("5425"),
        "close": _quote("5442"),
        "volume": Quantity(Decimal("1")),
    }
    members[field_name] = None

    with pytest.raises(InvalidFuturesOHLCVBarError, match=f"{field_name} cannot be None"):
        FuturesOHLCVBar(**members)


def test_volume_cannot_be_none() -> None:
    with pytest.raises(InvalidFuturesOHLCVBarError, match="volume cannot be None"):
        FuturesOHLCVBar(
            contract=_ES_MARCH,
            point_in_time=_INSTANT,
            timeframe=_DAILY,
            open=_quote("1"),
            high=_quote("1"),
            low=_quote("1"),
            close=_quote("1"),
            volume=None,
        )


def test_wrong_member_types_are_rejected() -> None:
    with pytest.raises(InvalidFuturesOHLCVBarError, match="must be a FuturesContract value"):
        _bar(contract=_ES)
    with pytest.raises(InvalidFuturesOHLCVBarError, match="must be a PointInTime value"):
        _bar(point_in_time="2026-01-15T21:00:00Z")
    with pytest.raises(InvalidFuturesOHLCVBarError, match="must be a Timeframe value"):
        _bar(timeframe="1d")


def test_a_raw_decimal_is_not_a_quotation() -> None:
    with pytest.raises(InvalidFuturesOHLCVBarError, match="open must be a QuoteValue"):
        FuturesOHLCVBar(
            contract=_ES_MARCH,
            point_in_time=_INSTANT,
            timeframe=_DAILY,
            open=Decimal("5430"),
            high=_quote("5450"),
            low=_quote("5425"),
            close=_quote("5442"),
            volume=Quantity(Decimal("1")),
        )


def test_a_quantity_is_not_a_quotation_and_a_quotation_is_not_a_volume() -> None:
    with pytest.raises(InvalidFuturesOHLCVBarError, match="high must be a QuoteValue"):
        FuturesOHLCVBar(
            contract=_ES_MARCH,
            point_in_time=_INSTANT,
            timeframe=_DAILY,
            open=_quote("5430"),
            high=Quantity(Decimal("5450")),
            low=_quote("5425"),
            close=_quote("5442"),
            volume=Quantity(Decimal("1")),
        )
    with pytest.raises(InvalidFuturesOHLCVBarError, match="volume must be a Quantity value"):
        FuturesOHLCVBar(
            contract=_ES_MARCH,
            point_in_time=_INSTANT,
            timeframe=_DAILY,
            open=_quote("5430"),
            high=_quote("5450"),
            low=_quote("5425"),
            close=_quote("5442"),
            volume=_quote("1"),
        )


def test_the_error_is_a_validation_error() -> None:
    assert issubclass(InvalidFuturesOHLCVBarError, ValidationError)
    with pytest.raises(ValidationError):
        _bar(contract=None)


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


def test_the_natural_key_is_contract_instant_and_timeframe() -> None:
    bar = _bar()

    assert bar.natural_key == (_ES_MARCH, _INSTANT, _DAILY)
    assert len(bar.natural_key) == 3


def test_the_natural_key_expands_to_product_exchange_and_expiry() -> None:
    contract, point_in_time, timeframe = _bar().natural_key

    assert contract.product.product_code == Symbol("ES")
    assert contract.product.exchange_code == _CME
    assert contract.expiration_date == _MARCH
    assert (point_in_time, timeframe) == (_INSTANT, _DAILY)


def test_es_and_mes_at_one_instant_are_distinct_bars() -> None:
    """The defect the identity correction fixed: these must never merge."""
    standard = _bar(contract=_ES_MARCH)
    micro = _bar(contract=_MES_MARCH)

    assert standard != micro
    assert standard.natural_key != micro.natural_key
    assert len({standard, micro}) == 2
    assert len({standard.natural_key, micro.natural_key}) == 2


def test_one_product_at_different_expiries_gives_distinct_bars() -> None:
    march = _bar(contract=_ES_MARCH)
    june = _bar(contract=_ES_JUNE)

    assert march != june
    assert march.natural_key != june.natural_key
    assert march.contract.product == june.contract.product


def test_one_contract_at_different_instants_gives_distinct_bars() -> None:
    first = _bar(point_in_time=PointInTime("2026-01-15T21:00:00Z"))
    second = _bar(point_in_time=PointInTime("2026-01-16T21:00:00Z"))

    assert first.natural_key != second.natural_key


def test_one_contract_at_different_timeframes_gives_distinct_bars() -> None:
    daily = _bar(timeframe=Timeframe("1d"))
    hourly = _bar(timeframe=Timeframe("1h"))

    assert daily.natural_key != hourly.natural_key


def test_identical_observations_are_equal_and_hash_alike() -> None:
    assert _bar() == _bar()
    assert hash(_bar()) == hash(_bar())
    assert len({_bar(), _bar()}) == 1


def test_it_is_usable_as_a_dictionary_key() -> None:
    assert {_bar(): "ES March"}[_bar()] == "ES March"


def test_bars_differing_only_in_a_quote_are_unequal() -> None:
    assert _bar(close="5442.75") != _bar(close="5442.50")


# ---------------------------------------------------------------------------
# Value semantics and scope
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field_name",
    ["contract", "point_in_time", "timeframe", "open", "high", "low", "close", "volume"],
)
def test_the_bar_is_immutable(field_name: str) -> None:
    with pytest.raises(AttributeError):
        setattr(_bar(), field_name, None)


def test_the_natural_key_is_read_only() -> None:
    with pytest.raises(AttributeError):
        _bar().natural_key = ()


def test_string_and_repr_forms() -> None:
    bar = _bar()

    assert str(bar) == (
        "ES@CME 2026-03-20 2026-01-15T21:00:00Z 1d O=5430 H=5450.25 L=5425.5 C=5442.75 V=1250000"
    )
    assert repr(bar).startswith("FuturesOHLCVBar(contract=")


def test_the_bar_carries_no_deferred_or_equity_field() -> None:
    bar = _bar()

    for absent in (
        "adjusted_close",
        "open_interest",
        "settlement_price",
        "currency",
        "multiplier",
        "contract_multiplier",
        "tick_size",
        "provider_symbol",
        "listing_reference",
        "symbol",
        "exchange_code",
    ):
        assert not hasattr(bar, absent)


def test_only_the_approved_fields_are_stored() -> None:
    assert set(FuturesOHLCVBar.__slots__) == {
        "contract",
        "point_in_time",
        "timeframe",
        "open",
        "high",
        "low",
        "close",
        "volume",
    }


def test_the_constructor_accepts_no_adjusted_close_or_open_interest() -> None:
    """Absent by construction, not merely unset."""
    members = {
        "contract": _ES_MARCH,
        "point_in_time": _INSTANT,
        "timeframe": _DAILY,
        "open": _quote("1"),
        "high": _quote("1"),
        "low": _quote("1"),
        "close": _quote("1"),
        "volume": Quantity(Decimal("1")),
    }

    with pytest.raises(TypeError):
        FuturesOHLCVBar(**members, adjusted_close=_quote("1"))
    with pytest.raises(TypeError):
        FuturesOHLCVBar(**members, open_interest=Quantity(Decimal("1")))
