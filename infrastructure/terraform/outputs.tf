/**
 * Terraform Outputs
 * ================
 * Export important values for reference and CI/CD integration.
 */

# ============================================================================
# S3 Outputs
# ============================================================================

output "s3_cache_bucket_name" {
  description = "S3 bucket name for Parquet cache"
  value       = aws_s3_bucket.cache.bucket
}

output "s3_cache_bucket_arn" {
  description = "S3 bucket ARN for Parquet cache"
  value       = aws_s3_bucket.cache.arn
}

output "s3_lambda_artifacts_bucket" {
  description = "S3 bucket for Lambda deployment packages"
  value       = aws_s3_bucket.lambda_artifacts.bucket
}

# ============================================================================
# IAM Outputs
# ============================================================================

output "lambda_execution_role_arn" {
  description = "IAM role ARN for Lambda execution"
  value       = aws_iam_role.lambda_execution.arn
}

# ============================================================================
# Secrets Manager Outputs
# ============================================================================

output "secrets_manager_arn" {
  description = "ARN of main Secrets Manager secret"
  value       = aws_secretsmanager_secret.main.arn
}

output "secrets_manager_name" {
  description = "Name of main Secrets Manager secret"
  value       = aws_secretsmanager_secret.main.name
}

# ============================================================================
# Lambda Outputs
# ============================================================================

output "lambda_function_names" {
  description = "Names of all Lambda functions"
  value = {
    ingest     = aws_lambda_function.ingest.function_name
    trades_api = aws_lambda_function.trades_api.function_name
    data_api   = aws_lambda_function.data_api.function_name
    strategies_api = aws_lambda_function.strategies_api.function_name
    scanner_api = aws_lambda_function.scanner_api.function_name
  }
}

# ============================================================================
# General Outputs
# ============================================================================

output "environment" {
  description = "Deployment environment"
  value       = var.environment
}

output "aws_region" {
  description = "AWS region"
  value       = var.aws_region
}
