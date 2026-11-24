variable "project_name" {
  description = "Short project prefix used in resource names."
  type        = string
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
}

variable "availability_zone" {
  description = "Availability zone for the tenant private subnet."
  type        = string
}
