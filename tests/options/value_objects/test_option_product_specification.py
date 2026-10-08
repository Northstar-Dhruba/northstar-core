"""Tests for the exchange option product specification."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from northstar_core.derivatives import UnderlyingReference
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import ExchangeCode, Symbol
from northstar_core.futures import FuturesProductReference, FuturesProductSpecification
from northstar_core.options import (
    InvalidOptionProductSpecificationError,
    OptionProductReference,
    OptionProductSpecification,
)

_NSE = ExchangeCode("NSE")
_NIFTY50 = UnderlyingReference("NIFTY50")
_NIFTYBANK = UnderlyingReference("NIFTYBANK")

_NIFTY = OptionProductReference(Symbol("NIFTY"), _NSE)
_BANKNIFTY = OptionProductReference(Symbol("BANKNIFTY"), _NSE)


def _specification(
    reference: OptionProductReference = _NIFTY,
    underlying: UnderlyingReference = _NIFTY50,
) -> OptionProductSpecification:
    return OptionProductSpecification(reference=reference, underlying=underlying)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_a_specification_preserves_its_members() -> None:
    specification = _specification(_NIFTY, _NIFTY50)

    assert specification.reference == _NIFTY
    assert specification.underlying == _NIFTY50


def test_the_field_shape_is_exactly_reference_and_underlying() -> None:
    """Derived codes are not stored again, so they cannot disagree with the reference."""
    assert OptionProductSpecification.__slots__ == ("reference", "underlying")


# ---------------------------------------------------------------------------
# Derived properties
# ---------------------------------------------------------------------------


def test_product_and_exchange_codes_are_derived_from_the_reference() -> None:
    specification = _specification()

    assert specification.product_code == Symbol("NIFTY")
    assert specification.exchange_code == _NSE
    assert specification.product_code is specification.reference.product_code
    assert specification.exchange_code is specification.reference.exchange_code


@pytest.mark.parametrize("name", ["product_code", "exchange_code"])
def test_derived_codes_are_read_only(name: str) -> None:
    specification = _specification()

    with pytest.raises(AttributeError):
        setattr(specification, name, None)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_none_members_are_rejected() -> None:
    with pytest.raises(InvalidOptionProductSpecificationError, match="reference cannot be None"):
        OptionProductSpecification(None, _NIFTY50)
    with pytest.raises(InvalidOptionProductSpecificationError, match="underlying cannot be None"):
        OptionProductSpecification(_NIFTY, None)


def test_wrong_member_types_are_rejected() -> None:
    with pytest.raises(
        InvalidOptionProductSpecificationError, match="must be an OptionProductReference value"
    ):
        OptionProductSpecification("NIFTY@NSE", _NIFTY50)
    with pytest.raises(
        InvalidOptionProductSpecificationError, match="must be an UnderlyingReference value"
    ):
        OptionProductSpecification(_NIFTY, "NIFTY50")


def test_a_futures_product_reference_is_not_an_option_product() -> None:
    futures = FuturesProductReference(Symbol("NIFTY"), _NSE)

    with pytest.raises(
        InvalidOptionProductSpecificationError, match="must be an OptionProductReference value"
    ):
        OptionProductSpecification(futures, _NIFTY50)


def test_a_symbol_is_not_accepted_as_an_underlying() -> None:
    with pytest.raises(
        InvalidOptionProductSpecificationError, match="must be an UnderlyingReference value"
    ):
        OptionProductSpecification(_NIFTY, Symbol("NIFTY50"))


def test_the_error_is_a_validation_error() -> None:
    assert issubclass(InvalidOptionProductSpecificationError, ValidationError)
    with pytest.raises(ValidationError):
        OptionProductSpecification(None, _NIFTY50)


# ---------------------------------------------------------------------------
# Identity and equality
# ---------------------------------------------------------------------------


def test_equal_specifications_compare_and_hash_equal() -> None:
    assert _specification() == _specification()
    assert hash(_specification()) == hash(_specification())


def test_different_products_are_distinct_specifications() -> None:
    assert _specification(_NIFTY, _NIFTY50) != _specification(_BANKNIFTY, _NIFTYBANK)
    assert len({_specification(_NIFTY, _NIFTY50), _specification(_BANKNIFTY, _NIFTYBANK)}) == 2


def test_the_same_reference_with_a_different_underlying_is_a_distinct_value() -> None:
    """Rejecting a contradictory second specification is a registry's job, not this value's."""
    honest = _specification(_NIFTY, _NIFTY50)
    contradictory = _specification(_NIFTY, _NIFTYBANK)

    assert honest != contradictory
    assert honest.reference == contradictory.reference


def test_option_and_futures_specifications_on_one_underlying_stay_distinct() -> None:
    option = _specification(_NIFTY, _NIFTY50)
    futures = FuturesProductSpecification(FuturesProductReference(Symbol("NIFTY"), _NSE), _NIFTY50)

    assert option.underlying == futures.underlying
    assert option != futures
    assert len({option, futures}) == 2


# ---------------------------------------------------------------------------
# Value semantics and scope
# ---------------------------------------------------------------------------


def test_the_specification_is_immutable() -> None:
    specification = _specification()

    with pytest.raises(FrozenInstanceError):
        specification.reference = _BANKNIFTY  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        specification.underlying = _NIFTYBANK  # type: ignore[misc]


def test_string_and_repr_forms() -> None:
    specification = _specification()

    assert str(specification) == "NIFTY@NSE on NIFTY50"
    assert repr(specification) == (
        "OptionProductSpecification("
        "reference=OptionProductReference("
        "product_code=Symbol(value='NIFTY'), "
        "exchange_code=ExchangeCode(value='NSE')"
        "), "
        "underlying=UnderlyingReference(value='NIFTY50')"
        ")"
    )


def test_the_specification_carries_no_deferred_detail() -> None:
    specification = _specification()

    for absent in (
        "lot_size",
        "multiplier",
        "point_value",
        "strike_interval",
        "tick_size",
        "exercise_style",
        "settlement_method",
        "currency",
        "expiry_calendar",
        "instrument_key",
    ):
        assert not hasattr(specification, absent)
