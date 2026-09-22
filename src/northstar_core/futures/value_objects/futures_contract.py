"""One individual futures contract within an exchange-defined product series.

A contract is fully determined by which product it belongs to and when it
expires, so those two values are its identity rather than attributes hanging
off a separate identifier. There is deliberately no surrogate
FuturesContractIdentity: a natural key already exists, and a second identifier
alongside it would be an independent source of truth that could disagree with
the first.

That distinguishes a contract from a paper order or fill, which genuinely need
surrogate identities because two of them can be identical in every field while
being different events. Two futures contracts identical in product and expiry
are the same contract.

The contract carries no economic underlying, multiplier, tick size, contract
month, last trading day, settlement instant, provider symbol or listing
identity. Each of those is either derivable, owned by a product specification,
or a provider naming concern.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.derivatives.value_objects import ExpirationDate
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.futures.value_objects.futures_product_reference import (
    FuturesProductReference,
)


class InvalidFuturesContractError(ValidationError):
    """Raised when a FuturesContract value is invalid."""


def _validate_product(value: FuturesProductReference) -> FuturesProductReference:
    if value is None:
        raise InvalidFuturesContractError("FuturesContract product cannot be None.")
    if not isinstance(value, FuturesProductReference):
        raise InvalidFuturesContractError(
            "FuturesContract product must be a FuturesProductReference value."
        )
    return value


def _validate_expiration_date(value: ExpirationDate) -> ExpirationDate:
    if value is None:
        raise InvalidFuturesContractError("FuturesContract expiration date cannot be None.")
    if not isinstance(value, ExpirationDate):
        raise InvalidFuturesContractError(
            "FuturesContract expiration date must be an ExpirationDate value."
        )
    return value


@dataclass(frozen=True, slots=True)
class FuturesContract:
    """Immutable identity of one futures contract.

    Identity is exactly ``(product, expiration_date)``. Two contracts on one
    underlying, one exchange and one expiry are still different contracts when
    their products differ -- a standard and a micro contract share everything
    except the specification that makes them tradable as separate instruments.
    """

    product: FuturesProductReference
    expiration_date: ExpirationDate

    def __post_init__(self) -> None:
        object.__setattr__(self, "product", _validate_product(self.product))
        object.__setattr__(self, "expiration_date", _validate_expiration_date(self.expiration_date))

    @property
    def natural_key(self) -> tuple[FuturesProductReference, ExpirationDate]:
        """Return the identity under which this contract is known."""
        return (self.product, self.expiration_date)

    def __str__(self) -> str:
        return f"{self.product} {self.expiration_date}"

    def __repr__(self) -> str:
        return (
            f"FuturesContract(product={self.product!r}, expiration_date={self.expiration_date!r})"
        )
