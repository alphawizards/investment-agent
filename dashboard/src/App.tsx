/**
 * Main Application Component
 * ==========================
 */

import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';
import { Sidebar } from './components/layout/Sidebar';
import { Dashboard as TradeTracker } from './pages/TradeTracker';
import { TruthEngine } from './pages/TruthEngine';
import { Quant1Dashboard } from './pages/Quant1Dashboard';
import { Quant2Dashboard } from './pages/Quant2Dashboard';
import ScannerDashboard from './pages/ScannerDashboard';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60, // 1 minute
      gcTime: 1000 * 60 * 5, // 5 minutes (formerly cacheTime)
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <Toaster 
        position="top-right" 
        richColors 
        closeButton
        toastOptions={{
          style: {
            background: '#1e293b',
            color: '#f8fafc',
            border: '1px solid #334155',
          },
        }}
      />
      <BrowserRouter>
        <div className="flex min-h-screen bg-slate-950">
          <Sidebar />
          <main className="flex-1 ml-56">
            <Routes>
              <Route path="/" element={<TradeTracker />} />
              <Route path="/truth-engine" element={<TruthEngine />} />
              <Route path="/quant1" element={<Quant1Dashboard />} />
              <Route path="/quant2" element={<Quant2Dashboard />} />
              <Route path="/scanner" element={<ScannerDashboard />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

export default App;
