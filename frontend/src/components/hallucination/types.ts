/**
 * Types for hallucination detection dashboard.
 */

export interface HallucinationAnalytics {
  total_checks: number;
  hallucination_count: number;
  hallucination_rate: number;
  avg_hallucination_score: number;
  avg_grounding_score: number;
  avg_relevance_score: number;
  avg_confidence: number;
  period_days: number;
}

export interface TrendDataPoint {
  period: string;
  total_checks: number;
  hallucination_count: number;
  hallucination_rate: number;
  avg_hallucination_score: number;
}

export interface HallucinationTrends {
  data: TrendDataPoint[];
  granularity: string;
  period_start: string;
  period_end: string;
}

export interface HallucinationIssue {
  type: string;
  severity: 'low' | 'medium' | 'high';
  description: string;
  evidence: Record<string, unknown>;
}

export interface HallucinationLogEntry {
  id: string;
  trace_id: string | null;
  hallucination_score: number | null;
  grounding_score: number | null;
  is_hallucination: boolean;
  confidence: number | null;
  issues: HallucinationIssue[] | null;
  check_type: string | null;
  duration_ms: number | null;
  created_at: string | null;
}

export interface HallucinationLogs {
  logs: HallucinationLogEntry[];
  total: number;
}

export interface HallucinationCheckResult {
  is_hallucination: boolean;
  confidence: number;
  hallucination_score: number;
  grounding_score: number | null;
  consistency_score: number | null;
  relevance_score: number | null;
  factuality_score: number | null;
  issues: HallucinationIssue[];
  check_types_performed: string[];
  duration_ms: number;
}

// Period selector options
export type HallucinationPeriod = '7d' | '30d' | '90d';

// Granularity options
export type HallucinationGranularity = 'hourly' | 'daily' | 'weekly';
