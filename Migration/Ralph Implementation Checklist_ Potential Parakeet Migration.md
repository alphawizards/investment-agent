# Ralph Implementation Checklist: Potential Parakeet Migration

This checklist provides a step-by-step guide for Ralph to execute the migration of the Potential Parakeet repository to a serverless architecture on AWS with Neon PostgreSQL.

## Phase 1: Environment Setup & Initial Refactoring

- [ ] **1.1. Create `.env` file**: Copy `env.template` to a new `.env` file in the `backend` directory.
- [ ] **1.2. Update Environment Variables**: In the new `.env` file, comment out the `DATABASE_URL` for SQLite and add a placeholder for the Neon database URL (`NEON_DATABASE_URL`).
- [ ] **1.3. Install `psycopg2-binary`**: Add `psycopg2-binary` to `requirements.txt` to support PostgreSQL connections.
- [ ] **1.4. Update `backend/config.py`**: Modify the `Settings` class in `backend/config.py` to read the `NEON_DATABASE_URL` from the environment. Prioritize `NEON_DATABASE_URL` if it exists.
- [ ] **1.5. Update `backend/database/connection.py`**: Modify the database connection logic to use the `NEON_DATABASE_URL` and `psycopg2` when available. The application should still be able to run with SQLite for local testing.

## Phase 2: Database Schema Migration

- [ ] **2.1. Create SQL Schema File**: Create a new file `database/schema.sql` and add the provided `market_data` table schema.
- [ ] **2.2. Create a Migration Script**: Create a Python script `scripts/migrate_db.py` that connects to the Neon database and executes the `database/schema.sql` file to create the tables.
- [ ] **2.3. (Optional) Data Migration**: Create a script to migrate existing data from the SQLite database (`data/trades.db`) to the new Neon PostgreSQL database. This is for preserving historical data.

## Phase 3: Infrastructure as Code (IaC) with Terraform

- [ ] **3.1. Create Terraform Project**: Initialize a new Terraform project in a new top-level directory named `infrastructure`.
- [ ] **3.2. Create `main.tf`**: Define the AWS provider and region.
- [ ] **3.3. Create `variables.tf`**: Define variables for environment (e.g., `dev`, `prod`), AWS region, and other configurable parameters.
- [ ] **3.4. Create `lambda.tf`**: Define the `aws_lambda_function` for the daily data ingest. Use the provided Python script `lambda_daily_ingest.py` as the source.
- [ ] **3.5. Create `eventbridge.tf`**: Define the `aws_cloudwatch_event_rule` to trigger the Lambda function on a daily schedule.
- [ ] **3.6. Create `iam.tf`**: Define the IAM roles and policies required for the Lambda function to execute and access other AWS services (e.g., CloudWatch Logs, Secrets Manager).
- [ ] **3.7. Create `secrets.tf`**: Define the `aws_secretsmanager_secret` to store the Neon database URL.

## Phase 4: Application Code Refactoring for Serverless

- [ ] **4.1. Refactor Data Loading**: Modify `strategy/fast_data_loader.py` and other data loading modules to read from an S3 bucket instead of the local file system (`/cache`).
- [ ] **4.2. Implement S3 Caching**: Create a new module `aws/s3_cache.py` that provides functions to read from and write to an S3 bucket. This will replace the local Parquet cache.
- [ ] **4.3. Convert to Async I/O**: Refactor synchronous file and database I/O operations to be asynchronous using `aiofiles` and `asyncpg` (or `SQLAlchemy`'s async support).
- [ ] **4.4. Decompose Backend API**: Break down the monolithic FastAPI backend into smaller, single-purpose Lambda functions. For example, create separate Lambda functions for:
    - `/api/v1/data`
    - `/api/v1/strategies`
    - `/api/v1/backtest`
- [ ] **4.5. Use API Gateway**: Create a new Terraform file `api_gateway.tf` to define an AWS API Gateway that routes requests to the appropriate Lambda functions.

## Phase 5: Deployment & CI/CD

- [ ] **5.1. Create `buildspec.yml`**: Create a `buildspec.yml` file for AWS CodeBuild to automate the building and deployment process.
- [ ] **5.2. Create a Dockerfile for Lambda**: Create a `Dockerfile` in the `backend` directory to package the Lambda function with its dependencies.
- [ ] **5.3. Set up ECR**: Create an `aws_ecr_repository` in Terraform to store the Lambda Docker images.
- [ ] **5.4. Create CodePipeline**: Define an AWS CodePipeline in `pipeline.tf` that triggers on commits to the `main` branch, builds the Docker image, and deploys the Lambda functions.

## Phase 6: Testing

- [ ] **6.1. Update Unit Tests**: Modify existing unit tests in the `tests/` directory to mock AWS services (S3, Secrets Manager) using `moto`.
- [ ] **6.2. Create Integration Tests**: Create new integration tests that deploy the infrastructure to a temporary AWS environment, run tests against the live services, and then tear down the infrastructure.
- [ ] **6.3. End-to-End Testing**: Use Playwright tests (`tests/e2e/`) to test the deployed frontend and backend integration.
