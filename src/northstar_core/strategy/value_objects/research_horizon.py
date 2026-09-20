"""Forward measurement horizon expressed in completed observations.

ResearchHorizon counts completed observations strictly after the decision
observation. It deliberately carries no calendar duration: weekends, holidays
and early closes are handled by the observation series itself, and the same
horizon value remains meaningful for any Timeframe.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError


class InvalidResearchHorizonError(ValidationError):
    """Raised when a ResearchHorizon value is invalid."""


def _validate_observations(value: int) -> int:
    if value is None:
        raise InvalidResearchHorizonError("ResearchHorizon observations cannot be None.")
    if isinstance(value, bool):
        raise InvalidResearchHorizonError("ResearchHorizon observations must be an integer.")
    if not isinstance(value, int):
        raise InvalidResearchHorizonError("ResearchHorizon observations must be an integer.")
    if value < 1:
        raise InvalidResearchHorizonError(
            "ResearchHorizon observations must be at least one observation."
        )
    return value


@dataclass(frozen=True, slots=True, order=True)
class ResearchHorizon:
    """Immutable count of completed observations following one decision.

    ``observations`` is the number of completed observations strictly after the
    decision observation. Horizon one is the immediately following completed
    observation; the decision observation itself is never counted.

    ResearchHorizon does not represent a calendar duration, a Timeframe, a
    holding period, or an execution schedule.
    """

    observations: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "observations", _validate_observations(self.observations))

    def __str__(self) -> str:
        return str(self.observations)

    def __repr__(self) -> str:
        return f"ResearchHorizon(observations={self.observations!r})"
