"""Canonical quantity value object.

Purpose:
    Represent a normalized numeric amount as an immutable domain value.

Invariants:
    - A Quantity instance is always valid.
    - A Quantity value is always normalized to a canonical Decimal form.
    - A Quantity value never represents a symbolic identifier and remains finite.
    - A Quantity value represents magnitude only and cannot be negative.

Examples:
    1, 10.5, 0.25, 1000, 3.14159

Note:
    Quantity represents magnitude. It does not represent position, money, price, or percentage.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from northstar_core.foundation.exceptions.validation import InvalidQuantityError
from northstar_core.foundation.value_objects._canonical_decimal import (
    canonical_decimal,
)


def _normalize(value: object) -> Decimal:
    return canonical_decimal(value, "Quantity", InvalidQuantityError)


def _validate(value: Decimal) -> None:
    if value < 0:
        raise InvalidQuantityError("Quantity cannot be negative.")


@dataclass(frozen=True, slots=True, order=True)
class Quantity:
    """Immutable representation of a canonical quantity.

    Purpose:
        Preserve a normalized numeric amount as a domain value.

    Invariants:
        - The stored value is always valid.
        - The stored value is always normalized to a canonical Decimal form.
        - The stored value remains finite and does not represent a symbolic identifier.

    Examples:
        1
        10.5
        0.25
        1000
        3.14159
    """

    value: Decimal

    def __post_init__(self) -> None:
        normalized = _normalize(self.value)
        _validate(normalized)
        object.__setattr__(self, "value", normalized)

    def __add__(self, other: object) -> Quantity:
        if isinstance(other, Quantity):
            return Quantity(self.value + other.value)
        return NotImplemented

    def __sub__(self, other: object) -> Quantity:
        if isinstance(other, Quantity):
            result = self.value - other.value
            if result < 0:
                raise InvalidQuantityError("Quantity cannot be negative.")
            return Quantity(result)
        return NotImplemented

    def __mul__(self, other: object) -> Quantity:
        if isinstance(other, Decimal):
            result = self.value * other
            return Quantity(result)
        return NotImplemented

    def __truediv__(self, other: object) -> Quantity:
        if isinstance(other, Decimal):
            if other == 0:
                raise InvalidQuantityError("Quantity cannot be divided by zero.")
            return Quantity(self.value / other)
        return NotImplemented

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"Quantity(value={self.value!r})"
