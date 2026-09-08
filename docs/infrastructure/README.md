# Infrastructure Architecture

## Deployment model

Terraform in `infra/` defines a low-cost, single-host AWS environment. One Amazon Linux 2023
EC2 instance runs three Docker containers: Caddy, the immutable FastAPI/React application image,
and PostgreSQL 17. Caddy is the only public process and replaces a load balancer by terminating
TLS and reverse-proxying to the app over a private Docker network.

```text
Internet
   |
Route 53 A record -> Elastic IP
   |
Caddy container :80/:443
   |
FastAPI/React container :8000
   |
PostgreSQL container :5432 -> encrypted EBS data volume
```

The consolidation reduces managed-service costs but creates one failure domain. Host, Docker,
or availability-zone failure makes the whole application unavailable until recovery. There is
no automatic horizontal scaling or database failover.

## Container responsibilities

The root `Dockerfile` builds only the application image. Node 22 compiles the Vite frontend;
Python 3.12 installs backend dependencies and runs Alembic before Uvicorn. Deployment pulls that
image from ECR using an immutable commit tag.

The host deployment script starts:

- `ff-caddy` from pinned `caddy:2.11.4-alpine`, with persistent `/data` and `/config` mounts;
- `ff-app`, configured from a root-only environment file and published only to loopback for
  host health checks;
- `ff-postgres` from `postgres:17-alpine`, reachable only by containers on the private network.

Caddy obtains and renews public certificates automatically because the Route 53 A record points
to the Elastic IP and ports 80/443 are open. Its state is retained on the data disk to avoid
unnecessary certificate reissuance.

## AWS resource map

| Layer | Terraform resources and behavior |
| --- | --- |
| Network | A `10.42.0.0/16` VPC, internet gateway, one public subnet, and a route table. |
| Compute | One configurable EC2 instance, default `t3.micro`, using the current x86_64 Amazon Linux 2023 AMI from the AWS public SSM parameter. |
| Ingress | Elastic IP and Route 53 A record. The security group exposes TCP 80/443 and UDP 443; SSH and app/database ports are closed. |
| Data | Separate encrypted gp3 EBS volume, default 20 GiB, mounted at `/var/lib/florida-freediving`. Terraform prevents its destruction. |
| Backups | Data Lifecycle Manager takes daily EBS snapshots and retains seven. |
| Images | ECR repository with immutable tags, scan-on-push, and retention of the latest 20 images. |
| Secrets | Secrets Manager stores the generated database password, officer bcrypt hash, and generated session secret. |
| Identity | An EC2 instance profile grants SSM management, read-only access to those secrets, and pull access to the application repository. |
| State | An encrypted/versioned S3 backend with lockfiles serializes Terraform changes. |

IMDSv2 is mandatory. Docker logs rotate at five 10 MiB files per container. Systems Manager is
the only administrative path, so no SSH key or inbound management port is provisioned.

## Configuration boundaries

Terraform variables are `aws_region`, `project_name`, `domain_name`, `instance_type`,
`data_volume_size`, pinned `caddy_image`, and sensitive `officer_password_hash`. Outputs expose
the ECR URL, instance ID, Elastic IP, HTTPS application URL, and data-volume ID.

On each application deployment, the instance fetches Secrets Manager values and writes:

| Variable | Runtime value |
| --- | --- |
| `DATABASE_URL` | PostgreSQL URL targeting `ff-postgres` on the private Docker network. |
| `OFFICER_PASSWORD_HASH` | Bcrypt hash for shared officer authentication. |
| `SESSION_SECRET` | Cookie-signing secret; changing it invalidates all sessions. |
| `COOKIE_SECURE` | `true`, enabling the Secure `__Host-` cookie and HSTS. |
| `ALLOWED_ORIGINS` | Canonical `https://{domain_name}` origin. |

Secrets are not baked into images or committed. Generated passwords and sensitive inputs remain
in Terraform state, so the state bucket is itself sensitive and must have tightly scoped access.

## Persistence and lifecycle

The EC2 root disk and containers are replaceable. PostgreSQL files plus Caddy certificate state
live on the separately managed EBS volume, which can be reattached after host replacement in the
same availability zone. Completed dives and member PII remain until an officer deletes the dive.

EBS snapshots are crash-consistent. PostgreSQL performs crash recovery when restored, but regular
logical dumps and restore drills are recommended before the application becomes operationally
critical. See [Delivery and operations](operations.md) for deployment and recovery procedures.
