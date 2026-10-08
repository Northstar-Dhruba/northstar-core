"""What one exchange-defined option product is written on.

A specification names an option product and the economic underlying it derives
its value from. NIFTY@NSE options are written on the NIFTY50 index. The
underlying is an attribute of the product, not part of its identity, and it is
not part of an individual contract's identity either: every contract of the
product shares it, so repeating it on each contract would only create copies
that could disagree.

Exercise style and settlement method are also product-level facts -- NIFTY
options are European and cash-settled -- but nothing consumes them yet. The
first lifecycle exits every position by trading before expiry, so they are
deliberately deferred until expiry settlement is modelled.

The specification likewise carries no lot size, strike interval, tick size,
expiry calendar, currency, provider symbol or listing identity.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.derivatives.value_objects import UnderlyingReference
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import ExchangeCode, Symbol
from northstar_core.options.value_objects.option_product_reference import (
    OptionProductReference,
)


class InvalidOptionProductSpecificationError(ValidationError):
    """Raised when an OptionProductSpecification value is invalid."""


def _validate_reference(value: OptionProductReference) -> OptionProductReference:
    if value is None:
        raise InvalidOptionProductSpecificationError(
            "OptionProductSpecification reference cannot be None."
        )
    if not isinstance(value, OptionProductReference):
        raise InvalidOptionProductSpecificationError(
            "OptionProductSpecification reference must be an OptionProductReference value."
        )
    return value


def _validate_underlying(value: UnderlyingReference) -> UnderlyingReference:
    if value is None:
        raise InvalidOptionProductSpecificationError(
            "OptionProductSpecification underlying cannot be None."
        )
    if not isinstance(value, UnderlyingReference):
        raise InvalidOptionProductSpecificationError(
            "OptionProductSpecification underlying must be an UnderlyingReference value."
        )
    return value


@dataclass(frozen=True, slots=True)
class OptionProductSpecification:
    """Immutable description of one exchange-defined option product.

    Identity is the product reference. Product code and exchange code are
    surfaced as derived properties rather than stored again, so a
    specification can never disagree with the reference it describes.
    """

    reference: OptionProductReference
    underlying: UnderlyingReference

    def __post_init__(self) -> None:
        object.__setattr__(self, "reference", _validate_reference(self.reference))
        object.__setattr__(self, "underlying", _validate_underlying(self.underlying))

    @property
    def product_code(self) -> Symbol:
        """Return the exchange's code for this product."""
        return self.reference.product_code

    @property
    def exchange_code(self) -> ExchangeCode:
        """Return the exchange that defines this product."""
        return self.reference.exchange_code

    def __str__(self) -> str:
        return f"{self.reference} on {self.underlying}"

    def __repr__(self) -> str:
        return (
            "OptionProductSpecification("
            f"reference={self.reference!r}, "
            f"underlying={self.underlying!r}"
            ")"
        )
