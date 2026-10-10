/**
 * Types for cost analytics dashboard.
 */

export interface CostSummary {
  total_cost: number;
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  request_count: number;
  avg_latency_ms: number | null;
  success_rate: number;
  period_start: string;
  period_end: string;
}

export interface TimeSeriesDataPoint {
  period: string;
  total_cost: number;
  total_tokens: number;
  request_count: number;
}

export interface CostTimeSeries {
  data: TimeSeriesDataPoint[];
  granularity: string;
  period_start: string;
  period_end: string;
}

export interface BreakdownItem {
  name: string;
  total_cost: number;
  total_tokens: number;
  request_count: number;
  avg_latency_ms: number | null;
  percentage: number;
}

export interface CostBreakdown {
  items: BreakdownItem[];
  total_cost: number;
  period_start: string;
  period_end: string;
}

export interface CostForecast {
  projected_monthly_cost: number;
  daily_average: number;
  confidence: 'low' | 'medium' | 'high';
  basis_days: number;
  basis_cost: number;
  basis_requests: number;
}

// Period selector options
export type CostPeriod = '7d' | '30d' | '90d';

// Granularity options
export type CostGranularity = 'hourly' | 'daily' | 'weekly' | 'monthly';
