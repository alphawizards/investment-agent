# Potential Parakeet - Infrastructure as Code

AWS infrastructure for the Potential Parakeet quantitative trading platform using Terraform.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         CloudFlare Edge                          │
│  ┌──────────────┐      ┌─────────────────┐                     │
│  │ Pages (UI)   │      │ Workers (Auth)  │                     │
│  └──────────────┘      └─────────────────┘                     │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                         AWS Cloud                                │
│                                                                  │
│  ┌────────────────┐         ┌──────────────────────┐           │
│  │ API Gateway    │────────▶│  Lambda Functions    │           │
│  │ (REST API)     │         │  - Trades API        │           │
│  └────────────────┘         │  - Data API          │           │
│                             │  - Strategies API    │           │
│          ┌─────────────────│  - Scanner API       │           │
│          │                 │  - Daily Ingest      │           │
│          │                 └──────────┬───────────┘           │
│          │                            │                        │
│          ▼                            ▼                        │
│  ┌──────────────┐           ┌─────────────────┐              │
│  │ EventBridge  │           │ Secrets Manager │              │
│  │ (Scheduler)  │           │ - DB Creds      │              │
│  └──────────────┘           │ - API Keys      │              │
│                             └─────────────────┘              │
│                                                               │
│  ┌──────────────────────────────────────────────────┐       │
│  │              S3 (Parquet Cache)                  │       │
│  │  - Market data cache                             │       │
│  │  - Lambda deployment packages                    │       │
│  └──────────────────────────────────────────────────┘       │
│                                                               │
│  ┌──────────────────────────────────────────────────┐       │
│  │         CloudWatch (Logs & Monitoring)           │       │
│  └──────────────────────────────────────────────────┘       │
└───────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Neon PostgreSQL (External)                    │
│  - Serverless PostgreSQL                                         │
│  - Auto-scaling compute and storage                              │
└─────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
infrastructure/
├── terraform/              # Terraform configuration files
│   ├── main.tf            # Provider config, locals
│   ├── variables.tf       # Input variables
│   ├── outputs.tf         # Output values
│   ├── s3.tf              # S3 buckets
│   ├── iam.tf             # IAM roles and policies
│   ├── secrets.tf         # Secrets Manager
│   ├── lambda.tf          # Lambda functions
│   ├── api_gateway.tf     # API Gateway (HTTP API v2)
│   ├── eventbridge.tf     # EventBridge scheduled rules
│   └── monitoring.tf      # CloudWatch alarms
└── environments/           # Environment-specific configs
    ├── dev.tfvars
    ├── staging.tfvars
    └── prod.tfvars
```

## Prerequisites

1. **Install Terraform** (>= 1.6.0)
   ```bash
   # macOS
   brew install terraform

   # Windows
   choco install terraform

   # Verify installation
   terraform version
   ```

2. **AWS CLI** configured with credentials
   ```bash
   aws configure
   # Enter your AWS Access Key ID, Secret Access Key, Region
   ```

3. **Neon PostgreSQL Account**
   - Sign up at https://neon.tech
   - Create a new project
   - Get connection string (Format: `postgresql://user:pass@host/db?sslmode=require`)

## Quick Start

### 1. Initialize Terraform

```bash
cd infrastructure/terraform
terraform init
```

### 2. Set Required Variables

**Option A: Environment Variables (Recommended)**
```bash
# Database credentials
export TF_VAR_neon_database_url="postgresql+asyncpg://user:pass@ep-xxx.us-east-1.aws.neon.tech/db?sslmode=require"
export TF_VAR_db_username="your_username"
export TF_VAR_db_password="your_password"
export TF_VAR_db_host="ep-xxx.us-east-1.aws.neon.tech"

# API keys
export TF_VAR_tiingo_api_key="your_tiingo_key"
export TF_VAR_polygon_api_key="your_polygon_key"
```

**Option B: Create terraform.tfvars (NOT recommended - do not commit)**
```hcl
neon_database_url = "postgresql+asyncpg://..."
tiingo_api_key    = "your_key"
# etc.
```

### 3. Plan Deployment

```bash
# Development environment
terraform plan -var-file=../environments/dev.tfvars

# Production environment
terraform plan -var-file=../environments/prod.tfvars
```

### 4. Deploy Infrastructure

```bash
# Deploy to development
terraform apply -var-file=../environments/dev.tfvars

# Deploy to production (requires confirmation)
terraform apply -var-file=../environments/prod.tfvars
```

### 5. Get Outputs

```bash
# View all outputs
terraform output

# Get API Gateway URL
terraform output api_gateway_url

# Get S3 bucket name
terraform output s3_cache_bucket_name
```

## Environment Configuration

### Development (`dev.tfvars`)
- Lower resource limits (cost optimization)
- Disabled scheduled data ingest
- Disabled CloudWatch alarms
- 30-day cache expiration

### Production (`prod.tfvars`)
- Higher resource limits (performance)
- Enabled scheduled data ingest (6 AM UTC)
- Enabled CloudWatch alarms
- No cache expiration
- S3 versioning enabled

## State Management

Terraform state is stored in **S3** with DynamoDB locking (already configured in `main.tf`).

### First-Time Setup

Before running `terraform init`, you must create the state bucket and lock table:

```bash
# Create S3 bucket for state
aws s3 mb s3://potential-parakeet-terraform-state

# Create DynamoDB table for locking
aws dynamodb create-table \
  --table-name terraform-state-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

### Local Development (Optional)

If you prefer local state for development, comment out the `backend "s3"` block in `main.tf`:

```hcl
# backend "s3" {
#   bucket         = "potential-parakeet-terraform-state"
#   key            = "dev/terraform.tfstate"
#   region         = "us-east-1"
#   encrypt        = true
#   dynamodb_table = "terraform-state-lock"
# }
```

Then run `terraform init` without the `-migrate-state` flag.

## Cost Estimation

### Development Environment
- Lambda (Free Tier): $0
- S3 (< 1GB): ~$0.02/month
- API Gateway (< 1M requests): ~$3.50/month
- Secrets Manager: $0.40/month per secret
- **Total: ~$5/month**

### Production Environment
- Lambda (1M requests): ~$0.20/month
- S3 (10GB, versioning): ~$0.50/month
- API Gateway (10M requests): ~$35/month
- Secrets Manager: $0.80/month
- CloudWatch Logs: ~$5/month
- **Total: ~$45/month**

*Note: Neon PostgreSQL is billed separately (starts at $0/month for free tier)*

## Security Best Practices

1. **Never commit secrets to Git**
   - Use environment variables
   - Use AWS Secrets Manager Console
   - Add `*.tfvars` (except examples) to `.gitignore`

2. **Least-privilege IAM roles**
   - Lambda functions only have access to required resources
   - No wildcard (`*`) permissions

3. **Encryption at rest**
   - S3 buckets use AES256 encryption
   - Secrets Manager encrypts using AWS KMS

4. **VPC Security** (Optional)
   - Uncomment VPC configuration in `iam.tf` if Lambda needs private network

## Troubleshooting

### Issue: `terraform init` fails
- **Solution**: Ensure AWS credentials are configured (`aws configure`)

### Issue: Secrets Manager errors
- **Solution**: Set `TF_VAR_neon_database_url` and `TF_VAR_tiingo_api_key`

### Issue: Lambda deployment package too large
- **Solution**: Use Lambda Layers for dependencies (see `lambda.tf`)

### Issue: Terraform state conflicts
- **Solution**: Use S3 backend with state locking (see State Management)

## Cleanup

To destroy all infrastructure:

```bash
# Development
terraform destroy -var-file=../environments/dev.tfvars

# Production (CAREFUL!)
terraform destroy -var-file=../environments/prod.tfvars
```

## Next Steps

1. **Phase 2**: Create Lambda function handlers (`lambda.tf`)
2. **Phase 3**: Configure API Gateway (`api_gateway.tf`)
3. **Phase 4**: Set up EventBridge schedules (`eventbridge.tf`)
4. **Phase 5**: Add CloudWatch monitoring (`monitoring.tf`)
5. **Phase 6**: Deploy Lambda code packages
6. **Phase 7**: Configure Cloudflare Workers and Pages

## Support

For issues or questions:
1. Check [Migration Documentation](../../Migration/MIGRATION_STRATEGY_DOCUMENT.md)
2. Review [Implementation Guide](../../Migration/Ralph Implementation Guide_ Potential Parakeet Migration.md)
3. Open an issue on GitHub

## License

MIT
