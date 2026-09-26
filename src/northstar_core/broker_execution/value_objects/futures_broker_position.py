"""Signed net exposure to one futures contract, as a broker reports it.

FuturesBrokerPosition is an external fact: what a broker says an account holds
in one concrete contract. It is compared against what Northstar expects from its
own recorded executions; it is never derived from them and never adjusted to
agree with them.

``net_contracts`` is signed: positive is long, negative is short. Zero is
rejected because a flat holding is represented by the absence of a position,
the same rule FuturesPosition follows.

It is deliberately not FuturesPosition. That value requires an average entry in
the product's own quotation convention, and brokers report average prices in
conventions of their own that are not frozen yet. There is no average entry,
profit and loss, margin, market value or broker symbol here.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.futures.value_objects.futures_contract import FuturesContract


class InvalidFuturesBrokerPositionError(ValidationError):
    """Raised when a FuturesBrokerPosition value is invalid."""


def _validate_contract(value: FuturesContract) -> FuturesContract:
    if value is None:
        raise InvalidFuturesBrokerPositionError("FuturesBrokerPosition contract cannot be None.")
    if not isinstance(value, FuturesContract):
        raise InvalidFuturesBrokerPositionError(
            "FuturesBrokerPosition contract must be a FuturesContract value."
        )
    return value


def _validate_net_contracts(value: int) -> int:
    if value is None:
        raise InvalidFuturesBrokerPositionError(
            "FuturesBrokerPosition net contracts cannot be None."
        )
    # bool is an int subclass; True must not pass as one long contract.
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidFuturesBrokerPositionError(
            "FuturesBrokerPosition net contracts must be an integer."
        )
    if value == 0:
        raise InvalidFuturesBrokerPositionError(
            "FuturesBrokerPosition net contracts cannot be zero; a flat holding is absent."
        )
    return value


@dataclass(frozen=True, slots=True)
class FuturesBrokerPosition:
    """Immutable broker-reported signed net exposure to one futures contract."""

    contract: FuturesContract
    net_contracts: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "contract", _validate_contract(self.contract))
        object.__setattr__(self, "net_contracts", _validate_net_contracts(self.net_contracts))

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
        return f"{self.contract} {self.net_contracts:+d}"

    def __repr__(self) -> str:
        return (
            "FuturesBrokerPosition("
            f"contract={self.contract!r}, "
            f"net_contracts={self.net_contracts!r}"
            ")"
        )
