export type DORAMetricValue = number | string | null;

export interface DORAWidgetPayload {
  type: 'dora';
  title?: string;
  timeframe?: string;
  metrics: {
    deploymentFrequency?: DORAMetricValue;
    leadTimeForChanges?: DORAMetricValue;
    meanTimeToRecovery?: DORAMetricValue;
    changeFailureRate?: DORAMetricValue;
  };
  units?: {
    deploymentFrequency?: string;
    leadTimeForChanges?: string;
    meanTimeToRecovery?: string;
    changeFailureRate?: string;
  };
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
