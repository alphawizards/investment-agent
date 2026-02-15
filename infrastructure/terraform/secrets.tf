/**
 * AWS Secrets Manager Configuration
 * ==================================
 * Secure storage for database credentials and API keys.
 *
 * Secrets:
 * 1. Main secret: Database credentials and configuration
 * 2. API keys: Tiingo, Polygon, etc.
 *
 * Note: Secret values are set via Terraform variables or AWS Console.
 * Never commit actual secrets to version control!
 */

# ============================================================================
# Main Secret (Database Credentials)
# ============================================================================

resource "aws_secretsmanager_secret" "main" {
  # checkov:skip=CKV_AWS_149:KMS CMK is cost-prohibitive, using default key
  # checkov:skip=CKV2_AWS_57:Secret rotation is cost-prohibitive and requires maintenance
  name        = "potential-parakeet/${var.environment}"
  description = "Database credentials and configuration for Potential Parakeet ${var.environment}"

  recovery_window_in_days = var.environment == "prod" ? 30 : 7

  tags = merge(
    local.common_tags,
    {
      Name        = "main-secret-${var.environment}"
      SecretType  = "database-credentials"
    }
  )
}

# Secret version with database credentials
resource "aws_secretsmanager_secret_version" "main" {
  secret_id = aws_secretsmanager_secret.main.id

  secret_string = jsonencode({
    NEON_DATABASE_URL = var.neon_database_url != "" ? var.neon_database_url : "postgresql+asyncpg://user:pass@host/db?sslmode=require"
    DB_USERNAME       = var.db_username
    DB_PASSWORD       = var.db_password
    DB_HOST           = var.db_host
    DB_NAME           = var.db_name
    DB_PORT           = "5432"
    USE_NEON          = "true"
  })

  lifecycle {
    ignore_changes = [secret_string] # Prevent overwrites from Terraform after manual updates
  }
}

# ============================================================================
# API Keys Secret
# ============================================================================

resource "aws_secretsmanager_secret" "api_keys" {
  # checkov:skip=CKV_AWS_149:KMS CMK is cost-prohibitive, using default key
  # checkov:skip=CKV2_AWS_57:Secret rotation is cost-prohibitive
  name        = "potential-parakeet/${var.environment}/api-keys"
  description = "API keys for market data providers (${var.environment})"

  recovery_window_in_days = var.environment == "prod" ? 30 : 7

  tags = merge(
    local.common_tags,
    {
      Name       = "api-keys-secret-${var.environment}"
      SecretType = "api-keys"
    }
  )
}

resource "aws_secretsmanager_secret_version" "api_keys" {
  secret_id = aws_secretsmanager_secret.api_keys.id

  secret_string = jsonencode({
    TIINGO_API_KEY        = var.tiingo_api_key != "" ? var.tiingo_api_key : "your-tiingo-api-key"
    TIINGO_IS_PREMIUM     = "true"
    POLYGON_API_KEY       = var.polygon_api_key != "" ? var.polygon_api_key : "your-polygon-api-key"
    ALPHA_VANTAGE_API_KEY = ""
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}

# ============================================================================
# Secret Rotation (Optional - for production)
# ============================================================================

# Uncomment for production environments
# resource "aws_secretsmanager_secret_rotation" "main" {
#   count               = var.environment == "prod" ? 1 : 0
#   secret_id           = aws_secretsmanager_secret.main.id
#   rotation_lambda_arn = aws_lambda_function.secret_rotation[0].arn
#
#   rotation_rules {
#     automatically_after_days = 90
#   }
# }
