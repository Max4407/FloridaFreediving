# System Architecture

## Purpose and boundaries

Florida Freediving manages club dive registration and officer coordination. Members use a
public, dive-specific signup link. Officers use a protected dashboard to manage dives,
participants, assignments, carpools, and shared loaner inventory. The first release has no
member accounts, individual officer identities, payments, attendance, automatic waitlist
promotion, or outbound email.

## Runtime topology

The production application artifact is one container. A Vite build produces static React assets,
and FastAPI serves those assets plus the JSON API from the same origin. Caddy terminates HTTPS
and proxies to the application container. PostgreSQL runs in a separate container on the same
EC2 host. Requests under `/api/*` are never handled by the SPA fallback. Local development runs
Vite and FastAPI separately; Vite proxies `/api` and `/health`, preserving the deployed request
model.

```text
Member or officer browser
          |
          v
 Route 53 / Elastic IP
          |
          v
 Caddy (automatic HTTPS)
          |
          v
 FastAPI container ---- serves ----> React static assets
          |
          +---- /api/* -------------> route/service layer
                                      |
                                      v
                              PostgreSQL container
```

See [Infrastructure](infrastructure/README.md) for the AWS resource mapping.

## Public signup flow

1. An officer creates a dive and shares `/signup?dive={publicId}`.
2. `SignupPage` fetches the public projection, which contains no roster or member PII.
3. The member supplies identity, optional carpool details, and optional rental sizes.
4. The backend normalizes the email, locks the dive row, checks for a duplicate and a past
   start time, then compares confirmed signups with capacity.
5. The signup is committed as `confirmed` or appended to the ordered `waitlisted` queue.

The `(dive_id, email)` database constraint is the final duplicate safeguard. PostgreSQL row
locking prevents simultaneous requests from overfilling the last confirmed space.

## Officer flow

`/dash` first checks `/api/auth/session`. A valid cookie opens the dashboard; otherwise the
login form is shown. The dashboard loads dives, officers, and inventory, then presents:

- a month calendar containing past and upcoming dives;
- dive details with separate confirmed and waitlisted lists;
- staffing, capacity, carpool, and gear information;
- dive, signup, officer, assignment, and inventory controls.

Waitlist promotion is manual, restricted to the first queued member, and allowed only when
capacity is available. Deleting a dive permanently cascades its signups and assignments.

## Gear and warning rules

A rental request represents one wetsuit, compatible fins, one mask, and one weight set.
Primary shortage warnings count confirmed renters only; waitlist demand is displayed
separately. Wetsuits are compared by `XS`–`XL`. Fin ranges may overlap; the allocation logic
assigns each diver to at most one compatible range and prioritizes the range with the lowest
maximum size. Identical ranges are combined for reporting. Inventory entries that reach zero
are removed through the dashboard.

Upcoming dives are flagged when they have fewer than two active assigned officers, confirmed
participants above capacity, or any confirmed gear shortage. Completed dives retain records
and suppress operational warnings until explicitly deleted.

## Security model

- The shared password is stored only as a bcrypt hash.
- Successful login issues a signed, seven-day, `HttpOnly`, `SameSite=Lax` cookie. Production
  uses the `__Host-` prefix and `Secure` flag.
- Protected state-changing requests must have an origin in `ALLOWED_ORIGINS`.
- Five failed login attempts per hashed client address within 15 minutes trigger rate limiting.
- API responses use `Cache-Control: no-store`; global headers restrict framing, MIME sniffing,
  referrers, content sources, and, under HTTPS, transport downgrade.
- Member PII appears only in protected officer responses and must not be logged.
- Rotating `SESSION_SECRET` invalidates every active officer session.

Detailed route and payload contracts are in the [API reference](backend/api.md).
