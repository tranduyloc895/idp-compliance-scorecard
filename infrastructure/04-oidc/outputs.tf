output "oidc_provider_arn" {
  description = "ARN of the GitHub OIDC Identity Provider"
  value       = aws_iam_openid_connect_provider.github.arn
}

output "role_arn" {
  description = "ARN of the IAM Role for GitHub Actions — dùng làm giá trị cho GitHub Secret AWS_ROLE_ARN"
  value       = aws_iam_role.github_actions.arn
}

output "role_name" {
  description = "Name of the IAM Role"
  value       = aws_iam_role.github_actions.name
}
