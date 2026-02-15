/**
 * Metric Card Component
 * =====================
 * Displays a single metric with label, value, and optional change indicator.
 */

import React from 'react';
import { LucideIcon } from 'lucide-react';
import { formatCurrency, formatPercent, getPnlColorClass } from '../../hooks/useMetrics';

interface MetricCardProps {
  label: string;
  value: number;
  format?: 'currency' | 'percent' | 'number';
  change?: number;
  icon?: LucideIcon;
  iconColor?: string;
  className?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  format = 'currency',
  change,
  icon: Icon,
  iconColor = 'text-gray-400',
  className = '',
}) => {
  const formattedValue = React.useMemo(() => {
    switch (format) {
      case 'currency':
        return formatCurrency(value);
      case 'percent':
        return formatPercent(value);
      case 'number':
        return value.toLocaleString('en-AU');
      default:
        return value.toString();
    }
  }, [value, format]);

  const valueColorClass = format === 'currency' || format === 'percent'
    ? getPnlColorClass(value)
    : 'text-gray-900';

  return (
    <div className={`bg-white rounded-lg shadow-sm border border-gray-200 p-4 ${className}`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500 uppercase tracking-wide">
            {label}
          </p>
          <p className={`text-2xl font-bold mt-1 ${valueColorClass}`}>
            {formattedValue}
          </p>
          {change !== undefined && (
            <p className={`text-sm mt-1 ${getPnlColorClass(change)}`}>
              {formatPercent(change)} from previous
            </p>
          )}
        </div>
        {Icon && (
          <div className={`p-3 rounded-full bg-gray-50 ${iconColor}`}>
            <Icon className="w-6 h-6" />
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * Metric Card Grid
 */
interface MetricGridProps {
  children: React.ReactNode;
  columns?: 2 | 3 | 4;
  className?: string;
}

export const MetricGrid: React.FC<MetricGridProps> = ({
  children,
  columns = 4,
  className = '',
}) => {
  const gridCols = {
    2: 'grid-cols-1 md:grid-cols-2',
    3: 'grid-cols-1 md:grid-cols-3',
    4: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-4',
  };

  return (
    <div className={`grid ${gridCols[columns]} gap-4 ${className}`}>
      {children}
    </div>
  );
};

export default MetricCard;
