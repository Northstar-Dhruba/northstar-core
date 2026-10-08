"""Tests for the identity association of one exchange-defined option product."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import ExchangeCode, Symbol
from northstar_core.futures import FuturesProductReference
from northstar_core.options import InvalidOptionProductReferenceError, OptionProductReference

_NSE = ExchangeCode("NSE")
_BSE = ExchangeCode("BSE")


def _product(code: str = "NIFTY", exchange: ExchangeCode = _NSE) -> OptionProductReference:
    return OptionProductReference(product_code=Symbol(code), exchange_code=exchange)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_a_product_preserves_its_members() -> None:
    product = _product("NIFTY", _NSE)

    assert product.product_code == Symbol("NIFTY")
    assert product.exchange_code == _NSE


def test_the_field_shape_is_exactly_product_code_and_exchange_code() -> None:
    assert OptionProductReference.__slots__ == ("product_code", "exchange_code")


def test_the_product_code_is_normalized_by_symbol() -> None:
    assert _product(" nifty ") == _product("NIFTY")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_none_members_are_rejected() -> None:
    with pytest.raises(InvalidOptionProductReferenceError, match="product code cannot be None"):
        OptionProductReference(None, _NSE)
    with pytest.raises(InvalidOptionProductReferenceError, match="exchange code cannot be None"):
        OptionProductReference(Symbol("NIFTY"), None)


def test_wrong_member_types_are_rejected() -> None:
    with pytest.raises(InvalidOptionProductReferenceError, match="must be a Symbol value"):
        OptionProductReference("NIFTY", _NSE)
    with pytest.raises(InvalidOptionProductReferenceError, match="must be an ExchangeCode value"):
        OptionProductReference(Symbol("NIFTY"), "NSE")


def test_an_exchange_code_is_not_accepted_as_a_product_code() -> None:
    with pytest.raises(InvalidOptionProductReferenceError, match="must be a Symbol value"):
        OptionProductReference(ExchangeCode("NIFTY"), _NSE)


def test_the_error_is_a_validation_error() -> None:
    assert issubclass(InvalidOptionProductReferenceError, ValidationError)
    with pytest.raises(ValidationError):
        OptionProductReference(None, _NSE)


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


def test_equality_is_by_value() -> None:
    assert _product("NIFTY", _NSE) == _product("NIFTY", _NSE)
    assert hash(_product("NIFTY", _NSE)) == hash(_product("NIFTY", _NSE))


def test_different_products_on_one_exchange_are_distinct() -> None:
    assert _product("NIFTY", _NSE) != _product("BANKNIFTY", _NSE)


def test_the_same_product_code_on_different_exchanges_is_a_different_product() -> None:
    assert _product("NIFTY", _NSE) != _product("NIFTY", _BSE)


def test_it_is_usable_as_a_dictionary_key() -> None:
    products = {_product("NIFTY"): "index", _product("BANKNIFTY"): "bank"}

    assert products[_product("NIFTY")] == "index"


def test_an_option_product_is_never_the_futures_product_of_the_same_name() -> None:
    """NSE lists NIFTY futures and NIFTY options under one code; they stay distinct."""
    option = _product("NIFTY", _NSE)
    futures = FuturesProductReference(Symbol("NIFTY"), _NSE)

    assert str(option) == str(futures) == "NIFTY@NSE"
    assert option != futures
    assert futures != option
    assert not isinstance(option, FuturesProductReference)
    assert not isinstance(futures, OptionProductReference)
    assert len({option, futures}) == 2


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------


def test_products_order_by_code_then_exchange() -> None:
    assert _product("BANKNIFTY", _NSE) < _product("NIFTY", _BSE)
    assert _product("NIFTY", _BSE) < _product("NIFTY", _NSE)


def test_sorting_a_product_set_is_deterministic() -> None:
    products = {_product("NIFTY", _NSE), _product("BANKNIFTY", _NSE), _product("NIFTY", _BSE)}

    assert [str(product) for product in sorted(products)] == [
        "BANKNIFTY@NSE",
        "NIFTY@BSE",
        "NIFTY@NSE",
    ]


# ---------------------------------------------------------------------------
# Value semantics and scope
# ---------------------------------------------------------------------------


def test_the_reference_is_immutable() -> None:
    product = _product()

    with pytest.raises(FrozenInstanceError):
        product.product_code = Symbol("BANKNIFTY")  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        product.exchange_code = _BSE  # type: ignore[misc]


def test_string_and_repr_forms() -> None:
    product = _product("NIFTY", _NSE)

    assert str(product) == "NIFTY@NSE"
    assert repr(product) == (
        "OptionProductReference("
        "product_code=Symbol(value='NIFTY'), "
        "exchange_code=ExchangeCode(value='NSE')"
        ")"
    )


def test_the_reference_carries_no_specification_detail() -> None:
    product = _product()

    for absent in (
        "underlying",
        "lot_size",
        "multiplier",
        "strike_interval",
        "tick_size",
        "exercise_style",
        "settlement_method",
        "instrument_key",
        "trading_symbol",
    ):
        assert not hasattr(product, absent)
