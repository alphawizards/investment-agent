# Claude Migration Implementation Prompt
## Potential Parakeet: AWS + Cloudflare + Neon PostgreSQL Migration

**Repository**: `C:\Users\ckr_4\01 Web Projects\potential-parakeet\potential-parakeet-2`

---

## 🎯 Mission Statement

You are tasked with migrating the **Potential Parakeet** quantitative trading platform from a monolithic Docker-based architecture to a modern serverless architecture using:

- **AWS Lambda** - Compute layer (API handlers, data ingest)
- **AWS S3** - Cache storage (replacing local Parquet files)
- **Neon PostgreSQL** - Serverless database (replacing SQLite)
- **Cloudflare** - Edge layer (Workers for auth, Pages for frontend)
- **Terraform** - Infrastructure as Code

---

## 📚 Required Reading (In Order)

Before making ANY changes, you MUST read and understand these files in the `Migration/` directory:

| Priority | File | Purpose |
|----------|------|---------|
| 1️⃣ | `MIGRATION_STRATEGY_DOCUMENT.md` | **Primary Source of Truth** - Complete audit, target architecture, 7-phase roadmap |
| 2️⃣ | `Critical Files Summary for Ralph.md` | Quick reference to key files for navigation |
| 3️⃣ | `Ralph Implementation Guide_ Potential Parakeet Migration.md` | Step-by-step guide with code patterns |
| 4️⃣ | `Ralph Implementation Checklist_ Potential Parakeet Migration.md` | Detailed task checklist |
| 5️⃣ | `lambda_daily_ingest.py` | Reference implementation for Lambda handler |
| 6️⃣ | `market_data_schema.sql` | PostgreSQL schema for market data |

---

## ⚠️ Critical Constraints

### Non-Negotiable Requirements

1. **No Breaking Changes** - Existing API contracts must remain backward compatible
2. **Async First** - All database and HTTP operations must use async/await
3. **Type Safety** - Full type hints on all new code (match existing codebase style)
4. **Connection Pooling** - Use `pool_size=1, max_overflow=0` for Lambda compatibility
5. **Secrets Management** - All credentials via AWS Secrets Manager (never hardcode)
6. **Idempotency** - All data operations must be idempotent (UPSERT patterns)

### Architecture Decisions Already Made

- **Database Driver**: `asyncpg` with async SQLAlchemy
- **HTTP Client**: `httpx` (replacing `requests`)
- **Lambda Wrapper**: `mangum` for FastAPI
- **IaC Tool**: Terraform (not CDK or CloudFormation)
- **Logging**: AWS Lambda Powertools

---

## 🏗️ Phase-by-Phase Implementation

### Phase 1: Foundation (CRITICAL - Start Here)

**Goal**: Establish database connectivity and Infrastructure as Code foundation.

#### Task 1.1: Database Migration to Neon PostgreSQL

```
Files to Modify:
├── backend/config.py           # Add NEON_DATABASE_URL support
├── backend/database/connection.py  # Convert to async SQLAlchemy
├── requirements.txt            # Add asyncpg, alembic, psycopg2-binary
└── alembic/                    # Initialize Alembic migrations (create)
```

**Key Code Pattern** (from `lambda_daily_ingest.py`):
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

engine = create_async_engine(
    config.database_url,
    pool_size=1,          # Lambda: 1 connection per instance
    max_overflow=0,       # No connection overflow
    pool_pre_ping=True,   # Verify connections before use
    echo=False
)
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)
```

#### Task 1.2: Infrastructure as Code Setup

```
Create Directory Structure:
infrastructure/
├── terraform/
│   ├── main.tf           # Provider config, backend state
│   ├── variables.tf      # Input variables
│   ├── lambda.tf         # Lambda function definitions
│   ├── api_gateway.tf    # API Gateway REST API
│   ├── s3.tf             # S3 buckets for cache
│   ├── iam.tf            # IAM roles and policies
│   ├── secrets.tf        # Secrets Manager
│   ├── eventbridge.tf    # Scheduled triggers
│   └── outputs.tf        # Output values
└── environments/
    ├── dev.tfvars
    ├── staging.tfvars
    └── prod.tfvars
```

#### Task 1.3: Environment & Secrets Management

```
Files to Create/Modify:
├── .env.example          # Update with AWS/Neon vars
├── backend/config.py     # Add secrets retrieval from AWS
└── backend/utils/secrets.py  # AWS Secrets Manager helper (create)
```

---

### Phase 2: Storage Layer Refactoring

**Goal**: Replace local file system with S3 for all Parquet cache operations.

```
Files to Create/Modify:
├── backend/aws/s3_cache.py        # NEW: S3 cache adapter
├── strategy/fast_data_loader.py   # Refactor to use S3
├── strategy/tiingo_data_loader.py # Refactor to use S3
└── strategy/unified_asx_loader.py # Refactor to use S3
```

**S3 Cache Pattern**:
```python
import aioboto3
import pandas as pd
from io import BytesIO

class S3CacheStorage:
    def __init__(self, bucket: str, prefix: str = "cache/"):
        self.bucket = bucket
        self.prefix = prefix
    
    async def read_parquet(self, key: str) -> pd.DataFrame:
        async with aioboto3.Session().client('s3') as s3:
            obj = await s3.get_object(Bucket=self.bucket, Key=f"{self.prefix}{key}")
            body = await obj['Body'].read()
            return pd.read_parquet(BytesIO(body))
    
    async def write_parquet(self, key: str, df: pd.DataFrame) -> None:
        buffer = BytesIO()
        df.to_parquet(buffer, engine='pyarrow', compression='snappy')
        buffer.seek(0)
        async with aioboto3.Session().client('s3') as s3:
            await s3.put_object(Bucket=self.bucket, Key=f"{self.prefix}{key}", Body=buffer.getvalue())
```

---

### Phase 3: Application Decomposition (Lambda Functions)

**Goal**: Decompose monolithic FastAPI into separate Lambda functions.

```
Create Lambda Handlers:
lambda/
├── trades/
│   ├── handler.py        # Trades API Lambda
│   └── requirements.txt
├── data/
│   ├── handler.py        # Data API Lambda
│   └── requirements.txt
├── strategies/
│   ├── handler.py        # Strategies API Lambda
│   └── requirements.txt
├── scanner/
│   ├── handler.py        # Scanner API Lambda
│   └── requirements.txt
└── ingest/
    ├── handler.py        # Daily data ingest (use lambda_daily_ingest.py as base)
    └── requirements.txt
```

**Lambda Handler Pattern** (using Mangum):
```python
from mangum import Mangum
from fastapi import FastAPI
from backend.routers.trades import router

app = FastAPI()
app.include_router(router)

handler = Mangum(app, lifespan="off")
```

---

### Phase 4: API Layer (Convert to Async)

**Goal**: Convert all FastAPI routes to async operations.

```
Files to Modify:
├── backend/routers/trades.py      # Convert to async
├── backend/routers/data.py        # Convert to async
├── backend/routers/strategies.py  # Convert to async
├── backend/routers/scanner.py     # Convert to async
├── backend/routers/dashboard.py   # Convert to async
└── backend/main.py                # Update for Lambda compatibility
```

**Async Route Pattern**:
```python
# BEFORE (sync)
@router.get("/trades")
def get_trades(db: Session = Depends(get_db)):
    return db.query(Trade).all()

# AFTER (async)
@router.get("/trades")
async def get_trades(db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(Trade))
    return result.scalars().all()
```

---

### Phase 5: Cloudflare Edge Layer

**Goal**: Deploy frontend to Cloudflare Pages, implement edge authentication.

```
Create:
cloudflare/
├── workers/
│   ├── auth-worker/       # JWT validation at edge
│   │   ├── index.js
│   │   └── wrangler.toml
│   └── rate-limiter/      # Rate limiting worker
│       ├── index.js
│       └── wrangler.toml
└── pages/
    └── wrangler.toml      # Frontend deployment config
```

---

### Phase 6: CI/CD Pipeline

**Goal**: Automated testing and deployment via GitHub Actions.

```
Create:
.github/
└── workflows/
    ├── test.yml           # Run tests on PR
    ├── deploy-dev.yml     # Deploy to dev on push to develop
    └── deploy-prod.yml    # Deploy to prod on push to main
```

---

### Phase 7: Monitoring & Observability

**Goal**: CloudWatch integration, structured logging, alerting.

```
Implement in Lambda handlers:
- AWS Lambda Powertools (Logger, Tracer, Metrics)
- CloudWatch dashboards (via Terraform)
- SNS alerts for errors
```

---

## 📋 Execution Checklist

Use this checklist to track progress:

```markdown
## Phase 1: Foundation
- [ ] 1.1 Install asyncpg, alembic, psycopg2-binary in requirements.txt
- [ ] 1.2 Update backend/config.py with NEON_DATABASE_URL
- [ ] 1.3 Refactor backend/database/connection.py to async
- [ ] 1.4 Initialize Alembic and create initial migration
- [ ] 1.5 Create infrastructure/terraform/ directory structure
- [ ] 1.6 Write main.tf with AWS provider config
- [ ] 1.7 Create AWS Secrets Manager config in Terraform

## Phase 2: Storage
- [ ] 2.1 Create backend/aws/s3_cache.py
- [ ] 2.2 Add boto3, aioboto3, s3fs to requirements.txt
- [ ] 2.3 Refactor strategy/fast_data_loader.py for S3
- [ ] 2.4 Create S3 bucket definitions in Terraform

## Phase 3: Lambda
- [ ] 3.1 Create lambda/ directory structure
- [ ] 3.2 Implement trades Lambda handler
- [ ] 3.3 Implement data Lambda handler
- [ ] 3.4 Implement strategies Lambda handler
- [ ] 3.5 Add Lambda definitions to Terraform
- [ ] 3.6 Configure API Gateway in Terraform

## Phase 4: Async Conversion
- [ ] 4.1 Convert all routers to async
- [ ] 4.2 Update all database queries to async
- [ ] 4.3 Replace requests with httpx

## Phase 5: Cloudflare
- [ ] 5.1 Create Cloudflare Workers for auth
- [ ] 5.2 Configure Cloudflare Pages deployment

## Phase 6: CI/CD
- [ ] 6.1 Create GitHub Actions test workflow
- [ ] 6.2 Create deploy workflow for dev
- [ ] 6.3 Create deploy workflow for prod

## Phase 7: Monitoring
- [ ] 7.1 Add Lambda Powertools to all handlers
- [ ] 7.2 Create CloudWatch dashboards in Terraform
- [ ] 7.3 Configure SNS alerts
```

---

## 🚨 Common Pitfalls to Avoid

1. **Connection Exhaustion** - Always use `pool_size=1` for Lambda database connections
2. **Cold Start Timeouts** - Keep Lambda package size small, use layers for dependencies
3. **Import Errors** - Ensure all imports work both locally and in Lambda environment
4. **Missing SSL** - Neon requires SSL (`?sslmode=require` in connection string)
5. **Sync in Async** - Never use `requests` library; always use `httpx` async client
6. **Hardcoded Paths** - Replace ALL `Path("cache/...")` with S3 operations
7. **Missing Type Hints** - The codebase has excellent type coverage; maintain it

---

## 📊 Success Criteria

The migration is complete when:

1. ✅ All API endpoints respond correctly from Lambda via API Gateway
2. ✅ Daily data ingest runs on schedule via EventBridge trigger
3. ✅ All market data stored in Neon PostgreSQL (not SQLite)
4. ✅ All cached Parquet files stored in S3 (not local filesystem)
5. ✅ Frontend deployed to Cloudflare Pages
6. ✅ Authentication validated at Cloudflare edge
7. ✅ CI/CD pipeline deploys automatically on merge to main
8. ✅ CloudWatch dashboards show healthy metrics
9. ✅ All existing tests pass with new infrastructure

---

## 🔗 Quick Reference Commands

```bash
# Initialize Terraform
cd infrastructure/terraform
terraform init
terraform plan -var-file=environments/dev.tfvars

# Run Alembic migrations
alembic upgrade head

# Test Lambda locally
cd lambda/trades
python -c "from handler import handler; print(handler({}, None))"

# Deploy with Terraform
terraform apply -var-file=environments/prod.tfvars -auto-approve
```

---

## 💡 Ask for Clarification If:

1. The existing code behavior is unclear
2. You need credentials or access to external services
3. A design decision could go multiple valid directions
4. The migration documentation conflicts with actual code
5. You encounter edge cases not covered in this prompt

---

**Ready to begin? Start with Phase 1, Task 1.1: Database Migration to Neon PostgreSQL.**
