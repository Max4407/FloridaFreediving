data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_route53_zone" "main" {
  name         = var.domain_name
  private_zone = false
}

data "aws_ssm_parameter" "amazon_linux" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

resource "aws_vpc" "main" {
  cidr_block           = "10.42.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = { Name = var.project_name }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = var.project_name }
}

resource "aws_subnet" "app" {
  vpc_id                  = aws_vpc.main.id
  availability_zone       = data.aws_availability_zones.available.names[0]
  cidr_block              = cidrsubnet(aws_vpc.main.cidr_block, 8, 0)
  map_public_ip_on_launch = true

  tags = { Name = "${var.project_name}-app" }
}

resource "aws_route_table" "app" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
}

resource "aws_route_table_association" "app" {
  subnet_id      = aws_subnet.app.id
  route_table_id = aws_route_table.app.id
}

resource "aws_security_group" "web" {
  name        = "${var.project_name}-web"
  description = "Public web traffic to Caddy"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP and ACME challenges"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP3"
    from_port   = 443
    to_port     = 443
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "random_password" "database" {
  length  = 32
  special = false
}

resource "random_password" "session" {
  length  = 64
  special = false
}

resource "aws_secretsmanager_secret" "database_password" {
  name = "${var.project_name}/database-password"
}

resource "aws_secretsmanager_secret_version" "database_password" {
  secret_id     = aws_secretsmanager_secret.database_password.id
  secret_string = random_password.database.result
}

resource "aws_secretsmanager_secret" "officer_password" {
  name = "${var.project_name}/officer-password-hash"
}

resource "aws_secretsmanager_secret_version" "officer_password" {
  secret_id     = aws_secretsmanager_secret.officer_password.id
  secret_string = var.officer_password_hash
}

resource "aws_secretsmanager_secret" "session" {
  name = "${var.project_name}/session-secret"
}

resource "aws_secretsmanager_secret_version" "session" {
  secret_id     = aws_secretsmanager_secret.session.id
  secret_string = random_password.session.result
}

resource "aws_ecr_repository" "app" {
  name                 = var.project_name
  image_tag_mutability = "IMMUTABLE"
  force_delete         = false

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Retain the latest 20 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 20
      }
      action = { type = "expire" }
    }]
  })
}

data "aws_iam_policy_document" "ec2_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "app" {
  name               = "${var.project_name}-instance"
  assume_role_policy = data.aws_iam_policy_document.ec2_trust.json
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.app.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

data "aws_iam_policy_document" "app" {
  statement {
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer",
    ]
    resources = [aws_ecr_repository.app.arn]
  }

  statement {
    actions = ["secretsmanager:GetSecretValue"]
    resources = [
      aws_secretsmanager_secret.database_password.arn,
      aws_secretsmanager_secret.officer_password.arn,
      aws_secretsmanager_secret.session.arn,
    ]
  }
}

resource "aws_iam_role_policy" "app" {
  name   = "application-runtime"
  role   = aws_iam_role.app.id
  policy = data.aws_iam_policy_document.app.json
}

resource "aws_iam_instance_profile" "app" {
  name = var.project_name
  role = aws_iam_role.app.name
}

resource "aws_ebs_volume" "data" {
  availability_zone = aws_subnet.app.availability_zone
  encrypted         = true
  size              = var.data_volume_size
  type              = "gp3"

  tags = {
    Name   = "${var.project_name}-data"
    Backup = var.project_name
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_instance" "app" {
  ami                         = data.aws_ssm_parameter.amazon_linux.value
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.app.id
  vpc_security_group_ids      = [aws_security_group.web.id]
  iam_instance_profile        = aws_iam_instance_profile.app.name
  associate_public_ip_address = true
  user_data_replace_on_change = true
  user_data = templatefile("${path.module}/user_data.sh.tftpl", {
    aws_region          = var.aws_region
    caddy_image         = var.caddy_image
    data_volume_id      = aws_ebs_volume.data.id
    database_secret_arn = aws_secretsmanager_secret.database_password.arn
    domain_name         = var.domain_name
    officer_secret_arn  = aws_secretsmanager_secret.officer_password.arn
    repository_url      = aws_ecr_repository.app.repository_url
    session_secret_arn  = aws_secretsmanager_secret.session.arn
  })

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  root_block_device {
    encrypted   = true
    volume_size = 16
    volume_type = "gp3"
  }

  tags = { Name = var.project_name }

  depends_on = [
    aws_iam_role_policy.app,
    aws_iam_role_policy_attachment.ssm,
    aws_secretsmanager_secret_version.database_password,
    aws_secretsmanager_secret_version.officer_password,
    aws_secretsmanager_secret_version.session,
  ]
}

resource "aws_volume_attachment" "data" {
  device_name = "/dev/sdf"
  instance_id = aws_instance.app.id
  volume_id   = aws_ebs_volume.data.id
}

resource "aws_eip" "app" {
  domain   = "vpc"
  instance = aws_instance.app.id

  tags = { Name = var.project_name }
}

resource "aws_route53_record" "app" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = var.domain_name
  type    = "A"
  ttl     = 300
  records = [aws_eip.app.public_ip]
}

data "aws_iam_policy_document" "dlm_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["dlm.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "dlm" {
  name               = "${var.project_name}-snapshot-lifecycle"
  assume_role_policy = data.aws_iam_policy_document.dlm_trust.json
}

resource "aws_iam_role_policy_attachment" "dlm" {
  role       = aws_iam_role.dlm.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSDataLifecycleManagerServiceRole"
}

resource "aws_dlm_lifecycle_policy" "data" {
  description        = "Daily PostgreSQL data-volume snapshots"
  execution_role_arn = aws_iam_role.dlm.arn
  state              = "ENABLED"

  policy_details {
    resource_types = ["VOLUME"]
    target_tags = {
      Backup = var.project_name
    }

    schedule {
      name = "Daily snapshots"

      create_rule {
        interval      = 24
        interval_unit = "HOURS"
        times         = ["05:00"]
      }

      retain_rule {
        count = 7
      }

      copy_tags = true
      tags_to_add = {
        SnapshotCreator = "DLM"
      }
    }
  }
}
