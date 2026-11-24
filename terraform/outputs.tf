output "tenant_vpc_id" {
  description = "ID of the tenant VPC."
  value       = module.tenant_env.tenant_vpc_id
}

output "tenant_private_subnet_id" {
  description = "ID of the tenant private subnet."
  value       = module.tenant_env.tenant_private_subnet_id
}

output "tenant_ingest_bucket_arn" {
  description = "ARN of the tenant ingest logs bucket."
  value       = module.tenant_env.tenant_ingest_bucket_arn
}
