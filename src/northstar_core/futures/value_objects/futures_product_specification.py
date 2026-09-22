"""What one exchange-defined futures product is written on.

A specification names a product and the economic underlying it tracks. ES@CME
and MES@CME both track SP500 and remain entirely distinct products: the
underlying is what they have in common, never what tells them apart.

Why contract multiplier and tick size are not here yet
------------------------------------------------------
Both are routinely described as "a positive number", and modelling them that
way would be wrong. They are quantities in economic units, and the units differ
per product:

- An ES multiplier of 50 means 50 USD *per index point*: a currency rate
  against a dimensionless underlying.
- A CL contract size of 1000 means 1000 *barrels*: a physical quantity, with no
  currency in it at all.
- A ZB tick of one thirty-second of a point is a fraction in a non-decimal
  quotation convention, not a decimal price increment.
- Tick value is neither of the above; it is multiplier times tick size,
  expressed in currency.

A bare ``Decimal > 0`` would let all four be stored in one field and silently
compared, summed or multiplied across incompatible units. Getting them right
needs a quotation-unit concept this domain does not have, and inventing that
concept before anything consumes it would fix the wrong abstraction in place.
They are therefore deferred until a consumer -- notional value, tick-aligned
order validation, or futures profit and loss -- actually requires them, and
each of those is out of scope.

The specification likewise carries no contract size, tick value, quote units,
currency assumption, provider symbol or listing identity.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.derivatives.value_objects import UnderlyingReference
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import ExchangeCode, Symbol
from northstar_core.futures.value_objects.futures_product_reference import (
    FuturesProductReference,
)


class InvalidFuturesProductSpecificationError(ValidationError):
    """Raised when a FuturesProductSpecification value is invalid."""


def _validate_reference(value: FuturesProductReference) -> FuturesProductReference:
    if value is None:
        raise InvalidFuturesProductSpecificationError(
            "FuturesProductSpecification reference cannot be None."
        )
    if not isinstance(value, FuturesProductReference):
        raise InvalidFuturesProductSpecificationError(
            "FuturesProductSpecification reference must be a FuturesProductReference value."
        )
    return value


def _validate_underlying(value: UnderlyingReference) -> UnderlyingReference:
    if value is None:
        raise InvalidFuturesProductSpecificationError(
            "FuturesProductSpecification underlying cannot be None."
        )
    if not isinstance(value, UnderlyingReference):
        raise InvalidFuturesProductSpecificationError(
            "FuturesProductSpecification underlying must be an UnderlyingReference value."
        )
    return value


@dataclass(frozen=True, slots=True)
class FuturesProductSpecification:
    """Immutable description of one exchange-defined futures product.

    Identity is the product reference: a product is the specification an
    exchange publishes under one code on one venue. The underlying is an
    attribute of that product, not part of its identity, and it is not part of
    a contract's identity either -- a FuturesContract remains
    ``(product reference, expiration date)``.

    Product code and exchange code are surfaced as derived properties rather
    than stored again, so a specification can never disagree with the reference
    it describes.
    """

    reference: FuturesProductReference
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
            "FuturesProductSpecification("
            f"reference={self.reference!r}, "
            f"underlying={self.underlying!r}"
            ")"
        )
