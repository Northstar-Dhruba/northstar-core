"""Private directional signal shared by strategy analysis generators.

The signal is plain arithmetic over numbers: it compares the latest value with
the previous close, a short moving average of closes with a long one, and the
latest volume with its long average. Nothing in it depends on what the numbers
denominate, so it takes bare Decimals and lets each generator unwrap its own
values.

Arithmetic runs in one explicit context
---------------------------------------
Summing and dividing a Decimal both consult a context, and by default that is
the caller's ambient one. A caller running at six digits of precision would
round the sums before the averages are compared, and a near-tie such as nineteen
closes at 7663.00 followed by 7663.01 would read as no trend at all -- the same
observations producing a different signal depending on who asked.

Every sum and division therefore runs under ``_SIGNAL_CONTEXT``: 28 digits,
round-half-even. That is the explicit arithmetic contract of this algorithm,
not a claim of exactness: an input whose sum needs more than 28 significant
digits is rounded, identically for every caller. The context equals Python's
default, so results are unchanged for any caller that never altered its own.

The comparisons themselves are exact for finite Decimals and need no context.

This module is internal to the strategy package and is not exported.
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext

_SHORT_WINDOW_LENGTH = 5
_LONG_WINDOW_LENGTH = 20

_SIGNAL_CONTEXT = Context(prec=28, rounding=ROUND_HALF_EVEN)

STRONG_BULLISH = "strong bullish"
STRONG_BEARISH = "strong bearish"
NEUTRAL_TREND = "neutral trend"


def select_directional_signal(
    *,
    latest: Decimal,
    previous_close: Decimal,
    recent_closes: tuple[Decimal, ...],
    latest_volume: Decimal,
    recent_volumes: tuple[Decimal, ...],
) -> str:
    """Return the one directional signal the observations support.

    Strongly bullish when the latest value rose above the previous close, the
    short average of closes is above the long average, and the latest volume is
    at least its long average; strongly bearish on the mirror image with the
    same volume confirmation; otherwise a neutral trend.

    The caller guarantees at least twenty closes and volumes. The averages read
    the trailing five and twenty closes and the trailing twenty volumes.
    """
    with localcontext(_SIGNAL_CONTEXT):
        short_average = _average(recent_closes[-_SHORT_WINDOW_LENGTH:])
        long_average = _average(recent_closes[-_LONG_WINDOW_LENGTH:])
        average_volume = _average(recent_volumes[-_LONG_WINDOW_LENGTH:])

    rising = latest > previous_close
    falling = latest < previous_close
    elevated_volume = latest_volume >= average_volume

    if rising and short_average > long_average and elevated_volume:
        return STRONG_BULLISH
    if falling and short_average < long_average and elevated_volume:
        return STRONG_BEARISH
    return NEUTRAL_TREND


def _average(values: tuple[Decimal, ...]) -> Decimal:
    """Mean of ``values``; must be called inside the signal context."""
    return sum(values, Decimal()) / len(values)
