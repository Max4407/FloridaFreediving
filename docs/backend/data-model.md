# Data Model and Migrations

## Storage contract

SQLAlchemy models in `backend/models/entities.py` are the application mapping; Alembic revisions
in `backend/alembic/versions/` are the database change history. Production uses PostgreSQL and
stores timezone-aware timestamps. UUID primary keys are internal identifiers unless a route
explicitly uses a short public ID.

```text
dives 1 -------- * signups
  |
  *
dive_officers
  *
  |
officers

inventory       independent aggregate stock
login_attempts  independent short-lived security data
```

## Enums

- `SignupStatus`: `confirmed`, `waitlisted`.
- `SuitSize`: `XS`, `S`, `M`, `L`, `XL`.
- `GearCategory`: `wetsuit`, `fins`, `mask`, `weight_set`.

## `dives`

| Field | Meaning |
| --- | --- |
| `id` | UUID primary key used by protected routes and relationships. |
| `public_id` | Unique, indexed, random short ID used in member signup links. |
| `title`, `description`, `location` | Officer-managed display content. |
| `starts_at` | Indexed timezone-aware dive start. |
| `capacity` | Positive confirmed-participant limit. |
| `created_at`, `updated_at` | Server-managed audit timestamps. |

A dive owns `signups` and `assignments` with delete-orphan cascade. Permanent dive deletion
therefore removes those dependent records.

## `signups`

Each row belongs to one dive through `dive_id` with database `ON DELETE CASCADE`.

- `name` and normalized `email` identify the member for officer use.
- `(dive_id, email)` is unique, preventing duplicate registration even under concurrent writes.
- `status` and monotonically assigned `queue_order` implement confirmed/waitlisted ordering.
- `(dive_id, status, queue_order)` is indexed for roster and promotion queries.
- `needs_carpool` controls nullable `pickup_location`.
- `needs_gear` controls nullable `suit_size` and `shoe_size`.
- Shoe size is constrained to 1–18 in storage; Pydantic additionally requires half increments.
- `created_at` and `updated_at` record lifecycle timestamps.

Removing a signup does not reorder the queue and does not trigger automatic promotion.

## `officers` and `dive_officers`

`officers` has a UUID, unique name, and active flag. Officers are deactivated rather than
deleted, preserving history. `dive_officers` is a many-to-many join table with the composite
primary key `(dive_id, officer_id)`. Dive deletion cascades assignments; officer deletion is
restricted while assignments exist. The current API does not expose officer deletion.

## `inventory`

Inventory represents quantities rather than individually serialized equipment.

| Category | Size columns | Application uniqueness |
| --- | --- | --- |
| Wetsuit | `suit_size` only | One row per suit size |
| Fins | Inclusive `min_shoe_size` and `max_shoe_size` | Multiple and overlapping ranges allowed |
| Mask | No size columns | One row |
| Weight set | No size columns | One row |

`quantity` cannot be negative. The database ensures a fin minimum does not exceed its maximum;
Pydantic additionally enforces allowed category shapes, bounds, and half increments. The
dashboard deletes a record when its last unit is removed, allowing that category/size to be
added again cleanly.

## `login_attempts`

This table supports login throttling and contains an integer key, indexed HMAC-like client hash,
and indexed attempt time. It stores neither raw IP addresses nor passwords. Old rows are removed
during later login attempts after the 15-minute window.

## Request schemas

Pydantic classes in `backend/schemas/payloads.py` form the input boundary:

| Schema | Used for |
| --- | --- |
| `LoginInput` | Shared password submission with a 256-character maximum. |
| `SignupCreate` | Public registration and its conditional carpool/gear validation. |
| `SignupUpdate` | Officer correction of complete member details; status is not changed by the service. |
| `DiveCreate` | Required dive fields and an optional officer UUID list. |
| `DiveUpdate` | Partial dive changes, including optional full assignment replacement. |
| `OfficerCreate` | Trimmed, nonempty officer name. |
| `OfficerUpdate` | Optional name and/or active-state changes. |
| `InventoryInput` | Category-specific inventory shape and quantity/range validation. |

Input schemas deliberately do not double as public response schemas. Service serializers build
explicit public and officer projections, making it harder to expose new database fields or PII
accidentally when a model grows.

## Migration lifecycle

`backend/alembic.ini` and `backend/alembic/env.py` load the same `DATABASE_URL` as the app. The
initial `0001` revision creates all tables, enums, indexes, foreign keys, and checks. New model
changes require a new forward Alembic revision; never edit an already-applied production
revision.

The production container runs `alembic upgrade head` before starting Uvicorn. A migration
failure therefore prevents an incompatible application version from becoming healthy. Review
data-destructive migrations and backup/rollback implications before deployment. SQLite is a
development convenience, not a substitute for testing PostgreSQL transaction and locking
behavior.
