"""The fixed envelope one issued recommendation is monitored within (EI5-D6, EI5-D7).

Four instants are distinct and are never interchanged:

- ``eligible_from``: the opening of the first bar that may establish an entry
  (EI4-D1). Bars opening earlier are never evaluated.
- ``latest_entry_bar_opens_at``: the opening of the last bar that may establish
  an entry. Both ends of ``[eligible_from, latest_entry_bar_opens_at]`` are
  included.
- ``entry_window_ends_at``: the close of the bar that opens at
  ``latest_entry_bar_opens_at``. It is the applicable evaluation boundary while
  waiting for entry: expiry needs that last bar as acceptable evidence, and a
  deficiency becomes terminal only at or after it.
- ``modeled_exit_at``: the mandatory modeled exit boundary. The bar closing
  exactly there is the last bar ever read, and it is the applicable boundary
  while active.

The evaluation instant -- a snapshot's ``as_of`` -- is not part of the window:
it arrives with each observation.

Every value comes from the issued recommendation's verified proposal, which
EI-4C already confined to its research-window grid. Core checks only their
order. No value here is an approved production cutoff, and the 09:15 to
15:00 IST research window is not a trading authorization.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime, Price
from northstar_core.recommendations.equity.levels import EquityRecommendationLevels


class InvalidEquityLifecycleWindowError(ValidationError):
    """Raised when a lifecycle window is invalid."""


@dataclass(frozen=True, slots=True)
class EquityLifecycleWindow:
    """The levels and boundaries one recommendation's lifecycle is evaluated against.

    Invariant:
        ``eligible_from <= latest_entry_bar_opens_at < entry_window_ends_at
        <= modeled_exit_at``.
    """

    levels: EquityRecommendationLevels
    eligible_from: PointInTime
    latest_entry_bar_opens_at: PointInTime
    entry_window_ends_at: PointInTime
    modeled_exit_at: PointInTime

    def __post_init__(self) -> None:
        error = InvalidEquityLifecycleWindowError
        if not isinstance(self.levels, EquityRecommendationLevels):
            raise error("EquityLifecycleWindow levels must be EquityRecommendationLevels.")
        for name in (
            "eligible_from",
            "latest_entry_bar_opens_at",
            "entry_window_ends_at",
            "modeled_exit_at",
        ):
            if not isinstance(getattr(self, name), PointInTime):
                raise error(f"EquityLifecycleWindow {name} must be a PointInTime.")
        if self.eligible_from.compare(self.latest_entry_bar_opens_at) > 0:
            raise error("Entry eligibility cannot begin after the latest entry-bar opening.")
        if self.latest_entry_bar_opens_at.compare(self.entry_window_ends_at) >= 0:
            raise error("The last entry bar must close after it opens.")
        if self.entry_window_ends_at.compare(self.modeled_exit_at) > 0:
            raise error("The entry window cannot end after the modeled exit boundary.")

    def entry_touched(self, low: Price, high: Price) -> bool:
        """Return whether a bar range intersects the entry zone (no gap-through for entry)."""
        zone = self.levels.entry_zone
        return low.amount <= zone.high.amount and high.amount >= zone.low.amount

    def stop_reached(self, low: Price) -> bool:
        """Return whether a LONG bar reached the stop, including a gap below it (O-1)."""
        return low.amount <= self.levels.stop.amount

    def target_reached(self, high: Price) -> bool:
        """Return whether a LONG bar reached the target, including a gap above it (O-1)."""
        return high.amount >= self.levels.target.amount
