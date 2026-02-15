"""Initial migration - trades, portfolio_snapshots, index_constituents, market_data

Revision ID: 20250112_0001
Revises:
Create Date: 2025-01-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20250112_0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create initial tables:
    - trades: Track all executed trades
    - portfolio_snapshots: Track portfolio value over time
    - index_constituents: Historical index membership (for survivorship bias correction)
    - market_data: OHLCV market data (PostgreSQL only)
    """

    # 1. Trades table
    op.create_table(
        'trades',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('trade_id', sa.String(length=50), nullable=False),
        sa.Column('ticker', sa.String(length=20), nullable=False),
        sa.Column('asset_name', sa.String(length=100), nullable=True),
        sa.Column('asset_class', sa.String(length=50), nullable=True),
        sa.Column('direction', sa.Enum('BUY', 'SELL', name='tradedirection'), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('entry_price', sa.Float(), nullable=False),
        sa.Column('exit_price', sa.Float(), nullable=True),
        sa.Column('commission', sa.Float(), nullable=True, default=3.0),
        sa.Column('currency', sa.String(length=3), nullable=True, default='AUD'),
        sa.Column('entry_date', sa.DateTime(), nullable=False),
        sa.Column('exit_date', sa.DateTime(), nullable=True),
        sa.Column('pnl', sa.Float(), nullable=True),
        sa.Column('pnl_percent', sa.Float(), nullable=True),
        sa.Column('strategy_name', sa.String(length=100), nullable=True, default='dual_momentum'),
        sa.Column('signal_score', sa.Float(), nullable=True),
        sa.Column('status', sa.Enum('OPEN', 'CLOSED', 'CANCELLED', name='tradestatus'), nullable=True, default='OPEN'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('knowledge_timestamp', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('event_timestamp', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Trades indexes
    op.create_index('ix_trades_ticker_date', 'trades', ['ticker', 'entry_date'])
    op.create_index('ix_trades_strategy_status', 'trades', ['strategy_name', 'status'])
    op.create_index('ix_trades_date_range', 'trades', ['entry_date', 'exit_date'])
    op.create_index('ix_trades_bitemporal', 'trades', ['knowledge_timestamp', 'event_timestamp'])
    op.create_index(op.f('ix_trades_trade_id'), 'trades', ['trade_id'], unique=True)
    op.create_index(op.f('ix_trades_ticker'), 'trades', ['ticker'], unique=False)
    op.create_index(op.f('ix_trades_entry_date'), 'trades', ['entry_date'], unique=False)
    op.create_index(op.f('ix_trades_strategy_name'), 'trades', ['strategy_name'], unique=False)

    # 2. Portfolio Snapshots table
    op.create_table(
        'portfolio_snapshots',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('snapshot_date', sa.DateTime(), nullable=False),
        sa.Column('total_value', sa.Float(), nullable=False),
        sa.Column('cash_balance', sa.Float(), nullable=False),
        sa.Column('invested_value', sa.Float(), nullable=False),
        sa.Column('daily_return', sa.Float(), nullable=True),
        sa.Column('cumulative_return', sa.Float(), nullable=True),
        sa.Column('volatility_21d', sa.Float(), nullable=True),
        sa.Column('sharpe_ratio_21d', sa.Float(), nullable=True),
        sa.Column('max_drawdown', sa.Float(), nullable=True),
        sa.Column('num_positions', sa.Integer(), nullable=True, default=0),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('knowledge_timestamp', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('event_timestamp', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Portfolio Snapshots indexes
    op.create_index('ix_snapshot_date', 'portfolio_snapshots', ['snapshot_date'])
    op.create_index('ix_snapshot_bitemporal', 'portfolio_snapshots', ['knowledge_timestamp', 'event_timestamp'])

    # 3. Index Constituents table
    op.create_table(
        'index_constituents',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('ticker', sa.String(length=20), nullable=False),
        sa.Column('index_name', sa.String(length=20), nullable=False),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Index Constituents indexes
    op.create_index('ix_constituents_lookup', 'index_constituents', ['index_name', 'start_date', 'end_date'])
    op.create_index(op.f('ix_index_constituents_ticker'), 'index_constituents', ['ticker'], unique=False)
    op.create_index(op.f('ix_index_constituents_index_name'), 'index_constituents', ['index_name'], unique=False)
    op.create_index(op.f('ix_index_constituents_start_date'), 'index_constituents', ['start_date'], unique=False)

    # 4. Market Data table (PostgreSQL only - for Neon)
    # This table will only be created if we're using PostgreSQL
    # SQLite will skip this (handled in migration logic)

    # Check if we're using PostgreSQL (by checking the bind)
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.create_table(
            'market_data',
            sa.Column('ticker', sa.String(length=20), nullable=False),
            sa.Column('date', sa.Date(), nullable=False),
            sa.Column('open', sa.Numeric(precision=12, scale=4), nullable=False),
            sa.Column('high', sa.Numeric(precision=12, scale=4), nullable=False),
            sa.Column('low', sa.Numeric(precision=12, scale=4), nullable=False),
            sa.Column('close', sa.Numeric(precision=12, scale=4), nullable=False),
            sa.Column('volume', sa.BigInteger(), nullable=False),
            sa.Column('adjusted_close', sa.Numeric(precision=12, scale=4), nullable=True),
            sa.Column('source', sa.String(length=50), nullable=True, default='yfinance'),
            sa.Column('data_quality', sa.String(length=20), nullable=True, default='good'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('metadata', sa.JSON(), nullable=True, default={}),
            sa.PrimaryKeyConstraint('ticker', 'date'),
            sa.CheckConstraint('low <= open AND low <= close AND low <= high AND high >= open AND high >= close', name='valid_ohlc'),
            sa.CheckConstraint('volume >= 0', name='positive_volume'),
            sa.CheckConstraint('open > 0 AND high > 0 AND low > 0 AND close > 0', name='positive_prices'),
            sa.CheckConstraint("data_quality IN ('good', 'suspect', 'bad')", name='valid_data_quality')
        )

        # Market Data indexes
        op.create_index('idx_market_data_ticker', 'market_data', ['ticker'])
        op.create_index('idx_market_data_date', 'market_data', [sa.text('date DESC')])
        op.create_index('idx_market_data_ticker_date', 'market_data', ['ticker', sa.text('date DESC')])
        op.create_index('idx_market_data_updated_at', 'market_data', [sa.text('updated_at DESC')])
        op.create_index(
            'idx_market_data_quality',
            'market_data',
            ['data_quality'],
            postgresql_where=sa.text("data_quality != 'good'")
        )

        # Create trigger for updated_at timestamp (PostgreSQL only)
        op.execute("""
            CREATE OR REPLACE FUNCTION update_market_data_timestamp()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)

        op.execute("""
            CREATE TRIGGER trigger_update_market_data_timestamp
                BEFORE UPDATE ON market_data
                FOR EACH ROW
                EXECUTE FUNCTION update_market_data_timestamp();
        """)


def downgrade() -> None:
    """Drop all tables."""

    # Check if we're using PostgreSQL
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        # Drop trigger and function
        op.execute("DROP TRIGGER IF EXISTS trigger_update_market_data_timestamp ON market_data;")
        op.execute("DROP FUNCTION IF EXISTS update_market_data_timestamp();")

        # Drop market_data table and indexes
        op.drop_index('idx_market_data_quality', table_name='market_data')
        op.drop_index('idx_market_data_updated_at', table_name='market_data')
        op.drop_index('idx_market_data_ticker_date', table_name='market_data')
        op.drop_index('idx_market_data_date', table_name='market_data')
        op.drop_index('idx_market_data_ticker', table_name='market_data')
        op.drop_table('market_data')

    # Drop index_constituents
    op.drop_index(op.f('ix_index_constituents_start_date'), table_name='index_constituents')
    op.drop_index(op.f('ix_index_constituents_index_name'), table_name='index_constituents')
    op.drop_index(op.f('ix_index_constituents_ticker'), table_name='index_constituents')
    op.drop_index('ix_constituents_lookup', table_name='index_constituents')
    op.drop_table('index_constituents')

    # Drop portfolio_snapshots
    op.drop_index('ix_snapshot_bitemporal', table_name='portfolio_snapshots')
    op.drop_index('ix_snapshot_date', table_name='portfolio_snapshots')
    op.drop_table('portfolio_snapshots')

    # Drop trades
    op.drop_index(op.f('ix_trades_strategy_name'), table_name='trades')
    op.drop_index(op.f('ix_trades_entry_date'), table_name='trades')
    op.drop_index(op.f('ix_trades_ticker'), table_name='trades')
    op.drop_index(op.f('ix_trades_trade_id'), table_name='trades')
    op.drop_index('ix_trades_bitemporal', table_name='trades')
    op.drop_index('ix_trades_date_range', table_name='trades')
    op.drop_index('ix_trades_strategy_status', table_name='trades')
    op.drop_index('ix_trades_ticker_date', table_name='trades')
    op.drop_table('trades')
