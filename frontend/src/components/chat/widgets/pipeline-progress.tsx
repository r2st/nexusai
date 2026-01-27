'use client';

import { useState, useEffect, useCallback } from 'react';
import { cn } from '@/lib/utils';
import type { PipelineProgressWidgetPayload } from './types';

interface PipelineProgressWidgetProps {
  widget: PipelineProgressWidgetPayload;
}

interface PipelineStatus {
  status: PipelineProgressWidgetPayload['status'];
  progress: number;
  totalTasks: number;
  finishedTasks: number;
  spentSeconds?: number;
  message?: string;
  errorMessage?: string;
  finishedAt?: string;
}

const STATUS_CONFIG = {
  TASK_CREATED: { label: 'Queued', color: 'bg-gray-400', textColor: 'text-gray-600' },
  TASK_RERUN: { label: 'Rerunning', color: 'bg-blue-400', textColor: 'text-blue-600' },
  TASK_RUNNING: { label: 'Running', color: 'bg-blue-500', textColor: 'text-blue-600' },
  TASK_COMPLETED: { label: 'Completed', color: 'bg-emerald-500', textColor: 'text-emerald-600' },
  TASK_FAILED: { label: 'Failed', color: 'bg-rose-500', textColor: 'text-rose-600' },
  TASK_CANCELLED: { label: 'Cancelled', color: 'bg-amber-500', textColor: 'text-amber-600' },
  TASK_PARTIAL: { label: 'Partial', color: 'bg-amber-400', textColor: 'text-amber-600' },
};

function formatDuration(seconds: number): string {
  if (seconds < 0) return '0s';
  const roundedSeconds = Math.round(seconds);
  if (roundedSeconds < 60) return `${roundedSeconds}s`;
  const minutes = Math.floor(roundedSeconds / 60);
  const secs = roundedSeconds % 60;
  if (minutes < 60) return `${minutes}m ${secs}s`;
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hours}h ${mins}m`;
}

function calculateETA(
  elapsedSeconds: number,
  progressPercent: number,
  estimatedDurationSeconds?: number
): number | null {
  // If we have an estimated duration, use it when progress is low
  if (estimatedDurationSeconds && estimatedDurationSeconds > 0) {
    if (progressPercent < 5 || elapsedSeconds < 10) {
      // Use estimated duration minus elapsed time
      return Math.max(0, estimatedDurationSeconds - elapsedSeconds);
    }
  }

  // Need at least 5% progress and 10 seconds elapsed for a reasonable estimate
  if (progressPercent < 5 || elapsedSeconds < 10) return null;

  // Calculate rate: percent per second
  const rate = progressPercent / elapsedSeconds;
  if (rate <= 0) return null;

  // Calculate remaining time
  const remainingPercent = 100 - progressPercent;
  const remainingSeconds = remainingPercent / rate;

  // Cap at 2 hours max estimate to avoid showing unrealistic times
  return Math.min(remainingSeconds, 7200);
}

export function PipelineProgressWidget({ widget }: PipelineProgressWidgetProps) {
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus>({
    status: widget.status,
    progress: widget.progress,
    totalTasks: widget.totalTasks,
    finishedTasks: widget.finishedTasks,
    spentSeconds: widget.spentSeconds,
    message: widget.message,
    errorMessage: widget.errorMessage,
    finishedAt: widget.finishedAt,
  });
  const [isPolling, setIsPolling] = useState(false);
  // Initialize elapsed time from widget, but it will be updated immediately by the first poll
  const [elapsedTime, setElapsedTime] = useState(widget.spentSeconds || 0);
  const [hasInitialized, setHasInitialized] = useState(false);

  const isTerminalStatus = ['TASK_COMPLETED', 'TASK_FAILED', 'TASK_CANCELLED'].includes(pipelineStatus.status);

  // Poll for updates
  const pollStatus = useCallback(async (isInitialPoll = false) => {
    if (!widget.pollUrl) return;
    // Only skip polling for terminal status after initialization
    if (!isInitialPoll && isTerminalStatus) return;

    try {
      // Get auth token for authenticated requests
      const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
      const headers: Record<string, string> = {};
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(widget.pollUrl, {
        credentials: 'include',
        headers,
      });
      if (response.ok) {
        const data = await response.json();

        // Calculate progress percentage
        const progress = data.totalTasks > 0
          ? Math.round((data.finishedTasks / data.totalTasks) * 100)
          : 0;

        setPipelineStatus({
          status: data.status,
          progress,
          totalTasks: data.totalTasks,
          finishedTasks: data.finishedTasks,
          spentSeconds: data.spentSeconds,
          message: data.message,
          errorMessage: data.errorName || data.message,
          finishedAt: data.finishedAt,
        });

        // Always update elapsed time from server response
        if (data.spentSeconds !== undefined && data.spentSeconds !== null) {
          setElapsedTime(data.spentSeconds);
        }

        if (isInitialPoll) {
          setHasInitialized(true);
        }
      } else {
        console.error('Pipeline poll failed:', response.status, response.statusText);
        if (isInitialPoll) {
          setHasInitialized(true);
        }
      }
    } catch (error) {
      console.error('Failed to poll pipeline status:', error);
      if (isInitialPoll) {
        setHasInitialized(true);
      }
    }
  }, [widget.pollUrl, isTerminalStatus]);

  // Initial poll on mount to get current state (especially spentSeconds)
  useEffect(() => {
    if (!widget.pollUrl || hasInitialized) return;

    // Immediately fetch current status on mount
    pollStatus(true);
  }, [widget.pollUrl, hasInitialized, pollStatus]);

  // Start polling when component mounts (for ongoing updates)
  useEffect(() => {
    if (isTerminalStatus || !widget.pollUrl || !hasInitialized) {
      setIsPolling(false);
      return;
    }

    setIsPolling(true);
    const pollInterval = widget.pollIntervalMs || 2000;

    // Set up interval for ongoing updates
    const intervalId = setInterval(() => pollStatus(false), pollInterval);

    return () => {
      clearInterval(intervalId);
      setIsPolling(false);
    };
  }, [widget.pollUrl, widget.pollIntervalMs, isTerminalStatus, hasInitialized, pollStatus]);

  // Elapsed time counter for running pipelines
  useEffect(() => {
    if (pipelineStatus.status !== 'TASK_RUNNING') return;

    const timer = setInterval(() => {
      setElapsedTime((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(timer);
  }, [pipelineStatus.status]);

  const statusConfig = STATUS_CONFIG[pipelineStatus.status] || STATUS_CONFIG.TASK_CREATED;
  const progressPercent = Math.min(100, Math.max(0, pipelineStatus.progress));

  // Default estimated duration for data sync if not provided (10 minutes)
  const DEFAULT_ESTIMATED_DURATION = 600;
  const estimatedDuration = widget.estimatedDurationSeconds || DEFAULT_ESTIMATED_DURATION;

  // Calculate estimated time remaining
  const estimatedTimeRemaining = pipelineStatus.status === 'TASK_RUNNING'
    ? calculateETA(elapsedTime, progressPercent, estimatedDuration)
    : null;

  // Show estimated total time
  const estimatedTotalTime = estimatedDuration;

  return (
    <section className="rounded-xl border border-border bg-background p-4 shadow-sm">
      {/* Header */}
      <header className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h4 className="text-sm font-semibold text-foreground">
            {widget.title || 'Pipeline Progress'}
          </h4>
          <span
            className={cn(
              'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
              statusConfig.color,
              'text-white'
            )}
          >
            {statusConfig.label}
            {isPolling && pipelineStatus.status === 'TASK_RUNNING' && (
              <span className="ml-1 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-white" />
            )}
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          {elapsedTime > 0 && (
            <span>{formatDuration(elapsedTime)}</span>
          )}
          {pipelineStatus.status === 'TASK_RUNNING' && estimatedTotalTime > 0 && (
            <>
              <span className="text-muted-foreground/50">/</span>
              <span>~{formatDuration(Math.max(estimatedTotalTime, elapsedTime))}</span>
            </>
          )}
          {estimatedTimeRemaining !== null && estimatedTimeRemaining > 0 && (
            <>
              <span className="text-muted-foreground/50">•</span>
              <span className="text-blue-500">~{formatDuration(estimatedTimeRemaining)} remaining</span>
            </>
          )}
        </div>
      </header>

      {/* Project/Repo info */}
      {(widget.projectName || widget.repoName) && (
        <div className="mb-3 flex items-center gap-4 text-xs text-muted-foreground">
          {widget.projectName && (
            <span>Project: <span className="font-medium text-foreground">{widget.projectName}</span></span>
          )}
          {widget.repoName && (
            <span>Repo: <span className="font-medium text-foreground">{widget.repoName}</span></span>
          )}
        </div>
      )}

      {/* Progress bar */}
      <div className="mb-3">
        <div className="mb-1 flex items-center justify-between text-xs">
          <span className="text-muted-foreground">
            {pipelineStatus.finishedTasks} / {pipelineStatus.totalTasks} tasks
          </span>
          <span className={cn('font-medium', statusConfig.textColor)}>
            {progressPercent}%
          </span>
        </div>
        <div className="h-2.5 overflow-hidden rounded-full bg-muted">
          {/* Show indeterminate animation when running but at 0% progress */}
          {pipelineStatus.status === 'TASK_RUNNING' && progressPercent === 0 ? (
            <div
              className="h-full w-1/3 rounded-full bg-blue-500 animate-indeterminate"
            />
          ) : (
            <div
              className={cn(
                'h-full rounded-full transition-all duration-500',
                statusConfig.color,
                pipelineStatus.status === 'TASK_RUNNING' && 'animate-pulse'
              )}
              style={{ width: `${progressPercent}%` }}
            />
          )}
        </div>
      </div>

      {/* Status message */}
      {pipelineStatus.status === 'TASK_RUNNING' && (
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 text-muted-foreground">
            <svg
              className="h-4 w-4 animate-spin text-blue-500"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <span>Syncing data from GitHub...</span>
          </div>
          {estimatedTimeRemaining !== null && estimatedTimeRemaining > 0 && (
            <span className="text-blue-500 font-medium">
              ETA: {formatDuration(estimatedTimeRemaining)}
            </span>
          )}
        </div>
      )}

      {/* Completed message */}
      {pipelineStatus.status === 'TASK_COMPLETED' && (
        <div className="flex items-center gap-2 text-xs text-emerald-600">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          <span>Data sync completed successfully!</span>
        </div>
      )}

      {/* Error message */}
      {pipelineStatus.status === 'TASK_FAILED' && pipelineStatus.errorMessage && (
        <div className="mt-2 rounded-lg border border-rose-200 bg-rose-50 p-2 text-xs text-rose-700 dark:border-rose-800 dark:bg-rose-900/20 dark:text-rose-400">
          <p className="font-medium">Error:</p>
          <p className="mt-1 break-words">{pipelineStatus.errorMessage}</p>
        </div>
      )}

      {/* Pipeline ID footer */}
      <div className="mt-3 flex items-center justify-between border-t border-border/50 pt-2 text-xs text-muted-foreground">
        <span>Pipeline ID: {widget.pipelineId}</span>
        {pipelineStatus.finishedAt && (
          <span>Finished: {new Date(pipelineStatus.finishedAt).toLocaleTimeString()}</span>
        )}
      </div>
    </section>
  );
}
