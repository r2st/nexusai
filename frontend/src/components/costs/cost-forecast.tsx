'use client';

import { TrendingUp, TrendingDown, Minus, AlertCircle, CheckCircle2 } from 'lucide-react';
import type { CostForecast as CostForecastType } from './types';
import { cn } from '@/lib/utils';

function formatCurrency(value: number): string {
  if (value >= 1000) return `$${(value / 1000).toFixed(2)}K`;
  if (value >= 1) return `$${value.toFixed(2)}`;
  return `$${value.toFixed(4)}`;
}

interface CostForecastProps {
  data: CostForecastType;
  currentMonthSpend?: number;
}

export function CostForecastWidget({ data, currentMonthSpend }: CostForecastProps) {
  const getConfidenceColor = (confidence: string) => {
    switch (confidence) {
      case 'high':
        return 'text-green-500';
      case 'medium':
        return 'text-yellow-500';
      case 'low':
        return 'text-red-500';
      default:
        return 'text-muted-foreground';
    }
  };

  const getConfidenceIcon = (confidence: string) => {
    switch (confidence) {
      case 'high':
        return <CheckCircle2 className="h-4 w-4" />;
      case 'medium':
        return <AlertCircle className="h-4 w-4" />;
      case 'low':
        return <AlertCircle className="h-4 w-4" />;
      default:
        return <Minus className="h-4 w-4" />;
    }
  };

  // Calculate trend vs current if provided
  const trend = currentMonthSpend
    ? ((data.projected_monthly_cost - currentMonthSpend) / currentMonthSpend) * 100
    : null;

  const getTrendIcon = () => {
    if (trend === null || Math.abs(trend) < 5) {
      return <Minus className="h-5 w-5 text-muted-foreground" />;
    }
    if (trend > 0) {
      return <TrendingUp className="h-5 w-5 text-red-500" />;
    }
    return <TrendingDown className="h-5 w-5 text-green-500" />;
  };

  return (
    <div className="space-y-4">
      {/* Main Projection */}
      <div className="text-center">
        <div className="flex items-center justify-center gap-2">
          {getTrendIcon()}
          <span className="text-4xl font-bold">
            {formatCurrency(data.projected_monthly_cost)}
          </span>
        </div>
        <p className="text-sm text-muted-foreground mt-1">
          Projected Monthly Cost
        </p>
        {trend !== null && (
          <p
            className={cn(
              'text-xs mt-1',
              trend > 0 ? 'text-red-500' : trend < 0 ? 'text-green-500' : 'text-muted-foreground'
            )}
          >
            {trend > 0 ? '+' : ''}
            {trend.toFixed(1)}% vs current pace
          </p>
        )}
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-4 pt-4 border-t">
        <div>
          <p className="text-sm text-muted-foreground">Daily Average</p>
          <p className="text-xl font-semibold">{formatCurrency(data.daily_average)}</p>
        </div>
        <div>
          <p className="text-sm text-muted-foreground">Basis Period</p>
          <p className="text-xl font-semibold">{data.basis_days} days</p>
        </div>
      </div>

      {/* Confidence Indicator */}
      <div className="flex items-center justify-between pt-4 border-t">
        <span className="text-sm text-muted-foreground">Forecast Confidence</span>
        <div className={cn('flex items-center gap-1.5', getConfidenceColor(data.confidence))}>
          {getConfidenceIcon(data.confidence)}
          <span className="text-sm font-medium capitalize">{data.confidence}</span>
        </div>
      </div>

      {/* Basis Info */}
      <div className="text-xs text-muted-foreground pt-2 border-t">
        <p>
          Based on {formatCurrency(data.basis_cost)} spent across{' '}
          {data.basis_requests.toLocaleString()} requests in the last{' '}
          {data.basis_days} days.
        </p>
      </div>
    </div>
  );
}

// Compact inline forecast display
export function CostForecastInline({ data }: { data: CostForecastType }) {
  return (
    <div className="flex items-center gap-4">
      <div>
        <span className="text-sm text-muted-foreground">Projected: </span>
        <span className="font-semibold">{formatCurrency(data.projected_monthly_cost)}/mo</span>
      </div>
      <div className="text-xs text-muted-foreground">
        ({formatCurrency(data.daily_average)}/day)
      </div>
      <div
        className={cn(
          'text-xs px-2 py-0.5 rounded-full',
          data.confidence === 'high'
            ? 'bg-green-500/10 text-green-500'
            : data.confidence === 'medium'
            ? 'bg-yellow-500/10 text-yellow-500'
            : 'bg-red-500/10 text-red-500'
        )}
      >
        {data.confidence} confidence
      </div>
    </div>
  );
}
