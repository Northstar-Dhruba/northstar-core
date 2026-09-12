"""Domain behavior for generating AssetAnalysis from factual observations."""

from __future__ import annotations

from decimal import Decimal

from northstar_core.strategy.value_objects.asset_analysis import AssetAnalysis
from northstar_core.strategy.value_objects.market_observation_context import (
    MarketObservationContext,
)

_SHORT_WINDOW_LENGTH = 5
_LONG_WINDOW_LENGTH = 20


class AssetAnalysisGenerator:
    """Generates deterministic Strategy input from one market observation context."""

    def generate(self, context: MarketObservationContext) -> AssetAnalysis:
        """Interpret one factual market context into the existing AssetAnalysis."""
        if context is None:
            raise TypeError("AssetAnalysisGenerator context cannot be None.")
        if not isinstance(context, MarketObservationContext):
            raise TypeError(
                "AssetAnalysisGenerator context must be a MarketObservationContext value."
            )

        return AssetAnalysis(
            listing=context.listing,
            point_in_time=context.observed_at,
            summarized_signals=(self._select_signal(context),),
        )

    @staticmethod
    def _select_signal(context: MarketObservationContext) -> str:
        short_average = AssetAnalysisGenerator._average(
            price.amount for price in context.recent_closes[-_SHORT_WINDOW_LENGTH:]
        )
        long_average = AssetAnalysisGenerator._average(
            price.amount for price in context.recent_closes[-_LONG_WINDOW_LENGTH:]
        )
        average_volume = AssetAnalysisGenerator._average(
            volume.value for volume in context.recent_volumes[-_LONG_WINDOW_LENGTH:]
        )

        price_is_rising = context.latest_price > context.previous_close
        price_is_falling = context.latest_price < context.previous_close
        elevated_volume = context.latest_volume.value >= average_volume

        if price_is_rising and short_average > long_average and elevated_volume:
            return "strong bullish"
        if price_is_falling and short_average < long_average and elevated_volume:
            return "strong bearish"
        return "neutral trend"

    @staticmethod
    def _average(values: object) -> Decimal:
        collected_values = tuple(values)
        return sum(collected_values, Decimal()) / len(collected_values)
