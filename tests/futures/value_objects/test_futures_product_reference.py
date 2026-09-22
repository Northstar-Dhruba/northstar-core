"""Tests for the exchange-defined futures product reference."""

from __future__ import annotations

import pytest

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import ExchangeCode, Symbol
from northstar_core.futures import (
    FuturesProductReference,
    InvalidFuturesProductReferenceError,
)

_CME = ExchangeCode("CME")
_NYMEX = ExchangeCode("NYMEX")
_CBOT = ExchangeCode("CBOT")


def _product(code: str = "ES", exchange: ExchangeCode = _CME) -> FuturesProductReference:
    return FuturesProductReference(Symbol(code), exchange)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_a_product_preserves_its_members() -> None:
    product = _product("ES", _CME)

    assert product.product_code == Symbol("ES")
    assert product.exchange_code == _CME


@pytest.mark.parametrize(("code", "exchange"), [("ES", _CME), ("MES", _CME), ("CL", _NYMEX)])
def test_known_products_are_constructible(code: str, exchange: ExchangeCode) -> None:
    assert _product(code, exchange).product_code == Symbol(code)


def test_the_product_code_is_normalized_by_symbol() -> None:
    assert _product("es").product_code == Symbol("ES")


# ---------------------------------------------------------------------------
# Type validation
# ---------------------------------------------------------------------------


def test_none_members_are_rejected() -> None:
    with pytest.raises(InvalidFuturesProductReferenceError, match="product code cannot be None"):
        FuturesProductReference(None, _CME)
    with pytest.raises(InvalidFuturesProductReferenceError, match="exchange code cannot be None"):
        FuturesProductReference(Symbol("ES"), None)


def test_wrong_member_types_are_rejected() -> None:
    with pytest.raises(InvalidFuturesProductReferenceError, match="must be a Symbol value"):
        FuturesProductReference("ES", _CME)
    with pytest.raises(InvalidFuturesProductReferenceError, match="must be an ExchangeCode value"):
        FuturesProductReference(Symbol("ES"), "CME")


def test_an_exchange_code_is_not_accepted_as_a_product_code() -> None:
    with pytest.raises(InvalidFuturesProductReferenceError, match="must be a Symbol value"):
        FuturesProductReference(_CME, _CME)


def test_the_error_is_a_validation_error() -> None:
    assert issubclass(InvalidFuturesProductReferenceError, ValidationError)
    with pytest.raises(ValidationError):
        FuturesProductReference(None, _CME)


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


def test_equality_is_by_value() -> None:
    assert _product("ES", _CME) == _product("ES", _CME)
    assert _product("ES", _CME) != _product("MES", _CME)


def test_the_same_product_code_on_different_exchanges_is_a_different_product() -> None:
    """A product is an exchange's specification; the code alone is not unique."""
    assert _product("ES", _CME) != _product("ES", _CBOT)


def test_standard_and_micro_products_are_distinct() -> None:
    assert _product("ES", _CME) != _product("MES", _CME)
    assert _product("CL", _NYMEX) != _product("QM", _NYMEX)


def test_hashing_follows_equality() -> None:
    assert hash(_product("ES", _CME)) == hash(_product("ES", _CME))
    assert len({_product("ES", _CME), _product("ES", _CME), _product("MES", _CME)}) == 2


def test_it_is_usable_as_a_dictionary_key() -> None:
    assert {_product("ES", _CME): "E-mini"}[_product("ES", _CME)] == "E-mini"


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------


def test_products_order_by_code_then_exchange() -> None:
    assert _product("ES", _CME) < _product("MES", _CME)
    assert _product("ES", _CBOT) < _product("ES", _CME)


def test_sorting_a_product_set_is_deterministic() -> None:
    products = (
        _product("MES", _CME),
        _product("CL", _NYMEX),
        _product("ES", _CME),
        _product("ES", _CBOT),
    )

    assert [str(product) for product in sorted(products)] == [
        "CL@NYMEX",
        "ES@CBOT",
        "ES@CME",
        "MES@CME",
    ]


# ---------------------------------------------------------------------------
# Value semantics and scope
# ---------------------------------------------------------------------------


def test_the_reference_is_immutable() -> None:
    product = _product()

    with pytest.raises(AttributeError):
        product.product_code = Symbol("MES")
    with pytest.raises(AttributeError):
        product.exchange_code = _NYMEX


def test_string_and_repr_forms() -> None:
    product = _product("ES", _CME)

    assert str(product) == "ES@CME"
    assert repr(product) == (
        "FuturesProductReference(product_code=Symbol(value='ES'), "
        "exchange_code=ExchangeCode(value='CME'))"
    )


def test_the_reference_carries_no_specification_detail() -> None:
    """Multiplier, tick and underlying belong to a specification, not a reference."""
    product = _product()

    for absent in (
        "underlying",
        "underlying_reference",
        "multiplier",
        "contract_multiplier",
        "tick_size",
        "currency",
        "trading_hours",
        "listing_reference",
    ):
        assert not hasattr(product, absent)
