'use client';

import { useMemo } from 'react';
import { cn } from '@/lib/utils';
import type { ToolPayload, ToolCallPayload } from './types';
import { MCPErrorRenderer } from './mcp-error-renderer';
import { parseWidgetBlocks, WidgetRenderer } from '../widgets';

interface ToolRendererProps {
  tool: ToolPayload;
  onRetry?: () => void;
}

function statusLabel(status: ToolCallPayload['status']): string {
  switch (status) {
    case 'queued':
      return 'Queued';
    case 'running':
      return 'Running';
    case 'completed':
      return 'Completed';
    case 'failed':
      return 'Failed';
    default:
      return 'Unknown';
  }
}

export function ToolRenderer({ tool, onRetry }: ToolRendererProps) {
  // Parse widgets from tool output if present (must be called before any early returns for hooks rules)
  const { content: cleanedOutput, widgets } = useMemo(() => {
    if (tool.type === 'tool_result' && tool.output) {
      return parseWidgetBlocks(tool.output);
    }
    return { content: tool.type === 'tool_result' ? tool.output : '', widgets: [] };
  }, [tool]);

  // Handle MCP errors with the dedicated renderer
  if (tool.type === 'mcp_error') {
    return <MCPErrorRenderer error={tool} onRetry={onRetry} />;
  }

  if (tool.type === 'tool_call') {
    return (
      <section className="rounded-xl border border-border bg-background p-4 shadow-sm">
        <header className="mb-2 flex items-center justify-between">
          <h4 className="text-sm font-semibold text-foreground">
            Tool Call: {tool.name}
          </h4>
          <span
            className={cn(
              'rounded-full px-2 py-0.5 text-xs font-medium',
              tool.status === 'failed' && 'bg-rose-500/10 text-rose-600',
              tool.status === 'completed' && 'bg-emerald-500/10 text-emerald-600',
              tool.status === 'running' && 'bg-amber-500/10 text-amber-600',
              (!tool.status || tool.status === 'queued') && 'bg-muted text-muted-foreground'
            )}
          >
            {statusLabel(tool.status)}
          </span>
        </header>
        {tool.args && (
          <pre className="max-h-48 overflow-auto rounded-lg bg-muted/40 p-3 text-xs text-foreground">
            {JSON.stringify(tool.args, null, 2)}
          </pre>
        )}
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-border bg-background p-4 shadow-sm">
      <header className="mb-2 flex items-center justify-between">
        <h4 className="text-sm font-semibold text-foreground">
          Tool Result{tool.name ? `: ${tool.name}` : ''}
        </h4>
        {tool.success !== undefined && (
          <span
            className={cn(
              'rounded-full px-2 py-0.5 text-xs font-medium',
              tool.success ? 'bg-emerald-500/10 text-emerald-600' : 'bg-rose-500/10 text-rose-600'
            )}
          >
            {tool.success ? 'Success' : 'Failed'}
          </span>
        )}
      </header>
      {/* Render any widgets found in the tool output */}
      {widgets.length > 0 && (
        <div className="mb-3 space-y-3">
          {widgets.map((widget, index) => (
            <WidgetRenderer key={`tool-widget-${index}`} widget={widget} />
          ))}
        </div>
      )}
      {/* Show remaining text output if any */}
      {cleanedOutput && cleanedOutput.trim() ? (
        <pre className="max-h-48 overflow-auto rounded-lg bg-muted/40 p-3 text-xs text-foreground">
          {cleanedOutput}
        </pre>
      ) : !widgets.length ? (
        <p className="text-xs text-muted-foreground">No output provided.</p>
      ) : null}
    </section>
  );
}
