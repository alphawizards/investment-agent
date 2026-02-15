/**
 * Lambda Functions Configuration
 * ===============================
 * Serverless compute for API endpoints and scheduled tasks.
 *
 * Functions:
 * 1. Ingest - Daily data ingestion (triggered by EventBridge)
 * 2. Trades API - Trading operations
 * 3. Data API - Market data queries
 * 4. Strategies API - Strategy management
 * 5. Scanner API - Stock scanning
 */

# ============================================================================
# Local Variables
# ============================================================================

locals {
  region     = var.aws_region
  account_id = data.aws_caller_identity.current.account_id

  common_tags = merge(
    {
      Project     = "potential-parakeet"
      Environment = var.environment
      ManagedBy   = "terraform"
    },
    var.additional_tags
  )

  # Common Lambda environment variables
  lambda_environment = {
    ENVIRONMENT       = var.environment
    AWS_S3_BUCKET     = aws_s3_bucket.cache.id
    SECRETS_ARN       = aws_secretsmanager_secret.main.arn
    API_KEYS_ARN      = aws_secretsmanager_secret.api_keys.arn
    LOG_LEVEL         = var.environment == "prod" ? "INFO" : "DEBUG"
    POWERTOOLS_SERVICE_NAME = "potential-parakeet"
  }
}

# Data source for account ID
data "aws_caller_identity" "current" {}

# ============================================================================
# Lambda Function: Daily Data Ingest
# ============================================================================

resource "aws_lambda_function" "ingest" {
  # checkov:skip=CKV_AWS_117:VPC placement is cost-prohibitive (NAT Gateway)
  # checkov:skip=CKV_AWS_272:Code signing is not required for this internal tool
  # checkov:skip=CKV_AWS_116:DLQ is configured below via dead_letter_config
  function_name = "potential-parakeet-ingest-${var.environment}"
  description   = "Daily market data ingestion from Tiingo/Polygon"
  role          = aws_iam_role.lambda_execution.arn

  # Use local file for initial deployment (switch to S3 in CI/CD later)
  filename         = "${path.module}/../lambda-packages/ingest.zip"
  source_code_hash = filebase64sha256("${path.module}/../lambda-packages/ingest.zip")

  runtime     = var.lambda_runtime
  handler     = "handler.lambda_handler"
  memory_size = 1024  # Higher memory for data processing
  timeout     = 300   # 5 minutes for large data pulls

  ephemeral_storage {
    size = 1024  # 1GB for temporary data files
  }

  environment {
    # checkov:skip=CKV_AWS_173:KMS CMK for env vars is cost-prohibitive
    variables = merge(local.lambda_environment, {
      FUNCTION_TYPE = "ingest"
    })
  }

  dead_letter_config {
    target_arn = aws_sqs_queue.lambda_dlq.arn
  }

  # checkov:skip=CKV_AWS_117:VPC placement is cost-prohibitive (NAT Gateway)

  reserved_concurrent_executions = var.lambda_reserved_concurrent_executions > 0 ? var.lambda_reserved_concurrent_executions : null

  tracing_config {
    mode = "Active"  # Enable X-Ray tracing
  }

  tags = merge(local.common_tags, {
    Name     = "ingest-lambda-${var.environment}"
    Function = "data-ingestion"
  })

  # Ignore changes to source code (updated by CI/CD)
  lifecycle {
    ignore_changes = [filename, source_code_hash]
  }
}

# ============================================================================
# Lambda Function: Trades API
# ============================================================================

resource "aws_lambda_function" "trades_api" {
  # checkov:skip=CKV_AWS_117:VPC placement is cost-prohibitive
  # checkov:skip=CKV_AWS_272:Code signing is not required
  # checkov:skip=CKV_AWS_116:DLQ is configured below
  # checkov:skip=CKV_AWS_115:Concurrent execution limit is intentionally unreserved
  function_name = "potential-parakeet-trades-api-${var.environment}"
  description   = "Trading operations API"
  role          = aws_iam_role.lambda_execution.arn

  # Use local file for initial deployment
  filename         = "${path.module}/../lambda-packages/trades_api.zip"
  source_code_hash = filebase64sha256("${path.module}/../lambda-packages/trades_api.zip")

  runtime     = var.lambda_runtime
  handler     = "handler.lambda_handler"
  memory_size = var.lambda_memory_size
  timeout     = var.lambda_timeout

  ephemeral_storage {
    size = var.lambda_ephemeral_storage_size
  }

  environment {
    # checkov:skip=CKV_AWS_173:KMS CMK for env vars is cost-prohibitive
    variables = merge(local.lambda_environment, {
      FUNCTION_TYPE = "trades_api"
    })
  }

  dead_letter_config {
    target_arn = aws_sqs_queue.lambda_dlq.arn
  }

  # checkov:skip=CKV_AWS_117:VPC placement is cost-prohibitive (NAT Gateway)

  tracing_config {
    mode = "Active"
  }

  tags = merge(local.common_tags, {
    Name     = "trades-api-lambda-${var.environment}"
    Function = "api-trades"
  })

  lifecycle {
    ignore_changes = [filename, source_code_hash]
  }
}

# ============================================================================
# Lambda Function: Data API
# ============================================================================

resource "aws_lambda_function" "data_api" {
  # checkov:skip=CKV_AWS_117:VPC placement is cost-prohibitive
  # checkov:skip=CKV_AWS_272:Code signing is not required
  # checkov:skip=CKV_AWS_115:Concurrent execution limit is intentionally unreserved
  function_name = "potential-parakeet-data-api-${var.environment}"
  description   = "Market data queries API"
  role          = aws_iam_role.lambda_execution.arn

  # Use local file for initial deployment
  filename         = "${path.module}/../lambda-packages/data_api.zip"
  source_code_hash = filebase64sha256("${path.module}/../lambda-packages/data_api.zip")

  runtime     = var.lambda_runtime
  handler     = "handler.lambda_handler"
  memory_size = var.lambda_memory_size
  timeout     = var.lambda_timeout

  ephemeral_storage {
    size = var.lambda_ephemeral_storage_size
  }

  environment {
    # checkov:skip=CKV_AWS_173:KMS CMK for env vars is cost-prohibitive
    variables = merge(local.lambda_environment, {
      FUNCTION_TYPE = "data_api"
    })
  }

  dead_letter_config {
    target_arn = aws_sqs_queue.lambda_dlq.arn
  }

  tracing_config {
    mode = "Active"
  }

  tags = merge(local.common_tags, {
    Name     = "data-api-lambda-${var.environment}"
    Function = "api-data"
  })

  lifecycle {
    ignore_changes = [filename, source_code_hash]
  }
}

# ============================================================================
# Lambda Function: Strategies API
# ============================================================================

resource "aws_lambda_function" "strategies_api" {
  # checkov:skip=CKV_AWS_117:VPC placement is cost-prohibitive
  # checkov:skip=CKV_AWS_272:Code signing is not required
  # checkov:skip=CKV_AWS_115:Concurrent execution limit is intentionally unreserved
  function_name = "potential-parakeet-strategies-api-${var.environment}"
  description   = "Strategy management API"
  role          = aws_iam_role.lambda_execution.arn

  # Use local file for initial deployment
  filename         = "${path.module}/../lambda-packages/strategies_api.zip"
  source_code_hash = filebase64sha256("${path.module}/../lambda-packages/strategies_api.zip")

  runtime     = var.lambda_runtime
  handler     = "handler.lambda_handler"
  memory_size = var.lambda_memory_size
  timeout     = var.lambda_timeout

  ephemeral_storage {
    size = var.lambda_ephemeral_storage_size
  }

  environment {
    # checkov:skip=CKV_AWS_173:KMS CMK for env vars is cost-prohibitive
    variables = merge(local.lambda_environment, {
      FUNCTION_TYPE = "strategies_api"
    })
  }

  dead_letter_config {
    target_arn = aws_sqs_queue.lambda_dlq.arn
  }

  tracing_config {
    mode = "Active"
  }

  tags = merge(local.common_tags, {
    Name     = "strategies-api-lambda-${var.environment}"
    Function = "api-strategies"
  })

  lifecycle {
    ignore_changes = [filename, source_code_hash]
  }
}

# ============================================================================
# Lambda Function: Scanner API
# ============================================================================

resource "aws_lambda_function" "scanner_api" {
  # checkov:skip=CKV_AWS_117:VPC placement is cost-prohibitive
  # checkov:skip=CKV_AWS_272:Code signing is not required
  # checkov:skip=CKV_AWS_115:Concurrent execution limit is intentionally unreserved
  function_name = "potential-parakeet-scanner-api-${var.environment}"
  description   = "Stock scanning API"
  role          = aws_iam_role.lambda_execution.arn

  # Use local file for initial deployment
  filename         = "${path.module}/../lambda-packages/scanner_api.zip"
  source_code_hash = filebase64sha256("${path.module}/../lambda-packages/scanner_api.zip")

  runtime     = var.lambda_runtime
  handler     = "handler.lambda_handler"
  memory_size = 1024  # Higher memory for scanning operations
  timeout     = 120   # 2 minutes for complex scans

  ephemeral_storage {
    size = var.lambda_ephemeral_storage_size
  }

  environment {
    # checkov:skip=CKV_AWS_173:KMS CMK for env vars is cost-prohibitive
    variables = merge(local.lambda_environment, {
      FUNCTION_TYPE = "scanner_api"
    })
  }

  dead_letter_config {
    target_arn = aws_sqs_queue.lambda_dlq.arn
  }

  tracing_config {
    mode = "Active"
  }

  tags = merge(local.common_tags, {
    Name     = "scanner-api-lambda-${var.environment}"
    Function = "api-scanner"
  })

  lifecycle {
    ignore_changes = [filename, source_code_hash]
  }
}

# ============================================================================
# CloudWatch Log Groups (with retention)
# ============================================================================

resource "aws_cloudwatch_log_group" "ingest" {
  # checkov:skip=CKV_AWS_158:KMS encryption for logs is cost-prohibitive
  # checkov:skip=CKV_AWS_338:Log retention < 365 days to maintain zero-cost profile
  name              = "/aws/lambda/${aws_lambda_function.ingest.function_name}"
  retention_in_days = 90

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "trades_api" {
  # checkov:skip=CKV_AWS_158:KMS encryption for logs is cost-prohibitive
  # checkov:skip=CKV_AWS_338:Log retention < 365 days
  name              = "/aws/lambda/${aws_lambda_function.trades_api.function_name}"
  retention_in_days = 90

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "data_api" {
  # checkov:skip=CKV_AWS_158:KMS encryption for logs is cost-prohibitive
  # checkov:skip=CKV_AWS_338:Log retention < 365 days
  name              = "/aws/lambda/${aws_lambda_function.data_api.function_name}"
  retention_in_days = 90

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "strategies_api" {
  # checkov:skip=CKV_AWS_158:KMS encryption for logs is cost-prohibitive
  # checkov:skip=CKV_AWS_338:Log retention < 365 days
  name              = "/aws/lambda/${aws_lambda_function.strategies_api.function_name}"
  retention_in_days = 90

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "scanner_api" {
  # checkov:skip=CKV_AWS_158:KMS encryption for logs is cost-prohibitive
  # checkov:skip=CKV_AWS_338:Log retention < 365 days
  name              = "/aws/lambda/${aws_lambda_function.scanner_api.function_name}"
  retention_in_days = 90

  tags = local.common_tags
}

# ============================================================================
# SQS Dead Letter Queue (DLQ)
# ============================================================================

resource "aws_sqs_queue" "lambda_dlq" {
  # checkov:skip=CKV_AWS_27:SQS encryption with CMK is cost-prohibitive, using SSE-SQS
  name                      = "potential-parakeet-lambda-dlq-${var.environment}"
  message_retention_seconds = 1209600 # 14 days
  sqs_managed_sse_enabled   = true

  tags = local.common_tags
}
