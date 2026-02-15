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

-- Drop existing table if recreating (use with caution in production)
-- DROP TABLE IF EXISTS market_data CASCADE;

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

-- ============================================================================
-- Indexes for Query Optimization
-- ============================================================================

-- Index for ticker-based queries (most common pattern)
CREATE INDEX IF NOT EXISTS idx_market_data_ticker 
ON market_data (ticker);

-- Index for date-based queries (time-series scans)
CREATE INDEX IF NOT EXISTS idx_market_data_date 
ON market_data (date DESC);

-- Composite index for ticker + date range queries (optimal for backtesting)
CREATE INDEX IF NOT EXISTS idx_market_data_ticker_date 
ON market_data (ticker, date DESC);

-- Index for data freshness monitoring
CREATE INDEX IF NOT EXISTS idx_market_data_updated_at 
ON market_data (updated_at DESC);

-- Index for data quality filtering
CREATE INDEX IF NOT EXISTS idx_market_data_quality 
ON market_data (data_quality) 
WHERE data_quality != 'good';

-- GIN index for JSONB metadata queries (if needed)
CREATE INDEX IF NOT EXISTS idx_market_data_metadata 
ON market_data USING GIN (metadata);

-- ============================================================================
-- Trigger for Automatic updated_at Timestamp
-- ============================================================================

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_market_data_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to call the function on UPDATE
DROP TRIGGER IF EXISTS trigger_update_market_data_timestamp ON market_data;
CREATE TRIGGER trigger_update_market_data_timestamp
    BEFORE UPDATE ON market_data
    FOR EACH ROW
    EXECUTE FUNCTION update_market_data_timestamp();

-- ============================================================================
-- Partitioning Strategy (Optional - for scaling beyond 10M rows)
-- ============================================================================
-- 
-- For large datasets, consider partitioning by date range (monthly or yearly)
-- This improves query performance and enables efficient data archival
-- 
-- Example: Convert to partitioned table (requires table recreation)
-- 
-- CREATE TABLE market_data (
--     ... same columns ...
-- ) PARTITION BY RANGE (date);
-- 
-- CREATE TABLE market_data_2024 PARTITION OF market_data
--     FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
-- 
-- CREATE TABLE market_data_2025 PARTITION OF market_data
--     FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
-- 
-- ============================================================================

-- ============================================================================
-- Helper Views
-- ============================================================================

-- View: Latest data per ticker (useful for data freshness checks)
CREATE OR REPLACE VIEW market_data_latest AS
SELECT DISTINCT ON (ticker)
    ticker,
    date,
    close,
    volume,
    updated_at,
    CURRENT_DATE - date AS days_stale
FROM market_data
ORDER BY ticker, date DESC;

-- View: Data quality summary
CREATE OR REPLACE VIEW market_data_quality_summary AS
SELECT 
    data_quality,
    COUNT(*) AS row_count,
    COUNT(DISTINCT ticker) AS ticker_count,
    MIN(date) AS earliest_date,
    MAX(date) AS latest_date
FROM market_data
GROUP BY data_quality;

-- ============================================================================
-- Utility Functions
-- ============================================================================

-- Function: Get latest close price for a ticker
CREATE OR REPLACE FUNCTION get_latest_close(p_ticker VARCHAR)
RETURNS NUMERIC AS $$
    SELECT close 
    FROM market_data 
    WHERE ticker = p_ticker 
    ORDER BY date DESC 
    LIMIT 1;
$$ LANGUAGE SQL STABLE;

-- Function: Get date range for a ticker
CREATE OR REPLACE FUNCTION get_ticker_date_range(p_ticker VARCHAR)
RETURNS TABLE(min_date DATE, max_date DATE, total_days BIGINT) AS $$
    SELECT 
        MIN(date) AS min_date,
        MAX(date) AS max_date,
        COUNT(*) AS total_days
    FROM market_data 
    WHERE ticker = p_ticker;
$$ LANGUAGE SQL STABLE;

-- ============================================================================
-- Sample Queries for Testing
-- ============================================================================

-- Query 1: Get latest 30 days of data for AAPL
-- SELECT * FROM market_data 
-- WHERE ticker = 'AAPL' 
-- ORDER BY date DESC 
-- LIMIT 30;

-- Query 2: Get all tickers with data from yesterday
-- SELECT DISTINCT ticker 
-- FROM market_data 
-- WHERE date = CURRENT_DATE - INTERVAL '1 day';

-- Query 3: Find tickers with stale data (>7 days old)
-- SELECT ticker, MAX(date) AS latest_date, CURRENT_DATE - MAX(date) AS days_stale
-- FROM market_data
-- GROUP BY ticker
-- HAVING CURRENT_DATE - MAX(date) > 7
-- ORDER BY days_stale DESC;

-- Query 4: Get price range for a ticker over last year
-- SELECT 
--     ticker,
--     MIN(low) AS year_low,
--     MAX(high) AS year_high,
--     AVG(close) AS avg_close,
--     SUM(volume) AS total_volume
-- FROM market_data
-- WHERE ticker = 'AAPL' 
--   AND date >= CURRENT_DATE - INTERVAL '1 year'
-- GROUP BY ticker;

-- ============================================================================
-- Performance Monitoring
-- ============================================================================

-- Check table size
-- SELECT 
--     pg_size_pretty(pg_total_relation_size('market_data')) AS total_size,
--     pg_size_pretty(pg_relation_size('market_data')) AS table_size,
--     pg_size_pretty(pg_indexes_size('market_data')) AS indexes_size;

-- Check index usage
-- SELECT 
--     schemaname,
--     tablename,
--     indexname,
--     idx_scan,
--     idx_tup_read,
--     idx_tup_fetch
-- FROM pg_stat_user_indexes
-- WHERE tablename = 'market_data'
-- ORDER BY idx_scan DESC;

-- ============================================================================
-- Grants (adjust based on your user roles)
-- ============================================================================

-- Grant SELECT to read-only users
-- GRANT SELECT ON market_data TO readonly_user;

-- Grant INSERT, UPDATE to Lambda execution role
-- GRANT SELECT, INSERT, UPDATE ON market_data TO lambda_ingest_role;

-- ============================================================================
-- Comments for Documentation
-- ============================================================================

COMMENT ON TABLE market_data IS 'Daily OHLCV market data for stocks and ETFs. Composite primary key (ticker, date) ensures idempotency.';
COMMENT ON COLUMN market_data.ticker IS 'Stock ticker symbol (e.g., AAPL, MSFT, BHP.AX)';
COMMENT ON COLUMN market_data.date IS 'Trading date (market close date)';
COMMENT ON COLUMN market_data.open IS 'Opening price for the trading day';
COMMENT ON COLUMN market_data.high IS 'Highest price during the trading day';
COMMENT ON COLUMN market_data.low IS 'Lowest price during the trading day';
COMMENT ON COLUMN market_data.close IS 'Closing price for the trading day (unadjusted)';
COMMENT ON COLUMN market_data.volume IS 'Trading volume (number of shares traded)';
COMMENT ON COLUMN market_data.adjusted_close IS 'Closing price adjusted for splits and dividends';
COMMENT ON COLUMN market_data.source IS 'Data source (e.g., yfinance, tiingo, polygon)';
COMMENT ON COLUMN market_data.data_quality IS 'Data quality flag: good, suspect, or bad';
COMMENT ON COLUMN market_data.created_at IS 'Timestamp when record was first inserted';
COMMENT ON COLUMN market_data.updated_at IS 'Timestamp when record was last updated';
COMMENT ON COLUMN market_data.metadata IS 'Additional metadata in JSONB format (extensible)';

-- ============================================================================
-- End of Schema Definition
-- ============================================================================
