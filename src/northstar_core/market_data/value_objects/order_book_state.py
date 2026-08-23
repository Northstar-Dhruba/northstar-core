"""Order Book-specific market-depth observation state value object.

OrderBookState composes approved quotation-value concepts for Order Book
market-depth observation meaning. In Version 1.0, Price is the approved
quotation-value concept and OrderBookState composes one or more Price values.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects.price import Price


class InvalidOrderBookStateError(ValidationError):
    """Raised when an OrderBookState value is invalid."""


def _normalize(quotation_values: object) -> tuple[Price, ...]:
    if quotation_values is None:
        raise InvalidOrderBookStateError("OrderBookState quotation values cannot be None.")

    if not isinstance(quotation_values, tuple):
        raise InvalidOrderBookStateError(
            "OrderBookState quotation values must be a tuple of Price values."
        )

    if not quotation_values:
        raise InvalidOrderBookStateError(
            "OrderBookState requires at least one approved quotation-value concept."
        )

    return quotation_values


def _validate(quotation_values: tuple[Price, ...]) -> None:
    for quotation_value in quotation_values:
        if quotation_value is None:
            raise InvalidOrderBookStateError(
                "OrderBookState quotation-value meaning cannot contain None."
            )
        if not isinstance(quotation_value, Price):
            raise InvalidOrderBookStateError(
                "OrderBookState quotation-value meaning must compose Price values."
            )


@dataclass(frozen=True, slots=True)
class OrderBookState:
    """Immutable Order Book-specific market-depth observation meaning.

    Purpose:
        Preserve approved market-depth quotation-value meaning for one Order
        Book context.

    Invariants:
        - The composed quotation-value meaning is non-empty.
        - Each composed quotation-value concept is an approved Price value.
        - Version 1.0 composition uses one or more Price values in a tuple.
        - The value is immutable and identity-free.
    """

    quotation_values: tuple[Price, ...]

    def __post_init__(self) -> None:
        normalized_values = _normalize(self.quotation_values)
        _validate(normalized_values)
        object.__setattr__(self, "quotation_values", normalized_values)

    def __str__(self) -> str:
        # Canonical business representation follows tuple order for determinism.
        return ", ".join(str(value) for value in self.quotation_values)

    def __repr__(self) -> str:
        return f"OrderBookState(quotation_values={self.quotation_values!r})"
