# Florida Freediving Documentation

This directory is the technical handbook for the Florida Freediving web application. The
documents describe the application by responsibility and contract, so the same references
apply to local development and the AWS-hosted deployment.

## Documentation map

| Document | Purpose |
| --- | --- |
| [Architecture](architecture.md) | System boundaries, request flows, security model, and core product rules |
| [Frontend](frontend/README.md) | React entry points, components, state, styling, and browser behavior |
| [Backend](backend/README.md) | FastAPI modules, services, major functions, validation, and transactions |
| [API reference](backend/api.md) | Every HTTP endpoint, request shape, response shape, and expected errors |
| [Data model](backend/data-model.md) | SQLAlchemy entities, relationships, constraints, enums, and migrations |
| [Infrastructure](infrastructure/README.md) | Container, AWS resources, secrets, networking, persistence, and scaling |
| [Delivery and operations](infrastructure/operations.md) | CI/CD, deployment, migrations, health checks, rollback, and secret rotation |
| [Product plan](PLAN.md) | Original scope, decisions, assumptions, and delivery plan |

## Source layout

```text
frontend/        React/Vite single-page application
backend/         FastAPI application, SQLAlchemy models, services, and Alembic
infra/           Terraform for the production AWS environment
.github/         Continuous integration and deployment workflows
docs/            Product and technical documentation
Dockerfile       Production multi-stage application image
compose.yaml     Local PostgreSQL service
```

## Documentation conventions

- Paths are relative to the repository root unless stated otherwise.
- API times are ISO 8601 values. Dive times are interpreted in `America/New_York` when an
  offset is omitted and are stored as timezone-aware values.
- `publicId` refers to the short ID used in member links; `diveId` and other entity IDs are
  internal UUIDs.
- “Officer access” means a valid signed shared-session cookie, not an individual user account.
- Environment-specific addresses, resource IDs, and secret values are deliberately omitted.
  Runtime configuration supplies them without changing application behavior or these contracts.

