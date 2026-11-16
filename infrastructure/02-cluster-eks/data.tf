# Đọc output của 01-network qua remote state (thay cho việc tra VPC theo tag
# hoặc copy output bằng tay). Bucket truyền qua TF_VAR_state_bucket.
data "terraform_remote_state" "network" {
  backend = "s3"
  config = {
    bucket = var.state_bucket
    key    = "01-network/terraform.tfstate"
    region = var.aws_region
  }
}

data "aws_caller_identity" "current" {}

locals {
  vpc_id             = data.terraform_remote_state.network.outputs.vpc_id
  private_subnet_ids = data.terraform_remote_state.network.outputs.private_subnet_ids
}
