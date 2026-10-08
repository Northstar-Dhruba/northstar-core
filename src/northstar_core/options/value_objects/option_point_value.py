"""Settlement-currency value of one premium point for one option contract.

An OptionPointValue states how much settlement currency a 1.0 change in an
OptionPremium is worth for one option contract:

    amount  =  settlement-currency units
               per 1.0 change in OptionPremium
               per one option contract

An amount of 65 in INR means a 1.0 move in the premium, on one contract, is
worth 65 INR. For an exchange that sizes a contract as a lot of underlying
units, the point value is the contract's lot multiplied by the premium
multiplier: a NIFTY lot of 65 at 1 INR per index point per unit is 65 INR per
premium point per contract. There is deliberately no separate lot size or
multiplier beside it; this single rate is the only one profit and loss needs.

It is not Money: Money is an amount of currency, whereas this is currency per
premium point per contract. It is not FuturesPointValue either, which values a
futures quote point; the two are separate types so that one family's rate can
never value the other's contracts. It is a unit value, not a calculator: it
performs no arithmetic, so no result can depend on a caller's decimal context.

The amount is strictly positive. The sign of a profit or loss comes from the
premium movement, never from the point value.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import Currency
from northstar_core.foundation.value_objects._canonical_decimal import (
    canonical_decimal,
)


class InvalidOptionPointValueError(ValidationError):
    """Raised when an OptionPointValue value is invalid."""


def _validate_amount(value: Decimal) -> Decimal:
    if value is None:
        raise InvalidOptionPointValueError("OptionPointValue amount cannot be None.")
    if not isinstance(value, Decimal):
        raise InvalidOptionPointValueError("OptionPointValue amount must be a Decimal.")
    amount = canonical_decimal(value, "OptionPointValue amount", InvalidOptionPointValueError)
    if amount <= 0:
        raise InvalidOptionPointValueError("OptionPointValue amount must be greater than zero.")
    return amount


def _validate_currency(value: Currency) -> Currency:
    if value is None:
        raise InvalidOptionPointValueError("OptionPointValue currency cannot be None.")
    if not isinstance(value, Currency):
        raise InvalidOptionPointValueError("OptionPointValue currency must be a Currency value.")
    return value


@dataclass(frozen=True, slots=True)
class OptionPointValue:
    """Immutable settlement-currency amount per premium point per option contract.

    Only a Decimal amount is accepted, stored in the context-independent
    canonical form every Core numeric value uses, so ``65``, ``65.0`` and
    ``65.000`` are one value. Point values are deliberately not ordered: two in
    different currencies have no order, and nothing needs to rank them.
    """

    amount: Decimal
    currency: Currency

    def __post_init__(self) -> None:
        object.__setattr__(self, "amount", _validate_amount(self.amount))
        object.__setattr__(self, "currency", _validate_currency(self.currency))

    def __str__(self) -> str:
        return f"{self.amount} {self.currency}/premium-point/contract"

    def __repr__(self) -> str:
        return f"OptionPointValue(amount={self.amount!r}, currency={self.currency!r})"
