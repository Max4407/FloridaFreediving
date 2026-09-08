output "ecr_repository_url" {
  value = aws_ecr_repository.app.repository_url
}

output "instance_id" {
  value = aws_instance.app.id
}

output "public_ip" {
  value = aws_eip.app.public_ip
}

output "application_url" {
  value = "https://${var.domain_name}"
}

output "data_volume_id" {
  value = aws_ebs_volume.data.id
}
