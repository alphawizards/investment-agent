# Coding Standards

## Purpose
This document defines the coding standards, conventions, and best practices for the quantitative trading platform. All contributors must follow these standards to ensure consistency, maintainability, and quality.

---

## 📁 Project Structure Standards

### Directory Organization

The project follows a modular structure with clear separation of concerns:

```
potential-parakeet/
├── strategy/              # Quantitative strategy engine (Python)
│   ├── quant2/           # Advanced strategies (ML, regime detection, stat arb)
│   ├── olps/             # Online portfolio selection
│   └── pipeline/         # Modular trading pipeline
├── backend/              # FastAPI REST API
│   ├── database/         # SQLAlchemy models
│   ├── routers/          # API endpoints
│   └── services/         # Business logic
├── dashboard/            # React TypeScript frontend
│   └── src/
│       ├── components/   # React components
│       ├── hooks/        # Custom React hooks
│       └── types/        # TypeScript type definitions
├── tests/                # Test suites
├── data/                 # Data files and databases
├── cache/                # Parquet cache for fast data loading
└── reports/              # Generated analysis reports
```

**Standards**:
- Each module must have a clear, single responsibility
- Related functionality should be grouped in subdirectories
- No circular dependencies between modules
- Public APIs should be exposed through `__init__.py` (Python) or `index.ts` (TypeScript)

---

## 🐍 Python Standards

### File Naming
- Use `snake_case` for all Python files: `data_loader.py`, `backtest_engine.py`
- Test files prefixed with `test_`: `test_signals.py`
- Module names should be descriptive and concise

### Code Style
Follow PEP 8 with these specific guidelines:

**Formatting**:
- Use Black formatter with default settings (88 character line length)
- Use ruff for linting with strict settings
- 4 spaces for indentation (no tabs)
- 2 blank lines between top-level functions and classes
- 1 blank line between methods in a class

**Naming Conventions**:
```python
# Variables and functions: snake_case
portfolio_value = 100000
def calculate_sharpe_ratio(returns: pd.Series) -> float:
    pass

# Classes: PascalCase
class MomentumStrategy:
    pass

# Constants: UPPER_SNAKE_CASE
MAX_POSITION_SIZE = 0.10
DEFAULT_LOOKBACK_DAYS = 252

# Private members: leading underscore
def _internal_helper():
    pass
```

### Import Organization
Organize imports in three groups, separated by blank lines:

```python
# Standard library
import os
import sys
from datetime import datetime
from typing import List, Dict, Optional

# Third-party packages
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException

# Local modules
from strategy.signals import calculate_momentum
from backend.database.models import Trade
```

**Standards**:
- Use absolute imports from project root
- Avoid wildcard imports (`from module import *`)
- Sort imports alphabetically within each group
- Use `isort` to automate import sorting

### Type Hints
All functions must have complete type hints:

```python
from typing import List, Dict, Optional, Union
import pandas as pd

def calculate_portfolio_weights(
    returns: pd.DataFrame,
    risk_free_rate: float = 0.02,
    max_weight: float = 0.20
) -> Dict[str, float]:
    """
    Calculate optimal portfolio weights using HRP.
    
    Args:
        returns: DataFrame of asset returns (index: dates, columns: tickers)
        risk_free_rate: Annual risk-free rate for Sharpe calculation
        max_weight: Maximum weight per asset (0.0 to 1.0)
    
    Returns:
        Dictionary mapping ticker to weight
    
    Raises:
        ValueError: If returns DataFrame is empty or contains NaN
    """
    pass
```

**Standards**:
- Use `mypy` in strict mode
- No `Any` types unless absolutely necessary (document why)
- Use `Optional[T]` for nullable values
- Use `Union[T1, T2]` for multiple possible types
- Financial amounts should be typed as `Decimal` or `float` with comments

### Documentation
All public functions, classes, and modules must have docstrings:

**Function Docstrings** (Google style):
```python
def backtest_strategy(
    signals: pd.DataFrame,
    prices: pd.DataFrame,
    initial_capital: float = 100000.0
) -> Dict[str, float]:
    """
    Backtest a trading strategy with realistic cost modeling.
    
    This function simulates trading based on provided signals,
    accounting for transaction costs, slippage, and market impact.
    
    Args:
        signals: DataFrame with trading signals (-1, 0, 1) for each asset
        prices: DataFrame with historical prices (aligned with signals)
        initial_capital: Starting portfolio value in AUD
    
    Returns:
        Dictionary containing performance metrics:
            - 'total_return': Cumulative return (%)
            - 'sharpe_ratio': Risk-adjusted return
            - 'max_drawdown': Maximum peak-to-trough decline (%)
            - 'num_trades': Total number of trades executed
    
    Raises:
        ValueError: If signals and prices have mismatched indices
        ValueError: If initial_capital is not positive
    
    Example:
        >>> signals = generate_momentum_signals(prices)
        >>> results = backtest_strategy(signals, prices, 100000)
        >>> print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
    """
    pass
```

**Class Docstrings**:
```python
class OLMARStrategy:
    """
    Online Moving Average Reversion strategy implementation.
    
    This strategy exploits mean reversion by taking positions
    when prices deviate from moving averages, with online
    learning to adapt parameters dynamically.
    
    Attributes:
        window: Moving average window size (default: 5)
        epsilon: Reversion threshold (default: 10)
        alpha: Learning rate (default: 0.5)
    
    References:
        Li, B., & Hoi, S. C. (2012). Online portfolio selection with
        moving average reversion. ICML.
    """
    pass
```

### Error Handling
Proper error handling is critical for production systems:

```python
# ❌ Bad: Bare except
try:
    data = fetch_market_data(ticker)
except:
    pass

# ✅ Good: Specific exception handling
try:
    data = fetch_market_data(ticker)
except requests.HTTPError as e:
    logger.error(f"Failed to fetch {ticker}: {e}")
    raise DataFetchError(f"HTTP error for {ticker}") from e
except requests.Timeout:
    logger.warning(f"Timeout fetching {ticker}, retrying...")
    return retry_with_backoff(fetch_market_data, ticker)
```

**Standards**:
- Always specify exception types
- Log errors with appropriate severity
- Re-raise exceptions with context when needed
- Use custom exception classes for domain-specific errors
- Clean up resources with context managers (`with` statements)

### Financial Code Standards

**Currency Handling**:
```python
from decimal import Decimal, ROUND_HALF_UP

# ✅ Use Decimal for money calculations
portfolio_value = Decimal('100000.00')
trade_cost = Decimal('3.00')
net_value = portfolio_value - trade_cost

# ✅ Round to appropriate precision
price = Decimal('123.456789').quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
```

**Timezone Handling**:
```python
import pandas as pd
from datetime import datetime
import pytz

# ✅ Always use timezone-aware datetimes
timestamp = pd.Timestamp('2024-01-01 09:30:00', tz='America/New_York')
utc_timestamp = timestamp.tz_convert('UTC')

# ❌ Bad: Timezone-naive datetime
naive_dt = datetime(2024, 1, 1, 9, 30)  # Ambiguous!
```

**Vectorized Operations**:
```python
# ❌ Bad: Loop over DataFrame
returns = []
for i in range(len(prices) - 1):
    ret = (prices.iloc[i+1] - prices.iloc[i]) / prices.iloc[i]
    returns.append(ret)

# ✅ Good: Vectorized operation
returns = prices.pct_change().dropna()
```

---

## 📘 TypeScript Standards

### File Naming
- Use `camelCase` for files: `tradeHistory.ts`, `portfolioMetrics.ts`
- React components use `PascalCase`: `TradeTable.tsx`, `MetricCard.tsx`
- Test files use `.test.ts` or `.spec.ts` suffix

### Code Style

**Naming Conventions**:
```typescript
// Variables and functions: camelCase
const portfolioValue = 100000;
function calculateSharpeRatio(returns: number[]): number {
  // ...
}

// Classes and interfaces: PascalCase
class MomentumStrategy {
  // ...
}

interface TradeRecord {
  ticker: string;
  quantity: number;
  price: number;
}

// Constants: UPPER_SNAKE_CASE
const MAX_POSITION_SIZE = 0.10;
const DEFAULT_LOOKBACK_DAYS = 252;

// Type aliases: PascalCase
type PortfolioWeights = Record<string, number>;
```

### TypeScript Configuration
Always use strict mode in `tsconfig.json`:

```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true
  }
}
```

### Type Definitions
Prefer interfaces for object shapes, types for unions:

```typescript
// ✅ Interface for object shapes
interface Trade {
  id: string;
  ticker: string;
  quantity: number;
  price: number;
  timestamp: Date;
  type: 'BUY' | 'SELL';
}

// ✅ Type for unions and complex types
type TradeStatus = 'PENDING' | 'EXECUTED' | 'CANCELLED' | 'FAILED';
type NumericValue = number | null | undefined;

// ✅ Avoid 'any' - use 'unknown' if type is truly unknown
function parseJSON(json: string): unknown {
  return JSON.parse(json);
}
```

### React Component Standards

**Functional Components with TypeScript**:
```typescript
import React, { useState, useCallback, useMemo } from 'react';

interface TradeTableProps {
  trades: Trade[];
  onTradeSelect?: (trade: Trade) => void;
  maxRows?: number;
}

export const TradeTable: React.FC<TradeTableProps> = ({
  trades,
  onTradeSelect,
  maxRows = 100
}) => {
  const [sortColumn, setSortColumn] = useState<keyof Trade>('timestamp');
  
  // ✅ Memoize expensive computations
  const sortedTrades = useMemo(() => {
    return [...trades].sort((a, b) => 
      a[sortColumn] > b[sortColumn] ? 1 : -1
    );
  }, [trades, sortColumn]);
  
  // ✅ Use useCallback for event handlers
  const handleRowClick = useCallback((trade: Trade) => {
    onTradeSelect?.(trade);
  }, [onTradeSelect]);
  
  return (
    <table>
      {/* Component JSX */}
    </table>
  );
};
```

**Component Organization**:
1. Imports
2. Type definitions
3. Component definition
4. Hooks (useState, useEffect, etc.)
5. Derived state (useMemo)
6. Event handlers (useCallback)
7. Render logic
8. Export

---

## 🧪 Testing Standards

### Test File Organization
```
tests/
├── unit/                 # Unit tests for individual functions
│   ├── test_signals.py
│   └── test_optimizer.py
├── integration/          # Integration tests for API endpoints
│   └── test_api.py
└── fixtures/             # Shared test fixtures
    └── sample_data.py
```

### Python Testing (pytest)

**Test Naming**:
```python
# ✅ Descriptive test names
def test_calculate_momentum_returns_positive_values_for_uptrend():
    pass

def test_calculate_momentum_handles_missing_data_gracefully():
    pass

def test_calculate_momentum_raises_error_for_empty_input():
    pass
```

**Test Structure (Arrange-Act-Assert)**:
```python
def test_backtest_strategy_with_realistic_costs():
    # Arrange: Set up test data and expected results
    prices = pd.DataFrame({
        'AAPL': [100, 105, 103, 108],
        'MSFT': [200, 198, 202, 205]
    })
    signals = pd.DataFrame({
        'AAPL': [1, 1, -1, 0],
        'MSFT': [1, -1, 1, 1]
    })
    initial_capital = 100000.0
    
    # Act: Execute the function under test
    results = backtest_strategy(signals, prices, initial_capital)
    
    # Assert: Verify the results
    assert results['total_return'] > 0
    assert 0 < results['sharpe_ratio'] < 5
    assert results['num_trades'] == 4
```

**Fixtures**:
```python
import pytest

@pytest.fixture
def sample_prices():
    """Fixture providing sample price data for testing."""
    return pd.DataFrame({
        'AAPL': [100, 105, 103, 108, 110],
        'MSFT': [200, 198, 202, 205, 207]
    }, index=pd.date_range('2024-01-01', periods=5))

def test_momentum_calculation(sample_prices):
    momentum = calculate_momentum(sample_prices, window=3)
    assert not momentum.isna().all()
```

### TypeScript Testing (Jest/Vitest)

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { TradeTable } from './TradeTable';

describe('TradeTable', () => {
  const mockTrades: Trade[] = [
    { id: '1', ticker: 'AAPL', quantity: 100, price: 150, timestamp: new Date(), type: 'BUY' },
    { id: '2', ticker: 'MSFT', quantity: 50, price: 300, timestamp: new Date(), type: 'SELL' }
  ];

  it('renders all trades', () => {
    render(<TradeTable trades={mockTrades} />);
    expect(screen.getByText('AAPL')).toBeInTheDocument();
    expect(screen.getByText('MSFT')).toBeInTheDocument();
  });

  it('calls onTradeSelect when row is clicked', () => {
    const handleSelect = jest.fn();
    render(<TradeTable trades={mockTrades} onTradeSelect={handleSelect} />);
    
    fireEvent.click(screen.getByText('AAPL'));
    expect(handleSelect).toHaveBeenCalledWith(mockTrades[0]);
  });
});
```

---

## 🔄 Git Workflow Standards

### Branch Naming
```
feature/add-olmar-strategy
bugfix/fix-timezone-handling
hotfix/critical-api-error
refactor/optimize-data-loader
docs/update-readme
```

**Format**: `<type>/<description-in-kebab-case>`

**Types**:
- `feature/`: New functionality
- `bugfix/`: Bug fixes
- `hotfix/`: Critical production fixes
- `refactor/`: Code improvements without behavior change
- `docs/`: Documentation updates
- `test/`: Test additions or fixes

### Commit Messages
Follow conventional commits format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Examples**:
```
feat(strategy): add OLMAR online learning strategy

Implement Online Moving Average Reversion (OLMAR) strategy
with kernel-based mean reversion detection. Includes:
- Gaussian and polynomial kernel support
- Dynamic parameter adjustment
- Comprehensive backtesting

Closes #42

---

fix(data-loader): handle timezone conversion for AUD normalization

Previously, currency conversion occurred on timezone-naive
datetimes, causing incorrect volatility calculations.

Now ensures all timestamps are UTC before FX conversion.

Fixes #58

---

refactor(backtest): optimize vectorized return calculations

Replace iterative return calculation with pandas pct_change(),
reducing backtest time from 45s to 2s for 20-year history.

Performance improvement: 22.5x speedup
```

### Pull Request Standards

**PR Title**: Same format as commit messages
```
feat(api): add trade history endpoint with pagination
```

**PR Description Template**:
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests pass locally

## Related Issues
Closes #42
Related to #38
```

---

## 📊 Performance Standards

### Python Performance
- Use vectorized operations (pandas, numpy) instead of loops
- Profile code with `cProfile` or `line_profiler` before optimizing
- Cache expensive computations with `@lru_cache` or custom caching
- Use generators for large datasets
- Prefer `itertools` for efficient iteration

### TypeScript/React Performance
- Memoize expensive computations with `useMemo`
- Memoize callbacks with `useCallback`
- Use `React.memo` for components that don't need frequent re-renders
- Virtualize large lists (react-window, react-virtualized)
- Lazy load components with `React.lazy` and `Suspense`
- Keep bundle size < 500KB gzipped

### Database Performance
- Add indexes on frequently queried columns
- Use pagination for large result sets
- Avoid N+1 queries (use joins or eager loading)
- Use connection pooling
- Monitor slow queries and optimize

---

## 🔒 Security Standards

### Secrets Management
- Never commit secrets to Git
- Use environment variables for all secrets
- Use `.env` files locally (add to `.gitignore`)
- Use secret management services in production (AWS Secrets Manager, etc.)
- Rotate secrets regularly

### Input Validation
- Validate all user inputs with Pydantic (Python) or Zod (TypeScript)
- Sanitize inputs before database queries
- Use parameterized queries (never string concatenation)
- Validate file uploads (type, size, content)
- Rate limit API endpoints

### API Security
- Use HTTPS in production
- Implement authentication (JWT, OAuth)
- Implement authorization (role-based access control)
- Set appropriate CORS policies
- Log security events

---

## 📝 Documentation Standards

### Code Comments
- Explain **why**, not **what** (code should be self-explanatory)
- Document complex algorithms with references
- Add TODO comments with issue numbers
- Remove commented-out code (use Git history instead)

```python
# ✅ Good: Explains why
# Use 252 trading days for annualization (US market standard)
annual_return = daily_return * 252

# ❌ Bad: Explains what (obvious from code)
# Multiply daily return by 252
annual_return = daily_return * 252
```

### README Standards
Every module should have a README with:
- Purpose and overview
- Installation/setup instructions
- Usage examples
- Configuration options
- API documentation (if applicable)
- Contributing guidelines

---

## 🚀 Deployment Standards

### Pre-Deployment Checklist
- [ ] All tests passing (unit, integration, end-to-end)
- [ ] Code review approved
- [ ] Documentation updated
- [ ] Changelog updated
- [ ] Database migrations tested
- [ ] Environment variables configured
- [ ] Monitoring and logging configured
- [ ] Rollback plan documented

### Environment Configuration
- Use separate environments: `development`, `staging`, `production`
- Never use production data in development
- Use feature flags for gradual rollouts
- Monitor error rates and performance metrics

---

**Last Updated**: 2024-12-28  
**Version**: 1.0  
**Maintainer**: Development Team
