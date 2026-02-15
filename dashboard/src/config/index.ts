/**
 * Frontend Configuration
 * =====================
 * Centralized configuration for the dashboard.
 */

export const CONFIG = {
  // Initial capital for the portfolio (should match backend strategy config)
  INITIAL_CAPITAL: 100000,
  
  // API endpoints
  API_BASE_URL: import.meta.env.VITE_API_URL || '/api',
  
  // Display settings
  CURRENCY: 'AUD',
  DATE_FORMAT: 'en-AU',
  
  // Pagination defaults
  DEFAULT_PAGE_SIZE: 50,
  
  // Refresh intervals (in milliseconds)
  REFRESH_INTERVALS: {
    METRICS: 60000,    // 1 minute
    TRADES: 300000,    // 5 minutes
  },
} as const;

export default CONFIG;
