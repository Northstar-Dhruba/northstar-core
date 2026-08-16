# Changelog

All notable changes to northstar-core are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Foundation – Measurement Family Completion

### Added

- `Quantity` value object in `foundation.value_objects`.
- `Percentage` value object in `foundation.value_objects`.
- `InvalidQuantityError` and `InvalidPercentageError` in `foundation.exceptions.validation`.
- Quantity and Percentage contract test suites at `tests/foundation/value_objects/test_quantity.py` and `tests/foundation/value_objects/test_percentage.py`.

### Engineering

- Completed the Measurement Family as an approved Foundation Value Object family.
- Established `Quantity` as the Measurement Family root.
- Established `Percentage` as the second approved Measurement family member.
- Extended the approved Foundation Value Object family beyond the Identity baseline.

### Documentation

- Updated the Reference Implementation Registry.
- Formalized the Measurement Family status as complete.

### Foundation – Financial Family Initiation

### Added

- `Currency` Value Object in `foundation.value_objects`.
- `InvalidCurrencyError` in `foundation.exceptions.validation`.
- Currency contract test suite at `tests/foundation/value_objects/test_currency.py`.

### Engineering

- Established `Currency` as the Financial Family Root.
- Introduced the Financial Family.
- Extended the Foundation Value Object Family.
- Validated structural denomination semantics independent of registry membership.

### Documentation

- Updated the Reference Implementation Registry.
- Updated Foundation Family status.

### Foundation – Financial Family Expansion

### Added

- `Price` Value Object in `foundation.value_objects`.
- `InvalidPriceError` in `foundation.exceptions.validation`.
- `CurrencyMismatchError` in `foundation.exceptions.validation`.
- Price contract test suite at `tests/foundation/value_objects/test_price.py`.

### Engineering

- Approved the first composed Foundation Value Object.
- Established the composed Financial Value Object implementation pattern.
- Extended the Financial Family.
- Validated currency-aware business operations.
- Validated composed value object contract testing.

### Documentation

- Updated Reference Implementation Registry.
- Updated Financial Family implementation status.

### Foundation – Financial Family Completion

### Added

- `Money` Value Object in `foundation.value_objects`.
- `InvalidMoneyError` in `foundation.exceptions.validation`.
- Money contract test suite at `tests/foundation/value_objects/test_money.py`.

### Engineering

- Completed the Financial Family.
- Approved `Money` as the Financial Family financial-state value object.
- Established the complete composed Financial Value Object pattern.
- Completed the Financial Family implementation.
- Validated composed Financial Value Object semantics.

### Documentation

- Updated Reference Implementation Registry.
- Updated Financial Family status.

### Foundation – Temporal Family and Foundation Completion

### Added

- `Timeframe` Value Object in `foundation.value_objects`.
- `InvalidTimeframeError` in `foundation.exceptions.validation`.
- Timeframe contract test suite at `tests/foundation/value_objects/test_timeframe.py`.

### Engineering

- Completed the Temporal Family.
- Approved `Timeframe` as the Temporal Family Root.
- Completed the Foundation package.
- Validated closed-vocabulary temporal semantics.
- Completed Foundation implementation and contract verification.

### Documentation

- Updated Reference Implementation Registry.
- Updated Foundation Family status.
- Updated Foundation completion status.

### Core Domain – Instrument

#### Added

- Instrument entity.
- InvalidInstrumentError.
- Instrument Reference Entity Contract Test Suite.

#### Engineering

- Established Instrument as the first Core Domain Entity.
- Established Instrument as the first approved Core Domain Reference Entity.
- Established the Core Domain Entity implementation pattern.
- Validated Instrument against ADR-005.
- Completed Instrument implementation and contract verification.

#### Documentation

- Added the Core Domain Reference Implementation Registry.
- Updated Core Domain implementation status.

### Core Domain – Exchange

#### Added

- Exchange entity.
- InvalidExchangeError.
- Exchange Reference Entity Contract Test Suite.

#### Engineering

- Established Exchange as the second approved Core Domain Entity.
- Established Exchange as the second approved Core Domain Reference Entity.
- Verified Exchange against ADR-005.
- Completed Exchange implementation and contract verification.
- Preserved the approved Instrument / Exchange / Listing boundaries.

#### Documentation

- Updated the Core Domain Reference Implementation Registry.
- Updated Core Domain implementation progress.

---

## [0.2.1] — 2026-08-11

### Foundation – ExchangeCode Reference Value Object

### Added

- `ExchangeCode` value object in `foundation.value_objects`.
- `InvalidExchangeCodeError` in `foundation.exceptions.validation`.
- ExchangeCode contract test suite at `tests/foundation/value_objects/test_exchange_code.py`.

### Engineering

- ExchangeCode designated as Northstar Reference Value Object v1.0.
- Extended the Northstar Reference Value Object Family.
- Verified Reference-First Engineering workflow across multiple Value Objects.

### Documentation

- Updated Reference Implementation Registry.

---

## [0.2.0] — 2026-08-10

### Foundation – Symbol Reference Implementation

### Added

- `Symbol` value object in `foundation.value_objects`.
- `ValidationError` and `InvalidSymbolError` exception hierarchy in `foundation.exceptions.validation`.
- Reference contract test suite at `tests/foundation/value_objects/test_symbol.py`.

### Engineering

- Established Northstar Reference Value Object v1.0 (`Symbol`).
- Established Northstar Value Object Testing Standard v1.0.

### Documentation

- Added Reference Implementation Registry at `docs/engineering/registry/Reference-Implementations.md`.
- Updated ES-002 with the Official Reference Implementations section.

---

## [0.1.0] — 2026-08-10

### Project Zero

### Added

- Initial repository structure.
- Foundation package skeleton (`enums`, `exceptions`, `identifiers`, `protocols`, `result`, `value_objects`).
