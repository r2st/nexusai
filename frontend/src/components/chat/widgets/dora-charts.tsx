'use client';

import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  BarChart,
  Bar,
  LineChart,
  Line,
} from 'recharts';
import type { DORAChartDataPoint } from './types';

// --- Theme constants (matching sample) ---

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
  boxShadow:
    '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
};

// Chart accent colors
const CHART_COLORS = {
  deploy: '#22c55e',   // green-500
  lead: '#3b82f6',     // blue-500
  restore: '#8b5cf6',  // violet-500
  failure: '#f43f5e',  // rose-500
};

function formatDateLabel(d: string): string {
  try {
    const date = new Date(d);
    if (isNaN(date.getTime())) return d;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  } catch {
    return d;
  }
}

function formatDateFull(d: unknown): string {
  const str = String(d);
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

// --- Chart Components ---

interface DORAChartProps {
  data: DORAChartDataPoint[];
}

export function DeploymentFrequencyChart({ data }: DORAChartProps) {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data}>
        <CartesianGrid {...gridStyle} vertical={false} />
        <XAxis
          dataKey="date"
          tickFormatter={formatDateLabel}
          {...axisStyle}
          axisLine={false}
          tickLine={false}
          dy={10}
        />
        <YAxis {...axisStyle} axisLine={false} tickLine={false} />
        <Tooltip
          contentStyle={tooltipStyle}
          labelFormatter={formatDateFull}
          cursor={{ fill: 'rgba(255,255,255,0.05)' }}
        />
        <Bar
          dataKey="deploymentFrequency"
          name="Deployments/Day"
          fill={CHART_COLORS.deploy}
          radius={[4, 4, 0, 0]}
          maxBarSize={32}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function LeadTimeChart({ data }: DORAChartProps) {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data}>
        <CartesianGrid {...gridStyle} vertical={false} />
        <XAxis
          dataKey="date"
          tickFormatter={formatDateLabel}
          {...axisStyle}
          axisLine={false}
          tickLine={false}
          dy={10}
        />
        <YAxis {...axisStyle} axisLine={false} tickLine={false} unit="m" />
        <Tooltip
          contentStyle={tooltipStyle}
          labelFormatter={formatDateFull}
        />
        <Line
          type="monotone"
          dataKey="leadTimeForChanges"
          name="Lead Time (min)"
          stroke={CHART_COLORS.lead}
          strokeWidth={2.5}
          dot={false}
          activeDot={{ r: 5, fill: CHART_COLORS.lead }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function RestoreTimeChart({ data }: DORAChartProps) {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={data}>
        <defs>
          <linearGradient id="doraColorRestore" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={CHART_COLORS.restore} stopOpacity={0.3} />
            <stop offset="95%" stopColor={CHART_COLORS.restore} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid {...gridStyle} vertical={false} />
        <XAxis
          dataKey="date"
          tickFormatter={formatDateLabel}
          {...axisStyle}
          axisLine={false}
          tickLine={false}
          dy={10}
        />
        <YAxis {...axisStyle} axisLine={false} tickLine={false} unit="m" />
        <Tooltip
          contentStyle={tooltipStyle}
          labelFormatter={formatDateFull}
        />
        <Area
          type="monotone"
          dataKey="timeToRestoreService"
          name="Time to Restore (min)"
          stroke={CHART_COLORS.restore}
          strokeWidth={2.5}
          fillOpacity={1}
          fill="url(#doraColorRestore)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function ChangeFailureChart({ data }: DORAChartProps) {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data}>
        <CartesianGrid {...gridStyle} vertical={false} />
        <XAxis
          dataKey="date"
          tickFormatter={formatDateLabel}
          {...axisStyle}
          axisLine={false}
          tickLine={false}
          dy={10}
        />
        <YAxis {...axisStyle} axisLine={false} tickLine={false} unit="%" />
        <Tooltip
          contentStyle={tooltipStyle}
          labelFormatter={formatDateFull}
        />
        <Line
          type="stepAfter"
          dataKey="changeFailureRate"
          name="Failure Rate (%)"
          stroke={CHART_COLORS.failure}
          strokeWidth={2.5}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
