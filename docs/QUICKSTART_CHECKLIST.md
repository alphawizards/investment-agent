# Quick Start Checklist
## Potential Parakeet - Setup in 30 Minutes

**Follow this checklist to get up and running quickly.**

---

## Pre-Setup (5 minutes)

- [ ] Credit card ready (for AWS verification - won't be charged)
- [ ] Email address for AWS account
- [ ] Email address for Neon account
- [ ] Phone number for AWS verification

---

## Part 1: AWS Account (15 minutes)

### Create Account
- [ ] Go to [aws.amazon.com](https://aws.amazon.com) → Create Account
- [ ] Fill in email, password, account name
- [ ] Choose "Personal" account type
- [ ] Enter billing info (credit card)
- [ ] Verify phone number
- [ ] Select "Basic Support - Free"

### Enable MFA (Security)
- [ ] Sign in → Click your name (top right) → Security credentials
- [ ] Assign MFA device → Virtual MFA
- [ ] Scan QR with Google Authenticator or Authy
- [ ] Enter two consecutive codes

### Create IAM User
- [ ] AWS Console → Search "IAM" → Users → Create user
- [ ] Username: `terraform-deployer`
- [ ] Attach policy: `AdministratorAccess`
- [ ] **Download credentials CSV** ⚠️ IMPORTANT

### Install & Configure AWS CLI
- [ ] Install AWS CLI:
  - Windows: Download from [aws.amazon.com/cli](https://aws.amazon.com/cli/)
  - Mac: `brew install awscli`
  - Linux: `curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && unzip awscliv2.zip && sudo ./aws/install`

- [ ] Run: `aws configure`
  - Access Key ID: (from CSV)
  - Secret Access Key: (from CSV)
  - Region: `us-east-1`
  - Output: `json`

- [ ] Test: `aws sts get-caller-identity` (should show your account)

---

## Part 2: Neon PostgreSQL (5 minutes)

### Create Account & Project
- [ ] Go to [neon.tech](https://neon.tech) → Sign Up (use GitHub)
- [ ] Create project:
  - Name: `potential-parakeet`
  - Region: `US East (Ohio)` or `US East (N. Virginia)`
  - PostgreSQL: `16`
- [ ] **Copy connection string** ⚠️ IMPORTANT
  - Format: `postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require`

### Test Connection
- [ ] Run: `pip install psycopg2-binary`
- [ ] Test: `python -c "import psycopg2; conn = psycopg2.connect('YOUR_CONNECTION_STRING'); print('✅ OK'); conn.close()"`

---

## Part 3: AWS Secrets Manager (5 minutes)

### Store Database Credentials
- [ ] Go to [AWS Secrets Manager Console](https://console.aws.amazon.com/secretsmanager)
- [ ] Store new secret → Other type → Plaintext
- [ ] Paste (replace with YOUR values):
```json
{
  "NEON_DATABASE_URL": "postgresql+asyncpg://user:pass@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require",
  "DB_USERNAME": "user",
  "DB_PASSWORD": "pass",
  "DB_HOST": "ep-xxx.us-east-2.aws.neon.tech",
  "DB_NAME": "neondb",
  "DB_PORT": "5432",
  "USE_NEON": "true"
}
```
- [ ] Secret name: `potential-parakeet/dev`
- [ ] Click Next → Next → Store

### Store API Keys
- [ ] Go to [tiingo.com](https://www.tiingo.com) → Sign up → Get API token
- [ ] Back to Secrets Manager → Store new secret
- [ ] Paste:
```json
{
  "TIINGO_API_KEY": "your-tiingo-key-here",
  "TIINGO_IS_PREMIUM": "true",
  "POLYGON_API_KEY": "",
  "ALPHA_VANTAGE_API_KEY": ""
}
```
- [ ] Secret name: `potential-parakeet/dev/api-keys`
- [ ] Click Next → Next → Store

### Verify
- [ ] Run: `aws secretsmanager get-secret-value --secret-id potential-parakeet/dev --query SecretString --output text`
- [ ] Should show your database credentials

---

## Part 4: Local Development (10 minutes)

### Setup Environment
- [ ] Navigate to project: `cd "c:\Users\ckr_4\01 Web Projects\potential-parakeet\potential-parakeet-2"`
- [ ] Copy `.env.example` to `.env`: `cp .env.example .env`
- [ ] Edit `.env` file:
  - Set `TIINGO_API_KEY=your-key`
  - Leave `USE_NEON=false` (for local dev with SQLite)
  - Set `AWS_REGION=us-east-1`
  - Set `AWS_SECRETS_MANAGER_NAME=potential-parakeet/dev`

### Install Dependencies
- [ ] Create virtual environment:
  - Windows: `python -m venv venv && venv\Scripts\activate`
  - Mac/Linux: `python -m venv venv && source venv/bin/activate`
- [ ] Install: `pip install -r requirements.txt` (takes ~3 minutes)

### Initialize Database
- [ ] Run migrations: `alembic upgrade head`
- [ ] Expected output: `Running upgrade  -> 20250112_0001, Initial migration`

### Test Setup
- [ ] Test database: `python -c "from backend.database.connection import init_db; init_db(); print('✅ OK')"`
- [ ] Test async: `python -c "import asyncio; from backend.database.connection import init_async_db; asyncio.run(init_async_db()); print('✅ OK')"`

---

## Part 5: Terraform Deployment (Optional - 10 minutes)

### Install Terraform
- [ ] Windows: `choco install terraform`
- [ ] Mac: `brew install terraform`
- [ ] Linux: Download from [terraform.io](https://www.terraform.io/downloads)
- [ ] Verify: `terraform --version`

### Set Variables
- [ ] Windows PowerShell:
```powershell
$env:TF_VAR_neon_database_url = "postgresql+asyncpg://user:pass@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require"
$env:TF_VAR_db_username = "user"
$env:TF_VAR_db_password = "pass"
$env:TF_VAR_db_host = "ep-xxx.us-east-2.aws.neon.tech"
$env:TF_VAR_tiingo_api_key = "your-key"
```

- [ ] Mac/Linux Bash:
```bash
export TF_VAR_neon_database_url="postgresql+asyncpg://user:pass@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require"
export TF_VAR_db_username="user"
export TF_VAR_db_password="pass"
export TF_VAR_db_host="ep-xxx.us-east-2.aws.neon.tech"
export TF_VAR_tiingo_api_key="your-key"
```

### Deploy Infrastructure
- [ ] Navigate: `cd infrastructure/terraform`
- [ ] Initialize: `terraform init`
- [ ] Plan: `terraform plan -var-file=../environments/dev.tfvars`
- [ ] Apply: `terraform apply -var-file=../environments/dev.tfvars`
- [ ] Type `yes` when prompted

### Verify Deployment
- [ ] Run: `terraform output`
- [ ] Should show S3 bucket names, secret ARNs, etc.
- [ ] Test S3: `aws s3 ls | grep potential-parakeet`

---

## Verification Tests

### ✅ Test 1: AWS Credentials
```bash
aws sts get-caller-identity
# Should show your account ID and user
```

### ✅ Test 2: Neon Connection
```bash
python -c "import psycopg2; conn = psycopg2.connect('YOUR_NEON_URL'); print('✅ Connected'); conn.close()"
```

### ✅ Test 3: Secrets Manager
```bash
aws secretsmanager get-secret-value --secret-id potential-parakeet/dev --query SecretString --output text
# Should show your database credentials
```

### ✅ Test 4: S3 Buckets
```bash
aws s3 ls | grep potential-parakeet
# Should show cache and artifacts buckets
```

### ✅ Test 5: Local Database
```bash
alembic current
# Should show: 20250112_0001 (head)
```

### ✅ Test 6: Python Imports
```bash
python -c "from backend.database.connection import get_async_db; from backend.utils.secrets import get_database_credentials; print('✅ All imports OK')"
```

---

## Troubleshooting Quick Fixes

### AWS CLI not found
```bash
# Add to PATH (Windows)
# System Properties → Environment Variables → Path → Add:
C:\Program Files\Amazon\AWSCLIV2\
# Restart terminal
```

### Terraform not found
```bash
# Windows: choco install terraform
# Mac: brew install terraform
# Verify: terraform --version
```

### Python module not found
```bash
# Ensure virtual environment is activated
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate
# Reinstall: pip install -r requirements.txt
```

### Can't connect to Neon
- [ ] Check connection string has `?sslmode=require`
- [ ] Verify Neon project is not suspended (check neon.tech dashboard)
- [ ] Test with raw psql: `psql "YOUR_CONNECTION_STRING"`

### Secrets Manager access denied
```bash
# Verify IAM permissions
aws iam list-attached-user-policies --user-name terraform-deployer
```

---

## What You Should Have Now

- ✅ AWS account with IAM user
- ✅ AWS CLI configured
- ✅ Neon PostgreSQL database
- ✅ Database credentials in AWS Secrets Manager
- ✅ API keys in AWS Secrets Manager
- ✅ S3 buckets (if deployed Terraform)
- ✅ Local development environment working
- ✅ Database initialized with Alembic

---

## Next Steps

**For Development:**
1. Start FastAPI server: `uvicorn backend.main:app --reload`
2. Test API endpoints: `http://localhost:8000/docs`
3. Add your first trade via API

**For Production Deployment:**
1. Complete Phase 2: S3 Cache Storage
2. Complete Phase 3: Lambda Functions
3. Complete Phase 4: Async API Conversion
4. Deploy to production

**See:** [MIGRATION_PROGRESS.md](MIGRATION_PROGRESS.md) for roadmap

---

## Cost Tracking

**Current Monthly Cost (Free Tier):**
- AWS: $0 (within free tier limits)
- Neon: $0 (free tier: 0.25 vCPU)
- **Total: $0/month**

**After Free Tier (12 months):**
- AWS: ~$5/month (S3 + Secrets Manager)
- Neon: $0 (still in free tier)
- **Total: ~$5/month**

**Set up cost alerts:**
1. Go to [AWS Billing Console](https://console.aws.amazon.com/billing)
2. Billing Preferences → Check "Receive Billing Alerts"
3. CloudWatch → Create alarm for > $10/month

---

## Security Reminders

- ⚠️ Never commit `.env` file
- ⚠️ Never commit `terraform.tfvars`
- ⚠️ Never share AWS credentials
- ⚠️ Enable MFA on all accounts
- ⚠️ Use IAM user, not root account

---

## Support

**Issues?** Check:
1. [SETUP_GUIDE.md](SETUP_GUIDE.md) - Detailed setup instructions
2. [MIGRATION_PROGRESS.md](MIGRATION_PROGRESS.md) - Implementation details
3. [infrastructure/README.md](infrastructure/README.md) - Terraform guide

**Still stuck?** Open an issue with:
- What you tried
- Error message (full output)
- Operating system
- AWS region

---

**Setup Time:** ~30-45 minutes
**Difficulty:** Beginner-friendly
**Cost:** $0 (free tier)

✅ **Ready to build!**
