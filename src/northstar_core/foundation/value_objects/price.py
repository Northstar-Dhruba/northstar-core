"""Financial price value object.

Price represents a denomination-bound monetary value.

It does not represent physical measurement, abstract measurement, exchange rates,
or currency conversion. Price is a financial value expressed in a specific
Currency and remains distinct from Quantity-based measurement semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from northstar_core.foundation.exceptions.validation import (
    CurrencyMismatchError,
    InvalidPriceError,
)
from northstar_core.foundation.value_objects.currency import Currency


def _normalize_amount(value: object) -> Decimal:
    if value is None:
        raise InvalidPriceError("Price amount cannot be None.")
    if isinstance(value, bool):
        raise InvalidPriceError("Price amount must be a numeric value.")
    if isinstance(value, float):
        raise InvalidPriceError("Price amount must not be a float.")
    if isinstance(value, Decimal):
        normalized = value
    elif isinstance(value, int):
        normalized = Decimal(value)
    elif isinstance(value, str):
        if not value.strip():
            raise InvalidPriceError("Price amount cannot be empty.")
        try:
            normalized = Decimal(value.strip())
        except InvalidOperation as exc:
            raise InvalidPriceError("Price amount must be a numeric value.") from exc
    else:
        raise InvalidPriceError("Price amount must be a numeric value.")

    if not normalized.is_finite():
        raise InvalidPriceError("Price amount must be finite.")

    normalized = normalized.normalize()
    canonical_text = format(normalized, "f")
    return Decimal(canonical_text)


def _validate_amount(value: Decimal) -> None:
    if value < 0:
        raise InvalidPriceError("Price amount cannot be negative.")


def _require_matching_currency(left: Currency, right: Currency) -> None:
    if left != right:
        raise CurrencyMismatchError("Price currencies do not match.")


@dataclass(frozen=True, slots=True)
class Price:
    """Immutable representation of a canonical financial price.

    Purpose:
        Preserve a monetary value expressed in a specific currency.

    Invariants:
        - The stored amount is always valid.
        - The stored currency is always a valid Currency instance.
        - The stored amount never becomes negative.
        - Cross-currency operations are rejected.

    Examples:
        100 USD
        25.50 EUR
        0 BTC
    """

    amount: Decimal
    currency: Currency

    def __post_init__(self) -> None:
        normalized_amount = _normalize_amount(self.amount)
        _validate_amount(normalized_amount)

        if self.currency is None:
            raise InvalidPriceError("Price currency cannot be None.")
        if not isinstance(self.currency, Currency):
            raise InvalidPriceError("Price currency must be a Currency value.")

        object.__setattr__(self, "amount", normalized_amount)
        object.__setattr__(self, "currency", self.currency)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Price):
            return NotImplemented
        if self.currency != other.currency:
            return False
        return self.amount == other.amount

    def __add__(self, other: object) -> Price:
        if isinstance(other, Price):
            _require_matching_currency(self.currency, other.currency)
            return Price(self.amount + other.amount, self.currency)
        return NotImplemented

    def __sub__(self, other: object) -> Price:
        if isinstance(other, Price):
            _require_matching_currency(self.currency, other.currency)
            result = self.amount - other.amount
            if result < 0:
                raise InvalidPriceError("Price amount cannot be negative.")
            return Price(result, self.currency)
        return NotImplemented

    def __mul__(self, other: object) -> Price:
        if isinstance(other, Decimal):
            return Price(self.amount * other, self.currency)
        if isinstance(other, int):
            return Price(self.amount * Decimal(other), self.currency)
        return NotImplemented

    def __truediv__(self, other: object) -> Price:
        if isinstance(other, Decimal):
            if other == 0:
                raise InvalidPriceError("Price cannot be divided by zero.")
            return Price(self.amount / other, self.currency)
        if isinstance(other, int):
            if other == 0:
                raise InvalidPriceError("Price cannot be divided by zero.")
            return Price(self.amount / Decimal(other), self.currency)
        return NotImplemented

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Price):
            return NotImplemented
        _require_matching_currency(self.currency, other.currency)
        return self.amount < other.amount

    def __le__(self, other: object) -> bool:
        if not isinstance(other, Price):
            return NotImplemented
        _require_matching_currency(self.currency, other.currency)
        return self.amount <= other.amount

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, Price):
            return NotImplemented
        _require_matching_currency(self.currency, other.currency)
        return self.amount > other.amount

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, Price):
            return NotImplemented
        _require_matching_currency(self.currency, other.currency)
        return self.amount >= other.amount

    def __str__(self) -> str:
        return f"{self.amount} {self.currency.value}"

    def __repr__(self) -> str:
        return f"Price(amount={self.amount!r}, currency={self.currency!r})"
