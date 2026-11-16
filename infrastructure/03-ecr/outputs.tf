output "repository_urls" {
  description = "Map tên service -> ECR repository URL"
  value       = { for k, v in aws_ecr_repository.services : k => v.repository_url }
}

output "repository_arns" {
  description = "Map tên service -> ECR repository ARN (04-oidc dùng qua remote state)"
  value       = { for k, v in aws_ecr_repository.services : k => v.arn }
}

output "registry_id" {
  description = "Registry ID (AWS account ID)"
  value       = values(aws_ecr_repository.services)[0].registry_id
}

output "registry" {
  description = "ECR registry host"
  value       = split("/", values(aws_ecr_repository.services)[0].repository_url)[0]
}
