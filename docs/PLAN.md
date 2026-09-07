# Florida Freediving Web Application Plan

## Goal

Build a responsive public dive-signup form and a password-protected officer dashboard using React/Vite, FastAPI, SQLAlchemy, and PostgreSQL.

## Member Experience

- Publish each dive at `/signup?dive={publicId}` with its title, description, location, Eastern date/time, availability, and signup status.
- Collect name, email, carpool needs, and pickup location. Renters also provide wetsuit size (`XS`–`XL`) and US unisex shoe size and request a wetsuit, fins, mask, and weight set.
- Confirm members up to capacity, then add submissions to an ordered waitlist. Enforce one normalized email per dive.
- Keep rosters and contact details private. Officers handle corrections and withdrawals.

## Officer Experience

- Protect `/dash` and all management pages with the shared officer password and a seven-day signed cookie.
- Show past and upcoming dives in a month calendar. Dive details include confirmed members, waitlist, carpool requests, officer assignments, capacity, and gear demand.
- Warn when an upcoming dive has fewer than two active officers, exceeds capacity, or lacks any required gear. Confirmed demand drives warnings; waitlist demand is shown separately.
- Allow officers to create, edit, and permanently delete dives; edit/remove signups; manually promote waitlisted members; manage officer names; and update inventory.

## Data and Rules

- Store dives, signups, officers, assignments, and inventory in PostgreSQL with Alembic migrations.
- Use random short public dive IDs and internal UUIDs. Store times in UTC and display them in `America/New_York`.
- Track wetsuits by size, fins by non-overlapping inclusive shoe-size ranges, and masks/weight sets by quantity.
- Serialize signup and promotion operations so concurrent requests cannot exceed capacity.
- Retain completed dives and PII until an officer explicitly deletes the dive.

## Delivery

1. Scaffold the database, API, authentication, and local environment.
2. Implement public signup and transactional waitlisting.
3. Implement the calendar, dive details, warnings, and officer management workflows.
4. Add the production container, Terraform AWS infrastructure, CI/CD, monitoring, backups, and operational documentation.

Production uses a single container on AWS ECS Express Mode, an encrypted private RDS PostgreSQL database, ECR, Route 53/ACM, Secrets Manager, and CloudWatch. Terraform owns infrastructure; GitHub Actions tests, builds, migrates, deploys, and verifies `/health`.

