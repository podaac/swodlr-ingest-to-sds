# -- VPC & Subnets --
data "aws_vpc" "default" {
    tags = {
        "Name": "Application VPC"
    }
}

data "aws_subnets" "private" {
    filter {
        name   = "vpc-id"
        values = [data.aws_vpc.default.id]
    }

    filter {
        name   = "tag:Name"
        values = ["Private application*"]
    }
}

# -- Security Group --
resource "aws_security_group" "default" {
  name = "${local.service_path}/default"
  vpc_id = data.aws_vpc.default.id

  egress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }
}