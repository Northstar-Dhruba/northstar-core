"""Tests for the economics of one individual option contract."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields
from decimal import Decimal
from pathlib import Path

import pytest

import northstar_core.options as options
from northstar_core.derivatives import ExpirationDate
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import Currency, ExchangeCode, Money, Symbol
from northstar_core.futures import (
    FuturesContract,
    FuturesContractEconomics,
    FuturesPointValue,
    FuturesProductReference,
)
from northstar_core.options import (
    InvalidOptionContractEconomicsError,
    OptionContract,
    OptionContractEconomics,
    OptionPointValue,
    OptionProductReference,
    OptionRight,
    OptionStrike,
)

_INR = Currency("INR")
_USD = Currency("USD")
_NSE = ExchangeCode("NSE")
_NIFTY = OptionProductReference(Symbol("NIFTY"), _NSE)
# Historically plausible lots: an expiry listed before a revision keeps 75, one after trades 65.
_DEC25 = ExpirationDate("2025-12-30")
_JAN26 = ExpirationDate("2026-01-27")
_K25000 = OptionStrike(Decimal("25000"))
_K25050 = OptionStrike(Decimal("25050"))
_LOT_75 = OptionPointValue(Decimal("75"), _INR)
_LOT_65 = OptionPointValue(Decimal("65"), _INR)


def _contract(
    expiration: ExpirationDate = _JAN26,
    strike: OptionStrike = _K25000,
    right: OptionRight = OptionRight.CALL,
    product: OptionProductReference = _NIFTY,
) -> OptionContract:
    return OptionContract(product, expiration, strike, right)


def _economics(contract: object = None, point_value: object = _LOT_65) -> OptionContractEconomics:
    return OptionContractEconomics(_contract() if contract is None else contract, point_value)


# ---------------------------------------------------------------------------
# Construction and shape
# ---------------------------------------------------------------------------


def test_economics_preserve_their_members() -> None:
    contract = _contract(_JAN26, _K25050, OptionRight.PUT)
    economics = OptionContractEconomics(contract, _LOT_65)

    assert economics.contract is contract
    assert economics.point_value is _LOT_65


def test_the_field_shape_is_exactly_contract_and_point_value() -> None:
    assert [field.name for field in fields(OptionContractEconomics)] == ["contract", "point_value"]
    assert OptionContractEconomics.__slots__ == ("contract", "point_value")


def test_the_exact_contract_identity_is_preserved() -> None:
    economics = _economics(_contract(_DEC25, _K25050, OptionRight.PUT), _LOT_75)

    assert economics.contract.natural_key == (_NIFTY, _DEC25, _K25050, OptionRight.PUT)


def test_the_settlement_currency_is_derived_from_the_point_value() -> None:
    assert _economics(point_value=_LOT_65).settlement_currency == _INR
    usd = OptionPointValue(Decimal("100"), _USD)
    assert _economics(point_value=usd).settlement_currency == _USD
    assert _economics().settlement_currency is _economics().point_value.currency


def test_the_settlement_currency_is_read_only() -> None:
    with pytest.raises(AttributeError):
        _economics().settlement_currency = _USD  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Every contract carries its own economics
# ---------------------------------------------------------------------------


def test_expiries_of_one_product_carry_their_own_point_values() -> None:
    december = _economics(_contract(expiration=_DEC25), _LOT_75)
    january = _economics(_contract(expiration=_JAN26), _LOT_65)

    assert december.point_value != january.point_value
    assert december != january
    assert len({december, january}) == 2


@pytest.mark.parametrize(
    "other",
    [
        _contract(expiration=_DEC25),
        _contract(strike=_K25050),
        _contract(right=OptionRight.PUT),
        _contract(product=OptionProductReference(Symbol("BANKNIFTY"), _NSE)),
        _contract(product=OptionProductReference(Symbol("NIFTY"), ExchangeCode("BSE"))),
    ],
    ids=["expiry", "strike", "right", "product", "exchange"],
)
def test_economics_for_any_other_contract_are_different_values(other: OptionContract) -> None:
    assert _economics(other) != _economics()
    assert len({_economics(other), _economics()}) == 2


def test_economics_differing_only_in_point_value_are_unequal() -> None:
    assert _economics(point_value=_LOT_65) != _economics(point_value=_LOT_75)


def test_equal_economics_compare_and_hash_equal() -> None:
    respelled = OptionPointValue(Decimal("65.000"), Currency("inr"))

    assert _economics(point_value=respelled) == _economics()
    assert hash(_economics(point_value=respelled)) == hash(_economics())


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_none_members_are_rejected() -> None:
    with pytest.raises(InvalidOptionContractEconomicsError, match="contract cannot be None"):
        OptionContractEconomics(None, _LOT_65)
    with pytest.raises(InvalidOptionContractEconomicsError, match="point value cannot be None"):
        OptionContractEconomics(_contract(), None)


@pytest.mark.parametrize(
    ("contract", "point_value", "message"),
    [
        ("NIFTY@NSE 2026-01-27 25000 CALL", _LOT_65, "must be an OptionContract value"),
        (_NIFTY, _LOT_65, "must be an OptionContract value"),
        (_contract(), Decimal("65"), "must be an OptionPointValue value"),
        (_contract(), Money(Decimal("65"), _INR), "must be an OptionPointValue value"),
    ],
    ids=["text-contract", "product-as-contract", "bare-decimal", "money"],
)
def test_wrong_member_types_are_rejected(
    contract: object, point_value: object, message: str
) -> None:
    with pytest.raises(InvalidOptionContractEconomicsError, match=message):
        OptionContractEconomics(contract, point_value)


def test_futures_types_are_rejected() -> None:
    futures_contract = FuturesContract(FuturesProductReference(Symbol("NIFTY"), _NSE), _JAN26)
    futures_point_value = FuturesPointValue(Decimal("65"), _INR)

    with pytest.raises(InvalidOptionContractEconomicsError, match="must be an OptionContract"):
        OptionContractEconomics(futures_contract, _LOT_65)
    with pytest.raises(InvalidOptionContractEconomicsError, match="must be an OptionPointValue"):
        OptionContractEconomics(_contract(), futures_point_value)


def test_the_error_is_a_validation_error() -> None:
    assert issubclass(InvalidOptionContractEconomicsError, ValidationError)
    with pytest.raises(ValidationError):
        OptionContractEconomics(None, _LOT_65)


# ---------------------------------------------------------------------------
# Value semantics
# ---------------------------------------------------------------------------


def test_economics_are_immutable() -> None:
    economics = _economics()

    with pytest.raises(FrozenInstanceError):
        economics.contract = _contract(strike=_K25050)  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        economics.point_value = _LOT_75  # type: ignore[misc]


def test_economics_are_not_ordered() -> None:
    with pytest.raises(TypeError):
        _ = _economics() < _economics(point_value=_LOT_75)  # type: ignore[operator]


def test_it_is_usable_as_a_dictionary_key() -> None:
    assert {_economics(): "configured"}[_economics()] == "configured"


def test_the_string_form_names_the_contract_and_keeps_the_unit() -> None:
    assert str(_economics()) == "NIFTY@NSE 2026-01-27 25000 CALL 65 INR/premium-point/contract"


def test_the_repr_is_deterministic() -> None:
    assert repr(_economics()) == (
        "OptionContractEconomics("
        "contract=OptionContract("
        "product=OptionProductReference("
        "product_code=Symbol(value='NIFTY'), "
        "exchange_code=ExchangeCode(value='NSE')"
        "), "
        "expiration_date=ExpirationDate(value='2026-01-27'), "
        "strike=OptionStrike(value=Decimal('25000')), "
        "right=<OptionRight.CALL: 'CALL'>"
        "), "
        "point_value=OptionPointValue(amount=Decimal('65'), currency=Currency(value='INR'))"
        ")"
    )


# ---------------------------------------------------------------------------
# Scope
# ---------------------------------------------------------------------------


def test_option_economics_are_never_futures_economics() -> None:
    futures = FuturesContractEconomics(
        FuturesContract(FuturesProductReference(Symbol("NIFTY"), _NSE), _JAN26),
        FuturesPointValue(Decimal("65"), _INR),
    )

    assert _economics() != futures
    assert futures != _economics()
    assert not isinstance(_economics(), FuturesContractEconomics)


def test_no_lot_size_or_duplicate_currency_is_stored() -> None:
    economics = _economics()

    for absent in (
        "lot_size",
        "lot",
        "multiplier",
        "contract_multiplier",
        "currency",
        "premium",
        "contracts",
        "contract_count",
        "margin",
        "fees",
        "natural_key",
    ):
        assert not hasattr(economics, absent)


_MODULE = Path(options.__file__).parent / "value_objects" / "option_contract_economics.py"


def test_the_module_depends_only_on_foundation_and_options() -> None:
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
        if name.startswith("northstar_core"):
            assert name.startswith(("northstar_core.foundation", "northstar_core.options")), name


def test_the_module_defines_no_calculation_or_lot_concept() -> None:
    tree = ast.parse(_MODULE.read_text(encoding="utf-8"))
    functions = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    classes = {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}

    for forbidden in ("pnl", "profit", "notional", "margin", "tick", "money", "__mul__", "lot"):
        assert not [name for name in functions if forbidden in name.lower()]
    assert classes == {"OptionContractEconomics", "InvalidOptionContractEconomicsError"}


def test_the_contract_economics_are_exported() -> None:
    assert "OptionContractEconomics" in options.__all__
    assert "InvalidOptionContractEconomicsError" in options.__all__
