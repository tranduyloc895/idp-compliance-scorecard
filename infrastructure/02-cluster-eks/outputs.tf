output "cluster_name" {
  description = "Name of the EKS cluster"
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "Endpoint URL of the EKS cluster API"
  value       = module.eks.cluster_endpoint
}

output "cluster_certificate_authority_data" {
  description = "Base64 encoded certificate data for cluster authentication"
  value       = module.eks.cluster_certificate_authority_data
  sensitive   = true
}

output "cluster_security_group_id" {
  description = "Security group ID attached to the EKS cluster"
  value       = module.eks.cluster_security_group_id
}

output "node_security_group_id" {
  description = "Security group ID attached to the EKS nodes"
  value       = module.eks.node_security_group_id
}

output "kms_key_arn" {
  description = "ARN of KMS key used for EKS secrets encryption"
  value       = aws_kms_key.eks.arn
}

output "cluster_autoscaler_iam_role_arn" {
  description = "ARN of the IRSA role for Cluster Autoscaler (annotate vào service account kube-system:cluster-autoscaler trong gitops)"
  value       = module.cluster_autoscaler_irsa.iam_role_arn
}
