# Infrastructure Architecture

## Deployment model

Terraform in `infra/` defines the production AWS environment. The deployable unit is an
immutable, commit-tagged container containing both the FastAPI server and compiled React
assets. This same-origin design avoids a separate static-site release, cross-origin cookies,
and browser-specific API base URLs.

The architecture and application contracts are independent of whether the backing database is
local SQLite, local PostgreSQL, or Amazon RDS. Runtime values enter exclusively through
environment variables and Secrets Manager.

## Container image

The root `Dockerfile` has two stages:

1. Node 22 installs locked frontend dependencies and runs the Vite production build.
2. Python 3.12 installs backend dependencies, copies backend source and frontend `dist/`, then
   exposes port 8000.

At startup the image runs `alembic upgrade head` and only then starts Uvicorn. FastAPI serves
`/assets`, the JSON API, health check, and SPA fallback. One image therefore represents one
complete application version and one expected database schema revision.

## AWS resource map

| Layer | Terraform resources and behavior |
| --- | --- |
| Network | A `10.42.0.0/16` VPC, internet gateway, two availability-zone application subnets, route table, and scoped security groups. |
| Compute | ECS cluster plus an ECS Express Gateway Service running 1–3 tasks at 256 CPU units and 512 MiB. Request-count scaling targets 500 requests per target. |
| Ingress | The Express service provides managed HTTP ingress and checks `/health`. ACM validates the application certificate through Route 53 DNS. |
| Database | Private, encrypted PostgreSQL 17 RDS (`db.t4g.micro`) with gp3 autoscaling from 20–100 GiB, TLS-required URL, seven-day backups, deletion protection, and final snapshot. |
| Images | ECR repository with immutable tags, scan-on-push, and retention of the latest 20 images. |
| Secrets | Separate Secrets Manager values for database URL, officer bcrypt hash, and generated session signing secret. |
| Identity | ECS task execution role reads only the three application secrets; the ECS infrastructure role uses the AWS-managed Express Gateway policy. |
| Observability | CloudWatch log group `/ecs/{project_name}` with 30-day retention. |
| State | S3 Terraform backend configured at initialization; native S3 lockfile support serializes state changes. |

RDS has `publicly_accessible` disabled and accepts PostgreSQL traffic only from the
application security group. Application tasks accept port 8000 traffic only from within the
VPC; public routing is owned by the Express service ingress.

## Configuration boundaries

Terraform variables are `aws_region`, `project_name`, `domain_name`, immutable `image_tag`, and
sensitive `officer_password_hash`. Terraform outputs expose the ECR URL, Express service ARN
and endpoint, validated certificate ARN, and a sensitive database endpoint.

The container receives:

| Variable | Source | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | Secrets Manager | SQLAlchemy PostgreSQL URL with `sslmode=require`. |
| `OFFICER_PASSWORD_HASH` | Secrets Manager | Bcrypt hash for the shared password. |
| `SESSION_SECRET` | Secrets Manager | Signed-cookie secret; rotation invalidates sessions. |
| `COOKIE_SECURE` | ECS environment (`true`) | Enables Secure and `__Host-` cookie behavior plus HSTS. |
| `ALLOWED_ORIGINS` | ECS environment | Canonical HTTPS application origin for mutation checks. |

Secrets are not baked into images or committed. Because sensitive Terraform inputs and generated
passwords are represented in state, the state bucket must be encrypted, versioned, and limited
to deployment administrators.

## Domain and TLS

Terraform requests and DNS-validates the ACM certificate. ECS Express Mode manages the load
balancer listener outside the current Terraform resource input surface, so the validated
certificate must be associated with the managed listener and the domain must alias the Express
ingress as a one-time platform connection. Application code requires no change: it continues to
serve the same origin, and `ALLOWED_ORIGINS` remains the canonical HTTPS domain.

## Persistence and lifecycle

Application tasks are disposable; durable state lives in RDS, Secrets Manager, ECR, CloudWatch,
and Terraform state. RDS deletion protection and final snapshots guard against accidental
destruction. Completed dives and participant data remain in the database until an officer
deletes the dive. Operational data-retention decisions should therefore include member PII and
database backup retention, not container or task lifetime.

See [Delivery and operations](operations.md) for release, migration, and recovery procedures.
