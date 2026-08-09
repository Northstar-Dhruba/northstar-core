# Northstar Core

Northstar Core is the heart of the Northstar platform.

It contains all business logic used throughout the platform while remaining completely independent of any API, database, or user interface.

---

## Responsibilities

- Technical Indicators
- Trading Strategies
- Risk Management
- Portfolio Logic
- Signal Generation
- Position Sizing
- Backtesting Engine
- Performance Analytics
- Financial Models
- Shared Domain Models

---

## Non-Responsibilities

Northstar Core does **not** contain:

- FastAPI
- SQLAlchemy
- PostgreSQL
- HTTP APIs
- Authentication
- React
- Scheduler
- Notifications

---

## Design Principles

- Pure Python library
- No infrastructure dependencies
- Highly testable
- Modular architecture
- Strategy Plugin Architecture
- Reusable across applications

---

## Repository Structure

```
northstar_core/
tests/
```

---

## Future Modules

- Indicators
- Strategies
- Backtesting
- Portfolio
- Risk Engine
- AI Research
- Analytics

---

## License

Private