"""Signed net exposure to one concrete futures contract.

FuturesPosition states a holding; it does not compute one. Folding fills into a
position -- including a reversal that crosses through zero in one trade -- is
later Application orchestration.

``net_contracts`` is signed: positive is long, negative is short. Zero is
rejected because a flat holding is represented by the absence of a position,
the same rule the equity Position follows.

``average_entry`` is a QuoteValue in the product's own convention and may be
positive, zero or negative. There is no multiplier, notional, margin or profit
and loss, and nothing here closes a position at contract expiration.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.derivatives.value_objects import QuoteValue
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.futures.value_objects.futures_contract import FuturesContract


class InvalidFuturesPositionError(ValidationError):
    """Raised when a FuturesPosition value is invalid."""


def _validate_contract(value: FuturesContract) -> FuturesContract:
    if value is None:
        raise InvalidFuturesPositionError("FuturesPosition contract cannot be None.")
    if not isinstance(value, FuturesContract):
        raise InvalidFuturesPositionError(
            "FuturesPosition contract must be a FuturesContract value."
        )
    return value


def _validate_net_contracts(value: int) -> int:
    if value is None:
        raise InvalidFuturesPositionError("FuturesPosition net contracts cannot be None.")
    # bool is an int subclass; True must not pass as one long contract.
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidFuturesPositionError("FuturesPosition net contracts must be an integer.")
    if value == 0:
        raise InvalidFuturesPositionError(
            "FuturesPosition net contracts cannot be zero; a flat holding is absent."
        )
    return value


def _validate_average_entry(value: QuoteValue) -> QuoteValue:
    if value is None:
        raise InvalidFuturesPositionError("FuturesPosition average entry cannot be None.")
    if not isinstance(value, QuoteValue):
        raise InvalidFuturesPositionError(
            "FuturesPosition average entry must be a QuoteValue value."
        )
    return value


@dataclass(frozen=True, slots=True)
class FuturesPosition:
    """Immutable signed net exposure to one futures contract."""

    contract: FuturesContract
    net_contracts: int
    average_entry: QuoteValue

    def __post_init__(self) -> None:
        object.__setattr__(self, "contract", _validate_contract(self.contract))
        object.__setattr__(self, "net_contracts", _validate_net_contracts(self.net_contracts))
        object.__setattr__(self, "average_entry", _validate_average_entry(self.average_entry))

    @property
    def is_long(self) -> bool:
        """Return whether the exposure is long."""
        return self.net_contracts > 0

    @property
    def is_short(self) -> bool:
        """Return whether the exposure is short."""
        return self.net_contracts < 0

    @property
    def absolute_contracts(self) -> int:
        """Return the unsigned number of contracts held."""
        return abs(self.net_contracts)

    def __str__(self) -> str:
        return f"{self.contract} {self.net_contracts:+d} @ {self.average_entry}"

    def __repr__(self) -> str:
        return (
            "FuturesPosition("
            f"contract={self.contract!r}, "
            f"net_contracts={self.net_contracts!r}, "
            f"average_entry={self.average_entry!r}"
            ")"
        )
