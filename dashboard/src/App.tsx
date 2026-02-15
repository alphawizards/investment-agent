/**
 * Main Application Component
 * ==========================
 */

import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Dashboard from './components/layout/Dashboard';
import { TruthEngine } from './pages/TruthEngine';

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/truth-engine" element={<TruthEngine />} />
        <Route path="/quant1" element={<div className="p-8 text-gray-500">Quant 1 Dashboard — coming soon</div>} />
        <Route path="/quant2" element={<div className="p-8 text-gray-500">Quant 2 Dashboard — coming soon</div>} />
        <Route path="/scanner" element={<div className="p-8 text-gray-500">Scanner Dashboard — coming soon</div>} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
