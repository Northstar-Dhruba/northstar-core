"""Tests for the economics of one exchange-defined futures product."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields
from decimal import Decimal
from pathlib import Path

import pytest

import northstar_core.futures as futures
from northstar_core.derivatives import ExpirationDate
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import Currency, ExchangeCode, Money, Symbol
from northstar_core.futures import (
    FuturesContract,
    FuturesPointValue,
    FuturesProductEconomics,
    FuturesProductReference,
    InvalidFuturesProductEconomicsError,
)

_USD = Currency("USD")
_EUR = Currency("EUR")
_ES = FuturesProductReference(Symbol("ES"), ExchangeCode("CME"))
_MES = FuturesProductReference(Symbol("MES"), ExchangeCode("CME"))
_ES_ELSEWHERE = FuturesProductReference(Symbol("ES"), ExchangeCode("CBOT"))
_POINT = FuturesPointValue(Decimal("50"), _USD)


def _economics(reference: object = _ES, point_value: object = _POINT) -> FuturesProductEconomics:
    return FuturesProductEconomics(reference, point_value)


def test_economics_preserve_their_members() -> None:
    economics = _economics()

    assert economics.reference == _ES
    assert economics.point_value == _POINT
    assert economics.settlement_currency == _USD


def test_the_field_shape_is_exactly_reference_and_point_value() -> None:
    """No expiry, underlying, tick, margin, notional or second currency."""
    assert [field.name for field in fields(FuturesProductEconomics)] == [
        "reference",
        "point_value",
    ]


def test_the_settlement_currency_is_owned_by_the_point_value() -> None:
    economics = _economics(point_value=FuturesPointValue(Decimal("5"), _EUR))

    assert economics.settlement_currency is economics.point_value.currency
    assert "settlement_currency" not in FuturesProductEconomics.__slots__


def test_every_expiry_of_a_product_shares_one_economics_value() -> None:
    product = FuturesProductReference(Symbol("ES"), ExchangeCode("CME"))
    december = FuturesContract(product, ExpirationDate("2026-12-18"))
    march = FuturesContract(product, ExpirationDate("2027-03-19"))
    economics = _economics(product)

    assert december != march
    assert economics.reference == december.product == march.product
    assert {december.product: economics}[march.product] is economics


@pytest.mark.parametrize(
    "other",
    [
        _economics(_MES),
        _economics(_ES_ELSEWHERE),
        _economics(point_value=FuturesPointValue(Decimal("50.5"), _USD)),
        _economics(point_value=FuturesPointValue(Decimal("50"), _EUR)),
    ],
    ids=["product", "exchange", "amount", "currency"],
)
def test_economics_differing_in_any_fact_are_not_equal(other: FuturesProductEconomics) -> None:
    assert other != _economics()


def test_equal_economics_compare_and_hash_equal() -> None:
    rebuilt = _economics(
        FuturesProductReference(Symbol("ES"), ExchangeCode("CME")),
        FuturesPointValue(Decimal("50.000"), Currency("usd")),
    )

    assert rebuilt == _economics()
    assert hash(rebuilt) == hash(_economics())


@pytest.mark.parametrize(
    ("reference", "point_value", "message"),
    [
        (None, _POINT, "reference cannot be None"),
        ("ES@CME", _POINT, "must be a FuturesProductReference"),
        (
            FuturesContract(_ES, ExpirationDate("2026-12-18")),
            _POINT,
            "must be a FuturesProductReference",
        ),
        (_ES, None, "point value cannot be None"),
        (_ES, Decimal("50"), "must be a FuturesPointValue"),
        (_ES, Money(Decimal("50"), _USD), "must be a FuturesPointValue"),
    ],
)
def test_wrong_member_types_are_rejected(
    reference: object, point_value: object, message: str
) -> None:
    with pytest.raises(InvalidFuturesProductEconomicsError, match=message):
        FuturesProductEconomics(reference, point_value)


def test_the_error_is_a_validation_error() -> None:
    assert issubclass(InvalidFuturesProductEconomicsError, ValidationError)


def test_economics_are_immutable() -> None:
    economics = _economics()

    with pytest.raises(FrozenInstanceError):
        economics.point_value = FuturesPointValue(Decimal("1"), _USD)  # type: ignore[misc]


def test_the_string_form_keeps_the_unit() -> None:
    assert str(_economics()) == "ES@CME 50 USD/point/contract"


# ---------------------------------------------------------------------------
# Boundaries
# ---------------------------------------------------------------------------

_ECONOMICS_MODULES = ("futures_point_value.py", "futures_product_economics.py")
_VALUE_OBJECTS = Path(futures.__file__).parent / "value_objects"


@pytest.mark.parametrize("filename", _ECONOMICS_MODULES)
def test_the_economics_modules_depend_only_on_foundation_and_futures(filename: str) -> None:
    tree = ast.parse((_VALUE_OBJECTS / filename).read_text(encoding="utf-8"))
    modules = {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }

    for name in modules:
        assert name.split(".")[0] not in {
            "northstar_application",
            "northstar_infrastructure",
            "sqlite3",
            "databento",
            "requests",
            "urllib",
            "socket",
            "time",
            "datetime",
        }
        if name.startswith("northstar_core"):
            assert name.startswith(("northstar_core.foundation", "northstar_core.futures")), name


@pytest.mark.parametrize("filename", _ECONOMICS_MODULES)
def test_the_economics_modules_define_no_calculation(filename: str) -> None:
    tree = ast.parse((_VALUE_OBJECTS / filename).read_text(encoding="utf-8"))
    functions = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}

    for forbidden in ("pnl", "profit", "notional", "margin", "tick", "money", "__mul__"):
        assert not [name for name in functions if forbidden in name.lower()]


def test_the_economics_are_exported_and_the_helpers_are_not() -> None:
    for name in (
        "FuturesPointValue",
        "FuturesProductEconomics",
        "InvalidFuturesPointValueError",
        "InvalidFuturesProductEconomicsError",
    ):
        assert name in futures.__all__
    assert not hasattr(futures, "canonical_decimal")
    assert "TickSize" not in futures.__all__
