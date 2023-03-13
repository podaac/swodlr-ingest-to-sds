terraform {
  required_version = ">=1.2.7"

  backend "s3" {
    key = "services/swodlr/ingest-to-sds/terraform.tfstate"
  }

  required_providers {
    aws = {
      source = "hashicorp/aws"
      version = ">=4.56.0"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = local.default_tags
  }

  ignore_tags {
    key_prefixes = ["gsfc-ngap"]
  }
}

data "aws_caller_identity" "current" {}

data "local_file" "pyproject_toml" {
  filename = abspath("${path.root}/../pyproject.toml")
}

locals {
  name        = regex("name = \"(\\S*)\"", data.local_file.pyproject_toml.content)[0]
  version     = regex("version = \"(\\S*)\"", data.local_file.pyproject_toml.content)[0]
  environment = var.stage

  app_prefix      = "service-${var.app_name}-${local.environment}"
  service_prefix  = "service-${var.app_name}-${local.environment}-${var.service_name}"
  service_path    = "/service/${var.app_name}/${var.service_name}"

  sds_ca_cert = file(var.sds_ca_cert_path)

  account_id = data.aws_caller_identity.current.account_id

  default_tags = length(var.default_tags) == 0 ? {
    team = "TVA"
    application = local.app_prefix
    version     = local.version
    Environment = local.environment
  } : var.default_tags
}
