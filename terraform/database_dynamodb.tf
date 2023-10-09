# -- Tables --

// This is mapped from the Terraform infrastructure defined in the
// podaac/swodlr-api repo
data "aws_dynamodb_table" "ingest" {
  name = "${local.app_prefix}-ingest"
}

data "aws_dynamodb_table" "avalible_tiles" {
  name = "${local.app_prefix}-avalible-tiles"
}
