"""The economic facts profit and loss needs about one futures contract.

Economics belong to the individual contract, not to its product. An exchange
can revise a product's contract size so that expiries listed before and after
the revision trade side by side with different sizes: NIFTY@NSE November and
December 2025 contracts traded at a lot of 75 while the January 2026 contract
traded at 65. The product alone therefore does not determine the value of a
quote point, and the contract -- product and expiration -- is the identity of
its economics.

The only fact carried is the point value, which already holds both the
settlement-currency rate per quote point per contract and the settlement
currency itself. For an exchange that sizes a contract as a lot of underlying
units, the point value is the contract's lot multiplied by the quote
multiplier: a NIFTY lot of 65 at 1 INR per index point per unit is 65 INR per
point per contract. There is deliberately no separate lot size, multiplier,
second currency, tick size, tick value, notional or margin.

Economics are assumed constant for the life of one contract. A contract whose
size changes after listing would need effective-dated economics, which are
deferred.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import Currency
from northstar_core.futures.value_objects.futures_contract import FuturesContract
from northstar_core.futures.value_objects.futures_point_value import FuturesPointValue


class InvalidFuturesContractEconomicsError(ValidationError):
    """Raised when a FuturesContractEconomics value is invalid."""


def _validate_contract(value: FuturesContract) -> FuturesContract:
    if value is None:
        raise InvalidFuturesContractEconomicsError(
            "FuturesContractEconomics contract cannot be None."
        )
    if not isinstance(value, FuturesContract):
        raise InvalidFuturesContractEconomicsError(
            "FuturesContractEconomics contract must be a FuturesContract value."
        )
    return value


def _validate_point_value(value: FuturesPointValue) -> FuturesPointValue:
    if value is None:
        raise InvalidFuturesContractEconomicsError(
            "FuturesContractEconomics point value cannot be None."
        )
    if not isinstance(value, FuturesPointValue):
        raise InvalidFuturesContractEconomicsError(
            "FuturesContractEconomics point value must be a FuturesPointValue value."
        )
    return value


@dataclass(frozen=True, slots=True)
class FuturesContractEconomics:
    """Immutable economics of one individual futures contract.

    The contract is the identity: product code, exchange code and expiration
    are read from it and never stored beside it, so they cannot disagree.
    """

    contract: FuturesContract
    point_value: FuturesPointValue

    def __post_init__(self) -> None:
        object.__setattr__(self, "contract", _validate_contract(self.contract))
        object.__setattr__(self, "point_value", _validate_point_value(self.point_value))

    @property
    def settlement_currency(self) -> Currency:
        """Return the currency the contract settles in, owned by the point value."""
        return self.point_value.currency

    def __str__(self) -> str:
        return f"{self.contract} {self.point_value}"

    def __repr__(self) -> str:
        return (
            "FuturesContractEconomics("
            f"contract={self.contract!r}, "
            f"point_value={self.point_value!r}"
            ")"
        )
