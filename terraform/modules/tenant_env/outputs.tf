output "tenant_vpc_id" {
  description = "ID of the tenant VPC."
  value       = aws_vpc.tenant.id
}

output "tenant_private_subnet_id" {
  description = "ID of the tenant private subnet."
  value       = aws_subnet.private.id
}

output "tenant_ingest_bucket_arn" {
  description = "ARN of the tenant ingest logs bucket."
  value       = aws_s3_bucket.ingest_logs.arn
}
