# -- Step Function --
resource "aws_sfn_state_machine" "ingest_to_sds" {
  name = local.service_prefix
  role_arn = aws_iam_role.sfn.arn

  definition = jsonencode({
    StartAt = "SubmitToSDS"
    States = {
      SubmitToSDS = {
        Type = "Task"
        Resource = aws_lambda_function.submit_to_sds.arn
        Next = "CheckJobs"
      }

      CheckJobs = {
        Type = "Choice",
        Choices = [{
            Variable = "$.jobs[0]"
            IsPresent = true
            Next = "Wait"
        }],
        Default = "Done"
      }

      Wait = {
        Type = "Wait"
        Seconds = 60
        Next = "PollStatus"
      }

      PollStatus = {
        Type = "Task"
        Resource = aws_lambda_function.poll_status.arn
        Next = "CheckJobs"
      }

      Done = {
        Type = "Succeed"
      }
    }
  })
}

# -- IAM --
resource "aws_iam_role" "sfn" {
  name = "sfn"
  path = "${local.service_path}/"

  permissions_boundary = "arn:aws:iam::${local.account_id}:policy/NGAPShRoleBoundary"
  managed_policy_arns = [
    "arn:aws:iam::${local.account_id}:policy/NGAPProtAppInstanceMinimalPolicy"
  ]

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "states.amazonaws.com"
      }
    }]
  })

  inline_policy {
    name = "LambdasExecute"
    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [{
        Sid = ""
        Action = "lambda:InvokeFunction"
        Effect   = "Allow"
        Resource = [
          "arn:aws:ssm:${var.region}:${local.account_id}:function:${aws_lambda_function.submit_to_sds.function_name}",
          "arn:aws:ssm:${var.region}:${local.account_id}:function:${aws_lambda_function.poll_status.function_name}",
        ]
      }]
    })
  }
}
