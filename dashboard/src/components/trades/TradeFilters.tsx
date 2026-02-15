/**
 * Trade Filters Component
 * =======================
 * Filter controls for trade history table.
 */

import React, { useState } from 'react';
import { Search, Filter, X } from 'lucide-react';
import type { TradeFilters as TradeFiltersType, TradeStatus } from '../../types/trade';

interface TradeFiltersProps {
  filters: TradeFiltersType;
  onFilterChange: (filters: TradeFiltersType) => void;
  onClear: () => void;
}

export const TradeFilters: React.FC<TradeFiltersProps> = ({
  filters,
  onFilterChange,
  onClear,
}) => {
  const [localFilters, setLocalFilters] = useState<TradeFiltersType>(filters);
  const [isExpanded, setIsExpanded] = useState(false);

  const handleChange = (key: keyof TradeFiltersType, value: string | undefined) => {
    const newFilters = { ...localFilters, [key]: value || undefined };
    setLocalFilters(newFilters);
  };

  const handleApply = () => {
    onFilterChange(localFilters);
  };

  const handleClear = () => {
    setLocalFilters({});
    onClear();
  };

  const hasActiveFilters = Object.values(filters).some((v) => v !== undefined);

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-4">
      {/* Quick Search Row */}
      <div className="flex items-center gap-4">
        {/* Ticker Search */}
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search ticker..."
            value={localFilters.ticker || ''}
            onChange={(e) => handleChange('ticker', e.target.value.toUpperCase())}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        {/* Status Select */}
        <select
          value={localFilters.status || ''}
          onChange={(e) => handleChange('status', e.target.value as TradeStatus)}
          className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="">All Status</option>
          <option value="OPEN">Open</option>
          <option value="CLOSED">Closed</option>
          <option value="CANCELLED">Cancelled</option>
        </select>

        {/* Strategy Select */}
        <select
          value={localFilters.strategy || ''}
          onChange={(e) => handleChange('strategy', e.target.value)}
          className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="">All Strategies</option>
          <option value="dual_momentum">Dual Momentum</option>
          <option value="momentum">Momentum</option>
          <option value="hrp">HRP</option>
        </select>

        {/* Toggle Advanced */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <Filter className="w-4 h-4" />
          {isExpanded ? 'Less' : 'More'}
        </button>

        {/* Apply Button */}
        <button
          onClick={handleApply}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Apply
        </button>

        {/* Clear Button */}
        {hasActiveFilters && (
          <button
            onClick={handleClear}
            className="flex items-center gap-1 px-4 py-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-4 h-4" />
            Clear
          </button>
        )}
      </div>

      {/* Advanced Filters */}
      {isExpanded && (
        <div className="mt-4 pt-4 border-t border-gray-200 grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Date Range */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Start Date
            </label>
            <input
              type="date"
              value={localFilters.start_date?.split('T')[0] || ''}
              onChange={(e) =>
                handleChange(
                  'start_date',
                  e.target.value ? `${e.target.value}T00:00:00` : undefined
                )
              }
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              End Date
            </label>
            <input
              type="date"
              value={localFilters.end_date?.split('T')[0] || ''}
              onChange={(e) =>
                handleChange(
                  'end_date',
                  e.target.value ? `${e.target.value}T23:59:59` : undefined
                )
              }
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Sort By
            </label>
            <select
              value={localFilters.sort_by || 'entry_date'}
              onChange={(e) => handleChange('sort_by', e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="entry_date">Entry Date</option>
              <option value="ticker">Ticker</option>
              <option value="pnl">P&L</option>
              <option value="pnl_percent">P&L %</option>
              <option value="quantity">Quantity</option>
            </select>
          </div>
        </div>
      )}
    </div>
  );
};

export default TradeFilters;
