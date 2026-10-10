'use client';

import {
  DollarSign,
  Hash,
  Clock,
  CheckCircle2,
  TrendingUp,
  TrendingDown,
  Minus,
} from 'lucide-react';
import type { CostSummary as CostSummaryType } from './types';
import { cn } from '@/lib/utils';

function formatCurrency(value: number): string {
  if (value >= 1000) return `$${(value / 1000).toFixed(2)}K`;
  if (value >= 1) return `$${value.toFixed(2)}`;
  return `$${value.toFixed(4)}`;
}

function formatNumber(value: number): string {
  if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
  if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
  return value.toString();
}

function formatLatency(ms: number | null): string {
  if (ms === null) return 'N/A';
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.round(ms)}ms`;
}

interface StatCardProps {
  label: string;
  value: string | number;
  subValue?: string;
  icon: React.ReactNode;
  trend?: number;
  color?: 'default' | 'green' | 'blue' | 'amber' | 'red';
}

function StatCard({ label, value, subValue, icon, trend, color = 'default' }: StatCardProps) {
  const colorClasses = {
    default: 'text-primary',
    green: 'text-green-500',
    blue: 'text-blue-500',
    amber: 'text-amber-500',
    red: 'text-red-500',
  };

  const getTrendIcon = () => {
    if (trend === undefined || trend === 0) return null;
    if (trend > 0) return <TrendingUp className="h-3 w-3 text-green-500" />;
    return <TrendingDown className="h-3 w-3 text-red-500" />;
  };

  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="flex items-center justify-between mb-2">
        <div className={cn('p-2 rounded-lg bg-muted', colorClasses[color])}>
          {icon}
        </div>
        {trend !== undefined && trend !== 0 && (
          <div className="flex items-center gap-1">
            {getTrendIcon()}
            <span
              className={cn(
                'text-xs font-medium',
                trend > 0 ? 'text-green-500' : 'text-red-500'
              )}
            >
              {trend > 0 ? '+' : ''}
              {trend.toFixed(1)}%
            </span>
          </div>
        )}
      </div>
      <div className="text-2xl font-bold">{value}</div>
      <div className="flex items-center justify-between mt-1">
        <span className="text-sm text-muted-foreground">{label}</span>
        {subValue && (
          <span className="text-xs text-muted-foreground">{subValue}</span>
        )}
      </div>
    </div>
  );
}

interface CostSummaryProps {
  data: CostSummaryType;
  previousPeriod?: CostSummaryType;
}

export function CostSummaryCards({ data, previousPeriod }: CostSummaryProps) {
  // Calculate trends if previous period provided
  const costTrend = previousPeriod
    ? ((data.total_cost - previousPeriod.total_cost) / previousPeriod.total_cost) * 100
    : undefined;

  const tokenTrend = previousPeriod
    ? ((data.total_tokens - previousPeriod.total_tokens) / previousPeriod.total_tokens) * 100
    : undefined;

  const requestTrend = previousPeriod
    ? ((data.request_count - previousPeriod.request_count) / previousPeriod.request_count) * 100
    : undefined;

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <StatCard
        label="Total Cost"
        value={formatCurrency(data.total_cost)}
        subValue={`${formatNumber(data.total_tokens)} tokens`}
        icon={<DollarSign className="h-4 w-4" />}
        trend={costTrend}
        color="green"
      />
      <StatCard
        label="Requests"
        value={formatNumber(data.request_count)}
        subValue={`${(data.success_rate * 100).toFixed(1)}% success`}
        icon={<Hash className="h-4 w-4" />}
        trend={requestTrend}
        color="blue"
      />
      <StatCard
        label="Avg Latency"
        value={formatLatency(data.avg_latency_ms)}
        icon={<Clock className="h-4 w-4" />}
        color="amber"
      />
      <StatCard
        label="Success Rate"
        value={`${(data.success_rate * 100).toFixed(1)}%`}
        subValue={`${data.request_count - Math.round(data.request_count * data.success_rate)} failed`}
        icon={<CheckCircle2 className="h-4 w-4" />}
        color={data.success_rate >= 0.95 ? 'green' : data.success_rate >= 0.9 ? 'amber' : 'red'}
      />
    </div>
  );
}

// Token breakdown component
export function TokenBreakdown({ data }: { data: CostSummaryType }) {
  const promptPercentage = data.total_tokens > 0
    ? (data.prompt_tokens / data.total_tokens) * 100
    : 0;
  const completionPercentage = data.total_tokens > 0
    ? (data.completion_tokens / data.total_tokens) * 100
    : 0;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">Token Distribution</span>
        <span className="text-sm text-muted-foreground">
          {formatNumber(data.total_tokens)} total
        </span>
      </div>

      {/* Stacked bar */}
      <div className="h-4 rounded-full bg-muted overflow-hidden flex">
        <div
          className="bg-blue-500 transition-all"
          style={{ width: `${promptPercentage}%` }}
          title={`Prompt: ${formatNumber(data.prompt_tokens)}`}
        />
        <div
          className="bg-green-500 transition-all"
          style={{ width: `${completionPercentage}%` }}
          title={`Completion: ${formatNumber(data.completion_tokens)}`}
        />
      </div>

      {/* Legend */}
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-2">
          <div className="h-3 w-3 rounded bg-blue-500" />
          <span className="text-muted-foreground">
            Prompt: {formatNumber(data.prompt_tokens)} ({promptPercentage.toFixed(1)}%)
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-3 w-3 rounded bg-green-500" />
          <span className="text-muted-foreground">
            Completion: {formatNumber(data.completion_tokens)} ({completionPercentage.toFixed(1)}%)
          </span>
        </div>
      </div>
    </div>
  );
}
