# ============================================================
# GitHub Actions OIDC — IAM Provider + Role + ECR Push Policy
# ============================================================
#
# Kiến trúc:
#   GitHub Actions → OIDC token → STS AssumeRoleWithWebIdentity
#   → IAM Role → ECR Push (6 repo của 03-ecr)
#
# Không cần static access key nào trong GitHub Secrets!

# Repo ECR lấy từ remote state của 03-ecr (không ghi cứng account ID — audit #4).
data "terraform_remote_state" "ecr" {
  backend = "s3"
  config = {
    bucket = var.state_bucket
    key    = "03-ecr/terraform.tfstate"
    region = var.aws_region
  }
}

# Mỗi account chỉ có 1 OIDC provider cho token.actions.githubusercontent.com.
# Nếu account đã có (tạo tay hoặc project khác), đặt create_oidc_provider=false.
data "aws_iam_openid_connect_provider" "github" {
  count = var.create_oidc_provider ? 0 : 1
  url   = "https://token.actions.githubusercontent.com"
}

locals {
  oidc_provider_arn = var.create_oidc_provider ? aws_iam_openid_connect_provider.github[0].arn : data.aws_iam_openid_connect_provider.github[0].arn

  # Claim `sub` có hai dạng:
  #   - mặc định:          repo:<owner>/<repo>:<ref|environment|pull_request>
  #   - immutable subject: repo:<owner>@<owner_id>/<repo>@<repo_id>:...
  #     (repo này bật sẵn; xem gh api repos/<owner>/<repo>/actions/oidc/customization/sub)
  # Chấp nhận cả hai để role không hỏng khi GitHub đổi cấu hình mặc định.
  github_subjects = compact([
    "repo:${var.github_org}/${var.github_repo}:*",
    var.github_owner_id != "" && var.github_repo_id != "" ? "repo:${var.github_org}@${var.github_owner_id}/${var.github_repo}@${var.github_repo_id}:*" : "",
  ])
}

# Lấy thumbprint tự động từ OIDC endpoint (tránh hardcode)
data "tls_certificate" "github" {
  url = "https://token.actions.githubusercontent.com/.well-known/openid-configuration"
}

# ─── OIDC Identity Provider ──────────────────────────────────────────────────
resource "aws_iam_openid_connect_provider" "github" {
  count = var.create_oidc_provider ? 1 : 0
  url   = "https://token.actions.githubusercontent.com"

  # STS là audience chuẩn cho OIDC với AWS
  client_id_list = ["sts.amazonaws.com"]

  # Thumbprint lấy từ certificate của OIDC endpoint
  thumbprint_list = [data.tls_certificate.github.certificates[0].sha1_fingerprint]


  tags = {
    Name = "github-actions-oidc-provider"
  }
}

# ─── IAM Role ────────────────────────────────────────────────────────────────
resource "aws_iam_role" "github_actions" {
  name        = var.iam_role_name
  description = "Assumed by GitHub Actions via OIDC (monorepo CI: build/push ECR)"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "GitHubActionsOIDC"
        Effect = "Allow"
        Principal = {
          Federated = local.oidc_provider_arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            # Chỉ cho phép token từ GitHub Actions (audience đúng)
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            # Giới hạn đúng repo monorepo, mọi branch/tag/PR (cả hai dạng sub)
            "token.actions.githubusercontent.com:sub" = local.github_subjects
          }
        }
      }
    ]
  })
}

# ─── ECR Push Policy ─────────────────────────────────────────────────────────
resource "aws_iam_role_policy" "ecr_push" {
  name = "ecr-push-retail-store"
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # GetAuthorizationToken không hỗ trợ resource-level permission → phải dùng "*"
        Sid      = "ECRGetAuthToken"
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },
      {
        # Chỉ cấp quyền push/pull trên các repo do 03-ecr tạo (least privilege)
        Sid    = "ECRPushPullRetailStore"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:PutImage",
          # Pull để Trivy scan có thể kéo image về
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer",
          # Describe để kiểm tra repo tồn tại
          "ecr:DescribeRepositories",
          "ecr:DescribeImages"
        ]
        Resource = values(data.terraform_remote_state.ecr.outputs.repository_arns)
      }
    ]
  })
}
