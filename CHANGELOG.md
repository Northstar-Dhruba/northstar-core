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
