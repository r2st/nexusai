'use client';

import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import type { TimeSeriesDataPoint } from './types';

// Theme constants matching the project style
const axisStyle = {
  fontSize: 11,
  fill: '#94a3b8',
  fontFamily: 'ui-monospace, monospace',
};

const gridStyle = {
  stroke: '#334155',
  strokeDasharray: '3 3',
  opacity: 0.2,
};

const tooltipStyle: React.CSSProperties = {
  backgroundColor: 'rgba(15, 23, 42, 0.9)',
  border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: '8px',
  fontSize: '12px',
  color: '#f8fafc',
  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
};

const CHART_COLORS = {
  cost: '#22c55e',      // green-500
  tokens: '#3b82f6',    // blue-500
  requests: '#8b5cf6',  // violet-500
};

function formatDate(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return dateStr;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  } catch {
    return dateStr;
  }
}

function formatDateFull(dateStr: unknown): string {
  const str = String(dateStr);
  try {
    const date = new Date(str);
    if (isNaN(date.getTime())) return str;
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  } catch {
    return str;
  }
}

function formatCurrency(value: number): string {
  return `$${value.toFixed(4)}`;
}

function formatNumber(value: number): string {
  if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
  if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
  return value.toString();
}

interface CostTimeSeriesChartProps {
  data: TimeSeriesDataPoint[];
  height?: number;
  showCost?: boolean;
  showTokens?: boolean;
  showRequests?: boolean;
}

export function CostTimeSeriesChart({
  data,
  height = 300,
  showCost = true,
  showTokens = false,
  showRequests = false,
}: CostTimeSeriesChartProps) {
  // Transform data for the chart
  const chartData = data.map((point) => ({
    ...point,
    date: point.period,
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={chartData}>
        <defs>
          <linearGradient id="costGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={CHART_COLORS.cost} stopOpacity={0.3} />
            <stop offset="95%" stopColor={CHART_COLORS.cost} stopOpacity={0} />
          </linearGradient>
          <linearGradient id="tokensGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={CHART_COLORS.tokens} stopOpacity={0.3} />
            <stop offset="95%" stopColor={CHART_COLORS.tokens} stopOpacity={0} />
          </linearGradient>
          <linearGradient id="requestsGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={CHART_COLORS.requests} stopOpacity={0.3} />
            <stop offset="95%" stopColor={CHART_COLORS.requests} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid {...gridStyle} vertical={false} />
        <XAxis
          dataKey="date"
          tickFormatter={formatDate}
          {...axisStyle}
          axisLine={false}
          tickLine={false}
          dy={10}
        />
        <YAxis
          yAxisId="cost"
          {...axisStyle}
          axisLine={false}
          tickLine={false}
          tickFormatter={formatCurrency}
          orientation="left"
          hide={!showCost}
        />
        <YAxis
          yAxisId="tokens"
          {...axisStyle}
          axisLine={false}
          tickLine={false}
          tickFormatter={formatNumber}
          orientation="right"
          hide={!showTokens && !showRequests}
        />
        <Tooltip
          contentStyle={tooltipStyle}
          labelFormatter={formatDateFull}
          formatter={(value, name) => {
            const v = typeof value === 'number' ? value : 0;
            const n = typeof name === 'string' ? name : '';
            if (n === 'Cost') return [formatCurrency(v), n];
            return [formatNumber(v), n];
          }}
        />
        <Legend />
        {showCost && (
          <Area
            yAxisId="cost"
            type="monotone"
            dataKey="total_cost"
            name="Cost"
            stroke={CHART_COLORS.cost}
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#costGradient)"
          />
        )}
        {showTokens && (
          <Area
            yAxisId="tokens"
            type="monotone"
            dataKey="total_tokens"
            name="Tokens"
            stroke={CHART_COLORS.tokens}
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#tokensGradient)"
          />
        )}
        {showRequests && (
          <Area
            yAxisId="tokens"
            type="monotone"
            dataKey="request_count"
            name="Requests"
            stroke={CHART_COLORS.requests}
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#requestsGradient)"
          />
        )}
      </AreaChart>
    </ResponsiveContainer>
  );
}

// Simple cost-only line chart variant
export function CostTrendChart({
  data,
  height = 200,
}: {
  data: TimeSeriesDataPoint[];
  height?: number;
}) {
  return (
    <CostTimeSeriesChart
      data={data}
      height={height}
      showCost={true}
      showTokens={false}
      showRequests={false}
    />
  );
}
