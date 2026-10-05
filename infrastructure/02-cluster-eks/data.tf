# Find VPC by name tag
data "aws_vpc" "ecommerce" {
  tags = {
    Name = var.vpc_name
  }
}

# Find Private Subnets in the VPC with the tag "kubernetes.io/role/internal-elb" = "1"
data "aws_subnets" "private" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.ecommerce.id]
  }

  tags = {
    "kubernetes.io/role/internal-elb" = "1"
  }
}

# Data sources for Jenkins Agent IAM role and Security Group were removed
# after migrating to GitOps. Module 02-cluster-eks no longer references
# anything from 03-jenkins-server, eliminating the cross-module dependency
# that previously caused issues during teardown.
