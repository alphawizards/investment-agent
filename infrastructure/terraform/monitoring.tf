/**
 * CloudWatch Monitoring Configuration
 * ====================================
 * Alarms and dashboards for production monitoring.
 *
 * Alarms:
 * - Lambda errors
 * - Lambda duration
 * - API Gateway 5xx errors
 * - API Gateway latency
 */

# ============================================================================
# SNS Topic for Alarm Notifications
# ============================================================================

resource "aws_sns_topic" "alarms" {
  # checkov:skip=CKV_AWS_26:KMS CMK for SNS is cost-prohibitive
  count = var.enable_cloudwatch_alarms ? 1 : 0

  name = "potential-parakeet-alarms-${var.environment}"

  tags = merge(local.common_tags, {
    Name = "alarm-notifications-${var.environment}"
  })
}

resource "aws_sns_topic_subscription" "alarm_email" {
  count = var.enable_cloudwatch_alarms && var.alert_email != "" ? 1 : 0

  topic_arn = aws_sns_topic.alarms[0].arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# ============================================================================
# Lambda Error Alarms
# ============================================================================

resource "aws_cloudwatch_metric_alarm" "lambda_ingest_errors" {
  count = var.enable_cloudwatch_alarms ? 1 : 0

  alarm_name          = "potential-parakeet-ingest-errors-${var.environment}"
  alarm_description   = "Lambda ingest function errors exceeded threshold"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300  # 5 minutes
  statistic           = "Sum"
  threshold           = var.lambda_error_alarm_threshold
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.ingest.function_name
  }

  alarm_actions = [aws_sns_topic.alarms[0].arn]
  ok_actions    = [aws_sns_topic.alarms[0].arn]

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "lambda_api_errors" {
  count = var.enable_cloudwatch_alarms ? 1 : 0

  alarm_name          = "potential-parakeet-api-errors-${var.environment}"
  alarm_description   = "Lambda API function errors exceeded threshold"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = var.lambda_error_alarm_threshold
  treat_missing_data  = "notBreaching"

  # Combined metric for all API functions
  dimensions = {
    FunctionName = aws_lambda_function.data_api.function_name
  }

  alarm_actions = [aws_sns_topic.alarms[0].arn]
  ok_actions    = [aws_sns_topic.alarms[0].arn]

  tags = local.common_tags
}

# ============================================================================
# Lambda Duration Alarms
# ============================================================================

resource "aws_cloudwatch_metric_alarm" "lambda_ingest_duration" {
  count = var.enable_cloudwatch_alarms ? 1 : 0

  alarm_name          = "potential-parakeet-ingest-duration-${var.environment}"
  alarm_description   = "Lambda ingest function duration exceeded threshold"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Average"
  threshold           = var.lambda_duration_alarm_threshold_ms
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.ingest.function_name
  }

  alarm_actions = [aws_sns_topic.alarms[0].arn]

  tags = local.common_tags
}

# ============================================================================
# API Gateway Alarms
# ============================================================================

resource "aws_cloudwatch_metric_alarm" "api_gateway_5xx" {
  count = var.enable_cloudwatch_alarms ? 1 : 0

  alarm_name          = "potential-parakeet-api-5xx-${var.environment}"
  alarm_description   = "API Gateway 5xx errors exceeded threshold"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "5xx"
  namespace           = "AWS/ApiGateway"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiId = aws_apigatewayv2_api.main.id
  }

  alarm_actions = [aws_sns_topic.alarms[0].arn]
  ok_actions    = [aws_sns_topic.alarms[0].arn]

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "api_gateway_latency" {
  count = var.enable_cloudwatch_alarms ? 1 : 0

  alarm_name          = "potential-parakeet-api-latency-${var.environment}"
  alarm_description   = "API Gateway latency exceeded threshold"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "Latency"
  namespace           = "AWS/ApiGateway"
  period              = 300
  statistic           = "Average"
  threshold           = 5000  # 5 seconds
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiId = aws_apigatewayv2_api.main.id
  }

  alarm_actions = [aws_sns_topic.alarms[0].arn]

  tags = local.common_tags
}
