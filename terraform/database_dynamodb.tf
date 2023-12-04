# -- Tables --

// This is mapped from the Terraform infrastructure defined in the
// podaac/swodlr-api repo
data "aws_dynamodb_table" "ingest" {
  name = "${local.app_prefix}-ingest"
}

data "aws_dynamodb_table" "available_tiles" {
  name = "${local.app_prefix}-available-tiles"
}
