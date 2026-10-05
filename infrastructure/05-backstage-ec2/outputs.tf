output "instance_id" {
  description = "EC2 instance ID of the Backstage host"
  value       = aws_instance.backstage.id
}

output "elastic_ip" {
  description = "Elastic IP address assigned to Backstage (use this for OAuth callback URL)"
  value       = aws_eip.backstage.public_ip
}

output "public_ip" {
  description = "Public IP of the EC2 instance (same as Elastic IP after association)"
  value       = aws_eip.backstage.public_ip
}

output "backstage_url" {
  description = "URL to access the Backstage UI"
  value       = "http://${aws_eip.backstage.public_ip}:3000"
}

output "github_oauth_callback_url" {
  description = "GitHub OAuth App callback URL — use this when creating the OAuth App"
  value       = "http://${aws_eip.backstage.public_ip}:7007/api/auth/github/handler/frame"
}

output "security_group_id" {
  description = "Security group ID attached to the Backstage EC2 instance"
  value       = aws_security_group.backstage.id
}
