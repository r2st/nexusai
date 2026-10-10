/**
 * Hallucination detection API client.
 */

import { api } from '@/lib/api';
import type {
  HallucinationAnalytics,
  HallucinationTrends,
  HallucinationLogs,
  HallucinationCheckResult,
  HallucinationGranularity,
} from './types';

export const hallucinationApi = {
  /**
   * Perform a hallucination check on a response.
   */
  async check(
    query: string,
    response: string,
    options?: {
      context?: string[];
      sources?: Array<{ id: string; content: string; title?: string; url?: string }>;
      checkConsistency?: boolean;
    }
  ): Promise<HallucinationCheckResult> {
    const res = await api.post('/hallucination/check', {
      query,
      response,
      context: options?.context,
      sources: options?.sources,
      check_consistency: options?.checkConsistency ?? false,
    });
    return res.data;
  },

  /**
   * Get hallucination analytics summary.
   */
  async getAnalytics(days: number = 30): Promise<HallucinationAnalytics> {
    const response = await api.get('/hallucination/analytics', { params: { days } });
    return response.data;
  },

  /**
   * Get hallucination trends over time.
   */
  async getTrends(
    days: number = 30,
    granularity: HallucinationGranularity = 'daily'
  ): Promise<HallucinationTrends> {
    const response = await api.get('/hallucination/trends', {
      params: { days, granularity },
    });
    return response.data;
  },

  /**
   * Get recent hallucination detection logs.
   */
  async getLogs(
    limit: number = 50,
    onlyHallucinations: boolean = false
  ): Promise<HallucinationLogs> {
    const response = await api.get('/hallucination/logs', {
      params: { limit, only_hallucinations: onlyHallucinations },
    });
    return response.data;
  },
};
