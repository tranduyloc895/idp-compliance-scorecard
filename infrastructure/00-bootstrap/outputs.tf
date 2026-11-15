output "state_bucket" {
  description = "Tên S3 bucket chứa Terraform state (truyền vào -backend-config=bucket=... và TF_VAR_state_bucket)"
  value       = aws_s3_bucket.tfstate.bucket
}

output "account_id" {
  description = "AWS account ID của credential đang dùng"
  value       = data.aws_caller_identity.current.account_id
}
