terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

module "tenant_env" {
  source = "./modules/tenant_env"

  project_name      = var.project_name
  tenant_id         = var.tenant_id
  environment       = var.environment
  vpc_cidr          = var.vpc_cidr
  availability_zone = var.availability_zone
}
