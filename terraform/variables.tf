variable "project_name" {
  description = "Short project prefix used in resource names."
  type        = string
  default     = "tenantforge"
}

variable "tenant_id" {
  description = "Customer tenant identifier used in resource names and tags."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.tenant_id))
    error_message = "tenant_id must contain only lowercase letters, digits, and hyphens."
  }
}

variable "environment" {
  description = "Deployment environment for the tenant."
  type        = string

  validation {
    condition     = contains(["staging", "prod"], var.environment)
    error_message = "environment must be either staging or prod."
  }
}

variable "vpc_cidr" {
  description = "CIDR block for the tenant VPC; prefix must be /16 through /24."
  type        = string
  default     = "10.20.0.0/16"

  validation {
    condition = (
      can(cidrnetmask(var.vpc_cidr))
      && tonumber(split("/", var.vpc_cidr)[1]) >= 16
      && tonumber(split("/", var.vpc_cidr)[1]) <= 24
    )
    error_message = "vpc_cidr must be a valid CIDR block with a prefix between /16 and /24."
  }
}

variable "aws_region" {
  description = "AWS region for tenant resources."
  type        = string
  default     = "us-east-1"
}

variable "availability_zone" {
  description = "Availability zone for the tenant private subnet."
  type        = string
  default     = "us-east-1a"
}
