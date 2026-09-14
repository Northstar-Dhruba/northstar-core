# Development Guide

## Environment Setup

Requirements:

- Python 3.13
- `uv`

Create or synchronize the repository environment:

```powershell
uv sync
```

## Development Commands

Run the full validation set:

```powershell
uv run ruff check .
uv run ruff format --check .
uv run python -m pytest
uv lock --check
```

Format the repository when required:

```powershell
uv run ruff format .
```

Run a focused test area:

```powershell
uv run python -m pytest tests/strategy
uv run python -m pytest tests/foundation/value_objects
```

## Common Workflow

1. Read the approved Domain or product change.
2. Make the smallest change in the owning Core module.
3. Add or update focused contract tests.
4. Run Ruff, formatting, tests, and lock validation.
5. Review the diff for scope, public exports, and generated files before opening a pull request.

Northstar Core must remain independent of API, Application, Infrastructure, and UI concerns.
