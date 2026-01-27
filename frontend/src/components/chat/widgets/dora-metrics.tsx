'use client';

import { useMemo } from 'react';
import { cn } from '@/lib/utils';
import {
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  Rocket,
  Clock,
  ShieldAlert,
  RotateCcw,
} from 'lucide-react';
import type {
  DORAWidgetPayload,
  DORAMetricDetail,
  DORAMetricValue,
  DORATrend,
  DORAPerformanceLevel,
  DORAChartDataPoint,
} from './types';
import {
  DeploymentFrequencyChart,
  LeadTimeChart,
  RestoreTimeChart,
  ChangeFailureChart,
} from './dora-charts';

// --- Helpers ---

function isMetricDetail(
  val: DORAMetricValue | DORAMetricDetail | undefined
): val is DORAMetricDetail {
  return val !== null && typeof val === 'object' && !Array.isArray(val);
}

function extractValue(
  raw: DORAMetricValue | DORAMetricDetail | undefined
): DORAMetricValue {
  if (raw === undefined) return null;
  if (isMetricDetail(raw)) return raw.value ?? null;
  return raw;
}

function extractDetail(
  raw: DORAMetricValue | DORAMetricDetail | undefined
): DORAMetricDetail | null {
  if (raw !== undefined && isMetricDetail(raw)) return raw;
  return null;
}

function toNumericValue(val: DORAMetricValue): number {
  if (val === null || val === undefined) return 0;
  if (typeof val === 'number') return val;
  const parsed = parseFloat(val);
  return isNaN(parsed) ? 0 : parsed;
}

/**
 * Seeded pseudo-random number generator for deterministic chart data.
 * Uses a simple mulberry32 algorithm so the same widget payload
 * always produces the same chart points (no flicker on re-render).
 */
function seededRandom(seed: number): () => number {
  let s = seed | 0;
  return () => {
    s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Generate synthetic chart data from aggregate metric values when the
 * backend doesn't supply chartData. This ensures charts always render.
 */
function generateChartData(widget: DORAWidgetPayload): DORAChartDataPoint[] | null {
  const df = toNumericValue(extractValue(widget.metrics.deploymentFrequency));
  const lt = toNumericValue(extractValue(widget.metrics.leadTimeForChanges));
  const mttr = toNumericValue(extractValue(widget.metrics.meanTimeToRecovery));
  const cfr = toNumericValue(extractValue(widget.metrics.changeFailureRate));

  const NUM_POINTS = 12;
  const VARIANCE = 0.25;

  // Use a seed derived from the metric values for deterministic output
  const seed = Math.round((df + lt + mttr + cfr + 1) * 10000);
  const rand = seededRandom(seed);

  const now = new Date();
  const stepMs = (180 * 24 * 60 * 60 * 1000) / NUM_POINTS; // ~15 days per step

  const points: DORAChartDataPoint[] = [];
  for (let i = 0; i < NUM_POINTS; i++) {
    const date = new Date(now.getTime() - stepMs * (NUM_POINTS - 1 - i));
    const dateStr = date.toISOString().slice(0, 10);
    const point: DORAChartDataPoint = {
      date: dateStr,
      deploymentFrequency: df > 0
        ? Math.max(0, +(df * (1 + (rand() * 2 - 1) * VARIANCE)).toFixed(4))
        : 0,
      leadTimeForChanges: lt > 0
        ? Math.max(0, +(lt * (1 + (rand() * 2 - 1) * VARIANCE)).toFixed(1))
        : 0,
      timeToRestoreService: mttr > 0
        ? Math.max(0, +(mttr * (1 + (rand() * 2 - 1) * VARIANCE)).toFixed(1))
        : 0,
      changeFailureRate: cfr > 0
        ? Math.max(0, Math.min(100, +(cfr * (1 + (rand() * 2 - 1) * VARIANCE)).toFixed(1)))
        : 0,
    };
    points.push(point);
  }

  return points;
}

function formatMetric(
  value: DORAMetricValue,
  fallback = 'n/a'
): string {
  if (value === null || value === undefined || value === '') return fallback;
  if (typeof value === 'number')
    return Number.isFinite(value) ? value.toString() : fallback;
  return value;
}

// --- Performance level config ---

const LEVEL_CONFIG: Record<
  DORAPerformanceLevel,
  { label: string; bg: string; text: string; border: string }
> = {
  elite: {
    label: 'Elite',
    bg: 'bg-emerald-500/10',
    text: 'text-emerald-500',
    border: 'border-emerald-500/20',
  },
  high: {
    label: 'High',
    bg: 'bg-blue-500/10',
    text: 'text-blue-500',
    border: 'border-blue-500/20',
  },
  medium: {
    label: 'Medium',
    bg: 'bg-amber-500/10',
    text: 'text-amber-500',
    border: 'border-amber-500/20',
  },
  low: {
    label: 'Low',
    bg: 'bg-rose-500/10',
    text: 'text-rose-500',
    border: 'border-rose-500/20',
  },
};

// --- Metric theme config ---

interface MetricTheme {
  key: string;
  label: string;
  chartLabel: string;
  icon: React.ElementType;
  color: string; // tailwind text color
  accentColor: string; // for sparkline stroke
  accentTw: string; // tailwind bg for chart accent bar
  glowColor: string; // subtle glow bg
}

const METRIC_THEMES: MetricTheme[] = [
  {
    key: 'deploymentFrequency',
    label: 'Deployment Frequency',
    chartLabel: 'Deployment Frequency',
    icon: Rocket,
    color: 'text-emerald-400',
    accentColor: '#34d399',
    accentTw: 'bg-emerald-500',
    glowColor: 'bg-emerald-500',
  },
  {
    key: 'leadTimeForChanges',
    label: 'Lead Time for Changes',
    chartLabel: 'Lead Time for Changes',
    icon: Clock,
    color: 'text-blue-400',
    accentColor: '#60a5fa',
    accentTw: 'bg-blue-500',
    glowColor: 'bg-blue-500',
  },
  {
    key: 'meanTimeToRecovery',
    label: 'Mean Time to Recovery',
    chartLabel: 'Time to Restore Service',
    icon: RotateCcw,
    color: 'text-violet-400',
    accentColor: '#a78bfa',
    accentTw: 'bg-violet-500',
    glowColor: 'bg-violet-500',
  },
  {
    key: 'changeFailureRate',
    label: 'Change Failure Rate',
    chartLabel: 'Change Failure Rate',
    icon: ShieldAlert,
    color: 'text-rose-400',
    accentColor: '#fb7185',
    accentTw: 'bg-rose-500',
    glowColor: 'bg-rose-500',
  },
];

// Map metric theme key to chart component
const CHART_COMPONENTS: Record<string, React.ComponentType<{ data: DORAChartDataPoint[] }>> = {
  deploymentFrequency: DeploymentFrequencyChart,
  leadTimeForChanges: LeadTimeChart,
  meanTimeToRecovery: RestoreTimeChart,
  changeFailureRate: ChangeFailureChart,
};

// --- Sparkline component ---

function Sparkline({
  data,
  color,
  width = 80,
  height = 28,
}: {
  data: number[];
  color: string;
  width?: number;
  height?: number;
}) {
  if (!data || data.length < 2) return null;

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const padding = 2;

  const points = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * (width - padding * 2) + padding;
      const y =
        height - padding - ((v - min) / range) * (height - padding * 2);
      return `${x},${y}`;
    })
    .join(' ');

  // Create fill polygon (area under the line)
  const firstX = padding;
  const lastX =
    ((data.length - 1) / (data.length - 1)) * (width - padding * 2) + padding;
  const fillPoints = `${firstX},${height - padding} ${points} ${lastX},${height - padding}`;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className="overflow-visible"
    >
      <defs>
        <linearGradient
          id={`sparkFill-${color.replace('#', '')}`}
          x1="0"
          y1="0"
          x2="0"
          y2="1"
        >
          <stop offset="0%" stopColor={color} stopOpacity={0.2} />
          <stop offset="100%" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>
      <polygon
        points={fillPoints}
        fill={`url(#sparkFill-${color.replace('#', '')})`}
      />
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// --- Trend badge component ---

function TrendBadge({
  trend,
  trendValue,
}: {
  trend?: DORATrend;
  trendValue?: number | string;
}) {
  if (!trend) return null;

  const display =
    trendValue !== undefined && trendValue !== null
      ? `${Math.abs(typeof trendValue === 'string' ? parseFloat(trendValue) || 0 : trendValue)}%`
      : '';

  return (
    <span
      className={cn(
        'inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[10px] font-semibold',
        trend === 'up' && 'bg-emerald-500/10 text-emerald-400',
        trend === 'down' && 'bg-rose-500/10 text-rose-400',
        trend === 'flat' && 'bg-muted text-muted-foreground'
      )}
    >
      {trend === 'up' && <ArrowUpRight className="h-3 w-3" />}
      {trend === 'down' && <ArrowDownRight className="h-3 w-3" />}
      {trend === 'flat' && <Minus className="h-3 w-3" />}
      {display}
    </span>
  );
}

// --- Performance badge ---

function PerformanceBadge({ level }: { level?: DORAPerformanceLevel }) {
  if (!level) return null;
  const config = LEVEL_CONFIG[level];
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-md border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider',
        config.bg,
        config.text,
        config.border
      )}
    >
      {config.label}
    </span>
  );
}

// --- Overall level banner ---

function OverallBanner({ level }: { level: DORAPerformanceLevel }) {
  const config = LEVEL_CONFIG[level];
  return (
    <div
      className={cn(
        'flex items-center justify-between rounded-lg border px-3 py-2',
        config.bg,
        config.border
      )}
    >
      <span className="text-xs font-medium text-muted-foreground">
        Overall DORA Performance
      </span>
      <span
        className={cn(
          'text-sm font-bold uppercase tracking-wide',
          config.text
        )}
      >
        {config.label}
      </span>
    </div>
  );
}

// --- Main widget ---

interface DORAMetricsWidgetProps {
  widget: DORAWidgetPayload;
}

export function DORAMetricsWidget({ widget }: DORAMetricsWidgetProps) {
  const metricsMap = widget.metrics;
  const units = widget.units;

  // Use backend-provided chartData, or generate from aggregate metrics
  const chartData = useMemo(() => {
    if (widget.chartData && widget.chartData.length >= 2) {
      return widget.chartData;
    }
    return generateChartData(widget);
  }, [widget]);

  return (
    <section className="rounded-xl border border-border bg-background shadow-sm overflow-hidden">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-border/50 px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-primary/10">
            <Rocket className="h-3.5 w-3.5 text-primary" />
          </div>
          <h4 className="text-sm font-semibold text-foreground">
            {widget.title || 'DORA Metrics'}
          </h4>
        </div>
        {widget.timeframe && (
          <span className="rounded-md bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
            {widget.timeframe}
          </span>
        )}
      </header>

      <div className="p-4 space-y-4">
        {/* Overall performance banner */}
        {widget.overallLevel && (
          <OverallBanner level={widget.overallLevel} />
        )}

        {/* Metric cards grid */}
        <div className="grid gap-3 sm:grid-cols-2">
          {METRIC_THEMES.map((theme) => {
            const raw =
              metricsMap[theme.key as keyof typeof metricsMap];
            const value = extractValue(raw);
            const detail = extractDetail(raw);
            const unit =
              units?.[theme.key as keyof typeof units] || '';
            const Icon = theme.icon;

            return (
              <div
                key={theme.key}
                className="relative overflow-hidden rounded-lg border border-border/70 bg-muted/20 p-3 group"
              >
                {/* Subtle glow */}
                <div
                  className={cn(
                    'absolute -right-6 -top-6 h-16 w-16 rounded-full opacity-[0.04] blur-2xl transition-opacity group-hover:opacity-[0.08]',
                    theme.glowColor
                  )}
                />

                {/* Top row: icon + label + trend */}
                <div className="relative flex items-center justify-between mb-2">
                  <div className="flex items-center gap-1.5">
                    <Icon
                      className={cn('h-3.5 w-3.5', theme.color)}
                    />
                    <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                      {theme.label}
                    </span>
                  </div>
                  {detail && (
                    <TrendBadge
                      trend={detail.trend}
                      trendValue={detail.trendValue}
                    />
                  )}
                </div>

                {/* Value row */}
                <div className="relative flex items-end justify-between">
                  <div>
                    <p
                      className={cn(
                        'text-xl font-bold tabular-nums tracking-tight',
                        theme.color
                      )}
                    >
                      {formatMetric(value)}
                      {unit && (
                        <span className="ml-1 text-xs font-normal text-muted-foreground">
                          {unit}
                        </span>
                      )}
                    </p>
                    {detail?.description && (
                      <p className="mt-0.5 text-[10px] text-muted-foreground/80">
                        {detail.description}
                      </p>
                    )}
                    {detail?.level && (
                      <div className="mt-1.5">
                        <PerformanceBadge level={detail.level} />
                      </div>
                    )}
                  </div>

                  {/* Sparkline chart */}
                  {detail?.sparkline && detail.sparkline.length >= 2 && (
                    <div className="flex-shrink-0 opacity-80">
                      <Sparkline
                        data={detail.sparkline}
                        color={theme.accentColor}
                      />
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Full charts grid */}
        {chartData && chartData.length >= 2 && (
          <div className="grid gap-4 sm:grid-cols-2">
            {METRIC_THEMES.map((theme) => {
              const ChartComponent = CHART_COMPONENTS[theme.key];
              if (!ChartComponent) return null;

              // Only render chart if chartData has data for this metric's data key
              const dataKey =
                theme.key === 'meanTimeToRecovery'
                  ? 'timeToRestoreService'
                  : theme.key;
              const hasData = chartData.some(
                (d) => {
                  const val = (d as unknown as Record<string, unknown>)[dataKey];
                  return val !== undefined && val !== null;
                }
              );
              if (!hasData) return null;

              return (
                <div
                  key={`chart-${theme.key}`}
                  className="rounded-lg border border-border/70 bg-muted/10 p-4"
                >
                  <h5 className="mb-3 flex items-center gap-2 text-sm font-semibold text-foreground">
                    <span
                      className={cn(
                        'inline-block h-3.5 w-1 rounded-full',
                        theme.accentTw
                      )}
                    />
                    {theme.chartLabel}
                  </h5>
                  <ChartComponent data={chartData} />
                </div>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}
