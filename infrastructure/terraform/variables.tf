/**
 * Terraform Variables
 * ===================
 * Input variables for infrastructure configuration.
 */

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod"
  }
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

# ============================================================================
# S3 Configuration
# ============================================================================

variable "s3_bucket_name" {
  description = "S3 bucket name for Parquet cache storage"
  type        = string
  default     = "potential-parakeet-cache"
}

variable "s3_cache_prefix" {
  description = "S3 prefix for cache files"
  type        = string
  default     = "cache/"
}

variable "enable_s3_versioning" {
  description = "Enable S3 bucket versioning"
  type        = bool
  default     = false
}

variable "s3_lifecycle_expiration_days" {
  description = "Days until S3 objects expire (0 = never)"
  type        = number
  default     = 0
}

# ============================================================================
# Lambda Configuration
# ============================================================================

variable "lambda_runtime" {
  description = "Lambda runtime version"
  type        = string
  default     = "python3.11"
}

variable "lambda_memory_size" {
  description = "Lambda memory allocation in MB"
  type        = number
  default     = 512

  validation {
    condition     = var.lambda_memory_size >= 128 && var.lambda_memory_size <= 10240
    error_message = "Lambda memory must be between 128 and 10240 MB"
  }
}

variable "lambda_timeout" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 60

  validation {
    condition     = var.lambda_timeout >= 1 && var.lambda_timeout <= 900
    error_message = "Lambda timeout must be between 1 and 900 seconds"
  }
}

variable "lambda_ephemeral_storage_size" {
  description = "Lambda ephemeral storage in MB"
  type        = number
  default     = 512

  validation {
    condition     = var.lambda_ephemeral_storage_size >= 512 && var.lambda_ephemeral_storage_size <= 10240
    error_message = "Ephemeral storage must be between 512 and 10240 MB"
  }
}

variable "lambda_reserved_concurrent_executions" {
  description = "Reserved concurrent executions for Lambda functions (0 = unreserved)"
  type        = number
  default     = 0
}

# ============================================================================
# Database Configuration (Neon)
# ============================================================================

variable "neon_database_url" {
  description = "Neon PostgreSQL connection string (stored in Secrets Manager)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "db_username" {
  description = "Database username"
  type        = string
  sensitive   = true
  default     = ""
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
  default     = ""
}

variable "db_host" {
  description = "Database host"
  type        = string
  default     = ""
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "potential_parakeet"
}

# ============================================================================
# API Gateway Configuration
# ============================================================================

variable "api_gateway_stage_name" {
  description = "API Gateway stage name"
  type        = string
  default     = "v1"
}

variable "enable_api_gateway_logging" {
  description = "Enable API Gateway execution logging"
  type        = bool
  default     = true
}

variable "api_throttle_rate_limit" {
  description = "API Gateway throttle rate limit (requests per second)"
  type        = number
  default     = 1000
}

variable "api_throttle_burst_limit" {
  description = "API Gateway throttle burst limit"
  type        = number
  default     = 2000
}

# ============================================================================
# EventBridge (Scheduled Data Ingest)
# ============================================================================

variable "daily_ingest_schedule" {
  description = "Cron expression for daily data ingest (UTC)"
  type        = string
  default     = "cron(0 6 * * ? *)" # 6 AM UTC daily
}

variable "enable_daily_ingest" {
  description = "Enable daily data ingest scheduler"
  type        = bool
  default     = true
}

# ============================================================================
# API Keys (stored in Secrets Manager)
# ============================================================================

variable "tiingo_api_key" {
  description = "Tiingo API key for market data"
  type        = string
  sensitive   = true
  default     = ""
}

variable "polygon_api_key" {
  description = "Polygon.io API key"
  type        = string
  sensitive   = true
  default     = ""
}

# ============================================================================
# Monitoring & Alerting
# ============================================================================

variable "enable_cloudwatch_alarms" {
  description = "Enable CloudWatch alarms"
  type        = bool
  default     = true
}

variable "alert_email" {
  description = "Email for CloudWatch alarm notifications"
  type        = string
  default     = ""
}

variable "lambda_error_alarm_threshold" {
  description = "Number of errors to trigger alarm"
  type        = number
  default     = 5
}

variable "lambda_duration_alarm_threshold_ms" {
  description = "Lambda duration threshold for alarm (milliseconds)"
  type        = number
  default     = 50000 # 50 seconds
}

# ============================================================================
# Tags
# ============================================================================

variable "additional_tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# ============================================================================
# Cloudflare Access (JWT Authorization)
# ============================================================================

variable "cloudflare_team_domain" {
  description = "Cloudflare Access team domain (e.g., 'mycompany' for mycompany.cloudflareaccess.com)"
  type        = string
  default     = "potential-parakeet"
}

variable "cloudflare_access_audience" {
  description = "Cloudflare Access application audience tag (AUD claim from Access policy)"
  type        = string
  default     = ""
  sensitive   = true
}
