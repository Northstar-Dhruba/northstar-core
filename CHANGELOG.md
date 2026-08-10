# Changelog

All notable changes to northstar-core are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
