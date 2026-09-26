"""Tests for the exchange futures product specification."""

from __future__ import annotations

import pytest

from northstar_core.derivatives import ExpirationDate, UnderlyingReference
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import ExchangeCode, Symbol
from northstar_core.futures import (
    FuturesContract,
    FuturesProductReference,
    FuturesProductSpecification,
    InvalidFuturesProductSpecificationError,
)

_CME = ExchangeCode("CME")
_NYMEX = ExchangeCode("NYMEX")
_SP500 = UnderlyingReference("SP500")
_WTI = UnderlyingReference("WTI")

_ES = FuturesProductReference(Symbol("ES"), _CME)
_MES = FuturesProductReference(Symbol("MES"), _CME)
_CL = FuturesProductReference(Symbol("CL"), _NYMEX)


def _specification(
    reference: FuturesProductReference = _ES,
    underlying: UnderlyingReference = _SP500,
) -> FuturesProductSpecification:
    return FuturesProductSpecification(reference=reference, underlying=underlying)


# ---------------------------------------------------------------------------
# One underlying, several products
# ---------------------------------------------------------------------------


def test_standard_and_micro_specifications_share_one_underlying() -> None:
    """ES and MES both track SP500; the underlying is what they have in common."""
    standard = _specification(_ES, _SP500)
    micro = _specification(_MES, _SP500)

    assert standard.underlying == micro.underlying == _SP500
    assert standard.exchange_code == micro.exchange_code == _CME


def test_specifications_sharing_an_underlying_remain_distinct_products() -> None:
    standard = _specification(_ES, _SP500)
    micro = _specification(_MES, _SP500)

    assert standard != micro
    assert standard.reference != micro.reference
    assert hash(standard) != hash(micro)
    assert len({standard, micro}) == 2


def test_the_underlying_never_identifies_a_product() -> None:
    """Grouping by underlying must not collapse two products into one."""
    specifications = {_specification(_ES, _SP500), _specification(_MES, _SP500)}

    assert len({spec.underlying for spec in specifications}) == 1
    assert len(specifications) == 2


def test_different_underlyings_on_one_exchange_are_distinct() -> None:
    assert _specification(_ES, _SP500) != _specification(_CL, _WTI)


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


def test_the_same_reference_and_underlying_are_equal() -> None:
    assert _specification(_ES, _SP500) == _specification(_ES, _SP500)
    assert hash(_specification(_ES, _SP500)) == hash(_specification(_ES, _SP500))


def test_the_same_reference_with_a_different_underlying_is_a_distinct_value() -> None:
    """Both are constructible, and they are unequal.

    Identity of a specification is its product reference, but value equality
    compares every field, so two specifications claiming one product on
    different underlyings are distinct values that share an identity. Nothing
    here can detect that contradiction, because a value object only sees
    itself. The concern is real but belongs to whatever later holds a
    collection of specifications: a registry keyed by reference must reject or
    reconcile the second, exactly as PaperFillStore rejects a conflicting fill
    under one identity.
    """
    honest = _specification(_ES, _SP500)
    contradictory = _specification(_ES, _WTI)

    assert honest != contradictory
    assert honest.reference == contradictory.reference
    assert len({honest, contradictory}) == 2
    assert len({honest.reference, contradictory.reference}) == 1


def test_identity_is_the_product_reference() -> None:
    specification = _specification(_ES, _SP500)

    assert specification.reference == _ES
    assert specification.reference != _MES


# ---------------------------------------------------------------------------
# Derived properties
# ---------------------------------------------------------------------------


def test_product_and_exchange_codes_are_derived_from_the_reference() -> None:
    specification = _specification(_CL, _WTI)

    assert specification.product_code == Symbol("CL")
    assert specification.exchange_code == _NYMEX
    assert specification.product_code is specification.reference.product_code
    assert specification.exchange_code is specification.reference.exchange_code


def test_derived_codes_are_not_stored_again() -> None:
    """Duplicated storage could disagree with the reference it describes."""
    assert set(FuturesProductSpecification.__slots__) == {"reference", "underlying"}


@pytest.mark.parametrize("name", ["product_code", "exchange_code"])
def test_derived_codes_are_read_only(name: str) -> None:
    specification = _specification()

    with pytest.raises(AttributeError):
        setattr(specification, name, None)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_none_members_are_rejected() -> None:
    with pytest.raises(InvalidFuturesProductSpecificationError, match="reference cannot be None"):
        FuturesProductSpecification(None, _SP500)
    with pytest.raises(InvalidFuturesProductSpecificationError, match="underlying cannot be None"):
        FuturesProductSpecification(_ES, None)


def test_wrong_member_types_are_rejected() -> None:
    with pytest.raises(
        InvalidFuturesProductSpecificationError, match="must be a FuturesProductReference"
    ):
        FuturesProductSpecification("ES@CME", _SP500)
    with pytest.raises(
        InvalidFuturesProductSpecificationError, match="must be an UnderlyingReference"
    ):
        FuturesProductSpecification(_ES, "SP500")


def test_a_symbol_is_not_accepted_as_an_underlying() -> None:
    with pytest.raises(
        InvalidFuturesProductSpecificationError, match="must be an UnderlyingReference"
    ):
        FuturesProductSpecification(_ES, Symbol("SP500"))


def test_the_error_is_a_validation_error() -> None:
    assert issubclass(InvalidFuturesProductSpecificationError, ValidationError)
    with pytest.raises(ValidationError):
        FuturesProductSpecification(None, _SP500)


# ---------------------------------------------------------------------------
# Value semantics and scope
# ---------------------------------------------------------------------------


def test_the_specification_is_immutable() -> None:
    specification = _specification()

    with pytest.raises(AttributeError):
        specification.reference = _MES
    with pytest.raises(AttributeError):
        specification.underlying = _WTI


def test_it_is_usable_as_a_dictionary_key() -> None:
    catalogue = {_specification(_ES, _SP500): "E-mini", _specification(_MES, _SP500): "Micro"}

    assert catalogue[_specification(_ES, _SP500)] == "E-mini"
    assert catalogue[_specification(_MES, _SP500)] == "Micro"


def test_string_and_repr_forms() -> None:
    specification = _specification(_ES, _SP500)

    assert str(specification) == "ES@CME on SP500"
    assert repr(specification).startswith("FuturesProductSpecification(reference=")


def test_the_specification_carries_no_contract_economics() -> None:
    """Multiplier and tick need quotation units this domain does not yet have."""
    specification = _specification()

    for absent in (
        "multiplier",
        "contract_multiplier",
        "tick_size",
        "tick_value",
        "contract_size",
        "quote_units",
        "currency",
        "listing_reference",
        "provider_symbol",
    ):
        assert not hasattr(specification, absent)


# ---------------------------------------------------------------------------
# The contract is unchanged
# ---------------------------------------------------------------------------


def test_the_contract_identity_still_excludes_the_underlying() -> None:
    contract = FuturesContract(_ES, ExpirationDate("2026-03-20"))

    assert contract.natural_key == (_ES, ExpirationDate("2026-03-20"))
    assert not hasattr(contract, "underlying")
    assert not hasattr(contract, "specification")


def test_two_contracts_on_one_underlying_remain_distinct() -> None:
    march = ExpirationDate("2026-03-20")
    standard = FuturesContract(_ES, march)
    micro = FuturesContract(_MES, march)

    assert _specification(_ES, _SP500).underlying == _specification(_MES, _SP500).underlying
    assert standard != micro
