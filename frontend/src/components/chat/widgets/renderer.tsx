'use client';

import { cn } from '@/lib/utils';
import type { WidgetPayload } from './types';
import { PipelineProgressWidget } from './pipeline-progress';

interface WidgetRendererProps {
  widget: WidgetPayload;
}

function formatMetric(value: number | string | null | undefined, fallback = 'n/a'): string {
  if (value === null || value === undefined || value === '') return fallback;
  if (typeof value === 'number') return Number.isFinite(value) ? value.toString() : fallback;
  return value;
}

export function WidgetRenderer({ widget }: WidgetRendererProps) {
  // Debug logging for widget rendering
  console.log('[WidgetRenderer] Rendering widget:', widget.type, widget);

  switch (widget.type) {
    case 'dora':
      return (
        <section className="rounded-xl border border-border bg-background p-4 shadow-sm">
          <header className="mb-3 flex items-center justify-between">
            <h4 className="text-sm font-semibold text-foreground">
              {widget.title || 'DORA Metrics'}
            </h4>
            {widget.timeframe && (
              <span className="text-xs text-muted-foreground">{widget.timeframe}</span>
            )}
          </header>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-lg border border-border/70 bg-muted/30 p-3">
              <p className="text-xs text-muted-foreground">Deployment Frequency</p>
              <p className="text-lg font-semibold">
                {formatMetric(widget.metrics.deploymentFrequency)}
                {widget.units?.deploymentFrequency ? ` ${widget.units.deploymentFrequency}` : ''}
              </p>
            </div>
            <div className="rounded-lg border border-border/70 bg-muted/30 p-3">
              <p className="text-xs text-muted-foreground">Lead Time for Changes</p>
              <p className="text-lg font-semibold">
                {formatMetric(widget.metrics.leadTimeForChanges)}
                {widget.units?.leadTimeForChanges ? ` ${widget.units.leadTimeForChanges}` : ''}
              </p>
            </div>
            <div className="rounded-lg border border-border/70 bg-muted/30 p-3">
              <p className="text-xs text-muted-foreground">Mean Time to Recovery</p>
              <p className="text-lg font-semibold">
                {formatMetric(widget.metrics.meanTimeToRecovery)}
                {widget.units?.meanTimeToRecovery ? ` ${widget.units.meanTimeToRecovery}` : ''}
              </p>
            </div>
            <div className="rounded-lg border border-border/70 bg-muted/30 p-3">
              <p className="text-xs text-muted-foreground">Change Failure Rate</p>
              <p className="text-lg font-semibold">
                {formatMetric(widget.metrics.changeFailureRate)}
                {widget.units?.changeFailureRate ? ` ${widget.units.changeFailureRate}` : ''}
              </p>
            </div>
          </div>
        </section>
      );
    case 'space': {
      const dimensions = [
        { key: 'satisfaction', label: 'Satisfaction', value: widget.dimensions.satisfaction },
        { key: 'performance', label: 'Performance', value: widget.dimensions.performance },
        { key: 'activity', label: 'Activity', value: widget.dimensions.activity },
        { key: 'communication', label: 'Communication', value: widget.dimensions.communication },
        { key: 'efficiency', label: 'Efficiency', value: widget.dimensions.efficiency },
      ];

      return (
        <section className="rounded-xl border border-border bg-background p-4 shadow-sm">
          <header className="mb-3 flex items-center justify-between">
            <h4 className="text-sm font-semibold text-foreground">
              {widget.title || 'SPACE Framework'}
            </h4>
            {widget.scale && (
              <span className="text-xs text-muted-foreground">Scale: {widget.scale}</span>
            )}
          </header>
          <div className="space-y-3">
            {dimensions.map((dimension) => {
              const value = dimension.value ?? null;
              const percentage = value === null ? 0 : Math.max(0, Math.min(100, value));
              return (
                <div key={dimension.key} className="space-y-1">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>{dimension.label}</span>
                    <span>{value === null ? 'n/a' : value}</span>
                  </div>
                  <div className="h-2 rounded-full bg-muted">
                    <div
                      className={cn('h-2 rounded-full bg-primary transition-all')}
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
          {widget.notes && widget.notes.length > 0 && (
            <ul className="mt-3 list-disc space-y-1 pl-4 text-xs text-muted-foreground">
              {widget.notes.map((note, index) => (
                <li key={index}>{note}</li>
              ))}
            </ul>
          )}
        </section>
      );
    }
    case 'insights':
      return (
        <section className="rounded-xl border border-border bg-background p-4 shadow-sm">
          <header className="mb-3">
            <h4 className="text-sm font-semibold text-foreground">
              {widget.title || 'Engineering Insights'}
            </h4>
            {widget.summary && (
              <p className="mt-1 text-xs text-muted-foreground">{widget.summary}</p>
            )}
          </header>
          <div className="space-y-2">
            {widget.items.map((item, index) => (
              <div
                key={`${item.label}-${index}`}
                className="flex items-center justify-between rounded-lg border border-border/70 bg-muted/30 px-3 py-2 text-sm"
              >
                <span className="text-foreground">{item.label}</span>
                <span className="flex items-center gap-2 text-muted-foreground">
                  {item.value}
                  {item.trend && (
                    <span
                      className={cn(
                        'text-xs font-medium',
                        item.trend === 'up' && 'text-emerald-600',
                        item.trend === 'down' && 'text-rose-600',
                        item.trend === 'flat' && 'text-muted-foreground'
                      )}
                    >
                      {item.trend === 'up' ? '▲' : item.trend === 'down' ? '▼' : '■'}
                    </span>
                  )}
                </span>
              </div>
            ))}
          </div>
        </section>
      );
    case 'pipeline_progress':
      return <PipelineProgressWidget widget={widget} />;
    default: {
      // Log unknown widget types for debugging
      const unknownWidget = widget as { type: string };
      const widgetType = unknownWidget?.type;
      console.warn('[WidgetRenderer] Unknown widget type:', widgetType, 'Full widget:', JSON.stringify(widget));
      return (
        <section className="rounded-xl border border-dashed border-border bg-background p-4 text-xs text-muted-foreground">
          Unsupported widget type: {widgetType ? `"${widgetType}"` : '(undefined)'}
        </section>
      );
    }
  }
}
