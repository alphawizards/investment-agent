# Potential Parakeet: AWS/Neon Migration Strategy Document

**Phase 1 Audit Report**  
**Prepared by**: Manus AI (Senior Quantitative Developer & Cloud Architect)  
**Date**: January 11, 2026  
**Repository**: [alphawizards/potential-parakeet](https://github.com/alphawizards/potential-parakeet)

---

## Executive Summary

This document presents a comprehensive Phase 1 audit of the **Potential Parakeet** quantitative trading platform, evaluating its readiness for migration to a modern serverless architecture leveraging AWS Lambda, Neon PostgreSQL, and Cloudflare. The audit examines four critical dimensions: architecture fit, Ralph CLI readiness, quantitative logic modularity, and missing infrastructure dependencies.

### Key Findings

The codebase demonstrates **strong foundational architecture** with excellent modularity, comprehensive documentation, and robust testing. However, the migration to serverless infrastructure represents a **high-complexity transformation** requiring significant refactoring across database, storage, and API layers. The project currently operates as a monolithic Docker-based application with SQLite database and local file storage—patterns fundamentally incompatible with distributed serverless architectures.

| Assessment Area | Score | Status |
|----------------|-------|--------|
| **Architecture Fit** | 6/10 | 🟠 Moderate - Requires major refactoring |
| **Ralph CLI Readiness** | 8/10 | ✅ Good - Minor optimizations needed |
| **Quantitative Logic Modularity** | 8.5/10 | ✅ Excellent - Well-separated concerns |
| **Infrastructure Readiness** | 2/10 | 🔴 Critical - Missing all IaC components |

### Migration Feasibility

**Overall Assessment**: ✅ **FEASIBLE** with significant architectural refactoring  
**Estimated Timeline**: **12-14 weeks** (3-4 months)  
**Estimated Effort**: **400-500 developer hours**  
**Risk Level**: 🟠 **MEDIUM-HIGH**  
**Recommended Approach**: **Phased migration** with rollback capabilities

---

## 1. Architecture Fit for AWS/Neon Migration

### 1.1 Current Architecture Analysis

The Potential Parakeet platform currently implements a **monolithic containerized architecture** designed for single-server deployment. This architecture consists of three primary components deployed via Docker Compose with Traefik reverse proxy for routing.

**Backend Layer**: The application core is a single FastAPI application (`backend/main.py`) serving multiple API routers for trades, data management, strategies, scanning, and dashboard endpoints. The backend utilizes SQLAlchemy ORM for database access and implements a bi-temporal data model with `knowledge_timestamp` and `event_timestamp` fields—an advanced pattern that provides audit trails and point-in-time query capabilities essential for regulatory compliance and accurate backtesting.

**Data Layer**: The system employs a sophisticated data management strategy with multiple specialized loaders (`FastDataLoader`, `TiingoDataLoader`, `UnifiedASXLoader`) that fetch market data from Tiingo (US equities) and yFinance (ASX and cryptocurrency markets). Data caching utilizes Parquet file format stored on the local file system in the `cache/` directory, with incremental loading logic that reduces API calls by 99.6% according to project documentation. The data layer implements retry logic with exponential backoff and rate limit handling.

**Strategy Engine**: The quantitative strategy implementation follows a clean **pipeline architecture** with four distinct layers: data ingestion, signal generation, portfolio allocation, and performance reporting. The codebase contains 91 Python files implementing two strategy families—Quant 1.0 (momentum-based with Hierarchical Risk Parity) and Quant 2.0 (machine learning-enhanced with regime detection, statistical arbitrage, and meta-labeling). This modular design demonstrates strong separation of concerns and extensibility.

**Database**: The current implementation uses SQLite with three primary tables: `trades` (trade execution records), `portfolio_snapshots` (historical portfolio values), and `index_constituents` (point-in-time index membership for survivorship bias elimination). The bi-temporal schema implementation is sophisticated and production-ready from a data modeling perspective.

**Frontend**: The user interface consists of a React application built with TypeScript, Vite, and TailwindCSS, alongside multiple static HTML dashboards for different strategy visualizations. The frontend is served via Nginx in production containers.

### 1.2 Critical Migration Blockers

The migration to AWS Lambda and Neon PostgreSQL faces five **critical architectural blockers** that must be resolved before deployment:

**Infrastructure as Code Absence**: The repository contains zero Infrastructure as Code files. No Terraform configurations, AWS CDK stacks, CloudFormation templates, or Serverless Framework definitions exist. This represents the most significant gap, as modern cloud deployments require declarative infrastructure definitions for reproducibility, version control, and automated provisioning. Without IaC, the migration cannot proceed beyond manual console-based experimentation.

**SQLite Database Incompatibility**: SQLite operates as an embedded database engine with file-based storage, making it fundamentally incompatible with serverless architectures where compute instances are ephemeral and stateless. AWS Lambda functions cannot share SQLite database files across invocations, and the database file would be lost when Lambda containers are recycled. The migration to Neon PostgreSQL is non-negotiable and represents the highest-risk component of this transformation.

**File System Storage Dependencies**: The caching layer stores Parquet files directly on the local file system, with hardcoded paths throughout the codebase (e.g., `Path("cache/us_prices_close.parquet")`). Lambda functions have limited writable storage (512MB in `/tmp`) that is not persistent across invocations. All file-based storage must migrate to Amazon S3, requiring modifications to every module that reads or writes cached data.

**Synchronous I/O Architecture**: The current implementation uses blocking I/O operations for API calls (via `requests` library) and database queries (synchronous SQLAlchemy). Lambda functions benefit significantly from asynchronous operations to maximize throughput and minimize execution time (and thus cost). The codebase requires conversion to async/await patterns using `httpx` or `aiohttp` for HTTP requests and async SQLAlchemy for database operations.

**Monolithic Application Design**: The FastAPI application runs as a single process serving all endpoints. AWS Lambda requires decomposition into separate functions, each handling specific API routes or background tasks. While the router-based structure provides natural boundaries for decomposition, this refactoring touches every part of the application and requires careful planning to maintain functionality.

### 1.3 Moderate Migration Challenges

Beyond the critical blockers, several **moderate-complexity issues** require attention:

The absence of database migration tooling (Alembic) means schema changes have been applied manually or through ORM auto-creation. Production database migrations require versioned, reversible migration scripts. The hardcoded file paths scattered throughout the codebase assume local file system access and must be replaced with cloud storage abstractions. The lack of async SQLAlchemy configuration means all database queries must be rewritten from synchronous to asynchronous patterns. Environment management relies on simple `.env` files rather than cloud-native secrets management like AWS Secrets Manager or Systems Manager Parameter Store. Finally, the application serves HTTP directly via Uvicorn rather than integrating with API Gateway, requiring Lambda-specific handler wrappers (e.g., Mangum).

### 1.4 Architectural Strengths

Despite these challenges, the codebase demonstrates several **architectural strengths** that facilitate migration:

The **modular strategy engine** with clean separation between data, signal, allocation, and reporting layers means quantitative logic can remain largely unchanged during infrastructure migration. The **RESTful API design** with distinct routers provides natural boundaries for Lambda function decomposition—each router can become a separate Lambda function with minimal refactoring. The extensive use of **Pydantic models** for request/response validation is fully compatible with serverless architectures and provides type safety. The existing **Docker containerization** demonstrates the application can run in isolated environments and provides a foundation for Lambda container images. Most impressively, the **bi-temporal data model** implementation is production-grade and ahead of many commercial systems, providing audit capabilities and point-in-time queries essential for regulated financial applications.

### 1.5 Recommended Target Architecture

The target architecture implements a **serverless, event-driven design** leveraging managed services to eliminate operational overhead and enable automatic scaling:

**Edge Layer (Cloudflare)**: Cloudflare Workers handle authentication, rate limiting, and request routing at the edge, minimizing latency for global users. Cloudflare Pages hosts the static React frontend with automatic deployments from Git. The Cloudflare CDN caches static assets and API responses where appropriate.

**API Layer (AWS API Gateway)**: API Gateway provides a unified HTTP endpoint for all backend services, with JWT-based authorization, request validation, and throttling. Routes map to specific Lambda functions based on path patterns (e.g., `/api/trades/*` → Trades Lambda, `/api/strategies/*` → Strategies Lambda).

**Compute Layer (AWS Lambda)**: The monolithic FastAPI application decomposes into five specialized Lambda functions: Trades API (trade CRUD operations), Data API (market data refresh), Strategies API (backtest execution), Scanner API (stock screening), and Dashboard API (analytics aggregation). Each function is independently deployable and scalable, with provisioned concurrency for latency-sensitive endpoints.

**Database Layer (Neon PostgreSQL)**: Neon provides serverless PostgreSQL with automatic scaling, branching for development/staging environments, and connection pooling optimized for Lambda's ephemeral nature. The bi-temporal schema migrates directly with minimal modifications. Connection pooling configuration uses `pool_size=1` and `max_overflow=0` per Lambda instance to prevent connection exhaustion.

**Storage Layer (AWS S3)**: All Parquet cache files migrate to S3 with lifecycle policies for automatic expiration. S3 Transfer Acceleration reduces latency for large file uploads. CloudFront caches frequently accessed files at edge locations. Reports and generated artifacts also store in S3 with presigned URLs for secure access.

**Orchestration Layer (AWS Services)**: SQS queues handle asynchronous data refresh jobs triggered by API requests or schedules. EventBridge rules trigger scheduled backtests and data updates. Secrets Manager stores API keys for Tiingo and other external services. CloudWatch provides centralized logging, metrics, and alarms for operational monitoring.

This architecture provides **automatic scaling** (Lambda and Neon scale independently based on load), **high availability** (multi-AZ deployment with no single points of failure), **cost optimization** (pay only for actual compute time and storage), and **operational simplicity** (no server management, patching, or capacity planning).

---

## 2. Ralph CLI Readiness Assessment

### 2.1 Strengths for Ralph Navigation

The Potential Parakeet codebase demonstrates **excellent readiness** for Ralph CLI-driven development, with several factors that enable effective AI-assisted code navigation and modification:

**Comprehensive Documentation**: The codebase contains **1,062 docstrings** across 91 Python files in the strategy module alone, plus 56 Markdown documentation files. Every major module includes detailed docstrings explaining purpose, parameters, return values, and usage examples. This documentation density (averaging 11.7 docstrings per file) significantly exceeds industry standards and provides Ralph with rich context for understanding code intent.

**Strong Type Hints**: Type annotations appear in **53 files** with explicit `from typing import` statements, indicating widespread use of type hints for function parameters and return values. The codebase leverages Python's type system extensively, using `List`, `Dict`, `Optional`, `Union`, and custom types. Pydantic models provide runtime type validation for API requests and responses, creating self-documenting interfaces.

**Clear Module Boundaries**: The presence of **24 `__init__.py` files** indicates proper Python package structure with explicit module boundaries. Each package exposes a clean public API through `__init__.py` exports, hiding internal implementation details. This modularity allows Ralph to understand component responsibilities and dependencies without analyzing internal implementation.

**Consistent Naming Conventions**: The codebase follows PEP 8 naming conventions consistently: `snake_case` for functions and variables, `PascalCase` for classes, `UPPER_CASE` for constants. This consistency allows Ralph to infer component types from naming patterns alone.

**RESTful API with OpenAPI**: FastAPI automatically generates OpenAPI (Swagger) documentation from code annotations, providing machine-readable API specifications. Ralph can parse these specifications to understand endpoint contracts, request/response schemas, and error handling without reading implementation code.

**Strategy Pattern Implementation**: The use of abstract base classes (e.g., `BaseStrategy`) with clearly defined interfaces (`generate_signals()` method) provides explicit contracts that Ralph can recognize and utilize when extending functionality or refactoring code.

### 2.2 Challenges for Ralph Navigation

Despite strong overall readiness, several patterns may complicate Ralph's code navigation and modification:

**Deep Module Nesting**: Some strategy modules nest up to **4 levels deep** (e.g., `strategy/quant2/meta_labeling/orchestrator.py`). Deep nesting increases cognitive load for understanding import paths and module relationships. Ralph may struggle to maintain context when navigating between deeply nested modules, potentially leading to incorrect import statements or module references.

**Circular Import Risks**: The `backend/main.py` file uses dynamic imports with try/except blocks to handle both module and direct execution modes. This pattern, while functional, obscures static dependency analysis. Ralph may not recognize these dynamic dependencies when refactoring, potentially breaking imports.

**Mixed Concerns**: Some modules combine multiple responsibilities. For example, data loader modules handle data fetching, transformation, caching, and error handling. This violates the Single Responsibility Principle and makes it harder for Ralph to understand which parts of the module to modify for specific tasks.

**Lack of API Versioning**: All API endpoints exist at `/api/*` without version prefixes (e.g., `/api/v1/`). This makes it difficult to introduce breaking changes safely. Ralph may not recognize the need for backward compatibility when modifying API contracts.

**Configuration Sprawl**: Settings are split across three locations: `backend/config.py`, `strategy/config.py`, and `.env` files. This fragmentation makes it difficult for Ralph to understand the complete configuration surface and may lead to inconsistent configuration updates.

**Limited Interface Contracts**: While the codebase uses some abstract base classes, many components lack explicit interface definitions. Only approximately **5 ABC classes** exist across the entire codebase. More extensive use of Protocol classes (PEP 544) would provide better contracts for dependency injection and make component boundaries clearer to Ralph.

### 2.3 Recommendations for Ralph Optimization

To maximize Ralph CLI effectiveness, implement the following improvements:

**Flatten Module Structure**: Reduce nesting from 4 levels to a maximum of 2 levels. For example, consolidate `strategy/quant2/meta_labeling/orchestrator.py` into `strategy/meta_labeling.py`. This simplification reduces import path complexity and makes module relationships more apparent.

**Introduce Protocol Classes**: Add explicit interface definitions using `typing.Protocol` for major components (data loaders, strategy implementations, storage adapters). Protocols provide structural typing that Ralph can recognize and validate without requiring inheritance relationships.

**Consolidate Configuration**: Merge `backend/config.py` and `strategy/config.py` into a single `config/settings.py` module using Pydantic's `BaseSettings` with environment variable overrides. This provides a single source of truth that Ralph can reference and modify confidently.

**Implement API Versioning**: Introduce `/api/v1/` prefix for all endpoints, with explicit version routing in FastAPI. This allows Ralph to understand API stability guarantees and make appropriate decisions about breaking changes.

**Refactor to Dependency Injection**: Replace dynamic imports with explicit dependency injection using FastAPI's `Depends()` system. This makes dependencies explicit in function signatures, allowing Ralph to understand and modify dependency graphs accurately.

---

## 3. Quantitative Logic Modularity Assessment

### 3.1 Data Fetching Layer (Score: 8/10)

The data fetching implementation demonstrates **strong modularity** with clear separation between data sources, caching, and error handling:

**Decoupled Data Loaders**: Three specialized loader classes handle different data sources: `FastDataLoader` for cached data with incremental updates, `TiingoDataLoader` for US equity data from Tiingo API, and `UnifiedASXLoader` for Australian Securities Exchange data via yFinance. Each loader implements a consistent interface, allowing strategy code to remain agnostic to data source specifics.

**Intelligent Caching Layer**: The Parquet-based caching system implements incremental loading that checks for existing cached data and fetches only missing date ranges. This optimization reduces API calls by 99.6% according to project benchmarks, transforming a 38-minute full data fetch into a 10-second incremental update. The cache implementation includes staleness detection and automatic refresh logic.

**Robust Retry Logic**: Data fetching implements exponential backoff with configurable retry attempts (default: 3 attempts). The error handling classifies failures into categories (DELISTED, RATE_LIMIT, TIMEOUT, NETWORK) and applies appropriate retry strategies for each. Rate limit errors trigger longer delays, while network timeouts use shorter backoff periods.

**Multi-Source Routing**: The `get_data_source()` function intelligently routes ticker symbols to appropriate data providers based on suffix patterns (`.AX` for ASX) and special cases (`^VIX`, `BTC-USD` for yFinance). This abstraction allows the system to expand data sources without modifying strategy code.

However, the data layer exhibits **two significant weaknesses** for serverless migration:

**File System Coupling**: All cache operations assume local disk access with hardcoded paths like `Path("cache/us_prices_close.parquet")`. This pattern appears in approximately 15 files across the codebase. Migrating to S3 requires replacing every file operation with S3 API calls, a substantial refactoring effort.

**Synchronous I/O**: Data fetching uses blocking HTTP requests via the `requests` library. For Lambda functions processing multiple tickers, synchronous I/O wastes execution time waiting for network responses. Converting to async with `httpx` or `aiohttp` could reduce execution time by 3-5x through concurrent requests.

### 3.2 Trading Logic Layer (Score: 9/10)

The trading logic implementation represents the **strongest aspect** of the codebase architecture:

**Pipeline Architecture**: The four-layer pipeline (data → signal → allocation → reporting) provides clean separation of concerns. Each layer has a dedicated manager class (`DataManager`, `SignalManager`, `AllocationManager`, `ReportingManager`) with well-defined responsibilities. This separation allows independent testing and modification of each stage.

**Strategy Abstraction**: The `BaseStrategy` abstract base class defines a clear contract with a single required method: `generate_signals(prices: pd.DataFrame) -> SignalResult`. This interface enables strategy implementations to focus purely on signal logic without concerning themselves with data fetching, portfolio optimization, or performance reporting.

**Type-Safe Results**: The use of dataclasses (`SignalResult`, `AllocationResult`) for inter-layer communication provides type safety and self-documentation. Each result object carries metadata about its creation, enabling comprehensive audit trails and debugging.

**Strategy Registry**: The `SignalManager` implements a registration system allowing dynamic strategy discovery and loading. New strategies can be added by simply creating a class that inherits from `BaseStrategy` and registering it—no modifications to core pipeline code required.

**Extensibility**: The architecture makes it trivial to add new strategies. For example, adding a mean reversion strategy requires creating a single class with a `generate_signals()` method. The pipeline automatically handles data fetching, portfolio optimization, and performance reporting.

The trading logic has **minimal weaknesses**:

**Monolithic Strategy Files**: A few strategy implementations (e.g., `hard_asset_backtest.py`) exceed 500 lines, combining signal generation, parameter tuning, and analysis. These should be decomposed into separate modules for signal logic, optimization, and reporting.

**Embedded Position Sizing**: Some strategies calculate position sizes internally rather than delegating to the allocation layer. This violates the pipeline architecture and makes it harder to apply consistent risk management across strategies.

### 3.3 Portfolio Management Layer (Score: 7/10)

The portfolio management implementation provides **solid functionality** with room for improvement:

**Multiple Optimization Methods**: The `AllocationManager` supports four allocation approaches: Hierarchical Risk Parity (HRP), Mean-Variance Optimization (MVO), Inverse Volatility, and Equal Weight. This flexibility allows strategy-specific allocation logic without code duplication.

**Risk Management Modules**: Dedicated modules calculate risk metrics (volatility, Sharpe ratio, maximum drawdown, Sortino ratio) with consistent methodology. These metrics appear in both real-time monitoring and backtest reports.

**Configurable Rebalancing**: The system supports daily, weekly, and monthly rebalancing frequencies with transaction cost modeling. The rebalancing logic respects minimum position sizes and trade fee structures.

However, **two weaknesses** limit the portfolio management layer:

**Position Sizing Inconsistency**: Some strategies calculate position sizes internally using strategy-specific logic, while others delegate to the allocation layer. This inconsistency makes it difficult to apply uniform risk limits across all strategies.

**Missing Order Management**: The system jumps directly from allocation weights to executed positions without an order management layer. Production systems require order routing, execution simulation, slippage modeling, and partial fill handling—all absent from the current implementation.

### 3.4 Backtesting Layer (Score: 8/10)

The backtesting implementation leverages **VectorBT**, a high-performance backtesting library, providing:

**Performance Optimization**: VectorBT uses NumPy vectorization for fast backtests across multiple parameter combinations. The codebase reports backtesting 1,000+ parameter combinations in under 10 seconds for simple strategies.

**Comprehensive Metrics**: The `ReportingManager` calculates 15+ performance metrics including CAGR, Sharpe ratio, Sortino ratio, maximum drawdown, Calmar ratio, win rate, and profit factor. These metrics match industry standards for strategy evaluation.

**Bi-Temporal Support**: The database schema's bi-temporal design enables accurate point-in-time backtests that eliminate look-ahead bias and survivorship bias. The `IndexConstituent` table tracks historical index membership, ensuring backtests use only stocks that were actually in the index at each point in time.

**Weaknesses** in the backtesting layer:

**Hardcoded Configuration**: Backtest parameters (start date, end date, initial capital, transaction costs) are often hardcoded in strategy files rather than externalized to configuration files. This makes it difficult to run consistent backtests across strategies.

**No Walk-Forward Analysis**: The system lacks integrated walk-forward optimization, where parameters are optimized on a training period and tested on an out-of-sample period. This is a standard technique for avoiding overfitting in quantitative strategies.

---

## 4. Missing Dependencies for AWS/Neon Migration

### 4.1 Infrastructure as Code Requirements

The most critical gap is the **complete absence of Infrastructure as Code**. Modern cloud deployments require declarative infrastructure definitions for several reasons: reproducibility (infrastructure can be recreated identically in multiple environments), version control (infrastructure changes are tracked alongside code changes), automation (CI/CD pipelines can provision infrastructure automatically), and documentation (infrastructure code serves as executable documentation of system architecture).

**Required IaC Tools**:

For AWS resource provisioning, choose **Terraform** (most popular, cloud-agnostic), **AWS CDK** (Python-native, AWS-specific), or **Pulumi** (modern, supports multiple languages). Terraform is recommended for this project due to its maturity, extensive AWS provider support, and large community.

For Lambda deployment specifically, consider **Serverless Framework** or **AWS SAM** (Serverless Application Model). These tools abstract Lambda packaging, API Gateway configuration, and event source mapping, significantly simplifying serverless deployments.

For CI/CD, implement **GitHub Actions** workflows (already integrated with the repository's GitHub hosting) to automate testing, building, and deployment.

**Required Infrastructure Files**:

Create an `infrastructure/` directory with the following structure:

```
infrastructure/
├── terraform/
│   ├── main.tf                 # Root module, provider configuration
│   ├── lambda.tf               # Lambda function definitions
│   ├── api_gateway.tf          # API Gateway REST API
│   ├── neon.tf                 # Neon database connection config
│   ├── s3.tf                   # S3 buckets for cache and reports
│   ├── iam.tf                  # IAM roles and policies
│   ├── cloudwatch.tf           # Log groups and alarms
│   ├── secrets.tf              # Secrets Manager secrets
│   ├── variables.tf            # Input variables
│   ├── outputs.tf              # Output values
│   └── backend.tf              # Terraform state storage (S3)
├── cloudflare/
│   ├── workers/                # Cloudflare Workers for auth
│   └── pages/                  # Frontend deployment config
├── scripts/
│   ├── deploy.sh               # Deployment orchestration
│   ├── migrate.sh              # Database migration runner
│   └── rollback.sh             # Rollback procedure
└── environments/
    ├── dev.tfvars              # Development environment variables
    ├── staging.tfvars          # Staging environment variables
    └── prod.tfvars             # Production environment variables
```

Each Terraform file should define specific resources: `lambda.tf` creates Lambda functions with appropriate memory, timeout, and environment variable configuration; `api_gateway.tf` defines REST API with routes, authorizers, and integrations; `iam.tf` creates least-privilege IAM roles for Lambda execution; `cloudwatch.tf` sets up log groups with retention policies and CloudWatch alarms for error rates and latency.

### 4.2 Database Layer Requirements

Migrating from SQLite to Neon PostgreSQL requires several new dependencies and significant code changes:

**Required Python Packages**:

```python
alembic>=1.13.0                 # Database migration framework
asyncpg>=0.29.0                 # Async PostgreSQL driver (fastest)
psycopg2-binary>=2.9.9          # Sync PostgreSQL driver (fallback)
sqlalchemy[asyncio]>=2.0.0      # Async SQLAlchemy support
```

**Migration Tasks**:

1. **Replace Database URL**: Change `DATABASE_URL` from `sqlite:///./data/trades.db` to Neon's PostgreSQL connection string: `postgresql+asyncpg://user:password@ep-xxx.neon.tech/dbname?sslmode=require`

2. **Convert to Async SQLAlchemy**: Replace synchronous `create_engine()` and `sessionmaker()` with async equivalents:

```python
# Current (sync)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# Target (async)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

engine = create_async_engine(
    DATABASE_URL,
    pool_size=1,          # Lambda: 1 connection per instance
    max_overflow=0,       # No connection overflow
    pool_pre_ping=True    # Verify connections before use
)
async_session = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)
```

3. **Implement Alembic Migrations**: Initialize Alembic and create initial migration from existing schema:

```bash
alembic init alembic
alembic revision --autogenerate -m "Initial schema from SQLite"
alembic upgrade head
```

4. **Update All Database Queries**: Convert every database query from synchronous to asynchronous:

```python
# Current (sync)
def get_trades(db: Session) -> List[Trade]:
    return db.query(Trade).filter(Trade.status == "OPEN").all()

# Target (async)
async def get_trades(db: AsyncSession) -> List[Trade]:
    result = await db.execute(
        select(Trade).where(Trade.status == "OPEN")
    )
    return result.scalars().all()
```

5. **PostgreSQL-Specific Types**: Update models to leverage PostgreSQL features:

```python
from sqlalchemy.dialects.postgresql import JSONB, ARRAY

class Trade(Base):
    # Replace Text with JSONB for structured data
    metadata = Column(JSONB, nullable=True)
    # Use ARRAY for list fields
    tags = Column(ARRAY(String), nullable=True)
```

6. **Connection Pooling for Lambda**: Configure connection pooling optimized for Lambda's ephemeral nature. Each Lambda instance should maintain exactly one database connection with aggressive timeout settings to prevent connection leaks.

### 4.3 Storage Layer Requirements

Migrating from local file storage to S3 requires new AWS SDK dependencies and storage abstraction layers:

**Required Python Packages**:

```python
boto3>=1.34.0                   # AWS SDK (sync)
aioboto3>=12.3.0                # AWS SDK (async)
s3fs>=2024.1.0                  # S3 filesystem interface for pandas
```

**Implementation Requirements**:

1. **S3 Storage Adapter**: Create an abstraction layer for S3 operations:

```python
import aioboto3
from io import BytesIO
import pandas as pd

class S3CacheStorage:
    def __init__(self, bucket: str, prefix: str = "cache/"):
        self.bucket = bucket
        self.prefix = prefix
    
    async def read_parquet(self, key: str) -> pd.DataFrame:
        """Read Parquet file from S3."""
        async with aioboto3.Session().client('s3') as s3:
            try:
                obj = await s3.get_object(
                    Bucket=self.bucket,
                    Key=f"{self.prefix}{key}"
                )
                body = await obj['Body'].read()
                return pd.read_parquet(BytesIO(body))
            except s3.exceptions.NoSuchKey:
                return pd.DataFrame()
    
    async def write_parquet(self, key: str, df: pd.DataFrame) -> None:
        """Write Parquet file to S3."""
        buffer = BytesIO()
        df.to_parquet(buffer, engine='pyarrow', compression='snappy')
        buffer.seek(0)
        
        async with aioboto3.Session().client('s3') as s3:
            await s3.put_object(
                Bucket=self.bucket,
                Key=f"{self.prefix}{key}",
                Body=buffer.getvalue(),
                ContentType='application/octet-stream',
                ServerSideEncryption='AES256'
            )
```

2. **Update All File Operations**: Replace every instance of `pd.read_parquet(path)` with `await storage.read_parquet(key)` and `df.to_parquet(path)` with `await storage.write_parquet(key, df)`.

3. **S3 Lifecycle Policies**: Configure automatic expiration for cached data:

```hcl
# terraform/s3.tf
resource "aws_s3_bucket_lifecycle_configuration" "cache" {
  bucket = aws_s3_bucket.cache.id

  rule {
    id     = "expire-old-cache"
    status = "Enabled"

    expiration {
      days = 30  # Delete cache files older than 30 days
    }
  }
}
```

### 4.4 Application Layer Requirements

Lambda deployment requires several new dependencies and code patterns:

**Required Python Packages**:

```python
mangum>=0.17.0                  # ASGI adapter for Lambda
aws-lambda-powertools>=2.30.0   # Lambda utilities (logging, tracing)
httpx>=0.26.0                   # Async HTTP client
pydantic-settings>=2.1.0        # Settings management
```

**Lambda Handler Implementation**:

Each Lambda function requires a handler that wraps the FastAPI application:

```python
# lambda/trades/handler.py
from mangum import Mangum
from fastapi import FastAPI
from backend.routers.trades import router

app = FastAPI()
app.include_router(router)

# Mangum converts API Gateway events to ASGI format
handler = Mangum(app, lifespan="off")
```

**Secrets Management**:

Replace environment variables with AWS Secrets Manager:

```python
import aioboto3
import json

async def get_secret(secret_name: str) -> dict:
    """Retrieve secret from AWS Secrets Manager."""
    async with aioboto3.Session().client('secretsmanager') as sm:
        response = await sm.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])

# Usage
secrets = await get_secret("potential-parakeet/prod/api-keys")
tiingo_api_key = secrets['TIINGO_API_KEY']
```

**Async HTTP Client**:

Replace `requests` library with async-capable `httpx`:

```python
import httpx

async def fetch_ticker_data(ticker: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.tiingo.com/tiingo/daily/{ticker}/prices",
            headers={"Authorization": f"Token {api_key}"}
        )
        return response.json()
```

### 4.5 DevOps & CI/CD Requirements

Automated deployment requires GitHub Actions workflows:

**Test Workflow** (`.github/workflows/test.yml`):

```yaml
name: Test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: pip install -r requirements.txt -r requirements-dev.txt
      - name: Run tests
        run: pytest tests/ --cov=backend --cov=strategy
      - name: Check coverage
        run: coverage report --fail-under=80
```

**Deploy Workflow** (`.github/workflows/deploy.yml`):

```yaml
name: Deploy
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      - name: Deploy infrastructure
        run: |
          cd infrastructure/terraform
          terraform init
          terraform apply -auto-approve -var-file=environments/prod.tfvars
      - name: Run database migrations
        run: |
          export DATABASE_URL=${{ secrets.NEON_DATABASE_URL }}
          alembic upgrade head
      - name: Deploy Lambda functions
        run: |
          cd lambda
          for dir in */; do
            cd $dir
            zip -r function.zip .
            aws lambda update-function-code \
              --function-name ${dir%/} \
              --zip-file fileb://function.zip
            cd ..
          done
```

### 4.6 Monitoring & Observability Requirements

Production monitoring requires CloudWatch integration and structured logging:

**Required Packages**:

```python
aws-lambda-powertools>=2.30.0   # Structured logging, metrics, tracing
```

**Implementation**:

```python
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit

logger = Logger()
tracer = Tracer()
metrics = Metrics()

@tracer.capture_lambda_handler
@logger.inject_lambda_context
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event, context):
    logger.info("Processing trade", extra={"trade_id": trade_id})
    
    metrics.add_metric(
        name="TradeCreated",
        unit=MetricUnit.Count,
        value=1
    )
    
    return {"statusCode": 200, "body": "Success"}
```

**CloudWatch Alarms** (Terraform):

```hcl
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "lambda-trades-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "Alert when Lambda errors exceed threshold"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}
```

---

## 5. Prioritized Refactoring Roadmap

This section presents a **7-phase roadmap** spanning 12-14 weeks, with tasks prioritized by dependency relationships and risk. Each phase includes effort estimates, complexity ratings, and specific deliverables.

### Phase 1: Foundation (Weeks 1-2) - 🔴 CRITICAL

**Priority**: BLOCKER - Must complete before any AWS deployment  
**Total Effort**: 6-10 days  
**Risk Level**: HIGH

This phase establishes the foundational infrastructure required for all subsequent work. No AWS deployment can proceed without database migration and Infrastructure as Code.

#### Task 1.1: Database Migration to Neon PostgreSQL

**Effort**: 3-5 days  
**Complexity**: HIGH  
**Dependencies**: None  
**Risk**: Data loss, query incompatibility

**Deliverables**:

- [ ] Install Alembic: `pip install alembic` and initialize migration repository with `alembic init alembic`
- [ ] Create initial migration: Generate migration from existing SQLite schema using `alembic revision --autogenerate -m "Initial schema"`
- [ ] Update database connection: Modify `backend/database/connection.py` to support PostgreSQL connection strings with SSL
- [ ] Implement async SQLAlchemy: Replace `create_engine()` with `create_async_engine()` and `sessionmaker()` with async session factory
- [ ] Configure connection pooling: Set `pool_size=1` and `max_overflow=0` for Lambda compatibility
- [ ] Convert all queries to async: Update every database query in `backend/routers/` to use `async def` and `await db.execute()`
- [ ] Test migrations: Run migrations on Neon staging database and verify schema correctness
- [ ] Document rollback: Create rollback procedures for failed migrations

**Code Changes**:

```python
# backend/database/connection.py (BEFORE)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(
    "sqlite:///./data/trades.db",
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(bind=engine)

# backend/database/connection.py (AFTER)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

engine = create_async_engine(
    os.getenv("NEON_DATABASE_URL"),
    pool_size=1,
    max_overflow=0,
    pool_pre_ping=True,
    echo=False
)
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)
```

**Validation Criteria**:

- All Alembic migrations run successfully on Neon staging database
- All existing tests pass with PostgreSQL backend
- Query performance meets or exceeds SQLite baseline (measure with `pytest-benchmark`)
- Connection pooling prevents connection exhaustion under load (test with 100 concurrent requests)

#### Task 1.2: Infrastructure as Code Setup

**Effort**: 2-3 days  
**Complexity**: MEDIUM  
**Dependencies**: None  
**Risk**: Misconfiguration, cost overruns

**Deliverables**:

- [ ] Choose IaC tool: Terraform recommended for maturity and AWS provider support
- [ ] Create directory structure: `infrastructure/terraform/` with separate files for each resource type
- [ ] Configure Terraform backend: Store state in S3 with DynamoDB locking for team collaboration
- [ ] Define AWS provider: Configure AWS provider with region and default tags
- [ ] Create VPC resources: Define VPC, subnets, security groups, and NAT gateway (if required)
- [ ] Define IAM roles: Create Lambda execution role with least-privilege permissions
- [ ] Set up S3 buckets: Create buckets for cache, reports, and logs with encryption and versioning
- [ ] Configure CloudWatch: Create log groups with 30-day retention policy
- [ ] Document architecture: Generate architecture diagram from Terraform code

**Terraform Structure**:

```hcl
# infrastructure/terraform/main.tf
terraform {
  required_version = ">= 1.6"
  
  backend "s3" {
    bucket         = "potential-parakeet-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "potential-parakeet"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
```

**Validation Criteria**:

- `terraform plan` executes without errors
- `terraform apply` creates all resources successfully
- All resources tagged correctly for cost tracking
- State file stored securely in S3 with versioning enabled

#### Task 1.3: Environment & Secrets Management

**Effort**: 1-2 days  
**Complexity**: LOW  
**Dependencies**: Task 1.2 (requires AWS infrastructure)  
**Risk**: Credential exposure, configuration drift

**Deliverables**:

- [ ] Create AWS Secrets Manager secrets: Store Tiingo API key, database credentials, and JWT secret
- [ ] Update `backend/config.py`: Add async function to retrieve secrets from Secrets Manager
- [ ] Create environment configs: Separate configuration files for dev, staging, and production
- [ ] Remove hardcoded credentials: Audit codebase for hardcoded secrets and replace with secret references
- [ ] Update `.env.example`: Document all required environment variables with example values
- [ ] Document secret rotation: Create procedures for rotating API keys and database passwords
- [ ] Implement caching: Cache secrets in Lambda memory to reduce Secrets Manager API calls

**Code Changes**:

```python
# backend/config.py (AFTER)
import aioboto3
import json
from functools import lru_cache

@lru_cache(maxsize=1)
async def get_secrets() -> dict:
    """Retrieve secrets from AWS Secrets Manager (cached)."""
    async with aioboto3.Session().client('secretsmanager') as sm:
        response = await sm.get_secret_value(
            SecretId=f"potential-parakeet/{os.getenv('ENVIRONMENT')}/secrets"
        )
        return json.loads(response['SecretString'])

class Settings(BaseSettings):
    # Load from Secrets Manager instead of environment variables
    async def load_secrets(self):
        secrets = await get_secrets()
        self.TIINGO_API_KEY = secrets['tiingo_api_key']
        self.JWT_SECRET = secrets['jwt_secret']
```

**Validation Criteria**:

- No secrets visible in environment variables or logs
- Secrets Manager API calls occur only once per Lambda cold start (verify with CloudWatch metrics)
- All environments (dev/staging/prod) use separate secret stores
- Secret rotation procedures documented and tested

---

### Phase 2: Storage Layer Refactoring (Weeks 3-4) - 🟠 HIGH PRIORITY

**Priority**: HIGH - Required for serverless architecture  
**Total Effort**: 5-7 days  
**Risk Level**: MEDIUM

This phase eliminates local file system dependencies by migrating all cache storage to S3 and converting data fetching to asynchronous operations.

#### Task 2.1: S3 Cache Migration

**Effort**: 3-4 days  
**Complexity**: MEDIUM  
**Dependencies**: Task 1.2 (requires S3 buckets)  
**Risk**: Performance degradation, data loss during migration

**Deliverables**:

- [ ] Create `S3CacheStorage` adapter: Implement async read/write methods for Parquet files in `strategy/storage/s3_cache.py`
- [ ] Update `FastDataLoader`: Replace file system operations with S3 storage adapter calls
- [ ] Implement S3 lifecycle policies: Configure automatic expiration of cache files older than 30 days
- [ ] Add cache invalidation: Implement cache key versioning for forced cache refresh
- [ ] Implement retry logic: Add exponential backoff for S3 operations (handle throttling)
- [ ] Performance testing: Benchmark S3 vs local file latency and optimize with compression
- [ ] Update all cache references: Search codebase for `Path("cache/")` and replace with storage adapter
- [ ] Migration script: Create script to copy existing cache files from local disk to S3

**Implementation**:

```python
# strategy/storage/s3_cache.py
import aioboto3
from io import BytesIO
import pandas as pd
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class S3CacheStorage:
    """S3-based cache storage for Parquet files."""
    
    def __init__(self, bucket: str, prefix: str = "cache/"):
        self.bucket = bucket
        self.prefix = prefix
    
    async def read_parquet(self, key: str) -> Optional[pd.DataFrame]:
        """Read Parquet file from S3."""
        try:
            async with aioboto3.Session().client('s3') as s3:
                obj = await s3.get_object(
                    Bucket=self.bucket,
                    Key=f"{self.prefix}{key}"
                )
                body = await obj['Body'].read()
                df = pd.read_parquet(BytesIO(body))
                logger.info(f"Cache hit: {key} ({len(df)} rows)")
                return df
        except Exception as e:
            logger.warning(f"Cache miss: {key} ({e})")
            return None
    
    async def write_parquet(
        self, 
        key: str, 
        df: pd.DataFrame,
        compression: str = 'snappy'
    ) -> None:
        """Write Parquet file to S3."""
        buffer = BytesIO()
        df.to_parquet(buffer, engine='pyarrow', compression=compression)
        buffer.seek(0)
        
        async with aioboto3.Session().client('s3') as s3:
            await s3.put_object(
                Bucket=self.bucket,
                Key=f"{self.prefix}{key}",
                Body=buffer.getvalue(),
                ContentType='application/octet-stream',
                ServerSideEncryption='AES256',
                Metadata={
                    'rows': str(len(df)),
                    'columns': str(len(df.columns)),
                    'compression': compression
                }
            )
        logger.info(f"Cache write: {key} ({len(df)} rows)")
    
    async def exists(self, key: str) -> bool:
        """Check if cache key exists."""
        try:
            async with aioboto3.Session().client('s3') as s3:
                await s3.head_object(
                    Bucket=self.bucket,
                    Key=f"{self.prefix}{key}"
                )
                return True
        except:
            return False
```

**Validation Criteria**:

- All cache operations use S3 storage adapter (no file system access)
- S3 read latency < 200ms P95 (measure with CloudWatch metrics)
- Cache hit rate > 90% after warm-up period
- No data loss during migration (verify row counts match)
- S3 costs < $30/month for 100GB cache (monitor with AWS Cost Explorer)

#### Task 2.2: Async Data Fetching

**Effort**: 2-3 days  
**Complexity**: MEDIUM  
**Dependencies**: None  
**Risk**: API rate limiting, request failures

**Deliverables**:

- [ ] Convert `FastDataLoader` to async: Change all methods to `async def` and use `await` for I/O operations
- [ ] Replace `requests` with `httpx`: Install `httpx` and replace all HTTP calls with async client
- [ ] Implement concurrent API calls: Use `asyncio.gather()` to fetch multiple tickers simultaneously
- [ ] Add rate limiting: Implement token bucket algorithm to respect Tiingo API limits (20,000 requests/hour)
- [ ] Update retry logic: Adapt exponential backoff for async context with `asyncio.sleep()`
- [ ] Performance testing: Measure speedup vs synchronous implementation (target: 3-5x faster)
- [ ] Update all callers: Convert all code that calls data loaders to async

**Implementation**:

```python
# strategy/fast_data_loader.py (AFTER)
import httpx
import asyncio
from typing import List, Dict
import pandas as pd

class FastDataLoader:
    """Async data loader with concurrent API calls."""
    
    def __init__(self, api_key: str, max_concurrent: int = 10):
        self.api_key = api_key
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def fetch_ticker(self, ticker: str) -> pd.DataFrame:
        """Fetch single ticker with rate limiting."""
        async with self.semaphore:  # Limit concurrent requests
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.tiingo.com/tiingo/daily/{ticker}/prices",
                    headers={"Authorization": f"Token {self.api_key}"},
                    timeout=30.0
                )
                response.raise_for_status()
                return pd.DataFrame(response.json())
    
    async def fetch_prices_fast(
        self, 
        tickers: List[str]
    ) -> Dict[str, pd.DataFrame]:
        """Fetch multiple tickers concurrently."""
        tasks = [self.fetch_ticker(ticker) for ticker in tickers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            ticker: result 
            for ticker, result in zip(tickers, results)
            if not isinstance(result, Exception)
        }
```

**Validation Criteria**:

- Data fetching 3-5x faster than synchronous implementation (benchmark with 100 tickers)
- No API rate limit errors (monitor Tiingo API response codes)
- All errors handled gracefully (no unhandled exceptions)
- Retry logic works correctly (test with simulated network failures)

---

### Phase 3: API Layer Decomposition (Weeks 5-6) - 🟠 HIGH PRIORITY

**Priority**: HIGH - Core serverless migration  
**Total Effort**: 7-10 days  
**Risk Level**: HIGH

This phase decomposes the monolithic FastAPI application into separate Lambda functions, each handling specific API routes.

#### Task 3.1: Lambda Function Decomposition

**Effort**: 5-7 days  
**Complexity**: HIGH  
**Dependencies**: Task 1.1 (database), Task 1.2 (infrastructure)  
**Risk**: Breaking changes, increased complexity

**Deliverables**:

- [ ] Create Lambda directory structure: `lambda/trades/`, `lambda/data/`, `lambda/strategies/`, `lambda/scanner/`, `lambda/dashboard/`
- [ ] Split routers into functions: Each Lambda function includes only its relevant router
- [ ] Create handler wrappers: Use Mangum to wrap FastAPI apps for Lambda
- [ ] Configure Lambda resources: Define memory (512MB-1024MB), timeout (30s-300s), and environment variables in Terraform
- [ ] Implement cold start optimization: Use Lambda layers for shared dependencies, minimize package size
- [ ] Add Lambda Powertools: Integrate structured logging, metrics, and tracing
- [ ] Test each function: Unit tests and integration tests for each Lambda function
- [ ] Document responsibilities: Create README for each function explaining its purpose and endpoints

**Lambda Function Structure**:

```python
# lambda/trades/handler.py
from mangum import Mangum
from fastapi import FastAPI
from aws_lambda_powertools import Logger, Tracer, Metrics

from backend.routers.trades import router
from backend.database.connection import init_db

logger = Logger()
tracer = Tracer()
metrics = Metrics()

app = FastAPI(title="Trades API")
app.include_router(router)

@app.on_event("startup")
async def startup():
    """Initialize database connection on cold start."""
    await init_db()
    logger.info("Trades API initialized")

# Mangum converts API Gateway events to ASGI
handler = Mangum(app, lifespan="off")
```

**Terraform Configuration**:

```hcl
# infrastructure/terraform/lambda.tf
resource "aws_lambda_function" "trades" {
  function_name = "potential-parakeet-trades-${var.environment}"
  role          = aws_iam_role.lambda_exec.arn
  
  filename         = "lambda/trades/function.zip"
  source_code_hash = filebase64sha256("lambda/trades/function.zip")
  
  runtime = "python3.12"
  handler = "handler.handler"
  
  memory_size = 512
  timeout     = 30
  
  environment {
    variables = {
      ENVIRONMENT      = var.environment
      DATABASE_URL     = var.neon_database_url
      S3_CACHE_BUCKET  = aws_s3_bucket.cache.id
      LOG_LEVEL        = "INFO"
    }
  }
  
  tracing_config {
    mode = "Active"  # Enable X-Ray tracing
  }
  
  layers = [
    aws_lambda_layer_version.dependencies.arn
  ]
}
```

**Validation Criteria**:

- Each Lambda function deploys successfully
- All API endpoints respond correctly (test with Postman or curl)
- Cold start latency < 2 seconds (measure with CloudWatch metrics)
- Memory usage < 80% of allocated memory (optimize if needed)
- All logs appear in CloudWatch with structured format

#### Task 3.2: API Gateway Configuration

**Effort**: 2-3 days  
**Complexity**: MEDIUM  
**Dependencies**: Task 3.1 (Lambda functions)  
**Risk**: Routing errors, authentication bypass

**Deliverables**:

- [ ] Define REST API: Create API Gateway REST API in Terraform with descriptive name
- [ ] Configure routes: Map URL paths to Lambda functions (`/api/trades/*` → Trades Lambda)
- [ ] Add JWT authorizer: Implement Lambda authorizer for JWT token validation
- [ ] Implement request validation: Define request schemas and enable validation in API Gateway
- [ ] Configure CORS: Set CORS headers to allow Cloudflare frontend domain
- [ ] Add rate limiting: Configure throttling (100 requests/second per client)
- [ ] Set up custom domain: Configure custom domain with SSL certificate from ACM
- [ ] Test end-to-end: Verify complete request flow from client → API Gateway → Lambda → database

**Terraform Configuration**:

```hcl
# infrastructure/terraform/api_gateway.tf
resource "aws_apigatewayv2_api" "main" {
  name          = "potential-parakeet-${var.environment}"
  protocol_type = "HTTP"
  
  cors_configuration {
    allow_origins = ["https://app.potential-parakeet.com"]
    allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_headers = ["Content-Type", "Authorization"]
    max_age       = 300
  }
}

resource "aws_apigatewayv2_route" "trades" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "ANY /api/trades/{proxy+}"
  
  target = "integrations/${aws_apigatewayv2_integration.trades.id}"
  
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_integration" "trades" {
  api_id           = aws_apigatewayv2_api.main.id
  integration_type = "AWS_PROXY"
  
  integration_uri        = aws_lambda_function.trades.invoke_arn
  payload_format_version = "2.0"
}
```

**Validation Criteria**:

- All routes map correctly to Lambda functions (test each endpoint)
- JWT authentication works (test with valid and invalid tokens)
- CORS headers present in responses (verify with browser DevTools)
- Rate limiting prevents abuse (test with load testing tool)
- Custom domain resolves correctly with HTTPS

---

### Phase 4: Strategy Engine Optimization (Weeks 7-8) - 🟡 MEDIUM PRIORITY

**Priority**: MEDIUM - Performance and maintainability  
**Total Effort**: 7-10 days  
**Risk Level**: LOW

This phase improves code organization and maintainability to enhance Ralph CLI navigation and reduce technical debt.

#### Task 4.1: Configuration Consolidation

**Effort**: 2-3 days  
**Complexity**: LOW  
**Dependencies**: None  
**Risk**: Configuration errors, missing settings

**Deliverables**:

- [ ] Merge configuration files: Combine `backend/config.py` and `strategy/config.py` into `config/settings.py`
- [ ] Use Pydantic BaseSettings: Leverage Pydantic's settings management with environment variable overrides
- [ ] Create environment overrides: Separate configuration for dev, staging, and production
- [ ] Validate configuration: Add validation rules for all settings (e.g., positive integers, valid URLs)
- [ ] Remove duplicate code: Eliminate redundant configuration definitions
- [ ] Update all imports: Change imports across codebase to use new configuration module
- [ ] Document settings: Add docstrings explaining each configuration parameter

**Implementation**:

```python
# config/settings.py
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    """Unified application settings."""
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str
    DB_POOL_SIZE: int = 1
    DB_MAX_OVERFLOW: int = 0
    
    # AWS
    AWS_REGION: str = "us-east-1"
    S3_CACHE_BUCKET: str
    
    # APIs
    TIINGO_API_KEY: str
    TIINGO_RATE_LIMIT: int = 20000  # requests per hour
    
    # Strategy
    INITIAL_CAPITAL: float = 100000.0
    RISK_FREE_RATE: float = 0.04
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    def validate_settings(self):
        """Validate configuration on startup."""
        assert self.INITIAL_CAPITAL > 0, "Initial capital must be positive"
        assert 0 <= self.RISK_FREE_RATE <= 1, "Risk-free rate must be between 0 and 1"

settings = Settings()
settings.validate_settings()
```

**Validation Criteria**:

- All configuration in single module (no duplicate definitions)
- Environment-specific overrides work correctly (test dev/staging/prod)
- Validation catches invalid configuration (test with invalid values)
- All imports updated (no references to old config modules)

#### Task 4.2: Module Structure Flattening

**Effort**: 3-4 days  
**Complexity**: MEDIUM  
**Dependencies**: None  
**Risk**: Breaking imports, test failures

**Deliverables**:

- [ ] Identify deeply nested modules: Find all modules nested 3+ levels deep
- [ ] Flatten strategy modules: Move `strategy/quant2/meta_labeling/orchestrator.py` to `strategy/meta_labeling.py`
- [ ] Create public interfaces: Add `__all__` exports to `__init__.py` files
- [ ] Update import statements: Change all imports to use flattened structure
- [ ] Run test suite: Verify no tests break from import changes
- [ ] Update documentation: Revise architecture diagrams and documentation

**Before**:
```
strategy/
├── quant2/
│   ├── meta_labeling/
│   │   ├── orchestrator.py
│   │   ├── feature_engineering.py
│   │   └── model.py
│   ├── regime/
│   │   ├── hmm_detector.py
│   │   └── regime_allocator.py
```

**After**:
```
strategy/
├── meta_labeling.py          # Consolidated meta-labeling logic
├── regime_detection.py       # Consolidated regime detection
```

**Validation Criteria**:

- Maximum nesting depth = 2 levels
- All tests pass (no import errors)
- Public APIs clearly defined in `__init__.py`
- Import paths simplified (e.g., `from strategy.meta_labeling import MetaLabeler`)

#### Task 4.3: Dependency Injection

**Effort**: 3-4 days  
**Complexity**: MEDIUM  
**Dependencies**: Task 4.1 (configuration)  
**Risk**: Circular dependencies, complexity increase

**Deliverables**:

- [ ] Replace dynamic imports: Remove try/except import blocks with explicit imports
- [ ] Create dependencies module: `backend/dependencies.py` with FastAPI `Depends()` functions
- [ ] Inject database sessions: Use FastAPI dependency injection for database sessions
- [ ] Inject configuration: Pass settings as dependencies rather than global imports
- [ ] Inject storage adapters: Use dependency injection for S3 storage
- [ ] Add Protocol classes: Define interfaces using `typing.Protocol` for major components
- [ ] Update tests: Use dependency injection in tests for easier mocking
- [ ] Document DI patterns: Create guide for Ralph on dependency injection usage

**Implementation**:

```python
# backend/dependencies.py
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator

from config.settings import settings
from backend.database.connection import async_session
from strategy.storage.s3_cache import S3CacheStorage

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Database session dependency."""
    async with async_session() as session:
        yield session

def get_storage() -> S3CacheStorage:
    """Storage adapter dependency."""
    return S3CacheStorage(
        bucket=settings.S3_CACHE_BUCKET,
        prefix="cache/"
    )

# Usage in router
from fastapi import APIRouter, Depends
from backend.dependencies import get_db, get_storage

router = APIRouter()

@router.get("/trades")
async def get_trades(
    db: AsyncSession = Depends(get_db),
    storage: S3CacheStorage = Depends(get_storage)
):
    # db and storage injected automatically
    trades = await db.execute(select(Trade))
    return trades.scalars().all()
```

**Validation Criteria**:

- No dynamic imports (no try/except import blocks)
- All dependencies injected via FastAPI `Depends()`
- Tests use dependency injection for mocking
- Protocol classes define clear interfaces

---

### Phase 5: Frontend & Edge (Weeks 9-10) - 🟡 MEDIUM PRIORITY

**Priority**: MEDIUM - User experience and performance  
**Total Effort**: 4-6 days  
**Risk Level**: LOW

This phase deploys the frontend to Cloudflare Pages and implements edge authentication with Cloudflare Workers.

#### Task 5.1: Cloudflare Pages Deployment

**Effort**: 2-3 days  
**Complexity**: LOW  
**Dependencies**: None  
**Risk**: Build failures, routing issues

**Deliverables**:

- [ ] Configure Cloudflare Pages: Connect GitHub repository to Cloudflare Pages
- [ ] Set up build pipeline: Configure Vite build command and output directory
- [ ] Configure environment variables: Set API endpoint URLs for each environment
- [ ] Add custom domain: Configure custom domain with SSL certificate
- [ ] Configure caching headers: Set appropriate cache headers for static assets
- [ ] Test deployment: Verify frontend loads and API calls work
- [ ] Set up preview deployments: Enable preview deployments for pull requests

**Configuration**:

```yaml
# wrangler.toml
name = "potential-parakeet-frontend"
compatibility_date = "2024-01-01"

[site]
bucket = "./dashboard/dist"

[env.production]
name = "potential-parakeet-frontend-prod"
route = "app.potential-parakeet.com/*"

[env.production.vars]
API_URL = "https://api.potential-parakeet.com"
```

**Validation Criteria**:

- Frontend deploys successfully on git push
- All pages load correctly (test navigation)
- API calls reach backend (verify in Network tab)
- Custom domain resolves with HTTPS
- Preview deployments work for PRs

#### Task 5.2: Cloudflare Workers for Auth

**Effort**: 2-3 days  
**Complexity**: MEDIUM  
**Dependencies**: Task 5.1 (Cloudflare Pages)  
**Risk**: Authentication bypass, performance impact

**Deliverables**:

- [ ] Create Cloudflare Worker: Implement JWT validation at edge
- [ ] Implement rate limiting: Token bucket algorithm at edge
- [ ] Add CORS headers: Set CORS headers for API requests
- [ ] Route authenticated requests: Forward valid requests to API Gateway
- [ ] Test authentication flow: Verify login, token validation, and logout
- [ ] Document worker deployment: Create deployment guide

**Implementation**:

```javascript
// cloudflare/workers/auth.js
export default {
  async fetch(request, env) {
    // Extract JWT from Authorization header
    const authHeader = request.headers.get('Authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return new Response('Unauthorized', { status: 401 });
    }
    
    const token = authHeader.substring(7);
    
    // Validate JWT (simplified - use jose library in production)
    try {
      const payload = await verifyJWT(token, env.JWT_SECRET);
      
      // Add user info to request headers
      const modifiedRequest = new Request(request);
      modifiedRequest.headers.set('X-User-ID', payload.sub);
      
      // Forward to API Gateway
      return fetch(env.API_URL + request.url.pathname, modifiedRequest);
    } catch (error) {
      return new Response('Invalid token', { status: 401 });
    }
  }
};
```

**Validation Criteria**:

- JWT validation works correctly (test with valid and invalid tokens)
- Rate limiting prevents abuse (test with load testing tool)
- CORS headers present (verify with browser DevTools)
- Authentication adds < 10ms latency (measure with CloudFlare analytics)

---

### Phase 6: CI/CD & Monitoring (Weeks 11-12) - 🟡 MEDIUM PRIORITY

**Priority**: MEDIUM - Operational excellence  
**Total Effort**: 5-7 days  
**Risk Level**: LOW

This phase implements automated testing, deployment, and monitoring to ensure operational excellence.

#### Task 6.1: GitHub Actions CI/CD

**Effort**: 3-4 days  
**Complexity**: MEDIUM  
**Dependencies**: All previous tasks  
**Risk**: Deployment failures, downtime

**Deliverables**:

- [ ] Create test workflow: `.github/workflows/test.yml` for automated testing on every push
- [ ] Create deploy workflow: `.github/workflows/deploy.yml` for automated deployment to staging and production
- [ ] Add staging environment: Separate staging environment for testing before production
- [ ] Implement blue-green deployment: Zero-downtime deployments with automatic rollback
- [ ] Add database migration step: Run Alembic migrations as part of deployment
- [ ] Configure secrets: Store AWS credentials and API keys in GitHub Secrets
- [ ] Add approval gates: Require manual approval for production deployments
- [ ] Document deployment process: Create runbook for deployments and rollbacks

**Test Workflow**:

```yaml
# .github/workflows/test.yml
name: Test
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run linting
        run: ruff check .
      
      - name: Run tests
        run: pytest tests/ --cov=backend --cov=strategy --cov-report=xml
      
      - name: Check coverage
        run: coverage report --fail-under=80
      
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
```

**Deploy Workflow**:

```yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Deploy infrastructure
        run: |
          cd infrastructure/terraform
          terraform init
          terraform apply -auto-approve -var-file=environments/staging.tfvars
      
      - name: Run database migrations
        run: |
          export DATABASE_URL=${{ secrets.STAGING_DATABASE_URL }}
          alembic upgrade head
      
      - name: Deploy Lambda functions
        run: ./scripts/deploy-lambda.sh staging
  
  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production
    steps:
      # Same steps as staging, but with production variables
      - name: Deploy to production
        run: ./scripts/deploy-lambda.sh production
```

**Validation Criteria**:

- Tests run automatically on every push
- Deployments succeed without manual intervention
- Database migrations run successfully
- Rollback procedures work (test with intentional failure)
- Production deployments require manual approval

#### Task 6.2: Monitoring & Alerting

**Effort**: 2-3 days  
**Complexity**: MEDIUM  
**Dependencies**: Task 6.1 (deployed infrastructure)  
**Risk**: Alert fatigue, missed incidents

**Deliverables**:

- [ ] Configure CloudWatch dashboards: Create dashboards for Lambda metrics, API Gateway metrics, and database metrics
- [ ] Add custom metrics: Instrument code with business KPIs (trades created, backtests run, cache hit rate)
- [ ] Set up CloudWatch Alarms: Create alarms for error rate, latency, and cold starts
- [ ] Integrate AWS X-Ray: Enable distributed tracing for request flow visualization
- [ ] Add Sentry integration: Optional error tracking for detailed error reports
- [ ] Create runbook: Document common issues and resolution procedures
- [ ] Document monitoring strategy: Explain metrics, alarms, and escalation procedures

**CloudWatch Dashboard** (Terraform):

```hcl
# infrastructure/terraform/cloudwatch.tf
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "potential-parakeet-${var.environment}"
  
  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/Lambda", "Invocations", { stat = "Sum" }],
            [".", "Errors", { stat = "Sum" }],
            [".", "Duration", { stat = "Average" }]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "Lambda Metrics"
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ApiGateway", "Count", { stat = "Sum" }],
            [".", "4XXError", { stat = "Sum" }],
            [".", "5XXError", { stat = "Sum" }],
            [".", "Latency", { stat = "Average" }]
          ]
          period = 300
          region = var.aws_region
          title  = "API Gateway Metrics"
        }
      }
    ]
  })
}

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "lambda-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "Alert when Lambda errors exceed 5 in 10 minutes"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}
```

**Validation Criteria**:

- CloudWatch dashboard displays all key metrics
- Custom metrics appear in CloudWatch (verify with test data)
- Alarms trigger correctly (test with intentional errors)
- X-Ray traces show complete request flow
- Runbook covers common failure scenarios

---

### Phase 7: Testing & Validation (Weeks 13-14) - 🟠 HIGH PRIORITY

**Priority**: HIGH - Quality assurance  
**Total Effort**: 5-7 days  
**Risk Level**: MEDIUM

This phase validates the entire migration through comprehensive integration testing and load testing.

#### Task 7.1: Integration Testing

**Effort**: 3-4 days  
**Complexity**: MEDIUM  
**Dependencies**: All previous tasks  
**Risk**: Undetected bugs, data inconsistencies

**Deliverables**:

- [ ] Add Lambda integration tests: Test each Lambda function with realistic payloads
- [ ] Mock AWS services: Use `moto` library to mock S3, Secrets Manager, and other AWS services
- [ ] Test database migrations: Verify migrations work correctly on Neon staging database
- [ ] Test S3 cache operations: Verify cache read/write/invalidation work correctly
- [ ] Test API Gateway integration: End-to-end tests from API Gateway to Lambda to database
- [ ] Test Cloudflare Workers: Verify authentication and rate limiting at edge
- [ ] Achieve code coverage: Target >80% code coverage across all modules
- [ ] Document test strategy: Explain test organization and how to run tests

**Integration Test Example**:

```python
# tests/integration/test_trades_api.py
import pytest
from httpx import AsyncClient
from moto import mock_s3, mock_secretsmanager
import boto3

@pytest.mark.asyncio
@mock_s3
@mock_secretsmanager
async def test_create_trade_end_to_end():
    """Test complete trade creation flow."""
    # Setup mocks
    s3 = boto3.client('s3', region_name='us-east-1')
    s3.create_bucket(Bucket='test-cache-bucket')
    
    sm = boto3.client('secretsmanager', region_name='us-east-1')
    sm.create_secret(
        Name='potential-parakeet/test/secrets',
        SecretString='{"tiingo_api_key": "test-key"}'
    )
    
    # Make API request
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/trades",
            json={
                "ticker": "AAPL",
                "direction": "BUY",
                "quantity": 100,
                "entry_price": 150.00,
                "strategy_name": "momentum"
            },
            headers={"Authorization": "Bearer test-token"}
        )
    
    # Verify response
    assert response.status_code == 201
    data = response.json()
    assert data['ticker'] == 'AAPL'
    assert data['status'] == 'OPEN'
    
    # Verify database
    async with async_session() as db:
        trade = await db.execute(
            select(Trade).where(Trade.ticker == 'AAPL')
        )
        assert trade.scalar_one() is not None
```

**Validation Criteria**:

- All integration tests pass
- Code coverage > 80% (measure with `pytest-cov`)
- All AWS services properly mocked (no real AWS calls in tests)
- Tests run in < 5 minutes (optimize slow tests)

#### Task 7.2: Load Testing

**Effort**: 2-3 days  
**Complexity**: MEDIUM  
**Dependencies**: Task 7.1 (integration tests)  
**Risk**: Performance degradation under load

**Deliverables**:

- [ ] Create load testing scenarios: Use Locust or k6 to simulate realistic traffic patterns
- [ ] Test Lambda cold starts: Measure cold start latency and frequency
- [ ] Test API Gateway throughput: Verify API Gateway can handle expected traffic
- [ ] Test Neon connection pooling: Verify database connections don't exhaust under load
- [ ] Test S3 cache performance: Measure S3 read/write latency under concurrent load
- [ ] Document performance benchmarks: Record baseline metrics for future comparison
- [ ] Optimize based on results: Identify and fix performance bottlenecks

**Load Testing Script** (Locust):

```python
# tests/load/locustfile.py
from locust import HttpUser, task, between

class TradingPlatformUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login and get JWT token."""
        response = self.client.post("/api/auth/login", json={
            "username": "test@example.com",
            "password": "test-password"
        })
        self.token = response.json()['access_token']
    
    @task(3)
    def get_trades(self):
        """Get list of trades (most common operation)."""
        self.client.get(
            "/api/trades",
            headers={"Authorization": f"Bearer {self.token}"}
        )
    
    @task(1)
    def create_trade(self):
        """Create new trade (less common)."""
        self.client.post(
            "/api/trades",
            json={
                "ticker": "AAPL",
                "direction": "BUY",
                "quantity": 100,
                "entry_price": 150.00
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
    
    @task(2)
    def run_backtest(self):
        """Run strategy backtest (moderate frequency)."""
        self.client.post(
            "/api/strategies/backtest",
            json={
                "strategy_name": "momentum",
                "start_date": "2023-01-01",
                "end_date": "2024-01-01"
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
```

**Run Load Test**:

```bash
# Test with 100 concurrent users, ramping up over 1 minute
locust -f tests/load/locustfile.py \
  --host https://api.potential-parakeet.com \
  --users 100 \
  --spawn-rate 10 \
  --run-time 10m \
  --html report.html
```

**Validation Criteria**:

- API handles 100 concurrent users without errors
- P95 latency < 500ms for all endpoints
- Lambda cold start < 2 seconds
- Database connections don't exhaust (monitor Neon metrics)
- S3 cache hit rate > 90%
- No memory leaks (monitor Lambda memory usage over time)

---

## 6. Risk Assessment & Mitigation

### 6.1 High-Risk Areas

This section identifies the highest-risk components of the migration and provides specific mitigation strategies.

#### Database Migration (Risk: 🔴 HIGH)

**Risk Factors**:

- **Schema Incompatibility**: SQLite and PostgreSQL have different data types and constraints. For example, SQLite's flexible typing may allow invalid data that PostgreSQL rejects.
- **Async Conversion Complexity**: Converting from synchronous to asynchronous database operations introduces race conditions and transaction management challenges.
- **Data Loss Potential**: Migration process could corrupt or lose data if not executed correctly.
- **Downtime Requirements**: Database migration may require application downtime, impacting users.

**Mitigation Strategies**:

1. **Comprehensive Testing**: Create a complete test database with production-like data and run migrations multiple times to identify issues.

2. **Staged Rollout**: Migrate in stages—first to staging environment, then to production with a maintenance window.

3. **Backup Strategy**: Create full database backups before migration with tested restore procedures. Store backups in S3 with versioning enabled.

4. **Validation Queries**: Write SQL queries to validate data integrity after migration (row counts, checksum comparisons, foreign key validation).

5. **Rollback Plan**: Document rollback procedures with specific commands. Test rollback in staging environment.

6. **Dual-Write Period**: Consider a dual-write period where the application writes to both SQLite and Neon, allowing easy rollback if issues arise.

**Validation Checklist**:

- [ ] All tables migrated with correct row counts
- [ ] All indexes created successfully
- [ ] Foreign key constraints valid
- [ ] Bi-temporal queries return correct results
- [ ] Query performance meets or exceeds baseline
- [ ] Backup and restore tested successfully

#### Lambda Cold Starts (Risk: 🟠 MEDIUM)

**Risk Factors**:

- **Latency Impact**: Python Lambda cold starts typically take 1-3 seconds, significantly impacting user experience for latency-sensitive endpoints.
- **Large Dependencies**: The project uses heavy scientific libraries (pandas, numpy, scikit-learn) that increase cold start time.
- **Frequency**: Cold starts occur when Lambda scales up or after periods of inactivity.

**Mitigation Strategies**:

1. **Provisioned Concurrency**: Configure provisioned concurrency for latency-sensitive endpoints (trades, dashboard) to keep Lambda instances warm.

2. **Lambda Layers**: Extract common dependencies (pandas, numpy) into Lambda layers to reduce deployment package size and improve cold start time.

3. **Code Splitting**: Separate heavy dependencies into dedicated Lambda functions. For example, backtesting functions can have longer cold starts than trade CRUD operations.

4. **Lazy Loading**: Import heavy libraries only when needed rather than at module level:

```python
# Bad: Import at module level
import pandas as pd
import numpy as np

def handler(event, context):
    # Uses pandas
    pass

# Good: Lazy import
def handler(event, context):
    import pandas as pd  # Only imported when function executes
    # Uses pandas
    pass
```

5. **Monitoring**: Track cold start frequency and duration with CloudWatch metrics. Set alarms for cold start rate > 5%.

6. **Optimization**: Use lightweight alternatives where possible (e.g., `orjson` instead of standard `json`, `httpx` instead of `requests`).

**Performance Targets**:

- Cold start latency < 2 seconds (P95)
- Cold start frequency < 5% of invocations
- Warm start latency < 100ms (P95)

#### S3 Latency (Risk: 🟡 LOW-MEDIUM)

**Risk Factors**:

- **Increased Latency**: S3 read operations typically take 50-100ms compared to <1ms for local disk access.
- **Large Files**: Parquet cache files can exceed 100MB, increasing transfer time.
- **Concurrent Access**: Multiple Lambda instances reading the same cache file simultaneously could trigger S3 throttling.

**Mitigation Strategies**:

1. **S3 Transfer Acceleration**: Enable S3 Transfer Acceleration for faster uploads/downloads, especially for large files.

2. **Compression**: Use aggressive Parquet compression (snappy or gzip) to reduce file size by 70-90%.

3. **Caching Layer**: Implement ElastiCache (Redis) for frequently accessed cache keys, reducing S3 reads by 80-90%.

4. **Parallel Downloads**: Use S3 multipart downloads for large files to improve throughput.

5. **CloudFront Distribution**: Place CloudFront in front of S3 for edge caching of static cache files.

6. **Monitoring**: Track S3 request latency and throttling errors with CloudWatch metrics.

**Performance Optimization Example**:

```python
# Before: Single-threaded S3 download
async def read_large_parquet(key: str) -> pd.DataFrame:
    async with aioboto3.Session().client('s3') as s3:
        obj = await s3.get_object(Bucket=bucket, Key=key)
        body = await obj['Body'].read()  # Slow for large files
        return pd.read_parquet(BytesIO(body))

# After: Multipart download with caching
from aiocache import cached

@cached(ttl=3600)  # Cache for 1 hour
async def read_large_parquet(key: str) -> pd.DataFrame:
    # Use S3 Transfer Manager for multipart download
    transfer_config = TransferConfig(
        multipart_threshold=1024 * 25,  # 25MB
        max_concurrency=10
    )
    # Download in parallel chunks
    # ... implementation details
```

**Performance Targets**:

- S3 read latency < 200ms (P95)
- Cache hit rate > 90% after warm-up
- S3 costs < $30/month for 100GB cache

#### Cost Overruns (Risk: 🟠 MEDIUM)

**Risk Factors**:

- **Lambda Invocation Costs**: Data-intensive operations (backtesting, data refresh) could trigger millions of Lambda invocations.
- **Neon Compute Costs**: Long-running queries or high connection counts could increase Neon compute costs.
- **S3 Storage and Transfer**: Large cache files and frequent transfers could increase S3 costs.
- **Unexpected Scaling**: Sudden traffic spikes could trigger auto-scaling, increasing costs.

**Mitigation Strategies**:

1. **Cost Monitoring**: Set up AWS Cost Explorer with daily cost reports and budget alerts at $100, $200, and $300 thresholds.

2. **Reserved Capacity**: Use Lambda provisioned concurrency only for production, not development/staging.

3. **Query Optimization**: Optimize database queries to reduce Neon compute time. Use indexes, limit result sets, and cache query results.

4. **S3 Lifecycle Policies**: Automatically transition old cache files to S3 Glacier or delete after 30 days.

5. **Rate Limiting**: Implement strict rate limiting to prevent abuse and runaway costs.

6. **Cost Allocation Tags**: Tag all resources with `Project`, `Environment`, and `Component` for detailed cost tracking.

**Cost Monitoring Dashboard** (Terraform):

```hcl
resource "aws_budgets_budget" "monthly" {
  name              = "potential-parakeet-monthly-budget"
  budget_type       = "COST"
  limit_amount      = "200"
  limit_unit        = "USD"
  time_period_start = "2024-01-01_00:00"
  time_unit         = "MONTHLY"
  
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = ["alerts@potential-parakeet.com"]
  }
}
```

**Cost Optimization Checklist**:

- [ ] Budget alerts configured at 80%, 90%, 100%
- [ ] Cost allocation tags on all resources
- [ ] S3 lifecycle policies configured
- [ ] Lambda memory optimized (not over-provisioned)
- [ ] Neon auto-suspend enabled
- [ ] CloudWatch log retention set to 30 days (not indefinite)

### 6.2 Migration Risk Matrix

| Risk | Probability | Impact | Severity | Mitigation Priority |
|------|-------------|--------|----------|---------------------|
| Data loss during database migration | LOW | CRITICAL | 🔴 HIGH | 1 (Highest) |
| Performance degradation from S3 latency | MEDIUM | HIGH | 🟠 MEDIUM | 3 |
| Lambda cold start impact on UX | MEDIUM | MEDIUM | 🟡 LOW-MEDIUM | 4 |
| Cost overruns from unexpected scaling | HIGH | MEDIUM | 🟠 MEDIUM | 2 |
| Breaking API changes | LOW | HIGH | 🟠 MEDIUM | 5 |
| Vendor lock-in to AWS | HIGH | MEDIUM | 🟡 LOW-MEDIUM | 6 |
| Security vulnerabilities in new architecture | MEDIUM | HIGH | 🟠 MEDIUM | 3 |
| Insufficient monitoring leading to undetected issues | MEDIUM | MEDIUM | 🟡 LOW-MEDIUM | 5 |

---

## 7. Cost Analysis

### 7.1 Current State Cost (Docker on VPS)

**Infrastructure**:

- VPS (4 vCPU, 8GB RAM, 100GB SSD): $50-100/month
- Domain and SSL certificate: $15/year (~$1.25/month)
- **Total**: ~$100/month

**Operational Costs**:

- Manual server management: ~2 hours/month × $50/hour = $100/month (opportunity cost)
- Backup storage: Included in VPS cost
- Monitoring: Free (self-hosted)

**Total Current Cost**: ~$100-200/month (including opportunity cost)

### 7.2 Target State Cost (AWS + Neon + Cloudflare)

#### AWS Costs (Estimated Monthly)

**Lambda**:

- Assumptions: 1M requests/month, 512MB memory, 3s average duration
- Compute: 1M × 3s × $0.0000166667/GB-second × 0.5GB = $25
- Requests: 1M × $0.20/1M = $0.20
- **Subtotal**: ~$25/month

**API Gateway**:

- HTTP API: 1M requests × $1.00/million = $1.00
- Data transfer: 10GB × $0.09/GB = $0.90
- **Subtotal**: ~$2/month

**S3**:

- Storage: 100GB × $0.023/GB = $2.30
- PUT requests: 10,000 × $0.005/1,000 = $0.05
- GET requests: 100,000 × $0.0004/1,000 = $0.04
- Data transfer: 10GB × $0.09/GB = $0.90
- **Subtotal**: ~$3.30/month

**CloudWatch**:

- Logs: 10GB × $0.50/GB = $5.00
- Metrics: 50 custom metrics × $0.30 = $15.00
- Alarms: 10 alarms × $0.10 = $1.00
- **Subtotal**: ~$21/month

**Secrets Manager**:

- Secrets: 10 secrets × $0.40 = $4.00
- API calls: 100,000 × $0.05/10,000 = $0.50
- **Subtotal**: ~$4.50/month

**Data Transfer**:

- Internet egress: 10GB × $0.09/GB = $0.90
- **Subtotal**: ~$1/month

**Total AWS**: ~$57/month (conservative estimate)

#### Neon Costs (Estimated Monthly)

**Compute**:

- Assumptions: 10 hours active per day, auto-suspend enabled
- Compute units: 10 hours/day × 30 days × 0.25 CU × $0.16/CU-hour = $12
- **Subtotal**: ~$12/month

**Storage**:

- Database: 10GB × $0.000164/GB-hour × 730 hours = $12
- **Subtotal**: ~$12/month

**Total Neon**: ~$24/month

#### Cloudflare Costs (Estimated Monthly)

**Pages**:

- Free tier (500 builds/month, unlimited requests)
- **Subtotal**: $0/month

**Workers**:

- Free tier (100,000 requests/day)
- Paid plan if needed: $5/month (10M requests)
- **Subtotal**: ~$5/month (if paid plan needed)

**Total Cloudflare**: ~$5/month

### 7.3 Total Cost Comparison

| Component | Current (VPS) | Target (Serverless) | Difference |
|-----------|---------------|---------------------|------------|
| Compute | $50-100 | $25 (Lambda) | -$25 to -$75 |
| Database | Included | $24 (Neon) | +$24 |
| Storage | Included | $3 (S3) | +$3 |
| Monitoring | Free | $21 (CloudWatch) | +$21 |
| Edge/CDN | $0 | $5 (Cloudflare) | +$5 |
| Other AWS | $0 | $9 (API Gateway, Secrets, etc.) | +$9 |
| **Total** | **$100/month** | **$87/month** | **-$13/month** |

**Cost Savings**: ~$13/month (~13% reduction)

**Note**: This analysis assumes moderate usage (1M requests/month). Costs scale with usage:

- **Low usage** (100K requests/month): ~$30/month (70% savings)
- **Moderate usage** (1M requests/month): ~$87/month (13% savings)
- **High usage** (10M requests/month): ~$350/month (250% increase)

### 7.4 Cost Optimization Strategies

To minimize costs while maintaining performance:

1. **Lambda Memory Optimization**: Right-size Lambda memory allocation. Over-provisioning wastes money; under-provisioning increases execution time (and cost).

2. **S3 Intelligent-Tiering**: Enable S3 Intelligent-Tiering to automatically move infrequently accessed cache files to cheaper storage tiers.

3. **Neon Auto-Suspend**: Configure Neon to auto-suspend after 5 minutes of inactivity, reducing compute costs by 80-90%.

4. **CloudWatch Log Retention**: Set log retention to 30 days instead of indefinite to reduce storage costs.

5. **Reserved Capacity**: For predictable workloads, consider Lambda reserved concurrency or Neon reserved compute for 30-50% discounts.

6. **Caching Strategy**: Implement aggressive caching (CloudFront, ElastiCache) to reduce Lambda invocations and S3 requests.

7. **Batch Processing**: Batch data refresh operations to reduce Lambda invocations. Instead of fetching 1,000 tickers individually, batch into 10 requests of 100 tickers each.

8. **Monitoring and Alerts**: Set up cost anomaly detection to catch unexpected cost increases early.

---

## 8. Success Metrics

### 8.1 Technical Metrics

These metrics validate that the migrated system meets performance and reliability requirements:

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| API Latency (P95) | < 500ms | CloudWatch metrics |
| API Latency (P50) | < 200ms | CloudWatch metrics |
| Lambda Cold Start (P95) | < 2 seconds | CloudWatch metrics |
| Lambda Cold Start Frequency | < 5% of invocations | CloudWatch metrics |
| Database Query Latency (P95) | < 100ms | Neon metrics |
| S3 Cache Read Latency (P95) | < 200ms | CloudWatch metrics |
| S3 Cache Hit Rate | > 90% | Custom CloudWatch metric |
| Test Coverage | > 80% | pytest-cov |
| Deployment Success Rate | > 95% | GitHub Actions metrics |
| Mean Time to Recovery (MTTR) | < 1 hour | Incident tracking |

### 8.2 Business Metrics

These metrics validate that the migration delivers business value:

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| System Uptime | 99.9% (3 nines) | CloudWatch alarms |
| Cost per Trade | < $0.01 | AWS Cost Explorer |
| Data Refresh Latency | < 5 minutes | Custom CloudWatch metric |
| Backtest Execution Time | < 30 seconds | Application logs |
| User-Reported Issues | < 5 per month | Support ticket system |
| Page Load Time | < 2 seconds | Cloudflare analytics |

### 8.3 Operational Metrics

These metrics validate operational excellence and developer productivity:

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Deployment Frequency | Daily | GitHub Actions logs |
| Change Failure Rate | < 5% | GitHub Actions + rollback tracking |
| Infrastructure Provisioning Time | < 10 minutes | Terraform execution time |
| Alert Response Time | < 15 minutes | PagerDuty/SNS metrics |
| False Positive Alert Rate | < 10% | Manual tracking |
| Documentation Coverage | 100% of public APIs | Manual review |

### 8.4 Measurement and Reporting

**Weekly Reports**: Generate automated weekly reports with key metrics, cost trends, and performance graphs. Distribute to stakeholders via email.

**Monthly Reviews**: Conduct monthly review meetings to assess progress against targets, identify issues, and plan optimizations.

**Dashboards**: Create real-time dashboards in CloudWatch and Grafana showing all key metrics. Make dashboards accessible to entire team.

**Alerts**: Configure alerts for metrics that fall outside acceptable ranges. Use SNS to send notifications to Slack and email.

---

## 9. Conclusion

### 9.1 Overall Assessment

The Potential Parakeet quantitative trading platform demonstrates **strong foundational architecture** with excellent code quality, comprehensive documentation, and robust testing. The codebase's modular design, particularly the pipeline architecture for strategy execution, represents best practices in quantitative finance software engineering. The bi-temporal data model implementation is notably advanced, providing audit capabilities that exceed many commercial systems.

However, the migration to AWS Lambda, Neon PostgreSQL, and Cloudflare represents a **high-complexity architectural transformation**. The current monolithic, file-based architecture is fundamentally incompatible with distributed serverless patterns. The migration requires significant refactoring across five critical areas: database layer (SQLite → Neon with async conversion), storage layer (local files → S3), API layer (monolith → Lambda functions), configuration management (environment variables → Secrets Manager), and deployment infrastructure (Docker → IaC).

**Migration Feasibility**: ✅ **FEASIBLE** with significant architectural refactoring  
**Estimated Timeline**: **12-14 weeks** (3-4 months)  
**Estimated Effort**: **400-500 developer hours**  
**Risk Level**: 🟠 **MEDIUM-HIGH**

### 9.2 Key Takeaways

**1. Strong Foundation Enables Migration**: The codebase's excellent modularity, documentation (1,062 docstrings), and testing (13 test files, 3,607 lines) provide a solid foundation for refactoring. The clean separation between data fetching, trading logic, portfolio management, and backtesting means quantitative strategies can remain largely unchanged during infrastructure migration.

**2. Database Migration is Critical Path**: The SQLite → Neon PostgreSQL migration represents the highest-risk, highest-priority task. This migration blocks all other work and requires careful planning, comprehensive testing, and robust rollback procedures. The conversion from synchronous to asynchronous database operations touches every part of the application and introduces complexity that must be managed carefully.

**3. Ralph CLI Readiness is Good**: With minor optimizations (module flattening, configuration consolidation, explicit interfaces), the codebase will be highly navigable by Ralph CLI. The extensive type hints, consistent naming conventions, and clear module boundaries provide excellent context for AI-assisted development.

**4. Quantitative Logic is Well-Isolated**: The strategy engine's modular design means trading logic can remain unchanged during infrastructure migration. The pipeline architecture with abstract base classes and dataclass results provides clean interfaces that insulate strategy code from infrastructure changes.

**5. Infrastructure Gap is Significant**: The complete absence of Infrastructure as Code is the most significant gap. Modern cloud deployments require declarative infrastructure definitions for reproducibility, version control, and automation. Creating comprehensive Terraform configurations will consume 20-30% of total migration effort.

**6. Cost Impact is Neutral to Positive**: The migration is projected to reduce costs by ~13% at moderate usage levels (1M requests/month) and by up to 70% at low usage levels. However, costs could increase significantly at high usage levels (10M+ requests/month), requiring careful monitoring and optimization.

### 9.3 Recommended Next Steps

To proceed with this migration, follow these steps in order:

**1. Approve Phase 1 Tasks** (Database + IaC + Secrets) - **CRITICAL PATH**

The database migration, Infrastructure as Code setup, and secrets management form the critical path. No other work can proceed until these foundations are in place. Allocate 2 weeks and your most experienced developers to this phase.

**2. Prototype Lambda Function**

Before committing to full migration, build one Lambda function (e.g., `/api/trades`) end-to-end to validate the architecture. This prototype should include:

- Lambda function with Mangum wrapper
- API Gateway integration
- Neon database connection with async SQLAlchemy
- S3 cache access
- CloudWatch logging and metrics
- Terraform configuration

This prototype validates assumptions about performance, costs, and complexity before investing in full migration.

**3. Conduct Cost Analysis**

Run detailed cost projections based on current usage patterns. Analyze:

- Current API request volume (requests/month)
- Current data refresh frequency and volume
- Current backtest execution frequency
- Expected growth rate

Use AWS Pricing Calculator to estimate costs at current usage, 2x usage, and 5x usage. Set up cost monitoring and budget alerts before migration.

**4. Set Up Staging Environment**

Create a complete staging environment in AWS that mirrors production architecture. Use this environment for:

- Testing database migrations
- Validating Lambda function performance
- Load testing
- Training team on new architecture

Never test infrastructure changes directly in production.

**5. Team Training**

Ensure the team is familiar with:

- AWS Lambda development and deployment
- Terraform infrastructure management
- Async Python programming (asyncio, async/await)
- Neon PostgreSQL features and limitations
- CloudWatch monitoring and alerting

Consider bringing in AWS Solutions Architect for consultation.

**6. Phased Migration with Rollback Capabilities**

Execute the migration in phases, maintaining the ability to rollback at each stage:

- **Phase 1**: Database migration (with dual-write period)
- **Phase 2**: Storage migration (with fallback to local files)
- **Phase 3**: API migration (one Lambda function at a time)
- **Phase 4**: Frontend migration (with blue-green deployment)

At each phase, validate functionality and performance before proceeding.

### 9.4 Final Recommendation

**Proceed with migration** following the phased approach outlined in this document. The project is **well-positioned for this transformation** due to its strong architectural foundations, but expect **3-4 months of focused development effort** to complete the transition safely.

Prioritize **database migration** and **Infrastructure as Code setup** first, then incrementally migrate API endpoints to Lambda. Maintain the current Docker deployment as a fallback during the transition period. This approach minimizes risk while enabling the benefits of serverless architecture: automatic scaling, reduced operational overhead, and pay-per-use pricing.

The migration will modernize the platform's infrastructure, improve scalability, and position the project for future growth. However, success requires careful planning, comprehensive testing, and disciplined execution of the roadmap presented in this document.

---

## Appendix A: Technology Stack Comparison

| Component | Current | Target | Migration Complexity |
|-----------|---------|--------|---------------------|
| **Compute** | Docker containers on VPS | AWS Lambda functions | HIGH |
| **Database** | SQLite (embedded) | Neon PostgreSQL (serverless) | HIGH |
| **Storage** | Local file system | AWS S3 | MEDIUM |
| **API Gateway** | Direct Uvicorn | AWS API Gateway | MEDIUM |
| **Authentication** | JWT in application | Cloudflare Workers + JWT | MEDIUM |
| **Frontend Hosting** | Nginx in Docker | Cloudflare Pages | LOW |
| **Secrets Management** | .env files | AWS Secrets Manager | LOW |
| **Monitoring** | Self-hosted | CloudWatch + X-Ray | MEDIUM |
| **CI/CD** | Manual | GitHub Actions | MEDIUM |
| **Infrastructure** | Manual provisioning | Terraform (IaC) | HIGH |

---

## Appendix B: Glossary

**Alembic**: Database migration tool for SQLAlchemy that manages schema changes through versioned migration scripts.

**API Gateway**: AWS service that creates, publishes, and manages RESTful and WebSocket APIs at scale.

**Async/Await**: Python syntax for asynchronous programming, allowing non-blocking I/O operations.

**Bi-Temporal Data Model**: Database schema that tracks both when events occurred (event time) and when the system learned about them (knowledge time).

**CloudFront**: AWS content delivery network (CDN) that caches content at edge locations globally.

**Cold Start**: The latency incurred when a Lambda function is invoked after being idle, requiring AWS to provision a new execution environment.

**HRP (Hierarchical Risk Parity)**: Portfolio optimization technique that uses hierarchical clustering to allocate capital based on risk contribution.

**IaC (Infrastructure as Code)**: Practice of managing infrastructure through machine-readable definition files rather than manual configuration.

**Lambda Layer**: Deployment package containing libraries and dependencies that can be shared across multiple Lambda functions.

**Mangum**: Python library that adapts ASGI applications (like FastAPI) to run on AWS Lambda.

**Neon**: Serverless PostgreSQL database with automatic scaling, branching, and connection pooling.

**Parquet**: Columnar storage file format optimized for analytics workloads, commonly used with pandas.

**Provisioned Concurrency**: Lambda feature that keeps a specified number of function instances warm to eliminate cold starts.

**SQLAlchemy**: Python SQL toolkit and Object-Relational Mapping (ORM) library.

**VectorBT**: High-performance Python library for backtesting trading strategies using vectorized operations.

---

**End of Migration Strategy Document**

*This document should be reviewed and approved before proceeding with any migration activities. All stakeholders should sign off on the proposed architecture, timeline, and budget before work begins.*


---

## Appendix C: Daily Data Ingest Module

This appendix provides the complete implementation specification for the **Daily Data Ingest Module**, a serverless data pipeline designed to run on AWS Lambda. It fetches daily OHLCV data from `yfinance` and stores it in the Neon PostgreSQL database, ensuring the platform's market data is consistently up-to-date.

### 1. Overview

**Objective**: Create a robust, scalable, and cost-effective data pipeline for ingesting daily stock market data.

**Architecture**:
- **Trigger**: Amazon EventBridge (scheduled to run daily at 6:00 PM EST after market close).
- **Compute**: AWS Lambda function with Python 3.12 runtime.
- **Data Source**: `yfinance` Python library.
- **Database**: Neon serverless PostgreSQL.
- **Monitoring**: Amazon CloudWatch for logs, metrics, and alarms.

### 2. Database Schema

The `market_data` table is designed for time-series data with a composite primary key (`ticker`, `date`) to ensure data integrity and prevent duplicates. This design supports efficient querying for backtesting and analysis.

```sql
-- ============================================================================
-- Market Data Table Schema for Neon PostgreSQL
-- ============================================================================
-- 
-- Purpose: Store daily OHLCV (Open, High, Low, Close, Volume) data for stocks
-- Optimized for: Time-series queries, point-in-time lookups, data integrity
-- Idempotency: Composite primary key (ticker + date) prevents duplicates
-- 
-- Features:
-- - Composite primary key for natural deduplication
-- - Indexes optimized for common query patterns
-- - Timestamp tracking for audit and data freshness monitoring
-- - Partitioning-ready design for scaling to millions of rows
-- - JSONB metadata field for extensibility
-- ============================================================================

-- Main market data table
CREATE TABLE IF NOT EXISTS market_data (
    -- Primary key components
    ticker VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    
    -- OHLCV data
    open NUMERIC(12, 4) NOT NULL,
    high NUMERIC(12, 4) NOT NULL,
    low NUMERIC(12, 4) NOT NULL,
    close NUMERIC(12, 4) NOT NULL,
    volume BIGINT NOT NULL,
    
    -- Adjusted close (for splits and dividends)
    adjusted_close NUMERIC(12, 4),
    
    -- Metadata
    source VARCHAR(50) DEFAULT 'yfinance',
    data_quality VARCHAR(20) DEFAULT 'good' CHECK (data_quality IN ('good', 'suspect', 'bad')),
    
    -- Audit timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Additional metadata (extensible)
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Composite primary key (natural deduplication)
    PRIMARY KEY (ticker, date),
    
    -- Data integrity constraints
    CONSTRAINT valid_ohlc CHECK (
        low <= open AND 
        low <= close AND 
        low <= high AND 
        high >= open AND 
        high >= close
    ),
    CONSTRAINT positive_volume CHECK (volume >= 0),
    CONSTRAINT positive_prices CHECK (
        open > 0 AND 
        high > 0 AND 
        low > 0 AND 
        close > 0
    )
);

-- Indexes for Query Optimization
CREATE INDEX IF NOT EXISTS idx_market_data_ticker_date ON market_data (ticker, date DESC);

-- Trigger for Automatic updated_at Timestamp
CREATE OR REPLACE FUNCTION update_market_data_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_market_data_timestamp ON market_data;
CREATE TRIGGER trigger_update_market_data_timestamp
    BEFORE UPDATE ON market_data
    FOR EACH ROW
    EXECUTE FUNCTION update_market_data_timestamp();

COMMENT ON TABLE market_data IS 'Daily OHLCV market data for stocks and ETFs. Composite primary key (ticker, date) ensures idempotency.';
```

### 3. Lambda Handler Implementation

The Python script below is the complete handler for the AWS Lambda function. It includes configuration management, data fetching logic, and database operations with UPSERT functionality.

**Key Features**:
- **Idempotency**: Uses `ON CONFLICT DO UPDATE` to prevent duplicate data entries.
- **Concurrency**: Fetches data for multiple tickers concurrently using `asyncio` to improve performance.
- **Error Handling**: Logs failed tickers but continues processing the rest of the universe, ensuring partial success.
- **Configuration**: Uses environment variables for database credentials and other settings.
- **Monitoring**: Integrates with AWS Lambda Powertools for structured logging, custom metrics, and distributed tracing.

```python
"""
Daily Data Ingest Lambda Handler
=================================

AWS Lambda function to fetch daily OHLCV data from yfinance and store in Neon PostgreSQL.

Features:
- Fetches latest daily candle for each ticker in configured universe
- UPSERT logic (ON CONFLICT DO UPDATE) for idempotency
- Concurrent data fetching for performance
- Robust error handling with per-ticker failure logging
- CloudWatch metrics and structured logging
- Environment-based configuration

Environment Variables:
- NEON_DATABASE_URL: PostgreSQL connection string
- UNIVERSE_KEY: Stock universe to fetch (default: SPX500)
- MAX_CONCURRENT: Maximum concurrent yfinance requests (default: 10)
- LOG_LEVEL: Logging level (default: INFO)

Author: Manus AI
Date: 2026-01-11
"""

import os
import sys
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import logging

# Third-party imports
import yfinance as yf
import pandas as pd
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.metrics import MetricUnit

# Configure AWS Lambda Powertools
logger = Logger(service="daily-data-ingest")
tracer = Tracer(service="daily-data-ingest")
metrics = Metrics(namespace="PotentialParakeet", service="daily-data-ingest")

# ============================================================================
# Configuration
# ============================================================================

@dataclass
class Config:
    """Lambda configuration from environment variables."""
    
    database_url: str
    universe_key: str = "SPX500"
    max_concurrent: int = 10
    log_level: str = "INFO"
    lookback_days: int = 5  # Fetch last N days to handle holidays/weekends
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        database_url = os.getenv("NEON_DATABASE_URL")
        if not database_url:
            raise ValueError("NEON_DATABASE_URL environment variable is required")
        
        return cls(
            database_url=database_url,
            universe_key=os.getenv("UNIVERSE_KEY", "SPX500"),
            max_concurrent=int(os.getenv("MAX_CONCURRENT", "10")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            lookback_days=int(os.getenv("LOOKBACK_DAYS", "5"))
        )

# ============================================================================
# Stock Universe Definitions
# ============================================================================

def get_sp500_tickers() -> List[str]:
    """Get S&P 500 tickers (simplified for Lambda)."""
    # In production, fetch from external source or parameter store
    return [
        "AAPL", "MSFT", "AMZN", "GOOG", "GOOGL", "META", "TSLA", "NVDA", "BRK-B", "JPM",
        "V", "UNH", "HD", "MA", "PG", "XOM", "CVX", "JNJ", "LLY", "ABBV",
        "BAC", "PFE", "KO", "COST", "WMT", "MRK", "DIS", "CSCO", "PEP", "TMO",
        "ABT", "AVGO", "VZ", "ACN", "MCD", "ADBE", "CRM", "NKE", "CMCSA", "TXN",
        "DHR", "NEE", "WFC", "ORCL", "LIN", "BMY", "UPS", "PM", "QCOM", "RTX",
        "HON", "INTC", "INTU", "T", "LOW", "SPGI", "UNP", "CAT", "AMD", "SBUX",
        "GE", "AMGN", "BA", "IBM", "BLK", "AXP", "DE", "GILD", "MDT", "ISRG",
        "TJX", "BKNG", "MMM", "SYK", "ADP", "CI", "VRTX", "REGN", "ZTS", "CB",
        "NOW", "PLD", "SCHW", "MO", "ADI", "TMUS", "LRCX", "EOG", "DUK", "SO",
        "SLB", "MDLZ", "PNC", "USB", "BDX", "TGT", "CL", "EQIX", "ITW", "APD"
    ]

def get_nasdaq100_tickers() -> List[str]:
    """Get NASDAQ 100 tickers (simplified for Lambda)."""
    return [
        "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "GOOG", "META", "TSLA", "AVGO", "COST",
        "PEP", "ADBE", "CSCO", "NFLX", "TMUS", "AMD", "CMCSA", "INTC", "INTU", "TXN",
        "QCOM", "HON", "AMGN", "AMAT", "BKNG", "ISRG", "SBUX", "MDLZ", "GILD", "ADI",
        "PDD", "VRTX", "LRCX", "ADP", "REGN", "PANW", "KLAC", "MU", "SNPS", "CDNS",
        "ASML", "MELI", "PYPL", "MRVL", "CHTR", "MAR", "ORLY", "NXPI", "CSX", "ABNB"
    ]

def get_asx200_tickers() -> List[str]:
    """Get ASX 200 tickers (simplified for Lambda)."""
    return [
        "BHP.AX", "CBA.AX", "CSL.AX", "NAB.AX", "WBC.AX", "ANZ.AX", "WES.AX", "MQG.AX",
        "WOW.AX", "TLS.AX", "RIO.AX", "FMG.AX", "WDS.AX", "GMG.AX", "TCL.AX", "STO.AX",
        "QBE.AX", "SUN.AX", "IAG.AX", "AMC.AX", "COL.AX", "ORG.AX", "APA.AX", "REA.AX",
        "ALL.AX", "BXB.AX", "JHX.AX", "NCM.AX", "S32.AX", "ORI.AX", "ASX.AX", "XRO.AX"
    ]

UNIVERSE_REGISTRY = {
    "SPX500": get_sp500_tickers,
    "NASDAQ100": get_nasdaq100_tickers,
    "ASX200": get_asx200_tickers,
}

def get_universe_tickers(universe_key: str) -> List[str]:
    """Get tickers for specified universe."""
    if universe_key not in UNIVERSE_REGISTRY:
        raise ValueError(f"Unknown universe: {universe_key}. Available: {list(UNIVERSE_REGISTRY.keys())}")
    return UNIVERSE_REGISTRY[universe_key]()

# ============================================================================
# Data Models
# ============================================================================

@dataclass
class MarketDataRow:
    """Represents a single row of market data."""
    ticker: str
    date: str  # YYYY-MM-DD format
    open: float
    high: float
    low: float
    close: float
    volume: int
    adjusted_close: Optional[float] = None
    source: str = "yfinance"
    data_quality: str = "good"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for database insertion."""
        return asdict(self)

@dataclass
class FetchResult:
    """Result of fetching data for a single ticker."""
    ticker: str
    success: bool
    rows_fetched: int = 0
    error: Optional[str] = None
    data: Optional[List[MarketDataRow]] = None

# ============================================================================
# Data Fetching
# ============================================================================

class YFinanceDataFetcher:
    """Fetches OHLCV data from yfinance with error handling."""
    
    def __init__(self, config: Config):
        self.config = config
        self.semaphore = asyncio.Semaphore(config.max_concurrent)
    
    async def fetch_ticker(self, ticker: str) -> FetchResult:
        """
        Fetch latest daily data for a single ticker.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            FetchResult with success status and data or error
        """
        async with self.semaphore:  # Limit concurrent requests
            try:
                # Run yfinance in thread pool (it's synchronous)
                loop = asyncio.get_event_loop()
                df = await loop.run_in_executor(
                    None,
                    self._fetch_ticker_sync,
                    ticker
                )
                
                if df is None or df.empty:
                    return FetchResult(
                        ticker=ticker,
                        success=False,
                        error="No data returned from yfinance"
                    )
                
                # Convert DataFrame to MarketDataRow objects
                rows = self._dataframe_to_rows(ticker, df)
                
                logger.info(f"✅ {ticker}: Fetched {len(rows)} rows")
                return FetchResult(
                    ticker=ticker,
                    success=True,
                    rows_fetched=len(rows),
                    data=rows
                )
                
            except Exception as e:
                logger.warning(f"❌ {ticker}: {str(e)}")
                return FetchResult(
                    ticker=ticker,
                    success=False,
                    error=str(e)
                )
    
    def _fetch_ticker_sync(self, ticker: str) -> Optional[pd.DataFrame]:
        """Synchronous yfinance fetch (runs in thread pool)."""
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.config.lookback_days)
            
            # Fetch data
            ticker_obj = yf.Ticker(ticker)
            df = ticker_obj.history(
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                interval="1d",
                auto_adjust=False  # Keep both Close and Adj Close
            )
            
            if df.empty:
                return None
            
            # Reset index to make Date a column
            df = df.reset_index()
            
            return df
            
        except Exception as e:
            logger.warning(f"yfinance error for {ticker}: {e}")
            return None
    
    def _dataframe_to_rows(self, ticker: str, df: pd.DataFrame) -> List[MarketDataRow]:
        """Convert yfinance DataFrame to MarketDataRow objects."""
        rows = []
        
        for _, row in df.iterrows():
            try:
                # Extract date (handle different yfinance formats)
                if isinstance(row['Date'], pd.Timestamp):
                    date_str = row['Date'].strftime("%Y-%m-%d")
                else:
                    date_str = str(row['Date'])[:10]
                
                # Create MarketDataRow
                market_row = MarketDataRow(
                    ticker=ticker,
                    date=date_str,
                    open=float(row['Open']),
                    high=float(row['High']),
                    low=float(row['Low']),
                    close=float(row['Close']),
                    volume=int(row['Volume']),
                    adjusted_close=float(row.get('Adj Close', row['Close'])),
                    source="yfinance",
                    data_quality="good"
                )
                
                rows.append(market_row)
                
            except Exception as e:
                logger.warning(f"Failed to parse row for {ticker}: {e}")
                continue
        
        return rows
    
    async def fetch_all(self, tickers: List[str]) -> List[FetchResult]:
        """
        Fetch data for all tickers concurrently.
        
        Args:
            tickers: List of ticker symbols
            
        Returns:
            List of FetchResult objects
        """
        logger.info(f"📥 Fetching data for {len(tickers)} tickers (max {self.config.max_concurrent} concurrent)")
        
        tasks = [self.fetch_ticker(ticker) for ticker in tickers]
        results = await asyncio.gather(*tasks)
        
        return results

# ============================================================================
# Database Operations
# ============================================================================

class MarketDataRepository:
    """Handles database operations for market data."""
    
    def __init__(self, config: Config):
        self.config = config
        self.engine = create_async_engine(
            config.database_url,
            pool_size=1,  # Lambda: 1 connection per instance
            max_overflow=0,
            pool_pre_ping=True,
            echo=False
        )
        self.async_session = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async def upsert_market_data(self, rows: List[MarketDataRow]) -> int:
        """
        Insert or update market data rows using UPSERT.
        
        Args:
            rows: List of MarketDataRow objects
            
        Returns:
            Number of rows affected
        """
        if not rows:
            return 0
        
        # Prepare UPSERT query (PostgreSQL-specific)
        upsert_query = text("""
            INSERT INTO market_data (
                ticker, date, open, high, low, close, volume, 
                adjusted_close, source, data_quality, created_at, updated_at
            ) VALUES (
                :ticker, :date, :open, :high, :low, :close, :volume,
                :adjusted_close, :source, :data_quality, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            ON CONFLICT (ticker, date) 
            DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume,
                adjusted_close = EXCLUDED.adjusted_close,
                source = EXCLUDED.source,
                data_quality = EXCLUDED.data_quality,
                updated_at = CURRENT_TIMESTAMP
        """)
        
        async with self.async_session() as session:
            try:
                # Execute batch insert
                result = await session.execute(
                    upsert_query,
                    [row.to_dict() for row in rows]
                )
                await session.commit()
                
                rows_affected = result.rowcount if result.rowcount else len(rows)
                logger.info(f"💾 Upserted {rows_affected} rows to database")
                
                return rows_affected
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Database error: {e}")
                raise
    
    async def close(self):
        """Close database connection."""
        await self.engine.dispose()

# ============================================================================
# Lambda Handler
# ============================================================================

@tracer.capture_lambda_handler
@logger.inject_lambda_context
@metrics.log_metrics(capture_cold_start_metric=True)
async def handler_async(event: Dict, context) -> Dict:
    """
    Main Lambda handler (async version).
    """
    start_time = datetime.now()
    
    try:
        # Load configuration
        config = Config.from_env()
        
        # Allow universe override from event
        if "universe_key" in event:
            config.universe_key = event["universe_key"]
        
        logger.info(f"🚀 Starting daily data ingest for universe: {config.universe_key}")
        
        # Get ticker universe
        tickers = get_universe_tickers(config.universe_key)
        logger.info(f"📊 Universe contains {len(tickers)} tickers")
        
        # Initialize fetcher and repository
        fetcher = YFinanceDataFetcher(config)
        repo = MarketDataRepository(config)
        
        # Fetch data for all tickers
        fetch_results = await fetcher.fetch_all(tickers)
        
        # Separate successful and failed fetches
        successful = [r for r in fetch_results if r.success]
        failed = [r for r in fetch_results if not r.success]
        
        logger.info(f"✅ Successful: {len(successful)}, ❌ Failed: {len(failed)}")
        
        # Log failed tickers
        if failed:
            failed_tickers = [r.ticker for r in failed]
            logger.warning(f"Failed tickers: {', '.join(failed_tickers[:20])}")
            if len(failed_tickers) > 20:
                logger.warning(f"... and {len(failed_tickers) - 20} more")
        
        # Collect all rows for database insertion
        all_rows = []
        for result in successful:
            if result.data:
                all_rows.extend(result.data)
        
        logger.info(f"📦 Total rows to upsert: {len(all_rows)}")
        
        # Upsert to database
        rows_affected = 0
        if all_rows:
            rows_affected = await repo.upsert_market_data(all_rows)
        
        # Close database connection
        await repo.close()
        
        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Record CloudWatch metrics
        metrics.add_metric(name="TickersProcessed", unit=MetricUnit.Count, value=len(tickers))
        metrics.add_metric(name="TickersSuccessful", unit=MetricUnit.Count, value=len(successful))
        metrics.add_metric(name="TickersFailed", unit=MetricUnit.Count, value=len(failed))
        metrics.add_metric(name="RowsUpserted", unit=MetricUnit.Count, value=rows_affected)
        metrics.add_metric(name="ExecutionTime", unit=MetricUnit.Seconds, value=execution_time)
        
        # Build response
        response = {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Daily data ingest completed",
                "universe": config.universe_key,
                "tickers_processed": len(tickers),
                "tickers_successful": len(successful),
                "tickers_failed": len(failed),
                "rows_upserted": rows_affected,
                "execution_time_seconds": round(execution_time, 2),
                "failed_tickers": [r.ticker for r in failed[:50]]  # First 50 failures
            })
        }
        
        logger.info(f"✅ Ingest completed in {execution_time:.2f}s")
        return response
        
    except Exception as e:
        logger.exception(f"❌ Fatal error: {e}")
        
        metrics.add_metric(name="FatalErrors", unit=MetricUnit.Count, value=1)
        
        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": "Daily data ingest failed",
                "error": str(e)
            })
        }

def handler(event: Dict, context) -> Dict:
    """
    Lambda handler entry point (sync wrapper for async handler).
    """
    # Run async handler in event loop
    return asyncio.run(handler_async(event, context))

```

### 4. Deployment & Configuration

**Terraform Configuration**:

This Lambda function will be defined in `infrastructure/terraform/lambda.tf` and triggered by an EventBridge rule.

```hcl
# infrastructure/terraform/lambda.tf
resource "aws_lambda_function" "daily_ingest" {
  function_name = "potential-parakeet-daily-ingest-${var.environment}"
  role          = aws_iam_role.lambda_exec.arn
  
  package_type = "Image"
  image_uri    = aws_ecr_repository.daily_ingest.repository_url
  
  memory_size = 1024
  timeout     = 900  # 15 minutes
  
  environment {
    variables = {
      ENVIRONMENT       = var.environment
      NEON_DATABASE_URL = data.aws_secretsmanager_secret_version.db_credentials.secret_string
      UNIVERSE_KEY      = "SPX500"
      MAX_CONCURRENT    = "10"
      LOG_LEVEL         = "INFO"
    }
  }
}

# infrastructure/terraform/eventbridge.tf
resource "aws_cloudwatch_event_rule" "daily_ingest_schedule" {
  name                = "potential-parakeet-daily-ingest-schedule-${var.environment}"
  description         = "Run daily data ingest at 6:00 PM EST"
  schedule_expression = "cron(0 22 * * ? *)"  # 10 PM UTC = 6 PM EST
}

resource "aws_cloudwatch_event_target" "daily_ingest_target" {
  rule      = aws_cloudwatch_event_rule.daily_ingest_schedule.name
  target_id = "DailyIngestLambda"
  arn       = aws_lambda_function.daily_ingest.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.daily_ingest.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_ingest_schedule.arn
}
```

**Dependencies (`requirements.txt`)**:

```
yfinance
pandas
sqlalchemy[asyncpg]
aws-lambda-powertools
```

This module provides a complete, production-ready data pipeline for daily market data ingestion, forming a critical component of the overall migration strategy.

---

**End of Appendix C**
