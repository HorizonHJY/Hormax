<!--
SYNC IMPACT REPORT
==================
Version change: INITIAL → 1.0.0
Rationale: First ratification of Hormax constitution with comprehensive governance.

Principles established (7 core + 3 additional sections):
- I. Package Partitioning & Modularity
- II. Type Safety & Documentation Standards
- III. Logging & Error Handling
- IV. Module Organization & Import Hygiene
- V. Testing Discipline (pytest-based)
- VI. Semantic Versioning & Release Management
- VII. Data Responsibility & Reproducibility
+ Code Standards
+ Git Strategy & Workflow
+ Governance

Templates requiring updates:
- ✅ .specify/templates/plan-template.md (Constitution Check section validated)
- ✅ .specify/templates/spec-template.md (Requirements alignment validated)
- ✅ .specify/templates/tasks-template.md (Task categorization validated)

Follow-up items:
- RATIFICATION_DATE set to 2025-10-14 (today) as initial adoption
-->

# Hormax Constitution

## Core Principles

### I. Package Partitioning & Modularity

**Rules (NON-NEGOTIABLE)**:
- Hormax MUST be partitioned into three primary subpackages: `finance/`, `sql/`, and
  `dataframe/`.
- Each subpackage MUST be self-contained with minimal cross-dependencies.
- Subpackage rules:
  - `finance/`: Financial calculations, metrics, and domain logic. MAY depend on
    `dataframe/` for data structures but MUST NOT depend on `sql/`.
  - `sql/`: Database query building, connection management, ORM utilities. MUST be
    database-agnostic where possible.
  - `dataframe/`: DataFrame transformations, analytics utilities. MUST NOT depend on
    `finance/` or `sql/`.
- Shared utilities (logging, config, exceptions) MUST live in `hormax/core/` or
  `hormax/utils/`.
- New subpackages require architecture review and justification in the Complexity
  Tracking section of implementation plans.

**Rationale**: Clear separation ensures testability, reduces coupling, and allows
users to install/use only needed functionality in future modular distributions.

### II. Type Safety & Documentation Standards

**Rules (NON-NEGOTIABLE)**:
- All public functions and methods MUST have complete type annotations (PEP 484).
- All public APIs MUST include docstrings following Google or NumPy style
  (project-wide consistency enforced; default: Google style).
- Docstrings MUST include:
  - One-line summary
  - Args section with types (even if annotated)
  - Returns section with type and description
  - Raises section for all exceptions that can propagate to callers
  - Examples section for non-trivial functions
- Private functions SHOULD have docstrings if logic is non-obvious.
- Type checking MUST pass with `mypy --strict` (or equivalent) in CI.

**Rationale**: Strong typing prevents runtime errors, improves IDE support, and
serves as executable documentation. Comprehensive docstrings ensure maintainability
and ease onboarding.

### III. Logging & Error Handling

**Rules (NON-NEGOTIABLE)**:
- Use Python's `logging` module; NEVER use `print()` for application logs.
- Logging levels MUST follow this discipline:
  - `DEBUG`: Granular diagnostics (loop iterations, variable states)
  - `INFO`: High-level progress (function entry/exit, milestone events)
  - `WARNING`: Recoverable issues (deprecated API usage, fallback behavior)
  - `ERROR`: Operation failures that affect functionality
  - `CRITICAL`: System-level failures requiring immediate attention
- Custom exceptions MUST be defined in `hormax/exceptions.py` and MUST inherit from
  appropriate base classes (`ValueError`, `RuntimeError`, etc.).
- Error messages MUST be actionable: include context (parameters, state) and suggest
  remediation where applicable.
- NEVER catch exceptions silently; re-raise or log at ERROR level minimum.
- External API calls (database, HTTP) MUST use structured logging with request/response
  context.

**Rationale**: Consistent logging enables debugging in production. Actionable errors
reduce support burden and improve developer experience.

### IV. Module Organization & Import Hygiene

**Rules (NON-NEGOTIABLE)**:
- Folder and module names MUST be lowercase with underscores (`snake_case`).
- Avoid single-letter module names except for conventional abbreviations (e.g., `io`).
- Package structure follows:
  ```
  hormax/
  ├── core/          # Shared utilities (config, logging setup, base classes)
  ├── finance/       # Financial domain logic
  ├── sql/           # Database utilities
  ├── dataframe/     # DataFrame operations
  ├── exceptions.py  # All custom exceptions
  └── __init__.py    # Top-level exports
  ```
- Import rules:
  - Absolute imports REQUIRED (`from hormax.finance.metrics import calculate_irr`).
  - Relative imports FORBIDDEN except within same subpackage for internal modules.
  - Wildcard imports (`from module import *`) FORBIDDEN.
  - Circular imports MUST be resolved via refactoring (never via lazy imports).
- Configuration management:
  - YAML MUST be the primary config format.
  - Config files MUST live in `config/` at repo root or user-specified paths.
  - Environment variable overrides MUST follow pattern `HORMAX_<SECTION>_<KEY>`.
  - Config schema MUST be validated at load time (use `pydantic` or `marshmallow`).

**Rationale**: Strict import hygiene prevents namespace pollution and circular
dependency issues. YAML config provides readability and tooling support while
environment overrides enable deployment flexibility.

### V. Testing Discipline (pytest-based)

**Rules (NON-NEGOTIABLE)**:
- All tests MUST use `pytest` framework.
- Test layout mirrors source structure:
  ```
  tests/
  ├── unit/          # Isolated unit tests (no external deps)
  ├── integration/   # Cross-module/database/API tests
  ├── fixtures/      # Shared pytest fixtures
  └── data/          # Minimal reproducible test data (CSV, JSON)
  ```
- Unit tests MUST:
  - Run in isolation (no database, no network, no filesystem except temp dirs).
  - Use fixtures for common setup; NEVER duplicate setup code.
  - Cover edge cases, error paths, and boundary conditions.
- Integration tests MUST:
  - Use test databases (Docker containers or in-memory SQLite).
  - Clean up state after each test (fixtures with teardown).
- Test data MUST be:
  - Minimal: smallest dataset that reproduces scenario.
  - Anonymized: no real PII or proprietary data.
  - Versioned: committed to repo under `tests/data/`.
- Code coverage target: 85% minimum for new code (measured in CI).
- Tests MUST pass before any PR merge.

**Rationale**: pytest's fixture system reduces boilerplate. Strict isolation ensures
tests are reliable and fast. Reproducible test data prevents flaky tests.

### VI. Semantic Versioning & Release Management

**Rules (NON-NEGOTIABLE)**:
- Hormax MUST follow Semantic Versioning 2.0.0 (MAJOR.MINOR.PATCH).
- Version bumps:
  - MAJOR: Breaking API changes (remove/rename public functions, change signatures).
  - MINOR: New features, new subpackages, backward-compatible enhancements.
  - PATCH: Bug fixes, documentation updates, internal refactoring.
- Changelog:
  - MUST be maintained in `CHANGELOG.md` following Keep a Changelog format.
  - Each release MUST document: Added, Changed, Deprecated, Removed, Fixed, Security.
  - Changelog MUST be updated in the same PR that introduces the change.
- Release process:
  - Version bump MUST update `pyproject.toml` (or `setup.py`) and `CHANGELOG.md`.
  - Git tags MUST match version (e.g., `v1.2.3`).
  - CI MUST run full test suite + linting + type checking before release build.
  - Releases MUST be automated via CI hooks (GitHub Actions or equivalent).
  - Release artifacts MUST be published to PyPI with signed checksums.
- Pre-release versions (alpha, beta, rc) MUST use PEP 440 format (e.g., `1.0.0a1`).

**Rationale**: SemVer communicates compatibility guarantees. Automated releases reduce
human error. Changelog keeps stakeholders informed.

### VII. Data Responsibility & Reproducibility

**Rules (NON-NEGOTIABLE)**:
- Caching:
  - HTTP/API responses MUST be cached when safe (GET requests, idempotent operations).
  - Cache MUST respect TTL and invalidation rules.
  - Use `requests-cache` or equivalent; cache directory MUST be configurable.
- Rate limiting:
  - External API calls MUST implement rate limiting (configurable requests/second).
  - Use exponential backoff for retries (max 3 attempts default).
  - Rate limits MUST be logged at INFO level.
- Retries:
  - Transient failures (network errors, 5xx responses) MUST auto-retry.
  - Non-transient failures (4xx responses, auth errors) MUST NOT retry.
  - Retry behavior MUST be configurable via config file.
- Reproducibility:
  - Random seeds MUST be configurable and logged.
  - Data transformations MUST be deterministic unless explicitly random.
  - Notebooks/scripts using Hormax MUST document dependencies (requirements.txt,
    environment.yml).
  - Data provenance: Log source URLs, fetch timestamps, API versions.
- Data privacy:
  - NEVER log sensitive data (PII, API keys, passwords) even at DEBUG level.
  - Mask sensitive fields in structured logs.

**Rationale**: Responsible data handling prevents abuse, ensures reproducibility for
research/compliance, and protects user privacy.

## Code Standards

**Static Analysis**:
- Linting: `ruff` or `flake8` with project config (max line length: 100).
- Formatting: `black` with default settings (line length: 100).
- Import sorting: `isort` with black-compatible profile.
- Type checking: `mypy --strict` (no `type: ignore` without justification comment).

**Code Review**:
- All code MUST pass automated checks (lint, format, type, test) before human review.
- PRs MUST include test coverage for new code.
- Breaking changes MUST be flagged in PR description and require maintainer approval.

## Git Strategy & Workflow

**Branching Model**:
- Trunk-based development: `main` branch is always deployable.
- Feature branches: `feature/<issue-number>-<short-description>`.
- Hotfix branches: `hotfix/<issue-number>-<short-description>`.
- Release branches: `release/v<version>` (for release preparation only).

**Pull Request Checks (CI enforced)**:
- All tests pass (unit + integration).
- Code coverage ≥ 85% for changed files.
- Linting, formatting, type checking pass.
- No merge conflicts with `main`.
- At least one approving review from maintainer.

**Commit Message Style**:
- Follow Conventional Commits specification.
- Format: `<type>(<scope>): <subject>`
- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`.
- Examples:
  - `feat(finance): add IRR calculation function`
  - `fix(sql): handle NULL values in query builder`
  - `docs(readme): update installation instructions`
- Subject: imperative mood, lowercase, no period, max 72 chars.
- Body (optional): explain WHY, not WHAT (code shows what).
- Footer: reference issues (`Fixes #123`, `Relates to #456`).

## Governance

**Amendment Procedure**:
- Constitution changes require PR with:
  - Rationale document explaining why change is needed.
  - Impact analysis on existing code and workflows.
  - Migration plan if change breaks existing patterns.
  - Approval from 2+ maintainers.
- Version bump rules (for constitution itself):
  - MAJOR: Remove/redefine core principles, change governance model.
  - MINOR: Add new principles, expand guidance.
  - PATCH: Clarifications, typo fixes, formatting.

**Compliance Review**:
- All PRs MUST verify compliance with applicable principles (automated via CI where
  possible).
- Quarterly constitution review: assess if principles are being followed, identify
  gaps.
- Violations require either: (1) fix the code, or (2) justify complexity in plan and
  amend constitution.

**Complexity Justification**:
- Any deviation from constitution MUST be documented in implementation plan's
  Complexity Tracking table.
- Justification MUST explain: what rule is broken, why simpler alternative is
  insufficient, and mitigation plan.

**Version**: 1.0.0 | **Ratified**: 2025-10-14 | **Last Amended**: 2025-10-14
