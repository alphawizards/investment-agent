# Ralph Implementation Guide: Potential Parakeet Migration

**Objective**: This document provides a comprehensive guide for Ralph (the Claude Code CLI tool) to successfully execute the migration of the **Potential Parakeet** repository to a modern, serverless architecture on AWS and Neon PostgreSQL.

---

## 1. Critical Files for Initial Context

Before making any changes, Ralph must first analyze the following files to understand the project's architecture, dependencies, and configuration. This initial context is crucial for a successful migration.

| File Path | Purpose & Key Insights |
|---|---|
| `MIGRATION_STRATEGY_DOCUMENT.md` | **Primary Source of Truth**. Contains the complete audit, target architecture, and 7-phase roadmap. Ralph must refer to this document for all high-level decisions. |
| `backend/config.py` | **Configuration Hub**. Defines how environment variables and settings are loaded using Pydantic. This file will need to be modified to support Neon DB URLs and AWS service configurations. |
| `env.template` | **Environment Setup**. Shows the required environment variables. Ralph will need to create a `.env` file from this template and add new variables for AWS and Neon. |
| `strategy/stock_universe.py` | **Ticker Universe Definition**. Shows how lists of stocks are defined and retrieved. The new Lambda data ingest module will use this logic. |
| `strategy/pipeline/pipeline.py` | **Core Strategy Logic**. Demonstrates the modular pipeline architecture (Data → Signal → Allocation → Reporting). This logic should remain largely untouched. |
| `strategy/fast_data_loader.py` | **Data Caching & Loading**. Shows the current file-based Parquet caching mechanism. This entire module needs to be refactored to use S3 for storage. |
| `backend/database/connection.py` | **Database Connection**. Contains the current SQLAlchemy setup for SQLite. This file will be modified to handle the new Neon PostgreSQL connection. |
| `docker-compose.yml` | **Current Deployment Model**. Defines the existing monolithic, container-based deployment. Understanding this is key to decomposing the application into microservices/Lambda functions. |

## 2. Existing Architecture & Conventions

Ralph should be aware of the following architectural patterns and coding conventions to ensure the refactored code aligns with the existing codebase:

- **Pydantic for Configuration**: All configuration is managed through `pydantic-settings` in `backend/config.py`. New configurations (e.g., S3 bucket names, AWS regions) should be added here.
- **SQLAlchemy ORM**: The project uses SQLAlchemy for database interactions. The migration should continue to use SQLAlchemy but with its `asyncio` extension and the `asyncpg` driver.
- **Modular Pipeline**: The quantitative strategies are built on a highly modular pipeline. Data fetching, signal generation, and allocation are in separate layers. This separation must be maintained.
- **FastAPI Routers**: The backend API is organized into routers (`backend/routers/`). This structure provides a natural way to decompose the API into separate Lambda functions.
- **Type Hinting**: The codebase has excellent type hint coverage. All new code written by Ralph must include full type hints.
- **Pathlib for Paths**: The project uses `pathlib.Path` for all file system operations. This will need to be replaced with an S3 client (e.g., `boto3` or `s3fs`) for cache and data storage.

## 3. Step-by-Step Implementation Checklist

This checklist provides the granular, step-by-step tasks for Ralph to execute. Ralph should proceed through these phases sequentially.

### Phase 1: Environment Setup & Initial Refactoring

- [ ] **1.1. Create `.env` file**: Copy `env.template` to a new `.env` file in the `backend` directory.
- [ ] **1.2. Update Environment Variables**: In the new `.env` file, comment out the `DATABASE_URL` for SQLite and add a placeholder for the Neon database URL (`NEON_DATABASE_URL`).
- [ ] **1.3. Install `psycopg2-binary` & `asyncpg`**: Add `psycopg2-binary` and `asyncpg` to `requirements.txt`.
- [ ] **1.4. Update `backend/config.py`**: Modify the `Settings` class to read `NEON_DATABASE_URL` and other AWS-related variables from the environment.
- [ ] **1.5. Update `backend/database/connection.py`**: Implement logic to create an `async` SQLAlchemy engine using `create_async_engine` with the `NEON_DATABASE_URL`.

### Phase 2: Database Schema & Data Ingest

- [ ] **2.1. Create SQL Schema File**: Use the provided `market_data_schema.sql` to create the `market_data` table in the Neon database.
- [ ] **2.2. Implement Lambda Handler**: Use the provided `lambda_daily_ingest.py` script as the basis for the daily data ingest Lambda function.

### Phase 3: Infrastructure as Code (IaC) with Terraform

- [ ] **3.1. Initialize Terraform Project**: Create an `infrastructure/` directory and initialize a Terraform project.
- [ ] **3.2. Define Lambda Function**: Create `lambda.tf` to define the `aws_lambda_function` for the data ingest, using a container image for deployment.
- [ ] **3.3. Define EventBridge Trigger**: Create `eventbridge.tf` to define the daily trigger for the Lambda.
- [ ] **3.4. Define S3 Bucket**: Create `s3.tf` to define the S3 bucket that will replace the local `/cache` directory.
- [ ] **3.5. Define Secrets**: Create `secrets.tf` to define the AWS Secrets Manager secret for the `NEON_DATABASE_URL`.

### Phase 4: Application Code Refactoring

- [ ] **4.1. Implement S3 Cache**: Create a new module `aws/s3_cache.py` with functions to `read_parquet_from_s3` and `write_parquet_to_s3`.
- [ ] **4.2. Refactor `fast_data_loader.py`**: Replace all local file system calls (`pd.read_parquet`, `df.to_parquet`) with calls to the new `s3_cache` module.
- [ ] **4.3. Convert Database I/O to Async**: Refactor all database calls in the API routers to use `async/await` with the async SQLAlchemy session.
- [ ] **4.4. Decompose API into Lambdas**: Create separate handler files for each main API router (e.g., `lambda_trades.py`, `lambda_strategies.py`) and wrap them with an API Gateway adapter like `mangum`.

---

By following this guide, Ralph will have all the necessary context and instructions to perform a successful and structured migration of the Potential Parakeet project.
