# Repository Guidelines

## Plan

Reference docs/PLAN.md for overall project goals, plans, and specific details of how to implement. Always ask before modifying PLAN.md 

## Stack
- Backend: FastAPI (Python 3.12), Postgres via SQLAlchemy
- Frontend: React (Vite), plain CSS — no UI library
- Auth: single officer account, bcrypt hash stored in OFFICER_PASSWORD_HASH env var,
  signed session cookie (itsdangerous), httponly + secure + samesite=lax

## Project Structure & Module Organization
- frontend/
    - src/
        - components/
        - features/
        - hooks/
    - assets/
- backend/
    api/             # All FastAPI route logic
    services/        # Business logic lives here - validation etc
    repository/      # DB operations live here
    models/          # SQLAlchemy models
    schemas/         # Pydantic models
    exceptions/
    tests/
    main.py
- docs/
    PLAN.md

## Commands
- Backend dev server: `uvicorn main:app --reload`  (run from /backend)
- Frontend dev server: `npm run dev` (in /frontend)
- Run backend tests: `pytest`
- Lint: `ruff check .`


## Coding Style & Naming Conventions

Use UTF-8 files, final newlines, and consistent spaces rather than tabs. Choose descriptive names: `PascalCase` for types and classes, `camelCase` for functions and variables, and `snake_case` for documentation or asset filenames. Keep modules small and avoid unrelated refactors in focused changes.

## Testing Guidelines

- Mirror backend/ structure under backend/tests/
- Name test files test_<module>.py
- Cover happy-path, boundary, and failure cases; bug fixes need a regression test

## Commit & Pull Request Guidelines

Use short, imperative subjects, optionally following Conventional Commits, for example `feat: add dive-site search` or `fix: reject invalid depth values`. Keep each commit coherent.

Pull requests should explain the problem and solution, list verification performed, and link related issues. Include screenshots or recordings for visible UI changes and call out configuration, migration, or compatibility impacts. Keep PRs reviewable and ensure checks pass before requesting review.

## Security & Configuration

Never commit credentials, API keys, or personal diver data. Store local settings in ignored environment files, provide sanitized examples such as `.env.example`, and document every required variable in the `README.md`.


## Conventions
- All new backend routes go in backend/api/, not directly in main.py
- Never hardcode secrets — always read from environment variables
- All routes except member signup endpoints, `POST /api/auth/login`, and `GET /health` must use the `requireOfficer` cookie dependency
- Keep member-facing form endpoints public, no auth required

## Non-goals
- Don't add a multi-user auth system — this app only ever has one officer login
- Don't introduce a new frontend framework or state library without asking first

## Rule 1 — Think Before Coding

State assumptions explicitly. Ask rather than guess.

Push back when a simpler approach exists. Stop when confused.

## Rule 2 — Simplicity First

Minimum code that solves the problem. Nothing speculative.

No abstractions for single-use code.

## Rule 3 — Surgical Changes

Touch only what you must. Don't improve adjacent code.

Match existing style. Don't refactor what isn't broken.

## Rule 4 — Goal-Driven Execution

Define success criteria before implementation. Verify with the narrowest relevant check. If verification cannot run, say exactly why.

## Rule 5 — Surface conflicts, don't average them

If two patterns contradict, pick one (more recent / more tested).

Explain why. Flag the other for cleanup.

Don't blend conflicting patterns.

## Rule 6 — Read before you write

Before adding code, read exports, immediate callers, shared utilities.

If unsure why existing code is structured a certain way, ask.

## Rule 7 — Tests verify intent, not just behavior

Tests must encode WHY behavior matters, not just WHAT it does.

A test that can't fail when business logic changes is wrong.

## Rule 8 — Match the codebase's conventions, even if you disagree

Conformance > taste inside the codebase.

If you think a convention is harmful, surface it. Don't fork it silently.

## Rule 9 — (IMPORTANT) Pushback when appropriate

If a prompt has an idea that may be bad or fundamental misunderstanding, push back freely and explain reasoning. 

It is better to raise concerns than to implement fault or inefficient features.
