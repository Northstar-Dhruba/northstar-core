"""One individual option contract within an exchange-defined option product.

A contract is fully determined by which product it belongs to, when it
expires, where it is struck and which right it grants, so those four values
are its identity rather than attributes hanging off a separate identifier.
There is deliberately no surrogate option-contract identity: a natural key
already exists, and a second identifier alongside it would be an independent
source of truth that could disagree with the first.

What is not identity
--------------------
- The underlying belongs to OptionProductSpecification and is shared by every
  contract of the product.
- Weekly and monthly series are not different products or different kinds of
  contract. They are contracts of one product with different expiration dates,
  and the date alone identifies them.
- Lot size is an economic fact that can differ between expiries of one product,
  so it belongs to contract economics, never to identity.
- Exercise style and settlement method are product-level facts, deferred until
  expiry settlement is modelled.
- Provider instrument keys and trading symbols are provider naming concerns and
  stay in Infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.derivatives.value_objects import ExpirationDate
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.options.value_objects.option_product_reference import (
    OptionProductReference,
)
from northstar_core.options.value_objects.option_right import OptionRight
from northstar_core.options.value_objects.option_strike import OptionStrike


class InvalidOptionContractError(ValidationError):
    """Raised when an OptionContract value is invalid."""


def _validate_product(value: OptionProductReference) -> OptionProductReference:
    if value is None:
        raise InvalidOptionContractError("OptionContract product cannot be None.")
    if not isinstance(value, OptionProductReference):
        raise InvalidOptionContractError(
            "OptionContract product must be an OptionProductReference value."
        )
    return value


def _validate_expiration_date(value: ExpirationDate) -> ExpirationDate:
    if value is None:
        raise InvalidOptionContractError("OptionContract expiration date cannot be None.")
    if not isinstance(value, ExpirationDate):
        raise InvalidOptionContractError(
            "OptionContract expiration date must be an ExpirationDate value."
        )
    return value


def _validate_strike(value: OptionStrike) -> OptionStrike:
    if value is None:
        raise InvalidOptionContractError("OptionContract strike cannot be None.")
    if not isinstance(value, OptionStrike):
        raise InvalidOptionContractError("OptionContract strike must be an OptionStrike value.")
    return value


def _validate_right(value: OptionRight) -> OptionRight:
    if value is None:
        raise InvalidOptionContractError("OptionContract right cannot be None.")
    # A plain "CALL" string compares equal to OptionRight.CALL; only the member is accepted.
    if not isinstance(value, OptionRight):
        raise InvalidOptionContractError("OptionContract right must be an OptionRight value.")
    return value


@dataclass(frozen=True, slots=True)
class OptionContract:
    """Immutable identity of one option contract.

    Identity is exactly ``(product, expiration_date, strike, right)``. Two
    contracts that differ in any one of those are different contracts.
    """

    product: OptionProductReference
    expiration_date: ExpirationDate
    strike: OptionStrike
    right: OptionRight

    def __post_init__(self) -> None:
        object.__setattr__(self, "product", _validate_product(self.product))
        object.__setattr__(self, "expiration_date", _validate_expiration_date(self.expiration_date))
        object.__setattr__(self, "strike", _validate_strike(self.strike))
        object.__setattr__(self, "right", _validate_right(self.right))

    @property
    def natural_key(
        self,
    ) -> tuple[OptionProductReference, ExpirationDate, OptionStrike, OptionRight]:
        """Return the identity under which this contract is known."""
        return (self.product, self.expiration_date, self.strike, self.right)

    def __str__(self) -> str:
        return f"{self.product} {self.expiration_date} {self.strike} {self.right}"

    def __repr__(self) -> str:
        return (
            "OptionContract("
            f"product={self.product!r}, "
            f"expiration_date={self.expiration_date!r}, "
            f"strike={self.strike!r}, "
            f"right={self.right!r}"
            ")"
        )
