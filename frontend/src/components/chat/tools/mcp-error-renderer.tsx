'use client';

import { useState } from 'react';
import {
  AlertTriangle,
  WifiOff,
  KeyRound,
  Clock,
  Ban,
  Search,
  Server,
  Wrench,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Copy,
  Check,
  RefreshCw,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { MCPErrorPayload, MCPErrorCategory, MCPErrorSuggestion } from './types';

interface MCPErrorRendererProps {
  error: MCPErrorPayload;
  onRetry?: () => void;
}

const categoryConfig: Record<
  MCPErrorCategory,
  {
    icon: React.ElementType;
    label: string;
    color: string;
    bgColor: string;
    borderColor: string;
  }
> = {
  connection: {
    icon: WifiOff,
    label: 'Connection Error',
    color: 'text-orange-600 dark:text-orange-400',
    bgColor: 'bg-orange-50 dark:bg-orange-950/30',
    borderColor: 'border-orange-200 dark:border-orange-800',
  },
  authentication: {
    icon: KeyRound,
    label: 'Authentication Error',
    color: 'text-red-600 dark:text-red-400',
    bgColor: 'bg-red-50 dark:bg-red-950/30',
    borderColor: 'border-red-200 dark:border-red-800',
  },
  validation: {
    icon: AlertTriangle,
    label: 'Validation Error',
    color: 'text-amber-600 dark:text-amber-400',
    bgColor: 'bg-amber-50 dark:bg-amber-950/30',
    borderColor: 'border-amber-200 dark:border-amber-800',
  },
  timeout: {
    icon: Clock,
    label: 'Timeout Error',
    color: 'text-blue-600 dark:text-blue-400',
    bgColor: 'bg-blue-50 dark:bg-blue-950/30',
    borderColor: 'border-blue-200 dark:border-blue-800',
  },
  rate_limit: {
    icon: Ban,
    label: 'Rate Limit Exceeded',
    color: 'text-purple-600 dark:text-purple-400',
    bgColor: 'bg-purple-50 dark:bg-purple-950/30',
    borderColor: 'border-purple-200 dark:border-purple-800',
  },
  not_found: {
    icon: Search,
    label: 'Not Found',
    color: 'text-gray-600 dark:text-gray-400',
    bgColor: 'bg-gray-50 dark:bg-gray-950/30',
    borderColor: 'border-gray-200 dark:border-gray-700',
  },
  server: {
    icon: Server,
    label: 'Server Error',
    color: 'text-rose-600 dark:text-rose-400',
    bgColor: 'bg-rose-50 dark:bg-rose-950/30',
    borderColor: 'border-rose-200 dark:border-rose-800',
  },
  tool_execution: {
    icon: Wrench,
    label: 'Tool Execution Error',
    color: 'text-yellow-600 dark:text-yellow-400',
    bgColor: 'bg-yellow-50 dark:bg-yellow-950/30',
    borderColor: 'border-yellow-200 dark:border-yellow-800',
  },
  unknown: {
    icon: HelpCircle,
    label: 'Unknown Error',
    color: 'text-slate-600 dark:text-slate-400',
    bgColor: 'bg-slate-50 dark:bg-slate-950/30',
    borderColor: 'border-slate-200 dark:border-slate-700',
  },
};

function SuggestionCard({ suggestion }: { suggestion: MCPErrorSuggestion }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (suggestion.command) {
      await navigator.clipboard.writeText(suggestion.command);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="rounded-lg border border-border bg-background/50 p-3">
      <p className="text-sm font-medium text-foreground">{suggestion.action}</p>
      <p className="mt-1 text-xs text-muted-foreground">{suggestion.description}</p>
      {suggestion.command && (
        <div className="mt-2 flex items-center gap-2">
          <code className="flex-1 rounded bg-muted px-2 py-1 text-xs font-mono text-foreground">
            {suggestion.command}
          </code>
          <button
            onClick={handleCopy}
            className="rounded p-1 hover:bg-muted transition-colors"
            title="Copy command"
          >
            {copied ? (
              <Check className="h-3.5 w-3.5 text-emerald-500" />
            ) : (
              <Copy className="h-3.5 w-3.5 text-muted-foreground" />
            )}
          </button>
        </div>
      )}
    </div>
  );
}

export function MCPErrorRenderer({ error, onRetry }: MCPErrorRendererProps) {
  const [showDetails, setShowDetails] = useState(false);
  const config = categoryConfig[error.category] || categoryConfig.unknown;
  const IconComponent = config.icon;

  return (
    <section
      className={cn(
        'rounded-xl border p-4 shadow-sm',
        config.bgColor,
        config.borderColor
      )}
      role="alert"
      aria-live="polite"
    >
      {/* Header */}
      <header className="flex items-start gap-3">
        <div className={cn('mt-0.5 rounded-full p-1.5', config.bgColor)}>
          <IconComponent className={cn('h-4 w-4', config.color)} aria-hidden="true" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <h4 className={cn('text-sm font-semibold', config.color)}>
              {config.label}
              {error.code && (
                <span className="ml-2 text-xs font-normal opacity-75">
                  ({error.code})
                </span>
              )}
            </h4>
            {error.retryable && onRetry && (
              <button
                onClick={onRetry}
                className={cn(
                  'flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors',
                  'bg-background hover:bg-muted border border-border'
                )}
              >
                <RefreshCw className="h-3 w-3" />
                Retry
              </button>
            )}
          </div>
          {error.toolName && (
            <p className="mt-0.5 text-xs text-muted-foreground">
              Tool: <span className="font-mono">{error.toolName}</span>
            </p>
          )}
        </div>
      </header>

      {/* Message */}
      <div className="mt-3 rounded-lg bg-background/60 p-3">
        <p className="text-sm text-foreground">{error.message}</p>
      </div>

      {/* Suggestions */}
      {error.suggestions && error.suggestions.length > 0 && (
        <div className="mt-4">
          <h5 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Suggested Actions
          </h5>
          <div className="space-y-2">
            {error.suggestions.map((suggestion, index) => (
              <SuggestionCard key={index} suggestion={suggestion} />
            ))}
          </div>
        </div>
      )}

      {/* Details Toggle */}
      {error.details && Object.keys(error.details).length > 0 && (
        <div className="mt-4">
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            {showDetails ? (
              <ChevronUp className="h-3.5 w-3.5" />
            ) : (
              <ChevronDown className="h-3.5 w-3.5" />
            )}
            {showDetails ? 'Hide Details' : 'Show Details'}
          </button>
          {showDetails && (
            <pre className="mt-2 max-h-40 overflow-auto rounded-lg bg-muted/60 p-3 text-xs font-mono text-foreground">
              {JSON.stringify(error.details, null, 2)}
            </pre>
          )}
        </div>
      )}

      {/* Documentation Link */}
      {error.documentationUrl && (
        <a
          href={error.documentationUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-4 inline-flex items-center gap-1.5 text-xs font-medium text-primary hover:underline"
        >
          <ExternalLink className="h-3 w-3" />
          View Documentation
        </a>
      )}
    </section>
  );
}
