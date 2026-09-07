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
  description = "Route 53 hosted-zone domain."
  type        = string
  default     = "floridafreediving.com"
}

variable "image_tag" {
  description = "Immutable application image tag already pushed to ECR."
  type        = string
  default     = "bootstrap"
}

variable "officer_password_hash" {
  description = "Bcrypt hash for the shared officer password."
  type        = string
  sensitive   = true
}

