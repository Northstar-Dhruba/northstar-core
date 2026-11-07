"""Versioned synthetic inputs for equity recommendation formation (EI4-D4, ADR-020).

Every input that EI-4 cannot yet take from an approved source is an explicit,
versioned synthetic value:

- ``EquitySyntheticVersion`` names one synthetic policy, schedule or reference.
  It must begin ``synthetic-``, the convention EI3-D5 established, so a
  synthetic value can never pass for an approved one.
- ``EquityPriceIncrement`` is the price grid every level is aligned to. It is a
  synthetic reference, not an exchange tick size (EI0-D13 is pending).
- ``EquitySyntheticGenerationPolicy`` holds the entry-zone offsets, the target
  risk multiple and the minimum net reward-to-risk (EI0-D14, EI4-D3).
- ``EquitySyntheticRiskPolicy`` holds model capital and the per-recommendation
  risk and exposure fractions (EI0-D10, EI0-D11 are pending).

Numeric parameters must be Decimal instances. A float, int, str or bool is
refused rather than converted, and every Decimal is canonicalized, so ``1.50``
and ``1.5`` are one value. Nothing has a default: a missing parameter is a
construction error. None of these values is an exchange fact, a broker tariff
or an approved trading parameter, and changing any of them needs a new version.
Core sees one value at a time and cannot detect a version reused with different
content; that is a responsibility of later Application persistence.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import Currency, Money
from northstar_core.recommendations.equity._exact import require_decimal, text

_SYNTHETIC_PREFIX = "synthetic-"


class InvalidEquitySyntheticVersionError(ValidationError):
    """Raised when an EquitySyntheticVersion is invalid."""


class InvalidEquityPriceIncrementError(ValidationError):
    """Raised when an EquityPriceIncrement is invalid."""


class InvalidEquitySyntheticGenerationPolicyError(ValidationError):
    """Raised when an EquitySyntheticGenerationPolicy is invalid."""


class InvalidEquitySyntheticRiskPolicyError(ValidationError):
    """Raised when an EquitySyntheticRiskPolicy is invalid."""


@dataclass(frozen=True, slots=True)
class EquitySyntheticVersion:
    """The name and version of one synthetic policy, schedule or reference.

    Invariants:
        - It begins ``synthetic-`` and names something after the prefix.
        - It carries no leading or trailing whitespace: it is never trimmed.
    """

    value: str

    def __post_init__(self) -> None:
        value = self.value
        if not isinstance(value, str):
            raise InvalidEquitySyntheticVersionError("EquitySyntheticVersion must be a string.")
        if value != value.strip():
            raise InvalidEquitySyntheticVersionError(
                "EquitySyntheticVersion must not have surrounding whitespace."
            )
        if not value.startswith(_SYNTHETIC_PREFIX) or len(value) == len(_SYNTHETIC_PREFIX):
            raise InvalidEquitySyntheticVersionError(
                "EquitySyntheticVersion must begin 'synthetic-' and name the version after it."
            )

    def __str__(self) -> str:
        return self.value


def _require_version(value: object, error: type[ValidationError], owner: str) -> None:
    if not isinstance(value, EquitySyntheticVersion):
        raise error(f"{owner} version must be an EquitySyntheticVersion.")


@dataclass(frozen=True, slots=True)
class EquityPriceIncrement:
    """The synthetic price grid every level is aligned to.

    A positive Decimal under a synthetic reference version. It is not evidence
    of the exchange's tick size for any listing.
    """

    amount: Decimal
    version: EquitySyntheticVersion

    def __post_init__(self) -> None:
        _require_version(self.version, InvalidEquityPriceIncrementError, "EquityPriceIncrement")
        amount = require_decimal(
            self.amount,
            "EquityPriceIncrement amount",
            InvalidEquityPriceIncrementError,
            allow_zero=False,
        )
        object.__setattr__(self, "amount", amount)

    def document(self) -> dict[str, Any]:
        """Return the canonical content."""
        return {"version": self.version.value, "amount": text(self.amount)}


@dataclass(frozen=True, slots=True)
class EquitySyntheticGenerationPolicy:
    """Synthetic entry-zone, target and reward-to-risk parameters (EI0-D14, EI4-D3).

    - ``entry_offset_below`` and ``entry_offset_above`` are fractions of the
      signal close: the zone is ``[close * (1 - below), close * (1 + above)]``
      before inward alignment. ``below`` is less than one, so the zone stays
      positive. Both may be zero.
    - ``target_risk_multiple`` is the target's distance above the worst entry,
      in units of worst-entry risk per share.
    - ``minimum_net_reward_to_risk`` is the least acceptable ratio of net
      modeled reward to net modeled risk for the sized quantity.
    """

    version: EquitySyntheticVersion
    entry_offset_below: Decimal
    entry_offset_above: Decimal
    target_risk_multiple: Decimal
    minimum_net_reward_to_risk: Decimal

    def __post_init__(self) -> None:
        error = InvalidEquitySyntheticGenerationPolicyError
        _require_version(self.version, error, "EquitySyntheticGenerationPolicy")
        name = "EquitySyntheticGenerationPolicy"
        values = {
            "entry_offset_below": require_decimal(
                self.entry_offset_below,
                f"{name} entry offset below",
                error,
                allow_zero=True,
                below_one=True,
            ),
            "entry_offset_above": require_decimal(
                self.entry_offset_above, f"{name} entry offset above", error, allow_zero=True
            ),
            "target_risk_multiple": require_decimal(
                self.target_risk_multiple, f"{name} target risk multiple", error, allow_zero=False
            ),
            "minimum_net_reward_to_risk": require_decimal(
                self.minimum_net_reward_to_risk,
                f"{name} minimum net reward to risk",
                error,
                allow_zero=False,
            ),
        }
        for field_name, value in values.items():
            object.__setattr__(self, field_name, value)

    def document(self) -> dict[str, Any]:
        """Return the canonical content."""
        return {
            "version": self.version.value,
            "entry_offset_below": text(self.entry_offset_below),
            "entry_offset_above": text(self.entry_offset_above),
            "target_risk_multiple": text(self.target_risk_multiple),
            "minimum_net_reward_to_risk": text(self.minimum_net_reward_to_risk),
        }


@dataclass(frozen=True, slots=True)
class EquitySyntheticRiskPolicy:
    """Synthetic model capital and per-recommendation budgets.

    - ``model_capital`` is a positive model input. It is not a broker balance or
      buying power, and no leverage or margin is modelled.
    - ``risk_fraction`` (0 < x <= 1) of model capital bounds the net modeled
      loss at the stop, costs included.
    - ``exposure_fraction`` (0 < x <= 1) of model capital bounds the entry
      notional at the worst entry.
    """

    version: EquitySyntheticVersion
    model_capital: Money
    risk_fraction: Decimal
    exposure_fraction: Decimal

    def __post_init__(self) -> None:
        error = InvalidEquitySyntheticRiskPolicyError
        _require_version(self.version, error, "EquitySyntheticRiskPolicy")
        if not isinstance(self.model_capital, Money):
            raise error("EquitySyntheticRiskPolicy model capital must be Money.")
        if self.model_capital.amount <= 0:
            raise error("EquitySyntheticRiskPolicy model capital must be greater than zero.")
        name = "EquitySyntheticRiskPolicy"
        object.__setattr__(
            self,
            "risk_fraction",
            require_decimal(
                self.risk_fraction,
                f"{name} risk fraction",
                error,
                allow_zero=False,
                at_most_one=True,
            ),
        )
        object.__setattr__(
            self,
            "exposure_fraction",
            require_decimal(
                self.exposure_fraction,
                f"{name} exposure fraction",
                error,
                allow_zero=False,
                at_most_one=True,
            ),
        )

    @property
    def currency(self) -> Currency:
        """Return the model capital's currency."""
        return self.model_capital.currency

    def document(self) -> dict[str, Any]:
        """Return the canonical content."""
        return {
            "version": self.version.value,
            "model_capital": text(self.model_capital.amount),
            "currency": self.currency.value,
            "risk_fraction": text(self.risk_fraction),
            "exposure_fraction": text(self.exposure_fraction),
        }
