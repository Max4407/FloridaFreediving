# Backend Reference

## Overview

The backend is a synchronous FastAPI application using SQLAlchemy 2, Pydantic 2, Alembic, and
PostgreSQL in production. SQLite is supported for lightweight local development and tests.
Route modules translate HTTP concerns; `services/` owns business rules; `models/` owns storage
shape; and `schemas/` owns request validation.

## Application modules

- `main.py` creates the app, includes the three routers, applies security/cache headers, exposes
  the data-free health check, serves built assets, and provides the SPA fallback.
- `config.py` loads environment variables through `Settings`. Production-safe validation rejects
  missing password hashes and the development signing secret when secure cookies are enabled.
- `database.py` builds the engine and session factory. `pool_pre_ping` detects stale connections;
  SQLite additionally enables foreign keys. `get_db()` scopes one session to a request.
- `api/public.py`, `api/auth.py`, and `api/officer.py` define the HTTP surface documented in
  [API reference](api.md).
- `exceptions/` defines service-level `NotFoundError` and `ConflictError` so route handlers can
  map business failures to HTTP responses.

## Dive and signup services

The medium and major functions in `services/dives.py` are:

| Function | Behavior |
| --- | --- |
| `public_id` | Generates a random nine-character member-facing dive identifier. |
| `get_dive` / `get_public_dive` | Resolve internal or public IDs, optionally adding `FOR UPDATE`, and raise `NotFoundError`. |
| `counts` | Aggregates confirmed and waitlisted totals for a dive. |
| `public_view` | Produces the PII-free public projection and next-signup status. |
| `create_signup` | Locks the dive, rejects past/duplicate signups, normalizes email, assigns capacity status and queue order, commits, and reports waitlist position. |
| `set_assignments` | Validates all officer IDs and replaces the dive’s assignment join rows. |
| `create_dive` / `update_dive` | Persist dive fields and officer assignments. Public IDs never change. |
| `serialize_signup` | Produces the protected roster representation. |
| `gear_report` | Separates confirmed/waitlist renters and calculates wetsuit, fin, mask, and weight-set demand. |
| `_allocate_fins` | Allocates each shoe size once across overlapping compatible ranges; unmatched demand becomes a zero-availability shortage row. |
| `_gear_row` | Creates a consistent inventory-demand record and confirmed shortage flag. |
| `detail_view` | Eager-loads related records and constructs the complete officer dive response and upcoming warnings. |
| `update_signup` | Revalidates member fields, normalizes email, and preserves status. |
| `promote_signup` | Locks signup and dive, enforces first-in queue and spare capacity, then confirms manually. |
| `save_inventory` | Adds inventory while preventing duplicate wetsuit sizes and duplicate unsized categories. Fin ranges may overlap. |

## Authentication services

`services/auth.py` contains the shared-login security boundary:

- `validate_origin` rejects state-changing requests from unknown origins.
- `session_serializer` binds signed values to the `officer-session-v1` salt.
- `create_session` signs the officer role and issue timestamp.
- `requireOfficer` validates the configured cookie and seven-day maximum age.
- `client_hash` irreversibly combines the signing secret and client address for rate-limit keys.
- `check_rate_limit` removes expired attempts and enforces five failures per 15-minute window.
- `verify_login` validates origin/rate limit, checks bcrypt, records failures, clears successful
  attempts, and returns a new signed session.

Changing the cookie signing secret intentionally logs out every officer. Changing the bcrypt
hash changes the accepted shared password without altering application data.

## Validation and transaction rules

Pydantic strips user-entered text and validates lengths, email format, positive capacity,
conditional carpool/gear fields, suit enum values, and half-step US shoe sizes from 1 through
18. Naive dive timestamps are interpreted as Eastern time.

Database constraints provide a second line of protection. Capacity decisions and promotion use
row locks on PostgreSQL. Commits occur at completed business operations; expected integrity
failures are rolled back before returning conflicts. Schema details are in
[Data model](data-model.md).

## Tests and quality checks

Pytest fixtures use an in-memory SQLite engine with foreign keys and dependency overrides.
Tests cover public privacy, conditional fields, duplicate emails, capacity/waitlist behavior,
authentication/origin checks, promotion ordering, warnings, overlapping fins, and cascade
deletion. Run `pytest` and `ruff check .` from `backend/`.

