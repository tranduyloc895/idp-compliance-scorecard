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

locals {
  resolved_ami = var.ami_id != "" ? var.ami_id : data.aws_ami.amazon_linux_2023.id
}

# ─── Security Group ────────────────────────────────────────────────────────

resource "aws_security_group" "backstage" {
  name        = "backstage-sg"
  description = "Security group for Backstage IDP Portal EC2 instance"
  vpc_id      = var.vpc_id

  # Backstage UI (served via nginx reverse proxy or direct)
  ingress {
    description = "Backstage UI"
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Backstage backend API (internal auth callbacks)
  ingress {
    description = "Backstage Backend API"
    from_port   = 7007
    to_port     = 7007
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # SSH access
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ssh_cidrs
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

resource "aws_iam_instance_profile" "backstage_ec2" {
  name = "backstage-ec2-profile"
  role = aws_iam_role.backstage_ec2.name
}

# ─── EC2 Instance ──────────────────────────────────────────────────────────

resource "aws_instance" "backstage" {
  ami                         = local.resolved_ami
  instance_type               = var.instance_type
  subnet_id                   = var.subnet_id
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

  lifecycle {
    # Prevent destroy if instance type changes — just stop/start
    create_before_destroy = false
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
