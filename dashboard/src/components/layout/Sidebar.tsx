/**
 * Sidebar Navigation Component
 * ============================
 * Persistent sidebar for navigating between dashboard pages.
 */

import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  TrendingUp,
  Brain,
  Search,
  Shield,
} from 'lucide-react';

const navItems = [
  { to: '/', label: 'Portfolio', icon: LayoutDashboard },
  { to: '/quant1', label: 'Quant 1.0', icon: TrendingUp },
  { to: '/quant2', label: 'Quant 2.0', icon: Brain },
  { to: '/scanner', label: 'Scanner', icon: Search },
  { to: '/truth-engine', label: 'Truth Engine', icon: Shield },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="fixed left-0 top-0 h-screen w-56 bg-slate-900 border-r border-slate-800 flex flex-col z-40">
      {/* Logo / Brand */}
      <div className="px-4 py-5 border-b border-slate-800">
        <h2 className="text-lg font-bold text-white tracking-tight">QuantDash</h2>
        <p className="text-xs text-slate-500 mt-0.5">Investment Agent</p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`
            }
          >
            <item.icon className="w-4 h-4 flex-shrink-0" />
            {item.label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-slate-800">
        <p className="text-xs text-slate-600">v2.0.0</p>
      </div>
    </aside>
  );
};

export default Sidebar;
