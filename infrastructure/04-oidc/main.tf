# ============================================================
# GitHub Actions OIDC — IAM Provider + Role + ECR Push Policy
# ============================================================
#
# Kiến trúc:
#   GitHub Actions → OIDC token → STS AssumeRoleWithWebIdentity
#   → IAM Role → ECR Push (5 repos retail-store/*)
#
# Không cần static access key nào trong GitHub Secrets!

# Lấy thumbprint tự động từ OIDC endpoint (tránh hardcode)
data "tls_certificate" "github" {
  url = "https://token.actions.githubusercontent.com/.well-known/openid-configuration"
}

# ─── OIDC Identity Provider ──────────────────────────────────────────────────
resource "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"

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
  description = "Assumed by GitHub Actions via OIDC for idp-microservices CI"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "GitHubActionsOIDC"
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.github.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            # Chỉ cho phép token từ GitHub Actions (audience đúng)
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            # Giới hạn chỉ repo tranduyloc895/idp-microservices, mọi branch/tag
            "token.actions.githubusercontent.com:sub" = "repo:${var.github_org}/${var.github_repo}:*"
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
        # Chỉ cấp quyền push/pull trên 5 repos retail-store/* (principle of least privilege)
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
        Resource = [
          "arn:aws:ecr:${var.aws_region}:${var.ecr_account_id}:repository/retail-store/ui",
          "arn:aws:ecr:${var.aws_region}:${var.ecr_account_id}:repository/retail-store/catalog",
          "arn:aws:ecr:${var.aws_region}:${var.ecr_account_id}:repository/retail-store/cart",
          "arn:aws:ecr:${var.aws_region}:${var.ecr_account_id}:repository/retail-store/orders",
          "arn:aws:ecr:${var.aws_region}:${var.ecr_account_id}:repository/retail-store/checkout",
        ]
      }
    ]
  })
}
