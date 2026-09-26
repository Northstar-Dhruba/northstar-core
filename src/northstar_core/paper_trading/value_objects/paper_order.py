"""Terminal record of one simulated execution attempt.

PaperOrder pairs one approved ExecutionIntent with the result of simulating it.
It is created already resolved and never changes: there are no lifecycle
transitions, no cancellation, no replacement and no amendment, because
simulated execution resolves immediately against decision-time evidence.

Intent detail is not duplicated here. Listing, side, quantity, strategy and
decision instant remain owned by the frozen intent, so an order can never
disagree with what was intended.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.paper_trading.value_objects.execution_intent import ExecutionIntent
from northstar_core.paper_trading.value_objects.paper_order_identity import PaperOrderIdentity
from northstar_core.paper_trading.value_objects.paper_order_status import PaperOrderStatus


class InvalidPaperOrderError(ValidationError):
    """Raised when a PaperOrder value is invalid."""


def _validate_identity(value: PaperOrderIdentity) -> PaperOrderIdentity:
    if value is None:
        raise InvalidPaperOrderError("PaperOrder identity cannot be None.")
    if not isinstance(value, PaperOrderIdentity):
        raise InvalidPaperOrderError("PaperOrder identity must be a PaperOrderIdentity value.")
    return value


def _validate_intent(value: ExecutionIntent) -> ExecutionIntent:
    if value is None:
        raise InvalidPaperOrderError("PaperOrder intent cannot be None.")
    if not isinstance(value, ExecutionIntent):
        raise InvalidPaperOrderError("PaperOrder intent must be an ExecutionIntent value.")
    return value


def _validate_status(value: PaperOrderStatus) -> PaperOrderStatus:
    if value is None:
        raise InvalidPaperOrderError("PaperOrder status cannot be None.")
    if not isinstance(value, PaperOrderStatus):
        raise InvalidPaperOrderError("PaperOrder status must be a PaperOrderStatus value.")
    return value


@dataclass(frozen=True, slots=True)
class PaperOrder:
    """Immutable terminal result of simulating one ExecutionIntent.

    ``status`` is terminal on construction. A FILLED order is expected to have
    exactly one corresponding PaperFill; a REJECTED order has none and
    contributes nothing to any derived Position.
    """

    identity: PaperOrderIdentity
    intent: ExecutionIntent
    status: PaperOrderStatus

    def __post_init__(self) -> None:
        object.__setattr__(self, "identity", _validate_identity(self.identity))
        object.__setattr__(self, "intent", _validate_intent(self.intent))
        object.__setattr__(self, "status", _validate_status(self.status))

    def __str__(self) -> str:
        return f"{self.identity} {self.status} {self.intent}"

    def __repr__(self) -> str:
        return (
            "PaperOrder("
            f"identity={self.identity!r}, "
            f"intent={self.intent!r}, "
            f"status={self.status!r}"
            ")"
        )
