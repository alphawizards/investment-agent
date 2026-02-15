# 🗺️ Functional Data Flow & Architecture Map

This document outlines the end-to-end journey of data within the `potential-parakeet` ecosystem.

> [!NOTE]
> **Mermaid Support**: If diagrams appear as code, ensure your Markdown viewer (VS Code, GitHub, etc.) has Mermaid rendering enabled.

---

## 📂 Project Structure

A detailed view of the reorganized codebase and component responsibilities:

```text
potential-parakeet/
├── strategy/                   # 🧠 Core Quant Logic & Calculations
│   ├── quant2/                 # Advanced Quant 2.0 (OLMAR, StatArb, Meta-Labeling)
│   ├── pipeline/               # Modular Pipeline (Data, Signal, Allocation layers)
│   ├── olps/                   # Online Portfolio Selection Models
│   ├── stock_universe.py       # Universe definitions (SPX, ASX, NASDAQ)
│   └── fast_data_loader.py     # Incremental data fetching engine
│
├── dashboard/                  # 📊 Frontend Web Application (React/Vite)
│   ├── src/components/         # UI Components (Charts, Alpha Matrix, Layout)
│   ├── src/hooks/              # Custom Hooks (useMetrics, useTrades)
│   └── src/services/           # API Client & Data Transformation
│
├── backend/                    # ⚙️ FastAPI REST API
│   ├── routers/                # API Endpoints (trades, data, strategies, scanner)
│   ├── database/               # SQLAlchemy Models & Bi-temporal Schema
│   ├── services/               # Business logic & external API wrappers
│   └── main.py                 # API Entry point
│
├── scripts/                    # 🛠️ Data & Maintenance Utilities
│   ├── refresh_data.py         # Daily unified data spinner script
│   ├── fetch_*.py              # Individual data source fetchers (Tiingo/yFinance)
│   └── verify_*.py             # Cache and data integrity checkers
│
├── infrastructure/             # ☁️ DevOps & Cloud Setup
│   └── terraform/              # AWS IaC (Lambda, API Gateway, S3, IAM)
│
├── docs/                       # 📚 Documentation & Research
│   ├── testing/                # E2E and Unit Test Guides
│   └── architecture_map.md     # [Current Document]
│
├── tests/                      # 🧪 Automated Test Suites (Pytest)
├── examples/                   # 💡 Demo Scripts for Research & Onboarding
└── cache/                      # ⚡ Local Parquet Storage (Optimized Time-Series)
```

---

## 🔄 Visual Data Flow Map

This diagram tracks the lifecycle of market data from the provider to the user's screen.

![Institutional Data Flow](file:///C:/Users/ckr_4/.gemini/antigravity/brain/5ea39c76-db6c-4141-8879-db0847d2e340/architecture_data_flow_map_1768283422779.png)

```mermaid
flowchart LR
    subgraph Ingestion ["1. INGESTION"]
        T(Tiingo) & Y(yFinance) --> |Raw Data| L[Lambda / Ingest Service]
    end

    subgraph Processing ["2. PROCESSING & STORAGE"]
        L --> |Normalization| P[FastAPI Engine]
        P --> |Structured| DB[(PostgreSQL)]
        P --> |Cache| S3[Parquet Cache]
    end

    subgraph Intelligence ["3. STRATEGY ENGINE"]
        DB & S3 --> |Time Series| Q[Quant Logic]
        Q --> |Metrics| R[API Router]
    end

    subgraph Presentation ["4. PRESENTATION"]
        R --> |JSON| UI[React Dashboard]
        UI --> |Visuals| User([User View])
    end

    style Ingestion fill:#f9f,stroke:#333,stroke-width:2px
    style Processing fill:#bbf,stroke:#333,stroke-width:2px
    style Intelligence fill:#bfb,stroke:#333,stroke-width:2px
    style Presentation fill:#fdb,stroke:#333,stroke-width:2px
```

---

## 🏗️ High-Level Architecture

System-wide component interaction and infrastructure layers.

```mermaid
graph TD
    User([User]) <--> Dashboard[React Dashboard]
    Dashboard <--> Cloudflare[Cloudflare Pages / Access]
    Cloudflare <--> APIGateway[AWS API Gateway]
    
    subgraph backend ["Backend (FastAPI / Lambdas)"]
        APIGateway <--> Router[API Routers]
        Router <--> QuantLogic[Quant / Strategy Engine]
        Router <--> DataService[Data Ingestion Service]
        QuantLogic <--> DB[(PostgreSQL / SQLAlchemy)]
        DataService <--> DB
    end
    
    subgraph external ["External Data Providers"]
        DataService <--> Tiingo[Tiingo API]
        DataService <--> yFinance[yFinance API]
    end
    
    subgraph infra ["Infrastructure & Storage"]
        Router <--> S3[S3 Cache / Artifacts]
        Router <--> Logs[CloudWatch Logs]
    end

    Schedule[EventBridge Schedule] --> DataService
```

---

## 🧠 Strategy Pipeline Detail

Visualizing the modular layers within `strategy/pipeline/`.

```mermaid
flowchart TD
    D[Data Loader] --> S[Signal Generator]
    S --> A[Allocation Engine]
    A --> R[Risk Overlay]
    R --> O[Output Generation]
    
    subgraph strategy/pipeline/
        D
        S
        A
        R
    end
```

---

## ⚡ The Data Journey

Detailed breakdown of the stages shown in the visual maps above.

### 1. User Interaction (The Trigger)
The user interacts with the **React Dashboard** (Vite-powered).
*   **Examples**: Viewing trade history, triggering a new backtest, or searching for stocks in the alpha matrix.
*   **Result**: The frontend generates an HTTP request to the API.

### 2. Security & Routing
The request passes through **Cloudflare Access** (Zero Trust) for authentication and is routed via **AWS API Gateway** to the unified **FastAPI backend**.

### 3. Backend Processing (The Engine)
Depending on the request, data flows through specific **Routers**:
*   **Trade Flow**: Uses `routers/trades.py` to perform CRUD operations on executed trades stored in the database.
*   **Strategy Flow**: Uses `routers/strategies.py` and the `quant/` engine to run backtests, calculate metrics (Sharpe, P&L), and generate performance charts.
*   **Metrics Flow**: `routers/dashboard.py` aggregates data from trades and snapshots to show the "Top-Line" portfolio performance.

### 4. Data Ingestion (The Source)
Market data is the primary fuel for the system:
*   **Scheduled Ingestion**: **AWS EventBridge** triggers Lambdas to fetch the latest OHLCV data from **Tiingo** (Premium US) or **yFinance** (ASX fallback).
*   **Storage**: Data is normalized and stored in the **Database** for SQL queries or **S3** for larger analysis artifacts.

### 5. Final Result (The Output)
1.  Quant logic transforms raw price data into trading signals and performance metrics.
2.  The API returns JSON responses containing formatted data (Currency, Percentages, Chart Series).
3.  The **Dashboard** visualizes this data using **Recharts** and **Tailwind CSS**.

---

## 🔐 Core Data Models

- **`Trade`**: The atomic unit of execution (Ticker, Price, Qty, P&L).
- **`PortfolioSnapshot`**: A point-in-time "save game" of the entire portfolio's value and risk metrics.
- **`IndexConstituent`**: Tracks what was in an index (like SPX500) to prevent survivorship bias in strategies.
