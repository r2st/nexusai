export type DORAMetricValue = number | string | null;
export type DORATrend = 'up' | 'down' | 'flat';
export type DORAPerformanceLevel = 'elite' | 'high' | 'medium' | 'low';

export interface DORAMetricDetail {
  value?: DORAMetricValue;
  trend?: DORATrend;
  trendValue?: number | string; // e.g. 12 for "12%"
  level?: DORAPerformanceLevel;
  sparkline?: number[]; // array of numbers for mini chart
  description?: string;
}

export interface DORAChartDataPoint {
  date: string; // ISO date or label like "Jan 5"
  deploymentFrequency?: number;
  leadTimeForChanges?: number;
  timeToRestoreService?: number;
  changeFailureRate?: number;
}

export interface DORAWidgetPayload {
  type: 'dora';
  title?: string;
  timeframe?: string;
  overallLevel?: DORAPerformanceLevel;
  metrics: {
    deploymentFrequency?: DORAMetricValue | DORAMetricDetail;
    leadTimeForChanges?: DORAMetricValue | DORAMetricDetail;
    meanTimeToRecovery?: DORAMetricValue | DORAMetricDetail;
    changeFailureRate?: DORAMetricValue | DORAMetricDetail;
  };
  units?: {
    deploymentFrequency?: string;
    leadTimeForChanges?: string;
    meanTimeToRecovery?: string;
    changeFailureRate?: string;
  };
  chartData?: DORAChartDataPoint[]; // time-series data for full charts
}

export interface SPACEWidgetPayload {
  type: 'space';
  title?: string;
  scale?: string;
  dimensions: {
    satisfaction?: number | null;
    performance?: number | null;
    activity?: number | null;
    communication?: number | null;
    efficiency?: number | null;
  };
  notes?: string[];
}

export interface InsightsWidgetPayload {
  type: 'insights';
  title?: string;
  summary?: string;
  items: Array<{
    label: string;
    value: string;
    trend?: 'up' | 'down' | 'flat';
  }>;
}

export interface PipelineProgressWidgetPayload {
  type: 'pipeline_progress';
  title?: string;
  pipelineId: number;
  pipelineName: string;
  status: 'TASK_CREATED' | 'TASK_RERUN' | 'TASK_RUNNING' | 'TASK_COMPLETED' | 'TASK_FAILED' | 'TASK_CANCELLED' | 'TASK_PARTIAL';
  progress: number; // 0-100
  totalTasks: number;
  finishedTasks: number;
  currentStage?: string;
  startedAt?: string;
  finishedAt?: string;
  spentSeconds?: number;
  message?: string;
  errorMessage?: string;
  pollUrl?: string; // URL to poll for updates
  pollIntervalMs?: number; // How often to poll (default 2000ms)
  projectName?: string;
  repoName?: string;
  estimatedDurationSeconds?: number; // Estimated total duration for this pipeline type
}

export type WidgetPayload = DORAWidgetPayload | SPACEWidgetPayload | InsightsWidgetPayload | PipelineProgressWidgetPayload;
