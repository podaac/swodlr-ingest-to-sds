# -- SQS --

// This is mapped from the Terraform infrastructure defined in the
// podaac/swodlr-api repo
data "aws_sqs_queue" "ingest" {
  name = "${local.app_prefix}-ingest-queue"
}

# -- Event Mapping --
resource "aws_lambda_event_source_mapping" "ingest_queue" {
  event_source_arn = data.aws_sqs_queue.ingest.arn
  function_name = aws_lambda_function.bootstrap.arn
}
