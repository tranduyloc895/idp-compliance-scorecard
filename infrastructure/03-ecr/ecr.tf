# ECR Repositories cho Retail Store Microservices
# Chi phí: chỉ tính theo dung lượng image lưu trữ ($0.10/GB/tháng)
# Lifecycle policy tự động xóa image cũ để giảm chi phí

locals {
  services = ["ui", "catalog", "cart", "orders", "checkout"]
}

resource "aws_ecr_repository" "services" {
  for_each = toset(local.services)

  name                 = "retail-store/${each.key}"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

# Lifecycle policy: giữ tối đa 5 tagged images, xóa untagged sau 1 ngày
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
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Keep only last 5 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 5
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
