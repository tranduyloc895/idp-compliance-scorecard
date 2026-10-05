# IDP Platform — Infrastructure

Terraform IaC cho toàn bộ hạ tầng AWS của dự án IDP.

## Modules

| Module | Mô tả |
|---|---|
| `01-network/` | VPC, subnets, NAT Gateway, Internet Gateway |
| `02-cluster-eks/` | EKS cluster, IRSA cho EBS CSI + Cluster Autoscaler, ArgoCD |
| `03-ecr/` | ECR repositories cho 5 microservices |
| `04-oidc/` | OIDC identity provider cho GitHub Actions |

## Region
`us-east-1` (N. Virginia) — lựa chọn rẻ nhất

## Usage

```bash
# 1. Network
cd 01-network && terraform init && terraform apply

# 2. EKS + ArgoCD
cd 02-cluster-eks && terraform init && terraform apply

# 3. ECR
cd 03-ecr && terraform init && terraform apply
```

## Teardown (tiết kiệm chi phí)

```bash
cd 02-cluster-eks && terraform destroy
cd 01-network && terraform destroy
# Giữ 03-ecr (chi phí gần như 0)
```
