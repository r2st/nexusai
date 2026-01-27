'use client';

import { memo, useState, useCallback } from 'react';
import {
  GitBranch,
  GitPullRequest,
  AlertTriangle,
  Calendar,
  Filter,
  X,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Clock,
  Users,
  FileCode,
  Activity,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------

export interface RepoContext {
  id: string;
  name: string;
  full_name: string;
  url: string;
  default_branch: string;
  language?: string;
  last_commit?: string;
}

export interface PRContext {
  id: string;
  number: number;
  title: string;
  url: string;
  state: 'open' | 'closed' | 'merged';
  author: string;
  created_at: string;
  files_changed?: number;
  additions?: number;
  deletions?: number;
}

export interface IncidentContext {
  id: string;
  title: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  status: 'investigating' | 'identified' | 'monitoring' | 'resolved';
  started_at: string;
  resolved_at?: string;
  affected_services?: string[];
}

export interface TimeframeContext {
  start: string;
  end: string;
  preset?: 'last_hour' | 'last_24h' | 'last_7d' | 'last_30d' | 'custom';
}

export interface ContextPanelProps {
  repo?: RepoContext | null;
  pr?: PRContext | null;
  incident?: IncidentContext | null;
  timeframe?: TimeframeContext | null;
  filters?: Record<string, unknown>;
  onRepoChange?: (repo: RepoContext | null) => void;
  onPRChange?: (pr: PRContext | null) => void;
  onIncidentChange?: (incident: IncidentContext | null) => void;
  onTimeframeChange?: (timeframe: TimeframeContext | null) => void;
  onFiltersChange?: (filters: Record<string, unknown>) => void;
  className?: string;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

// -----------------------------------------------------------------------------
// Context Panel Component
// -----------------------------------------------------------------------------

export const ContextPanel = memo(function ContextPanel({
  repo,
  pr,
  incident,
  timeframe,
  filters,
  onRepoChange,
  onPRChange,
  onIncidentChange,
  onTimeframeChange,
  onFiltersChange,
  className,
  collapsed = false,
  onToggleCollapse,
}: ContextPanelProps) {
  const hasContext = repo || pr || incident || timeframe || (filters && Object.keys(filters).length > 0);

  if (collapsed) {
    return (
      <div className={cn('border-l bg-muted/30 w-12 flex flex-col items-center py-4 gap-4', className)}>
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggleCollapse}
          aria-label="Expand context panel"
        >
          <ChevronDown className="h-4 w-4 rotate-90" />
        </Button>
        {repo && <GitBranch className="h-4 w-4 text-muted-foreground" />}
        {pr && <GitPullRequest className="h-4 w-4 text-muted-foreground" />}
        {incident && <AlertTriangle className="h-4 w-4 text-muted-foreground" />}
        {timeframe && <Calendar className="h-4 w-4 text-muted-foreground" />}
      </div>
    );
  }

  return (
    <aside
      className={cn(
        'border-l bg-muted/30 w-80 flex flex-col overflow-hidden',
        className
      )}
      aria-label="Context panel"
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b px-4 py-3">
        <h2 className="text-sm font-semibold">Context</h2>
        <div className="flex items-center gap-1">
          {hasContext && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                onRepoChange?.(null);
                onPRChange?.(null);
                onIncidentChange?.(null);
                onTimeframeChange?.(null);
                onFiltersChange?.({});
              }}
              className="h-7 px-2 text-xs"
            >
              Clear all
            </Button>
          )}
          {onToggleCollapse && (
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={onToggleCollapse}
              aria-label="Collapse panel"
            >
              <ChevronUp className="h-4 w-4 rotate-90" />
            </Button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {!hasContext && (
          <div className="text-center py-8 text-sm text-muted-foreground">
            <Filter className="h-8 w-8 mx-auto mb-3 opacity-50" />
            <p>No context selected</p>
            <p className="text-xs mt-1">
              Use quick actions or mention a repo, PR, or incident in chat
            </p>
          </div>
        )}

        {/* Repository Context */}
        {repo && (
          <ContextSection
            icon={<GitBranch className="h-4 w-4" />}
            title="Repository"
            onRemove={() => onRepoChange?.(null)}
          >
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-medium truncate">{repo.name}</span>
                <a
                  href={repo.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-muted-foreground hover:text-foreground"
                  aria-label="Open repository in new tab"
                >
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>
              <div className="text-xs text-muted-foreground space-y-1">
                <p className="truncate">{repo.full_name}</p>
                <div className="flex items-center gap-3">
                  <span className="flex items-center gap-1">
                    <GitBranch className="h-3 w-3" />
                    {repo.default_branch}
                  </span>
                  {repo.language && (
                    <span className="flex items-center gap-1">
                      <FileCode className="h-3 w-3" />
                      {repo.language}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </ContextSection>
        )}

        {/* Pull Request Context */}
        {pr && (
          <ContextSection
            icon={<GitPullRequest className="h-4 w-4" />}
            title="Pull Request"
            onRemove={() => onPRChange?.(null)}
          >
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-medium truncate flex items-center gap-2">
                  #{pr.number}
                  <PRStateBadge state={pr.state} />
                </span>
                <a
                  href={pr.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-muted-foreground hover:text-foreground"
                  aria-label="Open pull request in new tab"
                >
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>
              <p className="text-sm truncate" title={pr.title}>{pr.title}</p>
              <div className="text-xs text-muted-foreground space-y-1">
                <div className="flex items-center gap-3">
                  <span className="flex items-center gap-1">
                    <Users className="h-3 w-3" />
                    {pr.author}
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {formatDate(pr.created_at)}
                  </span>
                </div>
                {(pr.files_changed !== undefined || pr.additions !== undefined) && (
                  <div className="flex items-center gap-3">
                    {pr.files_changed !== undefined && (
                      <span>{pr.files_changed} files</span>
                    )}
                    {pr.additions !== undefined && (
                      <span className="text-green-600 dark:text-green-400">+{pr.additions}</span>
                    )}
                    {pr.deletions !== undefined && (
                      <span className="text-red-600 dark:text-red-400">-{pr.deletions}</span>
                    )}
                  </div>
                )}
              </div>
            </div>
          </ContextSection>
        )}

        {/* Incident Context */}
        {incident && (
          <ContextSection
            icon={<AlertTriangle className="h-4 w-4" />}
            title="Incident"
            onRemove={() => onIncidentChange?.(null)}
          >
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <SeverityBadge severity={incident.severity} />
                <IncidentStatusBadge status={incident.status} />
              </div>
              <p className="text-sm font-medium truncate" title={incident.title}>
                {incident.title}
              </p>
              <div className="text-xs text-muted-foreground space-y-1">
                <div className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  Started: {formatDate(incident.started_at)}
                </div>
                {incident.resolved_at && (
                  <div className="flex items-center gap-1">
                    <Activity className="h-3 w-3" />
                    Resolved: {formatDate(incident.resolved_at)}
                  </div>
                )}
                {incident.affected_services && incident.affected_services.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1">
                    {incident.affected_services.map(service => (
                      <span
                        key={service}
                        className="px-1.5 py-0.5 rounded bg-muted text-xs"
                      >
                        {service}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </ContextSection>
        )}

        {/* Timeframe Context */}
        {timeframe && (
          <ContextSection
            icon={<Calendar className="h-4 w-4" />}
            title="Timeframe"
            onRemove={() => onTimeframeChange?.(null)}
          >
            <div className="space-y-2">
              {timeframe.preset && timeframe.preset !== 'custom' && (
                <span className="text-sm font-medium">
                  {getPresetLabel(timeframe.preset)}
                </span>
              )}
              <div className="text-xs text-muted-foreground">
                <p>{formatDate(timeframe.start)} - {formatDate(timeframe.end)}</p>
              </div>
            </div>
          </ContextSection>
        )}

        {/* Active Filters */}
        {filters && Object.keys(filters).length > 0 && (
          <ContextSection
            icon={<Filter className="h-4 w-4" />}
            title="Filters"
            onRemove={() => onFiltersChange?.({})}
          >
            <div className="flex flex-wrap gap-1">
              {Object.entries(filters).map(([key, value]) => (
                <span
                  key={key}
                  className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-muted text-xs"
                >
                  <span className="font-medium">{key}:</span>
                  <span>{String(value)}</span>
                  <button
                    onClick={() => {
                      const newFilters = { ...filters };
                      delete newFilters[key];
                      onFiltersChange?.(newFilters);
                    }}
                    className="hover:text-destructive"
                    aria-label={`Remove ${key} filter`}
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
          </ContextSection>
        )}
      </div>
    </aside>
  );
});

// -----------------------------------------------------------------------------
// Helper Components
// -----------------------------------------------------------------------------

interface ContextSectionProps {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
  onRemove?: () => void;
}

function ContextSection({ icon, title, children, onRemove }: ContextSectionProps) {
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="rounded-lg border bg-card p-3">
      <div className="flex items-center justify-between mb-2">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-2 text-sm font-medium hover:text-foreground/80"
        >
          {icon}
          {title}
          {expanded ? (
            <ChevronUp className="h-3 w-3" />
          ) : (
            <ChevronDown className="h-3 w-3" />
          )}
        </button>
        {onRemove && (
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={onRemove}
            aria-label={`Remove ${title.toLowerCase()}`}
          >
            <X className="h-3 w-3" />
          </Button>
        )}
      </div>
      {expanded && <div className="text-sm">{children}</div>}
    </div>
  );
}

function PRStateBadge({ state }: { state: 'open' | 'closed' | 'merged' }) {
  const styles = {
    open: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    closed: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    merged: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  };

  return (
    <span className={cn('px-1.5 py-0.5 rounded text-xs font-medium', styles[state])}>
      {state}
    </span>
  );
}

function SeverityBadge({ severity }: { severity: 'critical' | 'high' | 'medium' | 'low' }) {
  const styles = {
    critical: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    high: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
    medium: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
    low: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  };

  return (
    <span className={cn('px-1.5 py-0.5 rounded text-xs font-medium uppercase', styles[severity])}>
      {severity}
    </span>
  );
}

function IncidentStatusBadge({ status }: { status: 'investigating' | 'identified' | 'monitoring' | 'resolved' }) {
  const styles = {
    investigating: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    identified: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
    monitoring: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
    resolved: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  };

  return (
    <span className={cn('px-1.5 py-0.5 rounded text-xs font-medium', styles[status])}>
      {status}
    </span>
  );
}

// -----------------------------------------------------------------------------
// Utility Functions
// -----------------------------------------------------------------------------

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) {
    return date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
  } else if (diffDays === 1) {
    return 'Yesterday';
  } else if (diffDays < 7) {
    return `${diffDays} days ago`;
  } else {
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  }
}

function getPresetLabel(preset: string): string {
  const labels: Record<string, string> = {
    last_hour: 'Last hour',
    last_24h: 'Last 24 hours',
    last_7d: 'Last 7 days',
    last_30d: 'Last 30 days',
    custom: 'Custom range',
  };
  return labels[preset] || preset;
}

export default ContextPanel;
