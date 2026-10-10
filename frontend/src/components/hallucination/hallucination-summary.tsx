'use client';

import {
  AlertTriangle,
  CheckCircle2,
  BarChart3,
  Shield,
  Target,
  Zap,
} from 'lucide-react';
import type { HallucinationAnalytics } from './types';
import { cn } from '@/lib/utils';

function formatPercentage(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

interface StatCardProps {
  label: string;
  value: string | number;
  subValue?: string;
  icon: React.ReactNode;
  color?: 'default' | 'green' | 'red' | 'amber' | 'blue';
}

function StatCard({ label, value, subValue, icon, color = 'default' }: StatCardProps) {
  const colorClasses = {
    default: 'text-primary',
    green: 'text-green-500',
    red: 'text-red-500',
    amber: 'text-amber-500',
    blue: 'text-blue-500',
  };

  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="flex items-center justify-between mb-2">
        <div className={cn('p-2 rounded-lg bg-muted', colorClasses[color])}>
          {icon}
        </div>
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

interface HallucinationSummaryCardsProps {
  data: HallucinationAnalytics;
}

export function HallucinationSummaryCards({ data }: HallucinationSummaryCardsProps) {
  const cleanRate = 1 - data.hallucination_rate;

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <StatCard
        label="Total Checks"
        value={data.total_checks.toLocaleString()}
        subValue={`${data.period_days} day period`}
        icon={<BarChart3 className="h-4 w-4" />}
        color="blue"
      />
      <StatCard
        label="Hallucinations"
        value={data.hallucination_count.toLocaleString()}
        subValue={formatPercentage(data.hallucination_rate)}
        icon={<AlertTriangle className="h-4 w-4" />}
        color="red"
      />
      <StatCard
        label="Clean Rate"
        value={formatPercentage(cleanRate)}
        subValue={`${data.total_checks - data.hallucination_count} clean`}
        icon={<CheckCircle2 className="h-4 w-4" />}
        color={cleanRate >= 0.95 ? 'green' : cleanRate >= 0.9 ? 'amber' : 'red'}
      />
      <StatCard
        label="Avg Confidence"
        value={formatPercentage(data.avg_confidence)}
        icon={<Shield className="h-4 w-4" />}
        color={data.avg_confidence >= 0.8 ? 'green' : data.avg_confidence >= 0.6 ? 'amber' : 'red'}
      />
    </div>
  );
}

// Score breakdown component
export function ScoreBreakdown({ data }: { data: HallucinationAnalytics }) {
  const scores = [
    {
      label: 'Hallucination Score',
      value: data.avg_hallucination_score,
      description: 'Lower is better',
      good: (v: number) => v < 0.3,
      warning: (v: number) => v >= 0.3 && v < 0.5,
    },
    {
      label: 'Grounding Score',
      value: data.avg_grounding_score,
      description: 'Higher is better',
      good: (v: number) => v >= 0.7,
      warning: (v: number) => v >= 0.5 && v < 0.7,
    },
    {
      label: 'Relevance Score',
      value: data.avg_relevance_score,
      description: 'Higher is better',
      good: (v: number) => v >= 0.7,
      warning: (v: number) => v >= 0.5 && v < 0.7,
    },
  ];

  return (
    <div className="space-y-4">
      {scores.map((score) => {
        const isGood = score.good(score.value);
        const isWarning = score.warning(score.value);
        const color = isGood ? 'bg-green-500' : isWarning ? 'bg-yellow-500' : 'bg-red-500';
        const textColor = isGood ? 'text-green-500' : isWarning ? 'text-yellow-500' : 'text-red-500';

        return (
          <div key={score.label} className="space-y-2">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-sm font-medium">{score.label}</span>
                <span className="text-xs text-muted-foreground ml-2">
                  ({score.description})
                </span>
              </div>
              <span className={cn('text-sm font-medium', textColor)}>
                {formatPercentage(score.value)}
              </span>
            </div>
            <div className="h-2 rounded-full bg-muted overflow-hidden">
              <div
                className={cn('h-full rounded-full transition-all', color)}
                style={{ width: `${score.value * 100}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// Compact health indicator
export function HallucinationHealthIndicator({
  hallucinationRate,
  size = 'default',
}: {
  hallucinationRate: number;
  size?: 'sm' | 'default' | 'lg';
}) {
  const isHealthy = hallucinationRate < 0.1;
  const isWarning = hallucinationRate >= 0.1 && hallucinationRate < 0.2;

  const sizeClasses = {
    sm: 'h-6 w-6',
    default: 'h-8 w-8',
    lg: 'h-12 w-12',
  };

  const Icon = isHealthy ? CheckCircle2 : AlertTriangle;
  const color = isHealthy ? 'text-green-500' : isWarning ? 'text-yellow-500' : 'text-red-500';

  return (
    <div className={cn('flex items-center gap-2', color)}>
      <Icon className={sizeClasses[size]} />
      <div>
        <div className="text-sm font-medium">
          {isHealthy ? 'Healthy' : isWarning ? 'Warning' : 'Critical'}
        </div>
        <div className="text-xs opacity-80">
          {formatPercentage(hallucinationRate)} hallucination rate
        </div>
      </div>
    </div>
  );
}
