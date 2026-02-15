/**
 * Alpha Matrix Component
 * ======================
 * The core strategy performance matrix with institutional-grade metrics.
 * Uses @tanstack/react-table for sorting/filtering.
 */

import React, { useMemo, useState } from 'react';
import {
    useReactTable,
    getCoreRowModel,
    getSortedRowModel,
    getFilteredRowModel,
    flexRender,
    createColumnHelper,
    SortingState,
} from '@tanstack/react-table';
import { StrategyMetrics, isPSRSignificant } from '../../types/strategy';
import { DSRBadge, PSRIndicator, GraveyardBadge } from './DSRBadge';
import { ArrowUpDown, ChevronUp, ChevronDown, Search } from 'lucide-react';

interface AlphaMatrixProps {
    strategies: StrategyMetrics[];
    onSelectStrategy?: (strategy: StrategyMetrics) => void;
}

const columnHelper = createColumnHelper<StrategyMetrics>();

export const AlphaMatrix: React.FC<AlphaMatrixProps> = ({
    strategies,
    onSelectStrategy
}) => {
    const [sorting, setSorting] = useState<SortingState>([
        { id: 'dsr', desc: true }
    ]);
    const [globalFilter, setGlobalFilter] = useState('');

    const columns = useMemo(() => [
        // Strategy Name
        columnHelper.accessor('name', {
            header: 'Strategy',
            cell: info => (
                <div className="font-semibold text-slate-100">
                    {info.getValue()}
                </div>
            ),
        }),

        // === VALIDITY GROUP ===
        columnHelper.accessor(row => row.validity.dsr, {
            id: 'dsr',
            header: ({ column }) => (
                <button
                    onClick={() => column.toggleSorting()}
                    className="flex items-center gap-1 hover:text-emerald-400 transition-colors"
                >
                    DSR
                    <SortIcon isSorted={column.getIsSorted()} />
                </button>
            ),
            cell: info => <DSRBadge dsr={info.getValue()} />,
        }),

        columnHelper.accessor(row => row.validity.psr, {
            id: 'psr',
            header: ({ column }) => (
                <button
                    onClick={() => column.toggleSorting()}
                    className="flex items-center gap-1 hover:text-emerald-400 transition-colors"
                >
                    PSR
                    <SortIcon isSorted={column.getIsSorted()} />
                </button>
            ),
            cell: info => <PSRIndicator psr={info.getValue()} />,
        }),

        // === EFFICIENCY GROUP ===
        columnHelper.accessor(row => row.efficiency.sharpe, {
            id: 'sharpe',
            header: ({ column }) => (
                <button
                    onClick={() => column.toggleSorting()}
                    className="flex items-center gap-1 hover:text-emerald-400 transition-colors"
                >
                    Sharpe
                    <SortIcon isSorted={column.getIsSorted()} />
                </button>
            ),
            cell: info => (
                <span className={`font-mono ${info.getValue() >= 1.5 ? 'text-emerald-400' : 'text-slate-300'}`}>
                    {info.getValue().toFixed(2)}
                </span>
            ),
        }),

        columnHelper.accessor(row => row.efficiency.sortino, {
            id: 'sortino',
            header: ({ column }) => (
                <button
                    onClick={() => column.toggleSorting()}
                    className="flex items-center gap-1 hover:text-emerald-400 transition-colors"
                >
                    Sortino
                    <SortIcon isSorted={column.getIsSorted()} />
                </button>
            ),
            cell: info => (
                <span className="font-mono text-slate-300">
                    {info.getValue().toFixed(2)}
                </span>
            ),
        }),

        // === RISK GROUP ===
        columnHelper.accessor(row => row.risk.max_drawdown, {
            id: 'maxdd',
            header: ({ column }) => (
                <button
                    onClick={() => column.toggleSorting()}
                    className="flex items-center gap-1 hover:text-emerald-400 transition-colors"
                >
                    Max DD
                    <SortIcon isSorted={column.getIsSorted()} />
                </button>
            ),
            cell: info => {
                const value = info.getValue();
                const isRisky = value < -0.20;
                return (
                    <span className={`font-mono ${isRisky ? 'text-red-400' : 'text-slate-300'}`}>
                        {(value * 100).toFixed(1)}%
                    </span>
                );
            },
        }),

        columnHelper.accessor(row => row.risk.tail_ratio, {
            id: 'tail',
            header: ({ column }) => (
                <button
                    onClick={() => column.toggleSorting()}
                    className="flex items-center gap-1 hover:text-emerald-400 transition-colors"
                >
                    Tail Ratio
                    <SortIcon isSorted={column.getIsSorted()} />
                </button>
            ),
            cell: info => (
                <span className="font-mono text-slate-300">
                    {info.getValue().toFixed(2)}
                </span>
            ),
        }),

        // === OVERFITTING GROUP ===
        columnHelper.accessor(row => row.validity.num_trials, {
            id: 'trials',
            header: ({ column }) => (
                <button
                    onClick={() => column.toggleSorting()}
                    className="flex items-center gap-1 hover:text-amber-400 transition-colors"
                >
                    ⚰️ Trials
                    <SortIcon isSorted={column.getIsSorted()} />
                </button>
            ),
            cell: info => <GraveyardBadge trials={info.getValue()} />,
        }),

        // CAGR
        columnHelper.accessor(row => row.returns.cagr, {
            id: 'cagr',
            header: ({ column }) => (
                <button
                    onClick={() => column.toggleSorting()}
                    className="flex items-center gap-1 hover:text-emerald-400 transition-colors"
                >
                    CAGR
                    <SortIcon isSorted={column.getIsSorted()} />
                </button>
            ),
            cell: info => (
                <span className={`font-mono font-semibold ${info.getValue() > 0.15 ? 'text-emerald-400' : 'text-slate-300'
                    }`}>
                    {(info.getValue() * 100).toFixed(1)}%
                </span>
            ),
        }),
    ], []);

    const table = useReactTable({
        data: strategies,
        columns,
        state: { sorting, globalFilter },
        onSortingChange: setSorting,
        onGlobalFilterChange: setGlobalFilter,
        getCoreRowModel: getCoreRowModel(),
        getSortedRowModel: getSortedRowModel(),
        getFilteredRowModel: getFilteredRowModel(),
    });

    return (
        <div className="bg-slate-900/50 backdrop-blur-xl rounded-2xl border border-slate-700/50 overflow-hidden">
            {/* Header */}
            <div className="px-6 py-4 border-b border-slate-700/50 flex items-center justify-between">
                <div>
                    <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                        <span className="text-emerald-400">α</span> Strategy Matrix
                    </h2>
                    <p className="text-sm text-slate-500 mt-1">
                        Statistical validity metrics • DSR-validated
                    </p>
                </div>

                {/* Search */}
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                    <input
                        type="text"
                        placeholder="Filter strategies..."
                        value={globalFilter}
                        onChange={e => setGlobalFilter(e.target.value)}
                        className="pl-10 pr-4 py-2 bg-slate-800 border border-slate-700 rounded-lg
                       text-slate-300 placeholder:text-slate-500 focus:outline-none 
                       focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20"
                    />
                </div>
            </div>

            {/* Table */}
            <div className="overflow-x-auto">
                <table className="w-full">
                    <thead>
                        {table.getHeaderGroups().map(headerGroup => (
                            <tr key={headerGroup.id} className="bg-slate-800/50">
                                {headerGroup.headers.map(header => (
                                    <th
                                        key={header.id}
                                        className="px-4 py-3 text-left text-xs font-medium text-slate-400 
                               uppercase tracking-wider"
                                    >
                                        {header.isPlaceholder
                                            ? null
                                            : flexRender(
                                                header.column.columnDef.header,
                                                header.getContext()
                                            )}
                                    </th>
                                ))}
                            </tr>
                        ))}
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                        {table.getRowModel().rows.map(row => {
                            const isSignificant = isPSRSignificant(row.original.validity.psr);

                            return (
                                <tr
                                    key={row.id}
                                    onClick={() => onSelectStrategy?.(row.original)}
                                    className={`
                    cursor-pointer transition-colors
                    ${isSignificant
                                            ? 'hover:bg-emerald-500/5'
                                            : 'hover:bg-slate-800/50 opacity-60'
                                        }
                  `}
                                >
                                    {row.getVisibleCells().map(cell => (
                                        <td key={cell.id} className="px-4 py-4 whitespace-nowrap">
                                            {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                        </td>
                                    ))}
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>

            {/* Footer */}
            <div className="px-6 py-3 bg-slate-800/30 border-t border-slate-700/50 
                      flex items-center justify-between text-sm text-slate-500">
                <span>
                    {table.getFilteredRowModel().rows.length} strategies
                </span>
                <span>
                    Gray rows: PSR &lt; 95% (not statistically significant)
                </span>
            </div>
        </div>
    );
};

// Sort direction icon
const SortIcon: React.FC<{ isSorted: false | 'asc' | 'desc' }> = ({ isSorted }) => {
    if (!isSorted) {
        return <ArrowUpDown className="w-3 h-3 opacity-40" />;
    }
    return isSorted === 'asc'
        ? <ChevronUp className="w-4 h-4 text-emerald-400" />
        : <ChevronDown className="w-4 h-4 text-emerald-400" />;
};

export default AlphaMatrix;
