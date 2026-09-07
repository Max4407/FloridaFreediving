output "ecr_repository_url" {
  value = aws_ecr_repository.app.repository_url
}

output "express_service_arn" {
  value = aws_ecs_express_gateway_service.app.service_arn
}

output "express_endpoint" {
  value = aws_ecs_express_gateway_service.app.ingress_paths[0].endpoint
}

output "certificate_arn" {
  value = aws_acm_certificate_validation.app.certificate_arn
}

output "database_endpoint" {
  value     = aws_db_instance.main.endpoint
  sensitive = true
}

