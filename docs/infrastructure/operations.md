# Delivery and Operations

## Continuous integration

`.github/workflows/ci.yml` runs backend tests/Ruff, frontend tests/ESLint/build, Terraform format
and validation, and Playwright browser flows. A change is release-ready only when all relevant
jobs pass. Infrastructure plans, migration behavior, and single-host risk still require review.

## Production deployment

`.github/workflows/deploy.yml` runs on `main` and manual dispatch. GitHub Actions assumes
`AWS_DEPLOY_ROLE_ARN` through OIDC and never stores a long-lived AWS key. The workflow:

1. Initializes the locked S3 Terraform backend.
2. Plans and applies networking, EC2, EBS, DNS, ECR, secrets, identity, and snapshot policy.
3. Builds the complete application image and pushes immutable tag `${github.sha}` to ECR.
4. Waits for the EC2 instance to register with Systems Manager.
5. Uses SSM Run Command to invoke `/usr/local/bin/deploy-florida-freediving {tag}`.
6. Verifies the public Caddy endpoint at `/health`.

The deployment script refreshes runtime secrets, ensures PostgreSQL is ready, pulls the requested
image, starts it, and checks loopback health. If health fails, it restores the prior application
image automatically. Caddy is recreated only after the new app is healthy. The old ECR image is
retained for later manual rollback.

The GitHub role needs Terraform's infrastructure permissions plus ECR push and
`ssm:SendCommand`, `ssm:GetCommandInvocation`, and `ssm:DescribeInstanceInformation` for the
tagged production instance. Repository environment protection should gate this role.

## First deployment

Unlike the former ECS design, infrastructure can be created before an application image exists.
Run the normal deploy workflow: Terraform creates the empty ECR repository and prepared host,
then later steps build and deploy the first image. Caddy begins serving only after the app passes
its first health check and DNS is available for certificate issuance.

## Database migrations

The app container runs `alembic upgrade head` before Uvicorn. Because one app container is
replaced at a time, deployment has a brief maintenance window rather than mixed application
versions. Destructive or long-running migrations still require a current EBS snapshot, a tested
PostgreSQL restore, and a coordinated image/schema rollback plan.

When migrating existing data from RDS or another PostgreSQL server:

1. Put the existing application into a write-free maintenance window.
2. Create and verify a final source backup.
3. Use `pg_dump` and `pg_restore` over a controlled SSM session or temporary private connection.
4. Confirm row counts and critical signup/officer/inventory records in the container database.
5. Switch DNS/deployment only after application smoke tests pass.
6. Retain the source database and final snapshot through an agreed rollback window.

Terraform does not move database contents. Do not approve a plan that destroys an existing RDS
database until this migration and rollback window are complete.

## Health and diagnostics

`GET /health` proves the FastAPI process responds but does not query PostgreSQL. Caddy actively
checks the same path. Use Session Manager and Docker state for deeper diagnosis:

```sh
aws ssm start-session --target INSTANCE_ID
sudo docker ps
sudo docker logs --tail 200 ff-app
sudo docker logs --tail 200 ff-postgres
sudo docker logs --tail 200 ff-caddy
sudo journalctl -u docker --since "1 hour ago"
```

Never paste `app.env`, container environment output, member records, or database URLs into logs
or support messages. The root-only environment file contains production secrets.

## Rollback

For an application-only rollback, rerun the host deployment command with the prior immutable ECR
tag through SSM. The script applies the same health gate and can restore the image it replaced.
Rollback is safe only when the current database schema remains compatible with the old image.

For host failure, replace the EC2 instance through Terraform and reattach the protected data
volume; user data remounts it and reinstalls the deployment script. For data failure, restore a
DLM snapshot to a new volume, stop PostgreSQL, attach/mount the restored volume, and validate it
before changing Terraform ownership. Perform restore drills before relying on this path.

## Secret rotation

- Change the officer password by updating the bcrypt hash input and deploying; plaintext is never
  stored. The next deploy refreshes `app.env`.
- Rotate `SESSION_SECRET` by replacing its Secrets Manager version and redeploying. This logs out
  every officer.
- Database password rotation must update PostgreSQL itself first with `ALTER ROLE`, then update
  Secrets Manager and redeploy. Changing only the secret disconnects the app from the existing
  database container.
- Review the GitHub OIDC role, instance profile, Systems Manager history, and Terraform state
  access periodically.

## Single-host maintenance

Operating-system updates, Docker restarts, instance replacement, and database recovery may cause
downtime. Schedule them outside dive signup peaks. Before maintenance, confirm a recent snapshot;
afterward, verify Caddy certificate status, `/health`, officer login, public dive lookup, and one
read-only dashboard load.

