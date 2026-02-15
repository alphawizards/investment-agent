/**
 * IAM Roles and Policies
 * =======================
 * Least-privilege IAM configuration for Lambda functions.
 *
 * Permissions:
 * - CloudWatch Logs: Write execution logs
 * - S3: Read/Write cache files
 * - Secrets Manager: Read database credentials and API keys
 * - VPC: Network interfaces (if VPC-enabled)
 */

# ============================================================================
# Lambda Execution Role
# ============================================================================

# IAM role for Lambda function execution
resource "aws_iam_role" "lambda_execution" {
  name               = "potential-parakeet-lambda-execution-${var.environment}"
  description        = "Lambda execution role for Potential Parakeet"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json

  tags = merge(
    local.common_tags,
    {
      Name = "lambda-execution-role-${var.environment}"
    }
  )
}

# Allow Lambda service to assume this role
data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

# ============================================================================
# CloudWatch Logs Policy
# ============================================================================

resource "aws_iam_role_policy" "lambda_cloudwatch_logs" {
  name   = "cloudwatch-logs-policy"
  role   = aws_iam_role.lambda_execution.id
  policy = data.aws_iam_policy_document.lambda_cloudwatch_logs.json
}

data "aws_iam_policy_document" "lambda_cloudwatch_logs" {
  statement {
    effect = "Allow"

    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]

    resources = [
      "arn:aws:logs:${local.region}:${local.account_id}:log-group:/aws/lambda/potential-parakeet-*",
    ]
  }
}

# ============================================================================
# S3 Access Policy (Read/Write Cache)
# ============================================================================

resource "aws_iam_role_policy" "lambda_s3_access" {
  name   = "s3-cache-access-policy"
  role   = aws_iam_role.lambda_execution.id
  policy = data.aws_iam_policy_document.lambda_s3_access.json
}

data "aws_iam_policy_document" "lambda_s3_access" {
  # List buckets
  statement {
    effect = "Allow"

    actions = [
      "s3:ListBucket",
      "s3:GetBucketLocation",
    ]

    resources = [
      aws_s3_bucket.cache.arn,
    ]
  }

  # Read/Write cache objects
  statement {
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:GetObjectVersion",
    ]

    resources = [
      "${aws_s3_bucket.cache.arn}/*",
    ]
  }

  # Read Lambda artifacts
  statement {
    effect = "Allow"

    actions = [
      "s3:GetObject",
    ]

    resources = [
      "${aws_s3_bucket.lambda_artifacts.arn}/*",
    ]
  }
}

# ============================================================================
# Secrets Manager Access Policy
# ============================================================================

resource "aws_iam_role_policy" "lambda_secrets_manager" {
  name   = "secrets-manager-access-policy"
  role   = aws_iam_role.lambda_execution.id
  policy = data.aws_iam_policy_document.lambda_secrets_manager.json
}

data "aws_iam_policy_document" "lambda_secrets_manager" {
  statement {
    effect = "Allow"

    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret",
    ]

    resources = [
      aws_secretsmanager_secret.main.arn,
      aws_secretsmanager_secret.api_keys.arn,
    ]
  }
}

# ============================================================================
# VPC Access Policy (Optional - if using VPC)
# ============================================================================

# Uncomment if Lambda functions need VPC access (e.g., for RDS)
# resource "aws_iam_role_policy_attachment" "lambda_vpc_execution" {
#   role       = aws_iam_role.lambda_execution.name
#   policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
# }

# ============================================================================
# X-Ray Tracing Policy (Optional - for distributed tracing)
# ============================================================================

resource "aws_iam_role_policy" "lambda_xray" {
  name   = "xray-tracing-policy"
  role   = aws_iam_role.lambda_execution.id
  policy = data.aws_iam_policy_document.lambda_xray.json
}

data "aws_iam_policy_document" "lambda_xray" {
  statement {
    effect = "Allow"

    actions = [
      "xray:PutTraceSegments",
      "xray:PutTelemetryRecords",
    ]

    resources = ["*"]
  }
}

# ============================================================================
# API Gateway Execution Role (for CloudWatch Logs)
# ============================================================================

resource "aws_iam_role" "api_gateway_cloudwatch" {
  name               = "potential-parakeet-apigateway-cloudwatch-${var.environment}"
  description        = "API Gateway CloudWatch logging role"
  assume_role_policy = data.aws_iam_policy_document.api_gateway_assume_role.json

  tags = merge(
    local.common_tags,
    {
      Name = "api-gateway-cloudwatch-role-${var.environment}"
    }
  )
}

data "aws_iam_policy_document" "api_gateway_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["apigateway.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role_policy_attachment" "api_gateway_cloudwatch" {
  role       = aws_iam_role.api_gateway_cloudwatch.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
}

# ============================================================================
# EventBridge Execution Role (for invoking Lambda)
# ============================================================================

resource "aws_iam_role" "eventbridge_lambda" {
  name               = "potential-parakeet-eventbridge-lambda-${var.environment}"
  description        = "EventBridge role for invoking Lambda functions"
  assume_role_policy = data.aws_iam_policy_document.eventbridge_assume_role.json

  tags = merge(
    local.common_tags,
    {
      Name = "eventbridge-lambda-role-${var.environment}"
    }
  )
}

data "aws_iam_policy_document" "eventbridge_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role_policy" "eventbridge_invoke_lambda" {
  name   = "invoke-lambda-policy"
  role   = aws_iam_role.eventbridge_lambda.id
  policy = data.aws_iam_policy_document.eventbridge_invoke_lambda.json
}

data "aws_iam_policy_document" "eventbridge_invoke_lambda" {
  statement {
    effect = "Allow"

    actions = [
      "lambda:InvokeFunction",
    ]

    resources = [
      aws_lambda_function.ingest.arn,
    ]
  }
}

# ============================================================================
# SQS Permissions (for DLQ)
# ============================================================================

resource "aws_iam_role_policy" "lambda_sqs_dlq" {
  name   = "sqs-dlq-policy"
  role   = aws_iam_role.lambda_execution.id
  policy = data.aws_iam_policy_document.lambda_sqs_dlq.json
}

data "aws_iam_policy_document" "lambda_sqs_dlq" {
  statement {
    effect = "Allow"

    actions = [
      "sqs:SendMessage",
    ]

    resources = [
      aws_sqs_queue.lambda_dlq.arn,
    ]
  }
}
