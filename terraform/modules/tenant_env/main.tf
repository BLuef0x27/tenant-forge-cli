locals {
  name_prefix = "${var.project_name}-${var.tenant_id}-${var.environment}"
  common_tags = {
    Tenant      = var.tenant_id
    Environment = var.environment
    ManagedBy   = "TenantForge-Terraform"
  }
}

resource "aws_vpc" "tenant" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-vpc"
  })
}

resource "aws_subnet" "private" {
  vpc_id                  = aws_vpc.tenant.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 4, 1)
  availability_zone       = var.availability_zone
  map_public_ip_on_launch = false

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-private"
  })
}

resource "aws_s3_bucket" "ingest_logs" {
  bucket        = "${local.name_prefix}-ingest-logs"
  force_destroy = true

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-ingest-logs"
  })
}

resource "aws_s3_bucket_server_side_encryption_configuration" "ingest_logs" {
  bucket = aws_s3_bucket.ingest_logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "ingest_logs" {
  bucket = aws_s3_bucket.ingest_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
