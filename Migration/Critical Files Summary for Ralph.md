# Critical Files Summary for Ralph

This document provides a quick reference to the most important files Ralph should examine before making changes.

## Configuration & Environment

- `env.template` - Environment variable template
- `backend/config.py` - Pydantic settings configuration
- `requirements.txt` - Python dependencies

## Database Layer

- `backend/database/connection.py` - Database connection setup
- `backend/database/models.py` - SQLAlchemy ORM models
- `market_data_schema.sql` - New PostgreSQL schema for market data

## Backend API

- `backend/main.py` - FastAPI application entry point
- `backend/routers/` - API route handlers (trades, data, strategies, etc.)

## Data Loading & Caching

- `strategy/fast_data_loader.py` - Current file-based data loader (needs S3 refactoring)
- `strategy/tiingo_data_loader.py` - Tiingo API data fetcher
- `strategy/stock_universe.py` - Stock ticker universe definitions

## Strategy Pipeline

- `strategy/pipeline/pipeline.py` - Core pipeline orchestration
- `strategy/pipeline/data_layer.py` - Data fetching layer
- `strategy/pipeline/signal_layer.py` - Signal generation layer
- `strategy/pipeline/allocation_layer.py` - Portfolio allocation layer
- `strategy/pipeline/reporting_layer.py` - Performance reporting

## Lambda Functions (New)

- `lambda_daily_ingest.py` - Daily data ingest Lambda handler
- `market_data_schema.sql` - Database schema for market_data table

## Documentation

- `MIGRATION_STRATEGY_DOCUMENT.md` - Complete migration strategy and audit
- `RALPH_IMPLEMENTATION_GUIDE.md` - Step-by-step implementation guide
- `ralph_checklist.md` - Detailed task checklist

## Key Directories

- `backend/` - FastAPI backend application
- `strategy/` - Quantitative strategy modules
- `tests/` - Unit and integration tests
- `dashboard/` - React frontend (TypeScript)
- `infrastructure/` - (To be created) Terraform IaC files
