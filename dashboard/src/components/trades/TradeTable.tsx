/**
 * Trade Table Component
 * =====================
 * Displays trade history in a sortable, filterable table.
 */

import React from 'react';
import { ChevronUp, ChevronDown, ChevronLeft, ChevronRight } from 'lucide-react';
import type { Trade } from '../../types/trade';
import {
  formatCurrency,
  formatPercent,
  formatDateTime,
  getPnlColorClass,
  getStatusBadgeClass,
  getDirectionBadgeClass,
} from '../../hooks/useMetrics';

interface TradeTableProps {
  trades: Trade[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  loading?: boolean;
  onPageChange: (page: number) => void;
  onSort?: (column: string, desc: boolean) => void;
  sortBy?: string;
  sortDesc?: boolean;
}

export const TradeTable: React.FC<TradeTableProps> = ({
  trades,
  total,
  page,
  pageSize,
  totalPages,
  loading = false,
  onPageChange,
  onSort,
  sortBy = 'entry_date',
  sortDesc = true,
}) => {
  const handleSort = (column: string) => {
    if (onSort) {
      const newDesc = sortBy === column ? !sortDesc : true;
      onSort(column, newDesc);
    }
  };

  const SortIcon: React.FC<{ column: string }> = ({ column }) => {
    if (sortBy !== column) return null;
    return sortDesc ? (
      <ChevronDown className="w-4 h-4 inline ml-1" />
    ) : (
      <ChevronUp className="w-4 h-4 inline ml-1" />
    );
  };

  const columns = [
    { key: 'entry_date', label: 'Date', sortable: true },
    { key: 'ticker', label: 'Ticker', sortable: true },
    { key: 'direction', label: 'Direction', sortable: false },
    { key: 'quantity', label: 'Qty', sortable: true },
    { key: 'entry_price', label: 'Entry', sortable: true },
    { key: 'exit_price', label: 'Exit', sortable: true },
    { key: 'pnl', label: 'P&L', sortable: true },
    { key: 'pnl_percent', label: 'P&L %', sortable: true },
    { key: 'status', label: 'Status', sortable: true },
    { key: 'strategy_name', label: 'Strategy', sortable: true },
  ];

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      {/* Table Header */}
      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">
            Trade History
          </h3>
          <span className="text-sm text-gray-500">
            {total.toLocaleString()} total trades
          </span>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={`px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${col.sortable ? 'cursor-pointer hover:bg-gray-100' : ''
                    }`}
                  onClick={() => col.sortable && handleSort(col.key)}
                >
                  {col.label}
                  {col.sortable && <SortIcon column={col.key} />}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {loading ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-8 text-center">
                  <div className="flex items-center justify-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                    <span className="ml-2 text-gray-500">Loading trades...</span>
                  </div>
                </td>
              </tr>
            ) : trades.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-8 text-center text-gray-500">
                  No trades found
                </td>
              </tr>
            ) : (
              trades.map((trade) => (
                <TradeRow key={trade.id} trade={trade} />
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="px-4 py-3 border-t border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-500">
            Showing {(page - 1) * pageSize + 1} to{' '}
            {Math.min(page * pageSize, total)} of {total}
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
              className="p-2 rounded border border-gray-300 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-sm text-gray-700">
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => onPageChange(page + 1)}
              disabled={page >= totalPages}
              className="p-2 rounded border border-gray-300 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

/**
 * Individual Trade Row
 */
interface TradeRowProps {
  trade: Trade;
}

const TradeRow: React.FC<TradeRowProps> = ({ trade }) => {
  return (
    <tr className="hover:bg-gray-50 transition-colors">
      {/* Date */}
      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
        {formatDateTime(trade.entry_date)}
      </td>

      {/* Ticker */}
      <td className="px-4 py-3 whitespace-nowrap">
        <span className="font-mono font-medium text-gray-900">
          {trade.ticker}
        </span>
        {trade.asset_class && (
          <span className="ml-2 text-xs text-gray-500">
            {trade.asset_class}
          </span>
        )}
      </td>

      {/* Direction */}
      <td className="px-4 py-3 whitespace-nowrap">
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${getDirectionBadgeClass(trade.direction)}`}>
          {trade.direction}
        </span>
      </td>

      {/* Quantity */}
      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 font-mono">
        {trade.quantity.toLocaleString()}
      </td>

      {/* Entry Price */}
      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 font-mono">
        {formatCurrency(trade.entry_price)}
      </td>

      {/* Exit Price */}
      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 font-mono">
        {trade.exit_price ? formatCurrency(trade.exit_price) : '-'}
      </td>

      {/* P&L */}
      <td className="px-4 py-3 whitespace-nowrap">
        {trade.pnl !== null && trade.pnl !== undefined ? (
          <span className={`text-sm font-medium font-mono ${getPnlColorClass(trade.pnl)}`}>
            {formatCurrency(trade.pnl)}
          </span>
        ) : (
          <span className="text-sm text-gray-400">-</span>
        )}
      </td>

      {/* P&L % */}
      <td className="px-4 py-3 whitespace-nowrap">
        {trade.pnl_percent !== null && trade.pnl_percent !== undefined ? (
          <span className={`text-sm font-medium font-mono ${getPnlColorClass(trade.pnl_percent)}`}>
            {formatPercent(trade.pnl_percent)}
          </span>
        ) : (
          <span className="text-sm text-gray-400">-</span>
        )}
      </td>

      {/* Status */}
      <td className="px-4 py-3 whitespace-nowrap">
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${getStatusBadgeClass(trade.status)}`}>
          {trade.status}
        </span>
      </td>

      {/* Strategy */}
      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
        {trade.strategy_name}
      </td>
    </tr>
  );
};

export default TradeTable;
