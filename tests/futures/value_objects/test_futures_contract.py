"""Tests for the identity of one individual futures contract."""

from __future__ import annotations

import pytest

from northstar_core.derivatives import ExpirationDate
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import ExchangeCode, Symbol
from northstar_core.futures import (
    FuturesContract,
    FuturesProductReference,
    InvalidFuturesContractError,
)

_CME = ExchangeCode("CME")
_NYMEX = ExchangeCode("NYMEX")
_MARCH = ExpirationDate("2026-03-20")
_JUNE = ExpirationDate("2026-06-19")

_ES = FuturesProductReference(Symbol("ES"), _CME)
_MES = FuturesProductReference(Symbol("MES"), _CME)
_CL = FuturesProductReference(Symbol("CL"), _NYMEX)


def _contract(
    product: FuturesProductReference = _ES, expiration: ExpirationDate = _MARCH
) -> FuturesContract:
    return FuturesContract(product=product, expiration_date=expiration)


# ---------------------------------------------------------------------------
# The regression this identity exists to prevent
# ---------------------------------------------------------------------------


def test_standard_and_micro_contracts_at_one_expiry_are_distinct() -> None:
    """ES and MES share an underlying, an exchange and an expiry, yet differ.

    An identity keyed on the economic underlying instead of the product would
    collapse these two genuinely different instruments into one.
    """
    standard = _contract(_ES, _MARCH)
    micro = _contract(_MES, _MARCH)

    assert standard != micro
    assert standard.natural_key != micro.natural_key
    assert hash(standard) != hash(micro)
    assert len({standard, micro}) == 2
    assert standard.expiration_date == micro.expiration_date
    assert standard.product.exchange_code == micro.product.exchange_code


def test_the_same_product_at_different_expiries_is_distinct() -> None:
    assert _contract(_ES, _MARCH) != _contract(_ES, _JUNE)
    assert len({_contract(_ES, _MARCH), _contract(_ES, _JUNE)}) == 2


def test_the_same_product_code_on_different_exchanges_is_distinct() -> None:
    elsewhere = FuturesProductReference(Symbol("ES"), ExchangeCode("CBOT"))

    assert _contract(_ES, _MARCH) != _contract(elsewhere, _MARCH)


def test_identical_product_and_expiration_are_the_same_contract() -> None:
    assert _contract(_ES, _MARCH) == _contract(_ES, _MARCH)
    assert hash(_contract(_ES, _MARCH)) == hash(_contract(_ES, _MARCH))


def test_a_micro_series_stays_separate_across_expiries() -> None:
    contracts = {
        _contract(_ES, _MARCH),
        _contract(_ES, _JUNE),
        _contract(_MES, _MARCH),
        _contract(_MES, _JUNE),
    }

    assert len(contracts) == 4


# ---------------------------------------------------------------------------
# Construction and validation
# ---------------------------------------------------------------------------


def test_a_contract_preserves_its_members() -> None:
    contract = _contract(_CL, _JUNE)

    assert contract.product == _CL
    assert contract.expiration_date == _JUNE


def test_none_members_are_rejected() -> None:
    with pytest.raises(InvalidFuturesContractError, match="product cannot be None"):
        FuturesContract(None, _MARCH)
    with pytest.raises(InvalidFuturesContractError, match="expiration date cannot be None"):
        FuturesContract(_ES, None)


def test_wrong_member_types_are_rejected() -> None:
    with pytest.raises(InvalidFuturesContractError, match="must be a FuturesProductReference"):
        FuturesContract("ES@CME", _MARCH)
    with pytest.raises(InvalidFuturesContractError, match="must be an ExpirationDate"):
        FuturesContract(_ES, "2026-03-20")


def test_a_symbol_is_not_accepted_as_a_product() -> None:
    with pytest.raises(InvalidFuturesContractError, match="must be a FuturesProductReference"):
        FuturesContract(Symbol("ESH26"), _MARCH)


def test_the_error_is_a_validation_error() -> None:
    assert issubclass(InvalidFuturesContractError, ValidationError)
    with pytest.raises(ValidationError):
        FuturesContract(None, _MARCH)


# ---------------------------------------------------------------------------
# Natural key
# ---------------------------------------------------------------------------


def test_the_natural_key_is_exactly_product_and_expiration() -> None:
    contract = _contract(_ES, _MARCH)

    assert contract.natural_key == (_ES, _MARCH)
    assert len(contract.natural_key) == 2
    assert isinstance(contract.natural_key, tuple)


def test_the_natural_key_distinguishes_every_identity_component() -> None:
    assert _contract(_ES, _MARCH).natural_key != _contract(_MES, _MARCH).natural_key
    assert _contract(_ES, _MARCH).natural_key != _contract(_ES, _JUNE).natural_key


def test_equal_contracts_share_one_natural_key() -> None:
    assert _contract(_ES, _MARCH).natural_key == _contract(_ES, _MARCH).natural_key


def test_the_natural_key_is_derived_not_stored() -> None:
    """A surrogate identity would be a second source of truth that could disagree."""
    assert "natural_key" not in FuturesContract.__slots__
    assert set(FuturesContract.__slots__) == {"product", "expiration_date"}


def test_the_natural_key_is_read_only() -> None:
    contract = _contract()

    with pytest.raises(AttributeError):
        contract.natural_key = ()


# ---------------------------------------------------------------------------
# Value semantics and scope
# ---------------------------------------------------------------------------


def test_the_contract_is_immutable() -> None:
    contract = _contract()

    with pytest.raises(AttributeError):
        contract.product = _MES
    with pytest.raises(AttributeError):
        contract.expiration_date = _JUNE


def test_it_is_usable_as_a_dictionary_key() -> None:
    holdings = {_contract(_ES, _MARCH): 3, _contract(_MES, _MARCH): 7}

    assert holdings[_contract(_ES, _MARCH)] == 3
    assert holdings[_contract(_MES, _MARCH)] == 7


def test_string_and_repr_forms() -> None:
    contract = _contract(_ES, _MARCH)

    assert str(contract) == "ES@CME 2026-03-20"
    assert repr(contract).startswith("FuturesContract(product=FuturesProductReference(")


def test_the_contract_carries_no_surrogate_identity() -> None:
    contract = _contract()

    for absent in ("identity", "contract_identity", "futures_contract_identity"):
        assert not hasattr(contract, absent)


def test_the_contract_carries_no_deferred_concepts() -> None:
    contract = _contract()

    for absent in (
        "symbol",
        "provider_symbol",
        "listing_reference",
        "underlying",
        "underlying_reference",
        "multiplier",
        "contract_multiplier",
        "tick_size",
        "contract_month",
        "last_trading_day",
        "settlement_instant",
        "is_continuous",
        "roll",
    ):
        assert not hasattr(contract, absent)
