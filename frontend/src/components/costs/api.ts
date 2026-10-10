/**
 * Cost analytics API client.
 */

import { api } from '@/lib/api';
import type {
  CostSummary,
  CostTimeSeries,
  CostBreakdown,
  CostForecast,
  CostGranularity,
} from './types';

export const costsApi = {
  /**
   * Get cost summary for a period.
   */
  async getSummary(days: number = 30, userId?: string): Promise<CostSummary> {
    const params: Record<string, string | number> = { days };
    if (userId) params.user_id = userId;
    const response = await api.get('/costs/summary', { params });
    return response.data;
  },

  /**
   * Get cost time-series data for charts.
   */
  async getTimeSeries(
    days: number = 30,
    granularity: CostGranularity = 'daily',
    filters?: {
      userId?: string;
      model?: string;
      provider?: string;
    }
  ): Promise<CostTimeSeries> {
    const params: Record<string, string | number> = { days, granularity };
    if (filters?.userId) params.user_id = filters.userId;
    if (filters?.model) params.model = filters.model;
    if (filters?.provider) params.provider = filters.provider;
    const response = await api.get('/costs/time-series', { params });
    return response.data;
  },

  /**
   * Get cost breakdown by model.
   */
  async getBreakdownByModel(days: number = 30): Promise<CostBreakdown> {
    const response = await api.get('/costs/breakdown/model', { params: { days } });
    return response.data;
  },

  /**
   * Get cost breakdown by provider.
   */
  async getBreakdownByProvider(days: number = 30): Promise<CostBreakdown> {
    const response = await api.get('/costs/breakdown/provider', { params: { days } });
    return response.data;
  },

  /**
   * Get cost forecast.
   */
  async getForecast(): Promise<CostForecast> {
    const response = await api.get('/costs/forecast');
    return response.data;
  },
};
