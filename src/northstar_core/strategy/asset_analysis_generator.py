"""Domain behavior for generating AssetAnalysis from factual observations."""

from __future__ import annotations

from northstar_core.strategy._directional_signal import select_directional_signal
from northstar_core.strategy.value_objects.asset_analysis import AssetAnalysis
from northstar_core.strategy.value_objects.market_observation_context import (
    MarketObservationContext,
)


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
            listing_reference=context.listing_reference,
            point_in_time=context.observed_at,
            summarized_signals=(self._select_signal(context),),
        )

    @staticmethod
    def _select_signal(context: MarketObservationContext) -> str:
        # The context guarantees one currency across every Price, so comparing
        # amounts is exactly what comparing the Prices did.
        return select_directional_signal(
            latest=context.latest_price.amount,
            previous_close=context.previous_close.amount,
            recent_closes=tuple(price.amount for price in context.recent_closes),
            latest_volume=context.latest_volume.value,
            recent_volumes=tuple(volume.value for volume in context.recent_volumes),
        )
