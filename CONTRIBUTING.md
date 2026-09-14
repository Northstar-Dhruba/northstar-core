# Contributing to northstar-core

## Branching

Create focused feature branches from the current integration branch. Use names such as `feature/<scope>` or `fix/<scope>`. Keep one product or engineering concern per branch.

## Commits

Use concise imperative commit subjects, for example `Add market observation contract tests`. Keep commits small, reviewable, and free of generated artifacts.

## Pull Requests

Pull requests should explain the change, its architectural boundary, tests run, and any remaining risk. Keep unrelated refactoring out of the change. At least one reviewer should verify Domain ownership and dependency direction.

## Validation

Run from this repository:

```powershell
uv run ruff check .
uv run ruff format --check .
uv run python -m pytest
uv lock --check
```

## Coding Standards

- Use Python 3.13 and the repository `uv` environment.
- Keep Core independent of API, Application, Infrastructure, and UI frameworks.
- Preserve immutable Value Object semantics with `@dataclass(frozen=True, slots=True)` where appropriate.
- Keep business meaning and validation in the owning Domain concept.
- Add focused contract tests for new or changed public Domain behavior.

## Review Expectations

Reviewers check behavior, invariants, public exports, dependency direction, test coverage, documentation, and accidental scope expansion. Architecture changes require explicit approval.
