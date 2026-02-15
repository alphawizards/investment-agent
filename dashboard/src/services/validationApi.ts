/**
 * Validation API Service
 * ====================
 * Service for fetching Truth Engine validation data from backend API.
 */

import axios from 'axios';
import type { ValidationResponse, StrategyMetrics } from '../types/strategy';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const validationApi = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Fetch all validated strategies from the backend.
 */
export async function fetchValidatedStrategies(): Promise<ValidationResponse> {
  try {
    const response = await validationApi.get<ValidationResponse>('/validation/strategies');
    return response.data;
  } catch (error) {
    console.error('Failed to fetch validated strategies:', error);
    throw error;
  }
}

/**
 * Fetch validation data directly from reports directory.
 */
export async function fetchValidationFromReports(): Promise<ValidationResponse> {
  try {
    const response = await validationApi.get<ValidationResponse>('/validation/from-reports');
    return response.data;
  } catch (error) {
    console.error('Failed to fetch validation from reports:', error);
    throw error;
  }
}

/**
 * Calculate DSR for a given Sharpe ratio.
 */
export async function calculateDSR(
  sharpeRatio: number,
  nTrials: number = 1,
  nSamples: number = 252
): Promise<{
  sharpe_ratio: number;
  deflated_sharpe_ratio: number;
  probabilistic_sharpe_ratio: number;
  is_significant: boolean;
  confidence_level: string;
  interpretation: string;
}> {
  try {
    const response = await validationApi.post('/validation/calculate-dsr', {
      sharpe_ratio: sharpeRatio,
      n_trials: nTrials,
      n_samples: nSamples,
    });
    return response.data;
  } catch (error) {
    console.error('Failed to calculate DSR:', error);
    throw error;
  }
}

export default validationApi;
