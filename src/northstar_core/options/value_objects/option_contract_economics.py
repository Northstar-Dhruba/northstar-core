"""The economic facts profit and loss needs about one option contract.

Economics belong to the individual contract, not to its product. An exchange
can revise a product's lot size so that expiries listed before and after the
revision trade side by side with different lots, and every strike and right of
an expiry is its own contract. The complete OptionContract -- product,
expiration, strike and right -- is therefore the identity of its economics, and
nothing coarser can answer for it.

The only fact carried is the point value, which already holds both the
settlement-currency rate per premium point per contract and the settlement
currency itself. There is deliberately no separate lot size, multiplier,
second currency, tick size, notional, margin, fee or tax.

Economics are assumed constant for the life of one contract. A contract whose
size changes after listing would need effective-dated economics, which are
deferred.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import Currency
from northstar_core.options.value_objects.option_contract import OptionContract
from northstar_core.options.value_objects.option_point_value import OptionPointValue


class InvalidOptionContractEconomicsError(ValidationError):
    """Raised when an OptionContractEconomics value is invalid."""


def _validate_contract(value: OptionContract) -> OptionContract:
    if value is None:
        raise InvalidOptionContractEconomicsError(
            "OptionContractEconomics contract cannot be None."
        )
    if not isinstance(value, OptionContract):
        raise InvalidOptionContractEconomicsError(
            "OptionContractEconomics contract must be an OptionContract value."
        )
    return value


def _validate_point_value(value: OptionPointValue) -> OptionPointValue:
    if value is None:
        raise InvalidOptionContractEconomicsError(
            "OptionContractEconomics point value cannot be None."
        )
    if not isinstance(value, OptionPointValue):
        raise InvalidOptionContractEconomicsError(
            "OptionContractEconomics point value must be an OptionPointValue value."
        )
    return value


@dataclass(frozen=True, slots=True)
class OptionContractEconomics:
    """Immutable economics of one individual option contract.

    The contract is the identity: product code, exchange code, expiration,
    strike and right are read from it and never stored beside it, so they
    cannot disagree.
    """

    contract: OptionContract
    point_value: OptionPointValue

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
            f"OptionContractEconomics(contract={self.contract!r}, point_value={self.point_value!r})"
        )
