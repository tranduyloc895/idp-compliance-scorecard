# ─── Data Sources ──────────────────────────────────────────────────────────

# Lookup latest Amazon Linux 2023 AMI if ami_id is not provided
data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# VPC/subnet lấy từ remote state của 01-network (audit #4: không nhập tay vpc_id/subnet_id).
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
  resolved_ami = var.ami_id != "" ? var.ami_id : data.aws_ami.amazon_linux_2023.id
  vpc_id       = data.terraform_remote_state.network.outputs.vpc_id
  subnet_id    = data.terraform_remote_state.network.outputs.public_subnet_ids[0]
}

# ─── Security Group ────────────────────────────────────────────────────────

resource "aws_security_group" "backstage" {
  name        = "backstage-sg"
  description = "Security group for Backstage IDP Portal EC2 instance"
  vpc_id      = local.vpc_id

  # Backstage production build: backend phục vụ cả frontend trên MỘT port 7007
  # (audit #23 — trước đây publish 3000:7007 nhưng URL/callback dùng 7007).
  ingress {
    description = "Backstage (frontend + backend)"
    from_port   = 7007
    to_port     = 7007
    protocol    = "tcp"
    cidr_blocks = var.allowed_http_cidrs
  }

  # SSH chỉ mở khi có key pair; mặc định truy cập bằng SSM Session Manager.
  dynamic "ingress" {
    for_each = var.key_name != "" ? [1] : []
    content {
      description = "SSH"
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = var.allowed_ssh_cidrs
    }
  }

  # All outbound traffic
  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "backstage-sg"
  }
}

# ─── IAM Role & Instance Profile (SSM Session Manager) ────────────────────

resource "aws_iam_role" "backstage_ec2" {
  name = "backstage-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

# Attach SSM core policy — allows Session Manager access (no SSH key needed)
resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.backstage_ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Optional: read-only ECR access so Backstage can pull catalog info
resource "aws_iam_role_policy_attachment" "ecr_readonly" {
  role       = aws_iam_role.backstage_ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

# Đọc secret và URL compliance engine (do aws-up ghi) từ SSM Parameter Store.
resource "aws_iam_role_policy" "ssm_params_read" {
  name = "read-idp-ssm-parameters"
  role = aws_iam_role.backstage_ec2.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["ssm:GetParameter", "ssm:GetParameters", "ssm:GetParametersByPath"]
      Resource = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${var.ssm_prefix}/*"
    }]
  })
}

resource "aws_iam_instance_profile" "backstage_ec2" {
  name = "backstage-ec2-profile"
  role = aws_iam_role.backstage_ec2.name
}

# ─── EC2 Instance ──────────────────────────────────────────────────────────

resource "aws_instance" "backstage" {
  ami                         = local.resolved_ami
  instance_type               = var.instance_type
  subnet_id                   = local.subnet_id
  vpc_security_group_ids      = [aws_security_group.backstage.id]
  iam_instance_profile        = aws_iam_instance_profile.backstage_ec2.name
  key_name                    = var.key_name != "" ? var.key_name : null
  associate_public_ip_address = true

  user_data = file("${path.module}/userdata.sh")

  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.volume_size_gb
    delete_on_termination = true
    encrypted             = true
  }

  tags = {
    Name = "backstage-portal"
  }

}

# ─── Elastic IP ────────────────────────────────────────────────────────────
# Fixed IP so the GitHub OAuth callback URL never changes.

resource "aws_eip" "backstage" {
  instance = aws_instance.backstage.id
  domain   = "vpc"

  tags = {
    Name = "backstage-eip"
  }

  # EIP must be released before instance is destroyed
  depends_on = [aws_instance.backstage]
}
