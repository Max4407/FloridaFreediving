# AWS deployment

## Prerequisites

- Terraform 1.12+, AWS CLI, Docker, and an AWS account with a Route 53 hosted zone for the domain.
- An S3 state bucket with versioning/encryption and a state-locking configuration.
- A bcrypt officer password hash supplied through `TF_VAR_officer_password_hash` or CI secrets.

## Bootstrap

ECS needs an existing image, while the image repository is created by Terraform. Apply the ECR target first, push a bootstrap image, then apply the full stack:

```sh
terraform init -backend-config="bucket=YOUR_STATE_BUCKET" -backend-config="key=florida-freediving/terraform.tfstate" -backend-config="region=us-east-1" -backend-config="use_lockfile=true"
terraform apply -target=aws_ecr_repository.app -var="officer_password_hash=$OFFICER_PASSWORD_HASH"
docker build -t florida-freediving .
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ACCOUNT.dkr.ecr.us-east-1.amazonaws.com
docker tag florida-freediving:latest ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/florida-freediving:bootstrap
docker push ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/florida-freediving:bootstrap
terraform apply -var="officer_password_hash=$OFFICER_PASSWORD_HASH"
```

The container runs `alembic upgrade head` before starting the web process, so a deployment becomes healthy only after its migrations succeed. Review destructive migrations separately before deployment.

## Custom domain

Terraform provisions and validates the ACM certificate. ECS Express Mode currently manages its ALB listener outside the input surface exposed by the Terraform AWS provider. After the first apply, follow AWS’s “Adding a custom domain to your service” procedure to attach the output certificate to the managed listener and create a Route 53 alias for `floridafreediving.com`. Keep this one-time association documented if AWS adds a first-class Terraform input later.

Rotating `SESSION_SECRET` invalidates every officer session. RDS deletion protection and a final snapshot are enabled intentionally.
