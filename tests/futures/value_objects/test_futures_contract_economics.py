"""Tests for the economics of one individual futures contract."""

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
    FuturesContractEconomics,
    FuturesPointValue,
    FuturesProductEconomics,
    FuturesProductReference,
    InvalidFuturesContractEconomicsError,
)

_INR = Currency("INR")
_USD = Currency("USD")
_NIFTY = FuturesProductReference(Symbol("NIFTY"), ExchangeCode("NSE"))
_ES = FuturesProductReference(Symbol("ES"), ExchangeCode("CME"))
# Historically plausible fixtures only: NOV25 and DEC25 traded at a lot of 75, JAN26 at 65.
_NOV25 = FuturesContract(_NIFTY, ExpirationDate("2025-11-25"))
_JAN26 = FuturesContract(_NIFTY, ExpirationDate("2026-01-27"))
_LOT_75 = FuturesPointValue(Decimal("75"), _INR)
_LOT_65 = FuturesPointValue(Decimal("65"), _INR)


def _economics(
    contract: object = _NOV25, point_value: object = _LOT_75
) -> FuturesContractEconomics:
    return FuturesContractEconomics(contract, point_value)


def test_economics_preserve_their_members() -> None:
    economics = _economics()

    assert economics.contract == _NOV25
    assert economics.point_value == _LOT_75
    assert economics.settlement_currency == _INR


def test_the_field_shape_is_exactly_contract_and_point_value() -> None:
    """Product, exchange and expiration come from the contract, never stored beside it."""
    assert [field.name for field in fields(FuturesContractEconomics)] == [
        "contract",
        "point_value",
    ]


def test_the_settlement_currency_is_owned_by_the_point_value() -> None:
    economics = _economics()

    assert economics.settlement_currency is economics.point_value.currency
    assert "settlement_currency" not in FuturesContractEconomics.__slots__


def test_expiries_of_one_product_carry_their_own_point_values() -> None:
    """The load-bearing fact: one product, two concurrent expiries, two point values."""
    november = _economics(_NOV25, _LOT_75)
    january = _economics(_JAN26, _LOT_65)
    lookup = {november.contract: november, january.contract: january}

    assert november.contract.product == january.contract.product
    assert november != january
    assert lookup[_NOV25].point_value.amount == Decimal("75")
    assert lookup[_JAN26].point_value.amount == Decimal("65")
    assert _NIFTY not in lookup


@pytest.mark.parametrize(
    "other",
    [
        _economics(_JAN26),
        _economics(FuturesContract(_ES, ExpirationDate("2025-11-25"))),
        _economics(
            FuturesContract(
                FuturesProductReference(Symbol("NIFTY"), ExchangeCode("BSE")),
                ExpirationDate("2025-11-25"),
            )
        ),
        _economics(point_value=_LOT_65),
        _economics(point_value=FuturesPointValue(Decimal("75"), _USD)),
    ],
    ids=["expiration", "product", "exchange", "amount", "currency"],
)
def test_economics_differing_in_any_fact_are_not_equal(other: FuturesContractEconomics) -> None:
    assert other != _economics()


def test_equal_economics_compare_and_hash_equal() -> None:
    rebuilt = _economics(
        FuturesContract(
            FuturesProductReference(Symbol("nifty"), ExchangeCode("nse")),
            ExpirationDate("2025-11-25"),
        ),
        FuturesPointValue(Decimal("75.000"), Currency("inr")),
    )

    assert rebuilt == _economics()
    assert hash(rebuilt) == hash(_economics())


def test_contract_economics_are_not_product_economics() -> None:
    product = FuturesProductEconomics(_NIFTY, _LOT_75)

    assert _economics() != product
    assert not isinstance(product, FuturesContractEconomics)


@pytest.mark.parametrize(
    ("contract", "point_value", "message"),
    [
        (None, _LOT_75, "contract cannot be None"),
        ("NIFTY@NSE 2025-11-25", _LOT_75, "must be a FuturesContract"),
        (_NIFTY, _LOT_75, "must be a FuturesContract"),
        (_NOV25, None, "point value cannot be None"),
        (_NOV25, Decimal("75"), "must be a FuturesPointValue"),
        (_NOV25, Money(Decimal("75"), _INR), "must be a FuturesPointValue"),
        (_NOV25, FuturesProductEconomics(_NIFTY, _LOT_75), "must be a FuturesPointValue"),
    ],
)
def test_wrong_member_types_are_rejected(
    contract: object, point_value: object, message: str
) -> None:
    with pytest.raises(InvalidFuturesContractEconomicsError, match=message):
        FuturesContractEconomics(contract, point_value)


def test_the_error_is_a_validation_error() -> None:
    assert issubclass(InvalidFuturesContractEconomicsError, ValidationError)


def test_economics_are_immutable() -> None:
    economics = _economics()

    with pytest.raises(FrozenInstanceError):
        economics.point_value = _LOT_65  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        economics.contract = _JAN26  # type: ignore[misc]


def test_the_string_form_names_the_contract_and_keeps_the_unit() -> None:
    assert str(_economics()) == "NIFTY@NSE 2025-11-25 75 INR/point/contract"


def test_the_repr_is_deterministic() -> None:
    assert repr(_economics()) == (
        f"FuturesContractEconomics(contract={_NOV25!r}, point_value={_LOT_75!r})"
    )


# ---------------------------------------------------------------------------
# Boundaries
# ---------------------------------------------------------------------------

_MODULE = Path(futures.__file__).parent / "value_objects" / "futures_contract_economics.py"


def test_the_module_depends_only_on_foundation_and_futures() -> None:
    tree = ast.parse(_MODULE.read_text(encoding="utf-8"))
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
            "requests",
            "time",
            "datetime",
        }
        if name.startswith("northstar_core"):
            assert name.startswith(("northstar_core.foundation", "northstar_core.futures")), name


def test_the_module_defines_no_calculation_or_lot_concept() -> None:
    tree = ast.parse(_MODULE.read_text(encoding="utf-8"))
    functions = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    classes = {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}

    for forbidden in ("pnl", "profit", "notional", "margin", "tick", "money", "__mul__", "lot"):
        assert not [name for name in functions if forbidden in name.lower()]
    assert classes == {"FuturesContractEconomics", "InvalidFuturesContractEconomicsError"}


def test_the_contract_economics_are_exported() -> None:
    assert "FuturesContractEconomics" in futures.__all__
    assert "InvalidFuturesContractEconomicsError" in futures.__all__
