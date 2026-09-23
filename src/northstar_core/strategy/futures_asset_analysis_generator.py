"""Domain behavior for generating FuturesAssetAnalysis from factual observations.

The futures parallel of AssetAnalysisGenerator. Both unwrap their own context
into bare Decimals and hand them to the one shared directional signal, so the
two asset classes read the same observations the same way and there is a single
implementation of the arithmetic to keep deterministic.

Nothing here assumes a quotation is positive. The signal compares the latest
quote with the previous close and a short average with a long one; it never
divides by a quote, so a negative, zero or zero-crossing series is read exactly
as a positive one shifted by a constant would be.
"""

from __future__ import annotations

from northstar_core.strategy._directional_signal import select_directional_signal
from northstar_core.strategy.value_objects.futures_asset_analysis import FuturesAssetAnalysis
from northstar_core.strategy.value_objects.futures_market_observation_context import (
    FuturesMarketObservationContext,
)


class FuturesAssetAnalysisGenerator:
    """Generates deterministic Strategy input from one futures observation context."""

    def generate(self, context: FuturesMarketObservationContext) -> FuturesAssetAnalysis:
        """Interpret one factual futures context into a FuturesAssetAnalysis."""
        if context is None:
            raise TypeError("FuturesAssetAnalysisGenerator context cannot be None.")
        if not isinstance(context, FuturesMarketObservationContext):
            raise TypeError(
                "FuturesAssetAnalysisGenerator context must be a "
                "FuturesMarketObservationContext value."
            )

        return FuturesAssetAnalysis(
            contract=context.contract,
            point_in_time=context.observed_at,
            summarized_signals=(self._select_signal(context),),
        )

    @staticmethod
    def _select_signal(context: FuturesMarketObservationContext) -> str:
        return select_directional_signal(
            latest=context.latest_quote.value,
            previous_close=context.previous_close.value,
            recent_closes=tuple(quote.value for quote in context.recent_closes),
            latest_volume=context.latest_volume.value,
            recent_volumes=tuple(volume.value for volume in context.recent_volumes),
        )
