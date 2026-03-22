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
  visibility_timeout_seconds = 40
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


# ==================
# IAM Role for Lambda
# ==================

resource "aws_iam_role" "lambda_role" {
  name = "careplan-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# 基本权限：写 CloudWatch 日志
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# 读写 SQS 权限
resource "aws_iam_role_policy_attachment" "lambda_sqs" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSQSFullAccess"
}

# 读写 RDS 权限
resource "aws_iam_role_policy_attachment" "lambda_rds" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonRDSFullAccess"
}

# ==================
# Lambda Functions
# ==================

resource "aws_lambda_function" "create_order" {
  filename      = "lambda.zip"
  source_code_hash = filebase64sha256("lambda.zip")
  function_name = "careplan-create-order"
  role          = aws_iam_role.lambda_role.arn
  handler       = "careplan.lambda_handlers.create_order_handler"
  runtime       = "python3.11"
  timeout       = 30

  layers = [
    "arn:aws:lambda:us-east-1:148124689982:layer:psycopg2-linux:2",
    "arn:aws:lambda:us-east-1:148124689982:layer:careplan-llm-layer:2"
  ]

  environment {
    variables = {
      DJANGO_SETTINGS_MODULE = "careplan.settings_lambda"
      SQS_URL                = aws_sqs_queue.order_queue.url
      DB_HOST                = aws_db_instance.careplan.address
      DB_NAME                = "careplan"
      DB_USER                = "careplan_admin"
      DB_PASSWORD            = var.db_password
    }
  }
}

resource "aws_lambda_function" "generate_careplan" {
  filename      = "lambda.zip"
  source_code_hash = filebase64sha256("lambda.zip")
  function_name = "careplan-generate-careplan"
  role          = aws_iam_role.lambda_role.arn
  handler       = "careplan.lambda_handlers.generate_careplan_handler"
  runtime       = "python3.11"
  timeout       = 30

  layers = [
    "arn:aws:lambda:us-east-1:148124689982:layer:psycopg2-linux:2",
    "arn:aws:lambda:us-east-1:148124689982:layer:careplan-llm-layer:2"
  ]

  environment {
    variables = {
      DJANGO_SETTINGS_MODULE = "careplan.settings_lambda"
      DB_HOST                = aws_db_instance.careplan.address
      DB_NAME                = "careplan"
      DB_USER                = "careplan_admin"
      DB_PASSWORD            = var.db_password
    }
  }
}

resource "aws_lambda_function" "get_order" {
  filename      = "lambda.zip"
  source_code_hash = filebase64sha256("lambda.zip")
  function_name = "careplan-get-order"
  role          = aws_iam_role.lambda_role.arn
  handler       = "careplan.lambda_handlers.get_order_handler"
  runtime       = "python3.11"
  timeout       = 30

  layers = [
    "arn:aws:lambda:us-east-1:148124689982:layer:psycopg2-linux:2",
    "arn:aws:lambda:us-east-1:148124689982:layer:careplan-llm-layer:2"
  ]

  environment {
    variables = {
      DJANGO_SETTINGS_MODULE = "careplan.settings_lambda"
      DB_HOST                = aws_db_instance.careplan.address
      DB_NAME                = "careplan"
      DB_USER                = "careplan_admin"
      DB_PASSWORD            = var.db_password
    }
  }
}


# ==================
# API Gateway
# ==================

resource "aws_apigatewayv2_api" "careplan" {
  name          = "careplan-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["Content-Type"]
  }
}

# 部署阶段
resource "aws_apigatewayv2_stage" "careplan" {
  api_id      = aws_apigatewayv2_api.careplan.id
  name        = "prod"
  auto_deploy = true
}

# ==================
# API Gateway 路由
# ==================

# POST /orders → create_order Lambda
resource "aws_apigatewayv2_integration" "create_order" {
  api_id                 = aws_apigatewayv2_api.careplan.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.create_order.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "create_order" {
  api_id    = aws_apigatewayv2_api.careplan.id
  route_key = "POST /orders"
  target    = "integrations/${aws_apigatewayv2_integration.create_order.id}"
}

# GET /orders/{id} → get_order Lambda
resource "aws_apigatewayv2_integration" "get_order" {
  api_id                 = aws_apigatewayv2_api.careplan.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.get_order.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "get_order" {
  api_id    = aws_apigatewayv2_api.careplan.id
  route_key = "GET /orders/{id}"
  target    = "integrations/${aws_apigatewayv2_integration.get_order.id}"
}

# 允许 API Gateway 调用 Lambda
resource "aws_lambda_permission" "create_order" {
  statement_id  = "AllowAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.create_order.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.careplan.execution_arn}/*/*"
}

resource "aws_lambda_permission" "get_order" {
  statement_id  = "AllowAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_order.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.careplan.execution_arn}/*/*"
}

# 输出 API URL
output "api_url" {
  value = aws_apigatewayv2_stage.careplan.invoke_url
}

# SQS 触发 generate_careplan Lambda
resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn = aws_sqs_queue.order_queue.arn
  function_name    = aws_lambda_function.generate_careplan.arn
  batch_size       = 1
}

# 允许 Lambda 读取 SQS
resource "aws_iam_role_policy_attachment" "lambda_sqs_trigger" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaSQSQueueExecutionRole"
}
