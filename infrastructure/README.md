# Infrastructure (Terraform)

| Module | Lớp | Nội dung | State |
|---|---|---|---|
| `00-bootstrap/` | nền | S3 state bucket `idp-tfstate-<account>-us-east-1` | local |
| `03-ecr/` | nền | 6 repo ECR (`force_delete=false`, giữ 10 image) | S3 |
| `04-oidc/` | nền | GitHub OIDC provider + IAM role CI (đọc ARN ECR qua remote state) | S3 |
| `01-network/` | tạo-huỷ | VPC, subnet, 1 NAT | S3 |
| `02-cluster-eks/` | tạo-huỷ | EKS 1.35, IRSA (EBS CSI, autoscaler), Argo CD + root app | S3 |
| `05-backstage-ec2/` | tạo-huỷ | EC2 Backstage (tuỳ chọn) | S3 |

Backend S3 cấu hình một phần; bucket truyền lúc init, `TF_VAR_state_bucket` cho remote state. Không chạy tay — dùng `scripts/aws-foundation-up.sh`, `scripts/aws-up.sh`, `scripts/aws-down.sh` (xem `docs/SETUP.md`). Kiểm tĩnh: `scripts/terraform-validate.sh`.
