variable "aws_region" {
  description = "AWS region for all application resources."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Prefix used for AWS resource names."
  type        = string
  default     = "florida-freediving"
}

variable "domain_name" {
  description = "Route 53 hosted-zone domain served by Caddy."
  type        = string
  default     = "floridafreediving.com"
}

variable "instance_type" {
  description = "EC2 instance type running Caddy, the app, and PostgreSQL."
  type        = string
  default     = "t3.micro"
}

variable "data_volume_size" {
  description = "Size in GiB of the persistent PostgreSQL EBS volume."
  type        = number
  default     = 20

  validation {
    condition     = var.data_volume_size >= 20
    error_message = "The data volume must be at least 20 GiB."
  }
}

variable "caddy_image" {
  description = "Pinned official Caddy container image."
  type        = string
  default     = "caddy:2.11.4-alpine"
}

variable "officer_password_hash" {
  description = "Bcrypt hash for the shared officer password."
  type        = string
  sensitive   = true
}
