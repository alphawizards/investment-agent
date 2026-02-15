"""
Database schema and connection for stock data storage.
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

# Database path
DB_PATH = Path(__file__).parent.parent / "data" / "stock_data.db"


def get_connection() -> sqlite3.Connection:
    """Get database connection."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database() -> None:
    """Initialize database schema."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Tickers universe table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT UNIQUE NOT NULL,
            name TEXT,
            exchange TEXT NOT NULL,
            sector TEXT,
            last_updated DATETIME,
            is_active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Daily prices table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker_id INTEGER NOT NULL,
            date DATE NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            adj_close REAL,
            volume INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ticker_id) REFERENCES tickers(id),
            UNIQUE(ticker_id, date)
        )
    """)
    
    # Create indexes for performance
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_daily_prices_ticker_date 
        ON daily_prices(ticker_id, date)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_daily_prices_date 
        ON daily_prices(date)
    """)
    
    # Data quality log table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS data_quality_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker_id INTEGER,
            date DATE,
            issue_type TEXT NOT NULL,
            issue_details TEXT,
            detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ticker_id) REFERENCES tickers(id)
        )
    """)
    
    # Update history table (for tracking when data was updated)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS update_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            update_type TEXT NOT NULL,
            tickers_processed INTEGER,
            tickers_succeeded INTEGER,
            tickers_failed INTEGER,
            records_inserted INTEGER,
            started_at DATETIME,
            completed_at DATETIME,
            status TEXT DEFAULT 'running',
            error_message TEXT
        )
    """)
    
    conn.commit()
    conn.close()
    print(f"[OK] Database initialized at: {DB_PATH}")


def add_ticker(ticker: str, name: str, exchange: str, sector: Optional[str] = None) -> int:
    """Add a ticker to the universe."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR IGNORE INTO tickers (ticker, name, exchange, sector)
        VALUES (?, ?, ?, ?)
    """, (ticker.upper(), name, exchange, sector))
    
    conn.commit()
    cursor.execute("SELECT id FROM tickers WHERE ticker = ?", (ticker.upper(),))
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else None


def add_tickers_batch(tickers: List[Dict[str, str]]) -> int:
    """Add multiple tickers in batch."""
    conn = get_connection()
    cursor = conn.cursor()
    
    count = 0
    for item in tickers:
        cursor.execute("""
            INSERT OR IGNORE INTO tickers (ticker, name, exchange, sector)
            VALUES (?, ?, ?, ?)
        """, (item['ticker'].upper(), item.get('name'), item.get('exchange'), item.get('sector')))
        count += cursor.rowcount
    
    conn.commit()
    conn.close()
    return count


def get_ticker_id(ticker: str) -> Optional[int]:
    """Get ticker ID by symbol."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM tickers WHERE ticker = ?", (ticker.upper(),))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def get_all_tickers(exchange: Optional[str] = None, active_only: bool = True) -> List[Dict[str, Any]]:
    """Get all tickers from the universe."""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM tickers"
    params = []
    
    if exchange:
        query += " WHERE exchange = ?"
        params.append(exchange)
    
    if active_only:
        query += " AND is_active = 1" if exchange else " WHERE is_active = 1"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_ticker_price_range(ticker_id: int) -> Optional[Dict[str, Any]]:
    """Get the date range of available prices for a ticker."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT MIN(date) as min_date, MAX(date) as max_date, COUNT(*) as count
        FROM daily_prices WHERE ticker_id = ?
    """, (ticker_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    return dict(result) if result else None


def insert_daily_price(ticker_id: int, data: Dict[str, Any]) -> bool:
    """Insert a single daily price record."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO daily_prices 
            (ticker_id, date, open, high, low, close, adj_close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticker_id,
            data['date'],
            data.get('open'),
            data.get('high'),
            data.get('low'),
            data.get('close'),
            data.get('adj_close'),
            data.get('volume')
        ))
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        conn.close()
        return False


def insert_daily_prices_batch(ticker_id: int, prices: List[Dict[str, Any]]) -> int:
    """Insert multiple daily price records."""
    conn = get_connection()
    cursor = conn.cursor()
    
    count = 0
    for data in prices:
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO daily_prices 
                (ticker_id, date, open, high, low, close, adj_close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ticker_id,
                data['date'],
                data.get('open'),
                data.get('high'),
                data.get('low'),
                data.get('close'),
                data.get('adj_close'),
                data.get('volume')
            ))
            count += 1
        except sqlite3.Error:
            pass
    
    conn.commit()
    conn.close()
    return count


def get_latest_price_date(ticker_id: int) -> Optional[str]:
    """Get the most recent price date for a ticker."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT MAX(date) FROM daily_prices WHERE ticker_id = ?
    """, (ticker_id,))
    
    result = cursor.fetchone()
    conn.close()
    return result[0] if result and result[0] else None


def log_data_quality_issue(ticker_id: int, date: str, issue_type: str, details: str) -> None:
    """Log a data quality issue."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO data_quality_log (ticker_id, date, issue_type, issue_details)
        VALUES (?, ?, ?, ?)
    """, (ticker_id, date, issue_type, details))
    
    conn.commit()
    conn.close()


def get_data_quality_issues(ticker_id: Optional[int] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Get recent data quality issues."""
    conn = get_connection()
    cursor = conn.cursor()
    
    if ticker_id:
        cursor.execute("""
            SELECT * FROM data_quality_log 
            WHERE ticker_id = ?
            ORDER BY detected_at DESC LIMIT ?
        """, (ticker_id, limit))
    else:
        cursor.execute("""
            SELECT * FROM data_quality_log 
            ORDER BY detected_at DESC LIMIT ?
        """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_ticker_last_updated(ticker_id: int) -> None:
    """Update the last_updated timestamp for a ticker."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE tickers SET last_updated = CURRENT_TIMESTAMP WHERE id = ?
    """, (ticker_id,))
    
    conn.commit()
    conn.close()


def start_update_history(update_type: str) -> int:
    """Start a new update history record."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO update_history (update_type, started_at)
        VALUES (?, CURRENT_TIMESTAMP)
    """, (update_type,))
    
    conn.commit()
    cursor.execute("SELECT last_insert_rowid()")
    result = cursor.fetchone()
    conn.close()
    return result[0]


def finish_update_history(
    update_id: int,
    tickers_processed: int,
    tickers_succeeded: int,
    tickers_failed: int,
    records_inserted: int,
    status: str = 'completed',
    error_message: Optional[str] = None
) -> None:
    """Finish updating an update history record."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE update_history 
        SET completed_at = CURRENT_TIMESTAMP,
            tickers_processed = ?,
            tickers_succeeded = ?,
            tickers_failed = ?,
            records_inserted = ?,
            status = ?,
            error_message = ?
        WHERE id = ?
    """, (tickers_processed, tickers_succeeded, tickers_failed, 
          records_inserted, status, error_message, update_id))
    
    conn.commit()
    conn.close()


def get_data_freshness() -> Dict[str, Any]:
    """Get data freshness summary."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get overall stats
    cursor.execute("""
        SELECT 
            COUNT(DISTINCT ticker_id) as total_tickers,
            COUNT(*) as total_records,
            MIN(date) as earliest_date,
            MAX(date) as latest_date
        FROM daily_prices
    """)
    overall = cursor.fetchone()
    
    # Get tickers with most recent update
    cursor.execute("""
        SELECT t.ticker, t.exchange, dp.max_date, dp.record_count
        FROM tickers t
        JOIN (
            SELECT ticker_id, MAX(date) as max_date, COUNT(*) as record_count
            FROM daily_prices
            GROUP BY ticker_id
        ) dp ON t.id = dp.ticker_id
        ORDER BY dp.max_date DESC
        LIMIT 20
    """)
    recent = cursor.fetchall()
    
    # Get stale tickers (not updated in 7 days)
    cursor.execute("""
        SELECT t.ticker, t.exchange, t.last_updated
        FROM tickers t
        WHERE t.last_updated < datetime('now', '-7 days')
        AND t.is_active = 1
        ORDER BY t.last_updated ASC
        LIMIT 20
    """)
    stale = cursor.fetchall()
    
    conn.close()
    
    return {
        'total_tickers': overall[0] or 0,
        'total_records': overall[1] or 0,
        'earliest_date': overall[2],
        'latest_date': overall[3],
        'recent_updates': [dict(row) for row in recent],
        'stale_tickers': [dict(row) for row in stale]
    }


if __name__ == "__main__":
    init_database()
