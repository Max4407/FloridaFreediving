# AWS deployment

Terraform provisions a single-host production stack: Amazon Linux 2023 on EC2, an Elastic IP,
Route 53, ECR, Secrets Manager, and a protected EBS data volume. Caddy, the FastAPI/React image,
and PostgreSQL run as Docker containers on the instance. No ALB, ECS service, ACM certificate,
or RDS instance is used.

## Prerequisites

- Terraform 1.12+, AWS CLI, Docker, and an AWS account with a public Route 53 hosted zone.
- An encrypted, versioned S3 Terraform-state bucket using S3 lockfiles.
- A bcrypt officer password hash supplied through `TF_VAR_officer_password_hash`.
- For GitHub deployment, `AWS_DEPLOY_ROLE_ARN`, `TF_STATE_BUCKET`, and
  `OFFICER_PASSWORD_HASH` environment secrets.

## Provisioning

```sh
terraform init \
  -backend-config="bucket=YOUR_STATE_BUCKET" \
  -backend-config="key=florida-freediving/terraform.tfstate" \
  -backend-config="region=us-east-1" \
  -backend-config="use_lockfile=true"
terraform plan -var="officer_password_hash=$OFFICER_PASSWORD_HASH"
terraform apply -var="officer_password_hash=$OFFICER_PASSWORD_HASH"
```

The instance boot script installs Docker, mounts the data disk, writes the Caddy configuration,
and installs `/usr/local/bin/deploy-florida-freediving`. It does not deploy an app image. The
GitHub workflow builds a commit-tagged image, pushes it to ECR, and invokes that script through
Systems Manager Run Command.

## Host layout

- `ff-caddy`: public ports 80 and 443; automatic certificates and HTTP-to-HTTPS redirect.
- `ff-app`: private Docker-network port 8000 plus loopback-only port 8000 for health checks.
- `ff-postgres`: private Docker-network port 5432; never published on the host.
- `/var/lib/florida-freediving/postgres`: database files on the protected EBS volume.
- `/var/lib/florida-freediving/caddy-*`: persistent Caddy certificates and configuration state.
- `/opt/florida-freediving/app.env`: root-only runtime secrets fetched from Secrets Manager.

The host has no SSH ingress. Use Session Manager for diagnostics, for example:

```sh
aws ssm start-session --target "$(terraform output -raw instance_id)"
sudo docker ps
sudo docker logs --tail 200 ff-app
sudo docker logs --tail 200 ff-caddy
```

## Data safeguards

The PostgreSQL data disk is encrypted, has Terraform `prevent_destroy`, and is covered by an
EBS Data Lifecycle Manager policy retaining seven daily snapshots. The protection intentionally
blocks a normal `terraform destroy`; remove it only as part of an explicit, reviewed data
retirement or restore procedure.

This architecture minimizes recurring services but is intentionally single-host. Instance or
availability-zone failure causes downtime until EC2 and the data volume recover. EBS snapshots
are crash-consistent, not a replacement for tested logical PostgreSQL exports.

See [the infrastructure handbook](../docs/infrastructure/README.md) and
[operations runbook](../docs/infrastructure/operations.md) for deployment, rollback, migration,
and restore behavior.
