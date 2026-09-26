"""Factual futures observations used to generate a FuturesAssetAnalysis.

This is the futures parallel of MarketObservationContext. The two are not
unified, and the reason is representability rather than taste: the equity
context stores every observation as a Price, and Price refuses a negative
amount. Futures quotations go negative, which is why QuoteValue exists, so the
equity context could not hold this data whatever its field names were.

Nothing here carries a currency. A quotation is a number in its product's own
convention -- index points for ES, points of par for ZB -- and stamping a
Currency on it would assert something false. There is likewise no positivity
rule: negative and zero quotations are ordinary facts.

The subject is a FuturesContract and nothing else. No listing reference, no
provider symbol, no session-calendar detail: the calendar decided which bars
exist before this value was built, and repeating that decision here would give
it two homes.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.derivatives import QuoteValue
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime, Quantity, Timeframe
from northstar_core.futures import FuturesContract

_LONG_WINDOW_LENGTH = 20


class InvalidFuturesMarketObservationContextError(ValidationError):
    """Raised when a FuturesMarketObservationContext value is invalid."""


def _validate_contract(value: FuturesContract) -> FuturesContract:
    if value is None:
        raise InvalidFuturesMarketObservationContextError(
            "FuturesMarketObservationContext contract cannot be None."
        )
    if not isinstance(value, FuturesContract):
        raise InvalidFuturesMarketObservationContextError(
            "FuturesMarketObservationContext contract must be a FuturesContract value."
        )
    return value


def _validate_timeframe(value: Timeframe) -> Timeframe:
    if value is None:
        raise InvalidFuturesMarketObservationContextError(
            "FuturesMarketObservationContext timeframe cannot be None."
        )
    if not isinstance(value, Timeframe):
        raise InvalidFuturesMarketObservationContextError(
            "FuturesMarketObservationContext timeframe must be a Timeframe value."
        )
    return value


def _validate_observed_at(value: PointInTime) -> PointInTime:
    if value is None:
        raise InvalidFuturesMarketObservationContextError(
            "FuturesMarketObservationContext observed-at cannot be None."
        )
    if not isinstance(value, PointInTime):
        raise InvalidFuturesMarketObservationContextError(
            "FuturesMarketObservationContext observed-at must be a PointInTime value."
        )
    return value


def _validate_quote(value: QuoteValue, field_name: str) -> QuoteValue:
    if value is None:
        raise InvalidFuturesMarketObservationContextError(
            f"FuturesMarketObservationContext {field_name} cannot be None."
        )
    if not isinstance(value, QuoteValue):
        raise InvalidFuturesMarketObservationContextError(
            f"FuturesMarketObservationContext {field_name} must be a QuoteValue."
        )
    return value


def _validate_volume(value: Quantity, field_name: str) -> Quantity:
    if value is None:
        raise InvalidFuturesMarketObservationContextError(
            f"FuturesMarketObservationContext {field_name} cannot be None."
        )
    if not isinstance(value, Quantity):
        raise InvalidFuturesMarketObservationContextError(
            f"FuturesMarketObservationContext {field_name} must be a Quantity value."
        )
    return value


def _validate_quote_history(value: tuple[QuoteValue, ...]) -> tuple[QuoteValue, ...]:
    if not isinstance(value, tuple):
        raise InvalidFuturesMarketObservationContextError(
            "FuturesMarketObservationContext recent closes must be a tuple."
        )
    if len(value) < _LONG_WINDOW_LENGTH:
        raise InvalidFuturesMarketObservationContextError(
            "FuturesMarketObservationContext recent closes must contain at least "
            f"{_LONG_WINDOW_LENGTH} observations."
        )
    return tuple(_validate_quote(quote, "recent closes") for quote in value)


def _validate_volume_history(value: tuple[Quantity, ...]) -> tuple[Quantity, ...]:
    if not isinstance(value, tuple):
        raise InvalidFuturesMarketObservationContextError(
            "FuturesMarketObservationContext recent volumes must be a tuple."
        )
    if len(value) < _LONG_WINDOW_LENGTH:
        raise InvalidFuturesMarketObservationContextError(
            "FuturesMarketObservationContext recent volumes must contain at least "
            f"{_LONG_WINDOW_LENGTH} observations."
        )
    return tuple(_validate_volume(volume, "recent volumes") for volume in value)


@dataclass(frozen=True, slots=True)
class FuturesMarketObservationContext:
    """Immutable factual futures observations at one decision instant.

    The twenty-observation minimum is a strategy requirement, not a market one:
    the signal logic compares a short moving average against a twenty-
    observation long average, so fewer observations cannot produce a signal at
    all. It says nothing about the calendar, and the observations need not be
    contiguous sessions -- a sparse futures series is ordinary, and the series
    itself already accounts for weekends, holidays and early closes.

    ``recent_closes`` and ``recent_volumes`` must be the same length, because
    they describe the same observations and a mismatch would silently pair a
    close with another observation's volume.

    Invariants:
        - The contract is the sole subject identity.
        - session_low <= latest_quote <= session_high.
        - At least twenty recent closes and volumes, of equal length.
        - No currency is stored and none is validated.
        - Negative and zero quotations are valid.
    """

    contract: FuturesContract
    timeframe: Timeframe
    observed_at: PointInTime
    latest_quote: QuoteValue
    previous_close: QuoteValue
    latest_volume: Quantity
    session_high: QuoteValue
    session_low: QuoteValue
    recent_closes: tuple[QuoteValue, ...]
    recent_volumes: tuple[Quantity, ...]

    def __post_init__(self) -> None:
        contract = _validate_contract(self.contract)
        timeframe = _validate_timeframe(self.timeframe)
        observed_at = _validate_observed_at(self.observed_at)
        latest_quote = _validate_quote(self.latest_quote, "latest quote")
        previous_close = _validate_quote(self.previous_close, "previous close")
        latest_volume = _validate_volume(self.latest_volume, "latest volume")
        session_high = _validate_quote(self.session_high, "session high")
        session_low = _validate_quote(self.session_low, "session low")
        recent_closes = _validate_quote_history(self.recent_closes)
        recent_volumes = _validate_volume_history(self.recent_volumes)

        if len(recent_closes) != len(recent_volumes):
            raise InvalidFuturesMarketObservationContextError(
                "FuturesMarketObservationContext recent closes and recent volumes "
                "must describe the same observations."
            )
        if session_low > session_high:
            raise InvalidFuturesMarketObservationContextError(
                "FuturesMarketObservationContext session low must not exceed session high."
            )
        if latest_quote < session_low or latest_quote > session_high:
            raise InvalidFuturesMarketObservationContextError(
                "FuturesMarketObservationContext latest quote must fall within "
                "the session high and low."
            )

        object.__setattr__(self, "contract", contract)
        object.__setattr__(self, "timeframe", timeframe)
        object.__setattr__(self, "observed_at", observed_at)
        object.__setattr__(self, "latest_quote", latest_quote)
        object.__setattr__(self, "previous_close", previous_close)
        object.__setattr__(self, "latest_volume", latest_volume)
        object.__setattr__(self, "session_high", session_high)
        object.__setattr__(self, "session_low", session_low)
        object.__setattr__(self, "recent_closes", recent_closes)
        object.__setattr__(self, "recent_volumes", recent_volumes)

    def __str__(self) -> str:
        return f"{self.contract} {self.timeframe} @ {self.observed_at} {self.latest_quote}"

    def __repr__(self) -> str:
        return (
            "FuturesMarketObservationContext("
            f"contract={self.contract!r}, "
            f"timeframe={self.timeframe!r}, "
            f"observed_at={self.observed_at!r}, "
            f"latest_quote={self.latest_quote!r}, "
            f"previous_close={self.previous_close!r}, "
            f"latest_volume={self.latest_volume!r}, "
            f"session_high={self.session_high!r}, "
            f"session_low={self.session_low!r}, "
            f"recent_closes={self.recent_closes!r}, "
            f"recent_volumes={self.recent_volumes!r}"
            ")"
        )
