"""Record of one simulated futures order awaiting or having received its fill.

A futures paper order exists from the decision onward, before the next stored
bar needed to simulate its fill has been observed. It therefore carries no
status: PaperOrderStatus is terminal on construction and would force the order
to claim a result it cannot yet know. Whether an order has been filled is
derived later from whether a FuturesPaperFill exists for it.

Intent detail is not duplicated here, so an order can never disagree with what
was intended. There is no limit or stop price, time in force, rejection or
broker state.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.paper_trading.value_objects.futures_execution_intent import (
    FuturesExecutionIntent,
)
from northstar_core.paper_trading.value_objects.paper_order_identity import PaperOrderIdentity


class InvalidFuturesPaperOrderError(ValidationError):
    """Raised when a FuturesPaperOrder value is invalid."""


def _validate_identity(value: PaperOrderIdentity) -> PaperOrderIdentity:
    if value is None:
        raise InvalidFuturesPaperOrderError("FuturesPaperOrder identity cannot be None.")
    if not isinstance(value, PaperOrderIdentity):
        raise InvalidFuturesPaperOrderError(
            "FuturesPaperOrder identity must be a PaperOrderIdentity value."
        )
    return value


def _validate_intent(value: FuturesExecutionIntent) -> FuturesExecutionIntent:
    if value is None:
        raise InvalidFuturesPaperOrderError("FuturesPaperOrder intent cannot be None.")
    if not isinstance(value, FuturesExecutionIntent):
        raise InvalidFuturesPaperOrderError(
            "FuturesPaperOrder intent must be a FuturesExecutionIntent value."
        )
    return value


@dataclass(frozen=True, slots=True)
class FuturesPaperOrder:
    """Immutable simulated futures order for one FuturesExecutionIntent."""

    identity: PaperOrderIdentity
    intent: FuturesExecutionIntent

    def __post_init__(self) -> None:
        object.__setattr__(self, "identity", _validate_identity(self.identity))
        object.__setattr__(self, "intent", _validate_intent(self.intent))

    def __str__(self) -> str:
        return f"{self.identity} {self.intent}"

    def __repr__(self) -> str:
        return f"FuturesPaperOrder(identity={self.identity!r}, intent={self.intent!r})"
