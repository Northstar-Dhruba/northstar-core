"""Factual market observations used to generate an AssetAnalysis."""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.domain.value_objects import ListingReference
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import Currency, PointInTime, Price, Quantity

_LONG_WINDOW_LENGTH = 20


class InvalidMarketObservationContextError(ValidationError):
    """Raised when a MarketObservationContext value is invalid."""


def _validate_listing_reference(value: ListingReference) -> ListingReference:
    if value is None:
        raise InvalidMarketObservationContextError(
            "MarketObservationContext listing reference cannot be None."
        )
    if not isinstance(value, ListingReference):
        raise InvalidMarketObservationContextError(
            "MarketObservationContext listing reference must be a ListingReference value."
        )
    return value


def _validate_point_in_time(value: PointInTime) -> PointInTime:
    if value is None:
        raise InvalidMarketObservationContextError(
            "MarketObservationContext observed-at cannot be None."
        )
    if not isinstance(value, PointInTime):
        raise InvalidMarketObservationContextError(
            "MarketObservationContext observed-at must be a PointInTime value."
        )
    return value


def _validate_price(value: Price, field_name: str) -> Price:
    if value is None:
        raise InvalidMarketObservationContextError(
            f"MarketObservationContext {field_name} cannot be None."
        )
    if not isinstance(value, Price):
        raise InvalidMarketObservationContextError(
            f"MarketObservationContext {field_name} must be a Price value."
        )
    return value


def _validate_denominated_price(value: Price, field_name: str, currency: Currency) -> Price:
    price = _validate_price(value, field_name)
    if price.currency != currency:
        raise InvalidMarketObservationContextError(
            f"MarketObservationContext {field_name} currency "
            "must match the market observation currency."
        )
    return price


def _validate_volume(value: Quantity, field_name: str) -> Quantity:
    if value is None:
        raise InvalidMarketObservationContextError(
            f"MarketObservationContext {field_name} cannot be None."
        )
    if not isinstance(value, Quantity):
        raise InvalidMarketObservationContextError(
            f"MarketObservationContext {field_name} must be a Quantity value."
        )
    return value


def _validate_price_history(value: tuple[Price, ...], currency: Currency) -> tuple[Price, ...]:
    if not isinstance(value, tuple):
        raise InvalidMarketObservationContextError(
            "MarketObservationContext recent closes must be a tuple."
        )
    if len(value) < _LONG_WINDOW_LENGTH:
        raise InvalidMarketObservationContextError(
            "MarketObservationContext recent closes must contain at least 20 observations."
        )
    return tuple(_validate_denominated_price(price, "recent closes", currency) for price in value)


def _validate_volume_history(value: tuple[Quantity, ...]) -> tuple[Quantity, ...]:
    if not isinstance(value, tuple):
        raise InvalidMarketObservationContextError(
            "MarketObservationContext recent volumes must be a tuple."
        )
    if len(value) < _LONG_WINDOW_LENGTH:
        raise InvalidMarketObservationContextError(
            "MarketObservationContext recent volumes must contain at least 20 observations."
        )
    return tuple(_validate_volume(volume, "recent volumes") for volume in value)


@dataclass(frozen=True, slots=True)
class MarketObservationContext:
    """Complete factual daily market context for one listed asset at one point in time.

    The market observation currency is the denomination of ``latest_price``.
    Every other Price fact must use that same currency. Quantity values remain
    undenominated and are never currency-checked.
    """

    listing_reference: ListingReference
    observed_at: PointInTime
    latest_price: Price
    previous_close: Price
    latest_volume: Quantity
    daily_high: Price
    daily_low: Price
    recent_closes: tuple[Price, ...]
    recent_volumes: tuple[Quantity, ...]

    def __post_init__(self) -> None:
        listing_reference = _validate_listing_reference(self.listing_reference)
        latest_price = _validate_price(self.latest_price, "latest price")
        currency = latest_price.currency

        previous_close = _validate_denominated_price(
            self.previous_close, "previous close", currency
        )
        daily_high = _validate_denominated_price(self.daily_high, "daily high", currency)
        daily_low = _validate_denominated_price(self.daily_low, "daily low", currency)

        recent_closes = _validate_price_history(self.recent_closes, currency)
        recent_volumes = _validate_volume_history(self.recent_volumes)
        if len(recent_closes) != len(recent_volumes):
            raise InvalidMarketObservationContextError(
                "MarketObservationContext recent closes and volumes must have equal lengths."
            )

        if daily_low > daily_high:
            raise InvalidMarketObservationContextError(
                "MarketObservationContext daily low cannot exceed daily high."
            )

        object.__setattr__(self, "listing_reference", listing_reference)
        object.__setattr__(self, "observed_at", _validate_point_in_time(self.observed_at))
        object.__setattr__(self, "latest_price", latest_price)
        object.__setattr__(self, "previous_close", previous_close)
        object.__setattr__(
            self, "latest_volume", _validate_volume(self.latest_volume, "latest volume")
        )
        object.__setattr__(self, "daily_high", daily_high)
        object.__setattr__(self, "daily_low", daily_low)
        object.__setattr__(self, "recent_closes", recent_closes)
        object.__setattr__(self, "recent_volumes", recent_volumes)
