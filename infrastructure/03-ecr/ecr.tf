# ============================================================
# ECR — lớp NỀN: giữ lại giữa các buổi lab (chi phí theo GB lưu trữ).
# 5 service Retail Store + compliance-engine (audit #9).
# force_delete = false: `terraform destroy` không xoá được repo còn image,
# tránh mất image khi dọn nhầm (lỗi bổ sung: ECR bị xoá mỗi lần destroy).
# ============================================================

locals {
  repositories = ["ui", "catalog", "cart", "orders", "checkout", "compliance-engine"]
}

resource "aws_ecr_repository" "services" {
  for_each = toset(local.repositories)

  name                 = "${var.repository_prefix}/${each.key}"
  image_tag_mutability = "MUTABLE"
  force_delete         = false

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }
}

# Lifecycle: xoá untagged sau 1 ngày, giữ N image gần nhất.
resource "aws_ecr_lifecycle_policy" "services" {
  for_each   = aws_ecr_repository.services
  repository = each.value.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Remove untagged images after 1 day"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 1
        }
        action = { type = "expire" }
      },
      {
        rulePriority = 2
        description  = "Keep only the last ${var.keep_images} images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = var.keep_images
        }
        action = { type = "expire" }
      }
    ]
  })
}
