"""The direction of one trade recommendation.

LONG profits from a rise in the contract's quotation and SHORT from a fall.
This is the direction of a trade setup and nothing else. It is deliberately not
RecommendationAction, whose BUY, SELL and HOLD are research actions, and not
OrderSide, whose BUY and SELL describe one execution instruction. A research
SELL is not inherently a SHORT recommendation, and no conversion between these
vocabularies exists here (ADR-017).
"""

from __future__ import annotations

from enum import StrEnum


class TradeDirection(StrEnum):
    """Closed vocabulary for the direction of a trade recommendation."""

    LONG = "LONG"
    SHORT = "SHORT"
