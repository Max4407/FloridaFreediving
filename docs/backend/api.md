# API Reference

## Conventions

All routes return JSON except successful `DELETE` operations, which return `204 No Content`.
Validation failures use FastAPI's `422` response. Application errors use
`{"detail": "message"}`. UUID fields are serialized as strings and timestamps as ISO 8601.

Officer routes require the signed officer cookie. All `POST`, `PUT`, `PATCH`, and `DELETE`
requests involved in authentication or officer operations must also send an `Origin` header
listed in `ALLOWED_ORIGINS`. Browsers do this automatically for the same-origin application.

## Public and health endpoints

### `GET /health`

Unauthenticated infrastructure health check. Returns `200` with `{"status":"ok"}`. It proves
the web process is responsive; it does not query the database or expose application data.

### `GET /api/public/dives/{publicId}`

Returns the member-safe view for a dive. `404` means the public ID does not exist.

```json
{
  "public_id": "Ab3xY91pq",
  "title": "Blue Heron Bridge",
  "description": "Meet by the east beach.",
  "location": "Riviera Beach, FL",
  "starts_at": "2030-09-12T12:00:00Z",
  "capacity": 12,
  "remaining": 3,
  "next_status": "confirmed"
}
```

`next_status` is `confirmed` while capacity remains and `waitlisted` when full. The response
never contains roster, email, carpool, or gear-request details.

### `POST /api/public/dives/{publicId}/signups`

Creates one signup. Returns `201`; it returns `404` for an unknown dive and `409` for a past
dive or an email already used for that dive.

```json
{
  "name": "Diver Name",
  "email": "diver@example.com",
  "needs_carpool": true,
  "pickup_location": "Campus recreation center",
  "needs_gear": true,
  "suit_size": "M",
  "shoe_size": 9.5
}
```

Names are 1–160 characters and emails are normalized to lowercase. If `needs_carpool` is true,
`pickup_location` is required; otherwise it is cleared. If `needs_gear` is true, `suit_size`
(`XS`, `S`, `M`, `L`, or `XL`) and a shoe size from 1–18 in 0.5 increments are required;
otherwise both are cleared.

```json
{
  "id": "6b7c2dc3-b4e6-4aeb-8843-cae08c223ccb",
  "status": "waitlisted",
  "waitlist_position": 2
}
```

`waitlist_position` is `null` for a confirmed signup.

## Authentication endpoints

### `POST /api/auth/login`

Accepts `{"password":"shared password"}` and returns `{"authenticated":true}`. Success sets
the seven-day officer session cookie. Incorrect credentials return `401`; an unapproved origin
returns `403`; five recent failures from the client produce `429` until the 15-minute window
passes. This endpoint does not require an existing session.

### `POST /api/auth/logout`

Requires officer access, deletes the session cookie, and returns `{"authenticated":false}`.

### `GET /api/auth/session`

Requires officer access and returns `{"authenticated":true}`. Missing, expired, or tampered
cookies return `401`. The frontend uses this route to restore dashboard state after navigation.

## Dive endpoints

### `GET /api/officer/dives`

Returns an array of full dive-detail objects ordered by `starts_at`. Optional ISO 8601 query
parameters `starts_after` (inclusive) and `starts_before` (exclusive) filter the calendar range.

### `POST /api/officer/dives`

Creates a dive and returns its full detail with `201`.

```json
{
  "title": "Morning Springs Dive",
  "description": "Bring water and certification cards.",
  "location": "Ginnie Springs, FL",
  "starts_at": "2030-10-05T08:00:00-04:00",
  "capacity": 16,
  "officer_ids": ["fca72300-a97b-469b-870f-816825c089a9"]
}
```

Capacity is 1–500. Text limits are 160 for title, 300 for location, and 5,000 for description.
Unknown officer IDs return `404` and no partial assignment is saved.

### `GET /api/officer/dives/{diveId}`

Returns one full detail object or `404`.

### `PATCH /api/officer/dives/{diveId}`

Accepts any subset of the create fields. Supplying `officer_ids` replaces all assignments;
omitting it preserves them. Lowering capacity below the confirmed count is allowed and creates
an upcoming warning. The public ID is immutable. Returns the updated detail or `404`.

### `DELETE /api/officer/dives/{diveId}`

Permanently deletes the dive and cascades signups and dive-officer assignments. Returns `204`
or `404`. The dashboard requires a detailed browser confirmation before calling this route.

## Full dive-detail response

The dive list, create, read, and update routes share this representation:

```json
{
  "id": "8affd84e-0d87-4371-9ee9-aa974b5e4c24",
  "public_id": "Ab3xY91pq",
  "title": "Blue Heron Bridge",
  "description": "Meet by the east beach.",
  "location": "Riviera Beach, FL",
  "starts_at": "2030-09-12T12:00:00Z",
  "capacity": 12,
  "confirmed_count": 1,
  "waitlist_count": 1,
  "officers": [{"id": "...", "name": "Officer Name"}],
  "assigned_officer_ids": ["..."],
  "confirmed": [{"id": "...", "name": "...", "email": "..."}],
  "waitlisted": [{"id": "...", "name": "...", "email": "..."}],
  "gear": [{
    "category": "wetsuit",
    "label": "M",
    "available": 3,
    "confirmed_needed": 2,
    "waitlisted_needed": 1,
    "shortage": false
  }],
  "warnings": ["Fewer than two active officers are assigned"]
}
```

Each roster object also contains `status`, `needs_carpool`, `pickup_location`, `needs_gear`,
`suit_size`, `shoe_size`, and `created_at`. `officers` includes active assignees only;
`assigned_officer_ids` retains active and inactive assignments for editing and history.

## Signup administration

### `PATCH /api/officer/signups/{signupId}`

Updates member details and returns the protected signup representation. This is a full member
details payload: `name` and `email` are required, and the carpool/gear fields follow the public
conditional rules. Status is preserved; use promotion for status changes. Duplicate email for
the same dive returns `409`; unknown signup returns `404`.

### `DELETE /api/officer/signups/{signupId}`

Permanently removes a signup and returns `204`, or `404` when missing. It does not automatically
promote the waitlist.

### `POST /api/officer/signups/{signupId}/promote`

Promotes a waitlisted signup and returns its protected representation. The request returns
`409` unless the signup is first in queue and confirmed count is below capacity. It returns
`404` when missing. Promotion does not send email.

## Officer endpoints

### `GET /api/officer/officers`

Returns officers alphabetically as `[{"id":"...","name":"...","active":true}]`.

### `POST /api/officer/officers`

Accepts `{"name":"Officer Name"}`, returns the created active officer with `201`, and returns
`409` for a duplicate name.

### `PATCH /api/officer/officers/{officerId}`

Accepts `name`, `active`, or both and returns the updated officer. Inactivation preserves past
assignments but removes the officer from active staffing counts. Missing IDs return `404` and
duplicate names return `409`.

## Inventory endpoints

Inventory responses contain `id`, `category`, `suit_size`, `min_shoe_size`, `max_shoe_size`, and
`quantity`.

### `GET /api/officer/inventory`

Returns every inventory row ordered by category. The dashboard hides zero-quantity legacy rows.

### `POST /api/officer/inventory`

Creates a row with `201`. Valid shapes are:

```json
{"category":"wetsuit","suit_size":"L","quantity":3}
{"category":"fins","min_shoe_size":7,"max_shoe_size":10.5,"quantity":2}
{"category":"mask","quantity":8}
{"category":"weight_set","quantity":6}
```

Fin bounds are 1–18 in 0.5 increments and may overlap other fin ranges. One row is allowed per
wetsuit size and per unsized category; duplicates return `409`. Quantity is 0–10,000.

### `PUT /api/officer/inventory/{itemId}`

Replaces an inventory row using one complete shape above and returns it. Category changes are
allowed if they do not violate uniqueness rules. Missing IDs return `404`; conflicts return
`409`. The dashboard normally calls `DELETE` instead of storing a final quantity of zero.

### `DELETE /api/officer/inventory/{itemId}`

Deletes an inventory row and returns `204`, or `404` when missing.

