/**
 * Main Application Component
 * ==========================
 */

import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Sidebar } from './components/layout/Sidebar';
import Dashboard from './components/layout/Dashboard';
import { TruthEngine } from './pages/TruthEngine';
import { Quant1Dashboard } from './pages/Quant1Dashboard';

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 ml-56">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/truth-engine" element={<TruthEngine />} />
            <Route path="/quant1" element={<Quant1Dashboard />} />
            <Route path="/quant2" element={<div className="p-8 text-gray-500">Quant 2 Dashboard — coming soon</div>} />
            <Route path="/scanner" element={<div className="p-8 text-gray-500">Scanner Dashboard — coming soon</div>} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
};

export default App;
