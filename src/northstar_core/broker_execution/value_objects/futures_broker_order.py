"""Northstar's record of one futures order it intends a broker to execute.

A futures broker order is Northstar's own fact: the client order identity it
assigned and the intent it approved. It exists before the broker has seen it,
and nothing a broker later reports changes it.

It therefore carries no broker order identifier, status, broker timestamp,
execution or lifecycle state. Those are external observations the broker makes
about this order, recorded separately so that the order itself can never be
rewritten to agree with them. Intent detail is not duplicated here either, so an
order can never disagree with what was intended.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.broker_execution.value_objects.client_order_identity import (
    ClientOrderIdentity,
)
from northstar_core.broker_execution.value_objects.futures_broker_execution_intent import (
    FuturesBrokerExecutionIntent,
)
from northstar_core.foundation.exceptions.validation import ValidationError


class InvalidFuturesBrokerOrderError(ValidationError):
    """Raised when a FuturesBrokerOrder value is invalid."""


def _validate_identity(value: ClientOrderIdentity) -> ClientOrderIdentity:
    if value is None:
        raise InvalidFuturesBrokerOrderError("FuturesBrokerOrder identity cannot be None.")
    if not isinstance(value, ClientOrderIdentity):
        raise InvalidFuturesBrokerOrderError(
            "FuturesBrokerOrder identity must be a ClientOrderIdentity value."
        )
    return value


def _validate_intent(value: FuturesBrokerExecutionIntent) -> FuturesBrokerExecutionIntent:
    if value is None:
        raise InvalidFuturesBrokerOrderError("FuturesBrokerOrder intent cannot be None.")
    if not isinstance(value, FuturesBrokerExecutionIntent):
        raise InvalidFuturesBrokerOrderError(
            "FuturesBrokerOrder intent must be a FuturesBrokerExecutionIntent value."
        )
    return value


@dataclass(frozen=True, slots=True)
class FuturesBrokerOrder:
    """Immutable Northstar order for one FuturesBrokerExecutionIntent."""

    identity: ClientOrderIdentity
    intent: FuturesBrokerExecutionIntent

    def __post_init__(self) -> None:
        object.__setattr__(self, "identity", _validate_identity(self.identity))
        object.__setattr__(self, "intent", _validate_intent(self.intent))

    def __str__(self) -> str:
        return f"{self.identity} {self.intent}"

    def __repr__(self) -> str:
        return f"FuturesBrokerOrder(identity={self.identity!r}, intent={self.intent!r})"
