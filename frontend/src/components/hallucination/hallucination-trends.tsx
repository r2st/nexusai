'use client';

import {
  ResponsiveContainer,
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import type { TrendDataPoint } from './types';

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
  hallucination: '#f43f5e', // rose-500
  checks: '#3b82f6',        // blue-500
  rate: '#f59e0b',          // amber-500
  score: '#8b5cf6',         // violet-500
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

function formatPercentage(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

interface HallucinationTrendsChartProps {
  data: TrendDataPoint[];
  height?: number;
  showRate?: boolean;
  showScore?: boolean;
  showCount?: boolean;
}

export function HallucinationTrendsChart({
  data,
  height = 300,
  showRate = true,
  showScore = true,
  showCount = false,
}: HallucinationTrendsChartProps) {
  const chartData = data.map((point) => ({
    ...point,
    date: point.period,
    rate: point.hallucination_rate,
    score: point.avg_hallucination_score,
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={chartData}>
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
          yAxisId="rate"
          {...axisStyle}
          axisLine={false}
          tickLine={false}
          tickFormatter={formatPercentage}
          domain={[0, 1]}
          orientation="left"
        />
        <YAxis
          yAxisId="count"
          {...axisStyle}
          axisLine={false}
          tickLine={false}
          orientation="right"
          hide={!showCount}
        />
        <Tooltip
          contentStyle={tooltipStyle}
          labelFormatter={formatDateFull}
          formatter={(value: number | undefined, name: string | undefined) => {
            const v = value ?? 0;
            if (name === 'Hallucination Rate' || name === 'Avg Score') {
              return [formatPercentage(v), name ?? ''];
            }
            return [v, name ?? ''];
          }}
        />
        <Legend />
        {showRate && (
          <Line
            yAxisId="rate"
            type="monotone"
            dataKey="rate"
            name="Hallucination Rate"
            stroke={CHART_COLORS.rate}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 5, fill: CHART_COLORS.rate }}
          />
        )}
        {showScore && (
          <Line
            yAxisId="rate"
            type="monotone"
            dataKey="score"
            name="Avg Score"
            stroke={CHART_COLORS.score}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 5, fill: CHART_COLORS.score }}
          />
        )}
        {showCount && (
          <Line
            yAxisId="count"
            type="monotone"
            dataKey="hallucination_count"
            name="Hallucinations"
            stroke={CHART_COLORS.hallucination}
            strokeWidth={2}
            dot={false}
          />
        )}
      </LineChart>
    </ResponsiveContainer>
  );
}

// Area chart variant showing hallucinations vs total checks
export function HallucinationVolumeChart({
  data,
  height = 250,
}: {
  data: TrendDataPoint[];
  height?: number;
}) {
  const chartData = data.map((point) => ({
    date: point.period,
    checks: point.total_checks,
    hallucinations: point.hallucination_count,
    clean: point.total_checks - point.hallucination_count,
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={chartData}>
        <defs>
          <linearGradient id="hallucinationGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={CHART_COLORS.hallucination} stopOpacity={0.3} />
            <stop offset="95%" stopColor={CHART_COLORS.hallucination} stopOpacity={0} />
          </linearGradient>
          <linearGradient id="checksGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={CHART_COLORS.checks} stopOpacity={0.3} />
            <stop offset="95%" stopColor={CHART_COLORS.checks} stopOpacity={0} />
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
        <YAxis {...axisStyle} axisLine={false} tickLine={false} />
        <Tooltip
          contentStyle={tooltipStyle}
          labelFormatter={formatDateFull}
        />
        <Legend />
        <Area
          type="monotone"
          dataKey="clean"
          name="Clean Responses"
          stackId="1"
          stroke={CHART_COLORS.checks}
          strokeWidth={2}
          fillOpacity={1}
          fill="url(#checksGradient)"
        />
        <Area
          type="monotone"
          dataKey="hallucinations"
          name="Hallucinations"
          stackId="1"
          stroke={CHART_COLORS.hallucination}
          strokeWidth={2}
          fillOpacity={1}
          fill="url(#hallucinationGradient)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
