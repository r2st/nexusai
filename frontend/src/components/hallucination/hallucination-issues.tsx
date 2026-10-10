'use client';

import { AlertTriangle, AlertCircle, Info, ExternalLink } from 'lucide-react';
import type { HallucinationLogEntry, HallucinationIssue } from './types';
import { cn } from '@/lib/utils';

const severityConfig = {
  high: {
    icon: AlertTriangle,
    color: 'text-red-500',
    bgColor: 'bg-red-500/10',
    borderColor: 'border-red-500/20',
  },
  medium: {
    icon: AlertCircle,
    color: 'text-yellow-500',
    bgColor: 'bg-yellow-500/10',
    borderColor: 'border-yellow-500/20',
  },
  low: {
    icon: Info,
    color: 'text-blue-500',
    bgColor: 'bg-blue-500/10',
    borderColor: 'border-blue-500/20',
  },
};

interface IssueCardProps {
  issue: HallucinationIssue;
}

function IssueCard({ issue }: IssueCardProps) {
  const config = severityConfig[issue.severity] || severityConfig.low;
  const Icon = config.icon;

  return (
    <div
      className={cn(
        'rounded-lg border p-4',
        config.bgColor,
        config.borderColor
      )}
    >
      <div className="flex items-start gap-3">
        <div className={cn('mt-0.5', config.color)}>
          <Icon className="h-5 w-5" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={cn('text-sm font-medium', config.color)}>
              {issue.type.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
            </span>
            <span
              className={cn(
                'text-xs px-2 py-0.5 rounded-full capitalize',
                config.bgColor,
                config.color
              )}
            >
              {issue.severity}
            </span>
          </div>
          <p className="text-sm text-muted-foreground">{issue.description}</p>
          {issue.evidence && Object.keys(issue.evidence).length > 0 && (
            <div className="mt-2 text-xs text-muted-foreground">
              <span className="font-medium">Evidence: </span>
              {Object.entries(issue.evidence)
                .slice(0, 3)
                .map(([key, value]) => (
                  <span key={key} className="mr-2">
                    {key}: {String(value).substring(0, 50)}
                    {String(value).length > 50 ? '...' : ''}
                  </span>
                ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

interface HallucinationIssuesListProps {
  issues: HallucinationIssue[];
}

export function HallucinationIssuesList({ issues }: HallucinationIssuesListProps) {
  if (!issues || issues.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
        <p>No issues detected</p>
      </div>
    );
  }

  // Sort by severity
  const sortedIssues = [...issues].sort((a, b) => {
    const order = { high: 0, medium: 1, low: 2 };
    return (order[a.severity] || 2) - (order[b.severity] || 2);
  });

  return (
    <div className="space-y-3">
      {sortedIssues.map((issue, index) => (
        <IssueCard key={`${issue.type}-${index}`} issue={issue} />
      ))}
    </div>
  );
}

// Log entry card component
interface LogEntryCardProps {
  entry: HallucinationLogEntry;
  onViewDetails?: (entry: HallucinationLogEntry) => void;
}

export function LogEntryCard({ entry, onViewDetails }: LogEntryCardProps) {
  const scoreColor = entry.hallucination_score
    ? entry.hallucination_score > 0.7
      ? 'text-red-500'
      : entry.hallucination_score > 0.4
      ? 'text-yellow-500'
      : 'text-green-500'
    : 'text-muted-foreground';

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Unknown';
    try {
      const date = new Date(dateStr);
      return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div
      className={cn(
        'rounded-lg border p-4',
        entry.is_hallucination ? 'border-red-500/30 bg-red-500/5' : 'bg-card'
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            {entry.is_hallucination ? (
              <span className="flex items-center gap-1 text-red-500 text-sm font-medium">
                <AlertTriangle className="h-4 w-4" />
                Hallucination Detected
              </span>
            ) : (
              <span className="flex items-center gap-1 text-green-500 text-sm font-medium">
                <Info className="h-4 w-4" />
                Clean Response
              </span>
            )}
            <span className="text-xs text-muted-foreground">
              {formatDate(entry.created_at)}
            </span>
          </div>

          <div className="flex items-center gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">Score: </span>
              <span className={cn('font-medium', scoreColor)}>
                {entry.hallucination_score !== null
                  ? `${(entry.hallucination_score * 100).toFixed(1)}%`
                  : 'N/A'}
              </span>
            </div>
            {entry.grounding_score !== null && (
              <div>
                <span className="text-muted-foreground">Grounding: </span>
                <span className="font-medium">
                  {(entry.grounding_score * 100).toFixed(1)}%
                </span>
              </div>
            )}
            {entry.confidence !== null && (
              <div>
                <span className="text-muted-foreground">Confidence: </span>
                <span className="font-medium">
                  {(entry.confidence * 100).toFixed(1)}%
                </span>
              </div>
            )}
            {entry.duration_ms !== null && (
              <div>
                <span className="text-muted-foreground">Duration: </span>
                <span className="font-medium">{entry.duration_ms.toFixed(0)}ms</span>
              </div>
            )}
          </div>

          {entry.issues && entry.issues.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {entry.issues.slice(0, 3).map((issue, idx) => (
                <span
                  key={idx}
                  className={cn(
                    'text-xs px-2 py-0.5 rounded-full',
                    severityConfig[issue.severity]?.bgColor || 'bg-muted',
                    severityConfig[issue.severity]?.color || 'text-muted-foreground'
                  )}
                >
                  {issue.type.replace(/_/g, ' ')}
                </span>
              ))}
              {entry.issues.length > 3 && (
                <span className="text-xs text-muted-foreground">
                  +{entry.issues.length - 3} more
                </span>
              )}
            </div>
          )}
        </div>

        {onViewDetails && (
          <button
            onClick={() => onViewDetails(entry)}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <ExternalLink className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
}

// List of log entries
interface HallucinationLogsListProps {
  logs: HallucinationLogEntry[];
  onViewDetails?: (entry: HallucinationLogEntry) => void;
}

export function HallucinationLogsList({ logs, onViewDetails }: HallucinationLogsListProps) {
  if (!logs || logs.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
        <p>No hallucination checks recorded yet</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {logs.map((entry) => (
        <LogEntryCard key={entry.id} entry={entry} onViewDetails={onViewDetails} />
      ))}
    </div>
  );
}
