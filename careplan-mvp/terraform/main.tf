provider "aws" {
  region = "us-east-1"
}

# 第一步：先创建 DLQ（Dead Letter Queue）
resource "aws_sqs_queue" "order_dlq" {
  name = "careplan-order-dlq"
}

# 第二步：主队列，失败3次就把消息移到 DLQ
resource "aws_sqs_queue" "order_queue" {
  name = "careplan-order-queue"

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.order_dlq.arn
    maxReceiveCount     = 3
  })
}
# 拿到默认 VPC
data "aws_vpc" "default" {
  default = true
}
# 拿到默认 VPC 里的所有 Subnet
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# RDS 需要的 Subnet Group
resource "aws_db_subnet_group" "careplan" {
  name       = "careplan-subnet-group"
  subnet_ids = data.aws_subnets.default.ids
}

# RDS PostgreSQL
resource "aws_db_instance" "careplan" {
  identifier        = "careplan-db"
  engine            = "postgres"
  engine_version    = "16"
  instance_class    = "db.t3.micro"
  allocated_storage = 20

  db_name  = "careplan"
  username = "careplan_admin"
  password = var.db_password

  db_subnet_group_name = aws_db_subnet_group.careplan.name
  skip_final_snapshot  = true
  publicly_accessible  = true
}

# 密码从环境变量读取，不写死在代码里
variable "db_password" {
  description = "RDS 数据库密码"
  sensitive   = true
}
