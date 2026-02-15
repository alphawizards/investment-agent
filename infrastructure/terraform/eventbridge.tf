/**
 * EventBridge Configuration
 * =========================
 * Scheduled events for automated tasks.
 *
 * Schedules:
 * - Daily data ingest at 6 AM UTC (after US market close)
 */

# ============================================================================
# Daily Data Ingest Schedule
# ============================================================================

resource "aws_cloudwatch_event_rule" "daily_ingest" {
  count = var.enable_daily_ingest ? 1 : 0

  name                = "potential-parakeet-daily-ingest-${var.environment}"
  description         = "Trigger daily market data ingestion"
  schedule_expression = var.daily_ingest_schedule

  tags = merge(local.common_tags, {
    Name     = "daily-ingest-rule-${var.environment}"
    Function = "scheduler"
  })
}

resource "aws_cloudwatch_event_target" "daily_ingest" {
  count = var.enable_daily_ingest ? 1 : 0

  rule      = aws_cloudwatch_event_rule.daily_ingest[0].name
  target_id = "IngestLambdaTarget"
  arn       = aws_lambda_function.ingest.arn
  role_arn  = aws_iam_role.eventbridge_lambda.arn

  # Optional: Pass custom input to the Lambda
  input = jsonencode({
    source    = "scheduled"
    action    = "full_ingest"
    timestamp = "$time"
  })
}

# Permission for EventBridge to invoke Lambda
resource "aws_lambda_permission" "eventbridge_ingest" {
  count = var.enable_daily_ingest ? 1 : 0

  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingest.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_ingest[0].arn
}
