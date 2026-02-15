# Potential Parakeet - AWS Serverless Migration

**Quantitative Trading Platform Migration: Docker → AWS Lambda + Neon PostgreSQL**

[![Architecture](https://img.shields.io/badge/Architecture-Serverless-green)](/)
[![Database](https://img.shields.io/badge/Database-Neon_PostgreSQL-blue)](https://neon.tech)
[![Infrastructure](https://img.shields.io/badge/IaC-Terraform-purple)](https://www.terraform.io)
[![Python](https://img.shields.io/badge/Python-3.11-yellow)](https://www.python.org)

---

## 🚀 Quick Start

**New to the project?** Start here:

1. **[QUICKSTART_CHECKLIST.md](QUICKSTART_CHECKLIST.md)** - 30-minute setup checklist
2. **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Complete step-by-step setup guide
3. **[MIGRATION_PROGRESS.md](MIGRATION_PROGRESS.md)** - Current migration status

**Already setup?** Jump to:
- [Infrastructure Deployment](infrastructure/README.md)
- [Development Workflow](#development-workflow)
- [API Documentation](#api-documentation)

---

## 📋 Project Status

### ✅ Phase 1: Foundation (COMPLETED)
- [x] Async database layer with SQLAlchemy
- [x] Alembic migrations for schema management
- [x] AWS Secrets Manager integration
- [x] Terraform infrastructure configuration
- [x] S3 bucket setup for cache storage
- [x] IAM roles with least-privilege access

### 🔄 Phase 2: Storage Layer (IN PROGRESS)
- [ ] S3 cache adapter implementation
- [ ] Data loader refactoring
- [ ] Parquet file migration to S3

### ⏳ Phase 3-7: Upcoming
- [ ] Lambda function decomposition
- [ ] API Gateway configuration
- [ ] Async API conversion
- [ ] CloudFlare edge integration
- [ ] CI/CD pipeline
- [ ] Monitoring & observability

**Progress:** 14% complete (Phase 1 of 7)

---

## 🏗️ Architecture

### Before (Monolithic Docker)
```
┌─────────────────────────────────────┐
│     Docker Container (t3.medium)    │
│  ┌───────────────────────────────┐  │
│  │  FastAPI App                  │  │
│  │  ├── All routes (1 process)   │  │
│  │  ├── SQLite database          │  │
│  │  ├── Local Parquet cache      │  │
│  │  └── Sync operations          │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
Cost: ~$45/month
Scaling: Manual EC2 resize
```

### After (Serverless)
```
┌──────────────────────────────────────────────────────────┐
│                    CloudFlare Edge                        │
│  ┌──────────────┐        ┌──────────────────┐           │
│  │ Pages (UI)   │        │ Workers (Auth)   │           │
│  └──────────────┘        └──────────────────┘           │
└────────────────────────────┬─────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────┐
│                       AWS Cloud                           │
│                                                           │
│  ┌────────────┐        ┌────────────────────────┐       │
│  │ API        │        │  Lambda Functions      │       │
│  │ Gateway    │───────▶│  ├── Trades API        │       │
│  │            │        │  ├── Data API          │       │
│  └────────────┘        │  ├── Strategies API    │       │
│                        │  ├── Scanner API       │       │
│         ┌──────────────│  └── Daily Ingest      │       │
│         │              └────────┬───────────────┘       │
│         │                       │                        │
│         ▼                       ▼                        │
│  ┌──────────┐          ┌──────────────┐                │
│  │EventBridge│         │  Secrets     │                │
│  │(Schedule) │         │  Manager     │                │
│  └──────────┘          └──────────────┘                │
│                                                          │
│  ┌──────────────────────────────────────────┐          │
│  │     S3 (Parquet Cache Storage)           │          │
│  │     ├── Lifecycle policies               │          │
│  │     ├── Encryption (AES256)              │          │
│  │     └── Cost optimization                │          │
│  └──────────────────────────────────────────┘          │
│                                                          │
│  ┌──────────────────────────────────────────┐          │
│  │  CloudWatch (Logs & Monitoring)          │          │
│  └──────────────────────────────────────────┘          │
└──────────────────────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────┐
│              Neon PostgreSQL (Serverless)                 │
│  ├── Auto-scaling compute                                │
│  ├── Auto-scaling storage                                │
│  └── Branching for dev/staging                           │
└──────────────────────────────────────────────────────────┘

Cost: ~$5/month (89% reduction)
Scaling: Automatic, pay-per-use
```

---

## 💡 Key Features

### Performance
- ⚡ **Sub-200ms API latency** (p50)
- 🚀 **Auto-scaling** to handle traffic spikes
- 📦 **Edge caching** via CloudFlare
- 🔄 **Async operations** for better concurrency

### Cost Optimization
- 💰 **89% cost reduction** ($45 → $5/month)
- 📊 **Pay-per-use pricing** (no idle costs)
- 🗄️ **S3 lifecycle policies** (auto-archive old data)
- 🆓 **Free tier compatible** (first 12 months)

### Security
- 🔐 **Secrets Manager** for credentials
- 🛡️ **Least-privilege IAM** roles
- 🔒 **Encrypted at rest** (S3, RDS)
- 🌐 **Edge authentication** (CloudFlare Workers)

### Developer Experience
- 🐍 **Python 3.11** with type hints
- 🔄 **Async/await** throughout
- 📝 **Alembic migrations** for schema changes
- 🧪 **Local development** with SQLite
- 📚 **Comprehensive documentation**

---

## 📁 Project Structure

```
potential-parakeet-2/
├── backend/                      # FastAPI application
│   ├── config.py                # ✅ Settings with Neon support
│   ├── main.py                  # FastAPI app entry point
│   ├── database/
│   │   ├── connection.py        # ✅ Async SQLAlchemy
│   │   ├── models.py            # ORM models
│   │   └── schemas.py           # Pydantic schemas
│   ├── routers/                 # API endpoints
│   │   ├── trades.py            # ⏳ To convert to async
│   │   ├── data.py              # ⏳ To convert to async
│   │   ├── strategies.py        # ⏳ To convert to async
│   │   └── scanner.py           # ⏳ To convert to async
│   └── utils/
│       └── secrets.py           # ✅ AWS Secrets Manager
│
├── lambda/                       # ⏳ Lambda handlers (Phase 3)
│   ├── trades/
│   ├── data/
│   ├── strategies/
│   ├── scanner/
│   └── ingest/
│
├── infrastructure/               # ✅ Terraform IaC
│   ├── terraform/
│   │   ├── main.tf              # ✅ Provider config
│   │   ├── variables.tf         # ✅ Input variables
│   │   ├── outputs.tf           # ✅ Output values
│   │   ├── s3.tf                # ✅ S3 buckets
│   │   ├── iam.tf               # ✅ IAM roles
│   │   ├── secrets.tf           # ✅ Secrets Manager
│   │   ├── lambda.tf            # ⏳ Lambda functions
│   │   ├── api_gateway.tf       # ⏳ API Gateway
│   │   └── monitoring.tf        # ⏳ CloudWatch
│   └── environments/
│       ├── dev.tfvars           # ✅ Dev config
│       └── prod.tfvars          # ✅ Prod config
│
├── alembic/                      # ✅ Database migrations
│   ├── versions/
│   │   └── 20250112_0001_*.py   # ✅ Initial migration
│   ├── env.py                   # ✅ Async migration env
│   └── alembic.ini              # ✅ Alembic config
│
├── strategy/                     # Trading strategies
│   ├── fast_data_loader.py      # ⏳ To refactor for S3
│   ├── tiingo_data_loader.py    # ⏳ To refactor for S3
│   └── unified_asx_loader.py    # ⏳ To refactor for S3
│
├── .env.example                  # ✅ Environment template
├── requirements.txt              # ✅ Python dependencies
├── SETUP_GUIDE.md               # ✅ Complete setup guide
├── QUICKSTART_CHECKLIST.md      # ✅ 30-min setup checklist
├── MIGRATION_PROGRESS.md        # ✅ Migration status
└── README_MIGRATION.md          # ✅ This file
```

**Legend:**
- ✅ Completed
- 🔄 In Progress
- ⏳ Planned

---

## 🛠️ Development Workflow

### Local Development (SQLite)

```bash
# 1. Setup environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure .env
cp .env.example .env
# Edit .env: Set TIINGO_API_KEY, USE_NEON=false

# 3. Initialize database
alembic upgrade head

# 4. Run development server
uvicorn backend.main:app --reload

# 5. Access API docs
http://localhost:8000/docs
```

### Production Development (Neon PostgreSQL)

```bash
# 1. Update .env
USE_NEON=true
NEON_DATABASE_URL=postgresql+asyncpg://...

# 2. Run migrations
alembic upgrade head

# 3. Deploy to AWS
cd infrastructure/terraform
terraform apply -var-file=../environments/prod.tfvars
```

### Testing

```bash
# Unit tests
pytest tests/

# Integration tests with Neon
pytest tests/integration/ --neon

# Load tests
locust -f tests/load_test.py
```

---

## 📊 Database Schema

### Core Tables

**trades** - All executed trades
```sql
- id (PK)
- trade_id (unique)
- ticker, direction, quantity, prices
- entry_date, exit_date
- pnl, pnl_percent
- strategy_name, status
- knowledge_timestamp, event_timestamp (bi-temporal)
```

**portfolio_snapshots** - Daily portfolio values
```sql
- id (PK)
- snapshot_date
- total_value, cash_balance, invested_value
- daily_return, cumulative_return
- volatility_21d, sharpe_ratio_21d
```

**index_constituents** - Historical index membership
```sql
- id (PK)
- ticker, index_name
- start_date, end_date
- active
```

**market_data** - OHLCV data (PostgreSQL only)
```sql
- ticker, date (composite PK)
- open, high, low, close, volume
- adjusted_close
- source, data_quality
- created_at, updated_at
```

---

## 🔌 API Endpoints

### Trades
- `GET /trades` - List all trades
- `POST /trades` - Create trade
- `GET /trades/{id}` - Get trade details
- `PUT /trades/{id}` - Update trade
- `DELETE /trades/{id}` - Delete trade

### Market Data
- `GET /data/prices/{ticker}` - Get price history
- `GET /data/latest/{ticker}` - Get latest price
- `POST /data/refresh` - Refresh market data

### Strategies
- `GET /strategies` - List strategies
- `POST /strategies/backtest` - Run backtest
- `GET /strategies/performance` - Get performance metrics

### Scanner
- `POST /scanner/scan` - Run momentum scanner
- `GET /scanner/results` - Get scan results

---

## 💰 Cost Breakdown

### Current (Docker on EC2)
| Service | Cost |
|---------|------|
| EC2 t3.medium | $30/month |
| EBS 50GB | $5/month |
| Data transfer | $10/month |
| **Total** | **$45/month** |

### Target (Serverless)
| Service | Free Tier | After Free Tier |
|---------|-----------|-----------------|
| Lambda (1M req) | ✅ Free | $0.20/month |
| S3 (10GB) | ✅ Free (5GB) | $0.50/month |
| API Gateway (1M req) | ✅ Free | $3.50/month |
| Neon PostgreSQL | ✅ Free | $0/month |
| Secrets Manager | 30-day trial | $0.80/month |
| CloudWatch Logs | ✅ Free (5GB) | $0/month |
| **Total** | **$0/month** | **$5/month** |

**Savings: 89% ($40/month)**

---

## 🔐 Security Best Practices

### Implemented
- ✅ Secrets stored in AWS Secrets Manager
- ✅ IAM roles with least-privilege access
- ✅ S3 bucket encryption (AES256)
- ✅ MFA on AWS root account
- ✅ `.env` and `terraform.tfvars` in `.gitignore`

### Recommended
- [ ] Enable AWS CloudTrail for audit logs
- [ ] Set up AWS Cost Alerts
- [ ] Configure WAF for API Gateway
- [ ] Implement rate limiting per API key
- [ ] Enable VPC for Lambda (if needed)

---

## 📈 Performance Metrics

### Current (Docker)
- **API Latency (p50):** ~150ms
- **API Latency (p99):** ~800ms
- **Cold Start:** N/A
- **Concurrent Users:** 10-20
- **Daily Ingest Time:** ~8 minutes

### Target (Serverless)
- **API Latency (p50):** < 200ms ⏳
- **API Latency (p99):** < 1s ⏳
- **Cold Start:** < 2s ⏳
- **Concurrent Users:** 1000+ ⏳
- **Daily Ingest Time:** < 5 minutes ⏳

**Note:** Targets to be measured after Phase 4 completion

---

## 🚦 Migration Phases

### ✅ Phase 1: Foundation (2 weeks) - COMPLETE
- Database migration to async
- Alembic setup
- Terraform infrastructure
- Secrets Manager integration

### 🔄 Phase 2: Storage Layer (1 week) - IN PROGRESS
- S3 cache adapter
- Data loader refactoring

### ⏳ Phase 3: Lambda Functions (2 weeks)
- Lambda handlers
- API Gateway setup
- EventBridge schedules

### ⏳ Phase 4: API Async Conversion (1 week)
- Convert all routes to async
- Update dependencies
- Integration testing

### ⏳ Phase 5: CloudFlare Edge (1 week)
- Workers for authentication
- Pages for frontend

### ⏳ Phase 6: CI/CD (1 week)
- GitHub Actions workflows
- Automated testing
- Automated deployment

### ⏳ Phase 7: Monitoring (1 week)
- CloudWatch dashboards
- SNS alerts
- Performance monitoring

**Total Timeline:** 9 weeks (14% complete)

---

## 📚 Documentation

### Setup & Configuration
- **[QUICKSTART_CHECKLIST.md](QUICKSTART_CHECKLIST.md)** - Fast setup checklist
- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Detailed setup instructions
- **[infrastructure/README.md](infrastructure/README.md)** - Terraform guide

### Development
- **[MIGRATION_PROGRESS.md](MIGRATION_PROGRESS.md)** - Current status
- **[alembic/README](alembic/README)** - Database migrations

### Reference
- **[Migration Strategy Document](Migration/MIGRATION_STRATEGY_DOCUMENT.md)** - Complete migration plan
- **[Implementation Guide](Migration/Ralph Implementation Guide_ Potential Parakeet Migration.md)** - Step-by-step guide

---

## 🐛 Troubleshooting

### Common Issues

**AWS CLI not configured**
```bash
aws configure
# Enter Access Key ID, Secret Access Key, Region
```

**Can't connect to Neon**
```bash
# Ensure connection string has ?sslmode=require
# Check Neon dashboard for project status
```

**Alembic migration failed**
```bash
# Reset database (DEV ONLY!)
rm data/trades.db
alembic upgrade head
```

**Terraform state locked**
```bash
terraform force-unlock <LOCK_ID>
```

**Python imports failing**
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

**See [SETUP_GUIDE.md](SETUP_GUIDE.md#8-troubleshooting) for more solutions**

---

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Follow [SETUP_GUIDE.md](SETUP_GUIDE.md)
3. Create feature branch: `git checkout -b feature/amazing-feature`
4. Make changes and test
5. Commit: `git commit -m 'Add amazing feature'`
6. Push: `git push origin feature/amazing-feature`
7. Open Pull Request

### Code Standards
- Python 3.11+ with type hints
- Black formatter
- Ruff linter
- 80% test coverage minimum
- Async/await for I/O operations

---

## 📞 Support

**Questions?** Check:
1. [SETUP_GUIDE.md](SETUP_GUIDE.md) - Setup help
2. [MIGRATION_PROGRESS.md](MIGRATION_PROGRESS.md) - Implementation details
3. [infrastructure/README.md](infrastructure/README.md) - Terraform help

**Still stuck?** Open an issue with:
- What you tried
- Error message (full output)
- Operating system
- AWS region

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details

---

## 🎯 Roadmap

**Q1 2025**
- ✅ Phase 1: Foundation
- 🔄 Phase 2: Storage Layer
- ⏳ Phase 3: Lambda Functions

**Q2 2025**
- Phase 4: API Async Conversion
- Phase 5: CloudFlare Edge
- Phase 6: CI/CD
- Phase 7: Monitoring

**Q3 2025**
- Performance optimization
- Advanced features (real-time data, ML signals)
- Mobile app (React Native)

---

**Last Updated:** January 12, 2025
**Status:** Phase 1 Complete ✅
**Next Milestone:** S3 Cache Adapter

---

Made with ⚡ by the Potential Parakeet Team
