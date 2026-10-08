"""Identity association for one exchange-defined option product.

An option product is an exchange's option specification -- the family every
individual option contract is an instance of. NIFTY options on NSE are one
product; their weekly and monthly expiries, strikes, calls and puts are all
contracts of it.

This is deliberately a different type from FuturesProductReference, although
the two have the same shape. NSE lists a NIFTY future and a NIFTY option under
the same exchange product code, so both display as ``NIFTY@NSE``. They are
nonetheless different exchange products, and a shared type would make them one
equal value. Keeping the types apart makes that confusion unrepresentable.

The exchange is composed into the reference rather than sitting beside it,
because a product is defined by an exchange: ``NIFTY`` without ``NSE`` is not
a product.

``product_code`` is the exchange's code for the specification. It is neither
the economic underlying nor a provider-specific contract symbol: a provider
naming one contract ``NIFTY26OCT25000CE`` or by an instrument key is describing
how that provider spells things, and such names must never become domain
identity.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import ExchangeCode, Symbol


class InvalidOptionProductReferenceError(ValidationError):
    """Raised when an OptionProductReference value is invalid."""


def _validate_product_code(value: Symbol) -> Symbol:
    if value is None:
        raise InvalidOptionProductReferenceError(
            "OptionProductReference product code cannot be None."
        )
    if not isinstance(value, Symbol):
        raise InvalidOptionProductReferenceError(
            "OptionProductReference product code must be a Symbol value."
        )
    return value


def _validate_exchange_code(value: ExchangeCode) -> ExchangeCode:
    if value is None:
        raise InvalidOptionProductReferenceError(
            "OptionProductReference exchange code cannot be None."
        )
    if not isinstance(value, ExchangeCode):
        raise InvalidOptionProductReferenceError(
            "OptionProductReference exchange code must be an ExchangeCode value."
        )
    return value


@dataclass(frozen=True, slots=True, order=True)
class OptionProductReference:
    """Immutable reference to one exchange-defined option product.

    Ordering is by product code, then exchange code. Both components are
    themselves ordered value objects, so the derived order is total and
    deterministic.

    The reference deliberately excludes the economic underlying, lot size,
    strike interval, exercise style, settlement method, trading hours and every
    descriptive attribute. The underlying belongs to OptionProductSpecification;
    the rest are deferred.
    """

    product_code: Symbol
    exchange_code: ExchangeCode

    def __post_init__(self) -> None:
        object.__setattr__(self, "product_code", _validate_product_code(self.product_code))
        object.__setattr__(self, "exchange_code", _validate_exchange_code(self.exchange_code))

    def __str__(self) -> str:
        return f"{self.product_code}@{self.exchange_code}"

    def __repr__(self) -> str:
        return (
            "OptionProductReference("
            f"product_code={self.product_code!r}, "
            f"exchange_code={self.exchange_code!r}"
            ")"
        )
