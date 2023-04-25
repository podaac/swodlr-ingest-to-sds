# -- Lambdas --
resource "aws_lambda_function" "bootstrap" {
  function_name = "${local.service_prefix}-bootstrap"
  handler = "podaac.swodlr_ingest_to_sds.bootstrap.lambda_handler"

  role = aws_iam_role.bootstrap.arn
  runtime = "python3.9"

  filename = "${path.module}/../dist/${local.name}-${local.version}.zip"
  source_code_hash = filebase64sha256("${path.module}/../dist/${local.name}-${local.version}.zip")
}

resource "aws_lambda_function" "submit_to_sds" {
  function_name = "${local.service_prefix}-submit_to_sds"
  handler = "podaac.swodlr_ingest_to_sds.submit_to_sds.lambda_handler"

  role = aws_iam_role.lambda.arn
  runtime = "python3.9"

  filename = "${path.module}/../dist/${local.name}-${local.version}.zip"
  source_code_hash = filebase64sha256("${path.module}/../dist/${local.name}-${local.version}.zip")

  vpc_config {
    security_group_ids = [aws_security_group.default.id]
    subnet_ids = data.aws_subnets.private.ids
  }
}

resource "aws_lambda_function" "poll_status" {
  function_name = "${local.service_prefix}-poll_status"
  handler = "podaac.swodlr_ingest_to_sds.poll_status.lambda_handler"

  role = aws_iam_role.lambda.arn
  runtime = "python3.9"

  filename = "${path.module}/../dist/${local.name}-${local.version}.zip"
  source_code_hash = filebase64sha256("${path.module}/../dist/${local.name}-${local.version}.zip")

  vpc_config {
    security_group_ids = [aws_security_group.default.id]
    subnet_ids = data.aws_subnets.private.ids
  }
}

# -- IAM --
resource "aws_iam_policy" "ssm_parameters_read" {
  name = "SSMParametersReadOnlyAccess"
  path = "${local.service_path}/"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid = ""
      Action = [
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:GetParametersByPath"
      ]
      Effect   = "Allow"
      Resource = "arn:aws:ssm:${var.region}:${local.account_id}:parameter${local.service_path}/*"
    }]
  })
}

resource "aws_iam_policy" "lambda_networking" {
  name = "LambdaNetworkAccess"
  path = "${local.service_path}/"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = [
        "ec2:DescribeInstances",
        "ec2:CreateNetworkInterface",
        "ec2:AttachNetworkInterface",
        "ec2:DescribeNetworkInterfaces",
        "ec2:DeleteNetworkInterface"
      ]
      Effect   = "Allow"
      Resource = "*"
    }]
  })
}

resource "aws_iam_role" "bootstrap" {
  name = "bootstrap"
  path = "${local.service_path}/"

  permissions_boundary = "arn:aws:iam::${local.account_id}:policy/NGAPShRoleBoundary"
  managed_policy_arns = [
    "arn:aws:iam::${local.account_id}:policy/NGAPProtAppInstanceMinimalPolicy",
    aws_iam_policy.ssm_parameters_read.arn
  ]

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

  inline_policy {
    name = "BootstrapPolicy"
    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [
        {
          Sid = ""
          Action = "states:StartExecution"
          Effect   = "Allow"
          Resource = "arn:aws:states:${var.region}:${local.account_id}:stateMachine:${aws_sfn_state_machine.ingest_to_sds.name}"
        },

        {
          Sid = ""
          Action = [
            "sqs:ReceiveMessage",
            "sqs:DeleteMessage",
            "sqs:GetQueueAttributes"
          ]
          Effect   = "Allow"
          Resource = "arn:aws:sqs:${var.region}:${local.account_id}:${data.aws_sqs_queue.ingest.name}"
        }
      ]
    })
  }
}

resource "aws_iam_role" "lambda" {
  name = "lambda"
  path = "${local.service_path}/"

  permissions_boundary = "arn:aws:iam::${local.account_id}:policy/NGAPShRoleBoundary"
  managed_policy_arns = [
    "arn:aws:iam::${local.account_id}:policy/NGAPProtAppInstanceMinimalPolicy",
    aws_iam_policy.ssm_parameters_read.arn,
    aws_iam_policy.lambda_networking.arn
  ]

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

  inline_policy {
    name = "LambdaPolicy"
    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [
        {
          Sid = ""
          Action = [
            "dynamodb:BatchGetItem",
            "dynamodb:BatchWriteItem",
            "dynamodb:GetItem",
            "dynamodb:PutItem",
            "dynamodb:UpdateItem"
          ]
          Effect   = "Allow"
          Resource = data.aws_dynamodb_table.ingest.arn
        }
      ]
    })
  }
}

# -- SSM Parameters --
resource "aws_ssm_parameter" "sds_pcm_release_tag" {
  name  = "${local.service_path}/sds_pcm_release_tag"
  type  = "String"
  overwrite = true
  value = var.sds_pcm_release_tag
}

resource "aws_ssm_parameter" "sds_host" {
  name  = "${local.service_path}/sds_host"
  type  = "String"
  overwrite = true
  value = var.sds_host
}

resource "aws_ssm_parameter" "sds_username" {
  name  = "${local.service_path}/sds_username"
  type  = "String"
  overwrite = true
  value = var.sds_username
}

resource "aws_ssm_parameter" "sds_password" {
  name  = "${local.service_path}/sds_password"
  type  = "SecureString"
  overwrite = true
  value = var.sds_password
}

resource "aws_ssm_parameter" "sds_ca_cert" {
  name = "${local.service_path}/sds_ca_cert"
  type = "SecureString"
  overwrite = true
  value = local.sds_ca_cert
}

resource "aws_ssm_parameter" "stepfunction_arn" {
  name  = "${local.service_path}/stepfunction_arn"
  type  = "String"
  overwrite = true
  value = aws_sfn_state_machine.ingest_to_sds.arn
}

resource "aws_ssm_parameter" "ingest_queue_url" {
  name  = "${local.service_path}/ingest_queue_url"
  type  = "String"
  overwrite = true
  value = data.aws_sqs_queue.ingest.id
}

resource "aws_ssm_parameter" "ingest_table_name" {
  name  = "${local.service_path}/ingest_table_name"
  type  = "String"
  overwrite = true
  value = data.aws_dynamodb_table.ingest.name
}