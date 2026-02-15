# Common Antipatterns

## Purpose
This document catalogs common antipatterns, code smells, and problematic practices to avoid in the quantitative trading platform. Use this as a reference during code reviews to identify and prevent recurring issues.

---

## 🐍 Python Antipatterns

### 1. Mutable Default Arguments

**Antipattern**:
```python
def add_trade(trade, portfolio=[]):
    portfolio.append(trade)
    return portfolio
```

**Problem**: The default list is created once and shared across all function calls, leading to unexpected state accumulation.

**Solution**:
```python
def add_trade(trade, portfolio=None):
    if portfolio is None:
        portfolio = []
    portfolio.append(trade)
    return portfolio
```

---

### 2. Bare Except Clauses

**Antipattern**:
```python
try:
    data = fetch_market_data(ticker)
except:
    return None
```

**Problem**: Catches all exceptions including `KeyboardInterrupt` and `SystemExit`, making debugging impossible and hiding critical errors.

**Solution**:
```python
try:
    data = fetch_market_data(ticker)
except requests.HTTPError as e:
    logger.error(f"HTTP error fetching {ticker}: {e}")
    return None
except requests.Timeout:
    logger.warning(f"Timeout fetching {ticker}")
    return None
```

---

### 3. Global Variables for State

**Antipattern**:
```python
portfolio_value = 100000

def update_portfolio(trade):
    global portfolio_value
    portfolio_value += trade.value
```

**Problem**: Makes code difficult to test, creates hidden dependencies, and causes issues in concurrent environments.

**Solution**:
```python
class Portfolio:
    def __init__(self, initial_value: float = 100000):
        self.value = initial_value
    
    def update(self, trade: Trade) -> None:
        self.value += trade.value
```

---

### 4. String Concatenation in Loops

**Antipattern**:
```python
result = ""
for ticker in tickers:
    result += ticker + ","
```

**Problem**: Creates a new string object on each iteration, resulting in O(n²) time complexity.

**Solution**:
```python
result = ",".join(tickers)
```

---

### 5. Using `import *`

**Antipattern**:
```python
from pandas import *
from numpy import *
```

**Problem**: Pollutes namespace, makes it unclear where functions come from, and can cause name collisions.

**Solution**:
```python
import pandas as pd
import numpy as np
```

---

### 6. Ignoring Return Values

**Antipattern**:
```python
df.sort_values('price')  # Returns new DataFrame, original unchanged
```

**Problem**: Many pandas operations return new objects and don't modify in place.

**Solution**:
```python
df = df.sort_values('price')
# Or use inplace=True if appropriate
df.sort_values('price', inplace=True)
```

---

### 7. Iterating Over DataFrame Rows

**Antipattern**:
```python
returns = []
for i in range(len(prices)):
    ret = (prices.iloc[i] - prices.iloc[i-1]) / prices.iloc[i-1]
    returns.append(ret)
```

**Problem**: Extremely slow for large datasets (100-1000x slower than vectorized operations).

**Solution**:
```python
returns = prices.pct_change()
```

---

### 8. Not Using Context Managers

**Antipattern**:
```python
f = open('data.csv', 'r')
data = f.read()
f.close()  # May not execute if exception occurs
```

**Problem**: Resources may not be properly cleaned up if an exception occurs.

**Solution**:
```python
with open('data.csv', 'r') as f:
    data = f.read()
```

---

### 9. Checking Type with `type()`

**Antipattern**:
```python
if type(value) == int:
    process_integer(value)
```

**Problem**: Doesn't work with inheritance, breaks duck typing.

**Solution**:
```python
if isinstance(value, int):
    process_integer(value)
```

---

### 10. Not Using List Comprehensions

**Antipattern**:
```python
squared = []
for x in numbers:
    squared.append(x ** 2)
```

**Problem**: More verbose and slower than list comprehensions.

**Solution**:
```python
squared = [x ** 2 for x in numbers]
```

---

## 📘 TypeScript Antipatterns

### 1. Using `any` Type

**Antipattern**:
```typescript
function processData(data: any): any {
    return data.value * 2;
}
```

**Problem**: Defeats the purpose of TypeScript, no type safety.

**Solution**:
```typescript
interface DataPoint {
    value: number;
}

function processData(data: DataPoint): number {
    return data.value * 2;
}

// If type is truly unknown:
function processUnknown(data: unknown): number {
    if (typeof data === 'object' && data !== null && 'value' in data) {
        const typed = data as DataPoint;
        return typed.value * 2;
    }
    throw new Error('Invalid data format');
}
```

---

### 2. Non-Null Assertion Without Validation

**Antipattern**:
```typescript
const element = document.getElementById('chart')!;
element.style.width = '100%';  // May crash if element is null
```

**Problem**: Bypasses TypeScript's null checking, can cause runtime errors.

**Solution**:
```typescript
const element = document.getElementById('chart');
if (element) {
    element.style.width = '100%';
} else {
    console.error('Chart element not found');
}
```

---

### 3. Ignoring TypeScript Errors with `@ts-ignore`

**Antipattern**:
```typescript
// @ts-ignore
const result = someFunction(invalidArg);
```

**Problem**: Hides type errors that may indicate real bugs.

**Solution**:
```typescript
// If you must ignore, use @ts-expect-error with explanation
// @ts-expect-error - Legacy API requires string, will be fixed in v2
const result = someFunction(invalidArg);

// Better: Fix the type issue
const result = someFunction(String(invalidArg));
```

---

### 4. Type Assertions Without Validation

**Antipattern**:
```typescript
const data = JSON.parse(response) as Trade[];
```

**Problem**: No runtime validation that the data actually matches the type.

**Solution**:
```typescript
import { z } from 'zod';

const TradeSchema = z.object({
    ticker: z.string(),
    quantity: z.number(),
    price: z.number(),
});

const TradesSchema = z.array(TradeSchema);

const data = TradesSchema.parse(JSON.parse(response));
```

---

### 5. Empty Interfaces

**Antipattern**:
```typescript
interface EmptyProps {}
```

**Problem**: Serves no purpose, use `type` or remove entirely.

**Solution**:
```typescript
// If truly no props needed:
type EmptyProps = Record<string, never>;

// Or just use an empty object type:
const Component: React.FC<{}> = () => { ... };
```

---

## ⚛️ React Antipatterns

### 1. Inline Function Definitions in JSX

**Antipattern**:
```typescript
function TradeTable({ trades }: Props) {
    return (
        <div>
            {trades.map(trade => (
                <button onClick={() => handleClick(trade.id)}>
                    {trade.ticker}
                </button>
            ))}
        </div>
    );
}
```

**Problem**: Creates a new function on every render, causing unnecessary re-renders of child components.

**Solution**:
```typescript
function TradeTable({ trades }: Props) {
    const handleClick = useCallback((id: string) => {
        // Handle click
    }, []);
    
    return (
        <div>
            {trades.map(trade => (
                <TradeRow 
                    key={trade.id}
                    trade={trade}
                    onClick={handleClick}
                />
            ))}
        </div>
    );
}
```

---

### 2. Missing Dependencies in useEffect

**Antipattern**:
```typescript
function Component({ userId }: Props) {
    const [data, setData] = useState(null);
    
    useEffect(() => {
        fetchData(userId).then(setData);
    }, []); // Missing userId dependency!
    
    return <div>{data}</div>;
}
```

**Problem**: Effect doesn't re-run when `userId` changes, showing stale data.

**Solution**:
```typescript
function Component({ userId }: Props) {
    const [data, setData] = useState(null);
    
    useEffect(() => {
        fetchData(userId).then(setData);
    }, [userId]); // Correct dependencies
    
    return <div>{data}</div>;
}
```

---

### 3. Using Index as Key

**Antipattern**:
```typescript
{trades.map((trade, index) => (
    <TradeRow key={index} trade={trade} />
))}
```

**Problem**: Causes incorrect re-rendering when list order changes, leading to bugs and performance issues.

**Solution**:
```typescript
{trades.map(trade => (
    <TradeRow key={trade.id} trade={trade} />
))}
```

---

### 4. Prop Drilling

**Antipattern**:
```typescript
function App() {
    const [user, setUser] = useState(null);
    return <Dashboard user={user} setUser={setUser} />;
}

function Dashboard({ user, setUser }) {
    return <Sidebar user={user} setUser={setUser} />;
}

function Sidebar({ user, setUser }) {
    return <UserMenu user={user} setUser={setUser} />;
}

function UserMenu({ user, setUser }) {
    // Finally use the props here
}
```

**Problem**: Props passed through many intermediate components that don't use them.

**Solution**:
```typescript
// Use Context
const UserContext = createContext<UserContextType | null>(null);

function App() {
    const [user, setUser] = useState(null);
    return (
        <UserContext.Provider value={{ user, setUser }}>
            <Dashboard />
        </UserContext.Provider>
    );
}

function UserMenu() {
    const { user, setUser } = useContext(UserContext);
    // Use directly without prop drilling
}
```

---

### 5. Not Cleaning Up Effects

**Antipattern**:
```typescript
useEffect(() => {
    const interval = setInterval(() => {
        fetchLatestPrices();
    }, 1000);
}, []);
```

**Problem**: Interval continues running after component unmounts, causing memory leaks.

**Solution**:
```typescript
useEffect(() => {
    const interval = setInterval(() => {
        fetchLatestPrices();
    }, 1000);
    
    return () => clearInterval(interval); // Cleanup
}, []);
```

---

### 6. Unnecessary State

**Antipattern**:
```typescript
function Component({ trades }: Props) {
    const [trades, setTrades] = useState(props.trades);
    const [tradeCount, setTradeCount] = useState(trades.length);
    
    useEffect(() => {
        setTradeCount(trades.length);
    }, [trades]);
}
```

**Problem**: `tradeCount` is derived from `trades`, doesn't need to be state.

**Solution**:
```typescript
function Component({ trades }: Props) {
    const tradeCount = trades.length; // Just compute it
}
```

---

## 💰 Financial Domain Antipatterns

### 1. Floating-Point Arithmetic for Money

**Antipattern**:
```python
portfolio_value = 100000.00
trade_cost = 3.00
net_value = portfolio_value - trade_cost  # 99997.0 (may have precision errors)

# Worse:
price = 0.1 + 0.2  # 0.30000000000000004
```

**Problem**: Floating-point arithmetic has precision errors that accumulate over many calculations.

**Solution**:
```python
from decimal import Decimal, ROUND_HALF_UP

portfolio_value = Decimal('100000.00')
trade_cost = Decimal('3.00')
net_value = portfolio_value - trade_cost  # Exact: 99997.00

# For display:
display_value = float(net_value)
```

---

### 2. Timezone-Naive Datetimes

**Antipattern**:
```python
from datetime import datetime

market_open = datetime(2024, 1, 1, 9, 30)  # Which timezone?
```

**Problem**: Ambiguous time representation, causes errors when converting between timezones or comparing times.

**Solution**:
```python
import pandas as pd
import pytz

# Explicit timezone
market_open = pd.Timestamp('2024-01-01 09:30:00', tz='America/New_York')

# Convert to UTC for storage
utc_open = market_open.tz_convert('UTC')
```

---

### 3. Look-Ahead Bias in Backtesting

**Antipattern**:
```python
def generate_signals(prices: pd.DataFrame) -> pd.DataFrame:
    # Calculate moving average using future data!
    ma = prices.rolling(window=20, center=True).mean()
    signals = (prices > ma).astype(int)
    return signals
```

**Problem**: Uses future data (center=True) to make past decisions, inflating backtest performance.

**Solution**:
```python
def generate_signals(prices: pd.DataFrame) -> pd.DataFrame:
    # Only use past data
    ma = prices.rolling(window=20).mean()
    signals = (prices > ma).astype(int)
    return signals
```

---

### 4. Survivorship Bias

**Antipattern**:
```python
# Only fetch currently listed S&P 500 stocks
tickers = get_current_sp500_tickers()
historical_data = fetch_data(tickers, start='2000-01-01')
```

**Problem**: Excludes delisted companies, inflating historical performance (survivors performed better by definition).

**Solution**:
```python
# Fetch historical constituents at each point in time
def get_historical_universe(date: pd.Timestamp) -> List[str]:
    """Get stocks that were in the index on the given date."""
    return fetch_historical_constituents(date)

# Or use a dataset that includes delisted stocks
historical_data = fetch_data_with_delisted(start='2000-01-01')
```

---

### 5. Ignoring Transaction Costs

**Antipattern**:
```python
def backtest(signals, prices):
    returns = signals.shift(1) * prices.pct_change()
    total_return = returns.sum()
    return total_return
```

**Problem**: Ignores transaction costs, slippage, and market impact, overstating performance.

**Solution**:
```python
def backtest(signals, prices, cost_per_trade=3.0):
    returns = signals.shift(1) * prices.pct_change()
    
    # Count trades (signal changes)
    trades = signals.diff().abs().sum()
    
    # Subtract costs
    total_return = returns.sum() - (trades * cost_per_trade / portfolio_value)
    return total_return
```

---

### 6. Currency Conversion After Statistical Calculations

**Antipattern**:
```python
# Calculate volatility in USD
usd_prices = fetch_prices('AAPL')
volatility = usd_prices.pct_change().std()

# Convert to AUD (WRONG!)
aud_volatility = volatility * usd_aud_rate
```

**Problem**: Volatility is not linear with exchange rates. Must convert prices first, then calculate statistics.

**Solution**:
```python
# Convert prices to AUD first
usd_prices = fetch_prices('AAPL')
usd_aud_rate = fetch_fx_rate('USD/AUD')
aud_prices = usd_prices * usd_aud_rate

# Then calculate volatility
volatility = aud_prices.pct_change().std()
```

---

### 7. Not Handling Corporate Actions

**Antipattern**:
```python
# Fetch raw prices without adjustment
prices = yf.download('AAPL', start='2020-01-01')
```

**Problem**: Stock splits and dividends cause artificial price jumps/drops that distort returns.

**Solution**:
```python
# Use adjusted prices
prices = yf.download('AAPL', start='2020-01-01', auto_adjust=True)

# Or manually adjust for splits/dividends
def adjust_for_splits(prices, split_dates, split_ratios):
    adjusted = prices.copy()
    for date, ratio in zip(split_dates, split_ratios):
        adjusted.loc[:date] /= ratio
    return adjusted
```

---

### 8. Overfitting to Historical Data

**Antipattern**:
```python
# Optimize parameters on full dataset
best_params = optimize_strategy(
    data=historical_data,  # All data
    param_grid={'window': range(5, 100), 'threshold': np.arange(0.01, 0.1, 0.001)}
)
```

**Problem**: Parameters optimized on the same data used for evaluation will overfit and fail in live trading.

**Solution**:
```python
# Use walk-forward analysis
def walk_forward_optimization(data, train_period, test_period):
    results = []
    for i in range(0, len(data) - train_period - test_period, test_period):
        train_data = data[i:i+train_period]
        test_data = data[i+train_period:i+train_period+test_period]
        
        # Optimize on training data
        params = optimize_strategy(train_data)
        
        # Test on out-of-sample data
        performance = backtest_strategy(test_data, params)
        results.append(performance)
    
    return results
```

---

## 🚀 Performance Antipatterns

### 1. N+1 Query Problem

**Antipattern**:
```python
# Fetch all trades
trades = db.query(Trade).all()

# For each trade, fetch the user (separate query!)
for trade in trades:
    user = db.query(User).filter(User.id == trade.user_id).first()
    print(f"{user.name}: {trade.ticker}")
```

**Problem**: Makes N+1 database queries (1 for trades, N for users), extremely slow.

**Solution**:
```python
# Use join to fetch everything in one query
trades = db.query(Trade).join(User).all()

for trade in trades:
    print(f"{trade.user.name}: {trade.ticker}")
```

---

### 2. Synchronous I/O in Async Functions

**Antipattern**:
```python
async def fetch_all_prices(tickers):
    prices = []
    for ticker in tickers:
        # Blocking call in async function!
        price = requests.get(f'https://api.example.com/{ticker}').json()
        prices.append(price)
    return prices
```

**Problem**: Defeats the purpose of async, blocks the event loop.

**Solution**:
```python
import aiohttp

async def fetch_all_prices(tickers):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_price(session, ticker) for ticker in tickers]
        prices = await asyncio.gather(*tasks)
    return prices

async def fetch_price(session, ticker):
    async with session.get(f'https://api.example.com/{ticker}') as response:
        return await response.json()
```

---

### 3. Loading Entire Dataset into Memory

**Antipattern**:
```python
# Load 20 years of tick data (100GB+) into memory
data = pd.read_csv('all_ticks.csv')
```

**Problem**: Causes out-of-memory errors, extremely slow.

**Solution**:
```python
# Use chunking
for chunk in pd.read_csv('all_ticks.csv', chunksize=10000):
    process_chunk(chunk)

# Or use Parquet with partitioning
data = pd.read_parquet('all_ticks.parquet', filters=[('date', '>=', '2024-01-01')])
```

---

### 4. Unnecessary Re-renders in React

**Antipattern**:
```typescript
function Dashboard() {
    const [data, setData] = useState(initialData);
    
    // Creates new object on every render!
    const config = { theme: 'dark', showGrid: true };
    
    return <Chart data={data} config={config} />;
}
```

**Problem**: `config` object is recreated on every render, causing `Chart` to re-render unnecessarily.

**Solution**:
```typescript
function Dashboard() {
    const [data, setData] = useState(initialData);
    
    // Memoize the config object
    const config = useMemo(() => ({
        theme: 'dark',
        showGrid: true
    }), []);
    
    return <Chart data={data} config={config} />;
}
```

---

### 5. Not Using Indexes on Database Columns

**Antipattern**:
```sql
-- No index on ticker column
SELECT * FROM trades WHERE ticker = 'AAPL';  -- Full table scan!
```

**Problem**: Database must scan entire table to find matching rows.

**Solution**:
```sql
-- Add index
CREATE INDEX idx_trades_ticker ON trades(ticker);

-- Now query is fast
SELECT * FROM trades WHERE ticker = 'AAPL';
```

---

## 🔒 Security Antipatterns

### 1. Hardcoded Secrets

**Antipattern**:
```python
API_KEY = "sk_live_abc123xyz789"
```

**Problem**: Secrets committed to Git, exposed to anyone with repository access.

**Solution**:
```python
import os

API_KEY = os.getenv('API_KEY')
if not API_KEY:
    raise ValueError('API_KEY environment variable not set')
```

---

### 2. SQL Injection Vulnerability

**Antipattern**:
```python
ticker = request.args.get('ticker')
query = f"SELECT * FROM trades WHERE ticker = '{ticker}'"
db.execute(query)  # Vulnerable!
```

**Problem**: Attacker can inject SQL: `ticker = "AAPL'; DROP TABLE trades; --"`

**Solution**:
```python
ticker = request.args.get('ticker')
query = "SELECT * FROM trades WHERE ticker = ?"
db.execute(query, (ticker,))  # Parameterized query
```

---

### 3. Exposing Secrets in Logs

**Antipattern**:
```python
logger.info(f"Connecting to database with password: {db_password}")
```

**Problem**: Secrets appear in log files, which may be stored insecurely or shared.

**Solution**:
```python
logger.info("Connecting to database")
# Never log passwords, API keys, or tokens
```

---

### 4. Weak CORS Configuration

**Antipattern**:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows any origin!
    allow_credentials=True,
)
```

**Problem**: Allows any website to make authenticated requests to your API.

**Solution**:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
)
```

---

## 📊 Summary: Most Critical Antipatterns to Avoid

### Python
1. ❌ Mutable default arguments
2. ❌ Bare except clauses
3. ❌ Iterating over DataFrame rows
4. ❌ Using global variables

### TypeScript/React
1. ❌ Using `any` type
2. ❌ Inline functions in JSX
3. ❌ Missing useEffect dependencies
4. ❌ Using index as key

### Financial
1. ❌ Floating-point money calculations
2. ❌ Look-ahead bias in backtesting
3. ❌ Survivorship bias
4. ❌ Ignoring transaction costs

### Security
1. ❌ Hardcoded secrets
2. ❌ SQL injection vulnerabilities
3. ❌ Exposing secrets in logs
4. ❌ Weak CORS configuration

### Performance
1. ❌ N+1 query problem
2. ❌ Loading entire dataset into memory
3. ❌ Synchronous I/O in async functions
4. ❌ Missing database indexes

---

**Last Updated**: 2024-12-28  
**Version**: 1.0  
**Maintainer**: Code Review Team
