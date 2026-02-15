# AWS & Neon Setup Guide
## Potential Parakeet - Complete Setup Instructions

**Estimated Time**: 30-45 minutes
**Cost**: $0 (using free tiers)
**Prerequisites**: Credit card for AWS account verification (not charged on free tier)

---

## Table of Contents

1. [AWS Account Setup](#1-aws-account-setup)
2. [AWS CLI Installation & Configuration](#2-aws-cli-installation--configuration)
3. [Neon PostgreSQL Setup](#3-neon-postgresql-setup)
4. [AWS Secrets Manager Configuration](#4-aws-secrets-manager-configuration)
5. [Local Development Setup](#5-local-development-setup)
6. [Terraform Deployment](#6-terraform-deployment)
7. [Verification & Testing](#7-verification--testing)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. AWS Account Setup

### Step 1.1: Create AWS Account

1. Go to [https://aws.amazon.com](https://aws.amazon.com)
2. Click **"Create an AWS Account"**
3. Fill in your details:
   - Email address
   - Password
   - AWS account name (e.g., "Potential Parakeet Trading")
4. Choose **"Personal"** account type
5. Enter billing information (credit card required, but won't be charged on free tier)
6. Verify your phone number
7. Select **"Basic Support - Free"** plan
8. Complete sign-up

**⏱ Time**: ~10 minutes

### Step 1.2: Enable MFA (Highly Recommended)

1. Sign in to [AWS Console](https://console.aws.amazon.com)
2. Click your account name (top right) → **"Security credentials"**
3. Under **"Multi-factor authentication (MFA)"**, click **"Assign MFA device"**
4. Choose **"Virtual MFA device"** (use Google Authenticator or Authy)
5. Scan QR code with your authenticator app
6. Enter two consecutive MFA codes
7. Click **"Assign MFA"**

**⏱ Time**: ~5 minutes

### Step 1.3: Create IAM User (Best Practice)

**Why?** Don't use root account for daily operations.

1. In AWS Console, search for **"IAM"**
2. Click **"Users"** → **"Create user"**
3. User name: `terraform-deployer`
4. Check **"Provide user access to the AWS Management Console"** (optional)
5. Click **"Next"**
6. Attach policies:
   - ✅ `AdministratorAccess` (for setup; restrict later)
7. Click **"Next"** → **"Create user"**
8. **IMPORTANT**: Download CSV with credentials or note:
   - Access Key ID
   - Secret Access Key
   - Console password (if enabled)

**⏱ Time**: ~5 minutes

---

## 2. AWS CLI Installation & Configuration

### Step 2.1: Install AWS CLI

**Windows:**
```powershell
# Download installer
msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi

# Verify installation
aws --version
```

**macOS:**
```bash
# Using Homebrew
brew install awscli

# Or download installer
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /

# Verify installation
aws --version
```

**Linux:**
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Verify installation
aws --version
```

**Expected Output:**
```
aws-cli/2.15.0 Python/3.11.6 Windows/10 exe/AMD64 prompt/off
```

**⏱ Time**: ~5 minutes

### Step 2.2: Configure AWS CLI

```bash
aws configure
```

**Enter the following when prompted:**
```
AWS Access Key ID [None]: AKIAIOSFODNN7EXAMPLE
AWS Secret Access Key [None]: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
Default region name [None]: us-east-1
Default output format [None]: json
```

**Verify configuration:**
```bash
# Test AWS credentials
aws sts get-caller-identity
```

**Expected Output:**
```json
{
    "UserId": "AIDAIOSFODNN7EXAMPLE",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/terraform-deployer"
}
```

**⏱ Time**: ~2 minutes

---

## 3. Neon PostgreSQL Setup

### Step 3.1: Create Neon Account

1. Go to [https://neon.tech](https://neon.tech)
2. Click **"Sign Up"**
3. Choose sign-up method:
   - GitHub (recommended)
   - Google
   - Email
4. Complete authentication

**⏱ Time**: ~2 minutes

### Step 3.2: Create Neon Project

1. After login, you'll see **"Create your first project"**
2. Fill in project details:
   - **Project name**: `potential-parakeet`
   - **Region**: `US East (Ohio)` (us-east-2) or `US East (N. Virginia)` (us-east-1)
   - **PostgreSQL version**: `16` (latest)
   - **Compute size**: Use default (0.25 vCPU - free tier)
3. Click **"Create project"**

**⏱ Time**: ~2 minutes

### Step 3.3: Get Database Connection String

1. After project creation, you'll see a **connection string** like:
   ```
   postgresql://alex:AbC123dEf@ep-cool-darkness-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```

2. **IMPORTANT**: Save these details:
   - **Host**: `ep-cool-darkness-123456.us-east-2.aws.neon.tech`
   - **Database**: `neondb`
   - **User**: `alex`
   - **Password**: `AbC123dEf`
   - **Full connection string**

3. Click **"Copy"** to save connection string

**⏱ Time**: ~1 minute

### Step 3.4: Create Database (Optional)

By default, Neon creates `neondb`. To create a custom database:

1. In Neon Console, go to **"Databases"** tab
2. Click **"New Database"**
3. Name: `potential_parakeet`
4. Owner: Select default user
5. Click **"Create"**

**⏱ Time**: ~1 minute

### Step 3.5: Test Connection

**Using psql (if installed):**
```bash
psql "postgresql://alex:AbC123dEf@ep-cool-darkness-123456.us-east-2.aws.neon.tech/neondb?sslmode=require"
```

**Using Python (in your project):**
```bash
# Install psycopg2
pip install psycopg2-binary

# Test connection
python -c "
import psycopg2
conn = psycopg2.connect('postgresql://alex:AbC123dEf@ep-cool-darkness-123456.us-east-2.aws.neon.tech/neondb?sslmode=require')
print('✅ Connection successful!')
conn.close()
"
```

**⏱ Time**: ~2 minutes

---

## 4. AWS Secrets Manager Configuration

### Step 4.1: Store Database Credentials in Secrets Manager

**Option A: Using AWS Console (Recommended for beginners)**

1. Go to [AWS Secrets Manager Console](https://console.aws.amazon.com/secretsmanager)
2. Click **"Store a new secret"**
3. Select **"Other type of secret"**
4. Click **"Plaintext"** tab
5. Paste the following JSON (replace with your actual values):

```json
{
  "NEON_DATABASE_URL": "postgresql+asyncpg://alex:AbC123dEf@ep-cool-darkness-123456.us-east-2.aws.neon.tech/neondb?sslmode=require",
  "DB_USERNAME": "alex",
  "DB_PASSWORD": "AbC123dEf",
  "DB_HOST": "ep-cool-darkness-123456.us-east-2.aws.neon.tech",
  "DB_NAME": "neondb",
  "DB_PORT": "5432",
  "USE_NEON": "true"
}
```

6. Click **"Next"**
7. Secret name: `potential-parakeet/dev`
8. Description: `Database credentials for Potential Parakeet (dev environment)`
9. Click **"Next"** → **"Next"** → **"Store"**

**⏱ Time**: ~3 minutes

**Option B: Using AWS CLI**

```bash
# Create secret from JSON file
cat > /tmp/db-secret.json << 'EOF'
{
  "NEON_DATABASE_URL": "postgresql+asyncpg://alex:AbC123dEf@ep-cool-darkness-123456.us-east-2.aws.neon.tech/neondb?sslmode=require",
  "DB_USERNAME": "alex",
  "DB_PASSWORD": "AbC123dEf",
  "DB_HOST": "ep-cool-darkness-123456.us-east-2.aws.neon.tech",
  "DB_NAME": "neondb",
  "DB_PORT": "5432",
  "USE_NEON": "true"
}
EOF

# Store secret
aws secretsmanager create-secret \
    --name potential-parakeet/dev \
    --description "Database credentials for Potential Parakeet (dev)" \
    --secret-string file:///tmp/db-secret.json \
    --region us-east-1

# Clean up
rm /tmp/db-secret.json
```

**Verify:**
```bash
aws secretsmanager get-secret-value \
    --secret-id potential-parakeet/dev \
    --region us-east-1 \
    --query SecretString \
    --output text
```

**⏱ Time**: ~2 minutes

### Step 4.2: Store API Keys in Secrets Manager

1. Go back to [Secrets Manager Console](https://console.aws.amazon.com/secretsmanager)
2. Click **"Store a new secret"**
3. Select **"Other type of secret"** → **"Plaintext"**
4. Paste:

```json
{
  "TIINGO_API_KEY": "your-tiingo-api-key-here",
  "TIINGO_IS_PREMIUM": "true",
  "POLYGON_API_KEY": "",
  "ALPHA_VANTAGE_API_KEY": ""
}
```

5. Secret name: `potential-parakeet/dev/api-keys`
6. Click **"Next"** → **"Next"** → **"Store"**

**⏱ Time**: ~2 minutes

### Step 4.3: Get Your Tiingo API Key

1. Go to [https://www.tiingo.com](https://www.tiingo.com)
2. Click **"Sign Up"** (free account)
3. After login, go to [API](https://www.tiingo.com/account/api/token)
4. Copy your API token
5. Update the secret in AWS Secrets Manager with your actual token

**⏱ Time**: ~3 minutes

---

## 5. Local Development Setup

### Step 5.1: Clone and Setup Project

```bash
# Navigate to project directory
cd "c:\Users\ckr_4\01 Web Projects\potential-parakeet\potential-parakeet-2"

# Create .env file from example
cp .env.example .env
```

### Step 5.2: Configure .env File

Open `.env` in your editor and update:

```bash
# ============== DATABASE ==============
# For local development with SQLite (default)
DATABASE_URL=sqlite:///./data/trades.db
USE_NEON=false

# For testing with Neon PostgreSQL (optional)
# USE_NEON=true
# NEON_DATABASE_URL=postgresql+asyncpg://alex:AbC123dEf@ep-cool-darkness-123456.us-east-2.aws.neon.tech/neondb?sslmode=require

# ============== AWS CONFIGURATION ==============
AWS_REGION=us-east-1
AWS_SECRETS_MANAGER_NAME=potential-parakeet/dev

# Leave these empty to use AWS CLI credentials
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=

# ============== S3 CACHE ==============
USE_S3_CACHE=false
S3_BUCKET_NAME=potential-parakeet-cache

# ============== API KEYS ==============
TIINGO_API_KEY=your-tiingo-api-key-here
TIINGO_IS_PREMIUM=true
```

**⏱ Time**: ~3 minutes

### Step 5.3: Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**⏱ Time**: ~5 minutes

### Step 5.4: Initialize Database

```bash
# Run Alembic migrations
alembic upgrade head
```

**Expected Output:**
```
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 20250112_0001, Initial migration
```

**⏱ Time**: ~1 minute

### Step 5.5: Test Local Setup

```bash
# Test database connection
python -c "
from backend.database.connection import init_db
init_db()
print('✅ Database initialized successfully!')
"

# Test async database connection
python -c "
import asyncio
from backend.database.connection import init_async_db

async def test():
    await init_async_db()
    print('✅ Async database initialized successfully!')

asyncio.run(test())
"
```

**⏱ Time**: ~2 minutes

---

## 6. Terraform Deployment

### Step 6.1: Install Terraform

**Windows:**
```powershell
# Using Chocolatey
choco install terraform

# Or download from https://www.terraform.io/downloads
```

**macOS:**
```bash
brew install terraform
```

**Linux:**
```bash
wget https://releases.hashicorp.com/terraform/1.7.0/terraform_1.7.0_linux_amd64.zip
unzip terraform_1.7.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/
```

**Verify:**
```bash
terraform --version
```

**⏱ Time**: ~3 minutes

### Step 6.2: Set Terraform Variables

**Option A: Environment Variables (Recommended)**

```bash
# Windows PowerShell:
$env:TF_VAR_neon_database_url = "postgresql+asyncpg://alex:AbC123dEf@ep-cool-darkness-123456.us-east-2.aws.neon.tech/neondb?sslmode=require"
$env:TF_VAR_db_username = "alex"
$env:TF_VAR_db_password = "AbC123dEf"
$env:TF_VAR_db_host = "ep-cool-darkness-123456.us-east-2.aws.neon.tech"
$env:TF_VAR_tiingo_api_key = "your-tiingo-api-key"

# macOS/Linux:
export TF_VAR_neon_database_url="postgresql+asyncpg://alex:AbC123dEf@ep-cool-darkness-123456.us-east-2.aws.neon.tech/neondb?sslmode=require"
export TF_VAR_db_username="alex"
export TF_VAR_db_password="AbC123dEf"
export TF_VAR_db_host="ep-cool-darkness-123456.us-east-2.aws.neon.tech"
export TF_VAR_tiingo_api_key="your-tiingo-api-key"
```

**Option B: Create terraform.tfvars (NOT recommended - don't commit)**

```bash
cd infrastructure/terraform

cat > terraform.tfvars << 'EOF'
neon_database_url = "postgresql+asyncpg://alex:AbC123dEf@ep-cool-darkness-123456.us-east-2.aws.neon.tech/neondb?sslmode=require"
db_username = "alex"
db_password = "AbC123dEf"
db_host = "ep-cool-darkness-123456.us-east-2.aws.neon.tech"
tiingo_api_key = "your-tiingo-api-key"
EOF
```

**⚠️ IMPORTANT**: Add to `.gitignore`:
```bash
echo "terraform.tfvars" >> .gitignore
echo "*.tfvars" >> .gitignore
echo "!infrastructure/environments/*.tfvars" >> .gitignore
```

**⏱ Time**: ~2 minutes

### Step 6.3: Initialize Terraform

```bash
cd infrastructure/terraform

# Initialize Terraform
terraform init
```

**Expected Output:**
```
Initializing the backend...
Initializing provider plugins...
- Finding hashicorp/aws versions matching "~> 5.0"...
- Installing hashicorp/aws v5.31.0...

Terraform has been successfully initialized!
```

**⏱ Time**: ~2 minutes

### Step 6.4: Plan Deployment

```bash
# Review what will be created
terraform plan -var-file=../environments/dev.tfvars
```

**Review the output carefully. You should see:**
- ✅ S3 buckets to be created
- ✅ IAM roles to be created
- ✅ Secrets Manager secrets to be created
- ❌ Lambda functions (not yet implemented - Phase 3)

**⏱ Time**: ~2 minutes

### Step 6.5: Deploy Infrastructure

```bash
# Apply the configuration
terraform apply -var-file=../environments/dev.tfvars
```

**When prompted:**
```
Do you want to perform these actions?
  Terraform will perform the actions described above.
  Only 'yes' will be accepted to approve.

  Enter a value: yes
```

**Expected Output:**
```
Apply complete! Resources: 15 added, 0 changed, 0 destroyed.

Outputs:

s3_cache_bucket_name = "potential-parakeet-cache-dev"
secrets_manager_name = "potential-parakeet/dev"
aws_region = "us-east-1"
```

**⏱ Time**: ~3 minutes

---

## 7. Verification & Testing

### Step 7.1: Verify S3 Bucket

```bash
# List S3 buckets
aws s3 ls | grep potential-parakeet

# Expected output:
# 2025-01-12 10:30:45 potential-parakeet-cache-dev
# 2025-01-12 10:30:45 potential-parakeet-lambda-artifacts-dev
```

### Step 7.2: Verify Secrets Manager

```bash
# List secrets
aws secretsmanager list-secrets --region us-east-1 | grep potential-parakeet

# Get secret value
aws secretsmanager get-secret-value \
    --secret-id potential-parakeet/dev \
    --region us-east-1 \
    --query SecretString \
    --output text | python -m json.tool
```

### Step 7.3: Test S3 Upload/Download

```bash
# Create test file
echo "Test cache file" > test.parquet

# Upload to S3
aws s3 cp test.parquet s3://potential-parakeet-cache-dev/cache/test.parquet

# Download from S3
aws s3 cp s3://potential-parakeet-cache-dev/cache/test.parquet downloaded.parquet

# Verify
cat downloaded.parquet
# Expected: Test cache file

# Clean up
rm test.parquet downloaded.parquet
aws s3 rm s3://potential-parakeet-cache-dev/cache/test.parquet
```

### Step 7.4: Test Secrets Retrieval in Python

```python
# test_secrets.py
import asyncio
from backend.utils.secrets import get_database_credentials

async def test():
    creds = await get_database_credentials()
    print("✅ Database credentials retrieved:")
    print(f"   Host: {creds.get('DB_HOST')}")
    print(f"   Database: {creds.get('DB_NAME')}")
    print(f"   User: {creds.get('DB_USERNAME')}")
    print("✅ Connection string available:", bool(creds.get('NEON_DATABASE_URL')))

asyncio.run(test())
```

Run it:
```bash
python test_secrets.py
```

### Step 7.5: Test Database Connection with Neon

```python
# test_neon_connection.py
import asyncio
from sqlalchemy import select, text
from backend.database.connection import async_engine, get_async_db
from backend.database.models import Trade
from backend.config import settings

async def test():
    # Temporarily enable Neon for testing
    settings.USE_NEON = True
    settings.NEON_DATABASE_URL = "your-connection-string-here"

    async with async_engine.begin() as conn:
        # Test raw query
        result = await conn.execute(text("SELECT version()"))
        version = result.scalar()
        print(f"✅ Connected to PostgreSQL: {version}")

        # Test table creation
        from backend.database.connection import Base
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Tables created successfully")

if __name__ == "__main__":
    asyncio.run(test())
```

**⏱ Time**: ~5 minutes

---

## 8. Troubleshooting

### Issue 1: AWS CLI Not Found

**Error:**
```
'aws' is not recognized as an internal or external command
```

**Solution:**
```bash
# Add AWS CLI to PATH (Windows)
# Add to System Environment Variables:
C:\Program Files\Amazon\AWSCLIV2\

# Restart terminal
```

### Issue 2: AWS Credentials Invalid

**Error:**
```
An error occurred (InvalidClientTokenId) when calling the GetCallerIdentity operation
```

**Solution:**
```bash
# Reconfigure AWS CLI
aws configure

# Or check credentials file
# Windows: C:\Users\USERNAME\.aws\credentials
# macOS/Linux: ~/.aws/credentials
```

### Issue 3: Neon Connection Failed

**Error:**
```
psycopg2.OperationalError: could not connect to server
```

**Solution:**
1. Check connection string has `?sslmode=require`
2. Verify Neon project is active (not suspended)
3. Check IP whitelist in Neon console (if configured)
4. Test with `psql` directly

### Issue 4: Secrets Manager Access Denied

**Error:**
```
An error occurred (AccessDeniedException) when calling the GetSecretValue operation
```

**Solution:**
```bash
# Verify IAM user has SecretsManagerReadWrite permission
aws iam list-attached-user-policies --user-name terraform-deployer

# Or add permission
aws iam attach-user-policy \
    --user-name terraform-deployer \
    --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite
```

### Issue 5: Terraform State Lock

**Error:**
```
Error acquiring the state lock
```

**Solution:**
```bash
# If no other Terraform process is running, force unlock
terraform force-unlock <LOCK_ID>
```

### Issue 6: S3 Bucket Already Exists

**Error:**
```
Error: error creating S3 bucket: BucketAlreadyExists
```

**Solution:**
```bash
# Change bucket name in dev.tfvars
s3_bucket_name = "potential-parakeet-cache-yourname"
```

### Issue 7: Python Import Errors

**Error:**
```
ModuleNotFoundError: No module named 'asyncpg'
```

**Solution:**
```bash
# Ensure virtual environment is activated
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue 8: Alembic Migration Failed

**Error:**
```
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) table trades already exists
```

**Solution:**
```bash
# Drop database and recreate (DEV ONLY!)
rm data/trades.db

# Run migrations again
alembic upgrade head
```

---

## Quick Reference Cheatsheet

### AWS CLI
```bash
# Test credentials
aws sts get-caller-identity

# List S3 buckets
aws s3 ls

# Get secret
aws secretsmanager get-secret-value --secret-id potential-parakeet/dev
```

### Terraform
```bash
# Initialize
terraform init

# Plan
terraform plan -var-file=../environments/dev.tfvars

# Apply
terraform apply -var-file=../environments/dev.tfvars

# Destroy
terraform destroy -var-file=../environments/dev.tfvars

# View outputs
terraform output
```

### Alembic
```bash
# Run migrations
alembic upgrade head

# Create migration
alembic revision --autogenerate -m "Description"

# Rollback
alembic downgrade -1

# Show history
alembic history
```

### Python Testing
```bash
# Activate virtual environment
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Test database
python -c "from backend.database.connection import init_db; init_db(); print('✅ OK')"

# Test async database
python -c "import asyncio; from backend.database.connection import init_async_db; asyncio.run(init_async_db()); print('✅ OK')"
```

---

## Next Steps

After completing this setup:

1. ✅ You have AWS account configured
2. ✅ You have Neon PostgreSQL database
3. ✅ You have secrets stored in AWS Secrets Manager
4. ✅ You have S3 buckets for cache storage
5. ✅ You have local development environment working

**Ready for Phase 2:**
- Implement S3 cache storage adapter
- Refactor data loaders to use S3
- Create Lambda function handlers

**See:** [MIGRATION_PROGRESS.md](MIGRATION_PROGRESS.md) for next steps

---

## Cost Monitoring

### Free Tier Limits (First 12 months)

**AWS:**
- Lambda: 1M requests/month + 400,000 GB-seconds compute
- S3: 5GB storage + 20,000 GET requests
- Secrets Manager: 30-day trial (then $0.40/secret/month)
- API Gateway: 1M requests/month (first 12 months)

**Neon:**
- Free tier: 0.25 vCPU, 256 MB RAM, 512 MB storage
- Auto-suspend after 5 minutes of inactivity

**Total Expected Cost (after free tier):**
- Month 1-12: ~$0/month (within free tier)
- After 12 months: ~$5/month

### Monitor Your Costs

```bash
# AWS Cost Explorer (Web Console)
https://console.aws.amazon.com/cost-management/home#/dashboard

# CLI: Get month-to-date costs
aws ce get-cost-and-usage \
    --time-period Start=2025-01-01,End=2025-01-31 \
    --granularity MONTHLY \
    --metrics "UnblendedCost"
```

---

## Security Checklist

- [x] MFA enabled on AWS root account
- [x] IAM user created (not using root)
- [x] Secrets stored in Secrets Manager (not in code)
- [x] `.env` file added to `.gitignore`
- [x] `terraform.tfvars` added to `.gitignore`
- [ ] AWS CloudTrail enabled (optional, for auditing)
- [ ] AWS Cost Alerts configured (optional)

---

## Support & Resources

**Documentation:**
- AWS: https://docs.aws.amazon.com
- Neon: https://neon.tech/docs
- Terraform: https://www.terraform.io/docs

**Community:**
- AWS Community: https://repost.aws
- Neon Discord: https://discord.gg/neon
- Terraform Forum: https://discuss.hashicorp.com/c/terraform-core

**Project Documentation:**
- [README.md](README.md)
- [MIGRATION_PROGRESS.md](MIGRATION_PROGRESS.md)
- [infrastructure/README.md](infrastructure/README.md)

---

**Setup Complete!** 🎉

You now have a fully configured AWS + Neon environment for the Potential Parakeet trading platform.
