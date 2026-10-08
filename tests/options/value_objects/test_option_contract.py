"""Tests for the identity of one individual option contract."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from northstar_core.derivatives import ExpirationDate
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import ExchangeCode, Symbol
from northstar_core.futures import FuturesContract, FuturesProductReference
from northstar_core.options import (
    InvalidOptionContractError,
    OptionContract,
    OptionProductReference,
    OptionRight,
    OptionStrike,
)

_NSE = ExchangeCode("NSE")
_NIFTY = OptionProductReference(Symbol("NIFTY"), _NSE)
_BANKNIFTY = OptionProductReference(Symbol("BANKNIFTY"), _NSE)

_WEEKLY = ExpirationDate("2026-10-20")
_MONTHLY = ExpirationDate("2026-10-27")

_K25000 = OptionStrike(Decimal("25000"))
_K25050 = OptionStrike(Decimal("25050"))


def _contract(
    product: OptionProductReference = _NIFTY,
    expiration: ExpirationDate = _MONTHLY,
    strike: OptionStrike = _K25000,
    right: OptionRight = OptionRight.CALL,
) -> OptionContract:
    return OptionContract(product=product, expiration_date=expiration, strike=strike, right=right)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_a_contract_preserves_its_members() -> None:
    contract = _contract(_NIFTY, _MONTHLY, _K25000, OptionRight.PUT)

    assert contract.product == _NIFTY
    assert contract.expiration_date == _MONTHLY
    assert contract.strike == _K25000
    assert contract.right is OptionRight.PUT


def test_the_field_shape_is_exactly_four_identity_components() -> None:
    assert OptionContract.__slots__ == ("product", "expiration_date", "strike", "right")


# ---------------------------------------------------------------------------
# Identity: every component distinguishes
# ---------------------------------------------------------------------------


def test_identical_components_are_the_same_contract() -> None:
    assert _contract() == _contract()
    assert hash(_contract()) == hash(_contract())


def test_contracts_differing_only_by_expiry_are_distinct() -> None:
    """A weekly and a monthly expiry of one product are told apart by date alone."""
    weekly = _contract(expiration=_WEEKLY)
    monthly = _contract(expiration=_MONTHLY)

    assert weekly != monthly
    assert weekly.natural_key != monthly.natural_key
    assert len({weekly, monthly}) == 2


def test_contracts_differing_only_by_strike_are_distinct() -> None:
    assert _contract(strike=_K25000) != _contract(strike=_K25050)
    assert len({_contract(strike=_K25000), _contract(strike=_K25050)}) == 2


def test_contracts_differing_only_by_right_are_distinct() -> None:
    call = _contract(right=OptionRight.CALL)
    put = _contract(right=OptionRight.PUT)

    assert call != put
    assert len({call, put}) == 2


def test_contracts_differing_only_by_product_are_distinct() -> None:
    assert _contract(product=_NIFTY) != _contract(product=_BANKNIFTY)
    assert len({_contract(product=_NIFTY), _contract(product=_BANKNIFTY)}) == 2


def test_contracts_differing_only_by_exchange_are_distinct() -> None:
    elsewhere = OptionProductReference(Symbol("NIFTY"), ExchangeCode("BSE"))

    assert _contract(product=_NIFTY) != _contract(product=elsewhere)


def test_equivalent_strike_spellings_are_one_contract() -> None:
    respelled = _contract(strike=OptionStrike(Decimal("2.5E+4")))

    assert respelled == _contract(strike=_K25000)
    assert hash(respelled) == hash(_contract(strike=_K25000))


def test_a_small_chain_keeps_every_contract_separate() -> None:
    contracts = {
        _contract(product, expiration, strike, right)
        for product in (_NIFTY, _BANKNIFTY)
        for expiration in (_WEEKLY, _MONTHLY)
        for strike in (_K25000, _K25050)
        for right in OptionRight
    }

    assert len(contracts) == 16


def test_it_is_usable_as_a_dictionary_key() -> None:
    holdings = {_contract(right=OptionRight.CALL): 2, _contract(right=OptionRight.PUT): 5}

    assert holdings[_contract(right=OptionRight.CALL)] == 2
    assert holdings[_contract(right=OptionRight.PUT)] == 5


def test_an_option_contract_is_never_a_futures_contract() -> None:
    futures = FuturesContract(FuturesProductReference(Symbol("NIFTY"), _NSE), _MONTHLY)
    option = _contract()

    assert option != futures
    assert not isinstance(option, FuturesContract)
    assert len({option, futures}) == 2


# ---------------------------------------------------------------------------
# Natural key
# ---------------------------------------------------------------------------


def test_the_natural_key_is_exactly_product_expiry_strike_and_right() -> None:
    contract = _contract(_NIFTY, _MONTHLY, _K25000, OptionRight.CALL)

    assert contract.natural_key == (_NIFTY, _MONTHLY, _K25000, OptionRight.CALL)
    assert isinstance(contract.natural_key, tuple)
    assert len(contract.natural_key) == 4


def test_the_natural_key_component_types_are_exact() -> None:
    product, expiration, strike, right = _contract().natural_key

    assert type(product) is OptionProductReference
    assert type(expiration) is ExpirationDate
    assert type(strike) is OptionStrike
    assert type(right) is OptionRight


def test_equal_contracts_share_one_natural_key() -> None:
    assert _contract().natural_key == _contract().natural_key


def test_natural_keys_order_by_product_then_expiry_then_strike_then_right() -> None:
    contracts = [
        _contract(_NIFTY, _MONTHLY, _K25000, OptionRight.PUT),
        _contract(_NIFTY, _WEEKLY, _K25050, OptionRight.CALL),
        _contract(_NIFTY, _MONTHLY, _K25000, OptionRight.CALL),
        _contract(_BANKNIFTY, _MONTHLY, _K25050, OptionRight.PUT),
        _contract(_NIFTY, _WEEKLY, _K25000, OptionRight.PUT),
    ]

    ordered = sorted(contracts, key=lambda contract: contract.natural_key)

    assert [str(contract) for contract in ordered] == [
        "BANKNIFTY@NSE 2026-10-27 25050 PUT",
        "NIFTY@NSE 2026-10-20 25000 PUT",
        "NIFTY@NSE 2026-10-20 25050 CALL",
        "NIFTY@NSE 2026-10-27 25000 CALL",
        "NIFTY@NSE 2026-10-27 25000 PUT",
    ]


def test_strikes_in_the_natural_key_order_numerically_not_textually() -> None:
    low = _contract(strike=OptionStrike(Decimal("9950")))
    high = _contract(strike=OptionStrike(Decimal("25000")))

    assert low.natural_key < high.natural_key


def test_the_natural_key_is_derived_not_stored() -> None:
    """A surrogate identity would be a second source of truth that could disagree."""
    assert "natural_key" not in OptionContract.__slots__


def test_the_natural_key_is_read_only() -> None:
    contract = _contract()

    with pytest.raises(AttributeError):
        contract.natural_key = ()  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_none_members_are_rejected() -> None:
    with pytest.raises(InvalidOptionContractError, match="product cannot be None"):
        OptionContract(None, _MONTHLY, _K25000, OptionRight.CALL)
    with pytest.raises(InvalidOptionContractError, match="expiration date cannot be None"):
        OptionContract(_NIFTY, None, _K25000, OptionRight.CALL)
    with pytest.raises(InvalidOptionContractError, match="strike cannot be None"):
        OptionContract(_NIFTY, _MONTHLY, None, OptionRight.CALL)
    with pytest.raises(InvalidOptionContractError, match="right cannot be None"):
        OptionContract(_NIFTY, _MONTHLY, _K25000, None)


def test_wrong_member_types_are_rejected() -> None:
    with pytest.raises(InvalidOptionContractError, match="must be an OptionProductReference"):
        OptionContract("NIFTY@NSE", _MONTHLY, _K25000, OptionRight.CALL)
    with pytest.raises(InvalidOptionContractError, match="must be an ExpirationDate"):
        OptionContract(_NIFTY, "2026-10-27", _K25000, OptionRight.CALL)
    with pytest.raises(InvalidOptionContractError, match="must be an OptionStrike"):
        OptionContract(_NIFTY, _MONTHLY, Decimal("25000"), OptionRight.CALL)
    with pytest.raises(InvalidOptionContractError, match="must be an OptionRight"):
        OptionContract(_NIFTY, _MONTHLY, _K25000, "CALL")


@pytest.mark.parametrize("spelling", ["CE", "PE"])
def test_venue_right_spellings_are_rejected(spelling: str) -> None:
    with pytest.raises(InvalidOptionContractError, match="must be an OptionRight"):
        OptionContract(_NIFTY, _MONTHLY, _K25000, spelling)


def test_a_futures_product_reference_is_not_an_option_product() -> None:
    futures = FuturesProductReference(Symbol("NIFTY"), _NSE)

    with pytest.raises(InvalidOptionContractError, match="must be an OptionProductReference"):
        OptionContract(futures, _MONTHLY, _K25000, OptionRight.CALL)


def test_a_provider_trading_symbol_is_not_a_product() -> None:
    with pytest.raises(InvalidOptionContractError, match="must be an OptionProductReference"):
        OptionContract(Symbol("NIFTY26OCT25000CE"), _MONTHLY, _K25000, OptionRight.CALL)


def test_the_error_is_a_validation_error() -> None:
    assert issubclass(InvalidOptionContractError, ValidationError)
    with pytest.raises(ValidationError):
        OptionContract(None, _MONTHLY, _K25000, OptionRight.CALL)


# ---------------------------------------------------------------------------
# Value semantics
# ---------------------------------------------------------------------------


def test_the_contract_is_immutable() -> None:
    contract = _contract()

    with pytest.raises(FrozenInstanceError):
        contract.product = _BANKNIFTY  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        contract.expiration_date = _WEEKLY  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        contract.strike = _K25050  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        contract.right = OptionRight.PUT  # type: ignore[misc]


def test_contracts_are_not_ordered_directly() -> None:
    """Canonical order is spelled out through the natural key, as for futures contracts."""
    with pytest.raises(TypeError):
        _ = _contract() < _contract(strike=_K25050)  # type: ignore[operator]


def test_string_form() -> None:
    assert str(_contract(_NIFTY, _MONTHLY, _K25000, OptionRight.CALL)) == (
        "NIFTY@NSE 2026-10-27 25000 CALL"
    )
    assert str(_contract(_NIFTY, _WEEKLY, OptionStrike(Decimal("24950.50")), OptionRight.PUT)) == (
        "NIFTY@NSE 2026-10-20 24950.5 PUT"
    )


def test_repr_form() -> None:
    assert repr(_contract()) == (
        "OptionContract("
        "product=OptionProductReference("
        "product_code=Symbol(value='NIFTY'), "
        "exchange_code=ExchangeCode(value='NSE')"
        "), "
        "expiration_date=ExpirationDate(value='2026-10-27'), "
        "strike=OptionStrike(value=Decimal('25000')), "
        "right=<OptionRight.CALL: 'CALL'>"
        ")"
    )


# ---------------------------------------------------------------------------
# Scope
# ---------------------------------------------------------------------------


def test_the_contract_carries_no_surrogate_identity() -> None:
    contract = _contract()

    for absent in ("identity", "contract_identity", "option_contract_identity"):
        assert not hasattr(contract, absent)


def test_the_contract_carries_no_deferred_concepts() -> None:
    contract = _contract()

    for absent in (
        "underlying",
        "underlying_reference",
        "series",
        "is_weekly",
        "is_monthly",
        "lot_size",
        "multiplier",
        "point_value",
        "premium",
        "exercise_style",
        "settlement_method",
        "instrument_key",
        "trading_symbol",
        "provider_symbol",
        "symbol",
        "listing_reference",
        "moneyness",
        "implied_volatility",
        "delta",
        "last_trading_day",
    ):
        assert not hasattr(contract, absent)
