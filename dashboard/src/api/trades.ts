/**
 * Trade API Client
 * ================
 * Axios-based API client for trade operations.
 */

import axios, { AxiosInstance } from 'axios';
import type {
  Trade,
  TradeCreate,
  TradeUpdate,
  TradeListResponse,
  PortfolioMetrics,
  DashboardSummary,
  TradeStats,
  TradeFilters,
} from '../types/trade';

// API base URL - uses proxy in development
const API_BASE_URL = '/api/trades';

// Create axios instance with defaults
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

// Request interceptor for logging
apiClient.interceptors.request.use(
  (config) => {
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('[API Error]', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

/**
 * Trade API functions
 */
export const tradeApi = {
  // ============== CRUD ==============

  /**
   * Create a new trade
   */
  create: async (trade: TradeCreate): Promise<Trade> => {
    const response = await apiClient.post<Trade>('/', trade);
    return response.data;
  },

  /**
   * Get paginated list of trades
   */
  getAll: async (
    page: number = 1,
    pageSize: number = 50,
    filters?: TradeFilters
  ): Promise<TradeListResponse> => {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
    });

    if (filters?.ticker) params.append('ticker', filters.ticker);
    if (filters?.status) params.append('status', filters.status);
    if (filters?.strategy) params.append('strategy', filters.strategy);
    if (filters?.start_date) params.append('start_date', filters.start_date);
    if (filters?.end_date) params.append('end_date', filters.end_date);
    if (filters?.sort_by) params.append('sort_by', filters.sort_by);
    if (filters?.sort_desc !== undefined) {
      params.append('sort_desc', filters.sort_desc.toString());
    }

    const response = await apiClient.get<TradeListResponse>(`/?${params}`);
    return response.data;
  },

  /**
   * Get a single trade by ID
   */
  getById: async (id: number): Promise<Trade> => {
    const response = await apiClient.get<Trade>(`/${id}`);
    return response.data;
  },

  /**
   * Update a trade
   */
  update: async (id: number, data: TradeUpdate): Promise<Trade> => {
    const response = await apiClient.patch<Trade>(`/${id}`, data);
    return response.data;
  },

  /**
   * Close a trade
   */
  close: async (
    id: number,
    exitPrice: number,
    exitDate?: string
  ): Promise<Trade> => {
    const params = new URLSearchParams({
      exit_price: exitPrice.toString(),
    });
    if (exitDate) params.append('exit_date', exitDate);

    const response = await apiClient.post<Trade>(`/${id}/close?${params}`);
    return response.data;
  },

  /**
   * Delete a trade
   */
  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/${id}`);
  },

  // ============== Metrics ==============

  /**
   * Get portfolio metrics
   */
  getPortfolioMetrics: async (
    initialCapital: number = 100000
  ): Promise<PortfolioMetrics> => {
    const response = await apiClient.get<PortfolioMetrics>(
      `/metrics/portfolio?initial_capital=${initialCapital}`
    );
    return response.data;
  },

  /**
   * Get dashboard summary
   */
  getDashboardSummary: async (
    initialCapital: number = 100000
  ): Promise<DashboardSummary> => {
    const response = await apiClient.get<DashboardSummary>(
      `/metrics/dashboard?initial_capital=${initialCapital}`
    );
    return response.data;
  },

  /**
   * Get stats grouped by ticker
   */
  getStatsByTicker: async (): Promise<TradeStats[]> => {
    const response = await apiClient.get<TradeStats[]>('/metrics/by-ticker');
    return response.data;
  },

  // ============== Utilities ==============

  /**
   * Generate a unique trade ID
   */
  generateTradeId: async (prefix: string = 'TRD'): Promise<string> => {
    const response = await apiClient.get<{ trade_id: string }>(
      `/utils/generate-id?prefix=${prefix}`
    );
    return response.data.trade_id;
  },
};

export default tradeApi;
