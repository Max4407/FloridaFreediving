# Delivery and Operations

## Continuous integration

`.github/workflows/ci.yml` runs on pull requests and pushes to `main`:

- Python 3.12 installs `backend/requirements-dev.txt`, runs Pytest, and runs Ruff.
- Node 22 installs with `npm ci`, runs Vitest, ESLint, and the production Vite build.
- Terraform 1.12 checks formatting, initializes without a backend, and validates configuration.
- Playwright installs Chromium, migrates a temporary database, starts the backend, and exercises
  browser smoke flows through the Vite development server.

A change is release-ready only when all relevant jobs pass. Database, security, and deployment
changes should receive human review even when automated checks succeed.

## Production deployment

`.github/workflows/deploy.yml` runs on `main` and manual dispatch. GitHub Actions obtains AWS
credentials through OIDC using `AWS_DEPLOY_ROLE_ARN`; no long-lived AWS key is required.

The workflow:

1. Initializes the S3 Terraform backend using `TF_STATE_BUCKET`.
2. Authenticates Docker to ECR.
3. Builds the complete application image and pushes tag `${github.sha}`.
4. Plans Terraform with that immutable image tag and the protected password hash.
5. Applies the reviewed plan, causing ECS to deploy the new task revision.
6. Retries the Express endpoint `/health` until the service responds successfully.

Terraform serializes production applies through remote state locking, while the workflow's
`production` concurrency group prevents overlapping deployments.

## Initial bootstrap

The first environment creation has an ECR dependency cycle: Terraform defines the repository,
but the full ECS service needs an image already present. Apply the ECR repository target, push a
`bootstrap` image, then apply the full configuration. The detailed shell commands remain in
`infra/README.md`; normal releases use the automated workflow afterward.

## Database migrations

Every container executes `alembic upgrade head` before Uvicorn. Migrations must be backward-safe
for any overlap between old and new ECS tasks. Prefer additive changes, backfill separately when
needed, and remove old columns only after no running image depends on them.

Before a destructive or long-running migration:

1. Review the RDS automated backup window and create an explicit snapshot when warranted.
2. Test against PostgreSQL with representative data volume.
3. Confirm expected lock duration and old-image compatibility.
4. Define the database restore point and application image rollback together.

Alembic downgrade functions are developer aids, not a substitute for a production recovery plan.

## Health and observability

`GET /health` is intentionally data-free and does not verify RDS. It is appropriate for task
liveness and ingress routing; application/API errors must additionally be monitored through
CloudWatch logs and external functional checks. Avoid logging request bodies, signup responses,
or other member PII. The current log retention is 30 days.

Useful failure boundaries are:

- migration/startup failure: ECS task never becomes healthy; inspect task logs;
- ingress failure: Express health retries fail while task logs may remain healthy;
- database failure: API requests fail despite `/health` returning `200`;
- authentication failure: distinguish expected pre-login session `401`, invalid origin `403`,
  incorrect password `401`, and rate limit `429`.

## Rollback and recovery

ECR retains immutable commit images, so application rollback means redeploying the prior known-good
tag through Terraform. Do not retag or overwrite an image. If the release included a compatible
additive migration, the old image can normally run against the newer schema. Otherwise restore
the coordinated RDS snapshot and deploy the matching image.

RDS deletion protection should remain enabled. If infrastructure must be dismantled, explicitly
plan the final snapshot name and preserve Terraform state until recovery assets are verified.

## Secret and credential rotation

- Change the shared officer password by generating a new bcrypt hash and updating the protected
  deployment secret/input; never store the plaintext password.
- Rotate `SESSION_SECRET` when universal logout is desired or compromise is suspected. Every
  existing cookie immediately becomes invalid.
- Rotate database credentials by updating the RDS credential and Secrets Manager URL as one
  coordinated operation, then recycle application tasks.
- Restrict the GitHub OIDC role to the repository, production environment, and required AWS
  actions. Review CloudTrail and repository environment approvals periodically.

## Local parity

Local operation may use SQLite or the PostgreSQL service in `compose.yaml`, and Vite may run on a
separate port. These are adapters around the same schemas, endpoints, cookie flow, and migration
history used in AWS. Production-specific hostnames and secrets belong in configuration; no source
or documentation changes are required when moving between environments.

