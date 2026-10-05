output "repository_urls" {
  description = "Map of service name to ECR repository URL"
  value       = { for k, v in aws_ecr_repository.services : k => v.repository_url }
}

output "registry_id" {
  description = "The registry ID (AWS Account ID)"
  value       = values(aws_ecr_repository.services)[0].registry_id
}
