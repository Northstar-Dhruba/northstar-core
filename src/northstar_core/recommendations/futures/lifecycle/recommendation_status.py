"""The derived lifecycle state of one trade recommendation.

A status is never stored on a recommendation and never set directly. It is
derived from the recommendation's ordered lifecycle events by
FuturesTradeRecommendationLifecycle, so it cannot disagree with them.

INDETERMINATE_ENTRY is terminal: its entry observation also touched the stop
or the target, and a daily observation cannot show which came first. Going on
would require inventing that chronology. It is neither a winner nor a loser.

EXPIRED_WITH_INCOMPLETE_COVERAGE is terminal: validity ended by time while some
required observation was missing, unapproved or unverified. It does not mean
the stop or target was not reached, and it is not a verified expiry; neither it
nor INDETERMINATE_ENTRY is a verified recommendation outcome. EXPIRED_BEFORE_ENTRY
and EXPIRED_AFTER_ACTIVATION are reached only on an observed bar or on time
expiry with complete verified coverage.
"""

from __future__ import annotations

from enum import StrEnum


class RecommendationStatus(StrEnum):
    """Closed vocabulary for the lifecycle state of a trade recommendation."""

    WAITING_FOR_ENTRY = "WAITING_FOR_ENTRY"
    ACTIVE = "ACTIVE"
    CLOSED_TARGET = "CLOSED_TARGET"
    CLOSED_STOP = "CLOSED_STOP"
    EXPIRED_BEFORE_ENTRY = "EXPIRED_BEFORE_ENTRY"
    EXPIRED_AFTER_ACTIVATION = "EXPIRED_AFTER_ACTIVATION"
    INDETERMINATE_ENTRY = "INDETERMINATE_ENTRY"
    EXPIRED_WITH_INCOMPLETE_COVERAGE = "EXPIRED_WITH_INCOMPLETE_COVERAGE"

    @property
    def is_terminal(self) -> bool:
        """Return whether no further observation can change this state."""
        return self not in (RecommendationStatus.WAITING_FOR_ENTRY, RecommendationStatus.ACTIVE)
