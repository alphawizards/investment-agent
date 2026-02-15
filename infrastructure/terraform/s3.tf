/**
 * S3 Bucket Configuration
 * =======================
 * S3 bucket for Parquet cache storage (replaces local file system).
 *
 * Features:
 * - Server-side encryption (AES256)
 * - Versioning (optional, disabled by default for cost)
 * - Lifecycle policies for cost optimization
 * - Public access blocked
 * - CORS configuration for CloudFlare Pages
 */

# ============================================================================
# S3 Bucket for Parquet Cache
# ============================================================================

resource "aws_s3_bucket" "cache" {
  # checkov:skip=CKV_AWS_144:Cross-region replication is cost-prohibitive
  # checkov:skip=CKV_AWS_145:KMS CMK encryption is cost-prohibitive, using SSE-S3
  # checkov:skip=CKV_AWS_18:Access logging enabled below via aws_s3_bucket_logging
  # checkov:skip=CKV2_AWS_62:S3 notification configuration is not required
  bucket = "${var.s3_bucket_name}-${var.environment}"

  tags = merge(
    local.common_tags,
    {
      Name        = "${var.s3_bucket_name}-${var.environment}"
      Purpose     = "parquet-cache-storage"
      DataType    = "market-data-cache"
      Compliance  = "none"
    }
  )
}

# Block all public access (security best practice)
resource "aws_s3_bucket_public_access_block" "cache" {
  bucket = aws_s3_bucket.cache.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable versioning (Improved security, lifecycle managed below for cost)
resource "aws_s3_bucket_versioning" "cache" {
  bucket = aws_s3_bucket.cache.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Server-side encryption (SSE-S3 is free)
resource "aws_s3_bucket_server_side_encryption_configuration" "cache" {
  bucket = aws_s3_bucket.cache.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true # Reduce encryption costs
  }
}

# Access logging for cache bucket
resource "aws_s3_bucket_logging" "cache" {
  bucket = aws_s3_bucket.cache.id

  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "cache/"
}

# Lifecycle policy for cost optimization
resource "aws_s3_bucket_lifecycle_configuration" "cache" {
  bucket = aws_s3_bucket.cache.id

  # Transition old data to cheaper storage classes
  rule {
    id     = "transition-to-ia"
    status = "Enabled"

    filter {
      prefix = ""  # Apply to all objects
    }

    # Move cache files older than 30 days to Infrequent Access
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    # Move cache files older than 90 days to Glacier Instant Retrieval
    transition {
      days          = 90
      storage_class = "GLACIER_IR"
    }

    # Optional: Delete old cache files (must be > 90 days due to Glacier transition)
    dynamic "expiration" {
      for_each = var.s3_lifecycle_expiration_days > 90 ? [1] : []
      content {
        days = var.s3_lifecycle_expiration_days
      }
    }
  }

  # Clean up incomplete multipart uploads (cost optimization)
  rule {
    id     = "abort-incomplete-multipart-uploads"
    status = "Enabled"

    filter {
      prefix = ""
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  # Delete old versions if versioning is enabled
  dynamic "rule" {
    for_each = var.enable_s3_versioning ? [1] : []
    content {
      id     = "expire-old-versions"
      status = "Enabled"

      filter {
        prefix = ""
      }

      noncurrent_version_transition {
        noncurrent_days = 30
        storage_class   = "STANDARD_IA"
      }

      noncurrent_version_expiration {
        noncurrent_days = 1 # Keep for only 1 day to avoid storage costs
      }

      abort_incomplete_multipart_upload {
        days_after_initiation = 7
      }
    }
  }
}

# CORS configuration (for CloudFlare Pages frontend)
resource "aws_s3_bucket_cors_configuration" "cache" {
  bucket = aws_s3_bucket.cache.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = [
      "http://localhost:3000",
      "http://localhost:5173",
      "https://*.pages.dev",                              # CloudFlare Pages preview
      "https://potential-parakeet.pages.dev",             # Production domain
    ]
    expose_headers  = ["ETag"]
    max_age_seconds = 3600
  }
}

# ============================================================================
# S3 Bucket for Lambda Deployment Packages (Optional)
# ============================================================================

resource "aws_s3_bucket" "lambda_artifacts" {
  # checkov:skip=CKV_AWS_144:Cross-region replication is cost-prohibitive
  # checkov:skip=CKV_AWS_145:KMS CMK encryption is cost-prohibitive, using SSE-S3
  # checkov:skip=CKV_AWS_18:Access logging enabled below via aws_s3_bucket_logging
  # checkov:skip=CKV2_AWS_62:S3 notification configuration is not required
  bucket = "potential-parakeet-lambda-artifacts-${var.environment}"

  tags = merge(
    local.common_tags,
    {
      Name    = "lambda-artifacts-${var.environment}"
      Purpose = "lambda-deployment-packages"
    }
  )
}

resource "aws_s3_bucket_public_access_block" "lambda_artifacts" {
  bucket = aws_s3_bucket.lambda_artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable versioning for artifacts
resource "aws_s3_bucket_versioning" "lambda_artifacts" {
  bucket = aws_s3_bucket.lambda_artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "lambda_artifacts" {
  bucket = aws_s3_bucket.lambda_artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Access logging for artifacts bucket
resource "aws_s3_bucket_logging" "lambda_artifacts" {
  bucket = aws_s3_bucket.lambda_artifacts.id

  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "lambda_artifacts/"
}

# Lifecycle: Delete old Lambda packages after 30 days
resource "aws_s3_bucket_lifecycle_configuration" "lambda_artifacts" {
  bucket = aws_s3_bucket.lambda_artifacts.id

  rule {
    id     = "cleanup-old-artifacts"
    status = "Enabled"

    filter {
      prefix = ""  # Apply to all objects
    }

    # Keep only last 5 versions
    noncurrent_version_expiration {
      newer_noncurrent_versions = 5
      noncurrent_days          = 1
    }

    # Delete artifacts older than 30 days
    expiration {
      days = 30
    }

    # Clean up incomplete multipart uploads (cost optimization)
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# ============================================================================
# S3 Bucket for Access Logs (Secure Storage)
# ============================================================================

resource "aws_s3_bucket" "logs" {
  # checkov:skip=CKV_AWS_144:Logging bucket does not need replication
  # checkov:skip=CKV_AWS_145:KMS CMK is cost-prohibitive
  # checkov:skip=CKV_AWS_18:Logging bucket does not log to itself
  # checkov:skip=CKV2_AWS_62:S3 notification configuration is not required
  bucket = "potential-parakeet-logs-${var.environment}"

  tags = merge(
    local.common_tags,
    {
      Name    = "logs-${var.environment}"
      Purpose = "access-logs"
    }
  )
}

resource "aws_s3_bucket_public_access_block" "logs" {
  bucket = aws_s3_bucket.logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "logs" {
  bucket = aws_s3_bucket.logs.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    id     = "expire-logs"
    status = "Enabled"

    filter {
      prefix = ""
    }

    expiration {
      days = 90
    }

    noncurrent_version_expiration {
      noncurrent_days = 1
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}
