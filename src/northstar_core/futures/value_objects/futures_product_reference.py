"""Identity association for one exchange-defined futures product.

A futures product is an exchange's contract specification -- the family every
individual contract is an instance of. ES and MES are two products on one
economic underlying, distinguished by their specifications rather than by what
they track, which is precisely why the underlying cannot identify a product.

The exchange is composed into the reference rather than sitting beside it,
because a product is defined by an exchange: ``ES`` without ``CME`` is not a
product. Holding them together makes a product attributed to the wrong venue
unrepresentable rather than merely invalid.

``product_code`` is the exchange's code for the specification. It is neither
the economic underlying nor a provider-specific contract symbol: a provider
naming one contract ``CLH26``, ``CL2603`` or ``/CLH26`` is describing how that
provider spells things, and such names must never become domain identity.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import ExchangeCode, Symbol


class InvalidFuturesProductReferenceError(ValidationError):
    """Raised when a FuturesProductReference value is invalid."""


def _validate_product_code(value: Symbol) -> Symbol:
    if value is None:
        raise InvalidFuturesProductReferenceError(
            "FuturesProductReference product code cannot be None."
        )
    if not isinstance(value, Symbol):
        raise InvalidFuturesProductReferenceError(
            "FuturesProductReference product code must be a Symbol value."
        )
    return value


def _validate_exchange_code(value: ExchangeCode) -> ExchangeCode:
    if value is None:
        raise InvalidFuturesProductReferenceError(
            "FuturesProductReference exchange code cannot be None."
        )
    if not isinstance(value, ExchangeCode):
        raise InvalidFuturesProductReferenceError(
            "FuturesProductReference exchange code must be an ExchangeCode value."
        )
    return value


@dataclass(frozen=True, slots=True, order=True)
class FuturesProductReference:
    """Immutable reference to one exchange-defined futures product.

    Ordering is by product code, then exchange code. Both components are
    themselves ordered value objects, so the derived order is total and
    deterministic, which lets collections of products be presented canonically
    without a caller re-deriving the rule.

    The reference deliberately excludes the economic underlying, contract
    multiplier, tick size, trading hours and every descriptive attribute. Those
    belong to a product specification, which this value references rather than
    contains.
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
            "FuturesProductReference("
            f"product_code={self.product_code!r}, "
            f"exchange_code={self.exchange_code!r}"
            ")"
        )
