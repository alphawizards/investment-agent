/**
 * Trade Types
 * ===========
 * TypeScript interfaces matching backend Pydantic schemas.
 */

export type TradeDirection = 'BUY' | 'SELL';
export type TradeStatus = 'OPEN' | 'CLOSED' | 'CANCELLED';

export interface Trade {
  id: number;
  trade_id: string;
  ticker: string;
  asset_name?: string;
  asset_class?: string;
  direction: TradeDirection;
  quantity: number;
  entry_price: number;
  exit_price?: number;
  commission: number;
  currency: string;
  entry_date: string;
  exit_date?: string;
  pnl?: number;
  pnl_percent?: number;
  strategy_name: string;
  signal_score?: number;
  status: TradeStatus;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface TradeCreate {
  trade_id: string;
  ticker: string;
  asset_name?: string;
  asset_class?: string;
  direction: TradeDirection;
  quantity: number;
  entry_price: number;
  entry_date: string;
  commission?: number;
  currency?: string;
  strategy_name?: string;
  signal_score?: number;
  notes?: string;
}

export interface TradeUpdate {
  exit_price?: number;
  exit_date?: string;
  status?: TradeStatus;
  notes?: string;
}

export interface TradeListResponse {
  trades: Trade[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface PortfolioMetrics {
  total_value: number;
  cash_balance: number;
  invested_value: number;
  daily_return?: number;
  total_return?: number;
  volatility?: number;
  sharpe_ratio?: number;
  max_drawdown?: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate?: number;
  total_pnl: number;
  avg_pnl_per_trade?: number;
  best_trade?: number;
  worst_trade?: number;
}

export interface DashboardSummary {
  portfolio: PortfolioMetrics;
  recent_trades: Trade[];
  open_positions: number;
  today_pnl: number;
  week_pnl: number;
  month_pnl: number;
  last_updated: string;
}

export interface TradeStats {
  ticker: string;
  total_trades: number;
  total_pnl: number;
  avg_pnl: number;
  win_rate: number;
}

export interface TradeFilters {
  ticker?: string;
  status?: TradeStatus;
  strategy?: string;
  start_date?: string;
  end_date?: string;
  sort_by?: string;
  sort_desc?: boolean;
}
